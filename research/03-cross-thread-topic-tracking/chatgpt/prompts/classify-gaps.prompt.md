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

Research topic: **Direct enterprise email/chat studies of longitudinal cross-thread conversation or work-item linking, especially evidence for concrete business-event identity and for partial, evolving, subevent, or non-transitive continuity relations in organizational workflows.**
Run id: `2be7131314a5`  Round: 4 of at most 4

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
  "description": "Which evidence combinations actually establish or refute continuity of a concrete work matter across independent workplace messages, conversations, attachments, email, and Teams remains open. The corpus contains direct cross-thread enterprise-email evidence and stronger process/event evidence, but it still does not validate the required combination of subject, customer/project names, conversation ancestry, referenced artifacts, commitments, state compatibility, attachments, and cross-source evidence for the target domain.",
  "classification": "ACADEMIC",
  "priority": "HIGH",
  "suggested_query": "(\"work item identity\" OR \"work matter identity\" OR \"business event coreference\" OR \"cross-document event coreference\") AND (email OR \"workplace communication\" OR enterprise) AND (cross-thread OR cross-document OR cross-source)"
 },
 {
  "id": "gap-2",
  "description": "The application-specific decision policy remains open: the relative cost of false merges versus false splits, thresholds for attachment versus rejection, and exact semantics/calibration of CONTINUE, NEW, and UNCERTAIN must be determined from msgloom requirements and empirical evaluation. The corpus supports reject options and risk-coverage trade-offs but does not establish msgloom's loss function or false-merge cost.",
  "classification": "ENGINEERING",
  "priority": "HIGH"
 },
 {
  "id": "gap-3",
  "description": "The msgloom correction and identity-state model remains open. Stable Topic IDs independent of generated labels or source thread IDs, versioned identity assessments, supersession links, immutable evidence lineage, and general MERGE/SPLIT correction require project-level design and testing. Incremental entity-resolution and stable-ID papers establish useful mechanisms but not msgloom's required history semantics.",
  "classification": "ENGINEERING",
  "priority": "HIGH"
 },
 {
  "id": "gap-4",
  "description": "There is still no direct production-domain evidence in this corpus for longitudinal work-matter identity across Outlook email and Microsoft Teams. The direct enterprise-email study and enterprise-process literature are useful adjacent evidence but do not establish production accuracy or representativeness for msgloom's Outlook-plus-Teams environment.",
  "classification": "ACADEMIC",
  "priority": "HIGH",
  "suggested_query": "(enterprise OR workplace OR organizational) AND (email OR \"Microsoft Teams\" OR \"enterprise chat\" OR \"workplace chat\") AND (cross-thread OR longitudinal OR cross-conversation) AND (\"topic identity\" OR \"task tracking\" OR \"case tracking\" OR \"event coreference\" OR \"conversation linking\")"
 },
 {
  "id": "gap-5",
  "description": "How partial, subevent, evolving, membership, or otherwise non-transitive relations should map onto workplace work-matter continuity remains unresolved. The corpus strongly establishes that these relations exist and can violate transitivity, but it does not define when they should mean CONTINUE, RELATED-BUT-SEPARATE, MERGE, SPLIT, or another workplace-specific relation.",
  "classification": "ACADEMIC",
  "priority": "HIGH",
  "suggested_query": "(\"partial event identity\" OR \"partial coreference\" OR \"subevent relation\" OR \"event evolution\" OR \"event membership\" OR \"non-transitive coreference\") AND (workflow OR task OR case OR workplace OR enterprise)"
 },
 {
  "id": "gap-6",
  "description": "The best operational strategy for Phase 2 evidence seeking remains unresolved. Retrieval-based event-coreference search and global-context models show that additional evidence can matter, but msgloom still needs engineering benchmarks for bounded historical retrieval, candidate generation, latency, retrieval stopping rules, and whether retrieved context actually changes identity decisions correctly.",
  "classification": "ENGINEERING",
  "priority": "MEDIUM"
 },
 {
  "id": "gap-7",
  "description": "Calibration under non-stationary workplace streams remains unresolved. The corpus provides substantial evidence that calibration deteriorates under distribution shift and that drift-aware, selective, or conformal approaches can help, but it does not establish reliable calibration, abstention thresholds, or coverage guarantees for longitudinal workplace coreference or clustering.",
  "classification": "ACADEMIC",
  "priority": "MEDIUM",
  "suggested_query": "(\"selective classification\" OR abstention OR \"confidence calibration\" OR \"selective prediction\") AND (\"distribution shift\" OR nonstationary OR streaming OR \"concept drift\") AND (text OR NLP OR coreference OR clustering)"
 }
]

