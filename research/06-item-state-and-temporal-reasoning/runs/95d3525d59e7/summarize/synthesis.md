# Executive Summary

This 31-paper corpus provides strong component-level evidence but no direct solution to longitudinal workplace work-item revision. Factuality studies consistently model what a source presents as true, uncertain, or false rather than independently verified truth. Temporal and state-tracking studies show that nonlocal context, structured inference, and explicit state trajectories can improve performance, although gains vary by dataset and constraint. Formal dialogue, commitment, truth-maintenance, and belief-revision work distinguishes correction, retraction, cancellation, persistence, reopening, and incompatible alternatives while retaining historical information. Provenance and event-sourcing work supplies complementary history-preservation concepts. Evidence-retrieval and conflict-arbitration studies expose further difficulty when evidence is distributed or inconsistent. However, no admitted paper jointly evaluates these dimensions in successive workplace communications, and none establishes claimed-versus-independently-confirmed completion. All eight previously identified gaps therefore remain open.

## Themes

### 1. Source-relative factuality is not independent verification

Across factuality and speaker-commitment studies, the predicted quantity is generally the commitment or presentation of an event by a particular source, not independent determination that the event occurred. FactBank explicitly represents factuality relative to relevant sources [doi-10-1007-s10579-009-9089-9]. Modal dependency parsing likewise models the certainty a source expresses about an event [doi-10-18653-v1-2021-acl-long-122], and generative factuality prediction defines factuality as presentation or judgment attributed to a source [doi-10-18653-v1-2023-findings-acl-44]. CommitmentBank similarly evaluates speaker commitment rather than external truth [doi-10-18653-v1-p19-1412].

This evidence demonstrates a semantic distinction between source assertion and objective verification. It does not establish a method for independently verifying completion.

### 2. Longitudinal state tracking benefits from broader trajectories in process narratives

ProPara demonstrates that global paragraph-level modeling substantially outperforms sentence-local propagation for process-state tracking, especially when the location after a state change is not stated locally [1805.06975]. ProPara-CRTS further shows that immutable canonical referents, temporally explicit transitions, and more complete state accounting can expose missing or erroneous gold transitions and generally improve evaluation and training behavior [manual-2362cbe877].

These are process-narrative results. Neither study evaluates workplace actions, approvals, cancellations, reopened tasks, or revision histories in email or enterprise chat.

### 3. Structured temporal reasoning helps in several benchmarks, but not uniformly

Several temporal-relation studies report gains from representations or inference that connect multiple temporal decisions rather than treating each pair independently. TemProb improves local and globally constrained temporal extraction on TimeBank-Dense [1804.06020]. Structured joint event/relation inference improves end-to-end relation extraction on TB-Dense and MATRES [1909.05360]. CAEVO reports a substantial contribution from transitive closure [doi-10-1162-tacl-a-00182], and interval-based global inference improves event timeline construction over local classifiers [manual-b3703967d3]. Endpoint decomposition also improves over a strong direct-classification baseline on TB-Dense and MATRES [manual-eef7a0219f].

The papers do not jointly validate a single structured-reasoning design, and the contribution of individual constraints differs substantially between systems.

### 4. Revision can preserve earlier history and undenied content

Formal dialogue and truth-maintenance accounts do not equate revision with erasing the earlier utterance or all of its consequences. The retraction analysis distinguishes changing current commitment from erasing the historical fact that a commitment was made [doi-10-1023-a-1010318403544]. Dialogue SDRT preserves undenied parts of earlier contributions when a correction is accepted and can restore earlier material when a correction is itself corrected [doi-10-1093-jos-ffn013]. ATMS maintains incompatible alternatives in separate consistent environments and localizes inconsistent assumption combinations as nogoods [doi-10-1016-0004-3702-86-90080-9].

These are formal or normative accounts rather than evaluated natural-language longitudinal classifiers.

### 5. Commitment lifecycle operations are more differentiated than simple active/inactive state

