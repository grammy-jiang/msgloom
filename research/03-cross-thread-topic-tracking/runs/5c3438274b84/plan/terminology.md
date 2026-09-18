# Direct enterprise communication evidence for cross-thread work-matter continuity, with emphasis on email/chat conversation linking, business-event coreference, and partial or evolving event identity in organizational workflows academic terminology analysis

## Product problem

The product problem is not ordinary topic similarity, thread reconstruction, or message classification. The decision object is a **persistent concrete work-matter identity** whose evidence may appear across independent email threads, Teams conversations, attachments, documents, and time.

For each new candidate matter, msgloom ultimately needs to distinguish:

- **CONTINUE** an existing identity;
- **NEW** identity;
- **UNCERTAIN**, preserving separation;
- later **MERGE** correction;
- later **SPLIT** correction.

The literature search therefore needs evidence about five separate questions that broad keyword searches tend to conflate:

1. **Identity:** what makes two textual descriptions evidence of the same concrete event or matter rather than merely related or similar?
2. **Novelty:** when is a new observation sufficiently unsupported by existing identities that a new identity should be created?
3. **Non-equivalence relations:** when are two observations partially overlapping, subevent-related, successive, evolving, or related-but-separate rather than coreferential?
4. **Incrementality and correction:** how should decisions change as later evidence arrives?
5. **Uncertainty:** when should the system abstain rather than force either an attachment or a new identity?

Round 3 should also search a terminology family that is more business-process-specific than the original seed list: **event-to-case correlation / case-notion discovery in process mining**. That literature studies how business events are assigned to process instances when a reliable case identifier is absent. It is not the same problem as communication-based work-matter identity, but it is unusually close to the target's organizational setting and evidence structure.

A second important addition is **object-centric process mining**. Its importance is representational rather than directly predictive: it rejects the assumption that every event belongs to one flat case and therefore offers useful models for one observation participating in several object-centered histories.

## Seed keyword audit

| Seed | Academic meaning | Fit | Main risk |
| --- | --- | --- | --- |
| cross-document event coreference | Determines which event mentions in different documents denote the same real-world event. | STRONG | Mostly news/public-text benchmarks; target-domain transfer remains unvalidated. |
| cross-document event coreference resolution | Resolves cross-document event mentions into identity-equivalent clusters. | STRONG | Often static and based on transitive equivalence classes, without online abstention or correction. |
| event coreference resolution | Resolves textual mentions referring to the same event, within or across documents. | STRONG | Unqualified search retrieves large within-document literatures. |
| event identity | Criteria under which descriptions or mentions denote the same event. | STRONG | Highly polysemous; attracts philosophy and formal semantics without operational evaluation. |
| same-event detection | Decides whether reports, stories, mentions, or records concern the same event. | MODERATE | “Same event” may mean broad topical relatedness. |
| event linking | Can mean canonical-event linking, KB linking, argument linking, or relation linking. | MODERATE | Frequently not identity clustering at all. |
| cross-document event linking | Links event information across documents. | MODERATE | May cover broader related-event relations rather than identity. |
| cross-document coreference | Cross-document resolution of coreferential mentions. | MODERATE | Strongly attracts entity/person coreference rather than events. |
| entity resolution | Matches records or mentions referring to the same underlying entity. | MODERATE | Persistent entities have different identity semantics from evolving work matters. |
| entity linking | Maps mentions to canonical entities in a knowledge base. | WEAK | Usually fixed-inventory normalization, not persistent cluster discovery. |
| record linkage | Matches records representing the same entity without a perfect shared identifier. | MODERATE | Classical setting is static, attribute-based, and equivalence-oriented. |
| topic detection and tracking | Detects and tracks news events/topics through a stream. | MODERATE | Topic/story membership may be broader than concrete event identity. |
| story link detection | TDT decision about whether two stories concern the same target event/topic. | MODERATE | Story relatedness does not necessarily imply strict identity. |
| new event detection | Detects that an incoming story represents an event not previously observed. | STRONG | Close operational mapping to NEW, but news-event definitions differ from work matters. |
| novelty detection | Detects observations unlike known data/classes. | MODERATE | Extremely broad outside text/open-world assignment contexts. |
| incremental clustering | Updates clusters as observations arrive. | STRONG | Cluster cohesion is often similarity rather than identity. |
| online clustering | Sequentially assigns observations to clusters. | STRONG | Many methods force assignment and omit NEW/UNKNOWN semantics. |
| streaming clustering | Clusters high-volume streams with bounded resources. | MODERATE | Usually geometric/scalability research rather than semantic identity. |
| cluster linking | Associates clusters across partitions, times, or systems. | WEAK | Not a standardized academic task name. |
| cluster maintenance | Updates clusters through insertions, merges, splits, aging, etc. | MODERATE | Does not imply semantic identity, stable IDs, or lineage. |
| dynamic clustering | Allows clustering structure to change with time. | MODERATE | Often models changing geometry rather than identity correction. |
| event evolution | Models how events or event stories develop through time. | STRONG | Evolution and identity are different relations and are often conflated. |
| event timeline tracking | Builds or updates chronological event timelines. | MODERATE | Identity clusters are frequently assumed as inputs. |
| business email | Organizational email as a study domain. | MODERATE | Not a task name; attracts classification, spam, overload, and social-network work. |
| workplace communication | Communication through organizational media. | MODERATE | Dominated by HCI, organizational behavior, and discourse work. |
| enterprise communication | Organizational communication systems and data. | MODERATE | Dominated by systems, security, organizational analytics, and product literature. |
| work chat | Informal phrase for workplace messaging. | WEAK | Weak scholarly terminology; misses standard names such as enterprise social media or team messaging. |
| asynchronous conversation | Communication separated in time. | WEAK | Describes interaction mode, not work-matter identity. |

