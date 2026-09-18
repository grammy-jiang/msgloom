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

Research topic: **Direct empirical evaluations of longitudinal cross-thread workplace briefing: cycle-by-cycle new/open/resolved/superseded work-item tracking, obligation-versus-preference selection, adaptive personalization under preference drift, and joint omission/repetition/false-alert evaluation.**

Must-have terms: direct, empirical, evaluations
Nice-to-have terms: longitudinal, cross-thread, workplace, briefing:, cycle-by-cycle, new/open/resolved/superseded, work-item, tracking,, obligation-versus-preference, selection,, adaptive, personalization, under, drift,, joint, omission/repetition/false-alert, evaluation.
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
- F1 [TRANSFER]
    "update summarization" longitudinal unresolved resolved superseded
    "update summarization" "open" unresolved repeated cycles
    "multi-document update summarization" evolving state
    "temporal summarization" unresolved state persistence
    "stream summarization" novelty persistence unresolved
    "temporal summaries" evolving topic redundancy update
- F2 [TRANSFER]
    "novelty detection" summarization prior information redundancy
    "novel information" summarization repeated updates
    "redundancy reduction" update summarization evaluation
    "novelty" "unresolved" summarization
    "information filtering" novelty redundancy temporal
- F3 [TRANSFER]
    "event threading" longitudinal summarization
    "temporal event" summarization evolving topic
    "timeline summarization" evolving state
    "timeline summarization" redundancy update
    "event-centric summarization" temporal evolution
- F4 [TRANSFER]
    "query-focused multi-document summarization" update
    "query-focused multi-document summarization" coverage redundancy
    "coverage-aware summarization" important information redundancy
    "constrained summarization" user requirements coverage
    "multi-document summarization" actions deadlines decisions
    "content selection" summarization mandatory information constraints
- F5 [DIRECT]
    "email prioritization" urgency importance task obligation
    "email triage" action required priority
    "email triage" task management outstanding
    "email task management" outstanding tasks unresolved
    "task-centric email" user study
    "email overload" task management outstanding tasks
    "email prioritization" user preferences rules
    workplace email priority action required response
- F6 [DIRECT]
    "attention-sensitive alerting" email
    "notification prioritization" email urgency interruption
    "expected cost of delayed review" email
    "email alerting" urgency criticality user model
    "notification management" workplace email importance
    "email prioritization" interruption cost
- F7 [DIRECT]
    "email reminder" task forgetting importance urgency
    "email task management" reminder forgetting
    "prospective memory" email tasks reminders
    "prospective memory" workplace reminders
    "task reminder" importance urgency forgetting
    "task reminder" stale reminder user study
    workplace reminder usefulness task importance recency
- F8 [TRANSFER]
    "personalized summarization" user preferences feedback
    "personalized summarization" long term short term interests
    "user-adaptive summarization" feedback
    "personalized summarization" changing preferences
    "user model" summarization preference adaptation
- F9 [TRANSFER]
    "adaptive user model" changing preferences longitudinal
    "long-term user modeling" preference change
    "preference drift" personalized ranking
    "concept drift" personalization user profile
    "continual personalization" user feedback
    "online learning to rank" nonstationary preferences
    "dynamic user model" changing goals preferences
    "email prioritization" adaptive user model feedback longitudinal
    "email triage" personalization longitudinal feedback
- F10 [TRANSFER]
    "incremental dialogue summarization" unresolved tasks
    "incremental dialogue summarization" action items
    "long-running conversation summarization" actions decisions
    "conversation summarization" commitments decisions action items
    "meeting summarization" action item tracking longitudinal
    "dialogue summarization" persistent state unresolved
- F11 [DIRECT]
    "cross-thread" email summarization task
    "cross-thread" email task management
    "multi-thread" email summarization project task
    "activity-centric" email task management
    "task-centric" email multiple threads
    email "work item" tracking multiple threads
    workplace email project-centric summarization
    multiple conversations task-centric workplace summarization
    email task aggregation across conversations
    cross-conversation workplace task summarization
