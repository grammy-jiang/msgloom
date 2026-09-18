# Direct enterprise email/chat studies of longitudinal cross-thread conversation or work-item linking, especially evidence for concrete business-event identity and for partial, evolving, subevent, or non-transitive continuity relations in organizational workflows. academic terminology analysis

## Product problem

The target is not ordinary conversation threading, document similarity, topic modeling, or message classification. The required decision is longitudinal identity of a **concrete work matter** across independent evidence units: messages, conversation groups, attachments, email threads, enterprise-chat conversations, and eventually channels.

For a new candidate matter, the system must distinguish:

- continuation of an existing work matter;
- a genuinely new work matter;
- an uncertain relation that should remain separate;
- later merge correction;
- later split correction.

The terminology search therefore needs two layers.

First, it must look for **DIRECT** literature in organizational communication and workflow research where the object being linked is itself a task, case, issue, business process instance, or other concrete work item. The most promising terminology expansion beyond the original seeds is not another variant of “topic”; it is **event correlation, case correlation, case identification, case-notion discovery, process-instance identification, and event-to-case assignment** from process mining.

Second, it must use **TRANSFER** literatures for mechanisms and evaluation: cross-document event coreference for identity evidence; TDT and first-story detection for NEW-versus-existing assignment; record linkage and entity resolution for evidence combination and uncertain matching; dynamic clustering for incremental revision; object-centric process mining for multi-object and non-equivalence relations; selective prediction for abstention; and retrieval-oriented coreference for Phase-2 evidence seeking.

Direct and transfer evidence must remain explicitly separated. News-domain event coreference can justify an evidence feature or experiment. It cannot establish production accuracy for Outlook email or Microsoft Teams.

## Seed keyword audit

| Seed | Academic meaning | Fit | Main risk |
| --- | --- | --- | --- |
| cross-document event coreference | Whether event mentions in different documents denote the same underlying event, normally followed by event clustering. | STRONG | Most evidence is from news or other non-enterprise domains, and benchmark events may be more atomic than evolving work matters. |
| cross-document event coreference resolution | Resolution of same-event relations across documents. | STRONG | Strong identity terminology but normally lacks enterprise-workflow semantics, attachment relations, or evolving case state. |
| event coreference resolution | Resolution of multiple mentions of the same event, within or across documents. | MODERATE | Unqualified searches are dominated by within-document work. |
| event identity | Semantic criteria for deciding when two event descriptions denote the same event. | STRONG | Also retrieves philosophy, formal semantics, and ontology work without an empirical linking task. |
| same-event detection | Pairwise classification that two event descriptions concern the same event. | STRONG | Phrase is less standardized and may retrieve duplicate-news or semantic-similarity work. |
| event linking | Overloaded: mention-to-mention, event-to-KB, event-graph, temporal, causal, or related-event linking. | WEAK | “Linking” frequently does not mean identity. |
| cross-document event linking | Connecting events across documents, possibly by identity, relation, or timeline. | MODERATE | No reliable guarantee that the relation is coreference. |
| cross-document coreference | Cross-document reference resolution, especially entities and sometimes events. | MODERATE | Entity-coreference results can swamp event-identity work. |
| entity resolution | Grouping records or observations that denote the same underlying entity. | MODERATE | Strong identity methodology, but persistent entities differ from evolving work matters. |
| entity linking | Mapping a mention to a canonical KB entity. | REJECT | Solves canonical knowledge-base assignment rather than cross-message work-matter continuity. |
| record linkage | Statistical matching of records referring to the same real-world entity, often with match/non-match/uncertain decisions. | MODERATE | Useful identity theory but normally static records rather than evolving event structures. |
| topic detection and tracking | TDT tasks for detecting, linking, and tracking news stories/events over time. | MODERATE | “Topic” frequently means a news-story cluster and can be broader than strict identity. |
| story link detection | TDT decision whether two stories concern the same target topic/event. | MODERATE | Positive labels may capture topical relatedness rather than strict same-event identity. |
| new event detection | Determine whether an incoming story introduces an unseen event instead of belonging to an existing one. | STRONG | Excellent NEW-versus-existing analogue but often lacks abstention and later correction. |
| novelty detection | Detect observations or information unlike previous data or known classes. | WEAK | Novel content is not equivalent to a new work matter. |
| incremental clustering | Update clustering as observations arrive. | MODERATE | Many algorithms force assignments and optimize cohesion rather than semantic identity. |
| online clustering | Sequential cluster assignment using information available at arrival time. | MODERATE | Captures operational setting but not the work-matter identity relation itself. |
| streaming clustering | Continuous/high-volume clustering with bounded-state representations. | MODERATE | Literature emphasizes scale and drift more often than false merges or identity semantics. |
| cluster linking | Associating clusters across time, datasets, or views. | WEAK | Not a stable task name; does not imply same-event identity. |
| cluster maintenance | Maintaining clusters through creation, retirement, merging, splitting, or prototype updates. | MODERATE | Mechanically relevant but usually lacks stable semantic identity and immutable history. |
| dynamic clustering | Clusters evolve through drift, creation, disappearance, merge, or split. | MODERATE | Broad term; often concerns feature-distribution evolution rather than identity correction. |
| event evolution | Modeling changes in events, event clusters, or storylines over time. | MODERATE | Evolution can connect related but distinct events rather than one continuing identity. |
| event timeline tracking | Building and updating chronological event timelines. | MODERATE | Timeline membership does not imply coreference. |
| business email | Domain descriptor for organizational email. | MODERATE | Alone retrieves classification, summarization, spam, speech acts, response prediction, and network analysis. |
| workplace communication | Broad organizational/HCI/CSCW communication domain. | MODERATE | Mostly not an identity-resolution task. |
| enterprise communication | Organizational communication through enterprise channels. | MODERATE | Useful domain filter but retrieves adoption, systems, security, and network studies. |
| work chat | Informal expression for workplace instant messaging. | WEAK | Poor academic indexing consistency and high consumer-chat noise. |
| asynchronous conversation | Communication whose turns occur at different times. | WEAK | Describes interaction timing rather than business-matter identity. |

