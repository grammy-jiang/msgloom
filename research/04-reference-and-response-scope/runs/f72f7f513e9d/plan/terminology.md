# empirical reply-to-proposition alignment in email and dialogue, focusing on partial replies, multiple questions, unanswered questions, and multi-proposition antecedents academic terminology analysis

## Product problem

The target is not ordinary coreference, email threading, dialogue-act classification, or question answering. The desired unit is a semantic link from an observed response to the exact preceding proposition or propositions that the response affects:

`response span -> antecedent proposition/span(s) -> semantic relation -> scope/uncertainty`

The important relations include answer, agreement, acceptance/approval, rejection, disagreement, clarification, correction, confirmation, condition, and reference. The target representation must be able to distinguish exact, partial, ambiguous, unsupported, missing, composite, and potentially multiple antecedents.

The difficult cases are structurally asymmetric. A preceding work message may contain five propositions and three questions, while the reply contains only "yes", "approved", "not the date", or one short sentence. The research problem is therefore not merely whether the reply expresses agreement or supplies an answer. It is which proposition or question receives that relation and which neighboring propositions remain untouched.

The terminology audit indicates that no single mature academic task name cleanly covers the complete problem. Discovery should therefore combine several DIRECT task families and explicitly separate them from TRANSFER families.

The strongest promoted umbrella terminology is:

- non-nominal anaphora / non-nominal antecedent;
- abstract and propositional anaphora;
- discourse deixis / discourse-deictic reference;
- dialogue discourse attachment and discourse dependencies;
- response target / reply target / antecedent selection;
- question-under-discussion, answerhood, partial answer, and unresolved question;
- agreement or acceptance with target identification;
- null, ambiguous, multiple, composite, and discontinuous antecedents.

"Coreference resolution", "dialogue act", "agreement detection", "contradiction detection", "business email", and "workplace communication" should not be used as standalone discovery terms because they retrieve large bodies of literature that do not perform antecedent selection.

## Seed keyword audit

