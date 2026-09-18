# work-item state, event factuality, temporal reasoning, and conflicting revisions in workplace communication: tracking whether an event is planned, confirmed, revoked, completed, or contradicted academic terminology analysis

## Product problem

Topic 06 is not simply an event-extraction or temporal-information-extraction problem. Its object is an **evidence-backed longitudinal assessment of a work item**.

The system must preserve at least four distinct temporal axes or temporal roles:

- utterance/message time;
- event or effective time;
- deadline/constraint time;
- observed collection, ingestion, or version time.

It must also preserve state dimensions that ordinary event extraction frequently collapses:

- asserted versus merely mentioned;
- positive versus negated;
- certain versus uncertain;
- actual versus hypothetical or conditional;
- planned versus completed;
- reported complete versus independently confirmed complete;
- currently accepted versus historically accepted;
- contradicted versus explicitly corrected;
- supplemented versus superseded;
- revoked versus merely no longer discussed;
- resolved versus still disputed.

The closest established NLP literature is **event factuality plus temporal relation extraction**, but neither alone supplies the required longitudinal semantics. Topic 06 therefore spans several direct NLP families and several transfer families from symbolic AI, temporal databases, provenance, and multi-agent reasoning.

A particularly important terminology addition is **bitemporal data / valid time / transaction time**. Temporal-database research explicitly distinguishes when a fact is valid in the represented world from when it became known or recorded in a database. This is not identical to msgloom's semantics, but it closely matches the requirement not to collapse event/effective time into collection/version time.

Likewise, **truth maintenance**, **belief revision**, and **provenance** are not NLP extraction tasks, but they provide concepts for preserving historical evidence while changing the current assessment.

Topic 05's output should be treated as an uncertain utterance-time semantic event, not as authoritative state. If Topic 05 is uncertain about owner, deadline attachment, condition, modality, or negation, Topic 06 must preserve that uncertainty rather than silently resolving it.

## Seed keyword audit

