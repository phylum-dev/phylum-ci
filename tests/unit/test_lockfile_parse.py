"""Test the `deps` property from the `Depfile` class."""

from pathlib import Path
from unittest.mock import patch

from phylum.ci.common import LockfileEntry, PackageDescriptor
from phylum.ci.depfile import Depfile, DepfileType

EXPECTED_NUM_PACKAGES = 2


@patch("subprocess.run")
def test_deps(mock_run):
    """Test the `deps` property of the `Depfile` class."""
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

    depfile_path = Path("Cargo.lock")
    provided_lockfile_type = "cargo"
    cli_path = Path("dummy_cli_path")
    lockfile_entry = LockfileEntry(depfile_path, provided_lockfile_type)
    depfile = Depfile(lockfile_entry, cli_path, DepfileType.LOCKFILE)

    # Test the `deps` property
    packages = depfile.deps
    expected_cargo_package = PackageDescriptor("quote", "1.0.21", "cargo", "Cargo.lock")
    expected_npm_package = PackageDescriptor("example", "0.1.0", "npm")

    assert len(packages) == EXPECTED_NUM_PACKAGES
    assert expected_cargo_package in packages
    assert expected_npm_package in packages

    # Ensure the mock was called correctly
    mock_run.assert_called_once_with(
        [str(depfile.cli_path), "parse", "--lockfile-type", provided_lockfile_type, str(depfile.path)],
        cwd=Path.cwd(),
        check=True,
        capture_output=True,
        text=True,
    )
