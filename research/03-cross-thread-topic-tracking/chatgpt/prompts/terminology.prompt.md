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

Research topic: **Direct enterprise email/chat studies of longitudinal cross-thread conversation or work-item linking, especially evidence for concrete business-event identity and for partial, evolving, subevent, or non-transitive continuity relations in organizational workflows.**

The seed terms below come from the research brief. They are seeds, not
validated academic terminology: a seed may name a different task in the
literature, or match a large body of work that lacks the capability this
project needs. Audit them first, then build the queries discovery will run.

This is gap-closure round 4. Earlier rounds left these gaps
open; the terminology must be able to find literature that closes them:
- gap-1 [ACADEMIC, HIGH]: Which evidence combinations actually establish or refute continuity of a concrete work matter across independent workplace messages, conversations, attachments, email, and Teams remains open. The corpus supports adjacent-domain signals but does not validate subject, customer/project names, conversation ancestry, referenced artifacts, commitments, or state compatibility as target-domain identity evidence.
    suggested query: ("work item identity" OR "work matter identity" OR "business event coreference" OR "cross-document event coreference") AND (email OR "workplace communication" OR enterprise) AND (cross-thread OR cross-document OR cross-source)
    searched in rounds: [1, 2, 3] (still open)
- gap-2 [ENGINEERING, HIGH]: The application-specific decision policy remains open: the relative cost of false merges versus false splits, thresholds for attachment versus rejection, and exact semantics/calibration of CONTINUE, NEW, and UNCERTAIN must be determined from msgloom requirements and empirical evaluation. The corpus supports rejection and risk-coverage trade-offs but does not establish msgloom's loss function or false-merge cost.
- gap-3 [ENGINEERING, HIGH]: The msgloom correction and identity-state model remains open. Stable Topic IDs independent of generated labels or source thread IDs, versioned identity assessments, supersession links, immutable evidence lineage, and general MERGE/SPLIT correction require project-level design and testing. Incremental entity-resolution papers show that earlier clusters can be revised but do not define msgloom's identity/history semantics.
- gap-4 [ACADEMIC, HIGH]: There is still no direct production-domain evidence in this corpus for longitudinal work-matter identity across Outlook email and Microsoft Teams. The enterprise email and process-correlation papers provide useful adjacent evidence but do not establish production accuracy or representativeness for msgloom.
    suggested query: (enterprise OR workplace OR organizational) AND (email OR "Microsoft Teams" OR "enterprise chat" OR "workplace chat") AND (cross-thread OR longitudinal OR cross-conversation) AND ("topic identity" OR "task tracking" OR "case tracking" OR "event coreference" OR "conversation linking")
    searched in rounds: [1, 2, 3] (still open)
- gap-5 [ACADEMIC, HIGH]: How partial, subevent, evolving, membership, or otherwise non-transitive relations should map onto workplace work-matter continuity remains unresolved. The corpus establishes that such relations exist and can violate transitivity, but it does not define when they should mean CONTINUE, RELATED-BUT-SEPARATE, MERGE, SPLIT, or another workplace-specific relation.
    suggested query: ("partial event identity" OR "partial coreference" OR "subevent relation" OR "event evolution" OR "event membership" OR "non-transitive coreference") AND (workflow OR task OR case OR workplace OR enterprise)
    searched in rounds: [1, 2, 3] (still open)
- gap-6 [ENGINEERING, MEDIUM]: The best operational strategy for Phase 2 evidence seeking remains unresolved. Retrieval-based event-coreference search and global-context models show that additional evidence can matter, but msgloom still needs engineering benchmarks for bounded historical retrieval, candidate generation, latency, retrieval stopping rules, and whether retrieved context actually changes identity decisions correctly.
- gap-7 [ACADEMIC, MEDIUM]: Calibration under non-stationary workplace streams remains unresolved. The corpus now contains stronger evidence that calibration deteriorates under distribution shift and that drift-aware or conformal approaches can help, but it does not establish reliable calibration, abstention thresholds, or coverage guarantees for longitudinal workplace coreference or clustering.
    suggested query: ("selective classification" OR abstention OR "confidence calibration" OR "selective prediction") AND ("distribution shift" OR nonstationary OR streaming OR "concept drift") AND (text OR NLP OR coreference OR clustering)
    searched in rounds: [1, 2, 3] (still open)

Seed terms to audit:
- cross-document event coreference
- cross-document event coreference resolution
- event coreference resolution
- event identity
- same-event detection
- event linking
- cross-document event linking
- cross-document coreference
- entity resolution
- entity linking
- record linkage
- topic detection and tracking
- story link detection
- new event detection
- novelty detection
- incremental clustering
- online clustering
- streaming clustering
- cluster linking
- cluster maintenance
- dynamic clustering
- event evolution
- event timeline tracking
- business email
- workplace communication
- enterprise communication
- work chat
- asynchronous conversation

## Project context you must work within

This is the project's own description of the problem, its boundaries,
and the distinctions it needs preserved. It governs what counts as
relevant; the academic task names alone do not.

# Topic 03 context — Cross-thread Topic identity and incremental continuity

## Why this Topic exists

After Topic 02 identifies work-matter evidence inside supplied messages/groups, msgloom still needs to answer a harder longitudinal question: **does new evidence continue an existing concrete work matter, start a new work matter, or remain uncertain?**

