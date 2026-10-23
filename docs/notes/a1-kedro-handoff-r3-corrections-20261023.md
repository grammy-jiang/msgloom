# A1 → Kedro A2: exact handoff, status, claim and receipt contract

**Status:** design candidate amended after independent R4 (REVISE), pending exact-SHA R5 review.
**Date:** 2026-10-23 (Australia/Sydney).
**A1 accepted qualification SHA:** 34057c6c9f85688fd2bd1868d90302ab5a61205f.
**Repository source baseline:** 895fc40a0ec889bd96f620df8c62491787218217.
**Historical review:** R3 at 3c0903b and R4 at 467ca23 both REVISE; original reports retained separately. This is an A2 design, not implemented behavior.
**Governing decision:** [Kedro is A2 main ETL](../decisions/2026-10-23-a2-kedro-primary-etl.md).

## 1. Exact mapping: admission workset is a reduced projection

`PreparationIntakeWorkset` is the accepted durable admission state,
**not** a lossless serialized copy of `ReleasedInput`. A2 never
compensates for missing details by scanning mutable A1 projections.

| A1 immutable source | Persisted intake value | Missing or compressed information | New A2 dataset responsibility |
| --- | --- | --- | --- |
| `ReleaseEntryRef` / `ReleasedInput.facts` | `workset.entries`, anchors, `IntakeSelection.entry` | Fact payloads, group/profile/coverage details | Re-read **the same exact** entry via `ReleaseSourceReader.read_entry(entry_ref)`; verify digest and exact fact members |
| `ReleasedInput.selection` | `IntakeSelection(entry,result)` + saved `CollectedSelection@1` | Primary vs component role | Validate saved selection against original exact primary and recomputed ordinal identity |
| `ReleasedInput.components` | The same `IntakeSelection` structure | Component position and role | Match by immutable saved selection, original ordered components, recomputed selection result ID and entry role; duplicate-equality ambiguity cannot be guessed |
| `ReleasedInput.contexts` | Not present as primary selections | Full supporting context | Only exact re-read or explicit `read_supporting_context`; never silently admit it as a message |
| `ReleasedInput.transitions` | Reduced `IntakeTransition` with fact ID, classification, resource and scope | Reason, parent, authority revision, provider order, byte/evidence associations | Enrich only by exact fact/entry reference with equality/scope proof; keep reduced transition authority if more cannot be verified |
| A1 `control_context` or Teams `component_observation` fact | Scoped `context_refresh` | Detailed component/provider original | All non-proof Teams component facts may yield refresh, **even when a primary exists**; never fabricate a parent body |
| Unmaterializable entry | `workset.held` | No admissible bytes | Preserve intake-held reason and reference; do not parse |
| Historical baseline | Approved baseline sources/selections | No implicit past ledger entries | Only approved exact versions and saved evidence |

`IntakeSelection` keeps entry and result **but no role**. Intake emits
saved selections from `(released.selection, *released.components)` in
that exact order after dropping `None`. It computes an immutable
per-ordinal result identifier using
`_identity("selection", [scope.claim_key(), entry.model_dump(mode="json"), entry_members, configuration_version, code_version, ordinal])`.
New A2 can reconstruct and compare this exact ID using a **read-only,
version-pinned verifier**, then validate actual `CollectedSelection`
equality. Prefer a separately reviewed public projection/identity helper
over copying the private algorithm; do not change existing A1 release or
intake payload/schema bytes. If both ordinal proof and equality cannot be
verified, the selection is A2-held rather than assigned a guessed role.

A1 `release_entry_seq` is global. A per-source/stream consumer cursor
may correctly skip sequences belonging to another stream; contiguous
numbers are never required. Intake currently emits only the held reasons
`byte_limit`, `query_limit`, and
`materialization_failed`. The last is deliberately coarse and may
also cover an unsupported transition reason or release without an intake
disposition; it is **not** always proof that a saved file disappeared.
Other `HeldIntakeEntry` enum members are not currently emitted by
the inspected implementation.

## 2. New scheduled-outcome translation without modifying A1

