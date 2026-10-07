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

Research topic: **Direct empirical evaluations of longitudinal cross-thread workplace briefing: cycle-by-cycle new/open/resolved/superseded work-item tracking, obligation-versus-preference selection, adaptive personalization under preference drift, and joint omission/repetition/false-alert evaluation.**

You did not write this synthesis and you are not reviewing your own work.
Your verdict decides whether the report may be written. Rejecting is a normal
outcome: reject when the evidence does not support the synthesis. Do not
soften a real problem into a note so that the work can pass.

Check five things against the analyses below, not against how well the
synthesis reads:

1. Faithfulness — every finding is traceable to at least one analysis, and no
   finding states more than its cited analyses support.
2. Citation integrity — every cited paper_id is one of: `1301.6707`, `2107.14691`, `2109.06896`, `2202.07088`, `2208.03828`, `2403.01365`, `2403.19795`, `2609.02465`, `doi-10-1007-978-3-319-67684-5-24`, `doi-10-1016-j-cag-2014-02-006`, `doi-10-1016-j-eswa-2021-114890`, `doi-10-1016-j-eswa-2021-115626`, `doi-10-1016-j-knosys-2013-02-015`, `doi-10-1093-jcmc-zmac001`, `doi-10-1098-rsos-181870`, `doi-10-1109-access-2022-3182390`, `doi-10-1109-fuzz-ieee-2016-7737835`, `doi-10-1136-amiajnl-2014-002945`, `doi-10-1145-1056808-1057071`, `doi-10-1145-1557019-1557124`, `doi-10-1145-2063576-2063683`, `doi-10-1145-2523813`, `doi-10-1145-290941-291025`, `doi-10-1145-2998181-2998251`, `doi-10-1145-3705328-3748164`, `doi-10-1145-383952-383954`, `doi-10-1145-634067-634150`, `doi-10-1145-642611-642672`, `doi-10-1155-2016-1340973`, `doi-10-1177-1071181322661236`, `doi-10-1186-s41235-019-0195-y`, `doi-10-1207-s15327051hci2001-2-3`, `doi-10-1609-icwsm-v12i1-15014`, `doi-10-18653-v1-2007-sigdial-1-4`, `doi-10-18653-v1-2020-acl-main-122`, `doi-10-18653-v1-2024-acl-long-390`, `doi-10-18653-v1-2026-acl-long-1149`, `doi-10-18653-v1-d19-1386`, `doi-10-2196-43977`, `doi-10-3389-fpsyg-2014-00657`, `doi-10-3758-bf03201140`, `doi-10-3758-s13421-025-01708-x`, `doi-10-3758-s13423-026-02985-6`, `doi-10-6028-nist-sp-500-302-tempsumm-overview`, `doi-10-64898-2025-11-28-25341233`, `manual-0839b98ee7`, `manual-13a21477e7`, `manual-1d6b22c7ad`, `manual-39435af3dd`, `manual-4cb48c423e`, `manual-50ed5dc808`, `manual-bdce973227`, `manual-c2f56a571b`.
3. Coherence — contradictions between papers are named, not averaged away.
4. Gap completeness — a gap this corpus cannot close is reported as open. A
   gap presented as closed without evidence is a rejection.
5. Overreach — transfer-domain or synthetic evidence is not presented as
   direct-domain evidence, and no production claim rests on it.

