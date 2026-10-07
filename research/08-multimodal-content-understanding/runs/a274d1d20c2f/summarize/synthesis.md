# Executive Summary

Across 27 distinct papers represented by 28 analyses, the strongest evidence concerns structure-preserving document understanding, page and region evidence localization, table and spreadsheet structure, and version-aware retrieval or differencing in adjacent domains. Controlled ablations show benefits from spatial, hierarchical, and explicitly structured representations on several document and spreadsheet benchmarks. Fine-grained provenance has been demonstrated separately at page, bounding-box, mask, quotation-to-region, table-cell, passage, and answer-span levels. Version-aware retrieval and cross-version element alignment also improve their respective technical-documentation and scientific-PDF tasks. However, these components have not been jointly validated for revised workplace attachments. Multi-page questions remain harder than single-page questions in MMLongBench-Doc, while MMDocRAG reports lower performance on multi-page and multi-image questions. All eight prior gaps therefore remain open.

# Themes

1. **Structure preservation has experimentally demonstrated value on several specific tasks.** DocFormer ablations show gains from spatial features and multimodal attention; TUTA shows gains from tree-aware attention and tree-position embeddings; LongDocURL shows large downstream QA gains from structure-preserving parsed text relative to PyMuPDF text; SpreadsheetAgent improves with explicit structural sketches; and DocTrace loses accuracy when structured parsing is removed [2106.11539] [2010.12537] [2412.18424] [2604.12282] [2608.03292]. TAPAS preserves table row-column relationships and benefits from table-specific pretraining, but the supplied TAPAS analysis does not contain a direct ablation isolating row-column structure itself [doi-10-18653-v1-2020-acl-main-398].

2. **Table structure and table evidence can be preserved at different levels.** The complex-table recognition framework retains explicit cell boxes and rectilinear cell relationships and derives row and column spans [2111.07129]. TAPAS explicitly selects supporting cells before optional aggregation, giving within-table cell-level evidence localization [doi-10-18653-v1-2020-acl-main-398]. By contrast, the PubTabNet version described in the original EDD paper lacked individual cell coordinates even though the model achieved strong structure-recognition scores [1911.10683].

3. **Page-level localization is a measurable part of long-document QA rather than merely an implicit property of answering.** Hi-VT5 jointly predicts an answer and its evidence page and reports cases in which the answer is correct but the predicted page is wrong [2212.05935]. MMLongBench-Doc explicitly annotates evidence pages and reports declining performance when answer evidence appears later in a document [2407.01523]. DocTrace identifies page localization as a major remaining bottleneck, especially for multi-page questions, and improves substantially when gold evidence pages are supplied [2608.03292].

4. **Fine-grained grounding is feasible through several different interfaces, but the interfaces have been validated separately.** RefChartQA trains models to emit chart-element bounding boxes with answers [2503.23131]. LAT associates individual reasoning steps and final answers with page indices and bounding boxes [2511.12003]. The coordinate-free evidence-attribution study instead has VLMs emit textual quotations that an external layout parser and retriever map back to semantic regions [2607.24651]. M3Grounder links individual answer spans to phrase-, line-, and block-level segmentation masks [manual-0661fc0cba]. These studies do not jointly validate one combined grounding representation.

5. **Correct grounding and correct answering are not equivalent.** RefChartQA reports cases where a model localizes the correct chart evidence but performs the subsequent mathematical reasoning incorrectly [2503.23131]. Hi-VT5 reports correct answers with incorrect evidence-page predictions, which the authors use as a diagnostic for reliance on priors rather than the actual source page [2212.05935]. DocTrace's counterfactual masking shows that answers are behaviorally associated with cited evidence, but the authors explicitly state that this does not prove that the visible evidence graph is the model's internal causal reasoning program [2608.03292].

6. **The evidence for harder distributed cases should be stated narrowly.** MMLongBench-Doc reports that evaluated models perform worse on cross-page than single-page questions [2407.01523]. MMDocRAG separately reports lower performance on multi-page and multi-image questions than on corresponding simpler cases [2505.16470]. The supplied analyses do **not** establish a general empirical claim that cross-modal questions are harder than single-modality questions, so no such conclusion is drawn here.

7. **Workbook-level spreadsheet structure matters, but end-to-end workflow accuracy remains limited.** SpreadsheetAgent improves when explicit workbook structural sketches and a verification agent are retained, and stronger structure extraction improves downstream reasoning with the reasoner held fixed [2604.12282]. SpreadsheetBench 2 shows that high cell-level modification accuracy can coexist with much lower exact task accuracy and identifies insufficient workbook inspection and incorrect target-cell selection as major causes of failure [2606.29955].

