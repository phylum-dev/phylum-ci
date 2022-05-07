"""Define an implementation for when there is no active CI platform.

This is the case when the `phylum-ci` command is run directly, from the CLI, but not within a CI environment.
This might be useful for running locally.
This is also the fallback implementation to use when no known CI platform is detected.
"""
import argparse
import subprocess
from pathlib import Path
from typing import Optional

from phylum.ci import SCRIPT_NAME
from phylum.ci.ci_base import CIBase
from phylum.constants import SUPPORTED_LOCKFILES


def git_remote() -> str:
    """Get the git remote and return it.

    This function is limited in that it will only work when there is a single remote defined.
    A RuntimeError exception will be raised when there is not exactly one remote.
    """
    cmd = "git remote"
    remotes = subprocess.run(cmd.split(), check=True, text=True, capture_output=True).stdout.splitlines()
    if not remotes:
        raise RuntimeError("No git remotes configured")
    if len(remotes) > 1:
        raise RuntimeError("Only one git remote is supported at this time")
    remote = remotes[0]
    return remote


class CINone(CIBase):
    """Provide methods for operating outside of a known CI environment."""

    def __init__(self, args: argparse.Namespace) -> None:
        super().__init__(args)
        self.ci_platform_name = "No CI"

    @property
    def phylum_label(self):
        """Get a custom label for use when submitting jobs with `phylum analyze`."""
        cmd_line = ["git", "branch", "--show-current"]
        current_branch = subprocess.run(cmd_line, check=True, text=True, capture_output=True).stdout.strip()

        # This is the unique key that git uses to refer to the blob type data object for the lockfile.
        # Reference: https://git-scm.com/book/en/v2/Git-Internals-Git-Objects
        if self.lockfile:
            cmd_line = ["git", "hash-object", self.lockfile]
            lockfile_hash_object = subprocess.run(cmd_line, check=True, text=True, capture_output=True).stdout.strip()
            label = f"{SCRIPT_NAME}_NO-CI_{current_branch}_{lockfile_hash_object}"
        else:
            label = f"{SCRIPT_NAME}_NO-CI_{current_branch}_NO-LOCKFILE"

        return label

    def _detect_lockfile(self) -> Optional[Path]:
        """Detect the lockfile in use by the repository and return it.

        For the case of operating outside of a CI platform, some assumptions are made:
        * There is only one remote configured for the repository
        * The diff is comparing against the remote and not another ref
        * The diff is comparing by using the files at the current HEAD

        References:
        https://git-scm.com/docs/git-diff#Documentation/git-diff.txt-emgitdiffemltoptionsgtltcommitgtltcommitgt--ltpathgt82308203
        """
        remote = git_remote()
        cmd = f"git diff --name-only {remote}..."
        changed_files = subprocess.run(cmd.split(), check=True, text=True, capture_output=True).stdout.splitlines()
        changed_files = [Path(changed_file) for changed_file in changed_files]
        lockfiles = [file_ for file_ in changed_files if file_.name in SUPPORTED_LOCKFILES]
        if not lockfiles:
            return None
        if len(lockfiles) > 1:
            raise RuntimeError("Only one lockfile is supported at this time")
        lockfile = lockfiles[0]
        return lockfile

    def _is_lockfile_changed(self, lockfile: Path) -> bool:
        """Predicate for detecting if the given lockfile has changed."""
        remote = git_remote()
        cmd = f"git diff {remote}... -- {lockfile.resolve()}"
        lockfile_diff = subprocess.run(cmd.split(), check=True, text=True, capture_output=True).stdout
        return bool(len(lockfile_diff))
