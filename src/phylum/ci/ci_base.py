"""Define a base environment for CI platforms.

The "base" environment is one that makes use of the CLI directly and is not necessarily part of a continuous
integration (CI) environment. Common functionality is provided where possible and CI specific features are
designated as abstract methods to be defined in specific CI environments.
"""
import shutil
import string
import subprocess
import textwrap
from abc import ABC, abstractmethod
from argparse import Namespace
from contextlib import contextmanager
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Generator, List, Optional, Tuple

from packaging.version import Version
from phylum.constants import SUPPORTED_LOCKFILES
from phylum.init.cli import get_expected_phylum_bin_path
from phylum.init.cli import main as phylum_init

# Headers for distinct comment types
FAILED_COMMENT = textwrap.dedent(
    """
    ## Phylum OSS Supply Chain Risk Analysis - FAILED

    <details>
    <summary>Background</summary>
    <br />
    This repository analyzes the risk of new dependencies. An administrator of
    this repository has set score requirements for Phylum's five risk domains.
    <br /><br />
    If you see this comment, one or more dependencies added to the
    package manager lockfile have failed Phylum's risk analysis.
    </details>

    """
)
SUCCESS_COMMENT = textwrap.dedent(
    """
    ## Phylum OSS Supply Chain Risk Analysis - SUCCESS

    The Phylum risk analysis is complete and did not identify any issues.
    """
).strip()
INCOMPLETE_COMMENT_TEMPLATE = string.Template(
    textwrap.dedent(
        """
        ## Phylum OSS Supply Chain Risk Analysis - INCOMPLETE

        The analysis contains $count package(s) Phylum has not yet processed, preventing
        a complete risk analysis. Phylum is processing these packages currently and
        should complete within 30 minutes. Please wait for at least 30 minutes,
        then re-run the analysis.
        """
    ).strip()
)


# TODO: Move this function to the `phylum.init` package?
def get_phylum_cli_version(cli_path: Path) -> str:
    """Get the version of the installed and active Phylum CLI and return it."""
    cmd = f"{cli_path} --version"
    version = subprocess.run(cmd.split(), check=True, capture_output=True, text=True).stdout.strip().lower()

    # Starting with Python 3.9, the str.removeprefix() method was introduced to do this same thing
    prefix = "phylum "
    prefix_len = len(prefix)
    if version.startswith(prefix):
        version = version[prefix_len:]

    return version


# TODO: Move this function to the `phylum.init` package?
def get_phylum_bin_path(version: str = None) -> Tuple[Optional[Path], Optional[str]]:
    """Get the current path and corresponding version to the Phylum CLI binary and return them.

    Provide a CLI version as a fallback method for looking on an explicit path,
    based on the expected path for that version.
    """
    # Look for `phylum` on the PATH first
    which_cli_path = shutil.which("phylum")

    if which_cli_path is None and version is not None:
        # Maybe `phylum` is installed already but not on the PATH or maybe the PATH has not been updated in this
        # context. Look in the specific location expected by the provided version.
        expected_cli_path = get_expected_phylum_bin_path(version)
        which_cli_path = shutil.which("phylum", path=expected_cli_path)

    if which_cli_path is None:
        return (None, None)

    cli_path = Path(which_cli_path)
    cli_version = get_phylum_cli_version(cli_path)
    return cli_path, cli_version


def detect_lockfile() -> Optional[Path]:
    """Detect the lockfile in use and return it.

    This method has some assumptions:
      * It is called from the root of a repository
      * There is only one lockfile allowed
    """
    cwd = Path.cwd()
    lockfiles_in_cwd = [path.resolve() for lockfile_glob in SUPPORTED_LOCKFILES for path in cwd.glob(lockfile_glob)]
    if not lockfiles_in_cwd:
        return None
    if len(lockfiles_in_cwd) > 1:
        lockfiles = ", ".join(str(lockfile) for lockfile in lockfiles_in_cwd)
        print(f" [!] Multiple lockfiles detected: {lockfiles}")
        raise SystemExit(" [!] Only one lockfile is supported at this time. Consider specifying it with `--lockfile`.")
    lockfile = lockfiles_in_cwd[0]
    return lockfile


@dataclass(order=True, frozen=True)
class PackageDescriptor:
    """Class for keeping track of packages returned by the `phylum parse` subcommand."""

    name: str
    version: str
    type: str


Packages = List[PackageDescriptor]


class ReturnCode(IntEnum):
    """Integer enumeration to track return codes."""

    SUCCESS = 0
    FAILURE = 1
    INCOMPLETE = 5


