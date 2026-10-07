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

Release-input parsing is finite before semantic processing: the wheel is capped
at 512 MiB and 10,000 members, core METADATA at 4 MiB and 2,048 dependency
requirements, the runtime lock at 4 MiB, and explicit resource selections at
128 entries of at most 1,024 characters each. Oversized inputs fail closed
before full reads; the wheel digest remains streaming and bounded by the same
artifact limit.

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

Subprocess stdout/stderr is consumed through nonblocking descriptors and only
a finite tail is retained. Read work is capped per selector turn so continuous
output cannot starve lifetime checks. One absolute command deadline remains
authoritative until the leader has exited, inherited output reaches EOF, and
the invocation-owned process group is gone. An exited leader therefore cannot
turn an inherited-pipe descendant into an unbounded read or wait. Deadline
expiry records return code 124, sends SIGTERM to only that invocation-owned group,
uses a short bounded grace, then SIGKILLs remaining group members. Cancellation
uses the same idempotent cleanup path. Focused real-subprocess tests cover
closed stdout/stderr followed by sleep, an exited leader with an inherited
pipe, a SIGTERM-resistant descendant, noisy bounded output, and cancellation.

Every `docker run` has a unique invocation-owned `--name`. The runner
explicitly attempts `docker rm -f` for that exact name after the Docker CLI
returns, including successful or already-exited CLI cases; an already removed
`--rm` container is accepted as absent. A failed owned-container cleanup makes
that command check fail even when its primary command returned zero; primary
command evidence and cleanup evidence remain separately labeled. Target
cleanup attempts the invocation-owned volume and image independently. Cleanup
failures are bounded evidence and do not replace the original target
interruption. Absence-only cleanup remains idempotent.

`container-qualification.json` is atomically written immediately after the
output root is created, after release-input and host-preflight checkpoints,
before and after each target, and from finalization. Packaging, host-probe,
target, KeyboardInterrupt, and unexpected runtime failures therefore leave
truthful partial evidence. Unexecuted work remains `pending`; interrupted
work is `fail`; no incomplete work is promoted to `pass`. Context cleanup
and target image/volume cleanup errors are retained separately while the
original non-routine exception is re-raised.

Focused R3 validation used a temporary isolated environment, installed the
real sdist-built wheel there, and exercised both host production preflights:
the parser returned `parser-isolation-ok` and the offline SDK sandbox returned
`ai-isolation-ok`. The shared development environment was not modified. This
is host lifecycle evidence only; it is not the manager-owned ARM64 image
matrix, integrated entrypoint, digest, or runtime-lock acceptance gate.

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

## Required host resource enforcement

Qualification first reads the daemon's memory, swap, CPU quota, and PID-limit
capabilities. Each capability must be explicitly supported. A missing or false
value stops qualification before package or container work. Skipping the
isolation probe does not bypass this gate. Requested Docker flags alone do not
prove that the kernel enforces them.

On the manager's ARM64 host on September 29, 2026, Docker reported memory and
swap enforcement unavailable. The host kernel command line contained
`cgroup_disable=memory`, so the cgroup v2 hierarchy offered only the
`cpuset`, `cpu`, `io`, and `pids` controllers. Restricted-container
parser and offline AI probes also failed. Container acceptance remains pending
on a host that can enforce the required limits and run both isolated workers.
The manager did not change host kernel or daemon settings and did not weaken
the worker boundary.
