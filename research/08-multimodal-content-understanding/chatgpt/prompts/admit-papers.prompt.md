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

# Task: admission gate for 25 screened candidate(s)

Research topic: **Direct empirical methods for cross-version multimodal document element lineage and hierarchical provenance, with special attention to revised workbook provenance and message referring-expression grounding into versioned pages, regions, and cells.**

Decide which of these candidates enters the reading round. Admit a paper only
when it materially strengthens one of the research streams below, and the
abstract shows that, not merely shared vocabulary. A paper count is never a
reason to admit: admitting six of twenty is a valid answer, and so is
admitting none. Rejecting a paper here costs little; reading a paper that
cannot strengthen a stream costs a reading slot that a better paper needed.

Research streams:
- TF1 [DIRECT] Cross-version document alignment and element correspondence: Align successive revisions of a document and determine which page, region, block, table, figure, or other element in one version corresponds to which element in another, including moves, splits, merges, insertions, deletions, and changed content.
- TF2 [DIRECT] Document evolution, semantic differencing, and persistent element identity: Represent document revisions as an evolution history in which document components retain or acquire persistent identities and changes are classified structurally or semantically rather than only as text edits.
- TF3 [DIRECT] Spreadsheet and workbook structural-semantic understanding: Model spreadsheets as workbooks containing sheets, regions, headers, formulas, formatting, merged cells, hidden structures, named ranges, units, cross-sheet references, and other semantics beyond a flat table.
- TF4 [DIRECT] Spreadsheet formula dependency, auditing, and cell-level provenance: Recover, analyze, or trace formula dependencies and cell-to-cell relationships, including cross-sheet dependency graphs and explanations of how derived values depend on source cells.
- TF5 [DIRECT] Versioned spreadsheet and workbook lineage: Relate cells, ranges, formulas, sheets, names, and structural regions across workbook revisions and identify semantic changes while preserving their history.
- TF6 [DIRECT] Message-to-document referring-expression grounding: Resolve discourse expressions such as this screenshot, the highlighted row, numbers below, that table, or attachment v2 to a concrete attachment object, version, page, region, table, cell, or range.
- TF7 [DIRECT] Document-region and cell-level evidence grounding: Ground a question, generated answer, claim, or extracted fact to exact document evidence such as a page, bounding region, table cell, or source span.
- TF8 [DIRECT] Multi-page document visual question answering and evidence routing: Answer questions over multi-page documents while selecting relevant pages and, where supported, localizing evidence within them.
- TF9 [DIRECT] Visually rich document representation and layout-aware extraction: Encode text, two-dimensional layout, and visual features so document regions, tables, and other elements retain structural context during extraction and reasoning.
- TF10 [DIRECT] Table structure recognition and semantic table understanding: Recover table cells, spanning structure, hierarchical headers, row-column associations, and semantic relationships required before cell-level grounding or QA.
- TF11 [TRANSFER] Fine-grained data provenance and lineage: Database and data-management work formalizing where results came from, which source items contributed to them, and how provenance propagates through transformations.
- TF12 [TRANSFER] Visual referring-expression comprehension and phrase grounding: Resolve linguistic descriptions to visual objects or regions, usually in natural images.
- TF13 [TRANSFER] Multimodal coreference and grounded reference resolution: Resolve linguistic expressions across turns or discourse when the referent is represented visually or in another modality.
- TF14 [TRANSFER] Scientific-document evidence localization and source-span attribution: Question answering or claim support over scientific documents where systems identify supporting passages, evidence spans, pages, or document sections in addition to producing an answer.
- TF15 [TRANSFER] Document image registration, visual change detection, and page correspondence: Geometrically align page images or layouts and detect changed regions across scans, renderings, or document versions.
- TF16 [DIRECT] Failure-aware document QA and extraction evaluation: Evaluate answerability, abstention, OCR and parser failures, localization errors, structural corruption, and extraction completeness rather than scoring only successful answers.
- TF17 [DIRECT] Long-document and large-workbook robustness and scaling: Measure quality, latency, memory, routing, and failure behavior as page counts, table sizes, workbook sizes, and structural complexity increase.
- TF18 [TRANSFER] Screenshot, GUI, and visual-region grounding: Ground instructions or referring expressions to regions and interface elements in screenshots or rendered screens.