Gaps carried over from the previous round (keep their ids):
- gap-1 [ACADEMIC, HIGH]: Which evidence combinations actually establish or refute continuity of a concrete work matter across independent workplace messages, conversations, attachments, email, and Teams remains open. The corpus now contains direct cross-thread enterprise-email evidence and stronger process/event evidence, but it still does not validate the required combination of subject, customer/project names, conversation ancestry, referenced artifacts, commitments, state compatibility, attachments, and cross-source evidence for the target domain.
    suggested query: ("work item identity" OR "work matter identity" OR "business event coreference" OR "cross-document event coreference") AND (email OR "workplace communication" OR enterprise) AND (cross-thread OR cross-document OR cross-source)
    searched in rounds: [1, 2, 3, 4] (still open)
- gap-2 [ENGINEERING, HIGH]: The application-specific decision policy remains open: the relative cost of false merges versus false splits, thresholds for attachment versus rejection, and exact semantics/calibration of CONTINUE, NEW, and UNCERTAIN must be determined from msgloom requirements and empirical evaluation. The corpus supports reject options and risk-coverage trade-offs but does not establish msgloom's loss function or false-merge cost.
- gap-3 [ENGINEERING, HIGH]: The msgloom correction and identity-state model remains open. Stable Topic IDs independent of generated labels or source thread IDs, versioned identity assessments, supersession links, immutable evidence lineage, and general MERGE/SPLIT correction require project-level design and testing. Incremental entity-resolution and stable-ID papers establish useful mechanisms but not msgloom's required history semantics.
- gap-4 [ACADEMIC, HIGH]: There is still no direct production-domain evidence in this corpus for longitudinal work-matter identity across Outlook email and Microsoft Teams. The direct enterprise-email study and enterprise-process literature are useful adjacent evidence but do not establish production accuracy or representativeness for msgloom's Outlook-plus-Teams environment.
    suggested query: (enterprise OR workplace OR organizational) AND (email OR "Microsoft Teams" OR "enterprise chat" OR "workplace chat") AND (cross-thread OR longitudinal OR cross-conversation) AND ("topic identity" OR "task tracking" OR "case tracking" OR "event coreference" OR "conversation linking")
    searched in rounds: [1, 2, 3, 4] (still open)
- gap-5 [ACADEMIC, HIGH]: How partial, subevent, evolving, membership, or otherwise non-transitive relations should map onto workplace work-matter continuity remains unresolved. The corpus strongly establishes that these relations exist and can violate transitivity, but it does not define when they should mean CONTINUE, RELATED-BUT-SEPARATE, MERGE, SPLIT, or another workplace-specific relation.
    suggested query: ("partial event identity" OR "partial coreference" OR "subevent relation" OR "event evolution" OR "event membership" OR "non-transitive coreference") AND (workflow OR task OR case OR workplace OR enterprise)
    searched in rounds: [1, 2, 3, 4] (still open)
- gap-6 [ENGINEERING, MEDIUM]: The best operational strategy for Phase 2 evidence seeking remains unresolved. Retrieval-based event-coreference search and global-context models show that additional evidence can matter, but msgloom still needs engineering benchmarks for bounded historical retrieval, candidate generation, latency, retrieval stopping rules, and whether retrieved context actually changes identity decisions correctly.
- gap-7 [ACADEMIC, MEDIUM]: Calibration under non-stationary workplace streams remains unresolved. The corpus provides substantial evidence that calibration deteriorates under distribution shift and that drift-aware, selective, or conformal approaches can help, but it does not establish reliable calibration, abstention thresholds, or coverage guarantees for longitudinal workplace coreference or clustering.
    suggested query: ("selective classification" OR abstention OR "confidence calibration" OR "selective prediction") AND ("distribution shift" OR nonstationary OR streaming OR "concept drift") AND (text OR NLP OR coreference OR clustering)
    searched in rounds: [1, 2, 3, 4] (still open)

