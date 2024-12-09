# syntax=docker/dockerfile:1
# The syntax statement above is to make use of buildkit's build mounts for caching

##########################################################################################
# This Dockerfile makes use of BuildKit mode, which needs to be enabled client side first:
#
# $ export DOCKER_BUILDKIT=1
#
# This Dockerfile can be used to build the project's package within the image it creates.
# To do so, simply build the image WITHOUT any build args specified (e.g., `--build-arg`):
#
# $ docker build --tag phylum-ci .
#
# This Dockerfile can also be used in CI, as part of the release pipeline.
# The goal there is to ensure that the exact Python package that was built and
# released is the one that is installed while creating this image. Prerequisites are:
#
#   * The package has already been built (e.g., `poetry build -vvv`)
#   * There is exactly one wheel available to reference by glob expression
#
# To make use of this feature, build the image WITH build args specified:
#
# $ export PKG_SRC=dist/phylum-*.whl
# $ export PKG_NAME=phylum-*.whl
# $ docker build --tag phylum-ci --build-arg PKG_SRC --build-arg PKG_NAME .
#
# Another build arg is exposed to optionally specify the Phylum CLI version to install:
#
# $ docker build --tag phylum-ci --build-arg CLI_VER=v4.8.0 .
#
# The PHYLUM_API_URI build arg is exposed to optionally specify the URI of a Phylum API
# instance to use:
#
# $ export PHYLUM_API_URI=https://api.staging.phylum.io
# $ docker build --tag phylum-ci --build-arg PHYLUM_API_URI .
#
# Another build arg is exposed to optionally specify a GitHub Personal Access Token (PAT):
#
# $ docker build --tag phylum-ci --build-arg GITHUB_TOKEN .
#
# Providing a build argument like this (without a value) works when there is already an
# environment variable defined with the same name. Providing a GitHub PAT is useful to
# make authenticated requests and therefore increase the API rate limit.
#
# To make use of BuildKit's inline layer caching feature, add the `BUILDKIT_INLINE_CACHE`
# build argument to any instance of building an image. Then, that image can be used
# locally or remotely (if it was pushed to a repository) to warm the build cache by using
# the `--cache-from` argument:
#
# $ docker build --tag phylumio/phylum-ci:cache --build-arg BUILDKIT_INLINE_CACHE=1 .
# $ docker push phylumio/phylum-ci:cache && docker image rm phylumio/phylum-ci:cache
# $ docker build --tag phylumio/phylum-ci:faster --cache-from phylumio/phylum-ci:cache .
#
# There is no ENTRYPOINT in this Dockerfile by design. That way, it is possible to provide
# unquoted extra parameters to run arbitrary commands in the context of the container:
#
# $ docker run --rm phylumio/phylum-ci:latest ls -alh /
#
# However, there may be cases where an entrypoint is needed. One is provided and placed in
# a directory that will be included in the final layer and also known to be part of the
# $PATH. To make use of it, add the `--entrypoint` option to a docker run command,
# specifying the `entrypoint.sh` script, providing extra parameters as a *quoted* string:
#
# $ docker run --rm --entrypoint entrypoint.sh phylumio/phylum-ci:latest "ls -alh /"
#
# Images built from this Dockerfile can be tested for basic functionality:
#
# $ docker build --tag phylum-ci .
# $ scripts/docker_tests.sh --image phylum-ci
##########################################################################################

FROM python:3.12-slim-bookworm AS builder

# PKG_SRC is the path to a built distribution/wheel and PKG_NAME is the name of the built
# distribution/wheel. Both can optionally be specified in glob form. When not defined,
# the values will default to the root of the package (i.e., `pyproject.toml` path).
ARG PKG_SRC
ARG PKG_NAME

ENV APP_PATH="/app"
ENV POETRY_VENV="${APP_PATH}/.venv"
ENV POETRY_PATH="${POETRY_VENV}/bin/poetry"
ENV PHYLUM_VENV="/opt/venv"
ENV PHYLUM_VENV_PIP="${PHYLUM_VENV}/bin/pip"
ENV PIP_NO_COMPILE=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV POETRY_VERSION="1.8.5"

