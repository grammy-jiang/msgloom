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

Research topic: **Direct empirical methods for cross-version multimodal document element lineage and hierarchical provenance, with special attention to revised workbook provenance and message referring-expression grounding into versioned pages, regions, and cells.**

The seed terms below come from the research brief. They are seeds, not
validated academic terminology: a seed may name a different task in the
literature, or match a large body of work that lacks the capability this
project needs. Audit them first, then build the queries discovery will run.

This is gap-closure round 4. Earlier rounds left these gaps
open; the terminology must be able to find literature that closes them:
- gap-1 [ACADEMIC, HIGH]: The corpus still does not establish a complete method for maintaining evidence provenance across successive workplace attachment revisions, including stable attachment identity, version-relative source locations, semantic changes between versions, and lineage from an older cited region to its later counterpart. Version-aware retrieval, scientific-PDF alignment, and XML persistent identity cover separate components, but the full multimodal attachment-revision provenance problem remains unvalidated.
    suggested query: "document version alignment" multimodal provenance region lineage semantic change revised document attachments
    searched in rounds: [1, 2, 3] (still open)
- gap-2 [ACADEMIC, HIGH]: Direct grounding of workplace-message referring expressions such as "this screenshot", "the highlighted row", "numbers below", or "use attachment v2" into attachment objects, pages, cells, or regions remains unvalidated. Existing scene-text and visually grounded dialogue studies provide adjacent-domain evidence only.
    suggested query: "referring expression grounding" document multimodal attachment table cell screenshot coreference email
    searched in rounds: [1, 2, 3] (still open)
- gap-3 [ACADEMIC, HIGH]: Comprehensive spreadsheet understanding remains open for formulas, hidden rows and sheets, cross-sheet references, merged regions, formatting semantics, units, named ranges, and provenance across revised workbook versions. Current workbook studies address retrieval, structure reconstruction, verification, workflow completion, and within-state cell provenance but not this complete set.
    suggested query: "spreadsheet understanding" workbook formulas hidden sheets named ranges merged cells cross-sheet provenance version
    searched in rounds: [1, 2, 3] (still open)
- gap-4 [ACADEMIC, HIGH]: No admitted paper validates one end-to-end provenance representation that jointly identifies attachment version, page, document element, exact region or spreadsheet cell, and answer span. Different studies validate subsets of this hierarchy, and their combination remains untested.
    suggested query: "evidence provenance" document question answering version page region cell answer span multimodal grounding
    searched in rounds: [1, 2, 3] (still open)
- gap-5 [ENGINEERING, HIGH]: End-to-end behavior when extraction or grounding is unsupported, incomplete, or wrong remains insufficiently exercised. The corpus contains unanswerable-question evaluation and parser, retrieval, OCR, localization, and grounding failure analyses, but not a complete engineering contract distinguishing genuine evidence absence from parser, OCR, layout, retrieval, or grounding failure.
- gap-6 [ENGINEERING, HIGH]: Robustness of candidate extraction and structural-preservation pipelines on heterogeneous workplace-style documents remains an engineering gap. No admitted benchmark jointly exercises sparse tables, merged and hierarchical structures, OCR corruption, irregular reading order, embedded visual objects, scanned pages, and explicit extraction-completeness accounting.
- gap-7 [ENGINEERING, MEDIUM]: Operational scaling remains open for long documents, large tables, and realistic workbooks. The corpus reports page-routing costs, evidence-graph overhead, parsing limits, workbook inspection failures, and trade-offs in change detection, but does not close the system-level latency, memory, and throughput question for the target workload.
- gap-8 [ENGINEERING, HIGH]: The corpus lacks one evaluation that simultaneously measures semantic correctness, extraction completeness, exact provenance, unsupported-evidence handling, and preservation of tables, images, document hierarchy, and reading order on workplace-style attachments. Existing benchmarks and metrics evaluate overlapping subsets rather than the complete combination.

Seed terms to audit:
- document AI
- document intelligence
- visually rich document understanding
- VRDU
- document layout analysis
- layout-aware language models
- document information extraction
- document visual question answering
- DocVQA
- multi-page document understanding
- long-document multimodal understanding
- OCR layout understanding
- reading order detection
- table detection
- table structure recognition
- table understanding
- table question answering
- spreadsheet understanding
- chart understanding
- chart question answering
- multimodal information extraction
- multimodal coreference resolution
- cross-modal reference resolution
- visual grounding
- referring expression comprehension
- document region grounding
- citation localization
- scanned document understanding
- document version comparison
- visual document differencing
- attachment content extraction
- email attachment understanding
- screenshot understanding
- figure caption grounding
- multimodal document retrieval

## Project context you must work within

This is the project's own description of the problem, its boundaries,
and the distinctions it needs preserved. It governs what counts as
relevant; the academic task names alone do not.

# Topic 08 context — Email, image, table, and attachment understanding

## Why this Topic exists

Important work information is not confined to plain message text. It appears in HTML layout, tables, screenshots, scanned PDFs, spreadsheets, Word documents, diagrams, inline images, and attachments with multiple versions. A message may say “see the highlighted row”, “numbers below”, “use attachment v2”, or “the red box is the issue”. Flattening everything into plain text can destroy relationships, units, coordinates, visual emphasis, or version identity.

