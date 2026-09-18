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

Research topic: **Direct empirical NLP methods for longitudinal work-item revision in workplace or operational communication, especially relation labeling for supersession/correction/supplementation/reopening/conflict and evidence models separating claimed completion from independently corroborated completion.**

Below are 38 per-paper analyses (reduced to questions and top findings to fit the size cap). Synthesize them into a
cross-paper synthesis: recurring themes, contradictions (name the papers on
both sides), open gaps classified as ENGINEERING (fillable from docs, code,
or benchmarks), ACADEMIC (needs more papers) or OUT_OF_SCOPE, actionable
insights, an overall confidence note, and the synthesis' own limitations.
Every finding must cite at least one paper_id from this list: `1804.06020`, `1805.06975`, `1909.00429`, `1909.05360`, `2007.14864`, `2011.03088`, `2103.08541`, `2104.01146`, `2110.08222`, `2210.15067`, `2406.00197`, `2406.19764`, `2606.18037`, `2608.20116`, `doi-10-1007-3-540-44503-x-20`, `doi-10-1007-s10458-012-9202-0`, `doi-10-1007-s10579-009-9089-9`, `doi-10-1007-s11390-024-2655-1`, `doi-10-1016-0004-3702-86-90080-9`, `doi-10-1016-0020-0255-94-90059-0`, `doi-10-1016-j-artint-2003-08-003`, `doi-10-1016-j-ipm-2021-102836`, `doi-10-1016-j-ipm-2026-104709`, `doi-10-1016-j-knosys-2016-07-032`, `doi-10-1017-cbo9780511526664-007`, `doi-10-1023-a-1010318403544`, `doi-10-1093-jos-ffn013`, `doi-10-1145-1082473-1082754`, `doi-10-1162-tacl-a-00182`, `doi-10-18653-v1-2021-acl-long-122`, `doi-10-18653-v1-2021-emnlp-main-815`, `doi-10-18653-v1-2023-findings-acl-44`, `doi-10-18653-v1-d18-1155`, `doi-10-18653-v1-p19-1412`, `manual-2362cbe877`, `manual-b3703967d3`, `manual-d574dff39d`, `manual-eef7a0219f`.
Do not cite any other paper.

The independent reviewer that reads this rejects one thing above all others,
and it has rejected the first round of every topic so far for it: **a
project judgement written as a literature finding**. Separate them here and
the review passes on the first attempt.

- A `finding` states what the cited papers demonstrate, and nothing further.
  If the papers show a method works on one corpus, say that; do not say the
  method is required, necessary, or suitable for this project.
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
   Name it in `contradictions` even when it is inconvenient.
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

# Topic 06 context — Work-item state, event factuality, time, and conflicting revisions

## Why this Topic exists

Knowing that an action or decision was mentioned is not enough. msgloom must know its current evidence-backed state: requested, proposed, planned, approved, completed, revoked, superseded, disputed, conditional, or still unresolved. Business communication contains future plans, retrospective reports, corrections, contradictions, changing deadlines, and statements with different effective times.

A dangerous failure is converting “we plan to send Friday” into “sent”, or treating an old approval as current after a revocation. Topic 06 therefore owns **state evolution and temporal/factual reasoning over Topic evidence**.

## Core research object

Maintain an evidence-backed timeline/state model that distinguishes:

- utterance/message time;
- event/effective time;
- deadline/constraint time;
- observed collection time/version;
- factuality/modality (planned, asserted, confirmed, negated, hypothetical, conditional);
- supersession, supplementation, contradiction, and unresolved conflict;
- current accepted assessment versus historical assessments.

The model must preserve evidence rather than overwrite history.

## Product and phase relevance

Phase 1 triage needs current-enough actions, deadlines, risks, and limitations from supplied evidence. Phase 2 investigation can obtain more history/evidence to resolve uncertain state. Reports must not present stale accepted assessments as current when newer input is pending.

## Relationships to other Topics

| Topic | Relationship |
| --- | --- |
| 03 | Stable Topic identity determines which evidence belongs in the same longitudinal state history. |
| 04 | Correct reference/response scope determines what was approved, revoked, answered, or changed. |
| 05 | Supplies extracted actions, commitments, decisions, deadlines, and conditions whose state evolves. |
| 07 | Retrieves missing evidence when current state cannot be resolved from available sources. |
| 08 | State evidence may come from document versions, tables, attachments, or screenshots. |
| 09 | Briefing must distinguish new developments from still-open state and avoid repeating superseded facts. |
| 10 | Evaluates current-state correctness, contradiction handling, evidence support, and uncertainty. |

## Key conceptual distinctions

- Mentioned event ≠ factual event.
- Planned ≠ completed.
- Asserted complete ≠ independently confirmed complete.
- Message timestamp ≠ event/effective time.
- Later message ≠ automatically superseding message.
- Contradiction ≠ supersession.
- Absence of new evidence ≠ completion.
- Correction creates a new assessment and lineage; it does not erase prior source records.

## High-value academic terminology

- event factuality prediction; factuality profiling;
- event modality; event certainty; event veridicality;
- negation detection; speculation/hedging detection;
- temporal information extraction; temporal relation extraction;
- event temporal ordering; temporal relation classification;
- TimeML / temporal graphs / temporal constraint reasoning;
- event status tracking; state tracking; dialogue state tracking (transfer only where semantics match);
- event evolution / event update / timeline extraction;
- contradiction detection; natural language inference (NLI);
- belief revision; truth maintenance systems (TMS); assumption-based truth maintenance;
- knowledge-base revision; temporal knowledge graphs;
- document/version supersession; revision tracking; change detection;
- provenance-aware state / event sourcing (engineering/background literature).

## Query families

- `"event factuality prediction" NLP`
- `event modality certainty negation speculation`
- `"temporal relation extraction" event ordering`
- `"event temporal ordering" document`
- `"event status tracking" text`
- `"belief revision" natural language evidence`
- `"truth maintenance" conflicting evidence`
- `contradiction supersession document revisions`
- `temporal knowledge graph event state update`
- `business email deadline change completion status`

## False friends / exclusions

- pure date extraction without event relation;
- Topic 05 action extraction alone;
- generic NLI benchmarks where the system is not maintaining a longitudinal state;
- latest-message-wins heuristics;
- workflow-engine state machines with no language/evidence uncertainty;
- update summarization (Topic 09), which consumes state rather than defines its truth semantics.

## Gap-evaluation guidance

Prioritize errors that can mark open work complete, resurrect superseded work, lose a changed deadline, or resolve contradictions without evidence. Prefer explicit state transitions with provenance over one opaque “current summary”. When the unresolved state is caused by missing evidence rather than reasoning limitations, hand off an evidence need to Topic 07.

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

## From Topic 05 — Action items, requests, commitments and decisions

*Completed 2026-09-16. 4 rounds, 48 papers, review accepted at faithfulness
0.93. Nine gaps left open, none downgraded.*

