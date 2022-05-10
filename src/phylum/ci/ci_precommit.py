"""Define an implementation for when called as a pre-commit hook.

This is the case when the `phylum-ci` command is run directly, from the CLI, but not within a CI environment.
The command will be issued by the `pre-commit` tool and include extra arguments representing a list of staged files.
"""
import argparse
import shutil
import subprocess
from pathlib import Path
from typing import List

from phylum.ci import SCRIPT_NAME
from phylum.ci.ci_base import CIBase


class CIPreCommit(CIBase):
    """Provide methods for operating within a pre-commit hook."""

    def __init__(self, args: argparse.Namespace, remainder: List[str]) -> None:
        self.extra_args = remainder
        self.ci_platform_name = "pre-commit"
        super().__init__(args)

    def check_prerequisites(self) -> None:
        """Ensure the necessary pre-requisites are met and bail when they aren't.

        These are the current pre-requisites for operating within a pre-commit hook:
          * Have `git` installed and available for use on the PATH
          * The extra unparsed arguments passed to the CLI represent the staged files, no more and no less
        """
        with super().check_prerequisites():
            if shutil.which("git"):
                print(" [+] `git` binary found on the PATH")
            else:
                raise SystemExit(" [!] `git` is required to be installed and available on the PATH")

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
        if self.lockfile:
            cmd = f"git hash-object {self.lockfile}".split()
            lockfile_hash_object = subprocess.run(cmd, check=True, text=True, capture_output=True).stdout.strip()
            label = f"{SCRIPT_NAME}_{self.ci_platform_name}_{current_branch}_{lockfile_hash_object}"
        else:
            label = f"{SCRIPT_NAME}_{self.ci_platform_name}_{current_branch}_NO-LOCKFILE"
        label = label.replace(" ", "-")

        return label

    def _is_lockfile_changed(self, lockfile: Path) -> bool:
        """Predicate for detecting if the given lockfile has changed.

        For the case of operating within a pre-commit hook, some assumptions are made:
          * The extra, unparsed, arguments provided to the CLI represent the list of staged files
        """
        staged_files = (Path(staged_file).resolve() for staged_file in self.extra_args)
        return lockfile in staged_files
