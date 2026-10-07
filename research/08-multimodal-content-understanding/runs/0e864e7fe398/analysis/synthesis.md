# Cross-Paper Synthesis

## Executive Summary

The corpus provides substantial evidence for several components of multimodal document grounding but not for their full cross-version combination. Layout-aware and structure-aware representations improve document and table understanding; hierarchical page, region, cell, and answer evidence can be localized; and explicit attribution exposes failures hidden by answer-only metrics. Long, cross-page, cross-modal documents and realistic workbooks remain difficult. Separate literatures demonstrate version-aware retrieval, cross-version PDF element alignment, persistent XML node identity, and fine-grained spreadsheet provenance, but none jointly validates stable attachment identity, semantic revision lineage, and answer-level evidence across workplace attachment versions. Referring-expression work establishes useful adjacent-domain mechanisms, not direct email-to-attachment grounding. All eight prior gaps therefore remain open: four require additional direct academic evidence and four require engineering evaluation or contracts.

The corpus contains 38 analysis records representing 37 distinct papers because [manual-1048d6caf2] and [doi-10-1109-tmm-2022-3219642] are duplicate records of the same Scene-Text Oriented Referring Expression Comprehension study.

## Themes

1. **Layout and document structure are empirically consequential.** Spatial, hierarchical, and structure-aware representations improve evaluated document and table tasks compared with weaker text-only or less-structured variants [2106.11539] [2010.12537] [2401.00908] [2412.18424].

2. **Evidence is increasingly represented hierarchically.** The corpus contains document/page/region bounding boxes [2605.12882], page-to-region routing [2607.29638], element evidence graphs [2608.03292], phrase/line/block masks linked to answer spans [manual-0661fc0cba], and selected supporting cells [doi-10-18653-v1-2020-acl-main-398]. These papers validate different subsets, not one combined hierarchy.

3. **Correct answers and correct evidence are different outcomes.** Hi-VT5 can answer correctly while identifying the wrong evidence page [2212.05935]. RefChartQA reports cases of correct visual localization followed by incorrect reasoning [2503.23131]. CiteVQA reports lower strict attributed accuracy than answer-only scores [2605.12882]. DocTrace shows that masking cited evidence frequently changes answers while explicitly cautioning that this does not prove that the internal reasoning process follows the visible evidence graph [2608.03292].

4. **Distributed evidence remains difficult.** Models perform worse when evidence spans pages, images, or modalities in MMLongBench-Doc [2407.01523], LongDocURL [2412.18424], and MMDocRAG [2505.16470]. Graph-based evidence expansion improves cross-page results in MAGE-RAG but does not eliminate the difficulty [2606.15906].

5. **Tables require more than extracted strings.** PubTabNet evaluates complete table-tree structure and content [1911.10683]. Complex-table recognition benefits from explicit cell geometry and spanning relations [2111.07129] [2203.09056]. Business-table QA explicitly models hierarchical relationships [manual-7fdf40b3c6]. LongDocURL reports substantially better QA when table structure is preserved during parsing [2412.18424].

6. **Workbook-scale spreadsheet understanding is materially harder than isolated table QA.** Multi-granular row, column, window, and image retrieval improves FRTR-Bench results [2601.08741]. Structured extraction and verification improve SpreadsheetAgent results [2604.12282]. SpreadsheetBench 2 shows that high cell-modification accuracy can coexist with much lower complete-task accuracy and identifies insufficient workbook inspection and wrong-cell selection as major failures [2606.29955].

7. **Versioning literature covers complementary components rather than one end-to-end solution.** VersionRAG improves explicit version-sensitive retrieval but finds change questions harder [2510.08109]. Scientific-PDF differencing demonstrates cross-version alignment across text, tables, formulas, and figures [2607.14117]. XML work demonstrates semantic matching despite restructuring [doi-10-1007-978-3-540-30480-7-29] and persistent logical node identities across snapshots [manual-ae200642f8]. None of these experiments jointly evaluates the full workplace attachment problem.

8. **Language-to-visual-object grounding is demonstrated in adjacent domains.** Scene-text-oriented referring-expression comprehension links expression-relevant visible text to regions [doi-10-1109-tmm-2022-3219642]. Joint textual and multimodal reference modeling improves pronoun grounding in visually grounded dialogue [doi-10-18653-v1-2025-acl-long-547]. Neither study evaluates email language referring to cells, attachment versions, screenshots, or document regions.

