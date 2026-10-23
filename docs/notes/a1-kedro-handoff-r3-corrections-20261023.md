# A1 → Kedro A2: verified role, outcome and idempotence corrections

**Status:** D4-R3 REMEDIATION DRAFT; design review required; no runtime authorization.
**Reviewed candidate:** 3c0903bc23be2ebe9594ffe08a423a586a846595.
**Original independent verdict:** REVISE, retained at a2-kedro-independent-review-r3-20261023.txt.
**Source authority:** accepted A1 release, exact reader and intake contracts on master 895fc40.
**Applies to:** `docs/plans/2026-10-23-a2-kedro-native-design.md` and `docs/plans/2026-10-23-a1-release-to-kedro-auto-handoff.md`.

## 1. The committed workset is authoritative, but not a lossless ReleasedInput copy

The workset is a **durably admitted, intentionally reduced projection** of
a release, not a full copy of its source facts. New Kedro A2 must not infer
roles or full transition explanations from IntakeSelection alone.

| A1 exact read | Workset persisted content | Information not retained | New Kedro adapter rule |
| --- | --- | --- | --- |
| ReleaseEntryRef and ordered fact membership | workset.entries plus previous/cutoff anchor | Full ReleaseGroup/FactPayload not inside workset | Re-read immutable `ReleaseSourceReader.read_entry(entry_ref)` by the exact saved reference and verify digest; never read current projection |
| ReleasedInput.selection | IntakeSelection(entry, collected_selection@1 ResultRef) | "primary" role is not tagged | Re-read exact release and match saved CollectedSelection to original primary selection by equality |
| ReleasedInput.components | Same IntakeSelection fields as primary | "component" role and source position not explicit | Compare each saved selection to `released.components` and match unambiguously; on duplicate/equality ambiguity, hold and do not guess |
| ReleasedInput.contexts | Not stored as primary selection | Original context payload and provenance omitted | Access only by exact `read_entry` or explicit read_supporting_context; context is supporting, not new primary |
| ReleasedInput.transitions | workset.transitions: fact_id, transition_kind, resource/scope IDs | reason, parent IDs, authority revision, provider order and saved evidence may be absent | Workset typed transition remains authority; enrich only by verifying the same fact and scope against exact released transition/facts; otherwise record limitation |
| control_context and Teams component-only facts | context_refresh IntakeTransition | Some parent/component original details collapsed | Re-read exact fact by the saved entry if needed, do not fabricate missing parent or body; proof-role facts excluded |
| Evidence that cannot be materialized | HeldIntakeEntry(entry, reason) | No admissible body/content | Keep held; no Kedro parser invocation, new VersionRef or global deletion |
| Explicit historical supporting context | baseline_approval, baseline_sources, baseline_selections | No automatic primary release backfill | Only user-approved exact versions, no SQLite timestamp/history scan |

The actual intake currently emits `byte_limit`,
`query_limit`, or `materialization_failed` held reasons. The
model also allows `missing_evidence`, `corrupt_evidence`, and
`unsupported_source_type`, but they are not emitted by the inspected
intake writer. No test may assert one of those more-specific reasons as an
existing implementation result without a reviewed classifier enhancement.

The global `release_entry_seq` is monotonically ordered in the A1 catalog.
A per-(source, stream, consumer) cursor therefore legitimately crosses
**sequence gaps** belonging to other streams. Never require contiguous sequence
numbers in one source stream.

**Role resolution failure:** If a re-read fails because previously selected
evidence is now unavailable, do not substitute a fresh source or invent
roles. Preserve the exact saved CollectedSelection and workset/held identity;
the missing enrichment is an INCOMPLETE/HELD limitation. Where safe equality
cannot identify the saved member, fail closed, do not silently group it.
An A2 adapter may cache the validated exact released envelope only within
one bounded invocation; it is not a second durable event ledger.

## 2. Typed outward outcome mapping for the NEW A2 scheduled wrapper

