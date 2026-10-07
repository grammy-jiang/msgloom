# Executive Summary

Across 37 supplied analyses, the literature converges on a decomposed view of reliability: factual correctness, attribution correctness, evidence completeness, temporal validity, omission, calibration, and abstention behave as separable evaluation dimensions. Fine-grained claims, rationales, content units, and temporal evidence checks improve diagnosis, while retrieval quality strongly constrains downstream generation without eliminating omission or misuse even under oracle evidence. Selective-generation and claim-level calibration work now directly address free-form outputs, resolving the prior gap on whether such methods exist, but their guarantees remain task- and shift-dependent. Report-level omission is now measured more explicitly by DEER, ARGUE, GAMUT, and multi-source RAG benchmarks, yet no study covers evolving workplace communication end to end. Human and LLM judging evidence also shows that agreement, abstention handling, directional bias, and evaluator optimization materially affect conclusions. The combined cross-dimensional evaluation scheme remains unvalidated.

# Themes

## 1. Reliability dimensions are separable

Across QA, citation-grounded generation, temporal QA, and report-generation studies, answer correctness, attribution support, evidence completeness, temporal evidence validity, and omission produce materially different scores and failure patterns rather than acting as interchangeable measures. Attributed QA finds only moderate alignment between ordinary answer quality and attribution quality [2212.08037]. Citation-generation work separately evaluates answer correctness, citation recall, and citation precision and finds substantial unsupported generated content [2305.14627]. Temporal QA shows that even an oracle-correct answer can be paired with temporally invalid evidence [doi-10-1109-access-2026-3679691]. Auto-ARGUE and DEER separately operationalize coverage or omission rather than treating factuality alone as complete report evaluation [2509.26184] [2512.17776]. GAMUT likewise identifies omitted rubric elements as a dominant failure mode [2607.19322].

**Finding confidence: HIGH.**

## 2. Fine-grained units improve diagnostic resolution

Sentence-, claim-, rationale-, and content-unit decomposition improves diagnostic resolution or calibration in several evaluated domains. FactCC localizes source and claim spans in addition to classifying consistency [1910.12840]. SciFact ties verification decisions to minimal sentence-level rationales [2004.14974]. SummaC reports better inconsistency detection when document-level evaluation is decomposed into finer NLI comparisons [2111.09525]. Claim-level confidence calibration provides more actionable uncertainty than response-level confidence on mixed-correctness factual outputs [2608.22483]. The Pyramid Method provides reliable content-unit-based system comparisons across summarization settings [doi-10-1017-s1351324909005051].

**Finding confidence: HIGH.**

## 3. Retrieval quality constrains generation, but oracle evidence does not close the problem

Retrieval and evidence coverage contribute substantially to end-to-end error. SciFact oracle experiments attribute material error to both document retrieval and rationale selection [2004.14974]. Citation-generation experiments find retrieval quality strongly constraining answer and citation quality, while relevant evidence still does not guarantee successful use by the generator [2305.14627]. MSRS reports generation quality increasing with stronger retrieval and oracle evidence, yet oracle-retrieval outputs still omit major and minor details [2508.20867]. Temporal QA similarly identifies first-stage retrieval coverage as the dominant error source in its analysis [doi-10-1109-access-2026-3679691].

**Finding confidence: HIGH.**

## 4. Omission remains substantial even with relevant evidence available

MSRS reports omissions under oracle retrieval, including multiple minor details and, on the meeting benchmark, multiple major details [2508.20867]. DEER explicitly separates Coverage from Quality and finds that plausible report structure does not imply complete task fulfillment [2512.17776]. GAMUT reports omission as the dominant factual-completeness failure mode, with structured requirements missed even by the strongest evaluated systems [2607.19322].

**Finding confidence: HIGH.**

## 5. Dedicated calibration signals outperform raw confidence in several evaluated settings

Raw likelihood or uncalibrated confidence is unreliable in multiple tasks. Generative QA models can be accurate while remaining poorly calibrated [doi-10-1162-tacl-a-00407]. The conversational-calibration study reports strong overconfidence and improves the relationship between confident language and factual correctness without materially increasing overall factual accuracy [2012.14983]. Token-level self-evaluation substantially outperforms raw sequence likelihood for selective generation on TruthfulQA [2312.09300]. Linguistic-calibration training, RL-trained verbalized confidence, claim-level factual calibration, and calibration-aware selective commitment each improve confidence-quality relationships in their reported long-form settings [2404.00474] [2505.23912] [2604.12046] [2605.01749].

