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

Research topic: **authentic workplace email and enterprise-chat benchmarks for structured action/decision extraction, focusing specifically on implicit and group assignees, action-to-deadline binding, condition/negation/modality scope, and exact argument evidence spans**
Run id: `5060d000e7b4`  Round: 4 of at most 4

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
  "description": "There is no direct modern workplace email/chat benchmark in this corpus that jointly annotates speech-act type, owner/assignee, action object, deadline, conditions/exceptions, and exact evidence spans.",
  "classification": "ACADEMIC",
  "priority": "HIGH",
  "suggested_query": "\"action item extraction\" (email OR Slack OR \"workplace chat\" OR \"enterprise chat\") assignee deadline condition \"evidence span\" corpus"
 },
 {
  "id": "gap-2",
  "description": "Direct empirical evidence for extracting decisions, approvals, rejections, and proposals with structured arguments from authentic workplace email or chat is still missing from this corpus.",
  "classification": "ACADEMIC",
  "priority": "HIGH",
  "suggested_query": "(\"decision extraction\" OR \"decision detection\" OR \"proposal extraction\") (\"workplace email\" OR \"enterprise chat\" OR Slack) approval rejection proposal \"argument extraction\""
 },
 {
  "id": "gap-3",
  "description": "Owner/assignee extraction remains weakly evidenced, especially for implicit owners, group ownership, multiple actions with different owners, and owners recoverable only from organizational or conversation context.",
  "classification": "ACADEMIC",
  "priority": "HIGH",
  "suggested_query": "(\"assignee prediction\" OR \"assignee extraction\" OR \"responsibility extraction\" OR \"action owner\") (email OR Slack OR \"workplace chat\") implicit owner group owner context"
 },
 {
  "id": "gap-4",
  "description": "The corpus does not establish reliable deadline binding in workplace communication: distinguishing a deadline for a particular action from a merely mentioned date, shared date, scheduling expression, or conditional future time remains open.",
  "classification": "ACADEMIC",
  "priority": "HIGH",
  "suggested_query": "(\"deadline extraction\" OR \"due date extraction\" OR \"deadline detection\") (email OR \"workplace communication\" OR Slack) \"action item\" temporal relation event argument"
 },
 {
  "id": "gap-5",
  "description": "Direct workplace evidence is insufficient for attaching conditions, exceptions, negation, and modality to the correct action when several actions or clauses occur together.",
  "classification": "ACADEMIC",
  "priority": "HIGH",
  "suggested_query": "(\"conditional commitment\" OR \"deontic modality\" OR \"negation scope\" OR \"condition extraction\") (email OR \"workplace communication\" OR Slack) action attachment obligation"
 },
 {
  "id": "gap-6",
  "description": "Build an independent argument-level benchmark and adversarial fixture suite covering implicit owners, multiple actions in one sentence, shared deadlines, conditional and negated actions, overlapping request/commitment labels, quoted-history contamination, and attachment references; score false positives, false negatives, and each argument separately.",
  "classification": "ENGINEERING",
  "priority": "HIGH"
 },
 {
  "id": "gap-7",
  "description": "Compare sentence-local, message-level, and selectively expanded thread-context extraction with controlled ablations, because the literature shows both context gains and context-induced degradation.",
  "classification": "ENGINEERING",
  "priority": "HIGH"
 },
 {
  "id": "gap-8",
  "description": "Test author/quoted/forwarded content zoning while preserving provenance, and measure whether zoning improves act and argument extraction without losing obligations whose interpretation depends on prior-message context.",
  "classification": "ENGINEERING",
  "priority": "HIGH"
 },
 {
  "id": "gap-9",
  "description": "Evaluate an uncertainty-preserving structured output in which owner, deadline, condition, or act subtype can remain unresolved, and measure whether this reduces false obligations and wrong argument assignments without unacceptable recall loss.",
  "classification": "ENGINEERING",
  "priority": "HIGH"
 },
 {
  "id": "boundary-1",
  "description": "Exact proposition-level scope for approvals, rejections, agreements, answers, and commitments remains an inherited Topic 04 problem; this synthesis does not establish that an extracted Topic 05 act label has the correct antecedent scope.",
  "classification": "OUT_OF_SCOPE",
  "priority": "HIGH"
 }
]

