# Executive Summary

Across 26 papers, the strongest empirical conclusion is structural rather than proposition-semantic: reply and reference relations are frequently non-bijective, and systems must be able to represent no link, one link, and multiple antecedents or targets. Dialogue and email studies also show that adjacency alone is unreliable and that thread, discourse, segmentation, and conversational context materially help alignment. Abstract-anaphora work establishes that antecedents may be clauses, discourse segments, or composite material, while annotation studies document overlapping, disputed, or multiple acceptable antecedents. However, the corpus still does not validate proposition-level partial-answer, approval, rejection, or commitment scope in authentic workplace communication. Existing QA datasets generally align sentences, utterances, paragraphs, or grouped segments. Consequently, all five carried gaps remain open, including the combined annotation contract and msgloom-specific uncertainty/cost policy.

## Themes

A recurring theme is that reply and reference structures are not reliably one-to-one. Customer-service data contain explicit None alignments and one-to-many answer-to-question links [doi-10-1609-aaai-v33i01-3301134]. Multiparty dialogue contains one question with several answer attachments, later moves attached to several antecedents, and other non-tree structures [doi-10-18653-v1-d15-1109]. Email work likewise permits one answer sentence to correspond to several preceding questions [doi-10-3233-aic-2012-0516]. The empirical implication is limited but important: a representation that forces exactly one target cannot cover all observed structures.

A second theme is that relevant antecedents extend beyond entity coreference. Spoken-dialogue analysis finds substantial sentential antecedence and cases with no identifiable linguistic antecedent [doi-10-1093-jos-17-1-51]. The survey of non-nominal anaphora documents events, facts, propositions, situations, discontinuous material, and multi-sentence antecedents [doi-10-1162-coli-a-00327]. DAD explicitly annotates verbal phrases, clauses, discourse segments, propositions, questions, speech acts, and alternative interpretations [manual-be69c3aa17].

The literature also supports a distinction between question resolution and mere relevance. Roberts' QUD framework allows an assertion to contribute a partial answer without completely resolving the current question [doi-10-3765-sp-5-6], while Karttunen and the situation-semantics work provide formal accounts of questions and their resolutions [doi-10-1007-bf00351935; doi-10-1007-bf00983299]. These are semantic foundations, not empirical validation of a proposition-level workplace reply-state taxonomy.

Existing computational QA studies stop short of that proposition-level target. Customer-service alignment operates over utterances [doi-10-1609-aaai-v33i01-3301134]. The email systems operate principally over sentences or paragraphs [doi-10-3233-aic-2012-0516; manual-a6314f615a]. Japanese assembly work segments speeches into topic units, and the NTCIR evaluation expands multi-sentence QA groups into cross-product sentence pairs rather than identifying which proposition answers which proposition [doi-10-1109-icaicta63815-2024-10762999; manual-5a32708675]. These papers therefore provide evidence for coarse correspondence, not direct evidence for partial approval or partial answer scope inside a multi-proposition message.

Multiple interrogatives also require interpretation before they are counted as multiple obligations. In oral proficiency interviews, repeated or multiple questions can be reformulations used proactively or reactively to manage comprehension rather than independent requests [doi-10-1016-j-pragma-2007-07-011]. A system that mechanically counts question marks or interrogative clauses would therefore risk overstating outstanding work.

Antecedent boundaries are often difficult or ambiguous to delimit. The non-nominal-anaphora survey identifies span delimitation as a central annotation problem [doi-10-1162-coli-a-00327]. Discourse-deixis error analysis finds missing annotations, overlapping or multiple acceptable antecedents, and cases in which a pronoun packages a set of clauses [doi-10-18653-v1-s15-1035]. TRAINS annotation shows stronger agreement on antecedent endings than beginnings and only moderate span agreement [manual-7743c50805]. DAD permits alternative interpretations and identifies discontinuous antecedents as unresolved representational problems [manual-be69c3aa17]. The supported conclusion is therefore that boundaries are often disputed, overlapping, or multiply acceptable—not that every exact boundary is intrinsically ambiguous.

