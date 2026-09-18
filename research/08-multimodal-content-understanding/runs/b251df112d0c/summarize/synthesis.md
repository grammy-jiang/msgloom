# Executive Summary

Across 14 papers, the evidence separates document understanding into complementary layers rather than a single solved task. Structure-aware representations improve table and document tasks on web tables, forms, receipts, and long PDFs, while image-based table systems address recovery of spatial cells from page images. Multi-page benchmarks show persistent degradation for later, cross-page, and multimodal evidence. Provenance is demonstrated at several granularities—selected cells, pages, bounding boxes, and segmentation masks—but no paper in this corpus validates a unified chain from attachment version to page to precise region or cell. Grounding and answering are also distinct: correct localization can coexist with incorrect reasoning, and correct answers can be paired with wrong evidence pages. Visual features are not uniformly beneficial; observed gains depend on task, representation, and model. Direct evidence for email-linked attachments and longitudinal version identity remains limited.

# Themes

## Structure preservation affects downstream understanding

Across independent tasks, explicit structure improves measured performance. TURL preserves row-column relationships in relational web tables [2006.14806], TUTA benefits from tree-structured attention and position encodings on general structured-table tasks [2010.12537], and DocFormer reports gains from spatial and multimodal information on form and receipt/entity extraction [2106.11539]. LongDocURL separately reports substantial QA improvements when structure-preserving parsed text is used instead of plain PyMuPDF extraction [2412.18424].

These results validate different representations on different tasks; they do not jointly validate one combined document-processing scheme.

## Table reconstruction and table semantics are distinct

Image-based systems address reconstruction of table geometry that semantic table models often assume has already been supplied. EDD recognizes structure and content from table images, but the PubTabNet version evaluated in the paper lacks individual cell coordinates [1911.10683]. The complex-table framework in [2111.07129] instead retains detected cell boxes while recovering rectilinear relations and row/column spans.

By contrast, TURL, TUTA, and TAPAS begin from structured tables. They preserve row-column, tree, or selected-cell relationships, but do not map those structures back to source-document page pixels or attachment identities [2006.14806] [2010.12537] [doi-10-18653-v1-2020-acl-main-398].

## Provenance exists at multiple granularities, but in separate systems

The corpus demonstrates several distinct grounding levels. TAPAS explicitly selects supporting cells before optional aggregation [doi-10-18653-v1-2020-acl-main-398]. Hi-VT5 predicts the page containing answer evidence [2212.05935]. RefChartQA trains models to generate supporting chart-element bounding boxes [2503.23131]. M3Grounder describes per-answer-span phrase-, line-, and block-level segmentation masks [manual-0661fc0cba].

These are separately validated mechanisms. No admitted paper experimentally validates a combined attachment-version → page → region/cell → answer-span provenance hierarchy.

## Long and distributed evidence remains difficult

Hi-VT5 outperforms evaluated concatenation baselines in realistic multi-page QA, with its relative advantage increasing when the answer occurs later in the document [2212.05935]. MMLongBench-Doc likewise reports poorer results for cross-page questions and evidence appearing later in long documents [2407.01523]. LongDocURL contains substantial multi-page and cross-element evidence and still reports a large gap between evaluated models and its human baseline [2412.18424].

The evidence therefore supports difficulty with distributed and late evidence in the studied long-document benchmarks, not a production-email accuracy estimate.

## Grounding correctness and answer correctness are different measurements

Hi-VT5 reports cases in which an answer is correct while its predicted supporting page is wrong, suggesting that answer correctness alone can conceal weak evidence localization [2212.05935]. RefChartQA reports the reverse failure mode: a model can localize the correct chart elements yet still compute the wrong answer [2503.23131].

RefChartQA additionally shows that explicit grounding instruction tuning is not uniformly beneficial to answering. Some evaluated models gain substantially, while UniChart, ChartGemma, and some Qwen2.5-VL configurations lose answer accuracy on reported splits [2503.23131].

## Reading order is a separate structural failure mode

The handwritten-document reading-order study reports large improvements from hierarchical region-then-line processing on OHG and FCR, but its heterogeneous ABP collection remains inadequate for practical full reading-order recovery [doi-10-1007-s00521-022-06948-5]. The same study shows that the hierarchical approach depends on accurate upstream layout segmentation, so layout errors can propagate into ordering errors [doi-10-1007-s00521-022-06948-5].

## Flattened text is useful but can discard multimodal evidence

MMLongBench-Doc finds OCR-based LLM pipelines competitive on text and table questions but comparatively weak on chart- and image-dependent questions [2407.01523]. LongDocURL separately shows that retaining table structure inside parsed text materially improves downstream QA relative to plain PyMuPDF text [2412.18424].

The evidence therefore distinguishes useful text extraction from preservation of all document information.

# Contradictions

## Utility of added visual features

There is a clear cross-paper tension over whether additional visual representations improve results.

