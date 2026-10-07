You are one worker inside an automated literature-review pipeline.
A script, not a person, reads your reply. Follow these rules exactly:
- Do the task completely in this single reply. Do not ask questions and do not
  wait for confirmation.
- Reply with the requested artifact block(s) only: no preamble, no commentary
  outside the blocks. Each block starts with a line `===BEGIN <name>===` and
  ends with a line `===END <name>===`; the content between those lines is
  written to a file verbatim.
- Never invent papers, identifiers, numbers, or quotes. Leave unknown fields
  out or mark them as unknown.
- Do not use your code tool, canvas, or connectors; plain text is enough.

# Task: admission gate for 25 screened candidate(s)

Research topic: **direct empirical studies of proposition-level partial reply scope in workplace email or enterprise dialogue, especially multi-question messages, unanswered subquestions, scoped approval/rejection, and responses linked jointly to multiple antecedent propositions**

Decide which of these candidates enters the reading round. Admit a paper only
when it materially strengthens one of the research streams below, and the
abstract shows that, not merely shared vocabulary. A paper count is never a
reason to admit: admitting six of twenty is a valid answer, and so is
admitting none. Rejecting a paper here costs little; reading a paper that
cannot strengthen a stream costs a reading slot that a better paper needed.

Research streams:
- F1 [DIRECT] non-nominal antecedent and abstract-anaphora resolution: Resolve an anaphoric or discourse-deictic expression to clausal, sentential, eventive, factual, situational, or propositional antecedent spans rather than ordinary nominal entities.
- F2 [DIRECT] dialogue discourse attachment and response-relation parsing: Predict which prior discourse unit a current conversational unit attaches to and classify the semantic-pragmatic relation between them.
- F3 [DIRECT] question-answer pair extraction and alignment in email or dialogue: Detect naturally occurring questions and link each question to the answer utterance or span that responds to it within an email thread or dialogue.
- F4 [DIRECT] partial answers, answer completeness, and multi-question resolution: Determine which components of a question set or multi-part issue are resolved by an answer, which receive only partial information, and which remain unresolved.
- F5 [DIRECT] agreement, disagreement, acceptance, and rejection target identification: Detect agreement-like or disagreement-like conversational acts and identify the preceding utterance, speaker, discourse unit, or proposition they target.
- F6 [DIRECT] multi-antecedent and composite discourse antecedents: Represent cases where a response or referring expression relates to more than one antecedent discourse unit or to a complex discourse object constructed from multiple propositions.
- F7 [TRANSFER] workplace email speech acts and utterance-level action annotation: Identify requests, commitments, proposals, acceptances, and other communicative actions in authentic workplace email, preferably at utterance or sentence level.
- F8 [TRANSFER] targeted stance and claim-target relation extraction: Identify both a stance-bearing expression and the claim, proposition, argument, entity, or span toward which positive, negative, supporting, or opposing stance is expressed.
- F9 [TRANSFER] proposition-pair entailment, contradiction, and semantic relation classification: Classify whether one proposition entails, contradicts, supports, weakens, or is neutral with respect to another already selected proposition.
- F10 [TRANSFER] antecedent selection with ambiguity, no-link, and abstention: Select an antecedent from candidate discourse units while allowing ambiguous, multiple, non-linguistic, absent, or explicit no-antecedent outcomes rather than forcing a single link.
- F11 [TRANSFER] adjacency-pair and conversational sequence analysis: Model how actions such as questions, requests, proposals, invitations, acceptances, refusals, and answers create expectations for paired or sequentially related responses.

Open gaps this round must close (a paper that speaks to one of these
is worth admitting even when its topic wording is unusual):
- gap-1 [ACADEMIC, HIGH]: Direct empirical evidence is still missing for proposition-level agreement, rejection, approval, clarification, and answer scope in authentic workplace email or enterprise chat, especially cases where one short response applies to only part of a preceding message.
    suggested query: "partial reply" OR "response scope" email workplace dialogue proposition agreement rejection approval
    searched in rounds: [1, 2, 3] (still open)
