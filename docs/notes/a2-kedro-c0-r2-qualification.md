# A2 Kedro C0 R2 qualification

Result: tasks CR-01 to CR-08 are done. The independent review R2 accepted
commit `ee2c8e125f9d7f65a26f0d56ab7e07c492342472` (archived in
`docs/notes/a2-kedro-c0-independent-review-r2.txt`). This note does not claim
production readiness.

Tested SHA: `ee2c8e1` (`ee2c8e125f9d7f65a26f0d56ab7e07c492342472`), on top of
`0eb8fe6`. The earlier claim of an "uncommitted tree" run is replaced by this
SHA. The R1 review file is archived and unchanged.

## R2 minor-finding fixes (after ee2c8e1)

The fix commit SHA is set by the manager. Review R2 findings 2 to 7 are fixed.
Findings 1 and 8 are unchanged.

| Finding | Status |
| --- | --- |
| 1 Ruff E741 | Unchanged. `ruff check scripts tests` exits 0, so E741 is not selected. |
| 2 Stale run claims | Fixed. The doc and this note name `ee2c8e1` as the tested SHA. |
| 3 Foreign roots | Fixed. New `test_c0_receipt_foreign_roots.py` has a positive control and three foreign-root cases. |
| 4 Replay wording | Fixed in the doc section 6 and the `append_or_verify` docstring. The whole payload including `ResultRef` is compared. |
| 5 Style | Fixed. Two long comments are shortened. Multiline docstrings in the touched files start with the quotes on their own line. |
| 6 prepared@2 control | Fixed. The same claim shape stores prepared@1. |
| 7 Changed output | Fixed. An equal replay with identical metadata passes. A replay that differs only in the semantic bytes raises `ImmutableRecordError`. |
| 8 Semantic digest | Unchanged. It stays a production requirement. |

Not changed: `scripts/research/c0_atomic_acceptance_prototype.py` is outside
the allowed edit scope. Its module docstring still puts text on the opening
quote line.

## Status per task

| Task | Status | Evidence |
| --- | --- | --- |
| CR-01 | done | Contract doc section 1 table row and the policy-change finding. Old completion can finalize a held-only workset as COMPLETE. The aggregate ignores `workset.held`. Receipt@2 is a new v2 policy. A1 is unchanged. I re-read the cited legacy lines and they match. |
| CR-02 | done | Three weak tests now decode JSON-mode payloads with `model_validate_json`. Each has a positive control. Each negative case must produce exactly one error with the expected text. Checked: extra field, selected-roots XOR transition batch, kind/version pairing, receipt policy version. |
| CR-03 | done | `test_duplicate_saved_selection_ref_never_collapses_intake_occurrences`. One `ResultRef` at two entries. `selection_refs` has one item. The receipt needs two results. The docstring says real A1 cannot produce this case. |
| CR-04 | done | Doc section 6. The bypass cause is the `c0-a2:` key prefix (not `prepare:`). Empty `required_inputs` is a separate gap. Seven unverified items are listed. |
| CR-05 | done | Native A1 test has two new negative cases on real A1 data. One selection is in the workset with a wrong ordinal identity. One saved selection has different content. The ambiguous-ordinal branch cannot be built honestly and stays unexercised. Doc says so. A1 is not changed. |
| CR-06 | done | Pyright: 0 errors with the CI command. Typed helper `required_semantic_ref` and explicit guards with `pytest.fail`. No ignore, `type: ignore` or `noqa`. |
| CR-07 | done | No "Expected C0 test condition at line N" text remains. Messages explain the expectation. Live claims use 120 s leases. Expiry tests use `lease=0` with no sleeps. Barrier waits use 30 s. Three repeat runs pass. |
| CR-08 | done | Doc section 6 "Research-prototype limits". It covers private `_store`, unprotected `asyncio.to_thread` cancellation, decode inside the writer lock and `create_all` as experiment-only. It also explains the distinct claim keys and the missing start barrier in the concurrency tests. |

## Commands and exit codes

### At ee2c8e1 (clean `git archive` export, run once)

| Command | rc |
| --- | --- |
| `python -m pytest -q -n 0 -p no:cacheprovider tests/research/test_c0_*.py` | 0 (24 passed) |

Earlier gates for this tree (Ruff, Pyright, pre-commit) were recorded by the
original CR worker and are not re-run here.

### After the R2 minor fixes (working tree on top of f0eace0)

Run in the C0 worktree.

| Command | rc |
| --- | --- |
| `uv run --no-sync python -m pytest -q -n 0 tests/research/test_c0_*.py` (3 runs) | 0, 0, 0 (25 passed each) |
| `uv run --no-sync ruff check` on the 7 touched Python files | 0 |
| `uv run --no-sync ruff format --check` on the 7 touched Python files | 0 (7 formatted) |
| `uv run --no-sync ruff check scripts tests` | 0 |
| `npx --yes --package pyright@1.1.413 pyright --pythonpath .venv/bin/python scripts/research tests/research` | 0 (0 errors) |
| `grep` for `assert` statements, `type: ignore`, `noqa`, `pyright: ignore`, `skip`, `xfail` in the 7 files | 1 (no match) |
| `uv tool run --from pre-commit==4.7.0 pre-commit run --files <8 touched files>` | 0 (gitleaks, markdownlint, ruff passed) |

Test count: 13 + 1 + 1 + 4 + 5 + 1 = 25. Line counts:
`c0_contract_prototype.py` 464, `test_c0_contract_prototype.py` 498,
`test_c0_phase1_storage_integration.py` 478, `test_c0_atomic_acceptance.py`
313, `test_c0_native_a1_exact_handoff.py` 168,
`test_c0_baseline_contract.py` 121, `test_c0_receipt_foreign_roots.py` 52.
All are below 500.

## Remaining known gaps

- The pyproject `extend-exclude = ["research"]` setting excludes both research
  directories from the CI Ruff run. I ran Ruff on the files directly. CI Pyright
  covers `tests/research` but not `scripts/research`. I ran that separately.
- The two concurrency tests have no start barrier. They show SQLite
  serialization, not proven overlap. The doc says this.
- The ambiguous-ordinal branch of the A1 verifier is not exercised.
- Native A1 proof covers one primary Mail entry. Components, transitions,
  contexts, baseline and Teams fixtures are not proven.
- The verifier copies A1's private identity algorithm. It needs a pinned
  golden fixture and a public verifier.
- Receipt@2 is structural only. It does not read stored payloads or claims.
- The production blockers from R1 stay open. C0 is not ready for a production
  freeze. The Snyk CVE-2026-3840 owner decision is open. Kedro is not a
  dependency.
- I did not run the full repository test suite.

## Files changed

- `docs/plans/2026-10-23-a2-kedro-c0-contract-candidate.md`
- `scripts/research/c0_contract_prototype.py`
- `tests/research/test_c0_atomic_acceptance.py`
- `tests/research/test_c0_contract_prototype.py`
- `tests/research/test_c0_native_a1_exact_handoff.py`
- `tests/research/test_c0_phase1_storage_integration.py`
- `tests/research/test_c0_receipt_foreign_roots.py` (new, R2 fix)
- `docs/notes/a2-kedro-c0-r2-qualification.md` (this note)

The list above is the original CR set. The R2 fix changed only the doc, this
note, `c0_contract_prototype.py` and the test files named in the fix table.
No file under `msgloom/`, `message_ingest/`, `microsoft_graph/`,
`pyproject.toml` or `uv.lock` changed. `.venv` is git-ignored.
