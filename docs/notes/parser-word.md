# Word parser implementation note

**Scope:** isolated Phase 1 native Word parsing only.

## Identity and lifecycle

The lane exposes
`parse(request: ParserRequest, content: bytes) -> ParserOutput` with parser
identity `msgloom.word@1` and backend
`python-docx-1.2.0+lxml-6.1.3`. The only supported parser configuration is
profile `word-native-v1` with no settings; identity, profile, or setting
mismatches fail before native package parsing.

The function is synchronous and bytes-only. The later parser-isolation boundary
owns process wall time, memory enforcement, cancellation, and reaping. This
parser performs no filesystem discovery, provider access, database work,
network access, model download, conversion subprocess, or durable stage
transition. It verifies the supplied byte count and SHA-256 before parsing and
copies request provenance exactly into the output.

Legacy `.doc` has no qualified conversion profile. A request still uses the
closed `word-native-v1` parser profile, but the saved DOC bytes are not parsed
or converted: the result contains one `legacy-doc-unsupported` limitation and
no invented content. The parser does not install or launch LibreOffice.

## DOCX validation and limits

DOCX is treated as an untrusted ZIP/XML container before `python-docx` opens
it. Validation rejects a non-ZIP signature, duplicate or unsafe member paths,
encrypted members, missing core DOCX members, macros, malformed XML, and XML
DTD/entity declarations. DTD detection uses an encoding-aware XML tokenizer
and parsed document metadata, so UTF-8 and UTF-16 declarations are covered.
XML validation uses lxml with entity resolution, network access, DTD loading,
and huge-tree mode disabled; comments and processing nodes are skipped during
feature scanning.

The parser enforces the request's container-member and total decompressed-byte
ceilings before document traversal. Extracted text, links, merge metadata, and
limitation text are counted as UTF-8 semantic output and rejected when they
exceed the output-byte ceiling. The isolated process remains responsible for
the request's wall-time and memory ceilings.

Hyperlink targets are retained as inert data only. They are never fetched.
External relationships other than hyperlinks, and relationship types outside
the supported native set, produce an explicit
`unsupported-relationships` limitation.

## Ordering and locations

The main story is emitted first in its paragraph/table source order. Each
`DocumentLocation` names the exact OOXML part and zero-based block index
within that part. Unique header and footer parts follow in deterministic part
name order; their locations retain the original `word/header*.xml` or
`word/footer*.xml` identity. Word has no single semantic reading order across
independent header, footer, and main-document stories, so this deterministic
serialization does not claim one.

Tables remain structured `TableBlock` values. Cells retain one-based logical
OOXML grid positions, including rows with `w:gridBefore` or `w:gridAfter`
omissions; extraction owns each physical `w:tc` directly rather than using a
flattened `table.cell(row, column)` lookup. Horizontal and vertical merge
restart/continuation markup is represented as an explicit `RrCc:RrCc` span on
the starting cell rather than duplicating merged continuation cells. Malformed
grid coverage or vertical continuation ownership fails visibly instead of
misattributing text. Cell hyperlinks remain data attached to the cell. Nested
tables are disclosed as partial because they are not emitted as separate
ordered blocks.

## Coverage limitations

A successful DOCX parse always includes `word-feature-coverage`. The native
path covers paragraphs, tables, headers, footers, and hyperlinks; success does
not mean full OOXML document understanding.

Package inspection adds visible limitations when it detects text boxes,
tracked revisions, comments, footnotes/endnotes, images, embedded objects,
nested tables, or unsupported relationships. Those features are neither
executed nor silently treated as understood. Embedded objects and unsupported
stories are not flattened into ordinary paragraph text.

## Focused synthetic validation

The lane tests construct DOCX bytes in memory and cover paragraph/table order,
header/footer locations, inert hyperlinks, horizontal and vertical merged
cells, revisions, embedded objects, text boxes, comments, footnotes, and an
unsupported external relationship. Safety tests cover container mismatch,
DTD/entity declarations, macros, encrypted ZIP flags, malformed XML, member
count, decompressed-byte limits, semantic output limits, and saved-byte
identity mismatches.

These tests measure the native parser behavior only. They do not close the
later parser-isolation gate, broader Phase 1 integration, or external source
consent gates.
