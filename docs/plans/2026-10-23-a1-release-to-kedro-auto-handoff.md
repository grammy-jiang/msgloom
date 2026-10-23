# A1 committed-release -> Kedro-primary A2 automatic handoff

**Status:** DESIGN CANDIDATE / NOT DEPLOYED.
**Date:** 2026-10-23, Australia/Sydney.
**User decision:** after A1 reaches its real completion/authority gate, Kedro is the primary new A2 ETL orchestrator; obsolete legacy A2 is deprecated. Public application API remains async.
**Authoritative upstream:** ../superpowers/specs/2026-10-03-a1-a2-handoff-contract-design.md; ../notes/task15-final-qualification-20261016.md; ../notes/a1-a2-qualification-checklist.md.
**Kedro architecture:** 2026-10-23-a2-kedro-native-design.md.
**Decision ADR:** ../decisions/2026-10-23-a2-kedro-primary-etl.md.
**Scope:** design/execution wiring, not A1 source modifications, Kedro implementation, or external scheduler deployment.

## 1. Direct conclusion: the handoff is already a committed event ledger

A1 does **not** publish arbitrary Scrapy results or a mutable SQLite table as a consumable batch. It publishes acquisition facts under source/stream/scope, then atomically commits a ReleaseGroup and ordered ReleaseEntries only when provider-specific logical completion/authority is proved. Failed, incomplete or losing acquisition states must not be silently released. The immutable ReleaseEntryRef is the downstream admission anchor, with catalog identity, global release-entry sequence and entry digest.

A2 must consume only **committed** entries, not raw_http_evidence, provider projections, timestamps, Spider close signals or active Scrapy objects. The current A1 design already does the essential heavy lifting:

- 20 installed Scrapy Spiders and seven A2 streams (microsoft_profile has no release, Teams notification reconciliation adds facts to existing Teams chat/channel streams).
- A1 ReleaseSourceReader reconstructs exact ReleasedInput: entry reference, optional primary CollectedSelection, component selections, inventory/control context, scoped transitions and ordered facts. It verifies saved evidence and release hashes.
- PreparationIntakeService consumes a fixed finite entry cut and persists exact collected_selection@1 plus one PreparationIntakeWorkset with the previous/cutoff anchors, pending/held dispositions and consumer cursor in the separate Phase1Persistence store.
- HistoricalBaselineService is the explicit new-consumer initialization path for caller-approved **exact versions**. It never invents pre-ledger release entries or infers a batch from current source tables.
- Kedro new A2 receives immutable exact workset references and owns downstream ETL stage ordering through programmatically configured Pipeline/DataCatalog/Runner. Existing claimed new pipeline must never fall back to old A2 private processing.

This is the already accepted A1 output contract. There is **no requirement to redesign the A1 source catalogue, rewrite Spiders or add A2 callbacks inside A1**.

## 2. Natural automatic end-to-end behavior

~~~mermaid
flowchart TD
  C["A1 Scrapy collection / reconciliation"] --> G{"Logical completeness & authority gate"}
  G -->|not yet committed| H["Keep staged/pending A1 facts"]
  G -->|accepted| L["Atomic immutable ReleaseGroup + ReleaseEntries"]
  L --> W["External runner wakes finite A2 invocation"]
  T["Periodic reconciliation trigger"] --> W
  W --> I["prepare-scheduled: read pending + fixed new release cut"]
  I --> F["Persist exact selections + immutable workset + cursor"]
  F --> K["New Kedro-owned A2 ETL pipeline"]
  K --> R["Claim-fenced versioned stage-result datasets"]
  R --> P["Accepted receipt / pending retry / explicit held disposition"]
  P --> A["A3 consumes accepted A2 results"]
~~~

**Wakeup is advisory; ledger is authoritative.** Even if an external wakeup is duplicated, lost or arrives before an A1 transaction commits, the reader's fixed released-entry cut and durable cursor determine actual eligible work. The wakeup carries no provider payload or claimed source version. No A1 write path should synchronously invoke Kedro; A1 must remain available if A2 is offline.

A1 can keep collecting while A2 processes frozen selections. No global barrier waits for every source or every Spider. Source-level completion gates and atomic release publication remain A1-owned.

## 3. Trigger design without changing A1

Use the already chosen **external Prefect 3** deployment side, not a new msgloom internal scheduler or in-process queue.

**Immediate trigger:** for collection jobs launched by Prefect, the external orchestration wrapper invokes the finite `msgloom prepare-scheduled` operation after the collection invocation ends. The wrapper may invoke it even after a failed/partially completed collector, because only *committed ReleaseEntries* qualify as new work. No release simply means safe no-op. Avoid reading source payloads or manufacturing release IDs in Prefect. This is a wake-up notification, **not** a business completion signal.

**Recovery trigger:** a configurable periodic Prefect reconciliation invokes the same finite command for configured scopes. This covers missed immediate wakeups, independently running A1 sources, worksets left pending across failure/restart, backlog greater than one page and new releases arriving while a prior A2 job was active. Multiple triggers share the same stable consumer cursor; no second queue or event database is necessary.

