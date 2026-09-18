# cycle-based cross-thread workplace briefing with explicit work-item state transitions: evidence for longitudinal new/open/resolved/superseded tracking, adaptive personalization, obligation-versus-preference prioritization, and joint omission/repetition evaluation academic terminology analysis

## Product problem

The target is not ordinary summarization and not a text diff. The required object is a **stateful briefing over stable work-item identities**. At reporting cycle \(t\), selection must combine:

- genuinely new or changed decision-relevant information;
- unchanged information that remains open, mandatory, risky, or otherwise still requires attention;
- enough prior context to understand a change;
- suppression of content whose resolved or superseded state makes repetition misleading;
- explicit rules and obligations that act as stronger constraints than inferred personal preference;
- softer personalized priority, reminder value, urgency, recency, and forgetting-risk signals;
- visible uncertainty, staleness, dispute, or incomplete investigation;
- evaluation of missed essential work, redundant repetition, false alerts, and failure to preserve unresolved state.

No single established academic task name covers that full contract. Round 3 should therefore search an exact DIRECT family first and then several clearly labeled component and TRANSFER families. A transfer paper can justify a mechanism or benchmark design; it cannot establish end-to-end workplace briefing performance.

The most important terminology correction is that **sequential update summarization** is a better-established search anchor than the generic phrase *incremental summarization*. NIST's update task explicitly assumes that a reader has already seen an earlier document set and asks the later summary to convey new information. citeturn246077search0turn246077search4 However, that task still does not express msgloom's rule that unchanged but unresolved critical work must remain visible.

Likewise, for gap 2, **email criticality**, **expected cost of delayed review**, **ranking under constraints**, **hard constraints versus soft preferences**, and **lexicographic optimization** are safer search anchors than *response priority prediction*. Early email-alerting research explicitly modeled criticality and delayed-review cost, whereas reply/action probability is an observational behavior signal rather than an obligation label. citeturn947358search1turn222664search120

For gap 3, prefer **adaptive user modeling**, **preference drift**, **user-interest drift**, **concept drift**, and **online personalization** over the less standardized phrase *longitudinal personalization*. Concept-drift research explicitly studies changing relations over time, and adaptive-user-modeling work distinguishes long- and short-term preferences. citeturn176004search13turn176004search3

For gap 5, the missing vocabulary is substantially outside summarization: **prospective memory**, **prospective remembering**, **reminder effectiveness**, and **cognitive offloading** directly study future intentions and forgetting. This literature dates back at least to Meacham and Singer's 1977 naturalistic prospective-remembering work. citeturn760539search0

## Seed keyword audit

