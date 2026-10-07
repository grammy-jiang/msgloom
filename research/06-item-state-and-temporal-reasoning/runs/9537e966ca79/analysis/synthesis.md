# Executive Summary

The corpus establishes several complementary foundations for longitudinal state reasoning but does not evaluate them as one integrated operational-communication task. Factuality work shows that event status is source-relative and distinct from objective verification, while temporal-relation research demonstrates useful ordering models and global consistency mechanisms. Commitment and dialogue formalisms distinguish lifecycle transitions, retraction, correction, persistence, and reopening. Belief-revision research separately distinguishes changed-world updates from corrected beliefs and offers conflict-preserving revision strategies. Temporal-database, provenance, and event-sourcing work provides mechanisms for retaining historical states and derivations. Important empirical tensions remain over the value of transitivity and alternative timeline representations. Most NLP evidence is news-derived, while lifecycle and revision evidence is mainly formal, modeled, or adjacent-domain. None of the eight prior gaps is fully resolved by the expanded corpus.

# Themes

## Source-relative factuality rather than objective verification

Event factuality is represented in the admitted factuality literature as a source's commitment or presentation regarding an event rather than as direct proof of objective real-world truth. FactBank combines polarity and epistemic certainty and explicitly attaches factuality to relevant discourse sources; its reported annotation agreement was substantial across source-predicate identification, source identification, and factuality-value assignment. The later generative FactBank work retains this source-relative interpretation while jointly predicting sources, target events, and factuality values. [doi-10-1007-s10579-009-9089-9] [doi-10-18653-v1-2023-findings-acl-44]

The literature also demonstrates more than one way to aggregate factuality. FactBank preserves assessments relative to relevant sources and notes that an event may receive a different assessment later in discourse, although its released annotations deliberately remain sentence-local. ExDLEF explicitly observes that sentence-level assessments of one event can differ but defines one document-level factuality value for prediction. These are different task definitions; neither experiment supplies a longitudinal revision history. [doi-10-1007-s10579-009-9089-9] [doi-10-1007-s11390-024-2655-1]

## Temporal structure and ordering

News-derived temporal-relation experiments repeatedly show gains from adding structure or temporal knowledge. TemProb priors improve both local and globally constrained temporal-relation extraction; the MATRES neural baseline gains from a TemProb-trained common-sense encoder; structured joint prediction improves end-to-end event/relation F1; relative-event-time prediction improves MATRES relation extraction; and endpoint decomposition improves TB-Dense and MATRES results while reducing many VAGUE-related errors. [1804.06020] [1909.00429] [1909.05360] [doi-10-18653-v1-2021-emnlp-main-815] [manual-eef7a0219f]

Dense temporal reasoning nevertheless contains substantial uncertainty. TimeBank-Dense labels 46% of its temporal graph VAGUE, and the CAEVO experiments show that relations involving small edge categories can materially influence other relations through graph closure. [doi-10-1162-tacl-a-00182]

Direct relative-timeline prediction provides a different representation: it places entities on a consistent relative axis rather than first assigning every pair a temporal label. Its performance relative to relation-based TL2RTL changes across datasets, and the paper explicitly notes that putting factual, hypothetical, negated, expected, and opinionated events on one axis is a limitation. [doi-10-18653-v1-d18-1155]

## Commitment lifecycle, correction, retraction, and reopening

The Event Calculus commitment model supplies explicit lifecycle semantics for conditional and base commitments, including active, satisfied, canceled, violated, detached, replaced, released, and expired conditions. It also distinguishes cancellation, which results from an action, from violation, which results from failure to satisfy a required temporal property. Its Reactive Event Calculus implementation updates commitment state as an event narrative grows. [doi-10-1007-s10458-012-9202-0]

The layered message-semantics model likewise makes interpretation dependent on conversational and commitment state: the same structural message can acquire a more specific meaning according to the commitment it targets and its current state. This work is conceptual rather than an empirical workplace benchmark. [doi-10-1145-1082473-1082754]

Dialogue research adds explicit semantics for changes to public commitments. Retraction changes what a participant is currently committed to without erasing the historical fact of the earlier utterance. [doi-10-1023-a-1010318403544] In the SDRT-based account, accepted corrections remove disavowed commitments while preserving undenied prior material; a correction of a correction can restore an earlier commitment structure, giving a formal account of reopening previously displaced content. [doi-10-1093-jos-ffn013]

