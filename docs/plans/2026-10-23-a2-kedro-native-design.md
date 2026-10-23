# A2 Kedro-native preparation architecture

**Status:** DESIGN CANDIDATE; no production-code implementation authorised by this document.
**Date:** 2026-10-23 (Australia/Sydney).
**Planning base:** master/origin/master at 895fc40a0ec889bd96f620df8c62491787218217.
**A1 handoff qualification authority:** 34057c6c9f85688fd2bd1868d90302ab5a61205f; 28/28 exact-SHA automated gates and separate accepted review.
**Owner:** msgloom Phase 1 / A2. **Implementation plan:** 2026-10-23-a2-kedro-native-implementation-plan.md.
**Readiness evidence:** ../notes/a2-kedro-readiness-audit-20261023.md.

## 1. Decision and precedence

Implement a new Kedro-native A2 deterministic preparation execution path, not a line-for-line migration or a wrapper around the existing PreparationHandler. The present A2 implementation is the reference corpus for functional contracts, regression fixtures, source-level threat analysis, and rollback. Shared *capabilities* can be reused when their interfaces are sound: immutable data contracts, verified byte readers, format parsers and isolation, prepared/filter/group pure semantics, persistence and claims. Do not copy the legacy RecordSteps/StageSteps/handler sequencing into new Kedro nodes.

The accepted A1-to-A2 contract owns upstream semantics. It outranks this design if conflict is discovered; any requested contract extension requires explicit review rather than an opportunistic A1 modification. The stable baseline includes:

- A1 source catalogue and verified raw evidence; immutable acquisition facts;
- atomic release groups and sequenced release entries;
- ReleaseSourceReader and its exact, read-only reconstructable ReleasedInput;
- bounded PreparationIntakeService, catalog-identity anchored cursor, immutable workset, historical-baseline API, held entries and pending rotation;
- Phase1Persistence, stage-result codecs, claim fencing, semantic versions and replay.

The September 29 local plan at program/kedro-a2-plan (commit c7dcb41, 648 lines) was explicitly a *legacy-engine migration* plan pinned to Kedro 1.6.0. Its K0–K8 migration sequence, A2_ENGINE two-engine runtime, and 25% legacy-code deletion criterion are NOT the governing new implementation plan. Retain its useful framework constraints and benchmark criteria, not its migration authority.

Higher-level product intent is in docs/phase-1/design.md sections 2–3 and docs/plans/msgloom-next-implementation-program.md section 14 and P2. The latter is a 2026-09-29 execution baseline, not a reliable inventory of current code. docs/notes/preparation-pipeline-api.md and docs/notes/preparation-semantics.md describe the currently implemented **reference** semantics. docs/superpowers/specs/2026-10-03-a1-a2-handoff-contract-design.md, the Task 15 report, and msgloom/sources/release_api.md govern the accepted source boundary. This design controls the new A2 execution implementation only.

## 2. Explicit scope / non-goals

A2 turns an already authorized, durably frozen collection into source-mapped, limited, replayable prepared content, deterministic filter decisions, and conservative relationship groups. Inputs may be Outlook Mail, Calendar, Teams chat/channel, To Do, OneDrive or Contacts. Supporting source context must not silently enter the primary workset. No A2 semantic model or NLP guesses about conversation identity.

Not in this work: new Graph endpoints/permissions; Scrapy traversal, middleware, JOBDIR, checkpoints, or existing A1 schemas; A3 model inference; semantic cross-source topic/entity linking; A4 investigation; A5 delivery; a Kedro project, session, CLI, YAML configuration, data persistence, plugin discovery, hooks, daemon, scheduler or browser UI; live enterprise Teams tenant acceptance. The external Prefect scheduler remains deployment-owned, and no scheduler deployment is required to qualify this A2 replacement.

Keep msgloom's one async Application/CLI boundary. Installation and imports must not cause IO, network access, spontaneous service startup, or telemetry. Offline manual preparation and the finite prepare-scheduled command must both remain supported.

