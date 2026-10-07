# Executive Summary

The corpus supports a robust transfer-level architecture for cross-thread work-matter identity, but it does not yet validate that architecture directly on longitudinal enterprise email and chat. Across event coreference, record linkage, entity resolution, topic tracking, and process correlation, the strongest recurring result is that identity should be inferred from multiple compatible signals rather than lexical or topical similarity alone. Incremental assignment with later repair is feasible, and explicit rejection or unresolved states are better supported than forced clustering when evidence is weak. New-event detection is consistently harder than tracking known matters. Partial, evolving, and subevent relations also challenge flat transitive clustering. However, corpus and domain shift materially degrade performance and calibration. For msgloom, the literature therefore supports conservative CONTINUE decisions, visible UNCERTAIN states, stable identities, versioned corrections, and bounded Phase 2 evidence retrieval, while leaving workplace-specific evidence weights, thresholds, relation semantics, and production accuracy unresolved.

# Themes

## 1. Identity is multi-dimensional, not semantic similarity

The strongest recurring pattern is that concrete identity should not be inferred from one convenient surface feature. Joint event/entity models show value from predicate-argument and entity relationships [1906.01753]. New-event work finds that names alone are insufficient because different events may share people, places, or organizations, and that names plus topical evidence separate old from new stories better than either alone [doi-10-3115-1220575-1220591]. Event-coreference experiments add participant, temporal, and spatial compatibility to action semantics [manual-61a7e10e5f], while business-process work shows that interpretable association rules can improve event-case assignment [doi-10-1109-icpm57379-2022-9980684].

For msgloom, this supports treating subject, customer/project names, participants, lexical overlap, conversation ancestry, references, actions, time, and state as separate evidence dimensions rather than identity keys.

## 2. Wider cross-document context can change an identity decision

Local mention evidence is often incomplete. Iterative event-coreference systems improve decisions by propagating arguments accumulated from already merged mentions [1707.07344]. Discourse-based models obtain additional gains from cross-document discourse structure and long-distance paths [doi-10-18653-v1-2023-emnlp-main-294]. A later system explicitly constructs discourse bridges between mentions from separate documents and reports further strong cross-document results [doi-10-1016-j-ipm-2025-104085].

This supports msgloom's Phase 2 premise that historical evidence seeking can resolve relationships that Phase 1 supplied content cannot safely decide.

## 3. UNCERTAIN is methodologically justified

The literature provides unusually strong support for an explicit unresolved state. Classical record linkage is a three-way decision problem with link, possible-link, and non-link outcomes [doi-10-1080-01621459-1969-10501049]. Open-world recognition explicitly rejects observations from unknown classes [1412.5687]. Selective classification controls error by sacrificing coverage [1705.08500], and reject-option text classification likewise routes uncertain cases to specialized handling rather than forcing the first-stage decision [doi-10-1007-978-3-540-27868-9-84].

For msgloom, failure to prove CONTINUE should therefore not automatically imply NEW. An UNCERTAIN relationship is a legitimate outcome.

## 4. Incremental identity plus later repair is feasible

Incremental entity-resolution work shows that newly arriving evidence can be compared against existing resolved entities without reprocessing the complete history, while still allowing historical clusters to merge when evidence changes [1402.4417]. Multi-source incremental entity resolution similarly finds that limited-depth reclustering can approach batch quality while repairing previous assignments and reducing arrival-order sensitivity [doi-10-1007-978-3-030-49461-2-23].

These results support the feasibility of stable Topic identities whose current relationships can be reassessed later rather than immutable one-shot clustering.

## 5. NEW is harder than CONTINUE

News-stream research repeatedly shows that identifying a genuinely new event is more difficult than tracking an already established one. Online event detection substantially trails retrospective detection [doi-10-1145-290941-290953]. First-story detection is characterized as intrinsically difficult given achievable tracking error [doi-10-1145-354756-354843]. Turkish TDT experiments likewise find tracking substantially easier than new-event detection [doi-10-1002-asi-21264].

This matters directly to msgloom: NEW should be an affirmative decision with its own evidence and evaluation, not simply the residue after no existing Topic exceeds a matching threshold.

## 6. Evolving continuity cannot always be represented as one flat equivalence cluster

