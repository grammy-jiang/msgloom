# Reference resolution to propositions and the semantic scope of replies in work communication academic terminology analysis

## Product problem

The core academic problem is **not ordinary entity coreference**. It is the joint problem of deciding:

1. what prior discourse content a response or referring expression targets;
2. whether that antecedent is an event, fact, proposition, situation, question, proposal, condition, or larger discourse unit;
3. what semantic relation the response bears to that antecedent, such as answer, acknowledgement, agreement, correction, rejection, clarification, or condition;
4. how much of the antecedent is actually covered; and
5. whether the evidence supports an exact target, multiple targets, an ambiguous set of candidates, or no supported antecedent.

The strongest established terminology for the reference component is **non-nominal-antecedent anaphora**, **abstract anaphora**, and **discourse deixis**. The 2018 Computational Linguistics survey explicitly treats non-nominal-antecedent anaphora as also known as abstract anaphora or discourse deixis and describes antecedents representing events, facts, and propositions. citeturn244391search0

For dialogue, the closest modern benchmark line is **discourse deixis resolution in dialogue**. CODI-CRAC separates discourse deixis from identity coreference and bridging rather than treating all three as one entity-coreference problem. citeturn244391search8turn244391search10turn244391search9

For reply scope, a second literature is needed: **dialogue discourse attachment and discourse relations**. STAC represents dialogue as links among discourse units and includes relations such as Question-Answer Pair, Acknowledgement, Correction, Clarification Question, Conditional, Contrast, and others. Importantly for msgloom, STAC's Question-Answer Pair relation includes partial or indirect answers, and replies may attach to complex discourse units rather than merely to the immediately preceding turn. citeturn259084search1turn620098search14turn620098search16

A third necessary branch is **question semantics and answerhood**, especially **partial answerhood** and **Questions Under Discussion (QUD)**. This literature supplies a more precise semantic vocabulary than the product phrase "answer scope": a proposition may provide a complete answer, a partial answer, an indirect answer, or fail to answer the question under discussion. Foundational treatments of partial answers predate modern NLP by decades. citeturn483419search0turn483419search4

A fourth branch covers **agreement, disagreement, acknowledgement, correction, and public commitments**. Lascarides and Asher explicitly model agreement and disputes in terms of agents' public commitments and discuss what content is agreed upon even when dispute is present. This is materially closer to "approved, but not that condition" than generic sentiment or stance classification. citeturn259084search6turn259084search11

The research programme should therefore avoid looking for one literature called "response scope". The capability is distributed across several established task families.

## Seed keyword audit

