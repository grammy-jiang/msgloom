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

# Task: independent review of the cross-paper synthesis

Research topic: **Direct empirical methods for cross-version multimodal document element lineage and hierarchical provenance, with special attention to revised workbook provenance and message referring-expression grounding into versioned pages, regions, and cells.**

You did not write this synthesis and you are not reviewing your own work.
Your verdict decides whether the report may be written. Rejecting is a normal
outcome: reject when the evidence does not support the synthesis. Do not
soften a real problem into a note so that the work can pass.

Check five things against the analyses below, not against how well the
synthesis reads:

1. Faithfulness — every finding is traceable to at least one analysis, and no
   finding states more than its cited analyses support.
2. Citation integrity — every cited paper_id is one of: `1704.08476`, `1911.10683`, `2006.14806`, `2010.12537`, `2104.12756`, `2106.11539`, `2111.07129`, `2203.09056`, `2212.05935`, `2401.00908`, `2404.05719`, `2404.19024`, `2407.01523`, `2410.05243`, `2412.18424`, `2503.23131`, `2505.16470`, `2506.21055`, `2510.08109`, `2511.12003`, `2601.08741`, `2604.12282`, `2604.13731`, `2605.12882`, `2606.15906`, `2606.29955`, `2607.14117`, `2607.24651`, `2607.29638`, `2608.03292`, `2609.08364`, `doi-10-1002-spe-2305`, `doi-10-1007-3-540-44503-x-20`, `doi-10-1007-3-540-48172-9-21`, `doi-10-1007-978-3-540-30480-7-29`, `doi-10-1007-s00521-022-06948-5`, `doi-10-1109-icde-2002-994696`, `doi-10-1109-icse-2012-6227171`, `doi-10-1109-tmm-2022-3219642`, `doi-10-1145-2950290-2950359`, `doi-10-1145-357775-357777`, `doi-10-18653-v1-2020-acl-main-398`, `doi-10-18653-v1-2025-acl-long-547`, `doi-10-18653-v1-2025-findings-naacl-295`, `doi-10-18653-v1-2026-eacl-long-192`, `doi-10-3390-app152312430`, `manual-0661fc0cba`, `manual-1048d6caf2`, `manual-7fdf40b3c6`, `manual-8444bbc95c`, `manual-ae200642f8`, `manual-bc798b0eed`, `manual-d896e242a6`.
3. Coherence — contradictions between papers are named, not averaged away.
4. Gap completeness — a gap this corpus cannot close is reported as open. A
   gap presented as closed without evidence is a rejection.
5. Overreach — transfer-domain or synthetic evidence is not presented as
   direct-domain evidence, and no production claim rests on it.

