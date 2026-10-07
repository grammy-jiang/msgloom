# Executive Summary

The corpus establishes strong conceptual and transfer-method foundations for proposition-level reference and response scope, but it does not directly solve the target workplace problem. Abstract and discourse-deictic reference can target propositions, events, facts, utterances, and composite discourse objects, and antecedent selection is empirically difficult even in dialogue benchmarks [doi-10-1162-coli-a-00327] [doi-10-18653-v1-2022-emnlp-main-778]. Formal work also supports partial answerhood and multiple simultaneously unresolved questions [doi-10-3765-sp-5-6] [doi-10-1007-bf00351935]. However, none of the 13 papers empirically evaluates whether a workplace reply answers, approves, rejects, or clarifies one exact proposition while leaving neighboring propositions unresolved. Multi-proposition antecedents are theoretically plausible, but direct response-scope evidence is absent [manual-8b8a394daa]. Consequently, all five inherited gaps remain open. The strongest immediate path is an engineering benchmark with proposition-level gold targets, explicit partial and unresolved states, multiple antecedents, and conservative abstention.

## Themes

Propositional and discourse reference is distinct from ordinary entity coreference. Antecedents may denote events, propositions, facts, situations, utterances, or speech acts rather than nominal entities [doi-10-1162-coli-a-00327] [doi-10-18653-v1-2022-emnlp-main-778].

Exact antecedent selection is repeatedly identified as a major difficulty. Errors arise not only from recognizing the referring expression but from candidate generation, antecedent boundaries, parsing, and insufficient context [1706.02256] [doi-10-18653-v1-2021-naacl-main-329] [doi-10-18653-v1-p17-1009]. In the end-to-end dialogue study, improved discourse-deixis performance was attributed principally to better antecedent selection rather than better anaphor recognition [doi-10-18653-v1-2022-emnlp-main-778].

Question semantics and QUD theory provide an important conceptual distinction between complete resolution and partial contribution. An assertion can be relevant because it supplies a partial answer, while multiple questions or subquestions can remain active in a discourse strategy [doi-10-3765-sp-5-6] [doi-10-1007-bf00351935]. This supports proposition-level state tracking rather than assuming that a reply resolves an entire preceding message.

Antecedent locality is useful but domain-dependent. In the evaluated dialogue data, more than 90 percent of discourse-deictic antecedents occurred within four utterances and recency restriction was particularly useful [doi-10-18653-v1-2022-emnlp-main-778]. By contrast, event-noun reference can span materially longer distances and generate very large candidate spaces [manual-555fa5b6e8], while a most-recent-verb heuristic performs poorly for event-pronoun resolution [manual-5c0971730d].

Rigid linguistic constraints are not reliable universal filters. Shell-noun family syntax helps some tightly constrained nouns but excludes valid cases for more versatile nouns [doi-10-3115-v1-d14-1056]. Similarly, explicit syntactic information helps a shell-noun task but can hurt unrestricted abstract-anaphora ranking [1706.02256]. Syntax should therefore operate as defeasible evidence rather than a hard eligibility rule.

Composite antecedents are linguistically plausible. Several propositions can be organized into one coherent abstract discourse referent, potentially enlarged as discourse develops [manual-8b8a394daa]. Independently, split-antecedent work demonstrates that some reference problems require selecting more than one antecedent source rather than forcing one antecedent [doi-10-18653-v1-2021-naacl-main-329]. These results motivate support for multi-proposition targets, although they do not directly validate workplace reply scope.

The empirical domain mismatch remains substantial. The main benchmarks cover general dialogue, newswire, broadcast news, and abstract-anaphora datasets rather than authentic workplace email or enterprise chat [doi-10-18653-v1-2021-codi-sharedtask-1] [doi-10-18653-v1-2022-emnlp-main-778] [manual-555fa5b6e8]. They provide transfer mechanisms and evaluation lessons, not production-domain accuracy evidence.

## Contradictions

**Recency versus long-distance search.** The dialogue discourse-deixis evidence strongly favors recent antecedents and finds a recency window especially useful [doi-10-18653-v1-2022-emnlp-main-778]. Event-reference work, however, documents substantially longer-distance links [manual-555fa5b6e8], and a simple most-recent-verb strategy performs poorly [manual-5c0971730d]. This is better interpreted as a domain/task tension than a direct contradiction. For msgloom, it argues for recency as a prior rather than a fixed exclusion window.

