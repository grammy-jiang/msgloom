# A2 v2 P2-07: normalized content with a strict offset map (PROVISIONAL)

Code: `msgloom/a2_kedro/normalize.py`.
Tests: `tests/a2_kedro/test_p2_07.py`.

All names and bounds are PROVISIONAL. The module is self-contained. It
imports only the standard library. It does not import the C0-05 contract.

## Entry points

- `normalize_text(raw, *, max_chars, max_segments, max_irreversible_markers)`
  returns a frozen `NormalizedContent`.
- `validate_offset_map(content, raw)` re-checks every invariant and raises
  `NormalizeError` (a `ValueError`) on the first violation.
- `NormalizedContent.is_reversible(index)`: True when no marker overlaps
  the original range of segment `index`.

## Units

Offsets are Unicode code point indexes into a Python `str`. They are not
UTF-8 byte offsets.

## C0-05 contract alignment

The C0-05 contract (`contracts/zones.py` at commit 62a9a13) already defines
`NormalizedContent` with `Segment(normalized: Span, original_start,
original_end, mode)` and modes `identity` and `transformed`. This module
mirrors those field names, the mode names and the 8192 segment bound. It
differs in three ways:

1. The contract counts UTF-8 bytes. This module counts code points. A merge
   needs a conversion step (`len(s[:i].encode())`).
2. The contract stores digests and lengths, not text. This module stores
   `text` and `source_length`. A merge adapter must hash the texts.
3. The contract has no marker list. `markers` is new here. The contract
   allows an empty original range (a pure insertion). This module rejects
   one, because no transform here inserts text.

`NormalizedContent.project` of the contract is not ported.

## Transforms and markers

1. Strip zero-width (U+200B, U+200C, U+200D, U+2060, U+FEFF, U+180E) and
   bidi controls (U+061C, U+200E, U+200F, U+202A-U+202E, U+2066-U+2069).
   IRREVERSIBLE: one marker `strip` per contiguous run, with a count.
   Stripping U+200D changes some emoji sequences. This is a policy choice.
2. `CRLF` and `CR` become `LF`. Reversible. No marker.
3. A run of 2 or more space or tab becomes one space (`collapse_space`).
   A run of 3 or more `LF` becomes two (`collapse_blank_lines`).
   IRREVERSIBLE. Strip runs inside a collapsed run are absorbed into its
   marker, so a loss is counted once.
4. NFC per cluster. A cluster ends where the next character is a starter
   that does not compose with the last character. NFC can shrink the text
   (`e` + U+0301), grow it (U+0958) or join three characters into one
   (Hangul jamo).

## Map invariants (all checked by the validator)

- Normalized ranges are non-empty, start at 0, are contiguous and end at
  `len(text)`.
- Source ranges are non-empty, in bounds, ascending and non-overlapping.
- A source gap holds only stripped characters.
- `identity`: source slice equals normalized slice. `transformed`: it
  differs, and re-normalizing the source slice gives the normalized slice.
- Markers must equal the markers of a full rebuild. An unmarked loss, an
  extra marker, or a changed text is rejected. So the validator proves the
  map against this module's rules, not against another version's rules.

## Duplicates

The map is built from a left-to-right scan with a running cursor. It never
calls `str.find` and never de-duplicates by content. Equal fragments get
their own offsets. Only adjacent identity runs merge, and only when the
source ranges touch.

## Bounds and failure

- `max_chars` (default 1,000,000), `max_segments` (8192),
  `max_irreversible_markers` (1024). Each is a positive `int`.
- Exceeding any bound raises `NormalizeError`. There is no truncation.
- A lone surrogate raises. It has no UTF-8 form. Replacing it would be a
  silent, irreversible edit.
- The empty string is valid: empty text, empty map.
- Messages are fixed text. `repr` shows no text.

## Gaps and open items

- The marker cap is checked after the scan, not during it. Work is still
  bounded by `max_chars`.
- The validator rebuilds the text, so it costs O(n) like `normalize_text`.
- Collapse rules do not treat whitespace-only lines specially.
- No Unicode version pin. NFC results follow the Python `unicodedata`
  version.
