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

Research topic: **Direct empirical evaluations of longitudinal cross-thread workplace briefing: cycle-by-cycle new/open/resolved/superseded work-item tracking, obligation-versus-preference selection, adaptive personalization under preference drift, and joint omission/repetition/false-alert evaluation.**

Decide which of these candidates enters the reading round. Admit a paper only
when it materially strengthens one of the research streams below, and the
abstract shows that, not merely shared vocabulary. A paper count is never a
reason to admit: admitting six of twenty is a valid answer, and so is
admitting none. Rejecting a paper here costs little; reading a paper that
cannot strengthen a stream costs a reading slot that a better paper needed.

Research streams:
- F1 [TRANSFER] Update, temporal, and stream summarization: Summarize an evolving information stream relative to information already seen, emphasizing changes and controlling repetition across time.
- F2 [TRANSFER] Novelty detection and redundancy control: Identify information that is new relative to prior material and suppress duplicate or redundant content.
- F3 [TRANSFER] Temporal event structure, event threading, and timeline construction: Represent evolving topics as ordered events, event dependencies, or timelines instead of flat document collections.
- F4 [TRANSFER] Query-focused and coverage-constrained multi-document content selection: Select information across multiple documents according to an explicit information need while controlling coverage, redundancy, and output constraints.
- F5 [DIRECT] Workplace email triage, prioritization, and task management: Study how workers prioritize, organize, act on, defer, and manage tasks represented in email, including urgency and importance signals.
- F6 [DIRECT] Attention-sensitive alerting and notification utility: Decide which messages or alerts merit attention by balancing urgency or delayed-review cost against interruption and false-alert cost.
- F7 [DIRECT] Task reminders, prospective memory, and forgetting-sensitive support: Study systems that help users remember intended actions and determine when reminders are useful, mistimed, stale, or unnecessary.
- F8 [TRANSFER] Personalized summarization and user-model-conditioned selection: Select or summarize information based on user interests, profiles, feedback, knowledge, or inferred information needs.
- F9 [TRANSFER] Adaptive user modeling, online personalization, and preference drift: Maintain user models that change over time as goals, expertise, roles, preferences, behavior, or feedback evolve, including online and non-stationary learning formulations.
- F10 [TRANSFER] Long-running and incremental conversation summarization: Maintain summaries of growing conversations, meetings, or dialogues while preserving decisions, actions, entities, and prior context.
- F11 [DIRECT] Cross-thread, activity-centric, and work-item-centric workplace aggregation: Treat tasks, projects, activities, or work matters rather than individual messages as the organizing unit across multiple communications.
- F12 [TRANSFER] Hard-constraint versus soft-preference ranking and selection: Selection or ranking in which mandatory constraints, rules, or feasibility requirements are distinguished from defeasible preferences or learned utility.
- F13 [TRANSFER] Uncertainty, staleness, conflict, and incomplete-information presentation: Represent and communicate uncertainty, stale data, conflicting evidence, missing information, or provisional status to decision makers.
- F14 [TRANSFER] Joint longitudinal coverage, omission, repetition, and false-alert evaluation: Evaluate repeated outputs over time for missed important information, unnecessary repetition, spurious inclusion or alerts, and persistence of unresolved state.

Open gaps this round must close (a paper that speaks to one of these
is worth admitting even when its topic wording is unusual):
- gap-1 [ACADEMIC, HIGH]: This corpus does not directly evaluate a longitudinal workplace briefing that, across successive report cycles, distinguishes newly changed information from unchanged-but-still-open work while suppressing resolved or superseded information.
    suggested query: "incremental summarization" longitudinal workplace email briefing "open" resolved superseded state
    searched in rounds: [1, 2, 3] (still open)
- gap-2 [ACADEMIC, HIGH]: This corpus does not establish how explicit user rules or response obligations interact with softer personalized importance, triage, reminder-value, or forgetting signals in briefing selection, nor whether separating these signal classes improves outcomes.
    suggested query: "email prioritization" "response obligation" hard constraints soft preferences personalized triage reminder
    searched in rounds: [1, 2, 3] (still open)
