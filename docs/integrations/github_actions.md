# GitHub Actions Integration

## Overview

Integrations with the GitHub Actions environment are available in several forms.
The primary method is through the `phylum-dev/phylum-analyze-pr-action` action.
This action is available in the [GitHub Actions Marketplace][marketplace].
Full documentation can be found there or by viewing the [Phylum Analyze PR action repository][repo] directly.

[marketplace]: https://github.com/marketplace/actions/phylum-analyze-pr
[repo]: https://github.com/phylum-dev/phylum-analyze-pr-action

## Alternatives

The Phylum Analyze PR action is a [Docker container action][container_action]. The default `phylum-ci` Docker
image it uses contains `git` and the installed `phylum` Python package. It also contains an installed version
of the Phylum CLI and all required tools needed for [lockfile generation][lockfile_generation].
An advantage of using the default Docker image is that the complete environment is packaged and made available
with components that are known to work together.

One disadvantage to the default image is it's size. It can take a while to download and may provide more
tools than required for your specific use case. Special `slim` tags of the `phylum-ci` image are provided as
an alternative. These tags differ from the default image in that they do not contain the required tools needed
for [lockfile generation][lockfile_generation] (with the exception of the `pip` tool). The `slim` tags are
significantly smaller and allow for faster action run times. They are useful for those instances where **no**
manifest files are present and/or **only** lockfiles are used.

Using the slim image tags is possible by altering your workflow to use the image directly instead of this
GitHub Action. That is possible with either [container jobs](#container-jobs) or [container steps](#container-steps).

[container_action]: https://docs.github.com/en/actions/creating-actions/creating-a-docker-container-action
[lockfile_generation]: ../cli/lockfile_generation.md

### Container Jobs

GitHub Actions allows for workflows to run a job within a container, using the `container:` statement in the
workflow file. These are known as container jobs. More information can be found in GitHub documentation:
["Running jobs in a container"][container_job]. To use a `slim` tag in a container job, use this minimal
configuration:

```yaml
name: Phylum_analyze
on: pull_request
jobs:
  analyze_deps:
    name: Analyze dependencies with Phylum
    permissions:
      contents: read
      pull-requests: write
    runs-on: ubuntu-latest
    container:
      image: docker://ghcr.io/phylum-dev/phylum-ci:slim
      env:
        GITHUB_TOKEN: ${{ github.token }}
        PHYLUM_API_KEY: ${{ secrets.PHYLUM_TOKEN }}
    steps:
      - name: Checkout the repo
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Analyze dependencies
        run: phylum-ci -vv
```

The `image:` value is set to the latest slim image, but other tags are available to ensure a specific release
of the `phylum-ci` project and a specific version of the Phylum CLI. The full list of available `phylum-ci`
image tags can be viewed on [GitHub Container Registry][ghcr_tags] (preferred) or [Docker Hub][docker_hub_tags].

The `GITHUB_TOKEN` and `PHYLUM_API_KEY` environment variables are required to have those exact names.
Those environment variables and the rest of the options are more fully documented in the
[Phylum Analyze PR action repository][repo].

[container_job]: https://docs.github.com/actions/using-jobs/running-jobs-in-a-container
[ghcr_tags]: https://github.com/phylum-dev/phylum-ci/pkgs/container/phylum-ci
[docker_hub_tags]: https://hub.docker.com/r/phylumio/phylum-ci/tags

### Container Steps

GitHub Actions allows for workflows to run a step within a container, by specifying that container image in
the `uses:` statement of the workflow step. These are known as container steps. More information can be found
in [GitHub workflow syntax documentation][container_step]. To use a `slim` tag in a container step, use this
minimal configuration:

```yaml
name: Phylum_analyze
on: pull_request
jobs:
  analyze_deps:
    name: Analyze dependencies with Phylum
    permissions:
      contents: read
      pull-requests: write
    runs-on: ubuntu-latest
    steps:
      - name: Checkout the repo
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Analyze dependencies
        uses: docker://ghcr.io/phylum-dev/phylum-ci:slim
        env:
          GITHUB_TOKEN: ${{ github.token }}
          PHYLUM_API_KEY: ${{ secrets.PHYLUM_TOKEN }}
        with:
          args: phylum-ci -vv
```

The `uses:` value is set to the latest slim image, but other tags are available to ensure a specific release
of the `phylum-ci` project and a specific version of the Phylum CLI. The full list of available `phylum-ci`
image tags can be viewed on [GitHub Container Registry][ghcr_tags] (preferred) or [Docker Hub][docker_hub_tags].

The `GITHUB_TOKEN` and `PHYLUM_API_KEY` environment variables are required to have those exact names.
Those environment variables and the rest of the options are more fully documented in the
[Phylum Analyze PR action repository][repo].

[container_step]: https://docs.github.com/actions/using-workflows/workflow-syntax-for-github-actions#jobsjob_idstepsuses

### Direct `phylum` Python Package Use

It is also possible to make direct use of the [`phylum` Python package][pypi] within CI.
This may be necessary if the Docker image is unavailable or undesirable for some reason.
To use the `phylum` package, install it and call the desired entry points from a script under your control.
See the [Installation][installation] and [Usage][usage] sections of the [README file][readme] for more detail.

[pypi]: https://pypi.org/project/phylum/
[readme]: https://github.com/phylum-dev/phylum-ci/blob/main/README.md
[installation]: https://github.com/phylum-dev/phylum-ci/blob/main/README.md#installation
[usage]: https://github.com/phylum-dev/phylum-ci/blob/main/README.md#usage