**Finding confidence: HIGH.**

## 6. Free-form selective generation now has direct methodological evidence

The prior corpus gap concerning direct selective prediction for free-form outputs is now answered by several studies. Selective Generation for Controllable Language Models provides PAC-style control of entailment-based false discovery under its assumptions [2307.09254]. CURE reports claim-level confidence thresholding with explicit factual-accuracy versus factual-recall trade-offs [2604.12046]. Calibration-Aware Generation selectively commits to content according to reliability estimates and exposes a factuality-versus-coverage trade-off [2605.01749]. Conformal risk-control work for structured generation characterizes when certification is feasible and when base risk or distribution shift makes requested guarantees unattainable [2606.29054].

**Finding confidence: HIGH.**

## 7. Calibration behavior under shift is method- and guarantee-dependent

Adaptive Conformal Inference provides a distribution-free long-run average miscoverage guarantee and tracks changing coverage in its election-night experiment [2106.00170]. Linguistic calibration retains improvements on several held-out QA domains and a biography task [2404.00474]. In contrast, QA temperature scaling transfers imperfectly and can over-correct on a changed evaluation domain [doi-10-1162-tacl-a-00407]. For structured LLM outputs, static conformal risk control and ACI both violate emitted-risk targets in most tested genuine cross-dataset transfers when the target base risk is infeasible, while a full-feedback anytime-valid monitor remains valid in those reported experiments [2606.29054].

These are scope-qualified results rather than direct contradictions: the methods, guarantees, tasks, and definitions of risk or coverage differ.

**Finding confidence: HIGH.**

## 8. Contradictory evidence is a difficult abstention condition

The evidence-sufficiency RAG benchmark finds that complete absence is generally easier for models to recognize than internal contradiction between plausible evidence passages. All seven evaluated models substantially over-answer under the strongest conflicting-evidence condition, and six of seven show significant sensitivity to conflicting-passage order [doi-10-32604-cmc-2026-086343].

**Finding confidence: HIGH.**

## 9. Temporal evidence validity is distinct from ordinary correctness

Temporal QA experiments show that oracle-correct answers can still cite evidence invalid at the query time, and a temporal reranker materially improves temporal-validity recall [doi-10-1109-access-2026-3679691]. ChronoFact reports large gains from explicit chronology modeling on complex temporal claims, with the chronological-order classifier producing the largest ablation degradation [2410.14964]. Runtime-verification work establishes sound and observationally complete monitoring semantics for out-of-order observations, with monotonic refinement of three-valued verdicts [1707.05555].

**Finding confidence: HIGH.**

## 10. LLM judging results depend materially on validation design

AutoAIS correlates strongly with human attribution ratings at the system level but less reliably at the individual-question level [2212.08037]. Agreement-measurement work shows that abstention exclusion, recoding, or retention changes the estimand and can materially alter headline accuracy [2606.00093]. Citation-verifier experiments find that judges with similar aggregate F1 can differ substantially in false-positive and false-negative behavior, and cost does not track accuracy [2607.08700]. Human-review augmentation work provides valid estimators that reduce review requirements when LLM ratings predict human judgments, with diminishing returns and a nonzero human-review floor [2605.16354]. CASF shows that constrained active sampling can preserve full-dataset system rankings more reliably than random sampling in the evaluated NLG datasets [2406.07967].

**Finding confidence: HIGH.**

## 11. Evaluation proxies can degrade under optimization or operating-regime change

Using AutoAIS itself to select attributions created outlier systems whose automatic attribution scores were more favorable than human judgments [2212.08037]. In deep-research attribution experiments, increasing search depth from 2 to 150 tool calls reduced factual-support accuracy substantially even though link validity and topical relevance remained comparatively stable [2605.06635]. Together these studies show two distinct proxy failures: direct optimization against an automatic evaluator and degradation of the target property while easier surface indicators remain stable.

**Finding confidence: MEDIUM.**

# Contradictions

No direct contradictions met the required comparability criterion.

Several apparent tensions were retained as scope qualifications rather than labeled contradictions:

- Adaptive conformal inference reports successful long-run coverage adaptation [2106.00170], whereas conformal risk-control experiments report frequent emitted-risk violations under genuine cross-dataset shift [2606.29054]. These studies evaluate different guarantees, prediction structures, and shift regimes.
- Linguistic calibration retains gains across several held-out domains [2404.00474], whereas post-hoc QA temperature scaling transfers imperfectly [doi-10-1162-tacl-a-00407]. These are different calibration methods and tasks.
- Stronger retrieval improves multi-source generation [2508.20867], while increasing deep-research search depth can reduce citation factual support [2605.06635]. Retrieval quality and completeness are not equivalent to the number of search steps, so the experiments do not answer the same question under comparable conditions.

