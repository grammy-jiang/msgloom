# proposition-level response scope in workplace email and dialogue, with emphasis on partial replies to multi-question or multi-proposition antecedents, unanswered subquestions, approval/rejection scope, and multi-antecedent response links academic terminology analysis

## Product problem

The product problem is not ordinary entity coreference and is not adequately described by generic dialogue-act, agreement, QA, or email-reply terminology.

The required prediction is approximately:

`response span → one or more exact antecedent proposition/span(s) → semantic response relation → scope/uncertainty`

The response relation may be answer, agreement, acceptance/approval, rejection, clarification, condition, correction, or reference. The target may be one proposition inside a larger message, several propositions jointly, a composite discourse object, or no recoverable antecedent in the supplied context.

The decisive distinction is therefore **response-target selection plus semantic scope**, not merely detection that a response exists. In particular, a system must be able to represent:

- one short response targeting only one of several preceding propositions;
- one response answering one or several of multiple pending questions;
- questions that remain unanswered;
- acceptance of a proposal but rejection or non-acceptance of one condition;
- approval of one parameter but not another;
- clarification targeted at one prior clause;
- non-adjacent antecedents;
- several simultaneous antecedents;
- a composite antecedent formed from several discourse units;
- ambiguity between plausible antecedents;
- an explicit no-link or missing-context result.

The terminology is fragmented across several academic traditions. No single seed term should be expected to retrieve the complete capability.

## Seed keyword audit

| Seed | Academic meaning | Fit | Main risk |
| --- | --- | --- | --- |
| discourse deixis | Demonstrative or related reference to prior discourse segments, propositions, facts, events, situations, or other abstract discourse objects. | STRONG | Often studies `this`/`that`, not elliptical acts such as `yes`, `approved`, or `not that part`. |
| discourse-deictic reference | Reference relation between a deictic expression and a discourse segment or abstract discourse referent. | STRONG | Older/formal terminology may not retrieve newer dialogue-linking work. |
| abstract anaphora | Anaphora whose antecedent is an event, proposition, fact, state, situation, or discourse segment rather than a nominal entity. | STRONG | Antecedent resolution may be studied without response-relation or scope classification. |
| propositional anaphora | Anaphoric reference to proposition-like discourse objects. | STRONG | Correct concept but not a uniformly standardized search label. |
| event anaphora | Anaphoric reference to events or eventualities. | MODERATE | Event identity is not equivalent to answer/agreement/approval scope. |
| anaphora resolution | Generic resolution of an anaphor to its antecedent or interpretation. | WEAK | Dominated by nominal pronouns and noun phrases. |
| coreference resolution | Linking or clustering mentions sharing a referent. | WEAK | Mainstream coreference is overwhelmingly entity-oriented. |
| coreference to events | Linking mentions denoting the same event. | MODERATE | Usually models identity, not a response relation to an event. |
| coreference to propositions | Linking expressions to proposition-like referents. | STRONG | Useful concept but sparse/non-uniform task terminology. |
| conversational coreference | Coreference resolution in dialogue. | WEAK | Usually people, objects, pronouns, or nominal mentions rather than propositions. |
| dialogue reference resolution | Reference resolution using conversational context. | MODERATE | Often situated/object-oriented or multimodal. |
| dialogue discourse parsing | Predicting attachment structure and discourse relations between conversational discourse units. | STRONG | Typical targets are turns or EDUs rather than exact proposition spans. |
| conversational discourse relations | Semantic/pragmatic relations among dialogue units, including response-like relations. | STRONG | Relation inventories can remain too coarse for partial scope. |
| discourse relation recognition | Identification/classification of discourse relations. | MODERATE | Many tasks supply relation arguments as gold. |
| response-to discourse relation | Response/reply attachment between discourse units; terminology is non-standard. | MODERATE | Exact phrase has low recall and also retrieves structural reply links. |
| adjacency pairs | Conversation-analysis pairings such as question-answer, request-acceptance/refusal, offer-acceptance. | MODERATE | Sequential relevance does not itself locate exact proposition spans. |
| dialogue act | Communicative-function classification such as question, request, answer, accept, reject. | MODERATE | Identifies what the current unit does, not necessarily what it targets. |
| question answer alignment | Linking a response or answer to the question it addresses. | STRONG | QA literature often assumes the question is already supplied. |
| question resolution | Resolution of a pending issue/question; an overloaded phrase rather than one stable task. | MODERATE | Can mean rewriting, interpreting, clarifying, or answering questions. |
| answer scope | Which question, subquestion, alternative, or issue an answer resolves; useful description but not a stable task name. | MODERATE | Retrieves extractive answer spans and linguistic scope. |
| partial answer detection | Detection that a response resolves only part of a question or information need. | MODERATE | Relevant literature is distributed across answerhood, QUD, issue tracking, and dialogue management. |
| multi-question answering in dialogue | Dialogue involving multiple questions. | WEAK | Usually sequential conversational QA, not subset alignment among simultaneously pending questions. |
| agreement detection | Recognizing agreement or acceptance. | MODERATE | Often utterance-level with no target identification. |
| disagreement detection | Recognizing disagreement, rejection, or non-alignment. | MODERATE | Does not identify which clause is rejected. |
| agreement target identification | Identifying the proposition, utterance, claim, or span toward which agreement is directed. | STRONG | Some work supplies the target or uses whole-turn targets. |
| agreement scope | Portion of prior content over which agreement holds. | MODERATE | Not a well-established task label; also attracts legal/grammatical scope. |
| stance with target identification | Predicting a stance relation together with its entity/claim/span target. | MODERATE | Typical targets are predefined entities or claims rather than prior dialogue propositions. |
| entailment relative to a proposition | Semantic support/entailment between two propositions. | WEAK | Standard NLI supplies both propositions and performs no antecedent selection. |
| contradiction detection | Detection of semantic incompatibility between propositions. | WEAK | Contradiction is not equivalent to conversational rejection or scoped disagreement. |
| business email | Professional email as a domain. | MODERATE | Alone retrieves spam, summarization, security, classification, and productivity work. |
| email reply | A message sent in response to another message. | MODERATE | Message-level reply structure does not establish proposition-level semantic scope. |
| approval scope | Portion of content to which an approval applies; useful product phrase but not a standard NLP task. | WEAK | Mostly retrieves law, authorization, procurement, and regulatory meanings. |
| workplace communication | Professional email/chat/meeting communication as a domain. | MODERATE | Too broad without a precise semantic-linking term. |

