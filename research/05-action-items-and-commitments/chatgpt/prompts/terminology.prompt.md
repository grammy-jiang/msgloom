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

Research topic: **authentic workplace email and enterprise-chat benchmarks for structured action/decision extraction, focusing specifically on implicit and group assignees, action-to-deadline binding, condition/negation/modality scope, and exact argument evidence spans**

The seed terms below come from the research brief. They are seeds, not
validated academic terminology: a seed may name a different task in the
literature, or match a large body of work that lacks the capability this
project needs. Audit them first, then build the queries discovery will run.

This is gap-closure round 4. Earlier rounds left these gaps
open; the terminology must be able to find literature that closes them:
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

Seed terms to audit:
- action item extraction
- action item detection
- task extraction
- to-do extraction
- task-oriented information extraction
- email speech act classification
- dialogue act classification
- request detection
- request identification
- commissive speech acts
- commitment extraction
- commitment detection
- promise detection
- obligation detection
- deontic modality
- intention detection
- intent-to-act
- decision extraction
- decision detection
- meeting decision detection
- event extraction
- event argument extraction
- semantic role labeling
- implicit argument resolution
- zero anaphora
- omitted argument recovery
- conditionality detection
- hedge detection
- speculation detection
- modality detection
- temporal expression extraction
- temporal expression normalization
- deadline extraction
- responsibility assignment
- owner assignment
- assignee extraction
- email action-item corpora
- request-response corpora

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
