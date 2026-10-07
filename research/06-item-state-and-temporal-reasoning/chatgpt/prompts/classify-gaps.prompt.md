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

Research topic: **Direct empirical NLP methods for longitudinal work-item revision in workplace or operational communication, especially relation labeling for supersession/correction/supplementation/reopening/conflict and evidence models separating claimed completion from independently corroborated completion.**
Run id: `0ecdd7e4a549`  Round: 4 of at most 4

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
  "description": "No admitted paper directly evaluates longitudinal state tracking across workplace messages in which one work item moves among requested, proposed, planned, approved, completed, revoked, superseded, disputed, conditional, and unresolved states while retaining historical assessments.",
  "classification": "ACADEMIC",
  "priority": "HIGH",
  "suggested_query": "workplace email enterprise chat longitudinal work item lifecycle state tracking requested planned approved completed revoked superseded disputed unresolved",
  "evidence": [
   "1805.06975",
   "doi-10-1007-s10458-012-9202-0",
   "manual-d574dff39d"
  ]
 },
 {
  "id": "gap-2",
  "description": "The corpus provides formal treatments of correction, retraction, persistence, and reopening and empirical work on document revision, but does not establish a natural-language method evaluated across successive operational communications for distinguishing supersession, correction, supplementation, contradiction, reopening, and unresolved conflict.",
  "classification": "ACADEMIC",
  "priority": "HIGH",
  "suggested_query": "natural language dialogue revision relation classification supersession correction supplementation contradiction reopening unresolved conflict longitudinal",
  "evidence": [
   "doi-10-1093-jos-ffn013",
   "doi-10-1023-a-1010318403544",
   "2210.15067",
   "2406.00197",
   "2103.08541"
  ]
 },
 {
  "id": "gap-3",
  "description": "No admitted paper jointly evaluates source-relative factuality, temporal ordering, lifecycle state, contradiction, and provenance as one longitudinal model; the admitted studies validate separate components and their combination remains untested.",
  "classification": "ACADEMIC",
  "priority": "HIGH",
  "suggested_query": "\"event factuality\" temporal relation contradiction provenance lifecycle longitudinal joint model",
  "evidence": [
   "doi-10-1007-s10579-009-9089-9",
   "1909.00429",
   "doi-10-1007-s10458-012-9202-0",
   "2606.18037",
   "2608.20116"
  ]
 },
 {
  "id": "gap-4",
  "description": "Direct target-task evidence for workplace email, Teams-like dialogue, or comparable operational communication remains absent. One admitted workplace-email study evaluates task and message-relation learning, but not longitudinal factuality, lifecycle revision, supersession, or evidence-backed current-state resolution.",
  "classification": "ACADEMIC",
  "priority": "HIGH",
  "suggested_query": "workplace email enterprise chat operational communication task state tracking revision factuality temporal commitment",
  "evidence": [
   "manual-d574dff39d",
   "2110.08222"
  ]
 },
 {
  "id": "gap-5",
  "description": "The admitted factuality literature models what a source presents or commits to, and the fact-verification literature evaluates corroborating evidence, but no admitted paper establishes how to distinguish an author's assertion that work is complete from independent confirmation or stronger evidential verification of completion in longitudinal operational communication.",
  "classification": "ACADEMIC",
  "priority": "HIGH",
  "suggested_query": "dialogue event factuality evidentiality source attribution claimed completion independent confirmation corroboration longitudinal",
  "evidence": [
   "doi-10-1007-s10579-009-9089-9",
   "doi-10-18653-v1-2023-findings-acl-44",
   "2011.03088",
   "2110.08222",
   "2606.18037",
   "doi-10-1016-j-ipm-2026-104709"
  ]
 },
 {
  "id": "gap-6",
  "description": "Evaluation is still needed on adversarial longitudinal sequences such as plan-to-cancel, approve-to-revoke, deadline changes, contradictory same-time updates, out-of-order ingestion, stale messages arriving late, and completion claims later corrected.",
  "classification": "ENGINEERING",
  "priority": "HIGH",
  "evidence": [
   "2103.08541",
   "2406.19764",
   "2608.20116",
   "doi-10-1093-jos-ffn013"
  ]
 },
 {
  "id": "gap-7",
  "description": "The combined representation of message time, event or effective time, deadline or constraint time, and observed collection or version time has not been benchmarked for the target state-resolution task; the corpus contains related temporal formalisms and temporal NLP evaluations rather than such a combined benchmark.",
  "classification": "ENGINEERING",
  "priority": "HIGH",
  "evidence": [
   "doi-10-1016-0020-0255-94-90059-0",
   "doi-10-18653-v1-d18-1155",
   "doi-10-18653-v1-2021-emnlp-main-815"
  ]
 },
 {
  "id": "gap-8",
  "description": "The corpus does not evaluate a provenance-preserving implementation for this target state-resolution task that stores immutable source observations and successive assessments while exposing a separately derived current-state view.",
  "classification": "ENGINEERING",
  "priority": "HIGH",
  "evidence": [
   "2007.14864",
   "doi-10-1007-3-540-44503-x-20",
   "2104.01146",
   "2606.18037"
  ]
 }
]

