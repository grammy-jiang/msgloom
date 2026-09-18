# Executive Summary

Across 29 analyzed papers, the literature supports several component-level capabilities but not an integrated longitudinal workplace briefing system. Email studies show that task and salience judgments are user- and context-dependent, that task-centered organization can improve retrieval and handling, and that static thread summarization still suffers role, intent, and length-related errors. Temporal summarization and clinical-transfer work show that incremental processing can preserve dated context and reduce repeated processing, while novelty-oriented methods reduce redundant content. Reminder studies show that reminder value is not equivalent to urgency: forgotten low-importance tasks can matter, and reminders linking a cue to an intended action outperform weaker reminder forms in laboratory tasks. Personalized ranking and interactive preference learning can improve user-specific outcomes, but long-term workplace adaptation remains untested. Evaluation evidence exposes trade-offs among coverage, redundancy, latency, coherence, and user preference, with weak correspondence between overlap metrics and human judgments in several summarization settings.

# Themes

- **Incremental processing and temporal representations.** Incremental processing is demonstrated in news-timeline and clinical-record transfer domains, including stream-wise event clustering and dated change-focused patient summaries [doi-10-18653-v1-2024-acl-long-390] [doi-10-64898-2025-11-28-25341233]. These studies do not directly evaluate explicit workplace work-item lifecycle state.

- **Novelty depends on prior information state.** MMR explicitly balances relevance against similarity to already selected material, Summary Cloze benefits from conditioning on the summary-so-far, and TREC temporal summarization evaluates novel updates separately from overall comprehensiveness [doi-10-1145-290941-291025] [doi-10-18653-v1-d19-1386] [doi-10-6028-nist-sp-500-302-tempsumm-overview].

- **Priority is personal and contextual.** Workplace users employ heterogeneous triage strategies, perceived importance depends on work relevance and consequences, and social-network-derived features improve personalized email-priority prediction in the studied collections [doi-10-1145-1056808-1057071] [doi-10-1093-jcmc-zmac001] [doi-10-1145-1557019-1557124].

- **Reminder value differs from urgency.** Microsoft workers reported value from reminders for forgotten low-importance, ad hoc, and small tasks, while prospective-memory experiments found reminder effectiveness depended strongly on whether the reminder linked the target cue and intended action [2403.01365] [doi-10-3758-bf03201140].

- **Selection depends on the objective.** Decision-focused selection, omission-sensitive clinical problem selection, and interactive personalized summarization each demonstrate that different objectives favor different content selections [2109.06896] [manual-1d6b22c7ad] [manual-13a21477e7].

- **Overlap metrics are incomplete proxies.** EmailSum, TAC update summarization, Summary Cloze, and interactive personalized summarization all expose situations in which ROUGE-style overlap does not fully represent human quality, valid alternative content, or personalized preference [2107.14691] [manual-39435af3dd] [doi-10-18653-v1-d19-1386] [manual-13a21477e7].

- **Uncertainty effects are presentation- and task-dependent.** The uncertainty-communication review finds no universal trust penalty from acknowledging uncertainty, while the Verifi study finds conflicting evidence cues associated with more uncertainty and error [doi-10-1098-rsos-181870] [doi-10-1609-icwsm-v12i1-15014].

# Findings

1. **Static email-thread summarization remains difficult as context grows.** In EmailSum, whole-thread T5 was a strong baseline, but performance declined as threads contained more emails; generated summaries also exhibited sender-intent and participant-role errors, and ROUGE/BERTScore correlated poorly with human judgments [2107.14691].

2. **Task-centered workplace-email representations have produced measurable benefits in small studies.** ContactMap increased task success and reduced completion time in its controlled evaluation, while Taskmaster participants responded positively to persistent task-centric collections, reminders, deadlines, and related metadata [doi-10-1207-s15327051hci2001-2-3] [doi-10-1145-642611-642672].

