# Executive Summary

Across 26 papers, the strongest empirical conclusion is that reply/reference structure is not reliably one-to-one: answers may target several earlier questions, questions may receive several responses, some moves have no antecedent, and abstract references may target clauses, discourse segments, or composite antecedents. Email, customer-service, assembly, and multiparty-dialogue studies show that thread/discourse structure materially improves alignment, but their units remain mostly sentences, paragraphs, utterances, or pre-grouped QA segments. None directly validates proposition-level partial approval, rejection, agreement, clarification, or answer scope in authentic workplace communication. Unanswered questions appear in annotations or discourse models but are rarely evaluated as first-class outcomes. Exact antecedent boundaries are also intrinsically ambiguous, especially for multi-clause or discontinuous content. The corpus therefore supports a multi-target, abstaining, scope-sensitive architecture, while leaving all five carried-over gaps open.

# Themes

## 1. Non-bijective alignment is normal, not exceptional

Several independent datasets reject a simple one-question/one-answer architecture. In customer-service conversations, answer utterances may align to no customer question or to multiple preceding questions [doi-10-1609-aaai-v33i01-3301134]. In multiparty STAC dialogue, one question may receive several answer attachments and a later move may attach to several earlier moves [doi-10-18653-v1-d15-1109]. A newer STAC parser therefore permits multiple parents, although it recovers only a minority of annotated multi-parent cases [doi-10-18653-v1-2023-eacl-main-247]. Email work likewise finds that a single answer sentence can correspond to several preceding questions [doi-10-3233-aic-2012-0516].

**Finding — HIGH confidence:** msgloom should represent response scope as a graph permitting zero, one, or multiple antecedents, rather than forcing one parent per response [doi-10-1609-aaai-v33i01-3301134; doi-10-18653-v1-d15-1109; doi-10-18653-v1-2023-eacl-main-247; doi-10-3233-aic-2012-0516].

## 2. Existing QA alignment stops above the proposition level

The closest direct email work links questions to sentence or paragraph answer units [doi-10-3233-aic-2012-0516; manual-a6314f615a]. Customer-service alignment operates on whole utterances [doi-10-1609-aaai-v33i01-3301134]. Japanese assembly benchmarks operate on topical segments or grouped sentence sets, with the NTCIR benchmark expanding each grouped correspondence into the full Cartesian product of its question and answer sentences [manual-5a32708675]. The cross-council study similarly notes that its one-question/one-answer representation does not identify partial response to propositions inside a question segment [doi-10-1109-icaicta63815-2024-10762999].

**Finding — HIGH confidence:** none of these direct alignment studies establishes whether a short reply answers, approves, rejects, or clarifies only one proposition inside a larger antecedent [doi-10-3233-aic-2012-0516; manual-5a32708675; doi-10-1609-aaai-v33i01-3301134; doi-10-1109-icaicta63815-2024-10762999].

## 3. Unanswered questions need an explicit state

Unresolved-question structure is directly modeled in student forums, including whether a question received an answer [doi-10-1007-s10489-013-0481-1]. The earlier email corpus also contained annotated questions for which no answer existed, but such questions were excluded from answer-pair classifier training [manual-a6314f615a]. The customer-service work has a `None` alignment for server utterances that answer no question, but its task is answer-centric rather than a direct evaluation of which customer questions remain unanswered [doi-10-1609-aaai-v33i01-3301134]. The later email study can leave a question unmatched but does not report unresolved-question performance as a distinct target phenomenon [doi-10-3233-aic-2012-0516].

**Finding — HIGH confidence:** lack of an answer must not be conflated with failed alignment; unresolved antecedent obligations need explicit representation and evaluation [doi-10-1007-s10489-013-0481-1; manual-a6314f615a; doi-10-1609-aaai-v33i01-3301134].

## 4. Several questions do not necessarily mean several obligations

Interactional analysis of oral proficiency interviews shows that multiple questions in one turn can be repetitions or reformulations used to repair an observed comprehension problem or proactively prevent one [doi-10-1016-j-pragma-2007-07-011].

**Finding — HIGH confidence:** msgloom should not mechanically convert every interrogative into an independent outstanding obligation; reformulation and repair relations must be considered [doi-10-1016-j-pragma-2007-07-011].

## 5. Proposition-like antecedents are broader than noun phrases or single clauses

