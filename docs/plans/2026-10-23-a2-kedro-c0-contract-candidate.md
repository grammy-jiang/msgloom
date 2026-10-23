# A2 C0 — Kedro-primary contracts, A1 source fidelity and persistence design

**Status: C0 contract candidate for independent review. Not yet a frozen production contract.**
**Date:** 2026-10-23, Australia/Sydney.
**Repository base:** master 895fc40a0ec889bd96f620df8c62491787218217.
**Architecture authority:** Draft design PR #68, independent D4 R6 ACCEPT on 878121fa9ab7ca35754b36d824440a77e92f5f4d.
**Kedro feasibility:** Draft research PR #69, Q0 independent R2 ACCEPT on 5f1050a4939f1ec44e3326df10d83fc686f72721, synthetic ONLY.

C0 investigates the actual accepted A1 release and native Phase1Persistence implementation. This document records proposed versioned A2 interfaces and the precise code changes that remain necessary before a production change. All examples use synthetic fixtures and temporary SQLite. The immutable A1 ReleaseGroup, ReleaseEntry, ReleaseSourceReader, PreparationIntakeWorkset@1, intake cursor and existing stored historical results remain unchanged.

## 1. Source audit — what is already implemented, and what is not

| Actual source | Verified behavior | C0 consequence |
| --- | --- | --- |
| msgloom/sources/release_reader.py | read_entry(ref) revalidates catalog and ReleaseEntryRef, loads facts and reconstructs selection, components, contexts, transitions | New A2 must bind exact entry and re-read saved facts, never scan provider-current projections |
| msgloom/preparation_pipeline/intake_models.py | Workset@1 contains entries, selected ResultRefs, reduced transitions, held, frozen code/config, optional baseline; selections have NO primary/component role | Role/evidence requires exact release re-read and original ordinal proof. Preserve contexts and full transition facts separately |
| msgloom/preparation_pipeline/intake.py | Saved intake selection identity is input-derived from (scope claim key, exact entry JSON, exact ordered fact-role members, config, code, ordinal); values iterate primary then components, never contexts | New verified source resolver must compare that full ordinal identity and the saved CollectedSelection canonical digest; no equality-only guessing, no contiguous release sequence assumption |
| msgloom/persistence/store.py | append_result_with_data uses BEGIN IMMEDIATE, canonical semantic reference and live ClaimToken publication checks in one transaction | Existing writer is useful infrastructure; its current shape is NOT a complete A2 logical-key acceptance store |
| msgloom/contracts/models.py | StageResult includes execution and attempt, while result_id is globally immutable | Reusing a deterministic result_id with a different attempt/exec is rejected even when bytes match; attempt audit must be separate from accepted logical data |
| msgloom/persistence/preparation_proof.py | Existing plan binding allowlists only version-1 prepared/filter/group/etc, requires PREPARE plan ownership and binds result to attempt | Simply registering prepared@2 in ResultSchemaRegistry is insufficient; a new versioned A2 acceptance/plan proof is required |
| msgloom/persistence/intake_completion.py | Existing completion requires accepted prepared@1 output for every selected root (line 252 raises only when ``selection_refs`` is non-empty) and has a fixed old-output bound. It does **not** reject a held-only workset: with no selections no plan proof exists, the aggregate status check at lines 183-195 is skipped (``if proofs``), and ``intake_store.py`` accepts any COMPLETE or INCOMPLETE status. Even with selections, the aggregate status ignores ``workset.held``. | The old proof **can** finalize a held-only workset as COMPLETE, and can accept COMPLETE for a workset with intake-held entries when every plan is COMPLETE. It cannot finalize A2-held roots, because it needs prepared@1 for every root. See the policy-change finding after this table. |
| msgloom/persistence/async_store.py | _drain_thread drains real write tasks before exposing CancelledError | Postcommit caller cancellation must cause **read-back**, not blind retry or inference that the SQLite transaction rolled back |

**Policy-change finding (legacy held-only behavior).** The statements in the
table row above come from reading the legacy source. This worker did not
execute a legacy held-only completion. The v2 rules in sections 7 and 8 are
therefore a deliberate **new v2 policy change**, not a restatement of legacy
behavior:

- A workset with any intake-held entry or any A2-held root ends INCOMPLETE,
  never COMPLETE.
