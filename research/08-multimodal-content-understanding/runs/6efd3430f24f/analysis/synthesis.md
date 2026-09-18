# Executive Summary

Across 52 distinct studies, the corpus demonstrates strong but fragmented empirical support for document structure preservation, table and spreadsheet semantics, hierarchical evidence localization, multimodal referring-expression grounding, and several forms of version-aware provenance. Cross-version work includes spreadsheet-version clustering, persistent XML identities and reversible deltas, heterogeneous PDF element alignment, version-aware retrieval, and evolving-document QA with document/page/passage/update-status citations. Separately, document-QA studies show that page and region localization can materially affect answer quality and that correct answers can still carry incorrect or incomplete provenance. Spreadsheet studies preserve useful within-version cell, sheet, formula, and image locations but do not establish lineage across revised workbooks. Adjacent dialogue, GUI, and scene-text studies demonstrate useful reference-grounding mechanisms, but direct grounding of workplace-message references into versioned attachments remains unvalidated. All eight previously identified gaps therefore remain open.

# Themes

- **Cross-version identity and change tracking are demonstrated, but in separate representation families.** SpreadCluster recovers likely spreadsheet evolution groups from structural and textual similarity [1704.08476]. Persistent XML XIDs preserve logical node identity across snapshots and completed deltas support composition and inversion [manual-ae200642f8]. Scientific-PDF differencing aligns and compares text, tables, formulas, and figures across revisions [2607.14117]. VersionRAG explicitly represents document versions and inter-version changes [2510.08109]. SentryLine carries document, page, passage, citation-key, and update-status provenance for evolving clinical guidelines and reports temporal drift only where retrieved passages explicitly document it [2609.08364]. These studies cover different portions of the overall lineage problem rather than one jointly evaluated multimodal scheme.

- **Hierarchical provenance is increasingly treated as part of document understanding rather than an after-the-fact explanation.** Hi-VT5 jointly answers questions and identifies supporting pages [2212.05935]. HierDoc learns page selection followed by region routing [2607.29638]. DocTrace builds evidence graphs over localized multimodal elements [2608.03292]. CiteVQA evaluates document index, page index, and element bounding box together with answer correctness [2605.12882]. LAT jointly trains answering and visual evidence attribution [2511.12003].

- **Preserving structure or visual semantics often improves downstream understanding.** DocFormer gains from combining text, visual, and spatial information [2106.11539]. DocLLM's spatial interactions improve its reported pretraining accuracy over text-only attention [2401.00908]. LongDocURL reports substantially better QA when parsed text preserves document and table structure than when using PyMuPDF text [2412.18424]. MMDocRAG reports better aggregate results from detailed VLM-generated visual descriptions than from OCR alone [2505.16470].

- **Table semantics require more than extracting cell strings.** PubTabNet evaluates both table-tree structure and cell content [1911.10683]. Complex-table recognition preserves explicit cell boxes and spanning relations [2111.07129], while another heterogeneous-image pipeline reports strong row, column, and spanning-cell structure recognition [2203.09056]. TUTA demonstrates benefits from hierarchical table structure in representation learning [2010.12537], and TAPAS explicitly connects answers to selected table cells before aggregation [doi-10-18653-v1-2020-acl-main-398].

- **Spreadsheet reasoning benefits from fine-grained structure but remains difficult at complete-workbook scale.** FRTR indexes sheets, cells, formulas, windows, and images and reports higher QA accuracy from multi-granular retrieval than from individual retrieval-unit types [2601.08741]. SpreadsheetAgent reports gains from explicit structural sketches and from verification [2604.12282]. SpreadsheetBench 2 shows a large difference between cell-level modification correctness and complete-task correctness and identifies insufficient inspection and wrong-cell selection as common failure categories [2606.29955].

