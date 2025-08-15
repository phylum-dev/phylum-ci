"""Place test package constants here."""

import os
import pathlib

import pytest
import tomli

HERE = pathlib.Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
PYPROJECT_TOML_PATH = PROJECT_ROOT / "pyproject.toml"

with PYPROJECT_TOML_PATH.open("rb") as f:
    PYPROJECT = tomli.load(f)

# This pytest fixture is used to mark tests that should only run in a CI environment (e.g., too slow for local testing)
only_run_if_ci = pytest.mark.skipif(not os.getenv("CI"), reason="Test should only run in CI")
