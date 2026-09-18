# longitudinal and cross-thread workplace briefing systems that track new, open, resolved, and superseded work-item state over repeated cycles, with adaptive user-specific prioritization, reminder value, uncertainty presentation, and omission/repetition evaluation academic terminology analysis

## Product problem

The target is not ordinary email summarization and not merely a shorter inbox. The academic decomposition has to preserve five separate decisions:

1. **Longitudinal content state:** distinguish a genuinely new development from information the user has already seen, while deliberately carrying forward unchanged but unresolved important work and suppressing information that has become resolved or superseded.
2. **Cross-source synthesis:** summarize a stable work matter across messages, threads, conversations, and eventually multiple sources rather than treating each message or thread as an independent summary unit.
3. **Priority architecture:** enforce explicit user/Triage rules first, then use softer personalized importance, urgency, reminder value, recency, and learned preference signals without confusing predicted behavior with obligation.
4. **User adaptation:** update personalization as work roles, projects, relationships, priorities, and feedback change rather than relying on a static user profile.
5. **Loss-sensitive reporting:** measure decision-important omission, redundant resurfacing, false alerts, and failure to preserve important unresolved state over successive cycles, while making stale, incomplete, disputed, or otherwise uncertain state visible.

The closest established academic task for the *new information* half is **update summarization**. TAC 2008 explicitly assumed that a user had read an earlier document set and asked the later summary to convey what was new; the task was piloted in DUC 2007. That is a strong analogue for novelty suppression, but it does not impose msgloom's requirement that unchanged unresolved work remain visible. citeturn467345search1turn467345search7

Likewise, TREC's **Temporal Summarization** formalized sequential monitoring of developing events, including novelty, reliability, latency, and comprehensiveness, but in a breaking-news setting rather than long-lived workplace obligations. citeturn586321search2turn586321search8 Query-focused multi-document summarization is also relevant because it synthesizes many documents in response to a user information need, but the classic DUC task is a fixed one-shot corpus rather than a repeated briefing cycle. citeturn159814search0turn159814search4

The direct workplace roots are older than modern LLM literature. Whittaker and Sidner's 1996 study already described email as task management and task tracking, including outstanding work that users can lose sight of. citeturn344631search1turn344631search2 Taskmaster later explicitly recast email around task management, and contemporary studies continue through email triage and AI-powered workplace reminders such as Microsoft's Viva Daily Briefing Email. citeturn344631search5turn344631search10turn610517search1

## Seed keyword audit