- **Reading order has both representation and generalization problems.** Pairwise and hierarchical ordering methods achieve very low error on some handwritten-document datasets but remain inadequate on the heterogeneous ABP collection [doi-10-1007-s00521-022-06948-5]. A later study finds that LLM-generated global reading-order relations align poorly with adjacency-oriented human labels while nevertheless improving several downstream document-understanding results [doi-10-18653-v1-2026-eacl-long-192].

- **Adjacent-domain reference-grounding evidence is useful but does not directly validate workplace-message attachment grounding.** Explicit textual-reference/coreference modeling improves pronoun grounding in J-CRe3 [doi-10-18653-v1-2025-acl-long-547]. Scene-graph spatial relationships and conversational recency improve multimodal coreference in SIMMC 2.0 [manual-bc798b0eed]. Specialized referring and grounding supervision improves several Ferret-UI results [2404.05719]. J-CRe3 separately demonstrates that omitted or zero references and region-valued targets can be represented and evaluated [manual-d896e242a6]. The supplied analyses do **not** report improved grounding specifically for omitted references.

- **Evidence locations can be non-unique.** In extended MP-DocVQA, some questions remain answerable from a page other than the single annotated answer page [2404.19024]. RefChartQA annotation finds samples with multiple defensible grounding regions [2503.23131]. CiteVQA accommodates this phenomenon with multiple-gold evidence settings [2605.12882].

- **Answer correctness and provenance correctness are empirically separable.** Hi-VT5 can return a correct answer while predicting the wrong evidence page [2212.05935]. CiteVQA's strongest system reports a lower Strict Attributed Accuracy than its answer score [2605.12882]. RefChartQA also reports cases in which the correct visual evidence is localized but subsequent mathematical reasoning still produces the wrong answer [2503.23131].

# Findings

1. Multiple studies demonstrate useful **components** of cross-version provenance, including spreadsheet-version recovery [1704.08476], persistent cross-snapshot XML identity [manual-ae200642f8], heterogeneous PDF element alignment [2607.14117], version-aware retrieval and change queries [2510.08109], and evolving-document citations with update status and explicitly evidenced temporal drift [2609.08364]. Their combination into one multimodal element-lineage mechanism is not evaluated.

2. Explicit table hierarchy, spatial localization, and cell relationships improve table recognition or downstream table understanding on the evaluated datasets [1911.10683] [2111.07129] [2203.09056] [2010.12537] [doi-10-18653-v1-2020-acl-main-398].

3. Hierarchical document-to-page-to-region evidence routing is empirically viable, and several studies show gains from localizing or structuring evidence before or during answering [2212.05935] [2607.29638] [2608.03292] [2605.12882] [2511.12003].

4. Structure-preserving or visually enriched document representations outperform flatter alternatives in several direct experiments, although the exact representation and task differ by study [2106.11539] [2401.00908] [2412.18424] [2505.16470].

5. Current spreadsheet systems can retain useful within-workbook provenance through sheet identities, cell addresses, formulas, and image identifiers, but complete-workbook correctness remains substantially harder than individual modifications or retrieved evidence [2601.08741] [2604.12282] [2606.29955].

6. Reading-order models can work very accurately on some document collections while failing to generalize equally well to heterogeneous layouts, and downstream-useful ordering relations need not coincide closely with an adjacency-oriented annotation convention [doi-10-1007-s00521-022-06948-5] [doi-10-18653-v1-2026-eacl-long-192].

7. Adjacent-domain studies demonstrate improvements from textual-reference/coreference structure, spatial scene structure, and specialized UI referring/grounding supervision [doi-10-18653-v1-2025-acl-long-547] [manual-bc798b0eed] [2404.05719]. J-CRe3 separately demonstrates representation and evaluation of omitted or zero references and spatial-region targets [manual-d896e242a6]. No supplied analysis demonstrates that these methods specifically improve grounding accuracy for omitted references.

