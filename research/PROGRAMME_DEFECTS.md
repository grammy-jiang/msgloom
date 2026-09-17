# Programme defects register

Defects found while running `portfolio-blueprint` over the ten closed topics,
recorded as they were found. **This is not the integration-gap register.**
That one records what nobody researched; this one records how the programme
and the tools that ran it went wrong.

Three audiences, marked per entry:

- **SKILL** — fix in the `research-pipeline` skill so the next programme
  cannot repeat it
- **REPORT** — fix in a topic's own outputs, or accept and annotate
- **PROCESS** — how the programme was sequenced and recorded

Severity is what it costs a reader who trusts the output: **HIGH** means a
wrong conclusion is reachable from what is written.

---

## D1 — Evidence counted by record, not by distinct study · HIGH · SKILL

Two topics admitted one study twice and cited it as independent corroboration.

| Topic | Records | Distinct | The duplicate |
| --- | --- | --- | --- |
| 04 | 47 | **45** | two pairs, both caught at closure |
| 08 | 53 | **52** | `doi-10-1109-tmm-2022-3219642` and `manual-1048d6caf2` |

**It passed every structural check.** Topic 08's round 2 was rejected by the
independent reviewer, who caught it by reading; no gate did. The failure is
that a corpus is keyed by identifier, and one paper reachable through a DOI,
an arXiv id and a `manual-` hash is three identifiers.

**It propagates.** Topic 04's Finding 5 (HIGH, composite antecedents) reads as
resting on four papers. Three of its four citations are distinct studies —
and all three are transfer evidence. A reader counting citations to judge
strength gets a number that is wrong in the direction of confidence.

**Fix (SKILL):** a title-normalised duplicate scan at admission, not at
closure, and an evidence-strength count that reports distinct studies. Topics
06 and 10 ran the scan at their own closure and found none; that check should
not be a thing a topic remembers to do.

**Fix (REPORT):** Topic 04's Finding 5 needs its evidence count corrected in
place. Topic 08's corpus still contains the pair.

---

## D2 — A gap can vanish and leave no trace · HIGH · SKILL

Topic 10's gaps run `gap-1, gap-2, gap-4 … gap-8`. **There is no `gap-3`.**
One gap was resolved in round 2 and its text survives nowhere — not in the
report, not in `gaps.json`, not in `CURRENT_STATUS.md`.

A resolved gap is a finding: it says the literature answered something the
programme thought was open. Deleting it loses that, and it makes the gap
count unreconcilable across rounds.

**Fix (SKILL):** a gap is never removed, only given `status: resolved` with
what closed it. The `gap_classification` schema should require `status`.

---

## D3 — A topic's own gap count is wrong in its status file · MEDIUM · REPORT

Topic 05's `CURRENT_STATUS.md` says "all nine gaps". There are **ten**:
`gap-1`…`gap-9` plus `boundary-1`, which the file handles in prose and does
not count. `boundary-1` is not `gap-10` and cannot be renamed into one — it
came from Topic 04 and carries that provenance.

Anything taking the input count from status files instead of `gaps.json`
undercounts the programme by one, silently.

**Fix (REPORT):** correct the sentence. **Fix (SKILL):** the closure step
should count from `gaps.json`, not from prose.

---

## D4 — Gap ids were never constrained, so four namespaces exist · HIGH · SKILL

`gap-<n>` (03–10), `boundary-<n>` (05), `G<n>-A`/`G<n>-E` (02), `A<n>`/`E<n>`
(01). Ninety-one ids, four incompatible schemes, each internally consistent.

Root cause, traced: the schema typed `id` as a bare string while every other
controlled field in the same file carried an enum; the contract said only
"unique gap identifier"; **`build_prompt.py` told the model to use `gap-1`,
`gap-2`**, which is why 03–10 agree and 01–02, which predate that line, do
not; `manifest.json` declared `schema_valid` on nine outputs and the string
appeared in exactly one file in the whole skill — the manifest declaring it;
and `validate_artifact` returned True for any validation name it did not
recognise.

**Fixed (SKILL)** in `753f4f93`: pattern `^GAP-[0-9]{3}$`, the contract and
prompt aligned, a real dependency-free schema check, and an unknown validation
name now fails. **The closed topics keep their ids** — renaming them would
break every handoff already recorded against them.

---

## D5 — A declared validation that nobody implemented · HIGH · SKILL

Not only `schema_valid`. `evidence_present` is declared on three tasks and
implemented nowhere; `exit_code_zero` on seven and checked on another path.
A guarantee nobody implemented is worse than none, because it reads as one.

Discovered downstream of D4 and partly fixed: unknown names now block,
`evidence_present` prints that it is unimplemented on every task claiming it.
**`evidence_present` still does nothing.** It is declared on `paper-screener`,
`paper-analyzer` and `summarize` — the three tasks whose output *is* evidence.

---

## D6 — A schema required a key the producer never wrote · MEDIUM · SKILL

