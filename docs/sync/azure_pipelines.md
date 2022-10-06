---
title: Azure Pipelines Integration
category: 62cdf6722c2c1602a4b69643
hidden: false
---
# Azure Pipelines Integration

## Overview

Once configured for a repository, the Azure Pipelines integration will provide analysis of project dependencies from
a lockfile during a Pull Request (MR) and output the results as a comment in a thread on the PR.
The CI job will return an error (i.e., fail the pipeline) if any of the newly added/modified dependencies from the
PR fail to meet the project risk thresholds for any of the five Phylum risk domains:

* Vulnerability (aka `vul`)
* Malicious Code (aka `mal`)
* Engineering (aka `eng`)
* License (aka `lic`)
* Author (aka `aut`)

See [Phylum Risk Domains documentation][risk_domains] for more detail.

**NOTE**: It is not enough to have the total project threshold set. Individual risk domain threshold values must be
set, either in the UI or with `phylum-ci` options, in order to enable analysis results for CI. Otherwise, the risk
domain is considered disabled and the threshold value used will be zero (0).

There will be no comment if no dependencies were added or modified for a given PR.
If one or more dependencies are still processing (no results available), then the comment will make that clear and
the CI pipeline job will only fail if dependencies that have _completed analysis results_ do not meet the specified
project risk thresholds.

## Prerequisites

The Azure Pipelines environment is primarily supported through the use of a Docker image.
The pre-requisites for using this image are:

* Access to the [phylumio/phylum-ci Docker image][docker_image]
* Azure DevOps Services is used with [Azure Repos Git][azure_repos_git] repository type
  * Azure DevOps Server versions are not guaranteed to work at this time
  * GitHub and Bitbucket Cloud hosted repositories are not supported at this time
* An [Azure token][azure_auth] with API access
  * Can be the default `System.AccessToken` provided automatically at the start of each pipeline build
    * The [scoped build identity][build_scope] using this token needs the `Contribute to pull requests` permission
    * See documentation for using the [token][access_token] and setting it's [job authorization scope][auth_scope]
  * Can be a personal access token (PAT) - see [documentation][PAT]
    * Needs at least the `Pull Request Threads` scope (read & write)
    * Consider using a service account for this token
* A [Phylum token][phylum_tokens] with API access
  * [Contact Phylum][phylum_contact] or [register][app_register] to gain access
    * See also [`phylum auth register`][phylum_register] command documentation
  * Consider using a bot or group account for this token
* Access to the Phylum API endpoints
  * That usually means a connection to the internet, optionally via a proxy
  * Support for on-premises installs are not available at this time
* A `.phylum_project` file exists at the root of the repository
  * See [`phylum project`][phylum_project] and [`phylum project create`][phylum_project_create] command documentation

[risk_domains]: https://docs.phylum.io/docs/phylum-package-score#risk-domains
[docker_image]: https://hub.docker.com/r/phylumio/phylum-ci/tags
[azure_repos_git]: https://learn.microsoft.com/azure/devops/pipelines/repos/azure-repos-git
[azure_auth]: https://learn.microsoft.com/azure/devops/integrate/get-started/authentication/authentication-guidance
[build_scope]: https://learn.microsoft.com/azure/devops/pipelines/process/access-tokens#scoped-build-identities
[access_token]: https://learn.microsoft.com/azure/devops/pipelines/build/variables#systemaccesstoken
[auth_scope]: https://learn.microsoft.com/azure/devops/pipelines/process/access-tokens#job-authorization-scope
[PAT]: https://learn.microsoft.com/azure/devops/organizations/accounts/use-personal-access-tokens-to-authenticate
[phylum_tokens]: https://docs.phylum.io/docs/api-keys
[phylum_contact]: https://phylum.io/contact-us/
[app_register]: https://app.phylum.io/register
[phylum_register]: https://docs.phylum.io/docs/phylum_auth_register
[phylum_project]: https://docs.phylum.io/docs/phylum_project
[phylum_project_create]: https://docs.phylum.io/docs/phylum_project_create

