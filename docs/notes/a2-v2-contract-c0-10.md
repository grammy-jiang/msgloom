# A2 v2 contract C0-10: a2_completion_receipt@2 (PROVISIONAL)

Code: `msgloom/a2_kedro/contracts/receipt.py`.
Tests: `tests/a2_kedro/test_c0_10.py` (older cases stay in
`tests/a2_kedro/test_held_receipt.py` and `test_c0_09.py`).

The receipt proves structure only. It reads no database and does not check
that a claim is live or that a result was saved. A finalizer must check
each `ResultRef` against durable accepted-stage proofs.

## Changes to the existing module

- `TerminalRoot` has a new field `limitations`. An INCOMPLETE root (prepared
  or A2-held) must list at least one limitation. A COMPLETE root lists
  none. Limitations are a sorted set. Rules come from
  `result_base.check_limitations`, shared with `prepared@2`.
- `CompletionReceipt` has two new fields:
  - `acceptance_index_sha256`: digest (domain `a2-acceptance-index@1`) of
    the ordered terminal coverage and the batch. If a caller omits it, the
    model derives it. A supplied value must match.
  - `claim_proofs`: tuple of `ResultClaimProof` (`result`, `proof`). The
    `proof` is the existing `AttemptProof`: execution, attempt, claim key
    and a claim token digest. No raw token is stored.
- Duplicate `workset_selection_index` values now fail with "one occurrence
  has several terminals". Gaps and reordering still fail with "roots must
  cover frozen indexes in order".
- `Accepted` now comes from `result_base`. The local copy is removed.

## Rules kept

- One terminal per frozen `workset.selections` occurrence, in frozen order.
  The de-duplicated `selection_refs` are never the unit. A repeated
  selection ref at two occurrences needs two terminals with two results.
- A terminal is an accepted `prepared@2` or an accepted
  `a2_input_disposition@1`. The same result cannot cover two occurrences.
- Any intake-held entry, A2-held root, INCOMPLETE root or INCOMPLETE batch
  forces INCOMPLETE. A held-only workset is a legal INCOMPLETE terminal.
- The batch is required when, and only when, the workset has transitions.

## Claim proof rule

`claim_proofs` is empty, or it holds exactly one proof for each terminal
result (roots and batch), with no duplicate and no foreign result.
`require_claim_proofs()` raises when it is empty.

## Open

- `claim_proofs` may still be empty at construction. Making it required
  would break existing store fixtures. A finalizer must call
  `require_claim_proofs()`. Decide whether to make the field required.
- `acceptance_index_sha256` binds this receipt only. It is not yet tied to
  the `a2_result_manifest@1` digest (the manifest has no digest yet).
- A root limitation is not checked against the limitations of the stored
  stage. The store layer must compare them.
- A2-held roots need a limitation code. No vocabulary is decided.
