# A2 v2 semantics P3-08: scoped transitions (PROVISIONAL)

Code: `msgloom/a2_kedro/semantics/transitions.py`.
Tests: `tests/a2_kedro/test_p3_08.py`, `tests/a2_kedro/test_p3_08_bounds.py`,
`tests/a2_kedro/test_p3_08_authority.py`, `tests/a2_kedro/test_p3_08_review_fixes.py`.
Depends on: C0-08 (`contracts/transition.py`). No wire name changed.

The layer is pure and deterministic. It reads previous and observed
records of one explicit scope and returns `ScopedTransition` values.
`to_items` and `to_batch` map them to the C0-08 `TransitionItem` and
`TransitionBatch`.

## Scope and role

- `ScopeRef`: the A1 intake scope (catalog, source, stream, consumer)
  plus a `scope_kind` and a `scope_id`.
- `ScopeObservation`: `ScopeRef`, `role`, `enumeration`, `authority` and
  the release `entry` that carries absence facts.
- Role `content`: the scope owns content. Records need a content hash.
- Role `membership`: the scope lists container members. A content hash is
  refused (`role_violation`). Content and membership are separate runs
  with separate scope kinds and IDs.

## Decision table (one resource key)

| previous | observed | result | authority |
| --- | --- | --- | --- |
| any | provider marker, content role | `deletion` | scope authority (marker must match) |
| any | provider marker, membership role | refused: `membership_marker` | - |
| absent | present | `presence` | scope authority |
| present | present, hash differs, content role | `context_refresh` | scope authority |
| present | present, same hash or membership role | none | - |
| present | absent, complete, content role | `absence` | scope authority |
| present | absent, complete, membership role | `membership_removal` | scope authority |
| present | absent, partial | none; `UnprovenAbsence` | - |
| absent | absent | none | - |

A partial scope adds one `absence_not_proven` limitation. Its detail
holds a count only. `TransitionOutcome.complete` is false in that case.
A marker in a content scope needs no complete enumeration.

## Errors

`TransitionSemanticsError` (a subclass of `A2ContractError`) has a closed
`code` and an optional record `position`: `cross_scope`,
`duplicate_record`, `conflicting_record`, `role_violation`,
`fact_conflict`, `too_many`, `bad_record_type` (an `observed` item that
is not an `ObservedRecord`), `authority_mismatch` (a marker
`deletion_authority` that differs from the scope `authority`),
`membership_marker` (a provider marker in a membership scope) and
`partial_scope` (`to_batch` on a non-complete outcome). The message never holds resource, scope,
hash or authority text. A test checks this with a marker string.

## Determinism

Output sorts by `(resource_kind, resource_id)`. Input order does not
matter. One key yields at most one transition. Absence and removal use
the previous fact ID with the scope observation entry. Presence, refresh
and deletion use the observed fact ID and entry.

## Decisions and gaps

- Marker records must not carry a content hash. Provider markers seen
  again produce another `deletion` (previous state holds present records
  only). Known gap: the layer does not dedupe a repeated marker. The
  caller must dedupe, and must not replay a consumed marker as new input.
- Two transitions with one fact ID in one scope are rejected, because
  the C0-08 batch allows one item per `(fact_id, scope_kind, scope_id)`.
- `to_batch` fails (pydantic error) on an empty outcome. The caller
  decides what an empty transition set means.
- `to_batch` raises `partial_scope` when the outcome has unproven
  absences or limitations (review fix F1). `TransitionBatch` has no
  limitation field, so the batch would look complete. A caller that
  accepts a partial outcome uses `to_items` and keeps `limitations`.
- Record models derive from `ResultPart`, which hides input values in
  pydantic construction errors. A test checks this with a marker string.
- `ScopeObservation.entry` must belong to the scope catalog, like each
  observed record entry (`cross_scope`).
- `authority` text is opaque. The layer does not check it against A1.
- Not wired into Kedro nodes or the stage key. Field names are not frozen.

## Review fixes (P3 independent review, F1 and F2)

- F1: `to_batch` refuses a non-complete outcome (`partial_scope`). This
  is the smallest safe design. It changes no contract module. Tests in
  `test_p3_08_review_fixes.py` cover it.
- F2: a provider marker in a membership scope is refused
  (`membership_marker`). It no longer emits `deletion`. The old test
  `test_membership_marker_is_a_deletion` is now
  `test_membership_marker_is_refused_not_a_deletion`. The membership
  case of `test_marker_with_other_authority_is_refused` now expects
  `membership_marker`, because the role check runs before the authority
  check. Why refuse and not emit `membership_removal`: a marker states
  that the content is gone. `membership_removal` states only that the
  resource left the container. Mapping one to the other would lose a
  fact.

## Open owner question

Should a membership-role scope accept a provider marker? Current rule:
no. The producer must report a marker through a content scope. The owner
may instead choose to emit `deletion` from a membership scope, or to
emit `membership_removal` for a marker. The code keeps the refusal until
the owner decides.
