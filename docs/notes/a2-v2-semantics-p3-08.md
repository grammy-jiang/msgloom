# A2 v2 semantics P3-08: scoped transitions (PROVISIONAL)

Code: `msgloom/a2_kedro/semantics/transitions.py`.
Tests: `tests/a2_kedro/test_p3_08.py`.
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
| any | provider marker | `deletion` | marker authority |
| absent | present | `presence` | scope authority |
| present | present, hash differs, content role | `context_refresh` | scope authority |
| present | present, same hash or membership role | none | - |
| present | absent, complete, content role | `absence` | scope authority |
| present | absent, complete, membership role | `membership_removal` | scope authority |
| present | absent, partial | none; `UnprovenAbsence` | - |
| absent | absent | none | - |

A partial scope adds one `absence_not_proven` limitation. Its detail
holds a count only. `TransitionOutcome.complete` is false in that case.
A marker needs no complete enumeration.

## Errors

`TransitionSemanticsError` (a subclass of `A2ContractError`) has a closed
`code` and an optional record `position`: `cross_scope`,
`duplicate_record`, `conflicting_record`, `role_violation`,
`fact_conflict`, `too_many`. The message never holds resource, scope,
hash or authority text. A test checks this with a marker string.

## Determinism

Output sorts by `(resource_kind, resource_id)`. Input order does not
matter. One key yields at most one transition. Absence and removal use
the previous fact ID with the scope observation entry. Presence, refresh
and deletion use the observed fact ID and entry.

## Decisions and gaps

- Marker records must not carry a content hash. Provider markers seen
  again produce another `deletion` (previous state holds present records
  only), so a caller must not replay a consumed marker as new input.
- Two transitions with one fact ID in one scope are rejected, because
  the C0-08 batch allows one item per `(fact_id, scope_kind, scope_id)`.
- `to_batch` fails (pydantic error) on an empty outcome. The caller
  decides what an empty transition set means.
- Record construction errors come from pydantic and may echo input.
  The layer assumes trusted records.
- `authority` text is opaque. The layer does not check it against A1.
- Not wired into Kedro nodes or the stage key. Field names are not frozen.
