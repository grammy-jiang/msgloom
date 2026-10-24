# A2 v2 contract C0-04: parsed_parts@1 (PROVISIONAL)

Code: `msgloom/a2_kedro/contracts/parse.py`.
Tests: `tests/a2_kedro/test_c0_04.py`.

All names and limits below are PROVISIONAL. They are not frozen. The
wire-form test fails on any change. The names are new wire decisions of
this task; no earlier record fixed them.

- Record fields: `header`, `parts`, `pages`, `sheets`, `cells`, `receipt`.
- Part fields: `part_id`, `role`, `declared_format`, `detected_format`,
  `link`, `parent_part_id`, `page_count`, `sheet_count`.
- Link fields: `component_id`, `component_sha256`, `component_size`,
  `offset`, `length`.
- Page fields: `part_id`, `page_index`, `char_count`.
- Sheet fields: `part_id`, `sheet_index`, `row_count`, `column_count`.
- Cell fields: `part_id`, `sheet_index`, `row`, `column`, `value_kind`,
  `value_sha256`.
- Receipt fields: `worker`, `worker_version`, `outcome`, `limit_hit`,
  `input_bytes`, `part_count`.
- Enums: roles `body`, `alternate`, `attachment`, `embedded`. Formats
  `rfc822`, `html`, `plain_text`, `pdf`, `docx`, `xlsx`, `pptx`, `csv`,
  `image`. Cell kinds `empty`, `text`, `number`, `boolean`, `date`,
  `error`. Outcomes `complete`, `partial`. Limit hits `none`, `bytes`,
  `parts`, `pages`, `cells`, `time`.
- Limits: 256 parts, 4096 pages, 256 sheets, 8192 cells, 1048576 rows,
  16384 columns.

Rules:

- The record holds no parsed text. A cell keeps a position, a kind and a
  digest of the value. A page keeps a character count.
- `declared_format` must equal `detected_format`. A mismatch is rejected.
  The occurrence then goes to a held record (`parser_unsupported`).
- A link window must fit inside `component_size`.
  `ParsedParts.validate_against(extracted)` proves that the link names a
  `present` or `partial` component with the same digest.
- Pages exist only for `pdf`, `docx`, `pptx`. Sheets and cells exist only
  for `xlsx`, `csv`. Indexes stay below the counts of the part or sheet.
- Part IDs are unique. A parent part precedes its children. Pages, sheets
  and cells are sorted and unique.
- `outcome` is `complete` only with `limit_hit` `none`. `part_count`
  equals the number of parts. A failed run produces a held record, not a
  `ParsedParts`.
- Models hide input values in pydantic error text. Messages are fixed.

Open: `component_size` is a producer claim. `ExtractedComponents` has no
size field, so this contract cannot check it. The parser worker must read
it from the saved bytes.
Open: sheet names and cell text are not modeled. A later task may add
bounded name digests.
Open: the vocabulary of `worker` is not decided.