Adaptive topic tracking improves continuity by updating the representation of a topic with newly accepted stories [doi-10-1002-asi-21264]. However, dense event-identity annotation finds that a substantial class of useful relationships are only partially identical, including membership, subevent, and spatiotemporal-continuity relations, and that such pairwise relations can violate transitivity [2109.06417]. Structural subevent research likewise distinguishes full identity from parent-child and sister relations [manual-35bac66e3c]. Evaluation work explicitly argues that ordinary flat coreference metrics are inadequate for hierarchical partial relations [doi-10-3115-v1-w14-2910].

Msgloom therefore should distinguish exact Topic identity from weaker forms of relatedness or evolution instead of simply expanding a cluster whenever two items are semantically connected.

## 7. Hard negatives and lexical variation are critical

ECB+ deliberately includes different instances of the same event type, which makes superficial similarity less reliable [1906.01753]. Metaphoric paraphrasing causes large performance drops for systems that are strong on ordinary ECB+, exposing reliance on trigger wording [2407.11988]. Argument-centric work presents both same-trigger/different-event and different-trigger/same-event cases [doi-10-1038-s41598-025-32765-6]. ECB+ itself arose partly because the earlier EventCorefBank underrepresented distinct instances within a domain [manual-f56d02b8f9].

A useful msgloom benchmark therefore needs both directions: nearly identical workplace messages belonging to different matters and one continuing matter whose wording, thread, participants, or channel changes.

## 8. Cross-domain generalization and calibration are weak points

Cross-corpus event-coreference evaluation finds substantial performance degradation when systems are applied to unseen corpora, and signals that work well on ECB+ are not sufficient elsewhere [2011.12249]. Calibration studies find that calibrators fitted only to in-domain validation data become increasingly overconfident under drift [manual-03d6dfa532]. Conformal selective prediction likewise shows deterioration under temporal/distribution shift despite calibration and deferral machinery [doi-10-1038-s41598-026-40637-w].

This prevents direct transfer of benchmark confidence thresholds into workplace streams.

## 9. Enterprise evidence exists, but it is adjacent rather than decisive

An enterprise email study reports high-precision classification of incoming messages into predefined user tasks from sender, recipient, and subject information [doi-10-1145-1111449-1111473]. Process-mining research shows that temporal activity relations, process models, cross-organizational activity connections, and learned association rules can reconstruct missing case relationships [doi-10-1007-978-3-030-33223-5-12] [doi-10-1109-access-2023-3284053] [doi-10-1109-icpm57379-2022-9980684].

These studies show that enterprise structure is useful evidence, but none establishes a production rule for stable work-matter identity across independent email threads, Teams conversations, attachments, and evolving work states.

## 10. Retrieval is promising for Phase 2, but requires application evaluation

CoreSearch demonstrates that a marked event can be used to retrieve likely cross-document coreferents without exhaustively clustering an entire collection [doi-10-18653-v1-2022-emnlp-main-58]. Iterative propagation and global discourse models also show that additional context can change difficult identity decisions [1707.07344] [doi-10-18653-v1-2023-emnlp-main-294].

The transferable conclusion is that evidence retrieval can help. The corpus does not answer how much history msgloom should search, when retrieval should stop, what latency is acceptable, or whether additional retrieved evidence improves final work-matter decisions rather than merely retrieval metrics.

# Contradictions

## Topic pre-clustering: strong signal versus benchmark overfitting

On ECB+, document topic clustering is extremely consequential: near-perfect topic clustering makes even a lemma-based baseline strong, and adding clustering substantially improves another system [1906.01753] [manual-e988e24127]. In contrast, cross-corpus evaluation warns that ECB+-specific preclustering and document-link assumptions can generalize poorly [2011.12249].

These findings are compatible only if preclustering is treated as dataset-dependent candidate-generation evidence rather than identity itself. For msgloom, Group or conversation structure may narrow candidates but should not establish Topic continuity.

## Forced assignment versus explicit uncertainty

EC-SA assigns every event to exactly one case even when it cannot be replayed as enabled by the process model [doi-10-1007-978-3-030-33223-5-12]. Classical linkage instead reserves a possible-link region [doi-10-1080-01621459-1969-10501049], while open-world and selective-classification methods explicitly reject uncertain observations [1412.5687] [1705.08500].

