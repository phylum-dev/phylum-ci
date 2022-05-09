"""Define a base environment for CI platforms.

The "base" environment is one that makes use of the CLI directly and is not necessarily part of a continuous
integration (CI) environment. Common functionality is provided where possible and CI specific features are
designated as abstract methods to be defined in specific CI environments.
"""
import argparse
import shutil
import subprocess
from abc import ABC, abstractmethod
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from phylum.constants import SUPPORTED_LOCKFILES
from phylum.init.cli import get_expected_phylum_bin_path
from phylum.init.cli import main as phylum_init


# TODO: Move this function to the `phylum.init` package?
def get_phylum_cli_version(cli_path):
    """Get the version of the installed and active Phylum CLI and return it."""
    cmd_line = [cli_path, "--version"]
    version = subprocess.run(cmd_line, check=True, capture_output=True, text=True).stdout.strip().lower()

    # Starting with Python 3.9, the str.removeprefix() method was introduced to do this same thing
    prefix = "phylum "
    prefix_len = len(prefix)
    if version.startswith(prefix):
        version = version[prefix_len:]

    return version


# TODO: Move this function to the `phylum.init` package?
def get_phylum_bin_path(version=None):
    """Get the current path and corresponding version to the Phylum CLI binary and return them.

    Provide a CLI version as a fallback method for looking on an explicit path,
    based on the expected path for that version.
    """
    # Look for `phylum` on the PATH first
    cli_path = shutil.which("phylum")

    if cli_path is None and version is not None:
        # Maybe `phylum` is installed already but not on the PATH or maybe the PATH has not been updated in this
        # context. Look in the specific location expected by the provided version.
        expected_cli_path = get_expected_phylum_bin_path(version)
        cli_path = shutil.which("phylum", path=expected_cli_path)

    if cli_path is None:
        return (None, None)

    cli_path = Path(cli_path)
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


class CIBase(ABC):
    """Provide methods for a basic CI environment."""

    @abstractmethod
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args

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
    @abstractmethod
    def phylum_label(self) -> str:
        """Get a custom label for use when submitting jobs with `phylum analyze`.

        Each CI platform/environment has unique ways of referencing events, PRs, branches, etc.
        """

    @contextmanager
    @abstractmethod
    def check_prerequisites(self) -> None:
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

    def init_cli(self):
        """Check for an existing Phylum CLI install, install it if needed, and return the path to its binary."""
        cli_path, cli_version = get_phylum_bin_path(version=self.args.version)
        if cli_path is None:
            print(f" [+] Existing Phylum CLI instance not found. Installing version `{self.args.version}` ...")
            install_args = ["--phylum-release", self.args.version, "--phylum-token", self.args.token]
            phylum_init(install_args)
        else:
            print(f" [+] Existing Phylum CLI instance found: {cli_version} at {cli_path}")

        cli_path, cli_version = get_phylum_bin_path(version=self.args.version)
        print(f" [+] Using Phylum CLI instance: {cli_version} at {str(cli_path)}")

        # TODO: Set a class property with the `cli_path` value?
        return cli_path

    @abstractmethod
    def _is_lockfile_changed(self, lockfile: Path) -> bool:
        """Predicate for detecting if the given lockfile has changed."""
