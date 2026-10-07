# Integrated evaluation of evidence completeness and omission for temporally evolving multi-source free-form generation, with calibrated selective prediction under non-stationary distribution shift academic terminology analysis

## Product problem

The research object is not a generic hallucination metric. It is a **decomposed reliability evaluation contract** for free-form outputs built from evolving evidence. The contract needs separately observable denominators for:

1. whether each generated claim is factually supported;
2. whether the cited or identified source actually supports that claim;
3. whether all evidence needed for the full claim was supplied;
4. whether the claim is still the correct current state after revision, contradiction or supersession;
5. whether decision-relevant information was omitted;
6. whether confidence is empirically calibrated to a named correctness event;
7. how risk changes as the system abstains and coverage falls; and
8. whether automatic evaluation itself is trustworthy against independent human judgments.

The central terminology problem is that several neighboring literatures use apparently compatible words for materially different tasks. In particular, **faithfulness does not imply completeness; citation correctness does not imply citation completeness; retrieval recall does not imply evidence sufficiency; calibration does not imply a safe operating policy; and conformal coverage does not automatically imply semantic reliability of a free-form report**.

The most important round-3 vocabulary shift is therefore from generic terms such as *hallucination*, *groundedness* and *coverage* toward **claim-level factuality, attribution, citation recall/completeness, evidence sufficiency, partial support, complementary evidence, content-unit omission, update summarization, selective risk, risk-coverage, online calibration and adaptive conformal inference**.

## Seed keyword audit

