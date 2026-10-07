# Triage — 06: gap-7

Produced by the `engineering-investigation` skill, Stage 0, on 2026-09-17.
Raised as **IG8** in `msgloom-integration-gaps.md`, where it was ranked the
cheapest item in the register at "an hour's reading".

**Gap, verbatim:**

> `gap-7` · ENGINEERING · HIGH · open
>
> The combined representation of message time, event or effective time,
> deadline or constraint time, and observed collection or version time has not
> been benchmarked for the target state-resolution task; the corpus contains
> related temporal formalisms and temporal NLP evaluations rather than such a
> combined benchmark.
>
> *Resolution notes:* specify a four-time data model … then implement a
> benchmark that independently perturbs each dimension. Measure
> state-resolution accuracy on retroactive updates, future-effective changes,
> changed deadlines, late collection, and out-of-order ingestion. **Compare the
> full representation against ablations that omit each time dimension** to
> establish whether each field materially contributes.

**Owner:** Topic 06 — Work-item state, event factuality, time, conflicting
revisions.

**Kind:** INSPECTION
**Depends on:** nothing

## Why not the others

- **DECISION:** rejected. The question is whether an artifact already answers
  it, not a judgement that would survive perfect measurement.
- **MEASUREMENT:** rejected. Nothing to instrument — no candidate
  representation has been selected, and the gap asks for a benchmark rather
  than a timing.
- **GOLD:** rejected **for now**. The gap does need fixtures, but IG8 asked a
  prior question: does a fixture design already exist in a closed topic?
- **COMPARISON:** rejected for now, for the same reason, and because it would
  need the GOLD first.

## What was inspected

Topic 10's final report — its Recommendation 4, its trade-off table row on
temporal replay, and its Points of Agreement 3 — against Topic 06's `gap-7`
and its `resolution_notes`.

Topic 10's own record called its mechanism "almost exactly" what Topic 06's
gap asks for. **That reading is close and not right.**

## The answer

**Topic 10's Recommendation 4 supplies a substantial part of `gap-7`'s fixture
design and does not close it.** Three differences, in order of consequence.

| | Topic 06 `gap-7` | Topic 10 Recommendation 4 |
| --- | --- | --- |
| Time dimensions | message · event/effective · **deadline/constraint** · collection/version | event · message · collection/version · **current evaluation time** |
| Fixture design | independently perturb each dimension | construct cases where the times disagree |
| Named cases | retroactive updates, future-effective changes, changed deadlines, late collection, out-of-order ingestion | delayed arrival, out-of-order arrival, supersession, correction, stale evidence |
| **Ablations** | **required** — omit each dimension to prove it contributes | **not mentioned** |
| Measured quantity | state-resolution accuracy | unspecified; it is an evaluation-design recommendation |

**1. The fourth time is not the same time.** Topic 06's fourth dimension is
*deadline/constraint time* — a property of the work item, the thing a user must
respond by. Topic 10's fourth is *current evaluation time* — a property of the
measurement, the moment from which the system is being scored. They share
three dimensions and each has one the other does not.

That matters beyond bookkeeping: a benchmark built to Topic 10's
recommendation would never perturb a deadline, and "changed deadlines" is one
of the five cases Topic 06 names.

**2. The ablations are absent, and they are the question.** `gap-7` asks
whether each time field *materially contributes*. Only an ablation answers
that. Topic 10's recommendation builds fixtures where the times disagree, which
establishes that a system can be tested — not that every dimension earns its
place in the data model.

**3. Topic 10 recommends a method; Topic 06 asks for a result.** Recommendation
4 is evaluation-design guidance with no measured quantity attached. `gap-7`
wants state-resolution accuracy on named cases. One is an instrument, the other
is a reading from it.

## What happens next

**`gap-7` stays open, and is materially narrower.** What was "no combined
benchmark exists" is now "a cutoff-replay fixture design exists in Topic 10 and
covers three of the four dimensions and five overlapping cases; what remains is
the deadline dimension and the ablation design".

Recorded in Topic 06's `gaps.json` as a `resolution_notes` addition, not as a
closure.

**Route:** GOLD, when someone builds it. Start from Topic 10's Recommendation 4
and its four cited sources rather than from nothing, add deadline/constraint
time as a fourth perturbable dimension, and add the per-dimension ablation that
`gap-7` actually asks for.

**IG8 is closed by this file.** The register's question was "are these the same
benchmark?" and the answer is no, with the overlap quantified. The hour was
worth spending: it did not close a gap, and it saved whoever builds the
benchmark from starting at zero.

## A note for the programme

This is the only cross-topic resolution candidate found in 92 gaps, and it came
from a merge rather than from either topic. Neither could have found it:
closure steps compare gaps against gaps, and this was a gap against a
*finding*.

The near-miss is itself the lesson. Topic 10's record said "almost exactly",
and "almost exactly" turned out to be three of four dimensions with the
decisive element missing. **A closure step that had trusted that phrase would
have closed a gap that is still open.**
