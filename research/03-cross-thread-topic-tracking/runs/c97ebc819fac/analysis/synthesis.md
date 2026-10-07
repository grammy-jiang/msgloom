# Executive Summary

Across 14 papers, adjacent-domain evidence supports an architectural hypothesis for msgloom: longitudinal work-matter resolution is likely to benefit from open-world rejection, multi-signal identity reasoning, incremental assignment, and repair-capable historical state rather than forced similarity clustering. Event-coreference studies show that useful identity signals and benchmark structure vary substantially across corpora, while open-world and selective-classification work establishes general mechanisms for rejecting uncertain assignments. Incremental entity-resolution studies show that new evidence can revise earlier clustering without complete recomputation, although specific repair algorithms impose specific state-retention requirements. Partial event identity can also be non-transitive. None of these findings directly validates msgloom's CONTINUE/NEW/UNCERTAIN semantics, workplace-specific evidence features, error-cost policy, stable-ID implementation, or correction model. Those remain explicit engineering or academic gaps, and no reviewed benchmark establishes production accuracy for longitudinal Outlook/Teams work matters.

# Themes

The recurring themes are:

- Identity resolution requires more than generic textual similarity in the reviewed adjacent domains; event arguments, participants, time, context, linkage structure, and related-mention information can matter, but their importance varies by corpus. [2011.12249] [manual-e988e24127]
- Open-world recognition and selective classification provide mechanisms for rejecting or abstaining on uncertain assignments instead of forcing every observation into a known class. [1412.5687] [1705.08500]
- Incremental entity resolution can update identity state using only affected historical regions and can revise some earlier clustering decisions without a complete batch rerun. [1402.4417] [doi-10-1007-978-3-030-49461-2-23]
- Repairability depends on algorithm-specific retained state: FAMER's bounded n-depth reclustering specifically requires retained intra-cluster linkage that cluster fusion can discard. [doi-10-1007-978-3-030-49461-2-23]
- Cross-corpus event-coreference performance degrades materially, showing that benchmark structure and domain-specific shortcuts can dominate apparent accuracy. [2011.12249] [2104.05022] [manual-f56d02b8f9]
- Partial or quasi-event identity may be non-transitive, creating a mismatch between pairwise relatedness and conventional globally transitive clusters. [manual-c43ffe3135]
- Candidate restriction, document/topic preclustering, and retrieval can improve efficiency or benchmark performance, but the reviewed literature does not establish such structures as enterprise work-matter identity. [manual-e988e24127] [2011.12249] [doi-10-18653-v1-2022-emnlp-main-58]
- Novelty and first-story detection are distinct from tracking and linking; forcing novelty detection to behave like repeated similarity tracking can accumulate substantial error. [doi-10-1145-354756-354843] [manual-5c20fb0229]

### Literature-supported findings

1. **Identity evidence is corpus-dependent.** In cross-document event coreference, event-action information dominates more strongly on ECB+, while time, participants, and other contextual signals matter more on FCC-T and GVC. Joint entity-event information also improves ECB+ event and entity coreference. This supports multi-signal reasoning in adjacent domains, but does not establish the corresponding feature set for workplace Topics. [2011.12249] [manual-e988e24127]

2. **Single-benchmark performance does not establish general robustness.** Single-corpus event-coreference models degrade substantially on unseen corpora; WEC/ECB+ transfer loses roughly 8 to 12 CoNLL-F1 points. ECB+ itself was introduced because the earlier ECB resource understated event and lexical diversity. [2011.12249] [2104.05022] [manual-f56d02b8f9]

3. **Rejection and abstention are established general mechanisms.** Open-world recognition allows unknown observations to be rejected rather than assigned to a known class, while selective classification provides confidence-thresholded abstention with an explicit risk-coverage trade-off. These results support the mechanism, not msgloom's exact CONTINUE/NEW/UNCERTAIN semantics. [1412.5687] [1705.08500]

4. **Novelty detection can be much harder than ordinary tracking.** In the TDT setting, first-story detection can be reduced to repeated tracking decisions, and modest tracking error can accumulate into poor novelty-detection performance. The TDT framework also distinguishes tracking, linking, detection, and first-story detection as separate evaluation tasks. [doi-10-1145-354756-354843] [manual-5c20fb0229]

