# Version-aware multimodal evidence provenance and reference grounding across revised workplace attachments academic terminology analysis

## Product problem

The project is not merely doing document parsing. It needs an evidence model in which an answer can remain traceable through a hierarchy such as:

`attachment identity → attachment version → page/sheet → document element → region/cell → supporting answer span`

and, when a document is revised, it additionally needs correspondence such as:

`version N evidence region → version N+1 counterpart → change type/semantic change`.

Four academic gaps dominate this round:

1. **Cross-version evidence lineage**: preserving stable identity and locating corresponding text, table, figure, formula, or region across revisions.
2. **Cross-modal referring expressions into attachments**: grounding phrases such as “this screenshot”, “the highlighted row”, and “numbers below” to a particular region, table, cell, or visual element.
3. **Workbook-level spreadsheet semantics**: understanding formulas, dependencies, multiple sheets, formatting, merged structures, names, hidden content, and workbook relationships rather than treating a spreadsheet as one flat table.
4. **Hierarchical evidence provenance**: evaluating not merely whether an answer is correct, but whether its exact supporting version, page, element, region/cell, and answer-linked span are correct.

The terminology audit therefore separates broad Document AI vocabulary from the narrower task names that can actually close these gaps.

Recent literature confirms that several of the most precise task formulations are only now emerging. BoundingDocs explicitly adds answer bounding boxes to document QA, BBox DocVQA evaluates bounding-box-grounded evidence, and M3Grounder links generated answer spans with localized evidence masks. citeturn342619academia67turn342619academia64turn342619search1 Cross-version document work is also becoming more explicit: recent work studies heterogeneous element alignment across scientific-document versions and page matching plus multi-layer differencing across revision cycles. citeturn363858academia41turn363858academia42

## Seed keyword audit

