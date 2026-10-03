# A1 to A2 Durable Handoff Implementation Plan

> Status: readiness-reviewed implementation plan; production implementation not yet executed.
>
> Design authority: docs/superpowers/specs/2026-10-03-a1-a2-handoff-contract-design.md
>
> Baseline at plan creation: 5ff41d6724818cbcd40a72b91d17751cf131726f plus the reviewed design-readiness amendments in the working tree.

## Goal

Implement the approved durable A1-to-A2 handoff contract without redesigning existing Microsoft Graph traversal or the existing finite A2 preparation producer.

The implementation adds:

- A1 immutable acquisition facts;
- A1 mutable effective-state freshness index;
- atomic release groups and sequenced release entries;
- provider-specific fact/release integration for all current Microsoft Spiders;
- exact release-aware source reconstruction;
- A2 PREPARE_INTAKE ownership, cursor, immutable workset, pending-workset state, and neutral-schema v4;
- scheduled bounded intake that persists exact CollectedSelection inputs and pending work before advancing its cursor;
- reuse of the existing PreparationHandler replay/exact-selection path after intake.

Kedro orchestration is intentionally downstream of this plan. This plan makes the input boundary deterministic first.

## Non-negotiable constraints

- Runtime Scrapy is 2.19.0.
- Keep Spider traversal, Requests, callback flow, retry/cache behavior, provider checkpoint algorithms, and existing source permissions unchanged unless a task explicitly names the required compatibility fix.
- A1 must not import msgloom.sources, msgloom.preparation, CollectedSelection, or other A2 implementation types.
- A2 must not mutate A1 rows as consumed.
- Do not use provider observed_at as the incremental watermark.
- Do not infer handoff work by scanning current provider tables.
- Every downstream-visible A1 state advancement and its acquisition fact commit in the same SQLite transaction.
- Authority promotion and its release group/entries commit in the same SQLite transaction.
- A1 release entry sequence orders admission only; it does not replace provider ordering/freshness semantics.
- Non-authoritative release builders revalidate the effective source_state_key before publishing.
- authority_staged facts cannot become A2 entries outside the winning authority promotion.
- A2 cursor advances only with a durable immutable intake workset and pending-workset state in one short Phase 1 transaction.
- Evidence reads, source assembly, and CollectedSelection construction occur outside the final A2 cursor transaction.
- One bad release entry is durably held rather than poisoning the stream forever.
- Mail folder removal and Calendar fixed-window removal remain scoped transitions, not global deletion.
- Existing exact CollectedSelection codec/replay behavior is reused.
- Existing Phase1Persistence remains the only owner of the neutral application SQLite schema.
- The neutral schema migration is explicit v3 -> v4.
- The A1 acquisition catalog continues to use additive schema creation; ledger metadata initializes a stable catalog identity on first ledger-aware open.
- No automatic ledger pruning in this implementation.
- No production implementation step starts Kedro nodes.
- Development may be parallelized after the shared ledger contracts are frozen. Do not use local Codex subagents; if parallel agents are used, use actual ChatGPT chat sessions.

## Dependency DAG

    Task 1  A1 ledger contracts/schema/store
      |
      +---- Task 2 Mail persistence facts
      +---- Task 3 Calendar persistence facts
      +---- Task 4 To Do + Contacts persistence facts
      +---- Task 5 OneDrive persistence facts
      +---- Task 6 release-aware A1 read API skeleton
      |
      +---- Task 7 Mail/Calendar Full release completeness
      |
      +---- Task 8 non-authoritative release extension
      |
      +---- Task 9 authority release integration
                  |
                  +---- Task 10 A1 end-to-end release qualification
                  |
                  +---- Task 11 A2 neutral schema v4 + intake persistence
                               |
                               +---- Task 12 release-aware source adapters
                               |
                               +---- Task 13 A2 intake service
                                            |
                                            +---- Task 14 scheduled PREPARE composition
                                                         |
                                                         +---- Task 15 end-to-end qualification and closeout

Tasks 2-7 are parallel after Task 1.
Task 11 can start after the release-entry public read contract from Tasks 1 and 6 is stable; it need not wait for every provider integration.
Tasks 8 and 9 can be developed in parallel once their provider prerequisites land.

