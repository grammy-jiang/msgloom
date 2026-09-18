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

# Task: admission gate for 25 screened candidate(s)

Research topic: **Joint evaluation and selective prediction for temporally evolving multi-source generation: evidence completeness for compound and partially supported claims, longitudinal omission of superseded or due work-item state, and online calibration under non-stationary streams**

Decide which of these candidates enters the reading round. Admit a paper only
when it materially strengthens one of the research streams below, and the
abstract shows that, not merely shared vocabulary. A paper count is never a
reason to admit: admitting six of twenty is a valid answer, and so is
admitting none. Rejecting a paper here costs little; reading a paper that
cannot strengthen a stream costs a reading slot that a better paper needed.

Research streams:
- tf_atomic_factuality [DIRECT] Atomic claim decomposition and evidence-conditioned factuality: Decompose generated text into independently checkable propositions and score support, contradiction, insufficiency, or partial support against evidence.
- tf_citation_attribution [DIRECT] Claim-to-source attribution and citation quality: Evaluate whether the correct evidence source is attached to each generated claim, separating citation correctness or precision from citation completeness or recall.
- tf_evidence_completeness [DIRECT] Evidence sufficiency and completeness for compound and multi-source claims: Determine whether all propositions in a generated claim have sufficient supporting evidence, including cases where support is partial, distributed across complementary sources, or requires multiple pieces of evidence.
- tf_joint_multidimensional_eval [DIRECT] Multi-dimensional and end-to-end generation evaluation: Evaluation frameworks that retain distinct dimensions for factual correctness, evidence attribution, support completeness, temporal correctness, omission, uncertainty, abstention, and human validation rather than collapsing them into one score.
- tf_temporal_currentness [TRANSFER] Temporal validity, current-state correctness, and version-aware evidence: Methods that evaluate whether evidence and generated claims are valid at the observation time, particularly when facts change, later evidence supersedes earlier evidence, or versions conflict.
- tf_longitudinal_omission [TRANSFER] Update, temporal, and longitudinal summarization with omission and redundancy control: Evaluation of whether an evolving summary captures newly important information over time while avoiding redundant or obsolete material and retaining required event or state updates.
- tf_selective_generation [DIRECT] Selective prediction and abstention for NLP and free-form generation: Language systems that answer or generate only when estimated risk is acceptable, otherwise abstaining, requesting more evidence, or deferring to a human.
- tf_selective_foundations [TRANSFER] Selective classification, reject option, and risk-coverage foundations: Foundational theory and metrics for trading predictive coverage against conditional risk using an explicit reject option.
- tf_calibration_generation [DIRECT] Task-level probability calibration for NLP and generated-answer correctness: Calibration of confidence against empirically observed correctness, preferably at claim, answer, or decision level rather than token-likelihood level.
- tf_online_nonstationary_calibration [TRANSFER] Online calibration under concept drift and distribution shift: Sequential recalibration or uncertainty-control methods designed for data whose distribution changes over time rather than remaining IID or exchangeable.
- tf_conformal_risk_control [TRANSFER] Adaptive conformal inference and conformal risk control: Conformal methods that move beyond static exchangeable prediction sets toward online adaptation or explicit control of application-defined loss.
- tf_human_metaevaluation [DIRECT] Human evaluation reliability, metric meta-evaluation, and evaluator validation: Research on annotation reliability, disagreement, adjudication, metric-human correlation, evaluator bias, and validation of automatic or LLM-based judges.
- tf_utility_sensitive_eval [TRANSFER] Cost-sensitive, utility-sensitive, and decision-focused reliability evaluation: Evaluation where different errors carry different downstream costs and acceptance or abstention is assessed by expected loss, utility, regret, or decision consequences.

Open gaps this round must close (a paper that speaks to one of these
is worth admitting even when its topic wording is unusual):
- gap-1 [ACADEMIC, HIGH]: No admitted study validates one end-to-end evaluation scheme that jointly measures claim correctness, evidence attribution correctness, citation or evidence completeness, temporal or current-state correctness, omission, calibrated uncertainty, and abstention while preserving separate denominators for those dimensions. The corpus validates individual components and smaller combinations.
    suggested query: "joint evaluation framework" factuality attribution completeness temporal correctness omission calibration abstention "free-form generation" multi-source
    searched in rounds: [1, 2, 3] (still open)
