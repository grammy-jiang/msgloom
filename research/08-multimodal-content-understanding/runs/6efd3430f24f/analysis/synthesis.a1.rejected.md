# Executive Summary

Across the distinct studies represented here, document understanding improves when models retain spatial, hierarchical, table, and multimodal structure rather than relying only on flattened text [2106.11539] [2010.12537] [2412.18424]. Evidence localization is repeatedly shown to be separable from answer correctness [2212.05935] [2503.23131] [2605.12882]. Long-document results show that page and region routing become harder as scope and cross-page composition increase [2404.19024] [2407.01523]. Spreadsheet studies demonstrate useful within-workbook structural and cell provenance [2601.08741], while versioning studies independently demonstrate persistent identity, similarity-based version recovery, and cross-version element alignment [manual-ae200642f8] [1704.08476] [2607.14117]. These components have not been jointly validated for revised workplace attachments. Referring-expression grounding is demonstrated in GUI, scene-text, and visually grounded dialogue domains, but not directly for workplace messages pointing into versioned attachments, screenshots, pages, table rows, or spreadsheet cells [2404.05719] [doi-10-1109-tmm-2022-3219642] [doi-10-18653-v1-2025-acl-long-547].

## Themes

### 1. Spatial and hierarchical structure materially affects document understanding

DocFormer reports improvements when visual, textual, and shared spatial representations are combined, including gains over text-plus-spatial variants on FUNSD and CORD [2106.11539]. TUTA reports that tree-structured neighborhoods and tree-position embeddings improve cell- and table-level classification on its evaluated table datasets [2010.12537]. DocLLM similarly reports better pre-training accuracy when spatial interactions are added to text-only attention [2401.00908].

The same pattern appears downstream. LongDocURL reports materially better QA when table structure is preserved by the parser rather than flattened with PyMuPDF text [2412.18424]. TRH2TQA separately reports benefits from recovering hierarchical business-table structure before question answering [manual-7fdf40b3c6].

**Finding:** Across these specific document and table benchmarks, explicit spatial or hierarchical representations improve measured performance relative to weaker structure-aware or text-only variants [2106.11539] [2010.12537] [2401.00908] [2412.18424] [manual-7fdf40b3c6].

### 2. Answer correctness and evidence correctness are different quantities

Hi-VT5's MP-DocVQA analysis includes cases where the answer is correct while the predicted evidence page is wrong, which the authors use to diagnose answers based on priors rather than the annotated supporting page [2212.05935]. RefChartQA reports the converse failure: a model can localize the correct chart evidence and still obtain the wrong answer because subsequent mathematical reasoning fails [2503.23131].

CiteVQA makes this distinction explicit in evaluation. Its strongest evaluated system reports an answer score of 86.1 but only 76.0 Strict Attributed Accuracy, and the discrepancy is much larger for the strongest open-source model [2605.12882]. DocTrace adds a behavioral test: masking cited evidence alters generated answers far more often than masking uncited context, although the authors explicitly caution that this does not prove the hidden reasoning computation follows the visible evidence graph [2608.03292].

**Finding:** The cited experiments demonstrate that answer correctness and evidence-localization correctness are separable and can fail independently [2212.05935] [2503.23131] [2605.12882] [2608.03292].

### 3. Long documents create a hierarchical evidence-acquisition problem

MP-DocVQA contains 47,952 pages across 5,928 documents, and Hi-VT5's advantage over concatenation baselines grows when the answer appears later in a document [2212.05935]. A separate OCR-free MP-DocVQA system falls from 81.55% page-selection accuracy to 60.45% when evaluation is expanded to complete documents reaching 793 pages [2404.19024].

Coarse-to-fine systems improve their respective baselines by reducing the amount of evidence that must be inspected. Doc-V* reports gains from semantic retrieval plus targeted high-resolution page fetching [2604.13731]. MAGE-RAG reports higher MMLongBench-Doc scores when page-only retrieval is augmented with fine-grained element rendering and graph-neighbor expansion [2606.15906]. HierDoc reports further gains when a learned region-routing stage follows page selection, while also showing that local crops and full-page context are complementary rather than interchangeable [2607.29638].