5. **Incremental resolution can approach batch quality while revising historical state.** ERLD updates only relevant previously resolved entities and can merge earlier clusters when new evidence arrives. FAMER's incremental methods similarly achieve quality close to batch processing while avoiding complete repeated recomputation. [1402.4417] [doi-10-1007-978-3-030-49461-2-23]

6. **The historical-state requirement must be stated narrowly.** For FAMER specifically, retained intra-cluster links permit bounded n-depth reclustering around newly inserted entities. Cluster fusion reduces state but discards those links, preventing that particular repair procedure. This is not evidence that every possible merge/split correction algorithm requires the same historical representation. [doi-10-1007-978-3-030-49461-2-23]

7. **Some event relations are non-transitive.** CDEC-WN reports that about 32 percent of its cross-document links were candidates for partial identity, including membership, subevent, and spatiotemporal-continuity relations. Because such relations can violate transitivity, pairwise relatedness and globally coherent identity clusters are not always equivalent. [manual-c43ffe3135]

8. **Identity can be approached through retrieval rather than exhaustive clustering.** CoreSearch formulates cross-document coreference as retrieval from a marked query event. Its qualitative analysis nevertheless found argument-inconsistency errors and cases where local contexts were insufficient for an identity decision. [doi-10-18653-v1-2022-emnlp-main-58]

9. **Preclustering is a transfer-risk issue, not an identity rule established by this corpus.** Topic preclustering materially improves ECB+ results in one study, while another shows that ECB+-specific exploitation of document-link distributions can overfit and transfer poorly. The evidence therefore does not determine whether conversation, source, or document partitions should define Topic identity in enterprise communication. [manual-e988e24127] [2011.12249]

10. **Probabilistic linkage supports evidence weighting rather than deterministic agreement.** The public-health linkage work models agreement using match and nonmatch probabilities and accounts for differing informativeness of field values. Because only its abstract was available, transfer to work-matter identity and the magnitude of its claimed advantages remain uncertain. [doi-10-1002-sim-4780140510]

# Contradictions

### Preclustering utility versus transfer robustness

On ECB+, document topic preclustering substantially improves event-coreference performance. [manual-e988e24127] In contrast, cross-corpus analysis finds that ECB+-specific use of document-link distributions can overfit and transfer poorly. [2011.12249] These results are not irreconcilable: structural partitions can be useful candidate restrictions on one benchmark while still being unsafe as general identity assumptions. The reviewed evidence therefore supports a transfer-risk warning, not a rule that enterprise conversation or document boundaries either must or must not determine Topic identity.

### Transitive clustering versus partial/non-transitive event relations

WEC and ECB+-style systems evaluate event coreference through clustering. [2104.05022] [manual-e988e24127] CDEC-WN instead deliberately represents links pairwise because partial identity can violate transitivity. [manual-c43ffe3135] This is a representational tension rather than a direct empirical contradiction because the resources annotate different relation semantics. For msgloom, the implication is only that the distinction between full identity and other relations requires investigation; the appropriate Topic model remains open.

# Open Gaps

### G03-1 — ACADEMIC — HIGH

Which evidence combinations actually establish or refute continuity of a concrete work matter across independent workplace messages, conversations, attachments, email, and Teams remains open. The corpus supports adjacent-domain evidence types, but it does **not** validate subject, customer/project names, conversation ancestry, referenced artifacts, commitments, or state compatibility as target-domain identity signals. [2011.12249] [manual-e988e24127] [doi-10-18653-v1-2022-emnlp-main-58]

Suggested query: `"work item identity" email cross-thread enterprise communication OR "cross-source" work matter identity OR business email event coreference`

**Status: open.** The reviewed papers do not answer the target-domain evidence question.

### G03-2 — ENGINEERING — HIGH

The application-specific decision policy remains open. Open-world recognition and selective classification support rejection and abstention mechanisms, but they do not establish msgloom's relative cost of false merges versus false splits, its attachment threshold, or the exact semantics and calibration of CONTINUE, NEW, and UNCERTAIN. [1412.5687] [1705.08500] [doi-10-1145-354756-354843]

In particular, this corpus does **not** justify assigning a higher explicit cost to false merges than false splits. That remains a msgloom design hypothesis to be determined from application requirements and empirical evaluation.

**Status: open.**

### G03-3 — ENGINEERING — HIGH

