# Direct empirical methods for cross-version multimodal document element lineage and hierarchical provenance, with special attention to revised workbook provenance and message referring-expression grounding into versioned pages, regions, and cells. academic terminology analysis

## Product problem

The research target is narrower than generic Document AI. It requires a system to preserve a chain of evidence such as:

`work message referring expression -> attachment identity -> attachment version -> page/sheet -> document element -> visual region/table range/cell -> source text/value -> answer span`

and to preserve that chain when the attachment is revised.

The four highest-value academic gaps therefore correspond to four distinct questions:

1. **Cross-version lineage:** given evidence at a location in attachment version 1, what is the corresponding logical element in version 2 after edits, moves, splits, merges, formatting changes, row/column insertion, or other restructuring?
2. **Cross-modal reference grounding:** when a message says “this screenshot”, “the highlighted row”, “numbers below”, “that table”, or “use attachment v2”, what concrete attachment/version/page/region/cell does the expression denote?
3. **Workbook semantics:** can a method preserve formulas, dependencies, hidden rows and sheets, cross-sheet references, merged cells, formatting semantics, units, named ranges, and other workbook constructs rather than reducing Excel to displayed values?
4. **Hierarchical provenance:** can an answer be traced through one representation that jointly preserves attachment version, page or sheet, element, region or cell, and answer span?

Several literatures solve pieces of this problem, but their terminology differs. In particular, the search should not assume that authors use the phrases “attachment provenance” or “email attachment understanding”. The more academically productive vocabulary is **document version alignment**, **document evolution**, **persistent element identity**, **semantic differencing**, **data provenance**, **where-provenance**, **cell lineage**, **spreadsheet dependency graphs**, **referring-expression grounding**, **multimodal coreference**, **document region grounding**, and **evidence localization**.

A central methodological rule for round 4 is therefore: a paper that solves one layer must not be treated as validation of the whole hierarchy.

## Seed keyword audit

