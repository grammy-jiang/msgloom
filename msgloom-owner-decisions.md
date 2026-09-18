# msgloom — product owner decision register

One row per decision the owner has made. This file is an **index**: it states
each decision in one or two sentences and points at where it is elaborated and
what it changed. It does not restate the reasoning.

**Why it exists.** The decisions were made across several review sessions on
2026-09-17 and 2026-09-18 and landed in five different documents. The
architecture stage needs one list.

| # | Decision | Date | Elaborated in |
| --- | --- | --- | --- |
| **D-0** | Security and privacy come first, above the whole decision order | 2026-09-17 | `docs/design-principles.md §2` — **applied** |
| **D-1** | An item that could not be read is always reported, with its reason | 2026-09-17 | `msgloom-security-review.md` |
| **D-2** | One trust rule: source bytes are data, only configuration is instruction | 2026-09-17 | `docs/design-principles.md §2`, `msgloom-security-review.md` |
| **D-3** | Content may go to the model. No message reaches anyone but the owner | 2026-09-17 | `docs/design-principles.md §2`, `msgloom-security-review.md` |
| **D-4** | Nothing is sent at all, for now — no external business action | 2026-09-17 | `msgloom-security-review.md` |
| **D-5** | Attachment-derived recipients: deferred to Phase 3 | 2026-09-17 | `msgloom-security-review.md` |
| **D-6** | A citation is the message's own permalink plus a plain-text locator | 2026-09-17 | `msgloom-integration-gaps.md` IG6 — **resolves IG6** |
| **D-7** | Record that a person made a claim; never report the claim as fact | 2026-09-17 | `msgloom-integration-gaps.md` IG2 — **resolves IG2** |
| **D-8** | The deployment target is x86 plus cloud services, not a Raspberry Pi | 2026-09-17 | below |
| **D-9** | There is no cost or token budget at this stage | 2026-09-17 | below |
| **D-10** | "Topic" must be defined explicitly. The owner is asking for help | 2026-09-17 | `msgloom-topic-definition-proposal.md` — **proposal delivered** |
| **D-11** | A Topic sits at the level at which an action is owed | 2026-09-17 | proposal §7 Q-A |
| **D-12** | A Topic is permanent. `resolved` stops reporting; it reopens as the same Topic and inherits everything | 2026-09-17 | proposal §7 Q-B |
| **D-13** | The system names a Topic; the owner may rename it | 2026-09-17 | proposal §7 Q-C |
| **D-14** | R-L and R-M confirmed: the send feature is not built, and credentials stay in their process | 2026-09-17 | `msgloom-security-review.md` |
| **D-15** | One Python core, several thin front doors. A front door invokes and displays; it never analyses | 2026-09-18 | below |
| **D-16** | Phase 2 investigation tools are granted and bounded, never inherited. Scope binding is an open problem | 2026-09-18 | below |
| **D-17** | Identity anchors are configured by the owner in a configuration file, not built into the product | 2026-09-18 | proposal §3.2.1–§3.2.4 |
| **D-18** | An anchor carries a kind and a weight. Same-kind matches do not stack; different kinds add | 2026-09-18 | proposal §3.2.3 |
| **D-19** | Code buckets by pattern, the AI adjudicates one group at a time, and the residue is first class | 2026-09-18 | proposal §3.7 |
| **D-20** | A Topic is stored as a set of attributes and matched by a combined exact and fuzzy query that reports which fields matched | 2026-09-18 | proposal §3.8 |
| **D-21** | The Topic definition §§1–6 is approved, with the two amendments below | 2026-09-18 | `msgloom-topic-definition-proposal.md` — **approved** |
| **D-22** | A Topic can form because evidence accumulated over months, not only because the owner's context changed | 2026-09-18 | proposal §2.1 |
| **D-23** | A scheduled pass maintains Topic relationships. It deletes nothing, and it changes nothing without new evidence | 2026-09-18 | proposal §6.1 |
| **D-24** | There are two Topic-to-Topic edges: `supersedes` and `member of` | 2026-09-18 | proposal §6 |
| **D-25** | Relationship storage is a named stack decision. The owner proposes a graph database. **OPEN** | 2026-09-18 | below |

