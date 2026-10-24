# A2 v2 receipt store (C0-14a): PROVISIONAL / RESEARCH

Status: PROVISIONAL. Every wire name, file name, domain string and limit is
provisional until the C0 schema review freezes it. The module changes no
database and no protected file. Tests use `tmp_path` only.

Module: `msgloom/persistence/a2_receipt_store.py`.

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

## Bounds (provisional)

2048 coverage items, 1 MiB for a proof, 256 claims, 8 KiB for a claim. A
bound failure raises `A2ReceiptBoundError`. No value is clamped.

## Open items

- Files are not covered by the SQL transaction. A finalizer must write the
  proof first, then commit SQL that stores the proof digest. This ordering
  is not implemented here.
- Only the file is fsynced. The directory entry is not fsynced.
- No cross-process lock beyond the `os.link` race rule. Needs a local POSIX
  file system.
- Leftover `.tmp-*` files from a hard crash are ignored, never removed.
- Claim entries are not checked against the SQL claim table.
