# cross-thread topic identity and incremental continuity in work communication academic terminology analysis

## Product problem

The product problem is not ordinary email threading, semantic similarity, topic modeling, or summarization. It is an **incremental identity decision over concrete work matters**.

For each new candidate matter/span/group, the system must decide among:

- **CONTINUE** an existing Topic;
- create a **NEW** Topic;
- preserve an **UNCERTAIN** relationship while keeping matters separate;
- later issue a **MERGE** correction;
- later issue a **SPLIT** correction.

The critical semantic distinction is **identity versus relatedness**. Two messages may share participants, customer, project, subject, wording, or embeddings and still concern different matters. Conversely, the same matter may migrate across email threads, titles, groups, attachments, and communication systems.

No single established academic task captures the complete product requirement. The literature should therefore be assembled around several adjacent task families, with an explicit distinction between **DIRECT** evidence and **TRANSFER** evidence.

The strongest direct academic analogues are:

1. **cross-document event coreference / event identity**;
2. **Topic Detection and Tracking (TDT), especially story-link detection and new-event detection**;
3. any genuinely domain-specific work on **cross-thread or cross-channel work-item/task/case identity**.

The most useful transfer literatures are:

- entity resolution and cross-document entity coreference;
- probabilistic record linkage;
- incremental/online clustering;
- open-set recognition and reject-option classification;
- evolving-cluster merge/split maintenance;
- incremental entity resolution;
- event threading/storyline evolution;
- process-event correlation and case-notion discovery.

The search must heavily penalize false merges, because a false merge can cause one distinct due work matter to disappear from a downstream report.

## Seed keyword audit

| Seed | Academic meaning | Fit | Main risk |
| --- | --- | --- | --- |
| cross-document event coreference | Deciding whether event mentions in different documents denote the same real-world event and clustering coreferent mentions. | STRONG | News-event identity is usually narrower and more static than a continuing work matter. |
| cross-document event coreference resolution | Resolving cross-document event mentions into same-event equivalence classes. | STRONG | Frequently evaluated as static clustering, without online abstention or later correction. |
| event coreference resolution | Determining which textual event mentions refer to the same event, within or across documents. | STRONG | Unqualified searches are dominated by within-document work. |
| event identity | Broad term for determining when descriptions correspond to one event. | STRONG | Also attracts philosophy, ontology, and formal event semantics. |
| same-event detection | Pairwise or clustering decision that observations/descriptions concern the same underlying event. | STRONG | Less standardized terminology and often conflated with similarity. |
| event linking | Linking an event mention to another event, event cluster, KB event, or related event. | MODERATE | A link often denotes relatedness rather than identity. |
| cross-document event linking | Linking event information across documents. | MODERATE | May include causal, temporal, or storyline relations instead of equivalence. |
| cross-document coreference | Resolving cross-document references, especially entities and sometimes events. | MODERATE | Entity coreference dominates many searches. |
| entity resolution | Matching records/mentions representing one real-world entity. | MODERATE | Stable entities differ substantially from evolving work matters. |
| entity linking | Mapping text mentions to canonical KB entities, sometimes with NIL handling. | WEAK | Mostly a knowledge-base grounding task rather than emergent Topic identity. |
| record linkage | Matching structured records believed to represent the same underlying entity. | MODERATE | Usually structured, static, and entity-oriented. |
| topic detection and tracking | TDT family for detecting and tracking specific news events/topics in streams. | STRONG | TDT topic semantics must be checked: specific event is useful; broad category is not. |
| story link detection | TDT decision whether two stories concern the same target topic/event. | STRONG | Pairwise linkage alone does not supply persistent cluster maintenance. |
| new event detection | TDT decision that an incoming story concerns a previously unseen event. | STRONG | Usually first-story news detection rather than evolving workplace cases. |
| novelty detection | Detecting observations unlike known data/classes/content. | MODERATE | Statistical novelty is not equivalent to a new Topic identity. |
| incremental clustering | Updating clusters as new observations arrive. | STRONG | Many algorithms force similarity-based assignment without identity semantics. |
| online clustering | Sequentially assigning observations to clusters. | STRONG | Online clustering is useful structurally but may equate nearest cluster with same identity. |
| streaming clustering | Clustering continuously arriving data under resource and drift constraints. | MODERATE | Literature often emphasizes throughput/memory/concept drift rather than identity. |
| cluster linking | Connecting clusters across time, partitions, views, or systems. | WEAK | Not standardized and frequently means cluster similarity/alignment. |
| cluster maintenance | Maintaining clusters under additions, deletions, drift, merge, or split. | MODERATE | Often computational maintenance without semantic identity or provenance. |
| dynamic clustering | Clustering evolving data and possibly modeling cluster birth/death/merge/split. | MODERATE | Very broad; frequently geometric rather than identity-preserving. |
| event evolution | Modeling how events/storylines develop into stages or related subevents. | MODERATE | Often deliberately links distinct but related events. |
| event timeline tracking | Tracking and ordering events or event-bearing documents over time. | MODERATE | Identity may already be assumed; task may only order or summarize. |
| business email | Domain descriptor for organizational email. | WEAK | Retrieves classification, summarization, thread reconstruction, spam, and organizational studies. |
| workplace communication | Broad organizational communication domain. | WEAK | Dominated by organizational behavior rather than computational identity. |
| enterprise communication | Broad enterprise collaboration/communications domain. | WEAK | Infrastructure, social-network, compliance, and organizational literature dominates. |
| work chat | Informal descriptor for workplace messaging. | WEAK | Not a stable academic task name; attracts chatbot and communication studies. |
| asynchronous conversation | Delayed interaction through email/forums/chat. | WEAK | Primarily retrieves conversation structure, discourse, and participation research. |