## Configure `azure-pipelines.yml`

Phylum analysis of dependencies can be added to existing pipelines or on it's own with this minimal configuration:

```yaml
trigger:
  - main

jobs:
  - job: Phylum
    pool:
      vmImage: ubuntu-latest
    container: phylumio/phylum-ci:latest
    steps:
      - checkout: self
        fetchDepth: 0
      - script: phylum-ci
        displayName: Analyze dependencies with Phylum
        env:
          PHYLUM_API_KEY: $(PHYLUM_TOKEN)
          AZURE_TOKEN: $(AZURE_PAT)
```

This single stage pipeline configuration contains a single container job named `Phylum`, triggered to run on pushes
or PRs targeting the `main` branch. It does not override any of the `phylum-ci` arguments, which are all either
optional or default to secure values.

Let's take a deeper dive into each part of the configuration:

### Pipeline control

Choose when to run the pipeline. See the [YAML schema trigger definition][yaml_trigger] documentation for more detail.

```yaml
# This is a CI trigger that will cause the
# pipeline to run on pushes to the `main` branch
trigger:
  - main
```

It is recommended to also enable PR validation for the target trigger branch(es). To do so, navigate to the branch
policies for the desired branch (`main` in this example), and configure the [Build validation policy][build_validation]
for that branch. For more information, see the documentation on [PR triggers for Azure Repos Git][pr_triggers] hosted
repositories or, more broadly, [events that trigger pipelines][triggers].

[yaml_trigger]: https://learn.microsoft.com/azure/devops/pipelines/yaml-schema/trigger
[build_validation]: https://learn.microsoft.com/azure/devops/repos/git/branch-policies#build-validation
[pr_triggers]: https://learn.microsoft.com/azure/devops/pipelines/repos/azure-repos-git#pr-triggers
[triggers]: https://learn.microsoft.com/azure/devops/pipelines/build/triggers

### Job names

The job name can be named differently or included in an existing stage/job.

```yaml
jobs:
  - job: Phylum  # Name this what you like
```

### Pool selection

The pool is specified at the job level here because this is a [container job][container_job]. While Azure Pipelines
allows container jobs for `windows-2019` and `ubuntu-*` base `vmImage` images, only `ubuntu-*` is supported by Phylum
at this time. Keeping that restriction in mind, the pool can be specified at the pipeline or stage level instead.
See the [YAML schema pool definition][yaml_pool] documentation for more detail.

[container_job]: https://learn.microsoft.com/azure/devops/pipelines/process/container-phases
[yaml_pool]: https://learn.microsoft.com/azure/devops/pipelines/yaml-schema/pool

```yaml
    pool:
      vmImage: ubuntu-latest
```

### Docker image selection

The container is specified at the job level here because this is a [container job][container_job] where all steps
in the job are meant to run with the same image. The container can also be specified as a
[resource at the pipeline level][resource_container] and then
[referenced by name in individual steps of a job][step_target] instead.
See the YAML schema [jobs.job.container definition][yaml_job_container] and [resource definition][yaml_resources]
documentation for more detail.

Choose the Docker image tag to match your comfort level with image dependencies. `latest` is a "rolling" tag that
will point to the image created for the latest released `phylum-ci` Python package. A particular version tag
(e.g., `0.15.0-CLIv3.10.0`) is created for each release of the `phylum-ci` Python package and _should_ not change
once published.

However, to be certain that the image does not change...or be warned when it does because it won't be available
anymore...use the SHA256 digest of the tag. The digest can be found by looking at the `phylumio/phylum-ci`
[tags on Docker Hub][docker_image] or with the command:

```sh
# The command-line JSON processor `jq` is used here for the sake of a one line example. It is not required.
❯ docker manifest inspect --verbose phylumio/phylum-ci:0.15.0-CLIv3.10.0 | jq .Descriptor.digest
"sha256:db450b4233484faf247fffbd28fc4f2b2d4d22cef12dfb1d8716be296690644e"
```

