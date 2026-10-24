# A2 v2 contract C0-05: normalized_content@1 and zones@1 (PROVISIONAL)

Code: `msgloom/a2_kedro/contracts/zones.py`.
Tests: `tests/a2_kedro/test_c0_05.py`.

All names and limits below are PROVISIONAL. They are not frozen. The
wire-form test fails on any change. The names are new wire decisions of
this task; no earlier record fixed them. The kinds `normalized_content@1`
and `zones@1` are already approved in `schema_ids.py`.

- `normalized_content@1` fields: `header`, `part_id`, `parsed_sha256`,
  `parsed_length`, `normalized_sha256`, `normalized_length`, `segments`.
- Segment fields: `normalized` (span), `original_start`, `original_end`,
  `mode`. Modes: `identity`, `transformed`.
- `zones@1` fields: `header`, `part_id`, `parsed_sha256`, `parsed_length`,
  `normalized_sha256`, `normalized_length`, `zones`.
- Zone fields: `zone_id`, `kind`, `original` (span), `normalized` (span),
  `quote_occurrence`, `quote_author_sha256`.
- Span fields: `start`, `end`. Half open byte range, non-empty.
- Quote occurrence fields: `ordinal`, `depth`.
- Zone kinds: `authored`, `quote`, `signature`, `disclaimer`,
  `forward_header`, `boilerplate`.
- Limits: 8192 segments, 1024 zones, quote depth 16, text 2^30 bytes.

Rules:

- No record holds text. A2 text rules refuse control characters, so the
  records hold digests, byte lengths and byte offsets. Offsets are UTF-8
  byte offsets and must sit on character boundaries (`verify_bytes`).
- Segments cover the normalized text with no gap. Original ranges ascend
  and never overlap. A gap between two original ranges means dropped
  parsed bytes.
- `identity` segments have equal length and equal bytes. Any offset inside
  one maps exactly. A `transformed` segment maps only its two ends.
- A zone holds its range in both texts. `ContentZones.validate_against`
  proves that `original` is the exact projection of `normalized`.
- Zones are sorted and do not overlap in either coordinate. Zones may
  leave text unzoned.
- `quote_occurrence` (order and depth of the quote in this text) and
  `quote_author_sha256` (digest of the attribution claim) are separate
  fields. Only a `quote` zone carries them. A `quote` zone needs an
  occurrence. The author is optional. Ordinals run 0, 1, 2 in text order.

Non-reversible limit: the map goes from normalized text to parsed text
only. Normalized text plus the map cannot rebuild the parsed text. The
parsed text must stay saved. Its digest binds the record.

Open: whether the parser text (`parsed_sha256`) needs its own saved-text
kind. Today `ParsedParts` holds no text and no digest of text.
Open: the vocabulary of zone kinds and the quote author digest basis
(which bytes the digest covers) are not decided.
Open: nested quote zones use `depth`; zones themselves are flat.
