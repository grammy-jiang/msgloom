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

Research topic: **Joint evaluation and selective prediction for temporally evolving multi-source generation: evidence completeness for compound and partially supported claims, longitudinal omission of superseded or due work-item state, and online calibration under non-stationary streams**
Run id: `1b615a33607c`  Round: 4 of at most 4

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
  "description": "No admitted study validates one end-to-end evaluation scheme that jointly measures claim correctness, evidence attribution correctness, citation or evidence completeness, temporal or current-state correctness, omission, calibrated uncertainty, and abstention while preserving separate denominators for those dimensions. The corpus validates individual components and smaller combinations.",
  "classification": "ACADEMIC",
  "priority": "HIGH",
  "suggested_query": "\"joint evaluation framework\" factuality attribution completeness temporal correctness omission calibration abstention \"free-form generation\" multi-source"
 },
 {
  "id": "gap-2",
  "description": "The corpus contains no direct evaluation on private workplace email or Teams-style communication with realistic revisions, quoted history, conflicting updates, delayed or out-of-order arrival, versioned attachments, and permission-constrained evidence. Target-domain fixtures and gold data remain an engineering validation gap.",
  "classification": "ENGINEERING",
  "priority": "HIGH"
 },
 {
  "id": "gap-4",
  "description": "The corpus does not establish a general evidence-completeness method that jointly handles compound claims, partially supportive evidence, multiple complementary sources, and temporally versioned evidence. Separate studies cover subsets of these conditions.",
  "classification": "ACADEMIC",
  "priority": "HIGH",
  "suggested_query": "\"evidence completeness\" compound claims partial support complementary evidence multi-source temporal versioning provenance evaluation"
 },
 {
  "id": "gap-5",
  "description": "Report-level omission has substantial benchmark coverage, but the corpus still does not establish omission detection for evolving workplace work items, due information, superseded facts, or decision-relevant state across time.",
  "classification": "ACADEMIC",
  "priority": "HIGH",
  "suggested_query": "\"omission detection\" longitudinal summarization work-item state superseded facts due dates temporal updates decision-relevant information"
 },
 {
  "id": "gap-6",
  "description": "A target-domain human-review protocol remains an engineering gap: representative or risk-stratified sampling, minimum human-review volume, multi-rater adjudication, confusion matrices, abstention treatment, coverage reporting, and validation of any LLM-assisted judge against independent human judgments remain project-specific choices.",
  "classification": "ENGINEERING",
  "priority": "HIGH"
 },
 {
  "id": "gap-7",
  "description": "The corpus demonstrates evaluator-optimization effects, rating indeterminacy, abstention sensitivity, and directional judge bias but does not provide a project-specific procedure for preventing acceptance criteria from being overfit to the same automatic evaluator used during development. Independent holdouts, evaluator separation, and regression checks remain an engineering validation problem.",
  "classification": "ENGINEERING",
  "priority": "MEDIUM"
 },
 {
  "id": "gap-8",
  "description": "Calibration under continuing temporal or distributional change remains open for non-stationary free-form communication streams. The corpus supplies adaptive coverage results, cross-domain calibration studies, benchmark-aging evidence, and structured-generation risk-control results, but not one validated selective-prediction method for continuously changing workplace communication.",
  "classification": "ACADEMIC",
  "priority": "MEDIUM",
  "suggested_query": "\"selective prediction\" \"non-stationary\" free-form generation online calibration concept drift abstention adaptive conformal temporal stream"
 }
]

Gaps carried over from the previous round (keep their ids):
- gap-1 [ACADEMIC, HIGH]: No admitted study validates one end-to-end evaluation scheme that jointly measures claim correctness, evidence attribution correctness, citation or evidence completeness, temporal or current-state correctness, omission, calibrated uncertainty, and abstention while preserving separate denominators for those dimensions. The corpus validates individual components and smaller combinations.
    suggested query: "joint evaluation framework" factuality attribution completeness temporal correctness omission calibration abstention "free-form generation" multi-source
    searched in rounds: [1, 2, 3] (still open)
- gap-2 [ENGINEERING, HIGH]: The corpus contains no direct evaluation on private workplace email or Teams-style communication with realistic revisions, quoted history, conflicting updates, delayed or out-of-order arrival, versioned attachments, and permission-constrained evidence. Target-domain fixtures and gold data remain an engineering validation gap.
- gap-4 [ACADEMIC, HIGH]: The corpus does not establish a general evidence-completeness method that jointly handles compound claims, partially supportive evidence, multiple complementary sources, and temporally versioned evidence. Separate studies cover subsets of these conditions.
    suggested query: "evidence completeness" compound claims partial support complementary evidence multi-source temporal versioning provenance evaluation
    searched in rounds: [1, 2, 3] (still open)