The most important promotions are:

- **event correlation**
- **case correlation**
- **case identification**
- **case notion discovery**
- **process instance identification**
- **event-to-case correlation / assignment**
- **uncorrelated event logs**
- **partial event identity**
- **quasi-identity**
- **subevent relation**
- **event membership / overlap**
- **object-centric process mining**
- **artifact-centric process mining**
- **first story detection**
- **incremental entity resolution**
- **clerical review**
- **selective classification / selective prediction**
- **reject option / abstention**
- **candidate retrieval / candidate generation**

The terms that should be demoted as primary search terms are **entity linking**, generic **event linking**, **cluster linking**, generic **novelty detection**, **work chat**, and **asynchronous conversation**.

## Academic task families

### F1 — Enterprise cross-thread and cross-channel work-item identity — DIRECT

This is the closest formulation of the actual msgloom problem: determine whether independently occurring emails, chat messages, conversations, attachments, or channels concern the same concrete task, issue, case, or business matter.

This family must be searched aggressively even if the literature is sparse. Only evidence from this family, or similarly direct enterprise studies, can substantially close the Outlook/Teams production-domain gap.

No seed paper is asserted here because the point of round 4 is specifically to determine whether sufficiently direct literature exists.

### F2 — Process-mining event correlation and case identification — DIRECT

Process-mining research contains a terminology family that is more precise than generic “work-item identity”:

- event correlation;
- case correlation;
- case identification;
- case-notion discovery;
- process-instance identification;
- event-to-case assignment;
- correlation of uncorrelated event logs.

The central problem is determining which business events belong to the same process instance or case.

This is directly relevant to gap-1 because candidate evidence can include timestamps, resources, business objects, attributes, process state, and structural constraints. It is also relevant to gap-5 because workflow instances can exhibit branching, shared objects, and other relations that do not reduce cleanly to textual similarity.

### F3 — Cross-document event coreference and same-event identity — TRANSFER

This is the strongest established academic family for strict event identity across independent documents.

Known seeds include:

- Bagga and Baldwin (1999), *Cross-Document Event Coreference: Annotations, Experiments, and Observations*.
- Barhom et al. (2019), *Revisiting Joint Modeling of Cross-document Entity and Event Coreference Resolution*.

This literature is especially valuable for examining combinations of:

- event arguments;
- participants;
- time;
- location;
- lexical/event-type information;
- document context;
- global cluster context.

