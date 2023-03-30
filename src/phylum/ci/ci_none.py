"""Define an implementation for when there is no active CI platform.

This is the case when the `phylum-ci` command is run directly, from the CLI, but not within a CI environment.
This might be useful for running locally.
This is also the fallback implementation to use when no known CI platform is detected.
"""
import argparse
import re
import subprocess
from functools import cached_property
from pathlib import Path
from typing import Optional

from phylum.ci.ci_base import CIBase
from phylum.ci.git import git_curent_branch_name, git_remote


class CINone(CIBase):
    """Provide methods for operating outside of a known CI environment."""

    def __init__(self, args: argparse.Namespace) -> None:
        super().__init__(args)
        self.ci_platform_name = "No CI"

    def _check_prerequisites(self) -> None:
        """Ensure the necessary pre-requisites are met and bail when they aren't.

        These are the current pre-requisites for when no CI environments/platforms is detected:
          * Run the script from the root of a git repository
        """
        super()._check_prerequisites()

        git_dir = Path.cwd() / ".git"
        if git_dir.is_dir():
            print(" [+] Existing `.git` directory was found at the current working directory")
        else:
            raise SystemExit(" [!] This script expects to be run from the top level of a `git` repository")

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
        remote = git_remote()
        cmd = ["git", "merge-base", "HEAD", f"refs/remotes/{remote}/HEAD"]
        try:
            common_commit = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()
        except subprocess.CalledProcessError as err:
            print(f" [!] The common ancestor commit could not be found: {err}")
            print(f" [!] stdout:\n{err.stdout}")
            print(f" [!] stderr:\n{err.stderr}")
            common_commit = None
        return common_commit

    @property
    def is_any_lockfile_changed(self) -> bool:
        """Predicate for detecting if any lockfile has changed.

        For the case of operating outside of a CI platform, some assumptions are made:
          * There is only one remote configured for the repository
          * The diff is comparing against the remote and not another ref
          * The diff is comparing by using the files at the current HEAD

        The usefulness of this approach is limited in that lockfile changes must already be committed to be detected.

        References:
        https://git-scm.com/docs/git-diff#Documentation/git-diff.txt-emgitdiffemltoptionsgtltcommitgtltcommitgt--ltpathgt82308203
        """
        remote = git_remote()
        self.update_lockfiles_change_status(f"refs/remotes/{remote}/HEAD...")
        return any(lockfile.is_lockfile_changed for lockfile in self.lockfiles)
