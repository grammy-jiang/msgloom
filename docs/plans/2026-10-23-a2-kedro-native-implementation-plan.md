# A2 Kedro-primary ETL implementation plan

**Status:** DRAFT FOR REVIEW — no production implementation authorized by this planning work.
**Date:** 2026-10-23 (Australia/Sydney).
**Decision authority:** [ADR: Kedro is A2 ETL](../decisions/2026-10-23-a2-kedro-primary-etl.md).
**Architecture:** [A2 Kedro-primary architecture](2026-10-23-a2-kedro-native-design.md).
**Automatic A1 trigger/cursor design:** [A1 release-to-Kedro handoff](2026-10-23-a1-release-to-kedro-auto-handoff.md).
**Accepted A1 source:** 34057c6c9f85688fd2bd1868d90302ab5a61205f (28/28 Task 15 exact-SHA gates).
**Current master at planning:** 895fc40a0ec889bd96f620df8c62491787218217.
**Historical review:** 37f5886 R1 REVISE, c1ac6cf R2 REVISE; neither approves this redesigned plan.
**Actual A1 output / activation contract:** [Source trace](../notes/a1-kedro-handoff-activation-20261023.md).
**Automatic activation execution plan:** [AUTO-01–AUTO-26](2026-10-23-a1-release-to-kedro-auto-handoff.md).

**New D4 R3 hard prerequisites:** (1) immutable role/provenance re-read matching
against a reduced workset; (2) a deliberate new A2 scheduled outcome taxonomy
that distinguishes trust BLOCKED, normal pending, busy claim and held-only;
(3) exact intake/workset/partition/transition claim ownership, finite worker
drain budget and deterministic accepted semantic result identity. Details:
[R3 corrective contract](../notes/a1-kedro-handoff-r3-corrections-20261023.md).
The historical R3 reviewer returned REVISE; this revised design remains
unaccepted until a separate exact-SHA review.

## 0. Implementation objective and authority boundaries

Build a **fresh Kedro-primary A2 ETL pipeline**: exact A1 released inputs -> verified extraction -> parser execution -> normalization -> semantic zoning -> source-native relationships -> deterministic filtering -> bounded grouping -> durable versioned semantic outputs -> A3. Kedro must own the stage-level dependency graph and its DataCatalog I/O relationships. It cannot merely be invoked by the old custom PreparationHandler after parsing and before saving.

Deprecated old A2 code is an **acceptance reference**, not a migration target. Retain only explicitly accepted A1-to-A2 handoff/reader/intake code and shared components that independently satisfy their new interfaces. Do not automatically preserve old internal batching, prepared serialization, private helper methods or heuristics. Any changed semantics require new versioned evidence and explicit A3/A5 compatibility.

Non-goals: A1 changes, new provider access, provider write scopes, AI triage or semantic topic joining, A4 investigation, A5/report rewrite, external scheduler deployment, Kedro CLI/session/project scaffolding, permanently dual A2 engines, generic custom async Kedro runner. No shipping A2 code before D4 design acceptance and Q0 framework/security feasibility passes.

## 1. Worktree, ownership and source discipline

- A1 frozen: message_ingest/, microsoft_graph/ and A1 catalog/release ownership. Do not modify these without separate review and authorization.
- Handoff frozen by contract (even though some code physically lives in preparation_pipeline/): ReleaseSourceReader, PreparationIntakeService, saved workset/cursor/held/historical baseline and scoped transitions. No second intake or cursor.
- New Kedro ETL owner: new package such as msgloom/a2_kedro/ with clear source selection, parser adapter, zoning, relations, filters, groups, dataset bridge, result publisher, runner, typed contracts.
- Shared schema/dependencies owner: one manager handles pyproject.toml/uv.lock, migrations and cross-stage A3 adapter integration; no concurrent lockfile edits.
- Source/fixture owners: separate parser/zone/source shapes in own worktrees; never alter A1 or published Task 15 evidence.
- Independent reviewer: separate from code author; reviews exact SHA, tests, security, clock/cancel/claim boundary and semantic accuracy. No self-attested acceptance.
- All changes on isolated feature worktrees from fixed manager integration SHA; do not touch untracked archival research in the main Pi checkout. Avoid git clean/reset broad deletes. Keep each Python module under 500 lines, use only approved native dependency versions and existing project conventions.
- Production A2 remains as currently installed until a new Kedro A2 fully qualifies and cutover occurs. Preserve a Git rollback tag/commit; do not maintain a permanent public A2_ENGINE knob.

