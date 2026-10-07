# Direct empirical NLP methods for longitudinal work-item revision in workplace or operational communication academic terminology analysis

## Product problem

The target problem is not generic event extraction and not generic summarization. It is a longitudinal evidence-resolution problem over repeated natural-language observations about the same work item.

The desired system must preserve at least four logically distinct layers:

1. **Source observation:** what a particular message or attachment actually says.
2. **Source-relative interpretation:** whether that source presents an event as requested, planned, conditional, complete, negated, disputed, uncertain, and so forth.
3. **Revision relation:** how a new observation relates to earlier observations about the same work item: supplementation, correction, supersession, revocation, reopening, contradiction, or unresolved conflict.
4. **Derived assessment:** the current evidence-backed state, together with the complete lineage that explains why the current assessment differs from previous assessments.

The terminology audit therefore needs to prevent several common collapses:

- factuality into truth;
- later timestamp into supersession;
- contradiction into correction;
- changed wording into changed state;
- a completion assertion into verified completion;
- event chronology into lifecycle semantics;
- current state into destructive replacement of historical evidence.

The most important search refinement is to combine several established academic vocabularies rather than assume that one existing task name denotes the complete problem. The strongest established components are event factuality/source commitment, temporal relation extraction, contradiction/NLI, belief revision/truth maintenance, provenance, and revision classification. The closest direct target terminology is **longitudinal work-item revision relation classification**, but this does not appear to be a single mature canonical NLP task name and should therefore be searched through multiple neighboring vocabularies.

## Seed keyword audit

| Seed | Academic meaning | Fit | Main risk |
| --- | --- | --- | --- |
| event factuality prediction | Predict whether a source commits to occurrence/non-occurrence or expresses uncertainty about an event. | STRONG | Source commitment is not independent truth, and most evaluations are not longitudinal. |
| factuality profiling | Loosely used for aggregating or characterizing factuality-related properties. | WEAK | Not a stable task name; attracts source, document, misinformation, or credibility profiling. |
| event modality | Identify modal status such as possible, intended, obligatory, hypothetical, or conditional. | STRONG | Describes utterance-time status but not later completion, revocation, or supersession. |
| event certainty | Estimate expressed certainty concerning an event or proposition. | MODERATE | Certainty is not factuality, evidence strength, or lifecycle state. |
| event veridicality | Determine whether linguistic context commits a source to the truth/occurrence of an event. | STRONG | Usually source-relative and sentence/document-local rather than longitudinal. |
| negation detection | Detect negation and its semantic scope. | MODERATE | Negation is only one dimension of state and does not distinguish cancellation, correction, or revocation. |
| speculation detection | Detect speculative or uncertain propositions/events. | MODERATE | Captures uncertainty but not revision semantics. |
| hedging detection | Detect linguistic weakening or qualification of commitment. | MODERATE | Surface hedging cannot establish lifecycle state or independent evidence. |
| temporal information extraction | Extract events, temporal expressions, normalized times, and temporal relations. | MODERATE | Broad term attracts date extraction with no event-state reasoning. |
| temporal relation extraction | Infer BEFORE/AFTER/SIMULTANEOUS and related temporal relations. | STRONG | Temporal precedence does not imply supersession or validity. |
| event temporal ordering | Construct chronology or partial ordering among events. | STRONG | Ordering does not identify correction, supplementation, or supersession. |
| temporal relation classification | Classify event/time pairs into temporal relation categories. | STRONG | Usually pairwise and lacks source, provenance, and lifecycle semantics. |
| TimeML | Annotation framework for events, times, signals, and temporal links. | MODERATE | Representation scheme rather than a state-resolution method. |
| temporal graphs | Represent temporal entities and relations as globally constrained graphs. | STRONG | Temporal consistency does not resolve semantic or evidential conflict. |
| temporal constraint reasoning | Propagate/check temporal constraints, frequently through interval or point algebra. | STRONG | Time consistency alone cannot resolve competing factual claims. |
| event status tracking | Track changing labels or status of events/processes. | MODERATE | Not a stable NLP term and attracts workflow/monitoring systems. |
| state tracking | Maintain changing system state from observations. | WEAK | Extremely broad across dialogue, robotics, process control, and probabilistic estimation. |
| dialogue state tracking | Maintain slot/value or goal beliefs across turns in task-oriented dialogue. | WEAK | Canonical DST semantics differ substantially from provenance-preserving work-item state. |
| event evolution | Model development of an event across documents or time. | MODERATE | Often means story development rather than semantic revision of the same item. |
| event update | Update an event representation when new information arrives. | WEAK | Ambiguous; attracts update summarization, stream processing, and databases. |
| timeline extraction | Extract and chronologically organize events. | MODERATE | Usually orders events without maintaining changing validity assessments. |
| contradiction detection | Identify mutually incompatible textual propositions. | STRONG | Contradiction is not equivalent to supersession or correction. |
| natural language inference | Classify premise/hypothesis relations such as entailment, contradiction, neutral. | MODERATE | Standard NLI removes source, temporal, provenance, and historical context. |
| belief revision | Formally change a belief set when evidence is added, contradicted, or withdrawn. | STRONG | Usually symbolic rather than empirical NLP. |
| truth maintenance systems | Maintain conclusions and their justifications as evidence changes. | STRONG | Excellent transfer semantics, but generally no natural-language interpretation. |
| assumption-based truth maintenance | Maintain alternative supporting assumption environments for conclusions. | STRONG | Logical assumptions are not uncertain language-derived observations. |
| knowledge-base revision | Revise structured knowledge under additions, deletions, and inconsistency. | MODERATE | Often assumes propositions have already been normalized. |
| temporal knowledge graphs | Represent and reason over time-indexed/evolving structured relations. | MODERATE | Common benchmarks focus on link prediction rather than evidence provenance. |
| document supersession | A document formally replaces another document or record. | MODERATE | Often legal/records metadata rather than inferred semantic relations. |
| version supersession | One explicit artifact version replaces another. | MODERATE | Explicit version ordering is much easier than message-level semantic supersession. |
| revision tracking | Record successive versions and edits, sometimes including edit purpose. | MODERATE | Usually explicit document versions rather than distributed workplace communication. |
| change detection | Detect differences between observations or versions. | WEAK | Surface difference does not establish semantic state change. |
| provenance-aware state | State representation retaining origin/derivation information. | MODERATE | Descriptive phrase rather than canonical NLP task; attracts database infrastructure. |
| event sourcing | Store immutable events and derive current state through projections/replay. | MODERATE | Engineering architecture, not a method for correctly interpreting language. |