3. **Reminder usefulness is not equivalent to urgency.** In the Microsoft workplace study, users often valued reminders for forgotten low-importance, ad hoc, or small tasks [2403.01365]. In laboratory prospective-memory experiments, reminders linking the triggering event with the intended action outperformed target-only or action-only reminders [doi-10-3758-bf03201140]. These studies cover different settings and do not jointly validate a workplace reminder-selection model.

4. **Email priority varies by user and work context.** Workers reported different triage strategies and context-dependent importance judgments [doi-10-1145-1056808-1057071], perceived importance was tied to personal work relevance and consequential stakeholders or delay [doi-10-1093-jcmc-zmac001], and personalized social-network features reduced prediction error in the evaluated personal-email models [doi-10-1145-1557019-1557124].

5. **Interactive personalization can change what users regard as a good summary.** In news summarization, sparse interaction feedback shifted summaries toward individual interests and raised personalized human ratings, while increased personalization could lower generic ROUGE when user interests differed from the reference summaries [manual-13a21477e7].

6. **Continual adaptation improves performance under preference drift in recommender-system transfer domains.** Incremental recommenders outperformed corresponding batch approaches under several supermarket drift and cold-start conditions [doi-10-1016-j-eswa-2021-114890], and MTUPD's multi-transition temporal preference model outperformed its evaluated dynamic collaborative-filtering comparators across eight recommendation datasets [doi-10-1016-j-eswa-2021-115626].

7. **Incremental summarization itself is technically demonstrated outside the target workplace domain.** LLM-TLS incrementally updates event and topic timelines as text arrives [doi-10-18653-v1-2024-acl-long-390], and CLIN-SUMM incrementally incorporates newly documented clinical information into dated patient representations without using future notes [doi-10-64898-2025-11-28-25341233].

8. **Previous-summary context and novelty objectives can reduce redundant selection.** Summary Cloze obtains better content selection and generation when conditioned on preceding summary context and uses coverage to discourage repetition [doi-10-18653-v1-d19-1386]. MMR directly trades query relevance against similarity to already selected material [doi-10-1145-290941-291025]. TREC temporal summarization separately measures novel-update gain and comprehensiveness and observes a gain/coverage trade-off [doi-10-6028-nist-sp-500-302-tempsumm-overview].

9. **Content-selection results depend on what errors are valued.** DecSum strongly improved decision faithfulness and representativeness relative to tested baselines but lost some grammaticality and coherence [2109.06896]. In clinical problem selection, feature selection performed better under equal precision/recall weighting, whereas heavier recall weighting through F2 favored retaining more candidate evidence [manual-1d6b22c7ad].

10. **There is no single empirically supported uncertainty-presentation rule.** The uncertainty review reports effects varying by audience and expression format and finds no simple rule that uncertainty disclosure reduces trust [doi-10-1098-rsos-181870]. In Verifi, conflicting cues were associated with greater uncertainty and more inaccurate judgments [doi-10-1609-icwsm-v12i1-15014].

11. **Automatic overlap evaluation can diverge from human usefulness.** EmailSum reports weak metric-human correlations [2107.14691]; TAC 2008 found automatic metrics did not reproduce the clear human-versus-machine separation seen under manual evaluation [manual-39435af3dd]; Summary Cloze notes multiple valid next sentences despite a single reference [doi-10-18653-v1-d19-1386]; and personalized news summaries could receive better user ratings without the best generic ROUGE [manual-13a21477e7].

# Contradictions

No direct cross-paper contradiction met the required same-question and comparable-condition criterion.

Several apparent tensions are scope qualifications rather than contradictions. For example, classification beat ordinal regression on personalized email while ordinal regression won on UCI-derived benchmarks within the same study; the datasets and model assumptions differed [doi-10-1145-2063576-2063683]. Likewise, workplace users reporting that low-importance tasks are often forgotten [2403.01365] does not contradict prospective-memory evidence that experimentally increasing an intention's importance can improve recall [doi-10-3389-fpsyg-2014-00657]; the studies ask different questions.

# Open Gaps