## 2. Dependency graph and major gates

    H0 prior-decision reconciliation + A1 authority audit
       |
       v
    D0 design + D1 main DAG & dataset/async contract + D2 implementation plan
       |
       v
    D4 independent design review (must ACCEPT)
       |
       v
    Q0 Kedro pinned-source/security/bridge feasibility
       |
       +--- NO-GO -> stop / review architecture without touching production
       |
       v
    F0 locked dependency isolated qualification
       |
       v
    C0 frozen new A2 input/output/version contracts + A3 adapter strategy
       |
       +----------+------------------+
       |          |                  |
       v          v                  v
    P1 Kedro   P2 format/zone      T0 golden/negative
    DataCatalog  extraction         fixture oracles
       |          |                  |
       +----------+------------------+
                  |
                  v
    E0 end-to-end ETL DAG + atomic stage persistence
                  |
                  v
    I0 manual/scheduled composition cutover, A3 adapter and Prefect trigger
                  |
                  v
    V0 acceptance and independent exact-SHA review
                  |
                  v
    R0 delete redundant legacy A2, update docs, release

The major gates are serial. After the C0 schemas are frozen, typed Kedro/Dataset work and parser/semantic fixture work can proceed in parallel. External wake-up design and fixtures may proceed in parallel with core Kedro work, but no live deployment begins until the new producer is accepted. No parallel worker gets permission to change the A1 handoff or shared dependency lock.

## 3. D0–D4 design readiness (this task, no source code)

| ID | Active edit target | Responsible | Artifact + acceptance |
| --- | --- | --- | --- |
| D0.1 | 15m | Supervisor | Historical 2026-10-03/07 decision and rejection of narrow Kedro migration recorded as ADR |
| D0.2 | 20m | Supervisor | Existing 20-Spider / 7-stream, 13-scenario accepted A1 release/intake matrix checked |
| D0.3 | 25m | Supervisor | Native A1 Mail release->frozen Workset->finite prepare exact-source E2E verified and source-ref crosswalk recorded |
| D1.1 | 20m | Architecture author | Kedro-owned extract/parse/normalize/zone/relations/filter/group/publish DAG drawn |
| D1.2 | 20m | Architecture author | Programmatic DataCatalog and exact read, parser, semantic and transition dataset roles |
| D1.3 | 25m | Architecture author | AsyncServiceBridge and bounded runner/thread cancellation/claim handoff design |
| D1.4 | 20m | Architecture author | Versioned prepared/zoning contracts and A3 consumer adaptation strategy |
| D1.5 | 20m | Architecture author | Explicit legacy-A2 deprecation and no-permanent-dual-engine decision |
| D2.1 | 25m | Planning author | This DAG, small bounded tasks, file ownership and dependency restrictions |
| D2.2 | 20m | Planning author | Evidence-gated security, reproducible tests, perf/complexity, rollback |
| D4.1 | 15m | Static reviewer | Linked docs/paths, source decision matrix and Markdown/pre-commit checks |
| D4.2 | Review session | Independent AI reviewer | Exact-SHA source/doc review, must explicitly ACCEPT or REVISE |
| D4.3 | 15m | Supervisor | Revise findings, preserve review histories, review exact new SHA until accepted |

**Document lint is not D4 acceptance.** R1 and R2 reports of earlier incorrect pure-subgraph draft remain REVISE; a fresh review must consider the present ADR and main-ETL architecture rather than merely closing their P1 findings.