- Receipt@2 must account for ``workset.held`` itself. The legacy aggregate does
  not force that inclusion.
- A1 and the legacy completion code are **not** changed by C0. The owner of A1
  and legacy completion receives the legacy behavior as a finding. Any change
  to it needs its own reviewed task.
- The prototype enforces the v2 rule only in
  ``CompletionReceipt.validate_against`` (structural, no store reads).

### Real isolation tests

- tests/research/test_c0_phase1_storage_integration.py: actual Phase1Persistence/SQLAlchemy/SQLite, new attempt metadata conflict, changed output conflict, lease expiry and stale claim, post-COMMIT cancellation and reopen, prepared@2 rejected by legacy plan proof, integrity check rejects inconsistent canonical bytes. Five tests. Live claims use a 120-second lease. Expiry tests use ``lease=0`` with no sleeps. Failure messages describe the violated expectation.
- tests/research/test_c0_contract_prototype.py: pure accepted-stage input identity. Checks missing, foreign and duplicate roots separately, plus multiple occurrences in noncontiguous ReleaseEntry sequence, held-only and A2-held mandatory INCOMPLETE, transition-only batch identity, and strict frozen payloads. Each strict-decode negative test decodes a valid JSON-mode payload (``model_validate_json``), has a positive control, and checks the exact predicate: extra field, selected-roots XOR transition batch, kind/version pairing and receipt policy version. One defensive test builds two ReleaseEntry occurrences that share one ResultRef: ``selection_refs`` deduplicates, and the receipt still needs one result per occurrence. Real A1 hashes the entry into every intake selection ID, so honest acquisition does not produce that case. Thirteen tests.
- tests/research/test_c0_baseline_contract.py: approved historical baseline selection/source without invented ReleaseEntryRef, exact receipt coverage and A2-held. One test.
- tests/research/test_c0_atomic_acceptance.py with scripts/research/c0_atomic_acceptance_prototype.py: **four tests of a research-only experimental SQLite acceptance table**. Actual Phase1Store BEGIN IMMEDIATE and ClaimToken validate; same input-only key across two different attempts, read-back and conflict rollback, expired claim refusal, two concurrent owners with equal output, and two concurrent owners with conflicting output. The research table is created ONLY in pytest tmp_path.
- tests/research/test_c0_native_a1_exact_handoff.py: authentic local Scrapy Mail acquire → atomic A1 ReleaseEntry → ReleaseSourceReader → IntakeService → real saved CollectedSelection@1; recomputed intake ordinal identity, exact role and canonical semantic digest. Three separate negative cases use only local in-memory copies: a candidate absent from the workset (membership guard only), a candidate that is in the frozen workset but whose ID is no ordinal identity of the exact release, and a stored selection whose content differs from the release re-read. The ambiguous-ordinal branch (two matches) cannot be built honestly because the ordinal is part of the hash, so it stays unexercised. One test.
- Prototype model/validator implementation: scripts/research/c0_contract_prototype.py. These files are research/qualification artifacts only. No actual A2 runtime, persistence schema or registered production codec has been added.

**Focused research gate:** 24/24 tests (13 + 1 + 4 + 5 + 1) passed in each of three consecutive runs on the Raspberry Pi, using the existing msgloom Python 3.13 environment, including one native Scrapy/A1 release fixture. The runs used the uncommitted tree on top of 0eb8fe6. This number is a locally observed focused suite, not a portable CI matrix or full Kedro integration acceptance.

The original A1 frozen Task15 acceptance (28/28, exact SHA 34057c6c9f85688fd2bd1868d90302ab5a61205f) is historical and **not** requalified by the C0 tests above.

## 2. Versioned storage and codec decisions

**New A2 semantic schemas (proposed, not installed):**

