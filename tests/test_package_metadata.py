"""Test the package metadata."""

import pathlib
import sys

import tomli
from phylum_ci import PKG_NAME, PKG_SUMMARY, __author__, __email__, __version__

HERE = pathlib.Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
PYPROJECT_TOML_PATH = PROJECT_ROOT / "pyproject.toml"

with open(PYPROJECT_TOML_PATH, "rb") as f:
    PYPROJECT = tomli.load(f)


def test_project_version():
    """Ensure the source version matches the PEP-440 post-normalization format given to the package."""
    package_version = __version__
    source_version = PYPROJECT.get("tool", {}).get("poetry", {}).get("version")
    assert package_version == source_version, "Source version should match PEP-440 post-normalization format"


def test_python_version():
    """Ensure the python version used to test is a supported version."""
    supported_minor_versions = (7, 8, 9, 10)
    python_version = sys.version_info
    assert python_version.major == 3, "Only Python 3 is supported"
    assert python_version.minor in supported_minor_versions


def test_author_email_metadata():
    """Ensure the project and package metadata for author and email match and are correct."""
    assert __author__ == "Phylum, Inc.", "The company name should be used instead of individual developers"
    assert __email__ == "engineering@phylum.io", "The engineering group email account should be used"
    # Package authors in Poetry are specified as a list of "name <email>" entries
    expected_poetry_author = f"{__author__} <{__email__}>"
    poetry_authors = PYPROJECT.get("tool", {}).get("poetry", {}).get("authors", [])
    assert expected_poetry_author in poetry_authors
    assert len(poetry_authors) == 1, "There should only be one author - the company, with it's engineering group email"


def test_package_name():
    """Ensure the package name is traced through from the pyproject.toml definition to the script entrypoint usage."""
    expected_pkg_name = PYPROJECT.get("tool", {}).get("poetry", {}).get("name", "")
    assert expected_pkg_name == PKG_NAME


def test_package_description():
    """Ensure the package description is traced through from the pyproject definition to the script entrypoint usage."""
    expected_pkg_name = PYPROJECT.get("tool", {}).get("poetry", {}).get("description", "")
    assert expected_pkg_name == PKG_SUMMARY