**Finding:** On the evaluated long-document benchmarks, longer scope and distributed evidence make localization harder, while hierarchical page and region acquisition improves performance over the corresponding weaker routing variants [2212.05935] [2404.19024] [2604.13731] [2606.15906] [2607.29638].

### 4. Table understanding requires more than text extraction

PubTabNet's TEDS metric jointly evaluates table tree structure and content and distinguishes errors that adjacency-only metrics can underrepresent [1911.10683]. Complex-table recognition studies report strong performance while explicitly preserving empty cells, spanning relationships, and strict cell localization [2111.07129] [2203.09056]. T-Recs earlier demonstrated bottom-up construction of row/column tile structures without requiring ruling lines and was designed to support sparse and spanning tables [doi-10-1007-3-540-48172-9-21].

Table semantics also affect answering. TAPAS explicitly links predicted answers to selected cells before optional aggregation [doi-10-18653-v1-2020-acl-main-398]. TRH2TQA reports improved business-table QA after recovering hierarchical relationships among cells [manual-7fdf40b3c6].

**Finding:** The admitted table literature demonstrates recovery and use of cell geometry, empty cells, spanning relationships, hierarchy, and cell-level evidence in ways that plain OCR text alone does not represent [1911.10683] [2111.07129] [2203.09056] [doi-10-18653-v1-2020-acl-main-398] [manual-7fdf40b3c6].

### 5. Spreadsheet reasoning benefits from structural representations, but full-workbook correctness remains difficult

FRTR reports 0.74 answer accuracy from hybrid retrieval versus 0.59 for vector-only and 0.42 for lexical-only retrieval, and its combination of row, column, window, and image retrieval units outperforms each single granularity on FRTR-Bench [2601.08741]. The same study retains explicit sheet locations, cell references, formulas, and image identifiers as within-workbook provenance [2601.08741].

SpreadsheetAgent reports gains from explicit YAML/JSON structural sketches and measurable degradation when its verification stage is removed [2604.12282]. SpreadsheetBench 2, however, shows a large separation between local edit accuracy and complete workflow correctness: its strongest evaluated model achieves 89.69% modification accuracy but only 34.00% task accuracy on financial modeling, with similarly large gaps in debugging [2606.29955].

**Finding:** On the reported spreadsheet benchmarks, multi-granular retrieval, structural reconstruction, and verification improve measured reasoning performance, while high cell-level modification accuracy does not imply complete-workbook task success [2601.08741] [2604.12282] [2606.29955].

### 6. Cross-version lineage has multiple empirically demonstrated mechanisms

Change-Centric Management of Versions in an XML Warehouse uses persistent XIDs so corresponding XML nodes retain logical identity across snapshots; its completed deltas can also be inverted and composed across the history [manual-ae200642f8]. Earlier XML differencing work uses XML IDs and subtree signatures as matching anchors and propagates matches hierarchically [doi-10-1109-icde-2002-994696]. Schema-less semantic change detection demonstrates matching when semantically corresponding XML content is reorganized structurally [doi-10-1007-978-3-540-30480-7-29].

For PDFs, the heterogeneous-element differencing study reports that removing cross-version alignment reduces detection, localization, alignment, and matching scores, and that type-specific spatial, content, and structural weights outperform uniform weights [2607.14117]. For spreadsheets, SpreadCluster reports 74.4% F-measure for recovering Enron evolution groups from structural and textual similarity, outperforming its filename-based comparison [1704.08476].

**Finding:** Persistent identifiers, semantic or structural matching, heterogeneous-element alignment, and similarity clustering are each empirically demonstrated mechanisms for recovering identity or correspondence across versions in their respective XML, scientific-PDF, and spreadsheet settings [manual-ae200642f8] [doi-10-1109-icde-2002-994696] [doi-10-1007-978-3-540-30480-7-29] [2607.14117] [1704.08476].

These papers do **not** jointly validate one combined version-lineage scheme.

