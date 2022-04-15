# Contributing

Contributions are welcome and appreciated!

Phylum is the future of software supply chain security and is eager to provide integrations across the diverse
set of environments and ecosystems used by developers. If there is an unsupported use case for managing the
security of your dependencies, we want to know about it. If there is a way Phylum can be used to make your life
as a developer easier, we want to be there for you and do it!

_You_ can contribute in many ways:

## Types of Contributions

### Report Bugs

Report bugs at <https://github.com/phylum-dev/phylum-ci/issues>.

Please use the bug report template which should remind you to include:

* A clear and consise description of the bug
* Detailed steps to reproduce the bug
* Expected behavior
* Screenshots, where appropriate
* Additional context
  * Your operating system name and version
  * Any details about your local setup that might be helpful in troubleshooting

### Fix Bugs

Look through the GitHub issues for bugs to work on, which will be labeled with `bug`.

### Implement Features

Look through the GitHub issues for features to work on, which will be labeled with `enhancement`.

### Write Documentation

The `phylum-ci` project could always use more documentation, whether as part of the
official phylum-ci docs, in docstrings, or even on the web in blog posts, articles, and such.

### Submit Feedback

The best way to send feedback is to file an issue at <https://github.com/phylum-dev/phylum-ci/issues>.

If you are proposing a feature, please use the feature request template which should remind you to include:

* Explain in detail how it would work
* Keep the scope as narrow as possible, to make it easier to implement
* Provide additional context
* Add acceptance criteria

## Local Development

Ready to contribute with code submissions and pull requests (PRs)?
Here's how to set up `phylum-ci` for local development.

1. Clone the `phylum-ci` repo locally

    ```sh
    git clone git@github.com:phylum-dev/phylum-ci.git
    ```

2. Ensure all supported Python versions are installed locally
   1. The strategy is to support all released minor versions of Python that are not end-of-life yet
   2. The current list
      1. at the time of this writing is 3.7, 3.8, 3.9, and 3.10
      2. can be inferred with the Python Developer's Guide, which maintains the [status of active Python releases](https://devguide.python.org/#status-of-python-branches)
   3. It is recommended to use [`pyenv`](https://github.com/pyenv/pyenv) to manage multiple Python installations

    ```sh
    # Use `pyenv install --list` to get available versions and usually install the latest patch version.
    # NOTE: These versions are examples; the latest patch version available from pyenv should be used in place of `.x`.
    #       example: `pyenv install --list |grep 3.9.` to show latest patch version for the cpython 3.9 minor release.
    pyenv install 3.7.x
    pyenv install 3.8.x
    pyenv install 3.9.x
    pyenv install 3.10.x
    pyenv rehash
    # Ensure all environments are available globally (helps tox to find them)
    pyenv global 3.10.x 3.9.x 3.8.x 3.7.x
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
    # Dependencies will be checked automatically in CI during a PR, but checking locally is possible:
    phylum analyze poetry.lock
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

9. Submit a pull request (PR) through the GitHub website

## Pull Request Guidelines

Before you submit a pull request, check that it meets these guidelines:

* Does this PR have an associated issue?
* Have you ensured that you have met the expected acceptance criteria?
* Have you created sufficient tests?
* Have you updated all affected documentation?
* Have you updated the CHANGELOG?
* Have you applied labels to this PR, to usually include at least one `Semver-*` label?
  * These are used to better automate the GitHub release notes
  * Use the `ignore-for-release` label to keep the PR out of the release notes

The pull request should work for Python 3.6, 3.7, 3.8 and 3.9.
Check <https://github.com/phylum-dev/phylum-ci/actions> and make sure that the tests
pass for all supported Python versions.

## Tips

To run a subset of tests from the tox test environments, call `tox` from `poetry` and
interact with `pytest` by passing additional positional arguments:

```sh
# run a specific test module across all test environments
poetry run tox tests/test_phylum_ci.py
# run a specific test module across a specific test environment
poetry run tox -e py39 test/test_phylum_ci.py
# run a specific test function within a test module, in a specific test environment
poetry run tox -e py310 test/test_phylum_ci.py::test_python_version
# passing additional options to pytest requires using the double dash escape
poetry run tox -e py310 -- --help
```
