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
    MIN_CLI_VER_FOR_INSTALL,
    REQ_TIMEOUT,
    SUPPORTED_ARCHES,
    SUPPORTED_PLATFORMS,
    TOKEN_ENVVAR_NAME,
)
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
    prefix_len = len(prefix)
    if version.startswith(prefix):
        version = version[prefix_len:]

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


def get_latest_version():
    """Get the "latest" version programmatically and return it."""
    # API Reference: https://docs.github.com/en/rest/releases/releases#get-the-latest-release
    github_api_url = "https://api.github.com/repos/phylum-dev/cli/releases/latest"

    headers = {"Accept": "application/vnd.github+json"}
    req = requests.get(github_api_url, headers=headers, timeout=REQ_TIMEOUT)
    req.raise_for_status()
    req_json = req.json()

    # The "name" entry stores the GitHub Release name, which could be set to something other than the version.
    # Using the "tag_name" entry is better since the tags are much more tightly coupled with the release version.
    latest_version = req_json.get("tag_name")

    return latest_version


@lru_cache(maxsize=1)
def supported_releases() -> List[str]:
    """Get the most recent supported releases programmatically and return them."""
    # API Reference: https://docs.github.com/en/rest/releases/releases#list-releases
    github_api_url = "https://api.github.com/repos/phylum-dev/cli/releases"

    headers = {"Accept": "application/vnd.github+json"}
    query_params = {"per_page": 100}
    req = requests.get(github_api_url, headers=headers, params=query_params, timeout=REQ_TIMEOUT)
    req.raise_for_status()
    req_json = req.json()

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

    headers = {"Accept": "application/vnd.github+json"}
    req = requests.get(github_api_url, headers=headers, timeout=REQ_TIMEOUT)
    req.raise_for_status()
    req_json = req.json()

    assets = req_json.get("assets", [])
    targets: List[str] = []
    prefix, suffix = "phylum-", ".zip"
    for asset in assets:
        name = asset.get("name", "")
        if name.startswith(prefix) and name.endswith(suffix):
            target = name.replace(prefix, "").replace(suffix, "")
            targets.append(target)

    return list(set(targets))


def version_check(version):
    """Check a given version for validity and return a normalized form of it."""
    if version == "latest":
        version = get_latest_version()

    version = version.lower()
    if not version.startswith("v"):
        version = f"v{version}"

    supported_versions = supported_releases()
    if version not in supported_versions:
        releases = ", ".join(supported_versions)
        raise argparse.ArgumentTypeError(f"version must be from a supported release: {releases}")

    return version


def get_target_triple():
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
    with open(path, "wb") as f:
        f.write(req.content)
    print("Done")


def get_archive_url(tag_name, archive_name):
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
    """Process the token option as parsed from the arguments."""
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


def setup_token(token):
    """Setup the CLI credentials with a provided token."""
    phylum_bin_path = get_expected_phylum_bin_path()
    phylum_settings_path = get_phylum_settings_path()

    # The phylum CLI settings.yaml file won't exist upon initial install
    # but running a command will trigger the CLI to generate it
    if not phylum_settings_path.exists():
        cmd = [str(phylum_bin_path), "version"]
        subprocess.run(cmd, check=True)

    yaml = YAML()
    settings_dict = yaml.load(phylum_settings_path.read_text(encoding="utf-8"))
    settings_dict.setdefault("auth_info", {})
    settings_dict["auth_info"]["offline_access"] = token
    with open(phylum_settings_path, "w", encoding="utf-8") as f:
        yaml.dump(settings_dict, f)

    # Check that the token was setup correctly by using it to display the current auth status
    cmd = [str(phylum_bin_path), "auth", "status"]
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
        default="latest",
        type=version_check,
        help="""The version of the Phylum CLI to install. Can be specified as `latest` or a specific tagged release,
            with or without the leading `v`.""",
    )
    parser.add_argument(
        "-t",
        "--target",
        default=get_target_triple(),
        help="The target platform type where the CLI will be installed.",
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
        help=f"""Phylum user token. Can also specify this option's value by setting the `{TOKEN_ENVVAR_NAME}`
            environment variable. The value specified with this option takes precedence when both are provided.
            Leave this option and it's related environment variable unspecified to either (1) use an existing token
            already set in the Phylum config file or (2) to manually populate the token with a `phylum auth login` or
            `phylum auth register` command after install.""",
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

    if args.list_releases:
        print("Looking up supported releases ...")
        releases = ", ".join(supported_releases())
        print(f"Supported releases: {releases}")
        return 0

    tag_name = args.version
    supported_target_triples = supported_targets(tag_name)
    if args.list_targets:
        print(f"Looking up supported targets for release {tag_name} ...")
        targets = ", ".join(supported_target_triples)
        print(f"Supported targets for release {tag_name}: {targets}")
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
                raise zipfile.BadZipFile(f"There was a bad file in the zip archive {archive_name}")
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

    process_token_option(args)

    # Check to ensure everything is working
    phylum_bin_path, _ = get_phylum_bin_path()
    cmd = [str(phylum_bin_path), "--help"]
    subprocess.run(cmd, check=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