### 7. Referring-expression grounding has adjacent-domain evidence, not direct workplace-message evidence

Ferret-UI reports strong screen-element grounding after UI-specific referring and grounding instruction tuning [2404.05719]. Scene-Text Oriented Referring Expression Comprehension explicitly aligns referring expressions, scene text, and visual regions [doi-10-1109-tmm-2022-3219642]. J-CRe3 supplies persistent object-instance identifiers, object boxes, spatial regions, dialogue, and cross-modal references, including omitted arguments [manual-d896e242a6].

The ACL 2025 J-CRe3 study reports that adding textual coreference information improves pronoun grounding from Recall@1 0.277 to 0.361 and also improves higher recall cutoffs [doi-10-18653-v1-2025-acl-long-547]. GRAVL-BERT separately reports improvements from scene-graph relationships and conversational recency on SIMMC 2.0 [manual-bc798b0eed].

**Finding:** Explicit textual-reference, spatial, scene-text, and dialogue context improves grounding on the cited GUI, scene-text, and situated-dialogue datasets [2404.05719] [doi-10-1109-tmm-2022-3219642] [doi-10-18653-v1-2025-acl-long-547] [manual-d896e242a6] [manual-bc798b0eed].

This is transfer evidence. None of these studies directly evaluates workplace-message expressions such as “use attachment v2” or “the highlighted row” against versioned business attachments.

### 8. Hierarchical provenance can be made inspectable within a document

CiteVQA represents evidence with document index, page index, and element bounding box, and maps synthesized evidence back to source-PDF coordinates [2605.12882]. M3Grounder links individual generated answer spans to segmentation masks and supports phrase-, line-, and block-level evidence [manual-0661fc0cba].

MAGE-RAG retains page identifiers, element nodes, bounding boxes, image references, and page-node alignment in its evidence graph [2606.15906]. HierDoc similarly carries page-to-region metadata and bounding boxes, although its region aliases are sample-local rather than persistent across document revisions [2607.29638]. DocTrace constructs an explicit hierarchical evidence graph and reports high structural-validity metrics for the generated traces [2608.03292].

**Finding:** These systems demonstrate inspectable provenance at combinations of page, element, region, mask, and answer-span granularity within the evaluated document state [2605.12882] [manual-0661fc0cba] [2606.15906] [2607.29638] [2608.03292].

They do not validate persistence of those identities across attachment revisions.

### 9. Flattened OCR or plain text can lose decision-relevant visual structure

MMLongBench-Doc finds that OCR-based LLM pipelines are competitive on text and table questions but comparatively weak on image- and chart-dependent questions [2407.01523]. LongDocURL reports a large downstream QA difference between structure-preserving Docmind parsing and plain PyMuPDF text, particularly around table structure [2412.18424].

MMDocRAG reports that detailed VLM-generated descriptions of visual evidence outperform OCR-only evidence in its aggregate comparison [2505.16470]. InfographicVQA similarly finds that locating and reasoning over combined text, layout, graphics, tables, and visualizations remains difficult even when much of the answer text itself is present in OCR spans or a common-answer vocabulary [2104.12756].

**Finding:** The cited benchmarks demonstrate cases where OCR or flattened text omits structure or visual semantics that affect downstream answering [2407.01523] [2412.18424] [2505.16470] [2104.12756].

### 10. Provenance has multiple semantics

Why and Where: A Characterization of Data Provenance formally separates why-provenance, which identifies source information sufficient to justify why an output exists, from where-provenance, which identifies source locations from which output values originate [doi-10-1007-3-540-44503-x-20].

The warehouse-lineage work separately defines lineage as tracing a selected materialized-view item back to the exact source tuples that produced it, including views with aggregation [doi-10-1145-357775-357777].

**Finding:** The provenance literature represented here establishes distinct semantics for explanation, source location, and source-item lineage rather than treating them as one interchangeable notion [doi-10-1007-3-540-44503-x-20] [doi-10-1145-357775-357777].

## Contradictions

