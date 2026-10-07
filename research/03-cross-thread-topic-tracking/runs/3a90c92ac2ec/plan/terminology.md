# direct evidence for cross-thread workplace work-matter identity, including cross-document business event coreference, enterprise email/chat continuity, and partial or evolving event identity academic terminology analysis

## Product problem

The target decision is not ordinary topic similarity and not conversation reconstruction. Given a new candidate work-matter span or Group and existing longitudinal identities, msgloom must determine whether the new evidence:

- continues one existing concrete work matter;
- starts a genuinely new work matter;
- remains too ambiguous to attach safely;
- later justifies a merge correction; or
- later justifies a split correction.

The strongest open academic question is what combinations of observable evidence actually establish or refute identity across independent workplace communications. Candidate evidence includes event arguments, participants, customers/projects, referenced artifacts, temporal information, actions and commitments, state compatibility, source/conversation ancestry, and explicit references. The search must distinguish evidence that merely indicates relatedness from evidence that supports strict same-matter identity.

Three distinct evidence levels must remain separate:

1. **Direct identity evidence** — literature explicitly deciding same-event, same-task, same-case, or same-work-matter identity.
2. **Transfer evidence** — methods from record linkage, TDT, online clustering, process mining, or selective prediction that may support msgloom engineering but do not validate workplace identity accuracy.
3. **Production-domain evidence** — evaluation on genuinely comparable enterprise email/chat or cross-channel work communication. News or database benchmarks cannot substitute for this.

A particularly important semantic issue is that related events need not be identical. Subevents, partial overlap, different granularities, revisions, and evolving business situations may invalidate a simple transitive-equivalence interpretation. Search therefore needs terminology for both strict coreference and non-equivalent event relations.

## Seed keyword audit

| Seed | Academic meaning | Fit | Main risk |
| --- | --- | --- | --- |
| cross-document event coreference | Resolve event mentions in different documents that refer to the same real-world event. | STRONG | Usually evaluated on news rather than workplace communication. |
| cross-document event coreference resolution | Computational resolution of cross-document event mentions into same-event clusters. | STRONG | Benchmark event ontologies may not match evolving work matters. |
| event coreference resolution | Resolve multiple textual event mentions as same or different events. | STRONG | Unqualified searches retrieve large volumes of within-document work. |
| event identity | Criteria under which event descriptions denote the same event. | MODERATE | Strong semantic/philosophical ambiguity; may not be computational. |
| same-event detection | Decide whether two mentions, documents, or stories concern the same event. | STRONG | TDT usage may operate at whole-story/topic granularity. |
| event linking | Link an event to another mention, cluster, KB entry, timeline, or canonical record. | MODERATE | Frequently means KB linking rather than same-event resolution. |
| cross-document event linking | Link event information across documents. | MODERATE | Non-standardized; can mean relation extraction or KB linking. |
| cross-document coreference | Resolve cross-document mentions of the same referent. | MODERATE | Entity coreference dominates many results. |
| entity resolution | Resolve noisy mentions or records referring to one real-world entity. | MODERATE | Persistent-entity assumptions are stronger than evolving work-matter identity. |
| entity linking | Map a mention to a canonical KB entity. | WEAK | Usually a different task from longitudinal instance identity. |
| record linkage | Determine which database records describe the same underlying entity. | MODERATE | Primarily static and entity-centric. |
| topic detection and tracking | Detect, link, and track news events/topics over a stream. | MODERATE | A TDT topic is not automatically a concrete work matter. |
| story link detection | Determine whether two news stories belong to the same target event/topic. | MODERATE | Whole-story similarity can be broader than strict identity. |
| new event detection | Decide whether an incoming item represents an event not previously observed. | STRONG | Newness may be defined by content novelty rather than explicit identity rejection. |
| novelty detection | Detect observations or information differing from prior data. | MODERATE | Novel information can occur inside an existing matter. |
| incremental clustering | Update clusters as items arrive. | STRONG | Generic methods often force geometric assignments without identity semantics. |
| online clustering | Sequentially assign observations or create clusters. | STRONG | Often lacks abstention and semantic merge/split correction. |
| streaming clustering | Cluster unbounded streams under resource and adaptation constraints. | MODERATE | Dominated by numeric/sensor-stream literature. |
| cluster linking | Associate clusters across datasets, time slices, or systems. | WEAK | Not a stable task name; very heterogeneous results. |
| cluster maintenance | Maintain changing clusters as data arrive or clusters merge/split. | MODERATE | Frequently about efficiency rather than persistent semantic identity. |
| dynamic clustering | Cluster data whose distributions or memberships change over time. | MODERATE | Dynamic structure is not necessarily longitudinal identity. |
| event evolution | Model how events or event descriptions develop over time. | MODERATE | Often assumes event identity has already been established. |
| event timeline tracking | Follow event developments and organize them temporally. | WEAK | Mostly timeline generation/summarization rather than identity resolution. |
| business email | Domain descriptor for organizational email. | MODERATE | Retrieves classification, spam, security, summarization, and threading. |
| workplace communication | Broad domain covering organizational communication channels. | MODERATE | Most results lack computational work-matter identity labels. |
| enterprise communication | Organizational email/chat/collaboration communication. | MODERATE | Often infrastructure, HCI, governance, or social-network research. |
| work chat | Informal phrase for workplace instant messaging. | WEAK | Poor academic terminological precision. |
| asynchronous conversation | Non-synchronous communication such as email/forums/chat. | WEAK | Strongly attracts conversation disentanglement and threading rather than matter identity. |

