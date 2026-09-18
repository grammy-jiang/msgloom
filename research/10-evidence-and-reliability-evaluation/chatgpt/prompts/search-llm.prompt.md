You are one worker inside an automated literature-review pipeline.
A script, not a person, reads your reply. Follow these rules exactly:
- Do the task completely in this single reply. Do not ask questions and do not
  wait for confirmation.
- Reply with the requested artifact block(s) only: no preamble, no commentary
  outside the blocks. Each block starts with a line `===BEGIN <name>===` and
  ends with a line `===END <name>===`; the content between those lines is
  written to a file verbatim.
- Never invent papers, identifiers, numbers, or quotes. Leave unknown fields
  out or mark them as unknown.
- Do not use your code tool, canvas, or connectors; plain text is enough.

# Task: literature search

Research topic: **Joint evaluation and selective prediction for temporally evolving multi-source generation: evidence completeness for compound and partially supported claims, longitudinal omission of superseded or due work-item state, and online calibration under non-stationary streams**

Must-have terms: joint, selective
Nice-to-have terms: prediction, temporally, evolving, multi-source, generation:, evidence, completeness, compound, partially, supported, claims,, longitudinal, omission, superseded, due, work-item, state,, online, calibration, under, non-stationary, streams
Date range: {"primary_months": 300, "fallback_months": 480}

Run every query below with your web search tool. Prefer arXiv listings
(arxiv.org/abs/<id>) but include other venues when they are clearly relevant;
much of the foundational work in a field is in conference proceedings rather
than on arXiv, and it must not be dropped for that reason. Aim for 30-60
distinct papers (at least 5). Stop when new searches only return papers
already listed.

Query families (from the terminology analysis; DIRECT means the
literature studies this problem, TRANSFER means the method may carry
over from another domain). Run every query:
- tf_atomic_factuality [DIRECT]
    "atomic claims" factuality evaluation generated text evidence support
    "claim decomposition" factuality verification evidence generation
    "atomic fact" evaluation partial support generated text
    "proposition-level" factual consistency evidence evaluation generation
    "compound claims" decomposition verification partial entailment
- tf_citation_attribution [DIRECT]
    "citation correctness" "citation completeness" generation
    "citation precision" "citation recall" language model generation
    "citation quality" claim-level support long-form generation
    "source attribution" generated claims evidence evaluation
    "attribution evaluation" grounded generation citations
- tf_evidence_completeness [DIRECT]
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
- tf_joint_multidimensional_eval [DIRECT]
    "multidimensional evaluation" generation factuality attribution completeness uncertainty
    "holistic evaluation" RAG factuality citation completeness calibration
    "joint evaluation framework" factuality attribution completeness abstention generation
    "end-to-end evaluation" generation evidence attribution completeness uncertainty
    "claim-level evaluation" citation completeness abstention calibration
    "generation evaluation framework" factual correctness attribution coverage uncertainty
    "RAG evaluation" citation completeness factuality abstention uncertainty
- tf_temporal_currentness [TRANSFER]
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
- tf_longitudinal_omission [TRANSFER]
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
- tf_selective_generation [DIRECT]
    "selective prediction" natural language generation abstention
    "selective generation" language model risk coverage
    "selective generation" LLM abstention
    "answer abstention" question answering calibration coverage
    "selective question answering" risk coverage
    "risk-coverage" language model generation
    "abstention" RAG factuality uncertainty
    "abstention" generated answers calibrated confidence
- tf_selective_foundations [TRANSFER]
    "selective classification" risk coverage
    "classification with a reject option" risk coverage
    "reject option" calibrated confidence classification
    "selective risk" coverage prediction
    "risk-coverage curve" selective prediction
    "error reject tradeoff" prediction
- tf_calibration_generation [DIRECT]
    "uncertainty calibration" natural language generation factuality
    "calibrated confidence" factuality language model
    "calibration" generated answer correctness language model
    "calibration" question answering abstention ECE Brier
    "claim-level confidence" calibration factuality
    "probability calibration" LLM answer correctness
    "confidence calibration" RAG answer correctness
- tf_online_nonstationary_calibration [TRANSFER]
    "online calibration" concept drift probabilistic prediction
    "calibration under distribution shift" sequential prediction
    "adaptive calibration" concept drift prediction
    "prequential calibration" nonstationary
    "online recalibration" distribution shift machine learning
    "calibration" non-stationary stream concept drift
    "selective prediction" distribution shift calibration
    "risk coverage" distribution shift selective prediction
- tf_conformal_risk_control [TRANSFER]
    "adaptive conformal inference" distribution shift
    "online conformal prediction" nonstationary
    "conformal prediction" concept drift online
    "conformal risk control" NLP
    "conformal risk control" language generation
    "conformal prediction" abstention language model
    "adaptive conformal" selective prediction risk coverage
