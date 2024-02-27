# Azure Pipelines Integration

## Overview

Azure Pipelines [supports several different source repositories][supported_repos]. This integration works with repos
hosted on [Azure Repos Git][azure_repos_git] and [GitHub][github_repos].

Once configured for a repository, the Azure Pipelines integration will provide analysis of project dependencies from
manifests and lockfiles. This can happen in a branch pipeline run from a CI trigger or in a Pull Request (PR)
pipeline run from a PR trigger.

For PR triggered pipelines, analyzed dependencies will include any that are added/modified in the PR.

For CI triggered pipelines, the analyzed dependencies will be determined by comparing dependency files in the branch
to the default branch. **All** dependencies will be analyzed when the CI triggered pipeline is run on the default
branch.

The results will be provided in the pipeline logs and provided as a comment in a thread on the PR. The CI job will
return an error (i.e., fail the build) if any of the analyzed dependencies fail to meet the established policy.

There will be no comment if no dependencies were added or modified for a given PR.
If one or more dependencies are still processing (no results available), then the comment will make that clear and
the CI pipeline job will only fail if dependencies that have _completed analysis results_ do not meet the active policy.

[supported_repos]: https://learn.microsoft.com/azure/devops/pipelines/repos
[azure_repos_git]: https://learn.microsoft.com/azure/devops/pipelines/repos/azure-repos-git
[github_repos]: https://learn.microsoft.com/azure/devops/pipelines/repos/github

## Prerequisites

The Azure Pipelines environment is primarily supported through the use of a Docker image.
The pre-requisites for using this image are:

* Access to the [phylumio/phylum-ci Docker image][docker_image]
* Azure DevOps Services is used with an [Azure Repos Git][azure_repos_git] or [GitHub][github_repos] repository type
  * Azure DevOps Server versions are not guaranteed to work at this time
  * Bitbucket Cloud hosted repositories are not supported at this time
* An [Azure token][azure_auth] with API access
  * This is only required when the build repository is [Azure Repos Git][azure_repos_git] and PR triggers are enabled
  * Can be the default `System.AccessToken` provided automatically at the start of each pipeline build
    * The [scoped build identity][build_scope] using this token needs the `Contribute to pull requests` permission
    * See documentation for using the [token][access_token] and setting it's [job authorization scope][auth_scope]
  * Can be a personal access token (PAT) - see [documentation][AZP_PAT]
    * Needs at least the `Pull Request Threads` scope (read & write)
    * Consider using a service account for this token
* A [GitHub PAT][GH_PAT] with API access
  * This is only required when the build repository is [GitHub][github_repos] and PR triggers are enabled
  * Can be a fine-grained PAT
    * Needs repository access and permissions: read access to `metadata` and read/write access to `pull requests`
    * See [permissions required for fine-grained PATs][fine_pats]
  * Can be a classic PAT
    * Needs the `repo` scope or minimally the `public_repo` scope if private repositories are not used
    * See [documentation][scopes]
* A [Phylum token][phylum_tokens] with API access
  * [Contact Phylum][phylum_contact] or [register][app_register] to gain access
    * See also [`phylum auth register`][phylum_register] command documentation
  * Consider using a bot or group account for this token
* Access to the Phylum API endpoints
  * That usually means a connection to the internet, optionally via a proxy
  * Support for on-premises installs are not available at this time

[docker_image]: https://hub.docker.com/r/phylumio/phylum-ci/tags
[azure_auth]: https://learn.microsoft.com/azure/devops/integrate/get-started/authentication/authentication-guidance
[build_scope]: https://learn.microsoft.com/azure/devops/pipelines/process/access-tokens#scoped-build-identities
[access_token]: https://learn.microsoft.com/azure/devops/pipelines/build/variables#systemaccesstoken
[auth_scope]: https://learn.microsoft.com/azure/devops/pipelines/process/access-tokens#job-authorization-scope
[AZP_PAT]: https://learn.microsoft.com/azure/devops/organizations/accounts/use-personal-access-tokens-to-authenticate
[GH_PAT]: https://docs.github.com/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token
[fine_pats]: https://docs.github.com/rest/overview/permissions-required-for-fine-grained-personal-access-tokens
[scopes]: https://docs.github.com/developers/apps/building-oauth-apps/scopes-for-oauth-apps#available-scopes
[phylum_tokens]: ../knowledge_base/api-keys.md
[phylum_contact]: https://phylum.io/contact-us/
[app_register]: https://app.phylum.io/register
[phylum_register]: ../cli/commands/phylum_auth_register.md