Composite targets are linguistically plausible. SDRT Complex Discourse Units can combine several EDUs into one antecedent and may encompass a complete question-answering sequence [doi-10-18653-v1-d15-1109]. The Spanish abstract-anaphora analysis describes merged propositional referents formed from rhetorically coherent propositions [manual-8b8a394daa]. DAD and the non-nominal-anaphora survey likewise cover discourse-segment and multi-sentence antecedents [manual-be69c3aa17; doi-10-1162-coli-a-00327]. None of this directly establishes how a workplace reply should distribute approval, rejection, or answer scope across several propositions.

Context and structure repeatedly improve alignment. Email thread and candidate-context features outperform lexical similarity alone [manual-a6314f615a]. Conversation-level context and dependencies improve customer-service QA alignment [doi-10-1609-aaai-v33i01-3301134]. Better segmentation materially improves cross-council QA alignment in the Japanese assembly study, although gold segmentation still leaves substantial alignment error [doi-10-1109-icaicta63815-2024-10762999]. Multiparty discourse parsing similarly benefits from structural modeling rather than simple adjacency [doi-10-18653-v1-d15-1109].

Locality is not uniform across tasks. In CODI-CRAC discourse deixis, more than 90% of evaluated antecedents occur within four utterances [doi-10-18653-v1-2022-emnlp-main-778]. In contrast, asynchronous email can contain answers several messages after their questions [manual-a6314f615a], and event-NP resolution produces substantially larger, longer-distance candidate spaces [manual-555fa5b6e8]. The short window in the event-pronoun model [manual-5c0971730d] is a modeling restriction, not empirical evidence that real antecedents are generally local.

Syntactic evidence shows convergence around task dependence rather than a contradiction. Explicit syntax helps some shell-noun settings but can hurt the broader ARRAU abstract-anaphora setting [1706.02256]. Family-specific shell-noun cues help nouns with stricter syntactic behavior but hurt more versatile nouns [doi-10-3115-v1-d14-1056]. Both results support treating syntax as useful but defeasible evidence.

## Contradictions

### One-to-one assumptions versus non-bijective discourse

The Japanese assembly pipeline uses one-to-one Hungarian matching and explicitly identifies two-answers-to-one-question cases as a residual problem requiring future one-to-many support [doi-10-1109-icaicta63815-2024-10762999]. The NTCIR benchmark also organizes question and answer groups into correspondence units [manual-5a32708675]. In contrast, customer-service, email, and multiparty-dialogue studies directly observe one-to-many, many-to-one, or multi-parent structures [doi-10-1609-aaai-v33i01-3301134; doi-10-3233-aic-2012-0516; doi-10-18653-v1-d15-1109]. This is best viewed as a mismatch between some benchmark/model assumptions and the broader empirical structure of conversation, rather than a contradiction between studies of an identical task.

### Local versus delayed antecedents

Discourse-deictic antecedents are highly local in the four CODI-CRAC dialogue datasets [doi-10-18653-v1-2022-emnlp-main-778]. Email QA and event-reference work, however, document delayed or longer-distance dependencies [manual-a6314f615a; manual-555fa5b6e8]. The evidence therefore does not support one universal distance constraint. manual-5c0971730d imposes a current-plus-two-previous-sentence window, but that is a modeling assumption and must not be counted as evidence for empirical locality.

### Exact gold links versus ambiguous or overlapping antecedents

Shared-task benchmarking necessarily scores concrete predicted links against gold structures [doi-10-18653-v1-2021-codi-sharedtask-1]. Yet discourse-deixis and annotation work documents multiple acceptable antecedents, overlap, alternative readings, and boundary disagreement [doi-10-18653-v1-s15-1035; manual-be69c3aa17; manual-7743c50805]. This creates a methodological tension: exact-link evaluation is operationally convenient, but some instances do not have one uniquely defensible antecedent span.

## Open Gaps

### gap-1 — ACADEMIC — HIGH

Direct empirical evidence is still missing for proposition-level agreement, rejection, approval, clarification, and answer scope in authentic workplace email or enterprise chat, especially cases where one short response applies to only part of a preceding message. Existing email studies align sentences or paragraphs rather than validating proposition-level semantic scope [doi-10-3233-aic-2012-0516; manual-a6314f615a].

Suggested query: `"reply scope" email dialogue proposition agreement approval rejection workplace communication`

**Status: open.**

### gap-2 — ENGINEERING — HIGH

A validated annotation and evaluation scheme remains missing for mapping workplace responses to exact proposition or span targets while representing exact, partial, ambiguous, unsupported, discontinuous, multiple-antecedent, and explicit no-link cases.

