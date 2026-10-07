# Phase 1 triage input API

**Scope:** pure A3 input selection, structural snapshot construction,
splitting, and handler handoff only.

This lane owns no provider/filesystem discovery, SDK/model call, database
schema, global semantic registry, CLI, handler, or persistence implementation.
It consumes reviewed prepared@1, filter_result@1, group_result@1, and
triage_rules@1 values and exact saved references. Public work is synchronous,
immutable, and has no background work or cancellation point.

## Selection boundary

TriageSelection binds each exact prepared source to both its saved ResultRef
and SemanticDataRef plus a fully revalidated PreparedRecord. It also carries
exact saved filter and group bindings, the FilterConfig needed to replay
filtering,
one saved TriageRuleEvaluation binding, a caller-selected SourceRole for every
source, the exact working-context snapshot VersionRef, and trusted prompt,
model, output-schema, and triage-input configuration versions.

validate_selection() re-encodes and decodes every supplied saved value through
its reviewed codec. It verifies each semantic digest/byte count and result
kind/schema, requires unique/full prepared/filter/role source coverage, replays
apply_filters(), replays group_records(), and replays evaluate_rule_set().
Model-copy/model-construct bypasses therefore do not cross the public boundary.
Public validation errors use fixed classifications and do not reproduce source
values.

A saved filter result is the A2 authority; PreparedRecord.filtering is not used
as a substitute. The exact FilterConfig is required because a result reference
alone cannot prove that saved effects match the prepared value.

Excluded or conflicting filter results and deterministic rule exclusions or
conflicts become HeldSource values with explicit reasons. They remain in the
persisted snapshot but are not emitted as ordinary semantic AI input. Guidance
remains semantic input.

Only GroupStatus.CONFIRMED grants multi-record unit authority. Uncertain and
None members are separate units even when subjects or content match. To Do,
OneDrive, and Contacts remain separate contextual units. Independent groups and
source scopes are never joined by subject or meaning.

## Structured AI-input snapshot

build_triage_input(selection, config) returns immutable TriageInputSnapshot.
It has stable content-derived unit/part identities and hashes over the
validated selection, trusted configuration, exact saved references, and
meaning-bearing fragment content. The snapshot also retains the canonical
selected source/role bindings so a saved fragment cannot silently move to an
unselected source or change its temporal role. A separate selection-binding
hash ties those bindings and saved semantic references to the full validated
selection hash, so recomputing only the outer snapshot hash cannot replace
them. Display titles are never identity.

Each active prepared record, its exact filter result, deterministic rule
outcome, and grouping evidence are represented as typed, path-addressed
SemanticFragment values. Container markers retain object/array shape and order.
Scalar/text paths retain the original prepared structure, including:

- body/subject, participants, source time, and native relationships;
- attachment references and explicit unavailable/partial limitations;
- ordered parser blocks and source locations;
- tables, cell row/column/coordinate and value type;
- formula and cached-value fields independently;
- links and MIME relationship facts; and
- exact prepared SourceMapping values.

Source strings are always data fields. They do not carry application authority
to fetch sources, change scope, execute tools, or alter configuration.

RepetitionPolicy.remove_exact_text_repetitions is opt-in. When false, all
repetitions are preserved. When true, removal is limited to byte-for-byte equal
prepared body or parsed text occurrences inside one already-authorized unit.
Each removed occurrence remains a REPETITION fragment naming the retained exact
source/path. Metadata, formulas, cached values, coordinates, links, rule
constraints, roles, and cross-unit occurrences are never deduplicated.

## Serialized-byte splitting and coverage

SplitBudget supplies a finite UTF-8 serialized-byte ceiling and finite
part-count ceiling. split_unit() measures canonical encoded InputPart bytes,
not characters or tokens. No tokenizer guarantee or token estimate is made.

Structured containers and scalar metadata are indivisible. Only typed text
leaves are split, at Python character boundaries that preserve valid UTF-8.
Each text chunk retains its exact original character range and structural path.
Large bodies, parsed text blocks, and individual table-cell text therefore
split without chopping arbitrary JSON or flattening surrounding structure.

