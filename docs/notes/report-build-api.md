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
identity to the policy/destination, exact source triage results, exact topic and
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
topic-to-part mapping and its essential fields. Counts or self-reported coverage
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

The handler acquires the existing per-policy REPORT_BUILD durable claim with
the exact triage result dependencies. It loads only those declared saved
inputs, freezes selection, builds and renders, atomically writes the report@1
stage result plus semantic payload, then finishes the claim. Cancellation
drains accepted persistence work before claim completion. The configured claim
lease must exceed the finite operation budget; elapsed lease checks prevent a
known-expired owner from returning success. Persistence ownership errors fail
the operation rather than claiming success.

No numerical semantic release threshold is asserted by this API. Those
thresholds remain manager/user acceptance decisions.