`query_plan.schema.json` required `topic`. The plan stage writes `topic_raw`
and `topic_normalized`. Roughly forty successful runs produced a
"non-conforming" artifact and nothing noticed, because nothing validated.
Fixed against what the stage actually produces.

---

## D7 — "Delivered" and "applied" are different, and nothing checks · HIGH · PROCESS

Of 26 recorded seams:

| | count |
| --- | --- |
| arrived after the receiver had closed | 3 |
| reached the receiver only from round 2 | 2 |
| recorded by the sender alone, never in the receiver's folder | 2 |
| **arrived on time and were not taken up** | **≥6** |

The last six are the dangerous ones: the handoff file shows them present and
correct. Named instances:

- **08 → 09** structured evidence a briefing must not flatten. Topic 09's
  report contains no discussion of attachments, tables, figures or flattening
  anywhere. 08's warning that *briefing completeness cannot be inferred from
  extraction success* is unanswered by the topic that owns briefing
  completeness.
- **06(b) → 07** a *claimed* completion is not a corroborated one. No matching
  Topic 07 finding or gap.
- **08(a)/(b) → 07** a retrieved span may carry no usable address. Topic 07
  recommends preserving "evidence location" without establishing one exists.
- **06 → 09** the same claimed-completion warning. Topic 09 assumes the state
  it receives.
- **04(b)/(c) → 05** mixed-act validation and composite-versus-several
  antecedents. Not taken up; they bear directly on how many action items one
  reply yields, which is Topic 05's F7.
- **01 → 02** authored-versus-quoted separation. Present as one fixture case;
  Topic 02's `G1-A` complaint is precisely that authored-only remains
  unestablished.

**Fix (SKILL):** the closure step should require, per inherited handoff, an
explicit *applied / scope-only / not taken up* verdict with a pointer. Five
topics did this voluntarily in their appendices and it is where every instance
above was found.

---

## D8 — Two handoffs never reached the receiver's folder at all · MEDIUM · PROCESS

`01 → 10` and `02 → 10` (calibration and selective-prediction methodology)
are recorded by both senders and are **absent from Topic 10's
`INHERITED_HANDOFFS.md`**, which holds seven entries and not these two. Topic
02's carried a live warning — that its own abstention plumbing *failed* its
joint error/coverage target — which the programme's methodology owner never
saw.

---

## D9 — The receiver-side convention arrived part-way through · MEDIUM · PROCESS

Seven of ten topics have no `INHERITED_HANDOFFS.md` (01, 02, 03, 04, 06 lack
it; 05 has one entry). Their inbound record lives in `TOPIC_CONTEXT.md`,
`CURRENT_STATUS.md` or `GAP_REVIEW_DECISION.md`.

**Had the programme relied on the receiver-side file alone, 14 of 26 seams
would be invisible.** Every one was recoverable only because each sender wrote
its half.

**Fix (SKILL):** the closure step writes both halves, always.

---

## D10 — A handoff transfers scope and never evidence · HIGH · PROCESS

Five topics state in their own appendices that inherited handoffs were
"treated as project context only and were not used as evidence for findings or
gap closure". That discipline is correct.

Its consequence is not recorded anywhere: **the programme has no mechanism by
which one topic's result becomes another topic's premise.** Topic 07 received
the same shape of work from five directions — *an unresolved X becomes an
explicit evidence need* — accepted all five, built one loop for them, and then
found in its `gap-8` that nobody has validated a single controller doing all
of it. The convergence is real and the integration is unevidenced.

This is a design question for the next programme, not a defect to patch: if
handoffs may never be evidence, who integrates?

---

## D11 — A report section name means something else than it says · MEDIUM · REPORT

Topic 02's report has a **Contradiction Map** holding 29 entries. They are
inconsistencies *within individual papers*, not conflicts between Topic 02's
own positions. Any consumer reading it as the topic's contradictions — which
is what the name says and what every other topic's equivalent section means —
would produce a completely false picture.

**Fix (REPORT):** rename to "Intra-paper inconsistencies observed".
**Fix (SKILL):** the report template should fix this section's meaning.

---

## D12 — Closure signal and its counter-evidence coexist unreconciled · MEDIUM · REPORT

Topic 02: the gap classifier returned `should_continue: true`, the report says
convergence was **not** established, and the project-value review stopped the
topic anyway. All three are recorded; none reconciles the other two.

Stopping was defensible — `review_decision` is the strongest closure signal in
this programme. But a reader cannot tell from the files whether the review
overrode the classifier knowingly or never saw it.

**Fix (REPORT):** one sentence in `CURRENT_STATUS.md` saying the review read
the classifier's verdict and overrode it, if that is what happened.

---

## D13 — A status file undercounts because it predates a later closure · LOW · REPORT

Topic 10's `CURRENT_STATUS.md` says "Only Topic 06 has also managed this"
about all-rounds-first-attempt acceptance. Topic 07 also managed it, and
closed afterwards. The claim was true when written.

**Fix (PROCESS):** comparative claims across topics belong in the programme
README, which is revised, not in a topic file, which is not.

---

## D14 — A concept with no project term · LOW · REPORT