| Seed | Academic meaning | Fit | Main risk |
| --- | --- | --- | --- |
| update summarization | Later summary assumes earlier information was already read and emphasizes updates | STRONG | Canonical tasks optimize novelty and can suppress unchanged open work |
| incremental summarization | Summary updated as new input arrives | MODERATE | Often means computational/streaming incrementality rather than semantic lifecycle tracking |
| temporal summarization | Timely, novel, important updates from an evolving time-ordered stream | STRONG | Mostly news/disaster events without obligations |
| timeline summarization | Key dates plus descriptions of important developments | MODERATE | Key-event timelines do not guarantee cycle-by-cycle carry-forward |
| query-focused summarization | Summary tailored to a stated information need | MODERATE | Query relevance is not stable work-item identity |
| query-focused multi-document summarization | Multi-source summary optimized for an information need | STRONG | Usually one-shot over a fixed document set |
| multi-document summarization | One summary from multiple documents | MODERATE | Too broad; no temporal or personal semantics implied |
| entity-centric summarization | Summary or profile organized around a named entity | WEAK | A work item is not an entity; entity identity can over-merge |
| event-centric summarization | Summary organized around an event and developments | MODERATE | Event literature rarely models requests, obligations, completion, or revocation |
| topic-focused summarization | Summary focused on a topic/information need | MODERATE | Academic topic usually means theme/query rather than concrete work matter |
| novelty detection | Detect relevant information not previously observed | MODERATE | Novel information is not equivalent to important information |
| redundancy reduction in summarization | Suppress overlapping selected content | MODERATE | An intentional unresolved reminder may look redundant |
| delta summarization | Informal label for summarizing differences/changes | REJECT | Not a stable task name; attracts diffs, software and version-control literature |
| information update detection | Detect new/update-worthy information | WEAK | Often KB/entity update detection rather than briefing generation |
| personalized summarization | Select/generate summaries using a user model | STRONG | Usually optimizes interest, not mandatory coverage |
| user-adaptive summarization | Adapt summary to user/context/feedback | MODERATE | Adaptation may concern style or readability rather than content priority |
| personalized ranking | User-specific ordering of candidates | STRONG | Preference ranking provides no mandatory-item guarantee |
| learning to rank | Learned ordering from relevance/preference supervision | WEAK | Vast generic IR/recommendation literature |
| preference-aware ranking | Ranking influenced by user preferences | MODERATE | Usually soft preference only |
| email prioritization | Rank email by importance, urgency, criticality, or expected action | STRONG | Importance/action probability can be confused with obligation |
| email triage | Decide what mail to read, act on, defer, organize, or prioritize | STRONG | Includes spam, foldering and generic inbox management |
| response priority prediction | Ambiguous reply/action urgency or probability task | WEAK | Strong false-friend risk: response probability ≠ response obligation |
| salience estimation | Score text/events/entities for importance or centrality | WEAK | Usually generic rather than user- and obligation-specific |
| content selection | Choose source information for summary/NLG output | MODERATE | Extremely broad unless combined with constraints/state/update terms |
| coverage-aware summarization | Optimize semantic/aspect/concept coverage | MODERATE | Coverage units may not correspond to mandatory work items |
| constrained summarization | Summarization subject to explicit output/content constraints | STRONG | Most constraints concern length/style/entities, not Triage precedence |
| long-running conversation summarization | Summarize long-duration or long-context dialogue | MODERATE | Usually a single conversation rather than cross-thread work-item history |
| incremental dialogue summarization | Update a dialogue summary as turns arrive | MODERATE | Rolling snapshots may overwrite state and lack work-item lifecycle |
| notification prioritization | Select/timing alerts using urgency, value and interruption cost | STRONG | Notification utility is not equivalent to periodic briefing completeness |
| digest generation | Compact digest from many items | WEAK | Non-standard task term with large product/newsletter false-positive space |

Three historical anchors make several of these distinctions concrete. MMR explicitly combined relevance with information novelty and redundancy reduction in summarization. citeturn222664search10 TREC 2002 formalized novelty retrieval over ordered relevant documents. citeturn246077search5turn246077search6 Allan, Gupta, and Khandelwal's 2001 temporal summarization work explicitly treated news stories as arriving one at a time and tried to monitor changes over time. citeturn422137search0 These are highly relevant transfer ancestors, but none requires unresolved workplace obligations to persist.

## Academic task families

### T01 — Longitudinal work-item briefing across workplace threads and sources — DIRECT

This is the exact target family and should be searched even if the result set is sparse. Search for work-item/task-state briefing or digesting across multiple email threads or workplace sources, with explicit outstanding, resolved, superseded, or persistent state.

A paper closes gaps 1 or 6 only if it actually evaluates repeated cycles over stable work-item identities. Merely summarizing several emails is insufficient.

### T02 — Sequential update summarization — TRANSFER

Preferred terms:

- sequential update summarization;
- update summarization;
- sequential summarization;
- prior-document / prior-summary aware summarization.

Canonical update summarization gives the strongest precedent for distinguishing new information from material already communicated. TAC's formulation assumes prior reading, while later temporal work treats relevance, novelty and importance in a sequential stream. citeturn246077search0turn930782search3

Known seeds:

- Allan, Gupta, and Khandelwal, *Temporal Summaries of News Topics* (2001);
- Dang and Owczarzak, *Overview of the TAC 2008 Update Summarization Task*;
- Gao, Li, and Zhang, *Sequential Summarization: A New Application for Timely Updated Twitter Trending Topics* (2013). citeturn930782search6

### T03 — Temporal, timeline, and evolutionary summarization — TRANSFER

Preferred terms:

- temporal summarization;
- evolutionary timeline summarization;
- trans-temporal summarization;
- cross-date diversity;
- sequential update summarization.

Evolutionary timeline work explicitly models summaries across dates and balances coverage/coherence against cross-date diversity. citeturn887220search2 TREC Temporal Summarization later formalized sequential updates, comprehensiveness, latency, relevance and novelty. citeturn930782search3

Known seeds:

- Yan et al., *Evolutionary Timeline Summarization: A Balanced Optimization Framework via Iterative Substitution* (2011);
- Yan et al., *Timeline Generation through Evolutionary Trans-Temporal Summarization* (2011);
- Aslam et al., *TREC 2013 Temporal Summarization* (2013).

