# Executive Summary

Across the 38 papers, the strongest cross-paper conclusion is that response scope cannot safely be represented as a single message-to-message or nearest-turn link. Dialogue and email contain unanswered questions, non-adjacent answers, one-to-many and many-to-many links, composite antecedents, ambiguous targets, and responses that accept one proposition while rejecting another. The literature therefore supports msgloom's requirement to preserve exact, partial, multiple, ambiguous, and no-link outcomes rather than forcing whole-message resolution. However, evidence is fragmented across discourse parsing, question-answer alignment, abstract anaphora, grounding, and formal pragmatics. Direct empirical evidence for proposition-level approval, rejection, agreement, and partial-answer scope in authentic workplace communication remains insufficient. Consequently, all five carried-over gaps remain open: three require additional academic evidence and two require engineering validation of annotation, evaluation, abstention, and asymmetric error policy.

# Themes

- **Response scope is frequently non-bijective.** A single server answer can align to multiple preceding customer questions, email answer sentences can correspond to several questions, and multi-party discourse graphs contain multi-parent and many-to-many structures. [doi-10-1609-aaai-v33i01-3301134] [doi-10-3233-aic-2012-0516] [doi-10-18653-v1-d15-1109] [2403.16609]

- **Unanswered material must remain explicit.** Email annotations contain questions without answers and dangling request links, while dialogue research shows locally coherent query responses that nevertheless leave the original question unresolved. [doi-10-3115-1220355-1220483] [doi-10-3115-1708376-1708429] [doi-10-15398-jlm-v4i2-173] [manual-e1981ecd9a]

- **Adjacency and thread structure are evidence, not semantic scope.** Email replies can answer issues raised several messages earlier; chat contains crossing dependencies and concurrent threads; later turns can answer older contributions rather than the immediately preceding one. [doi-10-3115-1220355-1220483] [doi-10-18653-v1-d15-1109] [2403.16609]

- **Acceptance and rejection require proposition-level scope.** A response can accept an entailed or weaker subproposition while rejecting the stronger claim, and scalar substitution can reject only the omitted or replaced component rather than the entire antecedent. [doi-10-1177-002383099603900306]

- **Multiple questions do not produce a simple one-question/one-answer obligation structure.** In interview data, respondents often answer the most recent or most specific member of a bundled sequence and leave broader material unanswered. At the same time, some repeated interrogatives are reformulations designed to repair comprehension rather than independent questions. [doi-10-1016-j-pragma-2018-03-015] [doi-10-1016-j-pragma-2007-07-011] A grounding study also reports a response after three questions whose target could not be assigned confidently to any one question. [2403.16609]

- **Non-nominal antecedents are central to the problem.** Spoken-dialogue evidence contains substantial sentential antecedence, and abstract-anaphora work identifies events, propositions, facts, speech acts, clauses, and discourse segments as legitimate antecedent/referent types. [doi-10-1093-jos-17-1-51] [doi-10-1162-coli-a-00327] [manual-ad98de9372] [manual-be69c3aa17]

- **Exact antecedent boundaries are intrinsically difficult.** The non-nominal-anaphora survey identifies span delimitation as a central annotation problem, while unconstrained annotation of abstract-object reference found substantially stronger convergence on antecedent endings than beginnings. [doi-10-1162-coli-a-00327] [manual-7743c50805] This directly supports retaining span uncertainty rather than manufacturing exact boundaries.

- **Composite antecedents are legitimate but should not be arbitrary unions.** Abstract-anaphora analyses allow several propositions to form a merged referent when rhetorical organization makes them coherent, while dialogue discourse formalisms allow several elementary units to form one complex antecedent. [doi-10-1515-ling-2018-0008] [manual-8b8a394daa] [doi-10-18653-v1-d15-1109]

- **Ambiguity and no-link are genuine outcomes.** Grounding annotations retain ambiguous scope where a response cannot be assigned to one of several active questions; DAD permits alternative antecedent interpretations; customer-service alignment contains many explicit None alignments; and email/dialogue annotation schemes contain dangling links. [2403.16609] [manual-be69c3aa17] [doi-10-1609-aaai-v33i01-3301134] [doi-10-3115-1708376-1708429]

- **Evaluation must expose multi-antecedent errors separately.** Split-antecedent work shows that rare multi-antecedent phenomena can be almost invisible in aggregate coreference scores and motivates partial-credit scoring. [doi-10-5210-dad-2023-201] A discourse parser capable of multi-parent attachment recovered only a minority of the test-set multi-parent structures despite much stronger aggregate attachment performance. [doi-10-18653-v1-2023-eacl-main-247]

