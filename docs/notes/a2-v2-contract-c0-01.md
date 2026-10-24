# A2 v2 contract C0-01: FrozenSourceSelection (PROVISIONAL)

Code: `msgloom/a2_kedro/contracts/source.py` and
`msgloom/a2_kedro/contracts/source_selection_checks.py` (structural root rules,
split out to keep `source.py` below 500 lines).
Tests: `tests/a2_kedro/test_c0_01.py`.

`FrozenRoot` (one occurrence) and the read-only A1 adapter existed before
this task. C0-01 adds `FrozenSourceSelection`, the
`frozen_source_selection@1` payload. It holds the ordered roots of one
workset under one scope.

Rules:

- Exactly one of `incremental_roots` and `baseline_roots` is set and
  non-empty. Both or neither fails.
- Incremental roots: ascending unique `workset_index`, no baseline root,
  unique `(entry, ordinal)`, entry catalog equal to the scope catalog,
  `primary` only at ordinal 0 and once per entry, ordinal proof equal to the
  digest in the selection ID.
- Baseline roots: role `baseline` only (no incremental root), ascending
  unique index, one approval, no repeated `baseline_source`, no repeated
  `selected` reference. Intake already rejects repeats in
  `baseline_sources` and `baseline_selections`, so a repeat is never a
  faithful copy.
- `selection_set_sha256` is recomputed from the canonical content. A
  different supplied value fails. The digest detects edits only. A forger can
  recompute it, so it proves nothing about A1.
- `verify_against(workset)` checks the digest, scope, mode, root count and
  that every root equals the workset item at its index. It cannot prove
  `role`, `ordinal` or `selection_sha256`: those need A1 evidence.
- `verify_against_evidence(workset, evidence)` takes one item per root, in
  root order. An incremental root needs the `OccurrenceEvidence` of its
  entry. A baseline root needs its real `CollectedSelection`. It rebuilds
  each root with `verify_exact_occurrence` or `verify_baseline_selection`
  and fails when any field differs, or when the item count differs.

How K0 must call it: read the selection, read the workset, re-read every
root entry through `ReadOnlyOccurrenceAdapter`, then call
`selection.verify_against_evidence(workset, evidence)` before any stage uses
a root. `verify_against` alone is not enough.

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

Decisions and open questions from the C0-01 review:

- Not added: rejecting one `selected` reference under two release entries.
  The architecture (line 84) defines occurrence identity as workset index
  plus entry plus ordinal, and CR-03 treats the same `ResultRef` under two
  entries as a legal defensive case. A test pins that it is accepted.
  Under one entry the ordinal sits inside the selection ID, so the same
  reference at two ordinals cannot occur. Open: ask the plan owner if CR-03
  should change this.
- Not added: a scope check for `baseline_source`. `IntakeScope` holds
  catalog, source ID, stream and consumer. `VersionRef` holds kind, identity
  and version. No field is comparable. Open: a public A1 rule must say how a
  baseline source version maps to a scope.
- Decision (needs review): `verify_against` requires one root per workset
  occurrence. A selection that drops an occurrence fails. The plan says
  every frozen occurrence needs a terminal result.
- Open: `verify_baseline_selection` mirrors a private baseline identity
  formula, as `verify_exact_occurrence` mirrors the Intake ordinal formula.
  A public A1 verifier is still missing.
