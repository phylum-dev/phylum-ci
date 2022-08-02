---
title: Git pre-commit Integration
category: 62cdf6722c2c1602a4b69643
hidden: false
---
# Git `pre-commit` Integration

## Overview

[pre-commit] is a framework for managing and maintaining multi-language Git pre-commit hooks.

[pre-commit]: https://pre-commit.com/

Phylum is available as a pre-commit hook.

Once configured for a repository, the git `pre-commit` integration will provide analysis of project dependencies
from a lockfile during a commit containing that lockfile. The hook will fail and provide a report if any of the
newly added/modified dependencies from the commit fail to meet the project risk thresholds for any of the five
Phylum risk domains:

* Vulnerability (aka `vul`)
* Malicious Code (aka `mal`)
* Engineering (aka `eng`)
* License (aka `lic`)
* Author (aka `aut`)

See [Phylum Risk Domains documentation](https://docs.phylum.io/docs/phylum-package-score#risk-domains) for more detail.

**NOTE**: It is not enough to have the total project threshold set. Individual risk domain threshold values
must be set, either in the Phylum web UI or with `phylum-ci` options, in order to enable analysis results.
Otherwise, the risk domain is considered disabled and the threshold value used will be zero (0).

The hook will be skipped if no dependencies were added or modified for a given commit.
If one or more dependencies are still processing (no results available), then the hook will only fail if
dependencies that have _completed analysis results_ do not meet the specified project risk thresholds.

## Prerequisites

The pre-requisites for using the git `pre-commit` hook are:

* The [pre-commit] package manager installed
* A [Phylum token][phylum_tokens] with API access
  * [Contact Phylum][phylum_contact] or create an account and register to gain access
    * See also [`phylum auth register`][phylum_register] command documentation
  * Consider using a bot or group account for this token
* Access to the Phylum API endpoints
  * That usually means a connection to the internet, optionally via a proxy
  * Support for on-premises installs are not available at this time
* A `.phylum_project` file exists at the root of the repository
  * See [`phylum project`](https://docs.phylum.io/docs/phylum_project) and
    [`phylum project create`](https://docs.phylum.io/docs/phylum_project_create) command documentation

[phylum_tokens]: https://docs.phylum.io/docs/api-keys
[phylum_contact]: https://phylum.io/contact-us/
[phylum_register]: https://docs.phylum.io/docs/phylum_auth_register

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
        # Optional: Specify the lockfile pattern for your repository
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

The `files` key in the hook configuration file is the way to ensure the hook only runs when the specified
lockfile has changed, saving execution time.

The value for the `files` key is a [Python regular expression][re] and are matched with `re.search`.

[re]: https://docs.python.org/3/library/re.html#regular-expression-syntax

```yaml
        # NOTE: These are examples. Only one `files` key for the hook is expected

        # Specify `package-lock.json`
        files: ^package-lock\.json$

        # Specify `poetry.lock`
        files: ^poetry\.lock$

        # Specify `requirements-*.txt` files
        # NOTE: An explicit lockfile should still be specified in the `args` key
        files: ^requirements-.*\.txt$
```

### Argument Control

The `args` key is the way to exert control over the execution of the Phylum analysis.
The `phylum-ci` script entry point is called by the hook. It has a number of arguments that are all optional
and defaulted to secure values. To view the arguments, their description, and default values, run the script
with `--help` output as specified in the [Usage section of the top-level README.md][usage] or view the
[source code][src] directly.

[usage]: https://github.com/phylum-dev/phylum-ci/blob/main/README.md#usage
[src]: https://github.com/phylum-dev/phylum-ci/blob/main/src/phylum/ci/cli.py

```yaml
        # NOTE: These are examples. Only one `args` key for the hook is expected

        # Use the defaults for all the arguments.
        # The default behavior is to only analyze newly added dependencies against
        # the risk domain threshold levels set at the Phylum project level.
        # The key can be removed if the defaults are used.
        args: []

        # Consider all dependencies in analysis results instead of just the newly added ones.
        # The default is to only analyze newly added dependencies, which can be useful for
        # existing code bases that may not meet established project risk thresholds yet,
        # but don't want to make things worse. Specifying `--all-deps` can be useful for
        # casting the widest net for strict adherence to Quality Assurance (QA) standards.
        args: [--all-deps]

        # Some lockfile types (e.g., Python/pip `requirements.txt`) are ambiguous in that
        # they can be named differently and may or may not contain strict dependencies.
        # In these cases, it is best to specify an explicit lockfile path.
        args: [--lockfile=requirements-prod.txt]

        # Thresholds for the five risk domains may be set at the Phylum project level.
        # They can be set differently for the hook.
        # NOTE: The shortened form is used here for brevity, but the long form might be more
        #       descriptive for future readers. For instance `--vul-threshold` instead of `-u`.
        args: [-u=60, -m=60, -e=70, -c=90, -o=80]

        # Ensure the latest Phylum CLI is installed.
        args: [--force-install]

        # Install a specific version of the Phylum CLI.
        args: [--phylum-release=3.3.0, --force-install]

        # Mix and match for your specific use case.
        args: [-u=60, -m=60, -e=70, -c=90, -o=80, --lockfile=requirements-prod.txt, --all-deps]
```
