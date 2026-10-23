# A2 Kedro-native readiness audit (D0–D4)

**Audit date:** 2026-10-23 Australia/Sydney.
**Mode:** read-only investigation plus planning-document creation. No A2 runtime change or dependency installation.
**Repository:** grammy-jiang/msgloom.
**Main snapshot:** master == origin/master == GitHub at 895fc40a0ec889bd96f620df8c62491787218217; GitHub PR #67 merged and its 10-job CI succeeded.
**Formal A1 evidence:** exact candidate 34057c6c9f85688fd2bd1868d90302ab5a61205f, 28/28 gates and independent ACCEPT; this qualification does not cover future Kedro changes.
**Planning branch:** docs/a2-kedro-native-design-20261023 in a separate Raspberry Pi worktree; master and unrelated untracked research left untouched.

## Executive disposition

A1 has the accepted source and durable release/intake contract needed for new A2 implementation. The repository has functioning **legacy** A2, source-reader, isolated parsers, filter/group semantics, persistence and full Phase 1 cross-stage tests. The user-approved direction is **new Kedro-native A2 execution**, not a migration-wrapper and not A1 rework. The local 2026-09-29 Kedro integration plan is historically valuable but obsolete as execution authority.

D0–D3 are documented in:

- docs/plans/2026-10-23-a2-kedro-native-design.md
- docs/plans/2026-10-23-a2-kedro-native-implementation-plan.md

D4 independent review R1 of exact 37f588676404a92b5d4e521a25d513070df42efc by official Claude Code Sonnet (read-only) returned **DECISION: REVISE**, with nine P1 blocking design defects and eight P2 improvements. The complete original finding report is retained at docs/notes/a2-kedro-independent-review-r1-20261023.txt; it must not be retrospectively relabeled. This plan has been revised to address those findings. A separate independent R2 review of the new exact SHA remains required before any code task may begin. This planning audit does not assert that Kedro runtime is installed, that an official Kedro security advisory is resolved, or that a new A2 has already passed production tests.

## D0. Decision reconciliation / authority

| Source | Role | Disposition |
| --- | --- | --- |
| docs/notes/a1-closeout.md | A1 source closeout | ACCEPTED upstream boundary, not reopened |
| docs/superpowers/specs/2026-10-03-a1-a2-handoff-contract-design.md | immutable release/intake authority | ACCEPTED exact-SHA interface contract |
| docs/notes/task15-final-qualification-20261016.md | formal 28-gate evidence + independent review | ACCEPTED only for 34057c6 |
| docs/phase-1/design.md, docs/tech-stack.md | Phase 1 behaviour/parser rules | Functional requirements; draft versions are not current code inventory |
| docs/notes/preparation-pipeline-api.md | legacy implementation API | Regression and integration oracle; not new architecture |
| docs/notes/preparation-semantics.md | legacy deterministic semantic behaviour | Reusable validated pure contract, subject to external invariants |
| docs/plans/msgloom-next-implementation-program.md §14, §23 | older A2 work plan / P2 gate | Requirements seed; was authored before A1 closeout and updated schemas |
| program/kedro-a2-plan at c7dcb41 | historical 648-line Kedro 1.6 migration plan | NON-AUTHORITATIVE for new greenfield A2; retains useful framework cautions |
| docs/plans/2026-10-23-a2-kedro-native-design.md | proposed new A2 authority | Must pass D4 independent review |
| docs/plans/2026-10-23-a2-kedro-native-implementation-plan.md | proposed implementation DAG | Must pass D4 independent review |

## D1. A1 source/release coverage inventory

The following 20-Spider set is the exact reviewed Task 15 scope; it is not a statement that the Spider always produces a new release or that Teams has live enterprise acceptance. Table rows come from docs/notes/a1-a2-qualification-checklist.md and the accepted governing handoff design.

