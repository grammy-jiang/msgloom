# Longitudinal event and work-item state transitions in dialogue and operational communication academic terminology analysis

## Product problem

The target is not ordinary event extraction and not ordinary thread summarization. The research object is a **persistent, evidence-backed assessment of one work item across successive communications**, where the system must preserve both the historical observations and the history of its own assessments.

The most important semantic separations are:

- mention versus factual event;
- plan, intention or condition versus completion;
- a source asserting completion versus completion being independently confirmed;
- message/utterance time versus event/effective time versus deadline/constraint time versus observation/version time;
- contradiction versus correction versus supersession;
- later evidence versus stronger or more authoritative evidence;
- withdrawal/revocation versus ordinary negation;
- supplementation versus replacement;
- resolved state versus unresolved conflict;
- current accepted assessment versus historical assessment.

The terminology audit shows that there is **no single established academic task name covering that whole contract**. Discovery therefore needs several narrowly defined task families, with explicit DIRECT versus TRANSFER roles.

Event factuality is one of the strongest direct families because the literature explicitly models the factual status of event mentions and, in FactBank-style work, does so relative to discourse sources rather than treating truth as an unqualified document-level property. FactBank itself is based on newswire/broadcast material, which also illustrates why this family does not close the workplace-domain gap. citeturn514853search0turn514853search3 Later event-factuality work continues to model holders/sources, targets and factuality values. citeturn148079search1turn148079search8

Temporal NLP is another direct component. TimeML was explicitly designed to represent events, temporal expressions, anchoring and ordering, and TempEval subsequently operationalized temporal-relation evaluation. citeturn517637search0turn514853search1turn517637search2 Cross-document timeline research is useful for longitudinal accumulation, but its canonical task is chronological ordering of events, not maintenance of competing historical assessments. citeturn554706search46

The most important terminology promotion in this round is **dialogue commitment / correction / retraction / grounding**. Formal dialogue work explicitly distinguishes participants' public commitments and analyzes what survives or changes after correction, acknowledgement and dispute. Lascarides and Asher's work is particularly close to gap 2 because a correction can deny part of an earlier contribution while leaving other commitments intact; it is therefore much closer to the required semantics than generic contradiction detection. citeturn599613search1turn599613search10 Work on retraction likewise treats withdrawal as a governed operation on commitments rather than as simple contradiction. citeturn599613search7

A second major promotion is **bitemporal / temporal-database terminology**. Snodgrass and Ahn's temporal-database taxonomy explicitly distinguishes different notions of time in stored information, making this a much better search family for gap 7 than the vague phrase "temporal graphs." citeturn869908search46

A third is **data provenance / lineage**. The provenance literature explicitly asks where derived information came from and distinguishes kinds of provenance such as why- and where-provenance. That terminology is substantially stronger than searching for the non-standard phrase "provenance-aware state." citeturn869908search0turn869908search1

## Seed keyword audit

