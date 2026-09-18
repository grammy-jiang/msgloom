# msgloom — Architecture Design

**Status: a hypothesis, and labelled as one.** `[07: gap-8]` is explicit that no
admitted study validates a single controller jointly handling structured gaps,
version lineage, temporal validity, calibrated stopping and abstention. Topic 06,
Topic 07 and Topic 10 each say that no production architecture was approved by
their research. **This document composes supported modules into a design. It does
not claim an evidence-validated end-to-end reliability framework**, and blueprint
§21 forbids claiming one.

**This is a stage output, not yet a design document.** `docs/architecture.md` and
`docs/design.md` remain authoritative. §14 below lists what would be carried into
them, and that carry is a separate step the owner approves.

**Inputs.** Blueprint §11, §13, §14, §21 and R1–R3 in §22; the decision register
D-0 to D-23; the approved Topic definition; and R-A to R-M in the security
review.

---

## 1. What this stage was handed, and what was left

Blueprint §21 deferred four decisions to this stage. **Three were settled before
it began**, and the blueprint now records them as inherited. One was open.

| Deferred | State on arrival |
| --- | --- |
| The permission mechanism | **Void.** Withdrawn 2026-09-17; no permission-aware retrieval component is built |
| How a Topic identity is made stable | **Settled** by D-12 and D-20 |
| The provenance address format | **Settled** by D-6 — but see §9, which is not the same question |
| Where the derived current-state projection lives | **Open.** §2 answers it |

---

## 2. The Current view — blueprint §21's open decision

Blueprint §14 records a concept the project has never named: Topic 06's *derived
current-state view*, the thing that is recomputed and never stored as truth. Its
neighbours all map to project terms; this one does not. **It needs a name before
a data model can be fixed, because without one every consumer invents its own.**

> **Current view.** The present-time state of one Topic, derived from the
> accepted stage results that concern it. It is computed, never received and
> never saved as truth.

It is not the report's *Overview*, which is a section of a delivered report.
The Current view is the computation an Overview is rendered from.

### 2.1 Where it lives

**It is not a new component and not a new store.** `docs/architecture.md §8`
already defines the Report interface as *read accepted topic information and
build a saved report*. **Reading accepted topic information is exactly this
computation.** The Current view is therefore what the Report interface reads, and
it is owned by the Application.

### 2.2 The five properties that make it safe

| | Property | Why |
| --- | --- | --- |
| 1 | **A pure function** of the accepted stage-result versions, the Topic record and the configuration version. Same inputs, same output | It can be recomputed at any time, which is what "never stored as truth" requires |
| 2 | **Cacheable only as a disposable artifact**, keyed by the exact input versions. A cache miss is always recoverable by recomputation | A cache that cannot be discarded has become truth |
| 3 | **Exactly one implementation** | `DP-07`. If the email adapter and the website each compute the current state of a Topic, the product has two answers and no way to say which is right |
| 4 | **Every report records the versions it was computed from** | `DP-02`. A report stays reproducible after later evidence changes the view |
| 5 | **A report saves the view it was built from** | `design.md §1` already defines a Report as a saved selection. Without this, reopening an old report recomputes it against today's evidence and silently rewrites history |

### 2.3 What it is the right home for

Three things that must happen once rather than per surface:

- **D-7's distinction.** Whether a completion was claimed or corroborated is
  applied here, so no report format can flatten it.
- **§3.3's three outcomes.** CONTINUE, NEW and UNCERTAIN become reader-visible
  here.
- **D-22's re-evaluation.** Whether a matter still passes the admission test is a
  property of the current working context, not a fact stored on a message.

---

## 3. The Topic data model

From the approved definition. **Field types, encodings and storage are still
absent**; this is the shape, not a schema.

### 3.1 Identity, held apart from description

`§3.4` requires a persistent identifier separate from the mutable description.
The architecture makes that a hard split, because `§3.6` and `§3.8` record a
drift loop that runs through the description.

| Part | Contents | May the model write it? |
| --- | --- | --- |
| **Persistent identity** | The identifier that survives every rename, merge and reopen | **No** |
| **Identifier fields** | Invoice, deal, ticket key, contract reference. Multi-valued | **No** |
| **Mutable description** | Name, short description, keywords | **Yes** |
| **Accumulated membership** | Participants, organisations, time window | Proposed, then adjudicated |

