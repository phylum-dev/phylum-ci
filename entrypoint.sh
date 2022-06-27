#!/bin/sh

# This entrypoint script is meant for the GitHub Action integration defined in the
# `phylum-dev/phylum-analyze-pr-action` repository. It is available for any other users
# of the `phylumio/phylum-ci` Docker image who wish to specify an entrypoint for the
# image since there is not one defined in the corresponding Dockerfile.
#
# There is no ENTRYPOINT in the Dockerfile by design. That way, it is possible to provide
# *unquoted* extra parameters to run arbitrary commands in the context of the container:
#
# $ docker run --rm phylumio/phylum-ci:latest ls -alh /
#
# In cases where an entrypoint is needed, this script is provided.
# To make use of it, add the `--entrypoint` option to a docker run command, specifying
# the `entrypoint.sh` script, and providing extra parameters as a *quoted* string:
#
# $ docker run --rm --entrypoint entrypoint.sh phylumio/phylum-ci:latest "ls -alh /"
#
# One such case is the `phylum-dev/phylum-analyze-pr-action` GitHub Action which is a
# Docker container action. GitHub Docker container actions allow for this `--entrypoint`
# option to be specified, but only as a string and not a list:
# https://docs.github.com/en/actions/creating-actions/metadata-syntax-for-github-actions#runsentrypoint
# https://docs.docker.com/engine/reference/builder/#shell-form-entrypoint-example
#
# This limitation means the ENTRYPOINT is of the "shell form" instead of the preferred
# "exec form." The action is also configured to use `runs.args`
# (https://docs.github.com/en/actions/creating-actions/metadata-syntax-for-github-actions#runsargs),
# which is an array of strings used in place of the `CMD` instruction in the Dockerfile
# and which get passed to the container's `ENTRYPOINT` when the container starts up.
#
# The interaction of CMD and ENTRYPOINT
# (https://docs.docker.com/engine/reference/builder/#understand-how-cmd-and-entrypoint-interact),
# combined with YAML syntax limitations, result in the option to provide a single input
# to the overridden entrypoint. This means it has to be an executable. Most solutions
# recommend creating a wrapper script that expands the CMD input(s) into a series of
# tokens that can be executed by the shell. GitHub recommends a script just like this:
# https://docs.github.com/en/actions/creating-actions/dockerfile-support-for-github-actions#entrypoint

# `$*` splits `args` in a string separated by whitespace. Reference:
# https://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html#tag_18_05_02
sh -c "$*"