## Task 1 — Add the provider-neutral A1 ledger core

### Task 1 files

Create:

- message_ingest/acquisition/handoff.py
- message_ingest/catalog/models/handoff.py
- message_ingest/catalog/stores/handoff.py
- tests/test_acquisition_handoff_catalog.py

Modify:

- message_ingest/catalog/models/__init__.py
- message_ingest/catalog/__init__.py
- message_ingest/catalog/schema.py

### Contracts

Define closed A1-only enums/data contracts for:

- AcquisitionStream
- AcquisitionFactKind
- StorageRelation
  - advanced
  - current_equivalent
  - authority_staged
  - stale
- ReleaseKind
- ReleaseEntryKind
- FactSpec
- ReleaseGroupSpec
- ReleaseEntrySpec
- EffectiveStateKey
- SourceStateKey
- SourceVersionLocator

Do not import A2 types.

### Tables

Add additive A1 tables equivalent to:

- acquisition_ledger_metadata
  - schema_version
  - stable catalog identity
- acquisition_facts
- acquisition_effective_states
- acquisition_release_groups
- acquisition_release_entries
- acquisition_release_entry_facts
- acquisition_run_outcomes

The exact ORM names can differ, but semantics must match the design.

release_entry_seq must be a monotonic local SQLite sequence suitable for bounded source/stream reads.

### Store API

AcquisitionHandoffStore must support caller-owned SQLAlchemy Session and Core Connection operations. It must not open a nested transaction when called from a provider store/promotion.

Minimum operations:

- stage_state_fact_in_session(...)
- stage_authority_fact_in_session(...)
- current_effective_state(...)
- release_effective_group_in_session(...)
- release_authority_group_in_session(...)
- list_release_entries(...)
- load_release_entry(...)
- load_release_facts(...)
- catalog_identity(...)

For normal current-state writes:

1. provider store decides whether the write is stale;
2. canonical source_state_key is calculated from retained semantic state;
3. fact is inserted idempotently;
4. acquisition_effective_states is updated only for a new advanced state;
5. same key becomes current_equivalent and retains the prior effective advanced fact;
6. stale does not replace effective state.

For authority_staged facts, do not update acquisition_effective_states until the winning promotion applies them.

### Identity/digest rules

Use canonical bounded JSON and SHA-256 for:

- fact idempotency material;
- source_state_key;
- release group digest;
- release entry digest.

Run/capture identifiers are provenance and must not be included in source_state_key if they do not change source meaning.

SourceVersionLocator remains an A1-owned closed structure, not an arbitrary string/path.

### Source-state key policies

Primary-resource state keys and enrichment-component state keys are separate.
Do not hash a sparse discovery representation and a Full representation into
the same surface key merely because they contain different field sets.

| Family | Primary resource state | Component state |
| --- | --- | --- |
| Outlook Mail | provider `changeKey` plus bounded fallback projection when unavailable; discovery/delta/reconcile observations revalidate this primary state | detail, MIME, attachment inventory/metadata/raw use independent component keys; detail can supply exact primary bytes for a Full release without forcing a false primary-version change |
| Outlook Calendar | event `changeKey` plus bounded fallback projection; calendar metadata uses its own canonical projection | detail/profile surface, attachments/content, and series topology have independent component keys bound to event/resource version |
| To Do | canonical retained task/list/checklist/linked-resource projection; task `lastModifiedDateTime` participates when present | checklist/linked-resource entries are child components of task but also retain exact provider identities |
| Contacts | canonical retained snapshot/delta provider projection including scope and `lastModifiedDateTime` when present | no mutable merged current ContactRecord may substitute for an immutable sparse delta fact |
| OneDrive | sanitized provider item projection including deletion state and `eTag`/`cTag` when present | explicit content key uses content SHA-256 plus the metadata-version binding/response tag contract |

Canonical fallback projections exclude run IDs, capture timestamps, evidence
IDs, access tokens, preauthenticated URLs, and other transport-only values.

### Task 1 tests

Prove:

- fresh catalog gets one stable identity;
- reopen preserves identity;
- backup/copy preserves identity;
- exact fact staging is idempotent;
- advanced/current_equivalent/stale classification;
- authority_staged does not become effective before promotion;
- fact failure rolls back effective-state update;
- release group/entries are immutable;
- entry sequence is monotonic;
- zero-entry groups are valid;
- one group can contain more entries than one downstream intake limit;
- digest mismatch is rejected;
- Session and Core Connection integration both work without nested transaction ownership.