### Terms to promote

The next discovery round should add the following terms rather than relying on the original list:

- **event mention identity**
- **same-event identity**
- **event identity criteria**
- **event cluster assignment**
- **new-cluster creation**
- **first-story detection**
- **selective prediction**
- **reject option**
- **risk-coverage**
- **uncertain match**
- **incremental entity resolution**
- **collective entity resolution**
- **case notion**
- **case notion discovery**
- **event-to-case correlation**
- **case correlation**
- **case identification**
- **process instance identification**
- **business-process event correlation**
- **object-centric process mining**
- **object-centric event log**
- **artifact-centric process mining**
- **event partonomy**
- **event hierarchy**
- **event mereology**
- **subevent relation**
- **partial event coreference**
- **event granularity**
- **activity-based computing**
- **task-based information management**
- **cross-application activity tracking**
- **cross-channel activity linking**
- **cluster lineage**
- **cluster revision**
- **concept drift**
- **selective classification under distribution shift**

### Terms to demote unless constrained

These should not be used as broad standalone searches:

- entity linking;
- cluster linking;
- work chat;
- asynchronous conversation;
- dynamic clustering;
- cluster maintenance;
- novelty detection;
- business email;
- workplace communication;
- enterprise communication;
- event timeline tracking;
- event linking.

## Academic task families

### F1 — Cross-document event coreference and same-event identity — DIRECT

**Task.** Determine whether event mentions in different documents refer to the same concrete real-world event and form identity-equivalent clusters.

**Why it matters.** This is the closest mature NLP task to the core identity decision. It directly studies identity rather than merely semantic similarity.

**Important limitation.** Most benchmarks are news/public text. They therefore provide direct task evidence but not direct Outlook/Teams production evidence.

**Known seed papers**

- *Cross-document event coreference: Annotations, experiments, and observations* — Bagga and Baldwin (1999).
- *Joint Entity and Event Coreference Resolution across Documents* — Lee et al. (2012).
- *Revisiting Joint Modeling of Cross-document Entity and Event Coreference Resolution* — Barhom et al. (2019).

### F2 — Enterprise cross-thread work-matter, task, activity, and case continuity — DIRECT

**Task.** Explicitly link workplace email, enterprise chat, documents, or communication fragments to the same persistent task, activity, case, project episode, or concrete work item across independent conversations or channels.

**Why it matters.** This is the most important family for gap-1 and gap-4. It is also likely to be sparse, so terminology must span several communities rather than requiring the phrase “work-matter identity.”

**Admission requirement.** Enterprise data alone is not enough. A paper must actually infer or evaluate persistent cross-message/cross-conversation identity.

No seed paper is named here because a confidently direct target-domain canonical paper has not been established.

### F3 — Topic Detection and Tracking / story-link / first-story detection — TRANSFER

**Task.** Track events/topics in a news stream and decide whether an incoming story belongs to an existing event or is the first story of a new event.

**Why it matters.** The operational decision closely resembles CONTINUE versus NEW and provides mature online evaluation methodology.