| Spider | A1 completion / A2 contract | A2 implications |
| --- | --- | --- |
| microsoft_profile | No release | Profile is explicitly NOT an incremental A2 intake stream |
| microsoft_todo_discover | Complete additive traversal | Inventory/control context; do not assume task deletion |
| microsoft_todo_sync | Winning authoritative snapshot + scoped presence | Contextual task, scoped absence; no communication group |
| microsoft_contacts_discover | Complete recursive traversal | Inventory/supporting scope, not fabricated person-topic relation |
| microsoft_contacts_sync | Winning snapshot + generation | Contextual contact; exact version and scoped changes |
| microsoft_contacts_delta | Winning custom-folder delta | Scoped folder membership; no global contact deletion |
| microsoft_onedrive_discover | Drive/root pagination | Inventory contexts and evidence provenance |
| microsoft_onedrive_delta | Checkpoint with normal/410 reset | New version/reset facts; no current-state fallback |
| microsoft_onedrive_content | Version-linked content capture | Exact metadata association and parser saved-byte evidence |
| outlook_discover | Full/truncated discovery | Honest truncation limitation; folder inventory/context |
| outlook_folder_delta | Atomic folder checkpoint | Scoped folder transitions, no global message absence |
| outlook_delta | Immediate/deferred authority based on rules | Message primary, components, obligations and exact release |
| outlook_full | Profile obligations, partial multi-target outcomes | Attachments/MIME/full metadata; preserve partial failures |
| outlook_calendar_discover | Complete calendar inventory | Calendar contexts; no fabricated communication grouping |
| outlook_calendar_window | Exact fixed window with resume | Stable selected observation/window scope |
| outlook_calendar_delta | Winning window promotion, 410 baseline | Window-scoped removals, exact immutable selection |
| outlook_calendar_full | Per-event enrichment profile | Exact event/attachments; partial outcomes distinguished |
| microsoft_teams_chat_discover | Native fixture chat crawl/release/intake | Chat scope, hosted components, independently saved facts |
| microsoft_teams_channel_discover | Native fixture root/reply crawl/release/intake | Same-channel native parent only; missing root uncertain |
| microsoft_teams_notification_reconcile | Readback and scoped state changes | No separate A2 intake stream; reconcile Teams chat/channel |

A1 reader returns ReleasedInput with exact reference, optional selection, components, contexts, transitions and facts. None may be dropped. There are *seven* current PreparedSourceType categories: Outlook email, Outlook calendar, Teams channel message, Teams chat message, To Do, OneDrive and Contact. Input category counts must not be conflated with the 20-Spider count or release stream count.

### Seven A1 release streams mapped into A2

This crosswalk is based on AcquisitionStream (message_ingest/acquisition/handoff.py), ReleaseInput fields, the actual intake.py extraction rule and the existing seven PreparedSourceType members; it is **not** a second persisted schema.

| A1 stream | Spider sources | ReleasedInput possibilities | Accepted workset | A2 disposition |
| --- | --- | --- | --- | --- |
| outlook_mail | outlook_discover, outlook_folder_delta, outlook_delta, outlook_full | Mail primary/Full profile components, inventory context, scoped folder membership | selection_refs (primary + components), transitions/held | outlook_email prepared/filter/group within one exact plan batch; folder transitions bypass Kedro |
| outlook_calendar | outlook_calendar_discover, outlook_calendar_window, outlook_calendar_delta, outlook_calendar_full | Window/event versions, inventory, scoped window authority | selection_refs, context_refresh/transitions/held | outlook_calendar contextual one-member None; window removals scoped |
| todo | microsoft_todo_discover, microsoft_todo_sync | Resource snapshot, control inventory, task presence | selection_refs, transitions/held | todo contextual one-member None |
| contacts | microsoft_contacts_discover, microsoft_contacts_sync, microsoft_contacts_delta | Person/folder inventory, generation, membership observation | selection_refs, transitions/held | contact contextual one-member None |
| onedrive | microsoft_onedrive_discover, microsoft_onedrive_delta, microsoft_onedrive_content | Metadata primary, exact version-linked content component, 410/control context | selection_refs, transitions/held | onedrive contextual one-member None, exact metadata/content provenance |
| teams_chat | microsoft_teams_chat_discover; microsoft_teams_notification_reconcile contributes scoped effects | Chat message primary, component-only observation, side context, presence | selection_refs when materialized; parent context_refresh transitions when component-only | teams_chat_message; explicit same-scope chat reply may confirm, membership alone cannot |
| teams_channel | microsoft_teams_channel_discover; microsoft_teams_notification_reconcile contributes scoped effects | Channel message root/reply primary, component-only observation, scoped state | selection_refs when materialized; parent context_refresh transitions when component-only | teams_channel_message; exact same-channel root/reply may confirm |

