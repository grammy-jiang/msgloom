# Executive Summary

The 61-paper corpus supports a modular picture rather than a validated unified controller. Structured sufficiency and gap representations can drive iterative retrieval and early stopping on multi-hop QA, while adaptive retrieval studies show that additional retrieval can be beneficial, neutral, or harmful depending on the query and evidence state. Separate conformal and selective-prediction work provides calibrated risk or coverage control, including several forms of distribution-shift adaptation. Temporal and version-aware systems improve retrieval over evolving documents, and separate permission-aware RAG systems enforce access constraints. Budget-aware controllers reduce calls, tokens, or latency in several benchmark settings. However, no admitted study combines structured evidence gaps, temporal/version lineage, permission-aware replenishment, calibrated stopping under shift, abstention, and total-cost control in one evaluated iterative retrieval loop. All eight prior gaps therefore remain open.

# Themes

## Structured sufficiency and explicit evidence gaps

Several multi-hop QA systems make missing evidence explicit rather than treating retrieval as an undifferentiated request for additional context. S2G-RAG represents typed gaps and maps them to subsequent queries [2604.23783]. FAIR-RAG enumerates required and confirmed findings and retrieves against unresolved findings [2510.22344]. AdaGATE combines explicit gap repair with a global evidence-token constraint [2605.05245]. DynaKRAG places sufficiency checking, gap-directed retrieval, continuation, and stopping inside one learnable evidence-control policy [2607.06507]. MEGRAG similarly tracks remaining information need and issues focused follow-up queries until resolution or budget exhaustion [2608.02195].

Across their own multi-hop QA evaluations, these systems report stronger evidence or answer metrics than their stated comparison systems while retaining explicit stopping or hard iteration bounds [2604.23783] [2510.22344] [2605.05245] [2607.06507] [2608.02195].

## Retrieval benefit is heterogeneous

Additional retrieval is not uniformly beneficial. FLARE reports plateauing or degraded performance when retrieval fires too frequently [2305.06983]. DRAGIN finds that fixed retrieval schedules do not consistently beat single-round RAG [2403.10081]. SeaKR reports poorer results when retrieval is forced at every generation step [2406.19215]. A budget-aware Active RAG evaluation directly measures examples on which retrieval harms otherwise correct behavior [2607.24010]. CLEAR likewise reports settings in which additional retrieved evidence provides little benefit or degrades performance when the parametric baseline is already strong [2609.16301].

This is a recurring empirical pattern across different tasks, not evidence for one universal trigger.

## Adaptive stopping reduces resources but remains fallible

Training-free, learned, confidence-based, and structured stopping methods reduce retrieval or reasoning resources in several benchmark settings. TASR retains much of fixed-five-turn performance with substantially fewer calls in its main experiments [2606.13814]. AB-RAG stops when calibrated confidence exceeds a threshold or when its retrieval budget is exhausted [2606.29090]. Pre-retrieval budget allocation can skip or reduce retrieval for queries with sufficiently strong calibrated closed-book predictions [2606.29959]. RAG-on-a-Diet reports lower modeled cost through learned routing and dual stopping [doi-10-18653-v1-2026-acl-long-1562].

Stopping error is nevertheless material in some studies. In the structured Search-R1 evaluation, 27 of 69 executed confirmatory early stops were classified as unsafe under the paper's probe-based definition, even though aggregate exact-match degradation remained inside the experiment's predefined noninferiority margin [2608.13237].

## Conformal control and distribution shift

Conformal work establishes several forms of coverage or risk control under explicit assumptions. Weighted conformal prediction restores marginal coverage under covariate shift when the likelihood ratio is available [1904.06019]. Conformal Risk Control extends calibration to bounded monotone loss functions [2208.02814]. TRAQ supplies an end-to-end answer-set coverage construction for RAG under its exchangeability assumptions [2307.04642]. C-RAG certifies bounded generation risks for fixed RAG configurations and derives a bound for a specified Hellinger-distance shift neighborhood [2402.03181]. MiCP calibrates retrieval, adaptive stopping, and final prediction sets across multi-turn reasoning [2604.01413].

