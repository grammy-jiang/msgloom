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

Research topic: **Unified iterative RAG stopping and provenance control under distribution shift: search specifically for controllers that combine structured evidence sufficiency with temporal/version-aware provenance and calibrated or conformal risk-controlled stopping, including any systems that additionally integrate permission-aware access or bounded retrieval budgets.**

The seed terms below come from the research brief. They are seeds, not
validated academic terminology: a seed may name a different task in the
literature, or match a large body of work that lacks the capability this
project needs. Audit them first, then build the queries discovery will run.

This is gap-closure round 4. Earlier rounds left these gaps
open; the terminology must be able to find literature that closes them:
- gap-1 [ACADEMIC, HIGH]: Structured gap representations remain insufficiently validated for temporal constraints, multi-entity joins, and complex compositional evidence requirements; the corpus contains structured-gap, temporal-retrieval, and query-planning methods, but no admitted study evaluates these capabilities together.
    suggested query: "structured evidence gap" temporal constraints multi-entity joins compositional retrieval iterative RAG
    searched in rounds: [1, 2, 3] (still open)
- gap-2 [ACADEMIC, HIGH]: No admitted study validates an iterative evidence-gap retrieval loop that jointly preserves document-version lineage, freshness or effective-time validity, and structured sufficiency decisions.
    suggested query: "version-aware retrieval" temporal provenance iterative RAG document lineage freshness effective-time sufficiency
    searched in rounds: [1, 2, 3] (still open)
- gap-3 [ACADEMIC, HIGH]: Stopping reliability under domain shift remains open: sufficiency, confidence, conformal, and stability signals guide stopping in separate studies, but no admitted study provides a general bounded-risk iterative-RAG stopping guarantee under distribution shift.
    suggested query: "iterative RAG" calibrated stopping domain shift conformal risk control selective prediction adaptive retrieval
    searched in rounds: [1, 2, 3] (still open)
- gap-4 [ENGINEERING, HIGH]: The corpus does not test a bounded replenishment loop in which unauthorized candidates are filtered through native IAM, evidence sufficiency is reassessed, and another permission-constrained query is issued when authorized evidence remains incomplete.
- gap-5 [ENGINEERING, HIGH]: The evaluated systems do not jointly distinguish empty retrieval, authorization denial, unavailable source, unsupported extraction, exhausted budget, and true negative evidence as separate terminal or retry conditions.
- gap-6 [ENGINEERING, MEDIUM]: An end-to-end cost evaluation covering retrieval calls, retrieved passages or tokens, planner or judge inference, reranking, permission-check latency, and total wall-clock latency remains absent from the admitted corpus.
- gap-7 [ENGINEERING, HIGH]: The corpus lacks a workplace-communication evaluation combining explicit evidence gaps with heterogeneous messages and documents, multi-hop dependencies, permission restrictions, stale or conflicting evidence, and bounded retrieval.
- gap-8 [ACADEMIC, HIGH]: No admitted study validates a single controller that jointly handles structured evidence gaps, permission-aware source access, version lineage, temporal validity, calibrated stopping, abstention, and total-cost budgeting; the reported successes remain component-level or cover smaller subsets of these functions.
    suggested query: "adaptive RAG controller" permission-aware provenance temporal version calibrated stopping abstention budget
    searched in rounds: [1, 2, 3] (still open)

Seed terms to audit:
- conversational query rewriting
- query reformulation
- query resolution
- conversational search
- context-aware search
- question decontextualization
- retrieval-augmented generation
- adaptive retrieval augmented generation
- active retrieval augmented generation
- iterative retrieval
- self-directed retrieval
- multi-hop retrieval
- iterative multi-hop question answering
- retrieval planning
- evidence acquisition
- tool-use planning
- query-focused evidence retrieval
- temporal information retrieval
- time-aware retrieval
- recency-aware retrieval
- version-aware retrieval
- provenance-aware retrieval
- unanswerability detection
- answerability prediction
- selective question answering
- answer abstention
- retrieval stopping criterion
- budgeted retrieval
- cost-aware retrieval
- enterprise search
- access-controlled retrieval
- evidence sufficiency estimation

