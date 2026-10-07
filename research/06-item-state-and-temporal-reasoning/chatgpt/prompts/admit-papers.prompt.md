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

Research topic: **Direct empirical NLP methods for longitudinal work-item revision in workplace or operational communication, especially relation labeling for supersession/correction/supplementation/reopening/conflict and evidence models separating claimed completion from independently corroborated completion.**

Decide which of these candidates enters the reading round. Admit a paper only
when it materially strengthens one of the research streams below, and the
abstract shows that, not merely shared vocabulary. A paper count is never a
reason to admit: admitting six of twenty is a valid answer, and so is
admitting none. Rejecting a paper here costs little; reading a paper that
cannot strengthen a stream costs a reading slot that a better paper needed.

Research streams:
- F1 [DIRECT] Longitudinal work-item revision relation classification: Classify semantic relations between successive communications about the same work item, including supersession, correction, supplementation, revocation, reopening, contradiction, and unresolved conflict, while retaining the earlier observation.
- F2 [TRANSFER] Event factuality, veridicality, modality, and speaker commitment: Infer whether a source presents an event as actual, negated, possible, intended, hypothetical, conditional, uncertain, or otherwise non-factual.
- F3 [TRANSFER] Source attribution, evidentiality, and evidence-based claim verification: Separate what a particular source asserts from what is supported by other evidence, including attribution, evidence retrieval, corroboration, and verification of claims.
- F4 [TRANSFER] Temporal relation extraction and temporal constraint reasoning: Extract and globally reason over temporal relations among events, message times, and explicit times rather than relying on surface message order.
- F5 [TRANSFER] Event evolution, temporal event aggregation, and timeline construction: Link descriptions of evolving events across documents or time and construct event-centric histories or timelines.
- F6 [TRANSFER] Contradiction, entailment, and semantic consistency between updates: Determine whether statements entail, contradict, or are compatible with one another, including contradiction detection and natural-language inference.
- F7 [TRANSFER] Dialogue commitment and belief-state tracking: Maintain conversational commitments, beliefs, dialogue variables, or public conversational state as turns accumulate and previous commitments may be revised.
- F8 [TRANSFER] Belief revision and truth-maintenance reasoning: Maintain beliefs and derivations under additions, contradictions, retractions, and alternative assumptions while retaining justification structure.
- F9 [TRANSFER] Document revision, edit-intent classification, and semantic change: Analyze successive versions of documents and classify the purpose or semantic effect of edits rather than only detecting surface differences.
- F10 [TRANSFER] Dynamic and temporal knowledge-graph update: Represent facts whose validity or relations change over time and learn or reason over temporally evolving structured knowledge.
- F11 [TRANSFER] Data provenance, immutable observations, and derived current-state views: Represent the lineage of derived facts or assessments back to source observations, often separating immutable historical records from recomputable or materialized current views.
- F12 [TRANSFER] Multi-time and bitemporal representation for changing facts: Represent facts using distinct notions such as valid/effective time and transaction/observation time, with possible extensions for utterance time and deadlines.

Open gaps this round must close (a paper that speaks to one of these
is worth admitting even when its topic wording is unusual):
- gap-1 [ACADEMIC, HIGH]: No admitted paper directly evaluates longitudinal state tracking across workplace messages in which one work item moves among requested, proposed, planned, approved, completed, revoked, superseded, disputed, conditional, and unresolved states while retaining historical assessments.
    suggested query: workplace email enterprise chat longitudinal work item lifecycle state tracking requested planned approved completed revoked superseded disputed unresolved
    searched in rounds: [1, 2, 3] (still open)
- gap-2 [ACADEMIC, HIGH]: The corpus provides formal treatments of correction, retraction, persistence, and reopening, but does not establish a natural-language method evaluated across successive operational communications for distinguishing supersession, correction, supplementation, contradiction, reopening, and unresolved conflict.
    suggested query: natural language dialogue revision relation classification supersession correction supplementation contradiction reopening unresolved conflict longitudinal
    searched in rounds: [1, 2, 3] (still open)
- gap-3 [ACADEMIC, HIGH]: No admitted paper jointly evaluates source-relative factuality, temporal ordering, lifecycle state, contradiction, and provenance as one longitudinal model; the papers validate separate components and their combination remains untested.
    suggested query: "event factuality" temporal relation contradiction provenance lifecycle longitudinal joint model
    searched in rounds: [1, 2, 3] (still open)
