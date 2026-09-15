# Topic 02 Academic Round 2 terminology refresh

## Scope

Round 2 is gap-directed, not a repeat of broad Round 1 discovery. Search terms must map to R2-A, R2-B, or R2-C.

## R2-A — set-valued / overlapping / non-contiguous assignment

Promoted terms:

- `multi-label span prediction`
- `multi-label span classification`
- `overlapping span prediction`
- `discontinuous span recognition`
- `unified overlapped and discontinuous span`
- `multi-label sequence tagging`
- `multiple labels per span`
- `shared fragment` / `discontinuous object`

Capability distinction:

`overlap/discontinuity representable` != `same span predicts several labels` != `email Topic evidence`.

Transfer methods are admissible only if they materially test a representation/prediction capability missing from Round 1.

## R2-B — decision-bearing preservation

Promoted terms:

- `coverage and faithfulness`
- `missing information` evaluation
- `atomic content units`
- `summary content units`
- `semantic coverage`
- `content omission`
- `fine-grained human evaluation`
- `scope preservation`
- `condition` / `exception` / `decision qualifier` preservation

Capability distinction:

`factual consistency` != `coverage` != `decision-bearing preservation`.

Generic hallucination-only papers are secondary. Papers that explicitly measure missing/covered content units are preferred.

## R2-C — modern business/work email

Search families:

- `business email topic segmentation`
- `workplace email topic assignment`
- `enterprise email topic segmentation`
- `work email topic annotation benchmark`
- `business email multi-topic span`

Current discovery boundary: modern enterprise-email papers are easy to find for importance, task intent, priority, or whole-message classification, but no 2020–2026 task-matched business-email Topic span benchmark has yet passed the admission gate. This is a search result boundary, not a claim of literature absence.

## Explicit demotions

- ordinary contiguous topic boundary detection;
- whole-message multi-label classification without support spans;
- generic NER span work that adds no new overlap/discontinuity/multi-label capability beyond Round 1;
- enterprise-email importance/priority/intent classification when no Topic span gold is present;
- generic summarization faithfulness that measures only hallucination and not coverage/omission.
