"""Console script for phylum-init."""

import argparse
from collections.abc import Sequence
from functools import lru_cache
import itertools
import operator
import os
import pathlib
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
from typing import Optional
import zipfile

from packaging.utils import canonicalize_version
from packaging.version import InvalidVersion, Version
import requests
from ruamel.yaml import YAML

from phylum import __version__
from phylum.constants import (
    ENVVAR_NAME_API_URI,
    ENVVAR_NAME_TOKEN,
    HELP_MSG_API_URI,
    HELP_MSG_TARGET,
    HELP_MSG_TOKEN,
    HELP_MSG_VERSION,
    MIN_CLI_VER_FOR_INSTALL,
    REQ_TIMEOUT,
    SUPPORTED_ARCHES,
    SUPPORTED_PLATFORMS,
)
from phylum.exceptions import PhylumCalledProcessError
from phylum.github import github_request
from phylum.init import SCRIPT_NAME
from phylum.init.sig import verify_sig
from phylum.logger import LOG, MARKUP_NO_HI, progress_spinner, set_logger_level


def get_phylum_settings_path():
    """Get the Phylum settings path and return it."""
    home_dir = pathlib.Path.home()

    config_home_path = os.getenv("XDG_CONFIG_HOME")
    if not config_home_path:
        config_home_path = home_dir / ".config"

    phylum_config_path = pathlib.Path(config_home_path) / "phylum" / "settings.yaml"

    return phylum_config_path


def get_expected_phylum_bin_path():
    """Get the expected path to the Phylum CLI binary and return it."""
    phylum_bin_path = pathlib.Path.home() / ".local" / "bin" / "phylum"
    return phylum_bin_path


def get_phylum_cli_version(cli_path: Path) -> str:
    """Get the version of the installed and active Phylum CLI and return it."""
    cmd = [str(cli_path), "--version"]
    try:
        version = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip().lower()  # noqa: S603
    except subprocess.CalledProcessError as err:
        msg = "There was an error retrieving the Phylum CLI version"
        raise PhylumCalledProcessError(err, msg) from err
    version = version.removeprefix("phylum ").removesuffix("+")
    return version


def get_phylum_bin_path() -> tuple[Optional[Path], Optional[str]]:
    """Get the current path and corresponding version to the Phylum CLI binary and return them."""
    # Look for `phylum` on the PATH first
    which_cli_path = shutil.which("phylum")

    if which_cli_path is None:
        # Maybe `phylum` is installed already but not on the PATH or maybe the PATH has not been updated in this
        # context. Look in the specific expected location.
        expected_cli_path = get_expected_phylum_bin_path()
        which_cli_path = shutil.which("phylum", path=expected_cli_path)

    if which_cli_path is None:
        return (None, None)

    cli_path = Path(which_cli_path)
    cli_version = get_phylum_cli_version(cli_path)
    return cli_path, cli_version


def default_phylum_cli_version() -> str:
    """Find the default version of the Phylum CLI to use and return it.

    The default behavior is to use the installed version and fall back to `latest` when no CLI is already installed.
    """
    _, installed_cli_version = get_phylum_bin_path()
    if installed_cli_version is None:
        LOG.debug("No installed Phylum CLI found")
        return "latest"
    LOG.debug("Found installed Phylum CLI version: %s", installed_cli_version)
    return installed_cli_version


@lru_cache(maxsize=1)
def get_latest_version() -> str:
    """Get the "latest" version programmatically and return it."""
    # API Reference: https://docs.github.com/en/rest/releases/releases#get-the-latest-release
    github_api_url = "https://api.github.com/repos/phylum-dev/cli/releases/latest"
    req_json: dict = github_request(github_api_url)

    # The "name" entry stores the GitHub Release name, which could be set to something other than the version.
    # Using the "tag_name" entry is better since the tags are much more tightly coupled with the release version.
    latest_version = req_json.get("tag_name")
    if not latest_version:
        msg = f"The `tag_name` entry was not available or not set when querying: {github_api_url}"
        raise SystemExit(msg)

    return latest_version


