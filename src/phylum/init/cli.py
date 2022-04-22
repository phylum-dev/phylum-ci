"""Console script for phylum-init."""
import argparse
import os
import pathlib
import platform
import subprocess
import sys
import tempfile
import zipfile

import requests
from packaging.utils import canonicalize_version
from packaging.version import InvalidVersion, Version
from phylum import __version__
from phylum.init import SCRIPT_NAME
from ruamel.yaml import YAML

# These are the currently supported Rust target triples
#
# Targets are identified by their "target triple" which is the string to inform the compiler what kind of output
# should be produced. A target triple consists of three strings separated by a hyphen, with a possible fourth string
# at the end preceded by a hyphen. The first is the architecture, the second is the "vendor", the third is the OS
# type, and the optional fourth is environment type.
#
# References:
#   * https://doc.rust-lang.org/nightly/rustc/platform-support.html
#   * https://rust-lang.github.io/rfcs/0131-target-specification.html
SUPPORTED_TARGET_TRIPLES = (
    "aarch64-apple-darwin",
    "x86_64-apple-darwin",
    "x86_64-unknown-linux-musl",
)
# Keys are lowercase machine hardware names as returned from `uname -m`.
# Values are the mapped rustc architecture.
SUPPORTED_ARCHES = {
    "arm64": "aarch64",
    "amd64": "x86_64",
}
# Keys are lowercase operating system name as returned from `uname -s`.
# Values are the mapped rustc platform, which is the vendor-os_type[-environment_type].
SUPPORTED_PLATFORMS = {
    "linux": "unknown-linux-musl",
    "darwin": "apple-darwin",
}

TOKEN_ENVVAR_NAME = "PHYLUM_TOKEN"
PHYLUM_PATH = pathlib.Path.home() / ".phylum"
PHYLUM_BIN_PATH = PHYLUM_PATH / "phylum"
SETTINGS_YAML_PATH = PHYLUM_PATH / "settings.yaml"

# TODO: Add logging support, a verbosity option to control it, and swap out print statements for logging


def version_check(version):
    """Check a given version for validity and return a normalized form of it."""
    if version == "latest":
        return version

    version = version.lower()
    if not version.startswith("v"):
        version = f"v{version}"

    # TODO: Check for valid versions by using the GitHub API to compare against actual releases?
    #       raise argparse.ArgumentTypeError(f"version {version} does not exist as a release")

    try:
        # Ensure the version is at least v2.0.0, which is when the release layout structure changed
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
    req = requests.get(url, timeout=2.0)
    req.raise_for_status()
    print("Done")

    print(f" [*] Saving {url} file to {path} ...", end="")
    with open(path, "wb") as f:
        f.write(req.content)
    print("Done")


def get_archive_url(version, archive_name):
    """Craft an archive download URL from a given version and archive name."""
    github_base_uri = "https://github.com/phylum-dev/cli/releases"
    latest_version_uri = f"{github_base_uri}/latest/download"
    specific_version_uri = f"{github_base_uri}/download"

    # TODO: Use the GitHub API instead?
    # GITHUB_API = "https://api.github.com"

    if version == "latest":
        archive_url = f"{latest_version_uri}/{archive_name}"
    else:
        archive_url = f"{specific_version_uri}/{version}/{archive_name}"

    return archive_url


def is_token_set(token=None):
    """Check if any token is already set.

    Optionally, check if a specific given `token` is set.
    """
    if not SETTINGS_YAML_PATH.exists():
        return False
    yaml = YAML()
    settings_dict = yaml.load(SETTINGS_YAML_PATH.read_text(encoding="utf-8"))
    configured_token = settings_dict.get("auth_info", {}).get("offline_access")
    if configured_token is None:
        return False
    if token is not None:
        if token != configured_token:
            return False
    return True


def setup_token(token):
    """Setup the CLI credentials with a provided token."""
    # The phylum CLI settings.yaml file won't exist upon initial install
    # but running a command will trigger the CLI to generate it
    if not SETTINGS_YAML_PATH.exists():
        cmd_line = [PHYLUM_BIN_PATH, "version"]
        subprocess.run(cmd_line, check=True)

    yaml = YAML()
    settings_dict = yaml.load(SETTINGS_YAML_PATH.read_text(encoding="utf-8"))
    settings_dict.setdefault("auth_info", {})
    settings_dict["auth_info"]["offline_access"] = token
    with open(SETTINGS_YAML_PATH, "w", encoding="utf-8") as f:
        yaml.dump(settings_dict, f)

    # Check that the token was setup correctly by using it to display the current auth status
    cmd_line = [PHYLUM_BIN_PATH, "auth", "status"]
    subprocess.run(cmd_line, check=True)


def get_args():
    """Get the arguments from the command line and return them.

    Use `args` parameter as dependency injection for testing.
    """
    parser = argparse.ArgumentParser(
        prog=SCRIPT_NAME,
        description="Fetch and install the Phylum CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "-v",
        "--phylum-version",
        dest="version",
        default="latest",
        type=version_check,
        help="the version of the Phylum CLI to install",
    )
    parser.add_argument(
        "-t",
        "--target",
        choices=SUPPORTED_TARGET_TRIPLES,
        default=get_target_triple(),
        help="the target platform type where the CLI will be installed",
    )
    parser.add_argument(
        "-k",
        "--phylum-token",
        dest="token",
        help=f"""Phylum user token. Can also specify this option's value by setting the `{TOKEN_ENVVAR_NAME}`
            environment variable. The value specified with this option takes precedence when both are provided.""",
    )
    # TODO: Add a --list option, to show which versions are available?
    # TODO: Account for pre-releases?
    # parser.add_argument("-p", "--pre-release", action="store_true", help="specify to include pre-release versions")
    parser.add_argument("--version", action="version", version=f"{SCRIPT_NAME} {__version__}")

    return parser.parse_args()


def main():
    """Main entrypoint."""
    args = get_args()

    token = args.token or os.getenv(TOKEN_ENVVAR_NAME)
    if not token and not is_token_set():
        raise ValueError(f"Phylum Token not supplied as option or `{TOKEN_ENVVAR_NAME}` environment variable")

    target_triple = args.target
    if target_triple not in SUPPORTED_TARGET_TRIPLES:
        raise ValueError(f"The identified target triple `{target_triple}` is not currently supported")

    archive_name = f"phylum-{target_triple}.zip"
    minisig_name = f"{archive_name}.minisig"
    archive_url = get_archive_url(args.version, archive_name)
    minisig_url = f"{archive_url}.minisig"

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = pathlib.Path(temp_dir)
        archive_path = temp_dir_path / archive_name
        minisig_path = temp_dir_path / minisig_name

        save_file_from_url(archive_url, archive_path)
        save_file_from_url(minisig_url, minisig_path)

        # TODO: Verify the download with minisign

        with zipfile.ZipFile(archive_path, mode="r") as zip_file:
            if zip_file.testzip() is not None:
                raise zipfile.BadZipFile(f"There was a bad file in the zip archive {archive_name}")
            extracted_dir = temp_dir_path
            top_level_zip_entry = zip_file.infolist()[0]
            if top_level_zip_entry.is_dir():
                extracted_dir = temp_dir_path / top_level_zip_entry.filename
            zip_file.extractall(path=temp_dir)

        # Run the install script
        cmd_line = ["sh", "install.sh"]
        subprocess.run(cmd_line, check=True, cwd=extracted_dir)

    if not is_token_set(token=token):
        setup_token(token)

    # Do a check to ensure everything is working
    cmd_line = [PHYLUM_BIN_PATH, "--help"]
    subprocess.run(cmd_line, check=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