| Seed | Academic meaning | Fit | Main risk |
| --- | --- | --- | --- |
| event factuality prediction | Predict the factual status of an event, usually using polarity, modality, certainty, source perspective, or related dimensions. | STRONG | Usually one-shot factuality prediction rather than longitudinal revision. |
| factuality profiling | Multidimensional representation of factors contributing to factuality; the label is less standardized than event factuality. | STRONG | Exact phrase may have sparse or inconsistent indexing. |
| event modality | Semantic status such as possibility, necessity, intention, obligation, or hypotheticality attached to an event. | STRONG | Modality does not establish later completion, revocation, or supersession. |
| event certainty | Degree of epistemic commitment to an event. | STRONG | Certainty is not the same as actuality or current validity. |
| event veridicality | Whether a linguistic context licenses inference that an embedded event or proposition is true or false. | STRONG | Can retrieve formal semantic work with little operational state tracking. |
| negation detection | Detection of negation cues and normally their scope or target. | STRONG | Cue-only detection can negate the wrong event. |
| speculation detection | Detection of speculative, hypothetical, or uncertain language and sometimes scope. | STRONG | Much evidence comes from biomedical domains. |
| hedging detection | Detection of linguistic weakening or qualification of commitment. | MODERATE | Hedge detection covers only one source of factuality uncertainty. |
| temporal information extraction | Broad extraction of times, events, temporal attributes, and relations. | STRONG | Date extraction without event relations is a major false friend. |
| temporal relation extraction | Identification of relations between events and times or between events. | STRONG | Pairwise relations do not supply the complete state model. |
| event temporal ordering | Relative chronological ordering of events. | STRONG | Correct ordering does not imply that the events actually occurred. |
| temporal relation classification | Classification of candidate event/event or event/time pairs into temporal relation labels. | STRONG | Often pairwise and locally evaluated rather than globally coherent. |
| TimeML | Foundational representation for textual events, temporal expressions, and temporal links. | STRONG | Does not itself define supersession or longitudinal factuality. |
| temporal graphs | Graph representations connecting events/times through temporal relations. | STRONG | Extremely broad outside NLP. |
| temporal constraint reasoning | Reasoning over temporal constraints for closure, consistency, and inferred relations. | STRONG | Scheduling/CSP literature can dominate search results. |
| event status tracking | Heterogeneous label for following changes in an event's status. | MODERATE | Frequently refers to structured workflow or incident status rather than inference from text. |
| state tracking | Generic maintenance of changing state across observations. | WEAK | Too broad to search unqualified. |
| dialogue state tracking | Tracking conversational goals, slots, constraints, and uncertainty across turns. | WEAK | Conversational state is not external event truth; useful only as transfer evidence. |
| event evolution | Study of how events or event representations develop through time. | MODERATE | Often actually means topic/story evolution. |
| event update | Generic phrase for incremental event changes. | WEAK | Strongly polluted by update summarization, stream processing, vision, and databases. |
| timeline extraction | Construction of chronological event timelines from documents. | STRONG | Often assumes selected events are factual and optimizes salience instead of status semantics. |
| contradiction detection | Detection of semantic incompatibility between statements. | STRONG | Contradiction is not supersession and does not identify the currently accepted assessment. |
| natural language inference | Entailment/contradiction/neutral reasoning between textual propositions. | MODERATE | Standard benchmarks discard longitudinal provenance and temporal context. |
| belief revision | Formal modification of a belief state under new information. | STRONG | Symbolic assumptions are much cleaner than extracted communication evidence. |
| truth maintenance systems | Dependency-aware maintenance and retraction/reinstatement of beliefs. | STRONG | Assumes explicit symbolic propositions rather than noisy NLP outputs. |
| assumption-based truth maintenance | Maintenance of alternative belief environments supported by different assumption sets. | STRONG | Reasoning substrate rather than an NLP task. |
| knowledge-base revision | Revision or update of knowledge while maintaining selected logical properties. | STRONG | Some approaches replace information rather than preserving evidence history. |
| temporal knowledge graphs | Time-indexed or validity-indexed graph facts and evolving relations. | MODERATE | Much literature is embedding/link prediction rather than evidence revision. |
| document supersession | One document or record replacing another for some scope or purpose. | MODERATE | Document-level replacement is too coarse for proposition-level changes. |
| version supersession | A newer version becoming current instead of an older version. | MODERATE | Frequently assumes chronological version order is sufficient evidence of replacement. |
| revision tracking | Recording differences and history across document or data revisions. | MODERATE | Syntactic changes do not determine semantic correction or supersession. |
| change detection | Generic detection of differences between observations. | WEAK | Dominated by vision, remote sensing, networks, databases, and software engineering. |
| provenance-aware state | State retained together with sources, derivations, versions, and justifications. | STRONG | Capability is strong but the exact phrase is not a canonical task name. |
| event sourcing | Append-only software architecture in which current state is reconstructed from events. | WEAK | Excellent engineering analogy for history preservation but does not solve NLP semantics. |

Terms that should be actively promoted during discovery include:

- event factuality;
- factuality inference;
- factuality value;
- event polarity;
- epistemic modality;
- modal scope;
- negation scope;
- speculation scope;
- source commitment;
- temporal closure;
- temporal consistency;
- global temporal reasoning;
- timeline construction;
- event state change;
- correction detection;
- retraction detection;
- claim revision;
- semantic supersession;
- iterated belief revision;
- knowledge-base update;
- justification-based truth maintenance;
- data provenance;
- data lineage;
- version provenance;
- valid time;
- transaction time;
- bitemporal data;
- bitemporal database;
- commitment lifecycle;
- social commitments.

Terms that should be demoted as standalone discovery queries are:

- state tracking;
- event update;
- change detection;
- event sourcing;
- dialogue state tracking;
- version supersession;
- revision tracking.

They remain useful only with strong qualifiers.

## Academic task families

### F1 — Event factuality, polarity, modality, certainty, and source commitment
**Role: DIRECT**

This is the primary literature for deciding what status a source assigns to an event at an utterance.

It covers distinctions such as:

- asserted versus non-asserted;
- positive versus negated;
- certain versus uncertain;
- actual versus possible;
- intended or planned versus already realized;
- hypothetical or conditional versus unconditional.

