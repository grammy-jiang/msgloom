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

# Task: cross-paper synthesis

Research topic: **Unified iterative RAG stopping and provenance control under distribution shift: search specifically for controllers that combine structured evidence sufficiency with temporal/version-aware provenance and calibrated or conformal risk-controlled stopping, including any systems that additionally integrate permission-aware access or bounded retrieval budgets.**

Below are 61 per-paper analyses (reduced to questions and top findings to fit the size cap). Synthesize them into a
cross-paper synthesis: recurring themes, contradictions (name the papers on
both sides), open gaps classified as ENGINEERING (fillable from docs, code,
or benchmarks), ACADEMIC (needs more papers) or OUT_OF_SCOPE, actionable
insights, an overall confidence note, and the synthesis' own limitations.
Every finding must cite at least one paper_id from this list: `1904.06019`, `2006.09462`, `2010.11915`, `2105.04166`, `2112.08558`, `2208.02814`, `2208.08401`, `2210.03350`, `2212.10509`, `2305.06983`, `2307.04642`, `2310.11511`, `2402.03181`, `2403.10081`, `2406.10490`, `2406.19215`, `2411.06037`, `2412.15540`, `2505.02811`, `2506.05167`, `2506.20978`, `2508.01084`, `2510.08109`, `2510.13590`, `2510.14337`, `2510.22344`, `2601.19827`, `2603.28444`, `2604.01413`, `2604.19899`, `2604.23783`, `2604.25676`, `2605.03534`, `2605.05245`, `2606.05658`, `2606.13814`, `2606.15964`, `2606.29054`, `2606.29090`, `2606.29959`, `2607.06507`, `2607.24010`, `2607.27726`, `2608.02195`, `2608.08512`, `2608.13237`, `2609.08364`, `2609.11572`, `2609.16301`, `doi-10-1016-0306-4379-96-00017-8`, `doi-10-1038-s41598-026-71936-x`, `doi-10-1109-access-2025-3628960`, `doi-10-1145-1247715-1247720`, `doi-10-1145-1571941-1572085`, `doi-10-1145-181550-181560`, `doi-10-1145-3786625`, `doi-10-1609-aaai-v39i14-33670`, `doi-10-18653-v1-2026-acl-long-1562`, `doi-10-18653-v1-2026-findings-acl-2090`, `doi-10-32604-cmc-2026-086343`, `manual-2bb76a9136`.
Do not cite any other paper.

The independent reviewer that reads this rejects one thing above all others,
and it has rejected the first round of every topic so far for it: **a
project judgement written as a literature finding**. Separate them here and
the review passes on the first attempt.

- A `finding` states what the cited papers demonstrate, and nothing further.
  If the papers show a method works on one corpus, say that; do not say the
  method is required, necessary, or suitable for this project.
- **A finding containing "should", "must" or "needs to" is a recommendation
  wearing a finding's clothes.** Search your own draft for those words before
  replying and move each one to `actionable_insights`, marked as a
  synthesis-derived recommendation. The single exception is reporting what a
  cited paper itself recommends, and then you name whose recommendation it
  is. "Systems should maintain explicit visibility for stale items" is the
  sentence that has cost this pipeline the most rounds.
- An `actionable_insight` is where a recommendation belongs. Mark every one
  that goes beyond the experiments as a synthesis-derived recommendation,
  in those words, and do not attach paper citations to the part that is a
  project decision. Citing a paper for a decision it never tested is the
  single most common rejection.
- Deciding which part of the product owns a problem, or which later topic a
  case is routed to, is always a project decision. It carries no citation.
- Work handed to this topic by an earlier one is a starting condition, never
  evidence. An earlier topic's open gap does not support a finding or a gap
  of yours: only the analyses listed above can. If an inherited gap matters,
  name it in `limitations` as inherited context, not as something this
  corpus shows. The reviewer calls this "project-external evidence" and it
  is the one thing the handoff section is most likely to tempt you into.
- `confidence_summary` describes the evidence, not the design. Write
  "well-supported design principles", never "necessary design requirements".
- Papers that each validate one aspect do not jointly validate a combined
  scheme. Say what each one covers and that the combination is untested.
- Two records of the same study are one piece of evidence. The corpus can
  carry the same paper twice under different ids -- a bare `manual-` row and
  the same work with its DOI -- so check titles before you call two analyses
  independent corroboration, and count distinct papers, not analyses.
- A gap you believe is real stays in `gaps` with its classification. It does
  not become a finding by being restated confidently.

Before you reply, check your own draft against the five things the reviewer
rejects for. These are its triggers, not a paraphrase, and any one of them
sends the work back:

1. A finding cites no analysis, or cites a paper outside the list above.
2. A finding states more than its evidence supports.
3. A contradiction between analyses is dropped or silently averaged away.
   Name it in `contradictions` even when it is inconvenient. The reviewer
   rejects the opposite mistake just as readily, and it is the commoner one:
   **two papers are in contradiction only if they disagree about the same
   question under comparable conditions.** Different tasks, datasets,
   settings or definitions are a scope qualification, not a disagreement,
   and calling one a contradiction costs coherence exactly as much as
   dropping a real one costs faithfulness. Before you list a contradiction,
   name the single question both papers answer; if you cannot, it belongs in
   the findings as a qualification instead.
4. A gap the corpus cannot close is presented as closed. If no admitted paper
   answers it, it is open.
5. Transfer evidence is presented as direct evidence. Say which domain each
   result comes from, and never let an adjacent-domain or synthetic result
   carry a production claim.

Go through your findings one at a time against this list. Fixing a sentence
now costs you nothing; a rejection costs a full synthesis and review cycle.


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

