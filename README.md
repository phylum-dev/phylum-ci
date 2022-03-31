# phylum-ci
<!--
[![PyPI](https://img.shields.io/pypi/v/phylum-ci)](https://pypi.org/project/phylum-ci/)
![PyPI - Status](https://img.shields.io/pypi/status/phylum-ci)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/phylum-ci)](https://pypi.org/project/phylum-ci/)
[![GitHub](https://img.shields.io/github/license/phylum-dev/phylum-ci)](https://github.com/phylum-dev/phylum-ci/blob/main/LICENSE)
[![GitHub issues](https://img.shields.io/github/issues/phylum-dev/phylum-ci)](https://github.com/phylum-dev/phylum-ci/issues)
![GitHub last commit](https://img.shields.io/github/last-commit/phylum-dev/phylum-ci)
TODO: enable build status shield(s) when there are workflows to reference
[![Build Status](https://github.com/phylum-dev/phylum-ci/actions/workflows/test.yml/badge.svg)](https://github.com/phylum-dev/phylum-ci/actions/workflows/test.yml)
-->

Python package for handling CI and other integrations

## Local Development
Here's how to set up `phylum-ci` for local development.

1. Clone the `phylum-ci` repo locally

    ```sh
    git clone git@github.com:phylum-dev/phylum-ci.git
    ```

2. Ensure all supported Python versions are installed locally
   1. The strategy is to support all released minor versions of Python that are not end-of-life yet
   2. The current list is 3.7, 3.8, 3.9, and 3.10, but the Python Developer's Guide can be referenced for the [status of active Python releases](https://devguide.python.org/#status-of-python-branches)
   3. It is recommended to use [`pyenv`](https://github.com/pyenv/pyenv) to manage multiple Python installations

    ```sh
    # `pyenv install --list` to get available versions and usually install the latest patch version
    pyenv install 3.7.13
    pyenv install 3.8.13
    pyenv install 3.9.11
    pyenv install 3.10.3
    pyenv rehash
    # ensure all environments are available globally (helps tox to find them)
    pyenv global 3.10.3 3.9.11 3.8.13 3.7.13
    ```

3. Ensure [poetry](https://python-poetry.org/docs/) is installed
4. Install dependencies with `poetry`, which will automatically create a virtual environment:

    ```sh
    cd phylum-ci
    poetry install
    ```

5. Create a branch for local development:

    ```sh
    git checkout -b <name-of-your-branch>
    ```

    Now you can make your changes locally.

6. If new dependencies are added, ensure the `poetry.lock` file is updated (and committed):

    ```sh
    poetry lock
    ```

7. When you're done making changes, check that your changes pass the tests:

    ```sh
    poetry run tox
    ```

8. Commit your changes and push your branch to GitHub:

    ```sh
    git add .
    git commit -m "Description of the changes goes here"
    git push --set-upstream origin <name-of-your-branch>
    ```

9. Submit a pull request through the GitHub website