| Seed | Academic meaning | Fit | Main risk |
| --- | --- | --- | --- |
| factual consistency evaluation | Whether generated statements are consistent with or supported by an input source. Established particularly in abstractive summarization. | STRONG | Usually evaluates support errors but not omitted information, temporal validity or calibrated abstention. |
| factuality evaluation | Whether generated factual statements are correct against evidence or external knowledge. | STRONG | External-world truth may be conflated with source faithfulness; completeness is normally outside the metric. |
| summarization faithfulness | Whether a summary preserves source meaning without unsupported additions. | STRONG | A completely faithful summary can still omit critical information. |
| hallucination evaluation | Detection or measurement of unsupported or false generated information. | MODERATE | Definitions vary widely and frequently collapse several failure modes into one label. |
| claim decomposition | Splitting output into independently assessable propositions. | STRONG | Decomposition can lose qualifiers, conjunctions and temporal scope. |
| atomic claim extraction | Creating minimal independently verifiable factual statements. | STRONG | Atomicity definitions change the scoring denominator and can destroy necessary cross-claim dependencies. |
| claim verification | Support/refute/insufficient-evidence assessment for a claim against evidence. | STRONG | Most work assumes a fixed claim and static evidence rather than generated-report completeness. |
| fact verification | Evidence-based verification of factual statements. | MODERATE | Search results are dominated by misinformation and external-world fact checking. |
| attribution evaluation | Whether generated statements are attributable to identified evidence sources. | STRONG | Correct attribution does not establish that all necessary evidence was supplied. |
| source attribution | Identification of the source supporting a generated statement. | STRONG | Large false-positive literatures exist for authorship, plagiarism and speaker attribution. |
| citation correctness | Whether a cited source actually supports its associated claim. | STRONG | Does not penalize claims that should have citations but have none. |
| citation precision | Whether provided citations are relevant, necessary and supportive. | STRONG | High precision can coexist with low completeness. |
| citation completeness | Whether citation-worthy claims have sufficient citations. | STRONG | Existing formulations may count one partly supportive source as complete for a compound claim. |
| citation recall | Fraction of evidence-requiring claims supplied with appropriate evidence. | STRONG | The result depends critically on the denominator of citation-worthy propositions. |
| groundedness evaluation | Whether generated output is supported by context/evidence. | MODERATE | The term is not standardized and is often an opaque aggregate. |
| evidence grounding | Linking an output to specific supporting source evidence. | STRONG | Correct localization does not guarantee semantic sufficiency or currentness. |
| context faithfulness | In RAG evaluation, whether answer claims follow from retrieved context. | MODERATE | Usually tests support, not whether context retrieval or citations are complete. |
| completeness evaluation | Whether all required information appears in an output. | MODERATE | Extremely broad term with many unrelated literatures and often no explicit denominator. |
| coverage evaluation | Degree to which required information or instances are represented. | WEAK | “Coverage” has incompatible meanings across summarization, IR, testing and selective prediction. |
| omission detection | Identification of relevant information missing from an output. | STRONG | Meaningful omission evaluation requires an independently defined set of required content. |
| atomic content units | Fine-grained semantic content units for salience and summary-content evaluation. | STRONG | ACUs do not by themselves determine source support, temporal validity or abstention. |
| proposition-level evaluation | Evaluation at proposition rather than whole-sentence/document granularity. | STRONG | A proposition can still be compound or context-dependent. |
| selective prediction | Prediction with abstention, evaluated through a risk/coverage trade-off. | STRONG | Formal literature is mostly classification or structured prediction. |
| selective classification | Classification with a reject option and conditional error measured on accepted predictions. | MODERATE | Useful methodological transfer but not direct validation for free-form outputs. |
| reject option | Decision-theoretic withholding of predictions when expected error/cost is excessive. | MODERATE | Foundational work is pattern recognition rather than NLG. |
| uncertainty calibration | Agreement between predictive confidence and empirical probability of correctness. | STRONG | “Correctness” must be dimension-specific for a multi-claim report. |
| expected calibration error | Binned difference between confidence and empirical accuracy. | MODERATE | ECE can hide local/subgroup miscalibration and depends on binning choices. |
| Brier score | Proper squared-error score for probabilistic predictions. | MODERATE | Requires a clearly defined outcome and should not collapse several error dimensions into one event. |
| risk-coverage curve | Conditional prediction risk plotted against the fraction of examples answered. | STRONG | Meaning depends on a defensible risk function. |
| selective risk | Expected loss conditional on issuing rather than rejecting a prediction. | STRONG | One scalar loss can hide different safety-critical failure types. |
| abstention | Explicit deferral or withholding of a prediction. | STRONG | Refusal behavior is not automatically calibrated abstention; coverage must remain visible. |
| conformal prediction | Distribution-free prediction sets/intervals with stated coverage guarantees under specified assumptions. | MODERATE | Standard guarantees do not automatically survive non-stationarity or transfer to semantic free-form generation. |
| inter-annotator agreement | Consistency among humans applying an annotation protocol. | MODERATE | Agreement is not correctness and does not establish representativeness. |
| human evaluation reliability | Reproducibility, validity and annotator variation in human generation evaluation. | STRONG | Preference/fluency evaluation is insufficient for evidence-level reliability. |
| retrieval-augmented generation evaluation | Evaluation of retrieval relevance/coverage and generated-answer correctness/faithfulness. | STRONG | Many frameworks conflate retrieval quality, answer support and evidence sufficiency or rely on unvalidated judges. |
| decision-focused evaluation | Evaluation or optimization according to downstream decision utility or asymmetric cost. | WEAK | Searches often return decision-focused learning/predict-then-optimize rather than evaluation methodology. |

Known anchor literature confirms the distinction between these task families. FactCC explicitly evaluates factual consistency of abstractive summaries; TRUE meta-evaluates factual-consistency methods across datasets. citeturn207856search3turn953460search8 FActScore decomposes long-form generation into atomic facts before checking source support, while the RoSE work uses Atomic Content Units for fine-grained summarization evaluation. citeturn953460search0turn207856search1

For attribution, AIS defines evaluation of whether generated statements are attributable to identified sources, while ALCE evaluates citation-grounded generation and explicitly separates citation quality from other dimensions. citeturn952659search8turn952659search0 These are especially important for this project because they prevent “has a citation” from becoming a surrogate for “is correct and completely supported.”

## Academic task families