## 3. Component ownership

| Owner | Responsibility and failure boundary |
| --- | --- |
| A1 (message_ingest/microsoft_graph) | Capture with native Scrapy, persist provider facts/bytes, publish atomic releases. No A2 imports. |
| msgloom.sources | Read verified, immutable ReleasedInput and saved selections by exact IDs; pinned path/integrity checks. No Kedro imports. |
| Existing intake boundary | Durable catalog/source/stream/consumer cursor, workset, held reason, pending fairness, explicit historical baseline. Remains outside Kedro. |
| New A2 controller | Request admission, claim/lease and budget, freeze selected inputs, call parser isolation, invoke bounded Kedro executor, publish and finish. Async and effectful. |
| Parser boundary | Select trusted parsers, check signatures and saved byte digests, isolate native/hostile file parsing in bounded processes, drain on cancellation. No Kedro imports needed. |
| New Kedro Core subgraph | **Pure deterministic** normalization, prepared-record assembly, filter evaluation, relationship analysis, group construction, canonical output assembly. No IO or claims. |
| msgloom.persistence | Serial durable publication, per-result claim fencing, immutable semantic/result IDs, dependencies, completion receipts and terminal lifecycle. No arbitrary Kedro dataset I/O. |
| A3 and A5 | Consume exact accepted A2 results; their code, prompt behaviour and delivery are unchanged. |
| Deployment | External scheduling, process/container/resource limits and operational secret injection; does not invoke Kedro nodes directly. |

A1's releases and current A2 intake code straddle the historical "A1/A2" naming boundary. Ownership is determined by accepted business semantics, not directory names: do not replace immutable intake or release semantics under the pretext of replacing A2 orchestration.

## 4. Input, intermediate and output contracts

Define versioned, closed, frozen types (prefer existing validated domain types where an exact semantic match already exists). Working names below are proposals; implementation must inspect actual schemas and not duplicate them.

- PreparationIntakeWorkset (existing intake_models.py): the complete immutable source/stream/consumer/cursor cut, exact entry refs, selection refs, transitions, held entries, cutoff and prior anchor. **Do not create A2SourceCut**, which would duplicate this contract.
- A2RecordExecutionInput (new, one selected record): exact accepted CollectedSelection@1 ref and payload, immutable source/version/byte refs, already verified derived_bytes@1 dependencies and accepted isolated parser outputs, parser identity/config/limitations, FilterConfig/version, source-scope and native relationships, and trusted config/code versions. Never include live readers, sessions, DBs, claim tokens or provider credentials.
- RecordTransformOutput (new, one record): immutable PreparedRecord, FilterResult, source spans/limitations and **semantic-version material**; no durable ResultRef or acceptance claim. PreparedRecord.filtering stays PENDING because filter_result@1 is authoritative.
- GroupingInput (new, at most one duplicate-free plan batch): corresponding prepared records and filter outcomes plus exact source scope, canonical ordering and bounded size. No invented relationship graph data type is required.
- GroupTransformOutput (new): tuple of validated GroupResult domain objects with Confirmed / Uncertain / None, source relationships and matched filter evidence.
- A2ExecutionOutput is only a logical aggregate view of per-record and per-batch pure outputs already validated by the controller. **Scoped transitions do not enter Kedro**; the existing prepared_transitions@1 publisher handles workset.transitions in its own claim.

These working type names must map to existing contracts before adding new schemas. An execution envelope is never a new durable checkpoint or source of truth.

Never encode provider IDs, addresses, attachment names, subject text or any private payload into Kedro node names, dataset names, logging labels, metrics or error strings. IDs in authorized immutable payload objects must remain available for business identity and persistence.

ReleasedInput can contain primary selection, components, contexts, transitions and facts **in one release**. A component-only release cannot manufacture a parent; a transition-only release cannot manufacture source bytes or global deletion. A1 provider profiles carry their own completeness and authority boundaries. Confirm source selection remains immutable if mutable A1 projections change during processing.