## Configure `azure-pipelines.yml`

Phylum analysis of dependencies can be added to existing pipelines or on it's own with this minimal configuration:

```yaml
trigger:
  - main
pr:
  - main

jobs:
  - job: Phylum
    pool:
      vmImage: ubuntu-latest
    container: phylumio/phylum-ci:latest
    steps:
      - checkout: self
        fetchDepth: 0
        persistCredentials: true
      - script: phylum-ci
        displayName: Analyze dependencies with Phylum
        env:
          PHYLUM_API_KEY: $(PHYLUM_TOKEN)
          AZURE_TOKEN: $(AZURE_PAT)     # For Azure repos only
          GITHUB_TOKEN: $(GITHUB_PAT)   # For GitHub repos only
```

This single stage pipeline configuration contains a single container job named `Phylum`, triggered to run on pushes
or PRs targeting the `main` branch. It does not override any of the `phylum-ci` arguments, which are all either
optional or default to secure values.

Let's take a deeper dive into each part of the configuration:

### Pipeline control

Choose when to run the pipeline. See the YAML schema [trigger definition][yaml_trigger] and [pr definition][yaml_pr]
documentation for more detail.

```yaml
# This is a CI trigger that will cause the
# pipeline to run on pushes to the `main` branch
trigger:
  - main
```

It is recommended to also enable PR validation for the target trigger branch(es). To do so for GitHub repos, use
the `pr` keyword. See the YAML schema [pr definition][yaml_pr] documentation for more detail.

```yaml
# This is a PR trigger that will cause the pipeline to run when
# a pull request is opened with `main` as the target branch.
# NOTE: This has no affect for Azure Repos Git based repositories
pr:
  - main
```

To enable PR validation for Azure Repos Git, navigate to the branch policies for the desired branch
(`main` in this example), and configure the [Build validation policy][build_validation] for that branch.
For more information, see the documentation on [PR triggers for Azure Repos Git][az_pr_triggers] hosted repositories,
[PR triggers for GitHub][gh_pr_triggers], or more broadly [events that trigger pipelines][triggers].

[yaml_trigger]: https://learn.microsoft.com/azure/devops/pipelines/yaml-schema/trigger
[yaml_pr]: https://learn.microsoft.com/azure/devops/pipelines/yaml-schema/pr
[build_validation]: https://learn.microsoft.com/azure/devops/repos/git/branch-policies#build-validation
[az_pr_triggers]: https://learn.microsoft.com/azure/devops/pipelines/repos/azure-repos-git#pr-triggers
[gh_pr_triggers]: https://learn.microsoft.com/azure/devops/pipelines/repos/github#pr-triggers
[triggers]: https://learn.microsoft.com/azure/devops/pipelines/build/triggers

### Job names

The job name can be named differently or included in an existing stage/job.

```yaml
jobs:
  - job: Phylum  # Name this what you like
```

### Pool selection

The pool is specified at the job level here because this is a [container job][container_job]. While Azure Pipelines
allows container jobs for `windows-2019` and `ubuntu-*` base `vmImage` images, only `ubuntu-*` is supported by
Phylum at this time. Keeping that restriction in mind, the pool can be specified at the pipeline or stage level
instead. See the [YAML schema pool definition][yaml_pool] documentation for more detail.

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
(e.g., `0.21.0-CLIv4.0.1`) is created for each release of the `phylum-ci` Python package and _should_ not change
once published.

However, to be certain that the image does not change...or be warned when it does because it won't be available
anymore...use the SHA256 digest of the tag. The digest can be found by looking at the `phylumio/phylum-ci`
[tags on Docker Hub][docker_image] or with the command:

```sh
# The command-line JSON processor `jq` is used here for the sake of a one line example. It is not required.
❯ docker manifest inspect --verbose phylumio/phylum-ci:0.21.0-CLIv4.0.1 | jq .Descriptor.digest
"sha256:7ddeb98897cd7af9dacae2e1474e8574dcf74b2e2e41e47327519d12242601cc"
```

For instance, at the time of this writing, all of these tag references pointed to the same image:

```yaml
    # NOTE: These are examples. Only one container line for `phylum-ci` is expected.

    # Be explicit about wanting the `latest` tag
    container: phylumio/phylum-ci:latest

    # Use a specific release version of the `phylum-ci` package
    container: phylumio/phylum-ci:0.21.0-CLIv4.0.1

    # Use a specific image with it's SHA256 digest
    container: phylumio/phylum-ci@sha256:7ddeb98897cd7af9dacae2e1474e8574dcf74b2e2e41e47327519d12242601cc
```