Open gaps this round must close (a paper that speaks to one of these
is worth admitting even when its topic wording is unusual):
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
- gap-5 [ENGINEERING, HIGH]: End-to-end behavior when extraction or grounding is unsupported, incomplete, or wrong remains insufficiently exercised. The corpus contains unanswerable-question evaluation and parser, retrieval, OCR, localization, and grounding failure analyses, but not a complete engineering contract distinguishing genuine evidence absence from parser, OCR, layout, retrieval, or grounding failure.
- gap-6 [ENGINEERING, HIGH]: Robustness of candidate extraction and structural-preservation pipelines on heterogeneous workplace-style documents remains an engineering gap. No admitted benchmark jointly exercises sparse tables, merged and hierarchical structures, OCR corruption, irregular reading order, embedded visual objects, scanned pages, and explicit extraction-completeness accounting.
- gap-7 [ENGINEERING, MEDIUM]: Operational scaling remains open for long documents, large tables, and realistic workbooks. The corpus reports page-routing costs, evidence-graph overhead, parsing limits, workbook inspection failures, and trade-offs in change detection, but does not close the system-level latency, memory, and throughput question for the target workload.
- gap-8 [ENGINEERING, HIGH]: The corpus lacks one evaluation that simultaneously measures semantic correctness, extraction completeness, exact provenance, unsupported-evidence handling, and preservation of tables, images, document hierarchy, and reading order on workplace-style attachments. Existing benchmarks and metrics evaluate overlapping subsets rather than the complete combination.
Decisions:
- ADMIT — name the stream and why the abstract shows the contribution.
- REJECT — name the reason: topic words match but the capability does not,
  the evidence duplicates a paper already admitted, or the claim is out of
  scope.
- PENDING — the abstract cannot settle it; say what would.

`identity: UNCHECKED` means the host could not confirm the paper's identifier
with the provider. That is not proof the paper is wrong, but prefer a
VERIFIED paper when the two are otherwise equal, and say so in the reason.


## Project context you must work within

This is the project's own description of the problem, its boundaries,
and the distinctions it needs preserved. It governs what counts as
relevant; the academic task names alone do not.

# Topic 08 context — Email, image, table, and attachment understanding

## Why this Topic exists

Important work information is not confined to plain message text. It appears in HTML layout, tables, screenshots, scanned PDFs, spreadsheets, Word documents, diagrams, inline images, and attachments with multiple versions. A message may say “see the highlighted row”, “numbers below”, “use attachment v2”, or “the red box is the issue”. Flattening everything into plain text can destroy relationships, units, coordinates, visual emphasis, or version identity.

Topic 08 owns **preserving and interpreting multimodal/document structure and grounding evidence back to precise source locations**.

## Product and phase relevance

Basic extraction of collected Excel/PDF/Word attachments is a Phase 1 A2 responsibility; failures and unsupported features must remain explicit. Topic 08 research goes beyond parser selection to the semantic question of whether tables/layout/images and cross-modal references can be understood without losing decision-relevant content. Phase 2 may retrieve additional attachments through Topic 07/A4, but retrieved content still uses A1/A2 preservation and parsing contracts.

## Direct handoffs from earlier Topics

Topic 04 (completed 2026-09-16, 47 papers, 4 rounds) covers reference resolution over text propositions only. References to tables, screenshots, attachments, cells, pages or visual regions were excluded from its corpus and are handed to Topic 08 for grounding. Topic 04 still owns the *scope* question once such an object is grounded: which proposition the response applies to.

**The full text of every inherited handoff is in [`INHERITED_HANDOFFS.md`](INHERITED_HANDOFFS.md)**, including what each sending Topic established, what it left open, and where the ownership boundary lies. Read it before planning; you do not need to open an earlier Topic's folder.

## Relationships to other Topics

| Topic | Relationship |
| --- | --- |
| 01 | HTML/layout/forwarded blocks can affect quote boundaries; Topic 01 owns email quotation provenance. |
| 02 | Extracted document spans/regions may belong to one or multiple Topics. |
| 04 | References such as “see row 4”, “this screenshot”, or “attachment version two” require multimodal grounding. |
| 05 | Actions/deadlines/decisions can reside in tables or attachments. |
| 06 | Versioned documents can supersede or contradict earlier state. |
| 07 | Retrieves missing attachments/documents; Topic 08 interprets their content. |
| 09 | Briefing must preserve critical structured evidence rather than summarizing only body text. |
| 10 | Evaluates extraction completeness, grounding/citation correctness, and omission of multimodal evidence. |

