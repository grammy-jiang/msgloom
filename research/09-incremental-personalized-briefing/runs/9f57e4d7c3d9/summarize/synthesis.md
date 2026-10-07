# Executive Summary

Across 43 distinct studies, the corpus supports several components of cycle-based briefing but not their end-to-end combination. Update and temporal summarization research separates novelty, timeliness, redundancy, and coverage, and shows a recurring trade-off between concise high-gain updates and comprehensiveness. Workplace email studies show that pending requests and reminders are managed longitudinally, that stale or incorrect task state is a material user concern, and that importance is highly personalized. Personalization and drift-adaptation studies demonstrate gains from user-specific models and continual updating, but long-term workplace adaptation remains untested. Prospective-memory research further shows that reminder value is not reducible to urgency or importance. Evaluation studies expose weaknesses in ROUGE-only assessment and sensitivity to temporal split design. No admitted paper directly evaluates the requested integrated cross-thread workplace briefing scheme.

# Themes

## Incremental update selection, coverage, and repetition

**Finding — HIGH confidence.** Sequential and update-summarization studies treat novelty, timeliness, coverage, and redundancy as distinct objectives, and temporal-summarization benchmarks report a recurring trade-off between high-gain concise updates and comprehensiveness. [doi-10-6028-nist-sp-500-302-tempsumm-overview] [doi-10-1155-2016-1340973] [doi-10-1016-j-knosys-2013-02-015] [doi-10-1145-290941-291025]

The TREC Temporal Summarization framework explicitly separates expected gain from comprehensiveness and reports an anti-correlation between them. The sequential-update work similarly reports that one variant attains higher comprehensiveness while another attains higher expected gain. Query-focused summarization and MMR independently demonstrate explicit relevance/coverage/novelty and relevance/diversity formulations. These studies establish separate optimization dimensions, not a validated workplace briefing policy.

## Longitudinal workplace tasks and stale state

**Finding — HIGH confidence.** In workplace-email studies, people retain messages and use reminders to keep future actions salient, while users of an AI-generated collaborative-task briefing reported stale or insufficiently up-to-date task state as a material problem. [doi-10-1145-634067-634150] [doi-10-1145-642611-642672] [2403.01365]

Prospective-information studies found widespread use of inboxes as stores and reminder mechanisms for future actions. Task-centered email systems likewise found value in reminders, deadlines, and action indicators. In the AI-reminder study, 12 of 45 validating-survey participants reported inaccurate or insufficiently current information, while forgotten-task reminders were a major positive theme. This is direct workplace evidence for longitudinal pending-work concerns, but it does not test explicit new/open/resolved/superseded state transitions.

## Personalized priority and heterogeneous work context

**Finding — HIGH confidence.** Personalized email-priority models outperform global or less-personalized baselines in several email studies, while both preferred triage strategy and useful predictive formulation vary across users, contexts, and datasets. [manual-50ed5dc808] [doi-10-1145-1557019-1557124] [doi-10-1145-2063576-2063683] [doi-10-1145-1056808-1057071]

Gmail Priority Inbox reports substantially lower error after adding user-specific models and personalized thresholds. Social-network-derived personal features also reduce email-priority prediction error. A separate priority-model comparison finds classification superior to ordinal regression on personalized email data but the reverse on UCI-derived ordinal datasets, demonstrating task and dataset dependence rather than a universal model ordering. Observational triage work additionally reports multiple user strategies and substantial dependence on social and work context.

## Obligation signals versus importance signals

**Finding — HIGH confidence.** Workplace-email evidence distinguishes action-related signals from importance judgments: requests-for-action can be annotated relatively reliably, commitments are harder to annotate, and separate email studies model perceived or predicted importance rather than response obligation. [manual-0839b98ee7] [doi-10-1093-jcmc-zmac001] [manual-50ed5dc808]

Request-for-action presence has substantially higher annotation agreement than commitment-to-act presence or strength, with conditional offers producing major ambiguity. Separately, perceived-email research characterizes important and important-and-urgent mail, and Gmail Priority Inbox predicts user-specific importance. These works establish different signal families; they do not experimentally test a unified hard-obligation/soft-preference selection policy.

## Reminder value and forgetting risk

**Finding — HIGH confidence.** Reminder usefulness is not equivalent to urgency: workplace participants reported forgetting low-importance or non-urgent tasks, while prospective-memory experiments show reminder effectiveness varies with cue content, delay, confidence, and cue visibility. [2403.01365] [doi-10-3758-bf03201140] [doi-10-3758-s13421-025-01708-x] [doi-10-1186-s41235-019-0195-y] [doi-10-3389-fpsyg-2014-00657]