- F12 [TRANSFER]
    "hard constraints" "soft preferences" ranking
    "hard constraints" "soft preferences" personalization
    "constrained ranking" user preferences hard constraints
    "personalized ranking" hard constraints soft preferences
    "learning to rank" constraints user preferences
    "preference learning" mandatory constraints soft preferences
    "lexicographic" ranking hard constraints preferences
    "rule-based" personalized ranking constraints
- F13 [TRANSFER]
    "uncertainty visualization" decision making stale information
    "uncertainty communication" decision support incomplete information
    "stale information" decision support visualization
    "conflicting information" visualization decision support
    "incomplete information" workplace decision support visualization
    "data staleness" uncertainty decision support
    "provenance uncertainty" decision support
    "disputed information" decision support presentation
- F14 [TRANSFER]
    "update summarization" evaluation omission redundancy
    "longitudinal summarization" evaluation repetition omission
    "summary evaluation" content coverage redundancy omission
    "summarization" omission error redundancy evaluation
    "notification" false positives false negatives utility evaluation
    "alert" false positive false negative interruption utility
    "alert fatigue" false alarms prioritization
    "stream summarization" temporal evaluation repeated
    "online evaluation" concept drift ranking chronological
    "prequential evaluation" concept drift personalization
False friends — these match the words but not the capability, so do
not list them:
- Downgrade any update-summarization paper that only compares one earlier document set with one later document set and does not evaluate repeated cycles; it is useful transfer evidence, not direct longitudinal briefing evidence.
- Downgrade novelty-only systems that suppress all previously seen information. They conflict with the requirement to preserve unchanged-but-still-open important work.
- Downgrade timeline or temporal-summarization work when the output is merely a chronology of salient events and does not maintain actionable or unresolved state.
- Downgrade document-diff, source-code-diff, version-control, database-delta, or web-page-change literature returned by 'delta summarization' or 'information update detection' unless it evaluates semantic information selection relevant to human briefings.
- Downgrade generic multi-document summarization if it is static and has no prior-view, update, longitudinal, task, user, or workplace component.
- Downgrade message-level email importance classifiers when they predict only urgency, importance, or likelihood of opening/replying and do not distinguish an explicit response obligation.
- Downgrade reply-probability and response-time prediction when observed behavior is treated as evidence that a user ought to respond.
- Downgrade spam filtering, phishing detection, folder prediction, archive/delete prediction, and generic inbox classification unless they explicitly evaluate work priority or actionable task management.
- Downgrade recommendation, advertising, product, entertainment, social-feed, and popularity-ranking literature returned by personalized ranking or learning-to-rank queries.
- Downgrade personalized summarization that optimizes only topical interest without testing mandatory information, explicit rules, obligations, or failure costs from omitted important content.
- Downgrade personalization studies using a fixed profile or a single short session when cited as evidence for long-term adaptation under preference, role, project, or workload drift.
- Downgrade concept-drift papers that are purely methodological classification studies with no personalized selection or ranking connection; retain only as benchmark/evaluation transfer evidence.
- Downgrade generic constrained summarization where constraints are only output length, lexical inclusion, style, or decoding restrictions unless the method can represent mandatory versus defeasible selection requirements.
- Downgrade coverage-aware summarization when coverage is only topic diversity, embedding dispersion, or ROUGE overlap rather than coverage of decision-relevant semantic units.
- Downgrade entity-centric literature when the entity is used as a proxy for work-item identity. The same entity may participate in many independent Topics.
- Downgrade event-centric literature when one work item can persist across events or remain open without any new event.
- Downgrade long-conversation or incremental-dialogue summarization if the scope is one thread and there is no cross-conversation or cross-source consolidation.
- Downgrade clustering papers that group similar messages but do not establish persistent work-item identity; semantic similarity is not sufficient evidence of Topic identity.
- Downgrade notification-prioritization work optimized primarily for click-through, engagement, advertising response, or smartphone receptivity; these objectives do not establish workplace decision value.
- Downgrade attention-management work that only determines notification timing. Alert suppression does not imply that the same information may be omitted from a periodic briefing.
- Downgrade reminder studies that measure interruption or compliance only and do not analyze usefulness, forgetting risk, staleness, task importance, or false reminders.
- Downgrade uncertainty visualization that presents statistical model uncertainty only if the target need is stale, disputed, conflicting, incomplete, or provisionally investigated workplace information.
- Downgrade summarization evaluation papers limited to fluency, coherence, ROUGE, BERTScore, or generic similarity when they do not measure missed important content, redundancy, or false inclusion.
- Downgrade papers reporting only aggregate precision or recall if their evaluation cannot separate omission of essential work from unnecessary repetition or false alerts.
- Downgrade studies with random train/test splits when used as evidence for adaptation under temporal drift; retain them only for non-longitudinal methodological claims.
- Downgrade one-shot personalization evaluations when used to claim robustness to changing roles, projects, priorities, or user feedback over months or repeated report cycles.
- Downgrade work-item or task extraction papers that stop at extraction and do not evaluate briefing selection, persistence, prioritization, reminder utility, or longitudinal presentation.
- Downgrade generic meeting action-item extraction as direct evidence for cross-thread workplace briefing; it may be transfer evidence for identifying actionable state.
- Downgrade studies in which resolved or completed information is simply deleted without testing erroneous completion, revocation, reopening, supersession, or conflicting state.
- Downgrade any paper as direct evidence for gap-4 unless its repeated-output evaluation includes at least two of omission, repetition/redundancy, false inclusion/false alert, and persistence of unresolved important state; papers measuring only one component remain transfer evidence.
- Downgrade any paper as direct evidence for gap-6 unless its unit of organization spans multiple workplace conversations, threads, or sources around a persistent task/activity/work item.
- Do not treat synthetic, news, social-media, dialogue, recommendation, or generic decision-support results as production-email accuracy. Label them TRANSFER even when the mechanism is highly relevant.
Reach back to 1988 at least. Discovery should reach at least 1988. The longitudinal summarization line itself becomes clearly visible by Allan, Gupta, and Khandelwal's 2001 temporal-summary work, the TREC Novelty Track in 2002, and DUC/TAC update summarization in 2007-2008. However, the direct workplace side is older: Wendy Mackay's 1988 studies of professional email use already identify prioritization, task management, delegation, and diverse user strategies. Excluding the 1980s-1990s would also miss foundational email overload/task-management and adaptive user-model/attention work that defines the workplace problem and priority concepts later systems inherit. Use 1988 as the default floor for this round; older papers should still be admitted if backward citation chasing identifies a directly relevant precursor.

