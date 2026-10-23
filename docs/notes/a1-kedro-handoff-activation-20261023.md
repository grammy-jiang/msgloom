# A1 committed output → automatic Kedro A2 activation

**Status:** SOURCE-VERIFIED DESIGN PROPOSAL; no runtime changes or deployment.
**Date:** 2026-10-23 (Australia/Sydney).
**Current code base:** master 895fc40a0ec889bd96f620df8c62491787218217.
**Formal upstream A1 qualification:** Task 15 source 34057c6c9f85688fd2bd1868d90302ab5a61205f.
**Owner decision:** [Kedro is A2's primary ETL](../decisions/2026-10-23-a2-kedro-primary-etl.md).
**Related design:** [Kedro A2 architecture](../plans/2026-10-23-a2-kedro-native-design.md).
**Automatic deployment tasks:** [A1 release-to-Kedro plan](../plans/2026-10-23-a1-release-to-kedro-auto-handoff.md), including AUTO-01 through AUTO-14 acceptance gates.
**Scope:** actual A1 emitted data and deployment activation, not A1 code refactoring.

## 1. What A1 actually publishes

A1 is the Graph-over-Scrapy acquisition engine (Scrapy 2.19.0). A crawler success or Spider close alone **is not proof of a downstream release**. Provider facts, effective-state/authority gates and their scoped release are validated and committed in the A1 catalog.

The transaction-owned release writer at `message_ingest/catalog/stores/handoff.py: _release` persists:

- immutable `ReleaseGroup` with source/stream, release_kind, coverage_kind, owner run, scope, profile and limitation codes;
- ordered `ReleaseEntry` impact rows with monotonically increasing `release_entry_seq`, digest, resource role and immutable fact memberships;
- source-evidence locators and scope/freshness semantics linked by fact IDs and digest (not raw bodies or arbitrary filepaths in release entry payload).

Seven accepted streams are `outlook_mail`, `outlook_calendar`, `todo`, `contacts`, `onedrive`, `teams_chat` and `teams_channel`. Of the 20 installed Spiders, `microsoft_profile` has no downstream release and `microsoft_teams_notification_reconcile` contributes scoped changes to the two existing Teams streams; it creates no third Teams A2 stream. The publisher's `released_at` is not provider chronology, and a Spider logical run_id is not a universal A2 processing batch.

**Read API:** `ReleaseSourceReader.read_entry(ReleaseEntryRef)` validates exact catalog/seq/digest and reconstructs `ReleasedInput(reference, selection, components, contexts, transitions, facts)`. It verifies evidence/observation/content capture and never silently substitutes a current mutable projection.

`CollectedSelection` binds `source`, `selection`, and `record`. Its immutable `CollectedRecord` includes source VersionRef, source_scope, PreparedSourceType, semantic_identity, aware observed_at/source_time, subject, sender, author, recipients, source_content_kind and saved source bytes, primary/alternate bodies, attachments, native relationships, metadata, source locations and limitations. The body/alternate `CollectedBody.saved_bytes` may identify a whole Graph envelope **rather than the body text**: an exact derived text artifact must be created before parser dispatch, with its own digest and lineage.

These structures are documented in `msgloom/sources/{handoff_models,release_models,models}.py` and `msgloom/sources/release_api.md`.

## 2. Existing downstream admission contract (do not redesign)

`PreparationIntakeService.run(IntakeScope, ...)` currently does:

1. Anchor a trusted `A1CatalogIdentity` and one stable `(source_id, stream, consumer_id)` consumer scope.
2. Check the previous cursor's seq/digest against the current A1 catalog, reject a restored/replaced catalog behind the cursor, and capture an **upper release sequence cutoff**.
3. Read a bounded page of exact release refs after the previous cursor, each through `ReleaseSourceReader.read_entry()`.
4. Admit `ReleasedInput.selection` and all `components` as immutable `collected_selection@1` results; do **not** turn `contexts` into primary work. `control_context` and Teams component-only facts may instead produce exact `context_refresh` transitions.
5. Keep typed scoped transitions and `held` unmaterializable evidence dispositions rather than invent absent bodies. Preserve scope, provenance and limitation reasons.
6. Commit one immutable `PreparationIntakeWorkset` result, the pending index and cursor **together**. A cursor means durable work admission, NOT completed parsing.

Workset fields: `scope`, `previous`, `cutoff`, `entries`, `selections`, `transitions`, `held`, `configuration_version`, `code_version`, and separately approved historical-baseline fields. Its `selection_refs` list is a deterministic set of accepted `collected_selection@1` ResultRefs. No second workset, checkpoint, event log or database belongs in Kedro.

The existing `prepare-scheduled` operation considers pending work first (durable rotation prevents one failure monopolizing attempts), then admits a bounded new page. A failed A2 attempt does **not** rewind the cursor; subsequent finite operations reopen the accepted exact selection. New A1 releases after the captured cutoff remain for a later invocation.

**Critical implementation seam:** `msgloom/preparation_pipeline/scheduled.py:_process()` currently creates the *legacy* `PreparationHandler` for each plan batch. The new integration replaces this producer/composition call with an accepted Kedro-primary producer. It does **not** replace `PreparationIntakeService`, frozen workset/cursor/held semantics or source-reader logic. Scope-limited transitions retain their own proof/claim and are executed through a Kedro-owned transition lane backed by the existing trusted publisher.

## 3. Grounded end-to-end example

A representative test, `tests/test_a1_handoff_scheduled_e2e.py::test_native_mail_scheduled_intake_prepares_once`, uses a native local Mail acquisition fixture:

- A1 emits **one** `outlook_mail` resource ReleaseEntry for the exact message, with `coverage_kind=complete` and an immutable ReleaseEntryRef.
- `ReleaseSourceReader.read_entry()` reconstructs the message's `CollectedSelection`; its subject matches the fixture and `load_saved_bytes(source_bytes)` equals the captured raw evidence.
- A2 intake saves `PreparationIntakeWorkset.entries=(entry.reference,)`, exactly one selection, no held entry or transition, previous anchor at seq 0, cutoff at the released entry and matching durable cursor.
- The saved `collected_selection@1` semantic payload equals `ReleasedInput.selection` **exactly**.
- The existing legacy producer publishes one `prepared@1` with `input_refs[0] == selection_ref`. This is oracle evidence, **not** a requirement to reuse its internal engine or preserve `prepared@1` forever.
- A second scheduled run returns COMPLETE with no output refs, proving the accepted intake does not replay the completed work spuriously.

**Current-base focused verification:** On this planning branch, `/home/grammy-jiang/Projects/msgloom/.venv/bin/python -m pytest -q tests/test_a1_handoff_scheduled_e2e.py::test_native_mail_scheduled_intake_prepares_once` passed (1 passed in 6.93s). This only verifies the existing implementation. The new Kedro producer is not implemented or qualified.

## 4. Kedro should connect at exactly this point

Architecture:

    A1 native Scrapy
       -> raw immutable saved evidence + scoped authority/fact
       -> committed A1 ReleaseEntry + digest
       -> ReleaseSourceReader (no provider fetch)
       -> PreparationIntakeService -> durable immutable Workset + cursor/pending
                            ^ this is accepted upstream authority
                            |
              ===== Kedro ETL consumer boundary =====
                            |
       Trusted DataCatalog[workset result / exact selection]
       -> parse planning, saved-byte verification and isolated parsing
       -> normalization, source-span mapping and content zoning
       -> native relationships, filtering and grouping
       -> claim-fenced versioned A2 stage datasets
       -> exact accepted workset manifest (msgloom validity check)
       -> A3 typed input adapter

The Kedro graph owns the **ETL dependency ordering** from the pinned workset to stage-result datasets, not merely two pure calculations. It does not acquire the release or advance the cursor; those are committed before Kedro starts.

For Kedro 1.7.0 (official source version; candidate not installed):

| Kedro primitive | Proposed integration | Qualification concern |
| --- | --- | --- |
| `Pipeline`/`Node` | Explicit pure transformations and validated typed requests/values; dependencies encode order | No dynamic provider-ID-based names or hidden current-state lookups |
| `DataCatalog` | Programmatic, invocation-scoped datasets, only already-approved exact refs and bounded ordinals | `DataCatalog.get(...fallback_to_runtime_pattern=True)` can otherwise silently create MemoryDataset; assert full graph/catalog allowlist |
| `AbstractDataset[save type, load type]` | Trusted `ParserRequest -> ParsedParts` and `SemanticPayload -> AcceptedStageRef` adapters: Kedro orders I/O while msgloom service owns execution and durability | Exceptions/dataset repr in Kedro error wrappers may expose content; redact by type/codes and don't log raw values |
| `MemoryDataset` | Only bounded immutable intermediate values; explicit copy mode after test | Default inference uses deepcopy on most custom objects; measure Pi RSS |
| `SequentialRunner(is_async=False)` | Topological, one node at a time, all dataset load/save synchronous **in owned worker** | Async Application loop never blocked; `is_async=True` does not await coroutine nodes |
| `runner.run()` | Executes finite graph; then independently load/reconcile exact durable output manifest | Returns output Dataset objects, **not** a business completion proof; on exception it raises and may release intermediate datasets |

The official Kedro 1.7.0 `AbstractDataset` supports differing input/save and output/load types. A candidate dataset can therefore `save(ParserRequest)` by invoking the existing **bounded** parser service and `load() -> ParsedParts` for the downstream normalization node. This is a conscious I/O adapter, **not** a parser hidden in a supposedly pure business Node. Likewise a `ClaimFencedSemanticDataset` may `save(SemanticPayload)` through the existing SQL transaction and then `load() -> AcceptedStageRef`. It must be proven by a minimal isolated PoC before assuming stage saves can round-trip under failure/release/cancellation.

The official runner's Task path is: catalog.load inputs -> invoke synchronous node -> catalog.save outputs -> release ephemeral datasets after last use. Thus Kedro really sequences the data flow, but side-effect completion **cannot** be inferred from a green node or a returned dictionary. An accepted stage ResultRef must already have been committed by the trusted dataset transaction and verified by msgloom before the workset is completed.

A2 still has an async public operation. Proposed feasibility proof runs the entire synchronous runner in one owned bounded worker, while I/O adapters call approved async msgloom services via a bounded cross-thread bridge. Verify event-loop heartbeat, cancellation propagation, pending service drain, claim lease validity and no post-deadline writes; do not create a custom async Kedro runner. The bridge is **unproven**, and its failure is an architecture NO-GO, not permission to downgrade Kedro to two trivial pure nodes.

## 5. Automatic and natural A1 → A2 activation

**Separate the wake-up mechanism from correctness.** A1's immutable ReleaseEntry, not a Scrapy close signal, is the ground truth for what may be prepared. The automation mechanism only causes another finite intake attempt.

### 5.1 Preferred initial operation

Deployment-side Prefect (already selected external scheduler in `docs/phase-1/architecture.md`) or an equivalent authorized launcher coordinates:

1. Launch one configured *finite* A1 collection/sync command in its existing process/container.
2. When that attempt terminates, **enqueue/coalesce one A2 wake-up**, even when A1 reports a partial/non-success exit, provided catalog files are accessible. Some independently valid releases may have committed before a later A1 failure.
3. Launch the installed msgloom `prepare-scheduled` finite operation with the configured, stable `expected_catalog`, `source_id`, `stream`, `consumer_id` targets. The new implementation plugs Kedro into its producer dispatch; the Intake API/semantics remain unchanged.
4. The new Kedro Pipeline reads the frozen Workset and prepares only eligible selected entries. Completed output gets claim-fenced persisted results and a final workset receipt; partial/failure remains pending or held as applicable.
5. If the source or pending queue still has eligible work, schedule the next **bounded** invocation. Do not let one CLI call run forever or consume unlimited entries.
6. Repeat once on scheduler startup and periodically at a configurable, conservative recovery cadence to catch lost wake-up notifications and sources collected by other operators. No high-frequency busy polling required.

The wake-up can be coalesced by `(catalog_identity, source_id, stream, consumer_id)`; concurrency and duplicate wakeups are made safe by the existing `PREPARE_INTAKE` and workset claims, durable cursor and idempotent stored selections. **A1 does not import or invoke Kedro**, nor is it forced to wait for full A2 processing to publish a valid release.

The current package has `msgloom prepare-scheduled` and its finite versioned invocation envelope, but **does not deploy the external Prefect flow**. This section is a deployment design, not a statement that event-driven activation already exists.

### 5.2 Why not directly run Kedro from Spider signals?

A Spider close, callback, statistics counter or crawl process exit does not prove a resource set's semantic completion or release authorization. Some A1 work is incomplete/truncated/held; a native callback can precede the final release transaction. Calling A2 from those components risks processing uncommitted or mutable source data, binding A2 to Scrapy internals, and extending A1's lifetime/locks with costly processing. It also violates the accepted no-A1-import-of-A2 boundary.

The release writer in `message_ingest/catalog/stores/handoff.py` commits group and entry rows through an A1 transaction and does not currently expose a durable per-release notification outbox. A push event after commit would be a **hint** (it can be lost if the process crashes after commit and before notify) unless coupled to an additional transactional outbox. Such an outbox would modify already-qualified A1 state and is **not needed** for the first correct deployment. Prefer external invocation completion plus low-frequency catch-up.

### 5.3 Fault and replay examples

| Case | Correct behavior |
| --- | --- |
| A1 run completes but no new Release Entry | A2 intake no-op; no false prepared results |
| One A1 run commits several Release Entries then fails | Wake A2 and process only committed/readable entries |
| A1 writes after A2 captures cutoff | Those entries wait for the next A2 invocation |
| Scheduler loses wake-up after A1 commit | Startup/periodic reconciliation reads release cursor and recovers |
| Same wake-up delivered twice or A2 overlaps | Workset/consumer claim prevents duplicate acceptance; retry explicit |
| A2 crashes after cursor+workset commit | Workset remains pending and resumes from saved selection, **no cursor rewind** |
| Saved component evidence missing | Held or partial with exact reason; later good entries still progress |
| Scoped deletion/restoration | Explicit typed transition result; no invented global absence or document text |
| Existing A1 release but no default historical baseline | Future-only policy unless explicit historical approval |

### 5.4 Acceptance for automatic activation

- Native A1 fixture first commits a release, then external launcher calls the finite A2 operation; no manual copying of SQLite rows, schema or input files beyond configured invocation.
- Repeated/overlapping wake-up after identical release yields no duplicated accepted output; one stable consumer ID survives restart.
- Simulated crash in A1 between release commit and wake-up is recovered by a catch-up invocation.
- Simulated A1 partial failure still processes an independently committed source release and never processes uncommitted facts.
- Batch/page boundaries, correct cutoff and held/pending retry remain true under new Kedro producer; include all 13 Task 15 invariants without relabeling the historical exact-SHA acceptance.
- No direct A1 import of Kedro, Scrapy signal coupling, new Graph permissions, external bytes fetch or in-package daemon.
- A2 output is fully versioned and accepted for A3 consumption, or remains explicitly blocked/incomplete; the new engine is only released after an independent exact-source audit.

## 6. Implementation seam and review gates

D0: fix the user authority: **Kedro is main ETL**, not old-A2 migration.
D1: freeze the real ReleaseEntry/ReleasedInput/CollectedSelection/PreparationIntakeWorkset mapping in the schema, including context/transition/held shapes.
D2: prove the Kedro 1.7 programmatic DataCatalog/Runner/AbstractDataset lifecycle and asynchronous bridge on isolated synthetic input.
D3: produce a new explicit deployment wake-up and catch-up integration task; keep Prefect external to the package.
D4: independent design review of the entire Kedro-primary DAG **and** activation semantics.

First source-code change after successful D4/Q0 must not be an A1 edit. Work in new A2/dataset/launcher owners, replace only legacy producer dispatch when new Kedro runs correctly, and retain rollback before deleting old A2. Dated Kedro dependency security risks remain a separate mandatory gate.

## 7. Direct source evidence

- `message_ingest/acquisition/handoff.py`: the 7 AcquisitionStream values, release facts and completeness.
- `message_ingest/catalog/stores/handoff.py:_release`: idempotent release writer under caller's transaction.
- `msgloom/sources/release_models.py`, `handoff_models.py`, `models.py`, `release_reader.py`: immutable read contracts and safe exact evidence.
- `msgloom/preparation_pipeline/intake.py`, `intake_models.py`, `scheduled.py`: finite intake, workset/cursor, pending/held/claims and legacy producer dispatch seam.
- `docs/notes/operator-configuration.md#scheduled-preparation`: stable target/consumer configuration and finite CLI invocation.
- `docs/phase-1/architecture.md`, `docs/microsoft-change-notifications.md`: external Prefect and notification-hint semantics.
- `tests/test_a1_handoff_scheduled_e2e.py`: native A1 fixture -> exact release -> frozen selection -> durable output -> no duplicate second invocation.
- Kedro 1.7.0 official: `kedro-org/kedro` tag 1.7.0, `docs/getting-started/architecture_overview.md`, `docs/build/run_a_pipeline.md`, `kedro/io/core.py`, `kedro/io/data_catalog.py`, `kedro/io/memory_dataset.py`, `kedro/runner/{runner,task,sequential_runner}.py`.

**No real A1 credentials or tenant data were used for this analysis. No code, dependency lock or external schedule is changed.**