### Exit gate

Run:

- focused new test
- tests/test_catalog_schema.py
- tests/test_catalog_store_layout.py
- Ruff/Pyright for changed modules

Commit only after green.

## Task 2 — Integrate Outlook Mail facts and fix Mail JOBDIR half-support

### Task 2 files

Modify:

- message_ingest/items/microsoft/outlook/email.py
- message_ingest/catalog/stores/microsoft/outlook/email.py
- message_ingest/catalog/stores/microsoft/outlook/_email_lifecycle.py
- message_ingest/pipelines/microsoft/outlook/email.py
- message_ingest/spiders/microsoft/outlook/email/discover.py
- message_ingest/spiders/microsoft/outlook/email/full.py
- message_ingest/spiders/microsoft/outlook/email/_attachments.py
- message_ingest/commands/microsoft/outlook/mail.py or the narrowest existing validation layer

Tests:

- tests/test_pipeline.py
- tests/test_outlook_mail_full_enrichment.py
- tests/test_outlook_commands.py
- tests/test_jobdir_resume.py
- new tests/test_outlook_mail_handoff_facts.py

### Task 2 required changes

1. OutlookMessageSurfaceItem gains explicit run_id.
2. Every producer of OutlookMessageSurfaceItem supplies the logical run ID.
3. Mail attachment/surface store methods receive logical run provenance.
4. record_message returns structured persistence outcome rather than using observation-created/replay as the only signal.
5. set_surface, upsert_attachment, upsert_folder, mark_folder_removed expose stale/equivalent/advanced semantics.
6. Each downstream-visible state advancement stages its fact in the same transaction.
7. record_folder_removal stages a scoped folder-membership transition fact in its transaction.
8. mark_folder_removed stages folder control/transition facts but does not release them before folder-delta authority commit.
9. Mail discover and Mail full explicitly reject JOBDIR until separately qualified. Do not change qualified Mail delta JOBDIR.

### Mail source-state rules

For primary message state, source_state_key is derived from the exact retained Graph message representation intended for downstream meaning, not from run/evidence IDs.

For MIME/raw components, source_state_key uses the verified saved content digest plus semantic component identity.

For terminal surface limitations, state key includes the terminal status/profile/component/resource-version semantics but excludes attempt identity.

### Task 2 tests

Include the already reproduced HTTP-cache case:

- Run 1 network evidence advances M.
- Run 2 cache replay resolves to Run 1 canonical evidence.
- Run 2 has a fact with current run provenance and the same source_state_key.
- No duplicate primary work is published if the prior advanced state was already released.
- The exact prior advanced fact can be adopted if it was never released.

Also prove delayed older run cannot release after a newer state supersedes it.

## Task 3 — Integrate Outlook Calendar facts

### Task 3 files

Modify:

- message_ingest/items/microsoft/outlook/calendar.py
- message_ingest/catalog/stores/microsoft/outlook/calendar.py
- message_ingest/catalog/stores/microsoft/outlook/_calendar_planning.py
- message_ingest/pipelines/microsoft/outlook/calendar.py

Tests:

- tests/test_calendar_pipeline.py
- tests/test_calendar_full_pipeline.py
- tests/test_calendar_series_topology.py
- tests/test_calendar_delta_pipeline.py
- new tests/test_calendar_handoff_facts.py

### Task 3 required changes

1. OutlookCalendarEventSurfaceItem gains explicit run_id.
2. set_event_surface returns storage relation and stages a component fact atomically.
3. persist_calendar/event/attachment/series/content stage facts in their existing transaction.
4. persist_delta_observation stages authority_staged facts only.
5. Existing Calendar event immutable observation identities remain valid locator material for non-delta exact versions.
6. Full component locators are evidence-backed fact locators, never future mutable surface rows.

### Task 3 tests

Prove:

- created/changed/unchanged/replay/stale mapping;
- component parent is the event;
- old Calendar Full attempt cannot publish after newer component state wins;
- delta observations remain invisible as entries before checkpoint promotion.

