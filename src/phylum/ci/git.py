"""Provide common git functions."""

from collections.abc import Generator, Mapping
import contextlib
from inspect import cleandoc
from pathlib import Path
import shlex
import subprocess
import tempfile

from phylum.exceptions import PhylumCalledProcessError, pprint_subprocess_error
from phylum.logger import LOG, MARKUP


def git_base_cmd(git_c_path: Path | None = None) -> list[str]:
    """Provide a normalized base command list for use in constructing git commands.

    The optional `git_c_path` is used to tell `git` to run as if it were started in that
    path instead of the current working directory, which is the default when not provided.
    """
    if git_c_path is None or not git_c_path.exists():
        return ["git"]
    return ["git", "-C", str(git_c_path.resolve())]


def is_in_git_repo(git_c_path: Path | None = None) -> bool:
    """Predicate for determining if operating within the context of an accessible git repository.

    The optional `git_c_path` is used to tell `git` to run as if it were started in that
    path instead of the current working directory, which is the default when not provided.
    """
    base_cmd = git_base_cmd(git_c_path=git_c_path)
    cmd = [*base_cmd, "rev-parse", "--show-toplevel"]

    # We want the return code here and don't want to raise when non-zero.
    return not bool(subprocess.run(cmd, check=False, capture_output=True).returncode)  # noqa: S603


def ensure_git_repo_access(git_c_path: Path | None = None) -> None:
    """Ensure user account executing `git` has access to the repository.

    The optional `git_c_path` is used to tell `git` to run as if it were started in that
    path instead of the current working directory, which is the default when not provided.
    """
    if is_in_git_repo(git_c_path=git_c_path):
        LOG.debug("Operating within git repository, with proper access")
        return

    # There are two likely reasons to fail the git repo membership test:
    #
    #   1. Not actually in a git repo, in which case there is nothing that can be done.
    #   2. The repository is owned by a different user and we don't have access to it.
    #      This can be remedied with a configuration change. References:
    #      https://confluence.atlassian.com/pages/viewpage.action?pageId=1167744132
    #      https://confluence.atlassian.com/pages/viewpage.action?pageId=1384121844
    #      https://git-scm.com/docs/git-config/2.35.2#Documentation/git-config.txt-safedirectory

    base_cmd = git_base_cmd(git_c_path=git_c_path)
    cmd = [*base_cmd, "rev-parse", "--show-toplevel"]

    try:
        _ = subprocess.run(cmd, check=True, text=True, capture_output=True, encoding="utf-8")  # noqa: S603
    except subprocess.CalledProcessError as outer_err:
        # Account for reason #1
        std_err: str = outer_err.stderr
        if "not a git repository" in std_err:
            msg = "Must be operating within the context of a git repository"
            raise PhylumCalledProcessError(outer_err, msg) from outer_err

        # Account for reason #2
        # The error message states the command to use to update the configuration, so use it
        start_of_cmd = "git config --global --add safe.directory"
        if start_of_cmd in std_err:
            msg = """
                This git repository is owned by a different user!
                Adding repository directory to git global config as safe directory ..."""
            LOG.warning(cleandoc(msg))
            start_of_cmd_idx = std_err.find(start_of_cmd)
            cmd_msg = std_err[start_of_cmd_idx:]
            cmd_list = shlex.split(cmd_msg)
            # Ensure the `git` part of the command takes into account the optional `git_c_path`
            conf_cmd = [*base_cmd, *cmd_list[1:]]
            num_tokens = len(conf_cmd)
            # Ensure the "<DIR>" part of the command is only one token and that nothing comes after it:
            # "<GIT_BASE_CMD> config --global --add safe.directory <DIR>"
            expected_num_tokens = len(base_cmd) + 5
            if num_tokens != expected_num_tokens:
                msg = f"""
                    {num_tokens} tokens provided but exactly {expected_num_tokens} were expected.
                    Bailing instead of executing this unexpected command:
                        [code]{shlex.join(conf_cmd)}[/]
                    Please report this as a bug if you believe the command is correct."""
                raise PhylumCalledProcessError(outer_err, cleandoc(msg)) from outer_err
            LOG.debug("Executing command: [code]%s[/]", shlex.join(conf_cmd), extra=MARKUP)
            try:
                _ = subprocess.run(conf_cmd, check=True, text=True, capture_output=True, encoding="utf-8")  # noqa: S603
            except subprocess.CalledProcessError as inner_err:
                msg = "Unable to add repository to git global config as safe directory"
                raise PhylumCalledProcessError(inner_err, msg) from inner_err
            msg = f"""
                Config updated. Undo for non-ephemeral environments with command:
                    [code]{shlex.join(conf_cmd).replace("--add", "--unset", 1)}[/]"""
            LOG.warning(cleandoc(msg), extra=MARKUP)