## 5. Dataflow, batch granularity and partial-result publication

An immutable **PreparationIntakeWorkset** is the durable admission/cursor unit, **not** a single Kedro invocation. Preserve the exact legacy splitting rule in scheduled.py: select source versions in saved order; start a new PreparationPlan whenever the active batch reaches the configured max_records or the next selection repeats a source VersionRef already present in the batch. Never silently deduplicate those repeat releases; each remains associated with its own saved selection and release entry. A manual plan has the same uniqueness and max_records constraints. Grouping scope is exactly one such batch; groups must not span batches or released worksets. Any later change to grouping scope is a separately approved semantic policy/version change.

Each batch has zero or more record-transform invocations followed by **one** group-transform invocation after all eligible record/filter results are durable. This preserves the legacy partial-result lifecycle and avoids making Kedro responsible for SQLite commits.

    A1 ledger -> ReleaseSourceReader -> accepted PreparationIntakeWorkset
      -> exact saved selections (including components) -> split unique batches
      -> for each selected record:
           verify body/alternate/attachment evidence
           -> controller-owned parse planning and isolated parsing
           -> durable derived_bytes@1 artifacts
           -> per-record Kedro pipeline:
                assemble_prepared_record -> apply_deterministic_filters
           -> claim-fenced prepared@1, then filter_result@1 immediately
      -> batch Kedro pipeline:
           validate_group_inputs -> group_records -> GroupTransformOutput
      -> claim-fenced group_result@1 for each exact group
      -> existing transitions path publishes prepared_transitions@1
      -> finalize accepted workset receipt, retain pending/held as needed
      -> A3 from existing accepted ResultRefs

Proposed pure node signatures (use actual domain types, not false no-op nodes):

    def assemble_prepared_record(parsed: A2RecordExecutionInput) -> PreparedRecord: ...
    def apply_deterministic_filters(
        record: PreparedRecord, policy: FilterConfig
    ) -> FilterResult: ...
    def validate_group_inputs(
        records: tuple[PreparedRecord, ...],
        filters: tuple[FilterResult, ...],
    ) -> GroupingInput: ...
    def group_exact_native_relations(groups: GroupingInput) -> tuple[GroupResult, ...]: ...

The existing reviewed apply_filters() and group_records() pure algorithms are the semantic baseline and should be called by the relevant new nodes without an unapproved relationship-graph refactor. The proposed Kedro topology consists of two meaningful pure dependency chains. It is **not** one fictional six-node end-to-end DAG: effectful parser/claim/publish steps remain between the two subgraphs. If this split yields no measurable maintainability benefit, reject Kedro rather than invent extra one-line nodes.

### 5.1 Controller-side parse planning: explicit contract

For each captured exact selection, the controller:

1. Computes a finite component plan from primary body, alternate MIME/HTML/plain bodies, structured collected metadata, saved attachments and declared parser profiles. Only trusted parser configuration chooses a format. Retain all source/byte refs, descriptions and source locations.
2. Loads each saved byte with the already qualified no-follow/digest/byte-limit reader. It must not treat stored Graph JSON as parsed body text under the Graph envelope digest.
3. Generates the derived canonical UTF-8 bytes for each parser input, including structured metadata JSON, saves the exact derived_bytes@1 semantic result **before** parser invocation, and binds its stable sha256/byte-count to the captured selection.
4. Calls the existing bounded parse_isolated interface sequentially per admitted component, records parser identity/config/profile/version, canonical parsed content and source mappings, and retains missing, unsupported, encrypted or inaccessible component limitations. Existing limitation codes (including saved-content-unavailable, content-parse-failed, parser-profile-unavailable, unsupported-attachment-format) remain unchanged.
5. Enforces **both** per-item and aggregate max_total_selected_bytes, max_derived_bytes, max_total_derived_bytes and max_total_parser_output_bytes, plus parser subprocess memory/CPU/output/time/decompression/container ceilings. Aggregate budget exceedance is fatal and cannot be transformed into a benign per-component limitation.
6. Produces exactly one frozen A2RecordExecutionInput with the already verified outputs and ordered limitations, not a mutable list of callbacks. No parse IO is hidden in a Kedro node.

