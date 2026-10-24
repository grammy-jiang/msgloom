# A2 v2 contract C0-02: source resolution (PROVISIONAL)

Code: `msgloom/a2_kedro/source_resolution.py`.
Tests: `tests/a2_kedro/test_c0_02.py`.

`resolve_frozen_selection(selection, workset, reader, allow_gaps=True)`
re-reads each release entry that owns a root, once, through an injected
`ReleaseReader`. It proves every root with `verify_exact_occurrence` and
requires the rebuilt root to equal the stored root in every field.

- Ordinal and byte mismatch, forged role, a reader answer for another entry,
  and a root over an entry with no selectable occurrence raise
  `A2ContractError`.
- Component-only entries are legal: ordinal 0 is a `component`.
- Context-only, transition-only and empty entries hold no occurrence. A root
  over one fails with a distinct message.
- A `SourceReaderError` becomes one `InputDisposition` per root of that
  entry. `SourceEvidenceLimitError` maps to `input_limit`. Every other
  reader error maps to `source_evidence_unavailable`. The error text is
  never copied.
- Sequence gaps are reported as `SequenceGap`. Intake says gaps are legal
  (A1 sequences are global across streams), so `allow_gaps=False` is opt-in.
- Baseline selections raise: the release reader cannot read them.

No wire field is added. The result types are internal Python names.

Open: the reason mapping needs review. Open: should a gap be a hard
failure for any consumer? Open: a baseline path needs a baseline reader.