The seeds that should drive discovery most strongly are therefore **discourse deixis / abstract anaphora**, **dialogue discourse attachment**, **question-response alignment**, **agreement/acceptance target identification**, and **composite or multi-antecedent discourse reference**.

Several useful terms should be promoted even though they were not in the original seed list:

- abstract object anaphora;
- abstract entity reference;
- discourse segment antecedent;
- complex antecedent;
- complex discourse referent;
- composite antecedent;
- multi-antecedent reference;
- split antecedent, but only when combined with abstract/propositional/discourse terms;
- discourse attachment;
- reply-to relation;
- dialogue-act dependency;
- question-response pair identification;
- answerhood;
- Question Under Discussion / QUD;
- issue resolution and open issues;
- unanswered-question detection;
- incomplete answer;
- conditional relevance;
- agreement target;
- acceptance target;
- rejection target;
- proposal acceptance/rejection;
- grounding;
- clarification antecedent;
- antecedent-span selection;
- no antecedent / no-link;
- ambiguous antecedent;
- multiple antecedents;
- selective prediction / abstention.

Generic `anaphora resolution`, `coreference resolution`, `dialogue act`, `multi-question answering`, NLI, contradiction detection, and `approval scope` should be demoted to supporting terms rather than used as primary discovery queries.

## Academic task families

### F1 — Abstract, propositional, event, and discourse-deictic antecedent resolution — DIRECT

This family resolves expressions to prior propositions, events, facts, situations, or discourse segments. It is the strongest mature terminology for non-entity antecedents.

Known foundational sources include:

- Webber (1991), *Structure and Ostension in the Interpretation of Discourse Deixis*.
- Asher (1993), *Reference to Abstract Objects in Discourse*.
- Byron (2002), *Resolving Pronominal Reference to Abstract Entities*.

It directly supports exact antecedent representation, but discovery must distinguish simple demonstrative anaphora from response acts such as `yes`, `agreed`, or `approved`.

### F2 — Dialogue discourse attachment and reply-to relation prediction — DIRECT

This family predicts which previous conversational unit a current unit attaches to or responds to, sometimes jointly with a discourse-relation label.

A known seed is:

- Afantenos et al. (2015), *Discourse Parsing for Multi-Party Chat Dialogues*.

This family is particularly important for non-adjacent antecedents, candidate competition, explicit attachment links, and relation-aware response structure. Whole-turn or whole-EDU evaluation, however, is insufficient evidence for proposition-level partial scope.

### F3 — Question-response alignment, answerhood, and open-issue resolution — DIRECT

This family asks which question or issue a response addresses and whether that issue has been fully or partially resolved.

A useful foundational source is:

- Roberts (1996), *Information Structure in Discourse: Towards an Integrated Formal Theory of Pragmatics*.

The terminology to emphasize is not merely `question answering`. Discovery should combine:

- question-response alignment;
- answerhood;
- Question Under Discussion / QUD;
- issue resolution;
- open questions;
- unanswered questions;
- incomplete or partial answers;
- conditional relevance.

This is the highest-value route for gap-3 because a multi-question message creates several simultaneously available response targets and a short reply may close only a subset.

### F4 — Agreement, disagreement, acceptance, and rejection with target identification — DIRECT

This family detects an agreement-like or rejection-like response and identifies its target.

A known seed is:

- Galley et al. (2004), *Identifying Agreement and Disagreement in Conversational Speech: Use of Bayesian Networks to Model Pragmatic Dependencies*.

Discovery must require target or antecedent information. Pure utterance-level agreement classification does not close gap-1.

Especially valuable terms are:

- agreement target;
- acceptance target;
- rejection target;
- partial agreement;
- partial disagreement;
- agreement antecedent;
- acceptance antecedent;
- discourse attachment of agreement/rejection.

### F5 — Proposal, request, grounding, acceptance, rejection, and clarification sequences — DIRECT

Conversation research treats requests, proposals, assertions, acknowledgements, acceptances, rejections, repairs, and clarification requests as structured interaction rather than independent labels.

Useful foundations include:

- Clark and Schaefer (1989), *Contributing to Discourse*.
- Traum (1994), *A Computational Theory of Grounding in Natural Language Conversation*.

This family may supply the closest established concepts for `approved`, `agreed`, `no`, `not that part`, and clarification responses, even when `approval scope` itself has little NLP literature.

For msgloom, an approval should be treated as a specialized acceptance relation whose target still needs to be resolved.

### F6 — Composite, complex, discourse-segment, and multi-antecedent reference — DIRECT

This family covers interpretations whose antecedent cannot be reduced to one simple nominal mention or one single discourse unit.

Relevant vocabulary includes:

- complex antecedent;
- complex discourse referent;
- discourse-segment antecedent;
- composite antecedent;
- multiple antecedents;
- multi-antecedent;
- split antecedent;
- discontinuous antecedent.

Asher (1993) is a safe foundational starting point for abstract discourse objects.

This family is the main path for gap-4. Discovery should specifically test whether papers permit an abstract referent constructed from multiple propositions or multiple discourse units. Entity-oriented split-antecedent work should be downgraded unless the representation transfers to proposition/discourse antecedents.

### F7 — Workplace email and enterprise-conversation response structure — DIRECT

This family supplies domain-specific evidence from professional communication.

Known email speech-act seeds include:

- Cohen, Carvalho, and Mitchell (2004), *Learning to Classify Email into Speech Acts*.
- Carvalho and Cohen (2005), *On the Collective Classification of Email Speech Acts*.

Those papers do not by themselves establish proposition-level response scope, but they provide an entry point into authentic email communicative structure.

This family should search specifically for:

- question-response pairs in email;
- multiple questions in one email and later replies;
- unanswered questions;
- request-response links;
- acceptance/rejection in professional email;
- Enron email question/answer or request/response annotation;
- enterprise-chat response relations.

For gap-1 and gap-3, target-domain papers should receive much higher evidential weight than generic dialogue transfer papers.

### F8 — Targeted stance and proposition-pair semantic relations — TRANSFER

Stance, entailment, contradiction, support, and opposition can help classify the **relation once a target has been selected**.

Known transfer seeds include:

- Bowman et al. (2015), *A Large Annotated Corpus for Learning Natural Language Inference*.
- Mohammad et al. (2016), *SemEval-2016 Task 6: Detecting Stance in Tweets*.

This family does not close the response-scope gaps unless target selection is also evaluated.

### F9 — Discourse-relation parsing and argument-span identification — TRANSFER

This family contributes methods for finding relation arguments and span boundaries.

Foundational seeds include:

- Mann and Thompson (1988), *Rhetorical Structure Theory: Toward a Functional Theory of Text Organization*.
- Prasad et al. (2008), *The Penn Discourse TreeBank 2.0*.

The useful transfer is exact argument-span representation, non-adjacent relations, attachment, and potentially discontinuous arguments. Monologic discourse relation recognition is not direct evidence for workplace reply scope.

### F10 — No-link, ambiguity, multi-link, and abstaining antecedent prediction — TRANSFER

msgloom's annotation contract requires more than conventional forced classification. Search should find methods or annotation schemes that permit:

- no antecedent;
- null/no-link;
- unresolved references;
- missing context;
- several plausible antecedents;
- several simultaneously valid antecedents;
- confidence or calibrated abstention.

This family is especially relevant to gap-2 and gap-5. Literature from coreference, structured prediction, selective prediction, and dialogue attachment can transfer mechanisms, but it does not establish msgloom's domain-specific confidence thresholds or asymmetric costs.

## Query families

### F1 — DIRECT: abstract/propositional antecedent resolution

- `"discourse deixis" antecedent resolution proposition dialogue`
- `"discourse-deictic" reference antecedent discourse segment`
- `"abstract anaphora" antecedent resolution dialogue`
- `"abstract anaphora" proposition event fact antecedent`
- `"propositional anaphora" antecedent resolution`
- `"abstract entities" anaphora resolution dialogue`
- `"discourse segment" demonstrative antecedent resolution`

### F2 — DIRECT: dialogue discourse attachment

- `"dialogue discourse parsing" attachment response relation`
- `"discourse attachment" dialogue reply response antecedent`
- `"reply-to" relation dialogue discourse parsing`
- `"response relation" dialogue antecedent attachment`
- `"dialogue act dependency" antecedent response`
- `"conversational discourse" attachment relation antecedent`
- `"multi-party chat" discourse parsing response relation`

### F3 — DIRECT: question-response alignment and unresolved questions

- `"question answer alignment" dialogue antecedent`
- `"question-response" alignment dialogue multiple questions`
- `"question-response pairs" dialogue identification`
- `"answerhood" dialogue question under discussion`
- `"question under discussion" partial answer dialogue`
- `"partial answer" dialogue unresolved question`
- `"incomplete answer" dialogue question resolution`
- `"unanswered question" detection dialogue`
- `"open questions" dialogue issue tracking`
- `"issue resolution" dialogue questions answers`
- `"multiple questions" single response dialogue answer`
- `"multi-question" response alignment dialogue`
- `"subquestion" answer dialogue unresolved`
- `"conditional relevance" question answer dialogue`

### F4 — DIRECT: agreement/rejection target and scope

- `"agreement target" dialogue identification`
- `"agreement target identification" conversation`
- `"agreement" antecedent identification dialogue`
- `"disagreement" antecedent target dialogue`
- `"acceptance" target proposition dialogue`
- `"rejection" target proposition dialogue`
- `"partial agreement" dialogue proposition`
- `"partial disagreement" dialogue proposition`
- `"agreement scope" dialogue conversation`
- `"acceptance scope" dialogue proposition`
- `"agreement disagreement" discourse attachment dialogue`
- `"yes" antecedent resolution dialogue agreement`