**Limitation.** TDT's “event/topic” can denote a broader story cluster than the concrete-work-matter identity required by msgloom.

**Known seed paper**

- *A Study of Retrospective and On-Line Event Detection* — Yang, Pierce, and Carbonell (1998).

### F4 — Online, incremental, and evolving clustering — TRANSFER

**Task.** Sequentially attach observations to existing clusters, create new clusters, and sometimes merge, split, age, or restructure clusters.

**Why it matters.** Supplies mechanisms for incremental operation, bounded history, late evidence, and cluster revision.

**Limitation.** A cluster can be a similarity construct rather than an identity construct.

**Known seed papers**

- *Clustering Data Streams* — Guha et al. (2000).
- *A Framework for Clustering Evolving Data Streams* — Aggarwal et al. (2003).

### F5 — Entity resolution, record linkage, and incremental identity matching — TRANSFER

**Task.** Infer whether incomplete or heterogeneous records represent the same underlying entity.

**Why it matters.** This is the strongest classical family for combining multiple uncertain pieces of identity evidence and explicitly trading false links against missed links.

**Limitation.** Classical record linkage normally assumes persistent entities and equivalence relations. A work matter can evolve, split conceptually, contain subevents, or acquire new state.

**Foundational seed paper**

- *A Theory for Record Linkage* — Fellegi and Sunter (1969).

### F6 — Partial event identity, subevents, hierarchy, granularity, and event evolution — DIRECT

**Task.** Represent relationships weaker or more structured than strict identity: part-of, subevent, overlap, hierarchical membership, different granularities, or stages of an evolving event.

**Why it matters.** This family is the main academic route for gap-5. It can prevent a false binary assumption that every related pair must be either exactly SAME or completely DIFFERENT.

**Known seed paper/dataset**

- *MAVEN-ERE: A Unified Large-scale Dataset for Event Coreference, Temporal, Causal, and Subevent Relation Extraction*.

### F7 — Business-process event correlation and case-notion discovery — TRANSFER

**Task.** Determine which process instance or case an observed business event belongs to when an explicit case identifier is missing or unreliable.

**Why it matters.** This is a high-value terminology addition. It concerns concrete business-event membership and often combines object attributes, actors, time, control-flow constraints, and process state. That is substantially closer to msgloom's evidence problem than generic clustering.

**Limitation.** Structured event logs differ substantially from natural-language email/chat, and process-mining papers may assume stronger schemas.

**Known seed paper**

- *Correlation Miner: Mining Business Process Models and Event Correlations Without Case Identifiers*.

### F8 — Object-centric and artifact-centric process mining — TRANSFER

**Task.** Model an event as relating to multiple business objects instead of forcing every event into a single flat case trace.

**Why it matters.** msgloom explicitly allows one message to continue several matters through different spans. Object-centric models are useful because they reject a single compulsory case identity and expose convergence/divergence structures.

**Limitation.** Most object-centric work assumes object identity has already been established. It therefore informs representation more strongly than text-based identity inference.

**Known seed paper**

- *Object-Centric Process Mining: Dealing with Divergence and Convergence in Event Data*.

### F9 — Cross-channel activity linking and task-based personal information management — DIRECT

**Task.** Associate email, documents, application artifacts, and interactions with persistent user activities/tasks across applications and time.

**Why it matters.** This is a potential bridge from email-thread research to persistent work activities.

**Admission requirement.** Generic productivity support or task extraction is insufficient; useful papers must actually associate artifacts with continuing activities.

**Known seed paper**

- *TaskTracer: A Desktop Environment to Support Multi-Tasking Knowledge Workers*.

### F10 — Selective prediction, reject option, calibration, and drift — TRANSFER

**Task.** Permit abstention, calibrate confidence, evaluate risk versus coverage, and analyze degradation under shift or concept drift.

**Why it matters.** This supplies formal support for UNCERTAIN and for treating false merges as a controlled risk instead of forcing every candidate into either CONTINUE or NEW.

**Limitation.** It cannot specify msgloom's business loss function. That remains an engineering/product decision.

**Known seed papers**

- *On the Foundations of Noise-free Selective Classification* — El-Yaniv and Wiener (2010).
- *Selective Classification for Deep Neural Networks* — Geifman and El-Yaniv (2017).
- *On Calibration of Modern Neural Networks* — Guo et al. (2017).
- *Can You Trust Your Model's Uncertainty? Evaluating Predictive Uncertainty Under Dataset Shift* — Ovadia et al. (2019).
- *A Survey on Concept Drift Adaptation* — Gama et al. (2014).