### Grounding supervision does not universally improve answer accuracy

LAT reports simultaneous gains in soft exact match and IoU-based attribution relative to its vanilla backbone [2511.12003]. CiteVQA's oracle analyses also show answer improvements when systems are restricted to gold documents or pages, indicating evidence localization can be a performance bottleneck [2605.12882].

RefChartQA, however, directly contradicts a universal positive-effect claim. Grounding instruction tuning improves TinyChart and some Qwen variants, but UniChart loses answer accuracy on all three reported splits, ChartGemma loses substantially on human and PoT splits, and Qwen2.5-VL declines on two splits [2503.23131].

The consistent synthesis is therefore narrower: grounding and answer quality are related, but the effect of grounding supervision on answer accuracy depends on the model and training setting.

### OCR/text pipelines and native multimodal processing show mixed comparative results

MMLongBench-Doc reports that most evaluated LVLMs perform worse than LLM counterparts supplied with OCR text, with GPT-4o and GPT-4V as exceptions [2407.01523]. In contrast, MMDocRAG reports that detailed VLM-generated descriptions outperform OCR-only evidence [2505.16470], while LongDocURL reports that structure-preserving parsing substantially outperforms plain PyMuPDF text [2412.18424].

These experiments differ in models, parsing representations, question modalities, and tasks. They cannot be reduced to either “vision always wins” or “OCR text always wins.”

### Coordinate generation and language-mediated attribution favor different interfaces

Evidence Attribution in Visual Document Understanding without Coordinates or Region Labels finds that replacing direct bounding-box generation with evidence quotations raises evidence recall from a maximum of 8.1% for coordinate output to 25.9%-46.9% for the language interface and sharply reduces attribution hallucination [2607.24651].

In contrast, M3Grounder reports strong phrase-, line-, and block-level mask grounding with an architecture trained specifically for those outputs [manual-0661fc0cba], and Ferret-UI reports high manually checked box-grounding accuracy for UI elements [2404.05719].

The experiments therefore support different interfaces under different supervision and task conditions rather than establishing one universally superior grounding representation.

### Human-labelled reading order and downstream-useful reading order are not the same target

The handwritten-document reading-order study evaluates directly against annotated reading sequences and reports very low ordering error on OHG and FCR, while performance remains substantially worse on heterogeneous ABP [doi-10-1007-s00521-022-06948-5].

The EACL 2026 study reports that GPT-4o-derived reading-order relations score only 30.25 F1 against segment-level human labels versus 80.49 for LayoutLMv3-large, yet the GPT-derived relations improve downstream entity extraction, entity linking, and document QA when added to models [doi-10-18653-v1-2026-eacl-long-192].

The apparent contradiction reflects different objectives: label agreement and downstream structural usefulness are not equivalent.

### A single annotated evidence location is not always uniquely correct

The multi-page OCR-free DocVQA study observes questions that remain answerable from a page other than the annotated evidence page, especially in its extended-document evaluation [2404.19024]. RefChartQA's manual checking similarly found cases with multiple defensible chart grounding regions [2503.23131].

CiteVQA, by contrast, evaluates against defined gold evidence regions or sets [2605.12882]. These approaches are not mutually exclusive, but the first two studies show that single-positive annotations can underrepresent valid alternative support.

## Open Gaps

### gap-1 — ACADEMIC, HIGH

The corpus still does not establish a complete method for maintaining evidence provenance across successive workplace attachment revisions, including stable attachment identity, version-relative source locations, semantic changes between versions, and lineage from an older cited region to its later counterpart.

There is strong partial coverage. SpreadCluster recovers candidate spreadsheet evolution groups [1704.08476]. Persistent XIDs preserve XML-node identity across snapshots [manual-ae200642f8]. Schema-less matching can align semantically equivalent XML content across restructuring [doi-10-1007-978-3-540-30480-7-29]. Scientific-PDF alignment handles text, tables, formulas, and figures across versions [2607.14117]. VersionRAG explicitly retrieves version-specific content and differences [2510.08109]. No admitted study combines those components for revised workplace attachments.