For instance, at the time of this writing, all of these tag references pointed to the same image:

```yaml
    # NOTE: These are examples. Only one container line for `phylum-ci` is expected.

    # Be explicit about wanting the `latest` tag
    container: phylumio/phylum-ci:latest

    # Use a specific release version of the `phylum-ci` package
    container: phylumio/phylum-ci:0.15.0-CLIv3.10.0

    # Use a specific image with it's SHA256 digest
    container: phylumio/phylum-ci@sha256:db450b4233484faf247fffbd28fc4f2b2d4d22cef12dfb1d8716be296690644e
```

Only the last tag reference, by SHA256 digest, is guaranteed to not have the underlying image it points to change.

[resource_container]: https://learn.microsoft.com/azure/devops/pipelines/yaml-schema/resources-containers-container
[step_target]: https://learn.microsoft.com/azure/devops/pipelines/process/tasks#step-target
[yaml_job_container]: https://learn.microsoft.com/azure/devops/pipelines/yaml-schema/jobs-job-container
[yaml_resources]: https://learn.microsoft.com/azure/devops/pipelines/yaml-schema/resources

### Repository checkout

The `phylum-ci` logic for determining changes in lockfiles requires git history beyond what is available in a shallow
clone/checkout/fetch. To ensure the shallow fetch option is disabled for the pipeline, an explicit checkout step is
specified here, with `fetchDepth` set to `0`. It is also possible to disable the shallow fetch option in the
[pipeline settings UI][pipeline_settings]. See the [YAML schema steps.checkout definition][yaml_checkout] documentation
for more detail.

[pipeline_settings]: https://learn.microsoft.com/azure/devops/pipelines/repos/azure-repos-git#shallow-fetch
[yaml_checkout]: https://learn.microsoft.com/azure/devops/pipelines/yaml-schema/steps-checkout

```yaml
      # Reference: https://learn.microsoft.com/azure/devops/pipelines/yaml-schema/steps-checkout
      - checkout: self
        fetchDepth: 0
```

### Script arguments

The arguments to the script step are the way to exert control over the execution of the Phylum analysis.
The entry here will run as a script in the `phylum-ci` based container job.
See the [YAML schema steps.script definition][yaml_script] and [container job][container_job] documentation for
more detail.

The `phylum-ci` script entry point is expected to be called. It has a number of arguments that are all optional
and defaulted to secure values. To view the arguments, their description, and default values,
run the script with `--help` output as specified in the [Usage section of the top-level README.md][usage] or
view the [script options output][script_options] for the latest release.

[yaml_script]: https://learn.microsoft.com/azure/devops/pipelines/yaml-schema/steps-script
[script_options]: https://github.com/phylum-dev/phylum-ci/blob/main/docs/script_options.md

```yaml
      # NOTE: These are examples. Only one script entry line for `phylum-ci` is expected.

      # Use the defaults for all the arguments.
      # The default behavior is to only analyze newly added dependencies against
      # the risk domain threshold levels set at the Phylum project level.
      - script: phylum-ci

      # Consider all dependencies in analysis results instead of just the newly added ones.
      # The default is to only analyze newly added dependencies, which can be useful for
      # existing code bases that may not meet established project risk thresholds yet,
      # but don't want to make things worse. Specifying `--all-deps` can be useful for
      # casting the widest net for strict adherence to Quality Assurance (QA) standards.
      - script: phylum-ci --all-deps

      # Some lockfile types (e.g., Python/pip `requirements.txt`) are ambiguous in that
      # they can be named differently and may or may not contain strict dependencies.
      # In these cases, it is best to specify an explicit lockfile path.
      - script: phylum-ci --lockfile requirements-prod.txt

      # Thresholds for the five risk domains may be set at the Phylum project level.
      # They can be set differently for CI environments to "fail the build."
      - script: |
        phylum-ci \
          --vul-threshold 60 \
          --mal-threshold 60 \
          --eng-threshold 70 \
          --lic-threshold 90 \
          --aut-threshold 80

      # Ensure the latest Phylum CLI is installed.
      - script: phylum-ci --force-install

      # Install a specific version of the Phylum CLI.
      - script: phylum-ci --phylum-release 3.10.0 --force-install

      # Mix and match for your specific use case.
      - script: |
        phylum-ci \
          --vul-threshold 60 \
          --mal-threshold 60 \
          --eng-threshold 70 \
          --lic-threshold 90 \
          --aut-threshold 80 \
          --lockfile requirements-prod.txt \
          --all-deps
```