Dialogue anaphora work reports that a substantial class of pronouns and demonstratives has sentential rather than nominal antecedents and that some have no identifiable linguistic antecedent [doi-10-1093-jos-17-1-51]. The non-nominal-anaphora survey identifies propositions, facts, events, and situations as major antecedent types and emphasizes discontinuous and multi-sentence cases [doi-10-1162-coli-a-00327]. Dialogue annotation experiments show references to regions spanning several utterances [manual-7743c50805], while DAD explicitly annotates clauses, discourse segments, propositions, questions, speech acts, and provisional discontinuous antecedents [manual-be69c3aa17]. The Spanish theoretical account goes further and models sums of several propositions as coherent abstract discourse referents [manual-8b8a394daa].

**Finding — HIGH confidence:** proposition-level resolution cannot safely require one contiguous nominal or clause span [doi-10-1093-jos-17-1-51; doi-10-1162-coli-a-00327; manual-7743c50805; manual-be69c3aa17; manual-8b8a394daa].

## 6. Exact boundaries and unique gold answers are often unstable

Discourse-deixis error analysis finds missing annotations, multiple acceptable antecedents, and cases where both system and gold choices are debatable; it explicitly argues for evaluation more flexible than one exact gold antecedent [doi-10-18653-v1-s15-1035]. TRAINS dialogue annotation obtains only moderate agreement for exact spans, with antecedent endings much easier to agree on than beginnings [manual-7743c50805]. The survey identifies exact boundary annotation as a central source of disagreement [doi-10-1162-coli-a-00327]. DAD obtains substantial agreement overall but notes that conventional kappa treats partially overlapping spans as complete mismatches and treats different preferred readings as disagreement even when both were recorded as legitimate alternatives [manual-be69c3aa17].

**Finding — HIGH confidence:** msgloom evaluation should explicitly represent overlap, alternative targets, ambiguity, and discontinuous targets rather than relying only on exact-match single-gold scoring [doi-10-18653-v1-s15-1035; manual-7743c50805; manual-be69c3aa17].

## 7. Structural context matters

Email answer detection improves substantially when thread and candidate-context features are added to lexical similarity [manual-a6314f615a]. Customer-service pointer networks exploit whole-conversation context and dependencies among alignment decisions [doi-10-1609-aaai-v33i01-3301134]. STAC research likewise shows that concurrent threads, crossing dependencies, and multi-parent structures matter for discourse parsing [doi-10-18653-v1-d15-1109], while attachment/relation multi-task learning gives additional gains [doi-10-18653-v1-2023-eacl-main-247].

**Finding — HIGH confidence:** Topic, thread, speaker, and discourse structure should enter antecedent ranking or constraints rather than relying on lexical similarity alone [manual-a6314f615a; doi-10-1609-aaai-v33i01-3301134; doi-10-18653-v1-d15-1109].

## 8. Locality is a useful prior, not a safe hard boundary

In CODI dialogue data, more than 90 percent of discourse-deictic antecedents fall within four utterances, and removing the recency restriction significantly hurts the model [doi-10-18653-v1-2022-emnlp-main-778]. However, asynchronous email explicitly contains answers delayed by several messages [manual-a6314f615a], and event-NP resolution shows substantially longer-distance candidate sets [manual-555fa5b6e8]. Short-window event-pronoun work also shows that proximity alone performs poorly even inside a deliberately local search space [manual-5c0971730d].

**Finding — HIGH confidence:** recency should be a ranking prior or cost control, not an irreversible candidate-elimination rule [doi-10-18653-v1-2022-emnlp-main-778; manual-a6314f615a; manual-555fa5b6e8].

## 9. Upstream segmentation and candidate generation are major failure sources

On Anjo assembly data, even gold segmentation leaves substantial alignment error, so segmentation is not the only problem; nevertheless better segmentation materially improves end-to-end QA alignment [doi-10-1109-icaicta63815-2024-10762999]. Split-antecedent work shows a large drop because valid cases are removed by candidate/anaphor gating before resolution [doi-10-18653-v1-2021-naacl-main-329]. In discourse deixis, oracle recognition produces much stronger antecedent resolution than predicted recognition [doi-10-18653-v1-s15-1035]. Event-coreference error analysis similarly shows that missing or mistyped triggers prevent later coreference recovery [doi-10-18653-v1-p17-1009].

