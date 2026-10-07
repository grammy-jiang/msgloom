# Triage — IG5, the cost function

Produced by the `engineering-investigation` skill, Stage 0, on 2026-09-17.
Ranked first in `msgloom-integration-gaps.md`.

**Gap, verbatim:**

> **IG5 — The cost function nobody could write**
> `aliases`: `04: gap-5`, `05: gap-9`, `10: gap-6`, `10: gap-7`, `03: gap-2`
> `question`: What does an over-broad link cost, against a missed one?
> `seam`: none recorded — five gaps in four topics stop at the same wall
> `sender_established`: four topics each established that the threshold
> **cannot be read off a benchmark score**, because the two errors do not cost
> the same
> `receiver_established`: **there is no receiver.** This is a product decision
> and no topic could make it
> `classification`: ENGINEERING · `severity`: HIGH

**Kind:** DECISION
**Depends on:** nothing. It is the dependency.

## Why not the others

- **INSPECTION:** rejected. Searched `design-brief.md`, `design-principles.md`,
  `research/CONTEXT.md` and `phase-roadmap.md` for any statement of relative
  cost. The frame gives a goal **ordering** and never quantifies the exchange.
  Nothing to find.
- **MEASUREMENT:** rejected. Two measurements already exist and neither can be
  judged — that is the gap, not its solution.
- **GOLD:** rejected. A fixture set would produce a risk–coverage curve. Four
  topics already know the shape of that curve; none can pick a point on it.
- **COMPARISON:** rejected for the same reason. You can compare two abstention
  policies all week and still not know which is better.

**The test that decides it:** would this still be a judgement if you had
perfect measurements? **Yes.** That is a DECISION, and no amount of building
closes it.

## Who decides

**You — the product owner.** There is no other candidate. The measurement
exists, the judgement does not, and no topic had the authority to make it.

## What you need in order to decide

### 1. The two errors, in msgloom's own terms

| | What it is | What it costs |
| --- | --- | --- |
| **False obligation** | The report says you owe a response you do not | You read and possibly act on something that is not yours. **Recoverable** — you notice when you open it |
| **Missed obligation** | Work needing your response never appears | Goal 1 fails. `design-brief.md §1`: "missing one is **unacceptable**" |

Topic 05 names five concrete routes to a false obligation, which is what makes
the first column real rather than hypothetical: an invented owner; a mentioned
date promoted to a deadline; a lost condition or negation scope; quoted-history
duplication; a forced completion of uncertain fields.

### 2. The two measurements that already exist

Both are honest, both are unjudgeable without you.

| Source | Coverage | Error | The topic's own words |
| --- | --- | --- | --- |
| `01: E4` | **0.400** | 0.000 accepted error | "Correct, and possibly unusable" — 60% of eligible decisions abstained |
| `02: G8-E2` | 0.600 | 0.333 | Recorded as a **failure** against its target of ≤0.05 error at ≥0.40 coverage |

Topic 02 set itself a target — ≤0.05 error at ≥0.40 coverage — and missed it.
**Where that target came from is not recorded anywhere.** If it was your number,
say so and IG5 is half-closed. If it was invented to have something to fail
against, that is worth knowing too.

### 3. The thing your stated ordering does not settle

`design-principles.md §2` orders the goals: correct meaning and report coverage
first, then traceability, then ease of use, then speed and brevity.
`design-brief.md §1` puts *miss nothing* ahead of *reduce reading*.

**Read strictly, that ordering has no interior solution.** A lexicographic
preference for never missing anything says: never abstain, never filter,
surface everything. That is an inbox — which is the thing msgloom exists to
improve on, and goal 2 exists precisely to rule it out.

So the ordering is lexicographic in intent and cannot be in practice. **The
decision you are being asked for is where it stops being lexicographic.**

### 4. A question you can actually answer

You do not need to invent a loss function. One elicitable number does most of
the work:

> **How many false obligations a week would you accept, to catch one more real
> one you would otherwise have missed?**

If the answer is "ten", the exchange rate is 10:1 and every threshold in the
product follows from it. If the answer is "it depends on the work matter", then
the answer is a small table by priority — which is fine, and is itself the
decision.

A second, cheaper question sets the abstention floor:

> **At what coverage does a report stop being worth reading?** Topic 01
> measured zero error at 40% coverage. Is a briefing that abstains on three of
> every five items useful to you, or is it noise with good manners?

