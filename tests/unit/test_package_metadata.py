"""Test the package metadata."""

import sys
from typing import Any

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import Version

from phylum import PKG_NAME, PKG_SUMMARY, __author__, __email__, __version__
from tests.constants import PYPROJECT

PROJECT_TABLE: dict[str, Any] = PYPROJECT.get("project", {})


def test_project_version() -> None:
    """Ensure the source version can be normalized as specified in PEP-440."""
    package_version = Version(__version__)
    source_version = Version(PROJECT_TABLE.get("version", "0.0.0"))
    assert package_version == source_version


def test_python_version() -> None:
    """Ensure the python version used to test is a supported version."""
    supported_minor_versions = (10, 11, 12, 13)
    python_version = sys.version_info
    acceptable_python_major_version = 3
    assert python_version.major == acceptable_python_major_version, "Only Python 3 is supported"
    assert python_version.minor in supported_minor_versions, "Attempting to run unsupported Python version"


def test_author_email_metadata() -> None:
    """Ensure the project and package metadata for author and email match and are correct."""
    assert __author__ == "Veracode Inc.", "The company name should be used instead of individual developers"
    assert "," not in __author__, "Author name must not contain commas (according to pyproject.toml spec)"
    assert __email__ == "dl-phylum-engineering@veracode.com", "The engineering distribution list should be used"
    poetry_authors: list = PROJECT_TABLE.get("authors", [])
    assert len(poetry_authors) == 1, "There should only be one author - the company, with it's engineering group email"
    poetry_author: dict = poetry_authors[0]
    assert __author__ == poetry_author.get("name"), "Package author name should be defined in pyproject.toml only"
    assert __email__ == poetry_author.get("email"), "Package author email should be defined in pyproject.toml only"


def test_package_name() -> None:
    """Ensure the package name is traced through from the pyproject.toml definition."""
    expected_pkg_name: str = PROJECT_TABLE.get("name", "")
    assert expected_pkg_name == PKG_NAME, "The package name should be defined in pyproject.toml only"


def test_package_description() -> None:
    """Ensure the package description is traced through from the pyproject definition."""
    expected_pkg_desc: str = PROJECT_TABLE.get("description", "")
    assert expected_pkg_desc == PKG_SUMMARY, "The package description should be defined in pyproject.toml only"


def test_build_system() -> None:
    """Ensure the PEP 517/518 build system has not changed without explicit review.

    Arbitrary code execution can occur when building/installing packages from source distributions. This test guards
    against changes to the established/vetted build system. There may be legitimate times to change the build system
    requirements and/or backend, but those changes will be more apparent in code reviews since this test will also have
    to change. Changes to the values in the `pyproject.toml` file may be subtle and go unnoticed. In the worst case, it
    is possible for the values to be changed to malicious entries that seek to cause harm in CI systems.
    """
    # NOTE: Changes to these values should be inspected closely!
    expected_build_req_name = "poetry-core"
    expected_build_req_spec = SpecifierSet(">=2.1,<3.0")
    expected_build_backend = "poetry.core.masonry.api"

    build_system: dict[str, Any] = PYPROJECT.get("build-system", {})

    requires: list = build_system.get("requires", [])
    assert len(requires) == 1, "There should be only one build system requirement"

    build_req = Requirement(requires[0])
    assert expected_build_req_name == build_req.name, f"This package uses `{expected_build_req_name}` for building"
    assert expected_build_req_spec == build_req.specifier, f"Possible breaking version of `{expected_build_req_name}`"

    build_backend: str = build_system.get("build-backend", "")
    assert expected_build_backend == build_backend, "Be wary if the build backend changes"
