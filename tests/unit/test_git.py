"""Test the git helper functions."""

from inspect import cleandoc
import logging
from pathlib import Path
import subprocess
from unittest.mock import MagicMock, call, patch

from dulwich import porcelain, repo
import pytest

from phylum.ci import git
from tests.constants import only_run_if_ci

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
    """Ensure a local repo, with no remotes, has its name correctly identified."""
    repo_path = tmp_path / repo_name
    porcelain.init(repo_path)
    local_repo_name = git.git_repo_name(git_c_path=repo_path)
    assert local_repo_name == repo_name, "The local repo name should be found"


@pytest.mark.parametrize("repo_name", CLONED_LOCAL_REPO_NAMES)
def test_cloned_local_repo_name(tmp_path: Path, repo_name: str) -> None:
    """Ensure a cloned local repo has its name correctly identified."""
    init_repo_path = tmp_path / repo_name
    cloned_repo_path = tmp_path / "cloned_local_repo_name"
    porcelain.init(init_repo_path)
    porcelain.clone(source=str(init_repo_path), target=cloned_repo_path)
    remote_repo_name = git.git_repo_name(git_c_path=cloned_repo_path)
    assert remote_repo_name == repo_name, "The cloned local repo name should be found"


@only_run_if_ci
def test_cloned_remote_repo_name(tmp_path: Path) -> None:
    """Ensure a cloned remote repo has its name correctly identified."""
    repo_path = tmp_path / "cloned_remote_repo_name"
    porcelain.clone(source="https://github.com/phylum-dev/phylum-ci.git", target=repo_path, depth=1)
    remote_repo_name = git.git_repo_name(git_c_path=repo_path)
    assert remote_repo_name == "phylum-ci", "The cloned remote repo name should be found"


def test_remote_defined_git_repo_name(tmp_path: Path) -> None:
    """Ensure a git repo with a remote defined has its name correctly identified."""
    repo_path = tmp_path / "test_repo"
    porcelain.init(repo_path)
    porcelain.remote_add(repo_path, "origin", url="https://github.com/phylum-dev/phylum-ci.git")
    remote_repo_name = git.git_repo_name(git_c_path=repo_path)
    assert remote_repo_name == "phylum-ci", "The remote repo name should be found"


def test_git_repo_name_fails_with_subprocess_error(tmp_path: Path) -> None:
    """Ensure `git_repo_name` raises a error when all attempts to acquire name fail."""
    repo_path = tmp_path / "non_git_dir"
    repo_path.mkdir()
    with (
        # Simulate a successful `git_remote` call
        patch("phylum.ci.git.git_remote", return_value="origin"),
        # Simulate a failed `git remote get-url` call
        patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, ["git", "remote", "get-url", "origin"])),
        # `PhylumCalledProcessError` is initially raised but will ultimately raise `SystemExit`
        pytest.raises(SystemExit),
    ):
        git.git_repo_name(git_c_path=repo_path)


def test_git_base_cmd_with_non_existent_path(tmp_path: Path) -> None:
    """Ensure `git_base_cmd` returns the correct base command with a non-existent path."""
    non_existent_path = tmp_path / "non_existent_dir"
    assert git.git_base_cmd(git_c_path=non_existent_path) == ["git"], "Base command should not include -C option"


@patch("subprocess.run")
def test_git_fetch_no_repo_or_ref(mock_run: MagicMock, tmp_path: Path) -> None:
    """Ensure `git_fetch` successfully executes with no repo or ref specified."""
    repo_path = tmp_path / "test_repo"
    porcelain.init(repo_path)
    base_cmd = git.git_base_cmd(git_c_path=repo_path)
    expected_cmd = [*base_cmd, "fetch"]
    git.git_fetch(git_c_path=repo_path)
    mock_run.assert_called_once_with(expected_cmd, check=True, capture_output=True, text=True, encoding="utf-8")


@patch("subprocess.run")
def test_git_fetch_with_repo_only(mock_run: MagicMock, tmp_path: Path) -> None:
    """Ensure `git_fetch` executes with a specified repo but no ref."""
    repo_path = tmp_path / "test_repo"
    porcelain.init(repo_path)
    repo_name = "origin"
    git.git_fetch(repo=repo_name, git_c_path=repo_path)
    expected_cmd = ["git", "-C", str(repo_path), "fetch", repo_name]
    mock_run.assert_called_once_with(expected_cmd, check=True, capture_output=True, text=True, encoding="utf-8")


