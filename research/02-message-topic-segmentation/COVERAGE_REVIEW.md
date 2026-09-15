# Topic 02 Phase-A coverage review

Status: acquisition round 1 coverage gate. This review decides whether the manually acquired corpus is sufficient to begin a local-corpus Research Pipeline round. It does **not** claim research conclusions; full-text evidence extraction has not started.

## Corpus at this checkpoint

- 29 local academic PDFs.
- 24 manually downloaded for Topic 02.
- 5 direct-email source PDFs reused byte-for-byte from Topic 01 with fresh hash verification and zero network requests.
- Evidence families: 3 core DIRECT_EMAIL Topic-segmentation papers; 3 additional DIRECT_EMAIL support papers; 5 reused DIRECT_EMAIL support papers; 9 DIRECT_WORK/dialogue papers; 4 TRANSFER_SEGMENTATION papers; 4 TRANSFER_SPAN papers; 1 TRANSFER_DISCOURSE_UNIT paper.
- D05 (BC3 original corpus paper) remains a clean-source acquisition failure/pending item; its absence does not block the later Joty Topic-annotation papers, which are locally present.

## Capability coverage matrix

| Capability from Topic 02 | Strongest candidate coverage | Acquisition-stage assessment | Remaining question for full-text analysis |
| --- | --- | --- | --- |
| Topic assignment in email/asynchronous conversations | D01, D02, D03 | **Strong direct** | Exact annotation cardinality, graph representation, and whether evidence is within-message vs thread-level |
| Multiple Topics in one email/thread | D01, D02, D03, D07 | **Strong direct at sentence/thread level** | Quantify how often one message contains multiple Topic clusters and how they are scored |
| A sentence/span with multiple Topic memberships | D01; S04 transfer | **Direct seed exists + transfer mechanism** | Verify D01 gold annotation/evaluation treatment of multi-topic sentences; determine whether models actually predict multiple memberships |
| Non-contiguous evidence for one Topic | D01–D03 topical clusters; S01–S03 transfer span methods | **Promising direct + strong representation transfer** | Verify whether a single email can contain separated same-topic spans in gold data and how cluster metrics treat them |
| Overlapping assignments | D01 multi-topic sentence; S02/S04 transfer | **Partial direct + transfer** | Direct business-email evaluation of overlap appears weak in acquisition pass |
| Annotation unit: sentence vs clause vs EDU vs arbitrary span | D06, D08, R03, U01, U02, T03, T04 | **Broad coverage** | Compare empirical annotation reliability/error modes across unit choices without conflating tasks |
| Topic segmentation + semantic labeling | D03, T05, T07, T08 | **Direct asynchronous + transfer** | Separate topic cluster identity from generated labels/taxonomies and from msgloom stable Topic identity |
| Reply/question/action scope inside email | R01, R02, R04, R05, D06, D08 | **Strong direct support** | These are related span/scope tasks, not Topic segmentation; measure what can legitimately transfer |
| Loss of conditions/evidence/action scope from segmentation errors | R03, D06, D08, R01/R05 | **Relevant direct evidence, but likely incomplete** | No acquisition-stage evidence yet establishes a decision-bearing-loss metric for Topic segmentation itself |
| Boundary/segmentation evaluation metrics | T02 plus T01/T03/T04/D01–D03 | **Strong** | Harmonize Pk/WindowDiff/cluster/sentence-pair metrics; do not pool incompatible scores |
| Modern neural/LLM dialogue segmentation | T08–T12 | **Current transfer through 2026** | No direct email LLM Topic-segmentation benchmark found in pass 1; do not infer email accuracy |
| Production/business email context | D07 contact center; D06/D08 work email; secondary RANLP 2023 lead | **Enough for context, not direct end-to-end Topic segmentation** | Modern private/business datasets and span-level gold remain a likely domain-transfer gap |

## Search families explicitly downgraded

- `hierarchical text classification`: not a core Topic 02 task unless a specific paper supplies a relevant mechanism.
- whole-message `multi-label text classification`: useful only for the fact that a message can carry multiple categories; it does not locate supporting spans.
- generic NER discontinuous/overlap papers: representation transfer only.
- email thread reconstruction/conversation detection: primarily Topic 01/03 unless a paper contains a within-message segmentation/assignment mechanism.
- action-item extraction: direct support for unit/scope preservation only; do not turn Topic 02 into Topic 05.

## Material residual acquisition gaps

### G1 — Explicit within-one-email non-contiguous Topic gold

The direct Joty line is highly promising because it clusters email sentences and permits asynchronous/interleaved Topics, but acquisition-stage inspection is not enough to prove that one individual message contains separated spans assigned to the same Topic or how that case is evaluated. Resolve from full text before deciding another paper search is required.

### G2 — Direct overlapping Topic-membership evaluation

D01 annotation permits multi-topic sentences, but model/evaluation support for predicting overlap is not yet established. Transfer span papers cover the representation problem, not business-email Topic semantics.

### G3 — Decision-bearing loss

No discovered Topic-segmentation benchmark obviously reports “lost condition / lost evidence / wrong approval scope” as an error metric. Direct action/Q&A/zoning papers provide related risks. This may remain an ENGINEERING evaluation gap even after literature synthesis.

### G4 — Current direct business-email segmentation

Recent DTS work through 2026 is mostly dialogue transfer. The manual pass found recent whole-email business classification but no obvious modern direct within-email Topic-segmentation successor to the Joty line. This is partial search evidence, **not** proof no such literature exists.

## Acquisition-round decision

**READY TO FREEZE ROUND-1 CORPUS.**

Rationale:

1. Every core Brief capability has either direct evidence, a clearly labelled transfer mechanism, or an explicit residual gap.
2. Direct email evidence is not outnumbered conceptually by transfer literature: the evidence classes are separated and the direct Joty line anchors the Topic task.
3. Recent transfer work through 2026 is represented, so the corpus is not purely historical.
4. Further generic downloads would mostly add redundant contiguous segmentation or generic span papers without closing G1–G4.
5. The remaining gaps are best resolved first by full-text analysis of the already acquired direct papers. If synthesis identifies a precise missing citation/query that can change a recommendation, do a later targeted manual acquisition round rather than padding this corpus now.

This is a corpus-sufficiency decision for **research round 1**, not a claim of literature exhaustion or convergence.