This is gap-closure round 4 of at most 4 for the
original topic **incremental, personalized and priority-aware briefings from workplace communication: how accepted topic information is selected, updated, prioritized and summarized for a user over time, distinguishing new developments from still-open state without repeating superseded facts**. Earlier rounds could not
close the open gaps below. Run every suggested query as well, and look
specifically for papers that answer these gaps:
- gap-1 [ACADEMIC, HIGH]: This corpus does not directly evaluate a longitudinal workplace briefing that, across successive report cycles, distinguishes newly changed information from unchanged-but-still-open work while suppressing resolved or superseded information.
    suggested query: "incremental summarization" longitudinal workplace email briefing "open" resolved superseded state
    searched in rounds: [1, 2, 3] (still open)
- gap-2 [ACADEMIC, HIGH]: This corpus does not establish how explicit user rules or response obligations interact with softer personalized importance, triage, reminder-value, or forgetting signals in briefing selection, nor whether separating these signal classes improves outcomes.
    suggested query: "email prioritization" "response obligation" hard constraints soft preferences personalized triage reminder
    searched in rounds: [1, 2, 3] (still open)
- gap-3 [ACADEMIC, HIGH]: Long-term adaptation to changing user roles, projects, priorities, feedback, and work patterns is not directly evaluated in the admitted personalized workplace email or reminder studies.
    suggested query: "longitudinal personalization" workplace email preference drift adaptive prioritization user feedback
    searched in rounds: [1, 2, 3] (still open)
