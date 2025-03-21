# Changelog

All notable changes to this project will be documented in this file.

The format is partially based on [Keep a Changelog], and this project adheres to
[Semantic Versioning]. The entries in this changelog are primarily automatically
generated through the use of [conventional commits] and the [Python Semantic Release]
tool. However, some entries may be manually edited, where it helps for clarity
and understanding.

[Keep a Changelog]: https://keepachangelog.com/en/1.0.0/
[Semantic Versioning]: https://semver.org/spec/v2.0.0.html
[conventional commits]: https://www.conventionalcommits.org
[Python Semantic Release]: https://python-semantic-release.readthedocs.io/en/latest/index.html

<!--next-version-placeholder-->

## [v0.58.1](https://github.com/phylum-dev/phylum-ci/compare/v0.58.0...v0.58.1) (2025-03-20)

### Documentation

* Update language for veracode transition ([#543](https://github.com/phylum-dev/phylum-ci/pull/543)) ([`42d05ac`](https://github.com/phylum-dev/phylum-ci/commit/42d05acd61749d72733c315be96794fd943dfdac))

## [v0.58.0](https://github.com/phylum-dev/phylum-ci/compare/v0.57.0...v0.58.0) (2025-01-14)

### Breaking

* Remove `success` comments from prs/mrs ([#526](https://github.com/phylum-dev/phylum-ci/pull/526)) ([`6cca5bd`](https://github.com/phylum-dev/phylum-ci/commit/6cca5bdf4f288952a7d277537b4e2df3c6c1a39c))
  * PRs/MRs will no longer have `SUCCESS` comments.

## [v0.57.0](https://github.com/phylum-dev/phylum-ci/compare/v0.56.0...v0.57.0) (2025-01-09)

### Breaking

* Add python 3.13 support and drop python 3.9 support ([#522](https://github.com/phylum-dev/phylum-ci/pull/522)) ([`5ac96e0`](https://github.com/phylum-dev/phylum-ci/commit/5ac96e042a7e66bc39d6d86b48f6b847a5342e01))
  * Support for Python 3.9 was removed.

### Features

* Ensure git repository access as prerequisite ([#518](https://github.com/phylum-dev/phylum-ci/pull/518)) ([`5317fd9`](https://github.com/phylum-dev/phylum-ci/commit/5317fd98af3c2084a1d49c6fcf40a20b68b89129))

## [v0.56.0](https://github.com/phylum-dev/phylum-ci/compare/v0.55.0...v0.56.0) (2024-12-13)

### Features

* Automatically analyze newly created projects ([#514](https://github.com/phylum-dev/phylum-ci/pull/514)) ([`2683fe4`](https://github.com/phylum-dev/phylum-ci/commit/2683fe4d1f4f972a3c9bcd606936ed7726438272))

## [v0.55.0](https://github.com/phylum-dev/phylum-ci/compare/v0.54.0...v0.55.0) (2024-12-05)

### Features

* Add option to fail for incomplete analysis ([#510](https://github.com/phylum-dev/phylum-ci/pull/510)) ([`d2c21ae`](https://github.com/phylum-dev/phylum-ci/commit/d2c21aecad0abdb270d9b5000c3b83833ecb55a9))

## [v0.54.0](https://github.com/phylum-dev/phylum-ci/compare/v0.53.0...v0.54.0) (2024-12-02)

### Features

* Allow for ignoring non-analysis errors ([#508](https://github.com/phylum-dev/phylum-ci/pull/508)) ([`a372523`](https://github.com/phylum-dev/phylum-ci/commit/a372523830b1e29b828a9ae2a5950b6910b977f5))

## [v0.53.0](https://github.com/phylum-dev/phylum-ci/compare/v0.52.1...v0.53.0) (2024-11-26)

### Features

* Avoid github api calls during version check ([#505](https://github.com/phylum-dev/phylum-ci/pull/505)) ([`25d9c85`](https://github.com/phylum-dev/phylum-ci/commit/25d9c85ff644654e26470253abd8708274f4ef6b))

### Bug Fixes

* `gradle` lockfile generation requires `javac` ([#507](https://github.com/phylum-dev/phylum-ci/pull/507)) ([`17994a6`](https://github.com/phylum-dev/phylum-ci/commit/17994a61291070d431697fe5fcc2215bd140e27f))

## [v0.52.1](https://github.com/phylum-dev/phylum-ci/compare/v0.52.0...v0.52.1) (2024-11-21)

### Bug Fixes

* Account for analysis started in repo sub-dirs ([#504](https://github.com/phylum-dev/phylum-ci/pull/504)) ([`3055ce8`](https://github.com/phylum-dev/phylum-ci/commit/3055ce82d68a5efe1e2878e1a7bbdaa671f525f1))
* Exit cleanly when no current dependencies ([#503](https://github.com/phylum-dev/phylum-ci/pull/503)) ([`d43a047`](https://github.com/phylum-dev/phylum-ci/commit/d43a047d5ac37f74d2a7d3434e605e135ce6d3c0))

## [v0.52.0](https://github.com/phylum-dev/phylum-ci/compare/v0.51.0...v0.52.0) (2024-11-07)

### Breaking

* Add organization support ([#499](https://github.com/phylum-dev/phylum-ci/pull/499)) ([`1ad0ea7`](https://github.com/phylum-dev/phylum-ci/commit/1ad0ea723d897455cf5e3c6cba5a130a3e41f876))
  * Phylum CLI installs before v7.1.4-rc1 are no longer supported. That release is the first one providing support for analysis with organizations via extensions.

## [v0.51.0](https://github.com/phylum-dev/phylum-ci/compare/v0.50.0...v0.51.0) (2024-10-09)

### Feature

* Add windows standalone archive install option ([#481](https://github.com/phylum-dev/phylum-ci/pull/481)) ([`83538a0`](https://github.com/phylum-dev/phylum-ci/commit/83538a03368330e04a9dfa49074b435c10b012ce))

### Fix

* Include `phylum-ci.exe` in release artifacts ([#477](https://github.com/phylum-dev/phylum-ci/pull/477)) ([`23c1e28`](https://github.com/phylum-dev/phylum-ci/commit/23c1e286aa52780c36dd715b56cf4682566e11ad))

## [v0.50.0](https://github.com/phylum-dev/phylum-ci/compare/v0.49.0...v0.50.0) (2024-10-02)

### Breaking

* Add windows support with standalone binary ([#474](https://github.com/phylum-dev/phylum-ci/pull/474)) ([`24a20c9`](https://github.com/phylum-dev/phylum-ci/commit/24a20c95d92b797a397b948b732d28432260cb80))
  * Phylum CLI installs before v7.1.0-rc1 are no longer supported. That release is the first one providing full Windows support.

### Documentation

* Add exit code information ([#465](https://github.com/phylum-dev/phylum-ci/pull/465)) ([`b5842eb`](https://github.com/phylum-dev/phylum-ci/commit/b5842eb705c16245b670366e45f306ebb87ee5d0))

## [v0.49.0](https://github.com/phylum-dev/phylum-ci/compare/v0.48.0...v0.49.0) (2024-08-21)

### Feature

* Add option to exclude dependency files ([#462](https://github.com/phylum-dev/phylum-ci/pull/462)) ([`258709b`](https://github.com/phylum-dev/phylum-ci/commit/258709b1acefb32e9ad88d5839d65f2e59d92d29))

## [v0.48.0](https://github.com/phylum-dev/phylum-ci/compare/v0.47.0...v0.48.0) (2024-07-26)

### Feature

* Add `git-lfs` to docker images ([#453](https://github.com/phylum-dev/phylum-ci/pull/453)) ([`3ad6de5`](https://github.com/phylum-dev/phylum-ci/commit/3ad6de58f8fae5107b623b87f4504389d41e888c))

### Documentation

* Add missing jenkins link ([#444](https://github.com/phylum-dev/phylum-ci/pull/444)) ([`83587b9`](https://github.com/phylum-dev/phylum-ci/commit/83587b9209057bef5257938e4f94db37e7265d39))

## [v0.47.0](https://github.com/phylum-dev/phylum-ci/compare/v0.46.0...v0.47.0) (2024-06-28)

### Feature

* Allow groups to be specified without a project ([#443](https://github.com/phylum-dev/phylum-ci/pull/443)) ([`ec3bd63`](https://github.com/phylum-dev/phylum-ci/commit/ec3bd63c05f9c30b2c700623a0907483c11a7ff8))

## [v0.46.0](https://github.com/phylum-dev/phylum-ci/compare/v0.45.0...v0.46.0) (2024-06-21)

### Feature

* Add `ps` to docker images ([#441](https://github.com/phylum-dev/phylum-ci/pull/441)) ([`474c9b2`](https://github.com/phylum-dev/phylum-ci/commit/474c9b2703931082d8ecfc2c8ce94675f7a2a217))

## [v0.45.0](https://github.com/phylum-dev/phylum-ci/compare/v0.44.1...v0.45.0) (2024-06-12)

### Feature

* Add support for jenkins pipelines ([#438](https://github.com/phylum-dev/phylum-ci/pull/438)) ([`910cca7`](https://github.com/phylum-dev/phylum-ci/commit/910cca7389a9697cccdf4507ca206302b91cfa5a))

### Documentation

* Update docs based on user feedback ([#434](https://github.com/phylum-dev/phylum-ci/pull/434)) ([`f5c12ec`](https://github.com/phylum-dev/phylum-ci/commit/f5c12ecce4c582a03c81fbba1f6807bddeb5a316))

## [v0.44.1](https://github.com/phylum-dev/phylum-ci/compare/v0.44.0...v0.44.1) (2024-06-04)

### Fix

* Account for `cargo_suffix` in cli version ([#433](https://github.com/phylum-dev/phylum-ci/pull/433)) ([`bfbd426`](https://github.com/phylum-dev/phylum-ci/commit/bfbd42628b5fb52016eab323aba7fb9c86ccd4e2))

## [v0.44.0](https://github.com/phylum-dev/phylum-ci/compare/v0.43.0...v0.44.0) (2024-04-04)

### Feature

* Ensure bitbucket repo urls use https scheme ([#406](https://github.com/phylum-dev/phylum-ci/pull/406)) ([`5ea8cb2`](https://github.com/phylum-dev/phylum-ci/commit/5ea8cb260d5dfc361d83b7e4c9e64ba8dd3aad24))

### Documentation

* Recommend triggering scans for default branch ([#407](https://github.com/phylum-dev/phylum-ci/pull/407)) ([`efa67d0`](https://github.com/phylum-dev/phylum-ci/commit/efa67d0e0648a587461aad21ffe7c07bca3f1b63))

## [v0.43.0](https://github.com/phylum-dev/phylum-ci/compare/v0.42.4...v0.43.0) (2024-03-08)

### Feature

* Implement audit mode ([#400](https://github.com/phylum-dev/phylum-ci/pull/400)) ([`1613851`](https://github.com/phylum-dev/phylum-ci/commit/1613851fa82bcaadb5b4d7d67937ae292c6ab02f))

## [v0.42.4](https://github.com/phylum-dev/phylum-ci/compare/v0.42.3...v0.42.4) (2024-03-05)

### Fix

* `pre-commit` hook failures ([#397](https://github.com/phylum-dev/phylum-ci/pull/397)) ([`a6d0f5e`](https://github.com/phylum-dev/phylum-ci/commit/a6d0f5eaae3977e85fbe8779821571dbef93485d))

### Documentation

* Restore integration documentation ([#395](https://github.com/phylum-dev/phylum-ci/pull/395)) ([`a209f58`](https://github.com/phylum-dev/phylum-ci/commit/a209f58170e9462718685a0019bd9a3d5d273470))

## [v0.42.3](https://github.com/phylum-dev/phylum-ci/compare/v0.42.2...v0.42.3) (2024-02-22)

### Fix

* Image failures for non-root uses of `yarn` and `pnpm` ([#391](https://github.com/phylum-dev/phylum-ci/pull/391)) ([`345ecd2`](https://github.com/phylum-dev/phylum-ci/commit/345ecd24124d11abe8a922c1820027d1e5b95b07))

## v0.42.2 (2024-02-09)

### Performance

* Reduce `phylum` binary size for slim images ([#385](https://github.com/phylum-dev/phylum-ci/pull/385)) ([`ac5e477`](https://github.com/phylum-dev/phylum-ci/commit/ac5e47740f9bedaed71b11988d2d22dd7c4a20aa))

## v0.42.1 (2024-01-05)

### Documentation

* Update documentation links ([#370](https://github.com/phylum-dev/phylum-ci/issues/370)) ([`60ee5ca`](https://github.com/phylum-dev/phylum-ci/commit/60ee5ca3cc36b5011d830d7ac2c73ba2f5174ba3))

## v0.42.0 (2023-12-13)

### Breaking

* Phylum CLI installs before v6.0.0-rc3 are no longer supported. That release introduced a number of breaking changes which are only functional with this release of the `phylum` package. ([`35adcaf`](https://github.com/phylum-dev/phylum-ci/commit/35adcaf694368987433da471e5a657190aecfb9f))
* The `--lockfile`/`-l` argument to to the `phylum-ci` script has changed to `--depfile`/`-d`. ([`35adcaf`](https://github.com/phylum-dev/phylum-ci/commit/35adcaf694368987433da471e5a657190aecfb9f))

## v0.41.0 (2023-12-05)

### Feature

* Extend GHA integration to support `pull_request_target` events ([#341](https://github.com/phylum-dev/phylum-ci/issues/341)) ([`6ed6c14`](https://github.com/phylum-dev/phylum-ci/commit/6ed6c14ab5c72f09fb6b9d0a2aea008278e8b927))

### Breaking

* Phylum CLI installs before v5.9.0-rc2 are no longer supported. A version with support for disabling lockfile generation and skipping sandbox usage is required. ([`6ed6c14`](https://github.com/phylum-dev/phylum-ci/commit/6ed6c14ab5c72f09fb6b9d0a2aea008278e8b927))
* The `phylum-ci` return code for a policy violation that results from a Phylum analysis has been changed from 1 to 2 in order to make it distinct from the default failure code that is generated for all raised `SystemExit` exceptions with a message instead of a code. ([`6ed6c14`](https://github.com/phylum-dev/phylum-ci/commit/6ed6c14ab5c72f09fb6b9d0a2aea008278e8b927))

## v0.40.0 (2023-12-04)

### Feature

* Parse current dependencies only once ([#359](https://github.com/phylum-dev/phylum-ci/issues/359)) ([`a96dccb`](https://github.com/phylum-dev/phylum-ci/commit/a96dccb53560967ab561cba8a17f561a88a508aa))

### Fix

* Repository URL sometimes formatted with `False` ([#361](https://github.com/phylum-dev/phylum-ci/issues/361)) ([`195136d`](https://github.com/phylum-dev/phylum-ci/commit/195136d68883efd4a1fe264f29b1607fb4ae922b))

## v0.39.0 (2023-11-27)

### Feature

* Set repository URL for CI environments ([#355](https://github.com/phylum-dev/phylum-ci/issues/355)) ([`28cf1a9`](https://github.com/phylum-dev/phylum-ci/commit/28cf1a9dd687f1912943e70775692e8babea223b))
* Ensure remote `HEAD` set for `CINone` implementation ([#351](https://github.com/phylum-dev/phylum-ci/issues/351)) ([`e303919`](https://github.com/phylum-dev/phylum-ci/commit/e30391908d9a50f0d68bd8cc9c717f51f22d74a0))

## v0.38.0 (2023-11-09)

### Feature

* Support workspace projects for all lockfile types ([#344](https://github.com/phylum-dev/phylum-ci/issues/344)) ([`2bf66c7`](https://github.com/phylum-dev/phylum-ci/commit/2bf66c77f8d39fb3b870d48279045bcf4741219b))
* Cache parsing results of current dependency files ([#342](https://github.com/phylum-dev/phylum-ci/issues/342)) ([`1ceff86`](https://github.com/phylum-dev/phylum-ci/commit/1ceff860a2828c65cc3c92f41938a8816d250119))

### Breaking

* CLI installs prior to v5.8.0 are no longer supported. A Phylum CLI version with the `find-lockable-files` command is needed. ([`2bf66c7`](https://github.com/phylum-dev/phylum-ci/commit/2bf66c77f8d39fb3b870d48279045bcf4741219b))

## v0.37.1 (2023-10-20)

### Fix

* More container tools broken when home-less ([#337](https://github.com/phylum-dev/phylum-ci/issues/337)) ([`403eb7d`](https://github.com/phylum-dev/phylum-ci/commit/403eb7d2326f915c36c743cd94f124a3fe5a61f2))

## v0.37.0 (2023-10-19)

### Feature

* Add Python 3.12 support and drop Python 3.8 support ([#335](https://github.com/phylum-dev/phylum-ci/issues/335)) ([`feb3502`](https://github.com/phylum-dev/phylum-ci/commit/feb35020ce1a49e50151422bd9e1b438d657c273))
* Enforce strict engine control for `npm` ([#336](https://github.com/phylum-dev/phylum-ci/issues/336)) ([`4e69e3e`](https://github.com/phylum-dev/phylum-ci/commit/4e69e3e6da19a5a67c7eb574539f79deeae2ebef))

### Breaking

* Support for Python 3.8 was removed due to the change in CONTRIBUTING policy to support only the current/latest release plus the previous three minor versions of Python. ([`feb3502`](https://github.com/phylum-dev/phylum-ci/commit/feb35020ce1a49e50151422bd9e1b438d657c273))

## v0.36.0 (2023-10-16)

### Feature

* Account for dependency file types ([#324](https://github.com/phylum-dev/phylum-ci/issues/324)) ([`918902d`](https://github.com/phylum-dev/phylum-ci/commit/918902dba1ca32bf67312c5ec8876cbffc95e1fe))
* Replace lockfile detection with `phylum status` ([#322](https://github.com/phylum-dev/phylum-ci/issues/322)) ([`224e3a6`](https://github.com/phylum-dev/phylum-ci/commit/224e3a6e71d4c29593b7c6d3266fae5b5dc44bf7))
* Add lockfile generation support ([#318](https://github.com/phylum-dev/phylum-ci/issues/318)) ([`f96ff48`](https://github.com/phylum-dev/phylum-ci/commit/f96ff48362de5dcf8bfd60291dbda6c47169fa6a))

### Fix

* Container tools broken when home-less ([#329](https://github.com/phylum-dev/phylum-ci/issues/329)) ([`f951e3c`](https://github.com/phylum-dev/phylum-ci/commit/f951e3c76e17502ea617470f7691503ac687b9a0))

### Breaking

* The `phylum-ci` docker image created from the default `Dockerfile` is much larger, containing *all* the required tools for lockfile generation across all supported ecosystems. To retain the previous functionality, a new `slim` tag is offered for those instances where *no* manifest files are present and/or *only* lockfiles are used. ([`f96ff48`](https://github.com/phylum-dev/phylum-ci/commit/f96ff48362de5dcf8bfd60291dbda6c47169fa6a))

### Documentation

* Add more detail for manifest file support ([#328](https://github.com/phylum-dev/phylum-ci/issues/328)) ([`3241d2d`](https://github.com/phylum-dev/phylum-ci/commit/3241d2dc35a7f774b634a24e51f5d72df040f88d))

## v0.35.2 (2023-09-18)

### Fix

* Integrations should check for previous comments ([#305](https://github.com/phylum-dev/phylum-ci/issues/305)) ([`12e7445`](https://github.com/phylum-dev/phylum-ci/commit/12e74456ff061492a435860ab08cd370721b595d))

## v0.35.1 (2023-09-07)

### Fix

* Incorrect new dependency logic ([#304](https://github.com/phylum-dev/phylum-ci/issues/304)) ([`b447b46`](https://github.com/phylum-dev/phylum-ci/commit/b447b46c0f75692cfa22ec3c7a5faa8ab1379329))

## v0.35.0 (2023-08-29)

### Feature

* Add CycloneDX lockfile support ([#297](https://github.com/phylum-dev/phylum-ci/issues/297)) ([`3897879`](https://github.com/phylum-dev/phylum-ci/commit/3897879c6ce90eb74f7e2ab077755b3385207f55))

### Breaking

* CLI installs prior to v5.7.0 are no longer supported. A Phylum CLI version with ability to parse CycloneDX lockfiles is needed. ([`3897879`](https://github.com/phylum-dev/phylum-ci/commit/3897879c6ce90eb74f7e2ab077755b3385207f55))

## v0.34.0 (2023-08-15)

### Feature

* Improve GitLab integration for partial checkouts ([#291](https://github.com/phylum-dev/phylum-ci/issues/291)) ([`ca33672`](https://github.com/phylum-dev/phylum-ci/commit/ca33672ce75c59b4365ca4d618148ce1501a5313))

## v0.33.0 (2023-08-09)

### Feature

* Add `packages.*.lock.json` lockfile detection ([#287](https://github.com/phylum-dev/phylum-ci/issues/287)) ([`00e1d57`](https://github.com/phylum-dev/phylum-ci/commit/00e1d57ecec0778481401cee876175fa827a765d))

## v0.32.1 (2023-08-08)

### Chore

* Add `lockfile` to `PackageDescriptor` ([#282](https://github.com/phylum-dev/phylum-ci/pull/282))

## v0.32.0 (2023-07-19)

### Feature

* Add `pnpm-lock.yaml` and `packages.lock.json` lockfile support ([#277](https://github.com/phylum-dev/phylum-ci/issues/277)) ([`a24b2c2`](https://github.com/phylum-dev/phylum-ci/commit/a24b2c27a6726015c4b830c1bf4a44be03ba836c))

### Breaking

* CLI installs prior to v5.5.0 are no longer supported. A Phylum CLI version with ability to parse `pnpm-lock.yaml` and `packages.lock.json` lockfiles is needed. ([`a24b2c2`](https://github.com/phylum-dev/phylum-ci/commit/a24b2c27a6726015c4b830c1bf4a44be03ba836c))

## v0.31.0 (2023-06-29)

### Feature

* Update the phylum analysis technique ([#269](https://github.com/phylum-dev/phylum-ci/issues/269)) ([`4a6367b`](https://github.com/phylum-dev/phylum-ci/commit/4a6367b2fd53d4594557c3b29d1e7fede5f044d6))

### Documentation

* Remove docs hosted in `documentation` repo ([#264](https://github.com/phylum-dev/phylum-ci/issues/264)) ([`1bcc72b`](https://github.com/phylum-dev/phylum-ci/commit/1bcc72b6a4e7220d447e55304fb99b958c2a5166))

## v0.30.1 (2023-06-09)

### Style

* Account for new report format ([#259](https://github.com/phylum-dev/phylum-ci/pull/259))

## v0.30.0 (2023-05-24)

### Feature

* Add `npm-shrinkwrap.json` and `requirements*.txt` to supported lockfiles ([#250](https://github.com/phylum-dev/phylum-ci/issues/250)) ([`c21b0e6`](https://github.com/phylum-dev/phylum-ci/commit/c21b0e6b18c02549d25e592d558fcbf51c374553))

## v0.29.0 (2023-05-23)

### Feature

* Add logging support and better error output ([#247](https://github.com/phylum-dev/phylum-ci/issues/247)) ([`0350be9`](https://github.com/phylum-dev/phylum-ci/commit/0350be9257cc906583b0a8ede83fe3e0ebe9ff12))

## v0.28.1 (2023-04-14)

### Fix

* Link to Phylum UI project clipped in logs ([#227](https://github.com/phylum-dev/phylum-ci/issues/227)) ([`8d2e91e`](https://github.com/phylum-dev/phylum-ci/commit/8d2e91e0223045525c68d899df63fd75b20c10ba))

## v0.28.0 (2023-04-13)

### Feature

* Switch to policy based operation ([#226](https://github.com/phylum-dev/phylum-ci/issues/226)) ([`ed3532e`](https://github.com/phylum-dev/phylum-ci/commit/ed3532ecc26da657b1a4ae50c65d3f669a2276c7))

### Breaking

* The risk domain threshold options have been removed. ([`ed3532e`](https://github.com/phylum-dev/phylum-ci/commit/ed3532ecc26da657b1a4ae50c65d3f669a2276c7))
* CLI installs prior to v5.0.0 are no longer supported. A Phylum CLI version with ability to return policy results and specify the `--base` option in the `analyze` command is required. ([`ed3532e`](https://github.com/phylum-dev/phylum-ci/commit/ed3532ecc26da657b1a4ae50c65d3f669a2276c7))

## v0.27.0 (2023-04-07)

### Feature

* Provide ability to specify Phylum API URI ([#222](https://github.com/phylum-dev/phylum-ci/issues/222)) ([`80a54db`](https://github.com/phylum-dev/phylum-ci/commit/80a54dbeac19f8e9c411fcff86b9966d3bdd80a8))

### Breaking

* The short option `-u` for `--vul-threshold` was removed. ([`80a54db`](https://github.com/phylum-dev/phylum-ci/commit/80a54dbeac19f8e9c411fcff86b9966d3bdd80a8))

## v0.26.0 (2023-04-05)

### Feature

* Detect SPDX formatted SBOM files ([#220](https://github.com/phylum-dev/phylum-ci/issues/220)) ([`8325cc3`](https://github.com/phylum-dev/phylum-ci/commit/8325cc392ef41026d9c43a059cb6d92e4ddc4d7b))

### Breaking

* Support for Python 3.7 was removed due to its imminent end of life ([`1b65787`](https://github.com/phylum-dev/phylum-ci/commit/1b65787d98f6e97cf16d81aa5c2a91e8bb8896a8))

## v0.25.0 (2023-03-28)

### Feature

* Allow `.phylum_project` file to be optional ([#209](https://github.com/phylum-dev/phylum-ci/issues/209)) ([`7092c93`](https://github.com/phylum-dev/phylum-ci/commit/7092c9359c5e8e11d0b7785d2eed276c6ee9c608))

### Breaking

* CLI installs prior to v4.5.0 are no longer supported. A Phylum CLI version with ability to specify multiple lockfiles is required. ([`7092c93`](https://github.com/phylum-dev/phylum-ci/commit/7092c9359c5e8e11d0b7785d2eed276c6ee9c608))

### Documentation

* Fix support link ([#210](https://github.com/phylum-dev/phylum-ci/issues/210)) ([`ba0240e`](https://github.com/phylum-dev/phylum-ci/commit/ba0240e03f0b929a83da74b0ea8e898cedf62bad))

## v0.24.1 (2023-02-14)

### Fix

* Duplicate PR comments are possible ([#199](https://github.com/phylum-dev/phylum-ci/issues/199)) ([`d660406`](https://github.com/phylum-dev/phylum-ci/commit/d6604066da7acbd1a05a132c7c3456d7395aadbb))

### Documentation

* Align to main website ([#198](https://github.com/phylum-dev/phylum-ci/issues/198)) ([`cc5ff48`](https://github.com/phylum-dev/phylum-ci/commit/cc5ff481ecc1a277eb46c0f1291a5d1620a5772a))

## v0.24.0 (2023-02-10)

### Feature

* Add support for Bitbucket Pipelines ([#196](https://github.com/phylum-dev/phylum-ci/issues/196)) ([`3a95dce`](https://github.com/phylum-dev/phylum-ci/commit/3a95dced668b1ffa01c0c57bc40acafb7e1ab2c9))

### Documentation

* Update GitLab CI documentation ([#191](https://github.com/phylum-dev/phylum-ci/issues/191)) ([`8bd9c72`](https://github.com/phylum-dev/phylum-ci/commit/8bd9c7288af48b9e2d71bec7ca4706bf6533fa16))

## v0.23.1 (2023-01-10)

### Fix

* Link to Phylum UI project clipped in logs ([#186](https://github.com/phylum-dev/phylum-ci/issues/186)) ([`95d6838`](https://github.com/phylum-dev/phylum-ci/commit/95d6838d053efbecab06068b44f5b8396ed49d95))

## v0.23.0 (2023-01-03)

### Feature

* Improve experience around GitHub rate limiting API requests ([#179](https://github.com/phylum-dev/phylum-ci/issues/179)) ([`df5f1e2`](https://github.com/phylum-dev/phylum-ci/commit/df5f1e2db6a9b58c6af80b488d9322393188d14a))

### Breaking

* The `--phylum-release` option (`-r`) default is no longer `latest`. Default behavior now is to use the installed version and fall back to `latest` when no Phylum CLI is already installed. ([`df5f1e2`](https://github.com/phylum-dev/phylum-ci/commit/df5f1e2db6a9b58c6af80b488d9322393188d14a))

## v0.22.1 (2022-12-19)

### Fix

* Issue summary entries repeated in output ([#175](https://github.com/phylum-dev/phylum-ci/issues/175)) ([`30d9e42`](https://github.com/phylum-dev/phylum-ci/commit/30d9e42dab881178a6560a8579a2e0c6a3ca204b))

## v0.22.0 (2022-12-15)

### Feature

* Support Azure Pipelines CI triggers ([#173](https://github.com/phylum-dev/phylum-ci/issues/173)) ([`7d6d859`](https://github.com/phylum-dev/phylum-ci/commit/7d6d859ad368d1ab0a933f24679e3d3c08a40eac))

### Breaking

* For GitLab branch pipelines, the analyzed dependencies are now determined by comparing the lockfile in the branch to the default branch instead of the previous commit that ran in that branch pipeline. All dependencies will be analyzed when the branch pipeline is run on the default branch. ([`7d6d859`](https://github.com/phylum-dev/phylum-ci/commit/7d6d859ad368d1ab0a933f24679e3d3c08a40eac))

## v0.21.0 (2022-12-06)

### Feature

* Add `go.sum` and `Cargo.lock` as supported lockfiles ([#169](https://github.com/phylum-dev/phylum-ci/issues/169)) ([`187a863`](https://github.com/phylum-dev/phylum-ci/commit/187a8634a9c96fc10812f8581087b58f218c9d60))

## v0.20.0 (2022-11-29)

### Feature

* Support RSA SHA256 signature verification in `phylum-init` ([#165](https://github.com/phylum-dev/phylum-ci/issues/165)) ([`4fad7dd`](https://github.com/phylum-dev/phylum-ci/commit/4fad7ddac071de506e0ec684d31b10e4e658ccca))

### Breaking

* CLI installs prior to v3.12.0 are no longer supported.
* CLI installs and upgrades can no longer be confirmed with `.minisig` minisign signatures and must instead use `.signature` RSA SHA256 based signatures. ([`4fad7dd`](https://github.com/phylum-dev/phylum-ci/commit/4fad7ddac071de506e0ec684d31b10e4e658ccca))

## v0.19.0 (2022-11-15)

### Feature

* Extend Azure Pipelines integration to support GitHub repos ([#160](https://github.com/phylum-dev/phylum-ci/issues/160)) ([`39e80ac`](https://github.com/phylum-dev/phylum-ci/commit/39e80ac1c98ceb74056bfe3de60c3043a4db66a8))

## v0.18.0 (2022-11-04)

### Feature

* Add Python 3.11 support ([#157](https://github.com/phylum-dev/phylum-ci/issues/157)) ([`815c368`](https://github.com/phylum-dev/phylum-ci/commit/815c3683b619e910efc3965ddd3f754fa3a11168))

## v0.17.1 (2022-10-17)

### Fix

* Sanitize user input to guard against possible cmd injection ([#144](https://github.com/phylum-dev/phylum-ci/issues/144)) ([`4d72ece`](https://github.com/phylum-dev/phylum-ci/commit/4d72ecee9d226f3e78eeddd93239f22c0e23bf8d))

### Documentation

* Provide more hints about using the SVG files ([#146](https://github.com/phylum-dev/phylum-ci/issues/146)) ([`747e230`](https://github.com/phylum-dev/phylum-ci/commit/747e230e2f3a1628abc0bac90eb51c5e797bb723))

## v0.17.0 (2022-10-10)

### Feature

* Allow for creating projects ([#139](https://github.com/phylum-dev/phylum-ci/issues/139)) ([`e47abec`](https://github.com/phylum-dev/phylum-ci/commit/e47abec72455f2e6f4adb60331dfed15f4bed9e0))
* Support GitLab branch pipelines ([#137](https://github.com/phylum-dev/phylum-ci/issues/137)) ([`1dee2ac`](https://github.com/phylum-dev/phylum-ci/commit/1dee2acfaea1233c45bd65c84034bd04df0ea757))

## v0.16.1 (2022-10-05)

### Fix

* Account for shallow fetch in Azure Pipelines integration ([#135](https://github.com/phylum-dev/phylum-ci/issues/135)) ([`36e2413`](https://github.com/phylum-dev/phylum-ci/commit/36e2413c5336b05801886452c402ccd2537aed19))

## v0.16.0 (2022-09-29)

### Feature

* Add support for Azure Pipelines CI environment ([#127](https://github.com/phylum-dev/phylum-ci/issues/127)) ([`a22de2c`](https://github.com/phylum-dev/phylum-ci/commit/a22de2c0dde2f99127602c156ef5f397cb8220e6))

### Documentation

* Use long form options in documentation examples ([#129](https://github.com/phylum-dev/phylum-ci/issues/129)) ([`bbca9d3`](https://github.com/phylum-dev/phylum-ci/commit/bbca9d3a23697b99a42976bb01b474c39c62ac12))

## v0.15.0 (2022-09-14)

### Feature

* Allow docker image use for non-root users ([`3e87aa9`](https://github.com/phylum-dev/phylum-ci/commit/3e87aa99608807dd8f7469cc72580dd7b10b56f3))
* Don't require serial processing of pre-commit hook ([#115](https://github.com/phylum-dev/phylum-ci/issues/115)) ([`b0fb110`](https://github.com/phylum-dev/phylum-ci/commit/b0fb1109ddd3ab19361611102f41efd2bded565d))

### Breaking

* CLI installs prior to v2.2.0 are no longer supported.  ([`e5c0fca`](https://github.com/phylum-dev/phylum-ci/commit/e5c0fcac7d15adc40fef6002cf054fe28b903c5f))

## v0.14.0 (2022-08-26)

### Feature

* Change supported maven lockfile to `effective-pom.xml` ([#112](https://github.com/phylum-dev/phylum-ci/issues/112)) ([`c98fa8e`](https://github.com/phylum-dev/phylum-ci/commit/c98fa8efa4b8f2b1877b95843bae079838cae565))

## v0.13.3 (2022-08-24)

### Documentation

* Revert bad script options SVG files ([`907e8f2`](https://github.com/phylum-dev/phylum-ci/commit/907e8f2d3acb19a33e7e4cb83a69398db62a5221))

## v0.13.2 (2022-08-24)

### Fix

* Script options auto update still can't find package ([#108](https://github.com/phylum-dev/phylum-ci/issues/108)) ([`967c1c0`](https://github.com/phylum-dev/phylum-ci/commit/967c1c06a2815b5698972279af3f355ad1e80134))

### Documentation

* Revert bad script options SVG files ([`0c9dfc2`](https://github.com/phylum-dev/phylum-ci/commit/0c9dfc21728a7c87f48dee4ec4f4f60432fa08d6))

## v0.13.1 (2022-08-23)

### Fix

* Script options auto update can't find package ([#107](https://github.com/phylum-dev/phylum-ci/issues/107)) ([`9fb7164`](https://github.com/phylum-dev/phylum-ci/commit/9fb71642f95315df8fad441fe39be22b3e13277b))

### Documentation

* Revert bad script options SVG files ([`9d7d6fc`](https://github.com/phylum-dev/phylum-ci/commit/9d7d6fc7980059878032a0f928af87cf4b83c488))

## v0.13.0 (2022-08-22)

### Feature

* Provide a Docker image with glibc instead of musl libc ([#104](https://github.com/phylum-dev/phylum-ci/issues/104)) ([`c5fadb4`](https://github.com/phylum-dev/phylum-ci/commit/c5fadb4eced4029afaf61d833212e63f7082ed2b))

### Breaking

* Versions of the CLI older than v3.8.0-rc2 are no longer possible to install on Linux systems with the `phylum-init` script. ([`c5fadb4`](https://github.com/phylum-dev/phylum-ci/commit/c5fadb4eced4029afaf61d833212e63f7082ed2b))

### Documentation

* Add script options docs with auto updates ([#102](https://github.com/phylum-dev/phylum-ci/issues/102)) ([`6ba8e96`](https://github.com/phylum-dev/phylum-ci/commit/6ba8e96381184039afa1ef3bf67f9a5be275dd8a))

## v0.12.1 (2022-08-12)

### Fix

* `Issue Summary` data missing for vulnerability domain ([#99](https://github.com/phylum-dev/phylum-ci/issues/99)) ([`3a833cf`](https://github.com/phylum-dev/phylum-ci/commit/3a833cfa5954fb0133af8080717690680d81b7f9))

## v0.12.0 (2022-08-11)

### Feature

* Host `phylum-ci` Docker image on GitHub Container Registry ([#97](https://github.com/phylum-dev/phylum-ci/issues/97)) ([`ebc882e`](https://github.com/phylum-dev/phylum-ci/commit/ebc882ec202f351ca2522dc0cd1d34d32f63465c))

## v0.11.0 (2022-08-04)

### Feature

* Add git pre-commit hook integration ([#91](https://github.com/phylum-dev/phylum-ci/issues/91)) ([`99c5726`](https://github.com/phylum-dev/phylum-ci/commit/99c57265bec7f583dc76da01ac4bfcc7e655516a))

### Fix

* Incorrect vulnerability risk domain package key name ([#94](https://github.com/phylum-dev/phylum-ci/issues/94)) ([`247b4a4`](https://github.com/phylum-dev/phylum-ci/commit/247b4a4f75417ae663e21de183ba0d32c3bf4256))

### Documentation

* Update CONTRIBUTING.md to show how to add dependencies without constraints ([`d25dd1f`](https://github.com/phylum-dev/phylum-ci/commit/d25dd1ff786dc79dd083268877290c9171e465aa))
* Create exclusive directory for Integrations docs to sync properly ([#80](https://github.com/phylum-dev/phylum-ci/issues/80)) ([`d8b608b`](https://github.com/phylum-dev/phylum-ci/commit/d8b608b3c426e81619936a6273a3e82a21e08f0e))

## v0.10.0 (2022-07-14)

### Feature

* Check for and list valid versions and targets programmatically in `phylum-init` ([#74](https://github.com/phylum-dev/phylum-ci/issues/74)) ([`7066565`](https://github.com/phylum-dev/phylum-ci/commit/7066565956d159b17811a4a6418f06037537629e))

### Documentation

* Add integration documentation to Phylum docs page ([`5b988b9`](https://github.com/phylum-dev/phylum-ci/commit/5b988b9c408b2b1088f5fde3f53386b36540798c))

### Performance

* Allow native Docker image creation ([#77](https://github.com/phylum-dev/phylum-ci/issues/77)) ([`9ee4123`](https://github.com/phylum-dev/phylum-ci/commit/9ee4123c2510bf86fc72880adad12828cd95d1b1))

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
