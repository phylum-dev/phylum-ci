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


@dataclass()
class ProjectThresholdInfo:
    """Class for keeping track of project risk threshold information.

    `threshold`: The risk domain threshold value in use.
    `req_src`: The source of the threshold requirement. For example, `phylum-ci option` for command line options
    """

    threshold: float
    req_src: str


@dataclass(order=True, frozen=True)
class RiskDomain:
    """Class for keeping track of a specific risk domain.

    Each risk domain can be referenced in various ways. See "Phylum Risk Domains" documentation for more detail:
    https://docs.phylum.io/docs/phylum-package-score#risk-domains

    * `output_name`: The descriptive name; useful for output expected to be read by humans
    * `project_name`: Key name returned from a Phylum analysis as known by the overall project threshold mapping
    * `package_name`: Key name returned from a Phylum analysis as known by an individual package riskVectors mapping
    """

    output_name: str
    project_name: str
    package_name: str


class ReturnCode(IntEnum):
    """Integer enumeration to track return codes."""

    SUCCESS = 0
    FAILURE = 1
    INCOMPLETE = 5
    FAILURE_INCOMPLETE = 6