The msgloom identity-state and correction model remains open. Incremental ER shows that historical decisions can sometimes be revised, and FAMER provides one bounded reclustering mechanism, but the literature does not establish msgloom's proposed stable-ID scheme, title-independent identity, versioned assessments, supersession links, immutable evidence lineage, or general MERGE/SPLIT correction semantics. [1402.4417] [doi-10-1007-978-3-030-49461-2-23]

Those are project-level engineering choices requiring validation through design review, prototypes, invariants, and correction-focused tests.

**Status: open.**

### G03-PRODUCTION — ACADEMIC — HIGH

There is no direct production-domain evidence in this corpus for longitudinal work-matter identity across Outlook email and Microsoft Teams. The empirical domains are news, Wikipedia/Wikinews, image recognition, public-health linkage, knowledge graphs, process databases, and other entity-resolution settings. [2011.12249] [2104.05022] [manual-c43ffe3135] [doi-10-18653-v1-2022-emnlp-main-58]

Suggested query: `enterprise email Teams longitudinal work item identity dataset cross-thread task case tracking workplace communication`

**Status: open.** None of the reviewed papers establishes production representativeness or production accuracy for msgloom.

### G03-4 — ACADEMIC — HIGH

How partial, subevent, evolving, or otherwise non-transitive relations should map onto work-matter continuity remains unresolved. CDEC-WN demonstrates that event relations can be partially identical and non-transitive, but no reviewed paper defines the corresponding workplace semantics. [manual-c43ffe3135]

Suggested query: `"partial event identity" workflow OR task evolution OR case identity OR work item relationship`

### G03-5 — ENGINEERING — MEDIUM

The best Phase 2 evidence-seeking strategy remains unresolved. CoreSearch shows that query-driven retrieval can locate coreferent events in a large adjacent-domain collection and also shows cases in which local context is insufficient. [doi-10-18653-v1-2022-emnlp-main-58] Msgloom still needs benchmarks for bounded historical retrieval, candidate generation, latency, and whether additional context changes work-matter identity decisions.

### G03-6 — ACADEMIC — MEDIUM

Calibration under a non-stationary workplace stream remains unresolved. Selective-classification guarantees depend on calibration examples representative of deployment, while event-coreference transfer studies demonstrate substantial cross-corpus sensitivity. [1705.08500] [2011.12249] [2104.05022]

Suggested query: `selective classification abstention distribution shift streaming text calibration open set incremental clustering`

# Actionable Insights

The following items deliberately separate literature-supported mechanisms from **proposed msgloom engineering choices requiring validation**.

1. **Architectural hypothesis from adjacent-domain evidence:** prototype an incremental resolver that can attach evidence to an existing identity, create a candidate new identity, or reject an uncertain assignment instead of forcing every input into an existing cluster. Incremental ER and open-world/selective classification support the constituent mechanisms, but their mapping to msgloom's CONTINUE/NEW/UNCERTAIN contract remains unvalidated. [1402.4417] [doi-10-1007-978-3-030-49461-2-23] [1412.5687] [1705.08500]

2. **Proposed Phase 1 design choice requiring validation:** use a conservative rejection path when supplied evidence is insufficient. The exact threshold and the distinction between NEW and UNCERTAIN remain part of G03-2; the literature establishes abstention mechanisms, not the target semantics. [1412.5687] [1705.08500]

3. **Proposed msgloom metric, not a literature-established requirement:** instrument false merges and false splits separately so their real operational impact can be measured. Do not pre-assign a higher cost to either category; that cost model remains G03-2.

4. **Proposed evidence policy requiring validation:** assign substantial negative weight to incompatible argument, participant, temporal, state, or other evidence when available, and experimentally compare soft negative weighting with hard-veto variants. CoreSearch documents argument-inconsistency errors, but the reviewed corpus does not establish a universal argument or temporal veto. [doi-10-18653-v1-2022-emnlp-main-58]

5. Treat conversation, document, topic, or source structure as potentially useful candidate-generation or retrieval evidence, while explicitly testing transfer failure. Do not claim from these papers that such partitions either must or must not define enterprise Topic identity. [manual-e988e24127] [2011.12249]

6. If evaluating a FAMER-like n-depth repair algorithm, retain the intra-cluster links that algorithm requires. Do not generalize this storage requirement to unrelated correction algorithms. [doi-10-1007-978-3-030-49461-2-23]

