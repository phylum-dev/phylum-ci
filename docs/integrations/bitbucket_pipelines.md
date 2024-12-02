# Bitbucket Pipelines Integration

## Quickstart

Add the following "Phylum Analyze" step to a `bitbucket-pipelines.yml` configuration, in one or more pipeline start
conditions:

```yaml
# Ensure these variables are set at the repository or workspace level:
#  - `PHYLUM_API_KEY`: Phylum authentication token
#  - `BITBUCKET_TOKEN`: repository, project, or workspace access token with
#                       `pullrequest` (read) scope. It is not needed when in
#                       audit mode or when comment generation is disabled.

    - step:
        name: Phylum Analyze
        image: phylumio/phylum-ci:latest
        clone:
          depth: full
        script:
          - phylum-ci -vv
```

## Overview

Once configured for a repository, the Bitbucket Pipelines integration will provide analysis of project
dependencies from manifests and lockfiles. This can happen in a branch or default pipeline as a result of a commit
or in a pull request (PR) pipeline.

For PR pipelines, analyzed dependencies will include any that are added/modified in the PR.

For branch pipelines, the analyzed dependencies will be determined by comparing dependency files in the branch to
the default branch. **All** dependencies will be analyzed when the branch pipeline is run on the default branch.

The results will be provided in the pipeline logs and provided as a comment on the PR unless the option to skip
comments is provided. The CI job will return an error (i.e., fail the build) if any of the analyzed dependencies fail
to meet the established policy unless audit mode is specified.

There will be no comment if no dependencies were added or modified for a given PR.
If one or more dependencies are still processing (no results available), then the comment will make that clear and
the CI job will only fail if dependencies that have _completed analysis results_ do not meet the active policy.

## Prerequisites

