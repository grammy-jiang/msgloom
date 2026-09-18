# Executive Summary

Across 13 papers, the literature covers several components of longitudinal work-item state reasoning, but not the complete workplace problem. Event-factuality work demonstrates source-relative polarity and certainty prediction, including sentence-level and document-level formulations [doi-10-1007-s10579-009-9089-9] [doi-10-1007-s11390-024-2655-1]. Temporal-relation research demonstrates pairwise, graph-based, and relative-timeline representations, although the measured value of global transitivity varies by architecture and benchmark [doi-10-1162-tacl-a-00182] [1909.05360]. Formal commitment monitoring supplies explicit lifecycle semantics, while belief-revision work supplies conflict handling under ranked propositional assumptions [doi-10-1007-s10458-012-9202-0] [doi-10-1016-j-artint-2003-08-003]. None of the admitted papers directly evaluates a provenance-preserving, cross-message workplace state history combining factuality, time, lifecycle transition, supersession, contradiction, and unresolved conflict. The component mechanisms are supported; their integration and workplace-domain effectiveness remain untested.

# Themes

- **Source-relative event factuality and uncertainty.** FactBank represents factuality through source-relative polarity and certainty, while later work predicts scalar or document-level factuality [doi-10-1007-s10579-009-9089-9] [doi-10-1016-j-ipm-2021-102836] [doi-10-1007-s11390-024-2655-1].
- **Temporal relation extraction and event ordering.** Multiple papers improve temporal relation extraction using corpus priors, contextual encoders, relative time, structured endpoint representations, and cross-document semantic knowledge [1804.06020] [1909.00429] [doi-10-18653-v1-2021-emnlp-main-815] [manual-eef7a0219f] [doi-10-1016-j-knosys-2016-07-032].
- **Global temporal consistency.** Temporal graphs, ILP constraints, cascaded inference, and transitive closure recur across the temporal literature, but their incremental empirical value differs materially between systems [1804.06020] [1909.05360] [doi-10-1162-tacl-a-00182].
- **Relative timelines versus pairwise relations.** Direct timeline models can produce consistent relative ordering without explicit pairwise relation prediction, but their comparative performance changes by dataset [doi-10-18653-v1-d18-1155].
- **Explicit commitment lifecycle monitoring.** Event Calculus formalizes changing commitment states and supports incremental monitoring of an event narrative [doi-10-1007-s10458-012-9202-0].
- **Conflict resolution and belief revision.** DMA preserves information by weakening ranked conflicting propositions instead of simply deleting all conflicting information [doi-10-1016-j-artint-2003-08-003].
- **Cross-document identity and timeline construction.** Cross-document ordering depends materially on event and entity identity, with manual entity coreference improving recall [doi-10-1016-j-knosys-2016-07-032].
- **Upstream error propagation.** Event-detection and coreference errors remain downstream bottlenecks even in joint or structured temporal systems [1909.05360] [doi-10-1016-j-knosys-2016-07-032].
- **Rare-state and ambiguity problems.** Minority temporal and factuality classes remain difficult, and VAGUE occupies a large portion of dense temporal annotation [1909.05360] [doi-10-1162-tacl-a-00182] [doi-10-1007-s11390-024-2655-1].
- **Component evidence does not establish an integrated longitudinal state model.** The corpus studies factuality, temporal relations, commitment lifecycles, belief revision, and event identity separately; no admitted experiment evaluates their complete combination.

# Findings

1. **Source-relative factuality is empirically annotatable, but FactBank does not annotate longitudinal revision.** FactBank combines polarity and epistemic certainty relative to discourse sources and reports high agreement, while deliberately excluding factuality changes requiring multiple sentences [doi-10-1007-s10579-009-9089-9].

2. **End-to-end sentence-level factuality prediction can jointly detect events and estimate factuality.** DLGRN reports better factuality-induction results than its compared baselines on FactBank, Meantime, UW, and UDS-IH2; its UW ablation shows labeled syntactic information producing the largest tested graph-information degradation when removed [doi-10-1016-j-ipm-2021-102836].

