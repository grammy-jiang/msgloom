# Topic 02 manual search notes

Search date: 2026-09-14 (Australia/Sydney). Discovery is manual and precedes the Research Pipeline run.

## Starting seeds from BRIEF.md

`topic segmentation`; `dialogue topic segmentation`; `span classification`; `multi-label text classification`; `hierarchical text classification`.

## Terminology correction

Search results showed direct email literature uses `topic segmentation of email conversations`, `topic assignment`, `topical clusters`, and `topic segmentation and labeling in asynchronous conversations`. `hierarchical text classification` and whole-message `multi-label text classification` were downgraded because their normal academic tasks do not imply support-span assignment.

## Query families used in discovery pass 1

- `"dialogue topic segmentation"`
- `"topic segmentation" dialogue`
- `"topic segmentation" email conversations`
- `"email conversations" "topic segmentation"`
- `"topic segmentation and labeling" asynchronous conversations`
- `"topical clusters" email conversations`
- `"email" "topic assignment" sentence conversation segmentation`
- `"email" "topical clustering" sentences email thread`
- `"joint document segmentation" "segment labeling"`
- `"multi-label span classification" NLP`
- `"overlapping span" discontinuous span NLP`
- `"discontinuous span extraction" NLP`
- `"EDU segmentation"` / `"discourse unit segmentation" dialogue` (family retained for deeper pass)

## Important exclusions / downgrades already observed

- Email thread reconstruction or conversation detection is primarily whole-message/thread grouping and belongs mainly to Topic 01/03 unless it provides a concrete within-message method.
- Email sentiment/topic models at whole-document level are secondary.
- Generic NER span work is method-transfer evidence only.
- Preliminary Joty 2009/NW-NLP papers are retained as citation leads but appear substantially superseded by the 2010 EMNLP / 2011 ICWSM / 2013 JAIR line; acquire only if they add unique evidence.

## Next discovery pass

1. citation/reference trace from D01–D03;
2. annotation-unit literature (sentence vs clause vs EDU vs arbitrary span);
3. recent 2024–2026 dialogue/topic segmentation including LLM methods;
4. direct email/work-message studies beyond the Joty line;
5. exact multi-label span literature where overlapping labels, rather than only overlapping entities, are evaluated.
