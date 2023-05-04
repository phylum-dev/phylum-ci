"""Test the package metadata."""

import sys

from packaging.requirements import Requirement
from packaging.version import Version

from phylum import PKG_NAME, PKG_SUMMARY, __author__, __email__, __version__
from tests.constants import PYPROJECT


def test_project_version():
    """Ensure the source version can be normalized as specified in PEP-440."""
    package_version = Version(__version__)
    source_version = Version(PYPROJECT.get("tool", {}).get("poetry", {}).get("version", "0.0.0"))
    assert package_version == source_version


def test_python_version():
    """Ensure the python version used to test is a supported version."""
    supported_minor_versions = (8, 9, 10, 11)
    python_version = sys.version_info
    acceptable_python_major_version = 3
    assert python_version.major == acceptable_python_major_version, "Only Python 3 is supported"
    assert python_version.minor in supported_minor_versions, "Attempting to run unsupported Python version"


def test_author_email_metadata():
    """Ensure the project and package metadata for author and email match and are correct."""
    assert __author__ == "Phylum, Inc.", "The company name should be used instead of individual developers"
    assert __email__ == "engineering@phylum.io", "The engineering group email account should be used"
    # Package authors in Poetry are specified as a list of "name <email>" entries
    expected_poetry_author = f"{__author__} <{__email__}>"
    poetry_authors = PYPROJECT.get("tool", {}).get("poetry", {}).get("authors", [])
    assert expected_poetry_author in poetry_authors, "Package author/email should be defined in pyproject.toml only"
    assert len(poetry_authors) == 1, "There should only be one author - the company, with it's engineering group email"


def test_package_name():
    """Ensure the package name is traced through from the pyproject.toml definition."""
    expected_pkg_name = PYPROJECT.get("tool", {}).get("poetry", {}).get("name", "")
    assert expected_pkg_name == PKG_NAME, "The package name should be defined in pyproject.toml only"


def test_package_description():
    """Ensure the package description is traced through from the pyproject definition."""
    expected_pkg_desc = PYPROJECT.get("tool", {}).get("poetry", {}).get("description", "")
    assert expected_pkg_desc == PKG_SUMMARY, "The package description should be defined in pyproject.toml only"


def test_build_system():
    """Ensure the PEP 517/518 build system has not changed without explicit review.

    Arbitrary code execution can occur when building/installing packages from source distributions. This test guards
    against changes to the established/vetted build system. There may be legitimate times to change the build system
    requirements and/or backend, but those changes will be more apparent in code reviews since this test will also have
    to change. Changes to the values in the `pyproject.toml` file may be subtle and go unnoticed. In the worst case, it
    is possible for the values to be changed to malicious entries that seek to cause harm in CI systems.
    """
    # NOTE: Changes to these values should be inspected closely!
    expected_build_requirement = "poetry-core"
    expected_build_backend = "poetry.core.masonry.api"

    requires = PYPROJECT.get("build-system", {}).get("requires", [])
    assert len(requires) == 1, "There should be only one build system requirement"
    req = Requirement(requires[0])
    assert expected_build_requirement == req.name, "This package uses `poetry-core` for building"
    build_backend = PYPROJECT.get("build-system", {}).get("build-backend")
    assert expected_build_backend == build_backend, "Be wary if the build backend changes"