| Seed | Academic meaning | Fit | Main risk | Typical false positives |
| --- | --- | --- | --- | --- |
| document AI | Broad umbrella for ML/CV methods operating on document text, layout and visuals. | MODERATE | Far broader than provenance or revision lineage. | OCR, classification, field extraction, generic foundation models. |
| document intelligence | Broad umbrella overlapping OCR, IE, layout analysis and QA; also heavily used commercially. | WEAK | Low academic precision and vendor contamination. | Intelligent document processing products and workflow automation. |
| visually rich document understanding | Joint modeling of text, 2-D layout and visual appearance. | STRONG | Usually single-version and does not preserve persistent element identity. | Forms, receipts, invoices and document classification. |
| VRDU | Abbreviation for visually rich document understanding. | MODERATE | Less stable and more ambiguous than the expanded phrase. | Unrelated acronym uses and generic multimodal models. |
| document layout analysis | Page segmentation, region classification, geometry and reading structure. | STRONG | Coordinates alone are not provenance or cross-version correspondence. | Region detection and layout classification only. |
| layout-aware language models | Models that encode text together with document coordinates or visual features. | MODERATE | Layout awareness does not imply exact grounding or version lineage. | Token classification, forms and receipts. |
| document information extraction | Extraction of entities, fields, relations or structured records from documents. | MODERATE | Usually targets values rather than persistent evidence objects. | NER, key-value extraction and invoice parsing. |
| document visual question answering | QA over document images using text, vision and layout. | STRONG | Many benchmarks score answer text without evidence location. | Answer-only QA and single-page OCR-centric systems. |
| DocVQA | Established family of document visual QA tasks and benchmarks. | STRONG | The name does not imply multi-page, version-aware or region-grounded QA. | Generic benchmark improvements without provenance. |
| multi-page document understanding | Processing and reasoning over multiple pages in one document. | STRONG | Page selection can still stop above the required region/cell level. | Page retrieval and document summarization. |
| long-document multimodal understanding | Multimodal reasoning when page and context length exceed ordinary single-page settings. | MODERATE | Often focuses on context length rather than traceability. | Long-context multimodal LMs and summarization. |
| OCR layout understanding | Informal phrase combining OCR and structure. | WEAK | Not a stable task name and conflates recognition with interpretation. | OCR accuracy, text detection and box prediction. |
| reading order detection | Recovery of logical reading sequence among blocks or lines. | MODERATE | Important preservation primitive but not version lineage. | Page segmentation and reading-order benchmarks only. |
| table detection | Localization of table regions. | WEAK | A table box says nothing about cell semantics or workbook state. | Object detection for tables. |
| table structure recognition | Recovery of rows, columns, cells and spanning structure. | STRONG | Usually covers visible page tables, not complete workbook semantics. | Isolated image-table extraction. |
| table understanding | Structural and semantic representation and reasoning over tables. | STRONG | Mixes document tables, web tables and database tables. | Web-table representation and knowledge-table matching. |
| table question answering | QA using a tabular source, often by selecting or computing over cells. | MODERATE | Usually assumes the input table is already correct. | Semantic parsing over clean tables and answer-only QA. |
| spreadsheet understanding | Modeling spreadsheet layout, formulas, regions, roles and semantics. | STRONG | Narrow tasks may be presented as full spreadsheet understanding. | CSV reasoning, formula completion and single-sheet QA. |
| chart understanding | Recognition and reasoning over axes, legends, marks and chart data. | MODERATE | Only one embedded-object class and not central to revision lineage. | Chart classification and chart-to-table conversion. |
| chart question answering | QA over chart images. | WEAK | Peripheral to the four unresolved academic gaps. | Synthetic chart QA without provenance. |
| multimodal information extraction | IE combining language with visual/layout or other modalities. | MODERATE | Includes many domains unrelated to documents. | Social-media multimodal NER, video IE and generic image-text extraction. |
| multimodal coreference resolution | Resolution of references whose antecedents or referents cross linguistic/visual modalities. | STRONG | Most studies use dialogue, images or embodied environments rather than workplace attachments. | Visual-dialogue and video coreference. |
| cross-modal reference resolution | Resolution of an expression in one modality to an entity in another. | MODERATE | Less standardized than multimodal coreference or referring-expression grounding. | Cross-modal retrieval and image-text matching. |
| visual grounding | Mapping language to visual objects or spatial regions. | MODERATE | Dominated by natural-image localization without document hierarchy or versions. | Phrase grounding on natural images, robotics and open-vocabulary detection. |
| referring expression comprehension | Localizing the entity denoted by a referring expression. | MODERATE | Standard tasks assume one image and visible objects rather than versioned documents. | RefCOCO-style natural-image localization. |
| document region grounding | Grounding language, questions, claims or answers to spatial document regions. | STRONG | Useful but not fully standardized terminology. | Layout detection with no linguistic grounding. |
| citation localization | Identification of evidence underlying a claim or answer. | MODERATE | Overloaded across bibliometrics, RAG and evidence localization. | Citation recommendation and citation-function classification. |
| scanned document understanding | Structural or semantic interpretation of rasterized documents. | MODERATE | Often collapses back to OCR. | Historical transcription, restoration and recognition. |
| document version comparison | Comparison of revisions to identify structural or semantic changes. | STRONG | Can retrieve textual diff, redlining or product software rather than persistent lineage. | Diff tools, plagiarism detection and near-duplicate detection. |
| visual document differencing | Visual change detection between page renderings. | MODERATE | Pixel differences do not establish semantic element identity. | Screenshot regression and generic image differencing. |
| attachment content extraction | Operational phrase for parsing attachments. | WEAK | Not a stable academic task term. | MIME tools, ETL, malware analysis and parser documentation. |
| email attachment understanding | Product description of reasoning over email attachments. | REJECT | Very poor academic precision. | Phishing, malware, email forensics and MIME processing. |
| screenshot understanding | Broad understanding of rendered screen images. | MODERATE | Literature is dominated by interactive GUI agents. | Web/mobile agents, accessibility and UI navigation. |
| figure caption grounding | Linking textual descriptions with figures or figure regions. | MODERATE | Usually caption/figure alignment rather than arbitrary discourse grounding. | Caption generation and scientific figure retrieval. |
| multimodal document retrieval | Retrieval of documents or pages using textual and visual signals. | MODERATE | Retrieval supplies a candidate, not validated final provenance. | Cross-modal search and document embeddings. |

### Terms to promote

Round 4 should promote terminology that expresses the unresolved capabilities rather than their surrounding research fields:

- **document version alignment**
- **document revision alignment**
- **cross-version element correspondence**
- **document evolution**
- **semantic document differencing**
- **persistent document element identity**
- **versioned document provenance**
- **page correspondence**
- **region correspondence**
- **spreadsheet provenance**
- **spreadsheet lineage**
- **cell-level provenance**
- **cell lineage**
- **spreadsheet dependency graph**
- **formula dependency graph**
- **cross-sheet dependency**
- **workbook structure understanding**
- **versioned workbook lineage**
- **referring expression grounding**
- **grounded coreference**
- **multimodal coreference resolution**
- **document region grounding**
- **cell grounding**
- **evidence localization**
- **answer grounding**
- **answer provenance**
- **fine-grained evidence provenance**
- **hierarchical provenance**
- **where-provenance**
- **why-provenance**
- **data lineage**
- **document image registration**
- **document image change detection**
- **failure-aware document understanding**
- **extraction completeness**
- **unanswerable document question answering**

