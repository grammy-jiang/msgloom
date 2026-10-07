# Email, image, table and attachment understanding in workplace communication: preserving multimodal and document structure, and grounding evidence back to precise source locations such as a cell, region, page or attachment version academic terminology analysis

## Product problem

The target problem is broader than document parsing and narrower than generic multimodal AI. The required capability is to preserve the relationships that determine meaning in workplace material—page structure, reading order, table hierarchy, headers and units, images and visual emphasis, cross-modal references, attachment identity and version—and then make extracted claims traceable back to the source object that supports them.

This creates three separate layers that discovery must not collapse:

1. **Structural recovery:** recover page regions, reading order, tables, cells, figures and document hierarchy.
2. **Semantic interpretation:** understand what those structures mean and reason over them.
3. **Evidence grounding:** identify the exact page, cell, region, bounding box or attachment version supporting an extracted fact or answer.

Modern visually rich document understanding explicitly combines textual, spatial and visual information; LayoutLM and its successors are canonical examples. LayoutLM jointly modeled text and layout for document-image understanding, while LayoutLMv2 explicitly modeled text, layout and image in a multimodal framework. citeturn428525search5turn344133search2 Document visual question answering provides a high-level test of document interpretation, but the original DocVQA benchmark primarily evaluates answering questions from document images rather than the complete evidence-provenance contract required here. citeturn428525search4turn428525academia121

The terminology audit therefore promotes academically established task names while demoting product phrases that retrieve unrelated security, retrieval or bibliometric literature.

## Seed keyword audit

| Seed | Academic meaning | Fit | Main risk |
| --- | --- | --- | --- |
| document AI | Broad umbrella for ML and multimodal analysis of documents. | STRONG | Too broad: easily dominated by OCR, classification and commercial IDP rather than structure-preserving understanding. |
| document intelligence | Broad umbrella overlapping Document AI and visually rich document understanding. | STRONG | Heterogeneous academic and commercial usage. |
| visually rich document understanding | Joint understanding of text, 2-D layout and visual appearance in documents. | STRONG | Much work is single-page form/receipt extraction and does not test arbitrary workplace documents or provenance. |
| VRDU | Common abbreviation for visually rich document understanding. | STRONG | Acronym is not universally standardized and can collide with unrelated vision terminology. |
| document layout analysis | Physical/logical decomposition of pages into regions and structures. | STRONG | Region detection alone does not establish semantic understanding. |
| layout-aware language models | Models encoding text together with 2-D layout, sometimes also image features. | STRONG | Model family rather than task; benchmark gains need not imply precise grounding. |
| document information extraction | Extraction of fields, entities, relations or records from documents. | STRONG | Dominated by fixed-schema KIE on simple forms and receipts. |
| document visual question answering | QA over document images using textual, spatial and visual information. | STRONG | Correct answer strings can be produced without explicit evidence localization. |
| DocVQA | Established task/benchmark name for document visual QA. | STRONG | Particular benchmarks may be materially weaker than the product's provenance requirement. |
| multi-page document understanding | Understanding and reasoning over multiple pages of one document. | STRONG | Some datasets add distractor pages rather than genuine cross-page reasoning. |
| long-document multimodal understanding | Long-context multimodal processing of multi-page documents. | MODERATE | Retrieves generic long-context LMM work unrelated to structured evidence. |
| OCR layout understanding | Informal phrase for combining OCR with spatial/layout signals. | MODERATE | Non-standard phrase easily collapses back to OCR accuracy work. |
| reading order detection | Recovery of the intended sequence among text lines/blocks/regions. | STRONG | Correct sequence does not by itself preserve tables, graphics or cross-modal references. |
| table detection | Localization of table regions. | STRONG | Does not recover row-column relationships, headers, spans or units. |
| table structure recognition | Recovery of rows, columns, cells, spans and sometimes header/function roles. | STRONG | Geometric accuracy may not measure semantic header/value correctness. |
| table understanding | Broad structural and semantic understanding of tables. | STRONG | Much literature starts from clean relational tables rather than raw documents. |
| table question answering | Natural-language reasoning over tables. | STRONG | Usually assumes normalized tables are already available. |
| spreadsheet understanding | Semantic and structural interpretation of spreadsheets, including hierarchy, formatting and formulas. | STRONG | Current work can drift toward spreadsheet editing agents rather than faithful interpretation. |
| chart understanding | Extraction and reasoning over axes, legends, marks and quantitative relations. | MODERATE | Charts cover only one relevant visual object class and many benchmarks are synthetic. |
| chart question answering | QA requiring visual and numerical reasoning over charts. | MODERATE | Underlying table data or template questions can bypass hard visual extraction. |
| multimodal information extraction | IE jointly using text, visual and other modalities. | STRONG | Generic term includes social media, news and natural-image IE. |
| multimodal coreference resolution | Coreference across text and visual modalities. | MODERATE | Established work is frequently based on image narration or dialogue rather than structured documents. |
| cross-modal reference resolution | Resolving a linguistic expression to a referent represented in another modality. | MODERATE | Less standardized terminology; attracts HCI, dialogue and embodied-reference work. |
| visual grounding | Mapping language to visual objects or regions. | MODERATE | Dominated by natural-image datasets unless document constraints are added. |
| referring expression comprehension | Localizing the image object/region described by an expression. | MODERATE | Standard natural-image setting lacks pages, cells, document hierarchy and attachment identity. |
| document region grounding | Emerging document-specific language-to-region/evidence localization task. | STRONG | Search vocabulary is still fragmented; must also search grounded DocVQA, answer localization and evidence grounding. |
| citation localization | Usually localization of scholarly citation contexts or citation spans. | WEAK | Major false friend: bibliometric/citation-analysis literature rather than visual source grounding. |
| scanned document understanding | Semantic understanding of scanned page images using OCR/OCR-free and layout-aware techniques. | STRONG | Easily degenerates into scanning and OCR quality research. |
| document version comparison | Comparison of revisions to identify changed content. | MODERATE | No single canonical task matches semantic revision identity plus provenance; searches retrieve plagiarism and textual diff. |
| visual document differencing | Image-level localization of changes between rendered document versions. | MODERATE | Pixel differences need not be semantic differences and vice versa. |
| attachment content extraction | Practical phrase for extracting data from attached files. | MODERATE | Not a canonical academic task; attracts forensics, MIME processing and malware literature. |
| email attachment understanding | Understanding attachments in their email context. | WEAK | Searches are dominated by malicious-attachment and phishing work. |
| screenshot understanding | Visual-language interpretation or parsing of screenshots/UI renderings. | MODERATE | Much literature optimizes UI interaction instead of evidence interpretation. |
| figure caption grounding | Linking captions/references to figures or visual regions. | MODERATE | Useful but considerably narrower than arbitrary workplace visual references. |
| multimodal document retrieval | Retrieval of pages/documents using text plus visual/layout representations. | WEAK | Mainly Topic 07 territory; retrieval is not evidence interpretation. |

