# Executive Summary

The corpus strongly supports msgloom's central premise that conversation structure, lexical similarity, shared participants, and generated labels are evidence for continuity but are not themselves work-matter identity. Direct enterprise-email evidence shows that real work activities cross reply-thread boundaries and that participants alone can confuse concurrent activities. Event-coreference and process-correlation literature further supports combining action, entity, participant, temporal, structural, and domain-constraint evidence while guarding against superficial similarity. Equally important, partial identity, subevents, membership, evolving events, and spatiotemporal continuity cannot always be represented as transitive equivalence clusters. Online systems therefore need explicit rejection or uncertainty, incremental evidence accumulation, and repairable identity state. However, the corpus still lacks direct Outlook-plus-Teams production evidence and does not establish msgloom-specific decision thresholds, correction semantics, or mappings from partial-event relations to workplace Topic continuity.

# Themes

## 1. Cross-thread structure is evidence, not identity

The clearest directly relevant enterprise-email result is that a user's work activity can span messages outside a single reply thread. Threading alone was materially weaker than approaches combining content, participants, and thread information, and the same participants may occur across several simultaneous activities [doi-10-1145-1111449-1111471]. A related enterprise-email study observed an actual confusion between two concurrently outstanding requests, showing that task identity can become lost across exchanges even when humans are mediating the workflow [doi-10-1145-1111449-1111472].

This directly supports the msgloom distinction between Group/conversation membership and Topic identity.

## 2. Identity requires multiple kinds of evidence

Cross-document event-coreference studies consistently show that useful identity signals extend beyond event wording. Joint entity-event models improve event decisions when participant entities and predicate-argument structure are resolved together [1906.01753]. Cross-corpus work shows that the relative importance of event action, time, participants, and context changes substantially across datasets [2011.12249]. Participant compatibility improves over action similarity alone in another study, although overly broad semantic action similarity can increase recall while substantially reducing precision [manual-61a7e10e5f].

Enterprise process-correlation literature points in the same direction. Data attributes and domain constraints improve reconstruction of concrete case identity when explicit case identifiers are absent [2206.10009], while an ER-grounded approach uses selected business entities as semantic anchors and deliberately filters broadly shared resource objects that could spuriously connect unrelated executions [2607.26384].

The resulting product implication is not that one particular feature set has been validated for msgloom, but that a single shared subject, customer, person, trigger, or embedding score is not a defensible identity rule [doi-10-3115-1220575-1220591].

## 3. Semantic similarity is necessary but dangerous

Lexical identity is too narrow: paraphrasing and metaphoric variation substantially degrade systems that depend heavily on trigger overlap even when the underlying event identity is preserved [2407.11988]. Conversely, semantic broadening can over-merge different instances of the same event class. TDT failure analysis describes representations drifting from a specific event toward a broad class, producing confusion among distinct crashes, bombings, or other similar events [doi-10-1145-290941-290954].

Argument-centric work demonstrates both sides explicitly: different events can share the same trigger, while the same event can use different triggers [doi-10-1038-s41598-025-32765-6]. Argument-aware and paraphrase-aware representations therefore provide useful identity evidence beyond simple lexical matching [doi-10-18653-v1-2020-coling-main-275].

For msgloom, semantic similarity should primarily support candidate generation and evidence accumulation, not independently authorize a merge.

## 4. Longitudinal continuity is richer than equivalence clustering

Dense event-identity annotation provides the strongest evidence against representing every meaningful longitudinal relationship as binary identity. Approximately one-third of annotated cross-document links in that study were candidates for partial identity, with membership, subevent relations, and spatiotemporal continuity among the recurring patterns [2109.06417]. The same analysis explicitly observes that partial identity can violate transitivity [2109.06417] [manual-c43ffe3135].

Subevent research similarly distinguishes full coreference, directed parent-child subevent relations, sister relations, and non-coreference [manual-35bac66e3c]. MAVEN-ERE takes a cleaner representational approach by keeping same-event coreference separate from temporal, causal, and subevent relations [2211.07342]. Earlier evaluation research likewise treats partial event coreference as hierarchical relations between conceptual event nodes rather than ordinary flat clusters [doi-10-3115-v1-w14-2910].

