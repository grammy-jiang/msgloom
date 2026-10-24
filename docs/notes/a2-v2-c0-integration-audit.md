# A2 v2 C0-20a integration audit

Status: STAGING EVIDENCE. This note is not a production acceptance.
C0-20c, F0_PRODUCTION_ADMISSION and the CI gate stay open.

## Result

Four accepted C0 branches merge with no textual conflict. Four test files
had drift that only shows after the merge. This branch fixes them. After
the fix, 2,780 focused tests pass.

## Integrated heads

| Branch | Head | Tasks |
| --- | --- | --- |
| `feat/a2-v2-c0-21a-registry-20261025` (includes contracts `62a9a13`) | `52e3c03` | C0-01 to C0-10, C0-15, C0-16, C0-19, C0-21a, C0-21b |
| `feat/a2-v2-db-20261024` | `8f200e7` | C0-11, C0-12, C0-13a, C0-14a to C0-14e, C0-22 |
| `feat/a2-v2-a3-triage-v2-20261025` | `526e49f` | C0-17a to C0-17g |
| `feat/a2-v2-c0-18-scope-status-20261025` | `c161e83` | C0-18 |

Base of all four: master `895fc40`. Merge order: registry, db, a3, c0-18.

## Drift found and fixed

Cause: contracts commits `bf563f8` and `20d54dd` were made after the db
branch forked. They tightened two contracts.

1. `CompletionReceipt.acceptance_index_sha256` is now a required field.
   Tests that called `CompletionReceipt(...)` failed with a missing-field
   error (87 errors, 16 failures). Fix: call `CompletionReceipt.build(...)`.
   Files: `tests/a2_kedro/helpers_c0_14b.py`,
   `tests/a2_kedro/test_c0_14b_recheck.py`,
   `tests/a2_kedro/test_c0_14c.py`,
   `tests/persistence/test_a2_v2_finalization.py`.
2. A `TerminalRoot` with status INCOMPLETE must carry limitations.
   `test_all_roots_held_finalizes_incomplete` built a held root without
   them. Fix: give the saved result, the accepted stage and the root the
   same `Limitation("held", ...)`.

Only test code changed. No production module changed.

Action for the db owner: when PR80 is stacked on the contracts branch,
apply the same test edit (cherry-pick the C0-20a fix commit).

## Ownership and protected files

Compared with master `895fc40`, only two existing protected persistence
files changed, both additive:

- `msgloom/persistence/intake_store.py`: +3 lines, 497 lines in total.
  This is the v1 writer-fence hook from C0-14c. It needs Supervisor
  confirmation (open item since cycle 41).
- `msgloom/persistence/async_store.py`: +11 lines, 453 lines in total.
  This is the `run_bounded` hook. It needs Supervisor confirmation.

`schema_store.py`, `store.py` and `intake_completion.py` are unchanged.
Existing A3 modules changed: `finalize_mixin.py` (+71/-1),
`handler.py` (+6), `io_mixin.py` (+2/-10), `limitations.py` (+133/-1),
`models.py` (+43). `handler.py` is also the file that C0-17h would need.
The +6 lines come from C0-17c. C0-17h still needs a Supervisor ruling.

No changed Python file has 500 lines or more. No added line has a Python
`assert`.

## Verification (merge head `e3a51f0` plus the test-fix commit)

- `pytest` on `tests/a2_kedro tests/persistence tests/persistence_fences
  tests/persistence_reconciliation tests/phase1_foundation
  tests/phase1_data_contracts tests/triage_pipeline tests/triage_input
  tests/triage_contracts tests/working_context
  tests/test_python_source_conventions.py`, deselecting `test_c0_18`:
  2,780 passed.
- `tests/a2_kedro/test_c0_18.py` run with `PYTHONPATH` set: 27 passed,
  12 failed. The 12 are the process tests that run `python -I`. In a
  worktree the editable install points at the main checkout, so
  `msgloom.cli.a2_scope_status` is not found. This is an environment
  limit, not a regression.
- `ruff check` and `ruff format --check` on all added or changed Python
  files: clean.
- `pyright` on the same files: 0 errors.
- All SQLite use is in `tmp_path`. No user database is opened.

## Not covered

- C0-20b (real A1 Workset to v2 receipt to A3 end-to-end fixture).
- Full GitHub required checks. `uv audit --locked` fails on Twisted
  26.4.0, so the quality job stops before Ruff and Pyright there.
- Production migration, F0 admission and cutover.