## 4. Q0 security/runtime feasibility — before any production code

Read-only research may begin after the design is recorded; manifest/lock edits require separate authorization and a successful D4 review.

| ID | Active edit target | Task | Hard acceptance |
| --- | --- | --- | --- |
| Q0.1 | 20m | Confirm latest safe Kedro candidate against official pinned API/wheel metadata; historical 1.6 plan was stale | Exact version/wheel SHA, stdlib platform support evidence |
| Q0.2 | 25m | Dated Kedro CVE-2026-3840 vs CVE-2026-35167 source-level reconciliation | OSV, GHSA/GitHub, GitLab, Snyk, PyPI/wheel hash risk record, no silent ignore |
| Q0.3 | 20m | Static inspect custom AbstractDataset load/save wrapping, DataCatalog output save/load, SequentialRunner node ordering, ephemeral release behavior and DatasetError logging | Pinned public API matches proposal, unsafe default paths rejected |
| Q0.4 | 20m | Design isolated no-network, no-telemetry programmatic catalog test; enumerate all transitive dependencies | No CLI/session, versioned file paths or auto-loading plugins; no sensitive logging |
| Q0.5 | Experiment gate | Execute **isolated** Kedro ETL proof: exact read dataset -> fake parser service dataset -> semantic dataset save via async bridge | Heartbeat proves async nonblocking; forced save fault/cancel/stale-claim proves no deadlock/late writes, bounded cleanup |
| Q0.6 | Experiment gate | Repeat tests on Pi aarch64 and CPython 3.12/3.13/3.14 with fixed test data | Stable wire/semantic output; compatible wheels and no native-process regression |
| Q0.7 | 20m | Independent Q0 review and GO/NO-GO on using Kedro for **full ETL**, not just pure transform | No-go if safe async dataset bridge cannot be demonstrated |
| Q0.8 | Manager-only change | Approved separate dependency PR with exact locked Kedro and hashes | No unintended downgrade; security audits green; no effectful A2 code in dependency PR |

Q0.5 requires an isolated disposable test environment and deliberately injected data only, not active production A1 catalog or secrets. Never execute untrusted downloaded sdist build scripts for exploratory source inspection. A security advisory exception requires an explicit owner decision, expiry and demonstrated reachability boundary; otherwise NO-GO. Do not preemptively downgrade to a model of Kedro that only calls `group_records`.

## 5. C0 new domain and IO contracts (freeze before parallel implementation)

| ID | Active edit target | Deliverable | Focused tests |
| --- | --- | --- | --- |
| C0.1 | 20m | Strict frozen `FrozenSourceSelection` binding accepted workset, exact selection@1 and scoped entry evidence | No current projection fallback, duplicate releases not lost |
| C0.2 | 20m | `ExtractedComponents` and `ParsedParts` with known missing/unsupported/partial byte refs | Evidence digest and held reasoning, signed format vs filename mismatch |
| C0.3 | 20m | `NormalizedContent` and `ContentZones` schemas with immutable original offsets and limitations | Quote occurrence distinct from source attribution |
| C0.4 | 20m | `NativeRelations` with typed reply, ancestor, quote hypotheses and scope | Missing/cyclic/cross-scope edges do not auto-confirm |
| C0.5 | 20m | `FilterDisposition`, `GroupingDisposition`, `ScopedTransition`, `A2ResultManifest` | All matched rules and exact scoped changes |
| C0.6 | 25m | Choose `prepared@2` + `zones@1` or prove old output shape adequate; formal versioning/persistence schema plan | A3/A5 typed compatibility and historical saved result loading |
| C0.7 | 20m | Public `async def prepare` input/output, claim and terminal status contract | Bad plan rejected before IO; no event loop creation in API |
| C0.8 | 20m | Decide bounded partition and grouping context (not copied blindly from old A2) with versioned policy | No accidental merging across worksets/scopes |
| C0.9 | 25m | Re-read exact ReleaseEntry by saved ref for roles, contexts and full transitions without altering IntakeSelection | Missing/ambiguous equality-match held; global sequence gaps accepted |
| C0.10 | 25m | Freeze workset/partition/transition claims, plan proof, deterministic accepted result identity and outward status taxonomy | No generic INCOMPLETE for trust errors; no duplicate accepted ResultRef |
| C0.11 | 25m | New A2 v2 completion-proof/receipt and queryable held-at-A2 index while IntakeWorkset remains frozen | Every root prepared or explicit A2-held; terminal INCOMPLETE never endlessly pending |
| C0.12 | 25m | Versioned input-derived accepted result keys with output digest verify and resumable accepted stage lookup | Conflicting parser bytes fail closed under same key; attempts recorded separately |
| C0.13 | 20m | Typed SourceReferenceError subclasses for exact catalog/cursor anchors, preserving base interface | Trust errors BLOCKED; busy INCOMPLETE; source sequence gaps pass |
| C0.14 | 20m | Safe progress digest/read-only status for external launcher and explicit terminal replay policy | Prefect sees no-progress without reading private SQLite; terminal partial not automatically retried |