## Key conceptual distinctions

- Parsing success ≠ complete understanding.
- OCR text ≠ layout/table understanding.
- Text extraction ≠ reading order correctness.
- Table cell values ≠ table semantics/units/headers/merged relationships.
- Attachment filename ≠ document version identity.
- Visual grounding ≠ generic image captioning.
- A missing/unsupported region must be a limitation, not an empty successful result.

## High-value academic terminology

- document AI / document intelligence;
- visually rich document understanding (VRDU);
- document layout analysis; layout-aware language models;
- document information extraction;
- document visual question answering (DocVQA);
- multi-page document understanding / long-document multimodal understanding;
- OCR + layout understanding; reading order detection;
- table detection; table structure recognition (TSR); table understanding;
- table question answering; spreadsheet understanding;
- chart understanding / chart QA (when relevant);
- multimodal information extraction;
- multimodal coreference; cross-modal reference resolution;
- visual grounding / referring expression comprehension;
- document region grounding / citation localization;
- scanned document understanding;
- document version comparison / visual document differencing (supporting evidence).

## Query families

- `"visually rich document understanding" layout`
- `"document layout analysis" information extraction`
- `"document visual question answering" grounding`
- `"multi-page document understanding" multimodal`
- `"table structure recognition" business documents`
- `"table understanding" document AI`
- `spreadsheet understanding semantic table`
- `"multimodal coreference" document`
- `"visual grounding" document screenshot`
- `document region grounding citation`
- `scanned PDF information extraction layout`
- `document version comparison semantic change`

## False friends / exclusions

- OCR character accuracy alone;
- image captioning with no source-location grounding;
- generic VQA with no document structure;
- parser throughput benchmarks that do not measure meaning preservation;
- Topic 07 retrieval/search;
- Topic 04 language-only reference resolution when the referent is already textually available.

## Gap-evaluation guidance

Prioritize failure modes that hide or distort evidence that could change a decision: wrong table row/column associations, lost units, omitted scanned pages, unsupported embedded objects, wrong attachment version, or unresolved visual references. Performance is secondary to meaning preservation. Clearly separate Phase 1 extraction coverage from deeper semantic interpretation and from Phase 2 retrieval.

## How to use this file

This file is the self-contained research context for this Topic. A future AI research agent should read **this file first**, then `BRIEF.md`, then any existing `CURRENT_STATUS.md`, gap decisions, reports, manifests, and prior-round artifacts in this folder. The aim is that an agent given only this Topic folder can reconstruct the project intent, Topic boundary, dependencies, search vocabulary, and gap-prioritization logic without relying on the original ChatGPT conversation.

If the full repository is available, the authoritative product documents remain `../../docs/design-brief.md`, `../../docs/design-principles.md`, `../../docs/design.md`, and `../../docs/phase-roadmap.md`. This file explains how those product constraints apply to this research Topic; it does not replace or approve changes to those design documents.

## Shared msgloom background

msgloom is a personal work-information system for one user. It is intended to process very large daily volumes of work communication, initially Outlook email and Microsoft Teams, while ensuring that **work requiring the user's response is not missed** and reducing how much the user must read to stay current.

The product is organized around **Topics**, not message summaries. A Topic is a concrete work matter described by information from one or more sources. One message can contain several Topics; one Topic can span many messages, conversations, attachments, groups, and eventually multiple sources. A conversation or Group is therefore not automatically one Topic.

The report contract is the ultimate product pressure on all ten research Topics. Reports must preserve every due Topic and the decision-relevant information needed to act on it, including developments, actions, deadlines, conditions, risks, uncertainty, and links back to exact source evidence. Missing or conflicting information must remain visible rather than being silently filled in.

The design decision order is important when evaluating research gaps: user permissions are fixed; then preserve correct meaning and report coverage; then traceability and recovery; then usability/maintenance; finally speed, brevity, and token savings. A method that is faster but loses a condition, deadline, branch, source relation, or important Topic is not an improvement for msgloom.

