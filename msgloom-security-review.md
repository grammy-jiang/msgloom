# msgloom — Security Review (design stage)

| Field | Value |
| --- | --- |
| **Artifact type** | security-review |
| **Project slug** | msgloom |
| **Stage** | Architecture-phase review of a design. **No code exists yet** |
| **Generated** | 2026-09-17 |
| **Trigger** | `IG11` — attachment security has no owner |
| **Sources** | `docs/design-brief.md`, `docs/design-principles.md`, `docs/design.md`, `docs/architecture.md`, `docs/phase-roadmap.md`, `docs/tech-stack.md`, `docs/phase-1/`, `msgloom-portfolio-blueprint.md`, `msgloom-integration-gaps.md` |

> This review does not own risk acceptance. It says what the risk is and what
> would reduce it; the product owner decides. It proposes no library and no
> scanner — DP-10 and the phase roadmap both treat technology selection as a
> later decision.

## Why this review exists

Ten research topics ran for months and **attachment security has no owner**.
Topic 08, which owns attachment understanding, marked it ❌ Missing in its own
coverage matrix. Topic 10, which owns evaluation methodology, marks "security
model ❌ Missing". None of the other eight picked it up.

## The headline

**IG11's judgement is right at the research level and overstated at the design
level.** The design documents already absorb most of attachment security — the
controls are spread across four files and none of them says "attachment
content is the adversary" in those words.

Verifiable: **`DP-09` appears exactly once in the design documents, at its own
definition.** `design.md`, `architecture.md`, `phase-1/design.md`,
`phase-1/architecture.md` and `tech-stack.md` never reference it. The controls
that enforce it exist; none declares that it is enforcing it.

**The single most important conclusion:**

> In Phase 1, DP-09's real enforcer is `tools=[]` — an injected instruction has
> nothing to call. That is the strongest control in the design and it is real.
> **But it protects actions, not interpretation.** Phase 1's only output *is*
> interpretation, and the product's first goal succeeds or fails there.

A line of text hidden in a spreadsheet cell that makes the interpreter believe
a matter is closed removes it from the report. `§16` of the blueprint already
records that a missed obligation has **no established detector** — `[10:
gap-5]`, "the project cannot measure this".

**Injection produces exactly the failure mode this product cannot detect.**

## Where DP-09 is actually enforced

| Enforcement point | Basis | Real? |
| --- | --- | --- |
| AI process has no tools | `phase-1/architecture.md §4`; `tech-stack.md §6` — `tools=[]`, `mcp_servers={}`, `strict_mcp_config=True`, and "verify effective SDK, CLI and managed settings rather than rely on a prompt restriction" | **Yes.** Structural, not a prompt constraint |
| Authority resolved by the Application, not by content | `design.md §6.1`, `§11`; `architecture.md §8` | **Yes**, at the caller boundary — **not inside the AI's input** |
| Approval boundary | `design.md §8.2` — AI cannot approve its own proposal; every external action needs explicit approval | **Yes** (Phase 4) |
| Parsers execute nothing and fetch nothing | `architecture.md §7`; `tech-stack.md` Parser selection — "must not execute macros, follow external document links or fetch remote resources" | **Yes.** Clearer than most production systems |
| Credential isolation | `phase-1/architecture.md §4` — parser workers get no credentials; the AI process gets model credentials only | **Yes** |
| Teams files go through authorised download, not parser URL access | `phase-1/design.md §2` | **Yes** |
| Injection testing | `tech-stack.md §9` lists `injection attempts` as a Phase 1 gate | **Named, no pass criteria** |
| **Channel separation between instruction and content** | — | **Absent. No document requires it** |
| **Trust labelling of attachment content** | — | **Absent** |

**What the existing controls have in common:** they all constrain what the AI
*can do* — no tools, no credentials, no network. **None constrains what the AI
*sees*.** That is F1.

### Why `design.md §5` does not cover this

§5 says semantic triage "cannot silently override deterministic constraints".
That binds **rule against rule**, not **content against interpreter**.

A deterministic rule can force an exclusion, a required priority, a minimum
priority or guidance. **It cannot force a topic to exist.** Whether a topic
exists, whether it carries an action, whether it has a deadline — all decided
by semantic triage. Injection never needs to override a deterministic
constraint; it works in the space where deterministic rules are silent, and
`design-brief.md §4` says that is the main space: "propose priorities for
topics the rules do not cover".

## Findings, by cost

### F1 — Attachment content enters the interpreter with no trust label · Phase 1 · HIGHEST

