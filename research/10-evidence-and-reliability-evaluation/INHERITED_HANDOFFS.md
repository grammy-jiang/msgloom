# Inherited handoffs

Everything an earlier Topic explicitly handed to this one, copied in full so
that this folder is enough on its own. You do not need to open an earlier
Topic's documents to start work here.

Each entry states what was handed over, what the sending Topic still owns, and
what it had established or left open at the time. A handoff is not a finding:
where the sender left a gap open, it is still open.

**Two entries at the end arrived after this Topic closed.** Topics 07 and 09
finished later, and their evaluation questions are recorded below because the
programme's integration map is built from recorded handoffs — an unrecorded
one is invisible to every stage that follows. Topic 10's four rounds never saw
them. They are seams the programme owns, not work this Topic did.

## From Topic 03 — Cross-thread Topic identity and incremental continuity

*Completed 2026-09-16. 4 rounds, 50 papers, report validated PASS 0.94.*

**Handed to Topic 10.** Calibration under non-stationary workplace streams,
as general methodology. Topic 03 records it as an open ACADEMIC gap (MEDIUM):
its corpus does not settle how confidence should behave when the stream's
distribution shifts.

**Boundary.** Topic 03 retains identity-specific uncertainty. The relative
cost of a false merge against a false split is a Topic 03 decision, not a
general calibration question.

## From Topic 04 — Reference resolution and response scope

*Completed 2026-09-16. 4 rounds, 47 papers, report validated PASS.*

**Handed to Topic 10.** Two open ENGINEERING gaps that are evaluation
questions rather than literature questions. Neither is closable by more
papers; Topic 04 searched four rounds and the required contract is
msgloom-specific.

- **A combined annotation and evaluation contract** covering exact, partial,
  ambiguous, unsupported, discontinuous, multiple-antecedent, composite and
  no-link outcomes. Exact links, span overlap, zero-link outcomes and
  multi-antecedent partial credit must be scored **separately**: a single
  aggregate can reward structurally unsafe behaviour and hide over-broad
  links. Topic 04 found the ingredients in the literature but not the
  combined scheme.
- **An abstention and asymmetric error-cost policy.** An over-broad approval
  link and a missed link do not cost the same, so a threshold cannot be read
  off a benchmark score. Topic 04's suggested form is to measure false-broad,
  missed and wrong-link errors separately against an explicit cost function,
  using independent synthetic and adversarial sets first and authorized
  workplace data later.

**Boundary.** Topic 10 owns the general calibration and attribution
methodology. Topic 04 keeps ownership of what the outcomes *mean*: which
proposition a response applies to, and what partial or absent scope is.

## From Topic 05 — Action items, requests, commitments and decisions

*Completed 2026-09-16. 4 rounds, 48 papers.*

**Handed to Topic 10.** Four open ENGINEERING gaps that are evaluation
questions rather than literature questions, and none closable by more papers:

- **G6** An argument-level benchmark and adversarial fixture suite covering
  implicit owners, several actions in one sentence, shared deadlines,
  conditional and negated actions, overlapping request/commitment labels,
  quoted-history contamination and attachment references. False positives,
  false negatives and each argument must be scored **separately**.
- **G7** Controlled comparison of sentence-local, message-level and
  selectively expanded thread context, with ablations, because the literature
  shows both context gains and context-induced degradation.
- **G8** Zoning author, quoted and forwarded content while preserving
  provenance, measuring both false-obligation reduction and recall loss.
- **G9** An uncertainty-preserving output with abstention, measuring whether
  leaving a field unresolved reduces false obligations without unacceptable
  recall loss.

**Boundary.** Topic 10 owns generic calibration and attribution methodology.
Topic 05 keeps ownership of what an action, owner, deadline or condition
means, and of what counts as a false obligation.

## From Topic 06 — Work-item state, event factuality, time, conflicting revisions

*Completed 2026-09-17. 4 rounds, 38 papers, no duplicate records. Every
round's synthesis was accepted by the independent review at the first attempt
— faithfulness 0.93 to 0.95 — which no earlier Topic managed. Stopped on
`round_cap_reached`. All eight gaps remain open and none was downgraded.*

**Handed to Topic 10.** Three open ENGINEERING gaps that are evaluation
questions rather than literature questions, and none closable by more papers.
This follows the pattern set by Topics 03, 04 and 05.

- **Gap 6** An end-to-end adversarial longitudinal suite covering
  plan→cancel, approve→revoke, deadline changes, contradictory same-time
  updates, out-of-order ingestion, stale late-arriving evidence, and
  completion claims later corrected. Topic 06's own suggested resolution
  requires that future evidence be **hidden from the prediction input**, that
  both false completion and failure-to-close be measured **separately**, and
  that the full evidence lineage be preserved.
- **Gap 7** A benchmark combining message time, effective/event time,
  deadline/constraint time and collection/version time, with fixtures where
  the four deliberately disagree, and current-state reconstruction evaluated
  at several observation cutoffs.
- **Gap 8** A provenance-preserving implementation with append-only
  observations and assessments, a reproducibly derived current-state
  projection, replay from empty state, and regression tests proving
  historical evidence cannot be silently overwritten.

