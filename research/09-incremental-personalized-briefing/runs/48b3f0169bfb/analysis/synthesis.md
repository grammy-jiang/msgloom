# Executive Summary

Across 13 distinct studies, direct workplace-email evidence shows that perceived message importance and triage depend on work relevance, consequences of delay, recency, collaborators, projects, role, and heterogeneous processing habits. Separate reminder research shows that usefulness is influenced by forgotten-task recovery, staleness, interaction patterns, and workstyle; likelihood of forgetting is therefore a reminder-selection/value consideration, not an established determinant of perceived priority. Personalized email-priority models improve with user-specific social/context features, while static email summarization remains vulnerable to intent, attribution, length, and evaluation-metric problems. Transfer-domain studies contribute mechanisms for novelty control, context-conditioned continuation, personalization, decision-focused selection, and action-item structure, but do not validate longitudinal workplace briefings. No admitted paper directly evaluates a briefing that jointly distinguishes new developments, still-open work, resolved or superseded state, hard obligations, and personalized ranking across successive report cycles.

# Themes

## Evidence-backed findings

1. In direct email studies, perceived importance and triage are shaped by work relevance, consequences of delay, recency, collaborators, active projects, role, and heterogeneous processing strategies; the studies do not establish one universal priority policy. [doi-10-1093-jcmc-zmac001] [doi-10-1145-1056808-1057071]

2. Personalized email-priority prediction improved when user-specific social-network information was added to conventional message features. A separate personalized-email study found flexible order-based classification more accurate than support-vector ordinal regression on its email data. [doi-10-1145-1557019-1557124] [doi-10-1145-2063576-2063683]

3. The classification-versus-ordinal-regression result was domain-specific rather than general: the same study reported that support-vector ordinal regression performed better on its seven UCI-derived ordinal benchmarks than the classification approaches. [doi-10-1145-2063576-2063683]

4. In the Microsoft reminder study, users valued reminders that recovered forgotten tasks, while stale or inaccurate surfaced state was a recurring source of dissatisfaction. Low-importance or non-urgent tasks were among the categories participants commonly reported forgetting. [2403.01365]

5. The Microsoft reminder study associated briefing interaction and perceived value with several workstyle variables, but it did not establish those workstyle variables or likelihood of forgetting as determinants of perceived message priority. Importance and urgency were studied separately through employee judgments of message characteristics. [2403.01365] [doi-10-1093-jcmc-zmac001]

6. Static email-thread summarization remains difficult on discourse-critical information. EmailSum reports errors involving sender intention and sender/receiver attribution, performance degradation with longer threads, and poor correlation between ROUGE or BERTScore and human judgments. [2107.14691]

7. On a static Enron email-summarization corpus, local clue-word conversational cohesion outperformed the tested PageRank variants, adding subjective-language evidence improved pyramid precision, and human annotators distinguished essential from optional supporting sentences. [manual-c2f56a571b]

8. ContactMap specifically produced higher task success and lower completion time than participants' normal email interfaces for the collaborative-task-management activities tested. TeleNotes provides different evidence: during its qualitative deployment, users made use of task-oriented spatial piles and short reminder annotations while continuing to use conventional chronological email for recent events. The measured ContactMap result should therefore not be generalized to TeleNotes or to task-centered representations as a class. [doi-10-1207-s15327051hci2001-2-3]

9. In the Wikipedia-derived Summary Cloze task, preceding summary context improved learned content selection and generation and was used with coverage to discourage local repetition. The learned selector remained substantially below oracle extraction. These are transfer results from Wikipedia-derived summarization, not direct workplace-briefing validation. [doi-10-18653-v1-d19-1386]

10. Several transfer-domain studies validate different mechanisms, but not their combination. MMR explicitly trades query relevance against novelty in retrieval and summarization, with only preliminary evidence for its strongest multi-document claims. [doi-10-1145-290941-291025] Interactive personalized summarization on news-event collections adapted summaries from user feedback and produced user-specific preferences that could diverge from generic ROUGE references. [manual-13a21477e7] Decision-Focused Summarization on restaurant reviews improved decision faithfulness and representativeness while sacrificing some coherence and grammaticality. [2109.06896] Structured action-item modeling on research-group meetings improved action-item detection and timeframe extraction, while task-description extraction remained weak. [doi-10-18653-v1-2007-sigdial-1-4]

11. Human-oriented evaluation can diverge materially from generic overlap metrics. EmailSum found weak ROUGE/BERTScore correlations with human judgments; personalized news summaries could receive stronger user-specific ratings without the best ROUGE scores; and Summary Cloze notes that multiple valid next sentences limit single-reference ROUGE evaluation. [2107.14691] [manual-13a21477e7] [doi-10-18653-v1-d19-1386]

The recurring themes are therefore contextual rather than universal priority; personalization from user-specific signals; reminder value from forgotten-work recovery and freshness; repetition control through prior context or diversity mechanisms; structural cues for task and conversational information; and substantial limitations in generic summary-overlap evaluation.

# Contradictions

