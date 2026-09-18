# Joint evaluation and selective prediction for temporally evolving multi-source generation: evidence completeness for compound and partially supported claims, longitudinal omission of superseded or due work-item state, and online calibration under non-stationary streams academic terminology analysis

## Product problem

The research object is not a generic “hallucination metric.” It is a decomposed reliability system for free-form, multi-source, temporally evolving generation.

The required evaluation object has at least seven distinct denominators:

1. whether each generated claim is factually supported;
2. whether the identified source or citation is the correct support;
3. whether all support-requiring claims have sufficient evidence;
4. whether that evidence is still valid at the relevant observation time after revisions, conflicts, or supersession;
5. whether important current or due information was omitted;
6. whether uncertainty is calibrated against explicitly defined correctness events; and
7. whether accepting versus abstaining achieves an acceptable risk/coverage tradeoff.

The round-4 searches should therefore move away from broad phrases such as `hallucination evaluation`, `completeness`, and `RAG evaluation` and toward claim-level support, citation recall, evidence sufficiency, update/temporal summarization, selective prediction, online calibration, adaptive conformal inference, and metric meta-evaluation.

Three important boundaries must remain explicit. Gap-2, gap-6, and gap-7 are ENGINEERING gaps. Academic literature may inform their implementation, but further papers cannot establish that msgloom has representative private-workplace fixtures, an adequate human-review protocol, or evaluator-development separation.

## Seed keyword audit

