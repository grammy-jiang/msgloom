# A2 Kedro F0-05c: types, tests and build with Kedro 1.7.0 installed

Date: 2026-10-24. Host: Raspberry Pi 5, Linux aarch64 (glibc), uv 0.12.24.
Task: F0-05c. Branch `research/a2-kedro-f0-20261024`, base `895fc40`.
Candidate: `kedro` 1.7.0 (wheel SHA-256
`488701a27c7d595b62a611cb23596953a9929fe5cc42a376c28abe26654c2438`).

## Full-suite results (final)

The full normal pytest set finished on all three Python versions.

| Python | Exit code | Result |
| --- | --- | --- |
| 3.12.14 | 0 | 4705 passed, 42 min 17 s |
| 3.13.16 | 0 | 4705 passed, 24 min 9 s |
| 3.14.7 | 1 | 1 failed, 4704 passed, 43 min 0 s |

The 3.14.7 failure is
`tests/container_deployment/test_container_qualification.py::test_real_local_container_timeout_is_removed_if_image_present`.
The 3.12.14 and 3.14.7 runs ran at the same time. Both started at about
09:14 local time. They ended at 09:56:39 and 09:57:22 (file times of the
`.time` logs). That test uses the fixed Docker container name
`msgloom-qual-pytest-timeout`. A name collision between the two runs is a
likely cause. It is not proven. Other explanations are not excluded: host
load (the two runs used `-n 2` each, so four workers on four cores), a delay
in Docker `--rm` removal after the client process is killed, or a defect in
the test. Supporting facts: the 12-directory subset, which includes
`tests/container_deployment`, passed on 3.14.7 earlier (exit 0, 327 passed,
`pytest-subset-cand-3.14.out`). The same test passed alone on 3.14.7 in two
runs, with raw logs `pytest-solo-container-3.14-run1.out` and
`pytest-solo-container-3.14-run2.out` (exit 0 each). A clean sequential full
rerun on 3.14.7 was not made. This failure is an open item for the security
owner. Logs: `/tmp/f0-scratch-20261024/f05b/logs/`
(`pytest-normal-cand-3.12.out`, `pytest-normal-cand-3.14.out`,
`exitcodes.txt`).

## Result

Pyright, the source-boundary tests and the package build all pass with
Kedro 1.7.0 installed. Kedro ships a `py.typed` marker. Pyright uses the
inline types of Kedro and finds no problem in the msgloom code base. No
STOP condition was found. This note does not approve any dependency change.

| Question | Answer |
| --- | --- |
| (a) Does Pyright 1.1.413 pass with the repository config? | Yes. 0 errors, 0 warnings on 1064 files, with and without Kedro (Python 3.13). F0-05b: 0 errors on 3.12, 3.13 and 3.14. |
| (a) Does the `py.typed` marker of Kedro help or break Pyright? | It helps. Kedro types resolve (`Node`, `Pipeline`, `DataCatalog`) and wrong calls produce errors. It breaks nothing today, because no msgloom file imports Kedro. Type completeness is 84.7%, so some Kedro types are partly unknown. |
| (b) What are the results of the full pytest runs on 3.12 and 3.14? | 3.12.14: exit 0, 4705 passed. 3.14.7: exit 1, 1 failed, 4704 passed. See "Full-suite results (final)" and part (b). |
| (c) Do the wheel and sdist build reproducibly with Kedro present? | Yes. Two builds per Python 3.12, 3.13 and 3.14 gave one wheel hash and one sdist hash. |
| (c) Do the source-boundary tests still pass? | Yes. 34 tests ran and passed; 24 `linux_cgroup_v2` tests in the same files did not run. |
| Did installing Kedro change a locked package version? | No. 134 installed packages, 20 not in the base lock, 0 version mismatches. |

Scope limit: the checks ran on Linux aarch64 only. No test touches Kedro.

## Method

All work ran under `/tmp/f0-scratch-20261024/f05c/`. No repository file
changed. The production venv and the main checkout were not touched. The
F0-05b directories were read and not modified.

1. `git clone --no-hardlinks` of the F0 worktree (`895fc40`) gave
   `clone-base` and a copy `clone-cand`.
2. `clone-base` keeps the production `pyproject.toml` and `uv.lock`
   (lock SHA-256
   `5db0bbf6f7ec6b787f892c85477d90a5a22abf343010cc84e6843828168ae02d`).
3. `clone-cand` holds the F0-05a scratch candidate files (lock SHA-256
   `be6dbacb03873335654c32b4a3434aee944402554d1cd241eab5edf902b794c1`).
   The only changes are `"kedro==1.7.0"` in the dependencies and the
   scratch `exclude-dependencies = ["pypydispatcher"]` table. The clone
   has uncommitted changes. No commit was made.
