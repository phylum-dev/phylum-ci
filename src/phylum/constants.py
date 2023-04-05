"""Provide constants for use throughout the package."""
from phylum import __version__

# This is the minimum CLI version supported for new installs.
# Ability to specify multiple lockfiles was added in v4.5.0
MIN_CLI_VER_FOR_INSTALL = "v4.5.0"

# This is the minimum CLI version supported for existing installs.
# Ability to specify multiple lockfiles was added in v4.5.0
MIN_CLI_VER_INSTALLED = "v4.5.0"

# Keys are lowercase machine hardware names as returned from `uname -m`.
# Values are the mapped rustc architecture.
SUPPORTED_ARCHES = {
    "aarch64": "aarch64",
    "arm64": "aarch64",
    "x86_64": "x86_64",
    "amd64": "x86_64",
}

# Keys are lowercase operating system name as returned from `uname -s`.
# Values are the mapped rustc platform, which is the vendor-os_type[-environment_type].
SUPPORTED_PLATFORMS = {
    "linux": "unknown-linux-gnu",
    "darwin": "apple-darwin",
}

# Environment variable name to hold the Phylum CLI token used to access the backend API.
# The API token can also be set via the environment variable `PHYLUM_API_KEY`, which will take precedence over
# the `offline_access` parameter in the `settings.yaml` file.
TOKEN_ENVVAR_NAME = "PHYLUM_API_KEY"  # nosec ; this is NOT a hard-coded password

# These are the currently supported lockfiles.
# Keys are the standard lockfile filename, optionally specified with glob syntax.
# Values are the name of the tool that generates the lockfile.
SUPPORTED_LOCKFILES = {
    # Javascript/Typescript
    "package-lock.json": "npm",
    "yarn.lock": "yarn",
    # Ruby
    "Gemfile.lock": "gem",
    # Python
    "requirements.txt": "pip",
    "Pipfile.lock": "pipenv",
    "poetry.lock": "poetry",
    # C#
    "*.csproj": "nuget",
    # Java
    "effective-pom.xml": "mvn",
    "gradle.lockfile": "gradle",
    # Go
    "go.sum": "go",
    # Rust
    "Cargo.lock": "cargo",
    # SBOM
    "*.spdx.json": "spdx",
    "*.spdx.yaml": "spdx",
    "*.spdx.yml": "spdx",
    "*.spdx": "spdx",
}

# Timeout value, in seconds, to tell the Python Requests package to stop waiting for a response.
# Reference: https://requests.readthedocs.io/en/latest/user/quickstart/#timeouts
REQ_TIMEOUT: float = 10.0

# User-Agent header to use when making web requests, to identify this tool instead of falling
# back to the default provided by the Python Requests package (e.g., `python-requests/2.28.1`).
PHYLUM_USER_AGENT = f"phylum-ci/{__version__}"