### F1 — Claim-level factual consistency and faithfulness — DIRECT

This is the core correctness family: verify generated claims against source evidence. Appropriate anchors include **Evaluating the Factual Consistency of Abstractive Text Summarization (FactCC)**, **QAGS**, **SummaC**, and **TRUE**. FactCC, for example, combines consistency prediction with extraction of supporting or conflicting spans, while TRUE explicitly meta-evaluates factual-consistency methods at example level. citeturn207856search3turn207856search12turn953460search4turn953460search8

Its role is narrow by design: it establishes a factual-support denominator but must not be used as the report-completeness denominator.

### F2 — Atomic claim and content-unit decomposition — DIRECT

This family supplies the units on which the other metrics can operate. Relevant terminology includes **atomic facts**, **atomic claims**, **Atomic Content Units (ACUs)**, **Summary Content Units**, **Pyramid Method**, and **proposition-level evaluation**.

The Pyramid Method is established summarization terminology dating to 2004 for evaluation of content selection. citeturn780385search0 RoSE's ACU protocol and FActScore's atomic-fact representation are modern direct anchors. citeturn207856search1turn953460search0

For msgloom, decomposition should preserve qualifiers, conditions, ownership, dates and temporal scope rather than mechanically minimizing sentence length.

### F3 — Attribution and citation correctness — DIRECT

Search for **Attributable to Identified Sources (AIS)**, **attribution evaluation**, **citation correctness**, **citation precision**, and related claim-to-source support terminology.

AIS was explicitly proposed as a framework for checking whether NLG output is supported by identified underlying sources. citeturn952659search2 ALCE is a direct citation-grounded-generation benchmark and evaluates citation quality separately from general answer quality. citeturn952659search0

### F4 — Evidence completeness, citation recall and multi-source sufficiency — DIRECT

This is the highest-priority terminology family for **gap-4**.

The search must combine:

- citation completeness / citation recall;
- evidence sufficiency;
- compound claims;
- partial or partially supportive evidence;
- complementary evidence;
- multiple evidence passages or sources;
- multi-hop evidence;
- claim decomposition; and
- temporal/versioned evidence.

ALCE is a useful anchor because it treats incomplete citation support as a distinct problem, but the round-3 question is narrower: whether the literature contains a validated method that handles **compound claims whose full semantics require multiple pieces of evidence**, including partial and temporally versioned support. citeturn952659search0

Do not let a paper close gap-4 merely because it reports citation recall.

### F5 — Content coverage, salience and omission evaluation — DIRECT

This family supplies the missing-information denominator. It includes:

- content selection evaluation;
- Summary Content Units / Pyramid evaluation;
- Atomic Content Units;
- salience coverage;
- summary completeness; and
- semantic omission.

The Pyramid Method is a foundational direct task family for evaluating which information a summary contains, rather than only whether what it says is true. citeturn780385search0 RoSE further develops fine-grained human content evaluation through ACUs. citeturn207856search1

### F6 — Update, temporal and longitudinal summarization evaluation — DIRECT

This is the strongest existing academic bridge to **gap-5**.

The most important promoted terms are **update summarization**, **temporal summarization**, **timeline summarization**, **incremental summarization**, **novelty**, and **evolving information**.

The TAC 2008 Update Summarization task explicitly assumed that a reader had already seen earlier material and asked systems to summarize later batches with the purpose of communicating what was new or different. It also evaluated content using Pyramid-style assessment. citeturn762792search0 TREC later ran a Temporal Summarization track. citeturn762792search5

This is much closer to repeated briefing than static summarization, but it still does **not** automatically establish evaluation of due work, superseded obligations, current-state reconstruction or workplace-specific omissions.

### F7 — Integrated multidimensional evaluation and meta-evaluation — DIRECT

This is the principal family for **gap-1**.

Queries should explicitly co-locate:

- factuality;
- attribution;
- citation/evidence completeness;
- omission or content coverage;
- temporal/current-state correctness;
- uncertainty calibration;
- abstention; and
- separate dimensions or denominators.