def git_remote(git_c_path: Path | None = None) -> str:
    """Get the git remote and return it.

    The optional `git_c_path` is used to tell `git` to run as if it were started in that
    path instead of the current working directory, which is the default when not provided.

    This function is limited in that it will only work when there is a single remote defined.
    A RuntimeError exception will be raised when there is not exactly one remote.
    """
    cmd = [*git_base_cmd(git_c_path), "remote"]
    try:
        remotes = subprocess.run(  # noqa: S603
            cmd,
            check=True,
            text=True,
            capture_output=True,
            encoding="utf-8",
        ).stdout.splitlines()
    except subprocess.CalledProcessError as err:
        msg = "There was an error retrieving the git remote"
        raise PhylumCalledProcessError(err, msg) from err
    if not remotes:
        msg = "No git remotes configured"
        raise RuntimeError(msg)
    if len(remotes) > 1:
        msg = "Only one git remote is supported at this time"
        raise RuntimeError(msg)
    remote = remotes[0]
    return remote


def git_fetch(repo: str | None = None, ref: str | None = None, git_c_path: Path | None = None) -> None:
    """Execute a `git fetch` command with optional repository and refspec specified.

    See git documentation for more detail: https://git-scm.com/docs/git-fetch

    The optional `git_c_path` is used to tell `git` to run as if it were started in that
    path instead of the current working directory, which is the default when not provided.
    """
    base_cmd = git_base_cmd(git_c_path=git_c_path)
    cmd = [*base_cmd, "fetch"]
    if repo is not None:
        cmd.append(repo)
        # Specifying a refspec is only possible when a repository is already specified
        if ref is not None:
            cmd.append(ref)
    LOG.debug("Executing command: %s", shlex.join(cmd))
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, encoding="utf-8")  # noqa: S603
    except subprocess.CalledProcessError as err:
        msg = "Fetching failed. Ensure credentials are available to run git commands."
        raise PhylumCalledProcessError(err, msg) from err


def git_branch_exists(ref_path: str, git_c_path: Path | None = None) -> bool:
    """Predicate for whether a given branch exists.

    `ref_path` is meant to be an "exact path" to a specific reference (e.g., `refs/remotes/origin/main`)
    Reference: https://git-scm.com/docs/git-show-ref

    The optional `git_c_path` is used to tell `git` to run as if it were started in that
    path instead of the current working directory, which is the default when not provided.
    """
    base_cmd = git_base_cmd(git_c_path=git_c_path)
    cmd = [*base_cmd, "show-ref", "--quiet", "--verify", "--", ref_path]
    LOG.debug("Executing command: %s", shlex.join(cmd))
    # We want the return code here and don't want to raise when non-zero.
    if bool(subprocess.run(cmd, check=False).returncode):  # noqa: S603
        LOG.debug("%s does not exist", ref_path)
        return False
    LOG.debug("%s exists", ref_path)
    return True


