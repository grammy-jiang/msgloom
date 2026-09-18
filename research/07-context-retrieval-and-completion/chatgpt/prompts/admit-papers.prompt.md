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

Research topic: **Unified iterative RAG stopping and provenance control under distribution shift: search specifically for controllers that combine structured evidence sufficiency with temporal/version-aware provenance and calibrated or conformal risk-controlled stopping, including any systems that additionally integrate permission-aware access or bounded retrieval budgets.**

Decide which of these candidates enters the reading round. Admit a paper only
when it materially strengthens one of the research streams below, and the
abstract shows that, not merely shared vocabulary. A paper count is never a
reason to admit: admitting six of twenty is a valid answer, and so is
admitting none. Rejecting a paper here costs little; reading a paper that
cannot strengthen a stream costs a reading slot that a better paper needed.

Research streams:
- F1 [TRANSFER] Context-dependent gap-to-query transformation: Convert an explicit unresolved reference, missing field, or contextual dependency into a standalone retrieval request while preserving the intended semantics.
- F2 [DIRECT] Structured evidence decomposition and compositional retrieval: Represent a complex information need as subquestions, expected claims, entities, relations, joins, or evidence requirements, and use the evolving structure to decide what evidence to fetch next.
- F3 [DIRECT] Adaptive, active, and iterative RAG control: Dynamically choose whether, when, and how much to retrieve and repeatedly update retrieval decisions using the current generation or reasoning state.
- F4 [DIRECT] Evidence-coverage and verification-aware stopping: Terminate retrieval when accumulated evidence has verified the required claims or subgoals, rather than merely when generator confidence is high or a fixed hop count is reached.
- F5 [TRANSFER] Selective QA and abstention under distribution shift: Answer only when predicted risk is acceptable and otherwise abstain, with explicit attention to accuracy-coverage or risk-coverage tradeoffs and out-of-domain inputs.
- F6 [DIRECT] Conformal and risk-controlled retrieval-augmented prediction: Apply conformal prediction or conformal risk control to retrieval, RAG outputs, prediction sets, or evidence selection so that reliability statements have finite-sample or distribution-free statistical grounding.
- F7 [DIRECT] Temporal information retrieval and temporal QA: Retrieve information using temporal intent, document/content time, temporal relevance, historical constraints, or time-sensitive question semantics.
- F8 [TRANSFER] Valid-time, transaction-time, and bitemporal data semantics: Distinguish when a fact is true in the modeled world from when it was recorded, stored, or observed by an information system.
- F9 [DIRECT] Version-aware retrieval and versioned document QA: Retrieve and reason over evolving document versions while explicitly modeling version identity, supersession, change history, and version-sensitive questions.
- F10 [DIRECT] Evidence provenance, source attribution, and claim-level grounding: Preserve and evaluate which source evidence supports generated statements, including source identity, evidence spans, lineage, and claim-to-source relationships.
- F11 [DIRECT] Permission-aware and policy-gated retrieval: Apply user-, tenant-, role-, or attribute-specific authorization policies during retrieval so that only permitted evidence can enter the reasoning context.
- F12 [DIRECT] Budgeted and cost-aware evidence acquisition: Choose retrieval depth, evidence sources, models, or access tiers under explicit budgets for retrieval calls, evidence access, tokens, computation, latency, or monetary cost.
- F13 [DIRECT] Failure-aware answerability and evidence-absence handling: Determine whether an answer is currently supportable and distinguish insufficient or missing evidence from a supported negative answer.
- F14 [DIRECT] Integrated retrieval-controller architectures: Single controllers or end-to-end systems that combine multiple control dimensions such as structured gap tracking, iterative retrieval, temporal validity, provenance, permission checks, calibrated stopping, abstention, and bounded cost.
- F15 [DIRECT] Workplace and enterprise multi-source evidence investigation: Evaluation over heterogeneous organizational messages, documents, attachments, and repositories where evidence may be stale, conflicting, versioned, permission-restricted, or distributed across sources.

Open gaps this round must close (a paper that speaks to one of these
is worth admitting even when its topic wording is unusual):
- gap-1 [ACADEMIC, HIGH]: Structured gap representations remain insufficiently validated for temporal constraints, multi-entity joins, and complex compositional evidence requirements; the corpus contains structured-gap, temporal-retrieval, and query-planning methods, but no admitted study evaluates these capabilities together.
    suggested query: "structured evidence gap" temporal constraints multi-entity joins compositional retrieval iterative RAG
    searched in rounds: [1, 2, 3] (still open)