9. **Reading order is both a reconstruction target and a structural signal.** Learned hierarchical decoding produces strong results on some handwritten-document collections but remains inadequate on the heterogeneous ABP collection [doi-10-1007-s00521-022-06948-5]. Separately, LLM-inferred reading-order relations can disagree strongly with adjacency-oriented human labels while improving downstream extraction and QA [doi-10-18653-v1-2026-eacl-long-192].

10. **Evaluation is moving beyond answer strings.** CiteVQA jointly evaluates answer and regional support [2605.12882]; SMuDGE incorporates groundedness and calibration [doi-10-18653-v1-2025-findings-naacl-295]; RefChartQA evaluates answer-linked chart regions [2503.23131]; and DocTrace evaluates structural validity and counterfactual dependence of traces [2608.03292].

## Findings

### 1. Structural and spatial information improves evaluated document understanding

Across document- and table-understanding benchmarks, adding spatial, layout, hierarchical, or explicitly structured representations improves downstream performance relative to weaker text-only or less-structured variants. DocFormer reports gains from spatial and multimodal features [2106.11539]; TUTA reports benefits from tree-based attention and tree-position embeddings [2010.12537]; DocLLM reports higher pretraining accuracy from spatial interactions [2401.00908]; and LongDocURL reports substantial QA improvements from structure-preserving document parsing [2412.18424].

**Confidence: HIGH.**

### 2. Fine-grained evidence provenance is feasible within individual document states

Different papers demonstrate provenance at document, page, region, element, quotation, cell, or answer-span granularity. CiteVQA uses document index, page index, and element bounding boxes [2605.12882]. HierDoc preserves page-to-region metadata [2607.29638]. DocTrace represents evidence with hierarchical element graphs [2608.03292]. M3Grounder links individual generated answer spans to phrase-, line-, or block-level pixel masks [manual-0661fc0cba]. TAPAS explicitly selects answer-supporting table cells [doi-10-18653-v1-2020-acl-main-398].

These studies cover different subsets of the hierarchy; they do not jointly validate one combined identifier scheme.

**Confidence: HIGH.**

### 3. Answer accuracy cannot substitute for evidence-attribution accuracy

The corpus repeatedly separates these outcomes. Hi-VT5 reports correct answers associated with incorrect predicted answer pages [2212.05935]. RefChartQA reports correct region selection followed by incorrect mathematical reasoning [2503.23131]. CiteVQA reports a substantial difference between answer scores and Strict Attributed Accuracy [2605.12882]. DocTrace reports behavioral dependence on cited evidence under counterfactual masking but explicitly does not treat that test as proof that hidden model computation follows the visible graph [2608.03292].

**Confidence: HIGH.**

### 4. Cross-page and cross-modal evidence composition remains difficult

MMLongBench-Doc reports lower performance on cross-page questions [2407.01523]. LongDocURL contains extensive multi-page and multi-element evidence and retains a large human-model gap [2412.18424]. MMDocRAG reports lower performance on multi-page and multi-image cases even when evidence candidates are supplied [2505.16470]. MAGE-RAG improves cross-page performance through graph-neighbor expansion, but its reported scores still leave substantial remaining error [2606.15906].

**Confidence: HIGH.**

### 5. Explicit table structure supports recognition and reasoning

PubTabNet and TEDS evaluate tree structure and content rather than only character strings [1911.10683]. Complex-table recognition benefits from explicit geometry and spanning relationships [2111.07129] [2203.09056]. TRH2TQA explicitly recovers hierarchical business-table relationships before QA [manual-7fdf40b3c6]. LongDocURL reports lower QA quality when the parser loses table structure [2412.18424].

**Confidence: HIGH.**

### 6. Spreadsheet structure, retrieval granularity, and verification affect workbook QA, while complete workflow success remains low

FRTR reports higher accuracy from combined row, column, window, and image evidence units than from individual unit types on FRTR-Bench [2601.08741]. SpreadsheetAgent reports improvements from explicit structural sketches and verification [2604.12282]. SpreadsheetBench 2 reports that high cell-level modification scores do not imply complete workbook-task correctness and identifies workbook inspection and target-cell selection as major failure sources [2606.29955].

**Confidence: HIGH.**

### 7. Version-aware retrieval and cross-version matching are demonstrated separately