- **Response interpretation can be provisional.** Grounding annotators sometimes needed later utterances to revise earlier interpretations, and query-response theory requires simultaneous accessibility of unresolved issues rather than immediate closure. [2403.16609] [doi-10-15398-jlm-v4i2-173] This supports incremental revision of msgloom scope judgments.

- **Attachment and relation classification are interdependent.** Multi-task discourse parsing improves relation labeling by jointly learning attachment and relation information, event-coreference work benefits from joint trigger/anaphoricity/antecedent learning, and discourse-deixis pipelines show major error propagation from imperfect candidate/anaphor classification. [doi-10-18653-v1-2023-eacl-main-247] [doi-10-18653-v1-p17-1009] [doi-10-18653-v1-s15-1035]

# Contradictions

## Local versus long-distance antecedents

Dialogue discourse deixis in one benchmark is strongly local: more than 90% of antecedents lie within four utterances, and restricting the search window materially improves resolution. [doi-10-18653-v1-2022-emnlp-main-778] In contrast, event references can span much larger distances, while asynchronous email and multi-party chat include replies to older material and crossing-thread dependencies. [manual-555fa5b6e8] [doi-10-3115-1220355-1220483] [doi-10-18653-v1-d15-1109]

This should not be interpreted as a literal empirical contradiction across identical tasks. It demonstrates strong genre and relation dependence. A short recency window can be a useful feature or first-stage search strategy, but it is unsafe as a hard msgloom constraint without workplace validation.

## Stack versus partially ordered unresolved issues

Roberts's information-structure framework represents unresolved Questions Under Discussion with a stack and organizes discourse strategy hierarchically. [doi-10-3765-sp-5-6] The empirical analysis of query responses argues that MOTIV and NO ANSW patterns require several issues to remain simultaneously accessible in a partially ordered QUD rather than a simple stack. [doi-10-15398-jlm-v4i2-173]

For msgloom, the safer implication is that sibling questions or requests should retain independent state instead of assuming strict last-in-first-out resolution.

## Single-target versus multi-target alignment

Some QA-alignment pipelines use one-to-one matching assumptions or construct grouped correspondences that are later expanded to pairwise links. [doi-10-1109-icaicta63815-2024-10762999] [manual-5a32708675] Other empirical datasets explicitly contain one answer aligned to multiple questions. [doi-10-1609-aaai-v33i01-3301134] [doi-10-3233-aic-2012-0516]

These are primarily task-definition differences, not incompatible observations, but they show that one-to-one alignment is too restrictive as the general representation for Topic 04.

## Reliability of exact non-NP antecedent boundaries

The DAD annotation work reports substantial agreement on non-NP antecedent identification under its structured scheme. [manual-be69c3aa17] By contrast, unconstrained discourse-segment annotation produces only moderate convergence, and the computational survey describes precise non-nominal span delimitation as a recurring problem. [manual-7743c50805] [doi-10-1162-coli-a-00327]

The difference is plausibly due to annotation constraints, corpus characteristics, and task definitions. It means msgloom cannot assume that an exact-span scheme will be reliable merely because one controlled annotation framework achieved high agreement.

## Value of syntactic constraints

Syntax helps some shell-noun resolution settings, especially nouns with stable syntactic expectations. [doi-10-3115-v1-d14-1056] However, strict family constraints harm versatile shell nouns, broader abstract-anaphora results can improve when explicit syntax is removed or disrupted, and adding unnecessary structural expansion can introduce noise in event-reference models. [doi-10-3115-v1-d14-1056] [1706.02256] [manual-555fa5b6e8]

The evidence therefore supports syntax as one signal rather than a hard universal restriction.

# Open Gaps

## gap-1 — ACADEMIC — HIGH — OPEN

**Direct empirical evidence is still missing for proposition-level agreement, rejection, approval, clarification, and answer scope in authentic workplace email or enterprise chat, especially cases where one short response applies to only part of a preceding message.**

The corpus now provides strong transfer evidence that acceptance and rejection can have subpropositional scope. [doi-10-1177-002383099603900306] It also provides authentic email evidence for non-adjacent response links, unanswered requests, multiple questions, and multi-question answer alignment. [doi-10-3115-1220355-1220483] [doi-10-3115-1708376-1708429] [doi-10-3233-aic-2012-0516] But none of these directly studies proposition-level agreement, rejection, or approval scope over authentic workplace messages.

Suggested query: `"reply scope" email dialogue proposition agreement approval rejection workplace communication`

## gap-2 — ENGINEERING — HIGH — OPEN

**A validated annotation and evaluation scheme is still missing for mapping workplace responses to exact proposition or span targets while representing exact, partial, ambiguous, unsupported, discontinuous, multiple-antecedent, and explicit no-link cases.**