@only_run_if_ci
def test_fetch_default_remote_branch(tmp_path: Path) -> None:
    """Ensure `git_fetch` works with a cloned remote repo missing its default remote branch ref."""
    repo_path = tmp_path / "cloned_remote_repo_name"
    porcelain.clone(source="https://github.com/phylum-dev/phylum-ci.git", target=repo_path, depth=1)
    default_remote_branch_ref = "refs/remotes/origin/main"
    assert git.git_branch_exists(default_remote_branch_ref, git_c_path=repo_path)
    default_remote_branch_ref_path = repo_path / ".git" / default_remote_branch_ref
    default_remote_branch_ref_path.unlink(missing_ok=True)
    assert not git.git_branch_exists(default_remote_branch_ref, git_c_path=repo_path)
    git.git_fetch(repo="origin", ref="main", git_c_path=repo_path)
    assert git.git_branch_exists(default_remote_branch_ref, git_c_path=repo_path)


@patch("subprocess.run")
def test_git_fetch_with_unrecognized_error(
    mock_run: MagicMock,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Ensure `git_fetch` raises an error when the git command fails with an unrecognized error."""
    repo_path = tmp_path / "sample_repo"
    porcelain.init(repo_path)
    repo_name = "origin"
    ref_name = "main"
    mock_run.side_effect = subprocess.CalledProcessError(
        1,
        ["git", "-C", str(repo_path), "fetch", repo_name, ref_name],
        output=None,
        stderr="Unrecognized error",
    )

    # `PhylumCalledProcessError` is initially raised but will ultimately raise `SystemExit`
    with pytest.raises(SystemExit):
        git.git_fetch(repo=repo_name, ref=ref_name, git_c_path=repo_path)

    expected_err_msg = "Fetching failed. Ensure credentials are available to run git commands."
    assert expected_err_msg in caplog.text, "The expected error message was not found in the log"


def test_is_in_git_repo(tmp_path: Path) -> None:
    """Identify when the operating context is within a git repository or not."""
    repo_path = tmp_path / "maybe_a_git_repo"
    repo_path.mkdir()
    assert not git.is_in_git_repo(git_c_path=repo_path), "The path should not be a git repo yet"
    porcelain.init(repo_path)
    assert git.is_in_git_repo(git_c_path=repo_path), "The path should be a git repo"


def test_raises_when_not_in_git_repo(tmp_path: Path) -> None:
    """Ensure an exception is raised when operating outside of a git repository."""
    repo_path = tmp_path / "not_a_git_repo"
    repo_path.mkdir()
    # `PhylumCalledProcessError` is initially raised but will ultimately raise `SystemExit`
    with pytest.raises(SystemExit):
        git.ensure_git_repo_access(git_c_path=repo_path)


def test_ensure_git_repo_access_when_in_git_repo(tmp_path: Path) -> None:
    """Ensure a clean exit when operating within a git repository."""
    repo_path = tmp_path / "safe_repo"
    porcelain.init(repo_path)
    git.ensure_git_repo_access(git_c_path=repo_path)


@patch("subprocess.run")
@patch("phylum.ci.git.is_in_git_repo")
def test_ensure_git_repo_access_with_unsafe_directory(
    mock_is_in_git_repo: MagicMock,
    mock_run: MagicMock,
    tmp_path: Path,
) -> None:
    """Ensure repo directory added to git global config as safe directory when the repo is owned by a different user."""
    repo_path = tmp_path / "unsafe_repo"
    porcelain.init(repo_path)

    # Simulate skipping past the first check for not being in a git repo
    mock_is_in_git_repo.return_value = False

    std_err_msg = f"""
        fatal: detected dubious ownership in repository at '{repo_path}'
        git config --global --add safe.directory '{repo_path}'
        """
    mock_run.side_effect = [
        # Simulate failure of the 1st `run` call that checks for dubious ownership
        subprocess.CalledProcessError(
            128,
            ["git", "-C", str(repo_path), "rev-parse", "--show-toplevel"],
            output=None,
            stderr=cleandoc(std_err_msg),
        ),
        # Use the original function to apply the global git config command
        subprocess.run,
    ]

    git.ensure_git_repo_access(git_c_path=repo_path)

    first_expected_run_call = call(
        ["git", "-C", str(repo_path), "rev-parse", "--show-toplevel"],
        check=True,
        text=True,
        capture_output=True,
        encoding="utf-8",
    )
    second_expected_run_call = call(
        ["git", "-C", str(repo_path), "config", "--global", "--add", "safe.directory", str(repo_path.resolve())],
        check=True,
        text=True,
        capture_output=True,
        encoding="utf-8",
    )
    mock_run.assert_has_calls([first_expected_run_call, second_expected_run_call])


@patch("subprocess.run")
@patch("phylum.ci.git.is_in_git_repo")
def test_ensure_git_repo_access_with_incorrect_token_number(
    mock_is_in_git_repo: MagicMock,
    mock_run: MagicMock,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Ensure error is raised when the number of tokens in the configuration command is incorrect."""
    repo_path = tmp_path / "unsafe_repo"
    porcelain.init(repo_path)

    # Simulate skipping past the first check for not being in a git repo
    mock_is_in_git_repo.return_value = False

    # Simulate the error message including an extra token in the config update command
    git_err_code = 128
    std_err_msg = f"""
        fatal: detected dubious ownership in repository at '{repo_path}'
        git config --global --add safe.directory '{repo_path}' extra_token
        """
    mock_run.side_effect = [
        subprocess.CalledProcessError(
            git_err_code,
            ["git", "-C", str(repo_path), "rev-parse", "--show-toplevel"],
            output=None,
            stderr=cleandoc(std_err_msg),
        ),
    ]

    # `PhylumCalledProcessError` is initially raised but will ultimately raise `SystemExit`
    with pytest.raises(SystemExit) as exc_info:
        git.ensure_git_repo_access(git_c_path=repo_path)
    assert str(exc_info.value) == str(git_err_code)

    # Since the full error message is formatted uniquely, only check for the mismatched count portion of the text
    expected_err_msg_mismatched_count = "9 tokens provided but exactly 8 were expected."
    assert expected_err_msg_mismatched_count in caplog.text, "The expected error message was not found in the log"


@patch("subprocess.run")
@patch("phylum.ci.git.is_in_git_repo")
def test_ensure_git_repo_access_explains_double_failure(
    mock_is_in_git_repo: MagicMock,
    mock_run: MagicMock,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Ensure error is raised when repo is unable to be added as safe directory."""
    repo_path = tmp_path / "unsafe_repo"
    porcelain.init(repo_path)

    # Simulate skipping past the first check for not being in a git repo
    mock_is_in_git_repo.return_value = False

    # Simulate an exception for both `subprocess.run` calls,
    # indicating the repo was unable to be added as a safe directory
    git_err_code = 128
    std_err_msg = f"""
        fatal: detected dubious ownership in repository at '{repo_path}'
        git config --global --add safe.directory '{repo_path}'
        """
    mock_run.side_effect = [
        subprocess.CalledProcessError(
            git_err_code,
            ["git", "-C", str(repo_path), "rev-parse", "--show-toplevel"],
            output=None,
            stderr=cleandoc(std_err_msg),
        ),
        subprocess.CalledProcessError(
            git_err_code,
            ["git", "-C", str(repo_path), "config", "--global", "--add", "safe.directory", str(repo_path)],
            output=None,
            stderr=None,
        ),
    ]

    # `PhylumCalledProcessError` is initially raised but will ultimately raise `SystemExit`
    with pytest.raises(SystemExit) as exc_info:
        git.ensure_git_repo_access(git_c_path=repo_path)
    assert str(exc_info.value) == str(git_err_code)

    expected_err_msg = "Unable to add repository to git global config as safe directory"
    assert expected_err_msg in caplog.text, "The expected error message was not found in the log"


@patch("subprocess.run")
@patch("phylum.ci.git.is_in_git_repo")
def test_ensure_git_repo_access_with_unknown_error(
    mock_is_in_git_repo: MagicMock,
    mock_run: MagicMock,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Ensure `ensure_git_repo_access` raises an error when the git command fails with an unknown error."""
    repo_path = tmp_path / "unrelated_repo"
    repo_path.mkdir()

    # Simulate skipping past the first check for not being in a git repo
    mock_is_in_git_repo.return_value = False

    # Simulate an exception for the `subprocess.run` call that checks for the git root
    mock_run.side_effect = subprocess.CalledProcessError(
        1,
        ["git", "-C", str(repo_path), "rev-parse", "--show-toplevel"],
        output=None,
        stderr="Unknown error",
    )

    # `PhylumCalledProcessError` is initially raised but will ultimately raise `SystemExit`
    with pytest.raises(SystemExit):
        git.ensure_git_repo_access(git_c_path=repo_path)

    expected_err_msg = "Must be operating within git repository, with proper access"
    assert expected_err_msg in caplog.text, "The expected error message was not found in the log"


@patch("subprocess.run")
def test_git_set_remote_head_success(mock_run: MagicMock, tmp_path: Path) -> None:
    """Ensure `git_set_remote_head` successfully sets the remote HEAD in a newly initialized git repository."""
    repo_path = tmp_path / "test_repo"
    porcelain.init(repo_path)
    remote_name = "origin"
    porcelain.remote_add(repo_path, remote_name, url="https://github.com/phylum-dev/phylum-ci.git")

    git.git_set_remote_head(remote=remote_name, git_c_path=repo_path)

    expected_cmd = ["git", "-C", str(repo_path), "remote", "set-head", remote_name, "--auto"]
    mock_run.assert_called_once_with(
        expected_cmd,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


@patch("subprocess.run")
def test_git_set_remote_head_fails_with_incorrect_credentials(
    mock_run: MagicMock,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Ensure `git_set_remote_head` raises an error when setting remote HEAD with incorrect credentials."""
    repo_path = tmp_path / "sample_repo"
    porcelain.init(repo_path)
    remote_name = "origin"
    porcelain.remote_add(repo_path, remote_name, url="https://github.com/phylum-dev/phylum-ci.git")

    mock_run.side_effect = subprocess.CalledProcessError(
        128,
        ["git", "-C", str(repo_path), "remote", "set-head", remote_name, "--auto"],
        output=None,
        stderr="Authentication failed",
    )

    # `PhylumCalledProcessError` is initially raised but will ultimately raise `SystemExit`
    with pytest.raises(SystemExit):
        git.git_set_remote_head(remote=remote_name, git_c_path=repo_path)

    expected_err_msg = "Setting the remote HEAD failed. Ensure credentials are available to run git commands."
    assert expected_err_msg in caplog.text, "The expected error message was not found in the log"


@pytest.mark.parametrize(
    ("raw_default_branch_name", "expected_default_branch_name"),
    [
        ("refs/remotes/origin/main", "main"),
        ("refs/remotes/origin/main\n", "main"),
        ("refs/remotes/origin/master", "master"),
        ("refs/remotes/origin/non_standard", "non_standard"),
    ],
)
@patch("subprocess.run")
def test_git_default_branch_name_success(
    mock_run: MagicMock,
    raw_default_branch_name: str,
    expected_default_branch_name: str,
    tmp_path: Path,
) -> None:
    """Ensure `git_default_branch_name` returns the default branch name successfully with no unusual inputs."""
    repo_path = tmp_path / "test_repo"
    porcelain.init(repo_path)
    remote_name = "origin"
    porcelain.remote_add(repo_path, remote_name, url="https://github.com/phylum-dev/phylum-ci.git")
    mock_run.return_value = MagicMock(stdout=raw_default_branch_name)

    default_branch_name = git.git_default_branch_name(remote=remote_name, git_c_path=repo_path)

    mock_run.assert_called_once_with(
        ["git", "-C", str(repo_path), "symbolic-ref", f"refs/remotes/{remote_name}/HEAD"],
        check=True,
        text=True,
        capture_output=True,
        encoding="utf-8",
    )
    assert (
        default_branch_name == expected_default_branch_name
    ), f"Default branch name should be '{expected_default_branch_name}'"


@patch("subprocess.run")
def test_git_default_branch_name_failure(mock_run: MagicMock, tmp_path: Path) -> None:
    """Ensure `git_default_branch_name` bails when it failed to get the remote HEAD ref even after setting it."""
    repo_path = tmp_path / "test_repo"
    porcelain.init(repo_path)
    remote_name = "origin"
    porcelain.remote_add(repo_path, remote_name, url="https://github.com/phylum-dev/phylum-ci.git")

    mock_run.side_effect = [
        # Simulate a failure to get the remote HEAD ref
        subprocess.CalledProcessError(
            1,
            ["git", "-C", str(repo_path), "symbolic-ref", f"refs/remotes/{remote_name}/HEAD"],
            output=None,
            stderr="remote HEAD ref is not set",
        ),
        # Use the original function to set the remote HEAD
        subprocess.run,
        # Simulate a failure to get the remote HEAD ref after setting the remote HEAD
        subprocess.CalledProcessError(
            1,
            ["git", "-C", str(repo_path), "symbolic-ref", f"refs/remotes/{remote_name}/HEAD"],
            output=None,
            stderr="remote HEAD ref is not set",
        ),
    ]

    # `PhylumCalledProcessError` is initially raised but will ultimately raise `SystemExit`
    with pytest.raises(SystemExit):
        git.git_default_branch_name(remote=remote_name, git_c_path=repo_path)


def test_git_root_dir(tmp_path: Path) -> None:
    """Ensure the correct git root directory is returned, regardless of depth."""
    repo_path = tmp_path / "toplevel"
    nested_path = repo_path / "sub_dir_1" / "sub_dir_2"
    nested_path.mkdir(parents=True)
    porcelain.init(repo_path)
    assert git.git_root_dir(git_c_path=repo_path) == repo_path
    assert git.git_root_dir(git_c_path=nested_path) == repo_path


def test_git_root_dir_not_a_git_repo(tmp_path: Path) -> None:
    """Ensure an error is raised when not operating within the context of a git repo."""
    repo_path = tmp_path / "not_a_git_repo"
    # Create the directory but don't initialize it as a git repo
    repo_path.mkdir()
    # `PhylumCalledProcessError` is initially raised but will ultimately raise `SystemExit`
    with pytest.raises(SystemExit):
        git.git_root_dir(git_c_path=repo_path)


def test_git_current_branch_name_within_git_repo(tmp_path: Path) -> None:
    """Ensure `git_current_branch_name` returns the correct current branch name when inside a git repository."""
    repo_path = tmp_path / "test_repo"
    porcelain.init(repo_path)
    expected_branch_name = porcelain.active_branch(repo_path).decode()
    current_branch = git.git_current_branch_name(git_c_path=repo_path)
    assert current_branch == expected_branch_name, f"The current branch name should be '{expected_branch_name}'"


@patch("subprocess.run")
def test_git_current_branch_name_fails_with_error(mock_run: MagicMock, tmp_path: Path) -> None:
    """Ensure `git_current_branch_name` raises an error when command fails."""
    repo_path = tmp_path / "test_repo"
    porcelain.init(repo_path)

    mock_run.side_effect = subprocess.CalledProcessError(
        1,
        ["git", "-C", str(repo_path), "branch", "--show-current"],
        output=None,
        stderr="Failed to show current branch",
    )

    # `PhylumCalledProcessError` is initially raised but will ultimately raise `SystemExit`
    with pytest.raises(SystemExit):
        git.git_current_branch_name(git_c_path=repo_path)


def test_git_hash_object_success(tmp_path: Path) -> None:
    """Ensure `git_hash_object` returns the correct hash for a file in an initialized git repository."""
    repo_path = tmp_path / "test_repo"
    porcelain.init(repo_path)
    test_file_path = repo_path / "test_file2.txt"
    test_file_path.write_text("test content")

    # The Dulwich `porcelain` module doesn't provide a `hash-object` function, so it was manually computed here.
    # The content of the file is what matters and the name and path are not relevant for the hash computation.
    expected_hash = "08cf6101416f0ce0dda3c80e627f333854c4085c"

    hash_object = git.git_hash_object(object_path=test_file_path, git_c_path=repo_path)

    assert hash_object == expected_hash, f"Hash object should be '{expected_hash}'"


@patch("subprocess.run")
def test_git_hash_object_fails_with_error(mock_run: MagicMock, tmp_path: Path) -> None:
    """Ensure `git_hash_object` raises an error when the git command fails."""
    repo_path = tmp_path / "test_repo"
    porcelain.init(repo_path)
    test_file_path = repo_path / "test_file.txt"
    test_file_path.write_text("test content")

    mock_run.side_effect = subprocess.CalledProcessError(
        1,
        ["git", "-C", str(repo_path), "hash-object", str(test_file_path.resolve())],
        output=None,
        stderr="Hashing failed",
    )

    # `PhylumCalledProcessError` is initially raised but will ultimately raise `SystemExit`
    with pytest.raises(SystemExit):
        git.git_hash_object(object_path=test_file_path, git_c_path=repo_path)


def test_raises_runtime_error_when_no_remotes(tmp_path: Path) -> None:
    """Ensure a `RuntimeError` is raised when there are no remotes configured."""
    repo_path = tmp_path / "no_remote_repo"
    porcelain.init(repo_path)
    with pytest.raises(RuntimeError) as exc_info:
        git.git_remote(git_c_path=repo_path)
    assert str(exc_info.value) == "No git remotes configured"


def test_git_remote_single_remote(tmp_path: Path) -> None:
    """Ensure `git_remote` correctly identifies and returns the single configured remote."""
    repo_path = tmp_path / "single_remote_repo"
    porcelain.init(repo_path)
    porcelain.remote_add(repo_path, "origin", url="https://github.com/phylum-dev/phylum-ci.git")
    remote = git.git_remote(git_c_path=repo_path)
    assert remote == "origin", "The single remote should be found correctly"


def test_git_remote_with_trailing_slash(tmp_path: Path) -> None:
    """Ensure `git_remote` correctly retrieves the remote when `git_c_path` includes trailing slash."""
    repo_path = tmp_path / "repo_with_trailing_slash/"
    porcelain.init(repo_path)
    porcelain.remote_add(repo_path, "origin", url="https://github.com/phylum-dev/phylum-ci.git")
    remote = git.git_remote(git_c_path=repo_path)
    assert remote == "origin", "The remote should be found correctly"


def test_git_remote_from_nested_subdirectory(tmp_path: Path) -> None:
    """Ensure `git_remote` correctly identifies and returns the single configured remote from a nested subdirectory."""
    repo_path = tmp_path / "nested_remote_repo"
    nested_path = repo_path / "sub_dir_1" / "sub_dir_2"
    nested_path.mkdir(parents=True)
    porcelain.init(repo_path)
    porcelain.remote_add(repo_path, "origin", url="https://github.com/phylum-dev/phylum-ci.git")
    remote = git.git_remote(git_c_path=nested_path)
    assert remote == "origin", "The single remote should be found correctly from a nested subdirectory"


def test_git_remote_after_add_and_remove(tmp_path: Path) -> None:
    """Ensure `git_remote` correctly identifies the remote after adding and removing a remote."""
    repo_path = tmp_path / "repo_with_add_remove_remote"
    porcelain.init(repo_path)
    porcelain.remote_add(repo_path, "origin", url="https://github.com/phylum-dev/phylum-ci.git")
    porcelain.remote_remove(repo.Repo(repo_path), "origin")
    with pytest.raises(RuntimeError) as exc_info:
        git.git_remote(git_c_path=repo_path)
    assert str(exc_info.value) == "No git remotes configured"

    # Re-add the remote to ensure it is found correctly
    porcelain.remote_add(repo_path, "origin", url="https://github.com/phylum-dev/phylum-ci.git")
    remote = git.git_remote(git_c_path=repo_path)
    assert remote == "origin", "The single remote should be found correctly"


def test_raises_when_subprocess_fails(tmp_path: Path) -> None:
    """Ensure `PhylumCalledProcessError` is raised when `subprocess.run` fails in `git_remote`."""
    repo_path = tmp_path / "remote_failure_repo"
    porcelain.init(repo_path)
    with (
        # `PhylumCalledProcessError` is initially raised but will ultimately raise `SystemExit`
        pytest.raises(SystemExit),
        patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, ["git", "remote"])),
    ):
        git.git_remote(git_c_path=repo_path)


def test_raises_runtime_error_when_multiple_remotes(tmp_path: Path) -> None:
    """Ensure a `RuntimeError` is raised when there are multiple remotes configured."""
    repo_path = tmp_path / "multiple_remotes_repo"
    porcelain.init(repo_path)
    porcelain.remote_add(repo_path, "origin", url="https://github.com/phylum-dev/phylum-ci.git")
    porcelain.remote_add(repo_path, "upstream", url="https://github.com/org/repo.git")
    with pytest.raises(RuntimeError) as exc_info:
        git.git_remote(git_c_path=repo_path)
    assert str(exc_info.value) == "Only one git remote is supported at this time"


def test_git_remote_with_special_characters_in_url(tmp_path: Path) -> None:
    """Ensure `git_remote` correctly identifies and returns the remote when the URL contains special characters."""
    repo_path = tmp_path / "special_char_remote_repo"
    porcelain.init(repo_path)
    special_url = "https://user:pass@github.com/phylum-dev/phylum-ci.git"
    porcelain.remote_add(repo_path, "origin", url=special_url)
    remote = git.git_remote(git_c_path=repo_path)
    assert remote == "origin", "The single remote should be found correctly"


def test_git_remote_with_non_origin_remote(tmp_path: Path) -> None:
    """Ensure `git_remote` correctly identifies and returns the single configured remote that is not 'origin'."""
    repo_path = tmp_path / "non_origin_remote_repo"
    porcelain.init(repo_path)
    porcelain.remote_add(repo_path, "upstream", url="https://github.com/org/repo.git")
    remote = git.git_remote(git_c_path=repo_path)
    assert remote == "upstream", "The single remote should be found correctly"


def test_git_worktree_success(tmp_path: Path) -> None:
    """Ensure `git_worktree` creates and removes a git worktree successfully."""
    repo_path = tmp_path / "test_repo"
    porcelain.init(repo_path)
    # Create a commit to ensure a worktree can be created
    commit = porcelain.commit(str(repo_path), message="Initial commit").decode()

    initial_worktrees = [str(repo_path)]
    assert initial_worktrees == [
        wt.path for wt in porcelain.worktree_list(str(repo_path))
    ], "No additional worktrees should exist initially"

    with git.git_worktree(commit, git_c_path=repo_path) as worktree_path:
        assert worktree_path.is_dir(), "Worktree path should be a directory"
        assert sorted([str(repo_path), str(worktree_path)]) == sorted(
            wt.path for wt in porcelain.worktree_list(str(repo_path))
        ), "New worktree should be listed"

    assert initial_worktrees == [
        wt.path for wt in porcelain.worktree_list(str(repo_path))
    ], "No additional worktrees should exist after the context manager exits"


def test_git_worktree_failure_to_create_worktree(tmp_path: Path) -> None:
    """Ensure `git_worktree` bails with an error when it can't create a git worktree successfully."""
    repo_path = tmp_path / "test_repo"
    porcelain.init(repo_path)
    # Create a commit to ensure a worktree could be created
    commit = porcelain.commit(str(repo_path), message="Initial commit").decode()
    # Instead of hard-coding a bad value for the commit, reverse the good value
    invalid_commit = commit[::-1]
    # `PhylumCalledProcessError` is initially raised but will ultimately raise `SystemExit`
    with pytest.raises(SystemExit), git.git_worktree(invalid_commit, git_c_path=repo_path):
        # Unreachable since the `git_worktree` context manager should fail first
        ...


@patch("subprocess.run")
def test_remove_git_worktree_failure_logs_warning(
    mock_run: MagicMock,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Ensure `remove_git_worktree` logs a warning message when it fails to remove the worktree."""
    repo_path = tmp_path / "test_repo"
    desired_worktree_path = tmp_path / "worktree"
    porcelain.init(repo_path)
    commit = porcelain.commit(str(repo_path), message="Initial commit").decode()
    created_worktree_path = porcelain.worktree_add(str(repo_path), str(desired_worktree_path), commit)

    assert created_worktree_path == str(desired_worktree_path), "Worktree should have been created"

    mock_run.side_effect = subprocess.CalledProcessError(
        1,
        ["git", "-C", str(repo_path), "worktree", "remove", "--force", str(created_worktree_path)],
        output=None,
        stderr="Unable to remove worktree",
    )

    with caplog.at_level(logging.WARNING):
        git.remove_git_worktree(worktree=desired_worktree_path, git_c_path=repo_path)

    expected_err_msg = "Unable to remove the git worktree. Try running `git worktree prune` manually."
    assert expected_err_msg in caplog.text