VersionRAG reports large improvements over its version-agnostic baselines for version-sensitive questions while change-oriented questions remain harder [2510.08109]. A scientific-document differencing method shows that explicit cross-version alignment materially improves change detection and element matching across text, tables, formulas, and figures [2607.14117]. XML research demonstrates semantic element matching despite structural reorganization [doi-10-1007-978-3-540-30480-7-29] and persistent logical element identity across snapshots [manual-ae200642f8].

These are complementary results from technical documentation, scientific PDFs, and XML version stores. Their combination into one multimodal attachment-lineage scheme is untested.

**Confidence: HIGH.**

### 8. The corpus does not validate complete longitudinal provenance for revised workplace attachments

The closest papers separately address explicit version identity [2510.08109], heterogeneous cross-version alignment [2607.14117], within-workbook cell and sheet provenance [2601.08741], and document/page/region evidence addresses [2605.12882]. None of the admitted studies experimentally combines stable attachment identity, version-relative source location, semantic revision interpretation, persistent element lineage, and answer-level grounding for successive workplace attachment revisions.

**Confidence: HIGH.**

### 9. Adjacent-domain reference-grounding methods do not constitute direct workplace-message evidence

Scene-Text Oriented Referring Expression Comprehension demonstrates language-to-region grounding using visible scene text [doi-10-1109-tmm-2022-3219642]. Joint textual/multimodal relation modeling improves pronoun grounding in visually grounded dialogue [doi-10-18653-v1-2025-acl-long-547]. These experiments do not test messages such as “the highlighted row”, “this screenshot”, or “use attachment v2” against workplace attachments.

**Confidence: HIGH.**

### 10. Reading-order success depends on both domain and evaluation objective

Hierarchical learned ordering substantially improves several handwritten-document collections but remains inadequate on the heterogeneous ABP collection [doi-10-1007-s00521-022-06948-5]. The EACL study finds that LLM-generated global reading-order relations have low agreement with adjacency-oriented human labels while nevertheless improving several downstream document-understanding tasks [doi-10-18653-v1-2026-eacl-long-192].

**Confidence: HIGH.**

## Contradictions

### Grounding training does not uniformly improve answer accuracy

RefChartQA reports large accuracy gains from grounding instruction tuning for some backbones, including TinyChart and Qwen-VL-Chat, but accuracy decreases for other backbones and splits, including UniChart on all three reported splits and ChartGemma and Qwen2.5-VL in several settings [2503.23131]. The study therefore contradicts any universal claim that explicit grounding supervision necessarily increases answer accuracy.

### OCR-centric and richer visual representations show benchmark-dependent results

MMLongBench-Doc reports that most evaluated LVLMs perform worse than LLM pipelines supplied with OCR text, with GPT-4o and GPT-4V as exceptions [2407.01523]. In contrast, MMDocRAG reports better aggregate results from detailed VLM-generated visual descriptions than from OCR alone [2505.16470], while LongDocURL reports substantial benefits from structure-preserving parsing relative to plain PyMuPDF text [2412.18424]. These experiments use different systems and tasks and do not support one universally superior representation.

### Reading-order label agreement and downstream utility are not equivalent objectives

The handwritten-document study evaluates recovery of a target sequence and shows degradation on heterogeneous layouts [doi-10-1007-s00521-022-06948-5]. The EACL study reports that LLM-derived relations score poorly against adjacency-oriented labels yet improve downstream extraction and QA [doi-10-18653-v1-2026-eacl-long-192]. The results use different definitions of useful reading order and should not be silently averaged into one metric.

### Spreadsheet retrieval results depend on the benchmark

FRTR substantially outperforms the authors' SpreadsheetLLM adaptation on FRTR-Bench, but on the SpreadsheetLLM benchmark the strongest SpreadsheetLLM result remains slightly higher than FRTR [2601.08741]. The evidence does not establish benchmark-independent superiority for either retrieval-first or fuller-context approaches.

### Evidence-output interfaces produce different results under different supervision regimes

For six general open VLMs, textual evidence quotations produce much higher evidence recall and lower hallucination than direct bounding-box generation [2607.24651]. M3Grounder, using a dedicated grounding architecture and region-supervised data, reports strong pixel-mask grounding [manual-0661fc0cba]. The studies do not directly replicate one another. They contradict only a broad claim that coordinate-like spatial generation is intrinsically either ineffective or sufficient regardless of model and supervision.

## Open Gaps

### gap-1 — ACADEMIC — HIGH

