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
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Optional

from phylum.ci.ci_base import CIBase
from phylum.ci.git import git_curent_branch_name
from phylum.exceptions import PhylumCalledProcessError, pprint_subprocess_error
from phylum.logger import LOG, MARKUP


class CIPreCommit(CIBase):
    """Provide methods for operating within a pre-commit hook."""

    def __init__(self, args: argparse.Namespace, remainder: list[str]) -> None:  # noqa: D107
        # The base __init__ docstring is better here
        self.extra_args = remainder
        super().__init__(args)
        self.ci_platform_name = "pre-commit"

        # There is a history of bugs dealing with git and environment variables set while running pre-commit hooks. In
        # particular, GIT_INDEX_FILE set causes failures when adding new worktrees. Removing it from the environment
        # has no negative effect since git will populate/determine correct values even when this variable is not set.
        # https://github.com/pre-commit/pre-commit/blob/7b868c3508dd3a4c1f1930dc25f5433f2dac7950/pre_commit/git.py#L27
        # https://github.com/mgedmin/check-manifest/issues/122
        # https://git-scm.com/book/en/v2/Git-Internals-Environment-Variables
        self._env = os.environ.copy()
        self._env.pop("GIT_INDEX_FILE", None)

    def _check_prerequisites(self) -> None:
        """Ensure the necessary prerequisites are met and bail when they aren't.

        These are the current prerequisites for operating within a pre-commit hook:
          * The extra unparsed arguments passed to the CLI represent the staged files, no more and no less
        """
        super()._check_prerequisites()

        # "Repeat" these calls from the base class to ensure properties are set before using them
        self._backup_project_file()
        self._find_potential_depfiles()

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
            if any(depfile.path in extra_arg_paths for depfile in self.depfiles):
                LOG.info("Valid pre-commit scenario found: dependency file(s) found in extra arguments")
                return
            LOG.warning("A dependency file is not included in extra args. Nothing to do. Exiting ...")
            sys.exit(0)

        # Allow for a pre-commit config set up to filter the files sent to the hook
        if all(extra_arg in staged_files for extra_arg in self.extra_args):
            LOG.debug("All the extra args are staged files")
            if any(depfile.path in extra_arg_paths for depfile in self.depfiles):
                LOG.info("Valid pre-commit scenario found: dependency file(s) found in extra arguments")
                return
            LOG.warning("A dependency file is not included in extra args. Nothing to do. Exiting ...")
            sys.exit(0)

        # Allow for cases where the dependency file is included or explicitly specified.
        # Example: `pre-commit run --all-files`
        if any(depfile.path in extra_arg_paths for depfile in self.depfiles):
            LOG.info("A dependency file was included in the extra args")
        # NOTE: There is still the case where a dependency file is "accidentally" included as an extra argument. For
        #       example, `phylum-ci poetry.lock` was used instead of `phylum-ci --depfile poetry.lock`, which is bad
        #       syntax but nonetheless results in the `CIPreCommit` environment used instead of `CINone`. This is not
        #       terrible; it just might be a slightly confusing corner case. It might be possible to use a library like
        #       `psutil` to acquire the command line from the parent process and inspect it for `pre-commit` usage.
        #       That is a heavyweight solution and one that will not be pursued until the need for it is more clear.
        else:
            LOG.warning("A dependency file was not included in the extra args...possible invalid pre-commit scenario")
            LOG.error("Unrecognized arguments: [code]%s[/]", " ".join(self.extra_args), extra=MARKUP)
            sys.exit(0)

    @cached_property
    def phylum_label(self) -> str:
        """Get a custom label for use when submitting jobs for analysis."""
        current_branch = git_curent_branch_name()
        label = f"{self.ci_platform_name}_{current_branch}_{self.depfile_hash_object}"
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
    def is_any_depfile_changed(self) -> bool:
        """Predicate for detecting if any dependency file has changed.

        For the case of operating within a pre-commit hook, some assumptions are made:
          * The extra, unparsed, arguments provided to the CLI represent the list of staged files
        """
        staged_files = [Path(staged_file).resolve() for staged_file in self.extra_args]
        for depfile in self.depfiles:
            if depfile.path in staged_files:
                LOG.debug("The dependency file [code]%r[/] has changed", depfile, extra=MARKUP)
                depfile.is_depfile_changed = True
            else:
                LOG.debug("The dependency file [code]%r[/] has [b]NOT[/] changed", depfile, extra=MARKUP)
                depfile.is_depfile_changed = False
        return any(depfile.is_depfile_changed for depfile in self.depfiles)

    @property
    def phylum_comment_exists(self) -> bool:
        """Predicate for detecting whether a Phylum-generated comment exists."""
        # There are no historical comments in this implementation
        return False

    @property
    def repo_url(self) -> Optional[str]:
        """Get the repository URL for reference in Phylum project metadata."""
        # There is no repository URL in this implementation
        return None
