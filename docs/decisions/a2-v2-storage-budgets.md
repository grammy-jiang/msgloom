# A2 v2 intermediate-stage storage budget and retention (C0-22)

Status: PROVISIONAL. Research only. Every number is a proposal until the
owner and the security reviewer approve it. This record changes no database.

Code: `msgloom/persistence/a2_stage_budgets.py` and the `a2_*` stores.
Tests: `tests/persistence/test_a2_stage_budgets.py`. The test parses the
tables below. It fails when a name or a value differs from the code.
Detail and reasons: `docs/notes/a2-v2-db-storage-budgets.md`.

## Decision

- Every stored A2 artifact has a finite byte limit and a finite entry limit.
- A limit is "enforced" only when code refuses limit + 1. Section "Not
  enforced yet" lists the rest. Do not read a policy value as enforcement.
- `check_artifact` in `a2_stage_budgets.py` is pure. No store calls it yet.

## Budgets that exist in code

| Name | Value | Enforced at | Tested by |
| --- | --- | --- | --- |
| `a2_acceptance_models.MAX_PAYLOAD_BYTES` | 67108864 | `a2_schema.py` CHECK on `canonical_byte_count`; `AcceptedStage.canonical_byte_count` | `test_accepted_stage_bytes_at_limit_and_over` |
| `a2_acceptance_models.MAX_RECORD_BYTES` | 16384 | `a2_schema.py` CHECK on `record_json`; `AcceptedStage.record_bytes` | `test_accepted_stage_bytes_at_limit_and_over` |
| `a2_held_store.MAX_HELD_RECORD_BYTES` | 8192 | `a2_held_store.py:DDL` CHECK; `_stored` | `test_held_bytes_and_rows_at_limit_and_over` |
| `a2_held_store.DDL.workset_index_max` | 1023 | `a2_held_store.py:DDL` CHECK (a literal, no constant) | `test_held_bytes_and_rows_at_limit_and_over` |
| `a2_held_store.MAX_BATCH` | 1024 | `a2_held_store.py:put_many` | `test_held_batch_and_page_at_limit_and_over` |
| `a2_held_store.MAX_LIMIT` | 500 | `a2_held_store.py:list_held` | `test_held_batch_and_page_at_limit_and_over` |
| `a2_sqlite_store.MAX_RECEIPT_BYTES` | 1048576 | `a2_sqlite_ddl.py` CHECK `receipt_json`; `a2_sqlite_store.py` `canonical_model_bytes` | `test_research_bytes_at_limit_and_over` |
| `a2_sqlite_ddl.record_json_max` | 16384 | `a2_sqlite_ddl.py` CHECK on `record_json` (literal) | `test_research_bytes_at_limit_and_over` |
| `a2_receipt_store.MAX_COVERAGE_ITEMS` | 2048 | `a2_receipt_store.py:ReceiptProof` field and `check_structure` | `tests/a2_kedro/test_c0_14a.py` |
| `a2_receipt_store.MAX_PROOF_BYTES` | 1048576 | `a2_receipt_store.py:_canonical`, `read_bounded` | `tests/a2_kedro/test_c0_14a.py` |
| `a2_receipt_store.MAX_CLAIMS` | 256 | `a2_receipt_store.py:append_claim`, `claim_history` | `tests/a2_kedro/test_c0_14a.py` |
| `a2_receipt_store.MAX_CLAIM_BYTES` | 8192 | `a2_receipt_store.py:_canonical`, `read_bounded` | `tests/a2_kedro/test_c0_14a.py` |
| `a2_stage_budgets.DEFAULT_POLICY.max_entries_per_workset` | 16384 | `a2_stage_budgets.py:check_artifact` (pure, not wired) | `test_policy_limits_at_limit_and_over` |
| `a2_stage_budgets.DEFAULT_POLICY.max_bytes_per_workset` | 536870912 | `a2_stage_budgets.py:check_artifact` (pure, not wired) | `test_policy_limits_at_limit_and_over` |
| `a2_stage_budgets.MAX_RETENTION_DAYS` | 3650 | `a2_stage_budgets.py:ArtifactBudget` | `test_policy_limits_at_limit_and_over` |

The receipt store tests refuse limit + 1. They do not all prove acceptance
at the limit. This record does not claim more.

## Per-kind policy (artifact bytes and retention days)

`check_artifact` enforces `max_payload_bytes` for each kind. It refuses one
byte over the limit with `payload-too-large`. `retention_action` reads the
two day counts. No store or job calls either function yet.

