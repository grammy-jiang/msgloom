# Cross-version multimodal document grounding: stable region and element lineage across revised attachments, message-to-attachment referring expressions, revised-workbook provenance, and end-to-end hierarchical evidence identifiers from version through page, region or cell to answer span — academic terminology analysis

## Product problem

The project problem is not simply “document understanding.” It combines four capabilities that are usually separated in the literature:

1. **Revision-aware document identity and lineage.** An attachment can have multiple revisions. Evidence cited from an earlier revision needs a stable identity, a version-relative location, an account of what semantically changed, and—when possible—a mapping from the old element or region to its later counterpart.
2. **Language-to-attachment grounding.** Message language such as “this screenshot,” “the highlighted row,” “the numbers below,” or “use attachment v2” must resolve to a concrete artifact, page or sheet, document object, spatial region, table row/cell, or workbook element.
3. **Workbook semantics beyond a flat table.** Spreadsheet evidence may depend on formulas, hidden rows or sheets, cross-sheet references, merged regions, named ranges, formatting, units, and dependencies that disappear when a workbook is flattened.
4. **End-to-end evidence provenance.** A useful representation must be able to identify the artifact and its version, then the page/sheet, element, region/cell, and ultimately the answer or evidence span. Missing support or failed extraction must be distinguishable from a successful finding of “nothing there.”

No single seed term names this complete problem. Discovery therefore needs several academic families and must distinguish **DIRECT** evidence from **TRANSFER** mechanisms.

## Seed keyword audit

