# Topic 01 engineering-validation results

## Status

- Experiment execution: **EXPERIMENT_EXECUTION_COMPLETE_SYNTHETIC_WITH_IDENTIFIED_BASELINE_FAILURES**
- Independent review acceptance: **tracked separately in `STATUS.md` and review audit artifacts**

No production mailbox data was used. No external network access was used by the experiment runner. These are controlled synthetic/adversarial results, not production accuracy claims.

An independent methodological review of the first engineering run rejected two claims: circular extractor gold and omission of false-positive detections from the attribution-error denominator. The current result contract fixes both issues and also addresses the review's replay, source-semantics, source-availability, and calibration-split concerns. The rejected review remains under `audit/independent-review/` as historical evidence.

## E1 — Joint benchmark contract

- Status: **EXPERIMENT_EXECUTION_COMPLETE_SYNTHETIC**.
- Cases: **18**; messages: **40**; fixture families: **18**.
- Gold quote occurrences: **19**; gold source links: **19**.
- Alternative-source ambiguous occurrences: **1**; deliberately missing-source occurrences: **1**.
- Gold structural relations: **12**; labeled content spans: **16**.
- Replay orders: **26**.

Fixture expected bodies are authored independently of `extract_body`; the fixture module does not invoke the extractor under test. Composite multi-parent quoted text is represented as separate source-specific occurrences instead of being mislabeled as source ambiguity.

**Conclusion:** the executable joint annotation/fixture contract is completed for synthetic engineering research. Production representativeness remains explicitly unproven.

## E2 — Preservation and quote/source alignment

### Independently authored extraction/preservation gold

- Exact body match: **40/40**.
- Decision/condition/deadline span preservation: **12/12**.
- Unique/new-content span preservation: **4/4**.

A regression test corrupts the extractor by deleting `Deadline: Friday.` and requires both extraction and decision-relevant preservation metrics to fall, preventing the former circular-gold failure.

### Structural detector — arrival-time end-to-end

- Detection precision: **1.000**; recall: **0.842**.
- Accepted source attributions: **12**; false accepted: **0**.
- Accepted-attribution error: **0.000**.
- Candidate recall over source links available at arrival: **0.833**.
- Unique-resolution recall over eligible gold at arrival: **0.750**.

The structural detector misses markerless, forwarded, and one composite multi-source display occurrence/segment under the occurrence-level gold contract. Detection and source matching remain separate metrics.

### Exact-reuse-augmented detector — arrival-time end-to-end

- Detection precision: **0.818**; recall: **0.947**.
- Predicted occurrences: **22**; unmatched predicted occurrences: **4**.
- Accepted source attributions: **18**; false accepted: **4**.
- Accepted-attribution error: **0.222**.
- Candidate recall over source links available at arrival: **0.944**.
- Unique-resolution recall over eligible gold at arrival: **0.875**.

Every predicted occurrence, including unmatched false positives, is included in the attribution-error denominator. Reuse improves candidate recall but can create repeated-boilerplate false positives and reverse provenance when a reply containing quoted text is collected before its historical original. **Text reuse is candidate evidence, not proof of quotation status or provenance direction.**

### Gold-conditioned final-context diagnostic

- Conditional full-context candidate recall: **1.000**.
- Conditional accepted unique error: **0.000**.
- Conditional source-span exact boundary: **1.000**; mean IoU: **1.000**.

These numbers are explicitly capability diagnostics **given gold occurrence locations and final case context**. They are not end-to-end or arrival-time performance.

## E3 — Arrival replay, correction, ancestry, and duplicate identity

### Deliberately unsafe single-value Message-ID baseline

- Mean final-state agreement across multi-order cases: **0.952**.
- Parent precision/recall: **0.857 / 0.857**.
- Ancestry precision/recall: **1.000 / 1.000**.
- Quote occurrence precision/recall: **1.000 / 0.867**.
- Quote source-policy accuracy on matched occurrences: **0.923**.
- Quote source-policy recall over all gold occurrences: **0.800**.
- Duplicate-ID case final-state agreement: **0.667**.

### Ambiguity-preserving identifier comparator

- Mean final-state agreement across multi-order cases: **1.000**.
- Parent precision/recall: **1.000 / 1.000**.
- Ancestry precision/recall: **1.000 / 1.000**.
- Quote occurrence precision/recall: **1.000 / 0.867**.
- Quote source-policy recall over all gold occurrences: **0.800**.
- Duplicate-ID case final-state agreement: **1.000**.

The one-value identifier map is arrival-order dependent and forces unsupported unique parents under Message-ID collision. Preserving alternatives removes that specific synthetic failure. Replay now records occurrence spans, scores quotes one-to-one, distinguishes direct parent from indirect ancestry, and reports relations removed before the final snapshot instead of a tautological stale=0 metric.

**Conclusion:** future candidate implementations must preserve identifier collisions/alternative parent evidence or abstain, and must keep reply-parent, ancestry, and quote-source relations independently testable. This is an evidence-backed acceptance requirement for later design work, not an approved persistence architecture.

## E4 — Structural uncertainty / abstention

Calibration and test use disjoint authored template families and have **0** identical-content overlaps.

- Calibration examples: **200**; held-out test examples: **200**.
- Calibration template families: **cal-approval-deadline, cal-escalation-missing, cal-limit-near-collision, cal-review-boilerplate, cal-shipment-quantity**.
- Held-out template families: **holdout-budget-near-collision, holdout-dispatch-quantity, holdout-final-approval, holdout-incident-missing, holdout-status-boilerplate**.
- Selected threshold: **0.90**.
- Test coverage: **0.400**.
- Accepted unique-link error: **0.000**.
- Unique-source recall: **1.000**.
- Ambiguous-case abstention: **1.000**.
- Missing-source abstention: **1.000**.
- Candidate recall: **1.000**.
- Accepted-prediction ECE (synthetic diagnostic): **0.008**.

This is a relation-specific synthetic diagnostic. A clean held-out result does not establish production calibration, rare-stratum safety, or general selective-prediction methodology; those remain Topic 10/future domain validation.

## Current completion decision

E1–E4 experiment execution is complete at the synthetic level. Whether that evidence is accepted for Topic 01 closure is a separate independent-review decision recorded outside `metrics.json`; experiment execution status must not be read as review acceptance. Even after review acceptance, this does **not** mean msgloom has a production-ready reconstruction implementation.

The engineering results do **not** automatically trigger Topic 01 Academic Round 3:

- A2: current failures are concrete detection/provenance limitations of deliberately simple baselines; targeted literature refresh remains conditional on candidate-method selection or persistent failure of stronger candidates.
- A7: controlled late-parent replay can revise structural state. The concrete failure found here is duplicate-identifier representation plus quote detection, not evidence that modern/LLM literature is required. A7 remains open and can be revisited by separate decision.

## Deferred / handed off

- Production representativeness and user-reviewed domain validation: deferred until suitable real/domain data becomes available; current work does not wait for it.
- Semantic response / partial agreement: Topic 04.
- General selective-prediction / calibration methodology: Topic 10.
- E5 code/data/license/reproduction: after a concrete external method is selected.
- E6 Raspberry Pi performance: after correctness, preservation, and uncertainty behavior are established.
- Cross-independent-group Topic identity: Topic 03 / Phase 2.
