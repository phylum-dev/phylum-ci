# phylum-ci
[![PyPI](https://img.shields.io/pypi/v/phylum)](https://pypi.org/project/phylum/)
![PyPI - Status](https://img.shields.io/pypi/status/phylum)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/phylum)](https://pypi.org/project/phylum/)
[![GitHub](https://img.shields.io/github/license/phylum-dev/phylum-ci)](https://github.com/phylum-dev/phylum-ci/blob/main/LICENSE)
[![GitHub issues](https://img.shields.io/github/issues/phylum-dev/phylum-ci)](https://github.com/phylum-dev/phylum-ci/issues)
![GitHub last commit](https://img.shields.io/github/last-commit/phylum-dev/phylum-ci)
[![GitHub Workflow Status (branch)](https://img.shields.io/github/workflow/status/phylum-dev/phylum-ci/Test/main?label=Test&logo=GitHub)](https://github.com/phylum-dev/phylum-ci/actions/workflows/test.yml)

Python package for handling CI and other integrations

## Installation and usage

### Installation

The `phylum` Python package is pip installable for the environment of your choice:

```sh
pip install phylum
```

It can also also be installed in an isolated environment with the excellent [`pipx` tool](https://pypa.github.io/pipx/):

```sh
# Globally install the app(s) on your system in an isolated virtual environment for the package
pipx install phylum

# Use the apps from the package in an ephemeral environment
pipx run --spec phylum phylum-init <options>
pipx run --spec phylum phylum-ci <options>
```

These installation methods require Python 3.7+ to run. For a self contained environment, consider using the Docker
image as described below.

### Usage

The `phylum` Python package exposes its functionality with a command line interface (CLI).
To view the options available from the CLI, print the help message from one of the scripts provided as entry points:

```sh
phylum-init -h
phylum-ci -h
```

The functionality can also be accessed by calling the module:

```sh
python -m phylum.init -h
python -m phylum.ci -h
```

The functionality is also exposed in the form of a Docker image:

```sh
# Get the `latest` tagged image
docker pull phylumio/phylum-ci

# View the help
docker run --rm phylumio/phylum-ci phylum-ci --help

# Export a Phylum token (e.g., from `phylum auth token`)
export PHYLUM_API_KEY=$(phylum auth token)

# Run it from a git repo directory containing a `.phylum_project` and a lockfile
docker run -it --rm -e PHYLUM_API_KEY --mount type=bind,src=$(pwd),dst=/phylum -w /phylum phylumio/phylum-ci
```

The Docker image contains `git` and the installed `phylum` Python package.
It also contains an installed version of the Phylum CLI. The version of the Phylum CLI is the `latest` at the time of
the Docker image creation. An advantage of using the Docker image is that the complete environment is packaged and made
available with components that are known to work together.

#### `phylum-init` Script Entry Point

The `phylum-init` script can be used to fetch and install the Phylum CLI.
It will attempt to install the latest released version of the CLI but can be specified to fetch a specific version.
It will attempt to automatically determine the correct CLI release, based on the platform where the script is run, but
a specific release target can be specified.
It will accept a Phylum token from an environment variable or specified as an option, but will also function in the case
that no token is provided. This can be because there is already a token set that should continue to be used or because
no token exists and one will need to be manually created or set, after the CLI is installed.

#### `phylum-ci` Script Entry Point

The `phylum-ci` script is for analyzing lockfile changes.
The script can be used locally or from within a Continuous Integration (CI) environment.
It will attempt to detect the CI platform based on the environment from which it is run and act accordingly.
The current CI platforms/environments supported are:

* GitLab CI
  * See the [GitLab CI Integration documentation](docs/gitlab_ci.md) for more info

* None (local use)
  * This is the "fall-through" case used when no other environment is detected
  * Can be useful to analyze lockfiles locally, prior to or after submitting a pull/merge request (PR/MR) to a CI system
    * Establishing a successful submission prior to submitting a PR/MR to a CI system
    * Troubleshooting after submitting a PR/MR to a CI system and getting unexpected results

## License

MIT - with complete text available in the [LICENSE](LICENSE) file.

## Contributing

Suggestions and help are welcome. Feel free to open an issue or otherwise contribute.
More information is available on the [contributing documentation](CONTRIBUTING.md) page.

## Change log

All notable changes to this project are documented in the [CHANGELOG](CHANGELOG.md).

The format of the change log is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
The entries in the changelog are primarily automatically generated through the use of
[conventional commits](https://www.conventionalcommits.org) and the
[Python Semantic Release](https://python-semantic-release.readthedocs.io/en/latest/index.html) tool.
However, some entries may be manually edited, where it helps for clarity and understanding.