- gap-2 [ENGINEERING, HIGH]: The corpus contains no direct evaluation on private workplace email or Teams-style communication with realistic revisions, quoted history, conflicting updates, delayed or out-of-order arrival, versioned attachments, and permission-constrained evidence. Target-domain fixtures and gold data remain an engineering validation gap.
- gap-4 [ACADEMIC, HIGH]: The corpus does not establish a general evidence-completeness method that jointly handles compound claims, partially supportive evidence, multiple complementary sources, and temporally versioned evidence. Separate studies cover subsets of these conditions.
    suggested query: "evidence completeness" compound claims partial support complementary evidence multi-source temporal versioning provenance evaluation
    searched in rounds: [1, 2, 3] (still open)
- gap-5 [ACADEMIC, HIGH]: Report-level omission has substantial benchmark coverage, but the corpus still does not establish omission detection for evolving workplace work items, due information, superseded facts, or decision-relevant state across time.
    suggested query: "omission detection" longitudinal summarization work-item state superseded facts due dates temporal updates decision-relevant information
    searched in rounds: [1, 2, 3] (still open)
- gap-6 [ENGINEERING, HIGH]: A target-domain human-review protocol remains an engineering gap: representative or risk-stratified sampling, minimum human-review volume, multi-rater adjudication, confusion matrices, abstention treatment, coverage reporting, and validation of any LLM-assisted judge against independent human judgments remain project-specific choices.
- gap-7 [ENGINEERING, MEDIUM]: The corpus demonstrates evaluator-optimization effects, rating indeterminacy, abstention sensitivity, and directional judge bias but does not provide a project-specific procedure for preventing acceptance criteria from being overfit to the same automatic evaluator used during development. Independent holdouts, evaluator separation, and regression checks remain an engineering validation problem.
- gap-8 [ACADEMIC, MEDIUM]: Calibration under continuing temporal or distributional change remains open for non-stationary free-form communication streams. The corpus supplies adaptive coverage results, cross-domain calibration studies, benchmark-aging evidence, and structured-generation risk-control results, but not one validated selective-prediction method for continuously changing workplace communication.
    suggested query: "selective prediction" "non-stationary" free-form generation online calibration concept drift abstention adaptive conformal temporal stream
    searched in rounds: [1, 2, 3] (still open)
Decisions:
- ADMIT — name the stream and why the abstract shows the contribution.
- REJECT — name the reason: topic words match but the capability does not,
  the evidence duplicates a paper already admitted, or the claim is out of
  scope.
- PENDING — the abstract cannot settle it; say what would.

`identity: UNCHECKED` means the host could not confirm the paper's identifier
with the provider. That is not proof the paper is wrong, but prefer a
VERIFIED paper when the two are otherwise equal, and say so in the reason.


## Project context you must work within

This is the project's own description of the problem, its boundaries,
and the distinctions it needs preserved. It governs what counts as
relevant; the academic task names alone do not.

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

## From Topic 03 — Cross-thread Topic identity and incremental continuity

*Completed 2026-09-16. 4 rounds, 50 papers, report validated PASS 0.94.*

**Handed to Topic 10.** Calibration under non-stationary workplace streams,
as general methodology. Topic 03 records it as an open ACADEMIC gap (MEDIUM):
its corpus does not settle how confidence should behave when the stream's
distribution shifts.

**Boundary.** Topic 03 retains identity-specific uncertainty. The relative
cost of a false merge against a false split is a Topic 03 decision, not a
general calibration question.

## From Topic 04 — Reference resolution and response scope

*Completed 2026-09-16. 4 rounds, 47 papers, report validated PASS.*

**Handed to Topic 10.** Two open ENGINEERING gaps that are evaluation
questions rather than literature questions. Neither is closable by more
papers; Topic 04 searched four rounds and the required contract is
msgloom-specific.