**The two "no" rows are the design's answer to drift.** `§3.8` states it
plainly: the identifiers are what holds the rest in place, and they are also the
fields the model cannot rewrite. Making that an access property of the store
rather than a convention is the architectural commitment.

### 3.2 The six elements

`§4`, approved 2026-09-18 with a revisit trigger. **The owner expects to add to
this list after using the product, so adding an element must be cheap.** That is
a constraint on the storage choice, not a remark.

| Element | Shape |
| --- | --- |
| **People** | A role in this matter — asked, owes, decides, watches — not an address |
| **Time** | Four kinds: happened, due, last learned, last assessed |
| **Action** | Two directions: owed by the owner, owed to the owner |
| **Background** | Claims, each with a citation (D-6) and an attribution (D-7) |
| **State** | new / open / resolved / superseded, with D-7 binding on `resolved` |
| **Identity** | §3.1 |

**Deadline time is the weak one**, and it is the half of IG8 that is still open.
The architecture must carry it as a first-class kind anyway, so that the gap is
visible rather than absent.

### 3.3 The edge set

`§6`, and `§6.1` for how it grows.

| Edge | Carries |
| --- | --- |
| Topic → Person | The role in this matter |
| Topic → Time | Which of the four kinds, and its source |
| Topic → Action | Direction, who owes it, its state |
| Topic → Evidence | Citation and provenance address — both, see §9 |
| Topic → Topic | **`supersedes` only** |
| Topic → Topic | **`member of`**, for D-11's subevent acted on separately |

**`member of` was confirmed by the owner on 2026-09-18 — D-24.** The approved
definition had contradicted itself: `§3.5` and `§7` Q-A both required a
membership edge, while `§6`'s table listed `supersedes` as the only
Topic-to-Topic edge. The owner resolved it in favour of the membership edge.
Without it a budget's five separately decided items become five unrelated
Topics, which is the outcome D-11's granularity rule exists to prevent.

**No third Topic-to-Topic edge is added**, and `§3.5` is not relaxed. An edge is
recorded where it is observed and is never chained from two other edges.

**No edge may be inferred from two other edges.** A relates to B and B to C does
not give A to C. This binds the consolidation pass in §7 and every retrieval path.

---

## 4. The anchor configuration

D-17 and D-18. **Anchors are owner configuration, so they load through the
Configuration component.** `docs/architecture.md §2` already requires it to
validate and to provide a fixed version per run, and `docs/tech-stack.md`
already requires it to reject unknown fields at startup.

| Property | Contents |
| --- | --- |
| Form | Deterministic — a pattern code evaluates. Or semantic — plain English the AI interprets |
| Kind | identifier · participant · organisation · temporal · content · artifact |
| Weight | Set per anchor |

**Configuration is instruction; a match is data.** D-2 puts the anchor definition
on the trusted side and the value it pulls out of a message on the untrusted
side. **These two live next to each other in the same record, which is exactly
where the distinction gets lost.** The architecture keeps them in separate
regions of the AI input envelope, which R-A already requires and R-B already
labels.

**The model never writes weights.** A model that could rewrite its own weights
from what it read in a mailbox would move configuration to the wrong side of
D-2's line.

### 4.1 The anchor health report

D-17's guard is a count, not a threshold. Per anchor, per run:

- how many distinct Topics it links
- how often its weight was what carried a pair over the verification level

**An anchor that is always the deciding vote is either the best one configured or
badly over-weighted, and only the count says which.** This is A5 output and needs
no new mechanism.

---

## 5. The pipeline — where D-19 and D-20 sit in A1 to A5

**One anchor extraction, used twice.** `§3.8` says the store query generalises
the bucketing step; the architecture makes that literal rather than parallel.

| Step | Stage | Who | Model call |
| --- | --- | --- | --- |
| Extract anchors from new messages | **A2** | Code | No |
| Bucket new messages that share an anchor | **A2** | Code | No |
| Query the Topic store with the same anchors | **A2** | Code | No |
| Score candidates by kind and weight | **A2** | Code | No |
| Adjudicate one group, or one Topic's candidates | **A3** | The AI | One per group |
| Group the residue by accumulating kinds | **A3** | Code | No |
| Test remaining residue against the admission test | **A3** | The AI | One per item |

