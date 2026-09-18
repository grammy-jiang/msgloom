# Direct empirical evaluations of longitudinal cross-thread workplace briefing: cycle-by-cycle new/open/resolved/superseded work-item tracking, obligation-versus-preference selection, adaptive personalization under preference drift, and joint omission/repetition/false-alert evaluation. academic terminology analysis

## Product problem

The target is not ordinary email summarization and not ordinary novelty detection. The research object is a **persistent, user-specific briefing over repeated cycles**, organized around stable work matters rather than individual messages.

At cycle \(t\), the system must jointly decide:

- what is genuinely new since the previously accepted view;
- what is unchanged but remains open, actionable, risky, due, disputed, or otherwise decision-essential;
- what has become resolved, revoked, superseded, or stale and therefore should no longer be repeated as current;
- what supporting context must accompany a change so that the user can interpret it correctly;
- which information is mandatory because of explicit rules or response obligations;
- which information is merely preferred because of learned user importance, urgency, reminder value, or likely forgetting;
- how those softer preferences should adapt when the user's roles, projects, priorities, and work patterns change;
- how stale, uncertain, disputed, or incompletely investigated state should be presented;
- how to measure omissions, unnecessary repetitions, false alerts, and failure to preserve unresolved important work together.

This combination does not map cleanly onto one established academic task. The highest-value search strategy therefore separates **direct workplace families** from **transfer families** and refuses to treat transfer evidence as production-email validation.

`DIRECT` below means that the family directly studies workplace email, workplace tasks, or a closely matching workplace information-selection problem. It does **not** mean that the family already satisfies the end-to-end msgloom contract. `TRANSFER` means that the mechanism or evaluation can plausibly be reused but was principally studied in another domain or under a weaker task definition.

## Seed keyword audit

| Seed | Academic meaning | Fit | Main risk |
| --- | --- | --- | --- |
| update summarization | Summarize later information assuming earlier information has already been read, emphasizing relevant new content. | STRONG | Canonical DUC/TAC tasks suppress old information but do not preserve unchanged open obligations or lifecycle state. |
| incremental summarization | Update a summary incrementally as new documents, events, or utterances arrive. | STRONG | “Incremental” may refer only to processing architecture rather than persistent user-facing state. |
| temporal summarization | Time-aware summarization of an evolving information stream or topic. | STRONG | Usually event-centric; temporal relevance does not imply open/resolved/superseded work state. |
| timeline summarization | Produce a chronological sequence of salient events. | MODERATE | A timeline answers “what happened,” not necessarily “what remains actionable.” |
| query-focused summarization | Select summary content according to a query or information need. | MODERATE | A query is weaker than persistent Triage rules, obligations, and user context. |
| query-focused multi-document summarization | Summarize multiple sources according to an explicit information need. | STRONG | Strong cross-source analogue, but usually static and not lifecycle-aware. |
| multi-document summarization | Produce one summary from several documents. | MODERATE | Far too broad without temporal, user, work-item, or update qualifiers. |
| entity-centric summarization | Aggregate and summarize information about an entity. | MODERATE | Entity identity is not work-item identity; one customer/person/project can contain many Topics. |
| event-centric summarization | Summarize facts and developments associated with an event. | MODERATE | Work items may outlive individual events and remain open without new events. |
| topic-focused summarization | Summarize information about a specified topic. | MODERATE | Academic “topic” commonly means subject/theme rather than msgloom's persistent work-matter identity. |
| novelty detection | Identify relevant content not already seen. | MODERATE | Novelty-only selection would wrongly remove unchanged unresolved work. |
| redundancy reduction in summarization | Suppress semantically repetitive summary content. | MODERATE | Legitimate repeated reminders or persistent critical state may be removed. |
| delta summarization | Informal label for summarizing differences or changes. | WEAK | Unstable term with large software-diff and document-version false-positive space. |
| information update detection | Detect additions, changes, corrections, or supersession relative to prior information. | MODERATE | Change detection does not answer whether unchanged content must remain visible. |
| personalized summarization | Select summary content according to a user profile, interests, knowledge, or feedback. | STRONG | User interest can incorrectly override explicit obligations or mandatory coverage. |
| user-adaptive summarization | Adapt summarization to observed user interaction or changing user characteristics. | STRONG | Often short-term or interface adaptation rather than long-term preference drift. |
| personalized ranking | User-specific ranking based on profile, history, or context. | MODERATE | Dominated by search/recommendation literature and normally lacks hard-rule precedence. |
| learning to rank | Learn an ordering from relevance or utility signals. | WEAK | Too generic to identify the project's capability. |
| preference-aware ranking | Ranking that explicitly accounts for user preferences. | MODERATE | Usually does not distinguish mandatory constraints from defeasible preferences. |
| email prioritization | Estimate urgency, importance, criticality, or delayed-review cost for incoming email. | STRONG | Priority or reply probability is not response obligation; usually message-level. |
| email triage | Review unhandled email and decide disposition, priority, action, or organization. | STRONG | Typically inbox/message-centric rather than cross-thread longitudinal briefing. |
| response priority prediction | Predict reply likelihood, reply timing, urgency, or response importance. | WEAK | High risk of treating observed response behavior as normative obligation. |
| salience estimation | Estimate important sentences, facts, entities, or events. | WEAK | Generic prominence is not user-specific decision value. |
| content selection | Choose which source units or facts enter generated output. | MODERATE | Extremely broad without task-specific qualifiers. |
| coverage-aware summarization | Explicitly optimize coverage while controlling compression or redundancy. | MODERATE | “Coverage” rarely means all due Topics, actions, deadlines, conditions, and risks. |
| constrained summarization | Generate a summary subject to explicit constraints. | MODERATE | Typical constraints are length, keywords, entities, or decoding restrictions rather than hard-rule precedence. |
| long-running conversation summarization | Summarize conversations spanning many turns or long durations. | STRONG | Usually confined to one conversation rather than one work item across multiple conversations. |
| incremental dialogue summarization | Update a dialogue summary as new turns arrive. | STRONG | Strong structural transfer, but normally single-thread and not work-item-centric. |
| notification prioritization | Rank, delay, suppress, or deliver notifications according to utility and interruption cost. | STRONG | Alert timing/suppression is not equivalent to briefing completeness. |
| digest generation | Produce a compact periodic collection or summary of many items. | WEAK | Weakly standardized and heavily contaminated by newsletters, recommendations, and product literature. |

