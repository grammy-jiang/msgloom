# Evidence attribution, factuality, completeness and reliability evaluation for workplace communication systems academic terminology analysis

## Product problem

The research object is not a generic hallucination detector and should not be searched as one. The product needs a decomposed reliability contract in which a report or intermediate output can be inspected at the level of individual decision-relevant claims.

At minimum, the literature search must preserve these distinct questions:

1. Is each factual claim supported by the available source evidence?
2. Is the cited or attributed evidence actually the evidence that supports that claim?
3. Were all support-requiring claims given adequate evidence, rather than merely adding some citations?
4. Is the supporting evidence still valid at the required observation time, or has it been contradicted, revised, superseded, or rendered stale?
5. Did the output omit required Topics, actions, deadlines, conditions, conflicting evidence, or other decision-changing content?
6. Does the system's confidence correspond empirically to correctness?
7. What happens to risk as the system answers fewer or more cases?
8. When should the system explicitly return unknown, unresolved, insufficient evidence, or request review?
9. Are human or automated evaluators themselves reliable enough to support acceptance decisions?

These are separate dimensions. Factual correctness is not citation correctness; citation correctness is not citation completeness; evidence support is not current-state correctness; current-state correctness is not report completeness; calibration does not by itself define a safe decision policy.

The terminology search should therefore combine several DIRECT literatures with TRANSFER methodology from selective prediction, calibration, conformal inference, and cost-sensitive decision theory.

## Seed keyword audit