3. **Document context can improve factuality prediction while still collapsing local variation.** RSLN outperforms its reported comparison systems on English and Chinese ExDLEF, and ablations identify event encoding, topic context, and sentence selection as important components. The prediction target remains one document-level factuality value even though sentence-level factualities can differ [doi-10-1007-s11390-024-2655-1].

4. **Temporal commonsense priors improve temporal-relation extraction on news benchmarks.** TemProb features improve local and globally constrained temporal-relation models, and a TemProb-trained Common Sense Encoder improves the reported neural baseline under the evaluated MATRES metrics [1804.06020] [1909.00429].

5. **Joint event and temporal-relation modeling improves end-to-end performance but does not remove upstream error propagation.** The structured joint model improves event and relation F1 on TB-Dense and MATRES, while missed events still force associated relations to NONE and minority temporal labels remain difficult [1909.05360].

6. **The benefit of transitivity is architecture-dependent in the reported experiments.** CAEVO obtains a substantial gain from transitive inference on TimeBank-Dense, whereas the structured joint model reports zero additional TB-Dense F1 and only 0.1 MATRES F1 from its transitivity constraint [doi-10-1162-tacl-a-00182] [1909.05360].

7. **Direct relative-timeline prediction is not uniformly superior to pairwise-relation conversion.** C-TLM outperforms TL2RTL on the TE3 evaluation, while TL2RTL performs better on the smaller TimeBank-Dense-derived split [doi-10-18653-v1-d18-1155].

8. **Relative event times can help temporal-relation classification without becoming calibrated event dates.** Stack-Propagation improves MATRES F1 over its vanilla RoBERTa comparison, but direct timestamp comparison struggles with VAGUE and the learned time values are relative rather than calendar times [doi-10-18653-v1-2021-emnlp-main-815].

9. **Explicit commitment lifecycles can be incrementally monitored in a formal event model.** The Event Calculus framework distinguishes states and operations including active, satisfied, canceled, violated, detached, expired, released, and replaced commitments and processes an incrementally growing event narrative. It leaves simultaneous conflicting operations unresolved rather than choosing a universal precedence rule [doi-10-1007-s10458-012-9202-0].

10. **Ranked logical conflicts can be revised without deleting all conflicting information.** DMA weakens conflicting propositions through disjunction and can retain consequences that Maxi-Adjustment loses, but its experiments assume structured propositional knowledge and explicit priority strata rather than natural-language evidence [doi-10-1016-j-artint-2003-08-003].

11. **Cross-document timeline quality depends on upstream identity resolution.** Combining temporal, lexical-semantic, and distributional information improves the evaluated news timelines, while manual entity coreference particularly improves recall [doi-10-1016-j-knosys-2016-07-032].

12. **Logical decomposition of temporal labels can outperform independent classification.** The unified endpoint framework improves over its matched direct-classification baseline on TB-Dense and MATRES, reduces many VAGUE-associated errors, and improves low-resource and cross-definition transfer [manual-eef7a0219f].

# Contradictions

### Incremental value of global temporal transitivity

CAEVO reports transitive inference as a major contributor on TimeBank-Dense, including an ablation increase from 32.1 to 39.8 F1 [doi-10-1162-tacl-a-00182]. By contrast, the structured joint model reports no additional F1 from its transitivity constraint on TB-Dense and only 0.1 on MATRES [1909.05360]. Because the architectures, candidate-edge behavior, and constraint application differ, these results establish an architecture-dependent empirical effect rather than a uniform benefit.

### Sentence/source-relative versus single document-level factuality

FactBank treats factuality as relative to discourse sources and notes that an event introduced without commitment can later be presented as factual, although the released annotations stop at sentence boundaries [doi-10-1007-s10579-009-9089-9]. RSLN instead defines a single document-level target even when sentence-level factualities differ [doi-10-1007-s11390-024-2655-1]. This is a representational tension, not a head-to-head empirical comparison; these papers do not determine which representation is preferable for longitudinal workplace revisions.

### Conflict-resolution assumptions