- gap-3 [ACADEMIC, HIGH]: Long-term adaptation to changing user roles, projects, priorities, feedback, and work patterns is not directly evaluated in the admitted personalized workplace email or reminder studies.
    suggested query: "longitudinal personalization" workplace email preference drift adaptive prioritization user feedback
    searched in rounds: [1, 2, 3] (still open)
- gap-4 [ACADEMIC, HIGH]: The corpus does not provide an end-to-end evaluation of briefing content selection that jointly measures omission of decision-essential work, redundant repetition, false alerts, and preservation of unresolved important state over repeated cycles.
    suggested query: "longitudinal summarization" omission redundancy false alerts unresolved state evaluation
    searched in rounds: [1, 2, 3] (still open)
- gap-5 [ACADEMIC, MEDIUM]: The admitted studies do not determine how reminder usefulness or likelihood of forgetting combines with perceived importance, urgency, recency, or personalized priority when selecting content for a briefing.
    suggested query: "email reminder" forgetting importance urgency recency personalized priority task selection
    searched in rounds: [1, 2, 3] (still open)
- gap-6 [ACADEMIC, HIGH]: No admitted paper evaluates topic- or work-item-level incremental briefing across multiple workplace conversations and sources; direct email summarization remains primarily thread- or conversation-level, while incremental evidence comes from transfer domains.
    suggested query: "cross-thread summarization" email multi-source incremental "work item" workplace
    searched in rounds: [1, 2, 3] (still open)
- gap-7 [ACADEMIC, HIGH]: Although the corpus contains evidence about stale reminders, epistemic uncertainty, and conflicting cues, it does not experimentally establish how a workplace briefing presents stale, uncertain, disputed, or incompletely investigated state, or how alternative presentations affect workplace decisions.
    suggested query: "uncertainty visualization" workplace decision support stale disputed incomplete information briefing
    searched in rounds: [1, 2, 3] (still open)
- gap-8 [ENGINEERING, HIGH]: Candidate mechanisms from this corpus have not been compared in one reproducible cycle-based benchmark with chronological holdouts, independently labeled new/open/resolved/superseded state, user-specific priority labels, and explicit omission and repetition errors.
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

# Topic 09 context — Incremental, personalized, and priority-aware briefings

## Why this Topic exists

msgloom's final user-facing value is not a database of extracted facts; it is a briefing that lets one user keep up with important work with much less reading. The briefing must show **new developments** without repeating everything, while still carrying forward unresolved important work, actions, deadlines, conditions, and risks. It must reflect the user's Triage rules and working context without confusing likelihood of response with obligation to respond.

Topic 09 therefore owns **how accepted Topic information is selected, updated, prioritized, and summarized for the user over time**.

## Core research object

For each report cycle and Topic, determine:

- what changed since the user's previous accepted view;
- what remains open/important even if unchanged;
- what evidence/context is necessary to understand the change;
- what can be omitted as redundant without losing decision value;
- how Triage rules and working context affect ordering/priority;
- how uncertainty/pending investigation should be displayed.

The overview must cover every due Topic; summary compression must not remove essential content.

## Product and phase relevance

Phase 1 A5 already delivers email reports from accepted triage results. Phase 2 adds investigation findings and a navigable website, but reporting must remain useful even when investigation is incomplete. Topic 09 informs report-content selection and presentation; it does not own external action execution.

## Relationships to other Topics

| Topic | Relationship |
| --- | --- |
| 02 | Supplies correctly scoped within-message Topic evidence. |
| 03 | Supplies stable Topic identity so updates are compared against the same work matter rather than title similarity. |
| 04 | Supplies correct response/antecedent scope. |
| 05 | Supplies actions, deadlines, requests, commitments, decisions. |
| 06 | Supplies current state, supersession, temporal ordering, unresolved conflicts. |
| 07 | Investigation may add evidence, but report generation must not wait indefinitely; unresolved gaps can be shown. |
| 08 | Supplies grounded attachment/table/image evidence. |
| 10 | Evaluates factuality, attribution, completeness, omission, calibration, and report coverage. |

