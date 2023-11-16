"""Provide common data structures for the package."""
import dataclasses
from enum import IntEnum
import json
import os
from pathlib import Path
from typing import Optional, Union


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
    """Class for keeping track of an individual "lockfile" entry returned by `phylum` commands.

    Current commands that return entries in this format include `status` and `find-lockable-files`.
    """

    _path: dataclasses.InitVar[Union[str, Path]]
    type: str = "auto"  # noqa: A003 ; shadowing built-in `type` is okay since renaming here would be more confusing
    path: Path = dataclasses.field(init=False)

    def __post_init__(self, _path):
        """Ensure the `path` field is actually a `Path` object."""
        if isinstance(_path, str):
            self.path = Path(_path).resolve()
        elif isinstance(_path, Path):
            self.path = _path.resolve()
        else:
            msg = "Provided dependency file path is not `str` or `Path`"
            raise TypeError(msg)

    def __repr__(self) -> str:
        """Return a debug printable string representation of the `LockfileEntry` object."""
        # `PurePath.relative_to()` requires `self` to be the subpath of the argument, but `os.path.relpath()` does not.
        return os.path.relpath(self.path)

    def __eq__(self, other: object) -> bool:
        """Provide an equality "rich comparison" method to override the default.

        Since "auto" could be any value, exclude it from comparisons when
        either side of the equality contains an "auto" `type` value.
        """
        if not isinstance(other, LockfileEntry):
            return NotImplemented
        if "auto" in {self.type, other.type}:
            return self.path == other.path
        return (self.type, self.path) == (other.type, other.path)

    def __hash__(self) -> int:
        """Provide a custom hash method to go with the equality "rich comparison" method.

        Objects which compare equal should have the same hash value.
        """
        # Since "auto" could be any value, and the Python data model for this magic method requires objects that
        # compare equal have the same hash value, the `self.type` property must be excluded from hashing.
        # Ref: https://docs.python.org/3/reference/datamodel.html#object.__hash__
        return hash(self.path)


# Type alias
LockfileEntries = list[LockfileEntry]


class ReturnCode(IntEnum):
    """Integer enumeration to track return codes."""

    SUCCESS = 0
    FAILURE = 1
    INCOMPLETE = 5
    FAILURE_INCOMPLETE = 6
    DEPFILE_FILTER = 10


# Reference: https://stackoverflow.com/questions/51286748/make-the-python-json-encoder-support-pythons-new-dataclasses
class DataclassJSONEncoder(json.JSONEncoder):
    """Custom JSON Encoder class that is able to serialize dataclass objects."""

    def default(self, o):  # noqa: D102 ; the parent's docstring is better here
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        return super().default(o)