The commitment-monitoring framework explicitly avoids defining a universal precedence rule for simultaneous conflicting commitment operations [doi-10-1007-s10458-012-9202-0]. DMA resolves inconsistent information when explicit priority strata are supplied [doi-10-1016-j-artint-2003-08-003]. These are different assumptions rather than directly conflicting benchmark results, and the corpus does not establish how such priorities should be inferred from workplace language.

### DLGRN parameter-count claim

The DLGRN analysis identifies an internal contradiction: the paper's prose claims fewer parameters than all baselines, while its tables list BERT at 109.5M parameters and DLGRN at 119.7M [doi-10-1016-j-ipm-2021-102836]. The numerical tables therefore contradict the narrative parameter-count claim.

# Open Gaps

- **G06-01 — ACADEMIC, HIGH.** No admitted paper directly evaluates longitudinal workplace state tracking in which one work item moves among requested, proposed, planned, approved, completed, revoked, superseded, disputed, conditional, and unresolved states while retaining historical assessments.  
  Suggested query: `"event status tracking" longitudinal email dialogue planned completed canceled revision`

- **G06-02 — ACADEMIC, HIGH.** The corpus does not establish evaluated natural-language semantics for distinguishing supersession, correction, supplementation, contradiction, reopening, and unresolved conflict across successive communications.  
  Suggested query: `supersession correction contradiction revision tracking natural language event state`

- **G06-03 — ACADEMIC, HIGH.** No admitted paper jointly evaluates source-relative factuality, temporal ordering, lifecycle state, contradiction, and provenance. Each component has partial evidence, but their combination remains untested.  
  Suggested query: `"event factuality" temporal relation state tracking provenance contradiction`

- **G06-04 — ACADEMIC, HIGH.** Direct evidence from workplace email, Teams-like dialogue, or comparable operational communication is absent; the empirical NLP literature here is predominantly news-derived, and the formal reasoning studies use modeled or structured inputs.  
  Suggested query: `workplace email event factuality temporal revision commitment status tracking dialogue`

- **G06-05 — ACADEMIC, HIGH.** The admitted factuality literature models textual source commitment but does not establish how to distinguish an author's assertion of completion from independent confirmation or stronger evidential verification.  
  Suggested query: `event factuality evidentiality source reliability confirmation reported completed verification`

- **G06-06 — ENGINEERING, HIGH.** Evaluation remains open for longitudinal adversarial sequences such as plan-to-cancel, approve-to-revoke, deadline changes, contradictory same-time updates, stale messages arriving late, and completion claims later corrected.

- **G06-07 — ENGINEERING, HIGH.** The combined representation of message time, event/effective time, deadline or constraint time, and collection/version time has not been benchmarked for this product's state-resolution cases.

- **G06-08 — ENGINEERING, HIGH.** The corpus does not evaluate a provenance-preserving implementation that retains immutable source observations and successive assessments while exposing a separately derived current-state view.

- **G06-09 — OUT_OF_SCOPE, HIGH.** Topic 05's inherited uncertainties around owner or assignee extraction, deadline binding, and attachment of conditions, negation, and modality remain unresolved. They concern the utterance-time event supplied to Topic 06 rather than the later state-transition problem.

- **G06-10 — OUT_OF_SCOPE, HIGH.** Reliable cross-thread and cross-source identity of the event or work item being revised remains an upstream dependency rather than a question settled by this synthesis.

- **G06-11 — OUT_OF_SCOPE, MEDIUM.** Resolving uncertain state by retrieving missing historical evidence remains a separate evidence-retrieval problem.

- **G06-12 — OUT_OF_SCOPE, MEDIUM.** State-changing evidence contained in attachment versions, tables, images, or screenshots remains a separate multimodal/document-evidence problem.

# Actionable Insights

