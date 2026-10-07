# Executive Summary

The literature strongly supports treating longitudinal work-matter identity as an open-world, incremental identity-resolution problem rather than ordinary semantic clustering. Continuation decisions should combine multiple identity-bearing signals, permit abstention, and preserve sufficient historical evidence for later merge or split correction. Incremental entity-resolution work shows that localized reassessment can approach batch quality while avoiding full recomputation, but naive incremental assignment can become order-dependent. Event-coreference research shows that action similarity alone is insufficient across domains: participants, time, location, arguments, and context materially affect identity, while partial or quasi-identity can be non-transitive. New-event and selective-classification work further supports an explicit UNCERTAIN/reject outcome rather than forcing attachment or novelty. However, the evidence is primarily from news, Wikipedia, entity resolution, image recognition, and public-record linkage; none establishes production accuracy for cross-thread email and Teams work matters.

The synthesis contains 14 papers.

# Themes

## 1. Identity requires structured evidence, not similarity alone

Cross-document identity should be decided from multiple compatibility signals rather than semantic or action similarity alone. Cross-corpus event-coreference analysis shows that feature importance changes materially by dataset: ECB+ can rely heavily on event-action information, while FCC-T and GVC require a more balanced use of time, participants, and context [2011.12249]. CoreSearch error analysis similarly found argument inconsistency to be a prominent source of false coreference decisions [doi-10-18653-v1-2022-emnlp-main-58]. Classical probabilistic record linkage likewise treats agreements as evidence with different discriminative value rather than deterministic proof of identity [doi-10-1002-sim-4780140510].

For msgloom, same subject, customer, project, participant set, or embedding neighborhood should therefore be treated mainly as candidate-generation evidence. Positive continuation should depend on compatibility across several identity-bearing dimensions.

## 2. UNCERTAIN is a legitimate outcome

Open-world recognition explicitly rejects observations unsupported by known classes rather than forcing them into an existing class [1412.5687]. Selective classification formalizes the same principle as a risk-coverage trade-off: lower error can be obtained by abstaining on lower-confidence cases [1705.08500]. TDT first-story work shows why this matters in streams: small tracking errors accumulate badly when novelty must be judged against many historical items [doi-10-1145-354756-354843].

This strongly supports msgloom's distinction between “no confident continuation” and “proven NEW Topic.” In Phase 1, insufficient evidence should remain visible as UNCERTAIN rather than being converted into an unsupported merge or novelty claim.

## 3. Incremental continuity can be efficient without freezing history

Incremental ERLD combines new documents with previously resolved entities and can merge historical clusters when new evidence changes the identity structure; its reported incremental results remain close to batch quality while reconsidering only affected state [1402.4417]. Incremental multi-source entity resolution reaches a similar conclusion: local incremental processing can approach batch resolution while avoiding complete historical recomputation [doi-10-1007-978-3-030-49461-2-23].

The important design consequence is that an online assignment should be an assessment, not an irreversible rewrite. New evidence must be able to trigger later MERGE or SPLIT correction.

## 4. Arrival order and repairability matter

Simple max-both incremental assignment can become sensitive to source arrival order, while one-depth reclustering substantially reduces that dependency and recovers approximately batch-level quality in the reported experiments [doi-10-1007-978-3-030-49461-2-23].

The same work exposes a storage trade-off: cluster fusion reduces processing cost but discards intra-cluster links required by its repair-oriented reclustering method [doi-10-1007-978-3-030-49461-2-23]. For msgloom, derived Topic state should therefore not destroy the linkage evidence needed to reconstruct why items were joined and to revisit those decisions later.

## 5. Conversation or document structure helps, but is not identity

Document topic preclustering substantially improves ECB+ event-coreference performance in the joint entity/event system [manual-e988e24127]. However, cross-dataset analysis finds that ECB+-specific preclustering and document-link assumptions can overfit that corpus and generalize poorly [2011.12249]. WEC-to-ECB+ and ECB+-to-WEC transfer also loses substantial performance [2104.05022].

The appropriate msgloom interpretation is therefore narrow: Group ancestry, thread membership, source structure, and similar metadata can reduce the candidate search space or strengthen an assessment, but they must not define Topic identity.

