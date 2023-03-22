"""Provide common git functions."""

import os
import subprocess
from pathlib import Path
from typing import List, Optional


def git_base_cmd(git_c_path: Optional[Path] = None) -> List[str]:
    """Provide a normalized base command list for use in constructing git commands.

    The optional `git_c_path` is used to tell `git` to run as if it were started in that
    path instead of the current working directory, which is the default when not provided.
    """
    if git_c_path is None or not git_c_path.exists():
        return ["git"]
    return ["git", "-C", str(git_c_path.resolve())]


def git_remote(git_c_path: Optional[Path] = None) -> str:
    """Get the git remote and return it.

    The optional `git_c_path` is used to tell `git` to run as if it were started in that
    path instead of the current working directory, which is the default when not provided.

    This function is limited in that it will only work when there is a single remote defined.
    A RuntimeError exception will be raised when there is not exactly one remote.
    """
    cmd = git_base_cmd(git_c_path) + ["remote"]
    remotes = subprocess.run(cmd, check=True, text=True, capture_output=True).stdout.splitlines()
    if not remotes:
        raise RuntimeError("No git remotes configured")
    if len(remotes) > 1:
        raise RuntimeError("Only one git remote is supported at this time")
    remote = remotes[0]
    return remote


def git_set_remote_head(remote: str, git_c_path: Optional[Path] = None) -> None:
    """Set the remote HEAD ref for a given remote.

    The optional `git_c_path` is used to tell `git` to run as if it were started in that
    path instead of the current working directory, which is the default when not provided.

    Some CI environments do not set the remote HEAD. Use this function to do so.
    It assumes git credentials are available to run the command.
    """
    base_cmd = git_base_cmd(git_c_path=git_c_path)
    print(" [*] Automatically setting the remote HEAD ref ...")
    cmd = base_cmd + ["remote", "set-head", remote, "--auto"]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as err:
        print(f" [!] Setting the remote HEAD failed: {err}")
        print(f" [!] stdout:\n{err.stdout}")
        print(f" [!] stderr:\n{err.stderr}")
        raise SystemExit(" [!] Ensure credentials are available to run git commands") from err


def git_default_branch_name(remote: str, git_c_path: Optional[Path] = None) -> str:
    """Get the default branch name and return it.

    The optional `git_c_path` is used to tell `git` to run as if it were started in that
    path instead of the current working directory, which is the default when not provided.

    This function assumes that the symbolic ref `refs/remotes/<remote>/HEAD`
    exists and contains an entry/mapping to the current default branch.
    """
    base_cmd = git_base_cmd(git_c_path=git_c_path)
    prefix = f"refs/remotes/{remote}/"
    cmd = base_cmd + ["symbolic-ref", f"{prefix}HEAD"]
    try:
        default_branch_name = subprocess.run(cmd, check=True, text=True, capture_output=True).stdout.strip()
    except subprocess.CalledProcessError:
        # The most likely problem is that the remote HEAD ref is not set. The attempt to set it here, inside
        # the except block, is due to wanting to minimize calling commands that require git credentials.
        print(" [!] Failed to get the remote HEAD ref. It is likely not set. Attempting to set it and try again ...")
        git_set_remote_head(remote)
        default_branch_name = subprocess.run(cmd, check=True, text=True, capture_output=True).stdout.strip()

    # Starting with Python 3.9, the str.removeprefix() method was introduced to do this same thing
    if default_branch_name.startswith(prefix):
        default_branch_name = default_branch_name.replace(prefix, "", 1)

    print(f" [+] Default branch name: {default_branch_name}")

    return default_branch_name


def git_curent_branch_name(git_c_path: Optional[Path] = None) -> str:
    """Get the current branch name and return it.

    The optional `git_c_path` is used to tell `git` to run as if it were started in that
    path instead of the current working directory, which is the default when not provided.
    """
    base_cmd = git_base_cmd(git_c_path=git_c_path)
    cmd = base_cmd + ["branch", "--show-current"]
    current_branch = subprocess.run(cmd, check=True, text=True, capture_output=True).stdout.strip()
    return current_branch


def git_hash_object(object_path: Path, git_c_path: Optional[Path] = None) -> str:
    """Get the unique key that git uses to refer to the blob type data object for the provided path and return it.

    The optional `git_c_path` is used to tell `git` to run as if it were started in that
    path instead of the current working directory, which is the default when not provided.
    """
    base_cmd = git_base_cmd(git_c_path=git_c_path)
    # Reference: https://git-scm.com/book/en/v2/Git-Internals-Git-Objects
    cmd = base_cmd + ["hash-object", str(object_path)]
    hash_object = subprocess.run(cmd, check=True, text=True, capture_output=True).stdout.strip()
    return hash_object


def git_repo_name(git_c_path: Optional[Path] = None) -> str:
    """Get the git repository name and return it.

    The optional `git_c_path` is used to tell `git` to run as if it were started in that
    path instead of the current working directory, which is the default when not provided.

    The repo name will be extracted from the remote's url, when a single remote exists (e.g., repo was cloned).
    Otherwise, the repo name will be derived from the top-level directory name of the git repository. This can happen
    for local use cases where the repository was created with `git init` and no remote set. It may also happen if there
    are multiple remotes set or the link to the original remote was removed.

    Assumptions:
      * Only a single remote is in use if remotes are used
      * When a remote exists, it points to a URL and not another local repo
      * Cloned local repos without a remote defined will have a name that does not end in `.git`
    """
    base_cmd = git_base_cmd(git_c_path=git_c_path)

    try:
        remote = git_remote(git_c_path=git_c_path)
        is_remote_defined = True
        cmd = base_cmd + ["remote", "get-url", remote]
    except RuntimeError as err:
        print(f" [!] {err}. Will get the repo name from the local repository instead.")
        is_remote_defined = False
        cmd = base_cmd + ["rev-parse", "--show-toplevel"]

    full_repo_name = subprocess.run(cmd, check=True, text=True, capture_output=True).stdout.strip()

    repo_name = os.path.basename(full_repo_name)
    if is_remote_defined and repo_name.endswith(".git"):
        repo_name, _ = os.path.splitext(repo_name)

    return repo_name