- tf_human_metaevaluation [DIRECT]
    "human evaluation reliability" NLP generation
    "inter-annotator agreement" factuality summarization evaluation
    "meta-evaluation" summarization factuality metrics human
    "LLM as a judge" human validation evaluator bias
    "LLM judge" agreement human evaluation factuality
    "evaluator bias" language model judge evaluation
    "metric overfitting" automatic evaluation generation
    "evaluation leakage" language generation metric
    "adjudication" factuality annotation summarization
- tf_utility_sensitive_eval [TRANSFER]
    "cost-sensitive" selective prediction abstention
    "utility-sensitive" abstention prediction
    "decision-theoretic" reject option prediction
    "asymmetric error costs" selective prediction
    "decision-focused evaluation" language generation
    "risk-sensitive" evaluation abstention NLP
    "expected utility" abstention language model
False friends — these match the words but not the capability, so do
not list them:
- Downgrade literature that reports one aggregate hallucination, faithfulness, groundedness, or quality score when claim correctness, attribution correctness, evidence completeness, temporal correctness, omission, and abstention are not separately recoverable.
- Downgrade citation work that counts citation presence or syntactic citation validity without testing whether the cited source actually supports the associated claim.
- Downgrade citation-precision studies as evidence for completeness unless uncited support-requiring claims are explicitly included in a recall or coverage denominator.
- Downgrade evidence-completeness studies that score whole sentences as supported when compound propositions can be only partially supported.
- Downgrade multi-source work that merely retrieves several documents but never tests whether complementary evidence is jointly necessary to support a claim.
- Downgrade fact-verification work that assumes one immutable claim and one static corpus when used as evidence for temporal or version-aware correctness.
- Downgrade temporal papers where 'temporal' only means adding timestamps or temporal embeddings and no changing truth, revision, supersession, staleness, or observation cutoff is evaluated.
- Downgrade update or timeline summarization to TRANSFER unless it explicitly evaluates information omission, novelty, redundancy, state/value changes, or obsolete information across observation times.
- Do not treat news-event temporal summarization as direct evidence for workplace obligations, deadlines, approvals, cancellations, or due work-item state.
- Downgrade omission papers about linguistic ellipsis, missing tokens, grammar correction, or coding omissions unless the missing object is decision-relevant semantic content in a generated report.
- Downgrade selective-classification results to TRANSFER when risk is ordinary label error on a fixed IID benchmark.
- Downgrade calibration studies that calibrate next-token probability or model self-confidence without a clearly defined task-level correctness event.
- Downgrade studies reporting ECE alone when there is no proper scoring rule, subgroup analysis, risk-coverage behavior, or other evidence sufficient to detect localized calibration failure.
- Downgrade abstention demonstrations that measure how often a model refuses but not the error rate among accepted predictions and the recall or utility lost through refusals.
- Downgrade classical conformal prediction to TRANSFER when validity depends on exchangeability and the paper does not address drift, online adaptation, or a deployment assumption plausibly matching a communication stream.
- Downgrade concept-drift detection papers that only detect a shift and do not recalibrate uncertainty, control risk, or change the selective decision policy.
- Downgrade RAG evaluation papers that measure retrieval relevance only; retrieval quality is not generated-claim correctness or evidence completeness.
- Downgrade LLM-as-judge findings when the judge has not been validated against independent human judgments or suitable gold labels for the same construct.
- Downgrade human-evaluation work that reports inter-annotator agreement as if agreement alone established validity, representativeness, or an adequate sample size.
- Do not claim gap-2 closed from public, synthetic, news, QA, or generic enterprise data. The missing private-workplace fixture suite with revisions, quoted history, permissions, versions, and out-of-order arrival is an ENGINEERING validation gap.
- Do not claim gap-6 closed from generic annotation guidance. Representative or risk-stratified sampling, minimum review volume, adjudication, confusion matrices, abstention accounting, and judge validation remain project-specific ENGINEERING choices.
- Do not claim gap-7 closed merely because a paper documents evaluator bias. Independent holdouts, evaluator separation, anti-overfitting procedures, and regression checks must be implemented and validated for this project.
- A paper may inform gap-1 without closing it. Gap-1 closes only if one admitted study validates the required dimensions jointly while preserving distinct denominators rather than deriving them from one composite score.
- A paper may inform gap-4 without closing it. Gap-4 closes only if compound claims, partial support, complementary multi-source evidence, and temporal or versioned evidence are handled jointly in the evaluated method.
- A paper may inform gap-5 without closing it. Gap-5 closes only if omission is evaluated longitudinally for evolving state, including obsolete or superseded facts or functionally equivalent due-state information.
- A paper may inform gap-8 without closing it. Gap-8 closes only if selective prediction or risk control is validated under continuing non-stationarity in a sufficiently analogous free-form communication or generation setting.
Reach back to 1950 at least. The global discovery floor should be 1950 because the supplied terminology explicitly includes the Brier score, whose foundational probability-forecast verification paper is Brier's 1950 'Verification of Forecasts Expressed in Terms of Probability'. Selective rejection also has foundational work by Chow in 1970, while modern selective-classification, calibration, update-summarization, RAG, and LLM-evaluation work is much newer. A modern-only window would therefore silently remove foundational calibration and reject-option literature. Discovery should use 1950 as the global floor but apply family-specific queries: only the calibration, proper-scoring, reject-option, and selective-prediction foundation searches need to range that far back; direct generation-evaluation searches will naturally concentrate in the 2000s–2020s. citeturn703828search1turn663158search0

