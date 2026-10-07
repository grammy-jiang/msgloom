# Executive Summary

Across 64 corpus records, the evidence consistently supports decomposed reliability evaluation rather than a single factuality score. Summarization, RAG, report-generation, attribution, and fact-verification studies separate claim correctness, source support, evidence recall, and omission; temporal studies further show that current-state validity can diverge from generic support. Selective-prediction work demonstrates useful risk-coverage control and improved calibration in several domains, but guarantees depend on confidence quality, calibration regime, and shift assumptions. Online conformal methods provide strong results for changing streams, while structured-generation studies show that static or simply adaptive methods can fail under severe cross-dataset shift. Report and update-summarization benchmarks evaluate omission and redundancy, yet none directly models longitudinal workplace work-item states. The corpus therefore supplies strong component-level evidence but does not validate a single joint scheme for compound, multi-source, temporally versioned, selectively generated workplace briefings.

# Themes

The main recurring themes are dimension-separated evaluation of factual correctness, attribution, evidence completeness, and omission; atomic-claim decomposition combined with cross-claim consistency; evidence sufficiency and complementary multi-source evidence; temporal validity and out-of-order evidence; omission, novelty, and repetition in reports and updates; selective prediction and risk-coverage trade-offs; online calibration under distribution shift; human-review reliability; and decomposition of retrieval versus generation failures.

## Cross-paper findings

1. **Correctness, attribution, and completeness are empirically distinct.** Across summarization, attributed QA, report evaluation, and RAG, evaluated systems can score differently on claim correctness, citation or source support, and completeness rather than exposing one interchangeable quality variable. [2212.08037] [2305.14627] [2405.00982] [2408.08067]  
   **Confidence: HIGH**

2. **Fine-grained decomposition helps, but atomic support is not sufficient for aggregate correctness.** Sentence- or claim-level decomposition improves factual-consistency diagnosis and evidence localization in summarization and long-form evaluation, while entity-mixing experiments show that independently supportable atomic claims can still form a misleading aggregate narrative. [1910.12840] [2111.09525] [2402.05629] [2510.12839] [2604.03141]  
   **Confidence: HIGH**

3. **Incomplete, partial, and distributed evidence remain difficult.** Fact-checking and complex-verification experiments show substantial error when evidence is incomplete, partially supportive, contradictory, or spread across multiple sources. Decomposition, minimal-evidence-group identification, and multi-source retrieval improve subsets of the problem, but the studies do not jointly cover all of these conditions. [2204.02007] [2305.11859] [2404.15588] [2508.20867] [doi-10-18653-v1-2025-acl-long-837] [doi-10-32604-cmc-2026-086343]  
   **Confidence: HIGH**

4. **Temporal evidence validity is separate from generic factual support.** Static benchmark labels can become stale enough to penalize answers aligned with current facts; temporal-QA experiments find citations that support an answer but are invalid for the query time; explicit chronological modeling improves temporal fact verification; and runtime-verification work demonstrates sound treatment of incomplete and out-of-order temporal observations within its formal setting. [2510.07238] [doi-10-1109-access-2026-3679691] [2410.14964] [1707.05555]  
   **Confidence: HIGH**

5. **Omission and repetition can be evaluated separately at report or update level, but not yet for longitudinal workplace state.** Nugget, Pyramid, update-summarization, and real-time-summarization evaluations separately account for content coverage and repeated or redundant information. The admitted studies do not directly evaluate omission of evolving workplace work-item states such as due, resolved, or superseded items. [2405.00982] [doi-10-1017-s1351324909005051] [doi-10-1155-2016-1340973] [doi-10-6028-nist-sp-500-321-realtime-overview] [manual-39435af3dd] [2607.19322]  
   **Confidence: HIGH**

6. **Selective prediction can reduce accepted-answer risk, but confidence quality is task- and shift-dependent.** QA, NLP classification, RAG, and free-form generation studies obtain useful abstention or risk-coverage behavior from calibrated confidence, while raw sequence likelihood and uncalibrated probabilities frequently provide weak or overconfident selectors. [2006.09462] [doi-10-1162-tacl-a-00407] [2312.09300] [doi-10-18653-v1-2021-acl-long-84] [2605.03534] [2608.22483]  
   **Confidence: HIGH**

7. **Online conformal methods address distribution change, but the strength and locality of their guarantees vary.** Adaptive and strongly adaptive methods report useful coverage behavior in election, forecasting, image-shift, and theoretical drift settings. Structured-generation experiments additionally show that static conformal risk control and ACI can violate emitted-risk targets under severe cross-dataset shift. [2106.00170] [2208.08401] [2302.07869] [2602.16537] [2606.29054]  
   **Confidence: HIGH**