**Low-latency optional future integration:** an external A1 process coordinator may signal Prefect after successful release commit, but do not add such an A1 source-code hook unless measured latency requires it and a separate A1 review approves. There is currently no verified installed release-notification event bus. The accepted ledger plus ordinary Prefect invocation is sufficient to begin.

**Only one entrypoint:** keep the existing `msgloom prepare-scheduled config.toml invocation.json` operator contract. Replace its *legacy A2 producer* behind the Application composition with the accepted Kedro-primary pipeline at cutover. Never make Prefect call `kedro run` or schedule individual Kedro nodes.

## 4. Exact execution and ownership sequence

1. **Operator onboarding once, not per run.** Configure each allowed A1 source binding / stream / stable consumer_id, trusted expected_catalog identity and parser/policy configuration. `expected_catalog` is pinned from explicitly approved A1 identity; do not silently re-read a replacement catalog and trust it. Supported streams: outlook_mail, outlook_calendar, todo, contacts, onedrive, teams_chat and teams_channel. At most 32 targets per current invocation.
2. **Fresh finite invocation.** External coordinator reads the current redacted configuration version through `msgloom config inspect --config`, creates a fresh execution/attempt identity and trusted caller/authority reference, and runs `msgloom prepare-scheduled` using an argument vector. Preserve the same consumer_id across retries. No raw source contents, credentials, or arbitrary provider URLs in invocation JSON or logs.
3. **Intake and pending.** The application opens ReleaseSourceReader and existing Phase1Persistence. It checks the configured catalog identity and previously saved exact cursor anchor. It processes a bounded number of pending worksets fairly, then freezes a `max_release_entry_seq` for the configured (source_id, stream), lists only committed entries after the saved cursor up to that ceiling, and materializes exact selections.
4. **Atomic admission.** `collected_selection@1` saved before parser processing; workset, pending index and cursor commit in one existing atomic transaction. Cursor means durable admission, not ETL success. Evidence unavailable/corrupt produces explicit HeldIntakeEntry; subsequent eligible entries continue.
5. **Kedro A2.** Application passes the immutable workset/selection identities to the new Kedro-primary A2. Programmatic DataCatalog datasets load verified bytes and invoke trusted sandbox parsers, and its Pipeline executes extraction, normalization, content zones, scope/native relations, filtering, grouping and versioned output saves. No source discovery, provider fetch or mutable A1 reads here. Async boundaries/claims remain enforceable by msgloom.
6. **Durable completion.** Stage saves use exact trusted ClaimToken and ResultRefs. Completion receipt closes the workset only after accepted required stages have published their manifests. Fatal failure/cancel/timeout retains already durably saved results and leaves unfinished work discoverable pending; no false COMPLETE or cursor rewind.
7. **Next invocation.** A subsequent wakeup or periodic reconciliation processes pending saved work and the next fixed release cut. A new A1 entry above a prior cutoff waits for a later run. A3 consumes accepted prepared/zone/filter/group results through explicitly versioned schemas without assuming all fields are complete.

The existing scheduled.py currently processes multiple configured targets *sequentially* and attempts only bounded work per target. Deployment should start with one finite invocation or separately configured scopes, not unlimited concurrent writer processes contending on a Pi SQLite store. Add measured bounded concurrency later without changing A1.

## 5. Why a post-Spider callback or raw SQLite scan is wrong

| Tempting shortcut | Failure mode | Correct mechanism |
| --- | --- | --- |
| Launch Kedro when Spider closes | Pause, partial/failed scope or deferred Full obligations may not be authoritative | Release commit is the eligibility proof; close only wakes the external reconciler |
| Pass just Spider run_id | One logical release can span multiple runs; completion scopes vary | Exact committed entries and durable workset selection |
| Scan latest SQLite rows or raw HTTP files | Replays old rows, loses provider scope, misses deferred releases, guesses chronology | Sequenced committed ReleaseEntry after consumer cursor |
| Run Kedro inside A1 | A2 crash delays/corrupts A1 lifecycle, creates tangled dependencies | Independent async Application operation and external trigger |
| Use Prefect job state as release truth | Process exit isn't a provider-specific completion proof | A1 immutable release ledger is sole business signal |
| Treat one trigger as one batch | Multiple streams, multiple entries and finite pagination | A2 bounded saved worksets with stable consumer cursor |
| Update A1 cursor only after Kedro success | Crash creates duplicate admission; A1 state becomes downstream-dependent | Commit intake cursor with immutable workset before ETL |
| Blind-retry any nonzero CLI status | INCOMPLETE may mean normal pending work; BLOCKED may mean wrong catalog | Persist outcome, classify and use next finite run / operator alert |

## 6. Failure, duplicate wakeup and status policy