- gap-2 [ENGINEERING, HIGH]: A validated annotation and evaluation scheme is still missing for mapping workplace responses to exact proposition or span targets while representing exact, partial, ambiguous, unsupported, discontinuous, multiple-antecedent, and explicit no-link cases. Individual requirements are supported by the literature, but the combined msgloom annotation contract has not been validated.
- gap-3 [ACADEMIC, HIGH]: Direct evidence remains insufficient for aligning replies to one or more questions when a preceding workplace message contains multiple questions, requests, or alternatives, including proposition-level detection of questions that remain unanswered.
    suggested query: "multiple questions" "partial answer" dialogue email question answer alignment unanswered subquestions
    searched in rounds: [1, 2, 3] (still open)
- gap-4 [ACADEMIC, MEDIUM]: It remains open whether and how a workplace response should be modeled as targeting a composite or multi-proposition antecedent. The corpus supports composite abstract discourse referents and multi-unit discourse antecedents, but does not directly evaluate multi-proposition reply scope in work communication.
    suggested query: "multi-antecedent" dialogue response "composite antecedent" proposition discourse email
    searched in rounds: [1, 2, 3] (still open)
- gap-5 [ENGINEERING, HIGH]: The appropriate msgloom policy for uncertainty-driven abstention, ambiguity, missing antecedents, and asymmetric error costs remains unvalidated. The literature supports explicit no-link outcomes and preservation of ambiguous or multiple antecedents, but it does not establish confidence thresholds or the relative cost of over-broad approval/commitment links versus unresolved links.
Decisions:
- ADMIT — name the stream and why the abstract shows the contribution.
- REJECT — name the reason: topic words match but the capability does not,
  the evidence duplicates a paper already admitted, or the claim is out of
  scope.
- PENDING — the abstract cannot settle it; say what would.

`identity: UNCHECKED` means the host could not confirm the paper's identifier
with the provider. That is not proof the paper is wrong, but prefer a
VERIFIED paper when the two are otherwise equal, and say so in the reason.


## Project context you must work within

This is the project's own description of the problem, its boundaries,
and the distinctions it needs preserved. It governs what counts as
relevant; the academic task names alone do not.

# Topic 04 context — Reference resolution and response scope

## Why this Topic exists

Business communication contains short expressions whose meaning depends on prior propositions, events, proposals, questions, attachments, or specific spans: “this”, “that proposal”, “same as below”, “approved”, “agreed”, “yes”, “not that part”, “see row 4”, “please do the first two”. Entity coreference alone does not solve these cases.

A reply may answer only one of several questions, agree with a proposal but not its condition, approve an amount but not a date, or reject one clause while accepting the rest. If msgloom attaches a response too broadly, it can invent commitments or close work that remains open.

Topic 04 owns **reference resolution to propositional/event/content antecedents and the semantic scope of responses**.

## Direct handoffs from earlier Topics

Topic 01 hands off semantic reply/partial-agreement scope after it has identified quotation/source spans. Topic 02 hands off semantic response scope after it has identified Topic-related spans. These are explicit boundaries: Topic 04 should use those structural outputs rather than re-research quotation extraction or Topic segmentation.

## Core research object

Resolve a current expression/response to one or more exact antecedent spans or structured propositions, with uncertainty where needed:

```text
response span
   → antecedent proposition/span(s)
   → relation: answer / agreement / rejection / clarification / condition / reference
   → scope: exact, partial, ambiguous, unsupported
```

## Product and phase relevance

This capability affects Phase 1 semantic triage whenever supplied group context contains replies, approvals, and references. Phase 2 may retrieve additional evidence when the antecedent is outside the supplied context or uncertain. Missing antecedents must remain unresolved rather than guessed.

## Relationships to other Topics