- gap-2 [ACADEMIC, HIGH]: No admitted study validates an iterative evidence-gap retrieval loop that jointly preserves document-version lineage, freshness or effective-time validity, and structured sufficiency decisions.
    suggested query: "version-aware retrieval" temporal provenance iterative RAG document lineage freshness effective-time sufficiency
    searched in rounds: [1, 2, 3] (still open)
- gap-3 [ACADEMIC, HIGH]: Stopping reliability under domain shift remains open: sufficiency, confidence, conformal, and stability signals guide stopping in separate studies, but no admitted study provides a general bounded-risk iterative-RAG stopping guarantee under distribution shift.
    suggested query: "iterative RAG" calibrated stopping domain shift conformal risk control selective prediction adaptive retrieval
    searched in rounds: [1, 2, 3] (still open)
- gap-4 [ENGINEERING, HIGH]: The corpus does not test a bounded replenishment loop in which unauthorized candidates are filtered through native IAM, evidence sufficiency is reassessed, and another permission-constrained query is issued when authorized evidence remains incomplete.
- gap-5 [ENGINEERING, HIGH]: The evaluated systems do not jointly distinguish empty retrieval, authorization denial, unavailable source, unsupported extraction, exhausted budget, and true negative evidence as separate terminal or retry conditions.
- gap-6 [ENGINEERING, MEDIUM]: An end-to-end cost evaluation covering retrieval calls, retrieved passages or tokens, planner or judge inference, reranking, permission-check latency, and total wall-clock latency remains absent from the admitted corpus.
- gap-7 [ENGINEERING, HIGH]: The corpus lacks a workplace-communication evaluation combining explicit evidence gaps with heterogeneous messages and documents, multi-hop dependencies, permission restrictions, stale or conflicting evidence, and bounded retrieval.
- gap-8 [ACADEMIC, HIGH]: No admitted study validates a single controller that jointly handles structured evidence gaps, permission-aware source access, version lineage, temporal validity, calibrated stopping, abstention, and total-cost budgeting; the reported successes remain component-level or cover smaller subsets of these functions.
    suggested query: "adaptive RAG controller" permission-aware provenance temporal version calibrated stopping abstention budget
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

*Completed 2026-09-16. 4 rounds, 50 papers, report validated PASS 0.94. Seven
gaps left open.*

**Handed to Topic 07.** When the available material does not settle whether
two messages concern the same work matter, what should be retrieved next.
Topic 03 records this as an open ENGINEERING gap (MEDIUM): the operational
strategy for Phase 2 evidence seeking is unresolved.

**Boundary.** Topic 07 owns turning an unresolved identity question into a
targeted evidence need. Topic 03 keeps ownership of what counts as continuity
once the evidence arrives, and of the cost of a false merge against a false
split.

## From Topic 04 — Reference resolution and response scope

*Completed 2026-09-16. 4 rounds, 47 papers, report validated PASS.*

**Handed to Topic 07.** The case where a reference has **no resolvable
antecedent in the available material**. Topic 04's guidance is explicit: when
missing context is the real problem, that is an evidence need for Topic 07,
not a reference-model failure.

**What Topic 04 does with it.** It leaves the reference marked unresolved
rather than forcing a link, so Topic 07 receives an explicit
missing-antecedent signal rather than a wrong answer. Preserving that
distinction is deliberate: an invented link is more damaging than an admitted
gap.

**Boundary.** Topic 04 owns what the reference means once the material exists.
Topic 07 owns deciding what to fetch and stopping when enough has been
fetched.

## From Topic 05 — Action items, requests, commitments and decisions

*Completed 2026-09-16. 4 rounds, 48 papers.*

**Handed to Topic 07.** A missing owner, object or context becoming an
explicit retrieval need. Topic 05's uncertainty-preserving output leaves
owner, deadline, condition or act subtype **unresolved** rather than guessing,
which is its open engineering gap G9; each unresolved field is a concrete
evidence need for Topic 07.

**Boundary.** Topic 07 owns deciding what to fetch and when to stop. Topic 05
owns what the field means once the evidence arrives.

