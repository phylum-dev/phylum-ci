"""Define a base environment for CI platforms.

The "base" environment is one that makes use of the CLI directly and is not necessarily part of a continuous
integration (CI) environment. Common functionality is provided where possible and CI specific features are
designated as abstract methods to be defined in specific CI environments.
"""

from abc import ABC, abstractmethod
from argparse import Namespace
from collections import OrderedDict
from collections.abc import Mapping
from functools import cached_property, lru_cache
from inspect import cleandoc
from itertools import starmap
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
from typing import Optional

from packaging.version import Version
from rich.markdown import Markdown

from phylum.ci.common import (
    CLIExitCode,
    DataclassJSONEncoder,
    DepfileEntries,
    DepfileEntry,
    JobPolicyEvalResult,
    Package,
    Packages,
    ReturnCode,
)
from phylum.ci.depfile import Depfile, Depfiles, DepfileType, parse_depfile
from phylum.ci.git import git_hash_object, git_repo_name, git_worktree
from phylum.console import console
from phylum.constants import ENVVAR_NAME_TOKEN, MIN_CLI_VER_INSTALLED
from phylum.exceptions import PhylumCalledProcessError, pprint_subprocess_error
from phylum.exts.ci import CI_EXT_PATH
from phylum.init.cli import get_phylum_bin_path
from phylum.init.cli import main as phylum_init
from phylum.logger import LOG, MARKUP, progress_spinner


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
        self._returncode = ReturnCode.SUCCESS
        self._analysis_report = "No analysis output yet"
        self._env: Optional[Mapping[str, str]] = None
        self.ci_platform_name = "Unknown"
        self.disable_lockfile_generation = False

        # Disable comments when in audit mode
        self.audit_mode = args.audit
        self._skip_comments = True if self.audit_mode else args.skip_comments

        # Ensure all prerequisites are met and bail at the earliest opportunity when they aren't
        self._check_prerequisites()
        LOG.info("All prerequisites met")

        self._backup_project_file()

        # The token option takes precedence over the Phylum API key environment variable.
        token = os.getenv(ENVVAR_NAME_TOKEN)
        if args.token is not None:
            token = args.token
            os.environ[ENVVAR_NAME_TOKEN] = args.token
        self._args.token = token

        self._find_potential_depfiles()
        self._ensure_project_exists()

    @lru_cache(maxsize=1)
    def _backup_project_file(self) -> None:
        """Create a copy of the original `.phylum_project` file values, when the file exists.

        This is necessary because it is possible that user-provided values for the project and
        group are given, which causes the file to be overwritten when creating that project.
        """
        cmd = [str(self.cli_path), "status", "--json"]
        try:
            status_output = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603
        except subprocess.CalledProcessError as err:
            msg = "Phylum status check failed"
            raise PhylumCalledProcessError(err, msg) from err
        self._project_settings: dict = json.loads(status_output)
        project_root = self._project_settings.get("root")
        if project_root:
            self._phylum_project_file = Path(project_root).joinpath(".phylum_project").resolve()
        else:
            self._phylum_project_file = Path.cwd().joinpath(".phylum_project").resolve()
        self._project_file_already_existed = self._phylum_project_file.exists()

    @property
    def args(self) -> Namespace:
        """Get the namespace arguments provided on the command line."""
        return self._args

    @property
    def returncode(self) -> ReturnCode:
        """Get the current return code."""
        return self._returncode

    @returncode.setter
    def returncode(self, value: ReturnCode) -> None:
        """Set the return code value."""
        # Do not allow setting a `SUCCESS` value once the return code has already been set to an error value.
        if self._returncode == ReturnCode.SUCCESS or value != ReturnCode.SUCCESS:
            self._returncode = value

    def _find_potential_depfiles(self) -> None:
        """Find all the lockfiles and manifests at the current directory or below."""
        cmd = [str(self.cli_path), "find-dependency-files"]
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603
        except subprocess.CalledProcessError as err:
            msg = "Phylum `find-dependency-files` command failed"
            raise PhylumCalledProcessError(err, msg) from err
        lockable_files: dict = json.loads(result)
        self._potential_manifests: DepfileEntries = list(starmap(DepfileEntry, lockable_files.get("manifests", [])))
        self._potential_lockfiles: DepfileEntries = list(starmap(DepfileEntry, lockable_files.get("lockfiles", [])))

    @cached_property
    def depfiles(self) -> Depfiles:
        """Get the package dependency file(s) in lexicographic order.

        The package dependency file(s) can be specified as an option or contained in the `.phylum_project` file.
        Dependency files provided as an input option will be preferred over any entries in the `.phylum_project` file.

        When no valid dependency files are provided otherwise, an attempt will be made to automatically detect them.
        """
        arg_depfiles: Optional[list[list[Path]]] = self.args.depfile
        provided_arg_depfiles: DepfileEntries = []
        if arg_depfiles:
            # flatten the list of lists
            provided_arg_depfiles = [DepfileEntry(path) for sub_list in arg_depfiles for path in sub_list]
            LOG.debug("Dependency files provided as arguments: %s", provided_arg_depfiles)
            valid_depfiles = self._filter_depfiles(provided_arg_depfiles)
            if valid_depfiles:
                LOG.debug("Valid provided dependency files: %s", valid_depfiles)
                return valid_depfiles

        LOG.info("No valid dependency files were provided as arguments. An attempt will be made to detect them.")
        depfile_entries: list[OrderedDict] = self._project_settings.get("dependency_files", [])
        detected_depfiles = [DepfileEntry(lfe.get("path", ""), lfe.get("type", "auto")) for lfe in depfile_entries]
        if depfile_entries and self._project_settings.get("root"):
            LOG.debug("Dependency files provided in `.phylum_project` file: %s", detected_depfiles)
        else:
            LOG.debug("Detected dependency files: %s", detected_depfiles)
        if arg_depfiles:
            # Ensure any depfiles provided as arguments that were already filtered out are not included again here
            detected_depfiles = list(set(detected_depfiles).difference(set(provided_arg_depfiles)))
            LOG.debug("Unique new dependency files: %s", detected_depfiles)
        if detected_depfiles:
            valid_depfiles = self._filter_depfiles(detected_depfiles)
            if valid_depfiles:
                LOG.debug("Valid detected dependency files: %s", valid_depfiles)
                return valid_depfiles

        msg = """
            No valid dependency files were detected.
            Consider specifying at least one with
            `--depfile` argument or in `.phylum_project` file."""
        LOG.error(cleandoc(msg))
        if not self.returncode:
            self.returncode = ReturnCode.NO_DEPFILES_PROVIDED
        raise SystemExit(self.returncode)

    @progress_spinner("Filtering dependency files")
    def _filter_depfiles(self, provided_depfiles: DepfileEntries) -> Depfiles:
        """Filter potential dependency files and return the valid ones in sorted order."""
        depfiles: Depfiles = []
        for provided_depfile in provided_depfiles:
            # Make sure it exists
            if not provided_depfile.path.exists():
                LOG.warning("Provided dependency file does not exist: %r", provided_depfile)
                self.returncode = ReturnCode.DEPFILE_FILTER
                continue

            # Make sure it is not an empty file
            if not provided_depfile.path.stat().st_size:
                LOG.warning("Provided dependency file is an empty file: %r", provided_depfile)
                self.returncode = ReturnCode.DEPFILE_FILTER
                continue

            # Make sure it can be parsed by Phylum CLI
            try:
                _ = parse_depfile(
                    self.cli_path,
                    provided_depfile.type,
                    provided_depfile.path,
                    disable_lockfile_generation=self.disable_lockfile_generation,
                )
            except subprocess.CalledProcessError as err:
                pprint_subprocess_error(err)
                # The Phylum CLI will return a unique error code when a manifest is attempted to be parsed but
                # lockfile generation has been disabled. This situation is recognized with a distinct return code
                # to signal that a manifest may have new resolved dependencies that have not been analyzed by Phylum.
                if err.returncode == CLIExitCode.MANIFEST_WITHOUT_GENERATION.value:
                    msg = f"""
                        Provided manifest [code]{provided_depfile!r}[/] requires lockfile
                        generation to parse but it was disabled to prevent running arbitrary
                        code in untrusted contexts, like PRs from forks. The resolved
                        dependencies from the manifest have NOT been analyzed by Phylum. Care
                        should be taken to inspect changes manually before allowing a manifest
                        to be used in a trusted context. For Phylum analysis, consider adding
                        a lockfile instead of or along with the manifest, even for libraries."""
                    self.returncode = ReturnCode.MANIFEST_WITHOUT_GENERATION
                else:
                    msg = f"""
                        Provided dependency file [code]{provided_depfile!r}[/] failed to parse
                        as type [code]{provided_depfile.type}[/]. If this is a manifest, consider
                        supplying dependency file type explicitly in `.phylum_project` file.
                        For more info, see: https://docs.phylum.io/cli/lockfile_generation
                        Please report this as a bug if you believe [code]{provided_depfile!r}[/]
                        is a valid [code]{provided_depfile.type}[/] dependency file."""
                    self.returncode = ReturnCode.DEPFILE_FILTER
                LOG.warning(cleandoc(msg), extra=MARKUP)
                continue

            # Classify the file as a manifest or lockfile
            if provided_depfile in self._potential_manifests and provided_depfile in self._potential_lockfiles:
                msg = f"""
                    Provided dependency file [code]{provided_depfile!r}[/] is a [b]lockifest[/].
                    It will be treated as a [b]manifest[/].
                    For more info, see: https://docs.phylum.io/cli/lockfile_generation"""
                LOG.warning(cleandoc(msg), extra=MARKUP)
                depfile = Depfile(
                    provided_depfile,
                    self.cli_path,
                    DepfileType.LOCKIFEST,
                    disable_lockfile_generation=self.disable_lockfile_generation,
                )
            elif provided_depfile in self._potential_manifests:
                LOG.info("Provided dependency file [code]%r[/] is a [b]manifest[/]", provided_depfile, extra=MARKUP)
                depfile = Depfile(
                    provided_depfile,
                    self.cli_path,
                    DepfileType.MANIFEST,
                    disable_lockfile_generation=self.disable_lockfile_generation,
                )
            elif provided_depfile in self._potential_lockfiles:
                LOG.info("Provided dependency file [code]%r[/] is a [b]lockfile[/]", provided_depfile, extra=MARKUP)
                depfile = Depfile(
                    provided_depfile,
                    self.cli_path,
                    DepfileType.LOCKFILE,
                    disable_lockfile_generation=self.disable_lockfile_generation,
                )
            else:
                msg = f"""
                    Provided dependency file [code]{provided_depfile!r}[/] is an [b]unknown[/] type.
                    It will be treated as a [b]manifest[/]."""
                LOG.warning(cleandoc(msg), extra=MARKUP)
                depfile = Depfile(
                    provided_depfile,
                    self.cli_path,
                    DepfileType.UNKNOWN,
                    disable_lockfile_generation=self.disable_lockfile_generation,
                )
            depfiles.append(depfile)

        # Check for the presence of a manifest file
        if any(depfile.is_manifest for depfile in depfiles):
            msg = """
                At least one manifest file was included.
                Forcing analysis to ensure updated dependencies are included."""
            LOG.warning(cleandoc(msg))
            self._force_analysis = True

        return sorted(depfiles)

    @property
    def all_deps(self) -> bool:
        """Get the status of analyzing all dependencies."""
        return self._all_deps

    @property
    def force_analysis(self) -> bool:
        """Get the status of forcing an analysis."""
        return self._force_analysis

    @property
    def skip_comments(self) -> bool:
        """Get the status of skipping comments."""
        return self._skip_comments

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
            LOG.debug("Project name provided as argument: %s", project_name)
            return project_name

        LOG.info("Project name not provided as argument. Checking the `.phylum_project` file ...")
        project_name = self._project_settings.get("project")
        if project_name:
            LOG.debug("Project name provided in `.phylum_project` file: %s", project_name)
            return project_name

        LOG.info("Project name not found in the `.phylum_project` file or file does not exist. Detecting instead ...")
        project_name = git_repo_name()
        LOG.debug("Project name detected from git repository name: %s", project_name)
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
            return self._project_settings.get("group")

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
            LOG.warning("Existing Phylum CLI instance not found. Installing version `%s` ...", specified_version)
            phylum_init(install_args)
        else:
            LOG.debug("Existing Phylum CLI instance found: %s at %s", cli_version, cli_path)
            if cli_version != specified_version:
                LOG.warning("Existing version %s does not match specified version %s", cli_version, specified_version)
                if self.args.force_install:
                    LOG.warning("Forced install option given. Installing Phylum CLI version %s ...", specified_version)
                    phylum_init(install_args)
                else:
                    LOG.debug("Attempting to use existing version ...")
                    if Version(str(cli_version)) < Version(MIN_CLI_VER_INSTALLED):
                        msg = f"The existing CLI version must be at least {MIN_CLI_VER_INSTALLED}"
                        raise SystemExit(msg)
                    LOG.info("Version checks succeeded. Using existing version.")

        cli_path, cli_version = get_phylum_bin_path()
        if cli_path is None:
            msg = "Failed to initialize the Phylum CLI"
            raise SystemExit(msg)

        # Exit condition: a Phylum API key should be in place or available at this point.
        # Ensure stdout is piped to DEVNULL, to keep the token from being printed in (CI log) output.
        # We want the return code here and don't want to raise when non-zero.
        cmd = [str(cli_path), "auth", "token"]
        if bool(subprocess.run(cmd, stdout=subprocess.DEVNULL, check=False).returncode):  # noqa: S603
            msg = "A Phylum API key is required to continue."
            raise SystemExit(msg)

        LOG.info("Using Phylum CLI instance: %s at %s", cli_version, cli_path)
        return cli_path

    @property
    def analysis_report(self) -> str:
        """Get the report from the overall analysis, in markdown format."""
        return self._analysis_report

    @cached_property
    @abstractmethod
    def phylum_label(self) -> str:
        """Get a custom label for use when submitting jobs for analysis.

        Each CI platform/environment has unique ways of referencing events, PRs, branches, etc.
        However, each implementation is expected to at least:
          * Start the label with the `self.ci_platform_name`
          * Replace all runs of whitespace characters with a single `-` character
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def repo_url(self) -> Optional[str]:
        """Get the repository URL for reference in Phylum project metadata.

        The value should only exist for implementations that make use of a web hosted CI environment. The local use
        cases should not set this value. The expected format of the repository URL is the "URL of the web UI for the
        project root." This is not the URL to clone the repository.

        `None` should be returned when the repository URL can't be found, shouldn't be set, or there is an error.
        """
        raise NotImplementedError

    @property
    def depfile_hash_object(self) -> str:
        """Get the dependency file hash object of the first changed dependency file and return it.

        Since there can be many changed dependency files, find and use only the hash object of the
        first changed dependency file. Since it is possible that no dependency file has changed
        (e.g., when forcing analysis), default to first dependency file. When found, only the first
        seven characters of the hash object will be returned, which is a git "short SHA-1".
        Reference: https://git-scm.com/book/en/v2/Git-Tools-Revision-Selection
        """
        if not self.depfiles:
            return "unknown"
        first_changed_depfile = self.depfiles[0]
        for depfile in self.depfiles:
            if depfile.is_depfile_changed:
                first_changed_depfile = depfile
                break
        depfile_hash_object = git_hash_object(first_changed_depfile.path)
        return depfile_hash_object[:7]

    @cached_property
    @abstractmethod
    def common_ancestor_commit(self) -> Optional[str]:
        """Find the common ancestor commit.

        When found, it should be returned as a string of the SHA1 sum representing the commit.
        When it can't be found (or there is an error), `None` should be returned.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def is_any_depfile_changed(self) -> bool:
        """Get the dependency files' collective modification status.

        Implementations should return `True` if any dependency file has changed and `False` otherwise.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def phylum_comment_exists(self) -> bool:
        """Predicate for detecting whether a Phylum-generated comment exists.

        Implementations should return `True` if an existing Phylum-generated comment exists and `False` otherwise.
        """
        raise NotImplementedError

    def update_depfiles_change_status(self, commit: str, err_msg: Optional[str] = None) -> None:
        """Update each dependency file's change status.

        The input `commit` is the one to use in a `git diff` command to view the changes relative to the working tree.
        The input `err_msg` is what will be printed when `git diff` fails. This is usually due to not having enough
        branch history...which can happen with shallow clones.
        """
        for depfile in self.depfiles:
            LOG.debug("Checking [code]%r[/] for changes ...", depfile, extra=MARKUP)
            # `--exit-code` will make git exit with 1 if there were differences while 0 means no differences.
            # Any other exit code is an error and a reason to re-raise.
            cmd = ["git", "diff", "--exit-code", "--quiet", commit, "--", str(depfile.path)]
            ret = subprocess.run(cmd, check=False)  # noqa: S603
            if ret.returncode == 0:
                LOG.debug("The dependency file [code]%r[/] has [b]NOT[/] changed", depfile, extra=MARKUP)
                depfile.is_depfile_changed = False
            elif ret.returncode == 1:
                LOG.debug("The dependency file [code]%r[/] has changed", depfile, extra=MARKUP)
                depfile.is_depfile_changed = True
            else:
                if err_msg:
                    LOG.error("%s", cleandoc(err_msg))
                ret.check_returncode()

    @abstractmethod
    def _check_prerequisites(self) -> None:
        """Ensure the necessary prerequisites are met and bail when they aren't.

        The current prerequisites for *all* CI environments/platforms are:
          * A Phylum CLI version at least as new as the minimum supported version
          * Have `git` installed and available for use on the PATH
        """
        LOG.info("Confirming prerequisites ...")

        if Version(self.args.version) < Version(MIN_CLI_VER_INSTALLED):
            msg = f"The CLI version must be at least {MIN_CLI_VER_INSTALLED}"
            raise SystemExit(msg)

        if shutil.which("git"):
            LOG.debug("`git` binary found on the PATH")
        else:
            msg = "`git` is required to be installed and available on the PATH"
            raise SystemExit(msg)

    @progress_spinner("Ensuring a Phylum project exists")
    def _ensure_project_exists(self) -> None:
        """Ensure a Phylum project is created and in place.

        A project may or may not already exist. Attempt to create the project, possibly overwriting a `.phylum_project`
        file that already exists. Continue on without error when the specified project already exists.
        """
        LOG.info("Attempting to create a Phylum project with the name: %s ...", self.phylum_project)
        cmd = [str(self.cli_path), "project", "create"]
        if self.phylum_group:
            LOG.debug("Using Phylum group: %s", self.phylum_group)
            cmd.extend(["--group", self.phylum_group])
        if self.repo_url:
            LOG.debug("Using repository URL: %s", self.repo_url)
            cmd.extend(["--repository-url", self.repo_url])
        cmd.append(self.phylum_project)
        if not Path.cwd().joinpath(".git").is_dir():
            LOG.warning("Attempting to create a Phylum project outside the top level of a `git` repository")
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)  # noqa: S603
        except subprocess.CalledProcessError as err:
            # The Phylum CLI will return a unique error code when a project that already
            # exists is attempted to be created. This situation is recognized and allowed to happen
            # since it means the project exists as expected. Any other exit code is an error.
            if err.returncode == CLIExitCode.PROJECT_ALREADY_EXISTS.value:
                LOG.info("Project %s already exists. Continuing with it ...", self.phylum_project)
                self._set_repo_url()
                return
            msg = """
                There was a problem creating the project.
                A PRO account is needed to create a project with a group.
                If the command was expected to succeed, please report this as a bug."""
            raise PhylumCalledProcessError(err, cleandoc(msg)) from err
        LOG.info("Project %s created successfully", self.phylum_project)
        if self._project_file_already_existed:
            LOG.warning("Overwrote previous `.phylum_project` file found at: %s", self._phylum_project_file)

    def _set_repo_url(self) -> None:
        """Set the repository URL for the project.

        The value is meant to be the Web UI URL for where the project is hosted.
        It should not be set or changed if a value already exists.
        """
        if self.repo_url is None:
            LOG.debug("Repository URL not available to set")
            return

        LOG.info("Checking project for existing repository URL ...")
        cmd = [str(self.cli_path), "project", "status", "--project", self.phylum_project, "--json"]
        if self.phylum_group:
            LOG.debug("Using Phylum group: %s", self.phylum_group)
            cmd.extend(["--group", self.phylum_group])
        try:
            cmd_output = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603
        except subprocess.CalledProcessError as err:
            pprint_subprocess_error(err)
            msg = """
                Phylum project status failed. Skipping repository URL check.
                Use CLI to manually set it:
                https://docs.phylum.io/cli/commands/phylum_project_update"""
            LOG.warning(cleandoc(msg))
            return
        project_status: dict = json.loads(cmd_output)
        project_id = project_status.get("id")
        repo_url = project_status.get("repository_url")
        if not project_id:
            msg = """
                Could not find the project ID. Skipping repository URL check.
                Use CLI to manually set it:
                https://docs.phylum.io/cli/commands/phylum_project_update"""
            LOG.warning(cleandoc(msg))
            return
        LOG.debug("Found project ID: %s", project_id)

        if repo_url is not None:
            LOG.info("Repository URL already set: %s", repo_url)
            if repo_url != self.repo_url:
                msg = f"""
                    Repository URL differs from what would be set! Keeping existing value.
                    Existing: {repo_url}
                    Proposed: {self.repo_url}
                    To override: https://docs.phylum.io/cli/commands/phylum_project_update"""
                LOG.warning(cleandoc(msg))
                return
            LOG.info("Repository URL matches what would be set. Nothing to do.")
            return

        LOG.info("Repository URL not set. Setting it to: %s", self.repo_url)
        cmd = [str(self.cli_path), "project", "update", "--project-id", project_id, "--repository-url", self.repo_url]
        if self.phylum_group:
            cmd.extend(["--group", self.phylum_group])
        LOG.debug("Using command: %s", shlex.join(cmd))
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)  # noqa: S603
        except subprocess.CalledProcessError as err:
            pprint_subprocess_error(err)
            msg = """
                Phylum project update failed. Skipping repository URL check.
                Use CLI to manually set it:
                https://docs.phylum.io/cli/commands/phylum_project_update"""
            LOG.warning(cleandoc(msg))
            return
        LOG.info("Repository URL successfully set")

    def post_output(self) -> None:
        """Post the output of the analysis as markdown rendered for output to the terminal/logs.

        Each implementation that offers analysis output in the form of comments
        on a pull/merge request should ensure those comments are unique and not
        added multiple times as the review changes but no dependency file does.
        """
        # Post the markdown output, rendered for terminal/log output
        LOG.debug("Analysis output:\n")
        report_md = Markdown(self.analysis_report, hyperlinks=False)
        console.print(report_md)

    @progress_spinner("Analyzing dependencies with Phylum")
    def analyze(self) -> None:
        """Analyze the results gathered from passing the dependency file(s) to the CLI."""
        # Build up the command based on the provided inputs.
        cmd = [
            str(self.cli_path),
            "extension",
            "run",
            "--yes",
            str(CI_EXT_PATH),
            self.phylum_project,
            self.phylum_label,
        ]

        if self.phylum_group:
            cmd.extend(["--group", self.phylum_group])

        current_packages = sorted({pkg for depfile in self.depfiles for pkg in depfile.deps})
        LOG.debug("%s unique current dependencies from %s file(s)", len(current_packages), len(self.depfiles))
        if self.all_deps:
            LOG.info("Considering all current dependencies ...")
            base_packages = []
        else:
            LOG.info("Only considering newly added dependencies ...")
            base_packages = self._get_base_packages()
            new_packages = sorted(set(current_packages).difference(set(base_packages)))
            LOG.debug("%s new dependencies: %s", len(new_packages), new_packages)

        # TODO(maxrake): Better formatting with parenthesized context managers is available in Python 3.10+
        #     https://github.com/phylum-dev/phylum-ci/issues/357
        #     https://docs.python.org/3.10/whatsnew/3.10.html#parenthesized-context-managers
        #     https://stackoverflow.com/q/67808977
        with tempfile.NamedTemporaryFile(
            mode="w+",
            encoding="utf-8",
            prefix="base_",
            suffix=".json",
        ) as base_fd, tempfile.NamedTemporaryFile(
            mode="w+",
            encoding="utf-8",
            prefix="curr_",
            suffix=".json",
        ) as curr_fd:
            json.dump(base_packages, base_fd, cls=DataclassJSONEncoder)
            base_fd.flush()
            cmd.append(base_fd.name)
            json.dump(current_packages, curr_fd, cls=DataclassJSONEncoder)
            curr_fd.flush()
            cmd.append(curr_fd.name)

            LOG.info("Performing analysis. This may take a few seconds.")
            LOG.debug("Using analysis command: %s", shlex.join(cmd))
            try:
                analysis_result = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout  # noqa: S603
            except subprocess.CalledProcessError as err:
                # The Phylum project will fail analysis if the configured policy criteria are not met.
                # This causes the return code to be 100 and lands us here. Check for this case to proceed.
                cli_exit_code_failed_policy = 100
                if err.returncode == cli_exit_code_failed_policy:
                    analysis_result = err.stdout
                else:
                    msg = """
                        There was a problem analyzing the project.
                        A PRO account is needed to use groups.
                        If the command was expected to succeed, please report this as a bug."""
                    raise PhylumCalledProcessError(err, cleandoc(msg)) from err

        self._parse_analysis_result(analysis_result)

    def _get_base_packages(self) -> Packages:
        """Get the dependencies from the common ancestor commit and return them in sorted order."""
        if not self.common_ancestor_commit:
            LOG.info("No common ancestor commit for `%r`. Assuming no base dependencies.", self)
            return []

        base_packages: set[Package] = set()
        with git_worktree(self.common_ancestor_commit, env=self._env) as temp_dir:
            for depfile in self.depfiles:
                prev_depfile_path = temp_dir / depfile.path.relative_to(Path.cwd())
                try:
                    prev_depfile_pkgs = parse_depfile(
                        self.cli_path,
                        depfile.type,
                        prev_depfile_path,
                        start=temp_dir,
                        disable_lockfile_generation=self.disable_lockfile_generation,
                    )
                except subprocess.CalledProcessError as err:
                    pprint_subprocess_error(err)
                    # The Phylum CLI will return a unique error code when a manifest is attempted to be parsed but
                    # lockfile generation has been disabled. This situation is recognized and allowed to continue, but
                    # with a message explaining the reason why no packages from the previous manifest version are used.
                    if err.returncode == CLIExitCode.MANIFEST_WITHOUT_GENERATION.value:
                        msg = f"""
                            Provided manifest [code]{depfile!r}[/] requires lockfile
                            generation to parse but it was disabled to prevent running arbitrary
                            code in untrusted contexts, like PRs from forks. Therefore, no previous
                            packages will be assumed from the manifest."""
                    else:
                        msg = f"""
                            Due to error, assuming no previous packages in [code]{depfile!r}[/].
                            Consider supplying dependency file type explicitly in `.phylum_project`
                            file. For more info: https://docs.phylum.io/cli/lockfile_generation
                            Please report this as a bug if you believe [code]{depfile!r}[/]
                            is a valid [code]{depfile.type}[/] [b]{depfile.depfile_type.value}[/] at revision
                            [code]{self.common_ancestor_commit}[/]."""
                    LOG.warning(cleandoc(msg), extra=MARKUP)
                    continue
                base_packages.update(prev_depfile_pkgs)

        return sorted(base_packages)

    def _parse_analysis_result(self, analysis_result: str) -> None:
        """Parse the results of a Phylum analysis command output."""
        analysis = JobPolicyEvalResult(**json.loads(analysis_result))

        self._analysis_report = analysis.report

        # TODO(maxrake): The logic below would make for a good match statement, which was introduced in Python 3.10
        #     https://github.com/phylum-dev/phylum-ci/issues/357
        if analysis.incomplete_count == 0:
            if analysis.is_failure:
                LOG.error("The analysis is complete and there were failures")
                self.returncode = ReturnCode.POLICY_FAILURE
            else:
                LOG.info("The analysis is complete and there were NO failures")
                self.returncode = ReturnCode.SUCCESS
        elif analysis.is_failure:
            LOG.error("There were failures in one or more completed packages")
            self.returncode = ReturnCode.FAILURE_INCOMPLETE
        else:
            LOG.warning("There were no failures in the packages that have completed so far")
            self.returncode = ReturnCode.INCOMPLETE


# Type alias
CIEnvs = list[CIBase]