| Seed | Academic meaning | Fit | Main risk | Typical false positives |
|---|---|---:|---|---|
| document AI | Umbrella for OCR, classification, layout, extraction, tables, QA, and related document ML | MODERATE | Much broader than provenance, version lineage, or grounding | OCR-only, classification, invoice extraction, commercial IDP |
| document intelligence | Broad and partly industry-driven label for automated document processing and reasoning | MODERATE | Not a precise academic task name | Commercial platforms, workflow automation, generic extraction |
| visually rich document understanding | Joint understanding of text, layout, visual appearance, and document structure | STRONG | Usually assumes one document state and no revision lineage | Classification or key-value extraction with layout |
| VRDU | Abbreviation for visually rich document understanding | STRONG | Not universally used, so exact-term searches miss papers | Broad VRDU papers with only classification/field extraction |
| document layout analysis | Segmentation/classification of page zones and spatial relationships | STRONG | Layout segmentation does not itself imply semantic grounding | Page zoning, OCR preprocessing, object detection |
| layout-aware language models | Models encoding language jointly with 2-D position/layout or image features | STRONG | Architecture alone does not prove evidence preservation | Token labeling or classification using boxes |
| document information extraction | Structured extraction of fields, entities, relations, or key-value pairs | STRONG | Often discards exact source provenance | Invoice/receipt IE, template extraction |
| document visual question answering | QA over document images using text, layout, and visual evidence | STRONG | Usually scores answer correctness rather than complete evidence provenance | Answer-only DocVQA |
| DocVQA | Established document-image VQA benchmark/task label | STRONG | A DocVQA system can return only an answer string | Leaderboard QA with no region evidence |
| multi-page document understanding | Reasoning over multiple pages and cross-page context | STRONG | Multi-page support does not imply exact source traces | Page ranking, page compression, classification |
| long-document multimodal understanding | Understanding long documents containing text, pages, figures, tables, etc. | STRONG | Often primarily about context length and efficiency | Long-context summarization without grounding |
| OCR layout understanding | Informal phrase for combining OCR and spatial layout | MODERATE | Not a canonical task name; OCR dominates results | Character/word OCR and post-correction |
| reading order detection | Recovering intended sequence among page blocks/elements | STRONG | Commonly evaluated independently of semantic preservation | Simple geometric sorting |
| table detection | Localizing tables within documents | MODERATE | Does not recover cell structure or semantics | Table bounding-box detection |
| table structure recognition | Recovering rows, columns, cells, headers, and spanning structures | STRONG | Usually rendered-table focused rather than workbook focused | Structure reconstruction without semantics |
| table understanding | Semantic reasoning over headers, values, relations, and table context | STRONG | Often assumes a clean structured table | Web-table or relational-table representation learning |
| table question answering | Answering questions from tabular data | MODERATE | Usually bypasses extraction/layout and workbook structure | WikiTableQuestions, text-to-SQL |
| spreadsheet understanding | Interpretation of workbook structure, cells, formulas, sheets, and business semantics | STRONG | Recent work may still omit hidden content, formulas, names, or revision provenance | CSV reasoning and selected-range prompting |
| chart understanding | Interpretation of graphical marks, labels, axes, legends, and values | MODERATE | Secondary attachment class, not the core gaps | Chart classification or chart-to-text |
| chart question answering | QA over charts and graphical data | MODERATE | Typically isolated from documents and versions | Standalone chart benchmarks |
| multimodal information extraction | Extraction using text plus visual/layout modalities | STRONG | Extends well beyond document research | Social-media or image-text entity extraction |
| multimodal coreference resolution | Coreference where antecedent/referent can be visual | MODERATE | Dominated by dialogue/video/natural-image domains | Video, embodied dialogue, generic multimodal coreference |
| cross-modal reference resolution | Resolving expressions across modality boundaries | STRONG | Less standardized wording; cross-modal retrieval can contaminate results | Image-text matching and retrieval |
| visual grounding | Mapping language to visual entities or regions | STRONG | Dominated by natural scenes and GUIs | Object grounding, robotics, navigation |
| referring expression comprehension | Selecting the object/region denoted by a referring expression | STRONG | Classical datasets use natural images rather than documents | RefCOCO/ReferIt-style natural-scene work |
| document region grounding | Language/evidence mapping to spatial document regions | STRONG | Emerging terminology rather than one stable benchmark name | Object detection or page segmentation without language |
| citation localization | Locating supporting evidence or citation-related text | MODERATE | Strong ambiguity with bibliometrics and citation-context research | Citation intent/context/recommendation |
| scanned document understanding | Semantic processing of rasterized/scanned document pages | STRONG | Searches often collapse into OCR | OCR-only archive digitization |
| document version comparison | Comparing revisions and identifying document changes | STRONG | Generic phrase; often retrieves redline tools or text diff | Legal redlining, lexical diff, document-management software |
| visual document differencing | Detecting differences between rendered document versions | MODERATE | Pixel changes are not semantic lineage | Screenshot regression and pixel diff |
| attachment content extraction | Product term for extracting attached-file content | WEAK | Not an established academic task name | MIME parsing, malware scanning, commercial extraction |
| email attachment understanding | Product description for joint message/attachment reasoning | WEAK | Exact academic phrase may have little literature | Attachment malware/classification/search |
| screenshot understanding | Understanding rendered screens or UIs | MODERATE | Modern literature is GUI-agent dominated | Click prediction, UI navigation, screen-to-code |
| figure caption grounding | Linking figures/regions to captions or textual mentions | WEAK | Too narrow for the central gaps | Figure retrieval and caption generation |
| multimodal document retrieval | Retrieving documents/pages with textual and visual representations | REJECT | Primarily Topic 07 and not evidence of interpretation or grounding | RAG, page retrieval, cross-modal ranking |

### Terminology promoted for round 3

The most useful refinements are:

- **cross-version document element alignment**
- **document element correspondence across revisions**
- **semantic document differencing**
- **document revision lineage**
- **version-aware document provenance**
- **region lineage**
- **document-object grounding**
- **document region grounding**
- **document referring-expression grounding**
- **cross-modal reference resolution**
- **evidence-grounded document question answering**
- **document evidence localization**
- **page-region evidence attribution**
- **workbook-level spreadsheet understanding**
- **spreadsheet formula dependency analysis**
- **spreadsheet cell lineage**
- **spreadsheet provenance**
- **spreadsheet versioning / spreadsheet differencing**
- **cross-sheet dependency analysis**
- **merged-cell structure recognition**
- **named-range analysis**
- **table cell grounding**
- **reading-order reconstruction**
- **layout-preserving document parsing**
- **fine-grained evidence provenance**
- **region-level provenance / cell-level provenance**
- **unanswerable document question answering**
- **failure-aware document grounding**
- **structural-preservation evaluation**