## Changed-world updates, corrected beliefs, and conflict handling

The update-versus-revision literature distinguishes two forms of knowledge change: update models a world that has changed, whereas revision incorporates new information about a world treated as static. Its accessible account argues that the same rationality postulates do not apply uniformly to both operations. [doi-10-1017-cbo9780511526664-007]

Disjunctive Maxi-Adjustment addresses a different part of the problem: inconsistency in ranked propositional knowledge bases. Instead of deleting all formulas implicated in a conflict, DMA weakens conflicting formulas through disjunction. The paper proves an equivalence with lexicographical inference and reports experiments in which this strategy retained information that deletion-based alternatives lost, while also documenting computational and provenance-related tradeoffs. [doi-10-1016-j-artint-2003-08-003]

## Historical time, provenance, and retained state

Temporal-database work argues that valid time and transaction time are insufficient for some retroactive and proactive changes, and that event time is additionally needed to preserve histories involving retroactive updates, proactive updates, corrections, and delayed recording. This result was available only through the paper's abstract in the supplied analysis. [doi-10-1016-0020-0255-94-90059-0]

Database provenance provides a separate formal distinction: why-provenance identifies source data responsible for an output's existence, whereas where-provenance identifies source locations from which output values came. The paper establishes several formal invariance and composition properties under specified query restrictions but does not model temporal correction histories. [doi-10-1007-3-540-44503-x-20]

Industrial event-sourcing evidence shows that retaining state changes is one reported audit rationale and identifies versioned events, weak schema, upcasting, in-place transformation, and copy-and-transform as evolution techniques. Copy-and-transform retains original source events while producing transformed streams. The same empirical study also shows that complete immutability was not universal across the systems examined, so industrial practice does not supply one uniform history-retention pattern. [2104.01146]

## Source-aware evidence and cross-document transfer evidence

HeterMV demonstrates on Check-COVID and FEVEROUS-S that preserving evidence roles in a heterogeneous graph can improve the reported multi-source fact-verification results. Its nodes distinguish core evidence, surrounding context, and reference documents. This is adjacent-domain verification evidence, not an evaluation of longitudinal work-item transitions. [doi-10-1016-j-ipm-2026-104709]

Cross-document timeline work similarly shows that combining temporal, lexical, and distributional information improves news-event timeline construction, while manually corrected entity coreference improves downstream event recall. Its experiments concern event identity and ordering rather than changes in an event's factual or workflow state. [doi-10-1016-j-knosys-2016-07-032]

# Contradictions

### Global temporal transitivity

There is a clear empirical tension over the measured value of transitive constraints. CAEVO reports a large gain when transitive inference is added to its dense temporal-ordering cascade and estimates that transitive reasoning contributes roughly ten percent performance improvement. [doi-10-1162-tacl-a-00182] By contrast, the structured joint event/relation model reports no gain from its transitivity constraint on TB-Dense and only 0.1 F1 on MATRES; most of its structural gain came instead from event-relation consistency. [1909.05360] The experiments use different architectures, candidate graphs, and inference regimes, so the corpus does not support averaging them into a universal claim about transitivity.

### Direct timeline versus relation-to-timeline modeling

The relative-timeline study contains a cross-dataset reversal. Contextual direct timeline prediction beats the indirect TL2RTL variants on its TE3 evaluation, but TL2RTL beats the direct model on the smaller TimeBank-Dense-derived split. [doi-10-18653-v1-d18-1155] The paper discusses data volume, annotation density, and class balance as relevant differences, leaving the relative advantage conditional on the experimental setting.

### Single document-level factuality versus source-relative factuality

ExDLEF assigns one document-level factuality value even though it explicitly observes differing sentence-level assessments of the same event. [doi-10-1007-s11390-024-2655-1] FactBank and its later generative formulation instead retain factuality relative to identified sources. [doi-10-1007-s10579-009-9089-9] [doi-10-18653-v1-2023-findings-acl-44] This is a representational tension rather than proof that either task definition is universally preferable.

### DLGRN parameter-count claim

The DLGRN paper contains an internal contradiction: its narrative says the model has fewer parameters than all baselines, while its own tables list BERT at 109.5M parameters and DLGRN at 119.7M. [doi-10-1016-j-ipm-2021-102836] This inconsistency concerns the parameter-efficiency claim, not the reported factuality-performance values.

