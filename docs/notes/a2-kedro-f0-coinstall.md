# A2 Kedro F0-05b: co-install of msgloom and Kedro 1.7.0 on aarch64

Date: 2026-10-24. Host: Raspberry Pi 5, Linux aarch64 (glibc), uv 0.12.24.
Task: F0-05b. Branch `research/a2-kedro-f0-20261024`, base `895fc40`.

## Full-suite results (final)

The full normal pytest set finished on all three Python versions.

| Python | Exit code | Result |
| --- | --- | --- |
| 3.12.14 | 0 | 4705 passed, 42 min 17 s |
| 3.13.16 | 0 | 4705 passed, 24 min 9 s |
| 3.14.7 | 1 | 1 failed, 4704 passed, 43 min 0 s |

The 3.14.7 failure is
`tests/container_deployment/test_container_qualification.py::test_real_local_container_timeout_is_removed_if_image_present`.
The 3.12.14 and 3.14.7 runs ran at the same time. That test uses the fixed
Docker container name `msgloom-qual-pytest-timeout`. A name collision between
the two runs is a likely cause. It is not proven. The same test passed alone
on 3.14.7 in two runs (exit 0 each). This failure is an open item for the
security owner. Logs: `/tmp/f0-scratch-20261024/f05b/logs/`
(`pytest-normal-cand-3.12.out`, `pytest-normal-cand-3.14.out`,
`exitcodes.txt`).

## Result

msgloom and Kedro 1.7.0 co-install on Python 3.12.14, 3.13.16 and 3.14.7
on this host. Every install, `uv pip check`, import check and Pyright run
exited 0. No installed package differs from the locked version in the
production lock. No STOP condition was found.

| Check | 3.12.14 | 3.13.16 | 3.14.7 |
| --- | --- | --- | --- |
| `uv sync --frozen --no-build` | 0 | 0 | 0 |
| `uv pip check` | 0 | 0 | 0 |
| Imports (`kedro`, `message_ingest`, others) | 0 | 0 | 0 |
| Locked versions kept (script) | 0 | 0 | 0 |
| Pyright 1.1.413, repo config | 0 | 0 | 0 |
| Pytest, normal marker set | 0 (4705 passed) | 0 (4705 passed) | 1 (1 failed, 4704 passed) |
| Pytest, 12-directory subset | 0 (327 passed) | not run | 0 (327 passed) |

Not run on any version: the `exclusive_state` tests, the `fastmcp_compat`
tests and the `linux_cgroup_v2` tests. See "Tests that did not run".

The installs use the scratch candidate lock from F0-05a. They prove that
the 20 added packages install and import together with the locked set. They
do not approve the dependency change. They do not prove that any Kedro
feature is safe for msgloom.

## Method

All work ran under `/tmp/f0-scratch-20261024/f05b/`. No repository file
changed. The production venv and the main checkout were not touched.

1. Source: `git archive HEAD` from the F0 worktree (`895fc40`), copied once
   per Python version.
2. Lock: the F0-05a scratch candidate lock (`cand/uv.lock`, SHA-256
   `be6dbacb03873335654c32b4a3434aee944402554d1cd241eab5edf902b794c1`),
   with `kedro==1.7.0` and the scratch `pypydispatcher` exclusion.
3. Install: `UV_PROJECT_ENVIRONMENT=<copy>/.venv uv sync --frozen
   --no-build --python <series>`. The default groups install, which means
   the runtime set plus the `dev` group. The `compat-fastmcp4` group is not
   installed. msgloom installs as an editable project.
4. Interpreters are the uv-managed builds, selected by series. The system
   Python 3.13.5 was not used.
5. Telemetry guard: all test and import runs set `DO_NOT_TRACK=1` and
   `KEDRO_DISABLE_TELEMETRY=1`. Telemetry behavior is in F0-04.

Interpreters used (`python -VV`): CPython 3.12.14, 3.13.16 and 3.14.7, all
Clang 22.1.3 builds from uv. All three were already installed. No download
of an interpreter was needed.

## Commands and raw exit codes

Values below come from `/tmp/f0-scratch-20261024/f05b/logs/exitcodes.txt`.

| Step | Command (abridged) | 3.12 | 3.13 | 3.14 |
| --- | --- | --- | --- | --- |
| Install | `uv sync --frozen --no-build --python <v>` | 0 | 0 | 0 |
| Pip check | `uv pip check --python <venv>/bin/python` | 0 | 0 | 0 |
| Freeze | `uv pip freeze --python <venv>/bin/python` | 0 | 0 | 0 |
| Sync dry run | `uv sync --frozen --no-build --dry-run` | 0 | 0 | 0 |
| Imports | `<venv>/bin/python -I imports.py` | 0 | 0 | 0 |
| Version compare | `python -I cmp_freeze.py base/uv.lock freeze.txt` | 0 | 0 | 0 |
| Pyright | `pyright --pythonpath <venv>/bin/python` | 0 | 0 | 0 |

Pip check output on each version: `All installed packages are compatible`
(135, 135 and 134 entries checked; the count includes the msgloom project).
The sync dry run reports `Would make no changes` (3.13 shown; exit 0 on all).

## Installed set versus the production lock

`cmp_freeze.py` reads `uv pip freeze` and the production (base) `uv.lock`.
It exits 1 if any installed package has a version that the base lock does
not list.

| Python | Installed third-party packages | Also in base lock | Not in base lock | Version mismatches |
| --- | --- | --- | --- | --- |
| 3.12.14 | 134 | 114 | 20 | 0 |
| 3.13.16 | 134 | 114 | 20 | 0 |
| 3.14.7 | 133 | 113 | 20 | 0 |