DocFormer reports that combining image, text, and spatial information improves entity extraction relative to text-plus-spatial variants on its form and receipt/document benchmarks [2106.11539]. InfographicVQA, however, reports that generic detected-object regions were unhelpful for M4C and that adding visual features to OCR tokens did not improve its LayoutLM-based model [2104.12756]. MMLongBench-Doc further reports that most evaluated LVLMs performed worse than LLM counterparts given OCR-parsed text, although GPT-4o and GPT-4V were exceptions [2407.01523].

These results come from different tasks, domains, architectures, and visual representations. They therefore contradict a universal claim that adding visual features necessarily improves document understanding; they do not invalidate each paper's task-specific measurements.

## Effect of explicit grounding training on answer accuracy

RefChartQA itself contains both sides of this result. Grounding instruction tuning substantially increases answer accuracy for some TinyChart and Qwen configurations, but decreases accuracy for UniChart, ChartGemma, and some Qwen2.5-VL configurations [2503.23131]. The admitted evidence therefore does not support a model-independent claim that grounding supervision always improves answer accuracy.

# Open Gaps

### G1 — Attachment-version lineage
**Classification:** ACADEMIC  
**Priority:** HIGH

The corpus does not establish methods for maintaining evidence provenance across successive attachment revisions: stable attachment identity, version-relative locations, semantic changes between versions, or correspondence between an older cited region and its later revision. Multi-page, chart-grounding, and pixel-grounding systems explicitly stop short of version lineage [2212.05935] [2407.01523] [2503.23131] [manual-0661fc0cba].

Suggested query: `"document version comparison" multimodal provenance semantic change region grounding attachment revision`

### G2 — Cross-modal references from workplace messages into documents
**Classification:** ACADEMIC  
**Priority:** HIGH

The corpus does not directly evaluate workplace references such as “this screenshot”, “the highlighted row”, or “numbers below” where language in a message must be grounded into an attachment, table cell, or document region. Scene-text referring-expression comprehension provides adjacent-domain evidence for connecting language with textual image regions, but it concerns natural scenes rather than document attachments [manual-1048d6caf2]. RefChartQA and M3Grounder provide grounded visual/document QA mechanisms but do not test email-to-attachment reference resolution [2503.23131] [manual-0661fc0cba].

Suggested query: `"multimodal coreference" document attachment visual grounding referring expression email table screenshot`

### G3 — Full spreadsheet/workbook semantics
**Classification:** ACADEMIC  
**Priority:** HIGH

The admitted table literature does not establish understanding of complete spreadsheet workbooks containing formulas, hidden sheets or rows, cross-sheet references, merged regions, formatting semantics, named ranges, and workbook-level relationships. TURL excludes rows with merged columns, TUTA operates on already structured tables, and TAPAS addresses a single table at a time [2006.14806] [2010.12537] [doi-10-18653-v1-2020-acl-main-398].

Suggested query: `"spreadsheet understanding" formulas merged cells multi-sheet semantic workbook grounding`

### G4 — Unified fine-grained provenance hierarchy
**Classification:** ACADEMIC  
**Priority:** HIGH

No admitted paper validates an end-to-end provenance representation simultaneously identifying attachment version, page, document element, exact region or table cell, and associated answer span. The corpus instead validates page grounding [2212.05935], chart boxes [2503.23131], pixel masks [manual-0661fc0cba], and selected table cells [doi-10-18653-v1-2020-acl-main-398] separately.

Suggested query: `"document evidence grounding" provenance page region cell span multimodal citation localization`

### G5 — Explicit unsupported/incomplete extraction states
**Classification:** ENGINEERING  
**Priority:** HIGH

MMLongBench-Doc includes unanswerable questions [2407.01523], while DocFormer, complex-table recognition, and reading-order work expose dependencies on OCR, detection, or layout stages [2106.11539] [2111.07129] [doi-10-1007-s00521-022-06948-5]. The corpus does not supply an end-to-end contract distinguishing genuine absence of evidence from OCR, parser, layout, or grounding failure. This can be investigated through controlled parser and pipeline benchmarks.

### G6 — Robustness on heterogeneous workplace documents
**Classification:** ENGINEERING  
**Priority:** HIGH

The admitted studies expose concrete failure classes that can be exercised experimentally: sparse tables [2111.07129], heterogeneous reading order [doi-10-1007-s00521-022-06948-5], OCR/spatial-input dependence [2106.11539], and perceptual/document-element failures [2412.18424]. Candidate extraction pipelines can therefore be benchmarked against deliberately varied fixtures without claiming those fixtures represent a production mailbox.

### G7 — Scaling with long documents and large structures
**Classification:** ENGINEERING  
**Priority:** MEDIUM

The corpus reports quadratic table-relation inference in one table system [2111.07129], increasing training-memory pressure and information loss under page compression in Hi-VT5 [2212.05935], and input cut-off or merge strategies for models unable to consume full LongDocURL documents [2412.18424]. Operational limits for candidate implementations remain an engineering question.

### G8 — Integrated preservation and provenance evaluation
**Classification:** ENGINEERING  
**Priority:** HIGH