| Seed | Academic meaning | Fit | Main risk |
| --- | --- | --- | --- |
| discourse deixis | Reference to prior discourse segments or abstract objects evoked by discourse rather than ordinary nominal entities. | STRONG | Often theoretical or demonstrative-pronoun focused rather than short response acts. |
| discourse-deictic reference | Reference to propositions, facts, events, situations, or discourse material using discourse-dependent expressions. | STRONG | Terminology is fragmented across several neighboring names, so exact-phrase search has poor recall. |
| abstract anaphora | Anaphora to abstract objects such as propositions, events, facts, situations, or discourse segments. | STRONG | Broader than reply scope and often limited to pronouns such as this, that, or it. |
| propositional anaphora | Anaphoric reference to previously introduced propositional content. | STRONG | Relevant papers may instead call the phenomenon non-nominal or abstract anaphora. |
| event anaphora | Reference to a prior event or eventuality. | MODERATE | Event identity and event-coreference clustering do not establish response scope. |
| anaphora resolution | Selecting an antecedent for an anaphoric expression. | MODERATE | Dominated by nominal/pronominal entity resolution. |
| coreference resolution | Clustering mentions that refer to the same entity or referent. | WEAK | Mainstream benchmarks are entity-centric and structurally different from reply-to-proposition alignment. |
| coreference to events | Linking mentions referring to the same event. | MODERATE | Same-event classification is not the same as a response targeting an event description. |
| coreference to propositions | Reference or coreference involving propositional antecedents. | STRONG | Useful concept but less standardized as an exact task name. |
| conversational coreference | Coreference/reference resolution in conversational data. | MODERATE | Often remains entity-centric despite using dialogue data. |
| dialogue reference resolution | Resolving references using conversational state and previous turns. | STRONG | Frequently concerns physical objects or nominal entities unless proposition/span constraints are added. |
| dialogue discourse parsing | Recovering discourse attachments and relation labels among dialogue units. | STRONG | Typical units may be whole turns rather than independent propositions inside one message. |
| conversational discourse relations | Semantic/pragmatic links among conversational contributions. | STRONG | Relation labels may be present without sufficiently fine-grained scope. |
| discourse relation recognition | Classification of relations between discourse arguments. | MODERATE | Many benchmarks provide the two arguments as gold, removing antecedent selection from the task. |
| response-to discourse relation | A conversational attachment in which a later contribution responds to an earlier unit. | STRONG | Can reduce to turn-level reply structure rather than semantic proposition scope. |
| adjacency pairs | Paired conversational actions such as question-answer or offer-acceptance. | MODERATE | Sequential organization normally lacks exact span targets, multi-target scope, and uncertainty. |
| dialogue act | Functional label such as question, answer, agreement, request, acknowledgment, or acceptance. | MODERATE | Tells what an utterance does but normally not which earlier proposition it affects. |
| question answer alignment | Associating a response with the question it answers. | STRONG | Search results can drift into answer retrieval/ranking where the question is already given. |
| question resolution | Closure or resolution of a question/issue in dialogue. | MODERATE | Highly overloaded across QA, information retrieval, semantic interpretation, and issue management. |
| answer scope | The question, issue, subquestion, or portion thereof resolved by an answer. | STRONG | Excellent conceptual fit but not a consistently standardized computational task name. |
| partial answer detection | Detecting that a response resolves only part of the question or issue. | STRONG | Frequently confused with partially correct answers or partial-credit assessment. |
| multi-question answering in dialogue | Handling contexts involving more than one question. | WEAK | Usually means a system answering several supplied questions rather than aligning one human reply to competing prior questions. |
| agreement detection | Detecting agreement or acceptance. | MODERATE | Most work is targetless or turn-level. |
| disagreement detection | Detecting disagreement, rejection, or dissent. | MODERATE | Correct disagreement classification can still be attached to the wrong proposition. |
| agreement target identification | Identifying the proposition, claim, utterance, or argument toward which agreement is expressed. | STRONG | Relevant work may be indexed under stance, acceptance, grounding, or discourse attachment instead. |
| agreement scope | Determining the portion of preceding content to which agreement applies. | STRONG | Highly relevant but sparsely standardized as a computational task name. |
| stance with target identification | Jointly identifying stance and the entity, proposition, or claim targeted by that stance. | STRONG | Many stance datasets use a fixed named target rather than selecting an antecedent from dialogue. |
| entailment relative to a proposition | Testing whether one text entails or supports a target proposition. | MODERATE | NLI normally receives the proposition pair as input and therefore does not solve antecedent discovery. |
| contradiction detection | Detecting semantic inconsistency between statements. | WEAK | Usually sentence-pair or document-level classification with gold comparison units. |
| business email | Professional/organizational email as a data domain. | WEAK | Alone it retrieves large amounts of unrelated email classification, summarization, marketing, spam, and organizational research. |
| email reply | A reply message or reply relationship within email. | MODERATE | Often means threading, response generation, reply prediction, or response time rather than semantic scope. |
| approval scope | The precise prior content to which an approval applies. | MODERATE | Project-relevant but not a standard NLP task term and heavily overloaded by security, governance, and regulatory uses. |
| workplace communication | Organizational communication across email, meetings, messaging, and collaboration tools. | MODERATE | Useful as a domain filter, not as a task definition. |

Terms that should be promoted beyond the original seed list are `non-nominal anaphora`, `non-nominal antecedent`, `reference to abstract entities`, `sentential antecedent`, `antecedent selection`, `antecedent span`, `response target`, `reply target`, `discourse attachment`, `question-under-discussion`, `answerhood`, `unresolved question`, `null antecedent`, `missing antecedent`, `composite discourse referent`, `split antecedent`, `multiple antecedents`, `discontinuous antecedent`, `selective prediction`, and `abstention`.

## Academic task families

### F1 — Non-nominal, abstract, and propositional anaphora — DIRECT

This family studies reference whose antecedent is a proposition, fact, event, situation, clause, or discourse segment rather than a normal entity. It is the strongest established terminology family for the antecedent side of the msgloom problem.

Important seed work includes:

- Webber (1988), *Discourse Deixis: Reference to Discourse Segments*.
- Byron (2002), *Resolving Pronominal Reference to Abstract Entities*.
- Kolhatkar et al. (2018), *Anaphora with Non-Nominal Antecedents in Computational Linguistics: A Survey*.

The main limitation is that much of this literature resolves demonstratives or pronouns, not pragmatic response acts such as "yes", "approved", or "not that part". Nevertheless, antecedent-span representation, non-nominal candidate generation, null antecedents, and evaluation schemes are directly relevant to gaps 1 and 2.

### F2 — Dialogue discourse attachment and response relations — DIRECT

This family treats dialogue as a discourse graph or dependency structure. A later contribution attaches to an earlier discourse unit and receives a semantic/pragmatic relation.