**Finding — HIGH confidence:** component evaluation with gold inputs is useful diagnostically, but msgloom also needs end-to-end scoring in which upstream omissions remain in the final denominator [doi-10-1109-icaicta63815-2024-10762999; doi-10-18653-v1-2021-naacl-main-329; doi-10-18653-v1-s15-1035].

## 10. Linguistic constraints are valuable but defeasible

Shell-noun work shows that family-specific syntactic cues help some nouns but hurt syntactically versatile ones [doi-10-3115-v1-d14-1056]. The abstract-anaphora mention ranker similarly finds syntax useful in one shell-noun setting but potentially harmful on broader ARRAU abstract anaphora [1706.02256]. The survey therefore argues that explicit linguistic knowledge may remain useful in combination with data-driven approaches [doi-10-1162-coli-a-00327].

**Finding — HIGH confidence:** linguistic constraints should be soft evidence rather than hard universal filters [1706.02256; doi-10-3115-v1-d14-1056; doi-10-1162-coli-a-00327].

## 11. Formal semantics supports partial answerhood, but not yet the product task

Roberts defines relevance so an assertion may contribute only a partial answer to the current Question Under Discussion and allows unresolved questions to remain structurally active [doi-10-3765-sp-5-6]. Karttunen provides a compositional semantics for question denotations and multiple-wh questions [doi-10-1007-bf00351935]. The situation-semantic account distinguishes propositions, questions, and facts and treats resolution as a relation between facts and questions [doi-10-1007-bf00983299].

**Finding — MEDIUM confidence:** these theories justify preserving partial versus complete resolution conceptually, but they do not supply an empirical workplace annotation/evaluation solution [doi-10-3765-sp-5-6; doi-10-1007-bf00351935; doi-10-1007-bf00983299].

# Contradictions

### Locality of antecedents

[doi-10-18653-v1-2022-emnlp-main-778] finds a very strong locality pattern for dialogue discourse deixis, while [manual-555fa5b6e8] reports substantially longer-distance event-NP links and [manual-a6314f615a] documents delayed email answers. [manual-5c0971730d] imposes a short event-pronoun window but still finds that a nearest-verb heuristic is poor. This is best interpreted as domain/task dependence rather than a true contradiction.

### One-to-one alignment versus non-bijective structure

The assembly pipeline in [doi-10-1109-icaicta63815-2024-10762999] uses one-to-one Hungarian matching, and [manual-5a32708675] evaluates pre-grouped correspondence by cross-product sentence pairs. In contrast, customer-service data [doi-10-1609-aaai-v33i01-3301134] and multiparty discourse [doi-10-18653-v1-d15-1109; doi-10-18653-v1-2023-eacl-main-247] directly contain one-to-many or multi-parent structures. The Anjo results make the consequence explicit: one-to-one matching loses recall where two answers correspond to one question [doi-10-1109-icaicta63815-2024-10762999].

### Strict syntax versus flexible syntax

Syntax is beneficial in restricted shell-noun conditions but can hurt broader abstract-anaphora resolution [1706.02256]. Likewise, family-specific shell-noun constraints help nouns with strict constructions while hurting more versatile nouns [doi-10-3115-v1-d14-1056]. These results are compatible once syntactic constraints are treated as defeasible rather than universal.

### Unique exact antecedent versus ambiguous/composite antecedence

Single-gold formulations conflict with annotation evidence that multiple, overlapping, discontinuous, or composite antecedents can be reasonable. This tension is documented empirically in discourse deixis and dialogue annotation [doi-10-18653-v1-s15-1035; manual-7743c50805; manual-be69c3aa17] and theoretically in composite abstract-reference work [manual-8b8a394daa], consistent with the broader survey [doi-10-1162-coli-a-00327].

# Open Gaps

## gap-1 — OPEN — ACADEMIC — HIGH

Direct empirical evidence is still missing for proposition-level agreement, rejection, approval, clarification, and answer scope in authentic workplace email or enterprise chat, especially when a short response applies to only part of a preceding message. The email studies align questions and answers but do not supply the required agreement/approval scope labels [doi-10-3233-aic-2012-0516; manual-a6314f615a], while customer-service alignment remains utterance-level [doi-10-1609-aaai-v33i01-3301134].

Suggested query: `"reply scope" email dialogue proposition agreement approval rejection workplace communication`