### F11 — Retrieval-augmented and global-context event coreference — DIRECT

**Task.** Make event-identity decisions using evidence beyond the local mention pair: document context, cluster context, corpus-level evidence, candidate retrieval, or retrieved external/history context.

**Why it matters.** This is the academic family most directly relevant to Phase 2 evidence seeking and gap-6.

**Admission requirement.** Retrieval must be evaluated as evidence for identity/coreference, not merely generic retrieval-augmented generation.

## Query families

### F1 — DIRECT: cross-document event coreference

- `"cross-document event coreference" identity evidence`
- `"cross-document event coreference" same event criteria`
- `"event coreference resolution" cross-document identity clustering`
- `"same event" cross-document coreference temporal participants arguments`
- `"cross-document event coreference" temporal participant location argument compatibility`
- `"event identity" NLP cross-document coreference`
- `"event coreference" cross-document false positive false negative identity`

The objective is not another broad CDCR survey. Prioritize papers that describe **which combinations of evidence cause two mentions to be considered the same or different event**.

### F2 — DIRECT: enterprise cross-thread continuity

- `(email OR "enterprise chat" OR "workplace chat" OR "Microsoft Teams" OR Slack) AND ("work item" OR "work matter" OR task OR case OR activity) AND (identity OR linking OR continuity OR tracking) AND (cross-thread OR "cross conversation" OR longitudinal)`
- `(enterprise OR workplace OR organizational) AND email AND ("task identity" OR "activity identity" OR "case identity" OR "work item identity")`
- `(email OR "Microsoft Teams" OR Slack) AND ("cross-thread" OR "cross-conversation" OR "cross-channel") AND (linking OR continuity OR tracking) AND (task OR activity OR case OR project)`
- `"business email" AND ("cross-thread" OR "cross conversation") AND (task OR activity OR case) AND (linking OR tracking OR identity)`
- `("enterprise communication" OR "workplace communication") AND ("same task" OR "same activity" OR "same case" OR "same work item")`
- `(email AND chat) AND ("cross-channel" OR "cross-source") AND (task OR activity OR case) AND (linking OR correlation)`
- `(Outlook OR "Microsoft Teams") AND (task OR case OR activity) AND (tracking OR linking OR continuity) AND message`

This is the **highest-value gap-closure family**. Strict admission is required: merely using enterprise email is not sufficient.

### F3 — TRANSFER: TDT and new-event detection

- `"topic detection and tracking" "new event detection"`
- `"story link detection" event tracking`
- `"first story detection" event tracking stream`
- `"new event detection" online text stream existing event`
- `"new event detection" false alarm miss cost`
- `"topic tracking" event stream threshold`
- `"new event detection" rejection threshold clustering`

Focus on explicit decisions between an existing event and a new event and on asymmetric error treatment.

### F4 — TRANSFER: online/incremental clustering

- `("online clustering" OR "incremental clustering") AND text AND ("new cluster" OR novelty OR rejection)`
- `("online clustering" OR "incremental clustering") AND (merge OR split OR revision) AND cluster`
- `"incremental clustering" cluster correction merge split`
- `"streaming clustering" "new cluster" concept evolution`
- `"online event clustering" new event detection text`
- `"incremental event clustering" text stream identity`
- `"evolving clustering" cluster lineage merge split`

Prefer systems capable of **new-cluster creation, revision, merge/split, or abstention**, not forced nearest-cluster assignment.

### F5 — TRANSFER: entity resolution and record linkage

- `("entity resolution" OR "record linkage") AND (evidence OR features) AND identity AND uncertainty`
- `("incremental entity resolution" OR "incremental record linkage") AND cluster`
- `"entity resolution" false match false nonmatch threshold`
- `"record linkage" false links missed links decision threshold`
- `"entity resolution" abstention OR rejection OR uncertain match`
- `"collective entity resolution" relational evidence identity`
- `"entity resolution" temporal consistency incremental`

The main value here is evidence combination and the cost of false association, not the assumption that work matters behave exactly like people or database entities.

### F6 — DIRECT: partial/subevent/evolving identity