- **No released entries:** complete with empty result refs; no Kedro parsing and no new workset.
- **Committed A1 entries with an already active consumer:** scoped PREPARE_INTAKE/prepare claims reject duplicate admission or work; serialize external jobs or rely on fenced claims with bounded backoff.
- **Killed before workset commit:** no cursor advancement, next run replays/reuses any durably saved exact selections.
- **Killed after workset commit:** pending workset survives and is processed on next run, no need to rescan A1 current state.
- **One bad evidence component or malformed input:** explicit held/limited path; do not forge content, block other good releases, or auto-recollect.
- **Claim lost or catalog restored/mismatched:** STOP and mark FAILED/BLOCKED with safe diagnostic; don't reset consumer or accept a different catalog silently.
- **A2 ETL failure:** retain partial durable refs and pending proof; allow later finite retry with exact captured inputs.
- **Exit codes of current CLI:** 0 COMPLETE; 2 invalid input/config; 3 BLOCKED; 4 INCOMPLETE and other not-complete states. Do not treat all exit 4 as fatal provider errors. The external wrapper must inspect saved terminal status and limitation codes; it should never blindly overwrite/recreate a cursor or resend an external A3/A5 effect.

The existing workset-level locks and per-stage claim fencing remain the source of idempotence. There is no exact-once promise for arbitrary side effects; ingestion is at-least-once *attempted* with atomic durable admission, and accepted stage effects are deduplicated/fenced by their documented identities.

## 7. Current actual deployment readout and cold-start guidance

A1 code/contract is fully present and formally qualified, but **formal test acceptance is not proof that an external trigger is deployed**. Existing operator documentation specifies Prefect externally; repository inspection found no running/deployed Prefect-to-A1/Kedro trigger under package source/deployment modules. `msgloom prepare-scheduled` exists today but still composes the *old* A2 implementation. Neither fact should be described as Kedro automation already working.

On a fresh deployment, running scheduled preparation over a valid catalog with **zero committed ReleaseEntries** legitimately processes nothing. Presence of pre-ledger `raw_http_evidence` alone must not qualify historical records. HistoricalBaselineService accepts only caller-approved **exact VersionRefs** and verifies their immutable evidence/facts; it does not crawl arbitrary raw evidence or invent releases. Some older unledgered records may not be baseline-admissible. If existing history is required, inventory which exact sources are safely eligible for an approved historical baseline, or run new authorised A1 collection to publish real releases. Do not silently backfill.

No private catalog identity, source ID, body, path or credential belongs in checked-in examples.

## 8. Verification / deployment tasks (new work, not already passed)

| Gate | Execution test | Pass condition |
| --- | --- | --- |
| AUTO-01 | Real native A1 fixture emits one completed release, external wrapper wakes A2 | Exactly one immutable A2 workset and one set of accepted Kedro stage results |
| AUTO-02 | Spider exits without release (failed/paused/deferred) | No false Kedro work |
| AUTO-03 | Two A1 releases arrive during one A2 processing cycle | Prior fixed cutoff processed; later one remains for next run |
| AUTO-04 | Trigger delivered twice / overlapping reconciler | Same catalog/source/stream/consumer produces no duplicate workset or accepted stage |
| AUTO-05 | Crash after saved selection, before cursor/workset transaction | Safe retry without orphaned accepted cursor |
| AUTO-06 | Crash after workset commit, before Kedro done | Pending workset reruns exact selected evidence, no cursor rewind |
| AUTO-07 | Missing/corrupt evidence followed by good release | Held is explicit; later release proceeds |
| AUTO-08 | Two source streams incl Teams + contextual entity | Separate pinned cursors and correct scope/grouping rules |
| AUTO-09 | Historical initialisation in empty-release catalog | No automatic historical inference; explicit approved exact-version baseline only |
| AUTO-10 | Config identity mismatch/replaced catalog | BLOCKED before source/claim changes |
| AUTO-11 | Refused parser, timeout, cancellation and stale claims | No late claim-fenced publications; stage results persist honestly |
| AUTO-12 | Prefect invoker handles COMPLETE, INCOMPLETE, BLOCKED, FAILED | Limited next run for pending; alert for trust issues; no blind A3/A5 side-effect retry |
| AUTO-13 | A1 continues publishing while Kedro processes saved input | A1 does not wait; no mutable-projection reads in A2 |
| AUTO-14 | Full exact source→workset→Kedro→A3 E2E | Explicit lineage, output limitations and schema versions survive restart |

These tests are on the **new Kedro candidate** and a deployment-owned orchestration harness. The old `tests/test_a1_handoff_scheduled_e2e.py`, `tests/preparation_pipeline/test_scheduled_recovery.py`, and `tests/application_cli/test_scheduled_prepare.py` are source-level oracles, not substitutes for new Kedro tests. Keep A1's original Task 15 28-gate evidence frozen.

**Implementation order:** (1) read-only A1 catalog/pending/cursor inspection and current code/CLI confirmation; (2) independently validate new Kedro DataCatalog + async bridge; (3) integrate Kedro producer behind same Application prepare-scheduled admission; (4) implement only the external Prefect wrapper with fresh invocation envelopes; (5) build native fixture and failure/recovery end-to-end tests; (6) enable automatic triggers after reviewed exact-SHA acceptance. Do not make A1 emit new API events or place Prefect inside the package.
