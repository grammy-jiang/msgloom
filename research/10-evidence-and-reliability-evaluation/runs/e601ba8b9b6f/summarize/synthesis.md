# Executive Summary

Across 17 distinct studies, the literature supports decomposing reliability into multiple independently measurable dimensions rather than treating factuality, attribution, completeness, temporal validity, confidence, and abstention as one score. Citation presence or topical relevance does not establish factual support, and source support does not establish source truth or currency. Evidence localization can improve verification and human review, while retrieval remains a major source of error and additional context can sometimes degrade synthesis. Temporal ordering and benchmark aging introduce failure modes invisible to static claim checking. Raw model confidence is often miscalibrated, particularly under domain shift, and contradictory evidence produces substantial over-answering. Automatic judges can assist evaluation but require human validation because aggregate agreement can conceal instance-level errors, directional bias, abstention effects, and metric gaming. Direct evidence for private workplace communication remains absent.

# Themes

- **Reliability is multidimensional.** Answer correctness, evidence support, citation precision, citation completeness, source accessibility, temporal validity, confidence calibration, and abstention represent different evaluation targets rather than interchangeable labels [2212.08037] [2305.14627] [2605.06635].
- **Traceable evidence can accompany semantic verification.** FactCC predicts source and claim spans, and SciFact evaluates sentence-level rationales supporting or refuting a claim [1910.12840] [2004.14974].
- **Retrieval and evidence use are separate problems.** Retrieval errors materially affect verification, but having relevant evidence available does not guarantee that generation or verification will use it correctly [2004.14974] [2305.14627].
- **Temporal reliability is not reducible to static factual support.** Event order can change a verdict, while static benchmark answers can become outdated and make later correct information appear erroneous [2410.14964] [2510.07238].
- **Accuracy and confidence are distinct.** High task accuracy can coexist with poor calibration and unsafe answering under insufficient or contradictory evidence [doi-10-1162-tacl-a-00407] [doi-10-32604-cmc-2026-086343].
- **Evaluator reliability depends on measurement protocol.** Abstention rules, coverage, class marginals, directional errors, and aggregation choices materially affect what a reported agreement number means [2606.00093] [2607.08700].
- **Human evaluation also requires validation.** Sampling strategy, annotator protocol, documentation, and the distinction between aggregate and item-level agreement affect reproducibility and interpretation [2406.07967] [doi-10-1017-s1351324909005051] [manual-f5ce52cae2].

# Findings

1. Across attributed QA, citation-generation, and deep-research evaluation, separately scoring answer correctness, citation support, citation coverage or recall, citation precision, link accessibility, and topical relevance exposes failures that are hidden when those dimensions are treated as interchangeable. [2212.08037] [2305.14627] [2605.06635] **Confidence: HIGH.**

2. In scientific claim verification and news summarization, verification systems can associate verdicts with sentence- or span-level evidence. In the FactCC human study, showing predicted evidence spans reduced mean annotation time and increased inter-annotator agreement. [1910.12840] [2004.14974] **Confidence: HIGH.**

3. Evidence retrieval and evidence use are separate error sources in the evaluated systems. Oracle retrieval or rationales improve SciFact verification; ALCE shows that relevant evidence in context does not guarantee successful use and that adding passages need not proportionally improve results; and the two-model deep-research search-depth experiment found factual citation support decreasing as search depth increased. [2004.14974] [2305.14627] [2605.06635] **Confidence: HIGH.**

4. Temporal evaluation can change a factual verdict even when individual events appear independently supported. ChronoFact's chronological-order component materially improved temporal fact verification, while benchmark-aging experiments showed that stale gold answers and stale supplied context can penalize or redirect answers that better match later information. [2410.14964] [2510.07238] **Confidence: HIGH.**

5. In formal runtime monitoring over synthetic out-of-order event streams, an explicit unknown truth value permits missing information to remain unresolved, Boolean verdicts remain stable under observation refinement, and the proposed monitor is sound and observationally complete for its defined semantics without assuming timestamp-ordered arrival. This is formal and synthetic-stream evidence, not workplace-communication validation. [1707.05555] **Confidence: HIGH.**

6. High answer accuracy does not imply reliable confidence or abstention behavior in the evaluated QA settings. Generative QA models can remain overconfident when wrong, calibration transfers imperfectly across domains, and all seven models in the evidence-sufficiency benchmark over-answered more than 65% of conflicting-evidence cases. [doi-10-1162-tacl-a-00407] [doi-10-32604-cmc-2026-086343] **Confidence: HIGH.**

7. Evaluator protocol choices can materially alter reported reliability without changing underlying model outputs. Abstention handling changes the estimand and generated large accuracy differences in reconstructed judge evaluations, while citation judges with similar aggregate F1 displayed substantially different false-positive, false-negative, and pass-rate biases. [2606.00093] [2607.08700] **Confidence: HIGH.**

