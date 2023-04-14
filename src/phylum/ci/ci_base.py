"""Define a base environment for CI platforms.

The "base" environment is one that makes use of the CLI directly and is not necessarily part of a continuous
integration (CI) environment. Common functionality is provided where possible and CI specific features are
designated as abstract methods to be defined in specific CI environments.
"""
import json
import os
import shlex
import shutil
import subprocess
import tempfile
import textwrap
from abc import ABC, abstractmethod
from argparse import Namespace
from collections import OrderedDict
from functools import cached_property
from pathlib import Path
from typing import List, Optional

import pathspec
from packaging.version import Version
from rich.markdown import Markdown
from ruamel.yaml import YAML

from phylum.ci.common import DataclassJSONEncoder, JobPolicyEvalResult, ReturnCode
from phylum.ci.git import git_hash_object, git_repo_name
from phylum.ci.lockfile import Lockfile, Lockfiles
from phylum.console import console
from phylum.constants import ENVVAR_NAME_TOKEN, MIN_CLI_VER_INSTALLED, SUPPORTED_LOCKFILES
from phylum.init.cli import get_phylum_bin_path
from phylum.init.cli import main as phylum_init


class CIBase(ABC):
    """Provide methods for a basic CI environment."""

    @abstractmethod
    def __init__(self, args: Namespace) -> None:
        """Initialize the base class object.

        Each child class is expected to at least:
          * call `super().__init__(args)`
          * define `self.ci_platform_name`
        """
        self._args = args
        self._all_deps = args.all_deps
        self._force_analysis = args.force_analysis

        # Create a copy of the original `.phylum_project` file values, when the file exists.
        # This is necessary because it is possible that user-provided values for the project and
        # group are given, which causes the file to be overwritten when creating that project.
        self._phylum_project_file = Path.cwd().joinpath(".phylum_project").resolve()
        self._project_file_already_existed = self._phylum_project_file.exists()
        self._project_settings = {}
        if self._project_file_already_existed:
            yaml = YAML()
            self._project_settings = yaml.load(self._phylum_project_file.read_text(encoding="utf-8"))

        # Ensure all pre-requisites are met and bail at the earliest opportunity when they aren't
        self._check_prerequisites()
        print(" [+] All pre-requisites met")

        self._analysis_report = "No analysis output yet"
        self.ci_platform_name = "Unknown"

        # The token option takes precedence over the Phylum API key environment variable.
        token = os.getenv(ENVVAR_NAME_TOKEN)
        if args.token is not None:
            token = args.token
            os.environ[ENVVAR_NAME_TOKEN] = args.token
        self._args.token = token

        self.ensure_project_exists()

    @property
    def args(self) -> Namespace:
        """Get the namespace arguments provided on the command line."""
        return self._args

    @cached_property
    def lockfiles(self) -> Lockfiles:
        """Get the package lockfile(s) in lexicographic order.

        The package lockfile(s) can be specified as an option or contained in the `.phylum_project` file.
        Lockfiles provided as an input option will be preferred over any entries in the `.phylum_project` file.

        When no valid lockfiles are provided otherwise, an attempt will be made to automatically detect them.
        """
        arg_lockfiles: Optional[List[List[Path]]] = self.args.lockfile
        if arg_lockfiles:
            # flatten the list of lists
            provided_arg_lockfiles = [path for sub_list in arg_lockfiles for path in sub_list]
            print(f" [+] Lockfile(s) provided as arguments: {provided_arg_lockfiles}")
            valid_lockfiles = self.filter_lockfiles(provided_arg_lockfiles)
            if valid_lockfiles:
                print(f" [-] Valid provided lockfiles: {valid_lockfiles}")
                return valid_lockfiles

        print(" [+] No valid lockfiles were provided as arguments. Checking the `.phylum_project` file ...")
        lockfile_entries: List[OrderedDict] = self._project_settings.get("lockfiles", [])
        lockfile_paths = [lockfile_entry.get("path") for lockfile_entry in lockfile_entries]
        provided_project_lockfiles = [Path(lockfile) for lockfile in lockfile_paths if lockfile]
        if provided_project_lockfiles:
            print(f" [+] Lockfile(s) provided in `.phylum_project` file: {provided_project_lockfiles}")
            valid_lockfiles = self.filter_lockfiles(provided_project_lockfiles)
            if valid_lockfiles:
                print(f" [-] Valid provided lockfiles: {valid_lockfiles}")
                return valid_lockfiles

        print(" [+] No valid lockfiles in the `.phylum_project` file. An attempt will be made to detect lockfiles.")
        detected_lockfiles = detect_lockfiles()
        if detected_lockfiles:
            print(f" [+] Detected lockfile(s): {detected_lockfiles}")
            valid_lockfiles = self.filter_lockfiles(detected_lockfiles)
            if valid_lockfiles:
                print(f" [-] Valid detected lockfiles: {valid_lockfiles}")
                return valid_lockfiles

        raise SystemExit(" [!] No valid lockfiles were detected. Consider specifying at least one with `--lockfile`.")

    def filter_lockfiles(self, provided_lockfiles: List[Path]) -> Lockfiles:
        """Filter potential lockfiles and return the valid ones in sorted order."""
        lockfiles = []
        for provided_lockfile in provided_lockfiles:
            if not provided_lockfile.exists():
                raise SystemExit(f" [!] Provided lockfile does not exist: {provided_lockfile}")
            if not provided_lockfile.stat().st_size:
                print(f" [!] Provided lockfile is an empty file: {provided_lockfile}")
                continue
            cmd = [str(self.cli_path), "parse", str(provided_lockfile)]
            # stdout and stderr are piped to DEVNULL because we only care about the return code.
            # pylint: disable-next=subprocess-run-check ; we want return code here and don't want to raise when non-zero
            if bool(subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode):
                print(f" [!] Provided lockfile failed to parse as a known lockfile type: {provided_lockfile}")
                continue
            lockfiles.append(Lockfile(provided_lockfile, self.cli_path, self.common_ancestor_commit))
        return sorted(lockfiles)

    @property
    def all_deps(self) -> bool:
        """Get the status of analyzing all dependencies."""
        return self._all_deps

    @property
    def force_analysis(self) -> bool:
        """Get the status of forcing an analysis."""
        return self._force_analysis

    @cached_property
    def phylum_project(self) -> str:
        """Get the effective Phylum project name in use.

        The Phylum project name can be specified as an option or contained in the `.phylum_project` file.
        A project name provided as an input option will be preferred over an entry in the `.phylum_project` file.

        When no project name is provided through options or project file, a project name will be provided by detecting
        the git repository name. The goal is a unique and deterministic project name for each git repository submitted
        by the same Phylum user account.
        """
        project_name = self.args.project
        if project_name:
            print(f" [+] Project name provided as argument: {project_name}")
            return project_name

        print(" [+] Project name not provided as argument. Checking the `.phylum_project` file ...")
        project_name = self._project_settings.get("name")
        if project_name:
            print(f" [+] Project name provided in `.phylum_project` file: {project_name}")
            return project_name

        print(" [+] Project name not found in the `.phylum_project` file or file does not exist. Detecting instead ...")
        project_name = git_repo_name()
        print(f" [+] Project name detected from git repository name: {project_name}")
        return project_name

    @property
    def phylum_group(self) -> Optional[str]:
        """Get the effective Phylum group in use.

        The Phylum group name can be specified as an option or contained in the `.phylum_project` file.
        A group name provided as an input option will be preferred over an entry in the `.phylum_project` file.

        Return `None` when the group name is not available.
        """
        # Group supplied on command-line
        # A group can not be specified without a project
        if self.args.group and self.args.project:
            return self.args.group

        # Group supplied in `.phylum_project`
        # Don't "mix" a project supplied as an option with a group that wasn't
        if not self.args.project:
            return self._project_settings.get("group_name")

        return None

    @cached_property
    def cli_path(self) -> Path:
        """Get the path to the Phylum CLI binary.

        Check for an existing Phylum CLI and install it if needed.
        """
        specified_version = self.args.version
        # fmt: off
        install_args = [
            "--phylum-release", specified_version,
            "--target", self.args.target,
            "--phylum-token", self.args.token,
            "--api-uri", self.args.uri,
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
        if cli_path is None:
            raise SystemExit(" [!] Failed to initialize the Phylum CLI")

        # Exit condition: a Phylum API key should be in place or available at this point.
        # Ensure stdout is piped to DEVNULL, to keep the token from being printed in (CI log) output.
        cmd = [str(cli_path), "auth", "token"]
        # pylint: disable-next=subprocess-run-check ; we want the return code here and don't want to raise when non-zero
        if bool(subprocess.run(cmd, stdout=subprocess.DEVNULL).returncode):
            raise SystemExit(" [!] A Phylum API key is required to continue.")

        print(f" [+] Using Phylum CLI instance: {cli_version} at {cli_path}")
        return cli_path

    @property
    def analysis_report(self) -> str:
        """Get the report from the overall analysis, in markdown format."""
        return self._analysis_report

    @property
    @abstractmethod
    def phylum_label(self) -> str:
        """Get a custom label for use when submitting jobs with `phylum analyze`.

        Each CI platform/environment has unique ways of referencing events, PRs, branches, etc.
        However, each implementation is expected to at least:
          * Start the label with the `self.ci_platform_name`
          * Replace all runs of whitespace characters with a single `-` character
        """
        raise NotImplementedError()

    @property
    def lockfile_hash_object(self) -> str:
        """Get the lockfile hash object of the first changed lockfile and return it.

        Since there can be many changed lockfiles, find and use only the hash object of the first changed lockfile.
        Since it is possible that no lockfile has changed (e.g., when forcing analysis), default to first lockfile.
        When found, only the first seven characters of the hash object will be returned, which is a git "short SHA-1".
        Reference: https://git-scm.com/book/en/v2/Git-Tools-Revision-Selection
        """
        if not self.lockfiles:
            return "unknown"
        first_changed_lockfile = self.lockfiles[0]
        for lockfile in self.lockfiles:
            if lockfile.is_lockfile_changed:
                first_changed_lockfile = lockfile
                break
        lockfile_hash_object = git_hash_object(first_changed_lockfile.path)
        return lockfile_hash_object[:7]

    @cached_property
    @abstractmethod
    def common_ancestor_commit(self) -> Optional[str]:
        """Find the common ancestor commit.

        When found, it should be returned as a string of the SHA1 sum representing the commit.
        When it can't be found (or there is an error), `None` should be returned.
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def is_any_lockfile_changed(self) -> bool:
        """Get the lockfiles' collective modification status.

        Implementations should return `True` if any lockfile has changed and `False` otherwise.
        """
        raise NotImplementedError()

    def update_lockfiles_change_status(self, commit: str, err_msg: Optional[str] = None) -> None:
        """Update each lockfile's change status.

        The input `commit` is the one to use in a `git diff` command to view the changes relative to the working tree.
        The input `err_msg` is what will be printed when `git diff` fails. This is usually due to not having enough
        branch history...which can happen with shallow clones.
        """
        for lockfile in self.lockfiles:
            print(f" [*] Checking `{lockfile!r}` for changes ...")
            # `--exit-code` will make git exit with 1 if there were differences while 0 means no differences.
            # Any other exit code is an error and a reason to re-raise.
            cmd = ["git", "diff", "--exit-code", "--quiet", commit, "--", str(lockfile.path)]
            ret = subprocess.run(cmd, check=False)
            if ret.returncode == 0:
                print(f" [-] The lockfile `{lockfile!r}` has not changed")
                lockfile.is_lockfile_changed = False
            elif ret.returncode == 1:
                print(f" [-] The lockfile `{lockfile!r}` has changed")
                lockfile.is_lockfile_changed = True
            else:
                if err_msg:
                    print(textwrap.dedent(err_msg))
                ret.check_returncode()

    @abstractmethod
    def _check_prerequisites(self) -> None:
        """Ensure the necessary pre-requisites are met and bail when they aren't.

        The current pre-requisites for *all* CI environments/platforms are:
          * A Phylum CLI version with ability to specify multiple lockfiles
          * Have `git` installed and available for use on the PATH
        """
        print(" [+] Confirming pre-requisites ...")

        if Version(self.args.version) < Version(MIN_CLI_VER_INSTALLED):
            raise SystemExit(f" [!] The CLI version must be at least {MIN_CLI_VER_INSTALLED}")

        if shutil.which("git"):
            print(" [+] `git` binary found on the PATH")
        else:
            raise SystemExit(" [!] `git` is required to be installed and available on the PATH")

    def ensure_project_exists(self) -> None:
        """Ensure a Phylum project is created and in place.

        A project may or may not already exist. Attempt to create the project, possibly overwriting a `.phylum_project`
        file that already exists. Continue on without error when the specified project already exists.
        """
        print(f" [*] Attempting to create a Phylum project with the name: {self.phylum_project} ...")
        cmd = [str(self.cli_path), "project", "create", self.phylum_project]
        if self.phylum_group:
            print(f" [-] Using Phylum group: {self.phylum_group}")
            cmd = [str(self.cli_path), "project", "create", "--group", self.phylum_group, self.phylum_project]
        ret = subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # The Phylum CLI will return a unique error code of 14 when a project that already
        # exists is attempted to be created. This situation is recognized and allowed to happen
        # since it means the project exists as expected. Any other exit code is an error.
        if ret.returncode == 0:
            print(f" [-] Project {self.phylum_project} created successfully.")
            if self._project_file_already_existed:
                print(f" [!] Overwrote previous `.phylum_project` file found at: {self._phylum_project_file}")
        elif ret.returncode == 14:
            print(f" [-] Project {self.phylum_project} already exists. Continuing with it ...")
        else:
            print(f" [!] There was a problem creating the project with command: {shlex.join(cmd)}")
            ret.check_returncode()

    def post_output(self) -> None:
        """Post the output of the analysis as markdown rendered for output to the terminal/logs.

        Each implementation that offers analysis output in the form of comments on a pull/merge request should
        ensure those comments are unique and not added multiple times as the review changes but no lockfile does.
        """
        # Post the markdown output, rendered for terminal/log output
        print(" [+] Analysis output:\n")
        report_md = Markdown(self.analysis_report, hyperlinks=False)
        console.print(report_md, soft_wrap=True)

    def analyze(self) -> ReturnCode:
        """Analyze the results gathered from passing the lockfile(s) to `phylum analyze`."""
        # Build up the analyze command based on the provided inputs
        cmd = [str(self.cli_path), "analyze", "--label", self.phylum_label, "--project", self.phylum_project]
        if self.phylum_group:
            cmd.extend(["--group", self.phylum_group])
        cmd.extend(["--verbose", "--json"])

        if self.all_deps:
            print(" [+] Considering all current dependencies ...")
            base_pkgs = []
            total_packages = {pkg for lockfile in self.lockfiles for pkg in lockfile.current_lockfile_packages()}
            print(f" [+] {len(total_packages)} unique current dependencies")
        else:
            print(" [+] Only considering newly added dependencies ...")
            # When the `--force-analysis` flag is specified without the `--all-deps` flag, it is necessary
            # to ensure the `is_lockfile_changed` property is set for each lockfile. Simply referencing
            # the `is_any_lockfile_changed` property will ensure this happens.
            if self.force_analysis and self.is_any_lockfile_changed:
                print(" [-] Updated each lockfile's change status")
            base_pkgs = sorted({pkg for lockfile in self.lockfiles for pkg in lockfile.base_deps})
            new_packages = sorted({pkg for lockfile in self.lockfiles for pkg in lockfile.new_deps})
            print(f" [+] {len(new_packages)} unique newly added dependencies")

        with tempfile.NamedTemporaryFile(mode="w+", prefix="base_", suffix=".json") as base_fd:
            json.dump(base_pkgs, base_fd, cls=DataclassJSONEncoder)
            base_fd.flush()

            cmd.extend(["--base", base_fd.name])
            cmd.extend(str(lockfile.path) for lockfile in self.lockfiles)

            print(f" [*] Performing analysis with command: {shlex.join(cmd)}")
            try:
                analysis_result = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
            except subprocess.CalledProcessError as err:
                # The Phylum project will fail analysis if the configured policy criteria are not met.
                # This causes the return code to be 100 and lands us here. Check for this case to proceed.
                if err.returncode == 100:
                    analysis_result = err.stdout
                else:
                    print(f" [!] stdout:\n{err.stdout}")
                    print(f" [!] stderr:\n{err.stderr}")
                    raise SystemExit(f" [!] {err}") from err

        analysis = JobPolicyEvalResult(**json.loads(analysis_result))
        self._analysis_report = analysis.report

        returncode = ReturnCode.SUCCESS
        # The logic below would make for a good match statement, which was introduced in Python 3.10
        if analysis.incomplete_count == 0:
            if analysis.is_failure:
                print(" [!] The analysis is complete and there were failures")
                returncode = ReturnCode.FAILURE
            else:
                print(" [+] The analysis is complete and there were NO failures")
                returncode = ReturnCode.SUCCESS
        else:
            if analysis.is_failure:
                print(" [!] There were failures in one or more completed packages")
                returncode = ReturnCode.FAILURE_INCOMPLETE
            else:
                print(" [+] There were no failures in the packages that have completed so far")
                returncode = ReturnCode.INCOMPLETE

        return returncode


# Type alias
CIEnvs = List[CIBase]


def detect_lockfiles() -> List[Path]:
    """Detect the lockfile(s) in use and return them.

    Lockfiles that match entries in supported ignore files will be excluded.

    This function makes the following assumptions:
      * It is called from the root of a repository
      * Ignore files only exist at the root of a repository
      * Recursing fully into the repository is acceptable
    """
    cwd = Path.cwd()
    spec = None
    potential_ignore_files = (Path(".gitignore"), Path(".ignore"))

    ignore_files = [f.resolve() for f in potential_ignore_files if f.exists()]
    if ignore_files:
        try:
            lines = [line for ignore_file in ignore_files for line in ignore_file.read_text("utf-8").splitlines()]
            spec = pathspec.PathSpec.from_lines("gitwildmatch", lines)
        except (UnicodeDecodeError, pathspec.patterns.gitwildmatch.GitWildMatchPatternError) as err:
            # Ignore the failure and proceed without ignore-file filtering (how ironic)
            print(f" [!] Could not parse an ignore file: {err}")
            print(" [-] Continuing anyway ...")

    lockfiles = [path.resolve() for lockfile_glob in SUPPORTED_LOCKFILES for path in cwd.glob(f"**/{lockfile_glob}")]
    if spec:
        lockfiles = [path for path in lockfiles if not spec.match_file(str(path))]
    return lockfiles