8. Single-positive evidence annotations can underrepresent legitimate evidence alternatives, as shown by alternative answer-bearing pages in MP-DocVQA and multiple defensible regions in RefChartQA; CiteVQA explicitly supports multiple-gold evidence items [2404.19024] [2503.23131] [2605.12882].

9. Correct answers do not guarantee correct provenance, and correct localization does not guarantee correct downstream reasoning [2212.05935] [2605.12882] [2503.23131].

# Contradictions

## Grounding-oriented interventions, access to correct evidence, and answer accuracy

These studies examine three different interventions and therefore should not be collapsed into one controlled claim.

RefChartQA directly evaluates **grounding instruction tuning**. It reports large answer-accuracy improvements for TinyChart and some Qwen configurations, but UniChart loses accuracy on all three reported splits, ChartGemma loses substantially on two splits, and Qwen2.5-VL declines on two splits [2503.23131].

LAT instead applies **joint reasoning-and-evidence-attribution training** and reports simultaneous gains in answer exact match and spatial attribution over its vanilla model [2511.12003].

CiteVQA's oracle analyses test a third question: what happens when models receive **correct pages or documents**. Those experiments improve answer accuracy, indicating that localization can be a performance bottleneck [2605.12882].

The supported synthesis is therefore that grounding-oriented interventions or access to correct evidence can improve answering in some settings, but effects are not universally positive. Because the interventions and datasets differ, this is a scope-qualified tension rather than a strict cross-paper contradiction.

## Lossy OCR/plain-text representations versus structure- or visually enriched representations

MMLongBench-Doc provides the most direct OCR-versus-vision comparison in this corpus. Most evaluated LVLMs perform worse than LLM counterparts given lossy OCR text, although GPT-4o and GPT-4V are exceptions [2407.01523].

MMDocRAG answers a different question: detailed **VLM-generated descriptions of visual evidence** outperform OCR alone in its reported aggregate comparison [2505.16470].

LongDocURL evaluates another representation choice and reports that **structure-preserving parsed text** substantially outperforms PyMuPDF text for both proprietary and open models [2412.18424].

These are not three experiments on the same intervention. They show that plain OCR can remain competitive against some direct vision-language systems, while visually enriched textual descriptions and structure-preserving parsing can outperform more lossy textual representations in other settings.

# Open Gaps

## gap-1 — ACADEMIC, HIGH

The corpus still does not establish a complete method for maintaining evidence provenance across successive workplace attachment revisions, including stable attachment identity, version-relative source locations, semantic changes between versions, and lineage from an older cited region to its later counterpart.

The evidence is now broader than in earlier rounds. Spreadsheet evolution groups can be recovered probabilistically [1704.08476]; XML can maintain persistent node identities and invertible/composable deltas [manual-ae200642f8]; scientific-PDF elements can be aligned and differenced across versions [2607.14117]; VersionRAG explicitly handles version-specific retrieval and changes [2510.08109]; and SentryLine demonstrates evolving-document QA carrying source document, page, passage, citation key, and update status while reporting temporal drift only where passages explicitly document it [2609.08364]. Exact cross-version correspondence for attachment regions or spreadsheet cells, including old-to-new element lineage, remains unvalidated.

Suggested query: `"document version alignment" multimodal provenance region lineage semantic change revised document attachments`

## gap-2 — ACADEMIC, HIGH

Direct grounding of workplace-message expressions such as “this screenshot”, “the highlighted row”, “numbers below”, or “use attachment v2” into versioned attachment objects, pages, cells, or regions remains unvalidated.

Scene-text grounding [doi-10-1109-tmm-2022-3219642], textual-reference-aware visual dialogue grounding [doi-10-18653-v1-2025-acl-long-547], situated multimodal coreference [manual-bc798b0eed], UI referring-expression grounding [2404.05719], and J-CRe3's omitted-reference and region-target annotations [manual-d896e242a6] are adjacent-domain evidence rather than direct workplace-message evidence.

Suggested query: `"referring expression grounding" document multimodal attachment table cell screenshot coreference email`