- gap-4 [ACADEMIC, HIGH]: Direct evidence for workplace email, Teams-like dialogue, or comparable operational communication is absent; the empirical NLP evidence is predominantly news-derived, while the commitment and belief-revision papers use formal, modeled, argumentative-dialogue, or adjacent-domain settings.
    suggested query: workplace email enterprise chat operational communication task state tracking revision factuality temporal commitment
    searched in rounds: [1, 2, 3] (still open)
- gap-5 [ACADEMIC, HIGH]: The admitted factuality literature models textual source commitment, and the fact-verification literature models corroborating evidence, but no admitted paper establishes how to distinguish an author's assertion that work is complete from independent confirmation or stronger evidential verification of completion in longitudinal operational communication.
    suggested query: dialogue event factuality evidentiality source attribution claimed completion independent confirmation corroboration longitudinal
    searched in rounds: [1, 2, 3] (still open)
- gap-6 [ENGINEERING, HIGH]: Evaluation is still needed on adversarial longitudinal sequences such as plan-to-cancel, approve-to-revoke, deadline changes, contradictory same-time updates, out-of-order ingestion, stale messages arriving late, and completion claims later corrected.
- gap-7 [ENGINEERING, HIGH]: The combined representation of message time, event/effective time, deadline or constraint time, and observed collection/version time has not been benchmarked for this product's state-resolution tasks; the temporal-database paper provides a related three-time formal account rather than such an evaluation.
- gap-8 [ENGINEERING, HIGH]: The corpus does not evaluate a provenance-preserving implementation for this state-resolution task that stores immutable source observations and successive assessments while exposing a separately derived current-state view.
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

# Topic 06 context — Work-item state, event factuality, time, and conflicting revisions

## Why this Topic exists

Knowing that an action or decision was mentioned is not enough. msgloom must know its current evidence-backed state: requested, proposed, planned, approved, completed, revoked, superseded, disputed, conditional, or still unresolved. Business communication contains future plans, retrospective reports, corrections, contradictions, changing deadlines, and statements with different effective times.

A dangerous failure is converting “we plan to send Friday” into “sent”, or treating an old approval as current after a revocation. Topic 06 therefore owns **state evolution and temporal/factual reasoning over Topic evidence**.

## Core research object

Maintain an evidence-backed timeline/state model that distinguishes:

- utterance/message time;
- event/effective time;
- deadline/constraint time;
- observed collection time/version;
- factuality/modality (planned, asserted, confirmed, negated, hypothetical, conditional);
- supersession, supplementation, contradiction, and unresolved conflict;
- current accepted assessment versus historical assessments.

The model must preserve evidence rather than overwrite history.

## Product and phase relevance

Phase 1 triage needs current-enough actions, deadlines, risks, and limitations from supplied evidence. Phase 2 investigation can obtain more history/evidence to resolve uncertain state. Reports must not present stale accepted assessments as current when newer input is pending.

## Relationships to other Topics

| Topic | Relationship |
| --- | --- |
| 03 | Stable Topic identity determines which evidence belongs in the same longitudinal state history. |
| 04 | Correct reference/response scope determines what was approved, revoked, answered, or changed. |
| 05 | Supplies extracted actions, commitments, decisions, deadlines, and conditions whose state evolves. |
| 07 | Retrieves missing evidence when current state cannot be resolved from available sources. |
| 08 | State evidence may come from document versions, tables, attachments, or screenshots. |
| 09 | Briefing must distinguish new developments from still-open state and avoid repeating superseded facts. |
| 10 | Evaluates current-state correctness, contradiction handling, evidence support, and uncertainty. |

## Key conceptual distinctions

- Mentioned event ≠ factual event.
- Planned ≠ completed.
- Asserted complete ≠ independently confirmed complete.
- Message timestamp ≠ event/effective time.
- Later message ≠ automatically superseding message.
- Contradiction ≠ supersession.
- Absence of new evidence ≠ completion.
- Correction creates a new assessment and lineage; it does not erase prior source records.

## High-value academic terminology

- event factuality prediction; factuality profiling;
- event modality; event certainty; event veridicality;
- negation detection; speculation/hedging detection;
- temporal information extraction; temporal relation extraction;
- event temporal ordering; temporal relation classification;
- TimeML / temporal graphs / temporal constraint reasoning;
- event status tracking; state tracking; dialogue state tracking (transfer only where semantics match);
- event evolution / event update / timeline extraction;
- contradiction detection; natural language inference (NLI);
- belief revision; truth maintenance systems (TMS); assumption-based truth maintenance;
- knowledge-base revision; temporal knowledge graphs;
- document/version supersession; revision tracking; change detection;
- provenance-aware state / event sourcing (engineering/background literature).

## Query families