If an indivisible fragment cannot fit, or the part-count budget is exhausted,
the snapshot is explicitly incomplete. CoverageFailure records the first unsent
occurrence, an exact partial-text offset when applicable, remaining occurrence
count, and a digest over that remaining coverage. No truncated unit is
represented as complete.

Each occurrence manifest binds its source, role, namespace, structural path,
fragment kind, and text length. The codec recomputes occurrence and part
identities instead of trusting caller-supplied IDs. It also requires each
active selected source to occur in exactly one unit and each held source to
remain outside ordinary AI parts.

For complete units, TriageInputCodec proves every occurrence appears exactly
once, reconstructs split text to its exact original fragment, and verifies the
unit hash against that reconstructed content. Split text ranges must be
contiguous from zero through original length. An incomplete unit instead marks
its commitment as retained-prefix: its unit hash covers only the fragments
actually retained in saved parts. CoverageFailure separately identifies the
unavailable suffix and optional partial-text boundary. That suffix digest is a
coverage-manifest commitment, not a claim that omitted source content remains
verifiable from the snapshot. Parts are scoped to one unit only. A later
semantic combine must never merge parts from different unit identities.

## Codec and handler handoff

TriageInputCodec implements canonical triage_input@1. The default Phase 1
registries require its validated semantic payload for accepted input results.
The fixed codec ceiling is 64 MiB and every snapshot also carries a
trusted max_snapshot_bytes ceiling no larger than that value. Encoding and
decoding fully revalidate nested models, canonical JSON,
configuration and snapshot hashes, reference kinds/schemas, content-derived
part identities, unit bindings, coverage, the configured serialized byte
ceiling for every part, and the configured per-unit part-count ceiling.
Rehashing a snapshot after lowering those limits cannot make oversized saved
parts valid.

The later handler sequence is:

1. Load exact accepted prepared/filter/group/rule values and references.
2. Build TriageSelection with explicit earlier/new roles and context/version
   references.
3. Call build_triage_input() and persist its triage_input@1 snapshot before any
   AI call.
4. Call saved_part_payloads() and persist each exact canonical part byte string
   under its returned integrity reference before that part is consumed.
5. Retain PartExecution state for every exact reference. Pending and failed
   parts remain visible; they are not silently dropped or treated as complete.
6. Supply only saved part bytes for one unit to the isolated AI boundary.
7. Before parent semantic combination, call validate_parent_part_states(). It
   revalidates the snapshot and every typed PartExecution value, requires an
   explicitly complete snapshot with at least one part and exact full
   part-reference coverage, and returns true only when every part completed.
   Incomplete, held-only, pending, and failed inputs return false rather than
   gaining completion eligibility.
8. The parent must additionally validate the downstream structured candidate
   against all source coverage/rule constraints before persisting accepted
   triage@1 data.

The handler owns awaited persistence, AI cancellation, retry state, and parent
result lifecycle. This pure lane does not publish a stage result, start a
model, or claim that a failed/pending part has semantic output.

## Bounds and failure behavior

Selection is limited to 256 prepared sources and units. A unit is limited to
100,000 structural occurrences and one build to 200,000 occurrences in total.
Fragment construction consumes that aggregate budget incrementally rather than
first expanding an unbounded fragment graph. Part count is at most 512 per
unit; each part is between the configured 512-byte minimum and 4 MiB maximum.
Snapshot bytes are explicitly configured from 4 KiB through the fixed 64 MiB
codec ceiling. The build also applies a finite 64 MiB validated-selection
serialization bound and stops when accumulated part bytes already exceed the
snapshot ceiling.

Invalid saved integrity, incomplete source coverage, filter/group/rule replay
mismatch, configuration-version mismatch, unauthorized grouping, malformed
nested values, corrupted part references, duplicate coverage, gaps/overlaps,
or noncanonical stored JSON fail closed with bounded public classifications.
No source fetching, filesystem access, provider access, or persistence side
effect occurs in these functions.
