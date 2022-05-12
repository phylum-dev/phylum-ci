"""Define an implementation for when there is no active CI platform.

This is the case when the `phylum-ci` command is run directly, from the CLI, but not within a CI environment.
This might be useful for running locally.
This is also the fallback implementation to use when no known CI platform is detected.
"""
import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from phylum.ci import SCRIPT_NAME
from phylum.ci.ci_base import CIBase
from phylum.ci.common import PackageDescriptor, Packages


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
        self.ci_platform_name = "No CI"
        super().__init__(args)

    def check_prerequisites(self) -> None:
        """Ensure the necessary pre-requisites are met and bail when they aren't.

        These are the current pre-requisites for when no CI environments/platforms is detected:
          * Have `git` installed and available for use on the PATH
          * Run the script from the root of a git repository
        """
        super().check_prerequisites()

        if shutil.which("git"):
            print(" [+] `git` binary found on the PATH")
        else:
            raise SystemExit(" [!] `git` is required to be installed and available on the PATH")

        git_dir = Path.cwd() / ".git"
        if git_dir.is_dir():
            print(" [+] Existing `.git` directory was found at the current working directory")
        else:
            raise SystemExit(" [!] This script expects to be run from the top level of a `git` repository")

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

        For the case of operating outside of a CI platform, some assumptions are made:
          * There is only one remote configured for the repository
          * The diff is comparing against the remote and not another ref
          * The diff is comparing by using the files at the current HEAD

        The usefulness of this approach is limited in that lockfile changes must already be committed to be detected.

        References:
        https://git-scm.com/docs/git-diff#Documentation/git-diff.txt-emgitdiffemltoptionsgtltcommitgtltcommitgt--ltpathgt82308203
        """
        remote = git_remote()
        cmd = f"git diff --exit-code --quiet refs/remotes/{remote}/HEAD... -- {lockfile.resolve()}".split()
        return bool(subprocess.run(cmd).returncode)

    def get_new_deps(self) -> Packages:
        """Get the new dependencies added to the lockfile and return them."""
        # Get the common ancestor
        remote = git_remote()
        cmd = f"git merge-base HEAD refs/remotes/{remote}/HEAD".split()
        common_ancestor_commit = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()
        try:
            cmd = f"git rev-parse --verify {common_ancestor_commit}:{self.lockfile.name}".split()
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
        # This is a bit of a placeholder for now. The output works in that it is human readable.
        # However, it is more meant for display on the web, as HTML and rendered Markdown.
        print(f" [+] Analysis output:\n{self.analysis_output}")
