# A3 triage producer API

msgloom.triage_pipeline is the finite application-layer producer for the
TRIAGE capability. It composes reviewed preparation, triage-input,
working-context, AI, AI-evidence, triage reconciliation, and persistence
contracts. It does not own CLI admission, scheduling, provider discovery,
source collection, report delivery, or the application terminal-outcome row.

## Trusted construction

TriageReplayPlan freezes exact request targets, accepted prepared, filter,
and group ResultRef values, source roles, prior triage results, topic
allocations, and live-versus-replay context choice. TriageProducerConfig
binds that plan to exact filter/rule/input configuration, prompt/schema/model
versions, TrustedPolicy, finite AI limits, request parameters, aggregate
upstream count/byte limits, part count, one-attempt-per-part policy,
code/configuration versions, an explicit total operation timeout, a cleanup
margin, and a claim lease covering the whole operation budget. The acceptance
deadline is operation_timeout_seconds minus cleanup_margin_seconds. A single
attempt timeout must fit inside that acceptance window, and the claim lease
must be at least the total operation timeout.

At construction the handler snapshots a fully revalidated semantic
fingerprint, including filter/rule/input configuration, roles, allocations,
prompt text, schema, model, and attempt limits. At each public operation it
strictly reconstructs nested Pydantic values and trusted policy maps and
rejects mutation before persistence I/O. Changed semantic choices require a
new handler/configuration and produce distinct attempt/part/result identities.

The handler rejects capability, target, or parameter mismatch before semantic
payload loading. It first reads only result metadata and checks aggregate
semantic byte_count and result count. Only exact acceptable results with
semantic data are loaded.

Live mode captures only WorkingContextConfig.selected_files and saves the
result before downstream use. The bounded model context contains capture time,
timezone, configuration reference, snapshot digest, file capture states,
content, modification times, and limitations, but never configured allowed
roots or local paths. This metadata is retained even when no files are
selected. Replay requires an exact accepted saved working-context result,
serializes those exact saved values and never calls capture. Deterministic
triage rules are evaluated from exact saved prepared records and saved before
input building.

## Durable ordering and ownership

The handler acquires one ClaimKind.TRIAGE claim. Every result it owns is
published with that ClaimToken. Application still owns trusted caller
admission and terminal OperationOutcome persistence.

The durable order is exact upstream metadata preflight; claim acquisition;
semantic loads; triage_rules@1; working_context@1 capture or replay load;
triage_input@1; exact triage_input_part@1 bytes; ai_request@1, traces and
ai_response@1; triage_part_state@1; reconciliation; and final triage@1 only
after complete required parent coverage.

EvidenceSession.begin receives the enclosing claim. A child AttemptIdentity
is fresh per part and differs from the enclosing triage attempt. A stale
claim cannot be bypassed to save semantic output. Cancellation drains
accepted evidence writes and claim release through repeated cancellation,
then re-raises caller cancellation. There is no automatic AI retry. The
handler independently applies the declared per-attempt timeout even to an
injected runner. It also applies the enclosing
acceptance deadline to preflight and production. Pure input building,
canonical part encoding/hashing, context serialization, parent validation,
candidate combination, and reconciliation run off the caller event loop;
owned off-loop work drains before cancellation is propagated. Accepted
persistence remains awaited. Incomplete/failed operation outcomes retain the
ordered durable result prefix already published.

## Multipart and deterministic holds

saved_part_payloads supplies the exact UTF-8 bytes sent as input_text. Before
execution the handler verifies those bytes against the snapshot and persists
the same canonical InputPart. Storage data_id is scoped by execution and
prompt version because InputPart meaning includes trusted versions; digest
and byte count remain exactly those declared by the snapshot.

Filtered exclusions and deterministic rule exclusions/conflicts never invoke
the runner. They become explicit EXCLUDED or REVIEW_REQUIRED dispositions.
Snapshot failures, absent required parts, failed parts, invalid model
structure, or reconciliation failures return INCOMPLETE; they never become
low-value or no-reportable-content decisions. Each successful part must
explicitly account for every source represented by that part's fragments; an
empty response cannot borrow coverage from a different part that happens to
reference the same source. triage_part_state@1 accepts only coherent terminal
COMPLETE/FAILED shapes with an exact ai_response@1 reference.

Multipart topic combination is keyed only by trusted allocation_key. Display
title is never an identity key. Parts sharing an allocation must agree on
stable topic fields or the operation remains incomplete. Distinct
allocations remain distinct even when titles or subjects match.

## Replay and continuity

Prior assessments are accepted only by exact saved triage@1 result
references. The producer derives PriorTopicAssessment from those durable
values, including retained source evidence. Callers cannot inject fabricated
prior assessment models.

A changed prompt creates a new prompt version, child attempt, input snapshot,
part-data identity, assessment reference, and final result identity. Replay
can reuse a confirmed prior topic identity only when reconcile_triage
evidence rules support continuity. Replay never recaptures working-context
files and never sends a report.

## Producer schema composition

The default persistence registries include triage_input_part@1 for canonical
part bytes and triage_part_state@1 for bounded immutable part diagnostics.
Both require semantic data. TRIAGE_PIPELINE_CODECS and
TRIAGE_PIPELINE_RESULT_SCHEMAS also expose these contracts for explicit custom
registries. The package loads execution lazily so default codec construction
does not create a persistence import cycle.

The integration regression runs actual preparation, triage, and report
handlers with the default registries and an injected AI runner. It reopens the
database and checks exact saved lineage and report source evidence.
Cancellation remains the operation outcome after an owned worker fails while
draining. The original cancellation cannot become an ordinary stage failure.

## Lineage contract

A3 separates source, prepared, and topic lineage. Upstream prepared/filter/
group results must carry exact VersionRef(kind="prepared", ...) lineage. The
producer validates and propagates those prepared references independently
from provider source versions. Topic allocations use
VersionRef(kind="topic-assessment", ...) so saved triage output composes
directly with reporting's topic-assessment contract. Prior assessments remain
separate exact saved triage references and are never inferred from source or
prepared identity.