The workplace reminder study identifies low-importance, non-urgent, ad hoc, and small tasks among frequently forgotten categories. Laboratory prospective-memory studies find that target-plus-action reminders outperform target-only reminders, longer delays increase reminder use, cue visibility changes reminder behavior, and confidence can influence cognitive offloading. The prospective-memory review also finds that importance effects vary by manipulation and cost structure.

## Preference drift and continual adaptation

**Finding — MEDIUM confidence.** In recommender-system transfer domains, continually updated and drift-aware models can outperform batch or static counterparts under changing preferences, while the magnitude of personalization benefit is dataset-dependent. [doi-10-1016-j-eswa-2021-114890] [doi-10-1016-j-eswa-2021-115626] [doi-10-1109-fuzz-ieee-2016-7737835] [doi-10-1145-2523813] [2202.07088]

Streaming supermarket recommenders outperform batch counterparts under several drift conditions, and temporal recommenders model successive preference transitions and forgetting. The concept-drift survey describes modular memory, detection, learning, and loss-estimation strategies and cautions that simple recency is not a reliable relevance proxy. Personalized constraint prediction improves over a mean parameterization on MovieLens but not materially on YOW News. These are transfer results rather than longitudinal workplace-email evaluations.

## Incremental longitudinal representations

**Finding — MEDIUM confidence.** Incremental longitudinal summarization is feasible in transfer domains: clinical systems preserve dated longitudinal structure or links to source periods while compressing histories, and incremental event-timeline systems update clusters and summaries as new evidence arrives. [doi-10-64898-2025-11-28-25341233] [doi-10-1136-amiajnl-2014-002945] [doi-10-18653-v1-2024-acl-long-390]

CLIN-SUMM incrementally processes newly documented clinical information and preserves temporal structure while obtaining substantial compression. HARVEST exposes longitudinal problems linked back to clinical notes and time periods. LLM-TLS performs incremental event clustering and summarization as new documents arrive. Their target domains, state semantics, and evaluation outcomes differ from cross-thread workplace work items.

## Decision-focused coverage

**Finding — MEDIUM confidence.** Decision-focused content selection can preserve a downstream model decision substantially better than the tested text-focused summarization baselines, and separate decision experiments show that both the amount and structure of missing information affect decision performance. [2109.06896] [doi-10-1177-1071181322661236]

DecSum explicitly optimizes agreement with a full-text predictive decision and representativeness of decision evidence, preserving the simplified model's accuracy better than the tested summarization baselines. Separate incomplete-information experiments show that both information amount and cue structure affect human decision performance. Neither experiment directly evaluates workplace briefing omissions.

## Evaluation beyond ROUGE

**Finding — HIGH confidence.** Automatic summarization scores alone do not consistently reflect human preference or update quality: ROUGE improvements can fail to produce human-preference gains, personalized summaries can receive stronger user ratings without leading generic ROUGE, and TAC update evaluation found automatic metrics unable to reproduce some clear manual-evaluation distinctions. [2107.14691] [manual-13a21477e7] [manual-39435af3dd]

EmailSum reports automatic-score improvements from semi-supervised training without corresponding superiority in human preference. Interactive personalized summarization improves personalized human ratings while sometimes losing generic ROUGE. TAC 2008 reports a clear manual human-machine quality separation that its tested automatic metrics did not reproduce in the same way.

## Chronological evaluation

**Finding — MEDIUM confidence.** Sequential-system evaluation is sensitive to chronology: recommender experiments show that temporal split and target-definition choices can materially change measured model rankings, while windowed prequential evaluation exposes adaptation behavior during drift. [doi-10-1145-3705328-3748164] [doi-10-1016-j-eswa-2021-114890]

Global temporal splitting experiments report unstable model rankings across evaluation protocols and better alignment when validation follows the same temporal construction as testing. The supermarket study uses windowed prequential evaluation to observe adaptation around abrupt changes. Both results come from recommendation rather than briefing.

## Uncertainty and incomplete state

**Finding — MEDIUM confidence.** Uncertainty presentation has context-dependent effects in transfer decision-support studies: explicit uncertainty can alter decision process or reduce attempts without improving classification accuracy, and broader evidence does not support a universal loss of trust from communicating epistemic uncertainty. [doi-10-1016-j-cag-2014-02-006] [doi-10-1098-rsos-181870] [doi-10-1609-icwsm-v12i1-15014]

A target-identification experiment found fewer attempts with uncertainty visualization but no significant classification improvement. A broader uncertainty review concludes that effects vary by format and audience and that acknowledging uncertainty does not universally reduce trust. Conflicting-cue experiments likewise show greater uncertainty and more errors when evidence points in opposing directions.