| Seed | Academic meaning | Fit | Main risk |
| --- | --- | --- | --- |
| update summarization | Later summary assumes earlier information was already consumed and emphasizes newly added information. | STRONG | Canonical task is novelty-oriented and may suppress unchanged-but-open work. |
| incremental summarization | Summary/representation is updated as additional observations arrive. | STRONG | Highly overloaded; incremental processing does not imply correct lifecycle carry-forward. |
| temporal summarization | Time-aware or sequential summarization; TREC used it for evolving event streams. | MODERATE | Dominated by breaking news and low-latency novelty. |
| timeline summarization | Select important dates/events and describe them in chronological order. | MODERATE | Usually a retrospective timeline, not successive user-specific briefings. |
| query-focused summarization | Summary tailored to an explicit information need. | MODERATE | Normally one-shot and not stateful. |
| query-focused multi-document summarization | Synthesize multiple documents against a user need. | STRONG | Strong cross-document analogue but usually static. |
| multi-document summarization | Produce one summary from multiple related documents. | MODERATE | Too broad to imply Topic identity, personalization, or repeated cycles. |
| entity-centric summarization | Summarize information/events associated with one entity. | WEAK | Entity identity is not work-item identity. |
| event-centric summarization | Organize summary content around events/event structures. | MODERATE | A work item spans more than discrete events. |
| topic-focused summarization | Focus summary on a target topic/theme; overlaps query/topic-oriented summarization. | MODERATE | Academic 'topic' often means lexical theme, not a stable work matter. |
| novelty detection | Detect information not previously observed. | STRONG | Novel ≠ important; unchanged critical state would be lost. |
| redundancy reduction in summarization | Penalize repeated information while retaining relevant/salient content. | STRONG | Repeated unresolved work can be intentionally necessary. |
| delta summarization | Mostly a non-canonical phrase for version-difference or new-content summaries. | REJECT | Pulls search toward literal diff/redline products instead of semantic state. |
| information update detection | Diffuse phrase covering novelty/change/event-update detection. | WEAK | Poor retrieval precision and no stable task definition. |
| personalized summarization | Preserve content relevant to a user profile/interests/feedback. | STRONG | Interest-based personalization may omit mandatory work. |
| user-adaptive summarization | Adapt summary to user characteristics or interactions. | MODERATE | Often short-term/interface adaptation, not preference drift. |
| personalized ranking | User-specific ordering or scoring of items. | STRONG | Mostly recommendation/search; learned preference does not guarantee obligation coverage. |
| learning to rank | Learn an ordering from labels, clicks, preferences, or pairwise/listwise objectives. | MODERATE | Does not inherently enforce hard user rules or mandatory recall. |
| preference-aware ranking | Ranking incorporating explicit or inferred user preferences. | MODERATE | Diffuse phrase heavily associated with recommendation. |
| email prioritization | Rank email by importance, urgency, criticality, expected action, or delayed-review cost. | STRONG | Behavioral action/reply probability is not response obligation. |
| email triage | Decide what to do with unhandled mail: respond, defer, file, delete, task, etc. | STRONG | Often descriptive HCI rather than briefing-selection evaluation. |
| response priority prediction | Estimate urgency/priority/likelihood associated with responding. | WEAK | Especially prone to conflating response likelihood with obligation. |
| salience estimation | Estimate which facts/sentences/events are important for inclusion. | MODERATE | Generic salience lacks mandatory user-specific coverage semantics. |
| content selection | Decide which source information belongs in the summary. | STRONG | Broad term requires longitudinal/constraint/coverage modifiers. |
| coverage-aware summarization | Explicitly reward coverage of concepts/topics/entities/source units. | MODERATE | Proxy coverage can still miss a decisive deadline, condition, or action. |
| constrained summarization | Summarize under explicit length/content/lexical/style/structural constraints. | MODERATE | Most constraints are generation constraints, not Triage-rule precedence. |
| long-running conversation summarization | Summarize lengthy conversations or maintain rolling summaries. | MODERATE | Phrase is not sharply canonical and attracts context-compression engineering. |
| incremental dialogue summarization | Update dialogue summaries while turns arrive. | STRONG | Normally one conversation rather than cross-thread work-item state. |
| notification prioritization | Rank/filter/delay alerts using urgency, value, context, attention, or interruption cost. | MODERATE | Optimizes whether/when to interrupt, not necessarily briefing content. |
| digest generation | Produce a compact digest of multiple items. | WEAK | Product term with low academic precision. |

A few terminology corrections are especially important.

**Update summarization** should remain a promoted term. TAC's task definition is almost exactly the previous-view/new-information subproblem: documents arrive in chronological sets, and the later summary is written assuming the earlier set has already been read. citeturn467345search1

**Timeline summarization** should be retained only as transfer terminology. Modern TLS is typically defined as identifying important dates and describing events on those dates, not deciding which unresolved state should survive into a user's next briefing. citeturn715339search0turn715339search4

**Personalized summarization** is a genuine academic task. Díaz and Gervás explicitly modeled long- and short-term user interests and evaluated summaries tailored to user profiles, but the application was personalized information/news rather than mandatory workplace coverage. citeturn467345search4

**Delta summarization** should be removed from academic discovery as a primary term. It currently attracts document-version comparison and engineering/product material rather than a stable research task corresponding to semantic briefing state.

## Academic task families

### TF1 — Update and sequential-update summarization — TRANSFER

This is the strongest analogue for **what changed since the previous accepted view**. Search should explicitly combine update summarization with persistent importance, open items, and omission evaluation rather than merely repeating the canonical novelty task.

Known anchors:
- *Overview of the TAC 2008 Update Summarization Task*
- *The Use of MMR, Diversity-Based Reranking for Reordering Documents and Producing Summaries*

MMR is particularly relevant because it explicitly combines query relevance with information novelty/redundancy rather than treating diversity as an isolated objective. citeturn586321search0

### TF2 — Temporal, streaming, and timeline summarization — TRANSFER

This family studies information arriving over time and offers sequential evaluation concepts. TREC Temporal Summarization is unusually useful because it treated the output as **sentence-length updates from a temporally ordered stream** and evaluated comprehensiveness and latency rather than only a static final summary. citeturn586321search2