The most important seed correction is that **novelty is only one component of the target**. A system can perform excellent update summarization and still fail msgloom by hiding an unchanged deadline or unresolved obligation.

Likewise, **email priority is not obligation**. Email prioritization, reply prediction, response-time prediction, and user engagement are useful signals, but discovery must not admit them as evidence that an item objectively requires a response.

Terms worth actively adding to discovery include:

- `multi-document update summarization`
- `stream summarization`
- `temporal summaries`
- `event threading`
- `information filtering`
- `adaptive information filtering`
- `task-centric email`
- `email task management`
- `email overload`
- `outstanding tasks`
- `attention-sensitive alerting`
- `expected cost of delayed review`
- `prospective memory`
- `task reminders`
- `stale reminders`
- `adaptive user modeling`
- `dynamic user modeling`
- `long-term user modeling`
- `preference drift`
- `concept drift`
- `continual personalization`
- `online learning to rank`
- `activity-centric computing`
- `activity-centric email`
- `work-item tracking`
- `action-item tracking`
- `hard constraints`
- `soft preferences`
- `lexicographic ranking`
- `uncertainty communication`
- `uncertainty visualization`
- `information staleness`
- `conflicting information`
- `incomplete information`
- `longitudinal evaluation`
- `prequential evaluation`

`delta summarization`, generic `learning to rank`, `response priority prediction`, generic `salience estimation`, and `digest generation` should be demoted to auxiliary terms rather than used as primary discovery anchors.

## Academic task families

### F1 — Update, temporal, and stream summarization — TRANSFER

This is the strongest established analogue for **what changed since the previous view**.

Known foundations include:

- *Temporal summaries of new topics* — James Allan, Rahul Gupta, Vikas Khandelwal (2001).
- *Overview of the TAC 2008 Update Summarization Task* — Hoa Trang Dang, Karolina Owczarzak (2008).