Known seed paper:

- *FactBank: a corpus annotated with event factuality* — Roser Saurí and James Pustejovsky (2009).

The critical limitation is that most factuality work predicts an assessment at one textual point. Topic 06 needs that assessment to become one historical node in a later revision chain, not an immutable truth value.

### F2 — Temporal information extraction and event-time relation classification
**Role: DIRECT**

This family supplies event-time binding and temporal relations.

Known seed papers include:

- *TimeML: Robust Specification of Event and Temporal Expressions in Text* — James Pustejovsky et al. (2003).
- *SemEval-2007 Task 15: TempEval Temporal Relation Identification* — Marc Verhagen et al. (2007).

For msgloom, temporal extraction must distinguish a deadline from an event occurrence time and distinguish both from the message timestamp.

### F3 — Global temporal ordering, temporal graphs, closure, and consistency
**Role: DIRECT**

This family goes beyond independent pair classification and asks whether the resulting temporal structure is globally coherent.

Known seed papers include:

- *Jointly Combining Implicit Constraints Improves Temporal Ordering* — Nathanael Chambers and Dan Jurafsky (2008).
- *A Structured Learning Approach to Temporal Relation Extraction* — Qiang Ning, Zhili Feng, and Dan Roth (2017).

This literature is important because independently inferred relations can contradict one another. Topic 06 should be able to leave order unresolved rather than manufacture a total order.

### F4 — Longitudinal event evolution and timeline construction
**Role: DIRECT**

This family covers multi-document or repeated-observation representations of events and timelines.

Admission must be strict. "Event evolution" often means development of a news story, topic, or cluster rather than evolution of one event's factual or operational state.

Useful papers should represent at least one of:

- repeated evidence about the same event;
- event-state changes;
- cross-document temporal integration;
- longitudinal event timelines;
- changing attributes of an event.

### F5 — Correction, retraction, revision, and supersession detection
**Role: DIRECT**

This is a critical family that is poorly captured by the original seed list.

Topic 06 needs to distinguish:

- correction;
- retraction;
- revocation;
- replacement;
- supplementation;
- narrowing;
- contradiction without resolution;
- genuine semantic supersession.

The essential search principle is that **later does not imply superseding**.

A later message saying "actually, make that Monday" may supersede an earlier Friday deadline for that deadline property. A later message merely discussing another aspect of the same work item does not supersede the earlier statement.

### F6 — Textual contradiction and natural language inference
**Role: DIRECT**

Known seed papers include:

- *Finding Contradictions in Text* — Marie-Catherine de Marneffe, Anna N. Rafferty, and Christopher D. Manning (2008).
- *A large annotated corpus for learning natural language inference* — Samuel R. Bowman et al. (2015).

This literature is useful for detecting conflict, but a contradiction detector must not be promoted into a state-resolution engine.

Given:

- "The deployment completed."
- "The deployment did not complete."

the correct Topic 06 result may be **unresolved conflict**, not automatic acceptance of whichever sentence is newer.

### F7 — Belief revision and knowledge-base update
**Role: TRANSFER**

Foundational papers include:

- *On the Logic of Theory Change: Partial Meet Contraction and Revision Functions* — Carlos Alchourrón, Peter Gärdenfors, and David Makinson (1985).
- *On the Difference Between Updating a Knowledge Base and Revising It* — Hirofumi Katsuno and Alberto O. Mendelzon (1991).

This literature gives formal vocabulary for distinguishing changes to beliefs about a static world from updates representing changes in the world itself.

It is highly relevant conceptually but cannot be imported unchanged because workplace evidence is:

- linguistically uncertain;
- source-dependent;
- temporally scoped;
- sometimes mutually inconsistent;
- sometimes missing;
- extracted with non-zero error.

### F8 — Truth maintenance and assumption-based truth maintenance
**Role: TRANSFER**

Foundational papers include:

- *A Truth Maintenance System* — Jon Doyle (1979).
- *An Assumption-based TMS* — Johan de Kleer (1986).