### Terms to promote

The following terminology should receive more weight than the raw seeds:

- **source-sensitive event factuality**
- **speaker commitment / source commitment**
- **event veridicality**
- **epistemic modality**
- **evidentiality**
- **source attribution**
- **claim verification**
- **evidence retrieval**
- **independent corroboration**
- **revision relation classification**
- **update relation classification**
- **semantic revision classification**
- **edit intent classification**
- **revision purpose classification**
- **dialogue repair**
- **commitment tracking / commitment retraction**
- **temporal closure**
- **temporal constraint propagation**
- **cross-document temporal relation extraction**
- **valid time**
- **transaction time**
- **effective time**
- **observation time**
- **bitemporal data**
- **data provenance / data lineage**
- **immutable observations**
- **derived current-state view**
- **non-monotonic reasoning**
- **justification-based truth maintenance**
- **dynamic knowledge graph**

### Terms to demote

These terms should not be used alone because their academic meaning is either too broad or substantially different from the msgloom requirement:

- factuality profiling
- state tracking
- dialogue state tracking
- event update
- change detection
- event status tracking
- event sourcing

## Academic task families

### F1 — Longitudinal work-item revision relation classification — DIRECT

The core direct task is to classify the semantic relationship between successive communications concerning the same underlying work item.

Required relation distinctions include:

- supplementation;
- correction;
- supersession/replacement;
- revocation/cancellation;
- reopening;
- contradiction;
- unresolved conflict.

It must additionally maintain the history rather than rewriting an earlier observation.

This family is the primary search target for gaps 1, 2, and 4. No canonical seed paper is listed because a paper should not be implied to directly solve this task unless its evaluation genuinely covers longitudinal operational communication.

Particularly valuable target domains are:

- workplace/business email;
- enterprise chat;
- incident-management communication;
- issue trackers;
- operational support communication;
- task/project collaboration records.