4. Each clone got its own `.venv` with `uv sync --frozen --no-build
   --python 3.13`. The default groups install, so the runtime set and the
   `dev` group are present. Both commands exit 0.
5. Telemetry guard: every command set `DO_NOT_TRACK=1` and
   `KEDRO_DISABLE_TELEMETRY=1`.

Locked-version check on `clone-cand`: `uv pip freeze` and
`cmp_freeze.py` (from F0-05b) against the production lock. Result: 134
installed, 114 in the base lock, 20 not in it, 0 mismatches (exit 0).
`uv pip check` exit 0. This repeats the F0-05b result on a second,
independent venv. The STOP rule for a changed locked version did not
trigger.

## (a) Pyright

Pyright 1.1.413 is the PyPI wrapper in `~/.local/bin/pyright`. CI runs
`npx pyright@1.1.413`. The version number is the same. The repository
`[tool.pyright]` table applies (`typeCheckingMode = "standard"`).

| Run | Command (abridged) | Exit code | Files | Errors | Warnings |
| --- | --- | --- | --- | --- | --- |
| Base, Python 3.13 | `pyright --pythonpath .venv/bin/python microsoft_graph message_ingest msgloom tests` | 0 | 1064 | 0 | 0 |
| Candidate, Python 3.13 | same command in `clone-cand` | 0 | 1064 | 0 | 0 |
| Candidate, 3.12 / 3.13 / 3.14 | F0-05b, repository config | 0 / 0 / 0 | not recorded | 0 | 0 |

The base and candidate runs analyze the same number of files. The
diagnostic lists are both empty. Run times were 393 s and 247 s under
other load. They are not a benchmark.

The command lists the same four directories as the CI step, which includes
`message_ingest/` and `tests/`.

### Kedro type information

`kedro/py.typed` is in the wheel. Pyright therefore treats the inline
annotations in Kedro as the type source. Nine of the 20 new packages ship a
`py.typed` marker. One more package, `parse`, ships a `.pyi` file.

| Package | `py.typed` | `.pyi` files |
| --- | --- | --- |
| `arrow`, `binaryornot`, `build`, `dynaconf`, `gitpython`, `kedro`, `omegaconf`, `pyproject-hooks`, `python-slugify` | yes | 0 |
| `parse` | no | 1 |
| `appdirs`, `cookiecutter`, `fsspec`, `gitdb`, `kedro-telemetry`, `python-dateutil`, `six`, `smmap`, `text-unidecode`, `tzdata` | no | 0 |

Probe files in `typeprobe/` ran with the Python of `clone-cand` and
`typeCheckingMode = "standard"`.

| Probe | Exit code | Result |
| --- | --- | --- |
| `ok_usage.py`: `node`, `Pipeline`, `DataCatalog`, `MemoryDataset` | 0 | `Node`, `Pipeline`, `list[Node]` and `DataCatalog` resolve. `catalog.load("a")` is `Any`. |
| `bad_usage.py`: four wrong calls | 1 | 4 errors: `inputs=1`, `Pipeline(5)`, `DataCatalog(datasets=5)`, unknown attribute. |
| `untyped_usage.py`: `cookiecutter`, `dateutil`, `six` | 0 | No error. `dateutil` and `six` types come from the stubs that Pyright bundles. `cookiecutter` signatures resolve from source. |
| Repository config, `bad_usage.py` copied to `tests/` | 1 | Same 4 errors. The repository config catches Kedro misuse in `tests/`. |
| Repository config, `ok_usage.py` copied to `message_ingest/` | 0 | Same types as above. Copies were removed from the clone. |

These probes act as negative controls. The tool can fail on Kedro code, so
the clean result on the real tree is meaningful.

Completeness: `pyright --verifytypes kedro --ignoreexternal` reported 945
exported symbols, 39 referenced but not exported, and a type completeness
score of 84.7%. It listed 145 error lines. The most frequent classes:

| Count | Message class |
| --- | --- |
| 35 | Type is missing a type annotation and could be inferred differently by type checkers |
| 14 | Ambiguous base class override |
| 12 | Return type is partially unknown |
| 10 | Could not resolve module under `kedro.templates...` (cookiecutter template folders) |
| 9 | Type of parameter `catalog` is partially unknown |

Effects for msgloom:

- The standard mode of the repository config does not report problems
  inside Kedro. It reports only misuse at the call site.
- A partly unknown Kedro type (for example `DataCatalog.load` returns
  `Any`, and `datasets` is `dict[str, AbstractDataset[Unknown, Unknown]]`)
  passes in standard mode. A change to `strict` mode would report these as
  `reportUnknown*` errors in code that calls Kedro. The repository does
  not use strict mode.
- `--verifytypes` found the package only when `PYTHONPATH` pointed to the
  venv `site-packages`. Two earlier attempts with `--pythonpath` returned
  "No py.typed file found" and a score of 0%. Those two runs are a tool
  lookup failure, not a Kedro result. All three attempts exited 1. The
  third run exited 1 because it listed 145 error lines.
