# A2 v2 parser P2-06: attachment inventory (PROVISIONAL)

Code: `msgloom/a2_kedro/parsers/attachments.py`.
Tests: `tests/a2_kedro/test_p2_06.py`.
Stacked on P2-01 (`parse_mime`). No new dependency and no new wire name.

All names, limits, roles and limitation codes are PROVISIONAL.

## Entry point

`inventory_attachments(result: MimeParseResult, data: bytes, *,
declared_count: int | None = None) -> AttachmentInventory`.

The function is pure. It does not parse attachment content. A wrong
argument type raises `A2ContractError` with a fixed message. Message
content never raises.

## Result

- `status`: COMPLETE only when there is no limitation. Otherwise
  INCOMPLETE. A missing text body is not a limitation here (P2-01 reports
  it).
- `records`: one `AttachmentRecord` per attachment-like leaf part, in
  source order. Fields: `path`, `parent`, `message_path` (nearest
  enclosing `message/rfc822`), `role`, `media_type`, `filename`
  (sanitized label), `has_content_id`, `start`, `end` (half-open window of
  the whole part in `data`), `size` and `sha256` (decoded payload), `status`
  and `flags`.
- `limitations`: sorted `Limitation(code, detail)`. The detail is a part
  path only.
- `seen`: count of attachment-like parts. `seen` equals `len(records)`
  plus the parts that have a limitation and no record.
- `input_size`, `input_sha256`: bind the result to the saved bytes.

## Closed sets

Roles: `attachment`, `inline`, `embedded_message`, `calendar`. The role
comes from the part headers. P2-01 gives every part inside an embedded
message the role `embedded`, which would hide a nested attachment.

Record status: `ok`, `empty`, `undecodable`, `oversize`. A record that is
not `ok` has no size and no hash, and it has a limitation with the same
path.

Limitation codes: `attachment_empty`, `attachment_undecodable`,
`attachment_too_large`, `attachment_depth_limit`, `attachment_limit`,
`attachment_count_mismatch`, `attachment_error`, `structure_incomplete`,
`source_mismatch`.

Record flags: `filename_sanitized`, `filename_duplicate`,
`filename_unreadable`, `media_type_invalid`.

## Rules

- Not an attachment: `multipart/*` containers, and `text/plain` or
  `text/html` with no filename and no `attachment` disposition (even with
  `inline` or a Content-ID).
- A part that fails (empty, bad base64 or quoted-printable, unknown
  transfer encoding, oversize) keeps its record and gets a limitation.
  Nothing is dropped. The hash of a lenient guess is never reported.
- Depth: a path with more than `MAX_DEPTH` components, or a part that
  P2-01 did not expand (`depth_limit`), gets `attachment_depth_limit` and no
  record.
- P2-01 structure problems that can hide a part (`input_too_large`,
  `parser_error`, `part_limit`, `header_too_large`, `multipart_malformed`,
  `multipart_truncated`) become `structure_incomplete` with the same path.
- Count: `declared_count` differing from `seen`, or `X-MS-Has-Attach: yes`
  in the root headers with no part found, gives
  `attachment_count_mismatch` (path `1`).
- Source: if `data` is not the input of `result` (size or SHA-256), the
  inventory is empty and has `source_mismatch`.
- Filename: RFC 2231 and RFC 2047 are decoded. The label is the last path
  segment. Control, format, surrogate, private-use, unassigned, line and
  paragraph separator characters become `_`. Edge dots and spaces are
  stripped. The label is cut to `MAX_FILENAME_CHARS`. It is never a path.
  Names equal after case folding get `filename_duplicate`.

## Bounds

`MAX_ATTACHMENTS` 128 records (more parts get `attachment_limit`),
`MAX_ATTACHMENT_BYTES` 8 MiB, `MAX_DEPTH` 8 path components,
`MAX_FILENAME_CHARS` 128, `MAX_MEDIA_TYPE_CHARS` 127. P2-01 bounds also
apply.

## Known gaps

- Inline versus attachment is a header heuristic. A Content-ID on a
  non-text part, or a `multipart/related` parent, means `inline`.
- `declared_count` counts every attachment-like part. A provider that
  excludes inline parts needs its own count.
- Only the `X-MS-Has-Attach: yes` header is read; `no` is not checked.
- A multipart container with an attachment disposition and no children is
  not reported by this module. P2-01 reports the malformed structure.
- The hash covers the decoded payload of a leaf. For `message/rfc822` it
  covers the inner message bytes. It does not cover any decoded child.
- The `.eml` filename of an embedded message is only a label.

## Review follow-up (commit after 72fc3dd)

- An embedded message part (`message/rfc822` or `message/global`) whose body
  has a transfer encoding other than 7bit, 8bit or binary, or has no
  expanded child, now creates the `attachment_nested_unexpanded` limitation
  with the part path. Before this fix a nested attachment in such a part was
  dropped and the status stayed COMPLETE. The part itself stays in the
  inventory.
- Known gaps, not yet reported as limitations (review notes):
  - uuencoded attachments in a text body;
  - attachments inside a part with an unrecognized content type;
  - undecodable filename bytes become U+FFFD without the
    `filename_sanitized` flag;
  - a header cut at 64 KB can leave a leading quote in the filename.
- Cost: a 1.5 MB input made of 30 parts with 64 KB folded headers took about
  2.5 s in review. It is linear and bounded, but not fast.
