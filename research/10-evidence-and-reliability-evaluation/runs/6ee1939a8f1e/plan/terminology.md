# evaluation of calibrated abstention, evidence completeness, and omission for free-form multi-source generation under temporal and distributional change academic terminology analysis

## Product problem

The target is not a generic hallucination detector and not one aggregate reliability score. The academic mapping must preserve at least these distinct evaluation objects:

- correctness of each generated claim against evidence;
- correctness of the claim-to-source attribution;
- completeness of evidence or citations for all support-requiring claims;
- current-state correctness when evidence is revised, superseded, conflicting, delayed, or versioned;
- report/content coverage and omission of important information;
- probability calibration rather than raw model confidence;
- selective risk and useful coverage when the system abstains;
- human-review reliability and validation of automatic or LLM-based judges.

The strongest search vocabulary therefore combines **atomic factuality**, **attributed generation**, **citation recall/coverage**, **content selection and omission**, **selective generation**, **risk-coverage**, **calibration**, and **temporal/distribution-shift evaluation**.

Several inherited gaps are explicitly ENGINEERING gaps. Academic literature can supply annotation, sampling, calibration, evaluator-validation, and risk-control machinery, but it cannot by itself create msgloom-specific private workplace gold data or decide project-specific error costs.

## Seed keyword audit

| Seed | Academic meaning | Fit | Main risk |
| --- | --- | --- | --- |
| factual consistency evaluation | Whether generated text is semantically consistent with supplied source material, especially in summarization. | STRONG | Usually measures generated claims only; does not establish omission, attribution completeness, current state, or calibration. |
| factuality evaluation | Whether generated statements are factually correct relative to evidence or external knowledge. | STRONG | Mixes source-grounded factuality and world-truth factuality. |
| summarization faithfulness | Whether an abstractive summary is licensed by its source rather than unsupported or contradictory. | STRONG | Faithfulness is not completeness. |
| hallucination evaluation | Broad evaluation of unsupported, fabricated, contradictory, or ungrounded output. | MODERATE | Overloaded umbrella that collapses error types this project must separate. |
| claim decomposition | Breaking free-form text into independently assessable propositions or facts. | STRONG | Decomposition can erase condition, scope, temporal qualification, or relations among claims. |
| atomic claim extraction | Extraction of minimally scoped claims; closely related literature more often uses atomic facts or atomic fact decomposition. | MODERATE | Exact term is less standardized than atomic facts. |
| claim verification | Determine whether a claim is supported, contradicted, or insufficiently supported by evidence. | MODERATE | Usually assumes pre-isolated static claims. |
| fact verification | Evidence-based classification of factual claims. | MODERATE | Static fact checking is narrower than generated-report evaluation. |
| attribution evaluation | Whether generated statements can be traced to supporting identified sources. | STRONG | Unqualified attribution also retrieves XAI, authorship, and credit attribution. |
| source attribution | Link output information to its supporting source or sources. | MODERATE | Highly ambiguous outside grounded NLG. |
| citation correctness | Whether a cited passage really supports its associated claim. | STRONG | Correct citations can coexist with uncited unsupported claims. |
| citation precision | Proportion of supplied citations judged valid/supporting. | STRONG | Does not measure claims that should have citations but do not. |
| citation completeness | Whether all support-requiring generated content has adequate citations. | STRONG | Operational definitions vary for compound, partial, multi-source, and temporal support. |
| citation recall | Proportion of claims requiring evidence that are adequately citation-supported. | STRONG | Denominator may itself be incomplete. |
| groundedness evaluation | Whether generated content is supported by context or evidence. | MODERATE | Supplied context may itself be stale, incomplete, or wrong. |
| evidence grounding | Explicit linkage between a claim and supporting evidence location. | MODERATE | Localization alone does not prove correctness or completeness. |
| context faithfulness | Whether answer claims are inferable from supplied context, common in RAG evaluation. | MODERATE | Context faithfulness is not evidence sufficiency or current truth. |
| completeness evaluation | Generic assessment of whether required material is present. | WEAK | Not a sufficiently specific NLG term. |
| coverage evaluation | Generic measure of how much of a target inventory is covered. | WEAK | Used throughout unrelated fields with incompatible denominators. |
| omission detection | Detect information present or required in a source/reference but absent from output. | MODERATE | Strong machine-translation and non-NLG false-positive literature. |
| atomic content units | Fine semantic units for annotating salient summary content and scoring its inclusion. | STRONG | Reference-summary coverage does not by itself establish evidence attribution or temporal correctness. |
| proposition-level evaluation | Evaluation of individual semantic propositions rather than entire sentences/documents. | MODERATE | Broad term spanning semantics, discourse, logic, and argumentation. |
| selective prediction | Prediction with an abstention mechanism trading accepted coverage against error/risk. | STRONG | Foundational work is mostly classification/regression. |
| selective classification | Classification with a reject option. | MODERATE | Primarily a transfer formulation for free-form generation. |
| reject option | Decision rule allowing prediction rejection/deferment when error or cost is too high. | MODERATE | Old, broad classification terminology; partial generation is not naturally represented. |
| uncertainty calibration | Alignment between stated confidence/probability and empirical correctness frequency. | STRONG | Ranking uncertainty is not probability calibration. |
| expected calibration error | Bin-based discrepancy between confidence and empirical accuracy. | MODERATE | Binning-sensitive scalar that can hide important local failures. |
| Brier score | Proper squared-error scoring rule for probabilistic predictions. | MODERATE | Requires a clearly defined event; token likelihood is not claim correctness. |
| risk-coverage curve | Predictive risk among accepted predictions as accepted coverage varies. | STRONG | Requires an appropriate risk and coverage unit. |
| selective risk | Expected loss conditional on prediction acceptance. | STRONG | A scalar loss can conceal different unsafe error types. |
| abstention | Decline, defer, or limit a prediction because reliability is insufficient. | STRONG | Must distinguish evidence-based abstention from policy/safety refusal. |
| conformal prediction | Distribution-free finite-sample uncertainty methods under specified assumptions. | MODERATE | Classical exchangeability assumptions do not automatically survive a changing workplace stream. |
| inter-annotator agreement | Statistical consistency among annotators. | MODERATE | Agreement is not annotation validity or representative sampling. |
| human evaluation reliability | Reproducibility and validity of human evaluation protocols and judgments. | MODERATE | Extremely broad unless constrained to NLG/factuality/attribution. |
| retrieval-augmented generation evaluation | Separates retrieval and generated-answer quality, often including relevance and faithfulness. | STRONG | Typical RAG benchmarks are static query-answer tasks, not longitudinal reports. |
| decision-focused evaluation | Evaluation in terms of downstream decision consequences or utility. | WEAK | Not a stable NLG task name and attracts decision-focused learning and operations research. |

