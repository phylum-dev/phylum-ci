---
title: GitLab CI Integration
category: 62cdf6722c2c1602a4b69643
hidden: false
---
# GitLab CI Integration

## Overview

Once configured for a repository, the GitLab CI integration will provide analysis of project dependencies from
lockfiles. This can happen in a branch pipeline as a result of a commit or in a Merge Request (MR) pipeline.

For MR pipelines, analyzed dependencies will include any that are added/modified in the MR.

For branch pipelines, the analyzed dependencies will be determined by comparing lockfiles in the branch to the
default branch. **All** dependencies will be analyzed when the branch pipeline is run on the default branch.

The results will be provided in the pipeline logs and provided as a note (comment) on the MR. The CI job will
return an error (i.e., fail the build) if any of the analyzed dependencies fail to meet the established policy.

There will be no note if no dependencies were added or modified for a given MR.
If one or more dependencies are still processing (no results available), then the note will make that clear and
the CI job will only fail if dependencies that have _completed analysis results_ do not meet the active policy.

## Prerequisites

The GitLab CI environment is primarily supported through the use of a Docker image. GitLab [SaaS subscriptions][gl_saas]
hosted on <https://gitlab.com> are supported. [Self-managed subscriptions][self_managed] are supported for
"on-premises" installs which still have access to the internet. Self-hosted "offline" (e.g., air-gapped networks)
installs of GitLab may work but have not been confirmed.

The pre-requisites for using this image are:

* Access to the [phylumio/phylum-ci Docker image][docker_image]
* A [GitLab token][gitlab_tokens] with API access
  * This is only required when using the integration in merge request pipelines
  * The token needs the `api` scope
  * Tokens that specify a role will work with any role _other than_ `Guest`
* A [Phylum token][phylum_tokens] with API access
  * [Contact Phylum][phylum_contact] or [register][app_register] to gain access
    * See also [`phylum auth register`][phylum_register] command documentation
  * Consider using a bot or group account for this token
* Access to the Phylum API endpoints
  * That usually means a connection to the internet, optionally via a proxy

[gl_saas]: https://docs.gitlab.com/ee/subscriptions/gitlab_com/
[self_managed]: https://docs.gitlab.com/ee/subscriptions/self_managed/
[docker_image]: https://hub.docker.com/r/phylumio/phylum-ci/tags
[gitlab_tokens]: https://docs.gitlab.com/ee/security/token_overview.html
[phylum_tokens]: https://docs.phylum.io/docs/api-keys
[phylum_contact]: https://phylum.io/contact-us/
[app_register]: https://app.phylum.io/register
[phylum_register]: https://docs.phylum.io/docs/phylum_auth_register

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

Choose when to run the job. The Phylum integration can run in the context of branch pipelines or merge request
pipelines but [merge request pipelines][mr_pipelines] are given preferential treatment so care should be taken to
[avoid duplicate pipelines][duplicate_pipelines].

There are several ways to accomplish this goal. The first is to create a rule at the job level to specify that
the job should only run for merge request pipelines. Branch pipelines are the default type and will run when new
commits are pushed to a branch. If the desire is to only run the job for branch pipelines, then no rule limiting
the pipeline source should be specified.

```yaml
  # This optional rule specifies to run the job for merge request pipelines only.
  # Remove these lines entirely to run the job for branch pipelines instead.
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
```

It is also possible to allow for both pipeline types while ensuring only one runs at a time by using workflow
rules to automatically [switch between branch pipelines and merge request pipelines][switch]. To do so, remove
any _job_ level rules related to pipeline sources and add the following _workflow_ level rules to the configuration:

```yaml
workflow:
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH && $CI_OPEN_MERGE_REQUESTS
      when: never
    - if: $CI_COMMIT_BRANCH
```

See the [GitLab CI/CD Job Control][job_control] documentation for more detail.

[mr_pipelines]: https://docs.gitlab.com/ee/ci/pipelines/merge_request_pipelines.html
[duplicate_pipelines]: https://docs.gitlab.com/ee/ci/jobs/job_control.html#avoid-duplicate-pipelines
[switch]: https://docs.gitlab.com/ee/ci/yaml/workflow.html#switch-between-branch-pipelines-and-merge-request-pipelines
[job_control]: https://docs.gitlab.com/ee/ci/jobs/job_control.html

### Docker image selection

Choose the Docker image tag to match your comfort level with image dependencies. `latest` is a "rolling" tag that
will point to the image created for the latest released `phylum-ci` Python package. A particular version tag
(e.g., `0.23.1-CLIv4.4.0`) is created for each release of the `phylum-ci` Python package and _should_ not change
once published.

However, to be certain that the image does not change...or be warned when it does because it won't be available
anymore...use the SHA256 digest of the tag. The digest can be found by looking at the `phylumio/phylum-ci`
[tags on Docker Hub][docker_image] or with the command:

```sh
# NOTE: The command-line JSON processor `jq` is used here for the sake of a one line example. It is not required.
❯ docker manifest inspect --verbose phylumio/phylum-ci:0.23.1-CLIv4.4.0 | jq .Descriptor.digest
"sha256:f2840ad448278e26b69a076a93f2c90cb083803243a614f5efb518f032626578"
```

For instance, at the time of this writing, all of these tag references pointed to the same image:

