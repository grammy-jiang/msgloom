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
code/configuration versions, and a claim lease covering the configured
maximum AI elapsed budget.

The handler rejects capability, target, or parameter mismatch before semantic
payload loading. It first reads only result metadata and checks aggregate
semantic byte_count and result count. Only exact acceptable results with
semantic data are loaded.

Live mode captures only WorkingContextConfig.selected_files and saves the
result before downstream use. Replay requires an exact accepted saved
working-context result and never calls capture. Deterministic triage rules are
evaluated from exact saved prepared records and saved before input building.

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
then re-raises caller cancellation. There is no automatic AI retry.

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
low-value or no-reportable-content decisions.

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

## Opt-in producer schemas

Shared default registries are not mutated. This lane exports
TRIAGE_PIPELINE_CODECS and TRIAGE_PIPELINE_RESULT_SCHEMAS for manager
composition. They contain triage_input_part@1 for canonical part bytes and
triage_part_state@1 for bounded immutable part/attempt diagnostics.
Production composition must register both result schemas as semantic-data
results and add both codecs to its explicit semantic registry.