@lru_cache(maxsize=1)
def supported_releases() -> list[str]:
    """Get the most recent supported releases programmatically and return them in sorted order, latest first."""
    # API Reference: https://docs.github.com/en/rest/releases/releases#list-releases
    github_api_url = "https://api.github.com/repos/phylum-dev/cli/releases"
    query_params = {"per_page": 100}
    LOG.debug("Minimum supported Phylum CLI version required for install: %s", MIN_CLI_VER_FOR_INSTALL)

    req_json: list = github_request(github_api_url, params=query_params)

    cli_releases = {}
    rel: dict
    for rel in req_json:
        # The "name" entry stores the GitHub Release name, which could be set to something other than the version.
        # Using the "tag_name" entry is better since the tags are much more tightly coupled with the release version.
        rel_ver = rel.get("tag_name", "0.0.0")
        try:
            cli_releases[rel_ver] = Version(canonicalize_version(rel_ver))
        except InvalidVersion as err:
            msg = f"An invalid version was provided: {rel_ver}"
            raise SystemExit(msg) from err
    sorted_cli_releases = [rel for rel, _ in sorted(cli_releases.items(), key=operator.itemgetter(1), reverse=True)]
    releases = itertools.takewhile(is_supported_version, sorted_cli_releases)

    return list(releases)


def is_supported_version(version: str) -> bool:
    """Predicate for determining if a given version is supported."""
    try:
        provided_version = Version(canonicalize_version(version))
        min_supported_version = Version(MIN_CLI_VER_FOR_INSTALL)
    except InvalidVersion as err:
        msg = f"An invalid version was provided: {version}"
        raise SystemExit(msg) from err

    return provided_version >= min_supported_version


@lru_cache(maxsize=1)
def supported_targets(release_tag: str) -> list[str]:
    """Get the supported Rust target triples programmatically for a given release tag and return them.

    Targets are identified by their "target triple" which is the string to inform the compiler what kind of output
    should be produced. A target triple consists of three strings separated by a hyphen, with a possible fourth string
    at the end preceded by a hyphen. The first is the architecture, the second is the "vendor", the third is the OS
    type, and the optional fourth is environment type.

    References:
      * https://doc.rust-lang.org/nightly/rustc/platform-support.html
      * https://rust-lang.github.io/rfcs/0131-target-specification.html
    """
    if release_tag not in supported_releases():
        msg = f"Unsupported version: {release_tag}"
        raise SystemExit(msg)

    # API Reference: https://docs.github.com/en/rest/releases/releases#get-a-release-by-tag-name
    github_api_url = f"https://api.github.com/repos/phylum-dev/cli/releases/tags/{release_tag}"

    req_json: dict = github_request(github_api_url)

    assets = req_json.get("assets", [])
    targets: list[str] = []
    prefix, suffix = "phylum-", ".zip"
    asset: dict
    for asset in assets:
        name: str = asset.get("name", "")
        if name.startswith(prefix) and name.endswith(suffix):
            target = name.removeprefix(prefix).removesuffix(suffix)
            targets.append(target)

    return list(set(targets))


def version_check(version: str) -> str:
    """Check a given version for validity and return a normalized form of it."""
    if version == "latest":
        version = get_latest_version()

    version = version.lower()
    if not version.startswith("v"):
        version = f"v{version}"

    supported_versions = supported_releases()
    if version not in supported_versions:
        msg = f"Specified Phylum CLI version must be from a supported release: {', '.join(supported_versions)}"
        raise SystemExit(msg)

    return version


def process_version(version: str) -> str:
    """Process the version argument and return it."""
    if version:
        LOG.debug("Phylum CLI version was specified as: %s", version)
        version = version_check(version)
    else:
        LOG.debug("Phylum CLI version not specified")
        version = version_check(default_phylum_cli_version())
    LOG.info("Using Phylum CLI version: %s", version)
    return version