| Seed | Academic meaning | Fit | Main risk | False-positive literature |
| --- | --- | --- | --- | --- |
| document AI | Broad umbrella for ML and multimodal document processing. | MODERATE | Too broad to isolate the open gaps. | OCR, classification, invoice automation, generic IDP. |
| document intelligence | Broad interpretation and extraction from documents. | MODERATE | Heavy vendor/product usage and weak task specificity. | Enterprise automation, invoice/receipt processing, commercial platforms. |
| visually rich document understanding | Joint modelling of text, 2-D layout and visual appearance. | STRONG | Often single-page and field-extraction oriented. | Form/receipt extraction with no provenance. |
| VRDU | Acronym for visually rich document understanding. | STRONG | Acronym-only search can be noisy and incomplete. | Broad VRDU benchmarks without required grounding. |
| document layout analysis | Segmentation and structural interpretation of document pages. | STRONG | Geometry alone does not establish semantics or provenance. | Region segmentation without logical order or downstream grounding. |
| layout-aware language models | Language/multimodal models incorporating coordinates and document layout. | STRONG | Often assumes perfect OCR and one page. | Form understanding where layout is merely another input feature. |
| document information extraction | Extraction of fields, entities, relations or key-value records. | MODERATE | Predefined-schema extraction is narrower than general evidence interpretation. | NER, invoice fields, receipt extraction. |
| document visual question answering | QA over document images using text, layout and visual evidence. | STRONG | Many benchmarks score answer text only. | Answer-only DocVQA with no evidence localization. |
| DocVQA | Established document-image VQA task family. | STRONG | Different datasets have very different evidence and page assumptions. | Single-page answer extraction treated as complete grounding. |
| multi-page document understanding | Understanding and QA over documents containing multiple pages. | STRONG | Relevant-page identification can be mistaken for exact provenance. | Page selection with no region/cell evidence. |
| long-document multimodal understanding | Long-context reasoning over PDFs with text, tables, figures and layouts. | STRONG | Can degrade into plain-text long-context evaluation. | OCR-flattened long-document QA. |
| OCR layout understanding | OCR combined with spatial or structural interpretation. | MODERATE | Not a sharply standardized task label. | OCR or text-line detection alone. |
| reading order detection | Recover logical sequence among document regions or lines. | STRONG | Necessary structural signal but not semantic understanding by itself. | Page segmentation without order evaluation. |
| table detection | Locate table regions. | MODERATE | Stops before cell and semantic structure. | Table bounding-box detectors. |
| table structure recognition | Recover rows, columns, cells, spanning/merged relationships. | STRONG | May reconstruct HTML yet miss semantics or workbook context. | Structure-only reconstruction. |
| table understanding | Broad representation and reasoning over structured tables. | STRONG | Frequently assumes already-clean relational tables. | Wikipedia/CSV reasoning with no extraction problem. |
| table question answering | Natural-language QA over tabular data. | MODERATE | Usually bypasses visual and structural extraction. | QA on normalized relational tables. |
| spreadsheet understanding | Understanding spreadsheet values, layout, formulas, styles and structure. | STRONG | Some papers actually operate on one table or one sheet. | CSV QA or isolated table classification. |
| chart understanding | Recover meaning from axes, series, labels and visual encodings. | MODERATE | Only a subset of attachments requires it. | Chart generation or classification. |
| chart question answering | QA over chart evidence. | MODERATE | Answer accuracy need not imply grounded chart evidence. | Synthetic QA with no localization. |
| multimodal information extraction | IE combining language and visual/layout information. | MODERATE | Extremely broad across domains. | Multimodal NER and social-media IE. |
| multimodal coreference resolution | Resolve mentions to entities across text and visual modalities. | MODERATE | Existing data is usually dialogue or natural imagery rather than documents. | Person/object coreference in photos or video. |
| cross-modal reference resolution | Link a linguistic mention to a referent in another modality. | STRONG | Exact phrase is less standardized than REC or phrase grounding. | Generic image-text alignment. |
| visual grounding | Localize language in visual regions or objects. | MODERATE | Natural-image literature dominates. | Object/phrase grounding in photographs. |
| referring expression comprehension | Identify the object/region denoted by a linguistic expression. | MODERATE | Strong transfer method but normally no document structure. | RefCOCO/ReferIt-style object localization. |
| document region grounding | Ground language or answers to document regions. | STRONG | Emerging terminology; many relevant papers use different names. | Whole-page retrieval presented as grounding. |
| citation localization | Ambiguous localization of citations or supporting sources. | WEAK | Strongly contaminated by bibliometrics and RAG citation work. | Citation-context detection and bibliography linking. |
| scanned document understanding | Interpretation of rasterized documents. | MODERATE | Often stops at OCR or page segmentation. | OCR, deskewing and denoising. |
| document version comparison | Compare revisions and determine changed/corresponding content. | STRONG | Frequently text-only or XML-only. | Word diff, source-code diff, XML tree diff. |
| visual document differencing | Compare rendered document revisions visually or structurally. | MODERATE | Not yet a uniform task name and may reduce to pixel differencing. | Screenshot/pixel comparison sensitive to rendering noise. |
| attachment content extraction | Engineering phrase for parsing attached files. | WEAK | Not a stable academic task. | MIME extraction, e-discovery, malware analysis. |
| email attachment understanding | Product-level description of interpreting attachments in message context. | REJECT | Sparse academically and dominated by unrelated email/security work. | Phishing, malicious attachments, attachment recommendation. |
| screenshot understanding | Interpretation of text-rich screenshots or UI captures. | MODERATE | GUI-agent literature dominates. | UI navigation and mobile-screen understanding. |
| figure caption grounding | Link captions/phrases to figures or graphical regions. | MODERATE | Often solves caption pairing rather than arbitrary reference grounding. | Caption generation and figure-caption matching. |
| multimodal document retrieval | Retrieve relevant documents/pages using multimodal representations. | WEAK | Retrieval belongs primarily to Topic 07 and stops before interpretation. | Search/ranking without precise evidence localization. |

Several seeds therefore need to be **promoted into more precise academic terms**. In particular, searches should prefer **cross-version document alignment**, **cross-version element matching**, **layout-aware document differencing**, **document referring-expression grounding**, **evidence-grounded DocVQA**, **answer grounding**, **spatial evidence attribution**, **semantic evidence grounding**, **workbook-level spreadsheet understanding**, **formula-aware spreadsheet reasoning**, and **fine-grained provenance**.

Conversely, `document AI`, `document intelligence`, `attachment content extraction`, `email attachment understanding`, `citation localization`, and generic `multimodal document retrieval` should not drive gap-closing discovery.

## Academic task families

### TF1 — Cross-version document alignment, differencing, and element lineage — DIRECT

This is the closest task family to gap-1. Relevant work must align entities across actual revisions rather than merely noticing that two files differ. Required concepts include page correspondence, element matching, insert/delete/move/change classification, spatial alignment, and semantic comparison.

