# Natural-language longitudinal work-item revision in workplace and operational communication: distinguishing supersession, correction, supplementation, contradiction, reopening, unresolved conflict, and claimed versus independently confirmed completion. academic terminology analysis

## Product problem

The target is not generic extraction and not simply a chronological summary. The unit being maintained is a persistent work item whose evidence may arrive through multiple natural-language messages and whose accepted assessment may change without erasing earlier observations.

A useful academic decomposition is:

1. determine what event, action, commitment, decision, deadline, or condition a message asserts;
2. determine the source's commitment to that proposition: actual, planned, possible, conditional, negated, hypothetical, claimed complete, and so on;
3. determine the relevant times, including message time, event or effective time, deadline time, and observation time;
4. determine whether a new observation concerns the same persistent matter;
5. determine the relation of the new assertion to prior assertions: supplementation, correction, retraction or revocation, supersession, contradiction, reopening, or unresolved conflict;
6. preserve source-relative observations and historical assessments;
7. derive a current assessment only when the evidence justifies doing so;
8. distinguish a participant's assertion of completion from independent corroboration or stronger verification.

No single seed term reliably denotes all of this. The academic search therefore needs both DIRECT families that test whether the integrated problem has been studied and TRANSFER families that provide semantics, representations, or evaluation methods for its components.

The most important terminology changes are to promote **source commitment**, **source-relative factuality**, **factuality attribution**, **evidentiality**, **belief update versus belief revision**, **commitment lifecycle**, **temporal provenance**, **valid time versus transaction/observation time**, and **inconsistency-tolerant reasoning**. Broad labels such as `state tracking`, `dialogue state tracking`, `event update`, `change detection`, and `event sourcing` should not drive discovery without stronger qualifiers.

## Seed keyword audit