### Terms to promote

Primary discovery vocabulary should promote:

- **cross-document event coreference**;
- **cross-document event coreference resolution**;
- **event coreference resolution**;
- **event identity**;
- **same-event detection**;
- **event clustering**;
- **Topic Detection and Tracking**;
- **story link detection**;
- **new event detection**;
- **first-story detection**;
- **topic tracking**;
- **incremental clustering**;
- **online clustering**;
- **incremental entity resolution**;
- **online entity resolution**;
- **open-set recognition**;
- **unknown-class detection**;
- **reject option**;
- **selective classification**;
- **cluster merge/split**;
- **cluster evolution**;
- **event threading**;
- **process event correlation**;
- **case notion discovery**;
- **cross-channel work-item linking**.

### Terms to demote or qualify

The following should not be primary unqualified searches:

- event linking;
- cross-document event linking;
- entity linking;
- cluster linking;
- cluster maintenance;
- dynamic clustering;
- event evolution;
- event timeline tracking;
- business email;
- workplace communication;
- enterprise communication;
- work chat;
- asynchronous conversation.

They remain useful only when combined with stronger identity terminology.

## Academic task families

### F1 — Cross-document event coreference and event identity — DIRECT

**Task.** Determine whether event mentions in independent documents refer to the same underlying event, then construct event-identity clusters.

**Why it matters.** This is the closest mature NLP task to the requirement that independent pieces of evidence can denote one concrete matter. Particularly valuable evidence includes:

- identity versus semantic similarity;
- temporal, participant, location, action, and argument compatibility;
- pairwise versus cluster-level inference;
- transitivity and cluster consistency;
- false merges and false splits;
- benchmark construction for cross-document identity.

**Known seed paper:**  
Bagga and Baldwin (1999), *Cross-Document Event Coreference: Annotations, Experiments, and Observations*.

The transfer boundary still matters: a work matter may encompass a sequence of actions and state changes that event-coreference annotation would treat as several related events.

### F2 — Topic Detection and Tracking: story-link, tracking, and new-event detection — DIRECT

**Task.** Given a stream of incoming news stories, determine whether a story belongs to an existing tracked event/topic or begins a new one.

