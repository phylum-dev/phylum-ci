# Release process

The `phylum-ci` project repository currently makes use of
[GitHub flow](https://docs.github.com/en/get-started/quickstart/github-flow), which is also known as
[trunk-based development](https://www.atlassian.com/continuous-delivery/continuous-integration/trunk-based-development).

Specifically, for this repository, there is a single long-living branch:

* `main`
  * This is the default branch
  * Feature branches are created from here
  * This is where releases are cut
  * This is a protected branch
  * Release tags should point to this branch
  * Roughly aligns with the "Production" environment

## Cutting a release

To cut a release, follow these steps:

1. Go to the [`Release` Workflow](https://github.com/phylum-dev/phylum-ci/actions/workflows/release.yml) for the repo
2. Select the `Run workflow` dropdown
   1. The workflow can only be run on the `main` branch
   2. Optionally, select the `prerelease` checkbox to create a pre-release
3. Click the `Run workflow` button to trigger a release

## Workflows

All automation workflows use GitHub Actions. All workflows are therefore configured using
`.yml` files in the `.github/workflows` directory of the `phylum-ci` repository. This section
contains descriptions of the release related workflows.

### Preview workflow

This workflow creates a developmental release version of the package, runs it against the test
suite, and makes the artifacts available for download from the workflow summary. The workflow is
triggered on pushes to the `main` branch or manually from any branch. When using the manual
approach, an option is exposed to optionally publish the built package to the
[TestPyPI repository](https://test.pypi.org/). From there it can be tested locally in an ephemeral
environment. For example using `pipx` to run a specific developmental release version:

```sh
pipx run -i https://test.pypi.org/simple/ --spec "phylum==0.24.2.dev183" --pip-args="--extra-index-url=https://pypi.org/simple/" phylum-init -h
```

### Release workflow

This is a workflow for releasing packages in GitHub and publishing to PyPI.
This workflow is only triggered manually, from the Actions tab. It is limited to those with `write` access
to the repo (e.g., collaborators and orgs, people, teams given write access) and only for the `main` branch.

The release process leans heavily on the Python Semantic Release (PSR) package, which in turn is dependent on
conventional commits to determine release versions. Poetry is used to build the release distributions in order to
use them for "verification" purposes *before* creating a GitHub release and publishing to PyPI. PSR will bump the
release version, tag the release, update the change log, run `rich-codex` to update the script options documentation,
and commit the changes back to the repository. PSR will also generate the GitHub release and populate it with the
artifacts as built by `poetry`. Finally, PSR will upload the release to [PyPI](https://pypi.org).

Currently this workflow uses the `Production` environment, as configured in
[the repo settings](https://github.com/phylum-dev/phylum-ci/settings/environments).
This holds the PyPI API token as an environment secret. It also makes use of environment protections rules
such that there are designated reviewer groups that must approve the deployment.