| Seed | Academic meaning | Fit | Main risk | False-positive literature |
| --- | --- | --- | --- | --- |
| factual consistency evaluation | Whether generated statements are supported by or consistent with their conditioning source, especially in summarization. | STRONG | Often lacks exact evidence localization, completeness, and temporal validity. | Generic NLG quality and lexical similarity. |
| factuality evaluation | Factual correctness against supplied evidence or external/world knowledge. | STRONG | Source-grounded correctness and world-knowledge truth are often conflated. | Trivia, factual recall, source-free QA. |
| summarization faithfulness | Whether a summary introduces claims not licensed by its source. | STRONG | Usually emphasizes unsupported additions more than omissions, provenance, or supersession. | Relevance, fluency, coherence, ROUGE. |
| hallucination evaluation | Detection or measurement of unsupported or fabricated generation. | MODERATE | Overloaded umbrella that collapses distinct failure types. | Generic hallucination surveys and self-confidence work. |
| claim decomposition | Splitting complex output into independently verifiable claims. | STRONG | Atomicity can destroy qualifiers, scope, conditions, modality, or temporal context. | Semantic parsing and sentence segmentation. |
| atomic claim extraction | Extraction of minimal factual propositions for independent verification. | STRONG | Definitions of atomicity vary; over- and under-decomposition both distort evaluation. | Open IE and generic relation/event extraction. |
| claim verification | Evidence-conditioned support/refute/insufficient-evidence judgment for claims. | STRONG | Static benchmarks often ignore revisions, supersession, and partial support. | Stance or rumor classification without evidence. |
| fact verification | Evidence retrieval plus verification of factual claims. | STRONG | Often assumes public external evidence rather than private source-bounded evidence. | Fake-news or credibility classification without claim-evidence alignment. |
| attribution evaluation | Whether generated statements can be correctly traced to supporting source material. | STRONG | Some metrics only require some source support and omit completeness/currentness. | Authorship, feature, or causal attribution. |
| source attribution | Association of content with its source or supporting evidence. | MODERATE | Extremely ambiguous terminology. | Authorship attribution, forensics, plagiarism. |
| citation correctness | Whether a cited source actually supports its attached claim. | STRONG | Correct citations can coexist with uncited unsupported claims. | Citation formatting and bibliographic correctness. |
| citation precision | Fraction of generated citations that correctly support associated claims, depending on framework definition. | STRONG | Denominators vary and the term is overloaded. | Bibliometrics and citation retrieval. |
| citation completeness | Whether claims requiring support have adequate citations. | STRONG | Citation presence may be counted without checking entailment. | Bibliographic/reference-list completeness. |
| citation recall | Often the proportion of support-requiring claims that have adequate citations. | STRONG | Can instead mean recall of bibliography entries or recommended citations. | Scholarly citation retrieval. |
| groundedness evaluation | Whether generated content is supported by a specified grounding source. | STRONG | Definitions are inconsistent and often whole-answer rather than claim-level. | Symbol grounding and conversational grounding. |
| evidence grounding | Linking claims or outputs to evidence that licenses them. | STRONG | May evaluate retrieval/localization without semantic support. | Visual/entity grounding and retrieval-only work. |
| context faithfulness | In RAG evaluation, whether answer claims are inferable from retrieved context. | MODERATE | Treating retrieved context as authoritative hides stale or contradictory evidence. | Framework-specific unvalidated metrics. |
| completeness evaluation | Whether required information is fully represented. | WEAK | Far too broad without a semantic denominator. | Database, requirements, test, and KB completeness. |
| coverage evaluation | How much of a defined target information set is represented. | WEAK | Highly overloaded and often reduced to lexical overlap. | Code, network, geographic, corpus coverage. |
| omission detection | Finding information that should have appeared but is absent. | MODERATE | Requires an explicit definition of required content. | Ellipsis, omitted-word, missing-data, software omission work. |
| atomic content units | Fine-grained semantic units used to measure summary content inclusion. | STRONG | Reference-derived content units do not establish source truth or provenance. | Generic atomic propositions outside evaluation. |
| proposition-level evaluation | Evaluation at proposition rather than whole-sentence/document level. | MODERATE | Not a standardized task name. | Logic, semantic parsing, proposition extraction. |
| selective prediction | Prediction with an explicit option to abstain. | STRONG | Confidence must correspond to the failure that matters and useful coverage must remain. | Active learning and selective sampling. |
| selective classification | Classification with rejection, typically evaluated by risk versus coverage. | STRONG | Standard class error does not encode structured or asymmetric workplace failures. | Feature selection and selective inference. |
| reject option | Decision-theoretic withholding of a prediction when expected error is too high. | STRONG | Classical assumptions may not map to structured language tasks or asymmetric costs. | Generic rejection/filtering terminology. |
| uncertainty calibration | Agreement between stated confidence/probability and empirical correctness. | STRONG | Global calibration can hide subgroup, task, temporal, or shift failures. | Uncertainty scores with no calibration study. |
| expected calibration error | Binned discrepancy between confidence and observed accuracy. | MODERATE | Sensitive to binning and aggregation; can hide important local failures. | Papers reporting ECE as an isolated auxiliary metric. |
| Brier score | Proper squared-error scoring rule for probabilistic predictions. | MODERATE | Does not specify evidence completeness, abstention, or acceptable decision risk. | Domain-specific forecasting with no transferable reliability method. |
| risk-coverage curve | Risk among accepted predictions as accepted-example coverage changes. | STRONG | Safety depends on the definition of risk. | Unrelated uses of coverage curves. |
| selective risk | Expected error or loss conditional on making rather than rejecting a prediction. | STRONG | A scalar risk can hide distinct high-cost errors. | Generic financial/operational risk literature. |
| abstention | Withholding an answer or field when support/confidence is insufficient. | STRONG | Error can be trivially lowered by rejecting everything. | Political abstention and generic missing-response work. |
| conformal prediction | Distribution-free prediction sets/intervals with coverage guarantees under stated assumptions. | MODERATE | Statistical coverage is not semantic correctness; non-stationary streams can violate assumptions. | Generic regression/classification applications unrelated to language evidence. |
| inter-annotator agreement | Measurement of consistency among annotators. | STRONG | Agreement is not construct validity and disagreements can reveal task ambiguity. | Unrelated annotation domains without transferable methodology. |
| human evaluation reliability | Reliability, reproducibility, validity, protocol quality, and annotator variation in human judgments. | STRONG | Mean ratings alone are not reliable acceptance evidence. | User-preference surveys without reliability analysis. |
| retrieval-augmented generation evaluation | Evaluation of retrieval and generated-answer dimensions such as relevance, correctness and faithfulness. | STRONG | Many studies omit exact attribution, completeness, temporal validity, or abstention. | RAG papers reporting only QA accuracy, retrieval recall, or latency. |
| decision-focused evaluation | Evaluation using downstream utility, consequences, or decision costs rather than only predictive accuracy. | MODERATE | Strong lexical collision with decision-focused learning and optimization. | Predict-then-optimize and operations-research literature without reliability evaluation. |

The most important promoted vocabulary is: **claim-level factuality**, **factual precision**, **claim-evidence alignment**, **citation entailment**, **citation coverage**, **evidence attribution**, **attributed question answering**, **evidence sufficiency**, **answerability**, **insufficient-evidence detection**, **claim recall/content-unit coverage**, **selective question answering**, **calibration under distribution shift**, **cost-sensitive selective prediction**, **temporal fact verification**, **evidence freshness**, **knowledge staleness**, and **LLM-as-judge validation**.