The Event Calculus commitment formalization distinguishes satisfaction, cancellation, violation, release, replacement, detachment, expiration, and other lifecycle transitions and incrementally updates commitment state as events arrive [doi-10-1007-s10458-012-9202-0]. It explicitly distinguishes cancellation from violation. The same work also leaves simultaneous conflicting commitment operations unresolved in its implementation rather than defining a universal precedence rule [doi-10-1007-s10458-012-9202-0].

Layered commitment semantics likewise makes message interpretation depend on conversational sequence and current commitment state [doi-10-1145-1082473-1082754].

### 6. Revision requests and realized edits need not have one-to-one correspondence

Re3 directly links review requests to realized edits and permits one request to correspond to several edits [2406.00197]. More than half of explicit review suggestions are implemented in that corpus, while 18.47% of implemented requests require multiple sentence edits [2406.00197]. Its summarization experiments also show that generated revision summaries can omit observed edits [2406.00197].

The study cannot test whether an authentic author's statement that a requested change was completed matches the actual edits, because authentic author response summaries were unavailable and human-generated edit summaries were substituted [2406.00197].

### 7. Provenance and history preservation have distinct formal and industrial evidence

Database provenance distinguishes why-provenance—why an output exists—from where-provenance—the source locations from which particular values were derived [doi-10-1007-3-540-44503-x-20]. The same work proves several provenance-preservation properties under specified query restrictions.

Industrial event-sourcing interviews identify versioned events, weak schema, upcasting, in-place transformation, and copy-and-transform as observed schema-evolution approaches [2104.01146]. Complete immutability was not universal among the 19 systems studied; several allowed historical events to be changed [2104.01146].

These two papers cover different questions: one formalizes derivation provenance, while the other describes event-history practices in deployed systems.

### 8. Distributed evidence increases verification difficulty

HoVer shows sharply decreasing document-retrieval coverage as claims require evidence from more documents, and its end-to-end baseline remains far below sampled human performance [2011.03088]. The benchmark also found that Refuted and NotEnoughInfo were difficult enough to distinguish reliably that they were merged into Not-Supported [2011.03088].

HeterMV separately reports improved Micro-F1 on Check-COVID and FEVEROUS-S by representing core evidence, context, and reference documents with different source roles and reasoning views [doi-10-1016-j-ipm-2026-104709].

These are fact-verification results, not longitudinal work-item state-resolution results.

### 9. Commitment and factuality interpretation remains linguistically fragile

CommitmentBank evaluation shows that systems performing well on earlier factuality datasets deteriorate on naturally occurring commitment examples [doi-10-18653-v1-p19-1412]. Conditionals, neg-raising, and the no-commitment class are especially difficult, and performance varies by genre [doi-10-18653-v1-p19-1412].

Modal dependency parsing also reports substantial difficulty attaching an event to a source located in another sentence [doi-10-18653-v1-2021-acl-long-122]. These results show that source attribution and commitment interpretation remain difficult even before longitudinal revision is added.

### 10. Model conflict arbitration can be driven by recency, presentation order, and modality

In a controlled synthetic forecasting benchmark, instruction-tuned models display model-specific preferences for textual versus numerical evidence, are affected by evidence presentation order, and often give temporal recency more influence than an explicit unreliability cue [2608.20116]. Conflicting tool forecasts produce especially large degradation, and increasing model size does not monotonically eliminate these errors [2608.20116].

This is synthetic binary forecasting evidence. It does not establish the same behavior or its magnitude in workplace revision histories.

### 11. Multiple temporal dimensions are formally distinguished

A temporal-database analysis argues that event time, valid time, and transaction time are all needed within its formal model to preserve histories involving retroactive updates, proactive updates, corrections, and delayed entry [doi-10-1016-0020-0255-94-90059-0]. Only abstract-level material was accessible for that analysis, so detailed formal conditions and implementation behavior were not independently inspected.

Temporal NLP studies address a different problem: relative ordering of events. Relative-timeline work explicitly notes that factual, negated, hypothetical, expected, and opinionated events may require separate temporal axes [doi-10-18653-v1-d18-1155].

### 12. Updating a changed world and revising beliefs are formally distinct