These are the behaviours formerly implemented across `record_steps.py:_prepare_record`, `_parse_derived_body`, `_parse_derived_text` and `_parse`. They must be preserved as contract, not copied wholesale as old class inheritance. Byte-loss after selection is honest INCOMPLETE and never triggers reacquisition or substitution.

### 5.2 ReleasedInput-to-workset-to-DAG mapping

| ReleasedInput field | Accepted workset mapping | New A2 action | Published result |
| --- | --- | --- | --- |
| reference + facts | Exact entry refs, anchor and evidence-verified membership; not an independent mutable input | Verify frozen identity/selected version via workset and selection refs | Lineage in prepared and transition refs |
| selection | IntakeSelection with collected_selection@1 result when present | Read exact selection, parse authorized content | prepared@1, filter_result@1, group_result@1 in batch |
| components | Separate IntakeSelection/collected_selection@1 refs; Teams side facts additionally produce parent refresh | Prepare **only** each exact component selection as selected; do not fabricate an absent parent | Exact prepared result if readable; scoped refresh separately |
| contexts | Not copied into workset as primary data | Preserve only via A1 evidence; control_context facts map to context_refresh; explicit historical context uses read_supporting_context | No invented primary PreparedRecord |
| transitions | Workset.transitions (typed IntakeTransition) | Existing prepare_transitions bypasses Kedro | prepared_transitions@1 under separate transition claim |
| facts with component_observation | Teams chat/channel side-component context_refresh transition where applicable | Preserve exact parent/scope and no new primary message assumption | Scoped refresh only if no selected primary |
| invalid/unmaterializable entry | Workset.held entries | Existing held disposition, allow later good entries | Held without fabricated content |

Only these already defined workset paths feed the Kedro DAG. Additional A1 context read semantics require a separately approved extension, not adding a fictional workset field. A release entry may have selections **and** transitions; both must be retained.

### 5.3 Partial failure and durable progress

After each successful per-record DAG call, save prepared@1 then filter_result@1 immediately under the record's PREPARE claim; do not wait for the entire workset. Previously accepted per-record refs survive a later parser failure, group-stage failure, timeout or cancellation and remain inspectable/replayable. If a per-record parse has missing/nonfatal components, publish a partial PreparedRecord with explicit limitations and an INCOMPLETE status; fatal aggregate budget exhaustion publishes no invented completion but retains earlier durable refs.

Group computation begins only with the exact completed prepared/filter results for the current batch; if a later record aborts the batch, preserve the earlier refs and do **not** publish a fabricated complete group. Finish claims according to ownership and durable acceptance; the outer workset remains pending unless the same proof that the old path required is satisfied. This matches tests/preparation_pipeline/test_lifecycle.py (partial timeout) rather than making a single-shot Kedro DAG a transaction.

## 6. Kedro embedded runtime policy

Use only public Kedro Core APIs: Node/node, Pipeline/pipeline, DataCatalog, MemoryDataset and SequentialRunner(is_async=False), constructed programmatically per bounded invocation. No kedro-datasets, KedroSession, Kedro server, Kedro CLI, automatic hooks, runtime config discovery, or second serialization/versioning system. No custom async runner.

