"""Provide constants for use throughout the package."""
import string
import textwrap

# Headers for distinct comment types
FAILED_COMMENT = textwrap.dedent(
    """
    ## Phylum OSS Supply Chain Risk Analysis - FAILED

    <details>
    <summary>Background</summary>
    <br />
    This repository analyzes the risk of new dependencies. An administrator of
    this repository has set score requirements for Phylum's five risk domains.
    <br /><br />
    If you see this comment, one or more dependencies added to the
    package manager lockfile have failed Phylum's risk analysis.
    </details>

    """
)
SUCCESS_COMMENT = textwrap.dedent(
    """
    ## Phylum OSS Supply Chain Risk Analysis - SUCCESS

    The Phylum risk analysis is complete and did not identify any issues.
    """
).strip()
FAILED_INCOMPLETE_COMMENT_TEMPLATE = string.Template(
    textwrap.dedent(
        """
        ## Phylum OSS Supply Chain Risk Analysis - INCOMPLETE WITH FAILURES

        The analysis contains $count package(s) Phylum has not yet processed,
        preventing a complete risk analysis. Phylum is processing these
        packages currently and should complete soon.
        Please wait for up to 30 minutes, then re-run the analysis.

        <details>
        <summary>Background</summary>
        <br />
        This repository analyzes the risk of new dependencies. An administrator of
        this repository has set score requirements for Phylum's five risk domains.
        <br /><br />
        If you see this comment, one or more dependencies added to the
        package manager lockfile have failed Phylum's risk analysis.
        </details>

        """
    )
)
INCOMPLETE_COMMENT_TEMPLATE = string.Template(
    textwrap.dedent(
        """
        ## Phylum OSS Supply Chain Risk Analysis - INCOMPLETE

        The analysis contains $count package(s) Phylum has not yet processed,
        preventing a complete risk analysis. Phylum is processing these
        packages currently and should complete soon.
        Please wait for up to 30 minutes, then re-run the analysis.
        """
    ).strip()
)
