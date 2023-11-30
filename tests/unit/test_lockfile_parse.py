"""Test the `deps` property from the `Depfile` class."""

from pathlib import Path
from subprocess import CalledProcessError
from unittest.mock import MagicMock, patch

from phylum.ci.common import CLIExitCode, LockfileEntry, PackageDescriptor
from phylum.ci.depfile import Depfile, DepfileType


@patch("phylum.ci.depfile._is_sandbox_possible")
@patch("subprocess.run")
def test_deps(mock_run: MagicMock, mock_sandbox_check: MagicMock) -> None:
    """Test the `deps` property of the `Depfile` class."""
    # Prepare the mocks to skip running the subprocess calls since the Phylum CLI may not be installed and
    # we don't want to enforce that it is for a unit test. It will be given a dummy path value instead.
    mock_sandbox_check.return_value = True
    mock_run.return_value.stdout = """
    [
        {
            "name": "quote",
            "version": "1.0.21",
            "type": "cargo",
            "lockfile": "Cargo.lock"
        },
        {
            "name": "example",
            "version": "0.1.0",
            "type": "npm"
        }
    ]
    """

    expected_num_packages = 2
    expected_cargo_package = PackageDescriptor("quote", "1.0.21", "cargo", "Cargo.lock")
    expected_npm_package = PackageDescriptor("example", "0.1.0", "npm")
    depfile_path = Path("Cargo.lock")
    provided_lockfile_type = "cargo"
    cli_path = Path("dummy_cli_path")
    lockfile_entry = LockfileEntry(depfile_path, provided_lockfile_type)

    # Test the `deps` property with lockfile generation and sandbox enabled
    depfile = Depfile(lockfile_entry, cli_path, DepfileType.LOCKFILE)
    packages = depfile.deps
    assert len(packages) == expected_num_packages
    assert expected_cargo_package in packages
    assert expected_npm_package in packages
    mock_sandbox_check.assert_called_once()
    mock_run.assert_called_once_with(
        [str(depfile.cli_path), "parse", "--lockfile-type", provided_lockfile_type, str(depfile.path)],
        cwd=Path.cwd(),
        check=True,
        capture_output=True,
        text=True,
    )

    # Test the `deps` property with lockfile generation and sandbox disabled
    mock_sandbox_check.reset_mock()
    mock_run.reset_mock()
    cmd = [
        str(depfile.cli_path),
        "parse",
        "--lockfile-type",
        provided_lockfile_type,
        "--skip-sandbox",
        "--no-generation",
        str(depfile.path),
    ]
    mock_run.side_effect = CalledProcessError(returncode=CLIExitCode.MANIFEST_WITHOUT_GENERATION.value, cmd=cmd)
    assert isinstance(mock_run.side_effect, CalledProcessError)
    mock_sandbox_check.return_value = False
    depfile = Depfile(lockfile_entry, cli_path, DepfileType.LOCKFILE, no_gen=True)
    packages = depfile.deps
    assert packages == []
    mock_sandbox_check.assert_called_once()
    mock_run.assert_called_once_with(cmd, cwd=Path.cwd(), check=True, capture_output=True, text=True)
