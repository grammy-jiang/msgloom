# Phase 1 triage contract API

**Scope:** A3 deterministic and semantic contracts only.

This lane owns no SDK session, provider access, database schema, CLI operation,
or semantic registry composition. It consumes the reviewed VersionRef and
PreparedRecord contracts. The default Phase 1 registries include the closed
triage and deterministic-rule codecs beside the preparation/context codecs.
Accepted results require the corresponding validated semantic data.

The implementation targets the pinned Pydantic 2.13.5 API. Models use strict
validation, extra fields are forbidden, and instances are frozen. The codec
revalidates JSON on both encode and decode because model_construct() and
model_copy() can bypass ordinary construction validation. Validation failures
at the codec and reconciliation boundaries return fixed safe classifications
rather than embedding source values.

## Deterministic rules

TriageRuleConfig is an immutable versioned set of TriageRule values.
Predicates are a closed vocabulary over prepared facts: sender, author,
recipient, source type, exact/contained subject text, contained body text, and
aware source-time boundaries. There is no arbitrary expression evaluator or
regular-expression predicate.

evaluate_rules(records, config) applies AND within one rule and preserves every
matched effect independently. Output ordering is canonical by exact source and
rule reference, not caller order. Effects are exclusion, required priority,
minimum priority, and guidance. Guidance cannot exclude.

Required-priority disagreement, exclusion combined with priority work, and a
required priority below a stronger minimum create RuleReviewItem values. A
conflicted outcome has no accepted required priority. Reconciliation rejects a
semantic priority or disposition that would bypass saved deterministic
constraints. There are no built-in business rules or user defaults.

Priority order is Critical > Important > Normal > Low-value.

## Structured semantic result

TriageCandidate is the bounded structured-output shape for a later isolated AI
runner. validate_triage_candidate() is the safe JSON entry point and suppresses
Pydantic input echoes on malformed output. It retains topics, exact selected
source references, all rule matches,
reason, developments, actions, owner state, deadlines, risks, limitations, and
evidence. Owner state distinguishes known, unknown, and absent. A known owner
carries text; the other states cannot.

A deadline always retains original wording. An interpreted deadline is aware
and also records its timezone basis; ambiguity remains explicit. Evidence is
typed as source-statement or interpretation and references an exact source
version, optionally with the reviewed SourceMapping.

Every selected prepared source must occur in at least one topic or in exactly
one explicit SourceDisposition. A source cannot simultaneously be a topic
member and a disposition. Selection authority comes from the exact saved A2
FilterResult, not PreparedRecord.filtering. Missing/failed A2 work cannot
silently become Low-value or no-reportable-content. Saved filter exclusion,
filter conflict, deterministic exclusion, and rule conflict require their
matching explicit disposition/review.

Counts and text are bounded in the Pydantic models. TriageDataCodec caps the
canonical triage@1 payload at 4 MiB and uses sorted, compact UTF-8 JSON. It
implements the codec protocol consumed by SemanticDataRegistry but this lane
intentionally does not edit the shared registry.

## Topic identity and continuity

Titles are display text only. The semantic candidate carries an opaque
allocation_key; it never chooses a topic or assessment identity. Trusted
application code supplies TopicAllocation values containing exact topic and
assessment VersionRef values.

reconcile_triage(candidate, selected records, filter config/results,
TriageRuleEvaluation, topic allocations, prior assessments) validates and binds
the result. The function has no global registry, cache, database access, or
hidden mutable state. The caller persists allocations, accepted triage data,
the exact deterministic evaluation, and prior evidence used for continuity.
Replaying the same saved inputs therefore preserves the same identity decisions.

A prior continuation names an exact prior topic and assessment. The caller
must explicitly supply that PriorTopicAssessment; invented prior endpoints
fail. Confirmed continuity reuses the trusted prior topic identity and requires
evidence from both the current selected sources and caller-supplied prior
evidence. An uncertain continuation must retain a different topic identity.
Conversation membership, subject, title, and proximity are not consulted by
the reconciliation function and cannot merge topics. Multiple topics from one
communication group remain valid when source coverage and allocations support
them.

