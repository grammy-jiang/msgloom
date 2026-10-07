# Parser contract and dependency qualification note

Date: 2026-09-29

Scope: plan Section 14 preparation only. This note does not select persistence
schema, implement production parsers, add dependencies, or change A1. The
contracts in msgloom/preparation are intentionally independent of SQLAlchemy,
message_ingest, Scrapy, and unsettled Foundation persistence.

## Contract boundary

ParserRequest names an already-saved byte reference, SHA-256 digest, byte count,
detected format, exact parser identity, deterministic parser profile/settings,
and hard resource ceilings. Zero-byte saved evidence is valid input identity;
later parser logic must report its empty/unsupported outcome explicitly. Wall
time is finite and positive; byte/member ceilings are strict positive integers.
A parser never owns source acquisition.

ParserOutput contains immutable provenance copied from the request, contiguous
zero-based ordered blocks, source-mapped tables/cells, links, MIME part
relationships, and explicit limitations. Source locations cover PDF pages,
spreadsheet sheets/cells, document parts/block indexes, and MIME part refs.

The required limitation kinds are missing, unsupported, partial, encrypted, and
scanned. A successful parser process can still return limitations. ParserOutput
has deliberately no status, completion flag, persistence identifier, or method
that can mark an Application attempt complete. Parser output is untrusted data
until the parent validates it and durably records the stage result.

Spreadsheet cells can retain parser-observed text/type, formula text, cached
value, merged range, links, and exact cell coordinates. The primary Calamine
path is therefore allowed to return values while the targeted OpenPyXL pass can
supply formula/merge metadata without pretending the primary parser exposed it.

Links are retained as source data. No parser is authorised to dereference them.
MIME part refs preserve the tree relationship without copying source bytes into
the semantic contract. Every non-root parent must be another part declared in
the same ParserOutput, and parent chains must be acyclic. Root parts use
parent_ref=None; this contract intentionally allows no external root parent.

## Isolated worker design for the later implementation lane

The later Parser worker must be a bounded subprocess, not a thread for untrusted
native parsing. The parent resolves the opaque saved-byte reference and verifies
its digest before spawn. The child receives only the one input and a private
temporary output directory; it receives no database handle, Microsoft token,
credential/cache path, production configuration, or inherited unrelated file
descriptor.

The execution profile must enforce all of these gates:

1. Sanitize the environment and working directory. Close inherited descriptors.
   Disable document macros, network access, and external-document/resource
   fetching. Application-level socket monkey-patching alone is not an accepted
   network boundary; if the deployment cannot enforce the selected isolation
   profile, the parser profile is unavailable rather than silently less safe.
2. Apply parent-owned wall time plus Linux process ceilings for memory, CPU/file
   output, and descriptor count where supported. Enforce decompressed-byte and
   archive-member ceilings before or while expanding containers. ParserLimits
   supplies the portable policy values; the worker implementation owns the OS
   mapping.
3. Treat PDFium as process-confined. Do not make simultaneous PDFium calls from
   multiple threads in one process.
4. The child writes only a bounded result in its private temporary directory.
   Before deserialising, the parent verifies the output is a regular file inside
   that directory, is not a symlink, is within the output limit, and matches the
   expected result shape. Unexpected extra outputs are a failure.
5. On timeout or cancellation, stop the process group, allow only a bounded
   termination grace, kill survivors, and await/reap the child before releasing
   the claim or deleting temporary files. Cancellation is never a successful
   partial parse.
6. The parent validates ParserOutput, limitations, source coverage, and digest
   provenance before any persistence call. Persistence and completion remain
   Application responsibilities. Foundation is evaluating a separate
   provider-neutral schema owner; parser contracts do not prescribe A1 table or
   lock sharing before that decision is accepted.

A decompression/output limit hit is a failed or limited parse according to the
later Application policy; it is never converted to an empty successful result.
An isolated process exiting zero is not by itself evidence of complete
extraction.

## Synthetic acceptance fixture inventory

