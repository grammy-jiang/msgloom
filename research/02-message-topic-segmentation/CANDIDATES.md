# Topic 02 candidate bibliography

Status: manual discovery pass 1. This is not yet the frozen corpus and does not claim full-text analysis.

## Evidence classes

- **DIRECT_EMAIL** — primary object is email/asynchronous conversation topic segmentation or labeling.
- **DIRECT_WORK** — workplace/meeting/dialogue content whose task closely matches work-matter segmentation.
- **TRANSFER_SEGMENTATION** — general text/dialogue segmentation or evaluation methods.
- **TRANSFER_SPAN** — overlapping/discontinuous/multi-label span representation methods.
- **SECONDARY** — related whole-document classification or other weaker fit.

## High-priority candidates from pass 1

| ID | Class | Year | Paper | Why it matters | Acquisition lead |
| --- | --- | ---: | --- | --- | --- |
| D01 | DIRECT_EMAIL | 2010 | Joty, Carenini, Murray & Ng — *Exploiting Conversation Structure in Unsupervised Topic Segmentation for Emails* | Direct email corpus; topical clustering; conversation structure; likely foundational for interleaving topics | ACL Anthology D10-1038 |
| D02 | DIRECT_EMAIL | 2011 | Joty, Carenini, Murray & Ng — *Supervised Topic Segmentation of Email Conversations* | Direct email supervised sentence-pair/graph segmentation; explicitly motivated by non-sequential/intersecting email topics | AAAI ICWSM 5(1), DOI 10.1609/icwsm.v5i1.14198 |
| D03 | DIRECT_EMAIL | 2013 | Joty, Carenini & Ng — *Topic Segmentation and Labeling in Asynchronous Conversations* | Full framework; email + blog corpora; segmentation + labeling; likely strongest direct synthesis source | JAIR 47, DOI 10.1613/jair.3940; arXiv 1402.0586 |
| D04 | SECONDARY | 2020 | Liu, Lee & Lee — *Document-level multi-topic sentiment classification of Email data with BiLSTM and data augmentation* | Confirms multi-topic email characteristics but primary target is document-level sentiment, not support spans | Knowledge-Based Systems 197, DOI 10.1016/j.knosys.2020.105918 |
| T01 | TRANSFER_SEGMENTATION | 1997 | Hearst — *TextTiling: Segmenting Text into Multi-Paragraph Subtopic Passages* | Foundational contiguous topical segmentation and lexical-cohesion assumptions | Computational Linguistics 23(1); Berkeley author copy |
| T02 | TRANSFER_SEGMENTATION | 2002 | Pevzner & Hearst — *A Critique and Improvement of an Evaluation Metric for Text Segmentation* | Pk/WindowDiff evaluation definitions and known metric failure modes | ACL Anthology J02-1002 |
| T03 | DIRECT_WORK | 2003 | Galley et al. — *Discourse Segmentation of Multi-Party Conversation* | Foundational multiparty topic segmentation; lexical + conversational cues | ACL Anthology P03-1071 |
| T04 | DIRECT_WORK | 2006 | Arguello & Rosé — *Topic-Segmentation of Dialogue* | Atomic discourse-unit question; exchange vs contribution units | ACL Anthology W06-3407 |
| T05 | DIRECT_WORK | 2006 | Hsueh & Moore — *Automatic Topic Segmentation and Labeling in Multiparty Dialogue* | Segmentation + topic labels; hierarchy/granularity and annotation agreement | Edinburgh repository / SLT DOI 10.1109/SLT.2006.326826 |
| T06 | TRANSFER_SEGMENTATION | 2008 | Eisenstein & Barzilay — *Bayesian Unsupervised Topic Segmentation* | Strong classical unsupervised baseline and lexical-cohesion modeling | ACL Anthology D08-1035 |
| T07 | TRANSFER_SEGMENTATION | 2020 | Barrow et al. — *A Joint Model for Document Segmentation and Segment Labeling* | Joint boundary+label learning; includes multilabel segment labeling and error-alignment mechanism | ACL Anthology 2020.acl-main.29 |
| T08 | DIRECT_WORK | 2023 | Liu et al. — *Joint Dialogue Topic Segmentation and Categorization: A Case Study on Clinical Spoken Conversations* | Modern joint segmentation/categorization; domain-granularity robustness | ACL Anthology 2023.emnlp-industry.19 |
| T09 | DIRECT_WORK | 2025 | Yang et al. — *A Unified Supervised and Unsupervised Dialogue Topic Segmentation Framework Based on Utterance Pair Modeling* | Recent DTS; utterance adjacency/topic-affiliation formulation | ACL Anthology 2025.naacl-long.252 |
| T10 | DIRECT_WORK | 2025 | Lee et al. — *Def-DTS: Deductive Reasoning for Open-domain Dialogue Topic Segmentation* | Recent LLM/reasoning DTS; relevant modern comparison, still transfer | ACL Anthology 2025.findings-acl.1066 |
| S01 | TRANSFER_SPAN | 2020 | Dai et al. — *An Effective Transition-based Model for Discontinuous NER* | Representation/decoding of one semantic item over discontinuous spans | ACL Anthology 2020.acl-main.520 |
| S02 | TRANSFER_SPAN | 2021 | Li et al. — *A Span-Based Model for Joint Overlapped and Discontinuous Named Entity Recognition* | Joint overlap + discontinuity via span fragments and relations | ACL Anthology 2021.acl-long.372 |
| S03 | TRANSFER_SPAN | 2021 | Wang et al. — *Discontinuous Named Entity Recognition as Maximal Clique Discovery* | Segment graph joining separated spans into one semantic object | ACL Anthology 2021.acl-long.63 |
| S04 | TRANSFER_SPAN | 2022 | Murakami et al. — *Aspect-based Analysis of Advertising Appeals for Search Engine Advertising* | Exact spans can carry multiple labels; useful transfer for overlapping Topic memberships | ACL Anthology 2022.naacl-industry.9 |