Kedro Core synchronous Node execution is **not** coroutine execution; is_async=True on SequentialRunner parallelizes dataset loads/saves with threads, not business node awaits. The entire pure execution may run in an owned bounded worker thread, isolated from the Application event loop. Cancellation of Python threads is not preemptive. This design chooses **bounded cooperative cancellation**, not a new process host or custom Kedro runner. The controller runs at most one finite Kedro call per record or group batch, checks monotonic deadline and stop-flag before admission and between nodes, and disallows new steps if remaining budget is less than an empirically qualified maximum node duration plus cleanup margin. Node entry wrappers check a thread-safe cancellation flag; pure core algorithms remain deterministic and never read mutable business state. Await/drain the already accepted bounded step before returning, discard its result if cancellation or deadline was observed, then enforce claim ownership on any allowed publication. The measured worst-case pure-node drain plus persistence/claim cleanup must be strictly less than `claim_lease_seconds` minus `execution_timeout_seconds` (after the already reserved cleanup margin). If no positive margin exists, the request is rejected before node admission. A node that cannot meet this finite drain bound on Pi is rejected from Kedro adoption, not silently replaced by an unreviewed subprocess design. No worker callback can publish to persistence or outlive the Application operation.

Dataset names and node names are static, reviewed, non-sensitive constants. Construct MemoryDataset(copy_mode="assign") **only** for validated frozen Pydantic/domain objects, never mutable caller lists/dicts; validate absence of alias mutation with explicit tests. Bound materialized bytes and assert RSS under worst-size test fixtures, as default inferred copy mode can deepcopy large records. For mutable fixtures choose a reviewed explicit copy strategy and a smaller byte ceiling. The output is loaded by the controller and independently Pydantic-validated before publication; never trust a forged constructed model merely because it crossed a DAG.

Before importing/using Kedro in executable operations, deployment/test process sets KEDRO_DISABLE_TELEMETRY=1 or DO_NOT_TRACK. Never call versioned Kedro dataset constructors, catalog.from_config, load_obj, the Kedro CLI, hooks or catalog-from-user-config paths. The pinned runtime must prove these exclusions as executable architecture tests before Q0 acceptance, not merely rely on a scratch example. Verify no access to Kedro project/config discovery and no network/telemetry, including subprocess and help/import tests. Avoid auto-loading third-party plugins; inspect Kedro's actual version for hook and plugin behaviour.

**Dependency candidate:** Kedro 1.7.0 (PyPI release 2026-09-28) is the current candidate, not an approved runtime pin. The 2026-09-29 plan's 1.6.0 selection is stale. A new dependency lock change must be a separate reviewed gate. Security registries disagree: Snyk's CVE-2026-3840 marks current releases affected by unsanitized versioned dataset paths, whereas GitHub/GitLab CVE-2026-35167 says the similar path-traversal flaw was fixed in 1.3.0. Require dated code-level resolution on the **exact installed 1.7.0** plus actual no-versioned-dataset/no-untrusted-catalog guards before acceptance. No unreviewed security-ignore exception; the Q0 security owner is the repository owner, who must explicitly approve a dated source/applicability record covering OSV/uv audit, GitHub, GitLab, Snyk, the exact wheel hash, and a production-reachable-path proof. An audit ignore requires a separate explicit owner authorization and documented expiry; if the dependency remains unacceptable, stop adoption and retain current production behaviour. Do not install Kedro as a side effect of this design.

Official evidence:

- <https://pypi.org/project/kedro/1.7.0/>
- <https://docs.kedro.org/en/1.7.0/api/runner/kedro.runner.SequentialRunner/>
- <https://docs.kedro.org/en/latest/build/run_a_pipeline/>
- <https://docs.kedro.org/en/stable/about/telemetry/>
- <https://security.snyk.io/vuln/SNYK-PYTHON-KEDRO-17752561>
- <https://advisories.gitlab.com/pkg/pypi/kedro/CVE-2026-35167/>

## 7. Evidence-preserving parsing

Parser inputs are bytes already saved and verified by A1, never fetched directly from provider URLs or chosen by message content as Python paths. Preserve MIME entities and charset, HTML meaningful order/tables/links, spreadsheet cells/sheets/hidden/formula-vs-value provenance, PDF page mappings and missing layout, and Word block/table relationships; preserve original evidence even for a partially parsed result.