`phase-1/design.md §4.1` includes attachment content in the same triage input
as message body with no required distinction. `DP-04`'s "source statements
remain distinct from AI interpretation" separates **source from AI** — not
**trusted source from untrusted source**.

**Damage:** rewritten priority, forged deadline, suppressed topic. The last is
silent and unmeasurable.

**The design already contains the primitive.** `IG9` found that Topic 01 built
authored/quoted zoning and Topics 02 and 05 each re-opened it. It was filed as
a quality problem — quoted history producing false obligations. **It is also
the security primitive here.** One mechanism, two consumers.

**Requirement (testable):** the AI input envelope separates channels. The
instruction region is built only from configuration — prompt template, triage
rules, working-context snapshot. Every source-derived byte appears only in a
marked data region, each span carrying its trust class and its address.
**Test:** an xlsx with instructions written into a cell; assert no
source-derived byte appears in the instruction region and that the span is
marked attachment-derived.

### F2 — Provenance is a security primitive, and IG6 makes it unavailable · Phase 1 BLOCKER · reclassified

After extraction, **authored content and injected content are byte-identical.
The only thing that distinguishes them is the address.** No address, no
distinction, and therefore no downstream defence — F1's labelling, F6's
marking and F9's container paths all depend on an address existing.

`IG6` is currently filed as a quality and traceability problem, ranked 7th in
the register as an architecture-stage decision. **It is also a Phase 1 security
blocker.**

**Requirement:** an address carries, at minimum — source record identity,
observed version, **container path through nesting**, within-document
location, extractor identity and version, and **trust class**. The last two are
the security increment; `[08: gap-4]` does not name them. Schema is an
architecture decision.

### F3 — The vulnerability gate cannot see the code that parses the bytes · Phase 1

`tech-stack.md §7` already selects `pip-audit`, and pre-commit includes
Gitleaks. **The gap is narrower and more accurate than "no SCA":** pip-audit
sees PyPI package versions, not the native code that parses malicious bytes.

| What parses the bytes | Visible to pip-audit? |
| --- | --- |
| PDFium, vendored in a wheel | Only if an advisory names the wheel's package version |
| libxml2 / libxslt, vendored in a wheel | Same |
| **LibreOffice headless** — an optional deployment tool | **No. An OS package in the container, not in the lockfile** |
| Docling model assets | **No** |

**DP-10 cuts both ways here** and the review says so: for PDFium it is an asset
— continuously fuzzed by Chrome, patched fast. For a slow upstream it is a
liability.

**Requirement:** DP-10's "stable, actively maintained" becomes an admission
criterion — public security contact, observable patch cadence, hash-pinned
lockfile. Audit scope extends to the **container image layer** and vendored
native libraries. `tech-stack.md §2` already rechecks licences when locking
dependencies; **add CVEs to the same pass** — it is the cheapest route.

### F4 — Parser limits are named but unbounded, not OS-enforced, on a shared host · Phase 1

`phase-1/architecture.md §4` names time, memory, decompression and output
limits, with **no value, no enforcement mechanism, and no blast radius beyond
the worker**. `architecture.md §2` puts the AI runner "on the same host as
daily Claude Code".

A zip bomb or a declared 1M×16k used range exhausts 16 GB. **Two consequences:
the run dies (goal 1 — work is missed) and the user's own session is hit.**

**Requirement: limits must be OS-enforced** — cgroup memory, CPU rlimit,
wall-clock kill, output cap, expansion-ratio cap. A native parser spinning
inside libxml2 does not honour a Python timeout. The document's author knows
this — `tech-stack.md §6` says "terminate an isolated process before releasing
its claim" — it is simply not written as a parser obligation.

**Credit where due:** the design requires every file-level failure to become a
**recorded limitation** (`phase-1/design.md §2`, `§7`). That downgrades a DoS
from a silent miss to a visible gap. That is a correct call.

**A pattern worth naming:** `phase-1/architecture.md §4` says "process
isolation alone is not a complete security sandbox" and stops. **That is the
second time a document names a hole and does not claim it** — the first was
Topic 08's coverage matrix.

### F5 — XML external entities · Phase 1 · **corrected by measurement**

**The original finding was wrong in three ways and the corrections are more
useful than it was.** Measured on lxml 6.1.0 / libxml2 2.14.6 —
`research/security-probes/xxe_probe.py`, run 2026-09-17.