def get_target_triple() -> str:
    """Get the "target triple" from the current system and return it."""
    arch = SUPPORTED_ARCHES.get(platform.uname().machine.lower(), "unknown")
    plat = SUPPORTED_PLATFORMS.get(platform.uname().system.lower(), "unknown")
    return f"{arch}-{plat}"


@progress_spinner("Downloading")
def save_file_from_url(url: str, path: Path) -> None:
    """Save a file from a given URL to a local file path, in binary mode."""
    LOG.info("Getting %s file ...", url)
    req = requests.get(url, timeout=REQ_TIMEOUT)
    req.raise_for_status()
    LOG.info("Saving %s file to %s ...", url, path)
    path.write_bytes(req.content)


def get_archive_url(tag_name: str, archive_name: str) -> str:
    """Craft an archive download URL from a given tag name and archive name."""
    # Reference: https://docs.github.com/en/rest/releases/releases#get-a-release-by-tag-name
    github_base_uri = "https://github.com/phylum-dev/cli/releases"
    archive_url = f"{github_base_uri}/download/{tag_name}/{archive_name}"
    return archive_url


def is_token_set(phylum_settings_path: Path, token: Optional[str] = None) -> bool:
    """Check if any token is already set in the given CLI configuration file.

    Optionally, check if a specific given `token` is set.
    """
    try:
        settings_data = phylum_settings_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return False

    yaml = YAML()
    settings_dict: dict = yaml.load(settings_data)
    auth_info_dict: dict = settings_dict.get("auth_info", {})
    configured_token = auth_info_dict.get("offline_access")

    if configured_token is None:
        return False
    if token is not None:
        return token == configured_token

    return True


@progress_spinner("Processing Phylum token option")
def process_token_option(args):
    """Process the Phylum token option as parsed from the arguments."""
    phylum_settings_path = get_phylum_settings_path()

    # The token option takes precedence over the Phylum API key environment variable.
    token = os.getenv(ENVVAR_NAME_TOKEN)
    if args.token is not None:
        token = args.token

    if token:
        LOG.info("Phylum token supplied as an option or `%s` environment variable", ENVVAR_NAME_TOKEN)
        if is_token_set(phylum_settings_path):
            LOG.info("An existing token is already set")
            if is_token_set(phylum_settings_path, token=token):
                LOG.info("Supplied token matches existing token")
            else:
                LOG.warning("Supplied token will be used to overwrite the existing token")
        else:
            LOG.info("No existing token exists. Supplied token will be used.")
    else:
        LOG.info("Phylum token NOT supplied as option or `%s` environment variable", ENVVAR_NAME_TOKEN)
        if is_token_set(phylum_settings_path):
            LOG.info("Existing token found. It will be used without modification.")
        else:
            LOG.warning("No existing token found. Use `phylum auth login` or `phylum auth register` command to set it.")

    if token and not is_token_set(phylum_settings_path, token=token):
        setup_token(token)


def setup_token(token: str) -> None:
    """Configure the CLI credentials with a provided token."""
    phylum_settings_path = get_phylum_settings_path()
    ensure_settings_file()
    yaml = YAML()
    settings: dict = yaml.load(phylum_settings_path.read_text(encoding="utf-8"))
    settings.setdefault("auth_info", {})
    settings["auth_info"]["offline_access"] = token
    with phylum_settings_path.open("w", encoding="utf-8") as f:
        yaml.dump(settings, f)


