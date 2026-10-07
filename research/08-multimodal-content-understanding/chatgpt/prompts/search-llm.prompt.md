You are one worker inside an automated literature-review pipeline.
A script, not a person, reads your reply. Follow these rules exactly:
- Do the task completely in this single reply. Do not ask questions and do not
  wait for confirmation.
- Reply with the requested artifact block(s) only: no preamble, no commentary
  outside the blocks. Each block starts with a line `===BEGIN <name>===` and
  ends with a line `===END <name>===`; the content between those lines is
  written to a file verbatim.
- Never invent papers, identifiers, numbers, or quotes. Leave unknown fields
  out or mark them as unknown.
- Do not use your code tool, canvas, or connectors; plain text is enough.

# Task: literature search

Research topic: **Direct empirical methods for cross-version multimodal document element lineage and hierarchical provenance, with special attention to revised workbook provenance and message referring-expression grounding into versioned pages, regions, and cells.**

Must-have terms: direct, empirical
Nice-to-have terms: cross-version, multimodal, document, element, lineage, hierarchical, provenance,, special, attention, revised, workbook, message, referring-expression, grounding, versioned, pages,, regions,, cells.
Date range: {"primary_months": 300, "fallback_months": 480}

Run every query below with your web search tool. Prefer arXiv listings
(arxiv.org/abs/<id>) but include other venues when they are clearly relevant;
much of the foundational work in a field is in conference proceedings rather
than on arXiv, and it must not be dropped for that reason. Aim for 30-60
distinct papers (at least 5). Stop when new searches only return papers
already listed.

Query families (from the terminology analysis; DIRECT means the
literature studies this problem, TRANSFER means the method may carry
over from another domain). Run every query:
- TF1 [DIRECT]
    "document version alignment" region correspondence semantic change
    "document revision alignment" page region correspondence
    "document version" element correspondence revision
    "document change detection" layout semantic revision
    "document differencing" semantic structural change
    "document revision" region matching
    "versioned document" element alignment provenance
    "document evolution" element correspondence
- TF2 [DIRECT]
    "persistent identity" document element revision
    "persistent identifier" document element version
    "document evolution" persistent identity
    "versioned document" provenance lineage
    "document revision history" element lineage
    "semantic diff" document revision
    "semantic differencing" document
    "XML diff" persistent identity document
- TF3 [DIRECT]
    "spreadsheet understanding" workbook formulas formatting
    "workbook understanding" formulas cross-sheet references
    "spreadsheet structure" merged cells hierarchical headers
    "spreadsheet semantics" formulas formatting units
    "spreadsheet" hidden rows hidden sheets named ranges formulas
    "workbook" merged cells named ranges cross-sheet references
    "spreadsheet representation" cell role formula layout
    "workbook structure" hidden sheet named range
- TF4 [DIRECT]
    "spreadsheet provenance" cell formula
    "cell provenance" spreadsheet
    "spreadsheet lineage" cell
    "spreadsheet dependency graph" formula cross-sheet
    "formula dependency" spreadsheet provenance
    "spreadsheet auditing" formula dependency
    "cell dependency graph" workbook
    "cross-sheet dependency" spreadsheet formula
    "spreadsheet formula" provenance lineage
- TF5 [DIRECT]
    "spreadsheet version" cell lineage
    "workbook version" cell correspondence
    "spreadsheet revision" formula change detection
    "spreadsheet evolution" cell correspondence
    "workbook revision" provenance
    "spreadsheet change detection" semantic
    "spreadsheet diff" formula structure
    "workbook diff" formula sheet cell
    "versioned spreadsheet" provenance
    "spreadsheet" revision history provenance cell
- TF6 [DIRECT]
    "referring expression grounding" document region table cell
    "referring expression" document screenshot table
    "multimodal coreference" document screenshot attachment
    "grounded coreference" document image region
    "cross-modal reference resolution" document
    "visual reference resolution" document table screenshot
    "deictic reference" document screenshot
    "document grounding" referring expression region
    "referring expression" spreadsheet cell
    "message" referring expression attachment document
    "email" referring expression attachment screenshot
    "attachment" referring expression grounding
- TF7 [DIRECT]
    "document region grounding" question answering
    "evidence localization" document visual question answering
    "answer grounding" document VQA region
    "cell grounding" document question answering
    "region-level evidence" document QA
    "fine-grained evidence" document question answering
    "source localization" document VQA
    "evidence region" DocVQA
    "page region" answer provenance document
    "document question answering" bounding box evidence
