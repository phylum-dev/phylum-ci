"""Define an implementation for the GitLab CI platform."""
from argparse import Namespace
from pathlib import Path

from phylum.ci.ci_base import CIBase
from phylum.ci.common import Packages


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
        super().check_prerequisites()
        print("TO DO")

    def _is_lockfile_changed(self, lockfile: Path) -> bool:
        """Predicate for detecting if the given lockfile has changed."""
        return bool("TO DO")

    def get_new_deps(self) -> Packages:
        """Get the new dependencies added to the lockfile and return them."""
        # TODO

    def post_output(self) -> None:
        """Post the output of the analysis in the means appropriate for the CI environment."""
        # TODO: Change this placeholder when the real Gitlab CI integration is ready.
        print(f" [+] Analysis output:\n{self.analysis_output}")
