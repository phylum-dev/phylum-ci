"""Console script for phylum-ci."""
import argparse
import json
import os
import pathlib
import shlex
import subprocess
import sys
from typing import List, Optional, Sequence, Tuple

from phylum import __version__
from phylum.ci import SCRIPT_NAME
from phylum.ci.ci_azure import CIAzure
from phylum.ci.ci_base import CIBase, CIEnvs
from phylum.ci.ci_bitbucket import CIBitbucket
from phylum.ci.ci_github import CIGitHub
from phylum.ci.ci_gitlab import CIGitLab
from phylum.ci.ci_none import CINone
from phylum.ci.ci_precommit import CIPreCommit
from phylum.ci.common import ReturnCode
from phylum.constants import TOKEN_ENVVAR_NAME
from phylum.init.cli import default_phylum_cli_version, get_target_triple, version_check


def detect_ci_platform(args: argparse.Namespace, remainder: List[str]) -> CIBase:
    """Detect CI platform via known CI-based environment variables.

    Reference: https://github.com/watson/ci-info/blob/master/vendors.json
    """
    ci_envs: CIEnvs = []

    # Detect GitLab CI
    if os.getenv("GITLAB_CI") == "true":
        print(" [+] CI environment detected: GitLab CI")
        ci_envs.append(CIGitLab(args))

    # Detect GitHub Actions
    if os.getenv("GITHUB_ACTIONS") == "true":
        print(" [+] CI environment detected: GitHub Actions")
        ci_envs.append(CIGitHub(args))

    # Detect Azure Pipelines
    if os.getenv("SYSTEM_TEAMFOUNDATIONCOLLECTIONURI"):
        print(" [+] CI environment detected: Azure Pipelines")
        ci_envs.append(CIAzure(args))

    # Detect Bitbucket Pipelines
    if os.getenv("BITBUCKET_COMMIT"):
        print(" [+] CI environment detected: Bitbucket Pipelines")
        ci_envs.append(CIBitbucket(args))

    # Detect Python pre-commit environment
    # This might be a naive strategy for detecting the `pre-commit` case, but there is at least an attempt,
    # via a pre-requisite check, to check the extra arguments for common/valid pre-commit usage patterns.
    if any(remainder):
        print(" [+] Extra arguments provided. Assuming a Python `pre-commit` working environment.")
        ci_envs.append(CIPreCommit(args, remainder))

    if len(ci_envs) > 1:
        ci_platform_names = ", ".join(ci_env.ci_platform_name for ci_env in ci_envs)
        raise SystemExit(f" [!] Multiple CI environments detected: {ci_platform_names}")
    if len(ci_envs) == 1:
        ci_env = ci_envs[0]
    else:
        # Fallback to default local environment
        # This happens when the `phylum-ci` command is run directly, from the CLI, but not within a CI environment.
        print(" [+] No CI environment detected")
        ci_env = CINone(args)

    return ci_env


def get_phylum_analysis(ci_env: CIBase) -> dict:
    """Analyze a project's lockfile(s) from a given CI environment with the phylum CLI and return the analysis."""
    # Build up the analyze command based on the provided inputs
    cmd = [str(ci_env.cli_path), "analyze", "--label", ci_env.phylum_label, "--project", ci_env.phylum_project]
    if ci_env.phylum_group:
        cmd.extend(["--group", ci_env.phylum_group])
    cmd.extend(["--verbose", "--json"])
    cmd.extend(str(lockfile.path) for lockfile in ci_env.lockfiles)

    shell_escaped_cmd = " ".join(shlex.quote(arg) for arg in cmd)
    print(f" [*] Performing analysis with command: {shell_escaped_cmd}")
    try:
        analysis_result = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
    except subprocess.CalledProcessError as err:
        # The Phylum project can set the CLI to "fail the build" if threshold requirements are not met.
        # This causes the return code to be 100 and lands us here. Check for this case to proceed.
        if err.returncode == 100:
            analysis_result = err.stdout
        else:
            print(f" [!] stdout:\n{err.stdout}")
            print(f" [!] stderr:\n{err.stderr}")
            raise SystemExit(f" [!] {err}") from err
    analysis = json.loads(analysis_result)
    return analysis


def threshold_check(threshold_in: str) -> int:
    """Check a given threshold for validity and return it as an int."""
    msg = "threshold must be an integer between 0 and 100, inclusive"
    try:
        threshold_out = int(threshold_in)
    except ValueError as err:
        raise argparse.ArgumentTypeError(msg) from err
    if threshold_out not in range(101):
        raise argparse.ArgumentTypeError(msg)
    return threshold_out