- TF8 [DIRECT]
    "multi-page document visual question answering" evidence
    "multi-page document" evidence localization
    "multi-page DocVQA" grounding
    "document VQA" page retrieval evidence
    "page retrieval" document visual question answering
    "multi-page document" region grounding
    "long document" multimodal question answering page evidence
    "multi-page document understanding" provenance
- TF9 [DIRECT]
    "visually rich document understanding" evidence grounding
    "layout-aware" document evidence localization
    "document AI" region grounding provenance
    "document information extraction" bounding box provenance
    "layout-aware language model" evidence
    "multimodal document understanding" source grounding
    "document understanding" layout region attribution
- TF10 [DIRECT]
    "table structure recognition" merged cells hierarchical headers
    "table structure recognition" spanning cells sparse tables
    "table understanding" headers units merged cells
    "table semantics" units formatting headers
    "table question answering" cell evidence
    "cell grounding" table question answering
    "table provenance" cell
    "table structure" hierarchical header provenance
    "table extraction" merged cells reading order
- TF11 [TRANSFER]
    "where-provenance" database
    "why-provenance" data provenance
    "data lineage" fine-grained provenance
    "provenance semiring" query
    "fine-grained data provenance" attribute
    "cell-level provenance" data
    "data provenance" versioned data lineage
    "provenance" hierarchical source lineage
    "provenance propagation" derived value source
- TF12 [TRANSFER]
    "referring expression comprehension" region grounding
    "referring expression grounding" visual region
    "phrase grounding" referring expression region
    "visual grounding" deictic reference
    "referring expression" highlighted region grounding
    "grounded referring expression" visual object
    "visual grounding" table region
    "phrase grounding" document image
- TF13 [TRANSFER]
    "multimodal coreference resolution" visual
    "multimodal coreference" dialogue visual
    "grounded coreference resolution" visual
    "cross-modal coreference" referring expression
    "visual coreference" dialogue grounding
    "reference resolution" multimodal dialogue region
    "deictic reference resolution" multimodal
- TF14 [TRANSFER]
    "evidence localization" scientific document question answering
    "evidence span" scientific document QA
    "evidence extraction" scientific question answering
    "citation localization" scientific paper evidence
    "source span" scientific document question answering
    "rationale extraction" scientific document QA
    "evidence attribution" scientific document answer
    "answer provenance" scientific document
- TF15 [TRANSFER]
    "document image registration" page alignment
    "document image change detection" page
    "page image alignment" document versions
    "document page alignment" image registration
    "layout matching" document versions
    "visual document differencing" revision
    "region correspondence" document images
    "document image" region matching revision
    "page correspondence" document revision
- TF16 [DIRECT]
    "document parsing" extraction completeness benchmark
    "document understanding" extraction completeness
    "document AI" robustness OCR noise layout
    "document VQA" unanswerable evidence grounding
    "document question answering" abstention unanswerable
    "multimodal document" failure analysis OCR layout
    "table structure recognition" OCR corruption robustness
    "document extraction" unsupported content evaluation
    "document understanding" reading order robustness
    "table extraction" sparse tables merged cells robustness
- TF17 [DIRECT]
    "long document" multimodal document benchmark latency
    "multi-page document" scaling question answering
    "document VQA" many pages efficiency
    "large workbook" benchmark spreadsheet understanding
    "spreadsheet benchmark" large workbook formulas
    "workbook" scalability formula analysis
    "large table" table question answering scalability
    "document understanding" memory latency multi-page
- TF18 [TRANSFER]
    "screenshot" referring expression grounding
    "screenshot grounding" referring expression
    "screen grounding" natural language region
    "GUI grounding" referring expression
    "visual grounding" screenshot UI
    "screen understanding" region grounding
    "figure grounding" text region
    "figure caption grounding" region
    "highlighted region" visual grounding
- TF1 [DIRECT]
    "document version alignment" multimodal provenance region lineage
    "document revision" semantic change region lineage provenance
    "versioned document" page region lineage
    "document version" provenance page region correspondence attachment
    "document evolution" semantic change visual layout
- TF5 [DIRECT]
    "revised workbook" provenance cell lineage
    "workbook revision" formula cell lineage
    "spreadsheet revision" hidden sheet named range provenance
    "versioned workbook" cross-sheet provenance
    "workbook version" merged cells formula lineage
- TF6 [DIRECT]
    "this screenshot" grounding document
    "highlighted row" referring expression grounding
    "numbers below" reference resolution table
    "attachment v2" reference resolution
    "use attachment" referring expression version
    "highlighted cell" referring expression spreadsheet
