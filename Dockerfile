FROM python:3.10-slim AS builder

RUN mkdir /src
COPY . /src/
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && apt update \
    # Install build tools to compile dependencies that don't have prebuilt wheels
    && apt install -y git build-essential \
    && cd /src \
    && pip install --user --no-cache-dir .

FROM python:3.10-slim

# copy only Python packages to limit the image size
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

RUN apt update \
    && apt install -y git \
    && apt clean \
    && rm -rf /var/lib/apt/lists/* \
    # TODO: Remove the specific phylum release here to get the `latest` release.
    #       It is required for now, until at least CLI v3.3.0 is released.
    # NOTE: The target option is required here b/c this image returns a self
    #       reported platform triple of `aarch64-unknown-linux-musl`, which is
    #       not supported. However, `x86_64-unknown-linux-musl` does appear to work.
    && phylum-init --phylum-release 3.3.0-rc1 --target x86_64-unknown-linux-musl

ENTRYPOINT ["/bin/bash", "-c"]
CMD ["phylum-ci"]
