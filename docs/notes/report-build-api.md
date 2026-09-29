# Report build API

The msgloom.reporting package owns A5 report selection, saved report
construction, Jinja rendering, and the finite REPORT_BUILD handler. It does not
own delivery, scheduling, CLI composition, shared registries, provider
discovery, credentials, or business actions.

## Inputs and selection

ReportPolicy is trusted configuration. It explicitly binds a versioned policy,
owner destination, aware due time and timezone, eligible priorities, due mode,
repeat policy, and reminder policy. There are no implicit reporting defaults.
ReportSelectionPlan freezes the exact request targets, durable triage@1 result
references, explicit assessment choices for conflicts, prior-report evidence
keyed by policy plus assessment, pending-newer warnings, and optional
already-saved source links.

Only acceptable saved triage@1 results are eligible. Multiple assessment
versions for one topic fail closed unless the trusted plan selects exactly one.
An uncertain triage relationship is not used to merge identities. Previously
reported assessments are reconsidered only under the explicit reminder/repeat
policy. Pending newer work is retained as a warning against the selected
assessment; it cannot silently make an older assessment look current.

## Saved report and codec

SavedReport is the complete semantic report@1 product. It binds one report
identity to the policy/destination, exact source triage results, exact topic
and
assessment identities, overview, complete topic details, source messages,
labelled source-statement/interpretation evidence, actions and owner
uncertainty, deadline wording/interpreted time/timezone/ambiguity, risks,
priority reasons, limitations, pending work, renderer version, and exact output
parts.

ReportCodec is the closed canonical codec declaration for manager composition
into SemanticDataRegistry. This lane intentionally does not edit the shared
registry. The existing ResultSchemaRegistry.phase1() already reserves report@1
and requires semantic data.

Coverage validation compares exact topic/assessment identities and essential
content. Rendered validation additionally checks each topic's explicit
topic-to-part mapping and its essential fields. Counts or self-reported
coverage
metadata are not accepted as proof.

## Rendering

render_report uses packaged Jinja templates with StrictUndefined; HTML uses
autoescaping. Source values are template data. Source links must be explicit
saved HTTP(S) URLs without user information; absent links remain plain source
references. JavaScript/data URLs are rejected.

Each saved part contains exact plain text and HTML. A single-part report is
preferred. If it exceeds the configured bound, topics are split
deterministically into complete topic parts under one report identity. A topic
that cannot fit is rejected rather than truncated. The total byte and part
limits are trusted explicit configuration. Retry/delivery code can therefore
reuse the exact saved outputs without rerendering.

## Handler ownership and recovery

ReportBuildHandler implements the shared awaited OperationHandler shape. The
Application remains responsible for trusted caller admission and terminal
OperationOutcome persistence. The handler verifies REPORT_BUILD, exact target
references, and exact trusted parameters before claiming work.

The handler first inspects exact declared triage and history metadata and
enforces the aggregate semantic byte ceiling. It then acquires the existing
per-policy REPORT_BUILD durable claim with those exact durable dependencies,
loads only admitted semantic inputs, freezes selection, builds and renders,
atomically writes the report@1 stage result plus semantic payload, then finishes
the claim. Cancellation
drains accepted persistence work before claim completion. The configured claim
lease must exceed the finite operation budget; elapsed lease checks prevent a
known-expired owner from returning success. Persistence ownership errors fail
the operation rather than claiming success.

No numerical semantic release threshold is asserted by this API. Those
thresholds remain manager/user acceptance decisions.

## R2 durability and acceptance boundaries

Before Jinja rendering, the handler revalidates the trusted policy, selection
plan, renderer configuration and handler configuration, admits only the exact
declared triage results, and sums their saved semantic byte counts. The
configured aggregate input ceiling is enforced before any triage semantic
payload is loaded. The plan itself bounds the input count.

The handler then resolves the selected assessment versions and persists a
report_selection@1 result plus FrozenReportSelection semantic payload. That
snapshot binds the full policy and plan, renderer limits, code version, trusted
request parameters, exact input result/data integrity references and selected
topic/assessment versions. ReportSelectionCodec is the closed bounded codec
declaration for manager composition. This lane does not edit shared registries.
A render failure therefore leaves the selection evidence durable.

Prior-state suppression remains keyed by the complete policy reference plus
assessment. Every prior state names durable report_submission@1 evidence and is
resolved through the typed history resolver described below. Metadata
acceptability alone is not delivery evidence. No live receipt discovery occurs
during report selection.

Upstream StageResult limitations are retained alongside topic-local limitations
and pending-newer warnings in the saved report limitation set. Pending work
remains explicit and does not replace the selected assessment.