This maps unusually well to:

```text
existing target → CONTINUE
previously unseen target → NEW
insufficient confidence → ideally UNCERTAIN / reject
```

TDT is especially valuable because it explicitly studies:

- story-link detection;
- first-story/new-event detection;
- topic tracking;
- online rather than purely batch decisions;
- false alarms and misses.

**Known seed papers:**

- Allan, Papka, and Lavrenko (1998), *On-line New Event Detection and Tracking*.
- Yang, Pierce, and Carbonell (1998), *A Study of Retrospective and On-Line Event Detection*.

TDT papers must be admitted only when their "topic" corresponds to a **specific event/story target**, not a broad semantic category.

### F3 — Cross-document entity coreference and entity resolution — TRANSFER

**Task.** Determine whether distributed mentions or records represent the same entity.

Useful transferable ideas include:

- identity evidence from multiple weak attributes;
- collective rather than independent matching;
- transitivity;
- cluster consistency;
- ambiguous candidate sets;
- false-match and false-nonmatch control.

**Known seed paper:**  
Bagga and Baldwin (1998), *Entity-Based Cross-Document Coreferencing Using the Vector Space Model*.

The domain distinction is fundamental: a person or company is normally a persistent object, while a work matter has temporal development, completion, reopening, branching, and possible relation to other matters involving the same actors.

### F4 — Record linkage and probabilistic matching — TRANSFER

**Task.** Combine evidence from several fields to estimate whether two records represent one underlying identity.

Its main value is methodological: the system should not treat participant, project, object, source structure, timing, wording, or action overlap as individually dispositive. Identity can instead be treated as a combination of evidence with explicit support for match, non-match, and uncertainty.

**Foundational seed paper:**  
Fellegi and Sunter (1969), *A Theory for Record Linkage*.

This family is particularly relevant to Phase 1's requirement to avoid a continuation decision when supplied evidence does not support it strongly enough.

### F5 — Incremental, online, and streaming clustering — TRANSFER

**Task.** Maintain clusters as new observations arrive.

The important questions for msgloom are narrower than generic clustering:

- when is an observation attached to an existing cluster?
- when is a new cluster created?
- can assignment be deferred?
- how sensitive is assignment to arrival order?
- can earlier assignments be revised?
- what happens when clusters merge or split?
- is cluster identity persistent over time?

**Known seed papers:**

- Charikar, Chekuri, Feder, and Motwani (1997), *Incremental Clustering and Dynamic Information Retrieval*.
- Aggarwal, Han, Wang, and Yu (2003), *A Framework for Clustering Evolving Data Streams*.

A high-performing streaming-clustering method is not sufficient evidence if its clusters represent geometric similarity and every observation must be assigned somewhere.

### F6 — Open-set recognition, novelty detection, unknown classes, and reject option — TRANSFER

**Task.** Permit a decision system to say that no known class is adequate, or to abstain when evidence is insufficient.

This family matters because msgloom must not collapse:

```text
no confident continuation
```

into:

```text
therefore definitely NEW
```

The system requires at least three semantically distinct outcomes:

```text
known existing identity
new identity
uncertain / insufficient evidence
```

Useful concepts include:

- reject option;
- open-set recognition;
- unknown-class detection;
- open-world recognition;
- selective classification;
- risk-coverage trade-offs;
- false acceptance versus false rejection.

**Known seed papers:**

- Chow (1970), *On Optimum Recognition Error and Reject Tradeoff*.
- Scheirer, de Rezende Rocha, Sapkota, and Boult (2013), *Toward Open Set Recognition*.

Image-recognition results are only transfer evidence; the reusable part is the rejection formulation and evaluation methodology.

### F7 — Dynamic cluster maintenance, merge/split, and correction — TRANSFER

**Task.** Modify an evolving clustering when later evidence invalidates an earlier partition.

Search specifically for:

- cluster birth/death;
- cluster merge;
- cluster split;
- reassignment;
- persistent cluster identifiers;
- correction of online clustering;
- temporal cluster evolution.

