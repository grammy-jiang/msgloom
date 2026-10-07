# msgloom research programme

Ten research topics derived from the user-approved discussion. Review each result before treating it as settled. Topics may run **in parallel** where the inbound-handoff table below allows it; see [shared context](CONTEXT.md).

| Topic | Research brief | Status |
| --- | --- | --- |
| 01 | [Email conversation structure, branching, and inline replies](01-email-conversation-structure/BRIEF.md) | Complete — 2 academic rounds, stopped on `review_decision`; 4 gaps open (A2, A7, E5, E6); the only topic that built and measured |
| 02 | [Within-message Topic segmentation and multiple assignments](02-message-topic-segmentation/BRIEF.md) | Complete — 2 academic rounds, stopped on `review_decision`; 20 gaps retained; EV1–EV7 engineering validation accepted and closed |
| 03 | [Cross-thread Topic identity and incremental continuity](03-cross-thread-topic-tracking/BRIEF.md) | Complete — 4 rounds, 50 papers, report PASS 0.94, 7 gaps open |
| 04 | [Reference resolution and response scope](04-reference-and-response-scope/BRIEF.md) | Complete — 4 rounds, 47 records / **45 distinct papers**, report PASS, 5 gaps open; see its CURRENT_STATUS correction |
| 05 | [Action items, requests, commitments, and decisions](05-action-items-and-commitments/BRIEF.md) | Complete — 4 rounds, 48 papers, 9 gaps open |
| 06 | [Work-item state, event factuality, time, and conflicting revisions](06-item-state-and-temporal-reasoning/BRIEF.md) | Complete — 4 rounds, 38 papers, every round accepted first try, 8 gaps open |
| 07 | [Evidence-gap-driven context retrieval and completion](07-context-retrieval-and-completion/BRIEF.md) | Complete — 4 rounds, 61 papers, every round accepted first try, 8 gaps open |
| 08 | [Email, image, table, and attachment understanding](08-multimodal-content-understanding/BRIEF.md) | Complete — 4 rounds, 53 records / **52 distinct papers**, 8 gaps open |
| 09 | [Incremental, personalized, and priority-aware briefings](09-incremental-personalized-briefing/BRIEF.md) | Complete — 4 rounds, 53 papers, rounds 1 and 4 rejected once each, 8 gaps open |
| 10 | [Evidence attribution, factuality, completeness, and reliability evaluation](10-evidence-and-reliability-evaluation/BRIEF.md) | Complete — 4 rounds, 64 papers, every round accepted first try, 7 gaps open |

Status is a summary. Each completed topic's `CURRENT_STATUS.md` is the
authoritative record of what was finished, what is retained, and what was
handed to a later topic. Complete means everything actionable at this stage
is done and the rest is explicitly deferred, not that the literature is
exhausted or that any architecture is approved.

## Which topics may run in parallel

Two different tables get confused here, and only one of them is binding.

- A topic's **relationship table** in its `TOPIC_CONTEXT.md` lists what it is
  conceptually downstream of. It is a scope boundary, written before any
  research ran.
- A topic's **recorded handoffs** are what an earlier topic actually decided,
  at its closure, to hand over. This is the binding one, and it is narrower.

Topic 06 shows the difference. Its relationship table names 03, 04 and 05 as
suppliers, but at closure Topic 03 recorded handoffs only to 07 and 10, and
Topic 04 only to 05, 07, 08 and 10. Neither owed Topic 06 anything specific,
so Topic 06 inherits from Topic 05 alone — and that is correct, not a gap.

