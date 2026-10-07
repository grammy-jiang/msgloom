# Incremental, personalized and priority-aware briefings from workplace communication academic terminology analysis

## Product problem

The target is not ordinary summarization and not merely a shorter inbox. The research object is a **stateful briefing decision made repeatedly for one user over an evolving set of work Topics**.

At report cycle \(t\), the system receives accepted Topic information and must decide at least four different things:

1. **What is genuinely new or changed** relative to the user's previous accepted view.
2. **What remains important despite being unchanged**, especially unresolved requests, actions, commitments, deadlines, risks, conditions, and disputed or uncertain state.
3. **What prior information has been superseded and should no longer be repeated as current fact.**
4. **What can safely be omitted as redundant without creating a decision-relevant omission.**

It must then order the surviving information according to explicit Triage rules and user context, compress it without dropping required content, and display uncertainty when upstream state or investigation remains unresolved.

No single mature academic label appears to cover this complete capability. The closest literature is therefore a composition of several task families. The most important distinction for discovery is between literature that models **change/novelty** and literature that models **importance/coverage**. Topic 09 requires both.

A useful conceptual decomposition is:

```text
previous accepted Topic view
          +
new accepted Topic evidence
          +
current open/closed/superseded/uncertain state
          +
explicit Triage rules / user context
          ↓
change detection / novelty reasoning
          ↓
mandatory carry-forward of unresolved important state
          ↓
priority + salience + coverage-constrained content selection
          ↓
redundancy control
          ↓
personalized ordering and realization
          ↓
briefing
```

The central research gap to protect during discovery is:

> **Novel information is not the same as important information.**

A method that correctly emits only new facts but silently removes an unchanged overdue action is not adequate. Conversely, repeatedly printing the entire previous state defeats the purpose of incremental briefing.

The literature therefore needs to be searched across update summarization, incremental summarization, temporal summarization, personalized summarization, email triage, coverage-aware content selection, and conversation summarization, but admission must remain capability-based rather than keyword-based.

## Seed keyword audit