Several requirements are individually evidenced. Explicit None/no-link outcomes occur in customer-service alignment and dialogue anaphora [doi-10-1609-aaai-v33i01-3301134; doi-10-1093-jos-17-1-51]. Multiple antecedents or parents occur in discourse parsing and anaphora [doi-10-18653-v1-d15-1109; doi-10-18653-v1-2021-naacl-main-329]. Overlapping or alternative antecedents are documented in discourse-deixis annotation [doi-10-18653-v1-s15-1035; manual-be69c3aa17; manual-7743c50805]. Discontinuous and multi-sentence antecedents remain difficult [doi-10-1162-coli-a-00327; manual-be69c3aa17].

However, no reviewed paper validates the combined annotation contract required by msgloom.

**Status: open.**

### gap-3 — ACADEMIC — HIGH

Direct evidence remains insufficient for aligning replies to one or more questions when a preceding workplace message contains multiple questions, requests, or alternatives, including proposition-level identification of questions that remain unanswered.

The corpus now provides stronger evidence that multiple-question structures matter. Multiple interrogatives can be reformulations rather than independent obligations [doi-10-1016-j-pragma-2007-07-011]. One answer can align to multiple questions in customer service and email [doi-10-1609-aaai-v33i01-3301134; doi-10-3233-aic-2012-0516]. Batched political questions require explicit realignment [manual-5a32708675; doi-10-1109-icaicta63815-2024-10762999]. But these studies do not directly evaluate proposition-level partial answering and outstanding subquestions in workplace messages.

Suggested query: `"question answer alignment" dialogue "multiple questions" partial answer unanswered questions`

**Status: open.**

### gap-4 — ACADEMIC — MEDIUM

It remains open whether and how a workplace response should be modeled as targeting a composite or multi-proposition antecedent. Composite discourse referents and multi-unit antecedents are supported theoretically and empirically in other reference tasks [manual-8b8a394daa; doi-10-18653-v1-d15-1109; manual-be69c3aa17; doi-10-1162-coli-a-00327], but no reviewed study directly evaluates workplace reply scope over such a target.

Suggested query: `"multi-antecedent" propositional anaphora dialogue composite discourse referent reply`

**Status: open.**

### gap-5 — ENGINEERING — HIGH

The appropriate msgloom policy for uncertainty-driven abstention, ambiguity, missing antecedents, and asymmetric error costs remains unvalidated.

The literature supports representation of explicit None/no-link outcomes [doi-10-1609-aaai-v33i01-3301134; doi-10-1093-jos-17-1-51] and preservation of multiple or ambiguous antecedents [doi-10-18653-v1-s15-1035; manual-be69c3aa17]. It does **not** establish confidence thresholds for abstention or the relative cost of an over-broad approval or commitment link versus leaving the link unresolved. Those are msgloom-specific engineering and product-risk decisions requiring an explicit cost model and benchmark.

**Status: open.**

## Actionable Insights

The directly evidenced part of a candidate annotation scheme should support explicit no-link/None outcomes [doi-10-1609-aaai-v33i01-3301134; doi-10-1093-jos-17-1-51], multiple antecedents or parents [doi-10-18653-v1-d15-1109; doi-10-18653-v1-2023-eacl-main-247], non-nominal and discourse-segment antecedents [doi-10-1093-jos-17-1-51; manual-be69c3aa17], and alternative or overlapping antecedents [doi-10-18653-v1-s15-1035; manual-7743c50805]. The combined annotation contract is still an engineering hypothesis under gap-2 rather than an established standard.

Proposition decomposition should be treated as a proposed msgloom design hypothesis. Existing QA studies operate over sentences, paragraphs, utterances, topic segments, or QA groups and do not validate decomposition into proposition/question/request units before alignment [doi-10-3233-aic-2012-0516; manual-a6314f615a; manual-5a32708675; doi-10-1609-aaai-v33i01-3301134]. The same applies to assigning every antecedent proposition a full state set such as resolved, partially addressed, unresolved, ambiguous, and unsupported. Formal semantics motivates partial answerhood [doi-10-3765-sp-5-6], but the complete taxonomy requires engineering validation.