## From Topic 06 — Work-item state, event factuality, time, conflicting revisions

*Completed 2026-09-17. 4 rounds, 38 papers, no duplicate records. Every
round's synthesis was accepted by the independent review at the first attempt
— faithfulness 0.93 to 0.95 — which no earlier Topic managed. Stopped on
`round_cap_reached`. All eight gaps remain open and none was downgraded.*

**Handed to Topic 07.** An unresolved state becomes an explicit
missing-evidence requirement. Topic 06's report names this directly: evidence
retrieval should be evaluated jointly with state resolution "so unresolved
states can emit explicit missing-evidence requirements to Topic 07 rather
than hallucinating closure".

**What Topic 06 established.** Separate literatures cover factuality,
temporal ordering, commitment lifecycle, provenance and conflicting evidence,
and each works in its own setting. None of them was shown to work jointly.
An unresolved state is therefore the expected output, not a defect, and the
honest response to one is to ask for evidence rather than to guess.

**What Topic 06 left open, and Topic 07 must not treat as settled:**

- *(ACADEMIC, HIGH, Gap 3)* No joint evaluation of factuality, temporal
  ordering, lifecycle state, contradiction and provenance in one model.
  Component success does not establish integrated correctness.
- *(ACADEMIC, HIGH, Gap 5)* Nothing distinguishes a *claimed* completion from
  an independently corroborated one. A retrieval request built on a claimed
  state may be asking about work that is not actually done.
- *(ENGINEERING, HIGH, Gap 7)* Message time, effective time, deadline time
  and collection/version time have never been benchmarked together. A
  retrieval scoped by the wrong clock returns stale or retroactive evidence.

**Boundary.** Topic 07 owns deciding what to fetch, in what order, and when
to stop. Topic 06 owns what the state *is* once the evidence arrives, and
owns saying that it is still unresolved.

*Basis: Topic 06's report names Topic 07 explicitly (Future Directions 6);
the gaps are quoted from its Research Gaps table.*

## From Topic 08 — Email, image, table and attachment understanding

*Completed 2026-09-17. 4 rounds, 53 corpus records — **52 distinct papers**,
because one study was admitted twice under two identifiers. Rounds 2 and 4
were each rejected once and accepted after one repair; rounds 1 and 3 passed
at the first attempt. Stopped on `round_cap_reached`. All eight gaps remain
open and none was downgraded.*

**Handed to Topic 07.** A retrieved document, attachment or workbook still
has to be interpreted, and the evidence inside it located precisely. Topic 07
owns deciding what to fetch and when to stop; Topic 08 owns what the fetched
artefact says and where in it the claim sits — which page, region, cell or
version.

**What Topic 08 established.** Document-VQA work localises evidence to pages,
regions and answer spans; spreadsheet work localises to sheets, cells and
formulas; version-oriented work demonstrates version recovery, evolving
-document citation and version-aware retrieval. Each works in its own
setting. None was shown to work as one pipeline.

**What Topic 08 left open, and Topic 07 must not treat as settled:**

- *(ACADEMIC, HIGH, gap-1)* No complete method maintains evidence provenance
  across successive workplace attachment versions. A citation into "the
  attachment" is not yet a citation into a known version of it.
- *(ACADEMIC, HIGH, gap-4)* No admitted paper validates one end-to-end
  provenance representation identifying attachment version, page, document
  element and region together. Topic 07 cannot assume a retrieved span
  carries a usable address.
- *(ENGINEERING, HIGH, gap-5)* End-to-end behaviour when extraction or
  grounding is unsupported, incomplete or wrong is insufficiently exercised.
  A failed extraction must be distinguishable from an absent answer, which is
  a stopping-criterion concern as much as an extraction one.

**Boundary.** Topic 07 owns the retrieval decision and its budget. Topic 08
owns interpretation and grounding of whatever comes back.

*Basis: Topic 08's report names Topic 07 explicitly; the gaps are quoted from
its gaps.json.*

Candidates:
- paper_id `2603.08819` [identity: VERIFIED] Beyond Relevance: On the Relationship Between Retrieval and RAG Information Coverage (2026, ICTIR 2026)
    This work studies whether upstream retrieval measurements predict the information coverage of downstream RAG answers. Across text and multimodal RAG benchmarks, coverage-oriented retrieval metrics correlate more strongly with generated-response coverage than ordinary relevance metrics when the task requires broad information coverage. The results also show that iterative RAG can partially decouple final generation quality from initial retrieval effectiveness.