---

## D-8 — The deployment target is x86 plus cloud services

> "I'm not going to run this project on my Raspberry Pi 5. I'm going to run this
> project with Claude Code or Codex or GitHub Copilot on an x86 machine using
> the cloud service."

**The design documents never assumed a Pi**, so nothing in `docs/` changes. The
assumption lived only in the research record, where two topics deferred work
because of it:

| Where | What it said | Now |
| --- | --- | --- |
| Topic 01 `CURRENT_STATUS.md` | "E6 Raspberry Pi performance: after candidate correctness/preservation is established" | **Void.** E6's premise is gone |
| Topic 02 `CURRENT_STATUS.md` | "Raspberry Pi performance: deferred until correctness/preservation/uncertainty method selection is mature" | **Void**, same reason |

**Be careful what this does and does not license.** It removes an *arm64 and
16 GB* constraint. It does not make throughput and peak memory irrelevant —
`docs/tech-stack.md` still says to benchmark representative attachments on the
deployment hardware, and that sentence is already hardware-neutral. A parser
that needs 40 GB to open a spreadsheet is still a defect.

## D-9 — There is no cost or token budget at this stage

> "Currently there's no token budget, because I would like to make sure this
> project does work as expected and as it's designed. This is the most important
> thing at the beginning."

**This answers half of the blueprint's Q5** — cost had no owner because at this
stage it has no claim on the design.

**It does not lift IG5 or change R1–R3.** Those are about the *cost of being
wrong* — how an over-broad link trades against a missed one — which is a
question about the product's output, not about spend. D-9 is about spend. The
two are unrelated and IG5 stays deferred to measurement on its own terms.

**What it does change:** no design choice may be justified by token savings at
this stage. `design-principles.md §2` already ranks speed, brevity and token
saving last; D-9 says that for now they carry no weight at all.

## D-10 — "Topic" needs an explicit definition — OPEN

> "The topic is a key concept in this project and I think we should figure out a
> way to explicitly define it… I don't have a clear idea now. I definitely need
> your help. And this is very important."

The owner's working description, recorded in substance:

- a Topic is something **the owner needs to know about or act on**
- it is **self-maintained**
- it has a **time**, an **action**, the **people involved**, and **background**
- summarising a mailbox produces **many** Topics, and the product must then
  relate Topics to **people**, to a **timeline**, and to the **actions** owed

**This is not a research gap.** It is a definition the product cannot be built
without, and it is now the largest open item in the programme. It supersedes the
narrower "Topic identity must be stable across runs" note, which is one
consequence of it.

**Status: closed 2026-09-18.** The proposal was delivered on 2026-09-17 in
`msgloom-topic-definition-proposal.md`; its four open questions were settled the
same day (D-11, D-12, D-13, and one design default); and **§§1–6 were approved
on 2026-09-18 — D-21**, with the two amendments recorded as D-22 and D-23.
The product's central concept now has a definition the architecture stage can
fix a data model against.

## D-15 — One Python core, several thin front doors

**The question.** Should msgloom be a Skill that an AI agent runs, or a Python
program that calls an AI agent for the language work?

**The answer was already in the design documents**, and the owner's instinct
that it might be both was right about the shape.

### What was already decided

`docs/tech-stack.md` specifies the second form down to its parameters: a fresh
`query()` per analysis attempt with no resume, `tools=[]`, `mcp_servers={}`,
`strict_mcp_config=True`, `setting_sources=[]`, no inherited hooks or plugins, a
Pydantic schema through the structured-output interface, and validation of the
payload and source coverage **before** a stage result is accepted.

`docs/architecture.md` already provides for more than one front door: an Operator
CLI launched by an External scheduler that lives outside the package, a Report
website, and a future MCP adapter — all sharing one Application interface.

### The decision

> **The Python Application is the engine. A Skill, an MCP adapter or any other
> agent-facing surface is a front door over it. A front door may invoke an
> operation and display its result. It may never perform the analysis.**

**Never two implementations.** Two implementations mean two trust models and two
provenance records, and `DP-02` breaks immediately.

