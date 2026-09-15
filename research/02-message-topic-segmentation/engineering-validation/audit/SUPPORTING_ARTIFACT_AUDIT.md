# Topic 02 supporting artifact audit

## Scope

This audit addresses G1-E, G2-E1, G6-E1 and G6-E2 using the already accepted Round 1 full-paper analyses and locally available project artifacts. It does **not** claim to have obtained or inspected an external BC3 annotation/scorer release that is not present in the current project workspace.

## G1-E — message-local offsets and recurrence

**Status: unresolved externally; synthetic contract available internally.**

- D01 reports sentence-level Topic annotation and permits all relevant Topic labels for one sentence, but the accepted analysis records no frequency of multi-label sentences and no message-local offset release.
- D01 Figure 1 provides quote-inclusive separated same-Topic evidence within a displayed email, but authored-only recurrence prevalence/accuracy is not reported.
- D03 permits multiple ordered memberships but does not report exact realized frequency or how those memberships map to every scorer.

Current action: the engineering harness uses independently authored half-open offsets and explicit authored/quoted origins. This validates the benchmark machinery, not BC3 prevalence.

## G2-E1 — gold reduction / decoder / overlap

**Status: unresolved externally; task distinctions recorded.**

- D01 gold permits multi-membership, while final LDA/LCSeg-style outputs are effectively disjoint; the exact gold-to-evaluation membership rule is not reported sufficiently to reconstruct overlap scoring.
- D02 predicts same/different sentence pairs and partitions a graph; it does not supply overlapping final memberships.
- D03 again allows multi-membership gold while final segmentation decoders are disjoint; pair-label conversion remains incompletely specified.
- S04 directly supports coincident-boundary multi-label spans in advertising, but observed prevalence, overlap-only scores and arbitrary nested/crossing support are not established.

Current action: EV3 reports whole-message Topic sets, span memberships, overlap-only membership and complete Topic objects separately. It does not import unknown legacy reductions.

## G6-E1 — scorer implementations / populations

**Status: partially described in papers, not reproduced.**

Accepted Round 1 analyses preserve task-specific metrics (for example 1-to-1/loc3, pair classification, span-and-label macro F1) and their population ambiguities. No external scorer implementation is adopted by the current engineering harness, so reproducing legacy scorers is not required to validate EV1–EV7. If a legacy method is selected later, exact scorer code/version/population becomes a precondition before comparing numeric results.

## G6-E2 — dataset versions / splits / duplicates

**Status: unresolved for legacy external datasets; not silently assumed.**

D01/D02/D03 analyses explicitly record missing or incomplete held-out/split/duplicate/leakage details. S04 also lacks complete near-duplicate/grouping controls. The synthetic engineering corpus is deterministic and case-separated; it cannot establish legacy/public-data leakage controls or production representativeness.

If public data is adopted in EV7 or a later candidate-method evaluation, version/hash, split identities, group boundaries and duplicate controls must be recorded before numeric comparison.

## Decision

These four supporting gaps do not justify guessing missing artifact behavior or blocking the current synthetic engineering programme. They remain explicit external-artifact/reproduction requirements triggered by actual adoption of the corresponding dataset/scorer/method.