Gaps carried over from the previous round (keep their ids):
- gap-1 [ACADEMIC, HIGH]: There is no direct modern workplace email/chat benchmark in this corpus that jointly annotates speech-act type, owner/assignee, action object, deadline, conditions/exceptions, and exact evidence spans.
    suggested query: "action item extraction" (email OR Slack OR "workplace chat" OR "enterprise chat") assignee deadline condition "evidence span" corpus
    searched in rounds: [1, 2, 3] (still open)
- gap-2 [ACADEMIC, HIGH]: Direct empirical evidence for extracting decisions, approvals, rejections, and proposals with structured arguments from authentic workplace email or chat is still missing from this corpus.
    suggested query: ("decision extraction" OR "decision detection" OR "proposal extraction") ("workplace email" OR "enterprise chat" OR Slack) approval rejection proposal "argument extraction"
    searched in rounds: [1, 2, 3] (still open)
- gap-3 [ACADEMIC, HIGH]: Owner/assignee extraction remains weakly evidenced, especially for implicit owners, group ownership, multiple actions with different owners, and owners recoverable only from organizational or conversation context.
    suggested query: ("assignee prediction" OR "assignee extraction" OR "responsibility extraction" OR "action owner") (email OR Slack OR "workplace chat") implicit owner group owner context
    searched in rounds: [1, 2, 3] (still open)
- gap-4 [ACADEMIC, HIGH]: The corpus does not establish reliable deadline binding in workplace communication: distinguishing a deadline for a particular action from a merely mentioned date, shared date, scheduling expression, or conditional future time remains open.
    suggested query: ("deadline extraction" OR "due date extraction" OR "deadline detection") (email OR "workplace communication" OR Slack) "action item" temporal relation event argument
    searched in rounds: [1, 2, 3] (still open)
- gap-5 [ACADEMIC, HIGH]: Direct workplace evidence is insufficient for attaching conditions, exceptions, negation, and modality to the correct action when several actions or clauses occur together.
    suggested query: ("conditional commitment" OR "deontic modality" OR "negation scope" OR "condition extraction") (email OR "workplace communication" OR Slack) action attachment obligation
    searched in rounds: [1, 2, 3] (still open)
- gap-6 [ENGINEERING, HIGH]: Build an independent argument-level benchmark and adversarial fixture suite covering implicit owners, multiple actions in one sentence, shared deadlines, conditional and negated actions, overlapping request/commitment labels, quoted-history contamination, and attachment references; score false positives, false negatives, and each argument separately.
- gap-7 [ENGINEERING, HIGH]: Compare sentence-local, message-level, and selectively expanded thread-context extraction with controlled ablations, because the literature shows both context gains and context-induced degradation.
- gap-8 [ENGINEERING, HIGH]: Test author/quoted/forwarded content zoning while preserving provenance, and measure whether zoning improves act and argument extraction without losing obligations whose interpretation depends on prior-message context.
- gap-9 [ENGINEERING, HIGH]: Evaluate an uncertainty-preserving structured output in which owner, deadline, condition, or act subtype can remain unresolved, and measure whether this reduces false obligations and wrong argument assignments without unacceptable recall loss.