Saved TopicRelationship values preserve current/prior topic and assessment
endpoints, status, reason, and evidence. This is an assessment record, not a
mutable topic registry.

## Integration sequence

A later A3 handler should perform these steps in order:

1. Load accepted prepared@1 plus the exact saved A2 filter configuration and
   complete filter_result@1 coverage.
2. Replay the filter binding; pending/failed dependencies stop here.
3. Evaluate the exact triage rule configuration and durably save
   triage_rules@1 before semantic output depends on it.
4. Allocate candidate topic/assessment identities in trusted application code.
5. Supply only selected prepared content, deterministic facts, allocation keys,
   and explicitly selected prior assessment evidence to the isolated AI input.
6. Parse returned JSON with validate_triage_candidate(); malformed or
   oversized model output is not accepted semantic data.
7. Call reconcile_triage() with the exact saved bindings before persistence.
8. Encode the returned TriageData with TriageDataCodec and await the Phase 1
   write before any dependent report claims the exact triage@1 result.

These functions are synchronous and contain no owned background work or
cancellation point. A later async handler owns cancellation around AI work and
the existing awaited persistence facade; it must not publish a semantic result
until reconciliation and persistence both complete.

## Limits and failure behavior

The principal semantic bounds are 128 topics, 256 dispositions, 128 sources
per topic, 256 rule references per topic, 64 developments/actions/risks, 32
deadlines, and bounded evidence collections. Rule configuration is limited to
256 rules, 16 predicates and 8 effects per rule. Text fields use explicit
maximum lengths, with detailed semantic statements capped at 8,000 characters.

Extra fields, coercion, naive interpreted dates, malformed owner states,
duplicate selected inputs/dispositions/allocations, missing or invented source
coverage, omitted rule matches, priority violations, invented prior topics,
and ungrounded confirmed continuity fail closed. Codec errors deliberately do
not reproduce source values or Pydantic's detailed input echo.

## R2 boundary clarifications

### A2 to A3 persistence and input sequence

`PreparedRecord.filtering` is not the accepted A2 filter result. A2 deliberately
leaves `prepared@1` immutable and persists a separate `filter_result@1` for
each exact source. A3 therefore receives the exact `FilterConfig` plus complete
saved `FilterResult` coverage and replays `apply_filters()` against every
selected record. Configuration, source, effect and aggregate outcome must match
exactly. An included result can authorize a prepared record whose embedded
field remains PENDING; an embedded EXCLUDED field is not independent authority.

The required sequence is: persist accepted `prepared@1`; evaluate and await
persistence of exact `filter_result@1`; load those exact results/configuration
for A3; then persist deterministic A3 evaluation before accepting semantic
triage. Missing or failed filter work is a dependency failure, not Low-value or
no-reportable-content. Excluded results require an excluded disposition,
conflicts require review, and guidance alone never authorizes exclusion.

### Deterministic evaluation integrity

`RuleOutcome` summary fields are derived invariants over the complete canonical
`RuleMatch` set. Reconciliation does not trust separately supplied exclusion,
priority, guidance or review summaries. `TriageRuleEvaluation` binds the exact
`TriageRuleConfig` to canonical outcomes; each match must reference a configured
rule and exact configured effect. Reconciliation replays `evaluate_rules()`
against the selected prepared records and requires equality.

`TriageRuleEvaluationCodec` is the bounded canonical `triage_rules@1` codec
(4 MiB). It is registered as a required semantic payload. Conflicting
required priorities never select an arbitrary set member, so conflict evidence
and secondary review are stable across hash seeds and input permutations.

### Evidence and continuity

`TriageEvidence.source_ref` names the selected primary prepared record. Its
optional `SourceMapping` may instead name that record, an attachment reference,
or a parsed-content reference retained by the same `PreparedRecord`. This keeps
legitimate attachment evidence expressible. At reconciliation the mapping must
exactly occur in `PreparedRecord.source_mappings`; body/subject ranges are also
checked against the selected text. Invented fields, locations, ranges and
attachment/parsed-content mappings fail.

Without a mapping, source-statement evidence must occur in the selected subject
or body. Interpretation evidence requires an exact retained mapping. Endpoint
membership alone is therefore not proof that a source statement occurred.