### Terms to demote

The following should not be primary discovery axes because they are too broad, too commercial, or too weakly coupled to the open gaps:

- `document intelligence`
- `VRDU` without the expanded phrase or a specific capability
- `OCR layout understanding`
- `table detection` alone
- `chart question answering` as a primary search family
- `attachment content extraction`
- `email attachment understanding`
- `visual grounding` alone
- `citation localization` alone
- `multimodal document retrieval` alone
- `screenshot understanding` alone

## Academic task families

### TF1 — Cross-version document alignment and element correspondence — DIRECT

The target task is not ordinary diff. It is correspondence between logical elements across revisions: old page to new page, old region to its moved or edited counterpart, old table to revised table, and potentially one-to-many or many-to-one relationships after splits and merges.

Useful vocabulary:

- document version alignment
- document revision alignment
- element correspondence
- page correspondence
- region correspondence
- document change detection
- document evolution
- structural differencing

A known seed is **XyDiff: An Algorithm and Tool for the Detection of Changes in XML Documents**. XML is structurally cleaner than PDFs or spreadsheets, so XML work should be treated carefully when transferred to visual documents, but it is directly relevant to identity-preserving structural change.

### TF2 — Document evolution, semantic differencing, and persistent identity — DIRECT

A second family focuses not on geometric matching but on the identity model itself: what makes two elements in different versions “the same” logical element?

High-value terminology includes:

- persistent element identity
- persistent identifiers
- document evolution
- revision history
- semantic diff / semantic differencing
- versioned document provenance
- element lineage

This family is important because simple content similarity cannot safely distinguish:

- edited element versus deleted-and-replaced element;
- moved element versus duplicated element;
- one old element split into two new elements;
- two old elements merged into one;
- same logical table with inserted rows or columns.

### TF3 — Spreadsheet and workbook structural-semantic understanding — DIRECT

The target object is a **workbook**, not a CSV and not just a rendered table.

Discovery should look for methods that model combinations of:

- sheets and sheet identity;
- formulas;
- cross-sheet references;
- merged cells;
- named ranges;
- hidden rows, columns, and sheets;
- formatting used semantically;
- number formats and units;
- hierarchical row and column structure;
- multiple tables on one sheet;
- formula and value roles;
- comments, metadata, or embedded objects where relevant.

A useful seed is **TUTA: Tree-based Transformers for Generally Structured Table Pre-training**, but any such paper must be inspected for which workbook constructs it actually preserves.

### TF4 — Spreadsheet formula dependency, auditing, and cell-level provenance — DIRECT

Spreadsheet research also uses terminology closer to program analysis than Document AI:

- spreadsheet auditing;
- formula dependency;
- dependency graph;
- cell dependency graph;
- cross-sheet dependency;
- formula lineage;
- cell provenance;
- spreadsheet provenance.

This family matters because a computed value has both a **location provenance** and a **dependency provenance**. For example, an answer citing `Sheet2!G17` may also depend on source cells in several other sheets.

Within-state dependency provenance must not be mistaken for cross-version provenance.

### TF5 — Versioned spreadsheet and workbook lineage — DIRECT

This is the most gap-specific spreadsheet search family.

The desired literature would answer questions such as:

- Is cell `F20` in version 2 the descendant of `F17` in version 1 after three rows were inserted?
- Is a renamed sheet still the same logical sheet?
- Can a named range preserve identity when its coordinates move?
- Can formula lineage survive row or column insertion?
- Can a range split or merge across revisions?
- Can semantic changes be separated from harmless formatting changes?

No specific seed paper is promoted here because earlier rounds have not established a paper that validates this complete capability.

### TF6 — Message-to-document referring-expression grounding — DIRECT

This is the exact Topic 04 to Topic 08 boundary.

Target expressions include:

- “this screenshot”
- “the highlighted row”
- “the red box”
- “numbers below”
- “that table”
- “use attachment v2”
- “the second sheet”
- “those cells”

The desired output is not merely an entity label. It is a grounded reference such as:

`message expression -> attachment identity -> version -> sheet/page -> table/region -> cells`

Search terminology should combine document terms with:

- referring expression grounding;
- multimodal coreference;
- grounded coreference;
- deictic reference;
- visual reference resolution;
- cross-modal reference resolution.

No confident direct seed paper is supplied because that exact workplace-message-to-versioned-document problem remains one of the open gaps.

### TF7 — Document-region and cell-level evidence grounding — DIRECT

This family searches for methods where a correct answer is accompanied by an explicit source location.

Possible evidence units include:

- OCR token span;
- bounding box;
- region;
- table cell;
- table range;
- page;
- document element.

Useful task names include:

- evidence localization;
- answer grounding;
- document region grounding;
- region-level evidence;
- cell grounding;
- source localization;
- fine-grained evidence.

Known seeds include **DocVQA: A Dataset for VQA on Document Images** and **MP-DocVQA: Benchmarking Multi-Page Document Visual Question Answering**, but individual methods must be checked for whether they actually supervise or evaluate evidence rather than answer strings only.

### TF8 — Multi-page document VQA and evidence routing — DIRECT

Multi-page QA contributes the upper layers of the desired hierarchy:

`document -> page -> evidence`

The important distinction is between:

- retrieving the right page;
- localizing the right evidence on that page;
- generating the right answer.

A system that gets only the first or third correct does not establish the complete provenance chain.

Known seeds include **MP-DocVQA** and **DocVQA**.

### TF9 — Visually rich document representation and layout-aware extraction — DIRECT

This family provides structural representations needed by later provenance mechanisms.

Known seeds include:

- **LayoutLM: Pre-training of Text and Layout for Document Image Understanding**
- **LayoutLMv2: Multi-modal Pre-training for Visually-rich Document Understanding**
- **LayoutLMv3: Pre-training for Document AI with Unified Text and Image Masking**
- **Donut: Document Understanding Transformer without OCR**

These establish multimodal document representation techniques, not cross-version provenance by themselves.

### TF10 — Table structure recognition and semantic table understanding — DIRECT

The target goes beyond detecting a rectangle labelled “table”.

Relevant capabilities include:

- row and column reconstruction;
- spanning and merged cells;
- hierarchical headers;
- header-to-cell associations;
- sparse tables;
- units;
- reading order;
- cell coordinates;
- explicit cell evidence.

Known seeds include:

- **PubTables-1M: Towards Comprehensive Table Extraction From Unstructured Documents**
- **TAPAS: Weakly Supervised Table Parsing via Pre-training**

The clean-table assumptions of many Table QA papers must be recorded explicitly.

### TF11 — Fine-grained data provenance and lineage — TRANSFER

Database provenance contains highly relevant formal concepts:

- **where-provenance**: where a returned value originated;
- **why-provenance**: which source facts justify a result;
- **data lineage**: source-to-derived-result dependency;
- provenance propagation through transformations.

Known foundational seeds include:

- **Why and Where: A Characterization of Data Provenance**
- **Provenance Semirings**

This literature is TRANSFER because relational tuples and attributes do not directly model versioned pages, bounding regions, screenshots, merged cells, or message deixis. It may nevertheless provide the cleanest formal vocabulary for a hierarchical provenance representation.

### TF12 — Visual referring-expression comprehension and phrase grounding — TRANSFER

Natural-image grounding provides mature formulations of:

`linguistic expression -> visual region/object`

Known seeds include:

- **Modeling Context in Referring Expressions**
- **MDETR: Modulated Detection for End-to-End Multi-Modal Understanding**

This is methodologically useful for “the highlighted row” or “the red box”, but standard visual-grounding benchmarks omit attachment identity, document structure, revision history, and message discourse.

### TF13 — Multimodal coreference and grounded reference resolution — TRANSFER

This family becomes important when the reference depends on previous discourse rather than a standalone noun phrase.

Useful terminology:

- multimodal coreference;
- visual coreference;
- grounded coreference;
- cross-modal coreference;
- deictic reference resolution.

It should be searched as TRANSFER unless the empirical object is actually a document, table, screenshot, or comparable structured surface.

### TF14 — Scientific-document evidence localization and source attribution — TRANSFER

Scientific-document QA is useful because it often requires explicit supporting evidence.

A known seed is **QASPER: A Dataset for Question Answering over Scientific Research Papers**.

This literature can inform:

- evidence spans;
- support passages;
- section/page attribution;
- answer-plus-evidence evaluation.