The broad terms `document AI`, `document intelligence`, `OCR layout understanding`, `attachment content extraction`, `email attachment understanding`, `screenshot understanding`, `figure caption grounding`, and `multimodal document retrieval` should not be primary discovery terms without stronger qualifiers.

## Academic task families

### F1 — Cross-version document element alignment and semantic document differencing — DIRECT

Align regions, paragraphs, tables, figures, or other objects across revisions and identify unchanged, moved, modified, inserted, deleted, split, or merged content.

This is the nearest academic family to **gap-1**, but pairwise diff is not enough. A relevant paper must be examined for persistent correspondence and semantic change rather than merely changed pixels or changed text.

Known seeds already present in the programme:

- `VersionRAG` — bibliographic details are not supplied in this prompt.
- `arXiv:2607.14117` — prior-round seed covering cross-version element alignment; title is not supplied here.

### F2 — Versioned artifact provenance and revision lineage — TRANSFER

Database provenance, scientific-workflow provenance, data versioning, and other lineage research study identity and derivation across changing states.

Useful foundational seeds include:

- *Why and Where: A Characterization of Data Provenance* — Buneman, Khanna, and Tan, 2001.
- *Provenance Semirings* — Green, Karvounarakis, and Tannen, 2007.

These are representation mechanisms, not direct evidence that workplace document regions can be tracked.

### F3 — Document-object visual grounding and referring-expression comprehension — DIRECT

Maps language to a document object, bounding region, text block, table component, or cell.

This is the most direct terminology for **gap-2**. Searches should include the actual linguistic forms that matter—demonstratives, highlights, rows, “below,” screenshots, and attachment references—not merely generic visual grounding.

### F4 — Natural-scene referring-expression grounding — TRANSFER

Classical referring-expression comprehension supplies objectives and evaluation methods for language-to-region mapping.

A known foundational seed is:

- *ReferItGame: Referring to Objects in Photographs of Natural Scenes* — Kazemzadeh et al., 2014.

It is transfer evidence only unless evaluated on documents.

### F5 — Multimodal coreference and visually grounded dialogue — TRANSFER

Cross-modal discourse research can model phrases whose referents are visible objects introduced outside the immediate text.

A useful seed is:

- *Visual Dialog* — Das et al., 2017.

The mechanism is relevant to message-to-attachment reference resolution, but the domain differs materially.

### F6 — Evidence-grounded document visual question answering — DIRECT

The important refinement over ordinary DocVQA is **evidence-grounded** DocVQA: page, region, box, cell, or supporting span should be part of the target or evaluation.

Known seeds include:

- *DocVQA: A Dataset for VQA on Document Images*.
- *QASPER: A Dataset for Question Answering over Scientific Research Papers*.

QASPER is particularly useful for evidence annotations, although scientific papers are not workplace attachments.

### F7 — Workbook-level spreadsheet understanding — DIRECT

Search for workbooks rather than tables. Relevant methods must be capable of preserving multiple sheets and, ideally, formulas, hidden content, merged cells, named ranges, formatting, units, and cross-sheet relationships.

Known recent seeds include:

- *SpreadsheetLLM: Encoding Spreadsheets for Large Language Models*.
- *SheetCopilot*.

These should be inspected carefully rather than assumed to cover the entire gap.

### F8 — Spreadsheet formula dependency, change impact, versioning, and cell lineage — DIRECT

This family supplements modern spreadsheet-LLM work with program-analysis and provenance terminology:

- formula dependency
- dependency graph
- cross-sheet references
- change impact
- spreadsheet versioning
- spreadsheet differencing
- cell lineage
- spreadsheet provenance

It is important for both **gap-1** and **gap-3**.

### F9 — Table structure recognition and semantic table understanding — DIRECT

The useful task is not just detecting a table. Discovery should emphasize rows, columns, headers, spanning or merged cells, units, and cell-level evidence.

