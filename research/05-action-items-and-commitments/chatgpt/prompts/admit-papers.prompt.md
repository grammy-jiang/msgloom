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

Research topic: **authentic workplace email and enterprise-chat benchmarks for structured action/decision extraction, focusing specifically on implicit and group assignees, action-to-deadline binding, condition/negation/modality scope, and exact argument evidence spans**

Decide which of these candidates enters the reading round. Admit a paper only
when it materially strengthens one of the research streams below, and the
abstract shows that, not merely shared vocabulary. A paper count is never a
reason to admit: admitting six of twenty is a valid answer, and so is
admitting none. Rejecting a paper here costs little; reading a paper that
cannot strengthen a stream costs a reading slot that a better paper needed.

Research streams:
- F1 [DIRECT] workplace email action-item and task extraction: Detect and extract actionable task content from authentic business email, preferably with span-level annotations rather than only message or sentence labels.
- F2 [DIRECT] requests-for-action and commitments-to-act in workplace email: Speech-act classification specialized to requests that impose action and commitments in which the author undertakes future action.
- F3 [DIRECT] task-person assignment and addressee tagging for email task intent: Given a detected task in email, identify which person or persons are responsible for carrying it out, including multi-recipient settings.
- F4 [DIRECT] structured decisions, proposals, approvals, and rejections in workplace email or enterprise messaging: Identify decision-related communicative acts in authentic written workplace communication and extract their actor, target proposition/action, arguments, and source spans.
- F5 [TRANSFER] meeting action-item and decision discourse modeling: Detect the discourse regions and dialogue acts through which action items and decisions are proposed, negotiated, assigned, committed to, accepted, or rejected in multi-party meetings.
- F6 [TRANSFER] span-based event and predicate argument extraction: Extract a predicate or trigger together with exact textual spans for actor, object, recipient, time, and other semantic roles.
- F7 [TRANSFER] implicit semantic role labeling and implicit argument resolution: Detect missing semantic arguments and resolve them to discourse entities when the filler is not overtly expressed with the predicate.
- F8 [TRANSFER] event-time linking and temporal anchoring: Identify semantic relations between an event and a temporal expression rather than merely recognizing or normalizing the temporal expression.
- F9 [TRANSFER] negation, speculation, and modality scope resolution: Detect modal or negation cues and identify the precise proposition, predicate, event, or token span within their semantic scope.
- F10 [TRANSFER] conditional relation and exception attachment: Identify condition-consequence, prerequisite-action, exception-action, or unless-type relations and attach the condition to the proposition it governs.
- F11 [DIRECT] span-level structured communicative-event annotation: Benchmarks that jointly annotate a communicative act or action event and exact source spans for its arguments, potentially allowing discontinuous or multiple evidence spans.
- F12 [DIRECT] authentic enterprise messaging benchmark discovery: Corpora derived from real organizational chat or business messaging systems and annotated for requests, commitments, assignments, decisions, or action items.

Open gaps this round must close (a paper that speaks to one of these
is worth admitting even when its topic wording is unusual):
- gap-1 [ACADEMIC, HIGH]: There is no direct modern workplace email/chat benchmark in this corpus that jointly annotates speech-act type, owner/assignee, action object, deadline, conditions/exceptions, and exact evidence spans.
    suggested query: "action item extraction" (email OR Slack OR "workplace chat" OR "enterprise chat") assignee deadline condition "evidence span" corpus
    searched in rounds: [1, 2, 3] (still open)
- gap-2 [ACADEMIC, HIGH]: Direct empirical evidence for extracting decisions, approvals, rejections, and proposals with structured arguments from authentic workplace email or chat is still missing from this corpus.
    suggested query: ("decision extraction" OR "decision detection" OR "proposal extraction") ("workplace email" OR "enterprise chat" OR Slack) approval rejection proposal "argument extraction"
    searched in rounds: [1, 2, 3] (still open)