This strongly supports preserving a distinction between full SAME-MATTER identity and other continuity or relatedness relations. What remains unresolved is how those relation types map to msgloom's workplace semantics.

## 5. NEW, CONTINUE, and UNCERTAIN should be distinct outcomes

Classical record linkage formulates identity as a three-way decision among link, possible-link, and non-link rather than forcing every comparison into a binary answer [doi-10-1080-01621459-1969-10501049]. Open-world recognition similarly requires unknown inputs to be rejected before newly labeled classes are incorporated [1412.5687]. Selective classification provides a complementary risk-coverage formulation in which uncertain predictions can be withheld to control error on retained cases [1705.08500].

TDT provides domain-adjacent empirical motivation for this design. Online new-event detection was much harder than retrospective detection [doi-10-1145-290941-290953], and first-story detection remained difficult even when corresponding tracking systems were available [doi-10-1145-354756-354843]. The literature therefore gives no basis for treating "no confident existing match" as equivalent to "proven new matter."

For msgloom, UNCERTAIN should remain a first-class state rather than an implementation failure.

## 6. Identity should evolve as new evidence arrives

Later messages can contain evidence that was unavailable when a matter was first created. Adaptive TDT tracking consistently outperformed static tracking by updating the topic representation with newly accepted stories [doi-10-1002-asi-21264]. Another TDT study notes that important event-specific entities and facts may emerge well after initial stories and that adaptive rebuilding captures them [doi-10-1145-290941-290954].

Event coreference shows the same mechanism at a finer level: propagating arguments after event clusters are merged improves subsequent identity decisions [1707.07344]. Incremental entity resolution can incorporate new documents and merge historical clusters when new evidence changes the inferred structure [1402.4417]. Cross-organizational process linking can likewise use previously established mappings to discover additional activity connections iteratively [doi-10-1109-access-2023-3284053].

This supports versioned assessment rather than immutable first-pass classification.

## 7. Earlier decisions can be repaired without destroying identity history

Several adjacent fields provide concrete mechanisms for incremental correction. Incremental multi-source entity resolution shows that local reclustering can repair earlier decisions and reduce source-order sensitivity while approaching batch clustering quality [doi-10-1007-978-3-030-49461-2-23]. Stream clustering explicitly models emergence, disappearance, adjustment, split, and merge actions [doi-10-1109-tbdata-2022-3204207].

StableID addresses a related persistence problem: retaining historically supported identifiers across repeated entity-resolution runs greatly reduces identifier churn, and deterministic dominance rules make identifier survival after merges auditable [doi-10-3390-industries1010003].

These mechanisms strongly support msgloom's requirement for stable Topic IDs and later correction, but they do not themselves specify msgloom's append-only assessment, supersession, evidence-lineage, or merge/split semantics.

## 8. Concrete business objects can anchor enterprise identity

Process-mining research provides important enterprise analogues. An ER-grounded case notion uses a selected primary business entity as a semantic anchor and secondary entities to connect related executions; it deliberately filters resource-like and parent objects because broadly shared employees, equipment, customers, or other objects may spuriously merge unrelated cases [2607.26384].

The same study also reports incomplete cases as legitimate cases rather than treating missing expected events as evidence that the case does not exist [2607.26384]. This is relevant to an incremental work-information system where a matter may be only partially observed when first encountered.

Probabilistic event-case correlation similarly shows that correct data constraints improve concrete case reconstruction, whereas inaccurate constraints degrade it [2206.10009]. Learned rules can further improve correlation while producing human-readable explanations [doi-10-1109-icpm57379-2022-9980684].

The transfer is useful but indirect: a process case is not automatically equivalent to a msgloom Topic.

## 9. Bounded Phase 2 evidence seeking is plausible but not yet specified

CoreSearch demonstrates that cross-document event identity can be approached as retrieval from a query event rather than exhaustive global clustering [doi-10-18653-v1-2022-emnlp-main-58]. Other systems improve identity decisions through cross-document discourse structure or constructed coherent context [doi-10-18653-v1-2023-emnlp-main-294] [doi-10-1016-j-ipm-2025-104085] [doi-10-18653-v1-2025-acl-long-1134].

This supports msgloom's Phase 2 concept of retrieving additional historical evidence for an ambiguous candidate. It does not answer how much history to retrieve, when to stop, how to control latency, or whether a retrieval result actually changes the identity decision correctly.