A known seed is:

- *PubTables-1M: Towards Comprehensive Table Extraction From Unstructured Documents*.

### F10 — Document layout analysis, reading-order reconstruction, and scanned-document structure — DIRECT

This family supplies foundational mechanics for preserving heterogeneous attachments.

Known seeds include:

- *The Document Spectrum for Page Layout Analysis* — O'Gorman, 1993.
- *LayoutLM: Pre-training of Text and Layout for Document Image Understanding* — 2020.

For this project, reading-order correctness and structural preservation matter more than layout segmentation in isolation.

### F11 — Multimodal document information extraction with source localization — DIRECT

Information extraction should be combined with terms such as:

- bounding box
- source localization
- page region
- provenance
- evidence localization

Known architecture seeds include:

- *LayoutLM: Pre-training of Text and Layout for Document Image Understanding*.
- *LayoutLMv2: Multi-modal Pre-training for Visually-Rich Document Understanding*.

Field extraction with no source location should be downgraded.

### F12 — Hierarchical evidence provenance and fine-grained source attribution — TRANSFER

The complete hierarchy required by **gap-4**—

`attachment version -> page/sheet -> element -> region/cell -> answer span`

—is not itself a standard academic task.

Relevant mechanisms therefore come from:

- data provenance,
- fine-grained lineage,
- QA supporting-evidence annotation,
- answer attribution,
- region evidence,
- cell provenance.

This family must remain labeled TRANSFER unless a paper actually evaluates the complete document hierarchy.

### F13 — Unanswerable document QA, abstention, and failure-aware grounding — TRANSFER

The engineering requirement is stronger than ordinary unanswerable QA because it must distinguish:

- genuine absence,
- unsupported feature,
- parser failure,
- OCR failure,
- layout failure,
- retrieval/localization failure,
- grounding failure.

A foundational transfer seed is:

- *Know What You Don't Know: Unanswerable Questions for SQuAD* / SQuAD 2.0 — 2018.

### F14 — Long and multi-page multimodal document reasoning — DIRECT

This family addresses long documents, large contexts, page selection, compression, memory, and information loss.

A known seed is:

- *MP-DocVQA: Multi-page Document Visual Question Answering*.

For **gap-7**, discovery should prefer work reporting the consequences of scaling choices, not only throughput.

### F15 — Screenshot and GUI grounding — TRANSFER

Screenshot grounding is useful for visual references and highlighted regions, but GUI-action benchmarks should not be mistaken for document semantics.

Known seeds include:

- *SeeClick: Harnessing GUI Grounding for Advanced Visual GUI Agents*.
- *ScreenAI: A Vision-Language Model for UI and Infographics Understanding*.

### F16 — Chart and structured-graphic question answering with evidence — DIRECT

Charts are a secondary but relevant attachment class.

A known seed is:

- *ChartQA*.

The most useful work will include evidence localization rather than answer strings only.

### F17 — Document extraction robustness and structural-preservation evaluation — DIRECT

This family is the academic precursor to the engineering work required by **gap-6** and **gap-8**.

Searches should explicitly combine document extraction with:

- sparse tables,
- merged structures,
- OCR corruption,
- irregular reading order,
- embedded images,
- scanned pages,
- extraction completeness,
- structural preservation,
- failure analysis.

## Query families

### F1 — DIRECT: cross-version element alignment

- `"document version alignment" element alignment revision semantic change`
- `"document revision" "element alignment" cross-version`
- `"cross-version" document element correspondence alignment`
- `"document differencing" semantic structural alignment revisions`
- `"semantic diff" document revisions paragraphs tables figures`
- `"document change detection" layout semantic correspondence version`
- `"version-aware" document alignment provenance region`
- `"revision lineage" document regions elements`

### F2 — TRANSFER: revision provenance

- `"versioned data provenance" lineage revisions`
- `"data versioning" provenance lineage change history`
- `"provenance" versioned artifacts revision lineage`
- `"why provenance" version history data lineage`
- `"fine-grained provenance" versioned data`
- `"provenance semiring" versioning updates`
- `"artifact lineage" revision provenance`