| Topic | Relationship |
| --- | --- |
| 01 | Provides quote/source-span and message relationship evidence; Topic 04 decides semantic response target/scope. |
| 02 | Provides work-matter span membership; Topic 04 can constrain antecedent candidates to relevant Topic evidence. |
| 03 | Stable Topic identity narrows historical antecedent candidates across threads/sources. |
| 05 | Topic 04 determines what an approval/request/commitment applies to; Topic 05 classifies/extracts the action or speech act itself. |
| 06 | State changes such as approved/revoked depend on correct response scope. |
| 07 | If the antecedent is missing, Topic 07 can turn the unresolved reference into a targeted evidence need. |
| 08 | References to tables, screenshots, attachments, cells/pages, or visual regions require Topic 08 grounding. |
| 10 | General calibration/attribution evaluation belongs to Topic 10; Topic 04 owns domain-specific reference/response correctness. |

## Key conceptual distinctions

- Entity coreference ≠ propositional/discourse reference.
- Quote source ≠ what the response semantically answers.
- Agreement detection ≠ agreement scope.
- Question answering ≠ deciding which prior question a reply addresses.
- A short “yes” may resolve one proposition while leaving other requests open.
- Unsupported antecedent ≠ absent antecedent; the correct result may be uncertainty.

## High-value academic terminology

- discourse deixis; discourse-deictic reference;
- abstract anaphora; propositional anaphora; event anaphora;
- anaphora/coreference to events, propositions, facts, situations;
- conversational coreference; dialogue reference resolution;
- dialogue discourse parsing; conversational discourse relations;
- response-to / reply-to discourse relation;
- question–answer alignment; question resolution; answer scope;
- partial answer detection; multi-question answering in dialogue;
- agreement/disagreement detection; stance with target identification;
- dialogue act / speech-act relation; adjacency pairs;
- entailment/contradiction relative to a proposition (transfer evidence);
- reference resolution to document/table/visual objects (handoff to Topic 08).

## Query families

- `"discourse deixis" dialogue resolution`
- `"abstract anaphora" dialogue`
- `"propositional anaphora" conversation`
- `"event anaphora" email dialogue`
- `"dialogue discourse parsing" response relation`
- `"question answer alignment" dialogue multiple questions`
- `"partial answer" dialogue question`
- `agreement target identification dialogue`
- `"agreement scope" conversation`
- `email reply response scope approval`
- `business email partial approval response`

## False friends / exclusions

Do not treat these alone as sufficient:

- named-entity coreference;
- generic sentiment/stance without target span;
- Topic 01 quote attribution;
- Topic 05 speech-act label without antecedent scope;
- whole-message NLI that cannot locate the affected proposition;
- answer correctness benchmarks where the antecedent question is supplied as gold and no reference resolution is required.

## Gap-evaluation guidance

Prioritize gaps that could make msgloom state a broader approval, answer, rejection, or commitment than the evidence supports. Partial-scope errors are decision-critical. Prefer methods/evaluation that return exact antecedent spans, multiple candidate antecedents, or abstention rather than forcing one message-level label. When missing context is the real problem, hand the evidence need to Topic 07 rather than treating it as a reference-model failure.

## How to use this file

This file is the self-contained research context for this Topic. A future AI research agent should read **this file first**, then `BRIEF.md`, then any existing `CURRENT_STATUS.md`, gap decisions, reports, manifests, and prior-round artifacts in this folder. The aim is that an agent given only this Topic folder can reconstruct the project intent, Topic boundary, dependencies, search vocabulary, and gap-prioritization logic without relying on the original ChatGPT conversation.

If the full repository is available, the authoritative product documents remain `../../docs/design-brief.md`, `../../docs/design-principles.md`, `../../docs/design.md`, and `../../docs/phase-roadmap.md`. This file explains how those product constraints apply to this research Topic; it does not replace or approve changes to those design documents.

## Shared msgloom background

msgloom is a personal work-information system for one user. It is intended to process very large daily volumes of work communication, initially Outlook email and Microsoft Teams, while ensuring that **work requiring the user's response is not missed** and reducing how much the user must read to stay current.

The product is organized around **Topics**, not message summaries. A Topic is a concrete work matter described by information from one or more sources. One message can contain several Topics; one Topic can span many messages, conversations, attachments, groups, and eventually multiple sources. A conversation or Group is therefore not automatically one Topic.

The report contract is the ultimate product pressure on all ten research Topics. Reports must preserve every due Topic and the decision-relevant information needed to act on it, including developments, actions, deadlines, conditions, risks, uncertainty, and links back to exact source evidence. Missing or conflicting information must remain visible rather than being silently filled in.

