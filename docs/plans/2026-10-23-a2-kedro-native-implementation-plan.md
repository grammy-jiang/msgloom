# A2 Kedro-native implementation plan

**Status:** DESIGN-CANDIDATE implementation plan; no production implementation has started.
**Date:** 2026-10-23 (Australia/Sydney).
**Baseline:** 895fc40a0ec889bd96f620df8c62491787218217 (latest checked master/origin/master).
**Design authority:** 2026-10-23-a2-kedro-native-design.md.
**Evidence and review:** ../notes/a2-kedro-readiness-audit-20261023.md.

## 0. Scope control / definition of ready

This plan implements a **new** Kedro-native deterministic A2 execution path. It does not mechanically migrate legacy A2 control flow, add a second production orchestration system, change accepted A1 release/intake semantics, or start A3/A5 refactors. Reuse existing pure parsers/contracts and intake/persistence interfaces only where their independently audited behaviour matches the new design. The old A2 remains an offline oracle and rollback source until an independently accepted cutover. Pin that reference oracle to **895fc40a0ec889bd96f620df8c62491787218217**, including dependency lock and current fixture corpus. Do not compare against an unrecorded moving master.

**Before any production-code patch:** D0–D4 documentation must be accepted; owner has authorised implementation; latest GitHub master is captured; worktrees/active jobs are inventoried; Kedro dependency security and supported runtime gate is green. An unsuccessful gate ends the adoption path without changing the production default. D4 read-only design/security research may continue independently, but **any** manifest/lock/code edit (including Q0.5) requires an accepted revised plan and explicit owner implementation authorization. The first-round independent D4 review returned REVISE; see the readiness audit and the retained r1 report. No permission to implement is inferred from this plan.

Success is not "Kedro imports and one DAG runs". It is correct A2 lineage and all mandatory release/replay, security, lifecycle, performance, maintainability and downstream integration evidence.

## 1. Ownership and protected baseline

- A1 owner: message_ingest/, microsoft_graph/, immutable release and approved catalogue state. Do not edit in this plan without a separately reviewed, evidenced and owner-approved exception.
- Reused frozen boundaries: msgloom/sources/release_reader.py and reader contracts, preparation_pipeline/intake.py, historical_baseline.py, intake_models.py, the 13 Task 15 scenarios, claim-fenced msgloom/persistence and cross-stage result contracts. Preserve public behaviour.
- New A2 owner: an isolated namespace such as msgloom/preparation_kedro/ containing contracts.py, pipeline.py, nodes.py, executor.py, bridge.py and publication.py. It must implement one **controller-side parse planner** and two pure Kedro subgraphs (per-record prepare/filter; per-batch grouping), not another workset/cursor model. Every file must be below AGENTS.md's 500-line cap and total new/replacement orchestration must meet V13.
- Shared parser / pure domain owners: msgloom/preparation/isolation/, parsers/, records.py, filtering.py, grouping.py, grouping_graph.py, codecs. Only edit with a focused test and explicit ownership declaration; prefer adapters over duplicated logic.
- A2 composition: msgloom/cli/composition.py and scheduled wrapper integration only during final gated cutover; reuse existing PREPARE, prepare-scheduled and accepted preparation_intake_workset@1 contracts. There are three legacy claims to preserve: workset claim, per-PreparationPlan claim and separate prepared_transitions claim. No new public CLI or user-facing engine knob for initial alpha.
- A3/A5: unchanged business semantics and no new model/network processing. Their existing composition/e2e tests are mandatory downstream smoke.
- Old sequencing reference: preparation_pipeline/handler.py, record_steps.py, stage_steps.py, state module (_state.py). Retain unchanged through oracle tests and pre-cutover review; after cutover, remove only provably redundant orchestration in a separate reviewed PR.
- One manager owns pyproject.toml and uv.lock changes; no parallel worker rebases/rewrites the lock.
- Independent reviewer does not author the exact code/plan being reviewed.

Keep all unrelated untracked data untouched. The main Raspberry Pi repo has extensive untracked research outputs. Never use global git clean, reset --hard, git add -A, or destructive worktree pruning. Work in clean dedicated worktrees anchored at a recorded origin/master SHA; keep feature branches narrow and base them on the manager's accepted integration branch.