| Seed | Academic meaning | Fit | Main risk |
| --- | --- | --- | --- |
| factual consistency evaluation | Source-conditioned consistency of generated text with evidence or an input document. | STRONG | Usually precision-like and static; stale-but-supported statements may pass. |
| factuality evaluation | Correctness or evidential support of generated claims. | STRONG | Often mixes world truth, source faithfulness, and hallucination. |
| summarization faithfulness | Whether summary statements remain supported by the source. | MODERATE | Commonly ignores omission and current-state completeness. |
| hallucination evaluation | Detection of unsupported, fabricated, or inconsistent generated information. | MODERATE | Overloaded umbrella that collapses dimensions msgloom must separate. |
| claim decomposition | Splitting complex claims into independently checkable propositions. | STRONG | Bad decomposition can erase conditions, scope, or temporal qualifiers. |
| atomic claim extraction | Extraction of minimal independently verifiable factual units. | STRONG | “Atomic” has no universal granularity. |
| claim verification | Support/refute/insufficient-evidence evaluation of claims against evidence. | STRONG | Usually assumes static claims and evidence. |
| fact verification | Retrieval plus factual claim verification against external evidence. | MODERATE | Dominated by isolated static fact-checking rather than report completeness. |
| attribution evaluation | Tests whether generated information is attributable to identified evidence. | STRONG | May ignore uncited claims. |
| source attribution | Links a statement or claim to supporting/originating sources. | MODERATE | Strong collision with authorship and quotation-attribution literature. |
| citation correctness | Whether a cited source really supports its associated claim. | STRONG | High correctness does not imply complete support. |
| citation precision | Fraction of supplied citations that are valid/supportive under the benchmark. | STRONG | Denominator is citations, not missing citations. |
| citation completeness | Whether claims needing evidence have appropriate citations. | STRONG | Compound claims can be over-credited by binary sentence scoring. |
| citation recall | Recall-like support coverage over answer claims. | STRONG | Binary support may miss partial or complementary support requirements. |
| groundedness evaluation | Whether output is supported by supplied context/evidence. | STRONG | Often an opaque or framework-specific LLM-judge score. |
| evidence grounding | Mapping claims/spans to supporting evidence locations. | STRONG | Localization alone does not prove full entailment. |
| context faithfulness | RAG-oriented consistency of answers with retrieved context. | MODERATE | Non-standard terminology and often framework-specific. |
| completeness evaluation | Fraction of required or salient information represented. | MODERATE | Extremely broad and denominator frequently implicit. |
| coverage evaluation | Coverage of expected content units, topics, claims, or requirements. | MODERATE | Heavy collision with software, retrieval, and dataset “coverage.” |
| omission detection | Detection of semantically important information missing from an output. | STRONG | Generic searches attract grammatical omission and missing-token work. |
| atomic content units | Fine semantic content units used for summary salience and coverage evaluation. | STRONG | Static ACUs do not themselves encode supersession or current-state validity. |
| proposition-level evaluation | Evaluation over semantic propositions rather than whole documents/sentences. | STRONG | Proposition boundaries and dependencies vary by framework. |
| selective prediction | Prediction plus an abstain option, evaluated by accepted-set risk and coverage. | STRONG | Foundational literature largely assumes classification. |
| selective classification | Classification with a reject option. | MODERATE | Transfer methodology, not direct free-form-generation validation. |
| reject option | Decision rule permitting no prediction when expected error/risk is high. | MODERATE | Often assumes simple labels, stationary data, and symmetric loss. |
| uncertainty calibration | Agreement between confidence and empirical correctness frequency. | STRONG | Requires defining exactly what “correct” event is being calibrated. |
| expected calibration error | Binned confidence-versus-accuracy discrepancy. | MODERATE | Binning-sensitive and insufficient as a sole reliability criterion. |
| Brier score | Proper squared-error scoring rule for probabilistic forecasts. | MODERATE | Requires a well-defined event and is not pure calibration alone. |
| risk-coverage curve | Risk among accepted predictions as acceptance coverage changes. | STRONG | Only useful with a project-valid risk definition. |
| selective risk | Expected loss conditional on the system choosing to answer. | STRONG | One scalar loss can hide different unsafe error classes. |
| abstention | Withholding output when evidence or confidence is insufficient. | STRONG | Refusal rate alone says nothing about whether refusals are well targeted. |
| conformal prediction | Prediction sets/risk control with statistical coverage guarantees under stated assumptions. | MODERATE | Classical exchangeability assumptions conflict with continuing non-stationarity. |
| inter-annotator agreement | Quantitative agreement among multiple human annotators. | MODERATE | Agreement is not validity or representative sampling. |
| human evaluation reliability | Reliability, reproducibility, disagreement, adjudication, and validity of human evaluation. | STRONG | Cannot set msgloom-specific sample size or acceptance policy by itself. |
| retrieval-augmented generation evaluation | Multi-dimensional evaluation of retrieval and generated answers. | STRONG | Many frameworks collapse dimensions or depend on unvalidated LLM judges. |
| decision-focused evaluation | Evaluation in terms of downstream utility, cost, regret, or decision effect. | MODERATE | Strong collision with decision-focused learning and optimization literature. |

The strongest promoted terminology for round 4 is therefore:

- **atomic claim evaluation / claim-level factuality** rather than generic hallucination;
- **citation recall / citation coverage / support coverage** rather than citation presence;
- **evidence sufficiency, compound-claim verification, partial support, complementary evidence, multi-source evidence aggregation** for gap-4;
- **temporal validity, evidence currentness, stale evidence, temporal provenance, version-aware evidence** for the current-state part;
- **update summarization, sequential update summarization, temporal summarization, value tracking, novelty/redundancy, timeline summarization** for gap-5;
- **selective generation, selective prediction, selective risk, risk-coverage, calibrated abstention** for the operational uncertainty side; and
- **online calibration, adaptive calibration, prequential calibration, concept drift, distribution shift, adaptive conformal inference, conformal risk control** for gap-8.

FActScore is a strong seed for atomic factuality because it decomposes long-form generations into atomic facts before assessing support, while ACUEval uses atomic content units followed by source validation. citeturn936516search5turn663158search1 ALCE is particularly important for terminology because it explicitly separates citation-oriented correctness from completeness-like recall rather than treating “has citations” as sufficient. citeturn844243search0turn844243search3