## Pending discovery work

- Find direct email/work-message papers beyond the Joty line, especially models or corpora that explicitly support non-contiguous Topic membership inside a single message rather than only across a thread.
- Investigate annotation-unit literature (sentence/clause/EDU/arbitrary span) with direct relevance to semantic scope.
- Search for span-level multi-label classification where one text span legitimately has multiple semantic categories.
- Search recent 2024–2026 work on long-form/dialogue topic segmentation and LLM-based segmentation, without allowing recent papers to displace foundational direct-email evidence.
- Trace references/citations from D01–D03 before freezing the corpus.

## Direct-email preliminary/superseded leads

These are retained for provenance and citation tracing but are not automatically promoted into the frozen corpus if later papers subsume them:

| Lead | Year | Role | Current handling |
| --- | ---: | --- | --- |
| Joty et al. — *Finding Topics in Emails: Is LDA enough?* | 2009 | Early poster on sentence-level email topic assignment | Trace/compare against D01; likely superseded |
| Joty et al. — *Exploiting Conversation Features for Finding Topics in Emails* | 2010 | NW-NLP preliminary graph-theoretic formulation; reports sentence-level topic assignment and non-sequential email topics | Candidate for acquisition only if it contains unique method/evidence not retained in D01/D02 |
| Ulrich, Murray & Carenini — *A Publicly Available Annotated Corpus for Supervised Email Summarization* | 2008 | Underlying BC3 corpus provenance; topic annotation was added later by Joty et al. | Supporting corpus paper, not direct Topic-segmentation evidence |

## Recent additions from discovery pass 2

| ID | Class | Year | Paper | Why it matters | Acquisition lead |
| --- | --- | ---: | --- | --- | --- |
| T11 | DIRECT_WORK | 2024 | Artemiev et al. — *Leveraging Summarization for Unsupervised Dialogue Topic Segmentation* | Recent unsupervised DTS; summary-mediated boundary detection; tests modern non-classical setup | ACL Anthology 2024.findings-naacl.291 |
| T12 | DIRECT_WORK | 2026 | Sun et al. — *CobSeg: Coherence Boundary Modeling for Dialogue Topic Segmentation* | Current 2026 supervised/pseudo-label boundary model; useful freshness comparison and boundary metrics | arXiv:2605.30668 |

T12 is a current preprint, not treated as peer-reviewed evidence unless/until a publication record is verified.

## Annotation-unit / corpus-support additions

| ID | Class | Year | Paper | Why it matters | Acquisition lead |
| --- | --- | ---: | --- | --- | --- |
| U01 | TRANSFER_DISCOURSE_UNIT | 2019 | Zeldes et al. — *The DISRPT 2019 Shared Task on Elementary Discourse Unit Segmentation and Connective Detection* | Cross-formalism/multilingual view of the units used before discourse parsing; useful for sentence/clause/EDU RQ | ACL Anthology W19-2713 |
| U02 | DIRECT_WORK | 2025 | Prévot, Bertrand & Hunter — *Segmenting a Large French Meeting Corpus into Elementary Discourse Units* | Conversational EDU annotation/guidelines; shows spoken/work-dialogue unit difficulties | ACL Anthology 2025.sigdial-1.14 |
| D05 | SUPPORTING_EMAIL | 2008 | Ulrich, Murray & Carenini — *A Publicly Available Annotated Corpus for Supervised Email Summarization* | Primary BC3 corpus provenance underlying the later email-topic annotations; not itself a topic-segmentation result | AAAI EMAIL-2008 workshop |

The EDU papers answer the candidate-unit question only. They do not establish Topic identity or Topic-membership accuracy.

## Direct-email span/sentence additions

| ID | Class | Year | Paper | Why it matters | Acquisition lead |
| --- | --- | ---: | --- | --- | --- |
| D06 | DIRECT_EMAIL | 2005 | Bennett & Carbonell — *Detecting Action-Items in E-mail* | Directly contrasts whole-message topic classification with sentence/phrase-level request localization; useful for annotation granularity and lost-action evidence | Microsoft Research page -> CMU author PDF |
| D07 | DIRECT_EMAIL | 2015 | Gella et al. — *Assisting Composition of Email Responses: a Topic Prediction Approach* | Contact-center email; predicts next-sentence topic distribution, giving direct sentence-level topic evidence | arXiv:1510.02049 |

D06 is not Topic segmentation itself, but it directly evaluates the value of fine-grained email-body labels. D07 predicts sentence topics in responses rather than discovering persistent msgloom Topic identities; both must retain those task limits.

## Additional direct-email support

| ID | Class | Year | Paper | Why it matters | Acquisition lead |
| --- | --- | ---: | --- | --- | --- |

| D08 | DIRECT_EMAIL | 2004 | Corston-Oliver et al. — *Task-Focused Summarization of Email* | Full direct-email sentence-level task extraction system; supports annotation-unit and lost-work evidence questions | ACL Anthology W04-1008 |