microsoft_profile has no release and therefore belongs to **no** A2 stream.

The actual intake maps released.selection and released.components to exact collected_selection@1 refs; it does **not** admit released.contexts as a source selection. Only control_context facts become context_refresh transitions; Teams component-only facts can also produce parent context_refresh. All released.transitions are preserved in workset.transitions. Invalid evidence becomes workset.held. The new Kedro pure DAG receives **only** already captured selected records from a duplicate-free PreparationPlan, never the raw entire ReleasedInput or workset.transitions. No extra A2SourceCut model is authorised.

Release facts alone do not prove released completion. Cursor advancement is after durable workset admission, not parsing success. Supporting context is explicitly non-primary. Component-only entries may have immutable components without a readable parent, and transition-only releases have scoped authority facts without bytes; both must have defined new A2 handling, not be discarded or converted to fake records. The accepted scheduled intake has restored-catalog anchoring, pending-work rotation and held dispositions.

**13 inherited Task 15 scenarios:** new Mail once; future-only bootstrap; explicit historical baseline; equivalent retry; delayed losing run; large multi-page drain; crash after selection save; failure after cursor commit with rediscoverable pending; catalog-restore detection; held missing/corrupt evidence with later progress; scoped Mail/Calendar removals; rule-deferred Full obligations; cutoff isolation. All remain required A1/no-regression gates at A2 cutover.

**A1 evidence references:**

- docs/notes/a1-a2-qualification-checklist.md (20-Spider and 13-scenario matrix)
- msgloom/sources/release_api.md (types, exact reconstruction, historical context)
- docs/phase-1/architecture.md (durable incremental handoff)
- docs/notes/task15-final-qualification-20261016.md (exact-SHA test evidence)
- msgloom/preparation_pipeline/intake.py, scheduled.py, historical_baseline.py and transitions.py (current interfaces)
- msgloom/sources/release_models.py (ReleasedInput/ScopedTransition)

## D1. Legacy A2 code and test inventory (reference, not authority)

Observed on master 895fc40:

| Area | Evidence | New-design action |
| --- | --- | --- |
| Existing A2 controller | preparation_pipeline/handler.py (368 LOC) | Do not wrap/copy; independent oracle |
| Sequencing helpers | record_steps.py (460), stage_steps.py (287) | 1,115 LOC combined with handler; measure replacement complexity |
| A2 intake + scheduling | intake.py (421), scheduled.py (304), historical_baseline.py (183) | Accepted workset/replay semantics; preserve behaviours |
| Domain semantics | preparation/filtering.py, grouping.py, grouping_graph.py, records.py | Tested deterministic boundaries; reuse pure interfaces where valid |
| Parser isolation | preparation/isolation/ plus MIME/HTML, Excel, PDF, Word parsers | Preserve sandbox limits and existing source mapping |
| A2 tests | tests/preparation_pipeline/, tests/preparation_semantics/, tests/phase1_foundation/ | Golden/negative oracle; not certification of new engine |
| Cross-stage | tests/phase1_e2e/, tests/application_cli/ | Mandatory A3/A5 integration and replay/partial consistency |
| Operator command | msgloom/cli/app.py prepare-scheduled + configuration | Finite external-invocation model, no built-in scheduler |
| Current dependency set | pyproject.toml, uv.lock | No Kedro core dependency; 1.7.0 is not installed by this work |