Gaps carried over from the previous round (keep their ids):
- gap-1 [ACADEMIC, HIGH]: No admitted paper directly evaluates longitudinal state tracking across workplace messages in which one work item moves among requested, proposed, planned, approved, completed, revoked, superseded, disputed, conditional, and unresolved states while retaining historical assessments.
    suggested query: workplace email enterprise chat longitudinal work item lifecycle state tracking requested planned approved completed revoked superseded disputed unresolved
    searched in rounds: [1, 2, 3] (still open)
- gap-2 [ACADEMIC, HIGH]: The corpus provides formal treatments of correction, retraction, persistence, and reopening, but does not establish a natural-language method evaluated across successive operational communications for distinguishing supersession, correction, supplementation, contradiction, reopening, and unresolved conflict.
    suggested query: natural language dialogue revision relation classification supersession correction supplementation contradiction reopening unresolved conflict longitudinal
    searched in rounds: [1, 2, 3] (still open)
- gap-3 [ACADEMIC, HIGH]: No admitted paper jointly evaluates source-relative factuality, temporal ordering, lifecycle state, contradiction, and provenance as one longitudinal model; the papers validate separate components and their combination remains untested.
    suggested query: "event factuality" temporal relation contradiction provenance lifecycle longitudinal joint model
    searched in rounds: [1, 2, 3] (still open)
- gap-4 [ACADEMIC, HIGH]: Direct evidence for workplace email, Teams-like dialogue, or comparable operational communication is absent; the empirical NLP evidence is predominantly news-derived, while the commitment and belief-revision papers use formal, modeled, argumentative-dialogue, or adjacent-domain settings.
    suggested query: workplace email enterprise chat operational communication task state tracking revision factuality temporal commitment
    searched in rounds: [1, 2, 3] (still open)
- gap-5 [ACADEMIC, HIGH]: The admitted factuality literature models textual source commitment, and the fact-verification literature models corroborating evidence, but no admitted paper establishes how to distinguish an author's assertion that work is complete from independent confirmation or stronger evidential verification of completion in longitudinal operational communication.
    suggested query: dialogue event factuality evidentiality source attribution claimed completion independent confirmation corroboration longitudinal
    searched in rounds: [1, 2, 3] (still open)
- gap-6 [ENGINEERING, HIGH]: Evaluation is still needed on adversarial longitudinal sequences such as plan-to-cancel, approve-to-revoke, deadline changes, contradictory same-time updates, out-of-order ingestion, stale messages arriving late, and completion claims later corrected.
- gap-7 [ENGINEERING, HIGH]: The combined representation of message time, event/effective time, deadline or constraint time, and observed collection/version time has not been benchmarked for this product's state-resolution tasks; the temporal-database paper provides a related three-time formal account rather than such an evaluation.
- gap-8 [ENGINEERING, HIGH]: The corpus does not evaluate a provenance-preserving implementation for this state-resolution task that stores immutable source observations and successive assessments while exposing a separately derived current-state view.