These adjacent operational domains are preferable to news when direct email or Teams-like evidence is unavailable.

### F2 — Event factuality, veridicality, modality, and speaker commitment — TRANSFER

This family determines what status a source assigns to an event at the time of an utterance.

Relevant distinctions include:

- asserted actual;
- negated;
- possible;
- uncertain;
- hypothetical;
- intended;
- planned;
- conditional.

Known seed papers:

- Saurí and Pustejovsky (2009), *FactBank: a corpus annotated with event factuality*.
- de Marneffe, Manning, and Potts (2012), *Did It Happen? The Pragmatic Complexity of Veridicality Assessment*.

The critical transfer limitation is that factuality usually represents **source commitment**, not independent verification.

### F3 — Source attribution, evidentiality, and evidence-based claim verification — TRANSFER

This family should be searched aggressively for gap 5.

The desired conceptual structure is:

`source A asserts completion`
≠
`another source corroborates completion`
≠
`available evidence independently verifies completion`.

Search should therefore combine:

- source attribution;
- factuality;
- evidentiality;
- claim verification;
- evidence retrieval;
- corroboration;
- provenance;
- multiple sources.

Known seeds include FactBank for attributed factuality and FEVER for evidence-based claim verification. Neither should be assumed to solve the combined longitudinal workplace problem.

### F4 — Temporal relation extraction and temporal constraint reasoning — TRANSFER

The system needs temporal semantics richer than message chronology.

Relevant times are:

- message/utterance time;
- event/effective time;
- deadline/constraint time;
- collection/observation/version time.

Known foundations and seeds:

- Allen (1983), *Maintaining Knowledge about Temporal Intervals*.
- Pustejovsky et al. (2003), *TimeML: Robust Specification of Event and Temporal Expressions in Text*.
- Chambers and Jurafsky (2008), *Jointly Combining Implicit Constraints Improves Temporal Ordering*.

This family is essential because a newer message may describe an older event and a late-ingested message may itself be older than evidence already processed.

### F5 — Event evolution, temporal event aggregation, and timeline construction — TRANSFER

This family connects repeated descriptions of evolving events across documents.

It is useful only where successive mentions can be associated with the same continuing event or state history. Simple story timelines are insufficient.

Discovery should test whether papers represent:

- event identity through time;
- status changes;
- corrections;
- replaced information;
- conflicting observations.

### F6 — Contradiction, entailment, and semantic consistency — TRANSFER

Relevant known work includes:

- de Marneffe, Rafferty, and Manning (2008), *Finding Contradictions in Text*.
- Dagan, Glickman, and Magnini (2006), *The PASCAL Recognising Textual Entailment Challenge*.

This literature can identify incompatible statements but should not be allowed to collapse the following:

`contradiction ≠ correction ≠ supersession`.

Example:

- "Deadline is Friday."
- "Deadline is Monday."

These may represent a deadline change, a contradiction, a correction, two time-scoped constraints, or unresolved disagreement depending on source and context.

### F7 — Dialogue commitment and belief-state tracking — TRANSFER

The useful portion of dialogue research is not primarily slot-value DST. It is work on:

- public commitments;
- conversational commitment;
- belief updates;
- retractions;
- corrections;
- dialogue repair.

Williams et al. (2013), *The Dialog State Tracking Challenge*, is a known DST reference, but canonical DST should normally be treated only as transfer because its maintained state differs from an evidence-preserving work-item lifecycle.

### F8 — Belief revision and truth-maintenance reasoning — TRANSFER

Foundational papers include:

- Doyle (1979), *A Truth Maintenance System*.
- Alchourrón, Gärdenfors, and Makinson (1985), *On the Logic of Theory Change: Partial Meet Contraction and Revision Functions*.
- de Kleer (1986), *An Assumption-based TMS*.

These are highly relevant to msgloom's rule that new evidence should create a new assessment without deleting the old evidence.

A useful conceptual mapping is:

`immutable source observation`
→ `interpretation`
→ `support/justification graph`
→ `current assessment`.

When an assumption or interpretation changes, the current assessment can change while its history remains explainable.

This is strong architectural and formal transfer evidence, but not direct NLP evidence.