This family is central to gaps 1 and 4 but remains transfer evidence because the underlying objects are events rather than workplace obligations.

### T04 — Query-focused and task-focused multi-document summarization — TRANSFER

Preferred terms:

- query-focused multi-document summarization;
- task-focused summarization;
- topic-focused multi-document summarization;
- query-based meeting summarization.

This family supplies content-selection, relevance, coverage and cross-document redundancy mechanisms. *Beyond SumBasic* explicitly defines task-focused multi-document summarization around an information request. citeturn946501search0

Its key limitation is static evaluation: a fixed cluster and one output do not establish longitudinal briefing behavior.

### T05 — Workplace email task management and triage — DIRECT

Preferred terms:

- email task management;
- task-centric email;
- outstanding tasks;
- email triage;
- action-item management in email.

Whittaker and Sidner documented email being used for task management and inboxes containing outstanding tasks as early as 1996. citeturn222664search1 Bellotti and colleagues subsequently designed and evaluated Taskmaster as a task-management-centered email system. citeturn947358search4

This literature is direct evidence that workplace email contains persistent work state, but admission still requires care: task-management evidence is not automatically evidence for cycle-based summarization.

### T06 — Personalized email importance and priority ranking — DIRECT

Preferred terms:

- email prioritization;
- email importance prediction;
- personalized email ranking;
- per-user importance model;
- personalized email triage.

The Gmail Priority Inbox paper is particularly useful terminologically because it explicitly describes per-user models updated frequently from user behavior. citeturn222664search120 It is also a textbook false friend for the product distinction: the target described there is likelihood that the user will act on mail, not a normative label that the user is obliged to act.

Gap 2 searches should therefore combine this family with T05 and T07 rather than assuming one importance score can represent every signal.

### T07 — Constraint-aware and multi-objective content selection — TRANSFER

Preferred terms:

- ranking under constraints;
- hard constraints and soft preferences;
- lexicographic optimization;
- constrained ranking;
- multi-objective ranking;
- constrained summarization.

This family is the most promising terminology correction for gap 2. The needed abstraction is not merely "more weight for important rules"; it is **feasibility/mandatory constraints first, soft utility second**.

Constraint-satisfaction research explicitly distinguishes hard feasibility constraints from lexicographically represented preferences, while summarization work has combined objective terms with hard and soft constraints. citeturn392816search6turn392816search4

Papers where the only hard constraint is summary length do not close gap 2.

### T08 — Longitudinal user modeling, online adaptation, and preference drift — TRANSFER

Preferred terms:

- adaptive user modeling;
- long-term and short-term preferences;
- preference drift;
- user-interest drift;
- concept drift;
- online personalization;
- online learning for personalized ranking.

Díaz and Gervás already used long- and short-term interests for personalized summarization in 2007. citeturn246077search10 More general adaptive-user-modeling and recommender literature explicitly models short- versus long-term preferences and concept drift. citeturn176004search3turn176004search13

This is the main search family for gap 3. To close the gap rather than merely suggest a technique, an admitted paper needs longitudinal evaluation showing adaptation as the user's target preferences or context actually change.

### T09 — Prospective memory, reminder effectiveness, and intention offloading — TRANSFER

Preferred terms:

- prospective memory;
- prospective remembering;
- reminder effectiveness;
- intention maintenance;
- external memory aids;
- cognitive offloading;
- task importance and prospective memory.

Meacham and Singer's 1977 study already tied prospective remembering to incentive/task importance and external cue strategies. citeturn760539search0 Later experiments show that reminders are not uniformly beneficial: effectiveness depends on what the reminder cues. citeturn848226search12

This family is much more likely than generic email summarization to close the "forgetting likelihood/reminder value" part of gap 5. It remains transfer evidence until combined with workplace briefing selection.

### T10 — Attention-sensitive alerting and delayed-review utility — DIRECT

Preferred terms:

- attention-sensitive alerting;
- email criticality;
- expected cost of delayed review;
- notification prioritization;
- value of information;
- interruption cost.

Horvitz, Jacobs, and Hovel introduced utility-directed email alerting that balanced the cost of deferring information against interruption cost and discussed inferred email criticality. citeturn947358search1

This terminology is superior to *response priority prediction* for the urgency/value portion of gaps 2 and 5 because it does not require interpreting a predicted reply as an obligation.

### T11 — Novelty, redundancy, coverage, and repeated-update evaluation — TRANSFER

Preferred terms:

- novelty detection;
- redundancy reduction;
- comprehensiveness;
- update evaluation;
- latency/comprehensiveness;
- coverage-diversity trade-off.

TREC Temporal Summarization is particularly useful because it evaluates sequential updates and explicitly includes comprehensiveness/latency dimensions rather than only conventional static-summary similarity. citeturn930782search3

Gap 4, however, requires more. A relevant paper should ideally count at least:

1. omitted essential information;
2. redundant repeated information;
3. false/low-value alerts;
4. failure to preserve unresolved mandatory state.

A novelty score plus ROUGE does not satisfy that contract.

### T12 — Long conversation and meeting summarization with decisions and tasks — DIRECT

Preferred terms:

- long dialogue summarization;
- meeting summarization;
- query-based meeting summarization;
- decision summarization;
- action-item summarization;
- incremental dialogue summarization.

QMSum is an important direct bridge because it motivates meeting summaries as a means of recovering decisions and tasks and frames retrieval/summarization around user queries. citeturn910752search1 Long-dialogue work also studies retrieval-before-summarization when salient information is sparsely distributed. citeturn910752search2

For gap 6, nevertheless, meeting-level evidence remains insufficient unless multiple conversations/sources are joined through one persistent work item.

### T13 — Uncertainty, staleness, conflict, and incomplete-information presentation — TRANSFER

Preferred terms:

- uncertainty visualization;
- uncertainty communication;
- stale information;
- data currency;
- conflicting information visualization;
- incomplete-information decision support;
- provenance and uncertainty.

Gap 7 is specifically a **presentation-and-decision** question. Discovery should therefore downgrade papers that merely estimate uncertainty or detect conflict. The useful studies compare what users are shown and measure how alternative representations affect understanding or decisions.

Search should preserve separate concepts for:

- stale but once-valid information;
- epistemically uncertain information;
- directly disputed information;
- incomplete investigation or missing evidence.

Those states should not be collapsed into one generic confidence score.

### T14 — Longitudinal evaluation under non-stationarity — TRANSFER

Preferred terms:

- chronological split;
- temporal split;
- prequential evaluation;
- streaming evaluation;
- concept-drift evaluation;
- online evaluation.

Concept-drift methodology is useful for both gap 3 and engineering gap 8 because adaptive systems must be evaluated in temporal order. A concept-drift survey explicitly characterizes adaptive online-learning settings and their evaluation methodology. citeturn176004search13

For msgloom, this family supports benchmark design rather than product-domain accuracy claims.

## Query families

### T01 — DIRECT: exact longitudinal workplace briefing

- `"email briefing" longitudinal outstanding tasks resolved superseded`
- `"email digest" unresolved tasks resolved status longitudinal`
- `"cross-thread" email summarization tasks decisions`
- `"multi-thread" email summarization action items`
- `"task-centric email" summary outstanding tasks`

Admission requirement: repeated reporting or persistent task/work-item state. Static email summarization is not enough.

### T02 — TRANSFER: sequential update summarization

- `"sequential update summarization" novel important previous updates`
- `"update summarization" prior documents redundancy new information`
- `"update summarization" evolving documents previous summary`
- `"sequential summarization" evolving stream novelty importance`

Use primarily for gaps 1 and 4.

### T03 — TRANSFER: temporal and evolutionary summarization

- `"temporal summarization" evolving events novel updates`
- `"timeline summarization" coverage redundancy evolution`
- `"evolutionary timeline summarization" cross-date diversity`
- `"trans-temporal summarization" timeline generation`

Use for change tracking, temporal ordering and cross-cycle redundancy mechanisms.

### T04 — TRANSFER: focused multi-source content selection

- `"query-focused multi-document summarization" coverage redundancy`
- `"task-focused summarization" multi-document information need`
- `"multi-document summarization" dynamic documents content selection`
- `"query-based meeting summarization" decisions tasks`

Use for cross-source selection; do not infer cross-thread identity from document clustering.

### T05 — DIRECT: workplace outstanding tasks and triage

- `"email task management" outstanding tasks reminders`
- `"task-centric email" outstanding work`
- `"email triage" task management priority`
- `"email" action item prioritization outstanding tasks`
- `"email" requests commitments task management`

Use for gaps 1, 2, 5, and 6.

### T06 — DIRECT: personalized email priority

- `"email prioritization" personalized importance online learning`
- `"email importance" per-user model`
- `"Priority Inbox" personalized ranking`
- `"personalized email ranking" user feedback`
- `"email triage" personalized importance feedback`

