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
