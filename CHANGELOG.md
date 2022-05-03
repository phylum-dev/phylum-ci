# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
The entries in this changelog are primarily automatically generated through the use of
[conventional commits](https://www.conventionalcommits.org) and the
[Python Semantic Release](https://python-semantic-release.readthedocs.io/en/latest/index.html) tool.
However, some entries may be manually edited, where it helps for clarity and understanding.

<!--next-version-placeholder-->

## v0.2.0-rc.0 (2022-05-03)


## 0.1.1 - 2022-04-25
### Added
* `phylum-init` script entry point and initial functionality
* Test workflows for local and CI based testing
* Preview and Release workflows for Staging and Production environments
* Phylum analyze workflow for PRs

## 0.0.1 - 2022-03-28
### Added
* Basic Python project structure
  * Make use of `poetry` for environment, dependency, and package build/publish workflows
  * Not enough to provide any real functionality
  * Just enough to have a first release on TestPyPI and PyPI to claim the package name
* Basic test structure, making use of `pytest`
* This `CHANGELOG.md` file to adhere to a standard for documenting changes
* A `README.md` file to explain how to do local development with this structure
