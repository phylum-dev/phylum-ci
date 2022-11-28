""""Test the phylum-init command line interface (CLI)."""
import subprocess
import sys
from pathlib import Path

from phylum import __version__
from phylum.init import SCRIPT_NAME, sig
from phylum.init.cli import save_file_from_url

from ..constants import PYPROJECT


def test_run_as_module():
    """Ensure the CLI can be called as a module.

    This is the `python -m <module_name>` format to "run library module as a script."
    NOTE: The <module_name> is specified as the dotted path to the package where the `__main__.py` module exists.
    """
    cmd = f"{sys.executable} -m phylum.init --help".split()
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
    cmd = f"{sys.executable} -m phylum.init --version".split()
    ret = subprocess.run(cmd, capture_output=True, encoding="utf-8")
    assert not ret.stderr, "Nothing should be written to stderr"
    assert ret.returncode == 0, "A non-successful return code was provided"
    assert ret.stdout == expected_output, "Output did not match expected input"


def test_phylum_pubkey_is_constant(tmp_path):
    """Ensure the RSA public key in use by Phylum has not changed."""
    phylum_pubkey_url = "https://raw.githubusercontent.com/phylum-dev/cli/main/scripts/signing-key.pub"
    downloaded_key_path: Path = tmp_path / "signing-key.pub"
    save_file_from_url(phylum_pubkey_url, downloaded_key_path)
    assert downloaded_key_path.read_bytes() == sig.PHYLUM_RSA_PUBKEY, "The key should not be changing"