Its limitation is domain transfer. News-event identity is not automatically work-matter identity.

### F4 — Partial, quasi-, subevent, membership, and non-identity relations — TRANSFER

This is the key family for gap-5.

A strong seed is:

- Hovy et al. (2013), *Events are Not Simple: Identity, Non-Identity, and Quasi-Identity*.

Discovery should actively seek literature that rejects a single binary equivalence relation and instead distinguishes relations such as:

- strict identity;
- partial identity;
- quasi-identity;
- subevent;
- membership;
- overlap;
- evolving versions;
- related-but-separate events.

The important product question is not merely whether these relations exist. It is whether their semantics can inform a workplace distinction among CONTINUE, RELATED-BUT-SEPARATE, NEW, MERGE, SPLIT, or UNCERTAIN.

### F5 — Topic Detection and Tracking, story-link, and new-event detection — TRANSFER

Known foundational seeds include:

- Allan, Papka, and Lavrenko (1998), *On-Line New Event Detection and Tracking*.
- Yang, Pierce, and Carbonell (1998), *A Study of Retrospective and On-Line Event Detection*.

This family contributes:

- online NEW-versus-existing decisions;
- first-story detection;
- story linking;
- threshold selection;
- false-alarm versus miss evaluation;
- streaming operation.

The semantic warning is substantial: a TDT topic or story cluster can represent related reporting about an event rather than the strict identity relation msgloom needs.

### F6 — Incremental, online, and streaming clustering with cluster evolution — TRANSFER

This family covers:

- attaching new observations to clusters;
- creating new clusters;
- bounded-memory operation;
- evolving cluster representations;
- cluster merging;
- cluster splitting;
- cluster retirement.

A known seed is:

- Petrović, Osborne, and Lavrenko (2010), *Streaming First Story Detection with Application to Twitter*.

This is useful for mechanics but cannot define work-matter identity by itself.

### F7 — Entity resolution, record linkage, and incremental identity resolution — TRANSFER

The classical seed is:

- Fellegi and Sunter (1969), *A Theory for Record Linkage*.

The important transferable concepts include:

- explicit match versus non-match evidence;
- uncertain decisions;
- evidence combinations;
- asymmetric costs;
- thresholds;
- clerical review;
- incremental identity resolution;
- revision of earlier assignments.

This family is especially relevant to gap-1, gap-2, and gap-3, but it does not determine msgloom's own loss function or Topic-history semantics.

### F8 — Object-centric and artifact-centric process representations — TRANSFER

A known seed is:

- van der Aalst (2019), *Object-Centric Process Mining: Dealing with Divergence and Convergence in Event Data*.

This family is important because ordinary case-centric representations impose a single case relation, whereas real work can involve:

- one event affecting several business objects;
- one message continuing several matters through different spans;
- convergence of several object histories;
- divergence into multiple branches;
- subobjects with distinct life cycles.

This makes it especially useful for gap-5 and for avoiding an incorrect assumption that all continuity relations must be transitive equivalence classes.

### F9 — Enterprise email/chat longitudinal task, case, and issue tracking — DIRECT

This family should only admit studies that track a **work object beyond the source conversation itself**.

Relevant targets include:

- task tracking across emails;
- case tracking across messages;
- issue tracking across channels;
- activity/work-item continuity;
- longitudinal linkage of enterprise messages.

Conversation disentanglement, email threading, and reply reconstruction are neighboring tasks but do not satisfy this family unless an independent work-item relation is evaluated.

The search should explicitly include Outlook, Microsoft Teams, enterprise chat, business email, organizational communication, and cross-channel communication.

### F10 — Selective prediction, abstention, and calibration under distribution shift — TRANSFER

Known seeds include:

- Guo et al. (2017), *On Calibration of Modern Neural Networks*.
- Geifman and El-Yaniv (2017), *Selective Classification for Deep Neural Networks*.
- Gibbs and Candès (2021), *Adaptive Conformal Inference Under Distribution Shift*.

This family supports gap-7 through:

- abstention;
- reject options;
- selective risk;
- risk-coverage curves;
- recalibration;
- non-stationarity;
- adaptive conformal methods.

It cannot determine msgloom's application-specific cost of a false merge or define the correct CONTINUE/NEW/UNCERTAIN threshold. Those remain engineering questions.