| Stage | Semantic kind@version | Required content and limitation |
| --- | --- | --- |
| Input/fidelity proof | frozen_source_selection@1 | Exact workset ResultRef, release entry ref or approved historical baseline, frozen selection ref/digest, ordinal, primary/component role and proof |
| Evidence/extraction | extracted_components@1 | Exact saved evidence identifiers and digests, primary + alternates + nested attachment surfaces, missing/unsupported/partial each classified |
| Isolated parser | parsed_parts@1 | Bounded per-part decoded text/table/block outputs, MIME or actual format detection, source evidence span, unsupported feature limitations |
| Normalization | normalized_content@1 | Bounded normalization transform and reversible mapping or explicit non-reversible limitation to saved original spans |
| Zoning | zones@1 | Contribution/quote-occurrence/forward/signature/footer/unknown with offsets; quote occurrence never implies original author |
| Native relations | native_relations@1 | Typed direct reply/ancestor/candidate parent, scope and evidence, no confidence-only promotion to proof |
| Core prepared output | **prepared@2** | Versioned prepared record preserving source/evidence refs, zone/normalization/relationship refs and explicit limitations; not a silent prepared@1 rename |
| Deterministic filter | filter_result@2 | ALL matched configured rule IDs/versions, include/exclude/conflict/unknown, no best-match truncation |
| Scoped grouping | group_result@2 | Versioned source-scope and native-thread evidence; does not merge unrelated subjects or unrelated worksets |
| Transition terminal batch | prepared_transitions@2 | Exact ordered set of scoped transition facts from the workset, with source-specific authority and absence reasons |
| Held at A2 | **a2_input_disposition@1** | Exact frozen selected occurrence and safe reason, no fabricated prepared content, queryable for explicit operator repair |
| A2 result manifest | a2_result_manifest@1 | All accepted stage refs/decisions for a workset, explicit accepted roots and scoped transitions, policy pin and safe diagnostics |
| Completion proof | **a2_completion_receipt@2** | Exact selected occurrence coverage, optional exact transition batch, workset-held count, terminal outcome, claim/proof and acceptance refs |
| Attempt audit | a2_attempt_audit@1 | Separate invocation/claim/execution/attempt, stage error, outcome and timing; NEVER a part of the accepted input key |

All new acceptable semantic results require canonical encode/decode with a closed registry, explicit finite byte/row ceilings and a SHA-256 digest. Runtime parsers MAY have partial semantic outputs with truthful limitations, but never call an undecodable payload COMPLETE.

**Why this requires an explicit new producer contract:** Existing Phase1Persistence has an append-only global StageResult table, canonical semantic data table and (legacy) per-attempt PREPARE plan bindings. The exact result ID is immutable together with the original attempt/execution. C0 does **not** propose weakening or changing that historical immutability. A separate A2 acceptance/proof store must bind logical input identities to canonical output and attempt audit without rewriting StageResult.

**A3 compatibility:** A3/A5 must read prepared@2 and associated zones/native relations via an explicit versioned adapter while continuing to load historical prepared@1. No migration mutates old semantic bytes. A3 may not fabricate data for held selection, missing attachment or unsupported format. A new partial receipt MUST propagate incompleteness to later phases.

## 3. Root acquisition and release fidelity (C0.1 / C0.9)

Incremental A2 root = (immutable Workset ResultRef, exact ReleaseEntryRef, saved IntakeSelection ResultRef, ordered per-entry ordinal, original primary/component role, saved CollectedSelection@1 canonical SHA-256, A1 ordinal proof, saved configuration and code). Roles are only accepted after these conditions are independently verified:

1. Load workset by exact acceptable StageResult and SemanticDataRef through Phase1Persistence (not caller-supplied Workset dict).
2. Use ReleaseSourceReader.read_entry(exact ref); require same catalog-bound entry digest. Use only immutable released facts and ordered fact-role members; do NOT inspect current providers/Graph projections.
3. Enumerate exactly (released.selection, *released.components) without None and without contexts. For every ordinal recompute the existing intake-selection SHA-256 identity from the exact scope claim key, entry JSON, ordered fact-role members, frozen config/code and ordinal.
4. Require **exactly one** matching ordinal identity and byte-equivalent saved CollectedSelection payload; verify its registered canonical codec SHA-256. Role is primary only when the ordinal points to released.selection. All other candidates are component. A body in released.contexts is never primary.
5. If no unique match, role, byte equality or exact source cannot be proven, write a terminal A2-owned input disposition instead of silently guessing; a post-intake dataset evidence error maps A2-held rather than changing A1 admission.
6. Per-source A1 release sequence is globally allocated; gaps for other streams are normal, not a corruption proof. Duplicate *source versions* in distinct release entries are distinct occurrences; do not collapse by source ID.
7. Historical baseline has no ReleaseEntryRef; require explicit existing Workset.baseline_approval, exact ordered baseline_sources/baseline_selections, and read_baseline_selection of each approved VersionRef. Its role is baseline, not forged primary. Prototype FrozenRoot represents that separate role; full baseline verifier remains for C0 acceptance.

