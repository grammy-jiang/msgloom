# Inherited handoffs

Everything an earlier Topic explicitly handed to this one, copied in full so
that this folder is enough on its own. You do not need to open an earlier
Topic's documents to start work here.

Each entry states what was handed over, what the sending Topic still owns, and
what it had established or left open at the time. A handoff is not a finding:
where the sender left a gap open, it is still open.

## From Topic 03 — Cross-thread Topic identity and incremental continuity

*Completed 2026-09-16. 4 rounds, 50 papers, report validated PASS 0.94. Seven
gaps left open.*

**Handed to Topic 07.** When the available material does not settle whether
two messages concern the same work matter, what should be retrieved next.
Topic 03 records this as an open ENGINEERING gap (MEDIUM): the operational
strategy for Phase 2 evidence seeking is unresolved.

**Boundary.** Topic 07 owns turning an unresolved identity question into a
targeted evidence need. Topic 03 keeps ownership of what counts as continuity
once the evidence arrives, and of the cost of a false merge against a false
split.

## From Topic 04 — Reference resolution and response scope

*Completed 2026-09-16. 4 rounds, 47 papers, report validated PASS.*

**Handed to Topic 07.** The case where a reference has **no resolvable
antecedent in the available material**. Topic 04's guidance is explicit: when
missing context is the real problem, that is an evidence need for Topic 07,
not a reference-model failure.

**What Topic 04 does with it.** It leaves the reference marked unresolved
rather than forcing a link, so Topic 07 receives an explicit
missing-antecedent signal rather than a wrong answer. Preserving that
distinction is deliberate: an invented link is more damaging than an admitted
gap.

**Boundary.** Topic 04 owns what the reference means once the material exists.
Topic 07 owns deciding what to fetch and stopping when enough has been
fetched.

## From Topic 05 — Action items, requests, commitments and decisions

*Completed 2026-09-16. 4 rounds, 48 papers.*

**Handed to Topic 07.** A missing owner, object or context becoming an
explicit retrieval need. Topic 05's uncertainty-preserving output leaves
owner, deadline, condition or act subtype **unresolved** rather than guessing,
which is its open engineering gap G9; each unresolved field is a concrete
evidence need for Topic 07.

**Boundary.** Topic 07 owns deciding what to fetch and when to stop. Topic 05
owns what the field means once the evidence arrives.

## From Topic 06 — Work-item state, event factuality, time, conflicting revisions

*Completed 2026-09-17. 4 rounds, 38 papers, no duplicate records. Every
round's synthesis was accepted by the independent review at the first attempt
— faithfulness 0.93 to 0.95 — which no earlier Topic managed. Stopped on
`round_cap_reached`. All eight gaps remain open and none was downgraded.*

**Handed to Topic 07.** An unresolved state becomes an explicit
missing-evidence requirement. Topic 06's report names this directly: evidence
retrieval should be evaluated jointly with state resolution "so unresolved
states can emit explicit missing-evidence requirements to Topic 07 rather
than hallucinating closure".

**What Topic 06 established.** Separate literatures cover factuality,
temporal ordering, commitment lifecycle, provenance and conflicting evidence,
and each works in its own setting. None of them was shown to work jointly.
An unresolved state is therefore the expected output, not a defect, and the
honest response to one is to ask for evidence rather than to guess.

**What Topic 06 left open, and Topic 07 must not treat as settled:**

- *(ACADEMIC, HIGH, Gap 3)* No joint evaluation of factuality, temporal
  ordering, lifecycle state, contradiction and provenance in one model.
  Component success does not establish integrated correctness.
- *(ACADEMIC, HIGH, Gap 5)* Nothing distinguishes a *claimed* completion from
  an independently corroborated one. A retrieval request built on a claimed
  state may be asking about work that is not actually done.
- *(ENGINEERING, HIGH, Gap 7)* Message time, effective time, deadline time
  and collection/version time have never been benchmarked together. A
  retrieval scoped by the wrong clock returns stale or retroactive evidence.

**Boundary.** Topic 07 owns deciding what to fetch, in what order, and when
to stop. Topic 06 owns what the state *is* once the evidence arrives, and
owns saying that it is still unresolved.

*Basis: Topic 06's report names Topic 07 explicitly (Future Directions 6);
the gaps are quoted from its Research Gaps table.*

## From Topic 08 — Email, image, table and attachment understanding

*Completed 2026-09-17. 4 rounds, 53 corpus records — **52 distinct papers**,
because one study was admitted twice under two identifiers. Rounds 2 and 4
were each rejected once and accepted after one repair; rounds 1 and 3 passed
at the first attempt. Stopped on `round_cap_reached`. All eight gaps remain
open and none was downgraded.*

**Handed to Topic 07.** A retrieved document, attachment or workbook still
has to be interpreted, and the evidence inside it located precisely. Topic 07
owns deciding what to fetch and when to stop; Topic 08 owns what the fetched
artefact says and where in it the claim sits — which page, region, cell or
version.

**What Topic 08 established.** Document-VQA work localises evidence to pages,
regions and answer spans; spreadsheet work localises to sheets, cells and
formulas; version-oriented work demonstrates version recovery, evolving
-document citation and version-aware retrieval. Each works in its own
setting. None was shown to work as one pipeline.

**What Topic 08 left open, and Topic 07 must not treat as settled:**

- *(ACADEMIC, HIGH, gap-1)* No complete method maintains evidence provenance
  across successive workplace attachment versions. A citation into "the
  attachment" is not yet a citation into a known version of it.
- *(ACADEMIC, HIGH, gap-4)* No admitted paper validates one end-to-end
  provenance representation identifying attachment version, page, document
  element and region together. Topic 07 cannot assume a retrieved span
  carries a usable address.
- *(ENGINEERING, HIGH, gap-5)* End-to-end behaviour when extraction or
  grounding is unsupported, incomplete or wrong is insufficiently exercised.
  A failed extraction must be distinguishable from an absent answer, which is
  a stopping-criterion concern as much as an extraction one.

**Boundary.** Topic 07 owns the retrieval decision and its budget. Topic 08
owns interpretation and grounding of whatever comes back.

*Basis: Topic 08's report names Topic 07 explicitly; the gaps are quoted from
its gaps.json.*
