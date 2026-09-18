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

Research topic: **direct empirical studies of proposition-level partial reply scope in workplace email or enterprise dialogue, especially multi-question messages, unanswered subquestions, scoped approval/rejection, and responses linked jointly to multiple antecedent propositions**

The seed terms below come from the research brief. They are seeds, not
validated academic terminology: a seed may name a different task in the
literature, or match a large body of work that lacks the capability this
project needs. Audit them first, then build the queries discovery will run.

This is gap-closure round 4. Earlier rounds left these gaps
open; the terminology must be able to find literature that closes them:
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

Seed terms to audit:
- discourse deixis
- discourse-deictic reference
- abstract anaphora
- propositional anaphora
- event anaphora
- anaphora resolution
- coreference resolution
- coreference to events
- coreference to propositions
- conversational coreference
- dialogue reference resolution
- dialogue discourse parsing
- conversational discourse relations
- discourse relation recognition
- response-to discourse relation
- adjacency pairs
- dialogue act
- question answer alignment
- question resolution
- answer scope
- partial answer detection
- multi-question answering in dialogue
- agreement detection
- disagreement detection
- agreement target identification
- agreement scope
- stance with target identification
- entailment relative to a proposition
- contradiction detection
- business email
- email reply
- approval scope
- workplace communication

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
