# A2 v2 intermediate-stage storage budget and retention (C0-22)

Status: PROVISIONAL. Research only. This note adds a pure policy module.
It changes no database and no store.

Location note: the manifest names `docs/decisions/a2-v2-storage-budgets.md`.
That path is outside the allowlist of this stage. This note lives under
`docs/notes/` instead. Move it when the owner approves the decision.

Code: `msgloom/persistence/a2_stage_budgets.py`.
Tests: `tests/persistence/test_a2_stage_budgets.py`.

Every value marked `PROPOSED_NEEDS_OWNER` is a proposal. The owner must
approve it before any store enforces it. The blueprint (section 6.2) says
that a performance number is acceptance data, not a fixed magic value.
Measure on the Pi before you accept a proposal.

## 1. What the policy does

- `StageBudgetPolicy` is a frozen dataclass. `ArtifactBudget` is one row.
- `check_artifact(kind, size_bytes, entries_in_workset, bytes_in_workset)`
  raises `A2BudgetExceeded` when a limit is passed. The two counts are the
  values before the new artifact. The check tests the totals after adding it.
- `retention_action(kind, age_days)` returns `KEEP`,
  `DROP_PAYLOAD_KEEP_DIGEST` or `DELETE`.
- `A2BudgetExceeded` and `A2BudgetConfigError` extend `A2StageBudgetError`.
  That class extends `A2ContractError`, the error type of the A2 contracts.
  Errors carry a closed reason code only.
- The constructors reject zero, negative, non-integer, unbounded and
  inconsistent values. A missing kind is refused, because a missing kind
  would mean "unlimited". An artifact limit above the workset byte limit is
  refused. A payload limit above `MAX_PAYLOAD_BYTES` is refused.

## 2. Limits and reasons

Existing constants are reused. Nothing parallel is invented.

| Limit | Value | Reason |
| --- | --- | --- |
| Hard ceiling per artifact | `MAX_PAYLOAD_BYTES` = 64 MiB (`a2_acceptance_models.py`) | Schema 5 CHECK on `canonical_byte_count` and the `AcceptedStage` model already use it. No kind may exceed it. |
| `frozen_source_selection`, `filter_result`, `group_result` | `MAX_CANONICAL_BYTES` = 4 MiB (`contracts/codec.py`) | Default bound for one canonical contract payload. |
| `a2_input_disposition` | `MAX_HELD_RECORD_BYTES` = 8 KiB (`a2_held_store.py`) | A held record is one small row. |
| `a2_result_manifest` | `MAX_RECEIPT_BYTES` = 1 MiB (`a2_sqlite_store.py`) | Matches the receipt cap. |
| `extracted_components`, `parsed_parts`, `normalized_content`, `prepared` | 64 MiB (`MAX_PAYLOAD_BYTES`) | These hold parser output. They need the full ceiling. `PROPOSED_NEEDS_OWNER`: measure real parser output first. |
| `zones`, `native_relations`, `prepared_transitions` | 16 MiB | `PROPOSED_NEEDS_OWNER`. Derived from parsed content. Lower than the parser output on purpose. |
| `max_entries_per_workset` | 16384 | `PROPOSED_NEEDS_OWNER`. A workset has at most 1024 roots (`Ordinal` le 1023 in `identity.py`). 12 kinds times 1024 roots is 12288 at most. 16384 leaves a margin. |
| `max_bytes_per_workset` | 512 MiB | `PROPOSED_NEEDS_OWNER`. Bounds one workset on a 16 GB Pi. It is far below the 1 TB disk and below what 1024 maximum artifacts could reach. A real workset is expected to use much less. |

The limits fit the blueprint rule in section 6.2: every A2 stage payload
and every workset aggregate has a bytes cap and a count cap. The queryable
index for these caps is a schema matter and stays deferred (section 8).

## 3. Retention classes

Each kind has two ages in whole days.

| Class | Meaning |
| --- | --- |
| `KEEP` | Age below `payload_days`. Keep the payload and the digest. |
| `DROP_PAYLOAD_KEEP_DIGEST` | Age from `payload_days` to below `digest_days`. Keep only the digest-only metadata (SHA-256, byte count, status, lineage). |
| `DELETE` | Age of `digest_days` or more. Delete the entry. |

Proposed ages (`PROPOSED_NEEDS_OWNER`, all of them):

| Kinds | `payload_days` | `digest_days` |
| --- | --- | --- |
| `extracted_components`, `parsed_parts`, `normalized_content`, `zones`, `native_relations` | 14 | 365 |
| `frozen_source_selection`, `prepared`, `filter_result`, `group_result`, `prepared_transitions` | 30 | 365 |
| `a2_input_disposition`, `a2_result_manifest` | 90 | 730 |

Rules:

- `digest_days` must be greater than `payload_days`. The digest outlives the
  payload. The constructor enforces this.
- Both ages are at most 3650 days, so no age is unbounded.
- The function is pure. A later job must apply the action. No job exists.
- Warning for the owner: `DELETE` of an accepted-stage row removes the
  proof that `decide_append_or_verify` compares against. After a delete, the
  same logical key could be accepted again with different content. The owner
  must decide whether `DELETE` applies to accepted rows or only to payload
  and attempt rows. Until then, treat `DELETE` as a proposal.