| Seed | Academic meaning | Fit | Main risk | False-positive literature |
| --- | --- | --- | --- | --- |
| discourse deixis | Reference from expressions such as *this* or *that* to a discourse segment or abstract discourse object rather than an ordinary nominal entity. Webber's 1988 paper is a foundational computational treatment. citeturn259084search9 | STRONG | A discourse segment is not automatically the exact proposition span msgloom needs. | Spatial/temporal deixis, demonstratives to physical objects, purely theoretical deixis. |
| discourse-deictic reference | Reference relation between a discourse-deictic expression and prior discourse content. | STRONG | Less consistently indexed than "discourse deixis" or "non-nominal antecedent anaphora". | General deixis and physical-context demonstratives. |
| abstract anaphora | Anaphora to abstract objects such as events, facts, propositions, or situations, often through non-nominal antecedents. citeturn244391search0 | STRONG | Some studies assume the anaphor or candidate antecedents are already known. | Pure abstract-object semantics, nominal anaphora, shell-noun description without resolution. |
| propositional anaphora | Anaphoric reference specifically to proposition-like prior content. | MODERATE | Less standardized as a search label than abstract anaphora; low-recall if used alone. | Propositional attitudes, logic, ellipsis, proposition identity. |
| event anaphora | Anaphoric reference to a prior event or eventuality. | MODERATE | Easily collapses into event coreference rather than response-to-event reference. | Event extraction, temporal relations, event clustering. |
| anaphora resolution | General antecedent resolution for anaphoric expressions. | MODERATE | Mainstream results are dominated by entity and pronoun anaphora. | Pronoun resolution, nominal anaphora, zero anaphora, one-anaphora. |
| coreference resolution | Linking or clustering mentions referring to the same entity. | WEAK | Entity identity is a different problem from a response applying to a proposition. | Named-entity and pronoun coreference, entity clustering. |
| coreference to events | Determining whether event mentions denote the same event. This is an established task. citeturn405765search6turn405765search1 | MODERATE | Event identity does not locate what an acknowledgement, approval, or rejection refers to. | Within/cross-document event clustering and news-event matching. |
| coreference to propositions | Descriptive wording for proposition-level reference, but not a dominant standardized task name. | WEAK | Literal searches have poor recall and drift toward formal semantics. | Logic, proposition equivalence, philosophical identity. |
| conversational coreference | Coreference/anaphora in conversational data. | MODERATE | Often still ordinary entity coreference with dialogue features. | Speaker-aware entity and pronoun coreference. |
| dialogue reference resolution | Umbrella term for reference resolution in dialogue. | MODERATE | Includes entities, visual objects, task-state objects, and bridging, not specifically propositions. | Visual reference, task-oriented entity grounding. |
| dialogue discourse parsing | Predict discourse attachment links between dialogue units and usually their relation types. | STRONG | Benchmarks commonly stop at EDU/utterance level rather than exact proposition spans. | Gold-link relation classification or coarse whole-turn parsing. |
| conversational discourse relations | Relations such as QAP, acknowledgement, correction, clarification, elaboration, and contrast between conversational contributions. STAC is a strong canonical source. citeturn259084search1turn620098search14 | STRONG | Relation recognition is insufficient if the target link is already supplied. | Gold-pair relation classification and generic monologic discourse relations. |
| discourse relation recognition | Identification/classification of rhetorical relations between discourse units. | MODERATE | Much RST/PDTB work is monologic and assumes arguments rather than finding the response target. | PDTB relation labels, RST labels, adjacent-pair implicit relation classification. |
| response-to discourse relation | Descriptive label for a response linked semantically or structurally to an earlier contribution; neighboring literature uses reply-to, discourse attachment, QAP, acknowledgement, correction, etc. | MODERATE | The exact expression is not a stable task name. | Metadata reply graphs, response prediction, response generation. |
| adjacency pairs | Paired conversational actions such as question-answer, offer-acceptance, request-response. | MODERATE | Sequential pairing alone does not resolve exact semantic scope. | Conversation-analysis sequencing, turn-taking, ASR language modeling. |
| dialogue act | Communicative-function classification such as question, answer, request, agreement, acknowledgement. | MODERATE | Usually says what the utterance does, not what prior proposition it targets. | Intent classification and Topic 05 speech-act extraction. |
| question answer alignment | Pairing answers with questions; related terminology includes QAP, answer selection, response selection, and discourse attachment. | MODERATE | QA search often assumes the question is supplied. | FAQ retrieval, answer selection, pre-aligned QA. |
| question resolution | In semantic dialogue theory, providing information that settles or partly settles a question; the phrase is otherwise highly ambiguous. | MODERATE | Can retrieve generic QA, clarification, or query reformulation. | Question generation, ambiguity resolution, open-domain QA. |
| answer scope | Product term for which part of a question or set of questions an answer addresses. | WEAK | Not a stable NLP task name; "answer span" dominates search. | Extractive QA answer-span detection and syntactic scope. |
| partial answer detection | Determining that a response resolves only part of the information requested. Formal partial-answer semantics is well established, though standalone computational detection is less standardized. citeturn483419search0 | MODERATE | Search can conflate semantic partiality with partially correct answers. | Student-answer grading, partial credit, truncated answers. |
| multi-question answering in dialogue | Processing multiple questions within a dialogue or one context. | WEAK | Most work answers several supplied questions rather than maps one observed reply to the subset it addresses. | Batch QA, multi-question VQA, conversational QA. |
| agreement detection | Detecting agreement expressed by a response. | MODERATE | The target is often implicit or already supplied. | Message-level polarity, sentiment, fixed-topic stance. |
| disagreement detection | Detecting disagreement, dispute, correction, or opposition. | MODERATE | May not identify which proposition is rejected. | Sentiment, toxicity, generic contradiction classification. |
| agreement target identification | Identifying what prior content agreement applies to. | STRONG | Exact wording is not standard; relevant work may be indexed as discourse attachment, target-specific stance, acknowledgement, or public commitments. | Stance toward named entities/topics and agreement classification with a gold target. |
| agreement scope | Determining the semantic content covered by agreement, including partial agreement. | MODERATE | Excellent conceptual fit but weak lexical standardization. | Contract scope, inter-annotator agreement, organizational consensus. |
| stance with target identification | Finding a target and classifying a stance toward it. | MODERATE | Targets are typically entities, claims, topics, or authors rather than exact antecedent propositions. | Political stance, aspect sentiment, fixed-target stance. |
| entailment relative to a proposition | NLI/textual entailment between a response and a supplied proposition. | MODERATE | It assumes the candidate proposition has already been found. | Generic NLI, textual similarity, claim verification. |
| contradiction detection | Detecting semantic incompatibility between supplied propositions. | MODERATE | Does not perform antecedent selection or span localization. | Generic NLI, fact checking, summarization inconsistency. |
| business email | Target-domain descriptor. | WEAK | Not a task name; highly noisy alone. | Spam, summarization, writing assistance, email classification. |
| email reply | Structural/domain cue for asynchronous response messages. | MODERATE | Dominated by threading, quote handling, reply prediction and generation. | Thread reconstruction, quote attribution, reply generation. |
| approval scope | Product term for what an approval applies to. | WEAK | Academically sparse wording; "approval" is heavily overloaded. | Workflow permissions, regulatory/legal approvals, access control. |
| workplace communication | Broad target-domain descriptor. | WEAK | Far too broad without a strong semantic task term. | Organizational behavior, workplace sentiment, meetings, productivity. |

