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
   the coverage proof binds. Then each accepted stage is verified from the
   database (see "Durable recheck" below). No payload, semantic-data or body
   is read.
5. `UPDATE` the legacy row, read the row back (still inside the transaction),
   write the receipt proof file, `COMMIT`.

Written columns: `state='terminal'`, `terminal_status` (receipt status),
`result_refs` (root results in order, then the batch result),
`terminal_claim_token` (the claim token SHA-256, never the raw token),
`terminal_execution_id`, `terminal_attempt_id`.

## Durable recheck

For every accepted stage the receipt names, in the lock, from metadata only
(`phase1_stage_results`, `phase1_a2_accepted_stages`, `phase1_a2_claims`,
`phase1_a2_stage_attempts`; never `phase1_semantic_data`):

| Check | Reason code on failure |
| --- | --- |
| Saved `StageResult` row exists | `stage-result-missing` |
| Row decodes and is an acceptable stage | `stage-result-corrupt` |
| Row kind/version equal the record; writer execution and attempt equal the record writer | `stage-result-mismatch`, `stage-result-writer-mismatch` |
| Canonical SHA, length and semantic data id from the stored `semantic_data_ref` equal the record | `stage-result-mismatch` |
| Stage metadata SHA, lineage digest, status and limitations digest, recomputed from the saved row, equal the record | `stage-result-mismatch` |
| Accepted-stage columns (SHA, length, data id, metadata SHA, lineage, limitations digest) equal the record | `accepted-columns-mismatch` |
| Claim row at `writer_claim_seq` exists and equals the record writer (key, execution, attempt, token SHA-256) | `publish-claim-missing`, `publish-claim-mismatch` |
| That claim has an `inserted` row for the key in `phase1_a2_stage_attempts` | `publish-attempt-missing` |
| Receipt status equals the record status (coverage proof) | `accepted-result-mismatch` |

A stage may come from an earlier attempt. The old same-attempt rule of v1 is
not applied. Each stage carries its own original publication proof, and the
publishing claim may be released.

The canonical SHA comes from the `semantic_data_ref` text column of
`phase1_stage_results`. That column is metadata. It is not the
`phase1_semantic_data` table. The SHA of the stored payload bytes is not
recomputed here.

### Limits of the recheck (no stored metadata to compare)

1. The input-only accepted key is not recomputed. Recomputing needs the frozen
   `StageIdentity` (the plan). Schema 5 stores no plan, and the request does
   not carry one. The check is limited to key equality between the receipt,
   the accepted record and the saved result row.
2. "Published plan" is not checked, for the same reason. The lineage digest
   is compared with the saved row's `input_refs`, not with a stored plan.
   Required inputs are not rechecked at finalize time.
3. The payload SHA and byte count in `phase1_semantic_data` are not compared
   with the stored `semantic_data_ref`. That table is a payload table, and the
   task forbids reading it.
4. The receipt carries a status but no limitations. Limitations are compared
   between the saved result and the accepted record (digest), not against the
   receipt.
5. The attempt history is the SQL `phase1_a2_stage_attempts` table. The
   file-based claim history of `ReceiptStore` is not cross-checked with SQL
   (decision 6 below).

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
the `UPDATE` and the read-back, and before `COMMIT`. A failure before
`COMMIT` rolls back SQL. The read-back runs before the file write, so a
mismatch leaves no orphan proof file.
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
