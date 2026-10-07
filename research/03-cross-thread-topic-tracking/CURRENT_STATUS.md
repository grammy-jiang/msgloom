# Topic 03 current status

Written 2026-09-16, after Topic 04 closed. Topic 03's run finished earlier the
same day but its closure record was never written, so the status lived only in
the run artifacts. This file records the outcome; it changes no research
history.

## Academic research

- Rounds 1–4: complete. Stopped on `round_cap_reached`, the configured
  four-round cap.
- Corpus: 50 papers admitted and read. New papers per round: 14, 11, 13, 12,
  so every round contributed evidence and the loop was never stopped by
  `no_new_papers`.
- Independent review: round 1 was rejected (faithfulness 0.76) and accepted
  after one repair at 0.96; rounds 2–4 were accepted at 0.90, 0.89 and 0.88
  while still naming overreach each time. Every rejection is preserved.
- Report: `msgloom-topic-03-cross-thread-topic-tracking-research-report.md`,
  validated PASS 0.94. Per-round snapshots are kept as `…-report.r1…r3.md`.
- Three papers rejected in round 4 on a faulty identity check were restored
  after the check was fixed: identity became 40 VERIFIED, 2 TITLE_ONLY, none
  rejected, and admissions went from 12 to 14.

**Reaching the round cap is a stopping condition, not evidence.** All seven
gaps remain open and none was downgraded.

## Retained gaps

Academic:

- **HIGH** Which evidence combinations establish or refute continuity of a
  concrete work matter.
- **HIGH** No direct production-domain evidence for longitudinal work-matter
  tracking.
- **HIGH** How partial, subevent, evolving, membership and otherwise
  non-transitive relations should be represented.
- **MEDIUM** Calibration under non-stationary workplace streams.

Engineering, and not literature-search targets:

- **HIGH** The application-specific decision policy: the relative cost of a
  false merge against a false split.
- **HIGH** The msgloom correction and identity-state model, including stable
  Topic IDs under revision.
- **MEDIUM** The operational strategy for Phase 2 evidence seeking.

## Remaining deferred / handed-off work

- Production-domain representativeness: deferred until suitable authorized
  domain data exists; not a current blocker.
- Nothing is handed to Topic 04. Topic 03 *consumes* Topic 04's output:
  reference resolution can show that a new message refers to a prior matter,
  but its own `TOPIC_CONTEXT.md` warns that reference evidence alone may stay
  ambiguous, so it never forces a merge by itself. Topic 04 is now complete
  and that evidence is available.
- Evidence-gap-driven retrieval for the Phase 2 strategy: Topic 07.
- Calibration under non-stationary streams, as general methodology: Topic 10,
  while Topic 03 keeps ownership of identity-specific uncertainty.
- No production architecture has been approved by Topic 03 research.

## Run record

The first real run of the ChatGPT orchestrator. Its operating limits were
learned here: poll intervals, thread-bound Playwright objects, and the host's
memory ceiling. Worker conversations were archived locally and deleted from
the account.