## 2. Milestone dependency DAG

    D0 scope + D1 A1/source audit + D2 design + D3 plan
                    |
                    v
                 D4 review
                    |
                    v
        Q0 security/version/lock qualification
                    |
                    v
             C0 contracts/adapters
                 /          \
                v            v
        P0 pure Kedro     F0 fixture/oracle
                 \          /
                  v        v
                  E0 claim/publish integration
                    |
                    v
             I0 manual + scheduled cutover
                    |
                    v
              V0 full acceptance
                    |
                    v
         O0 clean up + documentation + release

No orchestration-node implementation runs in parallel with an unresolved core security/runtime gate. Independent F0 test extraction can run concurrently with P0 **after** C0 input/output contracts freeze. Parser fixture cases can be split by file type into separate worktrees; no parser worker edits the shared lock.

## 3. D0–D4 planning / audit (this phase)

| ID | Time target | Deliverable | Evidence / acceptance |
| --- | --- | --- | --- |
| D0.1 | 15m | Reconcile current user decision versus 2026-09-29 migration plan | New design explicitly supersedes runtime dual-engine migration |
| D0.2 | 15m | Fix A1 handoff authority and source SHA; freeze change scope | 34057c6 formal A1 qualification versus 895fc40 post-maintenance master distinguished |
| D1.1 | 20m | Inventory all 20 Scrapy Spiders/streams and read-only release API | Source-to-ReleaseEntry/ReleasedInput matrix; profile has no release |
| D1.2 | 20m | Inspect immutable selection, component-only, context-only and transitions contracts | Exact types, limitations, held and scope behaviours mapped |
| D1.3 | 20m | Inspect parser/filter/group types and existing tests | Existing oracle owner and semantic differences recorded |
| D1.4 | 20m | Inspect formal Task 15 test evidence and 13 scenarios | No false claim of certification for future Kedro code |
| D2.1 | 25m | New Kedro ownership and immutable execution types | No claims, I/O, parser process, A1 mutations inside DAG |
| D2.2 | 25m | Kedro runtime decision and telemetry/security constraints | Static dataset names, programmatic catalog, sequential runner |
| D2.3 | 25m | Source/semantic/gap and replay/lifecycle truth tables | Incomplete vs failed vs held; structural grouping only |
| D3.1 | 25m | Decompose implementation into bounded PRs and tests | Every changed file has one owner, no shared lock rewrites |
| D3.2 | 20m | Define quality/performance/maintainability gates | Concrete commands, invariants and stop/go thresholds |
| D4.1 | 20m | Static document cross-link and consistency checks | All linked repo paths exist; no contradictory A1 owner |
| D4.2 | 25m | Independent adversarial design review | Verdict with blockers, evidence and exact reviewed SHA |
| D4.3 | 15m | Final readiness record | Explicit ACCEPTED or BLOCKED and next work item |

D0–D4 do **not** add Kedro to the package or alter user-facing behaviour.

## 4. Q0 dependency/security/runtime qualification (hard stop)

| ID | Time target | Work | Mandatory proof |
| --- | --- | --- | --- |
| Q0.1 | 20m | Freeze installed runtime, Scrapy version, 3.12/3.13/3.14 interpreters, Pi ARM64, CI baseline | Versions and commit match manifest; no unsupported "works on Windows" claim |
| Q0.2 | 25m active review | Download wheel into isolated scratch directory; verify PyPI SHA-256 and wheel metadata without executing sdist build scripts; inspect extracted source with isolated Python; compare 1.7.0 public APIs against 1.6 plan | No untrusted sdist code executed; Python -I used for source inspect; catalog/copy mode/out read validated |
| Q0.3 | 25m investigation slice | Reconcile CVE-2026-3840 and CVE-2026-35167 against exact version; record OSV, GitHub, GitLab and Snyk advisory status with date | Reviewer-checked source-level reachability and written owner risk disposition; no automatic ignore |
| Q0.4 | 20m review/test design | Specify production guard against versioned datasets, DataCatalog.from_config, Kedro load_obj, dynamic hooks, plugins, untrusted catalog and CLI | Architecture-test cases defined; telemetry/network/logging/redaction requirements, no dynamic classes |
| Q0.5 | 25m active change | **Only after Q0.3 + Q0.4 ACCEPT and owner authorization:** one owner edits pyproject/uv.lock in isolated dependency PR; list every added transitive package and hash | 3.12/3.13/3.14 OSV audits and separate CVE applicability record; no silent vulnerability-ignore |
| Q0.6 | 25m active qualification setup | Only after Q0.5: independently install locked wheels into clean isolated environments, verify ARM64 and 3.14 wheel availability | Offline installed-wheel/metadata/telemetry/sandbox check; matrix runs may exceed the 25m active-change target |

