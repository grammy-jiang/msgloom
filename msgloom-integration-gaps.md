# msgloom — Integration Gap Register

Companion to `msgloom-portfolio-blueprint.md`. Eleven gaps found by walking all
26 recorded seams between the ten research topics. Six seams came back clean
and are listed at the end.

**How to read this.** These are gaps **no single topic owned** — they live
between topics, which is why four rounds of research inside each topic could
not find them. Nine of eleven are ENGINEERING: agreeing an interface is not a
fact to discover, and routing these to a literature search would spend weeks
confirming the literature is silent about msgloom's seams.

`already_searched` records what earlier topics exhausted **and in what terms**.
Read it before planning any search. A question several topics failed to close
over four rounds is strong evidence of silence *only if they searched it in
materially different terms*; every topic here shared one controlled vocabulary,
and eight stopped at a round cap while papers were still arriving.

---

## IG1 — What "already told the user" means

| Field | Value |
| --- | --- |
| `id` | IG1 |
| `aliases` | — (no topic gap covers it) |
| `question` | Is "already delivered to the reader" a property of the evidence, of the work item, or of the reader? |
| `seam` | 07 ↔ 09 — **no sender and no receiver** |
| `crossing_requires` | An agreed answer to whether a passage the reader has already seen counts as new evidence |
| `sender_established` | Nothing. Topic 07 defines sufficiency over retrieved evidence without reference to what was delivered |
| `receiver_established` | Nothing. Topic 09 defines new/open/resolved/superseded over work-item state without reference to what was retrieved |
| `classification` | ENGINEERING |
| `severity` | HIGH |
| `already_searched` | Not searched by any topic. Both ran concurrently and each was still running when the other closed |
| `blocks` | The briefing capability (K8) and the investigation loop (K10) → goal 2, *reduce the reading needed to keep up*, without breaking DP-06 |
| `out_of_scope_for` | Neither topic claimed it; both recorded it at closure |

**Recommendation.** Define it before Phase 2. A retrieval loop that re-fetches
what the reader saw wastes budget; a briefing that suppresses what retrieval
newly confirmed breaks DP-06. Both topics recorded this in identical words at
their own closures, and Topic 09's status file calls it "the clearest one the
programme produced".

---

## IG2 — A claimed completion is not a corroborated one

| Field | Value |
| --- | --- |
| `id` | IG2 |
| `aliases` | `06: gap-5` |
| `question` | Does a work-item state carry whether its "completed" was asserted by a source or corroborated independently? |
| `seam` | 06 → 07, 06 → 09, 06 → 10 |
| `crossing_requires` | A receiver to know which of the two it has |
| `sender_established` | That the distinction matters and nothing makes it. `[06: gap-5]` ACADEMIC HIGH, stated impact: "a false 'completed' state could hide work still requiring action" |
| `receiver_established` | **Nothing, in any of the three.** Topic 07 has no matching finding or gap; Topic 09 "assumes the state it receives"; Topic 10 received it as a calibration question and has no gap for it |
| `classification` | ENGINEERING |
| `severity` | HIGH |
| `already_searched` | Topic 06, rounds 1–4, `round_cap_reached`, in temporal-reasoning and factuality vocabulary. Not searched by any receiver |
| `blocks` | Every capability downstream of state (K7, K8, K10) → **goal 1, no work needing a response is missed** |
| `out_of_scope_for` | — |

**Recommendation.** Carry the distinction as a field on the assessment, not as
a research question. `[06: contradiction 4]` warns that the mechanism it would
rest on is itself contested — ProvenanceGuard finds a source-blind baseline
statistically competitive for binary rejection — so **record the distinction
first and decide later whether anything acts on it**.

**One sender, three receivers, zero uptake.** The strongest evidence in the
programme that a handoff being recorded says nothing about it being used.

### RESOLVED 2026-09-17 — owner decision D-7

**Record the declaration. Do not verify it, and do not report it as fact.**

> "Of course a declaration from someone is not the fact that something is done.
> The fact is that someone makes this declaration… we only need to mention
> somebody makes this clear declaration and shouldn't use a word like *this is
> a real fact and it is confirmed*. No such thing at this moment."

**The distinction is in the wording, not in a mechanism.** What the system knows
is an event: *a person said a thing on a date*. That event is a fact. What the
person said may or may not be true, and the product takes no position.