The synthesis judged them as follows:
[
 {
  "id": "gap-1",
  "status": "open",
  "note": "Round 4 strengthens adjacent evidence: enterprise email demonstrates cross-thread work-activity linking, and process/event studies identify useful combinations of content, participants, objects, time, and constraints. No corpus paper validates the required evidence combination for concrete cross-message, attachment, email, and Teams work-matter identity in the target domain.",
  "evidence": [
   "doi-10-1145-1111449-1111471",
   "1906.01753",
   "2206.10009",
   "2607.26384"
  ]
 },
 {
  "id": "gap-2",
  "status": "open",
  "note": "Three-way linkage, open-world rejection, and selective-risk literature establishes mechanisms for abstention and thresholding, but no paper supplies msgloom's loss function, false-merge cost, or operational semantics for CONTINUE, NEW, and UNCERTAIN.",
  "evidence": [
   "doi-10-1080-01621459-1969-10501049",
   "1412.5687",
   "1705.08500",
   "2405.05160"
  ]
 },
 {
  "id": "gap-3",
  "status": "open",
  "note": "Incremental entity resolution, stream clustering, and StableID demonstrate local repair, merge/split handling, and persistent identifiers, but they do not specify msgloom's versioned assessment, supersession, immutable lineage, or correction contract.",
  "evidence": [
   "1402.4417",
   "doi-10-1007-978-3-030-49461-2-23",
   "doi-10-1109-tbdata-2022-3204207",
   "doi-10-3390-industries1010003"
  ]
 },
 {
  "id": "gap-4",
  "status": "open",
  "note": "The corpus now has direct enterprise-email evidence and cross-organizational process evidence, but no study establishes longitudinal work-matter identity accuracy or representativeness across production Outlook email and Microsoft Teams.",
  "evidence": [
   "doi-10-1145-1111449-1111471",
   "doi-10-1145-1111449-1111472",
   "doi-10-1109-access-2023-3284053"
  ]
 },
 {
  "id": "gap-5",
  "status": "open",
  "note": "The corpus strongly establishes partial identity, subevent, membership, hierarchy, spatiotemporal continuity, and possible non-transitivity, but no paper maps those relations to workplace decisions such as CONTINUE, RELATED-BUT-SEPARATE, MERGE, or SPLIT.",
  "evidence": [
   "2109.06417",
   "manual-c43ffe3135",
   "manual-35bac66e3c",
   "2211.07342",
   "doi-10-3115-v1-w14-2910"
  ]
 },
 {
  "id": "gap-6",
  "status": "open",
  "note": "Coreference search and discourse-context models show that external historical context can improve identity evidence, but no corpus paper determines msgloom-specific candidate generation, retrieval bounds, stopping rules, latency targets, or decision-change utility.",
  "evidence": [
   "doi-10-18653-v1-2022-emnlp-main-58",
   "doi-10-18653-v1-2023-emnlp-main-294",
   "doi-10-1016-j-ipm-2025-104085"
  ]
 },
 {
  "id": "gap-7",
  "status": "open",
  "note": "Cross-corpus and distribution-shift studies confirm that calibration and confidence ranking degrade under shift and provide candidate mitigation techniques, but reliable thresholds and coverage guarantees for non-stationary workplace coreference remain unvalidated.",
  "evidence": [
   "2011.12249",
   "2405.05160",
   "doi-10-18653-v1-2024-findings-emnlp-725",
   "manual-03d6dfa532",
   "doi-10-1038-s41598-026-40637-w"
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

Reply format (one block containing one JSON object with run_id "2be7131314a5"
and round 4):
===BEGIN gaps.json===
<content>
===END gaps.json===
