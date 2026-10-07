# Topic 10 current status

## Academic research

- Rounds 1–4: complete. Stopped on `round_cap_reached`, the configured
  four-round cap, on 2026-09-17.
- Corpus: 64 papers admitted and read, none written off, **64 distinct** — a
  duplicate-title scan found no study recorded twice.
- New papers per round were 17, 20, 14, 13. Every round contributed and the
  loop was never stopped by `no_new_papers`.
- **Independent review accepted every round at the first attempt** —
  faithfulness 0.96, 0.94, 0.94, 0.94. Only Topic 06 has also managed this.
- Report:
  `msgloom-topic-10-evidence-and-reliability-evaluation-research-report.md`.

**Reaching the round cap is a stopping condition, not evidence.** All seven
gaps remain open and none was downgraded.

## Retained gaps

Academic, and not closed by four rounds of searching:

- **gap-1 (HIGH)** No study validates one end-to-end evaluation scheme that
  jointly measures claim correctness, evidence attribution, completeness and
  calibration. Component metrics exist; the combination does not.
- **gap-4 (HIGH)** No general evidence-completeness method handles compound
  claims, partial support and omission together.
- **gap-5 (HIGH)** Report-level omission has benchmark coverage, but omission
  detection for this product's reporting unit is not established.
- **gap-8 (MEDIUM)** Calibration under continuing temporal or distributional
  change remains open for non-stationary free-form communication.

Engineering, and deliberately not literature-search targets:

- **gap-2 (HIGH)** No direct evaluation on private workplace email or
  Teams-style communication with realistic conditions.
- **gap-6 (HIGH)** A target-domain human-review protocol: representative or
  risk-stratified sampling, adjudication, and agreement measurement.
- **gap-7 (MEDIUM)** Evaluator-optimisation effects, rating indeterminacy and
  abstention sensitivity are demonstrated but not controlled for here.

## Remaining deferred / handed-off work

**Topic 10 hands nothing to another topic.** It is the terminal node of the
programme's handoff graph: it receives evaluation questions from Topics 03,
04, 05, 06 and 08 and owns the methodology for answering them. Its own gaps
are the project's to close, not another topic's.

- Production-domain representativeness: deferred until suitable authorized
  domain data exists; this is gap-2 and it is the programme's most widely
  shared gap.
- No production architecture or evaluation harness has been approved by
  Topic 10 research.

## Inherited handoffs that Topic 10 answered

Topics 03, 04 and 05 handed over their open ENGINEERING gaps as evaluation
questions, and Topics 06 and 08 did the same at closure. Topic 10's corpus
addresses the *methodology* — attribution, claim decomposition, calibration,
selective prediction, omission detection — while each sending topic keeps
ownership of what its own quantities mean.

The boundary held in both directions. Topic 10 did not redefine what a false
obligation, a supersession or a grounded extraction is; those remain with
Topics 05, 06 and 08. What it establishes is how to measure any of them, and
its gap-1 says plainly that measuring them *together* is not established.

**Topic 08's handoff also carried a methodological warning**, recorded here
because it bears directly on Topic 10's own subject: Topic 08 round 2 was
rejected for citing one study twice — under a DOI and under a bare `manual-`
identifier — as independent corroboration. Structural integrity checks passed;
only the reader caught it. Evidence counting by record rather than by distinct
study is a live failure mode for any evaluation this topic informs.

## Run record

Driven by the ChatGPT orchestrator, `chat` profile, 18 active steps per round,
four gate types. Per-step reasoning effort: `max` for admission, per-paper
analysis, synthesis and review; `extended` for terminology, search, report
writing and gap classification.

Round durations, first send to last: 83.8, 94.9, 129.3, 89.2 minutes.

**Topic 10 ran in parallel with Topics 07 and 09 throughout** — the
programme's first three-way concurrency. One shard was lost to a socket
timeout in round 2 and re-dispatched; the ledger entry stays at `failed` for
that reason. The cause was this host's wireless link, not ChatGPT: the other
two topics kept sending throughout, and the host's own network monitor
reported an interface down and another demoted at the time.

Worker conversations were archived locally and deleted from the account.
