# Executive Summary

Across 25 analyses, the strongest evidence comes from cross-document event coreference, TDT/new-event detection, incremental entity resolution, and partial-event-identity work. These literatures converge on a central point: identity is not semantic similarity. Reliable continuity depends on combinations of event arguments, participants, time, location, discourse/global context, structural links, and evolving historical state, while lexical or topical overlap alone causes false merges and false splits. Incremental methods show that historical clusters can be locally revised as new evidence arrives, and open-world/selective-classification work supports explicit rejection rather than forced assignment. However, partial identity can be non-transitive, so a single flat cluster is sometimes the wrong representation. Most importantly, the corpus still contains no direct longitudinal Outlook/Teams evidence. Therefore the literature supports design principles and benchmark ideas, but not production accuracy or exact msgloom decision thresholds.

# Themes

## Identity is not similarity

The strongest recurring result is that cross-document identity cannot safely be inferred from lexical similarity, shared names, or generic topical resemblance. Cross-document event-coreference systems improve when event arguments and entity participants are modeled jointly [1906.01753]. Metaphoric paraphrasing substantially degrades systems that depend on surface event triggers even when human judgments preserve the underlying identity [2407.11988]. ACCI similarly demonstrates both directions of the failure: semantically different events may share a trigger, while the same event may use different triggers [doi-10-1038-s41598-025-32765-6]. TDT work likewise finds that shared named entities alone cannot distinguish separate events involving the same people, organizations, or places [doi-10-3115-1220575-1220591].

For msgloom, this strongly supports the existing distinction that same subject, customer, project, participant set, or embedding neighborhood is evidence but not proof of Topic identity.

## Identity evidence is multi-dimensional and corpus-dependent

Arguments, participants, time, location, lexical action information, and wider context all contribute to identity, but their relative value is not universal. ECB+ can be modeled heavily from action information, whereas FCC-T and GVC require more balanced use of time, participants, and contextual features [2011.12249]. Probabilistic record linkage similarly treats observed agreements as weighted evidence rather than deterministic identity, including the principle that agreement on common values is less discriminative than agreement on rare values [doi-10-1002-sim-4780140510].

This argues against hard-coding one universal evidence weighting for msgloom. Evidence combinations should be calibrated on the target task.

## Local pairs can be insufficient

Global context materially improves identity decisions. Cross-document discourse features raise event-coreference performance beyond local event-sentence representations, and discourse paths can recover shared participants that are not evident from direct local comparison [doi-10-18653-v1-2023-emnlp-main-294]. CoreSearch error analysis likewise found cases where the local query and candidate passages did not contain enough evidence to decide identity at all [doi-10-18653-v1-2022-emnlp-main-58].

This is direct support for separating Phase 1 supplied-evidence decisions from Phase 2 bounded evidence seeking.

## Topic or conversation structure is useful but must not become identity

Topic pre-clustering produces large performance gains on ECB+, including a 4.6-point gain when added to an earlier system [1906.01753] [manual-e988e24127]. However, multi-corpus evaluation shows that ECB+-specific structural assumptions and document-link distributions can overfit and transfer poorly [2011.12249].

The appropriate synthesis is therefore not “ignore thread/topic structure,” but “use it for candidate generation and supporting evidence without equating it with identity.”

## Novelty detection is harder than continuation recognition

The TDT literature consistently separates tracking an already known topic from detecting a genuinely new one. Online event detection was much weaker than retrospective detection in an early experiment [doi-10-1145-290941-290953], while first-story detection was shown to amplify ordinary tracking errors to the point that conventional similarity-based systems performed poorly [doi-10-1145-354756-354843]. Turkish TDT experiments similarly found tracking substantially easier than first-story detection [doi-10-1002-asi-21264].

This is highly relevant to msgloom's distinction between NEW and “no confident existing match.” The literature does not support treating those as equivalent.

## Abstention is a first-class decision

Open-world recognition explicitly permits an observation to be rejected as unknown rather than forced into an existing class, followed by later incorporation when evidence becomes available [1412.5687]. Selective classification formalizes the trade-off between accepted-decision risk and coverage and provides procedures for thresholding to a desired risk level under its assumptions [1705.08500].

These are transfer mechanisms rather than workplace evidence, but they provide strong conceptual support for msgloom's UNCERTAIN state.

## Continuity representations should evolve