# Contradictions

No direct cross-paper contradiction met the required criterion of answering the same question under comparable conditions.

Several apparent tensions were retained as scope qualifications rather than classified as contradictions. Personalized shadow-price prediction helps more on MovieLens than YOW News [2202.07088]; classification outperforms ordinal regression on the studied email data while ordinal regression performs better on the UCI-derived datasets [doi-10-1145-2063576-2063683]; and importance-related prospective-memory benefits vary by manipulation and task conditions [doi-10-3389-fpsyg-2014-00657]. These are dataset- or condition-dependent effects rather than comparable-condition disagreements between papers.

# Open Gaps

## gap-1 — ACADEMIC, HIGH — open

This corpus does not directly evaluate a longitudinal workplace briefing that, across successive report cycles, distinguishes newly changed information from unchanged-but-still-open work while suppressing resolved or superseded information.

Closest evidence covers AI workplace reminders, temporal news summarization, incremental event timelines, and clinical longitudinal summaries, but not the complete workplace-cycle question. [2403.01365] [doi-10-18653-v1-2024-acl-long-390] [doi-10-64898-2025-11-28-25341233] [doi-10-6028-nist-sp-500-302-tempsumm-overview]

Suggested query: `"incremental summarization" longitudinal workplace email briefing "open" resolved superseded state`

## gap-2 — ACADEMIC, HIGH — open

This corpus does not establish how explicit user rules or response obligations interact with softer personalized importance, triage, reminder-value, or forgetting signals in briefing selection, nor whether separating these signal classes improves outcomes.

The corpus separately studies requests and commitments, importance, triage, and reminder value, but not their combined policy. [manual-0839b98ee7] [doi-10-1093-jcmc-zmac001] [manual-50ed5dc808] [2403.01365]

Suggested query: `"email prioritization" "response obligation" hard constraints soft preferences personalized triage reminder`

## gap-3 — ACADEMIC, HIGH — open

Long-term adaptation to changing user roles, projects, priorities, feedback, and work patterns is not directly evaluated in the admitted personalized workplace email or reminder studies.

Drift-aware recommendation and continuously updated email importance provide candidate adaptation mechanisms without direct long-term role/project evaluation. [doi-10-1016-j-eswa-2021-114890] [doi-10-1016-j-eswa-2021-115626] [doi-10-1145-2523813] [manual-50ed5dc808]

Suggested query: `"longitudinal personalization" workplace email preference drift adaptive prioritization user feedback`

## gap-4 — ACADEMIC, HIGH — open

The corpus does not provide an end-to-end evaluation of briefing content selection that jointly measures omission of decision-essential work, redundant repetition, false alerts, and preservation of unresolved important state over repeated cycles.

Temporal benchmarks measure subsets such as gain, coverage, latency, redundancy, and summary quality rather than this joint workplace outcome set. [doi-10-6028-nist-sp-500-302-tempsumm-overview] [doi-10-1155-2016-1340973] [manual-39435af3dd] [2107.14691]

Suggested query: `"longitudinal summarization" omission redundancy false alerts unresolved state evaluation`

## gap-5 — ACADEMIC, MEDIUM — open

The admitted studies do not determine how reminder usefulness or likelihood of forgetting combines with perceived importance, urgency, recency, or personalized priority when selecting content for a briefing.

The corpus establishes several individual influences but not their combined selection function. [2403.01365] [doi-10-3758-s13421-025-01708-x] [doi-10-1186-s41235-019-0195-y] [doi-10-1093-jcmc-zmac001]

Suggested query: `"email reminder" forgetting importance urgency recency personalized priority task selection`

## gap-6 — ACADEMIC, HIGH — open

No admitted paper evaluates topic- or work-item-level incremental briefing across multiple workplace conversations and sources; direct email summarization remains primarily thread- or conversation-level, while incremental evidence comes from transfer domains.

EmailSum and conversational email work remain thread-oriented, while incremental timeline and clinical work use other domains. [2107.14691] [manual-c2f56a571b] [doi-10-18653-v1-2024-acl-long-390] [doi-10-64898-2025-11-28-25341233]

Suggested query: `"cross-thread summarization" email multi-source incremental "work item" workplace`

## gap-7 — ACADEMIC, HIGH — open

Although the corpus contains evidence about stale reminders, epistemic uncertainty, and conflicting cues, it does not experimentally establish how a workplace briefing presents stale, uncertain, disputed, or incompletely investigated state, or how alternative presentations affect workplace decisions.