Version decision: 1.7.0 is a **candidate**, not pre-approved. The older plan fixed 1.6.0 before 1.7.0 existed. Snyk currently flags all Kedro versions for CVE-2026-3840, while GitLab/GitHub link a very similar issue to an upstream fix in 1.3.0 under CVE-2026-35167. If overlap cannot be resolved conclusively, leave production unchanged and request an explicit security acceptance decision; do not silently add an audit ignore. No kedro-datasets required.

The Q0 security authority is the repository owner. Require source-level documented applicability, OSV/GitHub/GitLab/Snyk status and explicit approval tied to candidate SHA. If an advisory remains unresolved, no implicit CI green override; exceptions require separately approved policy plus expiry, not an agent-created ignore. Q0.3 and Q0.4 security/read-only conditions are strict prerequisites for Q0.5. Check the installed 1.7.0 build's true DataCatalog/MemoryDataset copy semantics and all new transitive libraries.

If Q0 fails, close this as a **rejected adoption** with documented evidence. Do not substitute custom runners or a vendored Kedro fork without a newly approved design.

## 5. C0 frozen contracts and compatibility seam

| ID | Time target | Change | Focused tests |
| --- | --- | --- | --- |
| C0.1 | 20m | Define strict immutable per-record A2RecordExecutionInput and reuse PreparationIntakeWorkset for exact source cut | Unknown fields/forged versions fail; no live resources |
| C0.2 | 20m | Define RecordTransformOutput and GroupingInput/GroupTransformOutput; no extra RelationshipGraph schema | Source/limits/lineage preserved; deterministic schema |
| C0.3 | 25m | Map existing workset.selection_refs and recorded source versions to per-record input envelope | All ReleasedInput shapes and 7 source categories |
| C0.4 | 20m | Specify parse planning for primary/alternate bodies, derived metadata JSON, attachment byte references and exact parser binding | No content-derived module/path dispatch |
| C0.5 | 20m | Define pass-through transition/context-only mapping outside Kedro; reuse existing prepare_transitions claim | No fabricated parent, body, or global absence |
| C0.6 | 20m | Prove A3/A5 input accepts equivalent prepared semantic versions; define no duplicate downstream change on engine-only cutover | Identical content/policy uses same config/code version and accepted semantic IDs |

C0 is a freeze barrier: parallel pure-DAG and oracle workers consume the same contracts. Do not permit a worker to rename shared schemas unilaterally.

## 6. P0 Kedro pure-dataflow implementation

| ID | Time target | Change | Focused tests |
| --- | --- | --- | --- |
| P0.1 | 20m | Define **two** programmatic Kedro pure DAGs: per-record assemble->filter, per-unique-batch validate->group | Meaningful dependency edges, no extra graph schema or duplicate/orphan datasets |
| P0.2 | 20m | Implement pure assemble_prepared_record on already parsed exact input | Deterministic prepared@1 candidate with source spans and limitations |
| P0.3 | 20m | Reuse proven pure apply_filters in Kedro node with explicit FilterConfig input | All matches, conflicts, guidance, excluded replay unchanged |
| P0.4 | 20m | Implement scope/duplication validation of GroupingInput (only one planned batch) | Missing/cross-scope parents uncertain; repeat selected sources split into new batch |
| P0.5 | 20m | Reuse reviewed group_records pure algorithm in batch Kedro node | Candidate Outlook only; supported Teams chat reply may confirm; contextual separate |
| P0.6 | 20m | Validate RecordTransformOutput + GroupTransformOutput; transitions excluded from DAG | No fake durable refs, ClaimToken or duplicate versioned dataset |
| P0.7 | 25m | Implement SequentialRunner(is_async=False), static programmatic catalog, MemoryDataset(copy_mode="assign") for frozen-only objects | No event-loop block, mutable alias leak, deep copy blowup, hooks/plugins/telemetry |
| P0.8 | 25m | Implement bounded cooperative stop checks before/between nodes, monotonic budget preflight and measured node drain margin | CPU-bound timeout before/during node; never late publish; no unbounded thread |
| P0.9 | 20m | Enforce node/catalog allowlist at runtime; reject versioned/from_config/load_obj paths; capture failure logs with private payload fixtures | CI executable guard, no leaked content/exceptions, no Kedro CLI |