# Open Gaps

### gap-1 — ACADEMIC — HIGH

No admitted paper directly evaluates longitudinal state tracking across workplace messages in which one work item moves among requested, proposed, planned, approved, completed, revoked, superseded, disputed, conditional, and unresolved states while retaining historical assessments. Commitment-state models cover subsets of such transitions, but not this target task. [doi-10-1007-s10458-012-9202-0] [doi-10-1145-1082473-1082754]

Suggested query: `longitudinal event state tracking dialogue email requested planned approved completed revoked superseded`

Status: **open**.

### gap-2 — ACADEMIC — HIGH

The corpus now contains substantive formal treatments of correction, retraction, persistence, and reopening. [doi-10-1023-a-1010318403544] [doi-10-1093-jos-ffn013] It still does not establish an evaluated natural-language method for distinguishing supersession, correction, supplementation, contradiction, reopening, and unresolved conflict across successive operational communications.

Suggested query: `natural language supersession correction contradiction revision reopening dialogue event state`

Status: **open**.

### gap-3 — ACADEMIC — HIGH

No admitted paper jointly evaluates source-relative factuality, temporal ordering, lifecycle state, contradiction, and provenance as one longitudinal model. FactBank covers source-relative factuality [doi-10-1007-s10579-009-9089-9], temporal work covers ordering [doi-10-1162-tacl-a-00182], commitment work covers lifecycle transitions [doi-10-1007-s10458-012-9202-0], and provenance work covers derivational lineage [doi-10-1007-3-540-44503-x-20]. Those separate results do not constitute evidence for the combined scheme.

Suggested query: `"event factuality" temporal relation contradiction provenance longitudinal state tracking`

Status: **open**.

### gap-4 — ACADEMIC — HIGH

Direct evidence for workplace email, Teams-like dialogue, or comparable operational communication remains absent. The quantitative NLP evidence is predominantly news-derived, while relevant commitment, dialogue, database, event-sourcing, and belief-change studies use formal, modeled, argumentative, enterprise-engineering, or adjacent-domain settings. [2104.01146] [doi-10-1007-s11390-024-2655-1] [doi-10-1016-j-ipm-2026-104709]

Suggested query: `workplace email dialogue event factuality temporal revision commitment status tracking`

Status: **open**.

### gap-5 — ACADEMIC — HIGH

The factuality literature establishes textual source commitment rather than independent truth verification. [doi-10-1007-s10579-009-9089-9] [doi-10-18653-v1-2023-findings-acl-44] HeterMV supplies adjacent-domain evidence that source-aware corroborating evidence can improve fact verification, but it does not evaluate the specific distinction between a workplace author's completion assertion and independent confirmation of that completion. [doi-10-1016-j-ipm-2026-104709]

Suggested query: `event factuality evidentiality source attribution independent confirmation verification reported completion`

Status: **open**.

### gap-6 — ENGINEERING — HIGH

Evaluation is still needed on adversarial longitudinal sequences such as plan-to-cancel, approve-to-revoke, deadline changes, contradictory same-time updates, out-of-order ingestion, stale messages arriving late, and completion claims later corrected. Individual papers cover cancellation and violation [doi-10-1007-s10458-012-9202-0], correction and reopening [doi-10-1093-jos-ffn013], and retroactive or delayed database updates [doi-10-1016-0020-0255-94-90059-0], but none supplies this benchmark.

Status: **open**.

### gap-7 — ENGINEERING — HIGH

The combined representation of message time, event/effective time, deadline or constraint time, and observed collection/version time has not been benchmarked for the target state-resolution task. The temporal-database paper supplies a related formal account involving event, valid, and transaction time, but not this four-part product evaluation. [doi-10-1016-0020-0255-94-90059-0]

Status: **open**.

### gap-8 — ENGINEERING — HIGH

The corpus does not evaluate a provenance-preserving implementation for this state-resolution task that stores immutable source observations and successive assessments while exposing a separately derived current-state view. Provenance theory formalizes derivational lineage [doi-10-1007-3-540-44503-x-20], while event-sourcing research documents historical-retention and schema-evolution practices [2104.01146], but the specified combined implementation and benchmark remain unevaluated.

Status: **open**.

# Actionable Insights

