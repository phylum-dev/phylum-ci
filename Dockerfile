# This Dockerfile can be used to build the project's package within the image it creates.
# To do so, simply build the image WITHOUT any build args specified (e.g., `--build-arg`):
#
# $ docker build --tag phylumio/phylum-ci .
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
# $ docker build --tag phylumio/phylum-ci --build-arg PKG_SRC --build-arg PKG_NAME .

FROM python:3.10-slim AS builder

# PKG_SRC is the path to a built distribution/wheel and PKG_NAME is the name of the built
# distribution/wheel. Both can optionally be specified in glob form. When not defined,
# the values will default to the root of the package (i.e., `pyproject.toml` path).
ARG PKG_SRC
ARG PKG_NAME
WORKDIR /app
COPY "${PKG_SRC:-.}" .
RUN apt update \
    && apt upgrade -y \
    # Install build tools to compile dependencies that don't have prebuilt wheels
    && apt install -y git build-essential \
    && pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --user --no-cache-dir ${PKG_NAME:-.}

FROM python:3.10-slim
LABEL maintainer="Phylum, Inc. <engineering@phylum.io>"

# copy only Python packages to limit the image size
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

RUN apt update \
    && apt upgrade -y \
    && apt install -y git \
    && apt clean \
    && apt purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
    && rm -rf /var/lib/apt/lists /var/cache/apt/archives \
    # NOTE: The target option is required here b/c this image returns a self
    #       reported platform triple of `aarch64-unknown-linux-musl`, which is
    #       not supported. However, `x86_64-unknown-linux-musl` does appear to work.
    && phylum-init --target x86_64-unknown-linux-musl

ENTRYPOINT ["/bin/bash", "-c"]
CMD ["phylum-ci"]
