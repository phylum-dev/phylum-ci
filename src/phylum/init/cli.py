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
from pathlib import Path
from typing import Optional, Tuple

import requests
from packaging.utils import canonicalize_version
from packaging.version import InvalidVersion, Version
from phylum import __version__
from phylum.common import CustomFormatter
from phylum.constants import SUPPORTED_ARCHES, SUPPORTED_PLATFORMS, SUPPORTED_TARGET_TRIPLES, TOKEN_ENVVAR_NAME
from phylum.init import SCRIPT_NAME
from phylum.init.sig import verify_minisig
from ruamel.yaml import YAML


def use_legacy_paths(version):
    """Predicate to specify whether legacy paths should be used for a given version.

    The Phylum config and binary paths changed following the v2.2.0 release, to adhere to the XDG Base Directory Spec.
    Reference: https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html
    """
    return Version(canonicalize_version(version)) <= Version("v2.2.0")


def get_phylum_settings_path(version):
    """Get the Phylum settings path based on a provided version."""
    home_dir = pathlib.Path.home()
    version = version_check(version)

    config_home_path = os.getenv("XDG_CONFIG_HOME")
    if not config_home_path:
        config_home_path = home_dir / ".config"

    phylum_config_path = pathlib.Path(config_home_path) / "phylum" / "settings.yaml"
    if use_legacy_paths(version):
        phylum_config_path = home_dir / ".phylum" / "settings.yaml"

    return phylum_config_path


def get_expected_phylum_bin_path(version):
    """Get the expected path to the Phylum CLI binary based on a provided version."""
    home_dir = pathlib.Path.home()
    version = version_check(version)

    phylum_bin_path = home_dir / ".local" / "bin" / "phylum"
    if use_legacy_paths(version):
        phylum_bin_path = home_dir / ".phylum" / "phylum"

    return phylum_bin_path


def get_phylum_cli_version(cli_path: Path) -> str:
    """Get the version of the installed and active Phylum CLI and return it."""
    cmd = f"{cli_path} --version"
    version = subprocess.run(cmd.split(), check=True, capture_output=True, text=True).stdout.strip().lower()

    # Starting with Python 3.9, the str.removeprefix() method was introduced to do this same thing
    prefix = "phylum "
    prefix_len = len(prefix)
    if version.startswith(prefix):
        version = version[prefix_len:]

    return version


def get_phylum_bin_path(version: str = None) -> Tuple[Optional[Path], Optional[str]]:
    """Get the current path and corresponding version to the Phylum CLI binary and return them.

    Provide a CLI version as a fallback method for looking on an explicit path,
    based on the expected path for that version.
    """
    # Look for `phylum` on the PATH first
    which_cli_path = shutil.which("phylum")

    if which_cli_path is None and version is not None:
        # Maybe `phylum` is installed already but not on the PATH or maybe the PATH has not been updated in this
        # context. Look in the specific location expected by the provided version.
        expected_cli_path = get_expected_phylum_bin_path(version)
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

    req = requests.get(github_api_url, timeout=5.0)
    req.raise_for_status()
    req_json = req.json()

    # The "name" entry stores the GitHub Release name, which could be set to something other than the version.
    # Using the "tag_name" entry is better since the tags are much more tightly coupled with the release version.
    latest_version = req_json.get("tag_name")

    return latest_version


def version_check(version):
    """Check a given version for validity and return a normalized form of it."""
    if version == "latest":
        version = get_latest_version()

    version = version.lower()
    if not version.startswith("v"):
        version = f"v{version}"

    try:
        # The release layout structure changed starting with v2.0.0 and support here is only for the new layout
        if Version("v2.0.0") > Version(canonicalize_version(version)):
            raise argparse.ArgumentTypeError("version must be at least v2.0.0")
    except InvalidVersion as err:
        raise argparse.ArgumentTypeError("an invalid version was provided") from err

    return version


