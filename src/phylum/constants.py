"""Provide constants for use throughout the package."""

# This is the minimum CLI version supported for new installs.
# `--label` was added as a long form option to the analyze command starting with v3.12.0
MIN_CLI_VER_FOR_INSTALL = "v3.12.0"

# This is the minimum CLI version supported for existing installs.
# `--label` was added as a long form option to the analyze command starting with v3.12.0
MIN_CLI_VER_INSTALLED = "v3.12.0"

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
    "Pipfile": "pipenv",
    "poetry.lock": "poetry",
    # C#
    "*.csproj": "nuget",
    # Java
    "effective-pom.xml": "mvn",
    "gradle.lockfile": "gradle",
}

# Timeout value, in seconds, to tell the Python Requests package to stop waiting for a response.
# Reference: https://2.python-requests.org/en/master/user/quickstart/#timeouts
REQ_TIMEOUT: float = 10.0
