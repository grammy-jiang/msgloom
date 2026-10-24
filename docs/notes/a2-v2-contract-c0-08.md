# A2 v2 contract C0-08: scoped transition batch (PROVISIONAL)

Code: `msgloom/a2_kedro/contracts/transition.py`.
Tests: `tests/a2_kedro/test_c0_08.py`.

This note resolves unresolved field 3 of `a2-v2-schema-ids.md` only in
research form. All names below are PROVISIONAL. The tests fail on change.

- Batch fields: `header`, `workset`, `code_version`, `policy_version`,
  `items`, `batch_sha256`.
- Item fields: `ordinal`, `entry`, `fact_id`, `scope_kind`, `scope_id`,
  `kind`, `authority`.
- Item kinds: `presence`, `absence`, `membership_removal`, `deletion`,
  `context_refresh` (same closed list as `IntakeTransition`).
- Digest domains: `a2-transition-item@1` and `a2-transition-batch@1`.
- Batch digest input: Workset Ref, code version, policy version, item
  count, ordered item digests. The validator recomputes it.
- Proof of one item: `ItemProof` with `batch_sha256`, `ordinal`, `count`,
  `item_sha256`. `verify_item_proof` checks it.
- Limits: 1 to 1024 items (existing `max_transitions`). Ordinals are
  contiguous from 0. One item per `(fact_id, scope_kind, scope_id)`.
- `authority` is a text taken from the A1 released fact
  (`authority_revision`). The field name and form are not decided.

Open: this digest is separate from the `StageIdentity` logical key. That
key still has no authority input. C0-10 or C0-21a must bind both.
Open: one item per fact and scope may be too strict if a fact needs two
kinds in one batch.
