# A2 v2 parser P2-04: DOCX parser (PROVISIONAL)

Code: `msgloom/a2_kedro/parsers/docx.py`.
Tests: `tests/a2_kedro/test_p2_04.py`, `tests/a2_kedro/test_p2_04_hostile.py`.

All names and bounds below are PROVISIONAL. The parser reuses the C0 models
(`ParserReceipt`, `LimitHit`) and the shared `Limitation` and
`TerminalStatus` types. It adds no wire name.

## Entry point

- `parse_docx(data: bytes) -> DocxResult`
- `DocxResult.to_receipt(worker_version) -> ParserReceipt | None`
- `DocxResult.to_contract_limitations() -> tuple[Limitation, ...]`

The parser never raises for document content. Only a non-bytes argument
raises `DocxInputError` (an `A2ContractError`) with a fixed message.

## Status rule

| Status       | Meaning                                                      | Receipt              |
| ------------ | ------------------------------------------------------------ | -------------------- |
| `COMPLETE`   | All body paragraphs and cells read. Nothing skipped.         | `complete`, `none`   |
| `INCOMPLETE` | Content skipped or a bound hit. Blocks read so far are kept. | `partial`, see below |
| `FAILED`     | No usable document. No block is returned.                    | `None`               |

`DocxResult` refuses `COMPLETE` when it holds a limitation or an unsupported
item. It also refuses a non-complete status without a limitation. A document
with zero blocks is `INCOMPLETE` with `empty_document`.

`limit_hit` maps the first limitation: `member_limit`, `unsupported_content`
and `unsupported_overflow` give `parts`; `paragraph_limit` gives `cells`;
all others give `bytes`. The closed `LimitHit` has no better value, so the
exact reason lives in `DocxResult.limitations`.

## Behavior table

| Input                                    | Status       | Limitation                 |
| ---------------------------------------- | ------------ | -------------------------- |
| Empty bytes                              | `FAILED`     | `empty_input`              |
| OLE compound file (encrypted or legacy)  | `FAILED`     | `encrypted_or_ole`         |
| Not a zip, truncated zip                 | `FAILED`     | `not_a_zip`                |
| Corrupt member data, any zip read error  | `FAILED`     | `corrupt_package`          |
| Duplicate member name                    | `FAILED`     | `duplicate_member`         |
| Zip member with the encryption flag      | `FAILED`     | `encrypted_member`         |
| No `word/document.xml`, wrong root       | `FAILED`     | `not_docx`                 |
| DTD, entity, XXE, billion laughs         | `FAILED`     | `xml_forbidden`            |
| Malformed XML, undefined entity          | `FAILED`     | `invalid_xml`              |
| Input over 32 MiB                        | `INCOMPLETE` | `size_limit`               |
| More than 1000 members                   | `INCOMPLETE` | `member_limit`             |
| Declared member over 16 MiB              | `INCOMPLETE` | `member_size_limit`        |
| Declared total over 64 MiB               | `INCOMPLETE` | `total_size_limit`         |
| XML depth over 128 or 1 000 000 elements | `INCOMPLETE` | `xml_limit`                |
| More than 100 000 paragraphs             | `INCOMPLETE` | `paragraph_limit`          |
| More than 5 000 000 text characters      | `INCOMPLETE` | `text_limit` (text is cut) |
| Table nesting over 4                     | `INCOMPLETE` | `table_depth_limit`        |
| Bad `w:gridSpan`                         | `INCOMPLETE` | `malformed_table`          |
| Any skipped content (see below)          | `INCOMPLETE` | `unsupported_content`      |
| More than 1000 skipped items             | `INCOMPLETE` | `unsupported_overflow`     |

## Blocks and IDs

- Each `w:p` and `w:tbl` child of `w:body` takes the next body index.
  `w:sdt` and `w:customXml` wrappers are transparent. Bookmarks, section
  properties and similar markers take no index.
- A paragraph is one block with ID `b{i}`.
- A table cell is one block with ID `b{i}/r{row}c{col}`. It joins its direct
  paragraphs with a newline. `col` is the grid column; `w:gridSpan` advances
  it. `w:gridBefore` and vertical merges are not modeled.
- A nested table sits at `b{i}/r{row}c{col}/{k}`, where `k` is the child
  index in the outer cell. Its cells follow the outer cell block.
- Empty paragraphs are blocks. IDs depend on structure only, never on text.

## Tracked changes policy

The parser reads the final view. It reads text in `w:ins` and `w:moveTo`.
It skips `w:del` and `w:moveFrom` and records `tracked_deletion` with the
block ID. The result is `INCOMPLETE`. Formatting changes are ignored.

## Unsupported content

Skipped and recorded with kind and, in the body, the block ID:

- Inline: images (`a:blip`, VML `imagedata`), charts, diagrams, text boxes
  (text inside is not read), other drawings, OLE objects, form controls,
  equations, comment, footnote and endnote references.
- Block level: `w:altChunk`, any unknown element.
- Package members: `word/media/`, `word/embeddings/`, `word/charts/`,
  `word/diagrams/`, `word/activeX/`, `word/vbaProject.bin` always count.
  `word/header*.xml`, `word/footer*.xml`, `word/footnotes.xml`,
  `word/endnotes.xml` count only when they hold text. `word/comments.xml`
  counts when it holds a comment. An unreadable or oversized part counts.

`DocxResult.to_contract_limitations()` returns one `Limitation` per
unsupported kind (`unsupported_image`) and one per other limitation. Details
are fixed text.

## Hostile input

- XML uses `defusedxml` with `forbid_dtd`. Any DTD is rejected, so entities
  never expand and no file or network is read.
- Sizes use the zip central directory. A member over its bound is not
  inflated. A read is capped at the bound. Probe reads stop when the total
  bound is exceeded.
- XML depth and element count are checked while streaming. All walks are
  iterative or bounded by the table depth. Work is linear in input size.
- Messages, `repr` and limitation details are fixed text. No input text or
  exception text is returned.

## Known gaps

- The main part is the fixed path `word/document.xml`. The package
  relationships are not followed.
- Hyperlink targets, field codes and document properties are not read and
  not recorded. A document that only has these is `COMPLETE`.
- Text boxes and drawings are skipped as a whole. Their text is not read.
- Zip tricks such as prefix data before the archive are accepted as far as
  `zipfile` accepts them.
- The read is whole-member in memory, bounded by the member bound.
- The module sits close to the 500 line limit. A split needs an allowlist
  change.
- `PartFormat` has no page model for DOCX. `page_count` stays 0.
- A broad `except Exception` maps any unexpected zip read failure to
  `corrupt_package`. A programming error in the parser would show the same
  way.