## Task 4 — Integrate To Do and Contacts facts

These products share snapshot-style positive observations plus later authoritative presence, but keep stores separate.

### Task 4 files

Modify To Do:

- message_ingest/catalog/stores/microsoft/todo.py
- message_ingest/sync/microsoft/todo/snapshots.py
- message_ingest/pipelines/microsoft/todo.py

Modify Contacts:

- message_ingest/catalog/stores/microsoft/contacts.py
- message_ingest/catalog/stores/microsoft/_contacts_delta.py
- message_ingest/catalog/stores/microsoft/_contacts_state.py
- message_ingest/pipelines/microsoft/contacts.py

Tests:

- tests/test_todo_catalog.py
- tests/test_todo_sync.py
- tests/test_contacts_catalog.py
- tests/test_contacts_ordering.py
- tests/test_contacts_integration.py
- new tests/test_todo_handoff_facts.py
- new tests/test_contacts_handoff_facts.py

### Task 4 required changes

To Do:

- TodoStore._upsert stages resource/component facts atomically.
- Snapshot sightings/completions remain separate authority proof.
- Unchanged resources do not repeatedly become A2 work.
- Equivalent retry can adopt an unreleased advanced fact.

Contacts snapshot:

- persist_folder/contact stage facts in the same writer transaction as current state.
- sightings remain authority proof.

Contacts delta:

- persist_observation stages authority_staged fact.
- no mutable merged ContactRecord is advertised as an immutable historical provider response.

### Task 4 tests

Prove:

- full unchanged snapshot after an already released state creates no duplicate resource entries;
- failure after advanced fact but before snapshot promotion can be recovered on equivalent retry;
- stale generation cannot publish;
- sparse Contact delta is not released before winning promotion.

## Task 5 — Integrate OneDrive facts

### Task 5 files

Modify:

- message_ingest/catalog/stores/microsoft/onedrive.py
- message_ingest/sync/microsoft/onedrive/state.py
- message_ingest/pipelines/microsoft/onedrive.py

Tests:

- tests/test_onedrive_catalog.py
- tests/test_onedrive_pipeline.py
- tests/test_onedrive_content.py
- tests/test_onedrive_resync.py
- new tests/test_onedrive_handoff_facts.py

### Task 5 required changes

- persist_drive/item stage facts through the OneDrive upsert-session helper.
- persist_content stages exact content component fact in the same transaction as OneDriveContentCapture.
- persist_resync_observation stages authority_staged fact.
- preauthenticated download URLs remain excluded.
- new release-aware exact OneDrive locator uses immutable evidence/capture association, never the existing current pseudo-version.

### Task 5 tests

Prove:

- current-equivalent metadata does not repeat work after release;
- content hash change advances item-content state;
- stale content cannot replace a newer content association;
- 410 staged observations cannot leak before winning reset promotion.

## Task 6 — Add the read-only A1 release feed API

### Task 6 files

Create:

- msgloom/sources/handoff_models.py
- msgloom/sources/handoff_catalog.py

Modify:

- msgloom/sources/__init__.py
- msgloom/sources/models.py as needed only for common read limits

Tests:

- tests/source_reader/test_handoff_catalog.py

### Task 6 contract

This is a read-only adapter over A1 ledger tables. It does not import message_ingest.

Expose bounded types:

- A1CatalogIdentity
- ReleaseEntryRef
- ReleasedFact
- ReleaseEntry
- ReleaseEntryPage

Minimum operations:

- catalog_identity()
- list_release_entries(source_id, stream, after_seq, through_seq, limit)
- max_release_entry_seq(source_id, stream)
- get_release_entry(seq)
- get_release_facts(entry)
- verify_entry_anchor(seq, digest)

Every query is bounded and read-only with the same safe SQLite path strategy as SavedSourceReader.

### Task 6 tests

Prove:

- bounded entry pages;
- stream/source isolation;
- immutable fact/member loading;
- anchor verification;
- restored/older catalog mismatch is visible;
- no access to tokens/provider credentials.

## Task 7 — Add per-target Mail and Calendar Full release completeness

### Task 7 files

Mail:

- extend message_ingest/acquisition/microsoft/outlook/email/full_completion.py

Calendar:

