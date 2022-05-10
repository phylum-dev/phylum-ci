"""Define a base environment for CI platforms.

The "base" environment is one that makes use of the CLI directly and is not necessarily part of a continuous
integration (CI) environment. Common functionality is provided where possible and CI specific features are
designated as abstract methods to be defined in specific CI environments.
"""
import shutil
import subprocess
from abc import ABC, abstractmethod
from argparse import Namespace
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, List, Optional, Tuple

from phylum.constants import SUPPORTED_LOCKFILES
from phylum.init.cli import get_expected_phylum_bin_path
from phylum.init.cli import main as phylum_init


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
        self.incomplete_pkgs: List[PackageDescriptor] = []
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
        """
        print(" [+] Confirming pre-requisites ...")

        phylum_project_file = Path.cwd() / ".phylum_project"
        if phylum_project_file.exists():
            print(" [+] Existing `.phylum_project` file was found at the current working directory")
        else:
            # TODO: Consider using CI specific error reporting
            raise SystemExit(" [!] The `.phylum_project` file was not found at the current working directory")

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
                    print(" [+] Using existing version")
                    # TODO: Account for the case that the existing version does not already have a token in place. This
                    #       could be the case if the Docker image is built with a known good/compatible CLI version but
                    #       without a token so that any user can use the image with their own supplied token.
                    #       https://github.com/phylum-dev/phylum-ci/issues/32

        cli_path, cli_version = get_phylum_bin_path(version=specified_version)
        print(f" [+] Using Phylum CLI instance: {cli_version} at {str(cli_path)}")

        self._cli_path = cli_path