The reviewed knowledge-base theory distinguishes update, where the represented world itself changes, from revision, where new information changes beliefs about a world treated as static [doi-10-1017-cbo9780511526664-007]. It argues that one uniform set of belief-revision postulates is not adequate for both forms of change [doi-10-1017-cbo9780511526664-007].

This is a conceptual and formal distinction; the admitted corpus does not supply a natural-language classifier that identifies these cases in operational communication.

## Contradictions

### Temporal transitivity contributes strongly in one system and almost nothing in another

CAEVO reports transitive inference as a major contributor to dense temporal-ordering performance [doi-10-1162-tacl-a-00182]. By contrast, the structured joint event/relation model reports no gain from its added transitivity constraint on TB-Dense and only 0.1 F1 on MATRES [1909.05360].

This is a genuine empirical tension, but not a direct replication conflict: the systems use different architectures, candidate graphs, and constraint interactions. In particular, the latter paper notes that NONE predictions can prevent transitivity constraints from applying.

### Joint and multi-task learning has mixed effects

DLGRN reports that removing multi-task learning degrades both event-anchor detection and factuality induction [doi-10-1016-j-ipm-2021-102836]. Structured joint event/relation prediction also improves end-to-end extraction [1909.05360].

In modal dependency parsing, however, joint learning produces essentially no event-extraction gain—90.8 versus 90.9 F1—and is slightly worse than the pipeline for labeled attachment when gold mentions are supplied, although it improves attachment when mentions are automatically extracted [doi-10-18653-v1-2021-acl-long-122].

The corpus therefore does not support a universal claim that joint modeling always improves every subtask.

### Direct timelines versus indirect pairwise conversion reverse by dataset

Within the relative-timeline study itself, contextual direct timeline prediction beats TL2RTL on the TempEval-derived evaluation, while TL2RTL beats the direct approach on the smaller TimeBank-Dense-derived split [doi-10-18653-v1-d18-1155]. The study associates this reversal partly with training-set size.

Neither representation therefore has uniform empirical dominance in that paper.

### DLGRN contains an internal parameter-count contradiction

The DLGRN paper's narrative says that DLGRN has fewer parameters than all baselines, but its own tables list BERT at 109.5M parameters and DLGRN at 119.7M [doi-10-1016-j-ipm-2021-102836]. The tabulated figures contradict the broader prose claim.

### ProPara-CRTS contains an internal result-summary contradiction

ProPara-CRTS broadly states that CRTS improves F1 in all settings except GPT-4o-mini sentence-level evaluation, but Table 2 also reports GPT-4o direct-prompting document-level F1 of 58.8 on CRTS versus 59.6 on original ProPara [manual-2362cbe877]. The broad prose characterization therefore overstates the consistency of the improvement.

## Open Gaps

All eight gaps carried into this round remain open.

### gap-1 — ACADEMIC, HIGH — open

No admitted paper directly evaluates longitudinal state tracking across workplace messages in which one work item moves among requested, proposed, planned, approved, completed, revoked, superseded, disputed, conditional, and unresolved states while retaining historical assessments.

ProPara and CRTS track process entities [1805.06975] [manual-2362cbe877], and commitment formalisms track selected commitment states [doi-10-1007-s10458-012-9202-0], but these do not answer the target workplace problem.

Suggested query: `workplace email dialogue longitudinal work item state tracking requested proposed planned approved completed revoked superseded disputed conditional unresolved`

### gap-2 — ACADEMIC, HIGH — open

The corpus provides formal treatments of correction, retraction, persistence, and reopening [doi-10-1093-jos-ffn013] [doi-10-1023-a-1010318403544] and empirical revision alignment in scientific documents [2406.00197], but it does not establish a natural-language method evaluated across successive operational communications for distinguishing supersession, correction, supplementation, contradiction, reopening, and unresolved conflict.

Suggested query: `natural language longitudinal dialogue supersession correction supplementation contradiction reopening unresolved conflict classification`

### gap-3 — ACADEMIC, HIGH — open