Suggested query: `"document version alignment" multimodal provenance region lineage semantic change revised document attachments`

### gap-2 — ACADEMIC, HIGH

Direct grounding of workplace-message referring expressions such as “this screenshot”, “the highlighted row”, “numbers below”, or “use attachment v2” into attachment objects, pages, cells, or regions remains unvalidated.

Grounding has been demonstrated for GUI screens [2404.05719], scene-text-dependent references [doi-10-1109-tmm-2022-3219642], situated dialogue [manual-d896e242a6] [manual-bc798b0eed], and multimodal textual-reference structures [doi-10-18653-v1-2025-acl-long-547]. These are adjacent domains rather than direct workplace-message-to-attachment evidence.

Suggested query: `"referring expression grounding" document multimodal attachment table cell screenshot coreference email`

### gap-3 — ACADEMIC, HIGH

Comprehensive spreadsheet understanding remains open for formulas, hidden rows and sheets, cross-sheet references, merged regions, formatting semantics, units, named ranges, and provenance across revised workbook versions.

FRTR covers multi-granular retrieval plus sheet, cell, formula, and image identifiers within a workbook state [2601.08741]. SpreadsheetAgent covers incremental structural extraction and verification [2604.12282]. SpreadsheetBench 2 covers large multi-sheet workflows and exposes target-cell and inspection failures [2606.29955]. Inter-worksheet smell work studies cross-sheet dependency structure [doi-10-1109-icse-2012-6227171], and TableCheck examines computationally corresponding table clones and inconsistent cells [doi-10-1145-2950290-2950359]. The complete feature inventory and cross-revision provenance problem remain unvalidated.

Suggested query: `"spreadsheet understanding" workbook formulas hidden sheets named ranges merged cells cross-sheet provenance version`

### gap-4 — ACADEMIC, HIGH

No admitted paper validates one end-to-end provenance representation that jointly identifies attachment version, page, document element, exact region or spreadsheet cell, and answer span.

CiteVQA covers document/page/element box hierarchy [2605.12882]. M3Grounder links answer spans to hierarchical pixel masks [manual-0661fc0cba]. FRTR keeps sheet and cell locations [2601.08741]. HierDoc and DocTrace retain page-region evidence structures [2607.29638] [2608.03292]. Version-aware and cross-version papers cover version identity and correspondence separately [2510.08109] [2607.14117] [manual-ae200642f8]. Their combination is untested.

Suggested query: `"evidence provenance" document question answering version page region cell answer span multimodal grounding`

### gap-5 — ENGINEERING, HIGH

End-to-end behavior when extraction or grounding is unsupported, incomplete, or wrong remains insufficiently exercised.

LAT evaluates no-answer behavior for unanswerable multi-image cases [2511.12003]. Coordinate-free attribution reports missing quotations, parser misses, and quote-to-region assignment conflicts [2607.24651]. MAGE-RAG identifies offline parsing and evidence-graph quality as an upper bound [2606.15906]. VersionRAG attributes failures to query misclassification and incomplete change extraction [2510.08109]. SpreadsheetBench 2 identifies incomplete inspection and wrong target-cell selection as major failures [2606.29955].

No admitted evaluation provides a complete engineering contract that distinguishes genuine evidence absence from parser, OCR, layout, retrieval, grounding, and unsupported-format failure.

### gap-6 — ENGINEERING, HIGH

Robustness of candidate extraction and structural-preservation pipelines on heterogeneous workplace-style documents remains open.

Complex-table studies separately cover empty and spanning cells [2111.07129], curved and distorted tables [2203.09056], and hierarchical business tables [manual-7fdf40b3c6]. Reading-order research covers handwritten and heterogeneous layouts [doi-10-1007-s00521-022-06948-5]. Document-image verification tests print-scan distortion and changes affecting text, images, and tables [doi-10-3390-app152312430]. Long-document benchmarks add mixed text, chart, table, image, and layout evidence [2407.01523] [2412.18424].