Each node operates only on captured immutable inputs and returns pure values. Do not invoke parser subprocess or write SQLite from nodes. Keep node granularity coarse; multiple microtasks need not mean multiple framework nodes.

## 7. F0 fixture and semantic oracle (can parallelize after C0)

| ID | Time target | Lane | Proof |
| --- | --- | --- | --- |
| F0.1 | 20m | Fixture registry and exact selected input snapshots | Golden snapshots independent of new pipeline output |
| F0.2 | 25m | Outlook Mail including duplicates, moves and old-version replay | Exact source mapping and ambiguous Message-ID |
| F0.3 | 20m | Calendar/To Do/OneDrive/Contacts contextual and scoped facts | No automatic communication group or global removal |
| F0.4 | 25m | Teams channel rooted replies and independent Teams chats **with explicit supported reply links** | Same-scope confirmed only for resolvable native links; fixture-only acceptance |
| F0.5 | 25m | MIME/HTML and alternative body, quoted/inline text spans | Preserve order, reference/source distinction, no false quote source |
| F0.6 | 25m | Excel, PDF and Word including partial/malformed/unavailable files | Retain cells, pages, tables, blocks, omissions |
| F0.7 | 20m | Filters and group ambiguity/fairness | Conflicts held, candidate-only relations remain uncertain |
| F0.8 | 20m | Canonical oracle comparison utility pinned to 895fc40 | Same meaning-bearing values and prepared semantic versions when code/config equal; ResultRefs may differ |
| F0.9 | 20m | Replay, changed policy, unstable/duplicate source identities | Semantic version equality/inequality by meaning-bearing change |

Use existing tests/preparation_pipeline/, tests/preparation_semantics/, tests/test_native_parser_integration.py, tests/phase1_e2e/ and Task 15 13-scenario fixtures as sources of truth. Do not "fix" an old test to make Kedro green. When exact bytes differ, the reviewer must decide whether the legacy result was incorrect under the governing design; record that as an explicit policy change, never hide it in the comparison.

F0 can be distributed across independent agents/worktrees, each owning only new tests/fixtures under a unique new namespace; a manager owns fixture and registry integration.

## 8. E0 effectful controller and durable publication (after P0 + F0)

| ID | Time target | Change | Proof |
| --- | --- | --- | --- |
| E0.1 | 25m | Trusted operation admission, finite plan, exact dependency preflight | Unknown caller values fail closed |
| E0.2 | 25m | Preserve scheduled workset claim and separate per-plan claim (split at max_records/repeated VersionRef) | Duplicate versions never co-group; exact selection saved before parsing |
| E0.3 | 25m | Controller parse planner with body/alternates/metadata-derived JSON/attachments; parser child lifecycle | Per/aggregate byte/output budgets, distinct limitations, cleanup and source mapping |
| E0.4 | 25m | Per-record pure Kedro invoke with finite drain bound, then one per-batch group invoke | Deadline preflight, no late publication, exact groups only within batch |
| E0.5 | 25m | Immediately revalidate and publish each prepared@1 after that record's DAG returns | Exact collected_selection/derived deps, per-write claim fencing; earlier refs survive later failure |
| E0.6 | 25m | Immediately publish per-record filter_result@1; after batch completion publish group_result@1 | Exact ordered member prepared/filter refs; no unfinished group on timeout |
| E0.7 | 25m | Retain separate existing prepared_transitions@1 claim and prepare_transitions publisher | Workset transition refs retained; no fabricated deletion body/primary |
| E0.8 | 25m | Complete operation workset receipt and terminal status | Only all accepted refs allow COMPLETE; incomplete remains visible |
| E0.9 | 25m | Fault injection: claim loss, post-parse failure, per-record timeout, group exception, cancellation during CPU-bound node | Earlier saved refs retained; no stale or late result; no false COMPLETE |
| E0.10 | 20m | Closed-loop replay and restart without A1 current projections | Exact saved selection; delayed retries supported |

Mutating the stored workset/cursor or durable schema is **not** needed by default. A proposed exception requires separate migration proof, old/new reader compatibility and a dedicated independent review. The outer controller may be new; the existing intake semantics are not.

## 9. I0 gated integration, cutover and cleanup