Known anchors:
- *TREC 2013 Temporal Summarization*
- *Examining the State-of-the-Art in News Timeline Summarization*
- *From Moments to Milestones: Incremental Timeline Summarization Leveraging Large Language Models*

### TF3 — Query-focused multi-document and cross-document synthesis — TRANSFER

This is the mature literature for synthesizing information scattered across documents. The gap-closing search should add **cross-thread**, **multi-thread email**, **multi-conversation**, **task-centric**, and **cross-document timeline** modifiers. Ordinary static MDS should not be admitted as closing gap-6.

Known anchor:
- *DUC 2005: Evaluation of Question-Focused Summarization Systems*

DUC 2005 explicitly required synthesizing a fluent answer from 25-50 documents to a complex information need. citeturn159814search0

### TF4 — Longitudinal state-preserving summarization — TRANSFER

This term should be promoted strongly for round 2. Longitudinal clinical records have a structural resemblance to msgloom that generic news summarization lacks: many encounters, repeated/copied text, evolving state, persistent problems, temporal dependencies, and potentially severe omission cost.

A particularly relevant recent transfer result is CLIN-SUMM, which incrementally constructs a date-partitioned patient representation and explicitly focuses subsequent summaries on newly documented information while retaining temporal history. It remains a clinical preprint and does **not** establish workplace performance, but its task formulation is much closer to gap-1 than static news summarization. citeturn282387search1turn282387search4

Known anchors:
- *CLIN-SUMM: Incremental Longitudinal Summarization of Clinical Notes Enables Scalable Representation and Early Disease Prediction*
- *Large Language Models with Temporal Reasoning for Longitudinal Clinical Summarization and Prediction* citeturn282387search9

### TF5 — Workplace email triage, task management, and collaborative reminders — DIRECT

This is direct target-domain evidence and should be weighted above generic recommender work when claims concern actual knowledge-worker behavior.

Known anchors:
- *Email Overload: Exploring Personal Information Management of Email*
- *Taking Email to Task: The Design and Evaluation of a Task Management Centered Email Tool*
- *RemindMe: Plugging a Reminder Manager into Email for Enhancing Workplace Responsiveness*
- *Email Triage: Challenges and Opportunities*
- *AI-Powered Reminders for Collaborative Tasks: Experiences and Futures*

The modern reminder study explicitly examined Microsoft Viva Daily Briefing Email with knowledge workers, making **collaborative task reminders**, **asynchronous collaboration**, and **daily briefing email** important promoted terms. citeturn610517search1

### TF6 — Personalized email importance and criticality ranking — DIRECT

The useful direct terms are **email importance**, **email criticality**, **expected cost of delayed review**, and **personalized email ranking**.

Known anchors:
- *Attention-Sensitive Alerting*
- *The Learning Behind Gmail Priority Inbox*

The Priority Inbox work is particularly important for gap-3 terminology because it describes per-user models updated frequently and explicitly discusses non-stationary noisy training data. It still learns importance from user actions, so it cannot be treated as an obligation model. citeturn344631search90

The earlier Priorities work framed email urgency through expected cost of delayed review and combined content with user attention/context, giving a more decision-theoretic vocabulary than generic 'importance'. citeturn919588search0

### TF7 — Longitudinal personalization, user modeling, and preference drift — TRANSFER

Gap-3 should no longer be searched mainly with `"longitudinal personalization"`, which is too narrow and not the dominant vocabulary. Promote:

- **preference drift**
- **concept drift**
- **dynamic user modeling**
- **online personalization**
- **continual personalization**
- **short-term and long-term interests**

Known anchors:
- *User-model based personalized summarization*
- *Personalized Preference Drift Aware Sequential Recommender System* citeturn610517search18

The latter is recommendation-domain transfer evidence only; it must not be used to claim workplace-email accuracy.

### TF8 — Hard-constraint and soft-preference selection/ranking — TRANSFER

Gap-2 is structurally a **constraint-vs-preference** problem, not simply personalized ranking.

Promote:
- **hard constraints and soft preferences**
- **constructive preference elicitation**
- **constrained ranking**
- **lexicographic preferences**
- **constrained learning to rank**