# Open Gaps

## gap-1 — ACADEMIC — HIGH

No admitted study validates one end-to-end evaluation scheme that jointly measures claim correctness, evidence attribution correctness, citation or evidence completeness, temporal or current-state correctness, omission, calibrated uncertainty, and abstention while preserving separate denominators for those dimensions. The corpus validates individual components and smaller combinations.

Suggested query: `"evaluation framework" factuality attribution citation completeness temporal correctness omission uncertainty abstention free-form generation`

**Status: open.** New work adds report omission, temporal validity, selective generation, factual completeness, and judge-validation components [2509.26184] [2512.17776] [2607.19322] [2608.22483] [doi-10-1109-access-2026-3679691], but not the complete combined scheme.

## gap-2 — ENGINEERING — HIGH

The corpus contains no direct evaluation on private workplace email or Teams-style communication with realistic revisions, quoted history, conflicting updates, delayed or out-of-order arrival, versioned attachments, and permission-constrained evidence. Target-domain fixtures and gold data remain an engineering validation gap.

**Status: open.** Adjacent-domain studies cover out-of-order temporal monitoring [1707.05555], multi-source synthesis [2508.20867], deep-research attribution [2605.06635], and temporally valid evidence [doi-10-1109-access-2026-3679691], but not the specified target domain.

## gap-3 — RESOLVED

The prior academic gap concerning calibrated selective prediction for free-form generation is resolved at the level of whether direct methods exist. Entailment-based selective generation supplies PAC-style control under its assumptions [2307.09254]; CURE evaluates claim-level selective prediction in long-form generation [2604.12046]; Calibration-Aware Generation selectively commits to sufficiently reliable content [2605.01749]; and structured-generation conformal risk-control work analyzes certification feasibility and shift failures [2606.29054].

The remaining question of continuing non-stationary workplace streams remains separate under gap-8.

## gap-4 — ACADEMIC — HIGH

The corpus does not establish a general evidence-completeness method that jointly handles compound claims, partially supportive evidence, multiple complementary sources, and temporally versioned evidence.

Minimal evidence groups address collective sufficiency and redundancy [2404.15588]. CAQA addresses partial support and compositional attribution [doi-10-18653-v1-2025-acl-long-837]. MSRS addresses multi-source aggregation [2508.20867]. Program-verifiable temporal QA addresses evidence validity at a query time [doi-10-1109-access-2026-3679691]. Their combination remains untested.

Suggested query: `"evidence completeness" compound claims partial support multi-source temporal versioned evidence attribution evaluation`

**Status: open.**

## gap-5 — ACADEMIC — HIGH

Report-level omission now has substantially stronger evidence than in the previous round. Auto-ARGUE operationalizes nugget recall [2509.26184], DEER separates Coverage from Quality [2512.17776], GAMUT evaluates structured factual completeness [2607.19322], and MSRS measures missing major and minor information in multi-source generation [2508.20867].

No admitted study establishes omission detection for evolving workplace work items, due information, superseded facts, or decision-relevant state across time.

Suggested query: `"report completeness" omission evolving information decision-relevant temporal summarization workplace`

**Status: open.**

## gap-6 — ENGINEERING — HIGH

A target-domain human-review protocol remains an engineering gap. Relevant literature covers active sampling [2406.07967], principled human-LLM augmentation [2605.16354], abstention-sensitive agreement reporting [2606.00093], rating indeterminacy [manual-32d5793dca], reproduction variability [manual-f5ce52cae2], and the distinction between agreement and correlation [doi-10-18653-v1-w19-8642]. Selection of representative or risk-stratified sampling, review volume, adjudication, confusion matrices, abstention treatment, and project acceptance criteria remains project-specific.

**Status: open.**

## gap-7 — ENGINEERING — MEDIUM

The corpus demonstrates evaluator optimization effects and directional judge bias. AutoAIS-based attribution selection can create automatic-human outliers [2212.08037], and citation judges with similar aggregate F1 can exhibit materially different directional errors [2607.08700]. No admitted paper supplies a project-specific development-versus-acceptance evaluator-separation and regression procedure.

**Status: open.**

## gap-8 — ACADEMIC — MEDIUM