### F11 — Retrieval and global-context evidence for cross-document identity — TRANSFER

This family separates two questions:

1. What evidence should be retrieved?
2. Given that evidence, does the identity decision change correctly?

Search should cover:

- candidate generation;
- document retrieval;
- mention retrieval;
- cluster retrieval;
- blocking;
- global context;
- historical context.

This directly informs Phase-2 experiments for bounded historical retrieval, latency, stopping rules, and whether additional context reduces actual identity errors rather than merely increasing recall.

### F12 — Identity revision, cluster merge/split, and provenance-preserving correction — TRANSFER

This family should seek work on:

- incremental entity-resolution correction;
- cluster merge and split;
- cluster evolution;
- stable or persistent identifiers;
- provenance and lineage;
- human review or adjudication;
- revision of previous cluster assignments.

It can inform implementation strategies for correction, but it cannot define msgloom's stable Topic IDs, supersession links, immutable evidence lineage, or versioned assessment semantics. Those remain project-level engineering decisions.

## Query families

### F1 — DIRECT: enterprise work-item identity

- `("work item identity" OR "work-item identity" OR "work matter" OR "business matter" OR "case identity") AND (email OR "enterprise chat" OR "workplace communication") AND (longitudinal OR "cross-thread" OR "cross-conversation" OR "cross-channel")`
- `("task continuity" OR "case continuity" OR "issue continuity" OR "work item linking") AND (email OR messaging OR "enterprise communication") AND (thread OR conversation OR channel)`
- `("cross-channel" OR "cross-source") AND (email AND chat) AND ("task tracking" OR "case tracking" OR "work item" OR "business process")`
- `("same case" OR "same task" OR "same issue" OR "same work item") AND (email OR "workplace chat" OR "enterprise messaging") AND (linking OR classification OR correlation)`
- `("Outlook" OR "business email" OR "enterprise email") AND ("work item" OR case OR task OR issue) AND (linking OR continuity OR correlation) AND (longitudinal OR "cross-thread")`

### F2 — DIRECT: process-mining case correlation

- `("event correlation" OR "case correlation" OR "case identification" OR "case notion discovery") AND ("process mining" OR workflow) AND (enterprise OR business)`
- `("process instance identification" OR "process instance discovery" OR "event-to-case" OR "case assignment") AND ("process mining" OR "business process")`
- `("uncorrelated event log" OR "uncorrelated events") AND (correlation OR "case identification" OR "case notion") AND "process mining"`
- `("event correlation" OR "case correlation") AND (email OR communication OR message OR document) AND (workflow OR "business process")`
- `("case notion" OR "case identification") AND (temporal OR resource OR object OR attribute OR state) AND "process mining"`

### F3 — TRANSFER: cross-document event identity

- `"cross-document event coreference" AND (identity OR "same event" OR clustering)`
- `"cross-document event coreference resolution" AND (time OR temporal OR participant OR argument OR location)`
- `("event coreference" AND "cross-document") AND (identity OR nonidentity OR "identity criteria")`
- `("same-event" OR "same event") AND (detection OR classification) AND ("cross-document" OR documents) AND event`
- `"cross-document event coreference" AND (arguments OR participants OR temporal OR location OR context) AND (features OR evidence)`

### F4 — TRANSFER: partial and non-transitive event relations

- `("event identity" OR "event coreference") AND ("partial identity" OR "partial coreference" OR "quasi-identity")`
- `("event identity" OR "event coreference") AND (subevent OR "sub-event" OR membership OR overlap)`
- `("non-transitive" OR nontransitive) AND ("event coreference" OR "event identity" OR "event relation")`
- `("event relation" OR "event relations") AND (subevent OR membership OR overlap) AND (identity OR coreference)`
- `("event evolution" OR "evolving event") AND (identity OR coreference OR continuation) AND (subevent OR state OR relation)`

### F5 — TRANSFER: TDT and new-event detection

- `("topic detection and tracking" OR TDT) AND ("new event detection" OR "story link detection")`
- `("online new event detection" OR "first story detection") AND (threshold OR similarity OR clustering)`
- `"story link detection" AND (same OR link OR topic OR event) AND evaluation`
- `("new event detection" OR "first story detection") AND ("new cluster" OR "cluster assignment" OR threshold) AND streaming`
- `("topic tracking" AND "new event") AND (false alarm OR miss OR detection cost)`