## Academic task families

### 1. Atomic claim decomposition and evidence-conditioned factuality — DIRECT

This family studies exactly the move from whole-output judgment to fine-grained claims or propositions. Relevant known seeds include **FactCC (2020)**, **QAGS (2020)**, **SummaC (2022)**, **FActScore (2023)**, and **ACUEval (2024)**. QAGS and SummaC are useful factual-consistency precedents, while FActScore and ACUEval are especially relevant to partially supported outputs because their evaluation unit is finer than an entire answer. citeturn936516search0turn936516search6turn936516search5turn663158search1

Primary gaps: gap-1 and gap-4.

### 2. Claim-to-source attribution and citation quality — DIRECT

Search for claim-level citation entailment, citation precision, citation recall, citation coverage, and source attribution. **ALCE, “Enabling Large Language Models to Generate Text with Citations” (2023)** is a high-value seed. citeturn844243search0

Primary gaps: gap-1 and gap-4.

### 3. Evidence sufficiency and completeness for compound and multi-source claims — DIRECT

This family is narrower than generic groundedness. Admission should require some combination of:

- compound or decomposed claims;
- partial support;
- complementary evidence;
- multiple sources or multi-hop evidence;
- an explicit claim denominator;
- evidence sufficiency rather than simple retrieval relevance.

This is the principal round-4 family for gap-4.

### 4. Multi-dimensional and end-to-end generation evaluation — DIRECT

Search explicitly for evaluation frameworks combining multiple reliability dimensions. For gap-1, a paper is not sufficient merely because it evaluates three metrics in the same benchmark. The relevant result must preserve meaningful independent denominators and jointly validate a scheme spanning the required dimensions.

Useful seeds include **SummEval**, **RoSE**, and **ALCE**, but their presence in the seed set must not be interpreted as establishing closure of gap-1. RoSE is useful particularly for fine-grained human-evaluation methodology and ACU-based evaluation. citeturn663158search2

### 5. Temporal validity, current-state correctness, and version-aware evidence — TRANSFER

Search temporal fact verification, time-sensitive fact verification, stale evidence, temporal validity, temporal provenance, versioned evidence, and changing knowledge.

The **TREC 2013 Temporal Summarization** work is useful transfer evidence because it explicitly studies information arriving over time, dynamic-corpus reliability, sequential updates, and changing event attributes. citeturn266799search0

It does not directly establish workplace approval/cancellation/deadline semantics.

### 6. Update, temporal, and longitudinal summarization — TRANSFER

This is the most important terminology correction for gap-5. “Omission detection” alone is too broad. Search instead for:

- update summarization;
- sequential update summarization;
- temporal summarization;
- timeline summarization;
- value tracking;
- comprehensiveness;
- novelty and redundancy;
- obsolete or superseded information.

**TAC 2008 Update Summarization** and **TREC 2013 Temporal Summarization** are established starting points. citeturn266799search3turn266799search0

Their target is evolving news/events, so they remain TRANSFER until a study evaluates functionally equivalent evolving work-item state.

### 7. Selective prediction and abstention for free-form NLP — DIRECT

Search selective generation, answer abstention, selective QA, risk-coverage in language models, and abstention in RAG.

For this project, a valid study should report both:

- performance or risk on accepted outputs; and
- retained coverage or abstention cost.

A paper showing that an LLM sometimes says “I don't know” is not selective-prediction evidence.

### 8. Selective classification and reject-option foundations — TRANSFER

The foundations go substantially further back than LLM research.

**Chow's “On Optimum Recognition Error and Reject Tradeoff” (1970)** formalizes the error/reject tradeoff. **El-Yaniv and Wiener, “On the Foundations of Noise-free Selective Classification” (2010)** explicitly frame selective classification as a risk-coverage tradeoff. **Geifman and El-Yaniv, “Selective Classification for Deep Neural Networks” (2017)** carries the formulation into deep networks. citeturn663158search0turn663158search8turn703828search14

