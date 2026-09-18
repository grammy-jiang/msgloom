# Executive Summary

Across 47 papers, the strongest cross-paper result is that reply semantics cannot safely be represented as one message-to-message edge. Natural dialogue, email, and customer-service data contain partial answers, unanswered questions, non-adjacent replies, one-to-many answer links, multi-parent discourse attachments, and abstract references to composite proposition sets. Multiple interrogatives also need structural interpretation because they may be reformulations or narrowing moves rather than independent obligations. Annotation studies further show that exact antecedent boundaries and answer scope are genuinely ambiguous, while explicit no-link and alternative antecedent representations are empirically justified. However, direct workplace evidence remains concentrated on question-answer alignment, not proposition-level approval, rejection, agreement, or clarification scope. Therefore the literature supports msgloom's representational requirements, but not production thresholds or domain-accuracy claims. The remaining high-value work is workplace-oriented annotation/evaluation plus calibrated, asymmetric abstention and scope-error testing. [manual-849c5f1c6d] [doi-10-3115-1220355-1220483] [2403.16609] [doi-10-5087-dad-2020-104]

# Themes

## Cross-paper findings

1. **Multi-question messages frequently receive selective rather than exhaustive responses.** Coding work explicitly treats multi-question turns separately because a response may answer only one component, and the Pine-Info email data directly contain initiating messages whose first replies map answers to only a subset of their questions. The implication is that response coverage must be evaluated per question or proposition, not per whole message. [doi-10-1016-j-pragma-2010-04-002] [manual-849c5f1c6e8]

2. **Unanswered status is an empirically necessary discourse outcome.** Email annotations permit questions without corresponding answers; Enron dialogue-function annotation represents unmatched requests as dangling links; query-response corpora contain coherent response classes that leave the original issue unresolved; and clarification requests can receive no answer at all. [doi-10-3115-1220355-1220483] [doi-10-3115-1708376-1708429] [doi-10-15398-jlm-v4i2-173] [manual-e1981ecd9a]

3. **Adjacency and thread mechanics are not reliable proxies for semantic scope.** Email messages sent through Reply or Reply-All can answer issues raised several messages earlier, written chat can answer an older contribution instead of the immediately preceding one, and concurrent dialogue threads create crossing dependencies. [doi-10-3115-1220355-1220483] [2403.16609] [doi-10-18653-v1-d15-1109]

4. **Non-bijective alignment is common enough to require explicit representation.** Customer-service data contain answer utterances linked to multiple preceding questions; email work permits one answer sentence to correspond to several questions; STAC-style discourse graphs permit multiple parents; and one question can receive several answer attachments. [doi-10-1609-aaai-v33i01-3301134] [doi-10-3233-aic-2012-0516] [doi-10-18653-v1-2023-eacl-main-247] [doi-10-18653-v1-d15-1109]

5. **Several propositions can jointly form one semantic antecedent.** Abstract-anaphora work explicitly represents merged proposition sets; situated-discourse work models acknowledgments responding jointly to several prior replies; and Complex Discourse Units can make an entire sequence the argument of a later relation. [doi-10-1515-ling-2018-0008] [manual-8b8a394daa] [doi-10-5087-dad-2020-104] [doi-10-18653-v1-d15-1109]

6. **Exact proposition boundaries are difficult and sometimes intrinsically ambiguous.** Reviews and annotation studies repeatedly report uncertainty over non-nominal antecedent boundaries: annotators often agree on the general region more reliably than its exact beginning and end. ARRAU consequently distinguishes ambiguous alternatives and multi-antecedent cases, while split-antecedent evaluation work argues for partial credit when only part of a complex target is recovered. [doi-10-1162-coli-a-00327] [manual-7743c50805] [manual-e4d6ad7ca1] [doi-10-5210-dad-2023-201]

7. **Several interrogatives do not necessarily create several independent work obligations.** Multiple questions can be repetitions, reformulations, comprehension-management devices, particularizations of a broader question, or replacements after failure of uptake. In institutional interviews, recipients often answer the most recent or specific component while an earlier broad question receives no separate opportunity for response. [doi-10-1016-j-pragma-2007-07-011] [doi-10-1515-text-2003-021] [doi-10-1016-j-pragma-2018-03-015]