### F9 — Document revision, edit-intent classification, and semantic change — TRANSFER

Search terminology should include:

- edit intent classification;
- revision purpose classification;
- semantic revision;
- correction/addition/deletion classification.

A known seed is:

- Daxenberger and Gurevych (2013), *Automatically Classifying Edit Categories in Wikipedia Revisions*.

This family is potentially useful because it models the semantic purpose of a revision rather than merely computing a text diff.

However, document versions generally provide explicit identity and order, whereas workplace messages require Topic identity and revision relation inference.

### F10 — Dynamic and temporal knowledge-graph update — TRANSFER

Relevant work represents facts changing through time in a structured graph.

Known seed:

- Trivedi et al. (2017), *Know-Evolve: Deep Temporal Reasoning for Dynamic Knowledge Graphs*.

This can inform representation of changing facts but should be downgraded when facts are already canonicalized and the benchmark measures only link prediction or forecasting.

### F11 — Data provenance, immutable observations, and derived current-state views — TRANSFER

A useful foundational reference is:

- Buneman, Khanna, and Tan (2001), *Why and Where: A Characterization of Data Provenance*.

This family addresses a central msgloom requirement:

`source evidence` must not be overwritten by `current assessment`.

The implementation should conceptually distinguish:

- immutable observations;
- extracted interpretations;
- assessment versions;
- dependency/provenance edges;
- materialized current state.

Event sourcing is useful terminology for the implementation pattern but should not be treated as an NLP method.

### F12 — Multi-time and bitemporal representation — TRANSFER

For the engineering gaps, discovery should additionally search temporal-database terminology:

- valid time;
- transaction time;
- effective time;
- observation time;
- bitemporal data.

The standard bitemporal distinction is particularly useful:

- **valid time:** when a fact is supposed to hold in the represented world;
- **transaction time:** when the database knew or stored it.

msgloom requires an expanded version because it also needs to distinguish the message timestamp and deadlines/constraints.

## Query families

### F1 — DIRECT: longitudinal work-item revision relations

```text
"work item" longitudinal revision classification email supersession correction supplementation reopening conflict
"task status" email longitudinal revision correction cancellation completion reopening
"action item" email thread status change completion cancellation correction
"workplace email" task lifecycle requested planned approved completed revoked superseded
"enterprise chat" task status update correction cancellation completion
"operational communication" state tracking revision contradiction supersession
"issue tracker" natural language status update correction reopen close supersede
"incident management" communication revision status update correction resolution reopen
"message" "supersedes" correction supplementation contradiction task status NLP
"revision relation" messages supersession correction supplementation retraction reopening
```

High-value domain-specific retries:

```text
"workplace email" supersession correction supplementation contradiction
"business email" deadline change correction cancellation completion
"email thread" task status correction completion cancellation
"enterprise communication" work item lifecycle NLP
"workplace communication" event factuality temporal revision
"Teams" task status correction completion NLP
"Slack" task status update correction NLP
"operational messages" task state revision NLP
```

### F2 — TRANSFER: factuality and source commitment

```text
"event factuality" source commitment longitudinal
"event factuality prediction" source attribution temporal
"event veridicality" source attribution event status
"event modality" factuality intention completion negation
"speaker commitment" event factuality dialogue
"source commitment" factuality NLP event
epistemic modality event factuality conditional planned completed
"factuality" correction retraction event
```

Gap-3 combination queries:

```text
"event factuality" temporal relation contradiction joint model
"factuality" "temporal relation extraction" joint
"event factuality" provenance source temporal
"event factuality" lifecycle state
"factuality" contradiction temporal ordering source
```

### F3 — TRANSFER: assertion versus corroboration

```text
"source attribution" factuality evidence corroboration NLP
"speaker commitment" independent evidence verification
"claim verification" source attribution corroborating evidence temporal
"fact verification" multiple sources provenance claim evidence
"evidence attribution" claim verification provenance NLP
"evidentiality" source attribution event factuality NLP
"independent corroboration" claim verification NLP
"source independence" corroboration claim verification
"event factuality" "fact verification" source
"completion" claim corroboration evidence task NLP
```

Gap-5 precision queries:

```text
"claimed completion" verification evidence
"completion claim" independent verification
"task completion" evidence verification natural language
"asserted completion" corroboration
"reported completion" evidence provenance
"completion status" source attribution evidence
```