**Handed to Topic 06.** Whether an extracted commitment is later confirmed,
revoked, completed or contradicted. Topic 05 emits the **utterance-time**
semantic event — what was said, by whom, about what, with which deadline and
conditions — and explicitly does not decide whether it stays valid. Its
report states the boundary: Topic 05 should "emit utterance-time semantic
events for Topic 06 instead of deciding whether they later remain valid".

**What Topic 05 established.** Extraction quality depends jointly on act
classification and argument attachment; a correct act label with the wrong
owner or deadline is not a usable event. Context helps and also hurts:
the literature shows both gains and context-induced degradation, which is why
Topic 05 leaves the context window an open engineering question.

**What Topic 05 left open, and Topic 06 must not treat as settled:**

- *(ACADEMIC, HIGH)* Owner and assignee extraction is weakly evidenced,
  above all for implicit owners, group ownership and owners recoverable only
  from organisational context. An event arriving without a confident owner is
  the normal case, not an error.
- *(ACADEMIC, HIGH)* Deadline binding is unresolved: a date in a message is
  not necessarily that action's deadline.
- *(ACADEMIC, HIGH)* Attaching conditions, negation and modality to the right
  action when several occur together. A conditional commitment that Topic 06
  tracks as firm would be wrong from the start.

**Boundary.** Topic 06 owns state and revision over time. Topic 05 owns what
the event *is* at the moment it was uttered, and its open gaps travel with
the event.