8. Human-evaluation conclusions depend on sampling and reporting granularity. Constrained active sampling preserved full-dataset NLG rankings better than random sampling in the reported experiments; Pyramid evaluations showed strong system-level robustness to annotator choice; and a clinical-text replication reproduced aggregate system ordering despite considerably weaker agreement at the individual-item level. [2406.07967] [doi-10-1017-s1351324909005051] [manual-f5ce52cae2] **Confidence: HIGH.**

9. LLM judges can be useful auxiliary evaluators without being interchangeable with human ground truth. AutoAIS showed strong system-level correlation but weaker instance-level agreement and became misleading for systems optimized against it; citation judges exhibit directional biases; and the LLM-assisted sampling framework explicitly retains human ratings as the inferential target. [2212.08037] [2607.08700] [2605.16354] **Confidence: HIGH.**

10. Evidence attribution establishes a relationship between a claim and a cited source, not the independent truth, authority, or currency of the source itself. This limitation is stated explicitly in attributed QA, scientific verification, and deep-research citation evaluation. [2212.08037] [2004.14974] [2605.06635] **Confidence: HIGH.**

# Contradictions

No direct contradiction meeting the required same-question, comparable-conditions test was identified.

Several apparent tensions are scope qualifications rather than contradictions. FactCC checks a summary sentence against the full source document because individual source sentences may be insufficient [1910.12840], whereas SummaC finds finer-grained NLI comparisons superior to applying sentence-trained NLI directly to whole-document inputs [2111.09525]. These studies use different model formulations and comparison conditions and therefore do not answer the same granularity question.

Likewise, useful source context improves some verification settings [1910.12840] [2004.14974], while ALCE reports diminishing or negative returns from adding more retrieved passages [2305.14627], and a two-model deep-research ablation finds lower citation support at larger search depths [2605.06635]. These results concern different tasks, retrieval regimes, and amounts of context; they do not establish opposing conclusions under comparable conditions.

# Open Gaps

### gap-1 — ENGINEERING — HIGH

No admitted study validates one end-to-end evaluation scheme that jointly measures claim correctness, evidence attribution correctness, citation or evidence completeness, temporal/current-state correctness, omission, calibrated uncertainty, and abstention while preserving separate denominators. The corpus validates individual components or smaller combinations [2212.08037] [2305.14627] [2510.07238] [2606.00093].

### gap-2 — ENGINEERING — HIGH

The corpus contains no direct evaluation on private workplace email or Teams-style communication with realistic revisions, quoted history, conflicting updates, delayed or out-of-order arrival, versioned attachments, and permission-constrained evidence. Target-domain fixtures and gold data therefore remain an engineering validation gap. The admitted studies instead use domains including news [1910.12840] [2111.09525], scientific literature [2004.14974], Wikipedia and open-domain QA [2212.08037] [2510.07238], public web research [2605.06635], and synthetic or controlled temporal conditions [1707.05555] [2410.14964].

### gap-3 — ACADEMIC — HIGH

Calibration and selective prediction for unconstrained free-form generation remain insufficiently answered by this corpus. The calibration study explicitly excludes unrestricted free-form abstractive QA [doi-10-1162-tacl-a-00407], while the evidence-sufficiency benchmark evaluates controlled answer-versus-abstain behavior rather than calibrated probabilities for arbitrary generated outputs [doi-10-32604-cmc-2026-086343].

**Suggested query:** `"selective prediction" free-form generation calibration domain shift NLP abstention risk coverage`

### gap-4 — ACADEMIC — HIGH

The corpus does not establish a general evidence-completeness method for compound claims, partial support, multi-source support, and temporally versioned evidence. ALCE evaluates citation recall and precision but identifies limitations in partial-support evaluation [2305.14627], while attributed QA uses a narrower fully-supported-passage criterion [2212.08037].

**Suggested query:** `"citation completeness" multi-source partial support compound claims temporal versioned evidence attribution evaluation`

### gap-5 — ACADEMIC — HIGH

Report-level omission and coverage of decision-relevant content remain underexplored. Pyramid evaluates weighted content units in summary evaluation [doi-10-1017-s1351324909005051], and ALCE measures whether generated claims receive citation support [2305.14627], but neither establishes omission detection for evolving workplace work items or due information.

**Suggested query:** `"summary completeness" omission detection content units decision-focused evaluation factual coverage`

### gap-6 — ENGINEERING — HIGH

A target-domain human-review protocol still has to specify representative or risk-stratified sampling, minimum human-review volume, multi-rater adjudication, confusion matrices, abstention handling, coverage reporting, and validation of any LLM-assisted judge against independent human judgments. Relevant components are studied separately by CASF, LLM-assisted sampling, agreement-protocol analysis, and replication work [2406.07967] [2605.16354] [2606.00093] [manual-f5ce52cae2].

### gap-7 — ENGINEERING — MEDIUM