**Observed current code limitation:** the existing
`ScheduledPreparationHandler.run` catches many exceptions, including
catalog mismatch, anchor restoration and claim contention, then returns
`INCOMPLETE` plus `scheduled-work-pending`. The old CLI cannot
distinguish these causes even though its documented exit codes include BLOCKED.
That is existing behavior, **not** the desired new Kedro status guarantee.

| Cause | New public outcome | Safe code | External action |
| --- | --- | --- | --- |
| No eligible release or pending work | COMPLETE, no refs | none | Idle; wait for next wake |
| Valid new/pending work remains | INCOMPLETE | scheduled-work-pending | Coalesced finite continuation |
| Released entry held with no successful primary preparation | INCOMPLETE | scheduled-work-held | Preserve held index; alert or explicit repair, do not spin |
| Another in-flight consumer holds a claim | INCOMPLETE | scheduled-consumer-busy | Bounded backoff and retry, never reset consumer |
| Trusted catalog pin mismatch, cursor anchor mismatch, or restored catalog | BLOCKED | scheduled-catalog-mismatch / scheduled-anchor-mismatch | Stop this scope; require owner reconciliation |
| Invalid authorization/configuration or unsupported secure source platform | BLOCKED | scheduled-invalid-authority | Stop; no source read/claim |
| Unexpected storage or invariant failure | FAILED | scheduled-persistence-failed | Alert; retain pending and prior accepted refs |
| Parser/content limitations with accepted partial stages | INCOMPLETE | scheduled-preparation-incomplete | Preserve partial results, next finite or operator-directed retry |
| External cancellation or claim expired while writing | CANCELLED or FAILED/claim-lost as appropriate | scheduled-cancelled / scheduled-claim-lost | Drain accepted work, no late publish |

These codes are **proposed v2 A2 outcome semantics** and require an explicit
new scheduled producer/composition translation layer, changed tests and
operator-documentation update. Do not claim the current CLI already returns
them. Do not change A1 source publication or the accepted intake cursor/
workset schema to classify external scheduler outcomes.

INCOMPLETE requires progress-aware backoff. A wrapper tracks accepted cursor,
workset states, code and bounded consecutive no-progress attempts, not only
exit code 4; persistent no-progress produces operator alert, not a busy loop.

## 3. Claim ownership table for Kedro DataCatalog saves

| Scope | Existing authority type | Proposed Kedro use |
| --- | --- | --- |
| (catalog, source, stream, consumer) | PREPARE_INTAKE scope claim | Existing intake is sole owner of freezing exact workset/cursor; Kedro never uses it for A2 semantic saves |
| One immutable workset ResultRef | Workset PREPARE claim | Protect pending/final acceptance, exact result manifest and terminal receipt |
| One bounded Kedro partition of saved selection ResultRefs | Per-partition PREPARE claim, successor to legacy per-PreparationPlan claim | Every parser artifact, zone, prepared, filter and group stage Dataset save carries this token and immutable dependencies |
| Workset scoped transitions | Separate PREPARE transition claim | ClaimFencedTransitionDataset uses existing typed transition publisher; no fabricated primary content |

A Kedro stage Dataset never borrows the workset claim to bypass per-partition
schema/plan proof. Existing persistence proof may require a **new A2 plan
receipt/schema version** for `prepared@2` and `zones@1` rather than
pretending legacy `prepared@1` proof accepts a new result graph.
That is a C0 gated migration plus A3 reader/consumer compatibility test, not
a modification to A1's formally accepted release format.

## 4. Finite deadlines and cancellation authority

Let E be configured active execution_timeout_seconds and L be the associated
claim_lease_seconds (currently L > E + 1 s, with no implicit renewal).
The existing scheduled workset wrapper uses
`E + (L - E) / 2` as one outer bounded replay limit. Preserve that
protective principle: the Kedro-owned worker deadline must fit within the
remaining workset and partition claim leases **after reserving finite cleanup**.