Existing isolated parser interface, resource ceilings and supported parser packages are reusable capabilities; parser failures must have explicit limitation codes rather than empty successful text. Invalid signature, encrypted file, bad container, partial read, size limit and post-selection evidence loss are distinct. No OCR unless explicitly enabled with a supported local profile and separately qualified resources. No implicit native macros/external asset fetches.

Body extraction must retain a reversible source span/location mapping. Quote *occurrence* is not automatically proof of quote *source*. Reply-parent, ancestor and quote-source are different relations. Duplicate Internet Message-ID values preserve ambiguity; abstain rather than invent disambiguation. Do not use research fixture gold in inference. Topic 01 and Topic 02 synthetic accepted research is test methodology, not production-domain accuracy or approval for semantic grouping expansion.

Do not require new A1 provider fields to preserve semantic evidence if bytes and mappings already suffice. If an immutable required fact is truly absent, write a source-contract gap with concrete provider/test proof and classify the impacted A2 behaviour as held/incomplete; never silently fetch it in A2.

## 8. Filtering and grouping rules

Filtering evaluates all strict, versioned deterministic rules and persists every match and conflict. Address normalization is declared; subject operations are bounded string comparisons, not unchecked regexes. Time windows are timezone-aware; source-scope predicates require exact scope metadata. Exclusion preserves the captured source and remains replayable. A guidance-only match cannot overrule a conflict.

Grouping uses only source-native structural evidence and exact scope/version identity. Confirmed edges require an unambiguous present native parent within the same scope. Outlook conversation ID and subject similarities are candidates only. Teams channel rooted replies may confirm. A Teams chat reply confirms a group **only** when an explicit supported teams_chat_reply_to parent is present, resolvable and in the same chat scope; Teams chat membership and time proximity alone cannot. Calendar, To Do, OneDrive and Contacts are contextual and do not create communication groups. Missing or contradictory ancestor/scope remains Uncertain; never confirm across sources or current-state joins. Save reasons and exact supporting relationship evidence. No invented global absence from a folder or Calendar window removal.

Keep context-only observations, component refreshes and scoped transitions distinct from communication groups. Scoped deletion/restoration belongs in prepared_transitions@1, not as fabricated "deleted message" content. Final output must preserve all limitations through A3 and A5 input adapters.

## 9. Durability, replay, claims, deadline and semantic identity

A1 release sequence is admission order, not provider chronology. The intake cursor signifies **durably accepted selection**, not successful parsing. Never rewind it to retry preparation, scan mutable projections to fill gaps, or duplicate workset state inside Kedro.

### 9.1 Claim topology and publication

There are **three existing ownership layers**, none replaced by Kedro:

1. A scheduled workset PREPARE claim from scheduled.py:_process protects the exact PreparationIntakeWorkset receipt and its pending/finalized status.
2. Each duplicate-free PreparationPlan batch obtains its own PREPARE claim through the new controller, mirroring PreparationHandler.run's claim admission. Derived bytes, prepared and filter/group result appends each pass this exact ClaimToken to append_result_with_data.
3. Workset.transitions are published through the separate existing prepare_transitions() claim, with its own exact reference, even when no primary record was materialized.

The workset claim's final accepted_preparation_results manifest includes all completed batch results and accepted transition refs. The result publisher must derive **each ResultRef only after its referenced predecessor write succeeds**, not prefill nonexistent IDs. prepared@1 depends on exact collected_selection and derived_bytes refs; filter_result@1 depends on its exact prepared ResultRef; group_result@1 depends on exact member prepared+filter ResultRefs. The saved workset receipt cannot claim acceptance when any required result is missing or stale. Preserve already saved partial refs if a later step fails.