Per-paper analyses:
[
 {
  "paper_id": "1804.06020",
  "title": "Improving Temporal Relation Extraction with a Globally Acquired Statistical Resource",
  "research_question": "Can large-scale corpus-derived prior knowledge about the temporal ordering of event types improve local and globally constrained temporal-relation extraction?",
  "key_findings": [
   "TemProb contains approximately 51,000 distinct verb semantic frames, 9.2 million verb-pair-relation entries, and up to about 80 million extracted temporal relations from the NYT corpus.",
   "TemProb's before/after probabilities behave as meaningful confidence estimates on TimeBank-Dense: increasing the probability threshold raises precision while reducing recall.",
   "On the converted EventCausality evaluation, using TemProb priors achieved 66.2% accuracy, an 11.5-point improvement over the majority T-Before baseline.",
   "Adding the full TemProb prior distribution as local classifier features improved F1 by 2.7 points for same-sentence relations and 6.5 points for adjacent-sentence relations relative to the original local features.",
   "Combining TemProb features and ILP regularization increased global TimeBank-Dense F1 from 46.2 to 52.1 and temporal-awareness F-score from 42.5 to 49.6, with the reported comparison significant at p<0.0005."
  ]
 },
 {
  "paper_id": "1805.06975",
  "title": "Tracking State Changes in Procedural Text: A Challenge Dataset and Models for Process Paragraph Comprehension",
  "research_question": "Can models reliably infer when entities are created, destroyed, or moved and where they are located across natural procedural paragraphs, and does global process modeling outperform approaches developed for shorter or synthetic reasoning tasks?",
  "key_findings": [
   "ProPara provides dense longitudinal annotations of entity existence and location over natural process descriptions, enabling evaluation of complete state trajectories rather than isolated sentence classification.",
   "ProGlobal substantially outperforms ProLocal and the earlier baselines on the aggregate state-tracking metrics, with reported macro scores of 45.08 for ProGlobal and 34.50 for ProLocal.",
   "The largest gap between global and local modeling appears on locating entities after changes: ProGlobal scores 35.9 on the location category versus 10.35 for ProLocal.",
   "About 30% of final locations are not explicitly stated in the sentence where the state change occurs, providing a structural reason that sentence-local extraction is insufficient for many examples.",
   "Human performance remains far above the evaluated models, with a reported macro score of 80.76 compared with 45.08 for ProGlobal, showing substantial remaining difficulty."
  ]
 },
 {
  "paper_id": "1909.00429",
  "title": "An Improved Neural Baseline for Temporal Relation Extraction",
  "research_question": "Can a comparatively standard neural architecture become a substantially stronger temporal-relation baseline when paired with higher-quality temporal annotations, contextual embeddings, temporal commonsense knowledge, and global consistency inference?",
  "key_findings": [
   "The best Concat+CSE variants improve over CogCompTime on MATRES by roughly ten absolute points in accuracy and F1, about five points in temporal-awareness score, and about eight points in the average of the three metrics.",
   "Adding the TemProb-based Common Sense Encoder improves the Concat model under every reported metric for both ELMo and BERT, with the paper reporting statistical significance for the CSE improvement.",
   "Direct concatenation of the two event-position hidden states is significantly better overall than the position-indicator approach across the embedding and metric comparisons.",
   "Contextualized ELMo and BERT representations significantly outperform conventional embeddings, while the difference between ELMo and BERT is not statistically significant in these experiments.",
   "The advantage generalizes to the separate TCR test set: Concat+CSE reaches a three-metric average of 76.4 with ELMo and 74.9 with BERT versus 66.8 for CogCompTime."
  ]
 },
 {
  "paper_id": "1909.05360",
  "title": "Joint Event and Temporal Relation Extraction with Shared Representations and Structured Prediction",
  "research_question": "Can event identification and temporal-relation extraction be learned jointly with shared representations and global structural constraints to reduce pipeline error propagation?",
  "key_findings": [
   "The structured joint model improves end-to-end temporal-relation F1 over the reported baselines by 10.0 points on TB-Dense and 6.8 points on MATRES, reaching 49.4 and 59.6 F1 respectively.",
   "The same structured model improves event-extraction F1 over the baselines by 3.5 points on TB-Dense and 2.6 points on MATRES.",
   "Sharing representations between event and relation tasks provides more benefit on heterogeneous TB-Dense events than on MATRES, where all annotated events are verbs and multi-task gains are smaller.",
   "The event-relation consistency constraint accounts for most of the measured structural-inference gain, adding 0.9 F1 on TB-Dense and 1.0 on MATRES, while the added transitivity constraint contributes no gain on TB-Dense and only 0.1 on MATRES.",
   "Severe class imbalance remains problematic: the neural model concentrates on dominant relations and fails to make any correct SIMULTANEOUS predictions in the class-weight experiment even when that class is weighted up to ten times."
  ]
 },
 {
  "paper_id": "2007.14864",
  "title": "How and Why is An Answer (Still) Correct? Maintaining Provenance in Dynamic Knowledge Graphs",
  "research_question": "Can the validity and derivational provenance of standing-query answers over large knowledge graphs be maintained efficiently as underlying facts are inserted or deleted, rather than recomputed from scratch?",
  "key_findings": [
   "Provenance polynomials retain the individual graph facts and alternative derivations responsible for each query answer, allowing the system to explain both why an answer exists and how it was derived.",
   "After a fact deletion, an answer can remain valid when at least one provenance monomial still evaluates nonzero, so alternative derivations act as explicit independently surviving evidence paths.",
   "Average update time was 0.119 seconds on YAGO2 and 1.252 seconds on DBpedia, and the authors report HUKA as roughly 4 to 48 times faster than the nearest compared baselines for update processing.",
   "Combining common subquery work into a global execution plan reduced the number of intermediate expressions by close to 70%.",
   "HUKA supports both insertion and deletion of graph facts and treats a factual update as a deletion followed by an insertion, enabling provenance to evolve with the underlying knowledge graph."
  ]
 },
 {
  "paper_id": "2011.03088",
  "title": "HoVer: A Dataset for Many-Hop Fact Extraction And Claim Verification",
  "research_question": "Can a large-scale fact-verification benchmark require models to retrieve evidence across as many as four documents and thereby expose weaknesses in shallow single-hop retrieval and verification methods?",
  "key_findings": [
   "HoVer contains 26,171 claims whose evidence may span as many as four English Wikipedia articles, creating a substantially longer evidence chain than common earlier fact-verification benchmarks.",
   "Five-worker claim labeling yielded Fleiss' kappa of 0.63, and 2,222 claims with a 2-2-1 vote split were discarded.",
   "The intended three-way distinction between Refuted and NotEnoughInfo proved ambiguous: an independent 100-claim validation matched the majority three-way label only 63% of the time, while the merged Supported versus Not-Supported labeling matched 90%.",
   "TF-IDF retrieval of the top 100 documents recovered all required supporting documents for about 80.02% of 2-hop claims, 39.18% of 3-hop claims, and 15.59% of 4-hop claims, demonstrating sharply increasing retrieval difficulty.",
   "With complete oracle evidence the BERT verifier reaches 81.2% accuracy, whereas a claim-only model reaches 63.7%, showing both a meaningful benefit from evidence and residual exploitable claim artifacts."
  ]
 },
 {
  "paper_id": "2103.08541",
  "title": "Get Your Vitamin C! Robust Fact Verification with Contrastive Evidence",
  "research_question": "Can fact-verification models be made more sensitive and robust to factual changes in evolving evidence by training on contrastive revisions where small textual edits alter a claim's truth status?",
  "key_findings": [
   "An ALBERT model using the full before-and-after sentences achieved 83.18 F1 and 91.97 AUC for factual-revision flagging, outperforming edit-distance, bag-of-words, and edited-span-only baselines.",
   "Contrastive training substantially increased sensitivity to changed evidence: the ALBERT-base FEVER-only model flipped its verdict on 55.53% of contrastive cases, whereas VitaminC plus FEVER training reached 85.89%, and the corresponding ALBERT-xlarge model reached 90.94%.",
   "Adding VitaminC training improved performance on adversarial evaluations while largely preserving in-domain FEVER or MNLI accuracy, indicating that revision-aware examples reduced reliance on static or lexical shortcuts.",
   "Distant token-level supervision derived from revision edits raised word-level rationale F1 from 37.33 to 47.36 and edit-prediction F1 from 31.23 to 59.11.",
   "For factually consistent generation, the BART claim generator received an 85.83 verifier score and the BART revision generator received 76.26, with manual evaluation additionally checking grammaticality and support."
  ]
 },
 {
  "paper_id": "2104.01146",
  "title": "An Empirical Characterization of Event Sourced Systems and Their Schema Evolution - Lessons from Industry",
  "research_question": "How are event-sourced systems used and defined in industry, how do practitioners evolve their event data structures, and what recurring engineering challenges arise?",
  "key_findings": [
   "Practitioners reported five major challenges: evolving event systems, a steep learning curve, insufficient technology support, rebuilding projections, and data privacy.",
   "The study identifies five event-schema evolution techniques used in practice: versioned events, weak schema, upcasting, in-place transformation, and copy-and-transform.",
   "No single schema-evolution technique is appropriate in every context; versioned events and weak schema are presented as comparatively simple starting points, upcasting as a way to retain event-store immutability, and copy-and-transform as an option when performance or maintainability motivates a more expensive transformation.",
   "Copy-and-transform preserves the original source events while creating new transformed event streams, allowing historical source events to remain immutable.",
   "Immutability was not universal in the 19 studied systems: eight never changed events, three permitted controlled cut-off changes backed by retained backups, and eight allowed event changes without indefinitely retained backups; the last group therefore did not preserve a complete audit trail."
  ]
 },
 {
  "paper_id": "2110.08222",
  "title": "DialFact: A Benchmark for Fact-Checking in Dialogue",
  "research_question": "Can dialogue fact-checking be benchmarked as a pipeline of verifiable-claim detection, evidence retrieval, and evidence-grounded claim verification, and can dialogue-adapted training improve over models developed for non-dialogue fact-checking?",
  "key_findings": [
   "Dialogue context materially improves evidence-document retrieval: test-set recall rises from 60.8 to 75.0 for the WikiAPI method and from 44.7 to 58.8 for the WoW-fine-tuned DPR method when context is added to the claim.",
   "The Aug-WoW verification model outperforms the evaluated baselines across oracle, Wiki-retrieved, and DPR-retrieved evidence settings; on the test set it reaches 69.2% accuracy and 69.0 macro F1 with oracle evidence.",
   "Evidence retrieval is a major bottleneck: Aug-WoW falls from 69.2% accuracy with oracle evidence to 51.6% with Wiki evidence and 51.5% with DPR evidence, with analogous degradation for other models.",
   "Verifiable-claim detection remains especially difficult for non-verifiable conversational content: the best reported Lexical+DNLI baseline has 82.8% overall accuracy but only 39.1 F1 for the Non-Verifiable class.",
   "Models frequently confuse Refuted and NEI claims and can be misled by lexical overlap instead of correctly reasoning over the semantics of claims and evidence."
  ]
 },
 {
  "paper_id": "2210.15067",
  "title": "arXivEdits: Understanding the Human Revision Process in Scientific Writing",
  "research_question": "How can revisions across successive versions of full scientific papers be aligned, decomposed into fine-grained edits, and automatically classified by the authors' revision intentions?",
  "key_findings": [
   "The corpus provides longitudinal full-document revision data for 751 papers and 1,790 versions, with manually annotated sentence alignment covering 13,008 sentence pairs.",
   "The neural sentence-alignment model trained on arXivEdits achieved 93.8 F1, supporting automated linkage of corresponding sentences across document versions.",
   "Span-alignment methods extracted finer-grained edits than latexdiff; QA-align with parse-based heuristics achieved 88.1 F1 on all revisions compared with 75.3 for latexdiff.",
   "A T5-large intention classifier achieved 79.3 accuracy and 78.9 weighted F1 in the fine-grained eight-class experimental setup, while the collapsed four-class setup reached 84.4 accuracy and 84.6 weighted F1 when trained directly on four classes.",
   "The annotated document-level alignments explicitly capture insertions, deletions, rephrasings, splits, merges, fusions, and unchanged copying across successive versions."
  ]
 },
 {
  "paper_id": "2406.00197",
  "title": "Re3: A Holistic Framework and Dataset for Modeling Collaborative Document Revision",
  "research_question": "How can document revisions, peer-review requests, and revision summaries be represented and annotated jointly so that collaborative revision behavior and NLP systems can be studied across edit granularity, action, intent, and cross-document relationships?",
  "key_findings": [
   "Re3 explicitly links a review request to the concrete edits that address it and allows one request to correspond to multiple edits, providing a direct representation of requested versus realized revision.",
   "The dataset contains 314 document-revision pairs and annotations at section, paragraph, sentence, and subsentence granularity, allowing revision history to be analyzed hierarchically rather than as a flat diff.",
   "Modify and Add are the dominant edit operations, and Fact/Evidence is the most common edit intent, showing that many revisions change substantive content rather than only surface form.",
   "More than half of explicit review suggestions are implemented, while 18.47% of implemented review requests are realized through multiple sentence edits, demonstrating that request-to-revision alignment is frequently one-to-many.",
   "Automatic intent classification remains imperfect: the best reported joint classification result reaches 0.70 accuracy and 0.69 macro F1, with Claim and Fact/Evidence among the difficult distinctions."
  ]
 },
 {
  "paper_id": "2406.19764",
  "title": "Belief Revision: The Adaptability of Large Language Models Reasoning",
  "research_question": "How reliably can language models decide whether a previously inferred conclusion should be updated or maintained when a new premise changes the conditions governing that conclusion?",
  "key_findings": [
   "Belief-R contains 1,912 basic two-premise cases and 1,744 three-premise revision cases, comprising 1,074 Belief Update and 670 Belief Maintain examples.",
   "Models that perform well on the initial basic inference still perform poorly on belief revision; most non-API models have near-zero Belief Update accuracy, and the larger open and commercial models reach only about 50% at best on the balanced BREU measure.",
   "The experiments reveal a trade-off between updating and maintaining prior conclusions, with models that improve on Belief Update often performing worse on Belief Maintain.",
   "Belief revision is harder in the modus-tollens subset, where the models show lower balanced revision performance and a stronger imbalance between updating and maintaining.",
   "Chain-of-thought prompting does not significantly improve average belief revision, and plan-and-solve prompting yields only about a one-percentage-point improvement in BREU overall."
  ]
 },
 {
  "paper_id": "2606.18037",
  "title": "ProvenanceGuard: Source-Aware Factuality Verification for MCP-Based LLM Agents",
  "research_question": "Can factuality verification for multi-source MCP agents explicitly preserve source ownership so that unsupported claims, contradictions, and claims supported by the wrong source are reliably blocked?",
  "key_findings": [
   "On the held-out set of 40 traces and 361 claims, ProvenanceGuard achieved 0.802 reject/block F1, 0.993 reject recall, and 0.858 source accuracy over source-eligible claims.",
   "Source-blind support baselines remained competitive on binary rejection, with MiniCheck reaching 0.783 F1, and the 0.019 F1 gap to ProvenanceGuard was not statistically significant; the distinctive measured capability was explicit claim-to-source attribution.",
   "On the harder multi-source benchmark, reject/block F1 remained 0.846 while source accuracy fell to 0.503 and source-plus-relation accuracy to 0.229, showing that exact provenance attribution becomes much harder among semantically similar candidate sources.",
   "All 50 deliberately injected source-attribution swaps in the controlled conflation probes were blocked and labeled as conflations, and no repaired output retained the deliberately wrong attribution.",
   "The repair loop made all 173 initially blocked full-trace answers pass reverification, but 144 resolutions used terminal fallback text, so verifier passage did not usually imply successful recovery of a rich substantive answer."
  ]
 },
 {
  "paper_id": "2608.20116",
  "title": "When Text and Numbers Disagree: Evidence Arbitration in Large Language Models",
  "research_question": "How do instruction-tuned language models arbitrate between conflicting textual, numerical, temporally recent, reliability-marked, and tool-generated evidence when exactly one source is correct?",
  "key_findings": [
   "Models exhibit model-specific modality priors even when textual and numerical evidence are designed to be equally reliable: Qwen models tend toward numerical evidence, while Llama and Mistral show stronger textual preferences and Gemma is more balanced.",
   "Evidence presentation order materially affects arbitration, with later evidence frequently exerting greater influence and textual evidence benefiting especially from being placed last.",
   "Temporal recency is a stronger and more consistently used arbitration cue than an explicit indication that one source is unreliable.",
   "Conflicting tool forecasts produce the strongest degradation among the tested conflict types, and some model configurations follow the tool despite the observed context being perfectly informative.",
   "Increasing model size does not monotonically improve conflict arbitration in the principal experiments; larger Qwen variants can still make systematic source-selection errors under conflict."
  ]
 },
 {
  "paper_id": "doi-10-1007-3-540-44503-x-20",
  "title": "Why and Where: A Characterization of Data Provenance",
  "research_question": "How can the provenance of query-produced data be formally characterized and computed in terms of both why an output exists and where its values originated, while remaining meaningful under query rewriting and view composition?",
  "key_findings": [
   "The paper distinguishes why-provenance, which identifies source data responsible for an output's existence, from where-provenance, which identifies source locations from which particular output values were obtained.",
   "Every well-formed query in the defined language has an equivalent normal form reachable through a strongly normalizing rewrite system.",
   "For a normal-form query and singular output value, the proposed Why procedure computes the same witness basis as the formal provenance definition.",
   "Although a query-dependent witness basis is not invariant under all equivalent formulations, its minimal witness basis is invariant for equivalent well-formed queries restricted to equality conditions, with stated extensions to some inequality subclasses.",
   "Why-provenance can be propagated through materialized views so that recursively tracing witnesses through views agrees with composing the views out of the query."
  ]
 },
 {
  "paper_id": "doi-10-1007-s10458-012-9202-0",
  "title": "Representing and monitoring social commitments using the event calculus",
  "research_question": "How can social commitments, their temporal conditions, and their changing lifecycle states be represented declaratively and monitored online as events occur?",
  "key_findings": [
   "The Event Calculus formalization gives an explicit lifecycle in which conditional commitments can be active and base-level commitments can be active, satisfied, canceled, or violated, with event-triggered operations moving commitments between states.",
   "Cancellation and violation are semantically distinct: cancellation results from an action, whereas violation results from failure to bring about or maintain a required temporal property.",
   "Reactive Event Calculus provides an executable semantics for updating commitment state incrementally as an event narrative grows, supporting online monitoring rather than only static verification.",
   "In the reported car-rental experiment with 15 contract clauses and 6000 events, total processing time was below five minutes and the longest single-event processing time was 294 ms.",
   "Increasing the number of contract clauses by factors of 5, 10, and 50 while holding 6000 events and 200 customers fixed did not produce a statistically significant change in total processing time in the reported experiment."
  ]
 },
 {
  "paper_id": "doi-10-1007-s10579-009-9089-9",
  "title": "FactBank: a corpus annotated with event factuality",
  "research_question": "How can event factuality be represented and reliably annotated as source-relative combinations of polarity and epistemic certainty in text?",
  "key_findings": [
   "FactBank contains 208 documents and 9,488 manually annotated events drawn from TimeBank and a subset of the AQUAINT TimeML corpus.",
   "The factuality representation combines positive, negative, or underspecified polarity with certain, probable, possible, or underspecified modality, thereby distinguishing facts, counterfacts, uncertainty, and non-commitment.",
   "Inter-annotator agreement was high for the annotation decomposition: Cohen's kappa was 0.88 for source-introducing predicates, 0.95 for source identification, and 0.81 for factuality-value assignment.",
   "The corpus explicitly represents factuality relative to relevant sources rather than treating factuality as a single source-independent truth value.",
   "The annotation deliberately excludes factuality changes that require multiple sentences, even though the authors note that an initially uncommitted event may later be presented as a fact."
  ]
 },
 {
  "paper_id": "doi-10-1007-s11390-024-2655-1",
  "title": "Document-Level Event Factuality Identification via Reinforced Semantic Learning Network",
  "research_question": "Can document-level event factuality be identified end to end by jointly encoding event and document semantics while learning to select the sentences and tokens most relevant to the target event?",
  "key_findings": [
   "The paper explicitly observes that sentence-level factualities concerning an event may differ within a document while defining the document-level factuality as a single value.",
   "On ExDLEF, RSLN reports macro/micro F1 of 67.42/77.48 for English and 75.74/78.29 for Chinese, outperforming the reported comparison systems.",
   "Ablation results identify the event encoder and topic-context encoder as two of the most important components: removing them produces substantial macro- and micro-F1 losses in both languages.",
   "Sentence selection has a larger measured effect than token selection: removing SPNet reduces macro-F1 by 4.07 points in English and 4.64 in Chinese, compared with 1.35 and 0.85 points when TPNet is removed.",
   "ExDLEF contains 5,030 English instances and 5,150 Chinese instances across Uu, CT-, PS-, PS+, and CT+ factuality categories."
  ]
 },
 {
  "paper_id": "doi-10-1016-0004-3702-86-90080-9",
  "title": "An assumption-based TMS",
  "research_question": "How can a truth-maintenance system represent and reason over many mutually incompatible assumption contexts simultaneously while preserving derivational support and avoiding repeated backtracking, context switching, and retraction?",
  "key_findings": [
   "An ATMS label records minimal consistent assumption environments supporting a datum, thereby preserving explicit provenance for which combinations of assumptions make each conclusion valid.",
   "Contradictory assumption combinations are stored as nogoods, and conclusions depending on those combinations are invalidated without forcing unrelated conclusions or alternative contexts to disappear.",
   "Mutually contradictory candidate solutions can coexist in separate consistent environments, allowing reasoning to continue without selecting a single global current belief state.",
   "Context membership can be determined from assumption-set inclusion, making repeated context switching unnecessary for applications that need to explore multiple alternatives.",
   "Directly retracting justifications is described as correct but very inefficient because it can trigger recursive recomputation of labels and previously recorded nogoods; representing defeasibility through assumptions is preferred."
  ]
 },
 {
  "paper_id": "doi-10-1016-0020-0255-94-90059-0",
  "title": "Resolution of time concepts in temporal databases",
  "research_question": "Which temporal dimensions and validity concepts are necessary to preserve database history precisely and losslessly when information may be entered retroactively, proactively, corrected, or recorded after a delay?",
  "key_findings": [
   "Three distinct temporal concepts are required for the paper's account of precise and lossless preservation of temporal database information.",
   "Valid time and transaction time alone cannot correctly represent retroactive and proactive updates; event time is additionally required.",
   "The combination of event time, valid time, and transaction time is presented as adequate for preserving past states generated by retroactive updates, proactive updates, error corrections, and delayed updates.",
   "Temporal validity and interpretation-based validity are introduced to clarify the semantics of different time concepts and to define an object's evolution along the valid-time dimension.",
   "The paper sketches a relational-data-model implementation for retaining object history rather than treating the formal distinctions only as abstract semantics."
  ]
 },
 {
  "paper_id": "doi-10-1016-j-artint-2003-08-003",
  "title": "Weakening conflicting information for iterated revision and knowledge integration",
  "research_question": "Can conflicts in prioritized knowledge bases be resolved with less information loss by weakening conflicting formulas rather than deleting them, while retaining practical computational behavior and desirable revision semantics?",
  "key_findings": [
   "DMA resolves inconsistency by weakening formulas involved in conflicts through disjunction rather than simply discarding all conflicting formulas at the affected priority level.",
   "DMA can preserve strictly more information than Maxi-Adjustment because information lost by removal can survive in weaker disjunctive form.",
   "DMA inference is shown to be equivalent to lexicographical inference, providing a compiled consistent base without explicitly enumerating the potentially exponential set of lexicographically preferred subbases.",
   "In the eight reported DIMACS examples, standard Adjustment retained no clauses from the inconsistent second stratum, while DMA retained or generated at least as much information as Maxi-Adjustment and substantially more on several instances.",
   "Whole-DMA was dramatically faster than kernel-computing MA, DMA, and IDMA on the eight reported examples, taking about 0.1 seconds per instance while some kernel-based runs required hundreds of seconds."
  ]
 },
 {
  "paper_id": "doi-10-1016-j-ipm-2021-102836",
  "title": "End-to-end event factuality prediction using directional labeled graph recurrent network",
  "research_question": "Can event anchors and their factuality scores be predicted jointly from plain sentences while improving factuality estimation through directional and labeled syntactic graph information?",
  "key_findings": [
   "Across the four benchmarks, DLGRN is reported to reduce MAE by an average of 17.12% and increase Pearson correlation by 5.40% relative to the strongest baseline.",
   "DLGRN achieved the best factuality-induction values in the reported comparison on all four datasets, including MAE/correlation pairs of 0.240/0.912 on FactBank, 0.279/0.516 on Meantime, 0.346/0.863 on UW, and 0.722/0.912 on UDS-IH2.",
   "The UW ablation shows labeled syntactic information as the most consequential tested graph component: removing it changes F1 from 0.91 to 0.89, MCC from 0.883 to 0.745, MAE from 0.346 to 0.422, and correlation from 0.863 to 0.788.",
   "Removing multi-task learning and reverting toward a pipeline setup degrades both event-anchor detection and factuality induction, supporting shared learning between the two subtasks.",
   "DLGRN outperforms the compared GCN and GAT-LSTM systems across sentence-length buckets, with larger correlation gaps in the longest buckets."
  ]
 },
 {
  "paper_id": "doi-10-1016-j-ipm-2026-104709",
  "title": "HeterMV: Multi-view reasoning over source-aware heterogeneous evidence graph for multi-source fact verification",
  "research_question": "Can explicit source-aware heterogeneous graph modeling and multi-view evidence reasoning improve multi-source fact verification while suppressing irrelevant, redundant, or inconsistent auxiliary evidence?",
  "key_findings": [
   "The framework explicitly preserves source roles by representing core evidence, context, and reference documents as different node types and by using source-specific directed relations rather than homogenizing all evidence.",
   "Four decoupled reasoning views are used to separate evidence perspectives, while view-conditioned prompt tuning aligns each perspective with the claim and cross-view contrastive learning is intended to reinforce supportive signals and suppress noisy ones.",
   "On Check-COVID with 1,504 claims, HeterMV reports Micro-F1 improvements of 3.06 percentage points in the gold setting and 3.27 percentage points under BM25 retrieval over the compared state-of-the-art baselines.",
   "On FEVEROUS-S with 29,890 claims, HeterMV reports Micro-F1 improvements of 1.72 percentage points in the gold setting and 1.41 percentage points in the corresponding BM25-retrieval setting.",
   "The accessible article preview reports that ablation studies validate contributions from the framework's major components and that the evaluation also includes hyperparameter-sensitivity and case analyses."
  ]
 },
 {
  "paper_id": "doi-10-1016-j-knosys-2016-07-032",
  "title": "Cross-document event ordering through temporal, lexical and distributional knowledge",
  "research_question": "Can temporal compatibility, lexical-semantic knowledge, and distributional-semantic knowledge be combined to improve cross-document event coreference and chronological timeline construction from multiple texts?",
  "key_findings": [
   "Combining temporal, lexical-semantic, and distributional-semantic knowledge improved the cross-document event-ordering results over previously evaluated systems, with gains reported as high as eight F1 points.",
   "The best configuration continued to be the combination of temporal, lexical, and distributional semantics when manual entity-coreference annotations were substituted for automatic entity coreference.",
   "With manual MEANTIME entity coreference, the combined configuration reached micro-F1 30.09, precision 25.37, and recall 36.98; relative to the best automatic-entity-coreference setup, the paper reports gains of 3.5 F1 points, 1.7 precision points, and 6.61 recall points.",
   "Entity-coreference quality is an important upstream bottleneck because correcting it manually particularly increases event recall in the resulting timelines.",
   "Nominal event mentions such as deverbal nouns remain difficult to match with verbal mentions, creating cross-document event-coreference errors."
  ]
 },
 {
  "paper_id": "doi-10-1017-cbo9780511526664-007",
  "title": "On the difference between updating a knowledge base and revising it",
  "research_question": "How should knowledge-base update for a changing world be distinguished from revision prompted by new information about a static world, and what does that distinction imply for rationality postulates governing belief change?",
  "key_findings": [
   "Knowledge-base update and revision are fundamentally different operations: update concerns a world that has changed, whereas revision concerns new information about a world treated as static.",
   "A single set of rationality postulates is not adequate for every knowledge-base modification application.",
   "The AGM postulates developed for belief revision require substantial modification when the intended operation is update.",
   "Ordinary database changes and state changes caused by a robot's actions are examples of update because they alter the represented world rather than merely correcting beliefs about an unchanged world."
  ]
 },
 {
  "paper_id": "doi-10-1023-a-1010318403544",
  "title": "The Problem of Retraction in Critical Discussion",
  "research_question": "What kind of dialogue model can permit retractions when they are reasonable or required while constraining or sanctioning retractions that would disrupt an orderly critical discussion?",
  "key_findings": [
   "Retraction changes a participant's current commitments rather than erasing the historical fact that an earlier utterance occurred, so adequate scorekeeping alone does not remove the problem caused by changing commitments on which another participant relied.",
   "A successful elementary critical discussion necessarily ends with at least one participant retracting a commitment, either the proponent's thesis or the opponent's doubt.",
   "Retraction rules should specify both which retractions are permissible in a given dialogical state and what consequences follow, including possible secondary retractions.",
   "Appropriate retraction rules depend on both the type of dialogue and the type of commitment, rather than being uniform across all conversations.",
   "Assertions and concessions carry different obligations, and a statement can in principle be retracted as an assertion while remaining available as a concession."
  ]
 },
 {
  "paper_id": "doi-10-1093-jos-ffn013",
  "title": "Agreement, Disputes and Commitments in Dialogue",
  "research_question": "How can dialogue semantics represent agreement, disagreement, correction, and changing commitments in a logically consistent way while accounting for implicit agreement and preservation of undisputed prior content?",
  "key_findings": [
   "Agreement can be defined as shared entailments of the dialogue participants' public commitments, including commitments introduced by rhetorical relations, which permits logically explicit treatment of implicit agreement.",
   "Keeping each participant's commitments in a separate information structure allows participants to hold mutually inconsistent positions while the dialogue representation itself remains interpretable rather than collapsing into inconsistency.",
   "When a speaker accepts a correction, the update should remove commitments that are disavowed while preserving parts of earlier contributions that were not denied.",
   "A correction can target a rhetorical relation rather than all of the underlying propositional content, so disagreement does not imply that every proposition in the corrected contribution is rejected.",
   "When a correction is itself corrected, the Denying Corrections principle normally restores the relevant earlier, undenied commitment structure and makes prior material available again, providing a formal account of reopening a previously disputed commitment."
  ]
 },
 {
  "paper_id": "doi-10-1145-1082473-1082754",
  "title": "Layered message semantics using social commitments",
  "research_question": "How can message semantics in open multiagent systems be grounded in publicly observable social commitments and conversational context rather than relying primarily on unverifiable private mental states?",
  "key_findings": [
   "The proposed semantics decomposes message interpretation into four cumulative levels: compositional structure, conversational use, commitment state, and joint activity.",
   "Social commitments provide publicly represented states including inactive, accepted or active, fulfilled, violated, and cancelled states, with adoption, fulfillment, violation, and discharge as relevant transitions.",
   "Conversational meaning depends on the temporal and sequential context of shared utterances, including whether a proposal remains available for a reply.",
   "At the commitment-state level, the same structural message can receive a more specific interpretation according to the current state of the referenced commitment, such as an offer withdrawal when an active commitment is proposed for discharge by the original offering agent.",
   "At the joint-activity level, message meaning is related to role-specific actions and their dependencies, as illustrated by bid production, bid evaluation, and contract performance in a contract-net activity."
  ]
 },
 {
  "paper_id": "doi-10-1162-tacl-a-00182",
  "title": "Dense Event Ordering with a Multi-Pass Architecture",
  "research_question": "How should temporal-ordering systems and evaluation change when they must label densely connected event graphs rather than only a sparse set of preselected event pairs?",
  "key_findings": [
   "TimeBank-Dense contains 12,715 labeled temporal relations over 36 TimeBank newspaper articles and produces strongly connected local event-time graphs by requiring annotation of all relevant pairs within the same or neighboring sentences plus document-time links.",
   "CAEVO achieves 50.7 F1 on the dense test setting, a 14% relative improvement over the retrained top TempEval-3 systems used for comparison.",
   "Global transitive inference is a major contributor: adding transitivity raises the ablated CAEVO configuration from 32.1 to 39.8 F1, and the authors estimate that transitive inference alone contributes about ten percent performance improvement.",
   "Edges produced through transitive inference have higher precision than edges directly classified by sieves, approximately 54.4-54.5% versus 49.8%.",
   "Time-time relations constitute only 2.6% of the evaluated edges, yet removing the time-time sieve reduces overall performance by almost five percent because those relations affect other decisions through transitive closure."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-2021-acl-long-122",
  "title": "Factuality Assessment as Modal Dependency Parsing",
  "research_question": "Can factuality assessment be formulated as modal dependency parsing that jointly identifies events and information sources, links them hierarchically, and predicts the degree of certainty each source asserts toward each event?",
  "key_findings": [
   "The resulting corpus contains 353 documents, 24,016 events, and 2,938 conceivers; crowd-worker versus expert agreement is 78.6% for unlabeled attachment and 72.1% for labeled attachment.",
   "Joint learning does not materially improve event extraction: test F1 is 90.8 for the joint model versus 90.9 for the pipeline.",
   "Joint learning significantly improves test conceiver extraction from 67.5 F1 to 70.4 F1.",
   "With gold mentions, the pipeline has slightly higher test labeled attachment performance, 80.6 versus 80.1 for the joint model.",
   "With automatically extracted mentions, the joint model significantly improves test labeled attachment from 67.5 to 69.0, indicating reduced pipeline error propagation."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-2021-emnlp-main-815",
  "title": "Utilizing Relative Event Time to Enhance Event-Event Temporal Relation Extraction",
  "research_question": "Can latent relative event times learned from temporal-relation supervision improve event-event temporal relation extraction when explicit event-time expressions are sparse?",
  "key_findings": [
   "The Stack-Propagation model reaches precision 78.4, recall 85.2, and F1 81.7 on MATRES, compared with F1 80.2 for the vanilla RoBERTa classifier; the paper reports p<0.05 for the comparison.",
   "The proposed model slightly exceeds the reported 81.6 F1 of the self-training baseline while not using that baseline's additional annotated and raw training resources.",
   "Relative-time prediction alone in the multi-task configuration improves F1 from 80.2 to 80.6, while explicitly propagating predicted times into classification raises F1 further to 81.7.",
   "Deriving relations by directly comparing predicted timestamps yields the highest recall, 86.8, but only F1 80.7 because this strategy cannot adequately handle VAGUE relations.",
   "Predicted relative-time differences correlate with BEFORE and AFTER decisions, while VAGUE and EQUAL pairs tend to have relative-time differences near zero."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-2023-findings-acl-44",
  "title": "Towards Generative Event Factuality Prediction",
  "research_question": "Can an end-to-end generative model predict source-relative event factuality, including factuality holders, target events, and factuality values, and can output design and multi-task learning improve that prediction?",
  "key_findings": [
   "Event factuality is modeled as the factuality presentation or judgment attributed to an author or other source, rather than as direct determination of objective real-world truth.",
   "Text normalization increased the source-and-target FactBank baseline exact-match triplet F1 from 0.472 to 0.512, with much of the improvement attributed to morphology and orthography corrections.",
   "Multi-task learning with the author-only FactBank projection substantially improved source-and-target prediction, with the FBST plus FBAO* configuration reaching an exact-match triplet F1 of 0.684 compared with 0.535 for the reported Table 4 baseline.",
   "For author-only FactBank prediction, the multi-task FBAO* plus FBST configuration achieved exact-match F1 of 0.897, compared with 0.866 for the basic FBAO configuration.",
   "The structure of generated output materially affects results; in the author-only exact-match evaluation, inline annotation generation performed worse than tuple or triplet generation."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-d18-1155",
  "title": "Temporal Information Extraction by Predicting Relative Time-lines",
  "research_question": "Can temporal information be extracted more efficiently and consistently by directly predicting relative event time-lines instead of first predicting pairwise temporal relations?",
  "key_findings": [
   "Direct relative time-line prediction can avoid pairwise temporal-relation extraction while producing temporally consistent outputs with linear prediction complexity in the number of entities.",
   "On the TE3 evaluation split, contextual C-TLM with the regular time-line loss achieved F=56.1, exceeding all reported TL2RTL variants, whose best F-score was 52.8.",
   "On the smaller TimeBank-Dense-derived split, indirect TL2RTL performed better than C-TLM, with the best TL2RTL result reaching F=62.3 while the best C-TLM result was F=58.4.",
   "The regular time-line loss was the most robust of the tested losses and was also cheaper and more directly interpretable than losses requiring scores for every relation type.",
   "The contextual direct model appears better than TL2RTL at correctly positioning temporally related entities that are farther apart in the text, consistent with reduced dependence on locally pruned pairwise TLink extraction."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-p19-1412",
  "title": "Do You Know That Florence Is Packed with Visitors? Evaluating State-of-the-art Models of Speaker Commitment",
  "research_question": "How well do state-of-the-art speaker-commitment models generalize to naturally occurring discourse, and which linguistic constructions systematically explain their errors?",
  "key_findings": [
   "The linguistically informed rule-based model outperforms the evaluated biLSTM models on the full CommitmentBank, but all systems perform substantially worse there than on their original reference datasets.",
   "Pearson correlation on the full set is 0.41 for the rule-based model versus 0.24, 0.09, and 0.23 for the linear, tree, and hybrid biLSTMs; on the restricted set the corresponding values are 0.50, 0.31, 0.13, and 0.33.",
   "The rule-based model captures negation relatively well with r=0.45 but performs poorly on modal and question environments, while the hybrid model is more consistent across negation, modality, and questions; both fail on conditionals.",
   "Both models have essentially no useful correlation on neg-raising examples, with r=0.04 for the rule-based model and -0.07 for the hybrid model.",
   "In the three-way classification analysis, neither system reliably recognizes the no-commitment class: its F1 is 0 for the rule-based model and 0.11 for the hybrid model."
  ]
 },
 {
  "paper_id": "manual-2362cbe877",
  "title": "ProPara-CRTS: Canonical Referent Tracking for Reliable Evaluation of Entity State Tracking in Process Narratives",
  "research_question": "Can a canonical referent-tracking representation and targeted reannotation make ProPara a more reliable benchmark for longitudinal entity-state tracking while improving model training and evaluation without changing model architectures?",
  "key_findings": [
   "The CRTS representation separates surface mentions from immutable underlying referents and requires an explicit state for each referent at each process step, directly reducing ambiguity in longitudinal state chains.",
   "The reannotation identified 789 errors, with incomplete state accounting accounting for 357 cases and referent-uniqueness problems for 311, showing that missing transitions and referential ambiguity were major sources of label noise.",
   "On a 100-paragraph dual-annotation sample, state-label agreement reached Cohen's kappa of 0.72 and location agreement reached pairwise F1 of 0.56, indicating meaningful but nontrivial residual annotation difficulty.",
   "Across the main model comparisons, CRTS generally increased sentence-level or document-level F1, including improvements for fine-tuned Llama 3.1, MeeT, and CGLI.",
   "The paper's broad statement that CRTS improves F1 in all settings except GPT-4o-mini sentence-level evaluation is not fully consistent with Table 2, where GPT-4o direct prompting has document-level F1 of 58.8 on CRTS versus 59.6 on original ProPara."
  ]
 },
 {
  "paper_id": "manual-b3703967d3",
  "title": "Joint Inference for Event Timeline Construction",
  "research_question": "Can an interval-based globally constrained model that jointly reasons over event-time associations, event-event temporal relations, and event coreference construct more accurate and coherent event timelines than independent local classifiers?",
  "key_findings": [
   "Global inference achieved overall F1 46.01 versus 42.13 for the local classifiers, a 9.2% relative improvement that was significant at p<0.01.",
   "Using gold event coreference with global inference raised overall F1 to 52.47, about 14% relatively above global inference without coreference and significantly above the compared systems.",
   "Automatically learned event coreference produced overall F1 46.42, but its improvement over global inference without coreference was not statistically significant, showing that the benefit depends strongly on coreference quality.",
   "The interval-based ILP averaged about 21 seconds per article, whereas the corresponding time-point formulation did not finish within five hours before being terminated.",
   "The evaluation corpus contains 232 intervals and 324 event mentions; after logical saturation it contains 324 event-time associations and 5,940 annotated or inferred event-event temporal relations."
  ]
 },
 {
  "paper_id": "manual-d574dff39d",
  "title": "Email Task Management: An Iterative Relational Learning Approach",
  "research_question": "Can email task management be improved by jointly and iteratively learning semantic parent-child relations between messages and message-level speech acts so that each prediction supplies relational evidence for the other?",
  "key_findings": [
   "Structured email information and clustering refinements substantially improve task identification in the e-commerce corpus, where reported F1 rises from 0.15 for plain cosine clustering to 0.82 for the strongest reported configuration.",
   "Free-text work email is harder and less cleanly partitioned into tasks than transaction email; the authors note that task boundaries in free text are fuzzy and may be disputed even by human annotators.",
   "Adding neighboring-message speech acts as relational features yields statistically significant Kappa improvements for the Request and Commit speech acts and overall improvements for several speech-act classifiers.",
   "Using speech-act information to identify message links achieves precision 0.91, recall 0.80, and F1 0.85 in the authors' potential-improvement experiment, improving precision relative to similarity-only relation identification.",
   "In the final cross-user iterative experiment, relation identification starts at precision, recall, and F1 of 0.95 and after the first iteration reaches precision 1.0, recall 0.95, and F1 0.98; speech-act performance also improves for most acts except Amend."
  ]
 },
 {
  "paper_id": "manual-eef7a0219f",
  "title": "More than Classification: A Unified Framework for Event Temporal Relation Extraction",
  "research_question": "Can event temporal relation extraction be improved and made more transferable by representing relation labels as logical constraints over event start and end points rather than as independent one-hot classes?",
  "key_findings": [
   "The unified endpoint framework consistently improves over the enhanced direct-classification baseline and reaches 68.1 micro-F1 on TB-Dense and 82.6 on MATRES with RoBERTa-Large, reported as 0.3 F1 above the previous state of the art on both benchmarks.",
   "Explicit logical treatment of the Vague relation substantially reduces confusion with Vague: the number of Vague-associated errors falls by 95 on TB-Dense and 22 on MATRES, although non-Vague errors increase slightly.",
   "The unified representation is more data-efficient in low-resource TB-Dense experiments, averaging gains of 2.9 micro-F1 and 1.8 macro-F1 over the baseline across training subsets from 1% to 30%.",
   "When trained on TB-Dense and evaluated under MATRES relation definitions, the unified model obtains 70.4 micro-F1 versus 63.1 and 64.3 for two baseline label-mapping strategies.",
   "Gains occur with both BERT-Base and RoBERTa-Large, suggesting that the endpoint decomposition contributes beyond the choice of text encoder."
  ]
 }
]

Open gaps carried over from round 3 (the corpus above
includes the papers of every round so far):
- gap-1 [ACADEMIC, HIGH]: No admitted paper directly evaluates longitudinal state tracking across workplace messages in which one work item moves among requested, proposed, planned, approved, completed, revoked, superseded, disputed, conditional, and unresolved states while retaining historical assessments.
    suggested query: workplace email enterprise chat longitudinal work item lifecycle state tracking requested planned approved completed revoked superseded disputed unresolved
    searched in rounds: [1, 2, 3] (still open)
- gap-2 [ACADEMIC, HIGH]: The corpus provides formal treatments of correction, retraction, persistence, and reopening, but does not establish a natural-language method evaluated across successive operational communications for distinguishing supersession, correction, supplementation, contradiction, reopening, and unresolved conflict.
    suggested query: natural language dialogue revision relation classification supersession correction supplementation contradiction reopening unresolved conflict longitudinal
    searched in rounds: [1, 2, 3] (still open)
- gap-3 [ACADEMIC, HIGH]: No admitted paper jointly evaluates source-relative factuality, temporal ordering, lifecycle state, contradiction, and provenance as one longitudinal model; the papers validate separate components and their combination remains untested.
    suggested query: "event factuality" temporal relation contradiction provenance lifecycle longitudinal joint model
    searched in rounds: [1, 2, 3] (still open)
- gap-4 [ACADEMIC, HIGH]: Direct evidence for workplace email, Teams-like dialogue, or comparable operational communication is absent; the empirical NLP evidence is predominantly news-derived, while the commitment and belief-revision papers use formal, modeled, argumentative-dialogue, or adjacent-domain settings.
    suggested query: workplace email enterprise chat operational communication task state tracking revision factuality temporal commitment
    searched in rounds: [1, 2, 3] (still open)
- gap-5 [ACADEMIC, HIGH]: The admitted factuality literature models textual source commitment, and the fact-verification literature models corroborating evidence, but no admitted paper establishes how to distinguish an author's assertion that work is complete from independent confirmation or stronger evidential verification of completion in longitudinal operational communication.
    suggested query: dialogue event factuality evidentiality source attribution claimed completion independent confirmation corroboration longitudinal
    searched in rounds: [1, 2, 3] (still open)
- gap-6 [ENGINEERING, HIGH]: Evaluation is still needed on adversarial longitudinal sequences such as plan-to-cancel, approve-to-revoke, deadline changes, contradictory same-time updates, out-of-order ingestion, stale messages arriving late, and completion claims later corrected.
- gap-7 [ENGINEERING, HIGH]: The combined representation of message time, event/effective time, deadline or constraint time, and observed collection/version time has not been benchmarked for this product's state-resolution tasks; the temporal-database paper provides a related three-time formal account rather than such an evaluation.
- gap-8 [ENGINEERING, HIGH]: The corpus does not evaluate a provenance-preserving implementation for this state-resolution task that stores immutable source observations and successive assessments while exposing a separately derived current-state view.

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