## 6. Relatedness is broader than identity

Dense cross-document annotation finds that a substantial portion of event links represent partial rather than full identity, including membership, subevent relations, and spatiotemporal continuity. These relations can violate transitivity [manual-c43ffe3135].

That result is highly relevant to work matters. Two messages may concern strongly related stages or subevents without belonging to one concrete Topic identity. Stable Topic IDs should remain coherent and transitive where identity is asserted, while related-but-not-identical and uncertain relationships should remain separate relation types.

## 7. Retrieval-first investigation is viable for Phase 2

CoreSearch reformulates exhaustive cross-document clustering as query-oriented retrieval followed by explicit coreference assessment across a collection containing roughly one million distractor passages per split [doi-10-18653-v1-2022-emnlp-main-58]. Its dense retriever outperforms BM25, and explicit coreference scoring improves downstream reranking and mention detection [doi-10-18653-v1-2022-emnlp-main-58].

However, its error analysis also found cases where the local query and candidate contexts were insufficient to establish identity [doi-10-18653-v1-2022-emnlp-main-58]. This maps well to the Phase 1/Phase 2 boundary: Phase 1 should avoid unsupported linkage, while Phase 2 can retrieve bounded historical evidence and investigate further.

## 8. Evaluation must separate different failure modes

TDT explicitly separates tracking, link detection, topic detection, first-story detection, and segmentation rather than treating stream organization as one metric [manual-5c20fb0229]. Selective classification adds risk versus coverage as a separate evaluation dimension [1705.08500]. First-story detection work shows that novelty detection can be substantially harder than ordinary tracking [doi-10-1145-354756-354843].

For msgloom, continuation/linking, NEW detection, UNCERTAIN coverage, clustering quality, false merges, false splits, MERGE repair, and SPLIT repair should therefore be measured separately. A single aggregate clustering score can conceal exactly the errors most dangerous to briefing coverage.

# Contradictions

## Document/topic preclustering: useful signal versus unsafe identity shortcut

On ECB+, document topic clustering materially improves event-coreference results [manual-e988e24127]. On the other hand, cross-corpus work shows that ECB+-specific document-link and preclustering assumptions can overfit and transfer poorly [2011.12249], and WEC/ECB+ cross-corpus experiments show substantial degradation [2104.05022].

This is best treated as a boundary condition rather than a logical contradiction. Structural grouping is useful for candidate generation and contextual evidence, but msgloom should preserve the project rule that Group or conversation membership is not Topic identity.

## Simple incremental attachment versus repair-oriented incremental clustering

Incremental ERLD reports results close to batch resolution while processing only affected historical state [1402.4417]. In contrast, the FAMER incremental study finds that a simpler max-both assignment can be source-order sensitive and that bounded reclustering is needed to recover approximately batch-level quality [doi-10-1007-978-3-030-49461-2-23].

The difference indicates that the amount of repair machinery required depends on data structure, matcher errors, and arrival patterns. Msgloom should not assume that a one-shot online attachment rule will remain stable under delayed or reordered evidence.

## Transitive cluster identity versus non-transitive relatedness

Entity-resolution systems naturally represent identity with transitive clusters [1402.4417] [doi-10-1007-978-3-030-49461-2-23]. Dense event annotation, however, identifies partial-identity relations that can violate transitivity [manual-c43ffe3135].

For msgloom, the clean resolution is to keep Topic identity itself coherent while storing subevent, evolution, continuation-like, and uncertain relationships outside the identity equivalence relation.

## Similarity-based tracking versus structure-aware identity modeling

TDT evidence shows that repeated full-text similarity tracking produces poor first-story detection at practically useful operating points [doi-10-1145-354756-354843]. Later event-coreference work finds that participants, time, arguments, and explicit coreference scoring add important discriminatory evidence [2011.12249] [doi-10-18653-v1-2022-emnlp-main-58].

This argues strongly against making embedding or lexical similarity the identity rule.

# Open Gaps

## G03-1 — Direct workplace benchmark

**Classification:** ACADEMIC  
**Priority:** HIGH

