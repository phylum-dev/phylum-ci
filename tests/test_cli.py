""""Test the command line interface (CLI)."""

import subprocess
import sys

from phylum import PKG_NAME, __version__

from .constants import PYPROJECT


def test_run_as_module():
    """Ensure the CLI can be called as a module.

    This is the `python -m <module_name>` format to "run library module as a script."
    NOTE: The <module_name> must be specified with an underscore, even if the corresponding
          script entry point is specified with a dash.
    """
    cmd_line = [sys.executable, "-m", "phylum", "--help"]
    ret = subprocess.run(cmd_line)
    assert ret.returncode == 0, "Running the package as a module failed"


def test_run_as_script():
    """Ensure the CLI can be called by it's script entry point."""
    scripts = PYPROJECT.get("tool", {}).get("poetry", {}).get("scripts", {})
    assert scripts, "There should be at least one script entry point"
    for script in scripts:
        ret = subprocess.run([script, "-h"])
        assert ret.returncode == 0, f"{script} entry point failed"


def test_version_option():
    """Ensure the correct program name and version is displayed when using the `--version` option."""
    # The argparse module adds a newline to the output
    expected_output = f"{PKG_NAME} {__version__}\n"
    cmd_line = [sys.executable, "-m", "phylum", "--version"]
    ret = subprocess.run(cmd_line, check=True, capture_output=True, encoding="utf-8")
    assert ret.stdout == expected_output, "Output did not match expected input"
    assert not ret.stderr, "Nothing should be written to stderr"
    assert ret.returncode == 0, "A non-successful return code was provided"