The preference-elicitation literature explicitly distinguishes a feasible set delimited by hard requirements from the ranking of feasible alternatives by user preferences, which is a useful formal analogue to "Triage rules first; personalization second." citeturn644575search0

Known anchors:
- *Constructive Preference Elicitation*
- *End-to-end Learning for Fair Ranking Systems*

The latter is a transfer method because its constraints concern fairness, not workplace rules, but it demonstrates ranking architectures that guarantee specified constraints rather than merely adding them to a score. citeturn644575academia61

### TF9 — Reminder value, prospective memory, and attention-sensitive alerting — TRANSFER

Gap-5 requires a term beyond importance: **reminder value** or **expected cost of not resurfacing something**.

Promote:
- **prospective memory**
- **expected cost of delayed review**
- **attention-sensitive alerting**
- **reminder utility**
- **notification management**
- **forgetting / follow-through**

Known anchors:
- *Attention-Sensitive Alerting*
- *Effects of Intelligent Notification Management on Users and Their Tasks*
- *Reminders Through Association*

The notification-management literature can test timing and interruption cost, while prospective-memory literature makes forgetting itself an explicit failure mode. These are mechanisms, not direct briefing evidence. citeturn919588search16turn610517search13

### TF10 — Incremental dialogue and long-conversation summarization — TRANSFER

Use the more precise **incremental dialogue summarization** and **task-oriented incremental dialogue summarization** rather than relying on the loose phrase *long-running conversation summarization*.

Known anchor:
- *QART: A System for Real-Time Holistic Quality Assurance for Contact Center Dialogues*

QART explicitly described a task-oriented incremental dialogue summary that is updated as contact-center conversations progress. It is valuable transfer evidence for incremental state representation but remains single-dialogue rather than cross-thread workplace briefing. citeturn193529search0

### TF11 — Uncertainty communication and decision support — TRANSFER

Gap-7 needs a separate literature family. Promote:

- **uncertainty communication**
- **uncertainty visualization**
- **information sufficiency**
- **epistemic uncertainty**
- **incomplete information**
- **ambiguity**
- **data freshness / stale information**
- **conflicting information**

The strongest studies are those measuring user decisions, confidence, recognition of ambiguity, or subsequent information seeking—not merely whether users can visually decode an uncertainty glyph.

For example, Dong and Hayes evaluated an uncertainty decision-support system and reported effects on recognizing ambiguous choices and planning to seek clarifying information. citeturn791839search1turn791839search10 Other empirical work demonstrates that uncertainty presentation can alter decision strategies even when accuracy effects are mixed, which is exactly why msgloom should not assume that simply displaying a confidence value is harmless or sufficient. citeturn791839search0

### TF12 — Coverage, omission, redundancy, and sequential briefing evaluation — TRANSFER

This family exists to attack gap-4 and to inform engineering gap-8. Promoted evaluation vocabulary should include:

- **comprehensiveness**
- **coverage**
- **recall-oriented evaluation**
- **omission**
- **redundancy**
- **novelty**
- **false positives / false negatives**
- **sequential evaluation**
- **persistent-state recall**

TREC Temporal Summarization already provides a useful precedent for comprehensiveness under sequential updates, while recent retrieval work gives a formal vocabulary for recall-oriented ranking when users care about finding *every* relevant item. citeturn586321search2turn644575search5 Neither is the required end-to-end msgloom metric by itself.

## Query families

### TF1 — Update and sequential-update summarization — TRANSFER

Purpose: close the novelty-versus-persistent-state part of gaps 1 and 4.

- `"update summarization" previously read multi-document novelty`
- `"sequential update summarization" novelty redundancy coverage`
- `"update summarization" persistent important information`
- `"incremental summarization" unresolved state open items`
- `"update summarization" carry forward unresolved`
- `"update summarization" evaluation omission redundancy`
- `"novelty" "update summarization" important information`

### TF2 — Temporal, streaming, and timeline summarization — TRANSFER

Purpose: find sequential monitoring, value tracking, and temporal-state evaluation.

- `"temporal summarization" sequential updates`
- `"sequential update summarization" temporal stream`
- `"timeline summarization" incremental`
- `"incremental timeline summarization"`
- `"temporal summarization" value tracking state`
- `"stream summarization" novelty coverage redundancy`
- `"timeline summarization" evolving state changes`

