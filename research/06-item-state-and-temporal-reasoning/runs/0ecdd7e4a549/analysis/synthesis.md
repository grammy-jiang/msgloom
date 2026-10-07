# Executive Summary

The 38-paper corpus provides strong component-level evidence for source-relative factuality, temporal ordering, longitudinal state tracking, revision alignment, provenance, contradiction handling, and evidence-based verification, but it does not directly validate the target task as an integrated workplace-communication problem. Empirical NLP results show that broader context and structured reasoning can improve temporal and state predictions, while revision datasets demonstrate recoverable alignments between successive document versions. Formal commitment, dialogue, belief-revision, and provenance work supplies precise distinctions among cancellation, correction, conflict, reopening, support, and historical persistence. However, workplace-domain evidence is narrow, no admitted study jointly labels the required revision relations across successive operational messages, and no study directly separates a completion claim from independently corroborated completion within such a longitudinal state model. All eight carried gaps therefore remain open.

# Themes

- **Source-relative factuality versus truth.** Factuality and commitment literature represents what a particular source presents, believes, or commits to, rather than directly deciding objective truth [doi-10-1007-s10579-009-9089-9] [doi-10-18653-v1-2023-findings-acl-44].
- **Longitudinal context and structure.** Temporal and state-tracking work frequently benefits from document context, global inference, temporal priors, or propagated relational information [1804.06020] [1805.06975] [1909.00429] [manual-b3703967d3].
- **Revision without erasure.** Document-revision, dialogue, and commitment work represents edits, corrections, retractions, reopening, and persistence of unaffected information rather than treating every later statement as a total replacement [2210.15067] [2406.00197] [doi-10-1093-jos-ffn013] [doi-10-1023-a-1010318403544].
- **Provenance and surviving support.** Provenance research preserves why an output exists, where its values originated, and which alternative derivations remain valid after changes [doi-10-1007-3-540-44503-x-20] [2007.14864].
- **Retrieval and attribution bottlenecks.** Fact-verification systems deteriorate when required evidence is not retrieved, and exact source attribution becomes difficult when multiple semantically similar sources exist [2011.03088] [2110.08222] [2606.18037].
- **Formal distinctions exceed current integrated NLP coverage.** Commitment, truth-maintenance, temporal-database, and belief-change work formalizes distinctions that have not been jointly evaluated as an NLP state model [doi-10-1016-0004-3702-86-90080-9] [doi-10-1016-0020-0255-94-90059-0] [doi-10-1017-cbo9780511526664-007].
- **Direct workplace evidence is narrow.** Workplace email is represented by task/message-relation learning, but not by a full factuality/revision/lifecycle evaluation [manual-d574dff39d].
- **Transfer dominates the empirical base.** News, procedural text, scientific documents, general dialogue, fact verification, and synthetic reasoning supply much of the evidence, so those results do not establish production performance for workplace state tracking.

# Findings

1. **Source-relative factuality is not objective truth.** FactBank represents factuality through polarity and epistemic certainty relative to relevant sources, while later generative and modal-dependency work likewise predicts source or conceiver judgments toward events [doi-10-1007-s10579-009-9089-9] [doi-10-18653-v1-2023-findings-acl-44] [doi-10-18653-v1-2021-acl-long-122]. **Confidence: HIGH.**

2. **Natural speaker commitment remains difficult to generalize.** On naturally occurring CommitmentBank examples, evaluated models perform substantially worse than on their source benchmarks, and no-commitment, conditionals, questions, modality, and neg-raising produce substantial errors [doi-10-18653-v1-p19-1412]. **Confidence: HIGH.**

3. **Several temporal systems benefit from non-local or structured information.** Temporal commonsense priors, global inference, and relative-time propagation improve results in multiple temporal-relation experiments, although effect sizes and responsible components vary [1804.06020] [1909.00429] [doi-10-1162-tacl-a-00182] [doi-10-18653-v1-2021-emnlp-main-815] [manual-b3703967d3]. **Confidence: HIGH.**

4. **Procedural state tracking demonstrates a measurable advantage for broader state modeling.** ProGlobal substantially outperforms sentence-local ProLocal on aggregate state tracking, especially final location, while CRTS reannotation identifies referent uniqueness and missing-state accounting as major annotation problems [1805.06975] [manual-2362cbe877]. **Confidence: HIGH.**

