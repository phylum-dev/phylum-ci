"""Provide common data structures for the package."""

import dataclasses
from enum import IntEnum
import json
import os
from pathlib import Path
from typing import Union


@dataclasses.dataclass(order=True, frozen=True)
class Package:
    """Class for tracking various package formats of the Phylum CLI and its extension API.

    This class is used for:

    * Keeping track of packages returned by the `phylum parse` subcommand (`PackageDescriptorAndLockfile`)
    * Representing the "base" packages used to filter results when getting a job's status (`Package`)
    * Representing "current" packages when submitting to Phylum CLI Extension API `analyze` call (`PackageWithOrigin`)
    """

    name: str
    version: str
    type: str
    lockfile: str = dataclasses.field(compare=False)  # path to dependency file containing this package


# Type alias
Packages = list[Package]


@dataclasses.dataclass()
class JobPolicyEvalResult:
    """Class for keeping track of the result when evaluating a policy for a job."""

    is_failure: bool
    incomplete_count: int
    output: str
    report: str


@dataclasses.dataclass()
class DepfileEntry:
    """Class for keeping track of an individual dependency file entry returned by `phylum` commands.

    Current commands that return entries in this format include `status --json` and `find-dependency-files`.
    """

    _path: dataclasses.InitVar[Union[str, Path]]
    type: str = "auto"
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
        """Return a debug printable string representation of the `DepfileEntry` object."""
        # `PurePath.relative_to()` requires `self` to be the subpath of the argument, but `os.path.relpath()` does not.
        return os.path.relpath(self.path)

    def __eq__(self, other: object) -> bool:
        """Provide an equality "rich comparison" method to override the default.

        Since "auto" could be any value, exclude it from comparisons when
        either side of the equality contains an "auto" `type` value.
        """
        if not isinstance(other, DepfileEntry):
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
DepfileEntries = list[DepfileEntry]


class ReturnCode(IntEnum):
    """Integer enumeration to track return codes."""

    SUCCESS = 0
    # NOTE: Don't create a unique entry here for the value `1`. That value is used for default
    #       failures (when a `SystemExit` exception is raised with a message instead of a code).
    #
    # Phylum analysis is complete and contains a policy violation
    POLICY_FAILURE = 2
    # Phylum analysis is incomplete and does not contain any policy violations
    INCOMPLETE = 5
    # Phylum analysis is incomplete and contains a policy violation
    FAILURE_INCOMPLETE = 6
    # A provided or detected dependency file failed one of the filters and was not included for analysis
    DEPFILE_FILTER = 10
    # No dependency files were provided or detected
    NO_DEPFILES_PROVIDED = 11
    # A manifest is attempted to be parsed but lockfile generation has been disabled
    MANIFEST_WITHOUT_GENERATION = 20


class CLIExitCode(IntEnum):
    """Integer enumeration to track the Phylum CLI exit codes."""

    # A project that already exists is attempted to be created
    PROJECT_ALREADY_EXISTS = 14
    # A manifest is attempted to be parsed but lockfile generation has been disabled
    MANIFEST_WITHOUT_GENERATION = 20


# Reference: https://stackoverflow.com/questions/51286748/make-the-python-json-encoder-support-pythons-new-dataclasses
class DataclassJSONEncoder(json.JSONEncoder):
    """Custom JSON Encoder class that is able to serialize dataclass objects."""

    def default(self, o):  # noqa: D102 ; the parent's docstring is better here
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        return super().default(o)
