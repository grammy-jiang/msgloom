# A2 Kedro F0-03: static dataset allowlist gate (specification)

Date: 2026-10-24. Task: F0-03. Candidate: `kedro` 1.7.0 (wheel SHA-256
`488701a27c7d595b62a611cb23596953a9929fe5cc42a376c28abe26654c2438`).

## Pending items in this evidence set

PENDING: two cells in the co-install note (`a2-kedro-f0-coinstall.md`).
They are the full pytest run on Python 3.12.14 (`FULL_312`, with
`FULL_312_EXIT` and `FULL_312_RESULT`) and on Python 3.14.7 (`FULL_314`,
with `FULL_314_EXIT` and `FULL_314_RESULT`). Both runs were still running
when this note was committed. No value is recorded and none is guessed.
The 3.13.16 full run is final: 4705 passed, exit 0.

No row in this note depends on those two cells.

## Result

This note is a specification with a scratch prototype. No production code
exists. The prototype proves that a small static gate rejects the listed
bad inputs. It does not prove the gate is complete. The gate is a design
proposal for the owner and for the later implementation task.

Key facts from the prototype run (Kedro 1.7.0, CPython 3.13, exit code 0):

- Without a gate, Kedro runs a node whose output name is not in the
  catalog. It creates an implicit `MemoryDataset`. The gate must check
  pipeline dataset names before a run.
- Dataset values are not written to logs during a successful run.
- A node's exception text is written to the ERROR log and is carried in the
  raised exception. A node must raise sanitized text only.
- Dataset names and node names are written to logs. They must be static.

## Scope

Allowed Kedro surface: `Pipeline`, `node`, `DataCatalog(datasets={...})`,
`MemoryDataset`, `SequentialRunner` (or another runner chosen later), and
msgloom-owned `AbstractDataset` subclasses. Everything else in the table
below is forbidden by the gate.

## Specification

| ID | Rule | Enforcement point | Evidence in this task |
| --- | --- | --- | --- |
| R1 | Dataset names are a fixed `frozenset` of string literals in msgloom code. No name comes from message content, config files or the network. | Catalog builder; pipeline check | Prototype `ALLOWED_NAMES` |
| R2 | The catalog is built only with `DataCatalog(datasets={name: instance})`. `DataCatalog.from_config` and `parse_dataset_definition` are never called. | Source scan test; code review | AST scan caught `from_config` |
| R3 | Dataset instances have an exact type from a short allowlist. Subclass checks use `type(ds) in ALLOWED`, not `isinstance`. msgloom-owned classes enter the allowlist by an explicit code change. | Catalog builder | `Sub(MemoryDataset)` rejected |
| R4 | No `AbstractVersionedDataset` subclass and no `Version(...)` object. `load_versions`, `save_version` and a `version=` argument to `DataCatalog.load` are never used. | Catalog builder; source scan; call wrapper | Versioned dataset rejected; `version` rejected; AST scan caught `load_versions` |
| R5 | Every dataset name used by a pipeline (inputs, outputs, node arguments) must be in the allowlist before the runner starts. | Pre-run check | Unlisted output rejected; Kedro alone ran it |
| R6 | No Kedro CLI (`kedro.framework.cli`), no `KedroSession`, no `ServiceSession`, no `kedro.server`, no `bootstrap_project`. | Source scan; module check at test time | AST scan caught CLI and session imports; modules not loaded by io, pipeline and runner imports |
| R7 | No `kedro_datasets`, no dynamic plugin or entry-point loading, no `kedro.hooks` entry points. | Source scan; hook manager is explicit | AST scan caught `kedro_datasets`; see F0-04 for entry points |
| R8 | A file-backed msgloom-owned dataset resolves its path with a `safe_join(base, relative)` helper. The helper rejects empty, NUL, absolute, backslash-leading and `..` inputs. It also rejects any `realpath` result outside the base directory (symlink escape). The relative part is a constant, not message content. | Dataset constructor | Seven bad inputs rejected; one good input accepted |
| R9 | Log and exception text contains no message content, addresses, names or tokens. Dataset and node names are static. A node raises a sanitized exception: a fixed code or a hash, never the raw input. | Node wrapper; redaction tests | Canary appeared in the ERROR log and exception text |
| R10 | The telemetry controls from F0-04 apply: no session, no entry-point hooks, `DO_NOT_TRACK=1` as a second line. | Process setup; network-namespace test | F0-04 modes A, B, H, I |
| R11 | The Kedro guard against unsafe version strings (F0-02) is a second line of defense only. The gate does not rely on it. | Not applicable | F0-02 probe |

## Prototype

Script: `/tmp/f0-scratch-20261024/scripts/f0_03_gate_demo.py`
(SHA-256
`d1fe1e7f286c7a15f63410b2b20f94c945f8a1e0cfd7b86c20082f8290e23173`;
run with `venv-kedro/bin/python -I`). Output: `json/f0_03_demo.out`. The prototype is
not production code and is not in the repository.

Prototype design:

- `check_catalog_datasets(datasets)`: name in allowlist, exact class in
  allowlist, not an `AbstractVersionedDataset`.
- `check_pipeline_names(pipeline)`: every input, output and node dataset
  name is in the allowlist.
- `check_load_version(version)`: rejects any non-`None` version.
- `safe_join(base, rel)`: the path rules from R8.
- `scan_source(src)`: an `ast` walk that flags forbidden attribute names,
  keyword names, names and import prefixes.

## Negative test cases (specification for the implementation task)