- gap-3 [ACADEMIC, HIGH]: Owner/assignee extraction remains weakly evidenced, especially for implicit owners, group ownership, multiple actions with different owners, and owners recoverable only from organizational or conversation context.
    suggested query: ("assignee prediction" OR "assignee extraction" OR "responsibility extraction" OR "action owner") (email OR Slack OR "workplace chat") implicit owner group owner context
    searched in rounds: [1, 2, 3] (still open)
- gap-4 [ACADEMIC, HIGH]: The corpus does not establish reliable deadline binding in workplace communication: distinguishing a deadline for a particular action from a merely mentioned date, shared date, scheduling expression, or conditional future time remains open.
    suggested query: ("deadline extraction" OR "due date extraction" OR "deadline detection") (email OR "workplace communication" OR Slack) "action item" temporal relation event argument
    searched in rounds: [1, 2, 3] (still open)
- gap-5 [ACADEMIC, HIGH]: Direct workplace evidence is insufficient for attaching conditions, exceptions, negation, and modality to the correct action when several actions or clauses occur together.
    suggested query: ("conditional commitment" OR "deontic modality" OR "negation scope" OR "condition extraction") (email OR "workplace communication" OR Slack) action attachment obligation
    searched in rounds: [1, 2, 3] (still open)
- gap-6 [ENGINEERING, HIGH]: Build an independent argument-level benchmark and adversarial fixture suite covering implicit owners, multiple actions in one sentence, shared deadlines, conditional and negated actions, overlapping request/commitment labels, quoted-history contamination, and attachment references; score false positives, false negatives, and each argument separately.
- gap-7 [ENGINEERING, HIGH]: Compare sentence-local, message-level, and selectively expanded thread-context extraction with controlled ablations, because the literature shows both context gains and context-induced degradation.
- gap-8 [ENGINEERING, HIGH]: Test author/quoted/forwarded content zoning while preserving provenance, and measure whether zoning improves act and argument extraction without losing obligations whose interpretation depends on prior-message context.
- gap-9 [ENGINEERING, HIGH]: Evaluate an uncertainty-preserving structured output in which owner, deadline, condition, or act subtype can remain unresolved, and measure whether this reduces false obligations and wrong argument assignments without unacceptable recall loss.
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

# Topic 05 context — Action items, requests, commitments, and decisions

## Why this Topic exists

msgloom's primary success criterion is not generic summarization quality: it is avoiding missed work that requires the user's response. That requires identifying what someone is asking for, promising, deciding, approving, assigning, or expecting — including owner, object, deadline, conditions, prerequisites, and evidence.

Business language is often indirect: “Can you take a look?”, “I’ll get this over once Finance confirms”, “We should proceed”, “Approved up to 50k”, “John to send by Friday”, or “No action needed unless X happens”. A system that extracts only verbs or dates can create false obligations or lose conditions.

Topic 05 owns **the semantic extraction and classification of action/commitment/decision content**, not its later state over time.

## Core research object

Represent work-relevant speech acts/events with explicit arguments and uncertainty, for example:

```text
type: request | commitment | decision | approval | proposal | action item
actor / owner
object / target
recipient / beneficiary
status/modality at utterance time
original deadline wording + normalized time if justified
conditions / prerequisites / exceptions
source span(s)
confidence / unresolved fields
```

Missing owner or deadline must remain unknown rather than be invented to make an action executable.

## Product and phase relevance

Topic 05 directly supports Phase 1 A3 triage outputs: actions, deadlines, risks, and required responses. Phase 3 A6 later consumes accepted Topic information to prepare drafts/proposals, but Topic 05 research must not cross into executing actions. A reviewed draft is not approval.

## Direct handoffs from earlier Topics

Topic 04 (completed 2026-09-16, 47 papers, 4 rounds) resolved **what a response is about**: the exact proposition, question or request an approval, rejection, answer or commitment applies to, including partial and multi-antecedent scope. It explicitly does **not** classify the act itself. Topic 05 owns the speech-act label and takes the antecedent scope as given. Topic 04's open ACADEMIC gap 1 is directly relevant: direct empirical evidence for proposition-level approval, rejection and agreement scope in authentic workplace mail or chat is still missing, so a Topic 05 act label must not be read as evidence that its scope is correct.