**A2 produces candidates; A3 decides.** This keeps blueprint §11's contract
intact — group membership is evidence, never identity — and it keeps the whole
deterministic half free of model calls.

### 5.1 The asymmetry, made structural

**The AI may remove a member from a group. It may not add one**, because it never
sees outside the group. `§3.7` states this and the architecture must not quietly
relax it: the adjudication call receives exactly the group, and its output schema
has no field for a message identifier that was not in the input. **Validation
rejects an addition rather than trusting the model not to make one.**

### 5.2 Two failure modes with declared handling

| Failure | Handling |
| --- | --- |
| **A group above the configured size** | Not adjudicated. Reported as a probable anchor defect, with D-17's per-anchor count naming the likely cause. It is a limitation under D-1, not a silent skip |
| **Residue that grows run over run** | Reported. D-22 requires **new residue and standing residue to be counted separately**, or the ordinary backlog of passing mentions swamps the signal that the anchors no longer fit |

---

## 6. The Topic store

D-20, restated as what the architecture requires. **Selecting the technology is
a stack decision and is not made here.**

| # | Requirement |
| --- | --- |
| 1 | Exact lookup on multi-valued identifier fields |
| 2 | Similarity search over description and keywords |
| 3 | **It returns which fields matched, not only a score** |
| 4 | Versioned writes — `DP-02` |
| 5 | Unbounded growth — D-12 keeps every Topic, and D-22 keeps the standing residue |
| 6 | No access-control layer — one owner, no roles |
| 7 | Adding an element to §3.2 is cheap |
| 8 | **Typed edges with properties**, and one-hop queries in both directions |
| 9 | **Multi-hop traversal is not a default operation** |
| 10 | Adding an edge type is cheap |

**Requirement 3 is the one that rules designs out.** D-18 cannot apply its
no-stacking rule without knowing each match's kind, and the contextual wording
has to name what matched. A store that returns a bare similarity number is
insufficient, which excludes the simplest vector-only design.

**Requirement 5 now covers two things.** D-12 made Topics permanent. D-22 makes
the residue a standing set measured in months. Both grow forever and neither is
a leak.

**Requirements 8 to 10 are new, added 2026-09-18 with D-24 and D-25.** D-20's
seven requirements described the Topic record and said nothing about the edges,
because `member of` did not exist when they were written. §3.3's edge set is
where the relationships live, and a store requirement that ignores them is
incomplete.

**Requirement 9 states a prohibition as a requirement on purpose.** §3.5 forbids
inferring an edge from two other edges. A store that offers traversal as an
ordinary query makes that prohibition a matter of discipline; a store that does
not offer it makes the prohibition structural. **The difference matters most in
the consolidation pass**, which runs unattended.

**Against over-building:** at one person's mailbox scale lexical matching may be
enough, and `DP-10` says avoid custom infrastructure. This is a real choice with
evidence on both sides, and it belongs to stack selection — see D-25, which the
owner opened on 2026-09-18.

---

## 7. The consolidation pass

D-23. **One new Operator CLI subcommand, launched by the External scheduler that
`docs/architecture.md §2` already defines. No new component.** It is A4 work and
Phase 2 by the roadmap's existing allocation.

Its permitted operations, its five inherited rules and its new sixth rule are in
proposal `§6.1` and are not restated here. Three architectural consequences are:

1. **Rule 6 is a testable property, not a guideline.** *No new source evidence,
   no change* makes the pass idempotent on a quiet mailbox. The acceptance case
   is: run it twice with no mail in between, and the second run writes nothing.
2. **It reads the Current view and writes stage results.** It never edits a Topic
   in place, so §2's property 1 continues to hold after it runs.
3. **A pass that changed anything is visible in the next report.** `§5`'s second
   obligation already requires a split to be reported; a merge is the same
   obligation in the other direction.

### 7.1 The Phase 1 requirement this creates

**The pass is Phase 2. The storage it depends on is Phase 1.**

