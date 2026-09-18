# Executive Summary

This 51-paper corpus provides strong evidence that reliability evaluation for long-form, multi-source generation is inherently multidimensional. Claim correctness, evidence attribution, evidence completeness, temporal validity, omission, confidence calibration, selective risk, and human-review reliability expose different failure modes and are not interchangeable. Fine-grained claim decomposition improves diagnosis, but atomic verification alone can miss cross-claim, entity, temporal, and report-level failures. Completeness remains difficult even with strong or oracle retrieval, while citation presence or topical relevance can substantially overstate factual support. Calibration and selective generation reduce risk in several settings, but coverage trade-offs, changing distributions, metric choice, and feasibility limits remain material. No admitted study validates the complete combination required by this topic, and evidence for continuously evolving workplace communication remains indirect. All seven carried gaps therefore remain open.

# Themes

1. **Correctness, attribution, and completeness are distinct empirical targets.** Attributed-QA and citation-generation work shows that ordinary answer correctness and source support are only partially aligned, while report frameworks separately score missing required content and unsupported or incorrectly cited generated material. Importance-aware factuality work likewise exposes omissions that precision-oriented correctness evaluation cannot detect. [2212.08037] [2305.14627] [2405.00982] [2408.08067] [2604.03141]

2. **Omission remains substantial even after strong evidence acquisition.** In MSRS, oracle retrieval still left strong generators omitting multiple details; DEER and GAMUT find omission-sensitive coverage to be a major source of failure even when reports can appear structurally plausible. Update summarization and importance-aware recall similarly distinguish missing content from repetition or unsupported content. [2508.20867] [2512.17776] [2604.03141] [2607.19322] [manual-39435af3dd]

3. **Fine-grained claim decomposition improves diagnosis, but atomic verification is not sufficient for all global failures.** FactCC and SummaC benefit from localized or sentence-granular verification, and FaStfact reports improved alignment with human claim annotations. D-FActScore demonstrates that individually supportable facts can still form a misleading entity-level narrative, while GAMUT finds structured dependencies that flat lists of independent facts fail to represent. [1910.12840] [2111.09525] [2402.05629] [2510.12839] [2607.19322]

4. **Citation presence and topical relevance materially overstate factual support.** Deep-research citation evaluation finds much lower factual support than link accessibility or topical relevance, and attributed-QA work shows that automatic attribution metrics can become unreliable when directly optimized as system components. Judge benchmarks further show directional false-positive and false-negative differences hidden by aggregate F1. [2212.08037] [2305.14627] [2605.06635] [2607.08700] [doi-10-18653-v1-2025-acl-long-837]

5. **Temporal validity is separate from ordinary factual correctness.** ChronoFact shows substantial gains from explicit chronological reasoning; benchmark-aging work documents cases where stale gold labels penalize currently correct answers; temporal-QA evaluation shows that even oracle-correct answers can cite evidence that was invalid at the required time. Runtime-verification work further demonstrates formal treatment of delayed and out-of-order evidence. [1707.05555] [2410.14964] [2510.07238] [doi-10-1109-access-2026-3679691]

6. **Calibration is not a single interchangeable property.** QA calibration transfers imperfectly across domains, long-form methods can improve linguistic or claim-level calibration under some shifts, and recent uncertainty evaluation shows that minimizing ECE can degrade ranking quality. SURE-RAG likewise reports improved binary ECE without improvement in low-coverage selective risk. [2012.14983] [doi-10-1162-tacl-a-00407] [2604.12046] [2605.03534] [2607.03870]

7. **Selective generation lowers risk only by accepting a coverage trade-off, and certification has feasibility limits.** Selective generation, selective abstraction, and calibration-aware generation all demonstrate risk-versus-information trade-offs. Structured-generation risk-control results show that when base risk exceeds the target, valid distribution-free certification can require substantial abstention or become infeasible at useful coverage. [2307.09254] [2602.11908] [2605.01749] [2606.29054]

8. **Adaptive conformal methods offer useful shift-handling evidence, but not a direct workplace free-form-generation result.** Adaptive conformal inference and strongly adaptive variants improve coverage behavior around distribution changes in their evaluated forecasting and classification-style settings. Drift-aware conformal work provides stronger regret results under abrupt and smooth drift. Structured-generation experiments show that these coverage results do not automatically imply emitted-risk control under genuine cross-dataset shift. [2106.00170] [2302.07869] [2602.16537] [2606.29054]

9. **Contradictory or partially sufficient evidence remains difficult for abstention.** The evidence-sufficiency benchmark reports heavy over-answering when plausible retrieved passages conflict, while SURE-RAG obtains better selective performance from claim-evidence sufficiency aggregation at low coverage. Minimal-evidence research separately shows that minimal sufficient support and exhaustive recovery of all relevant evidence are different objectives. [2605.03534] [doi-10-32604-cmc-2026-086343] [2404.15588]

