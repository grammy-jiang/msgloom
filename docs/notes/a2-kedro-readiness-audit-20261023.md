# A2 Kedro-primary ETL readiness and historical-decision audit

**Date:** 2026-10-23 Australia/Sydney.
**Status:** D0 historic decision RECONCILED; D1 accepted handoff audited; D2/D3 design + plan rewritten; D4 R4 returned REVISE and R4 corrective proposal is documented, pending independent re-review.
**Current production master at audit:** 895fc40a0ec889bd96f620df8c62491787218217.
**A1 qualification:** 34057c6c9f85688fd2bd1868d90302ab5a61205f, exact-SHA Task 15 28/28 automatic gates and separate accepted independent review; not new A2 certification.
**Authority:** [Historical user decision ADR](../decisions/2026-10-23-a2-kedro-primary-etl.md), [architecture](../plans/2026-10-23-a2-kedro-native-design.md), [implementation plan](../plans/2026-10-23-a2-kedro-native-implementation-plan.md).
**Automatic A1 release consumption:** [A1 release-to-Kedro handoff](../plans/2026-10-23-a1-release-to-kedro-auto-handoff.md).

## 1. Why a new architecture reconciliation was necessary

The user explicitly clarified on 2026-10-23 that our earlier 2026-10-03/07 decision required Kedro to be the **main ETL framework**, a new A2 implementation, depreciation of the pre-existing inaccurate A2, and extensive A1 readiness work before A2 started. The clarification has been checked against prior chats (2026-10-03, 2026-10-04, 2026-10-07, 2026-10-13). It is binding. This is not a new design preference inferred from engineering convenience.

Earlier 2026-10-23 documents at commits 37f5886 and c1ac6cf **incorrectly limited Kedro to two pure filtering/grouping-related subgraphs** while letting a bespoke controller own most extraction, parsing and stage-result persistence sequencing. That repeats too much of the old A2 architecture and violates the historical decision even if its implementation were technically safe. Two read-only independent reviews returned REVISE for other important reasons. Those technical findings remain preserved, but architecture alignment must take precedence over patching the old drafts.

**Historical reports (do not relabel or treat as current approval):**

- [D4 independent review R1](a2-kedro-independent-review-r1-20261023.txt), SHA 37f5886, DECISION: REVISE, 9 P1 and 8 P2.
- [D4 independent review R2](a2-kedro-independent-review-r2-20261023.txt), SHA c1ac6cf, DECISION: REVISE, remaining 3 blockers and P2 follow-ups.
- [D4 independent review R3](a2-kedro-independent-review-r3-20261023.txt), SHA 3c0903b, DECISION: REVISE, 3 source-contract blockers; source-level role/outcome/claim remediation draft at [A1 Kedro R3 corrections](a1-kedro-handoff-r3-corrections-20261023.md).
- [D4 independent review R4](a2-kedro-independent-review-r4-20261023.txt), SHA 467ca23, DECISION: REVISE; four narrow field/identity/outcome/held/gate findings. All source-level proposals are preserved in the expanded [R3/R4 correction](a1-kedro-handoff-r3-corrections-20261023.md), with no A1 schema changes.
- Local 2026-09-29 branch program/kedro-a2-plan, c7dcb41, 648-line migration-only plan pinned Kedro 1.6.0; useful background but not an authoritative implementation specification for this fresh A2.

**New direction:** Kedro controls exact-A1-to-persisted-A2 **ETL** dependencies, including source extraction interfaces, parser invocation via trusted datasets, normalization, source-aware zones, relations, filter/group policies and ordered semantic-result saves. msgloom remains authoritative for A1, async I/O, parser sandbox, SQL transaction and claim fences. The new design is more ambitious than the superseded narrow-pure-DAG design; the dataset/async bridge is an explicit feasibility hard gate, not an assumed solved problem.

## 2. Accepted A1→A2 handoff: what must be preserved

| Accepted capability | Owner | New Kedro A2 must use |
| --- | --- | --- |
| Graph/Scrapy collection and raw evidence | A1 Spiders/Middleware/Pipelines/Extensions | Raw stored bytes and immutable capture only, never live Graph/Spider |
| Immutable facts and terminal semantic completeness | A1 catalog | Atomic ReleaseGroup / ReleaseEntry facts with exact authority |
| Stable source identity, version, scope, relationships and limitations | A1/ReleaseSourceReader | Pinned read-only ReleasedInput and materialized bytes; no current-state fallback |
| Exact frozen selection and bounded cutoff | PreparationIntakeService / selected reader | collected_selection@1, PreparationIntakeWorkset, catalog/source/stream/consumer anchor |
| Cursor, pending fairness, held entries and crash recovery | Accepted handoff + Phase1Persistence | Durable admission means selected, not parsed; reprocess only saved pending work |
| Context-only, component-only and scoped transitions | Accepted release/intake | Never invent new parent/body or global deletion; preserve scope/reason and independent context |
| Explicit historical baseline | A1 reader + handoff | Historical support only by caller-approved exact reference, not primary auto-work |
| Full public async A2 contract | Application | Kedro sync execution isolated behind bounded, awaited worker and trusted async bridge |