### Why the engine cannot be the Skill — the security argument

The two forms differ in **where untrusted message content lands**.

| | Where content enters | What a successful injection achieves |
| --- | --- | --- |
| **Python core calling the AI** | A single-use session with `tools=[]`, no MCP, no inherited settings | **At worst a wrong analysis**, which the code then rejects on schema and source coverage |
| **A Skill doing the work in the agent's loop** | The operator's own agent context — file writes, shell, every MCP server they have installed | **Injection becomes action**, with whatever tools happen to be present |

`tools=[]` is what demotes an injection from *able to act* to *able to lie*.
This follows directly from D-0 and D-2, and it protects R-L: the operator's own
environment may well contain a tool that can send mail.

### The residual risk, stated honestly

A front door that displays a report brings quoted message content into an agent
context. **Reduced, not eliminated**: a front door should return a path and a
structured summary and leave the full report to be read by a person. Only the
core's `tools=[]` boundary eliminates the risk for the analysis step.

### Order of work

1. **Build the core.** It is already specified to parameter level.
2. **Front doors are thin.** The shared Application interface already exists in
   the architecture for exactly this.
3. A Skill cannot run a scheduled job — it needs a live agent session. The
   External scheduler already covers that and needs no new work.

## D-16 — Phase 2 tools are granted and bounded, never inherited

> "Later, I still want the AI agent to do some investigation with the company
> internal legacy system or service… in the future we have to allow the AI agent
> to have some tools to work."

**This is planned work, not a reversal.** `phase-roadmap.md` names Phase 2
*investigation and review*, and `tech-stack.md` already says Phase 2 may expose
bounded Application read operations through the SDK's custom-tool support.

### The rule D-15's `tools=[]` actually expresses

**The action surface is decided by the Application, not by the environment.**

| | Where tools come from | Scope |
| --- | --- | --- |
| **Inherited** | The operator's agent environment | Unknown, and it changes whenever they install something |
| **Granted** (Phase 2) | Defined one by one in Python, each a bounded read operation the Application implements | Exactly what was written |

**This makes the Python-core shape more necessary, not less.** Bounded tools
cannot be granted from inside a Skill, because that context already holds tools
and can only be added to.

### Conditions on every Phase 2 tool

| | |
| --- | --- |
| **Read only** | Investigation reads. Writing is Phase 4 |
| **A specific operation** | `ticket_status(ticket_id)`, never `run_sql(statement)` or `fetch(url)`. A general-purpose tool is not a boundary |
| **Credentials stay in Python** | `tech-stack.md` already requires source credentials to stay out of the Claude Code process. The call returns to the Application, which holds the credential |
| **Arguments are validated** | Against the Application's own schema and scope, never taken as given |
| **Every call is recorded** | What was asked, what returned, which version. `DP-02` |

### The new risk, and why no new rule is needed

A person who can email the owner can influence **what gets queried**. The
two-hop form is worse: the message says *check record 999*, and record 999's
notes field carries the payload, which returns into the same context.

**D-2 already covers this without amendment.** *Every byte that came from a
source is data.* A legacy system's response is a byte that came from a source.

The rule was widened once already — the owner corrected this review for scoping
it to attachments when message bodies have the same problem. It now generalises
to internal systems with no further change, which is evidence the rule is drawn
at the right place.

### D-3 and D-4 do not block this

They govern **messages reaching a recipient**. A read-only query is not a
message to a recipient, so Phase 2 investigation and "nothing is sent at all"
do not conflict.

### OPEN — scope binding

**How is a tool confined to the Topic under investigation rather than the whole
database?**

"Read only" is not "reads only what it should". A tool that can fetch any ticket,
combined with a crafted message, is an export channel.

**No answer is proposed here.** To be solved before Phase 2 begins.

**Also to confirm at Phase 2:** these queries appear in the company's own logs
under the owner's name. Whether a volume of automated queries is acceptable is
an operational question, not a technical one.

## D-21 — The Topic definition is approved

The owner was asked to confirm §§1–6 of the proposal, and specifically the three
places where it went beyond what they had said: that Topic-ness is re-evaluated
rather than fixed, that their four elements were split into six, and that only
`supersedes` is modelled between Topics.

