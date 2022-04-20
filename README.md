# phylum-ci
[![PyPI](https://img.shields.io/pypi/v/phylum)](https://pypi.org/project/phylum/)
![PyPI - Status](https://img.shields.io/pypi/status/phylum)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/phylum)](https://pypi.org/project/phylum/)
[![GitHub](https://img.shields.io/github/license/phylum-dev/phylum-ci)](https://github.com/phylum-dev/phylum-ci/blob/main/LICENSE)
[![GitHub issues](https://img.shields.io/github/issues/phylum-dev/phylum-ci)](https://github.com/phylum-dev/phylum-ci/issues)
![GitHub last commit](https://img.shields.io/github/last-commit/phylum-dev/phylum-ci)
[![GitHub Workflow Status (branch)](https://img.shields.io/github/workflow/status/phylum-dev/phylum-ci/Test/develop?label=Test&logo=GitHub)](https://github.com/phylum-dev/phylum-ci/actions/workflows/test.yml)

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
<!-- TODO: Fill this section in as functionality is added -->
The `phylum` Python package exposes its functionality with a command line interface (CLI).
To view the options available from the CLI, print the help message from one of the scripts provided as entry points:

```sh
phylum-init -h
```

## License

MIT - with complete text available in the [LICENSE](LICENSE) file.

## Contributing

This is a new project and suggestions and help are welcome. Feel free to open an issue or otherwise contribute.
More information is available on the [contributing documentation](CONTRIBUTING.md) page.

## Change log

All notable changes to this project are documented in the [CHANGELOG](CHANGELOG.md).

The format of the change log is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