Calibration under continuing temporal or distributional change remains open for non-stationary free-form communication streams. Adaptive conformal inference provides long-run sequential coverage results [2106.00170]. Linguistic calibration shows some out-of-domain transfer [2404.00474]. Static benchmarks can become temporally misaligned with current facts [2510.07238]. QA calibration transfer is imperfect [doi-10-1162-tacl-a-00407]. Structured-generation conformal risk-control experiments expose both feasibility limits and failures under genuine cross-dataset shift [2606.29054].

No admitted study validates calibrated selective prediction on a continuing non-stationary workplace communication stream.

Suggested query: `"selective prediction" non-stationary stream free-form generation temporal distribution shift calibration abstention`

**Status: open.**

# Actionable Insights

- **Synthesis-derived recommendation:** maintain separate evaluation denominators for claim correctness, source-attribution correctness, evidence completeness or omission, temporal validity, uncertainty calibration, and abstention or coverage rather than collapsing them into one reliability score.
- **Synthesis-derived recommendation:** evaluate both claim-level units and report-level coverage; use fine-grained units for support and confidence diagnostics while retaining a separate report-wide mechanism for detecting omitted decision-relevant content.
- **Synthesis-derived recommendation:** separate retrieval failure from generation failure through paired end-to-end and oracle-evidence evaluations so missing evidence is distinguishable from failure to use available evidence.
- **Synthesis-derived recommendation:** report selective behavior with risk-coverage curves, covered error, total coverage, false-answer and false-abstention counts, and explicit treatment of abstained cases.
- **Synthesis-derived recommendation:** construct temporal evaluation examples around observation cutoffs and versioned evidence so evidence that became available later cannot leak into earlier predictions.
- **Synthesis-derived recommendation:** validate any LLM judge against an independent human-reviewed sample and retain directional false-positive and false-negative analysis rather than relying only on aggregate correlation or F1.
- **Synthesis-derived recommendation:** keep development-time evaluators separate from acceptance-time holdouts and include regression cases specifically targeting evaluator gaming or proxy optimization.
- **Synthesis-derived recommendation:** include contradictory, partially supportive, multi-source, stale, and missing-evidence cases in abstention evaluation rather than testing only complete evidence and complete absence.
- **Synthesis-derived recommendation:** evaluate calibration repeatedly across chronological replay windows or other controlled distribution shifts so calibration drift and local coverage failures remain visible.

# Confidence Summary

Confidence is high that the corpus supports decomposed reliability evaluation, fine-grained claim or evidence units, explicit omission measurement, and risk-versus-coverage analysis as well-supported evaluation principles. Confidence is also high that free-form selective generation now has direct methodological evidence, although no single method dominates across tasks or shifts.

Evidence for temporal validity and distribution-shift behavior is substantial but heterogeneous. It spans runtime monitoring [1707.05555], adaptive conformal prediction [2106.00170], temporal fact verification [2410.14964], benchmark aging [2510.07238], structured-generation risk control [2606.29054], and temporal QA evidence validation [doi-10-1109-access-2026-3679691]. These results do not constitute direct validation on one common production setting.

Confidence is medium for transfer to continuously changing workplace communication because no admitted paper evaluates the complete target domain. The corpus does not validate the combined end-to-end scheme formed by joining individually supported components.

# Limitations

- The supplied material consists of reduced per-paper analyses containing research questions and selected top findings rather than full papers; this synthesis therefore depends on the fidelity and completeness of those analyses.
- No admitted study directly evaluates the complete private workplace-email or Teams-style setting described by the project. Findings from QA, summarization, deep research, RAG, temporal verification, and runtime monitoring are transfer evidence rather than production-domain validation.
- Papers validating different components do not jointly validate their combination. Evidence for claim calibration, omission scoring, temporal validity, attribution verification, and human-review sampling comes from different experimental settings.
- No direct contradictions were identified under the requirement that both papers answer the same question under comparable conditions. Apparent tensions involving calibration transfer, adaptive conformal behavior, retrieval strength, and research depth involve different methods, objectives, or operating conditions.
- The inherited handoffs from earlier project Topics are treated only as contextual starting conditions and do not support any finding or gap-status decision in this synthesis.
- The corpus includes several newly proposed 2026 benchmarks and methods whose independent replication breadth is not established in the supplied analyses.
- Human- and LLM-judge validation studies cover different rating scales, abstention conventions, sampling schemes, and domains, limiting direct numerical comparison across them.
