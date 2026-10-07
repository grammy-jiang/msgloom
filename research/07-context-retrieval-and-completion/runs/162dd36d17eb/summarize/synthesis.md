# Executive Summary

The 34-paper corpus provides strong component-level evidence for adaptive retrieval, explicit sufficiency/gap judging, temporal and version-aware retrieval, permission-gated access, selective abstention, and bounded retrieval budgets. Across QA and RAG benchmarks, iterative controllers often improve evidence recall or answer quality, while indiscriminate retrieval can add noise and cost. Structured gap judging and adaptive stopping reduce unnecessary search in some settings, but stopping calibration remains brittle: unsafe early stops, conservative over-retrieval, and threshold-transfer failures are all observed. Formal conformal-risk papers provide finite-sample or anytime-valid guarantees under stated assumptions, but those guarantees are not demonstrated for integrated RAG stopping. Permission-aware and version-aware papers validate separate mechanisms, not a combined workplace controller. All eight prior gaps remain open; no study joins structured gaps, permissions, version lineage, temporal validity, calibrated stopping, abstention, and total-cost accounting.

# Themes

1. **Adaptive rather than indiscriminate retrieval.** FLARE, Self-RAG, DRAGIN, SeaKR, and budget-aware evaluations all show that retrieval utility depends on when retrieval occurs and on the current information need; fixed-frequency or always-retrieve policies can add harmful evidence in some cases [2305.06983] [2310.11511] [2403.10081] [2406.19215] [2607.24010].

2. **Evidence sufficiency and explicit gaps as control state.** S2G-RAG operationalizes insufficiency as typed gap objects that generate the next query, while other systems use answer confidence, uncertainty, answer stability, reflection, or value functions as continuation signals [2604.23783] [2510.14337] [2606.13814] [2606.29090].

3. **Temporal validity and version lineage are distinct retrieval dimensions.** MRAG demonstrates gains from explicit temporal reasoning and VersionRAG demonstrates gains from explicit version modeling; temporal-database terminology separately distinguishes valid time from transaction time [2412.15540] [2510.08109] [doi-10-1145-181550-181560].

4. **Permission enforcement can be part of retrieval rather than an after-the-fact filter.** Native-IAM checking, access gating, encrypted private storage, and RBAC-aware vector indexing all appear in the admitted corpus [doi-10-1109-access-2025-3628960] [doi-10-1038-s41598-026-71936-x] [2508.01084] [doi-10-1145-3786625].

5. **Stopping and abstention remain calibration problems as well as reasoning problems.** Structured stopping, confidence-based stopping, sufficiency verification, and value-based stopping improve different trade-offs, but unsafe early stopping and weak threshold transfer remain visible [2510.14337] [2605.03534] [2606.13814] [2608.13237].

6. **Formal risk control exists adjacent to RAG stopping.** Conformal prediction under covariate shift, conformal risk control for bounded losses, and anytime-valid active risk control provide finite-sample or sequential guarantees under their stated assumptions [1904.06019] [2208.02814] [2406.10490]. These papers do not test an integrated iterative RAG controller.

7. **Query construction materially changes evidence acquisition.** Conversational contextual encoding, retrieval-reward-trained rewriting, critique-driven narrowing, structured-gap queries, and iterative query planning improve retrieval in their respective evaluations, while rewrite omissions and added misinformation remain observed failure modes [2105.04166] [2112.08558] [2604.23783] [2604.25676] [doi-10-18653-v1-2026-findings-acl-2090].

8. **Cost is multidimensional.** Retrieval-call budgets, passage or token budgets, computational overhead, router calibration, and permission-index latency can lead to different conclusions about controller quality [2606.29959] [2607.24010] [2412.15540] [doi-10-1145-3786625].

# Findings

### 1. Structured evidence gaps can control iterative retrieval on multi-hop QA

