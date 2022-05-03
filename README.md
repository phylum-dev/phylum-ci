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
```

It requires Python 3.7+ to run.

### Usage

The `phylum` Python package exposes its functionality with a command line interface (CLI).
To view the options available from the CLI, print the help message from one of the scripts provided as entry points:

```sh
phylum-init -h
```

The functionality can also be accessed by calling the module:

```sh
python -m phylum.init -h
```

#### `phylum-init`

The `phylum-init` script can be used to fetch and install the Phylum CLI.
It will attempt to install the latest released version of the CLI but can be specified to fetch a specific version.
It will attempt to automatically determine the correct CLI release, based on the platform where the script is run, but
a specific release target can be specified.
It will accept a Phylum token from an environment variable or specified as an option, but will also function in the case
that no token is provided. This can be because there is already a token set that should continue to be used or because
no token exists and one will need to be manually created or set, after the CLI is installed.

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
