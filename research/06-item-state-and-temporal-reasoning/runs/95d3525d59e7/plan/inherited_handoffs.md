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