S2G-RAG explicitly represents judged insufficiency as typed gap items containing fields such as target, slot, and description, converts those gaps into subsequent retrieval queries, and bounds the number and size of retrieval turns. It reports the strongest EM/F1 among its compared systems under the reported BM25 and E5 settings, and removing its sufficiency/gap judge produces its largest HotpotQA ablation loss [2604.23783]. This evidence is direct for the evaluated multi-hop QA setting, not workplace communication.

### 2. Adaptive retrieval frequently outperforms fixed or indiscriminate retrieval

FLARE reports that excessive retrieval can plateau or degrade performance [2305.06983]. Self-RAG reports degradation when its adaptive behavior is replaced by always using the top retrieved passage [2310.11511]. DRAGIN reports advantages for information-need-based timing over fixed schedules [2403.10081], and SeaKR reports worse results when retrieval occurs at every generation step [2406.19215]. A separate budget-aware study directly measures examples where retrieval harms the answer despite improving aggregate accuracy [2607.24010]. CLEAR likewise reports that extra retrieval can have little benefit or reduce performance when the parametric baseline is already strong [2609.16301].

### 3. Adaptive stopping improves some quality-cost trade-offs, but stopping errors remain substantial

Stop-RAG improves metrics over its own fixed-iteration and prompted-stopping comparisons on its principal benchmarks, with a transferred CoRAG HotpotQA exception [2510.14337]. TASR reduces retrieval relative to fixed-k=5 while retaining most of its reported F1 and reports no significant regression in its primary grid [2606.13814]. AB-RAG uses a confidence threshold and hard budget to trigger additional retrieval, with gains varying by model and dataset [2606.29090]. Search-R1 stopping experiments reduce searches within a predefined noninferiority margin, but 27 of 69 confirmatory early stops are classified as unsafe under the paper's probe definition [2608.13237]. SURE-RAG improves selective ranking, while improved calibration error does not improve its reported Risk@30 [2605.03534].

### 4. Formal bounded-risk machinery is available, but direct RAG-stopping guarantees are absent

Weighted conformal prediction restores marginal coverage under the paper's covariate-shift assumptions where ordinary conformal prediction can lose coverage [1904.06019]. Conformal Risk Control extends calibration to expected bounded monotone losses under exchangeability [2208.02814]. Active anytime-valid risk control provides a guarantee that remains valid at adaptive stopping times in sequential active-labeling settings [2406.10490]. These are formal results in their respective statistical settings; none evaluates the full iterative retrieval-and-stopping problem considered here.

### 5. Temporal and version-aware retrieval improve specialized retrieval tasks

MRAG finds that ordinary semantic retrievers are brittle under temporal perturbation and reports improved temporal evidence recall and QA after explicitly separating semantic and temporal reasoning [2412.15540]. VersionRAG reports substantially higher VersionQA accuracy than its naive-RAG and GraphRAG baselines, with large gains on version listing, change retrieval, and implicit change detection [2510.08109]. The temporal-database glossary provides the conceptual distinction between when a fact is valid in modeled reality and when it is current in the database [doi-10-1145-181550-181560]. The three works cover complementary aspects rather than one jointly tested retrieval controller.

### 6. Permission-aware retrieval can block unauthorized evidence before generation

The IAM-based Permission-Aware RAG framework performs provider-native authorization on retrieved candidates before they enter LLM context and reports permission-enforcement matches against its constructed ground truth [doi-10-1109-access-2025-3628960]. PPPARITL places authorization before similarity ranking and reports results on a synthetic enterprise evaluation [doi-10-1038-s41598-026-71936-x]. Provably Secure RAG provides formal security arguments and reports zero leakage or poisoning success for the evaluated attacks under its architecture [2508.01084]. HONEYBEE demonstrates that permission-safe vector retrieval also creates a measurable latency-memory-recall trade-off [doi-10-1145-3786625].

### 7. Evidence coverage materially changes apparent answerability