No C0 code is accepted unless requirements and acceptance cases have been explicitly frozen; no user-entered provider URL/path or A1 Graph context is ever allowed as dynamic Kedro Dataset factory input.

## 6. P1 main Kedro runtime, trusted IO and async execution

| ID | Active edit target | Deliverable | Focused tests |
| --- | --- | --- | --- |
| P1.1 | 20m | Programmatic per-workset/batch Pipeline builder with static/ordinal node/dataset names | Graph has extract/parse/normalize/zone/filter/group/save edges, no bypass |
| P1.2 | 20m | `ExactHandoffDataset` read-only selected input and `VerifiedEvidenceDataset` | Only saved refs, digest and root bounds; no current scan |
| P1.3 | 25m | `IsolatedParseDataset` trusted typed request and parser child dispatch | Sandbox limits, parser exception isolation and termination |
| P1.4 | 25m | `ClaimFencedSemanticDataset` storing exact StageResult and exposing durable reference | Claim-fenced per-write dependency; late save rejected |
| P1.5 | 20m | `ScopedTransitionDataset` with separate approved transition claim | Context-only and transition-only worksets accepted without fake bodies |
| P1.6 | 25m | `AsyncServiceBridge` off-loop `run_coroutine_threadsafe` facade, bounded sync waits | Wrong-thread hard failure; no nested event loop; no unbounded future |
| P1.7 | 25m | `SequentialRunner(is_async=False)` owned worker and completion handoff | Async outer loop heartbeat, no detached worker or coroutine |
| P1.8 | Experiment gate | CPU/memory/clock, cross-thread repeated cancel and timeout proof | Bounded worker drain within claim lease, no late publication |
| P1.9 | 20m | DataCatalog privacy/version/telemetry guards; no YAML, hooks or plugin discovery | Injected PII not in node/dataset names, logs, exception text |
| P1.10 | 20m | Stage-level durable progress / manifest adapters under Kedro dependency order | Node failure preserves accepted earlier refs but no false COMPLETE |

Kedro Nodes should be computation functions where possible; side-effectful IO should flow via closed Dataset adapters to trusted msgloom services. That makes Kedro the *orchestrator*, without promoting Kedro to the business transaction authority.

## 7. P2 parsing, normalization and zoning (parallel after contracts)

