"""Define a base environment for CI platforms.

The "base" environment is one that makes use of the CLI directly and is not necessarily part of a continuous
integration (CI) environment. Common functionality is provided where possible and CI specific features are
designated as abstract methods to be defined in specific CI environments.
"""
import json
import os
import shutil
import subprocess
import tempfile
import textwrap
import urllib.parse
from abc import ABC, abstractmethod
from argparse import Namespace
from pathlib import Path
from typing import List, Optional, Tuple

from connect.utils.terminal.markdown import render
from packaging.version import Version
from ruamel.yaml import YAML

from phylum.ci.common import PackageDescriptor, Packages, ProjectThresholdInfo, ReturnCode, RiskDomain
from phylum.ci.constants import (
    FAILED_COMMENT,
    INCOMPLETE_COMMENT_TEMPLATE,
    INCOMPLETE_WITH_FAILURE_COMMENT_TEMPLATE,
    PROJECT_THRESHOLD_OPTIONS,
    SUCCESS_COMMENT,
)
from phylum.constants import MIN_CLI_VER_INSTALLED, SUPPORTED_LOCKFILES, TOKEN_ENVVAR_NAME
from phylum.init.cli import get_phylum_bin_path
from phylum.init.cli import main as phylum_init


def git_remote() -> str:
    """Get the git remote and return it.

    This function is limited in that it will only work when there is a single remote defined.
    A RuntimeError exception will be raised when there is not exactly one remote.
    """
    cmd = ["git", "remote"]
    remotes = subprocess.run(cmd, check=True, text=True, capture_output=True).stdout.splitlines()
    if not remotes:
        raise RuntimeError("No git remotes configured")
    if len(remotes) > 1:
        raise RuntimeError("Only one git remote is supported at this time")
    remote = remotes[0]
    return remote


def detect_lockfile() -> Optional[Path]:
    """Detect the lockfile in use and return it.

    This method has some assumptions:
      * It is called from the root of a repository
      * There is only one lockfile allowed
    """
    cwd = Path.cwd()
    lockfiles_in_cwd = [path.resolve() for lockfile_glob in SUPPORTED_LOCKFILES for path in cwd.glob(lockfile_glob)]
    lockfiles_in_cwd = [path for path in lockfiles_in_cwd if path.stat().st_size]
    if not lockfiles_in_cwd:
        return None
    if len(lockfiles_in_cwd) > 1:
        lockfiles = ", ".join(str(lockfile) for lockfile in lockfiles_in_cwd)
        print(f" [!] Multiple lockfiles detected: {lockfiles}")
        raise SystemExit(" [!] Only one lockfile is supported at this time. Consider specifying it with `--lockfile`.")
    lockfile = lockfiles_in_cwd[0]
    return lockfile