These are methodological foundations, not evidence that a scalar classifier loss is appropriate for msgloom.

### 9. Task-level probability calibration for NLP/generation — DIRECT

Search calibration of answer correctness, claim-level confidence calibration, factuality confidence, and calibrated RAG answering.

**Guo et al., “On Calibration of Modern Neural Networks” (2017)** is an important modern calibration foundation, including temperature scaling, but its original experimental setting is classification and therefore should not itself close a generation-calibration gap. citeturn703828search0

ECE should be treated as one diagnostic, not the definition of successful calibration.

### 10. Online calibration under concept drift and distribution shift — TRANSFER

This is the key terminology family for gap-8:

- online calibration;
- adaptive calibration;
- online recalibration;
- prequential calibration;
- non-stationarity;
- concept drift;
- distribution shift;
- sequential selective prediction.

**Adaptive Conformal Inference Under Distribution Shift (2021)** is a strong seed because it explicitly studies sequential prediction when the data-generating distribution changes over time. citeturn266799search1

The open issue is transfer to free-form communication and multi-dimensional semantic loss.

### 11. Adaptive conformal inference and conformal risk control — TRANSFER

Search both adaptive conformal methods and conformal control of non-0/1 losses.

Useful seeds are **Adaptive Conformal Inference Under Distribution Shift (2021)** and **Conformal Risk Control (2024)**. The latter explicitly extends conformal methodology to control an expected monotone loss rather than only ordinary prediction-set coverage. citeturn266799search1turn703828search9

These methods are promising machinery, but they do not remove the need to define the correct semantic risk event and validate deployment assumptions.

### 12. Human evaluation reliability and evaluator meta-evaluation — DIRECT

Use this family to inform gap-6 and gap-7:

- human evaluation reliability;
- annotation disagreement;
- adjudication;
- metric meta-evaluation;
- LLM-judge validation;
- evaluator bias;
- metric overfitting;
- evaluation leakage.

RoSE explicitly addresses limitations in human summarization evaluation, including scale and inter-annotator reliability. citeturn663158search2

This literature can inform the engineering contract but cannot determine the project-specific review volume or acceptance criterion.

### 13. Cost-sensitive and utility-sensitive reliability evaluation — TRANSFER

Search asymmetric error costs, cost-sensitive selective prediction, decision-theoretic rejection, and expected-utility abstention.

This family is useful because false completion, missed obligation, false obligation, wrong attribution, and excessive abstention do not have equal downstream cost. It must not replace the owning Topics' definitions of those errors.

## Query families

### Atomic factuality — DIRECT

```text
"atomic claims" factuality evaluation generated text evidence support
"claim decomposition" factuality verification evidence generation
"atomic fact" evaluation partial support generated text
"proposition-level" factual consistency evidence evaluation generation
"compound claims" decomposition verification partial entailment
```

### Citation and attribution — DIRECT

```text
"citation correctness" "citation completeness" generation
"citation precision" "citation recall" language model generation
"citation quality" claim-level support long-form generation
"source attribution" generated claims evidence evaluation
"attribution evaluation" grounded generation citations
```

### Compound, partial, and complementary evidence completeness — DIRECT

```text
"evidence completeness" compound claims partial support multi-source
"evidence sufficiency" "compound claim" verification
"partial support" claim verification multiple evidence sources
"compositional claims" evidence verification multi-hop
"claim decomposition" "multi-source evidence" verification
"citation recall" compound claims multi-source evidence
"complementary evidence" claim verification multiple sources
"evidence sufficiency" generated claims attribution completeness
"partial entailment" compound claims evidence evaluation
"multi-hop evidence" factuality evaluation generated claims
```

### Joint multi-dimensional evaluation — DIRECT