For approval, agreement, rejection, or commitment handling, msgloom may adopt a conservative risk-management rule that prevents state from propagating to sibling propositions unless there is target-specific evidence. That rule should be documented as a product safety policy, not presented as an empirical result from these papers. The transfer-domain evidence only motivates avoiding forced single-target links and preserving no-link, multi-target, and ambiguous cases [doi-10-1609-aaai-v33i01-3301134; doi-10-18653-v1-s15-1035; doi-10-18653-v1-d15-1109].

Candidate generation should not use one universal hard distance window. Recency is demonstrably useful for discourse deixis [doi-10-18653-v1-2022-emnlp-main-778], but delayed email answers and longer-distance event references require a path for more remote candidates [manual-a6314f615a; manual-555fa5b6e8].

Evaluation should separate unit or candidate detection, segmentation, link prediction, relation labeling, and semantic completeness. The Japanese assembly results show that even gold segmentation leaves significant residual alignment error [doi-10-1109-icaicta63815-2024-10762999], while discourse-deixis work shows that recognition and antecedent selection can create distinct bottlenecks [doi-10-18653-v1-s15-1035; doi-10-18653-v1-2022-emnlp-main-778].

A benchmark should contain dedicated strata for zero-link, one-to-one, one-to-many, many-to-one or multi-parent, delayed, overlapping-antecedent, and ambiguous cases instead of relying only on aggregate alignment scores [doi-10-1609-aaai-v33i01-3301134; doi-10-18653-v1-d15-1109; doi-10-18653-v1-s15-1035].

Flexible scoring deserves engineering investigation. Exact-span or single-gold evaluation can penalize overlapping or alternative interpretations that annotation studies consider reasonable [doi-10-18653-v1-s15-1035; manual-be69c3aa17; manual-7743c50805]. This supports testing partial-credit or multi-gold evaluation; it does not establish one particular scoring formula.

The project-context handoffs to Topic 07 for missing evidence and Topic 08 for attachment/table/visual grounding remain valid project-boundary decisions, but they are external scope assignments rather than findings derived from this reviewed corpus.

## Confidence Summary

Confidence is **high** for the structural conclusions that reply/reference relations can have zero or multiple links, that non-nominal and discourse-segment antecedents occur, that abstract-antecedent boundaries can be difficult or multiply acceptable, and that discourse or thread structure improves alignment in several datasets [doi-10-1609-aaai-v33i01-3301134; doi-10-18653-v1-d15-1109; doi-10-1162-coli-a-00327; manual-a6314f615a].

Confidence is **medium** for transferring those mechanisms to workplace email. Only a small subset of the corpus directly studies email [doi-10-3233-aic-2012-0516; manual-a6314f615a], and neither provides proposition-level scope for approval, rejection, commitment, or partial answers.

Confidence is **low** for any claim about msgloom-specific abstention thresholds, asymmetric error costs, the proposed full proposition-state taxonomy, or production-domain accuracy. Those remain open engineering or academic questions rather than conclusions established by this literature.

## Limitations

The evidence base is heterogeneous. It combines formal semantics, qualitative conversation analysis, non-nominal anaphora, event coreference, discourse parsing, customer service, political assembly minutes, student forums, game chat, and email. Transfer findings therefore justify mechanisms or experiments, not production-email accuracy.

Several papers were available only as abstracts, preventing verification of detailed methods, annotation procedures, and errors [doi-10-1007-bf00983299; doi-10-1007-s10489-013-0481-1; doi-10-1016-j-pragma-2007-07-011; doi-10-1093-jos-17-1-51].

The empirical studies use incompatible units—utterances, sentences, paragraphs, EDUs, topic segments, and QA groups—and heterogeneous metrics, so numerical performance cannot be compared directly across papers.

The corpus contains no direct benchmark for proposition-level approval, rejection, agreement, clarification, or commitment scope in authentic enterprise email or Teams-like communication.

Unanswered questions are present or inferable in several datasets, but they are rarely a proposition-level primary evaluation target [manual-a6314f615a; doi-10-1007-s10489-013-0481-1; doi-10-1609-aaai-v33i01-3301134].

Composite abstract antecedents are supported by discourse and anaphora literature [manual-8b8a394daa; doi-10-18653-v1-d15-1109], but this does not establish how a workplace response should distribute semantic scope across propositions within such a composite.

Finally, none of the reviewed papers validates the msgloom-specific cost tradeoff between over-broad state propagation and leaving a response unresolved. That remains gap-5 rather than a literature conclusion.
