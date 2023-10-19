"""Provide common data structures for the package."""
import dataclasses
from enum import IntEnum
import json
import os
from pathlib import Path
from typing import Optional


@dataclasses.dataclass(order=True, frozen=True)
class PackageDescriptor:
    """Class for keeping track of packages returned by the `phylum parse` subcommand."""

    name: str
    version: str
    type: str  # noqa: A003 ; shadowing built-in `type` is okay since renaming here would be more confusing
    lockfile: Optional[str] = dataclasses.field(compare=False, default=None)


# Type alias
Packages = list[PackageDescriptor]


@dataclasses.dataclass()
class JobPolicyEvalResult:
    """Class for keeping track of the result when evaluating a policy for a job."""

    is_failure: bool
    incomplete_count: int
    output: str
    report: str


@dataclasses.dataclass()
class LockfileEntry:
    """Class for keeping track of an individual lockfile entry returned by the `phylum status` command."""

    _path: dataclasses.InitVar[os.PathLike]
    type: str = "auto"  # noqa: A003 ; shadowing built-in `type` is okay since renaming here would be more confusing
    path: Path = dataclasses.field(init=False)

    def __post_init__(self, _path):
        """Ensure the `path` field is actually a `Path` object."""
        if isinstance(_path, str):
            self.path = Path(_path)
        elif isinstance(_path, Path):
            self.path = _path
        else:
            msg = "Provided lockfile path is not PathLike"
            raise TypeError(msg)

    def __repr__(self) -> str:
        """Return a debug printable string representation of the `LockfileEntry` object."""
        # `PurePath.relative_to()` requires `self` to be the subpath of the argument, but `os.path.relpath()` does not.
        return os.path.relpath(self.path)


# Type alias
LockfileEntries = list[LockfileEntry]


class ReturnCode(IntEnum):
    """Integer enumeration to track return codes."""

    SUCCESS = 0
    FAILURE = 1
    INCOMPLETE = 5
    FAILURE_INCOMPLETE = 6
    LOCKFILE_FILTER = 10


# Reference: https://stackoverflow.com/questions/51286748/make-the-python-json-encoder-support-pythons-new-dataclasses
class DataclassJSONEncoder(json.JSONEncoder):
    """Custom JSON Encoder class that is able to serialize dataclass objects."""

    def default(self, o):  # noqa: D102 ; the parent's docstring is better here
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        return super().default(o)