class CIBase(ABC):
    """Provide methods for a basic CI environment."""

    @abstractmethod
    def __init__(self, args: Namespace) -> None:
        """Initialize the base class object.

        Each child class is expected to at least:
          * call `super().__init__(args)`
          * define `self.ci_platform_name`
        """
        self.args = args
        self._phylum_project_file = Path.cwd().joinpath(".phylum_project").resolve()

        # The lockfile specified as a script argument will be used, if provided.
        # Otherwise, an attempt will be made to automatically detect the lockfile.
        provided_lockfile: Path = args.lockfile
        if provided_lockfile and provided_lockfile.exists() and provided_lockfile.stat().st_size:
            self._lockfile = provided_lockfile.resolve()
            print(f" [-] Provided lockfile: {self._lockfile}")
        else:
            detected_lockfile = detect_lockfile()
            if detected_lockfile:
                self._lockfile = detected_lockfile
                print(f" [-] Detected lockfile: {self._lockfile}")
            else:
                raise SystemExit(
                    " [!] A lockfile is required and was not detected. Consider specifying one with `--lockfile`."
                )

        self._phylum_project = args.project
        self._phylum_group = args.group

        # Ensure all pre-requisites are met and bail at the earliest opportunity when they aren't
        self._check_prerequisites()
        print(" [+] All pre-requisites met")

        self._cli_path: Optional[Path] = None
        self.gbl_failed = False
        self.gbl_incomplete = False
        self.incomplete_pkgs: Packages = []
        self._analysis_output = "No analysis output yet"
        self.ci_platform_name = "Unknown"

        # The token option takes precedence over the Phylum API key environment variable.
        token = os.getenv(TOKEN_ENVVAR_NAME)
        if args.token is not None:
            token = args.token
            os.environ[TOKEN_ENVVAR_NAME] = args.token
        self.args.token = token

        self._lockfile_changed = self._is_lockfile_changed(self.lockfile)

    @property
    def lockfile(self) -> Path:
        """Get the package lockfile."""
        return self._lockfile

    @property
    def is_lockfile_changed(self) -> bool:
        """Get the lockfile's modification status."""
        return self._lockfile_changed

    @property
    def phylum_project(self) -> str:
        """Get the effective Phylum project name in use.

        The Phylum project name can be specified as an option or contained in the `.phylum_project` file.
        A project name provided as an input option will be preferred over an entry in the `.phylum_project` file.

        Return `None` when the project name is not available.
        """
        # Project supplied as an option
        if self._phylum_project:
            return self._phylum_project

        # Project supplied in `.phylum_project`
        yaml = YAML()
        settings_dict = yaml.load(self.phylum_project_file.read_text(encoding="utf-8"))
        return settings_dict.get("name")

    @property
    def phylum_group(self) -> Optional[str]:
        """Get the effective Phylum group in use.

        The Phylum group name can be specified as an option or contained in the `.phylum_project` file.
        A group name provided as an input option will be preferred over an entry in the `.phylum_project` file.

        Return `None` when the group name is not available.
        """
        # Group supplied on command-line
        if self._phylum_project:
            return self._phylum_group

        # Group supplied in `.phylum_project`
        yaml = YAML()
        settings_dict = yaml.load(self.phylum_project_file.read_text(encoding="utf-8"))
        return settings_dict.get("group_name")

    @property
    def phylum_project_file(self) -> Path:
        """Get the path to the Phylum project file `.phylum_project`."""
        return self._phylum_project_file

    @property
    def cli_path(self) -> Optional[Path]:
        """Get the path to the Phylum CLI binary."""
        return self._cli_path

    @property
    def analysis_output(self) -> str:
        """Get the output from the overall analysis, in markdown format."""
        return self._analysis_output

    @property
    @abstractmethod
    def phylum_label(self) -> str:
        """Get a custom label for use when submitting jobs with `phylum analyze`.

        Each CI platform/environment has unique ways of referencing events, PRs, branches, etc.
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def common_lockfile_ancestor_commit(self) -> Optional[str]:
        """Find the common lockfile ancestor commit.

        When found, it should be returned as a string of the SHA1 sum representing the commit.
        When it can't be found (or there is an error), `None` should be returned.
        """
        raise NotImplementedError()

    @abstractmethod
    def _is_lockfile_changed(self, lockfile: Path) -> bool:
        """Predicate for detecting if the given lockfile has changed."""
        raise NotImplementedError()

    @abstractmethod
    def _check_prerequisites(self) -> None:
        """Ensure the necessary pre-requisites are met and bail when they aren't.

        The current pre-requisites for *all* CI environments/platforms are:
          * A `.phylum_project` file exists at the working directory or project name is specified as an option
          * A Phylum CLI version with the `parse` command
          * Have `git` installed and available for use on the PATH
        """
        print(" [+] Confirming pre-requisites ...")

        if self.phylum_project_file.exists():
            print(f" [+] Existing `.phylum_project` file found at: {self.phylum_project_file}")
        else:
            print(f" [+] No existing `.phylum_project` file found at: {self.phylum_project_file}")
            if self.phylum_project:
                print(f" [+] A Phylum project will be used (or created) with the provided name: {self.phylum_project}")
            else:
                msg = """\
                    [!] No Phylum project could be determined!
                    [!] Consider specifying one with `--project` and optionally with the `--group` option."""
                raise SystemExit(textwrap.dedent(msg))

        if Version(self.args.version) < Version(MIN_CLI_VER_INSTALLED):
            raise SystemExit(f" [!] The CLI version must be at least {MIN_CLI_VER_INSTALLED}")

        if shutil.which("git"):
            print(" [+] `git` binary found on the PATH")
        else:
            raise SystemExit(" [!] `git` is required to be installed and available on the PATH")

    def post_output(self) -> None:
        """Post the output of the analysis as markdown rendered for output to the terminal/logs.

        Each implementation that offers analysis output in the form of comments on a pull/merge request should
        ensure those comments are unique and not added multiple times as the review changes but the lockfile doesn't.
        """
        print(f" [+] Analysis output:\n{render(self.analysis_output)}")

    # TODO: Use the `@functools.cached_property` decorator, introduced in Python 3.8, to avoid computing more than once.
    #       https://github.com/phylum-dev/phylum-ci/issues/18
    @property
    def current_lockfile_packages(self) -> Packages:
        """Get the current lockfile packages.

        This property expects the Phylum CLI path to be known and will raise `SystemExit` when that path is unknown.
        """
        if not self.cli_path:
            raise SystemExit(" [!] Phylum CLI path is unknown. Try using the `init_cli` method first.")
        try:
            cmd = [str(self.cli_path), "parse", str(self.lockfile)]
            parse_result = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()
        except subprocess.CalledProcessError as err:
            print(f" [!] There was an error running the command: {' '.join(err.cmd)}")
            print(f" [!] stdout:\n{err.stdout}")
            print(f" [!] stderr:\n{err.stderr}")
            raise SystemExit(f" [!] Is {self.lockfile} valid? If so, please report this as a bug.") from err
        parsed_pkgs = json.loads(parse_result)
        curr_lockfile_packages = [PackageDescriptor(**pkg) for pkg in parsed_pkgs]
        return curr_lockfile_packages

    @property
    def previous_lockfile_object(self) -> Optional[str]:
        """Get the previous git object for the lockfile."""
        if not self.common_lockfile_ancestor_commit:
            return None
        try:
            cmd = [
                "git",
                "rev-parse",
                "--verify",
                f"{self.common_lockfile_ancestor_commit}:{self.lockfile.name}",
            ]
            prev_lockfile_object = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()
        except subprocess.CalledProcessError as err:
            # There could be a true error, but the working assumption when here is a previous version does not exist
            print(f" [?] There *may* be an issue with the attempt to get the previous lockfile object: {err}")
            print(f" [?] stdout:\n{err.stdout}")
            print(f" [?] stderr:\n{err.stderr}")
            print(" [+] Assuming a previous lockfile version does not exist ...")
            prev_lockfile_object = None
        return prev_lockfile_object

    def get_previous_lockfile_packages(self, prev_lockfile_object: str) -> Packages:
        """Get the previous lockfile packages from the corresponding git object and return them.

        Expects the Phylum CLI path to be known and will raise `SystemExit` when that path is unknown.
        """
        if not self.cli_path:
            raise SystemExit(" [!] Phylum CLI path is unknown. Try using the `init_cli` method first.")

        with tempfile.NamedTemporaryFile(mode="w+") as prev_lockfile_fd:
            try:
                cmd = ["git", "cat-file", "blob", prev_lockfile_object]
                prev_lockfile_contents = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
                prev_lockfile_fd.write(prev_lockfile_contents)
                prev_lockfile_fd.flush()
            except subprocess.CalledProcessError as err:
                print(f" [!] There was an error running the command: {' '.join(err.cmd)}")
                print(f" [!] stdout:\n{err.stdout}")
                print(f" [!] stderr:\n{err.stderr}")
                print(" [!] Due to error, assuming no previous lockfile packages. Please report this as a bug.")
                return []
            try:
                cmd = [str(self.cli_path), "parse", prev_lockfile_fd.name]
                parse_result = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()
            except subprocess.CalledProcessError as err:
                print(f" [!] There was an error running the command: {' '.join(err.cmd)}")
                print(f" [!] stdout:\n{err.stdout}")
                print(f" [!] stderr:\n{err.stderr}")
                print(" [!] Due to error, assuming no previous lockfile packages. Please report this as a bug.")
                return []

        parsed_pkgs = json.loads(parse_result)
        prev_lockfile_packages = [PackageDescriptor(**pkg) for pkg in parsed_pkgs]
        return prev_lockfile_packages

    def get_new_deps(self) -> Packages:
        """Get the new dependencies added to the lockfile and return them."""
        curr_lockfile_packages = self.current_lockfile_packages

        prev_lockfile_object = self.previous_lockfile_object
        if not prev_lockfile_object:
            print(" [+] No previous lockfile object found. Assuming all packages in the current lockfile are new.")
            return curr_lockfile_packages

        prev_lockfile_packages = self.get_previous_lockfile_packages(prev_lockfile_object)

        prev_pkg_set = set(prev_lockfile_packages)
        curr_pkg_set = set(curr_lockfile_packages)
        new_deps = curr_pkg_set.difference(prev_pkg_set)
        print(f" [+] New dependencies: {new_deps}")

        return list(new_deps)

    def init_cli(self) -> None:
        """Check for an existing Phylum CLI install, install it if needed, and set the path class instance variable."""
        specified_version = self.args.version
        # fmt: off
        install_args = [
            "--phylum-release", specified_version,
            "--target", self.args.target,
            "--phylum-token", self.args.token,
        ]
        # fmt: on
        cli_path, cli_version = get_phylum_bin_path()
        if cli_path is None:
            print(f" [+] Existing Phylum CLI instance not found. Installing version `{specified_version}` ...")
            phylum_init(install_args)
        else:
            print(f" [+] Existing Phylum CLI instance found: {cli_version} at {cli_path}")
            if cli_version != specified_version:
                print(f" [+] Existing version {cli_version} does not match the specified version {specified_version}")
                if self.args.force_install:
                    print(f" [*] Installing Phylum CLI version {specified_version} ...")
                    phylum_init(install_args)
                else:
                    print(" [+] Attempting to use existing version ...")
                    if Version(str(cli_version)) < Version(MIN_CLI_VER_INSTALLED):
                        raise SystemExit(f" [!] The existing CLI version must be at least {MIN_CLI_VER_INSTALLED}")
                    print(" [+] Version checks succeeded. Using existing version.")

        cli_path, cli_version = get_phylum_bin_path()
        print(f" [+] Using Phylum CLI instance: {cli_version} at {str(cli_path)}")

        self._cli_path = cli_path

        # Exit condition: a Phylum API key should be in place or available at this point.
        # Ensure stdout is piped to DEVNULL, to keep the token from being printed in (CI log) output.
        cmd = [str(cli_path), "auth", "token"]
        # pylint: disable-next=subprocess-run-check ; we want the return code here and don't want to raise when non-zero
        if bool(subprocess.run(cmd, stdout=subprocess.DEVNULL).returncode):
            raise SystemExit(" [!] A Phylum API key is required to continue.")

    def get_project_url(self, project_id: str) -> str:
        """Construct a project URL from a given project ID and return it.

        The project URL is used to access a particular project in the web UI, by label, and optionally with a group.
        """
        query = {"label": self.phylum_label}
        if self.phylum_group is not None:
            query["group"] = self.phylum_group
        query_params = urllib.parse.urlencode(query, safe="/", quote_via=urllib.parse.quote)
        project_url = f"https://app.phylum.io/projects/{project_id}?{query_params}"
        print(f" [+] Project URL: {project_url}")
        return project_url

    def analyze(self, analysis: dict) -> ReturnCode:
        """Analyze the results gathered from passing a lockfile to `phylum analyze`."""
        if self.args.all_deps:
            print(" [+] Considering all current dependencies ...")
            pkgs = analysis.get("packages", [])
            packages = [PackageDescriptor(pkg.get("name"), pkg.get("version"), pkg.get("type")) for pkg in pkgs]
            print(f" [+] {len(packages)} current dependencies")
            risk_data = self.parse_risk_data(analysis, packages)
        else:
            print(" [+] Only considering newly added dependencies ...")
            packages = self.get_new_deps()
            print(f" [+] {len(packages)} newly added dependencies")
            risk_data = self.parse_risk_data(analysis, packages)

        returncode = ReturnCode.SUCCESS
        output = ""
        if self.gbl_failed and not self.gbl_incomplete:
            print(" [!] The analysis is complete and there were failures")
            returncode = ReturnCode.FAILURE
            output = FAILED_COMMENT
            for line in risk_data:
                output += line

        if self.gbl_incomplete:
            incomplete_pkg_count = len(self.incomplete_pkgs)
            print(f" [+] {incomplete_pkg_count} packages were incomplete in the analysis results")
            if self.gbl_failed:
                print(" [!] There were failures in one or more completed packages")
                returncode = ReturnCode.FAILURE_INCOMPLETE
                output = INCOMPLETE_WITH_FAILURE_COMMENT_TEMPLATE.substitute(count=incomplete_pkg_count)
                for line in risk_data:
                    output += line
            else:
                print(" [+] There were no failures in the packages that have completed so far")
                returncode = ReturnCode.INCOMPLETE
                output = INCOMPLETE_COMMENT_TEMPLATE.substitute(count=incomplete_pkg_count)

        if not self.gbl_failed and not self.gbl_incomplete:
            print(" [+] The analysis is complete and there were NO failures")
            returncode = ReturnCode.SUCCESS
            output = SUCCESS_COMMENT

        project_id = analysis.get("project", "00000000-0000-0000-0000-000000000000")
        project_url = self.get_project_url(project_id)
        output += f"\n[View this project in the Phylum UI]({project_url})"
        self._analysis_output = output

        return returncode

    def parse_risk_data(self, analysis_results: dict, packages: Packages) -> List[str]:
        """Parse risk packages from a Phylum analysis.

        Packages that are in a completed analysis state will be included in the risk score report.
        Packages that have not completed analysis will be included with other incomplete packages
        and the overall PR will be allowed to pass, but with a note about re-running again later.
        """
        analysis_pkgs = analysis_results.get("packages", [])
        project_thresholds = analysis_results.get("thresholds", {})
        risk_scores = []
        for package in packages:
            for phylum_pkg in analysis_pkgs:
                if phylum_pkg.get("name") == package.name and phylum_pkg.get("version") == package.version:
                    if phylum_pkg.get("status") == "complete":
                        risk_score = self.check_risk_scores(phylum_pkg, project_thresholds)
                        if risk_score:
                            risk_scores.append(risk_score)
                    elif phylum_pkg.get("status") == "incomplete":
                        self.incomplete_pkgs.append(package)
                        self.gbl_incomplete = True

        return risk_scores

    def check_risk_scores(self, package_result: dict, project_thresholds: dict) -> Optional[str]:
        """Check risk scores of a package against project or user-provided thresholds.

        Thresholds provided via the corresponding option will take precedence over the project defined threshold value.
        If a package has a risk score below the threshold, set the fail flag and generate the markdown output.
        Return None when the package meets or exceeds all threshold values.
        """
        failed_flag = False
        risk_vectors = package_result.get("riskVectors", {})
        issue_flags = []

        fail_string = f"\n### Package: `{package_result.get('name')}@{package_result.get('version')}` failed.\n"
        fail_string += "|Risk Domain|Identified Score|Requirement|Requirement Source|\n"
        fail_string += "|-----------|----------------|-----------|------------------|\n"

        for threshold_option, risk_domain in PROJECT_THRESHOLD_OPTIONS.items():
            pti = self._get_project_threshold_info(project_thresholds, threshold_option)
            # The `RiskDomain` dataclass and this logic can be simplified once the API standardizes the use of names
            # so that risk domains are referenced with the same name everywhere (e.g., vulnerability/vulnerabilities
            # and malicious_code/malicious)
            vul = None
            potential_names = [risk_domain.package_name, risk_domain.project_name]
            for potential_name in potential_names:
                vul = risk_vectors.get(potential_name)
                if vul is not None:
                    break
            vul = vul if vul is not None else 1.0
            if vul < pti.threshold:
                failed_flag = True
                issue_flags.extend(potential_names)
                fail_string += f"|{risk_domain.output_name}|{vul*100:.0f}|{pti.threshold*100:.0f}|{pti.req_src}|\n"

        fail_string += "\n"
        fail_string += "#### Issues Summary\n"
        fail_string += "|Risk Domain|Risk Level|Title|\n"
        fail_string += "|-----------|----------|-----|\n"

        issue_list = build_issues_list(package_result, issue_flags)
        for domain, severity, title in issue_list:
            fail_string += f"|{domain}|{severity}|{title}|\n"

        if failed_flag:
            self.gbl_failed = True
            return fail_string
        return None

    def _get_project_threshold_info(self, project_thresholds: dict, threshold_type: str) -> ProjectThresholdInfo:
        """Determine the project threshold info in effect for a given threshold type.

        Thresholds for the five risk domains can be set individually in several ways.
        They can be set at the Phylum project level from either the Phylum CLI or the web UI.
        They can be set by `phylum-ci` options (e.g., `--vul-threshold`), which are distinguished by `threshold_type`.
        The default is to use the project level setting unless overridden by a value specified by a `phylum-ci` option.
        A default secure value will be used when neither of these sources are used to set the value.
        """
        threshold = getattr(self.args, threshold_type, None)
        req_src = "phylum-ci option"
        if threshold is None:
            risk_domain: RiskDomain = PROJECT_THRESHOLD_OPTIONS.get(threshold_type, RiskDomain("", "", ""))
            threshold = project_thresholds.get(risk_domain.project_name)
            req_src = "project per-axis threshold"
            if threshold is None:
                threshold = 1.0
                req_src = "N/A (fail safe)"

            total_threshold = project_thresholds.get("total", 0.0)
            if threshold < total_threshold:
                threshold = total_threshold
                req_src = "project total threshold"
        else:
            # The project risk threshold values returned by the analysis are normalized to [0.0, 1.0].
            # They are converted internally like this because it is more natural to ask users for input
            # as an integer in the range of [0, 100].
            threshold /= 100
        pti = ProjectThresholdInfo(threshold=threshold, req_src=req_src)
        return pti


# Type alias
CIEnvs = List[CIBase]


def build_issues_list(package_result: dict, issue_flags: List[str]) -> List[Tuple[str, str, str]]:
    """Build a list of issues from a given package's result object and return it."""
    issues = []
    pkg_issues = package_result.get("issues", [])
    for flag in issue_flags:
        for pkg_issue in pkg_issues:
            if flag == pkg_issue.get("domain"):
                domain = pkg_issue.get("domain")
                severity = pkg_issue.get("severity")
                title = pkg_issue.get("title")
                issues.append((domain, severity, title))
    return issues
