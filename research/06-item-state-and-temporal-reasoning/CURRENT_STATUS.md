# Topic 06 current status

## Academic research

- Rounds 1–4: complete. Stopped on `round_cap_reached`, the configured
  four-round cap, on 2026-09-17.
- Corpus: 38 papers admitted and read, none written off, **38 distinct** — a
  duplicate-title scan found no study recorded twice, unlike Topics 04 and 08.
- New papers per round were 13, 9, 9, 7, so every round contributed and the
  loop was never stopped by `no_new_papers`. The decline is itself a finding:
  the searches narrowed and fewer papers qualified, which is why the academic
  gaps below could not be closed.
- **Independent review accepted every round at the first attempt** —
  faithfulness 0.95, 0.95, 0.94, 0.93 — which no earlier Topic managed.
  Topics 03, 04 and 05 each had at least one round rejected. This is the first
  Topic to run start-to-finish with the synthesis prompt that names what the
  reviewer rejects for.
- Report:
  `msgloom-topic-06-item-state-and-temporal-reasoning-research-report.md`.

**Reaching the round cap is a stopping condition, not evidence.** All eight
gaps remain open and none was downgraded.

## Retained gaps

Academic, and not closed by four rounds of searching:

- **G1 (HIGH)** No direct evaluation of multi-state work-item lifecycle
  tracking across successive workplace messages while preserving historical
  assessments.
- **G2 (HIGH)** No empirical operational-message classifier covering
  supersession, correction, supplementation, contradiction, reopening and
  unresolved conflict as one relation inventory.
- **G3 (HIGH)** No joint model evaluation combining factuality, temporal
  ordering, lifecycle state, contradiction and provenance. Component success
  does not establish integrated correctness.
- **G4 (HIGH)** Direct target-task evidence for workplace email or
  Teams-like operational communication remains absent; transfer evidence
  cannot establish production-domain performance.
- **G5 (HIGH)** Nothing distinguishes a *claimed* completion from an
  independently corroborated one. A false "completed" could hide work that
  still requires action.

Engineering, and deliberately not literature-search targets:

- **G6 (HIGH)** An end-to-end adversarial longitudinal evaluation suite.
- **G7 (HIGH)** A benchmark combining message, effective, deadline and
  collection/version time.
- **G8 (HIGH)** A provenance-preserving implementation with immutable
  observations, successive assessments and a derived current-state view.

## Remaining deferred / handed-off work

- Production-domain representativeness: deferred until suitable authorized
  domain data exists; not a current blocker.
- An unresolved state becoming an explicit missing-evidence requirement:
  Topic 07. Named directly in Topic 06's report.
- State evidence that lives in document versions, tables, attachments or
  screenshots: Topic 08.
- Distinguishing a new development from a restatement, and not repeating
  superseded facts: Topic 09.
- G6–G8 as evaluation methodology, plus G5 as a calibration and abstention
  question: Topic 10, which owns generic attribution and calibration while
  Topic 06 keeps ownership of what a state or a corroborated completion means.
- No production architecture has been approved by Topic 06 research.

Each handoff is recorded in the receiving topic's `INHERITED_HANDOFFS.md`,
and each entry states what it rests on. Only the Topic 07 handoff is named by
number in the report; the other three rest on the report's substance plus the
programme's ownership map, which is the same basis Topic 05's closure used.

**The Topic 08 handoff arrived after Topic 08 had finished.** The two Topics
ran in parallel, so Topic 08's four rounds never saw it. The folder is
complete; the rounds were not informed by it. If its substance matters, the
remedy is one more round on Topic 08's finished report, not a re-run.

## Inherited handoffs that Topic 06 answered

Topic 05 handed over the boundary: it emits the utterance-time semantic event
— what was said, by whom, about what, with which deadline and conditions —
and explicitly does not decide whether it stays valid. Topic 06 owns state and
revision over time, and took Topic 05's open gaps as travelling with the
event: an event arriving without a confident owner, a bound deadline, or a
correctly attached condition is the normal case, not an error.

Topics 03 and 04 recorded no handoff to Topic 06. Checked against their
closure documents rather than assumed from the numbering: Topic 03 hands only
to 07 and 10, Topic 04 only to 05, 07, 08 and 10.

## Run record

Driven by the ChatGPT orchestrator, `chat` profile, 18 active steps per round,
four gate types. Per-step reasoning effort: `max` for admission, per-paper
analysis, synthesis and review; `extended` for terminology, search, report
writing and gap classification.

Round 1 was interrupted by a host hard-freeze while `search-llm` was
delegated. The reply had finished on ChatGPT's side before the host died, so
it was harvested over HTTP and the step was not re-sent; the transcript is at
`chatgpt/r1-search-llm.json` and its ledger entry stays at `sent` for that
reason. Round durations, first send to last: 78.0, 77.1, 68.0, 68.6 minutes.

**Topic 06 ran in parallel with Topic 08 from 00:54 onwards.** This was the
programme's first concurrent pair. No send-window contention, no conversation
-id collision and no rate-limit event was recorded in either run.

Worker conversations were archived locally and deleted from the account.
