"""Define an implementation for when there is no active CI platform.

This is the case when the `phylum-ci` command is run directly, from the CLI, but not within a CI environment.
This might be useful for running locally.
This is also the fallback implementation to use when no known CI platform is detected.
"""
import argparse
import subprocess
from pathlib import Path
from typing import Optional

from phylum.ci.ci_base import CIBase, git_remote


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
        remote = git_remote()
        cmd = ["git", "merge-base", "HEAD", f"refs/remotes/{remote}/HEAD"]
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

        For the case of operating outside of a CI platform, some assumptions are made:
          * There is only one remote configured for the repository
          * The diff is comparing against the remote and not another ref
          * The diff is comparing by using the files at the current HEAD

        The usefulness of this approach is limited in that lockfile changes must already be committed to be detected.

        References:
        https://git-scm.com/docs/git-diff#Documentation/git-diff.txt-emgitdiffemltoptionsgtltcommitgtltcommitgt--ltpathgt82308203
        """
        remote = git_remote()
        # `--exit-code` will make git exit with with 1 if there were differences while 0 means no differences.
        # Any other exit code is an error and a reason to re-raise.
        cmd = ["git", "diff", "--exit-code", "--quiet", f"refs/remotes/{remote}/HEAD...", "--", str(lockfile.resolve())]
        ret = subprocess.run(cmd, check=False)
        if ret.returncode == 0:
            return False
        if ret.returncode == 1:
            return True
        ret.check_returncode()
        return False  # unreachable code but this makes mypy happy