- **A combined annotation and evaluation contract** covering exact, partial,
  ambiguous, unsupported, discontinuous, multiple-antecedent, composite and
  no-link outcomes. Exact links, span overlap, zero-link outcomes and
  multi-antecedent partial credit must be scored **separately**: a single
  aggregate can reward structurally unsafe behaviour and hide over-broad
  links. Topic 04 found the ingredients in the literature but not the
  combined scheme.
- **An abstention and asymmetric error-cost policy.** An over-broad approval
  link and a missed link do not cost the same, so a threshold cannot be read
  off a benchmark score. Topic 04's suggested form is to measure false-broad,
  missed and wrong-link errors separately against an explicit cost function,
  using independent synthetic and adversarial sets first and authorized
  workplace data later.

**Boundary.** Topic 10 owns the general calibration and attribution
methodology. Topic 04 keeps ownership of what the outcomes *mean*: which
proposition a response applies to, and what partial or absent scope is.

## From Topic 05 — Action items, requests, commitments and decisions

*Completed 2026-09-16. 4 rounds, 48 papers.*

**Handed to Topic 10.** Four open ENGINEERING gaps that are evaluation
questions rather than literature questions, and none closable by more papers:

- **G6** An argument-level benchmark and adversarial fixture suite covering
  implicit owners, several actions in one sentence, shared deadlines,
  conditional and negated actions, overlapping request/commitment labels,
  quoted-history contamination and attachment references. False positives,
  false negatives and each argument must be scored **separately**.
- **G7** Controlled comparison of sentence-local, message-level and
  selectively expanded thread context, with ablations, because the literature
  shows both context gains and context-induced degradation.
- **G8** Zoning author, quoted and forwarded content while preserving
  provenance, measuring both false-obligation reduction and recall loss.
- **G9** An uncertainty-preserving output with abstention, measuring whether
  leaving a field unresolved reduces false obligations without unacceptable
  recall loss.

**Boundary.** Topic 10 owns generic calibration and attribution methodology.
Topic 05 keeps ownership of what an action, owner, deadline or condition
means, and of what counts as a false obligation.

## From Topic 06 — Work-item state, event factuality, time, conflicting revisions

*Completed 2026-09-17. 4 rounds, 38 papers, no duplicate records. Every
round's synthesis was accepted by the independent review at the first attempt
— faithfulness 0.93 to 0.95 — which no earlier Topic managed. Stopped on
`round_cap_reached`. All eight gaps remain open and none was downgraded.*

**Handed to Topic 10.** Three open ENGINEERING gaps that are evaluation
questions rather than literature questions, and none closable by more papers.
This follows the pattern set by Topics 03, 04 and 05.

- **Gap 6** An end-to-end adversarial longitudinal suite covering
  plan→cancel, approve→revoke, deadline changes, contradictory same-time
  updates, out-of-order ingestion, stale late-arriving evidence, and
  completion claims later corrected. Topic 06's own suggested resolution
  requires that future evidence be **hidden from the prediction input**, that
  both false completion and failure-to-close be measured **separately**, and
  that the full evidence lineage be preserved.
- **Gap 7** A benchmark combining message time, effective/event time,
  deadline/constraint time and collection/version time, with fixtures where
  the four deliberately disagree, and current-state reconstruction evaluated
  at several observation cutoffs.
- **Gap 8** A provenance-preserving implementation with append-only
  observations and assessments, a reproducibly derived current-state
  projection, replay from empty state, and regression tests proving
  historical evidence cannot be silently overwritten.

**Also relevant to calibration.** Topic 06's Gap 5 — claimed versus
independently corroborated completion — is an abstention and confidence
question as much as an extraction one.

**Boundary.** Topic 10 owns generic attribution, calibration and selective
prediction methodology. Topic 06 keeps ownership of what a state, a
supersession or a corroborated completion *means*, and of what counts as a
false "completed".

*Basis: the ownership map — Topic 06's relationship table entry for 10, and
the precedent of Topics 03/04/05 routing their ENGINEERING gaps here — plus
Topic 06's Gaps 6, 7, 8 and their suggested resolutions, quoted from its
Research Gaps section. Topic 06's report does not name Topic 10 by number.*

## From Topic 08 — Email, image, table and attachment understanding