| ID | Active edit target | Lane | Tests |
| --- | --- | --- | --- |
| P2.1 | 20m | MIME/HTML primary+alternate bodies; preserved encodings/tables/links | Inline replies, quoted body, invalid MIME and source spans |
| P2.2 | 20m | XLSX/XLSM/XLSB/ODS extraction using verified parser capabilities | Sheet identity, numeric addresses, formulas/cached values, hidden-cell gaps |
| P2.3 | 20m | PDF page/text/layout extraction and limitations | Scanned/encrypted/partially extracted content not falsely complete |
| P2.4 | 20m | DOCX body/paragraph/table order and missing features | Exact block locations, unsupported embedded objects explicit |
| P2.5 | 25m | Semantic-safe text/metadata normalization | Reversible map to byte/block spans; no dropped decision-bearing content |
| P2.6 | 25m | Content zoning: contribution/quote-occurrence/forwarded/signature/footer/unknown | Duplicate Message-ID, inline quotes, absence/abstention and independent gold |
| P2.7 | 20m | Source-specific parser failure policies and held/partial classifications | Byte/digest change after selection; exhausted aggregate limit fatal |
| P2.8 | 20m | Resource profiling and observed bounds on Pi | Peak RSS, parser child count, wall time; no surprise IO |

Use existing isolated parser code only if its independent security interface qualifies under the new Dataset adapter; do not port the former `RecordSteps` control loop verbatim. Topic 01 and 02 synthetic research informs test cases but does not establish production accuracy.

## 8. P3 conservative native relationships, filtering, grouping

| ID | Active edit target | Deliverable | Tests |
| --- | --- | --- | --- |
| P3.1 | 20m | Exact source version/scope native relation decoder | Distinct reply parent, ancestry and quote-source; missing unknown |
| P3.2 | 20m | Conservative relationship confirmation and ambiguity closure | Same-subject and duplicate-ID do not merge |
| P3.3 | 20m | Typed deterministic filter rule evaluator preserving all matches | Include/exclude/guidance/conflict, timezone and source scope |
| P3.4 | 20m | Source-native thread/grouping policy with evidence/reason | Outlook conversation candidate only, Teams channel and explicit Teams chat reply |
| P3.5 | 20m | Contextual/source-scoped non-message item disposition | Calendar, To Do, OneDrive, Contacts not communication groups |
| P3.6 | 25m | Replay of changed policy/version and independent ordering | Version-stable equivalent input, changed config creates explicit new result |
| P3.7 | 20m | Transition/context refresh to A2 result format | Scoped absence/restore without global deletion |

Old A2 tests are regression *evidence*. Reuse tests that assert requirements; deliberately replace old-internal monkeypatch or fake-container tests with new public Kedro/Dataset integration tests.

## 9. E0 publish, A3 integration, operational invocation

| ID | Active edit target | Deliverable | Tests |
| --- | --- | --- | --- |
| E0.1 | 25m | Map intake, workset, per-partition and scoped transition claims into Kedro datasets | No borrowed intake token or ambiguous save authority |
| E0.2 | 25m | Source/parsed/zone/prepared/filter/group versioned staged outputs | Every later result depends on committed earlier refs |
| E0.3 | 25m | Terminal completeness / pending workset proof with partial refs | Failed/INCOMPLETE/CANCELLED never become COMPLETE |
| E0.4 | 25m | Restart and replay after crash at each dataset save boundary | No lost pending, no second authoritative checkpoint |
| E0.5 | 25m | A3 adapter for the accepted new output schema | Evidence and limitations consumed, no old private API |
| E0.6 | 25m | Manual prepare via existing Application/CLI command | Awaitable outside, correct terminal status and return code |
| E0.7 | 25m | `prepare-scheduled` using accepted intake with new Kedro A2 | Only released/selected inputs, cursor/pending as before |
| E0.8 | 25m | Full cross-stage E2E A1→Kedro A2→A3→A5 | No missing important source, stale output or inappropriate delivery |
| E0.9 | 20m | Architecture ownership and deprecation audit | No direct A1 import of new Kedro and no old A2 engine dispatch |
| E0.10 | 20m | Define no-payload external Prefect wakeup flow contract and safe invocation envelopes | Exact configured consumer/cursor; no A1 mutation or internal scheduler |
| E0.11 | 20m | Safely handle no-work, INCOMPLETE, BLOCKED and FAILED command outcomes | No blind retry, stable consumer_id and catalog pin, preserved pending |
| E0.12 | 20m | Cold-start eligibility inventory and explicit historical baseline only when approved | Unreleased raw evidence is not automatically promoted into A2 |
| E0.13 | 25m | Implement and integrate external Prefect/launcher wrapper that wakes `prepare-scheduled` after each finite A1 collection attempt and coalesces by stable consumer scope | Wake-up after committed A1 release starts Kedro; no Spider signal dependency |
| E0.14 | 25m | Crash-safe startup/periodic bounded catch-up, including A1 partial exits and lost wake-ups | Missed hint recovers from durable cursor; unchanged source is no-op |
| E0.15 | 25m | Pending-page backpressure, overlapping wake-ups and source/cutoff concurrency integration | No unbounded drain, no duplicate accepted result, later release processed on next invocation |

