# Topic 07 current status

## Academic research

- Rounds 1–4: complete. Stopped on `round_cap_reached`, the configured
  four-round cap, on 2026-09-17.
- Corpus: 61 papers admitted and read, none written off, **61 distinct** — a
  duplicate-title scan found no study recorded twice.
- New papers per round were 17, 17, 11, 16. Every round contributed and the
  loop was never stopped by `no_new_papers`.
- **Independent review accepted every round at the first attempt** —
  faithfulness 0.96, 0.94, 0.94, 0.96. Topics 06 and 10 also managed this.
- Report:
  `msgloom-topic-07-context-retrieval-and-completion-research-report.md`.

**Reaching the round cap is a stopping condition, not evidence.** Round 4 was
still admitting 16 new papers when the budget ran out, so this topic's silence
is weaker than a saturated search would give. All eight gaps remain open and
none was downgraded.

## Retained gaps

Academic, and not closed by four rounds of searching:

- **gap-1** Structured gap representations are insufficiently validated for
  temporal constraints and multi-entity conditions.
- **gap-2** No admitted study validates an iterative evidence-gap retrieval
  loop that jointly preserves document provenance across iterations.
- **gap-3** Stopping reliability under domain shift is open: sufficiency,
  confidence, conformal and stability criteria were each studied alone.
- **gap-8** No admitted study validates a single controller handling
  structured evidence gaps, planning and stopping together.

Engineering, and deliberately not literature-search targets:

- **gap-4** A bounded replenishment loop where unauthorized candidates are
  filtered without leaking their existence is untested here.
- **gap-5** The evaluated systems do not jointly distinguish empty retrieval,
  authorization denial and unavailability. These look identical to a reader
  and must not.
- **gap-6** An end-to-end cost evaluation covering retrieval calls, retrieved
  passages and planner overhead.
- **gap-7** A workplace-communication evaluation combining explicit evidence
  gaps with heterogeneous sources.

## Remaining deferred / handed-off work

**Topic 07 hands its evaluation questions to Topic 10**, which owns evaluation
methodology for the programme — the same handoff Topics 03, 04, 05, 06 and 08
made at their own closure. gap-5, gap-6 and gap-7 are the substance: how to
measure a retrieval loop's cost, and how to tell "nothing found" from "not
allowed to see it" in a way a reader can act on.

**Topic 10 closed before this handoff was written, so its rounds never used
it.** Recorded here rather than left implicit: a handoff that arrives after
its receiver has finished is a seam the programme owns and no topic closed.
The portfolio blueprint should read it as an integration gap, not as work
Topic 10 did.

**Topic 07 also has an unowned seam with Topic 09.** Both were still running
when the other closed, so neither recorded a handoff to the other, yet a
retrieval loop that decides it has enough evidence and a briefing that carries
state across deliveries must agree on what "already told the user" means — a
retrieved passage the reader has already seen is not new evidence. Neither
topic established it. This is an integration gap with no sender and no
receiver, recorded identically in Topic 09's status file.

- Production-domain representativeness is deferred until authorized workplace
  data exists. This is the programme's most widely shared gap.
- No production architecture or retrieval harness has been approved by Topic
  07 research.

## Inherited handoffs that Topic 07 answered

Topics 03, 04, 05, 06 and 08 handed over what a retrieval loop must preserve:
Topic identity across threads (03), reference resolution and response scope
(04), the action-item and commitment vocabulary (05), work-item state and
conflicting revisions (06), and attachment and table understanding (08).

The boundary held. Topic 07 did not redefine what a Topic, a commitment or a
supersession is; those stay with their owners. What it establishes is how
evidence for any of them is retrieved, when the loop may stop, and what the
system owes a reader when it cannot find something — and gap-8 says plainly
that doing all three in one controller is not established.

## Run record

Driven by the ChatGPT orchestrator, `chat` profile, 18 active steps per round,
four gate types. Per-step reasoning effort: `max` for admission, per-paper
analysis, synthesis and review; `extended` for terminology, search, report
writing and gap classification.

Round durations, first send to last: 87.5, 151.1, 93.3, 114.2 minutes.

**Topic 07 ran in parallel with Topics 09 and 10 throughout** — the
programme's first three-way concurrency. One shard was lost to a socket
timeout in round 2 and re-dispatched; the ledger entry stays at `failed` for
that reason. The cause was this host's wireless link, not ChatGPT: the other
two topics kept sending throughout, and the host's own network monitor
reported an interface down and another demoted at the time.

Worker conversations were archived locally and deleted from the account.