The prototype uses a read-only duplication of the currently accepted intake ordinal input encoding strictly for qualification. **Production must use a separately reviewed public verifier anchored to the existing A1 format and a version-pinned golden fixture**; C0 cannot assume private function import is a stable long-term API. The real native Mail fixture proves the reproduced algorithm for one primary entry; component, transition and approved historical baseline fidelity still need fixture proof.

## 4. Parsing / spans / relations / decisions (C0.2–C0.5)

- Source span: exact saved source/binary reference plus unit (byte, codepoint, MIME part, PDF page, Word block, spreadsheet cell), bounded start/end, extraction policy version and per-span limitations. A transformed-text offset is NEVER presented as an original-byte offset without a verified map. Preserve multiple independent locations.
- Extraction: enumerate primary/alternate body and all available attachment/component evidence. Use detected formats and trusted parser profiles; file extension or MIME description is only a hint. A missing/unsupported/encrypted/scanned/partly stored input produces a closed limitation or held result.
- Content zones: contribution, quote-occurrence, forward, signature, footer, unknown; quote-source attribution requires separate explicit native/evidence support and can remain unknown. Keep raw/normalized spans and ordering even when quotes repeat.
- Native relationships: explicit reply-parent relation, ancestry path, quote hypothesis and source scope are distinct. Missing parent, cycles, duplicate Message-ID and cross-scope edges never become confirmed merely through subject similarity.
- Filtering: preserve all rule evaluations and version; conflicts are explicit. Grouping: retain source-specific scope/thread evidence and membership confidence/limitations, not old A2 grouping implementation. No cross-workset merges by default.
- Intermediate Kedro DataCatalog datasets are bounded; MemoryDataset copy_mode=assign only for frozen immutable values that passed tests. Trusted side-effectful Dataset.save/load bridges to msgloom, not a parallel Kedro business DB or YAML-configured filesystem storage.

## 5. Partition and claim ownership (C0.7 / C0.8 / C0.10)

One finite public awaitable Application prepare call begins from a saved Workset ResultRef, not a provider URL/path. It creates NO event loop, prefetched iterator, Scrapy spider or mutable-source scan. Preflight validates schema/versions/scope/canonical refs before any A2 publish.

- Intake PREPARE_INTAKE claim: existing consumer/cursor ownership; A2 never borrows that claim.
- Workset PREPARE claim: owns processing of one exact immutable Workset ResultRef; it does not authorise writes after expiry.
- Partition PREPARE claim: deterministic key SHA-256 of workset Ref, policy, partition ordinal and exact ordered selected occurrences. Execution/attempt ID intentionally omitted. Validate role/evidence first; only then divide into finite bounded partitions.
- Transition PREPARE claim: separately fences the exact ordered scoped transition batch; it cannot fabricate message bodies or consume primary selection claims.
- Conservative initial partition policy candidate: at most 16 validated selected occurrences and at most 16 MiB of verified source bytes per partition, with tighter true parser-specific budgets from measured Pi limits. These constants are NOT declared production-safe until P1/P2 profiling. A large single record beyond the limit is held rather than silently truncated.
- Grouping context: staged semantic metadata within this immutable workset, never an unconstrained look-back over earlier worksets. A later cross-workset enrichment must be an explicit versioned policy with bounded historical references.
- Deadlines: start only if remaining workset/partition lease exceeds measured CPU/parser-child upper bound plus cleanup margin; cancellation stops subsequent Kedro saves, drains the worker/child, then reconciles durable accepted keys before reporting terminal state.

Do not introduce unreviewed generic PREPARE stage saves into the existing prepare: plan-binding namespace. The legacy binding only knows schema v1. The new A2 acceptance binding must be a distinct versioned API with explicit claim and transaction support.

## 6. Canonical acceptance and same-key conflict (C0.12)

**Input-only logical key, version 1:** SHA-256 of canonical sorted UTF-8 JSON for (scope digest, immutable Workset ResultRef, partition ordinal, ordered resolved selected roots/roles/ordinal and/or exact transition fact, stage kind/schema, **all ordered accepted upstream ResultRefs**, frozen config/code/parser/rule/partition versions). Stable string prefix a2-accepted:. The prototype uses a domain-separation tag a2-stage-accepted-input@1 plus a null byte to avoid another hash namespace.