Adaptive topic tracking, which updates its representation using newly accepted stories, outperforms corresponding static tracking in the Turkish TDT experiments [doi-10-1002-asi-21264]. However, a TDT topic includes a seminal event plus directly related subsequent developments, making its continuity semantics broader than strict same-event coreference [doi-10-1002-asi-21264].

Msgloom can borrow the principle of an evolving representation without importing the TDT definition of identity unchanged.

## Incremental identity decisions can be repaired

Incremental entity resolution demonstrates that new evidence can merge previously separate historical clusters and can achieve nearly batch-level quality while reconsidering only affected historical state [1402.4417]. Incremental multi-source entity resolution further shows that naive assignment becomes sensitive to source arrival order, whereas bounded reclustering substantially reduces this dependence and repairs earlier decisions [doi-10-1007-978-3-030-49461-2-23].

This strongly supports correction-capable online Topic identity rather than immutable first assignments. It does not, however, define msgloom's stable-ID or history model.

## Partial identity is not an edge case

Event relations need not be binary full-identity versus unrelated. Subevent work explicitly distinguishes full coreference, parent-child subevents, sister relations, and non-coreference [manual-35bac66e3c]. CDEC-WN goes further: about 32 percent of its annotated cross-document links were candidates for partial identity, including membership, subevent, and spatiotemporal-continuity relations, and some of these relations violate transitivity [manual-c43ffe3135].

Consequently, a flat equivalence-class clustering representation is insufficient if msgloom needs to preserve related-but-not-identical work developments.

## Structured business-process identity is relevant but narrower

Process-mining work demonstrates that missing case identity can be reconstructed from a process model and temporal behavior [doi-10-1007-978-3-030-33223-5-12]. This is valuable direct evidence that latent business case identity can be inferred from structural and temporal constraints.

However, the method forces every event into exactly one case and even uses fallback assignment when normal replay fails [doi-10-1007-978-3-030-33223-5-12]. That formulation is materially narrower than msgloom's need for uncertainty, multi-matter messages, evolving identity, and later correction.

## Target-domain transfer remains unvalidated

Single-corpus event-coreference systems degrade substantially on unseen corpora [2011.12249]. WEC-to-ECB+ and ECB+-to-WEC transfer loses roughly 8–12 CoNLL-F1 points [2104.05022]. These failures occur even within related public-document domains.

No reviewed paper establishes longitudinal work-matter identity across Outlook email and Microsoft Teams. Therefore none of the reported benchmark accuracies can be interpreted as msgloom production accuracy [1906.01753] [2011.12249] [2104.05022] [doi-10-18653-v1-2023-emnlp-main-294].

# Contradictions

## Topic pre-clustering: strong signal or dangerous shortcut?

On ECB+, topic pre-clustering is an unusually strong signal and materially improves event-coreference systems [1906.01753] [manual-e988e24127]. In contrast, the multi-corpus study concludes that ECB+-specific pre-clustering and structural assumptions can overfit and generalize poorly [2011.12249].

These results are best reconciled by treating source/topic/thread structure as candidate-generation evidence rather than Topic identity itself.

## Broad topic continuity versus strict event identity

TDT defines a topic broadly enough to contain a seminal event and directly related subsequent events and activities [doi-10-1002-asi-21264]. Cross-document event-identity work instead distinguishes full identity from subevents and other partial relations [manual-35bac66e3c] [manual-c43ffe3135].

These are genuinely different semantics. A later development may belong to the same TDT topic without being the same event. Msgloom must therefore explicitly define which kinds of evolving development constitute continuation of one work matter.

## Forced assignment versus abstention

The process-correlation approach assigns every event to exactly one case, even if a fallback assignment is required [doi-10-1007-978-3-030-33223-5-12]. Open-world recognition and selective classification instead make rejection a legitimate result when evidence is insufficient [1412.5687] [1705.08500].

For msgloom's requirement that uncertain relationships remain separate and visible, the rejection-oriented formulation is substantially more compatible than compulsory assignment.

## Flat clustering versus non-transitive relatedness

Mainstream cross-document event coreference treats coreference clusters as equivalence classes [1906.01753] [2104.05022]. CDEC-WN shows that important partial-event relations can be non-transitive and therefore deliberately avoids forcing all annotated links into clusters [manual-c43ffe3135].

Msgloom may consequently require two layers: stable Topic identity and weaker typed relationships among related Topics or developments.

# Open Gaps

## gap-1 — ACADEMIC — HIGH — OPEN

