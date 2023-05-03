"""Provide constants for use throughout the package."""
from phylum import __version__

# This is the minimum CLI version supported for new installs.
# The switch to policy based analysis was made in v5.0.0-rc2
MIN_CLI_VER_FOR_INSTALL = "v5.0.0-rc2"

# This is the minimum CLI version supported for existing installs.
# The switch to policy based analysis was made in v5.0.0-rc2
MIN_CLI_VER_INSTALLED = "v5.0.0-rc2"

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

# Environment variable name to hold the Phylum CLI token used to access the backend API.
# The API token can also be set via the environment variable `PHYLUM_API_KEY`, which will take precedence over
# the `offline_access` parameter in the `settings.yaml` file.
ENVVAR_NAME_TOKEN = "PHYLUM_API_KEY"  # noqa: S105 ; this is NOT a hard-coded password

# Environment variable name to hold the URI of the Phylum API instance used to access the backend API.
ENVVAR_NAME_API_URI = "PHYLUM_API_URI"

# These are help messages that are used for both `phylum-init` and `phylum-ci` and specified here to stay DRY
HELP_MSG_TARGET = "The target platform type where the CLI will be installed."
HELP_MSG_VERSION = """The version of the Phylum CLI to install. Can be specified as `latest` or a specific tagged
    release, with or without the leading `v`. Default behavior is to use the installed version and fall back to `latest`
    when no CLI is already installed."""
HELP_MSG_TOKEN = f"""Phylum user token. Can also specify this option's value by setting the `{ENVVAR_NAME_TOKEN}`
    environment variable. The value specified with this option takes precedence when both are provided. Leave this
    option and it's related environment variable unspecified to either (1) use an existing token already set in the
    Phylum settings file or (2) to manually populate the token with a `phylum auth login` or `phylum auth register`
    command after install."""
HELP_MSG_API_URI = f"""URI of Phylum API instance to use. Can also specify this option's value by setting the
    `{ENVVAR_NAME_API_URI}` environment variable. The value specified with this option takes precedence when both are
    provided. When not specified, the CLI will use the default value for the PRODUCTION instance for new installs and
    the existing value in the Phylum settings file when available.
    Example: specify 'https://api.staging.phylum.io' to point to the STAGING instance.
    Hint: ensure the value for `--phylum-token` is correct for the instance specified here."""

# The common Phylum header that must exist as the first text in the first line of all analysis output
PHYLUM_HEADER = "# Phylum OSS Supply Chain Risk Analysis"