There is no direct benchmark in this corpus for cross-thread, cross-channel concrete work-matter identity in enterprise email and chat. The reviewed event-coreference resources are news- or Wikipedia-oriented [2011.12249] [2104.05022] [manual-c43ffe3135], and their results cannot establish accuracy for same-project-but-different-matter cases, subject changes, multi-matter messages, or movement between email and Teams.

Suggested query: `"work item identity" email chat cross-thread enterprise OR "cross-channel" conversation linking work matter`

## G03-2 — Calibrated CONTINUE / NEW / UNCERTAIN policy

**Classification:** ACADEMIC  
**Priority:** HIGH

Open-world and selective-classification research supports rejection and risk-coverage reasoning [1412.5687] [1705.08500], and TDT shows the difficulty of novelty detection [doi-10-1145-354756-354843], but this corpus does not establish a calibrated decision rule for CONTINUE versus NEW versus UNCERTAIN under msgloom's asymmetric cost structure, where false merges deserve especially harsh treatment.

Suggested query: `"event coreference" abstention reject option open set OR "cluster assignment" abstention asymmetric cost`

## G03-3 — Partial identity and multi-matter continuation

**Classification:** ACADEMIC  
**Priority:** MEDIUM

Partial identity is demonstrably important and sometimes non-transitive [manual-c43ffe3135], but more evidence is needed on evolving work matters and messages containing multiple spans that continue different historical Topics.

Suggested query: `"partial event coreference" event evolution subevent cross-document multi-event`

## G03-4 — Msgloom-specific identity benchmark

**Classification:** ENGINEERING  
**Priority:** HIGH

Build an independent synthetic/adversarial evaluation suite plus suitable transfer datasets. Measure false merges, false splits, CONTINUE accuracy, NEW detection, UNCERTAIN coverage, insertion-order sensitivity, and correction quality. Cross-corpus fragility makes this engineering work necessary even before production-domain data are available [2011.12249] [2104.05022].

## G03-5 — Stable ID and correction data model

**Classification:** ENGINEERING  
**Priority:** HIGH

Define immutable Topic IDs and versioned relationship assessments covering CONTINUE, NEW, UNCERTAIN, MERGE, and SPLIT. Preserve source evidence, assessment provenance, and reconstructable correction history. Incremental-resolution evidence shows that historical identity decisions may legitimately change when new evidence arrives [1402.4417] [doi-10-1007-978-3-030-49461-2-23].

## G03-6 — Minimum retained evidence for repair

**Classification:** ENGINEERING  
**Priority:** HIGH

Determine which pairwise links, feature evidence, cluster history, and provenance must remain available for bounded reclustering and split/merge repair. The known trade-off between cluster fusion and repairability makes destructive compression risky [doi-10-1007-978-3-030-49461-2-23].

## G03-7 — Phase 2 candidate retrieval benchmark

**Classification:** ENGINEERING  
**Priority:** MEDIUM

Compare deterministic indexes, sparse retrieval, dense retrieval, and hybrids for historical candidate generation. Measure candidate recall, latency, and downstream identity accuracy. CoreSearch demonstrates that retrieval-first cross-document coreference is feasible at large candidate-set scale, while also showing that retrieval alone does not solve identity [doi-10-18653-v1-2022-emnlp-main-58].

## G03-8 — Topic-title optimization

**Classification:** OUT_OF_SCOPE  
**Priority:** LOW

Improving generated Topic titles or labels is not an identity problem. Titles are presentation metadata and should not be used as stable identifiers. The reviewed literature supports identity representations based on relational evidence and clusters rather than generated display names [1402.4417] [doi-10-1007-978-3-030-49461-2-23].

There are no prior-round gaps supplied with this synthesis, so `gap_status` is empty.

# Actionable Insights

1. Represent Topic identity with stable internal IDs independent of generated titles, subjects, conversation IDs, or source-specific thread IDs.

2. In Phase 1, link a candidate to an existing Topic only when supplied evidence positively supports identity. Otherwise preserve it separately with an explicit UNCERTAIN relationship rather than forcing CONTINUE or NEW. This is consistent with open-world rejection and selective prediction [1412.5687] [1705.08500].