| Seed | Academic meaning | Fit | Main risk |
| --- | --- | --- | --- |
| event factuality prediction | Predicts whether a mentioned event is presented as actual, negated, possible, uncertain, or otherwise factual/non-factual, often with polarity and certainty dimensions. | STRONG | Usually evaluates isolated mentions or documents rather than longitudinal assessments of the same work item. |
| factuality profiling | Less standardized label for characterizing events or propositions along factuality dimensions such as polarity, certainty, modality, and source perspective. | MODERATE | Terminology is unstable and may retrieve corpus profiling rather than prediction. |
| event modality | Models possibility, necessity, intention, obligation, conditionality, hypotheticality, and related modal status attached to an event. | STRONG | A modal label at one utterance does not determine later lifecycle validity. |
| event certainty | Estimates how certain a source is that an event or proposition holds. | MODERATE | Certainty can be mistaken for evidence strength or independent verification. |
| event veridicality | Determines whether linguistic contexts license an inference that an embedded event or proposition is true, false, or uncertain. | STRONG | Commonly sentence-local and lexical-semantic rather than longitudinal. |
| negation detection | Detects negation cues and usually their scope. | MODERATE | Negation alone does not distinguish cancellation, revocation, supersession, or conflict. |
| speculation detection | Detects speculative, hypothetical, or uncertain language and its scope. | MODERATE | Only one component of factuality and lifecycle reasoning. |
| hedging detection | Detects linguistic weakening of commitment. | MODERATE | Often clause- or discourse-level and may not attach cleanly to the tracked event. |
| temporal information extraction | Extracts and normalizes events, times, durations, and sometimes relations. | MODERATE | Frequently retrieves date/TIMEX extraction without event-state reasoning. |
| temporal relation extraction | Classifies temporal relations between events and times. | STRONG | Temporal precedence is not semantic supersession. |
| event temporal ordering | Places events into relative chronological order, sometimes using global constraints. | STRONG | Later occurrence or mention does not imply replacement of an earlier assertion. |
| temporal relation classification | Assigns relation labels such as before, after, overlap, or inclusion. | STRONG | Pairwise relations may omit global consistency and multiple kinds of time. |
| TimeML | Annotation specification for events, times, signals, and temporal links. | MODERATE | Annotation framework rather than a longitudinal revision model. |
| temporal graphs | Graph representation of temporally related entities or events. | MODERATE | Highly ambiguous; generic temporal-GNN literature dominates the phrase. |
| temporal constraint reasoning | Uses transitivity, interval constraints, consistency, or constraint satisfaction for temporal inference. | STRONG | Cannot decide factuality, provenance, authority, or supersession by itself. |
| event status tracking | Unstable label for tracking whether an event is planned, active, completed, cancelled, or otherwise changed. | MODERATE | Often means operational event management rather than NLP. |
| state tracking | Generic maintenance of a changing latent or explicit state. | WEAK | Retrieves control, robotics, games, workflows, and many unrelated tasks. |
| dialogue state tracking | Mainstream task-oriented dialogue task for maintaining user goals and slot values. | WEAK | Usually does not track truth or lifecycle of external work items. |
| event evolution | Models how events or representations evolve across time or documents. | MODERATE | Often means topic/story evolution rather than revised truth assessment of one item. |
| event update | Ambiguous label for updating event information or representations. | WEAK | Retrieves update summarization, event streams, databases, and software systems. |
| timeline extraction | Builds ordered event timelines from text. | MODERATE | Chronology alone cannot represent correction, supersession, or unresolved conflict. |
| contradiction detection | Determines whether two statements cannot simultaneously hold under an interpretation. | STRONG | Contradiction must not automatically be treated as supersession. |
| natural language inference | Classifies entailment, contradiction, or neutrality between a premise and hypothesis. | MODERATE | Mainstream NLI lacks persistent state, source lineage, and temporal revision. |
| belief revision | Formal study of rational change to beliefs after new information, including revision, contraction, and expansion. | STRONG | Formal work assumes propositions have already been extracted correctly. |
| truth maintenance systems | Maintains conclusions and their justifications and retracts consequences when support changes. | STRONG | Does not perform natural-language interpretation or work-item identity resolution. |
| assumption-based truth maintenance | Maintains alternative consistent environments supported by different assumption sets. | STRONG | Requires symbolic propositions and assumptions supplied externally. |
| knowledge-base revision | Changes a knowledge base while managing consistency and minimizing unwanted change. | STRONG | Often operates on normalized symbolic facts rather than source messages. |
| temporal knowledge graphs | Represent facts with temporal qualifiers or validity intervals and reason over evolving graphs. | MODERATE | Much work concerns link prediction and forecasting, not evidence lineage or competing claims. |
| document supersession | Describes one document replacing the authority/applicability of another. | MODERATE | Common in records and legal domains but not a stable NLP semantic relation. |
| version supersession | Describes one version replacing another. | WEAK | Version ordering does not imply that every proposition in the later version supersedes its predecessor. |
| revision tracking | Records or detects differences across versions. | MODERATE | Usually detects changed text rather than semantic relations among claims. |
| change detection | Generic detection of differences between observations. | WEAK | Dominated by remote sensing, vision, time-series, drift, and diff literature. |
| provenance-aware state | Descriptive term for state carrying source/derivation information. | MODERATE | Not a canonical task name; standard provenance terminology should also be searched. |
| event sourcing | Append-only software architecture in which current state is reconstructed from events. | REJECT | Useful engineering analogy, but not an academic NLP task and does not define truth semantics. |

### Terms to promote

The primary search vocabulary should include:

- event factuality assessment;
- speaker commitment;
- source commitment;
- source-relative factuality;
- factuality attribution;
- epistemic modality;
- event polarity;
- event veridicality;
- evidentiality;
- information-source attribution;
- claim verification;
- evidence corroboration;
- temporal relation extraction;
- event temporal ordering;
- temporal closure;
- global temporal inference;
- temporal dependency parsing;
- effective time;
- valid time;
- transaction time;
- bitemporal and multitemporal data;
- correction;
- retraction;
- revocation;
- cancellation;
- semantic supersession;
- revision relation classification;
- commitment store;
- social commitment lifecycle;
- commitment discharge;
- state change tracking;
- entity state tracking;
- belief revision;
- belief update;
- truth maintenance;
- assumption-based truth maintenance;
- knowledge-base revision;
- knowledge-base update;
- inconsistency-tolerant reasoning;
- paraconsistent reasoning;
- temporal/dynamic knowledge graphs;
- data provenance;
- temporal provenance;
- version lineage;
- semantic diff;
- cross-document event evolution.