Saved relationships require distinct current/prior assessment versions.
Confirmed continuity reuses the prior topic identity; uncertain continuity uses
a distinct topic identity. Confirmed saved data retains current-side evidence.
Reconciliation additionally
requires the exact trusted `PriorTopicAssessment`, grounds current evidence
against selected prepared data, and requires every claimed prior evidence item
to be present in that trusted prior assessment. A codec cannot establish
external persistence membership, so that trust check remains at reconciliation.
Current and prior evidence can refer to the same exact source version when an
explicit replay reassesses unchanged content. The new assessment version and
trusted prior assessment binding still remain required.

### Opaque public boundaries and qualification

Candidate, selected prepared inputs, filter configuration/results, deterministic
evaluation, allocations and prior assessments are fully revalidated before use.
Validation-bypass copies/constructions cannot reach binding logic, and public
errors use fixed safe codes without reproducing nested source/model values.

Mechanical qualification covers exact source/filter/rule coverage, replayed
deterministic effects, priority constraints, allocation/endpoints, evidence
mapping/ranges, aware deadline shape, and canonical persistence. Owner-fixture
qualification still owns semantic judgments: topic segmentation; unconstrained
priority; correctness of reasons, developments, actions, risks and limitations;
known/unknown/absent owner meaning; deadline interpretation/timezone basis; and
whether retained evidence is substantively sufficient for a business continuity
claim. Handler/runner integration and final semantic acceptance remain manager
scope.

## R3 mechanical evidence grounding

A `SOURCE_STATEMENT` is literal evidence, not a paraphrase. Reconciliation
requires its `statement` text to occur in available retained text. With a
mapping, the literal must occur inside the exact resolved mapping and, when
present, inside its character range. A known `VersionRef`, `SourceLocation`,
or `SourceMapping` membership is necessary but is not proof that content was
available or that the literal occurred there. Without a mapping, literal
statements may only be grounded in the selected record's subject or body.

`INTERPRETATION` is the representation for paraphrase, inference, and semantic
judgment. It requires an exact resolvable retained mapping. Reconciliation
checks that the cited content exists, but does not claim that the
interpretation is substantively correct. Business-semantic qualification
remains outside this mechanical contract.

The future A2 handler must emit evidence mappings using this closed producer
vocabulary. Primary subject/body mappings use `field="subject"` or
`field="body"`, name the exact `PreparedRecord.source`, and use a
`DocumentLocation`. Their optional offsets are character offsets into that
exact field. Parsed content uses
`parsed_contents[N].blocks[M]`, where both indices address the retained
`ReferencedParserOutput` and contiguous `ParserOutput.blocks` order. A
specific table cell may use
`parsed_contents[N].blocks[M].table.cells[C]`, where `C` is the retained
cell tuple index. Arbitrary attribute expressions are not accepted.

A parsed mapping names either the exact parsed-content reference or the owning
attachment reference. Attachment-backed mappings additionally require saved
bytes, the attachment's exact `parsed_content_ref`, and parser provenance for
those same saved bytes. Metadata-only, unsaved, or unparsed attachments cannot
support a source statement.

Locations are resolved against parser output, not trusted from the mapping
alone. MIME text blocks retain `MimePartLocation`; PDF text blocks retain
`PageLocation`; Word text blocks retain `DocumentLocation`; spreadsheet
cells retain `CellLocation`. A text block's location must equal the retained
block location. A table mapping at its table location exposes non-null cell
text in row/column order separated by newlines. A mapping at a unique cell
location exposes only that cell. Where several cells share a location, as Word
table cells can, the producer must use the explicit `.table.cells[C]` form.
Ambiguous cell locations fail closed.

Ranges are applied only after the resolver has selected actual mapped text.
They cannot point outside that text. Parser limitations and partial output stay
authoritative: only text actually retained in blocks/cells is evidence.
Limitations must remain visible to later triage/reporting; missing content is
not negative evidence.

Current-side continuity evidence is grounded through the same resolver. Prior
continuity evidence is different: reconciliation has no prior
`PreparedRecord` input, so it accepts only evidence exactly present in the
caller-supplied, trusted `PriorTopicAssessment.evidence`. It does not recreate
or weaken that saved prior evidence.
