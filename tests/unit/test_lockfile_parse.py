"""Test the lockfile current_lockfile_packages function."""

from pathlib import Path
from unittest.mock import patch

from phylum.ci.common import PackageDescriptor
from phylum.ci.lockfile import Lockfile

EXPECTED_NUM_PACKAGES = 2


@patch("subprocess.run")
def test_current_lockfile_packages(mock_run):
    """Test the `current_lockfile_packages` function of the Lockfile class."""
    # Prepare the mock
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

    lockfile_path = Path("Cargo.lock")
    cli_path = Path("dummy_cli_path")
    lockfile = Lockfile(lockfile_path, cli_path, None)

    # Test the current_lockfile_packages method
    packages = lockfile.current_lockfile_packages()
    expected_cargo_package = PackageDescriptor("quote", "1.0.21", "cargo", "Cargo.lock")
    expected_npm_package = PackageDescriptor("example", "0.1.0", "npm")

    assert len(packages) == EXPECTED_NUM_PACKAGES
    assert expected_cargo_package in packages
    assert expected_npm_package in packages

    # Ensure the mock was called correctly
    mock_run.assert_called_once_with(
        [str(lockfile.cli_path), "parse", str(lockfile.path)],
        check=True,
        capture_output=True,
        text=True,
    )