**The full text of every inherited handoff is in [`INHERITED_HANDOFFS.md`](INHERITED_HANDOFFS.md)**, including what each sending Topic established, what it left open, and where the ownership boundary lies. Read it before planning; you do not need to open an earlier Topic's folder.

## Relationships to other Topics

| Topic | Relationship |
| --- | --- |
| 02 | Supplies correct Topic scope so extracted actions/conditions attach to the right work matter. |
| 04 | Resolves what “approved”, “agreed”, or “please do that” refers to before Topic 05 interprets the speech act/action. |
| 06 | Topic 05 extracts the event/commitment; Topic 06 tracks whether it is planned, confirmed, revoked, completed, contradicted, etc. |
| 07 | Missing owner/object/context can become an explicit retrieval gap in Phase 2. |
| 08 | Action evidence may live in attachments/tables/screenshots; Topic 08 supplies grounded content. |
| 09 | Briefing uses action/deadline/decision outputs to decide what must remain visible. |
| 10 | Reliability evaluation checks evidence support and missed actions; generic calibration belongs there. |

## Key conceptual distinctions

- Request ≠ commitment.
- Proposal/intention ≠ decision.
- Mentioned action ≠ assigned action item.
- Capability (“can do”) ≠ promise (“will do”).
- Conditional commitment ≠ unconditional commitment.
- Deadline mention ≠ deadline for this action.
- Owner inferred from context must remain distinguished from explicitly stated owner.
- Extracting an action is not the same as determining its later state (Topic 06).

## High-value academic terminology

- action item extraction / detection;
- task extraction; to-do extraction; task-oriented information extraction;
- email speech act classification; dialogue act classification;
- request detection / request identification;
- commissive speech acts; commitment extraction/detection;
- promise detection; obligation detection; deontic modality;
- intention detection; intent-to-act;
- decision extraction / decision detection; meeting decision detection;
- event extraction; event argument extraction; semantic role labeling;
- implicit argument resolution; zero anaphora / omitted argument recovery (transfer);
- conditionality detection; hedge/speculation/modality detection;
- temporal expression extraction and normalization; deadline extraction;
- responsibility/owner assignment; assignee extraction;
- email action-item / request-response corpora.

## Query families

- `"action item extraction" email`
- `"task extraction" business email`
- `email "speech act classification" request commitment`
- `"commitment detection" dialogue email`
- `"commissive" speech act NLP commitment`
- `"decision extraction" meeting email`
- `"event argument extraction" implicit argument owner`
- `"deontic modality" obligation NLP`
- `deadline extraction email temporal normalization`
- `conditional commitment detection NLP`
- `request detection workplace communication`

## False friends / exclusions

- generic intent classification with no action arguments;
- calendar/event extraction that treats every date as a deadline;
- sentiment or urgency classification;
- Topic 06 factuality/state tracking;
- recommendation generation / drafting (Phase 3 A6);
- action execution / tool invocation (Phase 4 A7).

## Gap-evaluation guidance

Give highest priority to gaps that cause missed user-response obligations, false obligations, wrong owners, wrong deadlines, or lost conditions. Evaluate argument-level preservation rather than only speech-act accuracy. Direct business-email evidence is especially valuable, but strong transfer evidence from meetings/dialogue can justify representations or experiments if labeled as transfer. Engineering tests should include implicit owner, multiple actions in one sentence, shared deadlines, conditional/negated actions, and ambiguous references resolved by Topic 04.

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

## Work handed to this topic by an earlier one

Treat each entry as a starting condition, not as something to
rediscover. Where a sending topic left a gap open it is still open:
do not report it as established. Respect the stated ownership
boundary and do not absorb what the sender still owns.

# Inherited handoffs

Everything an earlier Topic explicitly handed to this one, copied in full so
that this folder is enough on its own. You do not need to open an earlier
Topic's documents to start work here.