```text
"multidimensional evaluation" generation factuality attribution completeness uncertainty
"holistic evaluation" RAG factuality citation completeness calibration
"joint evaluation framework" factuality attribution completeness abstention generation
"end-to-end evaluation" generation evidence attribution completeness uncertainty
"claim-level evaluation" citation completeness abstention calibration
"generation evaluation framework" factual correctness attribution coverage uncertainty
"RAG evaluation" citation completeness factuality abstention uncertainty
```

The admission test for gap-1 must be stricter than the search query: merely mentioning several dimensions does not close the gap.

### Temporal/current-state validity — TRANSFER

```text
"temporal fact verification" evidence currentness
"time-sensitive fact verification" evidence
"fact verification" outdated evidence temporal validity
"temporal validity" evidence claim verification
"stale evidence" factuality evaluation generation
"current information" fact verification temporal
"versioned evidence" provenance fact verification
"temporal provenance" claim verification
"knowledge updates" fact verification stale claims
"current-state" evaluation temporal summarization evidence
```

### Longitudinal omission and evolving state — TRANSFER

```text
"update summarization" completeness omission redundancy
"sequential update summarization" comprehensiveness redundancy
"temporal summarization" "value tracking" updates
"temporal summarization" omission completeness evolving events
"incremental summarization" evolving events novelty redundancy
"timeline summarization" state changes omission
"longitudinal summarization" stale information superseded facts
"update summarization" obsolete information superseded
"novelty detection" temporal summarization important updates
"action item" tracking email deadline update summarization
"work item" state tracking communication summarization
"deadline changes" longitudinal summarization communication
```

### Selective generation — DIRECT

```text
"selective prediction" natural language generation abstention
"selective generation" language model risk coverage
"selective generation" LLM abstention
"answer abstention" question answering calibration coverage
"selective question answering" risk coverage
"risk-coverage" language model generation
"abstention" RAG factuality uncertainty
"abstention" generated answers calibrated confidence
```

### Selective-prediction foundations — TRANSFER

```text
"selective classification" risk coverage
"classification with a reject option" risk coverage
"reject option" calibrated confidence classification
"selective risk" coverage prediction
"risk-coverage curve" selective prediction
"error reject tradeoff" prediction
```

### Task-level calibration — DIRECT

```text
"uncertainty calibration" natural language generation factuality
"calibrated confidence" factuality language model
"calibration" generated answer correctness language model
"calibration" question answering abstention ECE Brier
"claim-level confidence" calibration factuality
"probability calibration" LLM answer correctness
"confidence calibration" RAG answer correctness
```

### Non-stationary online calibration — TRANSFER

```text
"online calibration" concept drift probabilistic prediction
"calibration under distribution shift" sequential prediction
"adaptive calibration" concept drift prediction
"prequential calibration" nonstationary
"online recalibration" distribution shift machine learning
"calibration" non-stationary stream concept drift
"selective prediction" distribution shift calibration
"risk coverage" distribution shift selective prediction
```

### Adaptive conformal risk control — TRANSFER

```text
"adaptive conformal inference" distribution shift
"online conformal prediction" nonstationary
"conformal prediction" concept drift online
"conformal risk control" NLP
"conformal risk control" language generation
"conformal prediction" abstention language model
"adaptive conformal" selective prediction risk coverage
```

### Human evaluation and evaluator validation — DIRECT

```text
"human evaluation reliability" NLP generation
"inter-annotator agreement" factuality summarization evaluation
"meta-evaluation" summarization factuality metrics human
"LLM as a judge" human validation evaluator bias
"LLM judge" agreement human evaluation factuality
"evaluator bias" language model judge evaluation
"metric overfitting" automatic evaluation generation
"evaluation leakage" language generation metric
"adjudication" factuality annotation summarization
```

### Utility-sensitive reliability — TRANSFER

```text
"cost-sensitive" selective prediction abstention
"utility-sensitive" abstention prediction
"decision-theoretic" reject option prediction
"asymmetric error costs" selective prediction
"decision-focused evaluation" language generation
"risk-sensitive" evaluation abstention NLP
"expected utility" abstention language model
```