Important persistent principles:

- Use deterministic code for reliable mechanical relationships and AI for language understanding/judgement.
- Preserve source bytes, versions, stage history, identities, and lineage. New assessments do not erase old evidence.
- Group only on reliable relationships. Similar subjects, participants, wording, or model labels are not enough to prove Topic identity.
- Keep uncertain relationships separate and make the reason for uncertainty visible.
- Brevity must come from concise wording and layered detail, never from omitting decision-essential information.
- User-reviewed examples, missed important work, false alerts, wrong grouping, lost actions/deadlines, and evidence that changes a decision matter more than paper count or message throughput.

## Research-programme relationship

The ten Topics form a dependency network rather than ten independent literature reviews. A useful conceptual flow is:

```text
01 source/conversation structure
        ↓
02 within-message Topic spans/membership
        ↓
03 cross-thread/source Topic identity
        ↓
04 reference and response scope
        ↓
05 actions / requests / commitments / decisions
        ↓
06 state / factuality / time / revision
        ↓
07 retrieve missing context when needed
        ↘
08 understand attachments / tables / images
        ↓
09 incremental personalized briefing
        ↓
10 evidence, completeness, calibration, reliability evaluation
```

This is not a strict processing pipeline. Several Topics feed each other, and Topic 10 is cross-cutting. The numbering primarily gives a research order and ownership boundary so that one Topic does not silently absorb the whole product problem.

## Gap-evaluation rules inherited from Topics 01 and 02

The Research Pipeline must evaluate gaps using **project value**, not just academic novelty. The following rules are part of the context for every Topic:

1. A machine-classified `HIGH` or `ACADEMIC` gap does **not** automatically authorize another literature round.
2. After each academic round, perform a human/project-value review: decide whether the uncertainty is best addressed by more papers, engineering experiments, a later Topic, production-domain data, candidate-method selection, or no further current work.
3. Prefer targeted academic follow-up over broad searching. Do not fill paper quotas with weakly related literature.
4. Distinguish direct target-domain evidence from transfer methods/evaluation evidence. Transfer evidence can justify a mechanism or experiment, not production-email accuracy.
5. Engineering validation may use independent synthetic/adversarial fixtures and public data. Lack of production mailbox examples is not a reason to stop work that can be validly completed without them.
6. Never claim production representativeness from synthetic or transfer evidence. Record it as deferred until suitable authorized domain data exists.
7. If a gap belongs to another Topic, hand it off explicitly rather than duplicating research.
8. Research closure means **everything actionable at the current stage is complete and remaining work is explicitly deferred/handed off**. It does not mean literature exhaustion, production accuracy, or architecture approval.
9. For new academic work, use terminology refinement, strict paper admission, manual/controlled canonical acquisition, corpus freeze, fresh isolated Pipeline runs, direct-vs-transfer labels, independent review, strict validation, and post-round gap review. These are lessons learned from Topics 01 and 02.
10. For engineering research, keep gold independent from the component under test; structurally separate prediction inputs from evaluation gold/future context; count false positives and false negatives in end-to-end denominators; use clean-workspace reproducibility, mutation/regression tests, and fresh independent methodological review.

## Work handed to this topic by an earlier one

Treat each entry as a starting condition, not as something to
rediscover. Where a sending topic left a gap open it is still open:
do not report it as established. Respect the stated ownership
boundary and do not absorb what the sender still owns.

**None of this is evidence for your own report.** It scopes your
work; it does not support a finding or a gap. Only papers this
topic admitted can do that.

# Inherited handoffs

Everything an earlier Topic explicitly handed to this one, copied in full so
that this folder is enough on its own. You do not need to open an earlier
Topic's documents to start work here.

Each entry states what was handed over, what the sending Topic still owns, and
what it had established or left open at the time. A handoff is not a finding:
where the sender left a gap open, it is still open.

## From Topic 04 — Reference resolution and response scope

*Completed 2026-09-16. 4 rounds, 47 papers, report validated PASS.*

**Handed to Topic 08.** References to tables, screenshots, attachments,
cells, pages and visual regions. Topic 04's corpus covers reference
resolution over text propositions only; these were excluded from it by
design, so Topic 04's evidence says nothing about them.

