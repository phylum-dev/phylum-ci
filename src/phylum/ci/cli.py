"""Console script for phylum-ci."""

import argparse
from collections.abc import Sequence
import os
import pathlib
import sys
from typing import Optional

from phylum import __version__
from phylum.ci import SCRIPT_NAME
from phylum.ci.ci_azure import CIAzure
from phylum.ci.ci_base import CIBase, CIEnvs
from phylum.ci.ci_bitbucket import CIBitbucket
from phylum.ci.ci_github import CIGitHub
from phylum.ci.ci_gitlab import CIGitLab
from phylum.ci.ci_jenkins import CIJenkins
from phylum.ci.ci_none import CINone
from phylum.ci.ci_precommit import CIPreCommit
from phylum.ci.common import ReturnCode
from phylum.constants import HELP_MSG_API_URI, HELP_MSG_TARGET, HELP_MSG_TOKEN, HELP_MSG_VERSION
from phylum.init.cli import get_target_triple, process_version
from phylum.logger import LOG, set_logger_level


def detect_ci_platform(args: argparse.Namespace, remainder: list[str]) -> CIBase:
    """Detect CI platform via known CI-based environment variables.

    Reference: https://github.com/watson/ci-info/blob/master/vendors.json
    """
    ci_envs: CIEnvs = []

    # Detect GitLab CI
    if os.getenv("GITLAB_CI") == "true":
        LOG.debug("CI environment detected: GitLab CI")
        ci_envs.append(CIGitLab(args))

    # Detect GitHub Actions
    if os.getenv("GITHUB_ACTIONS") == "true":
        LOG.debug("CI environment detected: GitHub Actions")
        ci_envs.append(CIGitHub(args))

    # Detect Azure Pipelines
    if os.getenv("SYSTEM_TEAMFOUNDATIONCOLLECTIONURI"):
        LOG.debug("CI environment detected: Azure Pipelines")
        ci_envs.append(CIAzure(args))

    # Detect Bitbucket Pipelines
    if os.getenv("BITBUCKET_COMMIT"):
        LOG.debug("CI environment detected: Bitbucket Pipelines")
        ci_envs.append(CIBitbucket(args))

    # Detect Jenkins
    if all(map(os.getenv, ["JENKINS_URL", "BUILD_ID"])):
        LOG.debug("CI environment detected: Jenkins")
        ci_envs.append(CIJenkins(args))

    # Detect Python pre-commit environment
    # This might be a naive strategy for detecting the `pre-commit` case, but there is at least an attempt,
    # via a prerequisite check, to check the extra arguments for common/valid pre-commit usage patterns.
    if any(remainder):
        LOG.debug("Extra arguments provided. Assuming a Python `pre-commit` working environment.")
        ci_envs.append(CIPreCommit(args, remainder))

    if len(ci_envs) > 1:
        ci_platform_names = ", ".join(ci_env.ci_platform_name for ci_env in ci_envs)
        msg = f"Multiple CI environments detected: {ci_platform_names}"
        raise SystemExit(msg)
    if len(ci_envs) == 1:
        ci_env = ci_envs[0]
    else:
        # Fallback to default local environment
        # This happens when the `phylum-ci` command is run directly, from the CLI, but not within a CI environment.
        LOG.debug("No CI environment detected")
        ci_env = CINone(args)

    return ci_env