Synthesis under review:
{
 "topic": "Direct empirical evaluations of longitudinal cross-thread workplace briefing: cycle-by-cycle new/open/resolved/superseded work-item tracking, obligation-versus-preference selection, adaptive personalization under preference drift, and joint omission/repetition/false-alert evaluation.",
 "paper_count": 53,
 "executive_summary": "The corpus provides substantial component-level evidence for temporal update summarization, personalized email prioritization, reminder systems, preference-drift adaptation, uncertainty communication, and longitudinal summarization, but it does not directly evaluate the combined workplace-briefing task defined by this topic. News summarization work explicitly evaluates novelty, coverage, redundancy, latency, and off-event material, while email studies demonstrate heterogeneous user priority policies, useful personalization, reminder value, and problems caused by stale state. Incremental longitudinal processing is demonstrated in news and clinical settings, and recommender research supplies transfer evidence on adaptation under preference drift. Prospective-memory studies separately identify effects of reminder content, reminder-setting determinants, and learned reminder reliability. None of the admitted papers jointly evaluates cycle-by-cycle new/open/resolved/superseded workplace items, explicit obligations versus soft preferences, preference drift, omission, repetition, and false alerts.",
 "themes": [
  "Temporal and update summarization separates novelty, usefulness, coverage, redundancy, and latency rather than reducing quality to generic summary similarity.",
  "Email prioritization and triage are strongly user-dependent, and personalized models can outperform global or non-personalized alternatives.",
  "Workplace task and reminder studies expose persistent pending-work, staleness, forgotten-task, and heterogeneous-workstyle problems.",
  "Incremental longitudinal processing has empirical support in news and clinical domains, but direct cross-thread workplace briefing remains untested.",
  "Preference drift and continual adaptation are well studied in recommender systems, primarily as transfer evidence rather than workplace-email evidence.",
  "Hard requirements and soft preferences can be represented separately in adjacent constrained-decision domains, without direct evidence that this decomposition improves workplace briefing.",
  "Uncertainty and conflicting evidence alter human decision behavior in ways that depend on presentation and task context.",
  "Prospective-memory research distinguishes reminder content effectiveness from determinants of reminder use and from behavioral consequences of reminder reliability."
 ],
 "findings": [
  {
   "statement": "In temporal news summarization, evaluation frameworks explicitly distinguish useful or novel updates from coverage, redundancy, off-event material, verbosity, and latency, and the reported systems exhibit trade-offs between precision-like gain and comprehensiveness rather than one method maximizing all objectives.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "doi-10-1145-383952-383954",
     "section": "Key findings in supplied analysis"
    },
    {
     "paper_id": "doi-10-6028-nist-sp-500-302-tempsumm-overview",
     "section": "Key findings in supplied analysis"
    },
    {
     "paper_id": "doi-10-1155-2016-1340973",
     "section": "Key findings in supplied analysis"
    },
    {
     "paper_id": "manual-39435af3dd",
     "section": "Key findings in supplied analysis"
    }
   ]
  },
  {
   "statement": "Email-thread summarization experiments show that conversational structure can improve extractive content selection, while modern abstractive models still make salience and faithfulness errors involving main intentions, participant roles, and attribution, with performance declining on longer threads.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "2107.14691",
     "section": "Key findings in supplied analysis"
    },
    {
     "paper_id": "manual-c2f56a571b",
     "section": "Key findings in supplied analysis"
    }
   ]
  },
  {
   "statement": "Workplace email and task-management studies show that users retain messages as prospective-task cues, value reminders for forgotten work, encounter stale or incorrect reminder state, and differ substantially in triage and request-management practices.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "2403.01365",
     "section": "Key findings in supplied analysis"
    },
    {
     "paper_id": "doi-10-1145-634067-634150",
     "section": "Key findings in supplied analysis"
    },
    {
     "paper_id": "doi-10-1207-s15327051hci2001-2-3",
     "section": "Key findings in supplied analysis"
    },
    {
     "paper_id": "doi-10-1145-2998181-2998251",
     "section": "Key findings in supplied analysis"
    },
    {
     "paper_id": "doi-10-1145-642611-642672",
     "section": "Key findings in supplied analysis"
    }
   ]
  },
  {
   "statement": "Personalized email-priority models improve priority prediction relative to global or simpler baselines in the evaluated email datasets, while observed triage strategies and useful feature combinations vary across users and data conditions; these studies predict importance or priority rather than response obligation.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "manual-50ed5dc808",
     "section": "Key findings in supplied analysis"
    },
    {
     "paper_id": "doi-10-1145-1557019-1557124",
     "section": "Key findings in supplied analysis"
    },
    {
     "paper_id": "doi-10-1145-2063576-2063683",
     "section": "Key findings in supplied analysis"
    },
    {
     "paper_id": "doi-10-1145-1056808-1057071",
     "section": "Key findings in supplied analysis"
    }
   ]
  },
  {
   "statement": "Incremental longitudinal summarization is empirically demonstrated in the supplied analyses for an LLM-based news-timeline pipeline that processes new text as it arrives and for CLIN-SUMM, which incrementally summarizes newly documented clinical information without future documentation. The supplied analysis of MAS-TLS establishes chronological report generation and adaptive scheduling, but does not itself establish streaming incremental-arrival processing.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "doi-10-18653-v1-2024-acl-long-390",
     "section": "Key findings in supplied analysis"
    },
    {
     "paper_id": "doi-10-64898-2025-11-28-25341233",
     "section": "Key findings in supplied analysis"
    },
    {
     "paper_id": "doi-10-18653-v1-2026-acl-long-1149",
     "section": "Key findings in supplied analysis"
    }
   ]
  },
  {
   "statement": "In recommender-system transfer domains, incremental updating, temporal preference models, drift detection, and selective use of historical interactions can improve offline recommendation metrics under changing preferences, although gains vary by dataset, history utilization, and evaluation protocol.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "doi-10-1016-j-eswa-2021-114890",
     "section": "Key findings in supplied analysis"
    },
    {
     "paper_id": "doi-10-1016-j-eswa-2021-115626",
     "section": "Key findings in supplied analysis"
    },
    {
     "paper_id": "doi-10-1109-access-2022-3182390",
     "section": "Key findings in supplied analysis"
    },
    {
     "paper_id": "doi-10-1109-fuzz-ieee-2016-7737835",
     "section": "Key findings in supplied analysis"
    },
    {
     "paper_id": "doi-10-1145-2523813",
     "section": "Key findings in supplied analysis"
    },
    {
     "paper_id": "doi-10-1145-3705328-3748164",
     "section": "Key findings in supplied analysis"
    }
   ]
  },
  {
   "statement": "Adjacent constrained-decision studies demonstrate explicit separation of mandatory task constraints from softer learned preferences and show that personalized constrained ranking can retain constraint compliance, but these experiments concern robot planning and recommendation rather than workplace response obligations.",
   "confidence": "MEDIUM",
   "evidence": [
    {
     "paper_id": "2403.19795",
     "section": "Key findings in supplied analysis"
    },
    {
     "paper_id": "2202.07088",
     "section": "Key findings in supplied analysis"
    }
   ]
  },
  {
   "statement": "Uncertainty and conflicting-evidence studies show that presentation of uncertainty can change decision process or prioritization without necessarily improving classification accuracy, conflicting cues can increase uncertainty and errors, and communicating epistemic uncertainty does not have a uniform negative effect on trust.",
   "confidence": "MEDIUM",
   "evidence": [
    {
     "paper_id": "doi-10-1016-j-cag-2014-02-006",
     "section": "Key findings in supplied analysis"
    },
    {
     "paper_id": "doi-10-1609-icwsm-v12i1-15014",
     "section": "Key findings in supplied analysis"
    },
    {
     "paper_id": "doi-10-1098-rsos-181870",
     "section": "Key findings in supplied analysis"
    },
    {
     "paper_id": "2208.03828",
     "section": "Key findings in supplied analysis"
    }
   ]
  },
  {
   "statement": "In the tested prospective-memory experiments on reminder content, reminders linking the target event with the intended action produced stronger prospective-memory performance than target-only reminders and generally outperformed action-only reminders.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "doi-10-3758-bf03201140",
     "section": "Key findings in supplied analysis"
    }
   ]
  },
  {
   "statement": "Prospective-memory studies on reminder setting and cognitive offloading find that lower confidence can predict greater reminder use, longer delays can increase reminder setting in a time-based paradigm, and reduced cue visibility can increase reminder use; these results concern whether people externalize intentions, not a general effect of confidence or cue visibility on reminder effectiveness.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "doi-10-1186-s41235-019-0195-y",
     "section": "Key findings in supplied analysis"
    },
    {
     "paper_id": "doi-10-3758-s13421-025-01708-x",
     "section": "Key findings in supplied analysis"
    }
   ]
  },
  {
   "statement": "Experience with highly reliable reminders can reduce reported internal intention-maintenance thoughts and increase ongoing-task-related thoughts; when expected reminders were unexpectedly absent, worse prospective-memory performance in the fully reliable condition was reported as suggestive rather than definitive.",
   "confidence": "MEDIUM",
   "evidence": [
    {
     "paper_id": "doi-10-3758-s13423-026-02985-6",
     "section": "Key findings in supplied analysis"
    }
   ]
  }
 ],
 "contradictions": [
  {
   "topic": "Scope-qualified tension in the role of delay in prospective-memory reminder paradigms",
   "papers": [
    "doi-10-3758-bf03201140",
    "doi-10-3758-s13421-025-01708-x"
   ],
   "note": "These studies do not provide a clean direct contradiction because they use different prospective-memory paradigms and outcomes. The earlier reminder-content experiments found no significant effect of reminder-to-target or instruction-to-task delay within their tested ranges, whereas the later time-based-intention experiments found that longer delays reduced unaided first-response accuracy, lowered confidence, increased reminder use, and produced larger benefits from setting reminders. The evidence therefore does not support a domain-general claim that delay either does or does not affect reminder effectiveness."
  }
 ],
 "gaps": [
  {
   "id": "gap-1",
   "description": "This corpus still does not directly evaluate a longitudinal workplace briefing that, across successive report cycles, distinguishes newly changed information from unchanged-but-still-open work while suppressing resolved or superseded information.",
   "classification": "ACADEMIC",
   "priority": "HIGH",
   "suggested_query": "\"incremental summarization\" longitudinal workplace email briefing \"open\" resolved superseded state"
  },
  {
   "id": "gap-2",
   "description": "This corpus still does not establish how explicit user rules or response obligations interact with softer personalized importance, triage, reminder-value, or forgetting signals in briefing selection, nor whether separating these signal classes improves workplace outcomes.",
   "classification": "ACADEMIC",
   "priority": "HIGH",
   "suggested_query": "\"email prioritization\" \"response obligation\" hard constraints soft preferences personalized triage reminder"
  },
  {
   "id": "gap-3",
   "description": "Long-term adaptation to changing user roles, projects, priorities, feedback, and work patterns remains unevaluated in the admitted personalized workplace email or reminder studies; preference-drift evidence in the corpus comes primarily from recommender-system transfer domains.",
   "classification": "ACADEMIC",
   "priority": "HIGH",
   "suggested_query": "\"longitudinal personalization\" workplace email preference drift adaptive prioritization user feedback"
  },
  {
   "id": "gap-4",
   "description": "The corpus still lacks an end-to-end evaluation of briefing content selection that jointly measures omission of decision-essential work, redundant repetition, false alerts, and preservation of unresolved important state over repeated workplace cycles.",
   "classification": "ACADEMIC",
   "priority": "HIGH",
   "suggested_query": "\"longitudinal summarization\" omission redundancy false alerts unresolved state evaluation"
  },
  {
   "id": "gap-5",
   "description": "The admitted studies do not determine how reminder usefulness or likelihood of forgetting combines with perceived importance, urgency, recency, or personalized priority when selecting workplace briefing content.",
   "classification": "ACADEMIC",
   "priority": "MEDIUM",
   "suggested_query": "\"email reminder\" forgetting importance urgency recency personalized priority task selection"
  },
  {
   "id": "gap-6",
   "description": "No admitted paper evaluates topic- or work-item-level incremental briefing across multiple workplace conversations and sources; direct email summarization remains primarily thread- or conversation-level, while incremental longitudinal evidence comes from transfer domains.",
   "classification": "ACADEMIC",
   "priority": "HIGH",
   "suggested_query": "\"cross-thread summarization\" email multi-source incremental \"work item\" workplace"
  },
  {
   "id": "gap-7",
   "description": "Although the corpus contains evidence about stale reminders, epistemic uncertainty, conflicting cues, and uncertainty visualization, it does not experimentally establish how a workplace briefing presents stale, uncertain, disputed, or incompletely investigated state or how alternative presentations affect workplace decisions.",
   "classification": "ACADEMIC",
   "priority": "HIGH",
   "suggested_query": "\"uncertainty visualization\" workplace decision support stale disputed incomplete information briefing"
  },
  {
   "id": "gap-8",
   "description": "Candidate mechanisms from this corpus have not been compared in one reproducible cycle-based benchmark with chronological holdouts, independently labeled new/open/resolved/superseded state, user-specific priority labels, and explicit omission and repetition errors.",
   "classification": "ENGINEERING",
   "priority": "HIGH",
   "classification_note": "The ENGINEERING classification is intentional under the supplied taxonomy because the missing artifact is a reproducible benchmark and comparative experiment that can be constructed from code, public data, and independently authored synthetic or adversarial fixtures without first obtaining another paper. Such an engineering benchmark would not establish production-workplace representativeness; that separate question remains outside what the benchmark itself can prove."
  }
 ],
 "actionable_insights": [
  "Synthesis-derived recommendation: evaluate briefing selection cycle by cycle with independently labeled new, unchanged-open, resolved, and superseded states, and report omission, repetition, and false-alert errors separately rather than collapsing them into one summary score.",
  "Synthesis-derived recommendation: keep explicit rules and response obligations as a distinct signal class from learned importance, preference, urgency, recency, forgetting risk, and other soft ranking signals so that later evaluation can measure interactions between them rather than conflating them.",
  "Synthesis-derived recommendation: use chronological holdouts for adaptive personalization and prevent future interactions or later state from entering training, feature construction, or evaluation of earlier briefing cycles.",
  "Synthesis-derived recommendation: preserve stale, disputed, uncertain, and incompletely investigated states as explicit evaluation categories instead of silently mapping them to open or resolved.",
  "Synthesis-derived recommendation: when reminders are generated from an identified intention, include both the triggering target or context and the intended action in reminder-content experiments rather than assuming that either element alone is sufficient.",
  "Synthesis-derived recommendation: expose user correction paths for missed tasks, false positives, wrong priority, and stale state, while recording corrections as evaluation evidence for later personalization.",
  "Synthesis-derived recommendation: keep target-domain workplace results separate from transfer-domain evidence in benchmark reporting; news, clinical, recommender, cybersecurity, robot-planning, and prospective-memory results can motivate mechanisms or tests without serving as production-email accuracy estimates."
 ],
 "confidence_summary": "Confidence is high for the existence of several component-level empirical patterns: temporal-summary trade-offs, personalized email-priority gains, heterogeneous triage behavior, reminder-content effects, and incremental longitudinal processing in specific news and clinical settings. Confidence is medium for transferring hard-versus-soft constraint mechanisms, uncertainty-presentation findings, and preference-drift methods into workplace briefing because their strongest evidence comes from adjacent domains. Confidence is low for the combined target task itself: no admitted paper directly evaluates repeated cross-thread workplace briefing with work-item lifecycle state, obligation-versus-preference selection, adaptive personalization under drift, and joint omission/repetition/false-alert outcomes. The corpus therefore supports well-evidenced component principles and testable mechanisms, not validation of the integrated product behavior.",
 "limitations": [
  "The synthesis is based on the supplied reduced per-paper analyses rather than independent rereading of full papers, so conclusions are bounded by what those analyses report.",
  "The corpus spans email, news, clinical records, recommender systems, cybersecurity, robot planning, visualization, and prospective-memory experiments; adjacent-domain findings are explicitly treated as transfer evidence rather than direct workplace-briefing evidence.",
  "Several workplace-email studies evaluate message priority, thread summaries, reminders, requests, or task interfaces rather than stable cross-thread work-item identity across repeated briefing cycles.",
  "The supplied list contains 53 records and no exact-title duplicate is visible in the provided titles, so paper_count is reported as 53; identifier-level duplicate resolution was not independently performed from external metadata.",
  "The inherited handoffs from Topics 06 and 08 are project context only and are not used as evidence for any finding or gap closure in this synthesis.",
  "The corpus contains useful partial evaluations of omission, redundancy, false positives, stale reminders, drift, and uncertainty, but no single admitted study combines these dimensions under the target workplace-briefing protocol.",
  "Gap-8 remains categorized as ENGINEERING because its immediate missing artifact is a constructible benchmark and comparative experiment; success on such a benchmark would not by itself establish production-domain representativeness."
 ],
 "gap_status": [
  {
   "id": "gap-1",
   "status": "open",
   "note": "Incremental news and clinical summarization provide transfer evidence, but no admitted study evaluates repeated workplace briefing with explicit new, unchanged-open, resolved, and superseded work-item states.",
   "evidence": [
    "doi-10-18653-v1-2024-acl-long-390",
    "doi-10-64898-2025-11-28-25341233",
    "doi-10-1145-383952-383954"
   ]
  },
  {
   "id": "gap-2",
   "status": "open",
   "note": "The corpus separately studies personalized priority, constrained ranking, hard-versus-soft planning constraints, reminders, and importance, but no admitted workplace study experimentally combines explicit response obligations or user rules with soft personalization signals.",
   "evidence": [
    "manual-50ed5dc808",
    "2403.19795",
    "2202.07088",
    "2403.01365",
    "doi-10-1093-jcmc-zmac001"
   ]
  },
  {
   "id": "gap-3",
   "status": "open",
   "note": "Preference-drift adaptation is directly evaluated in recommender systems, but long-term adaptive personalization under changing workplace roles, projects, priorities, and feedback is not evaluated in the admitted email or reminder studies.",
   "evidence": [
    "doi-10-1016-j-eswa-2021-114890",
    "doi-10-1016-j-eswa-2021-115626",
    "doi-10-1109-access-2022-3182390",
    "doi-10-1145-2523813"
   ]
  },
  {
   "id": "gap-4",
   "status": "open",
   "note": "Temporal-summary evaluations measure combinations of novelty, coverage, redundancy, latency, and off-event material, and email-assistance work measures false positives and task outcomes, but no admitted study jointly evaluates omission, repetition, false alerts, and unresolved-state preservation across repeated workplace briefing cycles.",
   "evidence": [
    "doi-10-1145-383952-383954",
    "doi-10-6028-nist-sp-500-302-tempsumm-overview",
    "manual-bdce973227"
   ]
  },
  {
   "id": "gap-5",
   "status": "open",
   "note": "The corpus separately supplies evidence on perceived importance and urgency, forgotten-task reminder value, prospective-memory importance, and reminder-use determinants, but it does not evaluate their joint contribution to workplace briefing selection.",
   "evidence": [
    "2403.01365",
    "doi-10-1093-jcmc-zmac001",
    "doi-10-3389-fpsyg-2014-00657",
    "doi-10-1186-s41235-019-0195-y",
    "doi-10-3758-s13421-025-01708-x"
   ]
  },
  {
   "id": "gap-6",
   "status": "open",
   "note": "Email summarization evidence remains thread- or conversation-centered, while incremental longitudinal processing is demonstrated in news and clinical transfer domains rather than cross-thread workplace work items.",
   "evidence": [
    "2107.14691",
    "manual-c2f56a571b",
    "doi-10-18653-v1-2024-acl-long-390",
    "doi-10-64898-2025-11-28-25341233"
   ]
  },
  {
   "id": "gap-7",
   "status": "open",
   "note": "Stale reminders, uncertainty visualization, epistemic uncertainty, and conflicting cues are empirically studied, but no admitted paper compares presentation strategies for stale, disputed, uncertain, or incompletely investigated states in workplace briefings.",
   "evidence": [
    "2403.01365",
    "doi-10-1016-j-cag-2014-02-006",
    "doi-10-1098-rsos-181870",
    "doi-10-1609-icwsm-v12i1-15014"
   ]
  },
  {
   "id": "gap-8",
   "status": "open",
   "note": "No supplied study provides the specified unified cycle-based benchmark. The gap remains ENGINEERING because constructing and running the benchmark is feasible as an engineering experiment using independently authored gold labels and chronological fixtures without requiring another publication; production representativeness would remain unproven.",
   "evidence": [
    "doi-10-6028-nist-sp-500-302-tempsumm-overview",
    "doi-10-1145-383952-383954",
    "manual-50ed5dc808",
    "doi-10-1145-3705328-3748164"
   ]
  }
 ]
}