No direct cross-paper contradiction met the required criterion of two papers answering the same question under comparable conditions.

Several apparent tensions are scope qualifications rather than contradictions. The classification-versus-ordinal-regression reversal occurs between personalized email and UCI-derived ordinal tasks within the same study, so it demonstrates sensitivity to data assumptions rather than contradictory evidence. [doi-10-1145-2063576-2063683]

Likewise, the observation that some triage users clear low-importance mail early [doi-10-1145-1056808-1057071] does not contradict the finding that low-importance or non-urgent tasks can be easy to forget [2403.01365]. The former concerns processing order during inbox triage; the latter concerns reminder usefulness and forgotten collaborative tasks.

The divergence between generic ROUGE scores and personalized preferences in news summarization [manual-13a21477e7] is also compatible with EmailSum's weak metric-human correlation [2107.14691] rather than contradictory: both identify limitations of generic overlap metrics under different tasks.

# Open Gaps

## gap-1 — ACADEMIC, HIGH

This corpus does not directly evaluate a longitudinal workplace briefing that, across successive report cycles, distinguishes newly changed information from unchanged-but-still-open work while suppressing resolved or superseded information. Static email summarization and Summary Cloze provide only adjacent evidence. [2107.14691] [doi-10-18653-v1-d19-1386] [2403.01365]

Suggested query: `"incremental summarization" workplace email longitudinal new developments unresolved superseded briefing`

Status: **open**.

## gap-2 — ACADEMIC, HIGH

This corpus does not establish how explicit user rules or response obligations should interact with softer personalized importance, triage, reminder-value, or forgetting signals in briefing selection, nor does it test whether separating these signal classes improves outcomes. The admitted studies investigate these constructs separately. [doi-10-1093-jcmc-zmac001] [doi-10-1145-1056808-1057071] [doi-10-1145-1557019-1557124] [2403.01365]

Suggested query: `"response obligation" email priority personalization hard constraints user rules briefing triage`

Status: **open**.

## gap-3 — ACADEMIC, HIGH

Long-term adaptation to changing roles, projects, priorities, feedback, and work patterns is not directly evaluated in the admitted personalized-email or reminder studies. Existing personalized models use short observation periods, static per-user training, or transfer-domain interactions. [doi-10-1145-1557019-1557124] [doi-10-1145-2063576-2063683] [2403.01365] [manual-13a21477e7]

Suggested query: `"longitudinal" personalized email prioritization preference drift adaptive summarization workplace`

Status: **open**.

## gap-4 — ACADEMIC, HIGH

The corpus does not provide an end-to-end evaluation of briefing content selection that jointly measures omission of decision-essential work, redundant repetition, false alerts, and preservation of unresolved important state over repeated cycles. The papers instead evaluate subsets such as salience, overlap, decision faithfulness, representativeness, or redundancy. [2107.14691] [2109.06896] [doi-10-18653-v1-d19-1386] [doi-10-1145-290941-291025]

Suggested query: `"coverage-aware summarization" omission redundancy unresolved actions longitudinal briefing evaluation`

Status: **open**.

## gap-5 — ACADEMIC, MEDIUM

The admitted studies do not determine how reminder usefulness or likelihood of forgetting should be combined with perceived importance, urgency, recency, or personalized priority when selecting briefing content. Reminder usefulness and perceived priority must therefore remain empirically distinct in the current evidence base. [2403.01365] [doi-10-1093-jcmc-zmac001] [doi-10-1145-1056808-1057071]

Suggested query: `"email reminder" forgetting probability task priority importance selection personalized briefing`

Status: **open**.

## gap-6 — ACADEMIC, HIGH

No admitted paper evaluates Topic- or work-item-level incremental briefing across multiple conversations and sources. Direct email summarization operates mainly on static threads or conversations, while broader selection mechanisms come from transfer domains. [2107.14691] [manual-c2f56a571b] [doi-10-1207-s15327051hci2001-2-3]

Suggested query: `"topic-focused summarization" cross-thread email workplace multi-source incremental work item`

Status: **open**.

## gap-7 — ACADEMIC, HIGH

One direct workplace reminder study establishes that stale or inaccurate surfaced state was a recurring source of dissatisfaction. It does not experimentally establish how a briefing should present stale, uncertain, disputed, or incompletely investigated state, nor compare the effects of alternative presentations on user decisions. [2403.01365]

Suggested query: `uncertainty stale disputed incomplete state display workplace briefing reminder user study`

Status: **open**.

## gap-8 — ENGINEERING, HIGH

Candidate mechanisms from this corpus have not been compared in one reproducible cycle-based benchmark with chronological holdouts, independently labeled new/open/resolved/superseded state, user-specific priority labels, and explicit omission and repetition errors. Relevant papers separately demonstrate chronological splitting, static email evaluation, context-conditioned continuation, and reminder-use observations. [doi-10-1145-2063576-2063683] [2107.14691] [doi-10-18653-v1-d19-1386] [2403.01365]

Status: **open**.

