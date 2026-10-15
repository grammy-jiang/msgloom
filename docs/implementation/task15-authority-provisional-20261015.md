# Task 15: Mail provisional authority isolation

Both confirmed races are fixed in the working tree. Message-delta and
folder-delta observations remain provisional until the original cursor CAS
validates. Late losing callbacks cannot change accepted projections or releases.

- Branch: `fix/task15-authority-provisional-isolation-20261015`.
- Baseline: `897972cb0dd98d54fd8f32ffbfc13e9508a928b5`.
- Runtime: Python 3.13.5, Scrapy 2.19.0, aarch64.
- Design: `mail-authority-race-design-20261015.md`, read from the supplied
  independent task-runtime directory.

## Implementation

Three additive Mail tables retain exact original ownership/projections, accepted
projection ownership, and sealed promotion decisions. Schema validation fails
closed on partial or unknown definitions. Legacy pending work without retained
inputs requires reacquisition. Existing ledger payloads and cursor schemas are
preserved.

The original writer transaction validates CAS before applying selected state,
components, presence, release entries, and cursors. Exact promotion retries are
read-only. Advanced A/B/A applications retain exact identity; equivalent recovery
retains its original pin. Independent discovery and Full freshness rules remain
active. Source-reader tests reconstruct the original winning saved response.

Native overlap testing also found and fixed shared temporary evidence filenames,
SQLite lifecycle lock upgrades, stale inventory callbacks losing their own run
sighting, and membership transitions colliding with primary projection lookup.
These fixes preserve evidence-before-semantics ordering and native Scrapy idle,
410, and JOBDIR ownership. No Teams files changed.