## False friends and downgrade rules

Discovery should downgrade or reject the following word matches:

- one aggregate hallucination, groundedness, faithfulness, or quality score when the required dimensions cannot be recovered separately;
- citation presence without evidence entailment;
- citation precision without a denominator for uncited claims;
- sentence-level support that treats a partially supported compound claim as fully supported;
- multi-source retrieval where multiple sources are retrieved but complementary evidence is never required or evaluated;
- static fact verification used as evidence for temporal correctness;
- “temporal” models that merely encode timestamps without revisions, supersession, staleness, or observation-time correctness;
- update summarization that measures ROUGE only and never novelty, redundancy, comprehensiveness, changing values, or omission;
- linguistic ellipsis/missing-word “omission detection”;
- selective classification on IID images or ordinary labels presented as direct free-form-generation evidence;
- token-probability calibration presented as answer- or claim-correctness calibration;
- ECE used alone as proof of reliable calibration;
- abstention rate without accepted-set risk and coverage;
- classical exchangeable conformal prediction presented as a guarantee for a drifting workplace stream without validating the assumption;
- concept-drift detection with no recalibration or changed selective policy;
- RAG retrieval relevance without generated-claim support evaluation;
- LLM-as-judge evaluation without validation against independent human judgments or suitable gold labels;
- inter-annotator agreement treated as sufficient evidence of human-evaluation validity;
- public or synthetic data presented as proof of production-mailbox representativeness;
- generic human-evaluation methodology presented as closure of msgloom's project-specific review protocol;
- evaluator-bias papers presented as closure of the engineering requirement for independent holdouts and evaluator separation.

The closure standards for the three remaining academic gaps should be deliberately strict:

**Gap-1:** one admitted study must actually validate a joint scheme spanning the relevant dimensions while keeping interpretable separate denominators. A benchmark that merely happens to report factuality, citations, and fluency in one table is insufficient.

**Gap-4:** the evaluated method must jointly handle compound claims, partial support, complementary multi-source evidence, and temporal/versioned evidence. Papers covering only a subset remain supporting evidence, not closure.

**Gap-5:** the evaluation must be longitudinal and omission-sensitive with changing state. Static report coverage is insufficient; evolving facts, obsolete/superseded information, or functionally equivalent due-state changes must enter the evaluation.

**Gap-8:** the study must go beyond cross-domain calibration on fixed datasets and demonstrate selective prediction or calibrated risk control under continuing non-stationarity in a sufficiently analogous generation/communication setting.

## Date policy

**Earliest publication year to include: 1950.**

This is intentionally much earlier than modern NLP. The seed list itself contains the **Brier score**, whose foundational paper, Glenn W. Brier's *Verification of Forecasts Expressed in Terms of Probability*, was published in 1950. citeturn703828search1 Reject-option/selective-prediction foundations also precede modern machine learning: Chow's *On Optimum Recognition Error and Reject Tradeoff* appeared in 1970. citeturn663158search0

A recency cutoff such as 2015 or 2020 would therefore silently remove part of the theoretical foundation needed to interpret calibration, proper scoring, rejection, selective risk, and risk-coverage.

The correct discovery policy is not to run every query indiscriminately across 1950–2026. It is to use **1950 as the global admissible floor**, while letting terminology constrain each family:

- calibration/proper-scoring foundations: reach 1950;
- reject-option/selective-prediction foundations: reach at least 1970;
- update summarization and related evolving-information evaluation: include the 2000s, including TAC 2008; citeturn266799search3
- temporal summarization: include at least the early 2010s, including TREC 2013; citeturn266799search0
- neural-network calibration/selective prediction: include the 2010s;
- citation-grounded LLM generation, atomic-factuality LLM evaluation, RAG evaluation, and LLM judges: concentrate naturally in the 2020s.

This preserves foundational work without allowing old generic classification literature to overwhelm the round-4 direct searches.