**Boundary.** Topic 08 owns grounding the referenced object. Topic 04 still
owns the scope question once it is grounded: which proposition the response
applies to. A grounded object is not yet a scoped response.

## From Topic 05 — Action items, requests, commitments and decisions

*Completed 2026-09-16. 4 rounds, 48 papers.*

**Handed to Topic 08.** Action evidence that lives in attachments, tables or
screenshots. Topic 05's corpus covers text; where the deadline or the object
of an action is only in an attached file, Topic 08 supplies the grounded
content and Topic 05 still owns what the action is.

**Related open gap.** Topic 05's G8 covers zoning author, quoted and forwarded
text while preserving provenance. Attachment references are part of that
surface and are not yet evidenced.

Candidates:
- paper_id `manual-d896e242a6` [identity: UNCHECKED] J-CRe3: A Japanese Conversation Dataset for Real-world Reference Resolution (2024, LREC-COLING 2024)
    Provides conversational data in which linguistic referring expressions are linked across modalities to real-world objects represented by bounding boxes. It covers direct and indirect references and supplies empirical transfer evidence for language-to-region grounding.
- paper_id `2404.05719` [identity: VERIFIED] Ferret-UI: Grounded Mobile UI Understanding with Multimodal LLMs (2024)
    Extends region-level multimodal understanding to mobile UI screenshots with tasks including referring, grounding, and reasoning over interface regions. Its region annotations and empirical benchmarks provide transfer evidence for expression-to-region grounding on structured screenshots.
- paper_id `doi-10-1109-icde-2002-994696` [identity: UNCHECKED] Detecting Changes in XML Documents (2002, 18th International Conference on Data Engineering (ICDE 2002))
    Presents an XML differencing method that uses persistent node identifiers to track document components across versions and represents insertions, deletions, updates, and subtree moves. The method is empirically evaluated on synthetic data and web-derived XML documents and provides direct structured-document evidence for persistent element identity.
- paper_id `2404.19024` [identity: VERIFIED] Multi-Page Document Visual Question Answering using Self-Attention Scoring Mechanism (2024, International Conference on Document Analysis and Recognition (ICDAR 2024))
    Addresses multi-page DocVQA by assigning relevance scores to pages and selecting pertinent pages before answer generation. Experiments study document collections containing many pages, providing empirical page-level evidence localization but not exact region or cell provenance.
- paper_id `doi-10-1145-1265530-1265535` [identity: UNCHECKED] Provenance Semirings (2007, ACM Symposium on Principles of Database Systems (PODS 2007))
    Introduces a general algebraic framework in which provenance annotations are propagated through relational queries. The representation provides transfer foundations for compositional lineage of derived values, although its empirical domain is relational data rather than versioned multimodal documents.
- paper_id `manual-bc798b0eed` [identity: UNCHECKED] GRAVL-BERT: Graphical Visual-Linguistic Representations for Multimodal Coreference Resolution (2022, COLING 2022)
    Represents dialogue, scene objects, and their relationships jointly for multimodal coreference resolution. Experiments require linking language mentions to visual objects across conversational context, offering transfer evidence for grounding message references to structured visual entities.
- paper_id `manual-8444bbc95c` [identity: UNCHECKED] Performance Evaluation and Error Analysis for Multimodal Reference Resolution in a Conversation System (2004, HLT-NAACL 2004)
    Evaluates multimodal reference resolution in a conversational system and analyzes errors arising from combining language with nonlinguistic input. It provides early empirical evidence on resolving references to visually or interactively available entities.
- paper_id `doi-10-18653-v1-d19-1209` [identity: UNCHECKED] Dual Attention Networks for Visual Reference Resolution in Visual Dialog (2019, EMNLP-IJCNLP 2019)
    Models visual reference resolution in dialogue with dedicated mechanisms for finding and referring to visually grounded entities. The method is empirically evaluated in visual-dialog settings and serves as transfer evidence for multimodal referring-expression grounding.
- paper_id `1704.08476` [identity: VERIFIED] SpreadCluster: Recovering Versioned Spreadsheets through Similarity-Based Clustering (2017, 14th IEEE/ACM International Conference on Mining Software Repositories (MSR 2017))
    Learns similarity criteria such as worksheet-name and table-header features from known version groups and uses them to cluster spreadsheets likely to be versions of the same evolving artifact. It is evaluated on Enron spreadsheets and additional spreadsheet corpora and is used to construct the VEnron2 versioned corpus.
