"""Define a base environment for CI platforms.

The "base" environment is one that makes use of the CLI directly and is not necessarily part of a continuous
integration (CI) environment. Common functionality is provided where possible and CI specific features are
designated as abstract methods to be defined in specific CI environments.
"""
import argparse


class CIBase:
    """Provide methods for a basic CI environment."""

    def __init__(self, args: argparse.Namespace) -> None:
        self.ci_platform_name = "No CI"