## 10. Generalization and calibration are major deployment risks

Cross-corpus event-coreference performance degrades substantially when systems are evaluated on unseen corpora, and feature dependencies differ across ECB+, FCC-T, and GVC [2011.12249]. This directly cautions against interpreting one benchmark's score or threshold as a domain-independent identity guarantee.

Selective-classification research also finds that ordinary confidence and OOD scores can behave inconsistently when multiple shifts coexist [2405.05160]. Distance-aware calibration improves some shifted NLP conditions but is not uniformly superior to temperature scaling [doi-10-18653-v1-2024-findings-emnlp-725]. Perturbation-aware calibration can improve shifted-domain reliability while sometimes sacrificing in-domain behavior [manual-03d6dfa532].

Accordingly, the corpus does not justify production confidence thresholds for Outlook-plus-Teams work-matter identity.

# Contradictions

### Email metadata versus content

[doi-10-1145-1111449-1111471] finds threading insufficient and obtains much stronger activity linking when content is incorporated with other evidence. In contrast, [doi-10-1145-1111449-1111473] reports high-precision predefined-task prediction from sender, recipient, and subject features and finds no additional benefit from body words. These results concern different task definitions, granularity, and coverage regimes, so they should not be collapsed into a universal statement about whether message bodies matter.

### Topic pre-clustering: strong signal or benchmark shortcut

Topic pre-clustering is highly consequential on ECB+, and near-perfect topic clustering makes even a simple lemma baseline strong [1906.01753]. Cross-corpus research, however, warns that exploiting ECB+'s document-link distribution can overfit the corpus and generalize poorly [2011.12249]. WEC further removes the assumption that identity must remain within predefined topic partitions by allowing corpus-wide coreference [2104.05022]. For msgloom, coarse clustering may be useful for candidate generation but should not define identity boundaries.

### Transitive identity versus non-transitive continuity

Conventional coreference systems treat same-event identity as equivalence-style clusters [doi-10-18653-v1-2025-acl-long-1134]. Dense partial-identity annotation shows that membership, subevent, and spatiotemporal-continuity relations can be non-transitive [2109.06417] [manual-c43ffe3135]. MAVEN-ERE largely resolves the conceptual tension by representing coreference, subevent, temporal, and causal relations separately [2211.07342]. The contradiction appears when one clustering relation is asked to represent all of them.

### Forced assignment versus explicit uncertainty

EC-SA assigns every event to a case even when the event cannot be replayed as enabled by its process model [doi-10-1007-978-3-030-33223-5-12]. Record linkage instead preserves a possible-link region [doi-10-1080-01621459-1969-10501049], and open-world or selective classifiers explicitly reject uncertain instances [1412.5687] [1705.08500]. These approaches optimize different task contracts. Msgloom's requirement to avoid destructive false merges makes forced assignment an unsafe default unless independently validated.

### Semantic broadening versus precision

Semantic action matching can raise recall while reducing precision substantially [manual-61a7e10e5f]. Yet lexical diversity can also cause large failures when a system remains too dependent on exact triggers [2407.11988]. Argument-centric evidence provides a way through this tension because it helps distinguish same-trigger/different-event from different-trigger/same-event situations [doi-10-1038-s41598-025-32765-6].

# Open Gaps

## gap-1 — ACADEMIC — HIGH — OPEN

Which evidence combinations actually establish or refute continuity of a concrete work matter across independent workplace messages, conversations, attachments, email, and Teams remains open. Direct enterprise-email evidence confirms cross-thread activity linking [doi-10-1145-1111449-1111471], and event/process studies support combining entities, arguments, time, data attributes, and constraints [1906.01753] [2206.10009] [2607.26384]. None validates the required evidence combination for msgloom's concrete target-domain identity decision.

Suggested query:

`("work item identity" OR "work matter identity" OR "business event coreference" OR "cross-document event coreference") AND (email OR "workplace communication" OR enterprise) AND (cross-thread OR cross-document OR cross-source)`

## gap-2 — ENGINEERING — HIGH — OPEN