```yaml
  # NOTE: These are examples. Only one image line for `phylum-ci` is expected.

  # Not specifying a tag means a default of `latest`
  image: phylumio/phylum-ci

  # Be more explicit about wanting the `latest` tag
  image: phylumio/phylum-ci:latest

  # Use a specific release version of the `phylum-ci` package
  image: phylumio/phylum-ci:0.23.1-CLIv4.4.0

  # Use a specific image with it's SHA256 digest
  image: phylumio/phylum-ci@sha256:f2840ad448278e26b69a076a93f2c90cb083803243a614f5efb518f032626578
```

Only the last tag reference, by SHA256 digest, is guaranteed to not have the underlying image it points to change.

### Variables

The job variables are used to ensure the `phylum-ci` tool is able to perform it's job.

For instance, `git` is used within the `phylum-ci` package to do things like determine if there was a lockfile change
and, when specified, report on new dependencies only. Therefore, a clone of the repository is required to ensure that
the local working copy is always pristine and history is available to pull the requested information.
It _may_ also be necessary to specify the depth of cloning if/when there is not enough info.

A GitLab token with API access is required to use the API (e.g., to post notes/comments). This can be a personal,
project, or group access token. The account used to create the token will be the one that appears to post the
notes/comments on the MR. Therefore, it might be worth looking into using a bot account, which is available for
project and group access tokens. See the [GitLab Token Overview][gitlab_tokens] documentation for more info.
The token needs the `api` scope. Project or Group access tokens should specify a role _other than_ `Guest`.

Note, the GitLab token is only required when this Phylum integration is used in [merge request pipelines][mr_pipelines].
It is not required when used in branch pipelines.

Note, using `$CI_JOB_TOKEN` as the value will work in some situations because "API authentication uses the job token,
by using the authorization of the user triggering the job." This is not recommended for anything other than temporary
personal use in private repositories as there is a chance that depending on it will cause failures when attempting to
do the same thing in different scenarios.

A [Phylum token][phylum_tokens] with API access is required to perform analysis on project dependencies.
[Contact Phylum][phylum_contact] or [register][app_register] to gain access.
See also [`phylum auth register`][phylum_register] command documentation and consider using a bot or group account
for this token.

Values for the `GITLAB_TOKEN` and `PHYLUM_API_KEY` variables can come from a [CI/CD Variable][ci_cd_variable] or an
[External Secret][external_secret]. Since they are sensitive, **care should be taken to protect them appropriately**.

[ci_cd_variable]: https://docs.gitlab.com/ee/ci/variables/index.html
[external_secret]: https://docs.gitlab.com/ee/ci/secrets/index.html

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

    # Contact Phylum (phylum.io/contact-us) or register (app.phylum.io/register) to gain
    # access. See also `phylum auth register` (docs.phylum.io/docs/phylum_auth_register)
    # command documentation. Consider using a bot or group account for this token.
    PHYLUM_API_KEY: $PHYLUM_TOKEN_VARIABLE_OR_SECRET_HERE
```

### Script arguments

The script arguments to the Docker image are the way to exert control over the execution of the Phylum analysis.
The `phylum-ci` script entry point is expected to be called. It has a number of arguments that are all optional
and defaulted to secure values. To view the arguments, their description, and default values,
run the script with `--help` output as specified in the [Usage section of the top-level README.md][usage] or
view the [script options output][script_options] for the latest release.

[script_options]: https://github.com/phylum-dev/phylum-ci/blob/main/docs/script_options.md

```yaml
  # NOTE: These are examples. Only one script entry line for `phylum-ci` is expected.
  script:
    # Use the defaults for all the arguments.
    # The default behavior is to only analyze newly added dependencies
    # against the active policy set at the Phylum project level.
    - phylum-ci

    # Provide debug level output
    - phylum-ci -vv

    # Consider all dependencies in analysis results instead of just the newly added ones.
    # The default is to only analyze newly added dependencies, which can be useful for
    # existing code bases that may not meet established policy rules yet,
    # but don't want to make things worse. Specifying `--all-deps` can be useful for
    # casting the widest net for strict adherence to Quality Assurance (QA) standards.
    - phylum-ci --all-deps

    # Some lockfile types (e.g., Python/pip `requirements.txt`) are ambiguous in that
    # they can be named differently and may or may not contain strict dependencies.
    # In these cases, it is best to specify an explicit lockfile path.
    - phylum-ci --lockfile requirements-prod.txt

    # Specify multiple explicit lockfile paths
    - phylum-ci --lockfile requirements-prod.txt path/to/lock.file

    # Ensure the latest Phylum CLI is installed.
    - phylum-ci --force-install

    # Install a specific version of the Phylum CLI.
    - phylum-ci --phylum-release 4.8.0 --force-install

    # Mix and match for your specific use case.
    # Long commands: https://docs.gitlab.com/ee/ci/yaml/script.html#split-long-commands
    - |
      phylum-ci \
        -vv \
        --lockfile requirements-dev.txt \
        --lockfile requirements-prod.txt path/to/lock.file \
        --all-deps
```

## Alternatives

It is also possible to make direct use of the [`phylum` Python package][pypi] within CI.
This may be necessary if the Docker image is unavailable or undesirable for some reason.
To use the `phylum` package, install it and call the desired entry points from a script under your control.
See the [Installation][installation] and [Usage][usage] sections of the [README file][readme] for more detail.

[pypi]: https://pypi.org/project/phylum/
[readme]: https://github.com/phylum-dev/phylum-ci/blob/main/README.md
[installation]: https://github.com/phylum-dev/phylum-ci/blob/main/README.md#installation
[usage]: https://github.com/phylum-dev/phylum-ci/blob/main/README.md#usage
