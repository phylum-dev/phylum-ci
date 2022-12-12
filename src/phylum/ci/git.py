"""Provide common git functions."""

import subprocess
from pathlib import Path


def git_remote() -> str:
    """Get the git remote and return it.

    This function is limited in that it will only work when there is a single remote defined.
    A RuntimeError exception will be raised when there is not exactly one remote.
    """
    cmd = ["git", "remote"]
    remotes = subprocess.run(cmd, check=True, text=True, capture_output=True).stdout.splitlines()
    if not remotes:
        raise RuntimeError("No git remotes configured")
    if len(remotes) > 1:
        raise RuntimeError("Only one git remote is supported at this time")
    remote = remotes[0]
    return remote


def git_default_branch_name(remote: str) -> str:
    """Get the default branch name and return it.

    This function assumes that the symbolic ref `refs/remotes/<remote>/HEAD`
    exists and contains an entry/mapping to the current default branch.
    """
    prefix = f"refs/remotes/{remote}/"
    cmd = ["git", "symbolic-ref", f"{prefix}HEAD"]
    default_branch_name = subprocess.run(cmd, check=True, text=True, capture_output=True).stdout.strip()

    # Starting with Python 3.9, the str.removeprefix() method was introduced to do this same thing
    prefix_len = len(prefix)
    if default_branch_name.startswith(prefix):
        default_branch_name = default_branch_name[prefix_len:]

    print(f" [+] Default branch name: {default_branch_name}")

    return default_branch_name


def git_curent_branch_name() -> str:
    """Get the current branch name and return it."""
    cmd = ["git", "branch", "--show-current"]
    current_branch = subprocess.run(cmd, check=True, text=True, capture_output=True).stdout.strip()
    return current_branch


def git_hash_object(object_path: Path) -> str:
    """Get the unique key that git uses to refer to the blob type data object for the provided path and return it."""
    # Reference: https://git-scm.com/book/en/v2/Git-Internals-Git-Objects
    cmd = ["git", "hash-object", str(object_path)]
    hash_object = subprocess.run(cmd, check=True, text=True, capture_output=True).stdout.strip()
    return hash_object