10. **Human and LLM-judge reliability depends on what is being measured and how abstentions or ambiguous ratings are handled.** System-level automatic metrics can correlate strongly with humans while being weaker at individual-item agreement. Agreement statistics change meaning when abstentions are excluded or recoded, rating indeterminacy can reverse judge selection, and judges with similar aggregate scores can exhibit materially different directional errors. [2212.08037] [2606.00093] [2607.08700] [manual-32d5793dca] [doi-10-18653-v1-w19-8642]

11. **Human-review cost can be reduced in some evaluated settings, but the amount of reduction depends on sampling and auxiliary-judge quality.** CASF preserves full-dataset system rankings more reliably than random or heuristic sampling at the tested sampling levels, while doubly robust LLM-assisted evaluation reduces required human review as prediction quality improves but retains a nonzero floor. Pyramid and reproduction studies also show that system-level conclusions can remain stable under repeated human evaluation even when item-level agreement is weaker. [2406.07967] [2605.16354] [doi-10-1017-s1351324909005051] [manual-f5ce52cae2]

12. **Retrieval quality constrains generation, but additional context or search depth is not monotonically beneficial.** SciFact, citation-generation work, and RAGChecker show retrieval errors feeding downstream verification or generation errors. MSRS finds targeted strong retrieval better than simply providing very long context for the tested model, while deep-research citation experiments find factual support deteriorating as tool-call depth increases. [2004.14974] [2305.14627] [2408.08067] [2508.20867] [2605.06635]

# Contradictions

No direct contradiction met the required comparability criterion in the supplied analyses.

Several apparent tensions were therefore treated as scope qualifications rather than disagreements. FactCC reports benefits from checking a summary sentence against whole-document context [1910.12840], while SummaC reports improvements from sentence-granular NLI comparisons over direct document-level NLI [2111.09525]; the models, comparison procedures, and precise granularity questions differ. Likewise, strong targeted retrieval improves multi-source generation in MSRS [2508.20867], whereas increasing deep-research search depth reduces factual-support accuracy in another setting [2605.06635]; retrieval quality and unbounded evidence accumulation are not the same intervention.

# Open Gaps

- **gap-1 — ACADEMIC, HIGH.** No admitted study validates one end-to-end evaluation scheme that jointly measures claim correctness, evidence attribution correctness, citation or evidence completeness, temporal or current-state correctness, omission, calibrated uncertainty, and abstention while preserving separate denominators. Newer work strengthens individual components but does not close the combination. [2405.00982] [2604.03141] [2606.29054] [2607.19322] [doi-10-1109-access-2026-3679691]  
  Suggested query: `"evaluation framework" factuality attribution "evidence completeness" temporal correctness omission uncertainty abstention "free-form generation"`

- **gap-2 — ENGINEERING, HIGH.** No admitted study directly evaluates private workplace email or Teams-style communication containing the specified combination of revisions, quoted history, conflicting updates, delayed or out-of-order arrival, versioned attachments, and permission-constrained evidence. Existing studies cover pieces of that problem in transfer domains. [1707.05555] [2508.20867] [doi-10-32604-cmc-2026-086343] [doi-10-6028-nist-sp-500-321-realtime-overview] [manual-39435af3dd]

- **gap-4 — ACADEMIC, HIGH.** Minimal evidence groups, partial-support attribution, multi-source aggregation, and temporal validity are individually represented, but the corpus does not establish one general evidence-completeness method that jointly handles compound claims, partial support, complementary sources, and temporally versioned evidence. [2404.15588] [2508.20867] [doi-10-18653-v1-2025-acl-long-837] [doi-10-1109-access-2026-3679691]  
  Suggested query: `"evidence completeness" "compound claims" "partial support" multi-source temporal versioned evidence attribution evaluation`

- **gap-5 — ACADEMIC, HIGH.** Report-level omission now has substantial coverage through ARGUE, DEER, importance-aware recall, GAMUT, update summarization, and real-time summarization, while separate work covers temporal fact verification. The corpus still does not establish omission detection for evolving workplace work items, due information, superseded facts, or decision-relevant state across time. [2405.00982] [2512.17776] [2604.03141] [2607.19322] [2410.14964] [manual-39435af3dd] [doi-10-6028-nist-sp-500-321-realtime-overview]  
  Suggested query: `"omission detection" temporal summarization evolving state superseded information "decision-relevant" longitudinal workplace`

- **gap-6 — ENGINEERING, HIGH.** The corpus provides techniques for constrained sampling, LLM-assisted human estimation, agreement measurement, rating-indeterminacy handling, and reproducibility, but it does not determine the project-specific review volume, risk strata, adjudication process, confusion-matrix contract, abstention treatment, or acceptance thresholds. [2406.07967] [2605.16354] [2606.00093] [manual-32d5793dca] [doi-10-18653-v1-w19-8642] [manual-f5ce52cae2]

