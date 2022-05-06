"""Define an implementation for when there is no active CI platform.

This is the case when the `phylum-ci` command is run directly, from the CLI, but not within a CI environment.
This might be useful for running locally.
This is also the fallback implementation to use when no known CI platform is detected.
"""
import argparse

from phylum.ci.base import CIBase


class CINone(CIBase):
    """Provide methods for operating outside of a known CI environment."""

    def __init__(self, args: argparse.Namespace) -> None:
        super().__init__(args)
        self.ci_platform_name = "No CI"