| Seed | Academic meaning | Fit | Main risk | False-positive literature |
| --- | --- | --- | --- | --- |
| update summarization | Summarizing a new information set relative to information already assumed read, emphasizing new information and suppressing repetition; DUC/TAC update tasks are canonical. | STRONG | Usually optimizes novelty, not preservation of unchanged unresolved obligations. | Software/document updates; systems evaluated only for novelty or ROUGE. |
| incremental summarization | Maintaining or generating a summary as information arrives sequentially. | STRONG | “Incremental” may describe computation rather than semantic comparison with an accepted prior view. | Incremental training, memory-efficient online algorithms, latency-only streaming work. |
| temporal summarization | Selecting salient updates from evolving temporally ordered information. | MODERATE | Dominated by public events/news rather than personalized workplace state. | Crisis streams, temporal IR, event tracking. |
| timeline summarization | Building a chronological sequence of salient events or developments. | MODERATE | Unchanged open work has no new timeline event and can disappear. | News, historical, biography and social-media timelines. |
| query-focused summarization | Selecting summary content relevant to an explicit query or information need. | MODERATE | Static query relevance does not model prior accepted state or work-item lifecycle. | QA, search snippets, single-document query summarization. |
| query-focused multi-document summarization | Multi-source summarization conditioned on an information need, with cross-document redundancy control. | STRONG | Usually a fresh static summarization instance rather than repeated stateful briefing. | Static benchmark MDS with no prior-view semantics. |
| multi-document summarization | Producing one summary from several documents while combining overlap and reducing redundancy. | MODERATE | Too broad; usually lacks time, personalization, state and obligations. | Generic news and scientific-document summarization. |
| entity-centric summarization | Organizing a summary around an entity or entity profile. | WEAK | Entity identity is not work-Topic identity. | Biography generation, entity cards, entity search. |
| event-centric summarization | Structuring summaries around events or event clusters. | MODERATE | Work state includes more than discrete events. | News-event extraction, event coreference and disaster summaries. |
| topic-focused summarization | Broad label for content selected for topical relevance. | MODERATE | “Topic” often means lexical theme rather than a concrete continuing work matter. | Topic-model summarization and topical clustering. |
| novelty detection | Detecting previously unseen information, sentences, documents or events. | MODERATE | Novelty is not importance. | Anomaly detection, outlier detection, new-event detection that discards old state. |
| redundancy reduction in summarization | Suppressing overlapping units so summary space covers more information. | MODERATE | Repeated unresolved information can be intentionally important. | Lexical deduplication and diversity-only sentence selection. |
| delta summarization | Non-standard label usually referring to summarizing changes or differences. | REJECT | Strongly attracts unrelated diff/change literature and lacks a stable summarization task definition. | Code diffs, commit summaries, database deltas, revision summaries. |
| information update detection | Broad label for recognizing changed or newly available information. | MODERATE | Not a stable task boundary. | Knowledge-base updates, concept drift, generic change detection. |
| personalized summarization | Summary generation conditioned on an individual user's profile, interests, history or preferences. | STRONG | Interest optimization can conflict with explicit Triage and required coverage. | Personalized news/recommendation based on clicks or interests. |
| user-adaptive summarization | Summarization adapting to user model, expertise, interaction history or preferences. | STRONG | Learned behavior may override explicit rules. | Educational/readability/interface adaptation. |
| personalized ranking | User-conditioned ordering of candidate items. | MODERATE | Usually predicts relevance or engagement, not responsibility or mandatory visibility. | Search, recommendation, advertising and feed ranking. |
| learning to rank | ML methods for learning an ordering according to relevance or utility. | MODERATE | Method family, not target task; objective may be incompatible with mandatory coverage. | Search, e-commerce, ads and response ranking. |
| preference-aware ranking | Ranking using stated or inferred preferences. | WEAK | Preferences or likes are not obligations. | Consumer recommendation and pairwise preference learning. |
| email prioritization | Predicting or ordering email by importance, urgency, expected action or user attention. | STRONG | Importance labels often collapse into opening/replying behavior. | Spam, sender importance, reply prediction and Priority-Inbox-style engagement models. |
| email triage | Deciding which emails require attention, action, deferment, filing or priority handling. | STRONG | May study inbox behavior without producing cross-message Topic briefings. | Folder classification, interfaces, spam and organization-only studies. |
| response priority prediction | Unstable phrase covering likelihood, urgency, speed or priority of replying. | WEAK | High risk of confusing response probability with response obligation. | Reply likelihood, latency prediction and next-response ranking. |
| salience estimation | Estimating which information units are important enough to retain. | STRONG | Generic salience is not user-rule-aware or obligation-aware. | Entity salience, visual salience and generic sentence importance. |
| content selection | Selecting information units to include in a generated output. | STRONG | Extremely broad; does not itself imply time, personalization or mandatory coverage. | Data-to-text planning and generic extraction. |
| coverage-aware summarization | Explicitly rewarding coverage of concepts, topics or information units while controlling redundancy. | STRONG | Academic “coverage” may mean latent topics rather than mandatory work content. | Topic-model and lexical-concept coverage. |
| constrained summarization | Summarization under explicit inclusion, length, concept, entity, style or other constraints. | STRONG | Many constraints are unrelated to semantic completeness. | Length, lexical, grammatical or stylistic constrained generation. |
| long-running conversation summarization | Summarizing conversations extending over many turns or sessions. | MODERATE | Long context is not automatically stable work-item state. | Long-document processing and generic conversational memory. |
| incremental dialogue summarization | Updating the summary as dialogue turns arrive. | STRONG | Turn/session identity can conceal multiple Topics and cross-thread continuity. | Latency-focused online dialogue summarization and dialogue-state tracking. |
| notification prioritization | Ranking/scheduling notifications using importance, urgency, relevance or interruption cost. | WEAK | Usually optimizes interruption or engagement rather than completeness. | Mobile push timing and interruptibility prediction. |
| digest generation | Producing compact digests from multiple items; mostly an umbrella/product phrase. | WEAK | No stable academic task and high product/search noise. | Newsletters, RSS/social digests and generic aggregation. |

### Terms to promote

The search vocabulary should promote the following because they correspond either to established task names or to useful capability-bearing combinations:

- **update summarization**
- **incremental summarization**
- **incremental update summarization**
- **novelty-aware summarization**
- **redundancy-aware summarization**
- **query-focused multi-document summarization**
- **temporal summarization**
- **timeline summarization**
- **streaming summarization**
- **personalized summarization**
- **user-adaptive summarization**
- **email prioritization**
- **email triage**
- **email thread summarization**
- **salience-based content selection**
- **coverage-aware summarization**
- **coverage-constrained summarization**
- **constrained content selection**
- **incremental dialogue summarization**
- **action-item-aware summarization**
- **decision-focused meeting summarization**

Some promoted compound expressions are search constructions rather than claims that a mature task exists under exactly that name. Discovery must still verify terminology from papers.

### Terms to demote

These can remain as auxiliary probes but should not drive the main discovery corpus:

- delta summarization
- information update detection
- entity-centric summarization
- event-centric summarization
- topic-focused summarization
- preference-aware ranking
- response priority prediction
- notification prioritization
- digest generation
- generic learning to rank
- generic multi-document summarization

`delta summarization` should be considered rejected as a primary academic task label because its expected false-positive rate is especially high.

## Academic task families

### F1 — Update summarization and novelty-aware multi-document summarization — DIRECT

**Academic task.** Produce a summary for a new document set when the reader is assumed to know an earlier document set, emphasizing information that changes or extends that prior knowledge.

**Why it matters.** This is the closest established task to:

> What changed since the user's previous accepted view?

It directly supports novelty reasoning and redundant-information suppression.

The central transfer limitation is equally important: canonical update summarization generally assumes that previously known information need not be repeated. msgloom cannot adopt that assumption unconditionally because an unchanged but unresolved deadline or action may have to remain visible.

Confident seed papers:

- Carbonell and Goldstein (1998), *The Use of MMR, Diversity-Based Reranking for Reordering Documents and Producing Summaries*.
- Mani and Bloedorn (1999), *Summarizing Similarities and Differences Among Related Documents*.
- Dang and Owczarzak (2008), *Overview of the TAC 2008 Update Summarization Task*.

Discovery should specifically inspect evaluation definitions: a method that receives credit for suppressing all old information may be useful for novelty detection but insufficient for the final briefing contract.

### F2 — Incremental and streaming summarization of evolving information — DIRECT

**Academic task.** Maintain a summary or emit summary units as information arrives sequentially rather than after corpus closure.

**Why it matters.** msgloom repeatedly receives new workplace communication. It therefore needs more than a static MDS model executed once.

Relevant mechanisms include:

- deciding whether an incoming item changes the current summary;
- avoiding repeated emission;
- maintaining a compact representation of previously processed information;
- revising a summary when later evidence changes interpretation;
- balancing immediate emission against later evidence.

Confident seed paper:

- Allan et al. (1998), *On-Line New Event Detection and Tracking*.

This paper belongs to adjacent event-detection literature rather than the complete summarization task, but it is foundational for online novelty reasoning.

Discovery should distinguish **semantic incrementality** from papers where “incremental” only means reduced computation.

### F3 — Temporal and timeline summarization — TRANSFER

**Academic task.** Represent event evolution by selecting salient temporally distributed developments.

**Why it matters.** Topic 09 receives temporally ordered and supersession-aware state from Topic 06. Timeline literature may provide mechanisms for deciding which changes deserve explicit presentation and how to avoid repeating obsolete facts.

Confident seed paper:

- Yan et al. (2011), *Evolutionary Timeline Summarization: a Balanced Optimization Framework via Iterative Substitution*.

The main limitation is structural: timelines normally contain **events worth adding**. An unchanged overdue obligation may have no event at the current time but must remain visible in msgloom.

The family is therefore TRANSFER rather than direct evidence for the complete target.

### F4 — Query-focused and topic-focused multi-document summarization — TRANSFER

**Academic task.** Generate a multi-source summary conditioned on an explicit query or information need.

**Why it matters.** A msgloom Topic can be viewed, approximately, as a persistent information-selection target. Query-focused MDS therefore provides useful research on:

- relevance-conditioned sentence/proposition selection;
- combining evidence across sources;
- controlling redundancy;
- retaining information that answers the information need;
- balancing relevance and general importance.