The literature individually supports non-NP spans, alternative interpretations, no-link outcomes, multiple antecedents, and partial-credit evaluation. [manual-be69c3aa17] [manual-7743c50805] [2403.16609] [doi-10-1609-aaai-v33i01-3301134] [doi-10-5210-dad-2023-201] [doi-10-1162-coli-a-00327] No supplied paper validates this combined contract for the msgloom workplace setting.

This gap is therefore an engineering-validation problem rather than a reason for broad additional literature collection.

## gap-3 — ACADEMIC — HIGH — OPEN

**Direct evidence remains insufficient for aligning replies to one or more questions when a preceding workplace message contains multiple questions, requests, or alternatives, including proposition-level detection of questions that remain unanswered.**

Evidence has materially improved. Interview studies show selective answers to bundled questions. [doi-10-1016-j-pragma-2018-03-015] Email research permits unanswered questions and allows one answer sentence to correspond to several preceding questions. [doi-10-3115-1220355-1220483] [doi-10-3233-aic-2012-0516] Customer-service conversations contain one-to-many question-answer links. [doi-10-1609-aaai-v33i01-3301134] Assembly QA tasks directly address batches of questions followed by batches of answers. [manual-5a32708675] Grounding data additionally contain an ambiguous response after several questions. [2403.16609]

The remaining deficiency is exactly the project-critical one: proposition-level determination of which subquestions in a multi-question workplace message were answered and which remain open.

Suggested query: `"question answer alignment" dialogue "multiple questions" partial answer unanswered questions`

## gap-4 — ACADEMIC — MEDIUM — OPEN

**It remains open whether and how a workplace response should be modeled as targeting a composite or multi-proposition antecedent.**

Composite abstract referents are well supported linguistically: coherent propositions can be merged into one discourse referent. [doi-10-1515-ling-2018-0008] [manual-8b8a394daa] Dialogue parsing likewise permits complex discourse units and multi-parent structures. [doi-10-18653-v1-d15-1109] [doi-10-18653-v1-2023-eacl-main-247]

What remains missing is direct evidence about workplace responses such as a short “approved” or “yes” whose intended target is exactly a composite of several business propositions rather than the whole message or one component.

Suggested query: `"multi-antecedent" propositional anaphora dialogue composite discourse referent reply`

## gap-5 — ENGINEERING — HIGH — OPEN

**The appropriate msgloom policy for uncertainty-driven abstention, ambiguity, missing antecedents, and asymmetric error costs remains unvalidated.**

The literature clearly supports retaining ambiguous and no-link outcomes. [2403.16609] [doi-10-1609-aaai-v33i01-3301134] [manual-be69c3aa17] [doi-10-3115-1708376-1708429] It also supports evaluation that distinguishes partial multi-antecedent recovery from complete resolution. [doi-10-5210-dad-2023-201]

No supplied paper establishes confidence thresholds or the relative product cost of falsely broad approval/commitment links versus conservatively unresolved links. That decision therefore requires msgloom-specific engineering evaluation.

# Actionable Insights

1. **Use a proposition/span response graph, not a single message parent.** Each response should be able to link to zero, one, or multiple antecedent propositions, and one proposition should be able to receive multiple later responses. This follows directly from one-to-many, many-to-many, and multi-parent observations. [doi-10-1609-aaai-v33i01-3301134] [doi-10-18653-v1-d15-1109] [doi-10-3233-aic-2012-0516]

2. **Track each question or request independently.** A response to one component must not implicitly close sibling questions or the enclosing message. Unanswered links should remain visible. [doi-10-3115-1220355-1220483] [doi-10-3115-1708376-1708429] [doi-10-15398-jlm-v4i2-173]

3. **Treat Topic 01 and Topic 02 outputs as candidate constraints, not semantic answers.** Reply structure, quotations, adjacency, thread membership, and Topic spans are valuable signals, but email and dialogue evidence demonstrates that the semantic target may be non-adjacent or belong to only part of the structurally related material. [doi-10-3115-1220355-1220483] [2403.16609]

4. **Store relation type separately from antecedent identity.** The same target may stand in an answer, agreement, rejection, clarification, condition, or reference relation, and logically compatible responses are not necessarily acceptances. [doi-10-1177-002383099603900306]

5. **Make partial scope first-class.** A response should be able to accept one proposition while rejecting another, or answer one subquestion while leaving another open. [doi-10-1177-002383099603900306] [doi-10-1016-j-pragma-2018-03-015]

6. **Make ambiguity and abstention first-class.** If several active questions remain plausible or the antecedent is missing, preserve alternatives or return unresolved rather than selecting a single target. [2403.16609] [manual-be69c3aa17] [doi-10-1609-aaai-v33i01-3301134]

7. **Permit composite antecedents, but require coherence.** A composite target should be represented as an explicit set or structured group of spans. Arbitrary unions should not be created merely because propositions are nearby. [doi-10-1515-ling-2018-0008] [manual-8b8a394daa]