*Completed 2026-09-17. 4 rounds, 53 corpus records — **52 distinct papers**,
because one study was admitted twice under two identifiers. Rounds 2 and 4
were each rejected once and accepted after one repair; rounds 1 and 3 passed
at the first attempt. Stopped on `round_cap_reached`. All eight gaps remain
open and none was downgraded.*

**Handed to Topic 10.** Four open ENGINEERING gaps that are evaluation
questions rather than literature questions, following the pattern set by
Topics 03, 04, 05 and 06.

- **gap-5 (HIGH)** End-to-end behaviour when extraction or grounding is
  unsupported, incomplete or wrong. Unsupported extraction, missing evidence,
  failed localisation, ambiguous grounding and downstream reasoning failure
  must be **distinguishable outcomes**, not one bucket.
- **gap-6 (HIGH)** Robustness of candidate extraction and structure
  preservation on heterogeneous workplace-style documents.
- **gap-7 (MEDIUM)** Operational scaling on long documents, large tables and
  realistic workbooks. The corpus reports page-routing cost, evidence-graph
  overhead and document-length degradation, but no target-workload latency,
  memory or throughput.
- **gap-8 (HIGH)** One evaluation measuring semantic correctness, extraction
  completeness, exact provenance, unsupported-evidence handling and
  preservation together, rather than each alone.

**A methodological note Topic 10 should carry.** Topic 08 round 2 was
rejected because its synthesis cited one study twice — under a DOI and under
a bare `manual-` identifier — as independent corroboration. The structural
integrity checks passed; only the reader caught it. Evidence counting by
record rather than by distinct study is a live failure mode, and this topic's
own corpus still contains that pair.

**Boundary.** Topic 10 owns generic grounding-correctness, attribution and
completeness methodology. Topic 08 keeps ownership of what a correct
extraction, a grounded region or a preserved structure *means*.