### TF3 — Query-focused multi-document / cross-document synthesis — TRANSFER

Purpose: aggressively probe gap-6 rather than returning another set of ordinary static email-thread papers.

- `"query-focused multi-document summarization" email`
- `"cross-thread summarization" email`
- `"multi-thread email summarization"`
- `"task-centric email" summarization`
- `"multi-conversation summarization" topic`
- `"cross-document timeline" summarization topic`
- `"topic-level summarization" multiple conversations`
- `"cross-conversation" summarization workplace`

### TF4 — Longitudinal state-preserving summarization — TRANSFER

Purpose: find domains that explicitly preserve an evolving persistent state across encounters.

- `"longitudinal summarization" evolving state`
- `"incremental longitudinal summarization" new information`
- `"longitudinal clinical summarization" redundancy temporal`
- `"longitudinal summarization" unresolved resolved state`
- `"longitudinal summarization" persistent problems changes`
- `"problem-oriented" longitudinal summarization clinical`
- `"assessment and plan" longitudinal summarization`
- `"longitudinal summarization" omission completeness`

### TF5 — Workplace email triage, tasks, and collaborative reminders — DIRECT

Purpose: close gaps 2 and 5 with actual knowledge-worker evidence and probe gap-7's stale-reminder problem.

- `"email triage" workplace outstanding tasks`
- `"task-centric email" outstanding tasks reminders`
- `"email task management" unresolved tasks workplace`
- `"collaborative task reminders" email workplace`
- `"email reminder" workplace responsiveness`
- `"AI-powered reminders" collaborative tasks email`
- `"daily briefing" email reminders workplace`
- `"email triage" priority response task management`

### TF6 — Personalized email importance and criticality — DIRECT

Purpose: identify direct personalized ranking mechanisms while keeping importance separate from obligation.

- `"email prioritization" personalized importance`
- `"email importance" personalized ranking`
- `"email criticality" prioritization user model`
- `"expected cost of delayed review" email`
- `"email importance" online learning user`
- `"Priority Inbox" non-stationary user model`
- `"email prioritization" user feedback adaptive`
- `"email triage" personalized ranking`

### TF7 — Longitudinal personalization and preference drift — TRANSFER

Purpose: specifically close gap-3 rather than collecting more static user-profile papers.

- `"preference drift" personalized ranking`
- `"concept drift" personalized ranking user`
- `"dynamic user modeling" preferences longitudinal`
- `"longitudinal personalization" user preferences`
- `"continual personalization" ranking user feedback`
- `"online personalization" non-stationary preferences`
- `"user model" short-term long-term interests summarization`
- `"preference drift" summarization personalization`
- `"email prioritization" concept drift`

### TF8 — Hard rules versus soft preferences — TRANSFER

Purpose: find formalisms where mandatory constraints and learned preferences remain different signal classes.

- `"hard constraints" "soft preferences" ranking`
- `"constructive preference elicitation" hard constraints`
- `"constrained ranking" user preferences`
- `"learning to rank" hard constraints preferences`
- `"constrained learning to rank" user preferences`
- `"lexicographic preferences" ranking constraints`
- `"preference learning" hard constraints soft preferences`
- `"personalized ranking" policy constraints`

### TF9 — Reminder value and prospective memory — TRANSFER

Purpose: close gap-5 by modeling why an item is worth resurfacing, not merely whether it is important.

- `"prospective memory" reminders importance`
- `"prospective memory" reminder value task`
- `"attention-sensitive alerting" email criticality`
- `"expected cost of delayed review"`
- `"notification management" relevance interruption cost`
- `"reminder utility" forgetting task`
- `"reminder timing" forgetting urgency`
- `"collaborative task reminders" importance urgency`

### TF10 — Incremental dialogue/conversation summarization — TRANSFER

Purpose: find repeated updates that explicitly preserve open decisions/tasks inside evolving conversations.

- `"incremental dialogue summarization"`
- `"task-oriented incremental dialogue summarization"`
- `"real-time dialogue summarization" task state`
- `"long dialogue summarization" unresolved issues`
- `"conversation summarization" open tasks decisions`
- `"incremental conversation summarization" state`
- `"rolling summary" dialogue unresolved decisions academic`

### TF11 — Uncertainty communication and decision support — TRANSFER

