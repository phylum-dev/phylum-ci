"""Test the git helper functions."""

from pathlib import Path

from dulwich import porcelain
import pytest

from phylum.ci.git import (
    ensure_git_repo_access,
    git_branch_exists,
    git_fetch,
    git_repo_name,
    git_root_dir,
    is_in_git_repo,
)

# Names of a git repository that will be cloned locally
CLONED_LOCAL_REPO_NAMES = [
    "local_repo_name",
    "local_repo.name",
    "local.repo.name",
]

# Names of a git repository that will be initialized locally
# Separate lists are used because cloned local repos with a name ending in `.git` are not supported
INITIALIZED_LOCAL_REPO_NAMES = [*CLONED_LOCAL_REPO_NAMES, "local_repo.git"]


@pytest.mark.parametrize("repo_name", INITIALIZED_LOCAL_REPO_NAMES)
def test_initialized_local_repo_name(tmp_path: Path, repo_name: str) -> None:
    """Ensure a local repo, with no remotes, has it's name correctly identified."""
    repo_path = tmp_path / repo_name
    porcelain.init(str(repo_path))
    local_repo_name = git_repo_name(git_c_path=repo_path)
    assert local_repo_name == repo_name, "The local repo name should be found"


@pytest.mark.parametrize("repo_name", CLONED_LOCAL_REPO_NAMES)
def test_cloned_local_repo_name(tmp_path: Path, repo_name: str) -> None:
    """Ensure a cloned local repo has it's name correctly identified."""
    init_repo_path = tmp_path / repo_name
    cloned_repo_path = tmp_path / "cloned_local_repo_name"
    porcelain.init(str(init_repo_path))
    porcelain.clone(source=str(init_repo_path), target=str(cloned_repo_path))
    remote_repo_name = git_repo_name(git_c_path=cloned_repo_path)
    assert remote_repo_name == repo_name, "The cloned local repo name should be found"


def test_cloned_remote_repo_name(tmp_path: Path) -> None:
    """Ensure a cloned remote repo has it's name correctly identified."""
    repo_path = tmp_path / "cloned_remote_repo_name"
    porcelain.clone(source="https://github.com/phylum-dev/phylum-ci.git", target=str(repo_path), depth=1)
    remote_repo_name = git_repo_name(git_c_path=repo_path)
    assert remote_repo_name == "phylum-ci", "The cloned remote repo name should be found"


def test_fetch_default_remote_branch(tmp_path: Path) -> None:
    """Ensure `git_fetch` works with a cloned remote repo missing it's default remote branch ref."""
    repo_path = tmp_path / "cloned_remote_repo_name"
    porcelain.clone(source="https://github.com/phylum-dev/phylum-ci.git", target=str(repo_path), depth=1)
    default_remote_branch_ref = "refs/remotes/origin/main"
    assert git_branch_exists(default_remote_branch_ref, git_c_path=repo_path)
    default_remote_branch_ref_path = repo_path / ".git" / default_remote_branch_ref
    default_remote_branch_ref_path.unlink(missing_ok=True)
    assert not git_branch_exists(default_remote_branch_ref, git_c_path=repo_path)
    git_fetch(repo="origin", ref="main", git_c_path=repo_path)
    assert git_branch_exists(default_remote_branch_ref, git_c_path=repo_path)


def test_is_in_git_repo(tmp_path: Path) -> None:
    """Identify when the operating context is within a git repository or not."""
    repo_path = tmp_path / "maybe_a_git_repo"
    repo_path.mkdir()
    assert not is_in_git_repo(git_c_path=repo_path), "The path should not be a git repo yet"
    porcelain.init(str(repo_path))
    assert is_in_git_repo(git_c_path=repo_path), "The path should be a git repo"


def test_raises_when_not_in_git_repo(tmp_path: Path) -> None:
    """Ensure an exception is raised when operating outside of a git repository."""
    repo_path = tmp_path / "not_a_git_repo"
    repo_path.mkdir()
    with pytest.raises(SystemExit):
        ensure_git_repo_access(git_c_path=repo_path)


def test_git_root_dir(tmp_path: Path) -> None:
    """Ensure the correct git root directory is returned, regardless of depth."""
    repo_path = tmp_path / "toplevel"
    nested_path = repo_path / "sub_dir_1" / "sub_dir_2"
    nested_path.mkdir(parents=True)
    porcelain.init(str(repo_path))
    assert git_root_dir(git_c_path=repo_path) == repo_path
    assert git_root_dir(git_c_path=nested_path) == repo_path
