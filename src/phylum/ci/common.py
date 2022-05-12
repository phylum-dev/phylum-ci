"""Provide common data structures for the package."""
from dataclasses import dataclass
from enum import IntEnum
from typing import List


@dataclass(order=True, frozen=True)
class PackageDescriptor:
    """Class for keeping track of packages returned by the `phylum parse` subcommand."""

    name: str
    version: str
    type: str


# Type alias
Packages = List[PackageDescriptor]


class ReturnCode(IntEnum):
    """Integer enumeration to track return codes."""

    SUCCESS = 0
    FAILURE = 1
    INCOMPLETE = 5
    FAILURE_INCOMPLETE = 6