**Excluded from key:** output body, canonical output digest, current time, Kedro runtime node name, random execution/attempt ID and Python object hash.

**Separate accepted output:** logical key, exact result ref, canonical SHA-256, positive byte count and bounded metadata. The prototype pure append_or_verify accepts identical replay and rejects changed bytes **or** a substituted result ref under the same key.

**Required durable implementation:** a new A2-owned table with PRIMARY KEY(logical_key), canonical payload digest/length, accepted ResultRef and immutable lineage references, append transaction timestamp, publication claim/token proof and independent audit of attempts. Transactionally acquire SQLite BEGIN IMMEDIATE, verify active claim and frozen inputs/dependency refs, read accepted logical key, compare exact output digest and result ref, then insert the stage/semantic payload/acceptance row or return existing accepted ref. On integrity mismatch fail with stable scheduled-acceptance-conflict and preserve previously accepted data. Never expose an out-of-transaction get-then-insert as an atomicity proof.

**Postcommit cancellation:** existing Phase1Persistence can commit before returning a cancellation exception. If the caller sees CANCELLED or the worker disappears, the next authorised attempt first looks up the same accepted key and verified StageResult/SemanticDataRef and resumes from the earliest **not accepted** stage. A new attempt ID never renames an accepted output; its audit/history is append-only and separate.

The real SQLite negative test confirms current `StageResult` uniqueness prevents both equal-byte and changed-byte replay under a new attempt. The separate **research-only** transactional experiment demonstrates a claim-fenced input-key row which returns the original validated StageResult and semantic bytes without rewriting first-attempt metadata. The isolated SQLite table exercises `BEGIN IMMEDIATE` compare/insert across retries and two concurrent owners (both equal and conflicting payloads). These are evidence of design direction, **not** a qualified production migration.

**Critical boundary.** The experiment bypasses the old PREPARE plan-binding
path because its claim keys use the ``c0-a2:`` prefix. The legacy function
``bind_preparation_result`` returns early unless the claim key starts with
``prepare:``. That prefix is the **cause** of the bypass. Empty
``required_inputs`` is a **separate gap**: an empty input tuple would still
pass the v1 reference check, so it does not explain the bypass, and the
experiment claims carry no lineage.

The experimental ``publish`` call does **not** verify these items. Each item is
unverified:

1. **Status and limitations.** ``StageResult.status``, ``acceptable`` and
   declared limitations are not compared with the identity or the receipt. A
   replay counts as equal on digest and byte count alone, so a replay with a
   different status or limitations looks identical.
2. **Upstream refs.** The ordered ``upstream`` references and ``input_refs``
   are not checked for existence, kind, version or acceptance.
3. **Attempt versus claim.** ``require_claim_publication`` checks the
   execution only. The ``StageResult`` attempt is not compared with the claim
   attempt, as the legacy binding does.
4. **Workset scope.** The workset, the scope key and the selected roots are not
   checked against a durable workset. ``FrozenRoot`` is caller-constructible,
   and its fake digests are accepted.
5. **Batch transition identity.** ``StageIdentity`` now takes an ordered
   transition tuple, and the receipt requires one batch result. The prototype
   binds order and rejects duplicates. The batch-level production identity
   (what the batch claim and result bind) is still open.
6. **Kind and version allow-table.** The prototype table checks
   ``stage_kind`` against one fixed ``schema_version``. It is a local constant.
   The production table must be closed, versioned and tied to upstream arity.
7. **Synchronous facade bypass.** ``publish`` calls the private
   ``Phase1Store`` transaction directly. It skips the async facade accounting
   (semaphore, drain and close tracking).

The experiment therefore does NOT prove A1 input lineage, the production
publishing-plan receipt, finalization of the accepted A1 Workset, postcommit
crash recovery of this new index, or migration compatibility. The
**production** acceptance table/API has NOT been created, migrated, registered,
or exercised as a business workflow.

### Research-prototype limits (do not port to production)

- ``ExperimentalA2AcceptanceStore`` takes ``store._store``, a **private**
  attribute of ``Phase1Persistence``. It also uses the private
  ``_write_transaction``. A production API must expose a reviewed method.