### F5 — DIRECT: proposal/request/grounding sequences

- `"proposal acceptance" dialogue antecedent`
- `"proposal rejection" dialogue antecedent`
- `"request acceptance" dialogue response relation`
- `"request rejection" dialogue response relation`
- `"grounding" acceptance rejection proposal dialogue`
- `"grounding act" antecedent dialogue`
- `"clarification request" antecedent resolution dialogue`
- `"repair" clarification antecedent dialogue`
- `"adjacency pair" request acceptance rejection computational`
- `"adjacency pair" proposal acceptance dialogue`
- `"conditional relevance" request acceptance refusal`

### F6 — DIRECT: composite and multiple antecedents

- `"complex antecedent" discourse anaphora proposition`
- `"complex discourse referent" anaphora`
- `"discourse segment antecedent" anaphora`
- `"multiple antecedents" abstract anaphora`
- `"multi-antecedent" anaphora proposition discourse`
- `"split antecedent" abstract anaphora`
- `"split antecedent" proposition discourse`
- `"composite antecedent" discourse reference`
- `"composite discourse referent" proposition`
- `"multi-unit antecedent" discourse`
- `"discontinuous antecedent" anaphora discourse`

### F7 — DIRECT: workplace email / enterprise chat

- `"business email" question answer reply alignment`
- `"workplace email" question response alignment`
- `"email" multiple questions reply partial answer`
- `"email reply" partial answer question`
- `"email" agreement disagreement reply target`
- `"email" proposal acceptance rejection reply`
- `"email" approval reply proposition`
- `"business email" approval rejection response`
- `"enterprise chat" question response alignment`
- `"enterprise chat" agreement rejection reply`
- `"workplace communication" partial agreement reply`
- `"workplace communication" unanswered questions`
- `"Enron" email question answer pairs`
- `"Enron email" request response agreement`

The F7 queries should be deliberately run even if their hit counts are low. Gap-closure round 3 needs direct authentic-workplace evidence rather than another large collection of transfer papers.

### F8 — TRANSFER: targeted stance / NLI

- `"target identification" stance proposition span`
- `"targeted stance" claim proposition`
- `"stance target" span identification`
- `"claim target" support oppose span`
- `"natural language inference" proposition target dialogue`
- `"entailment" proposition pair dialogue response`
- `"contradiction" proposition pair dialogue response`
- `"partial contradiction" proposition span`

### F9 — TRANSFER: discourse argument spans

- `"discourse relation" argument span identification`
- `"discourse relation" argument extraction discontinuous`
- `"discourse parsing" argument spans attachment`
- `"discourse dependency" attachment relation dialogue`
- `"discourse relation" multi-argument antecedent`
- `"discourse relation" non-adjacent arguments dialogue`

### F10 — TRANSFER: no-link, ambiguity, multiple links, abstention

- `"no antecedent" anaphora resolution`
- `"null antecedent" reference resolution`
- `"no-link" antecedent prediction discourse`
- `"no link" dialogue attachment relation`
- `"multiple antecedents" dialogue attachment`
- `"ambiguous antecedent" dialogue reference resolution`
- `"uncertain antecedent" reference resolution`
- `"abstention" coreference resolution`
- `"selective prediction" coreference resolution`
- `"calibrated" antecedent selection coreference`
- `"confidence" discourse attachment abstention`

## False friends and downgrade rules

Discovery should downgrade or reject matches according to the following rules.

1. **Entity coreference is not sufficient.** Reject or downgrade work that resolves only people, organizations, objects, or nominal mentions unless it explicitly supports propositions, events, facts, situations, clauses, or discourse segments.

2. **Event identity is not response scope.** Event-coreference papers are transfer evidence if they merely cluster mentions of the same event.

3. **Dialogue-act labels are not antecedent links.** A turn labeled `accept`, `answer`, `reject`, or `clarify` does not tell msgloom what exact earlier proposition it applies to.

4. **Agreement detection is not agreement scope.** Whole-turn agreement/disagreement classification should not count toward gap-1 unless target selection is part of the task or annotation.

