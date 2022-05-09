"""Define an implementation for the GitLab CI platform."""
from argparse import Namespace
from pathlib import Path

from phylum.ci.ci_base import CIBase


# NOTE: This is just a stub for now
# TODO: Add support for GitLab MRs - https://github.com/phylum-dev/phylum-ci/issues/31
class CIGitLab(CIBase):
    """Provide methods for a GitLab CI environment."""

    def __init__(self, args: Namespace) -> None:
        self.ci_platform_name = "GitLab CI"
        super().__init__(args)

    @property
    def phylum_label(self) -> str:
        """Get a custom label for use when submitting jobs with `phylum analyze`."""
        return "TO DO"

    def check_prerequisites(self) -> None:
        """Ensure the necessary pre-requisites are met and bail when they aren't."""
        with super().check_prerequisites():
            print("TO DO")

    def _is_lockfile_changed(self, lockfile: Path) -> bool:
        """Predicate for detecting if the given lockfile has changed."""
        return bool("TO DO")
