# Executive Summary

The reviewed literature supports treating proposition-, event-, and discourse-level reference as a problem distinct from ordinary entity coreference. Empirical systems successfully use mention ranking, cluster ranking, pairwise candidate comparison, discourse-specific features, and combinations of syntactic and contextual evidence, but no single formulation is established as universally superior. Dialogue discourse deixis is often local, yet other event-reference tasks contain longer-distance antecedents, so proximity is not universally adequate. Exact antecedent boundaries, discontinuous or composite antecedents, and pronominal abstract reference remain difficult. Formal question work supports partial-answer and subordinate-question relevance, principally through the QUD framework, but the corpus does not directly establish semantic scope for approvals or multi-question replies in workplace communication. Engineering recommendations therefore require validation rather than being treated as empirical findings.

# Themes

1. **Abstract reference is not ordinary entity coreference.** Non-nominal antecedents may denote events, propositions, facts, situations, descriptions, or speech acts, and their boundaries can be considerably harder to identify than ordinary nominal mentions. The same linguistic material can also support different abstract interpretations depending on the anaphor's predicational context. [doi-10-1162-coli-a-00327] [doi-10-18653-v1-2022-emnlp-main-778]

2. **Several successful systems explicitly compare antecedent candidates.** The corpus contains mention-ranking approaches for abstract anaphora and event coreference, cluster ranking for split antecedents, and pairwise twin-candidate comparison for event references. This is a descriptive commonality across successful systems; these papers do **not** directly demonstrate superiority over every possible unconstrained whole-message classification formulation. [1706.02256] [doi-10-18653-v1-p17-1009] [doi-10-18653-v1-2021-naacl-main-329] [manual-555fa5b6e8] [manual-5c0971730d]

3. **Locality is useful but domain- and reference-type dependent.** In the evaluated dialogue discourse-deixis data, more than 90 percent of antecedents occur within four utterances and the immediately preceding utterance is the most common location; recency-window restriction is also the only individually significant ablation among the ten tested extensions. By contrast, event-NP reference can span substantially longer distances, while a most-recent-verb heuristic performs poorly on event pronouns. Proximity alone is therefore not a universally adequate antecedent-selection heuristic across the reviewed reference types and domains. [doi-10-18653-v1-2022-emnlp-main-778] [manual-555fa5b6e8] [manual-5c0971730d]

4. **Some abstract antecedents are larger or more complex than one contiguous local span.** The survey identifies discontinuous and multi-sentence abstract antecedents as an under-modeled problem. The Spanish theoretical account further proposes that rhetorically coherent groups of propositions may form a single complex abstract referent. [doi-10-1162-coli-a-00327] [manual-8b8a394daa] Split-antecedent work shows that a computational resolver can associate one anaphor with several antecedent entity clusters, but this is only analogous transfer evidence; it does not directly establish multi-proposition abstract reference or multi-proposition reply scope in workplace communication. [doi-10-18653-v1-2021-naacl-main-329]

5. **Partial-answer structure has direct support from the QUD framework.** Roberts explicitly treats an assertion as relevant when it contributes at least a partial answer to the current Question Under Discussion and treats a subordinate question as relevant when resolving it advances a strategy for resolving the broader question. [doi-10-3765-sp-5-6] Karttunen contributes a compositional account in which questions are related to answer propositions, but that analysis does not itself demonstrate partial workplace reply scope. [doi-10-1007-bf00351935] *Resolving questions, II* distinguishes questions, propositions, and facts and makes resolution sensitive to contextual factors; again, that is a semantic distinction rather than direct evidence about partial business replies. [doi-10-1007-bf00983299]

6. **Exact target boundaries remain difficult.** The non-nominal-anaphora survey reports substantial annotation difficulty in delimiting exact antecedent spans. [doi-10-1162-coli-a-00327] The end-to-end dialogue system improves discourse-deixis resolution while resolving to whole utterances, even though the authors acknowledge that actual antecedents may be clauses or other sub-utterance spans. [doi-10-18653-v1-2022-emnlp-main-778] The survey also notes that whether exact span recovery is necessary depends on the application. [doi-10-1162-coli-a-00327]

