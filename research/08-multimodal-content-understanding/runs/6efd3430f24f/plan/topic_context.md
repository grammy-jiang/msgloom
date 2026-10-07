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
