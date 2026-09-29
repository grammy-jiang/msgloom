# syntax=docker/dockerfile:1

# BASE_IMAGE is replaced by qualification with an official Python image
# pinned to a sha256 digest.
ARG BASE_IMAGE=invalid.invalid/msgloom/must-supply:3.13@sha256:0000000000000000000000000000000000000000000000000000000000000000
FROM $BASE_IMAGE

ARG WHEEL_SHA256
ENV HOME=/nonexistent \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONNOUSERSITE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bubblewrap \
        ca-certificates \
        libgcc-s1 \
        libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

COPY runtime-requirements.txt /tmp/runtime-requirements.txt
COPY msgloom.whl /tmp/msgloom.whl
RUN printf '%s  %s\n' "$WHEEL_SHA256" /tmp/msgloom.whl | sha256sum -c - \
    && python -m pip install --no-cache-dir --only-binary=:all: --require-hashes \
        -r /tmp/runtime-requirements.txt \
    && python -m pip install --no-cache-dir --no-deps /tmp/msgloom.whl \
    && rm -f /tmp/runtime-requirements.txt /tmp/msgloom.whl

RUN groupadd --gid 10001 msgloom \
    && useradd --uid 10001 --gid 10001 --no-create-home \
        --home-dir /nonexistent --shell /usr/sbin/nologin msgloom \
    && install -d -o 10001 -g 10001 -m 0700 /var/lib/msgloom

VOLUME ["/var/lib/msgloom"]
WORKDIR /var/lib/msgloom
USER 10001:10001
STOPSIGNAL SIGTERM