Record the supervised target of every admitted paper. `reply`, `open`, `click`, `act`, `importance`, `urgency`, and `obligation` must never be treated as interchangeable labels.

### T07 — TRANSFER: hard requirements versus soft utility

- `"ranking under constraints" personalized ranking utility`
- `"hard constraints" "soft preferences" ranking`
- `"constrained summarization" user requirements content selection`
- `"lexicographic" hard constraints preferences ranking`
- `"multi-objective ranking" personalized utility constraints`

This is the principal gap-2 transfer family.

### T08 — TRANSFER: preference drift and longitudinal personalization

- `"adaptive user modeling" long-term short-term preferences`
- `"preference drift" personalized ranking longitudinal`
- `"concept drift" recommender systems user preferences`
- `"online learning" personalized ranking feedback drift`
- `"longitudinal personalization" changing user interests`

Prefer studies with chronological or streaming evaluation and actual preference change.

### T09 — TRANSFER: reminder value and forgetting

- `"prospective memory" reminders task importance`
- `"prospective remembering" incentive importance reminders`
- `"prospective memory" task importance delay reminder`
- `"cognitive offloading" reminders intentions`
- `"reminder effectiveness" forgetting future intentions`

Use for gap 5. A useful result must say something about whether/when reminding improves completion or memory, not just when to display a notification.

### T10 — DIRECT: criticality and delayed-review cost

- `"attention-sensitive alerting" email criticality`
- `"expected cost of delayed review" email`
- `"email criticality" prioritization notification`
- `"notification prioritization" value interruption email`
- `"attention-sensitive" alerting urgency delay`

Use as the urgency/awareness-value counterpart to prospective-memory research.

### T11 — TRANSFER: omission/repetition/coverage evaluation

- `"update summarization" evaluation novelty redundancy coverage`
- `"temporal summarization" comprehensiveness latency novelty`
- `"summarization evaluation" omission redundancy coverage`
- `"sequential summarization" repetition omission`
- `"novelty detection" redundancy summarization evaluation`

For gap 4, flag whether each candidate independently measures omissions, repetitions, false positives, and persistence of unresolved items. Do not infer those properties from a single aggregate score.

### T12 — DIRECT: workplace-like long conversation summarization

- `"long dialogue summarization" decisions tasks`
- `"meeting summarization" action items decisions`
- `"incremental dialogue summarization" rolling summary`
- `"conversation summarization" unresolved tasks`
- `"query-based meeting summarization" action items`

Admit meeting/email studies as direct for their local content-selection problem but label single-conversation results insufficient for gap 6.

### T13 — TRANSFER: presentation of stale, disputed, uncertain, or incomplete information

- `"uncertainty visualization" decision support incomplete information`
- `"uncertainty communication" decision making disputed information`
- `"data staleness" decision support visualization`
- `"conflicting information" visualization decision support`
- `"provenance" uncertainty conflicting evidence decision support`

For gap 7, require an actual user-facing presentation or decision-support evaluation when claiming closure.

### T14 — TRANSFER: longitudinal benchmark methodology

- `"prequential evaluation" concept drift personalization`
- `"chronological split" recommender systems evaluation`
- `"temporal split" personalized ranking evaluation leakage`
- `"sequential evaluation" update summarization longitudinal`
- `"online evaluation" concept drift adaptive user model`

Use this family to design gap-8 benchmark methodology, particularly chronological holdouts and evaluation under changing user preferences.

## Promoted terminology

Discovery should preferentially use the following terms instead of relying on the original broad seeds:

- **sequential update summarization** rather than generic *incremental summarization*;
- **evolutionary timeline summarization** and **trans-temporal summarization** for cross-time diversity;
- **task-focused multi-document summarization** for explicit information-need-driven source selection;
- **task-centric email**, **email task management**, and **outstanding tasks** for persistent workplace work;
- **email criticality** and **expected cost of delayed review** for urgency/value of timely awareness;
- **adaptive user modeling**, **preference drift**, **user-interest drift**, and **concept drift** for changing personalization;
- **prospective memory**, **prospective remembering**, and **reminder effectiveness** for forgetting/reminder value;
- **ranking under constraints**, **hard constraints and soft preferences**, and **lexicographic optimization** for obligation-before-preference selection;
- **comprehensiveness**, **cross-date diversity**, and **sequential update evaluation** for repeated-cycle evaluation;
- **chronological split**, **temporal split**, and **prequential evaluation** for longitudinal benchmarking.

## False friends and downgrade rules

