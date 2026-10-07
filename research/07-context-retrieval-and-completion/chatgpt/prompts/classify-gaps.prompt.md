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

Research topic: **Unified iterative RAG stopping and provenance control under distribution shift: controllers combining structured evidence sufficiency with temporal/version-aware provenance and calibrated or conformal risk-controlled stopping, including permission-aware access and bounded retrieval budgets**
Run id: `1d3def4db417`  Round: 4 of at most 4

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
  "description": "Structured gap representations remain insufficiently validated for temporal constraints, multi-entity joins, and complex compositional evidence requirements; the corpus contains structured-gap, temporal-retrieval, and query-planning methods, but no admitted study evaluates these capabilities together.",
  "classification": "ACADEMIC",
  "priority": "HIGH",
  "suggested_query": "\"structured evidence gap\" temporal constraints multi-entity joins compositional retrieval iterative RAG"
 },
 {
  "id": "gap-2",
  "description": "No admitted study validates an iterative evidence-gap retrieval loop that jointly preserves document-version lineage, freshness or effective-time validity, and structured sufficiency decisions.",
  "classification": "ACADEMIC",
  "priority": "HIGH",
  "suggested_query": "\"version-aware retrieval\" temporal provenance iterative RAG document lineage freshness effective-time sufficiency"
 },
 {
  "id": "gap-3",
  "description": "Stopping reliability under domain shift remains open: sufficiency, confidence, conformal, stability, and drift-adaptive calibration signals are evaluated in separate studies, but no admitted study provides a general bounded-risk iterative-RAG stopping guarantee under distribution shift.",
  "classification": "ACADEMIC",
  "priority": "HIGH",
  "suggested_query": "\"iterative RAG\" calibrated stopping domain shift conformal risk control selective prediction adaptive retrieval"
 },
 {
  "id": "gap-4",
  "description": "The corpus does not test a bounded replenishment loop in which unauthorized candidates are filtered through native IAM, evidence sufficiency is reassessed, and another permission-constrained query is issued when authorized evidence remains incomplete.",
  "classification": "ENGINEERING",
  "priority": "HIGH"
 },
 {
  "id": "gap-5",
  "description": "The evaluated systems do not jointly distinguish empty retrieval, authorization denial, unavailable source, unsupported extraction, exhausted budget, and true negative evidence as separate terminal or retry conditions.",
  "classification": "ENGINEERING",
  "priority": "HIGH"
 },
 {
  "id": "gap-6",
  "description": "An end-to-end cost evaluation covering retrieval calls, retrieved passages or tokens, planner or judge inference, reranking, permission-check latency, and total wall-clock latency remains absent from the admitted corpus.",
  "classification": "ENGINEERING",
  "priority": "MEDIUM"
 },
 {
  "id": "gap-7",
  "description": "The corpus lacks a workplace-communication evaluation combining explicit evidence gaps with heterogeneous messages and documents, multi-hop dependencies, permission restrictions, stale or conflicting evidence, and bounded retrieval.",
  "classification": "ENGINEERING",
  "priority": "HIGH"
 },
 {
  "id": "gap-8",
  "description": "No admitted study validates a single controller that jointly handles structured evidence gaps, permission-aware source access, version lineage, temporal validity, calibrated stopping, abstention, and total-cost budgeting; the reported successes remain component-level or cover smaller subsets of these functions.",
  "classification": "ACADEMIC",
  "priority": "HIGH",
  "suggested_query": "\"adaptive RAG controller\" permission-aware provenance temporal version calibrated stopping abstention budget"
 }
]

Gaps carried over from the previous round (keep their ids):
- gap-1 [ACADEMIC, HIGH]: Structured gap representations remain insufficiently validated for temporal constraints, multi-entity joins, and complex compositional evidence requirements; the corpus contains structured-gap, temporal-retrieval, and query-planning methods, but no admitted study evaluates these capabilities together.
    suggested query: "structured evidence gap" temporal constraints multi-entity joins compositional retrieval iterative RAG
    searched in rounds: [1, 2, 3] (still open)
- gap-2 [ACADEMIC, HIGH]: No admitted study validates an iterative evidence-gap retrieval loop that jointly preserves document-version lineage, freshness or effective-time validity, and structured sufficiency decisions.
    suggested query: "version-aware retrieval" temporal provenance iterative RAG document lineage freshness effective-time sufficiency
    searched in rounds: [1, 2, 3] (still open)
- gap-3 [ACADEMIC, HIGH]: Stopping reliability under domain shift remains open: sufficiency, confidence, conformal, and stability signals guide stopping in separate studies, but no admitted study provides a general bounded-risk iterative-RAG stopping guarantee under distribution shift.
    suggested query: "iterative RAG" calibrated stopping domain shift conformal risk control selective prediction adaptive retrieval
    searched in rounds: [1, 2, 3] (still open)