Only the last tag reference, by SHA256 digest, is guaranteed to not have the underlying image it points to change.

The default `phylum-ci` Docker image contains `git` and the installed `phylum` Python package. It also contains an
installed version of the Phylum CLI and all required tools needed for [lockfile generation][lockfile_generation].
An advantage of using the default Docker image is that the complete environment is packaged and made available
with components that are known to work together.

One disadvantage to the default image is it's size. It can take a while to download and may provide more
tools than required for your specific use case. Special `slim` tags of the `phylum-ci` image are provided as
an alternative. These tags differ from the default image in that they do not contain the required tools needed
for [lockfile generation][lockfile_generation] (with the exception of the `pip` tool). The `slim` tags are
significantly smaller and allow for faster action run times. They are useful for those instances where **no**
manifest files are present and/or **only** lockfiles are used.

Here are examples of using the slim image tags:

```yaml
    # NOTE: These are examples. Only one container line for `phylum-ci` is expected.

    # Use the most current release of *both* `phylum-ci` and the Phylum CLI
    container: phylumio/phylum-ci:slim

    # Use the `slim` image with a specific release version of `phylum-ci` and Phylum CLI
    container: phylumio/phylum-ci:0.36.0-CLIv5.7.1-slim
```

[resource_container]: https://learn.microsoft.com/azure/devops/pipelines/yaml-schema/resources-containers-container
[step_target]: https://learn.microsoft.com/azure/devops/pipelines/process/tasks#step-target
[yaml_job_container]: https://learn.microsoft.com/azure/devops/pipelines/yaml-schema/jobs-job-container
[yaml_resources]: https://learn.microsoft.com/azure/devops/pipelines/yaml-schema/resources
[lockfile_generation]: ../cli/lockfile_generation.md

### Repository checkout

The `phylum-ci` logic for determining changes in dependency files requires git history beyond what is available in a
shallow clone/checkout/fetch. To ensure the shallow fetch option is disabled for the pipeline, an explicit checkout
step is specified here, with `fetchDepth` set to `0`. It is also possible to disable the shallow fetch option in the
[pipeline settings UI][pipeline_settings]. See the [YAML schema steps.checkout definition][yaml_checkout] documentation
for more detail.

In order to support CI triggers, certain git operations are needed to determine the default branch name and set the
remote HEAD ref for it since Azure Pipelines does not do so during repository checkout. These operations require git
credentials to be available after the initial fetch, which is done with the `persistCredentials` property. This property
is not required if CI triggers are disabled (e.g., via `trigger: none`).

```yaml
      # Reference: https://learn.microsoft.com/azure/devops/pipelines/yaml-schema/steps-checkout
      - checkout: self
        fetchDepth: 0
        persistCredentials: true    # Needed only for CI triggers
```

[pipeline_settings]: https://learn.microsoft.com/azure/devops/pipelines/repos/azure-repos-git#shallow-fetch
[yaml_checkout]: https://learn.microsoft.com/azure/devops/pipelines/yaml-schema/steps-checkout

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
      # The default behavior is to only analyze newly added dependencies
      # against the active policy set at the Phylum project level.
      - script: phylum-ci

      # Provide debug level output
      - script: phylum-ci -vv

      # Consider all dependencies in analysis results instead of just the newly added ones.
      # The default is to only analyze newly added dependencies, which can be useful for
      # existing code bases that may not meet established policy rules yet,
      # but don't want to make things worse. Specifying `--all-deps` can be useful for
      # casting the widest net for strict adherence to Quality Assurance (QA) standards.
      - script: phylum-ci --all-deps

      # Some lockfile types (e.g., Python/pip `requirements.txt`) are ambiguous in that
      # they can be named differently and may or may not contain strict dependencies.
      # In these cases it is best to specify an explicit path, either with the `--depfile`
      # option or in a `.phylum_project` file. The easiest way to do that is with the
      # Phylum CLI, using `phylum init` command (docs.phylum.io/cli/commands/phylum_init)
      # and committing the generated `.phylum_project` file.
      - script: phylum-ci --depfile requirements-prod.txt

      # Specify multiple explicit dependency file paths
      - script: phylum-ci --depfile requirements-prod.txt Cargo.toml path/to/dependency.file

      # Force analysis, even when no dependency file has changed. This can be useful for
      # manifests, where the loosely specified dependencies may not change often but the
      # completely resolved set of strict dependencies does.
      - script: phylum-ci --force-analysis

      # Force analysis for all dependencies in a manifest file. This is especially useful
      # for *workspace* manifest files where there is no companion lockfile (e.g., libraries).
      - script: phylum-ci --force-analysis --all-deps --depfile Cargo.toml

      # Ensure the latest Phylum CLI is installed.
      - script: phylum-ci --force-install

      # Install a specific version of the Phylum CLI.
      - script: phylum-ci --phylum-release 4.8.0 --force-install

      # Mix and match for your specific use case.
      - script: |
        phylum-ci \
          -vv \
          --depfile requirements-dev.txt \
          --depfile requirements-prod.txt path/to/dependency.file \
          --depfile Cargo.toml \
          --force-analysis \
          --all-deps