Use the existing result ID recipe: deterministic sha256 of execution, attempt, stage kind, stable tag, configuration_version, code_version and trusted-plan fingerprint (excluding retry attempt from claim-key identity). Claim writes remain atomically fenced and replay-safe. Idempotent recovery must not double-publish a completed result or silently replace an old immutable history row.

### 9.2 Semantic versions across cutover

Prepared semantic identity is the existing sha256 over (source kind/identity/version identity) and the canonical PreparedDataCodec payload plus the **operator-approved configuration_version and code_version**, matching stage_steps.py:_prepared_version. Parsed-content versions remain bound to the exact selected bytes, parser profile, parser output and existing code/config versions. Filtering and grouping link the correct prepared semantic versions.

**Equal source/content/policy semantics across old and new engines use the SAME code_version and yield the SAME prepared semantic versions.** Different execution/attempt IDs still produce different immutable ResultRefs. The new Kedro engine implementation ID is a nonsemantic diagnostic; do not inject it into the digest simply to force a difference. A meaning-bearing algorithm or policy change requires a deliberately bumped trusted code_version, a changelog entry and a new oracle expectation **before** cutover. This is a controlled version decision, not an automatic code-source hash; no silent semantic reinterpretation or duplicate downstream topics.

### 9.3 Deadline, cancellation and terminal truth table

The controller checks remaining execution budget before every per-record parse and pure Kedro step. It reserves a quantified cleanup margin **inside** the configured claim lease; do not begin if a measured worst-case bounded transformation could overrun that margin. On timeout, stop admitting new work, signal cooperative cancellation, await the already running pure step and parser cleanup and discard any result calculated after the deadline. No late publication ever occurs. No extra thread or callback survives return.

