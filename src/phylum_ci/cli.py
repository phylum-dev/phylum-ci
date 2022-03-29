"""Console script for phylum_ci."""

import argparse
import sys


def get_args():
    """Get the arguments from the command line and return them."""
    parser = argparse.ArgumentParser(
        prog="phylum-ci",
        description="CLI for handling Phylum integrations",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    return parser.parse_args()


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