```

### Script Variables

The script step environment variables are used to ensure the `phylum-ci` tool is able to perform it's job.

A [Phylum token][phylum_tokens] with API access is required to perform analysis on project dependencies.
[Contact Phylum][phylum_contact] or [register][app_register] to gain access.
See also [`phylum auth register`][phylum_register] command documentation and consider using a bot or group account
for this token.

#### Azure Repos Git Build Repositories

An Azure DevOps token with API access is required to use the API (e.g., to post notes/comments) when the build
repository is [Azure Repos Git][azure_repos_git] and PR triggers are enabled.
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

#### GitHub Build Repositories

A [GitHub PAT][GH_PAT] with API access is required to use the API (e.g., to post notes/comments) when the build
repository is [GitHub][github_repos] and PR triggers are enabled.
This can be a fine-grained or classic PAT.

If using a fine-grained PAT, it will need repository access and permissions for read access to `metadata` and
read/write access to `pull requests`. See [permissions required for fine-grained PATs][fine_pats] for more info.

If using a classic PAT, it will need the `repo` scope or minimally the `public_repo` scope if private
repositories are not used. See [documentation for scopes][scopes] for more info.

#### Setting Values

Values for the `PHYLUM_API_KEY` and either `AZURE_TOKEN` or `GITHUB_TOKEN` environment variable (e.g., `PHYLUM_TOKEN`
and one of either `AZURE_PAT` or `GITHUB_PAT` in the example here) can come from the pipeline UI, a variable group,
or an Azure Key Vault. View the full [documentation for how to set secret variables][secret_variables] for more
information. Since these tokens are sensitive, **care should be taken to protect them appropriately**.

[azure_pat]: https://learn.microsoft.com/azure/devops/organizations/accounts/use-personal-access-tokens-to-authenticate
[secret_variables]: https://learn.microsoft.com/azure/devops/pipelines/process/set-secret-variables

```yaml
        env:
          # Contact Phylum (phylum.io/contact-us) or register (app.phylum.io/register)
          # to gain access. See also `phylum auth register`
          # (docs.phylum.io/cli/commands/phylum_auth_register) command documentation.
          # Consider using a bot or group account for this token.
          # This value (`PHYLUM_TOKEN`) will need to be set as a secret variable:
          # https://learn.microsoft.com/azure/devops/pipelines/process/set-secret-variables
          PHYLUM_API_KEY: $(PHYLUM_TOKEN)

          # NOTE: These are examples. Only one `AZURE_TOKEN` entry line is expected, and only
          #       when the build repository is hosted in Azure Repos Git with PR triggers enabled.
          #
          # Use the `System.AccessToken` provided automatically at the start of each pipeline build.
          # This value does not have to be set as a secret variable since it is provided by default.
          AZURE_TOKEN: $(System.AccessToken)
          #
          # Use a personal access token (PAT).
          # This value (`AZURE_PAT`) will need to be set as a secret variable:
          # https://learn.microsoft.com/azure/devops/pipelines/process/set-secret-variables
          AZURE_TOKEN: $(AZURE_PAT)

          # NOTE: A `GITHUB_TOKEN` entry is only needed for GitHub hosted build repositories
          #       with PR triggers enabled.
          #
          # Use a personal access token (PAT).
          # This value (`GITHUB_PAT`) will need to be set as a secret variable:
          # https://learn.microsoft.com/azure/devops/pipelines/process/set-secret-variables
          GITHUB_TOKEN: $(GITHUB_PAT)
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
