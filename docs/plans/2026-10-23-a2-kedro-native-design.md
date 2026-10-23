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

- A2SourceCut: catalog identity, exact ReleaseEntryRef sequence/digest, source/stream/consumer scope, cutoff, held/transition/component entries, immutable workset reference, and whether the cut is explicit historical baseline. No implicit scans or latest-version lookup.
- A2ExecutionInput: immutable, explicitly bounded per-invocation collection of captured CollectedSelection@1 refs and payloads, exact source VersionRefs, verified SavedByteReferences or accepted derived_bytes@1 dependencies, parser outputs and failures, parser identities/profiles/limits, FilterConfig/version, source-scope and structural relationships, transition facts, supporting context references and trusted configuration/code versions. This is *data*, never live reader/session/DB/claim/credentials.
- PreparedBatch: exact PreparedRecord values and source mappings; reference to every valid input component and limitations. Persisted record still has pending filtering; filter_result@1 is authoritative.
- FilteredBatch: canonical filter_result values for each prepared version, all matched rule references, explicit include/exclude/conflict/guidance and no silent deletion.
- RelationshipGraph: typed native adjacency/candidate relations plus distinct confirmation, uncertainty and reason; refer only to exact present, scope-qualified source versions.
- GroupedBatch: canonical groups with status Confirmed / Uncertain / None, method, evidence, members and exactly corresponding filter values.
- A2ExecutionOutput: prepared/filter/group domain values, stable semantic-version inputs, ordered publication graph, source/parsed mapping, incomplete/held classification and transition preparations. It contains **no claim of persistence success**.

Never encode provider IDs, addresses, attachment names, subject text or any private payload into Kedro node names, dataset names, logging labels, metrics or error strings. IDs in authorized immutable payload objects must remain available for business identity and persistence.

ReleasedInput can contain primary selection, components, contexts, transitions and facts **in one release**. A component-only release cannot manufacture a parent; a transition-only release cannot manufacture source bytes or global deletion. A1 provider profiles carry their own completeness and authority boundaries. Confirm source selection remains immutable if mutable A1 projections change during processing.

## 5. Dataflow and canonical processing

One frozen workset is the outer unit of A2 execution. The existing intake service controls the finite release page and captures exact selection@1 before advancing the cursor. Both manual and scheduled callers pass the same trusted A2 controller an exact bounded plan.

    A1 committed release ledger
        -> ReleaseSourceReader + verified saved evidence
        -> durable intake workset and collected_selection@1
        -> parser admission/isolation and durable derived byte inputs
        -> frozen A2ExecutionInput
        -> Kedro Core: canonicalize_records
                     -> assemble_prepared_records
                     -> evaluate_filters
                     -> analyse_native_relationships
                     -> form_groups
                     -> assemble_execution_output
        -> claim-fenced publisher of prepared@1, filter_result@1, group_result@1
        -> claim-fenced prepared_transitions@1 (where applicable)
        -> workset receipt / pending status / terminal OperationOutcome
        -> A3 accepted-result consumer

The DAG is logical, not a requirement to create six trivial nodes. Decide final node granularity by real input/output coherence. Use two or more independently useful pure transformations and at least one meaningful DAG dependency; do not claim Kedro benefit merely by renaming the existing steps. Do not put source reading, isolated parsing, durability, async APIs or long-running blocking work in a Kedro node.

Proposed pure signatures:

    def assemble_prepared_records(source: A2ExecutionInput) -> PreparedBatch: ...
    def evaluate_filters(prepared: PreparedBatch, policy: A2FilterPolicy) -> FilteredBatch: ...
    def analyse_native_relationships(
        prepared: PreparedBatch, filtered: FilteredBatch
    ) -> RelationshipGraph: ...
    def form_groups(graph: RelationshipGraph) -> GroupedBatch: ...
    def assemble_output(
        prepared: PreparedBatch, filtered: FilteredBatch, groups: GroupedBatch
    ) -> A2ExecutionOutput: ...

The A2 controller owns the sequence of side effects; Kedro's topology owns the **pure** stage ordering. This separation is deliberate and non-negotiable. Where an existing pure filter/group implementation has a proved closed contract, call it from the new node (or use an equivalent independently tested pure function). Avoid reimplementing business semantics to satisfy a nominal "greenfield" label.

## 6. Kedro embedded runtime policy

Use only public Kedro Core APIs: Node/node, Pipeline/pipeline, DataCatalog, MemoryDataset and SequentialRunner(is_async=False), constructed programmatically per bounded invocation. No kedro-datasets, KedroSession, Kedro server, Kedro CLI, automatic hooks, runtime config discovery, or second serialization/versioning system. No custom async runner.

Kedro Core synchronous Node execution is **not** coroutine execution; is_async=True on SequentialRunner parallelizes dataset loads/saves with threads, not business node awaits. The entire pure execution may run in an owned bounded worker thread, isolated from the Application event loop. Cancelling a Python thread is not supported: await its completion/cleanup, reject late output after terminal cancellation/timeout, never publish from worker callbacks. If finite bounds/cleanup cannot be proved, use an explicitly owned process boundary or reject the proposed node. Do not hide a loop, independent queue or daemon inside an adapter.

Dataset names and node names are static, reviewed, non-sensitive constants. MemoryDataset must preserve immutable objects safely; validate any Kedro copy semantics with actual pinned version. The output is loaded by the controller and independently Pydantic-validated before publication; never trust a forged constructed model merely because it crossed a DAG.