The msgloom-specific decision policy remains unresolved. Three-way linkage, open-world rejection, and selective prediction support possible-link/reject states and risk-coverage trade-offs [doi-10-1080-01621459-1969-10501049] [1412.5687] [1705.08500] [2405.05160], but no paper specifies msgloom's false-merge versus false-split loss, attachment threshold, or exact operational semantics of CONTINUE, NEW, and UNCERTAIN.

## gap-3 — ENGINEERING — HIGH — OPEN

The correction and identity-state model remains unresolved. Local reclustering, historical merging, stream merge/split operations, and persistent identifiers provide mechanisms [1402.4417] [doi-10-1007-978-3-030-49461-2-23] [doi-10-1109-tbdata-2022-3204207] [doi-10-3390-industries1010003]. They do not define msgloom's stable Topic-ID contract, versioned assessments, supersession links, immutable evidence lineage, or general MERGE/SPLIT history semantics.

## gap-4 — ACADEMIC — HIGH — OPEN

No paper in this corpus establishes longitudinal work-matter identity accuracy or representativeness across production Outlook email and Microsoft Teams. Enterprise-email studies provide direct adjacent evidence [doi-10-1145-1111449-1111471] [doi-10-1145-1111449-1111472], and cross-organizational process work provides additional enterprise evidence [doi-10-1109-access-2023-3284053], but the target environment remains unvalidated.

Suggested query:

`(enterprise OR workplace OR organizational) AND (email OR "Microsoft Teams" OR "enterprise chat" OR "workplace chat") AND (cross-thread OR longitudinal OR cross-conversation) AND ("topic identity" OR "task tracking" OR "case tracking" OR "event coreference" OR "conversation linking")`

## gap-5 — ACADEMIC — HIGH — OPEN

The literature now strongly establishes partial identity, membership, subevents, hierarchy, spatiotemporal continuity, and possible non-transitivity [2109.06417] [manual-c43ffe3135] [manual-35bac66e3c] [2211.07342] [doi-10-3115-v1-w14-2910]. It still does not establish how those relations should map to workplace decisions such as CONTINUE, RELATED-BUT-SEPARATE, MERGE, SPLIT, or another msgloom-specific relation.

Suggested query:

`("partial event identity" OR "partial coreference" OR "subevent relation" OR "event evolution" OR "event membership" OR "non-transitive coreference") AND (workflow OR task OR case OR workplace OR enterprise)`

## gap-6 — ENGINEERING — MEDIUM — OPEN

Retrieval-oriented event coreference and global-context models show that additional historical evidence can improve identity reasoning [doi-10-18653-v1-2022-emnlp-main-58] [doi-10-18653-v1-2023-emnlp-main-294] [doi-10-1016-j-ipm-2025-104085]. Msgloom still needs engineering benchmarks for candidate generation, bounded retrieval, latency, stopping rules, and whether retrieved evidence actually changes incorrect or uncertain decisions to correct ones.

## gap-7 — ACADEMIC — MEDIUM — OPEN

Calibration under non-stationary workplace streams remains unresolved. Cross-corpus and distribution-shift literature shows that confidence reliability deteriorates under shift and that selective, drift-aware, and conformal techniques can help [2011.12249] [2405.05160] [doi-10-18653-v1-2024-findings-emnlp-725] [manual-03d6dfa532] [doi-10-1038-s41598-026-40637-w]. None establishes reliable calibration, abstention thresholds, or coverage guarantees for longitudinal workplace coreference.

Suggested query:

`("selective classification" OR abstention OR "confidence calibration" OR "selective prediction") AND ("distribution shift" OR nonstationary OR streaming OR "concept drift") AND (text OR NLP OR coreference OR clustering)`

All seven carried-over gaps therefore remain open; none is closed by the round-4 corpus.

# Actionable Insights

1. Phase 1 should use a conservative identity rule: CONTINUE only when explicit evidence supports the same concrete matter. A low match score should be allowed to yield UNCERTAIN rather than automatically NEW [doi-10-1080-01621459-1969-10501049] [1705.08500].

2. Identity evidence should be recorded as auditable feature families rather than collapsed immediately into one semantic score: conversation ancestry, action/object, participants/entities, time, references, artifacts, state compatibility, and source structure all have plausible roles [1906.01753] [2011.12249] [2206.10009].

3. Subject, customer/project names, participants, and thread identifiers should support candidate generation and explanation but should not independently authorize merging [doi-10-1145-1111449-1111471] [doi-10-3115-1220575-1220591] [2607.26384].

