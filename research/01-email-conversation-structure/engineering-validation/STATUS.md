# Topic 01 engineering-validation status

## Final verdict for work that can be completed now

**ACCEPTED — E1–E4 synthetic/adversarial engineering validation complete.**

This acceptance is deliberately narrow:

- it accepts the research harness, fixtures, metrics, replay/uncertainty machinery, and the synthetic findings;
- it does **not** claim production-email accuracy or representativeness;
- it does **not** approve a msgloom production architecture or implementation;
- it does **not** close the retained A2/A7 academic gaps globally.

## Independent review history

1. **Review 1 — rejected.** It found circular extractor gold, omission of false-positive quote detections from attribution-error denominators, and narrower methodology/test issues.
2. **Review 2 — accepted_with_issues.** It independently verified the major repairs and found no invalid headline result, but requested stronger mutation regressions, removal of stale E4 narrative, and execution/review status separation.
3. **Review 3 — accepted.** Fresh `gpt-6-astra/high`, confidence 0.98, with zero blocking issues, zero nonblocking issues, and zero recommended fixes. It independently re-ran tests, regenerated artifacts in a temporary directory, performed targeted in-memory mutations, and verified the corrected metrics and boundaries.

The authoritative final reviewer verdict is `audit/independent-review-03/verdict.json`.

## What E1–E4 mean now

- **E1 — ACCEPTED_SYNTHETIC:** independent authored joint-gold fixture contract with adversarial metadata/content structures.
- **E2 — ACCEPTED_SYNTHETIC:** independent preservation gold, strict arrival-time end-to-end attribution accounting, conditional final-context diagnostics, and structural-vs-reuse detector comparison.
- **E3 — ACCEPTED_SYNTHETIC:** replay/history, duplicate-ID ambiguity comparator, parent/ancestry separation, occurrence-specific quote scoring, and removed-relation detection.
- **E4 — ACCEPTED_SYNTHETIC:** relation-specific confidence/abstention plumbing with disjoint calibration and held-out template families.

Machine-readable `results/metrics.json` intentionally describes **experiment execution**, not review acceptance. The accepted review is a separate audit artifact so those concepts cannot be conflated.

## Evidence-backed requirements for later candidate implementations

1. Do not collapse duplicate Internet Message-ID values to one message without preserving ambiguity/alternatives.
2. Do not equate text reuse with quotation identity or provenance direction.
3. Keep quote-occurrence detection separate from source matching and report both denominators.
4. Keep reply-parent, indirect ancestry, and quote-source relations independently representable/testable.
5. Preserve correction/replay history rather than silently overwriting earlier assessments.
6. Evaluate abstention by ambiguity/missing-source strata, not aggregate calibration alone.
7. Preserve decision-bearing content across extraction/normalization; independent gold must remain external to the component being tested.

These are research acceptance requirements for later design work, not edits to the project design documents.

## Deferred boundaries

See `DEFERRED.md`. Production representativeness, Topic 04 semantic response scope, Topic 10 general reliability methodology, E5 post-selection artifact/license work, E6 later performance work, and Topic 03 cross-group Topic identity are explicitly deferred and do not block progression beyond Topic 01.