## Key conceptual distinctions

- Novel information ≠ important information.
- Unchanged but unresolved critical work must remain visible.
- Response probability ≠ response obligation.
- Summary brevity ≠ permissible omission.
- Update summarization ≠ merely diffing text.
- Personalization must not override explicit Triage rules.
- Topic summary ≠ list of message summaries.
- Report completeness is by Topic identity/version and essential content, not item counts.

## High-value academic terminology

- update summarization; incremental summarization;
- temporal summarization; timeline summarization;
- query-focused summarization; query-focused multi-document summarization;
- multi-document summarization; entity/event-centric summarization;
- topic-focused summarization; case-centric/work-item summarization;
- novelty detection / redundancy reduction in summarization;
- information update / delta summarization;
- personalized summarization; user-adaptive summarization;
- personalized ranking; learning to rank; preference-aware ranking;
- email prioritization / email triage;
- task/response priority prediction (carefully distinguished from obligation);
- salience estimation / content selection;
- coverage-aware summarization; constrained summarization;
- long-running conversation summarization / incremental dialogue summarization.

## Query families

- `"update summarization" multi-document`
- `"incremental summarization" evolving documents`
- `"temporal summarization" events`
- `"query-focused multi-document summarization"`
- `"topic-focused summarization" conversation`
- `novelty redundancy update summarization`
- `"personalized summarization" user preferences`
- `"email prioritization" triage`
- `"email triage" learning to rank`
- `unresolved action update summarization`
- `coverage-aware summarization important information`
- `incremental dialogue summarization unresolved tasks`

## False friends / exclusions

- generic message-level summarization with no stable Topic identity;
- pure novelty detection that drops unchanged open work;
- response-likelihood models treated as obligation classifiers;
- popularity/recommendation ranking;
- summarization evaluations focused only on fluency/ROUGE without decision-essential coverage;
- action drafting/execution (Phases 3/4).

## Gap-evaluation guidance

The first metric is **missed important work or evidence that would change a decision**, not average summary similarity. Prioritize research that helps prove coverage of due Topics, actions, deadlines, risks, and unresolved state while reducing redundancy. Evaluate both omission and false-alert/over-reporting costs. Personalization must remain subordinate to explicit user rules and source evidence.

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

## From Topic 06 — Work-item state, event factuality, time, conflicting revisions

*Completed 2026-09-17. 4 rounds, 38 papers, no duplicate records. Every
round's synthesis was accepted by the independent review at the first attempt
— faithfulness 0.93 to 0.95 — which no earlier Topic managed. Stopped on
`round_cap_reached`. All eight gaps remain open and none was downgraded.*

**Handed to Topic 09.** What counts as a *new development* rather than a
restatement, and which facts have been superseded and must not be repeated.
Topic 06 owns the state and its revision history; Topic 09 owns deciding what
of it is worth telling the user now.

**What Topic 06 established.** A work item's state evolves through requested,
proposed, planned, approved, completed, revoked, superseded, disputed,
conditional and unresolved, and the historical assessments must be kept, not
overwritten. A briefing that reports only the latest message therefore risks
both repeating superseded facts and hiding an item that is still open.

**What Topic 06 left open, and Topic 09 must not treat as settled:**

- *(ACADEMIC, HIGH, Gap 1)* No direct evaluation of multi-state lifecycle
  tracking across successive workplace messages while preserving historical
  assessments. The state Topic 09 receives is not a measured quantity.
- *(ACADEMIC, HIGH, Gap 5)* A "completed" state may be claimed rather than
  corroborated. A briefing that drops an item because it looks finished may
  be dropping work that still needs action — Topic 06 names this as the
  failure mode to fear.
- *(ENGINEERING, HIGH, Gap 6)* Cancellation, revocation, deadline change,
  late ingestion, same-time contradiction and corrected completion have never
  been measured end to end. These are exactly the transitions a briefing must
  surface.

**Boundary.** Topic 09 owns selection, priority and phrasing over time.
Topic 06 owns what the state is and what changed, including the admission
that it is unresolved.

