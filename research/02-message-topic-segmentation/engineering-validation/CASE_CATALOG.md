# Topic 02 synthetic case catalog

All cases are independently authored synthetic/adversarial fixtures. They are deliberately enriched stress cases and do not estimate production prevalence.

| Case | Purpose | Tags | Topics | Spans |
| --- | --- | --- | ---: | ---: |
| `single-topic-deadline` | Single work matter with a decision and deadline. | EV1, EV2, EV4 | 1 | 3 |
| `two-topics-contiguous` | Two independent contiguous work matters. | EV1, EV2, EV3 | 2 | 3 |
| `noncontiguous-aba` | Atlas evidence recurs after an intervening Beta matter. | EV1, EV2, EV3, noncontiguous | 2 | 5 |
| `overlap-shared-span` | One evidence span simultaneously belongs to two work matters. | EV1, EV3, overlap | 2 | 1 |
| `clause-split-two-matters` | One sentence contains two work matters with separate conditions. | EV2, EV4, clause | 2 | 4 |
| `condition-scope` | A condition narrows Atlas only, not neighboring Beta. | EV4 | 2 | 3 |
| `exception-scope` | An exception belongs only to Atlas. | EV4 | 2 | 3 |
| `shared-supporting-evidence` | One evidence item supports two matters. | EV3, EV4 | 2 | 1 |
| `heading-list-scope` | Headings govern following list items without becoming separate matters. | EV2, EV4, list | 2 | 6 |
| `table-rows` | Different table rows belong to different matters. | EV2, EV4, table | 2 | 4 |
| `ambiguous-reference` | The current message alone does not identify which matter 'this change' refers to. | EV5, EV6, ambiguity | 2 | 2 |
| `quoted-vs-authored` | Quoted Topic evidence and newly authored Topic evidence remain distinguishable. | EV1, EV4, origin | 2 | 3 |
| `shared-plus-specific` | Shared evidence coexists with a matter-specific approval constraint. | EV3, EV4 | 2 | 3 |
| `same-term-different-matters` | Shared lexical token Atlas does not make two concrete work matters identical. | EV3, lexical-collision | 2 | 2 |
| `context-correction` | Later context corrects one ambiguous interpretation without changing a neighboring explicit matter. | EV5, correction | 3 | 2 |
| `irrelevant-chatter` | No work matter should be invented for social chatter. | EV3, negative-control | 1 | 0 |
| `shared-evidence-separate-decision` | Shared evidence must not broaden an Atlas-only decision into Beta. | EV3, EV4, scope | 2 | 3 |
| `noncontiguous-with-overlap` | Atlas has separated evidence and shares a middle span with Beta. | EV1, EV3, noncontiguous, overlap | 2 | 4 |
