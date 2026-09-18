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