def get_args(args: Optional[Sequence[str]] = None) -> Tuple[argparse.Namespace, List[str]]:
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

    analysis_group = parser.add_argument_group(title="Lockfile Analysis Options")
    analysis_group.add_argument(
        "-l",
        "--lockfile",
        type=pathlib.Path,
        action="append",
        nargs="*",
        help="""Path to the package lockfile(s) to analyze. If not specified here or in the `.phylum_project` file, an
            attempt will be made to automatically detect the lockfile(s). Some lockfile types (e.g., Python/pip
            `requirements.txt`) are ambiguous in that they can be named differently and may or may not contain strict
            dependencies. In these cases, it is best to specify an explicit lockfile path.""",
    )
    analysis_group.add_argument(
        "-a",
        "--all-deps",
        action="store_true",
        help="Specify this flag to consider all dependencies in analysis results instead of just the newly added ones.",
    )
    analysis_group.add_argument(
        "-f",
        "--force-analysis",
        action="store_true",
        help="Specify this flag to force analysis, even when no lockfile has changed.",
    )
    analysis_group.add_argument(
        "-k",
        "--phylum-token",
        dest="token",
        help=f"""Phylum user token. Can also specify this option's value by setting the `{TOKEN_ENVVAR_NAME}`
            environment variable. The value specified with this option takes precedence when both are provided.
            Leave this option and it's related environment variable unspecified to either (1) use an existing token
            already set in the Phylum config file or (2) to manually populate the token with a `phylum auth login` or
            `phylum auth register` command after install.""",
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
        help="Optional group name, which will be the owner of the project. Only used when a project is also specified.",
    )

    threshold_group = parser.add_argument_group(
        title="Risk Domain Threshold Options",
        description="""Thresholds for the five risk domains may already be set at the Phylum project level.
            They can be set differently here for CI environments to "fail the build."
            The default is to use the project level setting unless overridden by a value specified in this group.
            Values must be an integer between 0 and 100, inclusive. Setting the value to zero (0) has the
            effect of disabling analysis against that risk domain. See "Phylum Risk Domains" documentation for more
            detail: https://docs.phylum.io/docs/phylum-package-score#risk-domains""",
    )
    threshold_group.add_argument(
        "-u",
        "--vul-threshold",
        type=threshold_check,
        help="v(u)lnerability risk score threshold value.",
    )
    threshold_group.add_argument(
        "-m",
        "--mal-threshold",
        type=threshold_check,
        help="(m)alicious Code risk score threshold value.",
    )
    threshold_group.add_argument(
        "-e",
        "--eng-threshold",
        type=threshold_check,
        help="(e)ngineering risk score threshold value.",
    )
    threshold_group.add_argument(
        "-c",
        "--lic-threshold",
        type=threshold_check,
        help="li(c)ense risk score threshold value.",
    )
    threshold_group.add_argument(
        "-o",
        "--aut-threshold",
        type=threshold_check,
        help="auth(o)r risk score threshold value.",
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
        help="""The version of the Phylum CLI to install. Can be specified as `latest` or a specific tagged release,
            with or without the leading `v`. Default behavior is to use the installed version and fall back to `latest`
            when no CLI is already installed.""",
    )
    cli_group.add_argument(
        "-t",
        "--target",
        default=get_target_triple(),
        help="The target platform type where the CLI will be installed.",
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
    """Main entrypoint."""
    parsed_args, remainder_args = get_args(args=args)

    # Perform version check and normalization here so as to minimize GitHub API calls when
    # showing the help message but still bail early when the version provided is invalid
    if parsed_args.version:
        print(f" [+] Phylum CLI version was specified as: {parsed_args.version}")
        parsed_args.version = version_check(parsed_args.version)
    else:
        print(" [+] Phylum CLI version not specified")
        parsed_args.version = default_phylum_cli_version()
    print(f" [*] Using Phylum CLI version: {parsed_args.version}")

    # Detect which CI environment, if any, we are in
    ci_env = detect_ci_platform(parsed_args, remainder_args)

    # Bail early if there are no changes to any lockfile
    print(f" [+] lockfile(s) in use: {ci_env.lockfiles}")
    if ci_env.force_analysis:
        print(" [+] Forced analysis specified with flag or otherwise set. Proceeding with analysis ...")
    else:
        if ci_env.is_any_lockfile_changed:
            print(" [+] A lockfile has changed. Proceeding with analysis ...")
        else:
            print(" [+] No lockfile has changed. Nothing to do.")
            return 0

    # Generate a label to use for analysis and report it
    print(f" [+] Label to use for analysis: {ci_env.phylum_label}")

    # Analyze current project lockfile(s) with phylum CLI
    analysis = get_phylum_analysis(ci_env)

    # Review analysis results to determine the overall state
    return_code = ci_env.analyze(analysis)
    print(f" [-] Return code: {return_code}")

    # Output the results of the analysis
    ci_env.post_output()

    # Don't return a failure code if the results are unknown at this point
    if return_code == ReturnCode.INCOMPLETE:
        return 0
    return return_code.value


def script_main() -> None:
    """Script entry point."""
    # The only point of this function is to ensure the proper exit code is set when called from the script entry point
    sys.exit(main())


if __name__ == "__main__":
    script_main()
