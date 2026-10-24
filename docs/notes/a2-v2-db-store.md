# A2 v2 guarded stores (C0-12b and C0-13): PROVISIONAL / RESEARCH

Status: PROVISIONAL. Research only. This note describes two store modules.
It changes no database and no A1 file. Tests use `tmp_path` SQLite only.

Supervisor override: the manifest names `tests/a2_kedro/test_c0_12b.py` and
`tests/a2_kedro/test_c0_13.py`. The tests live in
`tests/persistence/test_a2_store.py` and
`tests/persistence/test_a2_held_store.py` instead.

## C0-12b: `msgloom/persistence/a2_store.py`

`accept_result(db, identity, receipt)` is the one writer of
`phase1_a2_accepted_stages`. It reuses `a2_schema` (tables, `require_schema5`,
claims), `a2_acceptance_models` (record and append-or-verify rule) and
`a2_txn.rollback_quietly`. It adds no table and edits no existing file.

### Steps in one `BEGIN IMMEDIATE` transaction

1. Pure checks run first, with no lock: the receipt binding and the plan.
2. `require_schema5`: the file must be exactly schema 5.
3. Live claim: `phase1_a2_claims` must hold a `live` row for the claim key
   of the publisher proof. Execution, attempt and token digest must match.
4. Required inputs: each upstream ref of the frozen plan must be an
   accepted stage with the same kind and version.
5. Append or verify under the single primary key `logical_key`.
6. The live claim is checked again, then `COMMIT`.

### Receipt binding and plan

`PublisherReceipt` holds the raw `StageResult` as the publisher saved it and
the publisher `AttemptProof`. The proof must name the execution and attempt
of the result. The result must match the frozen `StageIdentity` (the plan):
key, kind, version, upstream refs, configuration and code version. The
stored `writer` is the publisher proof. `writer_claim_seq` is the live claim.

### Outcomes

| Case | Result |
| --- | --- |
| New key | Row inserted, attempt `inserted`. |
| Same key, same integrity fields | Stored row returned, attempt `replayed`. |
| Same key, other integrity fields | Attempt `conflict` committed, then `AcceptanceConflict` (field names only). |
| Claim released | `A2AcceptError("claim-not-live")`. |
| Claim held by another proof | `A2AcceptError("claim-foreign")`. |
| Missing or wrong-kind input | `required-input-missing` or `required-input-mismatch`. |
| Bad binding or plan | `receipt-binding-mismatch` or `plan-mismatch`. |

Every failure, including a failed `COMMIT` and a `BaseException`, rolls the
transaction back. Messages are short reason codes. They carry no path, key,
token, row value or SQL text. The raw database error never chains.

### TOCTOU

The claim is read only inside the write lock. A claim change before
`BEGIN IMMEDIATE` is seen by the check and refused. After the lock, a second
connection cannot write the claim table until `COMMIT`. Tests cover both
cases with a hooked connection and a second real connection.

### Open items (C0-12b)

- The schema has no column for the raw `StageResult` or a publisher plan
  row. The binding is held by `writer`, `writer_claim_seq` and the attempt
  row. A table for the raw receipt needs a schema revision (owner:
  `a2_schema.py`).
- The claim table has no lease or expiry column. "Expired" means
  `released` today. A lease needs a schema revision.
- The claim key is not tied to a workset or plan in the schema. A binding
  between claim key and workset needs a schema revision.
- Stored semantic-data bytes are not compared with `canonical_sha256`.
  Upstream reachability beyond the direct refs is not checked.
- The async facade (C0-12c) and old store hooks are later steps.

## C0-13: `msgloom/persistence/a2_held_store.py`

The held index stores `InputDisposition` records
(`msgloom.a2_kedro.contracts.held`, importable in this branch). It binds to
that contract directly. No local row dataclass replaces it. `HeldRow` is
only a read view of closed columns.

### Table and schema integration (pending)

Schema 5 has no held-index table. `a2_schema.py` stays unchanged. The table
`a2_held_index_pending` is created only by the explicit, idempotent
`ensure_held_index(db)`. No store function creates it. A missing table
raises `held-index-missing`. A table that differs from the pinned DDL
raises `held-index-definition-mismatch`.

Safety rules of `ensure_held_index`:

- A file with any `phase1_*` table is refused (`phase1-database-refused`).
- With `pending_integration_ack=True`, the file must be exact schema 5.
- The table name has no `phase1_` prefix. `classify_schema` still returns
  schema 5 after creation. A test checks this on a `tmp_path` file.
- The function is not called by any open or migration path.

### Queries and writes

| Function | Contract |
| --- | --- |
| `put_held` / `put_many` | Idempotent. Identical replay returns `replayed`. A batch holds 1 to 1024 records and is all or nothing. |
| `list_held` | Takes a workset ref, a required `limit` (1 to 500, never clamped) and an optional `HeldCursor`. Orders by `workset_index`. Reads `limit + 1` rows to find the next cursor. A cursor of another workset is refused. |
| `get_held` | Returns the digest-verified `InputDisposition` of one index. |
| `held_status` | Counts by closed reason and repair class, plus baseline and incremental counts. At most 10 groups. |

Conflict rule: one primary key `(workset_id, workset_index)` and one unique
key `(workset_id, selected_id)`. A different record at the same index, or
the same selection at another index, raises `A2HeldConflict` with field
names only. The stored row never changes.

Privacy: `held_status` selects only `reason`, `repair_class`, the baseline
flag and a count. It never reads `record_json`. `list_held` rows carry no
version text and no approval text. A test puts a canary string in every
free-text field and checks that no query result or error shows it.

### Open items (C0-13)

- Move the table into `a2_schema.py` as a reviewed schema revision, with a
  foreign key to the workset and the migration test matrix. Until then the
  index is not part of the pinned schema 5 definition.
- Link held rows to the accepted-stage proof of the held record
  (`a2_input_disposition@1` is an accepted stage kind). Today the index
  stores the record but does not check that an accepted stage exists.
- The async facade (C0-13a) and the receipt store (C0-14a) are later steps.
- Intake-held entries are frozen by Intake. They are not in this index.
