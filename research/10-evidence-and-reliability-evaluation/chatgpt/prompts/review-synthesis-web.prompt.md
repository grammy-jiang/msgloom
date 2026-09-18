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

# Task: independent review of the cross-paper synthesis

Research topic: **Joint evaluation and selective prediction for temporally evolving multi-source generation: evidence completeness for compound and partially supported claims, longitudinal omission of superseded or due work-item state, and online calibration under non-stationary streams**

You did not write this synthesis and you are not reviewing your own work.
Your verdict decides whether the report may be written. Rejecting is a normal
outcome: reject when the evidence does not support the synthesis. Do not
soften a real problem into a note so that the work can pass.

Check five things against the analyses below, not against how well the
synthesis reads:

1. Faithfulness — every finding is traceable to at least one analysis, and no
   finding states more than its cited analyses support.
2. Citation integrity — every cited paper_id is one of: `1707.05555`, `1910.12840`, `2004.14974`, `2006.09462`, `2012.14983`, `2105.00071`, `2106.00170`, `2111.09525`, `2204.02007`, `2208.02814`, `2208.08401`, `2212.08037`, `2302.07869`, `2305.11859`, `2305.14627`, `2307.09254`, `2312.09300`, `2402.05629`, `2404.00474`, `2404.15588`, `2405.00982`, `2406.07967`, `2408.08067`, `2410.14964`, `2505.23912`, `2508.20867`, `2509.26184`, `2510.07238`, `2510.12839`, `2511.01101`, `2511.16198`, `2512.17776`, `2602.11908`, `2602.16537`, `2604.03141`, `2604.12046`, `2605.01749`, `2605.03534`, `2605.06635`, `2605.16354`, `2606.00093`, `2606.27736`, `2606.29054`, `2607.03870`, `2607.08700`, `2607.19322`, `2608.11238`, `2608.22483`, `doi-10-1016-j-jisa-2025-104120`, `doi-10-1017-s1351324909005051`, `doi-10-1038-s41598-026-40637-w`, `doi-10-1109-access-2026-3679691`, `doi-10-1155-2016-1340973`, `doi-10-1162-tacl-a-00407`, `doi-10-1609-aaai-v40i40-40667`, `doi-10-18653-v1-2021-acl-long-84`, `doi-10-18653-v1-2025-acl-long-837`, `doi-10-18653-v1-w19-8642`, `doi-10-32604-cmc-2026-086343`, `doi-10-6028-nist-sp-500-321-realtime-overview`, `manual-2be3626f9e`, `manual-32d5793dca`, `manual-39435af3dd`, `manual-f5ce52cae2`.
3. Coherence — contradictions between papers are named, not averaged away.
4. Gap completeness — a gap this corpus cannot close is reported as open. A
   gap presented as closed without evidence is a rejection.
5. Overreach — transfer-domain or synthetic evidence is not presented as
   direct-domain evidence, and no production claim rests on it.

Synthesis under review:
{
 "topic": "Joint evaluation and selective prediction for temporally evolving multi-source generation: evidence completeness for compound and partially supported claims, longitudinal omission of superseded or due work-item state, and online calibration under non-stationary streams",
 "paper_count": 64,
 "executive_summary": "Across 64 corpus records, the evidence consistently supports decomposed reliability evaluation rather than a single factuality score. Summarization, RAG, report-generation, attribution, and fact-verification studies separate claim correctness, source support, evidence recall, and omission; temporal studies further show that current-state validity can diverge from generic support. Selective-prediction work demonstrates useful risk-coverage control and improved calibration in several domains, but guarantees depend on confidence quality, calibration regime, and shift assumptions. Online conformal methods provide strong results for changing streams, while structured-generation studies show that static or simply adaptive methods can fail under severe cross-dataset shift. Report and update-summarization benchmarks evaluate omission and redundancy, yet none directly models longitudinal workplace work-item states. The corpus therefore supplies strong component-level evidence but does not validate a single joint scheme for compound, multi-source, temporally versioned, selectively generated workplace briefings.",
 "themes": [
  "Dimension-separated evaluation of factual correctness, attribution, evidence completeness, and omission",
  "Atomic-claim decomposition combined with cross-claim and aggregate consistency checks",
  "Evidence sufficiency, partial support, and complementary multi-source evidence",
  "Temporal validity, benchmark aging, chronological reasoning, and out-of-order evidence",
  "Omission, novelty, repetition, and content-unit coverage in reports and update summaries",
  "Selective prediction, abstention, and risk-coverage trade-offs",
  "Online calibration and conformal methods under distribution shift",
  "Human-review reliability and validation of automated evaluators",
  "Retrieval and generation as separable sources of end-to-end failure"
 ],
 "findings": [
  {
   "statement": "Across summarization, attributed QA, report evaluation, and RAG, claim correctness, attribution correctness, and completeness behave as distinct quantities; evaluated systems can score differently on these dimensions rather than collapsing to one quality signal.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "2212.08037",
     "section": "key_findings"
    },
    {
     "paper_id": "2305.14627",
     "section": "key_findings"
    },
    {
     "paper_id": "2405.00982",
     "section": "key_findings"
    },
    {
     "paper_id": "2408.08067",
     "section": "key_findings"
    }
   ]
  },
  {
   "statement": "Fine-grained or atomic decomposition improves factual-consistency diagnosis and evidence localization in several summarization and long-form evaluation settings, while independent atomic verification can miss aggregate errors such as entity mixing or contradictory composition.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "1910.12840",
     "section": "key_findings"
    },
    {
     "paper_id": "2111.09525",
     "section": "key_findings"
    },
    {
     "paper_id": "2402.05629",
     "section": "key_findings"
    },
    {
     "paper_id": "2510.12839",
     "section": "key_findings"
    },
    {
     "paper_id": "2604.03141",
     "section": "key_findings"
    }
   ]
  },
  {
   "statement": "Evidence-sufficiency and complex-verification studies show substantial error when available evidence is incomplete, partially supportive, or distributed across multiple sources; decomposition and explicit evidence-group modeling improve subsets of this problem but do not jointly cover every condition.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "2204.02007",
     "section": "key_findings"
    },
    {
     "paper_id": "2305.11859",
     "section": "key_findings"
    },
    {
     "paper_id": "2404.15588",
     "section": "key_findings"
    },
    {
     "paper_id": "2508.20867",
     "section": "key_findings"
    },
    {
     "paper_id": "doi-10-18653-v1-2025-acl-long-837",
     "section": "key_findings"
    },
    {
     "paper_id": "doi-10-32604-cmc-2026-086343",
     "section": "key_findings"
    }
   ]
  },
  {
   "statement": "Temporal evidence validity is separable from generic factual support: stale benchmark labels can penalize current answers, citations can support a fact yet be invalid for the queried time, and explicit chronological reasoning improves temporal fact verification in the studied benchmarks.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "2510.07238",
     "section": "key_findings"
    },
    {
     "paper_id": "doi-10-1109-access-2026-3679691",
     "section": "key_findings"
    },
    {
     "paper_id": "2410.14964",
     "section": "key_findings"
    },
    {
     "paper_id": "1707.05555",
     "section": "key_findings"
    }
   ]
  },
  {
   "statement": "Report and update-summarization evaluations can measure omission-like coverage separately from repetition or redundancy by using nuggets, content units, novelty judgments, or weighted coverage; the admitted studies do not directly evaluate omission of longitudinal workplace work-item states such as due, resolved, or superseded items.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "2405.00982",
     "section": "key_findings"
    },
    {
     "paper_id": "doi-10-1017-s1351324909005051",
     "section": "key_findings"
    },
    {
     "paper_id": "doi-10-1155-2016-1340973",
     "section": "key_findings"
    },
    {
     "paper_id": "doi-10-6028-nist-sp-500-321-realtime-overview",
     "section": "key_findings"
    },
    {
     "paper_id": "manual-39435af3dd",
     "section": "key_findings"
    },
    {
     "paper_id": "2607.19322",
     "section": "key_findings"
    }
   ]
  },
  {
   "statement": "Selective-prediction studies across QA, classification, RAG, and free-form generation show that confidence-based abstention can reduce accepted-answer risk, but raw sequence likelihood or uncalibrated probabilities are often poor selectors and performance varies by domain, model, and calibration regime.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "2006.09462",
     "section": "key_findings"
    },
    {
     "paper_id": "doi-10-1162-tacl-a-00407",
     "section": "key_findings"
    },
    {
     "paper_id": "2312.09300",
     "section": "key_findings"
    },
    {
     "paper_id": "doi-10-18653-v1-2021-acl-long-84",
     "section": "key_findings"
    },
    {
     "paper_id": "2605.03534",
     "section": "key_findings"
    },
    {
     "paper_id": "2608.22483",
     "section": "key_findings"
    }
   ]
  },
  {
   "statement": "Online conformal methods provide adaptive coverage results under changing distributions in election, forecasting, image-shift, and theoretical drift settings, but their guarantees differ in locality and assumptions, and structured LLM experiments show that static conformal risk control and ACI can violate emitted-risk targets under severe cross-dataset shift.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "2106.00170",
     "section": "key_findings"
    },
    {
     "paper_id": "2208.08401",
     "section": "key_findings"
    },
    {
     "paper_id": "2302.07869",
     "section": "key_findings"
    },
    {
     "paper_id": "2602.16537",
     "section": "key_findings"
    },
    {
     "paper_id": "2606.29054",
     "section": "key_findings"
    }
   ]
  },
  {
   "statement": "Verbalized or linguistic confidence can be trained to better track factual correctness or downstream reader beliefs, but calibration, ranking quality, and factual accuracy are distinct: interventions that improve one can leave another unchanged or degrade confidence ranking.",
   "confidence": "MEDIUM",
   "evidence": [
    {
     "paper_id": "2012.14983",
     "section": "key_findings"
    },
    {
     "paper_id": "2404.00474",
     "section": "key_findings"
    },
    {
     "paper_id": "2505.23912",
     "section": "key_findings"
    },
    {
     "paper_id": "2607.03870",
     "section": "key_findings"
    },
    {
     "paper_id": "2604.12046",
     "section": "key_findings"
    }
   ]
  },
  {
   "statement": "Automatic evaluators and LLM judges can reproduce useful system-level signals, but item-level agreement, abstention handling, rating indeterminacy, and directional false-positive or false-negative bias materially affect interpretation; controlled human sampling and human-grounded estimation can reduce review cost without treating the automatic judge as ground truth.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "2212.08037",
     "section": "key_findings"
    },
    {
     "paper_id": "2509.26184",
     "section": "key_findings"
    },
    {
     "paper_id": "2406.07967",
     "section": "key_findings"
    },
    {
     "paper_id": "2605.16354",
     "section": "key_findings"
    },
    {
     "paper_id": "2606.00093",
     "section": "key_findings"
    },
    {
     "paper_id": "2607.08700",
     "section": "key_findings"
    },
    {
     "paper_id": "manual-32d5793dca",
     "section": "key_findings"
    }
   ]
  },
  {
   "statement": "Retrieval and generation form separable bottlenecks in multi-source factual generation: stronger retrieval generally improves downstream quality, while oracle or near-oracle evidence access still leaves generation omissions, unsupported claims, and incomplete evidence use.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "2004.14974",
     "section": "key_findings"
    },
    {
     "paper_id": "2305.14627",
     "section": "key_findings"
    },
    {
     "paper_id": "2408.08067",
     "section": "key_findings"
    },
    {
     "paper_id": "2508.20867",
     "section": "key_findings"
    }
   ]
  }
 ],
 "contradictions": [],
 "gaps": [
  {
   "id": "gap-1",
   "description": "No admitted study validates one end-to-end evaluation scheme that jointly measures claim correctness, evidence attribution correctness, citation or evidence completeness, temporal or current-state correctness, omission, calibrated uncertainty, and abstention while preserving separate denominators for those dimensions. The corpus validates individual components and smaller combinations.",
   "classification": "ACADEMIC",
   "priority": "HIGH",
   "suggested_query": "\"joint evaluation framework\" factuality attribution completeness temporal correctness omission calibration abstention \"free-form generation\" multi-source"
  },
  {
   "id": "gap-2",
   "description": "The corpus contains no direct evaluation on private workplace email or Teams-style communication with realistic revisions, quoted history, conflicting updates, delayed or out-of-order arrival, versioned attachments, and permission-constrained evidence. Target-domain fixtures and gold data remain an engineering validation gap.",
   "classification": "ENGINEERING",
   "priority": "HIGH"
  },
  {
   "id": "gap-4",
   "description": "The corpus does not establish a general evidence-completeness method that jointly handles compound claims, partially supportive evidence, multiple complementary sources, and temporally versioned evidence. Separate studies cover subsets of these conditions.",
   "classification": "ACADEMIC",
   "priority": "HIGH",
   "suggested_query": "\"evidence completeness\" compound claims partial support complementary evidence multi-source temporal versioning provenance evaluation"
  },
  {
   "id": "gap-5",
   "description": "Report-level omission has substantial benchmark coverage, but the corpus still does not establish omission detection for evolving workplace work items, due information, superseded facts, or decision-relevant state across time.",
   "classification": "ACADEMIC",
   "priority": "HIGH",
   "suggested_query": "\"omission detection\" longitudinal summarization work-item state superseded facts due dates temporal updates decision-relevant information"
  },
  {
   "id": "gap-6",
   "description": "A target-domain human-review protocol remains an engineering gap: representative or risk-stratified sampling, minimum human-review volume, multi-rater adjudication, confusion matrices, abstention treatment, coverage reporting, and validation of any LLM-assisted judge against independent human judgments remain project-specific choices.",
   "classification": "ENGINEERING",
   "priority": "HIGH"
  },
  {
   "id": "gap-7",
   "description": "The corpus demonstrates evaluator-optimization effects, rating indeterminacy, abstention sensitivity, and directional judge bias but does not provide a project-specific procedure for preventing acceptance criteria from being overfit to the same automatic evaluator used during development. Independent holdouts, evaluator separation, and regression checks remain an engineering validation problem.",
   "classification": "ENGINEERING",
   "priority": "MEDIUM"
  },
  {
   "id": "gap-8",
   "description": "Calibration under continuing temporal or distributional change remains open for non-stationary free-form communication streams. The corpus supplies adaptive coverage results, cross-domain calibration studies, benchmark-aging evidence, and structured-generation risk-control results, but not one validated selective-prediction method for continuously changing workplace communication.",
   "classification": "ACADEMIC",
   "priority": "MEDIUM",
   "suggested_query": "\"selective prediction\" \"non-stationary\" free-form generation online calibration concept drift abstention adaptive conformal temporal stream"
  }
 ],
 "actionable_insights": [
  "Synthesis-derived recommendation: maintain separate evaluation denominators for claim correctness, attribution correctness, evidence completeness, temporal or current-state correctness, report omission, calibration, and abstention rather than combining them into one acceptance score.",
  "Synthesis-derived recommendation: evaluate both atomic units and their higher-level composition so that locally supported claims do not hide entity mixing, contradictory aggregation, or incorrect work-item-level synthesis.",
  "Synthesis-derived recommendation: represent evidence status with more than a binary supported/unsupported outcome, including partial support, insufficient evidence, conflicting evidence, and complementary multi-source support.",
  "Synthesis-derived recommendation: construct temporal evaluation at explicit observation cutoffs and include delayed arrival, out-of-order evidence, supersession, corrected completion, and disagreements between event time and collection time.",
  "Synthesis-derived recommendation: pair omission measurement with repetition or false-alert measurement on longitudinal work-item fixtures, including new, still-open, resolved, superseded, and due states.",
  "Synthesis-derived recommendation: evaluate confidence using risk-coverage or selective-risk behavior under both stable and shifted streams in addition to scalar calibration error.",
  "Synthesis-derived recommendation: keep automated development evaluators separate from final acceptance holdouts, and validate any LLM-assisted judge on independently reviewed samples with directional error reporting.",
  "Synthesis-derived recommendation: preserve abstention as an explicit evaluation outcome and report coverage alongside covered-case accuracy or agreement rather than silently excluding abstained cases."
 ],
 "confidence_summary": "Evidence is strong for several cross-domain design principles at the component level: reliability dimensions are empirically separable; omission and unsupported generation require different measurements; retrieval and generation contribute distinct failures; and selective prediction has meaningful risk-coverage behavior. Evidence is also strong that temporal validity and distribution shift can invalidate otherwise plausible evaluation signals. Confidence is medium for transfer from summarization, QA, RAG, scientific verification, clinical triage, forecasting, cybersecurity, and news-update tasks to workplace communication. The combined scheme named by this topic remains untested, so the corpus supports well-supported design principles and evaluation mechanisms rather than an empirically validated end-to-end workplace framework.",
 "limitations": [
  "The synthesis is based on the supplied reduced per-paper analyses rather than full papers, so methodological details, negative results, and scope qualifications not retained in those reductions may be missing.",
  "Most evidence comes from summarization, QA, RAG, scientific fact verification, open-web research, news updates, forecasting, clinical triage, cybersecurity, or synthetic benchmarks rather than private workplace email and Teams-style communication.",
  "No admitted paper jointly evaluates all target dimensions, so evidence from papers covering different components cannot be interpreted as validation of their combination.",
  "Results span different datasets, tasks, models, definitions of correctness, confidence, coverage, and abstention; numerical results are therefore not directly comparable across much of the corpus.",
  "No direct contradictions were identified under genuinely comparable questions and conditions. Apparent tensions, such as strong softmax performance in some in-domain classification settings versus overconfidence under shifted QA, or successful adaptive conformal coverage in forecasting versus ACI failures under structured-generation cross-dataset shift, are scope qualifications rather than contradictions [doi-10-18653-v1-2021-acl-long-84] [2006.09462] [2106.00170] [2606.29054].",
  "The supplied records do not contain enough bibliographic metadata for duplicate-study detection beyond the visible identifiers and titles, so paper_count denotes corpus records rather than a guaranteed count of distinct underlying studies.",
  "Inherited handoffs are treated only as project context and gap provenance; none is used as evidence for findings or for closing a gap."
 ],
 "gap_status": [
  {
   "id": "gap-1",
   "status": "open",
   "note": "Newer papers add component-level combinations such as completeness plus support, selective risk control, temporal validity, and report-wide evaluation, but no admitted study validates the full joint evaluation scheme named by the gap.",
   "evidence": [
    "2405.00982",
    "2509.26184",
    "2510.07238",
    "2606.29054",
    "2607.19322"
   ]
  },
  {
   "id": "gap-2",
   "status": "open",
   "note": "No admitted paper directly evaluates the stated private workplace email or Teams-style target domain with the full set of revisions, quoted history, conflicting updates, delayed arrival, attachment versioning, and permission constraints.",
   "evidence": []
  },
  {
   "id": "gap-4",
   "status": "open",
   "note": "The corpus separately covers compound-claim decomposition, partial support, minimal sufficient evidence, multi-source retrieval, and temporal evidence validity, but no admitted method jointly handles all of these evidence-completeness conditions.",
   "evidence": [
    "2305.11859",
    "2404.15588",
    "2508.20867",
    "doi-10-18653-v1-2025-acl-long-837",
    "doi-10-1109-access-2026-3679691"
   ]
  },
  {
   "id": "gap-5",
   "status": "open",
   "note": "Update summarization, report evaluation, real-time summarization, and factual-completeness benchmarks measure omission, novelty, redundancy, or temporal update coverage, but none directly evaluates evolving workplace work-item states, due obligations, or supersession chains.",
   "evidence": [
    "2405.00982",
    "2607.19322",
    "doi-10-1155-2016-1340973",
    "doi-10-6028-nist-sp-500-321-realtime-overview",
    "manual-39435af3dd"
   ]
  },
  {
   "id": "gap-6",
   "status": "open",
   "note": "The corpus supplies methods for active human sampling, LLM-assisted estimation, agreement measurement, reproducibility, and rating indeterminacy, but it does not determine the target-domain review volume, adjudication protocol, risk strata, or acceptance procedure.",
   "evidence": [
    "2406.07967",
    "2605.16354",
    "2606.00093",
    "manual-32d5793dca",
    "manual-f5ce52cae2"
   ]
  },
  {
   "id": "gap-7",
   "status": "open",
   "note": "Metric optimization effects, judge bias, abstention sensitivity, and rating indeterminacy are documented, but no admitted study supplies a project-specific evaluator-separation and holdout procedure for this system.",
   "evidence": [
    "2212.08037",
    "2606.00093",
    "2607.08700",
    "manual-32d5793dca"
   ]
  },
  {
   "id": "gap-8",
   "status": "open",
   "note": "Adaptive and strongly adaptive conformal methods now provide substantial evidence for non-stationary prediction, while structured-generation experiments document failure modes under cross-dataset shift. No admitted study validates one selective-prediction method on continuously changing free-form workplace communication.",
   "evidence": [
    "2106.00170",
    "2208.08401",
    "2302.07869",
    "2602.16537",
    "2606.29054"
   ]
  }
 ]
}

