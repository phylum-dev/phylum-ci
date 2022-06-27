# GitHub Actions Integration

## Overview

Integrations with the GitHub Actions environment are available in several forms. The primary method is through the
`phylum-dev/phylum-analyze-pr-action` action. This action is available for direct use now and full documentation can be
found by viewing the [Phylum Analyze PR action repository](https://github.com/phylum-dev/phylum-analyze-pr-action).

The action will be available for discovery in the [GitHub Actions Marketplace](https://github.com/marketplace) soon.

The Phylum Analyze PR action is a [Docker container action][container]. This has the advantage of ensuring everything
needed to work with Phylum for analyzing a PR for dependencies in a lockfile is self contained and known to function as
a single unit. There are some disadvantages and some users may prefer a different solution.

[container]: https://docs.github.com/en/actions/creating-actions/creating-a-docker-container-action

## Alternatives

### Direct `phylum` Python Package Use

It is also possible to make direct use of the [`phylum` Python package](https://pypi.org/project/phylum/) within CI.
This may be necessary if the Docker image is unavailable or undesirable for some reason. To use the `phylum` package,
install it and call the desired entry points from a script under your control. See the
[Installation](../README.md#installation) and [Usage](../README.md#usage) sections of the [README file](../README.md)
for more detail.

### Container Jobs

There is another way to use the `phylumio/phylum-ci` Docker image, but without it being encapsulated in the Phylum
Analyze PR action directly. GitHub Actions allows for workflows to run a job within a container, using the `container:`
statement in the workflow file. These are known as container jobs. More information can be found in GitHub
documentation: ["Running jobs in a container"](https://docs.github.com/actions/using-jobs/running-jobs-in-a-container).
