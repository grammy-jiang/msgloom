# MIME, HTML, text, and JSON parser lane

**Scope:** synchronous mechanical extraction inside the later isolated parser
process.

The registry identity is fixed to:

- parser: `msgloom.mime-html`;
- version: `1`;
- backend: `stdlib-email+selectolax-0.4.12`.

The parser accepts only the reviewed `MIME`, `HTML`, `TEXT`, and `JSON`
formats. Its closed configuration is profile `mime-html-v1` with no settings;
unknown profiles or settings are rejected rather than ignored. A request
carrying another format or parser identity is also rejected before parsing.
Output provenance is copied exactly from the request. The later isolation
boundary verifies saved-byte hash/count before launch and validates encoded
output before persistence.

## MIME lifecycle and failure behavior

MIME uses the standard-library `email` parser. Parts are visited depth-first
with stable parser-local references: root `1`, children `1.1`, `1.2`,
and nested children continuing that numbering. Every retained part records its
parent, content type, disposition, content ID, and location. This preserves
mixed, alternative, related, attached-message, and multipart-attachment tree
relationships without inventing provider relationships.

Readable non-attachment `text/plain` and `text/html` leaves are
transfer-decoded and decoded with their declared character set. Unsupported
character sets, invalid bytes, transfer defects, and structural defects become
generic limitations. Limitation details never include source bodies, URLs, or
decoder exception text.

Attachment disposition applies to the complete subtree before multipart body
handling. The attachment node and traversable descendants remain MIME
metadata, but no readable descendant is emitted as message-body text. This
includes attached `message/rfc822` and multipart containers. Binary inline
or related leaves are metadata-only with an explicit skipped-content
limitation. Normal non-attachment multipart traversal remains depth-first.
MIME alternatives are extracted independently and carry a limitation stating
that equivalence or preferred alternatives were not inferred.

## HTML text, tables, order, and source mapping

HTML uses selectolax 0.4.12 with the Lexbor backend. Traversal is local to the
supplied text and never opens link, image, script, frame, or embedded-object
targets.

Normal-flow inline text retains source adjacency: the parser does not insert
spaces merely because text crosses an inline element. Explicit `br` and
block descendants retain newline boundaries so values such as `5` and
`10 units` cannot silently become `510 units`. List-item, blockquote, and
preformatted blocks are represented as paragraph-role blocks; preformatted
line breaks and interior spacing are retained. Table-cell text uses the same
boundary rules while excluding nested-table subtrees.

HTML tables preserve source row/cell order and map common positive `rowspan`
and `colspan` values onto stable one-based grid coordinates. Spanned source
cells carry `merged_range` in `RrCc:RrCc` form, and following cells skip
occupied grid positions. Malformed, zero, or structurally over-limit spans
cause the affected table to be skipped with an explicit limitation rather than
emitting plausible but incorrect coordinates.

Nested tables are emitted as separate table blocks and excluded from outer
cell text. The flat table/block contract cannot encode the nested table's exact
position between outer-cell text fragments, so every owning outer table gets
an explicit `html-nested-table-order-partial` limitation. This lane therefore
does not claim complete nested-table reading order. Locations remain the
stable traversal-index `DocumentLocation` mappings supported by the shared
parser contract; no shared `prepared@1` schema is changed here.

Headings, paragraphs, supported text blocks, tables, and standalone links
follow structural traversal order. Scripts and other active content are
skipped. Images and embedded content are not fetched or decoded and produce
explicit limitations. Nonempty HTML that yields no represented readable
content gets `html-no-readable-content`. The parser does not claim CSS visual
order, rendered layout, JavaScript output, remote-resource content, or full
accessibility semantics.

## Text and JSON representation

Direct text, HTML, and JSON inputs are strict UTF-8. Invalid encoding and empty
content are explicit limitations. No encoding guess is attempted.

JSON is parsed only to validate standard JSON syntax. `NaN` and `Infinity`
are rejected. Valid JSON is returned as its exact decoded source text, so key
order, nesting, array structure, and numeric spelling are not flattened or
silently normalized. The parser does not infer a provider schema or invoke AI.

## Resource limits and ownership

The parser consumes request limits in addition to later process-isolation
controls:

- the member ceiling bounds MIME nodes and HTML structural traversal;
- table spans/grid coordinates are additionally bounded by that member ceiling;
- the decompressed-byte ceiling is charged before readable decoded content;
- the output-byte ceiling is charged against source-derived semantic strings
  before blocks, tables, links, or MIME metadata are emitted.

When a ceiling prevents extraction, affected content is skipped with a safe
partial limitation. Tables are emitted whole or skipped rather than silently
truncated. The isolation codec remains responsible for the final exact
serialized-output bound, including provenance and diagnostic-envelope
overhead. OS time and memory enforcement remain outside this synchronous
parser.

This parser owns only mechanical extraction and safe coverage disclosure. It
has no persistence or attempt-completion authority. Its caller awaits the
isolated worker, validates output, and owns durable state transitions.