8. **Acceptance and rejection are proposition-sensitive, not simply whole-turn polar labels.** A reply can accept an entailed or weaker subproposition while rejecting stronger content, and scalar replacement can reject only the omitted portion rather than every proposition associated with the antecedent. This supports a semantic-scope representation, although the evidence is not specifically workplace email. [doi-10-1177-002383099603900306]

9. **Recency is useful but should not be a hard semantic constraint.** Dialogue discourse-deictic antecedents are overwhelmingly local in one benchmark, and clarification answers are also strongly local, yet asynchronous email and multi-thread dialogue demonstrate valid older antecedents. Recency is therefore best treated as a ranking prior whose strength depends on relation and genre. [doi-10-18653-v1-2022-emnlp-main-778] [manual-e1981ecd9a] [doi-10-3115-1220355-1220483]

10. **Detection, attachment, antecedent selection, and relation labeling have coupled but distinguishable failure modes.** Discourse-deixis benchmarks show large gains when gold anaphors are supplied, proving that identifying the referential expression is itself difficult; structured discourse parsing shows benefits from joint attachment/relation learning; and joint event-coreference work similarly benefits from modeling interacting subtasks. [manual-b0133009f6] [doi-10-18653-v1-s15-1035] [2306.15103] [doi-10-18653-v1-2023-eacl-main-247] [doi-10-18653-v1-p17-1009]

# Contradictions

**Local versus non-local response resolution.** Discourse-deixis and clarification studies show strong locality: more than 90% of evaluated discourse-deictic antecedents were within four utterances in one benchmark, and 94% of answered clarification requests in the analyzed BNC material were answered immediately. In contrast, email and multi-thread dialogue studies explicitly document responses to older contributions and crossing dependencies. [doi-10-18653-v1-2022-emnlp-main-778] [manual-e1981ecd9a] versus [doi-10-3115-1220355-1220483] [2403.16609] [doi-10-18653-v1-d15-1109]. This is best interpreted as genre and relation dependence, not evidence for a universal locality rule.

**Stack versus partially ordered unresolved issues.** The QUD framework represents accepted unresolved questions using a stack, while the query-response analysis argues that some response classes require several issues to remain simultaneously accessible in a partially ordered structure. [doi-10-3765-sp-5-6] versus [doi-10-15398-jlm-v4i2-173]. For msgloom, strict last-in-first-out closure is therefore unsafe when several work questions coexist.

**Tree-constrained parsing versus genuine multi-parent discourse structure.** A structured spanning-tree parser obtains strong benchmark improvements [2306.15103], while other STAC-based work explicitly permits or observes multiple parents and non-tree structures [doi-10-18653-v1-2023-eacl-main-247] [doi-10-18653-v1-d15-1109] [doi-10-5087-dad-2020-104]. The tension is between a useful modeling constraint and representational completeness rather than disagreement about the existence of multi-parent cases.

**One-to-one alignment versus observed one-to-many scope.** The local-assembly alignment work uses a one-to-one algorithm and still leaves substantial error even with gold segmentation [doi-10-1109-icaicta63815-2024-10762999]. Customer-service and email studies, by contrast, directly observe one answer corresponding to multiple questions [doi-10-1609-aaai-v33i01-3301134] [doi-10-3233-aic-2012-0516]. One-to-one matching should therefore not be imposed unless the domain contract guarantees it.

**Syntactic constraints help in some settings and hurt in others.** Syntactic information improves some shell-noun configurations, but unrestricted abstract-anaphora performance can improve when such information is removed, and elaborate structural expansions can inject noise for event antecedents. [1706.02256] [doi-10-3115-v1-d14-1056] [manual-555fa5b6e8]. Syntax is better treated as selective evidence than as a universal hard constraint.

# Open Gaps