- The tests call ``publish`` through ``asyncio.to_thread``. Cancellation of that
  await is **not protected**: the worker thread keeps running and may commit
  after the caller sees ``CancelledError``. The facade's own drain logic is
  bypassed on this path. Recovery needs read-back, and no test proves it for
  this path.
- On the row-exists path, ``publish`` decodes the stored semantic payload
  **inside the writer lock**. A 64 MiB payload would hold the lock and could
  outlast a lease. A1 loads proof before the writer transaction on purpose.
  Production must recheck metadata only inside the transaction.
- ``metadata.create_all`` on the scratch table is **experiment-only**. It runs
  in the constructor against a disposable ``tmp_path`` database. It is not a
  migration, and the table lives outside ``initialize_schema``. Production must
  not port it. ``byte_count`` is also a ``String(32)`` there, which production
  must not copy.
- The two concurrency tests use **different claim keys** for the two owners.
  A production deterministic partition claim key is the same for both, so the
  second owner would fail with ``ClaimUnavailableError`` before it reaches the
  acceptance table. The tests therefore exercise the table's BEGIN IMMEDIATE
  compare-and-insert in isolation: the claim fence cannot separate the owners,
  so the row decides. They start both threads without a barrier, so they show
  SQLite serialization and do not prove that the writes overlapped.

## 7. Held-only, transitions and new completion receipt (C0.11)

Receipt@2 must cover every ordered **workset.selections occurrence**, not only workset.selection_refs (which deduplicates equal ResultRefs). For each occurrence there is exactly one terminal outcome:

- prepared@2 accepted and claim-bound with truthful COMPLETE/INCOMPLETE status; or
- a2_input_disposition@1 accepted and claim-bound with safe reason such as role_unverifiable, source_evidence_unavailable, parser_unsupported, input_limit or proof_missing. Its repair_class is operator_repair and it must not contain imaginary prepared content.

If workset.transitions is nonempty, require exactly one accepted prepared_transitions@2 batch whose ordered transition list equals the frozen workset.transitions; no foreign entries, overlapping claims or missing transitions. Intake-held workset.held are an independent exact set without selected roots and are never rewritten by A2.

**Receipt terminal status:** COMPLETE only if every selected root is prepared complete, all required scoped transitions are terminal COMPLETE, and workset.held is empty. Held-only or any incomplete/held root yields INCOMPLETE. This is a **new v2 policy change**: the legacy completion code can finalize a held-only workset as COMPLETE (section 1). A1 and the legacy code stay unchanged. Missing/overlapping/foreign root, stale claim, incomplete publication, unaccepted output, unknown schema, or contradictory status yields FAIL/BLOCK at finalization rather than a forged complete receipt.

**Accepted v2 proof:** the producer must transactionally validate each stage's publishing claim receipt, accepted logical key/output digest, exact roots and source version scopes before writing the immutable completion receipt. A normal scheduled call may mark a fully accounted but held-only workset **terminal INCOMPLETE**, not leave it pending and spin indefinitely. A later operator-approved replay writes a NEW A2 attempt/receipt targeting the same original workset without changing the previous accepted terminal proof. The v2 reader/retirement of v1 proof requires a separately reviewed migration and A3 adapter.

The research prototype CompletionReceipt checks exact structural root order/count, per-root terminal version, optional exact transition batch and held/status logic. It deliberately does not claim to validate live SQL claim history or semantic payload bytes.

## 8. Failure classification and external scheduling (C0.13 / C0.14)