## gap-3 — ACADEMIC, HIGH

Comprehensive spreadsheet understanding remains open for formulas, hidden rows and sheets, cross-sheet references, merged regions, formatting semantics, units, named ranges, and provenance across revised workbook versions.

FRTR covers retrieval and within-state provenance [2601.08741]; SpreadsheetAgent covers structure reconstruction and verification [2604.12282]; SpreadsheetBench 2 covers realistic workflow completion [2606.29955]; TUTA covers structured table representation [2010.12537]; and spreadsheet dependency work covers inter-worksheet structure [doi-10-1109-icse-2012-6227171]. The full combination remains unevaluated.

Suggested query: `"spreadsheet understanding" workbook formulas hidden sheets named ranges merged cells cross-sheet provenance version`

## gap-4 — ACADEMIC, HIGH

No admitted paper validates one end-to-end provenance representation that jointly identifies attachment version, page, document element, exact region or spreadsheet cell, and answer span.

CiteVQA provides document/page/bounding-box addresses [2605.12882]. M3Grounder links generated spans to pixel-level regions [manual-0661fc0cba]. TAPAS associates answers with table cells [doi-10-18653-v1-2020-acl-main-398]. VersionRAG represents document versions [2510.08109]. SentryLine carries document/page/passage/update-status citations [2609.08364]. Their composition into a single evaluated hierarchy remains open.

Suggested query: `"evidence provenance" document question answering version page region cell answer span multimodal grounding`

## gap-5 — ENGINEERING, HIGH

End-to-end behavior when extraction or grounding is unsupported, incomplete, or wrong remains insufficiently exercised.

The corpus includes unanswerable-case evaluation [2511.12003], attribution-interface and parser failures [2607.24651], offline-parsing and evidence-graph limitations [2606.15906], spreadsheet inspection and target-selection failures [2606.29955], and page-selection ambiguity [2404.19024]. It does not supply one engineering contract distinguishing genuine evidence absence from parser, OCR, layout, retrieval, or grounding failure.

## gap-6 — ENGINEERING, HIGH

Robustness of candidate extraction and structural-preservation pipelines on heterogeneous workplace-style documents remains open.

Complex and sparse business tables are represented in table benchmarks [2111.07129] [doi-10-1007-3-540-48172-9-21], heterogeneous and distorted document images are covered in table-recognition work [2203.09056], and reading-order heterogeneity is exercised separately [doi-10-1007-s00521-022-06948-5]. No admitted benchmark jointly covers sparse tables, merged and hierarchical structures, OCR corruption, irregular reading order, embedded visual objects, scanned pages, and explicit extraction-completeness accounting.

## gap-7 — ENGINEERING, MEDIUM

Operational scaling remains open for long documents, large tables, and realistic workbooks.

Complete-document MP-DocVQA shows substantial degradation when document length increases [2404.19024]. Doc-V* reports page-exploration costs [2604.13731]. MAGE-RAG notes controller and state-management overhead [2606.15906]. VersionRAG reports large token and runtime differences between retrieval architectures [2510.08109]. SpreadsheetBench 2 exercises large multi-sheet workflows [2606.29955]. These studies do not establish system-level latency, memory, and throughput for the target workload.

## gap-8 — ENGINEERING, HIGH

No admitted evaluation simultaneously measures semantic correctness, extraction completeness, exact provenance, unsupported-evidence handling, and preservation of tables, images, document hierarchy, and reading order on workplace-style attachments.

CiteVQA evaluates attributed answer correctness [2605.12882]. SMuDGE combines semantic correctness, grounding, calibration, and robustness [doi-10-18653-v1-2025-findings-naacl-295]. MMLongBench-Doc and LongDocURL cover long multimodal evidence and locating [2407.01523] [2412.18424]. Table and spreadsheet benchmarks cover other structural dimensions [1911.10683] [2606.29955]. The complete combination remains absent.

# Actionable Insights