Synthesis under review:
{
 "topic": "Direct empirical methods for cross-version multimodal document element lineage and hierarchical provenance, with special attention to revised workbook provenance and message referring-expression grounding into versioned pages, regions, and cells.",
 "paper_count": 52,
 "executive_summary": "Across 52 distinct studies, the corpus demonstrates strong but fragmented empirical support for document structure preservation, table and spreadsheet semantics, hierarchical evidence localization, multimodal referring-expression grounding, and several forms of version-aware provenance. Cross-version work includes spreadsheet-version clustering, persistent XML identities and reversible deltas, heterogeneous PDF element alignment, version-aware retrieval, and evolving-document QA with document/page/passage/update-status citations. Separately, document-QA studies show that page and region localization can materially affect answer quality and that correct answers can still carry incorrect or incomplete provenance. Spreadsheet studies preserve useful within-version cell, sheet, formula, and image locations but do not establish lineage across revised workbooks. Adjacent dialogue, GUI, and scene-text studies demonstrate useful reference-grounding mechanisms, but direct grounding of workplace-message references into versioned attachments remains unvalidated. All eight previously identified gaps therefore remain open.",
 "themes": [
  "Cross-version identity and change tracking are empirically demonstrated for several representation families, but at different granularities and in different domains.",
  "Hierarchical provenance increasingly links answers to document, page, element, region, or cell locations rather than treating answer correctness alone as sufficient.",
  "Preserving document layout, table hierarchy, visual semantics, and spreadsheet structure often improves downstream understanding compared with flatter representations.",
  "Table and spreadsheet reasoning depend on structural context such as headers, merged or spanning relations, formulas, sheet identity, and spatial organization.",
  "Long-document evidence acquisition benefits from hierarchical page-to-region selection, but distributed evidence and long contexts remain difficult.",
  "Multimodal reference grounding benefits from textual-reference structure, spatial scene structure, and specialized referring/grounding supervision in adjacent domains.",
  "Evaluation increasingly distinguishes answer correctness from evidence correctness and exposes ambiguity when more than one page or region can legitimately support an answer."
 ],
 "findings": [
  {
   "statement": "The corpus demonstrates several distinct forms of version-aware provenance: spreadsheet versions can be recovered probabilistically from structural and textual similarity; XML nodes can retain persistent logical identities across snapshots with invertible and composable deltas; revised scientific PDFs can be aligned and differenced at text, table, formula, and figure level; version-aware RAG can explicitly retrieve version-specific content and changes; and evolving-document QA can carry document, page, passage, citation-key, and update-status provenance while reporting temporal drift only when retrieved passages explicitly document a change. These studies cover different parts of version provenance rather than one jointly evaluated multimodal lineage scheme.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "1704.08476",
     "section": "versioned spreadsheet clustering results"
    },
    {
     "paper_id": "manual-ae200642f8",
     "section": "persistent XIDs and completed deltas"
    },
    {
     "paper_id": "2607.14117",
     "section": "cross-version heterogeneous element alignment and differencing"
    },
    {
     "paper_id": "2510.08109",
     "section": "version-aware retrieval and change-query evaluation"
    },
    {
     "paper_id": "2609.08364",
     "section": "structured citations and evidenced temporal drift"
    }
   ]
  },
  {
   "statement": "Explicit table structure is empirically useful for recovering and reasoning over complex tables. Image-table systems recover cells, row and column structure, spanning relations, and spatial boxes; structure-aware table pretraining improves cell and table classification; and table QA can associate predictions with selected cells. These results are demonstrated on document-image, web-table, and table-QA benchmarks rather than on revised workplace workbooks.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "1911.10683",
     "section": "PubTabNet structure and content recognition"
    },
    {
     "paper_id": "2111.07129",
     "section": "complex table cells, spanning relations, and spatial boxes"
    },
    {
     "paper_id": "2203.09056",
     "section": "table detection and structure recognition"
    },
    {
     "paper_id": "2010.12537",
     "section": "tree-structured table pretraining ablations"
    },
    {
     "paper_id": "doi-10-18653-v1-2020-acl-main-398",
     "section": "cell selection for table question answering"
    }
   ]
  },
  {
   "statement": "Long-document studies demonstrate that evidence localization can be modeled hierarchically from documents to pages and then to regions or elements. Page identification, learned region routing, structured evidence graphs, and answer-plus-region attribution improve localization or downstream QA in their respective benchmarks, while answer correctness and evidence correctness remain separable outcomes.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "2212.05935",
     "section": "answer-page identification in MP-DocVQA"
    },
    {
     "paper_id": "2607.29638",
     "section": "page-to-region hierarchical routing"
    },
    {
     "paper_id": "2608.03292",
     "section": "hierarchical evidence graph traceability"
    },
    {
     "paper_id": "2605.12882",
     "section": "strict attributed accuracy and hierarchical spatial evidence addresses"
    },
    {
     "paper_id": "2511.12003",
     "section": "answer generation with visual evidence attribution"
    }
   ]
  },
  {
   "statement": "Several experiments show downstream benefits from representations that preserve or enrich non-textual document structure. DocFormer gains from combining text, visual, and shared spatial features; DocLLM improves pretraining accuracy when spatial interactions are added; LongDocURL reports substantially better QA from structure-preserving parsing than from PyMuPDF text; and MMDocRAG reports better aggregate performance from detailed VLM-generated visual descriptions than from OCR text alone.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "2106.11539",
     "section": "multimodal and spatial-feature ablations"
    },
    {
     "paper_id": "2401.00908",
     "section": "spatial-attention ablations"
    },
    {
     "paper_id": "2412.18424",
     "section": "structure-preserving parsing comparison"
    },
    {
     "paper_id": "2505.16470",
     "section": "visual-description versus OCR comparison"
    }
   ]
  },
  {
   "statement": "Spreadsheet studies demonstrate useful within-workbook structural and provenance representations but also substantial remaining workflow difficulty. Retrieval over sheet locations, cell references, formulas, and image identifiers supports auditable single-workbook reasoning; explicit structural sketches and verification improve spreadsheet QA; and SpreadsheetBench 2 shows that high cell-level modification accuracy can coexist with much lower complete-task accuracy, with insufficient workbook inspection and wrong target-cell selection among dominant failures.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "2601.08741",
     "section": "multi-granular retrieval and within-workbook provenance"
    },
    {
     "paper_id": "2604.12282",
     "section": "structural sketches and verification ablations"
    },
    {
     "paper_id": "2606.29955",
     "section": "workflow accuracy and failure analysis"
    },
    {
     "paper_id": "doi-10-1109-icse-2012-6227171",
     "section": "inter-worksheet dependencies and formula inspection"
    }
   ]
  },
  {
   "statement": "Reading order is not fully captured by a single universal representation. Pairwise and hierarchical ordering models achieve very low ordering error on some handwritten-document collections but remain inadequate on a heterogeneous collection, while LLM-inferred global reading-order relations align poorly with adjacency-oriented human labels yet improve several downstream document-understanding results in the reported experiments.",
   "confidence": "MEDIUM",
   "evidence": [
    {
     "paper_id": "doi-10-1007-s00521-022-06948-5",
     "section": "reading-order accuracy and heterogeneous-dataset failure"
    },
    {
     "paper_id": "doi-10-18653-v1-2026-eacl-long-192",
     "section": "reading-order label alignment and downstream-task ablations"
    }
   ]
  },
  {
   "statement": "Adjacent-domain studies show that explicit textual-reference or coreference structure, spatial scene structure, and specialized UI referring/grounding supervision can improve reference grounding in their evaluated settings. Separately, J-CRe3 demonstrates that a multimodal reference dataset can represent and evaluate omitted or zero references and targets that are spatial regions rather than only discrete objects. The supplied analyses do not demonstrate improved grounding accuracy specifically for omitted references.",
   "confidence": "MEDIUM",
   "evidence": [
    {
     "paper_id": "doi-10-18653-v1-2025-acl-long-547",
     "section": "textual-reference modeling and pronoun grounding"
    },
    {
     "paper_id": "manual-bc798b0eed",
     "section": "scene relationships and reference-distance ablations"
    },
    {
     "paper_id": "2404.05719",
     "section": "UI referring and grounding supervision"
    },
    {
     "paper_id": "manual-d896e242a6",
     "section": "zero references, region targets, and multimodal annotations"
    },
    {
     "paper_id": "doi-10-1109-tmm-2022-3219642",
     "section": "scene-text-oriented referring-expression grounding"
    }
   ]
  },
  {
   "statement": "Evidence localization is not always uniquely represented by one annotated page or region. MP-DocVQA experiments identify questions that remain answerable from a page different from the annotated evidence page, RefChartQA annotation reveals samples with multiple defensible grounding regions, and CiteVQA explicitly includes multiple-gold evidence settings rather than assuming one unique supporting location.",
   "confidence": "MEDIUM",
   "evidence": [
    {
     "paper_id": "2404.19024",
     "section": "alternative answer-bearing pages in MP-DocVQA"
    },
    {
     "paper_id": "2503.23131",
     "section": "manual grounding validation and multiple defensible regions"
    },
    {
     "paper_id": "2605.12882",
     "section": "multi-document multiple-gold evidence evaluation"
    }
   ]
  },
  {
   "statement": "Answer accuracy alone overstates provenance reliability in document QA. MP-DocVQA reports cases with a correct answer but an incorrect predicted evidence page; CiteVQA reports substantially lower strict attributed accuracy than answer score for its strongest system; and RefChartQA reports cases where the correct visual elements are localized but subsequent mathematical reasoning still produces an incorrect answer.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "2212.05935",
     "section": "correct-answer but wrong-answer-page analysis"
    },
    {
     "paper_id": "2605.12882",
     "section": "answer score versus Strict Attributed Accuracy"
    },
    {
     "paper_id": "2503.23131",
     "section": "correct localization with incorrect reasoning"
    }
   ]
  }
 ],
 "contradictions": [
  {
   "topic": "Grounding-oriented interventions, access to correct evidence, and answer accuracy",
   "papers": [
    "2503.23131",
    "2511.12003",
    "2605.12882"
   ],
   "note": "These studies should not be treated as controlled tests of one identical intervention. RefChartQA directly tests grounding instruction tuning and finds large gains for some backbones but accuracy losses for others. LAT jointly trains reasoning and evidence attribution and reports gains in both answer and attribution metrics. CiteVQA's oracle analyses instead provide ground-truth pages or documents and show improved answering. The defensible synthesis is that grounding-oriented interventions or access to correct evidence can help answering in some settings, but the effect is not universally positive; differences across these papers are primarily intervention and task scope qualifications rather than a strict cross-paper contradiction."
  },
  {
   "topic": "Lossy OCR/plain-text representations versus structure- or visually enriched representations",
   "papers": [
    "2407.01523",
    "2505.16470",
    "2412.18424"
   ],
   "note": "MMLongBench-Doc directly reports that most evaluated LVLMs underperform LLMs supplied with lossy OCR text, with GPT-4o and GPT-4V as exceptions. MMDocRAG tests a different representation choice and finds detailed VLM-generated descriptions of visual evidence outperform OCR alone. LongDocURL tests parsing representations and finds structure-preserving Docmind text outperforming PyMuPDF text. These results do not establish a strict contradiction because the alternatives are not the same: native vision-language processing, visually enriched textual descriptions, and structure-preserving parsing are distinct interventions."
  }
 ],
 "gaps": [
  {
   "id": "gap-1",
   "description": "The corpus still does not establish a complete method for maintaining evidence provenance across successive workplace attachment revisions, including stable attachment identity, version-relative source locations, semantic changes between versions, and lineage from an older cited region to its later counterpart. Version-aware retrieval, scientific-PDF element alignment, XML persistent identity, spreadsheet-version clustering, and evolving-document QA with document/page/passage/update-status provenance demonstrate separate components, but exact multimodal old-to-new region or cell lineage remains unvalidated.",
   "classification": "ACADEMIC",
   "priority": "HIGH",
   "suggested_query": "\"document version alignment\" multimodal provenance region lineage semantic change revised document attachments"
  },
  {
   "id": "gap-2",
   "description": "Direct grounding of workplace-message referring expressions such as \"this screenshot\", \"the highlighted row\", \"numbers below\", or \"use attachment v2\" into attachment objects, pages, cells, or regions remains unvalidated. Scene-text grounding, situated-dialogue coreference, omitted-reference annotation, and GUI grounding provide adjacent-domain evidence but do not evaluate workplace-message-to-versioned-attachment grounding.",
   "classification": "ACADEMIC",
   "priority": "HIGH",
   "suggested_query": "\"referring expression grounding\" document multimodal attachment table cell screenshot coreference email"
  },
  {
   "id": "gap-3",
   "description": "Comprehensive spreadsheet understanding remains open for formulas, hidden rows and sheets, cross-sheet references, merged regions, formatting semantics, units, named ranges, and provenance across revised workbook versions. Current studies address retrieval, structure reconstruction, verification, dependency visualization, workflow completion, and within-state cell provenance but not this complete set.",
   "classification": "ACADEMIC",
   "priority": "HIGH",
   "suggested_query": "\"spreadsheet understanding\" workbook formulas hidden sheets named ranges merged cells cross-sheet provenance version"
  },
  {
   "id": "gap-4",
   "description": "No admitted paper validates one end-to-end provenance representation that jointly identifies attachment version, page, document element, exact region or spreadsheet cell, and answer span. Hierarchical document-region evidence addresses, cell-level table evidence, version-aware retrieval, and evolving-document page/passage/update-status citations cover overlapping subsets, but their combination remains untested.",
   "classification": "ACADEMIC",
   "priority": "HIGH",
   "suggested_query": "\"evidence provenance\" document question answering version page region cell answer span multimodal grounding"
  },
  {
   "id": "gap-5",
   "description": "End-to-end behavior when extraction or grounding is unsupported, incomplete, or wrong remains insufficiently exercised. The corpus contains unanswerable-question evaluation and parser, retrieval, OCR, localization, attribution, and grounding failure analyses, but not a complete engineering contract distinguishing genuine evidence absence from parser, OCR, layout, retrieval, or grounding failure.",
   "classification": "ENGINEERING",
   "priority": "HIGH"
  },
  {
   "id": "gap-6",
   "description": "Robustness of candidate extraction and structural-preservation pipelines on heterogeneous workplace-style documents remains an engineering gap. No admitted benchmark jointly exercises sparse tables, merged and hierarchical structures, OCR corruption, irregular reading order, embedded visual objects, scanned pages, and explicit extraction-completeness accounting.",
   "classification": "ENGINEERING",
   "priority": "HIGH"
  },
  {
   "id": "gap-7",
   "description": "Operational scaling remains open for long documents, large tables, and realistic workbooks. The corpus reports page-routing costs, evidence-graph overhead, parsing limits, workbook inspection failures, token and runtime trade-offs, and change-detection costs, but does not close system-level latency, memory, and throughput for the target workload.",
   "classification": "ENGINEERING",
   "priority": "MEDIUM"
  },
  {
   "id": "gap-8",
   "description": "The corpus lacks one evaluation that simultaneously measures semantic correctness, extraction completeness, exact provenance, unsupported-evidence handling, and preservation of tables, images, document hierarchy, and reading order on workplace-style attachments. Existing benchmarks and metrics evaluate overlapping subsets rather than this complete combination.",
   "classification": "ENGINEERING",
   "priority": "HIGH"
  }
 ],
 "actionable_insights": [
  "Synthesis-derived recommendation: represent source provenance as composable levels rather than one opaque citation, keeping attachment/version identity, page or sheet identity, element identity, region or cell location, and answer-span linkage as separately inspectable fields.",
  "Synthesis-derived recommendation: keep version identity separate from within-version coordinates so that a cell, page region, or element location is always interpreted relative to an explicit attachment version.",
  "Synthesis-derived recommendation: treat cross-version element matching as an explicit lineage relation with confidence and change metadata rather than silently reusing old coordinates after a revision.",
  "Synthesis-derived recommendation: preserve native spreadsheet addresses, sheet names, formulas, merged-range information, hidden-state metadata, named ranges, formatting cues, and embedded-object identifiers before any flattened textual representation is produced.",
  "Synthesis-derived recommendation: evaluate message-to-attachment reference grounding separately from downstream proposition or response-scope reasoning, and include explicit unresolved and ambiguous outcomes when more than one target remains defensible.",
  "Synthesis-derived recommendation: construct engineering fixtures in which parser failure, OCR failure, page omission, table-structure corruption, retrieval miss, grounding miss, true evidence absence, and multiple-valid-evidence cases are distinguishable in the gold data.",
  "Synthesis-derived recommendation: measure answer correctness and provenance correctness independently and add an end-to-end metric that only credits a result when both the semantic answer and its source lineage are valid.",
  "Synthesis-derived recommendation: benchmark operational scaling with realistic multi-sheet workbooks and long mixed-modality attachments while retaining the same provenance and completeness checks used in smaller correctness tests."
 ],
 "confidence_summary": "Confidence is HIGH that the corpus supports well-supported design principles around preserving spatial and structural information, separating answer correctness from evidence correctness, and retaining explicit within-document provenance. Confidence is MEDIUM for transfer from scientific PDFs, XML versioning, GUI grounding, scene-text grounding, situated dialogue, and benchmark spreadsheets to workplace-message attachments because those domains do not directly evaluate the target setting. Evidence for cross-version provenance is substantial at the component level but fragmented across different representations and tasks. No admitted study validates the complete revised-workbook lineage or workplace-message-to-versioned-attachment grounding problem, so confidence that the literature closes those target-domain questions is LOW.",
 "limitations": [
  "The 53 supplied analysis records represent 52 distinct studies because manual-1048d6caf2 and doi-10-1109-tmm-2022-3219642 are two records of the same Scene-Text Oriented Referring Expression Comprehension study; they are not counted as independent corroboration.",
  "The corpus is heterogeneous: it includes scientific PDFs, clinical guidelines, XML stores, web tables, business-document images, GUI screenshots, charts, situated dialogue, synthetic or benchmark spreadsheets, and long-document QA. Transfer findings from these domains do not establish production workplace-email accuracy.",
  "Several studies evaluate synthetic data, curated benchmarks, or benchmark-specific adaptations. Those results support mechanisms and evaluation ideas but not representativeness of real workplace attachments.",
  "The supplied analyses do not provide one direct experiment covering revised workbook identity, cell-level old-to-new correspondence, semantic change classification, and persistent provenance together.",
  "The supplied analyses do not evaluate natural workplace-message expressions that refer directly to attachment versions, spreadsheet cells, highlighted rows, screenshots, or document regions.",
  "Some manual records provide less quantitative detail than full paper analyses, limiting cross-paper numerical comparison.",
  "Inherited handoffs from Topics 04, 05, and 06 are project context only. They were not used as evidence for findings or to claim closure of any gap.",
  "Differences in benchmarks, evaluation metrics, model families, document lengths, and evidence annotations make many apparent disagreements scope qualifications rather than strict contradictions."
 ],
 "gap_status": [
  {
   "id": "gap-1",
   "status": "open",
   "note": "The corpus now includes evolving-document QA that carries document/page/passage/update-status provenance and reports temporal drift only when retrieved passages explicitly evidence a change. Together with PDF alignment, XML persistent identity, version-aware RAG, and spreadsheet-version clustering, this strengthens component coverage but still does not establish exact cross-version region or cell correspondence and old-to-new multimodal element lineage for workplace attachments.",
   "evidence": [
    "2609.08364",
    "2607.14117",
    "manual-ae200642f8",
    "2510.08109",
    "1704.08476"
   ]
  },
  {
   "id": "gap-2",
   "status": "open",
   "note": "Adjacent-domain grounding studies cover scene text, GUI regions, visual dialogue, pronouns, omitted references, and region targets, but none directly evaluates workplace-message references into versioned attachment objects, pages, rows, cells, or document regions.",
   "evidence": [
    "doi-10-18653-v1-2025-acl-long-547",
    "manual-d896e242a6",
    "manual-bc798b0eed",
    "2404.05719",
    "doi-10-1109-tmm-2022-3219642"
   ]
  },
  {
   "id": "gap-3",
   "status": "open",
   "note": "Spreadsheet retrieval, structural reconstruction, verification, dependency analysis, workflow execution, and within-state provenance are demonstrated, but the supplied corpus does not jointly validate formulas, hidden structures, merged ranges, formatting semantics, units, named ranges, cross-sheet relations, and provenance across revised workbook versions.",
   "evidence": [
    "2601.08741",
    "2604.12282",
    "2606.29955",
    "2010.12537",
    "doi-10-1109-icse-2012-6227171"
   ]
  },
  {
   "id": "gap-4",
   "status": "open",
   "note": "Document/page/region evidence addresses, answer-span grounding, table-cell selection, version-aware retrieval, and document/page/passage/update-status citations are each demonstrated in subsets, but no admitted study evaluates a single hierarchy spanning attachment version through page or sheet, element, exact region or cell, and answer span.",
   "evidence": [
    "2605.12882",
    "manual-0661fc0cba",
    "doi-10-18653-v1-2020-acl-main-398",
    "2510.08109",
    "2609.08364"
   ]
  },
  {
   "id": "gap-5",
   "status": "open",
   "note": "The corpus analyzes unanswerable cases and multiple retrieval, parsing, localization, and attribution failures, but does not provide the requested end-to-end failure contract that distinguishes evidence absence from failures at each processing stage.",
   "evidence": [
    "2511.12003",
    "2607.24651",
    "2606.15906",
    "2606.29955",
    "2404.19024"
   ]
  },
  {
   "id": "gap-6",
   "status": "open",
   "note": "Individual benchmarks cover sparse or complex tables, OCR-derived documents, reading-order variation, scanned images, and mixed visual content, but no single admitted evaluation jointly exercises all listed workplace-style structural failure modes with explicit completeness accounting.",
   "evidence": [
    "2111.07129",
    "2203.09056",
    "doi-10-1007-3-540-48172-9-21",
    "doi-10-1007-s00521-022-06948-5",
    "2407.01523"
   ]
  },
  {
   "id": "gap-7",
   "status": "open",
   "note": "Several papers quantify document-length degradation, page-exploration cost, graph-controller overhead, token use, runtime, and workbook-scale failures, but they do not establish target-workload latency, memory, and throughput end to end.",
   "evidence": [
    "2404.19024",
    "2604.13731",
    "2606.15906",
    "2510.08109",
    "2606.29955"
   ]
  },
  {
   "id": "gap-8",
   "status": "open",
   "note": "CiteVQA, SMuDGE, MMLongBench-Doc, LongDocURL, table benchmarks, and spreadsheet benchmarks measure important overlapping dimensions, but no one admitted evaluation simultaneously measures semantic correctness, completeness, exact provenance, unsupported-evidence behavior, multimodal preservation, document hierarchy, and reading order in workplace-style attachments.",
   "evidence": [
    "2605.12882",
    "doi-10-18653-v1-2025-findings-naacl-295",
    "2407.01523",
    "2412.18424",
    "2606.29955"
   ]
  }
 ]
}