**Observed legacy behavior:** `ScheduledPreparationHandler.run`
catches catalog pin errors, some `SourceReferenceError` cases and
consumer contention into generic `INCOMPLETE` plus
`scheduled-work-pending`. That cannot safely drive automatic
Prefect retries. The **new A2 producer/wrapper** must intentionally change
the outward taxonomy while leaving A1 ledger, intake workset, cursor,
pending index, source reader identity and public saved inputs unchanged.

| Source condition | New terminal status | Stable safe code | Operator / external action |
| --- | --- | --- | --- |
| No admitted eligible work | COMPLETE | none | Idle; await another hint or catch-up |
| Finite work remains pending/backlogged | INCOMPLETE | scheduled-work-pending | Continue with bounded spacing while progress changes |
| Intentionally held-only or A2-held selection, no unresolved schedulable work | INCOMPLETE (terminal workset) | scheduled-work-held | Retain durable held disposition; alert for explicit repair/replay, **not** automatic busy retry |
| Consumer claim unavailable | INCOMPLETE | scheduled-consumer-busy | Coalesce and retry after bounded backoff |
| Trusted expected catalog pin differs (checked before source admission) | BLOCKED | scheduled-catalog-mismatch | Stop scope; trusted operator reconfiguration only |
| Escaped `SourceReferenceError` from accepted intake/reader, including lost cursor anchor / rollback / invalid exact reference | BLOCKED | scheduled-source-reference-invalid | Stop scope; verify catalog and restore coherently, never parse exception text |
| Invalid trusted authorization or unsupported secure host | BLOCKED | scheduled-invalid-authority | Stop without source mutation |
| Unexpected persistence/invariant failure | FAILED | scheduled-persistence-failed | Alert, preserve already accepted refs and pending |
| Accepted partial parser/semantic output with explicit limitations | INCOMPLETE (terminal workset) | scheduled-preparation-incomplete | Inspect saved results; deliberate explicit replay only if required |
| External cancellation / lost claim while publishing | CANCELLED / FAILED | scheduled-cancelled / scheduled-claim-lost | Await cleanup, no late durable publication |

**Classification implementation choice (fixes R4):** The new A2 wrapper
must catch `ClaimUnavailableError` distinctly from
`StaleClaimError`; trusted pin mismatch is an explicit preflight;
**all escaped `SourceReferenceError` from exact reader/intake are
conservatively BLOCKED under one code**. Do not rely on exception text or
an untrusted second cursor pre-check to distinguish `anchor` from
`ledger moved behind cursor`. This solves trust-vs-backlog distinction
without modifying A1 or intake persistence and without needing new
exception subclasses. Typed-source refinement can be considered separately
with source evidence and review, but is not a prerequisite.

### 2.1 External Prefect visibility and progress

The existing CLI returns terminal status, result refs, limitation codes and
failure codes; exit 4 multiplexes INCOMPLETE, FAILED and CANCELLED. Prefect
does not share the Application database merely because it is installed.

A new **read-only A2 scope-status command** (proposed, not implemented)
or equivalent allowlisted operator API must expose a privacy-safe digest
of the configured catalog/source/stream/consumer scope and state:
cursor anchor, active/pending count, terminal-held count, last accepted
manifest/progress digest and blocking code. It must not leak provider payload,
source addresses, file paths or credentials. The external wrapper reads this
state **through the installed msgloom CLI**, not by opening private SQLite
tables from Prefect.

Only work that is still **pending** is retried automatically. Terminal
INCOMPLETE with limited/held output is **not** automatically pending: the
existing `select_preparation_intake_worksets` selects pending worksets
only. Explicit repair/replay creates a new versioned A2 attempt/receipt,
never overwrites the original terminal record. An intake-held record remains
queryable via the accepted held index; A2-held records require the new
A2-owned disposition store below. Track repeated no-progress attempts and
apply capped backoff and operator alert to avoid spin.

## 3. Claim topology, bounded time, and publication