*What F5 originally said:* `defusedxml` appears in `tech-stack.md` Parser
selection only on the openpyxl line; DOCX goes through python-docx → lxml with
no protection; lxml's defaults resolve entities; therefore add defusedxml to
the Word path.

| Parser configuration | Reads a local file? | Network request? |
| --- | --- | --- |
| **Default** | **No — refuses, raises `XMLSyntaxError`** | No |
| `resolve_entities=False` | No | No |
| **`resolve_entities=True`, `no_network=True`** | **YES** | No |

**Correction 1 — the default is safe on this version.** lxml refuses the
entity outright, so "the Word path is exposed by default" does not hold today.
The risk class is real; the premise was not.

**Correction 2 — `no_network=True` is not protection.** This is the finding
worth keeping. Someone who enables entity resolution for a legitimate reason
and sets `no_network=True` will reasonably believe they are safe. They are
not: `no_network` blocks the network and does nothing about `file://`. A
`.docx` carrying a local-file entity reads that file into the extracted text,
and the extracted text goes to the model.

**Correction 3 — the recommended fix is being removed.** `defusedxml.lxml`
warns that it "is no longer supported and will be removed in a future
release". `defusedxml.ElementTree` still refuses the same bytes, so defusedxml
remains right for stdlib-ElementTree paths — which is what the openpyxl row
uses it for, correctly.

**Requirement, corrected:**

> Never set `resolve_entities=True` on a parser that touches source bytes. If a
> format genuinely needs entity expansion, that is a recorded decision with a
> reason, not a default. `no_network=True` is not a substitute. **Verify on
> every dependency upgrade** by running the probe — the current default is an
> observation about lxml 6.1.0, not a guarantee from lxml.

**This is why the requirement was always "disable *and verify*".** The
verification half turned out to be the whole of it: the thing to guard against
here is not a bad default but a well-meant override.

### F6 — An externally-effective field may come from an attachment, unmarked · Phase 3/4, with a Phase 1 consequence

**Credit first:** `design.md §8.2` binds actor, action type, destination and
content identity; changed content requires renewed approval; AI cannot approve
its own proposal; `§8.1` forbids inventing values to make a draft executable.

**The narrow gap is where the destination comes from.** A reply's destination
is derived deterministically and is safe. A task or ticket "identifies the
target system and **any known owner**" — and owner comes from extraction,
possibly from an attachment, possibly as Topic 05's third provenance kind,
`inferred_value`. The human gate exists, but the design does not require
showing that field's provenance. People review content and skim recipients.

**Requirement:** any externally-effective field — destination, recipient,
target system, amount, identifier — carries its provenance kind and trust
class, and the approval record binds them.

**Phase 1 consequence, needed now:** a proposal's evidence binding must include
the attachment's **observed version**, or `§8.1`'s "changed evidence marks an
affected proposal as needing revalidation" never fires when an attachment
changes.

### F7 — DP-04 and `[07: gap-4]` contradict each other · Phase 1 decision, Phase 2 effect

**No document had found this.**

`DP-04` makes uncertainty visible, unconditionally. `design.md §5` requires
every source record to map to a topic or an explicit disposition.
`phase-1/design.md §7` accepts a case where "the limitation appears in the
result **and report**".

Against: `[07: gap-4]` wants unauthorised candidates filtered "without leaking
that the filtered candidates exist", and the blueprint's `§12` names "we are
not allowed to tell you" as a reader-visible state **no design document
mentions**.

**A report saying "attachment 3/5 could not be read: access denied" discloses a
file the user may have no right to know exists.**

In Phase 1 — single user, own mailbox — disclosure is the correct default and
the risk is low. **The rule must be written now anyway**, or unconditional
disclosure gets hard-coded into every report template and Phase 2's leak-free
requirement becomes a rewrite.

### F8 — The report is an exfiltration channel, and no document says so · Phase 1 decision, Phase 2 amplifies

`tech-stack.md §3` renders to **escaped** HTML — scripting is covered, credit
given. But the parser line requires preserving "tables, **links** and
meaningful order", and no document decides how attacker-supplied URLs, remote
image references or autolinks are treated in a rendered report.

**Aggravating factor:** `design-brief.md §5` deliberately trains the user to
click through to original messages before approving. They are trained to follow
links from this surface.

**Honest calibration:** mail clients block remote content by default; single
user; corporate network. Real but limited in Phase 1. **Materially worse on the
Phase 2 Report website**, where rendering is entirely this design's and CSP is
free.

### F9 — Nested containers have no declared stopping point · Phase 1 rule, Phase 2 risk

