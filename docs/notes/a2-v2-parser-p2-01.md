# A2 v2 parser P2-01: MIME/HTML (PROVISIONAL)

Code: `msgloom/a2_kedro/parsers/mime_html.py` (parser) and
`msgloom/a2_kedro/parsers/__init__.py` (result models and small decode
helpers, kept apart to hold each module under 500 lines).
Tests: `tests/a2_kedro/test_p2_01.py`.

All names, limits and limitation codes are PROVISIONAL. No new wire name:
the parser fills the existing `ParsedParts` (C0-04) models.

## Entry point

`parse_mime(data: bytes, *, component_id="primary") -> MimeParseResult`.
It uses only the standard library (`email` for header blocks,
`html.parser`, `base64`, `quopri`). It adds no dependency.

## Result

- `status`: COMPLETE only when there is no limitation. Otherwise INCOMPLETE.
- `body_status`: `present`, `partial` or `missing`
  (the `ComponentStatus` values of C0-03).
- `limitations`: sorted `Limitation(code, detail)`. The detail is a part
  path. It is never content.
- `parts`: ordered `MimePart` records. Each keeps path, parent, content
  type, charset, disposition, role, format, byte window (`start`, `end`),
  `body_start`, flag codes, reduced `text` (not in `repr`), `text_map`
  and `quoted`.
- `parsed`: a `ParsedParts` for every part the wire record can name, or
  `None` (zero bytes, or no representable part). Part ID is the path.
  The byte link covers the whole part (headers and body).
- `input_size`, `input_sha256`: bind the windows to the saved bytes.

## Rules

- Own boundary scanner, because `email` reports no offsets. Child windows
  exclude the delimiter line and the line break that belongs to it.
- Roles: first non-attachment text leaf is `body`. Later text leaves in a
  `multipart/alternative` are `alternate`. Attachment subtrees are
  `attachment`. `message/rfc822` and related or Content-ID leaves are
  `embedded`.
- Limitation codes: `body_absent`, `input_empty`, `input_too_large`,
  `part_too_large`, `part_limit`, `depth_limit`, `header_too_large`,
  `multipart_malformed`, `multipart_truncated`, `part_empty`,
  `charset_unknown`, `charset_decode_error`, `base64_corrupt`,
  `qp_corrupt`, `cte_unknown`, `attachment_unsupported`,
  `part_unsupported`, `html_parse_error`, `map_truncated`,
  `parser_error`, `contract_rejected`.
- A corrupt encoding gives a best-effort decode (lenient base64, literal
  bad quoted-printable escapes, replacement characters) plus a flag. The
  part is never dropped.
- Receipt `outcome` is `partial` only for a resource cap (`bytes` or
  `parts`). C0-04 requires `outcome == "complete"` exactly when
  `limit_hit == "none"`, and `LimitHit` has no value for a content
  defect. A content defect (corrupt base64, unknown charset, truncated
  multipart) therefore leaves the wire receipt `complete`. The
  limitation list and `MimeParseResult.status` (INCOMPLETE) are the
  authority. Fix needs a contract change (see Known gaps).
- Multipart scanning continues after a close delimiter. A later
  delimiter of the same boundary keeps its part and adds
  `multipart_malformed`. Text after the close with no delimiter line is
  an epilogue and is ignored without a limitation.
- HTML: a skipped element (`script`, `style`, `title`, `template`) that
  is not closed at end of input adds `html_parse_error`. Nested
  `template` elements use a depth counter.
- HTML: script, style, template and title content is dropped. Attributes
  are never read. Nothing is fetched. `text_map` spans map text ranges to
  character ranges of the decoded body. Plain text has one identity span.
- Quotes: `>` lines (spaces allowed between marks) and `blockquote` become
  `QuotedRegion` records. Text is not removed.

## Bounds

Input 64 MiB, part 8 MiB, header block 64 KiB, depth 16, map items 4096
per part, parts 256 (wire limit).

## Known gaps

- `text_map` offsets are decoded-character offsets, not byte offsets.
  Only the part window is an exact byte link.
- A part type outside the closed `PartFormat` set (for example a zip
  attachment) is listed in `parts` and flagged. It is not in `parsed`.
- `declared_format` equals `detected_format`; there is no content sniffing.
- Attachment bytes are checked for transfer-encoding defects but not
  parsed. Preamble and epilogue bytes of a multipart are not parts.
- Header defects (for example folded or duplicated headers) are not
  flagged. `pre` whitespace is collapsed in HTML.
- Zero-byte or fully unrepresentable input cannot form `ParsedParts`
  (a byte link needs length of at least 1), so `parsed` is `None`.
- The wire receipt cannot say `partial` for a content defect (C0-04 ties
  `outcome` to `limit_hit`). A future contract change should add a
  limit-hit value or a separate defect flag.
- Preamble bytes (before the first delimiter) and epilogue bytes (after
  the close delimiter) are not parts and are not flagged.
- CPU is not bounded by time. A hostile 8 MB HTML part (the part cap) can
  take about 19 s to reduce. Only byte and item caps exist.