## Academic task families

### F1 — Non-nominal antecedent anaphora and discourse deixis — DIRECT

This is the highest-priority family.

The canonical phenomenon is an anaphor whose antecedent is syntactically non-nominal and denotes or evokes an event, fact, proposition, situation, or larger discourse segment. Kolhatkar et al.'s survey explicitly groups **non-nominal-antecedent anaphora**, **abstract anaphora**, and **discourse deixis** and documents the terminological fragmentation of this literature. citeturn244391search0

Known seeds:

- Bonnie Lynn Webber, **Discourse Deixis: Reference to Discourse Segments** (1988). citeturn259084search9
- Nicholas Asher, **Reference to Abstract Objects in Discourse** (1993), including events, propositions, states, facts, and a theory of abstract-entity anaphora. citeturn259084search0turn259084search4
- Ana Marasović et al., **A Mention-Ranking Model for Abstract Anaphora Resolution** (2017), explicitly selecting typically non-nominal antecedents. citeturn405765search5
- Varada Kolhatkar et al., **Anaphora With Non-nominal Antecedents in Computational Linguistics: a Survey** (2018). citeturn244391search0

For msgloom, prioritize papers that output antecedent spans rather than merely an abstract semantic type. Also look for **anaphoricity detection**, **no antecedent**, or equivalent mechanisms, because unsupported references must be allowed to remain unresolved.

### F2 — Discourse deixis and anaphora resolution in dialogue — DIRECT

The CODI-CRAC shared tasks make this a concrete modern computational family. They distinguish identity coreference, bridging, and discourse deixis and apply them to multiple dialogue genres. citeturn244391search10turn244391search9

Known seeds:

- Khosla et al., **The CODI-CRAC 2021 Shared Task on Anaphora, Bridging, and Discourse Deixis in Dialogue**. citeturn244391search10
- Li, Kobayashi, and Ng, **The CODI-CRAC 2021 Shared Task on Anaphora, Bridging, and Discourse Deixis Resolution in Dialogue: A Cross-Team Analysis**. citeturn244391search8
- Yu et al., **The CODI-CRAC 2022 Shared Task on Anaphora, Bridging, and Discourse Deixis in Dialogue**. citeturn244391search9
- Li, Kobayashi, and Ng, **Neural Anaphora Resolution in Dialogue Revisited**. citeturn244391search4

This family should be separated from ordinary conversational entity coreference during admission.

### F3 — Dialogue discourse attachment and relation parsing — DIRECT

Dialogue discourse parsing predicts both **where a discourse unit attaches** and **what relation holds**. This is especially important because msgloom needs:

`response → antecedent → relation`

rather than only `response → label`.