The corpus still does not establish a complete method for maintaining evidence provenance across successive workplace attachment revisions, including stable attachment identity, version-relative source locations, semantic changes, and lineage from an older cited region to its later counterpart.

VersionRAG covers version-aware retrieval [2510.08109]; cross-version scientific-document alignment covers heterogeneous element matching [2607.14117]; and XML research covers semantic or persistent logical identities [doi-10-1007-978-3-540-30480-7-29] [manual-ae200642f8]. No admitted study validates the complete combined problem.

**Status: open.**

Suggested query: `"document version alignment" multimodal provenance region lineage semantic change revised documents workplace attachments`

### gap-2 — ACADEMIC — HIGH

Direct grounding of workplace-message language such as “this screenshot”, “the highlighted row”, “numbers below”, or “use attachment v2” into attachment objects, pages, cells, or document regions remains unvalidated.

Scene-text referring-expression comprehension [doi-10-1109-tmm-2022-3219642] and visually grounded dialogue [doi-10-18653-v1-2025-acl-long-547] provide adjacent-domain mechanisms but not email-to-attachment evaluation.

**Status: open.**

Suggested query: `"referring expression grounding" document multimodal email attachment table cell screenshot coreference workplace`

### gap-3 — ACADEMIC — HIGH

Comprehensive spreadsheet understanding remains open for formulas, hidden rows or sheets, cross-sheet references, merged regions, formatting semantics, units, named ranges, and provenance across revised workbook versions.

FRTR covers fine-grained retrieval and within-workbook provenance [2601.08741], SpreadsheetAgent covers structure reconstruction and verification [2604.12282], and SpreadsheetBench 2 covers realistic multi-sheet workflows [2606.29955]. The complete requested semantic and longitudinal set is not established.

**Status: open.**

Suggested query: `"spreadsheet understanding" workbook formulas hidden sheets named ranges merged cells cross-sheet provenance version revisions`

### gap-4 — ACADEMIC — HIGH

No admitted paper validates an end-to-end provenance representation jointly identifying attachment version, page, document element, exact region or spreadsheet cell, and answer span.

CiteVQA provides document-page-box addresses [2605.12882]; HierDoc provides page-to-region evidence [2607.29638]; DocTrace provides hierarchical evidence graphs [2608.03292]; M3Grounder links answer spans to masks [manual-0661fc0cba]; TAPAS identifies supporting cells [doi-10-18653-v1-2020-acl-main-398]; and FRTR preserves sheet and cell references [2601.08741]. Their combination remains untested.

**Status: open.**

Suggested query: `"evidence provenance" document question answering version page region cell answer span hierarchical multimodal grounding`

### gap-5 — ENGINEERING — HIGH

End-to-end behavior when extraction or grounding is unsupported, incomplete, or wrong remains insufficiently exercised. The corpus contains unanswerable-case evaluation [2511.12003], attribution hallucination and parser-assignment failures [2607.24651], parser/evidence-graph limitations [2606.15906], and joint answer-attribution scoring [2605.12882], but no complete engineering contract distinguishing genuine absence from parser, OCR, layout, retrieval, or grounding failure.

**Status: open.**

### gap-6 — ENGINEERING — HIGH

Robustness of extraction and structural-preservation pipelines on heterogeneous workplace-style documents remains open. Individual papers test complex and empty-cell tables [2111.07129], distorted tables [2203.09056], heterogeneous reading order [doi-10-1007-s00521-022-06948-5], multimodal long documents [2407.01523], and realistic workbooks [2606.29955]. No admitted benchmark jointly exercises the requested failure surface.

**Status: open.**

### gap-7 — ENGINEERING — MEDIUM

Operational scaling remains open for long documents, large tables, and realistic workbooks. VersionRAG reports efficiency differences among retrieval strategies [2510.08109]. MAGE-RAG identifies parsing quality and controller overhead [2606.15906]. SpreadsheetBench 2 exposes large workbook workloads [2606.29955]. XML differencing demonstrates quality/speed trade-offs [doi-10-1002-spe-2305]. These results do not close target-workload latency, memory, and throughput evaluation.

**Status: open.**

### gap-8 — ENGINEERING — HIGH

No admitted evaluation simultaneously scores semantic correctness, extraction completeness, exact provenance, unsupported-evidence handling, table/image preservation, and reading-order preservation on workplace-style attachments.