def ensure_settings_file() -> None:
    """Ensure the Phylum CLI settings file exists."""
    # The Phylum CLI `settings.yaml` file may not exist upon initial install. This can happen if the install did not
    # include running any commands, like when using the `--global-install` method. The standard install method will run
    # `extension install` commands to install all the default extensions. Running a command will trigger the CLI to
    # generate the settings file.
    phylum_settings_path = get_phylum_settings_path()
    if not phylum_settings_path.exists():
        LOG.debug("Attempting to generate the Phylum CLI settings file ...")
        phylum_bin_path, _ = get_phylum_bin_path()
        if phylum_bin_path is None:
            msg = "Could not find the path to the Phylum CLI. Unable to ensure the settings file."
            raise SystemExit(msg)
        cmd = [str(phylum_bin_path), "version"]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)  # noqa: S603
        except subprocess.CalledProcessError as err:
            msg = "There was an error attempting to generate the Phylum CLI settings file"
            raise PhylumCalledProcessError(err, msg) from err


@progress_spinner("Processing Phylum API URI option")
def process_uri_option(args: argparse.Namespace) -> None:
    """Process the Phylum API URI option as parsed from the arguments."""
    phylum_settings_path = get_phylum_settings_path()

    # The API URI option takes precedence over the Phylum API URI environment variable.
    api_uri = os.getenv(ENVVAR_NAME_API_URI)
    if args.uri is not None:
        api_uri = args.uri

    settings_file_existed = phylum_settings_path.exists()
    ensure_settings_file()
    yaml = YAML()
    settings: dict = yaml.load(phylum_settings_path.read_text(encoding="utf-8"))
    configured_uri = settings.get("connection", {}).get("uri")

    if api_uri:
        LOG.info("Phylum API URI supplied as an option or `%s` environment variable: %s", ENVVAR_NAME_API_URI, api_uri)
        if configured_uri != api_uri:
            LOG.info("Updating settings to use supplied Phylum API URI: %s ...", api_uri)
            settings.setdefault("connection", {})
            settings["connection"]["uri"] = api_uri
            with phylum_settings_path.open("w", encoding="utf-8") as f:
                yaml.dump(settings, f)
        else:
            LOG.debug("Supplied API URI matches existing settings value")
    else:
        LOG.info("Phylum API URI NOT supplied as an option or `%s` environment variable", ENVVAR_NAME_API_URI)
        if settings_file_existed:
            LOG.debug("The value in the existing settings file will be used: %s", configured_uri)
        else:
            LOG.debug("The CLI will use the PRODUCTION instance: %s", configured_uri)


@progress_spinner("Installing the Phylum CLI")
def install_phylum_cli(args: argparse.Namespace, extracted_dir: Path) -> None:
    """Install the Phylum CLI from an archive that has been extracted to the given path."""
    # This may look wrong, but a decision was made to manually handle global installs
    # in the places it is required instead of updating the CLI's install script.
    # Reference: https://github.com/phylum-dev/cli/pull/671
    if args.global_install:  # noqa: SIM108 ; ternary operator makes it harder to place comments
        # Current assumptions for this method:
        #   * the /usr/local/bin directory exists, has proper permissions, and is on the PATH for all users
        #   * the install is on a system with glibc
        cmd = ["install", "-m", "0755", "phylum", "/usr/local/bin/phylum"]
    else:
        cmd = ["sh", "install.sh"]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=extracted_dir)  # noqa: S603
    except subprocess.CalledProcessError as err:
        msg = "There was an error while trying to install the Phylum CLI"
        raise PhylumCalledProcessError(err, msg) from err


@progress_spinner("Confirming Phylum CLI installation and setup")
def confirm_setup() -> None:
    """Check to ensure everything is working."""
    phylum_bin_path, _ = get_phylum_bin_path()

    # Print the version message to aid log review
    cmd = [str(phylum_bin_path), "version"]
    version_output = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout  # noqa: S603
    LOG.debug(version_output)

    if is_token_set(get_phylum_settings_path()):
        # Check that the token and API URI were setup correctly by using them to display the current auth status
        cmd = [str(phylum_bin_path), "auth", "status"]
        auth_output = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout  # noqa: S603
        LOG.debug(auth_output)
    else:
        LOG.warning("Existing token not found. Can't confirm setup.")

    # Print the help message to aid log review
    cmd = [str(phylum_bin_path), "--help"]
    help_output = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout  # noqa: S603
    LOG.debug(help_output)


