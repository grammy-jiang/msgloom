# PDF parser lane

**Scope:** synchronous PDF extraction inside the reviewed isolated parser
process.

## Contract

`msgloom.preparation.parsers.pdf.parse(request, content)` accepts only
`DocumentFormat.PDF`, parser identity `msgloom.pdf@1`, backend
`pypdfium2-5.13.0`, and profile `pdf-primary-v1`. Input is bytes only.
The parser does not read files, providers, databases, URLs, environment
configuration, or network resources.

The parser rechecks the saved byte count and SHA-256 digest before opening
PDFium. It also requires the PDF header at byte zero. The parent isolation
boundary performs its own source validation before launch; this duplicate
check keeps direct parser calls from returning provenance for different bytes.

Each page is processed in source order. A page with extractable text produces
one `TextBlock` with a one-based `PageLocation`. Block order is contiguous
across the text-bearing pages. Extraction uses
`PdfTextPage.get_text_bounded(errors="strict")`, rather than the UCS-2-limited
range helper, so PDFium's full Unicode result is retained. PDFium-detected web
URLs are returned as `ParsedLink` data on the page block and are never
fetched.

## Meaning and limitations

The primary profile is a text extraction profile, not document
understanding. Every successful result records that PDFium extraction order
does not establish semantic reading order, geometric layout is not
represented, and table structure is not inferred. These limitations remain
present even when the text API succeeds.

An image-only page with no extractable text records a `SCANNED` limitation.
A page containing both text and image objects records a partial image-content
limitation. A page with neither extractable text nor an image object records
an explicit empty-page limitation. No OCR, image understanding, table
reconstruction, or generic fallback runs in this lane.

A requested profile whose name identifies OCR, layout, or Docling fails
visibly because the qualified environment deliberately has no Docling
profile. Other unknown profiles and settings are rejected rather than
silently changing extraction behavior. Digital signature markers are not
verified cryptographically; their presence adds an explicit unsupported
verification limitation.

## Lifecycle and failures

PDFium is called only synchronously. A document handle owns page handles; a
page owns its text-page handle. The implementation nevertheless closes each
text page and page explicitly in nested `finally` blocks, closes every
PDFium web-link handle in its own `finally` block, and closes the document
in the outer `finally` block. Tests exercise cleanup after both successful
extraction and a forced output-limit failure. Native handles are never shared
with another thread.

Password-protected input, unsupported security handlers, malformed documents,
and extraction failures raise `PdfParseError`. A wrong signature, wrong
detected format, wrong parser identity, unsupported profile, unsupported
settings, or source-provenance mismatch fails before extraction. The parser
does not return an empty successful result for an unavailable OCR/layout
profile.

## Resource ceilings

The parser cooperatively checks `wall_time_seconds` while the parent process
retains the authoritative hard timeout and reap behavior. PDF page count is
bounded by `container_members`. Cumulative extracted UTF-8 text and detected
link bytes are bounded as parser work by `decompressed_bytes`; returned
text/link bytes are also bounded by `output_bytes`. The isolated-process
lane remains responsible for the hard `memory_bytes` ceiling and validates
the complete decoded `ParserOutput` size after return. This parser does not
pretend that an in-process byte counter is an RSS limit.

## Synthetic acceptance

`tests/parser_pdf/` covers the reviewed two-page text/image fixture plus
synthetic full-Unicode, detected URL, empty-page, mixed text/image, encrypted,
malformed, wrong-signature, unavailable-profile, provenance-mismatch, page,
work, and output-limit cases. The Unicode fixture uses a ToUnicode CMap with
BMP and astral characters. The encrypted fixture uses the Standard Security
Handler and requires a password, without containing private data.

The focused lane command is:

```bash
.venv/bin/pytest -q tests/parser_pdf
```

Static checks for the lane are:

```bash
.venv/bin/ruff check msgloom/preparation/parsers/pdf.py tests/parser_pdf
.venv/bin/ruff format --check msgloom/preparation/parsers/pdf.py \
    tests/parser_pdf
pyright msgloom/preparation/parsers/pdf.py
git diff --check
```

## Coordinator runtime qualification

Cold-start, throughput, and RSS are deployment measurements, not claims from
the unit suite. The coordinator should run the parser through the real
isolated-process boundary on Linux aarch64 CPython 3.12, 3.13, and 3.14 with
the locked `pypdfium2==5.13.0`. Use only synthetic or approved
representative fixtures.

For cold start, launch a fresh worker for a small text PDF at least 30 times
and record wall-clock launch-to-validated-output latency. Report median, p95,
minimum, and maximum; do not reuse a warm worker for this measurement.

For throughput, use fixed text, multipage, Unicode, image-only, and mixed
fixtures at several bounded page counts. Measure validated pages/second and
input MiB/second from worker launch through parent validation. Run sequential
PDFium work inside each worker; do not introduce threads to improve the
number.

For RSS, sample the child process resident set from launch until reap while
parsing the same fixed fixture matrix. Record peak RSS per fixture and compare
it with the configured `memory_bytes` ceiling. Include forced page, output,
work, wall-time, and memory failures and verify the child is terminated and
reaped with no later result acceptance.

Keep raw fixture identities, exact parser/backend versions, interpreter,
kernel/architecture, limits, and command line with the measurements. Do not
generalize CPython 3.13 measurements to 3.12 or 3.14, and do not describe
Docling/OCR/layout as qualified until its separate optional profile is
installed, pinned, and accepted.
