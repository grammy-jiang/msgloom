# A2 Kedro-primary ETL architecture (reconciled design)

**Status:** DRAFT FOR INDEPENDENT DESIGN REVIEW, NOT IMPLEMENTATION APPROVAL.
**Date:** 2026-10-23, Australia/Sydney.
**Source baseline:** master 895fc40a0ec889bd96f620df8c62491787218217.
**Accepted A1 boundary:** Task 15 source 34057c6c9f85688fd2bd1868d90302ab5a61205f.
**Governing owner decision:** [ADR-A2-20261023](../decisions/2026-10-23-a2-kedro-primary-etl.md).
**Implementation plan:** [A2 Kedro-primary plan](2026-10-23-a2-kedro-native-implementation-plan.md).
**Automatic release-to-ETL handoff:** [A1 Release -> Kedro A2](2026-10-23-a1-release-to-kedro-auto-handoff.md).
**Review record:** [Readiness audit](../notes/a2-kedro-readiness-audit-20261023.md).
**A1 output and automatic activation:** [Source-verified integration](../notes/a1-kedro-handoff-activation-20261023.md).
**A1 post-release orchestration plan:** [Automatic wake-up, catch-up, and E2E gates](2026-10-23-a1-release-to-kedro-auto-handoff.md).

## 1. Non-negotiable architectural decision

**Kedro is the primary A2 ETL framework**, not a decorative subgraph attached to the existing A2 implementation. Its Pipeline/DataCatalog/Runner determine the dependency graph and dataflow from exactly pinned A1 source inputs, through content extraction, parser dispatch, normalization, zoning, evidence-aware native relationships, filtering and grouping, to versioned stage publication.

The old A2 is **deprecated architecture**. Do not inherit PreparationHandler, RecordSteps or StageSteps as the new runtime engine; do not permanently maintain a selectable legacy engine; do not require line-by-line behavioral parity with old algorithms. Existing parsers, pure domain functions, type validators, and tests are useful candidates and acceptance references, not blanket code-reuse requirements. Any reuse must be argued as a self-contained, well-owned capability; old A2 private methods do not constrain the new architecture.

**The A1-to-A2 boundary is an exception to this deprecation.** Its accepted release ledger, reader, exact selection/workset, cursor, held/pending state, scoped transitions and historical-baseline contract were built specifically for downstream A2 and must remain authoritative and unchanged. Physical directory names are irrelevant: retained handoff code may be under preparation_pipeline without requiring preservation of legacy A2 orchestration.

Older 2026-09-29 local plan (c7dcb41) and early 2026-10-23 proposals (37f5886 and c1ac6cf) were based on narrower Kedro migration/pure-subgraph assumptions and are superseded as implementation authority. Historical reviewer REVISE findings remain archived; they are not an acceptance of this revised concept.

## 2. Accepted A1 output: freeze once, process exact inputs only

A1 remains the Scrapy 2.19.0 Graph-over-Scrapy acquisition subsystem. Its Spiders and provider extensions own traversal, raw response/attachment evidence, complete/partial acquisition facts, source/provider version and scope, native relationships, checkpoint authority, and atomic release-group publication. A2 never consumes live Scrapy Requests/Responses, mutates provider checkpoints, or issues Graph reads.

The A1/handoff layer exposes (names refer to existing, accepted contracts):

- Source identity and immutable evidence; atomic committed ReleaseGroup / ReleaseEntry with ordered facts and exact hashes.
- ReleaseSourceReader reading immutable ReleasedInput (reference, primary selection, components, contexts, scoped transitions, facts) with evidence/digest checks, not current mutable projection fallback.
- PreparationIntakeService capturing one bounded release cutoff into exact collected_selection@1 and PreparationIntakeWorkset, preserving catalog/source/stream/consumer anchor, held entries, transitions and pending fairness. Durable cursor advancement means **selection admission**, not successful parsing.
- Explicit historical baseline and read_supporting_context for caller-approved historical context. Context never becomes primary work merely because it exists in SQLite.
- Manual exact replay, restart after failures, scope-aware deletion/restoration and publication after semantic completion.