Each entry states what was handed over, what the sending Topic still owns, and
what it had established or left open at the time. A handoff is not a finding:
where the sender left a gap open, it is still open.

## From Topic 04 — Reference resolution and response scope

*Completed 2026-09-16. 4 rounds, 47 papers, report validated PASS,
faithfulness 0.91. Five gaps left open, none downgraded.*

**Handed to Topic 05.** Topic 04 resolves **what a response is about**: the
exact proposition, question or request that an approval, rejection, answer or
commitment applies to, including partial scope and links to several
antecedents at once. It explicitly does not classify the act. Topic 05 owns
the speech-act label and takes the antecedent scope as given.

**What Topic 04 established.** Direct evidence for multi-question partial
replies is materially stronger than for the other scope questions. Response
scope is routinely partial: a reply commonly addresses some propositions in a
message and leaves others unresolved, and systems that force one
message-level label lose that distinction.

**What Topic 04 left open, and that Topic 05 must not treat as settled:**

- *(ACADEMIC, HIGH)* Direct empirical evidence for exact proposition-level
  agreement, rejection, approval, clarification and answer scope in authentic
  workplace email or enterprise chat is still missing. **A Topic 05 act label
  must therefore not be read as evidence that its scope is correct.**
- *(ACADEMIC, HIGH)* Workplace messages that mix questions, requests,
  alternatives and conditions are not yet validated together with complete
  unresolved-subquestion detection. Missing mixed-act validation can cause
  open work to be closed incorrectly, which is directly a Topic 05 risk.
- *(ACADEMIC, MEDIUM)* Whether a response independently targets several
  propositions or targets one composite object is unresolved. This affects
  how many action items one reply should produce.

**Boundary.** If Topic 05 finds itself deciding which proposition an action
applies to, that is Topic 04's question and its evidence, including its open
gaps, applies.

Candidates:
- paper_id `2305.13469` [identity: VERIFIED] MailEx: Email Event and Argument Extraction (2023, EMNLP 2023)
    Introduces MailEx, an event-extraction dataset built from conversational email threads with a taxonomy of 10 event types and 76 argument roles. The dataset contains roughly 1.5K threads, 4K emails, and 8K event instances, and exposes challenges including non-contiguous or shared triggers, non-named-entity arguments, and dependence on conversational history.
- paper_id `doi-10-1145-3594536-3595162` [identity: UNCHECKED] Computable Contracts by Extracting Obligation Logic Graphs (2023, ICAIL 2023)
    Explores extraction of obligation logic graphs from natural-language contracts to support computable representations of obligations. The work includes modeling of complex conditions, making it transferable to structured action-plus-condition extraction even though the source domain is legal rather than workplace communication.
- paper_id `2109.09393` [identity: VERIFIED] Modality and Negation in Event Extraction (2021, CASE 2021)
    Presents an event extraction system that explicitly represents multiple kinds of modality and negation so that non-actual events are not treated as ordinary factual events. Its political-news setting makes it transfer rather than workplace evidence, but it directly connects modality information to extracted events.
- paper_id `1606.07965` [identity: VERIFIED] Summarizing Decisions in Spoken Meetings (2011, Workshop on Automatic Summarization for Different Genres, Media, and Languages)
    Studies generation of a concise decision abstract for each decision in a spoken meeting using token-level and dialogue-act-level methods. Because it targets the content of individual decisions rather than merely labeling a meeting as decision-related, it provides transfer evidence for extracting decision propositions, although the source is spoken meetings rather than email or enterprise chat.
- paper_id `doi-10-18653-v1-d17-1108` [identity: UNCHECKED] A Structured Learning Approach to Temporal Relation Extraction (2017, EMNLP 2017)
    Treats event temporal relation extraction as a structured prediction problem in which relations among other events constrain a target pair. The approach directly addresses global consistency and missing relations, properties relevant to binding a time expression or deadline to the correct action among several actions.
