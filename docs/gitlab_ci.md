# GitLab CI Integration

## Overview

Once configured for a repository, the GitLab CI integration will provide analysis of project dependencies from a
lockfile during a Merge Request (MR) and output the results as a note (comment) on the MR.
The CI job will return an error (i.e., fail the build) if any dependencies fail to meet the specified project risk
thresholds for any of the five Phylum risk domains:

* Vulnerability (aka `vul`)
* Malicious Code (aka `mal`)
* Engineering (aka `eng`)
* License (aka `lic`)
* Author (aka `aut`)

See [Phylum Risk Domains documentation](https://docs.phylum.io/docs/phylum-package-score#risk-domains) for more detail.

There will be no note if no dependencies were added or modified for a given MR.
If one or more dependencies are still processing (no results available), then the note will make that clear and the CI
job will only fail if dependencies that have _completed analysis results_ do not meet the specified project risk
thresholds.

## Prerequisites

The GitLab CI environment is primarily supported through the use of a Docker image.
The pre-requisites for using this image are:

* Access to the [phylumio/phylum-ci Docker image](https://hub.docker.com/r/phylumio/phylum-ci/tags)
* A [GitLab token](https://docs.gitlab.com/ee/security/token_overview.html) with API access
* A [Phylum token](https://docs.phylum.io/docs/api-keys) with API access
  * [Contact Phylum](https://phylum.io/contact-us/) or create an account and register to gain access
    * See also [`phylum auth register`](https://docs.phylum.io/docs/phylum_auth_register) command documentation
  * Consider using a bot or group account for this token
* Access to the Phylum API endpoints
  * That usually means a connection to the internet, optionally via a proxy
  * Support for on-premises installs are not available at this time
* A `.phylum_project` file exists at the root of the repository
  * See [`phylum project`](https://docs.phylum.io/docs/phylum_project) and
    [`phylum project create`](https://docs.phylum.io/docs/phylum_project_create) command documentation

## Configure `.gitlab-ci.yml`

Phylum analysis of dependencies can be added to existing CI workflows or on it's own with this minimal configuration:

```yaml
stages:
  - QA

analyze_MR_with_Phylum:
  stage: QA
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  image: phylumio/phylum-ci:latest
  variables:
    GIT_STRATEGY: clone
    GITLAB_TOKEN: $GITLAB_TOKEN_VARIABLE_OR_SECRET_HERE
    PHYLUM_API_KEY: $PHYLUM_TOKEN_VARIABLE_OR_SECRET_HERE
  script:
    - phylum-ci
```

This configuration contains a single Quality Assurance stage named QA and will only run in merge request pipelines.
It does not override any of the `phylum-ci` arguments, which are all either optional or default to secure values.
Let's take a deeper dive into each part of the configuration:

### Stage and Job names

The stage and job names can be named differently or included in existing stages/jobs.

```yaml
stages:
  - QA  # Name this what you like

analyze_MR_with_Phylum:  # Name this what you like
  stage: QA  # Change the stage where the job will run here
```

### Job control

Choose when to run the job. See the [GitLab CI/CD Job Control](https://docs.gitlab.com/ee/ci/jobs/job_control.html)
documentation for more detail.

```yaml
  rules:
    # This rule specifies to run the job for merge request pipelines
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
```

### Docker image selection

Choose the Docker image tag to match your comfort level with image dependencies. `latest` is a "rolling" tag that will
point to the image created for the latest released `phylum-ci` Python package. A particular version tag (e.g., `0.4.0`)
is created for each release of the `phylum-ci` Python package and _should_ not change once published.

However, to be certain that the image does not change...or be warned when it does because it won't be available anymore
...use the SHA256 digest of the tag. The digest can be found by looking at the `phylumio/phylum-ci`
[tags on Docker Hub](https://hub.docker.com/r/phylumio/phylum-ci/tags) or with the command:

```sh
# NOTE: The command-line JSON processor `jq` is used here for the sake of a one line example. It is not required.
❯ docker manifest inspect --verbose phylumio/phylum-ci:0.4.0 | jq .Descriptor.digest
"sha256:8d29ac57dfe4d0fca5c3b8c8b37b1188d13faa5e5c61e53aace7026804eac2c5"
```

For instance, at the time of this writing, all of these tag references pointed to the same image:

```yaml
  # not specifying a tag means a default of `latest`
  image: phylumio/phylum-ci

  # be more explicit about wanting the `latest` tag
  image: phylumio/phylum-ci:latest

  # use a specific release version of the `phylum-ci` package
  image: phylumio/phylum-ci:0.4.0

  # use a specific image with it's SHA256 digest
  image: phylumio/phylum-ci@sha256:8d29ac57dfe4d0fca5c3b8c8b37b1188d13faa5e5c61e53aace7026804eac2c5
```

Only the last tag reference, by SHA256 digest, is guaranteed to not have the underlying image it points to change.

### Variables

The job variables are used to ensure the `phylum-ci` tool is able to perform it's job.

For instance, `git` is used within the `phylum-ci` package to do things like determine if there was a lockfile change
and, when specified, report on new dependencies only. Therefore, a clone of the repository is required to ensure that
the local working copy is always pristine and history is available to pull the requested information.
It _may_ also be necessary to specify the depth of cloning if/when there is not enough info.

A GitLab token with API access is required to use the API (e.g., to post notes/comments).
This can be a personal, project, or group access token.
See the [GitLab Token Overview](https://docs.gitlab.com/ee/security/token_overview.html) documentation for more info.

Note, using `$CI_JOB_TOKEN` as the value will work in some situations because "API authentication uses the job token, by
using the authorization of the user triggering the job." This is not recommended for anything other than temporary
personal use in private repositories as there is a chance that depending on it will cause failures when attempting to do
the same thing in different scenarios.

A [Phylum token](https://docs.phylum.io/docs/api-keys) with API access is required to perform analysis on project
dependencies. [Contact Phylum](https://phylum.io/contact-us/) or create an account and register to gain access.
See also [`phylum auth register`](https://docs.phylum.io/docs/phylum_auth_register) command documentation and consider
using a bot or group account for this token.

The values for the `GITLAB_TOKEN` and `PHYLUM_API_KEY` variables can come from a
[CI/CD Variable](https://docs.gitlab.com/ee/ci/variables/index.html) or an
[External Secret](https://docs.gitlab.com/ee/ci/secrets/index.html). Since they are sensitive, **care should be taken
to protect them appropriately**.

```yaml
  variables:
    # References:
    # GIT_STRATEGY - https://docs.gitlab.com/ee/ci/runners/configure_runners.html#git-strategy
    # GIT_DEPTH - https://docs.gitlab.com/ee/ci/runners/configure_runners.html#shallow-cloning
    GIT_STRATEGY: clone
    # GIT_DEPTH: "50"

    # References for GitLab tokens:
    # All tokens - https://docs.gitlab.com/ee/security/token_overview.html
    # Personal - https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html
    # Project - https://docs.gitlab.com/ee/user/project/settings/project_access_tokens.html
    # Group - https://docs.gitlab.com/ee/user/group/settings/group_access_tokens.html
    GITLAB_TOKEN: $GITLAB_TOKEN_VARIABLE_OR_SECRET_HERE

    # Contact Phylum (https://phylum.io/contact-us/) or create an account and register to gain access.
    # See also `phylum auth register` (https://docs.phylum.io/docs/phylum_auth_register) command documentation.
    # Consider using a bot or group account for this token.
    PHYLUM_API_KEY: $PHYLUM_TOKEN_VARIABLE_OR_SECRET_HERE
```

### Script arguments

The script arguments to the Docker image are the way to exert control over the execution of the Phylum analysis. The
`phylum-ci` script entry point is expected to be called. It has a number of arguments that are all optional and
defaulted to secure values. To view the arguments, their description, and default values, run the script with `--help`
output as specified in the [Usage section of the top-level README.md](../README.md#usage) or view the
[source code](https://github.com/phylum-dev/phylum-ci/blob/main/src/phylum/ci/cli.py) directly.

```yaml
  # NOTE: These are examples. Only one script entry line for `phylum-ci` is expected.
  script:
    # Use the defaults for all the arguments.
    - phylum-ci

    # Only analyze newly added dependencies. This can be useful for existing code bases that
    # may not meet established project risk thresholds yet, but don't want to make things worse.
    - phylum-ci --new-deps-only

    # Some lockfile types (e.g., Python/pip `requirements.txt`) are ambiguous in that
    # they can be named differently and may or may not contain strict dependencies.
    # In these cases, it is best to specify an explicit lockfile path.
    - phylum-ci --lockfile requirements-prod.txt

    # Thresholds for the five risk domains may be set at the Phylum project level.
    # They can be set differently for CI environments to "fail the build."
    # NOTE: The shortened form is used here for brevity, but the long form might be more
    #       descriptive for future readers. For instance `--vul-threshold` instead of `-vt`.
    - phylum-ci -vt 60 -mt 60 -et 70 -lt 90 -at 80

    # Ensure the latest Phylum CLI is installed.
    - phylum-ci --force-install

    # Install a specific version of the Phylum CLI.
    - phylum-ci --phylum-release 3.3.0 --force-install

    # Mix and match for your specific use case.
    - phylum-ci -vt 60 -mt 60 -et 70 -lt 90 -at 80 --lockfile requirements-prod.txt --new-deps-only
```

## Alternatives

It is also possible to make direct use of the [`phylum` Python package](https://pypi.org/project/phylum/) within CI.
This may be necessary if the Docker image is unavailable or undesirable for some reason. To use the `phylum` package,
install it and call the desired entry points from a script under your control. See the
[Installation](../README.md#installation) and [Usage](../README.md#usage) sections of the [README file](../README.md)
for more detail.