TRUE is relevant as an example of rigorous metric meta-evaluation, AIS as an attribution framework, and ALCE as a citation-grounded generation benchmark, but none should be assumed to provide the complete target contract merely because it is called a framework or benchmark. citeturn953460search8turn952659search8turn952659search0

A round-3 candidate closes gap-1 only if the dimensions are **jointly evaluated while remaining separately reportable**.

### F8 — Selective prediction and abstention in NLP — TRANSFER

Promote **selective prediction**, **selective risk**, **risk-coverage**, **abstention**, and **reject option**.

Selective classification formalizes the trade-off between prediction coverage and conditional error. Geifman and El-Yaniv's deep selective-classification work is a useful modern anchor. citeturn953460search7 In NLP, *The Art of Abstention* explicitly studies selective prediction and confidence estimation for NLP tasks. citeturn757972search40

This remains TRANSFER because the target output is a free-form, multi-claim report with several different possible semantic failures.

### F9 — Probability calibration and proper scoring — TRANSFER

Promote:

- probability calibration;
- reliability;
- Brier score;
- calibration error;
- temperature scaling;
- calibration under shift.

Brier's probability-forecast score dates to 1950. citeturn981040search0 Modern neural-network calibration terminology is strongly anchored by Guo et al.'s *On Calibration of Modern Neural Networks*. citeturn757972search1

For this project, a probability must always have an explicit event, for example:

- probability that a claim is supported;
- probability that a citation fully supports its claim;
- probability that the report omitted a due Topic;
- probability that the reconstructed state is current.

A single “report confidence” is not an adequate calibration target.

### F10 — Reject-option decision theory and risk-coverage — TRANSFER

The phrase **reject option** has a much older technical lineage than modern LLM abstention. Chow's *On Optimum Recognition Error and Reject Tradeoff* formalized the error/reject trade-off in 1970, building on still earlier reject-rule work. citeturn780385search83

Discovery should retain this older literature because it clarifies the decision-theoretic meaning of abstention: rejection is useful only in relation to the error and coverage it trades against.

### F11 — Online calibration and conformal prediction under distribution shift — TRANSFER

This is the main methodological family for **gap-8**.

Promote:

- adaptive conformal inference;
- online conformal prediction/inference;
- calibration under distribution shift;
- non-stationary calibration;
- drifting streams;
- concept drift plus calibration;
- online coverage guarantees.

Conformal prediction has mature foundations; Shafer and Vovk's tutorial describes prediction sets with specified coverage under its assumptions, and the 2005 Vovk-Gammerman-Shafer book is a foundational treatment. citeturn981040search1turn981040search3

More directly relevant to gap-8, **Adaptive Conformal Inference Under Distribution Shift** studies online prediction when distributions vary over time, and later work develops conformal inference for arbitrary distribution shifts. citeturn207856search7turn207856search6

However, these results are still transfer evidence. Discovery must not silently reinterpret long-run label or interval coverage as calibrated correctness of evolving free-form workplace reports.

### F12 — Human evaluation reliability and evaluator meta-evaluation — DIRECT

Promote:

- robust human evaluation;
- inter-annotator agreement;
- adjudication;
- meta-evaluation;
- evaluator bias;
- LLM-judge validation;
- human-grounded evaluation.

RoSE is a useful direct anchor because it was motivated partly by insufficient scale and low agreement in summarization human evaluation and develops an ACU-based annotation protocol. citeturn207856search1

Literature here can inform gap-6 and gap-7, but it cannot decide msgloom's project-specific minimum review volume, risk-stratified sampling strategy, acceptance thresholds or holdout policy.

### F13 — Longitudinal workplace communication and briefing benchmarks — DIRECT

This is a deliberately bounded direct search for any literature that has been missed in earlier rounds.

Admission requires more than the word *email*. Strong candidates should contain several of:

- multiple threads or channels;
- repeated evaluation cycles;
- changing work-item state;
- revisions or corrections;
- quoted/forwarded history;
- conflicting information;
- asynchronous or out-of-order arrival;
- attachments or versions;
- permissions;
- obligations, deadlines or due items; and
- omission of decision-relevant state.

Ordinary email-thread summarization is not sufficient to close gap-2 or gap-5.

### F14 — Decision-focused and utility-sensitive evaluation — TRANSFER

This family supports asymmetric loss and project-value reasoning.

Useful terms are **utility-sensitive evaluation**, **cost-sensitive selective prediction**, **asymmetric error cost**, and **decision utility**. The raw phrase *decision-focused evaluation* should be demoted because it frequently retrieves decision-focused learning and predict-then-optimize research rather than evaluation of generated text.

## Query families

### F1 — Claim-level factuality — DIRECT

- `"factual consistency" evaluation summarization generated claims source evidence`
- `"factuality evaluation" long-form generation claim-level evidence`
- `"faithfulness evaluation" summarization source grounded factual consistency`
- `"factual consistency metric" grounded generation human evaluation`

### F2 — Atomic decomposition — DIRECT

- `"claim decomposition" factuality evaluation generation`
- `"atomic facts" factuality evaluation long-form generation`
- `"atomic claim" verification generated text`
- `"Atomic Content Units" summarization evaluation`
- `"proposition-level" evaluation summarization factuality`

### F3 — Attribution and citation correctness — DIRECT

- `"attribution evaluation" natural language generation evidence`
- `"Attributable to Identified Sources" generation evaluation`
- `"citation correctness" generated text evidence`
- `"citation precision" LLM generation supporting evidence`
- `"source attribution" grounded generation evaluation`

### F4 — Evidence completeness and compound claims — DIRECT

These should receive the highest round-3 priority:

- `"citation completeness" "compound claims" multi-source`
- `"citation recall" "compound claim" generation`
- `"evidence completeness" "partial support" multi-source claim`
- `"evidence sufficiency" "compound claim" fact verification`
- `"partially supported" claim attribution evidence generation`
- `"multi-source" "evidence completeness" generated claims`
- `"complementary evidence" claim verification multi-hop`
- `"citation completeness" multiple evidence passages long-form generation`
- `"evidence completeness" temporal versioned evidence attribution`
- `"claim decomposition" "citation completeness" evidence`

### F5 — Omission and semantic coverage — DIRECT

- `"omission detection" summarization content evaluation`
- `"content coverage" summarization evaluation semantic units`
- `"summary completeness" factuality omission evaluation`
- `"Atomic Content Units" salience coverage omission`
- `"Pyramid Method" summarization content coverage evaluation`
- `"information omission" long-form generation evaluation`

### F6 — Evolving information and update summarization — DIRECT

These are the primary gap-5 queries:

- `"update summarization" evaluation content coverage novelty`
- `"temporal summarization" evaluation evolving information coverage`
- `"timeline summarization" evaluation omission coverage`
- `"longitudinal summarization" evolving state evaluation`
- `"update summarization" stale information superseded`
- `"temporal summarization" current state conflicting updates`
- `"incremental summarization" repeated updates evaluation omission`
- `"evolving events" summarization evaluation content selection`

### F7 — Integrated evaluation — DIRECT

These are the primary gap-1 queries:

- `"evaluation framework" factuality attribution "evidence completeness" temporal correctness omission uncertainty abstention "free-form generation"`
- `"multi-dimensional evaluation" grounded generation factuality attribution completeness uncertainty`
- `"evaluation framework" "citation completeness" factuality abstention calibration generation`
- `"benchmark" factuality attribution citation recall abstention calibration "long-form generation"`
- `"generation evaluation" factuality attribution completeness omission calibration`
- `"reliability evaluation" free-form generation attribution completeness abstention`

The first query deliberately remains close to the prior gap query so that round 3 can distinguish “no result” from terminology drift rather than silently changing the question.

### F8 — Selective prediction — TRANSFER