| Kind | max_payload_bytes | payload_days | digest_days |
| --- | --- | --- | --- |
| `frozen_source_selection` | 4194304 | 30 | 365 |
| `extracted_components` | 67108864 | 14 | 365 |
| `parsed_parts` | 67108864 | 14 | 365 |
| `normalized_content` | 67108864 | 14 | 365 |
| `zones` | 16777216 | 14 | 365 |
| `native_relations` | 16777216 | 14 | 365 |
| `prepared` | 67108864 | 30 | 365 |
| `filter_result` | 4194304 | 30 | 365 |
| `group_result` | 4194304 | 30 | 365 |
| `prepared_transitions` | 16777216 | 30 | 365 |
| `a2_input_disposition` | 8192 | 90 | 730 |
| `a2_result_manifest` | 1048576 | 90 | 730 |

Tests: `test_policy_limits_at_limit_and_over` and
`test_retention_boundaries_for_every_kind`.

## Retention rules

- Before `payload_days`: keep the payload and the digest.
- From `payload_days` to `digest_days`: keep digest-only metadata (SHA-256,
  byte count, status, lineage). Drop the payload.
- From `digest_days`: delete the entry. The owner has not yet decided
  whether this applies to accepted-stage rows. Deleting one removes the
  proof that `decide_append_or_verify` compares against.
- The digest outlives the payload. `ArtifactBudget` enforces this.
- Schema 4 rows and read-only historical stage versions are not measured,
  dropped or deleted by this policy.
- A lower limit later applies to new writes only. It never deletes rows.

## PII rules

- Logs, status output and errors carry counts, sizes, kinds and closed reason
  codes. They carry no message body, address, subject or file name.
- Budget errors hold the reason code only. Tests use a canary value.
- Backups can hold payloads. A backup is PII storage.

## File permissions

- Staging DB file: mode 0600. Staging DB directory: mode 0700. Enforced by
  `Phase1Store.__init__` (`store.py`, protected) and tested.
- Backup file: mode 0600, created with `O_EXCL` in
  `a2_schema_migration.py:_write_backup`. Tested.
- Receipt store files: mode 0600 in `a2_receipt_io.py:create_once`. Tested.

## Single-writer rule

- One writer per database file. Every A2 write runs in `BEGIN IMMEDIATE`
  (`a2_store.py:_immediate`, `a2_held_store.py:_immediate`,
  `a2_sqlite_store.py:_immediate`).
- A second writer waits up to `BUSY_TIMEOUT_SECONDS` (10.0). Then
  `accept_result` raises `A2AcceptError("lock-failed")`.
- Test: `test_second_writer_is_refused_while_the_first_holds_the_lock`.
- A budget check must run inside the same transaction as the insert. A
  check outside it is advisory.

## Compatibility rule

- A schema 4 reader refuses schema 5. `Phase1Store` raises
  `IncompatibleSchemaError`. The file stays unchanged.
- A schema 5 reader opens recorded schema 4 history unchanged. Migration adds
  tables and metadata. It keeps every schema 4 table definition and row.
- `require_schema5` refuses a schema 4 file with `migration-required`.
- Tests: `test_schema4_reader_refuses_schema5_and_leaves_it_unchanged` and
  `test_migration_keeps_recorded_schema4_history`.

## Not enforced yet

Each item is a known gap. The test file checks that this list names it.

- GAP-WORKSET-COUNT: schema 5 `phase1_a2_accepted_stages` has no workset
  column. No code limits accepted entries per workset. Task: C0-12c wiring
  and a schema revision.
- GAP-WORKSET-BYTES: no code sums payload bytes per workset. Task: C0-12c.
- GAP-KIND-LIMITS: `accept_result` takes no policy. Per-kind caps below
  64 MiB are not applied. Only the global `MAX_PAYLOAD_BYTES` CHECK holds.
  Task: C0-12c.
- GAP-RETENTION-JOB: no job applies `retention_action`. Nothing is dropped
  or deleted. Task: C0-20c.
- GAP-WORKSET-COUNT-GLOBAL: the number of worksets and the total disk use
  have no limit. Task: C0-20c.
- GAP-RESEARCH-STORE-MODE: `A2ResearchStore.create` sets no file mode. The
  mode follows the umask. Task: C0-13a.
- GAP-BACKUP-DIR-MODE: `create_backup` does not create or change the backup
  directory. Task: C0-11c (operator CLI must create it with mode 0700).
- GAP-BACKUP-RETENTION: no rule or job removes old backups. Task: C0-11c.
- GAP-RECEIPT-DIR-MODE: `ReceiptStore._directory` creates directories with the umask
  mode. Task: C0-14a follow-up.
- GAP-HISTORICAL-VERSION: `check_artifact` takes no schema version. The
  `@1` refusal comes from `require_stage_schema`, not from this policy.
  Task: C0-12c.
- GAP-RECORD-JSON-BYTES: `record_json` (up to 16384 bytes per accepted row)
  and the attempt and claim tables are outside the workset byte budget.
  Task: C0-12c.