**gap-1 — ACADEMIC, HIGH — OPEN.** Direct empirical evidence is still missing for proposition-level agreement, rejection, approval, clarification, and answer scope in authentic workplace email or enterprise chat, especially when a short response applies to only part of a preceding message. Workplace-email work directly studies QA linkage, while proposition-sensitive partial acceptance/rejection evidence comes from more general dialogue. [doi-10-1145-3209978-3210046] [doi-10-3115-1220355-1220483] [doi-10-1177-002383099603900306]  
Suggested query: `"partial reply" OR "response scope" email workplace dialogue proposition agreement rejection approval`

**gap-2 — ENGINEERING, HIGH — OPEN.** A validated combined msgloom annotation and evaluation scheme is still missing for exact proposition/span targets with exact, partial, ambiguous, unsupported, discontinuous, multiple-antecedent, composite, and explicit no-link outcomes. The corpus separately validates many of these requirements, including ambiguous alternatives, multi-antecedents, exact-span difficulty, and partial-credit scoring, but no paper validates the complete workplace contract. [manual-e4d6ad7ca1] [manual-be69c3aa17] [doi-10-5210-dad-2023-201] [2403.16609]

**gap-3 — ACADEMIC, HIGH — OPEN.** This gap has narrowed materially but is not closed. Direct email evidence now demonstrates multi-question initiating messages, incomplete first replies, unanswered questions, and answer sentences mapped to several preceding questions. However, the corpus still does not fully validate proposition-level treatment of mixed workplace questions, requests, and alternatives together or a complete unresolved-subquestion detector. [manual-849c5f1c6d] [doi-10-3233-aic-2012-0516] [doi-10-3115-1220355-1220483]  
Suggested query: `"multiple questions" "partial answer" dialogue email question answer alignment unanswered subquestions`

**gap-4 — ACADEMIC, MEDIUM — OPEN.** The corpus strongly supports both multiple independent antecedent links and composite discourse antecedents, but it does not directly evaluate how authentic workplace responses distinguish these two semantic structures. [doi-10-1609-aaai-v33i01-3301134] [doi-10-5087-dad-2020-104] [doi-10-1515-ling-2018-0008] [doi-10-18653-v1-d15-1109]  
Suggested query: `"multi-antecedent" dialogue response "composite antecedent" proposition discourse email`

**gap-5 — ENGINEERING, HIGH — OPEN.** The msgloom policy for uncertainty-driven abstention, ambiguous alternatives, missing antecedents, and asymmetric error costs remains unvalidated. Papers justify explicit no-link states, ambiguity preservation, future-context dependence, and partial-credit scoring, but do not establish thresholds appropriate to the cost of inventing a broader approval or commitment versus leaving a link unresolved. [2403.16609] [manual-e4d6ad7ca1] [doi-10-3115-1708376-1708429] [doi-10-5210-dad-2023-201]

# Actionable Insights

1. Represent semantic response structure below the message level. Segment candidate questions, propositions, requests, conditions, and decisions, then permit each response span to link to zero, one, or multiple antecedent spans. [manual-849c5f1c6d] [doi-10-1609-aaai-v33i01-3301134] [doi-10-18653-v1-d15-1109]

2. Make unresolved/no-link a first-class output. A later message must not automatically close every prior question or request, and the model must not be forced to select an antecedent when evidence is insufficient. [doi-10-3115-1220355-1220483] [doi-10-3115-1708376-1708429] [doi-10-15398-jlm-v4i2-173]

3. Before creating multiple open obligations from a multi-question turn, classify whether its components are collateral independent questions, reformulations, particularizations, repairs, or replacements. [doi-10-1016-j-pragma-2007-07-011] [doi-10-1515-text-2003-021] [doi-10-1016-j-pragma-2018-03-015]

4. Support both multiple independent antecedent edges and an explicit composite-antecedent object. The literature supplies empirical motivation for both, and collapsing them would erase a meaningful distinction. [doi-10-5087-dad-2020-104] [doi-10-1515-ling-2018-0008] [doi-10-18653-v1-2023-eacl-main-247]

5. Store ambiguity explicitly as alternative candidate antecedents or candidate sets instead of selecting one target when the evidence cannot distinguish them. [2403.16609] [manual-be69c3aa17] [manual-e4d6ad7ca1]