Confident seed papers:

- Tombros and Sanderson (1998), *Advantages of Query Biased Summaries in Information Retrieval*.
- Daumé III and Marcu (2006), *Bayesian Query-Focused Summarization*.

The analogy must not be overextended. A query does not encode Topic identity, current lifecycle state, explicit Triage rules, or a previous accepted view.

### F5 — Personalized and user-adaptive summarization — TRANSFER

**Academic task.** Generate different summaries for different users according to profiles, interests, expertise, interaction histories, or preferences.

**Why it matters.** msgloom's report is explicitly personal rather than a universally optimal summary.

Research questions worth extracting include:

- which user signals are used;
- whether explicit and inferred preferences can be combined;
- whether personalization affects selection, ordering, realization, or all three;
- how personalization is evaluated;
- whether required information can be protected from personalization;
- how adaptation changes over time.

The critical msgloom rule is:

```text
explicit Triage rules / required coverage
              >
learned or inferred preference
              >
presentation optimization
```

A system that learns that the user rarely opens a class of urgent messages and subsequently suppresses them is precisely the behavior to avoid.

No seed paper is listed here because a paper should not be named without sufficient confidence in the exact bibliographic identity.

### F6 — Email prioritization and email triage — DIRECT

**Academic task.** Determine which emails deserve attention, should be acted upon, are important/urgent, or should be handled in a particular order.

**Why it matters.** This family operates directly in the target communication domain and addresses the scarce-attention problem underlying msgloom.

Foundational workplace context:

- Whittaker and Sidner (1996), *Email Overload: Exploring Personal Information Management of Email*.

Discovery must separate several targets that are frequently collapsed:

```text
important
urgent
interesting
likely to be opened
likely to receive a reply
likely to receive a fast reply
requires a response
requires an action
```

They are not interchangeable.

In particular:

> **P(reply | message, user) is not a model of obligation.**

Reply behavior may be a feature or weak proxy, but it cannot be accepted as the ground truth for “requires the user's response.”

### F7 — Salience, content selection, coverage, diversity and constrained summarization — TRANSFER

**Academic task.** Select a limited set of information units under some combination of importance, relevance, coverage, redundancy, diversity and explicit constraints.

**Why it matters.** This family addresses the other half of Topic 09 that novelty literature does not solve:

> What must survive compression even if it is not new?

Potentially useful formulations include:

- weighted set coverage;
- submodular selection;
- maximum coverage under a length budget;
- hard inclusion constraints;
- soft inclusion penalties;
- asymmetric omission costs;
- redundancy penalties;
- diversity objectives;
- constrained extractive summarization.

Confident seed papers:

- Carbonell and Goldstein (1998), *The Use of MMR, Diversity-Based Reranking for Reordering Documents and Producing Summaries*.
- Lin and Bilmes (2011), *A Class of Submodular Functions for Document Summarization*.

For msgloom, the important formulation is not merely:

```text
maximize average semantic coverage
```

but closer to:

```text
subject to:
    every due Topic remains represented
    every mandatory action/deadline/risk/condition remains represented
    unresolved high-priority state remains represented

maximize:
    decision-relevant salience
    novelty
    useful context

minimize:
    redundant repetition
    unnecessary detail
```

Discovery should therefore give higher value to papers allowing explicit required-item constraints or asymmetric omission penalties than to papers reporting only average ROUGE improvements.

### F8 — Email-thread and workplace-conversation summarization — DIRECT

**Academic task.** Summarize communication structures such as email threads and meetings, often exploiting conversational order, reply relations, speaker identity and discourse structure.

**Why it matters.** This family supplies the closest direct evidence about summarization of workplace communication.

Confident seed papers:

- Rambow et al. (2004), *Summarizing Email Threads*.
- Murray et al. (2005), *Extractive Summarization of Meeting Recordings*.

Important admission caveat:

```text
email thread != msgloom Topic
meeting != msgloom Topic
chat session != msgloom Topic
```

A single thread may contain several work matters, while one work matter may cross multiple threads and sources. Topic 03 owns that identity problem.

This family is nevertheless valuable for understanding what information workplace-conversation summarizers preserve or lose, particularly requests, decisions and action items.