7. **Proposed msgloom engineering contract requiring validation:** represent generated titles, subjects, conversation IDs, and source-specific thread IDs as attributes rather than assuming they are identity keys. This follows project requirements but is not a literature-backed finding from the reviewed corpus; enforce and test it as an implementation invariant rather than citing these papers as proof.

8. **Proposed correction architecture under G03-3:** preserve source evidence and record new identity assessments or corrections without destructive rewriting, then test whether versioned assessments, supersession links, and stable IDs provide adequate MERGE/SPLIT recovery. Incremental ER supports the general feasibility of revisiting historical decisions but does not establish this specific data model. [1402.4417] [doi-10-1007-978-3-030-49461-2-23]

9. For Phase 2, benchmark bounded historical retrieval before adopting global reclustering. CoreSearch shows retrieval-based cross-document identity search is viable in an adjacent domain, while its error analysis also shows that some decisions require evidence beyond the local pair. [doi-10-18653-v1-2022-emnlp-main-58]

10. Evaluate candidate methods on multiple datasets or deliberately different independent fixture families. Cross-corpus event-coreference results repeatedly demonstrate corpus-specific shortcuts and substantial transfer degradation. [2011.12249] [2104.05022] [manual-f56d02b8f9]

# Confidence Summary

Confidence is **HIGH** that the reviewed adjacent-domain literature supports rejection/abstention as a general mechanism, demonstrates substantial cross-corpus transfer risk, shows feasible incremental identity updating, and documents non-transitive partial event relations. [1412.5687] [1705.08500] [2011.12249] [2104.05022] [1402.4417] [doi-10-1007-978-3-030-49461-2-23] [manual-c43ffe3135]

Confidence is **MEDIUM** that these mechanisms will transfer usefully to msgloom because none of the 14 papers evaluates longitudinal workplace matters across email and Teams.

Confidence is **LOW to MEDIUM** for any concrete msgloom CONTINUE/NEW/UNCERTAIN calibration, workplace evidence weighting, false-merge versus false-split cost model, or stable-ID/correction data model. G03-1, G03-2, G03-3, and the production-domain limitation therefore remain explicitly open.

# Limitations

- No reviewed paper directly studies longitudinal concrete work-matter identity across enterprise email and Teams.
- Most event-coreference evidence comes from news, Wikipedia, or Wikinews, whose event semantics and document structure differ materially from workplace communication. [2011.12249] [2104.05022] [manual-c43ffe3135]
- Several event-coreference evaluations assume gold mentions or known topic partitions and therefore do not measure the complete msgloom problem from raw communication through identity assignment. [2104.05022] [manual-e988e24127] [manual-c43ffe3135]
- The open-world and selective-classification studies are image-domain experiments. They support rejection and abstention mechanisms in general but not workplace-specific decision semantics or thresholds. [1412.5687] [1705.08500]
- The incremental entity-resolution papers study people, companies, geographic/music/voter entities, or knowledge-graph entities rather than evolving work matters. [1402.4417] [doi-10-1007-978-3-030-49461-2-23]
- The FAMER state-retention result is algorithm-specific: it shows that n-depth reclustering requires retained intra-cluster links, not that every form of merge/split correction requires the same representation. [doi-10-1007-978-3-030-49461-2-23]
- The public-health probabilistic-linkage paper and TDT evaluation overview were available only at abstract level in the supplied analyses. [doi-10-1002-sim-4780140510] [manual-5c20fb0229]
- Cross-corpus degradation establishes a transfer-risk warning but does not quantify the domain shift from news or Wikipedia to workplace communication. [2011.12249] [2104.05022]
- CDEC-WN demonstrates partial and non-transitive event identity, but the mapping from those relations to msgloom Topic continuation, relationship, merge, or split semantics remains unknown. [manual-c43ffe3135]
- The corpus does not establish subjects, customer/project names, conversation ancestry, referenced artifacts, commitments, or state compatibility as reliable identity signals for longitudinal workplace Topics.
- Stable Topic IDs, independence from generated titles or thread IDs, immutable source history, versioned assessments, and supersession links are not established by the reviewed papers. They remain project-specific engineering design choices under G03-3.
- No reviewed evidence resolves G03-1, G03-2, G03-3, or the production-domain limitation.