| ID | Time target | Change | Proof |
| --- | --- | --- | --- |
| I0.1 | 20m | Integrate new controller behind internal development-only composition seam | Default production old behaviour, no public A2_ENGINE contract |
| I0.2 | 25m | Manual prepare complete/incomplete/replay through Application/CLI | Same exposed outputs, return codes and no model calls |
| I0.3 | 25m | Integrate new per-plan controller under unchanged prepare-scheduled intake/transition flow | Task 15 13 scenarios rerun without editing frozen runner, plus new-producer 1/8/10/11/13 cases |
| I0.4 | 25m | A3 Triage / A5 Reporting acceptance smoke with saved A2 results | Same source lineage, no report omissions |
| I0.5 | 20m | Confirm no unrelated consumer import or hidden legacy dispatch | Composition/architecture import guard tests |
| I0.6 | 25m | Independently approve cutover, flip default once | Exact SHA, no unchecked runtime fallback, rollback known |
| I0.7 | 25m | Remove only redundant legacy orchestration after stability evidence | No two long-lived producers, sources/intake untouched |
| I0.8 | 20m | Update architecture, component layout and tech-stack references | One current authority, no false Windows/live Teams claim |

Do not implement a permanent A2_ENGINE CLI/operator knob merely because the old migration plan proposed it. Use temporary test composition only; legacy rollback remains as a prior commit/tag, not an indefinitely maintained second subsystem.

## 10. V0 verification matrix and no-regression requirements

| Gate | Command / mechanism | Pass condition |
| --- | --- | --- |
| V01 pure DAG | Focused new tests under tests/preparation_kedro/ | Node topology and deterministic canonical output pass |
| V02 parser | tests/test_native_parser_integration.py and tests/preparation_pipeline/test_documents.py | MIME/HTML, Excel, PDF, Word and limitations retain mappings |
| V03 semantic | tests/preparation_semantics/, tests/preparation_pipeline/test_contracts.py, test_r2_regressions.py and new oracle comparisons | Exact policy, group scope, ambiguity, semantic identity parity |
| V04 replay/id | tests/preparation_pipeline/test_stable_identity.py, test_evidence_loss.py, test_lifecycle.py, test_timeout_boundary_controls.py and test_completion_bounds.py | Stable identity, partial timeout refs, bounded CPU drain/claim-lost |
| V05 scheduled | tests/preparation_pipeline/test_scheduled_recovery.py, test_scheduled_transitions.py, test_scheduled_fairness.py, test_historical_baseline_calendar.py and test_teams_historical_baseline_scope.py | No lost pending, exact transition/context, fair progression |
| V06 intake | Run the accepted Task 15 28-gate **runner unchanged** as separate regression evidence when required; new A2-specific tests rerun affected scenarios 1/8/10/11/13 | Preserve 20-Spider scope and all 13 scenarios; never mutate formal evidence/runner |
| V07 cross-stage | tests/phase1_e2e/, tests/application_cli/ | A2 result chain accepted by A3/A5 and finite CLI |
| V08 native security | Existing Linux delegated cgroup-v2 gate plus parser isolation tests | No weakened process isolation or late worker effects |
| V09 compatibility | tox Python 3.12, 3.13, 3.14 and opted FastMCP4 compatibility | No skips/unavailable interpreter accepted; Windows *smoke only* |
| V10 package/static | uv lock and audit, installed wheel/sdist/offline, Ruff, Pyright, pre-commit | 0 unresolved errors, published wheel imports and CLI safe |
| V11 telemetry/security | Network-deny import, exact-pinned Kedro source/CVE review, OSV/GitHub/GitLab/Snyk status record, architecture guards, failure-log redaction | No telemetry, untrusted version path, PII log leak or concealed high severity |
| V12 empirical | Identical offline source cut on Pi aarch64 and Linux x86_64 | No meaningful >10% wall regression or unbounded RSS |
| V13 complexity | At base SHA 895fc40: 1,115 old LOC and 89 AST branch nodes; count every new/replaced controller/parse/publish/DAG/bridge/type file and changed integration line | At most 1,000 LOC and 80 branches; no duplicate intake or custom runner; otherwise NO-GO |
| V14 independent | Reviewer reads exact SHA and all test evidence and source diff | ACCEPT, no unresolved blocking findings |

