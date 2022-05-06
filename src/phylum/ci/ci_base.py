"""Define a base environment for CI platforms.

The "base" environment is one that makes use of the CLI directly and is not necessarily part of a continuous
integration (CI) environment. Common functionality is provided where possible and CI specific features are
designated as abstract methods to be defined in specific CI environments.
"""
import argparse
import shutil
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

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


class CIBase(ABC):
    """Provide methods for a basic CI environment."""

    @abstractmethod
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args

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

    # TODO: Consider using CI specific error reporting before moving this method out of the class
    def ensure_phylum_project_present(self):
        """Ensure a `.phylum_project` file exists at the working directory and bail if it does not."""
        cwd = Path.cwd()
        phylum_project_file = cwd / ".phylum_project"
        if phylum_project_file.exists():
            print(" [+] Existing `.phylum_project` file was found at the current working directory")
        else:
            raise RuntimeError(" [!] The `.phylum_project` file was not found at the current working directory.")