- `("partial event identity" OR "partial coreference" OR "partial event coreference")`
- `("subevent relation" OR "sub-event relation") AND (coreference OR identity)`
- `("event hierarchy" OR "event partonomy" OR "event mereology") AND coreference`
- `("event evolution" OR "evolving event") AND (identity OR coreference OR subevent)`
- `("event membership" OR "event part-of") AND NLP AND identity`
- `("non-transitive" AND (coreference OR "event identity"))`
- `("event coreference" AND (subevent OR partial OR hierarchy OR overlap))`
- `("same event" AND (granularity OR subevent OR partial identity))`

This family should explicitly test whether the literature distinguishes strict identity from **part-of, overlap, succession, and different granularity**.

### F7 — TRANSFER: process-mining case correlation

- `("event correlation" OR "case correlation") AND "process mining" AND "case identifier"`
- `"event-to-case correlation" process mining`
- `"case notion discovery" process mining`
- `("case identification" OR "process instance identification") AND "process mining"`
- `"event correlation" business process "case id"`
- `"event correlation" workflow process instance`
- `"case correlation" business event temporal attribute`
- `"process mining" missing case identifier event correlation`

This family should receive substantially higher priority than generic clustering because it may contain direct evidence about how **business-event attributes, actors, time, and state constraints** combine to establish case membership.

### F8 — TRANSFER: object-centric/artifact-centric processes

- `"object-centric process mining" event identity object relations`
- `"object-centric event log" multiple objects event`
- `"artifact-centric process mining" event correlation`
- `"object-centric" process mining convergence divergence`
- `("object-centric process mining" OR "artifact-centric process mining") AND (identity OR correlation OR case notion)`
- `"multiple case notions" process mining event`
- `"event-to-object" correlation process mining`

The desired result is not generic process-mining performance. The search should identify models useful for **multi-membership, related-but-separate structures, and avoidance of false transitive merging**.

### F9 — DIRECT: task/activity-based workplace information

- `("activity-based computing" OR "task-based computing") AND email AND activity`
- `("task-based information management" OR "activity-based information management") AND email`
- `(workplace OR enterprise) AND (email OR chat OR document) AND "activity tracking"`
- `(email AND documents) AND "task tracking" knowledge worker`
- `"cross-application" activity tracking knowledge work`
- `(email OR chat) AND "task association" workplace`
- `(email OR "instant messaging") AND "activity-based" workplace`

Require actual cross-artifact association with persistent activities. Generic email task extraction is insufficient.

### F10 — TRANSFER: abstention and non-stationary calibration

- `("selective classification" OR "selective prediction" OR abstention OR "reject option") AND ("distribution shift" OR "concept drift")`
- `("confidence calibration" OR calibrated confidence) AND ("distribution shift" OR nonstationary OR streaming) AND NLP`
- `(abstention OR "reject option") AND clustering AND uncertain assignment`
- `"risk coverage" selective prediction distribution shift`
- `"selective prediction" NLP distribution shift`
- `"confidence calibration" coreference OR clustering`
- `("selective classification" OR abstention) AND streaming AND concept drift`

For gap-7, IID-only calibration work is foundational background, not closure evidence. Prefer explicit distribution-shift, streaming, or concept-drift evaluation.

### F11 — DIRECT: retrieved/global evidence for event coreference

- `"event coreference" retrieval context cross-document`
- `"cross-document event coreference" retrieval`
- `"event coreference" global context cross-document`
- `"event coreference" cluster-level context`
- `"cross-document event coreference" candidate retrieval`
- `"event coreference" external evidence retrieval`
- `"event coreference" global information evidence`

The key question is whether additional retrieved/global evidence changes identity decisions correctly, not whether retrieval improves generic downstream NLP.

## False friends and downgrade rules

Discovery should downgrade or reject the following even when keyword overlap is high:

1. **Semantic similarity without identity labels.** Document embeddings, nearest-neighbor retrieval, or similarity clustering are not evidence of continuity by themselves.
2. **Ordinary topic modeling.** A latent “topic” represented as a word distribution is not a concrete work matter.
3. **Conversation reconstruction.** Reply trees, thread reconstruction, quotation attribution, and conversation disentanglement belong to source/group structure unless they separately infer work-matter identity.
4. **Within-message segmentation.** This is Topic 02's problem unless cross-message identity is also evaluated.
5. **Near-duplicate detection.** Duplicate text is narrower than continuation expressed using new wording and new state.
6. **Knowledge-base entity linking.** Mapping a mention to Wikipedia/Wikidata is not the same as discovering or maintaining a work-matter identity.
7. **Persistent-entity ER without transferable identity methodology.** Customer/person/product matching is useful only when it contributes evidence combination, incremental correction, or false-link control.
8. **Process mining with perfect case IDs already supplied.** It bypasses the identity problem.
9. **Object-centric representations with all object IDs given.** Useful for representation, but not direct evidence that identity can be inferred.
10. **Broad TDT topical membership.** Retain only when the event definition and existing-versus-new decision are useful to concrete identity.
11. **Generic novelty/anomaly detection.** Novelty alone does not decide which existing identity, if any, an item continues.
12. **Forced clustering.** Methods that must attach every observation to a cluster are poor matches for msgloom's UNCERTAIN semantics.
13. **Unsupervised clustering evaluated only by cohesion indices.** Identity ground truth is required for claims about false merging or splitting.
14. **Timeline summarization with pre-existing clusters.** It does not solve identity.
15. **Temporal/causal relation extraction presented as “event linking.”** Related events are not necessarily identical.
16. **Event evolution without relation typing.** A storyline that groups successive developments together does not establish identity.
17. **Email spam/priority/sentiment/response prediction.** Enterprise data does not make these identity studies.
18. **Teams/Slack adoption and social-analysis work.** Platform relevance alone is insufficient.
19. **Thread identity mistaken for Topic identity.** Same conversation is evidence, not the product's identity criterion.
20. **Task extraction without cross-message task identity.** Finding a request or action item in each email does not establish whether they are the same work item.
21. **Activity recognition as class prediction.** Predefined activity labels are not persistent activity-instance identities.
22. **Static event-coreference systems used as online evidence.** If inference sees the complete future corpus, they cannot directly validate incremental operation.
23. **Destructive reclustering.** For msgloom design relevance, corrections that erase prior assignments without lineage are materially weaker.
24. **IID-only calibration offered as gap-7 closure.** Retain as foundation, but it does not establish reliability under workplace drift.
25. **Generic open-set image/sensor work.** Retain only transferable rejection/calibration machinery.
26. **Generic retrieval augmentation.** Retrieval must be evaluated as changing coreference/identity decisions, not merely improving generated text.
27. **Public-domain transfer mistaken for production evidence.** News, Wikipedia, healthcare, knowledge graphs, and generic databases remain TRANSFER for Outlook/Teams claims.
28. **Email corpora without the required labels.** Enron, Avocado, or another email dataset is not direct identity evidence unless it actually annotates cross-thread concrete work-matter continuity.
29. **Single-feature identity shortcuts.** Same subject, customer, project, participant set, or high semantic similarity cannot be treated as ground-truth identity without independent annotation.
30. **One-message/one-cluster assumptions.** Downgrade models unable to represent different spans of one message continuing different existing matters.
31. **Strict equivalence used to justify partial identity.** Transitive coreference does not itself define subevent, overlap, evolution, or related-but-separate semantics.
32. **Synthetic or transfer evidence presented as production accuracy.** It may justify mechanisms and engineering experiments, not representativeness.

## Date policy

**Earliest publication year discovery must include: 1969.**

The reason is not that the direct workplace problem dates to 1969. It is that one of the relevant identity traditions—probabilistic **record linkage**—has a foundational result in Fellegi and Sunter's *A Theory for Record Linkage* (1969), which formalizes evidence-based matching and false-link/non-link decisions.

The more directly relevant textual line begins much later:

- **late 1990s:** Topic Detection and Tracking and online/new-event detection;
- **1999:** cross-document event coreference is already an explicit research task;
- **2000s onward:** streaming/incremental clustering, enterprise task/activity systems, and increasingly explicit business-process event correlation;
- **later work:** modern neural CDCR, object-centric process mining, selective prediction, calibration under shift, and richer subevent/event-relation datasets.

Therefore a blanket recent window such as 2015–2026 would silently remove several foundations needed to interpret modern systems.

The recommended policy is:

- **global hard floor: 1969**;
- search the pre-1998 period mainly for foundational record-linkage/identity theory;
- search **1998 onward comprehensively** for TDT, CDCR, online event tracking, enterprise task/activity work, process-event correlation, and subsequent methods;
- prioritize newer work for production engineering, modern NLP models, non-stationary calibration, and Microsoft Teams/Slack evidence, but do not use recency to exclude the foundational task definitions.

The date range alone must not be interpreted as an instruction to fill the corpus with old record-linkage papers. Admission remains capability-driven and gap-driven.