- paper_id `2608.02195` [identity: VERIFIED] MEGRAG: Multi-Granular Evidence Graphs for Answer-Aware Multi-Hop RAG (2026)
    MEGRAG represents multi-hop reasoning as a path-structured, multi-granular evidence graph linking passages, sentences, and extracted triples. At each stage it uses an intermediate answer and prior reasoning to decide whether the original query has been resolved; unresolved cases produce an explicit missing-information diagnosis and focused next query, while resolved cases stop retrieval. This directly couples structured evidence representation, gap identification, iterative retrieval, and semantic stopping.
- paper_id `2607.06507` [identity: VERIFIED] DynaKRAG: A Unified Framework for Learnable Evidence Control in Multi-Hop Retrieval-Augmented Generation (2026)
    DynaKRAG formulates multi-hop evidence acquisition as state-conditioned control over atomic evidence operations. Its shared evidence state records retrieved documents, frontier information, query/action history, bridge candidates, and diagnostic feedback; a learned controller can choose retrieval, query rewriting, bridge expansion, gap-directed retrieval, sufficiency checking, or stopping. Controlled experiments show that sufficiency feedback and learned operation selection materially improve multi-hop QA, while additional retrieval is not uniformly beneficial.
- paper_id `manual-2bb76a9136` [identity: UNCHECKED] IDCR: Information-Directed Conformal Retrieval (2026, UAI 2026)
    IDCR selects evidence according to its effect on downstream conformal uncertainty rather than semantic similarity alone. It minimizes conformal prediction-set volume while preserving distribution-free coverage, derives a monotone submodular retrieval objective, and uses a marginal-gain-separation gate to route uncertain retrieval steps to lookahead search. This provides a direct mechanism for risk-aware evidence acquisition, although it is not an iterative free-form RAG stopping guarantee.
- paper_id `2510.22344` [identity: VERIFIED] FAIR-RAG: Faithful Adaptive Iterative Refinement for Retrieval-Augmented Generation (2025)
    FAIR-RAG uses a Structured Evidence Assessment module that decomposes a question into a checklist of required findings, audits accumulated evidence, and explicitly records confirmed facts and unresolved information gaps. Gap items drive targeted follow-up queries, and the loop repeats until the evidence is judged sufficient for faithful generation. It is evaluated on HotpotQA, 2WikiMultiHopQA, and MuSiQue.
- paper_id `manual-80ff27ab7b` [identity: UNCHECKED] Score-Based Diffusion Priors for Adaptive Conformal Inference under Distribution Shift (2026, UAI 2026)
    DiffConf develops adaptive conformal inference for temporal and covariate distribution shifts using score-based diffusion priors plus online recalibration. It provides finite-sample marginal coverage guarantees while the data distribution evolves and analyzes additional coverage behavior under drift assumptions. This is transfer evidence for online risk calibration in a non-stationary RAG controller.
- paper_id `2505.02811` [identity: VERIFIED] Knowing You Don't Know: Learning When to Continue Search in Multi-round RAG through Self-Practicing (2025, SIGIR 2025)
    SIM-RAG trains a lightweight information-sufficiency critic from synthetic multi-round retrieval trajectories generated through self-practice. At inference time the critic evaluates after each round whether enough information has been retrieved and guides the decision to continue searching or stop. The method is evaluated across multiple RAG benchmarks without requiring human-labeled intermediate retrieval supervision.
- paper_id `2307.04642` [identity: VERIFIED] TRAQ: Trustworthy Retrieval Augmented Question Answering via Conformal Prediction (2024, NAACL 2024)
    TRAQ applies conformal prediction to retrieval-augmented open-domain QA and constructs prediction sets guaranteed to contain a semantically correct response with high probability. Bayesian optimization is used to reduce prediction-set size while preserving the statistical correctness target. The guarantee is end-to-end for QA but does not control iterative retrieval depth.