### F6 — TRANSFER: online and dynamic clustering

- `("incremental clustering" OR "online clustering") AND text AND ("new cluster" OR "cluster assignment")`
- `("streaming clustering" OR "dynamic clustering") AND text AND (merge OR split OR evolution)`
- `"incremental clustering" AND ("cluster evolution" OR "cluster creation" OR "cluster deletion")`
- `("online clustering" OR "streaming clustering") AND (abstention OR reject OR uncertainty OR "unknown class")`
- `("dynamic clustering" OR "evolving clusters") AND (merge OR split) AND (stream OR text)`

### F7 — TRANSFER: record linkage and entity resolution

- `("incremental entity resolution" OR "online entity resolution") AND (merge OR split OR revision OR history)`
- `("record linkage" OR "entity resolution") AND (match OR nonmatch OR "non-match") AND (uncertain OR threshold OR cost)`
- `("entity resolution" OR "record linkage") AND ("false match" OR "false merge" OR "false non-match" OR "false split")`
- `("entity resolution" OR "record linkage") AND ("clerical review" OR abstention OR uncertain) AND decision`
- `("incremental entity resolution" OR "dynamic entity resolution") AND (provenance OR lineage OR cluster)`

### F8 — TRANSFER: multi-object workflow relations

- `"object-centric process mining" AND (convergence OR divergence OR "multiple objects")`
- `("object-centric" OR "artifact-centric") AND "process mining" AND (event OR case OR relation)`
- `("multi-object" OR "multiple objects") AND event AND ("process mining" OR workflow) AND relation`
- `("case notion" AND "object-centric") AND (event OR process)`
- `("artifact-centric process" OR "artifact-centric process mining") AND (correlation OR interaction OR lifecycle)`

### F9 — DIRECT: enterprise email/chat tracking

- `(enterprise OR workplace OR organizational) AND (email OR "Microsoft Teams" OR "enterprise chat" OR "workplace chat") AND ("task tracking" OR "case tracking" OR "issue tracking" OR "work item") AND longitudinal`
- `("business email" OR "enterprise email") AND (task OR case OR issue OR activity) AND ("cross-thread" OR "across threads" OR longitudinal) AND (linking OR tracking)`
- `("Microsoft Teams" OR "enterprise messaging" OR "enterprise chat") AND (task OR case OR issue OR "work item") AND (tracking OR linking OR continuity)`
- `(email AND chat) AND ("cross-channel" OR "cross-source") AND (task OR case OR workflow OR issue) AND (identity OR linking OR correlation)`
- `("organizational communication" OR "workplace communication") AND ("case linking" OR "task linking" OR "work-item linking" OR "issue linking")`

### F10 — TRANSFER: calibration and abstention under drift

- `("selective classification" OR "selective prediction" OR abstention OR "reject option") AND ("distribution shift" OR nonstationary OR "concept drift") AND (text OR NLP)`
- `("confidence calibration" OR calibration) AND ("distribution shift" OR "concept drift") AND (NLP OR text OR streaming)`
- `("adaptive conformal inference" OR "conformal prediction") AND ("distribution shift" OR nonstationary) AND classification`
- `("selective prediction" OR abstention) AND (coreference OR clustering OR "entity resolution")`
- `(calibration OR abstention) AND streaming AND text AND (risk OR coverage OR uncertainty)`

### F11 — TRANSFER: retrieval-based identity evidence

- `("event coreference" OR "cross-document event coreference") AND (retrieval OR "candidate retrieval" OR "document retrieval")`
- `"cross-document event coreference" AND ("global context" OR context) AND retrieval`
- `("event coreference" OR "entity resolution") AND ("candidate generation" OR blocking OR retrieval) AND cross-document`
- `(retrieval AND "event coreference") AND (evidence OR context OR history)`
- `("historical context" OR "additional context") AND (coreference OR "event identity") AND retrieval`

### F12 — TRANSFER: correction, merge/split, and identity history

