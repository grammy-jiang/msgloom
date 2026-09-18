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

# Task: classify the open research gaps

Research topic: **Direct empirical methods for cross-version multimodal document element lineage and hierarchical provenance, with special attention to revised workbook provenance and message referring-expression grounding into versioned pages, regions, and cells.**
Run id: `6efd3430f24f`  Round: 4 of at most 4

Classify every gap below as ACADEMIC (needs additional papers; give one
concrete arXiv search query in `suggested_search_query`), ENGINEERING
(resolvable from documentation, code, or benchmarks; say how in
`resolution_notes`) or OUT_OF_SCOPE (explain why in `resolution_notes`).
Give each gap a stable id (`gap-1`, `gap-2`, ...) and a priority.
Then fill `convergence`: `should_continue` is true with reason
`open_gaps_remain` when at least one ACADEMIC gap remains and the round is
below 4; otherwise false with reason `no_open_gaps` or
`round_cap_reached`. When continuing, set `next_round_topic` to a focused
topic for the next search round.

Open gaps from the synthesis:
[
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
]

Gaps carried over from the previous round (keep their ids):
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

The synthesis judged them as follows:
[
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

Include every carried-over gap in `gaps` with its original id and a
`status` field: `resolved` (say which papers resolved it in
`resolution_notes`) or `open`. New gaps get new ids and `status: open`.
Never drop or downgrade an unresolved gap.

JSON schema:
{
 "$schema": "http://json-schema.org/draft-07/schema#",
 "title": "GapClassification",
 "description": "Schema for the gap classification artifact produced after each research round.",
 "type": "object",
 "required": [
  "run_id",
  "round",
  "gaps",
  "convergence"
 ],
 "properties": {
  "run_id": {
   "type": "string"
  },
  "round": {
   "type": "integer",
   "minimum": 1,
   "maximum": 4
  },
  "topic": {
   "type": "string"
  },
  "gaps": {
   "type": "array",
   "items": {
    "type": "object",
    "required": [
     "id",
     "description",
     "classification"
    ],
    "properties": {
     "id": {
      "type": "string"
     },
     "description": {
      "type": "string",
      "minLength": 1
     },
     "classification": {
      "type": "string",
      "enum": [
       "ACADEMIC",
       "ENGINEERING",
       "OUT_OF_SCOPE"
      ]
     },
     "priority": {
      "type": "string",
      "enum": [
       "HIGH",
       "MEDIUM",
       "LOW"
      ]
     },
     "suggested_search_query": {
      "type": "string"
     },
     "resolution_notes": {
      "type": "string"
     }
    }
   }
  },
  "convergence": {
   "type": "object",
   "required": [
    "should_continue",
    "reason"
   ],
   "properties": {
    "should_continue": {
     "type": "boolean"
    },
    "reason": {
     "type": "string",
     "enum": [
      "open_gaps_remain",
      "no_open_gaps",
      "round_cap_reached",
      "no_new_papers",
      "user_marked_out_of_scope"
     ]
    },
    "next_round_topic": {
     "type": "string"
    }
   }
  }
 }
}

Reply format (one block containing one JSON object with run_id "6efd3430f24f"
and round 4):
===BEGIN gaps.json===
<content>
===END gaps.json===