Which evidence combinations actually establish or refute continuity of a concrete work matter across independent workplace messages, conversations, attachments, email, and Teams remains open. The corpus now gives stronger adjacent evidence for argument compatibility, participants, time, discourse/global context, structural links, and probabilistic evidence combination [1906.01753] [2011.12249] [doi-10-1038-s41598-025-32765-6] [doi-10-18653-v1-2023-emnlp-main-294]. It still does not validate subject, customer/project name, conversation ancestry, referenced artifacts, commitments, or state compatibility as target-domain evidence.

Suggested query: `("work item identity" OR "work matter identity" OR "business event coreference") AND (email OR "workplace communication" OR enterprise) AND (cross-thread OR cross-document OR cross-source)`

## gap-2 — ENGINEERING — HIGH — OPEN

The application-specific decision policy remains unresolved. Open-world and selective-classification literature supports rejection and explicit risk-coverage trade-offs [1412.5687] [1705.08500], but it does not determine msgloom's relative costs for false merges and false splits or the production thresholds and semantics for CONTINUE, NEW, and UNCERTAIN.

This remains an engineering problem requiring product-loss definitions, independent gold data, threshold experiments, and downstream error analysis.

## gap-3 — ENGINEERING — HIGH — OPEN

The correction and identity-state model remains unresolved. Incremental ER demonstrates that earlier clusters can be repaired and revised [1402.4417] [doi-10-1007-978-3-030-49461-2-23], but the literature does not specify msgloom's stable Topic IDs, versioned identity assessments, supersession links, immutable evidence history, or general MERGE/SPLIT protocol.

Those require project-level architecture, invariants, prototypes, and correction-oriented tests.

## gap-4 — ACADEMIC — HIGH — OPEN

There is still no direct production-domain evidence for longitudinal work-matter identity across Outlook email and Microsoft Teams. The reviewed evidence remains drawn from news, Wikipedia, image recognition, record linkage, knowledge graphs, or structured process logs [2011.12249] [2104.05022] [doi-10-1007-978-3-030-33223-5-12].

Suggested query: `(enterprise OR workplace) AND (email OR "Microsoft Teams" OR chat) AND (cross-thread OR longitudinal OR cross-conversation) AND (topic identity OR task tracking OR case tracking OR event coreference)`

## gap-5 — ACADEMIC — HIGH — OPEN

This round substantially strengthens the premise behind the gap but does not close it. Partial and non-transitive event identity is directly demonstrated, including parent-child subevents, sister relations, membership, and spatiotemporal continuity [manual-35bac66e3c] [manual-c43ffe3135].

What remains unanswered is how those relations map to workplace Topic semantics: CONTINUE, RELATED-BUT-SEPARATE, MERGE, SPLIT, or some other relationship.

Suggested query: `("partial event identity" OR "subevent relation" OR "event evolution" OR "non-transitive coreference") AND (workflow OR task OR case OR workplace)`

## gap-6 — ENGINEERING — MEDIUM — OPEN

Coreference search demonstrates that historical evidence can be retrieved from a very large collection [doi-10-18653-v1-2022-emnlp-main-58], and discourse work shows that global context can change identity decisions [doi-10-18653-v1-2023-emnlp-main-294].

Msgloom still needs engineering benchmarks for bounded historical retrieval, candidate generation, latency, retrieval stopping, and—most importantly—whether the extra context changes identity decisions correctly.

## gap-7 — ACADEMIC — MEDIUM — OPEN

Selective-risk guarantees assume calibration examples representative of deployment [1705.08500], while cross-corpus event-coreference studies show substantial distribution sensitivity [2011.12249] [2104.05022]. The corpus contains no solution for confidence calibration under non-stationary workplace communication.

Suggested query: `("selective classification" OR abstention OR "confidence calibration") AND ("distribution shift" OR nonstationary OR streaming OR "concept drift") AND (text OR coreference OR clustering)`

# Actionable Insights

1. Model cross-thread identity as an evidence-combination decision, not a similarity threshold. Keep separate signals for participants/entities, action/event semantics, temporal compatibility, objects or locations where relevant, references, discourse/global context, and source/thread structure [1906.01753] [2011.12249] [doi-10-1038-s41598-025-32765-6].

2. Do not permit subject lines, customer/project names, participant overlap, conversation ancestry, embeddings, or trigger words to establish continuity individually. Superficially similar but distinct events and differently worded identical events are both well documented [2407.11988] [doi-10-3115-1220575-1220591] [manual-f56d02b8f9].