The synthesis judged them as follows:
[
 {
  "id": "gap-1",
  "status": "open",
  "note": "Procedural state tracking, formal commitment lifecycles, and email task-relation learning cover separate portions of the problem, but no admitted paper evaluates the specified multi-state work-item lifecycle across successive workplace messages while retaining historical assessments.",
  "evidence": [
   "1805.06975",
   "doi-10-1007-s10458-012-9202-0",
   "manual-d574dff39d"
  ]
 },
 {
  "id": "gap-2",
  "status": "open",
  "note": "Formal dialogue work distinguishes correction, retraction, persistence, and reopening, while scientific revision datasets align and classify document edits, but no admitted empirical NLP study classifies the complete operational relation set across successive communications.",
  "evidence": [
   "doi-10-1093-jos-ffn013",
   "doi-10-1023-a-1010318403544",
   "2210.15067",
   "2406.00197",
   "2103.08541"
  ]
 },
 {
  "id": "gap-3",
  "status": "open",
  "note": "Separate admitted studies evaluate factuality, temporal relations, lifecycle or commitment state, conflicting evidence, and provenance, but none evaluates all of these jointly as one longitudinal model.",
  "evidence": [
   "doi-10-1007-s10579-009-9089-9",
   "1909.00429",
   "doi-10-1007-s10458-012-9202-0",
   "2606.18037",
   "2608.20116"
  ]
 },
 {
  "id": "gap-4",
  "status": "open",
  "note": "manual-d574dff39d supplies direct workplace-email evidence for task and message-relation learning, so workplace email is not wholly absent from the corpus; however, it does not evaluate the target longitudinal state, factuality, supersession, correction, or corroboration task. Direct target-task operational evidence therefore remains open.",
  "evidence": [
   "manual-d574dff39d",
   "2110.08222"
  ]
 },
 {
  "id": "gap-5",
  "status": "open",
  "note": "Source-relative factuality and evidence-based verification are both represented in the corpus, but no admitted paper evaluates the specific distinction between a longitudinal work-item completion assertion and independent corroboration of that completion in operational communication.",
  "evidence": [
   "doi-10-1007-s10579-009-9089-9",
   "doi-10-18653-v1-2023-findings-acl-44",
   "2011.03088",
   "2110.08222",
   "2606.18037",
   "doi-10-1016-j-ipm-2026-104709"
  ]
 },
 {
  "id": "gap-6",
  "status": "open",
  "note": "Revision-aware fact verification, belief revision, conflict arbitration, and formal correction semantics each cover selected adversarial changes, but no admitted study evaluates the specified end-to-end longitudinal adversarial suite.",
  "evidence": [
   "2103.08541",
   "2406.19764",
   "2608.20116",
   "doi-10-1093-jos-ffn013"
  ]
 },
 {
  "id": "gap-7",
  "status": "open",
  "note": "The temporal-database literature supplies a related event/valid/transaction-time formalization and temporal NLP studies evaluate event ordering, but no admitted benchmark combines message, effective, deadline, and collection/version time for the target state-resolution task.",
  "evidence": [
   "doi-10-1016-0020-0255-94-90059-0",
   "doi-10-18653-v1-d18-1155",
   "doi-10-18653-v1-2021-emnlp-main-815"
  ]
 },
 {
  "id": "gap-8",
  "status": "open",
  "note": "Provenance and event-sourcing studies demonstrate relevant storage and update mechanisms, but they do not evaluate a provenance-preserving implementation of this specific NLP state-resolution task with immutable observations, successive assessments, and a derived current-state view.",
  "evidence": [
   "2007.14864",
   "doi-10-1007-3-540-44503-x-20",
   "2104.01146",
   "2606.18037"
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

Reply format (one block containing one JSON object with run_id "0ecdd7e4a549"
and round 4):
===BEGIN gaps.json===
<content>
===END gaps.json===