The builders live in tests/parser_fixture_builders.py and use only synthetic
values and reserved example.invalid links. They intentionally require no parser
dependency in the shared project environment.

| Fixture | Covered acceptance facts | Later parser expectation |
| --- | --- | --- |
| MIME | quoted-printable UTF-8 plain and HTML alternatives, multipart relationships, base64 attachment | Preserve part refs, content types, transfer decoding result/defects, and HTML body source relationship. |
| HTML body | paragraph text, link inside paragraph, table, trailing paragraph | Preserve meaningful text/link/table order; retain target as data and never fetch it. |
| XLSX | first populated cell at B3, number/string/bool/date, formula plus cached value, D3:E3 merge, hidden sheet | Preserve original coordinates despite leading blanks; distinguish value/type/date/formula/cached value; record merge and hidden-sheet policy. |
| PDF | page 1 ordered text; page 2 image-only | Retain page locations and observed text order; image-only page produces a scanned/missing-OCR limitation unless an explicit OCR profile runs. |
| DOCX | paragraph, table, paragraph order plus OLE relationship/payload | Preserve paragraph/table/block order; disclose unsupported embedded object instead of dropping it silently. |

Future fixture additions should remain small and synthetic. Add encrypted
container fixtures, malformed/truncated containers, decompression-limit cases,
timeout/cancellation helpers, and output-directory escape attempts in the
worker lane. Do not introduce personal documents as acceptance fixtures.

## Dependency qualification matrix

Official metadata was checked on 2026-09-29. Direct wheels were downloaded with
pip --only-binary and --platform manylinux_2_17_aarch64 for CPython 3.12, 3.13,
and 3.14. This proves matching direct artifacts exist; it does not replace
runtime execution on interpreters that are absent from this host.

The Pi has CPython 3.13.5 on Linux aarch64. CPython 3.12 and 3.14 executables are
not installed. A separate temporary 3.13 venv under /tmp was used for candidate
installation and API exercises. The shared .venv and project lock were not
changed.

The CPython 3.13 API exercise is reproducible from repository root with
PYTHONPATH=. /tmp/msgloom-parser-qual-313/bin/python
scripts/parser_dependency_qualification.py. It uses only the synthetic fixture
builders and emits machine-readable JSON. The recorded result is
docs/notes/parser-qualification-result-cp313-aarch64.json. This is runtime
evidence only for CPython 3.13.5 on this Linux aarch64 host; CPython 3.12 and
3.14 evidence below remains direct-wheel artifact evidence only.

