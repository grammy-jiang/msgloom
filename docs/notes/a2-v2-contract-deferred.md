# A2 v2 contracts: deferred dependencies (PROVISIONAL)

Status: PROVISIONAL. This note records known gaps. It adds no code and no
test. Later tasks own the fixes.

## D-1: StageIdentity does not bind `batch_sha256`

Finding: the key of a `prepared_transitions@2` stage does not include the
`batch_sha256` of `TransitionBatch`.

Today:

- `StageIdentity.logical_key()` (domain `a2-stage-accepted-input@1`)
  covers the ordered `IntakeTransition` values in `transitions`. It has no
  field for `batch_sha256`.
- `TransitionBatch.batch_sha256` (domain `a2-transition-batch@1`) covers
  the Workset Ref, code version, policy version, item count and item
  digests. It includes the per-item `authority` text.
- `IntakeTransition` has no `authority` field. So two stages with equal
  `StageIdentity` can in principle carry batches with different
  `authority` values and different `batch_sha256` values.

Owner: later tasks C0-10 and C0-21a. Do not implement it in C0-00, C0-03,
C0-06 or C0-08. The fix needs the open wire decision 3 (authority per
transition) and decision 4 (root stage) in
`docs/decisions/a2-v2-schema-ids.md`.

Until then, a reader must not treat an equal logical key as proof that the
batch body is equal. It must check `batch_sha256` itself.

Code: `msgloom/a2_kedro/contracts/identity.py`,
`msgloom/a2_kedro/contracts/transition.py`.

## D-2: foreign transition models are not text-checked here

`StageIdentity.transitions` holds `IntakeTransition` models from
`msgloom/preparation_pipeline/intake_models.py`. Those models accept `str`
subclasses and newlines in `resource_identity`, `resource_kind` and
`scope_identity`. These values reach `logical_key()`.

`TransitionItem` checks again the fields that it copies, so C0-08 items are
safe. C0-10 must decide whether `StageIdentity` re-validates the foreign
fields. Do not change the foreign model in this stream.
