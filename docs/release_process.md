# Release process

The `phylum-ci` project repository currently makes use of the standard GitFlow Workflow.
Here are some references to describe that in more detail:

* <https://datasift.github.io/gitflow/IntroducingGitFlow.html>
* <https://www.atlassian.com/git/tutorials/comparing-workflows/gitflow-workflow>

Specifically, for this repository, there are two long living branches:

* `develop`
  * This is the default branch
  * Feature branches are created from here
  * Roughly aligns with the "Staging" environment
  * This is a protected branch
* `main`
  * This is where releases are cut, from stable commits from the develop branch
  * This is a protected branch
  * Release tags should point to this branch
  * Roughly aligns with the "Production" environment

## Cutting a release

To cut a release, follow these steps:

1. Create a new PR for the `develop` branch with the following contents
   1. bump the version, while following the semantic release strategy
   2. Review and update the changelog
      1. Ensure the current entries are correct
      2. Add new entries where needed
      3. Add the release date
      4. Create a new `Unreleased` section
2. Once the PR is merged to the `develop` branch ensure the `Preview` workflow passes
   1. Use the artifacts from the `Preview` workflow to test/preview the release
   2. See the [Preview workflow section](#preview-workflow) for more detail
3. Create another PR for the `main` branch with the following contents
   1. Merge commits from the `develop` branch
4. Once the PR is approved and merged, create a release tag of that commit to `main`
   1. Use the same release version from the earlier step and ensure the commit is signed

      ```sh
      git tag --sign --message "Tag release v0.1.2" v0.1.2
      git push --tags
      ```

   2. This will trigger the `Release` workflow, which requires approval to continue
      1. See the [Release workflow section](#release-workflow) for more detail

If anything fails, please go read the respective action's log output and configuration
file to reverse engineer your way to a fix/soluton.

## Workflows

All automation workflows use GitHub Actions. All workflows are therefore configured using
`.yml` files in the `.github/workflows` directory of the `phylum-ci` repository. This section
contains descriptions of the release related workflows.

### Preview workflow

This workflow creates a developmental release version of the package, runs it against the test
suite, and makes the artifacts available for download from the workflow summary. The workflow is
triggered on pushes to the `develop` branch or manually from any branch. When using the manual
approach, an option is exposed to optionally publish the built package to the
[TestPyPI repository](https://test.pypi.org/). From there it can be tested locally in an ephemeral
environment. For example using `pipx` to run a specific developmental release version:

```sh
pipx run --index-url https://test.pypi.org/simple/ --spec "phylum-ci==0.0.2.dev6" phylum-ci -h
```

Currently this workflow uses the `Staging` environment, as configured in
[the repo settings](https://github.com/phylum-dev/phylum-ci/settings/environments).
This holds the TestPyPI API token as an environment secret.

### Release workflow

This workflow sets the release version and runs the test suite against the new version. It then
builds the release package artifacts, creates a GitHub release with those artifacts, and publishes
the artifacts to [PyPI](https://pypi.org/). The workflow is triggered by pushing a tag of the form
`v#.#.#`. The tag can also be for a pre-release, but then the tag name should adhere to the
[post-normalized PEP440 form](https://peps.python.org/pep-0440/). Here are some example valid tags:

* Release versions:
  * `v0.0.1`
  * `v1.2.3`
* Pre-release versions:
  * `v0.1.0a1` (alpha)
  * `v0.1.2b4` (beta)
  * `v1.0.0rc0` (release candidate)
  * `v0.1.5rc3` (release candidate)

Currently this workflow uses the `Production` environment, as configured in
[the repo settings](https://github.com/phylum-dev/phylum-ci/settings/environments).
This holds the PyPI API token as an environment secret. It also makes use of environment protections rules
such that there are designated reviewer groups that must approve the deployment.