4. The data model should distinguish full SAME-MATTER identity from RELATED, SUBEVENT/MEMBER, and EVOLVING-CONTINUITY relations. Transitive closure should apply only to relation types whose semantics justify equivalence [2109.06417] [2211.07342] [manual-35bac66e3c].

5. Identity history should be append-only and repairable: preserve stable Topic IDs, record versioned assessments and their evidence, and express later merge/split corrections explicitly rather than rewriting prior source or assessment history [doi-10-3390-industries1010003] [doi-10-1007-978-3-030-49461-2-23] [doi-10-1109-tbdata-2022-3204207].

6. Phase 2 should retrieve bounded history primarily for ambiguous candidates. Evaluation should measure whether retrieval changes a wrong or uncertain decision into a correct one, not merely whether relevant passages are retrieved [doi-10-18653-v1-2022-emnlp-main-58] [doi-10-18653-v1-2023-emnlp-main-294].

7. Engineering evaluation should contain adversarial pairs and sequences: same customer/project but different matters, same participants with parallel requests, renamed subjects, paraphrased continuations, delayed identifying facts, incomplete matters, and messages that continue several matters through different spans [doi-10-1145-1111449-1111471] [doi-10-1145-290941-290954] [2407.11988] [2607.26384].

8. False merges and false splits should be reported separately, alongside abstention coverage. Aggregate clustering F1 is insufficient for a product where a false merge can make an independent due matter disappear from a briefing [1705.08500] [2405.05160].

9. Deployment calibration should use temporal, workplace-like holdouts and deliberate drift tests rather than thresholds imported from ECB+, WEC, or generic classification benchmarks [2011.12249] [manual-03d6dfa532] [doi-10-18653-v1-2024-findings-emnlp-725].

# Confidence Summary

Confidence is **HIGH** for the structural conclusions that thread membership is not identity, multiple evidence dimensions are needed, lexical or participant similarity can cause false merges, uncertainty should be representable, and incremental identity requires repair [doi-10-1145-1111449-1111471] [1906.01753] [doi-10-1080-01621459-1969-10501049] [1402.4417]. Confidence is also **HIGH** that partial and evolving event relations cannot universally be collapsed into transitive equivalence clusters [2109.06417] [manual-c43ffe3135].

Confidence is **MEDIUM** when transferring process-case mechanisms and news-event coreference evidence to concrete workplace Topics [2206.10009] [2607.26384]. Confidence is **LOW** for any claim about production accuracy, optimal thresholds, or exact relation semantics in Outlook-plus-Teams because no study in the corpus directly validates msgloom's target environment.

# Limitations

Most of the identity literature concerns news event coreference, TDT, entity resolution, or process mining rather than longitudinal Outlook-plus-Teams work communication [2011.12249] [2206.10009]. The strongest direct enterprise-email study links messages to user work activities, which is closely relevant but not identical to msgloom's narrower concrete work-matter semantics [doi-10-1145-1111449-1111471].

Some strong coreference results use gold event mentions, so they do not represent end-to-end performance when candidate matter detection itself can fail [doi-10-1016-j-ipm-2025-104085]. The benchmarks also differ in topic partitioning, lexical diversity, annotation ontology, and relation semantics, making raw score comparison a weak basis for method selection [2104.05022] [2407.11988] [2011.12249].

Partial-event identity is itself difficult to annotate consistently: agreement is materially lower for partial identity than for clear full identity [2109.06417]. Process-correlation evidence also requires caution because one enterprise event collection may admit multiple plausible correlations or process views [doi-10-1007-s00778-010-0203-9], and database case notions can similarly represent alternative process perspectives [doi-10-1007-s10115-019-01430-6].

The supplied 50 analyses are not 50 independent studies. In particular, [1906.01753] and [manual-e988e24127] analyze the same underlying joint entity/event-coreference work, while [2109.06417] and [manual-c43ffe3135] analyze the same dense event-identity work. These duplicates should not be treated as independent replication.

Finally, open-world recognition, selective classification, and calibration papers establish useful uncertainty mechanisms but do not validate the semantic evidence needed for workplace work-matter identity itself [1412.5687] [1705.08500] [2405.05160].