The design decision order is important when evaluating research gaps: user permissions are fixed; then preserve correct meaning and report coverage; then traceability and recovery; then usability/maintenance; finally speed, brevity, and token savings. A method that is faster but loses a condition, deadline, branch, source relation, or important Topic is not an improvement for msgloom.

Important persistent principles:

- Use deterministic code for reliable mechanical relationships and AI for language understanding/judgement.
- Preserve source bytes, versions, stage history, identities, and lineage. New assessments do not erase old evidence.
- Group only on reliable relationships. Similar subjects, participants, wording, or model labels are not enough to prove Topic identity.
- Keep uncertain relationships separate and make the reason for uncertainty visible.
- Brevity must come from concise wording and layered detail, never from omitting decision-essential information.
- User-reviewed examples, missed important work, false alerts, wrong grouping, lost actions/deadlines, and evidence that changes a decision matter more than paper count or message throughput.

## Research-programme relationship

The ten Topics form a dependency network rather than ten independent literature reviews. A useful conceptual flow is:

```text
01 source/conversation structure
        ↓
02 within-message Topic spans/membership
        ↓
03 cross-thread/source Topic identity
        ↓
04 reference and response scope
        ↓
05 actions / requests / commitments / decisions
        ↓
06 state / factuality / time / revision
        ↓
07 retrieve missing context when needed
        ↘
08 understand attachments / tables / images
        ↓
09 incremental personalized briefing
        ↓
10 evidence, completeness, calibration, reliability evaluation
```

This is not a strict processing pipeline. Several Topics feed each other, and Topic 10 is cross-cutting. The numbering primarily gives a research order and ownership boundary so that one Topic does not silently absorb the whole product problem.

## Gap-evaluation rules inherited from Topics 01 and 02

The Research Pipeline must evaluate gaps using **project value**, not just academic novelty. The following rules are part of the context for every Topic:

1. A machine-classified `HIGH` or `ACADEMIC` gap does **not** automatically authorize another literature round.
2. After each academic round, perform a human/project-value review: decide whether the uncertainty is best addressed by more papers, engineering experiments, a later Topic, production-domain data, candidate-method selection, or no further current work.
3. Prefer targeted academic follow-up over broad searching. Do not fill paper quotas with weakly related literature.
4. Distinguish direct target-domain evidence from transfer methods/evaluation evidence. Transfer evidence can justify a mechanism or experiment, not production-email accuracy.
5. Engineering validation may use independent synthetic/adversarial fixtures and public data. Lack of production mailbox examples is not a reason to stop work that can be validly completed without them.
6. Never claim production representativeness from synthetic or transfer evidence. Record it as deferred until suitable authorized domain data exists.
7. If a gap belongs to another Topic, hand it off explicitly rather than duplicating research.
8. Research closure means **everything actionable at the current stage is complete and remaining work is explicitly deferred/handed off**. It does not mean literature exhaustion, production accuracy, or architecture approval.
9. For new academic work, use terminology refinement, strict paper admission, manual/controlled canonical acquisition, corpus freeze, fresh isolated Pipeline runs, direct-vs-transfer labels, independent review, strict validation, and post-round gap review. These are lessons learned from Topics 01 and 02.
10. For engineering research, keep gold independent from the component under test; structurally separate prediction inputs from evaluation gold/future context; count false positives and false negatives in end-to-end denominators; use clean-workspace reproducibility, mutation/regression tests, and fresh independent methodological review.

Candidates:
- paper_id `doi-10-1016-j-pragma-2010-04-011` [identity: UNCHECKED] An overview of the question–response system in American English conversation (2010, Journal of Pragmatics)
    Analyzes hundreds of questions from videotaped spontaneous American English conversations. It characterizes question types, social actions, and response types, providing empirical evidence about how natural responses satisfy or fail to fit prior questions.