8. **Version awareness and cross-version alignment both have direct experimental support, but in different adjacent domains.** VersionRAG explicitly retains document-version identity and substantially outperforms naive RAG and its evaluated GraphRAG baseline on a small technical-documentation benchmark, especially on version-specific queries [2510.08109]. In scientific-PDF differencing, removing cross-version element alignment substantially degrades detection, localization, alignment, and matching metrics [2607.14117]. These results demonstrate version-aware retrieval and element lineage in their respective domains, not complete provenance across revised workplace attachments.

9. **The corpus contains complementary provenance layers rather than one validated end-to-end provenance hierarchy.** SentryLine records source document, page, passage, citation key, and update status [2609.08364]. LAT records page-plus-box evidence for reasoning steps and the final answer [2511.12003]. TAPAS selects table cells [doi-10-18653-v1-2020-acl-main-398]. M3Grounder links generated answer spans to evidence masks [manual-0661fc0cba]. The scientific-document differencing system aligns typed document elements across versions [2607.14117]. No supplied study validates all of these levels together.

10. **Adjacent-domain referring-expression work demonstrates useful mechanisms, but not email-to-attachment grounding.** Scene-Text Oriented Referring Expression Comprehension explicitly connects referring language, relevant scene text, and localized visual regions [doi-10-1109-tmm-2022-3219642]. Joint modeling of textual reference relations and multimodal grounding substantially improves pronoun grounding in Japanese visually grounded dialogue [doi-10-18653-v1-2025-acl-long-547]. Neither experiment evaluates workplace-message phrases such as “this screenshot”, “highlighted row”, or “numbers below” against attachments or revised document regions.

# Contradictions

### Visual features do not have a universal effect

DocFormer reports that combining image, text, and spatial features improves document entity extraction and that multimodal self-attention adds further gains [2106.11539]. InfographicVQA, however, reports that adding visual features to OCR tokens did not improve its LayoutLM-based model and that M4C variants using detected object regions could underperform variants with no objects or one full-image feature [2104.12756]. These results come from different architectures and document domains, so the evidence supports task- and representation-dependent effects rather than a universal benefit from adding visual features.

### Grounding-oriented training does not universally improve answer accuracy

RefChartQA contains both sides of this comparison within one study. Grounding instruction tuning produces large answer-accuracy gains for TinyChart and some Qwen configurations, while UniChart loses accuracy on all three reported splits, ChartGemma loses substantially on two splits, and Qwen2.5-VL declines on two splits [2503.23131]. A universal “grounding improves answers” claim is therefore contradicted by the paper's own results.

### Direct coordinate generation and alternative attribution interfaces show different behavior

For six evaluated open VLMs on a verified CiteVQA subset, direct coordinate generation produces very low evidence recall and high attribution hallucination, while textual evidence quotations followed by downstream region assignment perform substantially better [2607.24651]. In contrast, LAT reports strong page-plus-box attribution after dedicated supervised and reinforcement learning [2511.12003], and M3Grounder reports strong mask-based grounding after specialized grounding training [manual-0661fc0cba]. Because the datasets and training regimes differ, this is not evidence that one representation universally dominates; it shows that grounding-interface performance is setup-dependent.

### OCR/text and direct visual representations have non-uniform advantages

MMLongBench-Doc reports that most evaluated LVLMs perform worse overall than LLM counterparts given OCR-derived text, although OCR-based systems are comparatively weak on chart- and image-dependent questions [2407.01523]. MMDocRAG separately reports that detailed VLM-generated descriptions of visual evidence outperform OCR-only text in its aggregate comparison [2505.16470]. The evidence therefore varies with evidence type, representation, and model.

### Hierarchical compression helps scalability but discards information

Hi-VT5 performs better than evaluated realistic multi-page baselines and is less affected by evidence appearing late in a document, but its compressed page representation performs worse than T5 with the full answer page when an oracle supplies the relevant page [2212.05935]. The same study therefore demonstrates both the advantage and the information cost of page compression.

# Open Gaps

### gap-1 — ACADEMIC — HIGH