**Also relevant to calibration.** Topic 06's Gap 5 — claimed versus
independently corroborated completion — is an abstention and confidence
question as much as an extraction one.

**Boundary.** Topic 10 owns generic attribution, calibration and selective
prediction methodology. Topic 06 keeps ownership of what a state, a
supersession or a corroborated completion *means*, and of what counts as a
false "completed".

*Basis: the ownership map — Topic 06's relationship table entry for 10, and
the precedent of Topics 03/04/05 routing their ENGINEERING gaps here — plus
Topic 06's Gaps 6, 7, 8 and their suggested resolutions, quoted from its
Research Gaps section. Topic 06's report does not name Topic 10 by number.*

## From Topic 08 — Email, image, table and attachment understanding

*Completed 2026-09-17. 4 rounds, 53 corpus records — **52 distinct papers**,
because one study was admitted twice under two identifiers. Rounds 2 and 4
were each rejected once and accepted after one repair; rounds 1 and 3 passed
at the first attempt. Stopped on `round_cap_reached`. All eight gaps remain
open and none was downgraded.*

**Handed to Topic 10.** Four open ENGINEERING gaps that are evaluation
questions rather than literature questions, following the pattern set by
Topics 03, 04, 05 and 06.

- **gap-5 (HIGH)** End-to-end behaviour when extraction or grounding is
  unsupported, incomplete or wrong. Unsupported extraction, missing evidence,
  failed localisation, ambiguous grounding and downstream reasoning failure
  must be **distinguishable outcomes**, not one bucket.
- **gap-6 (HIGH)** Robustness of candidate extraction and structure
  preservation on heterogeneous workplace-style documents.
- **gap-7 (MEDIUM)** Operational scaling on long documents, large tables and
  realistic workbooks. The corpus reports page-routing cost, evidence-graph
  overhead and document-length degradation, but no target-workload latency,
  memory or throughput.
- **gap-8 (HIGH)** One evaluation measuring semantic correctness, extraction
  completeness, exact provenance, unsupported-evidence handling and
  preservation together, rather than each alone.

**A methodological note Topic 10 should carry.** Topic 08 round 2 was
rejected because its synthesis cited one study twice — under a DOI and under
a bare `manual-` identifier — as independent corroboration. The structural
integrity checks passed; only the reader caught it. Evidence counting by
record rather than by distinct study is a live failure mode, and this topic's
own corpus still contains that pair.

**Boundary.** Topic 10 owns generic grounding-correctness, attribution and
completeness methodology. Topic 08 keeps ownership of what a correct
extraction, a grounded region or a preserved structure *means*.

*Basis: the ownership map — Topic 08's relationship table entry for 10
("evaluates extraction completeness, grounding/citation correctness, and
omission of multimodal evidence") and the precedent of Topics 03/04/05/06 —
plus Topic 08's gaps 5–8, quoted from gaps.json, and its round-2 review
verdict. The report does not name Topic 10 by number.*

---

## From Topic 07 — Context retrieval and completion

**Recorded after Topic 10 closed. Topic 10's four rounds never used this.**

Topic 07 closed with eight open gaps, three of them evaluation questions that
belong to this Topic's methodology:

- **gap-5** — an evaluation must distinguish *empty retrieval*, *authorization
  denial* and *unavailability*. All three produce "nothing to show" and they
  demand opposite responses from a reader. Topic 10's gap-1 already says no
  scheme jointly measures correctness, attribution, completeness and
  calibration; this adds a fourth distinction that collapses into
  "incomplete" under every metric either Topic found.
- **gap-6** — an end-to-end cost evaluation covering retrieval calls,
  retrieved passages and planner overhead. Topic 10 has no cost dimension at
  all; its metrics are about correctness throughout.
- **gap-7** — a workplace-communication evaluation combining explicit evidence
  gaps with heterogeneous sources. This is Topic 10's own gap-2 (no evaluation
  on private workplace communication) seen from the retrieval side, and it is
  the programme's most widely shared gap.

**Boundary.** Topic 10 owns how any of this is measured. Topic 07 keeps
ownership of what a retrieval loop is, when it may stop, and what a
provenance-preserving iteration means.

*Basis: Topic 07's `CURRENT_STATUS.md` and `gaps.json` at closure, and the
precedent of Topics 03/04/05/06/08, which each handed their evaluation
questions here. The report does not name Topic 10 by number.*

## From Topic 09 — Incremental personalized briefing

**Recorded after Topic 10 closed. Topic 10's four rounds never used this.**

- **gap-8** — the only engineering gap Topic 09 retained: candidate briefing
  mechanisms have not been compared in one **reproducible cycle-based
  benchmark**. Successive deliveries make this different from every benchmark
  Topic 10 admitted: correctness must be judged against what the reader was
  already told, so the unit of evaluation is a *sequence*, not a report.
  Topic 10's gap-1 and gap-4 both assume a single reporting unit.

**Boundary.** Topic 10 owns benchmark and protocol design. Topic 09 keeps
ownership of what makes a briefing incremental and what "already told the
user" means.

*Basis: Topic 09's `CURRENT_STATUS.md` and `gaps.json` at closure. The report
does not name Topic 10 by number.*