STAC contains full discourse structures for multiparty dialogue and relations that are directly useful here, including Question-Answer Pair, Acknowledgement, Correction, Clarification Question, Conditional, Contrast, and related relations. citeturn259084search1turn620098search14

The STAC annotation material also demonstrates attachment to **complex discourse units**, which is highly relevant to a reply targeting a multi-proposition proposal rather than a single sentence. citeturn620098search16

Known seeds:

- Asher et al., **Discourse Structure and Dialogue Acts in Multiparty Dialogue: the STAC Corpus** (2016). citeturn259084search1
- Li et al., **Molweni: A Challenge Multiparty Dialogues-based Machine Reading Comprehension Dataset with Discourse Structure** (2020). Molweni includes discourse-dependency annotations over multiparty dialogue. citeturn259084search8
- Fan et al., **Improving Dialogue Discourse Parsing via Reply-to Structures of Addressee Recognition** (2023), which explicitly relates reply-to structure to dialogue discourse structure. citeturn852799search0

For admission, separate:

- **link prediction + relation classification** — high relevance;
- **link prediction only** — useful structural evidence;
- **relation classification with gold links** — secondary;
- **relation classification over supplied adjacent pairs** — weak transfer evidence.

### F4 — Question-answer relations, QUD, and partial answerhood — DIRECT

"Answer scope" should not be the primary academic search term. The stronger terminology is:

- **answerhood**;
- **partial answer** / **partial answerhood**;
- **complete answer**;
- **indirect answer**;
- **Questions Under Discussion (QUD)**;
- **Question-Answer Pair (QAP)**.

Formal question semantics explicitly distinguishes complete from partial answers. citeturn483419search0

The QUD tradition models discourse as organized around questions being addressed; utterances are interpreted relative to the current question under discussion. citeturn483419search4turn483419search9

STAC provides the computational-dialogue bridge: its QAP relation covers answers, including partial or indirect answers. citeturn620098search14

This family is directly relevant to:

- several questions in one prior message;
- one short reply addressing only one question;
- a reply narrowing the answer space without closing the question;
- indirect answers;
- clarification questions instead of answers;
- an answer that leaves other questions outstanding.

### F5 — Agreement, disagreement, acknowledgement, correction, and public commitments — DIRECT

Generic "agreement detection" is too weak. The stronger semantic literature models **what is publicly committed to** and how agreement or dispute affects that content.

Lascarides and Asher's work defines agreement in terms of shared entailments of agents' public commitments and explicitly addresses what content remains agreed upon in the presence of dispute. citeturn259084search6turn259084search10

Known seeds:

- Lascarides and Asher, **Agreement and Disputes in Dialogue** (2008). citeturn259084search11
- Lascarides and Asher, **Agreement, Disputes and Commitments in Dialogue** (2009). citeturn259084search6
- Rosenthal and McKeown, **I Couldn't Agree More: The Role of Conversational Structure in Agreement and Disagreement Detection in Online Discussions** (2015). citeturn852799search6

For msgloom, prioritize work that distinguishes the **target content** from the **agreement/disagreement label**.

### F6 — Event reference and event coreference — TRANSFER

Event coreference is real and mature enough to provide mechanisms for event representations, candidate scoring, anaphoricity, mention ranking, and contextual argument comparison. An early computational paper on event coreference appeared in 1997. citeturn405765search6

Later event-coreference systems cluster mentions of the same event within or across documents. citeturn405765search1turn405765search0

This is **TRANSFER**, because:

`event mention A ↔ event mention B denote the same event`

is not equivalent to:

`"yes, that happened" → prior event proposition`.

Use event-coreference literature for mechanisms, not as evidence that response scope has been solved.

### F7 — Target-specific stance, entailment, and contradiction — TRANSFER

These methods can help classify a relation once a candidate proposition has been identified.

Potential transferred capabilities include:

- target-conditioned representation;
- support versus oppose;
- entailment versus contradiction;
- pairwise proposition scoring;
- hard-negative selection;
- calibrated pair scoring.

But whole-message NLI is explicitly insufficient for msgloom if it cannot identify the proposition affected.

### F8 — Multiple- and split-antecedent reference — TRANSFER

msgloom permits one response to resolve more than one antecedent span. Standard split-antecedent research is mostly entity-oriented, but its output structures and evaluation can inform multi-span reference handling.

