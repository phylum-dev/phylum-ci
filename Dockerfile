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
##########################################################################################

FROM python:3.11-slim-bullseye AS builder

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

WORKDIR ${APP_PATH}

RUN set -eux; \
    python -m venv ${PHYLUM_VENV}; \
    ${PHYLUM_VENV_PIP} install --no-cache-dir --upgrade pip setuptools
RUN set -eux; \
    python -m venv ${POETRY_VENV}; \
    ${POETRY_VENV}/bin/pip install --no-cache-dir --upgrade pip setuptools; \
    ${POETRY_VENV}/bin/pip install --no-cache-dir poetry==1.6.1 poetry-plugin-export

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
    ${PHYLUM_VENV_PIP} install -r requirements.txt
COPY "${PKG_SRC:-.}" .
RUN ${PHYLUM_VENV_PIP} install --no-cache-dir ${PKG_NAME:-.}
RUN find ${PHYLUM_VENV} -type f -name '*.pyc' -delete

# Place in a directory included in the final layer and also known to be part of the $PATH
COPY entrypoint.sh ${PHYLUM_VENV}/bin/

FROM python:3.11-slim-bullseye

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

LABEL maintainer="Phylum, Inc. <engineering@phylum.io>"
LABEL org.opencontainers.image.source="https://github.com/phylum-dev/phylum-ci"

ENV PHYLUM_VENV="/opt/venv"
ENV PATH=${PHYLUM_VENV}/bin:$PATH
ENV PYTHONDONTWRITEBYTECODE=1

# Copy only Python packages to limit the image size
COPY --from=builder ${PHYLUM_VENV} ${PHYLUM_VENV}

RUN set -eux; \
    apt-get update; \
    apt-get upgrade --yes; \
    apt-get install --yes --no-install-recommends git; \
    chmod +x ${PHYLUM_VENV}/bin/entrypoint.sh; \
    phylum-init -vvv --phylum-release ${CLI_VER:-latest} --global-install; \
    apt-get purge --yes --auto-remove -o APT::AutoRemove::RecommendsImportant=false; \
    rm -rf /var/lib/apt/lists/*; \
    find / -type f -name '*.pyc' -delete

CMD ["phylum-ci"]