- `"event factuality prediction" NLP`
- `event modality certainty negation speculation`
- `"temporal relation extraction" event ordering`
- `"event temporal ordering" document`
- `"event status tracking" text`
- `"belief revision" natural language evidence`
- `"truth maintenance" conflicting evidence`
- `contradiction supersession document revisions`
- `temporal knowledge graph event state update`
- `business email deadline change completion status`

## False friends / exclusions

- pure date extraction without event relation;
- Topic 05 action extraction alone;
- generic NLI benchmarks where the system is not maintaining a longitudinal state;
- latest-message-wins heuristics;
- workflow-engine state machines with no language/evidence uncertainty;
- update summarization (Topic 09), which consumes state rather than defines its truth semantics.

## Gap-evaluation guidance

Prioritize errors that can mark open work complete, resurrect superseded work, lose a changed deadline, or resolve contradictions without evidence. Prefer explicit state transitions with provenance over one opaque “current summary”. When the unresolved state is caused by missing evidence rather than reasoning limitations, hand off an evidence need to Topic 07.

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

**None of this is evidence for your own report.** It scopes your
work; it does not support a finding or a gap. Only papers this
topic admitted can do that.

# Inherited handoffs

Everything an earlier Topic explicitly handed to this one, copied in full so
that this folder is enough on its own. You do not need to open an earlier
Topic's documents to start work here.

Each entry states what was handed over, what the sending Topic still owns, and
what it had established or left open at the time. A handoff is not a finding:
where the sender left a gap open, it is still open.

## From Topic 05 — Action items, requests, commitments and decisions

*Completed 2026-09-16. 4 rounds, 48 papers, review accepted at faithfulness
0.93. Nine gaps left open, none downgraded.*

**Handed to Topic 06.** Whether an extracted commitment is later confirmed,
revoked, completed or contradicted. Topic 05 emits the **utterance-time**
semantic event — what was said, by whom, about what, with which deadline and
conditions — and explicitly does not decide whether it stays valid. Its
report states the boundary: Topic 05 should "emit utterance-time semantic
events for Topic 06 instead of deciding whether they later remain valid".

**What Topic 05 established.** Extraction quality depends jointly on act
classification and argument attachment; a correct act label with the wrong
owner or deadline is not a usable event. Context helps and also hurts:
the literature shows both gains and context-induced degradation, which is why
Topic 05 leaves the context window an open engineering question.

**What Topic 05 left open, and Topic 06 must not treat as settled:**

- *(ACADEMIC, HIGH)* Owner and assignee extraction is weakly evidenced,
  above all for implicit owners, group ownership and owners recoverable only
  from organisational context. An event arriving without a confident owner is
  the normal case, not an error.
- *(ACADEMIC, HIGH)* Deadline binding is unresolved: a date in a message is
  not necessarily that action's deadline.
- *(ACADEMIC, HIGH)* Attaching conditions, negation and modality to the right
  action when several occur together. A conditional commitment that Topic 06
  tracks as firm would be wrong from the start.

**Boundary.** Topic 06 owns state and revision over time. Topic 05 owns what
the event *is* at the moment it was uttered, and its open gaps travel with
the event.

Candidates:
- paper_id `1803.05355` [identity: VERIFIED] FEVER: a Large-scale Dataset for Fact Extraction and VERification (2018, Proceedings of the 2018 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies)
    Introduces a large fact-verification dataset containing claims labeled Supported, Refuted, or NotEnoughInfo together with evidence sentences from Wikipedia. It provides an empirical framework for separating an asserted claim from independently retrieved textual evidence used to corroborate or refute it.
- paper_id `doi-10-18653-v1-p19-1040` [identity: UNCHECKED] Evidence-based Trustworthiness (2019, Proceedings of the 57th Annual Meeting of the Association for Computational Linguistics)
    Develops probabilistic models that jointly estimate source trustworthiness and claim credibility when multiple sources make assertions and provide evidence. The framework distinguishes directly asserted claims from claims inferred through noisy NLP processing and evaluates source- and evidence-aware credibility estimation.
- paper_id `2106.05707` [identity: VERIFIED] FEVEROUS: Fact Extraction and VERification Over Unstructured and Structured information (2021, Advances in Neural Information Processing Systems, Datasets and Benchmarks Track)
    Introduces a fact-verification dataset in which claims must be checked against evidence drawn from both Wikipedia sentences and table cells. Claims receive support, refutation, or insufficient-evidence labels, enabling empirical study of corroboration across heterogeneous evidence.
