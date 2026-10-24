# A2 v2 contract C0-03: extracted_components@1 (PROVISIONAL)

Code: `msgloom/a2_kedro/contracts/extract.py`.
Tests: `tests/a2_kedro/test_c0_03.py`.

All names and limits below are PROVISIONAL. They are not frozen. The
wire-form test fails on any change.

- Record fields: `header`, `components`.
- Component fields: `component_id`, `role`, `status`, `reference`,
  `sha256`, `metadata`.
- Roles: `primary`, `alternate`, `attachment`, `embedded`.
- Statuses: `present`, `missing`, `partial`, `unsupported`.
- Metadata: sorted pairs of text. Wire form is a list of `[key, value]`.
  `encode_metadata` and `decode_metadata` use a JSON object.
- Limits: 256 components, 32 metadata items, key 64 bytes, value 256
  bytes, 4096 metadata bytes.
- Rules: exactly one `primary` entry. Component IDs are unique. `missing`
  carries no reference or digest. `present` and `partial` need both.
  `unsupported` carries both or neither.

Open: the `reference` text form (saved-bytes reference) is not decided.