def get_args(args: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Get the arguments from the command line or input parameter, parse and return them."""
    parser = argparse.ArgumentParser(
        prog=SCRIPT_NAME,
        description="Fetch and install the Phylum CLI",
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

    parser.add_argument(
        "-r",
        "--phylum-release",
        dest="version",
        # NOTE: `default` and `type` values are not used here in an effort to minimize rate limited GitHub API calls.
        help=HELP_MSG_VERSION,
    )
    parser.add_argument(
        "-t",
        "--target",
        default=get_target_triple(),
        help=HELP_MSG_TARGET,
    )
    parser.add_argument(
        "-g",
        "--global-install",
        action="store_true",
        # Specify this flag to install the Phylum CLI to a globally accessible directory.
        # NOTE: This option is hidden from help output b/c it is meant to be used internally, for Docker image creation.
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-k",
        "--phylum-token",
        dest="token",
        help=HELP_MSG_TOKEN,
    )
    parser.add_argument(
        "-u",
        "--api-uri",
        dest="uri",
        help=HELP_MSG_API_URI,
    )

    list_group = parser.add_mutually_exclusive_group()
    list_group.add_argument(
        "--list-releases",
        action="store_true",
        help="List the Phylum CLI releases available to install.",
    )
    list_group.add_argument(
        "--list-targets",
        action="store_true",
        help="List the target platform types available for installing a given Phylum CLI release.",
    )

    return parser.parse_args(args=args)


def main(args=None):
    """Provide the main entrypoint."""
    args = get_args(args=args)
    set_logger_level(args.verbose - args.quiet)

    # Perform version check and normalization separately from the argument parsing so as to minimize GitHub
    # API calls when showing the help message but still bail early when the version provided is invalid.
    args.version = process_version(args.version)

    if args.list_releases:
        LOG.info("Looking up supported releases ...")
        releases = ", ".join(supported_releases())
        LOG.warning("Supported releases: %s", releases, extra={"highlighter": False})
        return 0

    tag_name = args.version
    LOG.info("Looking up supported targets for release %s ...", tag_name)
    supported_target_triples = supported_targets(tag_name)
    if args.list_targets:
        targets = ", ".join(supported_target_triples)
        LOG.warning("Supported targets for release %s: %s", tag_name, targets, extra={"highlighter": False})
        return 0

    target_triple = args.target
    if target_triple not in supported_target_triples:
        msg = f"The identified target triple `{target_triple}` is not supported for release {tag_name}"
        raise SystemExit(msg)

    archive_name = f"phylum-{target_triple}.zip"
    sig_name = f"{archive_name}.signature"
    archive_url = get_archive_url(tag_name, archive_name)
    sig_url = f"{archive_url}.signature"

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = pathlib.Path(temp_dir)
        archive_path = temp_dir_path / archive_name
        sig_path = temp_dir_path / sig_name

        save_file_from_url(archive_url, archive_path)
        save_file_from_url(sig_url, sig_path)

        verify_sig(archive_path, sig_path)

        with zipfile.ZipFile(archive_path, mode="r") as zip_file:
            if zip_file.testzip() is not None:
                msg = f"There was a bad file in the zip archive {archive_name}"
                raise zipfile.BadZipFile(msg)
            extracted_dir = temp_dir_path / f"phylum-{target_triple}"
            zip_file.extractall(path=temp_dir)

        install_phylum_cli(args, extracted_dir)

    process_uri_option(args)
    process_token_option(args)
    confirm_setup()
    LOG.warning(":white_check_mark: Installed Phylum CLI %s", tag_name, extra=MARKUP_NO_HI)

    return 0


if __name__ == "__main__":
    sys.exit(main())