- paper_id `2212.01350` [identity: VERIFIED] Improving Iterative Text Revision by Learning Where to Edit from Other Revision Tasks (2022, Proceedings of the 2022 Conference on Empirical Methods in Natural Language Processing)
    Models iterative text revision as a process that detects editable spans, predicts edit intentions, and generates revised text. It transfers supervision from related revision datasets to improve identification of where and how a document should be revised.
- paper_id `2305.13117` [identity: VERIFIED] AVeriTeC: A Dataset for Real-world Claim Verification with Evidence from the Web (2023)
    Introduces a dataset of real-world claims from fact-checking organizations with web evidence represented as question-answer pairs and textual justifications. The annotation procedure is designed to obtain sufficient contemporaneous evidence while reducing temporal leakage, supporting verification of claims against independently gathered sources.
- paper_id `manual-c1d5f8bde7` [identity: UNCHECKED] User Edits Classification Using Document Revision Histories (2012, Proceedings of the 13th Conference of the European Chapter of the Association for Computational Linguistics)
    Uses supervised learning over document revision histories to distinguish factual edits from fluency-oriented edits. Features include language-model probabilities, string similarity, part-of-speech information, named entities, and adaptive revision-history features.
- paper_id `2103.08541` [identity: VERIFIED] Get Your Vitamin C! Robust Fact Verification with Contrastive Evidence (2021, Proceedings of the 2021 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies)
    Introduces contrastive evidence derived from Wikipedia revisions in which small factual changes can alter whether evidence supports or refutes the same claim. The work explicitly treats evidence as changing over time and evaluates factual-revision detection and robust fact verification.
- paper_id `2606.18037` [identity: VERIFIED] ProvenanceGuard: Source-Aware Factuality Verification for MCP-Based LLM Agents (2026)
    Presents a source-aware verification system that decomposes generated answers into atomic claims, routes each claim to source-specific evidence, and verifies both factual support and attribution. The evaluation uses agent traces with stable source and tool identifiers and includes controlled source-attribution perturbations, directly testing whether evidence comes from the claimed source.
- paper_id `doi-10-18653-v1-2022-acl-long-250` [identity: UNCHECKED] Understanding Iterative Revision from Human-Written Text (2022, Proceedings of the 60th Annual Meeting of the Association for Computational Linguistics)
    Studies sequences of human-written revisions and introduces a corpus annotated with edit intentions across multiple domains. The work evaluates models that use distinctions among edit intentions to better understand and perform iterative text revision.
- paper_id `2210.15067` [identity: VERIFIED] arXivEdits: Understanding the Human Revision Process in Scientific Writing (2022, Proceedings of the 2022 Conference on Empirical Methods in Natural Language Processing)
    Constructs a corpus of scientific papers with multiple arXiv versions, aligns content across versions, and annotates fine-grained span edits and edit intentions. The work evaluates document, sentence, and word alignment together with automatic edit-intention classification.
- paper_id `manual-aa5656bede` [identity: UNCHECKED] Learning to Classify Email into “Speech Acts” (2004, Proceedings of the 2004 Conference on Empirical Methods in Natural Language Processing)
    Presents supervised methods for classifying email according to sender intent using an ontology containing communicative acts such as proposing, committing, delivering, and requesting. The work is motivated by tracking the status of ongoing joint activities in workplace email.
- paper_id `manual-f9b48b4c8b` [identity: UNCHECKED] One Document, Many Revisions: A Dataset for Classification and Description of Edit Intents (2022, Proceedings of the Thirteenth Language Resources and Evaluation Conference)
    Introduces a dataset based on complete Wikipedia revision histories with edit-intent labels associated with individual revisions. The paper evaluates edit-intent classification and generation of natural-language descriptions of revisions, explicitly modeling iterative revision histories rather than isolated document pairs.
- paper_id `2004.14974` [identity: VERIFIED] Fact or Fiction: Verifying Scientific Claims (2020, Proceedings of the 2020 Conference on Empirical Methods in Natural Language Processing)
    Introduces SciFact, a dataset of scientific claims paired with abstracts containing evidence that supports or refutes them and annotated rationales. The work evaluates retrieval and reasoning models that verify claims against independently selected scientific evidence.
- paper_id `1804.02472` [identity: VERIFIED] Neural Models of Factuality (2018, Proceedings of the 2018 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies)
    Develops neural models for predicting the factuality of events described in text and evaluates them on multiple factuality datasets. The models estimate source-relative textual commitment rather than independently verified truth.