- **Synthesis-derived recommendation:** represent source provenance as composable levels rather than one opaque citation, keeping attachment/version identity, page or sheet identity, element identity, region or cell location, and answer-span linkage as separately inspectable fields.

- **Synthesis-derived recommendation:** keep version identity separate from within-version coordinates so that every page region, table cell, or document element is interpreted relative to an explicit attachment version.

- **Synthesis-derived recommendation:** represent cross-version element matching as an explicit lineage relation with confidence and change metadata rather than silently reusing coordinates from an earlier version.

- **Synthesis-derived recommendation:** preserve native spreadsheet addresses, sheet names, formulas, merged-range information, hidden-state metadata, named ranges, formatting cues, and embedded-object identifiers before producing flattened textual representations.

- **Synthesis-derived recommendation:** evaluate message-to-attachment reference grounding separately from downstream proposition or response-scope reasoning, and retain unresolved or ambiguous grounding when more than one target remains defensible.

- **Synthesis-derived recommendation:** build independent engineering fixtures that distinguish parser failure, OCR failure, omitted pages, table-structure corruption, retrieval miss, grounding miss, true evidence absence, and multiple-valid-evidence cases.

- **Synthesis-derived recommendation:** score semantic answer correctness and provenance correctness separately and add an end-to-end measure that credits a result only when both are valid.

- **Synthesis-derived recommendation:** evaluate scaling on realistic multi-sheet workbooks and long mixed-modality attachments while retaining the same provenance and completeness checks used in smaller correctness tests.

# Confidence Summary

Confidence is **HIGH** that the corpus supports well-supported design principles around preserving spatial and structural information, distinguishing answer correctness from evidence correctness, and retaining explicit within-document provenance. These conclusions recur across table recognition, document QA, long-document routing, spreadsheet reasoning, and attribution evaluation [1911.10683] [2106.11539] [2212.05935] [2601.08741] [2605.12882].

Confidence is **MEDIUM** when transferring findings from scientific PDFs, XML warehouses, GUI screenshots, scene-text images, situated dialogue, clinical guidelines, and benchmark spreadsheets to workplace attachments because those studies do not directly evaluate the target domain [2607.14117] [manual-ae200642f8] [2404.05719] [doi-10-1109-tmm-2022-3219642] [manual-d896e242a6] [2609.08364].

Evidence for cross-version provenance is substantial at the component level but fragmented. No admitted study closes revised-workbook cell lineage or workplace-message-to-versioned-attachment grounding, so confidence that those target-domain questions are resolved is **LOW**.

# Limitations

- The 53 supplied analysis records represent **52 distinct studies**. `manual-1048d6caf2` and `doi-10-1109-tmm-2022-3219642` are records of the same *Scene-Text Oriented Referring Expression Comprehension* study and are not counted as independent corroboration.

- The corpus spans scientific PDFs, clinical guidelines, XML stores, web tables, business-document images, GUI screenshots, charts, situated dialogue, synthetic or benchmark spreadsheets, and long-document QA. Results from these domains are transfer evidence rather than direct production-workplace evidence.

- Several studies use synthetic data, curated benchmarks, or benchmark-specific adaptations. Their results demonstrate mechanisms or evaluation behavior but do not establish production mailbox representativeness.

- No supplied analysis reports one experiment covering revised-workbook identity, cell-level old-to-new correspondence, semantic change classification, and persistent provenance together.

- No supplied analysis directly evaluates natural workplace-message references to attachment versions, spreadsheet cells, highlighted rows, screenshots, or document regions.

- Some manual records contain less quantitative detail than the full-paper analyses, limiting direct numerical cross-study comparison.

- Inherited handoffs from Topics 04, 05, and 06 are project context only. They are not evidence for any finding or gap status in this synthesis.

- Differences in datasets, document lengths, model families, evidence annotations, and metrics mean that several apparent tensions are scope qualifications rather than genuine contradictions.