### F3 — DIRECT: document referring-expression grounding

- `"document grounding" referring expression region`
- `"document region grounding" language`
- `"referring expression" document region table cell`
- `"visual grounding" document table cell text region`
- `"phrase grounding" document image region`
- `"language grounding" document layout region`
- `"grounded reference" document screenshot table`
- `"referring expression comprehension" document image`
- `"highlighted row" document grounding`
- `"message" attachment referring expression grounding`
- `"email" attachment reference grounding document`
- `"this screenshot" visual grounding document`

### F4 — TRANSFER: classical referring expressions

- `"referring expression comprehension" visual grounding`
- `"referring expression grounding" ambiguous reference region`
- `"phrase grounding" referring expressions region localization`
- `"referring expression" spatial relations grounding`
- `"referring expression comprehension" context objects`

### F5 — TRANSFER: multimodal reference resolution

- `"multimodal coreference resolution" visual`
- `"cross-modal coreference" dialogue image`
- `"visual coreference" dialogue grounding`
- `"visually grounded dialogue" reference resolution`
- `"multimodal reference resolution" dialogue`
- `"deictic reference" visual grounding dialogue`
- `"demonstrative reference" image grounding dialogue`

### F6 — DIRECT: evidence-grounded DocVQA

- `"document visual question answering" evidence grounding`
- `"DocVQA" evidence localization region`
- `"document question answering" bounding box evidence`
- `"document question answering" supporting evidence page region`
- `"document VQA" answer grounding bounding box`
- `"document QA" evidence span localization`
- `"multi-page DocVQA" evidence page grounding`
- `"document question answering" provenance evidence`

### F7 — DIRECT: workbook-level spreadsheet understanding

- `"spreadsheet understanding" workbook formulas`
- `"spreadsheet understanding" multi-sheet formulas formatting`
- `"workbook understanding" spreadsheet language model`
- `"spreadsheet reasoning" cross-sheet references formulas`
- `"spreadsheet" hidden sheets hidden rows understanding`
- `"spreadsheet" named ranges merged cells semantics`
- `"spreadsheet understanding" formatting semantics units`
- `"workbook" formulas named ranges merged cells`
- `"spreadsheet QA" workbook multi-sheet`
- `"spreadsheet agent" workbook inspection structure`

### F8 — DIRECT: spreadsheet lineage and dependency

- `"spreadsheet provenance" cell lineage`
- `"spreadsheet data lineage" formulas`
- `"cell provenance" spreadsheet formulas`
- `"spreadsheet versioning" change tracking formulas`
- `"spreadsheet differencing" workbook versions`
- `"spreadsheet change detection" formula dependencies`
- `"formula dependency" spreadsheet analysis`
- `"spreadsheet dependency graph" formulas cross-sheet`
- `"spreadsheet change impact" formulas cells`
- `"workbook version" provenance cell`

### F9 — DIRECT: table structure and cell grounding

- `"table structure recognition" merged cells spanning cells`
- `"table structure recognition" headers rows columns`
- `"table understanding" hierarchical headers units`
- `"table extraction" merged cells sparse tables`
- `"table structure" semantic headers units document`
- `"table understanding" document layout provenance`
- `"table cell grounding" question answering`
- `"table question answering" evidence cell grounding`

### F10 — DIRECT: layout, reading order, and scans

- `"document layout analysis" reading order`
- `"reading order detection" document layout`
- `"reading order reconstruction" scanned document`
- `"document layout analysis" scanned pages tables figures`
- `"layout-aware" document understanding reading order`
- `"scanned document understanding" layout OCR`
- `"document structure extraction" reading order embedded images`
- `"page layout analysis" irregular reading order`

### F11 — DIRECT: extraction with exact source location

- `"document information extraction" source localization bounding box`
- `"multimodal information extraction" document layout region`
- `"document information extraction" provenance region`
- `"visually rich document" information extraction grounding`
- `"layout-aware" information extraction evidence localization`
- `"document extraction" page region provenance`
- `"multimodal document extraction" bounding box evidence`