A1 closeout was designed specifically to give A2 a reliable, crash-safe source of new complete work. Its accepted Task 15 scope includes 20 installed Spiders, seven release streams, thirteen test scenarios. These numbers differ: one Spider (microsoft_profile) has no A2 release, and microsoft_teams_notification_reconcile affects Teams chat/channel but has no independent third Teams A2 intake stream.

### 2.1 Seven release streams with original 20 Spider producers

| Stream | Spiders / cause | Kedro A2 accepted input semantics |
| --- | --- | --- |
| outlook_mail | outlook_discover, outlook_folder_delta, outlook_delta, outlook_full | New message and Full capture, MIME/attachments, exact source/authority and folder-scoped removals |
| outlook_calendar | outlook_calendar_discover, outlook_calendar_window, outlook_calendar_delta, outlook_calendar_full | Fixed-window versioned observations, scoped absence and event metadata; contextual not chat group |
| todo | microsoft_todo_discover, microsoft_todo_sync | Authoritative task snapshot/presence, contextual facts |
| contacts | microsoft_contacts_discover, microsoft_contacts_sync, microsoft_contacts_delta | Contact/folder scope/generation, contextual facts |
| onedrive | microsoft_onedrive_discover, microsoft_onedrive_delta, microsoft_onedrive_content | Metadata/content association, exact bytes, 410 recovery and context; contextual grouping |
| teams_chat | microsoft_teams_chat_discover + notification reconcile effects | Chat message, hosted/component-only and refresh; same-chat supported native reply edge only |
| teams_channel | microsoft_teams_channel_discover + notification reconcile effects | Channel root/reply, hosted/component-only and scope-limited state changes |

microsoft_profile: 1 additional Spider, no release. Count = (4 + 4 + 2 + 3 + 3 + 1 + 1) + 1 profile + 1 notification reconcile = 20.

### 2.2 The actual ReleasedInput-to-workset shape

In the accepted code:

- ReleasedInput has reference, optional selection, components, contexts, transitions and facts.
- Intake admits *selection* and *components* as exact collected_selection@1 refs. It does not turn contexts into primary selection.
- A1 control_context facts and Teams component-only facts yield scoped context_refresh transitions. It preserves released.transitions as IntakeTransition rows.
- Held/unmaterializable exact entries remain tracked while later valid entries advance; record the held reason, do not manufacture content.
- The new Kedro Dataset adapter consumes the already frozen selections and passes transitions into a distinct, typed Kedro branch with a separately fenced authority. Kedro never writes A1 state or pretends existing contexts have a missing primary body.

The source truth here is docs/superpowers/specs/2026-10-03-a1-a2-handoff-contract-design.md, docs/notes/a1-a2-qualification-checklist.md and msgloom/sources/release_api.md, not a scan of provider projections.

### 2.3 Thirteen Task 15 invariant cases

1. New Mail acquisition, scheduled intake and preparation once.
2. Future-only baseline does not automatically process pre-ledger records.
3. Explicit historical baseline pins one starting immutable workset.
4. Retry after failed advanced acquisition does not duplicate release.
5. A losing older run cannot supersede newer authoritative data.
6. Large snapshot drains across bounded worksets without loss.
7. Crash after selection save and before cursor finalization safely retries.
8. Preparation failure after cursor commit retains rediscoverable pending work.
9. Restored catalog behind cursor is rejected by immutable anchor check.
10. Missing/corrupt evidence is held while later entries progress.
11. Mail folder and Calendar window removals retain their source scope.
12. Rule-deferred Mail authority waits for all required Full obligations.
13. Entries after the fixed cutoff wait until a later intake.

Historical Task 15 automated results prove these on original 34057c6. The new Kedro implementation must re-prove affected stage behavior, with an independently authored exact-new-source validation, and cannot relabel the prior 28/28 as its own success.

## 3. Legacy A2 inventory and deprecation strategy

As of base 895fc40, existing A2 code includes preparation_pipeline/handler.py (368 lines), record_steps.py (460), stage_steps.py (287), legacy scheduled/intake and historical baseline plus preparation/parsers, isolation/filtering/grouping, persistence/semantics and phase1_e2e tests.

**Keep as accepted external boundary:** exact ReleaseSourceReader, source release models, durable intake workset, cursor, pending/held/historical baseline, scoped transitions and existing claim/persistence authoritative APIs. Their location in preparation_pipeline does not make them obsolete.

**May reuse after independent component review:** format parsers, process isolation, deterministic predicate helpers, validation models and contracts. New Kedro pipeline owns their invocation and relationships; do not import old orchestration layers to gain them.

**Deprecate after successful replacement:** old PreparationHandler, RecordSteps/StageSteps sequencing, legacy-internal fake workflows, private test monkeypatch dependencies, and redundant A2 configuration glue. Do not demand exact internal stage-result ID or grouping algorithm parity simply because those values were emitted before; protect external identity/lineage/evidence invariants and introduce explicit new semantic versions if meaning changes.

