# direct empirical studies of proposition-level partial reply scope in workplace email or enterprise dialogue, especially multi-question messages, unanswered subquestions, scoped approval/rejection, and responses linked jointly to multiple antecedent propositions academic terminology analysis

## Product problem

The project is not primarily an entity-coreference problem, a dialogue-act classification problem, or a conventional question-answering problem. Its target output is a semantic link from a current response span to one or more exact antecedent propositions or spans, together with the response relation and the extent of that relation.

The required distinction is approximately:

`response span -> antecedent proposition/span(s) -> answer/agreement/rejection/clarification/condition/reference -> exact/partial/ambiguous/unsupported scope`

The highest-value empirical cases are those in which a preceding workplace message contains several propositions, questions, requests, alternatives, conditions, amounts, dates, or proposed actions and a later short response applies to fewer than all of them. A method that labels the reply as an answer, agreement, acceptance, or approval without establishing its target is insufficient.

The terminology audit indicates that no single established task name cleanly covers the complete capability. Discovery therefore has to combine several literatures. The strongest established vocabulary comes from non-nominal antecedent anaphora, discourse deixis, dialogue discourse attachment, question-answer pair extraction, and agreement-target identification. Workplace-email speech acts, stance, NLI, and adjacency-pair research are useful supporting literatures but should not be mistaken for direct evidence of proposition-level reply scope.

## Seed keyword audit

| Seed | Academic meaning | Fit | Main risk |
| --- | --- | --- | --- |
| discourse deixis | Reference to discourse segments or abstract objects such as propositions, facts, events, states, and situations. | STRONG | Includes metalinguistic and demonstrative-reference phenomena that are not reply scope. |
| discourse-deictic reference | Deictic reference through expressions such as this or that to discourse-evoked abstract referents. | STRONG | Literature is often about demonstratives, not yes/no/approved/agreed responses. |
| abstract anaphora | Anaphora whose antecedent is non-nominal and denotes an abstract object such as a proposition, event, fact, or situation. | STRONG | Most corpora are prose or general dialogue rather than workplace response acts. |
| propositional anaphora | Anaphoric reference to proposition-like content expressed by clauses, sentences, or discourse units. | STRONG | Less standardized terminology than abstract anaphora or non-nominal antecedent anaphora. |
| event anaphora | Reference to a previously evoked event or eventuality. | MODERATE | Event identity is not the same as answer, agreement, rejection, or approval scope. |
| anaphora resolution | Determining the antecedent of an anaphoric expression. | WEAK | Unqualified searches are dominated by nominal and pronominal antecedents. |
| coreference resolution | Linking mentions that denote the same entity. | WEAK | Mainstream coreference is entity-centric and identity-based. |
| coreference to events | Linking mentions of the same event. | MODERATE | Usually evaluates event identity rather than response-to-event/proposition relations. |
| coreference to propositions | Reference or identity involving proposition-denoting content. | STRONG | Relevant work often uses other names, especially abstract anaphora. |
| conversational coreference | Coreference/reference resolution in conversational data. | MODERATE | Often concerns people and objects, not propositions. |
| dialogue reference resolution | Resolving referring expressions using dialogue context and structure. | STRONG | May concern physical, multimodal, or nominal entities. |
| dialogue discourse parsing | Recovering discourse attachments and relation labels between dialogue units. | STRONG | Endpoints are frequently whole EDUs or turns rather than exact proposition spans. |
| conversational discourse relations | Semantic/pragmatic relations connecting conversational discourse units. | STRONG | Relation inventories may be coarse and attachment granularity insufficient. |
| discourse relation recognition | Identification/classification of relations between discourse units. | MODERATE | Many benchmarks provide both arguments and never test antecedent selection. |
| response-to discourse relation | Attachment of a response to an earlier discourse unit, with terminology varying by framework. | STRONG | Search phrase is unstable and can retrieve purely structural reply trees. |
| adjacency pairs | Sequentially paired conversational actions such as question-answer or proposal-accept/reject. | MODERATE | Sequential pairing does not itself solve multi-proposition scope. |
| dialogue act | Functional label such as question, request, answer, accept, reject, or acknowledge. | WEAK | Says what an utterance does, usually not what exact antecedent it applies to. |
| question answer alignment | Matching naturally occurring answers to the questions they answer. | STRONG | Some work assumes a single supplied question and therefore avoids alignment. |
| question resolution | Determining how a conversational question or issue is resolved. | MODERATE | Broad term spanning formal semantics and dialogue management. |
| answer scope | The part of a question or issue resolved by an answer. | STRONG | Conceptually strong but not a stable computational task label. |
| partial answer detection | Determining that an answer resolves only part of a question or issue. | STRONG | Searches may retrieve QA quality/completeness rather than conversational alignment. |
| multi-question answering in dialogue | Handling several questions over a conversational context. | MODERATE | Often means answering a supplied list of questions about a transcript, which is a false friend. |
| agreement detection | Detecting agreement/acceptance/support in interaction. | MODERATE | Detection commonly lacks target identification. |
| disagreement detection | Detecting disagreement/rejection/correction. | MODERATE | Detection commonly lacks proposition-level target identification. |
| agreement target identification | Finding the preceding speaker, utterance, unit, or proposition being agreed with. | STRONG | Some studies stop at the target speaker rather than the target proposition. |
| agreement scope | Determining how much prior content an agreement applies to. | STRONG | Highly relevant but not a standardized high-recall search term. |
| stance with target identification | Jointly detecting stance and what the stance concerns. | MODERATE | Targets are often predefined entities or topics rather than prior propositions. |
| entailment relative to a proposition | Determining whether one statement entails another selected proposition. | MODERATE | Does not perform antecedent selection. |
| contradiction detection | Determining semantic incompatibility between statements. | WEAK | Covers only one relation and normally receives the pair as input. |
| business email | Professional email as a communication genre/domain. | MODERATE | Strongly attracts pedagogy, politeness, genre, marketing, and writing research. |
| email reply | A message responding to another email. | MODERATE | Dominated by threading, reply prediction, reply latency, and response generation. |
| approval scope | Portion of content to which approval applies. | MODERATE | Excellent product wording but weak academic standardization; attracts authorization literature. |
| workplace communication | Organizational communication across email, meetings, and chat. | MODERATE | Domain is relevant but the phrase is far too broad to identify the target capability. |

