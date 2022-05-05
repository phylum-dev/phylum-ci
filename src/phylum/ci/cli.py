"""Console script for phylum-ci."""
import argparse
import sys

from phylum import __version__
from phylum.ci import SCRIPT_NAME
from phylum.init.cli import get_phylum_bin_path


def get_phylum_cli_version():
    """Get the version of the installed and active Phylum CLI and return it."""
    # TODO: fill this in
    return "v3.1.0"


def get_args():
    """Get the arguments from the command line and return them."""
    parser = argparse.ArgumentParser(
        prog=SCRIPT_NAME,
        description="Use Phylum to analyze dependencies in a CI environment",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"{SCRIPT_NAME} {__version__}",
    )

    return parser.parse_args()


def main():
    """Main entrypoint."""
    args = get_args()

    if args is None:
        return 1

    # TODO: Check for the existence of the CLI and install it if needed
    # TODO: get the Phylum CLI version
    version = get_phylum_cli_version()
    cli_path = get_phylum_bin_path(version)
    print(f"Phylum CLI path: {str(cli_path)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