- **gap-1 — ACADEMIC, HIGH — OPEN.** This corpus does not directly evaluate a longitudinal workplace briefing that, across successive report cycles, distinguishes newly changed information from unchanged-but-still-open work while suppressing resolved or superseded information. Incremental mechanisms exist in news and clinical transfer domains [doi-10-18653-v1-2024-acl-long-390] [doi-10-64898-2025-11-28-25341233], and stale state is a reported problem in workplace reminders [2403.01365], but those results do not close the gap. Suggested query: `"incremental summarization" longitudinal workplace email briefing new developments unresolved resolved superseded`

- **gap-2 — ACADEMIC, HIGH — OPEN.** The corpus separately studies user importance, contextual priority, reminder value, prospective-memory importance, and personalized ranking [doi-10-1093-jcmc-zmac001] [doi-10-1145-1557019-1557124] [2403.01365] [doi-10-3389-fpsyg-2014-00657], but does not establish how explicit rules or response obligations interact with these softer signals. Suggested query: `"email prioritization" hard constraints soft preferences response obligation personalized triage user rules`

- **gap-3 — ACADEMIC, HIGH — OPEN.** Long-term adaptation to changing workplace roles, projects, priorities, feedback, and work patterns remains untested. Recommender-system studies demonstrate adaptation under drift [doi-10-1016-j-eswa-2021-114890] [doi-10-1016-j-eswa-2021-115626], and interactive multi-objective preference learning adapts over repeated interactions in other domains [manual-4cb48c423e], but these are transfer results. Suggested query: `"longitudinal personalization" email prioritization preference drift adaptive workplace summarization`

- **gap-4 — ACADEMIC, HIGH — OPEN.** No admitted study jointly measures omission of decision-essential work, redundant repetition, false alerts, and preservation of unresolved important state across repeated workplace briefing cycles. TREC supplies gain, comprehensiveness, latency, and verbosity measures [doi-10-6028-nist-sp-500-302-tempsumm-overview], while other studies separately expose update difficulty, repetition, or omission-sensitive objectives [manual-39435af3dd] [doi-10-18653-v1-d19-1386] [manual-1d6b22c7ad]. Suggested query: `"longitudinal summarization" omission redundancy false alerts unresolved state evaluation briefing`

- **gap-5 — ACADEMIC, MEDIUM — OPEN.** Reminder usefulness, forgetting likelihood, importance, urgency, recency, and personalized priority are studied separately rather than as a combined briefing-selection problem [2403.01365] [doi-10-1093-jcmc-zmac001] [doi-10-3389-fpsyg-2014-00657] [doi-10-3758-bf03201140]. Suggested query: `"email reminder" forgetting importance urgency recency personalized priority task selection`

- **gap-6 — ACADEMIC, HIGH — OPEN.** Direct email summarization studies remain primarily thread- or conversation-level [2107.14691] [manual-c2f56a571b]. Incremental multi-event methods operate in news and clinical transfer domains [doi-10-18653-v1-2024-acl-long-390] [doi-10-64898-2025-11-28-25341233]. No admitted paper evaluates Topic- or work-item-level incremental briefing across multiple workplace conversations and sources. Suggested query: `"cross-thread summarization" email multi-source incremental topic work item workplace`

- **gap-7 — ACADEMIC, HIGH — OPEN.** The corpus now contains relevant adjacent evidence: stale or inaccurate reminders reduce perceived value [2403.01365], uncertainty effects depend on expression and audience [doi-10-1098-rsos-181870], conflicting cues increase errors [doi-10-1609-icwsm-v12i1-15014], and inadequate uncertainty/negation handling can surface misleading clinical problems [doi-10-1136-amiajnl-2014-002945]. No controlled workplace-briefing experiment compares alternative presentations of stale, disputed, uncertain, or incompletely investigated work-item state. Suggested query: `"uncertainty visualization" stale disputed incomplete information workplace decision support briefing`