Each case must fail before the gate exists and pass after it. Expected
result is the gate raising a specific exception such as `GateError`. The
last column shows what the scratch prototype returned.

| Case | Input | Expected | Prototype result |
| --- | --- | --- | --- |
| N1 Unknown dataset | catalog `{"zzz": MemoryDataset()}` | Rejected | Rejected |
| N2 Unlisted pipeline output | node output name `zzz` | Rejected before run | Rejected |
| N3 Subclassed dataset | subclass of `MemoryDataset` | Rejected | Rejected |
| N4 Versioned dataset | `AbstractVersionedDataset` subclass with `Version(None, None)` | Rejected | Rejected |
| N5 Version argument | `version="2026-01-01"` | Rejected | Rejected |
| N6 Parent traversal | `../../etc/passwd` | Rejected | Rejected |
| N7 Embedded traversal | `sub/../../x` | Rejected | Rejected |
| N8 Absolute path | `/etc/passwd` | Rejected | Rejected |
| N9 Backslash traversal | `..\x` | Rejected | Rejected |
| N10 NUL byte | `a\x00b` | Rejected | Rejected |
| N11 Empty path | empty string | Rejected | Rejected |
| N12 Symlink escape | `link/secret` where `link` points outside the base | Rejected | Rejected |
| N13 `from_config` call | `DataCatalog.from_config({})` in source | Flagged | Flagged |
| N14 `load_versions` keyword | `f(load_versions={...})` in source | Flagged | Flagged |
| N15 CLI import | `from kedro.framework.cli import main` | Flagged | Flagged |
| N16 Session import | `from kedro.framework.session import KedroSession` | Flagged | Flagged |
| N17 Dynamic dataset package | `import kedro_datasets.pandas` | Flagged | Flagged |
| N18 Untrusted import in config | a dataset `type:` string naming a module | Not representable: no config path exists | Not tested (no config path in the prototype) |
| N19 PII in log | node raises with raw input text | Test fails the build if the text reaches any log record or exception string | The raw text reached both (this is the positive control that the test can see it) |
| N20 PII in value log | successful run with a canary value in a dataset | Canary absent from log records | Canary absent |
| N21 Runtime modules | after importing the bridge, none of `kedro.framework.cli`, `kedro.framework.session`, `kedro.server`, `kedro_datasets`, `kedro_telemetry` is in `sys.modules` | Test passes | All absent after `kedro.io`, `kedro.pipeline` and `kedro.runner` imports |
| N22 Positive controls | allowed catalog; allowed pipeline; path `sub/ok.json` | Accepted | Accepted (reported as "NOT REJECTED") |

Notes on the test design:

- Each negative test needs a matching positive control, as in N22. A test
  that never fails proves nothing.
- N19 must assert on log records and on the exception string. The ERROR
  log in Kedro 1.7.0 includes the exception text (Q0 R2 reached the same
  result with a node logger test).
- N21 must run in a fresh interpreter (`python -I`), because other tests
  can import those modules.
- Tests must follow `AGENTS.md`: no `assert` statements; use an explicit
  condition and `pytest.fail()`.

## Observations from the prototype run

| Check | Result |
| --- | --- |
| Kedro run with an output name absent from the catalog | Ran. Log: `Saving data to undeclared_out (MemoryDataset)` |
| Success run with a canary value (`jane.doe@example.invalid`) in dataset `a` | Canary absent from all log text |
| Log lines in a success run | Dataset names, node names and function names appear |
| Failure run, node raises `ValueError(f"cannot parse {x}")` | ERROR log and `str(exception)` both contain the canary |
| Modules loaded after `kedro.io`, `kedro.pipeline`, `kedro.runner` imports | `kedro.framework.project` loaded (the log shows `rich_logging.yml`). Not loaded: `kedro.framework.cli`, `kedro.framework.session`, `kedro.server`, `kedro_datasets`, `kedro_telemetry`, `requests`, `git`, `cookiecutter` |

The prototype gate is a Python-level check. A caller can bypass it by
calling Kedro directly. The source scan (R2, R4, R6, R7) and a code review
rule cover that. A sandbox or import hook was not tried.

## Commands and exit codes

| Command | Exit code |
| --- | --- |
| `venv-kedro/bin/python -I scripts/f0_03_gate_demo.py` | 0 |

Output was saved to `/tmp/f0-scratch-20261024/json/f0_03_demo.out`
(stdout, JSON) and `f0_03_demo.err` (Kedro Rich log lines).

## Source URLs

- `https://pypi.org/project/kedro/1.7.0/`
- Wheel files read: `kedro/io/data_catalog.py` (`DataCatalog.load`,
  `from_config`, `_validate_versions`), `kedro/io/core.py`
  (`AbstractVersionedDataset`), `kedro/runner/runner.py`.

## Status / Open items

- F0-03: DONE as a specification plus scratch prototype.
- Open: no production gate or test exists. The implementation task must
  add them.
- Open: N18 (untrusted import through a config string) is covered only by
  forbidding all config-driven catalogs. If the owner later allows a config
  catalog, a new rule and test are needed.
- Open: the runner's implicit dataset behavior (R5) was seen with
  `SequentialRunner` only. Other runners were not tested.
- Open: `safe_join` was tested on Linux only. Windows path rules were not
  tested.
- Open: the source scan is a name-based `ast` walk. It does not follow
  `getattr` strings or `importlib` calls.
- Open: msgloom-owned file-backed datasets do not exist yet. R8 has no
  production consumer today.
