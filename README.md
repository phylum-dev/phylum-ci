# phylum-ci
[![PyPI](https://img.shields.io/pypi/v/phylum)](https://pypi.org/project/phylum/)
![PyPI - Status](https://img.shields.io/pypi/status/phylum)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/phylum)](https://pypi.org/project/phylum/)
[![GitHub](https://img.shields.io/github/license/phylum-dev/phylum-ci)][license]
[![GitHub issues](https://img.shields.io/github/issues/phylum-dev/phylum-ci)][issues]
![GitHub last commit](https://img.shields.io/github/last-commit/phylum-dev/phylum-ci)
[![GitHub Workflow Status (branch)][workflow_shield]][workflow_test]
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)][CoC]
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)][pre-commit]
[![Poetry](https://img.shields.io/endpoint?url=https://python-poetry.org/badge/v0.json)][poetry]
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)][black]
[![Downloads](https://static.pepy.tech/badge/phylum/month)][downloads]
[![Discord](https://img.shields.io/discord/1070071012353376387?logo=discord)][discord_invite]

Utilities for integrating Phylum into CI pipelines (and beyond)

[license]: https://github.com/phylum-dev/phylum-ci/blob/main/LICENSE
[issues]: https://github.com/phylum-dev/phylum-ci/issues
[workflow_shield]: https://img.shields.io/github/actions/workflow/status/phylum-dev/phylum-ci/test.yml?branch=main&label=tests&logo=GitHub
[workflow_test]: https://github.com/phylum-dev/phylum-ci/actions/workflows/test.yml
[CoC]: https://github.com/phylum-dev/phylum-ci/blob/main/CODE_OF_CONDUCT.md
[pre-commit]: https://github.com/pre-commit/pre-commit
[poetry]: https://python-poetry.org/
[black]: https://github.com/psf/black
[downloads]: https://pepy.tech/project/phylum
[discord_invite]: https://discord.gg/Fe6pr5eW6p

## Installation and usage

### Installation

The `phylum` Python package is pip installable for the environment of your choice:

```sh
pip install phylum
```

It can also be installed in an isolated environment with the excellent [`pipx` tool](https://pypa.github.io/pipx/):

```sh
# Globally install the app(s) on your system in an isolated virtual environment for the package
pipx install phylum

# Use the apps from the package in an ephemeral environment
pipx run --spec phylum phylum-init <options>
pipx run --spec phylum phylum-ci <options>
```

These installation methods require Python 3.9+ to run.
For a self contained environment, consider using the Docker image as described below.

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

# Run it from a git repo directory containing at least one supported lockfile or manifest
docker run -it --rm -e PHYLUM_API_KEY --mount type=bind,src=$(pwd),dst=/phylum -w /phylum phylumio/phylum-ci
```

The default Docker image contains `git` and the installed `phylum` Python package.
It also contains an installed version of the Phylum CLI and all required tools needed for [lockfile generation].
An advantage of using the default Docker image is that the complete environment is packaged and made available with
components that are known to work together.

One disadvantage to the default image is it's size. It can take a while to download and may provide more tools than
required for your specific use case. Special `slim` tags of the `phylum-ci` image are provided as an alternative.
These tags differ from the default image in that they do not contain the required tools needed for [lockfile generation]
(with the exception of the `pip` tool). The `slim` tags are significantly smaller and will allow integrations relying
on them to complete faster. They are useful for those instances where *no* manifest files are present and/or *only*
lockfiles are used.

```sh
# Get the "latest" `slim` tagged image
docker pull phylumio/phylum-ci:slim
```

When using the `latest` tagged image, the version of the Phylum CLI is the `latest` available.
There are additional image tag options available to specify a specific release of the `phylum-ci` project and a specific
version of the Phylum CLI, in the form of `<phylum-ci version>-CLIv<Phylum CLI version>`.
Each of these also has a `-slim` variant that does not support [lockfile generation]. Here are image tag examples:

```sh
# Get the most current release of *both* `phylum-ci` and the Phylum CLI
docker pull phylumio/phylum-ci:latest

# Get the image with `phylum-ci` version 0.35.2 and Phylum CLI version 5.7.1
docker pull phylumio/phylum-ci:0.35.2-CLIv5.7.1

# Get the `slim` image with `phylum-ci` version 0.36.0 and Phylum CLI version 5.7.1
docker pull phylumio/phylum-ci:0.36.0-CLIv5.7.1-slim
```

[lockfile generation]: https://docs.phylum.io/cli/lockfile_generation

#### `phylum-init` Script Entry Point

The `phylum-init` script can be used to fetch and install the Phylum CLI.
It will attempt to install the latest released version of the CLI but can be specified to fetch a specific version.
It will attempt to automatically determine the correct CLI release, based on the platform where the script is run, but
a specific release target can be specified.
It will accept a Phylum token from an environment variable or specified as an option, but will also function in the case
that no token is provided. This can be because there is already a token set that should continue to be used or because
no token exists and one will need to be manually created or set, after the CLI is installed.

The options for `phylum-init`, automatically updated to be current for the latest release:

> **HINT:** Click on the image to bring up the SVG file, which should allow for search and copy/paste functionality.

![phylum-init options](https://raw.githubusercontent.com/phylum-dev/phylum-ci/main/docs/img/phylum-init_options.svg)

#### `phylum-ci` Script Entry Point

The `phylum-ci` script is for analyzing dependency file (lockfiles and manifests) changes.
The script can be used locally or from within a Continuous Integration (CI) environment.
It will attempt to detect the CI platform based on the environment from which it is run and act accordingly.
The current CI platforms/environments supported are:

|Platform/Environment|Information Link|
|--------------------|---------------------|
|GitHub Actions|[Documentation][github_docs]|
|GitLab CI|[Documentation][gitlab_docs]|
|Azure Pipelines|[Documentation][azure_docs]|
|Bitbucket Pipelines|[Documentation][bb_pipelines_docs]|
|Git `pre-commit` Hooks|[Documentation][precommit_docs]|

There is also support for local use. This is the "fall-through" case used when no other environment is detected.
This can be useful to analyze dependency files locally, prior to or after submitting a pull/merge request (PR/MR) to a
CI system. It can also help in establishing a successful submission prior to submitting a PR/MR to a CI system.
Additionally, local use can aid troubleshooting after submitting a PR/MR to a CI system and getting unexpected results.

The options for `phylum-ci`, automatically updated to be current for the latest release:

> **HINT:** Click on the image to bring up the SVG file, which should allow for search and copy/paste functionality.

![phylum-ci options](https://raw.githubusercontent.com/phylum-dev/phylum-ci/main/docs/img/phylum-ci_options.svg)

[github_docs]: https://docs.phylum.io/phylum-ci/github_actions
[gitlab_docs]: https://docs.phylum.io/phylum-ci/gitlab_ci
[azure_docs]: https://docs.phylum.io/phylum-ci/azure_pipelines
[bb_pipelines_docs]: https://docs.phylum.io/phylum-ci/bitbucket_pipelines
[precommit_docs]: https://docs.phylum.io/phylum-ci/git_precommit

## License

Copyright (C) 2022  Phylum, Inc.

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public
License as published by the Free Software Foundation, either version 3 of the License or any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program.
If not, see <https://www.gnu.org/licenses/gpl.html> or write to `phylum@phylum.io` or `engineering@phylum.io`

## Contributing

Suggestions and help are welcome. Feel free to open an issue or otherwise contribute.
More information is available on the [contributing documentation][contributing] page.

[contributing]: https://github.com/phylum-dev/phylum-ci/blob/main/CONTRIBUTING.md

## Code of Conduct

Everyone participating in the `phylum-ci` project, and in particular in the issue tracker and pull requests, is
expected to treat other people with respect and more generally to follow the guidelines articulated in the
[Code of Conduct][CoC].

## Security Disclosures

Found a security issue in this repository? See the [security policy][security]
for details on coordinated disclosure.

[security]: https://github.com/phylum-dev/phylum-ci/blob/main/docs/security.md

## Change log

All notable changes to this project are documented in the [CHANGELOG][changelog].

The format of the change log is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
The entries in the changelog are primarily automatically generated through the use of
[conventional commits](https://www.conventionalcommits.org) and the
[Python Semantic Release](https://python-semantic-release.readthedocs.io/en/latest/index.html) tool.
However, some entries may be manually edited, where it helps for clarity and understanding.

[changelog]: https://github.com/phylum-dev/phylum-ci/blob/main/CHANGELOG.md