WORKDIR ${APP_PATH}

RUN set -eux; \
    python -m venv ${PHYLUM_VENV}; \
    ${PHYLUM_VENV_PIP} install --no-cache-dir --upgrade pip setuptools
RUN set -eux; \
    python -m venv ${POETRY_VENV}; \
    ${POETRY_VENV}/bin/pip install --no-cache-dir --upgrade pip setuptools; \
    ${POETRY_VENV}/bin/pip install --no-cache-dir poetry==${POETRY_VERSION} poetry-plugin-export

# Copy the bare minimum needed for specifying dependencies.
# This will enable better layer caching and faster builds when iterating locally.
# `--without-hashes` is used to ensure the `pip` cache mount is used for packages that
# would otherwise only match the sdist and therefore have to be built for every run.
# References:
#   * https://pythonspeed.com/articles/pipenv-docker/
#   * https://hub.docker.com/r/docker/dockerfile
COPY pyproject.toml poetry.lock ./
RUN ${POETRY_PATH} export --without-hashes --format requirements.txt --output requirements.txt

# Cache the pip installed dependencies for faster builds when iterating locally.
# NOTE: This `--mount` feature requires BUILDKIT to be used
RUN --mount=type=cache,id=pip,target=/root/.cache/pip \
    set -eux; \
    ${PHYLUM_VENV_PIP} cache info; \
    ${PHYLUM_VENV_PIP} cache list; \
    ${PHYLUM_VENV_PIP} install -r requirements.txt pipenv poetry==${POETRY_VERSION}
COPY "${PKG_SRC:-.}" .
RUN ${PHYLUM_VENV_PIP} install --no-cache-dir ${PKG_NAME:-.}
RUN find ${PHYLUM_VENV} -type f -name '*.pyc' -delete

# Place the ENTRYPOINT alternative script in a directory included
# in the final layer and also known to be part of the $PATH
COPY entrypoint.sh ${PHYLUM_VENV}/bin/

FROM python:3.12-slim-bookworm

# CLI_VER specifies the Phylum CLI version to install in the image.
# Values should be provided in a format acceptable to the `phylum-init` script.
# When not defined, the value will default to `latest`.
ARG CLI_VER

# PHYLUM_API_URI is an optional build argument that can be used to specify
# the URI of a Phylum API instance to use.
ARG PHYLUM_API_URI

# GITHUB_TOKEN is an optional build argument that can be used to provide a
# GitHub Personal Access Token (PAT) in order to make authenticated requests
# and therefore increase the API rate limit.
ARG GITHUB_TOKEN

# Ref: https://docs.docker.com/engine/reference/builder/#automatic-platform-args-in-the-global-scope
ARG TARGETOS
ARG TARGETARCH

LABEL maintainer="Phylum, Inc. <engineering@phylum.io>"
LABEL org.opencontainers.image.source="https://github.com/phylum-dev/phylum-ci"

ENV PHYLUM_VENV="/opt/venv"