Separate online and drift-adaptive methods address changing distributions. DtACI adapts online without requiring the shift rate in advance [2208.08401]. PromptShift-CRC explicitly reweights historical calibration under prompt and domain drift [2606.15964]. A later CRC study reports substantially fewer target violations with ACI than static CRC under its temporal and gradual-severity shifts [2606.29054].

These papers validate different formulations. They do not jointly validate distribution-shift-aware conformal stopping together with structured evidence gaps, permissions, and version provenance.

## Static calibration can fail after shift

Selective QA finds source-trained models systematically overconfident on unseen domains and reports better selective performance from a calibrator exposed to known out-of-domain data [2006.09462]. Under covariate shift, ordinary split conformal falls well below its nominal coverage in the reported Airfoil experiment while weighted conformal restores it [1904.06019]. PromptShift-CRC reports large collapses for static calibration under its prototype shifts and stronger target tracking from adaptive procedures [2606.15964]. Static CRC also incurs many more violations than ACI in the temporal and severity-shift experiments reported in [2606.29054].

## Temporal and version-aware evidence selection

Temporal retrieval studies show that semantic relevance alone can select temporally invalid evidence. MRAG improves retrieval by separating semantic relevance from temporal reasoning [2412.15540]. VersionRAG explicitly models document versions and transitions and reports large gains on VersionQA over naive RAG and GraphRAG [2510.08109]. Temporal GraphRAG reports improved time-sensitive QA and efficient incremental incorporation of new corpus slices [2510.13590]. TimelyRAG improves retrieval over highly overlapping evolving documents by semantic-temporal reranking [2609.11572].

The evolving-document benchmark in [2608.08512] shows substantial remaining difficulty even with authoritative document access: standard semantic RAG often fails to retrieve all provisions required for amendment-timeline reasoning, and context-misalignment questions remain difficult.

SentryLine adds explicit guideline year, update status, superseding-passage verification, page and passage provenance in an oncology setting and reports improvements on questions containing outdated recommendations [2609.08364].

## Temporal provenance has multiple dimensions

Classical temporal-database work distinguishes valid time—when a fact holds in the modeled world—from transaction time—when it is current in a database [doi-10-1016-0306-4379-96-00017-8] [doi-10-1145-181550-181560]. Recent RAG work adds operational mechanisms such as version graphs [2510.08109], temporal retrieval [2609.11572], and explicit update or supersession status [2609.08364].

These are different forms of temporal provenance. The corpus does not evaluate them as one common provenance representation spanning iterative retrieval rounds.

## Permission-aware retrieval

Permission-aware RAG is directly represented in several studies. One architecture validates semantically retrieved candidates against each provider's native IAM before they enter the LLM context and reports matching its experimental authorization ground truth across the tested user profiles [doi-10-1109-access-2025-3628960]. PPPARITL places an authorization gate before ranking and adds trust assessment and encrypted embeddings in its synthetic enterprise evaluation [doi-10-1038-s41598-026-71936-x]. Provably Secure RAG isolates encrypted private data by authenticated user and reports zero leakage and poisoning success under its tested attacks [2508.01084]. HONEYBEE evaluates RBAC-aware vector partitioning as a latency-memory-recall trade-off [doi-10-1145-3786625].

None of these studies evaluates a structured sufficiency decision followed by repeated permission-constrained replenishment after unauthorized candidates have been removed.

## Sufficiency and confidence are different signals

The sufficient-context study separates retrieval insufficiency from generation failure and finds selective generation improves when context sufficiency is combined with answer confidence rather than relying on confidence alone [2411.06037]. SURE-RAG likewise evaluates set-level evidence sufficiency and selective answering [2605.03534].

The MetaRAG reproduction reports substantial disagreement between an LLM's sufficiency judgment and an NLI critic on the same retrieved evidence [2604.19899]. The evidence-sufficiency benchmark further shows that models frequently answer rather than abstain when retrieved evidence explicitly conflicts, with evidence picking dominating the reported conflict failure mode [doi-10-32604-cmc-2026-086343].

Thus the corpus directly demonstrates that answer confidence, evidence sufficiency, and conflict handling are not interchangeable measurements.

## Retrieval cost is multidimensional