Per-paper analyses (reduced to questions and top findings to fit the size cap):
[
 {
  "paper_id": "1707.05555",
  "title": "Runtime Verification of Temporal Properties over Out-of-order Data Streams",
  "research_question": "How can a runtime monitor soundly and completely evaluate data-aware real-time temporal properties when observations may be delayed, lost, incomplete, or received out of order?",
  "key_findings": [
   "The proposed three-valued semantics is monotonic under refinement of observations, so filling a knowledge gap cannot invalidate a previously established Boolean verdict.",
   "The monitoring algorithm is sound and observationally complete for the proposed semantics while making no assumption that event messages arrive in timestamp order.",
   "The general decision problem for evaluating an MTL-with-freeze formula over an observation is PSPACE-complete.",
   "The prototype can process event streams at rates of hundreds of events per second even when messages arrive out of order, but it does not scale to systems producing thousands or millions of events per second.",
   "MONPOLY was up to three orders of magnitude faster on overlapping policies, but that comparison favors a mature optimized tool that requires in-order input and delays some bounded-future verdicts, whereas the proposed prototype supports out-of-order observations and prompt verdicts."
  ]
 },
 {
  "paper_id": "1910.12840",
  "title": "Evaluating the Factual Consistency of Abstractive Text Summarization",
  "research_question": "Can factual inconsistencies in abstractive summaries be detected and localized using weak supervision generated from synthetic transformations rather than requiring a large manually labeled training set?",
  "key_findings": [
   "FactCC substantially outperformed the evaluated BERT models trained on MNLI or FEVER, reaching 74.15 class-balanced accuracy and 0.5106 F1 on the manually annotated test set.",
   "Training from synthetic perturbations can transfer to factual errors produced by multiple abstractive summarization systems despite not requiring those system outputs as the main training supervision.",
   "Checking a summary sentence against the whole source document addresses cases for which sentence-to-sentence comparison lacks enough context.",
   "FactCC's source and claim span predictions provide useful evidence localization in addition to a binary consistency decision.",
   "Providing model-generated evidence highlights reduced mean human annotation time from 224.89 seconds to 178.34 seconds and increased Fleiss' kappa from 0.1571 to 0.2526 in the reported study."
  ]
 },
 {
  "paper_id": "2004.14974",
  "title": "Fact or Fiction: Verifying Scientific Claims",
  "research_question": "How can a system retrieve scientific evidence, identify the exact rationale sentences supporting a decision, and determine whether an individual scientific source supports or refutes a claim?",
  "key_findings": [
   "SciFact links claim-verification decisions to minimal sentence-level rationales, enabling evaluation of whether the predicted verdict is supported by identifiable source evidence.",
   "Training on in-domain SciFact data substantially improves evidence selection and end-to-end verification compared with zero-shot transfer from general fact-checking datasets.",
   "In the open-retrieval setting, VeriSci reaches 39.5 sentence-level Selection+Label F1 and 46.5 abstract-level Label+Rationale F1, leaving large room for improvement.",
   "Oracle experiments show that both document retrieval and rationale selection make substantial contributions to total verification error.",
   "Independent re-annotation yields Cohen's kappa of 0.75 for claim-abstract labels and 0.71 for sentence-level rationale membership."
  ]
 },
 {
  "paper_id": "2006.09462",
  "title": "Selective Question Answering under Domain Shift",
  "research_question": "Can selective question answering remain reliable under an unknown domain shift by learning a confidence calibrator from source-domain examples and examples from a different known out-of-domain dataset?",
  "key_findings": [
   "Training the calibrator with source and known out-of-domain data raised average coverage at 80% target accuracy to about 56.1%, compared with 48.2% for maximum softmax probability.",
   "Using known out-of-domain data to train the confidence calibrator was more effective for selective QA than merely retraining the QA model with that data, reaching about 56.1% versus 51.8% coverage at 80% target accuracy.",
   "A calibrator trained on both source and known out-of-domain examples also outperformed a source-only calibrator at the same target accuracy, demonstrating transfer of calibration information across domains.",
   "Adding test-time dropout-derived features improved the calibrator further, reaching about 60.0% coverage at 80% target accuracy, but required repeated inference passes.",
   "Maximum softmax probability is systematically overconfident on shifted domains, whereas the learned calibrator narrows the confidence-quality gap between source and out-of-domain examples."
  ]
 },
 {
  "paper_id": "2012.14983",
  "title": "Reducing Conversational Agents’ Overconfidence Through Linguistic Calibration",
  "research_question": "Can an open-domain dialogue model's verbalized confidence be aligned with its probability of being factually correct by predicting correctness from model signals and controlling generation style?",
  "key_findings": [
   "The vanilla chatbot is strongly overconfident: it has 4.8% overall factual accuracy, answers 29.45% of questions with high linguistic confidence, and only about 14% of those confident answers are correct.",
   "The selected correctness calibrator achieves a reported 20-bin ECE of 0.018, MCE of 0.292, and average negative log-likelihood of 0.165.",
   "The controllable generator reliably changes expressed confidence: 96.27% of high-confidence-forced generations are judged high confidence, while 98.79% and 99.12% of the two lower-confidence settings are judged not high confidence.",
   "Among answers judged linguistically confident, factual correctness rises from 13.7% for the vanilla chatbot to 38.9% for the calibrator-controlled chatbot, with p less than 10^-6 under a paired permutation test.",
   "The improvement comes primarily from using confident language more selectively rather than materially improving factual accuracy; total accuracy changes from 4.8% to 5.1% and the difference is not statistically significant."
  ]
 },
 {
  "paper_id": "2105.00071",
  "title": "Evaluating Attribution in Dialogue Systems: The BEGIN Benchmark",
  "research_question": "How reliably do existing automatic metrics identify whether knowledge-grounded dialogue responses are actually attributable to the supplied evidence, including under challenging forms of distribution shift?",
  "key_findings": [
   "Existing automatic metrics do not reliably separate attributable abstractive responses from unattributable responses.",
   "All evaluated metric families exhibit a strong dependence on lexical overlap or extractivity rather than a robust semantic understanding of attribution.",
   "Unattributable but highly extractive responses can receive higher scores than attributable responses expressed through abstraction or paraphrase.",
   "Metrics perform substantially worse when the grounding knowledge source is longer, demonstrating a concrete distribution-shift and robustness failure.",
   "Training on the paper's adversarial attribution data provides stronger supervision than the tested NLI-style datasets for the BEGIN taxonomy, but classifier performance remains far below human annotation quality."
  ]
 },
 {
  "paper_id": "2106.00170",
  "title": "Adaptive Conformal Inference Under Distribution Shift",
  "research_question": "Can conformal prediction be adapted online to retain a target long-run coverage frequency when the data distribution changes unpredictably over time without relying on exchangeability?",
  "key_findings": [
   "The adaptive update has a distribution-free long-run guarantee: the time-average error rate converges almost surely to the target miscoverage level, with a finite-time deviation bound proportional to 1 divided by T times the step size.",
   "Adaptation speed and stability are controlled by the step size, creating a trade-off between rapidly tracking distribution changes and producing more volatile parameter updates.",
   "In the election-night experiment, fixed conformal inference suffered large local-coverage troughs around time-zone changes, whereas adaptive conformal inference maintained approximately 90% local coverage across the sequence.",
   "Coverage behavior depends strongly on the conformity score: an unnormalized volatility score produced substantially wider deviations from the 90% coverage target than the normalized score.",
   "The strongest general guarantee concerns long-run average coverage rather than uniform finite-window conditional coverage during every local distribution shift."
  ]
 },
 {
  "paper_id": "2111.09525",
  "title": "SummaC: Re-Visiting NLI-based Models for Inconsistency Detection in Summarization",
  "research_question": "Can natural-language-inference models reliably detect factual inconsistency in summaries if the granularity mismatch between sentence-level NLI training and document-level summarization evaluation is explicitly addressed?",
  "key_findings": [
   "Using sentence-level or similarly fine-grained NLI comparisons substantially improves inconsistency detection compared with applying NLI directly to full documents and summaries.",
   "SummaC-Conv achieved 74.4 percent average balanced accuracy on the six-dataset SummaC Benchmark, approximately five absolute points above the strongest reported non-NLI baseline.",
   "Overall improvements of both SummaC variants over prior work were statistically significant under the paper's bootstrap testing procedure, with the stronger significance level reported for SummaC-Conv.",
   "Using the full distribution of sentence-level entailment scores in SummaC-Conv is more robust than relying only on each summary sentence's single maximum entailment score.",
   "NLI architecture and training data materially affect factual-consistency performance, with Transformer-based models and domain-relevant NLI data outperforming the older decomposable-attention setup used in earlier negative results."
  ]
 },
 {
  "paper_id": "2204.02007",
  "title": "Fact Checking with Insufficient Evidence",
  "research_question": "Can fact-checking systems learn to abstain with an insufficient-evidence decision when the available evidence has been partially removed or is otherwise inadequate to determine a claim's truth?",
  "key_findings": [
   "When all three baseline models agree that the remaining evidence is sufficient, human annotators still label 430 of 1000 examined cases as insufficient, showing a substantial false-sufficiency problem.",
   "When all three baseline models agree that evidence is insufficient, their consensus matches the human insufficiency judgment in 972 of 1000 examined cases.",
   "Sensitivity to evidence omission depends strongly on what is removed: adverbial modifiers are among the hardest omissions for the models, while date-related omissions are substantially easier.",
   "Omission-driven counterfactual and contrastive training improves performance on the SufficientFacts diagnostic set, with Section 6.2 reporting gains of up to 17.2 F1 points.",
   "The same training approaches can preserve or improve ordinary fact-checking performance, with Section 6.2 reporting gains of up to 3.6 F1 points on the original test sets."
  ]
 },
 {
  "paper_id": "2208.02814",
  "title": "Conformal Risk Control",
  "research_question": "Can conformal prediction be generalized from miscoverage control to finite-sample control of the expected value of a broad class of bounded monotone losses?",
  "key_findings": [
   "For exchangeable examples and bounded, right-continuous, non-increasing loss functions, the proposed calibration rule controls the expected test loss at the target level in finite samples.",
   "Ordinary split conformal prediction is recovered as a special case when the loss is the indicator of prediction-set miscoverage.",
   "Under additional regularity assumptions, the attainable expected risk is within order 1/n of the requested risk level, although the authors note that the constant in their lower bound may not be tight.",
   "Across the four empirical application domains, average held-out risk was close to the requested risk level over repeated calibration/test splits.",
   "The basic conformal-risk-control rule does not provide a general finite-sample guarantee for arbitrary non-monotone losses; the paper gives examples where it can fail badly."
  ]
 },
 {
  "paper_id": "2208.08401",
  "title": "Conformal Inference for Online Prediction with Arbitrary Distribution Shifts",
  "research_question": "How can online conformal prediction adapt its calibration rate to distribution shifts of unknown and changing magnitude while retaining meaningful local coverage guarantees?",
  "key_findings": [
   "The dynamically tuned method obtains local dynamic-regret guarantees that adapt to temporal variation in the optimal calibration level rather than requiring a fixed known shift magnitude.",
   "Under a lower-density condition and a smooth relationship between the calibration level and coverage, the regret bounds imply control of average local coverage error.",
   "Relative to earlier ACI analyses, the method does not require prior knowledge of the size of the distribution shift and permits the conformity score or underlying predictive model to evolve.",
   "In abrupt-shift simulations, dynamic tuning adjusts more effectively to changes in shift magnitude than a method whose aggregation weights adapt more slowly.",
   "In stock-volatility experiments, local coverage-gap behavior is reported as close to the variability expected from correctly calibrated Bernoulli coverage indicators."
  ]
 },
 {
  "paper_id": "2212.08037",
  "title": "Attributed Question Answering: Evaluation and Modeling for Attributed Large Language Models",
  "research_question": "How should attributed question answering be evaluated, how well can automatic attribution metrics reproduce human judgments, and which modeling approaches produce answers that are supported by their cited sources?",
  "key_findings": [
   "Human AIS explicitly requires the answer's information to be interpretable and fully supported by the attributed passage, making source support a separate evaluation target from ordinary answer exact match.",
   "The strongest reported retrieve-then-read configuration reached 65.5 AIS before attribution reranking, while AutoAIS reranking raised human AIS to 71.4 in the summarized architecture comparison.",
   "Exact-match answer quality and attribution quality were only moderately aligned at the system level, with a reported Pearson correlation of 0.45 between EM and AIS.",
   "AutoAIS correlated strongly with human AIS at the system level, with Pearson correlation 0.96, but agreement was substantially weaker and more variable at the individual-question level.",
   "Using AutoAIS itself to select attribution passages created outlier systems whose human attribution ratings were lower than their automatic scores would suggest, showing that an evaluation metric can become unreliable when directly optimized as a system component."
  ]
 },
 {
  "paper_id": "2302.07869",
  "title": "Improved Online Conformal Prediction via Strongly Adaptive Online Learning",
  "research_question": "Can online conformal prediction be made strongly adaptive so that prediction sets maintain useful coverage and efficiency across localized time intervals under changing or arbitrarily shifting data distributions?",
  "key_findings": [
   "SAOCP achieves strongly adaptive regret of order approximately sqrt(k) up to logarithmic factors simultaneously for every interval length k, whereas the compared FACI guarantee can be tuned to a comparable rate for a particular interval length but not all lengths simultaneously.",
   "SF-OGD has a distribution-free empirical coverage-error bound that converges to zero, while SAOCP receives a distribution-free bound for a randomized expert-selection variant and stronger interval-wise coverage guarantees under additional distributional regularity assumptions.",
   "Across the three M4 forecasting datasets, SAOCP maintained global coverage near the 0.9 target and consistently obtained the best or second-best interval width, local coverage error, and strongly adaptive regret across the tested base predictors.",
   "Under sudden and gradual image-distribution shifts, SAOCP and SF-OGD kept local coverage closest to the 0.9 target, with the advantage most pronounced around abrupt change points.",
   "Directly predicting the conformal radius, as done by SF-OGD and SAOCP, was empirically more robust than quantile-style parameterizations in several cases where the underlying forecasting model had relatively high prediction error."
  ]
 },
 {
  "paper_id": "2305.11859",
  "title": "Complex Claim Verification with Evidence Retrieved in the Wild",
  "research_question": "How effectively can a fully automated system verify complex real-world claims using only web evidence that was available when the claim was made, rather than curated or future fact-checking evidence?",
  "key_findings": [
   "Under the realistic before-claim and non-fact-checking-site constraints, retrieval plus summarization improved test accuracy from 25.5% for the claim-only baseline to 33.0%, with corresponding improvements on several other veracity metrics.",
   "Removing temporal or site constraints substantially improves apparent fact-checking performance, indicating that unconstrained search often benefits from later fact-check articles rather than contemporaneous raw evidence.",
   "Searching with generated subquestions performs markedly better than searching with the original compound claim, showing that decomposition helps retrieve evidence for multiple aspects of a complex claim.",
   "Few-shot claim-focused summaries were rated fully faithful in 82.5% of 200 evaluated document-summary pairs, compared with 66.0% for the zero-shot text-davinci-003 summaries.",
   "Evidence completeness remains a major bottleneck: for few-shot summaries, 42.9% of evaluated subquestions were answerable, 21.1% partially answerable, and 36.0% unanswerable."
  ]
 },
 {
  "paper_id": "2305.14627",
  "title": "Enabling Large Language Models to Generate Text with Citations",
  "research_question": "How can retrieval-augmented language models generate useful long-form answers with citations, and how can citation completeness and correctness be evaluated automatically and against human judgments?",
  "key_findings": [
   "Separating answer correctness from citation recall and citation precision exposes systems that produce plausible or correct text without adequate evidence attribution.",
   "Current tested systems leave substantial portions of generated content unsupported by their citations; on ELI5, even strong baselines had citation recall around one half rather than complete support.",
   "Simple retrieval followed by placing the retrieved passages directly in the LLM context was competitive with more elaborate interaction strategies.",
   "Reranking multiple generated answers using automated citation recall consistently improved citation quality in the tested ASQA and ELI5 settings.",
   "Retrieval quality strongly constrains answer correctness and citation quality, but even oracle-like access to relevant evidence does not guarantee that an LLM will successfully use that evidence."
  ]
 },
 {
  "paper_id": "2307.09254",
  "title": "Selective Generation for Controllable Language Models",
  "research_question": "Can selective generation for free-form language models obtain statistical control over semantically incorrect accepted answers by defining correctness through textual entailment and calibrating when the model should abstain?",
  "key_findings": [
   "The paper provides a PAC-style theoretical guarantee that the learned selective generator's entailment-based false discovery rate is upper bounded with user-specified confidence under the stated assumptions.",
   "In the reported experiments, SGen-Semi generally controlled the requested FDR-E while obtaining higher average selection efficiency than the compared certified and heuristic semi-supervised alternatives.",
   "With only 75% of the labeled calibration examples used by fully supervised methods, SGen-Semi achieved selection efficiencies of 0.7334 for GPT-3.5-Turbo and 0.3173 for Alpaca-7B in the reported comparison.",
   "Adding more unlabeled examples increased selective-generation efficiency in the reported experiments.",
   "Textual entailment provides a more suitable semantic correctness criterion for free-form answers than exact match, which can reject semantically equivalent valid responses."
  ]
 },
 {
  "paper_id": "2312.09300",
  "title": "Self-Evaluation Improves Selective Generation in Large Language Models",
  "research_question": "Can an LLM's token-level self-evaluation of its own free-form answers provide better confidence signals for selective generation and abstention than ordinary sequence likelihood?",
  "key_findings": [
   "Raw sequence likelihood was a poor confidence signal for free-form generation and was negatively correlated with correctness on TruthfulQA in several settings.",
   "Recasting answer assessment as token-level self-evaluation substantially improved confidence-quality ranking compared with sequence likelihood.",
   "On PaLM-2 TruthfulQA, the hybrid method with a 'None of the above' option achieved a Calibration-AUC of 75.34 compared with 39.80 for raw sequence likelihood.",
   "Allowing 'None of the above' gave the model an explicit signal for cases in which none of the sampled answers appeared correct and generally improved calibration without a large accuracy penalty.",
   "The advantage of self-evaluation over sequence-level confidence also appeared on TL;DR summarization, although the improvements were smaller than on TruthfulQA."
  ]
 },
 {
  "paper_id": "2402.05629",
  "title": "Merging Facts, Crafting Fallacies: Evaluating the Contradictory Nature of Aggregated Factual Claims in Long-Form Generations",
  "research_question": "Can a long-form response be globally misleading even when its individual atomic claims are independently verifiable, and how should factuality metrics detect this failure under entity ambiguity?",
  "key_findings": [
   "Independent verification of atomic claims can substantially overestimate paragraph-level factuality when true facts about multiple entities are merged into a narrative that appears to describe one entity.",
   "Human D-FActScore is 8 to 16 percentage points lower than FActScore for the tested Llama and Tulu generations, exposing entity-mixing errors hidden by independent claim verification.",
   "FActScore and D-FActScore can reverse the relative ordering of systems because copying individually supportable sentences does not guarantee correct entity-level aggregation.",
   "The automatic D-FActScore pipeline reproduces the same model ordering as human evaluation and has an overall per-paragraph Pearson correlation of 0.75 with human D-FActScore.",
   "Providing demonstrations containing ambiguous names does not improve D-FActScore relative to demonstrations without ambiguity in the reported experiments."
  ]
 },
 {
  "paper_id": "2404.00474",
  "title": "Linguistic Calibration of Long-Form Generations",
  "research_question": "Can long-form language-model generations be trained to communicate uncertainty such that downstream users form calibrated probabilistic forecasts, including under substantial domain and task shifts?",
  "key_findings": [
   "Decision-based linguistic-calibration training substantially improves reader calibration relative to factuality-focused Llama 2 baselines while preserving comparable or better answer accuracy.",
   "The reinforcement-learning variant maintains improved calibration under distribution shifts to Jeopardy, scientific QA, and biomedical QA rather than only on the training-domain task.",
   "Calibration transfers zero-shot to a held-out biography-generation task, where claim-level evaluation shows improved calibration relative to non-confidence Llama-based methods.",
   "A scalable simulated-reader evaluation tracks the intended downstream forecasting behavior sufficiently well to be validated against crowdworker evaluation.",
   "The paper provides a decision-theoretic argument that appropriately calibrated downstream forecasts support informed decision making and connects weaker calibration notions to weaker decision guarantees."
  ]
 },
 {
  "paper_id": "2404.15588",
  "title": "Minimal Evidence Group Identification for Claim Verification",
  "research_question": "Can claim-verification systems identify the smallest non-redundant set of evidence passages that is collectively sufficient to support a claim instead of retrieving a redundant union of all relevant evidence?",
  "key_findings": [
   "The proposed bottom-up MEG method substantially improves precision and F0.5 over direct LLM prediction and classic evidence-selection baselines on both WiCE-MEG and SciFact-MEG.",
   "On WiCE-MEG, the proposed method reaches 0.809 soft-match precision and 0.684 F0.5, compared with 0.176 precision and 0.203 F0.5 for direct LLM prediction.",
   "On SciFact-MEG, the proposed method reaches 0.612 soft-match precision and 0.533 F0.5, outperforming the reported direct and classic baselines on those precision-oriented measures.",
   "The precision gains come with lower recall than several baselines, illustrating that selecting minimal sufficient evidence and exhaustively recovering all annotated evidence groups are different objectives.",
   "Minimal evidence groups dramatically reduce evidence volume in the downstream claim-generation experiment while preserving performance close to much larger evidence sets under comparable computation budgets."
  ]
 },
 {
  "paper_id": "2405.00982",
  "title": "On the Evaluation of Machine-Generated Reports",
  "research_question": "How can long-form machine-generated reports for complex information needs be evaluated jointly for completeness, factual support, citation correctness, responsiveness, and reuse across future systems?",
  "key_findings": [
   "ARGUE operationalizes report completeness as recall over assessor-defined information nuggets, with a nugget counted as covered only when the report states it with the required supporting citation evidence.",
   "The framework separately evaluates segment-level precision, allowing unsupported citations, missing required citations, and unattested claims to be penalized while avoiding conflation with missing-content errors.",
   "Repeated support for the same information nugget counts only once toward recall, giving the framework an explicit mechanism for separating coverage from repetition.",
   "Report requests can encode user background, required content, known background information, length constraints, and temporal source windows, making the intended information need substantially richer than a conventional short retrieval query.",
   "The framework explicitly permits a nugget representing a requested fact that is absent from the collection, allowing evaluation of whether the report correctly states that requested evidence is unavailable."
  ]
 },
 {
  "paper_id": "2406.07967",
  "title": "Better than Random: Reliable NLG Human Evaluation with Constrained Active Sampling",
  "research_question": "Can a constrained active sampling procedure select a limited human-evaluation subset that preserves full-dataset NLG system rankings more reliably than random or heuristic sampling?",
  "key_findings": [
   "Repeated random sampling can produce materially different inter-system rankings, with 87.5% of examined datasets showing different rankings across five random samples.",
   "At the main 50% sampling setting, CASF achieved an overall inter-system ranking Kendall correlation of 0.83, exceeding the reported aggregate performance of the comparison methods.",
   "CASF ranked first on 79.55% of the 44 human-evaluation metrics and first or second on 90.91% of them.",
   "CASF identified the full-dataset top-ranked system correctly for 93.18% of the 44 human-evaluation metrics.",
   "Wilcoxon signed-rank comparisons reported statistically better ranking performance for CASF than random and heuristic sampling."
  ]
 },
 {
  "paper_id": "2408.08067",
  "title": "RAGChecker: A Fine-grained Framework for Diagnosing Retrieval-Augmented Generation",
  "research_question": "Can claim-level entailment metrics jointly diagnose retrieval completeness, generation correctness, evidence use, and error sources in long-form retrieval-augmented generation better than coarse response-level evaluation?",
  "key_findings": [
   "For overall human assessment, RAGChecker achieved Pearson and Spearman correlations of 61.93 and 60.90, compared with 48.31 and 57.23 for the strongest displayed RAGAS Answer Similarity baseline.",
   "RAGChecker had the highest displayed completeness Pearson correlation at 60.67, although RAGAS Answer Similarity had a higher completeness Spearman correlation of 61.35 versus RAGChecker's 58.11, so the table does not support dominance on every individual correlation statistic.",
   "Replacing BM25 with E5-Mistral improved overall RAG performance for every fixed generator in the eight-system comparison, supporting the conclusion that retrieval quality consistently affects downstream answer quality.",
   "With either retriever fixed, Llama3-70B outperformed Llama3-8B in overall F1 and showed better generator diagnostics, including lower hallucination and higher faithfulness.",
   "The diagnostic decomposition directly measures omission-like behavior through ground-truth claim recall and context utilization while separating unsupported generated material into retrieved-noise and hallucination categories."
  ]
 },
 {
  "paper_id": "2410.14964",
  "title": "ChronoFact: Timeline-based Temporal Fact Verification",
  "research_question": "Can explicitly modeling the chronological relationships among multiple claim and evidence events improve verification of complex temporal claims?",
  "key_findings": [
   "ChronoFact achieves 85.49 macro F1 on ChronoClaims, substantially exceeding the compared baselines, whose best reported macro F1 is 63.42.",
   "ChronoFact remains comparatively strong as claims contain more events and when events overlap or recur.",
   "ChronoFact also reports the strongest performance among the compared systems on T-FEVER, T-FEVEROUS, and the real-world T-QuanTemp subset.",
   "Removing the chronological-order classifier causes the largest macro-F1 degradation on ChronoClaims, supporting the value of explicit sequence verification.",
   "In a manual analysis of 50 incorrect ChronoClaims predictions, 82% of errors involve implicit temporal information and the remaining 18% involve events with multiple dates or varying temporal granularity."
  ]
 },
 {
  "paper_id": "2505.23912",
  "title": "LoVeC: Reinforcement Learning for Better Verbalized Confidence in Long-Form Generation",
  "research_question": "Can reinforcement learning teach language models to emit sentence-level numerical confidence during long-form generation that is better calibrated to factual correctness and more efficient than post-hoc sampling methods?",
  "key_findings": [
   "RL-trained LoVeC models consistently improved sentence-level confidence calibration over prompting, SFT, self-consistency, and the LUQ baseline across the reported long-form datasets.",
   "For Llama-3 iterative tagging on WildHallu, LoVeC-GRPO reached a Brier Score of 5.7, ECE-M of 2.5, and Spearman correlation of 57.0, improving substantially over the SFT initialization.",
   "Calibration improvements transferred from WildHallu training to the out-of-domain Bios and PopQA evaluations.",
   "Inline confidence prediction was reported to process the WildHallu test set about 20 times faster than the sampling-based LUQ method in the stated Gemma-2-9B single-A100 comparison.",
   "The RL objective can improve calibration without requiring the model to avoid every hallucination, because hallucinated statements are acceptable to the objective if they receive appropriately low confidence."
  ]
 },
 {
  "paper_id": "2508.20867",
  "title": "MSRS: Evaluating Multi-Source Retrieval-Augmented Generation",
  "research_question": "How should RAG systems be evaluated when answering a query requires retrieving complementary information from multiple documents and synthesizing it into a long-form response, and where do retrieval and generation failures arise?",
  "key_findings": [
   "Generation quality tracked retrieval quality closely; on MSRS-Story, mean G-EVAL across models increased from 40.53 with BM25 to 53.34 with gemini-embedding, compared with an oracle average of 60.90.",
   "Providing the full set of relevant documents outperformed weaker evidence conditions, supporting the benchmark's intended requirement for multi-document evidence aggregation.",
   "Even with oracle retrieval, top non-reasoning systems omitted multiple minor details in 40% of evaluated MSRS-Story summaries and 60% of MSRS-Meet summaries, while MSRS-Meet summaries missed multiple major details 35% of the time.",
   "Reasoning models improved oracle-setting G-EVAL over the strongest non-reasoning baselines by as much as 11.22 points on MSRS-Story and 7.11 points on MSRS-Meet; GPT-5 reached G-EVAL 81.07 and 60.78 respectively.",
   "For Gemini 2.5 Pro, feeding a very long document context did not eliminate the value of retrieval: on MSRS-Story, G-EVAL was 61.30 for long context, 70.63 with the strong retriever, and 76.66 with oracle evidence."
  ]
 },
 {
  "paper_id": "2509.26184",
  "title": "Auto-ARGUE: LLM-Based Report Generation Evaluation",
  "research_question": "Can the ARGUE framework for evaluating long-form citation-backed reports be automated with an LLM judge while retaining useful agreement with human judgments of coverage and citation support?",
  "key_findings": [
   "Auto-ARGUE produced system-level rankings that agreed well with human ARGUE judgments on the TREC NeuCLIR report-generation pilot, with especially strong agreement for sentence precision.",
   "On TREC RAG 2024, Auto-ARGUE nugget recall correlated moderately to strongly with AutoNuggetizer's human-grounded nugget-support evaluation, with Spearman correlations of 0.81-0.86 and Kendall correlations of 0.65-0.72.",
   "The framework directly operationalizes evidence completeness as nugget recall rather than treating factual correctness alone as sufficient report quality.",
   "ARGUE explicitly represents justified abstention-like behavior through negative assertions, rewarding claims of unavailable information only when the corresponding nugget truly has no answer.",
   "The paper's NeuCLIR validation did not test negative-assertion judgments because every NeuCLIR nugget was answerable."
  ]
 },
 {
  "paper_id": "2510.07238",
  "title": "When Benchmarks Age: Temporal Misalignment through Large Language Model Factuality Evaluation",
  "research_question": "How much do static factuality benchmarks become temporally misaligned with current real-world facts, and how does that aging distort evaluations of modern LLM factuality?",
  "key_findings": [
   "Among time-sensitive questions, Dataset Drift Scores range from 24.19% to 63.78% across the five investigated benchmarks, except that the paper separately notes TriviaQA has relatively few time-sensitive questions overall.",
   "More than half of the reported model-benchmark combinations have an Evaluation Misleading Rate above 10%, meaning current answers can be scored as wrong because benchmark labels are stale.",
   "Seventy percent of Temporal Alignment Gap measurements are positive, indicating that model outputs more often align better with current web-derived facts than with benchmark gold answers.",
   "Supplying outdated BoolQ passages can pull models toward obsolete benchmark information even when their unaided responses better reflect current facts.",
   "The web-search pipeline was judged correct on 89.52% of a 105-question human-evaluated sample, with Cohen's kappa of 0.58."
  ]
 },
 {
  "paper_id": "2510.12839",
  "title": "FaStfact: Faster, Stronger Long-Form Factuality Evaluations in LLMs",
  "research_question": "Can long-form LLM factuality evaluation be made substantially more efficient while improving alignment with human judgments about claim coverage and factual correctness?",
  "key_findings": [
   "FaStfact produced the closest end-to-end factuality score to human ground truth among the compared pipelines: F1@K' was 0.780 versus a ground-truth value of 0.792, an absolute gap of 0.012.",
   "Its extracted claim counts were substantially closer to human annotations than the compared baselines, with an average absolute claim-count difference of 3.35.",
   "FaStfact claim verification agreed exactly with human labels on 85.3% of annotations and agreed on the coarser supported, non-supported, or irrelevant type on 92.9%.",
   "Longer extraction chunks did not degrade claim-count alignment in the ablation; strides from 28 sentences through the entire response aligned most closely with human claim counts while also reducing extraction cost.",
   "FaStfact used 5,615 tokens per sample in the baseline comparison, fewer than ExpertQA, VeriScore, and SAFE but more than FacTool's 4,480 tokens, so its advantage is a combined alignment-efficiency result rather than the lowest token count in isolation."
  ]
 },
 {
  "paper_id": "2511.01101",
  "title": "TSVer: A Benchmark for Fact Verification Against Time-Series Evidence",
  "research_question": "How can fact-verification systems be rigorously evaluated on real-world claims that require numerical and temporal reasoning over structured time-series evidence, including whether the correct evidence and time ranges were retrieved and whether generated justifications cover the relevant facts?",
  "key_findings": [
   "TSVer annotates both which time series are relevant and which temporal ranges within them matter, enabling retrieval evaluation that penalizes both omitted evidence and unnecessary over-retrieval.",
   "The Time Series Coverage Score jointly combines dataset-level F1 with temporal Jaccard overlap, explicitly measuring whether systems select the correct evidence sources and the correct time spans.",
   "The adapted Ev2R justification metric decomposes predicted and reference explanations into atomic facts and measures both precision and recall, directly exposing unsupported generated facts and omitted reference facts.",
   "On the reported test set, Gemini-2.5-Pro achieved 63.57% verdict accuracy, TSCS 27.87, and Ev2R 47.36, showing that even a strong long-context reasoning model has substantial room for improvement on temporal evidence selection and explanation.",
   "GPT-5.2 achieved 62.86% verdict accuracy, TSCS 25.83, and Ev2R 46.51, with performance close to Gemini but still far from complete retrieval or justification agreement."
  ]
 },
 {
  "paper_id": "2511.16198",
  "title": "SemanticCite: Citation Verification with AI-Powered Full-Text Analysis and Evidence-Based Reasoning",
  "research_question": "Can full-text retrieval and multi-class evidence reasoning provide scalable, interpretable verification of whether scholarly citations actually support the claims attributed to them?",
  "key_findings": [
   "The 4B model achieved 66.36% standard accuracy and 83.64% weighted accuracy, while the 8B model achieved 66.07% and 83.93%, respectively, showing that many errors were close to the correct category in the ordinal four-class scheme.",
   "All three fine-tuned models generated valid preprocessing outputs for all 112 test examples and exceeded 93% character similarity to preprocessing references.",
   "The 4B model provided the strongest reported balance of classification and generated-output behavior, with 90.01% character similarity and a mean output-length difference of minus 0.7 words while remaining close to the 8B model in weighted accuracy.",
   "The four-class scheme explicitly distinguishes complete support from support that omits qualifications or context and provides an Uncertain state instead of forcing ambiguous evidence into a binary decision.",
   "The paper reports that untuned base Qwen3 models performed substantially worse, produced poorly calibrated output lengths, and frequently failed to satisfy the required structured JSON format, supporting the value of task-specific fine-tuning."
  ]
 },
 {
  "paper_id": "2512.17776",
  "title": "DEER: A Benchmark for Evaluating Deep Research Agents on Expert Report Generation",
  "research_question": "Can expert-derived omission-sensitive rubrics and report-wide evidence verification provide a reliable, diagnostic evaluation of the completeness, analytical quality, and grounding of deep-research reports?",
  "key_findings": [
   "DEER separates omission from execution quality through 101 rubric items comprising 66 Coverage items and 35 Quality items; Coverage explicitly checks whether required content is present without omission.",
   "Baseline systems generally scored better on structural coherence, formatting, ethics, and information-use dimensions than on request fulfillment and analytical soundness, exposing a gap between plausible report form and expert-level task completion.",
   "Search and deep-research modes can improve information-related dimensions without guaranteeing better overall report reasoning or request fulfillment, so evidence acquisition alone is not sufficient for expert-quality synthesis.",
   "Adding task-specific Expert Evaluation Guidance produced the strongest agreement with human experts among the evaluated judging configurations, with average Pearson correlation 0.73, Spearman correlation 0.71, and pairwise agreement 0.84.",
   "Expert Guidance also increased agreement among different LLM judges to Krippendorff's alpha 0.55, ICC(2,1) 0.56, and ICC(2,k) 0.87."
  ]
 },
 {
  "paper_id": "2602.11908",
  "title": "When Should LLMs Be Less Specific? Selective Abstraction for Reliable Long-Form Text Generation",
  "research_question": "Can an LLM selectively replace uncertain atomic claims with less specific statements, rather than deleting them outright, to obtain a better calibrated trade-off between factual risk and retained information in long-form generation?",
  "key_findings": [
   "Atom-wise selective abstraction reduced average AURC relative to claim redaction by 17.43% on FactScore and 13.77% on LongFact-Objects across the six evaluated models.",
   "The largest reported gain occurred for gpt-oss-120b, with AURC improvements of 27.73% on FactScore and 21.02% on LongFact-Objects relative to redaction.",
   "At matched coverage, atom-wise abstraction generally produced substantially less factual risk than the Inline Abstraction and Self-Revision baselines, with the paper describing the average advantage as about ten percentage points.",
   "The Wikipedia-based correctness agent was checked against human judgments on 102 sampled claims and achieved an overall F1 of 0.93.",
   "The calibration procedure selected thresholds whose empirical risks stayed close to specified target risks across 600 repeated runs per dataset, although variability remained because the calibration and test samples were small."
  ]
 },
 {
  "paper_id": "2602.16537",
  "title": "Optimal training-conditional regret for online conformal prediction",
  "research_question": "How can online conformal prediction maintain strong training-conditional coverage guarantees under unknown abrupt or smooth distribution drift, including when prediction models themselves are updated online?",
  "key_findings": [
   "For pretrained scores, DriftOCP attains regret of order approximately sqrt((Ncp+1)T) under change points and sqrt(T) plus KS_T^(1/3)T^(2/3) under smooth score-distribution drift, up to logarithmic factors.",
   "The corresponding minimax lower bounds match the pretrained-score upper-bound dependence on the horizon and drift measures up to logarithmic factors, establishing minimax optimality within the stated admissible algorithm class.",
   "For online-trained scores under the stated Lipschitz and stability assumptions, DriftOCP-full attains regret of order approximately sqrt((Ncp+L+1)T) for change points and sqrt((L+1)T) plus TV_T^(1/3)T^(2/3) for smooth drift.",
   "The full-conformal analysis also yields a batch training-conditional coverage concentration result for stable data-dependent predictors without requiring permutation-invariant model fitting.",
   "In the pretrained-score simulations, DriftOCP remained comparatively stable in stationary segments while adapting rapidly after shifts, whereas ACI exhibited a stepsize trade-off between stable calibration and rapid reaction to drift."
  ]
 },
 {
  "paper_id": "2604.03141",
  "title": "Beyond Precision: Importance-Aware Recall for Factuality Evaluation in Long-Form LLM Generation",
  "research_question": "How can long-form LLM factuality evaluation measure not only whether generated claims are evidence-supported but also whether the response omits relevant and important facts?",
  "key_findings": [
   "Fine-grained recall exposes factual incompleteness that precision-only evaluation cannot measure, because reference facts absent from the generation are scored explicitly.",
   "The evaluated models show severe recall limitations in the biography and LongForm settings, while LongFact exhibits different precision-recall operating points and several models attain recall comparable to or above precision.",
   "Longer generation is neither necessary nor sufficient for better factuality; excessive claim production can raise recall while lowering precision.",
   "Unsupported claims are reported as more common than directly contradicted claims across the evaluated models and datasets, while biography generation has comparatively elevated contradiction rates.",
   "For very small reference-fact budgets, salience is especially useful for identifying facts models tend to cover first, whereas relevance becomes more important as broader fact coverage is considered."
  ]
 },
 {
  "paper_id": "2604.12046",
  "title": "Think Through Uncertainty: Improving Long-Form Generation Factuality via Reasoning Calibration",
  "research_question": "Can modeling and calibrating uncertainty at the atomic-claim level improve long-form factuality while preserving factual recall and enabling selective abstention?",
  "key_findings": [
   "CURE achieves the highest reported claim-level factual accuracy among the compared methods on FactBench, LongFact, and Biography, reaching 84.4, 90.2, and 65.9 respectively.",
   "Relative to the L2RF reinforcement-learning baseline, CURE improves factual accuracy by 9.4% on FactBench, 13.6% on LongFact, and 39.9% on Biography.",
   "CURE reports strong discriminative calibration, including AUROC values of 0.667 on FactBench and 0.669 on LongFact.",
   "Confidence-thresholded selective prediction provides an adjustable accuracy-recall trade-off, and the reported Pareto analysis shows viable CURE configurations dominating the base LLM and L2RF in accuracy versus factual recall.",
   "Joint GRPO optimization of factuality and calibration collapses toward overconfidence, with approximately 95% of predicted claim-confidence scores exceeding 0.9 during training."
  ]
 },
 {
  "paper_id": "2605.01749",
  "title": "Only Say What You Know: Calibration-Aware Generation for Long-Form Factuality",
  "research_question": "Can a long-form reasoning model improve factuality without resorting to coarse whole-answer abstention by estimating the reliability of intermediate reasoning and selectively committing only to sufficiently reliable content?",
  "key_findings": [
   "Calibration-Aware Generation improves long-form factuality across multiple models and benchmarks, with the paper reporting gains of up to 13 percent without a substantial loss of overall informativeness in the evaluated settings.",
   "Both calibrated exploration and selective commitment are necessary: removing either component consistently degrades performance across tested benchmarks and model sizes.",
   "Selective commitment creates an explicit factuality-versus-coverage trade-off: lower reliability thresholds retain more information but admit more hallucinations, while higher thresholds improve factuality by discarding more potentially useful content.",
   "Reliability estimates become better aligned with factual correctness than those of the corresponding vanilla models, as measured by AUC on Biography and FAVA.",
   "Benefits extend beyond the main long-form benchmarks to knowledge-intensive QA, chatbot evaluation, and retrieval-augmented generation."
  ]
 },
 {
  "paper_id": "2605.03534",
  "title": "SURE-RAG: Sufficiency and Uncertainty-Aware Evidence Verification for Selective Retrieval-Augmented Generation",
  "research_question": "Can answer-level aggregation of claim-evidence sufficiency and uncertainty support more accurate and calibrated selective RAG answering than passage-level pooling while remaining auditable?",
  "key_findings": [
   "Calibrated SURE-RAG achieved 0.9075 Macro-F1 on HotpotQA-RAG v3, compared with 0.8951 for raw SURE-RAG, 0.6516 for DeBERTa mean-pooling, and 0.8888 for the concat cross-encoder.",
   "At 30% coverage, SURE-RAG reduced unsafe-answer risk to 0.1642 versus 0.2588 for mean-pooling, while its advantage narrowed at higher coverage.",
   "Post-hoc calibration reduced binary ECE from 0.0304 to 0.0198, but did not improve Risk@30 and strict fixed-risk thresholds were too conservative to provide useful coverage.",
   "Removing construction-derived retrieval scores still produced 0.8370 Macro-F1 and replacing them with BM25 scores produced 0.8347, both substantially above mean-pooling at 0.6516.",
   "A GPT-4o audit judged 260 of 300 sampled refutation examples valid, and SURE-RAG obtained 0.9370 refuted-F1 on the audited subset."
  ]
 },
 {
  "paper_id": "2605.06635",
  "title": "Cited but Not Verified: Parsing and Evaluating Source Attribution in LLM Deep Research Agents",
  "research_question": "Do citations in deep-research reports actually support the claims attached to them, and how do citation reliability and factual support change across models and as research depth increases?",
  "key_findings": [
   "Working links and topically relevant sources substantially overstate citation reliability because factual support is much lower than those surface-level citation metrics.",
   "Across the evaluated models, factual-support performance spans a much wider and lower range than link accessibility, including a low of 24.4 percent Fact Check accuracy for OSS-120B.",
   "Fewer than half of the evaluated open-source-model runs successfully generated the required cited report, with reported task-success rates of 17 to 40 percent compared with 83 to 100 percent for frontier models.",
   "Increasing search depth from 2 to 150 tool calls reduced Fact Check accuracy by approximately 42 percent on average across the two frontier models in the ablation, while link validity and topical relevance stayed comparatively stable.",
   "For GPT-5.4, the largest factual-support deterioration appeared early in the depth ablation, with Fact Check accuracy falling from about 79 percent at 2 tool calls to 46 percent at 10 calls."
  ]
 },
 {
  "paper_id": "2605.16354",
  "title": "Augmenting Human Evaluation with LLM Judges: How Many Human Reviews Do You Need?",
  "research_question": "How can LLM-generated ratings be used as auxiliary measurements to reduce human evaluation cost while retaining a principled target level of statistical precision or power?",
  "key_findings": [
   "Because human-review probabilities are controlled and known by design, the doubly robust estimator can retain valid inference for the human-rating target even when the model predicting human ratings from auxiliary measurements is misspecified.",
   "The number of required human reviews decreases as the predictive relationship between LLM and human ratings becomes stronger and as the available LLM-rated pool becomes larger.",
   "For a fixed predictive quality, increasing the number of LLM evaluations has diminishing returns, and the required human sample approaches a nonzero floor proportional to one minus the squared predictive correlation.",
   "If LLM ratings contain no predictive information about human ratings, increasing the LLM-rated sample does not reduce the required human-review count.",
   "Stratifying human review according to heterogeneous LLM reliability can save human annotations by allocating more review to strata where LLM predictions are less reliable."
  ]
 },
 {
  "paper_id": "2606.00093",
  "title": "Agreement Measurement for Rubric-based LLM Judges: What to Report and Why",
  "research_question": "What measurement protocol and reporting practices are necessary for human-LLM judge agreement numbers to be interpretable, reconstructible and comparable, especially when evaluations include abstentions, multiple criteria and different aggregation choices?",
  "key_findings": [
   "For non-degenerate binary verdict vectors, Pearson correlation, Spearman correlation, Kendall tau-b, phi and Matthews correlation are mathematically identical, so reporting several of them adds no independent evidence.",
   "Cohen's kappa differs from phi through a marginal-mismatch factor and equals phi when the human and judge positive-label rates match.",
   "Excluding, recoding or retaining abstentions changes the estimand, and therefore agreement numbers produced under different abstention rules cannot be treated as measurements of the same quantity.",
   "When abstained cases are excluded, covered accuracy and coverage identify full-set forced-choice accuracy only within an interval whose width equals the uncovered fraction.",
   "In a reconstructed abstaining judge cascade, the same released predictions yield substantially different headline accuracies depending on abstention handling, including approximately 0.874 covered accuracy, approximately 0.73 after recoding and 0.534 with abstention retained as a third class."
  ]
 },
 {
  "paper_id": "2606.27736",
  "title": "ToE: A Hierarchical and Explainable Claim Verification Framework with Dynamic Multi-source Evidence Retrieval and Aggregation",
  "research_question": "Can automated claim verification be improved by dynamically retrieving heterogeneous evidence, decomposing uncertain claims, and aggregating evidence through an explainable hierarchical argument tree?",
  "key_findings": [
   "ToE obtains higher reported accuracy than the direct-prediction baseline for every displayed combination of the four evaluation datasets and two model backbones.",
   "On the constructed adversarial benchmark, ToE retains substantially higher accuracy than direct prediction for both evaluated backbones.",
   "Removing any tested source-tool category reduces overall accuracy in the source ablation, indicating that heterogeneous retrieval sources contribute complementary evidence in that experiment.",
   "Removing fact-checking sources causes the largest overall accuracy decrease among the displayed source-tool ablations.",
   "When the ideal reliability objective is submodular, the paper derives the standard greedy 1-1/e approximation relationship for its retrieval formulation."
  ]
 },
 {
  "paper_id": "2606.29054",
  "title": "When Can Conformal Risk Control Certify LLM Outputs? Bounds, Impossibility, and Adaptation for Structured Generation",
  "research_question": "Under what combinations of base risk, calibration data, confidence-score quality, and distribution shift can conformal risk control provide valid selective guarantees for structured LLM outputs, and when is such certification fundamentally infeasible?",
  "key_findings": [
   "When base risk exceeds the requested target, any valid distribution-free selective method must abstain on at least (mu-alpha)/(M-alpha) of examples, giving a feasibility limit that cannot be repaired merely by a tighter confidence bound.",
   "At strict targets across 716 seed-42 configurations, Hoeffding, Bernstein, and e-CRC certified 51, 72, and 80 configurations respectively, with zero test violations among their certified configurations in that split.",
   "Variance-aware certification was especially useful with limited calibration data: at a 10% calibration fraction, certification rates were 1.1% for Hoeffding, 1.9% for Bernstein, and 4.2% for e-CRC.",
   "Under genuine cross-dataset shift with target base risk above the requested level, static CRC and ACI each violated emitted-risk targets on 14 of 16 transfers at the headline ACI setting, and all seven tested ACI step sizes still yielded 14 of 16 emitted-risk violations.",
   "A full-feedback anytime-valid monitor produced zero violations on the same 16 transfer experiments and remained non-vacuous on feasible streams, emitting 65% to 97% of examples in the reported feasible cases."
  ]
 },
 {
  "paper_id": "2607.03870",
  "title": "Evaluating LLM Uncertainty in Long-Form Generation Using Deterministic Ground Truth",
  "research_question": "How can uncertainty in long-form LLM generation be evaluated at fine-grained resolution without noisy external judges, and what does such evaluation reveal about correctness propagation, calibration, confidence ranking, and reasoning?",
  "key_findings": [
   "Fine-grained confidence ranking deteriorates sharply at atomic resolution: many models' atomic Micro-AUROC values lie only modestly above chance, while line-level units exhibit substantially clearer ranking signal.",
   "Long-form correctness is path-dependent: errors in the generated prefix strongly reduce future correctness, while answer-context length contributes a separate but bounded degradation that saturates relatively early.",
   "Reasoning interventions improved answer precision but reduced the model's ability to rank its own correct and incorrect units by confidence; the reported paired analysis found a 23.3 percent relative AUROC degradation alongside accuracy gains.",
   "Logit-derived confidence functions significantly outperformed verbalized confidence across both calibration and ranking comparisons, but the best confidence function depended on which uncertainty property was being measured.",
   "Post-hoc binned calibration minimized ECE but harmed ranking, demonstrating that calibration quality and error-ranking quality can move in opposite directions."
  ]
 },
 {
  "paper_id": "2607.08700",
  "title": "Do You Need a Frontier Model as a Citation Verifier? Benchmarking Rubric LLMs for Deep-Research Source Attribution",
  "research_question": "How capable and expensive must an LLM citation judge be to evaluate source relevance and factual support reliably, and what judge biases are hidden by aggregate accuracy metrics?",
  "key_findings": [
   "A more expensive frontier judge was not consistently more accurate: GPT-5-mini achieved the highest reported source-relevance F1 at 0.908 despite being among the lower-cost evaluated judges.",
   "For factual support, the 95 percent confidence intervals of all eight judges overlap, so the benchmark does not establish a statistically distinguishable winner on that dimension.",
   "Judge cost spans a 49-fold range in the study, but cost does not track citation-verification accuracy.",
   "Judges with similar aggregate F1 can have materially different pass-rate drift, false-positive rates, and false-negative rates, so scalar F1 hides operationally important directional bias.",
   "All eight judges are systematically stricter than the gold labels on source relevance, and factual-support errors are dominated by rejection of genuinely supported citations rather than acceptance of unsupported ones."
  ]
 },
 {
  "paper_id": "2607.19322",
  "title": "Two-Level Meta-Rubrics for Evaluating Open-Ended Generation: GAMUT, a Benchmark for Factual Completeness",
  "research_question": "How can factual completeness of open-ended long-form generation be evaluated with rubrics rich enough to represent structured answer requirements yet simple enough for reliable automated judging?",
  "key_findings": [
   "Gamut exposes substantial factual incompleteness in current systems: the strongest evaluated model scored 58.7% on the multimodal benchmark.",
   "Omission was the dominant failure mode, with missing rubric elements accounting for more than a quarter of checks even for the strongest systems and roughly two-thirds for some weak systems.",
   "The structured meta-rubric was empirically necessary for nearly all questions: 98% contained answer structure that a flat list of independently required facts would misrepresent.",
   "Model ordering was highly stable across Gemini 3.1 Pro and Claude Opus 4.8 judges, while Qwen3-VL 235B was more lenient but preserved the broad ordering.",
   "Removing the visual-identification requirement improved every evaluated model by roughly 10 to 20 Gamut points while broadly preserving model ordering."
  ]
 },
 {
  "paper_id": "2608.11238",
  "title": "Towards Query-Agnostic RAG Evaluation via Query Coverage and Claim Verifiability",
  "research_question": "Can a reference-free RAG evaluation framework provide consistent fine-grained retrieval and generation diagnostics for both close-ended and open-ended queries by combining query coverage with claim verifiability?",
  "key_findings": [
   "Q-CARE produces fine-grained retrieval and generation measurements without requiring gold answers or gold evidence chunks, enabling the same framework to operate on both close-ended and open-ended queries.",
   "Across the constructed benchmark, Q-CARE reports higher agreement with human judgments than the four compared RAG evaluation frameworks on the reported retrieval and generation dimensions.",
   "The human-annotation study shows strong task-level agreement, with Fleiss' kappa between 0.801 and 0.891 for the three alignment tasks and over 97% agreement for decomposition verification.",
   "Q-CARE's coverage and verifiability formulation transfers to conversational RAG, where it achieves the highest reported correlation on three of four datasets in both evaluated dimensions without changing the framework.",
   "Query decomposition significantly improves Completeness across both close- and open-ended settings and both tested Qwen backbones, with reported gains from 0.056 to 0.473."
  ]
 },
 {
  "paper_id": "2608.22483",
  "title": "Claim-Level Confidence Calibration for Reliable Decision Making with Large Language Models",
  "research_question": "Can inference-time claim-level confidence estimation provide better calibrated and more decision-actionable uncertainty than assigning a single confidence value to an entire free-form LLM response?",
  "key_findings": [
   "Decomposing free-form responses into atomic claims and calibrating confidence at that level produces actionable per-claim uncertainty and reduces expected calibration error in factual-question settings.",
   "Claim-level calibration can match or outperform response-level uncertainty baselines on mixed-correctness factual responses, although the magnitude and best method vary substantially by model and dataset.",
   "False-premise and other adversarial inputs remain a major failure mode because models can assign high confidence to incorrect claims; the authors therefore recommend active verification or retrieval rather than confidence alone.",
   "Reasoning-focused models show stronger verbalized uncertainty behavior, but extracting claims from their entire chain of thought can dilute useful final-answer confidence and final-answer-only extraction performs better.",
   "The proposed inference pipeline is materially more expensive than one-call prompting, with the paper estimating roughly six times the API-call cost per query for its full claim extraction and verification workflow."
  ]
 },
 {
  "paper_id": "doi-10-1016-j-jisa-2025-104120",
  "title": "Conformal prediction for labelling and updating online models in the presence of concept drift in cybersecurity",
  "research_question": "Can conformal prediction supply sufficiently reliable pseudo-labels to update online cybersecurity classifiers when true labels are scarce and the data distribution undergoes concept drift?",
  "key_findings": [
   "Conformal pseudo-label updates improve online classification in a substantial subset of dataset-model-labeling configurations, but the gains are not consistent across all conditions.",
   "On the malicious-IP dataset, Adaptive Random Forest with conformal updates shows statistically significant improvements across the reported metrics for all evaluated true-label proportions.",
   "On CICIDS 2018, the conformal-update strategy is especially beneficial for Adaptive Random Forest and Logistic Regression in the reported comparisons.",
   "The effect of conformal pseudo-labeling is model- and dataset-dependent, and some configurations obtain little benefit or deteriorate.",
   "Larger concept drift is associated with smaller expected gains from the conformal-update mechanism in the authors' experiments."
  ]
 },
 {
  "paper_id": "doi-10-1017-s1351324909005051",
  "title": "Formal and functional assessment of the pyramid method for summary content evaluation",
  "research_question": "Can the Pyramid Method provide reliable, annotator-consistent and statistically discriminative evaluation of summary content across different summarization evaluation settings?",
  "key_findings": [
   "Peer-summary annotation showed generally strong inter-annotator reliability, with mean alpha-Dice agreement of about 0.78 in the reported DUC 2003 comparison.",
   "Independent annotations produced score distributions with no significant annotator effect in the reported Set I ANOVAs, indicating that annotation differences had little effect on aggregate scores.",
   "Two independently annotated evaluations disagreed on only two of 120 pairwise system-ranking comparisons, providing strong functional evidence that system-level conclusions were robust to annotator choice.",
   "The evaluated system was a highly significant predictor of Pyramid score in all three DUC years, despite changes in task and evaluation conditions.",
   "Power analyses indicated that substantially fewer document sets than those used in the evaluations could still distinguish systems at the specified high-power setting."
  ]
 },
 {
  "paper_id": "doi-10-1038-s41598-026-40637-w",
  "title": "Conformal selective prediction with cost aware deferral for safe clinical triage under distribution shift",
  "research_question": "Can calibrated probabilities, conformal prediction, and cost-aware deferral be combined to make clinical triage safer while maintaining useful coverage under temporal distribution shift?",
  "key_findings": [
   "At 80% retained coverage, selective prediction reduced retained-case error by 49.6% on the in-distribution test set and 46.7% on the temporally shifted test set relative to predicting on every case.",
   "The calibration-set cost optimization selected a deferral threshold of 0.8, yielding expected cost 0.5640 in distribution and 0.7053 under temporal shift, a 25.1% relative increase under shift.",
   "Importance-weighted conformal prediction preserved target coverage better under temporal shift than the vanilla and gender-Mondrian variants, attaining 88.2% empirical coverage against a 90% target.",
   "Temperature scaling produced low expected calibration error on both evaluations, with ECE 0.016 in distribution and 0.030 on the shifted test set.",
   "Gender-Mondrian conformal prediction produced similar in-distribution coverage for female and male groups, with a reported coverage gap of 1.4 percentage points."
  ]
 },
 {
  "paper_id": "doi-10-1109-access-2026-3679691",
  "title": "Program-Verifiable Evaluation for Temporal QA: Metrics for Evidence Validity",
  "research_question": "How can temporal question-answering systems be evaluated so that answer correctness is separated from whether the cited evidence was actually valid at the query time?",
  "key_findings": [
   "Answer correctness does not guarantee valid evidence: under oracle answers on TimeFact-CEO, 11.8 percent of selected citations are temporally invalid, with TMR 0.118 and RAS 0.903.",
   "The proposed lexico-temporal reranker raises temporal-validity recall on TimeFact-CEO from 48.2 percent for BM25 to 88.2 percent, a 40.0 percentage-point improvement under oracle-answer evaluation.",
   "On the noisy Wikidata-CEO corpus, the temporal reranker achieves RAS 0.936, RAR 0.934, and TMR 0.066, indicating that interval-aware evaluation remains useful outside the perfectly controlled synthetic benchmark.",
   "First-stage retrieval coverage is the dominant bottleneck: coverage is 76.3 percent at K=3 and the authors attribute 82.4 percent of analyzed errors to gold evidence being absent from the retrieved candidate set.",
   "Separating an oracle-answer diagnostic from end-to-end QA exposes evidence-timeliness failures that aggregate answer accuracy can hide."
  ]
 },
 {
  "paper_id": "doi-10-1155-2016-1340973",
  "title": "Mining Sequential Update Summarization with Hierarchical Text Analysis",
  "research_question": "Can a hierarchical combination of time-sensitive retrieval, topic-level keyword mining, and sentence-level scoring produce novel, timely, and comprehensive updates for rapidly developing news events?",
  "key_findings": [
   "The keyword-diversity-only KS method achieved expected gain 0.149 and expected latency gain 0.136, equal to the best reported values used for comparison in the paper.",
   "The more coverage-oriented KLP method attained substantially higher comprehensiveness than KS; its best reported configuration reached 0.224 comprehensiveness and 0.292 latency comprehensiveness versus 0.099 and 0.126 for KS.",
   "The experiments expose a precision-coverage trade-off: KS performs better on gain-oriented metrics while KLP covers more distinct gold nuggets but is more prone to selecting long sentences.",
   "Changing KLP's sentence-length and sentence-position weights had little effect relative to the importance of keyword diversity.",
   "The evaluation explicitly penalizes delayed updates and verbose updates while measuring coverage of atomic gold nuggets, providing a joint treatment of novelty, timeliness, and omission-like coverage failure."
  ]
 },
 {
  "paper_id": "doi-10-1162-tacl-a-00407",
  "title": "How Can We Know When Language Models Know? On the Calibration of Language Models for Question Answering",
  "research_question": "How reliably do generative language-model probabilities indicate whether answers to knowledge-based questions are correct, and which calibration techniques can improve that correspondence?",
  "key_findings": [
   "Strong generative QA models can have high answer accuracy while remaining poorly calibrated, and their raw probabilities frequently assign excessive confidence to incorrect answers.",
   "On the main multiple-choice evaluation datasets, candidate-aware fine-tuning and post-hoc calibration both reduced ECE with little or no corresponding loss of answer accuracy for several methods.",
   "The combined calibration approach reduced ECE on MC-test from 0.095 for the original UnifiedQA model to 0.044, although its accuracy decreased from 0.769 to 0.748.",
   "Calibration transferred imperfectly across domains: temperature scaling learned on the training domains over-corrected confidence on MC-test, and an oracle temperature fit directly on the evaluation domain was better aligned.",
   "Calibration improvements were substantially more limited for extractive QA than for multiple-choice QA, which the authors associate with the more uncertain automatically generated candidate-span sets."
  ]
 },
 {
  "paper_id": "doi-10-1609-aaai-v40i40-40667",
  "title": "COIN: Uncertainty-Guarding Selective Question Answering for Foundation Models with Provable Risk Guarantees",
  "research_question": "Can a foundation-model question-answering system calibrate an uncertainty threshold that gives a high-probability bound on conditional answer failure while retaining substantially more correct answers than existing conformal-alignment selection methods?",
  "key_findings": [
   "Across the reported repeated trials, both the Clopper-Pearson and Hoeffding COIN variants kept mean empirical conditional failure rates below the user-specified target risk levels for the evaluated foundation models.",
   "COIN retained substantially more admissible answers than conformal alignment in several settings; for Qwen2.5-14B on CommonsenseQA, the Clopper-Pearson variant reached power 0.85 at target risk 0.15, reported as 0.36 higher than conformal alignment.",
   "On TriviaQA, the reported power advantage over conformal alignment reached about 0.4 in some evaluated risk settings.",
   "The method continued to satisfy the evaluated risk targets when only one tenth of the available examples were allocated to calibration in the reported limited-calibration experiment.",
   "Because the threshold is pre-calibrated, COIN's deployment-time decision is a threshold comparison rather than a test-time comparison against every calibration example as required by the conformal-alignment baseline."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-2021-acl-long-84",
  "title": "The Art of Abstention: Selective Prediction and Error Regularization for Natural Language Processing",
  "research_question": "How well do common confidence estimators support abstention in NLP classification, and can training-time error regularization improve the ordering of examples by confidence without materially reducing task accuracy?",
  "key_findings": [
   "More capable Transformer classifiers generally achieved both better task accuracy and better selective-prediction quality than the LSTM baseline.",
   "Softmax response was a strong confidence baseline and generally compared favorably with Monte Carlo dropout; the latter required roughly 20 stochastic repetitions before becoming competitive in the reported setting.",
   "Pairwise error regularization improved confidence ranking while leaving task accuracy largely unchanged, with the best configurations reducing risk-coverage AUC by roughly 10% on average relative to unregularized training.",
   "Neither current-error regularization nor history-based regularization consistently dominated the other across tasks and models.",
   "In classifier cascades, confidence produced by an error-regularized first-stage model enabled a better accuracy-computation tradeoff than random routing and improved over the corresponding unregularized confidence strategy."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-2025-acl-long-837",
  "title": "Can LLMs Evaluate Complex Attribution in QA? Automatic Benchmarking using Knowledge Graphs",
  "research_question": "Can a knowledge-graph-generated benchmark with fine-grained attribution categories and compositional evidence requirements reliably evaluate and improve automatic attribution evaluators, including under out-of-domain testing?",
  "key_findings": [
   "Zero-shot and few-shot evaluators struggle with fine-grained negative attribution categories, especially partially supportive evidence, whereas after CAQA fine-tuning all evaluated models except Mistral-v0.2 exceed 90% performance in the reported fine-grained evaluation.",
   "Evaluator errors increase on attribution cases requiring multi-piece logical reasoning, and the paper documents failures caused by keyword co-occurrence rather than correct reasoning over evidence relationships.",
   "Evaluator micro-F1 scores computed using CAQA's automatically generated labels closely align with scores computed using separately collected human labels, with Pearson correlation 0.97.",
   "On 200 partially supportive examples, CAQA's automatically computed FACTSCORE is 0.62 versus 0.58 from human annotations, a gap of 0.04 that is smaller than the gaps of the evaluated attribution models.",
   "On out-of-domain ALCE-FineGrained, the CAQA-fine-tuned T5-11B reaches overall F1 of 0.63 versus 0.54 for AutoIS, while CAQA-fine-tuned Vicuna-13B reaches 0.38 versus 0.36 for AttrScore."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-w19-8642",
  "title": "Agreement is overrated: A plea for correlation to assess human evaluation reliability",
  "research_question": "Is inter-annotator agreement alone an adequate reliability criterion for human evaluation of NLG, or should correlation be used alongside agreement to capture systematic rater consistency?",
  "key_findings": [
   "Only 24 of the 135 surveyed papers, or 18%, report information about inter-annotator agreement.",
   "The survey identifies three recurring problems: reliability studies are infrequent, agreement reporting lacks a common practice, and reported agreement values are generally low under conventional interpretation scales.",
   "In the pilot case study, low Fleiss' kappa can coexist with very strong correlation; for native-English judges on fluency, the reported kappa is below 0.4 while Goodman and Kruskal's Gamma is perfect.",
   "For Flickr-8k, Fleiss' kappa is 0.52 while average Gamma is 0.98, showing that judges can differ in rating magnitude while covarying systematically.",
   "The authors recommend reporting correlation and agreement together because exact agreement and relative consistency measure different aspects of human-evaluation reliability."
  ]
 },
 {
  "paper_id": "doi-10-32604-cmc-2026-086343",
  "title": "Do LLMs Know When Evidence is Insufficient? An Evidence Sufficiency Benchmark for Answer-Abstention Calibration in Retrieval-Augmented Generation",
  "research_question": "Can current LLMs reliably recognize when retrieved evidence is sufficient to justify an answer and abstain when evidence is irrelevant, absent, incomplete, or contradictory?",
  "key_findings": [
   "All seven evaluated models substantially over-answer when presented with conflicting evidence, with L5 over-answer rates above 65%.",
   "Models generally recognize complete evidence absence more reliably than internal contradiction between plausible evidence passages.",
   "Abstention prompting and chain-of-thought prompting can improve behavior, but gains vary sharply across model families and do not eliminate conflict-driven over-answering.",
   "Six of seven models exhibit significant sensitivity to the order in which conflicting passages are presented.",
   "High answer accuracy under well-supported evidence does not imply reliable evidence-sufficiency behavior under insufficient or contradictory evidence."
  ]
 },
 {
  "paper_id": "doi-10-6028-nist-sp-500-321-realtime-overview",
  "title": "Overview of the TREC 2016 Real-Time Summarization Track",
  "research_question": "How should systems that continuously monitor a live social-media stream for prospective information needs be evaluated for relevance, novelty, redundancy, and timeliness in both immediate push-notification and periodic digest settings?",
  "key_findings": [
   "The track demonstrated a workable real-time evaluation architecture in which live system outputs could be routed immediately to mobile assessors and judged in the temporal context in which notifications were received.",
   "Treating redundant tweets separately from relevant novel tweets allowed the evaluation to explicitly penalize repeated information and measure the value of newly surfaced content.",
   "Across submitted runs, the authors observed no strong relationship between output-quality metrics and notification latency, contrary to the intuitive expectation that waiting longer to accumulate evidence would necessarily improve quality.",
   "Daily digest systems did not, as a group, outperform push-notification systems on quality metrics despite having the opportunity to accumulate evidence over an entire day.",
   "Metrics that reward correctly remaining silent made an empty or low-output strategy surprisingly competitive in some settings, showing the importance of evaluating whether a system knows when no valuable new update exists."
  ]
 },
 {
  "paper_id": "manual-2be3626f9e",
  "title": "Optimal Strategies for Reject Option Classifiers",
  "research_question": "Do the principal cost-based, risk-constrained, and coverage-constrained formulations of classification with a reject option share a common optimal decision strategy, and can the uncertainty ordering required by that strategy be learned for arbitrary black-box predictors?",
  "key_findings": [
   "The cost-based, bounded-improvement, and bounded-coverage formulations have the same structural form of Bayes-optimal strategy: a Bayes predictor paired with a selection rule based on thresholding conditional expected risk, with possible randomization on the decision boundary.",
   "The paper establishes explicit relationships between the rejection threshold and boundary randomization parameters across the three formulations, linking cost, target selective risk, and target coverage.",
   "A proper uncertainty score only needs to preserve the ordering induced by conditional expected risk, allowing selective decisions to be constructed even when the exact conditional risk is unavailable.",
   "Both regression-on-loss and the SELE objective are shown to be Fisher-consistent approaches for learning an uncertainty score for a fixed black-box predictor.",
   "In the classification experiments, SELE significantly outperformed several conventional confidence or regression baselines in some model settings, although the statistical tests did not distinguish every pair of methods."
  ]
 },
 {
  "paper_id": "manual-32d5793dca",
  "title": "Validating LLM-as-a-Judge Systems under Rating Indeterminacy",
  "research_question": "How should LLM-as-a-judge systems be validated when a rating item can legitimately admit multiple ratings, and how much error can standard forced-choice gold labels introduce?",
  "key_findings": [
   "Forced-choice validation can select a substantially worse judge because humans and LLM judges may resolve the same underlying rating indeterminacy differently.",
   "Across the evaluated tasks, response-set-based MSE selects more performant judges than the compared forced-choice metrics once modeled human rating indeterminacy reaches beta_H of at least 0.2.",
   "In the Civil Comments toxicity example, Claude Sonnet 3.5 is top-ranked by the standard forced-choice approach but is reported to be 31% less consistent with human downstream decisions than GPT o3-Mini when rating indeterminacy is accounted for.",
   "A response-set metric whose forced-choice translation matrix is estimated from only 100 paired forced-choice and response-set ratings performs almost as well as the corresponding oracle version.",
   "When only forced-choice ratings are available, the paper recommends distributional metrics and reports that KL divergence in the human-to-judge direction often performs best among the examined forced-choice alternatives."
  ]
 },
 {
  "paper_id": "manual-39435af3dd",
  "title": "Overview of the TAC 2008 Update Summarization Task",
  "research_question": "How effectively can automatic systems produce concise summaries containing new information from a later document set when the reader is assumed to know an earlier set, and how well do automatic summary metrics reflect human judgments of that capability?",
  "key_findings": [
   "Human summaries were significantly better than automatic summaries on manual measures of readability, Pyramid content coverage, and overall responsiveness.",
   "Human summarizers performed similarly on initial and update summaries, whereas automatic systems had greater difficulty selecting responsive content for the later update summaries.",
   "The Pyramid evaluation explicitly rewarded coverage of weighted information units while giving no extra credit for repeating the same Summary Content Unit, thereby operationalizing both content completeness and non-redundancy.",
   "ROUGE-2, ROUGE-SU4, and BE-HM correlated highly with manual evaluation for automatic summaries, and differences among their Pearson or Spearman correlations were not statistically significant at the 95 percent level.",
   "Automatic overlap metrics failed to reproduce some important distinctions visible to manual evaluation, including the clear human-versus-system gap, and BE-HM failed to detect the aggregate degradation from initial to update summaries."
  ]
 },
 {
  "paper_id": "manual-f5ce52cae2",
  "title": "ReproHum #0892-01: The painful route to consistent results: A reproduction study of human evaluation in NLG",
  "research_question": "Can the human understandability evaluation from a prior clinical text-simplification study be reproduced reliably despite incomplete documentation and unavoidable changes in the experimental setup?",
  "key_findings": [
   "The reproduced study preserves the same overall system ordering as the original evaluation, with NTS plus Phrase Table ranked best and the Phrase Table Baseline ranked worst.",
   "The best system's average rank is 1.93 in the original experiment and 1.82 in the reproduction.",
   "System-level results are extremely highly correlated across studies, with Pearson r of 0.98 and Spearman rho of 1.00.",
   "Correlations between average annotations for individual sentences are lower but still positive, with Pearson r of 0.76 and Spearman rho of 0.75.",
   "Inter-annotator agreement is higher in the replication than in the original study, with Krippendorff's alpha of 0.40 versus 0.22, while agreement between the two studies is 0.30."
  ]
 }
]

JSON schema for the verdict:
{
 "$schema": "http://json-schema.org/draft-07/schema#",
 "title": "ReviewerResult",
 "description": "Schema for reviewer gate results (synthesis reviewer, rank reviewer).",
 "type": "object",
 "required": [
  "reviewer_task_id",
  "target_artifact",
  "status"
 ],
 "properties": {
  "reviewer_task_id": {
   "type": "string"
  },
  "target_artifact": {
   "type": "string"
  },
  "status": {
   "type": "string",
   "enum": [
    "accepted",
    "rejected",
    "accepted_with_issues"
   ]
  },
  "issues": {
   "type": "array",
   "items": {
    "type": "string"
   }
  },
  "unsupported_claims": {
   "type": "array",
   "items": {
    "type": "string"
   }
  },
  "required_fixes": {
   "type": "array",
   "items": {
    "type": "string"
   }
  },
  "confidence": {
   "type": "number",
   "minimum": 0.0,
   "maximum": 1.0
  },
  "notes": {
   "type": "string"
  }
 }
}

Reply with one block containing one JSON object:
`reviewer_task_id` = "review-synthesis-web", `target_artifact` =
"/home/grammy-jiang/Projects/msgloom/research/10-evidence-and-reliability-evaluation/runs/1b615a33607c/analysis/synthesis.json", `status` = accepted | accepted_with_issues | rejected,
`issues` (each naming the finding or paper it is about), `required_fixes`
(required when rejected), `unsupported_claims`, `confidence`, and `scores`
with faithfulness, coherence, gap_completeness (0-1) and citation_integrity
(true/false).
===BEGIN synthesis_review.json===
<content>
===END synthesis_review.json===