- `("incremental entity resolution" OR "dynamic clustering") AND ("cluster merge" OR "cluster split" OR "merge split")`
- `("cluster evolution" OR "cluster maintenance") AND (merge OR split) AND (provenance OR lineage OR history)`
- `("entity resolution" OR "record linkage") AND (correction OR revision OR adjudication) AND (cluster OR identity)`
- `("stable identifier" OR "persistent identity") AND (cluster OR "entity resolution") AND incremental`
- `("human-in-the-loop entity resolution" OR "interactive entity resolution") AND (correction OR review OR uncertain)`

## False friends and downgrade rules

Discovery should downgrade or exclude the following even when the abstract contains apparently relevant words:

1. Ordinary topic modeling where “topic” is a latent word distribution rather than a concrete work matter.
2. Conversation disentanglement, reply-thread reconstruction, email threading, or channel reconstruction unless work-item identity is independently annotated and evaluated.
3. Knowledge-base entity linking without incremental same-identity clustering.
4. Document similarity, embedding similarity, nearest-neighbor retrieval, or related-document recommendation without same-event/same-case/same-task gold labels.
5. Within-document-only event coreference unless it supplies an identity criterion or relation model clearly transferable to cross-document decisions.
6. Duplicate or near-duplicate detection as a substitute for evolving work-matter continuity.
7. TDT results whose positive relation is broad topical relatedness and cannot be separated from strict event identity.
8. Novelty scoring that does not perform existing-identity versus new-identity assignment.
9. Clustering that forces every new item into an existing cluster and cannot create a new cluster or abstain.
10. Streaming-clustering work concerned only with memory, speed, or geometric compactness.
11. Process-mining work that assumes the correct case ID is already present. For gaps 1 and 5, prioritize research that must infer or validate case membership.
12. Object-centric process-mining work that assumes perfect object identifiers, except where its relation semantics—multi-object membership, convergence, divergence, or interaction—are themselves the transferable result.
13. Timeline construction where events only need to be related enough to appear on the same timeline.
14. General workplace-communication, CSCW, remote-work, or organizational-behavior studies without a message-to-task/case/work-item relation.
15. Enterprise-email studies limited to spam, summarization, prioritization, speech acts, response prediction, intent classification, or organizational-network analysis.
16. Workplace-chat conversation disentanglement unless it models a business work item independently of the conversation thread.
17. Static entity-resolution work used to support correction claims without incremental revision, uncertain matching, adjudication, or identity-history behavior.
18. Calibration studies restricted to IID test data when evaluating gap-7.
19. Selective-prediction papers used as if they establish msgloom's domain loss function. They only transfer abstention methodology.
20. Retrieval papers that improve retrieval recall but do not evaluate whether the retrieved context changes an identity decision correctly.
21. Any news, social-media, biomedical, bibliographic, customer-deduplication, or other transfer-domain benchmark presented as direct evidence of Outlook or Teams accuracy.
22. Any method that treats subject equality, customer/project equality, participant overlap, lexical similarity, source-thread membership, or a generated label as sufficient proof of work-matter identity.
23. Papers claimed as evidence for partial/non-transitive continuity merely because several event types are present. The work must explicitly represent partial identity, quasi-identity, subevents, membership, overlap, convergence/divergence, or another non-equivalence relation.
24. Algorithmic support for merge/split should not be interpreted as establishing msgloom's correction semantics. Stable Topic IDs, supersession, immutable evidence lineage, and versioned assessments remain project engineering decisions.

## Date policy

**Earliest publication year discovery must reach: 1969.**

The reason is deliberate rather than incidental. Record linkage is one of the retained transfer families, and Fellegi and Sunter's 1969 *A Theory for Record Linkage* is foundational for probabilistic match/non-match evidence, uncertain decisions, and threshold-based identity reasoning.

The more directly analogous streaming-text literature begins much later:

- Topic Detection and Tracking and online new-event detection have foundational work from **1998**.
- Cross-document event-coreference research is present by **1999**.

Therefore a search constrained to recent years would silently omit foundations of three concepts central to this Topic: probabilistic identity decisions, NEW-versus-existing streaming assignment, and cross-document event identity.

This does **not** mean every round-4 query should indiscriminately retrieve literature from 1969 onward. Discovery should prioritize recent enterprise communication, process mining, cross-document event coreference, selective prediction, and streaming work, while permitting targeted foundational sweeps back to 1969. Direct Outlook/Teams evidence should naturally skew recent because Microsoft Teams itself is a modern platform, whereas the transfer families require the longer historical window.
