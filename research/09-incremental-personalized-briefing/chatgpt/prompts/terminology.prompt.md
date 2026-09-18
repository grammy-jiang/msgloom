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

Research topic: **Direct empirical evaluations of longitudinal cross-thread workplace briefing: cycle-by-cycle new/open/resolved/superseded work-item tracking, obligation-versus-preference selection, adaptive personalization under preference drift, and joint omission/repetition/false-alert evaluation.**

The seed terms below come from the research brief. They are seeds, not
validated academic terminology: a seed may name a different task in the
literature, or match a large body of work that lacks the capability this
project needs. Audit them first, then build the queries discovery will run.

This is gap-closure round 4. Earlier rounds left these gaps
open; the terminology must be able to find literature that closes them:
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

Seed terms to audit:
- update summarization
- incremental summarization
- temporal summarization
- timeline summarization
- query-focused summarization
- query-focused multi-document summarization
- multi-document summarization
- entity-centric summarization
- event-centric summarization
- topic-focused summarization
- novelty detection
- redundancy reduction in summarization
- delta summarization
- information update detection
- personalized summarization
- user-adaptive summarization
- personalized ranking
- learning to rank
- preference-aware ranking
- email prioritization
- email triage
- response priority prediction
- salience estimation
- content selection
- coverage-aware summarization
- constrained summarization
- long-running conversation summarization
- incremental dialogue summarization
- notification prioritization
- digest generation

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
