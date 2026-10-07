# Topic 02 engineering-validation plan

## Gates inherited from Topic 01

1. Gold text, Topic spans, memberships, conditions and scope annotations are authored independently of the component under test.
2. End-to-end denominators include false-positive predicted units/spans/memberships, not just predictions aligned to gold.
3. Incremental tests use only context available at that step; final/full-context diagnostics are separate.
4. Matching is one-to-one or explicitly set-valued and protected by mutation-style regression tests.
5. Experiment execution state and independent-review acceptance state are separate.
6. Independent reviewer rejection blocks closure and is preserved.
7. Synthetic/public success does not establish production representativeness or approve architecture.

## Sequence

- **EV1 / G7-E:** lossless Topic representation and round-trip identity.
- **EV2 / G9-E:** sentence/clause/EDU-like/arbitrary/hybrid unit representational ceiling.
- **EV3 / G2-E2:** set-valued span-to-Topic assignment; overlap/non-contiguous/whole-message labels separate.
- **EV4 / G3-E:** decision-bearing preservation and scope loss/broadening.
- **EV5 / G8-E1:** incremental context, correction and retraction.
- **EV6 / G8-E2:** assignment-specific uncertainty/abstention with disjoint calibration/holdout strata.
- **EV7 / G4-E:** bounded domain-transfer harness; production-domain representativeness deferred.

Supporting audits G1-E/G2-E1/G6-E1/G6-E2 are performed only where they improve the above experiments. G6-E3 is conditional on selecting an external method. G8-E3 performance is deferred.