Phase 1 excludes joining independent groups by meaning, so the pass itself waits.
**But Phase 1 must retain the standing residue rather than discard it**, or there
is nothing for Phase 2 to re-examine and D-22's March message is gone. A Phase 2
capability creating a Phase 1 storage requirement is the kind of thing that is
cheap now and expensive later.

---

## 8. The error exchange rate — R1 to R3

Blueprint §22 requires the deferred cost function to have one home before anyone
types a placeholder. **The number is deferred; the place it will live is not.**

> **Error exchange rate.** How many over-broad links the owner accepts in order
> to avoid one missed obligation.

| # | Requirement | How the architecture meets it |
| --- | --- | --- |
| **R1** | One named setting, read at run time | A Configuration field. `docs/architecture.md §2` already gives Configuration a fixed version per run |
| **R2** | Every threshold derives from it rather than being set beside it | **A single derivation point.** No silent threshold is a configuration field of its own |
| **R3** | A change produces a new result version | No new mechanism. The exchange rate is part of the configuration version that every stage result already binds under `DP-02` |

### 8.1 Unset is legal, and it is what MVP-0 ships

**The setting has no value yet and must not acquire one by default.** An unset
exchange rate is a legal state meaning *surface everything*: no filtering, no
abstention, no threshold. That is what blueprint §22 prescribes for MVP-0, it is
the only configuration that needs no number, and it makes the counts the decision
needs observable.

**A default value would defeat the requirement it is meant to satisfy**, because
the first placeholder becomes permanent by accident.

### 8.2 R2 and D-18 conflict, and the conflict is resolved in D-18's favour

**R2 says every threshold derives from the exchange rate. D-18 sets a number by
hand and argues that it must be allowed to.** Both cannot be read literally.

D-18's argument is specific and correct: its verification level fails visibly in
both directions — too low costs model calls, which D-9 says are not a constraint
now, and too high shows a real link as context that the owner still reads.
**IG5's abstention threshold fails silently**, dropping an obligation nobody
learns existed.

> **The resolution.** The exchange rate governs every threshold whose error is
> **silent**. A threshold exempt from it must carry a written reason for why its
> errors are visible. D-18's verification level is the only exemption so far.

This keeps R2's actual purpose — that five numbers cannot be changed
independently — while honouring the one place the register argues an exception.

---

## 9. Two addresses, and deleting one would be a mistake

**D-6 resolved IG6. It did not remove R-C.** These are different addresses with
different readers, and a careless reading of "the address is the permalink"
deletes the internal one.

| | Citation — D-6 | Provenance address — R-C |
| --- | --- | --- |
| **Reader** | The owner | The system |
| **Contents** | The source system's permalink, plus a plain-text locator | Container path, extractor identity and version, trust class |
| **Purpose** | Open the original and look | Resolve a span back to bytes, and know how it was produced |
| **Printed in a report?** | **Yes** | **No** |

**Every extracted span carries both.** D-6 dissolved the problem of deriving a
stable external address, because the source system already issued one. It did not
dissolve `DP-02`'s requirement that a result be traceable to the extractor and
version that produced it, and it did not dissolve R-B's trust class.

---

## 10. The no-send construction — R-L and R-M

R-L requires that **no code path exists** by which a message reaches a recipient
other than the owner — not a flag, not a configuration. **A5 does deliver reports
by email, so this cannot mean "no mail client".** It means the destination can
never come from anywhere but configuration.

| | Construction |
| --- | --- |
| 1 | **Destinations come from configuration only.** No code path takes a destination from a source record, a parsed attachment, an AI output or a Topic field |
| 2 | **No Phase 1 output schema has an address-typed field.** Validation then rejects a destination the model tried to emit, because the schema has nowhere to put it |
| 3 | **Action adapters and the Action interface are absent from the package**, not present and disabled. `docs/architecture.md §8` already marks the Action interface Phase 4 only; D-4 makes that absence rather than configuration |
| 4 | **Source adapters expose no send operation.** The vendor clients for mail and chat have send methods; the adapter is where they are not exposed |

**Item 4 is the one most likely to be missed.** R-L is satisfied by what the
adapter does not expose, not by what the Application does not call. The check
belongs on the adapter's own surface.

