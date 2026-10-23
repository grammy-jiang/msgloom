# A2 Kedro C0 R2 qualification

Result: tasks CR-01 to CR-08 are done in the working tree. All local gates
pass. This note does not claim CR-10 ACCEPT. CR-10 needs an independent
read-only review of an exact commit SHA.

Base: branch `research/a2-kedro-c0-20261023`, HEAD
`0eb8fe6d2e5d301c359b60292c1852bbe7558c6d`. All changes are uncommitted.
The R1 review file is untracked and unchanged (SHA-256 `128b0308...9f67a`).

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

Run in the C0 worktree after `uv sync --locked --group dev` (rc 0).

| Command | rc |
| --- | --- |
| `uv run --no-sync python -m pytest -q -n 0 tests/research/test_c0_*.py` (3 runs) | 0, 0, 0 (24 passed each) |
| `ruff check` on the 5 touched Python files | 0 |
| `ruff format --check` on the 5 touched Python files | 0 |
| `ruff check scripts tests` and `ruff format --check microsoft_graph message_ingest msgloom scripts tests` (CI scope) | 0, 0 |
| `npx --yes --package pyright@1.1.413 pyright --pythonpath .venv/bin/python microsoft_graph message_ingest msgloom tests` (CI command) | 0 (0 errors) |
| same pyright on `scripts/research tests/research` | 0 (0 errors) |
| `grep -n -E '^\s*assert '` on touched and sibling research files | 1 (no match) |
| `uv tool run --from pre-commit==4.7.0 pre-commit run --files <6 touched files>` | 0 (gitleaks, markdownlint, ruff passed) |

Test count: 13 + 1 + 4 + 5 + 1 = 24. Line counts: `c0_contract_prototype.py`
454, `test_c0_contract_prototype.py` 499, `test_c0_phase1_storage_integration.py`
438, `test_c0_atomic_acceptance.py` 309, `test_c0_native_a1_exact_handoff.py`
167. All are below 500.

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
- `docs/notes/a2-kedro-c0-r2-qualification.md` (this note, new)

No file under `msgloom/`, `message_ingest/`, `microsoft_graph/`,
`pyproject.toml` or `uv.lock` changed. `.venv` is git-ignored.