| Seed | Academic meaning | Fit | Main risk |
| --- | --- | --- | --- |
| event factuality prediction | Predict factual status of event mentions, often relative to a source | STRONG | Usually static; source assertion is not independent confirmation |
| factuality profiling | Compose polarity, modality and source information into an event factuality assessment | STRONG | Older terminology; may miss newer EFP work |
| event modality | Modal status such as possible, intended, hypothetical or necessary | MODERATE | Modal classes do not equal lifecycle states |
| event certainty | Expressed epistemic certainty concerning an event | MODERATE | Easily confused with model confidence |
| event veridicality | Whether linguistic context licenses inference to an event's actuality | MODERATE | Often lexical/compositional rather than longitudinal |
| negation detection | Detect negation cues, scope and targets | MODERATE | Negation alone does not identify revocation or supersession |
| speculation detection | Detect speculative or uncertain propositions and scope | MODERATE | Often sentence-level and biomedical |
| hedging detection | Detect commitment-weakening expressions | WEAK | Much hedging is rhetorical rather than event-state semantics |
| temporal information extraction | Extract events, times and temporal relationships | STRONG | Pure date extraction is a large false-positive class |
| temporal relation extraction | Extract before/after/overlap/etc. relations | STRONG | Pairwise relations alone do not maintain state |
| event temporal ordering | Determine chronology among events | STRONG | Chronology is not message or supersession order |
| temporal relation classification | Classify event-event/event-time temporal relations | STRONG | Often pairwise and locally evaluated |
| TimeML | Temporal event/time/link annotation specification | STRONG | Does not itself define lifecycle or evidential state |
| temporal graphs | Graph representation of temporal entities/relations | MODERATE | Dominated by generic dynamic-graph literature if unqualified |
| temporal constraint reasoning | Constraint propagation and consistency over temporal relations | STRONG | Usually assumes symbolic relations already exist |
| event status tracking | Non-standard phrase for event/process status | WEAK | No stable NLP task definition |
| state tracking | Generic sequential state maintenance | WEAK | Far too broad |
| dialogue state tracking | Task-oriented maintenance of user goals and slot values | MODERATE | Standard DST state is not evidence-backed work-item truth |
| event evolution | Usually topic/story/event-cluster evolution | WEAK | Wrong evolving object |
| event update | Ambiguous incorporation of new event information | WEAK | Mixes streams, news and knowledge graphs |
| timeline extraction | Build temporally ordered/anchored event histories | MODERATE | Usually no competing assessments or correction lineage |
| contradiction detection | Detect semantic incompatibility | STRONG | Contradiction must not be equated with supersession |
| natural language inference | Entailment/contradiction/neutral relation between texts | MODERATE | Standard NLI is pairwise and stateless |
| belief revision | Rational change of beliefs under new information | STRONG | Symbolic propositions are normally assumed |
| truth maintenance systems | Maintain beliefs plus reasons/dependencies under change | STRONG | Does not solve language interpretation |
| assumption-based truth maintenance | Maintain alternative consistent assumption environments | STRONG | Formal alternatives are not conversational update semantics |
| knowledge-base revision | Revise structured knowledge under additions or inconsistency | MODERATE | Often formal-complexity rather than NLP work |
| temporal knowledge graphs | Time-indexed facts and temporal reasoning | MODERATE | Modern results are often forecasting/link prediction |
| document supersession | One document replaces another authoritatively | WEAK | Document-level replacement is not proposition-level supersession |
| version supersession | Later artifact version replaces earlier version | WEAK | Version order does not prove semantic replacement |
| revision tracking | Align and classify edits across document versions | WEAK | Editing the text is not updating real-world work state |
| change detection | Generic detection of change between observations | REJECT | Overwhelmingly retrieves unrelated domains |
| provenance-aware state | State whose derivation/source is retained | MODERATE | Non-standard phrase; search provenance/lineage directly |
| event sourcing | Append-only state-changing event history with derived projections | STRONG | Solves persistence, not language semantics |

Standard dialogue state tracking is especially important as a false friend. In the mainstream task-oriented formulation, dialogue state normally consists of accumulated user goals, dialogue acts or slot-value information, not a provenance-backed proposition history. citeturn915016search0turn465477search17 It should therefore remain a TRANSFER mechanism unless a paper explicitly implements correction/revision semantics relevant to this project.

Likewise, generic NLI must be demoted. Standard NLI asks whether a hypothesis is entailed by, contradicted by or neutral with respect to a premise; it does not maintain a historical state across successive evidence. citeturn582938search1 Contradiction-specific research is still valuable as a component, including work that distinguishes types of textual contradiction, but contradiction cannot itself decide whether the later statement corrects, supersedes or merely disputes the earlier one. citeturn582938search0

Text-revision terminology is also dangerous. Corpora such as ArXivEdits and IteraTeR study revisions and edit intentions in writing; this can provide transfer evidence for semantic corrections or supplementation, but the changed text is not automatically evidence that a real-world work item changed state. citeturn941462search3turn941462search8

## Academic task families

### F01 — Source-relative event factuality and factuality profiling — DIRECT

**Capability:** determine whether a source commits to an event as actual, non-actual or uncertain, while representing whose perspective the factuality belongs to.

**Why it matters:** directly supports "mentioned ≠ factual" and source-relative factuality. FactBank is an especially important anchor because it represents event factuality relative to relevant discourse sources. citeturn514853search13