Several distinctions are empirically important. PubLayNet, for example, defines document layout analysis as recognizing layout elements so documents can be converted into structured machine-readable representations, but that task does not itself guarantee downstream semantic understanding. citeturn428525search2 Table work makes the same distinction: TableBank targets table detection and recognition, while PubTables-1M explicitly separates detection, structure recognition and functional analysis. citeturn217084search0turn217084search9

The weak term **citation localization** should not drive discovery. For this project, the better current vocabulary is **document evidence grounding**, **answer localization**, **grounded Document VQA**, **visually grounded document QA**, and **document region grounding**. Recent grounded-document work explicitly evaluates or predicts bounding-box evidence rather than answer strings alone. citeturn444323search4turn444323academia56turn444323search10

## Academic task families

### F1 — Document layout analysis, logical structure and reading order — DIRECT

This family recovers page regions, their logical roles, hierarchy and reading sequence. It is foundational because text extraction with the wrong ordering can create a fluent but false representation of the source.

Seed literature:

- *Hierarchical Representation of Optically Scanned Documents* (1984).
- *The Document Spectrum for Page Layout Analysis* (1993).
- *PubLayNet: Largest Dataset Ever for Document Layout Analysis* (2019).

Document-layout research substantially predates deep learning: page segmentation was already a mature research problem by the 1980s and early 1990s. A 1992 paper, for example, defines page segmentation as dividing scanned pages into columns and blocks before classification. citeturn224505search0turn462191search0

### F2 — Visually rich document understanding and layout-aware multimodal representation — DIRECT

This is the principal modern model family for jointly encoding text, spatial layout and image information.

Seed literature:

- *LayoutLM: Pre-training of Text and Layout for Document Image Understanding* (2020). citeturn428525search5
- *LayoutLMv2: Multi-modal Pre-training for Visually-rich Document Understanding* (2021). citeturn344133search2
- *DocFormer: End-to-End Transformer for Document Understanding* (2021). citeturn344133search0
- *LayoutLMv3: Pre-training for Document AI with Unified Text and Image Masking* (2022). citeturn344133search3