The corpus still does not establish a complete method for maintaining evidence provenance across successive workplace attachment revisions, including stable attachment identity, version-relative source locations, semantic changes between versions, and lineage from an older cited region to its later counterpart. VersionRAG covers explicit version-aware retrieval in technical documentation [2510.08109], and cross-version element alignment is demonstrated for scientific PDFs [2607.14117], but neither validates the complete attachment-revision provenance problem.

Suggested query: `"document version comparison" multimodal provenance semantic change region grounding attachment revision`

**Status: open.**

### gap-2 — ACADEMIC — HIGH

Direct grounding of workplace-message language such as “this screenshot”, “the highlighted row”, or “numbers below” into an attachment, cell, page element, or document region remains unvalidated. Scene-text referring-expression comprehension [doi-10-1109-tmm-2022-3219642] and visually grounded dialogue [doi-10-18653-v1-2025-acl-long-547] provide adjacent-domain evidence only.

Suggested query: `"multimodal coreference" document attachment visual grounding referring expression email table screenshot`

**Status: open.**

### gap-3 — ACADEMIC — HIGH

Spreadsheet understanding beyond isolated tables remains open. SpreadsheetAgent covers workbook-structure extraction, verification, and reasoning [2604.12282], while SpreadsheetBench 2 exercises large multi-sheet business workflows [2606.29955]. The corpus still does not establish comprehensive handling of formulas, hidden rows or sheets, cross-sheet references, merged regions, formatting semantics, units, named ranges, and provenance across revised workbook versions.

Suggested query: `"spreadsheet understanding" formulas merged cells multi-sheet semantic workbook grounding`

**Status: open.**

### gap-4 — ACADEMIC — HIGH

No admitted paper validates an end-to-end provenance representation that jointly identifies attachment version, page, document element, exact region or cell, and answer span. Individual studies validate different subsets, including cross-version elements [2607.14117], page-plus-box reasoning evidence [2511.12003], answer-span masks [manual-0661fc0cba], table cells [doi-10-18653-v1-2020-acl-main-398], and document/page/passage citations [2609.08364]. Their combination remains untested.

Suggested query: `"document evidence grounding" provenance page region cell span multimodal citation localization`

**Status: open.**

### gap-5 — ENGINEERING — HIGH

End-to-end behavior when extraction or grounding is unsupported, incomplete, or wrong remains insufficiently exercised. MMLongBench-Doc includes unanswerable cases [2407.01523], the quotation-to-region method exposes parser and assignment ceilings [2607.24651], DocTrace exposes localization failures [2608.03292], and table recognition remains dependent on upstream cell detection and OCR [2111.07129]. The corpus does not provide a complete engineering contract distinguishing successful absence from parser, OCR, layout, retrieval, or grounding failure.

**Status: open.**

### gap-6 — ENGINEERING — HIGH

Robustness of extraction and structure-preservation pipelines on heterogeneous workplace documents remains open. Individual studies expose sparse-table failures [2111.07129], difficult heterogeneous reading order [doi-10-1007-s00521-022-06948-5], table-size and coordinate limitations [1911.10683], and parser-coverage ceilings [2607.24651], but they do not jointly benchmark sparse tables, merged structures, OCR corruption, irregular reading order, embedded images, and scanned pages under one workplace-style suite.

**Status: open.**

### gap-7 — ENGINEERING — MEDIUM

Operational scaling remains open. The table-structure graph method has approximately quadratic pairwise inference cost [2111.07129]; Hi-VT5 exposes page-count memory pressure and compression loss [2212.05935]; LongDocURL often requires cut-off or merge strategies because models cannot consume complete long inputs [2412.18424]; and SpreadsheetAgent reports substantial extraction latency and repeated agent calls [2604.12282].

**Status: open.**

### gap-8 — ENGINEERING — HIGH

The corpus lacks one evaluation that simultaneously scores semantic correctness, extraction completeness, exact provenance, unsupported-evidence handling, and preservation of tables, images, and reading order on workplace-style attachments. SMuDGE evaluates groundedness and answer quality [doi-10-18653-v1-2025-findings-naacl-295], MMLongBench-Doc includes evidence pages and unanswerable cases [2407.01523], SpreadsheetBench 2 distinguishes local modifications from whole-workbook task correctness [2606.29955], and separate work evaluates table structure and reading order [2111.07129] [doi-10-1007-s00521-022-06948-5]. No admitted benchmark combines the complete set.

**Status: open.**

# Actionable Insights

- **Synthesis-derived recommendation:** represent provenance as explicit composable layers rather than one opaque citation string, so attachment identity/version, page, parsed element, region or cell, and answer span can be retained independently even when some layers are unavailable.