Canonical update summarization assumes that earlier documents have already been read and asks for new relevant information from a later set. That maps well to delta selection but poorly to unchanged unresolved work.

This family is therefore highly useful but remains transfer evidence unless a study explicitly maintains work state across repeated workplace briefing cycles.

### F2 — Novelty detection and redundancy control — TRANSFER

Known foundation:

- *Overview of the TREC 2002 Novelty Track* — Donna Harman (2002).

This family provides methods for determining whether information is genuinely new and whether output repeats already known material.

Its central failure mode for msgloom is equally important: a perfect novelty filter can be a bad briefing system because it may suppress an old but still-open request, deadline, risk, or commitment.

### F3 — Temporal event structure, event threading, and timelines — TRANSFER

Known examples include:

- *Event Threading within News Topics* — Ramesh Nallapati, Ao Feng, Fuchun Peng, James Allan (2004).
- *Temporal summaries of new topics* — Allan, Gupta, Khandelwal (2001).

These tasks reject the assumption that a topic is merely a flat collection of documents and instead model developments and dependencies through time. That is useful for distinguishing restatements from actual developments.

However, events are not equivalent to work items. A work item can stay important during periods with no new event.

### F4 — Query-focused and coverage-constrained multi-document content selection — TRANSFER

This family supplies techniques for:

- selecting from many sources;
- conditioning selection on an explicit information need;
- balancing coverage and redundancy;
- imposing selection constraints.

Its value for msgloom is mainly methodological. An explicit user query can approximate a report requirement, but it does not naturally express the required ordering:

1. hard permissions and explicit rules;
2. mandatory semantic/report coverage;
3. obligations;
4. softer personalized utility.

### F5 — Workplace email triage, prioritization, and task management — DIRECT

This is one of the strongest direct-domain families.

Relevant foundations include:

- *Diversity in the Use of Electronic Mail: A Preliminary Inquiry* — Wendy E. Mackay (1988).
- *Email Overload: Exploring Personal Information Management of Email* — Steve Whittaker, Candace Sidner (1996).
- *Taking Email to Task: The Design and Evaluation of a Task Management Centered Email Tool* — Victoria Bellotti, Nicolas Ducheneaut, Mark Howard, Ian Smith (2003).
- *Quality versus quantity: E-mail-centric task management and its relation with overload* — Bellotti, Ducheneaut, Howard, Rebecca E. Grinter (2005).

This literature is important because email has long been used as a task-management substrate containing outstanding work, delegated work, partially completed work, and items people fear losing.

The direct gap remains: managing tasks in an inbox is not the same as generating a cycle-by-cycle Topic briefing.

### F6 — Attention-sensitive alerting and notification utility — DIRECT

Known foundation:

- *Attention-Sensitive Alerting* — Eric Horvitz, Andy Jacobs, David Hovel (1999).

This family introduces useful concepts such as:

- urgency/criticality;
- expected cost of delayed review;
- interruption cost;
- selective alerting;
- user/context-dependent utility.

It is especially relevant to false-alert costs and user-specific priority.

The boundary is important: information that should not interrupt the user immediately may still have to appear in the next periodic briefing.

### F7 — Task reminders, prospective memory, and forgetting-sensitive support — DIRECT

This is the best terminology expansion for gap-5.

`prospective memory` is particularly useful because reminder research often frames the problem as supporting intended future actions rather than merely assigning importance scores.

Discovery should look for combinations of:

- forgetting likelihood;
- reminder usefulness;
- reminder timing;
- task importance;
- urgency;
- staleness;
- false reminders;
- outstanding email tasks.

Only workplace/email studies should count as direct evidence; generic cognitive or consumer reminder studies remain transfer evidence.

### F8 — Personalized summarization and user-model-conditioned selection — TRANSFER

Known example:

- *User-model based personalized summarization* — Alberto Díaz, Pablo Gervás (2007).

This family demonstrates that summary content can depend on long-term and short-term user interests and explicit feedback.

The missing distinction is crucial: user interest is a **soft preference**, whereas an explicit Triage rule, deadline, obligation, or risk can be mandatory even when it is not interesting.

### F9 — Adaptive user modeling, online personalization, and preference drift — TRANSFER

