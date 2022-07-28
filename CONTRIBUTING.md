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

### Add New Integrations

Got a continuous integration (CI) environment where you'd like to see `phylum-ci` operate? Just add a new integration
for it by writing an implementation for that platform. It's simply a matter of defining a new class that inherits from
the `CIBase` class and defining the handful of abstract methods needed to represent the unique features of operating in
that CI environment. Look at existing CI integrations for examples and inspiration. The base class docstrings provide
more details about the expected inputs and outputs for each of the abstract methods.

### Write Documentation

The `phylum-ci` project could always use more documentation, whether as part of the
official phylum docs, in docstrings, or even on the web in blog posts, articles, and such.

### Increase Test Coverage

There can always be more and better tests to improve the overall test coverage. Contributions to unit or functional
tests will help make the project more robust, less prone to regressions, and easier for everyone to contribute as
it will be more likely that changes are made in a way that don't break other parts of the project. Even if there is
already 100% test coverage, there may still be room for contributions. For instance, it may be the case that certain
functionality or use cases are not covered in the existing set of tests.

### Submit Feedback

The best way to send feedback is to file an issue at <https://github.com/phylum-dev/phylum-ci/issues>.

If you are proposing a feature, please use the feature request template which should remind you to:

* Explain in detail how it would work
* Keep the scope as narrow as possible, to make it easier to implement
* Provide additional context
* Add acceptance criteria

## Security Disclosures

Found a security issue in this repository? See the [security policy](docs/security.md)
for details on coordinated disclosure.

## Code of Conduct

Everyone participating in the `phylum-ci` project, and in particular in the issue tracker and pull requests, is
expected to treat other people with respect and more generally to follow the guidelines articulated in the
[Code of Conduct](./CODE_OF_CONDUCT.md).

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
      2. can be inferred with the Python Developer's Guide, which maintains the
         [status of active Python releases](https://devguide.python.org/#status-of-python-branches)
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

6. If new dependencies are added, do so in a way that does not add upper version constraints and ensure
   the `poetry.lock` file is updated (and committed):

    ```sh
    # Unless there is a reason to do so, prefer to add dependencies without constraints
    poetry add "new-dependency-name==*"

    # When a version constraint is not specified, poetry chooses one. For example, the command:
    #
    #   $ poetry add new-dependency-name
    #
    # results in a caret-style version constraint added to the dependency in pyproject.toml:
    #
    #   new-dependency-name = "^1.2.3"
    #
    # Unless the constraint was intentional, change the pyproject.toml entry to remove the constraint:
    #
    #   new-dependency-name = "*"

    # Update the lockfile and the local environment to get the latest versions of dependencies
    poetry update

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

* Does this PR have an associated issue (i.e., `closes #<issueNum>` in the PR description)?
* Have you ensured that you have met the expected acceptance criteria?
* Have you created sufficient tests?
* Have you updated all affected documentation?

The pull request should work for Python 3.6, 3.7, 3.8 and 3.9.
Check <https://github.com/phylum-dev/phylum-ci/actions> and make sure that the tests
pass for all supported Python versions.

The [Semantic Pull Requests](https://github.com/apps/semantic-pull-requests) GitHub app is in use for this repository
as a means to ensure each PR that gets merged back to the `main` branch adheres to the
[conventional commit](https://www.conventionalcommits.org) strategy. This means that either the PR title (when
squash merging) or any included commit (when rebase merging) must adhere to the conventional commit format. This is
important because the conventional commits made to the default branch are used to automatically bump release versions,
populate the changelog, and create releases.

## Tips

To run a subset of tests from the tox test environments, call `tox` from `poetry` and
interact with `pytest` by passing additional positional arguments:

```sh
# run a specific test module across all test environments
poetry run tox tests/unit/test_package_metadata.py

# run a specific test module across a specific test environment
poetry run tox -e py39 tests/unit/test_package_metadata.py

# run a specific test function within a test module, in a specific test environment
poetry run tox -e py310 tests/unit/test_package_metadata.py::test_python_version

# passing additional options to pytest requires using the double dash escape
poetry run tox -e py310 -- --help
```

To run a script entry point with the local checkout of the code (in develop mode), use `poetry`:

```sh
# If not done previously, ensure the project is installed by poetry (only required once)
poetry install

# Use the `poetry run` command to ensure the installed project is used
poetry run phylum-init -h
```

To iterate during development of the `phylum-ci` integrations, it can be helpful to force the analysis of the lockfile,
even when it has not changed. It can also be useful to ensure all dependencies are considered. To do so, use the flags:

```sh
# long form options
poetry run phylum-ci --force-analysis --all-deps

# short form options
poetry run phylum-ci -fa
```