3. Use semantic similarity, subject, participants, customer/project names, and conversation ancestry primarily for candidate generation. Require additional identity-compatible evidence before merging because feature importance varies by corpus and argument inconsistencies produce false matches [2011.12249] [doi-10-18653-v1-2022-emnlp-main-58].

4. Combine positive and negative evidence across action/object, participants, time, location, referenced artifacts, commitments, state compatibility, and source relationships. Temporal or argument conflict should be able to veto a superficially similar match [2011.12249] [doi-10-18653-v1-2022-emnlp-main-58].

5. Persist versioned identity assessments and provenance so later MERGE or SPLIT corrections add history instead of rewriting earlier evidence. Incremental entity-resolution methods explicitly allow new data to revise earlier clustering [1402.4417] [doi-10-1007-978-3-030-49461-2-23].

6. Retain enough pairwise or graph-level historical evidence to support bounded local reclustering. Avoid irreversible fusion that destroys evidence needed for repair [doi-10-1007-978-3-030-49461-2-23].

7. Test incremental assignment under adversarial insertion orders and delayed evidence because arrival order can materially affect a non-repairing incremental method [doi-10-1007-978-3-030-49461-2-23].

8. Calibrate a reject/UNCERTAIN threshold using risk-coverage style evaluation, with a deliberately higher penalty for false merges than false splits under msgloom's reporting objective [1705.08500].

9. For Phase 2, retrieve a bounded set of historical candidate Topics and supporting evidence, then rerun identity assessment rather than expanding every Phase 1 decision across the complete history [doi-10-18653-v1-2022-emnlp-main-58].

10. Evaluate continuation, novelty, uncertainty, merge repair, and split repair separately. Aggregate clustering F1 alone can hide the failure modes that matter most to missing or duplicating actionable work [manual-5c20fb0229] [doi-10-1145-354756-354843].

# Confidence Summary

Confidence is **HIGH** for the architectural conclusions that identity should be multi-signal, incremental, repairable, and allowed to abstain. These mechanisms recur across entity resolution [1402.4417] [doi-10-1007-978-3-030-49461-2-23], event coreference [2011.12249] [manual-c43ffe3135], open-world recognition [1412.5687], selective classification [1705.08500], and TDT [doi-10-1145-354756-354843].

Confidence is also **HIGH** that single-benchmark performance does not demonstrate general robustness because cross-corpus degradation is repeatedly observed [2011.12249] [2104.05022].

Confidence is **MEDIUM** for the exact decision policy msgloom should use. No reviewed paper directly evaluates enterprise email/Teams work-matter identity, asymmetric false-merge costs, or the five-way CONTINUE/NEW/UNCERTAIN/MERGE/SPLIT contract. The transfer literature justifies mechanisms and experiments, not production-domain accuracy claims.

# Limitations

- No paper in the corpus directly evaluates concrete work-matter identity across enterprise email and Teams or an equivalent work-communication domain.

- Several of the strongest results come from news or Wikipedia event coreference, whose document structure, annotation assumptions, and event distributions differ materially from workplace communication [2011.12249] [2104.05022] [doi-10-18653-v1-2022-emnlp-main-58].

- Open-world and selective-classification evidence comes from image recognition. It strongly supports abstention and calibration mechanisms but does not establish text-identity accuracy [1412.5687] [1705.08500].

- Entity-resolution papers concern people, companies, records, or knowledge-graph entities. Their transitive identity assumptions transfer imperfectly to evolving work matters [1402.4417] [doi-10-1007-978-3-030-49461-2-23].

- The public-health probabilistic-linkage paper and TDT overview were available only at abstract level, limiting verification of experimental details [doi-10-1002-sim-4780140510] [manual-5c20fb0229].

- Many event-coreference evaluations assume gold event mentions or pre-existing topic partitions, so they do not measure end-to-end errors introduced by Topic-02 span detection or unrestricted historical candidate generation [2104.05022] [manual-c43ffe3135] [manual-e988e24127].

- The synthesis cannot determine production thresholds, calibration values, or acceptable UNCERTAIN coverage without engineering evaluation on independently constructed fixtures and, later, suitable authorized domain data.
