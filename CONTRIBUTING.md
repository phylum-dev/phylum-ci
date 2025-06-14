# Contributing

Contributions are welcome and appreciated!

Phylum is the software supply chain security company and is eager to provide integrations across the diverse
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
  * Output from the highest verbosity setting (`-vvv`)

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

2. Optional: Install [pre-commit](https://pre-commit.com/) and the local hooks

    ```sh
    # If the `pre-commit` tool is not already installed, the recommended method is to use `pipx`,
    # with the PyPI Package Firewall (https://docs.phylum.io/package_firewall/pypi)
    pipx install \
      --index-url https://<PHYLUM_ORG>%2F<PHYLUM_GROUP>:<PHYLUM_API_KEY>@pypi.phylum.io/simple/ \
      pre-commit

    # Installing with homebrew is another good option
    brew install pre-commit

    # Use the `pre-commit` tool to install the git hooks used by the repository
    pre-commit install
    ```

3. Ensure all supported Python versions are installed locally
   1. The strategy is to support the current/latest release plus the previous three minor versions of Python
   2. The current list
      1. at the time of this writing is 3.10, 3.11, 3.12, and 3.13
      2. can be inferred with the Python Developer's Guide, which maintains the
         [status of active Python releases](https://devguide.python.org/versions/)
   3. It is recommended to use [`pyenv`](https://github.com/pyenv/pyenv) to manage multiple Python installations

    ```sh
    # Take advantage of the `pyenv` feature that automatically resolves
    # specified minor versions to the latest patch version
    pyenv install 3.10
    pyenv install 3.11
    pyenv install 3.12
    pyenv install 3.13

    # Rebuild the shim files
    pyenv rehash

    # Ensure all environments are available globally (helps tox to find them)
    pyenv global 3.13 3.12 3.11 3.10
    ```

4. Ensure [poetry v2.1+](https://python-poetry.org/docs/) is installed
   1. PEP 621 support was added and the `pyproject.toml` file was updated to match in Poetry v2.0.0
   2. Support for alternate build backends was added in Poetry v2.1.0
5. Configure `poetry` to make use of the [PyPI Package Firewall](https://docs.phylum.io/package_firewall/pypi)

    ```sh
    cd phylum-ci

    # Add the Poetry package firewall as the primary source
    poetry source add --priority primary phylum https://pypi.phylum.io/simple/

    # Configure credentials to make use of the source
    poetry config http-basic.phylum "<PHYLUM_ORG>%2F<PHYLUM_GROUP>" "<PHYLUM_API_KEY>"

    # NOTE: Internal developers (employees of Veracode) should use the `Phylum/Phylum` org/group
    #
    # poetry config http-basic.phylum "Phylum%2fPhylum" "$(phylum auth token)"
    ```

6. Install dependencies with `poetry`, which will automatically create a virtual environment:

    ```sh
    # OPTIONAL: Configure Poetry to use an "in-project" virtual environment
    poetry config virtualenvs.in-project true

    # Verify the lockfile corresponds to the current version of `pyproject.toml`
    # and validate the content of the `pyproject.toml` file:
    poetry check --lock --strict

    # Install the main dependencies only:
    poetry sync

    # Alternatively, specific dependency groups can be installed at the
    # same time. It makes sense to add the "test" and "qa" groups now
    # if new code is going to be added and tested:
    poetry sync --with test,qa
    ```

7. Create a branch for local development:

    ```sh
    git checkout -b <name-of-your-branch>
    ```

    Now you can make your changes locally.

8. If new dependencies are added, do so in a way that does not add upper version constraints and ensure
   the `poetry.lock` file is updated (and committed):

    ```sh
    # Unless there is a reason to do so, prefer to add dependencies without constraints
    poetry add --lock "new-dependency-name==*"

    # When a version constraint is not specified, poetry chooses one. For example, the command:
    #
    #   $ poetry add --lock --group qa new-dependency-name
    #
    # results in a caret-style version constraint added to the "qa" group dependency in pyproject.toml:
    #
    #   new-dependency-name = "^1.2.3"
    #
    # Unless the constraint was intentional, change the pyproject.toml entry to remove the constraint:
    #
    #   new-dependency-name = "*"
    #
    # Similarly, the command:
    #
    #   $ poetry add --lock new-dependency-name
    #
    # results in a PEP 508 compliant dependency specifier added to the "main" dependencies:
    #
    #   "new-dependency-name (>=1.2.3,<2.0.0)"
    #
    # Unless the constraint was intentional, change the pyproject.toml entry to remove the constraint:
    #
    #   "new-dependency-name"

    # Update the lockfile and the local environment to get the latest versions of dependencies
    poetry update --lock --no-cache

    # Dependencies will be checked automatically in CI during a PR. They will also be checked
    # with the local pre-commit hook, if enabled. Manually checking locally is also possible:
    phylum analyze poetry.lock

    # If the dependencies pass the active Phylum policy, they can be installed locally:
    poetry sync --with test,qa
    ```

    **NOTE:** The version of `poetry` used to make changes to the lockfile must match the one specified
    in CI configuration files. Otherwise, the QA status check will fail when submitting a PR. The current
    version can be found in the `.github/workflows/*.yml` files by searching for `POETRY_VERSION`.

9. When you're done making changes, check that your changes pass QA and the tests:

    ```sh
    # Ensure the "test" and "qa" dependency groups are installed, if not done previously
    poetry sync --with test,qa
    poetry run tox run -e qa
    poetry run tox run-parallel
    ```

10. Commit your changes and push your branch to GitHub:

    ```sh
    git add .
    git commit -m "Description of the changes goes here"
    git push --set-upstream origin <name-of-your-branch>
    ```

11. Submit a pull request (PR) through the GitHub website

## Pull Request Guidelines

Before you submit a pull request, check that it meets these guidelines:

* Does this PR have an associated issue (i.e., `closes #<issueNum>` in the PR description)?
* Have you ensured that you have met the expected acceptance criteria?
* Have you created sufficient tests?
* Have you updated all affected documentation?

The pull request should work for Python 3.10, 3.11, 3.12 and 3.13.
Check <https://github.com/phylum-dev/phylum-ci/actions> and make sure that the tests
pass for all supported Python versions.

To ensure quality assurance (QA), a series of checks are performed in a `qa` test.
This test essentially runs the `pre-commit` hooks to ensure proper formatting and linting over the repo.
Sometimes it is necessary to bypass these checks (e.g., via `# noqa` directives). These exceptions should
be rare and include a reason in the comment for the exclusion. Create a new issue and reference that, when
more detail is needed or the exclusion is meant to be temporary.

The [Semantic Pull Requests](https://github.com/apps/semantic-pull-requests) GitHub app is in use for this repository
as a means to ensure each PR that gets merged back to the `main` branch adheres to the
[conventional commit](https://www.conventionalcommits.org) strategy. This means that either the PR title (when
squash merging) or any included commit (when rebase merging) must adhere to the conventional commit format. This is
important because the conventional commits made to the default branch are used to automatically bump release versions,
populate the changelog, and create releases.

## Release Process

See the [release process][release] for more info about how to cut a release and the automation workflows involved.

[release]: https://github.com/phylum-dev/phylum-ci/blob/main/docs/release_process.md

## Tips

To run a subset of tests from the tox test environments, call `tox` from `poetry` and
interact with `pytest` by passing additional positional arguments:

```sh
# passing additional options to pytest requires using the double dash
# escape twice, once for escaping `poetry` and again for escaping `tox`
poetry run -- tox run -e py310 -- --help

# run a specific test module across all test environments in parallel
poetry run -- tox run-parallel -- tests/unit/test_package_metadata.py

# run a specific test module across a specific test environment
poetry run -- tox run -e py310 -- tests/unit/test_package_metadata.py

# run a specific test function within a test module, in a specific test environment
poetry run -- tox run -e py311 -- tests/unit/test_package_metadata.py::test_python_version
```

To run a script entry point with the local checkout of the code (in develop mode), use `poetry`:

```sh
# If not done previously, ensure the project is installed by poetry (only required once)
poetry sync

# Use the `poetry run` command to ensure the installed project is used
poetry run phylum-init -h
```

To iterate during development of the `phylum-ci` integrations, it can be helpful to force the analysis of the
dependency file(s), even when it has not changed. It can also be useful to ensure all dependencies are considered.
To do so, use the flags:

```sh
# long form options
poetry run phylum-ci --force-analysis --all-deps

# short form options
poetry run phylum-ci -fa
```

To get more output and insight into the execution of the scripts, use the `--verbose`/`-v` flag multiple times.
The highest verbosity level, `-vvv`, can be used to get trace level output. This can be useful for troubleshooting
or to capture the full output for submission of a bug.

```sh
# running during development
poetry run phylum-ci -vvv <options>

# running a released version
phylum-ci -vvv <options>
```