Current tested parser libraries include python-calamine 0.9.0, openpyxl 3.1.5, pypdfium2 5.14.0, python-docx 1.2.0 and selectolax 0.4.13. Scrapy is pinned 2.19.0. These are lockfile observations, not license for an unreviewed parser upgrade.

Representative existing regression sources:

- tests/preparation_pipeline/test_integration.py
- tests/preparation_pipeline/test_documents.py
- tests/preparation_pipeline/test_evidence_loss.py
- tests/preparation_pipeline/test_stable_identity.py
- tests/preparation_pipeline/test_scheduled_recovery.py
- tests/preparation_pipeline/test_scheduled_transitions.py
- tests/preparation_pipeline/test_historical_baseline.py
- tests/preparation_pipeline/test_plan_acceptance.py
- tests/preparation_semantics/test_filtering.py
- tests/preparation_semantics/test_grouping.py
- tests/phase1_e2e/test_cross_stage_chain.py
- tests/phase1_e2e/test_replay_recovery.py

Topic 01 engineering validation ACCEPTED E1–E4 *synthetic*, not production design/accuracy. It requires duplicated Message-ID ambiguity, distinct quote occurrence/parent/source relations, versioned corrections and truly independent gold. Topic 02 synthetic/adversarial test campaign ACCEPTED, but production matter identities and response semantics remain research topics. These findings inform adversarial tests, not new AI joining logic inside deterministic A2.

## D1. Actual limitations and non-blocking upstream exclusions

- Real enterprise Teams work/school tenant integration was outside Task 15; local native Scrapy fixtures are not a live tenant proof. Do not force A1 reopen to begin A2.
- External Prefect scheduler deployment is intentionally outside the package/Task 15; prepare-scheduled is finite, not a resident job.
- Native Windows secure saved-source reader is not certified. POSIX descriptor-relative/no-follow and /dev/fd pinning are the accepted security assumptions; see GitHub issue #47. Windows smoke != production Windows A2.
- Numeric XLSB cell/value coverage has a documented parser limitation (docs/notes/phase1-acceptance.md); preserve it rather than falsely claim full spreadsheet comprehension.
- Research-based quotation/semantic grouping representativeness not yet proved on production mail. Do not elevate exploratory method results to shipping guarantees.

## D2. Kedro Core external evidence and open risk

- PyPI latest observed on 2026-10-23: 1.7.0 (published 2026-09-28); 1.6.0 was the September 29 historical candidate.
- Official SequentialRunner docs: synchronous node execution; is_async=True refers to thread-based dataset load/save. Programmatic DataCatalog and MemoryDataset are supported.
- Telemetry docs: KEDRO_DISABLE_TELEMETRY/DO_NOT_TRACK opt-out; verify on exact installed runtime and avoid dynamic project/plugin loading.
- **CVE conflict: unresolved as planning evidence.** Snyk SNYK-PYTHON-KEDRO-17752561/CVE-2026-3840 marks all versions susceptible to unsanitized versioned paths; GitLab CVE-2026-35167/GHSA-6326-w46w-ppjw documents a similar path traversal fixed in 1.3.0. The two records cannot be assumed identical or different from secondary summaries alone. Q0 requires installed source inspection, dated risk/advisory reconciliation, audit and explicit acceptance. Prohibition on versioned datasets, arbitrary catalog configs, CLI use and user version strings reduces direct reachability, but is **not** a substitute for source/advisory review.
- Runtime dependencies on Python 3.12/3.13/3.14, aarch64 Linux and cgroup process safety are to be tested separately at Q0; PyPI metadata by itself does not qualify the locked package.
- No Kedro upgrade or dependency manifest edit has been made.

External sources:

- <https://pypi.org/project/kedro/1.7.0/>
- <https://docs.kedro.org/en/1.7.0/api/runner/kedro.runner.SequentialRunner/>
- <https://docs.kedro.org/en/latest/build/run_a_pipeline/>
- <https://docs.kedro.org/en/stable/about/telemetry/>
- <https://security.snyk.io/vuln/SNYK-PYTHON-KEDRO-17752561>
- <https://advisories.gitlab.com/pkg/pypi/kedro/CVE-2026-35167/>

## D3. Implementation preparation verdict

The companion plan has micro-steps with <=30-minute active edit targets, explicit dependency and ownership DAG, isolated parser/fixture lanes, a serial dependency/lock owner, and commit/merge gates. Mandatory preservation includes 28-gate A1 historical evidence (never relabel), 13 handoff scenarios, current A2 golden data, seven prepared categories, scoped transition-only effects, security and platform limitations, semantic replay identity and correct partial/cancelled/failed outcomes.

New code must wait for owner approval, independent design acceptance and Q0 security/runtime proof. The main risk is architectural non-benefit: a Kedro adapter that simply repackages 1,115 LOC of old sequencing creates a worse system. The measured no-complexity-regression gate must be applied, not waived.

## D4. Review criteria / record

The independent reviewer must independently inspect actual repo paths, this design, the implementation plan, the historical branch plan, A1 handoff source and Task 15 proof, rather than treating document assertions as executable evidence. Review at least:

1. Does the new plan accidentally mutate or reimplement an accepted A1 release/intake invariant?
2. Does new Kedro truly own a meaningful pure dependency DAG rather than a wrapper?
3. Is the cancellation/timeout/claim/publish proof coherent without stopping threads?
4. Does 20-Spider coverage correctly count profile and Teams notification cases?
5. Are component-only, context-only, held and scoped transition shapes losslessly handled?
6. Are fixed semantic versions and filters/grouping, quote/parent ambiguity, parser source spans and limitations testable?
7. Is Kedro 1.7 security ambiguity treated as a genuine hard gate with a fail-closed path?
8. Can all microsteps be implemented in safe independent worktrees with one dependency lock owner?
9. Is the outcome measurable against old A2 and A3/A5, and is the rollback non-destructive?
10. Are unsupported live Teams and Windows claims excluded?

**D4 R1:** REVISE; reviewer found 9 P1 and 8 P2 at 37f5886. Source evidence was read-only, with **no tests run**. A1 original Task 15 acceptance is unaffected. Remediation mapped as follows: batching and grouping scope (new design §5); parser planning (§5.1); input/workset mapping (§5.2 plus above matrix); partial publication (§5.3); bounded cooperative cancellation (§6/§9); pure node topology (§5); semantic versioning (§9.2); security Q0 authorization (§6 and implementation §4); numeric maintainability baseline (§11). P2 corrections include explicit Teams supported reply, fixed legacy oracle SHA 895fc40, MemoryDataset copy_mode assign, redacted failure logs, additional tests and unchanged Task 15 runner.

**D4 status for revised candidate:** awaiting independent R2 verdict. No adoption GO until reviewer report records the **new** exact source commit and ACCEPT. A review finding must be fixed in documents and independently rechecked before changing status. Do not say "independent accepted" merely because a test or linter passed.

## Record of actions

- Read upstream A1 formal closeout and 13 scenarios from current repo/GitHub.
- Read the historical Kedro plan from **local-only** program/kedro-a2-plan commit c7dcb41; it was absent from remote master/branches.
- Read actual A2 Python classes, package versions and tests from baseline master.
- Checked public Kedro 1.7 and the conflicting security records.
- Created only documentation in isolated docs/a2-kedro-native-design-20261023 worktree; source base 895fc40, initial planning commit 37f5886.
- The first reviewer identified concrete design defects, so revised both the design and implementation plan, retained the original reviewer output, and added the stream crosswalk. The revision still needs a new exact-SHA review.
- No A2 Python/package/lock/scheduler changes, no source worktree cleanup and no runtime agent deployment in this audit.
