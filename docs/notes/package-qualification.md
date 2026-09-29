# Package qualification

## Scope

The repository builds the msgloom distribution with setuptools.build_meta.
The build requirement is exactly setuptools==84.0.0. Package discovery is
limited to the tested flat runtime roots msgloom, message_ingest, and
microsoft_graph. Tests, research, notes, worker state, credentials,
development archives, and repository-only configuration are not wheel
payloads.

The source distribution contains the build metadata plus runtime package
sources and declared package data needed to rebuild the wheel. MANIFEST.in
removes test and development trees that setuptools otherwise considers for an
sdist. Runtime package data is declared for future msgloom templates, prompts,
and migrations. No placeholder resource is added merely to satisfy packaging.

The Claude Agent SDK remains a declared runtime dependency. Its Python source
and bundled Claude Code executable are not copied into this distribution.
Prefect and FastMCP are not normal runtime requirements.

There is no package CLI entry point yet. Adding one before a concrete
application CLI exists would create a false installation contract. The manager
must wire and qualify the real entry point when that CLI lands. A required CLI
or resource can be passed to the qualification helper; absence then fails
visibly.

## Development and compatibility groups

The dev dependency group preserves the existing requirements and adds exact
pins for tox 4.64.4, tox-uv 1.36.0, pytest-xdist 3.8.0, and pytest-cov 7.1.0.
The separate compat-fastmcp4 group contains only fastmcp==4.0.10 and is
selected only by compatibility environments.

The normal tox environments are py312, py313, and py314. The FastMCP
compatibility environments are py312-fastmcp4, py313-fastmcp4, and
py314-fastmcp4. All use the tox-uv uv-venv-lock-runner, explicit dependency
groups, uv_sync_locked=true, and package=wheel. Missing interpreters fail
rather than skip.

Normal source-suite runs use at most four xdist workers, then run tests marked
exclusive_state separately with xdist disabled. Branch coverage is written
under each tox environment. The compatibility environments only import the
selected FastMCP release and exercise a synthetic shared typed/async contract;
they do not start a server, service, provider call, or model call.

The repository pytest configuration includes pythonpath=["."]. Therefore these
tox source-suite runs do not prove installed import provenance even though tox
installs a wheel. Installed-wheel qualification is deliberately a separate
check outside the checkout.

## Installed-wheel qualification

scripts/qualify_installed_wheel.py accepts only explicit source, output,
isolated-environment Python, and uv paths. It validates the expected build
backend before invoking build tooling. It uses argument lists rather than a
shell, runs uv builds offline, and rejects setup.py or setup.cfg from the
checkout. It stages only Git-tracked build inputs below the output root so
setuptools metadata generation never writes into the source checkout.

The helper performs this finite sequence:

1. Copy only tracked build inputs into a staging tree under the output root.
2. Build an sdist from that staging tree with the exact backend pin.
3. Inspect every sdist member for traversal, links, special files, and the
   rebuild allowlist, then normalize archive ordering and timestamps to the
   source revision for byte-reproducible qualification artifacts.
4. Build a wheel from that exact inspected and normalized sdist.
5. Inspect every wheel member and normal runtime metadata.
6. Install that exact wheel with --no-deps into the explicitly supplied
   isolated environment.
7. Run Python with -I from a directory outside the checkout, import all three
   runtime roots, and require their paths to live under the supplied
   environment.
8. Require FastMCP and Prefect to be absent in the normal environment and
   verify imports do not create files in the probe directory or background
   threads.
9. Check every explicitly required CLI and package resource. Missing required
   items fail the qualification.

The helper writes only below the supplied output root. It does not update the
lock, install into system Python, access provider credentials, make provider
calls, or perform paid/model acceptance.

A manager-owned invocation has this shape:

~~~console
python scripts/qualify_installed_wheel.py \
  --source-root . \
  --output-root /tmp/msgloom-package-qualification \
  --env-python /tmp/msgloom-wheel-env/bin/python \
  --uv "$(command -v uv)"
~~~

After the concrete CLI and runtime resources exist, add explicit gates such as
--require-cli NAME and --require-resource msgloom:PACKAGE_RELATIVE_PATH. Do
not omit those gates and then claim CLI/resource qualification.

## Commands and remaining gates

Focused lane checks do not resolve or rewrite uv.lock:

~~~console
.venv/bin/pytest -q tests/packaging/test_packaging_config.py \
  tests/packaging/test_qualification_helper.py
.venv/bin/ruff check scripts/qualify_installed_wheel.py tests/packaging
.venv/bin/ruff format --check scripts/qualify_installed_wheel.py \
  tests/packaging
pyright scripts/qualify_installed_wheel.py tests/packaging
git diff --check
~~~

After review, the manager owns lock resolution and the locked tox matrix:

~~~console
uv run tox run -e py312,py313,py314
uv run tox run -e py312-fastmcp4,py313-fastmcp4,py314-fastmcp4
~~~

Final qualification remains pending until the manager resolves the updated
lock and runs all required interpreters, serial/parallel comparison, semantic
fixtures, the actual installed-wheel check, and real container acceptance.
The future concrete CLI is also a pending package-installation gate. No result
from this lane should be described as those final gates having completed.
