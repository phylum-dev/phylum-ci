import pathlib
import sys

import tomli
from phylum_ci import __version__

HERE = pathlib.Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
PYPROJECT_TOML_PATH = PROJECT_ROOT / "pyproject.toml"


def test_version():
    """Ensure the package version string matches the reported project version."""
    with open(PYPROJECT_TOML_PATH, "rb") as f:
        pyproject = tomli.load(f)
    pyproject_version = pyproject.get("tool", {}).get("poetry", {}).get("version")
    assert __version__ == pyproject_version


def test_python_version():
    """Ensure the python version used to test is a supported version."""
    supported_minor_versions = (7, 8, 9)
    python_version = sys.version_info
    assert python_version.major == 3
    assert python_version.minor in supported_minor_versions
