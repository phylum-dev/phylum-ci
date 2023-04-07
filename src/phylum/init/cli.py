"""Console script for phylum-init."""
import argparse
import os
import pathlib
import platform
import shutil
import subprocess
import sys
import tempfile
import zipfile
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Tuple

import requests
from packaging.utils import canonicalize_version
from packaging.version import InvalidVersion, Version
from ruamel.yaml import YAML

from phylum import __version__
from phylum.constants import (
    API_URI_ENVVAR_NAME,
    HELP_MSG_API_URI,
    HELP_MSG_TARGET,
    HELP_MSG_TOKEN,
    HELP_MSG_VERSION,
    MIN_CLI_VER_FOR_INSTALL,
    REQ_TIMEOUT,
    SUPPORTED_ARCHES,
    SUPPORTED_PLATFORMS,
    TOKEN_ENVVAR_NAME,
)
from phylum.github import github_request
from phylum.init import SCRIPT_NAME
from phylum.init.sig import verify_sig


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
    version = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip().lower()

    # Starting with Python 3.9, the str.removeprefix() method was introduced to do this same thing
    prefix = "phylum "
    if version.startswith(prefix):
        version = version.replace(prefix, "", 1)

    return version


def get_phylum_bin_path() -> Tuple[Optional[Path], Optional[str]]:
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
        print(" [+] No installed Phylum CLI found")
        return "latest"
    print(f" [+] Found installed Phylum CLI version: {installed_cli_version}")
    return installed_cli_version


@lru_cache(maxsize=1)
def get_latest_version() -> str:
    """Get the "latest" version programmatically and return it."""
    # API Reference: https://docs.github.com/en/rest/releases/releases#get-the-latest-release
    github_api_url = "https://api.github.com/repos/phylum-dev/cli/releases/latest"
    req_json = github_request(github_api_url)

    # The "name" entry stores the GitHub Release name, which could be set to something other than the version.
    # Using the "tag_name" entry is better since the tags are much more tightly coupled with the release version.
    latest_version = req_json.get("tag_name")
    if not latest_version:
        raise SystemExit(f" [!] The `tag_name` entry was not available or not set when querying: {github_api_url}")

    return latest_version


@lru_cache(maxsize=1)
def supported_releases() -> List[str]:
    """Get the most recent supported releases programmatically and return them."""
    # API Reference: https://docs.github.com/en/rest/releases/releases#list-releases
    github_api_url = "https://api.github.com/repos/phylum-dev/cli/releases"
    query_params = {"per_page": 100}

    req_json = github_request(github_api_url, params=query_params)

    # The "name" entry stores the GitHub Release name, which could be set to something other than the version.
    # Using the "tag_name" entry is better since the tags are much more tightly coupled with the release version.
    releases = [rel.get("tag_name") for rel in req_json if is_supported_version(rel.get("tag_name", "0.0.0"))]

    return releases


def is_supported_version(version: str) -> bool:
    """Predicate for determining if a given version is supported."""
    try:
        provided_version = Version(canonicalize_version(version))
        min_supported_version = Version(MIN_CLI_VER_FOR_INSTALL)
    except InvalidVersion as err:
        raise SystemExit(f" [!] An invalid version was provided: {version}") from err

    return provided_version >= min_supported_version


@lru_cache(maxsize=1)
def supported_targets(release_tag: str) -> List[str]:
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
        raise SystemExit(f" [!] Unsupported version: {release_tag}")

    # API Reference: https://docs.github.com/en/rest/releases/releases#get-a-release-by-tag-name
    github_api_url = f"https://api.github.com/repos/phylum-dev/cli/releases/tags/{release_tag}"

    req_json = github_request(github_api_url)

    assets = req_json.get("assets", [])
    targets: List[str] = []
    prefix, suffix = "phylum-", ".zip"
    for asset in assets:
        name = asset.get("name", "")
        if name.startswith(prefix) and name.endswith(suffix):
            target = name.replace(prefix, "").replace(suffix, "")
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
        releases = ", ".join(supported_versions)
        raise SystemExit(f" [!] Specified Phylum CLI version must be from a supported release: {releases}")

    return version


def get_target_triple() -> str:
    """Get the "target triple" from the current system and return it."""
    arch = SUPPORTED_ARCHES.get(platform.uname().machine.lower(), "unknown")
    plat = SUPPORTED_PLATFORMS.get(platform.uname().system.lower(), "unknown")
    return f"{arch}-{plat}"


def save_file_from_url(url: str, path: Path) -> None:
    """Save a file from a given URL to a local file path, in binary mode."""
    print(f" [*] Getting {url} file ...", end="")
    req = requests.get(url, timeout=REQ_TIMEOUT)
    req.raise_for_status()
    print("Done")

    print(f" [*] Saving {url} file to {path} ...", end="")
    path.write_bytes(req.content)
    print("Done")


def get_archive_url(tag_name: str, archive_name: str) -> str:
    """Craft an archive download URL from a given tag name and archive name."""
    # Reference: https://docs.github.com/en/rest/releases/releases#get-a-release-by-tag-name
    github_base_uri = "https://github.com/phylum-dev/cli/releases"
    archive_url = f"{github_base_uri}/download/{tag_name}/{archive_name}"
    return archive_url


def is_token_set(phylum_settings_path, token=None):
    """Check if any token is already set in the given CLI configuration file.

    Optionally, check if a specific given `token` is set.
    """
    try:
        settings_data = phylum_settings_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return False

    yaml = YAML()
    settings_dict = yaml.load(settings_data)
    configured_token = settings_dict.get("auth_info", {}).get("offline_access")

    if configured_token is None:
        return False
    if token is not None:
        if token != configured_token:
            return False

    return True