Different studies expose different resource dimensions. Pre-retrieval budget allocation shows that reducing passages does not necessarily reduce retrieval calls because even a one-passage request still incurs a retrieval operation [2606.29959]. The Active RAG budget study distinguishes exact usage-matched ranking frontiers from deployable threshold frontiers and finds that nominal calibration budgets can be exceeded on held-out splits [2607.24010]. Agent-orchestrated RAG reports quality changes together with large latency increases from decomposition or reflection in some settings [2606.05658]. DRAGIN reports retrieval-call reductions relative to fixed schedules [2403.10081]. HONEYBEE treats access-safe search as a three-way latency-memory-recall optimization [doi-10-1145-3786625].

### Evidence findings summary

1. Explicit structured gaps can control subsequent retrieval and bounded stopping on multi-hop QA [2604.23783] [2510.22344] [2605.05245] [2607.06507] [2608.02195].
2. More retrieval is not monotonically better across the evaluated adaptive-RAG settings [2305.06983] [2403.10081] [2406.19215] [2607.24010] [2609.16301].
3. Adaptive stopping can lower calls, turns, tokens, or cost, while some stopping policies still produce substantial unsafe-stop rates [2606.13814] [2608.13237] [2606.29090] [2606.29959] [doi-10-18653-v1-2026-acl-long-1562].
4. Conformal methods provide risk or coverage guarantees under their stated assumptions, and separate methods adapt those guarantees to several kinds of shift [1904.06019] [2208.02814] [2208.08401] [2307.04642] [2402.03181] [2406.10490] [2604.01413] [2606.15964] [2606.29054].
5. Static confidence and calibration can degrade materially under distribution shift [2006.09462] [1904.06019] [2606.15964] [2606.29054].
6. Temporal and version-aware methods improve retrieval on evolving-document benchmarks, where ordinary semantic retrieval can return temporally invalid or incomplete evidence [2412.15540] [2510.08109] [2510.13590] [2608.08512] [2609.08364] [2609.11572].
7. Valid time, transaction time, version transitions, and supersession status represent distinct temporal provenance concepts [doi-10-1016-0306-4379-96-00017-8] [doi-10-1145-181550-181560] [2510.08109] [2609.08364].
8. Permission-aware systems demonstrate native-IAM, authorization-gate, isolation, and RBAC-aware retrieval mechanisms, without testing permission-filtered iterative sufficiency replenishment [doi-10-1109-access-2025-3628960] [doi-10-1038-s41598-026-71936-x] [2508.01084] [doi-10-1145-3786625].
9. Evidence sufficiency, answer confidence, and evidence conflict are empirically distinct signals [2411.06037] [2605.03534] [2604.19899] [doi-10-32604-cmc-2026-086343].
10. Passage count, token count, retrieval calls, controller computation, and latency capture different cost properties and can produce different policy comparisons [2606.29959] [2607.24010] [2606.05658] [2403.10081] [doi-10-1145-3786625].

# Contradictions

### Stop-RAG's consistency claim versus its reported HotpotQA result

The shared question is: **Does Stop-RAG consistently outperform the unmodified iterative-RAG baseline across the reported benchmark settings?**

The broad consistency claim in Stop-RAG is not supported by every reported result. On the CoRAG HotpotQA evaluation, Stop-RAG is slightly below the unmodified CoRAG baseline and does not dominate LLM-Stop [2510.14337]. This is an internal claim-versus-result contradiction within the study rather than a disagreement between two independent papers.

### MiCP's prediction-set-size claim versus reported rows

The shared question is: **Does MiCP consistently reduce prediction-set size relative to the no-early-stopping baseline?**

Several reported Table 1 rows do not support the paper's consistency statement. In GPT-4o-mini settings on HotpotQA and HotpotQA-ReAct, the proposed objective yields larger prediction sets than the no-early-stopping baseline [2604.01413]. This is also an internal claim-versus-result contradiction.

Other apparent tensions were not classified as contradictions when experiments used different tasks, controller definitions, datasets, or metrics. For example, decomposition improves several IRCoT outcomes [2212.10509] while producing poor retrieval-ranking metrics in one MuSiQue orchestration experiment [2606.05658]; these systems and evaluations are not sufficiently comparable to establish a direct contradiction.

# Open Gaps

## gap-1 — ACADEMIC, HIGH