*Basis: the ownership map — Topic 08's relationship table entry for 10
("evaluates extraction completeness, grounding/citation correctness, and
omission of multimodal evidence") and the precedent of Topics 03/04/05/06 —
plus Topic 08's gaps 5–8, quoted from gaps.json, and its round-2 review
verdict. The report does not name Topic 10 by number.*

Candidates:
- paper_id `2405.05160` [identity: VERIFIED] Selective Classification Under Distribution Shifts (2024, arXiv)
    Studies selective classification under label, covariate, and out-of-distribution shifts and evaluates confidence scores and rejection strategies when test distributions differ from training.
- paper_id `doi-10-1038-s41598-026-40637-w` [identity: UNCHECKED] Conformal selective prediction with cost aware deferral for safe clinical triage under distribution shift (2026, Scientific Reports)
    Combines calibrated probabilistic prediction, conformal uncertainty sets, and cost-aware deferral, evaluating selective decisions and risk-coverage behavior on temporally separated in- and out-of-distribution clinical data.
- paper_id `2006.09462` [identity: VERIFIED] Selective Question Answering under Domain Shift (2020, ACL 2020)
    Studies selective question answering when deployment mixes in-domain and shifted examples, using a calibrator to decide which answers to return and evaluating error as coverage changes.
- paper_id `doi-10-18653-v1-2021-acl-long-84` [identity: UNCHECKED] The Art of Abstention: Selective Prediction and Error Regularization for Natural Language Processing (2021, ACL-IJCNLP 2021)
    Studies selective prediction for NLP, compares confidence estimators used for abstention, and introduces error regularization to improve the relationship between retained coverage and prediction risk.
- paper_id `1705.08500` [identity: VERIFIED] Selective Classification for Deep Neural Networks (2017, NeurIPS 2017)
    Develops selective classifiers for deep networks that can reject predictions to meet a desired risk level with high probability and evaluates performance through the risk-coverage trade-off.
- paper_id `doi-10-1609-aaai-v40i40-40667` [identity: UNCHECKED] COIN: Uncertainty-Guarding Selective Question Answering for Foundation Models with Provable Risk Guarantees (2026, AAAI 2026)
    Develops uncertainty-aware selective question answering with statistical risk guarantees, using conformal techniques to control errors among answers that a foundation model elects to provide.
- paper_id `manual-2be3626f9e` [identity: UNCHECKED] Optimal Strategies for Reject Option Classifiers (2023, Journal of Machine Learning Research)
    Provides a unified treatment of reject-option classification under cost-based, bounded-improvement, and bounded-abstention formulations, including optimal strategies connecting selective risk and achievable coverage.
- paper_id `doi-10-1109-tit-1970-1054406` [identity: UNCHECKED] On optimum recognition error and reject tradeoff (1970, IEEE Transactions on Information Theory)
    Characterizes the trade-off between recognition error and rejection and derives an optimal rejection rule, providing a foundational decision-theoretic basis for selective prediction.
- paper_id `doi-10-1016-j-jbi-2026-105084` [identity: UNCHECKED] Selective classification under imbalance in multiclass settings: A novel metric for bias-aware risk–coverage evaluation (2026, Journal of Biomedical Informatics)
    Shows that aggregate risk-coverage evaluation can hide class-specific failures under imbalance and proposes class-aware measures and class-conditional rejection analysis.
- paper_id `2208.02814` [identity: VERIFIED] Conformal Risk Control (2022, ICLR 2024)
    Generalizes conformal methods from set coverage to control of expected monotone loss, with extensions addressing distribution shift and other risk functions relevant to selective deployment.
- paper_id `2606.27736` [identity: VERIFIED] ToE: A Hierarchical and Explainable Claim Verification Framework with Dynamic Multi-source Evidence Retrieval and Aggregation (2026, arXiv)
    Uses a hierarchical argument tree with iterative decomposition, dynamic multi-source retrieval, evidence evaluation, aggregation, and verification to handle complex claims requiring evidence from multiple sources.
- paper_id `doi-10-1016-j-jisa-2025-104120` [identity: UNCHECKED] Conformal prediction for labelling and updating online models in the presence of concept drift in cybersecurity (2025, Journal of Information Security and Applications)
    Investigates conformal prediction as a mechanism for assigning labels and updating online models under concept drift, directly testing recalibration and model adaptation in a changing data stream.
- paper_id `doi-10-64898-2025-11-28-25341233` [identity: UNCHECKED] CLIN-SUMM: Incremental Longitudinal Summarization of Clinical Notes Enables Scalable Representation and Early Disease Prediction (2025, medRxiv)
    Constructs longitudinal patient representations incrementally, summarizing newly documented information at each encounter while preserving temporal ordering and avoiding future information leakage.
- paper_id `2211.07145` [identity: VERIFIED] Towards Understanding Omission in Dialogue Summarization (2022, ACL 2023)
    Introduces explicit omission annotations and an omission-detection task for dialogue summaries, evaluating which important source information is absent from generated summaries rather than only measuring overall similarity or faithfulness.
- paper_id `2208.08401` [identity: VERIFIED] Conformal Inference for Online Prediction with Arbitrary Distribution Shifts (2022, arXiv)
    Develops online conformal inference for sequences whose distributions may vary arbitrarily, using adaptive procedures and regret-style guarantees to respond to non-stationarity rather than assuming a fixed exchangeable stream.
- paper_id `manual-80ff27ab7b` [identity: UNCHECKED] Score-Based Diffusion Priors for Adaptive Conformal Inference under Distribution Shift (2026, UAI 2026)
    Combines adaptive conformal inference with score-based diffusion priors and online recalibration to improve coverage behavior under temporal and covariate distribution shifts.
- paper_id `2204.02007` [identity: VERIFIED] Fact Checking with Insufficient Evidence (2022, Transactions of the Association for Computational Linguistics)
    Studies whether available evidence is sufficient for fact verification and develops diagnostics based on removing evidence constituents or sentences, separating evidence sufficiency from the final veracity decision.
- paper_id `doi-10-1155-2016-1340973` [identity: UNCHECKED] Mining Sequential Update Summarization with Hierarchical Text Analysis (2016, Mobile Information Systems)
    Addresses sequential update summarization for evolving information streams using hierarchical text analysis and evaluates update quality with temporal-summarization measures including comprehensiveness and latency-sensitive gain.
- paper_id `2503.14797` [identity: VERIFIED] FACTS&EVIDENCE: An Interactive Tool for Transparent Fine-Grained Factual Verification of Machine-Generated Text (2025, NAACL 2025 Demonstrations)
    Provides interactive fine-grained verification by breaking generated text into claims, retrieving multiple evidence sources, and exposing evidence and explanations so users can inspect attribution and support.
- paper_id `2604.20860` [identity: VERIFIED] RealRoute: Dynamic Query Routing System via Retrieve-then-Verify Paradigm (2026, arXiv)
    Proposes source-agnostic parallel retrieval followed by verification and dynamic routing across heterogeneous information sources, targeting evidence completeness and multi-hop questions rather than relying on one retrieval pass.
- paper_id `2305.11859` [identity: VERIFIED] Complex Claim Verification with Evidence Retrieved in the Wild (2023, NAACL 2024)
    Builds a complex-claim verification pipeline combining claim decomposition, web retrieval, fine-grained evidence selection, evidence summarization, and final veracity prediction, while examining incompleteness in retrieved evidence.
- paper_id `2411.15993` [identity: VERIFIED] Investigating Factuality in Long-Form Text Generation: The Roles of Self-Known and Self-Unknown (2024, arXiv)
    Studies factuality at the atomic-claim level in long-form generation and examines whether models can distinguish claims they know from claims they do not know, connecting claim support with uncertainty behavior.
- paper_id `2511.01101` [identity: VERIFIED] TSVer: A Benchmark for Fact Verification Against Time-Series Evidence (2025, EMNLP 2025)
    Introduces a benchmark in which real-world claims must be verified against time-series evidence, with annotations covering relevant time frames, verdicts, and justifications.
- paper_id `doi-10-1016-j-patcog-2023-109839` [identity: UNCHECKED] Unsupervised update summarization of news events (2023, Pattern Recognition)
    Presents unsupervised incremental summarization for evolving events, emphasizing novelty, cohesion, and information updates so later summaries avoid simply repeating earlier material.
- paper_id `doi-10-3390-math14101769` [identity: UNCHECKED] Atomic Contrastive Verification: Fine-Grained Fact-Checking via Claim Decomposition and Knowledge Graph-Grounded Contrastive Reasoning (2026, Mathematics)
    Decomposes text into atomic claims and applies knowledge-graph-grounded contrastive reasoning for fine-grained verification, including contradictions and temporal distortions that sentence-level scoring can obscure.

JSON schema:
{
 "$schema": "http://json-schema.org/draft-07/schema#",
 "title": "PaperAdmission",
 "description": "Per-candidate admission decision. A paper enters the reading round only when it materially strengthens an authorized research stream; a paper count is never a reason to admit.",
 "type": "object",
 "required": [
  "decisions"
 ],
 "properties": {
  "round": {
   "type": "integer",
   "minimum": 1
  },
  "streams": {
   "type": "array",
   "description": "The authorized research streams this round admits against.",
   "items": {
    "type": "object",
    "required": [
     "id",
     "description"
    ],
    "properties": {
     "id": {
      "type": "string",
      "minLength": 1
     },
     "description": {
      "type": "string",
      "minLength": 1
     }
    }
   }
  },
  "decisions": {
   "type": "array",
   "minItems": 1,
   "items": {
    "type": "object",
    "required": [
     "paper_id",
     "decision",
     "reason"
    ],
    "properties": {
     "paper_id": {
      "type": "string",
      "minLength": 1
     },
     "decision": {
      "type": "string",
      "enum": [
       "ADMIT",
       "REJECT",
       "PENDING"
      ]
     },
     "reason": {
      "type": "string",
      "minLength": 1
     },
     "stream_id": {
      "type": "string",
      "description": "Required for ADMIT: the stream this paper materially strengthens."
     },
     "role": {
      "type": "string",
      "enum": [
       "DIRECT",
       "TRANSFER"
      ]
     },
     "confidence": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0
     }
    }
   }
  },
  "notes": {
   "type": "string"
  }
 },
 "additionalProperties": true
}

Reply with one block containing one JSON object with a `decisions` array
covering every paper_id above, and a `streams` array describing the streams
you admitted against.
===BEGIN admission.json===
<content>
===END admission.json===
