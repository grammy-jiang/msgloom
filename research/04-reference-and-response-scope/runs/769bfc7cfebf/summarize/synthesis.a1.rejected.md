# Executive Summary

Across the 13 papers, the strongest common result is that reference resolution beyond entities requires explicit modeling of propositions, events, utterances, questions, and sometimes composite discourse objects. Candidate selection cannot safely rely on proximity alone: recency is highly useful in conversational discourse deixis, yet other event references can span substantially longer distances. Exact antecedent boundaries, split or multi-span antecedents, and semantic typing remain difficult. Question semantics and QUD theory further show that responses can be partial, subordinate, or relevant without resolving an entire preceding question. For msgloom, this supports proposition-level antecedent candidates, explicit response-to relations, partial-scope representations, and abstention when evidence is insufficient. However, the corpus provides little direct evidence on business email, approvals, multi-question replies, or partial agreement scope, leaving these as important academic and engineering gaps.

# Themes

- **Abstract reference is not entity coreference.** Relevant antecedents may denote propositions, events, facts, situations, utterances, speech acts, or other abstract discourse objects rather than ordinary nominal entities [doi-10-1162-coli-a-00327] [doi-10-18653-v1-2022-emnlp-main-778] [manual-8b8a394daa].

- **Candidate ranking is a recurring computational pattern.** Mention ranking, cluster ranking, and pairwise candidate comparison repeatedly outperform simplistic candidate selection and provide a natural architecture for explicit antecedent grounding [1706.02256] [doi-10-18653-v1-2021-naacl-main-329] [manual-555fa5b6e8] [manual-5c0971730d].

- **Recency is strong evidence but not a universal rule.** More than 90% of discourse-deictic antecedents in the evaluated dialogue data occurred within four utterances, and removing the recency restriction significantly degraded the reported system [doi-10-18653-v1-2022-emnlp-main-778]. By contrast, event-NP links can span much longer distances [manual-555fa5b6e8], and a most-recent-verb baseline performs poorly for event-pronoun resolution [manual-5c0971730d].

- **Exact scope may be structurally complex.** Antecedent boundaries are difficult to annotate, and abstract antecedents may be discontinuous or multi-sentential [doi-10-1162-coli-a-00327]. Split antecedents demonstrate that one anaphor may depend on several prior discourse entities [doi-10-18653-v1-2021-naacl-main-329], while theoretical work explicitly models complex propositional objects assembled from several rhetorically coherent propositions [manual-8b8a394daa].

- **Question answering is intrinsically scoped.** QUD theory treats an assertion as relevant when it contributes even a partial answer and allows subordinate questions to advance a larger unresolved issue [doi-10-3765-sp-5-6]. Formal question semantics likewise treats questions as structured semantic objects rather than ordinary propositions [doi-10-1007-bf00351935] [doi-10-1007-bf00983299]. This directly supports preserving unanswered siblings when a reply addresses only part of a multi-question message.

- **Syntax is useful but defeasible.** Shell-noun syntax helps for some nouns but hurts syntactically versatile ones [doi-10-3115-v1-d14-1056]. In abstract-anaphora experiments, explicit syntax helps one task but can hurt broader ARRAU-AA transfer [1706.02256]. Event-NP resolution similarly benefits from structural information while finding that richer syntactic representations can add noise [manual-555fa5b6e8].

- **Upstream detection errors matter.** Split-antecedent resolution loses valid cases before resolution because of candidate restrictions and recognition errors [doi-10-18653-v1-2021-naacl-main-329]. Event-coreference errors similarly arise from missing or mistyped triggers and inadequate contextual information [doi-10-18653-v1-p17-1009]. Dialogue benchmarks also show genre- and annotation-dependent difficulty [doi-10-18653-v1-2021-codi-sharedtask-1]. A missing link therefore cannot safely be interpreted as evidence that no antecedent exists.

- **The major product gap is response scope in real work communication.** The dialogue and anaphora literature provides useful transfer mechanisms, but the reviewed studies do not directly establish accuracy for business-email approvals, clause-specific rejection, multi-question replies, or terse responses such as “yes” and “approved” when several propositions are available [doi-10-18653-v1-2021-codi-sharedtask-1] [doi-10-18653-v1-2022-emnlp-main-778] [doi-10-1162-coli-a-00327] [doi-10-3765-sp-5-6].

# Contradictions

## Recency versus long-distance search

The strongest apparent tension concerns antecedent distance. Dialogue discourse deixis is highly local, and recency restriction is the only reported task-specific ablation whose removal significantly damages the dd-utt model [doi-10-18653-v1-2022-emnlp-main-778]. Event-NP resolution instead observes substantially longer-distance links and a very large candidate space [manual-555fa5b6e8], while event-pronoun work finds that simply choosing the most recent verb is inadequate [manual-5c0971730d]. These results argue against either extreme: msgloom should use recency as a strong prior but not as an irreversible cutoff.

## Strong versus permissive syntactic constraints

