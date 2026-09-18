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

Research topic: **Direct empirical evaluations of longitudinal cross-thread workplace briefing: cycle-by-cycle new/open/resolved/superseded work-item tracking, obligation-versus-preference selection, adaptive personalization under preference drift, and joint omission/repetition/false-alert evaluation.**
Run id: `229b747dc22e`  Round: 4 of at most 4

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
  "description": "This corpus still does not directly evaluate a longitudinal workplace briefing that, across successive report cycles, distinguishes newly changed information from unchanged-but-still-open work while suppressing resolved or superseded information.",
  "classification": "ACADEMIC",
  "priority": "HIGH",
  "suggested_query": "\"incremental summarization\" longitudinal workplace email briefing \"open\" resolved superseded state"
 },
 {
  "id": "gap-2",
  "description": "This corpus still does not establish how explicit user rules or response obligations interact with softer personalized importance, triage, reminder-value, or forgetting signals in briefing selection, nor whether separating these signal classes improves workplace outcomes.",
  "classification": "ACADEMIC",
  "priority": "HIGH",
  "suggested_query": "\"email prioritization\" \"response obligation\" hard constraints soft preferences personalized triage reminder"
 },
 {
  "id": "gap-3",
  "description": "Long-term adaptation to changing user roles, projects, priorities, feedback, and work patterns remains unevaluated in the admitted personalized workplace email or reminder studies; preference-drift evidence in the corpus comes primarily from recommender-system transfer domains.",
  "classification": "ACADEMIC",
  "priority": "HIGH",
  "suggested_query": "\"longitudinal personalization\" workplace email preference drift adaptive prioritization user feedback"
 },
 {
  "id": "gap-4",
  "description": "The corpus still lacks an end-to-end evaluation of briefing content selection that jointly measures omission of decision-essential work, redundant repetition, false alerts, and preservation of unresolved important state over repeated workplace cycles.",
  "classification": "ACADEMIC",
  "priority": "HIGH",
  "suggested_query": "\"longitudinal summarization\" omission redundancy false alerts unresolved state evaluation"
 },
 {
  "id": "gap-5",
  "description": "The admitted studies do not determine how reminder usefulness or likelihood of forgetting combines with perceived importance, urgency, recency, or personalized priority when selecting workplace briefing content.",
  "classification": "ACADEMIC",
  "priority": "MEDIUM",
  "suggested_query": "\"email reminder\" forgetting importance urgency recency personalized priority task selection"
 },
 {
  "id": "gap-6",
  "description": "No admitted paper evaluates topic- or work-item-level incremental briefing across multiple workplace conversations and sources; direct email summarization remains primarily thread- or conversation-level, while incremental longitudinal evidence comes from transfer domains.",
  "classification": "ACADEMIC",
  "priority": "HIGH",
  "suggested_query": "\"cross-thread summarization\" email multi-source incremental \"work item\" workplace"
 },
 {
  "id": "gap-7",
  "description": "Although the corpus contains evidence about stale reminders, epistemic uncertainty, conflicting cues, and uncertainty visualization, it does not experimentally establish how a workplace briefing presents stale, uncertain, disputed, or incompletely investigated state or how alternative presentations affect workplace decisions.",
  "classification": "ACADEMIC",
  "priority": "HIGH",
  "suggested_query": "\"uncertainty visualization\" workplace decision support stale disputed incomplete information briefing"
 },
 {
  "id": "gap-8",
  "description": "Candidate mechanisms from this corpus have not been compared in one reproducible cycle-based benchmark with chronological holdouts, independently labeled new/open/resolved/superseded state, user-specific priority labels, and explicit omission and repetition errors.",
  "classification": "ENGINEERING",
  "priority": "HIGH",
  "classification_note": "The ENGINEERING classification is intentional under the supplied taxonomy because the missing artifact is a reproducible benchmark and comparative experiment that can be constructed from code, public data, and independently authored synthetic or adversarial fixtures without first obtaining another paper. Such an engineering benchmark would not establish production-workplace representativeness; that separate question remains outside what the benchmark itself can prove."
 }
]

Gaps carried over from the previous round (keep their ids):
- gap-1 [ACADEMIC, HIGH]: This corpus does not directly evaluate a longitudinal workplace briefing that, across successive report cycles, distinguishes newly changed information from unchanged-but-still-open work while suppressing resolved or superseded information.
    suggested query: "incremental summarization" longitudinal workplace email briefing "open" resolved superseded state
    searched in rounds: [1, 2, 3] (still open)
- gap-2 [ACADEMIC, HIGH]: This corpus does not establish how explicit user rules or response obligations interact with softer personalized importance, triage, reminder-value, or forgetting signals in briefing selection, nor whether separating these signal classes improves outcomes.
    suggested query: "email prioritization" "response obligation" hard constraints soft preferences personalized triage reminder
    searched in rounds: [1, 2, 3] (still open)
- gap-3 [ACADEMIC, HIGH]: Long-term adaptation to changing user roles, projects, priorities, feedback, and work patterns is not directly evaluated in the admitted personalized workplace email or reminder studies.
    suggested query: "longitudinal personalization" workplace email preference drift adaptive prioritization user feedback
    searched in rounds: [1, 2, 3] (still open)
- gap-4 [ACADEMIC, HIGH]: The corpus does not provide an end-to-end evaluation of briefing content selection that jointly measures omission of decision-essential work, redundant repetition, false alerts, and preservation of unresolved important state over repeated cycles.
    suggested query: "longitudinal summarization" omission redundancy false alerts unresolved state evaluation
    searched in rounds: [1, 2, 3] (still open)
