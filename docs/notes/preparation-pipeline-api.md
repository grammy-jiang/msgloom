# A2 preparation pipeline API

## Scope

The preparation pipeline is the finite producer for the Phase 1 PREPARE
capability.  It implements an awaited OperationHandler and does not own caller
admission, terminal OperationOutcome persistence, an event loop, provider
fetches, discovery, scheduling, model calls, business actions, schema changes,
or parser implementations.

Application remains responsible for trusted caller admission and saving the
terminal operation outcome.  PreparationHandler receives an already-open
Phase1Persistence, a CollectedSourceReader, and one immutable PreparationPlan.
The later CLI can construct these values without granting authority through
OperationRequest parameters.

## Finite plan and admission

PreparationPlan fixes the attempt identity, exact source versions, live versus
replay mode, filter configuration, parser identities and profiles, resource
limits, code/configuration versions, aggregate byte limits, execution timeout,
and claim lease.  Parser formats are unique and source content cannot name a
module, path, profile, or setting.

OperationRequest must request PREPARE and its target_inputs must exactly equal
the ordered plan selection.  Request parameters are rejected.  Duplicate
parameter names are classified separately.  The plan rejects duplicate source
versions and requires the durable claim lease to extend beyond the execution
budget.

The durable claim key is a canonical digest of exact selected work and trusted
configuration, excluding the retry attempt identity.  Concurrent equivalent
work therefore cannot obtain a second owner even under a new attempt.  Replay
claims require the exact collected_selection ResultRef as an acceptable,
already-durable dependency.

## Evidence-first capture and replay

Live mode calls CollectedSourceReader.read_selection for every exact source,
checks the aggregate selected snapshot and declared saved-evidence byte budget,
and awaits every collected_selection@1 write before any parser starts.

Replay mode loads the exact accepted collected_selection@1 result and semantic
payload from Phase1Persistence.  It verifies the planned source and composite
selection reference and does not read current A1 projections.  Saved attachment
or alternate-representation bytes are still loaded and verified through the
reader using the references retained in the captured selection.

A body string inside a saved Graph JSON envelope is not parsed under the
envelope digest.  The producer first saves derived_bytes@1 with the exact UTF-8
text, component name, source location, captured-selection lineage, digest, and
byte count.  Only then is that exact derived byte sequence passed to
parse_isolated.  An alternate MIME representation that already has its own
verified saved bytes uses those bytes directly.

DerivedByteArtifactCodec is the bounded semantic codec for manager
composition.  Integration must extend ResultSchemaRegistry.phase1() with
derived_bytes@1 as semantic-data-required and add DerivedByteArtifactCodec to
the explicit SemanticDataRegistry.  This lane does not edit either shared
registry.

## Parsing and prepared records

All parsing routes through the reviewed production parse_isolated entry point.
PreparationPlan supplies exact trusted ParserIdentity, ParserConfig, and
ParserLimits values.  Work is admitted sequentially within the finite selected
record set; parser workers retain their own process time, memory,
decompression, output, and container-member ceilings.

Collected plain, HTML, MIME, and JSON representations route to the existing
MIME/HTML parser.  Attachment routing recognizes the reviewed Excel, PDF, and
Word formats from explicit collected content type and filename extension.
parse_isolated performs saved-byte identity, signature, and container
validation before dispatch.  Mismatched, unsupported, unavailable, missing, or
failed parsing becomes an explicit limitation rather than an empty success.

PreparedRecord keeps sender/author, recipients, source time, subject,
relationships, attachment references, verified saved-byte references, parser
outputs, and source limitations.  Plain body text remains readable.  Parsed
HTML body text becomes readable body text while the full ordered parser output
retains tables and links.

Meaning-bearing collected metadata is serialized deterministically into a
derived JSON artifact and parsed as a structured prepared content surface.  The
captured selection remains the lossless replay source for alternate
representations, collected metadata, unavailable associations, and source
locations that prepared@1 has no dedicated field for.

