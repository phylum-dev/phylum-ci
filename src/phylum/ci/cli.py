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

    # TODO: Add arguments for each of the inputs from the `phylum-analyze-pr-action`.
    #       Allow them to be specified as environment variables as well.
    # TODO: Allow for a specific lockfile name/path to be provided as input (instead of trying to determine it)
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

    # TODO: Determine which CI environment, if any, we are in

    # TODO: Check for existing `.phylum_project` file

    # TODO: Generate PHYLUM_LABEL

    # TODO: Determine the "PR type" (lockfile type or "NA") and report it.
    #       This is also where the diff of the lockfile is taken into account.

    # TODO: Check for the existence of the CLI and install it if needed

    # TODO: get the Phylum CLI version
    version = get_phylum_cli_version()
    cli_path = get_phylum_bin_path(version)
    print(f"Phylum CLI path: {str(cli_path)}")

    # TODO: Analyze project lockfile with phylum CLI

    # TODO: Replicate test matrix?

    # TODO: Compare added dependencies in PR to analysis results

    # TODO: Update the PR/MR with an appropriate comment.
    #       This can be done conditionally based on the CI env, if any, we are in.
    #       Not being in a CI env could be the case when run locally...and may be the basis for a good pre-commit hook.
    #       Look into the `python-gitlab` package

    return 0


if __name__ == "__main__":
    sys.exit(main())
