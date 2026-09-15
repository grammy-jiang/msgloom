# Topic 02 Academic Round 2 candidate bibliography

## Admission rule

A new paper enters the frozen Round 2 corpus only if it materially addresses at least one of:

- **A** non-contiguous / overlapping / set-valued span assignment;
- **B** decision-bearing/content preservation through explicit coverage/omission evaluation;
- **C** modern task-matched business/work-email Topic segmentation or assignment.

A=B=C=No means screen out.

## Admitted for acquisition

| ID | Role | Stream | Paper | Admission rationale |
| --- | --- | --- | --- | --- |
| A01 | TRANSFER_METHOD | R2-A / G2-A | Lybarger et al. (2022/2023), *Leveraging Natural Language Processing to Augment Structured Social Determinants of Health Data in the Electronic Health Record* | mSpERT explicitly adds multi-label predictions for the same span. Not email evidence. |
| A02 | TRANSFER_METHOD | R2-A / G1-A+G2-A | Huang et al. (2023), *T²-NER: A Two-Stage Span-Based Framework for Unified Named Entity Recognition with Templates* | Jointly models overlapped and discontinuous structures; useful representation/prediction transfer. Not email evidence. |
| A03 | TRANSFER_METHOD / ANNOTATION | R2-A / G2-A | Hasanain, Ahmad, Alam (2024), *Large Language Models for Propaganda Span Annotation* | Span-level multilabel sequence tagging where more than one technique can occupy the same span; includes human/LLM annotation behavior. Not Topic/email evidence. |
| B01 | TRANSFER_EVAL | R2-B / G3-A | Huang et al. (2023), *SWING: Balancing Coverage and Faithfulness for Dialogue Summarization* | Treats missing information as coverage distinct from factual inconsistency; human + automatic evaluation. Not segmentation/email evidence. |
| B02 | TRANSFER_EVAL | R2-B / G3-A | Liu et al. (2023), *Revisiting the Gold Standard: Grounding Summarization Evaluation with Robust Human Evaluation* | Atomic Content Units provide fine-grained semantic coverage/salience annotation and agreement protocol. Not segmentation/email evidence. |
| C01 | DIRECT_EMAIL_SUPPORT | R2-A / R2-B / R2-C | Srivastava et al. (2023), *MailEx: Email Event and Argument Extraction* | Modern conversational email span/event benchmark with non-continuous and shared trigger spans, long arguments, and conversation-history dependence. Not Topic segmentation, but direct email support for the missing representation/domain phenomena. |
| D05 | DIRECT_EMAIL_CORPUS_PROVENANCE | Opportunistic G5-A | Ulrich, Murray, Carenini (2008), *A Publicly Available Annotated Corpus for Supervised Email Summarization* | Clean official AAAI copy found; acquire only to close corpus/annotation provenance, not as Topic-segmentation evidence. |

## Screened out / boundary evidence

| Paper/resource | Reason for exclusion |
| --- | --- |
| Ray et al. (2026), *Argo: Efficient Importance Labeling for Enterprise Email Systems* | Modern direct enterprise-email domain, but whole-message importance labeling rather than Topic span segmentation/assignment. |
| Rameshkumar et al. (2018), *Assigning people to tasks identified in email* / EPA | Direct email task spans are provided, but prediction target is responsible people; does not evaluate Topic assignment or preservation loss. |
| van der Zwaan et al. (2016), *Assessing e-mail intent and tasks in e-mail messages* | Corporate email task/intent taxonomy and message-level task counts; not Topic span assignment/preservation. |
| Alkhereyf & Rambow (2017), *Work Hard, Play Hard* | Business vs personal whole-message classification; no Topic span gold. |
| generic 2024–2026 dialogue-topic segmentation papers from Round 1 | Already covered as transfer evidence; do not close modern business-email gap. |

## R2-C current result

No newly discovered 2020–2026 direct business/work-email paper has yet passed the task-matched admission gate. Continue targeted discovery, but do not lower the gate to fill the corpus.
