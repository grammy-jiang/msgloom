# Inherited handoffs

Everything an earlier Topic explicitly handed to this one, copied in full so
that this folder is enough on its own. You do not need to open an earlier
Topic's documents to start work here.

Each entry states what was handed over, what the sending Topic still owns, and
what it had established or left open at the time. A handoff is not a finding:
where the sender left a gap open, it is still open.

## From Topic 06 — Work-item state, event factuality, time, conflicting revisions

*Completed 2026-09-17. 4 rounds, 38 papers, no duplicate records. Every
round's synthesis was accepted by the independent review at the first attempt
— faithfulness 0.93 to 0.95 — which no earlier Topic managed. Stopped on
`round_cap_reached`. All eight gaps remain open and none was downgraded.*

**Handed to Topic 09.** What counts as a *new development* rather than a
restatement, and which facts have been superseded and must not be repeated.
Topic 06 owns the state and its revision history; Topic 09 owns deciding what
of it is worth telling the user now.

**What Topic 06 established.** A work item's state evolves through requested,
proposed, planned, approved, completed, revoked, superseded, disputed,
conditional and unresolved, and the historical assessments must be kept, not
overwritten. A briefing that reports only the latest message therefore risks
both repeating superseded facts and hiding an item that is still open.

**What Topic 06 left open, and Topic 09 must not treat as settled:**

- *(ACADEMIC, HIGH, Gap 1)* No direct evaluation of multi-state lifecycle
  tracking across successive workplace messages while preserving historical
  assessments. The state Topic 09 receives is not a measured quantity.
- *(ACADEMIC, HIGH, Gap 5)* A "completed" state may be claimed rather than
  corroborated. A briefing that drops an item because it looks finished may
  be dropping work that still needs action — Topic 06 names this as the
  failure mode to fear.
- *(ENGINEERING, HIGH, Gap 6)* Cancellation, revocation, deadline change,
  late ingestion, same-time contradiction and corrected completion have never
  been measured end to end. These are exactly the transitions a briefing must
  surface.

**Boundary.** Topic 09 owns selection, priority and phrasing over time.
Topic 06 owns what the state is and what changed, including the admission
that it is unresolved.

*Basis: the ownership map — Topic 06's relationship table entry for 09
("briefing must distinguish new developments from still-open state and avoid
repeating superseded facts") — plus Topic 06's Gaps 1, 5 and 6. Topic 06's
report does not name Topic 09 by number.*

## From Topic 08 — Email, image, table and attachment understanding

*Completed 2026-09-17. 4 rounds, 53 corpus records — **52 distinct papers**,
because one study was admitted twice under two identifiers. Rounds 2 and 4
were each rejected once and accepted after one repair; rounds 1 and 3 passed
at the first attempt. Stopped on `round_cap_reached`. All eight gaps remain
open and none was downgraded.*

**Handed to Topic 09.** Critical structured evidence that a briefing must
preserve rather than flatten. A number in a table cell, a highlighted row, a
figure or an attachment version can carry the decision-relevant content, and
summarising only body text drops it.

**What Topic 08 established.** Flattening a document into plain text loses
relationships, units, coordinates, visual emphasis and version identity.
Structure- or visually enriched representations outperform lossy OCR or
plain-text pipelines in the settings tested. A briefing built on flattened
text inherits those losses.

**What Topic 08 left open, and Topic 09 must not treat as settled:**

- *(ACADEMIC, HIGH, gap-2)* Direct grounding of workplace-message referring
  expressions — "this screenshot", "the highlighted row", "numbers below" —
  is not established. A briefing that repeats such a phrase may be repeating
  a pointer nothing has resolved.
- *(ACADEMIC, HIGH, gap-3)* Comprehensive spreadsheet understanding is open
  for formulas, hidden rows and sheets, cross-sheet references and merged
  cells. A figure lifted from a workbook may not mean what it appears to.
- *(ENGINEERING, HIGH, gap-8)* No single evaluation measures semantic
  correctness, extraction completeness, exact provenance and
  unsupported-evidence handling together. Briefing completeness therefore
  cannot be inferred from extraction success.

**Boundary.** Topic 09 owns what is worth telling the user and when.
Topic 08 owns what the structured evidence says and where it came from.

*Basis: the ownership map — Topic 08's relationship table entry for 09
("briefing must preserve critical structured evidence rather than summarizing
only body text") — plus Topic 08's gaps 2, 3 and 8. The report does not name
Topic 09 by number.*