Workplace reminder research identifies stale information as a problem; uncertainty-presentation experiments come from other decision settings. [2403.01365] [doi-10-1016-j-cag-2014-02-006] [doi-10-1098-rsos-181870] [doi-10-1609-icwsm-v12i1-15014]

Suggested query: `"uncertainty visualization" workplace decision support stale disputed incomplete information briefing`

## gap-8 — ENGINEERING, HIGH — open

Candidate mechanisms from this corpus have not been compared in one reproducible cycle-based benchmark with chronological holdouts, independently labeled new/open/resolved/superseded state, user-specific priority labels, and explicit omission and repetition errors.

The literature supplies temporal metrics, chronological split methods, priority models, and update-evaluation methods separately. [doi-10-6028-nist-sp-500-302-tempsumm-overview] [doi-10-1145-3705328-3748164] [manual-50ed5dc808] [manual-39435af3dd]

# Actionable Insights

- **Synthesis-derived recommendation:** represent each report cycle as an explicit comparison against the user's prior accepted Topic view, with separate candidate classes for newly changed information, unchanged open information, resolved information, and superseded information.
- **Synthesis-derived recommendation:** keep obligation or explicit user-rule signals separate from softer preference, importance, urgency, reminder-value, or predicted-forgetting signals so their contributions can be evaluated independently before any combined ranking policy is adopted.
- **Synthesis-derived recommendation:** evaluate briefing selection with a multi-objective scorecard that records decision-essential omissions, unresolved-state omissions, redundant repetitions, false alerts, and useful compression separately rather than collapsing them into one similarity metric.
- **Synthesis-derived recommendation:** build chronological evaluation fixtures in report-cycle order and prohibit future-cycle evidence from entering prediction inputs; use later evidence only as independently separated evaluation gold where appropriate.
- **Synthesis-derived recommendation:** include low-urgency and low-importance open items in reminder-value experiments instead of restricting evaluation to highly ranked items, because forgetting risk and conventional importance are different candidate signals.
- **Synthesis-derived recommendation:** test personalization both statically and under simulated or observed preference drift, including role changes, project changes, explicit corrections, and changing thresholds.
- **Synthesis-derived recommendation:** expose stale, uncertain, disputed, and incompletely investigated state as separate experimental presentation conditions rather than silently converting them into a single confidence score.
- **Synthesis-derived recommendation:** treat news, clinical, recommender, and laboratory prospective-memory results as sources of candidate mechanisms and benchmark ideas, not as evidence of production workplace accuracy.
- **Synthesis-derived recommendation:** preserve a trace from every selected briefing item to its underlying work-item state and source evidence so omission, repetition, supersession, and stale-state errors can be audited cycle by cycle.

# Confidence Summary

Confidence is **HIGH** for component-level observations about update-summarization trade-offs, personalized email importance, workplace reminder practices, and limitations of similarity-only evaluation. Confidence is **MEDIUM** for transferring drift adaptation, longitudinal clinical summarization, temporal evaluation, decision-focused selection, and uncertainty-presentation mechanisms into workplace briefing. Confidence is **LOW** for any claim about the integrated scheme itself because no admitted paper jointly evaluates cross-thread work-item identity, new/open/resolved/superseded transitions, obligation-versus-preference prioritization, adaptive personalization, and omission/repetition over repeated workplace report cycles.

The corpus therefore supplies well-supported design principles and candidate mechanisms, not validated end-to-end workplace performance.

# Limitations

- The synthesis is based on the supplied reduced per-paper analyses rather than re-reading the complete papers, so methodological details not represented in those analyses cannot affect this synthesis.
- The 43 supplied analyses have 43 distinct titles; no duplicate-title record was identified, but title comparison alone cannot exclude every possible duplicate publication or extended version.
- Much of the evidence for incremental summarization, drift adaptation, chronological evaluation, longitudinal compression, and uncertainty presentation comes from news, clinical, recommender, or laboratory domains rather than workplace communication.
- Direct workplace-email evidence is strongest for thread summarization, task/reminder practices, request detection, triage, and importance prediction, not for cross-thread work-item lifecycle briefing.
- The corpus uses heterogeneous outcomes including ROUGE, human preference, task success, ranking error, recall, decision accuracy, prospective-memory performance, and user ratings, limiting direct quantitative aggregation.
- The absence of a qualifying direct contradiction does not imply uniform results; several studies report dataset-dependent or metric-dependent effects, but those differences arise under non-comparable tasks, datasets, or definitions and were not classified as contradictions.
- Inherited handoffs from Topics 06 and 08 were treated only as project context and boundary conditions; none was used as evidence for a finding or to close a gap.
- The corpus does not establish production representativeness for a personal system processing Outlook email and Teams across multiple concurrent work matters.