Terms that should be demoted unless constrained by other vocabulary are generic **hallucination evaluation**, **source attribution**, **completeness evaluation**, **coverage evaluation**, **omission detection**, **proposition-level evaluation**, standalone **ECE**, standalone **Brier score**, unconstrained **conformal prediction**, and unconstrained **decision-focused evaluation**.

## Academic task families

### F1 — Source-grounded factual consistency and summarization faithfulness — DIRECT

This literature directly asks whether generated summaries or statements are supported by their source. It is the main source for factual consistency definitions, error taxonomies, entailment-based approaches, QA-based approaches, and metric validation.

Known starting papers include:

- Maynez et al. (2020), *On Faithfulness and Factuality in Abstractive Summarization*.
- Kryściński et al. (2020), *Evaluating the Factual Consistency of Abstractive Text Summarization*.
- Wang et al. (2020), *Asking and Answering Questions to Evaluate the Factual Consistency of Summaries*.
- Durmus et al. (2020), *FEQA: A Question Answering Evaluation Framework for Faithfulness Assessment in Abstractive Summarization*.
- Pagnoni et al. (2021), *Understanding Factuality in Abstractive Summarization with FRANK: A Benchmark for Factuality Metrics*.

Its limitation is that faithful-but-incomplete output can still be unacceptable for msgloom.

### F2 — Atomic claim decomposition and evidence-conditioned verification — DIRECT

The required evaluation unit is often smaller than a sentence. This family covers decomposition into checkable claims and evidence-conditioned support/refute/insufficient-evidence decisions.

Known starting papers include:

- Thorne et al. (2018), *FEVER: a Large-scale Dataset for Fact Extraction and VERification*.
- Min et al. (2023), *FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long Form Text Generation*.

The important admission criterion is evidence-conditioned claim evaluation. Generic Open IE or proposition extraction is not enough.

### F3 — Attribution, citation correctness, and citation completeness — DIRECT

This family asks three separate questions: whether attribution exists, whether the attributed source actually supports the statement, and whether every support-requiring claim received adequate attribution.

Known starting work includes Gao et al. (2023), *Enabling Large Language Models to Generate Text with Citations*.

Discovery should search for **citation entailment**, **citation precision**, **citation recall**, **citation coverage**, **attributed question answering**, and **claim-level attribution**, not merely "citations".

### F4 — Content-unit coverage, completeness, and omission — DIRECT

This family provides denominators for what the output should contain. Semantic content units are more relevant than lexical recall because msgloom must preserve qualifiers, actions, conditions, deadlines, uncertainty, and competing evidence.

A foundational starting point is Nenkova and Passonneau (2004), *Evaluating Content Selection in Summarization: The Pyramid Method*.

Atomic Content Units and related proposition-level content representations should be searched here. The key question is not "does the output resemble a reference?" but "which required semantic units were retained, lost, partially represented, or distorted?"

### F5 — RAG evaluation: retrieval, answer correctness, context faithfulness, and evidence sufficiency — DIRECT

RAG evaluation directly provides decomposed retrieval/generation frameworks, but msgloom must avoid the common shortcut of treating retrieved context as automatically correct or sufficient.

Known starting papers include:

- Es et al. (2024), *RAGAS: Automated Evaluation of Retrieval Augmented Generation*.
- Saad-Falcon et al. (2024), *ARES: An Automated Evaluation Framework for Retrieval-Augmented Generation Systems*.

Relevant dimensions include retrieval relevance, evidence sufficiency, answer correctness, context faithfulness, and attribution. Retrieval success and supported generation are separate variables.

### F6 — Answerability, insufficient evidence, and language-task abstention — DIRECT

"No evidence found" must not become a fabricated answer or evidence of absence. This family covers explicit unanswerability and withholding answers when available evidence is insufficient.

Known starting papers include:

- Rajpurkar et al. (2018), *Know What You Don't Know: Unanswerable Questions for SQuAD*.
- Kamath et al. (2020), *Selective Question Answering under Domain Shift*.

Search should include **answerability**, **insufficient evidence**, **no-answer**, **unknown**, **selective question answering**, and **abstention**.

### F7 — Selective prediction, reject options, and risk-coverage analysis — TRANSFER