- **Synthesis-derived recommendation:** represent each new message or document observation as new evidence and a new assessment rather than overwriting prior evidence or historical assessments.
- **Synthesis-derived recommendation:** store message or utterance time, event or effective time, deadline or constraint time, and collection/version time as distinct fields rather than collapsing them into one timestamp.
- **Synthesis-derived recommendation:** keep lifecycle state, factuality or modality, temporal relations, and source provenance as distinct but linkable dimensions so that a temporal ordering decision does not imply factual occurrence or completion.
- **Synthesis-derived recommendation:** model contradiction, supplementation, correction, and supersession as separate relations; do not use a latest-message-wins rule as a generic conflict-resolution mechanism.
- **Synthesis-derived recommendation:** preserve unresolved conflicts explicitly when available evidence does not justify selecting one assessment, and derive any current accepted assessment separately from the historical record.
- **Synthesis-derived recommendation:** build an engineering benchmark of longitudinal adversarial sequences before choosing a state-resolution strategy, including revocations, changed deadlines, late-arriving old messages, contradictory updates, partial confirmations, and corrected completion claims.
- **Synthesis-derived recommendation:** propagate uncertainty from upstream event identity, owner, deadline, condition, negation, and modality extraction instead of silently converting uncertain inputs into firm state transitions.
- **Synthesis-derived recommendation:** keep missing-evidence retrieval, upstream Topic identity, and multimodal attachment interpretation at their existing project ownership boundaries, while exposing explicit interfaces for Topic 06 to request or consume that evidence.

# Confidence Summary

Confidence is high that the corpus establishes **well-supported design principles at the component level**: factuality is source- and uncertainty-sensitive [doi-10-1007-s10579-009-9089-9]; temporal ordering benefits from structured representations and, in some systems, global constraints [1804.06020] [doi-10-1162-tacl-a-00182] [manual-eef7a0219f]; explicit commitment lifecycles can be incrementally monitored [doi-10-1007-s10458-012-9202-0]; and formal belief revision can preserve information under explicit conflict priorities [doi-10-1016-j-artint-2003-08-003].

Confidence is only medium for transfer of these mechanisms to longitudinal workplace communication because almost all NLP evaluations use news-derived corpora and the formal reasoning papers assume structured inputs. Confidence is low that any particular combined architecture has been validated for msgloom: no admitted paper jointly evaluates event identity, source-relative factuality, multiple time axes, lifecycle transitions, supersession, contradiction, provenance, and current-state derivation. The combination is untested.

# Limitations

- This synthesis uses only the 13 supplied per-paper analyses and introduces no evidence from papers outside the admitted corpus.
- Most empirical NLP results come from news-derived datasets such as TimeBank, TB-Dense, MATRES, AQUAINT, MEANTIME, FactBank, and related benchmarks rather than workplace email or chat [1804.06020] [1909.00429] [1909.05360] [doi-10-1007-s10579-009-9089-9].
- The component literatures use different targets—factuality scores, temporal relations, timelines, commitment fluents, and propositional belief revision—and these targets are not interchangeable [doi-10-1016-j-ipm-2021-102836] [doi-10-18653-v1-d18-1155] [doi-10-1007-s10458-012-9202-0] [doi-10-1016-j-artint-2003-08-003].
- No paper in the corpus evaluates the complete combination required for longitudinal workplace-state reasoning.
- Several temporal systems assume supplied events, and multiple analyses identify event detection or entity coreference as significant downstream error sources [1909.00429] [1909.05360] [doi-10-1016-j-knosys-2016-07-032] [doi-10-18653-v1-2021-emnlp-main-815].
- Rare factuality and temporal categories are heavily imbalanced in several datasets, limiting evidence for uncommon states [1909.05360] [doi-10-1007-s10579-009-9089-9] [doi-10-1007-s11390-024-2655-1].
- The formal commitment and belief-revision studies demonstrate semantics and computational behavior under structured assumptions but do not demonstrate natural-language extraction of the required operations, priorities, or conflict relations [doi-10-1007-s10458-012-9202-0] [doi-10-1016-j-artint-2003-08-003].
- The disagreement over transitivity means global-constraint benefits cannot be generalized independently of architecture and benchmark [doi-10-1162-tacl-a-00182] [1909.05360].
- The supplied DLGRN analysis contains an explicit internal inconsistency between a prose parameter-count claim and the paper's numerical tables [doi-10-1016-j-ipm-2021-102836].
- The literature reviewed here does not establish production representativeness, production accuracy, or architecture approval for msgloom.
