"""Define an implementation for when called as a Python pre-commit hook.

This is the case when the `phylum-ci` command is run directly, from the CLI, but not within a CI environment. The
command will be issued by the Python `pre-commit` tool and include extra arguments representing a list of staged files.

References:
  * https://pre-commit.com/index.html#creating-new-hooks
  * https://pre-commit.com/index.html#pre-commit-during-commits
  * https://pre-commit.com/index.html#arguments-pattern-in-hooks
"""
import argparse
import subprocess
from pathlib import Path
from typing import List, Optional

from phylum.ci import SCRIPT_NAME
from phylum.ci.ci_base import CIBase


class CIPreCommit(CIBase):
    """Provide methods for operating within a pre-commit hook."""

    def __init__(self, args: argparse.Namespace, remainder: List[str]) -> None:
        self.extra_args = remainder
        self.ci_platform_name = "pre-commit"
        super().__init__(args)

    def _check_prerequisites(self) -> None:
        """Ensure the necessary pre-requisites are met and bail when they aren't.

        These are the current pre-requisites for operating within a pre-commit hook:
          * The extra unparsed arguments passed to the CLI represent the staged files, no more and no less
        """
        super()._check_prerequisites()

        cmd = "git diff --cached --name-only".split()
        staged_files = subprocess.run(cmd, check=True, text=True, capture_output=True).stdout.strip().split("\n")
        if sorted(staged_files) == sorted(self.extra_args):
            print(" [+] The extra args provided exactly match the list of staged files")
        else:
            raise SystemExit(f" [!] Unrecognized arguments: {' '.join(self.extra_args)}")

    @property
    def phylum_label(self) -> str:
        """Get a custom label for use when submitting jobs with `phylum analyze`."""
        cmd = "git branch --show-current".split()
        current_branch = subprocess.run(cmd, check=True, text=True, capture_output=True).stdout.strip()

        # This is the unique key that git uses to refer to the blob type data object for the lockfile.
        # Reference: https://git-scm.com/book/en/v2/Git-Internals-Git-Objects
        cmd = f"git hash-object {self.lockfile}".split()
        lockfile_hash_object = subprocess.run(cmd, check=True, text=True, capture_output=True).stdout.strip()
        label = f"{SCRIPT_NAME}_{self.ci_platform_name}_{current_branch}_{lockfile_hash_object}"
        label = label.replace(" ", "-")

        return label

    @property
    def common_lockfile_ancestor_commit(self) -> Optional[str]:
        """Find the common lockfile ancestor commit."""
        cmd = "git rev-parse --verify HEAD".split()
        try:
            common_ancestor_commit = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()
        except subprocess.CalledProcessError as err:
            print(f" [!] The common lockfile ancestor commit could not be found: {err}")
            common_ancestor_commit = None
        return common_ancestor_commit

    def _is_lockfile_changed(self, lockfile: Path) -> bool:
        """Predicate for detecting if the given lockfile has changed.

        For the case of operating within a pre-commit hook, some assumptions are made:
          * The extra, unparsed, arguments provided to the CLI represent the list of staged files
        """
        staged_files = (Path(staged_file).resolve() for staged_file in self.extra_args)
        return lockfile in staged_files

    def post_output(self) -> None:
        """Post the output of the analysis in the means appropriate for the CI environment."""
        # TODO: Change this placeholder when the real Python pre-commit hook is ready.
        #       https://github.com/phylum-dev/phylum-ci/issues/35
        print(f" [+] Analysis output:\n{self.analysis_output}")