| Path | Exact candidate / licence | Linux aarch64 evidence | Exercise and API risk | Recommendation |
| --- | --- | --- | --- | --- |
| MIME | Python stdlib email; PSF licence | Interpreter-owned on every required Python | 3.13 BytesParser exercised with encoded multipart fixture. Policy must be explicit and defects retained. | Use stdlib; no dependency lock entry. |
| HTML | selectolax 0.4.12; package MIT, Lexbor Apache-2.0 | cp312/cp313/cp314 manylinux_2_17_aarch64 wheels downloaded | 3.13 LexborHTMLParser exercised for link/table/body extraction. DOM text helpers can flatten order, so later lane must traverse nodes deliberately. | Manager lock candidate: selectolax==0.4.12. |
| Excel primary | python-calamine 0.8.2; MIT | cp312/cp313/cp314 manylinux_2_17_aarch64 wheels downloaded | 3.13 exercised. Visible sheet starts at B3 while to_python returns a compact 3x3 range; sheet.start must anchor original coordinates. Values include date and cached formula result; formula text is not supplied by this value path. Hidden metadata and merged ranges are exposed. | Manager lock candidate: python-calamine==0.8.2. |
| Excel targeted | openpyxl 3.1.5 MIT plus defusedxml 0.7.1 PSFL | Both pure-Python wheels downloaded for all three target interpreters | 3.13 exercised with formula mode and data_only cached-value mode, merge range, date and hidden state. openpyxl.xml reported DEFUSEDXML=True in the isolated environment. Never calculate formulas or execute VBA. | Manager lock candidates: openpyxl==3.1.5 and defusedxml==0.7.1. Keep this pass targeted. |
| PDF | pypdfium2 5.13.0; BSD-3-Clause, Apache-2.0 and bundled dependency licences | py3-none-manylinux_2_17_aarch64 wheel downloaded for all three targets | 3.13 exercised: two pages, ordered text on page 1, PdfImage with no text on page 2. PDFium is not thread-safe; reading order/table/image coverage require explicit limitations. Review bundled PDFium dependency licences in release lock evidence. | Manager lock candidate: pypdfium2==5.13.0. |
| Word | python-docx 1.2.0 MIT plus lxml 6.1.3 BSD-3-Clause | python-docx pure wheel plus lxml cp312/cp313/cp314 manylinux_2_17_aarch64 wheels downloaded | 3.13 exercised. Document.iter_inner_content preserves paragraph/table order in the fixture; OLE relationship remains detectable but unsupported. lxml is native and must remain inside the process boundary for untrusted input. | Manager lock candidates: python-docx==1.2.0 and lxml==6.1.3. |
| OCR/layout fallback | Docling 2.130.0; MIT code, separate model licences | Top-level py3-none-any metadata exists, but transitive native/model stack was not installed or exercised | ABSENT profile. Top-level wheel does not qualify OCR/model assets or aarch64 transitive dependencies. It can accept URLs, which the msgloom profile must prohibit. | Do not add to base lock. Qualify a separate optional extra later. |
| Legacy DOC conversion | LibreOffice 26.2.6 mature branch is current official enterprise-oriented release; MPL/LGPL ecosystem constraints require deployment review | Official downloads list Linux Aarch64, but executable is absent on this Pi | ABSENT profile and not exercised. Conversion changes representation and must preserve both input and derived bytes. Macro/external-resource/network isolation is mandatory. | Do not add to Python lock. Qualify as an optional deployment tool later. |

CPython 3.12 and 3.14 remain runtime-exercise gates. Their direct aarch64 wheels
are artifact-qualified only. Do not describe the full parser stack as qualified
on those interpreters until the manager runs the same fixture/API exercises in
the required clean environments.

### Exact direct wheel observations

For CPython 3.12, 3.13 and 3.14 respectively, pip selected:

- selectolax-0.4.12-cp312/cp313/cp314-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64
- python_calamine-0.8.2-cp312/cp313/cp314-manylinux_2_17_aarch64.manylinux2014_aarch64
- lxml-6.1.3-cp312/cp313/cp314-manylinux2014_aarch64.manylinux_2_17_aarch64
- pypdfium2-5.13.0-py3-none-manylinux_2_17_aarch64.manylinux2014_aarch64
- openpyxl-3.1.5-py2.py3-none-any
- defusedxml-0.7.1-py2.py3-none-any
- python_docx-1.2.0-py3-none-any

The download command used --no-deps intentionally to answer the direct native
artifact question. Manager dependency integration must still resolve and test
the complete transitive lock on every required interpreter.

## Official evidence URLs