- paper_id `2104.05919` [identity: VERIFIED] Document-Level Event Argument Extraction by Conditional Generation (2021, NAACL 2021)
    Formulates document-level event argument extraction as conditional generation and introduces WikiEvents with complete event and coreference annotation. It also evaluates informative argument extraction, a harder setting requiring implicit coreference reasoning to recover useful argument mentions.
- paper_id `doi-10-18653-v1-n18-1076` [identity: UNCHECKED] Implicit Argument Prediction with Event Knowledge (2018, NAACL 2018)
    Addresses prediction of implicit arguments that are not syntactically connected to their predicates. The approach incorporates event knowledge, narrative coherence, and entity salience and is evaluated on both synthetic and naturally occurring implicit arguments.
- paper_id `doi-10-18653-v1-2025-naacl-long-295` [identity: UNCHECKED] BEMEAE: Moving Beyond Exact Span Match for Event Argument Extraction (2025, NAACL 2025)
    Examines limitations of exact-span-match evaluation for event argument extraction by evaluating nine models on RAMS and GENEVA. It introduces BEMEAE, which supplements deterministic matching with semantic equivalence and is reported to align more closely with human judgments, making the paper useful for designing evidence-span evaluation protocols.
- paper_id `doi-10-18653-v1-2022-findings-naacl-187` [identity: UNCHECKED] Textual Entailment for Event Argument Extraction: Zero- and Few-Shot with Multi-Source Learning (2022, Findings of NAACL 2022)
    Recasts event argument extraction as textual entailment and evaluates transfer between ACE and WikiEvents. The method reduces dependence on a single event schema and provides evidence for transferring structured argument extraction across domains with limited target annotation.
- paper_id `1911.03766` [identity: VERIFIED] Multi-Sentence Argument Linking (2020, ACL 2020)
    Introduces RAMS and a document-level model for finding argument spans that fill event roles across sentence boundaries. RAMS contains 9,124 annotated events spanning 139 event types and directly evaluates cross-sentence argument linking.
- paper_id `2311.09105` [identity: VERIFIED] MAVEN-ARG: Completing the Puzzle of All-in-One Event Understanding Dataset with Event Argument Annotation (2024, ACL 2024)
    Extends MAVEN with exhaustive document-level event-argument annotations, creating an integrated benchmark for event detection, argument extraction, and event relations. It covers 162 event types, 612 argument roles, 98,591 events, and 290,613 entity and non-entity arguments.
- paper_id `doi-10-1162-coli-a-00236` [identity: UNCHECKED] Inducing Implicit Arguments from Comparable Texts: A Framework and Its Applications (2015, Computational Linguistics)
    Develops a framework for inducing implicit semantic arguments from comparable texts and applies it to implicit argument processing. It provides transferable mechanisms for recovering participants that are not overtly expressed with the predicate.
- paper_id `2310.05991` [identity: VERIFIED] Enhancing Document-level Event Argument Extraction with Contextual Clues and Role Relevance (2023, Findings of ACL 2023)
    Introduces a document-level event argument extraction model that uses non-argument contextual clues and dependencies among argument roles. Its span-trigger contextual pooling explicitly relates candidate argument spans to event triggers and is evaluated on RAMS and WikiEvents.
- paper_id `2005.06579` [identity: VERIFIED] Document-Level Event Role Filler Extraction using Multi-Granularity Contextualized Encoding (2020, ACL 2020)
    Studies document-level event role-filler extraction where evidence needed for an argument can occur across multiple sentences. The model identifies textual spans for event roles using context represented at multiple granularities and is evaluated on MUC-4.
- paper_id `doi-10-18653-v1-s15-1005` [identity: UNCHECKED] Combining Seemingly Incompatible Corpora for Implicit Semantic Role Labeling (2015, *SEM 2015)
    Studies how differently annotated resources can be combined for implicit semantic role labeling. The paper is relevant to owner recovery because the target roles may need to be resolved from discourse rather than from an overt sentence-local argument.