This is the formal decision layer for abstention. It provides selective risk, coverage, rejection policies, and risk-coverage curves.

Foundational or well-known work includes:

- Chow (1970), *On Optimum Recognition Error and Reject Tradeoff*.
- Geifman and El-Yaniv (2017), *Selective Classification for Deep Neural Networks*.
- Geifman and El-Yaniv (2019), *SelectiveNet: A Deep Neural Network with an Integrated Reject Option*.

It is TRANSFER because msgloom's losses are not ordinary classification error. False broad links, false obligations, missed obligations, unsupported claims, false completion, and omitted evidence require separate denominators and possibly different costs.

### F8 — Calibration and reliability under distribution shift — TRANSFER

Calibration asks whether a numerical confidence means what the system claims it means. This family supplies proper scoring, reliability diagrams, calibration metrics, post-hoc calibration, and distribution-shift analysis.

Important foundations and starting points include:

- Brier (1950), *Verification of Forecasts Expressed in Terms of Probability*.
- Guo et al. (2017), *On Calibration of Modern Neural Networks*.
- Ovadia et al. (2019), *Can You Trust Your Model's Uncertainty? Evaluating Predictive Uncertainty Under Dataset Shift*.
- Desai and Durrett (2020), *Calibration of Pre-trained Transformers*.

ECE should be treated as one diagnostic, not the definition of calibration quality. Non-stationarity is particularly important because workplace communication changes over time.

### F9 — Conformal and coverage-guaranteed uncertainty — TRANSFER

Conformal prediction supplies statistically controlled coverage under explicit assumptions and may be useful for prediction sets or abstention-like mechanisms.

A foundational source is Vovk, Gammerman, and Shafer (2005), *Algorithmic Learning in a Random World*.

This literature must not be imported mechanically. Exchangeability and other assumptions need scrutiny under evolving workplace streams, and statistical coverage does not prove evidence attribution or semantic correctness.

### F10 — Human evaluation reliability, agreement, and adjudication — DIRECT

User-reviewed examples and manually established gold data require their own evaluation discipline. Agreement must be measured, disagreements characterized, ambiguous cases adjudicated, and representative sampling documented.

Useful foundations include:

- Cohen (1960), *A Coefficient of Agreement for Nominal Scales*.
- Artstein and Poesio (2008), *Inter-Coder Agreement for Computational Linguistics*.
- van der Lee et al. (2019), *Best Practices for the Human Evaluation of Automatically Generated Text*.
- Howcroft et al. (2020), *Twenty Years of Confusion in Human Evaluation: NLG Needs Evaluation Sheets and Standardised Definitions*.

LLM-as-judge studies belong here only when validation against suitable human or independent gold judgments is part of the evidence.

### F11 — Temporal validity, stale evidence, supersession, and current-state evaluation — TRANSFER

This family is required because ordinary evidence support is insufficient. A source may accurately support an obsolete state. Search must therefore reach temporal fact verification, time-sensitive QA, evidence freshness, knowledge staleness, temporal entailment, and evaluation at observation cutoffs.

The target capability is stricter than identifying dates: the evaluator must distinguish valid-at-the-time evidence from evidence that has been superseded, contradicted, revised, or received out of order.

This is marked TRANSFER because the exact combination required by msgloom is not expected to exist as a standard workplace-communication benchmark.

### F12 — Cost-sensitive and decision-utility evaluation — TRANSFER

The inherited engineering gaps make symmetric accuracy insufficient. A false broad approval link can have a different cost from a missed link; a false obligation differs from an unresolved owner; false completion differs from delayed closure.

Search should therefore include **cost-sensitive selective prediction**, **asymmetric loss**, **reject-option cost**, **utility-sensitive classification**, and **expected utility**.

Chow's reject-option formulation is an important historical anchor, but msgloom-specific costs must be defined by the owning Topics rather than imported from generic classification benchmarks.

## Query families

### F1 — DIRECT: source-grounded factual consistency

- `"factual consistency" summarization evaluation source`
- `"factuality" abstractive summarization evaluation source faithfulness`
- `"summary faithfulness" factual consistency evaluation`
- `"faithfulness assessment" summarization factuality`
- `"factual consistency metric" summarization entailment`
- `"hallucination" summarization source faithfulness evaluation`

### F2 — DIRECT: atomic claims and verification