### Terms to promote

Use these actively in discovery:

- **factual precision**
- **atomic facts**
- **atomic fact decomposition**
- **claim-level factuality**
- **claim-level evidence entailment**
- **Attributable to Identified Sources (AIS)**
- **attributed generation**
- **citation quality**
- **citation coverage**
- **evidence completeness**
- **evidence sufficiency**
- **content selection evaluation**
- **salience evaluation**
- **Atomic Content Units (ACUs)**
- **selective generation**
- **risk-coverage trade-off**
- **selective risk**
- **semantic uncertainty**
- **semantic entropy**
- **confidence calibration**
- **calibration under distribution shift**
- **online calibration**
- **adaptive calibration**
- **conformal risk control**
- **cost-sensitive abstention**
- **metric meta-evaluation**
- **LLM judge validation**
- **temporal factuality**
- **knowledge freshness**
- **revision-aware evaluation**
- **current-state correctness**

### Terms to demote unless strongly qualified

- `hallucination evaluation`
- `completeness evaluation`
- `coverage evaluation`
- `source attribution`
- `groundedness`
- `decision-focused evaluation`
- `conformal prediction`
- `expected calibration error`
- `Brier score`
- `fact verification`
- `citation precision`

They remain useful concepts, but their standalone retrieval precision is poor.

## Academic task families

### TF01 — Joint multi-dimensional reliability evaluation for generated text — DIRECT

Search for evaluation schemes retaining separate measures for correctness, attribution, evidence completeness, omission/coverage, uncertainty, and abstention.

This is the most direct family for gap-1. A paper should not count as closing that gap merely because it calls itself a holistic evaluation framework; the dimensions and denominators must be inspected.

Known partial seed works:

- *Measuring Attribution in Natural Language Generation Models* — Rashkin et al., 2023.
- *Enabling Large Language Models to Generate Text with Citations* — Gao et al., 2023.
- *ARES: An Automated Evaluation Framework for Retrieval-Augmented Generation Systems* — Saad-Falcon et al., 2024.