These papers are highly relevant mechanisms, but discovery must inspect their downstream evaluations rather than treating the model-family label itself as proof of evidence preservation.

### F3 — Structured document information extraction — DIRECT

This family includes multimodal key-information extraction, entity labeling and relation/entity linking from visually structured documents.

Seed literature includes *StrucTexT: Structured Text Understanding with Multi-Modal Transformers*, which explicitly treats structured text understanding in visually rich documents and jointly addresses entity labeling and entity linking using text, image and layout information. citeturn344133academia134

For msgloom, the admission criterion should be stronger than ordinary form filling: papers become especially valuable when they preserve entity relationships and source coordinates or evaluate structurally ambiguous documents.

### F4 — Document visual question answering, multi-page and long-document understanding — DIRECT

This family tests question-conditioned semantic interpretation of document content and layout.

Seed literature:

- *DocVQA: A Dataset for VQA on Document Images*. citeturn428525academia121
- *Hierarchical Multimodal Transformers for Multi-Page DocVQA*. MP-DocVQA extends the setting to documents of multiple scanned pages and includes prediction of the page containing the answer. citeturn979666search6
- *Document Understanding Dataset and Evaluation (DUDE)*. DUDE specifically broadens document type, multi-page reasoning and questions about layout and visual elements. citeturn979666search70

A key downgrade condition is genuine multi-page reasoning. DUDE itself notes that MP-DocVQA reused existing single-page questions while adding surrounding pages, making many additional pages distractors rather than evidence that must be integrated. citeturn979666search70

### F5 — Grounded document QA and document evidence localization — DIRECT

This family is especially important to Topic 08 because it evaluates not only **what** answer is produced but **where the evidence came from**.

Search vocabulary should include:

- grounded Document VQA;
- visually grounded document QA;
- document answer localization;
- document evidence grounding;
- document region grounding;
- bounding-box-grounded DocVQA;
- page/region evidence localization.

Recent work explicitly treats textual correctness and spatial localization as separable capabilities. *Where is this coming from? Making groundedness count in the evaluation of Document VQA models* proposes document-VQA evaluation using the position of predicted and ground-truth evidence. citeturn444323search4 *DocVAL* likewise reports answer and bounding-box localization objectives, while 2026 work explicitly names the task “Visually Grounded Document Question Answering.” citeturn444323academia56turn444323search10 SciEGQA goes further by attaching evidence pages and semantic-region bounding boxes and evaluating answer correctness together with evidence grounding. citeturn444323search2

This terminology should be **promoted above “citation localization.”**

### F6 — Table detection, structure recognition and functional structure — DIRECT

This family should be split internally into:

1. table detection;
2. table structure recognition;
3. functional/semantic structure.

A table bounding box is not table understanding.

Historical table-structure work is already visible in the early 1990s; later work such as TableBank and PubTables-1M provides large benchmarks. PubTables-1M includes detailed cell/header/location annotations and explicitly targets table detection, structure recognition and functional analysis. citeturn462191search7turn217084search9

Seed literature:

- *Table Structure Recognition Based on Textblock Arrangement and Ruled Line Position* (1993).
- *DeepDeSRT: Deep Learning for Detection and Structure Recognition of Tables in Document Images* (2017). citeturn462191search14
- *TableBank: Table Benchmark for Image-based Table Detection and Recognition* (2020). citeturn217084search5
- *PubTables-1M: Towards Comprehensive Table Extraction from Unstructured Documents* (2022). citeturn217084search10

### F7 — Semantic table understanding, table QA and spreadsheet structure — DIRECT

This family covers what happens after cells have been recovered: identifying semantic roles and hierarchies and reasoning over values.

Seed literature:

- *TaPas: Weakly Supervised Table Parsing via Pre-training* uses cell selection and aggregation to answer questions over tables. citeturn428525search1
- *TUTA: Tree-based Transformers for Generally Structured Table Pre-training* explicitly models spatial, hierarchical and semantic table information and evaluates cell/table semantic-structure tasks. citeturn217084search1
- *HiTab: A Hierarchical Table Dataset for Question Answering and Natural Language Generation*, listed within the spreadsheet-intelligence/table-understanding research programme. citeturn217084search8

