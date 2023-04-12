"""Provide common data structures for the package."""
import dataclasses
import json
from enum import IntEnum
from typing import List


@dataclasses.dataclass(order=True, frozen=True)
class PackageDescriptor:
    """Class for keeping track of packages returned by the `phylum parse` subcommand."""

    name: str
    version: str
    type: str


# Type alias
Packages = List[PackageDescriptor]


@dataclasses.dataclass()
class JobPolicyEvalResult:
    """Class for keeping track of the result when evaluating a policy for a job."""

    is_failure: bool
    incomplete_count: int
    output: str
    report: str


class ReturnCode(IntEnum):
    """Integer enumeration to track return codes."""

    SUCCESS = 0
    FAILURE = 1
    INCOMPLETE = 5
    FAILURE_INCOMPLETE = 6


# Reference: https://stackoverflow.com/questions/51286748/make-the-python-json-encoder-support-pythons-new-dataclasses
class DataclassJSONEncoder(json.JSONEncoder):
    """Custom JSON Encoder class that is able to serialize dataclass objects."""

    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        return super().default(o)