| Scope | Authority | New A2 behavior |
| --- | --- | --- |
| `(catalog,source,stream,consumer)` | Existing `PREPARE_INTAKE` claim | Intake alone owns selection/workset/cursor atomic admission; never use this token to save A2 semantics |
| One immutable workset `ResultRef` | Existing workset `PREPARE` claim | Own progress and terminal completion of that exact workset |
| One bounded Kedro partition of saved selection refs | New partition `PREPARE` claim, successor to old plan claim | Every parser/zone/prepared/filter/group semantic Dataset save validates this exact claim |
| Workset transitions | Existing separate `PREPARE` transition claim | Only scoped, immutable transition results, no fabricated primary body |

Partition claim key is deterministic from **workset ref, partition ordinal,
exact selected ResultRefs, schema and policy version**, excluding execution
attempt ID. Partition identity must not accidentally merge two occurrences
of one source VersionRef in different release entries.

Let `E` be the configured finite execution timeout and `L`
the corresponding claim lease; today `L > E + 1s`, with no automatic
renewal. The legacy scheduled outer bound is
`E + (L - E) / 2`. The new Kedro worker must be admitted only if the
minimum remaining workset, partition and outer deadlines exceeds independently
measured node/service upper bounds **plus** parser-worker and claim-finish
cleanup. A synchronous Python thread cannot be killed. On cancellation,
stop new nodes/dataset saves, signal bounded cooperative cancellation,
await accepted service/drain, discard late values, and never publish after
claim expiry. If bounded node drain cannot be proven, the Kedro-primary
candidate is NO-GO pending a separately reviewed execution redesign.

## 4. Result identity and restart deduplication (fixes R4)

Legacy result IDs include attempt/execution identity. That is historical,
**not** a guarantee of deterministic accepted-semantic deduplication.
The new A2 should separate:

1. **Logical acceptance key (input-only).** SHA-256 over immutable workset
   ResultRef, partition ordinal/key, selection ResultRef + ReleaseEntryRef +
   resolved occurrence/role, stage kind/schema, all **accepted upstream
   ResultRefs**, frozen parser/configuration/policy/code versions and source
   scope. A transition key also binds its exact fact ID and scope/kind.
   **Never include output bytes/digest, current timestamps, Kedro node name,
   Python object hash or execution/attempt ID in this key.**
2. **Validated output digest.** Separately store a canonical codec digest,
   byte count and semantic metadata with the accepted result. Same logical
   key + different output digest is an **integrity conflict**: reject the
   second value and do not publish a second accepted result without a
   specifically versioned policy/schema change.
3. **Attempt audit.** Execution and attempt IDs remain separate audit
   identities for failures/retries; a new attempt does not rename an
   already accepted semantic result.
4. **Atomic append-or-verify.** A durable uniqueness constraint or
   transactionally serialized claim-fenced compare/insert is required.
   A non-atomic get-then-insert outside the transaction is insufficient.
   The existing intake `collected_selection@1` uses a similar
   deterministic lookup/verify pattern but does not by itself qualify
   new A2 result storage.
5. **Resume instead of recompute everything.** On restart, load and verify
   already accepted stages and their lineage/digests; skip those stages
   (and parse calls) when outputs remain valid, continue the earliest
   unaccepted dependencies within the same bounded workset. Explicit
   reproducibility tests can recompute a stage and verify digest equality;
   a nondeterministic parser mismatch must fail closed.
6. **Mid-pending upgrade.** A workset's frozen code/config versions are
   not silently reinterpreted by new A2 policy. At cutover, inventory and
   drain old-engine pending worksets where possible or perform an approved
   versioned downstream plan/receipt migration linked to the same frozen
   inputs **without modifying the intake cursor**. Keep old results
   readable. No automatic dual-engine fallback.

**Existing Phase1Persistence cannot be assumed to support this.** C0 must
inspect `StageResult` execution/attempt binding and result uniqueness,
then explicitly version the A2 semantic acceptance store/codec and A3 adapter
as required. Design acceptance does not imply migration code exists.

## 5. Durable A2-held selections and accepted completion proof