7. **Syntax is useful evidence, but it is defeasible rather than universally decisive.** Structural kernels substantially improve the reviewed event-NP and event-pronoun resolvers. [manual-555fa5b6e8] [manual-5c0971730d] In shell-noun resolution, family-specific syntactic cues help nouns with relatively strict behavior but hurt several versatile nouns. [doi-10-3115-v1-d14-1056] In unrestricted ARRAU abstract anaphora, removing or disrupting explicit syntactic information improves the reported results. [1706.02256]

8. **Joint modeling can help, but the effect is task-specific.** Joint trigger detection, anaphoricity determination, and event-coreference learning improves all three tasks in the TAC KBP study. [doi-10-18653-v1-p17-1009] By contrast, joint optimization in the split-antecedent system does not improve the ordinary single-antecedent and non-referring components, and its pre-trained variant performs better overall. [doi-10-18653-v1-2021-naacl-main-329]

9. **The reviewed empirical evidence is not production evidence for msgloom's core workplace cases.** CODI-CRAC provides valuable multi-genre dialogue evidence, but the organizers explicitly caution against broad conclusions from the first shared-task iteration, and its new datasets have annotation and domain-transfer limitations. [doi-10-18653-v1-2021-codi-sharedtask-1] The later dialogue resolver also notes limited training data, coarse antecedent granularity, and uncertain generalization outside the evaluated genres. [doi-10-18653-v1-2022-emnlp-main-778] The corpus therefore does not establish production behavior for approval scope, multi-question email replies, or downstream work-state transitions.

# Contradictions

### Local versus longer-distance antecedents

The dialogue discourse-deixis results show a strong locality pattern and a measurable benefit from recency restriction. [doi-10-18653-v1-2022-emnlp-main-778] Event-NP reference, however, can cross substantially longer distances, while event-pronoun experiments show that simply choosing the most recent verb is inadequate. [manual-555fa5b6e8] [manual-5c0971730d] These results concern different phenomena and genres, so the appropriate synthesis is conditional locality rather than a universal distance rule.

### How strongly syntax should constrain resolution

Structured syntax materially improves event-NP and event-pronoun models. [manual-555fa5b6e8] [manual-5c0971730d] However, strict shell-noun-family syntax loses valid cases for versatile nouns, [doi-10-3115-v1-d14-1056] and explicit syntax can reduce performance in the broader ARRAU abstract-anaphora task. [1706.02256] The evidence favors treating syntax as informative but defeasible.

### Whether tighter joint learning is preferable

Joint event trigger, anaphoricity, and coreference learning improves the TAC KBP results. [doi-10-18653-v1-p17-1009] In the split-antecedent study, however, joint training does not benefit the ordinary components and is generally weaker overall than the pre-trained configuration. [doi-10-18653-v1-2021-naacl-main-329] There is therefore no cross-paper basis for assuming that maximal joint optimization is always best.

### What a question is semantically

Karttunen models a question in terms of a set of propositions corresponding to its true answers. [doi-10-1007-bf00351935] *Resolving questions, II* explicitly distinguishes questions from propositions and facts and does not simply identify a question with its answers. [doi-10-1007-bf00983299] Both provide useful structure for answer resolution, but their ontological commitments differ; the latter comparison is additionally limited because only its abstract was available in the supplied analysis.

# Open Gaps

### G1 — Direct workplace response-scope evidence
**Classification: ACADEMIC — Priority: HIGH**

Direct empirical evidence is still missing for proposition-level agreement, rejection, approval, clarification, and answer scope in authentic workplace email or enterprise chat, particularly cases in which a short reply applies to only part of a preceding message. The dialogue literature demonstrates related reference phenomena but does not close this gap. [doi-10-18653-v1-2021-codi-sharedtask-1] [doi-10-18653-v1-2022-emnlp-main-778]

Suggested query: `"agreement scope" email dialogue proposition OR "partial agreement" workplace communication OR "reply scope" email approval`

**Gap status: open.**

### G2 — Exact target representation and evaluation
**Classification: ENGINEERING — Priority: HIGH**

The literature documents boundary ambiguity and coarse utterance-level resolution, but it does not supply a validated msgloom evaluation contract covering exact, partial, ambiguous, unsupported, discontinuous, and potentially multiple proposition targets. [doi-10-1162-coli-a-00327] [doi-10-18653-v1-2022-emnlp-main-778] This is currently better addressed through an independent annotation specification and benchmark than by assuming that an existing metric answers the product question.