Per-paper analyses (reduced to questions and top findings to fit the size cap):
[
 {
  "paper_id": "1301.6707",
  "title": "Attention-Sensitive Alerting",
  "research_question": "How can a notification system decide when and how to alert users about incoming email by balancing the expected value of timely information against context-sensitive interruption costs?",
  "key_findings": [
   "A linear SVM trained on approximately 1,500 labeled messages discriminated between high- and low-criticality email on a held-out set of 500 hand-selected messages, with performance reported as an ROC tradeoff rather than a single accuracy value.",
   "Automated expected-criticality scores correlated 0.9 with one author's manual criticality ratings for 200 messages received over three days.",
   "The PRIORITIES prototypes personalized criticality prediction using examples from a user's own email and applied the learned classifier to incoming messages in real time while also observing activity, acoustics, and calendar information.",
   "The compound-alert formulation explicitly models grouping several newly arrived messages into one interruption and increases interruption cost with informational complexity, but it assumes message values are independent and the authors warn that this can overestimate value when messages concern related content.",
   "The proposed NEVA rule says an alert should be sent when its expected informational value exceeds its expected interruption cost, but this paper does not report a controlled user-outcome experiment comparing that alerting policy with alternatives."
  ]
 },
 {
  "paper_id": "2107.14691",
  "title": "EmailSum: Abstractive Email Thread Summarization",
  "research_question": "How well do extractive, abstractive, transfer, semi-supervised, and hierarchical models summarize multi-message email threads, and what dataset and evaluation challenges distinguish email-thread summarization from conventional document summarization?",
  "key_findings": [
   "EmailSum provides 2,549 email threads with both short and long human-written abstractive summaries, supplying a substantially larger benchmark than the earlier 40-thread BC3 email summarization corpus discussed by the authors.",
   "Treating an entire email thread as one document and fine-tuning T5 provides a strong baseline; transferring from existing news or dialogue summarization datasets yields little benefit, and the proposed hierarchical T5 provides only marginal gains.",
   "Semi-supervised training on unlabeled email threads improves several automatic ROUGE results, but those improvements do not translate into superior human preference over the base T5 model.",
   "Current models frequently fail on discourse-critical information such as the sender's main intention and the correct roles or attribution of senders and receivers, creating both salience and faithfulness errors.",
   "Model performance decreases as the number of emails in a thread increases, indicating that longer conversational context remains harder to summarize."
  ]
 },
 {
  "paper_id": "2109.06896",
  "title": "Decision-Focused Summarization",
  "research_question": "Can summaries be selected specifically to support a downstream decision by optimizing both faithfulness to a predictive model's full-text decision and representativeness of the decision evidence in the input?",
  "key_findings": [
   "DecSum achieved much closer agreement with the full-text model prediction than text-only summarization and attribution baselines, with MSE-to-full of 0.0005 for the all-components variant versus roughly 0.34 to 0.54 for the main baselines.",
   "Explicitly optimizing representativeness significantly improved how well selected sentences covered the distribution of sentence-level decision evidence, measured by Wasserstein distance.",
   "DecSum selected a broader mix of positive, neutral, and negative evidence than the tested text-only systems, while PreSumm and BART tended toward positive sentences and attribution methods tended to omit neutral evidence.",
   "DecSum produced strong textual non-redundancy but scored worse on grammaticality and coherence than conventional text-focused summarizers.",
   "On the simplified model decision task, DecSum summaries preserved 76.1 percent model accuracy, essentially matching the 76.0 percent result from full text and exceeding the tested summarization baselines."
  ]
 },
 {
  "paper_id": "2202.07088",
  "title": "Scaling up Ranking under Constraints for Live Recommendations by Replacing Optimization with Prediction",
  "research_question": "Can constrained personalized ranking be made fast enough for live recommendation by predicting per-user optimization shadow prices instead of solving the full constrained optimization problem online?",
  "key_findings": [
   "Predicting personalized shadow prices substantially reduces online computation while retaining constraint compliance close to the per-user optimization solution.",
   "The KNeighbors shadow-price approach stays within the paper's 50 millisecond serving-time requirement even when ranking 1,000 items subject to at least five constraints.",
   "A single mean shadow-price vector performs worse than personalized shadow-price prediction on MovieLens, providing evidence that modeling user heterogeneity can improve constraint compliance.",
   "On YOW News, personalized and mean shadow-price prediction have similar constraint-compliance performance, so the benefit of personalization is dataset-dependent.",
   "Ignoring optimization produces the worst constraint compliance, whereas utility differences among constrained methods are generally small."
  ]
 },
 {
  "paper_id": "2208.03828",
  "title": "How Do Viewers Synthesize Conflicting Information from Data Visualizations?",
  "research_question": "How do people combine sequentially presented, potentially conflicting graphical evidence, and how are their synthesized judgments affected by the direction, magnitude, context, and presentation order of the evidence?",
  "key_findings": [
   "Across experiments, when both line-chart slopes pointed in the same direction, participants placed greater weight on the weaker, less steep relationship.",
   "When the two slopes pointed in opposite directions, participants consistently weighted the positive relationship more strongly than the negative relationship.",
   "As disagreement between the two slopes increased, synthesized judgments tended to move away from their arithmetic average and toward the stronger slope.",
   "The authors found no significant effect of whether the stronger slope was presented first or second in Experiment 1, Experiments 2A and 2B, or Experiment 3.",
   "Different elicitation methods were generally consistent but not identical; some statistically significant differences appeared between line-drawing and text-box responses, showing that measured synthesis can depend on response modality."
  ]
 },
 {
  "paper_id": "2403.01365",
  "title": "AI-Powered Reminders for Collaborative Tasks: Experiences and Futures",
  "research_question": "How do knowledge workers use and value AI-generated reminders for collaborative email tasks, what information should such systems surface, how does workstyle affect perceived value, and how should users interact with future reminder systems?",
  "key_findings": [
   "The most common positive theme was the value of receiving an extra reminder or being reminded about a forgotten task: 16 of 45 validating-survey respondents mentioned this theme, with most of those respondents rating the briefing as valuable.",
   "Staleness and incorrect state are material problems for briefing systems: 12 of 45 validating-survey participants described the system as not presenting accurate or sufficiently up-to-date information.",
   "Participants most commonly reported forgetting low-importance or non-urgent tasks, ad hoc tasks or meetings, and small low-effort tasks, implying that prioritizing only high-urgency items can miss tasks for which reminders have high marginal value.",
   "The authors explicitly argue that future reminder systems should reconsider prioritizing only urgent or high-importance tasks and should account for the likelihood that a task will otherwise be forgotten.",
   "Positive interaction with the briefing is strongly associated with perceived value, while reported workstyle variables associated with greater interaction include communicating about tasks via email, creating tasks from emails, having fewer scheduled meetings, and delegating less."
  ]
 },
 {
  "paper_id": "2403.19795",
  "title": "Learning Human Preferences Over Robot Behavior as Soft Planning Constraints",
  "research_question": "Can preferences over robot behavior be represented as soft planning constraints and inferred from noisy pairwise trajectory choices while keeping task requirements as hard constraints?",
  "key_findings": [
   "The framework explicitly separates mandatory task goals from nonmandatory behavioral preferences by representing the latter as soft PDDL constraints with costs.",
   "The learned models could infer the three simulated preference types under noisy user choices, although increasing choice noise reduced absolute prediction performance.",
   "When both training and evaluation were noise-free, the learned approach underperformed the perfectly rational baseline, whereas models trained and tested with noisy choices performed similarly to or better than that baseline at the corresponding noise levels.",
   "Training with a small amount of choice noise generalized better to noisy evaluation data than training without noise, while increasing training noise further did not produce additional gains.",
   "Distribution-based supervision was often similar to or better than single-target supervision under low or no training noise, but this advantage was not universal at higher noise levels."
  ]
 },
 {
  "paper_id": "2609.02465",
  "title": "Can Risk-Based Alerting Mitigate Cybersecurity Alert Fatigue?",
  "research_question": "Can combinations of interpretable risk-based alerting hypotheses reliably prioritize true cybersecurity alerts over false alerts across heterogeneous environments strongly enough to reduce analyst workload?",
  "key_findings": [
   "The optimized leave-one-out weighted pipeline achieved mean AUROC 0.92 with standard deviation 0.09 across eight datasets, compared with 0.72 and standard deviation 0.21 for straightforward rule-severity prioritization.",
   "Rule Level, Accumulation, and Variety each distinguished true from false alerts significantly above chance across datasets, whereas Rarity and Aperiodicity did not show significant above-chance aggregate performance.",
   "Weights obtained from the other datasets generalized well in leave-one-out evaluation, suggesting that the combined prioritization strategy was relatively robust to changes in environment, alert source, and attack.",
   "The broader multi-metric evaluation was mostly above corresponding no-skill levels, although individual datasets exposed weaknesses that AUROC alone did not capture.",
   "Using trailing rather than centered temporal windows reduced mean AUROC for the reference pipeline by about 17%, exposing a trade-off between immediate alerting and using future neighboring alerts for stronger prioritization."
  ]
 },
 {
  "paper_id": "doi-10-1007-978-3-319-67684-5-24",
  "title": "RemindMe: Plugging a Reminder Manager into Email for Enhancing Workplace Responsiveness",
  "research_question": "Can a reminder-management layer integrated with enterprise email reduce the cognitive burden of tracking incoming and outgoing workplace requests and improve reminder handling over time?",
  "key_findings": [
   "The system is explicitly designed around incoming and outgoing email requests rather than general email organization.",
   "RemindMe combines automatic reminder creation with a learning mechanism intended to improve reminder behavior over time.",
   "Reminder delivery is integrated into a user-facing email interface rather than implemented as a separate task-management application.",
   "The browser-plugin architecture allows the reminder functionality to be added on top of an existing enterprise webmail system.",
   "The accessible source establishes a design goal of reducing cognitive overhead but does not provide quantitative evidence that RemindMe actually improves workplace responsiveness."
  ]
 },
 {
  "paper_id": "doi-10-1016-j-cag-2014-02-006",
  "title": "Effects of visualizing uncertainty on decision-making in a target identification scenario",
  "research_question": "How does explicitly visualizing uncertainty in spatio-temporal sensor information affect expert target-identification and prioritization decisions under time pressure?",
  "key_findings": [
   "Participants shown uncertainty information required significantly fewer attempts before making their final target identification.",
   "The uncertainty-visualization group assigned significantly higher priority values and chose more hostile or suspect target identities.",
   "Displaying uncertainty did not significantly increase expressed workload or average decision time.",
   "Uncertainty visualization did not produce a significant improvement in classification performance measured through true positives, false negatives, and false positives.",
   "Participants' expressed confidence was not significantly changed by the uncertainty visualization."
  ]
 },
 {
  "paper_id": "doi-10-1016-j-eswa-2021-114890",
  "title": "A case study of batch and incremental recommender systems in supermarket data under concept drifts and cold start",
  "research_question": "How do batch and streaming collaborative-filtering recommender systems compare on real supermarket interaction data affected by concept drift and cold-start conditions?",
  "key_findings": [
   "Streaming recommenders achieved improvements of up to 21% over corresponding batch approaches in the studied supermarket data.",
   "ISGD significantly outperformed its batch SVD counterpart on RECALL@10 across all three dataset variants at the reported 95% confidence level.",
   "IBPRMF improved RECALL@10 by as much as 21% over BPRMF in the preprocessed datasets, where abrupt changes and cold-start effects were more visible.",
   "In the original dataset, IBPRMF's decreases at RECALL@10 and RECALL@20 were not statistically significant and were associated with volatile runs in which the model did not always converge.",
   "Windowed prequential evaluation showed that incrementally updated models adapted more effectively when abrupt distribution changes occurred, supporting the value of continual updating under drift and cold start."
  ]
 },
 {
  "paper_id": "doi-10-1016-j-eswa-2021-115626",
  "title": "A novel temporal recommender system based on multiple transitions in user preference drift and topic review evolution",
  "research_question": "Can a temporal recommender that jointly models multiple transitions in user-preference drift, time-based forgetting, and evolving review topics improve recommendations under changing preferences and sparse ratings?",
  "key_findings": [
   "MTUPD explicitly models user-preference drift across multiple successive transitions rather than treating temporal change as a single transition.",
   "A forgetting-time function is used to attenuate the influence of older observations when estimating current user preferences.",
   "Review text is incorporated through time-specific topic modeling so that evolving textual topics provide auxiliary information when rating observations are sparse.",
   "The model jointly represents rating dynamics and review-topic evolution instead of relying only on timestamped ratings.",
   "Experiments across eight datasets report that MTUPD outperforms the dynamic collaborative-filtering models used as comparators."
  ]
 },
 {
  "paper_id": "doi-10-1016-j-knosys-2013-02-015",
  "title": "Exploiting relevance, coverage, and novelty for query-focused multi-document summarization",
  "research_question": "Can query-focused multi-document summaries be improved by jointly modeling dependent relevance, content coverage, novelty, and topic balance rather than treating sentence relevance independently?",
  "key_findings": [
   "The paper argues that sentence utility is dependent on what has already been selected or seen, and PRCN therefore replaces the usual independent-relevance assumption with probabilistic dependent relevance.",
   "PRCN jointly represents relevance, topic coverage, and novelty rather than optimizing query relevance alone.",
   "The sentence-selection stage uses a greedy balancing procedure intended to preserve suitable proportions of document and query topics while limiting redundancy.",
   "Experiments on DUC 2005 and DUC 2006 report that PRCN outperforms the compared methods on ROUGE-2 and ROUGE-W by a statistically described significant margin.",
   "The approach is unsupervised and extractive, so its coverage and novelty decisions are made by selecting source sentences rather than generating new text."
  ]
 },
 {
  "paper_id": "doi-10-1093-jcmc-zmac001",
  "title": "Measurement of Perceived Importance and Urgency of Email: An Employees’ Perspective",
  "research_question": "What cues do employees use to judge received email as important or urgent, how can those perceptions be measured reliably, and how are the resulting constructs associated with email overload, work-role overload, and stress?",
  "key_findings": [
   "Employees' judgments did not support three cleanly separate constructs for important, urgent, and important-and-urgent email; the validated structure contained important email and important-and-urgent email, without a distinct urgent-only construct.",
   "Important-but-not-urgent messages were characterized primarily by their relevance to the employee's own work, whereas important-and-urgent messages commonly involved consequential matters, key stakeholders, or adverse consequences from delay.",
   "The resulting scales showed acceptable internal consistency and convergent validity, with reported Cronbach's alpha values of about 0.84 for important email and 0.88 for important-and-urgent email.",
   "Both perceived important email and important-and-urgent email had positive statistically significant associations with work-role overload in the structural model.",
   "Email overload and time spent on email were associated with work-role overload, while raw email volume was not a statistically significant predictor in the reported model."
  ]
 },
 {
  "paper_id": "doi-10-1098-rsos-181870",
  "title": "Communicating uncertainty about facts, numbers and science",
  "research_question": "How should epistemic uncertainty about facts, numerical quantities, and scientific hypotheses be classified and expressed, and what does existing evidence indicate about its effects on understanding, affect, trust, and decision-making?",
  "key_findings": [
   "The framework distinguishes three primary objects of epistemic uncertainty: categorical facts, continuous numerical quantities, and scientific models or hypotheses.",
   "The paper distinguishes direct uncertainty about an object from indirect uncertainty concerning the quality or adequacy of the evidence underlying a claim.",
   "The review identifies nine progressively less precise forms for expressing direct absolute uncertainty.",
   "Existing evidence does not support a simple rule that acknowledging epistemic uncertainty necessarily damages audience trust.",
   "Effects of uncertainty communication differ across audiences and depend on how uncertainty is expressed and formatted."
  ]
 },
 {
  "paper_id": "doi-10-1109-access-2022-3182390",
  "title": "An End-to-End Personalized Preference Drift Aware Sequential Recommender System With Optimal Item Utilization",
  "research_question": "Can a sequential recommender improve next-item prediction by detecting personalized preference drift, soft-clustering item characteristics, and selecting only historical interactions relevant to the user's current preference?",
  "key_findings": [
   "PPD+ consistently outperformed most evaluated baselines across the three benchmark datasets on NDCG, hit rate, and mean reciprocal rank.",
   "When competing models were constrained to use equal percentages of historical items, PPD+ still outperformed the baselines on most metrics across all three datasets, supporting the value of its history-selection and grouping mechanism rather than merely the amount of history consumed.",
   "Using more historical interactions was not uniformly beneficial: the highest NDCG@10 usually did not occur at the largest utilization percentage, and PPD+ showed negative, flat, or positive utilization trends depending on the dataset.",
   "A zero cosine-similarity threshold for retaining past subsequences outperformed variants based on the mean similarity or mean plus standard deviation on most validation metrics across the datasets.",
   "The experiments demonstrate better offline next-item prediction from a mechanism intended to respond to changing preferences, but they do not directly validate detected drift points against independently labeled ground-truth preference changes."
  ]
 },
 {
  "paper_id": "doi-10-1109-fuzz-ieee-2016-7737835",
  "title": "Fuzzy user-interest drift detection based recommender systems",
  "research_question": "Can fuzzy modeling of individual user-interest consistency combined with concept-drift detection improve recommendation accuracy when user interests evolve and item-interest information is incomplete or vague?",
  "key_findings": [
   "The paper treats user interests as time-varying rather than stationary and argues that ignoring such drift degrades recommendation accuracy.",
   "Interest drift is modeled separately for individual users because users may change preferences in different directions.",
   "Fuzzy-set modeling is used to address incomplete and vague representations of item features and user interests.",
   "A drift-detection mechanism based on concept-drift methods is integrated with recommendation generation rather than relying on a static interest model.",
   "Experiments on synthetic and MovieLens data report improved recommendation performance for the proposed approach according to mean absolute error."
  ]
 },
 {
  "paper_id": "doi-10-1136-amiajnl-2014-002945",
  "title": "HARVEST, a longitudinal patient record summarizer",
  "research_question": "Can an interactive, problem-oriented longitudinal summarizer built from clinical notes support physicians in reviewing complex patient histories without degrading task performance or efficiency relative to an established electronic record interface?",
  "key_findings": [
   "Physicians achieved similar task-questionnaire performance with HARVEST and the established iNYP system; the overall difference was not statistically significant.",
   "Task-completion time did not differ significantly between HARVEST and iNYP, although HARVEST tended to take somewhat longer in the study.",
   "Three quarters of participants said they would definitely use HARVEST again, and most participants rated its timeline, problem cloud, and note-access components as helpful.",
   "HARVEST links salient longitudinal problems back to the clinical notes and time periods in which those problems were documented.",
   "Simple frequency-based salience can be misleading because frequently documented concepts are not necessarily the most clinically important."
  ]
 },
 {
  "paper_id": "doi-10-1145-1056808-1057071",
  "title": "Beyond “From” and “Received”: Exploring the Dynamics of Email Triage",
  "research_question": "How do information workers actually triage accumulated email, what determines which messages they handle first, and what additional information could email interfaces expose to support that process?",
  "key_findings": [
   "Unread inbox messages and messages received today were rated the most important categories to include during triage, both averaging 4.4 on the study's five-point scale.",
   "Users did not share a single priority policy: 19 percent reported priority-only triage, 30 percent sequential-only triage, and 15 percent reported using both approaches.",
   "Multi-pass triage was more common than single-pass triage, with 47 percent reporting multi-pass only versus 17 percent single-pass only under the authors' combined-question criterion.",
   "Many multi-pass users first removed low-importance or junk messages because they were quick to process and because clearing them made important messages easier to find.",
   "Message importance depended substantially on the user's current social and work context, including schedule, close collaborators, active projects, and project role."
  ]
 },
 {
  "paper_id": "doi-10-1145-1557019-1557124",
  "title": "Mining social networks for personalized email prioritization",
  "research_question": "Can features derived from each user's personal email social network, including semi-supervised propagation of importance, improve personalized email-priority prediction when only limited labeled email is available?",
  "key_findings": [
   "Adding induced social-network information to conventional email features reduced priority-prediction error for personalized models.",
   "The complete combination of basic, clustering, social-importance, and importance-propagation features reduced average macro MAE from about 0.8510 to 0.7449, corresponding to roughly a 14% relative error reduction.",
   "The complete social-feature combination reduced micro-averaged MAE from about 0.7759 to 0.5909, reported as approximately a 31% relative error reduction.",
   "Social-network-derived information was particularly useful when only a limited number of explicit priority judgments were available, although the best feature combination varied with training-set size.",
   "The design permits each person's prioritizer to be learned from that person's own email and judgments without pooling private email across users."
  ]
 },
 {
  "paper_id": "doi-10-1145-2063576-2063683",
  "title": "Modeling Personalized Email Prioritization: Classification-based and Regression-based Approaches",
  "research_question": "For personalized five-level email priority prediction, do ordinal-regression models or classification-based models better capture users' judgments, and under what data assumptions does each modeling strategy work best?",
  "key_findings": [
   "On personalized email data, the order-based majority-voting classification approach significantly outperformed support-vector ordinal regression, despite the apparently ordinal nature of the five priority labels.",
   "With 150 training messages, the reported macro MAE was approximately 0.8689 for the order-based majority-voting method versus 1.0480 for SVOR and 1.1560 for the constant baseline.",
   "With 150 training messages, micro MAE was approximately 0.7907 for the order-based majority-voting method, compared with 1.0259 for SVOR and 1.0887 for the baseline.",
   "On the seven UCI-derived ordinal benchmarks, the result reversed: SVOR performed best across the evaluated training sizes, showing that the email result was not a general failure of ordinal regression.",
   "The authors attribute the email result to violations of the restrictive single-model or parallel-boundary assumptions underlying ordinal regression, while flexible classifiers can model different boundaries between priority regions."
  ]
 },
 {
  "paper_id": "doi-10-1145-2523813",
  "title": "A Survey on Concept Drift Adaptation",
  "research_question": "How can online supervised learning systems characterize, detect, adapt to, and evaluate changes in the relationship between inputs and targets over evolving data streams?",
  "key_findings": [
   "Concept drift includes changes in the target distribution conditional on observed inputs, and changing user interests in a news stream are presented as a canonical example.",
   "Adaptive learning can be decomposed into memory, change detection, learning, and loss-estimation modules, allowing different adaptation strategies to be combined modularly.",
   "Shorter recent-data windows react faster to changes but can be less stable, whereas larger windows improve stability in stationary periods while adapting more slowly.",
   "Recency alone is not a reliable proxy for relevance when data are noisy or concepts recur, so simple window-based forgetting can discard useful older information.",
   "Explicit change detection provides information about when and how a process changes beyond the implicit adaptation obtained from continuously updating an online model."
  ]
 },
 {
  "paper_id": "doi-10-1145-290941-291025",
  "title": "The Use of MMR, Diversity-Based Reranking for Reordering Documents and Producing Summaries",
  "research_question": "Can retrieval and summarization improve usefulness by explicitly balancing query relevance against novelty so that selected documents or passages remain relevant while avoiding redundant information?",
  "key_findings": [
   "MMR provides an explicit tunable mechanism for balancing query relevance with information novelty relative to items already selected, directly targeting redundant retrieval and summary content.",
   "In the five-user document-reranking pilot, most users preferred the broader and more diverse MMR presentation, and 80% selected MMR when subsequently choosing a search method.",
   "The MMR-based single-document summarizer obtained an F-score of 0.73 for query-relevant summaries and 70% accuracy on informative summaries in the reported SUMMAC evaluation, although the authors caution that differing system parameters limit direct comparison.",
   "For the reported single-document sentence-selection experiment, relevance precision did not differ significantly among lambda values of 1.0, 0.7, and 0.3, suggesting some diversity can be introduced without a statistically significant relevance loss in that experiment.",
   "The authors report that redundancy becomes particularly important for longer documents and multi-document collections, and their preliminary multi-document observations indicate that MMR reduces or eliminates duplicate and near-duplicate passages."
  ]
 },
 {
  "paper_id": "doi-10-1145-2998181-2998251",
  "title": "What Did I Ask You to Do, by When, and for Whom?: Passion and Compassion in Request Management",
  "research_question": "How do knowledge workers manage person-to-person requests across organizational contexts and communication channels, and what implications do those practices have for request-management system design?",
  "key_findings": [
   "Request management combines personal task management with collaborative-work concerns because requests carry both interpersonal relationships and organizational accountability.",
   "Person-to-person requests are scattered across multiple communication channels, making them difficult for workers to aggregate into a coherent view.",
   "Prioritizing requests is difficult and request-management practices differ according to work context.",
   "Knowledge workers can expend substantial effort managing requests while also taking account of the burden and efforts of their colleagues.",
   "The authors propose treating requests as socially implicated work objects and derive design implications for services intended to support request management."
  ]
 },
 {
  "paper_id": "doi-10-1145-3705328-3748164",
  "title": "Time to Split: Exploring Data Splitting Strategies for Offline Evaluation of Sequential Recommenders",
  "research_question": "How do leave-one-out and alternative global temporal splitting, target-selection, and validation strategies affect realism, metric consistency, model ranking, and model selection in offline evaluation of sequential recommender systems?",
  "key_findings": [
   "LOO can violate the global interaction timeline and was less aligned with the temporally separated Successive evaluation than several GTS alternatives, while changes in split and target definition could materially change model rankings.",
   "GTS Random had the strongest average agreement with GTS Successive, while GTS Last also showed high agreement and offered a deterministic, lower-cost alternative to Successive evaluation.",
   "GTS All showed especially poor agreement with Successive evaluation because its set-valued target does not match standard next-item prediction, and GTS First was weakened by atypical time gaps around the first post-cutoff interaction.",
   "The choice of splitting protocol created unstable rankings across models on most evaluated datasets, demonstrating that evaluation protocol can affect conclusions about which system performs best.",
   "Validation constructed with a matching global temporal split generally aligned most strongly with GTS test performance; for GTS Last, GT Last validation had the highest correlations on five of eight datasets."
  ]
 },
 {
  "paper_id": "doi-10-1145-383952-383954",
  "title": "Temporal Summaries of News Topics",
  "research_question": "How can an online system repeatedly summarize a developing news topic so that each update covers useful new events while avoiding previously reported, redundant, and off-event information?",
  "key_findings": [
   "The evaluation explicitly separates useful content, novel event coverage, and off-event material, with recall measuring coverage of relevant events and precision penalizing redundant or non-useful selections; this provides a direct laboratory analogue of jointly measuring omission, repetition, and irrelevant-update errors.",
   "The corpus contains 22 TDT-2 topics split evenly into training and test sets, with 343 annotated events across 17,049 sentences, enabling event-level temporal-summary evaluation.",
   "For usefulness ranking on the test topics, the probabilistic usefulness methods and the simple round-robin baseline performed similarly, and the authors conclude that the probabilistic approaches did not clearly outperform round robin.",
   "Novelty models looked better than several baselines under a novelty-only measure, but once off-event sentences were accounted for their performance degraded and round robin became the strongest comparator, leading the authors to state that the novelty models were inadequate for the task.",
   "The expected superiority of combining the strongest usefulness and novelty variants was not observed; on held-out topics the combined variants had nearly identical exact average nu-precision and were roughly comparable to round robin."
  ]
 },
 {
  "paper_id": "doi-10-1145-634067-634150",
  "title": "Supporting Prospective Information in Email",
  "research_question": "How do people use email to manage future actions and time-sensitive information, what deficiencies in email interfaces hinder this prospective-memory function, and how do these practices vary with users' organizational habits?",
  "key_findings": [
   "Fifteen of the 19 interviewed participants retained prospective messages in their inbox, showing that the inbox commonly served as storage for information about future actions and events.",
   "Fifteen of 19 interviewees also used email as a reminder mechanism for email-related actions, other tasks, or future events.",
   "Managing prospective information often required repeated inbox review or other manual techniques for keeping actionable messages salient, creating substantial monitoring and scanning overhead.",
   "Participants who retained prospective messages in email also tended to search or consult email more often outside the immediate context of replying or composing, consistent with active monitoring of pending information.",
   "Prospective-email practices were statistically associated with other organizational habits, supporting the argument that tools for pending information should accommodate different user styles rather than assume one universal workflow."
  ]
 },
 {
  "paper_id": "doi-10-1145-642611-642672",
  "title": "Taking Email to Task: The Design and Evaluation of a Task Management Centered Email Tool",
  "research_question": "Can redesigning email around task-management activities, threaded task contexts, task metadata, and overview mechanisms better support users who manage work through email?",
  "key_findings": [
   "Organizing email and related material into threaded, task-centric collections was well received and helped preserve the context of ongoing work.",
   "Participants rated organizing and deleting content within the thrask model at an average of 4.2 on a five-point love-to-hate scale oriented so that 5 represented strong approval.",
   "Deadlines, reminders, and action indicators were among the more successful task-centric metadata features, receiving ratings around four and helping users track obligations and dependencies.",
   "Warning-bar aggregation helped users identify which task collection contained the most urgent item and therefore supported prioritization.",
   "Action indicators conveyed that work remained to be done but did not adequately communicate the relative importance of different actions, limiting their usefulness for planning."
  ]
 },
 {
  "paper_id": "doi-10-1155-2016-1340973",
  "title": "Mining Sequential Update Summarization with Hierarchical Text Analysis",
  "research_question": "Can a hierarchical combination of time-sensitive retrieval, topic-level keyword mining, and sentence scoring produce useful, novel, timely, and sufficiently comprehensive updates for rapidly developing events?",
  "key_findings": [
   "The system explicitly treats novelty and timeliness as first-class properties of sequential updates and suppresses duplicate sentences before submission.",
   "Evaluation separates a precision-like notion of useful nonredundant information from a recall-like notion of nugget coverage, with latency-sensitive variants of both.",
   "The KS scorer reaches expected gain 0.149 and expected latency gain 0.136, equal to the best reported values shown in the paper's TREC comparison table.",
   "KLP provides substantially higher comprehensiveness than KS, while KS provides substantially higher expected gain, demonstrating a direct accuracy-versus-coverage tradeoff.",
   "Within KLP variants, changing sentence-length and position weights has little effect compared with keyword diversity, which the authors identify as the more influential feature."
  ]
 },
 {
  "paper_id": "doi-10-1177-1071181322661236",
  "title": "Strategy-Specific Decision Making with Incomplete Information",
  "research_question": "How do the amount and distribution of incomplete information affect decision performance and strategy adaptation across heuristic and analytic decision environments?",
  "key_findings": [
   "The amount of information presented significantly affected decision performance across all three decision environments.",
   "How information was structured within each cue across decision options significantly affected performance in all three environments.",
   "Participants' information-access patterns indicate that better decision performance is associated with adapting decision strategy to the environment."
  ]
 },
 {
  "paper_id": "doi-10-1186-s41235-019-0195-y",
  "title": "Confidence guides spontaneous cognitive offloading",
  "research_question": "Does confidence in unaided prospective-memory ability guide people's use of external reminders even when the reminder strategy must be generated spontaneously rather than explicitly instructed?",
  "key_findings": [
   "Participants who were never explicitly taught the reminder strategy nevertheless spontaneously used it, although their mean offloading rate was lower than that of participants who had been instructed about it.",
   "Allowing offloading improved delayed-intention performance in both groups, with average hit rate increasing from Phase 1 to Phase 2.",
   "Lower confidence in unaided Phase 1 performance predicted greater Phase 2 offloading in both the instructed and spontaneous groups, even when objective Phase 1 performance was included as a predictor.",
   "A general claim that objective memory ability robustly determines reminder use was not supported across groups; objective performance showed a negative relationship with offloading in the spontaneous group but not in the instructed group.",
   "Participants updated later confidence partly on the basis of earlier task performance, indicating some adaptation of metacognitive estimates from experience."
  ]
 },
 {
  "paper_id": "doi-10-1207-s15327051hci2001-2-3",
  "title": "Supporting Collaborative Task Management in E-mail",
  "research_question": "How can email interfaces better support collaborative task management, particularly remembering outstanding activities, finding prior task-related messages, and accessing distributed task information?",
  "key_findings": [
   "Users commonly appropriate their inboxes as informal task-management systems, but chronological message organization becomes inadequate for collaborative tasks that persist over time and span multiple exchanges.",
   "Dedicated to-do folders imposed enough filing and remembering overhead that almost all observed users who had tried them abandoned the practice.",
   "TeleNotes users made active use of spatial task piles and very short personal reminder annotations, showing value in separating task cues from the original message chronology.",
   "TeleNotes did not replace conventional chronological email; users continued using their ordinary mail interface for recent events while using the prototype selectively for salient or longer-running tasks.",
   "In the controlled evaluation, ContactMap produced higher task success than participants' normal email interfaces, with a reported interface effect of F(1,112)=23.52, p<0.0001."
  ]
 },
 {
  "paper_id": "doi-10-1609-icwsm-v12i1-15014",
  "title": "Can You Verifi This? Studying Uncertainty and Decision-Making About Misinformation Using Visual Analytics",
  "research_question": "How do confirmation-bias instructions and uncertainty from conflicting information cues affect people's judgments of misinformation when using a visual-analytics system?",
  "key_findings": [
   "The three confirmation-bias treatment conditions did not differ significantly in overall classification accuracy, real-versus-fake labeling rates or time spent interacting with the interface.",
   "Cue values and account identity were important predictors of participant decisions, indicating that the evidence configuration mattered more than the experimental instruction condition.",
   "Opinionated-language, fear and social-network cues were among the strongest cues associated with correct decisions when used consistently.",
   "Self-reported confidence had no significant relationship with accuracy or fake-account decisions after the other regression variables were considered.",
   "Accounts with cues pointing in conflicting directions produced greater uncertainty and more inaccurate judgments than easier accounts with mutually reinforcing cues."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-2007-sigdial-1-4",
  "title": "Detecting and Summarizing Action Items in Multi-Party Dialogue",
  "research_question": "Can action items in multi-party meetings be detected more accurately by modeling their dialogue structure and then summarized by extracting task and timeframe phrases using syntactic and semantic information?",
  "key_findings": [
   "The structured subdialogue detector outperformed a flat action-item classifier on manual transcripts, with overlap F1 of 0.45 versus 0.35.",
   "Action-item utterances were extremely sparse, with only about 1.4 percent of utterances receiving any action-item dialogue-act label.",
   "ASR errors caused a substantial degradation in action-item detection, reducing overlap F1 by roughly 8 to 9 absolute percentage points, although structured detection remained above the flat baseline in absolute performance.",
   "For timeframe summarization, semantic and lexical-head features plus temporal-expression information improved fragment ranking to F1 0.51, above the 1-best utterance baseline of 0.39 and TIMEX-only baseline of 0.31.",
   "For task-description phrases, none of the tested feature sets outperformed the full 1-best utterance baseline in F1, despite some gains in precision."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-2020-acl-main-122",
  "title": "Examining the State-of-the-Art in News Timeline Summarization",
  "research_question": "Which high-level strategies for news timeline summarization perform best under end-to-end temporal evaluation, and what dataset characteristics make longitudinal timeline construction difficult?",
  "key_findings": [
   "The Datewise system achieved the highest alignment-based ROUGE results among evaluated non-oracle methods on all three benchmark datasets.",
   "Datewise did not consistently dominate in Date-F1, indicating that much of its advantage came from sentence selection and summarization rather than superior date prediction alone.",
   "The new Entities benchmark substantially extends longitudinal coverage, with 47 topics, 47 timelines, an average of 959 documents and 600 publication dates per task, and an average duration of about 12 years.",
   "The clustering approach generally underperformed Datewise and the prior Martschat method, with analysis showing that nearby articles were sometimes merged even when ground-truth timelines treated them as separate events.",
   "Automatically generated timelines frequently contained adjacent-date redundancy, and simply prohibiting adjacent dates reduced the automatic evaluation scores, exposing a mismatch between redundancy control and the evaluated objectives."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-2024-acl-long-390",
  "title": "From Moments to Milestones: Incremental Timeline Summarization Leveraging Large Language Models",
  "research_question": "Can a unified LLM-based incremental event-clustering pipeline generate effective event and topic timelines from evolving text streams while remaining more efficient and interpretable than conventional timeline-summarization approaches?",
  "key_findings": [
   "The proposed pipeline supports incremental event clustering and summarization as new text arrives, rather than requiring retrospective processing of the complete collection.",
   "On event clustering, retrieval mode achieved 89.63 precision and 81.94 F1 while reducing the reported experiment time from roughly 35 minutes in global mode to 7 minutes.",
   "For event summarization on noisy input streams, LLM-TLS exceeded the reproduced oracle BART and DistillBART baselines on ROUGE-2 and ROUGE-L, although its results did not dominate every model on every ROUGE measure.",
   "For topic timelines, the hybrid LLM-TLS variant produced the strongest reported Date-F1 values among the compared methods on T17, CRISIS, and ENTITIES.",
   "The advantage of event-oriented LLM-TLS over the date-wise comparison became more apparent for topics spanning hundreds or more publication dates, suggesting greater robustness for long-range timeline construction."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-2026-acl-long-1149",
  "title": "Agent Newsroom: Efficient Chronological Report Generation via Dynamic Multi-Agent Collaboration",
  "research_question": "Can chronological report generation be organized as dynamically scheduled, budget-aware multi-agent collaboration that improves semantic coverage, temporal grounding, and narrative balance while reducing inference cost?",
  "key_findings": [
   "MAS-TLS improves most reported semantic-coverage and temporal-grounding measurements across the three benchmarks, although it does not dominate every individual metric; on T17 its AR-2 result is 2.8% below the strongest compared baseline.",
   "On the Entities benchmark MAS-TLS uses 13.8 million tokens and 37,078 seconds, compared with 20.2 million tokens and 39,009 seconds for the strongest efficiency-oriented baseline CHRONOS, while also obtaining higher AR-1.",
   "The reported temporal and topical distribution measures indicate that MAS-TLS produces more balanced timelines, including lower inter-event temporal variation and topic distributions closer to the reference timelines.",
   "Ablation experiments show that removing distinctiveness or the LLM-based ranking/adjudication component causes substantial quality losses, while disabling adaptive scheduling increases token consumption by about 34%.",
   "Across tested model backbones the paper reports less than 8% relative variation in AR-1, and its cross-lingual experiments retain a semantic-coverage advantage over the strongest compared baseline."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-d19-1386",
  "title": "Summary Cloze: A New Task for Content Selection in Topic-Focused Summarization",
  "research_question": "Can next-sentence prediction conditioned on a topic, reference documents, and the summary-so-far provide a scalable task for learning content selection in topic-focused summarization?",
  "key_findings": [
   "Access to the topic and preceding summary context helped human writers select content closer to the reference cloze, with human ROUGE-1 increasing from 24.49 without topic/context to 31.78 with them.",
   "The learned extractive ContentSelector outperformed the non-oracle extractive baselines, reaching ROUGE-1 25.13 versus 21.33 for BM25 and 17.50 for Lead-1.",
   "Most of the ContentSelector improvement from conditioning came from the partial-summary context; removing the topic alone did not produce a statistically significant degradation.",
   "Conditioning the abstractive decoder on the preceding summary context improved generated clozes across tested preprocessing variants, including roughly a two-point ROUGE-1 gain with ContentSelector preprocessing.",
   "The model design uses coverage together with the preceding summary context to discourage generation of information already expressed in that context, directly addressing local repetition."
  ]
 },
 {
  "paper_id": "doi-10-2196-43977",
  "title": "Effect of Personalized Email-Based Reminders on Participants’ Timeliness in an Online Education Program: Randomized Controlled Trial",
  "research_question": "Do progress-personalized email reminders improve the timeliness of adult online learners more than general schedule-based reminders?",
  "key_findings": [
   "The model-estimated probability of being on time was 14 percentage points higher after personalized reminders than after general reminders, with a 95% credible interval from 3 to 25 percentage points.",
   "In the unadjusted observations, 64.1% of personalized reminders were followed by an on-time state compared with 52.8% of general reminders.",
   "For an average participant at an average reminder time, the model estimated a 70% probability of being on time after personalized reminders and 56% after general reminders.",
   "A relatively small amount of state-specific personalization—telling a learner both expected and observed progress—was sufficient to improve timeliness relative to schedule-only reminders in this sample.",
   "The study had no no-reminder arm, so it estimates the incremental value of personalization over general reminders rather than the causal effect of reminders versus receiving no reminder."
  ]
 },
 {
  "paper_id": "doi-10-3389-fpsyg-2014-00657",
  "title": "How important is importance for prospective memory? A review",
  "research_question": "How does the importance assigned to an intended future action affect prospective-memory performance, and through which monitoring or retrieval mechanisms do different importance manipulations operate?",
  "key_findings": [
   "Across the reviewed literature, making an intention important generally improved prospective-memory performance, although the effect was not universal and depended on manipulation and task conditions.",
   "Evidence for reward-based importance was mixed: three reviewed studies reported improved prospective-memory performance while two did not.",
   "Relative-importance instructions generally improved prospective-memory performance, but the gain was commonly accompanied by poorer performance or greater monitoring cost on the ongoing task.",
   "Social-motive manipulations improved prospective-memory performance in all studies reviewed in that category and did so without measurable ongoing-task costs in the cited studies.",
   "The review associates rewards and relative-priority instructions with changes in resource allocation and strategic monitoring, whereas social motives and potentially absolute-importance instructions may improve retrieval by strengthening intention representations without the same monitoring cost."
  ]
 },
 {
  "paper_id": "doi-10-3758-bf03201140",
  "title": "Prospective memory: when reminders fail",
  "research_question": "Under what conditions do reminders improve prospective memory, and which reminder contents successfully reactivate an intended future action?",
  "key_findings": [
   "Reminders referring only to prospective-memory target events did not improve performance over a no-reminder control across the experiments testing that comparison.",
   "Reminders referring only to the intended action improved prospective memory relative to no reminder, but were less effective than reminders linking the target and action.",
   "Reminders that jointly referred to the target event and intended action produced the strongest prospective-memory benefit and exceeded target-only and action-only conditions where compared.",
   "Adding an instruction to imagine performing the prospective-memory task did not further improve performance beyond the effective target-plus-action reminder.",
   "Within the tested ranges, neither reminder-to-target delay nor instruction-to-task delay significantly changed prospective-memory performance."
  ]
 },
 {
  "paper_id": "doi-10-3758-s13421-025-01708-x",
  "title": "Strategic reminder setting for time-based intentions: Influence of metacognition, delay length, and cue visibility",
  "research_question": "How do delay length, metacognitive beliefs, and access to a visible time cue influence strategic reminder setting and performance for time-based prospective-memory intentions?",
  "key_findings": [
   "Longer delays reduced first-response prospective-memory accuracy, lowered confidence, and substantially increased reminder use.",
   "Setting reminders improved prospective-memory performance, reduced errors, and produced larger benefits at longer delays in both experiments.",
   "Within participants, a steeper decline in confidence as delay increased predicted a steeper rise in reminder use, even though the confidence decline did not track the corresponding decline in objective unaided accuracy.",
   "The preregistered hypothesis that people with lower average confidence across participants would generally use more reminders was not consistently supported; mean confidence did not significantly predict overall reminder use in the main analyses.",
   "Participants used significantly more reminders when the clock was hidden than when it remained visible, and clock visibility explained reminder usage independently of average confidence in Experiment 2."
  ]
 },
 {
  "paper_id": "doi-10-3758-s13423-026-02985-6",
  "title": "Let it go: How trusted reminders alter intention maintenance",
  "research_question": "Does experience with reminders of different perceived reliability cause people to shift from internally maintaining prospective intentions to relying on external reminders?",
  "key_findings": [
   "During the initial trust session, reminders improved prospective-memory performance without reducing prospective-memory-related thoughts, which is consistent with duplicative rather than immediately substitutive offloading.",
   "After experience with reliable support, participants expecting 100% reliable reminders reported substantially fewer prospective-memory-related thoughts than both the no-reminder and 50%-reliability groups.",
   "The 100%-reliability condition also produced more ongoing-task-related thoughts, while reminder reliability did not meaningfully alter task-unrelated thought.",
   "When reminders remained available in Session 2, both reminder groups substantially outperformed the no-reminder group in prospective-memory accuracy.",
   "When expected reminders were unexpectedly absent, the 100%-reliability group performed worse than the no-reminder group, but the associated Bayes factor was equivocal, so the authors characterize this result as suggestive rather than definitive."
  ]
 },
 {
  "paper_id": "doi-10-6028-nist-sp-500-302-tempsumm-overview",
  "title": "TREC 2013 Temporal Summarization",
  "research_question": "How should systems that continuously monitor developing events be evaluated for timely, novel and comprehensive updates and for accurate tracking of changing event attributes?",
  "key_findings": [
   "The evaluation framework explicitly separates update usefulness from coverage by measuring expected gain and comprehensiveness, while also discounting latency and unnecessary verbosity.",
   "Gain-based performance tended to be anti-correlated with comprehensiveness, analogous to the precision-recall tradeoff.",
   "Runs with higher gain generally emitted fewer updates, whereas runs with greater comprehensiveness emitted more, leading the authors to suggest reconciling or prioritizing the two objectives according to user intent.",
   "Performance varied substantially across event queries even when aggregate averages remained useful for overall run comparison.",
   "No Value Tracking system performed consistently well across all attributes, and some runs omitted entire attributes."
  ]
 },
 {
  "paper_id": "doi-10-64898-2025-11-28-25341233",
  "title": "CLIN-SUMM: Incremental Longitudinal Summarization of Clinical Notes Enables Scalable Representation and Early Disease Prediction",
  "research_question": "Can incremental, temporally faithful summarization of only newly documented clinical information produce a compact reusable longitudinal patient representation that preserves clinical content and supports scalable downstream prediction and trajectory extraction?",
  "key_findings": [
   "CLIN-SUMM reduced the longitudinal note representation by about 70% in tokens across the expanded cohort while retaining high clinician-rated correctness and completeness.",
   "The framework processes new encounter information incrementally and preserves dated longitudinal structure without using future documentation.",
   "Clinical ModernBERT trained on CLIN-SUMM representations achieved AUROC 0.86 for dementia diagnosis and 0.81 for three-year risk prediction in the reported expanded study.",
   "Risk separation emerged longitudinally before formal dementia diagnosis rather than appearing only immediately before diagnosis.",
   "Summary-based extraction found substantially more Donepezil medication instances than the compared structured tables, with 2,725 versus 1,312 instances in the dementia cohort."
  ]
 },
 {
  "paper_id": "manual-0839b98ee7",
  "title": "Can requests-for-action and commitments-to-act be reliably identified in email messages?",
  "research_question": "Can human annotators reliably and repeatably identify both the presence and strength of requests-for-action and commitments-to-act in workplace email, making these categories plausible targets for automated detection?",
  "key_findings": [
   "Three-way agreement for identifying whether a sentence contains a Request-for-Action is relatively high at kappa 0.78.",
   "Agreement on Request-for-Action strength is lower but still tentative at kappa 0.60.",
   "Commitments-to-Act are substantially harder to annotate consistently: presence agreement is kappa 0.54 and strength agreement is kappa 0.37.",
   "Agreement varies with audience structure; single-recipient messages generally produce the highest agreement, while closed-group messages produce the lowest, with Commitment-to-Act agreement particularly weak for closed groups.",
   "Conditional offers are a major systematic ambiguity and account for almost 40% of disagreements about whether a Commitment-to-Act is present."
  ]
 },
 {
  "paper_id": "manual-13a21477e7",
  "title": "Summarize What You Are Interested In: An Optimization Framework for Interactive Personalized Summarization",
  "research_question": "Can interactive user feedback be incorporated into an optimization framework so that successive extractive summaries increasingly reflect an individual user's interests while retaining conventional summary quality?",
  "key_findings": [
   "Sparse click and examination feedback can be propagated to related sentence content and used to update the summary toward the user's expressed interests over successive interactions.",
   "The interactive personalized method received substantially higher personalized human ratings than the non-interactive baselines across the four evaluated news collections.",
   "The personalized summaries did not consistently achieve the highest ROUGE-1 scores; generic summarization could score better when a user's interests diverged from the generic reference summaries.",
   "Summaries preferred by different evaluators exhibited relatively low content consistency, which the authors interpret as evidence that the interaction mechanism was capturing individual rather than generic preferences.",
   "Increasing the weight on user-specific utility strengthens personalization, but excessive weighting causes generic ROUGE quality to decline, demonstrating a trade-off between personal relevance and corpus-level representativeness."
  ]
 },
 {
  "paper_id": "manual-1d6b22c7ad",
  "title": "Corpus-Based Problem Selection for EHR Note Summarization",
  "research_question": "Can corpus-derived lexical, frequency, persistence, and temporal features identify which clinical problems from longitudinal notes should be retained in a concise patient summary?",
  "key_findings": [
   "The best reported relevance-classification accuracy reached 82%, with an F-measure of 0.62.",
   "Restricting candidate evidence to particular note sections significantly reduced F-measure rather than improving selection.",
   "A simple filter for problems that were predominantly or finally negated improved both precision and recall in the reported experiments.",
   "When precision and recall were weighted equally, best-first feature selection helped remove extraneous problems from the proposed summary.",
   "When recall was weighted more heavily through F2, omitting feature selection produced better results, showing that the preferred selector depends on the cost assigned to omissions."
  ]
 },
 {
  "paper_id": "manual-39435af3dd",
  "title": "Overview of the TAC 2008 Update Summarization Task",
  "research_question": "How well can automatic summarizers produce concise summaries of new information from a later document batch when the reader is assumed to already know the information in an earlier batch?",
  "key_findings": [
   "Manual evaluation showed a significant quality gap between human and automatic summarizers in readability, Pyramid content and overall responsiveness.",
   "Automatic systems performed worse on the later update summaries than on initial summaries, while human summarizers were approximately equally effective on both.",
   "ROUGE-2 and ROUGE-SU4 detected the initial-versus-update performance difference for automatic systems, whereas BE-HM did not distinguish the two summary types at the reported 95% confidence level.",
   "Differences among ROUGE-2, ROUGE-SU4 and BE-HM in Pearson and Spearman correlation with the manual measures were not statistically significant at the 95% level.",
   "Despite high correlations on automatic peers, the automatic metrics did not reproduce the clear manual-evaluation separation between human and machine summaries."
  ]
 },
 {
  "paper_id": "manual-4cb48c423e",
  "title": "Interactive Multi-Objective Probabilistic Preference Learning with Soft and Hard Bounds",
  "research_question": "Can an interactive probabilistic preference-learning framework using editable soft and hard bounds, active querying and global sensitivity analysis efficiently identify preferred Pareto-optimal solutions while improving decision-maker confidence?",
  "key_findings": [
   "Active-C-MoSH reached higher second-iteration utility than pairwise feedback and full ranking in the user study, while its difference from partial ranking was not statistically significant.",
   "Participants rated Active-C-MoSH as providing significantly greater decision confidence or trust than full ranking, partial ranking and pairwise feedback.",
   "The initial comparative ISE result was not statistically significant, but in the four-trial longitudinal study the final Active-C-MoSH trial reached a mean ISE of 0.82 and was reported as significantly higher than the baseline feedback mechanisms.",
   "An ablation comparing Active-C-MoSH with Active-MoSH produced higher ISE for the version including C-MoSH, supporting the sensitivity-analysis component as a contributor to decision confidence.",
   "Active-C-MoSH was rated as more cognitively demanding than the simpler feedback mechanisms but also more expressive than full ranking and pairwise feedback."
  ]
 },
 {
  "paper_id": "manual-50ed5dc808",
  "title": "The Learning Behind Gmail Priority Inbox",
  "research_question": "How can Gmail learn a scalable, continuously updated, user-specific ranking of email importance from noisy behavioral feedback and explicit corrections?",
  "key_findings": [
   "Email importance is strongly personalized, motivating a model that combines globally learned patterns with per-user parameter adjustments and per-user thresholds.",
   "On approximately 160,000 explicit user importance markings, the reported error rate falls from 45% for a global model to 38% with user-specific models and to 31% when personalized thresholds are also used.",
   "Implicit-feedback evaluation yields accuracy of about 80% with roughly five percentage points of variation, while the authors identify presentation bias of about two to three percentage points among active Priority Inbox users.",
   "False-negative importance errors occur approximately three to four times as often as false positives under the implicit-label evaluation, illustrating asymmetric behavior and the importance of threshold selection.",
   "In a comparison of roughly 2,000 Google employees with similar mail volume, Priority Inbox users spent about 6% less time reading email overall and about 13% less time reading messages classified as unimportant."
  ]
 },
 {
  "paper_id": "manual-bdce973227",
  "title": "Success of an Agent-Assisted System that Reduces Email Overload",
  "research_question": "Does combining automatic email task extraction with learned task-ordering advice improve novice performance under simulated email overload, and how do users respond to agent errors and critical-task recommendations?",
  "key_findings": [
   "Participants receiving both task extraction and ordering assistance achieved a mean overall score of 0.754 versus 0.706 with task-centric assistance alone and 0.550 with no learned assistance; the condition effect was significant and the paper summarizes the TCO-versus-None improvement as 37%.",
   "The email classifier was deliberately tuned toward precision and achieved precision 0.887 and recall 0.461, correctly identifying 47 of 102 task labels while producing six false positives.",
   "TCO users incorrectly completed an average of 2.6 false-positive or true-negative tasks, compared with 10.3 incorrectly completed tasks in the no-assistance condition, which the authors describe as up to a fourfold reduction in mistakes.",
   "TCO participants completed fewer total and fewer non-critical tasks than TC participants but achieved higher overall scores, consistent with the ordering agent steering limited effort toward higher-value obligations and away from overflow work.",
   "The Action List explicitly represented incomplete, overflow, completed, and deleted tasks and allowed users to add missed tasks or delete false positives, providing within-session work-state and correction mechanisms."
  ]
 },
 {
  "paper_id": "manual-c2f56a571b",
  "title": "Summarizing Emails with Conversational Cohesion and Subjectivity",
  "research_question": "Can the conversational structure of email threads, local lexical cohesion, and subjective language improve extractive summaries of email conversations?",
  "key_findings": [
   "Simple clue-word overlap was more accurate than cosine similarity and both tested WordNet semantic-similarity variants for weighting conversational links.",
   "The clue-word method achieved pyramid precision 0.60, compared with 0.39 for cosine similarity and 0.57 for each tested semantic-similarity method, with statistically significant differences.",
   "The local-neighborhood ClueWordSummarizer outperformed PageRank variants, suggesting that local conversational cohesion was more aligned with human sentence selections than global graph centrality in this corpus.",
   "Subjective-word scores alone were not consistently superior to the clue-word baseline, but combining subjective evidence with clue-word cohesion improved pyramid precision from 0.60 to 0.65 or 0.64.",
   "Clue-word and subjective-word signals overlapped only weakly, supporting the interpretation that they captured complementary forms of sentence importance."
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
"/home/grammy-jiang/Projects/msgloom/research/09-incremental-personalized-briefing/runs/229b747dc22e/analysis/synthesis.json", `status` = accepted | accepted_with_issues | rejected,
`issues` (each naming the finding or paper it is about), `required_fixes`
(required when rejected), `unsupported_claims`, `confidence`, and `scores`
with faithfulness, coherence, gap_completeness (0-1) and citation_integrity
(true/false).
===BEGIN synthesis_review.json===
<content>
===END synthesis_review.json===