Structured gap representations remain insufficiently validated for temporal constraints, multi-entity joins, and complex compositional evidence requirements. Structured-gap methods now have substantial multi-hop QA evidence [2604.23783] [2510.22344] [2605.05245] [2607.06507], while temporal retrieval and iterative query planning are separately represented [2412.15540] [doi-10-18653-v1-2026-findings-acl-2090]. No admitted study evaluates the requested combination.

Suggested query: `"structured evidence gap" temporal constraints multi-entity joins compositional retrieval iterative RAG`

**Status: open.**

## gap-2 — ACADEMIC, HIGH

No admitted study validates an iterative evidence-gap retrieval loop that jointly preserves document-version lineage, freshness or effective-time validity, and structured sufficiency decisions. VersionRAG, Temporal GraphRAG, TimelyRAG, and SentryLine address version or temporal evidence [2510.08109] [2510.13590] [2609.11572] [2609.08364], while S2G-RAG and FAIR-RAG address iterative structured sufficiency [2604.23783] [2510.22344]. The combination remains unevaluated.

Suggested query: `"version-aware retrieval" temporal provenance iterative RAG document lineage freshness effective-time sufficiency`

**Status: open.**

## gap-3 — ACADEMIC, HIGH

Stopping reliability under domain shift remains open. MiCP provides conformal multi-turn stopping [2604.01413]; weighted conformal prediction, DtACI, PromptShift-CRC, C-RAG, and later CRC work address different forms of shift or risk control [1904.06019] [2208.08401] [2402.03181] [2606.15964] [2606.29054]. No admitted study demonstrates a general bounded-risk iterative-RAG stopping guarantee under distribution shift.

Suggested query: `"iterative RAG" calibrated stopping domain shift conformal risk control selective prediction adaptive retrieval`

**Status: open.**

## gap-4 — ENGINEERING, HIGH

The corpus does not test a bounded replenishment loop in which unauthorized candidates are filtered through native IAM, evidence sufficiency is reassessed, and another permission-constrained query is issued when authorized evidence remains incomplete. Existing permission studies cover authorization mechanisms without this loop [doi-10-1109-access-2025-3628960] [doi-10-1038-s41598-026-71936-x] [2508.01084] [doi-10-1145-3786625].

**Status: open.**

## gap-5 — ENGINEERING, HIGH

The evaluated systems do not jointly distinguish empty retrieval, authorization denial, unavailable source, unsupported extraction, exhausted budget, and true negative evidence as separate terminal or retry conditions. Individual studies cover subsets such as explicit budget exhaustion [2608.02195], conflict and insufficiency [doi-10-32604-cmc-2026-086343], authorization denial [doi-10-1109-access-2025-3628960], or token-limit termination [2506.05167].

**Status: open.**

## gap-6 — ENGINEERING, MEDIUM

An end-to-end cost evaluation covering retrieval calls, retrieved passages or tokens, planner or judge inference, reranking, permission-check latency, and total wall-clock latency remains absent. Separate papers report different subsets of these quantities [2606.29959] [2607.24010] [2606.05658] [doi-10-18653-v1-2026-acl-long-1562] [doi-10-1145-3786625].

**Status: open.**

## gap-7 — ENGINEERING, HIGH

The corpus lacks a workplace-communication evaluation combining explicit evidence gaps with heterogeneous messages and documents, multi-hop dependencies, permission restrictions, stale or conflicting evidence, and bounded retrieval. The closest evidence comes from multi-hop QA [2604.23783], evolving oncology guidelines [2609.08364], constructed permission-aware environments [doi-10-1109-access-2025-3628960], and evolving authoritative documents [2608.08512], none of which directly evaluates the complete workplace setting.

**Status: open.**

## gap-8 — ACADEMIC, HIGH

No admitted study validates a single controller that jointly handles structured evidence gaps, permission-aware source access, version lineage, temporal validity, calibrated stopping, abstention, and total-cost budgeting. DynaKRAG covers multiple evidence-control actions, sufficiency, stopping, and bounded resources [2607.06507]; S2G-RAG covers structured gaps [2604.23783]; VersionRAG and SentryLine cover version or temporal provenance [2510.08109] [2609.08364]; permission-aware studies cover access enforcement [doi-10-1109-access-2025-3628960]; MiCP and PromptShift-CRC cover calibrated stopping or shift-aware risk control in separate formulations [2604.01413] [2606.15964]. No admitted paper evaluates their full combination.