| Condition | Persisted refs | Terminal disposition |
| --- | --- | --- |
| All records, filters, groups and required transitions accepted | All exact refs + accepted workset proof | COMPLETE unless accepted limitations make it INCOMPLETE |
| Missing/unsupported component with other verified content | Earlier and current partial prepared/filter refs, honest limitations | INCOMPLETE; no false parser success |
| Fatal parse/aggregate budget/phase failure | Already accepted earlier record refs; no unfinished group | FAILED (or existing boundary's declared INCOMPLETE for a bounded timeout) |
| Timeout before or during Kedro transform | Earlier saved refs only; no output from step completed after deadline | INCOMPLETE while still owning claim; otherwise FAILED/claim-lost |
| External asyncio cancellation | Drain accepted finite workers and claim cleanup; earlier refs remain | CANCELLED and cancellation re-raised |
| Claim lease expires or another owner supersedes | New write rejected atomically, earlier valid refs intact | FAILED/claim-lost, **never** COMPLETE |
| Unmaterializable A1 release | Exact held entry, later good entries may progress | Held/pending, never fabricated content |

A deadline is a **hard limit on admission/publication**, not a promise of instant thread preemption; process completion may exceed the nominal timeout only for the independently bounded drain. Test CPU-bound worst-size nodes on Pi with deadline expiry before and during the run. Record maximum observed drain latency, required lease margin and no-late-publication evidence. If the bound is not stable, the implementation is **NO-GO** rather than changing to a process design in the same approval.

### 9.4 Replay

Replay loads exact collected_selection and derived bytes, parser and policy versions and source mappings; it never consults current provider projections. Repeated inputs retain stable semantic version, code/config changes only create the documented changed versions, and per-run result IDs remain immutable. A timeout or worker abort does not rewrite the committed intake cursor; rediscover saved pending work. Keep 13 Task 15 scenarios intact without editing the formally qualified runner's original evidence.

## 10. Portability, security and operations

Supported mandatory package runtime/test matrix: CPython 3.12, 3.13, 3.14; Raspberry Pi Linux aarch64, Linux x86_64 with process/cgroup-v2 security as appropriate. Existing Windows smoke is a portability check only: secure A2 saved-source readers rely on POSIX pinning and are **not** qualified as native Windows support (issue #47). Test macOS platform-independent contracts, but do not claim full native parser security coverage until independently qualified.

Do not add broad Graph permissions, data export paths, arbitrary provider/content URLs, or configuration-to-import execution. An operator misconfiguration is a bounded, redacted terminal failure. No model/telemetry/network access in a deterministic A2 test. Budget ceilings include aggregate selected bytes, derived bytes, parser output, record/group count, worker wall time, memory and number of node invocations.

Prefer one clean operation per external scheduler invocation; logging contains execution/correlation IDs and safe limitation codes, never bodies/emails/paths. Preserve existing recoverability and no-detached-work semantics.

## 11. Acceptance and architecture gates

A2 is not accepted by a green Kedro demo. Required proof is mapped in the companion implementation plan and audit. Invariants:

- D1 source matrix: all 20 installed Spiders accounted for, profile explicitly produces no release; Teams fixture-only proof clearly distinguished.
- All seven PreparedSourceType categories and component-only/context-only/transition-only release shapes recognized without invented primary bytes.
- Parser MIME/HTML, Excel, PDF, Word, unavailable/invalid/partial evidence all tested with exact source locations and limitations.
- Zero unreviewed deterministic filter/group differences against the accepted legacy corpus; uncertain and contradictory cases stay uncertain.
- Repeated exact source/policy version yields stable semantic identity; changed content/parser/rules/code versions change the appropriate identity; no fall-forward on replay.
- A1/intake Task 15 13 scenarios remain green, including crash after selection, pending fairness, held entry progression and scoped absence.
- No new A1 import of A2/Kedro; no blocking outer event loop; cancellation, timeout, stale claim, restart and failed persistence produce correct terminal states and no late publications.
- Full CI on supported Python matrix and Linux process-security gate, installed-wheel packaging, Ruff/Pyright/pre-commit, offline import and telemetry/no-network tests.
- Existing A3/A5 end-to-end composition still consumes the published accepted result chain with exact lineage.
- Independent design and source-security review recorded before behaviour switch; reviewer evidence tied to exact commit SHA.
- **Maintainability gate:** baseline at 895fc40 is 1,115 LOC and 89 AST branching constructs in handler.py (368/36), record_steps.py (460/33) and stage_steps.py (287/20). Measure all new A2 controller, parse planner, publisher, Kedro nodes, executor, type adapters and composition-delta Python LOC together (not just "pure DAG" LOC), with the same Python AST branching-count script. Target at most 1,000 new/replacement LOC (>=10% reduction) **and** at most 80 branch constructs (>=10% reduction), without duplicating accepted intake/persistence. Record exceptions as NO-GO unless a later owner-approved design revises the measurement. If the target cannot be achieved, retain the current non-Kedro A2.
- **Performance gate:** compare fixed CPU/RAM and identical offline fixtures; target no material regression over 10% wall time and no unbounded RSS, especially on Raspberry Pi. Record actual values before accepting, not imagined numbers.

## 12. Decisions frozen and open checks

**Frozen:** A1/Intake read-only immutable contract; Kedro Core as target pure A2 DAG; claims/persistence/cleanup external; no second scheduler/state; old A2 stays as independent oracle through development; no permanent parallel engines; no widened grouping semantics or unsupported Windows promises.

**Must be established by independent implementation preflight, not guessed now:**

- Security disposition of Kedro candidate version and transitive lock impact (CVE conflict).
- Actual 1.7.0 DataCatalog/MemoryDataset lifecycle, plugin loading, output reads and memory/copy behaviour under the exact interpreter/runtime.
- Measured bounded pure-transform, cooperative cancellation and lease-margin drain budget.
- Which existing pure schemas/format parsers are reusable without reintroducing old sequencing.
- A2's actual post-cutover integration extension points and exact test node inventory.
- Benchmark baseline and any audited source/evidence field gaps discovered in D1.

Unresolved evidence blocks the affected implementation gate, not A1 closure or independent design analysis.