No admitted paper jointly evaluates source-relative factuality, temporal ordering, lifecycle state, contradiction, and provenance as one longitudinal model. FactBank covers source-relative factuality [doi-10-1007-s10579-009-9089-9], temporal papers cover ordering [1909.05360], ATMS covers conflicting support contexts [doi-10-1016-0004-3702-86-90080-9], provenance theory covers derivational lineage [doi-10-1007-3-540-44503-x-20], and commitment work covers lifecycle semantics [doi-10-1007-s10458-012-9202-0]. Their combination remains untested.

Suggested query: `"event factuality" temporal relation contradiction provenance lifecycle longitudinal model`

### gap-4 — ACADEMIC, HIGH — open

Direct evidence for workplace email, Teams-like dialogue, or comparable operational communication remains absent. CommitmentBank includes dialogue among several genres [doi-10-18653-v1-p19-1412], Re3 studies scientific revision [2406.00197], the event-sourcing study interviews industry practitioners [2104.01146], and the conflict-arbitration benchmark is synthetic [2608.20116]. None evaluates the target longitudinal workplace-language task.

Suggested query: `workplace email enterprise chat operational communication event state tracking factuality temporal revision commitment`

### gap-5 — ACADEMIC, HIGH — open

The factuality literature explicitly models source commitment rather than independently established truth [doi-10-1007-s10579-009-9089-9] [doi-10-18653-v1-2021-acl-long-122] [doi-10-18653-v1-2023-findings-acl-44]. HoVer and HeterMV address corroborating evidence in fact verification [2011.03088] [doi-10-1016-j-ipm-2026-104709], while Re3 cannot compare authentic author completion claims with observed edits [2406.00197].

No admitted paper establishes how to distinguish a claimed work-item completion from independently confirmed completion in longitudinal operational communication.

Suggested query: `event factuality evidentiality source attribution independent confirmation corroboration completion dialogue longitudinal`

### gap-6 — ENGINEERING, HIGH — open

Evaluation is still needed on adversarial longitudinal sequences such as plan-to-cancel, approve-to-revoke, deadline changes, contradictory same-time updates, out-of-order ingestion, stale messages arriving late, and completion claims later corrected.

The corpus contains isolated cancellation and conflict semantics [doi-10-1007-s10458-012-9202-0] [doi-10-1093-jos-ffn013], synthetic evidence conflicts [2608.20116], and formal temporal updates [doi-10-1016-0020-0255-94-90059-0], but no admitted benchmark covers this sequence family end to end.

### gap-7 — ENGINEERING, HIGH — open

The combined representation of message time, event/effective time, deadline or constraint time, and observed collection/version time has not been benchmarked for the target state-resolution task.

The temporal-database paper gives a related event-time, valid-time, transaction-time formalization [doi-10-1016-0020-0255-94-90059-0], while temporal NLP work evaluates ordering or relative timelines [doi-10-18653-v1-d18-1155] [1804.06020]. Neither evaluates the requested four-time combination.

### gap-8 — ENGINEERING, HIGH — open

The corpus does not evaluate a provenance-preserving implementation for this natural-language state-resolution task that stores immutable source observations and successive assessments while exposing a separately derived current-state view.

Relevant mechanisms exist separately in provenance theory [doi-10-1007-3-540-44503-x-20], ATMS [doi-10-1016-0004-3702-86-90080-9], and event-sourcing practice [2104.01146], but the target implementation and evaluation remain absent.

## Actionable Insights