# Some tools get installed and used based on a home directory. This can cause trouble
# when using a container started from this image with a UID:GID that does not map to
# a user/group account in the container. Examples include:
#
#   * The installation directory is `/root` and the container user has no access
#   * The tool relies on the existence of a $HOME directory, which may not be true
#     * https://medium.com/redbubble/running-a-docker-container-as-a-non-root-user-7d2e00f8ee15
#
# The following tools are susceptible to this issue and therefore have been provided
# with explicit install/home directories that allow them to be globally accessible.
#
# Specify a common, globally accessible directory to use instead of $HOME
ENV INSTALL_DIR="/usr/local"
# Phylum, pip, and any other tool that supports the XDG spec
# Ref: https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html
ENV XDG_DATA_HOME="${INSTALL_DIR}/share"
ENV XDG_CONFIG_HOME="${INSTALL_DIR}/.config"
ENV XDG_STATE_HOME="${INSTALL_DIR}/state"
ENV XDG_CACHE_HOME="${INSTALL_DIR}/.cache"
# Node and npm
# Ref: https://github.com/tj/n
ENV N_PREFIX="${INSTALL_DIR}/n"
# Corepack, Yarn, and pnpm
# Ref: https://github.com/nodejs/corepack#environment-variables
ENV COREPACK_HOME="${INSTALL_DIR}/corepack"
# Rust, Cargo, and rustup
# Ref: https://rust-lang.github.io/rustup/installation/index.html#choosing-where-to-install
ENV RUSTUP_HOME="${INSTALL_DIR}/rustup"
ENV CARGO_HOME="${INSTALL_DIR}/cargo"
# Gradle
# Ref: https://docs.gradle.org/current/userguide/build_environment.html#sec:gradle_environment_variables
ENV GRADLE_HOME="${INSTALL_DIR}/gradle"
ENV GRADLE_USER_HOME="${GRADLE_HOME}/.gradle"
# Dotnet
# Ref: https://learn.microsoft.com/en-us/dotnet/core/tools/dotnet-environment-variables
ENV DOTNET_ROOT="/usr/share/dotnet"
ENV DOTNET_CLI_HOME="${XDG_DATA_HOME}"
# Go
# Ref: https://go.dev/doc/install/source#environment
ENV GOROOT="${INSTALL_DIR}/go"
ENV GOPATH="${XDG_DATA_HOME}/go"

ENV PATH=$PATH:${PHYLUM_VENV}/bin:${N_PREFIX}/bin:${GRADLE_HOME}/bin:${CARGO_HOME}/bin:${GOROOT}/bin

ENV PYTHONDONTWRITEBYTECODE=1

# Ref: https://learn.microsoft.com/en-us/dotnet/core/tools/dotnet-environment-variables
ENV DOTNET_CLI_TELEMETRY_OPTOUT=1
ENV DOTNET_SKIP_FIRST_TIME_EXPERIENCE=1
ENV DOTNET_NOLOGO=1

# Copy only Python packages to limit the image size. This includes the `phylum` package with it's
# `phylum-ci` and `phylum-init` entry points, plus the `pip`, `pipenv`, and `poetry` required tools.
COPY --from=builder ${PHYLUM_VENV} ${PHYLUM_VENV}