SourceMapping uses the vocabulary consumed by msgloom.triage.evidence:
subject/body and parsed_contents[N].blocks[M], with
table.cells[C] for mapped cells.  Body-derived parser mappings are owned by the
exact parsed-content reference.  Attachment parser mappings are owned by the
attachment VersionRef and retain the parser saved-byte provenance.

## Durable stage order and terminal behavior

For each source, the producer awaits prepared@1 after its captured selection
and derived parser inputs are durable.  It then saves a separate
filter_result@1 bound to the exact FilterConfig.  The prepared record's
filtering field stays
PENDING because FilterResult is authoritative and lossless.

Grouping starts only after all selected prepared and filter results are
durable.  Every group_result@1 lists the exact member prepared and filter
ResultRefs as dependencies.  Result identities include execution, attempt,
stage semantics, configuration version, and code version, so a later execution
or attempt cannot silently overwrite a historical result.

Parser limitations and retained source limitations make the operation
INCOMPLETE while leaving acceptable partial prepared/filter/group results
inspectable.  Unexpected producer failures return FAILED with already-durable
result refs retained.  Execution timeout returns INCOMPLETE and cannot publish
later prepared semantics after the timed-out parser step.

Cancellation is propagated only after accepted parser/persistence work drains
and the owned claim is finished as CANCELLED.  Repeated cancellation during
claim completion is observed without abandoning the finish write.  Safe
terminal claims are released for restart.  The execution timeout is strictly
shorter than the claim lease, so successful writes are admitted while the
producer's lease budget is still active.

## Composition surface

The public package exports PreparationHandler, PreparationPlan, SelectionPlan,
PreparationMode, ParserProfile, DerivedByteArtifact,
DerivedByteArtifactCodec, DERIVED_BYTES_KIND, and
DERIVED_BYTES_SCHEMA_VERSION.  No provider, CLI, schema, global registry, or
shared dependency surface is modified by this lane.

## R2 hardened boundary and identity rules

`PreparationHandler(persistence, reader, plan)` remains the only producer
constructor. At each `run(request)` boundary it reconstructs the complete
`PreparationPlan` through strict canonical validation, including nested
dataclasses, enums, filter rules, parser profiles, limits, finite numeric
bounds, and replay bindings. Invalid copied/model-mutated plans are blocked
before source-reader or claim work. Public failures are bounded
classifications and do not include rejected values.

Replay admission reads only result metadata first. The aggregate canonical
`collected_selection@1` semantic byte count must fit
`max_total_selected_bytes` before any semantic payload load and before
`acquire_claim(required_inputs=...)`. After a selection is available, its
declared unique saved-evidence byte counts are admitted before attachment/body
byte loading. `max_derived_bytes` is per derived artifact,
`max_total_derived_bytes` is aggregate derived UTF-8 input, and
`max_total_parser_output_bytes` bounds aggregate accepted parser wire output.
Parser-native limits remain independently enforced.

Every operation-owned append passes the acquired `ClaimToken` to
`append_result_with_data(..., claim=token)`. Persistence therefore fences the
write atomically against expiry, reclaim, terminal ownership, and execution
mismatch. A stale owner cannot publish late prepared/filter/group semantics.
Claim completion drains under cancellation; a stale cleanup result does not
replace the original cancellation/failure and cannot produce a COMPLETE
outcome. There is no implicit lease renewal.

Prepared semantic identity is a `VersionRef(kind="prepared", ...)` derived
from canonical prepared bytes, distinct from the original source VersionRef.
Prepared, filter, and group StageResults publish these prepared versions.
Prepared `input_refs` include the captured selection and every durable
`derived_bytes@1` artifact created for that record; saved attachment
references and parser provenance remain in the prepared record/source lineage.
Parsed-content versions fingerprint the exact composite selection, original
source, selected component, saved-byte identity, parser identity, parser
configuration, parser limits, and canonical accepted parser output.