The most important terminology change is to promote **non-nominal antecedent anaphora**, **abstract anaphora resolution**, **antecedent selection**, **dialogue discourse attachment**, **question-answer pair extraction/matching**, **agreement target identification**, **complex discourse units**, **multiple antecedents**, and **explicit no-antecedent/ambiguous-antecedent cases**.

Generic `coreference resolution`, `dialogue act`, `email reply`, and `multi-question answering` should be used only with restrictive qualifiers.

## Academic task families

### F1 — Non-nominal antecedent and abstract-anaphora resolution — DIRECT

This literature resolves references to clauses, sentences, events, facts, situations, propositions, and other abstract discourse objects. It is the strongest established terminology for the project's non-entity antecedents.

Known seed papers include:

- Robin Lakoff, *Remarks on This and That* (1974).
- Bonnie Lynn Webber, *Structure and Ostension in the Interpretation of Discourse Deixis* (1991).
- Miriam Eckert and Michael Strube, *Dialogue Acts, Synchronizing Units, and Anaphora Resolution* (2000).
- Costanza Navarretta, *Resolving Individual and Abstract Anaphora in Texts and Dialogues* (2004).
- Ana Marasovic et al., *A Mention-Ranking Model for Abstract Anaphora Resolution* (2017).
- Varada Kolhatkar et al., *Anaphora With Non-nominal Antecedents in Computational Linguistics: a Survey* (2018).

This family is directly relevant to exact antecedent spans and to ambiguous, non-nominal, or absent antecedents. Its main limitation is that anaphoric demonstratives are much more common than elliptical response acts such as `yes`, `approved`, or `not that part`.

### F2 — Dialogue discourse attachment and response-relation parsing — DIRECT

This family predicts which earlier conversational discourse unit a current unit attaches to and often predicts the relation type at the same time. That is much closer to msgloom than ordinary dialogue-act classification.

Known seed papers/resources include:

- Asher et al., *Discourse Structure and Dialogue Acts in Multiparty Dialogue: the STAC Corpus* (2016).
- Shi and Huang, *A Deep Sequential Model for Discourse Parsing on Multi-Party Dialogues* (2019).
- Li et al., *Molweni: A Challenge Multiparty Dialogues-based Machine Reading Comprehension Dataset with Discourse Structure* (2020).
- Fan et al., *Improving Dialogue Discourse Parsing via Reply-to Structures of Addressee Recognition* (2023).

The admission test for gap closure is granularity. An EDU-to-EDU discourse edge is useful, but it does not close the product gap if one EDU contains several propositions that receive different response statuses.

### F3 — Question-answer pair extraction and alignment in email or dialogue — DIRECT

This is a high-priority family because it directly asks which naturally occurring question a later answer belongs to.

A particularly important seed is:

- Yang et al., *Characterizing and Supporting Question Answering in Human-to-Human Communication* (2018), which studies question-answer exchange in enterprise email and defines extraction of question-answer pairs from email threads.

Also relevant:

- Jia et al., *Matching Questions and Answers in Dialogues from Online Forums* (2020).

This family should be mined aggressively for annotation guidelines and negative examples. However, one-question/one-answer matching alone does not close gap-3. Discovery must look specifically for messages with multiple questions and for explicit treatment of unanswered or partially answered questions.

### F4 — Partial answers, answer completeness, and multi-question resolution — DIRECT

This is the missing bridge between ordinary QA alignment and the actual product requirement.

The desired empirical task is not:

`question + context -> generate an answer`

It is:

`several naturally occurring prior questions/subquestions + later reply -> determine exactly which are resolved, partially resolved, or still unresolved`

Important neighbouring terminology includes:

- partial answer;
- complete answer;
- answer completeness;
- answerhood;
- question under discussion;
- unresolved question;
- unanswered question;
- multi-part question;
- subquestion.

This family currently needs especially strict discovery because `multi-question QA` is a major false friend.

### F5 — Agreement/disagreement/acceptance/rejection target identification — DIRECT

This family is directly relevant to scoped approval and rejection because it separates **detecting agreement** from **identifying what is agreed with**.

Known seeds include:

- Galley et al., *Identifying Agreement and Disagreement in Conversational Speech: Use of Bayesian Networks to Model Pragmatic Dependencies* (2004).
- Germesin and Wilson, *Agreement Detection in Multiparty Conversation* (2009).

Germesin and Wilson is particularly useful terminologically because agreement annotations include agreement targets and the work explicitly explores identification of who is being agreed with. Nevertheless, speaker-target identification is still weaker than proposition-target identification and should be downgraded accordingly.

### F6 — Multi-antecedent and composite discourse antecedents — DIRECT

This family addresses gap-4.

Promote searches involving:

- multiple antecedents;
- multi-antecedent;
- split antecedents;
- complex antecedent;
- composite antecedent;
- complex discourse unit;
- discourse segment;
- abstract discourse referent.

The key distinction is between:

1. several alternative candidate antecedents because annotation is ambiguous; and
2. a genuinely joint antecedent in which the response semantically targets several propositions together.

Those are not the same phenomenon and discovery should record which one a paper studies.

Webber's discourse-deixis work and SDRT/STAC-style complex discourse structures are useful starting points, but direct empirical evidence for workplace replies jointly targeting several propositions remains the gap to close.

### F7 — Workplace email speech acts and utterance-level action annotation — TRANSFER

This is useful primarily because it provides authentic workplace-domain propositions and speech acts.

Known seeds include:

- Cohen, Carvalho, and Mitchell, *Learning to Classify Email into “Speech Acts”* (2004).
- Carvalho and Cohen, *Improving “Email Speech Acts” Analysis via N-gram Selection* (2006).
- Lampert, Dale, and Paris, *The Nature of Requests and Commitments in Email Messages* (2008).

The Lampert/Dale/Paris line is particularly useful for utterance-level requests and commitments in Enron email. However, classifying an utterance as a request or commitment does not establish the proposition targeted by a later response. This family therefore remains TRANSFER evidence for Topic 04.