| Origin | Public terminal state | Safe code | Next action |
| --- | --- | --- | --- |
| No work and no pending | COMPLETE | none | Idle, await next hint or catch-up |
| Pending finite backlog | INCOMPLETE | scheduled-work-pending | Continue with bounded progress-aware backoff |
| Consumer claim busy | INCOMPLETE | scheduled-consumer-busy | Coalesce and retry later |
| Workset held-only or A2-held but fully accounted | INCOMPLETE, terminal | scheduled-work-held | Operator repair/replay; **no automatic spin** |
| Expected catalog pin mismatch | BLOCKED | scheduled-catalog-mismatch | Stop scope for manual repair |
| Escaped SourceReferenceError from intake/preflight | BLOCKED | scheduled-source-reference-invalid | Stop and protect anchor; do not parse error strings |
| Post-intake verified re-read/evidence failure | INCOMPLETE, terminal held when proved | scheduled-work-held | Save A2 input disposition; explicit replay |
| Unsupported trusted authority | BLOCKED | scheduled-invalid-authority | No mutation |
| Missing/expired/stale active claim at durable write | FAILED | scheduled-claim-lost | Stop saves, reconcile accepted keys |
| Canonical output conflict under accepted logical key | FAILED | scheduled-acceptance-conflict | Stop automatic replay, investigate nondeterminism |
| Valid partial parse/output with declared limitations | INCOMPLETE, terminal | scheduled-preparation-incomplete | Preserve accepted partial ref; explicit repair only |
| Unexpected SQLite/invariant error | FAILED | scheduled-persistence-failed | Preserve committed earlier stages and alert |
| External cancellation | CANCELLED, reconciled | scheduled-cancelled | Drain, read accepted stage keys and preserve durable state |

An external Prefect flow is only a wakeup/hint. The stable configured source/stream/consumer identity and durable A1 release/cursor determine admissible inputs. Coalesce duplicate hints. Periodic finite catch-up reads a proposed privacy-safe scoped status **via msgloom CLI**, not direct Prefect SQLite access. Status exposes catalog/scope hashes, cursor anchor digest, pending count, last accepted receipt digest, count of intake/A2-held and most recent safe terminal code; never provider content, URL, raw identity, file path or credentials. Repeated no-progress terminal held outcomes are not automatically retried.

## 9. C0 acceptance matrix and explicit remaining work

| Gate | Contract decision | Required implementation proof |
| --- | --- | --- |
| C0.1 | Frozen incremental and approved-baseline roots | Native A1 reader + version-pinned identity/equality, component/duplicate/baseline cases |
| C0.2 | ExtractedComponents and ParsedParts | Reference/digest/limits, missing/unsupported/partial parser and hostile bytes |
| C0.3 | NormalizedContent, ContentZones | Exact offsets, semantic quote occurrence vs attribution, no silent drops |
| C0.4 | NativeRelations | Native parent evidence, unknown/duplicate/cycle/cross-scope negatives |
| C0.5 | Filter, Group, ScopedTransition and manifest | All rules and source scope retained, transition-only and context-only |
| C0.6 | prepared@2, zones@1 and v2 proof/adapter | New registered canonical codecs and A3/A5 historical-reader compatibility |
| C0.7 | Async public Application and owned Kedro worker | Preflight rejects before IO, no nested event loop, terminal OperationOutcome |
| C0.8 | Deterministic finite partitions, workset-scoped grouping | Bounded Pi profiling, stable policy and no cross-scope joining |
| C0.9 | Exact same A1 ReleaseEntry re-read | Ordinal+fact members+saved selection byte equality; baseline/Teams/transition fixtures |
| C0.10 | Separate workset/partition/transition claims | Concurrent, expired, lost, queued and postcancel fences in real SQLite |
| C0.11 | Held disposition and receipt@2 | Exact all-root/transition coverage, held-only terminal INCOMPLETE and replay |
| C0.12 | Input-only accepted key plus output verify | Real atomic acceptance table, conflict rollback, crash/restart and accepted-stage skip |
| C0.13 | Typed scheduled error classification | SourceReferenceError vs post-intake hold, consumer busy and claim loss |
| C0.14 | External read-only scope progress | Privacy leakage, no direct Prefect DB access, no terminal spin |

**C0 is not yet eligible for a production freeze:** the proposed result/receipt schemas and SQL acceptance store remain research artifacts, the component/relation edge fixtures, production baseline reader and A3 adapter are not qualified, Snyk CVE-2026-3840 requires an explicit owner applicability decision and Kedro is not a production dependency. An independent read-only C0 review can accept **contract direction and existing-store limitations** separately from production readiness.

**Next implementation increment (isolated):** publish exact v2 Pydantic codecs/DB migration behind a new reviewed API in a separate C0-owned branch, then qualify the full required-input/plan receipt transaction with genuine A1 Workset roots and Phase1Persistence read-back; do not modify A1 or register an automatic legacy fallback. The first accepted production contract change must have a single reviewer, a new exact SHA and targeted CI. Only after that may Kedro P1/P2/P3 parallel workstreams begin.
