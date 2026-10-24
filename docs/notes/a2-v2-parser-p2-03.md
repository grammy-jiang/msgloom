# A2 v2 parser P2-03: PDF parser (PROVISIONAL)

Code: `msgloom/a2_kedro/parsers/pdf.py`, `msgloom/a2_kedro/parsers/pdf_pagecheck.py`.
Tests: `tests/a2_kedro/test_p2_03.py`, `test_p2_03_hostile.py`,
`test_p2_03_review.py`, `test_p2_03_pagecheck.py`.

All names and bounds below are PROVISIONAL. The parser reuses the C0 models
(`ParserReceipt`, `ParsedParts`) and the shared `Limitation` and
`TerminalStatus` types of `msgloom.contracts`. It adds no wire name.

## Entry points

- `parse_pdf(data) -> PdfParseResult` (`bytes`, `bytearray` or `memoryview`)
- `source_block_id(page_index) -> str` (`page-0000`, `page-0001`, ...)
- `PdfParseResult.to_receipt(worker_version) -> ParserReceipt | None`
- `PdfParseResult.to_parsed_parts(component_id, worker_version, ...)`
  returns `ParsedParts | None`

`parse_pdf` never raises for PDF content. Only a non-bytes argument raises
`PdfInputError` (an `A2ContractError`) with a fixed message.

## Behavior table

| Input | Status | Limitation codes | Pages read |
| --- | --- | --- | --- |
| Text PDF | `COMPLETE` | none | all |
| Text PDF with a blank page | `COMPLETE` | none | all |
| Image-only (scanned) pages | `INCOMPLETE` | `no_text_layer`, `no_text` | all |
| Text and scanned pages | `INCOMPLETE` | `no_text_layer` | all |
| All pages blank | `INCOMPLETE` | `no_text` | all |
| Zero bytes | `FAILED` | `empty_input` | none |
| No `%PDF-` header | `FAILED` | `not_pdf` | none |
| Needs a password | `FAILED` | `encrypted`, `password_required` | none |
| Opens with empty password | `INCOMPLETE` | `encrypted` | all |
| Cut file, pdfium cannot open | `FAILED` | `truncated_pdf`, `invalid_pdf` | none |
| No `%%EOF`, pdfium recovers | `INCOMPLETE` | `truncated_pdf` | all |
| Corrupt, pdfium cannot open | `FAILED` | `invalid_pdf` | none |
| Zero pages | `FAILED` | `no_pages` or `invalid_pdf` | none |
| More bytes than `MAX_PDF_BYTES` | `INCOMPLETE` | `size_limit` | none |
| More pages than `MAX_PAGES` | `INCOMPLETE` | `page_limit` | first `MAX_PAGES` |
| More text than `MAX_TEXT_CHARS` | `INCOMPLETE` | `text_limit` | until the cut |
| Page count claim above real pages | `INCOMPLETE` | `page_unreadable` | real pages |
| Page leaves above the claim (detected form) | `INCOMPLETE` | `page_count_mismatch` | claimed pages |
| Object stream cannot be checked | `INCOMPLETE` | `page_count_unverified` | all |

`COMPLETE` needs no limitation and at least one page with text. An empty
read is never `COMPLETE`. When no page has text, the parser adds `no_text`.

## Bounds

`MAX_PDF_BYTES` 32 MiB, `MAX_PAGES` 500 (below the contract `MAX_PAGES`
of 4096), `MAX_TEXT_CHARS` 2 000 000 over all pages.

- The byte limit is all or nothing. A PDF cannot be parsed from a prefix.
- The page limit and the text limit give a partial result. The text limit
  cuts the page at the limit and reads no later page.
- A page count claim is not trusted. pdfium reports the `/Count` of the
  page tree up to an internal bound. The parser reads at most
  `MAX_PAGES` pages. A page that fails to load is `UNREADABLE` and sets
  `page_unreadable`. `claimed_pages` keeps the claim.

## Page count cross-check

pdfium trusts the `/Count` of the page tree. `pdf_pagecheck.check_page_count`
compares the claim with the number of page leaf objects in the bytes. It is
a heuristic. A result with no `page_count_mismatch` does not prove that the
count is right.

Detected (raw bytes and Flate object streams):

- `/Type /Page` with any white space between the names, also none. One
  compiled regular expression with no nested repetition; a 1 MB white space
  run is read once.
- `/Subtype /Page` (invalid PDF, but counted).
- `#xx` hex escapes in `/Type`, `/Subtype` and `/Page`, for example
  `/T#79pe /P#61ge`. The patterns match the escape; no byte is rewritten.
- Leaves in object streams (`/Type /ObjStm`, PDF 1.5 and later). The scan
  inflates each stream with `zlib.decompressobj` in chunks. Bounds: 256
  streams, 16 MiB compressed input and 8 MiB inflated output over all
  streams. A stream with no `/Filter` is already in the raw scan.
- `page_count_unverified` is set when an object stream cannot be checked:
  damaged or cut Flate data, a cap hit, a filter other than a single
  `FlateDecode`, a `/Predictor`, an indirect `/Filter`, or a stream marker
  without stream data. The result is `INCOMPLETE`.

Not detected (residual limits):

- Leaf objects with no `/Type` and no `/Subtype` entry.
- A comment (`%`) between `/Type` and `/Page`.
- Leaves in an object stream whose dictionary has no `/Type /ObjStm`.
- Leaves in an object stream with an encrypted body are reported as
  `page_count_unverified`, not counted.
- False positives: old page revisions (incremental update) and the token
  inside other stream data raise `page_count_mismatch`.
- Cost: one pass over the file for each pattern; 30 MB of hostile repeats
  takes about 1.5 s or less.

## Encryption

pdfium opens the file with no password. The parser has no password input
and never guesses one. A file that pdfium opens with the empty password is
read but never `COMPLETE`.

## Scanned and blank pages

A page with no text is `NO_TEXT_LAYER` when it has page objects (images,
paths) and `BLANK` when it has none. Only `NO_TEXT_LAYER` is a limitation.
Vector-drawn text without a text layer counts as `NO_TEXT_LAYER`. No OCR.

## Contract mapping

- `ParserReceipt.limit_hit` is `pages` for `page_limit` and `bytes` for
  every other limitation. `LimitHit` has no value for scanned, encrypted or
  damaged input. `limitations` keeps the exact reason.
- No receipt and no `ParsedParts` for `FAILED` results or when no page was
  read. `ParsedParts` needs one part.
- `Part.page_count` is the number of pages read. `PageRecord` exists for
  every readable page and holds `char_count`, not text.
- Source block IDs depend on the page index only. A limit never renumbers
  pages.

## PII

`repr` of every result type shows counts and states only. Limitation
details and error messages are fixed text. Page text is available only
through `PdfPage.text`. The parser catches every pdfium error and drops its
message.

## Known gaps

- pdfium runs in process. There is no time limit and no memory limit
  against decompression bombs or hostile content streams. The 1 MB hostile
  tests check wall time only. Run the parser in a worker process with an
  operating-system limit.
- pdfium is not thread safe. Call the parser from one thread.
- `%%EOF` is searched in the last 4096 bytes. A valid file with more
  trailing bytes reports `truncated_pdf`.
- Layout is the page size only (`PdfPage.width`, `PdfPage.height`, in
  points). Text order and spacing are those of pdfium. The parser gives no
  text coordinates, tables, forms, annotations or attachments.
- Encrypted files other than RC4 revision 2 are covered by pdfium, not by
  tests.
- Text of a damaged PDF may come from pdfium's repair of the file.