**Recorded handoffs, as of 2026-09-17** (from each receiving topic's
`INHERITED_HANDOFFS.md` and each sender's `CURRENT_STATUS.md`):

| Sender | Hands to | Recorded in |
| --- | --- | --- |
| 01 | 03, 04, 10 | its own `CURRENT_STATUS.md`, in prose — recorded before the `INHERITED_HANDOFFS.md` convention existed |
| 02 | 03, 04, 10 | its own `CURRENT_STATUS.md`, in prose — same |
| 03 | 07, 10 | receiver's `INHERITED_HANDOFFS.md` |
| 04 | 05, 07, 08, 10 | receiver's `INHERITED_HANDOFFS.md` and `TOPIC_CONTEXT.md` |
| 05 | 06, 07, 08, 10 | receiver's `INHERITED_HANDOFFS.md` |
| 06 | 07, 08, 09, 10 | receiver's `INHERITED_HANDOFFS.md`; each entry states its basis |
| 08 | 07, 09, 10 | receiver's `INHERITED_HANDOFFS.md`; each entry states its basis |
| 07 | 10 (**after 10 closed**) | receiver's `INHERITED_HANDOFFS.md`; its own `CURRENT_STATUS.md` |
| 09 | 10 (**after 10 closed**) | receiver's `INHERITED_HANDOFFS.md`; its own `CURRENT_STATUS.md` |
| 10 | — (terminal: receives from 01–09, hands to nobody) | its own `CURRENT_STATUS.md` |

**Topics 01 and 02 stopped differently, and it is a stronger signal, not a
weaker one.** Both ran two academic rounds and then a project-value review
read the gaps and declined to authorise a third — `review_decision`. Topics
03–10 all stopped on `round_cap_reached`, meaning a four-round budget ran out
while papers were still arriving. A decision about the evidence beats a budget
running out. Both files now say so in their first paragraph, because the
absence of that sentence made them read as unfinished.

**Four gap-id namespaces are in use.** Anything reading this programme has to
handle all of them:

| Namespace | Topics |
| --- | --- |
| `gap-<n>` | 03–10 |
| `boundary-<n>` | 05, alongside `gap-<n>` |
| `G<n>-A` / `G<n>-E` | 02 |
| `A<n>` / `E<n>` | 01 |

91 gap ids in total across the ten topics.

**Topic 01 is filed differently from the other nine.** It ran before the current pipeline
existed, so its two round reports live under `local-corpus-20260914/` and
`round2-20260915/` rather than at the topic root. Both a root `gaps.json` and
an index at the conventional report path have been added so that a tool
globbing `*research-report.md` finds the topic instead of concluding it never
ran — **the index is a pointer and says so; cite the round reports, not it.**

It is also the **only topic that built and measured rather than searched**:
`01-email-conversation-structure/engineering-validation/` holds fixtures, a
case catalog, results, an independent audit that returned `accepted` at 0.98
after two earlier cycles exposed and repaired methodology defects, and a
retrospective. For the question of how an ENGINEERING gap should be closed,
that directory is the programme's only worked example, and it is worth more
than the classification of the other 30 engineering gaps put together.

**Two handoffs arrived after their receiver had finished.** Topics 07 and 09
closed on 2026-09-17, after Topic 10, and each handed it evaluation questions
— Topic 07's gap-5/6/7, Topic 09's gap-8. They are recorded in Topic 10's
`INHERITED_HANDOFFS.md` and marked as arriving late, because the integration
map is built from recorded handoffs and an unrecorded one is invisible to
every later stage. Topic 10's four rounds never used them. They are seams the
programme owns, not work Topic 10 did.

**One seam has no sender and no receiver.** Topics 07 and 09 ran concurrently
and each closed after the other had already passed the point where a handoff
could be acted on, so neither recorded one — yet a retrieval loop that decides
it has enough evidence and a briefing that carries state across deliveries
must agree on what "already told the user" means. Neither established it. It
is recorded identically in both topics' `CURRENT_STATUS.md`, and it is the
clearest integration gap the programme produced.

**The conceptual graph has cycles, so no ordering satisfies every
relationship.** Topics 06, 07 and 08 each name the other two, and 07 and 08
name each other. Running strictly in numerical order still means 06 never
sees what 07 and 08 would supply it. The numbering is a research order and an
ownership boundary, not a topological sort; `CONTEXT.md` says as much.

What this means for running topics in parallel:

- Parallelism does not create a new class of problem. It changes how often an
  unavoidable one occurs.
- A handoff is never *lost* by running out of order. It is written into the
  receiving topic's folder when the sending topic closes, whether or not the
  receiver has already run, so the folder stays self-contained.
- What a parallel receiver loses is the *use* of that handoff during its own
  rounds: what the sender established, and which of the sender's gaps it must
  not treat as settled. The ownership boundary is not lost, because it is
  already in the receiver's own relationship table.
- Pair topics whose inbound handoff from the still-running topic would be
  thin. Topic 08 was chosen as the first parallel pairing because Topic 06
  supplies it one boundary sentence and researches a nearly disjoint
  literature.
- If a late handoff turns out to matter, the receiver takes one more round on
  top of its finished report. The pipeline resumes on a prior same-topic
  report by design; it does not start over.

An open gap is never downgraded by any of this. Gaps belong to the topic that
found them and stay open until evidence closes them.

## Review and improvement records

- [Pipeline issue register](PIPELINE_ISSUES.md)
- [Topic 01 independent evaluation](01-email-conversation-structure/EVALUATION.md)
- [Topic 01 conditional rerun prompt](01-email-conversation-structure/NEXT_RUN_PROMPT.md)

- [Request frequency and rate-restriction audit](01-email-conversation-structure/REQUEST_FREQUENCY_AUDIT.md)