**Seed literature:**
- *A Factuality Profiler for Eventualities in Text* (Sauri, 2008). citeturn148079search2
- *FactBank: a corpus annotated with event factuality* (Sauri and Pustejovsky, 2009). citeturn514853search3
- *Neural Models of Factuality* (Rudinger et al., 2018). citeturn148079search8
- *Towards Generative Event Factuality Prediction* (Murzaku et al., 2023). citeturn148079search1

**Important limitation:** this family normally models **commitment expressed by a textual source**. It does not establish that the event was independently verified. That distinction remains central to gap 5.

### F02 — Event modality, polarity, speculation and conditionality — DIRECT

This family supplies the semantic primitives needed to keep intended, possible, conditional and negated actions from becoming factual completions. Negation/speculation corpora such as BioScope explicitly annotate uncertainty, negation and scope, but are primarily transfer evidence for workplace text because the empirical domain is biomedical. citeturn497035search0turn497035search5

### F03 — Temporal extraction, temporal relations and temporal constraint reasoning — DIRECT

This family should include:

- TimeML / TimeBank;
- TempEval;
- event-event and event-time temporal relation extraction;
- temporal closure and global consistency;
- Allen-style interval reasoning;
- explicit distinction between event time and document/message time.

TimeML and TimeBank are core terminology anchors, not merely historical curiosities. citeturn517637search0turn517637search1

### F04 — Cross-document event ordering and timeline extraction — DIRECT

Use this family to find methods that integrate temporal evidence across documents rather than treating each message independently.

The closest established task terminology is **cross-document event ordering / cross-document timelines**, including SemEval-2015 TimeLine. Its normal objective is chronologically anchoring events for an entity, which is useful but still short of preserving conflicting assessments. citeturn554706search46

### F05 — Dialogue commitment, correction, retraction, grounding and dispute semantics — DIRECT

This family should receive significantly more weight in round 2 than generic NLI.

Useful terminology:

- public commitment;
- commitment store / commitment slate;
- correction;
- retraction;
- acknowledgement;
- grounding;
- dispute;
- agreement;
- undenied commitment;
- discourse relation `Correction`.

Krabbe's work explicitly treats retraction as an operation whose permissibility and consequences depend on the kind of commitment and dialogue. citeturn599613search7 Lascarides and Asher distinguish participants' public commitments and provide a formal treatment of corrections and disputes. citeturn599613search1turn599613search10 Venant and Asher similarly use agent-specific commitment structures for acknowledgements and corrections. citeturn599613search3

This is the strongest candidate family for closing the semantic part of **gap 2**.

### F06 — Social commitment lifecycle and message semantics — TRANSFER

Social-commitment work models communicative actions that create and manipulate commitments, including states such as active, fulfilled, violated, rejected or cancelled. The vocabulary has a useful structural resemblance to requested/approved/completed/revoked work-item states. *Layered Message Semantics Using Social Commitments* is a known anchor. citeturn883525search7

However, formal agent-protocol messages are not naturally occurring workplace email. The family therefore remains TRANSFER unless a candidate actually evaluates natural-language operational communication.

### F07 — Contradiction detection, NLI and correction-sensitive discourse relations — TRANSFER

Use this family for **semantic incompatibility detection**, not for state resolution.

A correct architecture must permit:

```text
contradiction(A, B) = true
supersedes(B, A) = false
```

for example when two sources continue to disagree.

SDRT is useful because its inventory includes discourse relations such as Correction, Contrast and Elaboration rather than collapsing discourse divergence into one contradiction class. citeturn903181search0

### F08 — Belief revision, truth maintenance and argument revision — TRANSFER

This family supplies the non-destructive reasoning concepts needed after message semantics has been interpreted.

Important foundations include:

- Doyle's *A Truth Maintenance System* (1979);
- AGM belief revision (1985);
- de Kleer's *An Assumption-Based TMS* (1986).

TMS records reasons behind maintained beliefs and revises dependent conclusions when assumptions change. citeturn465477search0 ATMS is particularly attractive for unresolved conflict because incompatible alternatives can be maintained under different assumption environments rather than forcing an immediate destructive choice. citeturn465477search1

Formal dialogue research has also combined commitment retraction with argument revision to preserve consistency after withdrawal. citeturn599613search6