**Gap status: open.**

### G3 — Multi-question workplace replies
**Classification: ACADEMIC — Priority: HIGH**

The QUD framework directly supports partial answers and subordinate-question relevance, [doi-10-3765-sp-5-6] but the corpus does not empirically establish how replies align to one or more questions when an email or Teams message contains several questions, requests, or alternatives, nor how remaining unanswered items should be identified.

Suggested query: `"multiple questions" dialogue answer alignment OR "partial answer detection" dialogue OR email "question answer alignment"`

**Gap status: open.**

### G4 — Composite or multi-proposition reply targets
**Classification: ACADEMIC — Priority: MEDIUM**

Composite abstract discourse referents are theoretically supported, [manual-8b8a394daa] and the survey notes discontinuous and multi-sentence antecedents. [doi-10-1162-coli-a-00327] Split-antecedent entity resolution supplies useful analogous evidence that one anaphor can computationally link to several antecedent clusters. [doi-10-18653-v1-2021-naacl-main-329] None of these directly demonstrates that a workplace reply should be interpreted against several propositions or one composite proposition.

Suggested query: `"abstract anaphora" multiple antecedents dialogue OR "propositional anaphora" composite antecedent OR "agreement target" multiple propositions`

**Gap status: open.**

### G5 — Abstention, ambiguity, and asymmetric error cost
**Classification: ENGINEERING — Priority: HIGH**

No reviewed paper determines msgloom's correct abstention threshold, missing-antecedent behavior, or treatment of ambiguity. Preserving uncertainty or returning an unresolved result is therefore an engineering design recommendation, not an experimentally established operational rule from these studies. [doi-10-1162-coli-a-00327] [doi-10-18653-v1-2022-emnlp-main-778]

Likewise, the corpus does **not** establish that incorrectly broadening an approval or commitment is more damaging than leaving a supported relation unresolved. That asymmetric cost is a product-risk assumption and should be specified from product requirements and measured explicitly rather than attributed to the literature.

**Gap status: open.**

### G6 — Propagation into work-state transitions
**Classification: OUT_OF_SCOPE — Priority: HIGH**

The corpus does not establish how reference-scope mistakes propagate into downstream states such as approved, rejected, revoked, completed, or still open. Topic 04 can provide the scoped response relation, but validating subsequent state transitions belongs principally to Topic 06.

**Gap status: open.**

# Actionable Insights

- **Candidate-oriented resolution is a reasonable architecture to evaluate, not a literature-mandated design.** Several successful studies rank mentions, clusters, or candidate pairs, so msgloom should benchmark explicit antecedent-candidate representations rather than assuming one specific classifier formulation in advance. [1706.02256] [doi-10-18653-v1-2021-naacl-main-329] [manual-555fa5b6e8] [manual-5c0971730d]

- **Exploit upstream structure rather than rediscovering it.** Topic 01's source/quote spans and Topic 02's Topic spans can constrain candidate generation; Topic 04 can then concentrate on semantic target and scope. This is an engineering recommendation motivated by evidence that mention/candidate generation and upstream representations are major sources of end-to-end error. [doi-10-18653-v1-2021-naacl-main-329] [doi-10-18653-v1-p17-1009]

- **Use recency as evidence and possibly as an optimization, not as an unconditional rule.** A local window is highly effective for the evaluated dialogue deixis task, [doi-10-18653-v1-2022-emnlp-main-778] but other event-reference tasks show longer-distance links or weak nearest-candidate baselines. [manual-555fa5b6e8] [manual-5c0971730d] Any production window should therefore be benchmarked against relevant fixtures.

- **Evaluate proposition/sub-message granularity explicitly.** Whole-utterance resolution can perform well on existing dialogue benchmarks while still being coarser than the proposition boundaries required by msgloom. [doi-10-18653-v1-2022-emnlp-main-778] Boundary ambiguity should therefore be measured rather than hidden inside a message-level correctness label. [doi-10-1162-coli-a-00327]

- **Provide representation capacity for multiple, discontinuous, or composite targets as a hypothesis to test.** The literature justifies testing that capability, but it does not establish multi-proposition reply scope as the correct model for work communication. Direct support comes from abstract-reference survey/theory; split-antecedent entity resolution is only transfer evidence. [doi-10-1162-coli-a-00327] [manual-8b8a394daa] [doi-10-18653-v1-2021-naacl-main-329]