For each dataset service call and CPU node:

- Determine remaining workset, partition and operation time, take the minimum.
- Admit only if measured worst-case node/service duration plus parser drain
  and claim finalization margin fits remaining time.
- Run SequentialRunner in one owned worker, not the Application event loop;
  synchronous facades submit approved coroutines through the reviewed bridge.
- On deadline/cancel, stop new nodes and dataset saves, signal cancellation,
  drain previously accepted bounded work, discard late transform output and
  finish claims only after cleanup. SQL writes additionally verify ClaimToken
  atomically.
- Prove measured CPU-bound node termination and child parser process shutdown
  on Raspberry Pi. If a node cannot be bounded, Kedro-primary adoption is
  **NO-GO** pending a separate revised execution boundary; Python cannot
  forcibly terminate an arbitrary worker thread.

The chosen exact budget algorithm and minimum lease margin are Q0 feasibility
deliverables. The design does **not** claim they are already verified.

## 5. Deterministic accepted result identity (new A2; not legacy)

Legacy A2 result_id historically includes execution and attempt. Its repeated
attempts may create distinct physical StageResults even for equal semantics.
This is not the desired new Kedro accepted-work deduplication contract.

- **Accepted semantic key candidate:** SHA-256 over exact workset ResultRef,
  saved IntakeSelection ResultRef + entry ref and occurrence/role, stage name and
  schema version, trusted parser/policy/configuration/code version, and canonical
  output digest. For scoped transitions, bind original immutable fact ID,
  resource/scope and transition kind. Never use wall clock, current rows,
  dynamic Kedro dataset names, or Python object hashes.
- **Append-or-verify:** A replay producing the same immutable result reuses
  the accepted semantic reference. A conflicting byte digest at the same
  semantic authority/policy key **fails closed** unless the algorithm version
  changes explicitly; never overwrite accepted history.
- **Separate attempt audit:** execution and attempt IDs identify attempts
  and errors, not accepted semantic content. Workset receipt accepts each
  required semantic stage exactly once, even if parser invocation is retried.
- **Distinct explicit schema:** This is new A2 result/receipt behavior.
  Existing StageResult/Phase1Persistence invariants, uniqueness constraints,
  A3 adapters and transition publication must be inspected and, if necessary,
  upgraded by reviewed migrations. Do not change A1/intake ledger identity.

This policy is a C0 design gate until the exact old-to-new persistence
integration is proven. Its existence here is **not** evidence that the current
legacy result IDs already obey it.

## 6. Additional mandatory automatic activation tests

Keep AUTO-01 through AUTO-14 in the automatic-handoff plan, then add:

- AUTO-15: dropped wake-up after committed A1 release; recovery by startup/
  periodic reconciliation on the same consumer scope.
- AUTO-16: A1 exits failed after an earlier committed release; Kedro processes
  only that valid released subset.
- AUTO-17: restored catalog/anchor mismatch, global sequence gaps and
  re-entrant consumer contention are accurately classified.
- AUTO-18: backlog larger than max_entries and max_pending_worksets drains
  across bounded invocations without starvation.
- AUTO-19: component-only Teams selection and repeated same VersionRef across
  entry refs retain unambiguous primary/component roles; uncertainty held.
- AUTO-20: context-only or transition-only workset and held-only cut preserves
  exact scope, no false body and explicit INCOMPLETE/held signal.
- AUTO-21: cancellation/deadline/claim loss mid-DataCatalog semantic-save
  and exact replay yields no late or duplicate accepted result/receipt.
- AUTO-22: wrapper correctly distinguishes COMPLETE, valid PENDING, HELD,
  BUSY, BLOCKED catalog/authority and FAILED persistence; no infinite retry.

All new codes, role enrichments, claim receipt/identity changes and
"held-only" status are future **A2 implementation changes** to be separately
reviewed. Do not re-label frozen Task 15 source tests or change the accepted
A1 consumer cursor to achieve them.