The synthesis judged them as follows:
[
 {
  "id": "gap-1",
  "status": "open",
  "note": "MAILEX supplies authentic workplace-email event and argument extraction, EPA supplies email assignees, and several email studies supply speech-act labels, but no paper jointly annotates and evaluates act type, owner, object, deadline, conditions or exceptions, and exact argument provenance.",
  "evidence": [
   "2305.13469",
   "doi-10-18653-v1-w18-6104",
   "manual-d19b0f6f1e",
   "doi-10-1145-3331184-3331260"
  ]
 },
 {
  "id": "gap-2",
  "status": "open",
  "note": "LEDA directly distinguishes proposals and decisions in organizational email, while several meeting papers model decision structure, but the corpus still lacks structured argument extraction for decisions, approvals, rejections, and proposals in authentic workplace email or enterprise chat.",
  "evidence": [
   "doi-10-18653-v1-2023-findings-acl-378",
   "manual-90280d2776",
   "doi-10-3115-1708376-1708410",
   "1606.07965"
  ]
 },
 {
  "id": "gap-3",
  "status": "open",
  "note": "EPA directly establishes implicit, plural, and no-one assignees in email, and Slack and meeting studies show contextual responsibility cues and owner difficulty, but reliable extraction for implicit owners, groups, several actions with different owners, and organization-dependent ownership remains unestablished.",
  "evidence": [
   "doi-10-18653-v1-w18-6104",
   "2312.05471",
   "doi-10-1007-11965152-18",
   "doi-10-3115-1564535-1564540"
  ]
 },
 {
  "id": "gap-4",
  "status": "open",
  "note": "Meeting action-item and general temporal-relation studies provide evidence for timeframe extraction and event-time linking, but no admitted workplace email/chat benchmark directly measures whether a particular date is the deadline of the correct action under multiple, shared, scheduling, or conditional temporal expressions.",
  "evidence": [
   "doi-10-18653-v1-2007-sigdial-1-4",
   "doi-10-1162-tacl-a-00006",
   "doi-10-1109-scc-2013-62",
   "manual-1e8332286e"
  ]
 },
 {
  "id": "gap-5",
  "status": "open",
  "note": "The corpus contains direct workplace evidence that conditional commitments are difficult and substantial transfer evidence for negation and modality scope, but it does not directly validate correct attachment of conditions, exceptions, negation, and modality to several co-occurring workplace actions.",
  "evidence": [
   "manual-0839b98ee7",
   "manual-d19b0f6f1e",
   "1410.4868",
   "2109.09393",
   "doi-10-18653-v1-d16-1078"
  ]
 },
 {
  "id": "gap-6",
  "status": "open",
  "note": "The literature identifies the component failure modes, but it does not perform the project-specific independent argument-level and adversarial evaluation described by this engineering gap.",
  "evidence": [
   "doi-10-18653-v1-w18-6104",
   "doi-10-18653-v1-2020-coling-main-164",
   "manual-0839b98ee7",
   "manual-cd3fa58e4c",
   "2410.03594"
  ]
 },
 {
  "id": "gap-7",
  "status": "open",
  "note": "Published results establish that context can help and can also hurt depending on task and corpus, but the required controlled comparison of sentence-local, message-level, and selectively expanded thread context has not been carried out for the project.",
  "evidence": [
   "doi-10-1145-3331184-3331260",
   "doi-10-1145-1076034-1076094",
   "2303.16763",
   "2305.13469"
  ]
 },
 {
  "id": "gap-8",
  "status": "open",
  "note": "Email zoning improves request detection, while conversational history improves event extraction, but the corpus does not jointly evaluate provenance-preserving zoning against loss of obligations that depend on quoted or earlier-message context.",
  "evidence": [
   "manual-cd3fa58e4c",
   "2305.13469",
   "manual-20b8cd2fdd"
  ]
 },
 {
  "id": "gap-9",
  "status": "open",
  "note": "Several papers expose unresolved owners, difficult implicit arguments, annotator ambiguity, and systems insufficient for unattended annotation, but none evaluates the project-specific effect of nullable structured fields on false obligations, wrong assignments, and recall.",
  "evidence": [
   "doi-10-18653-v1-w18-6104",
   "manual-fde6beef40",
   "2410.03594",
   "manual-0839b98ee7"
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

Reply format (one block containing one JSON object with run_id "5060d000e7b4"
and round 4):
===BEGIN gaps.json===
<content>
===END gaps.json===
