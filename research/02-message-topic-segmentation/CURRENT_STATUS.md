# Topic 02 current status

**This topic is CLOSED.** It stopped on `review_decision`: after round 2 a
project-value review read the gaps and did not authorise a third academic
round. That is a decision about the evidence, and it is a stronger closure
signal than the `round_cap_reached` the later topics hit — those stopped
because a four-round budget ran out while papers were still arriving.

Topic 02 ran under the earlier process, so it differs from Topics 03–10 in
three ways that matter to anything reading the programme:

| | Topic 02 | Topics 03–10 |
| --- | --- | --- |
| Rounds | 2 academic, then a review declined a third | 4, all stopping on the cap |
| Gap id namespace | `G<n>-A` / `G<n>-E` | `gap-<n>` |
| Engineering work | a separate validation phase, EV1–EV7, accepted and closed | classified as gaps, not built |

The report, `gaps.json` and this file are all at the conventional paths, so a
tool will find them. Only the vocabulary differed, and that is what this
header fixes.

## Academic research

- Round 1: complete over the frozen 29-paper corpus.
- Formal project-value review of the 20 Round 1 gaps: complete.
- Academic Round 2: complete in recovery runner run `a504cd060ba4`.
- Round 2 gap classifier snapshot: 5 Academic, 13 Engineering, 2 Out-of-scope.
- Post-Round-2 project-value review: complete. No Academic Round 3 is currently authorized.

## Engineering validation

EV1–EV7 synthetic/adversarial validation is **ACCEPTED_AND_CLOSED_FOR_CURRENT_STAGE**. Final independent Review 6 returned `accepted` with zero blocking issues, zero nonblocking issues, and zero recommended fixes. The full rejection/repair history is preserved under `engineering-validation/audit/independent-review-*`.

## Remaining deferred / handed-off work

- Production-domain representativeness: deferred until suitable authorized domain data exists; not a current blocker.
- G10 concrete work-matter identity/count: Topic 03.
- Semantic response/partial-agreement scope: Topic 04.
- General calibration/selective-prediction methodology: Topic 10.
- External-method reproduction/license checks: conditional on candidate selection.
- Raspberry Pi performance: deferred until correctness/preservation/uncertainty method selection is mature.
- No production architecture has been approved by Topic 02 research.
