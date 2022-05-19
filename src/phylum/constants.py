"""Provide constants for use throughout the package."""

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
    "aarch64": "aarch64",
    "arm64": "aarch64",
    "x86_64": "x86_64",
    "amd64": "x86_64",
}
# Keys are lowercase operating system name as returned from `uname -s`.
# Values are the mapped rustc platform, which is the vendor-os_type[-environment_type].
SUPPORTED_PLATFORMS = {
    "linux": "unknown-linux-musl",
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
    "pom.xml": "mvn",
    "gradle.lockfile": "gradle",
}

# Timeout value, in seconds, to tell the Python Requests package to stop waiting for a response.
# Reference: https://2.python-requests.org/en/master/user/quickstart/#timeouts
REQ_TIMEOUT: float = 5.0
