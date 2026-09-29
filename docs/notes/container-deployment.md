# Container deployment and qualification

## Scope

This lane packages an already reviewed msgloom source tree through the existing
installed-wheel qualifier, then qualifies that exact wheel in finite Docker
containers. It adds no application command, scheduler, provider access, model
call, credential loading, or dependency lock ownership.

The build base must be exactly one of the official
`python:3.12-slim-bookworm`, `python:3.13-slim-bookworm`, and
`python:3.14-slim-bookworm` tags plus a caller-supplied immutable
`sha256:<64 lowercase hex>` manifest digest. The qualifier rejects patch tags,
other distributions, mutable references, malformed digests, and target
reordering. Release owners obtain current ARM64 digests from the official
Python image publication and record them as release inputs rather than storing
mutable values in this repository.

Upstream references used for this recipe are Docker's build best practices,
build context, container-run/resource-constraint, and seccomp documentation,
plus the official Python image page:

- <https://docs.docker.com/build/building/best-practices/>
- <https://docs.docker.com/build/concepts/context/>
- <https://docs.docker.com/engine/containers/run/>
- <https://docs.docker.com/engine/containers/resource_constraints/>
- <https://docs.docker.com/engine/security/seccomp/>
- <https://hub.docker.com/_/python>

## Exact package and build context

`scripts/qualify_container_package.py` supports direct invocation by absolute
or relative script path from an arbitrary working directory without
`PYTHONPATH`. It bootstraps only its own repository module path; runtime
qualification still uses the installed wheel.

The existing `scripts/qualify_installed_wheel.py` remains the sole source
distribution and wheel builder. The container qualifier validates the returned
wheel with `packaging.utils.parse_wheel_filename`, requires distribution name
`msgloom`, and requires the filename version to equal core metadata Version.
The msgloom wheel itself must be the expected universal py3-none-any artifact.
SHA-256 digest is calculated over those exact bytes.

The generated Docker context contains only:

1. `Dockerfile`;
2. `Dockerfile.dockerignore`;
3. `runtime-requirements.txt`; and
4. the exact wheel under its original valid wheel filename.

The staged ignore file adds an allow rule for that exact validated filename.
There is no wheel glob and no rename to `msgloom.whl`. Docker receives both
`WHEEL_FILENAME` and `WHEEL_SHA256`; the image checks the digest and installs
that filename with `pip --no-deps`.

No checkout, `.env`, host home, auth cache, tests, research tree, source
credential, or unrelated wheel enters the context.

## Runtime dependency lock

`runtime-requirements.txt` is manager-owned release evidence exported from the
qualified lock. This lane does not edit `uv.lock`.

Every non-comment logical line must be exactly `name==version` followed by one
or more lowercase SHA-256 `--hash` values. Versions must parse as packaging
versions and a package may occur only once. Pip directives, indexes, editable
requirements, local paths, URLs, direct references, unhashed lines, and the
development-only FastMCP/Prefect/pytest/Ruff/setuptools/tox packages are
rejected.

Requires-Dist markers are evaluated for the three qualified Linux CPython
ARM64 targets with no extras selected. Dependencies whose platform, Python, or
extra marker is irrelevant to every target are not incorrectly required in the
runtime lock. Every active direct dependency must be present.

## Explicit runtime resources and entrypoint

Resource qualification is release-input driven. The caller supplies each
actual required file as `--require-resource package:relative/path`; at least
one resource is required. The exact file must already be present in the wheel
and must also resolve through `importlib.resources` in the installed
container. The qualifier never creates empty resources.

When the report implementation is integrated, its known resources are:

    --require-resource msgloom:reporting/templates/report.html.j2
    --require-resource msgloom:reporting/templates/report.txt.j2

A candidate that does not yet contain those files remains unqualified rather
than inventing `msgloom/templates`, `prompts`, or `migrations` directories.

The installed `msgloom` console entrypoint is also an acceptance gate. If the
entrypoint is absent, `entrypoint-help` is explicitly `pending`. Once
present, the qualifier loads the installed entrypoint and executes `--help`
with process/network startup blocked. Pending is never reported as pass.

## Runtime confinement and budgets