For msgloom, a useful mechanism must be interpreted through a stricter provenance rule:

> a later correction creates a new assessment and relationship history; it must not erase the original source evidence or pretend that the earlier decision never existed.

Most clustering literature will not satisfy that requirement directly, so this family is primarily mechanism transfer.

### F8 — Event threading, storyline construction, and event evolution — TRANSFER

**Task.** Connect event-bearing documents or subevents into temporally coherent developments.

Useful signals include:

- temporal compatibility;
- predecessor/successor relationships;
- state progression;
- participants and arguments;
- narrative continuity;
- discrimination of concurrent storylines.

**Known seed papers:**

- Nallapati, Feng, Peng, and Allan (2004), *Event Threading within News Topics*.
- Shahaf and Guestrin (2010), *Connecting the Dots Between News Articles*.

The principal admission test is whether the paper distinguishes **same event/case** from **related event in the same storyline**. A causal or narrative link is not proof of Topic identity.

### F9 — Incremental entity resolution and evolving identity clusters — TRANSFER

This family is more targeted than either static entity resolution or generic streaming clustering.

Queries should seek systems in which:

- new records arrive over time;
- a record can start a new entity;
- existing entity clusters are updated;
- an incorrect match can propagate;
- cluster repair or re-resolution is possible.

This is potentially valuable for stable Topic IDs and conservative assignment, but evidence remains transfer evidence because the object being resolved is normally a person/product/customer rather than a work matter.

### F10 — Process-event correlation and case notion discovery — TRANSFER

Process mining contains an adjacent problem: event records may lack reliable case identifiers, so events must be correlated into process instances or "cases."

This maps naturally onto:

```text
communication evidence → which concrete work case does it belong to?
```

Useful terminology includes:

- event correlation;
- event-to-case correlation;
- case identification;
- case notion discovery;
- case correlation.

This literature is worth searching because it may combine:

- object identifiers;
- actors;
- temporal constraints;
- workflow structure;
- activity compatibility.

It must remain TRANSFER unless its assumptions match the target domain. Many process-log methods rely on highly structured attributes or deterministic workflow constraints that free-form email and chat do not provide.

### F11 — Workplace email/chat matter linking and cross-channel continuity — DIRECT

This is the target-domain family but probably the least terminologically standardized.

Discovery should therefore search several formulations:

- work item;
- task;
- issue;
- case;
- activity;
- matter;
- cross-thread;
- cross-channel;
- email/chat linking;
- email/Teams continuity.

Papers should be considered genuinely DIRECT only when their target is something like:

> determine that communication artifacts in separate threads/channels belong to the same concrete work activity, task, issue, or case.

Ordinary email threading or conversation disentanglement is Topic 01 territory and should not be admitted here merely because it uses email.

## Query families

### F1 — DIRECT — Cross-document event coreference

```text
"cross-document event coreference" identity
"cross-document event coreference resolution"
"event coreference" "cross-document" clustering
"event identity" computational linguistics same event
"same event" detection cross document
"event coreference" identity criteria temporal participant location
"cross-document event coreference" benchmark dataset evaluation
"event coreference" false merge false split clustering
```

### F2 — DIRECT — TDT / new-event decisions

```text
"topic detection and tracking" "new event detection"
"story link detection" TDT
"new event detection" topic tracking
"first story detection" topic detection tracking
"on-line new event detection"
"online new event detection" news stream
"topic tracking" story link detection evaluation
"new event detection" false alarm miss cost
```

### F3 — TRANSFER — Entity resolution/coreference

```text
"cross-document entity coreference" identity
"entity resolution" collective evidence clustering
"entity resolution" ambiguous match abstention
"entity matching" identity evidence false merge
"cross-document coreference" entity clustering
"entity resolution" cluster consistency transitivity
```

### F4 — TRANSFER — Record linkage