**R4 finding:** `workset.held` is immutable and written only at intake.
A missing/ambiguous role or source re-read failure **during Kedro processing**
cannot be appended to it. The legacy
`msgloom/persistence/intake_completion.py` proof requires a
`prepared` output for every frozen selection; it also expects the
old fixed legacy result bound. Therefore a new A2-held disposition and
new A2-owned completion proof are **mandatory**, not optional.

- Add a proposed versioned `a2_input_disposition@1` result, keyed to
  the **exact IntakeSelection ResultRef**, immutable ReleaseEntryRef,
  attempted role/ordinal (when known), an enum reason such as
  `role_unverifiable` or `source_evidence_unavailable`,
  original selection digest, frozen config/code version and a retry
  class (`operator_repair`, not automatically pending). No fabricated
  prepared content, source body, or unverified parent.
- Add an A2-owned `a2_completion_receipt@2` or equivalent accepted
  producer-plan proof requiring **exactly one** terminal disposition
  (`accepted prepared@2` or `a2_input_disposition@1`) for
  every frozen root, plus every required scoped transition. It must reject
  missing, overlapping, foreign or stale claims and correctly produce
  INCOMPLETE on partial/held sources.
- Intake-only `workset.held` entries have **no frozen selection
  root**; their existence independently requires terminal
  INCOMPLETE/held, not a false COMPLETE.
- The existing immutable `PreparationIntakeWorkset@1`, consumer cursor,
  intake-held index and A1 release remain unchanged. The completion-proof
  consumer under `msgloom/persistence/intake_completion.py` and its
  terminal handling **must be versioned/reviewed** to accept the new A2
  receipts. This is a downstream A2 proof migration and requires a separate
  focused change, CI, independent review and A3 compatibility, not a new
  A1 authority or checkpoint.
- An A2-held selection can be finalized as **terminal INCOMPLETE** with its
  exact durable disposition and scoped manifest so ordinary scheduled
  invocations do not spin on it. Later explicit repair/replay produces a
  **new** append-only A2 attempt/receipt referencing the original
  workset (or an explicitly versioned derived workset), not an overwrite
  of the earlier terminal result. This recovery API must be qualified
  before cutover.
- External no-progress monitoring reads both intake-held and A2-held
  records through the proposed allowlisted scope-status CLI.

This versioned A2 completion receipt and held disposition are required
even if the new pipeline otherwise reuses existing pure parser helpers.

## 6. Required automatic E2E acceptance tests

AUTO-01 through AUTO-22 are in the companion activation plan.
Three additional hard cases must be included:

- AUTO-23: Same immutable acceptance key with two different canonical
  parser outputs: second publish is rejected, no duplicate accepted
  record or lost prior history; retry skips validated accepted stage.
- AUTO-24: A2 role reconstruction failure produces a durable
  `a2_input_disposition@1` and terminal INCOMPLETE, with no
  automatic reattempt loop; a separate explicit replay preserves
  the original audit. Also cover held-only intake workset.
- AUTO-25: An old-code-version workset is still pending during Kedro
  cutover: the migration does not rewrite its source selection or cursor,
  and semantic version/receipt conflicts fail closed.

Scope-specific status gate: catalog/anchor mismatch maps to a conservative
`scheduled-source-reference-invalid` BLOCKED code by **typed
SourceReferenceError catch**, no exception string matching or racy preflight.
Global release sequence gaps are a **normal-success** case, not an error.
The existing Task 15 28-gate qualification remains historical and unchanged.

## 7. Design gates and current implementation status

D4 evaluates architecture consistency with A1, not installed Kedro runtime.
Q0 still must validate the pinned Kedro 1.7.0 candidate, AbstractDataset
save/load semantics, parser bridge, platform limits and overlapping
security advisories before dependency or production code admission.

All new statuses, receipt types, deterministic accepted keys, scope-status
command and retry policies described here are **proposed**, not present in
master. New-code implementation remains NO-GO until an independent
exact-SHA D4 ACCEPT and the required Q0 proofs. Preserve original R1–R4
review output and treat each acceptance as binding only to its exact SHA.