Known early example:

- *The Lumiere Project: Bayesian User Modeling for Inferring the Goals and Needs of Software Users* — Eric Horvitz, Jack Breese, David Heckerman, David Hovel, Koos Rommelse (1998).

Terminology should expand beyond `longitudinal personalization` to:

- adaptive user modeling;
- dynamic user modeling;
- changing goals;
- persistent user profiles;
- preference drift;
- concept drift;
- continual personalization;
- online learning;
- non-stationary user preferences.

This family is the most promising transfer literature for gap-3.

A fixed-profile personalization paper does not close gap-3.

### F10 — Long-running and incremental conversation summarization — TRANSFER

This family should search for incremental maintenance of:

- action items;
- decisions;
- commitments;
- unresolved questions;
- persistent dialogue state.

It is structurally close to msgloom because the summary evolves as evidence arrives.

The primary downgrade criterion is scope: a single Slack thread, meeting, or chat is not cross-thread Topic tracking.

### F11 — Cross-thread, activity-centric, and work-item-centric workplace aggregation — DIRECT

This is the most important direct search family for gap-6.

The search should deliberately try terminology such as:

- activity-centric computing;
- task-centric email;
- project-centric email;
- work-item tracking;
- cross-thread email;
- multi-thread task management;
- task aggregation across conversations.

A paper counts as direct only if the organizing unit survives across multiple workplace communications. Merely clustering similar messages or summarizing each thread independently does not qualify.

### F12 — Hard-constraint versus soft-preference ranking and selection — TRANSFER

This family is needed because the project's signal hierarchy does not map cleanly onto ordinary personalization.

Relevant academic formulations include:

- hard versus soft constraints;
- constrained ranking;
- lexicographic preference;
- preference learning under feasibility constraints;
- rule-constrained ranking;
- personalized ranking with mandatory constraints.

The discovery question for gap-2 is not merely whether rules and preferences can both be features. It is whether systems **structurally separate them**, so that learned preference cannot override mandatory selection.

### F13 — Uncertainty, staleness, conflict, and incomplete-information presentation — TRANSFER

For gap-7, use terminology from decision support and visualization rather than summarization alone:

- uncertainty communication;
- uncertainty visualization;
- information staleness;
- conflicting information;
- incomplete information;
- data quality;
- provenance uncertainty;
- disputed evidence.

The target paper must evaluate how presentation affects human interpretation or decisions, not merely estimate an uncertainty score.

### F14 — Joint longitudinal coverage, omission, repetition, and false-alert evaluation — TRANSFER

No single standard metric name should be assumed.

Discovery should combine evaluation concepts from:

- update summarization;
- novelty/redundancy evaluation;
- information filtering;
- notification false positives and false negatives;
- alert fatigue;
- longitudinal evaluation;
- concept-drift evaluation;
- prequential/online evaluation.

For msgloom, the desired unit is a **cycle × work-item state** evaluation, not average summary similarity.

The end-to-end benchmark must eventually be able to count separately:

- an important item omitted when it should have appeared;
- an unchanged item correctly carried forward;
- a resolved/superseded item incorrectly repeated;
- an irrelevant item incorrectly surfaced;
- a genuinely new development correctly surfaced;
- a state-changing development omitted;
- repeated wording that adds no decision value;
- mandatory content displaced by softer personalization.

## Query families

### F1 — Update, temporal, and stream summarization — TRANSFER

```text
"update summarization" longitudinal unresolved resolved superseded
"update summarization" "open" unresolved repeated cycles
"multi-document update summarization" evolving state
"temporal summarization" unresolved state persistence
"stream summarization" novelty persistence unresolved
"temporal summaries" evolving topic redundancy update
```

### F2 — Novelty detection and redundancy control — TRANSFER

```text
"novelty detection" summarization prior information redundancy
"novel information" summarization repeated updates
"redundancy reduction" update summarization evaluation
"novelty" "unresolved" summarization
"information filtering" novelty redundancy temporal
```

### F3 — Temporal event structure and event threading — TRANSFER

```text
"event threading" longitudinal summarization
"temporal event" summarization evolving topic
"timeline summarization" evolving state
"timeline summarization" redundancy update
"event-centric summarization" temporal evolution
```