- **gap-7 — ENGINEERING, MEDIUM.** Automatic-evaluator optimization effects, rating indeterminacy, abstention sensitivity, and directional judge bias are documented, but the corpus does not provide the project-specific evaluator-isolation, independent-holdout, and regression procedure required to prevent development from overfitting its acceptance evaluator. [2212.08037] [2512.17776] [2606.00093] [2607.08700] [manual-32d5793dca]

- **gap-8 — ACADEMIC, MEDIUM.** Adaptive conformal inference, strongly adaptive online conformal prediction, drift-aware conformal methods, cross-domain linguistic calibration, benchmark-aging studies, and structured-generation risk control strengthen the evidence base for changing distributions. None validates one selective-prediction method for continuously changing workplace free-form communication streams. [2106.00170] [2302.07869] [2404.00474] [2505.23912] [2510.07238] [2602.16537] [2606.29054]  
  Suggested query: `"selective prediction" non-stationary stream "free-form generation" temporal distribution shift calibration abstention`

All seven prior gaps remain **open**; none is resolved by the current cumulative corpus.

# Actionable Insights

- **synthesis-derived recommendation:** Keep separate evaluation denominators for claim correctness, attribution correctness, evidence completeness, temporal or current-state correctness, omission and repetition, confidence calibration, and selective risk rather than compressing them into one reliability score.
- **synthesis-derived recommendation:** Evaluate both atomic claims and report-level structure so that support for individual statements does not conceal cross-claim entity, temporal, aggregation, or coverage failures.
- **synthesis-derived recommendation:** Treat evidence sufficiency and evidence completeness as separate objectives, and separately record minimal sufficient evidence, missing complementary evidence, and unsupported generated content.
- **synthesis-derived recommendation:** Evaluate evidence against explicit observation cutoffs and source versions, retaining late-arriving, stale, superseded, contradictory, and out-of-order cases as distinct test conditions.
- **synthesis-derived recommendation:** Pair calibration metrics such as ECE or Brier score with ranking and selective-decision measurements such as AUROC, risk-coverage curves, AURC, coverage, and emitted risk; a gain on one metric should not be interpreted as a gain on all uncertainty properties.
- **synthesis-derived recommendation:** Make abstention an explicit scored outcome and report its coverage together with false acceptance, false rejection, and unresolved or conflicting-evidence rates rather than evaluating only answered cases.
- **synthesis-derived recommendation:** Use independent human-reviewed holdouts for acceptance testing and keep development-time automatic judges separate from final evaluation so optimization against one evaluator cannot silently define success.
- **synthesis-derived recommendation:** Build target-domain adversarial fixtures for revisions, quoted history, conflicting updates, delayed arrival, versioned attachments, permission restrictions, omissions, and stale evidence before transferring conclusions from summarization, QA, RAG, or conformal-prediction benchmarks to workplace communication.

# Confidence Summary

Evidence confidence is **HIGH** for the general empirical separation of correctness, attribution, completeness, temporal validity, omission, calibration, and selective-risk dimensions; for the existence of risk-coverage trade-offs; and for important limitations of automatic judges and citation-presence metrics. Evidence is **MEDIUM** for human-review cost reductions because results depend on sampling and auxiliary-judge quality.

Transfer confidence to continuously evolving private workplace communication is substantially lower. Most evidence comes from summarization, QA, RAG, report generation, temporal verification, forecasting, or synthetic/adversarial benchmarks. The corpus therefore supports well-supported evaluation principles and failure modes, but not a validated integrated workplace evaluation scheme.

# Limitations

- This synthesis uses the supplied research questions and top findings rather than full paper text, raw claims, complete tables, or full methodological descriptions; reported numbers were not independently re-verified.
- No admitted study directly evaluates private workplace email or Teams-style communication, so workplace-production conclusions would be transfer claims rather than direct evidence.
- Much of the non-stationary and temporal evidence comes from runtime monitoring, forecasting, conformal prediction, temporal QA, or benchmark aging rather than continuously evolving free-form workplace generation.
- Several evaluation studies rely partly on LLM judges or automatic entailment and attribution models. Some provide human validation, but validation strength varies by task and aggregation level.
- The corpus contains substantial evidence for individual dimensions and smaller combinations, but no paper validates their complete joint operation; separately validated components do not establish the combined scheme.
- Apparent methodological tensions were excluded from `contradictions` when tasks, interventions, definitions, or datasets were not sufficiently comparable.
- Inherited handoffs from earlier project topics were treated strictly as scoping context and were not used as evidence for findings or gap closure.
- No duplicate study was identifiable from the supplied titles among these 51 records, although the reduced metadata does not permit a full bibliographic duplicate audit beyond the information provided.