Analysis of naturally occurring information-seeking QA shows that retrieval misses and source coverage account for substantial portions of observed unanswerability, and some questions labeled unanswerable against a supplied document become answerable after searching other sources [2010.11915]. The Sufficient Context study separately shows that retrieved-context sufficiency distinguishes retrieval failure from model failure after adequate evidence has already been retrieved, and that combining sufficiency with answer confidence improves selective generation over confidence alone in reported ranges [2411.06037].

### 8. Query reformulation and planning improve retrieval while creating their own failure modes

ConvDR improves conversational first-stage retrieval under the evaluated CAsT settings and directly encodes relevant conversational history [2105.04166]. CONQRR improves retrieval metrics over its supervised rewrite baseline but its error analysis finds generated rewrites that omit useful context or introduce extra information [2112.08558]. CORAL reports gains from critique-driven corpus selection and query reformulation in multilingual cultural QA [2604.25676]. ToolQP improves retrieval completeness and downstream tool execution through iterative query planning, with an ablation showing value from retaining the original request as an anchor [doi-10-18653-v1-2026-findings-acl-2090].

### 9. Retrieval-policy evaluation changes when budget and deployability are measured explicitly

Budget-aware Active RAG evaluation finds that router rankings vary across datasets, budgets, and model families and that calibration thresholds can miss held-out usage targets [2607.24010]. Calibrated budget allocation shows that passage-budget improvements do not necessarily improve retrieval-call efficiency because even a one-passage request incurs a call [2606.29959]. MRAG reports improved temporal accuracy together with roughly doubled computational overhead relative to standard RAG [2412.15540]. These results establish that different cost measures capture different properties.

### 10. Explicit source separation can expose evidence conflict before final reasoning

CLEAR keeps parametric, curated-local, and dynamically retrieved evidence separate through adjudication rather than merging them immediately. In its medical QA experiments, targeted follow-up retrieval improves aggregate performance for one evaluated backbone, but only 12 of 123 triggered searches produce an accepted answer revision [2609.16301]. This demonstrates cross-source adjudication in medicine rather than workplace communication.

# Contradictions

No qualifying **cross-paper contradiction under comparable conditions** was identified.

Several results look opposed at a high level but answer different questions under different conditions and therefore are scope qualifications rather than contradictions:

- Iterative RAG outperforms static Gold Context in aggregate across the scientific multi-hop evaluation of [2601.19827], while other studies observe examples or tasks where additional retrieval hurts [2305.06983] [2607.24010] [2609.16301]. The datasets, evidence conditions, controllers, and retrieval regimes differ.
- Stop-RAG reports advantages for a learned value controller in its evaluated pipelines [2510.14337], while a separate budget-aware evaluation finds that simple uncertainty or retrieval-score baselines often rival learned routers [2607.24010]. These are not matched-controller evaluations.
- Formal conformal methods establish risk guarantees under explicit statistical assumptions [1904.06019] [2208.02814] [2406.10490], whereas empirical RAG stopping studies report calibration failures or unsafe stops [2608.13237] [2607.24010]. The formal and empirical studies do not analyze the same stopping procedure under the same assumptions.

There is one **within-paper qualification**, not a cross-paper contradiction: Stop-RAG's broad abstract-level consistency statement has a CoRAG HotpotQA result where Stop-RAG is slightly below the unmodified CoRAG baseline and does not dominate LLM-Stop [2510.14337].

# Open Gaps

### gap-1 — ACADEMIC, HIGH — OPEN

Structured gap representations remain insufficiently validated for temporal constraints, multi-entity joins, and complex compositional evidence requirements. S2G-RAG validates typed gaps for multi-hop QA but identifies richer temporal and compositional structures as limitations [2604.23783]. ToolQP adds iterative decomposition in tool retrieval but does not close the structured evidence-schema question [doi-10-18653-v1-2026-findings-acl-2090].

Suggested query: `"structured evidence gap" temporal constraints multi-entity compositional retrieval iterative RAG`

### gap-2 — ACADEMIC, HIGH — OPEN