Per-paper analyses (reduced to questions and top findings to fit the size cap):
[
 {
  "paper_id": "1704.08476",
  "title": "SpreadCluster: Recovering Versioned Spreadsheets through Similarity-Based Clustering",
  "research_question": "Can spreadsheet versions whose explicit version history has been lost be recovered reliably by clustering spreadsheets according to structural and textual similarities in their worksheets and table headers?",
  "key_findings": [
   "On the Enron evaluation, SpreadCluster produced 1,561 candidate evolution groups, of which 1,226 were manually validated as correct, corresponding to 78.5% precision.",
   "Against the constructed Enron ground truth of 1,609 evolution groups, SpreadCluster achieved 70.7% recall and a 74.4% F-measure.",
   "The filename-based comparison method achieved 59.8% precision, 48.7% recall, and 53.7% F-measure on the same evaluation, substantially below the reported SpreadCluster metrics.",
   "The learned worksheet- and spreadsheet-level similarity thresholds were 0.60 and 0.33 respectively after threshold search on the curated training data.",
   "On EUSES the method reported 170 correct groups among 213 detected groups, or 79.8% precision, while a manually inspected sample of 200 FUSE groups produced 91.0% precision."
  ]
 },
 {
  "paper_id": "1911.10683",
  "title": "Image-based table recognition: data, model, and evaluation",
  "research_question": "How can complex tables in document images be converted into structured machine-readable representations while jointly recognizing table structure and cell content and evaluating both types of error appropriately?",
  "key_findings": [
   "PubTabNet contains about 568,000 table images paired with structured HTML and provides large-scale supervision for both table structure and cell content recognition.",
   "TEDS reacts more appropriately than the adjacency-relation metric to multi-hop cell shifts and graded OCR errors because it evaluates the complete table tree and uses content-sensitive substitution costs.",
   "EDD achieved 88.3% average TEDS on the PubTabNet test set, compared with 78.6% for WYGIWYS, an absolute improvement of 9.7 percentage points.",
   "EDD obtained 91.2% TEDS on simple tables and 85.4% on complex tables, and its advantage over WYGIWYS was slightly larger for complex tables.",
   "On the separate synthetic benchmark, EDD achieved at least 99.7% TEDS in each of four table categories and higher exact-match rates than TIES in every category."
  ]
 },
 {
  "paper_id": "2006.14806",
  "title": "TURL: Table Understanding through Representation Learning",
  "research_question": "Can a structure-aware pretrained representation model for relational Web tables support a broad range of table interpretation and augmentation tasks with limited task-specific fine-tuning?",
  "key_findings": [
   "TURL achieved the best reported F1 among the compared systems on WikiGS and the authors' held-out entity-linking test set, with F1 scores of 67 and 68 respectively.",
   "Raw TURL fine-tuning did not lead the T2D entity-linking benchmark: it scored 78 F1 versus 83 for Hybrid II, while a simple reweighting variant increased TURL to 82 F1.",
   "For column type annotation, TURL with fine-tuning achieved 94.75% F1, substantially above the listed Sherlock baseline at 78.47%.",
   "For row population, TURL obtained MAP values of 40.92 with no seed entity and 48.31 with one seed entity, compared with 17.90 and 42.31 for EntiTables under the same candidate-recall settings.",
   "For cell filling, TURL obtained precision of 54.80% at rank 1 and 90.98% at rank 10, higher than the compared Exact, H2H, and H2V methods."
  ]
 },
 {
  "paper_id": "2010.12537",
  "title": "TUTA: Tree-based Transformers for Generally Structured Table Pre-training",
  "research_question": "Can a Transformer pretrained with explicit spatial and hierarchical table structure learn transferable representations for generally structured tables rather than being restricted to simple relational tables?",
  "key_findings": [
   "TUTA achieved 88.1% average macro-F1 across four cell-type-classification datasets, at least 3.8 percentage points above the compared baselines.",
   "On WCC table-type classification, TUTA reached 87.6% macro-F1, exceeding the compared baselines by at least four percentage points.",
   "Restricting attention to progressively smaller tree-structured neighborhoods improved both cell- and table-level classification relative to global attention.",
   "Adding tree-position embeddings raised average cell-type macro-F1 from 85.3% for the strongest tree-attention-only base variant to 88.1% for TUTA with implicit tree positions.",
   "Removing any of the three pretraining objectives reduced downstream accuracy, with Cell-Level Cloze particularly important for cell classification and Cell-Level Cloze and Table Context Retrieval causing large drops in table-type classification when removed."
  ]
 },
 {
  "paper_id": "2104.12756",
  "title": "InfographicVQA",
  "research_question": "How effectively can visual-question-answering systems understand infographics that require joint reasoning over embedded text, document layout, graphics, tables, visualizations, and elementary numerical operations?",
  "key_findings": [
   "InfographicVQA exposes a large gap between humans and contemporary VQA/document models, with human test performance of 0.980 ANLS and 95.70% accuracy while the evaluated learned baselines are much lower.",
   "More than three quarters of questions have an answer available either in the common-answer vocabulary or as an OCR span, but locating and reasoning over the relevant content remains difficult for the evaluated models.",
   "In-domain pre-training substantially improves the LayoutLM-based baseline.",
   "Generic natural-image and document-layout object detectors produce relatively few useful detections on infographic images.",
   "For the M4C experiments, using no detected objects or one full-image feature performs better than using bottom-up object regions."
  ]
 },
 {
  "paper_id": "2106.11539",
  "title": "DocFormer: End-to-End Transformer for Document Understanding",
  "research_question": "Can an end-to-end transformer that jointly represents textual, visual, and spatial information learn stronger document representations than text-only or less-integrated multimodal architectures?",
  "key_findings": [
   "Combining image, text, and spatial features improves document entity extraction relative to text-plus-spatial variants on FUNSD and CORD.",
   "Shared spatial embeddings improve FUNSD and CORD performance compared with assigning independent spatial embeddings to language and vision.",
   "The component ablation shows a large gain from adding spatial features to a text model and an additional gain from multimodal self-attention.",
   "Pre-training is especially important in low-data document tasks, with very large degradation on FUNSD and CORD when pre-training is removed.",
   "DocFormer matches or exceeds the compared state of the art across the four evaluated datasets while often using fewer parameters than large competing models."
  ]
 },
 {
  "paper_id": "2111.07129",
  "title": "Visual Understanding of Complex Table Structures from Document Images",
  "research_question": "How can a document-image system recover complex table cells, including empty cells and spanning relationships, while remaining robust to strict spatial-overlap requirements?",
  "key_findings": [
   "Across the benchmark datasets considered by the authors, the proposed framework improved previous state-of-the-art performance by an average of 2.7 percentage points in F1.",
   "TUCD contributes 4,500 manually annotated business-table images from annual reports, including multiple languages, empty cells, and cell boxes designed to preserve alignment constraints.",
   "On UNLV and ICDAR-2013, where empty cells averaged 12.3% of cells, the proposed method outperformed TabStruct-Net by 4.2 percentage points in F1.",
   "The proposed detector retained a much larger advantage over TabStruct-Net as the IoU threshold became stricter; at IoU 0.7 its structure-recognition F1 values were 0.868, 0.852, 0.823, and 0.839 on FinTabNet, ICDAR-13, SciTSR, and TUCD respectively, compared with 0.704, 0.720, 0.682, and 0.722 for the baseline.",
   "Representing structure with rectilinear relationships enables the system to derive row and column spanning information while retaining explicit spatial cell boxes, making the representation more suitable for grounding extracted table structure back to image regions."
  ]
 },
 {
  "paper_id": "2203.09056",
  "title": "Robust Table Detection and Structure Recognition from Heterogeneous Document Images",
  "research_question": "Can a unified visual pipeline robustly detect tables and recover their row, column, and spanning-cell structure across heterogeneous, distorted, curved, and sparsely ruled document images?",
  "key_findings": [
   "The CornerNet-plus-Fast-R-CNN detector achieves a weighted-average F1 of 94.9% on cTDaR TrackA, exceeding the comparison methods reported in the table.",
   "On PubLayNet, the ResNet-18 detector reports AP 97.0 over IoU 0.5:0.95 and AP 92.0 at IoU 0.95, indicating particularly accurate localization at strict overlap thresholds.",
   "The structure recognizer reports F1 99.3% on SciTSR and 98.7% on the more complicated SciTSR-COMP subset.",
   "On PubTabNet, the method reports a TEDS-Struct score of 97.0%, above the listed comparison systems.",
   "On the authors' distorted and curved in-house data, weighted-average F1 rises from 63.8% for SPLERGE to 94.6% for the proposed recognizer."
  ]
 },
 {
  "paper_id": "2212.05935",
  "title": "Hierarchical multimodal transformers for Multi-Page DocVQA",
  "research_question": "Can a hierarchical multimodal transformer answer questions over entire multi-page documents while preserving enough page structure to identify the page containing the supporting evidence?",
  "key_findings": [
   "MP-DocVQA contains 46,176 questions over 5,928 documents and 47,952 page images, creating a substantially longer-input document-QA setting than single-page DocVQA.",
   "In the realistic multi-page setting, Hi-VT5 achieved 48.28 answer accuracy, 0.6201 ANLS, and 79.23% answer-page accuracy, outperforming the evaluated multi-page baseline configurations.",
   "Conventional concatenation baselines suffer increasingly when the answer occurs late in a document, whereas the performance gap in favor of Hi-VT5 becomes larger for later answer-page positions.",
   "Hierarchical denoising pretraining provides the largest answering boost in the ablation study: removing it drops accuracy from 48.28 to 42.10 and ANLS from 0.6201 to 0.5864.",
   "Joint page identification provides provenance useful for diagnosing unsupported answers: the authors observe cases where an answer is correct but the predicted evidence page is wrong, indicating reliance on learned prior bias rather than the actual source page."
  ]
 },
 {
  "paper_id": "2401.00908",
  "title": "DocLLM: A layout-aware generative language model for multimodal document understanding",
  "research_question": "Can a causal language model gain strong visually rich document understanding by incorporating OCR-derived spatial layout directly into attention, without relying on a heavyweight image encoder?",
  "key_findings": [
   "DocLLM-7B outperforms the compared state-of-the-art LLM baselines on 14 of the 16 datasets in the same-dataset evaluation setting.",
   "The model generalizes successfully on four of five previously unseen dataset settings, with reported improvements of roughly 15% to 61% for the Llama2-7B-based model on four of those five datasets.",
   "Ablation results show that text-only self-attention has the lowest pre-training next-token-prediction accuracy, while adding spatial interactions improves it; the best reported spatial-attention configuration reaches 39.12 versus 35.43 for text-only attention.",
   "Block infilling with spatial information reaches 39.1 next-token-prediction accuracy in the ablation, compared with 36.2 for causal learning with spatial information and 32.6 for plain causal learning.",
   "A causal decoder performs comparably to, and slightly better than, the tested prefix decoder configurations, so the authors retain the causal architecture."
  ]
 },
 {
  "paper_id": "2404.05719",
  "title": "Ferret-UI: Grounded Mobile UI Understanding with Multimodal LLMs",
  "research_question": "Can a multimodal large language model be adapted to high-resolution mobile user interfaces so that it both understands UI semantics and precisely grounds referring expressions to screen regions?",
  "key_findings": [
   "Specialized UI instruction tuning transforms the general Ferret model into a substantially stronger model for both referring and grounding of mobile-screen elements.",
   "Ferret-UI outperforms GPT-4V on the paper's elementary UI categories, including several referring and grounding evaluations, while GPT-4V scores higher on the advanced conversational categories evaluated by a GPT-4 judge.",
   "The any-resolution architecture improves several high-resolution UI results, most notably the reported iPhone advanced-task aggregate, but its benefit is not uniform across platforms.",
   "In manually checked grounded conversations, Ferret-UI's predicted bounding boxes achieve 91.7% accuracy versus 93.4% for GPT-4V when GPT-4V is allowed to choose from predefined candidate boxes.",
   "Adding elementary referring and grounding supervision improves performance on advanced UI-understanding tasks, indicating that explicit low-level grounding supervision benefits higher-level reasoning."
  ]
 },
 {
  "paper_id": "2404.19024",
  "title": "Multi-Page Document Visual Question Answering using Self-Attention Scoring Mechanism",
  "research_question": "Can an OCR-free visual question-answering system select the page containing answer evidence from a long multi-page document using a lightweight self-attention scoring module while retaining competitive answer accuracy?",
  "key_findings": [
   "The proposed scorer achieves 81.55% page-selection accuracy on the original MP-DocVQA test set while remaining OCR-free.",
   "The system reaches ANLS 0.6199 on the original test set, essentially matching the strongest reported competing multi-page result while using a smaller OCR-free architecture.",
   "Selecting the first output vector from the self-attention scorer performs slightly better than the alternative aggregation strategies evaluated in the ablation study.",
   "When evaluation expands from truncated documents to complete documents of up to 793 pages, test page-selection accuracy falls from 81.55% to 60.45% and ANLS falls from 0.6199 to 0.5394.",
   "Some questions remain answerable even when the model selects a page different from the annotated evidence page; this occurs more often in the extended-document setting and reveals ambiguity in single-positive-page ground truth."
  ]
 },
 {
  "paper_id": "2407.01523",
  "title": "MMLongBench-Doc: Benchmarking Long-context Document Understanding with Visualizations",
  "research_question": "How well can current vision-language and language models understand long multimodal documents when answering questions that require evidence localization, cross-page reasoning, multiple document modalities, and resistance to hallucination?",
  "key_findings": [
   "The benchmark explicitly preserves page-level provenance and evidence-source type for answers, covering text, layout, tables, charts, and images.",
   "Long-document understanding remains difficult: the best evaluated LVLM, GPT-4o, achieves 44.9% overall F1, compared with a 66.0% human F1 baseline.",
   "Cross-page questions are substantially represented and models generally perform worse on cross-page than single-page questions, demonstrating difficulty gathering and reasoning over evidence distributed across pages.",
   "Most evaluated LVLMs perform worse than LLM counterparts supplied with lossy OCR text, although GPT-4o and GPT-4V are exceptions.",
   "OCR-based LLM pipelines are competitive on text and table questions but comparatively weak on chart- and image-dependent questions, showing that flattening documents to text can discard important multimodal evidence."
  ]
 },
 {
  "paper_id": "2410.05243",
  "title": "Navigating the Digital World as Humans Do: Universal Visual Grounding for GUI Agents",
  "research_question": "Can a GUI agent relying only on screenshots and pixel-level actions achieve robust cross-platform operation when a specialized model grounds diverse referring expressions directly to interface coordinates?",
  "key_findings": [
   "On ScreenSpot in the standard grounding setting, the original UGround achieved 73.3 average accuracy versus 53.4 for SeeClick.",
   "With GPT-4o-generated referring expressions in the ScreenSpot agent setting, UGround achieved 81.4 average grounding accuracy versus 52.3 for SeeClick.",
   "Web-derived synthetic grounding data generalized across platforms, including desktop interfaces that were absent from the original UGround training data.",
   "With only 50,000 training screenshots, representing about 600,000 elements, UGround already exceeded SeeClick by more than 10 percentage points in the reported scaling study.",
   "Including positional referring expressions improved ScreenSpot grounding relative to removing positional referring expressions, especially in the standard setting."
  ]
 },
 {
  "paper_id": "2412.18424",
  "title": "LongDocURL: a Comprehensive Multimodal Long Document Benchmark Integrating Understanding, Reasoning, and Locating",
  "research_question": "Can a long-document benchmark jointly evaluate multimodal understanding, numerical reasoning, and cross-element evidence locating across structurally complex documents and long contexts?",
  "key_findings": [
   "LongDocURL explicitly evaluates locating relationships among document elements in addition to conventional understanding and numerical reasoning.",
   "The benchmark contains substantial distributed evidence: 52.9% of questions use multiple evidence pages and 37.1% use more than one document-element type.",
   "Current models remain well below the human baseline, with GPT-4o scoring 64.5 generalized accuracy overall versus 84.8 for human experts on the sampled human evaluation.",
   "Table questions are particularly difficult, which the authors identify as evidence of deficiencies in document-structure parsing.",
   "Preserving table structure during document parsing has a large effect on downstream QA performance: text parsed with the structure-preserving Docmind representation substantially outperforms PyMuPDF text for both proprietary and open-source models."
  ]
 },
 {
  "paper_id": "2503.23131",
  "title": "RefChartQA: Grounding Visual Answer on Chart Images through Instruction Tuning",
  "research_question": "Can chart question-answering models be instruction-tuned to return both an answer and the precise chart elements supporting that answer, and does this explicit spatial grounding improve answer reliability?",
  "key_findings": [
   "Manual checking of 50 samples from each split by two annotators yielded 93.45% agreement on grounding correctness, while also revealing cases with multiple defensible grounding regions.",
   "Grounding instruction tuning produced large answer-accuracy gains for some models: TinyChart improved by 17.42 points on the human split and 15.36 on the PoT split, while Qwen-VL-Chat improved by 22.94 points on the PoT split.",
   "A universal claim that grounding always improves answer accuracy is contradicted by Table 2: UniChart loses accuracy on all three splits, ChartGemma loses substantially on the human and PoT splits, and Qwen2.5-VL declines on the human and machine-generated splits.",
   "Grounding becomes substantially harder as reasoning complexity increases: reported P@FI is roughly 70-84% on mostly simple machine-generated questions, about 40-70% on PoT questions, and about 22-50% on human-authored questions.",
   "Correct visual localization does not guarantee a correct answer because models sometimes identify the right chart elements but fail at the subsequent mathematical reasoning."
  ]
 },
 {
  "paper_id": "2505.16470",
  "title": "Benchmarking Retrieval-Augmented Multimomal Generation for Document Question Answering",
  "research_question": "How well do current retrievers, language models, and vision-language models perform on retrieval-augmented document question answering when correct answers require selecting and integrating noisy textual and visual evidence across long multi-page documents?",
  "key_findings": [
   "MMDocRAG contains 4,055 questions, of which 52% require evidence from multiple pages, 39.2% involve multiple images, and 61.7% require cross-modal evidence, making evidence composition a central part of the benchmark.",
   "GPT-4.1 achieved a 70.2 quote-selection F1 and 4.14 answer-quality score with the 20-quote candidate setting, while many open and smaller models showed substantially weaker evidence selection and answer quality.",
   "Performance is lower on interpretative, multi-page, and multi-image questions than on descriptive or single-page questions, showing that evidence composition remains difficult even when candidate evidence is supplied.",
   "Fine-tuning the evaluated open vision-language models on MMDocRAG development data substantially improves their quote selection and answer generation performance.",
   "Using detailed VLM-generated descriptions of visual evidence outperformed relying on OCR text alone in the reported aggregate comparison, indicating that visual semantics not captured by OCR are useful for retrieval and answering."
  ]
 },
 {
  "paper_id": "2506.21055",
  "title": "Class-Agnostic Region-of-Interest Matching in Document Images",
  "research_question": "Can a visual prompt marking an arbitrary region in one document be used to identify semantically corresponding regions in another document without predefined classes or fixed granularity?",
  "key_findings": [
   "RoI-Matcher achieved 87.3% overall mIoU and 83.9% overall F-measure on RoI-Matching-Bench.",
   "Performance remained strongest across all three benchmark levels, with 92.1% mIoU and 92.2% F-measure at Level I and 85.0% mIoU and 72.3% F-measure at the more difficult Level III.",
   "The reported overall results exceeded the multimodal-model baselines Qwen2-VL-7B at 57.3% mIoU and 55.3% F-measure and InternVL2.5-8B at 53.2% and 50.5%.",
   "The paper reports inference time of 0.056 seconds per image for RoI-Matcher versus 3.121 seconds per image for Qwen2-VL-7B.",
   "Replacing cross-entropy plus Dice loss with PANLoss raised F-measure from 66.8% to 83.0% in the loss ablation while mIoU changed from 85.4% to 85.9%."
  ]
 },
 {
  "paper_id": "2510.08109",
  "title": "VersionRAG: Version-Aware Retrieval-Augmented Generation for Evolving Documents",
  "research_question": "Can retrieval-augmented generation explicitly represent document versions and changes so that questions about historical content, version identity, and inter-version differences are answered more accurately and efficiently than version-agnostic RAG?",
  "key_findings": [
   "With DeepSeek-R1 70B, VersionRAG achieved 90% overall accuracy on VersionQA, compared with 58% for naive RAG and 64% for the evaluated GraphRAG baseline.",
   "VersionRAG achieved 100% accuracy on the evaluated version-specific content retrieval and version-listing categories with the strongest evaluated model, showing a large advantage on questions that require explicit version identity.",
   "Change-oriented questions remained substantially harder than ordinary content or version questions; the strongest configuration reached 70% change-query accuracy, with implicit changes particularly difficult.",
   "For DeepSeek-R1 70B, VersionRAG used about 186K input tokens and 38K output tokens compared with roughly 2.97M input and 5.92M output tokens for GraphRAG, corresponding to the paper's reported 97% token reduction and substantially lower cost and runtime.",
   "The reported VersionRAG failures were attributed mainly to query misclassification and incomplete change extraction, demonstrating error propagation across the modular pipeline."
  ]
 },
 {
  "paper_id": "2511.12003",
  "title": "Look as You Think: Unifying Reasoning and Visual Evidence Attribution for Verifiable Document RAG via Reinforcement Learning",
  "research_question": "Can a vision-language model be trained to produce accurate document-RAG answers while grounding intermediate reasoning steps and final answers to verifiable page-level visual regions with limited stepwise supervision?",
  "key_findings": [
   "Across the reported single- and multi-image evaluations, LAT improves the vanilla model by an average of 8.23% in soft exact match and 47.0% in IoU@0.5.",
   "In the in-domain comparison, LAT reports gains of 7.95% in answer exact match and 44.6% in IoU@0.5 over the vanilla model.",
   "LAT substantially improves stepwise Chain-of-Evidence attribution quality, with a reported 37.5% gain in stepwise attribution compared with only a 4.0% gain from adding an in-context CoE demonstration.",
   "For unanswerable multi-image cases, LAT reports average precision of 65% when producing a no-answer response.",
   "LAT outperforms the direct supervised answer-plus-attribution baseline and shows stronger cross-domain generalization in the reported experiments."
  ]
 },
 {
  "paper_id": "2601.08741",
  "title": "From Rows to Reasoning: A Retrieval-Augmented Multimodal Framework for Spreadsheet Understanding",
  "research_question": "Can a retrieval-first multimodal architecture reason accurately and audibly over large multi-sheet spreadsheets by indexing and retrieving fine-grained spreadsheet evidence instead of placing an entire workbook into the model context?",
  "key_findings": [
   "On FRTR-Bench, hybrid Reciprocal Rank Fusion retrieval reaches 0.74 answer accuracy compared with 0.59 for vector-only retrieval and 0.42 for lexical-only retrieval.",
   "Combining row, column, window, and image retrieval units reaches 0.74 accuracy, compared with 0.52 for rows only, 0.18 for columns only, and 0.58 for windows only, supporting the value of multi-granular spreadsheet indexing.",
   "On FRTR-Bench, the reported FRTR configuration reaches 0.74 accuracy while the paper's SpreadsheetLLM comparison reaches 0.24, although this comparison reflects the authors' adaptation and benchmark setup rather than SpreadsheetLLM's own original benchmark conditions.",
   "On the SpreadsheetLLM benchmark, FRTR is competitive but does not exceed SpreadsheetLLM in raw accuracy for the strongest models; for example, the reported GPT-5 results are 0.87 for FRTR and 0.90 for SpreadsheetLLM.",
   "The benchmark and retrieval pipeline retain explicit within-workbook provenance through sheet locations, cell references, formulas, and image identifiers, but this provenance addresses a particular workbook state rather than lineage across workbook revisions."
  ]
 },
 {
  "paper_id": "2604.12282",
  "title": "Towards Robust Real-World Spreadsheet Understanding with Multi-Agent Multi-Format Reasoning",
  "research_question": "Can robust real-world spreadsheet understanding be improved by incrementally extracting and verifying a multimodal structural representation before performing query-specific reasoning?",
  "key_findings": [
   "SpreadsheetAgent with Qwen3-Coder-480B-A35B reached 41.67% soft accuracy on SpreadsheetBench, exceeding the previously reported ChatGPT Agent result of 35.27% cited by the authors.",
   "The framework improved spreadsheet-question performance across model scales, including an improvement of more than 11 percentage points for Qwen3-Coder-480B relative to the corresponding setup without the full framework.",
   "Verification contributes measurable value: in the reported ablation, the full configuration achieved 22.37% soft and 18.42% hard accuracy, while removing verification reduced performance to 20.44% and 15.69%.",
   "Explicit structural sketches in YAML or JSON improve reasoning compared with omitting the structured representation.",
   "A stronger extraction model improves downstream reasoning even when the reasoning model is held fixed, indicating that accurate workbook-structure reconstruction is an important bottleneck."
  ]
 },
 {
  "paper_id": "2604.13731",
  "title": "Doc-V*: Coarse-to-Fine Interactive Visual Reasoning for Multi-Page Document VQA",
  "research_question": "Can an OCR-free document agent improve long multi-page visual question answering by actively navigating from coarse document overviews to selectively retrieved high-resolution evidence rather than consuming all pages or a fixed retrieval set?",
  "key_findings": [
   "The GRPO-trained Doc-V* scored 64.5 on DUDE, 86.2 on MPDocVQA, 77.2 on SlideVQA, 42.1 on MMLongBench-Doc, and 56.3 on LongDocURL, exceeding the corresponding Qwen2.5-VL baseline on every benchmark.",
   "The paper reports an out-of-domain improvement of up to 47.9% over its static RAG baseline.",
   "On MMLongBench-Doc, the full SFT agent achieved 39.8 accuracy while examining 6.4 pages on average; removing retrieval reduced accuracy to 34.9 and increased exploration to 14.2 pages, while removing direct fetching reduced accuracy to 35.2.",
   "Page-level analysis shows complementary behavior: semantic retrieval has higher recall and generally lower precision, while direct page fetching supplies more targeted evidence.",
   "Returned high-resolution page observations are explicitly prefixed with absolute page identifiers, preserving an unambiguous page-to-evidence mapping even when pages are fetched out of order."
  ]
 },
 {
  "paper_id": "2605.12882",
  "title": "CiteVQA: Benchmarking Evidence Attribution for Trustworthy Document Intelligence",
  "research_question": "How can document visual question answering be evaluated so that a model receives credit only when its answer is correct and its cited document region genuinely supports that answer?",
  "key_findings": [
   "CiteVQA demonstrates a substantial gap between answer correctness and faithful evidence attribution: the strongest evaluated system reports 76.0 Strict Attributed Accuracy despite an 86.1 answer score, while the strongest open-source model reports 22.5 SAA.",
   "Evidence attribution becomes more difficult as document scope increases; for the strongest system, reported evidence recall decreases from 68.9 in the single-document setting to 55.3 in the multi-document multiple-gold setting.",
   "Restricting models to ground-truth pages or gold documents improves answer accuracy in the paper's oracle-style analyses, providing preliminary evidence that evidence localization is itself an important performance bottleneck rather than merely an explanation layer.",
   "The benchmark provides a hierarchical spatial evidence address consisting of document index, page index, and element bounding box, and its multi-document synthesis pipeline maintains a mapping from synthetic evidence back to source-PDF coordinates.",
   "A human study on a sampled subset finds no statistically significant difference between the automated and human assessments for the reported relevance and answer-correctness judging dimensions, supporting the evaluation pipeline's use of automated judges."
  ]
 },
 {
  "paper_id": "2606.15906",
  "title": "MAGE-RAG: Multigranular Adaptive Graph Evidence for Agentic Multimodal RAG in Long-Document QA",
  "research_question": "Can long-document multimodal question answering improve evidence coverage and control irrelevant context by dynamically constructing a query-specific page-and-element evidence subgraph under explicit budgets instead of relying on fixed top-k retrieval?",
  "key_findings": [
   "MAGE-RAG reports 52.75 overall accuracy on LongDocURL and 53.26 accuracy with 51.19 F1 on MMLongBench-Doc, showing that dynamically assembled graph evidence can be competitive with strong long-document multimodal QA baselines.",
   "The framework shows particularly large gains on cross-page questions in MMLongBench-Doc, where its reported cross-page score is 34.70 compared with 24.87 for M3DocRAG and 24.51 for EVisRAG.",
   "Ablations show that fine-grained node rendering and graph-neighbor expansion improve performance over page-only retrieval; graph-neighbor expansion raises the reported MMLongBench-Doc accuracy/F1 to 53.88/50.20 from 48.75/45.71 for the top-k page-only configuration.",
   "The evidence representation preserves within-document provenance through page identifiers, element nodes, bounding boxes, image references, and page-node alignment, allowing the final reader input and controller trajectory to be inspected at multiple granularities.",
   "The paper explicitly identifies offline parsing and evidence-graph quality as an upper bound on the system and notes that the controller adds evaluator calls and state-management cost, making the approach less compelling for short or simple single-hop documents."
  ]
 },
 {
  "paper_id": "2606.29955",
  "title": "SpreadsheetBench 2: Evaluating Agents on End-to-End Business Spreadsheet Workflows",
  "research_question": "How accurately can current spreadsheet agents complete realistic end-to-end business workflows over large, multi-sheet workbooks, and what failure modes limit reliable completion?",
  "key_findings": [
   "SpreadsheetBench 2 contains 321 workflow-level tasks averaging 11.8 worksheets and 593.5 required cell modifications per task, substantially exercising workbook-level structure rather than isolated tables.",
   "The strongest evaluated model, Claude Opus 4.6, achieved only 34.89% overall task accuracy, while six of the eight evaluated models remained below 25%.",
   "High cell-level modification scores did not translate into complete-workbook correctness: Claude Opus 4.6 reached 89.69% modification accuracy but 34.00% task accuracy on financial modeling, and 50.38% versus 12.00% on debugging.",
   "Insufficient workbook inspection and selection of the wrong target cells were identified as dominant failure categories among unsuccessful tasks.",
   "The agent scaffold materially affected end-to-end performance: with GLM-5 on a 50-task subset, the benchmark scaffold reached 15.45% task accuracy compared with 14.20% for Claude Code and 8.66% for both Cline and Kilo."
  ]
 },
 {
  "paper_id": "2607.14117",
  "title": "Heterogeneous Element-Aware Cross-Version Differencing of Scientific Documents via Layout-Aware Alignment and Structure-Aware Reasoning",
  "research_question": "How can two revised scientific PDF versions be aligned and differenced at the element level while preserving layout and internal structure across text, tables, formulas, and figures?",
  "key_findings": [
   "The proposed method achieved detection F1 scores of 0.903 for text, 0.855 for tables, 0.862 for formulas, and 0.845 for figures on the evaluation corpus.",
   "Cross-version alignment was a critical component: removing it reduced detection F1 from 0.866 to 0.779, localization F1 from 0.833 to 0.706, alignment accuracy from 0.856 to 0.681, and matching F1 from 0.859 to 0.692.",
   "Type-specific alignment weights outperformed uniform shared weights, supporting the use of different mixtures of spatial, content, and structural evidence for heterogeneous element types.",
   "Structural modeling produced particularly large gains for table-topology and formula-hierarchy changes, while content signals were comparatively more important for text and figures.",
   "A soft candidate window of plus or minus two pages produced the strongest reported overall alignment results, outperforming same-page-only matching and a wider plus or minus three-page window."
  ]
 },
 {
  "paper_id": "2607.24651",
  "title": "Evidence Attribution in Visual Document Understanding without Coordinates or Region Labels",
  "research_question": "Can visual document question-answering systems provide reliable, spatially grounded evidence attribution without requiring models to emit coordinates or training data with region-level labels?",
  "key_findings": [
   "Replacing direct bounding-box generation with textual evidence quotations substantially increased evidence recall across all six evaluated open VLMs, from a maximum of 8.1% under coordinate output to 25.9%-46.9% under the language interface.",
   "The language interface sharply reduced attribution hallucination rates, from 82.1%-97.0% with coordinate output to 38.6%-65.4% with language-based attribution.",
   "Answer quality was largely preserved when switching attribution interfaces: five of six backbones changed by no more than 2.3 answer-score points, although Qwen3-VL-8B showed a larger decrease before training.",
   "GRPO training without region labels increased Qwen3-VL-8B evidence recall from 39.9% to 51.3%, reduced attribution hallucination from 41.2% to 28.4%, and raised strict attributed accuracy from 22.4% to 33.8%.",
   "Residual failures under the language interface are dominated by cases in which the model does not quote the necessary evidence at all, while parser misses and quote-to-region assignment conflicts impose additional ceilings."
  ]
 },
 {
  "paper_id": "2607.29638",
  "title": "HierDoc: Hierarchical Page-to-Region Evidence Routing for Long-Document Visual Question Answering",
  "research_question": "Can long-document visual question answering improve evidence acquisition by learning page selection and fine-grained region selection as successive hierarchical policies rather than retrieving only pages or treating page and region evidence independently?",
  "key_findings": [
   "The Qwen3-VL-based HierDoc configuration reports 53.62 on MMLongBench-Doc and 65.80 on LongDocURL, alongside competitive results on SlideVQA, PaperTab, and FetaTab.",
   "Adding the learned region-routing stage to the page-only configuration improves the reported MMLongBench-Doc result from 50.8 accuracy and 45.6 F1 to 53.6 accuracy and 47.8 F1 when GRPO and reflection are used.",
   "Training the page selector with GRPO and adding reflection improves page-routing quality and downstream QA relative to the untrained selector in the reported ablation.",
   "Selected visual crops plus selected OCR provide stronger gains than indiscriminately adding all OCR, while removing the full selected pages and retaining only local crops and OCR reduces performance, showing that global page context and local region evidence are complementary.",
   "HierDoc carries hierarchical within-document evidence metadata from physical page to parsed region and bounding box, but its region aliases are sample-local action identifiers rather than persistent identities designed to survive document revisions."
  ]
 },
 {
  "paper_id": "2608.03292",
  "title": "DocTrace: Towards Traceable Long Document VQA via Hierarchical Evidence Graph Reasoning",
  "research_question": "Can long-document visual question answering be made both more accurate and more traceable by explicitly localizing pages, parsing multimodal page elements, and constructing hierarchical evidence graphs whose nodes provide provenance for the generated answer?",
  "key_findings": [
   "DocTrace improved the Qwen3-VL-8B backbone from 38.5% to 52.9% accuracy on MMLongBench-Doc, from 45.1% to 56.4% on LongDocURL, and from 73.4 to 85.1 F1 on SlideVQA after supervised and reinforcement-learning stages.",
   "Explicit structured parsing and evidence-graph reasoning materially contribute to accuracy: removing structured parsing reduced overall MMLongBench-Doc accuracy from 50.3% to 46.6%, while removing the graph reduced it to 47.2%.",
   "Generated traces showed very high structural validity, including 99.5% evidence grounding, 99.6% graph integrity, and 100% acyclicity and answer connectivity in the reported traceability evaluation.",
   "Counterfactual masking changed answers in 82.8% of cases when cited evidence was masked but only 9.6% when uncited context was masked, indicating that the reported citations are behaviorally associated with answer generation.",
   "The authors explicitly caution that counterfactual masking does not prove that the model's hidden computation internally follows the explicit evidence graph as a causal reasoning program."
  ]
 },
 {
  "paper_id": "2609.08364",
  "title": "SentryLine: Evidence-Grounded Question Answering over Evolving Documents in Oncology Care",
  "research_question": "Can a question-answering system reliably answer from evolving clinical guidelines while preserving auditable evidence citations, detecting temporal changes, and adapting responses to clinician and patient roles?",
  "key_findings": [
   "SentryLine represents answer evidence as structured citation items containing the source document, page, passage text, citation key, and update status, and exposes the cited PDF passage for inspection.",
   "Temporal drift is reported only when retrieved passages explicitly document a change across guideline versions, rather than being inferred from unexplained differences.",
   "ASCOBench contains 405 three-turn conversations covering factual, reasoning, contrasting, and role-specific questions, with 105 conversations and 315 questions in the test split.",
   "For reasoning questions, SentryLine achieved 78.1% fully correct with DeepSeek-R1 and 77.1% with Gemini 3.1 Pro, substantially above the corresponding RAG baselines reported by the authors.",
   "For role-specific questions with Gemini 3.1 Pro, SentryLine reached 65.3% fully correct compared with 43.1% for the strongest reported baseline in that comparison."
  ]
 },
 {
  "paper_id": "doi-10-1002-spe-2305",
  "title": "Bridging the gap between tracking and detecting changes on XML",
  "research_question": "Can an XML differencing algorithm be designed for text-centric documents so that its detected changes more closely resemble human-oriented change tracking while retaining acceptable computational performance?",
  "key_findings": [
   "JNDiff obtained the highest aggregate human-oriented quality scores among the evaluated systems on the five document-level quality tests.",
   "On the detailed DL2221 case containing 14 gold-standard changes, JNDiff's aggregate quality score was 25.199, compared with 12.833 for faxma and 13.545 for XyDiff.",
   "The synthetic evaluation starts from 60 heterogeneous XML files and produces 480 files spanning multiple document formats and change ratios, providing broader stress testing than the small manually inspected set.",
   "JNDiff generally produces compact descriptions of changes on text-centric XML and avoids many structurally verbose edits generated by algorithms optimized for data-centric XML.",
   "JNDiff trades execution speed for change-description quality: faxma is faster, JNDiff averaged about 1.1 seconds on the real-document sample, and all evaluated algorithms averaged below two seconds on the synthetic collection."
  ]
 },
 {
  "paper_id": "doi-10-1007-3-540-44503-x-20",
  "title": "Why and Where: A Characterization of Data Provenance",
  "research_question": "How can data provenance be formally separated into explanations of why an output exists and locations showing where an output value originated, and under what query restrictions are those notions preserved by query rewriting?",
  "key_findings": [
   "Why-provenance and where-provenance capture different questions: the former identifies source information sufficient to justify an output's existence, while the latter identifies source locations from which particular output values originate.",
   "The deterministic semistructured model gives every data item a location describable by a unique path, providing an explicit foundation for where-provenance.",
   "The paper's query rewrite system is strongly normalizing, so every well-formed query can be transformed to the specified normal form after finitely many rewrite steps.",
   "The Why procedure is proved sound and complete for computing the witness basis of a singular output value from a normal-form query.",
   "For well-formed queries containing only equality conditions, the minimal witness basis is invariant across equivalent queries, with an extension indicated for certain inequality subclasses."
  ]
 },
 {
  "paper_id": "doi-10-1007-3-540-48172-9-21",
  "title": "The T-Recs Table Recognition and Analysis System",
  "research_question": "Can table structure and page layout be recovered from word-level document segments through bottom-up spatial clustering rather than relying on explicit ruling lines or large whitespace separators?",
  "key_findings": [
   "T-Recs reverses the dominant separator-first strategy of its time by clustering word segments bottom-up into layout structures.",
   "The subsequent table analysis constructs a tile structure representing the intersections of inferred row and column structure.",
   "The system is designed to recognize structures containing row-spanning or column-spanning cells and sparse tables rather than requiring every table position to contain data.",
   "The recognition procedure can operate without relying on textual content, making its layout logic language-independent in principle.",
   "The approach is intended for mixed-mode pages and for noisy OCR-derived documents such as facsimiles rather than only clean, explicitly ruled tables."
  ]
 },
 {
  "paper_id": "doi-10-1007-978-3-540-30480-7-29",
  "title": "Schema-Less, Semantics-Based Change Detection for XML Documents",
  "research_question": "Can semantically corresponding XML elements be matched across successive versions without an external schema even when substantial structural reorganization makes conventional structural matching unreliable?",
  "key_findings": [
   "Semantic identifiers can be inferred from an XML instance without requiring a DTD or XML Schema.",
   "The proposed identifier-construction algorithm has a stated upper bound of O(n log n) for a document tree of size n.",
   "The worked examples show that nodes retaining the same semantic information can be matched even when that information is reorganized into a substantially different XML structure.",
   "Naively attempting every cross-version node pairing is expensive, and the authors estimate whole-document matching at O(P*Q*(P log P + Q log Q)) before applying their heuristic.",
   "When an element type retains the same identifier between versions, comparing evaluated identifier values directly can avoid the more expensive node-territory search."
  ]
 },
 {
  "paper_id": "doi-10-1007-s00521-022-06948-5",
  "title": "Reading order detection on handwritten documents",
  "research_question": "Can document reading order be recovered robustly by learning pairwise ordering relations among previously detected layout elements and then decoding those relations into a global sequence?",
  "key_findings": [
   "FDTD was substantially faster than the Greedy decoder, with Greedy typically taking about an order of magnitude more computation time, while their ordering accuracy remained very similar.",
   "On OHG, the learned decoders achieved normalized Spearman footrule error below 0.7% and required fewer than four swaps per page on average, a 74% reduction in swaps relative to top-bottom-left-right ordering.",
   "On FCR, normalized Spearman footrule error was below 1%, and the average 16.1 swaps needed to repair the sequence were 97% fewer than for the top-bottom-left-right baseline.",
   "Performance on the heterogeneous ABP collection remained inadequate for practical full reading-order recovery despite being around 47% better than the simple geometric baseline on normalized Spearman footrule distance.",
   "Hierarchical processing substantially improved ordering, reducing OHG from 3.4 to 0.07 swaps per page, FCR from more than 16 to about 4, and ABP from more than 2935 to 864."
  ]
 },
 {
  "paper_id": "doi-10-1109-icde-2002-994696",
  "title": "Detecting Changes in XML Documents",
  "research_question": "How can two versions of a large XML document be compared efficiently to recover node correspondence and a compact edit description that includes subtree moves as well as insertions, deletions, and updates?",
  "key_findings": [
   "The algorithm explicitly models node correspondence between two document versions and can represent subtree moves in addition to insertions, deletions, and value updates.",
   "XML ID attributes and subtree signatures provide strong anchors for preserving identity across versions, after which hierarchical propagation expands matches to related ancestors and descendants.",
   "The implementation uses linear memory and exhibits approximately linear running-time behavior in the reported experiments, contrasting with earlier approaches characterized by the authors as quadratic.",
   "On synthetically edited documents, the produced deltas are reported to remain reasonably close in size to the known edit scripts used to generate the modified versions.",
   "On a small real-web sample, the XML-aware deltas have sizes comparable to conventional textual diff output while also encoding structural tree operations such as moves."
  ]
 },
 {
  "paper_id": "doi-10-1109-icse-2012-6227171",
  "title": "Detecting and visualizing inter-worksheet smells in spreadsheets",
  "research_question": "Which inter-worksheet dependency smells occur in spreadsheets, how can they expose potential spreadsheet-quality problems, and can enriched data-flow diagrams effectively communicate those smells to spreadsheet developers?",
  "key_findings": [
   "Feature Envy was the most prevalent of the reported inter-worksheet smells in the corpus study, with 12.4% of spreadsheets exceeding the 70th-percentile threshold.",
   "Inappropriate Intimacy was also common, with 9.6% of spreadsheets exceeding the corresponding 70th-percentile threshold.",
   "In the industrial study, participants distinguished benign and problematic instances of Inappropriate Intimacy, showing that a high metric value is an indicator requiring interpretation rather than direct proof of a defect.",
   "For observed Feature Envy cases, participants agreed that refactoring could improve the spreadsheet, although understanding the exact cause often required inspecting formulas in addition to the visualization.",
   "Shotgun Surgery instances were regarded by the participating spreadsheet developers as design shortcomings and prompted discussion of structural adaptations."
  ]
 },
 {
  "paper_id": "doi-10-1109-tmm-2022-3219642",
  "title": "Scene-Text Oriented Referring Expression Comprehension",
  "research_question": "Can referring-expression comprehension be improved for expressions that depend on text visible in an image by explicitly aligning referring expressions, scene-text semantics, and localized visual regions?",
  "key_findings": [
   "The paper identifies scene text as an informative cue for object identification and disambiguation that conventional referring-expression comprehension methods largely neglect.",
   "The proposed ST-REC task explicitly incorporates text appearing in the scene into referring-expression grounding.",
   "STAN combines Correlated Text Extraction and Correlated Region Activation to connect expression-relevant scene text with localized visual regions.",
   "The authors introduce RefText as a benchmark for scene-text-oriented referring-expression comprehension.",
   "The official project repository describes RefText as containing approximately 31,000 manually generated referring expressions for 11,000 objects over 4,594 images."
  ]
 },
 {
  "paper_id": "doi-10-1145-2950290-2950359",
  "title": "Detecting Table Clones and Smells in Spreadsheets",
  "research_question": "Can spreadsheet table clones with corresponding computational semantics, and suspicious inconsistencies among their corresponding cells, be detected automatically from inferred row and column header structure?",
  "key_findings": [
   "Confirmed table clones occurred in 352 of the 1,617 evaluated spreadsheets, corresponding to 21.8% of the studied formula-bearing spreadsheets.",
   "TableCheck detected 1,317 table-clone groups, of which 1,214 were manually confirmed, yielding 92.2% precision.",
   "Among 3,382 cells flagged as smells, 2,892 were validated as true smells, for 85.5% smell-detection precision.",
   "177 of the 1,214 confirmed table-clone groups contained smells, corresponding to 14.6% of the confirmed clone groups.",
   "Manual inspection found wrong values in 971 of the 2,892 validated smelly cells, or 33.6%."
  ]
 },
 {
  "paper_id": "doi-10-1145-357775-357777",
  "title": "Tracing the lineage of view data in a warehousing environment",
  "research_question": "How can the exact source data items that produced a selected item in a materialized warehouse view be formally defined and traced consistently in a multisource data-warehousing environment?",
  "key_findings": [
   "The paper defines view-data lineage as identifying the source data items that produced a selected data item in a materialized warehouse view.",
   "The authors develop lineage-tracing algorithms for relational views that include aggregation.",
   "The work proposes mechanisms for performing consistent lineage tracing in a warehouse assembled from multiple source systems.",
   "The proposed lineage capability is intended to support drill-through from a selected warehouse view tuple to the exact source tuples that produced it."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-2020-acl-main-398",
  "title": "TaPas: Weakly Supervised Table Parsing via Pre-training",
  "research_question": "Can a pretrained transformer answer questions over tables from weak denotation supervision by directly selecting supporting cells and aggregation operations instead of generating explicit logical forms?",
  "key_findings": [
   "On weakly supervised WikiSQL, TAPAS reached 83.6 test accuracy, close to the 83.9 result of the then state-of-the-art system despite not requiring logical-form supervision.",
   "On SQA, TAPAS reached 67.2 overall accuracy and 40.4 sequence accuracy, compared with 55.1 and 28.1 respectively for the prior comparison system reported by the paper.",
   "Transferring a TAPAS model pretrained on related table-QA data substantially improved WikiTableQuestions results, reaching 48.7 after WikiSQL transfer and 48.8 after SQA transfer.",
   "Table-specific pretraining was important: removing it reduced development performance from 39.0 to 26.5 SQA sequence accuracy, from 84.7 to 80.8 on WikiSQL, and from 29.0 to 17.9 on WikiTableQuestions in the reported ablation.",
   "The predicted answer is explicitly tied to selected table cells, providing cell-level evidence localization before any optional aggregation is applied."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-2025-acl-long-547",
  "title": "Disambiguating Reference in Visually Grounded Dialogues through Joint Modeling of Textual and Multimodal Semantic Structures",
  "research_question": "Does jointly modeling textual reference relations such as coreference and predicate-argument structure with multimodal mention-to-object grounding improve the resolution of ambiguous and indirect references in visually grounded dialogue?",
  "key_findings": [
   "Adding the proposed textual-reference model substantially improved grounding of pronouns in J-CRe3: the coreference-enhanced model achieved Recall@1/5/10 of 0.361/0.683/0.772 versus 0.277/0.527/0.641 for the baseline.",
   "For pronoun grounding, the coreference-enhanced model outperformed both GLIP and MDETR in the reported J-CRe3 comparison, even though GLIP remained stronger on overall phrase grounding at lower recall cutoffs.",
   "Ablation experiments show that introducing textual reference relations improves pronoun grounding, with coreference providing the strongest individual benefit and combining relation types helping noun grounding.",
   "The proposed multimodal-reference model consistently improves Recall@10 over the model without the added textual-reference information and can represent zero-reference cases that the GLIP-plus-parser comparison cannot directly handle.",
   "Textual reference structure increases model confidence for relationships linking mentions, pronouns, predicates, and visually grounded objects in the qualitative analyses."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-2025-findings-naacl-295",
  "title": "Where is this coming from? Making groundedness count in the evaluation of Document VQA models",
  "research_question": "Can Document VQA evaluation better reflect semantic correctness, spatial grounding, calibration, and robustness by scoring where an answer comes from in the document rather than relying mainly on surface-string similarity?",
  "key_findings": [
   "Adding groundedness and answer-type awareness changes Document VQA leaderboard orderings, with numeric and hybrid answers causing larger ranking changes than purely textual answers.",
   "When SMuDGE gives relatively greater weight to groundedness, higher evaluation scores are associated with lower Expected Calibration Error; the paper selects approximately alpha=0.25 as a useful operating point from the DUDE calibration analysis.",
   "SMuDGE scores show a stronger relationship between score stability and ranking stability than ANLS, with reported regression coefficients of 0.58 for SMuDGE and 0.33 for ANLS.",
   "In the human preference experiment, annotators preferred SMuDGE's pairwise ordering in the majority of disagreement cases across DocVQA, MP-DocVQA, and InfographicVQA.",
   "The human study achieved mean Cohen's kappa of 0.82, indicating high annotator agreement before majority-agreement filtering."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-2026-eacl-long-192",
  "title": "Rethinking Reading Order: Toward Generalizable Document Understanding with LLM-based Relation Modeling",
  "research_question": "Can LLM-inferred global reading-order relations provide a scalable structural prior that improves document understanding more broadly than conventional locally annotated reading-order supervision?",
  "key_findings": [
   "LLM-generated reading-order relations align much less closely with adjacency-oriented human labels than a supervised LayoutLMv3 reading-order predictor, yet they can provide more useful global structure for downstream tasks.",
   "On segment-level reading-order prediction, LayoutLMv3-large reports F1 80.49 whereas GPT-4o text-only reports 30.25, illustrating that the LLM-derived relations differ substantially from the benchmark's human-annotated relation convention.",
   "Adding GPT-inferred reading order improves the reported EC-FUNSD SER and entity-linking scores for both LayoutLMv3-large and GeoLayoutLM compared with their respective baselines.",
   "For GPT-4o document QA, adding inferred reading order raises DocVQA ANLS to 92.77 and InfoVQA ANLS to 77.15, with corresponding gains in exact match in the detailed ablation.",
   "The authors report that generating reading-order relations for 6,000 pages requires 0.7 GPU-hours versus an estimated 25 hours of human annotation, and cached relation integration adds less than 0.5 ms per instance with under 1% parameter overhead."
  ]
 },
 {
  "paper_id": "doi-10-3390-app152312430",
  "title": "Document Image Verification Based on Paragraph Alignment and Subtle Change Detection",
  "research_question": "Can document images be verified against stored references by combining paragraph-structure retrieval, geometric paragraph alignment, and contrastive visual comparison robust to print-scan distortions and subtle content changes?",
  "key_findings": [
   "The proposed structural retrieval method achieved 0.976 precision, 0.96 hit rate, 24.29 ms average retrieval time, and a 1.33 MB retrieval data size in the reported Database A experiment.",
   "With paragraph alignment, the final verification scheme achieved 0.949 precision, 0.978 recall, 0.963 accuracy, and 0.963 F1; removing paragraph alignment reduced precision to 0.725, accuracy to 0.788, and F1 to 0.814 while recall remained 0.975.",
   "At threshold 0.9, adding the secondary verification step increased precision from 0.767 to 0.949 and accuracy from 0.840 to 0.963 while recall remained 0.978.",
   "VGG19 produced a higher precision of 0.976, but the proposed aligned method had substantially higher recall and a higher F1 score, 0.978 and 0.963 versus 0.910 and 0.942.",
   "The approach establishes paragraph-level correspondences independently of OCR text and was evaluated with English and Chinese documents as well as changes affecting text, images, and tables."
  ]
 },
 {
  "paper_id": "manual-0661fc0cba",
  "title": "M3Grounder: Mask-Based Multi-Span and Multi-Granular Grounding for Document QA",
  "research_question": "Can document question answering jointly generate accurate answers and associate individual answer spans with precise, potentially disjoint and hierarchically scoped pixel-level evidence regions instead of coarse bounding boxes?",
  "key_findings": [
   "Interleaving answer spans with [GROUND] tokens creates an explicit one-to-one link from each generated span to its own segmentation evidence region, including answers requiring multiple spatially separated regions.",
   "The method predicts evidence at phrase, line, and block levels and constrains those masks hierarchically rather than exposing only one fixed grounding granularity.",
   "GroundingDocQA is described as providing 200K documents and 2M multi-span, multi-granular QA pairs with pixel-level evidence masks, and GroundingDocQA-Bench as providing 2.5K documents and 5K human-verified QA pairs.",
   "The official benchmark table reports M3Grounder-Q scores of 81.4 F1g on BD-Test, 73.3 F1g on DOGR-Bench, 68.2 IoU on MMDocBench, and 79.0 F1g on GroundingDocQA-Bench, exceeding the compared systems in that table.",
   "For M3Grounder-Q, the official multi-granularity results report 80.1 phrase F1, 84.3 line F1, and 87.5 block F1."
  ]
 },
 {
  "paper_id": "manual-1048d6caf2",
  "title": "Scene-Text Oriented Referring Expression Comprehension",
  "research_question": "Can referring-expression comprehension be improved by explicitly recognizing scene text and aligning the text mentioned in a referring expression with corresponding textual regions in an image?",
  "key_findings": [
   "The paper establishes ST-REC as a task specifically designed to exploit scene text for identifying and disambiguating referred visual objects.",
   "STAN explicitly bridges linguistic references to scene text and the corresponding visual text regions through correlated text extraction and correlated region activation modules.",
   "The accessible abstract reports that STAN effectively handles scene-text-oriented referring expressions and achieves strong experimental performance, although the accessible text does not expose the numerical comparison.",
   "The official repository describes RefText as containing approximately 31K manually generated referring expressions referring to 11K objects from multiple image sources."
  ]
 },
 {
  "paper_id": "manual-7fdf40b3c6",
  "title": "TRH2TQA: Table Recognition with Hierarchical Relationships to Table Question-Answering on Business Table Images",
  "research_question": "Can explicit recovery of hierarchical relationships in visually complex business tables improve question answering over table images?",
  "key_findings": [
   "The proposed architecture explicitly separates visual table recognition, hierarchical relationship recovery, and table question answering.",
   "Hierarchical relations are inferred after table recognition using information including predicted column spans and bounding boxes.",
   "The intermediate representation is HTML containing recognized table structure and textual content rather than an unstructured visual embedding alone.",
   "The authors report that TRH2TQA improves question-answering performance on the VQAonBD 2023 business-document benchmark.",
   "The method is specifically motivated by hierarchical tables whose merged cells and indentation make ordinary flat table recognition insufficient."
  ]
 },
 {
  "paper_id": "manual-8444bbc95c",
  "title": "Performance Evaluation and Error Analysis for Multimodal Reference Resolution in a Conversation System",
  "research_question": "How well does a graph-matching multimodal reference resolver perform in real-time speech-and-gesture conversation, what causes its failures, and what design strategies can make reference resolution more robust?",
  "key_findings": [
   "The resolver correctly identified the intended referents for 137 of 219 evaluated user inputs.",
   "Thirty-one of the 219 inputs, about 14%, were complex inputs containing multiple referring expressions that all had to be resolved correctly.",
   "Speech-recognition errors were the largest observed error source, accounting for 55% of the reference-resolution errors.",
   "Among 90 inputs in which referring expressions were not correctly recognized by speech recognition, multimodal information still allowed 26 references to be resolved correctly.",
   "Gesture and speech order was not fixed: gestures preceded referring expressions in most cases, but users also produced overlapping and speech-before-gesture patterns, motivating relative temporal proximity rather than a rigid ordering rule."
  ]
 },
 {
  "paper_id": "manual-ae200642f8",
  "title": "Change-Centric Management of Versions in an XML Warehouse",
  "research_question": "How can an XML warehouse represent and store document version histories so that node identity persists across snapshots, changes can be composed or reversed, and new versions can be installed efficiently?",
  "key_findings": [
   "Persistent XIDs give corresponding XML nodes a continuing logical identity across document snapshots, directly addressing the problem of referring to the same element through multiple versions.",
   "Completed deltas retain information omitted by simple deltas and can therefore be inverted and composed, allowing navigation and transformation across a version history.",
   "A document history can be represented by the latest materialized version together with a sequence of completed deltas, from which earlier states can be reconstructed by applying changes backward.",
   "The proposed physical layout makes installation of a newly acquired version largely append-oriented, reducing updates to previously stored objects at the cost of redundant information in completed deltas.",
   "Simulation experiments show that delta-storage cost grows with the amount of modification and that richer completed deltas consume more space than simpler change representations, motivating compression and storage-policy optimization."
  ]
 },
 {
  "paper_id": "manual-bc798b0eed",
  "title": "GRAVL-BERT: Graphical Visual-Linguistic Representations for Multimodal Coreference Resolution",
  "research_question": "Can multimodal coreference resolution in situated dialogue be improved by jointly encoding dialogue, candidate-object appearance, scene-graph spatial relationships, object metadata, conversational recency, and local environmental context?",
  "key_findings": [
   "GRAVL-BERT reaches approximately 0.78 F1 on SIMMC 2.0 and is reported as the strongest system among the compared challenge submissions.",
   "Dialogue-domain pretraining alone markedly improves VL-BERT over the vanilla configuration, raising the reported development F1 from roughly 0.47 to roughly 0.68.",
   "Adding graph-convolutional scene relationships raises development F1 further, showing that explicit spatial structure contributes useful grounding information.",
   "Reference distance produces one of the largest incremental gains in the ablation sequence, supporting the usefulness of conversational recency for resolving referring expressions.",
   "Neighbor features and generated environmental captions provide additional smaller improvements after graph and reference-distance features are included."
  ]
 },
 {
  "paper_id": "manual-d896e242a6",
  "title": "J-CRe3: A Japanese Conversation Dataset for Real-world Reference Resolution",
  "research_question": "How can real-world Japanese conversational reference resolution be studied with a multimodal dataset that links linguistic references, including omitted arguments, to concrete objects and regions observed in egocentric video?",
  "key_findings": [
   "J-CRe3 provides jointly aligned dialogue, video, textual-reference annotations, object boxes, persistent object-instance identifiers, and cross-modal reference links, including indirect and omitted references.",
   "The annotation scheme can ground deictic expressions to spatial regions rather than requiring every reference target to be a discrete object.",
   "Zero references are substantially more frequent than explicitly direct text-to-object references in the released annotations, making omitted arguments a central part of the benchmark.",
   "The textual reference-resolution baseline reaches approximately 0.8 F-score and is reported as comparable to performance on established Japanese reference-resolution corpora.",
   "Visual phrase grounding remains difficult: the strongest reported fine-tuned configuration reaches Recall@1 of 0.410 on J-CRe3, while pretrained-only configurations perform poorly."
  ]
 }
]

JSON schema for the verdict:
{
 "$schema": "http://json-schema.org/draft-07/schema#",
 "title": "ReviewerResult",
 "description": "Schema for reviewer gate results (synthesis reviewer, rank reviewer).",
 "type": "object",
 "required": [
  "reviewer_task_id",
  "target_artifact",
  "status"
 ],
 "properties": {
  "reviewer_task_id": {
   "type": "string"
  },
  "target_artifact": {
   "type": "string"
  },
  "status": {
   "type": "string",
   "enum": [
    "accepted",
    "rejected",
    "accepted_with_issues"
   ]
  },
  "issues": {
   "type": "array",
   "items": {
    "type": "string"
   }
  },
  "unsupported_claims": {
   "type": "array",
   "items": {
    "type": "string"
   }
  },
  "required_fixes": {
   "type": "array",
   "items": {
    "type": "string"
   }
  },
  "confidence": {
   "type": "number",
   "minimum": 0.0,
   "maximum": 1.0
  },
  "notes": {
   "type": "string"
  }
 }
}

Reply with one block containing one JSON object:
`reviewer_task_id` = "review-synthesis-web", `target_artifact` =
"/home/grammy-jiang/Projects/msgloom/research/08-multimodal-content-understanding/runs/6efd3430f24f/analysis/synthesis.json", `status` = accepted | accepted_with_issues | rejected,
`issues` (each naming the finding or paper it is about), `required_fixes`
(required when rejected), `unsupported_claims`, `confidence`, and `scores`
with faithfulness, coherence, gap_completeness (0-1) and citation_integrity
(true/false).
===BEGIN synthesis_review.json===
<content>
===END synthesis_review.json===
