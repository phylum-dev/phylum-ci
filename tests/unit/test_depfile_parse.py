"""Test the `deps` property from the `Depfile` class."""

from pathlib import Path
from subprocess import CalledProcessError
from unittest.mock import MagicMock, patch

from phylum.ci.common import CLIExitCode, DepfileEntry, Package
from phylum.ci.depfile import Depfile, DepfileType


@patch("phylum.ci.depfile._is_sandbox_possible")
@patch("subprocess.run")
def test_deps(mock_run: MagicMock, mock_sandbox_check: MagicMock) -> None:
    """Test the `deps` property of the `Depfile` class."""
    # Prepare the mocks to skip running the subprocess calls since the Phylum CLI may not be installed and
    # we don't want to enforce that it is for a unit test. It will be given a dummy path value instead.
    mock_sandbox_check.return_value = True
    depfile_path = Path("dummy.spdx.json")
    mock_run.return_value.stdout = f"""
    [
        {{
            "name": "quote",
            "version": "1.0.21",
            "type": "cargo",
            "lockfile": "{depfile_path}"
        }},
        {{
            "name": "example",
            "version": "0.1.0",
            "type": "npm",
            "lockfile": "{depfile_path}"
        }}
    ]
    """

    provided_depfile_type = "spdx"
    depfile_entry = DepfileEntry(depfile_path, provided_depfile_type)
    cli_path = Path("dummy_cli_path")
    expected_num_packages = 2
    expected_cargo_package = Package("quote", "1.0.21", "cargo", str(depfile_path))
    expected_npm_package = Package("example", "0.1.0", "npm", str(depfile_path))

    # Test the `deps` property with lockfile generation and sandbox enabled
    depfile = Depfile(depfile_entry, cli_path, DepfileType.LOCKFILE)
    packages = depfile.deps
    assert len(packages) == expected_num_packages
    assert expected_cargo_package in packages
    assert expected_npm_package in packages
    assert all(pkg.lockfile == str(depfile_path) for pkg in packages)
    mock_sandbox_check.assert_called_once()
    mock_run.assert_called_once_with(
        [str(depfile.cli_path), "parse", "--type", provided_depfile_type, str(depfile.path)],
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
        "--type",
        provided_depfile_type,
        "--skip-sandbox",
        "--no-generation",
        str(depfile.path),
    ]
    mock_run.side_effect = CalledProcessError(returncode=CLIExitCode.MANIFEST_WITHOUT_GENERATION.value, cmd=cmd)
    assert isinstance(mock_run.side_effect, CalledProcessError)
    mock_sandbox_check.return_value = False
    depfile = Depfile(depfile_entry, cli_path, DepfileType.LOCKFILE, disable_lockfile_generation=True)
    packages = depfile.deps
    assert packages == []
    mock_sandbox_check.assert_called_once()
    mock_run.assert_called_once_with(cmd, cwd=Path.cwd(), check=True, capture_output=True, text=True)