class CIBase(ABC):
    """Provide methods for a basic CI environment."""

    @abstractmethod
    def __init__(self, args: Namespace) -> None:
        self.args = args

        # The risk vector values returned by the analysis are normalized to (0.0, 1.0]. The option values are converted
        # internally like this b/c it is more natural to ask users for input as an integer in the range of [0, 100).
        # TODO: If these are only used in one place, consider removing them from here and converting in place instead.
        self.vul = args.vul_threshold / 100
        self.mal = args.mal_threshold / 100
        self.eng = args.eng_threshold / 100
        self.lic = args.lic_threshold / 100
        self.aut = args.aut_threshold / 100

        self.gbl_failed = False
        self.gbl_incomplete = False
        self.incomplete_pkgs: Packages = []
        # self.previous_incomplete = False

        self._cli_path: Optional[Path] = None

        # The lockfile specified as a script argument will be used, if provided.
        # Otherwise, an attempt will be made to automatically detect the lockfile.
        self._lockfile = None
        provided_lockfile: Path = args.lockfile
        if provided_lockfile and provided_lockfile.exists():
            self._lockfile = provided_lockfile.resolve()
        else:
            self._lockfile = detect_lockfile()

        # Assume the lockfile has not changed unless proven otherwise by the specific CI environment
        self._lockfile_changed = False
        if self.lockfile:
            self._lockfile_changed = self._is_lockfile_changed(self.lockfile)

    @property
    def lockfile(self) -> Optional[Path]:
        """Get the package lockfile."""
        return self._lockfile

    @property
    def is_lockfile_changed(self) -> bool:
        """Get the lockfile's modification status."""
        return self._lockfile_changed

    @property
    def cli_path(self) -> Optional[Path]:
        """Get the path to the Phylum CLI binary."""
        return self._cli_path

    @property
    @abstractmethod
    def phylum_label(self) -> str:
        """Get a custom label for use when submitting jobs with `phylum analyze`.

        Each CI platform/environment has unique ways of referencing events, PRs, branches, etc.
        """

    @abstractmethod
    def _is_lockfile_changed(self, lockfile: Path) -> bool:
        """Predicate for detecting if the given lockfile has changed."""

    @contextmanager
    @abstractmethod
    def check_prerequisites(self) -> Generator:
        """Ensure the necessary pre-requisites are met and bail when they aren't.

        The current pre-requisites for *all* CI environments/platforms are:
          * A `.phylum_project` file exists at the working directory
          * Phylum CLI v3.3.0+, to make use of the `parse` subcommand
        """
        print(" [+] Confirming pre-requisites ...")

        phylum_project_file = Path.cwd() / ".phylum_project"
        if phylum_project_file.exists():
            print(" [+] Existing `.phylum_project` file was found at the current working directory")
        else:
            # TODO: Consider using CI specific error reporting
            raise SystemExit(" [!] The `.phylum_project` file was not found at the current working directory")

        if Version("v3.2.0") >= Version(self.args.version):
            raise SystemExit(" [!] The CLI version must be greater than v3.2.0")

        yield
        print(" [+] All pre-requisites met")

    def init_cli(self) -> None:
        """Check for an existing Phylum CLI install, install it if needed, and set the path class instance variable."""
        specified_version = self.args.version
        cli_path, cli_version = get_phylum_bin_path(version=specified_version)
        if cli_path is None:
            print(f" [+] Existing Phylum CLI instance not found. Installing version `{specified_version}` ...")
            install_args = ["--phylum-release", specified_version, "--phylum-token", self.args.token]
            phylum_init(install_args)
        else:
            print(f" [+] Existing Phylum CLI instance found: {cli_version} at {cli_path}")
            if cli_version != specified_version:
                print(f" [+] Existing version {cli_version} does not match the specified version {specified_version}")
                if self.args.force_install:
                    print(f" [*] Installing Phylum CLI version {specified_version} ...")
                    install_args = ["--phylum-release", specified_version, "--phylum-token", self.args.token]
                    phylum_init(install_args)
                else:
                    print(" [+] Attempting to use existing version ...")
                    if Version("v3.2.0") >= Version(cli_version):
                        raise SystemExit(" [!] The existing CLI version must be greater than v3.2.0")

                    # TODO: Account for the case that the existing version does not already have a token in place. This
                    #       could be the case if the Docker image is built with a known good/compatible CLI version but
                    #       without a token so that any user can use the image with their own supplied token.
                    #       https://github.com/phylum-dev/phylum-ci/issues/32

                    print(" [+] Version checks succeeded. Using existing version.")

        cli_path, cli_version = get_phylum_bin_path(version=specified_version)
        print(f" [+] Using Phylum CLI instance: {cli_version} at {str(cli_path)}")

        self._cli_path = cli_path

    def analyze(self, analysis: dict) -> ReturnCode:
        """TODO."""
        project_id = analysis.get("project")
        project_url = f"https://app.phylum.io/projects/{project_id}"
        print(f" [+] Project URL: {project_url}")

        if self.args.new_deps_only:
            print(" [+] Only considering newly added dependencies ...")
        else:
            print(" [+] Considering all current dependencies ...")
            pkgs = analysis.get("packages", [])
            packages = [PackageDescriptor(pkg.get("name"), pkg.get("version"), pkg.get("type")) for pkg in pkgs]
            risk_data = self.parse_risk_data(analysis, packages)

            returncode = ReturnCode.SUCCESS
            output = ""
            # Write output only if the analysis failed and all pkgvers are completed
            if self.gbl_failed and not self.gbl_incomplete:
                print(" [!] The analysis is complete and there were failures")
                returncode = ReturnCode.FAILURE
                output = FAILED_COMMENT
                for line in risk_data:
                    output += line

            if self.gbl_incomplete:
                print(f" [+] {len(self.incomplete_pkgs)} packages were incomplete in the analysis results")
                returncode = ReturnCode.INCOMPLETE
                output = INCOMPLETE_COMMENT_TEMPLATE.substitute(count=len(self.incomplete_pkgs))

            if not self.gbl_failed and not self.gbl_incomplete:
                print(" [+] The analysis is complete and there were no failures")
                returncode = ReturnCode.SUCCESS
                output = SUCCESS_COMMENT

            output += f"\n[View this project in the Phylum UI]({project_url})"
            # TODO: Do something else with the output
            print(f" [+] Output:\n{output}")

        return returncode

    def parse_risk_data(self, analysis_results: dict, packages: Packages) -> List[str]:
        """Parse risk packages from a Phylum analysis.

        Packages that are in a completed analysis state will be included in the risk score report.
        Packages that have not completed analysis will be included with other incomplete packages
        and the overall PR will be allowed to pass, but with a note about re-running again later.
        """
        analysis_pkgs = analysis_results.get("packages", [])
        risk_scores = []
        for package in packages:
            for phylum_pkg in analysis_pkgs:
                if phylum_pkg.get("name") == package.name and phylum_pkg.get("version") == package.version:
                    if phylum_pkg.get("status") == "complete":
                        risk_score = self.check_risk_scores(phylum_pkg)
                        if risk_score:
                            risk_scores.append(risk_score)
                    elif phylum_pkg.get("status") == "incomplete":
                        self.incomplete_pkgs.append(package)
                        self.gbl_incomplete = True

        return risk_scores

    def check_risk_scores(self, package_result: dict) -> Optional[str]:
        """Check risk scores of a package against user-provided thresholds.

        If a package has a risk score below the threshold, set the fail flag and generate the markdown output.
        """
        failed_flag = False
        risk_vectors = package_result.get("riskVectors", {})
        issue_flags = []
        fail_string = f"### Package: `{package_result.get('name')}@{package_result.get('version')}` failed.\n"
        fail_string += "|Risk Domain|Identified Score|Requirement|\n"
        fail_string += "|-----------|----------------|-----------|\n"

        pkg_vul = risk_vectors.get("vulnerability", 1.0)
        pkg_mal = risk_vectors.get("malicious_code", 1.0)
        pkg_eng = risk_vectors.get("engineering", 1.0)
        pkg_lic = risk_vectors.get("license", 1.0)
        pkg_aut = risk_vectors.get("author", 1.0)
        if pkg_vul <= self.vul:
            failed_flag = True
            issue_flags.append("vulnerability")
            fail_string += f"|Software Vulnerability|{pkg_vul*100}|{self.vul*100}|\n"
        if pkg_mal <= self.mal:
            failed_flag = True
            issue_flags.append("malicious_code")
            fail_string += f"|Malicious Code|{pkg_mal*100}|{self.mal*100}|\n"
        if pkg_eng <= self.eng:
            failed_flag = True
            issue_flags.append("engineering")
            fail_string += f"|Engineering|{pkg_eng*100}|{self.eng*100}|\n"
        if pkg_lic <= self.lic:
            failed_flag = True
            issue_flags.append("license")
            fail_string += f"|License|{pkg_lic*100}|{self.lic*100}|\n"
        if pkg_aut <= self.aut:
            failed_flag = True
            issue_flags.append("author")
            fail_string += f"|Author|{pkg_aut*100}|{self.aut*100}|\n"

        fail_string += "\n"
        fail_string += "#### Issues Summary\n"
        fail_string += "|Risk Domain|Risk Level|Title|\n"
        fail_string += "|-----------|----------|-----|\n"

        issue_list = self.build_issues_list(package_result, issue_flags)
        for risk_domain, risk_level, title in issue_list:
            fail_string += f"|{risk_domain}|{risk_level}|{title}|\n"

        if failed_flag:
            self.gbl_failed = True
            return fail_string
        return None

    def build_issues_list(self, package_result: dict, issue_flags: List[str]) -> List[Tuple[str, str, str]]:
        """TODO."""
        issues = []
        pkg_issues = package_result.get("issues", [])
        for flag in issue_flags:
            for pkg_issue in pkg_issues:
                if flag == pkg_issue.get("risk_domain"):
                    risk_domain = pkg_issue.get("risk_domain")
                    risk_level = pkg_issue.get("risk_level")
                    title = pkg_issue.get("title")
                    issues.append((risk_domain, risk_level, title))
        return issues