### Terms to promote

The search vocabulary should add terms that map more precisely onto the required capabilities:

- event mention coreference;
- same-event relation;
- same-event classification;
- event clustering;
- event cluster assignment;
- cross-document event clustering;
- event argument compatibility;
- temporal compatibility;
- first story detection;
- incremental entity resolution;
- online entity resolution;
- streaming entity resolution;
- case correlation;
- event correlation;
- process instance identification;
- case identification;
- case notion discovery;
- selective classification;
- selective prediction;
- reject option;
- abstention;
- open-set recognition;
- unknown-class detection;
- cross-channel linking;
- cross-source linking;
- work item tracking;
- case tracking;
- process instance;
- subevent relation;
- event granularity;
- quasi-identity.

### Terms to demote

Use these only with stronger qualifiers:

- entity linking;
- cluster linking;
- event timeline tracking;
- work chat;
- asynchronous conversation;
- event identity without coreference/same-event/computational qualifiers;
- novelty detection without new-event/open-set/identity qualifiers;
- dynamic clustering without text/event/identity/incremental-assignment qualifiers.

## Academic task families

### F1 — Cross-document event coreference and same-event identity — DIRECT

This is the closest established NLP task. It explicitly asks whether event mentions across documents denote the same event and normally represents the result as event clusters.

Its value for msgloom is not simply the clustering architecture. The high-value evidence is what a paper finds useful for distinguishing same from different events: participants and other semantic arguments, time, location, event type, lexical information, contextual entities, and compatibility or inconsistency among these attributes.

Known starting papers:

- Bagga and Baldwin (1999), *Cross-document event coreference: Annotations, experiments, and observations*.
- Lee et al. (2012), *Joint Entity and Event Coreference Resolution across Documents*.
- Cybulska and Vossen (2014), *Using a sledgehammer to crack a nut? Lexical diversity and event coreference resolution*.

These papers are direct evidence for the task class, but unless their data are workplace communications they remain non-production evidence for msgloom.

### F2 — Enterprise cross-thread work-matter, task, case, and business-event continuity — DIRECT

This is the most important discovery family for gap closure.

The search should not assume that the literature calls the target a "Topic." Candidate terms include:

- work item;
- task;
- case;
- business event;
- issue;
- process instance;
- matter;
- work activity.

The distinguishing condition is that identity must span independent messages, threads, conversations, documents, or channels.

This family should deliberately include direct searches for email, enterprise communication, workplace communication, enterprise chat, instant messaging, Microsoft Teams, Outlook, cross-thread, cross-conversation, cross-channel, and cross-source.

A negative finding here is meaningful: if tightly controlled searches still find only conversation threading, summarization, or UX work, gap-4 should remain explicitly open rather than being filled with adjacent news evidence.

### F3 — Topic Detection and Tracking, story-link detection, and new-event detection — TRANSFER

TDT provides an old and important analogue of:

- CONTINUE an existing event/story cluster; versus
- create a NEW event cluster.

The highest-value sub-tasks are story-link detection, first-story detection, and online new-event detection.

Known starting paper:

- Allan, Papka, and Lavrenko (1998), *On-line New Event Detection and Tracking*.

TDT must remain TRANSFER evidence because its unit is normally a news story and its notion of topic/event can be broader than a concrete business matter.

### F4 — Incremental, online, and streaming event/text clustering — TRANSFER

This family addresses sequential cluster assignment and creation.

Relevant capabilities are:

- candidate retrieval;
- attach-versus-create decisions;
- bounded historical state;
- delayed correction;
- merge/split maintenance;
- cluster retirement;
- incremental recomputation;
- latency and memory trade-offs.

Generic stream clustering should not be admitted merely because it is online. Discovery should prioritize text/event methods and papers that explicitly permit new clusters or rejection rather than forcing every observation into an existing cluster.

### F5 — Entity resolution, record linkage, and incremental entity resolution — TRANSFER

This family is useful for evidence combination and false-link control.

Record linkage provides explicit models of matching and non-matching evidence across multiple fields. That makes it relevant to questions such as whether agreement on participant, customer, project, artifact, and time should jointly increase identity confidence and whether disagreement should provide negative evidence.

Known foundational paper:

- Fellegi and Sunter (1969), *A Theory for Record Linkage*.

The conceptual limit is important: a customer or person is normally assumed to have persistent transitive identity. A work matter can branch, change granularity, contain subevents, or be only partially related. Therefore record linkage is mechanism-level evidence, not a definition of Topic identity.

### F6 — Partial, evolving, granular, and non-equivalence event relations — DIRECT

This family targets gap-5.

Search should distinguish:

- strict identity/coreference;
- subevent or part-of;
- temporal overlap;
- different granular descriptions;
- related-but-distinct events;
- quasi-identity or near-identity;
- event evolution;
- non-transitive relations.

The objective is not to discover another similarity score. It is to determine whether the literature has explicit semantics for relations that should *not* be collapsed into one equivalence class.

The exact acronym `CDEC-WN` should also be searched because it is already identified in the existing corpus as evidence that event relations can be non-transitive.

### F7 — Business-process case correlation and process-instance identification — TRANSFER

This is a particularly important terminology expansion beyond the original seed list.

Process-mining and workflow research can face a structurally similar question: when an event log does not have a reliable case identifier, which events belong to the same process instance?

Promoted terms include:

- case correlation;
- event correlation;
- process instance identification;
- case identification;
- case notion discovery.

This family is closer to business operations than news corpora, but it normally works with structured event logs whose event types and attributes are much cleaner than free-form email and Teams messages.

### F8 — Selective classification, reject option, open-set recognition, and abstention — TRANSFER

This family provides formal machinery for the UNCERTAIN state.

Known foundational work includes:

- Chow (1970), *On Optimum Recognition Error and Reject Tradeoff*.
- El-Yaniv and Wiener (2010), *On the Foundations of Noise-free Selective Classification*.

This literature can inform:

- when to abstain;
- confidence versus coverage;
- threshold design;
- unknown-class handling;
- cost-sensitive rejection.

It cannot establish which combination of workplace evidence proves identity. That remains a domain decision.

### F9 — Calibration and selective prediction under distribution shift or concept drift — TRANSFER

This family targets gap-7.

The search should require some combination of:

- selective classification or abstention;
- confidence calibration;
- distribution/domain shift;
- non-stationarity;
- concept drift;
- streaming deployment.

The desired result is evidence about when confidence or rejection policies fail as the deployment distribution changes.

Generic calibration work on IID test sets should be downgraded unless it provides a necessary methodological component.

### F10 — Cross-source and cross-channel communication linking — DIRECT

This family targets movement of one concrete matter between channels.

Search should cover combinations such as:

- email to enterprise chat;
- thread to independent thread;
- message to attachment/document;
- email to Teams;
- cross-source referenced artifacts.

The admission requirement is stricter than "these communications are related." A useful paper must resolve or evaluate a concrete task, case, event, or work-item linkage, or provide evidence directly relevant to such a decision.

## Query families

### F1 — DIRECT: cross-document event identity

Run:

- `"cross-document event coreference" identity evidence`
- `"cross-document event coreference resolution" same event`
- `("event coreference" OR "event mention coreference") AND cross-document AND (identity OR "same event")`
- `"cross-document event coreference" AND (participants OR arguments OR entities OR time OR temporal OR location) AND (features OR evidence)`
- `"event coreference" AND ("argument compatibility" OR "temporal compatibility" OR "semantic roles") AND identity`
- `"cross-document event coreference" AND (incompatibility OR contradiction OR negative evidence OR "different event")`
- `"event coreference" AND clustering AND cross-document AND "same event"`

The negative-evidence query is important. Gap-1 is not only about what raises match confidence; it also asks what evidence should refute a continuation.

### F2 — DIRECT: enterprise work-matter continuity

Run:

- `("work item identity" OR "work matter identity" OR "business event coreference") AND (email OR enterprise OR workplace)`
- `("task identity" OR "case identity" OR "work item") AND (email OR "workplace communication" OR "enterprise communication") AND (cross-thread OR cross-conversation OR longitudinal)`
- `(email OR "business email") AND (cross-thread OR "across threads") AND ("task tracking" OR "case tracking" OR "work item" OR continuity)`
- `(enterprise OR workplace) AND (email OR chat OR "instant messaging") AND ("same task" OR "same case" OR "same event" OR "same work item")`
- `("Microsoft Teams" OR "enterprise chat" OR "team chat") AND (cross-conversation OR cross-thread OR longitudinal) AND (task OR case OR event) AND (identity OR tracking OR continuity)`
- `(Outlook OR email) AND ("Microsoft Teams" OR "enterprise chat") AND (cross-source OR cross-channel) AND (task OR case OR "work item" OR "business event")`
- `"business event" AND coreference AND (email OR enterprise OR workplace)`

This is the family that must be inspected most strictly for genuine direct target-domain evidence.

### F3 — TRANSFER: TDT/new-event detection

Run:

- `"topic detection and tracking" AND "new event detection"`
- `"story link detection" AND "same event"`
- `"new event detection" AND tracking AND stream`
- `"first story detection" AND event tracking`
- `("story link detection" OR "new event detection") AND (threshold OR confidence OR rejection OR novelty)`
- `"online new event detection" AND clustering`

### F4 — TRANSFER: incremental identity assignment

Run:

- `("incremental clustering" OR "online clustering") AND text AND ("new cluster" OR assignment)`
- `("incremental event clustering" OR "online event clustering") AND text`
- `"streaming text clustering" AND (novelty OR "new cluster" OR assignment)`
- `("online clustering" OR "incremental clustering") AND (merge OR split OR correction) AND text`
- `"cluster maintenance" AND streaming AND (merge OR split) AND text`
- `("incremental clustering" OR "online clustering") AND abstention AND text`
- `"event cluster assignment" AND online`
- `(retrieval OR candidate generation) AND "cross-document event coreference"`

The last query directly supports gap-6 concerning bounded historical retrieval and candidate generation.

### F5 — TRANSFER: entity resolution and record linkage

Run:

- `("entity resolution" OR "record linkage") AND (match OR nonmatch OR "non-match") AND evidence`
- `"incremental entity resolution"`
- `("online entity resolution" OR "streaming entity resolution")`
- `("entity resolution" OR "record linkage") AND heterogeneous AND sources AND uncertainty`
- `"probabilistic record linkage" AND (agreement OR disagreement OR evidence)`
- `("entity resolution" OR "record linkage") AND (false match OR false merge OR precision) AND threshold`
- `"incremental entity resolution" AND (merge OR split OR correction)`

### F6 — DIRECT: partial and evolving event identity

Run:

- `("partial event identity" OR "event identity") AND (subevent OR granularity OR overlap OR partial)`
- `"event coreference" AND (subevent OR granularity OR "part of" OR overlap)`
- `"event coreference" AND ("quasi-identity" OR "near identity" OR non-identity)`
- `("non-transitive coreference" OR "non-transitive event") AND event`
- `"event relation" AND (subevent OR overlap OR containment) AND coreference`
- `("event evolution" OR "evolving event") AND identity AND coreference`
- `"CDEC-WN" AND event AND coreference`