def get_target_triple():
    """Get the "target triple" from the current system and return it."""
    arch = SUPPORTED_ARCHES.get(platform.uname().machine.lower(), "unknown")
    plat = SUPPORTED_PLATFORMS.get(platform.uname().system.lower(), "unknown")
    return f"{arch}-{plat}"


def save_file_from_url(url, path):
    """Save a file from a given URL to a local file path, in binary mode."""
    print(f" [*] Getting {url} file ...", end="")
    req = requests.get(url, timeout=5.0)
    req.raise_for_status()
    print("Done")

    print(f" [*] Saving {url} file to {path} ...", end="")
    with open(path, "wb") as f:
        f.write(req.content)
    print("Done")


def get_archive_url(version, archive_name):
    """Craft an archive download URL from a given version and archive name.

    Despite the name, the `version` is really what the GitHub API for releases calls the `tag_name`.
    Reference: https://docs.github.com/en/rest/releases/releases#get-a-release-by-tag-name
    """
    github_base_uri = "https://github.com/phylum-dev/cli/releases"
    archive_url = f"{github_base_uri}/download/{version}/{archive_name}"

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
    phylum_settings_path = get_phylum_settings_path(args.version)

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
        setup_token(token, args)


def setup_token(token, args):
    """Setup the CLI credentials with a provided token and path to phylum binary."""
    phylum_bin_path = get_expected_phylum_bin_path(args.version)
    phylum_settings_path = get_phylum_settings_path(args.version)

    # The phylum CLI settings.yaml file won't exist upon initial install
    # but running a command will trigger the CLI to generate it
    if not phylum_settings_path.exists():
        cmd = f"{phylum_bin_path} version".split()
        subprocess.run(cmd, check=True)

    yaml = YAML()
    settings_dict = yaml.load(phylum_settings_path.read_text(encoding="utf-8"))
    settings_dict.setdefault("auth_info", {})
    settings_dict["auth_info"]["offline_access"] = token
    with open(phylum_settings_path, "w", encoding="utf-8") as f:
        yaml.dump(settings_dict, f)

    # Check that the token was setup correctly by using it to display the current auth status
    cmd = f"{phylum_bin_path} auth status".split()
    subprocess.run(cmd, check=True)


def get_args(args=None):
    """Get the arguments from the command line and return them."""
    parser = argparse.ArgumentParser(
        prog=SCRIPT_NAME,
        description="Fetch and install the Phylum CLI",
        formatter_class=CustomFormatter,
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
        choices=SUPPORTED_TARGET_TRIPLES,
        default=get_target_triple(),
        help="The target platform type where the CLI will be installed.",
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

    target_triple = args.target
    if target_triple not in SUPPORTED_TARGET_TRIPLES:
        raise ValueError(f"The identified target triple `{target_triple}` is not currently supported")

    archive_name = f"phylum-{target_triple}.zip"
    minisig_name = f"{archive_name}.minisig"
    archive_url = get_archive_url(args.version, archive_name)
    minisig_url = f"{archive_url}.minisig"
    phylum_bin_path = get_expected_phylum_bin_path(args.version)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = pathlib.Path(temp_dir)
        archive_path = temp_dir_path / archive_name
        minisig_path = temp_dir_path / minisig_name

        save_file_from_url(archive_url, archive_path)
        save_file_from_url(minisig_url, minisig_path)

        verify_minisig(archive_path, minisig_path)

        with zipfile.ZipFile(archive_path, mode="r") as zip_file:
            if zip_file.testzip() is not None:
                raise zipfile.BadZipFile(f"There was a bad file in the zip archive {archive_name}")
            extracted_dir = temp_dir_path / f"phylum-{target_triple}"
            zip_file.extractall(path=temp_dir)

        cmd = "sh install.sh".split()
        subprocess.run(cmd, check=True, cwd=extracted_dir)

    process_token_option(args)

    # Check to ensure everything is working
    cmd = f"{phylum_bin_path} --help".split()
    subprocess.run(cmd, check=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