**All three were accepted, and two were extended** — the extensions are D-22 and
D-23. §§1–6 are therefore no longer a recommendation.

**What this unblocks.** Architecture design may now fix the data model. §4's six
elements, §6's edge set and §3.8's identity record are the shape it builds
against.

**What it does not settle.** The numbers. D-18's verification level and IG5's
abstention threshold are still unset, and §3.3 is explicit that MVP-0 ships
without them.

## D-22 — A Topic can be born from accumulation, not only from a change of context

> "The topic we learned from the email could be generated by time. For example…
> maybe something mentioned in March was just very small, tiny words. But three
> months later, in June, it becomes a real huge project."

**The proposal had one route into a Topic and the owner named a second.** Both
are re-evaluations; they differ in what changed and in what triggers them.

| Route | What changed | Trigger |
| --- | --- | --- |
| **Context** | The owner's working context | **A context change, with no new message** |
| **Accumulation** | The matter itself grew | New evidence |

**Three architectural consequences**, elaborated in proposal §2.1:

1. **Re-evaluation must run without new mail**, so *process what arrived* cannot
   be the only entry point. D-23's pass is the home for this.
2. **The residue is a standing set, not a queue that drains.** The March message
   has to survive until June, which makes residue retention a storage
   requirement measured in months.
3. **An admitted Topic's history starts at the first mention**, not at the point
   it was admitted, so its time window extends backwards.

**The accepted cost.** Residue grows. **The residue report must therefore
separate new residue from standing residue**, or D-19's trend signal is swamped
by the ordinary backlog of passing mentions.

## D-23 — A scheduled pass maintains the relationships

> "We may need to create a scheduled job to wash, clean up or wrap up the
> relationship regularly. It's kind of like building a knowledge database and
> regularly cleaning up the items inside to make the relationships between the
> items clearer."

**This is what makes `supersedes`-only safe as a starting point.** A relationship
that could not be decided when its evidence arrived is decided later, when more
of it has arrived.

**No new component.** `phase-roadmap.md` already puts *Topic relationships across
independent groups and sources* in **Phase 2, A4**, and `architecture.md §2`
already has an External scheduler that owns recurring triggers and launches an
Operator CLI subcommand. This is one more subcommand, so `DP-10` needs no
argument.

### The rules that bind it

Five already exist. **The sixth is new and is the reason this decision needed
more than a yes.**

| | Rule | Source |
| --- | --- | --- |
| 1 | It deletes nothing. A merge keeps both histories and the absorbed identifier still resolves | D-12 |
| 2 | It does not lower the bar for merging | D-18 |
| 3 | It may not infer an edge from two other edges | proposal §3.5 |
| 4 | It may not flip a Topic to `resolved` on a source's claim | D-7 |
| 5 | Every pass is a versioned stage result, and a pass that changed anything is visible in the next report | `DP-02` |
| 6 | **No new source evidence, no change** | **New** |

**Why rule 6.** The AI writes a Topic's description, the description retrieves
candidates, and the AI reads those candidates and updates the description. **A
scheduled job runs that loop on a timer with nobody watching**, and each pass
broadens the description slightly until distinct matters look alike. Rule 6 stops
it and makes the job idempotent on a quiet mailbox — run it twice with no mail in
between and the second run must change nothing, which is also the test.

### The Phase 1 requirement it creates

The pass is Phase 2, because Phase 1 excludes joining independent groups by
meaning. **But Phase 1 must retain the standing residue rather than discard it**,
or there is nothing for Phase 2 to re-examine. A Phase 2 capability creates a
Phase 1 storage requirement, and it is cheap now and expensive later.

## D-24 — Two Topic-to-Topic edges, not one

> "The five topics should remember where they come from."

**This resolves a contradiction inside the definition the owner had just
approved.** D-21 was put to them as *`supersedes` only*, which is what `§6`'s
table said. But `§3.5` and `§7` Q-A both required a subevent acted on separately
to carry a membership edge. Both could not be true.

| Edge | Means |
| --- | --- |
| **`supersedes`** | This Topic replaces that one — a revised contract against the one it revises |
| **`member of`** | This Topic is part of a larger matter and is acted on separately |