During development, new and old may coexist in *isolated test worktrees* for comparison. There is one production A2 path at any moment. Do not permanently operate both or automatically fall back to silently wrong legacy results.

## 10. T0 independent acceptance fixture streams (parallel with P1/P2)

| Lane | Scope | Approval proof |
| --- | --- | --- |
| T0-A | A1: 20 Spider coverage, 7 streams, 13 Task 15 scenarios and no release from profile | Match existing exact A1 names; verify read and handshake only |
| T0-B | Outlook MIME thread, inline quotes, duplicate IDs, moved/changed versions | Independently gold-authored zones, spans and uncertain parent |
| T0-C | Teams chat/channel with incomplete components and notification refresh | Distinct roots, supported replies, no historical fabrication |
| T0-D | Calendar/To Do/Contacts/OneDrive context, child components and scoped absence | Exact source scope, contextual not chat grouping |
| T0-E | Word/PDF/Excel malformed, huge, encrypted, HTML partial/source bytes missing | Parser ceilings and limitations |
| T0-F | Crash, cancellation, claims, late result, persistent saving failure | Real DataCatalog, no mock-only proof of ordering |
| T0-H | External A1 finite run → Kedro auto-activation, duplicate notification, lost post-commit wake-up, startup catch-up and partial-A1 failure | One durable cursor/workset chain; no event delivery correctness assumption |
| T0-G | Same-subject independent work, changed policy, partial reporting through A3/A5 | No false confirmed group or lost deadline |

Inputs must not contain actual user mail/provider credentials. An oracle generated by the new algorithm cannot validate itself; gold must be independently authored/reviewed.

## 11. V0 acceptance, CI and code cleanup

| Gate | Proof | Exit criterion |
| --- | --- | --- |
| V01 Kedro authority | Full main ETL topology and Dataset save/load exercise from frozen A1 input | Fails if extract/parse/normalize/zone/filter/group/save is bypassed |
| V02 A1 preserved | Original 20-Spider and all 13 Task 15 scenarios plus new-workset boundary checks | Frozen A1 runner/evidence not rewritten; new source SHA tested separately |
| V03 source integrity | Exact byte hashes, held/missing, version/scope and replay tests | No latest-current substitution or evidence invention |
| V04 parser + zoning | MIME/HTML, PDF, Excel, Word and verified spans/limitations | Independently checked content preservation and honest incomplete |
| V05 semantic | Relationship, filter and grouping adversarial tests | Correct uncertainty and no unauthorized semantic joining |
| V06 async lifecycle | Event-loop heartbeat, worker drain, CPU deadline, parser child cleanup | No hung runner or late publication, bounded lease margin |
| V07 durable result | Each schema/ClaimFencedSemanticDataset saved in declared order | No forged SUCCESS, partial durable refs accessible |
| V08 recovery | Interrupted intake/ETL/publish/replay and config change | No duplicate accepted effect, pending retained |
| V09 A3/A5 | Existing and new cross-stage test cases, new schema adapter | Reports retain actions, deadlines, missing attachments |
| V09b automatic activation | Prefect/launcher tests invoke finite A1 and automatically dispatch new Kedro A2, with missed/duplicate hints and catch-up | No A1 code change; only committed entries admitted; stable consumer and bounded retries |
| V10 portability | Python 3.12/3.13/3.14; Linux Pi aarch64; Linux x86-64; Mac smoke; Windows smoke only | No platform-dependent business tests; POSIX security limitation explicit |
| V11 static/dependency | Ruff, format, Pyright, pre-commit, locked dependency audit, wheel/sdist install | No hidden security exception or API break |
| V12 privacy/telemetry | Denied-network runtime, config-injection, subprocess/no-PII log tests | No unexpected network/telemetry/private body leakage |
| V13 performance | Identical A1 fixture cut measured old vs new on Pi and supported host | No material >10% wall regression unless absolute cost negligible; bounded RSS |
| V14 architecture | No bespoke A2 ETL sequencing duplicated outside Kedro; counted bridge/adapter/controller complexity | Kedro owns true stage graph, no permanent dual engine |
| V15 independent review | Full exact-SHA source, test mapping and original-base diff | Separate reviewer explicitly ACCEPT with no blocking issue |
| V16 automatic A1-to-A2 | AUTO-01–AUTO-26 in automatic-handoff design including missing wakeup, overlap, pending, empty ledger and cold start | No lost work, no duplicate durable admission, no untrusted automatic bootstrap |