- gap-4 [ACADEMIC, HIGH]: The corpus does not provide an end-to-end evaluation of briefing content selection that jointly measures omission of decision-essential work, redundant repetition, false alerts, and preservation of unresolved important state over repeated cycles.
    suggested query: "longitudinal summarization" omission redundancy false alerts unresolved state evaluation
    searched in rounds: [1, 2, 3] (still open)
- gap-5 [ACADEMIC, MEDIUM]: The admitted studies do not determine how reminder usefulness or likelihood of forgetting combines with perceived importance, urgency, recency, or personalized priority when selecting content for a briefing.
    suggested query: "email reminder" forgetting importance urgency recency personalized priority task selection
    searched in rounds: [1, 2, 3] (still open)
- gap-6 [ACADEMIC, HIGH]: No admitted paper evaluates topic- or work-item-level incremental briefing across multiple workplace conversations and sources; direct email summarization remains primarily thread- or conversation-level, while incremental evidence comes from transfer domains.
    suggested query: "cross-thread summarization" email multi-source incremental "work item" workplace
    searched in rounds: [1, 2, 3] (still open)
- gap-7 [ACADEMIC, HIGH]: Although the corpus contains evidence about stale reminders, epistemic uncertainty, and conflicting cues, it does not experimentally establish how a workplace briefing presents stale, uncertain, disputed, or incompletely investigated state, or how alternative presentations affect workplace decisions.
    suggested query: "uncertainty visualization" workplace decision support stale disputed incomplete information briefing
    searched in rounds: [1, 2, 3] (still open)

Papers already reviewed in earlier rounds (do NOT list them again):
2107.14691, 2109.06896, 2202.07088, 2403.01365, doi-10-1007-978-3-319-67684-5-24, doi-10-1016-j-cag-2014-02-006, doi-10-1016-j-eswa-2021-114890, doi-10-1016-j-eswa-2021-115626, doi-10-1016-j-knosys-2013-02-015, doi-10-1093-jcmc-zmac001, doi-10-1098-rsos-181870, doi-10-1109-fuzz-ieee-2016-7737835, doi-10-1136-amiajnl-2014-002945, doi-10-1145-1056808-1057071, doi-10-1145-1557019-1557124, doi-10-1145-2063576-2063683, doi-10-1145-2523813, doi-10-1145-290941-291025, doi-10-1145-2998181-2998251, doi-10-1145-3705328-3748164, doi-10-1145-634067-634150, doi-10-1145-642611-642672, doi-10-1155-2016-1340973, doi-10-1177-1071181322661236, doi-10-1186-s41235-019-0195-y, doi-10-1207-s15327051hci2001-2-3, doi-10-1609-icwsm-v12i1-15014, doi-10-18653-v1-2007-sigdial-1-4, doi-10-18653-v1-2024-acl-long-390, doi-10-18653-v1-2026-acl-long-1149, doi-10-18653-v1-d19-1386, doi-10-3389-fpsyg-2014-00657, doi-10-3758-bf03201140, doi-10-3758-s13421-025-01708-x, doi-10-6028-nist-sp-500-302-tempsumm-overview, doi-10-64898-2025-11-28-25341233, manual-0839b98ee7, manual-13a21477e7, manual-1d6b22c7ad, manual-39435af3dd, manual-4cb48c423e, manual-50ed5dc808, manual-c2f56a571b

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