- The schema 5 accepted-stage row has no raw payload column
  (`a2_store.py`). The payload lives in the semantic store. So
  `DROP_PAYLOAD_KEEP_DIGEST` means: drop the semantic payload, keep the
  accepted-stage record.

## 4. Single-writer rule

One writer at a time per database file. The existing code enforces it in
SQLite, not in this module:

- `a2_store.accept_result` runs every write in one `BEGIN IMMEDIATE`
  transaction (`a2_store.py`, `_immediate`). SQLite allows one such
  transaction at a time, so a second writer waits or fails.
- `a2_sqlite_store.py` uses the same rule. Its connection has a busy timeout
  `BUSY_TIMEOUT_SECONDS` = 10.0, and one instance owns one connection.
- Blueprint section 6.1: one recorded owner runner worker per workset. A new
  admission is refused until the previous worker is joined.

Budget rule: the budget check and the insert must run in the same
`BEGIN IMMEDIATE` transaction. Then the counts cannot change between the
check and the write. The caller reads `entries_in_workset` and
`bytes_in_workset` from trusted columns inside that transaction. It does
not decode large payloads under the lock (blueprint section 6.2). A check
outside the transaction is advisory only.

## 5. Backup file permissions

Rule: backup file mode 0600. Backup directory mode 0700.

- File mode 0600 is already enforced. `create_backup` creates the file
  with `O_EXCL` and mode `0o600` (`a2_schema_migration.py`). The test
  `tests/persistence/test_a2_schema_migrations.py` checks that no group or
  other bit is set. This stage adds no new test for it.
- Directory mode 0700 is enforced only for the database directory, by
  `Phase1Store` (`store.py`, `os.chmod(path.parent, 0o700)`). The backup
  directory is created by the caller. `create_backup` requires that it
  exists and does not change its mode. The operator CLI (C0-11c, not built)
  must create the backup directory with mode 0700. This stage only
  documents the rule.
- A `DROP_PAYLOAD_KEEP_DIGEST` or `DELETE` action does not reach backups.
  A backup keeps old payloads. The owner must decide the backup retention
  age. `PROPOSED_NEEDS_OWNER`: delete a backup when the newest backup is
  older than the longest `payload_days`, and the owner has confirmed the
  restore.

## 6. PII retention

- Status, log and error output carries counts, sizes, kinds and closed
  reason codes only. It carries no message body, address, subject or
  filename. The error classes in the module hold a reason code and nothing
  else. The tests check that the message equals the reason code.
- `retention_action` takes only a kind and an age. It cannot read content.
- After `payload_days`, only digest-only metadata remains. A digest is a
  SHA-256 and does not reveal content. Names and addresses are not part of
  the kept metadata.
- Backups can still hold payloads (section 5). A backup is therefore PII
  storage. It follows the 0600/0700 rule and its own retention age.
- `PROPOSED_NEEDS_OWNER`: the 14 and 30 day payload ages are a privacy
  decision, not only a size decision.

## 7. Compatibility with schema 4 history

- This stage runs no migration and edits no table.
- The policy applies to new A2 v2 stages only. It has an entry for each kind
  in `STAGE_SCHEMAS`.
- Schema 4 rows (`phase1_*` tables) are not stage artifacts. The policy never
  measures, drops or deletes them. They stay readable through the existing
  stores.
- The read-only historical stage versions in `HISTORICAL_READ_ONLY`
  (`prepared@1`, `filter_result@1`, `group_result@1`) have no budget row.
  `check_artifact` refuses writes for them with `unknown-kind`. Reading them
  is unaffected, because the module has no read path.
- Raising or lowering a limit later affects new writes only. An existing
  workset above a new, lower limit stays readable. A lower limit must never
  trigger a delete by itself.

## 8. Deferred integration

No existing A2 store function accepts an injected policy. `accept_result`
in `a2_store.py` and the writers in `a2_sqlite_store.py` and
`a2_held_store.py` take no budget parameter. Wiring needs a store edit. So
this stage adds no store test. The following work is deferred:

1. Add an optional `policy` parameter to `accept_result` (and the research
   store writer). Call `check_artifact` inside the `BEGIN IMMEDIATE`
   transaction before the insert.
2. Add a bounded, indexed way to read `entries_in_workset` and
   `bytes_in_workset` (counts and sums over `phase1_a2_accepted_stages`
   for one workset). This may need a schema revision and an index.
3. Add a retention job that applies `retention_action` and writes the
   result as a bounded status record without content.
4. Decide the `DELETE` rule for accepted rows (section 3).
5. Decide the backup retention rule and create the backup directory with
   mode 0700 in the C0-11c CLI (section 5).
6. Measure real parser output on the Pi to confirm or replace the proposed
   limits. Use the exclusive benchmark slot from blueprint section 6.2.

## 9. Owner approval list

All of these are `PROPOSED_NEEDS_OWNER`:

- Per-kind payload caps that have no existing constant: 16 MiB for `zones`,
  `native_relations` and `prepared_transitions`. The 64 MiB caps for the four
  parser-output kinds reuse the ceiling but still need confirmation.
- `max_entries_per_workset` = 16384.
- `max_bytes_per_workset` = 512 MiB.
- All `payload_days` and `digest_days` values in section 3.
- Whether `DELETE` applies to accepted-stage rows.
- The backup retention age and the 0700 backup directory rule.