**Testable criterion.** A build-time check that no module reachable from the
Application exposes or invokes a send operation, plus a test double in the
adapter layer that fails if a send method is reachable. `docs/phase-roadmap.md`
already requires this shape of test for Phase 3 — *a test double must detect any
attempted provider write*. R-L needs it in Phase 1.

---

## 11. The AI runner boundary

D-15 and D-16, and `docs/tech-stack.md` already specifies this to parameter
level. Restated here only for what the architecture must enforce.

| | Rule |
| --- | --- |
| **Phase 1** | A fresh session per attempt, no resume, `tools=[]`, no MCP, no inherited settings, a schema through structured output, and validation of payload and source coverage **before** a stage result is accepted |
| **Front doors** | A Skill, an MCP adapter or any agent-facing surface invokes and displays. **It never analyses.** Never two implementations |
| **Phase 2** | Tools are **granted** one by one in Python as bounded read operations, never inherited from the operator's environment. Credentials stay in the Application |

**`tools=[]` is what demotes an injection from able to act to able to lie**, and
the code then rejects the lie on schema and source coverage. This is the
security argument that decides the engine's shape, and it is why the pipeline in
§5 puts every model call inside the Application rather than in a front door.

**D-16's scope binding is unsolved and stays unsolved here.** How a Phase 2 read
tool is confined to the Topic under investigation rather than the whole database
has no answer proposed, and a read-only tool that can fetch any record is an
export channel. **It must be solved before Phase 2 begins.** §13 carries it.

---

## 12. What this stage does not decide

**Naming these matters as much as the decisions**, because a downstream stage
that assumes they were made will build on nothing.

| Not decided | Owner |
| --- | --- |
| The storage technology for §6, including whether relationships need a second engine | `tech-stack-selection` — **D-25, now triggered** |
| Every number — the exchange rate, the verification level, group size | Measurement, after MVP-0 runs |
| Screen layouts, copy and navigation | `ux-design` |
| Field types, encodings and identifiers | Implementation design |
| Exact subcommand names and exit codes | Implementation design, as `docs/architecture.md §7` already says |

---

## 13. Open problems carried forward

**None of these is downgraded to accepted.** Each is open, with who holds it.

| Item | State |
| --- | --- |
| **D-16 scope binding** | Open, no answer proposed. Blocks Phase 2 |
| **IG1** — what "already told the user" means | Open. D-12 constrains the answer: a Topic reopening after months must carry its history forward, so the force of having been told decays |
| **IG3** — attribution and accuracy on separate denominators | Open. Blocks every readiness claim |
| **IG4** — throughput, latency and peak memory | Open and unowned. Its original justification is void; the three measurements are not |
| **IG5** — the cost function | Open, deferred to measurement. §8 gives it a home |
| **IG7** — structured evidence a briefing must not flatten | Open |
| **IG8** — deadline time and the `gap-7` ablation | Open and narrower. §3.2 carries deadline time as a first-class kind so the gap stays visible |
| **IG10** — a failed abstention result never reached the methodology owner | Open |
| **Blueprint Q3 and Q4** | Need real mail. §5 makes Q3 an experiment rather than a hope |

---

## 14. What would be carried into the design documents

**This is a proposal for a later step, not a change already made.** The design
documents are authoritative and unchanged.

| Destination | What it would receive |
| --- | --- |
| `docs/design-brief.md §3` | No change. The Topic definition makes the brief's row operational without replacing it |
| `docs/design.md §1` | **Current view** joins the supporting concepts |
| `docs/design.md §4` | The anchor model, the three-stage pipeline, and the edge set |
| `docs/architecture.md §2` | The Topic store's place in Persistence; the consolidation subcommand |
| `docs/architecture.md §3` | Requirement 5 — the store and the standing residue both grow forever |
| `docs/architecture.md §7` | The no-send construction in §10 |
| `docs/tech-stack.md` | The store's seven requirements, as input to stack selection |
| `docs/phase-roadmap.md` | §7.1 — Phase 1 retains the standing residue |

**Both language versions change together.** The English documents are
authoritative and the Chinese ones are translations of them.
