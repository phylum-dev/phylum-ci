"""Place test package constants here."""
import pathlib

import tomli

HERE = pathlib.Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
PYPROJECT_TOML_PATH = PROJECT_ROOT / "pyproject.toml"

with open(PYPROJECT_TOML_PATH, "rb") as f:
    PYPROJECT = tomli.load(f)