**Status decision:** open. The added evidence strengthens transfer mechanisms but does not close the original domain-specific requirement.

## gap-2 — OPEN — ENGINEERING — HIGH

The corpus still does not establish a validated annotation and evaluation scheme for exact, partial, ambiguous, unsupported, discontinuous, and multiple response targets in workplace communication. Useful ingredients now exist: alternative antecedents and ambiguity [manual-be69c3aa17], flexible scoring needs [doi-10-18653-v1-s15-1035], boundary uncertainty [manual-7743c50805], and discontinuous/multi-sentence antecedents [doi-10-1162-coli-a-00327]. None combines these into the complete msgloom contract.

**Status decision:** open.

## gap-3 — OPEN — ACADEMIC — HIGH

Evidence now clearly establishes that one answer can correspond to multiple questions [doi-10-3233-aic-2012-0516; doi-10-1609-aaai-v33i01-3301134] and that unanswered questions occur in real email/forum data [manual-a6314f615a; doi-10-1007-s10489-013-0481-1]. However, proposition-level detection of which subset of questions or requests in a workplace message remains unanswered is still not directly evaluated.

Suggested query: `"question answer alignment" dialogue "multiple questions" partial answer unanswered questions workplace email`

**Status decision:** open.

## gap-4 — OPEN — ACADEMIC — MEDIUM

Composite abstract antecedents have considerably stronger support after this corpus. Multiple preceding propositions can form one abstract referent [manual-8b8a394daa]; discourse references can span several utterances [manual-7743c50805; manual-be69c3aa17]; and conversational discourse graphs contain multi-parent and Complex Discourse Unit structures [doi-10-18653-v1-d15-1109]. Split-antecedent resolution also demonstrates that plural antecedent sets can be modeled computationally [doi-10-18653-v1-2021-naacl-main-329]. What remains missing is direct evaluation of a workplace response whose semantic scope is a composite set of propositions.

Suggested query: `"multi-antecedent" propositional anaphora dialogue composite discourse referent reply workplace`

**Status decision:** open.

## gap-5 — OPEN — ENGINEERING — HIGH

The literature supports explicit `None` outcomes [doi-10-1609-aaai-v33i01-3301134], unidentified linguistic antecedents [doi-10-1093-jos-17-1-51], and explicit ambiguity/alternative targets [doi-10-18653-v1-s15-1035; manual-be69c3aa17]. It does not determine the msgloom-specific relative cost of falsely broadening an approval or commitment versus leaving it unresolved.

**Status decision:** open. A product-risk benchmark and cost model are still required.

## Topic 07 handoff — OUT_OF_SCOPE — HIGH

If the real antecedent is absent from supplied context, retrieving it is an evidence-retrieval problem rather than a Topic 04 alignment error. Topic 04 should expose the unresolved/missing-evidence state and hand the need to Topic 07.

## Topic 08 handoff — OUT_OF_SCOPE — MEDIUM

References to attachment pages, table cells, screenshots, rows, or visual regions require document/multimodal grounding. Topic 04 should consume the grounded target from Topic 08 and determine the semantic relation/scope, not duplicate the grounding research.

# Actionable Insights

1. Represent response scope as a graph over proposition/span nodes. Permit zero, one, or multiple antecedent targets and multiple replies to the same antecedent [doi-10-1609-aaai-v33i01-3301134; doi-10-18653-v1-d15-1109].

2. Decompose candidate antecedent messages into proposition/question/request units before semantic alignment, while retaining message/span lineage. A reply to one unit must not automatically resolve sibling units [doi-10-3233-aic-2012-0516; manual-5a32708675].

3. Maintain proposition-level state such as `resolved`, `partially-addressed`, `unresolved`, `ambiguous`, and `unsupported`, rather than a single answered/unanswered message flag [doi-10-1007-s10489-013-0481-1; doi-10-3765-sp-5-6].

4. Detect reformulation and repair before converting multiple interrogatives into multiple obligations [doi-10-1016-j-pragma-2007-07-011].

5. Permit clausal, multi-proposition, discontinuous, and alternative antecedents. The representation should not require every valid target to be one contiguous span [doi-10-1162-coli-a-00327; manual-be69c3aa17; doi-10-18653-v1-s15-1035].