Rendering is accepted blocking work owned by the handler and runs on a worker
thread. Jinja output is consumed incrementally and stops before crossing a
configured part or total byte ceiling; a complete topic is never truncated.
Cancellation and timeout drain accepted rendering before claim cleanup, and
the operation deadline is checked again after that drain. An expired render
cannot publish an acceptable report.

The handler has two persistence append sites, in this order:
report_selection@1 before rendering, then report@1 after rendered coverage
validation. Both use the reviewed claim-bound append API with the exact acquired
claim token. This lane does not implement a second claim mechanism.

Rendered coverage is structural. Overview identity and essential summary
content must occur in the overview section, while exact topic/assessment
identity, priority and reason, developments, action owner state/value, original
and interpreted deadline details, timezone basis and ambiguity, risks, source
references, evidence-kind labels, topic limitations, pending warnings and
report limitations are checked in their required sections. Saved HTML is
parsed as markup: source text remains escaped data, only the template
tag/attribute surface is accepted, and links must remain safe HTTP(S) URLs.
The report codec repeats semantic and rendered coverage checks without changing
the stored output bytes.

Report interval policies use elapsed instants, comparing in UTC. The configured
timezone must resolve through the IANA database and due_at must represent the
same local wall time and offset in that zone. This preserves fold-aware
fall-back behavior and spring-forward elapsed intervals. Original deadline
wording, interpretation, timezone basis and ambiguity remain unchanged.

## R3 structural, history, and claim closure

R3 admits every declared input by metadata before claim acquisition. It validates
and sums semantic byte counts for all triage inputs and any delivery-history
semantic payloads before claim acquisition; only after that bound passes may
claim validation or semantic resolution load payload bytes. The operation uses
one absolute acceptance deadline beginning before metadata admission and
covering claim acquisition, loading, selection, codec/reference construction,
rendering, publication, and completion. Synchronous codec/render work is
rechecked against that deadline before publication. Owned render work is
off-loop and drained through repeated cancellation.

Both report_selection@1 and report@1 publications pass the exact acquired claim
to the claim-fenced atomic result/data append API. There is no unfenced
fallback. A stale, expired, reclaimed, terminal, or execution-mismatched owner
therefore cannot publish either semantic product. Cleanup is drained without
replacing the original cancellation or failure; a failed outcome retains any
selection/report result references that had already become durable.

Prior report state is not evidence by itself. A configured handler with prior
state requires a ReportHistoryResolver. Its inspect method returns bounded
ReportHistoryMetadata without loading receipt semantic data, so the handler can
perform pre-claim byte admission. After claim acquisition, resolve returns
ReportHistoryEvidence: the exact durable report_submission@1 reference, report
VersionRef, complete policy VersionRef, assessment VersionRef, aware reported
time, receipt integrity VersionRef, optional semantic-data integrity reference,
and an external effect of only ACCEPTED or CONFIRMED. Every field must exactly
match the trusted prior state and inspected metadata. UNKNOWN, REJECTED,
NOT_STARTED, a forged timestamp, or another policy identity sharing a version
string fails closed. The verified receipt basis is copied into
FrozenReportSelection.history for restart/replay.

Rendered validation is exact and format-local. Every part number must be unique
and consecutive and the ordered topic-to-part mapping must equal the saved topic
order. Plain and HTML outputs are independently reproduced from the frozen
semantic report and compared byte-for-byte to the saved strings. HTML is also
parsed with strict allowed tags/attributes, balanced non-void tags, explicit br
void handling, non-nested unique article boundaries, and exact source-link href
bindings. Business text containing strings such as DETAILS, TOPIC, or PENDING
WORK remains ordinary template data and cannot create parser structure.

FrozenRendererConfig uses the same finite bounds and coherence rule as
RendererConfig. Frozen selections validate report/policy/topic/assessment
reference kinds, exact triage@1 result/data bindings, selected identities, and
the complete ordered history basis. Saved reports validate exact reference
kinds, consecutive part numbering, and ordered topic mapping. Both codecs still
strictly revalidate nested values and canonical bytes, so model_copy bypasses
and noncanonical replay fail without exposing business text.

The package root no longer eagerly imports the persistence-backed handler.
ReportBuildHandler and ReportHandlerConfig are loaded lazily, allowing the
shared semantic registry to import report codecs during persistence package
initialization without a reporting/persistence initialization cycle.

## Integrated registry and cleanup

The default Phase 1 composition registers both ``report_selection@1`` and
``report@1`` as required semantic products. The wheel includes the report
subpackage's Jinja templates. A default-registry restart test reloads both
products and checks exact saved content.

Canonical selection and report validation run off the caller event loop.
The handler drains this owned work before propagating cancellation. Stale
claim errors during terminal cleanup do not replace the original cancellation
or failure. Deterministic codec barriers check both publication boundaries.
