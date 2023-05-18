"""Define an implementation for when called as a Python pre-commit hook.

This is the case when the `phylum-ci` command is run directly, from the CLI, but not within a CI environment. The
command will be issued by the Python `pre-commit` tool and include extra arguments representing a list of staged files.

References:
  * https://pre-commit.com/index.html#creating-new-hooks
  * https://pre-commit.com/index.html#pre-commit-during-commits
  * https://pre-commit.com/index.html#arguments-pattern-in-hooks
"""
import argparse
from functools import cached_property
from pathlib import Path
import re
import subprocess
import sys
from typing import List, Optional

from phylum.ci.ci_base import CIBase
from phylum.ci.git import git_curent_branch_name
from phylum.exceptions import PhylumCalledProcessError, pprint_subprocess_error
from phylum.logger import LOG


class CIPreCommit(CIBase):
    """Provide methods for operating within a pre-commit hook."""

    def __init__(self, args: argparse.Namespace, remainder: List[str]) -> None:  # noqa: D107
        # The base __init__ docstring is better here
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
        try:
            output = subprocess.run(cmd, check=True, text=True, capture_output=True).stdout  # noqa: S603
        except subprocess.CalledProcessError as err:
            msg = "Getting the staged files from git failed."
            raise PhylumCalledProcessError(err, msg) from err
        staged_files = output.strip().split("\n")
        extra_arg_paths = [Path(extra_arg).resolve() for extra_arg in self.extra_args]

        LOG.debug("Checking extra args for valid pre-commit scenarios ...")

        # Allow for a pre-commit config set up to send all staged files to the hook
        if sorted(staged_files) == sorted(self.extra_args):
            LOG.debug("The extra args provided exactly match the list of staged files")
            if any(lockfile.path in extra_arg_paths for lockfile in self.lockfiles):
                LOG.info("Valid pre-commit scenario found: lockfile(s) found in extra arguments")
                return
            LOG.warning("A lockfile is not included in extra args. Nothing to do. Exiting ...")
            sys.exit(0)

        # Allow for a pre-commit config set up to filter the files sent to the hook
        if all(extra_arg in staged_files for extra_arg in self.extra_args):
            LOG.debug("All the extra args are staged files")
            if any(lockfile.path in extra_arg_paths for lockfile in self.lockfiles):
                LOG.info("Valid pre-commit scenario found: lockfile(s) found in extra arguments")
                return
            LOG.warning("A lockfile is not included in extra args. Nothing to do. Exiting ...")
            sys.exit(0)

        # Allow for cases where the lockfile is included or explicitly specified (e.g., `pre-commit run --all-files`)
        if any(lockfile.path in extra_arg_paths for lockfile in self.lockfiles):
            LOG.info("A lockfile was included in the extra args")
        # NOTE: There is still the case where a lockfile is "accidentally" included as an extra argument. For example,
        #       `phylum-ci poetry.lock` was used instead of `phylum-ci --lockfile poetry.lock`, which is bad syntax but
        #       nonetheless results in the `CIPreCommit` environment used instead of `CINone`. This is not terrible; it
        #       just might be a slightly confusing corner case. It might be possible to use a library like `psutil` to
        #       acquire the command line from the parent process and inspect it for `pre-commit` usage. That is a
        #       heavyweight solution and one that will not be pursued until the need for it is more clear.
        else:
            LOG.warning("A lockfile was not included in the extra args...possible invalid pre-commit scenario")
            LOG.error("Unrecognized arguments: [code]%s[/]", " ".join(self.extra_args), extra={"markup": True})
            sys.exit(0)

    @property
    def phylum_label(self) -> str:
        """Get a custom label for use when submitting jobs with `phylum analyze`."""
        current_branch = git_curent_branch_name()
        label = f"{self.ci_platform_name}_{current_branch}_{self.lockfile_hash_object}"
        label = re.sub(r"\s+", "-", label)
        return label

    @cached_property
    def common_ancestor_commit(self) -> Optional[str]:
        """Find the common ancestor commit."""
        cmd = ["git", "rev-parse", "--verify", "HEAD"]
        try:
            common_commit = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603
        except subprocess.CalledProcessError as err:
            pprint_subprocess_error(err)
            LOG.warning("The common ancestor commit could not be found")
            common_commit = None
        return common_commit

    @property
    def is_any_lockfile_changed(self) -> bool:
        """Predicate for detecting if any lockfile has changed.

        For the case of operating within a pre-commit hook, some assumptions are made:
          * The extra, unparsed, arguments provided to the CLI represent the list of staged files
        """
        staged_files = [Path(staged_file).resolve() for staged_file in self.extra_args]
        for lockfile in self.lockfiles:
            if lockfile.path in staged_files:
                LOG.debug("The lockfile [code]%r[/] has changed", lockfile, extra={"markup": True})
                lockfile.is_lockfile_changed = True
            else:
                LOG.debug("The lockfile [code]%r[/] has [b]NOT[/] changed", lockfile, extra={"markup": True})
                lockfile.is_lockfile_changed = False
        return any(lockfile.is_lockfile_changed for lockfile in self.lockfiles)