- **gap-8 — ENGINEERING, HIGH — OPEN.** The admitted literature provides individual mechanisms and evaluation components but no reproducible cycle-based comparison using chronological holdouts, independent new/open/resolved/superseded gold state, user-specific priority labels, and explicit omission/repetition errors [doi-10-6028-nist-sp-500-302-tempsumm-overview] [manual-39435af3dd] [doi-10-1016-j-eswa-2021-114890] [2107.14691].

# Actionable Insights

- **Synthesis-derived recommendation:** Represent briefing selection as a multi-objective decision with explicit, separately inspectable signals for lifecycle state, novelty, decision importance, reminder value, user preference, and uncertainty rather than collapsing them into one undifferentiated score.

- **Synthesis-derived recommendation:** Maintain a prior accepted briefing state for every Topic and evaluate each later cycle against that state so that new information, unchanged open information, resolved information, and superseded information can be tested independently.

- **Synthesis-derived recommendation:** Treat explicit user rules and response obligations as a separate decision layer from learned importance, predicted response likelihood, recency, or forgetting risk until direct evidence establishes a safe way to combine them.

- **Synthesis-derived recommendation:** Build the engineering benchmark around cycle-level false negatives and false positives, including missed decision-essential work, missing carry-forward items, repeated unchanged content, stale/resolved alerts, and omitted supersession.

- **Synthesis-derived recommendation:** Evaluate personalization chronologically and under simulated or observed preference drift, preserving hard constraints while measuring whether user feedback improves ranking without increasing omission of important work.

- **Synthesis-derived recommendation:** Model reminder value separately from urgency and include enough context to identify both the triggering work item and the intended action when generating reminder-like briefing entries.

- **Synthesis-derived recommendation:** Expose uncertainty as structured state rather than silently resolving it, distinguishing uncertainty about the underlying work-item state from uncertainty about evidence quality or completeness.

- **Synthesis-derived recommendation:** Do not use ROUGE-style overlap as the primary acceptance criterion for this briefing problem; pair semantic and factual evaluation with explicit coverage, omission, repetition, state-transition, and user-task measures.

# Confidence Summary

The corpus provides well-supported design principles for context-aware content selection, redundancy control, task-centered organization, personalized priority, reminder semantics, incremental processing, multi-objective evaluation, and uncertainty communication. Confidence is highest for the component-level findings because several are supported by controlled experiments or multiple independent studies.

Confidence is substantially lower for transfer to a production longitudinal workplace briefing. The incremental methods are mainly evaluated on news, recommendation, or clinical data, while workplace studies are often small, static, self-reported, or limited to individual email threads. No admitted paper validates the complete combination of cross-thread Topic identity, lifecycle-state carry-forward, adaptive user prioritization, reminder value, uncertainty presentation, and omission/repetition control across repeated briefing cycles.

# Limitations

- The corpus spans email, news, recommendation, clinical records, prospective-memory experiments, misinformation analysis, and multi-objective preference learning; transfer-domain results do not establish production workplace performance.
- Several workplace studies use small samples, one organization, older email environments, self-reported behavior, or short deployments.
- Two admitted sources are abstract-only, limiting verification of detailed methods and results [doi-10-1007-978-3-319-67684-5-24] [doi-10-1177-1071181322661236].
- The corpus contains component evidence for incrementality, personalization, novelty, reminders, uncertainty, and evaluation, but no paper tests their combined use in one longitudinal workplace system.
- Static email summarization evidence is mostly conversation- or thread-level rather than cross-thread work-item-level evidence.
- Incremental news and clinical summarization demonstrate mechanisms under transfer settings but do not provide direct evidence for new/open/resolved/superseded workplace state tracking.
- Personalization studies generally cover short observation periods or non-workplace interaction tasks, leaving sustained role and project drift weakly evidenced.
- The supplied per-paper analyses, rather than independently re-opened full texts, are the evidentiary basis for this synthesis.
- Inherited Topic 06 and Topic 08 handoffs are treated only as project context and are not used as evidence for findings or gap closure.
- No direct cross-paper contradiction met the same-question and comparable-condition criterion; differences arising from changed datasets, domains, definitions, or experimental manipulations were retained as scope qualifications rather than labeled contradictions.