- paper_id `2602.20735` [identity: VERIFIED] RMIT-ADM+S at the MMU-RAG NeurIPS 2025 Competition (2026, NeurIPS 2025 MMU-RAG Competition Workshop)
    The paper presents R2RAG, which dynamically adapts retrieval strategy using query complexity and evidence sufficiency. For iterative cases, accumulated evidence is reviewed for coverage of query subparts and remaining knowledge gaps; further queries target those gaps, while stopping also respects a context-token threshold and a bounded iteration cap. The system was evaluated in the MMU-RAG competition's dynamic setting.
- paper_id `doi-10-1609-aaai-v39i12-33353` [identity: UNCHECKED] Towards Trustworthy Knowledge Graph Reasoning: An Uncertainty Aware Perspective (2025, AAAI 2025)
    UAG introduces conformal uncertainty quantification into multi-step reasoning that combines knowledge graphs and language models. An error-rate control module allocates error rates across components of the multi-step process so the overall system can achieve a predefined coverage target. Although not an iterative document-RAG stopping controller, it is directly relevant to distributing a calibrated risk budget across structured evidence-acquisition and reasoning stages.
- paper_id `2506.05167` [identity: VERIFIED] ECoRAG: Evidentiality-guided Compression for Long Context RAG (2025, Findings of the Association for Computational Linguistics: ACL 2025)
    ECoRAG compresses retrieved documents according to evidentiality rather than general relevance alone. After compression it explicitly assesses whether the retained content supplies sufficient evidence and retrieves more when it does not, continuing until sufficiency is reached. Experiments on open-domain QA also evaluate latency and token-use savings.
- paper_id `2405.05160` [identity: VERIFIED] Selective Classification Under Distribution Shifts (2024, Transactions on Machine Learning Research)
    The paper develops generalized selective classification for deployment data containing in-distribution, covariate-shifted, and label-shifted or out-of-distribution samples. It studies confidence functions for deciding which cases should be rejected so that error on the retained predictions is controlled more reliably under shift. The framework is transfer evidence for abstention and risk-coverage evaluation of RAG controllers.
- paper_id `2609.08364` [identity: VERIFIED] SentryLine: Evidence-Grounded Question Answering over Evolving Documents in Oncology Care (2026)
    SENTRYLINE targets question answering over living oncology guidelines whose recommendations change across versioned documents. Its hierarchical RAG pipeline returns inline evidence citations together with factual and temporal verification reports and drift notes that identify guideline updates. ASCOBENCH evaluates multi-turn questions against expert-authored answers over evolving guideline evidence.
- paper_id `2506.20978` [identity: VERIFIED] Response Quality Assessment for Retrieval-Augmented Generation via Conditional Conformal Factuality (2025, SIGIR 2025)
    Conformal-RAG applies conformal prediction to quality assessment and filtering of subclaims in RAG responses. It provides group-conditional coverage across multiple subdomains without requiring manually constructed conformal sets and uses internal RAG information to retain more high-quality claims at a fixed reliability target. The method controls final response quality rather than retrieval stopping and is therefore transfer evidence for calibrated risk control.
- paper_id `2106.00170` [identity: VERIFIED] Adaptive Conformal Inference Under Distribution Shift (2021, NeurIPS 2021)
    Adaptive conformal inference constructs online prediction sets when the data-generating distribution changes over time in an unknown way. It continuously adapts the conformal control parameter and provably achieves the desired long-run coverage frequency without requiring an exchangeable stream. This is foundational transfer work for calibrating a stopping or abstention controller on a non-stationary evidence stream.
- paper_id `2402.03181` [identity: VERIFIED] C-RAG: Certified Generation Risks for Retrieval-Augmented Language Models (2024, ICML 2024)
    C-RAG develops conformal risk analysis for retrieval-augmented language models and certifies upper confidence bounds for bounded generation-risk functions. Its theory explicitly studies test-distribution shift and gives sufficient conditions under which RAG has lower conformal generation risk than a standalone language model. Retrieval depth itself remains fixed, so the result is most directly transferable as a risk-control layer for adaptive stopping.
- paper_id `2006.09462` [identity: VERIFIED] Selective Question Answering under Domain Shift (2020, ACL 2020)
    This paper formalizes selective QA under domain shift, where a system must answer as many questions as possible while maintaining a target accuracy on mixtures of in-domain and unseen out-of-domain inputs. It shows that raw model probabilities are poorly calibrated under shift and trains a separate calibrator using source and known out-of-domain behavior to decide when to abstain. The setting is directly transferable to risk-aware RAG stopping and abstention.