## Project context you must work within

This is the project's own description of the problem, its boundaries,
and the distinctions it needs preserved. It governs what counts as
relevant; the academic task names alone do not.

# Topic 07 context — Evidence-gap-driven context retrieval and completion

## Why this Topic exists

A3 triage should interpret the information it is given, not autonomously roam through all sources. In Phase 2, however, selected Topics may require further evidence: an unresolved pronoun, missing earlier approval, referenced attachment version, unknown owner, prior decision, or conflicting historical state.

Topic 07 studies how msgloom turns an **explicit evidence gap** into bounded retrieval, decides what to fetch next, and knows when to stop. The objective is not generic RAG for richer answers; it is targeted evidence acquisition that preserves permissions, versions, temporal validity, cost, and uncertainty.

## Core research object

A retrieval loop should be representable as:

```text
current Topic + question + known evidence
    → explicit missing-information need
    → bounded query/read request
    → source-mapped evidence or explicit failure
    → reassess gap
    → stop when answered, limits exhausted, denied, or still unanswerable
```

Empty search, denied access, unavailable attachment, or exhausted budget must not be interpreted as proof that the issue does not exist.

## Product and phase relevance

This Topic primarily belongs to **Phase 2 A4 Investigation**. Phase 1 deliberately does not search for further evidence. A4 reuses A1 collection and A2 preparation rather than inventing a separate source client or parsing pipeline.

## Direct handoffs from earlier Topics

Topic 04 (completed 2026-09-16, 47 papers, 4 rounds) hands over the case where a reference has **no resolvable antecedent in the available material**. Its guidance is explicit: when missing context is the real problem, that is an evidence need for Topic 07, not a reference-model failure. Topic 04 leaves the unresolved reference marked as unresolved rather than forcing a link, so Topic 07 receives an explicit missing-antecedent signal to turn into a targeted retrieval.

Topic 03 (completed 2026-09-16, 50 papers, 4 rounds) leaves its Phase 2 evidence-seeking strategy open as an ENGINEERING gap: when the available material does not settle whether two messages concern the same work matter, what should be retrieved next. Topic 07 owns turning that unresolved identity question into a targeted evidence need; Topic 03 keeps ownership of what counts as continuity once the evidence arrives.

**The full text of every inherited handoff is in [`INHERITED_HANDOFFS.md`](INHERITED_HANDOFFS.md)**, including what each sending Topic established, what it left open, and where the ownership boundary lies. Read it before planning; you do not need to open an earlier Topic's folder.

## Relationships to other Topics

| Topic | Relationship |
| --- | --- |
| 03 | Uncertain Topic identity can generate a targeted historical-evidence request. |
| 04 | Missing/unsupported antecedents can become retrieval gaps. |
| 05 | Missing owner/object/prerequisite may require historical evidence. |
| 06 | Conflicting or incomplete state may require earlier/later evidence. |
| 08 | Retrieved documents/attachments require grounded extraction and multimodal interpretation. |
| 09 | Briefing should not wait forever for investigation; it can report an explicit unresolved gap. |
| 10 | Evaluates answerability, source attribution, completeness, calibration, and stopping reliability. |

## Key conceptual distinctions

- Retrieval need ≠ vague desire for more context.
- Query rewriting ≠ deciding whether retrieval is warranted.
- Retrieval success ≠ question answered.
- No results ≠ negative evidence unless the source/query semantics justify it.
- Latest document ≠ temporally valid document for the question.
- More retrieval ≠ better if it exceeds scope, cost, or adds irrelevant evidence.
- Phase 1 parsing of already collected attachments ≠ Phase 2 investigation retrieval.

## High-value academic terminology

