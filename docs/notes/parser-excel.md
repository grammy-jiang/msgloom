# Spreadsheet parser implementation note

## Scope and API

The spreadsheet lane exposes the synchronous bytes-only function
parse(request: ParserRequest, content: bytes) -> ParserOutput from
msgloom.preparation.parsers.excel. The registered identity is msgloom.excel
version 1 with backend python-calamine-0.8.2+openpyxl-3.1.5.

The closed format set is XLSX, XLSM, XLS, XLSB, and ODS. The function does not
perform provider, network, database, or filesystem discovery. It is intended
to run later inside the separately owned isolated parser process.

## Lifecycle and failure boundary

The parser first verifies the saved byte count and SHA-256 digest, the exact
registered parser identity, the closed format set, and the closed request
settings. ZIP-based formats are inspected before either native parser is
called. The preflight rejects unsafe or duplicate member names, excessive
member counts, excessive declared decompressed bytes, missing required
package members, malformed ZIPs, and format/signature mismatches.

Encrypted ZIP members return an explicit ENCRYPTED limitation before native
parsing. OLE compound containers presented as XLSX/XLSM/XLSB/ODS fail closed
as detected-format mismatches; OLE magic is not treated as evidence of
encryption. ZIP packages must contain the required format-specific members and
the workbook content type must exactly match XLSX, XLSM, or XLSB. ODS retains
its exact mimetype gate. Legacy XLS still requires the OLE compound-document
signature.

For XLSX and XLSM only, openpyxl performs a targeted metadata pass after the
container gate. defusedxml must be active. Both metadata workbooks use
keep_vba=False and keep_links=False; one reads formula expressions and the
other reads only stored cached results. Cleanup ownership begins before the
first open, so partial construction failure closes every workbook already
opened. openpyxl never evaluates formulas. Metadata-pass failure is partial,
but values are omitted when requested hidden-row/column exclusion cannot be
verified.

Calamine is the value backend for every supported format. The parser closes
the workbook before return. Output is charged incrementally against the
request output ceiling. The later isolation lane remains responsible for the
hard wall-time, RSS, and final encoded-output enforcement.

## Order, coordinates, and values

Workbook sheet order is retained. Each represented worksheet becomes one
ordered TableBlock; sheets are not flattened into a document-wide table.
CalamineSheet.start is applied to every row and column so a used range that
starts at B3 still emits B3 as row 3, column 2. ParsedTable dimensions use the
absolute source extent so contract bounds remain compatible with those
original coordinates.

Strings, numerics, booleans, dates, datetimes, times, durations, and null
structural cells receive explicit value types. For XLSX/XLSM, bounded worksheet
XML records the exact set of source cell elements. Dense calamine padding is
therefore omitted, while explicit empty strings and formula caches remain
distinct from absent cells. Cached error, empty-string, zero, and false results
retain distinct types. openpyxl also restores error-cell identity that
python-calamine 0.8.2 otherwise loses. Merged ranges are attached to structural
cells. XLSX/XLSM hyperlinks are retained as metadata only and are never
followed.

XLS, XLSB, and ODS have no exact cell-presence metadata backend in this lane.
Calamine can represent both an absent padded position and an explicit empty
string as an empty Python string. Those ambiguous empty values are omitted
rather than claimed as known strings, and excel-cell-presence-unavailable makes
that loss visible.

For XLSX/XLSM formulas, the expression and stored cached result are separate.
If a stored cache exists, it becomes the displayed typed value and
cached_value. If no cache exists, the parser emits the formula without
inventing a result and adds excel-formula-cache-unavailable. XLS, XLSB, and
ODS do not have a second metadata backend in this lane, so formula-expression
metadata is explicitly partial there.

Number-format strings are not rendered into presentation text. An
excel-number-format-metadata limitation records the source coordinate and
format string while the typed raw value remains authoritative.

## Hidden content and unsupported workbook features

Hidden sheets, rows, and columns are excluded by default. The supported parser profile is `excel-primary-v1`. Unknown profiles and
settings are rejected with bounded errors that do not echo profile content.
The only accepted settings are:

- include_hidden_sheets=true|false
- include_hidden_rows=true|false
- include_hidden_columns=true|false

The defaults are all false. Hidden sheet state is available from calamine for
the supported workbook formats. Detailed row and column visibility is
available only in the XLSX/XLSM metadata pass. If requested row or column
exclusion cannot be verified (metadata failure, missing per-sheet metadata, or
XLS/XLSB/ODS), cells are omitted rather than treated as visible and explicit
visibility-unavailable limitations are emitted. Both unverifiable dimensions
must be explicitly included to emit their cells. Cell-specific limitations do
not reveal metadata from rows or columns excluded by the policy.

VBA projects are never executed or extracted. Embedded workbook objects are
not parsed. External workbook links are not fetched. ZIP member presence is
used only to disclose these limitations. Non-worksheet sheet types are
skipped with an explicit unsupported limitation.

XLSB and ODS expose calamine values and sheet metadata but not detailed
formula, hyperlink, formatting, row/column visibility, or exact cell-presence
metadata. XLS adds calamine merged-range support but otherwise has the same
detailed-metadata and cell-presence limitations. This is a deliberate backend
boundary rather than inferred data.

The supplied valid XLSB fixture also establishes a narrower value-backend gap.
Its controlled writer round-trip contains numeric C2=42 and C4=5. A bounded
probe of xl/worksheets/sheet1.bin finds the corresponding compact numeric
record payloads at byte offsets 152 and 279, but python-calamine 0.8.2 reports
start=(1, 0), end=(3, 1) and returns only columns A:B. The parser does not
reconstruct BIFF12 values speculatively. Every XLSB parse therefore emits
excel-xlsb-value-coverage-unverified: returned cells are usable evidence, but
complete XLSB cell-value coverage is not qualified with the pinned backend.

## Synthetic coverage

Focused fixtures cover an OOXML used range beginning at B3, multiple and
hidden sheets, hidden rows and columns, strings, numerics, booleans, errors,
dates, times, null structural cells, formulas with cached and unavailable
results, hyperlinks, merged ranges, number-format visibility, inert macro and
embedded members, and external-link package members. A hand-built ODS package
covers leading empty offsets and typed calamine values.

The repository does not contain downloaded or personal workbook fixtures.
The lane includes two supplied synthetic read fixtures only: a valid legacy XLS
generated from controlled literals with xlwt 1.3.0 and a valid XLSB generated
from controlled literals with SheetJS CE 0.18.5. Neither writer is a product
dependency. The XLS fixture qualifies typed B3/C3/B4 coordinates and the
explicit metadata/cell-presence boundary. The XLSB fixture qualifies the cells
the pinned reader does return, sparse/empty ambiguity, strict package identity,
and the documented numeric value-coverage gap.

## Coordinator benchmark and acceptance probes

Use only synthetic, non-personal workbooks. For XLS and XLSB acceptance,
export a coordinator-generated workbook containing leading blank rows and
columns, two sheets, typed cells, a formula with a stored result, and a merge.
Verify sheet order, absolute coordinates, typed cached values, and the
documented partial metadata limitations. Do not add a downloaded corpus.

For resource qualification, generate XLSX and ODS workbooks at increasing
sheet and cell counts. Run the parser through the isolated process boundary
and record p50/p95 wall time, peak RSS, decoded output bytes, and input versus
declared decompressed bytes. Repeat with sparse leading offsets so coordinate
preservation is measured independently from dense-cell throughput.

Probe the fail-closed gates with synthetic ZIPs that exceed the member limit,
exceed the declared decompressed-byte limit, contain duplicate or unsafe
member names, present arbitrary OLE bytes as OOXML, and set an output ceiling below the
fixture result. Arbitrary OLE bytes must not be labeled encrypted; only a
positive native password-protection signal may produce that classification.
The expected result is bounded rejection or verified encryption, never a retry
or partial silent success.

The coordinator should also rerun the focused suite with:

    .venv/bin/pytest -q tests/parser_excel
    .venv/bin/ruff check msgloom/preparation/parsers/excel*.py \
        tests/parser_excel

Static type and live-LSP checks remain part of integration validation.