**Automatic operation:** A1's committed ReleaseGroup/ReleaseEntries are the only source eligibility signal; the external Prefect orchestrator may wake one finite prepare-scheduled invocation after collection, with a configurable reconciliation trigger as a durable catch-up. Prefect job completion is never the evidence of A1 release; Ledger + fixed cursor cut are. The existing CLI still runs legacy A2 until this Kedro engine passes and is substituted. See the companion automatic-handoff plan for PIN/consumer configuration and no-work/pending/recovery semantics.

**Do not reopen accepted A1** to make Kedro integration convenient. A2 receives one immutable workset and exact selected versions; it must not list_versions or infer current "new" work from database timestamps. Component-only, context-only and transition-only entries must retain their semantics and cannot be coerced into fabricated message bodies. A1 Task 15 formally qualified 20 Spiders/13 scenarios on source 34057c6; that evidence does not qualify new Kedro code. Live work/school Teams acceptance and external scheduler deployment remain excluded.

## 3. System layers and ownership

| Layer | Responsible engine | Does | Does not |
| --- | --- | --- | --- |
| Acquire and publish A1 releases | Native Scrapy + A1 catalog | Saved bytes, identity, complete release groups and atomic proof | Call Kedro or interpret A2 business semantics |
| Admit exact immutable work | Existing reader + intake + Phase1Persistence | Verify ledger, pin release cutoff, write workset/pending/cursor | Choose A2 ETL node ordering or parse content |
| A2 ETL graph | **Kedro Pipeline + SequentialRunner** | Own ordered extract/parse/normalize/zone/relate/filter/group/result-stage dependencies | Own A1 cursor, business transaction authority, provider credentials |
| A2 data interfaces | **Programmatic DataCatalog** with trusted datasets | Load exact A1 evidence; execute approved parser service; enforce durable stage-output dependency and side effects | Scan mutable DB, use Kedro's versioned dataset paths, invent business IDs |
| Trusted async service layer | msgloom Application, parser isolation, persistence | Async bounded source reads, parser sandbox/cleanup, claims/leases, SQL transaction fencing, schema versioning, terminal outcome | Replace Kedro ETL graph with the old PreparationHandler loop |
| A3/A5 downstream | Existing consumers, with explicit schema adapter if necessary | Consume accepted output identity, provenance and known limitations | Assume all prepared content is complete or from the old layout |
| Deployment | External Prefect or finite CLI invocation | Trigger an awaited A2 operation and observe status | Schedule individual Kedro nodes, daemonize an in-package worker |

The new A2 may add schema versions (`prepared@2`, `zones@1` etc.) with reviewed migrations and consumer adapters; compatibility is required at *public* A3/A5 and saved-result semantics, not private old-A2 classes. Do not change `collected_selection@1`, `preparation_intake_workset@1` or A1 release business semantics as an incidental step.

## 4. Kedro-owned A2 ETL DAG

A finite A2 invocation takes one caller-authorized immutable workset. Admission and workset durable claims occur outside Kedro, then a programmatically built, bounded Kedro Pipeline processes only its exact selected records. Workset partitioning must be deterministic, bounded and source-version-aware; the old private max_records algorithm is **test data**, not automatically new policy. If scope/partition policy changes grouping outputs, version it and get explicit acceptance rather than treating old grouping as truth.

    A1: committed release ledger and immutable captured evidence
      |
      v
    accepted ReleaseSourceReader -> durable PreparationIntakeWorkset
      |                         (A1/intake owned; no Kedro dependency)
      v
    Kedro Pipeline / DataCatalog per bounded workset partition
      |
      +-- exact_handoff_input          [trusted read-only dataset]
      |    -> select_source_components [source, byte refs, contexts, transitions]
      |    -> verify_and_extract        [trusted saved-byte dataset service]
      |    -> parse_content             [trusted isolated parser dataset service]
      |    -> normalize_content         [canonical characters/metadata/structure]
      |    -> zone_content              [author/quote/forward/signature/etc. zones]
      |    -> map_native_relations      [scope-qualified, evidence-bound]
      |    -> apply_deterministic_rules [all matched filters and conflicts]
      |    -> group_communication       [confirmed/uncertain/none]
      |    -> construct_output_manifest [exact stage and limitation lineage]
      |
      +-- scoped_transition_lane       [presence, absence, refresh, removal]
      |    -> scoped_result_dataset     [no fabricated content or global deletion]
      |
      v
    claim_fenced_result_datasets: ordered durable semantic-stage results
      |
      v
    msgloom: check valid claims / finalize accepted workset proof
      |
      v
    A3 input adapter -> A3 -> A5