The 20 packages not in the base lock are exactly the 20 added packages that
F0-05a lists. `backports-zstd` installs on 3.12 and 3.13 and not on 3.14,
which explains the difference of one. Step 3 of the task (stop if an install
upgrades a locked package) did not trigger. No existing package was
upgraded, downgraded or removed on any version.

## Import checks

The script imported these modules under `python -I`, with a count of
failures: `kedro`, `kedro.framework.cli`, `kedro.io`, `kedro.pipeline`,
`kedro.runner`, `kedro_telemetry`, `msgloom`, `msgloom.cli`,
`message_ingest`, `message_ingest.settings`, `microsoft_graph`, `scrapy`,
`twisted`, `pydantic`, `sqlalchemy`, `lxml`, `jinja2`. All imported on all
three versions (0 failures). Versions seen: kedro 1.7.0, kedro-telemetry
0.9.0, Scrapy 2.19.0, Twisted 26.4.0, Pydantic 2.14.1, SQLAlchemy 2.0.54,
lxml 6.1.3, Jinja2 3.1.6.

Side effect: importing `kedro.framework.cli` logs one INFO line
("Using ... rich_logging.yml as logging configuration") at import time. The
import therefore configures logging in the process. A msgloom module that
imports Kedro CLI code at import time can change logging settings.

## Pyright

Pyright 1.1.413 is a user-level tool in `~/.local/bin`. The project does not
pin it. Each run used the repository `[tool.pyright]` settings
(`include = msgloom, message_ingest, microsoft_graph, tests`, standard mode)
with `--pythonpath` set to the per-version venv. Result on all three
versions: `0 errors, 0 warnings, 0 informations`. Run time was about 2.6 to
3.0 minutes each while other jobs ran.

Limit: no msgloom file imports Kedro today. A clean result means that the
existing code type-checks with the new packages installed. It does not test
future Kedro code.

Controls:

- Negative control: a scratch file with `x: int = "a"` and `import kedro`
  gave 1 error (the assignment) and exit 1. Pyright resolved the `kedro`
  import with the 3.13 venv.
- Pip check negative control: a separate scratch venv with the Kedro wheel
  installed `--no-deps` and `click==7.1.2` gave `Found 16 incompatibilities`
  and exit 1. The check can fail.

## Tests

The normal marker set is the one in the `[tool.tox.env_run_base]` table:
`-m "not exclusive_state and not fastmcp_compat and not linux_cgroup_v2"`.

| Run | Python | Command (abridged) | Exit code | Result |
| --- | --- | --- | --- | --- |
| Full normal set | 3.13.16 | `pytest -q -n 4 -m <normal>` | 0 | 4705 passed, 8 warnings, 24 min 8 s |
| Full normal set | 3.12.14 | `pytest -q -n 2 -m <normal>` | 0 | 4705 passed, 4 warnings, 42 min 17 s |
| Full normal set | 3.14.7 | `pytest -q -n 2 -m <normal>` | 1 | 1 failed, 4704 passed, 4 warnings, 43 min 0 s (see "Full-suite results") |
| 12-directory subset | 3.12.14 | `pytest -q -n 4 -m <normal> tests/<dirs>` | 0 | 327 passed, 56 s |
| 12-directory subset | 3.14.7 | same | 0 | 327 passed, 61 s |

The subset directories are `packaging`, `quality`, `configuration`,
`application_cli`, `container_deployment`, `persistence`,
`persistence_fences`, `persistence_reconciliation`, `parser_isolation`,
`handoff_qualification`, `phase1_e2e` and `delivery`. The 8 warnings in the
3.13 run are `PytestAssertRewriteWarning` messages for `tests.teams_support`
and `teams_support`. They do not involve Kedro or the added packages.

The 3.13 full run overlapped with three Pyright runs. Run times are not a
benchmark.

### Tests that did not run

- `exclusive_state` tests: not run on any version. They need `-n 0` and
  were out of the time budget.
- `fastmcp_compat` tests: not run. They need the `compat-fastmcp4` group,
  which these installs did not include.
- `linux_cgroup_v2` tests: not run. They need a delegated cgroup v2 scope.
  They are excluded by the same marker expression as in the project's tox
  configuration. This is not a statement that they pass. Their CI gate
  stays required.
- No test touches Kedro. All pass or fail results show that adding Kedro
  does not break the existing tests. They do not test Kedro integration.

## Limits

- Scratch lock: the install used the `pypydispatcher` exclusion from
  F0-05a. That package is PyPy-only, so no CPython install is affected.
- uv 0.12.24 ran here. CI pins uv 0.13.5. The locked dev group also
  installs a `uv==0.13.5` package into each venv. That package was not used
  to install. The CI workflow was not run.
- Only aarch64 glibc was tested. No x86_64 or macOS run exists.
- `--no-build` blocked all source builds. Every package installed from a
  wheel. The sdist of Kedro was not built.
- Package versions and hashes apply to the PyPI index on 2026-10-24.

## Status / Open items

- F0-05b: DONE with one open failure. Install, `uv pip check`, imports,
  locked-version compare and Pyright are DONE on 3.12, 3.13 and 3.14. The
  full pytest run passed on 3.12 and 3.13. It had 1 failure on 3.14. See
  "Full-suite results (final)".
- Open: the `exclusive_state`, `fastmcp_compat` and `linux_cgroup_v2` test
  sets were not run with Kedro installed.
- Open: Kedro import side effect on logging (see "Import checks").
- Open: no Kedro-specific test exists yet. Integration tests belong to a
  later task.