This family should be evaluated for explicit relation semantics, not merely performance on a coreference benchmark.

### F7 — TRANSFER: workflow/process-instance correlation

Run:

- `("case correlation" OR "event correlation") AND (workflow OR "business process" OR "event log")`
- `("process instance identification" OR "case identification") AND (workflow OR "process mining")`
- `"case notion discovery" AND "process mining"`
- `("case correlation" OR "process instance identification") AND uncertain`
- `("case correlation" OR "event correlation") AND (incremental OR online OR streaming)`
- `("case identification" OR "case correlation") AND (multiple sources OR heterogeneous OR cross-system)`

This family may prove more useful than generic entity resolution because it concerns business-process instances rather than persistent people or products.

### F8 — TRANSFER: abstention and unknown-class handling

Run:

- `("selective classification" OR "selective prediction" OR abstention OR "reject option") AND text`
- `("open set recognition" OR "open-set classification" OR "unknown class detection") AND text`
- `("cluster assignment" AND abstention) OR (clustering AND "reject option")`
- `("selective classification" OR abstention) AND (coreference OR entity resolution OR record linkage)`
- `(abstention OR "reject option") AND ("new event detection" OR event clustering)`
- `("open set" OR "unknown class") AND incremental AND clustering`

### F9 — TRANSFER: calibration under shift

Run:

- `("selective classification" OR abstention OR "selective prediction") AND ("distribution shift" OR nonstationary OR "concept drift")`
- `"confidence calibration" AND ("distribution shift" OR "domain shift" OR "concept drift") AND text`
- `(calibration OR "selective prediction") AND (coreference OR clustering OR "entity resolution") AND shift`
- `("confidence calibration" OR abstention) AND streaming AND text`
- `("selective classification" OR "reject option") AND nonstationary`
- `"calibration under distribution shift" AND NLP`

### F10 — DIRECT: cross-source enterprise communication linking

Run:

- `("cross-channel" OR "cross-source") AND (email OR chat OR "workplace communication") AND (linking OR continuity OR identity)`
- `(email AND chat) AND ("cross-source linking" OR "cross-channel linking" OR "conversation linking")`
- `("enterprise communication" OR "workplace communication") AND (cross-channel OR cross-source) AND (task OR case OR event) AND linking`
- `(email OR "enterprise chat") AND attachment AND ("same task" OR "same case" OR "same event" OR continuity)`
- `(email OR chat) AND (artifact OR attachment OR document) AND reference AND (task OR case OR event) AND identity`
- `"cross-channel conversation linking" AND enterprise`

## False friends and downgrade rules

Discovery should not return a paper as positive evidence merely because its abstract contains the same words. Apply the following downgrade rules.

1. **Latent topics are not Topics.** Ordinary topic modeling, latent-topic discovery, broad subject classification, and generic semantic clustering do not establish concrete work-matter identity.

2. **Similarity is not identity.** Document, sentence, or embedding similarity without independently annotated same-instance labels is not enough.

3. **Thread reconstruction is not cross-thread identity.** Email threading, reply prediction, conversation disentanglement, and thread segmentation belong primarily to source/conversation structure unless they separately evaluate cross-thread work-item identity.

4. **Shared metadata is not sufficient proof.** Matching subject lines, participants, project names, customers, or vocabulary without an independent identity target should be downgraded.

5. **Within-document coreference is not automatically cross-document evidence.** Retain only when the paper contributes explicit identity semantics or evidence mechanisms relevant across documents.

6. **Entity coreference is not event/work-matter identity.** Person, organization, location, and pronoun coreference may be TRANSFER evidence only.

7. **Entity linking is usually a different task.** Wikipedia/KB linking is not same-instance resolution among incoming work matters.

8. **Event-to-KB linking is not event coreference.** An event-linking result should be admitted only if its target is same-event or same-instance assignment.

9. **Duplicate detection is too narrow.** A continuation can contain entirely new information; a work matter need not be a duplicate or near duplicate.

10. **Timeline construction usually presupposes identity.** Timeline summarization and storyline extraction should be excluded if event clusters are given.

11. **Event extraction does not resolve identity.** Trigger, argument, and event-type extraction are useful evidence producers but do not close Topic-identity gaps by themselves.