8. **Calibration, confidence ranking, and factual accuracy are separate properties.** Linguistic or verbalized confidence can be trained to better reflect correctness or downstream reader beliefs, but factual accuracy can remain nearly unchanged, and reasoning or post-hoc calibration can improve accuracy or ECE while degrading confidence ranking. [2012.14983] [2404.00474] [2505.23912] [2607.03870] [2604.12046]  
   **Confidence: MEDIUM**

9. **Automatic judges can be useful without constituting ground truth.** System-level correlations can be strong, but item-level agreement, abstention handling, rating indeterminacy, and false-positive versus false-negative bias materially change interpretation. Active sampling and human-grounded auxiliary-estimator methods demonstrate ways to reduce human-review cost while retaining an explicit human target. [2212.08037] [2509.26184] [2406.07967] [2605.16354] [2606.00093] [2607.08700] [manual-32d5793dca]  
   **Confidence: HIGH**

10. **Retrieval and generation are separable end-to-end bottlenecks.** Better retrieval generally improves downstream factual generation in the evaluated RAG and fact-verification settings, but oracle or near-oracle evidence still leaves omissions, unsupported generation, and incomplete evidence use. [2004.14974] [2305.14627] [2408.08067] [2508.20867]  
    **Confidence: HIGH**

# Contradictions

No direct contradiction was identified in which two admitted papers answer the same question under sufficiently comparable conditions and reach incompatible conclusions.

Several apparent tensions are better treated as scope qualifications. Softmax confidence performs strongly in some in-domain NLP classification settings [doi-10-18653-v1-2021-acl-long-84], while maximum softmax is overconfident under shifted QA in [2006.09462]. Adaptive conformal inference gives useful coverage behavior in election and forecasting streams [2106.00170], while ACI violates structured-generation emitted-risk targets on severe cross-dataset transfers in [2606.29054]. These experiments differ in task, shift regime, loss definition, and guarantee, so they do not constitute direct contradictions.

# Open Gaps

## gap-1 — ACADEMIC, HIGH

No admitted study validates one end-to-end evaluation scheme that jointly measures claim correctness, evidence attribution correctness, citation or evidence completeness, temporal or current-state correctness, omission, calibrated uncertainty, and abstention while preserving separate denominators for those dimensions. The corpus validates individual components and smaller combinations.

**Status: open.** Papers such as [2405.00982], [2509.26184], [2510.07238], [2606.29054], and [2607.19322] extend particular combinations, but none answers the full joint question.

**Suggested query:** `"joint evaluation framework" factuality attribution completeness temporal correctness omission calibration abstention "free-form generation" multi-source`

## gap-2 — ENGINEERING, HIGH

The corpus contains no direct evaluation on private workplace email or Teams-style communication with realistic revisions, quoted history, conflicting updates, delayed or out-of-order arrival, versioned attachments, and permission-constrained evidence. Target-domain fixtures and gold data remain an engineering validation gap.

**Status: open.** No admitted paper directly evaluates that target-domain combination.

## gap-4 — ACADEMIC, HIGH

The corpus does not establish a general evidence-completeness method that jointly handles compound claims, partially supportive evidence, multiple complementary sources, and temporally versioned evidence. Separate studies cover subsets of these conditions.

**Status: open.** Compound-claim decomposition [2305.11859], minimal sufficient evidence [2404.15588], multi-source synthesis [2508.20867], partial-support evaluation [doi-10-18653-v1-2025-acl-long-837], and temporal evidence validity [doi-10-1109-access-2026-3679691] cover different pieces rather than one validated joint method.

**Suggested query:** `"evidence completeness" compound claims partial support complementary evidence multi-source temporal versioning provenance evaluation`

## gap-5 — ACADEMIC, HIGH

Report-level omission has substantial benchmark coverage, but the corpus still does not establish omission detection for evolving workplace work items, due information, superseded facts, or decision-relevant state across time.

**Status: open.** Update and report evaluation measure omission, novelty, redundancy, or evolving information in adjacent domains [2405.00982] [2607.19322] [doi-10-1155-2016-1340973] [doi-10-6028-nist-sp-500-321-realtime-overview] [manual-39435af3dd], but not the target work-item-state question.

**Suggested query:** `"omission detection" longitudinal summarization work-item state superseded facts due dates temporal updates decision-relevant information`

## gap-6 — ENGINEERING, HIGH

A target-domain human-review protocol remains an engineering gap: representative or risk-stratified sampling, minimum human-review volume, multi-rater adjudication, confusion matrices, abstention treatment, coverage reporting, and validation of any LLM-assisted judge against independent human judgments remain project-specific choices.

**Status: open.** Active sampling [2406.07967], human/LLM auxiliary estimation [2605.16354], agreement methodology [2606.00093], rating-indeterminacy analysis [manual-32d5793dca], and reproduction evidence [manual-f5ce52cae2] provide ingredients but do not determine the target-domain protocol.