Relevant terminology includes `dialogue discourse parsing`, `discourse attachment`, `discourse dependency`, `response-to`, `reply-to discourse relation`, and `conversational discourse relations`.

Known seed work includes:

- Schegloff and Sacks (1973), *Opening up Closings*, as foundational conversational-response organization.
- Asher et al. (2016), *Discourse Structure and Dialogue Acts in Multiparty Dialogue: the STAC Corpus*.
- Li et al. (2020), *Molweni: A Challenge Multiparty Dialogues-based Machine Reading Comprehension Dataset with Discourse Structure*.

This family is highly relevant but must be screened for unit granularity. A correct edge to an entire preceding turn is insufficient when that turn contains three independent questions or propositions.

### F3 — Question-answer attachment, answerhood, QUD, and unresolved questions — DIRECT

This is the principal family for gap-3.

The search should not center on generic "conversational QA". It should center on:

- question-answer attachment;
- question-answer pair identification;
- question-under-discussion / QUD;
- answerhood;
- complete versus partial answers;
- issue resolution;
- unanswered or unresolved questions;
- multiple competing questions in preceding discourse.

Roberts (1996), *Information Structure in Discourse: Towards an Integrated Formal Theory of Pragmatics*, is a useful foundational seed for the QUD tradition.

The desired empirical capability is:

`response -> which prior question(s)? -> complete/partial/non-answer -> which questions remain open?`

A benchmark where the gold question is handed directly to the answering system does not test this capability.

### F4 — Agreement, disagreement, acceptance, rejection, and grounding with explicit targets — DIRECT

This family is central to gap-1.

Galley et al. (2004), *Identifying Agreement and Disagreement in Conversational Speech: Use of Bayesian Networks to Model Pragmatic Dependencies*, is a known seed for computational agreement/disagreement work.

Discovery must impose a stronger admission criterion than "detects agreement". A useful paper should expose, recover, or evaluate the target of the agreement, acceptance, rejection, clarification, confirmation, correction, or grounding act.

For msgloom:

`agreement label without target < agreement + target < agreement + exact target scope`

The third level is the required capability.

### F5 — Workplace email and enterprise-dialogue response semantics — DIRECT

This family exists specifically to close the target-domain evidence gap rather than to discover another generic method.

Cohen, Carvalho, and Mitchell (2004), *Learning to Classify Email into Speech Acts*, is a useful seed for email communicative-act work, but ordinary email speech-act classification is not itself sufficient.

Target-domain papers should receive high priority only when they combine authentic organizational communication with at least one of:

- explicit antecedent links;
- proposition or span targets;
- multiple questions;
- partial answers;
- partial agreement;
- acceptance/rejection target;
- approval target;
- unresolved questions;
- fine-grained discourse attachment.

Authentic email data with only whole-message labels provides domain context but does not close gap-1, gap-2, or gap-3.

### F6 — Antecedent annotation and span-level response-target evaluation — DIRECT

Gap-2 requires dedicated discovery of annotation and evaluation methodology.

The desired annotation space should be able to represent at least:

- exact target;
- partial target;
- multiple targets;
- composite target;
- discontinuous target;
- ambiguous candidates;
- target absent from supplied context;
- unsupported link;
- unresolved/abstain.

Discovery should search for antecedent-span annotation, response-target annotation, non-nominal anaphora annotation, null antecedents, multiple antecedents, and ambiguous antecedent annotation.

A corpus that forces exactly one previous turn as the antecedent is structurally unable to represent several of the project's highest-risk cases.

Evaluation must also score target correctness. Relation-label accuracy alone is inadequate: predicting "agreement" while linking it to the wrong clause must be an error.

### F7 — Composite, multiple, split, and discontinuous antecedents — TRANSFER

This family targets gap-4.

Potentially useful terminology includes:

- multiple antecedents;
- multi-antecedent anaphora;
- split antecedents;
- composite discourse referents;
- plural antecedents;
- discontinuous antecedents;
- multiple discourse antecedents.

Much of this literature concerns plural entity reference rather than proposition-level response scope, so it must be classified as TRANSFER unless it directly evaluates abstract or propositional antecedents.

Its value is representational: it may show how one anaphor or response can depend on several independently introduced source units rather than forcing one contiguous antecedent.

### F8 — Ambiguous, null, unsupported, and missing antecedents with abstention — TRANSFER

This family supports gap-5.

Relevant concepts include:

- null antecedent;
- absent or missing antecedent;
- unresolved reference;
- ambiguous antecedent;
- non-anaphoric detection;
- multiple candidate antecedents;
- selective prediction;
- abstention;
- confidence calibration.

The literature can inform representation and confidence handling, but it cannot determine msgloom's final product cost function.

In particular, the relative harm of:

`incorrect broad approval link`

versus:

`leave approval unresolved`

must be determined by a dedicated product-risk benchmark. It must not be inferred from generic NLP accuracy.

### F9 — Target-conditioned stance and proposition-pair inference — TRANSFER

Stance, textual entailment, contradiction, support/attack, and proposition-pair relation classification can help after candidate antecedents have already been identified.

Known transfer seeds include:

- Bowman et al. (2015), *A Large Annotated Corpus for Learning Natural Language Inference*.
- Williams, Nangia, and Bowman (2018), *A Broad-Coverage Challenge Corpus for Sentence Understanding through Inference*.

These methods can help distinguish agreement, contradiction, rejection, or support relative to a candidate proposition.

They cannot by themselves answer:

`Which of the five preceding propositions should be compared with the response?`

They therefore remain TRANSFER evidence.

### F10 — Conversation disentanglement and reply-to graph prediction — TRANSFER

Conversation disentanglement predicts which previous turn or message a new contribution replies to.

Kummerfeld et al. (2019), *A Large-Scale Corpus for Conversation Disentanglement*, is a useful seed.

This can narrow candidate antecedents in enterprise chat, but Topic 01 already owns structural message relationships. For Topic 04, the output should be treated only as prior evidence:

`likely parent message -> candidate propositions inside that message -> semantic target resolution`

A message-level parent edge must never be treated as proof that every proposition in the parent was answered or approved.

## Query families

### F1 — DIRECT: non-nominal/propositional antecedents

- `"non-nominal anaphora" dialogue antecedent resolution`
- `"non-nominal antecedent" conversation proposition span`
- `"abstract anaphora" dialogue antecedent annotation`
- `"propositional anaphora" dialogue antecedent`
- `"discourse deixis" dialogue antecedent resolution`
- `"discourse-deictic" reference conversation antecedent`
- `"reference to abstract entities" dialogue anaphora`
- `"sentential antecedent" anaphora dialogue proposition`

### F2 — DIRECT: dialogue attachment and response relations

- `"dialogue discourse parsing" response attachment relation`
- `"dialogue discourse structure" response antecedent relation`
- `"conversational discourse relations" response attachment`
- `"response-to" discourse relation dialogue`
- `"reply-to" discourse relation dialogue semantic`
- `"discourse attachment" dialogue response antecedent`
- `"discourse dependency" dialogue response relation`
- `"multiparty dialogue" discourse attachment response`

### F3 — DIRECT: questions, partial answers, and unresolved questions

- `"question answer alignment" dialogue antecedent`
- `"question-answer" attachment dialogue discourse`
- `"question-answer pair" identification dialogue multiple questions`
- `"partial answer" dialogue question resolution`
- `"partial answer" conversation "question under discussion"`
- `"question under discussion" dialogue answer antecedent`
- `"unanswered question" dialogue previous turn`
- `"unresolved question" dialogue discourse`
- `"multiple questions" dialogue answer alignment`
- `"which question" answer dialogue antecedent`
- `"answerhood" dialogue partial answer`
- `"issue resolution" dialogue question answer`

This family should be searched before generic conversational-QA terminology because generic QA has extremely high false-positive volume.

### F4 — DIRECT: agreement/acceptance/rejection target and scope

- `"agreement target" dialogue proposition`
- `"agreement target identification" dialogue`
- `"agreement scope" dialogue proposition`
- `"partial agreement" dialogue antecedent`
- `"acceptance" dialogue antecedent proposition`
- `"rejection" dialogue antecedent proposition`
- `"acceptance relation" dialogue discourse`
- `"agreement disagreement" dialogue discourse attachment`
- `"clarification" dialogue antecedent identification`
- `"correction" dialogue antecedent proposition`
- `"confirmation" dialogue antecedent scope`
- `"grounding" dialogue acceptance antecedent`

### F5 — DIRECT: authentic workplace/email evidence

