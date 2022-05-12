"""Define an implementation for when called as a Python pre-commit hook.

This is the case when the `phylum-ci` command is run directly, from the CLI, but not within a CI environment. The
command will be issued by the Python `pre-commit` tool and include extra arguments representing a list of staged files.

References:
  * https://pre-commit.com/index.html#creating-new-hooks
  * https://pre-commit.com/index.html#pre-commit-during-commits
  * https://pre-commit.com/index.html#arguments-pattern-in-hooks
"""
import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List

from phylum.ci import SCRIPT_NAME
from phylum.ci.ci_base import CIBase
from phylum.ci.common import PackageDescriptor, Packages


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
        super().check_prerequisites()

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
        cmd = f"git hash-object {self.lockfile}".split()
        lockfile_hash_object = subprocess.run(cmd, check=True, text=True, capture_output=True).stdout.strip()
        label = f"{SCRIPT_NAME}_{self.ci_platform_name}_{current_branch}_{lockfile_hash_object}"
        label = label.replace(" ", "-")

        return label

    def _is_lockfile_changed(self, lockfile: Path) -> bool:
        """Predicate for detecting if the given lockfile has changed.

        For the case of operating within a pre-commit hook, some assumptions are made:
          * The extra, unparsed, arguments provided to the CLI represent the list of staged files
        """
        staged_files = (Path(staged_file).resolve() for staged_file in self.extra_args)
        return lockfile in staged_files

    def get_new_deps(self) -> Packages:
        """Get the new dependencies added to the lockfile and return them."""
        try:
            cmd = f"git rev-parse --verify HEAD:{self.lockfile.name}".split()
            prev_lockfile_object = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()
        except subprocess.CalledProcessError as err:
            # There could be a true error, but the working assumption when here is a previous version does not exist
            print(f" [?] There *may* be an issue with the attempt to get the previous lockfile object: {err}")
            prev_lockfile_object = None

        # Get the current lockfile packages
        cmd = f"{self.cli_path} parse {self.lockfile}".split()
        parse_result = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()
        parsed_pkgs = json.loads(parse_result)
        curr_lockfile_packages = [PackageDescriptor(**pkg) for pkg in parsed_pkgs]

        # When no previous version exists, assume all packages in the lockfile are new
        if not prev_lockfile_object:
            print(" [+] No previous lockfile object found. Assuming all packages in the current lockfile are new.")
            return curr_lockfile_packages

        with tempfile.NamedTemporaryFile(mode="w+") as prev_lockfile_fd:
            cmd = f"git cat-file blob {prev_lockfile_object}".split()
            prev_lockfile_contents = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
            prev_lockfile_fd.write(prev_lockfile_contents)
            cmd = f"{self.cli_path} parse {prev_lockfile_fd.name}".split()
            parse_result = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()

        parsed_pkgs = json.loads(parse_result)
        prev_lockfile_packages = [PackageDescriptor(**pkg) for pkg in parsed_pkgs]
        prev_pkg_set = set(prev_lockfile_packages)
        curr_pkg_set = set(curr_lockfile_packages)
        new_deps = curr_pkg_set.difference(prev_pkg_set)
        print(f" [+] New dependencies: {new_deps}")
        return list(new_deps)

    def post_output(self) -> None:
        """Post the output of the analysis in the means appropriate for the CI environment."""
        # TODO: Change this placeholder when the real Python pre-commit hook is ready.
        #       https://github.com/phylum-dev/phylum-ci/issues/35
        print(f" [+] Analysis output:\n{self.analysis_output}")