The corpus demonstrates evaluator gaming and directional judge bias but does not provide a project-specific procedure for preventing optimization against the same automatic evaluator used for acceptance. AutoAIS-based attribution selection produced outlier systems relative to human judgments [2212.08037], while citation judges with similar aggregate scores can possess materially different error profiles [2607.08700]. Independent holdouts, evaluator separation, and regression checks therefore remain an engineering validation problem.

### gap-8 — ACADEMIC — MEDIUM

Calibration under continuing temporal or distributional change remains open in this corpus. Cross-domain calibration transfer is imperfect [doi-10-1162-tacl-a-00407], and benchmark aging changes which answer should be treated as current [2510.07238], but no admitted paper establishes calibrated selective prediction for a non-stationary communication stream.

**Suggested query:** `"uncertainty calibration" non-stationary streams temporal distribution shift language models selective prediction`

No prior-round synthesis gap identifiers were supplied with this task, so `gap_status` contains no prior gaps to classify.

# Actionable Insights

- **Synthesis-derived recommendation:** maintain separate evaluation outputs for semantic claim correctness, attribution correctness, evidence completeness, temporal/current-state validity, omission, calibrated confidence, and abstention rather than collapsing them into one reliability score.
- **Synthesis-derived recommendation:** represent every decision-relevant generated claim as an independently reviewable unit linked to the exact evidence used for that assessment, while allowing multiple evidence items and unresolved support.
- **Synthesis-derived recommendation:** evaluate retrieval failure, evidence-selection failure, reasoning failure, stale-evidence failure, unsupported generation, and omission as distinguishable error categories so one stage cannot hide another stage's errors.
- **Synthesis-derived recommendation:** treat unknown, conflicting, insufficient, and not-yet-currently-resolvable states as explicit outcomes rather than forcing binary supported/unsupported decisions.
- **Synthesis-derived recommendation:** keep automatic judges auxiliary to independently defined gold or human-reviewed targets; measure false-positive and false-negative behavior separately and retain raw contingency data rather than only aggregate agreement scores.
- **Synthesis-derived recommendation:** use held-out or independently reviewed acceptance samples that are not optimized by the same evaluator used during development, and include difficult disagreement cases instead of validating only average cases.
- **Synthesis-derived recommendation:** construct target-domain longitudinal fixtures with revisions, cancellations, contradictory updates, stale late arrivals, out-of-order ingestion, missing evidence, and version changes, and evaluate at explicit observation cutoffs.
- **Synthesis-derived recommendation:** record evaluator protocol metadata including target population, judgment scale, abstention rule, coverage, aggregation procedure, sampling method, source version or observation time, and human-adjudication procedure so results remain reconstructible.

# Confidence Summary

The corpus provides well-supported design principles for decomposed reliability evaluation, evidence localization, temporal validation, calibration, abstention measurement, and human validation of automatic judges. Confidence is highest for the claim that these dimensions expose distinct failure modes because several independent studies demonstrate this across summarization, QA, scientific verification, web research, and evaluation methodology. Confidence in direct transfer to workplace communication is substantially lower: none of the admitted studies evaluates a private email-and-Teams stream with the project's combination of permissions, revisions, versions, temporal state, omissions, and user-specific decision relevance. The component principles are therefore well supported, while their combined operation in the target domain remains untested.

# Limitations

- No admitted paper directly evaluates private workplace email or Teams communication; most evidence comes from news summarization, open-domain QA, scientific fact verification, Wikipedia, web research, synthetic temporal benchmarks, or general NLG evaluation.
- Several strong results concern transfer domains or synthetic data. ChronoClaims is largely synthetic [2410.14964], the runtime-monitoring experiments use synthetic banking-compliance streams [1707.05555], and the evidence-sufficiency benchmark derives controlled conditions from SQuAD and HotpotQA [doi-10-32604-cmc-2026-086343]. None establishes production workplace accuracy.
- The corpus validates multiple components of a reliability framework separately, but no paper validates their combination as one end-to-end scheme.
- Some automatic-evaluation results depend on NLI or LLM judges whose own errors, biases, and prompt sensitivity are documented within the corpus [2212.08037] [2305.14627] [2605.06635] [2607.08700].
- Temporal-currentness evidence is limited. The benchmark-aging study uses a fixed July 2025 retrieval window [2510.07238], and cited public web content in deep-research evaluation can change after evaluation [2605.06635].
- Human-evaluation evidence spans different constructs, annotator populations, sampling strategies, and aggregation levels, so robust system ranking in one study should not be interpreted as universal human-label reliability [2406.07967] [doi-10-1017-s1351324909005051] [manual-f5ce52cae2].
- No duplicate titles were present among the 17 supplied analyses, so this synthesis treats them as 17 distinct studies; it does not infer stronger independence than the supplied records establish.
- Inherited handoffs from earlier project Topics were treated only as project context and were not used as evidence for findings or gaps in this synthesis.
- No prior-round synthesis gap identifiers were supplied in the task, so there are no prior gaps to classify in `gap_status`.
