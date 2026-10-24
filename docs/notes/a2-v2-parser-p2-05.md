# A2 v2 parser P2-05: spreadsheet parser (PROVISIONAL)

Code: `msgloom/a2_kedro/parsers/spreadsheets.py`.
Tests: `tests/a2_kedro/test_p2_05.py`, `tests/a2_kedro/test_p2_05_hostile.py`.

All names and bounds are PROVISIONAL. The parser reuses `ParserReceipt` and
`CellKind` from C0 and adds no wire name.

## Entry point

- `parse_spreadsheet(data: bytes) -> SheetResult`
- `SheetResult.to_receipt(worker_version) -> ParserReceipt | None`

The parser never raises for workbook content. A non-bytes argument raises
`A2ContractError` with a fixed message.

## Supported-format table (probed, not from memory)

Probe: openpyxl 3.1.5 and python-calamine 0.9.0 in the project venv.
Fixtures were built in code. No XLSB writer exists in the environment.

| Format | openpyxl | python-calamine | Admitted by the parser |
| ------ | -------- | --------------- | ---------------------- |
| XLSX | read, formula text and cached value (two passes) | read, cached value only, merged ranges, sheet visibility | Yes, openpyxl |
| XLSM | read; `keep_vba=False` ignores macros | not probed | Yes, openpyxl; `macros` flagged |
| XLSB | cannot read | documented, NOT probed (no fixture) | No: `unsupported_format` |
| ODS | cannot read | read, cached value only; no formula text, no hidden row, `merged_cell_ranges` is `None` | No: `unsupported_format` |

Why ODS and XLSB are refused: calamine allocates a dense grid from the first
to the last cell. Probe results:

- XLSX with `A1` and `XFD1048576` filled: calamine aborts the whole process
  (`memory allocation of 549755813888 bytes failed`, exit 134). No Python
  exception. `except` cannot save the worker.
- ODS with repeated rows and one far cell: calamine raises
  `Cell limit exceeded (16778184571 cells requested, max 100000000)`. Its
  own cap is 100 million cells, which is still gigabytes of memory.

A safe use of calamine needs a bounded pre-scan of the real cell extents
(expat for ODS, a BIFF12 record walk for XLSB). A working version exists
(773 lines, not in this commit). It does not fit the 500-line module rule
with the allowlist of one module file. See "Follow-up".

## Outcome rule

- `COMPLETE`: no limitation.
- `INCOMPLETE`: at least one limitation and at least one sheet read, or a
  hard limit before parsing (`size_limit`, `zip_limit`).
- `FAILED`: `empty_file`, `unsupported_format`, `password_protected` or
  `corrupt`, and no sheet read. `to_receipt` returns `None`.

`to_receipt` maps every limitation to `limit_hit == "bytes"`, as in P2-02.
`LimitHit` has no value for malformed or unsupported content.

## Formula and cached value

- `data_only=False` pass gives `Cell.formula` (text with leading `=`).
- `data_only=True` pass gives `Cell.value` (cached). Nothing is evaluated.
- A formula with no cached value: `formula_uncached` is true,
  `kind == "empty"`, and `formula_without_cache` makes the result
  `INCOMPLETE`. It is never a silent empty value.

## Hidden state

Sheet `state` is `visible`, `hidden` or `veryHidden` (openpyxl names).
`Sheet.hidden_rows` and `hidden_columns` are zero-based. `Cell.hidden_row`
and `hidden_column` repeat the flag per cell. Hidden content is still
extracted and flagged. A hidden row range (`<row hidden>`) is per row. A
`<col min max hidden>` range is clipped to 16 384 columns.

## Block IDs

- Sheet: `s{sheet_index}`.
- Cell: `s{sheet_index}!{A1}`, for example `s0!B2`. Rows and columns are
  zero based in the fields and one based in the A1 text.

## Limitations (closed, content-free)

`empty_file`, `unsupported_format`, `password_protected`, `corrupt`,
`size_limit`, `zip_limit`, `sheet_limit`, `cell_limit`, `text_limit`,
`dimension_limit`, `formula_without_cache`, `merged_cells`, `comments`,
`charts`, `images`, `drawings`, `pivot_cache`, `external_links`,
`embedded_objects`, `macros`.

Package content is detected by part name (`xl/comments*`, `xl/charts/`,
`xl/chartsheets/`, `xl/media/`, `xl/drawings/`, `xl/pivotCache*`,
`xl/pivotTables/`, `xl/externalLinks/`, `xl/embeddings/`,
`xl/vbaProject.bin`). Merges are found in the sheet scan (`mergeCell`).
Any such content makes the result `INCOMPLETE`. The content is not
extracted.

## Bounds

`MAX_BYTES` 32 MiB, `MAX_UNCOMPRESSED` 64 MiB (actual bytes, counted while
streaming; a member larger than its declared size is `corrupt`),
`MAX_ENTRIES` 2048, `MAX_SHEETS` and `MAX_CELLS` (the C0 limits 256 and
8192), `MAX_TEXT_CHARS` 1 000 000, `MAX_CELL_CHARS` 32 767,
`MAX_GRID_AREA` 2 000 000.

## Hostile input

- The declared `<dimension>` is never used. One expat scan per sheet finds
  the real extent of cells that hold `<v>`, `<f>` or `<is>`. Styled empty
  cells do not count.
- `openpyxl` iterates only `max_row` and `max_col` from the scan, limited
  by `MAX_GRID_AREA`. A sparse far cell gives `dimension_limit`, not an
  allocation.
- Expat rejects `DOCTYPE` and entity declarations (`corrupt`).
- Duplicate ZIP member names, ZIP-level encryption flags, and OLE2
  containers with an `EncryptedPackage` stream are detected from bytes.
- Input is never opened from a path. Macros do not run. External links are
  not followed (`keep_links=False`).

## PII

`repr` shows counts only. Limitation codes are fixed text. Library
exception text is dropped and never stored.

## Known gaps and follow-up

- ODS and XLSB are refused (see above). Follow-up: allow a second module
  (for example `parsers/sheet_scan.py`) and adopt the bounded pre-scan. XLSB
  hidden rows and columns would still be unchecked.
- `PartFormat` has only `xlsx`. XLSM, XLSB and ODS need a C0 change before
  they can enter `ParsedParts`. No `to_records` helper is provided; cell
  digests for `CellRecord` need that contract decision first.
- Hidden rows use a set, bounded only by the file size cap.
- A cell with an empty-string cached value is treated as empty.
- `xl/worksheets/*.xml` scan relies on `openpyxl` private `_worksheet_path`
  (pinned 3.1.5).
- Comments, charts, images, merges and similar content are flagged, not
  extracted.
- Hyperlinks, data validation and conditional formats are ignored and not
  flagged.