def git_set_remote_head(remote: str, git_c_path: Path | None = None) -> None:
    """Set the remote HEAD ref for a given remote.

    The optional `git_c_path` is used to tell `git` to run as if it were started in that
    path instead of the current working directory, which is the default when not provided.

    Some CI environments do not set the remote HEAD. Use this function to do so.
    It assumes git credentials are available to run the command.
    """
    base_cmd = git_base_cmd(git_c_path=git_c_path)
    LOG.info("Automatically setting the remote HEAD ref ...")
    cmd = [*base_cmd, "remote", "set-head", remote, "--auto"]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, encoding="utf-8")  # noqa: S603
    except subprocess.CalledProcessError as err:
        msg = "Setting the remote HEAD failed. Ensure credentials are available to run git commands."
        raise PhylumCalledProcessError(err, msg) from err


def git_default_branch_name(remote: str, git_c_path: Path | None = None) -> str:
    """Get the default branch name and return it.

    The optional `git_c_path` is used to tell `git` to run as if it were started in that
    path instead of the current working directory, which is the default when not provided.

    This function assumes that the symbolic ref `refs/remotes/<remote>/HEAD`
    exists and contains an entry/mapping to the current default branch.
    """
    base_cmd = git_base_cmd(git_c_path=git_c_path)
    prefix = f"refs/remotes/{remote}/"
    cmd = [*base_cmd, "symbolic-ref", f"{prefix}HEAD"]
    try:
        default_branch_name = subprocess.run(  # noqa: S603
            cmd,
            check=True,
            text=True,
            capture_output=True,
            encoding="utf-8",
        ).stdout
    except subprocess.CalledProcessError as outer_err:
        # The most likely problem is that the remote HEAD ref is not set. The attempt to set it here, inside
        # the except block, is due to wanting to minimize calling commands that require git credentials.
        pprint_subprocess_error(outer_err)
        LOG.warning("Failed to get the remote HEAD ref. It is likely not set. Attempting to set it and try again ...")
        git_set_remote_head(remote)
        try:
            default_branch_name = subprocess.run(  # noqa: S603
                cmd,
                check=True,
                text=True,
                capture_output=True,
                encoding="utf-8",
            ).stdout
        except subprocess.CalledProcessError as inner_err:
            msg = "Failed to get the remote HEAD ref even after setting it."
            raise PhylumCalledProcessError(inner_err, msg) from outer_err
    default_branch_name = default_branch_name.strip().removeprefix(prefix)
    LOG.debug("Default branch name: %s", default_branch_name)
    return default_branch_name


def git_root_dir(git_c_path: Path | None = None) -> Path:
    """Get the top-level (root) directory of the git working tree and return it.

    The optional `git_c_path` is used to tell `git` to run as if it were started in that
    path instead of the current working directory, which is the default when not provided.
    """
    base_cmd = git_base_cmd(git_c_path=git_c_path)
    cmd = [*base_cmd, "rev-parse", "--show-toplevel"]
    try:
        git_root = subprocess.run(  # noqa: S603
            cmd,
            check=True,
            text=True,
            capture_output=True,
            encoding="utf-8",
        ).stdout.strip()
    except subprocess.CalledProcessError as err:
        msg = "Must be operating within the context of a git repository"
        raise PhylumCalledProcessError(err, msg) from err
    return Path(git_root).resolve()


def git_current_branch_name(git_c_path: Path | None = None) -> str:
    """Get the current branch name and return it.

    The optional `git_c_path` is used to tell `git` to run as if it were started in that
    path instead of the current working directory, which is the default when not provided.
    """
    base_cmd = git_base_cmd(git_c_path=git_c_path)
    cmd = [*base_cmd, "branch", "--show-current"]
    try:
        current_branch = subprocess.run(  # noqa: S603
            cmd,
            check=True,
            text=True,
            capture_output=True,
            encoding="utf-8",
        ).stdout.strip()
    except subprocess.CalledProcessError as err:
        msg = "There was an error retrieving the current branch name"
        raise PhylumCalledProcessError(err, msg) from err
    return current_branch