### TF02 — Atomic claim decomposition and evidence-based factual verification — DIRECT

Break free-form output into assessable factual units and verify every unit against evidence.

This provides the machinery needed to avoid sentence-level judgments hiding mixtures of supported and unsupported information. Gap-4 additionally requires literature that handles compound claims, partial support and multiple sources.

Known seeds:

- *Asking and Answering Questions to Evaluate the Factual Consistency of Summaries* — Wang et al., 2020.
- *Evaluating the Factual Consistency of Abstractive Text Summarization* — Kryscinski et al., 2020.
- *FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long Form Text Generation* — Min et al., 2023.

### TF03 — Attributed generation and citation/evidence completeness — DIRECT

Evaluate both whether citations actually support claims and whether all claims needing evidence are sufficiently supported.

This is the primary family for the correctness-versus-completeness distinction and gap-4.

Known seeds:

- *Measuring Attribution in Natural Language Generation Models*.
- *Attributed Question Answering: Evaluation and Modeling for Attributed Large Language Models* — Bohnet et al., 2022.
- *Enabling Large Language Models to Generate Text with Citations*.

### TF04 — Content selection, summary coverage, and omission evaluation — DIRECT

Evaluate which salient semantic content should have appeared and what the output omitted.

This is the closest established family for gap-5, but reference-summary salience is not automatically equivalent to decision-relevant workplace omission.

Known seeds:

- *Evaluating Content Selection in Summarization: The Pyramid Method* — Nenkova and Passonneau, 2004.
- *Revisiting the Gold Standard: Grounding Summarization Evaluation with Robust Human Evaluation* — Liu et al., 2023, including Atomic Content Units.

### TF05 — Temporal, freshness, revision, and current-state factuality evaluation — TRANSFER

Search temporal QA, temporal fact verification, freshness, revision-aware summarization, supersession, versioned evidence and time-sensitive generation.

These methods may transfer to current-state evaluation, but a static temporal benchmark is not equivalent to reconstructing the correct state of a work item from evolving evidence.

### TF06 — Selective generation and evidence-based abstention for open-ended outputs — DIRECT

This is the preferred family for gap-3 because the target is actual free-form generation rather than finite-label selective classification.

Known seeds:

- *Self-Evaluation Improves Selective Generation in Large Language Models* — Ren et al., 2023.
- *Semantic Uncertainty: Linguistic Invariances for Uncertainty Estimation in Natural Language Generation* — Kuhn et al., 2023.

### TF07 — Probability calibration and uncertainty estimation for generative language models — DIRECT

Search for confidence values whose stated probability corresponds to empirical correctness of generated answers or claims.

Known seeds include:

- *Verification of Forecasts Expressed in Terms of Probability* — Brier, 1950.
- *On Calibration of Modern Neural Networks* — Guo et al., 2017.
- *How Can We Know When Language Models Know? On the Calibration of Language Models for Question Answering* — Jiang et al., 2021.
- *Language Models (Mostly) Know What They Know* — Kadavath et al., 2022.
- *Semantic Uncertainty* — Kuhn et al., 2023.

For gap-3, discovery must distinguish open-ended output calibration from multiple-choice calibration, token calibration and uncertainty discrimination.

### TF08 — Calibration and selective prediction under distribution shift and non-stationarity — TRANSFER

Search online calibration, adaptive calibration, temporal drift, concept drift, cross-domain calibration, distribution-shift selective prediction and shift-aware conformal methods.

This is the main family for gap-8. A one-time source-domain/target-domain transfer result is weaker than the required continuing non-stationary stream.

### TF09 — Reject-option, risk-coverage, and conformal risk control — TRANSFER

This is foundational methodology for useful-coverage versus bounded-risk decisions.

Known seeds:

- *On Optimum Recognition Error and Reject Tradeoff* — Chow, 1970.
- *On the Foundations of Noise-Free Selective Classification* — El-Yaniv and Wiener, 2010.
- *SelectiveNet: A Deep Neural Network with an Integrated Reject Option* — Geifman and El-Yaniv, 2019.
- *CAP: Conformalized Abstention Policies for Context-Adaptive Risk Management for LLMs and VLMs* — Tayebati et al., 2025.

