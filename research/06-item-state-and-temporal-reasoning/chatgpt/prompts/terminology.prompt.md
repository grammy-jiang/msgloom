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

# Task: academic terminology refinement (before any bulk search)

Research topic: **Direct empirical NLP methods for longitudinal work-item revision in workplace or operational communication, especially relation labeling for supersession/correction/supplementation/reopening/conflict and evidence models separating claimed completion from independently corroborated completion.**

The seed terms below come from the research brief. They are seeds, not
validated academic terminology: a seed may name a different task in the
literature, or match a large body of work that lacks the capability this
project needs. Audit them first, then build the queries discovery will run.

This is gap-closure round 4. Earlier rounds left these gaps
open; the terminology must be able to find literature that closes them:
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

Seed terms to audit:
- event factuality prediction
- factuality profiling
- event modality
- event certainty
- event veridicality
- negation detection
- speculation detection
- hedging detection
- temporal information extraction
- temporal relation extraction
- event temporal ordering
- temporal relation classification
- TimeML
- temporal graphs
- temporal constraint reasoning
- event status tracking
- state tracking
- dialogue state tracking
- event evolution
- event update
- timeline extraction
- contradiction detection
- natural language inference
- belief revision
- truth maintenance systems
- assumption-based truth maintenance
- knowledge-base revision
- temporal knowledge graphs
- document supersession
- version supersession
- revision tracking
- change detection
- provenance-aware state
- event sourcing

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


Do four things.

1. Audit every seed: its standard meaning in the literature, how well it fits
   this topic (STRONG, MODERATE, WEAK, or REJECT), its main risk, and the
   false-positive literature it attracts.
2. Translate the topic into academic task families. Mark each DIRECT (the
   literature studies this problem) or TRANSFER (the method may carry over
   from another domain). Name known seed papers where you are confident they
   exist; never invent one.
3. Build the query families discovery will run, grouped by task family, each
   carrying its family's role.
4. State the earliest publication year discovery must reach, and why. A
   recency window must not silently exclude the foundational work of the
   field. If the founding work of this problem is from the 1990s or 2000s,
   say so and set the year accordingly.

Also list downgrade rules: literature that matches the words but not the
capability, which discovery should not return.

JSON schema for the first block:
{
 "$schema": "http://json-schema.org/draft-07/schema#",
 "title": "TerminologyAnalysis",
 "description": "Academic terminology refinement performed before bulk discovery: each seed keyword is audited, the product problem is translated into academic task families, and query families are built with an explicit DIRECT or TRANSFER role.",
 "type": "object",
 "required": [
  "topic",
  "seed_audit",
  "task_families",
  "query_families"
 ],
 "properties": {
  "topic": {
   "type": "string",
   "minLength": 1
  },
  "seed_audit": {
   "type": "array",
   "minItems": 1,
   "description": "One entry per seed keyword supplied by the brief or the plan.",
   "items": {
    "type": "object",
    "required": [
     "seed",
     "academic_meaning",
     "fit",
     "main_risk"
    ],
    "properties": {
     "seed": {
      "type": "string",
      "minLength": 1
     },
     "academic_meaning": {
      "type": "string",
      "minLength": 1
     },
     "fit": {
      "type": "string",
      "enum": [
       "STRONG",
       "MODERATE",
       "WEAK",
       "REJECT"
      ]
     },
     "main_risk": {
      "type": "string",
      "minLength": 1
     },
     "false_positive_literature": {
      "type": "string"
     }
    }
   }
  },
  "task_families": {
   "type": "array",
   "minItems": 1,
   "description": "Academic task families the product problem maps onto.",
   "items": {
    "type": "object",
    "required": [
     "id",
     "name",
     "description",
     "role"
    ],
    "properties": {
     "id": {
      "type": "string",
      "minLength": 1
     },
     "name": {
      "type": "string",
      "minLength": 1
     },
     "description": {
      "type": "string",
      "minLength": 1
     },
     "role": {
      "type": "string",
      "enum": [
       "DIRECT",
       "TRANSFER"
      ]
     },
     "why_it_matters": {
      "type": "string"
     },
     "seed_papers": {
      "type": "array",
      "items": {
       "type": "string"
      }
     }
    }
   }
  },
  "query_families": {
   "type": "array",
   "minItems": 1,
   "description": "Queries to run, grouped by task family. These replace the plan's raw query variants.",
   "items": {
    "type": "object",
    "required": [
     "family_id",
     "role",
     "queries"
    ],
    "properties": {
     "family_id": {
      "type": "string",
      "minLength": 1
     },
     "role": {
      "type": "string",
      "enum": [
       "DIRECT",
       "TRANSFER"
      ]
     },
     "queries": {
      "type": "array",
      "minItems": 1,
      "items": {
       "type": "string",
       "minLength": 1
      }
     }
    }
   }
  },
  "promoted_terms": {
   "type": "array",
   "items": {
    "type": "string"
   }
  },
  "demoted_terms": {
   "type": "array",
   "items": {
    "type": "string"
   }
  },
  "downgrade_rules": {
   "type": "array",
   "description": "False friends: literature that matches the words but not the capability.",
   "items": {
    "type": "string"
   }
  },
  "date_policy": {
   "type": "object",
   "description": "Why the search window is what it is; foundational work must not be excluded silently.",
   "properties": {
    "earliest_year_to_include": {
     "type": "integer"
    },
    "rationale": {
     "type": "string"
    }
   }
  }
 },
 "additionalProperties": true
}

Reply with two blocks.
===BEGIN terminology.json===
<content>
===END terminology.json===
===BEGIN terminology.md===
# <topic> academic terminology analysis

## Product problem
...
## Seed keyword audit
| Seed | Academic meaning | Fit | Main risk |
...
## Academic task families
...
## Query families
...
## False friends and downgrade rules
...
## Date policy
...
===END terminology.md===