### F4 — Query-focused and coverage-constrained multi-document selection — TRANSFER

```text
"query-focused multi-document summarization" update
"query-focused multi-document summarization" coverage redundancy
"coverage-aware summarization" important information redundancy
"constrained summarization" user requirements coverage
"multi-document summarization" actions deadlines decisions
"content selection" summarization mandatory information constraints
```

### F5 — Workplace email triage, priority, and task management — DIRECT

```text
"email prioritization" urgency importance task obligation
"email triage" action required priority
"email triage" task management outstanding
"email task management" outstanding tasks unresolved
"task-centric email" user study
"email overload" task management outstanding tasks
"email prioritization" user preferences rules
workplace email priority action required response
```

### F6 — Attention-sensitive alerting — DIRECT

```text
"attention-sensitive alerting" email
"notification prioritization" email urgency interruption
"expected cost of delayed review" email
"email alerting" urgency criticality user model
"notification management" workplace email importance
"email prioritization" interruption cost
```

### F7 — Reminders, forgetting, and prospective memory — DIRECT

```text
"email reminder" task forgetting importance urgency
"email task management" reminder forgetting
"prospective memory" email tasks reminders
"prospective memory" workplace reminders
"task reminder" importance urgency forgetting
"task reminder" stale reminder user study
workplace reminder usefulness task importance recency
```

### F8 — Personalized summarization — TRANSFER

```text
"personalized summarization" user preferences feedback
"personalized summarization" long term short term interests
"user-adaptive summarization" feedback
"personalized summarization" changing preferences
"user model" summarization preference adaptation
```

### F9 — Preference drift and adaptive user models — TRANSFER

```text
"adaptive user model" changing preferences longitudinal
"long-term user modeling" preference change
"preference drift" personalized ranking
"concept drift" personalization user profile
"continual personalization" user feedback
"online learning to rank" nonstationary preferences
"dynamic user model" changing goals preferences
"email prioritization" adaptive user model feedback longitudinal
"email triage" personalization longitudinal feedback
```

### F10 — Incremental/long-running dialogue summarization — TRANSFER

```text
"incremental dialogue summarization" unresolved tasks
"incremental dialogue summarization" action items
"long-running conversation summarization" actions decisions
"conversation summarization" commitments decisions action items
"meeting summarization" action item tracking longitudinal
"dialogue summarization" persistent state unresolved
```

### F11 — Cross-thread workplace work-item aggregation — DIRECT

```text
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
```

### F12 — Hard rules versus soft preferences — TRANSFER

```text
"hard constraints" "soft preferences" ranking
"hard constraints" "soft preferences" personalization
"constrained ranking" user preferences hard constraints
"personalized ranking" hard constraints soft preferences
"learning to rank" constraints user preferences
"preference learning" mandatory constraints soft preferences
"lexicographic" ranking hard constraints preferences
"rule-based" personalized ranking constraints
```

### F13 — Stale, uncertain, disputed, or incomplete state — TRANSFER

```text
"uncertainty visualization" decision making stale information
"uncertainty communication" decision support incomplete information
"stale information" decision support visualization
"conflicting information" visualization decision support
"incomplete information" workplace decision support visualization
"data staleness" uncertainty decision support
"provenance uncertainty" decision support
"disputed information" decision support presentation
```

### F14 — Joint longitudinal evaluation — TRANSFER

```text
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
```

## False friends and downgrade rules

Discovery should downgrade or exclude the following even when they match the literal query vocabulary:

1. **One-shot update summarization presented as longitudinal briefing.** A DUC/TAC-style A→B update is useful transfer evidence but does not demonstrate repeated-cycle maintenance.

2. **Pure novelty filtering.** If previously seen information is categorically removed, the system cannot satisfy the requirement to carry forward unchanged open work.

3. **Chronology-only timeline systems.** A timeline of events is not an open-work register.

4. **Text/software/database diffs.** `delta summarization` and `information update detection` can retrieve source-code, document revision, database, and web-page change research unrelated to semantic briefing selection.

5. **Static multi-document summarization.** Cross-document coverage alone is not longitudinal state management.