- `"selective prediction" NLP abstention "risk coverage"`
- `"selective prediction" language generation abstention`
- `"selective generation" confidence calibration factuality`
- `"risk-coverage" language model factuality abstention`
- `"abstention" generated answers evidence uncertainty coverage`
- `"selective prediction" question answering distribution shift`

### F9 — Calibration — TRANSFER

- `"uncertainty calibration" NLP generation factuality`
- `"calibration" language model factual correctness confidence`
- `"expected calibration error" NLP uncertainty`
- `"Brier score" language model confidence factuality`
- `"calibration" claim-level factuality generation`
- `"probability calibration" abstention NLP`

### F10 — Reject option and selective risk — TRANSFER

- `"reject option" selective prediction risk coverage`
- `"selective risk" coverage abstention`
- `"risk-coverage curve" selective classification`
- `"error reject tradeoff" selective prediction`
- `"selective classification" calibrated confidence coverage risk`

### F11 — Continuing distribution shift — TRANSFER

These are the main gap-8 queries:

- `"selective prediction" non-stationary stream distribution shift calibration abstention`
- `"selective prediction" concept drift calibration`
- `"adaptive conformal inference" distribution shift online`
- `"online conformal" nonstationary distribution shift`
- `"conformal prediction" temporal distribution shift adaptive`
- `"online calibration" nonstationary stream prediction`
- `"calibration under distribution shift" NLP`
- `"selective prediction" distribution shift NLP abstention`
- `"adaptive calibration" language model distribution shift`
- `"free-form generation" distribution shift calibration abstention`

The family should retrieve adaptive-conformal work such as Gibbs and Candès, but such papers count as TRANSFER until the semantic prediction target and free-form output setting match the project. citeturn207856search7turn207856search6

### F12 — Human and evaluator reliability — DIRECT

- `"human evaluation reliability" text generation factuality`
- `"inter-annotator agreement" factuality summarization evaluation`
- `"meta-evaluation" factual consistency metrics human judgments`
- `"LLM judge" factuality evaluation human agreement bias`
- `"automatic evaluator" bias generation evaluation human validation`
- `"evaluator bias" LLM generated text evaluation`
- `"evaluation metric" overfitting meta-evaluation text generation`

### F13 — Workplace longitudinal benchmark search — DIRECT

- `"email summarization" longitudinal evaluation evolving`
- `"email thread summarization" update evaluation omission`
- `"workplace communication" summarization evaluation action items`
- `"enterprise communication" summarization longitudinal`
- `"meeting email" longitudinal summarization state tracking`
- `"workplace" "update summarization" communication`
- `"email" summarization revisions quoted history conflicting information`
- `"conversation summarization" superseded information temporal`
- `"work item" summarization evolving state evaluation`

This family should be stopped after a controlled direct-domain search if results again consist only of static email summarization or generic dialogue summarization. Gap-2 is an ENGINEERING validation gap, not justification for an indefinite literature search.

### F14 — Utility and asymmetric error cost — TRANSFER

- `"decision-focused evaluation" natural language generation`
- `"utility-sensitive evaluation" NLP abstention`
- `"cost-sensitive" selective prediction abstention NLP`
- `"asymmetric loss" selective prediction reject option`
- `"decision utility" summarization evaluation`
- `"risk-sensitive" generation evaluation abstention`

## False friends and downgrade rules

Discovery should apply the following rules before admitting results:

1. **One aggregate score is insufficient.** A factuality, faithfulness, hallucination or groundedness metric that collapses all failures into one number cannot close gap-1.
2. **Citation presence is not citation correctness.** Papers counting references without checking semantic support are not relevant evidence for attribution correctness.
3. **Citation correctness is not citation completeness.** A system can cite every cited statement correctly while leaving half its other claims unsupported.
4. **Single-source support is not automatically complete support.** For gap-4, compound claims must be decomposed or otherwise assessed for partial and complementary support.
5. **Retrieval recall is not evidence completeness.** Finding relevant passages says nothing about whether the generated claim has all necessary support.
6. **Static fact checking is transfer evidence.** FEVER-style or misinformation verification is useful only when its evaluation machinery transfers to generation, attribution or evidence sufficiency.
7. **Static summarization cannot directly close the longitudinal omission gap.** Gap-5 requires evolving information, prior state or repeated observation cycles.
8. **Novelty alone is insufficient.** Update summarization that scores only newness/redundancy without important-information omission does not close gap-5.
9. **Event ordering alone is insufficient.** Timeline generation must measure missing or superseded decision-relevant facts before it is treated as current-state evaluation.
10. **Generic email summarization does not close gap-2.** Direct target evidence needs realistic revisions, history, conflicts, asynchronous arrival, versions or comparable workplace complications.
11. **Synthetic/public evidence cannot establish production-email representativeness.** It can validate mechanisms and fixtures only.
12. **Raw model confidence is not calibration.** Token probability, entropy or verbal confidence requires empirical calibration against a named correctness event.
13. **ECE alone is not enough.** Calibration evaluation should not hide local failures, distribution shift or useful operating coverage behind one binned statistic.
14. **Abstaining on everything is not a reliability solution.** Risk and coverage must be reported together.
15. **Selective classification remains TRANSFER** when it only predicts one class and does not establish applicability to multi-claim generation.
16. **Conformal prediction remains TRANSFER** unless the assumptions and output object actually match the non-stationary free-form problem.
17. **Prediction-set coverage is not semantic completeness.** A formal coverage guarantee for labels or intervals cannot be relabeled as evidence completeness.
18. **One-time domain shift is weaker than continuing non-stationarity.** Gap-8 concerns streams whose distribution continues to change.
19. **Inter-annotator agreement is not ground truth.** Agreement must be distinguished from label validity, adjudication and representative sampling.
20. **Unvalidated LLM judges are insufficient.** Judge agreement must be established against independent human or ground-truth judgments on the actual evaluation dimensions.
21. **Evaluator-bias papers do not themselves solve gap-7.** Independent holdouts, evaluator separation and regression policy remain project engineering decisions.
22. **Reject authorship attribution/plagiarism/source-classification results** unless they concern attribution of generated statements to supporting evidence.
23. **Reject code/test/network/geographic coverage literature** returned by the word *coverage*.
24. **Reject grammatical or ASR deletion literature** returned by *omission* unless it addresses semantic information omission.
25. **Reject generic decision-focused learning** unless it contributes a usable asymmetric-risk or evaluation method.
26. **Count studies, not records.** Multiple identifiers or duplicate corpus records for one underlying study must not be treated as independent corroboration.

## Date policy

**Earliest publication year discovery must include: 1950.**

A recency filter starting at the LLM era would silently remove several foundations required to interpret the modern terminology correctly. Glenn W. Brier's *Verification of Forecasts Expressed in Terms of Probability* was published in 1950 and anchors the Brier-score branch of probabilistic evaluation. citeturn981040search0 Reject-option theory predates modern machine learning; Chow's error/reject trade-off work appeared in 1970 and the literature traces the optimal reject-rule problem to earlier work by Chow. citeturn780385search83turn780385search13

The summarization-content branch also predates current LLM metrics: the Pyramid Method was published in 2004. citeturn780385search0 Conformal prediction was established before the present generative-AI period, with the 2005 *Algorithmic Learning in a Random World* and 2008 JMLR tutorial providing key foundations. citeturn981040search3turn981040search1

Therefore discovery should use **1950 as the hard lower bound**, but rank modern direct evidence above foundational transfer literature. The older window should be activated through tightly scoped query families—Brier/proper scoring, reject option, summarization content units and conformal prediction—not by running an unconstrained generic search from 1950.

The round-3 search objective is not literature exhaustion. It is to determine whether targeted terminology uncovers evidence that actually closes gaps 1, 4, 5 or 8; if direct searches again return only component methods or transfer results, those gaps should remain open rather than being closed by semantic stretching.