```text
"record linkage" probabilistic matching uncertainty
"record linkage" match nonmatch clerical review
"probabilistic record linkage" evidence fields
"entity resolution" "record linkage" match probability
"record linkage" false match false nonmatch
```

The term **clerical review** is useful because classical linkage formulations explicitly recognize a middle region in which evidence does not justify an automatic match or non-match. That is conceptually close to msgloom's UNCERTAIN state even though human review is not necessarily the desired implementation.

### F5 — TRANSFER — Incremental/online clustering

```text
"incremental clustering" online new cluster creation
"online clustering" new cluster assignment
"streaming clustering" cluster creation merge split
"incremental clustering" text documents
"online clustering" text stream novelty
"streaming clustering" text events
"incremental clustering" dynamic information retrieval
"clustering evolving data streams" cluster evolution
```

### F6 — TRANSFER — Reject / unknown / open set

```text
"open set recognition" reject unknown class
"open set classification" abstention
"reject option" classification uncertainty
"classification with reject option" risk
"unknown class detection" open set
"novelty detection" new class streaming
"cluster assignment" abstention
"selective classification" abstention risk coverage
"open world" classification unknown class
```

### F7 — TRANSFER — Merge/split and correction

```text
"dynamic clustering" merge split clusters
"cluster maintenance" merge split incremental
"evolving clusters" merge split streaming
"online clustering" cluster split merge
"incremental clustering" correction reassignment
"cluster evolution" birth death merge split
"dynamic clustering" persistent cluster identity
```

### F8 — TRANSFER — Event evolution and threading

```text
"event threading" news
"event evolution" news tracking
"event timeline" tracking storyline
"storyline" event tracking news
"event evolution" temporal consistency
"event threading" temporal event relations
"storyline construction" news event identity
```

### F9 — TRANSFER — Incremental entity resolution

```text
"incremental entity resolution"
"online entity resolution"
"streaming entity resolution"
"incremental record linkage"
"dynamic entity resolution"
"incremental entity resolution" new entity
"entity resolution" streaming cluster
```

### F10 — TRANSFER — Process/case correlation

```text
"event correlation" process mining case
"case notion discovery" process mining
"case identification" process mining event correlation
"event-to-case correlation"
"case correlation" event log
"case notion" event correlation ambiguous
```

### F11 — DIRECT — Target workplace domain

```text
"work item" identity email
"work item" linking email chat
"task identity" workplace communication
"case identity" email communication
"issue linking" email workplace
"cross-thread" email topic tracking
"cross-thread" work matter email
"cross-channel" email chat task linking
"cross-channel" workplace communication continuity
"business email" topic tracking cross thread
"enterprise communication" task linking
"workplace communication" event linking
"email" "same task" identification
"email" "same issue" linking
"email" "same case" linking
"Teams" email cross-channel task
```

Domain queries should be snowballed aggressively. If a paper uses a different noun for the persistent unit — for example **case**, **activity**, **issue**, **task**, **work item**, **process instance**, or **matter** — that terminology should be added to subsequent discovery rather than forcing every result through the product word "Topic."

## False friends and downgrade rules

Discovery should downgrade or exclude the following even when keyword overlap is high.

1. **Latent topic modeling.** LDA, neural topic models, BERTopic-style clustering, or topic evolution where a "topic" is a word distribution or broad theme do not establish concrete-matter identity.

2. **Semantic similarity without identity labels.** Embedding similarity, nearest-neighbor retrieval, and document clustering are insufficient unless evaluation explicitly distinguishes the same underlying event/case from merely related content.

3. **Thread reconstruction and conversation disentanglement.** Reply trees, email conversation reconstruction, chat disentanglement, and quoted-text analysis belong to conversation/group structure, not Topic identity.

4. **Duplicate detection.** Exact and near-duplicate documents are a much narrower problem. Different descriptions may represent one matter, while highly similar templates may represent separate matters.

5. **Knowledge-base entity linking.** Wikipedia/Wikidata entity linking should normally be excluded except where NIL/unknown handling or open-world decision methodology is directly reusable.

