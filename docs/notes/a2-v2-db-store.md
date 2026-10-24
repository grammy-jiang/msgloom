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