def get_args(args: Optional[Sequence[str]] = None) -> tuple[argparse.Namespace, list[str]]:
    """Get the arguments from the command line and return them."""
    parser = argparse.ArgumentParser(
        prog=SCRIPT_NAME,
        description="Use Phylum to analyze dependencies in a CI environment",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"{SCRIPT_NAME} {__version__}",
    )

    log_group = parser.add_mutually_exclusive_group()
    log_group.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase output verbosity (the maximum is -vvv)",
    )
    log_group.add_argument(
        "-q",
        "--quiet",
        action="count",
        default=0,
        help="Decrease output verbosity (the maximum is -qq)",
    )

    analysis_group = parser.add_argument_group(title="Dependency File Analysis Options")
    analysis_group.add_argument(
        "-d",
        "--depfile",
        type=pathlib.Path,
        action="append",
        nargs="*",
        help="""Path to package dependency file(s) (lockfiles or manifests) to analyze. If not specified here or in the
            `.phylum_project` file, an attempt will be made to automatically detect the file(s). Some dependency file
            types (e.g., Python/pip `requirements.txt`) are ambiguous in that they can be named differently and may or
            may not contain strict dependencies. In these cases, it is best to specify an explicit dependency file path.
            """,
    )
    analysis_group.add_argument(
        "-e",
        "--exclude",
        action="append",
        nargs="*",
        help="""Glob-style exclusion patterns. Ignored when dependency files are specified explicitly by argument.
        Absolute patterns (those starting with "/") only match whole paths, as rooted from the working directory
        (e.g., the project root). Relative pattern matching is done from the right of paths. Specify patterns in quotes
        to prevent shell globbing. The recursive wildcard “**” is not supported (it acts like non-recursive “*”).""",
    )
    analysis_group.add_argument(
        "-a",
        "--all-deps",
        action="store_true",
        help="""Specify this flag to consider all dependencies in analysis results instead of just the newly added ones.
            This is especially useful for manifest files where there is no companion lockfile (e.g., libraries).""",
    )
    analysis_group.add_argument(
        "-f",
        "--force-analysis",
        action="store_true",
        help="""Specify this flag to force analysis, even when no dependency file has changed. This flag is implicitly
            set when *any* manifest is included, to maximize the chance that updated dependencies are accounted.""",
    )
    analysis_group.add_argument(
        "-k",
        "--phylum-token",
        dest="token",
        help=HELP_MSG_TOKEN,
    )
    analysis_group.add_argument(
        "-p",
        "--project",
        help="""Name of a Phylum project to create and use to perform the analysis. Can also specify this option's value
            in the `.phylum_project` file. The value specified with this option takes precedence when both are provided.
            A deterministic project name will be used when neither are provided.""",
    )
    analysis_group.add_argument(
        "-g",
        "--group",
        help="""Optional group name, which will be the owner of the project. Can also specify this option's value in the
            `.phylum_project` file. The value specified with this option takes precedence when both are provided. Group
            will be created if it does not already exist. Groups require a paid account: https://phylum.io/pricing""",
    )
    analysis_group.add_argument(
        "-s",
        "--skip-comments",
        action="store_true",
        help="""Specify this flag to disable posting comments/notes on pull/merge requests. This flag is implicitly
            set when audit mode is enabled.""",
    )
    analysis_group.add_argument(
        "--audit",
        action="store_true",
        help="Specify this flag to enable audit mode: analysis is performed but results do not affect the exit code.",
    )

    cli_group = parser.add_argument_group(
        title="Phylum CLI Options",
        description="""Use the options here to control the Phylum CLI version in use during analysis.
            Examples of when this may be useful are: for troubleshooting, maintaining a consistent evironment,
            ensuring the latest version, or reverting to a previous version when the installed one causes an issue.""",
    )
    cli_group.add_argument(
        "-r",
        "--phylum-release",
        dest="version",
        # NOTE: `default` and `type` values are not used here in an effort to minimize rate limited GitHub API calls.
        help=HELP_MSG_VERSION,
    )
    cli_group.add_argument(
        "-t",
        "--target",
        default=get_target_triple(),
        help=HELP_MSG_TARGET,
    )
    cli_group.add_argument(
        "-u",
        "--api-uri",
        dest="uri",
        help=HELP_MSG_API_URI,
    )
    cli_group.add_argument(
        "-i",
        "--force-install",
        action="store_true",
        help="""Specify this flag to ensure the specified Phylum CLI release version is the one that is installed.
            Otherwise, any existing version will be used.""",
    )

    return parser.parse_known_args(args=args)


def main(args: Optional[Sequence[str]] = None) -> int:
    """Provide the main entrypoint."""
    parsed_args, remainder_args = get_args(args=args)
    set_logger_level(parsed_args.verbose - parsed_args.quiet)

    # Perform version check and normalization separately from the argument parsing so as to minimize GitHub
    # API calls when showing the help message but still bail early when the version provided is invalid.
    parsed_args.version = process_version(parsed_args.version)

    # Detect which CI environment, if any, we are in
    ci_env = detect_ci_platform(parsed_args, remainder_args)

    # Bail early when possible
    LOG.debug("Dependency files in use: %s", ci_env.depfiles)
    if ci_env.force_analysis:
        LOG.info("Forced analysis specified or otherwise set. Proceeding with analysis.")
    elif ci_env.is_any_depfile_changed:
        # "lockfile" language is used from here forward because the existence
        # of even a single manifest means the forced analysis branch is taken
        LOG.info("A lockfile has changed. Proceeding with analysis.")
    elif ci_env.phylum_comment_exists:
        LOG.info("Existing Phylum comment found. Proceeding with analysis.")
    else:
        LOG.warning("No lockfile has changed. Nothing to do.")
        return 0

    # Generate a label to use for analysis and report it
    LOG.info("Label to use for analysis: %s", ci_env.phylum_label)

    # Analyze current project dependency file(s) with Phylum CLI
    ci_env.analyze()

    # Output the results of the analysis
    ci_env.post_output()

    # Don't return a failure code in audit mode or if analysis results are unknown at this point
    returncode = 0 if ci_env.returncode == ReturnCode.INCOMPLETE else ci_env.returncode.value
    if ci_env.audit_mode:
        LOG.info("Audit mode enabled. Original return code: %s", returncode)
        returncode = 0
    LOG.debug("Return code: %s", returncode)
    return returncode


def script_main() -> None:
    """Script entry point."""
    # The only point of this function is to ensure the proper exit code is set when called from the script entry point
    sys.exit(main())


if __name__ == "__main__":
    script_main()