Bitbucket Cloud is supported for repositories hosted on [https://bitbucket.org/](https://bitbucket.org/).
Bitbucket Data Center is not currently supported.

The Bitbucket Pipelines environment is primarily supported through the use of a Docker image. The prerequisites
for using this image are:

* Access to the [`phylumio/phylum-ci` Docker image][docker_image]
* A [Bitbucket access token][bb_tokens] with API access
  * This is only required when:
    * Using the integration in pull request pipelines
    * Comment generation has not been skipped
  * The token needs the `pullrequest` (read) scope
* A [Phylum token][phylum_tokens] with API access
  * [Contact Phylum][phylum_contact] or [register][app_register] to gain access
    * See also [`phylum auth register`][phylum_register] command documentation
  * Consider using a bot or group account for this token
* Access to the Phylum API endpoints
  * That usually means a connection to the internet, optionally via a proxy

[docker_image]: https://hub.docker.com/r/phylumio/phylum-ci/tags
[bb_tokens]: https://developer.atlassian.com/cloud/bitbucket/rest/intro/#access-tokens
[phylum_tokens]: ../knowledge_base/api-keys.md
[phylum_contact]: https://phylum.io/contact-us/
[app_register]: https://app.phylum.io/register
[phylum_register]: ../cli/commands/phylum_auth_register.md

## Configure `bitbucket-pipelines.yml`

Phylum analysis of dependencies can be added to existing CI workflows or on it's own with this minimal configuration:

```yaml
# Ensure these variables are set at the repository or workspace level:
#  - `PHYLUM_API_KEY`: Phylum authentication token
#  - `BITBUCKET_TOKEN`: repository, project, or workspace access token with
#                       `pullrequest` (read) scope. It is not needed when in
#                       audit mode or when comment generation is disabled.

pipelines:
  pull-requests:
    '**':
      - step:
          name: Phylum Analyze PR
          image: phylumio/phylum-ci:latest
          clone:
            depth: full
          script:
            - phylum-ci -vv
  default:
    - step:
        name: Phylum Analyze branch
        image: phylumio/phylum-ci:latest
        clone:
          depth: full
        script:
          - phylum-ci -vv
```

This configuration contains pipeline definitions for the `pull-requests` and `default` start conditions. It will
run for _all_ pull requests and pushes to _any_ branch. It provides debug output but otherwise does not override any of
the `phylum-ci` arguments, which are all either optional or default to secure values. Let's take a deeper dive into
each part of the configuration:

### User-defined variables

There are several user-defined variables needed to ensure the `phylum-ci` tool is able to perform it's job. Ensure
these variables are set at the repository or workspace level. See the [user-defined variables][user_vars] documentation
for more info.

A [Phylum token][phylum_tokens] with API access is required to perform analysis on project dependencies.
[Contact Phylum][phylum_contact] or [register][app_register] to gain access.
See also [`phylum auth register`][phylum_register] command documentation and consider using a bot or group account
for this token. Provide the token value in a user-defined variable named `PHYLUM_API_KEY`.

A Bitbucket token with API access is required to use the API (e.g., to post comments). This can be a repository,
project, or workspace access token. The token needs the `pullrequest` (read) scope. The name given to the token
will be the one that appears to post the comments on the PR. Therefore, it might be worth naming it something like
`Phylum Analysis`. See the [Bitbucket Access Tokens][bb_tokens] documentation for more info.

Note, the Bitbucket token is only required when this Phylum integration is used in
[pull request pipelines][pr_pipelines] where comment generation is not skipped. It is not required when used in branch
based pipelines. Provide the token value in a user-defined variable named `BITBUCKET_TOKEN`.

Values for the `BITBUCKET_TOKEN` and `PHYLUM_API_KEY` variables are sensitive and should be set as a
[secured variable][secured_var]. **Care should be taken to protect them appropriately**.

[user_vars]: https://support.atlassian.com/bitbucket-cloud/docs/variables-and-secrets/#User-defined-variables
[pr_pipelines]: https://support.atlassian.com/bitbucket-cloud/docs/pipeline-start-conditions/#Pull-Requests
[secured_var]: https://support.atlassian.com/bitbucket-cloud/docs/variables-and-secrets/#Secured-variables

### Pipeline start conditions

There are a handful of different [pipeline start conditions][start_conditions] available to trigger CI. The Phylum
analysis step can be included in most of these, or even multiple start conditions. The exceptions _may_ be `tags` and
`custom` pipelines. The example configuration adds the step to both the `pull-requests` and `default` pipelines:

```yaml
pipelines:
  # Pipeline definition for pull requests
  pull-requests:
    '**':   # Glob pattern to specify all branches
      - step:
          # Add the Phylum Analyze step here

  # Pipeline definition for all branches that don't
  # match a pipeline definition in other sections
  default:
    - step:
        # Add the Phylum Analyze step here
```

If the `default` pipeline start condition is not used, it is recommended to at least enable the `branches` pipeline
start condition for the default branch. That way, Phylum analysis results will stay current with updates to the default
branch.

```yaml
pipelines:
  # Pipeline definition for specific branches
  branches:
    main:   # The name of the default branch
      - step:
          # Add the Phylum Analyze step here
```

[start_conditions]: https://support.atlassian.com/bitbucket-cloud/docs/pipeline-start-conditions/

### Step name

The step name is optional, can be named what you like, and have different names depending on the pipeline context.
See the [`name` step option][step_option_name] documentation for more information.

```yaml
pipelines:
  pull-requests:
    '**':
      - step:
          name: Phylum Analyze PR    # Name this what you like

  default:
    - step:
        name: Phylum Analyze branch  # Name this what you like
```

[step_option_name]: https://support.atlassian.com/bitbucket-cloud/docs/step-options/#Name

### Docker image selection

Choose the Docker image tag to match your comfort level with image dependencies. `latest` is a "rolling" tag that
will point to the image created for the latest released `phylum-ci` Python package. A particular version tag
(e.g., `0.42.4-CLIv6.1.2`) is created for each release of the `phylum-ci` Python package and _should_ not change
once published.

However, to be certain that the image does not change...or be warned when it does because it won't be available
anymore...use the SHA256 digest of the tag. The digest can be found by looking at the `phylumio/phylum-ci`
[tags on Docker Hub][docker_image] or with the command:

```sh
# NOTE: The command-line JSON processor `jq` is used here for the sake of a one line example. It is not required.
❯ docker manifest inspect --verbose phylumio/phylum-ci:0.42.4-CLIv6.1.2 | jq .Descriptor.digest
"sha256:77b761ccef10edc28b0f009a40fbeab240bf004522edaaea05572dc3728b6ca6"
```

For instance, at the time of this writing, all of these tag references pointed to the same image:

```yaml
  # NOTE: These are examples. Only one image line for `phylum-ci` is expected.

  # Not specifying a tag means a default of `latest`
  image: phylumio/phylum-ci

  # Be more explicit about wanting the `latest` tag
  image: phylumio/phylum-ci:latest

  # Use a specific release version of the `phylum-ci` package
  image: phylumio/phylum-ci:0.42.4-CLIv6.1.2

  # Use a specific image with it's SHA256 digest
  image: phylumio/phylum-ci@sha256:77b761ccef10edc28b0f009a40fbeab240bf004522edaaea05572dc3728b6ca6
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
  # NOTE: These are examples. Only one image line for `phylum-ci` is expected.

  # Use the most current release of *both* `phylum-ci` and the Phylum CLI
  image: phylumio/phylum-ci:slim

  # Use the `slim` image with a specific release version of `phylum-ci` and Phylum CLI
  image: phylumio/phylum-ci:0.42.4-CLIv6.1.2-slim
```

See the Docker [image option][image_option] and [build environment][docker_builds] documentation for more information.

[lockfile_generation]: ../cli/lockfile_generation.md
[image_option]: https://support.atlassian.com/bitbucket-cloud/docs/docker-image-options/
[docker_builds]: https://support.atlassian.com/bitbucket-cloud/docs/use-docker-images-as-build-environments/

### Git clone behavior

The `git` version control system is used within the `phylum-ci` package to do things like determine if there was a
dependency file change and, when specified, report on new dependencies only. Therefore, a full clone of the
repository is required to ensure that the local working copy is always pristine and history is available to pull the
requested information.

```yaml
    - step:
        clone:
          depth: full
```

See the [git clone behavior][clone_behavior] documentation for more information.

[clone_behavior]: https://support.atlassian.com/bitbucket-cloud/docs/git-clone-behavior/

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

    # Provide debug level output. Highly recommended.
    - phylum-ci -vv

    # Consider all dependencies in analysis results instead of just the newly added ones.
    # The default is to only analyze newly added dependencies, which can be useful for
    # existing code bases that may not meet established policy rules yet,
    # but don't want to make things worse. Specifying `--all-deps` can be useful for
    # casting the widest net for strict adherence to Quality Assurance (QA) standards.
    - phylum-ci --all-deps

    # Some lockfile types (e.g., Python/pip `requirements.txt`) are ambiguous in
    # that they can be named differently and may or may not contain strict
    # dependencies. In these cases it is best to specify an explicit path, either
    # with the `--depfile` option or in a `.phylum_project` file. For more, see:
    # https://docs.phylum.io/knowledge_base/phylum_project_files
    - phylum-ci --depfile requirements-prod.txt

    # Specify multiple explicit dependency file paths.
    - phylum-ci --depfile requirements-prod.txt Cargo.toml path/to/dependency.file

    # Exclude dependency files by gitignore-style pattern.
    - phylum-ci --exclude "requirements-*.txt"

    # Specify multiple exclusion patterns.
    - phylum-ci --exclude "build.gradle" "tests/fixtures/"
    - |
      phylum-ci \
        --exclude "/requirements-*.txt" \
        --exclude "build.gradle" "fixtures/"

    # Force analysis for all dependencies in a manifest file. This is especially useful
    # for *workspace* manifest files where there is no companion lockfile (e.g., libraries).
    - phylum-ci --force-analysis --all-deps --depfile Cargo.toml

    # Perform analysis as part of an organization and/or group-owned project.
    # When an org is specified, a group name must also be specified.
    # A paid account is needed to use orgs or groups: https://phylum.io/pricing
    - phylum-ci --org my_org --group my_group
    - phylum-ci --group my_group

    # Analyze all dependencies in audit mode, to gain insight without failing builds.
    - phylum-ci --all-deps --audit

    # Ensure the latest Phylum CLI is installed.
    - phylum-ci --force-install

    # Install a specific version of the Phylum CLI.
    - phylum-ci --phylum-release 4.8.0 --force-install

    # Mix and match for your specific use case.
    - |
      phylum-ci \
        -vv \
        --org my_org \
        --group my_group \
        --depfile requirements-dev.txt \
        --depfile requirements-prod.txt path/to/dependency.file \
        --depfile Cargo.toml \
        --force-analysis \
        --all-deps
```

### Exit Codes

The Phylum analysis step will return a zero (0) exit code when it completes successfully and a non-zero code otherwise.
The full and current list of exit codes is [documented here][exit_codes] and [options exist][script_options] to be
loose with setting them.

[exit_codes]: https://github.com/phylum-dev/phylum-ci#exit-codes

## Alternatives

It is also possible to make direct use of the [`phylum` Python package][pypi] within CI.
This may be necessary if the Docker image is unavailable or undesirable for some reason.
To use the `phylum` package, install it and call the desired entry points from a script under your control.
See the [Installation][installation] and [Usage][usage] sections of the [README file][readme] for more detail.

[pypi]: https://pypi.org/project/phylum/
[readme]: https://github.com/phylum-dev/phylum-ci/blob/main/README.md
[installation]: https://github.com/phylum-dev/phylum-ci/blob/main/README.md#installation
[usage]: https://github.com/phylum-dev/phylum-ci/blob/main/README.md#usage