## gap-7 — ENGINEERING, MEDIUM

The corpus demonstrates evaluator-optimization effects, rating indeterminacy, abstention sensitivity, and directional judge bias but does not provide a project-specific procedure for preventing acceptance criteria from being overfit to the same automatic evaluator used during development. Independent holdouts, evaluator separation, and regression checks remain an engineering validation problem.

**Status: open.** Metric optimization effects [2212.08037], abstention-dependent estimands [2606.00093], citation-judge directional bias [2607.08700], and forced-choice validation failures [manual-32d5793dca] establish relevant failure modes without supplying the project-specific procedure.

## gap-8 — ACADEMIC, MEDIUM

Calibration under continuing temporal or distributional change remains open for non-stationary free-form communication streams. The corpus supplies adaptive coverage results, cross-domain calibration studies, benchmark-aging evidence, and structured-generation risk-control results, but not one validated selective-prediction method for continuously changing workplace communication.

**Status: open.** Adaptive conformal inference [2106.00170], dynamically tuned online conformal prediction [2208.08401], strongly adaptive methods [2302.07869], drift-adaptive training-conditional methods [2602.16537], and structured-generation risk-control experiments [2606.29054] substantially deepen the methodological evidence but do not answer the workplace free-form-stream question.

**Suggested query:** `"selective prediction" "non-stationary" free-form generation online calibration concept drift abstention adaptive conformal temporal stream`

# Actionable Insights

- **Synthesis-derived recommendation:** maintain separate evaluation denominators for claim correctness, attribution correctness, evidence completeness, temporal or current-state correctness, report omission, calibration, and abstention rather than combining them into one acceptance score.
- **Synthesis-derived recommendation:** evaluate both atomic units and their higher-level composition so that locally supported claims do not hide entity mixing, contradictory aggregation, or incorrect work-item-level synthesis.
- **Synthesis-derived recommendation:** represent evidence status with more than a binary supported/unsupported outcome, including partial support, insufficient evidence, conflicting evidence, and complementary multi-source support.
- **Synthesis-derived recommendation:** construct temporal evaluation at explicit observation cutoffs and include delayed arrival, out-of-order evidence, supersession, corrected completion, and disagreements between event time and collection time.
- **Synthesis-derived recommendation:** pair omission measurement with repetition or false-alert measurement on longitudinal work-item fixtures, including new, still-open, resolved, superseded, and due states.
- **Synthesis-derived recommendation:** evaluate confidence using risk-coverage or selective-risk behavior under both stable and shifted streams in addition to scalar calibration error.
- **Synthesis-derived recommendation:** keep automated development evaluators separate from final acceptance holdouts, and validate any LLM-assisted judge on independently reviewed samples with directional error reporting.
- **Synthesis-derived recommendation:** preserve abstention as an explicit evaluation outcome and report coverage alongside covered-case accuracy or agreement rather than silently excluding abstained cases.

# Confidence Summary

Evidence is strong for several cross-domain principles at the component level: reliability dimensions are empirically separable; omission and unsupported generation require different measurements; retrieval and generation contribute distinct failures; and selective prediction has meaningful risk-coverage behavior. Evidence is also strong that temporal validity and distribution shift can invalidate otherwise plausible evaluation signals.

Confidence is medium for transfer from summarization, QA, RAG, scientific verification, clinical triage, forecasting, cybersecurity, and news-update tasks to workplace communication. The combined scheme named by this topic remains untested, so the corpus supports well-supported design principles and evaluation mechanisms rather than an empirically validated end-to-end workplace framework.

# Limitations

- This synthesis uses the supplied reduced per-paper analyses rather than full papers, so methodological details, negative findings, and qualifications omitted from those reductions may not be represented.
- Most evidence comes from summarization, QA, RAG, scientific fact verification, open-web research, news updates, forecasting, clinical triage, cybersecurity, or synthetic benchmarks rather than private workplace email and Teams-style communication.
- No admitted paper jointly evaluates all target dimensions. Evidence from papers validating different components therefore does not validate the combined scheme.
- Results span different datasets, tasks, models, definitions of correctness, confidence, coverage, and abstention, making many numerical results unsuitable for direct comparison.
- No direct contradictions were identified under genuinely comparable questions and conditions. Apparent tensions such as in-domain softmax performance versus shifted-domain overconfidence, or adaptive conformal success in forecasting versus ACI failure under structured-generation cross-dataset shift, arise under materially different conditions [doi-10-18653-v1-2021-acl-long-84] [2006.09462] [2106.00170] [2606.29054].
- The supplied records do not contain enough bibliographic metadata for duplicate-study detection beyond visible identifiers and titles. The reported paper count therefore denotes 64 corpus records rather than a guaranteed count of distinct underlying studies.
- Inherited handoffs are treated only as project context and gap provenance. They are not evidence for any finding or for closing any gap.