Because the complete previous synthesis and its prior gap inventory were not supplied, exact one-to-one reconstruction of every unquoted prior gap identifier cannot be independently verified. The status set above preserves the reviewer-referenced **gap-2** explicitly and conservatively leaves the reconstructed gaps open rather than claiming closure unsupported by the corpus.

# Actionable Insights

- **Synthesis-derived recommendation:** evaluate a cycle-based briefing formulation that represents at least new developments, unchanged-but-still-open items, and information no longer eligible for repetition as distinct experimental categories. The admitted literature does not validate this combined formulation.

- **Synthesis-derived recommendation:** treat separation of explicit user rules or response obligations from softer personalized priority signals as a candidate design hypothesis, not an established prescription, and test it explicitly under gap-2.

- **Synthesis-derived recommendation:** treat explicit visibility for stale, uncertain, disputed, or incompletely investigated state as an evaluation/design hypothesis under gap-7. Compare alternative presentations rather than assuming that maintaining one particular representation is already evidence-backed.

- **Synthesis-derived recommendation:** evaluate reminder-selection signals such as likelihood of forgetting separately from perceived message importance and urgency so their incremental contributions can be measured without conflating distinct constructs.

- **Synthesis-derived recommendation:** use novelty-aware reranking, prior-summary conditioning, interactive personalization, decision-focused selection, and structured action extraction only as candidate mechanisms until they are evaluated on the target workplace briefing task. Their current evidence comes respectively from retrieval/summarization experiments, Wikipedia-derived summarization, news collections, restaurant reviews, and research-group meetings.

- **Synthesis-derived recommendation:** construct evaluation around chronological report cycles and measure missed essential content, repeated or superseded content, false alerts, stale-state presentation, user-specific priority errors, and human decision usefulness in addition to generic overlap metrics.

- **Synthesis-derived recommendation:** where personalization is evaluated, include preference drift and changing project or role context rather than assuming that a per-user priority model remains stationary.

# Confidence Summary

The corpus provides well-supported design principles at the level of separate components. Direct email studies establish contextual and personalized aspects of perceived importance and triage. [doi-10-1093-jcmc-zmac001] [doi-10-1145-1056808-1057071] [doi-10-1145-1557019-1557124] [doi-10-1145-2063576-2063683] A workplace reminder study documents value from recovering forgotten work and dissatisfaction with stale or inaccurate state. [2403.01365] Direct email-summarization studies identify discourse, attribution, length, structural, and evaluation problems. [2107.14691] [manual-c2f56a571b]

Confidence is lower for any longitudinal synthesis of those mechanisms because no admitted paper evaluates the combined problem. Wikipedia-derived summarization [doi-10-18653-v1-d19-1386], news personalization [manual-13a21477e7], MMR retrieval and summarization [doi-10-1145-290941-291025], restaurant-review decision-focused summarization [2109.06896], and research-group meeting action-item processing [doi-10-18653-v1-2007-sigdial-1-4] are transfer evidence only. They support candidate mechanisms or evaluation ideas, not production workplace-briefing claims.

# Limitations

- The 13 analyses cover 13 distinct papers, but the corpus is heterogeneous in task, domain, era, sample size, and evaluation methodology.
- Several direct workplace studies rely substantially on self-report, small participant samples, one organization, or older email practices, limiting generalization to contemporary multi-channel work environments. [2403.01365] [doi-10-1145-1056808-1057071] [doi-10-1145-1557019-1557124] [doi-10-1207-s15327051hci2001-2-3]
- EmailSum and the Enron conversational-summarization study evaluate static conversations or completed threads rather than successive user briefings. [2107.14691] [manual-c2f56a571b]
- The Wikipedia-derived Summary Cloze results are transfer evidence about context-conditioned content selection and repetition, not direct evidence for workplace reporting. [doi-10-18653-v1-d19-1386]
- The interactive personalized summarization study uses news-event collections and only three evaluators; its personalization results are transfer evidence. [manual-13a21477e7]
- The MMR evidence comes from retrieval and summarization experiments with limited or preliminary multi-document evaluation; it does not establish longitudinal workplace novelty handling. [doi-10-1145-290941-291025]
- Decision-Focused Summarization is evaluated on restaurant reviews and a future-rating task; its decision-faithfulness and representativeness results are transfer evidence. [2109.06896]
- The action-item study uses research-group meetings and modest detection accuracy, with task-description extraction remaining weak; it is transfer evidence for workplace-email briefing. [doi-10-18653-v1-2007-sigdial-1-4]
- The project handoffs concerning state, supersession, structured evidence, and earlier Topics are inherited context only and were not used as evidence for findings or gap closure.
- No cross-paper contradiction met the required criterion of two studies answering the same question under comparable conditions. Apparent differences were retained as scope qualifications rather than manufactured contradictions.
- The complete previous synthesis and prior gap inventory were not supplied. Consequently, the gap-status mapping preserves the explicitly reviewer-referenced gap-2 and avoids claiming resolution of any reconstructed gap whose closure is not demonstrated by the admitted papers.