5. **Formal commitment and dialogue work supports distinct revision semantics.** The admitted formal literature separately represents active, satisfied, canceled, and violated commitments and models correction, retraction, persistence of undisputed content, and reopening of earlier commitments [doi-10-1007-s10458-012-9202-0] [doi-10-1093-jos-ffn013] [doi-10-1023-a-1010318403544] [doi-10-1145-1082473-1082754]. **Confidence: HIGH.**

6. **Successive document versions can be aligned and their revisions classified.** arXivEdits reports high-performing sentence alignment and finer-grained span alignment across scientific-document versions, while Re3 links review requests to realized edits and shows that a single request can map to multiple edits [2210.15067] [2406.00197]. **Confidence: HIGH.**

7. **Provenance methods can retain alternative support and explicit source ownership.** Database and dynamic-KG provenance work preserves witnesses, source locations, and alternative derivations as underlying data changes, while source-aware verification work evaluates whether support comes from the correct source [doi-10-1007-3-540-44503-x-20] [2007.14864] [2606.18037] [doi-10-1016-j-ipm-2026-104709]. **Confidence: HIGH.**

8. **Verification is constrained by evidence retrieval.** HoVer retrieval success falls sharply as evidence spans more hops, and DialFact verification accuracy drops substantially when replacing oracle evidence with retrieved evidence [2011.03088] [2110.08222]. **Confidence: HIGH.**

9. **Belief revision and evidence arbitration remain unreliable in current language models.** Belief-R exposes a pronounced trade-off between updating and maintaining prior conclusions, while conflicting-evidence experiments find modality preferences, order effects, and strong influence from temporal recency [2406.19764] [2608.20116]. **Confidence: HIGH.**

10. **Direct workplace-email evidence supports relational modeling, but only for a narrower task.** Email Task Management reports substantial gains from structured message information and iterative interaction between message relations and speech acts, while also reporting fuzzy task boundaries in free-text work email [manual-d574dff39d]. **Confidence: HIGH.**

11. **The formal literature separates distinct temporal and belief-change dimensions.** Temporal-database work distinguishes event, valid, and transaction time for corrections and delayed or retroactive updates, while belief-change theory distinguishes revision of beliefs from update of a changing world [doi-10-1016-0020-0255-94-90059-0] [doi-10-1017-cbo9780511526664-007]. **Confidence: HIGH.**

# Contradictions

### Explicit transitivity constraints

Dense Event Ordering reports a major contribution from transitive inference: its ablated configuration rises from 32.1 to 39.8 F1 when transitivity is added [doi-10-1162-tacl-a-00182]. By contrast, Joint Event and Temporal Relation Extraction reports no gain from its transitivity constraint on TB-Dense and only 0.1 F1 on MATRES [1909.05360]. These experiments use different architectures and inference formulations, so the evidence does not support a universal benefit from explicit transitivity constraints.

### Joint versus pipeline learning

Structured joint learning improves end-to-end temporal-relation and event extraction in [1909.05360], and removing multi-task learning from DLGRN degrades factuality and event-anchor results [doi-10-1016-j-ipm-2021-102836]. Modal Dependency Parsing, however, reports almost identical event-extraction F1 for joint and pipeline systems and slightly better labeled attachment for the pipeline with gold mentions, although joint learning helps when mentions are automatic [doi-10-18653-v1-2021-acl-long-122]. Joint learning therefore has task- and error-regime-dependent empirical effects.

### Direct timeline versus relation-based representations

Direct contextual timeline prediction beats indirect TL2RTL conversion on the TE3 split but loses to the indirect method on the TimeBank-Dense-derived split within the same study [doi-10-18653-v1-d18-1155]. Separately, logical endpoint decomposition improves over direct relation classification on TB-Dense and MATRES [manual-eef7a0219f]. The corpus therefore does not identify one temporal representation as uniformly superior.

### Explicit source awareness

HeterMV reports gains from source-aware heterogeneous evidence modeling on two multi-source fact-verification datasets [doi-10-1016-j-ipm-2026-104709]. ProvenanceGuard, however, finds that a source-blind MiniCheck baseline remains statistically competitive on binary rejection; its distinctive measured advantage is explicit source attribution rather than a statistically established binary-rejection advantage [2606.18037]. These results concern different metrics and tasks and cannot be collapsed into one source-awareness accuracy claim.