Suggested query: `"adaptive RAG controller" permission-aware provenance temporal version calibrated stopping abstention budget`

**Status: open.**

# Actionable Insights

- **Synthesis-derived recommendation:** represent each investigation state with explicit required findings, confirmed findings, unresolved gaps, and the evidence identifiers supporting each confirmation; include temporal constraints, entity or field targets, and source-scope constraints as structured fields rather than only free-text prompts.
- **Synthesis-derived recommendation:** keep the evidence-sufficiency decision separate from answer confidence and from the retrieval-policy decision, so each signal can be measured, calibrated, replaced, and audited independently.
- **Synthesis-derived recommendation:** use an explicit terminal-state taxonomy that separates answered, budget exhausted, authorization denied, source unavailable, empty search, extraction unsupported, conflicting evidence, and unresolved insufficiency instead of mapping these outcomes to a common no-answer state.
- **Synthesis-derived recommendation:** maintain document identity, version identity, effective or valid time, collection or transaction time, and exact evidence location through every retrieval round so later evidence cannot silently overwrite the provenance of earlier evidence.
- **Synthesis-derived recommendation:** enforce permission checks before evidence enters the reasoning context and exercise a bounded authorized-evidence replenishment path when filtered results leave an explicit gap unresolved.
- **Synthesis-derived recommendation:** combine a conservative hard retrieval budget with an adaptive stopping layer; treat the hard bound as a safety and cost limit rather than evidence that the remaining gap has been resolved.
- **Synthesis-derived recommendation:** evaluate stopping under controlled distribution shifts and recalibration scenarios rather than selecting a sufficiency or confidence threshold only on an in-distribution development set.
- **Synthesis-derived recommendation:** account separately for retrieval calls, documents or passages read, context tokens, planner and judge inference, reranking, authorization checks, and end-to-end latency because optimization on one resource measure can hide movement in another.
- **Synthesis-derived recommendation:** construct an engineering benchmark containing multi-hop evidence gaps, evolving versions, stale and conflicting evidence, permission denial, empty retrieval, unavailable sources, extraction failure, and budget exhaustion, with gold outcomes independent of the controller under test.

# Confidence Summary

Confidence is **HIGH** for the component-level evidence: structured sufficiency control, adaptive retrieval, temporal/version-aware retrieval, permission enforcement, budget-aware retrieval, and conformal or selective risk control each have direct empirical support in their respective evaluated settings.

Confidence is **MEDIUM** for transfer of these principles across domains because most experiments use QA, medical, tool-retrieval, evolving-document, or synthetic settings rather than workplace communication.

Confidence is **LOW** that the corpus establishes an integrated controller. No admitted paper jointly evaluates structured gap reasoning, permission-aware access, temporal/version provenance, distribution-shift-aware calibrated stopping, abstention, and complete cost accounting. The corpus therefore supplies well-supported component-level design principles but not an experimentally validated unified architecture.

# Limitations

- This synthesis uses the supplied per-paper analyses as its evidence base and does not independently re-read or re-verify the full text of all 61 papers.
- The inherited Topic 03, 04, 05, 06, and 08 handoffs are project context only and are not used as evidence for findings or gap closure.
- Most direct controller evaluations are on multi-hop or open-domain QA rather than Outlook email, Teams messages, workplace attachments, or cross-thread work-item investigation, so production-workplace claims are not supported by this corpus.
- Temporal/version studies, permission studies, structured-gap controllers, and conformal-risk studies generally evaluate different datasets, metrics, and system boundaries. Their separate successes do not validate their combination.
- Several evaluations rely on synthetic perturbations, controlled conflict injection, constructed enterprise permission settings, or benchmark-specific evidence proxies. These results establish behavior in those test conditions rather than production representativeness.
- Cost reporting is heterogeneous across papers: some report retrieval calls, some tokens, some latency, some model cost, and some indexing or memory overhead, limiting direct cross-paper efficiency comparison.
- Apparent differences across retrieval, decomposition, reranking, and stopping methods were not labeled contradictions when the studies answer different questions, use different controller definitions, or operate under non-comparable conditions.
- No duplicate title was evident among the 61 supplied records. The manual IDCR record was treated as a distinct work because no supplied DOI record has the same title.