### F4 — TRANSFER: temporal relations and constraints

```text
"temporal relation extraction" event ordering cross-document
"event temporal ordering" cross-document update
"temporal relation classification" discourse events
"temporal graph" event ordering consistency NLP
"temporal closure" event relations NLP
"temporal constraint reasoning" natural language events
TimeML cross-document temporal relations
"document creation time" event time temporal relation extraction
"event time" "message time" NLP temporal
"effective time" natural language event temporal extraction
```

### F5 — TRANSFER: event evolution and timelines

```text
"event evolution" NLP cross-document
"event evolution" news timeline state change
"event tracking" cross-document temporal NLP
"event timeline extraction" cross-document
"timeline extraction" evolving events NLP
"event update" cross-document semantic revision
"event progression" NLP temporal
"event history" natural language temporal
```

### F6 — TRANSFER: contradiction and NLI

```text
"contradiction detection" temporal information source attribution
"textual contradiction" temporal contradiction NLP
"natural language inference" temporal contradiction
"natural language inference" source attribution contradiction
"contradiction" correction supersession NLP
"entailment" correction retraction dialogue
"temporal NLI" contradiction events
"fact consistency" revisions contradiction text
```

### F7 — TRANSFER: dialogue commitment revision

```text
"dialogue commitment" retraction correction
"commitment tracking" dialogue retraction
"public commitments" dialogue revision
"dialogue state" correction retraction belief update
"belief tracking" dialogue correction contradiction
"dialogue repair" correction retraction commitment
"conversational commitment" update retraction
"commitment store" dialogue correction
```

### F8 — TRANSFER: belief revision and truth maintenance

```text
"belief revision" natural language evidence
"belief revision" source reliability temporal
"belief revision" dialogue contradiction
"truth maintenance system" conflicting evidence provenance
"truth maintenance" retraction justification provenance
"assumption-based truth maintenance" conflicting evidence
"belief revision" provenance temporal information
"non-monotonic reasoning" conflicting reports source
```

### F9 — TRANSFER: revision purpose and semantic edit classification

```text
"edit intent classification" document revisions
"revision purpose classification" NLP
"semantic edit classification" document revision
"document revision" correction addition deletion classification NLP
"revision classification" Wikipedia correction clarification addition
"document supersession" semantic revision NLP
"version comparison" semantic change NLP
"document change" correction supersession natural language
```

### F10 — TRANSFER: dynamic and temporal knowledge

```text
"temporal knowledge graph" fact update contradiction
"dynamic knowledge graph" evolving facts provenance
"temporal knowledge graph" provenance source
"knowledge graph update" contradictory information source
"knowledge base revision" temporal provenance
"dynamic knowledge graph" event state change
"temporal knowledge graph" validity interval fact
```

### F11 — TRANSFER: provenance and immutable history

```text
"data provenance" derived state source evidence
"provenance" belief revision evidence lineage
"provenance-aware" state history
"immutable event log" derived state provenance
"event sourcing" provenance current state projection
"provenance" temporal database changing facts
"data lineage" temporal assertions source
"provenance semiring" conflicting information
```

### F12 — TRANSFER: multiple notions of time

```text
"bitemporal" natural language events provenance
"valid time" "transaction time" event data
"valid time" "event time" "transaction time"
"effective time" "transaction time" temporal database
"event time" "ingestion time" provenance
"observation time" temporal database provenance
"assertion time" "valid time" temporal information
"bi-temporal" knowledge base changing facts
```

## False friends and downgrade rules

Discovery should apply the following rules before admitting results as direct evidence.

1. **Pure temporal expression extraction is insufficient.** A paper finding dates but not relating them to events or revisions does not address the target capability.

2. **Canonical dialogue state tracking is normally a false friend.** Slot/value or goal tracking should remain TRANSFER unless the benchmark actually tracks persistent evidence-backed work-item states and revisions.

3. **Generic NLI is insufficient.** A sentence-pair contradiction label without source, time, history, or provenance does not solve longitudinal state resolution.

4. **Event factuality must not be interpreted as verification.** "The author asserts that X happened" and "X has been independently established" are different propositions.