### F09 — Evidentiality, source attribution, corroboration and claim verification — TRANSFER

This is the most important new query family for **gap 5**.

Search must distinguish:

```text
Alice: "Deployment is complete."
```

from:

```text
Alice: "Deployment is complete."
monitoring evidence: successful deployment observed
independent operator: completion confirmed
```

Linguistic **evidentiality** concerns the source or mode of information—reported, observed, inferred and related distinctions. citeturn210152search1 Claim-verification work such as FEVER goes further by evaluating claims against evidence and distinguishing support, refutation and insufficient evidence. citeturn210152search16

Neither family alone is a direct solution: evidentiality is not verification, and fact checking usually does not model work-item lifecycle or speaker-relative commitments. Their intersection is nevertheless the strongest transfer vocabulary for assertion-versus-confirmation.

### F10 — Temporal knowledge graphs and evolving facts — TRANSFER

Keep this family, but apply a strict filter. Modern temporal-KG research frequently means forecasting or temporal link prediction rather than revision of an accepted fact. citeturn465477search12

Only retain papers that actually address changing validity, inconsistent temporal facts, correction, provenance or explicit update semantics.

### F11 — Temporal and bitemporal database semantics — TRANSFER

This family should be promoted specifically for **gap 7**.

The crucial terminology is:

- valid time;
- transaction time;
- bitemporal data;
- temporal databases;
- application time / system time;
- event time / processing time.

Snodgrass and Ahn's 1985 taxonomy was explicitly motivated by the inadequacy and confusion created by using only one temporal attribute for changing information. citeturn869908search46turn869908search4

For msgloom, there is not a one-to-one mapping, but the conceptual distinction is valuable:

```text
message time       = when the communication was uttered/sent
effective/event time = when the described state holds in the world
deadline time      = constraint imposed on the work item
observed/version time = when msgloom acquired this evidence/version
```

A bitemporal representation does not solve all four, but it gives the correct academic vocabulary for separating **world validity** from **system observation/history**.

### F12 — Data provenance, lineage and temporal provenance — TRANSFER

Promote **data provenance**, **lineage**, **why-provenance** and **where-provenance** over the vague seed phrase `provenance-aware state`.

Buneman, Khanna and Tan explicitly define provenance in terms of where stored data came from and distinguish source influence from source location. citeturn869908search0turn869908search1

This family is directly relevant to preserving:

```text
immutable source observation
        ↓
assessment v1
        ↓ new evidence
assessment v2
        ↓ correction
assessment v3

current_view = projection over assessments/evidence
```

It is representation evidence, not evidence that the correct natural-language revision relation can be inferred.

### F13 — Event sourcing and immutable state history — TRANSFER

Event sourcing is the strongest engineering analogue for **gap 8**. Its defining idea is to retain the sequence of state-changing events and derive state from that sequence rather than destructively replacing history. Contemporary engineering literature similarly describes event stores as historical records from which application state can be reconstructed. citeturn538303search0turn538303search1

It should therefore inform implementation experiments, but no event-sourcing paper should be allowed to masquerade as evidence that NLP can distinguish correction from contradiction.

### F14 — Text revision, edit intention and document-version change — TRANSFER

Search this family only with qualifiers such as:

- factual correction;
- semantic change;
- edit intention;
- supplementation;
- sentence alignment across revisions.

ArXivEdits and IteraTeR are useful transfer datasets for understanding revision operations. citeturn941462search3turn941462search8

They do **not** establish that later wording supersedes earlier real-world evidence.

### F15 — Workplace and operational communication work-item lifecycle tracking — DIRECT

This is the **target-domain discovery family**, and it has no confident canonical seed paper from the terminology audit.

A candidate only counts as direct evidence if it follows the same work item across multiple workplace or comparable operational messages and evaluates state changes such as:

- proposed → approved;
- planned → cancelled;
- approved → revoked;
- deadline A → deadline B;
- asserted complete → disputed;
- asserted complete → independently confirmed;
- resolved → reopened;
- conflicting observations → unresolved.

A paper that merely extracts an action item from an email is Topic 05 evidence, not Topic 06 evidence.

### F16 — Dialogue issue management / Questions Under Discussion — TRANSFER