- paper_id `doi-10-1109-icse-2012-6227171` [identity: UNCHECKED] Detecting and visualizing inter-worksheet smells in spreadsheets (2012, 34th International Conference on Software Engineering (ICSE 2012))
    Analyzes dependencies between worksheets and proposes inter-worksheet smells and visualizations for identifying problematic workbook structure. The approach is evaluated on spreadsheet corpora and industrial case studies, providing empirical evidence for workbook-level dependency analysis.
- paper_id `doi-10-1145-357775-357777` [identity: UNCHECKED] Tracing the lineage of view data in a warehousing environment (2000, ACM Transactions on Database Systems)
    Defines and implements lineage tracing from derived warehouse view data back to the source data items that contributed to each result. The work handles query transformations including aggregation and provides transfer evidence for fine-grained derived-value-to-source provenance.
- paper_id `doi-10-18653-v1-2024-naacl-industry-9` [identity: UNCHECKED] Visual Grounding for User Interfaces (2024, NAACL 2024 Industry Track)
    Takes a user-interface screenshot together with a free-form referring expression and identifies the interface element denoted by that expression. The method incorporates layout information and is empirically evaluated on screenshot grounding, making it structurally close transfer evidence for references such as highlighted or nearby screen regions.
- paper_id `doi-10-1007-3-540-48172-9-21` [identity: UNCHECKED] The T-Recs Table Recognition and Analysis System (2026, Document Analysis Systems: Theory and Practice)
    Presents a bottom-up table structure recognizer that clusters word segments, constructs a tile structure, and recovers row- and column-spanning cells as well as sparse tables. It is designed to work across mixed-mode documents and low-quality OCR, making it foundational evidence for preserving nontrivial table topology.
- paper_id `2410.05243` [identity: VERIFIED] Navigating the Digital World as Humans Do: Universal Visual Grounding for GUI Agents (2024)
    Studies universal GUI grounding from natural-language references to elements in screenshots and builds large-scale training data from GUI elements and referring expressions. Evaluation across multiple GUI grounding benchmarks provides broad transfer evidence for language-to-region grounding on structured visual surfaces.
- paper_id `doi-10-1080-00140139108964845` [identity: UNCHECKED] Extracting implicit tree structures in spreadsheet calculation (1991, Ergonomics)
    Empirically studies how implicit computational structures are extracted from spreadsheet calculations. Experiments involving multiple spreadsheet types provide early evidence that spreadsheet computations possess higher-level hierarchical organization beyond individual cells.
- paper_id `2209.02215` [identity: VERIFIED] Reference Resolution and Context Change in Multimodal Situated Dialogue for Exploring Data Visualizations (2022)
    Empirically studies reference resolution in multimodal dialogue where people discuss data visualizations while also using gestures. The work models how referring expressions establish or revisit visual entities and supplies structurally relevant transfer evidence for grounding workplace references into visual regions.
- paper_id `2604.13731` [identity: VERIFIED] Doc-V*: Coarse-to-Fine Interactive Visual Reasoning for Multi-Page Document VQA (2026, ACL 2026)
    Presents coarse-to-fine reasoning over multi-page documents with iterative page retrieval, evidence accumulation, and structured working memory. The evaluation targets long multi-page document VQA and provides version-independent page-level evidence-selection results.
- paper_id `doi-10-1145-2950290-2950359` [identity: UNCHECKED] Detecting table clones and smells in spreadsheets (2016, 24th ACM SIGSOFT International Symposium on Foundations of Software Engineering (FSE 2016))
    Introduces TableCheck for matching spreadsheet tables using header information and detecting inconsistent corresponding cells among table clones. The empirical evaluation studies spreadsheets in the EUSES corpus and provides evidence about correspondence among copied and independently evolving spreadsheet regions.
- paper_id `manual-2e524ca7bc` [identity: UNCHECKED] Multi-modal Reference Resolution in Situated Dialogue by Integrating Linguistic and Extra-Linguistic Clues (2011, IJCNLP 2011)
    Combines linguistic context with extra-linguistic visual information for resolving references in situated dialogue. The empirical task requires linking referring expressions to entities in the shared visual environment, making it transfer evidence for attachment-region reference resolution.