6. Use recency, Topic membership, thread structure, speakers, and discourse relations as ranking evidence rather than hard pruning. Delayed answers must remain recoverable [doi-10-18653-v1-2022-emnlp-main-778; manual-a6314f615a; manual-555fa5b6e8].

7. Evaluate both component performance and the complete pipeline. Gold proposition segmentation can diagnose the linker, but predicted-input evaluation must count proposition-detection and candidate-generation failures in the final denominator [doi-10-1109-icaicta63815-2024-10762999; doi-10-18653-v1-2021-naacl-main-329].

8. Build a msgloom-specific annotation scheme with exact targets plus explicit partial overlap, multiple targets, alternative acceptable targets, discontinuity, ambiguity, and no-supported-antecedent outcomes [doi-10-18653-v1-s15-1035; manual-7743c50805; manual-be69c3aa17].

9. For downstream state changes, conservatively preserve scope. A detected “yes”, approval, rejection, or agreement should not propagate to sibling propositions without target-specific evidence. The literature supports no-link and ambiguity representations but does not supply the required product cost threshold [doi-10-1609-aaai-v33i01-3301134; doi-10-1162-coli-a-00327].

10. Combine linguistic rules with learned representations as soft evidence rather than irreversible constraints [1706.02256; doi-10-3115-v1-d14-1056].

# Confidence Summary

Confidence is **HIGH** for the structural conclusions that response/reference relations are often non-bijective, discourse context improves alignment, abstract antecedent boundaries can be ambiguous, and current QA-alignment benchmarks do not directly solve proposition-level partial response scope. These conclusions recur across email, customer service, assembly minutes, multiparty chat, discourse deixis, and abstract-anaphora studies [doi-10-3233-aic-2012-0516; doi-10-1609-aaai-v33i01-3301134; doi-10-18653-v1-d15-1109; doi-10-1162-coli-a-00327].

Confidence is **MEDIUM** for direct transfer to authentic enterprise approvals, agreements, commitments, and rejections. The closest email studies are coarse-grained and do not label those scope relations [doi-10-3233-aic-2012-0516; manual-a6314f615a]. Much of the strongest recent evidence comes instead from customer service, assembly minutes, task-oriented chat, or general discourse deixis [doi-10-1609-aaai-v33i01-3301134; doi-10-1109-icaicta63815-2024-10762999; doi-10-18653-v1-2022-emnlp-main-778]. Formal question theories support partial answerhood conceptually but are not empirical workplace validation [doi-10-3765-sp-5-6; doi-10-1007-bf00351935].

# Limitations

- This synthesis uses only the 26 supplied per-paper analyses and does not independently re-read the primary publications.

- Several relevant analyses rely on abstracts rather than full papers, limiting verification of annotation methods, examples, and detailed results [doi-10-1007-bf00983299; doi-10-1007-s10489-013-0481-1; doi-10-1016-j-pragma-2007-07-011; doi-10-1093-jos-17-1-51].

- Direct workplace-email evidence is sparse. The main email studies use Enron and a student-organization corpus, and neither evaluates proposition-level partial approval/agreement/rejection scope [doi-10-3233-aic-2012-0516; manual-a6314f615a].

- Most computational evaluations operate at sentence, paragraph, utterance, EDU, or grouped-segment level; their accuracy must not be interpreted as proposition-scope accuracy [doi-10-1609-aaai-v33i01-3301134; manual-5a32708675; doi-10-18653-v1-2023-eacl-main-247].

- The corpus combines QA alignment, discourse parsing, abstract anaphora, discourse deixis, event coreference, and formal question semantics. These provide useful transfer evidence but are not equivalent tasks [doi-10-1162-coli-a-00327; doi-10-18653-v1-p17-1009].

- Several benchmarks impose assumptions that can hide the target phenomenon: one-to-one matching [doi-10-1109-icaicta63815-2024-10762999], exact unique antecedents [doi-10-18653-v1-s15-1035], tree decoding [doi-10-18653-v1-d15-1109], or full cross-products between grouped question and answer sentences [manual-5a32708675].

- No supplied paper estimates the decision-specific harm of falsely broadening an approval, rejection, or commitment in a personal work-information system. The abstention threshold therefore remains an engineering/product-risk decision rather than a literature-derived value [doi-10-1609-aaai-v33i01-3301134; doi-10-1162-coli-a-00327].