Before importing/using Kedro in executable operations, deployment/test process sets KEDRO_DISABLE_TELEMETRY=1 or DO_NOT_TRACK. Verify no access to Kedro project/config discovery and no network/telemetry, including subprocess and help/import tests. Avoid auto-loading third-party plugins; inspect Kedro's actual version for hook and plugin behaviour.

**Dependency candidate:** Kedro 1.7.0 (PyPI release 2026-09-28) is the current candidate, not an approved runtime pin. The 2026-09-29 plan's 1.6.0 selection is stale. A new dependency lock change must be a separate reviewed gate. Security registries disagree: Snyk's CVE-2026-3840 marks current releases affected by unsanitized versioned dataset paths, whereas GitHub/GitLab CVE-2026-35167 says the similar path-traversal flaw was fixed in 1.3.0. Require dated code-level resolution on the **exact installed 1.7.0** plus actual no-versioned-dataset/no-untrusted-catalog guards before acceptance. No unreviewed security-ignore exception; if the dependency remains unacceptable, stop adoption and retain current production behaviour. Do not install Kedro as a side effect of this design.

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

Grouping uses only source-native structural evidence and exact scope/version identity. Confirmed edges require an unambiguous present native parent within the same scope. Outlook conversation ID and subject similarities are candidates only. Teams channel rooted replies may confirm, Teams chat membership/time proximity cannot. Calendar, To Do, OneDrive and Contacts are contextual and do not create communication groups. Missing or contradictory ancestor/scope remains Uncertain; never confirm across sources or current-state joins. Save reasons and exact supporting relationship evidence. No invented global absence from a folder or Calendar window removal.

Keep context-only observations, component refreshes and scoped transitions distinct from communication groups. Scoped deletion/restoration belongs in prepared_transitions@1, not as fabricated "deleted message" content. Final output must preserve all limitations through A3 and A5 input adapters.

## 9. Durability, replay and failure semantics

A1 release sequence is admission order, not provider chronology. The intake cursor signifies **durably accepted selection**, not successful parsing. Never advance it on uncommitted selection, never rewind it to retry preparation, never scan mutable current projections to fill gaps. Pending workset fairness and held-entry reasons must remain equivalent to Task 15's 13 scenarios.

1. Admit a trusted request/plan with source catalog pin, config/policy versions and finite byte/record/time/lease budgets.
2. Own PREPARE workset/preparation claims through existing ClaimToken rules and verify exact accepted dependencies. Capture all source selections and derived parser-input artifacts durably first.
3. Run allowed parsing under existing sandbox/worker limits; drain parser workers on timeout/cancellation.
4. Run only validated, bounded pure Kedro transformations; treat output as untrusted until revalidated.
5. Publish accepted prepared@1, filter_result@1, group_result@1 in durable dependency order. Every write is fenced with the current claim and exact previous ResultRefs. Do not create acceptance receipts before all required refs have been saved.
6. Publish scoped transitions with exact fact/scope identity; finalize pending work only with complete accepted preparation proof.
7. Save a single terminal outcome. Partial evidence/known format limitations are INCOMPLETE with inspectable accepted partial refs; stale claim is FAILED, cancellation propagates only after cleanup, unexpected failure retains already durable refs and no false COMPLETE.
8. Replay loads exact collected_selection/derived evidence, parser and policy versions and source mappings; never consult current provider projections. Same domain inputs yield identical content-derived semantic versions (within documented algorithm/policy version); new code/config meaning changes produce new versions as required. Per-run ResultRefs may differ and remain immutable.

The new pipeline may use a new internally versioned implementation identifier, but it cannot silently reinterpret existing accepted prepared/filter/group schemas. Propose any schema extension separately with migration, reader/writer compatibility and an A3/A5 consumer proof. No business source state or checkpoint may be stored in Kedro datasets. A timeout must never cause a late durable publication.

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
- **Maintainability gate:** not simply duplicate the old 1,115 lines of handler/record_steps/stage_steps. Measure production sequencing LOC, branches and adapter LOC; reject Kedro adoption if meaningful complexity is not reduced or safety needs a custom async runner.
- **Performance gate:** compare fixed CPU/RAM and identical offline fixtures; target no material regression over 10% wall time and no unbounded RSS, especially on Raspberry Pi. Record actual values before accepting, not imagined numbers.

## 12. Decisions frozen and open checks

**Frozen:** A1/Intake read-only immutable contract; Kedro Core as target pure A2 DAG; claims/persistence/cleanup external; no second scheduler/state; old A2 stays as independent oracle through development; no permanent parallel engines; no widened grouping semantics or unsupported Windows promises.

**Must be established by independent implementation preflight, not guessed now:**

- Security disposition of Kedro candidate version and transitive lock impact (CVE conflict).
- Actual 1.7.0 DataCatalog/MemoryDataset lifecycle, plugin loading, output reads and memory/copy behaviour under the exact interpreter/runtime.
- Measured bounded pure-transform and thread cancellation budget.
- Which existing pure schemas/format parsers are reusable without reintroducing old sequencing.
- A2's actual post-cutover integration extension points and exact test node inventory.
- Benchmark baseline and any audited source/evidence field gaps discovered in D1.

Unresolved evidence blocks the affected implementation gate, not A1 closure or independent design analysis.