- create message_ingest/acquisition/microsoft/outlook/calendar/full_completion.py

Modify narrow tests:

- tests/test_outlook_mail_full_completion.py
- new tests/test_calendar_full_completion.py
- tests/test_calendar_enrichment_planner.py

### Mail

Generalize the existing current-attempt verifier so it can evaluate one target independently as well as the existing all-selected-target authority gate.

Do not weaken rules-enabled Mail delta promotion: its existing workflow finalizer still requires every selected obligation.

### Calendar

Build a per-event Full-v1 verifier from existing:

- profile surface rules;
- resource_version binding;
- attachment inventory/child surfaces;
- recurring series topology requirements.

### Output

Return bounded completion objects containing:

- target identity;
- complete flag;
- terminal-with-limitations flag;
- exact required fact identities/locators;
- bounded limitation codes.

Do not return arbitrary provider payload.

### Task 7 tests

Prove one target can be complete while a second target in the same run is incomplete/failed.

## Task 8 — Add non-authoritative natural-idle release finalization

### Task 8 files

Create:

- message_ingest/extensions/handoff.py

Modify:

- message_ingest/settings.py
- resource Spider update_settings only where the generic extension must be disabled/enabled differently
- tests/test_handoff_release_extension.py

### Task 8 ownership

The extension handles only non-authoritative release subjects:

- Mail discover;
- Mail Full per message;
- Calendar discover;
- Calendar window;
- Calendar Full per event;
- To Do discover;
- Contacts discover;
- OneDrive discover;
- OneDrive content per item.

Authority paths remain owned by existing promotion stores/extensions.

### Task 8 lifecycle

Use spider_idle because native idle proves request/item-pipeline drain.

Do not use extension priority as signal-handler order.

Release only when the resource-specific completion proof is present.

Examples:

- Mail discover: pagination exhausted or explicit max-pages truncation.
- Calendar window: exact scope + pagination_exhausted.
- To Do/Contacts discover: durable traversal completion proof must be available; if discover currently lacks durable terminal proof for a scope, add the smallest explicit completion item/store rather than infer from close reason.
- OneDrive discover: drive + root-child pagination completion proof.
- Full: per-target verifier.

This task may require adding terminal completion markers for additive spiders that currently only end naturally. Those markers are control proof, not A2 entries.

### Critical tests

- clean Calendar JOBDIR pause creates no release;
- resumed window creates one idempotent group;
- explicit Mail truncation releases positive data with truncated coverage;
- callback/item error blocks the affected traversal group;
- multi-target Full can release one complete target independently;
- direct scrapy crawl and public Microsoft command produce the same release semantics.

## Task 9 — Integrate atomic authority releases

This task can be split in parallel by provider after Tasks 1-5.

### 9A Mail

Modify:

- message_ingest/sync/microsoft/outlook/email/promotion.py
- message_ingest/catalog/stores/microsoft/outlook/_email_lifecycle.py
- message_ingest/sync/microsoft/outlook/email/checkpoints.py
- message_ingest/extensions/microsoft/outlook/email/checkpoint.py
- message_ingest/extensions/microsoft/outlook/email/folder_checkpoint.py
- message_ingest/commands/microsoft/outlook/sync.py only for the existing deferred finalizer call

Requirements:

- immediate and deferred message-delta paths call the same atomic promotion/release service;
- promotion-derived presence transitions are facts;
- only changed/unreleased-recovery resource impacts become entries;
- folder delta checkpoint + folder transitions + release commit together;
- no global deletion inference from folder membership.

### 9B Calendar

Modify:

- message_ingest/sync/microsoft/outlook/calendar/checkpoints.py
- message_ingest/sync/microsoft/outlook/calendar/state.py

Requirements:

- winning attempt only;
- group/entries share the same explicit BEGIN IMMEDIATE transaction;
- rebaseline removal is fixed-window scope only;
- apply_calendar_delta_state returns/records exact applied transition identities rather than only a count.

### 9C To Do

Modify:

- message_ingest/sync/microsoft/todo/snapshots.py

Requirements:

- _reconcile_presence writes exact transition facts/entries in-session;
- unchanged already released states generate no repetitive work;
- absence skip caused by newer concurrent content does not fabricate an entry.

### 9D Contacts

Modify:

- message_ingest/catalog/stores/microsoft/contacts.py
- message_ingest/catalog/stores/microsoft/_contacts_delta.py

Requirements:

- snapshot and delta share existing generation ordering;
- exact applied/skipped identities are emitted during promotion;
- stale sparse delta observation never becomes a primary entry.

### 9E OneDrive

Modify:

- message_ingest/catalog/stores/microsoft/onedrive.py
- message_ingest/sync/microsoft/onedrive/state.py

Requirements:

- normal delta group references run facts only after checkpoint wins;
- reset uses only winning reset attempt authority_staged facts;
- apply_onedrive_resync_state emits exact applied/absence identities;
- checkpoint and release roll back together.

### Failure injection

Each provider needs an injected release-write failure test proving the prior provider authority state/cursor remains unchanged.

## Task 10 — Qualify the complete A1 release feed

### Task 10 files

Create:

- tests/test_a1_handoff_end_to_end.py

Modify documentation only after tests pass.

### Test matrix

Exercise through real Scrapy crawl/command paths:

- Mail discovery normal and truncated;
- Mail cache replay;
- Mail immediate delta;
- Mail rules-enabled deferred delta + Full;
- Mail folder delta;
- Calendar discovery/window/JOBDIR resume;
- Calendar delta normal + 410 rebaseline;
- Calendar Full multi-target partial success;
- To Do discover/sync;
- Contacts discover/sync/delta;
- OneDrive discover/delta/410/content;
- Profile produces no release entries.

For each, verify exact stream, group, entries, facts, source_state_key behavior, and authority atomicity.

Run a machine check that all 17 installed Microsoft Spiders remain covered by the release/non-release matrix.

## Task 11 — Migrate Phase 1 neutral persistence to schema v4

### Task 11 files

Modify:

- msgloom/contracts/enums.py
- msgloom/contracts/models.py
- msgloom/persistence/models.py
- msgloom/persistence/records.py
- msgloom/persistence/schema_store.py
- msgloom/persistence/store.py
- msgloom/persistence/async_store.py
- msgloom/persistence/semantic.py

Create:

- msgloom/preparation_pipeline/intake_models.py
- msgloom/preparation_pipeline/intake_codec.py
- tests/phase1_foundation/test_preparation_intake_persistence.py

### Task 11 schema

Add v4 tables for:

- preparation intake cursors;
- preparation intake workset metadata if not represented solely as StageResult;
- durable pending/terminal intake-workset state;
- any bounded held-entry disposition index needed for operator/replay queries.

Keep one current cursor row keyed by:

- A1 catalog identity;
- source_id;
- stream;
- consumer kind/version.

Store:

- last_release_entry_seq;
- last_release_entry_digest.

### Claim

Add ClaimKind.PREPARE_INTAKE.

Do not replace ClaimKind.PREPARE.

### Semantic result

Register preparation_intake_workset@1.

The immutable workset contains:

- A1 catalog identity;
- source_id/stream;
- previous and cutoff anchors;
- ordered admitted release-entry refs;
- CollectedSelection ResultRefs for readable primary records;
- typed transition inputs;
- held entry dispositions;
- configuration/code version and stable consumer_id.

### Migration

Implement exact v3 -> v4 only.

Tests prove:

- new DB creates v4;
- exact v3 migrates to v4;
- partial/unknown table sets fail closed;
- v2 does not skip directly to v4 unless the existing explicit migration chain is intentionally executed and tested;
- migration preserves all existing StageResults/claims/outcomes/reconciliations.

## Task 12 — Implement release-aware exact source reconstruction

### Task 12 files

Modify/create:

- msgloom/sources/handoff_catalog.py
- msgloom/sources/reader.py
- msgloom/sources/_catalog.py only where shared exact evidence helpers remain valid
- msgloom/sources/_assemble.py
- msgloom/sources/_outlook.py

Add:

- Calendar adapter modules as appropriate
- tests/source_reader/test_release_aware_reader.py
- tests/source_reader/test_calendar_release_reader.py

### Task 12 rules