Nothing declares that extraction stops at depth 1, or how a nested item
inherits scope. The current boundary is **accidental**: python-docx discloses
embedded objects as unsupported, so they are never expanded. Add embedded-object
extraction later and child items **inherit the grandparent's scope by
silence**.

**Requirement:** a maximum container depth, a total expansion budget, an
explicit scope-inheritance rule, and full container-path addressing. An item
beyond the depth is a **recorded limitation, not a silent drop** — consistent
with the design's existing habit.

## Requirements for the architecture stage

**Phase 1 obligations:**

| # | Requirement | Testable criterion |
| --- | --- | --- |
| R-A | AI input envelope separates channels; instruction region built only from configuration | Injection fixture: no source-derived byte in the instruction region |
| R-B | Every span carries a trust class — authored / quoted / attachment-derived / system | Envelope snapshot assertion |
| R-C | Provenance address includes container path, extractor identity and version, trust class | Every extracted span resolves back to bytes and a location |
| R-D | `resolve_entities` never enabled; **verified on every dependency upgrade** — `no_network` is not a substitute | `research/security-probes/xxe_probe.py` passes; a real `.docx` and `.xlsx` through the actual parser path |
| R-E | Parser limits OS-enforced — cgroup, rlimit, wall-clock, output cap, expansion ratio | Malicious fixture suite; host headroom preserved |
| R-F | Vulnerability audit covers the container layer and vendored native libraries; patch SLA in `§9` | Scope includes LibreOffice, PDFium, libxml2, model assets |
| R-G | Maximum nesting depth and explicit scope inheritance; over-depth recorded as a limitation | A depth N+1 file produces a visible limitation |
| R-H | Evidence binding includes the attachment's observed version | An attachment change marks downstream proposals for revalidation |
| R-I | Link and remote-resource policy for report rendering | No source-derived remote reference in rendered output |
| R-J | `§9`'s `injection attempts` gate gains pass criteria | Criteria stated, not merely listed |
| R-K | Disclosable classification for the four non-result states (F7) | Each state has a declared disclosure rule |

**Can wait:** Phase 2 website CSP and CSRF (`tech-stack.md §6` already defers
these correctly); A4 read-tool permission model; F6's approval trust class,
before Phase 3 starts.

## What this review does not worry about, and why

A review that flags everything is not useful. These are covered or out of
scope, with the reason.

| Item | Why not |
| --- | --- |
| XSS / CSRF | No web surface in Phase 1. `tech-stack.md §6` defers browser auth and CSRF to Phase 2 qualification — **a correct call; do not pull it forward** |
| SQL injection | "No handwritten application SQL" plus an ORM; configuration never executed as Python. Eliminated by construction |
| Command injection | `phase-1/architecture.md §2` — "use an argument list, never message content interpolated into shell commands" |
| Credential theft via attachment | Parser workers hold no credentials; the AI process holds model credentials only |
| AI self-escalation in Phase 1 | `tools=[]` — nowhere to escalate to |
| Excel formula evaluation, DDE, WEBSERVICE callouts | "Do not calculate formulas or execute macros" plus "parsing must not fetch URLs" |
| Self-ingestion loop — reports re-entering triage | `phase-1/architecture.md §4` uses stored identities and rule versions to prevent it. Already anticipated |
| Daily-memory poisoning | Memory mounts are read-only |
| Multi-tenant, PII, compliance | Single user, own mailbox, local storage. Encryption at rest is a host decision |
| Network exposure | None in Phase 1; the operations interface is local by default |
| ARM64 | A qualification risk, not a security one. Fewer prebuilt wheels means more source builds; a hash-pinned lockfile is sufficient and is already required |

## Two decisions for the product owner

Neither belongs to this review.

1. **F7 — must "authorization denied" be indistinguishable from "does not
   exist"?** A trade between DP-04 and `[07: gap-4]`. No practical cost in
   Phase 1; a rewrite cost in Phase 2 if decided late.
2. **F6 — should an externally-effective field derived only from attachment
   content block by default?** The review recommends blocking; it increases the
   human review burden in Phase 4.

---

## Product owner decisions — 2026-09-17

Recorded from the review session. These are the owner's, not this review's.

### D-0 — Security and privacy are the highest priority

> "This tool is going to read my own inbox so it definitely should be secure,
> safe, and also protect my privacy. This is the highest priority."

**This may amend `design-principles.md §2`.** That section currently makes user
permissions a fixed boundary and then orders correct meaning, traceability,
ease of use and speed within it. The statement above is broader than
permissions and sits above the whole ordering.