- paper_id `doi-10-1145-3209978-3210046` [identity: UNCHECKED] Characterizing and Supporting Question Answering in Human-to-Human Communication (2018, The 41st International ACM SIGIR Conference on Research & Development in Information Retrieval)
    Empirically studies question answering in a large enterprise-email collection and supplements the corpus analysis with a user survey. It defines extraction of question-answer pairs from threaded email conversations and evaluates neural question-to-answer matching at multiple granularities on manually labeled email data.
- paper_id `doi-10-2307-412243` [identity: UNCHECKED] A simplest systematics for the organization of turn-taking for conversation (1974, Language)
    Develops and empirically motivates a model of turn-taking from naturally occurring conversation. Although it does not provide proposition-level computational annotations, its concepts of next-speaker selection, transition relevance, and recipient design are foundational for later empirical work on sequential response relations.
- paper_id `manual-849c5f1c6d` [identity: UNCHECKED] Automatically Selecting Answer Templates to Respond to Customer Emails (2007, Proceedings of the 20th International Joint Conference on Artificial Intelligence (IJCAI 2007))
    Studies authentic customer-support email in which an incoming message can contain several questions and agents compose replies from one or more answer templates. The method identifies portions of customer queries requiring responses and learns associations between actual questions and answers from query-response email pairs, with evaluation including real contact-center data.
- paper_id `doi-10-3115-981623-981630` [identity: UNCHECKED] Getting at Discourse Referents (1989, 27th Annual Meeting of the Association for Computational Linguistics)
    Uses conversational data to compare discourse-anaphoric uses of the pronoun it with demonstrative that. The empirical analysis examines how grammatical and attentional properties of earlier discourse determine which discourse referent is selected.
- paper_id `doi-10-1016-j-pragma-2010-04-002` [identity: UNCHECKED] A coding scheme for question–response sequences in conversation (2010, Journal of Pragmatics)
    Presents the empirical coding scheme used in a ten-language comparative project on naturally occurring question-response sequences. The response annotation distinguishes answers, non-answer responses, and absence of a response, and separately records confirmation versus disconfirmation for polar questions.
- paper_id `doi-10-5087-dad-2020-104` [identity: UNCHECKED] Modelling Structures for Situated Discourse (2020, Dialogue & Discourse)
    Studies complete SDRT structures in situated multi-party chat and analyzes interactions among linguistic moves, nonlinguistic events, discourse threads, and higher-order structures. The work is relevant to responses whose discourse target is a complex discourse unit rather than a single preceding utterance.
- paper_id `doi-10-3389-frobt-2023-949600` [identity: UNCHECKED] End-to-end dialogue structure parsing on multi-floor dialogue based on multi-task learning (2023, Frontiers in Robotics and AI)
    Empirically studies dialogue structure in multi-floor collaborative robot-navigation conversations, where several concurrent conversational transactions may be active. The parser predicts antecedent links for utterances and then relation types, with dialogue-response prediction used as an auxiliary task.
- paper_id `2110.04526` [identity: VERIFIED] Improving Multi-Party Dialogue Discourse Parsing via Domain Integration (2021, Proceedings of the 2nd Workshop on Computational Approaches to Discourse)
    Studies prediction of discourse dependency structure and relations between elementary discourse units in multi-party dialogue. It evaluates cross-domain attachment and relation prediction and develops domain-integration methods for transferring dialogue discourse parsers across conversational settings.
- paper_id `doi-10-1177-1367006912441419` [identity: UNCHECKED] Reformulation of questions with candidate answers (2013, International Journal of Bilingualism)
    Studies a multi-unit format in which an open question is reformulated as a more specific yes-no question or a set of alternatives. The reformulation supplies candidate answers and changes the response space against which the recipient's subsequent answer is interpreted.
- paper_id `manual-a9d613628b` [identity: UNCHECKED] Coding Dialogs with the DAMSL Annotation Scheme (1997, Working Notes of the AAAI Fall Symposium on Communicative Action in Humans and Machines)
    Describes the DAMSL dialogue-act annotation scheme and reports initial human-annotation reliability. Its backward communicative functions explicitly encode how a current utterance relates to earlier dialogue, including answering a question, accepting a proposal, and confirming understanding, while allowing multiple communicative functions on an utterance.