- No call to list_versions() for scheduled intake.
- Release source_version_locator resolves exact immutable evidence/fact associations.
- OneDrive scheduled versions use evidence/capture locator, never current pseudo-version.
- Mail component assembly uses exact facts named by the release entry, never whatever surfaces/attachments are current later.
- Calendar adapter is release-aware from its first implementation.
- Scoped transitions return typed transition input rather than pretending a deleted source payload exists.
- Historical supporting-context read remains explicit and pins an exact version.

### Compatibility

Existing manual LIVE/REPLAY reader APIs remain working for their documented uses. Do not silently change manual VersionRef semantics in the same task unless required by an explicit compatibility test.

## Task 13 — Implement A2 preparation intake service

### Task 13 files

Create:

- msgloom/preparation_pipeline/intake.py

Modify:

- msgloom/preparation_pipeline/__init__.py
- msgloom/persistence/store.py
- msgloom/persistence/async_store.py

Tests:

- tests/test_preparation_intake.py
- tests/test_preparation_intake_recovery.py

### Intake algorithm

For one configured source/stream:

1. acquire PREPARE_INTAKE claim;
2. read/verify prior cursor anchor;
3. choose bounded release-entry cutoff;
4. load exact entries/facts;
5. for each entry:
   - reconstruct and persist exact CollectedSelection result, or
   - create typed transition input, or
   - record held disposition;
6. build immutable preparation_intake_workset@1;
7. call finalize_preparation_intake():
   - revalidate live claim;
   - require unchanged prior cursor;
   - append workset semantic data/result;
   - insert durable pending-workset state;
   - advance cursor to cutoff seq/digest;
   - commit one short transaction;
8. finish intake claim.

Intake does not run the parser/filter/group producer while holding the intake
claim. Its responsibility ends once the exact pending workset and cursor are
durable.

### Determinism

Result IDs for a release entry + exact fact set + stable consumer_id + current
configuration/code version are deterministic so a retry can reuse already saved
selection results.

### Cancellation

Follow existing Phase1Persistence behavior: accepted blocking DB work drains
before cancellation propagates. Cursor cannot advance without workset + pending
state commit.

### Task 13 tests

Prove:

- fixed cutoff excludes later concurrent A1 release;
- crash before finalization leaves cursor unchanged;
- crash after finalization leaves a discoverable pending workset;
- retry reuses selection results safely;
- held bad entry allows cursor progress only after workset disposition is durable;
- workset/pending-state/cursor transaction rollback is atomic;
- stale/expired intake owner cannot finalize;
- configuration/code changes do not silently create a fresh source cursor;
- two streams sharing one source ID advance independently.

## Task 14 — Add scheduled PREPARE composition without changing the scheduler boundary

### Task 14 configuration

Add a closed preparation intake target model under trusted preparation config:

- source_id;
- stream;
- stable consumer_id;
- enabled flag or presence-as-enabled;
- per-intake max entries bounded by global preparation max_records;
- bounded pending-workset processing budget.

Do not put credentials or provider account material into this config. Ordinary
parser/filter/config version changes must not change consumer_id.

### Invocation model

Do not overload PreparationMode LIVE/REPLAY with intake semantics. Add a
separate finite scheduled-preparation invocation/handler path under the existing
PREPARE capability.

The external scheduler still launches one normal finite CLI command; no in-
package daemon or detached queue worker is introduced.

### Scheduled flow

    trusted config
       -> discover durable pending worksets
       -> process pending worksets through exact REPLAY plans
       -> bounded intake target(s)
       -> save new immutable pending workset(s) + advance cursor(s)
       -> optionally process newly created pending worksets within run budget
       -> return terminal operation outcome

Pending workset processing:

1. loads the immutable intake workset;
2. builds the exact PreparationPlan in REPLAY mode from saved
   CollectedSelection ResultRefs;
3. invokes the existing PreparationHandler;
4. on accepted terminal COMPLETE/INCOMPLETE outcome, records terminal workset
   processing state and exact result refs;
5. on FAILED/CANCELLED/duplicate BLOCKED work, leaves the workset pending unless
   an explicit bounded policy records a terminal operator disposition;
6. continues to respect configured budgets so one bad pending workset does not
   monopolize all later scheduling forever.

If one scheduled invocation contains several source/stream targets, process
them deterministically and keep each cursor independent. A failure in one
target must not fabricate progress for another.