**Why the contradiction resolved this way.** D-11 splits a matter at the level an
action is owed. A Q3 budget whose five items are each approved separately becomes
five Topics. **Without a membership edge those five are unrelated**, and the split
has destroyed the thing it was splitting. That is the opposite of what D-11 is
for.

**No third edge.** Every other Topic-to-Topic relation runs into `§3.5`'s
non-transitivity and has no established workplace semantics.

**`§3.5` is not relaxed.** An edge is recorded where it is observed and is never
chained: A is `member of` B and B is `member of` C does not make A `member of` C.
This binds the D-23 consolidation pass, which runs unattended and is therefore
the most likely place for a wrong chain to be created.

## D-25 — Relationship storage is a stack decision — OPEN

> "I think we should introduce a graph database, like for the knowledge, knowledge
> storage. I think we haven't discussed this in the research topics, but when we
> try to build up this project, we will face this problem."

**The owner is right that this was never researched, and the observation is
confirmed.** None of the ten research topics covers storage. The design documents
parked it rather than answering it: `phase-roadmap.md` calls knowledge graphs and
vector databases "implementation options, not phase deliverables", and
`tech-stack.md §8` says none is selected **for Phase 1**. Parked is not decided.

**What is already selected.** `tech-stack.md` picks SQLite through an async
SQLAlchemy ORM as the Application database, and records that A4 needs no vector
database "by the logical contract". That contract was written before `member of`
existed.

### The real gap, which is separable from the engine

**D-20's seven store requirements describe the Topic record and say nothing about
the edges.** They were written before D-24. The edge set in `§6` is where the
relationships actually live, so the requirements were incomplete.

**That gap is closed now**, in `msgloom-architecture-design.md §6`, as three
added requirements: typed edges with properties and one-hop queries in both
directions; multi-hop traversal not available as a default operation; and adding
an edge type is cheap.

**Naming the requirement is not the same as naming the engine**, and the first is
what was missing.

### The argument the owner should weigh before deciding the engine

**A graph database's distinctive capability is multi-hop traversal.** `§3.5`
forbids exactly that operation: no edge may be inferred from two other edges.

| Query msgloom actually needs | Hops |
| --- | --- |
| What is `member of` the Q3 budget | **One** |
| What is this Topic a `member of` | **One** |
| Everything this person appears in, and in what role | **One** |
| Every Topic sharing this invoice number | **One**, and it is an indexed lookup, not a traversal |

**So the one thing that distinguishes a graph store is the one operation this
design prohibits.** A store that cannot traverse makes the prohibition
structural rather than a matter of discipline — which matters most in the D-23
pass, because it runs unattended.

**Three more costs of a second engine**, all from rules already in force:

1. `DP-10` — avoid custom infrastructure.
2. `architecture.md §3` requires the Application database and its referenced
   files to be **one recoverable set** for backup and restore. A second engine
   either joins that set or breaks the invariant.
3. `DP-02` binds every stage result to its input and configuration versions.
   Two write paths make that harder to keep consistent.

**And the honest case for it.** `§4` is approved with a revisit trigger, so the
element set is expected to grow; a schema-flexible edge store makes growth
cheaper. Against that, `§3.1` requires the model to be **unable** to write
identifier fields, and a schema enforces that where a convention does not.

### Recommendation, and what settles it

**Recommended: one store, extended, unless a measured query need forces a
second.** That is `DP-10` applied, and it matches how this programme settled IG5
and Q1 — by measurement rather than by intuition.

**What would change the recommendation:** a query the product genuinely needs
that cannot be answered in one hop. **If one exists, it is worth more than this
whole argument**, because it would also mean `§3.5` needs revisiting.

**Status: OPEN.** The owner's position is recorded above. This is theirs to
decide, and `tech-stack-selection` is the stage that carries it. It is now
triggered, because architecture design is complete.

## D-17 — Anchors are configured, not built in

> "In the real world it can be like the number of the deal, or a certain name of
> a product, or even just a certain request to approve these kinds of things. So
> the anchors should be configurable, and the user can edit them by a
> configuration file."

