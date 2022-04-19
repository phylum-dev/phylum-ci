"""Console script for phylum-install."""

import argparse
import sys

from phylum import PKG_NAME, PKG_SUMMARY, __version__


def get_args(args=None):
    """Get the arguments from the command line and return them.

    Use `args` parameter as dependency injection for testing.
    """
    parser = argparse.ArgumentParser(
        prog=PKG_NAME,
        description=PKG_SUMMARY,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("--version", action="version", version=f"{PKG_NAME} {__version__}")

    return parser.parse_args(args)


def main():
    """Main entrypoint."""
    args = get_args()
    if not args:
        print("Returning error ...")
        return 1

    print("Returning success ...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