Qualification containers run non-root as UID/GID 10001 with a Docker-managed
persistent volume at `/var/lib/msgloom`. The root filesystem is read-only and
`/tmp` is a 64 MiB `nosuid,nodev` tmpfs. Every probe uses:

- `--network none`;
- `--security-opt no-new-privileges`;
- `--cap-drop ALL`;
- `--memory 2g --memory-swap 2g`;
- `--cpus 2.0`; and
- `--pids-limit 256`.

No privileged mode, Docker socket, host-home mount, provider credential mount,
or `--userns=host` is accepted.

The Docker daemon itself must report native ARM64 (`aarch64` or `arm64`).
Each container must report the same normalized architecture and the requested
Python minor version.

## Parser and offline SDK preflights

After the installed-wheel helper succeeds, the qualifier runs host preflights
using that qualified environment. The parser probe calls the reviewed
`parse_isolated` API through `PRODUCTION_REGISTRY` with the accepted
`mime-html-v1` profile and synthetic text bytes. The AI probe imports the
installed SDK, constructs the reviewed `RuntimeIsolation` and
`build_sandbox_command`, then runs only the bundled CLI `--version` offline.
Host AI state is under the qualification output root.

The same probes run again inside each image. The outer container has no
network and receives no model/provider credentials, so the AI probe cannot
perform a paid or live provider call.

`--skip-isolation-preflight` records both host and container isolation checks
as `pending` and causes the overall CLI result to remain non-successful.

## Seccomp policy

With no override, Docker's built-in default seccomp policy applies. Docker
documents that default as an allowlist with `SCMP_ACT_ERRNO` as its default
action and warns against `seccomp=unconfined`.

A custom `--seccomp-profile` must be a non-symlink regular UTF-8 JSON file no
larger than 1 MiB. This qualifier accepts only a profile whose
`defaultAction` is `SCMP_ACT_ERRNO` and whose `syscalls` list is non-empty.
This intentionally rejects `SCMP_ACT_ALLOW`, logging-only defaults, malformed
JSON, empty pseudo-profiles, and `unconfined` equivalents. A custom profile is
release-review evidence for a narrow extension needed by the real bubblewrap
probes; it is not a general escape hatch.

## Bounded lifecycle and evidence

Subprocess stdout/stderr is consumed incrementally and only a finite tail is
retained. A timeout records return code 124 plus bounded partial output. Host
commands run in invocation-owned process groups that are terminated and reaped
on timeout or cancellation.

Every `docker run` has a unique invocation-owned `--name`. On timeout or
failure the runner explicitly removes exactly that container after terminating
the Docker CLI. Successful `--rm` runs self-remove. Target cleanup attempts
the invocation-owned volume and image independently; one cleanup error cannot
skip the other or replace the original target failure.

`container-qualification.json` is written after release execution begins,
after every completed target, and at finalization. Packaging/setup subprocess
failure therefore still leaves bounded machine-readable failure evidence.
Target command failures and timeouts produce target checks instead of aborting
the remaining matrix. No unexecuted target is represented as passed.

## Qualification invocation

A release owner supplies an output directory outside the checkout, the
isolated packaging environment, manager-owned runtime lock, explicit resources,
and exactly three ordered targets:

    env -u PYTHONPATH .venv/bin/python scripts/qualify_container_package.py \
      --source-root . \
      --output-root /qualified/msgloom-container \
      --env-python /qualified/package-env/bin/python \
      --uv /qualified/tools/uv \
      --runtime-lock /qualified/runtime-requirements.txt \
      --require-resource msgloom:reporting/templates/report.html.j2 \
      --require-resource msgloom:reporting/templates/report.txt.j2 \
      --target 3.12=python:3.12-slim-bookworm@sha256:<digest> \
      --target 3.13=python:3.13-slim-bookworm@sha256:<digest> \
      --target 3.14=python:3.14-slim-bookworm@sha256:<digest>

The full three-image matrix remains manager-owned acceptance work. This worker
does not claim it passed. Until the integrated candidate contains the real
report resources and console entrypoint and the manager supplies the qualified
runtime lock/current official digests, those release gates remain pending.