**The invoice number in the worked example was an illustration and was being
read as the design.** Every workplace anchors its matters on something
different.

**The decision reuses `DP-01` rather than inventing anything.** Anchors take the
same two forms the design already gives triage rules: **deterministic** anchors
that code evaluates as patterns, and **semantic** anchors written in plain
English that the AI interprets. Same configuration file, same trust model, no
new vocabulary.

**Three consequences are recorded in the proposal:**

1. **Configuration is instruction; a match is data.** D-2 puts the owner's rules
   on the trusted side. The anchor definition may steer behaviour; the value it
   pulls out of a message came from a source and stays data.
2. **A bad anchor is worse than no anchor**, and this is the real hazard
   configurability adds. A product name sold to everybody merges every matter
   that mentions it — Theme 2's high-connectivity failure by another route. The
   guard is a count, not a judgement: report how many distinct Topics each anchor
   links, and let the owner read the ranking. No threshold needed.
3. **Changing the anchors does not rebuild the past.** A new anchor is new
   evidence, which §3.4's repair mechanism already handles. The configuration
   version that produced a report is recorded, because changing anchors changes
   identity decisions.

**The system may propose an anchor it noticed; it never adopts one.** Adoption
is an edit to the owner's configuration file. Self-maintenance covers Topics,
not rules.

## D-18 — Every anchor carries a kind and a weight

> "I think we should have both category and also the importance score… only when
> it's from the same company and also the same people and maybe in the same
> period of time, then the signal becomes strong from weak."

**An earlier form of this decision, taken the same day, used three named levels
and no number. The owner judged it too coarse for real use and was right**; that
form is superseded rather than recorded separately, since it was never committed.

**Two properties per anchor, doing two different jobs.**

| Property | What it decides |
| --- | --- |
| **Kind** — identifier, participant, organisation, temporal, content, artifact | **Whether two matches may stack** |
| **Weight** — set per anchor, not per kind | How close a pair gets to verification |

### Why the kind is needed beside the weight

Theme 2 requires identity to rest on **independent** dimensions, and a plain
weighted sum does not know what is independent. *Same sender* and *same
recipient* look like two signals and are one — the same kind of evidence about
the same relationship. Counting both manufactures confidence.

**The rule:** matches of the same kind do not accumulate, the strongest counts;
matches of different kinds add. Theme 2's advice, expressed as arithmetic.

**Weights are per anchor because only the owner knows their workplace.** A
supplier name is weak among three thousand suppliers and strong among three.

### Two rules that override the arithmetic

1. **An identifier match reaches verification alone.** An invoice number does not
   hint at the same matter; it names it. This is the *deterministic* property the
   owner named.
2. **A hard contradiction vetoes**, whatever the total — the same invoice number
   against two different amounts. Theme 2's third finding, kept as a rule rather
   than a negative weight.

### What the total selects

Above the verification level the AI takes a deep look for *incompatible*
evidence and returns CONTINUE or NEW with its reason. Below it nothing merges,
and the wording **names exactly what matched** and scales with it — "you have had
other conversations with this person" and "the same supplier and the same three
people, within the same week" are different sentences. **Neither asserts
sameness**, which is D-7 again.

### The threshold objection, withdrawn with a reason

The earlier form avoided a number because a threshold needs IG5's cost function.
**That objection does not transfer**, and the difference matters:

| | If the number is wrong |
| --- | --- |
| **IG5's abstention threshold** | An obligation is dropped and nobody learns it existed. **Silent** |
| **This verification level** | Too low: more model calls, and D-9 says tokens are not a constraint now. Too high: a real link appears as context and the owner still sees it. **Neither is silent** |

So this number may be set by hand and tuned. It must not be confused with the
one that cannot be.

### Who computes what

Code matches anchors, applies the kind rule, sums weights and checks the two
overrides — deterministic and with no model call. The AI does the deep look and
writes the contextual wording. **Weights stay in configuration and the AI never
sets them**: D-2 puts configuration on the instruction side, and a model that
could rewrite its own weights from what it read in a mailbox would move
configuration to the wrong side of that line.