### Script Variables

The script step environment variables are used to ensure the `phylum-ci` tool is able to perform it's job.

A [Phylum token][phylum_tokens] with API access is required to perform analysis on project dependencies.
[Contact Phylum][phylum_contact] or [register][app_register] to gain access.
See also [`phylum auth register`][phylum_register] command documentation and consider using a bot or group account
for this token.

An Azure DevOps token with API access is required to use the API (e.g., to post notes/comments).
This can be the default `System.AccessToken` provided automatically at the start of each pipeline build for the
[scoped build identity][build_scope] or a personal access token (PAT).

If using a PAT, it will need at least the `Pull Request Threads` scope (read & write).
The account used to create the PAT will be the one that appears to post the comments on the pull request.
Therefore, it might be worth using a bot or service account.
See the Azure DevOps [documentation for using PATs to authenticate][azure_pat] for more info.

If using the `System.AccessToken`, the [scoped build identity][build_scope] it attaches to needs at least the
`Contribute to pull requests` permission. For example, to use the `System.AccessToken` on a project-scoped
identity, follow these steps:

* Go to project settings
* Select the `Repos --> Repositories` menu
* Select the `Security` tab
* Select the user `{Project Name} Build Service ({Org Name})`
  * NOTE: This user will only exist after the first time the pipeline has run
* Ensure the `Contribute to pull requests` permission is set to `Allow`

See the Azure DevOps documentation for [using the `System.AccessToken`][access_token] and setting it's
[job authorization scope][auth_scope].

Values for the `PHYLUM_API_KEY` and `AZURE_TOKEN` environment variable (e.g., `PHYLUM_TOKEN` and `AZURE_PAT`
in the example here) can come from the pipeline UI, a variable group, or an Azure Key Vault. View the full
[documentation for how to set secret variables][secret_variables] for more information.
Since these tokens are sensitive, **care should be taken to protect them appropriately**.

[azure_pat]: https://learn.microsoft.com/azure/devops/organizations/accounts/use-personal-access-tokens-to-authenticate
[secret_variables]: https://learn.microsoft.com/azure/devops/pipelines/process/set-secret-variables

```yaml
        env:
          # Contact Phylum (phylum.io/contact-us) or register (app.phylum.io/register)
          # to gain access. See also `phylum auth register`
          # (https://docs.phylum.io/docs/phylum_auth_register) command documentation.
          # Consider using a bot or group account for this token.
          # This value (`PHYLUM_TOKEN`) will need to be set as a secret variable:
          # https://learn.microsoft.com/azure/devops/pipelines/process/set-secret-variables
          PHYLUM_API_KEY: $(PHYLUM_TOKEN)

          # NOTE: These are examples. Only one `AZURE_TOKEN` entry line is expected.
          #
          # Use the `System.AccessToken` provided automatically at the start of each pipeline build.
          # This value does not have to be set as a secret variable since it is provided by default.
          AZURE_TOKEN: $(System.AccessToken)
          #
          # Use a personal access token (PAT).
          # This value (`AZURE_PAT`) will need to be set as a secret variable:
          # https://learn.microsoft.com/azure/devops/pipelines/process/set-secret-variables
          AZURE_TOKEN: $(AZURE_PAT)
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