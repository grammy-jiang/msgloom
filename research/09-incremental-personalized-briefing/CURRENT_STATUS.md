# Topic 09 current status

## Academic research

- Rounds 1–4: complete. Stopped on `round_cap_reached`, the configured
  four-round cap, on 2026-09-17.
- Corpus: 53 papers admitted and read, none written off, **53 distinct** — a
  duplicate-title scan found no study recorded twice.
- New papers per round were 13, 16, 14, 10. Every round contributed and the
  loop was never stopped by `no_new_papers`.
- **Two rounds were rejected on first review and passed on the second**:
  round 1 at faithfulness 0.84 → 0.93, round 4 at 0.88 → 0.96. Rounds 2 and 3
  passed at the first attempt (0.93, 0.94). This is the most contested review
  record in the programme; every round was accepted in the end, and none was
  accepted by lowering the bar.
- Report:
  `msgloom-topic-09-incremental-personalized-briefing-research-report.md`.

**Reaching the round cap is a stopping condition, not evidence.** Round 4 was
still admitting 10 new papers when the budget ran out. All eight gaps remain
open and none was downgraded.

## Retained gaps

Academic, and not closed by four rounds of searching. Seven of the eight are
academic — the highest proportion in the programme, and a sign that this
topic's questions are about what is known rather than what must be built:

- **gap-1** No direct evaluation of a longitudinal workplace briefing that
  carries state across successive deliveries.
- **gap-2** How explicit user rules interact with soft learned preferences is
  not established.
- **gap-3** Long-term adaptation to changing roles, projects and priorities
  remains open.
- **gap-4** No end-to-end evaluation of briefing content selection that
  jointly weighs relevance, novelty and obligation.
- **gap-5** How reminder usefulness and likelihood of forgetting combine into
  a surfacing decision is undetermined.
- **gap-6** No admitted paper evaluates topic- or work-item-level incremental
  briefing across multiple workplace sources.
- **gap-7** The corpus holds evidence about stale reminders, epistemic
  uncertainty and conflicting updates separately, but not their interaction.

Engineering, and deliberately not a literature-search target:

- **gap-8** Candidate mechanisms from this corpus have not been compared in
  one reproducible cycle-based benchmark.

## Remaining deferred / handed-off work

**Topic 09 hands gap-8 to Topic 10**, which owns evaluation methodology — a
cycle-based benchmark comparing briefing mechanisms across successive
deliveries is an evaluation design question, not a briefing question.

**Topic 10 closed before this handoff was written, so its rounds never used
it.** Recorded here rather than left implicit: a handoff arriving after its
receiver has finished is a seam the programme owns and no topic closed. The
portfolio blueprint should read it as an integration gap, not as work Topic 10
did.

**Topic 09 also has an unowned seam with Topic 07.** Both were still running
when the other closed, so neither recorded a handoff to the other, yet a
briefing that carries state across deliveries and a retrieval loop that
decides when it has enough evidence must agree on what "already told the user"
means. Neither topic established it. This is an integration gap with no sender
and no receiver, and it is the clearest one the programme produced.

- Production-domain representativeness is deferred until authorized workplace
  data exists.
- No production architecture or briefing harness has been approved by Topic 09
  research.

## Inherited handoffs that Topic 09 answered

Topics 06 and 08 handed over what a briefing must not misstate: work-item
state, event factuality and conflicting revisions (06), and what an
attachment or table actually said (08).

The boundary held. Topic 09 did not redefine supersession or extraction
grounding; those stay with 06 and 08. What it addresses is what to surface
now, given what was surfaced before — and gap-7 says plainly that the
interaction between staleness, uncertainty and conflict is not established,
which is precisely where an inherited definition stops being enough.

## Run record

Driven by the ChatGPT orchestrator, `chat` profile, 18 active steps per round,
four gate types. Per-step reasoning effort: `max` for admission, per-paper
analysis, synthesis and review; `extended` for terminology, search, report
writing and gap classification.

Round durations, first send to last: 162.7, 142.7, 84.9, 88.6 minutes.

**Topic 09 ran in parallel with Topics 07 and 10 throughout** — the
programme's first three-way concurrency. One shard was lost to a socket
timeout in each of rounds 1 and 2 and re-dispatched; the ledger entries stay
at `failed` for that reason. The cause was this host's wireless link, not
ChatGPT: the other two topics kept sending throughout, and the host's own
network monitor reported an interface down and another demoted at the time.

Worker conversations were archived locally and deleted from the account.
