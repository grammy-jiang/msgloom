# Topic 02 post-Round-2 gap-review decision

## Purpose

This is the required project-value review after Academic Round 2 and before any engineering validation. It does not alter the historical Round 1 or Round 2 gap-classifier artifacts and does not approve production architecture.

Academic Round 2 completed with the recovery runner `a504cd060ba4`. The fresh independent reviewer accepted the repaired report with faithfulness 0.99, coherence 0.97, gap completeness 1.0 and citation integrity true. Strict validation passed. The runner then classified 20 remaining gaps: 5 Academic, 13 Engineering and 2 Out-of-scope.

The gap classifier's `should_continue=true` is advisory academic convergence logic, not a project decision to start Round 3.

## Project-value decision

### Do not start Academic Round 3 now

The remaining Academic gaps are real but no longer justify another broad literature round at this stage:

- **G1-A — retain, conditional academic gap.** Round 2 strengthened discontinuous representation/prediction evidence but did not supply task-matched direct-email concrete-Topic evaluation. The next decision-relevant evidence should come from lossless representation and synthetic/public benchmark work (G7-E, G9-E, G2-E2). Reopen academic search only if candidate methods still fail a specific non-contiguous case.
- **G2-A — retain, conditional academic gap.** Same-span multi-label and overlap mechanisms now have transfer evidence. The important unknown is whether msgloom can represent and evaluate set-valued Topic assignments correctly. Do G7-E/G2-E2 first; reopen literature only for a concrete method deficit.
- **G3-A — retain, conditional academic gap.** Round 2 added stronger omission/coverage/atomic-content evaluation mechanisms but still no direct-email decision-bearing loss rate. The most useful next evidence is a msgloom preservation benchmark (G3-E), not another broad search.
- **G4-A — retain and defer production-domain closure.** No task-matched modern business/work-email Topic-span benchmark was admitted. More broad search is unlikely to substitute for future user-reviewed production-domain validation. Synthetic/public engineering validation can proceed without waiting for production data.
- **G5-A — stop active pursuit.** D05 provenance remains opportunistic only. One DNS failure is not source absence, but this supporting provenance item is not important enough to block Topic 02.

### Transfer out of Topic 02

- **G10-A and G10-E → Topic 03.** Concrete work-matter identity/count across threads or Sources belongs to cross-thread Topic continuity, not within-message segmentation. Do not duplicate it here.
- **Semantic response/agreement scope within G8-E1 → Topic 04.** Topic 02 keeps assignment/context-completeness behavior only.
- **General calibration/selective-prediction methodology within G8-E2 → Topic 10.** Topic 02 keeps assignment-specific uncertainty/abstention plumbing only.

## Engineering work to do now

### Core engineering-validation programme

1. **EV1 — G7-E: lossless Topic representation.** Prove round-trip support for discontinuous spans, overlapping/shared spans, multiple Topic memberships, stable object identity, explicit alternatives and abstention.
2. **EV2 — G9-E: annotation-unit comparison.** Compare sentence, clause, EDU-like, arbitrary-span and hybrid representations. Separate representational ceiling from predicted-unit quality.
3. **EV3 — G2-E2: set-valued Topic assignment.** Evaluate exact span-to-Topic memberships, overlapping memberships, non-contiguous Topic objects and whole-message label sets as separate outputs.
4. **EV4 — G3-E: decision-bearing preservation.** Measure lost conditions, exceptions, deadlines, approval constraints, evidence and scope; include false-positive predicted spans in denominators.
5. **EV5 — G8-E1: incremental context/correction.** Test assignment changes when context arrives later, preserve versions/retractions, and avoid semantic response-scope claims reserved for Topic 04.
6. **EV6 — G8-E2: uncertainty/abstention.** Use independent calibration/held-out synthetic strata, explicit coverage/error denominators and review recovery; defer general calibration method selection to Topic 10.
7. **EV7 — G4-E: domain-transfer harness.** Use synthetic/adversarial and legally/publicly usable work-message evidence where available. Production representativeness remains deferred.

### Supporting engineering audits

- **G1-E:** inspect existing annotations/artifacts where available for message-local offsets, within-message recurrence, authored-only versus quoted-inclusive denominators. Synthetic gold must remain independently authored.
- **G2-E1:** inspect how multi-membership gold is reduced into pairs/clusters/decoder outputs and how scorers treat overlap.
- **G6-E1:** document executable scorer definitions, populations and denominators for any baseline actually used.
- **G6-E2:** document dataset/version/split/duplicate controls for any public data actually used.

### Conditional/deferred engineering

- **G6-E3:** only after a concrete external method is selected for reproduction.
- **G8-E3:** Raspberry Pi 5 performance only after correctness/preservation/uncertainty behavior is established.
- **Production-domain validation:** future, when suitable user-reviewed data becomes available; it is not a blocker now.

## Methodology inherited from Topic 01

Engineering validation must start with these gates:

- synthetic gold is authored independently of the component being evaluated;
- end-to-end metrics include unmatched/false-positive predictions, not only gold-aligned predictions;
- incremental evaluation cannot use future context; full-context diagnostics are named separately;
- set/span matching must be one-to-one or explicitly set-valued and protected by mutation tests;
- experiment execution status and independent review acceptance are separate machine-readable concepts;
- rejected independent reviews are preserved and repaired, not bypassed;
- production representativeness, architecture approval and literature exhaustion are never inferred from synthetic success.

## Stop rule for Topic 02 current stage

Topic 02 can be closed for the current stage only after Academic Round 2 remains immutable, the actionable engineering programme above has reproducible synthetic/public evidence, a fresh independent methodological reviewer accepts it, and every remaining item is either conditional on method selection, future production data, later hardware work, or an explicit Topic 03/04/10 handoff.