- **Synthesis-derived recommendation:** represent source observations, source-relative assessments, and any derived current-state assessment as distinct records rather than collapsing them into one mutable fact. This is a project decision inferred from the combined literature, not a configuration directly evaluated by the papers.
- **Synthesis-derived recommendation:** model correction, supersession, contradiction, supplementation, reopening, and unresolved conflict as distinct candidate relations and test them independently before allowing any relation to replace prior state. This combined taxonomy is a project decision; no admitted paper evaluates it end to end.
- **Synthesis-derived recommendation:** keep temporal ordering and factuality or lifecycle status as separate dimensions so that an event can be temporally positioned without being treated as factual or completed. The exact product representation is a project decision.
- **Synthesis-derived recommendation:** maintain separate source-relative claims when parties disagree and derive any consolidated assessment from those claims with explicit provenance. The consolidation policy is a project decision and is not validated by the cited dialogue or factuality experiments.
- **Synthesis-derived recommendation:** build an engineering benchmark around adversarial state-transition sequences, including late-arriving evidence and corrections of corrections, because the admitted literature does not provide an equivalent workplace benchmark.
- **Synthesis-derived recommendation:** evaluate global temporal constraints empirically rather than assuming they will help; the admitted experiments show materially different effects across architectures and datasets.
- **Synthesis-derived recommendation:** treat independent confirmation as an evidential dimension separate from linguistic factuality until targeted literature or product-specific evaluation establishes a justified mapping between them.

# Confidence Summary

Confidence is high in the component-level conclusions concerning source-relative factuality, temporal-relation modeling, formal commitment-state transitions, correction and retraction semantics, and the existence of history-preserving provenance or event-sourcing mechanisms. FactBank, temporal-relation benchmarks, and several structured models provide direct evidence for their respective tasks. [doi-10-1007-s10579-009-9089-9] [1804.06020] [1909.05360] [doi-10-1162-tacl-a-00182]

Confidence is lower for transfer to longitudinal workplace communication. Most quantitative NLP evidence is news-derived, and the commitment, retraction, belief-change, temporal-database, and provenance literature is primarily formal, conceptual, modeled, or adjacent-domain. [doi-10-1007-s10458-012-9202-0] [doi-10-1023-a-1010318403544] [doi-10-1017-cbo9780511526664-007] [doi-10-1007-3-540-44503-x-20]

The corpus therefore supports well-supported design principles and candidate mechanisms, not necessary design requirements. In particular, no admitted experiment validates the combined use of source-relative factuality, temporal ordering, lifecycle state, contradiction handling, provenance, and historical-state retention as one longitudinal system.

# Limitations

- The corpus contains no direct benchmark of longitudinal workplace email or Teams-like communication covering the target lifecycle states.
- Most empirical temporal and factuality NLP results come from news-derived corpora, so production-email transfer is not established. [1804.06020] [1909.00429] [doi-10-1007-s10579-009-9089-9] [doi-10-1016-j-knosys-2016-07-032]
- Several important lifecycle, correction, retraction, belief-change, and provenance results are formal or conceptual rather than corpus-scale empirical evaluations. [doi-10-1023-a-1010318403544] [doi-10-1093-jos-ffn013] [doi-10-1007-3-540-44503-x-20]
- The temporal-database paper [doi-10-1016-0020-0255-94-90059-0], the update-versus-revision paper [doi-10-1017-cbo9780511526664-007], and HeterMV [doi-10-1016-j-ipm-2026-104709] were available only at abstract or preview level in the supplied analyses, limiting verification of detailed methods and failure cases.
- Papers separately validate factuality, temporal ordering, commitment transitions, provenance, belief revision, and multi-source verification; no experiment in the corpus validates their combined use as one scheme.
- The corpus does not establish a general natural-language rule for deciding when a later communication supersedes rather than contradicts, supplements, or corrects an earlier one.
- Source-relative factuality describes what a source commits to in text and does not itself establish independent real-world confirmation. [doi-10-1007-s10579-009-9089-9] [doi-10-18653-v1-2023-findings-acl-44]
- The DLGRN paper contains an internal inconsistency between its prose parameter-efficiency claim and the parameter counts in its tables. [doi-10-1016-j-ipm-2021-102836]
- The inherited Topic 05 handoffs and project context were treated only as starting conditions and scope. They were not used as evidence for any literature finding or as grounds for closing a gap.