- `"business email" reply proposition antecedent agreement`
- `"business email" partial reply question answer`
- `"business email" partial agreement reply`
- `"email reply" agreement antecedent proposition`
- `"email reply" approval antecedent scope`
- `"email reply" multiple questions partial answer`
- `"email" unanswered questions reply alignment`
- `"workplace email" response target proposition`
- `"workplace communication" agreement target antecedent`
- `"enterprise chat" reply proposition agreement`
- `"enterprise chat" multiple questions answer alignment`
- `"workplace chat" partial reply antecedent`
- `"organizational email" speech act antecedent`
- `"email" acceptance rejection discourse relation`

These queries carry the heaviest gap-closing value because earlier rounds still lack direct workplace evidence.

### F6 — DIRECT: annotation and evaluation

- `"antecedent span" anaphora annotation non-nominal`
- `"antecedent span" dialogue reference annotation`
- `"antecedent selection" dialogue proposition annotation`
- `"response target" annotation dialogue span`
- `"reply target" annotation proposition dialogue`
- `"multiple antecedents" annotation dialogue reference`
- `"ambiguous antecedent" annotation dialogue`
- `"null antecedent" annotation anaphora dialogue`
- `"discontinuous antecedent" anaphora annotation`
- `"partial antecedent" discourse anaphora`
- `"anaphora annotation" abstract antecedent span`
- `"discourse deixis" annotation antecedent span`

For gap-2, papers should be ranked substantially higher when annotation guidelines or evaluation metrics are available.

### F7 — TRANSFER: multiple/composite antecedents

- `"multiple antecedents" anaphora discourse`
- `"multi-antecedent" anaphora dialogue`
- `"split antecedent" anaphora resolution`
- `"split antecedents" coreference resolution`
- `"composite discourse referent" anaphora`
- `"composite discourse referent" dialogue`
- `"multiple discourse antecedents" reference resolution`
- `"discontinuous antecedent" reference resolution`
- `"plural antecedent" discourse reference resolution`
- `"propositional anaphora" multiple antecedents`

Entity-only split-antecedent work should remain TRANSFER, not be promoted to direct empirical evidence for multi-proposition reply scope.

### F8 — TRANSFER: uncertainty and abstention

- `"null antecedent" anaphora resolution`
- `"missing antecedent" anaphora resolution`
- `"absent antecedent" reference resolution dialogue`
- `"unresolved reference" dialogue antecedent`
- `"ambiguous antecedent" anaphora resolution confidence`
- `"non-anaphoric" antecedent detection coreference`
- `"antecedent uncertainty" anaphora resolution`
- `"selective prediction" coreference resolution abstention`
- `"abstention" anaphora resolution`
- `"confidence calibration" coreference resolution`
- `"multiple candidate antecedents" dialogue reference resolution`
- `"underspecified" anaphora antecedent annotation`

The important distinction is:

- antecedent exists and is clear;
- antecedent exists but several candidates are plausible;
- antecedent is not in supplied context;
- response does not actually refer back;
- system lacks enough evidence.

These should not be collapsed into one generic failure class.

### F9 — TRANSFER: stance/NLI relative to an explicit proposition

- `"target identification" stance proposition`
- `"target-dependent stance" claim proposition`
- `"stance target" dialogue agreement disagreement`
- `"claim stance" target identification conversation`
- `"entailment" dialogue response proposition target`
- `"contradiction" dialogue response proposition`
- `"natural language inference" dialogue response agreement`
- `"proposition pair" agreement disagreement classification`
- `"support attack" relation claim target dialogue`
- `"argument relation" target identification agreement disagreement`

These queries should not be allowed to dominate discovery. Their role begins after antecedent candidates exist.

### F10 — TRANSFER: reply-to graph and conversation disentanglement

- `"conversation disentanglement" reply-to relation`
- `"reply-to" prediction dialogue chat`
- `"reply-to graph" conversation disentanglement`
- `"response-to" link prediction conversation`
- `"thread disentanglement" enterprise chat reply`
- `"conversation structure" reply relation chat`
- `"asynchronous dialogue" reply-to identification`

This literature should be retained only as structural candidate-narrowing evidence.

## False friends and downgrade rules

Discovery should downgrade or exclude the following literature even when titles or abstracts contain the seed words:

1. Entity-only coreference, pronoun resolution, named-entity coreference, or entity linking without non-nominal/propositional antecedents.

2. Event coreference that only decides whether two event mentions denote the same event.

3. Email threading, quote attribution, conversation disentanglement, or reply-to prediction whose output is only a previous message or turn.

4. Dialogue-act classification that labels a response as agreement, answer, approval, rejection, acknowledgment, request, or clarification without identifying its antecedent.