### Terms to demote

Use these only with strong qualifiers rather than as primary discovery anchors:

- factuality profiling;
- hedging detection;
- temporal graphs;
- event status tracking;
- state tracking;
- dialogue state tracking;
- event update;
- timeline extraction;
- version supersession;
- change detection;
- provenance-aware state;
- event sourcing.

## Academic task families

### F1 — Longitudinal work-item lifecycle state tracking in workplace communication — DIRECT

This is the exact target family. It searches for systems that maintain the state of an external work matter over successive email, enterprise-chat, or operational messages, rather than merely detecting the original action.

The target inventory includes requested, proposed, planned, approved, completed, revoked, cancelled, superseded, disputed, conditional, reopened, and unresolved states. Historical assessments must remain recoverable.

No seed paper is named because no specific paper is sufficiently certain to be a direct match. That absence is itself what gap-1 and gap-4 require round 3 to test.

### F2 — Event factuality, source commitment, modality, and veridicality — DIRECT

This is the strongest established NLP family for the distinction between an event being mentioned and being presented as factual.

Particularly important terminology is **source commitment** or **speaker commitment**. A system that stores only `completed=true` after reading “we completed it” loses the distinction required by the project. The observation should instead preserve that a particular source committed to a completion proposition with a particular factuality value.

Known seeds include:

- Saurí and Pustejovsky (2009), *FactBank: a corpus annotated with event factuality*.
- de Marneffe, Manning, and Potts (2012), *Did It Happen? The Pragmatic Complexity of Veridicality Assessment*.

### F3 — Evidentiality, information-source attribution, corroboration, and claim verification — TRANSFER

This family targets gap-5.

Event factuality tells msgloom what a source asserts or appears committed to. It does not automatically establish that the asserted completion is independently true. Relevant neighboring terminology is therefore:

- evidentiality;
- information source;
- source attribution;
- corroboration;
- claim verification;
- fact verification;
- evidence aggregation;
- source reliability.

A known transfer seed is Thorne et al. (2018), *FEVER: a Large-scale Dataset for Fact Extraction and VERification*.

Fact-verification results remain transfer evidence unless a study actually evaluates longitudinal operational statements and distinguishes an actor's own completion report from independent corroboration.

### F4 — Temporal information extraction, temporal relations, and global temporal reasoning — DIRECT

The project needs several different temporal coordinates rather than one generic timestamp:

- utterance/message time;
- event or effective time;
- deadline/constraint time;
- observed/collection time.

Relevant academic terminology includes temporal relation extraction, event temporal ordering, temporal closure, global temporal inference, temporal dependency parsing, valid/effective time, and cross-document temporal relations.

Known seeds include:

- Pustejovsky et al. (2003), *TimeML: Robust Specification of Event and Temporal Expressions in Text*.
- Verhagen et al. (2007), *SemEval-2007 Task 15: TempEval Temporal Relation Identification*.
- Chambers and Jurafsky (2008), *Jointly Combining Implicit Constraints Improves Temporal Ordering*.

The critical project constraint is that temporal order must remain separate from revision semantics. A later message is not automatically a superseding message.

### F5 — Natural-language revision-relation classification — DIRECT

This is the main terminology family for gap-2.

The required relation inventory is richer than contradiction:

- supplementation;
- correction;
- retraction;
- revocation;
- cancellation;
- supersession;
- contradiction;
- reopening;
- unresolved conflict.

No single standardized NLP task name is known to cover the whole inventory. Discovery should therefore search several neighboring vocabularies: semantic revision, correction, retraction, discourse relations, cancellation, contradiction, supersession, and longitudinal updates.

The absence of a known seed paper is deliberate rather than an assertion that no such paper exists.

### F6 — Contradiction detection and natural language inference — TRANSFER

NLI can identify semantic incompatibility, but its normal entailment/contradiction/neutral labels are too coarse to become the project's lifecycle semantics directly.

Known seeds include:

- de Marneffe, Rafferty, and Manning (2008), *Finding Contradictions in Text*.
- Bowman et al. (2015), *A large annotated corpus for learning natural language inference*.
- Williams, Nangia, and Bowman (2018), *A Broad-Coverage Challenge Corpus for Sentence Understanding through Inference*.

A contradiction between two messages should normally become evidence of conflict until another mechanism establishes whether one is a correction, retraction, supersession, or simply a different-time claim.

### F7 — Dialogue commitments, commitment stores, retraction, cancellation, and reopening — TRANSFER

Task-oriented `dialogue state tracking` is not the most useful dialogue terminology for this project.

More relevant are:

- commitments;
- commitment stores;
- social commitments;
- commitment creation;
- commitment discharge;
- fulfillment;
- cancellation;
- retraction;
- violation;
- dialogue obligations.

These concepts can resemble a work item moving from proposed or promised to accepted, fulfilled, cancelled, or revoked. Much of the literature is nevertheless formal, argumentative, or multi-agent rather than empirical workplace NLP, so it should be treated as transfer unless a paper directly evaluates natural-language operational communication.

### F8 — Entity and process state-change tracking from text — TRANSFER

Procedural-text research supplies useful empirical machinery for maintaining persistent state across multiple sentences.

A known seed is Dalvi et al. (2018), *Tracking State Changes in Procedural Text: a Challenge Dataset and Models for Process Paragraph Comprehension*.

The transfer limitation is substantial: physical or procedural entity states are usually much cleaner than human commitments, approvals, disputes, and source-relative claims.

### F9 — Belief revision, belief update, truth maintenance, and inconsistency-tolerant reasoning — TRANSFER

This is the main formal family for retaining justifications and recomputing accepted conclusions without deleting historical evidence.

Important distinctions include:

- expansion versus revision versus contraction;
- revision versus update;
- assumption-supported conclusions;
- alternative consistent environments;
- inconsistency-tolerant or paraconsistent reasoning;
- non-monotonic inference.

Known foundational seeds are:

- Doyle (1979), *A Truth Maintenance System*.
- Alchourrón, Gärdenfors, and Makinson (1985), *On the Logic of Theory Change: Partial Meet Contraction and Revision Functions*.
- de Kleer (1986), *An assumption-based TMS*.
- Katsuno and Mendelzon (1991), *On the Difference Between Updating a Knowledge Base and Revising It*.

The revision/update distinction is especially important. Some new messages correct what was previously believed; others report that the real-world work item itself has changed. Those are not necessarily the same operation.

### F10 — Temporal and dynamic knowledge graphs — TRANSFER

Temporal knowledge graphs provide representations for facts whose validity changes over time.

Known seeds include:

- Trivedi et al. (2017), *Know-Evolve: Deep Temporal Reasoning for Dynamic Knowledge Graphs*.
- Dasgupta et al. (2018), *HyTE: Hyperplane-based Temporally aware Knowledge Graph Embedding*.

The main downgrade condition is that temporal link prediction or forecasting is insufficient. The product needs explicit source provenance, historical observations, competing claims, and a separately derived current assessment.

### F11 — Temporal databases, bitemporal/multitemporal data, and provenance — TRANSFER

This family is particularly important for gap-7 and gap-8.

Temporal databases provide terminology such as:

- valid time;
- transaction time;
- bitemporal data;
- decision time in some multitemporal treatments;
- historical versions.

Database provenance provides:

- source lineage;
- derivation lineage;
- why/where-style provenance concepts;
- provenance of derived views.

Known seeds include:

- Jensen et al. (1994), *A Consensus Glossary of Temporal Database Concepts*.
- Buneman, Khanna, and Tan (2001), *Why and Where: A Characterization of Data Provenance*.

This family can inform the representation of immutable observations and derived current state, but it does not provide the natural-language semantics that decide which assertion is a correction or supersession.

### F12 — Document revision, semantic change, version lineage, and supersession — TRANSFER

Version-control and document-history work can contribute lineage and change representations, but lexical change is not enough.

The discovery target is specifically **semantic** change across versions:

- a deadline changed;
- a completion claim was corrected;
- a previous instruction was revoked;
- a new statement merely supplemented the old one;
- one document/version became authoritative while some unchanged propositions remained valid.