- [Python email parser](https://docs.python.org/3.14/library/email.parser.html)
- [selectolax 0.4.12](https://pypi.org/project/selectolax/0.4.12/)
- [selectolax Lexbor API](https://selectolax.readthedocs.io/en/latest/parser.html)
- [python-calamine 0.8.2](https://pypi.org/project/python-calamine/0.8.2/)
- [python-calamine source](https://github.com/dimastbk/python-calamine)
- [openpyxl 3.1.5](https://pypi.org/project/openpyxl/3.1.5/)
- [openpyxl docs](https://openpyxl.readthedocs.io/en/stable/)
- [defusedxml 0.7.1](https://pypi.org/project/defusedxml/0.7.1/)
- [pypdfium2 5.13.0](https://pypi.org/project/pypdfium2/5.13.0/)
- [pypdfium2 API](https://pypdfium2.readthedocs.io/en/stable/python_api.html)
- [python-docx 1.2.0](https://pypi.org/project/python-docx/1.2.0/)
- [python-docx docs](https://python-docx.readthedocs.io/en/latest/)
- [lxml 6.1.3](https://pypi.org/project/lxml/6.1.3/)
- [Docling 2.130.0](https://pypi.org/project/docling/2.130.0/)
- [LibreOffice release notes](https://www.libreoffice.org/release-notes/)
- [LibreOffice conversion help](https://help.libreoffice.org/latest/en-US/text/shared/guide/convertfilters.html)

## Later parser lane prompts

### MIME and HTML lane

Implement stdlib MIME plus selectolax Lexbor behind the isolated worker. Use
BytesParser with an explicit policy, preserve defects and MIME tree refs, and
map HTML nodes into ordered blocks without flattening tables/links. Never fetch
link targets. Acceptance starts with build_mime_fixture and HTML_BODY and adds
malformed encodings and nested multipart cases. Return explicit limitations for
content that cannot be decoded; never infer Application completion.

### Excel lane

Implement python-calamine 0.8.2 as the primary value path. Use the worksheet
start offset to reconstruct original addresses; do not renumber B3 to A1.
Preserve value/type/date and hidden-sheet policy. Invoke openpyxl 3.1.5 with
defusedxml only for the declared metadata pass: formulas versus cached values,
merged cells and other approved XLSX/XLSM metadata. Do not calculate formulas,
run macros, or pretend non-XLSX formats expose OpenPyXL metadata. Acceptance
starts with build_xlsx_fixture and adds XLS/XLSB/ODS synthetic fixtures plus
encrypted and decompression-limit cases.

### PDF lane

Implement pypdfium2 5.13.0 in a dedicated process. Preserve one-based page
locations and observed text order. Detect image-only/zero-text coverage and
record scanned limitations when OCR is not configured. Do not infer tables or
reading order that PDFium did not establish. Acceptance starts with
build_pdf_fixture and adds multi-column, table-like, encrypted, malformed,
timeout, and memory-limit fixtures. No threaded PDFium calls.

### Word lane

Implement python-docx 1.2.0 plus lxml 6.1.3 in the isolated process. Use document
inner-content order so paragraphs and tables remain interleaved. Preserve
supported relationships and disclose text boxes, revisions, embedded objects,
or other unsupported content. Acceptance starts with build_docx_fixture and
adds headers/footers, hyperlinks, revisions/text boxes, encrypted/malformed
containers, and resource-limit cases.

### Worker isolation lane

Implement the parent/child lifecycle described above without importing
persistence into the parser package. Tests must launch real local subprocesses
for success, timeout, cancellation, memory/output/decompression limits, process
reaping, network denial, and temp-output escape attempts. Unit mocks do not
prove these guarantees. The Application integration lane later supplies the
awaited persistence call through the Foundation-approved provider-neutral
schema owner and must reject parser output as authoritative until validation
and durable save succeed. Parser contracts do not choose A1 tables or locks.

## Manager integration note

No pyproject.toml or uv.lock change belongs in this lane. When Foundation schema
and clean interpreter environments are ready, the dependency lane should start
from the exact candidates above, resolve the full lock, run the fixture/API
matrix on Linux aarch64 CPython 3.12/3.13/3.14, review direct/transitive
licences, and only then promote them from candidates to qualified locked
dependencies. Docling and LibreOffice remain absent optional profiles.

## Manager runtime qualification

The manager reran the committed candidate API exercise on isolated ARM64
CPython 3.12.14 and 3.14.7 environments with the same seven dependency pins. Both
passed. The matching JSON artifacts are saved beside the CPython 3.13 result.
The qualification script now derives its interpreter label from the runtime.
This extends the earlier artifact-only evidence to real synthetic API execution.
It does not establish full parser isolation or full-package compatibility.

The manager also reran all 52 parser contract tests and checked every changed
contract and fixture test with live LSP diagnostics. All passed.
