# Phase 1 AI evidence adapter

## Boundary

`msgloom.ai_evidence` is the durable evidence adapter for the reviewed
`msgloom.ai` execution boundary. It does not construct an `AIRunner`, invoke
the SDK, claim triage work, validate triage meaning, or turn a failed attempt
into a business disposition.

The adapter declares three semantic schemas:

- `ai_request@1` stores the exact public `AnalysisAttempt`, its declared
  durable prerequisite result references, and the schema/model values resolved
  from a caller-supplied `TrustedPolicy`.
- `ai_trace@1` stores one exact exposed `TraceEvent` and the saved request
  reference.
- `ai_response@1` stores the exact terminal `AnalysisResponse`, the saved
  request reference, the ordered durable trace references, transport
  eligibility, and an always-false triage-semantic-acceptance field.

The request codec has no runtime-isolation object. Credentials, transport
environment, session storage paths, work directories, and host paths therefore
have no evidence field. Trusted schema and model resolution is explicit and
uses only the supplied public policy.

All three codecs reconstruct public AI contracts before encoding. JSON is
canonical UTF-8 with sorted keys, finite numbers, closed object shapes,
duplicate-key rejection, bounded nesting, and fixed byte ceilings. Codec
failures are deliberately opaque and warnings are suppressed so invalid raw
content is not copied into diagnostics.

## Registry composition

This lane does not edit a global registry. It exports
`AI_EVIDENCE_CODECS` and `AI_EVIDENCE_SCHEMAS`. The later handler or
integration owner composes those declarations with the schemas it actually
uses and passes explicit `ResultSchemaRegistry` and
`SemanticDataRegistry` instances to `Phase1Persistence.open()`.

The lane tests demonstrate this with a synthetic prerequisite codec plus the
three exported AI evidence codecs. Package initialization keeps persistence-
backed session imports lazy, so importing `msgloom.ai_evidence.codecs` while
`msgloom.persistence.semantic` initializes does not create a runtime cycle. All
AI evidence schemas are declared as semantic-data-required. Every evidence
write uses `append_result_with_data()`; there is no metadata-only evidence
success.

## Session ordering

`EvidenceSession.begin()` takes the exact `AnalysisAttempt`, execution
identity, trusted policy, required `ResultRef` values, configuration version,
and code version. Before request evidence is written, every required result is
loaded, must be acceptable, must have semantic data, must match the exact
reference, and its semantic bytes must successfully load and validate.

Only after those checks does `begin()` atomically insert the
`ai_request@1` result and semantic payload in one existing persistence
transaction. Admission uses the persistence insert-only option: an existing
result identity is a duplicate even when every byte matches. The transaction
rolls back newly inserted semantic bytes when the result identity is already
present. The caller must await successful begin before invoking `AIRunner`.
One or many persistence facades opening the same SQLite file therefore admit
exactly one session for an attempt. Restarting does not reopen that admission;
a later begin raises the privacy-safe `DuplicateAttemptError`. An interrupted
attempt keeps its request and any trace prefix. Retrying execution requires a
new `AttemptIdentity`.

`PersistenceTraceSink.write()` accepts only the same attempt identity and
exact next sequence. One session lock serializes trace and terminal state
transitions. A trace saves before returning, and a concurrent finish cannot
overtake that accepted write. Duplicate, non-next, and post-terminal writes are
rejected. Trace stage lineage contains the request and the preceding ordered
unique trace prefix. In-memory prefix state advances only after persistence
succeeds.

`EvidenceSession.finish()` accepts only the same attempt and an exact trace
count. Terminal lineage contains the request followed by every durable trace
reference in order. Request references must be `ai_request@1`; terminal trace
references must be unique `ai_trace@1` values. `transport_eligible` must
equal the reconstructed public response eligibility. Failed transport evidence
therefore remains durable but cannot become triage acceptance. A terminal
diagnostic and a terminal response share the same serialized transition and
cannot overwrite one another.

## Byte budgets

The fixed codec ceilings remain 4 MiB for `ai_request@1`, 1 MiB for
`ai_trace@1`, and 4 MiB for `ai_response@1`. In addition, a session measures
the canonical public `TraceEvent` fields against
`AnalysisAttempt.limits.max_trace_event_bytes` and the canonical public
`AnalysisResponse` fields against `max_output_bytes`. Both the declared
attempt limit and the fixed codec ceiling must pass before persistence can
advance session state. Oversized trace or terminal evidence leaves the prefix
and terminal reference unchanged.

## Failure and cancellation ownership

This adapter does not catch an `AIRunner` exception because it does not own
runner invocation. After a runner raises, the later handler may call
`finish_diagnostic(cancelled=False, ...)` with a privacy-safe failure code
and detail. After runner cancellation and cleanup, it may call the same method
with `cancelled=True`. Those calls save terminal diagnostic response evidence
with failed or cancelled stage status and transport eligibility false.

If the handler itself is cancelled while an evidence write has already been
accepted, the session shields and drains that persistence operation through
repeated cancellation while retaining the transition lock. Durable session
state is updated before cancellation is re-raised and before a waiting finish
can proceed. A persistence failure never advances the trace prefix, creates a
terminal reference, or reports transport eligibility.

The caller owns the operation claim and the actual `AIRunner` lifecycle.
This lane creates no daemon, queue, SDK client, subprocess, provider access, or
competing triage claim.