5. Agreement/disagreement detection evaluated only at utterance level.

6. Stance classification where the target is a fixed politician, brand, topic, hashtag, organization, or dataset-level proposition rather than a candidate antecedent from preceding discourse.

7. NLI, entailment, contradiction, or fact verification where the premise/claim pair is supplied as gold.

8. Standard QA where the target question is explicitly supplied and the system only generates or retrieves an answer.

9. Conversational QA where "multiple questions" means a sequence of questions asked to a system, not several preceding questions competing for one human response.

10. "Unanswerable QA" where the answer is absent from a document rather than an interlocutor leaving a previous conversational question unanswered.

11. Extractive-QA work where "answer scope" means the text span returned by the system.

12. Response selection, next-utterance prediction, Smart Reply, dialogue response generation, or email reply generation.

13. Discourse-relation classification with gold argument pairs when no attachment or antecedent selection is required.

14. Monologic RST/PDTB parsing that provides no transferable mechanism for response attachment or target-span evaluation.

15. Adjacency-pair studies limited to neighboring turns and lacking skipped, partial, multiple, or ambiguous response relations.

16. Email or workplace corpora that provide authentic domain data but only whole-message intent, sentiment, topic, act, or summary labels.

17. Email speech-act classification without links from the act to prior propositions.

18. Security, access-control, governance, regulatory, legal, workflow, or IRB literature retrieved by the phrase "approval scope".

19. Split-antecedent work restricted to constructing plural entity referents from multiple people or objects. This can remain TRANSFER but is not direct evidence for composite propositional scope.

20. Theoretical composite-discourse-referent work without empirical annotation or evaluation. It can motivate representations but cannot close the empirical gaps.

21. Annotation schemes that force exactly one antecedent and cannot encode null, ambiguous, multiple, composite, or discontinuous targets.

22. Evaluation that reports only semantic-relation accuracy but does not score antecedent correctness.

23. Evaluation that scores only the correct source message when that message can contain several independently actionable propositions.

24. Nearest-turn or nearest-message heuristics that automatically attach every response without an explicit unresolved outcome.

25. Calibration literature that cannot produce an abstain/unresolved/null result.

26. Synthetic-only or adversarial-only evidence presented as if it established workplace-email representativeness. Such evidence is useful for engineering evaluation but must remain labeled accordingly.

27. Benchmarks where gold labels are produced by the same heuristic or model under evaluation.

28. Studies that report only aggregate accuracy and make it impossible to distinguish false broad links from missed links.

29. Schemes that collapse "antecedent missing from context" and "antecedent present but ambiguous" into one error category.

30. Any method that interprets an entire preceding message as answered, approved, rejected, or accepted merely because it is the structural parent of the response.

For gap closure, a particularly important admission test is:

`Does the evaluation become stricter if "Yes" is attached to question 1 instead of question 2 in the same preceding message?`

If the answer is no, the paper does not directly evaluate the capability required by gap-3.

Similarly:

`Does the evaluation distinguish approving one clause from approving the whole preceding message?`

If not, it does not directly close gap-1 or gap-2.

## Date policy

**Earliest year discovery must include: 1973.**

The search must not impose a recent-only window that starts in the 2000s or 2010s.

The reason is historical rather than merely bibliographic. The modern study of paired conversational actions and response organization, including adjacency-pair structure, has foundational work in the early 1970s. This foundation matters because later computational terminology for questions, answers, acceptance, rejection, acknowledgment, and response attachment descends from that conceptualization.

The more computationally recognizable proposition/reference branch becomes especially important from the late 1980s onward. Webber's 1988 work on discourse deixis is a key landmark, followed by later work on abstract entities, non-nominal anaphora, computational dialogue structure, agreement/disagreement, email speech acts, discourse parsing, and conversation disentanglement.

Discovery should therefore use at least two chronological strata:

- **1973-1999:** foundational conversation organization, discourse reference, abstract/propositional antecedents, dialogue semantics, and QUD/answerhood foundations.
- **2000-present:** computational corpora, annotation schemes, dialogue discourse parsing, email/enterprise studies, agreement and target detection, non-nominal anaphora systems, multi-party dialogue datasets, and modern uncertainty/calibration methods.

Modern empirical evidence should receive greater weight for engineering applicability, but older foundational work must remain searchable because excluding it would also remove the terminology needed to identify and correctly interpret the later literature.