6. **Generic message importance.** Email importance, urgency, criticality, or response probability is not response obligation.

7. **Reply prediction treated as obligation.** A model that predicts whether someone historically replies must not be interpreted as a classifier of whether that person ought to reply.

8. **Spam, phishing, foldering, archive/delete, or generic inbox classification.** These are not briefing selection unless actionable work priority is explicitly studied.

9. **Recommendation/popularity ranking.** Product, media, social-feed, advertising, or generic personalized ranking is outside the target unless used strictly as transfer evidence for constraint handling or drift.

10. **Interest-only personalization.** A system that optimizes user interest without mandatory coverage can be harmful for msgloom.

11. **Fixed-profile personalization cited for preference drift.** A static user profile does not establish adaptation to changing roles or priorities.

12. **Generic concept drift.** Classification work under drift is only evaluation/method transfer unless it concerns personalized ranking or selection.

13. **Lexical/length-only constrained summarization.** A 100-word budget or forced keyword is not the same as mandatory semantic coverage.

14. **Coverage defined only as topic diversity or embedding dispersion.** Msgloom requires coverage of decision-essential work, not abstract diversity.

15. **Entity identity substituted for Topic identity.** One entity may participate in many independent work matters.

16. **Event identity substituted for work-item identity.** One work item can persist across many events.

17. **Single-thread dialogue summarization presented as cross-thread aggregation.** It remains transfer evidence.

18. **Similarity clustering presented as work-item identity.** Subject, participant, semantic, or embedding similarity is insufficient to establish that two communications refer to the same work matter.

19. **Notification click-through or engagement optimization.** These objectives are not workplace decision value.

20. **Notification timing presented as briefing selection.** A notification may correctly be suppressed now yet still be mandatory in the next scheduled briefing.

21. **Reminder studies without reminder-value failure analysis.** Prioritize work that considers usefulness, forgetting, staleness, importance, or false reminders.

22. **Statistical-uncertainty-only visualization.** Gap-7 specifically needs stale, disputed, conflicting, incomplete, or provisional information presented to decision makers.

23. **Summary evaluation limited to fluency or similarity.** ROUGE/BERTScore/coherence alone cannot close omission/repetition gaps.

24. **Aggregate precision/recall without error semantics.** Evaluation must distinguish missing important work from unnecessary output.

25. **Random train/test splits used to claim drift robustness.** Longitudinal adaptation requires chronological or online evaluation.

26. **Short-session adaptation used to claim long-term personalization.** Evidence must span meaningful temporal change.

27. **Action-item extraction without selection.** Identifying a task is upstream of deciding whether and how long it remains in the briefing.

28. **Meeting action extraction used as direct workplace cross-thread evidence.** It is normally transfer evidence.

29. **Naive completed-item deletion.** Relevant longitudinal work must consider false completion, reopening, correction, revocation, supersession, or conflict.

30. **Single-axis evaluation used to close gap-4.** A paper that only evaluates omission, only redundancy, or only false alerts cannot establish the requested joint behavior.

31. **Single-thread systems used to close gap-6.** Direct evidence must organize information across multiple workplace conversations, threads, or sources around a persistent work item.

32. **Transfer-domain results presented as production-email accuracy.** News, dialogue, social-media, recommendation, synthetic, and generic decision-support findings may justify mechanisms and experiments but not direct workplace performance claims.

## Date policy

**Earliest year discovery must include: 1988.**

The summarization side of this problem becomes clearly established in the early 2000s: *Temporal summaries of new topics* appeared in 2001, TREC introduced its Novelty Track in 2002, and DUC/TAC later formalized update summarization.

The direct workplace lineage is older, however. Wendy Mackay's 1988 work on professional email use already describes users prioritizing incoming messages and using email for information, time, task, and delegation management. Later foundational work in the 1990s covers email overload, adaptive user models, email priority, and attention-sensitive alerting.

A search beginning in 2000 or 2010 would therefore silently discard part of the conceptual foundation needed for gaps 2, 3, 5, and 6.

The default discovery floor for this round should be:

```text
1988-present
```

Backward citation chasing may admit pre-1988 work if a directly relevant predecessor is discovered. The year is a search floor, not an exclusion rule for older canonical material.