- **Synthesis-derived recommendation:** represent source observations and later assessments as separate records so that changing assessments can be derived without deleting the observation history.
- **Synthesis-derived recommendation:** represent a source's assertion of completion separately from any independent corroboration or verification status; do not map the former directly to the latter.
- **Synthesis-derived recommendation:** model supersession, correction, supplementation, contradiction, reopening, and unresolved conflict as explicit relations or state-transition evidence rather than implementing a generic latest-message-wins rule.
- **Synthesis-derived recommendation:** keep message or utterance time, event or effective time, deadline or constraint time, and collection/version time separately addressable in the state representation.
- **Synthesis-derived recommendation:** allow unresolved competing assessments to coexist until evidence supports a resolution, while preserving which observations support each assessment.
- **Synthesis-derived recommendation:** make evidence completeness a separate concern from state-resolution reasoning so that an unresolved state caused by missing evidence is not silently converted into a negative or completed state.
- **Synthesis-derived recommendation:** build an adversarial longitudinal evaluation set containing cancellation, revocation, correction-of-correction, reopening, deadline replacement, out-of-order arrival, stale evidence, partial supplementation, contradictory same-time updates, and corrected completion claims.
- **Synthesis-derived recommendation:** evaluate rare and safety-relevant revision states explicitly with per-class and macro metrics instead of relying only on aggregate accuracy dominated by common states.
- **Synthesis-derived recommendation:** test any combined factuality-temporal-provenance-state scheme as a combined system; component-level success in separate papers should not be treated as validation of the composition.

## Confidence Summary

The corpus provides well-supported design principles at the component level. Source-relative factuality is established across several factuality and commitment studies [doi-10-1007-s10579-009-9089-9] [doi-10-18653-v1-2021-acl-long-122] [doi-10-18653-v1-2023-findings-acl-44]. Several temporal and state-tracking benchmarks demonstrate benefits from nonlocal or structured reasoning [1805.06975] [1804.06020] [doi-10-1162-tacl-a-00182] [manual-b3703967d3]. Formal dialogue, truth-maintenance, and provenance work provides explicit mechanisms for preserving earlier support, alternative contexts, or derivational history [doi-10-1093-jos-ffn013] [doi-10-1016-0004-3702-86-90080-9] [doi-10-1007-3-540-44503-x-20].

Confidence is high for those component-level findings within their demonstrated domains. Confidence is only medium for transferring them to longitudinal workplace communication because most empirical data is news, procedural narrative, scientific revision, fact verification, or synthetic conflict. Confidence is low that the corpus validates any unified production scheme. No admitted paper jointly tests factuality, temporal ordering, work-item lifecycle, revision relation, contradiction, provenance, and independent completion verification.

## Limitations

- No supplied empirical study directly evaluates the target problem on longitudinal workplace email, Teams-like chat, or comparable operational communication.
- The strongest NLP evidence is primarily transfer evidence from news, process narratives, scientific-paper revision, fact verification, and synthetic conflict tasks. It does not establish production-email accuracy.
- Several important contributions are formal or conceptual rather than corpus-scale empirical evaluations, including truth maintenance [doi-10-1016-0004-3702-86-90080-9], belief revision [doi-10-1017-cbo9780511526664-007], dialogue commitment [doi-10-1093-jos-ffn013], provenance [doi-10-1007-3-540-44503-x-20], and temporal databases [doi-10-1016-0020-0255-94-90059-0].
- The temporal-database paper was available only at abstract level [doi-10-1016-0020-0255-94-90059-0], HeterMV only through abstract/preview material [doi-10-1016-j-ipm-2026-104709], and the update-versus-revision paper through summary/introduction-level material [doi-10-1017-cbo9780511526664-007]. Their detailed methods and failure cases were therefore less inspectable.
- Several benchmarks have severe class imbalance or weak performance on rare states, including FactBank-derived factuality [doi-10-1007-s10579-009-9089-9], ExDLEF [doi-10-1007-s11390-024-2655-1], minority temporal relations [1909.05360], and CommitmentBank's no-commitment class [doi-10-18653-v1-p19-1412].
- The corpus validates factuality, temporal ordering, state tracking, provenance, revision, commitment, and evidence verification mostly as separate problems. Their combination is untested and has not been treated here as jointly validated.
- Some apparently conflicting results arise under different datasets or model formulations and therefore cannot be interpreted as direct replications of one another.
- The project context and Topic 05 handoff were treated only as scoping and inherited context. They were not used as evidence for findings and were not used to close any gap.
- The supplied analyses omit raw claims, so this synthesis relies on their provided findings, methodologies, limitations, and section references rather than independently rechecking underlying source passages.
- The paper count is 31 because the supplied corpus contains 31 analyzed paper identifiers with distinct titles; no same-title duplicate record was apparent in the supplied analyses.
