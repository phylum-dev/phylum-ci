#!/bin/sh

# This script is meant to provide a basic set of tests. It simply confirms that
# each of the tools expected for operation is present within the image. The
# path and version of the tool is shown and in some cases additional information
# is provided, like help or info output.

set -eu

# Check for a required command
require_command() {
    cmd="$1"
    help_msg="${2:-}"

    if ! type "${cmd}" > /dev/null 2>&1; then
        echo "ERROR: This script requires \`${cmd}\`. Please install it and re-run this script to continue." >&2
        if [ -n "${help_msg}" ]; then
            printf "\n" >&2
            echo "${help_msg}" >&2
        fi
        exit 1
    fi
}

usage() {
    cat 1>&2 <<EOF
docker_tests.sh [options]

Run basic tests against a supplied 'phylum-ci' Docker image.

Options
    -i, --image     Specify the image name to test
    -s, --slim      Specify to indicate a 'slim' image
    -h, --help      Show this help message
EOF
}

# All of the required commands (outside of POSIX)
require_command docker

# Parse command line arguments
while [ "$#" -gt 0 ]; do
    case "$1" in
        -i | --image)
            IMAGE=$2
            shift 2
            ;;
        -s | --slim)
            SLIM=1
            shift 1
            ;;
        -h | --help)
            usage
            exit 0
            ;;
        *)
            printf "Unsupported option: %s\n\n" "$1" >&2
            usage
            exit 1
            ;;
    esac
done

if [ -z "${IMAGE:-}" ]; then
    IMAGE="phylumio/phylum-ci:latest"
    echo " [!] \`--image\` option not specified. Attempting to use \`${IMAGE}\` ..."
fi

# These are the commands to ensure the base pre-requisites are available
SLIM_COMMANDS=$(cat <<EOF
set -eux
type git && git --version || false
type phylum && phylum --version && phylum --help || false
type phylum-init && phylum-init --version && phylum-init --help || false
type phylum-ci && phylum-ci --version && phylum-ci --help || false
EOF
)

# These are the commands to ensure lockfile generation is available by checking
# for each required tool: https://docs.phylum.io/docs/lockfile_generation
MANIFEST_COMMANDS=$(cat <<EOF
set -eux
type npm && npm --version || false
type yarn && yarn --version || false
type pnpm && pnpm --version || false
type pip && pip --version || false
type pipenv && pipenv --version || false
type poetry && poetry --version || false
type bundle && bundle --version || false
type mvn && mvn --version || false
type gradle && gradle --version || false
type go && go version || false
type cargo && cargo --version || false
type rustup && rustup --version && rustup show || false
type dotnet && dotnet --info || false
EOF
)

# The tests are meant to run as a non-root user/group to ensure all the required
# tools are available globally. This is an attempt to use the current user/group
# like when provided via `--user $(id -u):$(id -g)` and fall back to hard coded
# values when it happens to be run as `root:root`.
USER=$(id -u)
if [ "${USER}" -eq "0" ]; then
    USER=1000;
fi
GROUP=$(id -g)
if [ "${GROUP}" -eq "0" ]; then
    GROUP=1000;
fi

echo " [+] Running with UID:GID of: ${USER}:${GROUP}"

if [ -z "${SLIM:-}" ]; then
    echo " [+] \`--slim\` option not specified. Running all tests ..."
    docker run --rm --entrypoint entrypoint.sh --user "${USER}:${GROUP}" "${IMAGE}" "${SLIM_COMMANDS}"
    docker run --rm --entrypoint entrypoint.sh --user "${USER}:${GROUP}" "${IMAGE}" "${MANIFEST_COMMANDS}"
else
    echo " [+] \`--slim\` option specified. Skipping the lockfile generation tests ..."
    docker run --rm --entrypoint entrypoint.sh --user "${USER}:${GROUP}" "${IMAGE}" "${SLIM_COMMANDS}"
fi
