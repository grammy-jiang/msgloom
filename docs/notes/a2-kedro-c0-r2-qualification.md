# A2 Kedro C0 R2 qualification

Result: tasks CR-01 to CR-08 are done. The independent review R2 accepted
commit `ee2c8e125f9d7f65a26f0d56ab7e07c492342472` (archived in
`docs/notes/a2-kedro-c0-independent-review-r2.txt`). This note does not claim
production readiness.

R2 tested SHA: `ee2c8e1` (`ee2c8e125f9d7f65a26f0d56ab7e07c492342472`), on top of
`0eb8fe6`. The earlier claim of an "uncommitted tree" run is replaced by this
SHA. The R1 review file is archived and unchanged.

## R2 minor-finding fixes (after ee2c8e1)

Fix commit `46fe277` closed R2 findings 2 to 7. Findings 1 and 8 are
unchanged. The R3 review accepted `46fe277` with Minor findings N1 to N5.
The next section records how they are closed.

| Finding | Status |
| --- | --- |
| 1 Ruff E741 | Unchanged. `ruff check scripts tests` exits 0, so E741 is not selected. |
| 2 Stale run claims | Fixed. The doc and this note name `ee2c8e1` as the tested SHA. |
| 3 Foreign roots | Fixed. New `test_c0_receipt_foreign_roots.py` has a positive control, two foreign-selection cases that keep the root count, and one appended-root case that the generic count check rejects. |
| 4 Replay wording | Fixed in the doc section 6 and the `append_or_verify` docstring. The whole payload including `ResultRef` is compared. |
| 5 Style | Fixed. Two long comments are shortened. Multiline docstrings in the touched files start with the quotes on their own line. |
| 6 prepared@2 control | Fixed. The same claim shape stores prepared@1. |
| 7 Changed output | Fixed. An equal replay with identical metadata passes. A replay that differs only in the semantic bytes raises `ImmutableRecordError`. |
| 8 Semantic digest | Unchanged. It stays a production requirement. |

Not changed: `scripts/research/c0_atomic_acceptance_prototype.py` is outside
the allowed edit scope. Its module docstring still puts text on the opening
quote line.

## R3 minor-finding fixes (tree A)

Tree A is commit `f0072def98bffcf270ab0eed5b42902a0ea01d68`. Commit B changes only this note.

| Finding | Status |
| --- | --- |
| N1 Long comment | Fixed. The inline comment in `test_c0_phase1_storage_integration.py` is wrapped to 79 columns. |
| N2 Foreign-root wording | Fixed. The test docstring says two cases replace the first root's `IntakeSelection` and keep the root count. The third case appends a root. It changes the count, and the generic count check ("missing/overlapping") rejects it. |
| N3 Evidence binding | Fixed. The results below are bound to tree A. |
| N4 Opening-quote line | Unchanged, as declared. `c0_atomic_acceptance_prototype.py` is outside the edit scope. |
| N5 Missing edge tests | Fixed. New `test_c0_identity_and_replay_edges.py` has three tests. See below. |

N5 tests. Each has a positive control. Each negative case uses `match=` on the
expected message.

- `append_or_verify` with a byte-count-only difference and with a key-only
  difference raises `a2-accepted-result-integrity-conflict`. The test checks
  that each case changes exactly one field.
- `StageIdentity` rejects a duplicate selected occurrence
  (`duplicate selected occurrence`). The control differs only in `occurrence`.
- `StageIdentity` rejects selected roots from two catalogs
  (`cross-catalog selected roots`). The foreign root has a distinct
  occurrence, so the duplicate check cannot be the cause. The control uses
  the workset catalog.

Mutation check (temporary edits to the prototype, reverted): comparing only
the digest in `append_or_verify`, disabling the duplicate check, and disabling
the cross-catalog check each made exactly the matching new test fail.

All N5 checks already exist in the prototype. No open gap is added for N5.

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

### At tree A (clean tree, no uncommitted change)

Tested at tree A=`f0072def98bffcf270ab0eed5b42902a0ea01d68`; commit B changes only the note. `git status --short`
was empty before and after the runs. Run in the C0 worktree.

| Command | rc |
| --- | --- |
| `uv run --no-sync python -m pytest -q -n 0 -p no:cacheprovider tests/research/test_c0_*.py` (3 runs) | 0, 0, 0 (28 passed each) |
| `uv run --no-sync ruff check <3 changed test files>` | 0 |
| `uv run --no-sync ruff format --check <3 changed test files>` | 0 (3 formatted) |
| `uv run --no-sync ruff check scripts tests` | 0 |
| `uv run --no-sync ruff format --check scripts tests` | 0 (579 formatted) |
| `npx --yes --package pyright@1.1.413 pyright --pythonpath .venv/bin/python microsoft_graph message_ingest msgloom tests` (CI command) | 0 (0 errors) |
| `npx --yes --package pyright@1.1.413 pyright --pythonpath .venv/bin/python scripts/research tests/research` | 0 (0 errors) |
| `grep -nE "^\s*assert \|type: ignore\|noqa\|pyright: ignore\|skip\|xfail"` on the 3 changed test files | 1 (no match) |
| `uv tool run --from pre-commit==4.7.0 pre-commit run --files <3 changed test files>` | 0 (gitleaks, ruff check, ruff format passed) |

The 3 changed test files are `test_c0_identity_and_replay_edges.py`,
`test_c0_receipt_foreign_roots.py` and
`test_c0_phase1_storage_integration.py`. The note itself is checked by
`pre-commit run --files docs/notes/a2-kedro-c0-r2-qualification.md` in
commit B (markdownlint). That result is in the final report, not in this note.

Test count: 13 + 1 + 1 + 4 + 5 + 1 + 3 = 28. Line counts:
`c0_contract_prototype.py` 464 (unchanged), `test_c0_contract_prototype.py`
498, `test_c0_phase1_storage_integration.py` 479,
`test_c0_atomic_acceptance.py` 313, `test_c0_native_a1_exact_handoff.py` 168,
`test_c0_baseline_contract.py` 121, `test_c0_receipt_foreign_roots.py` 54,
`test_c0_identity_and_replay_edges.py` 100. All are below 500.

### Earlier runs (history)

At `ee2c8e1` (clean `git archive` export): the C0 tests gave 24 passed. After
the R2 fixes at `46fe277`, the C0 tests gave 25 passed. The R2 and R3 reviews
could not run code. Only the tree A results above are bound to an exact SHA.

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
- `tests/research/test_c0_receipt_foreign_roots.py` (new, R2 fix; R3 wording)
- `tests/research/test_c0_identity_and_replay_edges.py` (new, R3 fix)
- `docs/notes/a2-kedro-c0-r2-qualification.md` (this note)

The list above is the original CR set. The R2 fix changed only the doc, this
note, `c0_contract_prototype.py` and the test files named in the fix table.
The R3 fix (tree A) changed only `test_c0_phase1_storage_integration.py`,
`test_c0_receipt_foreign_roots.py` and the new
`test_c0_identity_and_replay_edges.py`; commit B changes only this note.
No file under `msgloom/`, `message_ingest/`, `microsoft_graph/`,
`pyproject.toml` or `uv.lock` changed. `.venv` is git-ignored.