The tasks have different assumptions, so this is not a methodological error in the process-mining paper. Nevertheless, msgloom's asymmetric cost of false merging makes the reject/uncertain family much better aligned with the product requirement.

## Simple communication metadata versus richer identity evidence

The enterprise task-recognition study found that sender, recipient, and subject were enough to obtain high precision for assigning incoming email to predefined user tasks, and email-body words added no benefit in its experiment [doi-10-1145-1111449-1111473]. New-event detection shows that high-IDF names alone cannot establish event identity [doi-10-3115-1220575-1220591], while joint event/entity work benefits from richer argument structure [1906.01753].

This is an apparent rather than literal contradiction: predefined task classification and longitudinal matter identity are different label spaces. It nonetheless cautions against treating enterprise metadata that predicts a known task as proof that two messages instantiate the same work matter.

## Flat clustering versus non-transitive partial identity

Mainstream CDCR systems represent event identity as equivalence-style clusters [1906.01753] [2104.05022]. Dense partial-identity annotation finds membership, subevent, and spatiotemporal-continuity relations that can violate transitivity [2109.06417] [manual-c43ffe3135], while structural work explicitly represents parent-child and sister subevents [manual-35bac66e3c].

Thus one data model cannot safely use the same transitive relation for both exact identity and all forms of evolving relatedness.

## Process constraints versus multiple plausible correlations

Process-model conformance can materially improve event-case correlation when the process model is accurate [doi-10-1007-978-3-030-33223-5-12]. Conversely, Web-service interaction logs can admit several plausible event correlations and process views, making user guidance useful [doi-10-1007-s00778-010-0203-9].

Workflow state and process structure should therefore contribute evidence but should not be assumed to uniquely determine work-matter identity.

## Strong lexical baselines versus lexical fragility

Lemma-based methods can be remarkably competitive on structurally favorable ECB+ settings [1906.01753]. Yet their robustness falls when lexical diversity is deliberately increased [2407.11988], and argument-centric analyses show both identical triggers for different events and different triggers for the same event [doi-10-1038-s41598-025-32765-6]. The motivation for ECB+ itself was partly the insufficient event diversity of its predecessor [manual-f56d02b8f9].

Lexical similarity is therefore useful evidence, but not an identity criterion.

# Open Gaps

## gap-1 — ACADEMIC — HIGH

Which evidence combinations actually establish or refute continuity of a concrete work matter across independent workplace messages, conversations, attachments, email, and Teams remains open. The corpus supports adjacent-domain combinations of arguments, participants, names, topical terms, temporal compatibility, discourse, metadata, and process constraints [1906.01753] [manual-61a7e10e5f] [doi-10-1109-icpm57379-2022-9980684], while the enterprise email study provides direct but task-classification rather than identity evidence [doi-10-1145-1111449-1111473]. It does not validate subject, customer/project names, conversation ancestry, referenced artifacts, commitments, or state compatibility as target-domain identity evidence.

Suggested query: `("work item identity" OR "work matter identity" OR "business event coreference" OR "cross-document event coreference") AND (email OR "workplace communication" OR enterprise) AND (cross-thread OR cross-document OR cross-source)`

**Status: open.**

## gap-2 — ENGINEERING — HIGH

The application-specific decision policy remains open. Record linkage, open-world recognition, selective classification, and conformal deferral justify rejection and risk-coverage trade-offs [doi-10-1080-01621459-1969-10501049] [1412.5687] [1705.08500] [doi-10-1038-s41598-026-40637-w], but none establishes msgloom's relative false-merge versus false-split loss, thresholds for attachment versus rejection, or exact CONTINUE, NEW, and UNCERTAIN semantics.

**Status: open.**

## gap-3 — ENGINEERING — HIGH

The msgloom correction and identity-state model remains open. Incremental entity-resolution methods demonstrate local cluster merging, reclustering, and repair [1402.4417] [doi-10-1007-978-3-030-49461-2-23], but they do not define stable Topic IDs independent of labels and source threads, versioned identity assessments, supersession links, immutable evidence lineage, or msgloom-specific MERGE/SPLIT semantics.

**Status: open.**

## gap-4 — ACADEMIC — HIGH

