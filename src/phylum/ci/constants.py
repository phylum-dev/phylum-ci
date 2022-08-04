"""Provide constants for use throughout the package."""
import string
import textwrap

from phylum.ci.common import RiskDomain

# The common Phylum header that must exist as the first text in the first line of all analysis output
PHYLUM_HEADER = "# Phylum OSS Supply Chain Risk Analysis"

# NOTE: All multi-line strings are indented by two levels on purpose, to ensure they line up correctly when used with
#       each other in templates and are all fully left justified after applying `textwrap.dedent` for normalization.

SUCCESS_DETAILS = "The Phylum risk analysis is complete and did not identify any issues."

# Expandable HTML providing information on why there was a failure
FAILURE_DETAILS = """
        <details>
        <summary>Background</summary>
        <br />
        This repository analyzes the risk of new dependencies. An administrator of
        this repository has set score requirements for Phylum's five risk domains.
        <br /><br />
        If you see this comment, one or more dependencies added to the
        package manager lockfile have failed Phylum's risk analysis.
        </details>
        """.strip()

# String template providing information about an incomplete analysis.
# Substitution variable(s) should be accounted for when using string variables containing this text.
INCOMPLETE_DETAILS = """
        The analysis contains $count package(s) Phylum has not yet processed,
        preventing a complete risk analysis. Phylum is processing these
        packages currently and should complete soon.
        Please wait for up to 30 minutes, then re-run the analysis.
        """

# Headers for distinct comment types:
FAILED_COMMENT = textwrap.dedent(
    f"""
        {PHYLUM_HEADER} - FAILED

        {FAILURE_DETAILS}
        """
)

SUCCESS_COMMENT = textwrap.dedent(
    f"""
        {PHYLUM_HEADER} - SUCCESS

        {SUCCESS_DETAILS}
        """
)

# Substitution variable(s) should be accounted for when using this template
INCOMPLETE_WITH_FAILURE_COMMENT_TEMPLATE = string.Template(
    textwrap.dedent(
        f"""
        {PHYLUM_HEADER} - INCOMPLETE WITH FAILURE
        {INCOMPLETE_DETAILS}
        {FAILURE_DETAILS}
        """
    )
)

# Substitution variable(s) should be accounted for when using this template
INCOMPLETE_COMMENT_TEMPLATE = string.Template(
    textwrap.dedent(
        f"""
        {PHYLUM_HEADER} - INCOMPLETE
        {INCOMPLETE_DETAILS}
        """
    )
)

# These are the project threshold options.
# Keys are the risk domain threshold options, as provided/known by argparse.
# Values are a RiskDomain dataclass object containing:
#   * the descriptive name
#   * key name returned from a Phylum analysis as known by the overall project threshold mapping
#   * key name returned from a Phylum analysis as known by an individual package riskVectors mapping
PROJECT_THRESHOLD_OPTIONS = {
    "vul_threshold": RiskDomain("Software Vulnerability", "vulnerability", "vulnerabilities"),
    "mal_threshold": RiskDomain("Malicious Code", "malicious", "malicious_code"),
    "eng_threshold": RiskDomain("Engineering", "engineering", "engineering"),
    "lic_threshold": RiskDomain("License", "license", "license"),
    "aut_threshold": RiskDomain("Author", "author", "author"),
}