def process_token_option(args):
    """Process the Phylum token option as parsed from the arguments."""
    phylum_settings_path = get_phylum_settings_path()

    # The token option takes precedence over the Phylum API key environment variable.
    token = os.getenv(TOKEN_ENVVAR_NAME)
    if args.token is not None:
        token = args.token

    if token:
        print(f" [+] Phylum token supplied as an option or `{TOKEN_ENVVAR_NAME}` environment variable")
        if is_token_set(phylum_settings_path):
            print(" [+] An existing token is already set")
            if is_token_set(phylum_settings_path, token=token):
                print(" [+] Supplied token matches existing token")
            else:
                print(" [!] Supplied token will be used to overwrite the existing token")
        else:
            print(" [+] No existing token exists. Supplied token will be used.")
    else:
        print(f" [+] Phylum token NOT supplied as option or `{TOKEN_ENVVAR_NAME}` environment variable")
        if is_token_set(phylum_settings_path):
            print(" [+] Existing token found. It will be used without modification.")
        else:
            print(" [!] Existing token not found. Use `phylum auth login` or `phylum auth register` command to set it.")

    if token and not is_token_set(phylum_settings_path, token=token):
        setup_token(token)


def setup_token(token: str) -> None:
    """Setup the CLI credentials with a provided token."""
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
        phylum_bin_path, _ = get_phylum_bin_path()
        if phylum_bin_path is None:
            raise SystemExit(" [!] Could not find the path to the Phylum CLI. Unable to ensure the settings file.")
        cmd = [str(phylum_bin_path), "version"]
        subprocess.run(cmd, check=True)


def process_uri_option(args: argparse.Namespace) -> None:
    """Process the Phylum API URI option as parsed from the arguments."""
    phylum_settings_path = get_phylum_settings_path()

    # The API URI option takes precedence over the Phylum API URI environment variable.
    api_uri = os.getenv(API_URI_ENVVAR_NAME)
    if args.uri is not None:
        api_uri = args.uri

    settings_file_existed = phylum_settings_path.exists()
    ensure_settings_file()
    yaml = YAML()
    settings: dict = yaml.load(phylum_settings_path.read_text(encoding="utf-8"))
    configured_uri = settings.get("connection", {}).get("uri")

    if api_uri:
        print(f" [+] Phylum API URI supplied as an option or `{API_URI_ENVVAR_NAME}` environment variable: {api_uri}")
        if configured_uri != api_uri:
            print(f" [*] Updating settings to use supplied Phylum API URI: {api_uri} ...")
            settings.setdefault("connection", {})
            settings["connection"]["uri"] = api_uri
            with phylum_settings_path.open("w", encoding="utf-8") as f:
                yaml.dump(settings, f)
        else:
            print(" [+] Supplied API URI matches existing settings value")
    else:
        print(f" [+] Phylum API URI NOT supplied as an option or `{API_URI_ENVVAR_NAME}` environment variable")
        if settings_file_existed:
            print(f" [-] The value in the existing settings file will be used: {configured_uri}")
        else:
            print(f" [-] The CLI will use the PRODUCTION instance: {configured_uri}")


def confirm_setup() -> None:
    """Check to ensure everything is working."""
    phylum_bin_path, _ = get_phylum_bin_path()

    if is_token_set(get_phylum_settings_path()):
        # Check that the token and API URI were setup correctly by using them to display the current auth status
        cmd = [str(phylum_bin_path), "auth", "status"]
        subprocess.run(cmd, check=True)
    else:
        print(" [!] Existing token not found. Can't confirm setup.")

    # Print the help message to aid log review
    cmd = [str(phylum_bin_path), "--help"]
    subprocess.run(cmd, check=True)


def get_args(args=None):
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
    """Main entrypoint."""
    args = get_args(args=args)

    if args.version:
        print(f" [+] Phylum CLI version was specified as: {args.version}")
        args.version = version_check(args.version)
    else:
        print(" [+] Phylum CLI version not specified")
        args.version = version_check(default_phylum_cli_version())
    print(f" [*] Using Phylum CLI version: {args.version}")

    if args.list_releases:
        print(" [*] Looking up supported releases ...")
        releases = ", ".join(supported_releases())
        print(f" [=] Supported releases: {releases}")
        return 0

    tag_name = args.version
    print(f" [*] Looking up supported targets for release {tag_name} ...")
    supported_target_triples = supported_targets(tag_name)
    if args.list_targets:
        targets = ", ".join(supported_target_triples)
        print(f" [=] Supported targets for release {tag_name}: {targets}")
        return 0

    target_triple = args.target
    if target_triple not in supported_target_triples:
        raise SystemExit(f" [!] The identified target triple `{target_triple}` is not supported for release {tag_name}")

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
                raise zipfile.BadZipFile(f" [!] There was a bad file in the zip archive {archive_name}")
            extracted_dir = temp_dir_path / f"phylum-{target_triple}"
            zip_file.extractall(path=temp_dir)

        # This may look wrong, but a decision was made to manually handle global installs
        # in the places it is required instead of updating the CLI's install script.
        # Reference: https://github.com/phylum-dev/cli/pull/671
        if args.global_install:
            # Current assumptions for this method:
            #   * the /usr/local/bin directory exists, has proper permissions, and is on the PATH for all users
            #   * the install is on a system with glibc
            cmd = ["install", "-m", "0755", "phylum", "/usr/local/bin/phylum"]
        else:
            cmd = ["sh", "install.sh"]
        subprocess.run(cmd, check=True, cwd=extracted_dir)

    process_uri_option(args)
    process_token_option(args)
    confirm_setup()

    return 0


if __name__ == "__main__":
    sys.exit(main())