Purpose: close gap-7 with experimental evidence about user decisions under stale, incomplete, disputed, or uncertain information.

- `"uncertainty visualization" incomplete information decision support`
- `"uncertainty communication" decision making confidence`
- `"information sufficiency" uncertainty decision support`
- `"stale information" decision support display`
- `"data freshness" uncertainty decision support`
- `"conflicting information" uncertainty visualization decision`
- `"epistemic uncertainty" visualization decision support`
- `"uncertainty visualization" information seeking ambiguity`
- `"incomplete information" visualization decision making`

### TF12 — Omission/repetition/sequential evaluation — TRANSFER

Purpose: assemble the evaluation components for gap-4 and the future cycle-based benchmark in gap-8.

- `"update summarization" evaluation coverage redundancy`
- `"temporal summarization" comprehensiveness redundancy evaluation`
- `"summary evaluation" omission redundancy coverage`
- `"longitudinal summarization" completeness redundancy evaluation`
- `"summarization" omission error important information`
- `"recall-oriented" summarization evaluation`
- `"false positives" "false negatives" email alerts`
- `"briefing" omission redundancy evaluation`
- `"sequential summarization" evaluation persistent state`

## False friends and downgrade rules

- A fixed-corpus summarizer with no previous-view or repeated-cycle condition does not close the longitudinal briefing gaps.
- An update summarizer that outputs only novel information remains **TRANSFER** unless it also preserves unchanged unresolved important state.
- A timeline that retrospectively lists important dates is not a longitudinal briefing policy.
- Multi-document input does not establish cross-thread Topic reasoning. The sources must be reconciled as one stable work matter.
- Entity identity must not be accepted as Topic identity.
- Literal version diffing, redlining, or changed-string detection is not semantic state/supersession reasoning.
- Email importance, read probability, reply probability, predicted action, and response obligation must remain separate labels.
- Static-profile personalized summarization cannot close gap-3.
- Preference-drift results from recommenders remain **TRANSFER** unless tested in workplace communication.
- Hard user rules represented merely as weighted ranking features do not demonstrate rule precedence.
- Length/style/lexical constrained summarization does not answer the hard-rule-versus-soft-preference problem.
- Reminder studies that simply improve adherence do not establish how reminder value should be traded against importance, urgency, or personalized priority.
- Notification timing/interruptibility is not briefing content selection.
- Uncertainty visualization papers about statistical error bars alone are only weak transfer evidence for stale, disputed, or incompletely investigated workplace state.
- ROUGE, BLEU, fluency, coherence, or compression alone cannot demonstrate safe omission.
- Topic/entity/n-gram coverage is not decision-essential coverage unless missing actions, deadlines, conditions, risks, and unresolved state are actually protected.
- Novelty/diversity gains without false-negative cost for important content cannot close gap-4.
- Spam/security false-positive metrics do not become briefing false-alert evidence merely because the vocabulary matches.
- Non-academic "digest generation", "delta summary", product pages, LLM memory recipes, and vendor tutorials should not enter the academic corpus.
- Transfer-domain results may justify mechanisms and experiments but must never be reported as production-email accuracy.
- A newer mention is not proof that an older state can be removed. Resolution, revocation, supersession, contradiction, and continued openness must be represented explicitly.
- Compression ratio is not a success criterion when decision-essential content can disappear.

## Date policy

**Earliest publication year discovery must include: 1996.**

A recency window beginning in 2000, 2005, 2010, or the LLM era would silently exclude foundational direct workplace work. In 1996, Whittaker and Sidner had already documented email being used for task management, task tracking, reminders, and outstanding work, which is part of the core problem this Topic is trying to solve. citeturn344631search1turn344631search2

The late 1990s also contain two other foundations that matter directly to the terminology: MMR formalized the tradeoff between relevance and novelty/redundancy in retrieval/summarization, and *Attention-Sensitive Alerting* framed email priority in terms of criticality, delayed-review cost, user context, and interruption. citeturn586321search0turn919588search0

The later lineage then adds task-centric email (2003), question-focused multi-document summarization (DUC 2005), update summarization (DUC 2007/TAC 2008), personalized email ranking, temporal summarization, workplace reminder systems, longitudinal summarization, preference drift, and uncertainty decision support. The correct discovery policy is therefore **1996-present**, with newer literature prioritized operationally but without excluding those foundational papers.