- paper_id `doi-10-18653-v1-d18-1003` [identity: UNCHECKED] DeClarE: Debunking Fake News and False Claims using Evidence-Aware Deep Learning (2018, Proceedings of the 2018 Conference on Empirical Methods in Natural Language Processing)
    Presents an evidence-aware neural model for assessing claim credibility using external evidence articles, textual signals, and information about source trustworthiness. The approach explicitly separates claims from supporting or contradicting evidence gathered from other sources.
- paper_id `2007.14864` [identity: VERIFIED] How and Why is An Answer (Still) Correct? Maintaining Provenance in Dynamic Knowledge Graphs (2020)
    Studies maintenance of query-result provenance as knowledge graphs change through insertions and deletions. The proposed method preserves provenance expressions that explain why an answer remains valid or becomes affected by graph updates, providing a transferable model for non-destructive historical evidence lineage.
- paper_id `2406.19764` [identity: VERIFIED] Belief Revision: The Adaptability of Large Language Models Reasoning (2024, Proceedings of the 2024 Conference on Empirical Methods in Natural Language Processing)
    Introduces a benchmark for evaluating whether language models revise conclusions when sequentially supplied premises or evidence change. It tests delta reasoning and belief updating across evolving information rather than evaluating only a single static inference instance.
- paper_id `1909.03242` [identity: VERIFIED] MultiFC: A Real-World Multi-Domain Dataset for Evidence-Based Fact Checking of Claims (2019, Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing and the 9th International Joint Conference on Natural Language Processing)
    Introduces a multi-domain collection of real-world claims from fact-checking organizations together with textual evidence sources, metadata, and expert veracity judgments. The work evaluates models that jointly rank evidence pages and predict claim veracity.
- paper_id `doi-10-18653-v1-d13-1055` [identity: UNCHECKED] Automatically Classifying Edit Categories in Wikipedia Revisions (2013, Proceedings of the 2013 Conference on Empirical Methods in Natural Language Processing)
    (no abstract supplied)
- paper_id `2110.08222` [identity: VERIFIED] DialFact: A Benchmark for Fact-Checking in Dialogue (2022, Proceedings of the 60th Annual Meeting of the Association for Computational Linguistics)
    Introduces a benchmark for fact-checking claims made in multi-turn dialogue against external Wikipedia evidence. It evaluates claim detection, evidence retrieval, and verification into supported, refuted, or insufficient-evidence classes, providing a conversational setting in which a speaker's assertion is distinct from corroborating evidence.
- paper_id `doi-10-1016-j-jbi-2015-11-011` [identity: UNCHECKED] DREAM: Classification Scheme for Dialog Acts in Clinical Research Query Mediation (2015, Journal of Biomedical Informatics)
    Develops and empirically validates a dialog-act annotation scheme using email exchanges for clinical research data requests. The corpus contains task-oriented multi-message dialogues, and the taxonomy includes task-management and resolution states as well as backward-looking correction or suggestion acts.
- paper_id `manual-82aa610b83` [identity: UNCHECKED] MEANTIME, the NewsReader Multilingual Event and Time Corpus (2016, Proceedings of the Tenth International Conference on Language Resources and Evaluation)
    Introduces a multilingual corpus annotated for entities, events, temporal expressions, semantic roles, temporal relations, and event and entity coreference, including cross-document links. The resource supports research combining event identity and temporal organization across documents.
- paper_id `manual-d574dff39d` [identity: UNCHECKED] Email Task Management: An Iterative Relational Learning Approach (2005, Second Conference on Email and Anti-Spam)
    Studies tasks and activities distributed over multiple email messages and jointly identifies task-related messages and semantic relations between them. Its semantic analysis includes communicative categories such as Propose, Request, Deliver, Commit, and Amend, and is evaluated on real-world email corpora.
- paper_id `doi-10-18653-v1-2023-findings-acl-378` [identity: UNCHECKED] LEDA: a Large-Organization Email-Based Decision-Dialogue-Act Analysis Dataset (2023, Findings of the Association for Computational Linguistics: ACL 2023)
    Introduces a dialog-act dataset derived from real-world IETF mailing-list discussions about organizational decision making and trains transformer-based dialog-act classifiers. The annotation inventory includes action proposals, stated decisions, agreement, disagreement, information exchange, and clarification-related acts, and the analysis examines communication over the life cycle of decision discussions.
- paper_id `manual-ddcda2d78d` [identity: UNCHECKED] Fully Automated Fact Checking Using External Sources (2017, Proceedings of the International Conference Recent Advances in Natural Language Processing, RANLP 2017)
    Presents an automated fact-checking framework that searches for external sources and combines semantic text representations with estimates of source reliability. The method is evaluated on rumor detection and community question-answering fact-checking tasks.

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