The transfer question is whether the risk definition and assumptions survive free-form generation and continuing distribution change.

### TF10 — Human evaluation reliability, adjudication, and evaluator meta-evaluation — DIRECT

Search protocol design, annotation reliability, multi-rater adjudication, LLM-judge validation, evaluator bias, metric meta-evaluation and evaluator gaming.

This provides methodology for engineering gaps 6 and 7, but literature cannot decide the msgloom-specific review volume, sample mix or acceptance threshold.

Known seeds:

- *A Coefficient of Agreement for Nominal Scales* — Cohen, 1960.
- *Revisiting the Gold Standard: Grounding Summarization Evaluation with Robust Human Evaluation*.
- *ARES*.

### TF11 — RAG and multi-source grounded-generation evaluation — DIRECT

Search frameworks that separate:

1. retrieval relevance/sufficiency;
2. answer correctness;
3. answer/context faithfulness;
4. source attribution;
5. evidence or citation coverage.

Known seeds:

- *Enabling Large Language Models to Generate Text with Citations*.
- *ARES*.

RAG evaluation is especially useful because it exposes the failure of treating retrieved context as equivalent to complete evidence.

### TF12 — Utility-sensitive, cost-sensitive, and asymmetric-error evaluation — TRANSFER

Search cost-sensitive selective prediction and decision-theoretic abstention.

This supports inherited requirements where false acceptance, false omission and abstention have different consequences. The numerical cost function remains a msgloom engineering decision.

### TF13 — Workplace communication and longitudinal enterprise-stream evaluation — DIRECT

Run an explicit target-domain probe for email, enterprise messaging, threaded communication, revisions, work items and generated briefings.

No seed paper is asserted here.

A paper should count as strong target-domain evidence only if its actual evaluation resembles the target capability. Generic email spam detection, email classification or even static email summarization is not enough. Gap-2 remains an engineering gap unless realistic revisions, quotes, conflicts, delayed/out-of-order evidence, versions, attachments and permission constraints are represented.

## Query families

### TF01 — DIRECT: joint multi-dimensional evaluation

- `"evaluation framework" factuality attribution "citation completeness" abstention generation`
- `"evaluation framework" factuality attribution completeness uncertainty abstention "text generation"`
- `"multi-dimensional evaluation" grounded generation factuality attribution completeness calibration`
- `"holistic evaluation" generated text factuality attribution completeness abstention`
- `"claim correctness" attribution completeness omission uncertainty abstention LLM evaluation`
- `"evaluation framework" grounded generation correctness coverage calibration selective prediction`

### TF02 — DIRECT: atomic claim factuality and verification

- `"claim decomposition" factuality evaluation LLM`
- `"atomic fact" decomposition factuality long-form generation`
- `"atomic claims" evidence verification generated text`
- `"compound claim" partial support evidence evaluation generation`
- `"partial support" claim verification evidence entailment`
- `"multi-source" claim verification generated text`
- `"claim-level" factuality evidence support long-form generation`

### TF03 — DIRECT: attribution and citation completeness

- `"Attributable to Identified Sources" evaluation`
- `"attributed question answering" evaluation attribution`
- `"citation correctness" "citation recall" LLM`
- `"citation precision" "citation recall" generated answers`
- `"citation completeness" LLM generation evidence`
- `"citation coverage" grounded generation attribution`
- `"multi-source" citation evaluation long-form generation`
- `"evidence completeness" attribution generated claims`
- `"compound claims" "citation completeness" multiple sources`

### TF04 — DIRECT: report content coverage and omission

- `"summary completeness" omission evaluation content coverage`
- `"content selection" summarization evaluation Pyramid`
- `"Atomic Content Units" summarization evaluation`
- `"content coverage" summarization evaluation salient information`
- `"content recall" generated summary evaluation`
- `"omission detection" summarization generated text`
- `"information coverage" long-form generation evaluation`
- `"decision-relevant" omission summarization evaluation`
- `"summary omission" salient information evaluation`

### TF05 — TRANSFER: temporal/current-state correctness

- `"temporal factuality" evaluation language generation`
- `"temporal fact verification" changing evidence`
- `"current-state" factuality evaluation evolving evidence`
- `"revision-aware" summarization factuality`
- `"temporal consistency" summarization conflicting updates`
- `"versioned evidence" claim verification`
- `"time-sensitive" question answering factuality evaluation`
- `"knowledge freshness" generation evaluation factuality`
- `"superseded" evidence generated summary evaluation`
- `"out-of-order" evidence temporal reasoning evaluation`