def git_hash_object(object_path: Path, git_c_path: Path | None = None) -> str:
    """Get the unique key that git uses to refer to the blob type data object for the provided path and return it.

    The optional `git_c_path` is used to tell `git` to run as if it were started in that
    path instead of the current working directory, which is the default when not provided.
    """
    base_cmd = git_base_cmd(git_c_path=git_c_path)
    # Reference: https://git-scm.com/book/en/v2/Git-Internals-Git-Objects
    cmd = [*base_cmd, "hash-object", str(object_path)]
    try:
        hash_object = subprocess.run(  # noqa: S603
            cmd,
            check=True,
            text=True,
            capture_output=True,
            encoding="utf-8",
        ).stdout.strip()
    except subprocess.CalledProcessError as err:
        msg = "There was an error retrieving the git hash object"
        raise PhylumCalledProcessError(err, msg) from err
    return hash_object


def git_repo_name(git_c_path: Path | None = None) -> str:
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
        cmd = [*base_cmd, "remote", "get-url", remote]
    except RuntimeError as err:
        LOG.warning("%s. Will get the repo name from the local repository instead.", err)
        is_remote_defined = False
        cmd = [*base_cmd, "rev-parse", "--show-toplevel"]

    try:
        full_repo_name = subprocess.run(  # noqa: S603
            cmd,
            check=True,
            text=True,
            capture_output=True,
            encoding="utf-8",
        ).stdout.strip()
    except subprocess.CalledProcessError as err:
        msg = """
            Getting the git repository name failed. Are all assumptions met:
              * Only a single remote is in use if remotes are used
              * When a remote exists, it points to a URL and not another local repo
              * Cloned local repos without a remote defined have a name that does
                not end in `.git`"""
        raise PhylumCalledProcessError(err, cleandoc(msg)) from err

    full_repo_path = Path(full_repo_name)
    repo_name = full_repo_path.name
    if is_remote_defined and repo_name.endswith(".git"):
        repo_name = full_repo_path.stem

    return repo_name


@contextlib.contextmanager
def git_worktree(
    commit: str,
    env: Mapping[str, str] | None = None,
    git_c_path: Path | None = None,
) -> Generator[Path, None, None]:
    """Create a git worktree at the given commit.

    This is a context manager that yields a `Path` to the worktree, created in a temporary directory.

    Example:
    ```
    with git_worktree(commit) as temp_dir:
        # Analyze files in the worktree.
        # The worktree will be removed at the end of the block.
    ```

    The optional `git_c_path` is used to tell `git` to run as if it were started in that
    path instead of the current working directory, which is the default when not provided.
    """
    base_cmd = git_base_cmd(git_c_path=git_c_path)
    with tempfile.TemporaryDirectory(prefix="phylum_") as temp_dir:
        cmd = [*base_cmd, "worktree", "add", "--detach", temp_dir, commit]
        LOG.debug("Adding git worktree for base iteration in a temporary directory ...")
        LOG.debug("Using command: %s", shlex.join(cmd))
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, env=env, encoding="utf-8")  # noqa: S603
        except subprocess.CalledProcessError as err:
            msg = f"Unable to create a git worktree at commit: {commit}"
            raise PhylumCalledProcessError(err, msg) from err
        temp_dir_path = Path(temp_dir).resolve()
        try:
            yield temp_dir_path
        finally:
            remove_git_worktree(temp_dir_path)


def remove_git_worktree(worktree: Path, git_c_path: Path | None = None) -> None:
    """Remove a given git worktree.

    The optional `git_c_path` is used to tell `git` to run as if it were started in that
    path instead of the current working directory, which is the default when not provided.

    If a working tree is deleted without using `git worktree remove`, then its associated
    administrative files, which reside in the repository, will eventually be removed automatically.
    Ref: https://git-scm.com/docs/git-worktree

    Use this function to remove the worktree now since the default for the `gc.worktreePruneExpire` setting is 3 months.
    """
    base_cmd = git_base_cmd(git_c_path=git_c_path)
    cmd = [*base_cmd, "worktree", "remove", "--force", str(worktree)]
    LOG.debug("Removing the git worktree for the base iteration ...")
    LOG.debug("Using command: %s", shlex.join(cmd))
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, encoding="utf-8")  # noqa: S603
    except subprocess.CalledProcessError as err:
        pprint_subprocess_error(err)
        LOG.warning("Unable to remove the git worktree. Try running `git worktree prune` manually.")