- TF7 [DIRECT]
    "evidence provenance" document question answering version page region cell
    "answer provenance" version page region cell
    "hierarchical provenance" document evidence
    "fine-grained provenance" page region cell answer
    "evidence hierarchy" document question answering
    "source attribution" page region cell answer span
    "answer span" document region provenance
False friends — these match the words but not the capability, so do
not list them:
- Downgrade papers that detect or OCR text but do not preserve document structure, source coordinates, or evidence identity.
- Downgrade papers that report answer accuracy without evidence localization when the claimed contribution is provenance or grounding.
- Downgrade single-version document methods when they are used as evidence for cross-version lineage; they may support representation or extraction only.
- Downgrade textual diff methods that cannot align moved, split, merged, reformatted, rasterized, or structurally transformed document elements.
- Downgrade visual diff or image-change methods that detect pixel differences without semantic element correspondence.
- Downgrade near-duplicate detection, plagiarism detection, and document-similarity work unless it establishes revision identity or element-level correspondence.
- Downgrade generic version control or source-code differencing unless the method is empirically evaluated on document, XML, spreadsheet, or comparable structured artifacts.
- Downgrade XML-tree differencing as TRANSFER evidence when the target evidence is rendered PDF, image regions, or spreadsheet semantics not represented in the XML task.
- Downgrade document layout analysis that stops at bounding boxes or region classes without linking those regions to language, evidence, or revisions.
- Downgrade table detection when cells, row-column topology, spanning cells, hierarchical headers, units, or reading order are not reconstructed.
- Downgrade table QA conducted on clean pre-extracted tables when making claims about PDF table extraction or workbook preservation.
- Downgrade spreadsheet work that converts sheets to CSV or flat tables and therefore discards formulas, formatting, merged cells, hidden structures, names, or cross-sheet references.
- Downgrade formula prediction or formula repair when it does not expose dependency or provenance relationships relevant to source tracing.
- Downgrade workbook reasoning evaluated on a single sheet when it is used to support claims about cross-sheet references, workbook-level semantics, or hidden sheets.
- Downgrade within-state spreadsheet provenance when it is used as evidence for provenance across workbook revisions.
- Downgrade natural-image referring-expression comprehension to TRANSFER unless the study uses documents, tables, screenshots, interfaces, or another structurally comparable surface.
- Downgrade image-text retrieval and contrastive alignment when there is no explicit referring expression and no localized referent.
- Downgrade visual dialogue coreference to TRANSFER unless referents are document elements or structurally comparable screen objects.
- Downgrade screenshot or GUI grounding to TRANSFER when the screenshot is an interactive interface rather than evidence embedded in a workplace attachment.
- Downgrade citation recommendation, bibliometrics, or citation-function classification; these do not provide source-location provenance.
- Downgrade RAG citation-generation papers when a citation identifies only a document or passage and does not validate the required page, region, cell, or answer-span hierarchy.
- Downgrade retrieval papers that find the correct attachment or page but do not ground the final answer to precise evidence.
- Downgrade multi-page QA that selects the correct page but provides no region or span localization when used to support fine-grained provenance.
- Downgrade scientific-PDF evidence localization to TRANSFER when it lacks attachment version identity or cross-version element lineage.
- Downgrade OCR-free document models if their evaluation cannot distinguish omitted content from correctly absent content.
- Downgrade parser benchmarks that report throughput or syntax coverage without measuring whether tables, images, layout, reading order, or unsupported features were preserved.
- Downgrade robustness studies that perturb OCR text only if they do not test structural corruption, merged tables, irregular reading order, embedded visuals, or scanned pages.
- Downgrade benchmark results that exclude unsupported examples from denominators; extraction completeness and failure accounting must remain explicit.
- Downgrade systems that silently return an empty result when extraction or grounding is unsupported; this violates the product distinction between genuine absence and processing failure.
- Downgrade provenance representations that identify only a source document but cannot represent at least one finer-grained level such as page, region, element, cell, or span.
- Downgrade a paper from DIRECT to TRANSFER if its empirical domain removes the central difficulty being claimed, such as using a clean relational table instead of a workbook or a single static image instead of a revision sequence.
- Do not treat combining several papers that separately solve document identity, page localization, region grounding, and cell provenance as validation of one end-to-end hierarchical provenance representation.
- Do not treat a filename, URL, or attachment label as stable document identity unless the method explicitly validates identity across renaming, replacement, or revision.
- Do not treat lexical similarity between old and new regions as lineage unless correspondence is empirically validated against moves, edits, splits, merges, or structural changes.
- Do not treat synthetic or transfer-domain success as evidence of production-email accuracy; retain the DIRECT versus TRANSFER distinction.
Reach back to 1990 at least. Discovery must reach at least 1990. The target combines several literatures whose modern neural forms are recent but whose foundations are substantially older: document image analysis, page segmentation, reading order, table recognition, document matching, and image registration were established before modern Document AI; database provenance and XML change tracking became important in the early 2000s; modern DocVQA, layout-aware transformers, and multimodal foundation models are mostly much later. A 2018, 2020, or similarly recent cutoff would therefore silently remove foundations needed to interpret persistent identity, structural correspondence, provenance, and document-layout evaluation. Round 4 should still prioritize recent direct evidence, but discovery should permit foundational results from 1990 onward.