The first implementation should process intake targets sequentially. Parallel
provider integration during development is encouraged; runtime SQLite intake
parallelism is not required until contention evidence justifies it.

### Task 14 files

Likely modify/create:

- msgloom/configuration/models.py
- msgloom/configuration/composition.py
- msgloom/configuration/loader.py
- msgloom/cli/models.py
- msgloom/cli/composition.py
- msgloom/cli/runner.py
- msgloom/preparation_pipeline/scheduled.py
- msgloom/preparation_pipeline/models.py only for shared exact-plan helpers, not
  a new INTAKE PreparationMode

Tests:

- configuration strictness and stable consumer_id;
- scheduled invocation with no pending/new work;
- pending workset restart after prior preparation failure;
- new intake followed by exact replay preparation;
- manual LIVE/REPLAY compatibility;
- authority/admission deny-by-default;
- no nested event loop;
- no background work after command exit.

## Task 15 — End-to-end qualification, documentation, and closeout

### End-to-end scenarios

1. Empty historical DB, collect one new Mail message, scheduled intake, prepare once.
2. Historical DB already populated before ledger, future-only baseline, unchanged old records do not appear as new work.
3. Explicit historical baseline produces one immutable starting workset.
4. Failed A1 run writes advanced state/fact but no release; successful equivalent retry releases it exactly once.
5. Older concurrent run finishes after newer run; old state never becomes a later entry.
6. Large To Do/Contacts snapshot creates one atomic release group with more entries than one A2 intake; several bounded worksets drain it without loss/duplication.
7. A2 crashes after selections saved but before cursor finalization; retry is safe.
8. A2 cursor/workset commit succeeds but preparation later fails; the pending
   workset is rediscovered and retried without cursor rewind.
9. A1 catalog restored behind cursor; anchor mismatch blocks intake.
10. Corrupt/missing evidence creates held entry disposition, later entries can still progress.
11. Mail folder removal and Calendar window removal stay scoped.
12. Rules-enabled Mail authority does not release before all required Full obligations.
13. A1 continues collecting after A2 cutoff; new entries wait for next intake.

### Gates

Run:

- full A1-focused suite;
- full normal Python 3.13 suite;
- serial exclusive-state suite;
- FastMCP compatibility suite;
- Python 3.12/3.13/3.14 matrix;
- Ruff check;
- Ruff format check;
- Pyright;
- Scrapy contracts;
- git diff --check;
- pre-commit;
- reverse dependency check confirming message_ingest does not import msgloom.sources/preparation.

### Documentation

Update:

- docs/notes/a1-closeout.md with additive handoff extension status without reopening source-capability closeout;
- docs/phase-1/architecture.md collection/preparation boundary;
- docs/component-layout.md;
- docs/README.md;
- operator scheduling/configuration documentation;
- the handoff design status to implemented only after all gates pass.

### Commit policy

Use small TDD commits at each task boundary.

Do not combine all provider integrations into one unreviewable commit.

Suggested commit sequence:

1. Add A1 handoff ledger core
2. Add Mail handoff facts
3. Add Calendar handoff facts
4. Add To Do and Contacts handoff facts
5. Add OneDrive handoff facts
6. Add release feed reader
7. Add Full release completeness
8. Add non-authoritative handoff releases
9. Add atomic authority releases
10. Qualify A1 handoff feed
11. Add Phase 1 intake persistence v4
12. Add release-aware source reconstruction
13. Add preparation intake service
14. Add scheduled preparation intake
15. Close A1-to-A2 handoff implementation

## Implementation review checklist

Before declaring the plan implemented, independently verify:

- every current Microsoft Spider is covered;
- no release is derived from a mutable current table after its completion transaction;
- no state advancement can commit without its fact;
- no authority can advance without group/entries;
- authority_staged facts cannot leak;
- release-time freshness rejects delayed stale completion;
- unchanged already released snapshots do not churn A2;
- failed-run equivalent recovery works;
- large groups are pageable via entries;
- A2 cursor/workset/pending-state finalization is short and atomic;
- admitted pending work remains discoverable until terminal processing;
- SavedSourceReader exact replay remains intact;
- Calendar support is explicit;
- manual preparation LIVE/REPLAY still works;
- scheduled intake performs no detached/background work;
- external scheduler remains outside the package.