These are **future** acceptance requirements, not gates already passed for the new Kedro implementation. The formally accepted Task 15 SHA (34057c6) is baseline/oracle evidence; do not relabel that acceptance onto a future candidate or silently weaken its 28-gate runner. The latest maintenance CI on 895fc40 does not by itself qualify Kedro, which is currently absent.

Normal development: affected unit/integration tests first, then phase-level checks at merge checkpoints. Avoid repeatedly running the full 3-interpreter suite for every small fix. Before release, run every required version/platform gate and an independent exact-SHA review; record fail/blocked/skip honestly.

## 11. Parallel task and review policy

Recommended bounded workstreams after security gate:

- **Manager / dependency owner:** Q0, contracts freeze, branches/lock, final integration and acceptance (serial).
- **Pure Kedro lane:** P0.2–P0.6 with programmatic DAG package ownership; no shared schema edits.
- **Fixture lane A:** F0.2–F0.4 source shapes, relations and contextual facts.
- **Fixture lane B:** F0.5–F0.6 parser and source mappings.
- **Fixture lane C:** F0.7–F0.9 identity/replay oracle.
- **Controller / durability lane:** E0 starts only after P0 and F0; one writer owns controller and publication.
- **Independent QA lane:** review updated design, exact code diff/fixtures, lifecycle, CVE and measured complexity; no code author reviews their own work as independent.

Prefer small **authoring/review changes** targeted at <=30 minutes of active editing. Matrix tests, dependency resolution, security audits, wheels and independent reviews can take longer; these are separate asynchronous-safe, resumable operations with isolated logs and recorded results. Never weaken a test to meet a nominal time budget. Use focused tests first; full matrix at gate boundaries. Each worker should be given exact file ownership and prohibition on changing other branches or the shared lock. Rebase a task branch only on the manager's accepted integration head. Merge once per reviewed wave to avoid one full CI matrix per tiny task; keep any failing wave unmerged.

No anonymous subagents may modify source without the owner's explicit workflow selection. Record when a local Claude Code/Codex agent is assigned, model/effort, task branch, exact repository, assigned tests and stopping conditions in the handoff note. Do not hardcode outdated CLI model IDs.

## 12. Release criteria, stop conditions and rollback

- **GO for P0 implementation:** D4 independent approval, Q0 candidate dependency runtime/security tests green and frozen C0 public contracts.
- **GO for cutover:** V01–V11 and V14 pass on same exact SHA, no pending A1-change request, integration can be rolled back without data repair.
- **GO for final release:** all V01–V14, including performance and complexity, pass; old sequencing removal proved safe and required docs updated; no unexplained regression or masked dependency warning.
- **NO-GO:** compromised source exactness, dependence on live Scrapy state, uncertain scope promoted to global deletion, custom async Kedro runner, claim state hidden inside Kedro, process cleanup failure, semantic divergence without approved decision, insecure Kedro version, data-leaking logging, or adapters that make architecture materially more complex.

Rollback uses a pre-cutover commit/tag and existing Phase 1 schema; newly published results remain append-only, not rewritten. Avoid any schema or cursor changes whose rollback requires data deletion. If Kedro fails, stop using it and retain current implementation as a supported production route; publish an explicit rejection memo rather than force adoption for its own sake.

## 13. Source references and handoff checklist

Read these in order:

1. docs/plans/2026-10-23-a2-kedro-native-design.md and docs/notes/a2-kedro-readiness-audit-20261023.md.
2. docs/superpowers/specs/2026-10-03-a1-a2-handoff-contract-design.md and docs/notes/task15-final-qualification-20261016.md.
3. msgloom/sources/release_api.md, docs/notes/preparation-pipeline-api.md and docs/notes/preparation-semantics.md.
4. docs/phase-1/design.md, docs/phase-1/architecture.md, docs/tech-stack.md, docs/plans/msgloom-next-implementation-program.md section 14 and 23.
5. AGENTS.md, pyproject.toml, uv.lock, composition/source/intake/persistence code and named tests.

Implementation handoff MUST state: verified HEAD, branch/worktree, latest code-owner edits and untracked files, currently running jobs, exact task IDs, files owned, known security disposition, diff and passing test IDs, deterministic fixtures and report location, next gate and rollback SHA. On a stop or error, preserve partial evidence; do not claim ongoing background work unless a real durable tool job exists.

The first code change after D4 should be Q0 security/runtime investigation and lock qualification **only**. No production A2 code is authorised by this planning PR.