No admitted study validates an iterative evidence-gap retrieval loop that jointly preserves document-version lineage, freshness or effective-time validity, and structured sufficiency decisions. VersionRAG covers document evolution [2510.08109], MRAG covers temporal validity [2412.15540], and S2G-RAG covers structured sufficiency/gap iteration [2604.23783]. Their combination is untested.

Suggested query: `"version-aware retrieval" temporal provenance iterative RAG document lineage freshness sufficiency`

### gap-3 — ACADEMIC, HIGH — OPEN

Stopping reliability under domain shift remains open. Structured and confidence-based stopping papers report unsafe early stopping, conservative behavior, and threshold-transfer problems [2608.13237] [2607.24010] [2605.03534]. Formal bounded-risk and anytime-valid methods exist in adjacent conformal-prediction settings [1904.06019] [2208.02814] [2406.10490], but no admitted paper gives a general bounded-risk guarantee for iterative RAG stopping under distribution shift.

Suggested query: `"adaptive retrieval" calibrated stopping domain shift selective prediction RAG risk`

### gap-4 — ENGINEERING, HIGH — OPEN

The corpus does not test a bounded replenishment loop in which unauthorized candidates are filtered through native IAM, evidence sufficiency is reassessed, and another permission-constrained query is issued when authorized evidence remains incomplete. Permission filtering is covered by [doi-10-1109-access-2025-3628960] and [doi-10-1038-s41598-026-71936-x], while sufficiency-driven iteration is covered separately by [2604.23783].

### gap-5 — ENGINEERING, HIGH — OPEN

The evaluated systems do not jointly distinguish empty retrieval, authorization denial, unavailable source, unsupported extraction, exhausted budget, and true negative evidence as separate terminal or retry conditions. Unanswerability [2010.11915], sufficiency [2411.06037], permission denial [doi-10-1109-access-2025-3628960], and budget termination [2606.29090] are covered separately.

### gap-6 — ENGINEERING, MEDIUM — OPEN

An end-to-end cost evaluation covering retrieval calls, retrieved passages or tokens, planner or judge inference, reranking, permission-check latency, and total wall-clock latency is still absent. Existing papers cover subsets such as retrieval calls and passage budgets [2606.29959], threshold/budget behavior [2607.24010], temporal-RAG computational overhead [2412.15540], or permission-aware vector-search latency and memory [doi-10-1145-3786625].

### gap-7 — ENGINEERING, HIGH — OPEN

The corpus lacks a workplace-communication evaluation combining explicit evidence gaps with heterogeneous messages and documents, multi-hop dependencies, permission restrictions, stale or conflicting evidence, and bounded retrieval. The closest evidence comes from separate QA, version-aware, temporal, permission-aware, tool, scientific, and medical settings [2604.23783] [2510.08109] [2412.15540] [doi-10-1109-access-2025-3628960] [2609.16301].

### gap-8 — ACADEMIC, HIGH — OPEN

No admitted study validates a single controller that jointly handles structured evidence gaps, permission-aware source access, version lineage, temporal validity, calibrated stopping, abstention, and total-cost budgeting. Evidence exists separately for structured gaps [2604.23783], permissions [doi-10-1109-access-2025-3628960], versions [2510.08109], temporal retrieval [2412.15540], stopping [2608.13237], formal risk control [2208.02814], and retrieval budgeting [2606.29959]. Component-level results do not establish correctness of their combination.

Suggested query: `"enterprise RAG" permission-aware provenance temporal adaptive retrieval calibrated stopping abstention`

# Actionable Insights

