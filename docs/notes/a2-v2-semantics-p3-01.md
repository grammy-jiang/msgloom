# A2 v2 semantics P3-01: native relation recovery (PROVISIONAL)

Code: `msgloom/a2_kedro/semantics/relations.py`.
Tests: `tests/a2_kedro/test_p3_01.py`, `tests/a2_kedro/test_p3_01_negative.py`.
Contract: `native_relations@1` (C0-06), see `a2-v2-contract-c0-06.md`.

Function: `recover_relations(SourceEvidence) -> RelationRecovery`. It is
pure. It handles one source per call and never links two sources.

## Rules

| Kind        | Evidence                                      | Basis text                   |
| ----------- | --------------------------------------------- | ---------------------------- |
| `reply_to`  | exactly one distinct explicit parent ID       | `same_source:reply_parent`   |
| `ancestor`  | each ID of an explicit ancestor list          | `same_source:ancestor_list`  |
| `reference` | a quote marker with a target ID               | `same_source:quote_marker`   |

- The three kinds are never merged. One pair can hold all three.
- The contract has no quote kind. A quote source is a `reference`. The
  basis text tells it from other references.
- A target outside the source is an `UnresolvedRelation` plus a limitation.
  It is never a node and never a guessed link.
- No subject, time or author input exists.

## Limitation codes

`self_reference`, `conflicting_parents`, `duplicate_reference`,
`duplicate_message_id`, `ambiguous_target`, `unresolved_target`,
`conversation_mismatch`, `quote_without_target`, `cycle`,
`depth_exceeded`, `list_too_long`, `too_many_messages`,
`too_many_relations`.

## Provisional bounds

64 ancestors per message (nearest kept), 8 parent IDs, 16 quote markers,
and the contract bounds of 1024 nodes and 4096 relations. Truncation keeps
the sorted prefix, so it is deterministic.

## Open

- `native_relations@1` has no field for limitations or unresolved
  relations. The result wrapper `RelationRecovery` holds them beside the
  record. A later contract decision may move them.
- The ancestor list is root first (References order). A source with the
  other order needs an adapter before this function.
- `conversation_mismatch` drops a relation whose two messages carry
  different conversation IDs. Some providers change the ID inside a
  thread. This check may need to become a limitation only.
- A cycle drops all `reply_to` and `ancestor` edges inside the cycle
  group. It does not guess which edge is wrong.
- Conflicting parents record no `reply_to`. An unresolved parent in a
  conflicting set is not reported as unresolved.
