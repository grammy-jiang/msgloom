# Topic 02 context — Within-message Topic segmentation and multiple assignments

## Why this Topic exists

A single business message can mention several independent work matters. A single matter may appear in multiple non-adjacent spans, and one span can legitimately support more than one matter. msgloom cannot safely treat a message, paragraph, sentence, or conversation as exactly one Topic.

Topic 02 therefore studies how supplied message content is divided and assigned to **concrete work matters within the current supplied content**, while preserving conditions, evidence, qualifiers, and ambiguous membership. It does not decide whether a matter in a different independent Group is the same continuing Topic; that is Topic 03.

## Core research object

The central representation is set-valued span-to-Topic membership:

```text
Topic A → span A1 + span A2           (non-contiguous)
span X → Topic A + Topic B             (joint membership)
span Y → {Topic A OR Topic B}          (ambiguity, not joint membership)
```

Research must keep those cases separate.

The key questions are not only boundary F1. They include whether a chosen annotation unit can represent the required semantic scope at all and whether segmentation/assignment loses decision-bearing information.

## Product and phase relevance

Topic 02 is central to Phase 1 A3 Topic assessment **within supplied Group content**. Phase 1 may produce several Topics from one Group. Topic 02 helps determine what evidence belongs to each matter without performing Phase 2 semantic joining across independent Groups/sources.

## Relationships to other Topics

| Topic | Relationship |
| --- | --- |
| 01 | Supplies preserved authored/quoted spans and conversation evidence. Topic 02 should not redo email quotation reconstruction. |
| 03 | Takes candidate Topic evidence from independent groups/messages and decides continuation/new-matter identity. G10 was explicitly handed from Topic 02 to Topic 03. |
| 04 | Topic 02 assigns spans to matters; Topic 04 resolves what references/responses semantically target, especially partial answers/agreement scope. |
| 05 | Action/commitment extraction uses Topic 02 scope so an action, deadline, condition, or decision attaches to the correct work matter. |
| 06 | State tracking consumes scoped Topic evidence across time. |
| 09 | Briefing relies on Topic-level content that has not been broadened or omitted by segmentation. |
| 10 | General calibration/selective prediction belongs to Topic 10; Topic 02 only validates assignment-specific uncertainty plumbing. |

## Current research state

Academic Round 1, targeted Academic Round 2, post-round gap review, and synthetic/adversarial EV1–EV7 are complete. Final engineering review is accepted with zero remaining issues. The Topic is `ACCEPTED_AND_CLOSED_FOR_CURRENT_STAGE`.

Important retained boundaries:

- direct modern business-email span-segmentation evidence remains limited; this does not justify automatic Academic Round 3;
- production representativeness is deferred;
- concrete work-matter identity/count → Topic 03;
- semantic response/partial-agreement scope → Topic 04;
- general calibration/selective prediction → Topic 10;
- external method reproduction/license checks → after candidate selection;
- hardware performance → later.

## High-value academic terminology

Do not search only for `topic segmentation`. Useful families include:

- dialogue topic segmentation; topical segmentation; topic shift detection;
- joint topic segmentation and labeling/categorization;
- multi-label span classification; span-level multi-label classification;
- multi-label sequence labeling; set-valued prediction;
- overlapping span extraction/classification;
- discontinuous span extraction / discontinuous sequence labeling;
- multi-span classification; nested/overlapping structures;
- discourse segmentation; elementary discourse units (EDUs); discourse-unit segmentation;
- semantic scope preservation; information preservation; semantic coverage;
- Atomic Content Units (ACU); content-unit coverage; salience coverage;
- decision-bearing information preservation; condition/exception/deadline scope;
- workplace email / business email / enterprise communication topic segmentation.

## Query families

- `"dialogue topic segmentation" labeling`
- `"topic segmentation" categorization dialogue`
- `"multi-label span" classification overlapping`
- `"discontinuous span" multi-label sequence labeling`
- `"overlapping" "discontinuous" span extraction`
- `"set-valued" span prediction NLP`
- `"semantic coverage" missing information evaluation`
- `"atomic content units" summarization coverage`
- `business email topic segmentation span`
- `workplace email multi-topic segmentation`
- `enterprise email span classification`

## False friends / exclusions

Do not silently substitute:

- whole-document/message multi-label classification for span assignment;
- simple topic-boundary detection for Topic membership;
- contiguous segmentation for non-contiguous membership;
- ordinary NER results for business-email Topic accuracy;
- shared vocabulary for same work-matter identity;
- high recall from broad local context for correct scope if precision collapses.

## Gap-prioritization guidance for this Topic

Prioritize gaps that can cause a work matter, condition, exception, deadline, evidence span, or shared span to be omitted or assigned to the wrong matter. Separate representational impossibility from model error: first ask whether sentence/clause/EDU/span units can express the gold structure, then evaluate prediction. Do not reopen literature merely because a benchmark is old if engineering evidence already answers the architecture-relevant question more directly.

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