- paper_id `doi-10-1515-text-2003-021` [identity: UNCHECKED] Multi-unit questions in institutional interactions: Sequential organizations and communicative functions (2003, Text)
    Analyzes a corpus of roughly four hundred multi-unit questions from authentic institutional interactions including health care, court trials, police interrogations, and social-welfare encounters. It identifies sequential organizations involving multiple interrogative and declarative units and examines how the units jointly constrain subsequent responses.
- paper_id `doi-10-3115-1118121-1118124` [identity: UNCHECKED] Non-Sentential Utterances in Dialogue: A: Corpus-Based Study (2002, Proceedings of the Third SIGdial Workshop on Discourse and Dialogue)
    Presents a corpus-based study of non-sentential utterances in dialogue, including short answers and other fragments whose interpretation depends on prior conversational material. The analysis motivates explicit recovery of the contextual antecedent needed to interpret such responses.
- paper_id `1812.00176` [identity: VERIFIED] A Deep Sequential Model for Discourse Parsing on Multi-Party Dialogues (2019, Proceedings of the AAAI Conference on Artificial Intelligence)
    Presents a sequential discourse parser for multi-party dialogue. For each elementary discourse unit, the model selects a previous EDU as its antecedent and predicts the corresponding discourse relation, jointly constructing a dialogue dependency structure.
- paper_id `doi-10-18653-v1-d19-1234` [identity: UNCHECKED] Weak Supervision for Learning Discourse Structure (2019, Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing and the 9th International Joint Conference on Natural Language Processing)
    Evaluates weak-supervision strategies for learning discourse structure in multi-party dialogue. The experiments address discourse attachment rather than only relation classification, so the system must identify which earlier discourse unit a later contribution is linked to.
- paper_id `doi-10-24963-ijcai-2021-543` [identity: UNCHECKED] A Structure Self-Aware Model for Discourse Parsing on Multi-Party Dialogues (2021, Proceedings of the Thirtieth International Joint Conference on Artificial Intelligence)
    Predicts discourse dependency structures for multi-party dialogues by modeling candidate EDU-to-EDU edges jointly rather than relying only on previous incremental decisions. Evaluation is performed on conversational discourse-parsing benchmarks where antecedent attachment and relation type must both be recovered.
- paper_id `doi-10-15760-mcnair-2019-13-1-2` [identity: UNCHECKED] Abstract Pronominal Anaphora in Three Registers of English (2019, PSU McNair Scholars Online Journal)
    Compares abstract pronominal anaphora across newswire, spontaneous dialogue, and planned speech. The corpus annotation explicitly marks non-nominal antecedents of it, this, and that when they refer to events, facts, propositions, or other abstract discourse entities.
- paper_id `2306.15103` [identity: VERIFIED] Structured Dialogue Discourse Parsing (2022, Proceedings of the 23rd Annual Meeting of the Special Interest Group on Discourse and Dialogue)
    Jointly predicts discourse links and corresponding relation types in multi-participant conversations. Structured encoding and decoding produce a labeled multi-root non-projective discourse structure, allowing nonlocal response dependencies rather than assuming simple adjacency.