**Decided and applied 2026-09-17.** The owner authorised the change, and §2 of
`design-principles.md` (and its zh-CN counterpart) now states the priority
explicitly and carries two boundaries under it: the trust rule from D-2 and the
outbound rule from D-3/D-4.

### D-1 — An unreadable attachment is always reported, with its reason

**Answers F7.** Disclosure is the default, and the reason is stated whatever it
is — permission, corruption, unsupported format, size.

> "This is my private inbox. So I definitely have the privilege to know
> everything… you should mention if there's any attachment you can't read
> because of permission. Well, because of anything."

The realistic case is a OneDrive link whose owner forgot to grant access. The
report says so plainly.

**What this removes:** the leak-free requirement from `[07: gap-4]` does not
apply to this product's own mailbox, so no mechanism is needed to decide
whether the user may know a file exists. `R-K` narrows to "state the reason";
the four-state disclosable classification is no longer needed.

### D-2 — One trust rule, not an attachment-specific one

The review framed this as attachment security. **That framing was too narrow
and the owner corrected it:** anyone can send an email, so message bodies are
untrusted content by the same argument. Injection does not need an attachment.

> "Even in the content of the email, we still need to think about, like, the
> prompt injection."

**The rule, singular:**

> Every byte that came from a source is **data**. Only configuration — the
> prompt template, the user's triage rules, the working-context snapshot — is
> **instruction**.

`R-A` and `R-B` are unchanged in substance and simpler in scope: they apply to
all source content, and attachments are merely where the problem is most
visible. One rule is easier to implement and harder to bypass than two.

### D-3 — Content may go to the model; credentials and outbound sends may not

**Accepted:** message and attachment content is sent to Anthropic for
interpretation. That is how the product works, and `tech-stack.md` already
records it as an explicit service exception rather than leaving it implicit.

**Refused, and this is a new constraint:**

> "It shouldn't automatically send email or my credentials to someone else."

| | Allowed |
| --- | --- |
| Content to the model, for interpretation | **Yes** |
| A report delivered to the owner's own mailbox | **Yes** — this is the product |
| Any message to any other recipient | **No, not automatically** |
| Credentials leaving the process that holds them | **No, ever** |

The design already separates credentials — parser workers receive none, and the
AI process holds model credentials only. **The outbound-send constraint is the
new part**, and it is stronger than the phase roadmap alone implies: Phase 4
exists to execute approved external actions, and this says no such action
happens without the owner, ever, by any path.

### D-4 — Nothing is sent at all, for now

> "Currently, I do not want to send anything."

Read as: no external business action of any kind in the current scope. This
matches Phase 1 and Phase 2 as written — Phase 3 produces drafts only, Phase 4
executes — and makes it a stated constraint rather than a consequence of
sequencing.

**Design obligation:** there must be no code path that can send, not merely no
configuration that does. A disabled feature is one flag away from an enabled
one.

### D-5 — Attachment-derived recipients: deferred to Phase 3

F6's question — should a recipient read out of an attachment be blocked by
default — is **out of scope now** and the owner was right to say so. Phases 3
and 4 are two phases away and no research topic covered them.

The Phase 1 half of F6 needs no new work: `DP-02` already binds each stage
result to its inputs and versions, and `design.md §2` already requires an
attachment's observed version to be preserved.

**Revisit before Phase 3 begins.**

## What changes in the requirements

| # | Change |
| --- | --- |
| R-A, R-B | Scope widens from attachments to **all source content**. Substance unchanged |
| R-K | Narrows to "state the reason an item could not be read". The disclosable classification is dropped — D-1 settles it |
| **R-L** | **New.** No code path exists by which a message reaches a recipient other than the owner. Not a flag, not a configuration — no path |
| **R-M** | **New.** Credentials never leave the process holding them, and no source-derived value can name a send destination |

R-D (XML entities disabled and verified in every parser) is unchanged and is
still the cheapest item on the list.

## Correction to how IG11 and IG6 are ranked

`msgloom-integration-gaps.md` ranks IG11 fifth and IG6 seventh, as an
architecture-stage decision.

- **IG6 is promoted to a Phase 1 blocker** — F2. It is the precondition for
  every defence IG11 needs.
- **IG9 and IG11 merge for handling.** The same zoning primitive serves two
  consumers: false obligations from quoted history, and injection labelling.
  This adds no work; it lets three registered items share one mechanism.

**IG11 now has an owner.** R-A through R-K are its content.