The shell-noun resolver finds that family-specific syntactic constraints help relatively regular nouns such as *reason* and *fact*, but harm more versatile nouns; its permissive resolver performs better overall [doi-10-3115-v1-d14-1056]. The abstract-anaphora ranking model likewise finds explicit syntax useful for shell nouns but potentially harmful on broader ARRAU-AA cases [1706.02256]. Event-NP experiments support structural syntax but find simpler structural representations superior to richer ones [manual-555fa5b6e8]. The combined conclusion is that syntax is useful evidence but should not be treated as a universal hard rule.

## Exact textual span versus abstract discourse object

The non-nominal-anaphora survey notes that exact text-span recovery is application-dependent [doi-10-1162-coli-a-00327]. The dialogue discourse-deixis resolver therefore links to whole utterances, partly because fine-grained clausal boundaries are difficult [doi-10-18653-v1-2022-emnlp-main-778]. Conversely, theoretical work shows that an abstract referent can be a complex object assembled from several propositions, for which no single contiguous text span is sufficient [manual-8b8a394daa]. For msgloom the product requirement is stricter than some source applications: traceability and approval scope require explicit grounding, but that grounding must permit multiple spans or structured propositions rather than insisting on one contiguous string.

## Joint versus staged optimization

Jointly learning event triggers, anaphoricity, and antecedent selection improves all three tasks in event coreference [doi-10-18653-v1-p17-1009]. In contrast, jointly training split-antecedent and ordinary anaphora components does not improve the ordinary tasks, and the pre-trained configuration is slightly better overall [doi-10-18653-v1-2021-naacl-main-329]. Cross-task dependencies therefore matter, but the evidence does not justify assuming that fully joint training is always superior to modular or staged architectures.

# Open Gaps

### G1 — Direct work-communication evidence
**Classification: ACADEMIC — Priority: HIGH**

There is insufficient direct evidence on proposition-level reference and response scope in business email or Teams-like work communication, especially approvals, rejections, commitments, and terse replies. Existing dialogue benchmarks establish transfer evidence but not production-domain validity [doi-10-18653-v1-2021-codi-sharedtask-1] [doi-10-18653-v1-2022-emnlp-main-778].

Suggested query: `"business email" reply scope approval agreement antecedent OR "email" "discourse deixis" OR workplace dialogue reference resolution`

### G2 — Multi-question and partial-agreement target identification
**Classification: ACADEMIC — Priority: HIGH**

The corpus does not adequately establish methods for aligning “yes”, “approved”, “agreed”, or a similar short response to one proposition among several questions, proposals, conditions, or clauses. QUD theory shows why partial answering is legitimate but does not supply a validated work-domain resolver [doi-10-3765-sp-5-6].

Suggested query: `"answer scope" dialogue multiple questions OR "question answer alignment" dialogue OR "agreement target" dialogue OR "partial agreement" conversation`

### G3 — Msgloom-specific scope representation and evaluation
**Classification: ENGINEERING — Priority: HIGH**

The literature does not provide a ready-made representation or benchmark matching msgloom's required outcomes: exact, partial, ambiguous, unsupported, multi-span, and composite scope. This can be addressed through an independent engineering benchmark informed by known boundary and multi-antecedent difficulties [doi-10-1162-coli-a-00327] [doi-10-18653-v1-2021-naacl-main-329].

### G4 — Candidate-window safety/recall trade-off
**Classification: ENGINEERING — Priority: HIGH**

The reviewed evidence cannot determine an appropriate history window for work communication. Strong locality in dialogue [doi-10-18653-v1-2022-emnlp-main-778] conflicts with longer-distance event reference [manual-555fa5b6e8]. This should be measured experimentally rather than fixed from either corpus.

### G5 — Abstention and unresolved-reference behavior
**Classification: ENGINEERING — Priority: HIGH**

A product-level policy is required for missing antecedents, competing candidates, and low-confidence scope decisions. Candidate loss and recognition errors in end-to-end systems show why failure to resolve must not be interpreted as evidence that the reference has no antecedent [doi-10-18653-v1-2021-naacl-main-329] [doi-10-18653-v1-p17-1009].

### G6 — Composite and discontinuous antecedents
**Classification: ACADEMIC — Priority: MEDIUM**

More evidence is needed on computational resolution of multi-proposition, discontinuous, and rhetorically composed abstract antecedents, especially when the referring expression is itself a response rather than a demonstrative [doi-10-1162-coli-a-00327] [manual-8b8a394daa].

Suggested query: `"abstract anaphora" discontinuous antecedent OR multi-sentence antecedent OR "propositional anaphora" rhetorical relation OR composite discourse referent`

### G7 — Attachment, table, and visual-object grounding
**Classification: OUT_OF_SCOPE — Priority: MEDIUM**

References such as “row 4”, “the highlighted section”, or “that attachment” require document, table, or visual grounding beyond the proposition-resolution problem considered in these papers. Topic 04 should preserve the unresolved reference and hand it to Topic 08 rather than broadening its own scope.

### G8 — General calibration and system-wide evidence reliability
**Classification: OUT_OF_SCOPE — Priority: MEDIUM**