## What it unblocks

Six gaps, directly:

| Gap | What it can do once the rate exists |
| --- | --- |
| `C5` / `03: gap-2` | Set the false-merge against false-split threshold for Topic identity |
| `04: gap-5` | Set the abstention and asymmetric error-cost policy for reference resolution |
| `05: gap-9` | Tune uncertainty-preserving output against a forced-complete baseline — its own text says "tune to a **predefined acceptable** precision-recall trade-off" |
| `10: gap-6` | Define the human-review acceptance protocol; a sampling frame needs to know which errors matter |
| `10: gap-7` | Set what "overfit to the evaluator" means, which needs an acceptance bar |

And it makes `01: E4` and `02: G8-E2` interpretable for the first time.

**It also unblocks §22's `architecture-design`**, which the portfolio blueprint
marks `Depends On: the cost function` with `Blocks Next Step: Yes`.

## What happens next — revised 2026-09-17, after the owner's reply

**The owner cannot answer yet, and that is the right answer.** The number is
not knowable before the tool has run: it is a count of how many false
obligations a week the product actually produces, and nothing produces it yet.

So IG5 stops blocking, and becomes an ordered sequence:

### 1. Build MVP-0 with no exchange rate at all

Run it in **surface-everything mode**: no filtering, no abstention, no
threshold. Every candidate obligation appears, marked with its confidence and
its unresolved fields.

This is not a compromise. It is exactly what a strictly lexicographic reading
of `design-brief.md §1` prescribes — *miss nothing* with no trade against
*reduce reading* — and it is the only configuration that needs no number.
Goal 2 is simply not served yet, and the report says so.

### 2. Run it for a few days and count

The two quantities the decision needs are then observations rather than
guesses:

- how many surfaced items were **not** the user's to act on
- how many the user acted on, and how many they would have missed

That is the elicitation question answered from data instead of from intuition.

### 3. Then set the rate, once

And keep setting it. `DP-11` already governs this: version changes that affect
results, evaluate missed important information as well as false alerts, and
demonstrate that an optimisation preserves higher-priority goals before
adopting it. **The exchange rate is exactly such an optimisation.**

## The one design requirement this creates

**The exchange rate must be a single configured value, in one place, that a
non-developer can change.**

This is now a constraint on the architecture, not a preference. If it is baked
into thresholds scattered across triage, extraction, identity and briefing, the
first number chosen becomes permanent by accident — and the first number will
be wrong, because it will be chosen before the data exists.

Three specific obligations follow:

| # | Requirement | Why |
| --- | --- | --- |
| R1 | One named setting, read at run time, not compiled in | It changes on a schedule of weeks; the code does not |
| R2 | Every threshold derives from it rather than being set beside it | Five gaps need thresholds; five independently-set numbers cannot be changed together |
| R3 | A change to it produces a new result version, never an in-place edit | `DP-02` — reruns create new results; and you will want to compare before and after |

**The failure this prevents:** someone puts a placeholder in to get the build
moving, it spreads, and by the time the real number is known there are nine
places to change and no way to tell whether they agree.

## Status

`DECISION_REQUIRED` → **`DEFERRED`**, blocker named.

**Blocker:** the product has not run, so the counts the decision needs do not
exist.
**What lifts it:** a few days of MVP-0 in surface-everything mode.
**Meanwhile:** R1–R3 above are binding on `architecture-design`, which no
longer waits for the number — only for the commitment that the number will
have one home.

---

*Original triage below, unchanged.*

## What the run originally concluded

**Nothing, until you answer.** This file was the complete output of the run.

The skill's triage is designed to stop here rather than manufacture an
investigation, because the alternative — building a fixture set and producing
numbers for a decision — makes the decision look answered without making it.

When you have the rate, the five aliased gaps become GOLD or COMPARISON work
and `engineering-investigation` can run properly on each.

## A note on how this gap was produced

Four topics — 03, 04, 05 and 10 — each searched four rounds and arrived
independently at the same wall. Sixteen rounds of literature search to
establish that the answer is not in the literature.

Every one of them recorded it correctly as ENGINEERING and none could act,
because **the programme had no step that routes a decision to the person who
can make it.** That is recorded as D19 in `research/PROGRAMME_DEFECTS.md`, and
it is a structural fact about the programme rather than a fault in any topic.
