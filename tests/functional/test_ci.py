""""Test the phylum-ci command line interface (CLI)."""
import subprocess
import sys

from phylum import __version__
from phylum.ci import SCRIPT_NAME

from ..constants import PYPROJECT


def test_run_as_module():
    """Ensure the CLI can be called as a module.

    This is the `python -m <module_name>` format to "run library module as a script."
    NOTE: The <module_name> is specified as the dotted path to the package where the `__main__.py` module exists.
    """
    cmd = f"{sys.executable} -m phylum.ci --help".split()
    ret = subprocess.run(cmd)
    assert ret.returncode == 0, "Running the package as a module failed"


def test_run_as_script():
    """Ensure the CLI can be called by it's script entry point."""
    scripts = PYPROJECT.get("tool", {}).get("poetry", {}).get("scripts", {})
    assert scripts, "There should be at least one script entry point"
    assert SCRIPT_NAME in scripts, f"The {SCRIPT_NAME} script should be a defined entry point"
    ret = subprocess.run([SCRIPT_NAME, "-h"])
    assert ret.returncode == 0, f"{SCRIPT_NAME} entry point failed"


def test_version_option():
    """Ensure the correct program name and version is displayed when using the `--version` option."""
    # The argparse module adds a newline to the output
    expected_output = f"{SCRIPT_NAME} {__version__}\n"
    cmd = f"{sys.executable} -m phylum.ci --version".split()
    ret = subprocess.run(cmd, capture_output=True, encoding="utf-8")
    assert not ret.stderr, "Nothing should be written to stderr"
    assert ret.returncode == 0, "A non-successful return code was provided"
    assert ret.stdout == expected_output, "Output did not match expected input"