6. Use recency, turn order, speaker information, and thread structure as ranking features rather than hard semantic constraints. [2306.15103] [doi-10-18653-v1-2022-emnlp-main-778] [doi-10-3115-1220355-1220483]

7. Evaluate at proposition/link level with exact-match and overlap-sensitive measures, explicit zero-link scoring, multi-antecedent partial credit, and separate false-positive and false-negative denominators. [doi-10-5210-dad-2023-201] [manual-7743c50805] [manual-e4d6ad7ca1]

8. Measure over-broad positive links separately from unresolved links. The literature establishes that ambiguity and legitimate no-link cases exist, but msgloom must determine its own asymmetric business loss for wrongly broad approvals or commitments. [2403.16609] [doi-10-3115-1708376-1708429]

9. Keep missing-context errors distinct from reference-resolution errors. When the relevant antecedent is outside supplied evidence, preserve the unresolved reference and hand the evidence need to Topic 07 rather than guessing. Cases with no identifiable linguistic antecedent and cases requiring later context directly support this distinction. [doi-10-1093-jos-17-1-51] [2403.16609]

10. Preserve component-level error analysis for response/anaphor detection, antecedent selection, attachment, relation labeling, and scope classification even if some components are eventually trained jointly. [manual-b0133009f6] [doi-10-18653-v1-s15-1035] [2306.15103]

# Confidence Summary

Confidence is **HIGH** that msgloom needs proposition-level, zero-or-many, non-adjacent, ambiguity-preserving response links and explicit unresolved-question state. These structural requirements recur across workplace email, customer-service dialogue, discourse parsing, question-response analysis, and abstract-anaphora research. [doi-10-3115-1220355-1220483] [doi-10-1609-aaai-v33i01-3301134] [2403.16609] [doi-10-1162-coli-a-00327]

Confidence is **MEDIUM** for transferring particular parsing architectures, locality windows, or dialogue-structure assumptions across domains because performance and interaction patterns vary substantially by genre. [2306.15103] [doi-10-18653-v1-2022-emnlp-main-778] [doi-10-5210-dad-2022-203]

Confidence is **LOW-to-MEDIUM** for claims about authentic workplace proposition-level approval, rejection, agreement, and clarification scope. The strongest direct workplace evidence in this corpus concerns question-answer retrieval and response linkage rather than approval or commitment semantics. [doi-10-1145-3209978-3210046] [doi-10-3115-1708376-1708429]

# Limitations

- The corpus contains much stronger direct evidence for question-answer alignment than for workplace approval, rejection, agreement, condition, or clarification scope. The main proposition-sensitive acceptance/rejection evidence therefore remains transfer evidence from general dialogue. [doi-10-1177-002383099603900306] [doi-10-1145-3209978-3210046]

- Several strong structural findings come from task-oriented dialogue, games, interviews, parliamentary proceedings, forums, or customer-service conversations rather than authentic enterprise email or Teams-style communication. [2306.15103] [doi-10-5087-dad-2020-104] [doi-10-1109-icaicta63815-2024-10762999]

- The supplied per-paper material is reduced to research questions and top findings. This synthesis therefore cannot independently inspect annotation manuals, sampling procedures, detailed error analyses, or experimental sections beyond those summaries.

- Some evidence concerns discourse deixis or abstract anaphora rather than replies themselves. Those papers strongly support antecedent-span representation, ambiguity handling, and multi-proposition reference, but they do not establish production workplace reply-scope accuracy. [doi-10-1162-coli-a-00327] [manual-e4d6ad7ca1]

- Metrics are not directly comparable across the corpus because tasks range from QA alignment and discourse attachment to anaphora resolution and thread-level unresolved-discussion classification. [doi-10-1609-aaai-v33i01-3301134] [2306.15103] [doi-10-1007-s10489-013-0481-1]

- No included paper quantifies msgloom's downstream asymmetric harm from a falsely broad approval or commitment link versus an unresolved link. Consequently, production confidence thresholds and abstention policies remain engineering decisions rather than literature-derived constants. [2403.16609] [doi-10-5210-dad-2023-201]