- paper_id `manual-e4d6ad7ca1` [identity: UNCHECKED] Anaphoric Annotation in the ARRAU Corpus (2008, Proceedings of the Sixth International Conference on Language Resources and Evaluation (LREC'08))
    Introduces an anaphorically annotated corpus that explicitly represents multiple antecedents for ambiguous anaphoric expressions and discourse antecedents for references to abstract entities such as events, actions, and plans. The corpus includes task-oriented TRAINS dialogues, making its annotation model directly reusable for ambiguous or multi-unit non-nominal antecedents in dialogue.
- paper_id `doi-10-18653-v1-2021-codi-sharedtask-3` [identity: UNCHECKED] Anaphora Resolution in Dialogue: Description of the DFKI-TalkingRobots System for the CODI-CRAC 2021 Shared-Task (2021, Proceedings of the CODI-CRAC 2021 Shared Task on Anaphora, Bridging, and Discourse Deixis in Dialogue)
    Describes an anaphora-resolution system for dialogue whose discourse-deixis component detects discourse-anaphor and antecedent pairs. This component directly models links from referring expressions to prior discourse content rather than only entity coreference.
- paper_id `doi-10-3115-1219840-1219869` [identity: UNCHECKED] Scaling up from Dialogue to Multilogue: Some Principles and Benchmarks (2005, Proceedings of the 43rd Annual Meeting of the Association for Computational Linguistics)
    Examines how dialogue interpretation mechanisms scale to conversations with more than two participants. Corpus evidence on non-sentential utterances is used to study contextual resolution, including cases where the relevant antecedent is not simply the immediately preceding contribution.
- paper_id `manual-b0133009f6` [identity: UNCHECKED] The CODI-CRAC 2022 Shared Task on Anaphora, Bridging, and Discourse Deixis in Dialogue (2022, Proceedings of the CODI-CRAC 2022 Shared Task on Anaphora, Bridging, and Discourse Deixis in Dialogue)
    Describes conversational datasets and evaluation tasks for identity, bridging, and discourse deixis in dialogue. Its discourse-deixis annotations and evaluation are relevant to selecting antecedent discourse content that is propositional or otherwise non-nominal.
- paper_id `doi-10-18653-v1-2024-codi-1-15` [identity: UNCHECKED] Discourse Relation Prediction and Discourse Parsing in Dialogues with Minimal Supervision (2024, Proceedings of the 5th Workshop on Computational Approaches to Discourse (CODI 2024))
    Develops a semi-supervised pipeline that first predicts dialogue discourse structures and then discourse relations. Evaluation includes STAC and cross-domain technical chat, providing evidence about antecedent attachment in a conversational domain beyond game chat.
- paper_id `manual-9571289efd` [identity: UNCHECKED] Remarks on this and that (1974, Papers from the Tenth Regional Meeting of the Chicago Linguistic Society)
    (no abstract supplied)
- paper_id `doi-10-3115-981344-981353` [identity: UNCHECKED] Some Facts About Centers, Indexicals, and Demonstratives (1991, 29th Annual Meeting of the Association for Computational Linguistics)
    Empirically examines demonstrative and personal-pronoun reference in discourse. It shows that demonstratives can access discourse entities that are not the current local center, supporting antecedent-selection mechanisms that are not restricted to the immediately salient nominal referent.

JSON schema:
{
 "$schema": "http://json-schema.org/draft-07/schema#",
 "title": "PaperAdmission",
 "description": "Per-candidate admission decision. A paper enters the reading round only when it materially strengthens an authorized research stream; a paper count is never a reason to admit.",
 "type": "object",
 "required": [
  "decisions"
 ],
 "properties": {
  "round": {
   "type": "integer",
   "minimum": 1
  },
  "streams": {
   "type": "array",
   "description": "The authorized research streams this round admits against.",
   "items": {
    "type": "object",
    "required": [
     "id",
     "description"
    ],
    "properties": {
     "id": {
      "type": "string",
      "minLength": 1
     },
     "description": {
      "type": "string",
      "minLength": 1
     }
    }
   }
  },
  "decisions": {
   "type": "array",
   "minItems": 1,
   "items": {
    "type": "object",
    "required": [
     "paper_id",
     "decision",
     "reason"
    ],
    "properties": {
     "paper_id": {
      "type": "string",
      "minLength": 1
     },
     "decision": {
      "type": "string",
      "enum": [
       "ADMIT",
       "REJECT",
       "PENDING"
      ]
     },
     "reason": {
      "type": "string",
      "minLength": 1
     },
     "stream_id": {
      "type": "string",
      "description": "Required for ADMIT: the stream this paper materially strengthens."
     },
     "role": {
      "type": "string",
      "enum": [
       "DIRECT",
       "TRANSFER"
      ]
     },
     "confidence": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0
     }
    }
   }
  },
  "notes": {
   "type": "string"
  }
 },
 "additionalProperties": true
}

Reply with one block containing one JSON object with a `decisions` array
covering every paper_id above, and a `streams` array describing the streams
you admitted against.
===BEGIN admission.json===
<content>
===END admission.json===
