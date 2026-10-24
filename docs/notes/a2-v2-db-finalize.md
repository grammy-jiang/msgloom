# A2 v2 Workset finalizer (C0-14b): PROVISIONAL / RESEARCH

Status: PROVISIONAL. Research only. `intake_completion.py` and every A1 file
are unchanged. Tests use `tmp_path` SQLite only.

Module: `msgloom/persistence/a2_workset_finalize.py`.
Entry point: `finalize_a2_intake_workset_v2(db, store, request)`.

## What one call does

One `BEGIN IMMEDIATE` transaction on a caller-owned autocommit connection:

1. Pure checks first: the receipt covers the frozen Workset
   (`CompletionReceipt.validate_against`) and the publisher proof names
   `workset_claim_key(result_id)`.
2. Exact schema 5, no legacy recovery hold, Workset stage result present
   (kind and version only), row scope and cutoff equal the Workset.
3. Row `pending` and the proof is the live claim in `phase1_a2_claims`.
4. Metadata recheck: every receipt result is an accepted-stage record that
   the coverage proof binds. No payload, semantic-data or body is read.
5. `UPDATE` the legacy row, write the receipt proof file, read the row back,
   `COMMIT`.

Written columns: `state='terminal'`, `terminal_status` (receipt status),
`result_refs` (root results in order, then the batch result),
`terminal_claim_token` (the claim token SHA-256, never the raw token),
`terminal_execution_id`, `terminal_attempt_id`.

## Outcomes

| Case | Result |
| --- | --- |
| Pending, all checks pass | `finalized` |
| Terminal with identical values and identical proof | `replayed`, no change |
| Terminal with other values (also a v1-terminal row) | `A2FinalizeConflict`, field names only |
| Same values, other receipt proof | `A2ReceiptConflict` |
| Any other refusal | `A2FinalizeError` or `A2ReceiptError`, fixed reason code |

After every refusal the row, the A2 tables and the proof directory are
unchanged. The v1 finalizer already refuses a terminal row whose values
differ from its own, so a v2-terminal row cannot be finished again by v1.

## Atomicity limit

SQLite cannot roll back a file. The write-once proof file is written after
the `UPDATE` and before `COMMIT`. A failure before `COMMIT` rolls back SQL.
A proof file written before a failed `COMMIT` stays as an orphan. A retry of
the same receipt replays it. A different receipt raises `A2ReceiptConflict`
and the row stays pending. A terminal row always has a proof file.

## Decisions taken conservatively (open questions)

1. No table or column was added. Schema 5 has none for the receipt, and
   `classify_schema` refuses any unreviewed `phase1_*` table. The receipt
   proof stays in `ReceiptStore` files. Moving it into SQL needs a schema
   revision owned by `a2_schema.py`.
2. The receipt digest is not stored in SQL, so the SQL row alone does not
   bind the proof file. A removed proof file is repaired on replay.
3. `terminal_claim_token` holds the claim token SHA-256 (a v2 value). The
   v1 column held the raw token.
4. `intake_completion.py` was not edited. Its v1 proof cannot check a v2
   receipt, and the architecture rule "v1 refuses a v2-marked Workset" is
   the producer binding of C0-14c, not this task.
5. The caller loads the frozen `PreparationIntakeWorkset` before the lock.
   The lock binds it to the row by scope and cutoff, not by payload bytes.
   Equality with the stored semantic payload is not rechecked in the lock,
   because that would read a payload.
6. The claim history head is not cross-checked with the SQL claim table.
7. A held-only receipt (no roots, no batch) finalizes as INCOMPLETE.
8. Status names are the `TerminalStatus` values `complete` and `incomplete`.
