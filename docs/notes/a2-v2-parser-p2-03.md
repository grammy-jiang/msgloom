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
- Leaves in Flate object streams (PDF 1.5 and later). The scan does not
  look for the exact key pair `/Type /ObjStm` and does not try to find the
  start of the dictionary. It looks for the word `ObjStm` (also `Obj#53tm`;
  a comment between `/Type` and `/ObjStm` is covered). For each word it
  takes the 8 KiB before it up to the next `>>`, white space, `stream` and
  CRLF or LF. It decodes the `#xx` escapes in that text. Then it checks for
  `/Filter`, `Predictor`, `DecodeParms` and `Crypt`, so `/Fil#74er` and
  `/Pred#69ctor` are seen. The text can hold a name such as `/xobj`, a string
  such as `(stream)` or a fake `N G obj` token; none of them can hide a key.
  The scan inflates each stream with `zlib.decompressobj` in chunks. Bounds:
  256 streams, 16 MiB compressed input, 8 MiB inflated output and 65 536
  decoded escapes over all streams. A stream with no `/Filter` and plain
  integer data is already in the raw scan.
- `page_count_unverified` is set (result `INCOMPLETE`) when an object stream
  cannot be checked:
  - the place is ambiguous: no stream start within 8 KiB after the word, no
    `N G obj` header in the 8 KiB before it (also when the window cut it
    off), no `endobj` before that header in a cut window, a `%` in the header
    line, unbalanced `(` and `)` between the header and the stream start, or
    a second `>>`, white space, `stream` opener before the first `endstream`;
  - more than one `/Filter` key, a filter other than one plain
    `FlateDecode` (single name or one-item array, no comment in it), or a
    `Predictor`, `DecodeParms` or `Crypt` word;
  - no `/Filter` and the stream is not a real object stream: exactly one
    integer `/N` and `/First` (at most 64 KiB), and exactly `N` pairs of
    integers with strictly increasing offsets in the first `/First` bytes. A
    stream that passes is plain bytes and the raw scan counts its leaves;
  - `endstream` missing, damaged or cut Flate data, or a cap hit.

Not detected (residual limits):

- Leaf objects with no `/Type` and no `/Subtype` entry.
- A comment (`%`) between `/Type` and `/Page` of a leaf.
- Leaves in an object stream whose dictionary has no `ObjStm` word.
- A dictionary that is well formed in every check above but hides its
  `/Filter` before the last `N G obj` header or more than 8 KiB before the
  word, by a trick other than a string with unbalanced parentheses or a
  `%` comment in the header line. The scan does not parse PDF syntax.
- A non-Flate filter is seen only when it is inside the 8 KiB window.
- Leaves in an object stream with an encrypted body are reported as
  `page_count_unverified`, not counted.
- False positives (all `INCOMPLETE`): old page revisions (incremental
  update), the token inside other stream data, and the 8 KiB text holding
  the end of the previous object, for example the dictionary of a short
  previous stream with its own `/Filter` or `Predictor`. A hidden page that
  returns `COMPLETE` is not accepted; a false `INCOMPLETE` is.
- Cost: one pass over the file for each pattern; each `ObjStm` word reads at
  most 16 KiB and at most 256 words are read; 30 MB of hostile repeats takes
  about 1.5 s or less.

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
