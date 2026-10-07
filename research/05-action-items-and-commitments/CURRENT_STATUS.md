# Topic 05 current status

## Academic research

- Rounds 1–4: complete. Stopped on `round_cap_reached`, the configured
  four-round cap, on 2026-09-16.
- Corpus: 48 papers admitted and read, none written off. New papers per round
  were 17, 12, 10, 9, so every round contributed and the loop was never
  stopped by `no_new_papers`.
- The admission rate fell each round as the topic narrowed — 17 of the first
  batch, then 9 of 25 in round 4. **That decline is itself a finding:** the
  searches got more precise, and fewer papers qualified, which is why the
  academic gaps below could not be closed.
- Independent review: round 1 was rejected once and accepted after a single
  repair; rounds 2, 3 and 4 were accepted at the first attempt with 5, 5 and
  3 issues. Final faithfulness 0.93, coherence 0.97, gap completeness 0.96.
- Report: `msgloom-topic-05-action-items-and-commitments-research-report.md`.
  Per-round snapshots are kept as `…-report.r1…r3.md`.

**Reaching the round cap is a stopping condition, not evidence.** All nine
gaps remain open and none was downgraded.

## Retained gaps

Academic, and not closed by four rounds of searching:

- **G1 (HIGH)** No modern workplace email or chat benchmark jointly annotates
  speech-act type, owner, action object, deadline, conditions and exact
  evidence spans.
- **G2 (HIGH)** Direct evidence for extracting decisions, approvals,
  rejections and proposals with structured arguments from authentic workplace
  material is missing.
- **G3 (HIGH)** Owner and assignee extraction stays weakly evidenced, above
  all for implicit owners, group ownership, several actions with different
  owners, and owners recoverable only from organisational context.
- **G4 (HIGH)** Reliable deadline binding is unresolved: telling a deadline
  for a particular action from a merely mentioned date, a shared date or a
  conditional future time.
- **G5 (HIGH)** Attaching conditions, exceptions, negation and modality to the
  correct action when several actions or clauses occur together.

Engineering, and deliberately not literature-search targets:

- **G6 (HIGH)** An argument-level benchmark and adversarial fixture suite.
- **G7 (HIGH)** Controlled comparison of sentence-local, message-level and
  selectively expanded thread context.
- **G8 (HIGH)** Author, quoted and forwarded content zoning with provenance.
- **G9 (HIGH)** An uncertainty-preserving output where owner, deadline,
  condition or act subtype may stay unresolved.

## Remaining deferred / handed-off work

- Production-domain representativeness: deferred until suitable authorized
  domain data exists; not a current blocker.
- Whether an extracted commitment is later confirmed, revoked, completed or
  contradicted: Topic 06. Topic 05 emits the utterance-time event and does
  not decide whether it stays valid.
- A missing owner, object or context becoming an explicit retrieval need:
  Topic 07.
- Action evidence that lives in attachments, tables or screenshots: Topic 08.
- G6–G9 as evaluation methodology: Topic 10, which owns generic calibration
  while Topic 05 keeps ownership of what an action, owner or deadline means.
- No production architecture has been approved by Topic 05 research.

Each handoff is recorded in the receiving topic's `INHERITED_HANDOFFS.md`.

## Inherited handoffs that Topic 05 answered

Topic 04 handed over the boundary rather than a task: it resolves *what* a
response is about, and Topic 05 classifies the act while taking that scope as
given. Topic 05's report states the rule explicitly — a correctly classified
act is not proof that its proposition-level scope is correct — and Topic 04's
open gap on workplace proposition-level scope still applies.

## Run record

Driven by the ChatGPT orchestrator, `chat` profile, 18 active steps per
round, four gate types. The first topic to run with per-step reasoning
effort: `max` for admission, per-paper analysis, synthesis and review;
`extended` for terminology, search, report writing and gap classification.
Worker conversations were archived locally and deleted from the account.