**Retain historical evidence** and test cases that expose bugs. Old A2 is the regression corpus, not a source of architecture authority. Separate A3/A5 adapters may need adjustment to consume new A2 output shapes. Do not pretend `prepared@1` necessarily represents all new zone information.

## 4. Kedro main ETL framework feasibility

The architectural fit is technically plausible on public documentation: Kedro Pipeline/Runner own dependency sequencing and DataCatalog supports externally-backed datasets and stage output `load`/`save`. Kedro Core nodes are synchronous, while the application must be fully asynchronous; trust boundaries require an owned worker with bounded asynchronous dataset service facades. See current proposed design §5–6.

**Open mandatory proof:** from an isolated scratch A1-like workset, execute a programmatic Kedro graph through a trusted source dataset, fake sandbox parser dataset, semantic stage-save dataset and manifest dataset using the real async lifecycle. Fault-inject timeout/cancel, stale claim and dataset exception. Confirm nonblocking Application loop and no late publication. Fail closed if not possible; do not silently restrict Kedro back to a pure two-node helper.

Kedro 1.7.0 is a candidate, not a dependency admitted to production. Review exact source/wheel hash, Python 3.12–3.14 and aarch64, no-network/telemetry, and advisory conflict CVE-2026-3840 vs CVE-2026-35167 with dated OSV/GitHub/GitLab/Snyk records. This remains a Q0 gate, not a solved or waived issue. No new Kedro daemon, project, CLI, plugin loading or versioned dataset checkpoint.

## 5. Automatic operation readiness

The accepted A1 release ledger is the authoritative source of new work, but no deployed Prefect trigger was verified in the package or repository deployment modules. \`msgloom prepare-scheduled\` already accepts configured, trust-pinned source/stream/consumer targets, resolves pending before a finite new release cut and records explicit terminal results. Its present composition still invokes the **legacy** A2 pipeline. The corrected design proposes replacing only its A2 internal ETL execution with Kedro and adding a deployment-owned wakeup plus periodic reconciliation safety net.

A read-only metadata-only check of the local default acquisition catalog (var/msgloom.sqlite3) on 2026-10-23 found 178 raw_http_evidence records, 0 acquisition_release_groups, 0 acquisition_release_entries and 0 acquisition_release_entry_facts. That is **not** the formal Task 15 candidate catalog, and it is not evidence of A1 failure. A new Kedro A2 invoked against a zero-release ledger must return a no-work result. HistoricalBaselineService requires caller-approved exact versions with resolvable immutable evidence and may be unavailable for some pre-ledger sources. No private catalog IDs or raw historical records are added to these public planning files.

The [source-to-workset trace](a1-kedro-handoff-activation-20261023.md) records the existing native Mail acceptance (1 passed in 6.93s with the project venv). The [automatic-handoff plan](../plans/2026-10-23-a1-release-to-kedro-auto-handoff.md) records the exact invocation, trust pin, status, duplicates, backlog, no-release, crash and A1-concurrent-publication cases as future AUTO-01 to AUTO-26 gates.

## 6. D0–D4 and code admission status

| Gate | Current assessment |
| --- | --- |
| D0 historical user decision | Reconciled; binding ADR states Kedro-primary new A2 and legacy deprecation |
| D1 A1 output/handoff source coverage | Recovered from accepted code/qualification; 20-Spider/7-stream/13-case matrix |
| D2 new architecture | Rewritten with full ETL DAG and owned dataset/async bridge; pending independent review |
| D3 detailed implementation plan | Rewritten with Q0/C0/P1/P2/P3/E0/T0/V0 DAG and parallel ownership; pending review |
| D4 independent review of Kedro-primary/A1 automatic design | **REVISE on 467ca23** — R4 findings corrected in proposal, but a fresh independent exact-SHA review is still required |
| Q0 external Kedro security/runtime | **NOT RUN**; exact pinned source/code security and bridge PoC must pass before production |
| Implementation / dependency lock | **NOT STARTED**; master runtime unchanged |

New planning is an explicit response to the user's historical instruction, not a request to reopen A1. Scope remains design only. Static checks and new independent review are required before claiming design acceptance.

## 7. Read-only actions and references

- Reviewed October 3/7/13 historical decisions and previous msgloom conversations about Kedro main ETL, abandoning inaccurate old A2 and making A1 handoff complete first.
- Read and preserved accepted A1 Task 15 qualification, source reader/intake/workset/cursor and related code evidence.
- Reviewed current old A2 layout, parser/semantic/CLI tests, and the obsolete local Kedro migration plan.
- Independently examined Kedro official Pipeline, SequentialRunner and AbstractDataset documentation on 2026-10-23.
- Preserved unmodified earlier independent R1/R2 REVISE logs.
- Rewrote **documentation only** on independent planning worktree; no Kedro package installation, dependency change, A1 edits, old A2 deletion, launch of implementation agents or scheduler modifications in this assessment.

Kedro references: <https://docs.kedro.org/en/latest/build/run_a_pipeline/>, <https://docs.kedro.org/en/stable/api/io/kedro.io.AbstractDataset/>, <https://pypi.org/project/kedro/1.7.0/>.