No admitted benchmark jointly exercises all of these with explicit extraction-completeness accounting.

### gap-7 — ENGINEERING, MEDIUM

Operational scaling remains open for long documents, large tables, and realistic workbooks.

The extended MP-DocVQA experiment demonstrates degradation as documents become much longer [2404.19024]. Doc-V* measures pages examined under different routing variants [2604.13731]. MAGE-RAG notes controller/evaluator overhead and added state-management cost [2606.15906]. RoI-Matcher reports very low per-image inference time relative to multimodal baselines [2506.21055]. SpreadsheetBench 2 exercises workbooks averaging 11.8 worksheets and hundreds of required cell modifications [2606.29955]. XML differencing work reports explicit quality-speed trade-offs [doi-10-1002-spe-2305].

These do not close target-workload latency, memory, and throughput at the system level.

### gap-8 — ENGINEERING, HIGH

The corpus lacks one evaluation that simultaneously measures semantic correctness, extraction completeness, exact provenance, unsupported-evidence handling, and preservation of tables, images, document hierarchy, and reading order on workplace-style attachments.

CiteVQA measures answer-plus-evidence correctness [2605.12882]. SMuDGE combines semantic correctness, groundedness, answer type, calibration, and robustness dimensions [doi-10-18653-v1-2025-findings-naacl-295]. MMLongBench-Doc and LongDocURL include multiple modalities and evidence localization [2407.01523] [2412.18424]. Table benchmarks deeply evaluate structural recovery [1911.10683] [2111.07129]. SpreadsheetBench 2 evaluates end-to-end workbook workflows [2606.29955].

No one admitted benchmark covers the full requested combination.

## Actionable Insights

The following are **synthesis-derived recommendations**. They go beyond what any single experiment directly tested and are project decisions rather than literature findings.

1. **Synthesis-derived recommendation:** represent evidence addresses as typed hierarchical objects rather than reducing every citation to a text span. Retain distinct fields for attachment/version identity, page or sheet, element type, region or cell address, and answer-span linkage.

2. **Synthesis-derived recommendation:** treat cross-version element correspondence as a relation separate from within-version location. A location identifies where evidence exists in one version; a lineage relation records whether and how an element corresponds to another version.

3. **Synthesis-derived recommendation:** retain source artifacts and extracted structural representations side by side so that later corrections can be traced to the exact version and region from which an interpretation was derived.

4. **Synthesis-derived recommendation:** evaluate answer correctness and provenance correctness independently. Include both “correct answer, wrong evidence” and “correct evidence, wrong answer” cases.

5. **Synthesis-derived recommendation:** distinguish genuine no-evidence cases from extraction, OCR, layout, retrieval, grounding, and unsupported-format failures instead of mapping all of them to an empty result.

6. **Synthesis-derived recommendation:** create spreadsheet fixtures that separately exercise formulas, cross-sheet dependencies, hidden content, merged cells, formatting and units, named ranges, embedded images, and revision lineage rather than assuming ordinary visible-cell QA covers these behaviors.

7. **Synthesis-derived recommendation:** evaluate workplace-message-to-attachment referring expressions as their own surface, including version-selection language, row and cell references, positional language, visual emphasis, and ambiguous references with multiple candidate regions.

8. **Synthesis-derived recommendation:** do not treat page routing, region grounding, spreadsheet cell provenance, and cross-version alignment as one empirically validated provenance design until that combined scheme has itself been tested end to end.

## Confidence Summary

Confidence is **high** for several well-supported design principles in the evidence: spatial and hierarchical structure improves performance in multiple document and table settings [2106.11539] [2010.12537] [2412.18424]; answer correctness and evidence correctness are distinct [2212.05935] [2503.23131] [2605.12882]; hierarchical evidence acquisition improves several long-document systems relative to their weaker variants [2604.13731] [2606.15906] [2607.29638]; and persistent identifiers or alignment mechanisms preserve correspondence in their evaluated versioning domains [manual-ae200642f8] [2607.14117].