Yu et al.'s **Stay Together: A System for Single and Split-antecedent Anaphora Resolution** is a known computational example. citeturn405765search10

This family should remain TRANSFER unless a paper actually handles proposition- or discourse-level multi-antecedent reference.

### F9 — Workplace and asynchronous message response grounding — DIRECT

This is the domain-specific search layer.

Search email, enterprise chat, and asynchronous communication only in conjunction with the strong task terminology above.

A paper is DIRECT target-domain evidence only if it actually evaluates one of:

- non-nominal antecedent resolution;
- reply attachment to prior discourse content;
- question-answer attachment;
- partial response/answer scope;
- agreement/rejection target;
- approval/acknowledgement scope.

An email summarizer or threading system is not direct evidence merely because its dataset is email.

## Query families

### F1 — DIRECT — Non-nominal antecedent anaphora

- `"non-nominal antecedent" anaphora resolution`
- `"non-nominal-antecedent anaphora" resolution`
- `"abstract anaphora" antecedent resolution`
- `"abstract anaphora resolution" antecedent span`
- `"discourse deixis" antecedent resolution`
- `"discourse-deictic" reference antecedent`
- `"abstract object anaphora" proposition event fact`
- `"propositional anaphora" antecedent resolution`
- `"discourse deixis" anaphoricity detection`
- `"abstract anaphora" anaphoricity antecedent`
- `"discourse deixis" unresolved antecedent`
- `"shell noun" antecedent resolution proposition`

### F2 — DIRECT — Dialogue discourse deixis

- `"discourse deixis" dialogue resolution`
- `"discourse deixis resolution" dialogue`
- `"abstract anaphora" dialogue`
- `"abstract anaphora resolution" conversation`
- `"non-nominal antecedent" dialogue`
- `"anaphora resolution" dialogue "discourse deixis"`
- `"discourse-deictic" dialogue antecedent`
- `"discourse deixis" conversation antecedent span`
- `"CODI-CRAC" discourse deixis dialogue`
- `"dialogue reference resolution" "discourse deixis"`

### F3 — DIRECT — Dialogue discourse attachment and relations

- `"dialogue discourse parsing" attachment relation`
- `"dialogue discourse parsing" "question-answer pair"`
- `"dialogue discourse parsing" acknowledgement correction`
- `"reply-to" dialogue discourse parsing`
- `"reply-to structure" dialogue discourse`
- `"discourse dependency parsing" dialogue response`
- `"discourse attachment" dialogue response`
- `"response relation" dialogue discourse attachment`
- `"question-answer pair" discourse relation dialogue`
- `"complex discourse unit" dialogue response`
- `"complex discourse unit" "question-answer" dialogue`
- `STAC dialogue question-answer acknowledgement correction`
- `Molweni dialogue discourse dependency relation`

### F4 — DIRECT — Questions, answers, and partial scope

- `"partial answer" question semantics`
- `"partial answer" dialogue`
- `"partial answerhood" question`
- `"answerhood" dialogue question`
- `"complete answer" "partial answer" dialogue`
- `"Questions Under Discussion" dialogue answer`
- `"question under discussion" response answer`
- `"question-answer pair" partial indirect answer dialogue`
- `"question resolution" dialogue answerhood`
- `"multiple questions" reply dialogue alignment`
- `"multiple questions" "partial answer" dialogue`
- `"answer completeness" dialogue question`
- `"which question" response dialogue`
- `"question-answer" discourse attachment multiple questions`

### F5 — DIRECT — Agreement and commitment scope

- `"agreement" "public commitments" dialogue`
- `"agreement" disputes commitments dialogue`
- `"partial agreement" dialogue`
- `"agreement scope" dialogue`
- `"implicit agreement" dialogue commitments`
- `"agreement detection" conversational structure`
- `"disagreement detection" conversational structure`
- `"agreement target" dialogue`
- `"agreement target identification" conversation`
- `"acknowledgement" dialogue discourse relation target`
- `"correction" dialogue discourse relation target`
- `"rejection" dialogue discourse relation antecedent`
- `"relational speech acts" agreement dialogue`
- `"public commitment" dialogue acknowledgement correction`

### F6 — TRANSFER — Event reference/coreference

