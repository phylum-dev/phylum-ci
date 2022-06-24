#!/bin/sh

# This entrypoint script is used for the GitHub Action integration, which allows for an `entrypoint` to be specified,
# but only in shell form since it takes a string and not a list. The `ENTRYPOINT` can be specified in the Dockerfile
# with the recommended exec form, but the desire is to not have an `ENTRYPOINT` in the Dockerfile at all. That way, it
# will continue to be possible to provide unquoted extra parameters to the running container.

# `$*` splits `args` in a string separated by whitespace.
# Reference: https://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html#tag_18_05_02
sh -c "$*"