**Strict syntax versus flexible semantic resolution.** Shell-noun family constraints improve some tightly constrained nouns but reduce performance for syntactically versatile nouns [doi-10-3115-v1-d14-1056]. Likewise, explicit syntactic signals can improve shell-noun resolution while hurting broader abstract-anaphora ranking [1706.02256]. Both papers therefore undermine any assumption that one rigid syntactic template should determine response scope.

**Joint versus staged optimization.** Joint modeling of event triggers, anaphoricity, and event coreference improves all three tasks over independent models [doi-10-18653-v1-p17-1009]. In contrast, joint training for split-antecedent anaphora does not improve the ordinary single-antecedent and non-referring components, and the pre-trained variant performs better overall [doi-10-18653-v1-2021-naacl-main-329]. Joint optimization is therefore task- and architecture-dependent rather than intrinsically preferable.

**Whole utterances versus finer or composite antecedents.** One discourse-deixis system deliberately links anaphors to whole utterances for tractability [doi-10-18653-v1-2022-emnlp-main-778]. The broader survey identifies clausal, discontinuous, and multi-sentence antecedents [doi-10-1162-coli-a-00327], while Spanish abstract-anaphora theory permits composite referents formed from several propositions [manual-8b8a394daa]. This is an implementation simplification versus broader linguistic coverage, not evidence that whole-utterance targets are semantically sufficient.

## Open Gaps

**gap-1 — ACADEMIC, HIGH — OPEN.** Direct empirical evidence is still missing for proposition-level agreement, rejection, approval, clarification, and answer scope in authentic workplace email or enterprise chat, especially where a short response applies only to part of a preceding message. Dialogue discourse-deixis establishes abstract-reference resolution but does not establish the semantic scope of workplace approvals or commitments [doi-10-18653-v1-2021-codi-sharedtask-1] [doi-10-18653-v1-2022-emnlp-main-778] [doi-10-1162-coli-a-00327]. Suggested query: `"reply scope" email dialogue proposition agreement approval rejection workplace communication`.

**gap-2 — ENGINEERING, HIGH — OPEN.** The corpus still does not establish a validated annotation and evaluation scheme for workplace responses that supports exact, partial, ambiguous, unsupported, discontinuous, and multiple antecedents. It does provide useful design ingredients: difficult span boundaries and discontinuous antecedents [doi-10-1162-coli-a-00327], multiple antecedents [doi-10-18653-v1-2021-naacl-main-329], and partial answerhood [doi-10-3765-sp-5-6]. These ingredients are insufficient to count the gap as resolved because the complete workplace-specific scheme has not been validated.

**gap-3 — ACADEMIC, HIGH — OPEN.** Direct evidence remains insufficient for aligning a reply with one or more questions when a workplace message contains multiple questions, requests, or alternatives, and for identifying questions that remain unanswered. Formal question semantics represents answer propositions and multiple-wh structures [doi-10-1007-bf00351935], and QUD theory explicitly permits partial answers and unresolved questions [doi-10-3765-sp-5-6]. The situation-semantics account distinguishes question resolution from propositions and facts [doi-10-1007-bf00983299]. None of these papers supplies an empirical multi-question workplace reply-alignment benchmark. Suggested query: `"question answer alignment" dialogue "multiple questions" partial answer unanswered questions`.

**gap-4 — ACADEMIC, MEDIUM — OPEN.** It remains open whether and how a workplace response should be modeled as targeting a composite or multi-proposition antecedent. Composite abstract discourse referents are directly motivated theoretically [manual-8b8a394daa], non-nominal antecedents can exceed one contiguous span [doi-10-1162-coli-a-00327], and split-antecedent resolution demonstrates computational multi-source reference [doi-10-18653-v1-2021-naacl-main-329]. No included study evaluates semantic reply scope over a structured set of workplace propositions. Suggested query: `"multi-antecedent" propositional anaphora dialogue composite discourse referent reply`.

**gap-5 — ENGINEERING, HIGH — OPEN.** The appropriate abstention, ambiguity, and missing-antecedent policy remains unvalidated. Existing work establishes that candidate selection can fail and that forced proximity-based resolution is unreliable [doi-10-18653-v1-2022-emnlp-main-778] [doi-10-18653-v1-2021-naacl-main-329] [manual-5c0971730d], but no paper supplies msgloom's product-specific cost model for over-broad approval or commitment links versus unresolved links. This requires a dedicated benchmark and explicit asymmetric error-cost policy.

All five inherited gaps therefore remain open. None is closed by the current 13-paper corpus.

## Actionable Insights

Model a response as a relation from a **response span** to **zero, one, or multiple proposition/span targets**, rather than as a relation between whole messages. The target representation should permit clause-level, discontinuous, and composite antecedents [doi-10-1162-coli-a-00327] [manual-8b8a394daa].

