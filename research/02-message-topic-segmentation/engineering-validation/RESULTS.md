# Topic 02 engineering-validation results

## Status

- Experiment execution: **EXPERIMENT_EXECUTION_COMPLETE_SYNTHETIC_WITH_IDENTIFIED_FAILURES**
- Independent review: **PENDING_INDEPENDENT_REVIEW**

No production mailbox data or external network access was used by the experiment runner. These are synthetic/adversarial engineering results only.

## EV1 — Lossless representation

- Cases: **18**; evidence spans: **52**; membership rows: **52**.
- Non-contiguous Topic objects: **7**; joint-membership spans: **5**; ambiguous rows: **3**.
- Canonical representation round trips: **18/18**.

This validates the research representation contract only, not a production schema. Topic identities/counts are fixture-supplied controlled gold, not automatically discovered.

## EV2 — Unit representational ceiling

| Unit | Exact Topic components | Extra scope chars | Decision-scope precision |
| --- | ---: | ---: | ---: |
| sentence | 0.692 | 320 | 0.828 |
| clause | 0.744 | 21 | 1.000 |
| edu_like | 0.744 | 21 | 1.000 |
| hybrid | 0.744 | 21 | 1.000 |

Sentence-level projection has full decision-scope recall in the frozen synthetic corpus but **5 wrong-Topic scope false positives**. Clause/EDU-like/hybrid remove those false positives here, but exact character-boundary representability remains below 1.0.

## EV3 — Set-valued Topic assignment

### Gold-span-conditioned membership diagnostic

- Single-label span-only membership P/R: **1.000/0.611**; overlap recall **0.200**.
- Set-valued span-only membership P/R: **1.000/0.741**; overlap recall **0.900**.
- Set-valued local-window P/R: **0.600/1.000**.

Set-valued output materially improves overlap recall. Naive local context obtains high recall by adding many false memberships; those errors remain in the denominator. These numbers are explicitly **gold-span-conditioned** and are not end-to-end span scores.

### Deterministic unit + membership end-to-end baseline

- Sentence + set-valued IoU>=0.5 P/R: **0.882/0.769**; exact-boundary recall **0.667**.
- Clause + set-valued IoU>=0.5 P/R: **0.897/0.897**; exact-boundary recall **0.692**.
- Clause + set-valued exact non-contiguous Topic objects: **0.286**.

Extra predicted Topic spans and missed gold spans are included in these end-to-end denominators.

## EV4 — Decision-bearing preservation

- Sentence oracle scope P/R: **0.828/1.000**.
- Clause oracle scope P/R: **1.000/1.000**.
- Set-valued span-only predicted decision membership P/R: **1.000/0.542**.
- Set-valued local-window predicted decision membership P/R: **0.667/1.000**.
- Scored required decision-bearing spans/memberships: **20/24**; ambiguous decision-bearing spans excluded from required-membership scoring: **1**.

| Decision kind | Annotated spans | Scored required spans | Required memberships | Span-only P/R | Local-window P/R |
| --- | ---: | ---: | ---: | ---: | ---: |
| approval_constraint | 2 | 2 | 2 | N/A/0.0 | 0.6666666666666666/1.0 |
| condition | 4 | 4 | 4 | 1.0/0.75 | 0.5/1.0 |
| deadline | 8 | 7 | 7 | N/A/0.0 | 0.5833333333333334/1.0 |
| decision | 2 | 2 | 2 | 1.0/1.0 | 0.6666666666666666/1.0 |
| exception | 1 | 1 | 1 | 1.0/1.0 | 0.5/1.0 |
| supporting_evidence | 4 | 4 | 8 | 1.0/0.875 | 1.0/1.0 |


These are **selected independently authored synthetic decision-bearing annotations**, not a source-complete semantic inventory. Predicted decision membership is gold-span-conditioned and does not measure decision-span detection.

## EV5 — Incremental context/correction

- Step exact: **5/5**.
- Expected abstention: **3/3**.
- Correction success: **1/1**.
- Future context used: **false**.

Semantic response/agreement scope is deliberately not evaluated and remains Topic 04.

## EV6 — Assignment uncertainty/abstention

- Calibration/test examples: **200/200**, with disjoint template families and **0** exact content overlap.
- Target: accepted error <= 0.05 with coverage >= 0.40.
- Target met: **False**.
- Fallback useful-coverage threshold: **0.6**.
- Holdout coverage/error: **0.600/0.333**.

The simple baseline **fails** the joint error/coverage target. An all-abstain threshold is not accepted as success.

## EV7 — Synthetic workplace-style stratification

This is not production-domain validation. Per-style results are recorded in `results/metrics.json`. The strata include plain prose, multi-clause sentences, structured list/table content, quoted history, context-dependent references, and overlap/non-contiguous cases.

## Supporting artifact audit

`audit/SUPPORTING_ARTIFACT_AUDIT.md` records G1-E/G2-E1/G6-E1/G6-E2. Missing external annotation/scorer details remain explicit unknowns and are not guessed.

## Deferred

Production representativeness, G10/Topic 03, semantic response scope/Topic 04, general calibration methodology/Topic 10, conditional external-method reproduction, and Raspberry Pi performance remain deferred as documented in `DEFERRED.md`.