# Specify the shell options here, based on the use of pipelines.
# Ref: https://github.com/hadolint/hadolint/wiki/DL4006
SHELL ["/bin/bash", "-euxo", "pipefail", "-c"]
RUN \
    # Install prerequisites and package manager versions for `npm`, `bundle`, and `mvn` tools
    apt-get update; \
    apt-get upgrade --yes; \
    apt-get install --yes --no-install-recommends \
        git \
        git-lfs \
        bundler \
        maven \
        default-jdk-headless \
        procps \
        curl \
        unzip \
        jq \
        ; \
    # Make ENTRYPOINT alternative script available
    chmod +x "${PHYLUM_VENV}/bin/entrypoint.sh"; \
    #
    # Create a shell function instead of an alias for `curl`, with secure and common options
    # Ref: https://github.com/koalaman/shellcheck/wiki/SC2262
    curls() { curl --proto "=https" --tlsv1.2 -sSfL "$@"; }; \
    #
    # Install Phylum CLI
    phylum-init -vvv --phylum-release "${CLI_VER:-latest}" --global-install; \
    #
    # Install `node` and `npm` with `n`
    # Ref: https://github.com/tj/n
    curls -o n.sh https://raw.githubusercontent.com/tj/n/master/bin/n; \
    chmod +x n.sh && ./n.sh install lts; \
    npm config set --global engine-strict=true; \
    ./n.sh rm lts && rm n.sh; \
    #
    # Install and enable `corepack` with cached instances of the latest major versions of `yarn` and `pnpm` tools
    npm install --global corepack@latest; \
    corepack pack yarn@stable pnpm@latest; \
    corepack enable yarn pnpm; \
    #
    # Manual install of `gradle`
    GRADLE_VERSION=$(curls https://services.gradle.org/versions/current | jq -r '.version'); \
    GRADLE_DL="https://services.gradle.org/distributions/gradle-${GRADLE_VERSION}-bin.zip"; \
    GRADLE_DL_SHA256=$(curls "${GRADLE_DL}.sha256"); \
    curls -o gradle.zip "${GRADLE_DL}"; \
    printf "%s *gradle.zip" "${GRADLE_DL_SHA256}" | sha256sum -c -; \
    mkdir "${GRADLE_HOME}"; \
    unzip -d "${GRADLE_HOME}" gradle.zip; \
    mv "${GRADLE_HOME}/gradle-${GRADLE_VERSION}"/* "${GRADLE_HOME}/"; \
    rm gradle.zip && rmdir "${GRADLE_HOME}/gradle-${GRADLE_VERSION}/"; \
    mkdir --mode=777 "${GRADLE_USER_HOME}"; \
    #
    # Manual install of `go`
    # Ref: https://pkg.go.dev/golang.org/x/website/internal/dl
    GO_DL_URL="https://go.dev/dl/?mode=json"; \
    GO_DL_REL=$(curls "${GO_DL_URL}" | jq '.[0].files[] | select(.os==env.TARGETOS and .arch==env.TARGETARCH)'); \
    GO_DL_FILENAME=$(echo "${GO_DL_REL}" | jq -r '.filename'); \
    GO_DL_SHA256=$(echo "${GO_DL_REL}" | jq -r '.sha256'); \
    curls -o go.tgz "https://go.dev/dl/${GO_DL_FILENAME}"; \
    printf "%s *go.tgz" "${GO_DL_SHA256}" | sha256sum -c -; \
    rm -rf "${GOROOT}"; \
    tar -C "${INSTALL_DIR}" -xzf go.tgz; \
    rm go.tgz; \
    #
    # Manual install of Rust to get `cargo` tool
    curls https://sh.rustup.rs | sh -s -- -v -y --default-toolchain stable --profile minimal; \
    #
    # Install .NET SDK to get `dotnet` tool
    # Ref: https://github.com/dotnet/core/tree/main/release-notes
    DOTNET_SDK_LATEST_CHANNEL_VER=$( \
        curls https://raw.githubusercontent.com/dotnet/core/main/release-notes/releases-index.json | \
        jq -r '[."releases-index"[] | select(."support-phase"=="active")] | first."channel-version"' \
    ); \
    DEB_MAJ_VER=$(cut -d "." -f1 /etc/debian_version); \
    curls -o ms-prod.deb "https://packages.microsoft.com/config/debian/${DEB_MAJ_VER}/packages-microsoft-prod.deb"; \
    dpkg --install ms-prod.deb; \
    rm ms-prod.deb; \
    apt-get update; \
    apt-get install --yes --no-install-recommends "dotnet-sdk-${DOTNET_SDK_LATEST_CHANNEL_VER}"; \
    #
    # Create a git config file in a location accessible for $HOME-less users
    # Ref: https://git-scm.com/docs/git-config#FILES
    mkdir -vp "${XDG_CONFIG_HOME}/git" && touch "${XDG_CONFIG_HOME}/git/config"; \
    #
    # Ensure non-root users have necessary permissions
    mkdir -vp "${XDG_DATA_HOME}" "${XDG_CONFIG_HOME}" "${XDG_STATE_HOME}" "${XDG_CACHE_HOME}"; \
    chmod -vR 777 "${XDG_DATA_HOME}" "${XDG_CONFIG_HOME}" "${XDG_STATE_HOME}" "${XDG_CACHE_HOME}"; \
    chmod -v 666 "${COREPACK_HOME}/lastKnownGood.json"; \
    #
    # Final cleanup
    apt-get remove --yes --auto-remove \
        curl \
        unzip \
        jq \
        ; \
    apt-get purge --yes --auto-remove -o APT::AutoRemove::RecommendsImportant=false; \
    rm -rf /var/lib/apt/lists/*; \
    rm -rf /tmp/*; \
    find / -type f -name '*.pyc' -delete;

CMD ["phylum-ci"]