CiteVQA evaluates answer plus evidence support [2605.12882]; SMuDGE evaluates groundedness and calibration [doi-10-18653-v1-2025-findings-naacl-295]; long-document benchmarks evaluate multimodal evidence localization [2407.01523] [2412.18424]; PubTabNet evaluates table structure and content [1911.10683]; and SpreadsheetBench 2 evaluates workbook workflows [2606.29955]. These are overlapping subsets, not one complete evaluation.

**Status: open.**

## Actionable Insights

- **Synthesis-derived recommendation:** represent document evidence with composable identifiers whose levels can include attachment identity, version, page or sheet, structural element, exact region or cell, and answer span, while permitting levels to be absent when the source format does not provide them.
- **Synthesis-derived recommendation:** keep persistent cross-version identity separate from version-relative coordinates or cell addresses, because logical identity and physical location are different concepts.
- **Synthesis-derived recommendation:** represent cross-version correspondence as an explicit relation carrying confidence and change metadata rather than overwriting an older evidence locator with its newest counterpart.
- **Synthesis-derived recommendation:** score answer correctness and evidence correctness independently and add a strict joint metric so correct answers supported by incorrect evidence remain visible.
- **Synthesis-derived recommendation:** preserve structured table and workbook representations alongside OCR or rendered text rather than relying on flattened text as the sole semantic representation.
- **Synthesis-derived recommendation:** distinguish successful no-evidence results from parser failure, OCR failure, unsupported embedded content, retrieval failure, and grounding failure through explicit failure states.
- **Synthesis-derived recommendation:** create an engineering fixture suite covering versioned PDFs, spreadsheets, screenshots, scanned pages, merged and hierarchical tables, hidden workbook structures, relocated elements, repeated labels, OCR corruption, and ambiguous referring expressions before closing the engineering gaps.
- **Synthesis-derived recommendation:** evaluate message-to-attachment referring expressions as a separate problem rather than assuming transfer from scene-text referring-expression comprehension or visually grounded dialogue.
- **Synthesis-derived recommendation:** preserve both local evidence and surrounding page, sheet, table, or section context in evaluation fixtures so precise localization can be tested without discarding structural context.
- **Synthesis-derived recommendation:** treat the integration of version lineage, multimodal grounding, spreadsheet provenance, and answer-span attribution as an unvalidated composition until an end-to-end benchmark directly evaluates that combination.

## Confidence Summary

Confidence is **high** in the recurring evidence-supported principles within the evaluated domains: spatial and structural representations matter; evidence attribution is distinct from answer accuracy; hierarchical localization can expose provenance; multi-page and cross-modal reasoning remains difficult; and explicit version or alignment representations improve version-sensitive tasks in their respective benchmarks.

Confidence is **medium** for transfer to longitudinal workplace attachments. Much of the evidence comes from scientific PDFs, web tables, infographics, visual scenes, clinical guidelines, XML histories, benchmark workbooks, and document-QA corpora rather than workplace communication. These papers provide well-supported design principles and candidate mechanisms, but the corpus does not directly validate the combined cross-version workplace scheme posed by this topic.

## Limitations

- The supplied source material consists of per-paper analysis summaries rather than full-paper text, so the synthesis is constrained to the reported research questions and key findings.
- [manual-1048d6caf2] and [doi-10-1109-tmm-2022-3219642] are two records of the same Scene-Text Oriented Referring Expression Comprehension study. They are counted once, giving 37 distinct papers from 38 analyses.
- The evidence spans heterogeneous domains including web tables, scientific PDFs, infographics, document QA, scene images, visually grounded dialogue, clinical guidelines, XML histories, and spreadsheet benchmarks. Transfer from those domains does not demonstrate production accuracy on workplace email attachments.
- Different studies validate individual provenance levels or versioning mechanisms, but none experimentally validates their combination into a stable version-to-page-to-region-or-cell-to-answer-span lineage.
- The inherited Topic 04 and Topic 05 handoffs are treated only as project context. They are not evidence for any finding or gap-status decision in this synthesis.
- Models, datasets, metrics, input representations, and evaluation protocols differ substantially across the corpus, limiting direct numerical comparison between papers.
- Several apparent disagreements are conditional rather than direct replications, particularly OCR versus visual representations, grounding interfaces, reading-order definitions, and spreadsheet retrieval strategies.
- No admitted study provides authorized production-mailbox evidence, so production representativeness and target-workload accuracy remain unestablished.