### Recency versus semantic correction

Evidence-arbitration experiments show that temporal recency often exerts strong influence on model choices [2608.20116]. Formal dialogue semantics instead models correction selectively: disavowed commitments are removed while undisputed content can persist, and a correction that is itself corrected can restore earlier material [doi-10-1093-jos-ffn013]. This is a tension between observed model behavior and a formal account of revision semantics, not a head-to-head empirical contradiction.

# Open Gaps

### gap-1 — ACADEMIC, HIGH

No admitted paper directly evaluates longitudinal state tracking across workplace messages in which one work item moves among requested, proposed, planned, approved, completed, revoked, superseded, disputed, conditional, and unresolved states while retaining historical assessments. Procedural state tracking [1805.06975], formal commitment monitoring [doi-10-1007-s10458-012-9202-0], and email task/message-relation learning [manual-d574dff39d] each address only subsets of this problem.

Suggested query: `workplace email enterprise chat longitudinal work item lifecycle state tracking requested planned approved completed revoked superseded disputed unresolved`

**Status: open.**

### gap-2 — ACADEMIC, HIGH

The corpus provides formal treatments of correction, retraction, persistence, and reopening [doi-10-1093-jos-ffn013] [doi-10-1023-a-1010318403544], empirical document-revision alignment and intent classification [2210.15067] [2406.00197], and revision-sensitive fact verification [2103.08541]. It still does not establish a natural-language method evaluated across successive operational communications for distinguishing supersession, correction, supplementation, contradiction, reopening, and unresolved conflict.

Suggested query: `natural language dialogue revision relation classification supersession correction supplementation contradiction reopening unresolved conflict longitudinal`

**Status: open.**

### gap-3 — ACADEMIC, HIGH

Separate admitted studies evaluate source-relative factuality [doi-10-1007-s10579-009-9089-9], temporal relations [1909.00429], commitment lifecycle [doi-10-1007-s10458-012-9202-0], provenance [2606.18037], and conflicting-evidence arbitration [2608.20116]. No admitted paper jointly evaluates those components as one longitudinal model.

Suggested query: `"event factuality" temporal relation contradiction provenance lifecycle longitudinal joint model`

**Status: open.**

### gap-4 — ACADEMIC, HIGH

Direct target-task evidence for workplace email, Teams-like dialogue, or comparable operational communication remains absent. The corpus does contain a workplace-email study, but it addresses task identification, message relations, and speech acts rather than longitudinal factuality, lifecycle revision, supersession, or evidence-backed current-state resolution [manual-d574dff39d]. DialFact supplies dialogue evidence, but its task is fact-checking rather than operational work-item state tracking [2110.08222].

Suggested query: `workplace email enterprise chat operational communication task state tracking revision factuality temporal commitment`

**Status: open.**

### gap-5 — ACADEMIC, HIGH

The factuality literature represents what a source asserts or commits to [doi-10-1007-s10579-009-9089-9] [doi-10-18653-v1-2023-findings-acl-44], while fact-verification and provenance-aware systems assess supporting evidence [2011.03088] [2110.08222] [2606.18037] [doi-10-1016-j-ipm-2026-104709]. No admitted paper evaluates how a longitudinal operational model should distinguish an author's assertion that work is complete from independent confirmation or stronger evidential verification of that completion.

Suggested query: `dialogue event factuality evidentiality source attribution claimed completion independent confirmation corroboration longitudinal`

**Status: open.**

### gap-6 — ENGINEERING, HIGH

Evaluation is still needed on adversarial longitudinal sequences such as plan-to-cancel, approve-to-revoke, deadline changes, contradictory same-time updates, out-of-order ingestion, stale messages arriving late, and completion claims later corrected. Revision-aware verification [2103.08541], belief-revision tests [2406.19764], evidence-conflict tests [2608.20116], and correction semantics [doi-10-1093-jos-ffn013] cover selected phenomena but not this complete end-to-end sequence set.

**Status: open.**

### gap-7 — ENGINEERING, HIGH

The combined representation of message time, event or effective time, deadline or constraint time, and observed collection or version time has not been benchmarked for the target state-resolution task. The temporal-database literature supplies a related three-time formal account [doi-10-1016-0020-0255-94-90059-0], while temporal NLP papers evaluate other time representations and relations [doi-10-18653-v1-d18-1155] [doi-10-18653-v1-2021-emnlp-main-815].