The recent paper **Heterogeneous Element-Aware Cross-Version Differencing of Scientific Documents via Layout-Aware Alignment and Structure-Aware Reasoning** explicitly aligns typed elements such as text, tables, formulas, and figures across versions. citeturn363858academia41 A separate 2026 building-permit study explicitly performs page matching across revision cycles before text-, table-, and pixel-level differencing. citeturn363858academia42 These are materially closer to the project's version-lineage problem than ordinary text diff.

**Admission pressure:** prefer papers that evaluate cross-version matching quality, not merely change detection.

### TF2 — Version-aware QA over evolving documents — DIRECT

A second relevant family asks questions against documents whose contents evolve over time. This can establish methods for stable version identity, temporal validity, change tracking, and selecting evidence from the correct revision.

**VersionRAG: Version-Aware Retrieval-Augmented Generation for Evolving Documents** explicitly frames versioned document QA as distinct from ordinary retrieval and models version sequences and changes. citeturn363858academia44

This remains only partial evidence for gap-1 unless a method also identifies the exact evidence region and connects that region to its counterpart in another version.

### TF3 — Document-centric cross-modal reference grounding — DIRECT

This is the desired direct task for expressions such as:

- “this screenshot”;
- “the highlighted row”;
- “the numbers below”;
- “see the red box”;
- “use the second table”;
- “the value in attachment v2”.

The academic search should therefore target combinations such as **document referring expression**, **text-to-region document grounding**, **language-to-cell grounding**, **multimodal reference resolution + document**, and **referring expression + table/document**.

A sparse result set in this family is itself informative: it would distinguish a real academic gap from a terminology failure.

### TF4 — Multimodal coreference and referring expression comprehension — TRANSFER

This is the major transfer family for gap-2.

ReferItGame established a large-scale natural-image referring-expression setting in which language identifies a target region. citeturn708314search0 Multimodal coreference has also been studied in dialogue around data visualizations, where linguistic context and gestures jointly identify visual referents. citeturn985622search1 Situated multimodal-dialogue work similarly predicts which scene objects are mentioned in the current turn. citeturn985622academia96

These studies provide transferable mechanisms, but they are not direct evidence that a system can resolve an email phrase into a spreadsheet cell or document region.

### TF5 — Evidence-grounded DocVQA and answer localization — DIRECT

This is the main task family for gap-4.

Classic DocVQA established document-image QA but focused primarily on answering questions from documents. citeturn815674search0 Newer datasets make the missing provenance dimension explicit. BoundingDocs associates QA answers with exact answer positions represented by bounding boxes. citeturn342619academia67 BBox DocVQA explicitly evaluates spatial evidence localization. citeturn342619academia64 M3Grounder goes further by generating answer text interleaved with grounding tokens and linking answer spans to evidence masks. citeturn342619search1

These terms should be much more productive than the seed `citation localization`.

The critical admission question is whether the representation identifies only a region, or actually links:

`answer span ↔ evidence region ↔ page/document identity`.

No currently identified term should be assumed to additionally contain **attachment revision identity**; that remains a separate dimension to verify.

### TF6 — Multi-page and long-context multimodal document understanding — DIRECT

This family addresses both provenance depth and operational scaling.

MP-DocVQA explicitly extends DocVQA to multi-page documents and includes prediction of the page containing relevant evidence. citeturn169746academia48 DUDE targets multi-page and visually heterogeneous document understanding. citeturn169746search47 MMLongBench-Doc evaluates lengthy PDFs containing text, tables, charts, images, cross-page questions, and unanswerable questions. citeturn169746academia46

For this project, page localization is useful but incomplete. A page ID must not be promoted to “exact provenance” unless the element/region or cell inside the page is also identified.

### TF7 — Workbook-level spreadsheet understanding — DIRECT

This is the primary academic family for gap-3.

The term should be expanded beyond generic `spreadsheet understanding` using:

- **spreadsheet semantic structure**;
- **formula-aware reasoning**;
- **cross-sheet reasoning**;
- **formula dependency**;
- **multi-sheet workbook**;
- **formatting semantics**;
- **named ranges**;
- **merged cells**;
- **hidden rows/sheets**;
- **workbook understanding**.

**Semantic Table Structure Identification in Spreadsheets** explicitly uses content, styles, spatial positions, header types, and header relations to infer semantic table structure. citeturn708314search6 TUTA models spatial, hierarchical, and semantic structure in generally structured tables including spreadsheet data. citeturn559254search1 SpreadsheetLLM explicitly retains cell addresses, values, and formats and addresses large spreadsheet structures under LLM context constraints. citeturn559254academia92 SpreadsheetBench moves further toward complex real-world spreadsheet manipulation and workbook workflows. citeturn815674search10