## D-19 — Bucket deterministically, adjudicate per group, keep the residue

> "We should use some deterministic ways to check this first… then I can send one
> group of emails to the AI agent, so the AI agent doesn't need to browse all of
> the emails at once… I may receive 100 emails and process them into three or
> four topics, and there are another 20 emails the AI cannot determine which
> topic they are talking on."

**Three stages: code buckets by identifier pattern, the AI reads one group at a
time, and whatever no bucket claimed goes through its own cascade.**

### This is a correctness measure, not an optimisation

Topic 05 measured quality degrading as context grows, and blueprint Q3 asks
whether Topic-scoped retrieval avoids it. **This is Topic-scoped retrieval.** The
model reads ten related messages rather than a mailbox, which turns Q3 from a
hope into an experiment `[05: gap-7]`'s ablation can run.

A secondary benefit: an injected instruction can only affect its own group's
analysis. The blast radius is a group.

### The asymmetry that must hold

**The AI may remove a member from a group** — a shared invoice number in a
forwarded thread is a common false positive and only the AI can see it. **The AI
cannot add one**, because it never sees outside the group. A message the
bucketing missed stays missed at that stage, and the residue cascade exists
because of it, not in spite of it.

### The residue is where a missed obligation hides

Goal 1 is that nothing needing a response is missed, so the leftovers get a
cascade of their own: weak-signal grouping using D-18's accumulating kinds, then
individual presentation against the admission test — a message that owes
something is a Topic of one. **The residue count is reported every run. A
residue that grows is the system saying the owner's anchors no longer fit their
work.**

### Two failure modes named in the proposal

**An over-large group** puts back the context problem stage 1 removed. A group
above a configured size is not adjudicated; it is reported as a probable anchor
defect, and D-17's per-anchor count says which anchor caused it.

**Batch thinking.** "100 emails into 3 Topics" is the cold start. Steady state is
a few new messages joining Topics that already exist, so the design is
incremental — which §3.4's repair requirement already demands.

## D-20 — The Topic store, and a query that is exact and fuzzy at once

> "One topic should not have only one thing to query — it should involve the
> invoice number, deal number, Jira issue ticket number, the company's name, the
> receiver's name, and also a short description, and maybe some keywords… this
> query is more like a deterministic query and fuzzy query together."

**This generalises D-19's first stage.** Bucketing groups new messages against
each other, which finds matters that are new. Querying a store finds new evidence
for Topics that already exist — the ordinary case once the product has run for a
while. Both are needed and they are different operations.

### A Topic's identity record

Every field is multi-valued, because one matter genuinely carries several
identifiers. Each field maps to one of D-18's kinds, and this is the mutable
description §3.4 keeps separate from the persistent ID.

**Identifiers do not drift. The AI-written description and keywords do** — which
is Theme 6's hazard sitting inside the record. **The identifiers are what holds
the rest in place**, and they are also the fields the model cannot rewrite.

**A feedback loop to watch:** the AI writes the description, the description
retrieves candidates, the AI reads them and updates the description. Identifiers
always participating, plus a recorded derivation per description version, is what
keeps that drift visible instead of silent.

### Three layers that must not merge

The store returns **candidates with the fields that matched**. D-18's scoring
applies kinds and weights to those matches. The AI adjudicates when the total
warrants it. **Theme 1 requires this separation** — retrieval by similarity is
legitimate precisely because it only proposes.

### The requirement that rules designs out

**The store must return which fields matched, not only a score.** D-18 cannot
apply its no-stacking rule without knowing each match's kind, and the contextual
wording has to name what matched. **A bare similarity number is insufficient**,
which excludes the simplest vector-only design.

Also required: exact lookup on multi-valued identifier fields, similarity search
over text, versioned writes (`DP-02`), unbounded growth (D-12 keeps every Topic),
and **no access-control layer** — blueprint §6 withdrew the permission
partitioning challenge because there is one owner and no roles.

**Against over-building:** "fuzzy" invites a vector database, and at one person's
mailbox scale lexical matching may be enough. `DP-10` says avoid custom
infrastructure. **This is a real stack decision**, deferred to stack selection,
not a foregone conclusion.