- `"event anaphora" resolution`
- `"event reference" anaphora discourse`
- `"event coreference resolution" antecedent`
- `"event coreference" anaphoricity`
- `"event coreference" mention ranking`
- `"event coreference" discourse structure`
- `"event coreference" dialogue`
- `"event anaphora" dialogue`

### F7 — TRANSFER — Target-specific stance and NLI

- `"target-specific stance" proposition`
- `"stance target identification" span`
- `"target identification" stance dialogue`
- `"agreement disagreement" target identification dialogue`
- `"natural language inference" dialogue response proposition`
- `"entailment" response proposition dialogue`
- `"contradiction" response proposition dialogue`
- `"entailment contradiction" dialogue discourse relation`
- `"claim target" stance response span`

### F8 — TRANSFER — Multiple antecedents

- `"split-antecedent anaphora" resolution`
- `"multiple antecedents" anaphora resolution`
- `"multi-antecedent" anaphora`
- `"split antecedent" dialogue anaphora`
- `"multiple antecedent spans" reference resolution`
- `"discourse deixis" multiple antecedents`
- `"abstract anaphora" multiple antecedents`

### F9 — DIRECT — Workplace/asynchronous communication

- `"business email" "discourse deixis"`
- `"business email" "abstract anaphora"`
- `"business email" anaphora resolution proposition`
- `"email reply" discourse relation question answer`
- `"email reply" discourse attachment`
- `"email reply" agreement disagreement target`
- `"email" "partial answer" reply`
- `"email" "question-answer pair" discourse`
- `"email" approval agreement scope`
- `"workplace communication" reference resolution proposition`
- `"workplace communication" discourse attachment reply`
- `"enterprise chat" dialogue discourse parsing`
- `"enterprise chat" agreement target`
- `"asynchronous conversation" discourse parsing reply`
- `"asynchronous dialogue" question answer attachment`

## Promoted terminology

Discovery should preferentially use these terms rather than the brief's weaker descriptive phrases:

- **non-nominal antecedent anaphora**
- **non-nominal-antecedent anaphora**
- **discourse deixis resolution**
- **abstract anaphora resolution**
- **abstract object anaphora**
- **discourse-deictic anaphora**
- **anaphoricity detection**
- **dialogue discourse attachment**
- **dialogue discourse parsing**
- **discourse dependency parsing**
- **reply-to structure**
- **Question-Answer Pair / QAP discourse relation**
- **Acknowledgement relation**
- **Correction relation**
- **complex discourse unit / CDU**
- **Questions Under Discussion / QUD**
- **answerhood**
- **partial answerhood**
- **complete versus partial answer**
- **indirect answer**
- **public commitments**
- **relational speech acts**
- **partial agreement**
- **response target identification**
- **multi-antecedent resolution**
- **asynchronous dialogue / asynchronous conversation**

The phrase **complex discourse unit** deserves particular attention because whole-message or whole-turn antecedents are often too coarse for the product. STAC explicitly allows replies to relate to complex units assembled from multiple discourse units. citeturn620098search16

## Demoted terminology

Do not use these as primary standalone discovery terms:

- `coreference resolution`
- `coreference to propositions`
- generic `anaphora resolution`
- unconstrained `event anaphora`
- `dialogue act`
- `question answer alignment`
- unconstrained `question resolution`
- `answer scope`
- `multi-question answering in dialogue`
- `contradiction detection`
- `business email`
- bare `email reply`
- `approval scope`
- `workplace communication`

They remain useful only when conjoined with stronger promoted terminology.

## False friends and downgrade rules

1. **Entity coreference is not sufficient.** Exclude or heavily downgrade papers that resolve only people, organizations, nominal mentions, or ordinary pronouns unless they separately evaluate discourse deixis or non-nominal antecedents.

2. **Event identity is not response scope.** Event-coreference literature is TRANSFER unless it resolves an anaphoric or response expression to an event antecedent.

3. **Dialogue-act classification is not antecedent resolution.** "Agreement", "answer", "approval", or "rejection" as a message-level act is insufficient without the target.

4. **Gold relation arguments hide the main problem.** A discourse model that receives the two correct discourse units and only chooses a relation label should be secondary evidence. The project needs attachment as well as classification.

5. **Gold questions hide answer-target selection.** Conventional QA where the question is supplied does not test which of several earlier questions a short reply addresses.