- conversational query rewriting / query reformulation;
- query resolution / conversational search / context-aware search;
- question decontextualization;
- retrieval-augmented generation (RAG), especially adaptive/active/iterative retrieval;
- active retrieval augmented generation; self-directed retrieval;
- multi-hop retrieval / iterative multi-hop QA;
- retrieval planning; evidence acquisition; tool-use planning (read-only/bounded);
- query-focused evidence retrieval;
- temporal information retrieval; time-aware retrieval; recency/freshness-aware retrieval;
- version-aware retrieval; provenance-aware retrieval;
- unanswerability detection; answerability prediction;
- selective question answering; answer abstention;
- retrieval stopping criterion; budgeted retrieval; cost-aware retrieval;
- retrieval with access constraints / enterprise search (direct-domain candidates).

## Query families

- `"conversational query rewriting" retrieval`
- `question decontextualization conversational search`
- `"adaptive retrieval" RAG stopping`
- `"active retrieval augmented generation"`
- `"iterative retrieval" evidence acquisition`
- `"multi-hop retrieval" stopping criterion`
- `"temporal information retrieval" document versions`
- `"version-aware retrieval" provenance`
- `"unanswerability detection" retrieval augmented`
- `"answer abstention" retrieval`
- `budgeted retrieval evidence acquisition`
- `enterprise search missing context email investigation`

## False friends / exclusions

- generic vector-search benchmarking with no explicit evidence need;
- unlimited agent browsing;
- retrieval that discards source/version provenance;
- Topic 08 document parsing itself;
- Topic 10 general factuality evaluation;
- recommendation retrieval unrelated to answering a bounded Topic question.

## Gap-evaluation guidance

Prioritize whether the system can formulate the **right missing-evidence question**, retrieve within allowed scope, distinguish evidence from absence, and stop responsibly. Ranking improvements are secondary unless they materially affect missed evidence or cost. Engineering validation should include denied reads, empty search, stale versions, conflicting versions, partial attachment access, multi-hop dependency, and budget exhaustion.

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

## From Topic 03 — Cross-thread Topic identity and incremental continuity

*Completed 2026-09-16. 4 rounds, 50 papers, report validated PASS 0.94. Seven
gaps left open.*

**Handed to Topic 07.** When the available material does not settle whether
two messages concern the same work matter, what should be retrieved next.
Topic 03 records this as an open ENGINEERING gap (MEDIUM): the operational
strategy for Phase 2 evidence seeking is unresolved.

**Boundary.** Topic 07 owns turning an unresolved identity question into a
targeted evidence need. Topic 03 keeps ownership of what counts as continuity
once the evidence arrives, and of the cost of a false merge against a false
split.

## From Topic 04 — Reference resolution and response scope

*Completed 2026-09-16. 4 rounds, 47 papers, report validated PASS.*

**Handed to Topic 07.** The case where a reference has **no resolvable
antecedent in the available material**. Topic 04's guidance is explicit: when
missing context is the real problem, that is an evidence need for Topic 07,
not a reference-model failure.

**What Topic 04 does with it.** It leaves the reference marked unresolved
rather than forcing a link, so Topic 07 receives an explicit
missing-antecedent signal rather than a wrong answer. Preserving that
distinction is deliberate: an invented link is more damaging than an admitted
gap.

**Boundary.** Topic 04 owns what the reference means once the material exists.
Topic 07 owns deciding what to fetch and stopping when enough has been
fetched.

## From Topic 05 — Action items, requests, commitments and decisions

*Completed 2026-09-16. 4 rounds, 48 papers.*

**Handed to Topic 07.** A missing owner, object or context becoming an
explicit retrieval need. Topic 05's uncertainty-preserving output leaves
owner, deadline, condition or act subtype **unresolved** rather than guessing,
which is its open engineering gap G9; each unresolved field is a concrete
evidence need for Topic 07.

**Boundary.** Topic 07 owns deciding what to fetch and when to stop. Topic 05
owns what the field means once the evidence arrives.