Confidence is **medium** for transferring referring-expression methods into workplace-email and attachment settings because the direct empirical evidence comes from GUI, scene-text, situated-dialogue, and related grounding domains [2404.05719] [doi-10-1109-tmm-2022-3219642] [doi-10-18653-v1-2025-acl-long-547].

Confidence is **low** for any claim that the literature already validates a complete cross-version workplace-attachment provenance stack. Individual components are evidenced; their integration is not.

## Limitations

- The supplied corpus contains 53 analysis records but 52 distinct studies. `manual-1048d6caf2` and `doi-10-1109-tmm-2022-3219642` describe the same **Scene-Text Oriented Referring Expression Comprehension** study and were treated as one independent piece of evidence rather than two corroborating papers.

- This synthesis is based on reduced per-paper analyses rather than full papers. Methodological details, negative results, and dataset caveats absent from those analyses cannot be reconstructed safely.

- The evidence spans document QA, scientific PDFs, XML warehouses, business tables, general spreadsheets, GUI screenshots, charts, clinical guidelines, and situated dialogue. Results from those domains are not direct production-email evidence.

- Several results come from synthetic, benchmark, or adjacent-domain settings. They support mechanisms and experiments but do not establish production representativeness for workplace communication.

- Metrics differ substantially across studies: ANLS, F1, IoU, TEDS, page-selection accuracy, task accuracy, modification accuracy, retrieval accuracy, strict attributed accuracy, and other measures are not directly interchangeable.

- Several papers independently validate pieces that could form a hierarchical cross-version provenance scheme, but papers that validate different pieces do not jointly validate their combination.

- The inherited handoffs from earlier Topics are project context only. They were not used as evidence for any finding or for closing any gap.

### Gap Status

- **gap-1: open.** Scientific-PDF alignment, XML persistent identity, spreadsheet version clustering, semantic XML matching, and version-aware retrieval provide partial mechanisms, but no admitted study closes the full workplace-attachment lineage problem [2607.14117] [manual-ae200642f8] [1704.08476] [2510.08109] [doi-10-1007-978-3-540-30480-7-29].

- **gap-2: open.** Direct workplace-message-to-versioned-attachment grounding remains unvalidated despite related GUI, scene-text, and situated-dialogue grounding results [2404.05719] [doi-10-1109-tmm-2022-3219642] [doi-10-18653-v1-2025-acl-long-547] [manual-d896e242a6] [manual-8444bbc95c].

- **gap-3: open.** Existing spreadsheet studies cover substantial but incomplete portions of the required semantics and provenance surface [2601.08741] [2604.12282] [2606.29955] [doi-10-1109-icse-2012-6227171] [doi-10-1145-2950290-2950359].

- **gap-4: open.** No admitted study jointly validates attachment version, page, element, region or cell, and answer span in one end-to-end representation [2605.12882] [manual-0661fc0cba] [2607.29638] [2608.03292] [2601.08741].

- **gap-5: open.** Failure analyses exist, but the corpus does not supply a complete engineering distinction between genuine evidence absence and upstream extraction, parsing, OCR, retrieval, or grounding failures [2511.12003] [2607.24651] [2606.15906] [2510.08109] [2606.29955].

- **gap-6: open.** Heterogeneous layout and extraction failure modes are covered piecemeal rather than by one complete workplace-style robustness benchmark [2111.07129] [2203.09056] [doi-10-1007-s00521-022-06948-5] [2412.18424] [doi-10-3390-app152312430].

- **gap-7: open.** Individual scaling and cost measurements exist, but target-workload system-level latency, memory, and throughput remain unevaluated [2404.19024] [2604.13731] [2606.15906] [2506.21055] [2606.29955] [doi-10-1002-spe-2305].

- **gap-8: open.** Existing metrics and benchmarks cover overlapping dimensions, but no single admitted evaluation combines semantic correctness, completeness, exact provenance, unsupported handling, multimodal preservation, hierarchy, and reading order [2605.12882] [doi-10-18653-v1-2025-findings-naacl-295] [2407.01523] [2412.18424] [1911.10683] [2606.29955].
