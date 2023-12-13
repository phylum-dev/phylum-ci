"""Test the `DepfileEntry` dataclass."""

from pathlib import Path

import pytest

from phylum.ci.common import DepfileEntry


def test_path_entries_are_paths(tmp_path: Path) -> None:
    """Ensure the path input gets converted to a properly resolved `Path`."""
    depfile_path_as_path = tmp_path / "requirements.txt"
    depfile_path_as_str = str(depfile_path_as_path)
    depfile_path_as_bytes = bytes(depfile_path_as_path)

    depfile_entry = DepfileEntry(depfile_path_as_str, type="pip")
    assert isinstance(depfile_entry.path, Path)
    assert depfile_entry.path == depfile_path_as_path

    depfile_entry = DepfileEntry(depfile_path_as_path, type="pip")
    assert isinstance(depfile_entry.path, Path)
    assert depfile_entry.path == depfile_path_as_path

    with pytest.raises(TypeError):
        depfile_entry = DepfileEntry(depfile_path_as_bytes, type="pip")


def test_repr_format() -> None:
    """Ensure the `repr` form is displayed correctly."""
    depfile_name = "requirements.txt"
    depfile_path_as_path = Path.cwd() / depfile_name
    depfile_entry = DepfileEntry(depfile_path_as_path, type="pip")
    assert depfile_entry.path == depfile_path_as_path.resolve()
    assert repr(depfile_entry) == depfile_name
    assert f"{depfile_entry!r}" == depfile_name


def test_entries_compare_equal() -> None:
    """Ensure entries with specific types compare equal."""
    specific_python_entry_1 = DepfileEntry("requirements.txt", "pip")
    specific_python_entry_2 = DepfileEntry("requirements.txt", "pip")
    assert specific_python_entry_1 == specific_python_entry_2

    specific_python_entry_3 = DepfileEntry("poetry.lock", type="poetry")
    assert specific_python_entry_1 != specific_python_entry_3


def test_entries_hash_equal() -> None:
    """Ensure entries with specific types hash equal."""
    specific_python_entry_1 = DepfileEntry("requirements.txt", "pip")
    specific_python_entry_2 = DepfileEntry("requirements.txt", "pip")
    assert hash(specific_python_entry_1) == hash(specific_python_entry_2)

    specific_python_entry_3 = DepfileEntry("poetry.lock", type="poetry")
    assert hash(specific_python_entry_1) != hash(specific_python_entry_3)


def test_auto_entries_compare_equal() -> None:
    """Ensure entries with the `auto` type compare equal to entries with a specific type."""
    depfile = Path("requirements.txt")
    entry_with_default_type = DepfileEntry(depfile)
    entry_with_specified_type = DepfileEntry(depfile, type="pip")
    assert entry_with_default_type == entry_with_specified_type


def test_auto_entries_hash_equal() -> None:
    """Ensure entries with the `auto` type hash equal to entries with a specific type."""
    depfile = Path("requirements.txt")
    entry_with_default_type = DepfileEntry(depfile)
    entry_with_specified_type = DepfileEntry(depfile, type="pip")
    assert hash(entry_with_default_type) == hash(entry_with_specified_type)
