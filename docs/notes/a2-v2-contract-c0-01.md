# A2 v2 contract C0-01: FrozenSourceSelection (PROVISIONAL)

Code: `msgloom/a2_kedro/contracts/source.py`.
Tests: `tests/a2_kedro/test_c0_01.py`.

`FrozenRoot` (one occurrence) and the read-only A1 adapter existed before
this task. C0-01 adds `FrozenSourceSelection`, the
`frozen_source_selection@1` payload. It holds the ordered roots of one
workset under one scope.

Rules:

- Exactly one of `incremental_roots` and `baseline_roots` is set and
  non-empty. Both or neither fails.
- Incremental roots: ascending unique `workset_index`, unique
  `(entry, ordinal)`, entry catalog equal to the scope catalog, `primary`
  only at ordinal 0 and once per entry, ordinal proof equal to the digest
  in the selection ID.
- Baseline roots: role `baseline`, ascending unique index, one approval.
- `selection_set_sha256` is recomputed from the canonical content. A
  different supplied value fails. `verify_against(workset)` compares the
  roots with the frozen Intake workset.

Provisional wire names (the plan does not fix them):

| Name | Meaning |
| --- | --- |
| `header` | `StageHeader` for `frozen_source_selection@1` |
| `workset` | `ResultRef` of `preparation_intake_workset@1` |
| `scope` | Intake scope (catalog, source, stream, consumer) |
| `incremental_roots` | Ordered roots of an incremental workset |
| `baseline_roots` | Ordered roots of an approved baseline |
| `selection_set_sha256` | Domain digest of all other fields |
| `a2-frozen-source-selection@1` | Digest domain |

Open: `docs/decisions/a2-v2-schema-ids.md` still says the record is a
bare `FrozenRoot` without a header. A reviewed decision must add the new
fields. Open: the digest covers A2 content only. It cannot prove A1 saved
bytes. That proof stays with `verify_exact_occurrence`.
