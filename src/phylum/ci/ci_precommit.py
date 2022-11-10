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
import sys
from pathlib import Path
from typing import List, Optional

from phylum.ci.ci_base import CIBase


class CIPreCommit(CIBase):
    """Provide methods for operating within a pre-commit hook."""

    def __init__(self, args: argparse.Namespace, remainder: List[str]) -> None:
        self.extra_args = remainder
        super().__init__(args)
        self.ci_platform_name = "pre-commit"

    def _check_prerequisites(self) -> None:
        """Ensure the necessary pre-requisites are met and bail when they aren't.

        These are the current pre-requisites for operating within a pre-commit hook:
          * The extra unparsed arguments passed to the CLI represent the staged files, no more and no less
        """
        super()._check_prerequisites()

        cmd = ["git", "diff", "--cached", "--name-only"]
        staged_files = subprocess.run(cmd, check=True, text=True, capture_output=True).stdout.strip().split("\n")
        extra_arg_paths = (Path(extra_arg).resolve() for extra_arg in self.extra_args)

        print(" [*] Checking extra args for valid pre-commit scenarios ...")

        # Allow for a pre-commit config set up to send all staged files to the hook
        if sorted(staged_files) == sorted(self.extra_args):
            print(" [+] The extra args provided exactly match the list of staged files")
            if self.lockfile in extra_arg_paths:
                print(" [+] Valid pre-commit scenario found: lockfile found in extra arguments")
                return
            print(" [+] The lockfile is not included in extra args. Nothing to do. Exiting ...")
            sys.exit(0)

        # Allow for a pre-commit config set up to filter the files sent to the hook
        if all(extra_arg in staged_files for extra_arg in self.extra_args):
            print(" [+] All the extra args are staged files")
            if self.lockfile in extra_arg_paths:
                print(" [+] Valid pre-commit scenario found: lockfile found in extra arguments")
                return
            print(" [+] The lockfile is not included in extra args. Nothing to do. Exiting ...")
            sys.exit(0)

        # Allow for cases where the lockfile is included or explicitly specified (e.g., `pre-commit run --all-files`)
        if self.lockfile in extra_arg_paths:
            print(" [+] The lockfile was included in the extra args")
        # NOTE: There is still the case where the lockfile is "accidentally" included as an extra argument. For example,
        #       `phylum-ci poetry.lock` was used instead of `phylum-ci --lockfile poetry.lock`, which is bad syntax but
        #       nonetheless results in the `CIPreCommit` environment used instead of `CINone`. This is not terrible; it
        #       just might be a slightly confusing corner case. It might be possible to use a library like `psutil` to
        #       acquire the command line from the parent process and inspect it for `pre-commit` usage. That is a
        #       heavyweight solution and one that will not be pursued until the need for it is more clear.
        else:
            print(" [+] The lockfile was not included in the extra args...possible invalid pre-commit scenario")
            print(f" [!] Unrecognized arguments: {' '.join(self.extra_args)}")
            sys.exit(0)

    @property
    def phylum_label(self) -> str:
        """Get a custom label for use when submitting jobs with `phylum analyze`."""
        cmd = ["git", "branch", "--show-current"]
        current_branch = subprocess.run(cmd, check=True, text=True, capture_output=True).stdout.strip()

        # This is the unique key that git uses to refer to the blob type data object for the lockfile.
        # Reference: https://git-scm.com/book/en/v2/Git-Internals-Git-Objects
        cmd = ["git", "hash-object", str(self.lockfile)]
        lockfile_hash_object = subprocess.run(cmd, check=True, text=True, capture_output=True).stdout.strip()
        label = f"{self.ci_platform_name}_{current_branch}_{lockfile_hash_object[:7]}"
        label = label.replace(" ", "-")

        return label

    @property
    def common_lockfile_ancestor_commit(self) -> Optional[str]:
        """Find the common lockfile ancestor commit."""
        cmd = ["git", "rev-parse", "--verify", "HEAD"]
        try:
            common_ancestor_commit = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()
        except subprocess.CalledProcessError as err:
            print(f" [!] The common lockfile ancestor commit could not be found: {err}")
            print(f" [!] stdout:\n{err.stdout}")
            print(f" [!] stderr:\n{err.stderr}")
            common_ancestor_commit = None
        return common_ancestor_commit

    def _is_lockfile_changed(self, lockfile: Path) -> bool:
        """Predicate for detecting if the given lockfile has changed.

        For the case of operating within a pre-commit hook, some assumptions are made:
          * The extra, unparsed, arguments provided to the CLI represent the list of staged files
        """
        staged_files = (Path(staged_file).resolve() for staged_file in self.extra_args)
        return lockfile in staged_files