6. **Static entity-resolution accuracy presented as direct evidence.** Customer/person/product linkage is useful transfer evidence but not production evidence for work-matter identity.

7. **Forced clustering.** Downgrade algorithms that must place every item in one existing cluster, assume a fixed number of clusters, or lack a principled new-cluster/rejection mechanism.

8. **Pure stream-engineering work.** Streaming clustering focused only on memory, throughput, micro-clusters, or numerical drift should not dominate the corpus.

9. **Generic anomaly detection.** "Unusual" does not mean "new Topic." A perfectly ordinary-looking email may begin a new matter.

10. **Broad-category TDT.** Admit TDT results only when a topic is a concrete event/story target rather than a category such as politics or finance.

11. **Related-event links presented as identity.** Temporal, causal, storyline, co-participation, or same-project relations are supporting evidence but do not imply equivalence.

12. **Timeline generation with identity assumed.** A system that receives pre-clustered events and only orders or summarizes them does not solve Topic 03.

13. **Process correlation based on an existing reliable case key.** Deterministic joining on an explicit case ID is not the target problem. Case-correlation work is useful only when case identity must actually be inferred.

14. **Email/chat studies without identity.** Spam, prioritization, sentiment, summarization, response prediction, organizational-network analysis, and general productivity studies are not Topic 03 evidence.

15. **Evaluation that hides false merges and false splits.** Prefer studies exposing these errors separately. For msgloom, false merging is especially costly because a distinct work matter may disappear from reports.

16. **Static batch-only clustering.** Batch results may still contribute methods, but should be downgraded for the longitudinal requirement unless the paper studies online assignment, new-cluster creation, order effects, or correction.

17. **No correction semantics.** An algorithm that silently rewrites cluster membership may help detect a better partition but does not by itself satisfy stable identity, lineage, or revision-history requirements.

18. **Single-feature identity assumptions.** Same subject, sender set, customer, project, work channel, thread, generated title, or embedding neighborhood must never be treated as sufficient proof of identity.

19. **Binary forced decisions.** Literature supporting explicit reject/uncertain outcomes is more relevant than otherwise similar work that requires every observation to be classified as either existing or new.

20. **Domain-transfer overclaiming.** News, bibliographic, process-log, customer, social-media, and synthetic results may justify mechanisms or experiments; they do not establish production-email accuracy.

## Date policy

**Earliest publication year discovery must include: 1969.**

A recent-only window would be methodologically wrong for this Topic.

The relevant foundations span several generations:

- **1969:** Fellegi and Sunter's probabilistic record-linkage formulation establishes foundational match/non-match evidence combination.
- **1970:** classical reject-option work formalizes the trade-off between automatic recognition and abstention.
- **1997:** incremental clustering is already an explicit research topic.
- **1998:** Topic Detection and Tracking work includes online event detection, tracking, story linkage, and first/new-event decisions.
- **1998:** cross-document entity coreference appears as an explicit computational problem.
- **1999:** cross-document event coreference is explicitly studied.
- **2000s onward:** streaming clustering, richer event threading, entity resolution, temporal/storyline modeling, and later open-set recognition substantially extend these foundations.

Therefore discovery should use **1969 as the global lower bound**, not an arbitrary recent window such as 2015-2026.

This does not mean every query needs equal attention across the entire period. A sensible discovery strategy is:

```text
1969 onward:
    foundational identity / record-linkage / rejection work

1997 onward:
    incremental clustering and dynamic information retrieval

1998 onward:
    TDT, story-link, topic tracking, new-event detection,
    cross-document coreference

2000s onward:
    streaming clustering, event threading/evolution,
    richer entity-resolution and case-correlation methods

recent literature:
    modern neural event coreference, representation learning,
    calibration, open-set/selective prediction, and cross-channel methods
```

Modern searches can add a recency-focused pass, but no recency filter should silently remove the late-1990s foundations of the most directly analogous tasks or the older probabilistic matching/rejection foundations.
