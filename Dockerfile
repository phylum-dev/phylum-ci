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
#   * There is only one wheel built and put in the `dist` directory
#
# To make use of this feature, build the image WITH build args specified:
#
# $ export PKG_SRC=dist/phylum-*.whl
# $ export PKG_NAME=phylum-*.whl
# $ docker build --tag phylum-ci --build-arg PKG_SRC --build-arg PKG_NAME .
#
# To make use of BuildKit's inline layer caching feature, add the `BUILDKIT_INLINE_CACHE`
# build argument to any instance of building an image. Then, that image can be used
# locally or remotely (if it was pushed to a repository) to warm the build cache by using
# the `--cache-from` argument:
#
# $ docker build --tag phylumio/phylum-ci:cache --build-arg BUILDKIT_INLINE_CACHE=1 .
# $ docker push phylumio/phylum-ci:cache && docker image rm phylumio/phylum-ci:cache
# $ docker build --tag phylumio/phylum-ci:faster --cache-from phylumio/phylum-ci:cache .
##########################################################################################

# Explicitly specify a platform that is supported by `phylum-init`
FROM --platform=linux/amd64 python:3.10-alpine AS builder

# PKG_SRC is the path to a built distribution/wheel and PKG_NAME is the name of the built
# distribution/wheel. Both can optionally be specified in glob form. When not defined,
# the values will default to the root of the package (i.e., `pyproject.toml` path).
ARG PKG_SRC
ARG PKG_NAME

WORKDIR /app

ENV PIP_NO_COMPILE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build tools to compile dependencies that don't have prebuilt wheels
RUN apk add --update --no-cache build-base git poetry libffi-dev
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy the bare minimum needed for specifying dependencies.
# This will enable better layer caching and faster builds when iterating locally.
# `--without-hashes` is used to ensure the `pip` cache mount is used for packages that
# would otherwise only match the sdist and therefore have to be built for every run.
# References:
#   * https://pythonspeed.com/articles/pipenv-docker/
#   * https://hub.docker.com/r/docker/dockerfile
COPY pyproject.toml poetry.lock ./
RUN poetry export --without-hashes --format requirements.txt --output requirements.txt

# Cache the pip installed dependencies
# NOTE: This `--mount` feature requires BUILDKIT to be used
RUN --mount=type=cache,id=pip,target=/root/.cache/pip \
    set -eux; \
    pip cache info; \
    pip cache list; \
    pip install --user -r requirements.txt
COPY "${PKG_SRC:-.}" .
RUN pip install --user --no-cache-dir ${PKG_NAME:-.}
RUN find /root/.local -type f -name '*.pyc' -delete

# Explicitly specify a platform that is supported by `phylum-init`
FROM --platform=linux/amd64 python:3.10-alpine

LABEL maintainer="Phylum, Inc. <engineering@phylum.io>"

# Copy only Python packages to limit the image size
COPY --from=builder /root/.local /root/.local

ENV PATH=/root/.local/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1

RUN set -eux; \
    apk add --update --no-cache git; \
    phylum-init; \
    find / -type f -name '*.pyc' -delete

CMD ["phylum-ci"]