### F8 — Targeted stance and claim-target extraction — TRANSFER

Stance literature is useful only when the target is explicitly identified.

Potentially reusable ideas include:

- joint extraction of stance expression and target;
- span-level target evaluation;
- one stance expression applying to several targets;
- separating stance polarity from target selection.

Fixed-topic stance detection is not useful direct evidence.

### F9 — Proposition-pair entailment and contradiction — TRANSFER

NLI and textual entailment can help after a candidate antecedent is selected.

For example, they may provide features for determining whether a response:

- confirms a proposition;
- contradicts it;
- leaves it neutral;
- supplies a condition.

They cannot by themselves decide which of six preceding propositions was targeted, so they must never be promoted to DIRECT evidence for reply-scope correctness.

### F10 — Antecedent selection with ambiguity, no-link, and abstention — TRANSFER

This family supports engineering gaps 2 and 5.

Search for annotation/evaluation that permits:

- an explicit no-antecedent outcome;
- multiple plausible antecedents;
- ambiguous antecedents;
- non-linguistic antecedents;
- missing-context cases;
- unresolved references;
- antecedent ranking rather than forced single classification.

No existing paper should be assumed to validate the complete msgloom contract. The literature can supply design precedents, while threshold selection, asymmetric error costs, and the exact label set remain engineering-validation work.

### F11 — Adjacency pairs and conversational sequence analysis — TRANSFER

Adjacency-pair theory is foundational for question-answer, request-response, proposal-acceptance/rejection, and similar response structures.

Its value to msgloom is conceptual: an earlier action creates an expected type of response, and absence of the expected second part can itself be meaningful.

Its limitation is equally important: adjacency is not proposition-level scope. One email turn may contain five first-pair parts, and a single later reply may satisfy only two of them.

## Query families

### F1 — DIRECT — non-nominal antecedents

- `"non-nominal antecedent" anaphora resolution dialogue proposition`
- `"non-nominal antecedent anaphora" dialogue`
- `"abstract anaphora" dialogue antecedent resolution proposition`
- `"abstract anaphora" conversation antecedent span`
- `"discourse deixis" dialogue antecedent proposition`
- `"discourse-deictic" dialogue antecedent resolution`
- `"propositional anaphora" dialogue antecedent`
- `"sentential antecedent" dialogue anaphora`
- `"clausal antecedent" dialogue anaphora`
- `"abstract anaphora" email`

### F2 — DIRECT — dialogue attachment and response relations

- `"dialogue discourse parsing" response relation antecedent`
- `"dialogue discourse parsing" question answer acknowledgment correction`
- `"multiparty dialogue discourse parsing" attachment relation`
- `"discourse attachment" dialogue response antecedent`
- `"reply-to structure" dialogue discourse relation`
- `"response relation" dialogue discourse attachment`
- `"conversational discourse relations" response antecedent`
- `"discourse dependency" dialogue question answer relation`
- `"complex discourse unit" dialogue response`
- `SDRT dialogue response relation antecedent`

### F3 — DIRECT — naturally occurring question-answer alignment

- `"question answer pairs" enterprise email`
- `"question answer pair" workplace email thread`
- `"question answer alignment" email thread`
- `"question answer matching" email conversation`
- `"question answer extraction" enterprise email`
- `"question answer pairs" threaded email conversations`
- `"matching questions and answers" dialogue conversation`
- `"QA matching" dialogue antecedent question`
- `"answer selection" dialogue previous question`
- `"question-answer relation" workplace email`

### F4 — DIRECT — partial answers and multiple questions

- `"partial answer" dialogue question`
- `"partial answers" conversation question`
- `"answer completeness" dialogue question`
- `"incomplete answer" dialogue question`
- `"unanswered question" dialogue discourse`
- `"unanswered questions" email thread`
- `"unanswered subquestion" dialogue`
- `"multiple questions" dialogue answer alignment`
- `"multiple questions" email answer`
- `"multi-part question" dialogue answer`
- `"multi-question" conversation answer alignment -"questions about a transcript"`
- `"question resolution" dialogue unanswered`
- `"question under discussion" partial answer dialogue`
- `"answerhood" partial answer conversation`