- The F0-05b limit still applies. No msgloom file imports Kedro. A clean
  result shows that the existing code type-checks with Kedro installed. It
  does not test future Kedro code beyond the probes above.

## (b) Full pytest runs

The co-install note (F0-05b) now holds the final results. The runs used
`pytest -q -n 2 -m "not exclusive_state and not fastmcp_compat and not
linux_cgroup_v2" -p no:cacheprovider` with a 3300 s timeout in
`/tmp/f0-scratch-20261024/f05b/cand-3.12` and `.../cand-3.14`. The logs are
in `/tmp/f0-scratch-20261024/f05b/logs/`.

| Python | Exit code | Result |
| --- | --- | --- |
| 3.12.14 | 0 | 4705 passed |
| 3.13.16 | 0 | 4705 passed |
| 3.14.7 | 1 | 1 failed, 4704 passed |

The 3.14.7 failure is
`test_real_local_container_timeout_is_removed_if_image_present`. The test
uses a fixed Docker container name, and the 3.12 and 3.14 runs overlapped in
time. A collision is a likely cause but is not proven. The test passed alone
on 3.14.7 in two runs. It does not exercise Kedro.

Evidence that applies to every Python version already:

| Evidence | Python | Result |
| --- | --- | --- |
| Full normal set, F0-05b | 3.13.16 | exit 0, 4705 passed, 8 warnings, 24 min 8 s |
| 12-directory subset, F0-05b | 3.12.14 | exit 0, 327 passed |
| 12-directory subset, F0-05b | 3.14.7 | exit 0, 327 passed |
| Source-boundary set, this task, candidate | 3.13.16 | exit 0, 34 passed |
| Source-boundary set, this task, base | 3.13.16 | exit 0, 33 passed |

The co-install note states the final results of all three full runs.

Tests that did not run in any F0 run:

| Test set | Status | Reason |
| --- | --- | --- |
| `linux_cgroup_v2` | NOT RUN | Needs a delegated cgroup v2 scope. The CI gate `linux_safety` stays required. This is not a pass. |
| `fastmcp_compat` | NOT RUN | Needs the `compat-fastmcp4` group, which these installs did not include. |
| `exclusive_state` (full tree) | NOT RUN | Needs `-n 0` and a long run time. The one exclusive test in the source-boundary files did run and pass. |

## (c) Build reproducibility and source boundary

The script `scripts/qualify_installed_wheel.py` of the repository ran
unchanged from each clone. It stages the tracked sources, builds the sdist
with `uv build --offline`, normalizes the sdist, builds the wheel from the
sdist, inspects both, installs the wheel into a separate venv, and probes
imports and the `msgloom` entry point. `SOURCE_DATE_EPOCH` is the commit
timestamp `1792727204`.

Each environment holds the runtime requirements (`uv export --frozen
--no-dev --no-emit-project`, installed with `uv pip sync --no-build`) and
no msgloom source. For the candidate, Kedro 1.7.0 and its 20 packages are
in that environment. For the base, Kedro is absent.

| Run | Env Python | Exit code | sdist SHA-256 (first 16) | wheel SHA-256 (first 16) |
| --- | --- | --- | --- | --- |
| Candidate r1 / r2 | 3.12 | 0 / 0 | `fd6a6ed5ad20c28a` | `d3508b369fd167c0` |
| Candidate r1 / r2 | 3.13 | 0 / 0 | `fd6a6ed5ad20c28a` | `d3508b369fd167c0` |
| Candidate r1 / r2 | 3.14 | 0 / 0 | `fd6a6ed5ad20c28a` | `d3508b369fd167c0` |
| Base r1 / r2 | 3.13 | 0 / 0 | `04780b0749865982` | `09e795e8553d7083` |

Full hashes (Python 3.13 runs):

| Artifact | SHA-256 | Size (bytes) |
| --- | --- | --- |
| Candidate sdist | `fd6a6ed5ad20c28a68697063a0faa5212d6c35a5c4b016cb791d316d542e8eb5` | 602001 |
| Candidate wheel | `d3508b369fd167c0f524c43894766af4f4b498db04b4ee8a31cb3e88f05aa3a6` | 897361 |
| Base sdist | `04780b07498659824bbe5ccba6f15b812a8ba88ab4879b6348b6d628a736e9a9` | 601904 |
| Base wheel | `09e795e8553d7083a2776b9164424e75c49a3b7cf7677ac2c02bbf8eca540dc9` | 897354 |

Findings:

- Both repeats and all three environment Python versions give identical
  hashes for the same input. Kedro in the install environment does not
  change the artifacts. `uv build` isolates the build environment, so an
  installed Kedro cannot affect the build. The wheel is `py3-none-any`.
