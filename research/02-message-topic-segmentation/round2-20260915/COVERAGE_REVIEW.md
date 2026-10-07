# Topic 02 Academic Round 2 coverage review

## Verdict

**Freeze the six acquired papers for Academic Round 2.**

The stopping rule is capability coverage plus diminishing value from further broad discovery, not a paper-count target. The corpus is intentionally small because Round 1 already contains 29 papers and Round 2 is gap-directed.

## R2-A — set-valued, overlapping, non-contiguous assignment

Coverage is sufficient for a targeted follow-up synthesis:

- **A01 (TRANSFER_METHOD):** explicit multi-label predictions for the same span.
- **A02 (TRANSFER_METHOD):** one framework for overlapped and discontinuous span structures.
- **A03 (TRANSFER_METHOD / ANNOTATION):** span/token-level multilabel tagging where multiple labels may occupy the same text.
- **C01 (DIRECT_EMAIL_SUPPORT):** modern email event extraction with non-continuous/shared trigger spans and long arguments.

What remains unsupported:

- task-matched direct-email prediction of simultaneous overlapping **Topic** membership;
- authored-only within-message Topic A-B-A prevalence/prediction.

The new papers can refine representation/evaluation requirements but must not be reported as email Topic accuracy.

## R2-B — decision-bearing preservation

Coverage is sufficient for a targeted follow-up synthesis:

- **B01 (TRANSFER_EVAL):** treats missing information as coverage distinct from factual inconsistency and evaluates that trade-off.
- **B02 (TRANSFER_EVAL):** Atomic Content Units provide fine-grained semantic content/salience units with human-evaluation methodology.
- **C01 (DIRECT_EMAIL_SUPPORT):** direct modern email evidence that event arguments can be long/non-NER spans and may depend on thread context.

What remains unsupported:

- an adjudicated direct-email rate of Topic-segmentation loss for conditions, exceptions, approval constraints, deadlines, or decision qualifiers.

Round 2 can improve how msgloom should define preservation gold/metrics without pretending these transfer evaluations directly measure Topic segmentation.

## R2-C — modern business/work-email evidence

**Gap remains materially open.**

C01 is a strong modern direct-email support paper but its task is event/argument extraction, not Topic segmentation or Topic assignment. Targeted searches also found modern business/enterprise email papers for importance, priority, task/intent taxonomy, business-vs-personal classification, and department-topic classification. Those are whole-message or other-target tasks and were screened out.

No 2020–2026 direct business/work-email paper discovered in this round passed the task-matched Topic-span admission gate. This is a bounded search result, not proof of literature absence.

## G5-A opportunistic provenance

A clean official D05 source was discoverable on the public web, but the single Raspberry Pi acquisition attempt failed at DNS resolution for `f.aaai.org`. D05 is not part of the corpus and does not block the round.

## Direct / transfer balance

- DIRECT_EMAIL_SUPPORT: 1 (C01)
- TRANSFER_METHOD / ANNOTATION: 3 (A01–A03)
- TRANSFER_EVAL: 2 (B01–B02)

The role imbalance is intentional and visible. Round 2 does not upgrade transfer evidence into direct business-email proof.

## Stop decision

Further broad search is unlikely to change the three targeted evidence roles enough to justify delaying analysis. Any additional discovery should now be triggered by citations/findings from full-text analysis, not by a paper quota.