These are substantially better search anchors than generic table QA.

### TF8 — Table structure recognition and semantic table understanding — DIRECT

Table work remains important because many spreadsheet and document failures occur before workbook reasoning.

TableBank is explicitly a table-detection and recognition benchmark. citeturn815674search2 PubTabNet's **Image-based table recognition: data, model, and evaluation** reconstructs table structure and cell content and introduces a structure-sensitive metric. citeturn708314search3 TUTA explicitly targets spatial, hierarchical and semantic information in generally structured tables. citeturn559254academia91

However, isolated-table success must not be reported as evidence of workbook-level understanding.

### TF9 — Document layout analysis, reading order, and structure-preserving extraction — DIRECT

This family underpins gap-6.

Modern systems such as LayoutLM jointly represent textual and layout information for document understanding. citeturn815674search4 But the underlying field is much older: O'Gorman's 1993 **The Document Spectrum for Page Layout Analysis** is a classic structural page-analysis paper. citeturn529653search0

Queries in this family should explicitly combine layout with **reading order**, **tables**, **figures**, **scanned pages**, or **structure preservation**. Otherwise discovery will return large quantities of OCR-only work that do not address msgloom's failure modes.

### TF10 — Unanswerable DocQA, abstention, and robustness — DIRECT

This family is useful for the engineering gaps, especially distinguishing genuine lack of evidence from system failure.

MMLongBench-Doc deliberately includes unanswerable questions to expose hallucination and unsupported answering under long-document conditions. citeturn169746academia46

Discovery should additionally seek:

- abstention;
- selective prediction;
- OCR corruption;
- layout perturbation;
- parser errors;
- unsupported evidence;
- answerability detection.

Academic results here can inform the engineering contract, but they cannot by themselves define all application-level failure states.

### TF11 — Fine-grained provenance and lineage — TRANSFER

Database and data-lineage research should be searched as a representation-design transfer family.

Potentially useful concepts include:

- fine-grained provenance;
- data lineage;
- provenance graphs;
- record/field/cell lineage;
- derivation provenance;
- source attribution.

This family is particularly relevant to designing a hierarchy such as:

`attachment/version → page/sheet → element → region/cell → answer span`.

It must remain labelled **TRANSFER** unless a study actually evaluates multimodal document evidence.

### TF12 — Scene-text, screenshot and text-rich-image grounding — TRANSFER

For gap-2 this is a particularly valuable transfer family because document/screenshot referents are frequently identified by visible text.

**Bridging the Gap between Expression and Scene Text for Referring Expression Comprehension** explicitly studies referring-expression grounding where scene text helps identify the target visual object. citeturn815674search6

This is closer to “the row labelled Total” or “the box saying Approved” than ordinary natural-object grounding, although it still does not directly establish email-to-attachment grounding.

## Query families

### TF1 — DIRECT — Cross-version alignment and lineage

Run:

- `"cross-version" document alignment element matching revision PDF`
- `"document differencing" layout-aware tables figures formulas`
- `"document image change detection" revision region localization`
- `"PDF" revision comparison page matching element alignment`
- `"document version comparison" semantic change region correspondence`
- `"scientific document differencing" cross-version alignment`

The most important admission signal is **correspondence across revisions**, not just the existence of a diff.

### TF2 — DIRECT — Version-aware QA

Run:

- `"version-aware" document question answering`
- `"evolving documents" question answering version`
- `"version-aware retrieval" document change tracking`
- `"versioned document" QA temporal validity revision`

Version filtering without region lineage counts only as partial evidence.

### TF3 — DIRECT — Document reference grounding

Run:

- `"document referring expression" grounding`
- `"cross-modal reference resolution" document region`
- `"multimodal reference resolution" document table screenshot`
- `"text-to-region" document grounding referring expression`
- `"referring expression" document image table region`
- `"highlighted row" grounding table document`

Also inspect terminology used by any relevant paper discovered here; this family may have unstable naming.

### TF4 — TRANSFER — General multimodal reference resolution

Run:

- `"multimodal coreference resolution" image dialogue`
- `"situated coreference resolution" multimodal dialogue`
- `"referring expression comprehension" visual grounding`
- `"cross-modal reference resolution" image dialogue`
- `"multimodal referring expression" dialogue visual object`