This family is especially relevant to the principle that new evidence should change an assessment without deleting the historical evidence that produced the old assessment.

Potentially transferable concepts include:

- justification dependencies;
- support sets;
- retraction;
- reinstatement;
- alternative environments;
- explicit inconsistency;
- explanation of why a conclusion currently holds.

### F9 — Temporal and dynamic knowledge graphs
**Role: TRANSFER**

Known seed papers include:

- *Know-Evolve: Deep Temporal Reasoning for Dynamic Knowledge Graphs* — Rakshit Trivedi et al. (2017).
- *HyTE: Hyperplane-based Temporally aware Knowledge Graph Embedding* — Shib Sankar Dasgupta, Swayambhu Nath Ray, and Partha Talukdar (2018).

The family is useful mainly for representation and temporal evolution. Much of it should be downgraded because link prediction over already-structured facts is not equivalent to resolving uncertain communication evidence.

### F10 — Document revision, version provenance, and data lineage
**Role: TRANSFER**

A foundational provenance seed is:

- *Why and Where: A Characterization of Data Provenance* — Peter Buneman, Sanjeev Khanna, and Wang-Chiew Tan (2001).

Relevant concepts include:

- source provenance;
- derivation provenance;
- version lineage;
- historical record retention;
- dependency tracing.

For Topic 06, provenance should attach to **assessments as well as source artifacts**.

For example, an assessment of "deadline = Friday" should retain which message and extraction supported it even after the current assessment becomes "deadline = Monday".

### F11 — Bitemporal and temporal database semantics
**Role: TRANSFER**

This is an important promoted family not adequately represented by the original seeds.

A foundational paper is:

- *A Taxonomy of Time in Databases* — Richard T. Snodgrass and Ilsoo Ahn (1985).

The literature distinguishes concepts such as:

- **valid time**: when a fact applies in the represented world;
- **transaction time**: when the database recorded or knew the fact.

This maps closely to the project's requirement to distinguish:

- event/effective time;
- observed collection/version time.

The mapping is not exact, but the conceptual distinction is strong enough that this family should be deliberately searched.

### F12 — Dialogue state tracking
**Role: TRANSFER**

Dialogue state tracking can contribute mechanisms for:

- incremental belief updates;
- uncertain state distributions;
- revision after new turns;
- retaining conversational context.

It should not be treated as direct evidence that the external-event state problem has been solved. Standard dialogue state is usually a model of user intent, goals, and slot values.

### F13 — Commitment lifecycle and social commitments
**Role: TRANSFER**

Multi-agent and dialogue literature often models commitments through lifecycle operations such as:

- creation;
- acceptance;
- discharge;
- cancellation;
- release;
- delegation;
- violation.

This is semantically attractive for work items because "committed", "completed", and "cancelled" are not merely textual labels but transitions with preconditions.

The main limitation is that this literature commonly assumes that communicative acts and parties are already represented formally. Topic 06 receives uncertain NLP outputs instead.

## Query families

### F1 — DIRECT: event factuality and modality

- `"event factuality" NLP factuality prediction`
- `"event factuality prediction" negation modality certainty`
- `"factuality inference" event modality polarity`
- `"factuality profiling" events`
- `"event certainty" modality negation NLP`
- `"event veridicality" NLP`
- `"factuality" source commitment embedded event`
- `"negation scope" event factuality`
- `"speculation scope" event factuality`
- `"epistemic modality" event factuality NLP`

### F2 — DIRECT: temporal information and relation extraction

- `"temporal information extraction" events relations`
- `"temporal relation extraction" event time`
- `"temporal relation classification" events`
- `"event temporal ordering" NLP`
- `TimeML event temporal relation`
- `TempEval event time relation`
- `"document creation time" temporal relation event`
- `"event time" "temporal relation extraction"`

### F3 — DIRECT: global temporal reasoning

- `"temporal ordering" events global constraints NLP`
- `"temporal graph" event ordering NLP`
- `"temporal closure" events NLP`
- `"temporal consistency" event relations NLP`
- `"temporal constraint" reasoning event extraction`
- `"structured prediction" temporal relation extraction`
- `"global temporal reasoning" events text`
- `"partial order" events temporal NLP`

