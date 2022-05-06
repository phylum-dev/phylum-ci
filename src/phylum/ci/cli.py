"""Console script for phylum-ci."""
import argparse
import os
import pathlib
import shutil
import subprocess
import sys

from phylum import __version__
from phylum.ci import SCRIPT_NAME
from phylum.ci.base import CIBase
from phylum.ci.gitlab import CIGitLab
from phylum.constants import TOKEN_ENVVAR_NAME
from phylum.init.cli import get_expected_phylum_bin_path
from phylum.init.cli import main as phylum_init
from phylum.init.cli import version_check


def get_phylum_cli_version(cli_path):
    """Get the version of the installed and active Phylum CLI and return it."""
    cmd_line = [cli_path, "--version"]
    version = subprocess.run(cmd_line, check=True, capture_output=True, text=True).stdout.strip().lower()

    # Starting with Python 3.9, the str.removeprefix() method was introduced to do this same thing
    prefix = "phylum "
    prefix_len = len(prefix)
    if version.startswith(prefix):
        version = version[prefix_len:]

    return version


def get_phylum_bin_path(version=None):
    """Get the current path and corresponding version to the Phylum CLI binary and return them.

    Provide a CLI version as a fallback method for looking on an explicit path,
    based on the expected path for that version.
    """
    # Look for `phylum` on the PATH first
    cli_path = shutil.which("phylum")

    if cli_path is None and version is not None:
        # Maybe `phylum` is installed already but not on the PATH or maybe the PATH has not been updated in this
        # context. Look in the specific location expected by the provided version.
        expected_cli_path = get_expected_phylum_bin_path(version)
        cli_path = shutil.which("phylum", path=expected_cli_path)

    if cli_path is None:
        return (None, None)

    cli_path = pathlib.Path(cli_path)
    cli_version = get_phylum_cli_version(cli_path)
    return cli_path, cli_version


def _init_cli(args):
    """Check for an existing Phylum CLI install, install it if needed, and return the path to its binary."""
    cli_path, cli_version = get_phylum_bin_path(version=args.version)
    if cli_path is None:
        print(f" [+] Existing Phylum CLI instance not found. Installing version `{args.version}` ...")
        install_args = ["--phylum-release", args.version, "--phylum-token", args.token]
        phylum_init(install_args)
    else:
        print(f" [+] Existing Phylum CLI instance found: {cli_version} at {cli_path}")

    cli_path, cli_version = get_phylum_bin_path(version=args.version)
    print(f" [+] Using Phylum CLI instance: {cli_version} at {str(cli_path)}")

    return cli_path


def detect_ci_platform(args: argparse.Namespace) -> CIBase:
    """Detect CI platform via known CI-based environment variables."""
    ci_envs = []
    if os.getenv("GITLAB_CI") == "true":
        print(" [+] CI environment detected: GitLab CI")
        ci_envs.append(CIGitLab(args))

    if len(ci_envs) > 1:
        ci_platform_names = ", ".join(ci_env.ci_platform_name for ci_env in ci_envs)
        raise RuntimeError(f" Multiple CI environments detected: {ci_platform_names}")
    elif len(ci_envs) == 1:
        ci_env = ci_envs[0]
    else:
        print(" [+] No CI environment detected")
        ci_env = CIBase(args)

    return ci_env


def get_args(args=None):
    """Get the arguments from the command line and return them."""
    parser = argparse.ArgumentParser(
        prog=SCRIPT_NAME,
        description="Use Phylum to analyze dependencies in a CI environment",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # TODO: Add arguments for each of the inputs from the `phylum-analyze-pr-action`.
    #       Allow them to be specified as environment variables as well.
    # TODO: Allow for a specific lockfile name/path to be provided as input (instead of trying to determine it)
    parser.add_argument(
        "-r",
        "--phylum-release",
        dest="version",
        default="latest",
        type=version_check,
        help="""The version of the Phylum CLI to install. Can be specified as `latest` or a specific tagged release,
            with or without the leading `v`.""",
    )
    parser.add_argument(
        "-k",
        "--phylum-token",
        dest="token",
        help=f"""Phylum user token. Can also specify this option's value by setting the `{TOKEN_ENVVAR_NAME}`
            environment variable. The value specified with this option takes precedence when both are provided.
            Leave this option and it's related environment variable unspecified to either (1) use an existing token
            already set in the Phylum config file or (2) to manually populate the token with a `phylum auth login` or
            `phylum auth register` command after install.""",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{SCRIPT_NAME} {__version__}",
    )

    return parser.parse_args(args=args)


def main(args=None):
    """Main entrypoint."""
    args = get_args(args=args)

    # Detect which CI environment, if any, we are in
    ci_env = detect_ci_platform(args)
    print(ci_env.ci_platform_name)

    # TODO: Check for existing `.phylum_project` file

    # TODO: Generate PHYLUM_LABEL

    # TODO: Determine the "PR type" (lockfile type or "NA") and report it.
    #       This is also where the diff of the lockfile is taken into account.

    # Check for the existence of the CLI and install it if needed
    cli_path = _init_cli(args)
    print(f"cli_path: {cli_path}")

    # TODO: Analyze project lockfile with phylum CLI

    # TODO: Replicate test matrix?

    # TODO: Compare added dependencies in PR to analysis results

    # TODO: Update the PR/MR with an appropriate comment.
    #       This can be done conditionally based on the CI env, if any, we are in.
    #       Not being in a CI env could be the case when run locally...and may be the basis for a good pre-commit hook.
    #       Look into the `python-gitlab` package

    return 0


if __name__ == "__main__":
    sys.exit(main())