12. **Novel information is not a new matter.** Novelty/anomaly detection should be downgraded unless it operationalizes rejection of all existing event/cluster identities.

13. **TDT must involve link/new-event decisions.** Broad news topic classification is insufficient.

14. **Generic streaming clustering is not enough.** Sensor, graph, image, and numeric-stream papers should be excluded unless a specific mechanism such as new-cluster creation, abstention, correction, or identity persistence is transferable.

15. **Forced clustering is structurally wrong for msgloom.** Methods that force every incoming item into an existing cluster and cannot create a new cluster or abstain should not be returned as candidate identity solutions.

16. **Generic clustering metrics are insufficient.** Purity, NMI, silhouette, or other aggregate cluster scores do not directly expose false merges and false splits unless identity errors can be reconstructed.

17. **Static record deduplication is only secondary evidence.** Record linkage remains useful when it contributes evidence combination, heterogeneous-source matching, uncertainty, incremental operation, or false-match control.

18. **Known case IDs do not test case correlation.** Process-mining papers that receive reliable case IDs as input do not address work-matter identity.

19. **Process prediction is not process-instance identification.** Prediction, discovery, and conformance checking should be downgraded unless event-to-case assignment itself is uncertain.

20. **Workplace domain words alone are not enough.** Email/Teams studies of sentiment, summarization, security, productivity, social networks, adoption, or communication behavior do not close the target gaps.

21. **Task-oriented UX is not automatic identity resolution.** Email task-management systems are relevant background only unless they evaluate automatic cross-message task identity.

22. **Cross-channel user identity is not cross-channel work identity.** Account linkage and social identity resolution are false positives.

23. **Broad topic labels are not concrete matters.** A benchmark whose `topic` is a category such as politics, finance, or sport does not test the target capability.

24. **Related-to is not same-as.** Same project, same customer, causally related, temporally adjacent, part-of, and related event relations must not be silently converted to identity.

25. **Subevent and partial-event research must preserve relation distinctions.** Papers that collapse overlap, part-of, and strict coreference into one positive class cannot resolve gap-5.

26. **IID calibration is insufficient for gap-7.** Generic confidence calibration should be downgraded unless it addresses selective prediction, abstention, domain/distribution shift, concept drift, or a relation/identity setting.

27. **Transfer-domain evidence cannot establish production accuracy.** News, Wikipedia, public-health linkage, knowledge graphs, database linkage, process logs, and synthetic data can justify mechanisms and experiments, but they cannot establish Outlook/Teams production representativeness.

28. **Direct production claims require comparable data and labels.** A paper should count as direct production-domain evidence only if its data are genuinely comparable enterprise communications and its target is longitudinal task/case/event/work-matter identity rather than thread membership or semantic similarity.

## Date policy

**Earliest publication year to include: 1969.**

A blanket modern recency cutoff would remove foundational work from several deliberately included task families.

The reason for going back to 1969 is not that the target workplace problem was already studied then. It is that the terminology plan explicitly uses record linkage as a TRANSFER family, and Fellegi and Sunter's 1969 *A Theory for Record Linkage* is foundational for probabilistic match/non-match evidence combination.

The reject-option family also has foundational work from 1970, including Chow's *On Optimum Recognition Error and Reject Tradeoff*.

The text-stream identity line becomes directly relevant in the late 1990s:

- Topic Detection and Tracking/new-event work is already established by 1998, including Allan, Papka, and Lavrenko's *On-line New Event Detection and Tracking*.
- Cross-document event coreference appears by 1999, including Bagga and Baldwin's *Cross-document event coreference: Annotations, experiments, and observations*.

Accordingly, discovery should support literature from **1969 onward**, but it should not perform an indiscriminate half-century search for every query. The sensible policy is:

- search pre-1998 literature narrowly for named foundational TRANSFER families such as record linkage and reject-option classification;
- include late-1990s foundational TDT and cross-document event-identity work;
- emphasize later literature for cross-document event coreference, enterprise communication, incremental text clustering, partial-event semantics, process-instance correlation, open-set/selective prediction, and calibration under shift;
- do not allow a recent-year filter to silently exclude the foundational papers that define the older task families.

This policy preserves the intellectual lineage needed for the gap analysis without turning the discovery round into an unfocused historical survey.