- **Synthesis-derived recommendation:** Represent every investigation request as a typed evidence-gap object containing the unresolved target, requested relation or slot, known evidence, temporal scope, source scope, and retry or budget state rather than as a generic request for more context.
- **Synthesis-derived recommendation:** Implement retrieval as a bounded reassessment loop with explicit outcomes for answered, still-insufficient, budget-exhausted, access-denied, source-unavailable, extraction-unsupported, and search-empty states.
- **Synthesis-derived recommendation:** Preserve authorization inside the retrieval path before evidence reaches reasoning, and permit another permission-constrained retrieval attempt when authorized evidence remains insufficient instead of treating filtered-out candidates as negative evidence.
- **Synthesis-derived recommendation:** Carry a provenance tuple through retrieval that identifies source/resource, source-local identifier, document or attachment version, evidence location, effective or valid time where available, and collection/version time.
- **Synthesis-derived recommendation:** Treat retrieval stopping as a calibrated deployment policy rather than a universal confidence threshold; evaluate threshold transfer on held-out and shifted workloads and retain a hard maximum retrieval budget.
- **Synthesis-derived recommendation:** Separate answer sufficiency, answer confidence, retrieval utility, and authorization state in controller telemetry so that one signal cannot silently stand in for the others.
- **Synthesis-derived recommendation:** Measure controller cost end to end, including retrieval calls, retrieved tokens or passages, planning/judging inference, reranking, permission checks, parsing or grounding work, and wall-clock latency.
- **Synthesis-derived recommendation:** Build engineering fixtures that independently vary missing hops, stale and conflicting versions, denied reads, empty results, unavailable attachments, unsupported extraction, query-rewrite errors, and budget exhaustion, with evaluation gold kept outside controller inputs.
- **Synthesis-derived recommendation:** Keep an unresolved evidence gap visible when the bounded loop terminates without adequate evidence, rather than converting retrieval failure or lack of authorization into a factual negative.

# Confidence Summary

Confidence is **HIGH** for the component-level conclusion that adaptive retrieval, explicit sufficiency assessment, temporal/version-aware retrieval, permission gating, and calibrated selective control each have empirical or theoretical support in their own settings. Confidence is **MEDIUM** for transfer of those design principles to workplace communication because the corpus is dominated by QA, RAG, tool-retrieval, scientific, medical, synthetic-enterprise, and vector-database evaluations. Confidence is **LOW** that the literature currently establishes correctness of an integrated controller combining all of these mechanisms. Formal bounded-risk guarantees are particularly strong within their stated conformal assumptions, but their direct application to iterative RAG stopping under domain shift remains unvalidated.

# Limitations

- This synthesis uses only the supplied 34 per-paper analyses rather than independently rereading the full papers. Evidence section descriptions identify analyzed result categories rather than verified verbatim paper headings.
- Most evidence is transfer evidence from open-domain or benchmark QA, generation, medical QA, scientific QA, tool retrieval, synthetic enterprise settings, or vector databases. None directly establishes production workplace-communication accuracy.
- The component literatures use different datasets, retrievers, model families, cost definitions, stopping policies, and notions of sufficiency, so their successes do not jointly validate an integrated scheme.
- Formal conformal-risk results rely on assumptions such as exchangeability, bounded monotone losses, known or estimated shift weights, or specific sequential constructions that are not demonstrated for the integrated retrieval-controller setting [1904.06019] [2208.02814] [2406.10490].
- Permission-aware papers validate enforcement in constructed or synthetic evaluations and security architectures but do not evaluate repeated evidence-gap reassessment after authorization filtering [doi-10-1109-access-2025-3628960] [doi-10-1038-s41598-026-71936-x].
- VersionRAG and MRAG separately address document evolution and temporal constraints; their joint interaction with structured evidence-gap stopping is not evaluated [2510.08109] [2412.15540] [2604.23783].
- Stop-RAG contains a within-paper qualification: its broad consistency claim has a CoRAG HotpotQA exception [2510.14337].
- Apparent differences between iterative-retrieval gains and retrieval-harm results are not treated as contradictions because they arise from different tasks, evidence conditions, controllers, and datasets [2601.19827] [2305.06983] [2607.24010] [2609.16301].
- Likewise, learned stopping results [2510.14337] and observations that simple uncertainty baselines can rival learned routers [2607.24010] come from different experimental settings and do not form a matched contradiction.
- Inherited handoffs from Topics 03, 04, 05, 06, and 08 are used only as project-scoping context. They do not support any finding or gap closure in this synthesis.