- paper_id `doi-10-3390-app152312430` [identity: UNCHECKED] Document Image Verification Based on Paragraph Alignment and Subtle Change Detection (2025, Applied Sciences)
    Compares an input document image against a corresponding reference document by retrieving the reference, aligning paragraphs using structural features, and detecting subtle content changes under print-scan distortions. Experiments on constructed document-image databases evaluate both correspondence and change detection.
- paper_id `2506.21055` [identity: VERIFIED] Class-Agnostic Region-of-Interest Matching in Document Images (2025)
    Defines a document-image task in which a user-selected reference region must be matched to the corresponding region in another target document image. The proposed benchmark covers multiple difficulty levels and the baseline uses Siamese feature extraction and cross-attention to align semantically similar regions at multiple granularities.
- paper_id `2401.10935` [identity: VERIFIED] SeeClick: Harnessing GUI Grounding for Advanced Visual GUI Agents (2024)
    Trains a vision-language model to ground natural-language instructions directly to locations in GUI screenshots and introduces evaluation for GUI grounding. Although the surface is an interactive interface rather than a workplace attachment, the task directly tests expression-to-screen-region localization.
- paper_id `manual-ae3d9ddaf8` [identity: UNCHECKED] Matching document images with ground truth (1998, International Journal on Document Analysis and Recognition)
    Develops methods for aligning document images with electronic ground-truth representations so that source information can be associated with positions in scanned images. The work is an early document-image alignment foundation for transferring logical or textual annotations to image coordinates.
- paper_id `doi-10-1117-12-2003911` [identity: UNCHECKED] Semi-structured document image matching and recognition (2013, Proceedings of SPIE)
    Studies matching, recognition, and localization of semi-structured document images using techniques adapted from visual object recognition. The method addresses repeated textual patterns and variable layouts, making it relevant transfer evidence for document-region correspondence.
- paper_id `doi-10-18653-v1-2026-acl-long-1679` [identity: UNCHECKED] Flow-Based Page Unique Semantic Mapping Architecture for Document Visual Question Answering (2026, ACL 2026)
    Introduces FUMA for distinguishing semantically similar document pages and localizing evidence through question-conditioned page representations and reversible flow-based mappings. Experiments evaluate both evidence localization and answer generation, but the localized unit is primarily the page rather than a complete page-region-cell hierarchy.

JSON schema:
{
 "$schema": "http://json-schema.org/draft-07/schema#",
 "title": "PaperAdmission",
 "description": "Per-candidate admission decision. A paper enters the reading round only when it materially strengthens an authorized research stream; a paper count is never a reason to admit.",
 "type": "object",
 "required": [
  "decisions"
 ],
 "properties": {
  "round": {
   "type": "integer",
   "minimum": 1
  },
  "streams": {
   "type": "array",
   "description": "The authorized research streams this round admits against.",
   "items": {
    "type": "object",
    "required": [
     "id",
     "description"
    ],
    "properties": {
     "id": {
      "type": "string",
      "minLength": 1
     },
     "description": {
      "type": "string",
      "minLength": 1
     }
    }
   }
  },
  "decisions": {
   "type": "array",
   "minItems": 1,
   "items": {
    "type": "object",
    "required": [
     "paper_id",
     "decision",
     "reason"
    ],
    "properties": {
     "paper_id": {
      "type": "string",
      "minLength": 1
     },
     "decision": {
      "type": "string",
      "enum": [
       "ADMIT",
       "REJECT",
       "PENDING"
      ]
     },
     "reason": {
      "type": "string",
      "minLength": 1
     },
     "stream_id": {
      "type": "string",
      "description": "Required for ADMIT: the stream this paper materially strengthens."
     },
     "role": {
      "type": "string",
      "enum": [
       "DIRECT",
       "TRANSFER"
      ]
     },
     "confidence": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0
     }
    }
   }
  },
  "notes": {
   "type": "string"
  }
 },
 "additionalProperties": true
}

Reply with one block containing one JSON object with a `decisions` array
covering every paper_id above, and a `streams` array describing the streams
you admitted against.
===BEGIN admission.json===
<content>
===END admission.json===