See [the storage and recovery contract](../notes/mail-provisional-authority.md).
The native boundary follows the installed Scrapy 2.19.0 implementation, including
[engine idle checks](https://github.com/scrapy/scrapy/blob/2.19.0/scrapy/core/engine.py).

## Validation results

| Check | Result |
| --- | --- |
| Final focused race/provisional/evidence tests | 34 passed |
| Authority, ledger, schema, and Mail store regression | 315 passed; 5 HTTP-fixture cases blocked by socket permissions |
| Saved-source regression, excluding Teams files | 222 passed |
| Workflow, Full, 410, JOBDIR, evidence, and cancellation regression | 219 passed; feed subprocess timed out without the IPC adapter |
| Existing native shutdown scenarios with retained IPC adapter | All 18 passed |
| Existing native feed-export scenario with retained IPC adapter | Passed exact canonical output comparison |
| `ruff check message_ingest tests` | Passed |
| `ruff format --check message_ingest tests` | 804 files already formatted |
| `pyright message_ingest tests` | 0 errors, 0 warnings |
| Live LSP on changed source and test documents | 48 opened, 48 reported, no diagnostics |
| `scrapy check` | 4 contracts passed |
| `git diff --check` | Passed |
| Changed Python modules | All 48 below 500 lines; no AST `assert` nodes |

The focused tests first reproduced the two supplied failures. Additional red
checks reproduced the shared evidence temporary-file race, lost inventory
sighting, and membership/primary collision before their fixes.

### Environment limits

This sandbox denies TCP socket creation and local socket sends. Async validation
used an external `/tmp/task15-pipe-ipc/sitecustomize.py` adapter that replaces only
asyncio's local wakeup socket with `os.pipe`. It does not provide networking or
change repository code. The new native race uses real Scrapy crawlers and a
fixture download handler, with one shared database and evidence directory.

The five blocked cases are
`test_mail_inventory_bindings.py::test_native_inventory_changes_and_delayed_parent_gap_only`
with parameters `empty`, `reduced`, `terminal`, `partial`, and `retry`. Their local
HTTP server fails with `PermissionError: [Errno 1] Operation not permitted`.
Earlier HTTP-based runs met the same restriction. These are not claimed as
passing. Earlier broad source-reader validation also encountered two unrelated
Teams HTTP-fixture errors; Teams code was not changed.

The standard shutdown and feed-export test subprocess launchers replace
`PYTHONPATH`, which removes the adapter. The shutdown batch was stopped after
repeated subprocess timeouts. Its original `_crawl` scenarios and original
`FEED_RUN` fixture were then run in bounded subprocesses with the adapter
retained. All 18 shutdown scenarios and the exact feed comparison passed.

A repository-wide size audit found pre-existing modules at or above 500 lines:
`msgloom/sources/handoff_catalog.py` (506),
`tests/ai_boundary/test_lifecycle_repair.py` (500), and research validation
`experiments.py` (733) and `fixtures.py` (659). They remain outside this change.
The repository-wide AST scan found no `assert` nodes.

The usage guard could not persist its alert file outside the writable sandbox.
No unattended manager was started. No remote operation was performed.

## Exact pytest selections

Each command below used `.venv/bin/pytest -q` with
`PYTHONPATH=/tmp/task15-pipe-ipc:.` in this sandbox. Logs are local files under
`/tmp/task15-*-final.log` and `/tmp/task15-workflow-portable.log`.

### Final focused selection

```text
tests/test_mail_losing_run_authority_isolation.py
tests/test_mail_provisional_components.py
tests/test_mail_provisional_native.py
tests/test_mail_provisional_projections.py
tests/test_mail_provisional_schema.py
tests/test_mail_provisional_transactions.py
tests/test_evidence_concurrent_blob.py
```

### Authority and store selection

```text
tests/test_acquisition_handoff_catalog.py
tests/test_acquisition_handoff_immutability.py
tests/test_acquisition_handoff_membership.py
tests/test_acquisition_handoff_reapplication.py
tests/test_acquisition_handoff_scope.py
tests/test_mail_authority_associations.py
tests/test_mail_authority_reapplication_boundary.py
tests/test_mail_authority_release.py
tests/test_mail_authority_release_freshness.py
tests/test_mail_authority_release_native.py
tests/test_mail_authority_release_recovery.py
tests/test_mail_authority_release_validation.py
tests/test_mail_authority_restoration_and_checkpoint.py
tests/test_mail_binding_schema.py
tests/test_mail_contract_associations.py
tests/test_mail_contract_pins.py
tests/test_mail_delta_absence_generation.py
tests/test_mail_delta_causality_schema.py
tests/test_mail_delta_overlap_causality.py
tests/test_mail_folder_delta_causal_race.py
tests/test_mail_folder_delta_schema.py
tests/test_mail_inventory_bindings.py
tests/test_mail_losing_run_authority_isolation.py
tests/test_mail_provisional_components.py
tests/test_mail_provisional_native.py
tests/test_mail_provisional_projections.py
tests/test_mail_provisional_schema.py
tests/test_mail_provisional_transactions.py
tests/test_mail_schema_guard_boundaries.py
tests/test_outlook_mail_atomic_promotion.py
tests/test_outlook_mail_checkpoint_provenance.py
tests/test_outlook_mail_handoff_boundaries.py
tests/test_outlook_mail_handoff_facts.py
tests/test_outlook_mail_presence.py
```

### Workflow and pipeline selection

```text
tests/test_outlook_mail_delta.py
tests/test_outlook_folder_delta.py
tests/test_outlook_delta_integrity.py
tests/test_mail_delta_causality_native.py
tests/test_mail_delta_state.py
tests/test_outlook_mail_rule_sync_workflows.py
tests/test_outlook_mail_rule_jobdir_resume.py
tests/test_jobdir_resume.py
tests/test_mail_enrichment_planner.py
tests/test_mail_full_completion_facts.py
tests/test_outlook_mail_full_completion.py
tests/test_outlook_mail_full_enrichment.py
tests/test_outlook_mail_profile_ownership.py
tests/test_mail_pipeline_cancellation.py
tests/test_raw_evidence_pipeline.py
tests/test_raw_evidence_transactions.py
tests/test_raw_evidence_cancellation.py
tests/test_evidence_concurrent_blob.py
tests/test_evidence_link_pipeline.py
```

### Saved-source reader selection

```text
tests/source_reader/test_authority_release_roundtrip.py
tests/source_reader/test_calendar_release_attachment_metadata_shape.py
tests/source_reader/test_calendar_release_reader.py
tests/source_reader/test_evidence_error_types.py
tests/source_reader/test_handoff_catalog.py
tests/source_reader/test_inbound_evidence.py
tests/source_reader/test_mail_release_adversarial.py
tests/source_reader/test_mail_release_components.py
tests/source_reader/test_mail_release_integrity.py
tests/source_reader/test_mail_release_pagination.py
tests/source_reader/test_malformed_delta_reference.py
tests/source_reader/test_nonmail_release_components.py
tests/source_reader/test_nonmail_release_integrity.py
tests/source_reader/test_nonmail_release_observations.py
tests/source_reader/test_onedrive_release_metadata_shape.py
tests/source_reader/test_platform_pinning_boundary.py
tests/source_reader/test_release_aware_nonmail.py
tests/source_reader/test_release_aware_reader.py
tests/source_reader/test_release_terminal_metadata.py
tests/source_reader/test_saved_source_reader.py
tests/source_reader/test_saved_source_reader_r2.py
tests/source_reader/test_saved_source_reader_r3.py
tests/source_reader/test_selection_semantic_persistence.py
```

## Local commit

The requested local commit could not be created. After validation, `git add`
failed with exit code 128:

```text
fatal: Unable to create '/home/grammy-jiang/Projects/msgloom/.git/worktrees/task15-authority-provisional-20261015/index.lock': Read-only file system
```

The worktree's Git metadata is outside the writable sandbox. No commit was
claimed or fabricated. The branch remains at the supplied baseline. All changes
remain available in this worktree. No push, PR, merge, deletion, or other branch
operation was performed.
