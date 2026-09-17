# Topic 01 — Email conversation structure, branching, and inline replies

> **This file is an index, not a synthesis.** Topic 01 ran before the current
> pipeline existed, so its evidence lives in two round reports under
> subdirectories rather than in one document here. This file exists so that a
> reader or a tool looking for `*-research-report.md` at the topic root finds
> the topic instead of concluding it never ran. **Do not cite this file as
> evidence.** Cite the round reports below.

## Standing

| | |
| --- | --- |
| Rounds | 2 academic, then a project-value review declined a third |
| Stopped on | `review_decision` — not a round cap, and not saturation |
| Engineering | a separate synthetic/adversarial validation phase, E1–E4 accepted |
| Open gaps | A2, A7 (academic), E5, E6 (engineering) — see `gaps.json` |
| Gap id namespace | `A<n>` / `E<n>`, not `gap-<n>` |
| Authoritative status | `CURRENT_STATUS.md` |

**How this topic stopped is a stronger closure signal than the round cap the
other topics hit, not a weaker one.** Topics 03–10 stopped because a
four-round budget ran out while papers were still arriving. Topic 01 stopped
because a review read the round-2 gaps and decided a third round was not
worth its cost. That is a decision about the evidence, not an accident of
budget.

## Where the evidence is

| Round | Scope | File |
| --- | --- | --- |
| 1 | The full topic: conversation structure, branching, inline replies | `local-corpus-20260914/email-conversation-structure-branching-and-inline-replies-research-report.md` (247 kB) |
| 2 | Narrowed to the two questions round 1 left open: incomplete email reconstruction, and quotation source-span alignment | `round2-20260915/topic-01-round-2-incomplete-email-reconstruction-and-robust-quotation-source-span-alignment-research-report.md` (67 kB) |

Round 2 does not supersede round 1. It answers a narrower question against a
different corpus, and the two are read together.

Round 2's gap classifier output is `round2-20260915/gaps.json`. The root
`gaps.json` is that file plus what `CURRENT_STATUS.md` records about each gap
after the engineering validation ran; it is the current state, and round 2's
is the snapshot.

## The engineering validation

`engineering-validation/` is the part of this topic no other topic has: a
built and measured artifact rather than a literature search.

- `PLAN.md`, `CASE_CATALOG.md`, `fixtures/`, `src/`, `results/`, `RESULTS.md`
- `audit/independent-review-01` … `-03` — three review cycles. The first two
  exposed methodology defects, which were repaired; the third returned
  `accepted` at confidence 0.98 with zero blocking issues, zero nonblocking
  issues and zero recommended fixes.
- `RETROSPECTIVE.md`, `DEFERRED.md`

E1–E4 are closed by this work at the synthetic and adversarial level. They are
**not** validated on production mailbox data, and `CURRENT_STATUS.md` says so
plainly: this is "the strongest conclusion justified now without production
mailbox data."

For the question of how an ENGINEERING gap should be closed — build a fixture
and measure, rather than search for a paper — this directory is the
programme's only worked example.

## Handoffs this topic recorded

In prose, in `CURRENT_STATUS.md`, before the `INHERITED_HANDOFFS.md`
convention existed:

- Semantic response and partial agreement → **Topic 04**
- General calibration and reliability methodology → **Topic 10**
- Cross-group and cross-source Topic identity → **Topic 03** / Phase 2

## Other documents at this root

`BLOCKERS.md`, `EVALUATION.md`, `FOLLOW_UP_REQUIREMENTS.md`,
`READING_LIST.md`, `REQUEST_FREQUENCY_AUDIT.md`, `RUN_STATUS.md`,
`VERSIONED_ARTIFACTS.md`, `SUMMARY.zh-CN.md` and the several `*_PROMPT.md`
files are working records from that run. They are history, not findings.