Maintain state per proposition or question in multi-question messages. A reply that resolves one proposition should not implicitly resolve adjacent propositions. QUD theory directly supports partial answerhood rather than all-or-nothing response interpretation [doi-10-3765-sp-5-6].

Separate **candidate generation** from **semantic relation classification** in both implementation and evaluation. Split-antecedent and event-coreference work shows that valid targets can be lost before the semantic resolver is even applied [doi-10-18653-v1-2021-naacl-main-329] [doi-10-18653-v1-p17-1009].

Use recency as a weighted prior rather than a hard cutoff. It is highly informative in dialogue discourse deixis [doi-10-18653-v1-2022-emnlp-main-778], but longer-distance reference is well documented in event resolution [manual-555fa5b6e8].

Combine lexical, syntactic, semantic, and discourse signals as defeasible evidence. Do not let one syntactic pattern eliminate a semantically plausible target without corroborating evidence [doi-10-3115-v1-d14-1056] [1706.02256] [manual-8b8a394daa].

The engineering gold schema should permit **no antecedent**, **one antecedent**, and **multiple antecedents**, together with labels such as `exact`, `partial`, `ambiguous`, `unsupported`, and `missing_context`. The need for non-contiguous and multiple antecedent representations is supported by abstract-anaphora and split-antecedent work [doi-10-1162-coli-a-00327] [doi-10-18653-v1-2021-naacl-main-329].

Evaluate over-broad links separately from missed links. Aggregate coreference scores do not directly expose the product-critical error in which one narrow approval becomes attached to several propositions [doi-10-18653-v1-2021-codi-sharedtask-1] [doi-10-18653-v1-2022-emnlp-main-778]. A dedicated proposition-scope benchmark should therefore count target-level false positives and false negatives separately.

When no adequately supported antecedent exists, preserve the link as unresolved and hand genuine missing-context cases to Topic 07. Large candidate spaces and weak nearest-candidate heuristics make forced linking unsafe [manual-555fa5b6e8] [manual-5c0971730d].

## Confidence Summary

Confidence is **HIGH** that proposition/event/discourse antecedents require treatment beyond ordinary entity coreference, that antecedent selection and boundary identification are difficult, that partial answerhood is a legitimate discourse relation, and that hard whole-message or single-candidate assumptions are unsafe [doi-10-1162-coli-a-00327] [doi-10-3765-sp-5-6] [doi-10-18653-v1-2022-emnlp-main-778].

Confidence is **MEDIUM** for transferring composite-antecedent mechanisms directly to workplace response scope. Composite proposition referents are theoretically motivated [manual-8b8a394daa], and split-antecedent resolution supplies a computational analogy [doi-10-18653-v1-2021-naacl-main-329], but neither directly evaluates partial workplace replies.

Confidence is **LOW** for any claim about production accuracy on authentic workplace email or enterprise chat because no included empirical study evaluates that target domain.

## Limitations

The corpus contains no direct empirical benchmark for proposition-level reply scope in authentic workplace email or enterprise chat. Dialogue and news findings therefore remain transfer evidence rather than domain validation [doi-10-18653-v1-2021-codi-sharedtask-1] [manual-555fa5b6e8].

The two most relevant treatments of partial answers and multiple questions are formal semantic/pragmatic analyses rather than quantitative studies of naturally occurring multi-question reply alignment [doi-10-1007-bf00351935] [doi-10-3765-sp-5-6].

The analysis of *Resolving questions, II* is based only on the accessible abstract, limiting confidence about its detailed derivations, examples, and scope conditions [doi-10-1007-bf00983299].

The strongest source for composite multi-proposition antecedents is qualitative and explicitly treats its proposed processing sequence as hypothetical rather than experimentally established [manual-8b8a394daa].

Existing discourse-deixis evaluation commonly simplifies antecedents to whole utterances and therefore does not directly measure the exact sub-utterance response scope needed by msgloom [doi-10-18653-v1-2022-emnlp-main-778].

Several relevant benchmarks are small or sparse for difficult phenomena. ARRAU-AA contains a limited number of pronominal cases [1706.02256], while the split-antecedent test data contain very few split anaphors [doi-10-18653-v1-2021-naacl-main-329]. Rare partial and ambiguous workplace cases could therefore behave differently.

Finally, the corpus combines heterogeneous tasks, annotation schemes, datasets, and metrics. Performance numbers from abstract anaphora, discourse deixis, event coreference, shell-noun resolution, and split-antecedent resolution are not directly comparable [doi-10-1162-coli-a-00327].