- gap-5 [ACADEMIC, MEDIUM]: The admitted studies do not determine how reminder usefulness or likelihood of forgetting combines with perceived importance, urgency, recency, or personalized priority when selecting content for a briefing.
    suggested query: "email reminder" forgetting importance urgency recency personalized priority task selection
    searched in rounds: [1, 2, 3] (still open)
- gap-6 [ACADEMIC, HIGH]: No admitted paper evaluates topic- or work-item-level incremental briefing across multiple workplace conversations and sources; direct email summarization remains primarily thread- or conversation-level, while incremental evidence comes from transfer domains.
    suggested query: "cross-thread summarization" email multi-source incremental "work item" workplace
    searched in rounds: [1, 2, 3] (still open)
- gap-7 [ACADEMIC, HIGH]: Although the corpus contains evidence about stale reminders, epistemic uncertainty, and conflicting cues, it does not experimentally establish how a workplace briefing presents stale, uncertain, disputed, or incompletely investigated state, or how alternative presentations affect workplace decisions.
    suggested query: "uncertainty visualization" workplace decision support stale disputed incomplete information briefing
    searched in rounds: [1, 2, 3] (still open)
- gap-8 [ENGINEERING, HIGH]: Candidate mechanisms from this corpus have not been compared in one reproducible cycle-based benchmark with chronological holdouts, independently labeled new/open/resolved/superseded state, user-specific priority labels, and explicit omission and repetition errors.

The synthesis judged them as follows:
[
 {
  "id": "gap-1",
  "status": "open",
  "note": "Incremental news and clinical summarization provide transfer evidence, but no admitted study evaluates repeated workplace briefing with explicit new, unchanged-open, resolved, and superseded work-item states.",
  "evidence": [
   "doi-10-18653-v1-2024-acl-long-390",
   "doi-10-64898-2025-11-28-25341233",
   "doi-10-1145-383952-383954"
  ]
 },
 {
  "id": "gap-2",
  "status": "open",
  "note": "The corpus separately studies personalized priority, constrained ranking, hard-versus-soft planning constraints, reminders, and importance, but no admitted workplace study experimentally combines explicit response obligations or user rules with soft personalization signals.",
  "evidence": [
   "manual-50ed5dc808",
   "2403.19795",
   "2202.07088",
   "2403.01365",
   "doi-10-1093-jcmc-zmac001"
  ]
 },
 {
  "id": "gap-3",
  "status": "open",
  "note": "Preference-drift adaptation is directly evaluated in recommender systems, but long-term adaptive personalization under changing workplace roles, projects, priorities, and feedback is not evaluated in the admitted email or reminder studies.",
  "evidence": [
   "doi-10-1016-j-eswa-2021-114890",
   "doi-10-1016-j-eswa-2021-115626",
   "doi-10-1109-access-2022-3182390",
   "doi-10-1145-2523813"
  ]
 },
 {
  "id": "gap-4",
  "status": "open",
  "note": "Temporal-summary evaluations measure combinations of novelty, coverage, redundancy, latency, and off-event material, and email-assistance work measures false positives and task outcomes, but no admitted study jointly evaluates omission, repetition, false alerts, and unresolved-state preservation across repeated workplace briefing cycles.",
  "evidence": [
   "doi-10-1145-383952-383954",
   "doi-10-6028-nist-sp-500-302-tempsumm-overview",
   "manual-bdce973227"
  ]
 },
 {
  "id": "gap-5",
  "status": "open",
  "note": "The corpus separately supplies evidence on perceived importance and urgency, forgotten-task reminder value, prospective-memory importance, and reminder-use determinants, but it does not evaluate their joint contribution to workplace briefing selection.",
  "evidence": [
   "2403.01365",
   "doi-10-1093-jcmc-zmac001",
   "doi-10-3389-fpsyg-2014-00657",
   "doi-10-1186-s41235-019-0195-y",
   "doi-10-3758-s13421-025-01708-x"
  ]
 },
 {
  "id": "gap-6",
  "status": "open",
  "note": "Email summarization evidence remains thread- or conversation-centered, while incremental longitudinal processing is demonstrated in news and clinical transfer domains rather than cross-thread workplace work items.",
  "evidence": [
   "2107.14691",
   "manual-c2f56a571b",
   "doi-10-18653-v1-2024-acl-long-390",
   "doi-10-64898-2025-11-28-25341233"
  ]
 },
 {
  "id": "gap-7",
  "status": "open",
  "note": "Stale reminders, uncertainty visualization, epistemic uncertainty, and conflicting cues are empirically studied, but no admitted paper compares presentation strategies for stale, disputed, uncertain, or incompletely investigated states in workplace briefings.",
  "evidence": [
   "2403.01365",
   "doi-10-1016-j-cag-2014-02-006",
   "doi-10-1098-rsos-181870",
   "doi-10-1609-icwsm-v12i1-15014"
  ]
 },
 {
  "id": "gap-8",
  "status": "open",
  "note": "No supplied study provides the specified unified cycle-based benchmark. The gap remains ENGINEERING because constructing and running the benchmark is feasible as an engineering experiment using independently authored gold labels and chronological fixtures without requiring another publication; production representativeness would remain unproven.",
  "evidence": [
   "doi-10-6028-nist-sp-500-302-tempsumm-overview",
   "doi-10-1145-383952-383954",
   "manual-50ed5dc808",
   "doi-10-1145-3705328-3748164"
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

Reply format (one block containing one JSON object with run_id "229b747dc22e"
and round 4):
===BEGIN gaps.json===
<content>
===END gaps.json===
