# A2 v2 parser P2-02: JSON and plain-text parser (PROVISIONAL)

Code: `msgloom/a2_kedro/parsers/plain_json.py`.
Tests: `tests/a2_kedro/test_p2_02.py`.

All names and bounds below are PROVISIONAL. The parser reuses the C0 models
(`ParserReceipt`, `ParsedParts`) and adds no wire name.

## Entry points

- `parse_plain_text(data: bytes) -> ParseResult`
- `parse_json(data: bytes) -> ParseResult`
- `ParseResult.lookup(pointer) -> FieldLookup` (JSON Pointer, RFC 6901)
- `ParseResult.to_receipt(worker_version) -> ParserReceipt | None`

Neither parser raises for body content. Only a non-`bytes` argument or a
malformed pointer raises `PlainJsonInputError` (an `A2ContractError`) with
a fixed message.

## Outcome rule

- `MISSING`: zero bytes, only a UTF-8 BOM, or only ASCII white space.
  Limitation `empty_body`. `to_receipt` returns `None`.
- `INCOMPLETE`: at least one other limitation.
- `COMPLETE`: no limitation.

The rule matches `ParserReceipt`: `complete` needs `limit_hit == "none"`.
`to_receipt` maps every limitation to `limit_hit == "bytes"`. The closed
`LimitHit` has no value for truncated or malformed input, so the exact
reason lives only in `ParseResult.limitations`.

## Limitations (closed, content-free)

`empty_body`, `size_limit`, `unsupported_encoding` (UTF-16/32 BOM),
`invalid_utf8`, `nul_bytes`, `line_limit`, `truncated_json`,
`invalid_json`, `depth_limit`, `duplicate_key`, `non_finite_number`,
`huge_integer`, `lone_surrogate`, `field_limit`, `paging_marker`.

## Bounds

`MAX_BODY_BYTES` 8 MiB, `MAX_JSON_DEPTH` 64, `MAX_INT_DIGITS` 64,
`MAX_JSON_FIELDS` 10 000, `MAX_LINES` 200 000.

## Plain text

The parser splits bytes, so offsets are source byte offsets. `CRLF`, `LF`
and `CR` end a line; the line span excludes the terminator and the
terminator kind is kept. A UTF-8 BOM is skipped and counted in offsets. A
block is a run of lines that hold a non-white-space byte. A NUL byte is
content, not white space. Text is decoded on request with replacement
characters; invalid UTF-8 and NUL bytes set a limitation.

## JSON

- Standard library only. Duplicate keys, `NaN`, `Infinity` and `-Infinity`
  and floats that overflow to infinity yield a limitation and no fields.
- A linear single-pass scanner (`parsers/json_scan.py`) bounds nesting
  depth before `json.loads` runs. Brackets in strings do not count. An
  unterminated string or a trailing lone backslash ends the input. No
  input shape causes a rescan.
- Integers longer than `MAX_INT_DIGITS` become a placeholder and set
  `huge_integer`. Text fields are still listed.
- Fields: every string, empty string and `null` leaf, in document order,
  with its JSON Pointer.
- `null`, `""` and a missing key are `FieldState.NULL`, `EMPTY` and
  `MISSING`. `lookup` answers `MISSING` only when a document was parsed
  and absence is proven. With `paging_marker`, `field_limit` or
  `huge_integer` an absent key is `FieldState.UNPROVEN`.
- Lone surrogates become `?` in both `fields` and `lookup`, and set
  `lone_surrogate`.
- Truncation: a decode error at the end of the text, or an unterminated
  string, is `truncated_json`. Any other decode error is `invalid_json`.
- Paging: a non-empty root `@odata.nextLink` or `nextPageToken`, or a root
  `"truncated": true`, sets `paging_marker`. A page keeps its parsed
  fields but is `INCOMPLETE`.

## PII

`repr` of every result type shows counts and states only. It never shows
a pointer, key, value or text. Limitation codes and error messages are
fixed text. `ByteSpan.text(source)` and `JsonField.value` do hold body text
for the caller.

## Known gaps

- JSON has no byte offsets. The pointer is the only position.
- `PartFormat` has no JSON value, so a JSON result has no `Part`. A
  C0 change must add one before JSON can enter `ParsedParts`.
- `LimitHit` has no truncation or malformed value (see above).
- Only root-level paging markers are detected.
- Duplicate-key and non-finite bodies give no fields, even for the
  unaffected keys.
- Whole-body decode and scan: bounded by `MAX_BODY_BYTES`, not streamed.