General confidence calibration, attribution, and completeness evaluation are cross-cutting reliability questions. Topic 04 should expose uncertainty and its evidence, while Topic 10 owns general evaluation methodology.

There were no prior-round gaps supplied for this synthesis, so there are no `gap_status` entries to resolve.

# Actionable Insights

1. Represent every plausible response target as an explicit source span or structured proposition with lineage rather than assigning only a message-level label [doi-10-1162-coli-a-00327].

2. Permit a response to link to one, several, or composite antecedents. Split-antecedent and abstract-discourse analyses show that one-target-only representations are too restrictive [doi-10-18653-v1-2021-naacl-main-329] [manual-8b8a394daa].

3. Use recency as a ranking prior, not a hard search boundary. Strong locality is useful in dialogue [doi-10-18653-v1-2022-emnlp-main-778], but longer-distance event references are empirically attested [manual-555fa5b6e8].

4. Treat syntax, quotation structure, Topic membership, rhetorical relations, and lexical cues as evidence for candidate generation or ranking rather than irreversible filters [doi-10-3115-v1-d14-1056] [1706.02256].

5. Separate response/anaphor detection, antecedent availability, candidate ranking, semantic relation, and scope confidence. This makes upstream losses and downstream semantic errors distinguishable [doi-10-18653-v1-2021-naacl-main-329] [doi-10-18653-v1-p17-1009].

6. Explicitly support `exact`, `partial`, `ambiguous`, and `unresolved/unsupported` outcomes instead of forcing a single antecedent. Partial answerhood is a legitimate discourse state, not necessarily a failure [doi-10-3765-sp-5-6].

7. When a message contains several questions, conditions, or proposals, maintain proposition-level sibling candidates. Answering one must not implicitly resolve the others [doi-10-3765-sp-5-6] [doi-10-1007-bf00351935].

8. Build an independent adversarial benchmark containing multi-question messages, mixed approval/rejection, conditional approval, corrections, terse yes/no replies, multi-span targets, and deliberately missing antecedents. Existing benchmarks do not directly cover this product-critical distribution [doi-10-18653-v1-2021-codi-sharedtask-1] [doi-10-18653-v1-2022-emnlp-main-778].

9. Count over-broad scope as a first-class failure mode. The literature establishes that antecedent boundaries and candidate selection are difficult [doi-10-1162-coli-a-00327]; for msgloom, falsely extending an approval or commitment beyond supported evidence is decision-critical.

10. Route missing-context cases to Topic 07 and attachment/table/visual references to Topic 08 rather than forcing Topic 04 to manufacture an antecedent.

# Confidence Summary

Confidence is **HIGH** for the broad architectural conclusions that abstract reference requires non-entity antecedents, candidate ranking is useful, exact boundaries are difficult, recency is defeasible, and partial question resolution must be represented [doi-10-1162-coli-a-00327] [doi-10-18653-v1-2022-emnlp-main-778] [doi-10-3765-sp-5-6].

Confidence is **MEDIUM** for transferring specific modeling choices or distance windows into msgloom. The empirical studies use ARRAU, CODI-CRAC dialogue, OntoNotes news/broadcast data, or TAC event corpora rather than business email [doi-10-18653-v1-2021-codi-sharedtask-1] [manual-555fa5b6e8] [doi-10-18653-v1-p17-1009].

Confidence is **LOW** for any claim that existing methods are already sufficient for business approval scope, multi-question email replies, or production work-state transitions. None of the reviewed studies directly validates those cases.

# Limitations

- No paper in the corpus provides a direct benchmark for Outlook email, Microsoft Teams work communication, or business approval/commitment scope [doi-10-18653-v1-2021-codi-sharedtask-1] [doi-10-18653-v1-2022-emnlp-main-778].

- Several foundational sources are formal linguistic theories rather than computational evaluations. They strongly motivate semantic distinctions but do not establish implementation performance [doi-10-1007-bf00351935] [doi-10-3765-sp-5-6].

- [doi-10-1007-bf00983299] was available only through its abstract, limiting independent assessment of its formal details.

- The computational studies use heterogeneous datasets, annotation schemes, candidate definitions, and metrics, so their numerical results cannot be directly compared [doi-10-1162-coli-a-00327] [doi-10-18653-v1-2021-codi-sharedtask-1].

- Rare phenomena remain supported by relatively small samples; split antecedents and pronominal abstract anaphora are notable examples [doi-10-18653-v1-2021-naacl-main-329] [1706.02256].

- Exact clausal antecedent boundaries have documented annotation difficulty, which means a msgloom gold standard will require explicit operational rules rather than assuming a naturally unambiguous span [doi-10-1162-coli-a-00327] [doi-10-18653-v1-2022-emnlp-main-778].

- None of these papers directly evaluates the asymmetric business cost of an over-broad approval, rejection, or commitment interpretation.

- Synthetic, dialogue, newswire, broadcast, or transfer evidence in this corpus does not establish production representativeness for the user's work communication [doi-10-18653-v1-2021-codi-sharedtask-1] [manual-555fa5b6e8].