### TF06 — DIRECT: free-form selective generation

- `"selective generation" language models abstention`
- `"selective generation" risk coverage LLM`
- `"free-form generation" calibration abstention`
- `"free-form" selective prediction language model`
- `"self-evaluation" "selective generation" large language models`
- `"semantic uncertainty" abstention generation`
- `"uncertainty estimation" "natural language generation" abstention`
- `"calibrated abstention" free-form language model`
- `"abstain" open-ended generation factuality`

### TF07 — DIRECT: generative probability calibration

- `"uncertainty calibration" language generation`
- `"calibration" open-ended question answering language model`
- `"calibration" free-form generation factuality`
- `"calibrated confidence" generated answers correctness`
- `"Brier score" language model generation correctness`
- `"expected calibration error" generative language model`
- `"semantic uncertainty" calibration language model`
- `"P(True)" calibration generated answer`
- `"sequence-level" confidence calibration generation`

### TF08 — TRANSFER: continuing distribution shift

- `"calibration under distribution shift" language models`
- `"uncertainty calibration" distribution shift NLP`
- `"online calibration" nonstationary language model`
- `"adaptive calibration" concept drift selective prediction`
- `"selective prediction" distribution shift risk coverage`
- `"risk coverage" distribution shift selective prediction`
- `"temporal drift" uncertainty calibration language model`
- `"non-stationary" calibration selective prediction`
- `"continual" calibration language model distribution shift`
- `"conformal" nonstationary selective prediction language model`

### TF09 — TRANSFER: bounded selective risk and conformal control

- `"risk-coverage" selective prediction language model`
- `"selective risk" language model abstention`
- `"reject option" selective prediction risk coverage`
- `"conformal risk control" language generation`
- `"conformal prediction" LLM abstention generation`
- `"selective generation" conformal risk`
- `"conformalized abstention" language model`
- `"risk controlling" language generation abstention`
- `"bounded risk" selective prediction generation`

### TF10 — DIRECT: human review and evaluator reliability

- `"human evaluation" factuality inter-annotator agreement summarization`
- `"human evaluation reliability" natural language generation`
- `"inter-annotator agreement" factuality evaluation generated text`
- `"adjudication" annotation factuality summarization`
- `"LLM as a judge" validation human judgments factuality`
- `"LLM judge" bias human agreement evaluation`
- `"automatic evaluator" gaming language model evaluation`
- `"meta-evaluation" factuality metrics human correlation`
- `"evaluator bias" LLM evaluation human`
- `"prediction-powered inference" language model evaluation human annotations`

### TF11 — DIRECT: RAG and multi-source generation evaluation

- `"RAG evaluation" faithfulness context recall attribution`
- `"retrieval augmented generation" evaluation framework factuality attribution`
- `"retrieval augmented generation" citation completeness`
- `"RAG evaluation" citation correctness completeness`
- `"RAG evaluation" abstention uncertainty`
- `"context faithfulness" "answer correctness" RAG evaluation`
- `"evidence sufficiency" RAG evaluation generation`
- `"multi-source" RAG evaluation attribution`
- `"retrieval completeness" generated answer faithfulness`

### TF12 — TRANSFER: asymmetric utility and costs

- `"cost-sensitive" selective prediction reject option`
- `"asymmetric cost" abstention selective prediction`
- `"utility-sensitive" abstention language model`
- `"decision-theoretic" abstention language model`
- `"selective prediction" asymmetric loss`
- `"risk-sensitive" language generation evaluation`
- `"decision-focused" summarization evaluation`
- `"utility" omission false positive abstention evaluation`

### TF13 — DIRECT: workplace-domain probe

- `"workplace email" summarization evaluation factuality`
- `"enterprise email" summarization evaluation`
- `"email thread" summarization factuality evaluation`
- `"email thread" information extraction actions decisions evaluation`
- `"workplace communication" NLP benchmark email`
- `"enterprise communication" NLP benchmark messaging`
- `"workplace communication" summarization actions decisions`
- `"email" longitudinal summarization revisions quoted messages`
- `"email thread" temporal state revision evaluation`
- `"workplace" generated briefing evaluation communication`

## False friends and downgrade rules