- **Synthesis-derived recommendation:** preserve extraction and grounding status separately from semantic absence, with explicit states for unsupported content, parser failure, OCR failure, layout failure, unresolved reference, and successful no-evidence results rather than collapsing them into an empty extraction.

- **Synthesis-derived recommendation:** build cross-version lineage as a distinct artifact from ordinary text diffing, allowing unchanged, modified, inserted, deleted, split, merged, and unresolved correspondences to remain explicit instead of assuming one-to-one continuity.

- **Synthesis-derived recommendation:** treat workbook understanding as a workbook-level problem rather than serializing only visible cell values; engineering evaluation should include formulas, hidden sheets or rows, merged regions, named ranges, formatting-derived semantics, units, and cross-sheet dependencies.

- **Synthesis-derived recommendation:** evaluate email-to-attachment referring expressions with dedicated workplace-style fixtures containing ambiguous phrases such as “this screenshot”, “highlighted row”, “numbers below”, and explicit attachment-version references, including no-valid-referent cases.

- **Synthesis-derived recommendation:** benchmark alternative grounding interfaces separately—direct coordinates, answer-linked boxes or masks, textual quotations plus downstream localization, and stable parser element IDs—because the literature does not establish a universally superior interface.

- **Synthesis-derived recommendation:** evaluate end-to-end correctness with both semantic-answer metrics and provenance metrics, and count failures caused by missing pages, wrong attachment versions, wrong table structure, wrong regions, and unsupported evidence separately.

- **Synthesis-derived recommendation:** include adversarial scaling cases such as late-page evidence, multi-page evidence, large or sparse tables, long workbooks, and structurally revised versions so that compression, truncation, retrieval, and alignment failures are visible before production deployment.

# Confidence Summary

The corpus provides well-supported design principles for preserving document structure, evaluating page or region grounding separately from answer correctness, retaining workbook-level structure, and modeling version identity or cross-version alignment in specific technical and scientific domains. Evidence is strongest where controlled ablations directly isolate structural parsing, page localization, verification, or cross-version alignment [2106.11539] [2010.12537] [2412.18424] [2604.12282] [2607.14117] [2608.03292].

Confidence is lower for transfer to natural workplace email and Teams attachments because most evaluations use document-QA, chart, scientific-publication, technical-documentation, clinical-guideline, spreadsheet, or visually grounded dialogue settings rather than real workplace communication. The 28 supplied analyses represent 27 distinct papers because [doi-10-1109-tmm-2022-3219642] and [manual-1048d6caf2] are duplicate analyses of the same Scene-Text Oriented Referring Expression Comprehension publication. No supplied study validates the full combined provenance hierarchy across attachment revisions.

# Limitations

- The corpus is dominated by document-QA, table, chart, spreadsheet, scientific-publication, technical-documentation, clinical-guideline, and visually grounded dialogue benchmarks rather than naturally occurring workplace email with repeatedly revised attachments.

- The 28 analyses correspond to 27 distinct papers. [doi-10-1109-tmm-2022-3219642] and [manual-1048d6caf2] describe the same underlying publication and were not treated as independent corroborating studies.

- Several records are available only at abstract or project-page level, including [doi-10-1109-tmm-2022-3219642]/[manual-1048d6caf2], [manual-0661fc0cba], and [manual-7fdf40b3c6], so detailed numerical results, ablations, or limitations cannot always be independently checked from full manuscripts.

- Cross-version evidence is concentrated mainly in technical-documentation retrieval [2510.08109] and scientific-PDF differencing [2607.14117]. These are direct results in their source domains, not production evidence for heterogeneous workplace attachments.

- Referring-expression evidence comes from natural-scene text grounding [doi-10-1109-tmm-2022-3219642] and Japanese visually grounded dialogue [doi-10-18653-v1-2025-acl-long-547]. It is transfer evidence for possible mechanisms, not direct evidence of email-to-attachment accuracy.

- Fine-grained provenance levels are validated separately across different tasks and datasets; combining attachment version, page, element, region or cell, and answer span into one scheme has not been experimentally validated by this corpus.

- Several newer evaluations use model-generated supervision, model-based answer extraction, or LLM judges, introducing evaluator or teacher-model dependence [2407.01523] [2412.18424] [2505.16470] [2510.08109] [2511.12003] [2608.03292].

- The inherited handoffs from earlier project Topics were treated solely as project context and were not used as evidence for findings, contradictions, or gap closure.