8. **Keep unresolved questions and requests as durable state.** They must remain available to Topic 05/06 rather than disappearing because some response occurred later in the thread. [doi-10-3115-1708376-1708429] [doi-10-15398-jlm-v4i2-173]

9. **Allow later evidence to revise scope.** Some grounding interpretations require subsequent context, so initial scope decisions should be versioned and revisable rather than destructively overwritten. [2403.16609]

10. **Evaluate rare structures separately.** Report performance for partial scope, no-link, multi-antecedent, composite antecedent, and ambiguity cases in addition to aggregate accuracy. Split-antecedent evaluation shows why otherwise strong aggregate metrics can conceal these failures. [doi-10-5210-dad-2023-201]

11. **For gap-2, run an independent annotation pilot.** Fixtures should include multi-question emails, partial yes/no replies, mixed approval/rejection, discontinuous targets, composite antecedents, explicit no-link, missing antecedents, and ambiguous alternatives. Exact-span agreement and proposition-level state agreement should be measured separately. The need for this separation is supported by documented span-boundary difficulty and alternative-antecedent phenomena. [doi-10-1162-coli-a-00327] [manual-7743c50805] [manual-be69c3aa17]

12. **For gap-5, evaluate asymmetric error costs.** False broad approval, rejection, or commitment links should be counted separately from conservative unresolved outputs. Existing literature justifies no-link and ambiguity as legitimate predictions but does not supply msgloom's decision threshold. [2403.16609] [doi-10-1609-aaai-v33i01-3301134]

13. **Use locality as a prior, not a hard constraint.** Dialogue-deixis results support strong recency priors, but email, event-reference, and multi-thread dialogue evidence requires escape to older candidates. [doi-10-18653-v1-2022-emnlp-main-778] [manual-555fa5b6e8] [doi-10-3115-1220355-1220483]

# Confidence Summary

Confidence is **high** in the structural conclusions that response scope can be non-adjacent, unanswered, multi-parent, composite, ambiguous, and proposition-specific. These properties recur across workplace email, customer service, dialogue discourse parsing, grounding, query-response analysis, and abstract-anaphora research. [doi-10-3115-1220355-1220483] [doi-10-1609-aaai-v33i01-3301134] [doi-10-18653-v1-d15-1109] [2403.16609] [doi-10-1177-002383099603900306]

Confidence is **medium** for transferring particular algorithms, candidate-window sizes, or annotation agreement figures directly to msgloom because the tasks and genres differ substantially. For example, very local discourse-deixis behavior coexists with long-distance email and event-reference evidence. [doi-10-18653-v1-2022-emnlp-main-778] [manual-555fa5b6e8]

Confidence is **low-to-medium** for production-level claims about partial approval, rejection, and commitment scope in authentic workplace email or enterprise chat. That remains the central evidence deficit represented by gap-1 and gap-3.

# Limitations

- The 38-paper corpus is heterogeneous, spanning workplace email, customer service, parliamentary minutes, institutional interviews, multiparty chat, task dialogue, free conversation, discourse semantics, grounding, coreference, and abstract anaphora.

- Only a minority of the papers directly study workplace email. [doi-10-3115-1220355-1220483] [doi-10-3115-1708376-1708429] [doi-10-3233-aic-2012-0516] None directly validates the complete msgloom proposition-level approval/rejection scope contract on authentic enterprise communication.

- Several highly relevant papers study anaphoric reference rather than response scope. They establish that propositions, events, clauses, and discourse segments can be antecedents and that exact boundaries can be uncertain, but they do not establish workplace answer or commitment accuracy. [doi-10-1162-coli-a-00327] [manual-be69c3aa17] [1706.02256]

- Several question-response datasets operate at sentence or utterance granularity, so their positive QA links do not by themselves establish which proposition inside a multi-proposition unit was answered.

- The input consists of reduced per-paper analyses rather than full papers. Methodological details, annotation guidelines, error analyses, and corpus definitions may therefore contain distinctions that cannot be reconstructed from the supplied findings alone.

- Reported numerical results are not directly comparable across papers because the units, candidate spaces, availability of gold segmentation or mentions, and scoring metrics differ.

- Composite antecedence is well supported as a linguistic and discourse phenomenon, but direct evidence about a short workplace response targeting exactly a coherent subset of several business propositions remains sparse. [doi-10-1515-ling-2018-0008] [doi-10-18653-v1-d15-1109]

- No supplied study determines msgloom-specific confidence thresholds or the asymmetric operational cost of a false broad approval/commitment link relative to an unresolved link. Consequently, gap-5 remains an engineering-validation problem rather than a literature-resolved parameter.