QUD and issue-management literature treats dialogue as raising and resolving issues, and therefore supplies potentially useful vocabulary for **open**, **unresolved** and **resolved** conversational objects. Experimental work explicitly studies whether later discourse resolves a QUD. citeturn903181search3

This should be searched as a transfer family for the `reopened` and `still unresolved` portions of gap 2. A QUD is not automatically the same object as a work item, so evidence must remain transfer-labelled.

## Query families

### F01 — DIRECT: source-relative factuality

```text
"event factuality" source attribution commitment holder
"event factuality prediction" source target holder
"factuality profiling" event source commitment
"source-relative" event factuality NLP
"event factuality" temporal update contradiction
"event factuality" cross-document longitudinal
```

### F02 — DIRECT: modality, negation and conditionality

```text
event modality negation conditionality factuality NLP
speculation negation scope event factuality
"conditional commitment" modality dialogue
planned completed event modality status text
event actuality hypothetical intended completed NLP
```

### F03 — DIRECT: temporal extraction and reasoning

```text
"temporal relation extraction" event ordering global consistency
TimeML temporal relation event time
"temporal constraint reasoning" events intervals
"temporal closure" temporal relation extraction
"Allen interval algebra" event temporal reasoning
"event time" "document creation time" temporal relation NLP
```

### F04 — DIRECT: longitudinal/cross-document timelines

```text
"cross-document" event ordering timeline extraction
"cross-document timeline" event correction contradiction
"timeline extraction" event factuality
"cross-document event ordering" temporal
longitudinal event timeline update correction text
```

### F05 — DIRECT: commitment, correction, retraction and dispute

```text
"grounding" "correcting commitments" dialogue
"commitment" correction retraction dialogue semantics
"public commitments" dispute correction dialogue
"commitment store" retraction dialogue
"discourse relation" Correction dialogue
dialogue retraction unresolved dispute commitment
"agreement disputes commitment" dialogue
"correction" acknowledgement commitment dialogue
```

This family should be prioritized for gap 2 before another generic contradiction/NLI search.

### F06 — TRANSFER: social-commitment lifecycle

```text
"social commitment" lifecycle fulfilled cancelled violated
"commitment state" fulfilled cancelled agent communication
commitment discharge cancellation multiagent communication
"message semantics" "social commitments"
"commitment lifecycle" communication protocol
"social commitment" adoption fulfilment cancellation
```

### F07 — TRANSFER: contradiction/NLI

```text
"contradiction detection" temporal context dialogue
"natural language inference" contradiction temporal context
"contradiction" correction discourse relation
NLI revision update longitudinal dialogue
"temporal contradiction" natural language inference
"correction relation" contradiction discourse
```

### F08 — TRANSFER: belief revision/TMS

```text
"belief revision" iterated revision new evidence
"truth maintenance system" justification contradiction retraction
"assumption-based truth maintenance" inconsistent evidence
"argument revision" commitment retraction dialogue
"non-monotonic reasoning" provenance belief revision
"belief revision" natural language dialogue evidence
"iterated belief revision" conflicting information
```

### F09 — TRANSFER: evidential confirmation

```text
"event factuality" evidentiality source attribution
evidentiality information source reported inferred witnessed NLP
"claim verification" evidence retrieval source provenance
"fact verification" temporal claims evidence
"multi-source" claim verification corroboration
corroboration independent evidence claim verification NLP
"source attribution" factuality evidence NLP
```

These queries explicitly target the missing distinction between **asserted completion** and **evidentially confirmed completion**.

### F10 — TRANSFER: temporal knowledge graphs

```text
"temporal knowledge graph" fact update contradiction
"temporal knowledge graph" revision provenance
"temporal knowledge graph" evolving facts validity
"knowledge graph" temporal fact revision
"knowledge graph" conflicting temporal facts provenance
```

### F11 — TRANSFER: multi-time / bitemporal semantics

```text
"valid time" "transaction time" temporal database
bitemporal database valid time transaction time
bitemporal data provenance version history
"event time" "processing time" stream processing
"temporal database" retroactive correction history
"application time" "system time" temporal database
```

This is the principal gap-7 family.

### F12 — TRANSFER: provenance and lineage