No benchmark here simultaneously measures semantic correctness, extraction completeness, exact provenance, unsupported-evidence handling, and preservation of tables, images, and reading order for workplace-style attachments. Existing benchmarks measure important subsets of those dimensions [2407.01523] [2412.18424] [2503.23131] [2111.07129]. An integrated engineering benchmark can test candidate implementations without treating synthetic or transfer data as production-domain evidence.

### G9 — Response scope after grounding
**Classification:** OUT_OF_SCOPE  
**Priority:** MEDIUM

Determining which textual proposition a grounded table, screenshot, cell, page, or attachment reference applies to is outside Topic 08's project boundary once the object itself has been grounded. This is a project ownership decision, not a literature finding.

### G10 — Action semantics after grounding
**Classification:** OUT_OF_SCOPE  
**Priority:** MEDIUM

Determining what action, request, commitment, or decision is expressed by already grounded attachment content is outside Topic 08's project boundary. This is a project ownership decision, not a literature finding.

No prior-gap list was supplied for this synthesis round, so `gap_status` is empty.

# Actionable Insights

- **Synthesis-derived recommendation:** preserve native structural outputs alongside extracted text, including page identity, cell grids, bounding boxes or masks, reading-order relations, headers, units, and span relationships, instead of allowing text serialization to become the only retained representation.
- **Synthesis-derived recommendation:** represent evidence location as a typed hierarchy capable of expressing attachment identity, attachment version, page, document element, region, table cell, and text span, while permitting some levels to be unavailable when a source format cannot supply them.
- **Synthesis-derived recommendation:** keep extraction, structural interpretation, evidence grounding, and downstream semantic judgement as distinguishable stages so that a correct answer cannot conceal a wrong source location and a correct source location cannot conceal failed reasoning.
- **Synthesis-derived recommendation:** evaluate answer or semantic correctness separately from provenance correctness, and include cases where requested evidence is absent, unsupported, or only partially parsed.
- **Synthesis-derived recommendation:** benchmark structured-text and image-based pathways by document type rather than assuming either OCR-text flattening or full visual processing is uniformly superior.
- **Synthesis-derived recommendation:** construct adversarial engineering fixtures for merged cells, sparse tables, ambiguous headers, units, late pages, cross-page evidence, charts, scanned pages, OCR corruption, wrong attachment versions, and unsupported embedded objects.
- **Synthesis-derived recommendation:** preserve parser and grounding failures as explicit states with lineage to the affected source object rather than representing failed or unsupported regions as empty successful extraction.
- **Synthesis-derived recommendation:** assign stable attachment and version identities outside model-generated descriptions so that later grounding records can reference immutable source artifacts even when semantic interpretation is recomputed.

# Confidence Summary

Confidence is **HIGH** for the broad evidence that document structure, layout, table organization, and evidence location affect measured understanding performance, because multiple full-text papers provide datasets, ablations, and task-specific results [2006.14806] [2010.12537] [2106.11539] [2412.18424]. Confidence is also **HIGH** that multi-page and cross-page evidence remains difficult [2212.05935] [2407.01523] [2412.18424], and that answer correctness should not be treated as evidence-location correctness [2212.05935] [2503.23131].

Confidence is **MEDIUM** for fine-grained pixel-mask grounding because M3Grounder was available only at abstract/project-page level [manual-0661fc0cba], and **MEDIUM** for transfer from scene-text referring expressions because that evidence comes from natural scenes rather than workplace documents [manual-1048d6caf2]. Confidence is **LOW** for production-email attachment versioning and cross-message visual references because this corpus contains little or no direct target-domain evaluation.

Overall, the corpus supports well-supported design principles and candidate evaluation dimensions, not production accuracy claims or a validated unified architecture.

# Limitations

- The corpus is heterogeneous: it includes Wikipedia and web tables, scientific PDF tables, annual-report tables, forms, receipts, contracts, infographics, charts, handwritten documents, long PDFs, and natural-scene referring expressions. Results from these domains are transfer evidence unless the target document type matches.
- No admitted study directly evaluates complete email threads in which message text refers to cells, screenshots, pages, or successively revised workplace attachments.
- Attachment identity and longitudinal attachment-version lineage are not modeled in the evaluated systems, so the corpus cannot close that problem.
- No single benchmark jointly evaluates extraction completeness, reading order, table semantics, multimodal reference resolution, multi-page reasoning, exact sub-page provenance, and attachment versions.
- Several systems depend on OCR, table detection, or layout analysis performed upstream; downstream results do not imply robustness to failures in those upstream stages [2106.11539] [2111.07129] [doi-10-1007-s00521-022-06948-5].
- The M3Grounder analysis is based on abstract and official project material rather than independently verified full text [manual-0661fc0cba].
- The Scene-Text Oriented Referring Expression Comprehension analysis is also abstract-level, and its natural-scene evidence is transfer evidence rather than direct evidence for workplace documents [manual-1048d6caf2].
- The inherited Topic 04 and Topic 05 handoffs were used only to define scope and ownership boundaries. None of their claims were used as evidence for findings or corpus-derived gaps.
- No prior-gap list was supplied with this synthesis task, so no earlier gap can legitimately be marked resolved or open in `gap_status`.
