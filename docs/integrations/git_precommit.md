# Git `pre-commit` Integration

## Overview

[pre-commit] is a framework for managing and maintaining multi-language Git pre-commit hooks.

Phylum is available as a pre-commit hook.

Once configured for a repository, the git `pre-commit` integration will provide analysis of project dependencies
from manifests or lockfiles during a commit containing those dependency files. The hook will fail and provide
a report if any of the newly added/modified dependencies from the commit fail to meet the established policy.

The hook will be skipped if no dependencies were added or modified for a given commit.
If one or more dependencies are still processing (no results available), then the hook will only fail if
dependencies that have _completed analysis results_ do not meet the active policy.

[pre-commit]: https://pre-commit.com/

## Prerequisites

The prerequisites for using the git `pre-commit` hook are:

* The [pre-commit] package manager installed
* A [Phylum token][phylum_tokens] with API access
  * [Contact Phylum][phylum_contact] or [register][app_register] to gain access
    * See also [`phylum auth register`][phylum_register] command documentation
  * Consider using a bot or group account for this token
* Access to the Phylum API endpoints
  * That usually means a connection to the internet, optionally via a proxy
  * Support for on-premises installs are not available at this time

[phylum_tokens]: ../knowledge_base/api-keys.md
[phylum_contact]: https://phylum.io/contact-us/
[app_register]: https://app.phylum.io/register
[phylum_register]: ../cli/commands/phylum_auth_register.md

**NOTE: If the `phylum` CLI binary is installed locally, it will be used. Otherwise, the hook will install it.**

## Configure `.pre-commit-config.yaml`

Phylum analysis of dependencies can be added to existing `pre-commit` configurations or
on it's own with this minimal configuration:

```yaml
# This is the config for using `pre-commit` on this repository.
#
# See https://pre-commit.com for more information
---
repos:
  - repo: https://github.com/phylum-dev/phylum-ci
    rev: main
    hooks:
      - id: phylum
        # Optional: Specify the dependency file pattern for your repository
        files: ''
        # Optional: Specify additional arguments to be passed to `phylum-ci`
        args: []
```

**NOTE**: This example configuration uses a mutable reference for `rev`, which is a bad practice
(and only done here to prevent old tags from being used through copy and paste implementations).
A best practice is to ensure the `rev` key for all hooks is updated to a valid and current immutable reference:

```sh
pre-commit autoupdate --freeze
```

The hook can be customized with [optional keys][hook_config] in the config file.
Two common customization keys for the `phylum` hook are `files` and `args`:

[hook_config]: https://pre-commit.com/index.html#pre-commit-configyaml---hooks

### File Control

The `files` key in the hook configuration file is the way to ensure the hook only runs when specified
dependency files have changed, saving execution time.

The value for the `files` key is a [Python regular expression][re] and is matched with `re.search`.

[re]: https://docs.python.org/3/library/re.html#regular-expression-syntax

```yaml
        # NOTE: These are examples. Only one `files` key for the hook is expected

        # Specify `package-lock.json`
        files: ^package-lock\.json$

        # Specify `poetry.lock`
        files: ^poetry\.lock$

        # Specify `requirements-*.txt` files
        files: ^requirements-.*\.txt$

        # Specify both `package-lock.json` and `poetry.lock` on one line
        files: ^(package-lock\.json|poetry\.lock)$

        # Specify multiple files using the inline `re.VERBOSE` flag `(?x)`
        files: |
            (?x)^(
                package-lock\.json|
                poetry\.lock|
                requirements-.*\.txt|
                Cargo\.toml|
                path/to/dependency\.file
            )$
```

### Argument Control

The `args` key is the way to exert control over the execution of the Phylum analysis.
The `phylum-ci` script entry point is called by the hook. It has a number of arguments that are all optional
and defaulted to secure values. To view the arguments, their description, and default values, run the script
with `--help` output as specified in the [Usage section of the top-level README.md][usage] or view the
[script options output][script_options] for the latest release.

[usage]: https://github.com/phylum-dev/phylum-ci/blob/main/README.md#usage
[script_options]: https://github.com/phylum-dev/phylum-ci/blob/main/docs/script_options.md

```yaml
        # NOTE: These are examples. Only one `args` key for the hook is expected

        # Use the defaults for all the arguments.
        # The default behavior is to only analyze newly added dependencies
        # against the active policy set at the Phylum project level.
        # The key can be removed if the defaults are used.
        args: []

        # Consider all dependencies in analysis results instead of just the newly added ones.
        # The default is to only analyze newly added dependencies, which can be useful for
        # existing code bases that may not meet established policy rules yet,
        # but don't want to make things worse. Specifying `--all-deps` can be useful for
        # casting the widest net for strict adherence to Quality Assurance (QA) standards.
        args: [--all-deps]

        # Provide debug level output.
        args: [-vv]

        # Some lockfile types (e.g., Python/pip `requirements.txt`) are ambiguous in that
        # they can be named differently and may be a manifest or a lockfile. In cases where
        # only specific dependency files are meant to be analyzed, it is best to specify an
        # explicit path, either with the `--depfile` option or in a `.phylum_project` file.
        # For more, see: https://docs.phylum.io/knowledge_base/phylum_project_files
        args: [--depfile=requirements-prod.txt]

        # Specify multiple explicit dependency file paths.
        args:
          - --depfile=requirements-prod.txt
          - --depfile=package-lock.json
          - --depfile=poetry.lock
          - --depfile=Cargo.toml
          - --depfile=path/to/dependency.file

        # Exclude dependency files by gitignore-style pattern.
        args: [--exclude=requirements-*.txt]

        # Specify multiple exclusion patterns.
        args:
          - --exclude=/requirements-*.txt
          - --exclude=build.gradle
          - --exclude=fixtures/

        # Force analysis for all dependencies in a manifest file. This is especially useful
        # for *workspace* manifest files where there is no companion lockfile (e.g., libraries).
        args: [--force-analysis, --all-deps, --depfile=Cargo.toml]

        # Perform analysis as part of an organization and/or group-owned project.
        # When an org is specified, a group name must also be specified.
        args: [--org=my_org, --group=my_group]
        args: [--group=my_group]

        # Ensure the latest Phylum CLI is installed.
        args: [--force-install]

        # Install a specific version of the Phylum CLI.
        args: [--phylum-release=4.8.0, --force-install]

        # Mix and match for your specific use case.
        args:
          - -vv
          - --org=my_org
          - --group=my_group
          - --depfile=requirements-prod.txt
          - --depfile=path/to/dependency.file
          - --depfile=Cargo.toml
          - --force-analysis
          - --all-deps
```

### Exit Codes

The Phylum analysis hook will return a zero (0) exit code when it completes successfully and a non-zero code otherwise.
The full and current list of exit codes is [documented here][exit_codes] and "Output Modification"
[options exist][script_options] to be strict or loose with setting them.

[exit_codes]: https://github.com/phylum-dev/phylum-ci#exit-codes

### Audit Mode

It is possible to use the Phylum hook in an audit mode, where analysis is performed but results do not affect the exit
code. To do so, update the `args` to include the `--audit` flag and add the `verbose: true` mapping to the hook
configuration. That will ensure the output of the hook is printed every time so it can be examined during the audit
period.

```yaml
repos:
  - repo: https://github.com/phylum-dev/phylum-ci
    rev: main
    hooks:
      - id: phylum
        # Additional args are possible, but `--audit` is the new one.
        args: [--audit]
        # Since the hook will pass in audit mode, forcing the output of the hook
        # to be printed will ensure failures have a chance of being noticed.
        verbose: true
```
