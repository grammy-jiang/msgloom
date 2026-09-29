# syntax=docker/dockerfile:1

# Qualification supplies an official Python slim-bookworm image pinned to an
# immutable sha256 digest.
ARG BASE_IMAGE=invalid.invalid/msgloom/must-supply:3.13@sha256:0000000000000000000000000000000000000000000000000000000000000000
FROM $BASE_IMAGE

ARG WHEEL_SHA256
ARG WHEEL_FILENAME
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
COPY ${WHEEL_FILENAME} /tmp/${WHEEL_FILENAME}
RUN printf '%s  %s\n' "$WHEEL_SHA256" "/tmp/$WHEEL_FILENAME" | sha256sum -c - \
    && python -m pip install --no-cache-dir --only-binary=:all: --require-hashes \
        -r /tmp/runtime-requirements.txt \
    && python -m pip install --no-cache-dir --no-deps "/tmp/$WHEEL_FILENAME" \
    && rm -f /tmp/runtime-requirements.txt "/tmp/$WHEEL_FILENAME"

RUN groupadd --gid 10001 msgloom \
    && useradd --uid 10001 --gid 10001 --no-create-home \
        --home-dir /nonexistent --shell /usr/sbin/nologin msgloom \
    && install -d -o 10001 -g 10001 -m 0700 /var/lib/msgloom

VOLUME ["/var/lib/msgloom"]
WORKDIR /var/lib/msgloom
USER 10001:10001
STOPSIGNAL SIGTERM