Real work does not respect email subjects or thread boundaries. A procurement matter can move from one email chain to another, then into Teams, then return under a new title. Conversely, two messages with the same customer, project name, participants, or subject can still be distinct matters. Wrong merging can hide a due item; wrong splitting can fragment history and obscure state.

This Topic is therefore the owner of **stable Topic identity across independent Groups and sources**, especially incrementally over time.

## Direct handoff from earlier Topics

Topic 01 established that conversation/group relationships are evidence but **not Topic identity**. Topic 02 explicitly handed off its G10 problem — concrete work-matter identity and Topic count — to Topic 03. Those handoffs are part of this Topic's starting context, not new gaps to rediscover.

## Core research object

Given a new candidate matter/span/group and a set of existing Topic identities, decide among:

```text
CONTINUE existing Topic
NEW Topic
UNCERTAIN relationship (keep separate)
MERGE correction
SPLIT correction
```

Identity must be stable and independent of generated titles. Corrections create new assessments and links; they do not rewrite source history.

## Product and phase relevance

This Topic straddles phases:

- Phase 1 can link a continuation only with explicit supporting evidence and otherwise must keep matters separate with uncertainty.
- Phase 2 A4 explicitly owns Topic relationships across **independent groups and sources** and can investigate additional evidence.

Therefore research should distinguish what can safely be done from supplied content in Phase 1 from what requires Phase 2 investigation.

## Relationships to other Topics

| Topic | Relationship |
| --- | --- |
| 01 | Supplies conversation/group ancestry and source provenance; these are features/evidence, not identity decisions. |
| 02 | Supplies within-message candidate Topic spans/memberships. Topic 03 decides cross-message/group continuity. |
| 04 | Reference resolution may provide evidence that a new message refers to a prior matter, but reference evidence alone may remain ambiguous. |
| 05 | Actions/commitments can be strong identity evidence when owner/object/target match, but must not force a merge by themselves. |
| 06 | State and temporal compatibility help distinguish continuation from a similar but different matter and help detect merge/split errors. |
| 07 | When identity is uncertain, Topic 07 may retrieve bounded historical evidence to resolve the relationship in Phase 2. |
| 09 | Briefing needs stable identities to avoid duplicate or missing Topic entries. |
| 10 | Topic 10 evaluates confidence/calibration and relationship evidence quality; Topic 03 owns the domain decision. |

## Key conceptual distinctions

- Group/conversation membership ≠ Topic identity.
- Same subject/customer/project ≠ same work matter.
- Semantic similarity ≠ continuation.
- One new message may continue multiple existing matters through different spans.
- A Topic label/title is presentation, not identity.
- “No confident match” ≠ proven new Topic; abstention/uncertainty may be correct.
- Online assignment decisions must support later correction when new evidence arrives.

## Research questions to emphasize

- What evidence establishes same-event/same-work-matter identity across documents?
- How do event/entity coreference methods distinguish identity from similarity?
- How should online clustering create a new cluster versus attach to an existing one?
- How are novelty/new-event detection and open-set rejection evaluated?
- How can merge/split corrections preserve stable IDs and history?
- How should temporal, participant, object, action, reference, and source-structure evidence be combined without over-merging?
- Which benchmarks actually test cross-document identity rather than topical similarity?
- How should uncertain cross-source relationships remain separate and visible?

## High-value academic terminology

Search across several research communities:

- cross-document event coreference (CDCR); event coreference resolution;
- cross-document entity coreference; entity resolution; entity matching; record linkage;
- event identity; event linking; event clustering;
- topic detection and tracking (TDT); topic tracking; new event detection;
- online clustering; incremental clustering; streaming clustering;
- novelty detection; open-set recognition/classification; reject option;
- cluster assignment with abstention; unknown-class detection;
- dynamic clustering; cluster merge/split; incremental entity resolution;
- temporal/event consistency; event evolution; storyline/event tracking;
- cross-source information linking; cross-channel conversation linking;
- task/work-item identity (when available in enterprise/workflow literature).

## Query families

- `"cross-document event coreference" identity`
- `"event coreference" cross-document clustering`
- `"new event detection" topic tracking`
- `"online clustering" event stream novelty`
- `"incremental clustering" entity resolution`
- `"open set" event classification clustering`
- `"cluster assignment" abstention streaming text`
- `"topic detection and tracking" new event`
- `work item identity email cross thread`
- `business email cross-thread topic tracking`
- `cross-source work matter identity`

Use snowballing aggressively because useful terminology may come from event coreference, entity resolution, TDT, streaming clustering, or case/workflow management rather than email research.

## False friends / exclusions

Be cautious with:

- document-level semantic similarity or embeddings without identity labels;
- ordinary topic modeling where “topic” means latent word distribution;
- thread/conversation reconstruction (Topic 01);
- within-document segmentation (Topic 02);
- duplicate detection, which is narrower than work-matter identity;
- recommendation-session/user-interest tracking unless identity semantics match;
- clustering results that force every item into a cluster and cannot abstain/create a new Topic.

## Gap-evaluation guidance

The highest-value gaps are those that affect **false merges, false splits, new-Topic detection, stable identity, or correction**. A small precision gain on similarity clustering is less valuable than evidence about when to abstain. Evaluate false merges especially harshly because they can cause one matter to disappear from reports. Separate Phase 1 supplied-evidence decisions from Phase 2 evidence-seeking decisions.

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