- `"claim decomposition" factuality verification`
- `"atomic claim" factuality evaluation verification`
- `"atomic claims" evidence verification language model`
- `"claim verification" evidence support refute insufficient evidence`
- `"fact verification" claim evidence support refute`
- `"factual precision" "atomic" long form generation`
- `"claim-level" factuality evidence evaluation`

### F3 — DIRECT: attribution and citations

- `"citation correctness" "citation completeness" language model`
- `"citation precision" "citation recall" generated answer`
- `"citation entailment" language model evaluation`
- `"attribution evaluation" grounded generation evidence`
- `"source attribution" generated claims evidence support`
- `"claim attribution" evidence span generation`
- `"attributed question answering" evaluation`
- `"citation coverage" generated answer evidence`
- `"evidence attribution" claim-level evaluation`

### F4 — DIRECT: completeness and omission

- `"Atomic Content Units" summarization evaluation`
- `"content units" summarization coverage evaluation`
- `"Pyramid Method" summarization content selection evaluation`
- `"summary completeness" content coverage omission`
- `"evidence completeness" generated summary evaluation`
- `"omission detection" summarization important information`
- `"content coverage" proposition-level summarization evaluation`
- `"claim recall" factuality evaluation generation`
- `"information coverage" summary evaluation semantic units`

### F5 — DIRECT: RAG evaluation

- `"retrieval augmented generation" evaluation faithfulness correctness`
- `"RAG evaluation" groundedness context faithfulness`
- `"RAG evaluation" evidence completeness attribution`
- `"retrieval augmented generation" citation correctness`
- `"answer correctness" "context faithfulness" RAG`
- `"evidence sufficiency" retrieval augmented generation`
- `"retrieval relevance" "faithfulness" RAG evaluation`
- `"groundedness" RAG evaluation claim evidence`

### F6 — DIRECT: answerability and abstention

- `"selective question answering" abstention`
- `"unanswerable questions" question answering no answer`
- `"answerability" evidence sufficiency question answering`
- `"insufficient evidence" question answering abstention`
- `"no answer" grounded question answering evaluation`
- `"abstention" language model question answering evidence`
- `"unknown" answerability grounded generation`
- `"defer" language model factuality evidence`

### F7 — TRANSFER: selective prediction

- `"selective prediction" NLP abstention`
- `"selective classification" reject option risk coverage`
- `"risk-coverage" language model`
- `"risk coverage curve" NLP`
- `"selective risk" abstention machine learning`
- `"reject option" neural network classification`
- `"selective prediction" question answering`
- `"coverage risk" abstention natural language processing`

### F8 — TRANSFER: calibration and distribution shift

- `"uncertainty calibration" NLP`
- `"calibration" language models factuality`
- `"calibration" question answering confidence`
- `"expected calibration error" NLP`
- `"Brier score" language model confidence`
- `"calibration" "distribution shift" NLP`
- `"predictive uncertainty" "dataset shift" calibration`
- `"calibration under domain shift" language model`
- `"temporal distribution shift" calibration NLP`

### F9 — TRANSFER: conformal methods

- `"conformal prediction" NLP`
- `"conformal prediction" language models`
- `"conformal" question answering abstention`
- `"conformal prediction" distribution shift language`
- `"conformal" selective prediction NLP`
- `"conformal risk control" language model`

### F10 — DIRECT: human evaluation reliability

- `"human evaluation reliability" natural language generation`
- `"inter-annotator agreement" factuality evaluation`
- `"inter-annotator agreement" summarization evaluation`
- `"human evaluation" NLG reliability adjudication`
- `"annotation agreement" claim verification`
- `"human evaluation" groundedness attribution`
- `"LLM as judge" human agreement factuality`
- `"LLM judge" validation human evaluation`

### F11 — TRANSFER: temporal/current-state correctness

- `"temporal fact verification"`
- `"time-sensitive" fact verification`
- `"temporal factuality" evaluation language model`
- `"stale evidence" question answering`
- `"evidence freshness" question answering`
- `"knowledge staleness" factuality evaluation`
- `"temporal entailment" claim verification`
- `"supersession" information extraction evaluation`
- `"current state" temporal question answering evidence`
- `"out-of-order" event stream state evaluation`

### F12 — TRANSFER: asymmetric cost and decision utility

- `"cost-sensitive" selective classification abstention`
- `"asymmetric cost" reject option classification`
- `"utility-sensitive" classification abstention`
- `"decision-focused evaluation" language generation`
- `"decision utility" model evaluation abstention`
- `"expected utility" selective prediction`
- `"asymmetric loss" selective prediction`
- `"cost-sensitive" NLP evaluation false positive false negative`