- paper_id `2603.19281` [identity: VERIFIED] URAG: A Benchmark for Uncertainty Quantification in Retrieval-Augmented Large Language Models (2026)
    URAG benchmarks uncertainty quantification for retrieval-augmented language models across domains and multiple RAG methods, including conformal-prediction-based approaches. Its experiments vary retrieval depth, retrieval noise, and other contextual factors that affect confidence reliability. The benchmark is relevant for evaluating whether a stopping confidence signal remains calibrated as retrieval conditions change.
- paper_id `manual-db92af7586` [identity: UNCHECKED] High Probability Risk Control Under Covariate Shift (2025, Fourteenth Symposium on Conformal and Probabilistic Prediction with Applications)
    This paper extends high-probability Learn-Then-Test risk control to covariate shift by importance-weighting calibration losses. It targets finite-sample control of user-specified risks when calibration and deployment distributions differ and validates the method on fraud detection and image classification. The method is a transferable candidate for calibrating RAG stopping policies when the query distribution shifts.
- paper_id `2604.19899` [identity: VERIFIED] A Reproducibility Study of Metacognitive Retrieval-Augmented Generation (2026, SIGIR 2026)
    This study reproduces MetaRAG, a multi-retrieval framework intended to recognize when enough information has been gathered, and compares it with SIM-RAG's lightweight sufficiency critic. It confirms relative improvements but reports lower absolute results than the original MetaRAG study and examines sensitivity to reranking and sufficiency judgments. The work is useful evidence on the reproducibility and robustness of semantic stopping mechanisms.
- paper_id `2605.05245` [identity: VERIFIED] AdaGATE: Adaptive Gap-Aware Token-Efficient Evidence Assembly for Multi-Hop Retrieval-Augmented Generation (2026)
    AdaGATE is a training-free evidence controller that treats multi-hop evidence acquisition as a token-constrained repair problem. It tracks entity-centric evidence gaps, generates targeted micro-queries, and scores candidates using gap coverage, corroboration, novelty, redundancy, and direct relevance while replacing low-utility evidence under a fixed token budget. Experiments on HotpotQA under clean, redundant, and noisy retrieval conditions evaluate evidence quality as well as token efficiency.
- paper_id `2208.08401` [identity: VERIFIED] Conformal Inference for Online Prediction with Arbitrary Distribution Shifts (2024, Journal of Machine Learning Research)
    This work extends adaptive conformal inference to online settings with arbitrary distribution changes and develops a procedure with small regret over local time intervals. The method adapts to both the size and type of shift by tuning the update step size online, reducing dependence on knowledge of the data-generating dynamics. It provides a relevant theoretical foundation for non-stationary calibrated stopping.
- paper_id `2608.08512` [identity: VERIFIED] Time Present and Time Past: Benchmarking Large Language Models on Temporally Evolving Document Understanding (2026)
    The paper introduces TIDE for question answering over documents that are amended, replaced, and sometimes reverted. Its central task is version resolution: identifying which official version was valid on the queried date, including rejecting a supplied version that did not govern that date. The benchmark contains explicit historical validity periods and evaluates parametric, gold-context, and retrieval-access settings with a hard temporal correctness gate.
- paper_id `doi-10-1016-0306-4379-96-00017-8` [identity: UNCHECKED] Semantics of time-varying information (1996, Information Systems)
    The paper systematically develops semantics for temporal database facts, including valid-time and transaction-time dimensions and their combination in bitemporal relations. It also discusses multiple transaction times created when facts are replicated or transferred between databases. These distinctions are directly transferable to version-aware evidence provenance where factual validity and system-observation history must not be conflated.
- paper_id `doi-10-1145-2619088` [identity: UNCHECKED] Survey of Temporal Information Retrieval and Related Applications (2014, ACM Computing Surveys)
    This survey organizes the temporal information-retrieval literature and reviews methods that exploit temporal information in documents and queries. It distinguishes multiple temporal search needs, summarizes temporal query analysis and retrieval models, and discusses open problems in end-to-end temporal retrieval. The survey provides transfer context for separating ordinary recency ranking from richer temporal evidence requirements.

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
