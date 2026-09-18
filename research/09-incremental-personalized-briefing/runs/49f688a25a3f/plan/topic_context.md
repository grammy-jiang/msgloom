# Topic 09 context — Incremental, personalized, and priority-aware briefings

## Why this Topic exists

msgloom's final user-facing value is not a database of extracted facts; it is a briefing that lets one user keep up with important work with much less reading. The briefing must show **new developments** without repeating everything, while still carrying forward unresolved important work, actions, deadlines, conditions, and risks. It must reflect the user's Triage rules and working context without confusing likelihood of response with obligation to respond.

Topic 09 therefore owns **how accepted Topic information is selected, updated, prioritized, and summarized for the user over time**.

## Core research object

For each report cycle and Topic, determine:

- what changed since the user's previous accepted view;
- what remains open/important even if unchanged;
- what evidence/context is necessary to understand the change;
- what can be omitted as redundant without losing decision value;
- how Triage rules and working context affect ordering/priority;
- how uncertainty/pending investigation should be displayed.

The overview must cover every due Topic; summary compression must not remove essential content.

## Product and phase relevance

Phase 1 A5 already delivers email reports from accepted triage results. Phase 2 adds investigation findings and a navigable website, but reporting must remain useful even when investigation is incomplete. Topic 09 informs report-content selection and presentation; it does not own external action execution.

## Relationships to other Topics

| Topic | Relationship |
| --- | --- |
| 02 | Supplies correctly scoped within-message Topic evidence. |
| 03 | Supplies stable Topic identity so updates are compared against the same work matter rather than title similarity. |
| 04 | Supplies correct response/antecedent scope. |
| 05 | Supplies actions, deadlines, requests, commitments, decisions. |
| 06 | Supplies current state, supersession, temporal ordering, unresolved conflicts. |
| 07 | Investigation may add evidence, but report generation must not wait indefinitely; unresolved gaps can be shown. |
| 08 | Supplies grounded attachment/table/image evidence. |
| 10 | Evaluates factuality, attribution, completeness, omission, calibration, and report coverage. |

## Key conceptual distinctions

- Novel information ≠ important information.
- Unchanged but unresolved critical work must remain visible.
- Response probability ≠ response obligation.
- Summary brevity ≠ permissible omission.
- Update summarization ≠ merely diffing text.
- Personalization must not override explicit Triage rules.
- Topic summary ≠ list of message summaries.
- Report completeness is by Topic identity/version and essential content, not item counts.

## High-value academic terminology

- update summarization; incremental summarization;
- temporal summarization; timeline summarization;
- query-focused summarization; query-focused multi-document summarization;
- multi-document summarization; entity/event-centric summarization;
- topic-focused summarization; case-centric/work-item summarization;
- novelty detection / redundancy reduction in summarization;
- information update / delta summarization;
- personalized summarization; user-adaptive summarization;
- personalized ranking; learning to rank; preference-aware ranking;
- email prioritization / email triage;
- task/response priority prediction (carefully distinguished from obligation);
- salience estimation / content selection;
- coverage-aware summarization; constrained summarization;
- long-running conversation summarization / incremental dialogue summarization.

## Query families

- `"update summarization" multi-document`
- `"incremental summarization" evolving documents`
- `"temporal summarization" events`
- `"query-focused multi-document summarization"`
- `"topic-focused summarization" conversation`
- `novelty redundancy update summarization`
- `"personalized summarization" user preferences`
- `"email prioritization" triage`
- `"email triage" learning to rank`
- `unresolved action update summarization`
- `coverage-aware summarization important information`
- `incremental dialogue summarization unresolved tasks`

## False friends / exclusions

- generic message-level summarization with no stable Topic identity;
- pure novelty detection that drops unchanged open work;
- response-likelihood models treated as obligation classifiers;
- popularity/recommendation ranking;
- summarization evaluations focused only on fluency/ROUGE without decision-essential coverage;
- action drafting/execution (Phases 3/4).

## Gap-evaluation guidance

The first metric is **missed important work or evidence that would change a decision**, not average summary similarity. Prioritize research that helps prove coverage of due Topics, actions, deadlines, risks, and unresolved state while reducing redundancy. Evaluate both omission and false-alert/over-reporting costs. Personalization must remain subordinate to explicit user rules and source evidence.

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