Searches therefore need terms such as semantic diff, semantic change, revision provenance, version lineage, correction, and supersession rather than generic `diff`.

### F13 — Cross-document event evolution and timeline construction — TRANSFER

Cross-document timeline and event-evolution systems can contribute methods for accumulating evidence over a stream of documents.

The transfer boundary is that story evolution and chronology are not themselves state-resolution semantics. A useful paper must do more than identify that a later article or message contains new information.

## Query families

### F1 — DIRECT: longitudinal workplace work-item lifecycle

- `"work item" lifecycle state tracking email NLP`
- `"workplace communication" longitudinal work item state tracking`
- `"business email" task status change completion cancellation correction`
- `"enterprise chat" commitment status tracking completion revocation`
- `email action item longitudinal state completed cancelled reopened`
- `workplace email commitment lifecycle planned approved completed revoked`
- `operational communication longitudinal state tracking superseded disputed unresolved`
- `email dialogue requested proposed planned approved completed revoked superseded`
- `"Microsoft Teams" task status change NLP`
- `Slack enterprise chat work item status change NLP`

This family is the primary search for gap-1 and gap-4. Results that merely extract action items must be downgraded.

### F2 — DIRECT: factuality and source commitment

- `"event factuality" source attribution`
- `"event factuality prediction" modality negation certainty`
- `"speaker commitment" event factuality`
- `"source commitment" factuality NLP`
- `"factuality assessment" nested sources events`
- `event factuality source perspective longitudinal`
- `event veridicality source commitment modality`
- `factuality polarity certainty source attribution event`

The high-value discriminator is whether the factuality value is tied to the source making the claim.

### F3 — TRANSFER: evidentiality, corroboration, and verification

- `evidentiality information source factuality NLP`
- `claim verification source attribution corroborating evidence`
- `fact verification evidence provenance source corroboration`
- `event factuality independent evidence verification`
- `multi-source corroboration claim verification NLP`
- `source reliability evidence aggregation factual claims NLP`
- `completion claim independent confirmation evidence NLP`
- `operational communication completion claim verification`

This family is intended to test whether gap-5 can be closed or at least narrowed.

### F4 — DIRECT: temporal relations and multiple notions of time

- `"temporal relation extraction" event ordering global inference`
- `"event temporal ordering" temporal constraints`
- `TimeML temporal closure event relations`
- `"temporal dependency parsing" events`
- `cross-document temporal relation extraction event timeline`
- `event time document creation time temporal relation NLP`
- `"valid time" event extraction natural language`
- `message time event time deadline temporal NLP`
- `effective time temporal information extraction text`

Discovery should specifically inspect whether systems can represent more than one temporal axis.

### F5 — DIRECT: semantic revision relations

- `natural language correction retraction supersession contradiction classification`
- `"revision relation" natural language correction contradiction`
- `dialogue correction retraction cancellation reopening unresolved conflict`
- `document revision semantic supersession correction supplementation NLP`
- `longitudinal text supersession correction contradiction`
- `conversation update correction revocation cancellation NLP`
- `semantic supersession natural language statements`
- `correction contrast elaboration discourse relation NLP`
- `retraction correction contradiction longitudinal dialogue`
- `supersession versus contradiction text revision`

This is the key round-3 query family for gap-2.

### F6 — TRANSFER: contradiction and NLI

- `contradiction detection document revisions longitudinal`
- `natural language inference temporal updates contradiction`
- `multi-sentence contradiction detection temporal`
- `natural language inference conflicting evidence provenance`
- `temporal NLI event contradiction`
- `contradiction detection same event different times`
- `cross-document contradiction detection evolving facts`

Generic sentence-pair benchmarks should be admitted only as transfer evidence.

### F7 — TRANSFER: dialogue commitments and lifecycle operations

- `dialogue commitment tracking retraction correction`
- `"commitment store" dialogue retraction`
- `"social commitment" lifecycle cancel revoke discharge`
- `dialogue obligations commitments update retraction`
- `argumentation dialogue commitment retraction`
- `conversation commitment fulfillment violation cancellation`
- `dialogue commitment accepted fulfilled cancelled`
- `commitment lifecycle multiagent communication revocation`
- `dialogue reopening commitment correction`