5. **A supplied stance target does not solve target identification.** Stance toward a predefined politician, topic, product, claim, or entity is transfer evidence only.

6. **Gold sentence pairs do not solve reference resolution.** NLI, entailment, contradiction, semantic similarity, and fact verification should be downgraded when both propositions are supplied.

7. **Ordinary QA is not question-response alignment.** Reading comprehension where a gold question is given does not determine which earlier question a new reply addresses.

8. **Conversational QA is not automatically multi-question scope.** A system that answers a series of user questions is irrelevant to gap-3 unless one response must be mapped to a subset of concurrently pending questions.

9. **Partial answer must mean partial issue resolution.** Reject matches where `partial answer` means truncated text, incomplete KB coverage, partial credit, or answer-quality grading.

10. **Email reply structure is not semantic reply scope.** Reply headers, quotation extraction, thread reconstruction, and conversation disentanglement establish structural provenance only.

11. **Reply generation is not response analysis.** Smart Reply, response generation, response-time prediction, and next-response selection should normally be rejected.

12. **Gold discourse arguments weaken relevance.** Relation classification with supplied Arg1/Arg2 spans does not solve antecedent selection.

13. **Monologic discourse parsing is transfer evidence.** It can contribute span and attachment machinery but cannot demonstrate workplace reply behavior.

14. **Adjacency-pair theory alone is insufficient.** Qualitative sequence analysis that does not operationalize proposition targets should be treated as conceptual background rather than gap-closing empirical evidence.

15. **Generic workplace communication is too broad.** Organizational psychology, management, communication surveys, and sociolinguistic workplace studies should be rejected unless they annotate the relevant response/antecedent relation.

16. **`Approval scope` has dangerous non-NLP meanings.** Reject access-control scope, regulatory approval, legal authority, procurement workflow, and authorization-system literature unless it analyzes natural-language approval targets.

17. **Forced single-link models are incomplete for msgloom.** A model that requires exactly one antecedent should be downgraded where genuine no-link, ambiguity, missing context, multiple links, or composite antecedents are possible.

18. **Message-level evaluation is insufficient for partial-scope claims.** If gold and predictions only state that a reply responds to a message, the paper cannot demonstrate whether a response applies to one clause or all clauses.

19. **A reply-to edge is not a semantic commitment edge.** Structural reply relationships must never be treated as evidence that all propositions in the parent message were answered, accepted, or approved.

20. **No-link and missing antecedent are different states.** Prefer annotation schemes that distinguish unsupported reference, genuinely absent antecedent, missing external context, ambiguity, and model uncertainty.

21. **Multiple antecedents must not automatically be collapsed to ambiguity.** Retain work that explicitly represents a legitimate composite target or several simultaneous semantic links.

22. **Exact target representations receive priority.** Antecedent spans, EDUs, propositions, clauses, or explicit discourse links are more useful than coarse turn/message labels.

23. **Synthetic or other-domain findings do not establish workplace accuracy.** They may support TRANSFER methods or engineering fixtures, but direct production-domain claims require authentic work-communication evidence.

24. **A relation label without candidate-selection evaluation is incomplete.** For gap closure, the paper must reveal whether the correct prior unit or proposition was identified, not only whether a relation classifier recognized `answer`, `agreement`, or `rejection`.

## Date policy

**Earliest publication year to include: 1973.**

Discovery should reach at least 1973 because the conversation-analysis foundations of adjacency pairs, sequence organization, and conditional relevance predate modern computational NLP. Those concepts underlie the distinction between a first action such as a question, request, offer, or proposal and the class of responses that make a relevant second action.

The computational literature closest to the present problem becomes especially important from the late 1980s and 1990s onward:

- grounding and collaborative contribution;
- discourse deixis;
- abstract discourse objects;
- propositional/event reference;
- later computational abstract-anaphora resolution;
- dialogue discourse attachment and conversational discourse parsing.

Accordingly, discovery may **prioritize 1990-present for computational retrieval**, but the canonical search/acquisition policy must permit **1973-present**. A 2000-present or recent-only window would silently remove conceptual foundations needed to understand response relevance, answerhood, grounding, and abstract discourse antecedents.