Admit these as transfer evidence unless document structure is genuinely part of the task.

### TF5 — DIRECT — Evidence-grounded document QA

Run:

- `"evidence-grounded" document question answering`
- `"answer grounding" DocVQA bounding box`
- `"answer localization" document visual question answering`
- `"spatial evidence" document question answering`
- `"evidence attribution" document visual question answering`
- `"multi-span" grounding document QA`
- `"element-level" evidence document VQA`

For gap-4, record exactly which levels each paper evaluates: document, page, element, region, cell, span, or combinations thereof.

### TF6 — DIRECT — Multi-page/long-document grounding

Run:

- `"multi-page" DocVQA evidence localization`
- `"multi-page document" question answering page grounding`
- `"long-context document understanding" multimodal evidence`
- `"long document" multimodal QA evidence localization`
- `"cross-page" document question answering evidence`

For gap-7, extract page limits, token limits, compression methods, memory behaviour, truncation, and evidence-loss observations.

### TF7 — DIRECT — Workbook semantics

Run:

- `"spreadsheet understanding" formulas multi-sheet workbook`
- `"spreadsheet semantic structure" formulas formatting`
- `"cross-sheet" spreadsheet reasoning references`
- `"workbook understanding" formulas named ranges`
- `"spreadsheet question answering" multi-sheet workbook`
- `"spreadsheet" hidden sheets merged cells semantic`
- `"spreadsheet formula" dependency reasoning`
- `"spreadsheet benchmark" multi-sheet workbook reasoning`

This family should be searched aggressively in software-engineering and data-management venues as well as NLP/ML venues; spreadsheet semantics has historically crossed those communities.

### TF8 — DIRECT — Table structure and semantics

Run:

- `"table structure recognition" merged cells spanning cells`
- `"semantic table structure" spreadsheet headers`
- `"table understanding" hierarchical headers units`
- `"table question answering" hierarchical table`
- `"table recognition" cell structure bounding box`
- `"table extraction" header hierarchy merged cells`

Prioritize methods that preserve row-column associations, spanning headers, cell coordinates, units and hierarchy.

### TF9 — DIRECT — Layout and reading order

Run:

- `"document layout analysis" reading order`
- `"reading order detection" document image`
- `"scanned document" layout understanding reading order`
- `"visually rich document understanding" layout information extraction`
- `"layout-aware" document language model bounding box`
- `"document parsing" tables figures reading order`

OCR-only hits should be downgraded.

### TF10 — DIRECT — Failure detection and abstention

Run:

- `"unanswerable" document visual question answering`
- `"unanswerable" DocVQA`
- `"abstention" document question answering`
- `"selective prediction" document question answering`
- `"OCR corruption" document question answering robustness`
- `"layout perturbation" document understanding robustness`
- `"document VQA" hallucination unanswerable evidence`

When analysing papers, distinguish at least:

`evidence truly absent`  
from  
`parser failed`  
from  
`OCR failed`  
from  
`layout/table reconstruction failed`  
from  
`grounding failed`  
from  
`model abstained`.

### TF11 — TRANSFER — Provenance representation

Run:

- `"fine-grained provenance" document version`
- `"data lineage" versioned document region`
- `"provenance graph" document version lineage`
- `"fine-grained data provenance" spreadsheet cell`
- `"cell-level lineage" spreadsheet provenance`
- `"source attribution" answer span provenance`

These searches are for representation mechanisms, not production-accuracy claims.

### TF12 — TRANSFER — Text-rich visual grounding

Run:

- `"scene-text" referring expression comprehension`
- `"visual grounding" scene text OCR`
- `"screenshot" referring expression grounding`
- `"figure grounding" referring expression document`
- `"text-rich image" referring expression grounding`

Prefer datasets where visible text is necessary for disambiguating the referent.

## False friends and downgrade rules

1. **OCR accuracy is not document understanding.** CER/WER, text-line recognition, deskewing, denoising, and character detection without semantic structure should not be admitted as gap-closing evidence.

2. **Layout segmentation is not provenance.** Detecting a rectangular region is useful only if its identity and relation to the evidence can be preserved.

3. **Answer accuracy is not grounding accuracy.** A DocVQA system can produce the correct answer from model knowledge, a wrong region, or an accidental shortcut.

4. **An attention map is not validated provenance.** It must not be treated as a ground-truth evidence location without explicit localization supervision/evaluation.

5. **Page retrieval is not region grounding.** A page ID is one level of provenance, not the complete hierarchy.