The DIRECT/TRANSFER boundary must be recorded per paper. A model reasoning over an already normalized Wikipedia table is direct evidence for **table reasoning**, but only transfer evidence for **recovering correct table structure from Excel/PDF/image input**.

Spreadsheet-specific searches are important because business spreadsheets contain formatting, merged regions, hierarchical headers and formulas that are absent from conventional relational-table benchmarks.

### F8 — Chart and data-visualization understanding — DIRECT

Charts are a smaller but directly relevant visual evidence class.

Seed literature:

- *DVQA: Understanding Data Visualizations via Question Answering* (2018). citeturn217084search2
- *PlotQA: Reasoning over Scientific Plots* (2020). citeturn979666search0
- *ChartQA: A Benchmark for Question Answering about Charts with Visual and Logical Reasoning* (2022). citeturn979666academia73
- *DePlot: One-shot Visual Language Reasoning by Plot-to-Table Translation* (2023). citeturn217084search4

Chart papers should be downgraded when questions are template-generated, the underlying table is supplied, or the visual extraction stage is bypassed.

### F9 — Cross-modal reference resolution and visual grounding — TRANSFER

This family covers mappings such as a phrase → visual object/region.

Canonical visual-grounding terminology is much more established than “cross-modal reference resolution.” Referring expression comprehension is normally defined as localizing the image region described by a linguistic expression; *MAttNet* is a clear example. citeturn344133search1

Multimodal coreference is also real academic terminology, but direct evidence is frequently outside documents. For example, *Semi-supervised Multimodal Coreference Resolution in Image Narrations* studies longer descriptive text paired with an image. citeturn344133search7

Therefore this family is **TRANSFER** unless a paper specifically studies documents, screenshots, tables or other structured visual surfaces.

### F10 — Screenshot and rendered-interface understanding — TRANSFER

Screenshot interpretation is useful because a work message may contain a screenshot whose visible layout and highlights carry evidence.

*Pix2Struct: Screenshot Parsing as Pretraining for Visual Language Understanding* is a strong seed: its pretraining task reconstructs simplified HTML from webpage screenshots and transfers across documents, illustrations, user interfaces and natural images. citeturn344133academia135

However, UI-agent work that only predicts clicks, actions or navigation should not be admitted as evidence for attachment interpretation.

### F11 — Document version comparison and semantic change localization — TRANSFER

There is no single mature task name that cleanly captures msgloom's requirement:

> identify attachment revision identity, preserve lineage, locate changes, distinguish semantic change from rendering noise, and determine which version supplied evidence.

Discovery should therefore search several neighboring literatures—document differencing, change detection, document revision analysis and semantic comparison—but label them TRANSFER unless they explicitly model revision provenance.

A pixel diff is insufficient: moving a paragraph may produce a large visual change without changing its meaning, while a one-character deadline change may be visually tiny but decision-critical.

### F12 — Email-to-attachment and workplace multimodal grounding — DIRECT

This is the exact-domain search and should be run despite likely sparse literature.

Target phenomena include:

- “see the highlighted row”;
- “numbers below”;
- “the red box is the issue”;
- “use attachment v2”;
- references from email prose into spreadsheet cells;
- references from prose into attached PDF pages;
- references to an inline screenshot or image;
- references whose intended attachment/version is ambiguous.

No seed paper is promoted here because no well-established canonical task paper was confidently identified. That absence should remain an explicit possible research gap rather than being filled with natural-image or cybersecurity papers.

### F13 — Figure-caption and document image-text association — TRANSFER

This family can contribute mechanisms for linking document prose, figure references and visual material. It remains TRANSFER because caption association is materially narrower than arbitrary workplace references to table cells, highlighted regions or attachment versions.

### F14 — Multimodal document retrieval — TRANSFER

This is supporting literature only. Page retrieval may make long-document processing feasible, but Topic 07 owns retrieval of missing context and Topic 08 owns interpretation after the relevant document or object is available.

Do not let retrieval papers dominate Topic 08 merely because they use document images.

## Query families

### F1 — DIRECT: layout, logical structure and reading order

- `"document layout analysis" logical structure reading order`
- `"document layout analysis" reading order document image`
- `"page segmentation" "reading order" document`
- `"logical layout analysis" document image`
- `"reading order detection" document layout`
- `"document structure analysis" regions hierarchy reading order`

### F2 — DIRECT: visually rich document understanding

- `"visually rich document understanding" layout image text`
- `"visually-rich document understanding" multimodal`
- `"document image understanding" text layout image`
- `"Document AI" multimodal layout understanding`
- `"layout-aware" document language model`
- `"multimodal document understanding" layout OCR`