- paper_id `doi-10-18653-v1-w19-5929` [identity: UNCHECKED] TDDiscourse: A Dataset for Discourse-Level Temporal Ordering of Events (2019, SIGDIAL 2019)
    Extends TimeBank-Dense with manually annotated temporal relations between events separated by more than one sentence. The benchmark specifically targets document-level temporal reasoning where local syntactic proximity is insufficient.
- paper_id `doi-10-63317-2kaxd8nu44bx` [identity: UNCHECKED] MUC-4 Revisited: Document-level Event Analysis beyond Span-based Arguments (2026, LREC 2026)
    Revisits the full original MUC-4 task rather than only its commonly used span-extraction subset. The formulation combines textual arguments with normalized, inferred, and categorical event information such as actor identities, temporal scope, and aggregated outcomes, and evaluates generative document-level models.
- paper_id `doi-10-1162-coli-a-00110` [identity: UNCHECKED] Semantic Role Labeling of Implicit Arguments for Nominal Predicates (2012, Computational Linguistics)
    Introduces a manually annotated corpus of implicit arguments for ten NomBank predicates and studies automatic recovery of arguments that are absent from the predicate's local syntactic context. The work provides direct empirical methodology for discourse-context recovery of omitted semantic participants.
- paper_id `doi-10-26615-978-954-452-092-2-076` [identity: UNCHECKED] Reading between the Lines: Information Extraction from Industry Requirements (2023, RANLP 2023)
    Defines each natural-language industry requirement in terms of scope, condition, and demand and introduces sequence-labeling and few-shot baselines for extracting those semantic components. The paper identifies implicit scope as a major challenge and shows that document context helps its recovery, making it particularly relevant to condition attachment and omitted arguments.
- paper_id `1804.07828` [identity: VERIFIED] A Multi-Axis Annotation Scheme for Event Temporal Relations (2018, ACL 2018)
    Proposes a multi-axis scheme for annotating temporal relations among events and simplifies relation judgments by focusing on event start points. The resulting MATRES-style annotation methodology is transferable to explicit action-to-time relation annotation rather than proximity-based date assignment.
- paper_id `doi-10-18653-v1-n16-1173` [identity: UNCHECKED] Unsupervised Learning of Prototypical Fillers for Implicit Semantic Role Labeling (2016, NAACL 2016)
    Investigates unsupervised learning of prototypical role fillers for implicit semantic role labeling. It offers a transferable approach for predicting semantically expected participants when arguments are omitted from the immediate predicate context.
- paper_id `doi-10-18653-v1-2022-findings-naacl-202` [identity: UNCHECKED] EA²E: Improving Consistency with Event Awareness for Document-Level Argument Extraction (2022, Findings of NAACL 2022)
    Models consistency of a participant's argument roles across multiple related events in the same document. The Event-Aware Argument Extraction model uses event-event context and is evaluated on WikiEvents and ACE2005, making it relevant to multi-action ownership and role consistency.
- paper_id `doi-10-1162-tacl-a-00182` [identity: UNCHECKED] Dense Event Ordering with a Multi-Pass Architecture (2014, Transactions of the Association for Computational Linguistics)
    Studies temporal ordering over densely connected event graphs and introduces a sieve architecture in which earlier high-precision temporal decisions constrain later ones through transitive closure. It provides transfer evidence for globally consistent temporal binding when many events coexist in a document.
- paper_id `doi-10-1007-s10579-009-9089-9` [identity: UNCHECKED] FactBank: a corpus annotated with event factuality (2009, Language Resources and Evaluation)
    Adds event-factuality annotations to TimeBank, representing whether mentioned events are presented as actual, non-occurring, or uncertain. The corpus is designed around the interaction of multiple linguistic factuality markers and provides transfer evidence for distinguishing asserted actions from negated, uncertain, or otherwise non-factual events.
- paper_id `2005.00242` [identity: VERIFIED] TORQUE: A Reading Comprehension Dataset of Temporal Ordering Questions (2020, EMNLP 2020)
    Introduces a temporal-reasoning benchmark whose questions require determining relationships among events, including relations not stated explicitly. It provides transfer evidence for contextual temporal reasoning rather than assigning times solely from surface proximity.

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