**Kedro owns the graph, including parsing and stage publication ordering.** Parsing itself runs in a sandbox maintained by msgloom; durable writes themselves are performed by the existing msgloom Persistence API. That is not the same as moving these phases outside the Kedro ETL DAG: they are reached through trusted `AbstractDataset` adapters that Kedro loads/saves in the declared dependency sequence. No new independent A2 orchestration loop may reimplement this business ETL order.

The implementation can construct bounded per-record subpipelines plus a batch group/transition subpipeline if that is demonstrably the safest way to retain stage-level durability and resource limits. Such composition still needs a **single architecturally coherent Kedro-controlled ETL graph** for each frozen work unit, with explicit public run manifest and typed inter-stage datasets. Merely invoking separate "filter" and "group" Kedro functions after controller-side parsing is prohibited.

## 5. DataCatalog adapters: Kedro schedules, msgloom holds authority

All dataset names are static or bounded ordinal labels such as `record_0003_parsed`, never provider IDs, subjects, emails or file paths. Use only programmatic catalog construction with exact known datasets; no YAML-driven class imports, `DataCatalog.from_config`, external plugin discovery, `kedro-datasets` or Kedro's path-versioning. `SequentialRunner(is_async=False)` is preferred until the security/runtime gate independently confirms the pinned API.

### 5.1 Trusted dataset interfaces (proposed contract)

| Dataset role | `load` / `save` behaviour | Who owns correctness |
| --- | --- | --- |
| `ExactHandoffDataset` | Load only exact approved workset and selected version refs; never enumerate current A1 | Reader/Intake verified IDs, bounds and file pin |
| `VerifiedEvidenceDataset` | Materialize only selected SavedByteReference with digest/limit/containment verification | Saved source reader, not source-controlled paths |
| `IsolatedParseDataset` | An upstream node emits a typed, strictly bounded ParserRequest; dataset save invokes the approved parser service and records a typed result; downstream load obtains it | Parser sandbox and bounded process cleanup |
| `MemoryDataset` | Finite immutable typed intermediate records/zone/relationship/filter results | Kedro dependency graph, memory ceiling and copy-mode test |
| `ClaimFencedSemanticDataset` | Persist accepted stage value via exact token, schema codec, dependency refs and version; downstream `load` yields a validated committed reference + payload | msgloom Persistence transaction/ClaimToken, not Kedro's own versioning |
| `ScopedTransitionDataset` | Publish exact scope-limited, typed transitions/refreshes under the separately owned transition claim | Existing approved transition/claim contract |
| `ResultManifestDataset` | Resolve and check every exact durable stage ref before workset receipt | Application/Phase1Persistence acceptance proof |

A dataset wrapper must be invocation-scoped, typed and fully audited. It may delegate through a narrow asynchronous bridge but **must not establish a second durable database, background queue, business checkpoint, implicit retry or separate source of truth**. Value returned by a node is not considered accepted until its claim-fenced dataset save has finished and a resolvable ResultRef is stored.

**Kedro's public DataCatalog/AbstractDataset contract supports both loading and saving stage outputs.** Whether a specific pinned Kedro version preserves dependency order, release and partial output semantics under exceptions must be proven on actual source/tests before implementation.

### 5.2 Actual ETL stage models

Working data shapes must be immutable and versioned; names are proposals, not demands to duplicate existing types:

- `FrozenSourceSelection`: exact released workset reference, selected source identity/version, source scopes, references and whether the entry is supporting, context-only, component-only or primary.
- `ExtractedComponents`: verified byte digest/size, body+alternate MIME representations, attachment refs, provider-native metadata, provenance, explicit unavailable components.
- `ParsedParts`: parser identity/profile, checked format, document blocks with sheet/cell, page/span and paragraph/table provenance, known omissions and parser-specific limits; no fabricated empty content.
- `NormalizedContent`: canonical textual and structural surface with reversible source-offset mapping, time/participant metadata and encoding normalization; preserved evidence bytes never overwritten.
- `ContentZones`: origin-contribution, quote occurrences, forwarded content, signature/footer and uncertain boundaries; each zone cites exact source spans. **Quote occurrence is not proof of quote source.**
- `NativeRelations`: reply-parent, indirect ancestry, exact source-native group candidates and quote-source hypotheses as **distinct** typed edges, with evidence and ambiguity status.
- `FilterDisposition`: explicit included/excluded/guidance/conflict with complete matched rule IDs and replayable input.
- `GroupingDisposition`: Confirmed/Uncertain/None based on actual in-scope native evidence. No subject-only, time-only or cross-source semantic joins.
- `A2ResultManifest`: accepted stage result refs, schema versions, exact input lineage and limitations; no assertion of success based solely on Kedro runner exit.

New zones and semantic provenance may require new A2 schemas and an A3 adapter; do not flatten novel information solely to make outputs equal old `PreparedRecord`. No unsupported text boxes, hidden cells, encrypted attachments or missing parent links may be silently treated as complete.

## 6. Fully async Application, synchronous Kedro: technical boundary

Kedro nodes and SequentialRunner are synchronous. The public `async def prepare(...)` must remain genuinely awaitable and nonblocking; do **not** run Kedro directly on the Application event loop or invent an unreviewed custom `AsyncKedroRunner`.

**Selected architecture candidate:** one finite, owned Kedro runner worker per admitted operation (initially one thread), with a narrow, typed `AsyncServiceBridge`. Inside that worker, Kedro nodes/datasets use only synchronous service facades. For safe A1 evidence read, isolated parser process, or Phase1Persistence, the facade submits the exact requested coroutine to the still-running Application loop (e.g. `asyncio.run_coroutine_threadsafe`) and waits in the **worker** with an independent bounded deadline. The outer async caller awaits the owned worker and retains all claim/lease and cancellation authority. Never call this facade from the event-loop thread; fail fast if wrong-thread invocation or nested event loop is detected.

A prototype must independently prove this bridge rather than assuming it works:

- no deadlock when datasets load/save, wrapper exceptions, cross-thread cancellation or worker shutdown happen concurrently;
- no producer publishes after cancellation, timeout or lease loss; all stage writes re-check claims inside their actual transaction;
- parser child reaped on deadline, resource ceiling or repeated cancel; no unobserved detached futures or thread;
- `execution_timeout` stops new work and writes; finite cleanup/drain fits a measured lease margin; if a CPU-bound node cannot terminate in bounded time, **do not ship** and reconsider the execution boundary in a separate design revision;
- no event-loop blocking under CPU, saved-byte I/O or SQLite load;
- equivalent restart/replay and no duplicate work/semantics despite failure between save and output manifest;
- all errors are converted to bounded classifications with no private source bodies or exception text in Kedro node/dataset logs.

The bridge is *transport/lifecycle plumbing*, not a second workflow engine. No custom thread-pool queue, polling scheduler, unsafe `asyncio.run` inside the Application thread, model calls, or unbounded subprocess tree.

## 7. Integrity, budget, failure and replay guarantees

### 7.1 Admission and resource budgets

Before launching a Kedro graph, validate frozen workset and exact captured selections against bounded record count, declared evidence byte sums and allowable source scopes. Reject invalid replay references **before** claim acquisition, and do not collapse repeated versions into one primary item. Compare hashes and content at load; do not copy stale values from live A1 projections.

Parser resource limits include wall time, RSS, decompressed bytes, output bytes and container members; selected and derived byte totals and total parser-output budget apply to their declared batch/workset boundaries, never only independently to each record. Missing evidence is classified held/partial as appropriate; aggregate overflow must not be converted into harmless single-component limitation. Preserving the earlier design's safety rule does not imply preserving every obsolete private implementation detail.

### 7.2 Claim-fenced writes and partial results