1. Downgrade any paper using one aggregate hallucination, faithfulness, or reliability score when correctness, attribution, completeness, omission, calibration and abstention are not separately measurable.
2. Factuality of generated claims is not evidence that important facts were included.
3. Citation presence or valid formatting is not citation correctness.
4. Citation correctness is not citation completeness.
5. High citation precision can be achieved while leaving many claims uncited.
6. Citation recall measured only against already retrieved passages can conceal retrieval-stage omissions.
7. Context faithfulness does not establish that the context is complete, current, authoritative, permission-valid, or the correct version.
8. Static single-claim fact verification is TRANSFER evidence for compound free-form generation unless partial support and multiple evidence sources are handled.
9. Sentence-level NLI is insufficient when one sentence contains several independently supported or unsupported propositions.
10. Reference-summary overlap, Pyramid, ACU, ROUGE, or similar coverage methods do not alone establish source attribution or current-state correctness.
11. Machine-translation omission, speech-recognition deletion, software omission faults and similar uses of “omission detection” should be rejected unless a transferable NLG evaluation mechanism is explicit.
12. Authorship attribution, plagiarism detection, feature attribution, causal attribution and citation-credit analysis are false positives for source attribution.
13. RAG retrieval relevance alone is not answer correctness, attribution correctness, or evidence completeness.
14. AUROC, AUPRC, entropy, confidence ranking and error detection are uncertainty-discrimination results, not probability calibration by themselves.
15. Token-level calibration cannot automatically be interpreted as calibrated claim or report correctness.
16. ECE alone is insufficient; outcome definition, binning and selective behavior matter.
17. Multiple-choice or fixed-label calibration is TRANSFER rather than direct evidence for gap-3 unless open-ended generation is also evaluated.
18. Selective classification is TRANSFER unless the work defines a meaningful structured/free-form generation risk.
19. Refusal-rate research must distinguish epistemic/evidence abstention from safety or policy refusal.
20. Classical conformal guarantees must not be transferred across violated exchangeability or stationarity assumptions without analysis.
21. One fixed source-to-target domain-shift experiment is weaker than the continuing non-stationarity required by gap-8.
22. Temporal QA involving dates is not sufficient if it never represents freshness, supersession, revisions or observation-time correctness.
23. Benchmark-aging studies expose temporal problems but do not close the calibration-under-change gap unless they also supply and validate a calibration/selective-prediction method.
24. LLM-as-judge results should not be treated as ground truth without independent human or equivalent independent-gold validation.
25. A system optimized against the same automatic evaluator used for acceptance needs independent evaluator/holdout checks before its score is considered reliable.
26. Inter-annotator agreement alone does not specify sampling, adjudication, confusion matrices, review volume, abstention treatment or target-specific denominators.
27. Generic enterprise-email spam, routing, search, classification or summarization studies do not close the workplace reliability gap.
28. Synthetic or public fixtures may support mechanism validation but must not be described as production-representative private workplace data.
29. A public email dataset does not close gap-2 unless the claimed evaluation actually includes relevant revisions, quoted history, conflicting updates, delayed/out-of-order arrival, versions, temporal cutoffs and permissions.
30. Multiple identifiers or corpus records for the same underlying study must not be counted as independent corroboration.

## Date policy

**Earliest publication year discovery must include: 1950.**

A modern-only window would silently remove foundational work needed to interpret the current literature.

The reason for the 1950 floor is not that free-form LLM evaluation existed in 1950. It is that this research topic explicitly depends on older methodological families:

- Glenn W. Brier's probabilistic forecast-verification work dates to **1950** and is the foundation for the Brier score.
- Jacob Cohen's nominal-scale agreement work dates to **1960** and is foundational for inter-annotator agreement methodology.
- C. K. Chow's error/reject trade-off work dates to **1970** and is foundational reject-option decision theory.
- Modern selective-classification risk/coverage theory predates current LLM research.
- The Pyramid Method for summary content-selection evaluation dates to **2004**.

Therefore discovery should **not** apply a global post-2018 or post-2020 cutoff.

The practical policy should be a **1950 global floor with tightly scoped task-family queries**. The old search range is required primarily for calibration, agreement, reject-option, risk/coverage, and content-selection foundations. Free-form generation, attributed LLMs, RAG evaluation, selective generation, temporal LLM evaluation and LLM-judge research will naturally concentrate in much more recent literature.