1. **Static one-shot summaries:** downgrade any work with no earlier accepted view, earlier summary, previous document set, or repeated cycle when considering gaps 1, 3, 4, or 6.
2. **Novelty-only systems:** useful for suppressing repetition, but they cannot justify dropping unchanged unresolved work.
3. **Thread = Topic assumptions:** single email thread, meeting, lexical cluster, or query is not evidence of stable cross-thread work-item identity.
4. **Response probability = obligation:** reject this substitution. Open/click/reply/action probability is an observed behavior target, not evidence that the user is required to respond.
5. **Generic importance = mandatory priority:** email-importance prediction is incomplete unless the supervised target is defined and distinguished from explicit user rules or obligations.
6. **Soft personalization overriding rules:** recommendation or ranking papers that optimize one weighted utility without mandatory constraints do not establish the project's precedence rule.
7. **Style personalization:** changing length, vocabulary, readability, or tone is not evidence for personalized briefing selection.
8. **Generic recommender literature:** retain only as TRANSFER when it contributes a concrete mechanism such as preference drift, online adaptation, constrained ranking, or temporal evaluation.
9. **Timeline without lifecycle:** key dates and event evolution are insufficient if open/resolved/revoked/superseded state is not represented.
10. **Single-conversation summarization:** meeting, dialogue, or email-thread summarization does not close gap 6 unless evidence is joined across multiple conversations/sources.
11. **Topic 06 leakage:** papers determining factual state, supersession, or temporal validity but not briefing selection should be treated as upstream state-estimation evidence, not Topic 09 closure.
12. **Length/style constraints:** constrained summarization is relevant to gap 2 only when constraints correspond to required content, feasibility, or priority—not merely length, lexical choice, entities, or abstractiveness.
13. **Drift detection without adaptation:** detecting concept/preference drift does not close gap 3 unless the system changes its user model and the change is evaluated over time.
14. **Reminder timing only:** a study about when to interrupt does not establish what should be included in a periodic briefing.
15. **Interruption optimization only:** notification engagement or interruption-cost optimization is not evidence of report completeness.
16. **Uncertainty estimation without presentation:** calibration/confidence work does not close gap 7 unless alternative user-facing representations or their decision effects are evaluated.
17. **ROUGE-only evaluation:** summary similarity, fluency, or generic preference cannot establish decision-essential coverage.
18. **Coverage without error decomposition:** an aggregate content score does not jointly measure omission, redundant repetition, and false alerts.
19. **Random split for adaptive models:** downgrade as evidence of longitudinal adaptation when future interactions can influence training. Use chronological, streaming, or prequential evaluation instead.
20. **Transfer-domain overclaiming:** methods from news, recommendation, prospective-memory experiments, or synthetic streams may justify mechanisms and benchmarks but not production workplace accuracy.
21. **Product-oriented 'digest' material:** do not admit newsletters, product documentation, or industry descriptions without a scholarly evaluated task.

## Date policy

**Earliest publication year discovery must include: 1977.**

The unusually early floor is deliberate and family-specific. Gap 5 asks whether reminder usefulness and likelihood of forgetting should influence briefing selection. Prospective-memory research directly studies remembering future intentions, and Meacham and Singer's *Incentive Effects in Prospective Remembering* was published in 1977. citeturn760539search0 A modern-only search would therefore silently remove foundational evidence for one of the explicit open gaps.

The other relevant branches also predate modern neural NLP by a substantial margin:

- workplace email overload/task management is documented by 1996; citeturn222664search6
- relevance-versus-novelty/diversity summarization is established by 1998; citeturn222664search10
- attention-sensitive email criticality and delayed-review reasoning appears by 1999; citeturn947358search1
- online temporal summarization of evolving news appears by 2001; citeturn422137search0
- TREC formalized novelty detection in 2002; citeturn246077search6
- task-focused multi-document summarization and personalized summarization are established by 2007; citeturn946501search0turn246077search10
- DUC piloted update summarization in 2007 and TAC ran the task at scale in 2008. citeturn246077search0turn246077search7

Discovery should therefore use **1977 as the hard global floor**, but keep the searches family-scoped: the 1970s-1990s range is mainly necessary for prospective memory, email/task management, diversity, and alerting; broad generic summarization searches should not be indiscriminately expanded back to 1977.

The practical conclusion for gap-closure round 3 is to search **exact longitudinal workplace capability first**, then use the promoted academic families to find narrowly relevant mechanisms. More papers about generic summarization, recommendation, or novelty should not be admitted merely because they share vocabulary with the product.