## False friends and downgrade rules

Discovery should apply the following downgrade or exclusion rules:

- Do not admit fluency, coherence, relevance, style, ROUGE, BLEU, embedding similarity, or reference similarity as evidence of factual correctness.
- Downgrade source-free factuality when the method never verifies a claim against an identified evidence source. It can be retained as TRANSFER when the mechanism itself is useful.
- Citation presence is not citation correctness.
- Citation correctness is not citation completeness.
- Exclude citation formatting, bibliography validation, citation recommendation, bibliometrics, and citation-network prediction unless claim support is actually evaluated.
- "Source attribution" that means authorship, source-device identification, plagiarism, causal attribution, or feature attribution is not the target task.
- Groundedness without an explicit grounding source is insufficiently specified.
- Visual grounding should be included only as TRANSFER when exact evidence localization is relevant; phrase-region matching alone is not Topic 10 evidence.
- Retrieval success is not evidence support. RAG papers that report only retrieval recall, answer accuracy, latency, or model quality should be downgraded.
- Faithfulness to retrieved context is not enough when the retrieved context itself may be stale, contradictory, or superseded.
- Raw softmax scores, entropy, verbal confidence, or model self-confidence are not calibration evidence.
- ECE alone is not an adequate reliability evaluation. Binning and aggregation can hide decision-relevant failures.
- Calibration alone is not a safe-decision policy; coverage and risk under abstention must also be measured.
- Abstention that attains high accuracy by rejecting nearly everything is not operationally useful.
- Selective risk must not collapse materially different errors into one scalar when those errors have different product costs.
- Conformal coverage is not a guarantee of semantic correctness, evidence support, or source attribution.
- Human mean ratings without clear instructions, representative sampling, agreement assessment, and adjudication should not be treated as reliable gold.
- LLM-as-judge agreement is not ground truth unless the evaluator has been validated against suitable independent human or gold judgments.
- "Completeness" or "coverage" is not meaningful without an explicit denominator defining required content.
- Lexical coverage is not enough for conditions, deadlines, modality, negation, identity, response scope, temporal validity, or decision state.
- "No evidence retrieved" must not be interpreted as "the proposition is false" or "the event did not occur."
- Public fact-checking work that permits unrestricted web evidence should not be presented as directly representative of permission-bounded workplace evidence.
- Temporal QA that only extracts or reasons over dates should be downgraded for the current-state requirement unless it also addresses observation time, freshness, revision, contradiction, or supersession.
- Decision-focused learning and predict-then-optimize papers should be excluded unless they contribute reusable methods for asymmetric costs, utility-aware evaluation, selective prediction, or abstention.
- One aggregate hallucination, faithfulness, groundedness, or reliability score must not replace separate measurement of factual correctness, attribution correctness, attribution completeness, current-state correctness, semantic coverage, calibration, and abstention.
- Multiple records or identifiers for the same underlying study must be deduplicated before evidence counting. Duplicate bibliographic records are not independent corroboration.

## Date policy

**Earliest publication year discovery must include: 1950.**

The reason is methodological rather than historical completeness for its own sake. Topic 10 explicitly owns calibration and probabilistic reliability, and Brier's *Verification of Forecasts Expressed in Terms of Probability* dates to 1950. Human-agreement foundations follow in the 1960s, formal reject-option work includes Chow's 1970 paper, semantic content-selection evaluation has important work in the 2000s, and the modern factual-consistency, RAG, citation-grounding, and LLM-evaluation literature is concentrated mainly in the 2010s and 2020s.

A recent-only window would therefore silently remove the foundations needed to interpret proper scoring, calibration, agreement, rejection, and risk-coverage methods.

This does not mean every query should search indiscriminately from 1950. The appropriate policy is family-sensitive:

- calibration/proper-scoring searches: admit work from 1950;
- annotation/agreement searches: admit foundational work from the 1960s onward;
- reject-option/selective-decision searches: admit work from at least 1970;
- semantic content-selection/completeness searches: include at least the early 2000s;
- factual consistency, RAG, citation-grounded generation, LLM judges, and modern claim decomposition: emphasize the 2010s and 2020s while allowing older directly relevant work.

The discovery system should therefore use **1950 as the global earliest permissible year**, while ranking by task-family relevance rather than flooding modern NLP families with unrelated historical literature.