- **Separate response type from response target/scope.** A label such as answer, agreement, rejection, clarification, or condition should not automatically determine which prior proposition it affects. Roberts' QUD analysis directly supports the possibility of partial answers, but this proposed schema still requires msgloom-specific validation. [doi-10-3765-sp-5-6]

- **Preserve ambiguity or an unresolved result as an engineering policy when evidence is insufficient, but label this correctly as a design recommendation.** The studies establish that antecedent boundaries and selection can be difficult; they do not experimentally prove a particular abstention representation for msgloom. [doi-10-1162-coli-a-00327] [doi-10-18653-v1-2022-emnlp-main-778] Missing-context cases should be handed to Topic 07.

- **Do not encode an untested error-cost asymmetry as fact.** The reviewed studies do not show that an over-broad approval/commitment link is more harmful than abstaining. Msgloom should define this cost ordering from product requirements and then measure false broadening and false non-resolution separately.

- **Build independent adversarial fixtures around product-critical failure modes.** Useful categories include wrong antecedent, wrong boundary, wrong semantic relation, partial-scope broadening, missed partial answer, unsupported resolution, missing antecedent, and unanswered questions. Existing work shows that candidate and mention errors materially affect end-to-end performance but does not supply this workplace-specific evaluation. [doi-10-18653-v1-2021-naacl-main-329] [doi-10-18653-v1-2022-emnlp-main-778]

# Confidence Summary

Confidence is **HIGH** that proposition/event/discourse reference is materially different from ordinary nominal coreference; that antecedent selection and boundary identification are central difficulties; that several successful systems explicitly rank or compare antecedent candidates; that locality and syntactic cues are task-dependent; and that the QUD account directly licenses partial answers and strategically subordinate questions. [doi-10-1162-coli-a-00327] [doi-10-3765-sp-5-6] [doi-10-18653-v1-2022-emnlp-main-778]

Confidence is **MEDIUM** for transferring composite-antecedent representations to msgloom because the direct evidence is theoretical or comes from adjacent reference tasks. [manual-8b8a394daa] [doi-10-18653-v1-2021-naacl-main-329]

Confidence is **LOW** for claims about production workplace behavior. The reviewed evidence does not establish production accuracy, calibration, or failure costs for approval scope, multi-question email replies, or downstream work-state transitions.

# Limitations

- None of the reviewed studies directly evaluates the complete msgloom target of proposition-level reply scope for workplace approvals, agreements, rejections, conditions, and unanswered work items in high-volume Outlook or Teams communication. [doi-10-18653-v1-2021-codi-sharedtask-1] [doi-10-18653-v1-2022-emnlp-main-778]

- Several empirical datasets are small, sparse in the target phenomenon, out of domain, or heterogeneous in their annotation and evaluation methods, which prevents straightforward numerical comparison across papers. [1706.02256] [doi-10-1162-coli-a-00327] [doi-10-18653-v1-2021-naacl-main-329] [doi-10-18653-v1-2021-codi-sharedtask-1]

- The formal question-semantics and QUD papers provide conceptual foundations rather than quantitative validation of workplace reply interpretation. [doi-10-1007-bf00351935] [doi-10-1007-bf00983299] [doi-10-3765-sp-5-6]

- The composite-reference account in the Spanish abstract-anaphora paper is qualitative and theoretical, and its proposed processing sequence is explicitly presented as a hypothesis requiring empirical testing. [manual-8b8a394daa]

- Split-antecedent results concern entity reference; using them to motivate multi-target proposition representations is transfer by analogy, not direct evidence for response scope. [doi-10-18653-v1-2021-naacl-main-329]

- The strongest reviewed dialogue discourse-deixis system resolves antecedents at whole-utterance granularity even though true antecedents can be smaller clauses or spans, so its reported performance does not directly measure the proposition-level precision required by msgloom. [doi-10-18653-v1-2022-emnlp-main-778]

- The supplied analysis of *Resolving questions, II* is based only on the abstract, restricting how strongly its formal theory can be compared with the full-text question-semantics papers. [doi-10-1007-bf00983299]

- The corpus cannot determine whether false broadening should be assigned a higher business cost than abstention. That asymmetry must come from product requirements or dedicated evaluation rather than being inferred from the reference-resolution literature.