There is still no direct production-domain evidence for longitudinal work-matter identity across Outlook email and Microsoft Teams. The corpus contains enterprise email task recognition [doi-10-1145-1111449-1111473] and business-process/cross-organizational correlation [doi-10-1007-s00778-010-0203-9] [doi-10-1109-access-2023-3284053], but neither establishes accuracy or representativeness for the target problem.

Suggested query: `(enterprise OR workplace OR organizational) AND (email OR "Microsoft Teams" OR "enterprise chat" OR "workplace chat") AND (cross-thread OR longitudinal OR cross-conversation) AND ("topic identity" OR "task tracking" OR "case tracking" OR "event coreference" OR "conversation linking")`

**Status: open.**

## gap-5 — ACADEMIC — HIGH

How partial, subevent, evolving, membership, or otherwise non-transitive relations should map onto workplace work-matter continuity remains unresolved. The corpus now gives strong evidence that these relations exist and can violate transitivity [2109.06417] [manual-c43ffe3135] [manual-35bac66e3c], and partial-coreference evaluation explicitly requires richer structures than ordinary flat clustering [doi-10-3115-v1-w14-2910]. No reviewed paper defines when such relationships should mean CONTINUE, RELATED-BUT-SEPARATE, MERGE, SPLIT, or another workplace-specific relation.

Suggested query: `("partial event identity" OR "partial coreference" OR "subevent relation" OR "event evolution" OR "event membership" OR "non-transitive coreference") AND (workflow OR task OR case OR workplace OR enterprise)`

**Status: open.**

## gap-6 — ENGINEERING — MEDIUM

The best Phase 2 evidence-seeking strategy remains unresolved. Retrieval-based event-coreference search demonstrates scalable candidate retrieval [doi-10-18653-v1-2022-emnlp-main-58], and iterative/global-context approaches show that additional evidence improves some identity decisions [1707.07344] [doi-10-18653-v1-2023-emnlp-main-294]. Msgloom still needs benchmarks for historical-search bounds, candidate generation, latency, stopping rules, and whether retrieved evidence changes the final identity decision correctly.

**Status: open.**

## gap-7 — ACADEMIC — MEDIUM

Calibration under non-stationary workplace streams remains unresolved. Cross-corpus event coreference demonstrates distribution sensitivity [2011.12249]. Drift-aware calibration reduces shifted-domain calibration error in other domains [manual-03d6dfa532], and conformal/selective prediction provides further evidence that uncertainty guarantees deteriorate under temporal shift [doi-10-1038-s41598-026-40637-w]. These papers substantially strengthen the mechanism-level evidence but do not establish reliable calibration or abstention under streaming workplace coreference and evolving Topic clusters.

Suggested query: `("selective classification" OR abstention OR "confidence calibration" OR "selective prediction") AND ("distribution shift" OR nonstationary OR streaming OR "concept drift") AND (text OR NLP OR coreference OR clustering)`

**Status: open.**

# Actionable Insights

1. **Phase 1 should be conservative.** Require explicit positive continuity evidence before assigning CONTINUE. Otherwise keep the candidate separate as UNCERTAIN rather than translating weak matching into NEW [doi-10-1080-01621459-1969-10501049] [1412.5687] [1705.08500].

2. **Do not use structural shortcuts as identity keys.** Conversation ancestry, subject, customer/project name, participant overlap, lexical similarity, and generated Topic labels should be candidate-generation or evidence features only [doi-10-3115-1220575-1220591] [1906.01753] [2011.12249].

3. **Expose the evidence vector.** Useful dimensions include action/object semantics, participant/entity compatibility, time, location where relevant, references, discourse relationships, and workflow/state compatibility [1906.01753] [manual-61a7e10e5f] [doi-10-18653-v1-2023-emnlp-main-294].

4. **Separate exact identity from relatedness.** Subevent, membership, evolution, and related-but-separate relations should not share the same transitive semantics as CONTINUE [2109.06417] [manual-35bac66e3c] [doi-10-3115-v1-w14-2910].

5. **Use stable Topic IDs with versioned assessments.** New evidence should be able to trigger MERGE or SPLIT corrections without rewriting historical source evidence. Incremental entity-resolution results make local repair technically plausible [1402.4417] [doi-10-1007-978-3-030-49461-2-23].