- gap-4 [ENGINEERING, HIGH]: The corpus does not test a bounded replenishment loop in which unauthorized candidates are filtered through native IAM, evidence sufficiency is reassessed, and another permission-constrained query is issued when authorized evidence remains incomplete.
- gap-5 [ENGINEERING, HIGH]: The evaluated systems do not jointly distinguish empty retrieval, authorization denial, unavailable source, unsupported extraction, exhausted budget, and true negative evidence as separate terminal or retry conditions.
- gap-6 [ENGINEERING, MEDIUM]: An end-to-end cost evaluation covering retrieval calls, retrieved passages or tokens, planner or judge inference, reranking, permission-check latency, and total wall-clock latency remains absent from the admitted corpus.
- gap-7 [ENGINEERING, HIGH]: The corpus lacks a workplace-communication evaluation combining explicit evidence gaps with heterogeneous messages and documents, multi-hop dependencies, permission restrictions, stale or conflicting evidence, and bounded retrieval.
- gap-8 [ACADEMIC, HIGH]: No admitted study validates a single controller that jointly handles structured evidence gaps, permission-aware source access, version lineage, temporal validity, calibrated stopping, abstention, and total-cost budgeting; the reported successes remain component-level or cover smaller subsets of these functions.
    suggested query: "adaptive RAG controller" permission-aware provenance temporal version calibrated stopping abstention budget
    searched in rounds: [1, 2, 3] (still open)

The synthesis judged them as follows:
[
 {
  "id": "gap-1",
  "status": "open",
  "note": "Structured-gap controllers now provide strong direct evidence for typed or enumerated missing findings, while temporal and query-planning papers cover temporal constraints or compositional retrieval separately. No admitted study evaluates structured gaps together with temporal constraints, multi-entity joins, and complex compositional requirements.",
  "evidence": [
   "2604.23783",
   "2510.22344",
   "2605.05245",
   "2607.06507",
   "2412.15540",
   "doi-10-18653-v1-2026-findings-acl-2090"
  ]
 },
 {
  "id": "gap-2",
  "status": "open",
  "note": "VersionRAG, temporal retrieval, Temporal GraphRAG, SentryLine, and TimelyRAG provide evidence for temporal or version-aware retrieval and provenance, while S2G-RAG and FAIR-RAG provide iterative structured sufficiency control. Their combination in one evaluated evidence-gap loop remains absent.",
  "evidence": [
   "2510.08109",
   "2510.13590",
   "2609.08364",
   "2609.11572",
   "2604.23783",
   "2510.22344"
  ]
 },
 {
  "id": "gap-3",
  "status": "open",
  "note": "MiCP provides conformally calibrated multi-turn stopping, and several conformal studies address covariate, online, prompt, domain, or temporal/severity shift. The corpus does not demonstrate a general iterative-RAG stopping controller whose bounded stopping risk remains controlled under distribution shift.",
  "evidence": [
   "2604.01413",
   "1904.06019",
   "2208.08401",
   "2606.15964",
   "2606.29054",
   "2402.03181"
  ]
 },
 {
  "id": "gap-4",
  "status": "open",
  "note": "Permission-aware RAG studies enforce native IAM, access gates, encrypted user isolation, or RBAC-safe retrieval, but none couples authorization filtering to repeated structured sufficiency reassessment and bounded permission-constrained replenishment.",
  "evidence": [
   "doi-10-1109-access-2025-3628960",
   "doi-10-1038-s41598-026-71936-x",
   "2508.01084",
   "doi-10-1145-3786625"
  ]
 },
 {
  "id": "gap-5",
  "status": "open",
  "note": "Several papers distinguish insufficiency, conflicts, budget exhaustion, or authorization, but no admitted system evaluates the full terminal-condition set of empty retrieval, denial, unavailable source, extraction failure, budget exhaustion, and true negative evidence.",
  "evidence": [
   "2608.02195",
   "doi-10-32604-cmc-2026-086343",
   "doi-10-1109-access-2025-3628960",
   "2506.05167"
  ]
 },
 {
  "id": "gap-6",
  "status": "open",
  "note": "The corpus contains separate measurements of retrieval calls, tokens, inference or routing overhead, latency, indexing cost, and permission-aware vector-search trade-offs, but no study measures all requested cost components end to end.",
  "evidence": [
   "2606.29959",
   "2607.24010",
   "2606.05658",
   "doi-10-18653-v1-2026-acl-long-1562",
   "doi-10-1145-3786625"
  ]
 },
 {
  "id": "gap-7",
  "status": "open",
  "note": "The admitted studies cover QA, evolving documents, medicine, tool retrieval, data lakes, and synthetic or constructed enterprise settings. No admitted evaluation covers the specified workplace-communication combination.",
  "evidence": [
   "2604.23783",
   "2609.08364",
   "doi-10-1109-access-2025-3628960",
   "2608.08512"
  ]
 },
 {
  "id": "gap-8",
  "status": "open",
  "note": "DynaKRAG and related controllers integrate multiple retrieval actions, sufficiency checks, stopping, and budgets, while separate papers provide temporal/version provenance, permissions, or conformal risk control. No admitted controller integrates the complete set in this gap.",
  "evidence": [
   "2607.06507",
   "2604.23783",
   "2510.08109",
   "2609.08364",
   "doi-10-1109-access-2025-3628960",
   "2604.01413",
   "2606.15964"
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

Reply format (one block containing one JSON object with run_id "1d3def4db417"
and round 4):
===BEGIN gaps.json===
<content>
===END gaps.json===
