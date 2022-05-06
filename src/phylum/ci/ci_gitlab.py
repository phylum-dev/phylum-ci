"""Define an implementation for the GitLab CI platform."""
import argparse

from phylum.ci.base import CIBase


# NOTE: This is just a stub for now
# TODO: Add support for GitLab MRs - https://github.com/phylum-dev/phylum-ci/issues/31
class CIGitLab(CIBase):
    """Provide methods for a GitLab CI environment."""

    def __init__(self, args: argparse.Namespace) -> None:
        super().__init__(args)
        self.ci_platform_name = "GitLab CI"
