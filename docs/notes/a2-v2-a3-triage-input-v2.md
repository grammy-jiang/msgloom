# A2 v2 A3 contract C0-17a/C0-17b: triage_input@2 (PROVISIONAL)

Code: `msgloom/triage_input/models_v2.py`, `msgloom/triage_input/codec_v2.py`.
Tests: `tests/a2_kedro/test_c0_17a.py`, `tests/a2_kedro/test_c0_17b.py`.

All names, limits and digest domains below are PROVISIONAL. This is a new
contract. It does not change `triage_input@1`. The v1 models, codec and
fixtures are untouched.

## Why v1 cannot read @2

- A v2 payload has a required `header` (`triage_input@2`). It has no
  `schema_version` field.
- Every v1 and v2 model forbids extra fields.
- The v1 codec allows only `prepared@1`, `filter_result@1` and
  `group_result@1` refs. The tests prove that a v1 snapshot with a
  re-hashed `prepared@2` ref fails the v1 codec.
- The v2 codec refuses v1 data with `HistoricalVersionError`.

## Models (`models_v2.py`)

Base: `A2Model` (frozen, strict, `extra="forbid"`, exact text, no control
character, hidden input in pydantic errors).

- `TriageInputSnapshot`: `header`, `binding`, `binding_sha256`,
  `configuration`, `configuration_sha256`, `held`, `units`, `parts`,
  `failures`, `limitations`, `complete`, `snapshot_sha256`.
- `SelectionBinding`: `prepared`, `filters`, `groups` (each a
  `result` accepted `ResultRef` plus a `data` `SemanticDataRef`), `rule`,
  `roles`, `working_context`, `versions`. Lists are sorted and unique.
  `roles` covers exactly the prepared refs.
- `SelectedRole` (new): `new-source`, `earlier-context`,
  `baseline-context`.
- `HeldReason` (new value): `filter-unknown`, with the v1 reasons.
- `PartState`: `pending`, `complete`, `failed`. A saved snapshot holds only
  `pending` parts. The codec enforces this.
- `UnitEntry` keeps `occurrence_count` and `occurrences_sha256`, not the
  occurrence list.
- Limitations: a sorted set. `complete` is true if and only if there is no
  limitation. A coverage failure needs the code `coverage_incomplete`.
- Active sources and held sources are disjoint and cover all roles.

## Codec (`codec_v2.py`)

Decode order: size bound, UTF-8 JSON (no duplicate key, float or NaN),
canonical-bytes equality, header allowlist, nested ref allowlist, strict
model validation, digest checks, pending-part check, configured size bound.
`encode` revalidates through `decode`, so `decode(encode(x)) == x` and
re-encode is byte-identical.

Closed allowlists:

- Header: `triage_input@2`.
- Refs: `prepared@2`, `filter_result@2`, `group_result@2`,
  `triage_rules@2` (PROVISIONAL), `triage_input_part@2` (PROVISIONAL).

Digests use `domain_sha256` with the domains `triage-input-binding@2`,
`triage-input-configuration@2` and `triage-input-snapshot@2`. They differ
from the v1 raw SHA-256 hashes. `seal_snapshot` computes all three.

Typed errors (all subclass `TriageInputV2Error`, fixed message, no chained
cause or context, no value, key or path): `OversizedInputError`,
`MalformedInputError`, `DuplicateKeyError`, `NonCanonicalError`,
`UnknownKindError`, `UnknownVersionError`, `HistoricalVersionError`,
`ExtraFieldError`, `SchemaViolationError`, `DigestMismatchError`,
`InvalidValueError`.

## Limits (PROVISIONAL)

256 sources, 256 units, 64 parts per unit, 4096 parts, 100000 occurrences
per unit, 4 MiB per payload (`MAX_CANONICAL_BYTES`).

## Known gaps

- No A3 builder or reader exists for @2. A later task must build units and
  parts from `prepared@2` content and check occurrence coverage against
  `occurrences_sha256`.
- `triage_rules@2` and `triage_input_part@2` are not in
  `schema_ids.STAGE_SCHEMAS`. The header allowlist already has
  `triage_input@2`.
- The model validators cannot check cross-record facts (for example that a
  filter ref points at the right prepared ref). The A3 reader must check
  them against the loaded records.
- Pydantic error text from the model layer can show field names. The codec
  hides them. Use the codec, not the model, at trust boundaries.
