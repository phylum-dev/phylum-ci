---
title: GitHub Actions Integration
category: 62cdf6722c2c1602a4b69643
hidden: false
---
# GitHub Actions Integration

## Overview

Integrations with the GitHub Actions environment are available in several forms.
The primary method is through the `phylum-dev/phylum-analyze-pr-action` action.
This action is available in the [GitHub Actions Marketplace][marketplace].
Full documentation can be found there or by viewing the [Phylum Analyze PR action repository][repo] directly.

The Phylum Analyze PR action is a [Docker container action][container_action].
This has the advantage of ensuring everything needed to work with Phylum for analyzing a PR
for dependencies in lockfiles is self contained and known to function as a single unit.
There are some disadvantages and some users may prefer a different solution.

[marketplace]: https://github.com/marketplace/actions/phylum-analyze-pr
[repo]: https://github.com/phylum-dev/phylum-analyze-pr-action
[container_action]: https://docs.github.com/en/actions/creating-actions/creating-a-docker-container-action

## Alternatives

### Direct `phylum` Python Package Use

It is also possible to make direct use of the [`phylum` Python package][pypi] within CI.
This may be necessary if the Docker image is unavailable or undesirable for some reason.
To use the `phylum` package, install it and call the desired entry points from a script under your control.
See the [Installation][installation] and [Usage][usage] sections of the [README file][readme] for more detail.

[pypi]: https://pypi.org/project/phylum/
[readme]: https://github.com/phylum-dev/phylum-ci/blob/main/README.md
[installation]: https://github.com/phylum-dev/phylum-ci/blob/main/README.md#installation
[usage]: https://github.com/phylum-dev/phylum-ci/blob/main/README.md#usage

### Container Jobs

There is another way to use the `phylumio/phylum-ci` Docker image,
but without it being encapsulated in the Phylum Analyze PR action directly.
GitHub Actions allows for workflows to run a job within a container,
using the `container:` statement in the workflow file.
These are known as container jobs.
More information can be found in GitHub documentation: ["Running jobs in a container"][container_job].

[container_job]: https://docs.github.com/actions/using-jobs/running-jobs-in-a-container