```text
"data provenance" lineage derivation historical state
"temporal provenance" database updates
provenance conflicting evidence knowledge base
"why provenance" "where provenance"
"data lineage" historical state revision
provenance belief revision evidence
```

### F13 — TRANSFER: event sourcing

```text
"event sourcing" immutable history state reconstruction
"event sourcing" temporal state evolution
"event sourcing" audit trail correction
"event sourcing" historical state projection
"event sourcing" schema evolution
```

### F14 — TRANSFER: textual revision semantics

```text
"revision intent" correction supplementation text
"edit intention" factual correction revision
"document revision" semantic change correction
"sentence alignment" document revisions correction
"version history" factual correction NLP
"text revision" factual correction supplementation
```

### F15 — DIRECT: workplace/operational state tracking

```text
"business email" action status completion cancellation NLP
"workplace email" commitment state tracking
"email thread" task status change deadline correction
"operational communication" action item lifecycle NLP
"enterprise dialogue" task status completion revocation
"workplace communication" contradiction correction task status
"email" commitment cancellation completion longitudinal
"meeting dialogue" action item status change
```

This family should use strict admission. Generic action extraction, email importance prediction or thread summarization does not qualify.

### F16 — TRANSFER: open/resolved/reopened dialogue issues

```text
"questions under discussion" unresolved dialogue
"issue management" dialogue open resolved
dialogue issue reopening resolved question
"unresolved issue" dialogue state
"conversational scoreboard" to-do list task
"question under discussion" resolution non-resolution
```

## Promoted terminology

The round-2 vocabulary should promote the following concepts over the original broad seeds:

- **source-relative event factuality**, **factuality holder**, **source commitment**;
- **public commitment**, **commitment store**, **commitment retraction**;
- **grounding**, **dispute**, **acknowledgement**, **Correction discourse relation**;
- **social commitment lifecycle**, **fulfilment**, **cancellation**, **violation**;
- **iterated belief revision**, **argument revision**, **truth maintenance**;
- **temporal closure**, **global temporal consistency**, **Allen interval algebra**;
- **cross-document event ordering** rather than generic event evolution;
- **evidentiality**, **source attribution**, **corroboration**, **multi-source claim verification**;
- **bitemporal database**, **valid time**, **transaction time**, **event time**, **processing time**;
- **data provenance**, **lineage**, **why-provenance**, **where-provenance**, **temporal provenance**;
- **event sourcing**, **immutable event history**, **state projection**;
- **revision/edit intention** only when explicitly tied to semantic or factual correction;
- **Questions Under Discussion / issue resolution** for open and unresolved dialogue state.

## False friends and downgrade rules

1. **Dialogue state tracking is not work-item factual state tracking.** Ordinary slot/value belief states should be downgraded unless they explicitly represent correction, retraction and preserved history.

2. **Contradiction is not supersession.** A pairwise contradiction detector can supply an input relation but cannot decide whether the conflict remains unresolved, one source retracts its claim, or a later statement authoritatively replaces an earlier one.

3. **Recency is not supersession.** Reject any implicit `latest message wins`, `latest timestamp wins` or `newest version wins` assumption as evidence for semantic supersession.

4. **Event factuality is not independent verification.** A factuality label can express that a source strongly commits to "completed"; that does not establish that completion has been corroborated.

5. **Certainty is not classifier confidence.** Search results about calibration, predictive confidence or uncertainty quantification should not be admitted as event-certainty evidence.

6. **Temporal IE is not date extraction.** Pure recognition/normalization of dates and times should be excluded unless events and their temporal relations are represented.

7. **A timeline is not a revision history.** Chronologically ordering events does not preserve competing assessments, corrections or unresolved conflict.

8. **Event evolution is usually the wrong object.** Topic/storyline evolution should not be admitted as evidence for evolution of one persistent work item's state.

9. **Temporal KGs require a revision filter.** Link prediction and event forecasting do not count as fact revision merely because timestamps are present.

10. **Document version order is not semantic authority.** A later document/version can supplement rather than supersede earlier material.

11. **Writing revision is not world-state revision.** Grammar, fluency, simplification and stylistic editing are false positives for gap 2.