### F9 — Incremental dialogue and long-running conversation summarization — TRANSFER

**Academic task.** Continuously revise a summary or memory representation as dialogue progresses over many turns or sessions.

**Why it matters.** This newer literature may provide mechanisms for:

- summary revision rather than full regeneration;
- compression of accumulated history;
- preservation of conversational state;
- removal of superseded information;
- incorporation of new turns;
- hierarchical memory.

The project should specifically search for papers that evaluate **summary changes across time**, not merely one final summary of a long transcript.

This remains TRANSFER because dialogue turn order does not establish stable cross-thread Topic identity, and many datasets lack explicit unresolved work state.

### F10 — Personalized ranking and learning-to-rank for priority ordering — TRANSFER

**Academic task.** Learn how to order candidate items from features, preferences or user interaction.

**Why it matters.** Ranking may be useful after the set of mandatory briefing content has been established.

Confident generic seed paper:

- Joachims (2002), *Optimizing Search Engines Using Clickthrough Data*.

For msgloom the correct architectural interpretation is approximately:

```text
mandatory coverage / explicit rules
        ↓
eligible briefing items
        ↓
priority scoring or ranking
        ↓
presentation order
```

not:

```text
rank everything
        ↓
truncate at K
```

The latter can lose mandatory work.

Learning-to-rank literature is therefore methodological transfer evidence rather than proof that ranking solves briefing completeness.

### F11 — Notification prioritization and attention management — TRANSFER

**Academic task.** Decide which notifications should interrupt or reach the user and when.

**Why it matters.** It may contribute models of urgency, attention cost and presentation ordering when the report contains many due Topics.

It does **not** determine whether a Topic may disappear from the report. A notification can legitimately be deferred because interruption cost is high; a required Topic in a scheduled briefing may still need to be represented.

Notification work should therefore be admitted only when it contributes a mechanism relevant to prioritization, urgency, attention allocation, or presentation—not as evidence for report completeness.

## Query families

Discovery should run task-family queries rather than one large bag of seed terms.

### F1 — Update summarization and novelty-aware MDS — DIRECT

```text
"update summarization" multi-document
"update summarization" novelty redundancy
"update summarization" previously read information
"update summarization" evolving documents
"update summarization" prior documents new information
"update summarization" important information redundancy
"update summarization" persistent state unresolved
"update summarization" action items deadlines
```

**Role:** find the established literature closest to “tell me what changed,” then inspect whether it can also retain still-relevant old information.

### F2 — Incremental and streaming summarization — DIRECT

```text
"incremental summarization" evolving documents
"incremental summarization" information stream
"incremental summarization" online summarization
"streaming summarization" novelty redundancy
"stream summarization" update detection
"incremental summary" evolving information
"incremental summarization" persistent information
"incremental summarization" unresolved tasks
```

**Role:** identify methods that maintain summaries across successive arrivals rather than treating each report cycle independently.

### F3 — Temporal and timeline summarization — TRANSFER

```text
"temporal summarization" events
"temporal summarization" evolving events
"timeline summarization" event evolution
"timeline summarization" update redundancy
"timeline summarization" temporal salience
"temporal summarization" novelty
"timeline summarization" obsolete information
```

**Role:** transfer mechanisms for chronological change, temporally distributed salience and obsolete-information suppression.

### F4 — Query/topic-focused multi-document summarization — TRANSFER

```text
"query-focused multi-document summarization"
"query focused summarization" multi-document redundancy
"query-focused summarization" information need coverage
"topic-focused summarization" conversation
"topic-focused summarization" multi-document
"query-focused summarization" temporal update
"query-focused summarization" evolving documents
```

**Role:** transfer Topic-conditioned multi-source content-selection mechanisms.

### F5 — Personalized/user-adaptive summarization — TRANSFER

```text
"personalized summarization" user preferences
"personalized summarization" user profile
"personalized summarization" user interests
"user-adaptive summarization"
"adaptive summarization" user model
"personalized summarization" multi-document
"personalized summarization" temporal
"personalized summarization" constraints
```

**Role:** determine how individual user context can influence selection and presentation without overriding explicit policy or mandatory content.

### F6 — Email prioritization and triage — DIRECT