### F4 — DIRECT: longitudinal event evolution

- `"event evolution" text documents timeline`
- `"event evolution tracking" NLP`
- `"event status" longitudinal text`
- `"event status tracking" NLP`
- `"timeline extraction" events documents`
- `"cross-document" event timeline extraction`
- `"event timeline" factuality revision`
- `"longitudinal event" extraction text`
- `"event state change" text extraction`

### F5 — DIRECT: correction, retraction, and supersession

- `"correction detection" text NLP`
- `"retraction detection" text NLP`
- `"revision detection" proposition text`
- `"supersession" text document NLP`
- `"superseding" statement correction NLP`
- `"claim revision" text correction`
- `"statement correction" contradiction NLP`
- `"document supersession" semantic`
- `"revision relation" document versions semantic`
- `"correction" "previous statement" NLP`
- `"deadline change" email NLP`
- `"changed deadline" text extraction`

### F6 — DIRECT: contradiction and NLI

- `"contradiction detection" text NLP`
- `"textual contradiction" temporal`
- `"natural language inference" temporal contradiction`
- `"NLI" event factuality contradiction`
- `"temporal contradiction" natural language inference`
- `"contradiction" correction supersession text`
- `"contradictory claims" provenance NLP`
- `"conflicting statements" natural language processing`

### F7 — TRANSFER: belief revision and knowledge-base update

- `"belief revision" conflicting evidence`
- `"belief revision" temporal information`
- `"belief update" evidence provenance`
- `"knowledge base revision" conflicting information`
- `"knowledge base update" revision temporal`
- `"belief revision" uncertain observations`
- `"iterated belief revision" conflicting information`
- `"belief revision" source reliability`

### F8 — TRANSFER: truth maintenance

- `"truth maintenance system" conflicting evidence`
- `"truth maintenance" justification dependencies`
- `"assumption-based truth maintenance" conflicting evidence`
- `"ATMS" beliefs assumptions contradiction`
- `"truth maintenance" provenance belief revision`
- `"justification-based truth maintenance" revision`
- `"truth maintenance" temporal reasoning`

### F9 — TRANSFER: temporal knowledge graphs

- `"temporal knowledge graph" evolving facts`
- `"temporal knowledge graph" fact validity`
- `"dynamic knowledge graph" event update`
- `"temporal knowledge graph" conflicting facts`
- `"temporal knowledge graph" provenance`
- `"temporal knowledge graph" revision`
- `"dynamic knowledge graph" fact revision`

### F10 — TRANSFER: provenance and revision history

- `"data provenance" version history revision`
- `"data lineage" conflicting records version`
- `"document provenance" revision history`
- `"version provenance" documents`
- `"provenance" belief revision evidence`
- `"provenance" conflicting information knowledge base`
- `"document revision" semantic change provenance`
- `"revision history" semantic change documents`

### F11 — TRANSFER: bitemporal semantics

- `"bitemporal" valid time transaction time`
- `"bitemporal database" correction history`
- `"valid time" "transaction time" temporal database`
- `"valid time" versioned facts`
- `"transaction time" historical correction`
- `"temporal database" retroactive correction`
- `"temporal database" valid time provenance`
- `"bitemporal" knowledge representation`

### F12 — TRANSFER: dialogue state mechanisms

- `"dialogue state tracking" revision correction`
- `"dialog state tracking" uncertainty update`
- `"dialogue state" belief update`
- `"dialogue state tracking" conflicting information`
- `"dialogue state tracking" incremental update`

### F13 — TRANSFER: commitment lifecycle

- `"social commitment" lifecycle multiagent`
- `"commitment lifecycle" cancel discharge release`
- `"commitment state" multiagent communication`
- `"commitment tracking" dialogue`
- `"commitment" create discharge cancel multiagent`
- `"social commitments" dialogue acts`
- `"commitment store" dialogue`
- `"commitment management" multiagent systems`

## False friends and downgrade rules

Discovery should downgrade or reject the following even when keyword matching is strong:

1. Pure date or TIMEX extraction with no event binding or temporal relation reasoning.
2. Topic 05-style action/request/commitment extraction that stops at what was said at utterance time.
3. Any approach that equates event mention with event occurrence.
4. Negation, speculation, or hedging systems that identify cues but not their semantic scope or target event.
5. "Certainty" literature about model confidence, annotator agreement, sentiment strength, or calibration rather than epistemic status of propositions.
6. Generic NLI benchmark work whose only capability is isolated sentence-pair classification.
7. Contradiction detection that automatically chooses a winner or assumes contradiction means supersession.
8. Any latest-message-wins or latest-version-wins state policy.
9. Temporal ordering that assumes every ordered event occurred.
10. Scheduling, project-planning, temporal-CSP, or workflow literature where events and constraints are already structured and authoritative.
11. Update summarization or timeline summarization whose objective is novelty or salience rather than truth/status maintenance.
12. Event-evolution work where "event" actually means a topic, news story, cluster, or trend.
13. Generic control-system, robotics, Bayesian-filtering, reinforcement-learning, or software state tracking.
14. Dialogue state tracking limited to goals or slots, except as explicitly labelled TRANSFER evidence.
15. Temporal-KG work limited to embeddings or link prediction without validity, revision, conflict, or provenance.
16. Workflow state machines where completed/cancelled/pending are authoritative database values rather than inferred from communication.
17. Raw text diff or revision tracking that does not distinguish correction, supplementation, retraction, contradiction, and supersession.
18. Whole-document supersession models that cannot preserve proposition-level validity.
19. Provenance work limited to reproducibility metadata with no source or derivational connection to an assessment.
20. Event sourcing and CQRS as evidence for language understanding. They are engineering background only.
21. Domain literature whose state labels are supplied by an external workflow rather than inferred from text.
22. Any method that infers completion, cancellation, or confirmation from the absence of later messages.
23. Any method that assumes chronological recency proves semantic replacement.
24. Any model that treats contradiction and supersession as equivalent.
25. Any revision mechanism that destroys previous source evidence or historical assessments without an adaptable provenance mechanism.
26. Transfer-domain results presented as evidence of production workplace-email accuracy.
27. Topic 06 methods that silently correct Topic 05 uncertainty in owner, deadline, condition, modality, or negation instead of carrying that uncertainty into the state model.

A useful admission distinction is therefore:

**Direct target capability**
- factuality of events;
- temporal relations;
- event ordering;
- event timelines;
- correction/retraction/supersession;
- contradiction among textual propositions.

**Transfer mechanism**
- belief revision;
- TMS/ATMS;
- temporal knowledge graphs;
- provenance;
- bitemporal databases;
- dialogue-state update;
- formal commitment lifecycles.

Transfer literature can justify a representation, reasoning mechanism, or engineering experiment. It cannot establish production-email accuracy.

## Date policy

**Earliest publication year discovery must include: 1979.**

The reason is not historical completeness for its own sake. Several foundations needed by Topic 06 substantially predate modern NLP benchmarks:

- 1979: Jon Doyle's *A Truth Maintenance System* establishes dependency-aware maintenance and retraction of beliefs.
- 1985: AGM belief revision formalizes revision and contraction.
- 1985: Snodgrass and Ahn's temporal-database taxonomy establishes distinctions including temporal dimensions that lead into valid-time/transaction-time and bitemporal modelling.
- 1986: de Kleer's assumption-based TMS develops reasoning over alternative assumption environments.
- 1991: Katsuno and Mendelzon distinguish knowledge-base updating from revision.
- 2003 onward: TimeML and subsequent TempEval work establish the modern NLP temporal-information tradition.
- Late 2000s onward: event factuality and textual contradiction become substantial empirical NLP task families.

Therefore a default search window such as 2000-present would silently remove important foundations for revision, provenance, and temporal-state semantics.

Discovery may use **family-specific emphasis windows** to control volume—for example, modern NLP searches can emphasize 2003 onward—but the overall programme must permit papers back to **1979**, and foundational symbolic or temporal-database results should not be excluded merely because they predate statistical NLP.