Run focused tests while implementing; run the full three-Python/platform CI matrix at integration checkpoints, not for every 20-minute task. Evidence records exact SHA, interpreter/package versions, JUnit path/counts, no skips, source fixtures, failures, digests and independent review. Do not claim the old Task 15 28/28 validates Kedro.

## 12. Models, parallel management and stop conditions

A local agent manager may schedule the P1/P2/P3/T0 workstreams in parallel **only after frozen C0**; select the current officially available Claude Code Sonnet high for architecture/security, medium for bounded implementation tasks and an independent reviewer at high for final acceptance. Codex can be an independent secondary reviewer, never an uncontrolled concurrent writer. The manager writes exact branch/sha, files owned, source tests, stop conditions and model/effort in each worker handoff; do not silently spawn new ChatGPT or work sessions. One manager merges audited small PRs, one lockfile owner updates dependencies, and no agent edits accepted A1 code.

**Stop rather than improvise if:** an A1 handoff field is genuinely missing, Kedro full-ETL dataset bridge cannot remain bounded/nonblocking, a required claim cannot be fenced on every save, security Q0 is unresolved, the parser sandbox is weakened, semantic grouping creates false certainty, or an implementation requires permanent competing A2 engines. The manager records the defect with source evidence; redesign affected A2 stage without modifying A1 implicitly.

**Rollback:** the currently deployed old A2 remains operational until accepted cutover; after cutover remove obsolete A2 runtime only after reviewed regressions, preserve exact earlier git tag and archival tests/evidence. No destructive DB schema rollback or automatic A1 replay; new versioned results must be explicitly readable or archived.

## 13. Handoff checklist and authoritative documents

An implementation handoff starts by reading in order: this plan and its [ADR](../decisions/2026-10-23-a2-kedro-primary-etl.md); [architecture](2026-10-23-a2-kedro-native-design.md) and [automatic release handoff](2026-10-23-a1-release-to-kedro-auto-handoff.md); A1 source closeout, Task 15 report and governing handoff contract; actual `msgloom.sources` ReleaseSourceReader and intake/persistence schemas; docs/phase-1/design.md, docs/tech-stack.md and existing test corpus; AGENTS.md. The old 2026-09-29 Kedro migration plan and 2026-10-23 two-subgraph drafts are historical evidence, not implementation instructions.

Before any code: verify master and origin, no other agent is mutating target files, clean isolated worktrees and the exact locked Python/Scrapy/Kedro runtime. Record D4 verdict, Q0 disposition and branch/execution identifiers. Start with Q0 **read-only** security/API inspection; do not modify production code, lock or schemas until approved gates pass.

**Final deliverables:** a true Kedro-main A2 ETL engine, no bespoke parallel ETL control flow, correct A1 immutable handoff, accepted versioned outputs and A3 adapter, documented migration/deprecation, tests/benchmarks, and independent exact-SHA approval.