This terminology is preferable to generic `dialogue state tracking` for lifecycle semantics.

### F8 — TRANSFER: textual state-change tracking

- `"state change tracking" procedural text`
- `"entity state tracking" text`
- `"tracking state changes" natural language`
- `process state tracking natural language`
- `event state change extraction text`
- `longitudinal state tracking textual observations`
- `state transition extraction natural language`

These papers can contribute evaluation structures even when their state inventories are not workplace states.

### F9 — TRANSFER: belief revision, update, truth maintenance, and inconsistency

- `"belief revision" conflicting evidence temporal`
- `"belief update" changing world temporal information`
- `"truth maintenance" conflicting evidence justifications`
- `"assumption-based truth maintenance" inconsistent evidence`
- `"knowledge base revision" update temporal information`
- `"revision versus update" knowledge base changing world`
- `inconsistency tolerant reasoning conflicting information provenance`
- `paraconsistent reasoning conflicting evidence knowledge base`
- `non-monotonic reasoning source provenance revision`
- `temporal belief revision evidence sources`

The revision-versus-update distinction should be explicitly preserved during synthesis.

### F10 — TRANSFER: temporal and dynamic knowledge graphs

- `"temporal knowledge graph" fact update history provenance`
- `"dynamic knowledge graph" evolving facts`
- `"temporal knowledge graph" contradiction update`
- `"temporal knowledge graph" event state change`
- `versioned knowledge graph provenance temporal`
- `"temporal knowledge graph" validity interval source provenance`
- `knowledge graph fact revision provenance time`

Papers that only forecast missing edges do not close any of the major target gaps.

### F11 — TRANSFER: temporal databases and provenance

- `bitemporal database valid time transaction time provenance`
- `"temporal provenance" database`
- `"valid time" "transaction time" provenance`
- `data provenance versioned facts temporal`
- `"valid time" "transaction time" "decision time" temporal database`
- `three time dimensions temporal database provenance`
- `multitemporal database observation time effective time`
- `immutable observations derived current state provenance database`
- `temporal database historical assertions source provenance`

This family is particularly relevant to the representation needed for gap-7 and gap-8, though those remain engineering gaps unless evaluated on the product's state-resolution task.

### F12 — TRANSFER: document/version semantic lineage

- `document version semantic change correction supersession`
- `document revision history semantic change NLP`
- `versioned documents contradiction supersession`
- `revision provenance document versions`
- `"semantic diff" document revision`
- `wiki revision correction retraction semantic`
- `document version lineage provenance semantic change`
- `version-aware text revision semantic relation`

Search results should be inspected for semantic relations, not merely textual differencing.

### F13 — TRANSFER: event evolution and timelines

- `"event evolution" tracking news timeline`
- `cross-document event evolution timeline`
- `event update tracking longitudinal text`
- `"timeline extraction" event state change`
- `cross-document event timeline conflicting reports`
- `event evolution correction contradiction news`
- `multi-document timeline factuality events`

This family may reveal architectures for longitudinal accumulation but should not be mistaken for lifecycle-state resolution.

## False friends and downgrade rules

1. **Task-oriented dialogue state tracking is not work-item state tracking.** Slot values, user goals, and booking states do not establish a method for the changing truth of an external business action.

2. **Pure date extraction is insufficient.** A paper that recognizes “Friday” without attaching it to the correct action or determining its temporal relation to earlier deadlines does not address the target problem.

3. **Topic 05 extraction is not Topic 06 state.** Detecting that a message contains a request, promise, decision, deadline, or condition establishes the utterance-time semantic event; it does not establish whether that event later remains valid.

4. **Identity alone is insufficient.** Event coreference, topic clustering, thread linking, and cross-document matching can establish that evidence belongs together but do not decide factuality or revision semantics.

5. **Generic NLI is transfer evidence only.** Entailment/contradiction/neutral does not encode correction, supplementation, supersession, revocation, reopening, or unresolved conflict.

6. **Contradiction is not supersession.** Do not admit a method as a direct solution if it automatically chooses one conflicting claim or replaces the older one solely because a contradiction exists.