*Basis: the ownership map — Topic 06's relationship table entry for 09
("briefing must distinguish new developments from still-open state and avoid
repeating superseded facts") — plus Topic 06's Gaps 1, 5 and 6. Topic 06's
report does not name Topic 09 by number.*

## From Topic 08 — Email, image, table and attachment understanding

*Completed 2026-09-17. 4 rounds, 53 corpus records — **52 distinct papers**,
because one study was admitted twice under two identifiers. Rounds 2 and 4
were each rejected once and accepted after one repair; rounds 1 and 3 passed
at the first attempt. Stopped on `round_cap_reached`. All eight gaps remain
open and none was downgraded.*

**Handed to Topic 09.** Critical structured evidence that a briefing must
preserve rather than flatten. A number in a table cell, a highlighted row, a
figure or an attachment version can carry the decision-relevant content, and
summarising only body text drops it.

**What Topic 08 established.** Flattening a document into plain text loses
relationships, units, coordinates, visual emphasis and version identity.
Structure- or visually enriched representations outperform lossy OCR or
plain-text pipelines in the settings tested. A briefing built on flattened
text inherits those losses.

**What Topic 08 left open, and Topic 09 must not treat as settled:**

- *(ACADEMIC, HIGH, gap-2)* Direct grounding of workplace-message referring
  expressions — "this screenshot", "the highlighted row", "numbers below" —
  is not established. A briefing that repeats such a phrase may be repeating
  a pointer nothing has resolved.
- *(ACADEMIC, HIGH, gap-3)* Comprehensive spreadsheet understanding is open
  for formulas, hidden rows and sheets, cross-sheet references and merged
  cells. A figure lifted from a workbook may not mean what it appears to.
- *(ENGINEERING, HIGH, gap-8)* No single evaluation measures semantic
  correctness, extraction completeness, exact provenance and
  unsupported-evidence handling together. Briefing completeness therefore
  cannot be inferred from extraction success.

**Boundary.** Topic 09 owns what is worth telling the user and when.
Topic 08 owns what the structured evidence says and where it came from.

*Basis: the ownership map — Topic 08's relationship table entry for 09
("briefing must preserve critical structured evidence rather than summarizing
only body text") — plus Topic 08's gaps 2, 3 and 8. The report does not name
Topic 09 by number.*

Candidates:
- paper_id `doi-10-1145-1242572-1242586` [identity: UNCHECKED] Summarizing Email Conversations with Clue Words (2007, WWW 2007)
    The paper proposes an email-conversation summarization framework using quotation structure and clue words to estimate sentence importance. It empirically evaluates summarization of threaded email conversations, providing direct workplace-email evidence at the single-conversation level.
- paper_id `doi-10-3758-s13423-026-02985-6` [identity: UNCHECKED] Let it go: How trusted reminders alter intention maintenance (2026, Psychonomic Bulletin & Review)
    The study crosses reminder reliability with reminder availability to test whether trusted external reminders merely duplicate internal intention maintenance or replace it. Thought probes track whether intentions remain in conscious awareness, providing empirical evidence about how reminder reliability changes ongoing maintenance of future tasks.
- paper_id `doi-10-18653-v1-2020-acl-main-122` [identity: UNCHECKED] Examining the State-of-the-Art in News Timeline Summarization (2020, ACL 2020)
    The paper systematically compares timeline-summarization strategies with full-task evaluation frameworks and introduces a larger benchmark spanning longer time periods. It provides empirical evidence about temporal coverage, date selection, and redundancy in evolving news timelines.
- paper_id `2201.01534` [identity: VERIFIED] Reinforcement Online Learning to Rank with Unbiased Reward Shaping (2022, Information Retrieval Journal)
    The paper develops an online learning-to-rank method that continuously learns from user interactions while correcting position bias through inverse-propensity-based reward shaping. Empirical evaluation on standard OLTR datasets tests effectiveness and user-experience metrics under ongoing interaction.
- paper_id `doi-10-1145-564376-564393` [identity: UNCHECKED] Novelty and Redundancy Detection in Adaptive Filtering (2002, SIGIR 2002)
    The work extends adaptive information filtering by explicitly and separately modeling relevance and redundancy. Five redundancy measures are experimentally evaluated, providing transfer evidence for distinguishing useful new information from repeated material in a temporal stream.
- paper_id `2609.02465` [identity: VERIFIED] Can Risk-Based Alerting Mitigate Cybersecurity Alert Fatigue? (2026)
    The paper reformulates risk-based cybersecurity alerting as continuous prioritization and systematically evaluates alternative risk hypotheses across eight alert datasets. Its threshold-spanning evaluation directly examines the trade-off between reducing false alerts and retaining important incidents under differing review capacities.
- paper_id `doi-10-1145-62266-62293` [identity: UNCHECKED] More Than Just a Communication System: Diversity in the Use of Electronic Mail (1988, CSCW 1988)
    An empirical study of professional email users identifies distinct work-management strategies including prioritizing incoming messages, archiving information, and delegating work. The findings argue that email systems need flexible support for heterogeneous user practices and preferences.
- paper_id `manual-7069f4e108` [identity: UNCHECKED] Novelty Detection: The TREC Experience (2005, HLT-EMNLP 2005)
    This empirical analysis of the TREC novelty task studies identification of relevant new information in ordered topical document streams. It reports differences between human and system selections and finds that tracking novel opinions is harder than tracking events.
- paper_id `doi-10-2196-43977` [identity: UNCHECKED] Effect of Personalized Email-Based Reminders on Participants’ Timeliness in an Online Education Program: Randomized Controlled Trial (2023, JMIR Formative Research)
    A randomized crossover study with adult professional learners compares personalized weekly email reminders with general reminders. Personalized reminders incorporate each participant's prior progress and produced higher probability of being on time, providing empirical transfer evidence for personalized reminder content over repeated cycles.
- paper_id `2302.06648` [identity: VERIFIED] That Escalated Quickly: An ML Framework for Alert Prioritization (2023)
    The paper presents a machine-learning framework for predicting alert- and incident-level actionability in security operations. Evaluation on real-world operational data measures both false-positive suppression and preservation of actionable incidents, making it useful transfer evidence for joint false-alert and omission trade-offs in high-volume workplace alerting.
- paper_id `2106.00829` [identity: VERIFIED] ConvoSumm: Conversation Summarization Benchmark and Improved Abstractive Summarization with Argument Mining (2021, ACL-IJCNLP 2021)
    The paper creates conversation-summarization datasets spanning several domains, including email threads, and benchmarks abstractive models with automatic and human evaluation. It also evaluates argument-mining structures that explicitly represent issues, viewpoints, and assertions.
- paper_id `manual-57f93e2aef` [identity: UNCHECKED] Overview of the TREC 2002 Novelty Track (2003, TREC 2002 / NIST Special Publication 500-251)
    The TREC novelty track evaluates systems that, given an ordered set of relevant documents, identify sentences that are both relevant and novel relative to information already encountered. Thirteen groups participated in the initial evaluation.
- paper_id `doi-10-1080-17470218-2011-651091` [identity: UNCHECKED] Prospective memory reminders: A laboratory investigation of initiation source and age effects (2012, Quarterly Journal of Experimental Psychology)
    Young and older adults complete prospective-memory tasks under no-reminder, self-initiated-reminder, and experimenter-initiated-reminder conditions. The experiments test whether reminders improve remembering and whether effectiveness depends on source, task type, or age.
- paper_id `2403.19795` [identity: VERIFIED] Learning Human Preferences Over Robot Behavior as Soft Planning Constraints (2024)
    The paper distinguishes required behavior from merely desired behavior by representing user preferences as soft planning constraints rather than collapsing all considerations into one scalar utility. Simulated experiments examine inference of several preference types under noisy user choices, providing transfer evidence for separating mandatory requirements from defeasible preferences.
- paper_id `doi-10-1016-j-ipm-2007-03-012` [identity: UNCHECKED] ‘Show me more’: Incremental length summarisation using novelty detection (2008, Information Processing & Management)
    A user study compares summaries containing only novel sentences with incremental summaries that add contextual sentences. The experiments test whether novelty-only presentation is sufficient for relevance judgments or whether preserved context improves interpretation.
- paper_id `1301.6707` [identity: VERIFIED] Attention-Sensitive Alerting (1999, UAI 1999)
    The paper presents utility-directed procedures for balancing the cost of interrupting users against the cost of delaying alerts. Its email-focused Priorities work models expected criticality and expected cost of delayed review and adapts notification decisions using message content and user context.
- paper_id `manual-bdce973227` [identity: UNCHECKED] Success of an Agent-Assisted System that Reduces Email Overload (2009)
    RADAR identifies tasks contained in email, presents them in a task-centric Action List, and suggests schedules based on learned task-order models. In a large controlled email-overload evaluation, novice users assisted by both agents achieved better task performance with substantially fewer errors, while users varied in how much agent advice they followed.
- paper_id `doi-10-1007-s10601-009-9069-0` [identity: UNCHECKED] Lexicographically-ordered constraint satisfaction problems (2010, Constraints)
    The paper presents a formalism that explicitly separates hard feasibility constraints from softer preferences represented by lexicographic orderings. It analyzes algorithms for finding preferred feasible solutions and relates the approach to more general soft-constraint formalisms.
- paper_id `2208.03828` [identity: VERIFIED] How Do Viewers Synthesize Conflicting Information from Data Visualizations? (2023, IEEE Transactions on Visualization and Computer Graphics)
    Across four controlled experiments, participants sequentially view pairs of visualizations presenting cumulative, sometimes conflicting evidence. The study measures how direction, magnitude, context, and accompanying text affect synthesis of conflicting information and derives implications for presenting evolving evidence.
- paper_id `doi-10-1111-coin-12208` [identity: UNCHECKED] Experimenting with prequential variations for data stream learning evaluation (2019, Computational Intelligence)
    The paper empirically compares Basic Window, Sliding Window, and Fading Factors variants of prequential evaluation for data streams with concept drift. It tests how accurately each protocol reflects performance as distributions change over time and finds sliding-window prequential evaluation the strongest of the tested alternatives.
- paper_id `manual-fde6beef40` [identity: UNCHECKED] Classifying Action Items for Semantic Email (2010, LREC 2010)
    The Semanta system models email action items such as task assignments and meeting proposals as parts of ad-hoc workflows. A rule-based classifier is empirically evaluated, with results supporting assisted suggestions for user review rather than fully automatic classification.
- paper_id `doi-10-1109-access-2022-3182390` [identity: UNCHECKED] An End-to-End Personalized Preference Drift Aware Sequential Recommender System With Optimal Item Utilization (2022, IEEE Access)
    The work proposes an end-to-end sequential recommender that detects user-specific preference drift and selects interaction history relevant to the current preference state. Its experiments evaluate adaptation to dynamically changing preferences and utilization of historical items.
- paper_id `doi-10-1145-383952-383954` [identity: UNCHECKED] Temporal summaries of new topics (2001, SIGIR 2001)
    The paper defines temporal summaries for monitoring changes in news coverage as stories arrive sequentially. Sentences must be ranked before subsequent stories are observed, and the authors develop an evaluation corpus and empirically compare several temporal summarization methods.
- paper_id `manual-d19b0f6f1e` [identity: UNCHECKED] The nature of requests and commitments in email messages (2008, AAAI Workshop 2008)
    The paper defines task-oriented requests and commitments at utterance level and validates the definitions through two manual annotation experiments on Enron email. It explicitly models requests as obligations placed on another agent and commitments as obligations accepted by an agent, including conditional cases.
- paper_id `doi-10-1145-1076034-1076140` [identity: UNCHECKED] Detecting action-items in e-mail (2005, SIGIR 2005)
    The paper studies automatic detection of emails that require action or response and localization of the text expressing that request. Its formulation targets sender intent and required receiver action rather than generic topical classification.

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