| Not this | This |
| --- | --- |
| The invoice has been sent | On 16 Sep, Dana wrote that the invoice had been sent |
| Completed | Reported complete by the supplier; not independently checked |
| Confirmed | — no report may use this word about a source's claim |

**No corroboration service is built now.** The recommendation above said "record
the distinction first and decide later whether anything acts on it". The owner
has decided: **nothing acts on it yet.**

**This makes IG2 cheaper than it looked.** It was filed as a schema decision
needing a field. It is really a report-language rule plus an attribution the
product already has — who said it and when. The schema question narrows to:
does a work-item state carry the utterance that produced it? It must, and
`DP-02` already requires that binding.

---

## IG3 — Attribution and accuracy on separate denominators

| Field | Value |
| --- | --- |
| `id` | IG3 |
| `aliases` | `10: gap-1`, `08: gap-8` (merged as `C1`) |
| `question` | What is the concrete contract in which a citation being wrong and an answer being wrong are counted separately? |
| `seam` | 01 → 10 (**absent from Topic 10's inherited file**), 06 → 10, 08 → 10 |
| `crossing_requires` | One evaluation contract with both denominators named |
| `sender_established` | Topic 01 **measured** the trade-off: attribution error 0.000 → 0.222 for recall 0.842 → 0.947. Topics 06 and 08 each reached "evaluate them separately" from their own literature |
| `receiver_established` | `[10: gap-1]` is the general form and is open. Topic 10 never saw Topic 01's measurement |
| `classification` | ENGINEERING |
| `severity` | HIGH |
| `already_searched` | Topic 10, rounds 1–4, `round_cap_reached`, in attribution and calibration vocabulary. Topic 01 did not search — it built and measured |
| `blocks` | The evaluation strategy (§17) and therefore every readiness claim |
| `out_of_scope_for` | — |

**Recommendation.** Start from Topic 01's measurement, which is the only
controlled comparison in the programme, and generalise it. This is contradiction
**C2** seen as a seam: the topic holding the measurement and the topic holding
the mandate never met.

---

## IG4 — Cost and scale are owned by nobody

| Field | Value |
| --- | --- |
| `id` | IG4 |
| `aliases` | `08: gap-7`, `07: gap-6` |
| `question` | Which topic — or which part of the design — owns latency, memory and throughput? |
| `seam` | 08 → 10, 07 → 10 (**arrived after Topic 10 closed**) |
| `crossing_requires` | An owner |
| `sender_established` | Topic 08 measured nothing and says so; Topic 07 lists every cost term and says no end-to-end evaluation exists |
| `receiver_established` | **Nothing. Topic 10 has no cost dimension at all** — its own record says so, and Topic 08's record says so independently |
| `classification` | ENGINEERING |
| `severity` | HIGH |
| `already_searched` | Topic 08 rounds 1–3 (round 4 was retargeted at academic gaps); Topic 07 rounds 1–4. Both `round_cap_reached`. Topic 10 never searched it |
| `blocks` | DP-10 (minimise maintenance) and the Raspberry Pi 5 host constraint, which make cost a first-class design concern the programme never assigned |
| `out_of_scope_for` | Topic 10 by its own scope statement |

**Recommendation.** Assign an owner at planning time, not at closure. The same
check would have caught IG11.

---

## IG5 — The cost function nobody could write

| Field | Value |
| --- | --- |
| `id` | IG5 |
| `aliases` | `04: gap-5`, `05: gap-9`, `10: gap-6`, `10: gap-7`, `03: gap-2` (merged as `C5`) |
| `question` | What does an over-broad link cost, against a missed one? |
| `seam` | None recorded — five gaps in four topics stop at the same wall |
| `crossing_requires` | A stated exchange rate |
| `sender_established` | Four topics each established that the threshold **cannot be read off a benchmark score**, because the two errors do not cost the same |
| `receiver_established` | **There is no receiver.** This is a product decision and no topic could make it |
| `classification` | ENGINEERING — a decision to make, explicitly not a literature question |
| `severity` | HIGH |
| `already_searched` | Four topics, four rounds each, all `round_cap_reached`, in calibration, selective-prediction and abstention vocabulary. The literature was not the problem |
| `blocks` | `[01: E4]`'s abstention result (coverage 0.400) and `[02: G8-E2]`'s (failed at 0.600/0.333) are **both unjudgeable without it**. Also C5, and every threshold in the product |
| `out_of_scope_for` | Every topic. It belongs to the product owner |

**Recommendation.** **Do this first.** The Project Frame gives the goal
ordering — miss nothing first, reduce reading second — and never quantifies the
exchange. It is the input four topics needed and the design documents do not
contain. It is a decision, not a study, and it unblocks six gaps.

---

## IG6 — A retrieved span may carry no usable address

| Field | Value |
| --- | --- |
| `id` | IG6 |
| `aliases` | `08: gap-4`, `08: gap-1` |
| `question` | What is the address format by which a retrieved region can be cited — version, page, element, region? |
| `seam` | 08 → 07 |
| `crossing_requires` | A retrieved region to be citable |
| `sender_established` | That no validated end-to-end representation does this, and explicitly that "Topic 07 cannot assume a retrieved span carries a usable address" |
| `receiver_established` | Topic 07 recommends preserving "evidence location" **without establishing that one exists** |
| `classification` | ENGINEERING |
| `severity` | HIGH |
| `already_searched` | Topic 08 rounds 1–4 `round_cap_reached`, in document-grounding and provenance vocabulary. Received by Topic 07 from round 2 |
| `blocks` | The report contract's requirement that topic details reference every source message; DP-02 |
| `out_of_scope_for` | — |

**Recommendation.** An architecture decision, named in §21. Both topics agree
on the ownership split and neither produced the format.

### RESOLVED 2026-09-17 — owner decision D-6

**The address is the message's own permalink, plus a description of what inside
it is being referenced.**

> "Usually the email will have a URL or link… it is already linked to a
> deterministic location, so you don't need to worry about the name changing or
> the page number changing."

| Part | What it is | Who follows it |
| --- | --- | --- |
| **Anchor** | The source system's own permalink to the message — an Outlook Web or Gmail message URL | A machine. It is stable and the source system owns it |
| **Locator** | Plain text naming what within it: which attachment, which page, which sheet | A person, by opening the anchor and looking |

**The general rule, in the owner's words:** *every time it mentions something,
it points to a deterministic place with a clear description.*

**Why this dissolves the gap.** Topic 08's warning was that no *derived* address
survives re-derivation — a filename changes, a page number moves when a document
is re-exported. That is true and it is also beside the point, because the
product does not need to derive an address. The source system already issued
one and never reissues it. Topic 07's "preserve evidence location" is
satisfiable after all; what it preserves is a link, not a computed coordinate.

**What the architecture still owes.** Three things, all small:

1. Every source must yield a permalink at ingestion, or it is not a usable
   source. **This is an acceptance condition on each connector**, not research.
2. The locator is human-readable text, so it is generated by the AI side and
   carries the same trust class as any other AI output.
3. A message the owner can no longer open — deleted, or in a mailbox since
   removed — makes the anchor dangle. The report says so rather than showing a
   link that fails. This is the same rule as D-1.

---

## IG7 — Structured evidence a briefing must not flatten

| Field | Value |
| --- | --- |
| `id` | IG7 |
| `aliases` | `08: gap-2`, `08: gap-3` |
| `question` | Which non-text evidence survives summarisation into a briefing? |
| `seam` | 08 → 09 — **arrived on time, zero uptake** |
| `crossing_requires` | The briefing to know which structured evidence is decision-relevant |
| `sender_established` | That a table cell, highlighted row, figure or attachment version can carry the decision-relevant content, and that **briefing completeness cannot be inferred from extraction success** |
| `receiver_established` | **Nothing.** Topic 09's report contains no discussion of attachments, tables, figures or flattening anywhere — not in themes, findings, recommendations, gaps or evidence map |
| `classification` | ENGINEERING |
| `severity` | HIGH |
| `already_searched` | Topic 08 rounds 1–4 `round_cap_reached`. **Topic 09 never searched it** despite receiving it before its own rounds 2–4 |
| `blocks` | DP-06 at the delivery end |
| `out_of_scope_for` | — |

**Recommendation.** **One more round on Topic 09's finished report, not a
re-run.** The handoff arrived in time; the topic did not engage it. Topic 08
recorded the same remedy for its own equivalent case.

---

## IG8 — Topic 06's benchmark may already exist in Topic 10

| Field | Value |
| --- | --- |
| `id` | IG8 |
| `aliases` | `06: gap-7` |
| `question` | Are `[06: gap-7]` and Topic 10's F4 the same benchmark? |
| `seam` | 06 → 10 |
| `crossing_requires` | Somebody to compare an open gap against a closed topic's **findings**, not only against its gaps |
| `sender_established` | `[06: gap-7]` — a benchmark combining message, effective, deadline and collection time, evaluated at several observation cutoffs |
| `receiver_established` | Topic 10's F4 and Recommendation 4 — the observation-cutoff temporal replay mechanism, which Topic 10's own record calls "almost exactly" that |
| `classification` | ENGINEERING — read both and decide |
| `severity` | MEDIUM |
| `already_searched` | Both topics searched four rounds; neither compared its output to the other's |
| `blocks` | Nothing, if they match |
| `out_of_scope_for` | — |

**Recommendation.** **An hour's reading, and it is the cheapest item in this
register.** Topic 06 does not know its gap may be closed; Topic 10 does not
know it closed one. This is the only candidate cross-topic resolution in 92
gaps, and the merge found it, not the research.

---

## IG9 — Authored versus quoted text, re-opened three times

| Field | Value |
| --- | --- |
| `id` | IG9 |
| `aliases` | `05: gap-8`, `02: G1-A`, `02: G1-E`, `01: E2` |
| `question` | Does Topic 01's synthetic authored-versus-quoted separation transfer to real mail? |
| `seam` | 01 → 02 (partially applied), 01 → 05 and 01 → 06 (declared dependency, never transferred) |
| `crossing_requires` | Downstream topics to receive text already separated into authored and quoted zones with provenance |
| `sender_established` | Topic 01 built and measured the separation synthetically — `E1`–`E4` closed at reviewer confidence 0.98 |
| `receiver_established` | Topic 02's `G1-A` complains that authored-only evaluation **remains unestablished**; Topic 05's `gap-8` asks for the zoning **from scratch** |
| `classification` | ENGINEERING |
| `severity` | MEDIUM |
| `already_searched` | Topic 01, 2 rounds, `review_decision`, in email-structure vocabulary. Topics 02 and 05 re-opened it rather than consuming it |
| `blocks` | False obligations from quoted history — Topic 05 lists quoted-history contamination as a named production route for a false obligation |
| `out_of_scope_for` | — |

**Recommendation.** Apply Topic 01's gold contract to real mail. One topic
built it and three re-opened it; that is a transfer question, not three
research questions.

---

## IG10 — A failed abstention result never reached the methodology owner

| Field | Value |
| --- | --- |
| `id` | IG10 |
| `aliases` | `02: G8-E2` |
| `question` | Was Topic 02's abstention failure a failure of the method or of the target? |
| `seam` | 02 → 10, recorded by the sender, **absent from Topic 10's inherited file** |
| `crossing_requires` | The methodology owner to see failed as well as successful attempts |
| `sender_established` | EV6's abstention plumbing **failed** its joint error/coverage target — holdout coverage 0.600 at error 0.333 against ≤0.05 error at ≥0.40 coverage — and Topic 02 recorded that as a live warning on the handoff |
| `receiver_established` | Topic 10's inbound file has seven entries and this is not one of them |
| `classification` | ENGINEERING |
| `severity` | MEDIUM |
| `already_searched` | Topic 02, 2 rounds, `review_decision`, then measured. Topic 10 never saw it |
| `blocks` | `[10: gap-6]`, which asks for a review protocol this result would have informed |
| `out_of_scope_for` | — |

**Recommendation.** Route the result to whoever writes the review protocol. It
is one of only two measured abstention results in the programme and the only
one that failed.

---

## IG11 — Attachment security has no owner

| Field | Value |
| --- | --- |
| `id` | IG11 |
| `aliases` | — |
| `question` | Who owns the risk that content arriving inside an attachment acts as authority? |
| `seam` | None recorded |
| `crossing_requires` | Somebody to own it |
| `sender_established` | Topic 08 marks attachment security **❌ Missing** in its own coverage matrix — it names the hole and disowns it |
| `receiver_established` | No other topic picked it up |
| `classification` | ENGINEERING |
| `severity` | MEDIUM |
| `already_searched` | **Not searched by any topic** |
| `blocks` | DP-09 — source content is data, not authority — where the content arrives inside an attachment |
| `out_of_scope_for` | Topic 08, explicitly, in its own coverage matrix |

**Recommendation.** Assign it to `security-review`, which §22 routes as RUN for
exactly this reason.

---

## Seams with no gap

Walking a seam and finding it sound is a result. Six came back clean.

| Seam | What each side established |
| --- | --- |
| **04 → 05** | Topic 04 established that an act's antecedent scope is a separate question; Topic 05 registered it as the open id `boundary-1` rather than absorbing it. The substance stays open in `[04: gap-1]`; the **seam** is agreed both sides |
| **05 → 06** | Topic 05 emits the utterance-time event and disowns lifecycle; Topic 06 accepts that an event arriving without a confident owner, deadline or condition is "the normal case, not an error" |
| **03 → 07** | An unresolved identity question becomes a targeted evidence need. Named in Topic 07's context file before its round 1 and answered there; continuity was not redefined |
| **04 → 07** | A reference with no resolvable antecedent stays unresolved rather than forced. "Empty retrieval ≠ negative evidence" runs through Topic 07's whole report |
| **08 → 07 (part c)** | A failed extraction must be distinguishable from an absent answer. Taken up directly: "unsupported extraction" is a named terminal state in `[07: gap-5]` |
| **06 → 09 (vocabulary)** | New / open / resolved / superseded. Topic 06 owns what the state is, Topic 09 owns what is worth telling now. Only the corroboration half failed to cross — that is IG2 |

---

## Recommendation

**Do not start a new research programme on these.** Nine of eleven are
ENGINEERING; the two cheapest (IG8, an hour's reading; IG7, one round on a
finished report) are not research at all; and the most valuable (IG5) is a
product decision.

**Order — revised 2026-09-17 after the design-stage security review
(`msgloom-security-review.md`):**

**IG6 is promoted to a Phase 1 blocker.** The review's F2 establishes why:
after extraction, authored content and injected content are byte-identical,
and the only thing that distinguishes them is the address. No address, no
distinction — so every defence IG11 needs depends on IG6 first. It was ranked
seventh here as an architecture-stage decision; that was wrong.

**IG9 and IG11 merge for handling.** The same authored/quoted zoning primitive
serves two consumers: false obligations from quoted history, and trust
labelling for injected content. Three registered items, one mechanism, no
extra work.

1. **IG6** — **resolved 2026-09-17, owner decision D-6.** The address is the
   source system's own message permalink plus a human-readable locator. It was
   promoted to a Phase 1 blocker earlier the same day; it stopped being one a
   few hours later, because the product never needed to derive an address. What
   remains is an acceptance condition on every connector, not a design problem.
2. **IG5** — the cost function. **Answered 2026-09-17: deferred to
   measurement**, because the number is a count the product has not produced
   yet. See `IG5-cost-function-triage.md`. Its three requirements — one
   setting, all thresholds derived from it, changes versioned — are binding on
   the architecture stage now.
3. **IG8** — **closed 2026-09-17.** Topic 10's Recommendation 4 covers three of
   the four time dimensions and five overlapping cases, and does **not** cover
   deadline/constraint time or the ablation `gap-7` actually asks for. The gap
   stays open and is materially narrower. See
   `research/06-.../gap-7-triage.md`.
4. **IG11 + IG9** — **owned as of 2026-09-17.** R-A…R-M in
   `msgloom-security-review.md`. F5 was measured rather than assumed and came
   back **corrected**: lxml's default already refuses external entities, and
   the real trap is that `no_network=True` blocks the network while doing
   nothing about local file reads. The probe is
   `research/security-probes/xxe_probe.py` and it is meant to be re-run on
   every dependency upgrade.
5. **IG2** — **resolved 2026-09-17, owner decision D-7.** Record that a person
   made a claim; never report the claim as fact. No corroboration mechanism is
   built at this stage. A report-language rule, not a schema programme.
6. **IG1** — define "already told the user" before Phase 2 begins.
7. **IG4** → assign an owner.
8. **IG7, IG10** — one more pass on finished work, not new programmes.
9. **IG3** — an architecture-stage decision, evidence attached in blueprint §21.

**If an authorized workplace corpus becomes available**, `P1` in the
consolidated register lifts and twelve gaps across nine topics become
researchable — but each needs its own annotation pass, and `[10: gap-6]` says
the review protocol for any of them is itself undefined. That is the first
thing to fix on the day the data arrives.
