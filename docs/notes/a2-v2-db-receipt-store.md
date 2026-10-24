# A2 v2 receipt store (C0-14a): PROVISIONAL / RESEARCH

Status: PROVISIONAL. Every wire name, file name, domain string and limit is
provisional until the C0 schema review freezes it. The module changes no
database and no protected file. Tests use `tmp_path` only.

Modules: `msgloom/persistence/a2_receipt_store.py` (store and proof logic),
`a2_receipt_io.py` (file helpers) and `a2_receipt_errors.py` (error types).

## What it stores, outside SQL

Schema 5 has no column for the receipt proof or the claim history. The store
keeps both as write-once files in a caller-owned directory. One directory
exists for each workset ref. Its name is a SHA-256 digest.

| File | Content |
| --- | --- |
| `receipt-proof.json` | One `ReceiptProof`: workset, receipt digest, policy version, ordered `CoverageItem` list, self digest. |
| `claim-NNNNN.json` | One hash-chained `StoredClaim` (the publisher's raw claim event). |

## Coverage rules

Order: `root` items (or `baseline` items) by position, then `transition`
items by position. A root or baseline digest is the accepted-stage
`record_sha256()`. A transition digest binds the accepted batch record, the
position and the exact transition. `verify_receipt_proof` rebuilds the
expected proof and refuses a missing, extra, duplicate, out-of-order or
altered item with a fixed reason code.

## Claim history

`append_claim(workset, entry, expected_seq)` is the only writer. The same
entry at a stored sequence replays. A different entry raises
`A2ReceiptConflict` (`claim-history-rewrite`). A gap or a broken chain fails
closed. There is no update or delete function.

### Head anchor

The hash chain proves that the stored claims are in order. It does NOT prove
that no claim was removed from the end. Without an anchor from the SQL claim
table, tail truncation and rollback are NOT detectable. Deleting
`claim-00002.json` leaves a valid chain of two claims, and a different entry
can then be appended at sequence 2.

`claim_history` and `append_claim` accept the keyword
`expected_head_sha256`. It is the `entry_sha256` of the newest claim, or
`GENESIS` (64 zeros) for an empty history. A different stored head raises
`A2ReceiptError` with reason `claim-head-mismatch`. This also catches a
removed tail and an empty history. `append_claim` checks the anchor against
the stored head before the call changes anything. After an append, the new
head is the `entry_sha256` of the new claim. Without the keyword, behavior
is as before. The SQL cross-check that supplies the anchor is a later task.
This store does not implement it.

## Write rules

A file is written in full with a loop over `os.write`. The byte count and
the file size are checked before `os.link` publishes the file. A short write,
a zero write or an error removes the temporary file and raises
`write-failed`. No final file exists after such a failure. The directory is
flushed with `fsync` after `os.link` and after `mkdir`. A directory `fsync`
error raises `write-failed`. The complete file can remain. A retry of
`put_receipt_proof` or `append_claim` flushes the directory again before it
reports `replayed`. If that flush fails, the retry raises `write-failed` and
never reports `replayed`. On Windows a directory
cannot be opened for `fsync`. There the flush is skipped, and a new name is
not guaranteed durable. Reads loop until end of file or the limit plus one
byte. Reads open files with `O_NOFOLLOW` and `O_NONBLOCK` (where the
platform has them). A symlink, a FIFO or another non-regular file raises
`read-failed` and does not block. An oversize payload raises
`A2ReceiptBoundError`.

## Read rules

`get_receipt_proof` checks only the self digest of the proof. It does not
compare the proof with a receipt. A caller must run `verify_receipt_proof`
with the receipt and the accepted-stage records.

## Bounds (provisional)

2048 coverage items, 1 MiB for a proof, 256 claims, 8 KiB for a claim. A
bound failure raises `A2ReceiptBoundError`. No value is clamped.

## Open items

- Files are not covered by the SQL transaction. A finalizer must write the
  proof first, then commit SQL that stores the proof digest. This ordering
  is not implemented here.
- A removed tail of the claim history is detectable only with an anchor from
  the SQL claim table (see "Head anchor"). A removed proof file is not
  detectable by the store alone. A proof anchor is not implemented.
- No cross-process lock beyond the `os.link` race rule. Needs a local POSIX
  file system.
- Leftover `.tmp-*` files from a hard crash are ignored, never removed.
- Claim entries are not checked against the SQL claim table.
