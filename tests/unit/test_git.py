"""Test the git helper functions."""

from pathlib import Path

from dulwich import porcelain
import pytest

from phylum.ci.git import git_branch_exists, git_fetch, git_repo_name

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
def test_initialized_local_repo_name(tmp_path, repo_name):
    """Ensure a local repo, with no remotes, has it's name correctly identified."""
    repo_path: Path = tmp_path / repo_name
    porcelain.init(str(repo_path))
    local_repo_name = git_repo_name(git_c_path=repo_path)
    assert local_repo_name == repo_name, "The local repo name should be found"


@pytest.mark.parametrize("repo_name", CLONED_LOCAL_REPO_NAMES)
def test_cloned_local_repo_name(tmp_path, repo_name: str):
    """Ensure a cloned local repo has it's name correctly identified."""
    init_repo_path: Path = tmp_path / repo_name
    cloned_repo_path: Path = tmp_path / "cloned_local_repo_name"
    porcelain.init(str(init_repo_path))
    porcelain.clone(source=str(init_repo_path), target=str(cloned_repo_path))
    remote_repo_name = git_repo_name(git_c_path=cloned_repo_path)
    assert remote_repo_name == repo_name, "The cloned local repo name should be found"


def test_cloned_remote_repo_name(tmp_path):
    """Ensure a cloned remote repo has it's name correctly identified."""
    repo_path: Path = tmp_path / "cloned_remote_repo_name"
    porcelain.clone(source="https://github.com/phylum-dev/phylum-ci.git", target=str(repo_path), depth=1)
    remote_repo_name = git_repo_name(git_c_path=repo_path)
    assert remote_repo_name == "phylum-ci", "The cloned remote repo name should be found"


def test_fetch_default_remote_branch(tmp_path):
    """Ensure `git_fetch` works with a cloned remote repo missing it's default remote branch ref."""
    repo_path: Path = tmp_path / "cloned_remote_repo_name"
    porcelain.clone(source="https://github.com/phylum-dev/phylum-ci.git", target=str(repo_path), depth=1)
    default_remote_branch_ref = "refs/remotes/origin/main"
    assert git_branch_exists(default_remote_branch_ref, git_c_path=repo_path)
    default_remote_branch_ref_path = repo_path / ".git" / default_remote_branch_ref
    default_remote_branch_ref_path.unlink(missing_ok=True)
    assert not git_branch_exists(default_remote_branch_ref, git_c_path=repo_path)
    git_fetch(repo="origin", ref="main", git_c_path=repo_path)
    assert git_branch_exists(default_remote_branch_ref, git_c_path=repo_path)