This is the most important query family for gap-3. Results must be manually screened to reject modern `multi-question QA` papers where a benchmark simply gives the model several explicit questions.

### F5 — DIRECT — agreement/rejection targets

- `"agreement target" dialogue`
- `"agreement target identification" conversation`
- `"agreement detection" target utterance conversation`
- `"agreement detection" addressee target dialogue`
- `"disagreement target" dialogue`
- `"agreement disagreement" adjacency pair target`
- `"agreement" "target utterance" multiparty conversation`
- `"acceptance" "target" dialogue proposition`
- `"rejection" "target" dialogue proposition`
- `"acceptance rejection" discourse relation dialogue`
- `"agreement scope" conversation`
- `"partial agreement" dialogue target`

### F6 — DIRECT — multiple/composite antecedents

- `"multiple antecedents" discourse anaphora proposition`
- `"multi-antecedent" discourse reference dialogue`
- `"split antecedent" abstract anaphora`
- `"split antecedents" discourse reference proposition`
- `"complex antecedent" abstract anaphora`
- `"composite antecedent" discourse anaphora`
- `"complex discourse unit" antecedent response dialogue`
- `"complex discourse unit" question answer dialogue`
- `"discourse segment" demonstrative "one or more clauses"`
- `"multiple discourse units" response relation dialogue`

### F7 — TRANSFER — workplace email speech acts

- `"email speech acts" Enron request commitment`
- `"requests and commitments" email messages annotation`
- `"utterance level" workplace email request commitment`
- `"business email" acceptance rejection corpus`
- `"workplace email" agreement disagreement corpus`
- `"enterprise email" speech act annotation`
- `"workplace email" proposal acceptance rejection`
- `"email" request commitment response annotation`

### F8 — TRANSFER — stance targets

- `"stance target identification" claim span`
- `"targeted stance" proposition target extraction`
- `"stance target extraction" argument claim`
- `"stance" "target span" conversation`
- `"claim target" agreement disagreement dialogue`
- `"target-specific stance" conversation claim`

### F9 — TRANSFER — proposition-pair semantic relations

- `"textual entailment" dialogue response proposition`
- `"natural language inference" dialogue agreement disagreement`
- `"contradiction" dialogue response proposition`
- `"entailment" "target proposition" dialogue`
- `"semantic relation" response antecedent proposition`
- `"NLI" conversation agreement disagreement target`

### F10 — TRANSFER — uncertainty and no-link

- `"abstract anaphora" "no antecedent"`
- `"abstract anaphora" ambiguous antecedent annotation`
- `"non-nominal antecedent" ambiguous multiple antecedents`
- `"anaphora resolution" "no identifiable antecedent" dialogue`
- `"discourse attachment" "no link" dialogue`
- `"dialogue discourse parsing" no-link antecedent`
- `"antecedent selection" abstention anaphora`
- `"antecedent selection" multiple candidates discourse`
- `"anaphora" unresolved antecedent annotation guidelines`
- `"discourse deixis" ambiguous antecedent corpus`

### F11 — TRANSFER — conversational sequence organization

- `"adjacency pairs" question answer conversation`
- `"adjacency pair" proposal acceptance rejection`
- `"adjacency pair" request compliance refusal`
- `"conditional relevance" unanswered question conversation`
- `"sequence organization" question answer acceptance rejection`
- `"adjacency pair identification" dialogue computational`

## False friends and downgrade rules

Discovery should not return a paper as capability-matching merely because its title contains `reply`, `answer`, `agreement`, `coreference`, or `scope`.

Downgrade or exclude the following:

1. Entity-only coreference, pronoun resolution, named-entity coreference, or speaker coreference with no non-nominal antecedents.
2. Event-coreference clustering that tests event identity but not response relations.
3. Dialogue-act classification without antecedent links.
4. Agreement/disagreement classification without target identification.
5. Agreement-target systems that identify only the target speaker and never the target utterance/proposition.
6. Whole-message email speech-act or intent classification when messages can contain several independently answerable propositions.
7. Generic QA or reading comprehension where the question is supplied as gold.
8. Multi-question QA in which a model is simply given a list of explicit questions about a document or transcript.
9. Answer-quality or answer-correctness evaluation with no question-to-reply alignment.
10. Smart Reply, response generation, next-utterance generation, or response ranking without antecedent-scope evaluation.
11. Email threading, In-Reply-To reconstruction, reply trees, reply-likelihood prediction, reply latency, or reply-length prediction.
12. Addressee recognition where only the recipient/person is predicted.
13. PDTB-style or other discourse-relation classification where both relation endpoints are supplied and attachment is not predicted; such work may remain TRANSFER.
14. Monologic rhetorical parsing unless it contributes explicit mechanisms for multiple, non-adjacent, complex, ambiguous, or no-link antecedents.
15. Fixed-topic stance or sentiment analysis.
16. NLI or contradiction classification where the proposition pair is supplied.
17. Grammatical agreement literature.
18. Access-control, legal, governance, regulatory, procurement, or workflow literature retrieved by `approval scope`.
19. Business-email pedagogy, politeness, genre, marketing, spam/phishing, or writing-quality research with no reply-target annotation.
20. Qualitative adjacency-pair work as direct computational validation. It is foundational terminology, not a substitute for proposition-level empirical evaluation.
21. Datasets that require exactly one antecedent per response without checking whether multiple or composite antecedents naturally occur.
22. Annotation schemes that silently collapse ambiguous antecedents to a single answer.
23. Systems that force an antecedent when the true antecedent may be missing from the available context.
24. Message-level or turn-level evaluation when the research question requires clause-, proposition-, EDU-, or span-level distinctions.
25. Synthetic-only dialogue as evidence of workplace-email accuracy. It may support an engineering experiment but not production-domain representativeness.
26. Forum, game-chat, social-media, or casual-dialogue studies should be marked TRANSFER for workplace-domain claims unless they evaluate a domain-independent mechanism.
27. Enterprise-email QA-pair extraction should remain DIRECT but must not be treated as closing gap-3 unless it explicitly evaluates multiple questions, unanswered questions, partial answers, or one answer associated with several questions.
28. Approval, acceptance, rejection, or agreement studies that automatically treat the whole immediately preceding turn as the target must not be treated as evidence of proposition-level scope.
29. Work on attachment/table/page/cell/visual grounding belongs primarily to Topic 08 unless it also evaluates the semantic proposition targeted by a response.
30. High benchmark accuracy does not compensate for an annotation contract that cannot represent partial, ambiguous, unsupported, discontinuous, multiple-antecedent, or no-link cases.

For gap closure, classify each accepted paper with at least these evidence labels:

- authentic workplace/enterprise communication vs transfer domain;
- antecedent selection evaluated vs endpoint supplied;
- message/turn vs EDU/clause/proposition/span granularity;
- one antecedent only vs multiple antecedents allowed;
- ambiguity preserved vs forced decision;
- explicit no-link/unresolved outcome vs forced link;
- multiple prior questions/actions represented vs single-question setting;
- unanswered subquestions explicitly evaluated vs not evaluated;
- partial answer/agreement/rejection represented vs whole-target only.

## Date policy

**Earliest publication year to include: 1974.**

The search window must not begin in 2000, 2010, or another recent benchmark era.

The relevant conceptual foundations predate modern computational NLP. Work from 1974 already supplies two vocabulary streams that later become central:

- demonstrative/discourse-reference work associated with the lineage leading to `discourse deixis`; and
- conversation-analysis work on sequential organization and adjacency-pair-like response structures.

Computational discourse-deixis and abstract-anaphora work becomes especially important in the late 1980s and 1990s, followed by dialogue anaphora and agreement/disagreement modeling in the 2000s, dialogue discourse parsing in the 2010s, and enterprise-email question-answer extraction in the late 2010s.

Accordingly, discovery should use **1974 as the hard earliest year**, while operationally prioritizing post-1990 computational and empirical work after the foundational pass. This preserves the terminology lineage without allowing historical theory to dominate the corpus.

A recent-only window would be methodologically unsafe because it would hide the terminology under which later work inherited the problem, especially `discourse deixis`, `non-nominal antecedents`, adjacency-pair relations, and proposition/event/fact reference.