### F3 — DIRECT: structured document information extraction

- `"document information extraction" layout multimodal`
- `"key information extraction" document layout image`
- `"structured text understanding" document multimodal`
- `"multimodal information extraction" document layout`
- `"entity linking" visually rich document`
- `"relation extraction" document image layout`

### F4 — DIRECT: DocVQA and multi-page understanding

- `"document visual question answering" layout`
- `"DocVQA" document structure`
- `"multi-page DocVQA"`
- `"multi-page document" visual question answering`
- `"multi-page document understanding" multimodal`
- `"long document" multimodal document question answering`
- `"document understanding" cross-page reasoning`

### F5 — DIRECT: evidence grounding and localization

This family should receive high priority because it most closely expresses the product's source-traceability requirement.

- `"grounded document VQA" bounding box`
- `"visually grounded document" question answering`
- `"document question answering" answer localization bounding box`
- `"document VQA" evidence grounding`
- `"document VQA" groundedness localization`
- `"document region grounding" question answering`
- `"document evidence grounding" page region`
- `"evidence-grounded" document question answering`

### F6 — DIRECT: table detection and TSR

- `"table structure recognition" document image`
- `"table structure recognition" header cell span`
- `"table detection" "structure recognition" document`
- `"table extraction" functional analysis document`
- `"table recognition" merged cells headers document`
- `"table structure" reading order document image`

### F7 — DIRECT: semantic tables and spreadsheets

- `"table understanding" hierarchical headers semantics`
- `"table question answering" hierarchical table`
- `"table question answering" document image`
- `"spreadsheet understanding" semantic structure`
- `"semantic table structure" spreadsheet`
- `"spreadsheet" cell role classification table structure`
- `"structured table" pretraining spreadsheet hierarchy`
- `"spreadsheet understanding" formulas formatting semantics`

### F8 — DIRECT: charts

- `"chart understanding" visual reasoning`
- `"chart question answering" visual grounding`
- `"chart QA" visual logical reasoning`
- `"plot question answering" chart elements`
- `"chart understanding" document image`
- `"chart-to-table" visual language reasoning`

### F9 — TRANSFER: visual grounding and cross-modal reference

- `"multimodal coreference resolution" image text`
- `"cross-modal reference resolution" image text`
- `"visual grounding" referring expression region`
- `"referring expression comprehension" visual grounding`
- `"phrase grounding" document region`
- `"referring expression" screenshot grounding`
- `"visual grounding" document screenshot`

### F10 — TRANSFER: screenshot understanding

- `"screenshot understanding" visual language`
- `"screenshot parsing" visual language understanding`
- `"screenshot" multimodal question answering`
- `"screen understanding" OCR layout visual`
- `"UI screenshot" visual grounding text`
- `"screenshot parsing" structure extraction`

### F11 — TRANSFER: version comparison

- `"document version comparison" semantic change`
- `"document differencing" layout change`
- `"visual document differencing"`
- `"document change detection" page image`
- `"PDF version comparison" semantic change`
- `"document revision" change localization layout`
- `"document version" change detection multimodal`

### F12 — DIRECT: workplace email and attachments

Security false positives will be heavy, so admission filtering must be strict.

- `"email attachment" semantic understanding document`
- `"email attachment" multimodal understanding`
- `"email" attachment reference grounding`
- `"email" "attached document" reference resolution`
- `"email" screenshot table attachment understanding`
- `"workplace communication" attachment document understanding`
- `"message" attachment cross-modal reference`
- `"email body" attachment grounding`

### F13 — TRANSFER: figure/caption association

- `"figure caption grounding" document`
- `"figure caption" region grounding`
- `"figure reference" document image grounding`
- `"figure-caption" alignment scientific document`
- `"text figure association" document understanding`

### F14 — TRANSFER: multimodal document retrieval

Run at low priority and do not treat it as a Topic 08 core family.

- `"multimodal document retrieval" page`
- `"visual document retrieval" layout text`
- `"document page retrieval" multimodal question answering`
- `"page retrieval" multi-page DocVQA`
- `"document retrieval" vision language layout`

## False friends and downgrade rules

Discovery should apply these rules before admitting papers:

1. **OCR is not understanding.** Character recognition, word recognition, dewarping, denoising, binarization and OCR-error correction alone are out of scope.
2. **A detected rectangle is not semantic structure.** Layout and table detection papers are supporting evidence unless they recover relations, roles, hierarchy, reading order or downstream semantics.
3. **Document classification is not enough.** A page-level label does not preserve evidence.
4. **KIE on fixed forms is narrower than Topic 08.** Admit it as core only when its mechanisms/evaluation genuinely address structural or multimodal relationships relevant to the topic.
5. **Image captioning is not grounding.** A caption can be plausible while being impossible to trace to the visual evidence that supports it.
6. **Generic VQA is not DocVQA.** Natural-image QA is TRANSFER unless document structure is part of the problem.
7. **Generic referring-expression comprehension is TRANSFER.** RefCOCO-style evidence cannot be presented as workplace-document accuracy.
8. **Generic multimodal coreference is TRANSFER.** Image narration, video and embodied-reference work need a documented mechanism-level transfer argument.
9. **Table detection ≠ TSR ≠ table semantics.** Record which level each paper evaluates.
10. **Normalized table QA does not validate PDF/Excel extraction.** It is useful evidence for reasoning after structure is correctly recovered.
11. **Cell values alone are insufficient.** Lost units, headers, row labels, merged relations or hierarchy are correctness failures.
12. **Spreadsheet editing agents are not automatically spreadsheet understanding.** Require evidence of semantic interpretation of existing sheets.
13. **Synthetic chart QA is weaker evidence.** Record whether the image must genuinely be parsed or whether source data are supplied.
14. **Attachment cybersecurity is out of scope.** Malware, phishing and malicious attachment detection should not enter the semantic-understanding corpus merely because they contain the word “attachment.”
15. **Email spam/phishing classification is out of scope.**
16. **UI action prediction is not screenshot evidence extraction.** Screenshot papers should recover or reason about visible structure, not merely choose a click.
17. **Scholarly citation localization is a false friend.** Citation recommendation, citation-context detection and bibliometrics do not implement source-region grounding.
18. **Retrieval is not understanding.** Multimodal document/page retrieval belongs primarily to Topic 07 and is supporting evidence here.
19. **Similarity is not version semantics.** Plagiarism, duplicate-document detection and generic similarity do not establish version identity, lineage or supersession.
20. **Pixel diff is not semantic diff.** Rendering regression and image registration should be TRANSFER unless meaningful document changes are distinguished from presentation noise.
21. **Filename is not version identity.** No literature should be credited with solving attachment revision tracking merely because it accepts two files.
22. **Page-level grounding is not region-level grounding.** Record the actual supported granularity: document, page, block, token, table, cell, region or bounding box.
23. **Answer occurrence is not evidence grounding.** Finding the generated answer string somewhere on the page does not prove the model reasoned from the correct source.
24. **Transfer-domain results remain transfer-domain results.** Scientific papers, forms, receipts, screenshots, natural images and synthetic charts cannot establish production Outlook/Teams accuracy.
25. **Unsupported content must remain visible as failure.** Silent omission of an embedded object, scanned page or unparsable region conflicts with the product's preservation contract.

## Date policy

**Earliest publication year discovery must include: 1984.**

This topic cannot use a transformer-era recency window. Relevant document-structure work predates modern Document AI by decades. A 1984 paper surveyed document segmentation and related document-image processing, and recursive hierarchical page segmentation was already being described in 1984 work on optically scanned documents. citeturn224505search0turn224505search5 By 1992, page segmentation and classification was an established research problem, and table-structure-recognition papers appear in the early 1990s. citeturn462191search0turn462191search7

Accordingly:

- **Bulk academic discovery window:** **1984–present**.
- Do not impose a “last 5/10 years” filter on F1 or F6.
- Recent model families such as LayoutLM/DocVQA should still dominate candidate-method work where appropriate, but they must be interpreted against the older layout/table foundations.
- If an admitted 1980s/1990s foundational source identifies a directly relevant pre-1984 predecessor, backward citation chasing may go earlier rather than treating 1984 as an absolute historical boundary.
- Publication age must not be used as a proxy for project value: old work can establish task definitions and failure modes, while recent work is more likely to provide deployable multimodal methods.

The resulting terminology hierarchy for discovery should therefore prioritize **visually rich document understanding, DocVQA/multi-page DocVQA, grounded document QA/evidence localization, document layout and reading order, table structure recognition, semantic table/spreadsheet understanding, and document-constrained cross-modal grounding**, while treating generic OCR, citation localization, generic visual grounding, attachment security, document retrieval and pixel differencing as supporting, transfer or false-friend literature rather than core evidence.
