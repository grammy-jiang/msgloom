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