6. **Evaluate NEW independently.** First-story/new-event work shows that novelty detection is harder than tracking [doi-10-1145-354756-354843] [doi-10-1002-asi-21264]. The benchmark should therefore distinguish false CONTINUE, false NEW, and appropriate UNCERTAIN outcomes.

7. **Create adversarial identity fixtures.** Include same subject/customer/participants but different work matters, and the same matter under changed wording, thread, participants, or channel [1906.01753] [2407.11988] [doi-10-1038-s41598-025-32765-6].

8. **Use Phase 2 retrieval selectively.** Retrieve historical evidence when the local decision is uncertain and evaluate whether retrieval changes the identity decision correctly, not merely whether relevant documents appear in the candidate set [doi-10-18653-v1-2022-emnlp-main-58] [1707.07344].

9. **Calibrate on representative and shifted conditions.** Confidence thresholds from ECB+, Wikipedia, news, process logs, or other domains should not be transferred unchanged into workplace streams [2011.12249] [manual-03d6dfa532] [doi-10-1038-s41598-026-40637-w].

10. **Prioritize error semantics over aggregate clustering F1.** False merges, false splits, NEW-versus-UNCERTAIN mistakes, correction quality, and loss of due work should be first-class evaluation outputs. Partial-coreference work shows that ordinary flat metrics can conceal important structural errors [doi-10-3115-v1-w14-2910] [2109.06417].

# Confidence Summary

Confidence is **HIGH** for the transfer-level conclusions that identity requires multi-signal evidence, uncertainty should be represented explicitly, new-event detection is harder than tracking, incremental repair is technically feasible, and benchmark/domain shift materially affects results. These conclusions recur across independent research traditions including event coreference, record linkage, entity resolution, topic detection and tracking, and selective prediction [1906.01753] [doi-10-1080-01621459-1969-10501049] [1402.4417] [doi-10-1145-354756-354843] [2011.12249].

Confidence is **MEDIUM** for applying specific evidence dimensions and retrieval strategies to msgloom because enterprise-oriented papers address adjacent task classification and process correlation rather than exactly the target cross-thread identity problem [doi-10-1145-1111449-1111473] [doi-10-1109-access-2023-3284053].

Confidence is **LOW** for any production-accuracy claim, universal threshold, evidence weighting, or Outlook/Teams representativeness because the corpus contains no direct longitudinal target-domain benchmark.

# Limitations

- The synthesis uses the supplied reduced per-paper analyses rather than independently inspecting the complete text of every paper. The conclusions are therefore bounded by the information represented in those analyses.

- The 38 `paper_id` entries are not 38 fully independent research works. In particular, [1906.01753] and [manual-e988e24127] describe the same titled joint entity/event-coreference work, while [2109.06417] and [manual-c43ffe3135] describe the same titled dense event-identity work.

- Most experimental evidence comes from news, Wikipedia, image recognition, public-health linkage, knowledge graphs, process logs, or other transfer domains rather than longitudinal workplace communication [2011.12249] [2104.05022] [doi-10-1038-s41598-026-40637-w].

- The directly relevant enterprise email paper classifies messages into predefined user tasks; it does not discover and maintain cross-thread work-matter identities [doi-10-1145-1111449-1111473].

- Some high-performing CDCR systems evaluate with gold event mentions, so their scores exclude errors from end-to-end event or matter detection [doi-10-1016-j-ipm-2025-104085].

- Standard event-coreference metrics assume flat equivalence-style clustering and are not well aligned with partial, evolving, hierarchical, or non-transitive workplace relationships [doi-10-3115-v1-w14-2910] [2109.06417].

- Benchmark scores are not directly comparable across datasets, candidate-generation regimes, mention assumptions, corpus partitions, and metric implementations [2011.12249] [2104.05022].

- The corpus does not determine msgloom's operational loss for false merges, false splits, missed new matters, or excessive abstention. Selective-prediction and linkage literature supplies mechanisms, not the product-specific cost function [1705.08500] [doi-10-1080-01621459-1969-10501049].

- No reviewed study directly evaluates one concrete work matter moving longitudinally among Outlook email, Teams chat, attachments, and independent conversation threads. The central target-domain evidence gap therefore remains open.