Topic 06's "derived current-state view / projection" maps to no term in the
controlled vocabulary. Its neighbours do map: *work item* → **Topic**,
*source observation* → **Source record**, *assessment* → **Stage result**.

A concept the research needs and the project has not named is a real finding —
it belongs in the blueprint's information model, not lost in a record.

---

## D15 — Every topic stopped on a budget, and the reports do not foreground it · HIGH · SKILL

Eight of ten topics stopped on `round_cap_reached`, each with new papers still
arriving in the final round (07: 16; 09: 10; 03: 12; 08: 15). Two stopped on
`review_decision`.

Every closed topic's `CURRENT_STATUS.md` carries the sentence *"Reaching the
round cap is a stopping condition, not evidence."* **None of the reports carry
it.** A reader of the report alone will read an OPEN gap as established
silence.

**Fixed (SKILL, `portfolio-blueprint` side)** — an OPEN verdict must now name
its stopping condition. **Not fixed (SKILL, `research-pipeline` side)**: the
report template should carry the caveat next to the gap list, not only in a
closure file the report does not reference.

---

## D16 — Transfer evidence dominates, and no topic can say by how much · HIGH · REPORT

Every topic labels evidence direct or transfer, which is the right discipline.
Aggregated across records, the picture is stark:

| Topic | Direct target-domain evidence |
| --- | --- |
| 03 | **one finding** (F1), on 2006-era enterprise email, pre-Teams |
| 06 | **one paper of 38**, and it does not cover the target task |
| 07 | **none of 17 findings** |
| 10 | **none** — its own Evidence Map marks "Direct workplace validation" as *none admitted* |

No blueprint claim of an evidence-validated capability can cite Topics 07 or
10 at all. The programme knows this per-topic and has never stated it as one
number.

**Fix (SKILL):** the report's Evidence Map should carry a direct-vs-transfer
ratio, so the reader sees it without summing a table.

---

---

## D17 — A gap may already be answered by another topic, and neither knows · HIGH · PROCESS

Topic 06's `gap-7` asks for a benchmark combining message, effective, deadline
and collection time, evaluated at several observation cutoffs. Topic 10's own
record says this is "**almost exactly** Topic 10's observation-cutoff temporal
replay mechanism (F4, Recommendation 4)".

Topic 10 closed before Topic 06's handoff was read as anything but scope, so
Topic 06 does not know its gap may be closed and Topic 10 does not know it
closed one. It is the **only** candidate cross-topic resolution found in 92
gaps, and it was found by the merge, not by either topic.

**Fix (PROCESS):** at closure, a topic should check its open gaps against
already-closed topics' *findings*, not only against their gaps. Nothing in the
programme does this, which is why one round of merging found something four
rounds of research did not.

---

## D18 — Cost and scale are measured by nobody · HIGH · PROCESS

Topic 08's `gap-7` (latency, memory, throughput on the target workload) has
**no counterpart anywhere**. Topic 10's record states it: "Topic 08's gap-7
(cost/scale) has no counterpart in Topic 10 at all — Topic 10 has no cost
dimension." Topic 07's `gap-6` is the retrieval-side cost question and was
handed to Topic 10 **after it closed**.

So the programme's evaluation methodology owner has no cost dimension, the two
topics that noticed said so independently, and the handoff that would have
told it arrived too late. Meanwhile `DP-10` (minimise maintenance) and the
Raspberry Pi 5 host constraint make cost a first-class design concern.

**Fix (PROCESS):** a programme-level dimension check at planning time — which
topic owns cost, which owns security, which owns scale. Topic 08's coverage
matrix marks "attachment security" as ❌ Missing in its own scope and no other
topic picked it up either.

---

## D19 — Four topics hit the same wall and none could act · MEDIUM · PROCESS

`04: gap-5`, `05: gap-9`, `10: gap-6`, `10: gap-7` and the merged `C5` all
reduce to one thing: **a threshold cannot be read off a benchmark score**,
because an over-broad approval link and a missed link do not cost the same.

This is a **project decision, not a literature question**, and no topic could
make it. Four topics independently reached it, recorded it, and stopped. The
Project Frame states the goal ordering — miss nothing first, reduce reading
second — without quantifying the exchange rate, so the input a topic would
need does not exist in the design documents either.

Not a defect in any topic. A structural fact: **the programme generated four
open gaps that only the product owner can close**, and no step routes them to
that owner.

---

## D20 — The merge rate is low, which is good news worth recording · LOW · PROCESS

Only 15 of 92 gap ids merged — 16%. Seven consolidated gaps, 77 standing
alone. The topics' boundaries held: this is ten reports on ten subjects, not
ten overlapping restatements.

Recorded because the opposite result was plausible. Ten topics sharing one
controlled vocabulary and one screening heuristic could easily have produced
the same gap ten times in ten wordings, and a merge finding 60% duplication
would have said the programme was badly partitioned. It was not.

## Still to come

Passes 2–4 of Stage 2 and Stages 3–6 have not run. This register is appended
to as they do.