**Status: open.**

### gap-8 — ENGINEERING, HIGH

Provenance and event-sourcing studies demonstrate mechanisms for preserving derivations, historical facts, and schema evolution [2007.14864] [doi-10-1007-3-540-44503-x-20] [2104.01146], and source-aware verification explicitly tracks claim-source relations [2606.18037]. None evaluates a provenance-preserving implementation of this target state-resolution task that stores immutable source observations and successive assessments while exposing a separately derived current-state view.

**Status: open.**

# Actionable Insights

- **Synthesis-derived recommendation:** represent source observations, interpreted assessments, and any derived current-state view as separate layers so that later reinterpretation does not overwrite historical evidence.
- **Synthesis-derived recommendation:** represent longitudinal revision as explicit relation edges such as supersedes, corrects, supplements, reopens, conflicts-with, and unresolved, with an abstention or unknown state rather than inferring revision from message recency alone.
- **Synthesis-derived recommendation:** keep source-relative claimed factuality separate from an evidence-strength or corroboration dimension, so that a statement of completion and independent confirmation of completion are not encoded as the same property.
- **Synthesis-derived recommendation:** preserve distinct message time, event or effective time, deadline or constraint time, and collection or version time when those values are available, rather than collapsing them into one timestamp.
- **Synthesis-derived recommendation:** evaluate the state model with adversarial longitudinal sequences, including late ingestion, changed deadlines, cancellation after planning, revocation after approval, contradictory same-time evidence, and corrected completion claims.
- **Synthesis-derived recommendation:** permit incompatible assessments to coexist with explicit provenance until the available evidence justifies a resolved current assessment, rather than deleting a conflicting historical record.
- **Synthesis-derived recommendation:** treat global consistency, transitivity, and joint inference as candidate mechanisms to benchmark rather than assumptions, because their observed gains vary by architecture and dataset.
- **Synthesis-derived recommendation:** require target-domain evaluation on workplace or operational communication before making production-accuracy claims, because most component evidence in this corpus comes from news, procedural text, scientific revision, formal dialogue, synthetic reasoning, or general fact verification.

# Confidence Summary

Confidence is **high** in the component-level findings because multiple distinct literatures establish source-relative factuality, temporal-relation modeling, longitudinal state tracking, revision alignment, provenance, and evidence-retrieval effects.

Confidence is **medium** for transfer of those mechanisms to operational communication. The corpus contains one direct workplace-email study [manual-d574dff39d], but its task is task/message-relation learning rather than longitudinal factuality and state revision.

Confidence is **low** for the integrated target problem. No admitted paper evaluates the full combination of revision-relation labeling, lifecycle state, factuality, temporal reasoning, conflict, provenance, and independent corroboration in successive workplace messages. The corpus therefore supports well-supported design principles and candidate mechanisms, not a validated combined production model.

# Limitations

- This synthesis uses the supplied reduced per-paper analyses rather than fresh inspection of the complete papers, so methodological details omitted from those analyses cannot be recovered here.
- Most empirical NLP evidence comes from news, procedural narratives, scientific-document revision, fact verification, or synthetic reasoning. These are transfer domains and do not establish workplace production accuracy.
- Formal dialogue, commitment, truth-maintenance, temporal-database, and belief-revision papers establish semantic distinctions or algorithms, not NLP classification performance on operational communication [doi-10-1007-s10458-012-9202-0] [doi-10-1016-0004-3702-86-90080-9] [doi-10-1016-0020-0255-94-90059-0].
- The workplace-email study directly supports task and message-relation learning but does not evaluate the lifecycle and revision distinctions required by this topic [manual-d574dff39d].
- Several apparent contradictions compare different datasets, architectures, annotation schemes, or evaluation metrics. They demonstrate non-universality of effects rather than direct replication failures.
- Papers validating factuality, temporal relations, state tracking, provenance, verification, and revision alignment separately do not jointly validate a combined scheme.
- The inherited Topic 05 handoff and the supplied project context were treated only as scoping conditions. They were not used as evidence for findings and were not used to close gaps.
- No duplicate titles are apparent among the 38 supplied analyses, but the reduced records do not contain enough bibliographic metadata to independently exclude every possible duplicate publication under a different title or identifier.