This is gap-closure round 4 of at most 4 for the
original topic **evidence attribution, factuality, completeness and reliability evaluation for workplace communication systems: what exact evidence supports each decision-relevant statement, whether it is current and correctly attributed, what was omitted, and when the system should abstain**. Earlier rounds could not
close the open gaps below. Run every suggested query as well, and look
specifically for papers that answer these gaps:
- gap-1 [ACADEMIC, HIGH]: No admitted study validates one end-to-end evaluation scheme that jointly measures claim correctness, evidence attribution correctness, citation or evidence completeness, temporal or current-state correctness, omission, calibrated uncertainty, and abstention while preserving separate denominators for those dimensions. The corpus validates individual components and smaller combinations.
    suggested query: "joint evaluation framework" factuality attribution completeness temporal correctness omission calibration abstention "free-form generation" multi-source
    searched in rounds: [1, 2, 3] (still open)
- gap-4 [ACADEMIC, HIGH]: The corpus does not establish a general evidence-completeness method that jointly handles compound claims, partially supportive evidence, multiple complementary sources, and temporally versioned evidence. Separate studies cover subsets of these conditions.
    suggested query: "evidence completeness" compound claims partial support complementary evidence multi-source temporal versioning provenance evaluation
    searched in rounds: [1, 2, 3] (still open)
- gap-5 [ACADEMIC, HIGH]: Report-level omission has substantial benchmark coverage, but the corpus still does not establish omission detection for evolving workplace work items, due information, superseded facts, or decision-relevant state across time.
    suggested query: "omission detection" longitudinal summarization work-item state superseded facts due dates temporal updates decision-relevant information
    searched in rounds: [1, 2, 3] (still open)
- gap-8 [ACADEMIC, MEDIUM]: Calibration under continuing temporal or distributional change remains open for non-stationary free-form communication streams. The corpus supplies adaptive coverage results, cross-domain calibration studies, benchmark-aging evidence, and structured-generation risk-control results, but not one validated selective-prediction method for continuously changing workplace communication.
    suggested query: "selective prediction" "non-stationary" free-form generation online calibration concept drift abstention adaptive conformal temporal stream
    searched in rounds: [1, 2, 3] (still open)

Papers already reviewed in earlier rounds (do NOT list them again):
1707.05555, 1910.12840, 2004.14974, 2012.14983, 2105.00071, 2106.00170, 2111.09525, 2212.08037, 2302.07869, 2305.14627, 2307.09254, 2312.09300, 2402.05629, 2404.00474, 2404.15588, 2405.00982, 2406.07967, 2408.08067, 2410.14964, 2505.23912, 2508.20867, 2509.26184, 2510.07238, 2510.12839, 2511.16198, 2512.17776, 2602.11908, 2602.16537, 2604.03141, 2604.12046, 2605.01749, 2605.03534, 2605.06635, 2605.16354, 2606.00093, 2606.29054, 2607.03870, 2607.08700, 2607.19322, 2608.11238, 2608.22483, doi-10-1017-s1351324909005051, doi-10-1109-access-2026-3679691, doi-10-1162-tacl-a-00407, doi-10-18653-v1-2025-acl-long-837, doi-10-18653-v1-w19-8642, doi-10-32604-cmc-2026-086343, doi-10-6028-nist-sp-500-321-realtime-overview, manual-32d5793dca, manual-39435af3dd, manual-f5ce52cae2

Write one JSON object per line. Fields (only `title` is mandatory):
- title: exact paper title
- url: arxiv.org/abs/<id> when available, else the landing page
- arxiv_id: e.g. 2401.12345 (omit when not on arXiv)
- doi: if known
- authors: list of author names
- year: integer
- published: YYYY-MM-DD if known
- abstract: the abstract, or a faithful paraphrase of at most 5 sentences
- venue: conference or journal if known

Reply format (one block, one JSON object per line, no array brackets):
===BEGIN llm_candidates.jsonl===
<content>
===END llm_candidates.jsonl===