Topic 08 owns **preserving and interpreting multimodal/document structure and grounding evidence back to precise source locations**.

## Product and phase relevance

Basic extraction of collected Excel/PDF/Word attachments is a Phase 1 A2 responsibility; failures and unsupported features must remain explicit. Topic 08 research goes beyond parser selection to the semantic question of whether tables/layout/images and cross-modal references can be understood without losing decision-relevant content. Phase 2 may retrieve additional attachments through Topic 07/A4, but retrieved content still uses A1/A2 preservation and parsing contracts.

## Direct handoffs from earlier Topics

Topic 04 (completed 2026-09-16, 47 papers, 4 rounds) covers reference resolution over text propositions only. References to tables, screenshots, attachments, cells, pages or visual regions were excluded from its corpus and are handed to Topic 08 for grounding. Topic 04 still owns the *scope* question once such an object is grounded: which proposition the response applies to.

**The full text of every inherited handoff is in [`INHERITED_HANDOFFS.md`](INHERITED_HANDOFFS.md)**, including what each sending Topic established, what it left open, and where the ownership boundary lies. Read it before planning; you do not need to open an earlier Topic's folder.

## Relationships to other Topics

| Topic | Relationship |
| --- | --- |
| 01 | HTML/layout/forwarded blocks can affect quote boundaries; Topic 01 owns email quotation provenance. |
| 02 | Extracted document spans/regions may belong to one or multiple Topics. |
| 04 | References such as “see row 4”, “this screenshot”, or “attachment version two” require multimodal grounding. |
| 05 | Actions/deadlines/decisions can reside in tables or attachments. |
| 06 | Versioned documents can supersede or contradict earlier state. |
| 07 | Retrieves missing attachments/documents; Topic 08 interprets their content. |
| 09 | Briefing must preserve critical structured evidence rather than summarizing only body text. |
| 10 | Evaluates extraction completeness, grounding/citation correctness, and omission of multimodal evidence. |

## Key conceptual distinctions

- Parsing success ≠ complete understanding.
- OCR text ≠ layout/table understanding.
- Text extraction ≠ reading order correctness.
- Table cell values ≠ table semantics/units/headers/merged relationships.
- Attachment filename ≠ document version identity.
- Visual grounding ≠ generic image captioning.
- A missing/unsupported region must be a limitation, not an empty successful result.

## High-value academic terminology

- document AI / document intelligence;
- visually rich document understanding (VRDU);
- document layout analysis; layout-aware language models;
- document information extraction;
- document visual question answering (DocVQA);
- multi-page document understanding / long-document multimodal understanding;
- OCR + layout understanding; reading order detection;
- table detection; table structure recognition (TSR); table understanding;
- table question answering; spreadsheet understanding;
- chart understanding / chart QA (when relevant);
- multimodal information extraction;
- multimodal coreference; cross-modal reference resolution;
- visual grounding / referring expression comprehension;
- document region grounding / citation localization;
- scanned document understanding;
- document version comparison / visual document differencing (supporting evidence).

## Query families

- `"visually rich document understanding" layout`
- `"document layout analysis" information extraction`
- `"document visual question answering" grounding`
- `"multi-page document understanding" multimodal`
- `"table structure recognition" business documents`
- `"table understanding" document AI`
- `spreadsheet understanding semantic table`
- `"multimodal coreference" document`
- `"visual grounding" document screenshot`
- `document region grounding citation`
- `scanned PDF information extraction layout`
- `document version comparison semantic change`

## False friends / exclusions

- OCR character accuracy alone;
- image captioning with no source-location grounding;
- generic VQA with no document structure;
- parser throughput benchmarks that do not measure meaning preservation;
- Topic 07 retrieval/search;
- Topic 04 language-only reference resolution when the referent is already textually available.

## Gap-evaluation guidance

Prioritize failure modes that hide or distort evidence that could change a decision: wrong table row/column associations, lost units, omitted scanned pages, unsupported embedded objects, wrong attachment version, or unresolved visual references. Performance is secondary to meaning preservation. Clearly separate Phase 1 extraction coverage from deeper semantic interpretation and from Phase 2 retrieval.

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

## From Topic 04 — Reference resolution and response scope

*Completed 2026-09-16. 4 rounds, 47 papers, report validated PASS.*

**Handed to Topic 08.** References to tables, screenshots, attachments,
cells, pages and visual regions. Topic 04's corpus covers reference
resolution over text propositions only; these were excluded from it by
design, so Topic 04's evidence says nothing about them.

**Boundary.** Topic 08 owns grounding the referenced object. Topic 04 still
owns the scope question once it is grounded: which proposition the response
applies to. A grounded object is not yet a scoped response.

## From Topic 05 — Action items, requests, commitments and decisions

*Completed 2026-09-16. 4 rounds, 48 papers.*

**Handed to Topic 08.** Action evidence that lives in attachments, tables or
screenshots. Topic 05's corpus covers text; where the deadline or the object
of an action is only in an attached file, Topic 08 supplies the grounded
content and Topic 05 still owns what the action is.

**Related open gap.** Topic 05's G8 covers zoning author, quoted and forwarded
text while preserving provenance. Attachment references are part of that
surface and are not yet evidenced.


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
