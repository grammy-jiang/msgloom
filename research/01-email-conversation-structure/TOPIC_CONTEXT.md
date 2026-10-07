# Topic 01 context — Email conversation structure, branching, and inline replies

## Why this Topic exists

Before msgloom can reason about work matters, it must know what text and relationship evidence actually exists in an email history. Email is not a clean linear transcript: messages arrive late or out of order, two people can reply independently to the same parent, forwards duplicate earlier material, inline replies appear between quoted fragments, headers can be absent or inconsistent, and exports can contain only fragments of the original conversation.

If this foundation is wrong, later Topics can confidently attribute a decision, condition, action, or Topic to the wrong source. Topic 01 therefore owns **conversation/reply structure and quotation/source-span provenance**, while deliberately not deciding semantic Topic identity or what a reply means.

## Core research object

Topic 01 studies the evidence graph among messages and text spans:

- reply parent and ancestry evidence;
- conversation membership/grouping evidence;
- authored/new text versus quoted/forwarded/history text;
- quotation occurrence to source-message/source-span alignment;
- multiple parents or multiple quoted sources;
- forks, missing ancestors, late arrivals, duplicate identifiers, and corrections;
- uncertainty when the evidence cannot justify one relation.

A crucial distinction is:

```text
reply/conversation evidence ≠ Topic identity
quote occurrence ≠ quote source provenance
quote source provenance ≠ semantic response scope
```

The last item belongs to Topic 04.

## Product and phase relevance

Topic 01 primarily supports Phase 1 preparation/triage by preventing duplicated history and preserving unique authored evidence. It also provides evidence lineage needed by Phase 2 investigation. It does **not** authorize semantic joining of independent Groups; Phase 2 / Topic 03 owns cross-group work-matter identity.

## Relationships to other Topics

| Topic | Relationship |
| --- | --- |
| 02 | Topic 02 consumes correctly preserved message/span content. Topic 01 must not decide within-message work-matter membership. |
| 03 | Topic 01 provides reply/group/source evidence, but Topic 03 decides whether independent groups/sources are the same work matter. |
| 04 | Topic 01 can identify the quoted/source span; Topic 04 decides what a response such as “Agreed” or “see below” semantically refers to. |
| 05 | Action/commitment extraction depends on knowing which text is current authored evidence versus quoted history. |
| 06 | State/revision reasoning depends on correct message order, ancestry, and source provenance. |
| 08 | HTML tables, forwarded blocks, attachments, and layout can affect quotation/source boundaries; Topic 08 owns deeper multimodal interpretation. |
| 10 | Topic 10 owns general reliability/calibration; Topic 01 owns relation-specific uncertainty and evidence preservation. |

## Current research state

Academic Round 1 and targeted Academic Round 2 are complete. Synthetic/adversarial Engineering Validation E1–E4 is accepted. The current stage is closed; do not automatically open Academic Round 3.

Retained conditional academic gaps:

- stronger structural quote-occurrence to source-span evidence for difficult edited/markerless/layout cases;
- modern direct-email evidence for incremental/online/LLM-assisted reconstruction.

Deferred/handoff work:

- cross-group/source Topic identity → Topic 03;
- semantic response/partial-agreement scope → Topic 04;
- general calibration/reliability methodology → Topic 10;
- external implementation/license reproduction → after candidate selection;
- Raspberry Pi performance → after candidate correctness is selected;
- production-domain validation → when suitable authorized examples exist.

## High-value academic terminology

Prefer task-specific terminology rather than only “email threading”:

- email thread reconstruction; reply-to prediction; reply graph reconstruction;
- email conversation reconstruction; conversation disentanglement;
- email quotation extraction; quoted text detection; quote attribution;
- quotation-to-source alignment; quote source attribution; source-span alignment;
- hidden email reconstruction; hidden/orphaned email fragments; orphaned quotations;
- precedence graph / partial-order reconstruction;
- local text reuse detection; passage alignment; local sequence alignment;
- edited quotation matching; approximate quotation matching; partial quotation matching;
- email zoning / body segmentation / signature-disclaimer detection;
- inline reply detection; interleaved reply extraction;
- missing-parent reconstruction; late-arrival correction; incremental thread reconstruction.

## Query families

Use combinations such as:

- `email "reply-to prediction" thread reconstruction`
- `email "quotation extraction" source attribution`
- `email "quote source" alignment edited quotation`
- `"hidden emails" reconstruction quotation`
- `email "missing parent" conversation reconstruction`
- `"local text reuse" quotation alignment`
- `email inline reply interleaved quotation`
- `incremental email thread reconstruction late arrival`
- `email duplicate "Message-ID" threading`

For a targeted refresh, search the specific failure stratum (for example markerless edited quotations) rather than reopening broad email-thread literature.

## False friends / exclusions

Do not treat these as equivalent to the Topic 01 target without evidence:

- social-media reply trees where metadata is complete;
- chat disentanglement with no quotation/history duplication;
- generic document deduplication;
- semantic Topic clustering;
- agreement/stance detection;
- generic coreference resolution.

They may be transfer evidence only.

## Gap-prioritization guidance for this Topic

A new Topic 01 gap is high project value when it risks losing unique authored evidence, assigning evidence to the wrong source, creating false ancestry, or making results arrival-order dependent. A gap is lower priority if it only improves a benchmark representation without changing preservation/provenance decisions. Before more academic work, ask whether a small synthetic engineering experiment can answer the decision more directly.

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