7. **Latest-message-wins is explicitly disqualifying as state semantics.** Observation order is not semantic authority.

8. **Fact verification is not automatically longitudinal state tracking.** Static claim verification can inform independent confirmation but does not by itself model the lifecycle of a work item.

9. **Source attribution must mean information-source or commitment attribution.** Authorship attribution and quotation attribution alone do not solve the target problem.

10. **Certainty, hedging, speculation, and negation must be attached to the correct event.** Generic sentence-level uncertainty does not establish the state of a specific work item.

11. **Chronology is not revision.** Timeline extraction and temporal ordering that only sort events should be treated as transfer evidence.

12. **Workflow state machines are not natural-language state reasoning.** A system whose input already contains structured states such as OPEN, DONE, or CANCELLED does not demonstrate extraction and resolution from messages.

13. **Process mining is transfer unless the state must be inferred from text.** Structured event logs eliminate much of the uncertainty central to this topic.

14. **Issue or ticket reopening is not direct evidence when status metadata provides the transition.** It becomes more relevant only if the paper determines reopening or closure from natural-language evidence.

15. **Version ordering is not proposition supersession.** A newer file can coexist with still-valid old propositions.

16. **Document diff is not semantic revision.** Lexical insert/delete operations do not tell the product whether a changed sentence is a correction, supplementation, contradiction, or stylistic rewrite.

17. **Legal or standards supersession is transfer unless proposition-level semantics are evaluated.** Document authority is useful but not equivalent to work-item revision.

18. **Temporal knowledge-graph forecasting is not sufficient.** Link prediction without source provenance, historical claims, and competing assessments should be downgraded.

19. **Generic temporal graph neural networks are false positives.** Dynamic graphs unrelated to natural-language events are out of scope.

20. **Belief revision and truth maintenance are normally transfer families.** They can justify semantics and data structures but do not establish language-understanding accuracy when their propositions are manually encoded.

21. **Event sourcing is engineering background, not academic evidence for natural-language semantics.** An append-only log is compatible with the product's preservation principle but does not decide what a message means.

22. **Database provenance alone is insufficient.** Tuple lineage does not resolve which conflicting assertion should currently be accepted.

23. **Update summarization is downstream.** A summarizer that assumes a current state does not define how the state became current.

24. **Dialogue repair can be a false friend.** ASR repairs, disfluency repair, or conversational fluency corrections are outside scope unless the repair changes the semantic status of the persistent proposition.

25. **Completion keywords are not confirmation.** A paper that marks an event completed because a source says “done” does not close gap-5 unless it explicitly distinguishes source assertion from corroborating evidence.

26. **Overwriting history is incompatible with the product requirement.** A method that mutates one current record while losing the previous observation or assessment cannot support the required provenance model.

27. **Synthetic and cross-domain evidence must remain labeled as transfer evidence.** It can validate mechanisms and adversarial fixtures but cannot establish production workplace-email accuracy.

28. **Production-domain absence is not an excuse to broaden admission criteria.** A weakly related paper should not be admitted merely to fill a paper quota.

## Date policy

**Earliest publication year to include: 1979.**

The search must reach at least 1979 because the truth-maintenance strand is directly relevant to the project's requirement that conclusions retain their justifications and be revised without destroying historical evidence. Doyle's 1979 *A Truth Maintenance System* is therefore a foundational transfer source that a modern-only recency window would silently exclude.

The search also needs to retain access to several later foundations:

- 1985: AGM-style belief revision;
- 1986: assumption-based truth maintenance;
- 1991: the formal distinction between knowledge-base **revision** and **update**;
- 1990s: temporal-database concepts needed for multiple notions of time;
- 2003 onward: TimeML and modern temporal NLP;
- late 2000s onward: contradiction detection, temporal-ordering methods, and event-factuality resources such as FactBank.

The 1979 boundary should **not** trigger an undirected search of all AI literature since 1979. It should be used selectively for the historical families whose foundations are genuinely that old. Modern NLP families can use much narrower effective windows, but discovery must not impose one global recency cutoff that removes the formal work needed to understand revision, update, justification, and persistence.