```text
"email prioritization" importance
"email prioritization" urgency
"email prioritization" action
"email triage" prioritization
"email triage" learning to rank
"email triage" task prediction
"email triage" action required
"email importance" prediction user
"email priority" user model
"email prioritization" reply prediction
"email triage" obligation response
```

**Role:** find direct workplace-domain evidence for prioritization and identify precisely what each paper's label means.

The paired searches involving reply prediction are deliberate: they should expose whether the literature distinguishes reply likelihood from required response.

### F7 — Coverage, salience and constrained content selection — TRANSFER

```text
"coverage-aware summarization"
"coverage aware" summarization important information
"constrained summarization" required information
"constrained summarization" content selection
"content selection" summarization coverage redundancy
"salience estimation" summarization coverage
"submodular" summarization coverage redundancy
"summary" mandatory content constraints
"summarization" required concepts coverage
"summarization" omission cost important information
```

**Role:** find mechanisms for protecting essential information while controlling redundancy and length.

### F8 — Email/workplace conversation summarization — DIRECT

```text
"email thread summarization"
"email conversation summarization"
"email summarization" thread structure
"email summarization" action items
"email summarization" decisions requests
"workplace communication" summarization
"meeting summarization" action items decisions
"conversation summarization" tasks decisions
"email thread" summary unresolved
```

**Role:** find direct target-domain evidence while explicitly rejecting the assumption that thread identity equals Topic identity.

### F9 — Incremental dialogue and long-running conversation summarization — TRANSFER

```text
"incremental dialogue summarization"
"incremental conversation summarization"
"online dialogue summarization"
"long-running conversation summarization"
"long conversation summarization" memory
"dialogue summarization" summary update
"dialogue summarization" unresolved tasks
"conversation summarization" action items unresolved
"dialogue summarization" evolving state
```

**Role:** find methods that revise conversational summaries over time and test whether they preserve pending or unresolved content.

### F10 — Personalized ranking / learning to rank — TRANSFER

```text
"personalized ranking" information priority
"personalized ranking" user context
"learning to rank" email priority
"learning to rank" importance ranking
"preference-aware ranking" information
"priority ranking" user preferences information
"learning to rank" urgency importance
"multi-objective ranking" importance coverage
```

**Role:** transfer ranking mechanisms for ordering already-admitted briefing content. Generic ranking papers should not enter the final evidence base unless the objective maps meaningfully onto Topic 09.

### F11 — Notification prioritization / attention management — TRANSFER

```text
"notification prioritization" importance urgency
"notification prioritization" user attention
"notification ranking" urgency relevance
"attention management" notification importance
"notification prioritization" work
"notification ranking" task importance
```

**Role:** transfer models of scarce attention, urgency and interruption cost. Do not treat suppression of a notification as evidence that report content can be omitted.

## False friends and downgrade rules

Discovery should downgrade or exclude the following even when titles or abstracts contain target keywords.

1. **Generic message-level summarization.** A paper summarizing each email separately does not solve Topic-level cross-message briefing.

2. **Static MDS with no prior state.** Multi-document summarization is insufficient when every report is generated from scratch and the system cannot distinguish previously accepted information from a new development.

3. **Pure novelty detection.** Reject as complete evidence when the algorithm intentionally suppresses all previously known material. Topic 09 requires selective persistence of unresolved important state.

4. **“Update” meaning software/document revision.** Exclude source-code change summaries, commit-message generation, revision-diff summaries, database deltas and change-log generation unless a transferable mechanism is explicitly relevant.

5. **Temporal/event systems with no open-state representation.** A correct event timeline still does not solve carrying forward an overdue action.

6. **Entity grouping as Topic identity.** An entity is not a work matter. Multiple Topics can involve the same people or organizations.

7. **Broad topical grouping as Topic identity.** Latent topics and lexical themes do not establish the concrete work-item identity supplied by Topic 03.

8. **Response likelihood treated as obligation.** Papers predicting whether, when or how rapidly a user replies cannot be admitted as evidence for required-response detection unless the targets are explicitly distinguished.

9. **Engagement ranking.** Click-through, dwell time, popularity, recommendation utility and opening probability are not substitutes for work priority.

