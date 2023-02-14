"""Provide common data structures for the package."""
from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
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


class RiskLevel(StrEnum):
    """Enumeration for risk levels, with their explanations, as provided by `phylum-types`.

    Reference: https://github.com/phylum-dev/phylum-types
    """

    # Informational, no action needs to be taken
    INFO = "info"
    # Minor issues like cosmetic code smells, possibly a problem in great number or rare circumstances
    LOW = "low"
    # May be indicative of overall quality issues
    MEDIUM = "medium"
    # Possibly exploitable behavior in some circumstances
    HIGH = "high"
    # Should fix as soon as possible, may be under active exploitation
    CRITICAL = "critical"


@dataclass(order=True)
class IssueEntry:
    """Class for keeping track of an individual issue entry."""

    sort_index_severity: int = field(init=False)
    severity: RiskLevel = field(compare=False)
    domain: str
    title: str

    def __post_init__(self):
        # Populate the first class attribute with a mapping from severity level to an int so
        # sorting by severity is done in the correct order instead of simply alphabetically.
        self.sort_index_severity = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}.get(self.severity, 5)


class ReturnCode(IntEnum):
    """Integer enumeration to track return codes."""

    SUCCESS = 0
    FAILURE = 1
    INCOMPLETE = 5
    FAILURE_INCOMPLETE = 6
