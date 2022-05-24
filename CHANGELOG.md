# Changelog
All notable changes to this project will be documented in this file.

The format is partially based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
The entries in this changelog are primarily automatically generated through the use of
[conventional commits](https://www.conventionalcommits.org) and the
[Python Semantic Release](https://python-semantic-release.readthedocs.io/en/latest/index.html) tool.
However, some entries may be manually edited, where it helps for clarity and understanding.

<!--next-version-placeholder-->

## v0.5.2 (2022-05-24)
### Fix
* Ensure notes are not duplicated in GitLab MRs ([#43](https://github.com/phylum-dev/phylum-ci/issues/43)) ([`a8ffe7f`](https://github.com/phylum-dev/phylum-ci/commit/a8ffe7f0ed5f8a209001abee9b90049e8d5eb4b3))

## v0.5.1 (2022-05-20)
### Fix
* Sync package issue key name changes from CLI v3.4.0 release ([#41](https://github.com/phylum-dev/phylum-ci/issues/41)) ([`2f5f8d5`](https://github.com/phylum-dev/phylum-ci/commit/2f5f8d5017c9d113a367ea47c906d9e5600a86ef))

## v0.5.0 (2022-05-19)
### Feature
* Add support for GitLab CI environment ([#38](https://github.com/phylum-dev/phylum-ci/issues/38)) ([`732daea`](https://github.com/phylum-dev/phylum-ci/commit/732daea1737c5bc3235245c3d25068209e5ddb06))

## v0.4.0 (2022-05-18)
### Feature
* Expose the Python package as a Docker image ([#37](https://github.com/phylum-dev/phylum-ci/issues/37)) ([`0976f1d`](https://github.com/phylum-dev/phylum-ci/commit/0976f1df5c78b258f53c50b1dbeeb3ef2328f683))

## v0.3.0 (2022-05-12)
### Feature
* Add `phylum-ci` script entry point to analyze lockfile changes ([#36](https://github.com/phylum-dev/phylum-ci/issues/36)) ([`f1cbac7`](https://github.com/phylum-dev/phylum-ci/commit/f1cbac7d05e8132c4f92831a5e11c86639ee8375))

## v0.2.1 (2022-05-04)
### Fix
* Use `phylum-bot` account instead of a personal account ([#34](https://github.com/phylum-dev/phylum-ci/issues/34)) ([`40ba743`](https://github.com/phylum-dev/phylum-ci/commit/40ba74373196bb63997fed9690e238ba51319e45))

## v0.2.0-rc.0 (2022-05-03)
### Added
* Modern release workflow

## v0.1.1 (2022-04-25)
### Added
* `phylum-init` script entry point and initial functionality
* Test workflows for local and CI based testing
* Preview and Release workflows for Staging and Production environments
* Phylum analyze workflow for PRs

## v0.0.1 (2022-03-28)
### Added
* Basic Python project structure
  * Make use of `poetry` for environment, dependency, and package build/publish workflows
  * Not enough to provide any real functionality
  * Just enough to have a first release on TestPyPI and PyPI to claim the package name
* Basic test structure, making use of `pytest`
* This `CHANGELOG.md` file to adhere to a standard for documenting changes
* A `README.md` file to explain how to do local development with this structure