Kedro controls when a prepared, zoning, filter, grouping or scoped-transition output reaches its `ClaimFencedSemanticDataset`. The save delegates to the *existing* claim-fenced Persistence transaction. Each accepted StageResult has exact source/version, upstream result refs, schema version and byte/digest evidence; saving a downstream group without its required committed prepared/filter/zone dependencies must fail closed.

The business partial-progress contract is explicit: results already durably accepted at the time of a later node/parser failure remain accessible for replay and diagnostic inspection, but a failed workset is **not complete**. There is no requirement to copy the old private stage-save order: the new graph's declared durable checkpoints define which partial refs may survive. Create independent tests with injected failures before/after each claim-fenced save, after parser output, and at group finalization; do not reuse tests that monkeypatch only the old class internals as proof of Kedro behaviour.

External cancellation drains accepted I/O, parser and dataset operations under finite limits and cannot change an accepted result to an overwritten result. A stale/expired claim cannot append a semantic stage. Workset finalization requires exactly the accepted required manifests and source scope, never just a green Kedro exit. Held missing/corrupt entries allow later valid release progress without falsely marking the held content as understood.

### 7.3 Replay, schema evolution and downstream

A1 selection/release identities, consumer anchor and cursor remain authoritative. Replay reopens exact saved sources/byte digests and A2 versioned policy/normalizer/parser configuration. It never discovers a "latest" A1 row; changes to code or rules require explicit, recorded semantic reruns.

A2 internal schema may evolve to preserve richer zoning/source mapping. Choose an explicit strategy before cutover: either add versioned `prepared@2` / `zones@1` results with a typed A3 adapter, or prove `prepared@1` can fully represent required output without information loss. Do not silently reinterpret old accepted results. Existing A3/A5 must still receive unambiguous source/version/limitation evidence; report coverage and cross-stage identity must be demonstrated on the new chain.

Task 15's 28-gate record is frozen and historically accepted. The **new Kedro candidate** needs new source-aware 13-scenario acceptance/targeted tests and an independent full exact-SHA review; cannot claim historical gates as new engine qualification.

## 8. Parsing and semantic behavior requirements

A2 parsing covers MIME/email/HTML, Excel, PDF and Word and only the formats actually selected and collected. Use stored bytes, not provider fetches. Preserve tables, links, ordered content, spreadsheet coordinates/hidden/formula state, PDF page/block limits and Word paragraph/table ordering; distinguish scanned/encrypted/unsupported/partial and record omitted coverage. OCR and other extraction profiles are opt-in and separately validated.

Normalize with explicit chronology, participants, source span/cell/page mapping and reversible source provenance. Zoning can identify quote occurrences or likely signatures but must not fabricate source authorship. Duplicate Internet Message-ID and missing parent relations retain alternatives/uncertainty. Proven research Topic 01/02 synthetic validations are adversarial test design references, not automatic production correctness claims. Source-native grouping confirms only exact supported same-scope relations (including explicit supported Teams chat reply when resolvable). Calendar, To Do, OneDrive and Contacts remain contextual, never automatic message groups. Stage/limitation lineage must reach A3/A5.

## 9. Runtime and security

Kedro Core candidate (2026-10-23): 1.7.0, pending independent pinned-version/source/security checks. PyPI wheel hash must be checked before execution; verify exact installed `AbstractDataset`, `DataCatalog`, `MemoryDataset`, `SequentialRunner` APIs on Python 3.12/3.13/3.14 and ARM64. Q0 must reconcile Kedro CVE-2026-3840 vs CVE-2026-35167 for the exact installed wheel with dated OSV/GitHub/GitLab/Snyk review and no unapproved ignore.

No Kedro CLI, server, project scaffolding, YAML-driven object import, Kedro versioned data paths, plugin auto-discovery or telemetry. Initialize KEDRO_DISABLE_TELEMETRY or DO_NOT_TRACK before import and network-deny tests. Allowlisted programmatic datasets and nodes only; LogRecorder should redact data and not blindly propagate `DatasetError` messages. Measure worst-case MemoryDataset copy cost on Pi; use explicit immutable-object copy semantics only after source-level verification. Windows portable smoke does not qualify native secure A2 reader; real Teams live work/school tenant is separate.