Per-paper analyses:
[
 {
  "paper_id": "1904.06019",
  "title": "Conformal Prediction Under Covariate Shift",
  "research_question": "Can conformal prediction retain distribution-free marginal coverage when training and test covariate distributions differ while the conditional outcome distribution given covariates remains unchanged?",
  "key_findings": [
   "When the covariate likelihood ratio is known, weighted conformal prediction restores finite-sample marginal coverage under covariate shift while ordinary conformal prediction need not retain its nominal coverage.",
   "The method is derived from a more general weighted-exchangeability framework that includes ordinary exchangeability and certain independent non-identically distributed settings as special cases.",
   "In the Airfoil experiment at 90% nominal coverage, ordinary split conformal averaged 90.2% without shift but only 82.2% on the shifted test distribution.",
   "Using the oracle covariate-shift weights raised average coverage on the shifted Airfoil test distribution to 90.8%.",
   "Importance weighting increases coverage variability because highly uneven weights reduce the effective calibration sample size."
  ]
 },
 {
  "paper_id": "2006.09462",
  "title": "Selective Question Answering under Domain Shift",
  "research_question": "Can a question-answering system learn an abstention policy that maintains high accuracy on answered questions when deployment data mixes in-domain examples with previously unseen out-of-domain examples?",
  "key_findings": [
   "A calibrator trained on both source and known-OOD examples reached 56.1% coverage while maintaining 80% accuracy, compared with 48.2% coverage for MaxProb using the same source-trained QA model.",
   "Training the calibrator with known-OOD data improved coverage at 80% accuracy by 2.4 percentage points relative to training the calibrator only on source-domain examples.",
   "The base QA model is systematically overconfident on OOD examples relative to in-domain examples, which makes raw softmax confidence a weak abstention signal under mixed-domain deployment.",
   "OOD inputs should not simply be rejected wholesale because the source-trained QA model still obtains roughly 40% to 50% exact-match accuracy on most evaluated OOD datasets.",
   "Test-time dropout can improve selective prediction further, but the experiment uses 30 stochastic forward passes and therefore introduces approximately 30-fold inference overhead."
  ]
 },
 {
  "paper_id": "2010.11915",
  "title": "Challenges in Information-Seeking QA: Unanswerable Questions and Paragraph Retrieval",
  "research_question": "Why do naturally occurring information-seeking questions remain unanswerable for strong QA systems, and how much of the difficulty comes from paragraph selection, answerability prediction, missing evidence, invalid questions, or restrictive task design?",
  "key_findings": [
   "Oracle experiments show that paragraph selection and answerability prediction account for substantial remaining error; once models receive gold evidence and answer-type information, their answer extraction becomes much stronger.",
   "Answerability prediction remains difficult on naturally occurring information-seeking questions: for binary classification, the reported QA model reaches 82.5% on NQ and 79.4% on TyDi QA, compared with aggregate human agreement of 85.6% and 94.0%.",
   "Question-only models exceed 70% binary answerability accuracy on NQ and TyDi QA, showing that surface-form artifacts provide substantial cues even though the questions were collected independently of evidence documents.",
   "The causes of unanswerability vary strongly by dataset and language: 38% of the analyzed NQ unanswerable subset consists of invalid or ill-defined questions, whereas retrieval misses account for roughly 50-74% of annotated TyDi examples across the five studied languages.",
   "Many questions labeled unanswerable relative to their supplied document become answerable when annotators search another Wikipedia page or a non-Wikipedia source, demonstrating that evidence-source coverage is a major determinant of apparent answerability."
  ]
 },
 {
  "paper_id": "2105.04166",
  "title": "Few-Shot Conversational Dense Retrieval",
  "research_question": "Can a conversational dense retriever learn robust contextual query embeddings from very little conversational relevance supervision by distilling an ad-hoc dense retriever, and thereby outperform query-rewriting retrieval pipelines?",
  "key_findings": [
   "ConvDR substantially improves first-stage retrieval over sparse retrieval and automatic query-rewriting baselines on the CAsT conversational-search benchmarks, while approaching retrieval based on manually rewritten queries in the strongest reported setting.",
   "Under the highly limited CAsT supervision regime, knowledge distillation from the ad-hoc retriever is the training signal that successfully adapts ConvDR, whereas sparse conversational ranking supervision alone can perform worse than the zero-shot alternatives.",
   "With substantially more supervision on OR-QuAC, ranking supervision becomes effective and combining ranking with knowledge distillation gives the strongest ConvDR training result reported there.",
   "Turn-by-turn and context-intrusion analyses indicate that ConvDR retains useful earlier conversational information and is more sensitive to removal of relevant history than to removal of relatively unimportant history.",
   "Direct contextual query encoding avoids the separate query-rewriting stage and reduces measured query-processing latency relative to the evaluated rewrite-then-retrieve pipelines."
  ]
 },
 {
  "paper_id": "2112.08558",
  "title": "CONQRR: Conversational Query Rewriting for Retrieval with Reinforcement Learning",
  "research_question": "Can conversational query rewriting trained directly against retrieval rewards produce better standalone search queries for fixed off-the-shelf retrievers than supervised rewriting trained only to imitate human rewrites?",
  "key_findings": [
   "On the updated QReCC BM25 evaluation, the pure-RL CONQRR model achieved MRR 0.383 and Recall@10 60.1 versus 0.328 and 52.5 for the supervised T5QR baseline; the mixed objective also outperformed T5QR.",
   "The mixed CONQRR model outperformed supervised T5QR across the reported combinations of two fixed retrievers and the principal in-domain and out-of-domain evaluations, although individual metric differences on TREC can be small.",
   "With the dual-encoder retriever on the aggregate QReCC evaluation, pure-RL CONQRR reached MRR 0.418, Recall@10 0.651, and Recall@100 0.847, compared with 0.361, 0.562, and 0.759 for supervised T5QR.",
   "Directly submitting the full dialogue context can work very well when a conversation remains centered on one topic but degrades sharply after topic shifts, while learned query rewriting is substantially more robust to those shifts.",
   "In an error analysis of 50 cases where mixed CONQRR underperformed the human rewrite with the dual encoder, the generated queries were fluent, but 56% omitted useful context and 34% introduced extra information associated with misinterpretation."
  ]
 },
 {
  "paper_id": "2208.02814",
  "title": "Conformal Risk Control",
  "research_question": "Can conformal prediction be generalized from binary miscoverage control to finite-sample control of the expected value of arbitrary bounded monotone loss functions?",
  "key_findings": [
   "For bounded losses that are non-increasing with a conservativeness parameter, the proposed calibration rule guarantees expected test loss at or below the user-specified risk level under the stated exchangeability assumptions.",
   "The expected-risk guarantee generalizes ordinary conformal miscoverage control rather than merely reproducing prediction-set coverage.",
   "Under additional i.i.d. continuity conditions, the method is shown to be tight up to an order-1/n term rather than becoming arbitrarily conservative.",
   "Empirical experiments on segmentation, multilabel classification, hierarchical classification, and open-domain QA produced mean risks close to but below their specified targets across repeated random splits.",
   "On Natural Questions, the F1-loss experiment with a target risk of 0.3 reported mean risk 0.2996 with standard deviation 0.0150 over 1,000 trials."
  ]
 },
 {
  "paper_id": "2208.08401",
  "title": "Conformal Inference for Online Prediction with Arbitrary Distribution Shifts",
  "research_question": "Can online conformal prediction maintain locally accurate coverage under changing distribution shifts without knowing the rate or magnitude of distribution change in advance?",
  "key_findings": [
   "DtACI adaptively tunes ACI's step size rather than requiring prior knowledge of how rapidly the data-generating distribution changes.",
   "Theorem 3.1 provides a local dynamic-regret guarantee whose bound adapts to variation in the time-varying optimal miscoverage parameter over the evaluated interval.",
   "The local-regret result can be translated into a local-coverage bound when the conformity-score distribution has a suitable density lower bound and the coverage map is sufficiently smooth.",
   "A modified DtACI with eta and sigma tending to zero obtains exact long-run average coverage at the target level.",
   "In simulations, DtACI suffers a small disadvantage under stationarity but adapts better than the comparison methods when the magnitude of distribution shifts changes sharply."
  ]
 },
 {
  "paper_id": "2210.03350",
  "title": "Measuring and Narrowing the Compositionality Gap in Language Models",
  "research_question": "How often do language models fail to compose facts they can answer individually, and can explicit decomposition with self-generated follow-up questions and external search reduce this compositionality gap?",
  "key_findings": [
   "GPT-3-family models frequently fail to answer a compositional question even when they correctly answer its component subquestions, with the compositionality gap remaining roughly constant rather than shrinking substantially with GPT-3 scale.",
   "Higher model confidence on the answers to constituent subquestions is associated with a substantially higher probability of correctly answering the corresponding compositional question.",
   "Elicitive prompting improves compositional question answering, and self-ask generally outperforms direct prompting and chain-of-thought in the reported experiments.",
   "Self-ask provides an explicit next-retrieval mechanism: the model generates a follow-up question, receives its answer, can generate another follow-up, and terminates the loop when it decides to issue the final answer.",
   "Adding internet search to self-ask improved Davinci-002 accuracy from 57.6% to 60.0% on Bamboogle, from 30.0% to 40.1% on 2WikiMultiHopQA, and from 13.8% to 15.2% on Musique in the reported evaluation."
  ]
 },
 {
  "paper_id": "2212.10509",
  "title": "Interleaving Retrieval with Chain-of-Thought Reasoning for Knowledge-Intensive Multi-Step Questions",
  "research_question": "Does repeatedly alternating chain-of-thought reasoning with retrieval, so that each reasoning step can determine what evidence to retrieve next, improve evidence recall and answer quality on knowledge-intensive multi-step questions?",
  "key_findings": [
   "With GPT-3 as the reasoning model, IRCoT increased fixed-budget retrieval recall over one-step retrieval by 11.3, 22.6, 12.5, and 21.2 points on HotpotQA, 2WikiMultihopQA, MuSiQue, and IIRC respectively.",
   "Interleaved retrieval also improved downstream QA F1 on most evaluated settings, including gains of 7.1, 13.2, and 7.1 points with GPT-3 on the first three datasets, although the large IIRC retrieval gain did not yield a corresponding QA improvement.",
   "IRCoT retained retrieval and QA advantages under cross-dataset demonstrations in the reported out-of-domain experiments, except that IIRC was excluded from this comparison because of its different structure.",
   "Manual factuality analysis found fewer factual errors in IRCoT reasoning than in the one-retrieval baseline, including reported reductions of 50% on HotpotQA and 40% on 2WikiMultihopQA.",
   "Retrieval improvements appeared across all tested language-model sizes, including small Flan-T5 models, whereas downstream QA gains were less reliable at the smallest scale."
  ]
 },
 {
  "paper_id": "2305.06983",
  "title": "Active Retrieval Augmented Generation",
  "research_question": "Can long-form generation be improved by actively deciding when external retrieval is needed and formulating retrieval queries from anticipated future text rather than relying on one-shot retrieval or fixed retrieval intervals?",
  "key_findings": [
   "FLARE's direct active-retrieval variant reaches 51.0 EM and 59.7 F1 on 2WikiMultiHopQA, outperforming the reported no-retrieval, single-retrieval, previous-context, and question-decomposition baselines.",
   "Using a predicted next sentence as the retrieval query outperforms retrieving from the previous sentence in the reported comparison, including 48.8 versus 39.0 EM on 2WikiMultiHopQA and 45.9 versus 42.5 EM on ASQA with hints.",
   "Performance does not monotonically improve as retrieval becomes more frequent: it plateaus on 2WikiMultiHopQA and degrades on StrategyQA when retrieval is triggered too often, indicating that irrelevant retrieval can add harmful noise.",
   "FLARE operationalizes the 'when to fetch' decision with a token-probability threshold and the 'what to fetch' decision with anticipated future content, masking or reformulating uncertain spans when constructing queries.",
   "The method does not show significant improvements on all tested generation tasks, with the paper specifically discussing weak results on Wizard of Wikipedia and ELI5."
  ]
 },
 {
  "paper_id": "2307.04642",
  "title": "TRAQ: Trustworthy Retrieval Augmented Question Answering via Conformal Prediction",
  "research_question": "Can conformal prediction provide an end-to-end statistical correctness guarantee for open-domain RAG while keeping the resulting semantic answer sets reasonably small?",
  "key_findings": [
   "TRAQ provides an end-to-end coverage guarantee that the aggregated answer set contains a semantically correct answer with probability at least the requested coverage level, subject to its conformal and model-capability assumptions.",
   "Empirical retriever, generator, and end-to-end coverage generally matched or exceeded the requested conformal coverage levels, while PAC variants were usually more conservative.",
   "Bayesian optimization reduced average prediction-set size by 16.2% relative to the corresponding non-optimized Bonferroni ablations while preserving the target coverage.",
   "The semantic-level conformal construction can operate with black-box generators because its uncertainty score is based on frequencies of sampled semantic clusters rather than token probabilities.",
   "The guarantees assume i.i.d. or approximately exchangeable calibration and test data and therefore do not provide explicit protection against test-time distribution shift."
  ]
 },
 {
  "paper_id": "2310.11511",
  "title": "Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection",
  "research_question": "Can a language model learn to decide when retrieval is needed, assess retrieved evidence and its own generations, and thereby improve factuality, attribution, and task performance without indiscriminately retrieving documents?",
  "key_findings": [
   "Self-RAG substantially outperforms comparable non-proprietary language-model and conventional RAG baselines across the evaluated task suite, including strong gains on factual and knowledge-intensive tasks.",
   "Adaptive retrieval is preferable to always using the top retrieved passage: the retrieve-top-1 ablation produces substantial degradation on PopQA and ASQA relative to the full system.",
   "Training with both retrieval-aware data and critique/reflection supervision contributes materially to performance, because removing either the retriever-oriented training or critic-oriented training reduces results on the ablation tasks.",
   "Inference-time reflection weights expose a controllable trade-off between evidence support and other generation properties: increasing the support weight improves citation precision but reduces MAUVE in the ASQA analysis.",
   "The retrieval threshold provides an explicit efficiency-versus-accuracy control because increasing the threshold sharply changes retrieval frequency, with the performance cost of reduced retrieval depending on the task."
  ]
 },
 {
  "paper_id": "2402.03181",
  "title": "C-RAG: Certified Generation Risks for Retrieval-Augmented Language Models",
  "research_question": "Can a conformal risk controller certify generation risk for configurable RAG systems, identify configurations satisfying a desired risk level, and maintain valid risk bounds under bounded test-time distribution shift?",
  "key_findings": [
   "For a fixed RAG configuration, C-RAG computes a high-confidence upper bound on a bounded generation-risk function from calibration data.",
   "Given a desired risk level, C-RAG can certify a set of configurations whose generation risks are jointly controlled below that level using family-wise error-rate control.",
   "The configuration explicitly includes the number of retrieved examples, so retrieval quantity is a controllable and certifiable resource dimension, although it is selected as a configuration rather than by a per-query evidence-sufficiency stopping loop.",
   "The paper derives a conformal generation-risk bound for general bounded risk functions when the shifted test distribution lies within a specified Hellinger-distance radius of the calibration distribution.",
   "In the simulated shift experiments, the certified risk bounds remained above empirical risk and rose approximately linearly with Hellinger distance, remaining non-trivial through a reported distance of 0.2."
  ]
 },
 {
  "paper_id": "2403.10081",
  "title": "DRAGIN: Dynamic Retrieval Augmented Generation based on the Information Needs of Large Language Models",
  "research_question": "Can dynamic RAG improve knowledge-intensive generation by deciding both when to retrieve and what to retrieve from the LLM's real-time information needs rather than from fixed retrieval schedules or only the most recent generated text?",
  "key_findings": [
   "DRAGIN achieved the strongest overall performance across most evaluated LLM and dataset combinations, with especially pronounced gains on multi-hop QA tasks.",
   "Fixed-interval and fixed-sentence dynamic retrieval did not consistently outperform single-round RAG, supporting the claim that retrieving at an inappropriate generation point can be unhelpful.",
   "When query formulation was held fixed, the RIND retrieval-timing strategy outperformed the timing strategies of FLARE, fixed-length RAG, and fixed-sentence RAG on the IIRC experiments.",
   "When retrieval timing was held to RIND, QFS outperformed query formulations based on the last sentence, local token windows, FLARE's filtered sentence, and the complete generation context on HotpotQA.",
   "DRAGIN required fewer retrieval calls than fixed-length and fixed-sentence RAG in the reported efficiency comparison, although FLARE generally made the fewest retrieval calls."
  ]
 },
 {
  "paper_id": "2406.10490",
  "title": "Active, anytime-valid risk controlling prediction sets",
  "research_question": "Can risk-controlling prediction sets be extended to sequential and actively labeled data so that risk control remains valid at every stopping time while labels are acquired efficiently under a budget?",
  "key_findings": [
   "The paper establishes an anytime-valid risk-control guarantee that holds simultaneously over all time steps, allowing the procedure to be stopped adaptively without invalidating the stated risk guarantee under its assumptions.",
   "Adaptive label sampling with inverse-propensity correction preserves the validity of the e-process construction while allowing the expected labeling rate to be constrained by a budget.",
   "The theoretically optimal auxiliary predictor is the conditional expected risk given the features, and the optimal labeling probability is related to the conditional residual variability under the budget constraint.",
   "Prediction error and deviation of the learned sampling policy from the optimal policy reduce expected wealth growth and therefore statistical efficiency, with this loss characterized by the paper's regret analysis.",
   "In both the numerical simulations and ImageNet experiments, the pretrained and learned active policies reach better prediction-set utility for a given number of queried labels than the label-all and oblivious strategies while the observed safety-violation rate remains below the configured level."
  ]
 },
 {
  "paper_id": "2406.19215",
  "title": "SeaKR: Self-aware Knowledge Retrieval for Adaptive Retrieval Augmented Generation",
  "research_question": "Can uncertainty derived from an LLM's internal states be used to decide when to retrieve external knowledge, which retrieved evidence to use, and how to reason, thereby improving adaptive retrieval-augmented generation without task-specific fine-tuning?",
  "key_findings": [
   "SeaKR achieves the highest reported F1 among the compared systems on all three complex-QA evaluations, reaching 36.0 on 2WikiMultiHopQA, 39.7 on HotpotQA, and 23.5 on answerable IIRC.",
   "Compared with the strongest reported baseline for each complex-QA benchmark, the corresponding SeaKR F1 improvements are 6.0, 5.5, and 0.6 percentage points.",
   "Ablating adaptive retrieval and retrieving at every generation step reduces performance, supporting the paper's claim that unnecessary retrieval can introduce misleading information rather than uniformly helping.",
   "Removing uncertainty-based reranking causes a substantial degradation, and in the reported ablation it has a larger effect than removing the adaptive retrieval trigger.",
   "The retrieval loop is explicitly bounded: iterative reasoning stops when the model emits its final-answer preface or when the configured maximum number of retrievals is reached."
  ]
 },
 {
  "paper_id": "2411.06037",
  "title": "Sufficient Context: A New Lens on Retrieval Augmented Generation Systems",
  "research_question": "Can retrieval-augmented generation failures be decomposed according to whether the retrieved context is sufficient to answer the question, and can this sufficiency signal improve abstention decisions beyond model confidence alone?",
  "key_findings": [
   "A one-shot Gemini 1.5 Pro sufficiency autorater achieves 0.930 accuracy and 0.935 F1 on the paper's 115-instance human-labeled sufficiency set.",
   "For the evaluated retrieval setup, increasing retained context from 6,000 to 10,000 tokens produced little or no additional sufficiency benefit, motivating the authors' use of a 6,000-token context cutoff.",
   "Context sufficiency separates two distinct failure sources: retrieval can fail to provide enough information, while an LLM can still fail even when the retrieved context contains enough information.",
   "Large models frequently answer rather than abstain when the provided context is insufficient, while models can also answer some insufficient-context cases correctly using parametric knowledge, guessing, or partial evidence.",
   "Combining context sufficiency with answer confidence improves selective generation over confidence alone, with reported accuracy gains exceeding 10 percentage points for Gemma 27B in part of the HotpotQA coverage range and exceeding 5 points for Gemini 1.5 Pro around 70 percent coverage."
  ]
 },
 {
  "paper_id": "2412.15540",
  "title": "MRAG: A Modular Retrieval Framework for Time-Sensitive Question Answering",
  "research_question": "Can explicitly separating semantic relevance from temporal reasoning improve retrieval and downstream answering for questions whose evidence must satisfy a temporal constraint?",
  "key_findings": [
   "Temporal perturbations expose substantial brittleness in conventional retrievers; for example, the Gemma baseline's top-1 answer recall on perturbed SituatedQA falls from 85.8% to 54.7%, while evidence recall falls from 45.0% to 20.3%.",
   "Controlled experiments indicate that conventional retrieval methods tend to favor exact date matching rather than correctly modeling relations such as before, after, and as-of.",
   "MRAG outperforms retrieve-then-rerank baselines on both TempRAGEval subsets; against Contriever plus Gemma it improves top-5 evidence recall by 7.7 points on TimeQA and 13.9 points on SituatedQA.",
   "Improved temporal retrieval propagates to end-to-end QA: for Llama-3.1-8B, MRAG-Concat improves TimeQA EM/F1 from 44.0/52.8 with standard RAG-Concat to 49.2/59.2, and Self-MRAG reaches 54.2/65.6.",
   "The modular filtering and ranking stages offer an adjustable efficiency-accuracy trade-off, but the complete MRAG pipeline is reported to require roughly twice the computational overhead of standard RAG."
  ]
 },
 {
  "paper_id": "2505.02811",
  "title": "Knowing You Don't Know: Learning When to Continue Search in Multi-round RAG through Self-Practicing",
  "research_question": "Can a separately trained information-sufficiency critic learn when a multi-round RAG system has enough evidence to answer and when it should continue searching, without requiring manually annotated stopping decisions?",
  "key_findings": [
   "SIM-RAG learns an explicit binary information-sufficiency decision that determines whether to return the current answer or perform another retrieval round.",
   "Self-practice generates Critic supervision automatically from multi-round trajectories by labeling rounds according to whether the current generated answer matches the known answer.",
   "The external Critic is separated from the Reasoner to reduce reliance on the same model's self-critique, and its Accept/Reject decision controls subsequent retrieval behavior.",
   "The reported GPT-4 configuration with the full Critic achieved F1 scores of 82.7 on TriviaQA, 52.2 on HotpotQA, and 54.6 on 2WikiMultiHopQA.",
   "Increasing the maximum self-practice/retrieval turn count improved HotpotQA results in the reported turn-count study, while the paper also observes that false rejection can cause harmful over-retrieval."
  ]
 },
 {
  "paper_id": "2506.05167",
  "title": "ECoRAG: Evidentiality-guided Compression for Long Context RAG",
  "research_question": "Can a RAG system compress long retrieved contexts by explicitly estimating evidence sufficiency and adaptively stop adding evidence once enough information is present to support a correct answer?",
  "key_findings": [
   "ECoRAG implements an explicit iterative evidence-sufficiency stopping rule: evidence is added in ranked order until the evaluator judges the accumulated context evidential.",
   "The evidence-accumulation loop has a hard token limit, preventing indefinite iteration when the initially retrieved corpus contains no sufficient evidence.",
   "The loop operates over an already retrieved and ranked pool rather than repeatedly issuing new document-retrieval requests, so it is bounded context accumulation rather than open-ended adaptive retrieval.",
   "ECoRAG achieved EM scores of 36.48 on NQ, 65.34 on TQA, and 30.17 on WQ while using hundreds rather than roughly fourteen thousand input tokens used by uncompressed 100-document RAG.",
   "The evidentiality evaluator exceeded the CompAct evaluator by 13.96 percentage points in F1 and performed within 0.08 percentage points of the much larger Flan-UL2 reader on the reported evidentiality test."
  ]
 },
 {
  "paper_id": "2506.20978",
  "title": "Response Quality Assessment for Retrieval-Augmented Generation via Conditional Conformal Factuality",
  "research_question": "Can conformal prediction filter unreliable sub-claims from RAG answers while retaining substantially more useful content and providing marginal or group-conditional factuality guarantees?",
  "key_findings": [
   "Conformal-RAG provides a probabilistic factuality guarantee for the retained sub-claims under the conformal assumptions and the assumption that calibration annotations are correct.",
   "The conditional variant uses Mondrian conformal prediction to provide separately calibrated thresholds for pre-specified query groups such as dataset or medical sub-domain.",
   "The authors report that Conformal-RAG retains up to 60% more high-quality sub-claims than direct conformal factuality applied to the LLM while targeting the same reliability level.",
   "At an 85% target factuality level on FActScore, Conformal-RAG removed 8.9% of claims while the Conformal-LLM baseline removed 86.8%.",
   "Empirical factuality was generally at or above target for the marginal experiments, and conditional Conformal-RAG approximately achieved target factuality across the tested groups with less fluctuation than the Conformal-LLM baseline."
  ]
 },
 {
  "paper_id": "2508.01084",
  "title": "Provably Secure Retrieval-Augmented Generation",
  "research_question": "Can a RAG architecture protect private textual content and embeddings against leakage and poisoning while providing formal confidentiality and integrity guarantees and retaining practical retrieval functionality?",
  "key_findings": [
   "The proposed architecture explicitly protects both stored text and stored embeddings rather than leaving vector representations exposed while encrypting only document content.",
   "Under the stated computational assumptions, the chained design provides formal reduction-based arguments for confidentiality, forward security, chain integrity, and privacy of the Authdoor authorization record.",
   "The system enforces user-level isolation by associating private encrypted data with authenticated users and decrypting it only after the validator establishes authorized access.",
   "Across the reported four-dataset evaluation, all tested leakage attacks have a reported zero attack-success rate and zero leaked-private-knowledge measurements under SAG.",
   "Across the evaluated poisoning attacks and datasets, the paper reports zero PASR, recall, and F1 values because injected adversarial content is prevented from entering the effective retrieval path."
  ]
 },
 {
  "paper_id": "2510.08109",
  "title": "VersionRAG: Version-Aware Retrieval-Augmented Generation for Evolving Documents",
  "research_question": "Can explicitly representing document versions, version sequences, and changes in a retrieval graph prevent RAG systems from returning semantically relevant but temporally invalid information from evolving documentation?",
  "key_findings": [
   "With DeepSeek-R1 70B, VersionRAG achieves 90% overall VersionQA accuracy compared with 58% for naive RAG and 64% for GraphRAG.",
   "The largest gains occur on version-sensitive tasks: VersionRAG reaches 100% on version listing and 70% on change retrieval with DeepSeek-R1 70B, versus 35% and 25% for naive RAG and 80% and 30% for GraphRAG.",
   "VersionRAG reaches 60% accuracy on implicit change detection while the reported baselines achieve only 0-10%, showing value from explicitly modeling transitions between document states.",
   "VersionRAG's structured indexing uses 186K tokens and 25 minutes with DeepSeek-R1 70B, compared with GraphRAG's 2.97M tokens and about 5.2 hours, corresponding to reported reductions of 97% in tokens and 92% in indexing time.",
   "Performance depends strongly on query-routing capability: intent-classification accuracy is reported as 92% with DeepSeek-R1 70B versus 76% with Llama 3 8B."
  ]
 },
 {
  "paper_id": "2510.13590",
  "title": "RAG Meets Temporal Graphs: Time-Sensitive Modeling and Retrieval for Evolving Knowledge",
  "research_question": "Can an explicitly temporal graph representation and incremental indexing strategy improve time-sensitive retrieval and question answering while efficiently incorporating newly arriving knowledge?",
  "key_findings": [
   "On base-corpus ECT-QA specific questions, Temporal GraphRAG obtains a Correct score of 0.599, compared with approximately 0.380 to 0.410 for the reported non-oracle RAG baselines.",
   "After adding the 2024 corpus slice, Temporal GraphRAG retains a Correct score of 0.587 on base queries and reaches 0.617 on new queries, indicating that incremental updates can add recent knowledge without a large loss on earlier questions.",
   "The incremental update consumes about 1.6 million prompt tokens and 2.0 million completion tokens for Temporal GraphRAG versus about 30.0 million prompt and 7.8 million completion tokens for the reported GraphRAG update.",
   "Pairwise evaluation of abstract questions reports high temporal-coverage win rates for Temporal GraphRAG against GraphRAG, HippoRAG2, and LightRAG, supporting the intended benefit of explicit temporal organization for broad time-sensitive synthesis.",
   "Ablation results show a large accuracy drop when temporal retrieval is removed, with Correct score falling from 0.599 for the full system to about 0.382 in the corresponding ablation, making temporal retrieval the strongest reported component-level contribution."
  ]
 },
 {
  "paper_id": "2510.14337",
  "title": "Stop-RAG: Value-Based Retrieval Control for Iterative RAG",
  "research_question": "Can a learned value function over iterative RAG trajectories determine whether the expected benefit of another retrieval step justifies continuing rather than stopping?",
  "key_findings": [
   "Within the authors' own iterative RAG pipeline, Stop-RAG improves EM, F1, and reported accuracy over both the unmodified fixed-iteration pipeline and LLM-prompted stopping on all three evaluated benchmarks.",
   "The abstract-level statement that Stop-RAG consistently outperforms both baselines across benchmark settings is contradicted by the CoRAG HotpotQA result, where Stop-RAG is slightly below the unmodified CoRAG baseline and does not dominate LLM-Stop.",
   "Stop-RAG is portable enough to be attached to a separately developed CoRAG pipeline, where it improves MuSiQue and 2WikiMultihopQA results despite the HotpotQA exception.",
   "The learned controller generally retains more useful retrieval evidence than prompting-based LLM stopping, although it can use slightly more retrieval steps than the prompted stopper.",
   "The full-width forward-view Q(lambda) objective performs better on the reported MuSiQue ablation than binary classification, Monte Carlo targets, and the Q(0) variant."
  ]
 },
 {
  "paper_id": "2510.22344",
  "title": "FAIR-RAG: Faithful Adaptive Iterative Refinement for Retrieval-Augmented Generation",
  "research_question": "Can iterative RAG improve faithful multi-hop answering by explicitly decomposing a query into required findings, auditing accumulated evidence for missing information, and refining retrieval until those evidence requirements are judged sufficient?",
  "key_findings": [
   "FAIR-RAG provides an explicit structured sufficiency representation: required findings are enumerated, confirmed findings are tracked, and unresolved findings become named evidence gaps.",
   "The iterative controller terminates early when the Structured Evidence Assessment judges every required finding confirmed; otherwise identified gaps are used to formulate the next retrieval query.",
   "On HotpotQA, the reported adaptive three-iteration configuration achieved F1 0.453, an 8.3-point absolute improvement over the cited Iter-RetGen iterative baseline at F1 0.370.",
   "Iteration analysis found that two to three retrieval-refinement cycles generally provided the best trade-off, while a fourth cycle could degrade answer quality and increased API calls and token consumption.",
   "Final generation is constrained to retrieved evidence and instructed to attach source-document reference tokens to claims, creating claim-to-source traceability."
  ]
 },
 {
  "paper_id": "2601.19827",
  "title": "When Iterative RAG Beats Ideal Evidence: A Diagnostic Study in Scientific Multi-hop Question Answering",
  "research_question": "When and why can an iterative retrieve-reason-retrieve controller outperform a static condition in which all oracle evidence is supplied at once, and which retrieval, synthesis, and stopping failures determine the outcome?",
  "key_findings": [
   "Across the eleven evaluated models, average accuracy increased from 37.16% with No Context to 69.14% with Gold Context and 80.89% with Iterative RAG.",
   "Every evaluated model improved from Gold Context to Iterative RAG in aggregate accuracy, although individual questions could regress when retrieval introduced noise or misleading evidence.",
   "The largest reported Gold-to-Iterative gain was 25.64 percentage points for GPT-4o, while gains were generally larger for the paper's non-reasoning model group than for reasoning models.",
   "Missing at least one required retrieval hop was a major failure mode, and accuracy was substantially worse when retrieval coverage gaps occurred.",
   "High retrieval coverage could partly compensate for low measured evidence sufficiency, whereas simultaneously low coverage and low sufficiency produced the weakest observed accuracy region."
  ]
 },
 {
  "paper_id": "2603.28444",
  "title": "Entropic Claim Resolution: Uncertainty-Driven Evidence Selection for RAG",
  "research_question": "Can a RAG system select evidence adaptively according to its expected reduction of uncertainty over competing answer hypotheses and stop once the remaining epistemic uncertainty is sufficiently small?",
  "key_findings": [
   "In the controlled three-hypothesis experiment, ECR reduced final entropy from about 1.585 bits to 0.2129 bits using five evaluated claims, whereas fixed retrieval-only selection left entropy unchanged after fifteen claims and random five-claim selection left substantially higher entropy.",
   "Across multiple random seeds in the controlled setting, ECR consistently reached the same low final entropy and five-claim collapse point, while random selection retained much larger residual uncertainty.",
   "On the 300-question HotpotQA-style evaluation, ECR used slightly fewer claims than relevance-ranked RAG and achieved comparable but slightly lower exact-match, F1, and faithfulness scores, while clearly outperforming random evidence selection.",
   "Under explicit contradiction injection, ECR exposed ambiguity rather than collapsing to an overconfident answer, with the reported contradiction conditions producing zero overconfident-error rate and full ambiguity exposure.",
   "The surrounding system records structural support and contradiction links for claims and includes explicit normalization of temporal expressions such as years, quarters, halves, LTM, and TTM, providing structured provenance signals beyond ordinary similarity retrieval."
  ]
 },
 {
  "paper_id": "2604.01413",
  "title": "Adaptive Stopping for Multi-Turn LLM Reasoning",
  "research_question": "Can conformal prediction jointly calibrate retrieval, adaptive early stopping, and final answer sets in multi-turn LLM reasoning while preserving target coverage and reducing unnecessary inference?",
  "key_findings": [
   "Across the evaluated datasets, models, and error levels, MiCP met or exceeded the intended empirical coverage at the retrieval and final-answer stages, with final prediction sets often slightly over-covering the nominal target.",
   "Adaptive stopping reduced the average number of reasoning or retrieval turns relative to the fixed three-turn no-early-stopping baseline across the reported benchmark rows.",
   "The paper's statement that MiCP consistently improves prediction-set size is contradicted by several Table 1 rows, including GPT-4o-mini on HotpotQA and HotpotQA-ReAct where the proposed objective gives larger sets than the no-early-stopping baseline.",
   "Optimizing explicitly for average turns generally produces the fewest turns and small prediction sets, illustrating a controllable trade-off between stopping aggressively and other objectives.",
   "Grid-search allocation of the turn-specific error budget improves the proposed composite objective for Qwen3.5-9B and GPT-4o-mini, while gains are smaller and less stable for Gemma-2-9B-IT."
  ]
 },
 {
  "paper_id": "2604.19899",
  "title": "A Reproducibility Study of Metacognitive Retrieval-Augmented Generation",
  "research_question": "How reproducible is MetaRAG under current models and retrieval implementations, and how do reranking and an alternative critic-based stopping framework affect its accuracy, robustness, and efficiency?",
  "key_findings": [
   "The reproduction preserves MetaRAG's relative advantage over the evaluated baselines on both multi-hop QA datasets, but absolute scores are lower than originally reported, particularly on 2WikiMultiHopQA.",
   "The LLM's sufficiency judgment and the NLI critic frequently disagree: among retrieval-required cases, the LLM judged retrieved evidence sufficient for 63.3% of HotpotQA and 33.6% of 2WikiMultiHopQA cases, while the NLI critic validated 86.7% and 72.9%, respectively.",
   "In the reproduced 2WikiMultiHopQA threshold study, answer quality peaked at a judgment threshold of 0.2 with EM 38.1 and F1 46.2, while average retrievals fell from 2.8 at threshold 0.4 to 1.2 at threshold 0.2.",
   "Reranking often improves MetaRAG but is configuration-dependent rather than uniformly beneficial; BGE and RankGPT are the strongest PointWise and ListWise configurations selected for the MetaRAG-versus-SIM-RAG comparison.",
   "SIM-RAG degrades substantially after some reranking-induced retrieval-distribution changes, especially with Llama3.3, whereas MetaRAG's prompt-based self-critique is more robust to those changes."
  ]
 },
 {
  "paper_id": "2604.23783",
  "title": "S2G-RAG: Structured Sufficiency and Gap Judging for Iterative Retrieval-Augmented QA",
  "research_question": "Can iterative retrieval-augmented QA be improved by explicitly judging whether current evidence is sufficient, representing unresolved information needs as structured gaps, using those gaps to choose the next bounded retrieval, and stopping once adequate evidence has been accumulated?",
  "key_findings": [
   "The controller makes retrieval explicitly evidence-gap-driven: insufficiency produces typed gap items containing fields such as target, slot, and description, and those items are converted into the next retrieval query.",
   "The retrieval process is bounded by a maximum number of turns and a fixed top-k per turn; the principal experiments use at most four retrieval turns and retrieve six documents per turn.",
   "S2G-RAG reports the strongest EM and F1 among the compared systems across the BM25 and E5 settings, with particularly large gains on HotpotQA and 2WikiMultiHopQA.",
   "On HotpotQA with BM25, removing S2G-Judge causes the largest reported ablation loss, reducing EM from 43.3 to 27.5 and F1 from 56.5 to 37.6.",
   "Against a sufficiency proxy based on whether all gold supporting titles have been retrieved, the judge has a reported false-positive rate of 6.44 percent but judges 31.60 percent of proxy-sufficient cases as still insufficient, indicating conservative stopping behavior."
  ]
 },
 {
  "paper_id": "2604.25676",
  "title": "CORAL: Adaptive Retrieval Loop for Culturally-Aligned Multilingual RAG",
  "research_question": "Can critique-driven iterative revision of both the corpus selection and the retrieval query improve culturally aligned multilingual RAG compared with fixed multilingual retrieval spaces?",
  "key_findings": [
   "CORAL achieved the strongest reported accuracy across the evaluated resource tiers and planner/critic configurations, with the final paper reporting improvements of roughly four percentage points on low-resource BLEnD averages in one configuration and up to 2.82 points on CLIcK.",
   "For the Qwen-based planner and critic, dynamic corpus selection without query rewriting improved the reported BLEnD mid-resource score by 3.78 points and CLIcK by 6.62 points relative to the multiRAG baseline.",
   "Adding query reformulation on top of dynamic selection produced further gains; with the GPT-OSS configuration the reported increments included 2.36 points on low-resource BLEnD and 1.41 points on CLIcK.",
   "Fixed retrieval from a culture's own language corpus remained below CORAL in the reported ablation, while indiscriminately pooling corpora could introduce culturally mismatched evidence.",
   "In a manual analysis of 158 rewritten queries from 100 CLIcK questions, 53.8% of rewrites narrowed the query and 32.9% were categorized as paraphrases; narrowing frequently supplied contextual details that the critic had identified as missing."
  ]
 },
 {
  "paper_id": "2605.03534",
  "title": "SURE-RAG: Sufficiency and Uncertainty-Aware Evidence Verification for Selective Retrieval-Augmented Generation",
  "research_question": "Can a structured set-level verifier determine whether retrieved evidence is sufficient to support a candidate answer and use uncertainty-aware selective prediction to abstain when that support is inadequate?",
  "key_findings": [
   "On controlled HotpotQA-RAG v3, calibrated SURE-RAG reaches 0.9075 Macro-F1 and raw SURE-RAG reaches 0.8951, substantially above DeBERTa mean-pooling at 0.6516 and comparable to the strong concat cross-encoder at 0.8888.",
   "Set-level answer aggregation materially improves over pooling-only verification, supporting the paper's argument that evidence sufficiency cannot be reduced to selecting the individually most supportive passage.",
   "SURE-RAG provides a strong low-coverage selective-ranking benefit, but this advantage does not constitute a strict high-coverage or anytime-valid risk guarantee.",
   "Post-hoc calibration improves binary expected calibration error from 0.0304 to 0.0198 but does not improve Risk@30, which changes from 0.1642 to 0.1670.",
   "Counterfactual swaps show near-perfect sensitivity to degradation of the evidence set on the controlled benchmark, including perfect reported success for partial, hard-insufficient, and irrelevant evidence substitutions."
  ]
 },
 {
  "paper_id": "2605.05245",
  "title": "AdaGATE: Adaptive Gap-Aware Token-Efficient Evidence Assembly for Multi-Hop Retrieval-Augmented Generation",
  "research_question": "Can a training-free multi-hop RAG controller use explicit evidence gaps and utility-based replacement to assemble sufficient complementary evidence under a global token constraint while remaining robust to redundant and noisy retrieval?",
  "key_findings": [
   "AdaGATE obtains the highest evidence F1 among the compared controllers in all three reported conditions: 62.3% on clean data, 71.2% with redundancy injection, and 62.7% with noise injection.",
   "AdaGATE uses 2.6 times fewer input tokens than Adaptive-k while obtaining higher evidence F1, demonstrating a favorable evidence-completeness versus context-cost tradeoff in the reported setup.",
   "The redundancy-aware utility mechanism improves rather than degrades evidence F1 under the redundancy stress test, while the controller also reduces the amount of selected context.",
   "Under noise injection, evidence F1 remains close to the clean result even though answer accuracy declines, indicating that evidence-set completeness can remain comparatively stable while passage quality or downstream reasoning deteriorates.",
   "The controller explicitly bounds final evidence length and can terminate on resolved gaps, lack of useful repair, or a repair-iteration ceiling, thereby combining structured sufficiency reasoning with bounded evidence assembly."
  ]
 },
 {
  "paper_id": "2606.05658",
  "title": "Agent-Orchestrated Adaptive RAG: A Comparative Study on Structured and Multi-Hop Retrieval",
  "research_question": "How do adaptive query decomposition, reflection, and rule-based strategy orchestration affect retrieval quality, citation quality, and latency in structured versus open-domain multi-hop RAG?",
  "key_findings": [
   "On the structured DevOps corpus, decomposition raises overall score from 0.814 to 0.855, critical-source recall from 0.750 to 0.806, MRR from 0.556 to 0.722, Success@5 from 0.833 to 1.000, and citation accuracy from 0.750 to 0.917, while latency rises from 21.00 to 47.66 seconds.",
   "On MuSiQue, decomposition improves overall score, citation accuracy, and topic coverage but sharply degrades retrieval ranking, with MRR falling from 0.469 to 0.102 and Success@5 from 1.000 to 0.063.",
   "The implemented reflection mechanism does not yield reliable quality gains: overall score falls on both DevOps and MuSiQue while MuSiQue latency increases from 17.21 to 103.53 seconds.",
   "Routing behavior is strongly domain-dependent, with 69.2% of DevOps queries handled by standard retrieval and only about 5% decomposed, compared with roughly 16% decomposition on MuSiQue.",
   "Even on MuSiQue, 49% of queries remain in the complex-RAG route rather than the decomposition route, which the authors interpret as evidence that the current decomposition trigger is conservative."
  ]
 },
 {
  "paper_id": "2606.13814",
  "title": "TASR: Training-Free Adaptive Stopping for Iterative Retrieval",
  "research_question": "Can iterative RAG stop adaptively without a learned stopping controller by combining answer stability with calibrated model confidence while preserving answer quality and reducing retrieval calls?",
  "key_findings": [
   "Across the primary three-model by two-dataset distractor grid, TASR reached 57.40 macro F1 at 3.13 calls, compared with 53.98 F1 at 3.00 calls for fixed-k=3, while retaining 94.8% of fixed-k=5 F1 with 62.6% of its calls.",
   "Three primary cells showed statistically significant F1 improvements over fixed-k=3 and the remaining three were statistical ties, with no significant regression in the primary grid.",
   "The fixed stopping rule transferred to open-domain BM25, dense retrieval, and a Nemotron-3-Ultra-550B scale stress test without significant regressions in the reported extension experiments.",
   "Verbalized confidence was highly collapsed on the studied RLHF-tuned models, while first-answer-token logit margins provided much stronger separation between correct and incorrect answers.",
   "The margin threshold protects against some premature stops caused by an answer becoming stable before the required evidence has entered the context."
  ]
 },
 {
  "paper_id": "2606.15964",
  "title": "PromptShift-CRC: Drift-Aware Conformal Risk Control for Foundation Models Under Prompt and Domain Shift",
  "research_question": "Can conformal risk control for foundation-model outputs remain approximately calibrated under changing prompt and domain distributions by explicitly detecting representation drift and adapting how historical calibration examples are weighted?",
  "key_findings": [
   "The theoretical result bounds deployment-time exceedance risk by the nominal target plus terms for representation drift, representation mismatch, and finite effective calibration size, making the cost of distribution shift explicit rather than assuming exchangeability is unchanged.",
   "In three prototype shifts for QA topic, summarization domain, and safety intent, PromptShift-CRC achieves reported coverages of 0.895, 0.893, and 0.897 respectively for a 0.90 target, while static calibration collapses to roughly 0.31 to 0.32.",
   "On LongHalQA, static calibration reaches coverage 0.585, rolling calibration 0.784, adaptive CRC 0.875, representation weighting 0.854, and PromptShift-CRC 0.901 against a target of 0.90.",
   "PromptShift-CRC is not uniformly the closest method to the target on every public benchmark; for example, adaptive CRC is closer on the TruthfulQA-derived experiment, where PromptShift-CRC obtains 0.907 and adaptive CRC obtains 0.904 for a 0.90 target.",
   "The ablation study indicates that the online risk-target update and the recent-data fallback are particularly important under sustained drift, with their removal degrading target coverage more than several other component removals."
  ]
 },
 {
  "paper_id": "2606.29054",
  "title": "When Can Conformal Risk Control Certify LLM Outputs? Bounds, Impossibility, and Adaptation for Structured Generation",
  "research_question": "Under what model, task, calibration, risk-target, and distribution-shift conditions can conformal risk control certify structured LLM outputs, and when is the desired selective-generation risk mathematically infeasible?",
  "key_findings": [
   "If the base risk μ exceeds target risk α, any distribution-free selective method must abstain by at least (μ-α)/(M-α), establishing a feasibility floor before calibration.",
   "At strict targets through α=0.20 in the main seed-42 experiment, Hoeffding, Bernstein, and e-CRC certify 51, 72, and 80 of 716 configurations respectively, with zero test violations among those certified configurations.",
   "Variance-aware certification is especially useful with limited calibration data: at a 10% calibration fraction, certification rates are 1.1% for Hoeffding, 1.9% for Bernstein, and 4.2% for e-CRC.",
   "Larger model scale reduces average base risk in the reported Qwen2.5 sequence and thereby expands the range of configurations that can be certified.",
   "Under the paper's index-order temporal shift, static CRC violates its target on 15 of 25 configurations whereas ACI reduces violations to 1 of 25; under gradual severity shift, static violations rise as high as 56% while ACI remains below 12%."
  ]
 },
 {
  "paper_id": "2606.29090",
  "title": "AB-RAG: Adaptive Budgeted Retrieval-Augmented Generation for Reliable Question Answering",
  "research_question": "Can a training-free RAG system use answer confidence to decide when to stop, when to retrieve more evidence, and how to bound retrieval cost while remaining usable with both open-weight models and closed APIs?",
  "key_findings": [
   "AB-RAG implements an explicit retrieve-or-stop loop: answers above the confidence threshold return immediately, while low-confidence answers trigger deeper retrieval until either the threshold or the retrieval budget is reached.",
   "The combined confidence estimator separated correct from incorrect answers on every evaluated backbone, with reported AUROC values from 0.600 to 0.733 in the static-versus-adaptive comparison.",
   "Adaptive retrieval improved Exact Match for Llama-3.2-3B on HotpotQA from 39.5 to 45.0 and for Claude Haiku on TriviaQA from 35.5 to 40.0, but produced no EM gain for the small Qwen model.",
   "Model certainty was the strongest individual confidence signal, while answer-evidence cosine similarity was weak or worse than chance for short-answer QA.",
   "The original interpretation of reranker-score variance was empirically reversed: treating high variance as a penalty produced AUROC 0.427, while treating it as a reward raised AUROC to 0.573."
  ]
 },
 {
  "paper_id": "2606.29959",
  "title": "Know Before You Fetch: Calibrated Retrieval-Budget Allocation for Retrieval-Augmented Generation",
  "research_question": "Can calibrated estimates of closed-book correctness be used before retrieval to allocate zero, compact, or full retrieval budgets per query, while also supporting abstention and explicitly accounting for retrieval calls, passage tokens, and latency?",
  "key_findings": [
   "Logistic calibration substantially improved probability quality without materially changing the underlying ranking signal; for example, sequence-log-probability ECE on Natural Questions fell from 0.643 before calibration to 0.009 after calibration.",
   "Graded zero/one/five-passage allocation improved full-context and passage-budget frontiers but produced essentially no improvement in retrieval-call frontier AUC because a one-passage retrieval still incurs a retrieval call.",
   "The amount of retrieval that can safely be skipped grows with reader capability: on TriviaQA, the retrieval rate needed to match always-RAG fell from 99.5% for Qwen3-1.7B to 46.0% for Qwen3-32B.",
   "Validation-selected thresholds on TriviaQA approached always-RAG accuracy while retrieving for roughly two-thirds of queries, whereas Natural Questions and MS MARCO selected retrieval for about 97-99% of queries because their closed-book headroom was low.",
   "Using confidence for the answer actually returned improved selective-prediction accuracy on TriviaQA and Natural Questions, but did not outperform naive closed-book confidence on MS MARCO."
  ]
 },
 {
  "paper_id": "2607.06507",
  "title": "DynaKRAG: A Unified Framework for Learnable Evidence Control in Multi-Hop Retrieval-Augmented Generation",
  "research_question": "Can multi-hop RAG jointly learn when to continue retrieving, which evidence-acquisition action to take, and when to stop so as to improve answer quality while controlling retrieval and generation cost?",
  "key_findings": [
   "The framework unifies frontier retrieval, gap-directed retrieval, query rewriting, bridge expansion, sufficiency checking, stopping, and terminal compression within one explicit evidence-control policy.",
   "A deterministic validity layer prevents actions when prerequisites are absent and prevents further retrieval when the configured retrieval budget is exhausted.",
   "The learned continuation gate explicitly decides whether the current state should stop or continue, while a separate advantage scorer chooses the next valid evidence-acquisition action.",
   "Across the reported nine dataset-backbone combinations, DynaKRAG obtained the highest reported EM/F1 among the compared systems and used 10.1% to 34.3% fewer tokens and 15.1% to 43.4% fewer retrieval calls than the matched S2G-RAG baseline.",
   "Removing the learned advantage scorer, sufficiency check, learned continuation mechanism, or terminal compression reduced F1 in the reported ablations, with the effect size depending on the dataset."
  ]
 },
 {
  "paper_id": "2607.24010",
  "title": "When Should Active RAG Retrieve? A Budget-Aware Evaluation of Utility, Calibration, and Cost",
  "research_question": "How should an Active RAG controller decide when retrieval is worth its cost while respecting a future evidence-usage budget, accounting for retrieval benefit, retrieval harm, threshold calibration error, and trigger-side computation?",
  "key_findings": [
   "Retrieval utility is heterogeneous rather than monotonic: with Qwen2.5-1.5B, retrieval harms 8.8% of 2Wiki examples, 4.0% of HotpotQA examples, and 1.5% of MuSiQue examples even though always-retrieve accuracy improves overall.",
   "A nominal evidence-usage target does not guarantee the same held-out usage: at the 50% target, several routers exceed the budget on substantial fractions of random calibration/test splits.",
   "Router rankings change across datasets, budgets, and model families, so a single adaptive-accuracy number does not provide a stable characterization of retrieval-policy quality.",
   "Simple uncertainty and retrieval-score baselines often rival learned budgeted-utility routers, so additional router complexity does not consistently translate into superior budgeted retrieval decisions.",
   "Exact top-k frontiers and deployable threshold frontiers measure different properties: the first isolates ranking quality at matched usage, whereas the second measures whether a threshold calibrated on historical data transfers to future inputs."
  ]
 },
 {
  "paper_id": "2607.27726",
  "title": "Baikal: Structured Search for Deep Research over Data Lakes",
  "research_question": "Can deep research over large heterogeneous data lakes be improved by partitioning evidence into semantic regions and adaptively allocating a limited search budget across those regions instead of repeatedly following locally promising retrieval results?",
  "key_findings": [
   "The strongest reported Baikal configurations reach report scores of 0.46 on HybridQA and 0.45 on TAT-QA, corresponding to improvements of 28% and 36% over the strongest compared baselines according to the paper.",
   "Three of the four Baikal region-selection policies outperform every reported baseline on both data lakes, while the LLM-only region policy underperforms on HybridQA because it concentrates too heavily on apparently safe regions and loses evidence coverage.",
   "Baikal recovers substantially more gold evidence than the compared OpenCode and DeepSearcher baselines, including approximately 0.32 to 0.35 gold-table recall on HybridQA versus lower values for those baselines.",
   "At the default budget of 50 findings, policy differences are difficult to separate because the available budget is close to the number of candidate semantic regions; in a 200-finding experiment on three HybridQA queries, Bayesian-UCB gains 5.61 cumulative finding-score points, or 8.8%, over random search.",
   "Ablations show that both the region-restricted research agent and semantic region expansion materially contribute to report quality, while LLM subquestion selection adds a smaller further gain."
  ]
 },
 {
  "paper_id": "2608.02195",
  "title": "MEGRAG: Multi-Granular Evidence Graphs for Answer-Aware Multi-Hop RAG",
  "research_question": "Can multi-hop RAG improve answer quality and efficiency by representing evidence at multiple granularities and explicitly deciding, after each reasoning step, whether the original question is sufficiently resolved or further retrieval is needed?",
  "key_findings": [
   "The controller explicitly represents remaining information need and stops only when it judges the initial query resolved; otherwise it formulates a focused query for the missing information.",
   "Adaptive fine-to-coarse evidence selection outperformed the best fixed-granularity variant by 1.45, 3.49, and 6.23 F1 points on the three evaluated datasets.",
   "Structured reasoning history materially contributed to performance, with its removal reducing F1 by 1.49, 2.83, and 5.81 points across the evaluated datasets.",
   "Answer-aware early stopping substantially reduced LLM calls and token use relative to forcing four retrieval-reasoning steps, although the accuracy trade-off varied by dataset.",
   "The system has an explicit bounded-search mechanism: it uses a hard step budget, and trajectories that remain unresolved when the budget is exhausted are handled by a final resolver and marked as budget exhausted."
  ]
 },
 {
  "paper_id": "2608.08512",
  "title": "Time Present and Time Past: Benchmarking Large Language Models on Temporally Evolving Document Understanding",
  "research_question": "How well can modern language models identify and reason from the version of an evolving authoritative document that was actually in force at a queried date under parametric, gold-context, and retrieval-based access?",
  "key_findings": [
   "Providing document access substantially improves performance for every evaluated model, but the best reported macro strict accuracy is still only 68.49% for GPT-5 in the gold-context ICL setting.",
   "For GPT-5, macro strict accuracy rises from 35.39% with parametric knowledge to 57.06% with RAG and 68.49% with gold-context ICL, illustrating both the value of authoritative context and the remaining version-resolution gap.",
   "Event Sorting drops from 66.23% for GPT-5 with gold context to 31.42% under RAG because a standard semantic retriever without temporal reranking often fails to retrieve all provisions required to reconstruct the amendment timeline.",
   "Context Misalignment is extremely difficult: strict accuracy never exceeds 27.62% under ICL or 25.09% under RAG even when authoritative clauses are supplied alongside a misleading premise.",
   "The benchmark's hard date gate exposes cases in which a model captures the semantic rule but associates it with the wrong effective date, which ordinary semantic-answer scoring would over-credit."
  ]
 },
 {
  "paper_id": "2608.13237",
  "title": "When Should Multi-Round RAG Stop? Structured Stopping Judgments and Retrieval Reduction in Search-R1",
  "research_question": "Can a structured sufficiency-and-gap judge change only the stopping time of a frozen multi-round Search-R1 trajectory to reduce retrieval while keeping answer-quality loss within a prespecified bound, and what stopping risk remains?",
  "key_findings": [
   "The confirmatory stopping policy removed 77 retrieval calls, reducing mean searches from 2.60125 to 2.50500, a 3.70% reduction, with the confidence interval satisfying the prespecified retrieval-reduction criterion.",
   "Official exact match decreased from 0.44875 to 0.44250, a 0.625 percentage-point loss whose confidence interval remained inside the prespecified two-percentage-point noninferiority margin; this does not establish unchanged or improved accuracy.",
   "Among 69 confirmatory early stops, 42 were classified as safe and 27 as unsafe, so 39.13% of the executed early stops were unsafe under the paper's probe-based definition.",
   "The expanded structured judge improved STOP average precision over the structured-base judge, but validation STOP precision did not transfer to the final test set and calibration remained weak.",
   "Exploratory trajectories contained substantial over-retrieval headroom: 143 of 523 native SEARCH actions occurred after the answer probe was already correct, and a native-preserving cost oracle could remove 131 searches while retaining native exact match."
  ]
 },
 {
  "paper_id": "2609.08364",
  "title": "SentryLine: Evidence-Grounded Question Answering over Evolving Documents in Oncology Care",
  "research_question": "Can a clinical RAG system reliably answer questions from evolving oncology guidelines while preserving exact source provenance, detecting superseded recommendations, and presenting evidence appropriately to clinicians and patients?",
  "key_findings": [
   "SentryLine explicitly incorporates temporal/version-aware provenance by identifying guideline years, confirmed updates, superseding passages, and stale recommendations.",
   "Each generated citation is converted into a structured evidence item containing document, page, passage text, citation key, and update status, enabling paragraph-level navigation back to the source.",
   "The temporal verifier only accepts a stale-guidance flag when it is backed by an explicit superseding passage, reducing reliance on the model's parametric knowledge of guideline history.",
   "On Gemini, SentryLine reached 59.3% fully correct on contrasting questions containing outdated recommendations, compared with 43.5% to 50.9% for the reported RAG baselines.",
   "Removing the temporal verifier raised the DeepSeek role-specific incorrect rate from 5.6% to 26.4%, indicating a substantial contribution from temporal checking in that setting."
  ]
 },
 {
  "paper_id": "2609.11572",
  "title": "TimelyRAG: Semantic-Temporal Hybrid Retrieval for Time-Critical Question Answering in Overlapping-Evolving Documents",
  "research_question": "Can a retriever-agnostic semantic-temporal reranking method reliably select the temporally valid version of highly overlapping evolving documents for time-critical question answering?",
  "key_findings": [
   "On the four overlapping-evolving TimelyQABench domains, temporal reranking improves retrieval over the corresponding vanilla sparse and dense retrievers, with the largest reported nDCG@10 gain reaching 28.6%.",
   "TimelyRAG substantially outperforms deployable temporal query rewriting, hard effective-date filtering, and LLM-based temporal reranking on the reported TimelyQABench nDCG@5 and MAP@5 comparisons, although an oracle using gold temporal information remains stronger.",
   "The method also improves retrieval on the disjoint-evolving TS-Retriever benchmark while leaving BEIR-FiQA retrieval scores unchanged when temporal context is absent.",
   "Ablations across four domains and both BM25 and BGE-M3 show that the full model performs better than variants using naive temporal distance or removing event-time activation or temporal-granularity modeling.",
   "Temporal reranking adds low incremental latency in the reported implementation: 2.15 ms per query over BM25 and 2.64 ms per query over BGE-M3 when averaged across TimelyQABench domains."
  ]
 },
 {
  "paper_id": "2609.16301",
  "title": "CLEAR: Cross-Source Evidence Adjudication for Large Language Models in Medicine",
  "research_question": "Can an LLM improve medical reasoning by keeping parametric, curated-local, and dynamically retrieved evidence separate, explicitly adjudicating disagreements among them, and selectively performing additional retrieval when existing evidence remains unresolved?",
  "key_findings": [
   "CLEAR shows its largest gains when the backbone's parametric baseline is weaker; for Qwen-3.5-9B, the best reported CLEAR configurations substantially improve MedQA and NEJM-QA over direct inference and conventional retrieval baselines.",
   "For o3-mini across MedQA, PubMedQA, and NEJM-QA, the full three-source CLEAR configuration has the highest aggregate score even though the best individual method varies by dataset.",
   "Targeted follow-up retrieval on Qwen-3.5-9B increases aggregate performance from 77.22 to 78.13, while only 12 of 123 triggered follow-up searches produce an accepted answer revision.",
   "External retrieval is not uniformly beneficial: when the o3-mini parametric baseline is already strong, additional evidence can provide little benefit and the default CLEAR configuration degrades performance on HealthBench.",
   "The architecture preserves the identity and provenance of parametric, local, and dynamic evidence until adjudication, making cross-source agreement and conflict explicit instead of merging all retrieved context before reasoning."
  ]
 },
 {
  "paper_id": "doi-10-1016-0306-4379-96-00017-8",
  "title": "Semantics of Time-Varying Information",
  "research_question": "How can the underlying semantics of time-varying database facts be characterized independently of particular temporal representations, especially with respect to valid time, transaction time, and equivalence of different temporal data models?",
  "key_findings": [
   "Valid time describes when a fact holds in the modeled reality, whereas transaction time describes when the fact is current in the database; the two dimensions have distinct semantics and can be recorded independently.",
   "Although valid time and transaction time are semantically orthogonal, applications can impose systematic relationships between them, motivating a taxonomy of specialized temporal relations such as retroactive, predictive, delayed, and degenerate relations.",
   "A single fact can legitimately accumulate multiple transaction times as it is copied or transferred through different relations or databases, preserving when each system stored that fact and enabling queries about earlier database states through later copies.",
   "The Bitemporal Conceptual Data Model separates the semantics of temporal information from representation and performance concerns by associating facts with regions in valid-time and transaction-time space.",
   "Snapshot equivalence provides a representation-independent criterion for saying that structurally different temporal relations contain the same information, and the authors describe mappings between the BCDM and six existing bitemporal relational models that preserve this equivalence."
  ]
 },
 {
  "paper_id": "doi-10-1038-s41598-026-71936-x",
  "title": "Privacy-provisioned-permission-aware RAG in cloud using identity and access management, trust and large-language models (PPPARITL)",
  "research_question": "Can a cloud-based RAG architecture combine identity and access management, dynamic trust assessment, encrypted embeddings, and malicious-query controls to reduce unauthorized information access while retaining useful LLM-assisted retrieval?",
  "key_findings": [
   "PPPARITL places authorization filtering before similarity ranking, so only candidates passing the RRAC access-control gate are eligible for decryption and retrieval.",
   "The framework combines static IAM policy enforcement with a second-stage trust score derived from contextual, behavioral, and historical interactions.",
   "Document and query embeddings are protected at rest using CKKS homomorphic encryption, with the decryption key held by an administrator.",
   "The architecture includes query sanitization and continuous malicious-query monitoring intended to mitigate denial-of-service and insider threats and to support user revocation.",
   "On the reported synthetic enterprise evaluation, the proposed approach reaches 95.84% authorization accuracy and reduces the False Access Rate relative to baseline access-control approaches."
  ]
 },
 {
  "paper_id": "doi-10-1109-access-2025-3628960",
  "title": "Permission-Aware RAG: Identity and Access Management (IAM)-Based Access Filtering in Multi-Resource Environments",
  "research_question": "Can a RAG system enforce fine-grained, current document permissions across independently governed resources by validating each retrieved document against its provider's native IAM system without centrally merging heterogeneous access policies?",
  "key_findings": [
   "The framework preserves provider-specific policy authority by performing per-document authorization through native IAM systems after semantic candidate retrieval and before documents enter the LLM context.",
   "The architecture maintains persistent resource and source-local identifiers and separates embeddings from mutable metadata, enabling resource metadata and permission-related mappings to be updated without necessarily rebuilding embeddings.",
   "In the constructed qualitative comparison, a manually merged policy omitted an attribute and incorrectly exposed a document, while delegated native-IAM checking denied that access.",
   "Across eight user profiles in the 1,000-question quantitative experiment, the framework achieved a PASS Match result for permission enforcement against the experiment's ground-truth authorization lists.",
   "Answer quality generally increased with permission coverage; for example, the reported F1 rose from 0.30 for a user with 9.48% permission coverage to 0.50 for a user with 69.84% coverage."
  ]
 },
 {
  "paper_id": "doi-10-1145-1247715-1247720",
  "title": "Temporal profiles of queries",
  "research_question": "Can temporal profiles derived from the timestamps of retrieved documents characterize a query's temporal dependence, classify temporal query types, and improve prediction of retrieval effectiveness?",
  "key_findings": [
   "Temporal-profile features distinguish temporal query classes substantially better than majority-class baselines on several evaluated collections.",
   "On the TREC Novelty queries, classification accuracy was 0.56 for the majority baseline, 0.62 with content clarity, 0.68 with temporal features, and 0.70 when temporal features and content clarity were combined.",
   "For distinguishing temporally ambiguous from atemporal ad-hoc queries, combining temporal and content features achieved 0.73 accuracy on both the AP and WSJ collections, compared with majority baselines of 0.54 and 0.66 respectively.",
   "In three-way classification, temporal features reached 0.75 accuracy on the search-log data versus a 0.27 majority baseline, while results were weaker on WSJ, showing that effectiveness varies substantially by collection.",
   "Temporal features used alone were generally weak predictors of average precision, but combining them with content clarity produced substantially stronger held-out correlations than either feature family alone."
  ]
 },
 {
  "paper_id": "doi-10-1145-1571941-1572085",
  "title": "Improving search relevance for implicitly temporal queries",
  "research_question": "Can frequency patterns of year-qualified query variants reveal implicit temporal intent and be used to improve ranking for queries whose desired results depend on a year that the user did not explicitly specify?",
  "key_findings": [
   "The query-log analysis estimated that more than 7% of queries belong to the implicitly year-qualified category considered by the paper.",
   "The proposed mining algorithm can infer implicit temporal intent solely from frequencies of base queries and their year-qualified variants, without click or session data.",
   "Baseline DCG@5 decreased monotonically as queries became more strongly associated with implicit temporal intent, indicating that the commercial search engine performed worse on the most temporally specific queries in this evaluation.",
   "Temporal reordering produced little or negative change for low-ambiguity-score groups but improved the highest temporal-intent group from 7.02 to 7.07 DCG@5, a reported 0.84% statistically significant improvement.",
   "The effectiveness of temporal reordering increased as the estimated confidence that a query had implicit temporal intent increased."
  ]
 },
 {
  "paper_id": "doi-10-1145-181550-181560",
  "title": "A Consensus Glossary of Temporal Database Concepts",
  "research_question": "Can the temporal-database community establish precise, broadly accepted definitions and names for the core concepts needed to describe temporal data, histories, and multiple dimensions of time?",
  "key_findings": [
   "The glossary separates valid time, meaning when a fact is true in the modeled reality, from transaction time, meaning when that fact is current and retrievable in the database.",
   "Transaction time is system-maintained, ordered consistently with database transactions, and does not permit rewriting past transaction-time values.",
   "A bitemporal relation combines one system-supported valid-time dimension with one system-supported transaction-time dimension, providing distinct representations of real-world validity and database-record history.",
   "The glossary defines history broadly enough to represent the temporal evolution of attributes, entities, relationships, schemas, transactions, and other database objects.",
   "Snapshot equivalence provides a way to regard differently represented temporal relations as equivalent when they yield the same state at every instant."
  ]
 },
 {
  "paper_id": "doi-10-1145-3786625",
  "title": "HONEYBEE: Efficient Role-based Access Control for Vector Databases via Dynamic Partitioning",
  "research_question": "Can the structure of role-based access-control policies be exploited to partition and selectively replicate vector indexes so that permission-safe search achieves a better latency-memory-recall trade-off than either post-filtering or dedicated per-role indexes?",
  "key_findings": [
   "Overlapping RBAC-aware partitions allow HONEYBEE to interpolate between one shared filtered index and highly redundant per-role indexes instead of being restricted to either extreme.",
   "With pgvector HNSW, HONEYBEE achieved up to a 13.5-fold query speedup over PostgreSQL row-level-security post-filtering while using 1.24 times the single-index memory footprint in the reported high-top-k setting.",
   "At comparable query performance to dedicated role partitioning, the reported high-top-k configuration reduced additional memory consumption by 90.4%.",
   "The system explicitly optimizes a three-way trade-off among query latency, memory overhead, and retrieval recall rather than treating permission filtering as an independent post-processing step.",
   "Physical partitioning was experimentally faster than logical partitioning under equal memory budgets because logical traversal incurred additional cache-miss costs, although logical partitioning can be useful when replication is unusually expensive."
  ]
 },
 {
  "paper_id": "doi-10-1609-aaai-v39i14-33670",
  "title": "Temporal Conjunctive Query Answering via Rewriting",
  "research_question": "Can temporal conjunctive queries over description-logic knowledge bases be answered more efficiently by rewriting temporal formulas into combinations of ordinary conjunctive and union-of-conjunctive queries instead of constructing finite automata?",
  "key_findings": [
   "The rewriting algorithm is sound and complete for the temporal conjunctive-query answering problem addressed by the paper and avoids constructing the finite automata required by the previous approach.",
   "Across benchmark cases completed by both systems, the rewriting implementation reports an average speedup of 19.09 with standard deviation 45.79 relative to the finite-automaton baseline.",
   "The previous finite-automaton system times out on three benchmark instances under the ten-hour limit, whereas the rewriting system completes those instances in approximately 3.52, 5.72, and 7.88 hours.",
   "For several temporal formulas, rewriting eliminates expensive UCQ entailment checks entirely, and the evaluation attributes much of the observed speedup on the largest benchmarks to reducing UCQ-answering work.",
   "The paper defines the proper syntactic subclass TCQ_CQ*, proves that membership in this fragment is decidable in polynomial time, and shows that members can be handled using only a CQ-answering oracle."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-2026-acl-long-1562",
  "title": "RAG-on-a-Diet: A Reinforcement Learning-Based Dynamic Resource Optimization Framework for RAG",
  "research_question": "Can a lightweight reinforcement-learning controller dynamically choose the least expensive adequate language model at each multi-hop RAG step while preserving answer quality and terminating unnecessary reasoning early?",
  "key_findings": [
   "On HotpotQA, the proposed controller obtained F1 0.7387 at reported cost 17.35, reducing cost by 60.07% relative to the DeepSeek-R1 IRCoT configuration while accepting a 3.70% F1 decrease.",
   "Relative to Adaptive-RAG, the method reports both a small F1 improvement and a 37.30% cost reduction on HotpotQA.",
   "Adding step-wise, cumulative, cost, and balance components to the reward progressively improves the quality-cost tradeoff; the full reward reaches F1 0.7387, cost 17.35, and 3.2 average hops versus F1 0.6985, cost 23.72, and 4.1 hops for terminal-only reward.",
   "The dual stopping mechanism outperforms both a ten-hop no-termination configuration and a five-hop hard-cap-only configuration, producing F1 0.7387 with 3.2 average hops and cost 17.35.",
   "The routing agent is reported to contain about 150,000 parameters and to add roughly 9.05 milliseconds of decision latency per hop, corresponding to about 0.11% of the DeepSeek-R1 inference latency used for comparison."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-2026-findings-acl-2090",
  "title": "Beyond Single-Shot: Multi-step Tool Retrieval via Query Planning",
  "research_question": "Can iterative query planning that decomposes complex requests and adapts subsequent queries to retrieval feedback outperform single-shot retrieval for large compositional tool libraries and improve downstream tool execution?",
  "key_findings": [
   "On ToolRet, ToolQP improved the reported macro zero-shot nDCG@10 and Completeness@10 from 29.8 and 27.0 for the base gte-Qwen retriever to 36.9 and 35.8.",
   "When transferred to retrievers not used to create its training trajectories, ToolQP produced average zero-shot gains of 5.4 points in nDCG@10 and 7.1 points in Completeness@10.",
   "End-to-end evaluation showed higher execution performance after ToolQP retrieval, including about a three-point accuracy improvement on API-Bank and roughly eight-to-nine-point pass-rate improvements on the reported StableToolBench measures.",
   "Ablations indicate that supervised training supplies most of the in-domain improvement, while the subsequent reinforcement-learning stage provides additional gains and is particularly useful for zero-shot performance.",
   "Removing the original user instruction from the iterative planner reduced performance, supporting the use of the original request as an anchor when subtask decomposition or intermediate retrieval feedback is incomplete."
  ]
 },
 {
  "paper_id": "doi-10-32604-cmc-2026-086343",
  "title": "Do LLMs Know When Evidence is Insufficient? An Evidence Sufficiency Benchmark for Answer-Abstention Calibration in Retrieval-Augmented Generation",
  "research_question": "Do contemporary LLMs appropriately switch from answering to abstaining as retrieved evidence moves from sufficient support through partial, irrelevant, absent, and explicitly conflicting evidence?",
  "key_findings": [
   "Models generally abstain more as evidence degrades from supported to irrelevant or absent, but this pattern reverses under explicit conflict: L5 abstention is only 9.5% to 34.8% compared with 34% to 84% under no-context L4.",
   "All seven evaluated models over-answer more than 65% of conflicting-evidence cases; Gemini 2.5 Flash abstains most at 34.8%, while Claude Sonnet 4.6 abstains only 9.5%.",
   "Evidence picking, in which a model selects one side of contradictory retrieved evidence, is the dominant reported L5 failure pattern.",
   "Explicit sufficiency-oriented prompting can substantially increase conflict abstention for some models but has strongly model-dependent effects; for example, P1-to-P3 abstention changes from 5.2% to 55.2% for Gemini and from 7.2% to 11.2% for Claude Sonnet 4.6.",
   "Six of seven models exhibit significant dependence on whether gold or conflicting evidence appears first, with the largest reported absolute order effect reaching 20.5 percentage points."
  ]
 },
 {
  "paper_id": "manual-2bb76a9136",
  "title": "IDCR: Information-Directed Conformal Retrieval",
  "research_question": "Can retrieval choose documents according to their expected reduction in conformal predictive uncertainty while preserving distribution-free coverage and remaining computationally tractable?",
  "key_findings": [
   "IDCR directly couples retrieval selection to conformal prediction-set volume while preserving the paper's claimed distribution-free predictive coverage.",
   "The conformal-volume objective is reported to be exactly equivalent to a log-determinant maximization objective that is monotone submodular, allowing greedy selection with a 1-1/e approximation guarantee.",
   "On the reported MIMIC-IV experiment, greedy selection achieved a mean greedy-to-optimal ratio of 0.9999, while conformal ellipsoids were reported as 4.8 times smaller than random retrieval and 5.8 times smaller than cosine retrieval while retaining coverage.",
   "A marginal-gain-separation gate routes uncertain selection decisions to two-step lookahead, which the abstract reports as closing 77% of the remaining greedy-to-optimal gap.",
   "The abstract reports that gains extend beyond the clinical task to SciQ and GoEmotions and that uncertainty is reduced relative to learned and uncertainty-aware retrieval baselines on GoEmotions and LexGLUE."
  ]
 }
]

Open gaps carried over from round 3 (the corpus above
includes the papers of every round so far):
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

Decide for each whether this corpus now resolves it. Never drop or
downgrade an unresolved gap: it stays open, with the same id, until the
literature closes it.

Produce two blocks.

Block 1, `synthesis.json`, one JSON object with these fields:
- topic: string
- paper_count: integer
- executive_summary: 100-150 words
- themes: list of strings
- findings: 5-12 items {statement, confidence: HIGH|MEDIUM|LOW,
  evidence: [{paper_id, section, quote (at most one sentence, optional)}]}
- contradictions: list of {topic, papers: [paper_id...], note}
- gaps: list of {description, classification: ACADEMIC|ENGINEERING|OUT_OF_SCOPE,
  priority: HIGH|MEDIUM|LOW, suggested_query (ACADEMIC only)}
- actionable_insights: list of strings
- confidence_summary: string
- limitations: list of strings
- gap_status (rounds after the first): one entry per prior gap
  {id, status: resolved|open, note, evidence: [paper_id...]}; a gap is
  `resolved` only when papers in this corpus answer it, otherwise it stays
  `open` and must also appear again in `gaps` with the same id

JSON schema (additional fields allowed):
{
 "$schema": "http://json-schema.org/draft-07/schema#",
 "title": "SynthesisReport",
 "description": "Schema for the cross-paper synthesis report produced by the summarize stage.",
 "type": "object",
 "required": [
  "topic",
  "findings",
  "gaps"
 ],
 "properties": {
  "topic": {
   "type": "string",
   "minLength": 1
  },
  "run_id": {
   "type": "string"
  },
  "generated_at": {
   "type": "string"
  },
  "findings": {
   "type": "array",
   "items": {
    "type": "object",
    "required": [
     "statement",
     "confidence",
     "evidence"
    ],
    "properties": {
     "statement": {
      "type": "string",
      "minLength": 1
     },
     "confidence": {
      "type": "string",
      "enum": [
       "HIGH",
       "MEDIUM",
       "LOW"
      ]
     },
     "evidence": {
      "type": "array",
      "items": {
       "type": "object",
       "required": [
        "paper_id"
       ],
       "properties": {
        "paper_id": {
         "type": "string"
        },
        "section": {
         "type": "string"
        },
        "quote": {
         "type": "string"
        }
       }
      },
      "minItems": 1
     }
    }
   }
  },
  "gaps": {
   "type": "array",
   "items": {
    "type": "object",
    "required": [
     "description"
    ],
    "properties": {
     "description": {
      "type": "string",
      "minLength": 1
     },
     "classification": {
      "type": "string",
      "enum": [
       "ACADEMIC",
       "ENGINEERING",
       "OUT_OF_SCOPE"
      ]
     },
     "priority": {
      "type": "string",
      "enum": [
       "HIGH",
       "MEDIUM",
       "LOW"
      ]
     },
     "suggested_query": {
      "type": "string"
     }
    }
   }
  },
  "themes": {
   "type": "array",
   "items": {
    "type": "string"
   }
  },
  "paper_count": {
   "type": "integer",
   "minimum": 0
  }
 },
 "additionalProperties": true
}

Block 2, `synthesis.md`: the same content as a Markdown narrative with the
sections Executive Summary, Themes, Contradictions, Open Gaps, Actionable
Insights, Confidence Summary, Limitations. Cite papers as [paper_id].

Reply format:
===BEGIN synthesis.json===
<content>
===END synthesis.json===
===BEGIN synthesis.md===
<content>
===END synthesis.md===