6. **Conversational QA is not automatically relevant.** Tracking the current user question in a QA system is much easier than resolving one response against several still-open prior questions.

7. **Multi-question QA is a false friend unless alignment is required.** Generating answers for multiple supplied questions is different from observing one human response and deciding which questions it resolved.

8. **"Partial answer" must mean semantic partiality.** Student grading, partial credit, incomplete generated answers, or truncated answer spans do not qualify merely because they contain the phrase.

9. **Agreement labels are not agreement scope.** A whole-message agree/disagree label does not establish whether the agreement applies to an amount, date, proposal, condition, or only one clause.

10. **Stance is useful only with a suitable target representation.** Fixed-topic, named-entity, hashtag, author-level, or broad-claim stance is TRANSFER at best.

11. **NLI is downstream evidence.** Entailment and contradiction over a supplied proposition pair may help classify the response relation, but whole-message NLI cannot substitute for locating the proposition.

12. **Single forced antecedents are a poor match.** Prefer models that can express no link, several links, candidate distributions, ambiguity, or abstention. A forced-best antecedent can create exactly the over-broad commitments the product is designed to avoid.

13. **Email structure is owned elsewhere.** Thread reconstruction, quotation extraction, quoted-source attribution, metadata reply graphs, subject matching, and conversation grouping are Topics 01/03 inputs, not Topic 04 results.

14. **Email summarization and response generation are not direct evidence.** Admit them only when they contain an independently evaluated antecedent or response-scope component.

15. **Speech-act extraction without scope belongs to Topic 05.** Detecting that "approved" is an approval does not identify what was approved.

16. **Bridging is adjacent but not equivalent.** CODI-CRAC's bridging track is useful context, but associative entity references do not solve proposition-level discourse deixis. citeturn244391search10

17. **Visual/table/document reference is a Topic 08 handoff.** A reference to "row 4", a screenshot region, an attachment page, or a spreadsheet cell should not cause Topic 04 to absorb multimodal grounding research.

18. **Whole-turn labels can be too coarse.** If one email paragraph contains several independent questions or conditions, a turn-level QAP or agreement link may still overstate scope. Give higher value to datasets or methods with EDU, clause, span, or complex-discourse-unit arguments.

19. **Antecedent-present-only benchmarks omit an important product state.** Prefer work that models anaphoricity, no-link cases, unanswerable cases, missing antecedents, or calibrated uncertainty.

20. **Domain transfer must remain labeled as transfer.** Performance on game chat, forums, spoken dialogue, news, or synthetic examples does not establish production accuracy on business email or Teams.

## Date policy

**Earliest publication year discovery must reach: 1973.**

The reason for going this far back is not that all broad searches should ingest fifty years of papers. It is that several conceptual foundations are substantially older than current NLP:

- the **adjacency-pair / sequential-response** tradition originates in 1970s conversation analysis;
- formal semantics of questions and **partial answers** was already developed by the 1980s; citeturn483419search0
- Webber's foundational computational paper **Discourse Deixis: Reference to Discourse Segments** appeared in **1988**; citeturn259084search9
- Asher's **Reference to Abstract Objects in Discourse** appeared in **1993** and explicitly develops reference to events, propositions, states, facts, and other abstract discourse entities. citeturn259084search0turn259084search4

Therefore a 2000, 2010, transformer-era, or "recent five years" cutoff would silently delete foundational work needed to understand what later datasets and models actually mean by discourse deixis, answerhood, agreement, and discourse attachment.

Operationally:

- use **1973 as the hard canonical-foundation floor**;
- perform targeted early searches for adjacency pairs, question/answer semantics, partial answerhood, discourse deixis, abstract-object reference, dialogue context, and commitments;
- use broader computational discovery from roughly the late 1990s onward;
- search the modern benchmark/model literature through the present;
- never interpret the early foundational literature itself as evidence of current production accuracy.

The practical discovery priority should therefore be:

**non-nominal antecedent anaphora / discourse deixis → dialogue discourse deixis → dialogue attachment/QAP → partial answerhood/QUD → agreement and commitment scope → target-domain email/workplace evidence**, with event coreference, multi-antecedent anaphora, stance, and NLI retained explicitly as TRANSFER rather than allowed to dominate the corpus.