## 10. Automatic activation after A1

The new Kedro A2 starts from the **already accepted** PreparationIntakeWorkset
and exact saved selection references, not from an active Spider or the mutable
A1 database. The existing `prepare-scheduled` command is a finite intake
operation whose producer dispatch currently points to the obsolete
PreparationHandler. Integration replaces **only that dispatch/composition** with
a qualified Kedro-primary producer and keeps the accepted
PreparationIntakeService, consumer cursor, held/pending index, exact reader,
scoped transitions and historical-baseline contracts unchanged.

A1 must not import Kedro. External Prefect (or the authorized finite-command
launcher) should enqueue/coalesce an A2 wake-up **after each finite A1 attempt
terminates**, including attempts that may have committed some valid releases
before a later failure. Such a wake-up is merely a hint; Kedro handles only
ReleaseEntries already committed and frozen by intake. Startup plus
configurable, low-frequency reconciliation must cover wake-ups lost after a
commit. A single release entry is not a universal ETL batch: intake uses an
exact bounded cutoff, processing uses its own bounded partitions, and entries
published after the cutoff wait for the next invocation.

Use one stable IntakeScope (catalog, source, stream, consumer) per target.
Do not reset consumer_id to retry, infer accepted history from SQLite rows,
blindly run a persistent in-process scheduler, or invoke A2 from Scrapy close
signals. On backlog, repeat finite pending-work attempts; never loop
unboundedly. Duplicate/concurrent wake-ups resolve through the existing
claims and persisted cursor, not an in-memory lock.

**Current operational truth:** `msgloom prepare-scheduled` and its durable
intake path already exist, but an external Prefect A1→A2 wake-up flow is not
deployed by Task 15. This is a new deployment work item, not a claimed
existing feature or permission to change A1's accepted schema.

See the [exact ReleaseEntry/CollectedSelection/Workset crosswalk and
activation fault table](../notes/a1-kedro-handoff-activation-20261023.md).
The native Mail A1→legacy A2 test passed on the current baseline, but new
Kedro activation still needs independently reviewed tests and code.

## 11. Verification and release decisions

A2 replacement requires proof of all of the following, attached to one new exact source SHA:

- Kedro is demonstrably responsible for **extract, parse, normalize, zone, relate, filter, group, and stage-result load/save dependencies**; graph topology and mutation tests fail if any stage is removed or bypassed.
- Accepted A1 reader/intake/cursor/workset schema and 20 Spider/13 scenario obligations are unchanged; no A1-to-Kedro import or unfrozen current-state fallback.
- Parser service and async bridge validate cancellation, deadlines, IO budgets, process cleanup, claim fencing, exact replay and partial durable results.
- New semantic zoning and conservative source relationships are validated with independently authored gold and ambiguity/abstention cases; old A2 oracle fixtures contribute evidence but do not dictate the new architecture.
- A3/A5 consume exact accepted new A2 versions via tested adapter, including limitations and changed/retracted scoped facts.
- Python 3.12–3.14 test matrix, native Linux security gates, installed-wheel smoke, static checks, security scans and no-network/telemetry enforcement pass.
- Simpler business architecture than a bespoke A2 ETL engine; no parallel production pipelines or permanent `A2_ENGINE`. Measure adapter/bridge LOC, graph complexity, wall-clock and RSS on constrained Pi. A Kedro DAG that only decorates a custom pipeline is automatic **NO-GO**.
- Fresh independent architecture/security review and full candidate review return ACCEPT; no inferred approval from lint or historic 28 gates.

**Open engineering proof:** The trusted synchronous Kedro dataset-to-async msgloom bridge and stage-save semantics are a feasibility gate. If that bridge cannot be implemented with bounded shutdown, exact claims and acceptable complexity, the team must **revise the Kedro-primary integration design**; it must not secretly reduce Kedro to a two-node pure helper DAG or relax the user's decision.

**Implementation not started.** The companion plan enumerates architecture probes, schema decisions, parallel tasks, testing and cutover. Original R1/R2 technical reviews remain REVISE and must not be relabeled.