## From Topic 06 — Work-item state, event factuality, time, conflicting revisions

*Completed 2026-09-17. 4 rounds, 38 papers, no duplicate records. Every
round's synthesis was accepted by the independent review at the first attempt
— faithfulness 0.93 to 0.95 — which no earlier Topic managed. Stopped on
`round_cap_reached`. All eight gaps remain open and none was downgraded.*

**Handed to Topic 07.** An unresolved state becomes an explicit
missing-evidence requirement. Topic 06's report names this directly: evidence
retrieval should be evaluated jointly with state resolution "so unresolved
states can emit explicit missing-evidence requirements to Topic 07 rather
than hallucinating closure".

**What Topic 06 established.** Separate literatures cover factuality,
temporal ordering, commitment lifecycle, provenance and conflicting evidence,
and each works in its own setting. None of them was shown to work jointly.
An unresolved state is therefore the expected output, not a defect, and the
honest response to one is to ask for evidence rather than to guess.

**What Topic 06 left open, and Topic 07 must not treat as settled:**

- *(ACADEMIC, HIGH, Gap 3)* No joint evaluation of factuality, temporal
  ordering, lifecycle state, contradiction and provenance in one model.
  Component success does not establish integrated correctness.
- *(ACADEMIC, HIGH, Gap 5)* Nothing distinguishes a *claimed* completion from
  an independently corroborated one. A retrieval request built on a claimed
  state may be asking about work that is not actually done.
- *(ENGINEERING, HIGH, Gap 7)* Message time, effective time, deadline time
  and collection/version time have never been benchmarked together. A
  retrieval scoped by the wrong clock returns stale or retroactive evidence.

**Boundary.** Topic 07 owns deciding what to fetch, in what order, and when
to stop. Topic 06 owns what the state *is* once the evidence arrives, and
owns saying that it is still unresolved.

*Basis: Topic 06's report names Topic 07 explicitly (Future Directions 6);
the gaps are quoted from its Research Gaps table.*

## From Topic 08 — Email, image, table and attachment understanding

*Completed 2026-09-17. 4 rounds, 53 corpus records — **52 distinct papers**,
because one study was admitted twice under two identifiers. Rounds 2 and 4
were each rejected once and accepted after one repair; rounds 1 and 3 passed
at the first attempt. Stopped on `round_cap_reached`. All eight gaps remain
open and none was downgraded.*

**Handed to Topic 07.** A retrieved document, attachment or workbook still
has to be interpreted, and the evidence inside it located precisely. Topic 07
owns deciding what to fetch and when to stop; Topic 08 owns what the fetched
artefact says and where in it the claim sits — which page, region, cell or
version.

**What Topic 08 established.** Document-VQA work localises evidence to pages,
regions and answer spans; spreadsheet work localises to sheets, cells and
formulas; version-oriented work demonstrates version recovery, evolving
-document citation and version-aware retrieval. Each works in its own
setting. None was shown to work as one pipeline.

**What Topic 08 left open, and Topic 07 must not treat as settled:**

- *(ACADEMIC, HIGH, gap-1)* No complete method maintains evidence provenance
  across successive workplace attachment versions. A citation into "the
  attachment" is not yet a citation into a known version of it.
- *(ACADEMIC, HIGH, gap-4)* No admitted paper validates one end-to-end
  provenance representation identifying attachment version, page, document
  element and region together. Topic 07 cannot assume a retrieved span
  carries a usable address.
- *(ENGINEERING, HIGH, gap-5)* End-to-end behaviour when extraction or
  grounding is unsupported, incomplete or wrong is insufficiently exercised.
  A failed extraction must be distinguishable from an absent answer, which is
  a stopping-criterion concern as much as an extraction one.

**Boundary.** Topic 07 owns the retrieval decision and its budget. Topic 08
owns interpretation and grounding of whatever comes back.

*Basis: Topic 08's report names Topic 07 explicitly; the gaps are quoted from
its gaps.json.*


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
