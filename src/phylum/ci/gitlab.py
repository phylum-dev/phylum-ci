"""Define a GitLab CI platform."""
import argparse

from phylum.ci.base import CIBase


class CIGitLab(CIBase):
    """Provide methods for a basic CI environment."""

    def __init__(self, args: argparse.Namespace) -> None:
        super().__init__(args)
        self.ci_platform_name = "GitLab CI"
