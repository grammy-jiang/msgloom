# A2 Kedro C0 v2 follow-up: missing public A1 bridge (RESEARCH)

Status: candidate research. Not production acceptance.

## What the real A1 types prove

Tests in `tests/a2_kedro/test_a1_typed_evidence.py` use real
`ReleasedInput`, `ReleasedFact`, `ReleaseEntryRef`, `CollectedSelection` and
`PreparationIntakeWorkset` values. They show these results.

- The adapter accepts only a real `ReleasedInput`. It rejects look-alikes.
- The adapter hashes with `CollectedSelectionCodec`. A caller can not pass an
  encoder, so a caller can not choose the hashed bytes.
- The adapter rejects a reader answer for another release entry, including
  another catalog.
- A root is built only when the Intake selection identity matches exactly
  one ordinal. Role follows that ordinal.
- A wrong saved digest, a wrong ordinal and a changed member list fail.
- Two equal occurrence digests in one release fail.
- A baseline root comes from a real `CollectedSelection`. The digest comes
  from the codec and the identity must match.

## What they can not prove

A1 has no public verifier. Two formulas are mirrored in A2:

1. The Intake selection identity (`intake-selection:` over scope, entry,
   members, configuration, code and ordinal).
2. The baseline selection identity (`intake-baseline-selection:`).

Both come from private A1 helpers. Tests import the private `_identity` to
check the mirror. A formula change in A1 makes A2 reject every root. The
test `test_gap_formula_change_fails_closed` shows this fail-closed result.

A second gap: `OccurrenceEvidence` is a plain dataclass. A caller can build
it by hand. `test_gap_evidence_object_is_caller_constructible` shows that
such evidence passes the workset check. Python can not bind evidence to a
read without help from A1.

## Narrow bridge A1 would need to expose

No A1 API is invented here. The bridge is:

- A public pure function that returns the Intake selection identity for
  `(scope, entry, members, configuration, code, ordinal)`.
- A public pure function for the baseline selection identity.
- A public way to mark evidence as produced by `read_entry`, for example a
  verifier that takes a `ReleasedInput` and a workset and returns the
  proven ordinal and role.

Until A1 owners add it, production use of these roots stays blocked.