- Base and candidate differ, as expected. The wheel has the same 513
  members. Only `METADATA` and `RECORD` differ. The `METADATA` diff is one
  line: `Requires-Dist: kedro==1.7.0`. The sdist has the same 518 files.
  Four files differ: both `PKG-INFO` files, `msgloom.egg-info/requires.txt`
  and `pyproject.toml`.
- The candidate sdist contains the scratch `[tool.uv]` exclusion because it
  ships `pyproject.toml`. A real change would not carry that table.
- The wheel allowlist accepted the candidate wheel. It did not report a
  forbidden runtime dependency (`fastmcp`, `prefect`).
- Limit: `uv build` here is uv 0.12.24 in offline mode. CI uses uv 0.13.5
  and a clean cache. Hashes from CI can differ if the uv version changes
  the output. This note did not run the CI workflow.

### Source-boundary tests

Command group, run in each clone with the Python 3.13 venv:

| Step | Command (abridged) | Candidate exit | Base exit |
| --- | --- | --- | --- |
| Reverse-import scan | `python -c 'from scripts.handoff_qualification.audit import reverse_imports; reverse_imports(Path.cwd())'` | 0 | 0 |
| Normal marker set | `pytest -q -n 0 tests/test_microsoft_graph_package_layout.py tests/packaging tests/test_handoff_qualification_portable.py tests/test_handoff_qualification_runner.py -m "not exclusive_state and not fastmcp_compat and not linux_cgroup_v2"` | 0 (33 passed, 25 deselected) | 0 (33 passed, 25 deselected) |
| Exclusive marker | same files, `-m "exclusive_state and not fastmcp_compat and not linux_cgroup_v2"` | 0 (1 passed) | not run |

The 25 deselected tests are 1 `exclusive_state` test and 24
`linux_cgroup_v2` tests. The 24 cgroup tests did not run.
`tests/packaging/test_packaging_config.py` passed with the Kedro pin in
`pyproject.toml`. The tests compare the build backend, the development
pins, the package discovery rules and the tox settings. One test rejects
runtime requirements that start with `tox`, `pytest-cov`, `pytest-xdist`,
`fastmcp` or `prefect`. `kedro` is not on that list.

## Commands and exit codes

| Step | Command (abridged) | Exit code |
| --- | --- | --- |
| Clone | `git clone --no-hardlinks <worktree> clone-base` | 0 |
| Sync base | `uv sync --frozen --no-build --python 3.13` in `clone-base` | 0 |
| Sync candidate | same in `clone-cand` | 0 |
| Freeze | `uv pip freeze --python clone-cand/.venv/bin/python` | 0 |
| Version compare | `python -I cmp_freeze.py base/uv.lock freeze.txt` | 0 |
| Pip check | `uv pip check --python clone-cand/.venv/bin/python` | 0 |
| Pyright, base | CI-style command above | 0 |
| Pyright, candidate | same | 0 |
| Probe `ok_usage.py` | `pyright --pythonpath <venv python> ok_usage.py` | 0 |
| Probe `bad_usage.py` | same | 1 (expected, 4 errors) |
| Probe `untyped_usage.py` | same | 0 |
| Repository-config probe | `pyright --pythonpath .venv/bin/python tests/<bad> message_ingest/<ok>` | 1 (expected) |
| `--verifytypes kedro` (three attempts) | see "Kedro type information" | 1, 1, 1 |
| Qualification runs | `qualify_installed_wheel.py` x 8 (see table) | 0 for all 8 |
| Reverse-import scan | see "Source-boundary tests" | 0 and 0 |
| Boundary pytest | see "Source-boundary tests" | 0, 0, 0 |
| Markdown lint (all 10 F0 notes, all hooks) | `pre-commit run --files docs/notes/a2-kedro-f0-*.md` | 0 |

## Limits

- One platform: Linux aarch64. See the portability note for other
  platforms.
- Pyright 1.1.413 is a user-level tool and the project does not pin it
  outside the CI command.
- Scratch lock: the `pypydispatcher` exclusion from F0-05a applies. It
  affects PyPy only.
- No test touches Kedro. Passing tests show that adding Kedro does not
  break existing tests. They do not test Kedro integration.
- The Kedro sdist was not built. All installs used wheels (`--no-build`).
- Package versions and hashes apply to the PyPI index on 2026-10-24.

## Status / Open items

- F0-05c: DONE for (a), (b) and (c). Part (b) records one failure on 3.14.7.
- Open: the `fastmcp_compat`, `linux_cgroup_v2` and full `exclusive_state`
  sets were not run with Kedro installed.
- Open: strict-mode Pyright would report partly unknown Kedro types.
- Open: the 3.14.7 full run has 1 failed test. The cause is a likely but
  unproven container-name collision.