10. **Spam and filing classification.** Email classification is not email prioritization unless it directly studies attention, importance, action or equivalent signals.

11. **Notification timing as completeness.** Interruptibility and delivery-time optimization do not establish whether information may be omitted from a briefing.

12. **Generic learning to rank.** Treat as method transfer only. A ranking loss alone does not supply the target objective.

13. **Coverage defined only as lexical/topic diversity.** Topic 09 needs coverage of semantically required information such as actions, deadlines, risks and unresolved state.

14. **Constrained summarization with irrelevant constraints.** Length, vocabulary, syntax, style and decoding constraints are not the target unless the paper also supports required information inclusion.

15. **Long-context capability without state semantics.** Processing 100k tokens is not evidence of incremental briefing if the model still produces a fresh one-shot summary.

16. **Dialogue session equals Topic.** Conversation and meeting summarizers must be treated cautiously because one session can contain multiple Topics and one Topic can span multiple sessions.

17. **Digest generation as a product label.** Newsletter/RSS/feed aggregation with no formal update, priority or coverage model should not enter the academic corpus.

18. **ROUGE-only evidence.** A paper can be methodologically relevant, but ROUGE improvements do not demonstrate that actions, deadlines, risks or due Topics are preserved.

19. **Fluency-only evaluation.** Human ratings of readability or coherence do not establish decision-essential completeness.

20. **Brevity as the objective.** Compression ratio is not success when it is achieved by deleting required information.

21. **Frequency as importance.** Repeated mentions can indicate unresolved urgency or mere redundancy. Frequency alone cannot decide which.

22. **Latest statement equals current truth.** Topic 09 should consume current/superseded/uncertain state from Topic 06 rather than infer state by choosing the most recent sentence.

23. **Body-text-only evidence.** Topic 08 establishes the boundary that structured attachment evidence can be decision-relevant. A briefing study relying only on flattened message text cannot by itself establish complete evidence coverage.

24. **Transfer-domain evidence mislabelled as direct.** News, social media, meetings, search and recommendation papers can justify mechanisms or experiments but not production-email effectiveness.

25. **Personalization allowed to override explicit rules.** User-interest optimization is relevant only when explicit Triage and mandatory coverage can remain authoritative.

A concise admission test is:

```text
Does the paper provide evidence about at least one of:

A. distinguishing new information from already-known information;
B. preserving/revising a summary over successive arrivals;
C. retaining required important content under compression;
D. prioritizing workplace communication for a specific user;
E. adapting summarization to user-specific information needs;
F. avoiding redundant or superseded content;
G. representing or preserving unresolved actions/state?

If none apply:
    downgrade.

If only a transferable mechanism applies outside workplace communication:
    label TRANSFER.

If the paper claims the whole target is solved merely through novelty,
reply likelihood, engagement or generic summarization:
    downgrade.
```

## Date policy

**Earliest publication year discovery must include: 1996.**

The search must not use a recent-only window.

The relevant intellectual roots begin in the **1990s**, not in the modern LLM period and not even only in the DUC/TAC period.

At least four lines of foundational work matter:

1. **Workplace email overload and triage context:** Whittaker and Sidner's *Email Overload: Exploring Personal Information Management of Email* appeared in **1996**.

2. **Query-biased summarization:** Tombros and Sanderson's work on query-biased summaries appeared in **1998**.

3. **Novelty/diversity/redundancy-aware selection:** Carbonell and Goldstein's MMR work appeared in **1998**.

4. **Online new-event detection:** Allan and colleagues' work appeared in **1998**.

Mani and Bloedorn's work on summarizing similarities and differences among related documents followed in **1999**, and the 2000s subsequently developed mature multi-document, query-focused and update-summarization benchmarks.

Therefore the discovery lower bound should be:

```text
1996-present
```

not:

```text
2005-present
2010-present
2015-present
LLM-era only
```

A later date filter would silently exclude exactly the work that established several concepts Topic 09 depends on: information overload, novelty, redundancy/diversity, query-conditioned summary selection and online change detection.

Modern neural and LLM literature should still receive substantial coverage, but it should be interpreted as a later methodological layer over these older task definitions rather than as the origin of the problem.