This is gap-closure round 4 of at most 4 for the
original topic **email, image, table and attachment understanding in workplace communication: preserving multimodal and document structure, and grounding evidence back to precise source locations such as a cell, region, page or attachment version**. Earlier rounds could not
close the open gaps below. Run every suggested query as well, and look
specifically for papers that answer these gaps:
- gap-1 [ACADEMIC, HIGH]: The corpus still does not establish a complete method for maintaining evidence provenance across successive workplace attachment revisions, including stable attachment identity, version-relative source locations, semantic changes between versions, and lineage from an older cited region to its later counterpart. Version-aware retrieval, scientific-PDF alignment, and XML persistent identity cover separate components, but the full multimodal attachment-revision provenance problem remains unvalidated.
    suggested query: "document version alignment" multimodal provenance region lineage semantic change revised document attachments
    searched in rounds: [1, 2, 3] (still open)
- gap-2 [ACADEMIC, HIGH]: Direct grounding of workplace-message referring expressions such as "this screenshot", "the highlighted row", "numbers below", or "use attachment v2" into attachment objects, pages, cells, or regions remains unvalidated. Existing scene-text and visually grounded dialogue studies provide adjacent-domain evidence only.
    suggested query: "referring expression grounding" document multimodal attachment table cell screenshot coreference email
    searched in rounds: [1, 2, 3] (still open)
- gap-3 [ACADEMIC, HIGH]: Comprehensive spreadsheet understanding remains open for formulas, hidden rows and sheets, cross-sheet references, merged regions, formatting semantics, units, named ranges, and provenance across revised workbook versions. Current workbook studies address retrieval, structure reconstruction, verification, workflow completion, and within-state cell provenance but not this complete set.
    suggested query: "spreadsheet understanding" workbook formulas hidden sheets named ranges merged cells cross-sheet provenance version
    searched in rounds: [1, 2, 3] (still open)
- gap-4 [ACADEMIC, HIGH]: No admitted paper validates one end-to-end provenance representation that jointly identifies attachment version, page, document element, exact region or spreadsheet cell, and answer span. Different studies validate subsets of this hierarchy, and their combination remains untested.
    suggested query: "evidence provenance" document question answering version page region cell answer span multimodal grounding
    searched in rounds: [1, 2, 3] (still open)

Papers already reviewed in earlier rounds (do NOT list them again):
1911.10683, 2006.14806, 2010.12537, 2104.12756, 2106.11539, 2111.07129, 2203.09056, 2212.05935, 2401.00908, 2407.01523, 2412.18424, 2503.23131, 2505.16470, 2510.08109, 2511.12003, 2601.08741, 2604.12282, 2605.12882, 2606.15906, 2606.29955, 2607.14117, 2607.24651, 2607.29638, 2608.03292, 2609.08364, doi-10-1002-spe-2305, doi-10-1007-3-540-44503-x-20, doi-10-1007-978-3-540-30480-7-29, doi-10-1007-s00521-022-06948-5, doi-10-1109-tmm-2022-3219642, doi-10-18653-v1-2020-acl-main-398, doi-10-18653-v1-2025-acl-long-547, doi-10-18653-v1-2025-findings-naacl-295, doi-10-18653-v1-2026-eacl-long-192, manual-0661fc0cba, manual-1048d6caf2, manual-7fdf40b3c6, manual-ae200642f8

Write one JSON object per line. Fields (only `title` is mandatory):
- title: exact paper title
- url: arxiv.org/abs/<id> when available, else the landing page
- arxiv_id: e.g. 2401.12345 (omit when not on arXiv)
- doi: if known
- authors: list of author names
- year: integer
- published: YYYY-MM-DD if known
- abstract: the abstract, or a faithful paraphrase of at most 5 sentences
- venue: conference or journal if known

Reply format (one block, one JSON object per line, no array brackets):
===BEGIN llm_candidates.jsonl===
<content>
===END llm_candidates.jsonl===