- gap-5 [ACADEMIC, HIGH]: Report-level omission has substantial benchmark coverage, but the corpus still does not establish omission detection for evolving workplace work items, due information, superseded facts, or decision-relevant state across time.
    suggested query: "omission detection" longitudinal summarization work-item state superseded facts due dates temporal updates decision-relevant information
    searched in rounds: [1, 2, 3] (still open)
- gap-6 [ENGINEERING, HIGH]: A target-domain human-review protocol remains an engineering gap: representative or risk-stratified sampling, minimum human-review volume, multi-rater adjudication, confusion matrices, abstention treatment, coverage reporting, and validation of any LLM-assisted judge against independent human judgments remain project-specific choices.
- gap-7 [ENGINEERING, MEDIUM]: The corpus demonstrates evaluator-optimization effects, rating indeterminacy, abstention sensitivity, and directional judge bias but does not provide a project-specific procedure for preventing acceptance criteria from being overfit to the same automatic evaluator used during development. Independent holdouts, evaluator separation, and regression checks remain an engineering validation problem.
- gap-8 [ACADEMIC, MEDIUM]: Calibration under continuing temporal or distributional change remains open for non-stationary free-form communication streams. The corpus supplies adaptive coverage results, cross-domain calibration studies, benchmark-aging evidence, and structured-generation risk-control results, but not one validated selective-prediction method for continuously changing workplace communication.
    suggested query: "selective prediction" "non-stationary" free-form generation online calibration concept drift abstention adaptive conformal temporal stream
    searched in rounds: [1, 2, 3] (still open)

The synthesis judged them as follows:
[
 {
  "id": "gap-1",
  "status": "open",
  "note": "Newer papers add component-level combinations such as completeness plus support, selective risk control, temporal validity, and report-wide evaluation, but no admitted study validates the full joint evaluation scheme named by the gap.",
  "evidence": [
   "2405.00982",
   "2509.26184",
   "2510.07238",
   "2606.29054",
   "2607.19322"
  ]
 },
 {
  "id": "gap-2",
  "status": "open",
  "note": "No admitted paper directly evaluates the stated private workplace email or Teams-style target domain with the full set of revisions, quoted history, conflicting updates, delayed arrival, attachment versioning, and permission constraints.",
  "evidence": []
 },
 {
  "id": "gap-4",
  "status": "open",
  "note": "The corpus separately covers compound-claim decomposition, partial support, minimal sufficient evidence, multi-source retrieval, and temporal evidence validity, but no admitted method jointly handles all of these evidence-completeness conditions.",
  "evidence": [
   "2305.11859",
   "2404.15588",
   "2508.20867",
   "doi-10-18653-v1-2025-acl-long-837",
   "doi-10-1109-access-2026-3679691"
  ]
 },
 {
  "id": "gap-5",
  "status": "open",
  "note": "Update summarization, report evaluation, real-time summarization, and factual-completeness benchmarks measure omission, novelty, redundancy, or temporal update coverage, but none directly evaluates evolving workplace work-item states, due obligations, or supersession chains.",
  "evidence": [
   "2405.00982",
   "2607.19322",
   "doi-10-1155-2016-1340973",
   "doi-10-6028-nist-sp-500-321-realtime-overview",
   "manual-39435af3dd"
  ]
 },
 {
  "id": "gap-6",
  "status": "open",
  "note": "The corpus supplies methods for active human sampling, LLM-assisted estimation, agreement measurement, reproducibility, and rating indeterminacy, but it does not determine the target-domain review volume, adjudication protocol, risk strata, or acceptance procedure.",
  "evidence": [
   "2406.07967",
   "2605.16354",
   "2606.00093",
   "manual-32d5793dca",
   "manual-f5ce52cae2"
  ]
 },
 {
  "id": "gap-7",
  "status": "open",
  "note": "Metric optimization effects, judge bias, abstention sensitivity, and rating indeterminacy are documented, but no admitted study supplies a project-specific evaluator-separation and holdout procedure for this system.",
  "evidence": [
   "2212.08037",
   "2606.00093",
   "2607.08700",
   "manual-32d5793dca"
  ]
 },
 {
  "id": "gap-8",
  "status": "open",
  "note": "Adaptive and strongly adaptive conformal methods now provide substantial evidence for non-stationary prediction, while structured-generation experiments document failure modes under cross-dataset shift. No admitted study validates one selective-prediction method on continuously changing free-form workplace communication.",
  "evidence": [
   "2106.00170",
   "2208.08401",
   "2302.07869",
   "2602.16537",
   "2606.29054"
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

Reply format (one block containing one JSON object with run_id "1b615a33607c"
and round 4):
===BEGIN gaps.json===
<content>
===END gaps.json===