3. Preserve CONTINUE, NEW, and UNCERTAIN as genuinely different outputs. Absence of sufficient evidence for continuation is not proof of novelty [1412.5687] [1705.08500] [doi-10-1145-354756-354843].

4. For Phase 1, prefer high-precision continuation decisions and visible uncertainty when evidence is insufficient. The literature supports rejection mechanisms but does not provide a universal msgloom threshold [1705.08500].

5. For Phase 2, retrieve bounded historical evidence when local context is insufficient. Evaluate retrieval by whether it improves the final identity decision rather than only by retrieval recall or latency [doi-10-18653-v1-2022-emnlp-main-58] [doi-10-18653-v1-2023-emnlp-main-294].

6. Retain historical links and evidence needed for correction. Incremental ER shows that local reclustering can repair old decisions, while cluster fusion that discards internal links can reduce later repairability [1402.4417] [doi-10-1007-978-3-030-49461-2-23].

7. Represent weaker relations separately from strict identity. Subevent, membership, sister-event, or spatiotemporal-continuity relations should not automatically cause a Topic merge because some are non-transitive [manual-35bac66e3c] [manual-c43ffe3135].

8. Construct adversarial evaluation fixtures containing same-name/different-matter, different-wording/same-matter, long gaps, participant changes, project-name reuse, evolving subevents, cross-thread references, and different arrival orders [2407.11988] [doi-10-3115-1220575-1220591] [doi-10-1007-978-3-030-49461-2-23].

9. Evaluate false merges, false splits, NEW-versus-CONTINUE errors, abstention coverage, correction success, and arrival-order sensitivity in addition to aggregate clustering metrics. TDT and selective-classification work show that novelty and risk behavior are not adequately characterized by ordinary cluster F1 alone [manual-5c20fb0229] [1705.08500] [doi-10-1145-354756-354843].

# Confidence Summary

Confidence is HIGH that surface similarity, shared names, and conversation/topic proximity are insufficient by themselves to establish identity. Confidence is also HIGH that participant/argument/context evidence, explicit abstention, incremental repair, and separate representation of partial relationships are appropriate design principles [1906.01753] [1412.5687] [1402.4417] [manual-c43ffe3135].

Confidence is HIGH that benchmark-specific structure can make results misleadingly strong: cross-corpus degradation, ECB+ topic effects, and lexical-diversity experiments all show this clearly [2011.12249] [2104.05022] [2407.11988].

Confidence is MEDIUM that specific mechanisms from news event coreference, entity resolution, TDT, or process mining will transfer effectively to msgloom.

Confidence is LOW for production accuracy, feature weights, false-merge rates, decision thresholds, or calibration on Outlook/Teams because no direct longitudinal enterprise-communication benchmark appears in the corpus.

# Limitations

The evidence base is dominated by news and Wikipedia rather than enterprise communication [1906.01753] [2011.12249] [2104.05022]. Target-domain transfer therefore remains the largest limitation.

Several high-performing event-coreference studies assume gold event or entity mentions, excluding upstream extraction errors that msgloom will encounter end to end [1906.01753] [2104.05022] [doi-10-18653-v1-2023-emnlp-main-294].

Benchmark structure can materially inflate or distort apparent performance. ECB+-specific topic partitions, limited event diversity, and lexical overlap are all documented concerns [2011.12249] [2407.11988] [manual-f56d02b8f9].

Several papers were available only at abstract level, limiting independent verification of algorithms, ablations, error analyses, and author-stated limitations [doi-10-1002-sim-4780140510] [doi-10-1145-290941-290953] [doi-10-2139-ssrn-7284343] [manual-5c20fb0229] [manual-f56d02b8f9].

The corpus also contains two analyses of the same joint entity/event coreference paper under different identifiers, [1906.01753] and [manual-e988e24127]. Therefore the 25 per-paper analyses are not 25 fully independent studies.

Partial-identity evidence is now considerably stronger, but its best direct studies remain news-oriented and do not establish workplace semantics [manual-35bac66e3c] [manual-c43ffe3135].

Open-world and selective-classification papers provide useful decision-theoretic mechanisms, but their experimental settings do not validate msgloom confidence calibration [1412.5687] [1705.08500].

Finally, the literature cannot determine msgloom's production loss function, stable-ID representation, correction-history model, or exact merge/split policy. Those remain engineering decisions requiring independent evaluation rather than further inference from benchmark scores.