5. **Fact verification alone is insufficient for gap 5.** Verification literature is relevant to corroboration, but only a method that retains the originating assertion and distinguishes it from corroborating evidence addresses the full requirement.

6. **Topic 05 extraction must not be re-admitted as Topic 06 state tracking.** Detecting a request, commitment, deadline, or decision in one message does not determine whether that event later remains valid.

7. **Update summarization is not revision reasoning.** Identifying what is new does not determine whether an earlier statement was corrected, superseded, supplemented, revoked, or remains valid.

8. **Latest-message-wins is explicitly invalid.** Chronological recency is evidence about observation order, not semantic supersession.

9. **Workflow state machines are not direct NLP evidence.** If transitions are already structured system events, the hard language-understanding problem has been bypassed.

10. **Process mining should be downgraded unless natural-language communication is the source of inferred state.**

11. **Document diffs are insufficient.** Insert/delete/change operations need a semantic interpretation to establish correction or supersession.

12. **Software version supersession is not message supersession.** Explicit version identifiers provide a deterministic relationship that workplace discourse usually lacks.

13. **Formal legal supersession metadata is not equivalent to inferred linguistic supersession.**

14. **Temporal knowledge-graph completion is not longitudinal evidence reasoning when all facts are already normalized and trusted.**

15. **BEFORE/AFTER is not a lifecycle relation.** A temporal classifier can support the model without deciding validity.

16. **An ordered timeline is not a changing assessment history.** Discovery should inspect whether repeated mentions of the same item can alter the state attached to that item.

17. **News-event evolution should remain TRANSFER unless semantic revision relations are explicitly evaluated.**

18. **Belief revision, TMS, and ATMS are formal transfer foundations, not empirical evidence of workplace NLP accuracy.**

19. **Provenance databases and event-sourcing implementations are engineering transfer literature.** They solve storage/lineage after interpretation, not interpretation itself.

20. **Destructive overwrite is incompatible with the target evidence model.** A method that cannot reconstruct previous observations and previous assessments should not be counted as satisfying the provenance requirement.

21. **Gap 1 and gap 2 require genuinely successive communications.** Label names alone do not count. A paper must operate over multiple observations of the same underlying item.

22. **Gap 4 requires an operational communication domain.** News-only results can supply transfer mechanisms but cannot establish workplace performance.

23. **Gap 5 requires a claim/evidence distinction.** Confidence, factuality, or entailment alone is not independent confirmation.

24. **Gap 3 requires an actual joint representation or evaluation.** A system does not close the gap merely because separate components for temporal extraction, factuality, contradiction, and provenance appear somewhere in its pipeline.

25. **Later-message ≠ superseding-message.** Direct methods should need semantic, referential, temporal, or explicit revision evidence.

26. **Do not collapse all changes into one CHANGE class.** At minimum discovery should inspect whether the method distinguishes correction, supersession, supplementation, contradiction, revocation/retraction, reopening, and unresolved conflict.

## Date policy

**Earliest year to include: 1979.**

A recent-only search would silently exclude several foundations directly relevant to the target representation.

The earliest necessary foundation identified here is:

- **1979:** Doyle, *A Truth Maintenance System*.

Other early foundations follow closely:

- **1983:** Allen, *Maintaining Knowledge about Temporal Intervals*.
- **1985:** Alchourrón, Gärdenfors, and Makinson, *On the Logic of Theory Change: Partial Meet Contraction and Revision Functions*.
- **1986:** de Kleer, *An Assumption-based TMS*.

The empirical NLP branches become much more visible in the 2000s:

- TimeML and modern temporal annotation;
- recognizing textual entailment;
- textual contradiction detection;
- event factuality corpora and models;
- later temporal graph, fact-verification, dynamic-KG, and neural inference work.

Therefore discovery should search from **1979 onward**, while distinguishing two historical strata:

1. **1979 onward:** foundational reasoning, temporal logic, truth maintenance, belief revision, and provenance concepts used as TRANSFER evidence.
2. **Approximately the 2000s onward:** empirical NLP methods and datasets that can supply extraction, factuality, temporal, contradiction, revision, or verification evidence.

The search should not mistake the older formal literature for direct empirical validation, but excluding it would remove exactly the historical-lineage and revision mechanisms that the product requires.