12. **Generic change detection is rejected.** Computer vision, remote sensing, sensor change-point detection, source-code diffs and similar literature should never enter this corpus merely because the phrase matches.

13. **Formal social commitments remain transfer evidence** when messages are symbolic protocol actions rather than naturally occurring language.

14. **Belief revision/TMS begins after interpretation.** It can specify what to do with conflicting propositions but does not prove an NLP system can identify the correct propositions or update relation.

15. **Fact checking remains transfer evidence** unless it jointly models source-relative assertion, evidence provenance and longitudinal state.

16. **Evidentiality is not verification.** Marking information as reported, inferred or observed is useful, but it is not equivalent to corroborating that the work was actually completed.

17. **Event sourcing/provenance cannot close language-semantic gaps.** They address storage, lineage and reconstruction, not linguistic judgment.

18. **Structured workflow state machines are not direct evidence** when statuses are supplied by a workflow engine rather than inferred under language uncertainty.

19. **Action extraction belongs to Topic 05.** A paper that identifies requests, commitments or deadlines but does not follow later state change should not be used to close Topic 06.

20. **Topic identity remains Topic 03.** Event coreference or cross-thread identity may be required as a controlled prerequisite, but Topic 06 must not claim that identity research solves state transition semantics.

21. **Update summarization belongs downstream.** A paper that summarizes "what changed" without defining evidence-backed truth/state resolution is Topic 09-like evidence, not Topic 06 state semantics.

22. **Process mining from structured logs is transfer evidence only.** Lifecycle models can inform representation, but structured status logs remove the core natural-language ambiguity.

23. **Gap 1 closure requires genuinely longitudinal evaluation:** multiple observations concerning the same work item plus at least one evaluated state transition. Single-message status classification is insufficient.

24. **Gap 2 closure requires explicit relational semantics:** at least two of correction, supplementation, contradiction, retraction, supersession, reopening or unresolved conflict must be separately represented or evaluated.

25. **Gap 3 cannot be closed compositionally by citation.** Finding one factuality paper, one temporal paper, one contradiction paper and one provenance paper does not establish a jointly evaluated longitudinal model.

26. **Gap 4 requires real target-domain evidence.** Workplace email, enterprise chat, meeting dialogue or closely comparable operational communication must be evaluated. News, biomedical, synthetic and formal-agent domains remain explicitly TRANSFER.

27. **Gap 5 requires evidence stronger than speaker commitment.** Search should actively prefer corroboration, evidence retrieval, multi-source verification and provenance.

28. **Gap 6 is primarily engineering after terminology closure.** Adversarial plan→cancel, approve→revoke, changed-deadline, out-of-order and stale-message sequences need controlled fixtures even if no paper supplies the exact benchmark.

29. **Gap 7 requires typed time dimensions.** A method exposing only one timestamp cannot substantiate the product's message/effective/deadline/observation-time contract.

30. **Gap 8 requires non-destructive lineage.** A correct final state is insufficient if source observations or prior assessments were overwritten.

## Date policy

**Earliest publication year for bulk discovery: 1979.**

A recent-only search would silently discard several of the foundations that define the mechanisms this project needs.

The lower bound is driven first by Jon Doyle's **1979 truth-maintenance work**, which established reason/dependency maintenance for beliefs subject to revision. citeturn465477search0 The immediately relevant foundation sequence then includes:

- Allen's temporal-interval reasoning in the early 1980s;
- AGM belief revision in 1985; citeturn537378search6
- Snodgrass and Ahn's temporal-database taxonomy in 1985; citeturn869908search46
- de Kleer's assumption-based TMS in 1986; citeturn465477search1
- formal commitment/retraction dialogue work in the 1990s and early 2000s; Walton and Krabbe's 1995 framework, for example, explicitly addresses when commitments may be retracted; citeturn599613search5
- modern database provenance from 2001; citeturn869908search0
- TimeML and TimeBank from 2003 onward. citeturn517637search0turn517637search1

Therefore discovery should use **1979 as the global floor**, while ranking recent empirical NLP highly within each family. Citation chaining from admitted foundational work may go earlier when it reveals a directly relevant precursor; the 1979 floor is a discovery policy, not a claim that no relevant intellectual precursor existed before that year.