It remains TRANSFER for msgloom if it does not preserve attachment version, visual regions, or spreadsheet cells.

### TF15 — Document image registration and visual change detection — TRANSFER

A separate computer-vision tradition aligns images before measuring change.

Relevant terminology:

- document image registration;
- page image alignment;
- page correspondence;
- region matching;
- document image change detection;
- visual document differencing.

This can help when version 2 preserves much of version 1's visual layout. It cannot establish semantic lineage on its own because the same-looking region may have changed meaning and a logically identical element may move substantially.

### TF16 — Failure-aware document QA and extraction evaluation — DIRECT

Although gaps 5, 6 and 8 are classified as engineering gaps, discovery should still capture empirical terminology for the mechanisms used to test them:

- answerability;
- unanswerable document QA;
- abstention;
- extraction completeness;
- OCR robustness;
- parser failure;
- layout corruption;
- table reconstruction errors;
- localization errors;
- unsupported content.

The required product state space is richer than success/failure:

`evidence genuinely absent`

must be distinguishable from:

`attachment unavailable`

`format unsupported`

`parser failure`

`OCR failure`

`structure reconstruction failure`

`retrieval failure`

`grounding failure`

`evidence found but ambiguous`

### TF17 — Long-document and large-workbook robustness and scaling — DIRECT

The target workload makes scale part of correctness because systems may silently truncate or omit content.

Searches should therefore cover:

- many-page DocVQA;
- large tables;
- large workbooks;
- workbook inspection limits;
- page routing;
- latency and memory;
- context truncation;
- quality degradation with document size.

A known useful seed is **MP-DocVQA**, while workbook-specific scaling remains especially important to find.

### TF18 — Screenshot, GUI, and visual-region grounding — TRANSFER

GUI and screen-grounding research is structurally closer to message screenshots than ordinary natural-image grounding because it deals with:

- text-heavy visual surfaces;
- repeated labels;
- precise rectangular regions;
- interface widgets;
- spatial instructions.

It remains TRANSFER where its objective is acting on a live GUI rather than understanding a static evidentiary screenshot inside workplace communication.

## Query families

### TF1 — Cross-version document alignment and element correspondence — DIRECT

Run:

- `"document version alignment" region correspondence semantic change`
- `"document revision alignment" page region correspondence`
- `"document version" element correspondence revision`
- `"document change detection" layout semantic revision`
- `"document differencing" semantic structural change`
- `"document revision" region matching`
- `"versioned document" element alignment provenance`
- `"document evolution" element correspondence`
- `"document version alignment" multimodal provenance region lineage`
- `"document revision" semantic change region lineage provenance`
- `"versioned document" page region lineage`
- `"document version" provenance page region correspondence attachment`

These queries should be preferred over the raw phrase `document version comparison`, which is too easily captured by ordinary text diff.

### TF2 — Persistent identity and document evolution — DIRECT

Run:

- `"persistent identity" document element revision`
- `"persistent identifier" document element version`
- `"document evolution" persistent identity`
- `"versioned document" provenance lineage`
- `"document revision history" element lineage`
- `"semantic diff" document revision`
- `"semantic differencing" document`
- `"XML diff" persistent identity document`

The relevant contribution is identity across revisions, not merely edit detection.

### TF3 — Workbook structural-semantic understanding — DIRECT

Run:

- `"spreadsheet understanding" workbook formulas formatting`
- `"workbook understanding" formulas cross-sheet references`
- `"spreadsheet structure" merged cells hierarchical headers`
- `"spreadsheet semantics" formulas formatting units`
- `"spreadsheet" hidden rows hidden sheets named ranges formulas`
- `"workbook" merged cells named ranges cross-sheet references`
- `"spreadsheet representation" cell role formula layout`
- `"workbook structure" hidden sheet named range`

Papers should be inspected against the specific workbook constructs rather than accepted because they use the phrase “spreadsheet understanding”.

### TF4 — Spreadsheet dependency and provenance — DIRECT

Run:

- `"spreadsheet provenance" cell formula`
- `"cell provenance" spreadsheet`
- `"spreadsheet lineage" cell`
- `"spreadsheet dependency graph" formula cross-sheet`
- `"formula dependency" spreadsheet provenance`
- `"spreadsheet auditing" formula dependency`
- `"cell dependency graph" workbook`
- `"cross-sheet dependency" spreadsheet formula`
- `"spreadsheet formula" provenance lineage`

This family is especially useful for distinguishing cell location from derivation lineage.

### TF5 — Versioned workbook lineage — DIRECT

Run:

- `"spreadsheet version" cell lineage`
- `"workbook version" cell correspondence`
- `"spreadsheet revision" formula change detection`
- `"spreadsheet evolution" cell correspondence`
- `"workbook revision" provenance`
- `"spreadsheet change detection" semantic`
- `"spreadsheet diff" formula structure`
- `"workbook diff" formula sheet cell`
- `"versioned spreadsheet" provenance`
- `"spreadsheet" revision history provenance cell`
- `"revised workbook" provenance cell lineage`
- `"workbook revision" formula cell lineage`
- `"spreadsheet revision" hidden sheet named range provenance`
- `"versioned workbook" cross-sheet provenance`
- `"workbook version" merged cells formula lineage`

This is the highest-priority query family for gap 3 because earlier work largely covered one workbook state rather than provenance through revisions.

### TF6 — Message-to-document reference grounding — DIRECT

Run:

- `"referring expression grounding" document region table cell`
- `"referring expression" document screenshot table`
- `"multimodal coreference" document screenshot attachment`
- `"grounded coreference" document image region`
- `"cross-modal reference resolution" document`
- `"visual reference resolution" document table screenshot`
- `"deictic reference" document screenshot`
- `"document grounding" referring expression region`
- `"referring expression" spreadsheet cell`
- `"message" referring expression attachment document`
- `"email" referring expression attachment screenshot`
- `"attachment" referring expression grounding`

Also run high-specificity formulations:

- `"this screenshot" grounding document`
- `"highlighted row" referring expression grounding`
- `"numbers below" reference resolution table`
- `"attachment v2" reference resolution`
- `"use attachment" referring expression version`
- `"highlighted cell" referring expression spreadsheet`

The quoted expressions are intentionally narrow probes. Failure to retrieve direct academic work from them is itself informative; discovery should then rely on the broader academic terms rather than inventing an “email attachment grounding” field.

### TF7 — Hierarchical evidence and exact region/cell grounding — DIRECT

Run:

- `"document region grounding" question answering`
- `"evidence localization" document visual question answering`
- `"answer grounding" document VQA region`
- `"cell grounding" document question answering`
- `"region-level evidence" document QA`
- `"fine-grained evidence" document question answering`
- `"source localization" document VQA`
- `"evidence region" DocVQA`
- `"page region" answer provenance document`
- `"document question answering" bounding box evidence`

For gap 4 also run:

- `"evidence provenance" document question answering version page region cell`
- `"answer provenance" version page region cell`
- `"hierarchical provenance" document evidence`
- `"fine-grained provenance" page region cell answer`
- `"evidence hierarchy" document question answering`
- `"source attribution" page region cell answer span`
- `"answer span" document region provenance`

The admission test must check whether the paper actually represents multiple provenance levels jointly. A method that returns only a page number or only a text span does not close gap 4.

### TF8 — Multi-page document VQA — DIRECT

Run:

- `"multi-page document visual question answering" evidence`
- `"multi-page document" evidence localization`
- `"multi-page DocVQA" grounding`
- `"document VQA" page retrieval evidence`
- `"page retrieval" document visual question answering`
- `"multi-page document" region grounding`
- `"long document" multimodal question answering page evidence`
- `"multi-page document understanding" provenance`

Record separately whether evaluation measures page routing, region localization, and answer correctness.

### TF9 — Visually rich document representations — DIRECT

Run:

- `"visually rich document understanding" evidence grounding`
- `"layout-aware" document evidence localization`
- `"document AI" region grounding provenance`
- `"document information extraction" bounding box provenance`
- `"layout-aware language model" evidence`
- `"multimodal document understanding" source grounding`
- `"document understanding" layout region attribution`

This is a supporting family, not evidence of revision lineage by itself.

### TF10 — Table reconstruction and semantics — DIRECT

Run:

- `"table structure recognition" merged cells hierarchical headers`
- `"table structure recognition" spanning cells sparse tables`
- `"table understanding" headers units merged cells`
- `"table semantics" units formatting headers`
- `"table question answering" cell evidence`
- `"cell grounding" table question answering`
- `"table provenance" cell`
- `"table structure" hierarchical header provenance`
- `"table extraction" merged cells reading order`

The queries deliberately include difficult structures because ordinary TSR benchmarks can overstate capability on clean rectangular tables.

### TF11 — Formal data provenance — TRANSFER

Run:

- `"where-provenance" database`
- `"why-provenance" data provenance`
- `"data lineage" fine-grained provenance`
- `"provenance semiring" query`
- `"fine-grained data provenance" attribute`
- `"cell-level provenance" data`
- `"data provenance" versioned data lineage`
- `"provenance" hierarchical source lineage`
- `"provenance propagation" derived value source`

These papers may contribute representation and algebra, not document-specific empirical validation.

### TF12 — Visual referring expressions — TRANSFER

Run:

- `"referring expression comprehension" region grounding`
- `"referring expression grounding" visual region`
- `"phrase grounding" referring expression region`
- `"visual grounding" deictic reference`
- `"referring expression" highlighted region grounding`
- `"grounded referring expression" visual object`
- `"visual grounding" table region`
- `"phrase grounding" document image`

Do not promote natural-image accuracy into claims about office documents.

### TF13 — Multimodal coreference — TRANSFER

Run:

- `"multimodal coreference resolution" visual`
- `"multimodal coreference" dialogue visual`
- `"grounded coreference resolution" visual`
- `"cross-modal coreference" referring expression`
- `"visual coreference" dialogue grounding`
- `"reference resolution" multimodal dialogue region`
- `"deictic reference resolution" multimodal`

This family is particularly relevant when grounding depends on prior turns or previous messages.

### TF14 — Scientific-document evidence localization — TRANSFER

Run:

- `"evidence localization" scientific document question answering`
- `"evidence span" scientific document QA`
- `"evidence extraction" scientific question answering`
- `"citation localization" scientific paper evidence`
- `"source span" scientific document question answering`
- `"rationale extraction" scientific document QA`
- `"evidence attribution" scientific document answer`
- `"answer provenance" scientific document`

This family can provide evaluation designs for answer-plus-evidence prediction but should not be mistaken for attachment revision provenance.

### TF15 — Image registration and visual revision matching — TRANSFER

Run:

- `"document image registration" page alignment`
- `"document image change detection" page`
- `"page image alignment" document versions`
- `"document page alignment" image registration`
- `"layout matching" document versions`
- `"visual document differencing" revision`
- `"region correspondence" document images`
- `"document image" region matching revision`
- `"page correspondence" document revision`

Geometric matching is valuable evidence only when the paper evaluates correspondence, not merely image similarity.

### TF16 — Failure-aware extraction and QA — DIRECT

Run:

- `"document parsing" extraction completeness benchmark`
- `"document understanding" extraction completeness`
- `"document AI" robustness OCR noise layout`
- `"document VQA" unanswerable evidence grounding`
- `"document question answering" abstention unanswerable`
- `"multimodal document" failure analysis OCR layout`
- `"table structure recognition" OCR corruption robustness`
- `"document extraction" unsupported content evaluation`
- `"document understanding" reading order robustness`
- `"table extraction" sparse tables merged cells robustness`

This family supports gaps 5, 6 and 8 but does not by itself replace the required product-specific engineering contract.

### TF17 — Operational scaling — DIRECT

Run:

- `"long document" multimodal document benchmark latency`
- `"multi-page document" scaling question answering`
- `"document VQA" many pages efficiency`
- `"large workbook" benchmark spreadsheet understanding`
- `"spreadsheet benchmark" large workbook formulas`
- `"workbook" scalability formula analysis`
- `"large table" table question answering scalability`
- `"document understanding" memory latency multi-page`

This family is supporting evidence for gap 7. Speed results must be interpreted together with omission and truncation behavior.

### TF18 — Screenshot and GUI grounding — TRANSFER

Run:

- `"screenshot" referring expression grounding`
- `"screenshot grounding" referring expression`
- `"screen grounding" natural language region`
- `"GUI grounding" referring expression`
- `"visual grounding" screenshot UI`
- `"screen understanding" region grounding`
- `"figure grounding" text region`
- `"figure caption grounding" region`
- `"highlighted region" visual grounding`

The family is especially useful for static screenshots containing text-heavy rectangular structures, but interactive UI action accuracy is not equivalent to evidence grounding.

## False friends and downgrade rules

Discovery should apply the following downgrade rules before admitting candidates as direct evidence.