### F12 — TRANSFER: fine-grained evidence provenance

- `"fine-grained provenance" evidence source span`
- `"evidence provenance" question answering source span`
- `"evidence attribution" question answering document span`
- `"source attribution" answer evidence span document`
- `"hierarchical provenance" document page region`
- `"provenance" page region answer span`
- `"evidence localization" page region answer`
- `"cell-level provenance" answer`
- `"region-level provenance" document`
- `"claim evidence" provenance span localization`

### F13 — TRANSFER: unsupported and failure-aware behavior

- `"unanswerable" document question answering`
- `"unanswerable questions" DocVQA`
- `"abstention" document question answering`
- `"selective prediction" document VQA`
- `"answerability" document question answering evidence`
- `"grounding failure" document question answering`
- `"OCR failure" document QA unanswerable`
- `"parser failure" document understanding evaluation`
- `"evidence not found" document question answering`

### F14 — DIRECT: long and multi-page documents

- `"multi-page document understanding" multimodal`
- `"multi-page DocVQA" long document`
- `"long-document multimodal understanding" pages`
- `"long document" multimodal question answering page retrieval`
- `"multi-page document" evidence grounding`
- `"long document VQA" memory efficiency`
- `"document VQA" page compression information loss`
- `"large document" multimodal reasoning scaling`

### F15 — TRANSFER: screenshot and GUI grounding

- `"screenshot grounding" referring expression`
- `"GUI grounding" referring expression screenshot`
- `"screen grounding" natural language region`
- `"visual grounding" screenshot text region`
- `"UI grounding" phrase region coordinates`
- `"screen understanding" reference resolution`
- `"highlighted region" screenshot grounding`

### F16 — DIRECT: charts and structured graphics

- `"chart question answering" evidence grounding`
- `"chart understanding" region grounding`
- `"chart QA" evidence localization`
- `"chart question answering" provenance`
- `"chart understanding" document context`

### F17 — DIRECT: robustness and preservation

- `"document parsing" robustness heterogeneous documents layout`
- `"document understanding" robustness OCR layout errors`
- `"document extraction" benchmark sparse tables merged cells`
- `"document parser" embedded images scanned pages reading order`
- `"layout analysis" robustness OCR corruption`
- `"table extraction" robustness sparse tables merged cells OCR`
- `"document understanding benchmark" extraction completeness`
- `"document extraction" reading order preservation evaluation`
- `"document AI" structural preservation benchmark`
- `"document understanding" failure analysis OCR layout grounding`

## False friends and downgrade rules

Discovery should downgrade or exclude the following even when the wording matches:

1. **OCR-only work.** Character, word, and line accuracy does not establish layout, table semantics, provenance, or grounding.
2. **Document classification.** Classifying a page or file does not solve any of the high-priority lineage or grounding gaps.
3. **Field extraction without localization.** Correct key-value output is insufficient if its page/region/cell provenance is discarded.
4. **Answer-only DocVQA.** An answer string without supporting page, region, box, cell, or span does not close gap-4.
5. **Natural-image VQA.** Generic VQA is not relevant unless it contributes an explicit transferable grounding mechanism.
6. **Natural-scene referring expressions.** Admit as TRANSFER only; RefCOCO/ReferIt results cannot establish workplace-document accuracy.
7. **GUI clicking.** Screenshot-coordinate prediction is TRANSFER unless it handles document-specific structures such as rows, tables, or cells.
8. **Multimodal dialogue outside documents.** Useful for reference mechanisms, not direct evidence for attachments.
9. **Bibliometric “citation localization.”** Citation contexts, citation intent, recommendation, and bibliographic linking are different tasks.
10. **Document-level citation generation.** Citing a URL or whole file is not page/region/cell evidence localization.
11. **Generic multimodal retrieval/RAG.** Document/page retrieval belongs primarily to Topic 07 unless exact within-document evidence grounding is also evaluated.
12. **Version-aware retrieval without lineage.** Selecting the correct revision is not the same as mapping an earlier cited element to its later counterpart.
13. **Text diff/redlining.** Lexical insert/delete reporting is insufficient without structural or semantic element correspondence.
14. **Pixel diff.** Visual changes are not stable semantic lineage unless regions are tied to persistent objects.
15. **Filename/hash identity.** Filenames, timestamps, checksums, and duplicate detection can support artifact identity but not semantic revision correspondence.
16. **Source-code version control.** AST or code-lineage work is TRANSFER at most unless a method is explicitly generalized to document/spreadsheet structures.
17. **Database provenance.** Useful TRANSFER evidence for provenance representation, but it does not validate page/region/cell grounding.
18. **Table detection alone.** A table bounding box says nothing about headers, merged cells, row/column relationships, units, or cell evidence.
19. **Clean-table QA.** Work starting from an already structured table bypasses the extraction and layout problems central to Topic 08.
20. **Text-to-SQL.** Relational semantic parsing is not document or workbook understanding.
21. **Flattened spreadsheet prompting.** Selected ranges serialized to CSV/text cannot establish support for hidden sheets, formulas, names, merged regions, formatting, or cross-sheet dependencies.
22. **Spreadsheet formula generation alone.** Formula synthesis or editing does not establish workbook interpretation or revision provenance.
23. **Single-sheet/single-cell manipulation.** Do not generalize to workbook-level understanding.
24. **Metadata-only version comparison.** Comparing file names, timestamps, or version labels does not provide element lineage.
25. **Layout segmentation without reading order.** Region detection alone cannot support claims about preserved textual sequence.
26. **Parser speed benchmarks.** Throughput and latency are secondary when completeness and meaning preservation are unmeasured.
27. **Semantic accuracy alone.** A benchmark does not close gap-8 unless it also addresses extraction completeness, provenance, unsupported evidence, and structural preservation as required by the claimed result.
28. **Collapsed failure states.** A system that represents parser failure, OCR failure, grounding failure, and genuine absence using the same empty result is not adequate evidence for gap-5.
29. **Figure-caption-only work.** Relevant only to figure-specific findings.
30. **Email attachment metadata.** MIME parsing, malware detection, attachment-name extraction, and presence classification do not ground message text into attachment content.
31. **Synthetic-domain overclaiming.** Scientific documents, natural images, GUIs, web pages, and synthetic data can support methods or experiments but cannot establish production-email accuracy.
32. **Pairwise alignment presented as persistent lineage.** Stable lineage requires considering correspondence through multiple revisions and cases such as insertion, deletion, movement, split, and merge.
33. **Bounding boxes presented as complete provenance.** Gap-4 requires the larger hierarchy including version and page/sheet and, where applicable, element/cell and answer span.
34. **Visible cells presented as full workbook support.** Hidden rows/sheets, formulas, names, cross-sheet references, merged regions, formatting semantics, and units remain separate capabilities until tested.
35. **Commercial IDP material.** Product pages, parser documentation, and feature matrices may inform later ENGINEERING work but are not academic evidence.

## Date policy

**Earliest publication year to include: 1990.**

A recent-only window would be methodologically wrong for this topic. The language-model and multimodal-document literature is recent, but the structural substrate is much older: page-layout analysis, document segmentation, reading-order recovery, table recognition, and document-image analysis were established research areas by the early 1990s. O'Gorman's 1993 work on page-layout analysis is one clear example of why a 2015-, 2020-, or even 2000-only search would remove relevant foundations.

The practical discovery policy should therefore be:

- global floor: **1990**;
- emphasize the 2000s onward for provenance and data lineage;
- emphasize the 2010s onward for visual grounding, multimodal coreference, and modern document QA;
- emphasize the 2020s for LayoutLM-family models, multi-page DocVQA, spreadsheet LLMs, GUI grounding, and current multimodal document models;
- do not exclude older work merely because its terminology predates “Document AI,” “VRDU,” or “multimodal document understanding.”

Round 3 should be targeted rather than broad. The older date floor exists to avoid silent loss of foundational work; it does not justify filling the corpus with generic historical OCR papers.
