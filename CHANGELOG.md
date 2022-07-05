# Changelog
All notable changes to this project will be documented in this file.

The format is partially based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
The entries in this changelog are primarily automatically generated through the use of
[conventional commits](https://www.conventionalcommits.org) and the
[Python Semantic Release](https://python-semantic-release.readthedocs.io/en/latest/index.html) tool.
However, some entries may be manually edited, where it helps for clarity and understanding.

<!--next-version-placeholder-->

## v0.9.1 (2022-07-01)
### Fix
* Detect lockfile changes in GitHub PRs ([#73](https://github.com/phylum-dev/phylum-ci/issues/73)) ([`c119a4a`](https://github.com/phylum-dev/phylum-ci/commit/c119a4ae9f6446ae518bde6f2acb0a9354031434))
* Apply total threshold to all risk domains ([#71](https://github.com/phylum-dev/phylum-ci/issues/71)) ([`0b19167`](https://github.com/phylum-dev/phylum-ci/commit/0b191676d63ece1c98b64e322ce0822af34c9bd8))

## v0.9.0 (2022-06-27)
### Feature
* Add support for GitHub Actions CI environment ([#68](https://github.com/phylum-dev/phylum-ci/issues/68)) ([`b59da0a`](https://github.com/phylum-dev/phylum-ci/commit/b59da0a3fb6ba460536ecd25c115ee6e6df8e7a4))

## v0.8.1 (2022-06-16)
### Fix
* Docker image tags are inconsistent ([#67](https://github.com/phylum-dev/phylum-ci/issues/67)) ([`00a2b53`](https://github.com/phylum-dev/phylum-ci/commit/00a2b53e603b6740f0b185e990ccde5511fb1968))

## v0.8.0 (2022-06-15)
### Feature
* Coordinate phylum-ci Docker image releases with new CLI releases ([#63](https://github.com/phylum-dev/phylum-ci/issues/63)) ([`82b57e2`](https://github.com/phylum-dev/phylum-ci/commit/82b57e2d7040c0db3b2892730763a407fe642e1b))
* Expose version arguments with a short form `-V` ([`92e9149`](https://github.com/phylum-dev/phylum-ci/commit/92e9149006e93162d8911a80d65c690ffba0239b))

### Fix
* Using gh cli requires specifying a token ([#65](https://github.com/phylum-dev/phylum-ci/issues/65)) ([`1e070fd`](https://github.com/phylum-dev/phylum-ci/commit/1e070fdc70bbfb7c7c4bda122fcfddc5a70a1013))
* Logical prefixed `not` fails GitHub workflow syntax ([#64](https://github.com/phylum-dev/phylum-ci/issues/64)) ([`00a5cb1`](https://github.com/phylum-dev/phylum-ci/commit/00a5cb17c8652129d246eb426c4039170615cda3))
* Re-enable building docker images with pre-built distributions ([`c5d7aa0`](https://github.com/phylum-dev/phylum-ci/commit/c5d7aa0157b5321ef27015023c66d71d1be71ac3))

### Documentation
* Add a Code of Conduct ([#60](https://github.com/phylum-dev/phylum-ci/issues/60)) ([`c953f68`](https://github.com/phylum-dev/phylum-ci/commit/c953f68f54ded778ad1cf8210b6ef8154ef29199))
* Add a security policy ([`21fce1b`](https://github.com/phylum-dev/phylum-ci/commit/21fce1b62a78e906caebbb4dcc340668767cf80e))
* Reformat code examples to add whitespace lines ([`a31fdce`](https://github.com/phylum-dev/phylum-ci/commit/a31fdce6b9faa2d3e9d6eccf87dcd561e158f981))

### Performance
* Optimize Docker image ([`0e28066`](https://github.com/phylum-dev/phylum-ci/commit/0e2806655b3adc3779b590f60b8631d7542c6f61))

## v0.7.0 (2022-06-01)
### Feature
* Use a single character for "single dash" options ([`6a4b032`](https://github.com/phylum-dev/phylum-ci/commit/6a4b032262222173e69463fbcc232555f499c97e))

### Breaking
* The short options for the following arguments changed ([`6a4b032`](https://github.com/phylum-dev/phylum-ci/commit/6a4b032262222173e69463fbcc232555f499c97e)):
  * `--force-analysis` was changed from `-fa` to `-f`
  * `--force-install` was changed from `-fi` to `-i`
  * `--vul-threshold` was changed from `-vt` to `-u`
  * `--mal-threshold` was changed from `-mt` to `-m`
  * `--eng-threshold` was changed from `-et` to `-e`
  * `--lic-threshold` was changed from `-lt` to `-c`
  * `--aut-threshold` was changed from `-at` to `-o`

## v0.6.0 (2022-05-27)
### Feature
* Provide an option to force analysis ([#55](https://github.com/phylum-dev/phylum-ci/pull/55)) ([`4d6fc3b`](https://github.com/phylum-dev/phylum-ci/commit/4d6fc3b842cec004d655d1c1a63553a0c54e1d54))
* Default to project settings for risk domain thresholds ([#52](https://github.com/phylum-dev/phylum-ci/pull/52)) ([`9f10442`](https://github.com/phylum-dev/phylum-ci/commit/9f10442ba41300093c65a5e5e1ff2fdb71c0772e))
* Default to analyzing new dependencies only ([#53](https://github.com/phylum-dev/phylum-ci/pull/53)) ([`e0894fc`](https://github.com/phylum-dev/phylum-ci/commit/e0894fcf9f52d3014798f8676a5ff2360e725a8a))

### Fix
* Ensure the "CI Platform Name" portion of a label is correct ([#55](https://github.com/phylum-dev/phylum-ci/pull/55)) ([`1867fb6`](https://github.com/phylum-dev/phylum-ci/commit/1867fb6e543183aa894cec4e06828069d62dee01))
* Enable Phylum UI links for groups ([#54](https://github.com/phylum-dev/phylum-ci/issues/54)) ([`8775a63`](https://github.com/phylum-dev/phylum-ci/commit/8775a6392456fe64f97efae7f8d514ebf66f6949))

### Breaking Changes
* Individual risk domain threshold values can be set with command line options, which now accept values between 0 and 100, inclusive
  * Previously, the accepted values were between 0 and 99, inclusive
* The option to analyze `--new-deps-only` was removed and replaced with one that has the opposite meaning: `--all-deps`
* The short option to `--force-install` was changed from `-f` to `-fi`

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
