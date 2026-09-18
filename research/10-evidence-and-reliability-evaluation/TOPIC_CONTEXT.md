# Topic 10 context — Evidence attribution, factuality, completeness, and reliability evaluation

## Why this Topic exists

Every earlier Topic can produce a plausible-looking but wrong result. msgloom therefore needs a cross-cutting evaluation discipline that asks: **what exact evidence supports each decision-relevant statement, is that evidence current and correctly attributed, what important evidence or Topic was omitted, and when should the system abstain?**

Topic 10 is not merely “LLM hallucination detection”. It owns the general evaluation framework for evidence attribution, claim correctness, completeness/coverage, uncertainty calibration, selective prediction, and user-reviewed acceptance across msgloom.

## Core research object

Decompose outputs into verifiable units and separately evaluate:

- claim correctness against source evidence;
- citation/source attribution correctness;
- citation/evidence completeness;
- current-state correctness after revisions/conflicts;
- Topic/report coverage and omitted important work;
- calibrated confidence / risk-coverage behavior;
- appropriate abstention and visible uncertainty;
- human-review protocols and representative evaluation samples.

These dimensions must not be collapsed into one “faithfulness” score.

## Direct handoffs from earlier Topics

Topic 01 explicitly handed off general calibration/reliability methodology while retaining relation-specific uncertainty. Topic 02 explicitly handed off general selective-prediction/calibration methodology while retaining assignment-specific diagnostics. Similar domain-specific outputs from Topics 03–09 should be evaluated here without moving their semantic ownership into Topic 10.

Topic 04 (completed 2026-09-16, 47 papers, 4 rounds) hands off two unresolved ENGINEERING gaps that are evaluation questions, not literature questions. Gap 2: a combined annotation and evaluation contract covering exact, partial, ambiguous, unsupported, discontinuous, multiple-antecedent, composite and no-link outcomes, scoring exact links, span overlap, zero-link outcomes and multi-antecedent partial credit separately. Gap 5: an abstention and asymmetric error-cost policy, since an over-broad approval link and a missed link do not cost the same. Topic 04 keeps ownership of what those outcomes *mean*; Topic 10 owns the general calibration and attribution methodology, and neither gap is closable by more papers.

Topic 03 (completed 2026-09-16, 50 papers, 4 rounds) hands off calibration under non-stationary workplace streams as general methodology, while retaining identity-specific uncertainty: the relative cost of a false merge against a false split is a Topic 03 decision, not a general calibration question.

**The full text of every inherited handoff is in [`INHERITED_HANDOFFS.md`](INHERITED_HANDOFFS.md)**, including what each sending Topic established, what it left open, and where the ownership boundary lies. Read it before planning; you do not need to open an earlier Topic's folder.

## Product and phase relevance

Topic 10 is cross-cutting across all phases. The design already states that schema validity and model confidence are **not evidence of semantic correctness**. Acceptance combines structural checks with user-reviewed work samples and measures missed important information, wrong grouping, unsupported relationships, lost actions/deadlines, report coverage, and recovery.

## Relationships to other Topics

| Topic | Reliability focus supplied to Topic 10 |
| --- | --- |
| 01 | reply/ancestry/quote-source attribution, preservation, relation uncertainty |
| 02 | span/Topic membership, overlap/non-contiguity, decision-scope preservation |
| 03 | false merge/split/new-Topic errors, identity confidence |
| 04 | antecedent correctness and partial-response scope |
| 05 | action/owner/deadline/condition extraction and missed obligations |
| 06 | factuality, temporal/current-state correctness, contradiction/supersession |
| 07 | retrieval relevance, answerability, evidence sufficiency, stopping/abstention |
| 08 | extraction/grounding completeness and multimodal source localization |
| 09 | report claim correctness, attribution, due-Topic coverage, omission/false-alert balance |

Topic 10 should define common evaluation machinery where useful but must not erase domain-specific denominators or semantics from the owning Topics.

## Key conceptual distinctions

- Factual correctness ≠ citation correctness.
- Citation correctness ≠ citation completeness.
- Evidence support ≠ current-state correctness.
- Current-state correctness ≠ report completeness.
- Confidence score ≠ calibrated probability.
- Calibration ≠ safe decision policy without coverage/risk analysis.
- Fluency ≠ reliability.
- LLM-as-judge agreement ≠ ground truth unless validated.
- No evidence found ≠ evidence of absence.

## High-value academic terminology

- factual consistency / factuality evaluation;
- summarization faithfulness / hallucination evaluation;
- claim decomposition / atomic claim extraction;
- claim verification / fact verification;
- attribution evaluation / source attribution;
- citation correctness / citation precision;
- citation completeness / citation recall / citation coverage;
- groundedness / evidence grounding;
- answer correctness vs context faithfulness (RAG evaluation literature, carefully interpreted);
- completeness / coverage evaluation; omission detection;
- Atomic Content Units (ACU), content units, proposition-level evaluation;
- selective prediction; selective classification; reject option;
- uncertainty calibration; expected calibration error (ECE); Brier score;
- risk-coverage curves; selective risk; abstention;
- conformal prediction (potential transfer, depending task);
- human evaluation reliability; inter-annotator agreement; adjudication;
- evaluation of retrieval-augmented generation / citation-grounded generation;
- decision-focused evaluation / utility-sensitive evaluation.

## Query families

- `"factual consistency" summarization evaluation`
- `"claim decomposition" verification LLM`
- `"claim verification" source attribution`
- `"citation correctness" "citation completeness"`
- `attribution evaluation grounded generation`
- `"evidence completeness" summarization`
- `"Atomic Content Units" evaluation`
- `"selective prediction" NLP abstention`
- `"risk coverage" language model`
- `"uncertainty calibration" NLP`
- `"RAG evaluation" citation groundedness completeness`
- `decision focused evaluation summarization omission`

## False friends / exclusions

- one aggregate “hallucination score” used as universal quality;
- model self-confidence with no calibration study;
- LLM-as-judge results without validation against human/ground truth;
- citation presence counted as citation correctness;
- schema validation counted as semantic correctness;
- generic benchmark accuracy replacing Topic-specific safety denominators;
- calibration research that ignores useful coverage.

## Gap-evaluation guidance

Prioritize evaluation gaps that could allow unsupported claims, omitted due Topics, hidden decision-changing evidence, false confidence, or incorrect “complete” status to pass unnoticed. Common metrics are useful only if they preserve Topic-specific semantics. Prefer decomposed, traceable evaluation with explicit denominators and user-reviewed representative examples. A strong Topic 10 result should help earlier Topics know when to abstain or request review without taking ownership of their domain logic.

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