Result IDs include a canonical fingerprint of the complete trusted plan in
addition to execution, attempt, stage tag, configuration version, and code
version. Changing parser profiles or other meaning-bearing plan semantics
therefore creates distinct immutable results even when callers reuse textual
execution/attempt/configuration identifiers. Historical result/data refs remain
loadable after restart.

Canonical codec, filtering, grouping, and prepared-version work is moved
off the event loop as finite owned work. Cancellation/operation timeout drains
accepted off-thread work before returning and discards results that complete
after cancellation. The package root imports codecs/models eagerly but loads
`PreparationHandler` lazily, allowing manager composition to register
`derived_bytes@1` without a persistence import cycle.

## Default composition and rejected content

The default Phase 1 registries include ``derived_bytes@1`` and require its
semantic payload. The full selection, derived bytes, prepared record, filter,
and grouping chain can be loaded after closing and reopening persistence.

A parser rejection, including input validation before child launch, adds the
``content-parse-failed`` limitation and retains the prepared record and other
parsed components. An aggregate parser output budget violation still fails
the operation. It cannot become an ordinary per-content limitation.

## Post-selection saved-evidence loss

A captured ``collected_selection@1`` remains authoritative when selected saved
component later disappears, becomes unreadable, or fails its recorded byte
count or digest. Preparation never recollects or substitutes current bytes.
The exact saved byte reference remains in the captured selection and, for
attachments, in the partial prepared attachment. The affected component is not
sent to a parser.

Saved component loading has a narrow failure classification. Evidence
availability, reference, and integrity failures after selection add
``saved-content-unavailable`` and allow unrelated verified metadata, bodies,
attachments, filtering, and grouping to publish as ``INCOMPLETE``. Reader
configuration/closed-state failures, cancellation, stale claim ownership,
source byte ceilings, aggregate selection/derived/parser-output ceilings, and
other producer failures remain fatal or retain their existing lifecycle
classification. ``SourceEvidenceLimitError`` distinguishes the configured
saved-byte ceiling from ordinary ``SourceEvidenceError`` without matching
exception text.

Replay uses the exact durable captured selection and repeats the same
availability checks against its saved byte references. A restart therefore
preserves the known selected version and honest unavailable-component state;
it does not consult mutable A1 projections or changed content.

## Stable semantic identity and durable lineage

Execution, attempt, result, and storage identifiers never enter prepared,
parsed, filter, or group semantic payloads or semantic versions. Derived UTF-8
parser inputs use a deterministic ``derived:sha256:<digest>`` saved-byte
reference, while their execution-scoped ``derived_bytes@1`` ResultRefs remain
durable dependencies of the prepared StageResult. The derived result itself
continues to depend on the exact captured ``collected_selection@1`` ResultRef.
This separates semantic byte identity from storage identity without weakening
evidence-first lineage.

Parsed-content versions bind the exact source and composite selection versions,
component, derived or collected saved-byte digest and count, parser identity,
parser configuration and limits, plan configuration/code versions, and
accepted parser output. Prepared versions bind canonical prepared bytes plus
the plan configuration/code versions. Filter and group StageResults retain the
prepared versions they consumed and their execution-scoped ``input_refs``.
Equivalent executions therefore append distinct immutable StageResults while
retaining identical semantic versions. A meaning-bearing byte, parser policy,
plan configuration version, or code version change creates a new affected
semantic version.

Replay and restart resolve through StageResult ``input_refs``, never by treating
the stable parser byte reference as a persistence key. Consumers validate
parsed provenance against the saved byte digest and count and retain the exact
captured-selection/derived-result chain; mismatched lineage or byte identity
fails closed instead of falling back to current source projections.

The preparation lane owns this classification and partial-result policy.
The source-reader change is limited to precise error typing for its existing
byte ceiling; it does not alter evidence lookup, containment, integrity,
transport, or collection behavior.