6. **Region grounding is not version lineage.** A bounding box in revision 3 does not tell us which region in revision 2 it replaced.

7. **Filename/version metadata is not stable semantic version identity.** Hashes, timestamps, `v2` filenames, and DMS revision numbers do not establish content correspondence.

8. **Text diff is not multimodal document differencing.** Text-only systems should be downgraded if tables, formulas, figures, movement, or layout changes are relevant.

9. **Pixel diff is not semantic change detection.** Rendering changes, font substitution, antialiasing, scaling, or page displacement can create visual changes without semantic changes.

10. **XML/DOM differencing is transfer evidence unless rendered-document correspondence is preserved.**

11. **Natural-image referring-expression work is TRANSFER.** RefCOCO/ReferIt-style evidence can support a grounding mechanism, but not workplace-attachment accuracy.

12. **Scene-text grounding is also TRANSFER unless the benchmark contains document-like structures.**

13. **GUI/screenshot grounding is TRANSFER unless the relevant difficulty is document-like text, labels, tables, or structured visual regions.**

14. **Table detection is not table understanding.** A table bounding box alone is insufficient.

15. **Flat cell extraction is not table semantics.** Lost spanning headers, units, row/column relations, merged cells, and semantic grouping remain failures.

16. **A normalized table is not a spreadsheet workbook.** CSV and Wikipedia-table QA bypass formulas, sheets, formatting, names, dependencies, hidden content, and workbook topology.

17. **Formula prediction alone does not establish workbook understanding.**

18. **Single-sheet success does not establish cross-sheet reasoning.**

19. **Chart QA is incomplete evidence unless the supporting chart elements can also be identified when provenance matters.**

20. **Citation-context research is a false friend.** Scholarly citation classification, citation intent, bibliography matching, and recommendation should be excluded from `citation localization`.

21. **Chunk citations are not fine-grained document provenance.** RAG citations that identify only a chunk or source document do not close gap-4.

22. **Retrieval-only papers should remain Topic-07 evidence.** Topic 08 should admit them only where retrieval is an internal step of evaluated evidence localization.

23. **Long-context text-only evaluation is insufficient.** Flattening a PDF can silently discard images, table topology, visual highlighting, units, or reading order.

24. **Throughput is secondary.** Parser speed or model latency does not close an extraction-completeness or meaning-preservation gap.

25. **“No answer” must not collapse unlike failures.** Genuine absence, unsupported format, OCR failure, parser failure, layout failure, grounding failure, and low confidence are different states.

26. **Evaluation gold must be independent.** A component cannot validate itself by generating both predicted structure and the supposed gold structure.

27. **Synthetic/adversarial data is valid for engineering robustness but not evidence of production-mailbox representativeness.**

28. **Database provenance is TRANSFER unless it is actually evaluated on multimodal documents.**

29. **A paper using only the latest document revision provides no evidence for historical-state preservation.**

30. **A version-aware system that can select the correct revision but cannot map the old evidence region to the revised region provides partial, not complete, evidence for gap-1.**

## Date policy

**Earliest year discovery must include: 1980.**

This is intentionally earlier than the neural Document AI era. Document-image structure analysis was already an active research area in the early 1980s, and classic hierarchical/page-layout methods predate today's models by decades. O'Gorman's well-known document-spectrum work dates to 1993, while its references include earlier hierarchical scanned-document and document-analysis work from the 1980s. citeturn529653search0turn529653search3

A search window beginning in 2018, 2020, or even 2000 would therefore silently exclude foundational work on physical layout, logical document structure, segmentation and reading order. These concepts remain directly relevant to whether evidence locations survive extraction.

The **global floor should therefore be 1980**, but discovery should rank recent work heavily for the current gap-closure round:

- **2024-2026** should receive highest priority for evidence-grounded DocVQA, long-context multimodal documents, modern spreadsheet/workbook agents, version-aware QA and cross-version heterogeneous-document alignment.
- **2020-2023** is especially important for LayoutLM-era document models, DocVQA, multi-page DocVQA, table pretraining and semantic spreadsheet work.
- **1990s-2010s** contain important document-layout, reading-order, table-recognition and visual-referring-expression foundations.
- **1980s** must remain searchable so foundational document-structure work is not excluded by policy.

The date policy is therefore **not** a recommendation to bulk-read forty years of generic document papers. The round should use the targeted query families above, rank recent direct evidence first, and reach backward only where citation trails or terminology indicate foundational relevance.