1. **OCR is not document understanding.** Character or token accuracy alone does not validate layout, table semantics, evidence grounding, or revision lineage.
2. **Bounding boxes are not provenance.** Document layout analysis that only detects regions is supporting evidence unless language or evidence is explicitly grounded to those regions.
3. **Answer correctness is not provenance correctness.** A DocVQA result that returns the right string without the right page/region/cell must not support claims about exact evidence.
4. **Page retrieval is not region grounding.** Selecting the correct page closes only one level of the hierarchy.
5. **Single-version methods do not validate version lineage.** They may support extraction or representation only.
6. **Text diff is not element lineage.** Ordinary token or line diff should be downgraded unless it handles structural moves, splits, merges, or persistent identities.
7. **Pixel change is not semantic change.** Visual differencing should be TRANSFER unless element correspondence is validated.
8. **Near-duplicate detection is not revision provenance.** Similarity can help identify candidates but does not establish lineage.
9. **Filename equality is not document identity.** A filename, URL, MIME label, or attachment name is not stable identity unless the method validates revision identity independently.
10. **Lexical similarity is not element identity.** Similar text in two versions cannot alone prove that the elements have a lineage relation.
11. **XML diff does not automatically solve PDF or workbook lineage.** XML methods are valuable structural evidence but must be downgraded to TRANSFER when the target modality is absent.
12. **Table detection is not table reconstruction.**
13. **Table reconstruction is not table semantics.** Correct cell boxes do not guarantee correct headers, units, spanning relations, or row/column interpretation.
14. **Clean Table QA is not document table QA.** Methods given a gold table should not support claims about extraction completeness from PDFs or screenshots.
15. **CSV is not a workbook.** Any transformation that discards formulas, styles, names, hidden structures, merged regions, or multiple sheets loses evidence needed for gap 3.
16. **Single-sheet evidence is not workbook-level evidence.**
17. **Formula prediction is not formula provenance.**
18. **Within-version cell provenance is not cross-version cell lineage.**
19. **Natural-image grounding is TRANSFER.** It may justify objectives or metrics but not production document accuracy.
20. **Visual dialogue grounding is TRANSFER** unless its referents are document-like objects.
21. **Cross-modal retrieval is not reference resolution.** Similarity between text and image does not mean an explicit referring expression was resolved.
22. **GUI grounding is TRANSFER** when evaluated as action selection on a live interface rather than evidentiary grounding in a static screenshot.
23. **Image captioning is not visual grounding.** A description of a screenshot does not establish the region referred to by “this row” or “the red box”.
24. **Citation recommendation is not citation localization.**
25. **RAG citations at document level do not validate page/region/cell provenance.**
26. **Scientific-document evidence is TRANSFER** if it lacks version identity and document-layout provenance.
27. **Retrieval is not evidence attribution.** Correctly finding an attachment or page does not close the grounding problem.
28. **Correct extraction on supported content does not measure completeness.** Unsupported objects and failed pages must remain in the denominator.
29. **Empty output is not evidence absence.** A parser or grounder that silently returns nothing must not be interpreted as confirming that no evidence exists.
30. **OCR robustness alone is insufficient for heterogeneous attachments.** Structural corruption, merged cells, sparse tables, irregular reading order, embedded visuals and scans remain separate failure modes.
31. **Throughput-only parser benchmarks are insufficient.** Faster extraction does not establish preservation of meaning.
32. **A provenance identifier at document level is insufficient for gap 4.** The representation must descend into finer-grained evidence.
33. **Combining separate papers is not an end-to-end validation.** A page-localization paper plus a region-grounding paper plus a cell-provenance paper does not establish that one representation jointly supports all three.
34. **Transfer evidence must remain labelled TRANSFER.** Success on natural images, scientific papers, databases, XML, or GUIs may justify a mechanism or experiment but cannot establish production workplace-email accuracy.
35. **Synthetic evidence cannot establish production representativeness.** It can support controlled engineering validation only.

## Date policy

**Earliest publication year discovery must include: 1990.**

A recent-only window would be methodologically unsafe.

The modern labels `Document AI`, `DocVQA`, `LayoutLM`, and multimodal foundation models are recent, but several foundations required by this project predate them substantially:

- document image analysis and page-layout analysis developed before modern deep learning;
- reading-order and table-recognition research has substantial 1990s-era foundations;
- image registration and structural document matching also predate modern multimodal models;
- formal database provenance became important in the early 2000s;
- structured-document and XML change detection developed in the same general period;
- modern visually rich document transformers and DocVQA represent only the newest layer of the stack.

Therefore discovery should permit papers from **1990 onward**, while ranking recent direct empirical work more highly for the final corpus.

A cutoff such as 2018 or 2020 would be inappropriate because it could make persistent identity, provenance, structural correspondence, and classical document analysis appear newer or less developed than they actually are. The purpose of going back to 1990 is not to fill the corpus with historical papers; it is to prevent foundational terminology and methods from being silently excluded.
