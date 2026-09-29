# Container deployment and qualification

## Scope

This lane packages an already qualified msgloom wheel into a finite Docker
deployment. It does not add application commands, scheduler code, provider
access, or runtime credentials. The wheel is built from the source distribution
only by scripts/qualify_installed_wheel.py; the container qualifier calls that
helper instead of implementing a second package builder.

The deployment follows current Docker guidance to keep build contexts narrow,
run applications as a non-root USER, and pin base images by digest. The Python
base is the official python:VERSION-slim-bookworm image. The qualification
owner supplies one immutable sha256 digest for each of 3.12, 3.13, and 3.14.
Mutable tags are rejected. Relevant upstream references:

- [Docker build best practices](https://docs.docker.com/build/building/best-practices/)
- [Docker build context](https://docs.docker.com/build/concepts/context/)
- [Dockerfile reference](https://docs.docker.com/reference/dockerfile)
- [Official Python image](https://hub.docker.com/_/python)

## Build inputs and dependency ownership

The actual Docker build context is generated outside the checkout and contains
only four files: Dockerfile, its Dockerfile-specific ignore file, the exact
wheel renamed to msgloom.whl, and runtime-requirements.txt. No repository
directory, .env, host home, var, auth cache, source credential, test, or
research tree is admitted.

runtime-requirements.txt is a release artifact exported from the manager-owned
qualified uv.lock. Every installable line must be an exact name==version with
at least one sha256 hash. It must cover every direct Requires-Dist name in the
wheel. Editable installs and URL requirements are rejected. Prefect, FastMCP,
pytest, Ruff, setuptools, tox, and tox-uv are rejected from this deployment
lock. Lock production and dependency resolution remain manager-owned; this lane
deliberately does not edit uv.lock.

The image installs the hash-locked dependencies first and then the exact wheel
with --no-deps. The wheel hash is checked inside the image build. Runtime OS
packages are limited to bubblewrap, CA certificates, libgcc, and libstdc++.
There is no compiler, package build backend, Prefect, FastMCP, repository
checkout, or editable source installation in the final image. The SDK and its
bundled CLI arrive only through the declared claude-agent-sdk Python dependency.

## Runtime policy

The image runs as UID/GID 10001 and declares /var/lib/msgloom as external
persistent storage. Operators must mount a Docker-managed volume or another
qualified external store there with write permissions for 10001:10001. The
container root filesystem can remain read-only; qualification uses a bounded
/tmp tmpfs. Docker volumes are preferred to host-home bind mounts for durable
state:

- [Docker volumes](https://docs.docker.com/engine/storage/volumes/)
- [Docker container runtime](https://docs.docker.com/engine/containers/run/)

No host Docker socket, repository path, host home, or provider credential
directory is mounted. Qualification runs with --network none,
--security-opt no-new-privileges, --cap-drop ALL, and no --privileged. Normal
deployment may add only the network access required by the selected application
operation; parser isolation itself remains network-unshared.

Shutdown ownership remains with the application and its reviewed awaited
process boundaries. Docker sends SIGTERM. The AI and parser runtimes retain
their own bounded termination/reaping contracts; deployment does not introduce
a daemon or second lifecycle manager.

## Bubblewrap preflight and Docker policy

Both reviewed isolation mechanisms require /usr/bin/bwrap and unprivileged user
namespaces. Bubblewrap 0.12 removed setuid support, so setuid/setcap workarounds
are not an accepted deployment policy. The qualifier exercises:

1. a synthetic text parse through the production parser registry and
   parse_isolated;
2. an offline SDK import plus bundled CLI --version through RuntimeIsolation
   and build_sandbox_command.

The outer qualification container has networking disabled, so the AI check
cannot make a provider or paid model call. It supplies no credentials.

Docker's default seccomp profile restricts namespace creation while making
specific exceptions for user namespaces. Host kernels, Docker releases, and
LSM policy can still differ. Therefore the actual parser and AI probes are the
acceptance boundary; a successful bwrap --version alone is insufficient.

References:

- [Docker seccomp](https://docs.docker.com/engine/security/seccomp/)
- [docker container run](https://docs.docker.com/reference/cli/docker/container/run)
- [Bubblewrap README](https://github.com/containers/bubblewrap/blob/main/README.md)

If the default Docker profile blocks the reviewed bubblewrap commands, the
deployment remains failed. An operator may test an explicit per-container
seccomp JSON with --seccomp-profile; the qualifier records that boundary. The
profile must be reviewed as a narrow extension of the current Docker default
for the namespace syscalls actually required by these probes.
seccomp=unconfined, --privileged, --userns=host, setuid bubblewrap, host-global
Docker changes, and silent unsandboxed fallback are not accepted.

## Qualification

A release owner runs scripts/qualify_container_package.py with an output
directory outside the checkout, the existing isolated packaging environment,
the manager-owned runtime requirements lock, and exactly three ordered targets:

    --target 3.12=python:3.12-slim-bookworm@sha256:<qualified-manifest-digest>
    --target 3.13=python:3.13-slim-bookworm@sha256:<qualified-manifest-digest>
    --target 3.14=python:3.14-slim-bookworm@sha256:<qualified-manifest-digest>

The qualifier is intentionally serial. Each target records the supplied base
image reference, built image sha256 ID/digest, Python version, Docker-daemon-matched actual architecture, msgloom
version, wheel sha256, and bounded status/detail evidence. It verifies runtime
imports, native Excel/PDF/Word imports, package resources, SQLite reopen across
two containers sharing one invocation-owned named volume, and the two
bubblewrap preflights. Once the msgloom console entrypoint is integrated it also
requires installed msgloom --help to succeed with networking disabled.

Missing templates, prompts, migrations, or the not-yet-integrated msgloom
entrypoint are pending, never pass. --skip-isolation-preflight likewise records
both isolation gates as pending and makes the CLI return a nonzero pending
status. Any failed check returns failure. The report is
container-qualification.json.

Only the image and named volume created for the current target are removed.
The staged build context is removed after the run. The evidence report and
sdist/wheel qualification artifacts remain for review. The script never prunes
Docker, deletes unrelated containers/images/volumes, or changes daemon/kernel
settings.

## Current gate status

This worker does not run the three-image build matrix on the shared Raspberry
Pi. The full ARM64 matrix is pending manager execution after CLI/resource
integration and after the manager supplies the qualified hash-locked runtime
requirements plus current official-image digests. The synthetic focused tests
cover configuration validation, lifecycle ownership, deadlines, output
redaction, pending-state semantics, and exact evidence structure without large
image builds.
