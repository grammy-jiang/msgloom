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

# Task: literature search

Research topic: **authentic workplace email and enterprise-chat benchmarks for structured action/decision extraction, focusing specifically on implicit and group assignees, action-to-deadline binding, condition/negation/modality scope, and exact argument evidence spans**

Must-have terms: authentic, workplace, email
Nice-to-have terms: enterprise-chat, structured, action/decision, extraction,, focusing, specifically, implicit, group, assignees,, action-to-deadline, binding,, condition/negation/modality, scope,, exact, argument, evidence, spans
Date range: {"primary_months": 300, "fallback_months": 480}

Run every query below with your web search tool. Prefer arXiv listings
(arxiv.org/abs/<id>) but include other venues when they are clearly relevant;
much of the foundational work in a field is in conference proceedings rather
than on arXiv, and it must not be dropped for that reason. Aim for 30-60
distinct papers (at least 5). Stop when new searches only return papers
already listed.

Query families (from the terminology analysis; DIRECT means the
literature studies this problem, TRANSFER means the method may carry
over from another domain). Run every query:
- F1 [DIRECT]
    "action item" (extraction OR detection OR identification) (email OR "business email" OR "workplace email") corpus annotation
    ("actionable item" OR "actionable sentence" OR "task extraction") Enron email annotation
    "task-focused summarization" email action items
    (email OR Enron) ("task intent" OR "task sentence") annotation extraction
    ("action item extraction" OR "task extraction") email (owner OR assignee OR deadline OR condition OR argument)
- F2 [DIRECT]
    "requests-for-action" email
    "commitments-to-act" email
    (request OR commitment) "workplace email" annotation speech act
    ("commitment detection" OR "commitment extraction") email Enron
    "email speech acts" (request OR commit OR proposal) corpus
    (commissive OR promise OR obligation) email NLP workplace
- F3 [DIRECT]
    "addressee tagging" "task intent" email
    "people assignment" task email NLP
    "Enron People Assignment"
    (email OR Enron) task "responsible person" extraction
    (email OR "workplace email") (assignee OR responsibility OR responsible) task extraction
    (email OR Enron) task assignment (implicit OR context OR addressee OR recipient)
    (email OR Enron) task assignment (group OR multiple OR multi-recipient OR "person(s)")
- F4 [DIRECT]
    ("decision extraction" OR "decision detection") (email OR "business email" OR "workplace email" OR "enterprise chat") corpus
    (approval OR rejection OR acceptance OR proposal) detection (email OR "enterprise chat" OR "workplace communication") NLP
    ("speech act" OR "dialogue act") (approval OR reject OR rejection OR proposal OR acceptance) email
    (decision OR approval OR rejection OR proposal) (Slack OR Teams OR "enterprise messaging" OR "business chat") corpus annotation
    ("decision extraction" OR "proposal extraction") workplace (actor OR argument OR span OR proposition)
- F5 [TRANSFER]
    "action item detection" meeting annotation assignee
    "action item assignment" meeting dialogue annotation
    "detecting and summarizing action items" dialogue
    "decision detection" "multi-party dialogue"
    "decision-related dialogue acts" meeting
    (proposal OR commitment OR decision) meeting dialogue act annotation
    "action item" meeting (owner OR assignee OR deadline OR argument OR condition)
- F6 [TRANSFER]
    "event argument extraction" span argument roles
    "span-based event extraction" arguments
    ("argument span extraction" OR "trigger argument extraction") event
    "semantic role labeling" exact span arguments
    (event OR predicate) argument extraction (actor OR agent OR recipient OR time) span
    "document-level event argument extraction" implicit arguments
- F7 [TRANSFER]
    "implicit argument resolution" NLP discourse
    "implicit semantic role labeling" discourse
    "implicit argument" semantic role labeling context
    "implicit argument recovery" NLP
    (implicit OR omitted) argument (agent OR actor OR addressee) resolution
    "implicit arguments" discourse context semantic roles
- F8 [TRANSFER]
    "event-time relation extraction" NLP
    "event time relation" temporal information extraction
    "temporal anchoring" events TimeBank
    "event time extraction" temporal argument
    ("temporal relation extraction" OR "event-time linking") event time expression
    (task OR action) ("event-time relation" OR "temporal anchoring" OR "time argument")
    (email OR workplace) task deadline ("temporal relation" OR "event-time" OR "time argument")
- F9 [TRANSFER]
    "negation scope resolution" event
    "negated event" "scope resolution" NLP
    "speculation scope resolution" NLP
    (modality OR modal) scope event extraction NLP
    "deontic modality" obligation extraction scope
    (obligation OR permission OR prohibition) extraction "deontic modality"
    (request OR commitment OR action) (negation OR modality) scope NLP
- F10 [TRANSFER]
    "conditional relation extraction" NLP event
    (condition OR prerequisite OR exception) "relation extraction" action
    "condition-action" relation extraction NLP
    (conditional OR condition) event argument extraction
    (unless OR exception) scope extraction NLP
    "conditional obligation" extraction NLP
    (request OR commitment OR obligation) condition attachment NLP
- F11 [DIRECT]
    (email OR "enterprise chat" OR workplace) "action item" "span annotation"
    (email OR "workplace communication") (request OR commitment OR decision) "argument span"
    (email OR "enterprise messaging") action (actor OR owner) deadline condition "span" corpus
    ("action item" OR request OR commitment) "exact span" annotation email
    (workplace OR email) "structured extraction" (owner OR assignee) deadline condition evidence
    (email OR chat) communicative event "trigger" "argument" annotation
- F12 [DIRECT]
    ("enterprise messaging" OR "enterprise chat" OR "workplace chat") corpus (request OR commitment OR decision OR action)
    (Slack OR "Microsoft Teams" OR Mattermost) corpus (action item OR request OR commitment OR decision) NLP
    ("organizational communication" OR "workplace communication") corpus task assignment NLP
    ("business chat" OR "collaboration platform") corpus speech act action item
    (Slack OR Teams OR "enterprise messaging") annotation (assignee OR deadline OR decision OR proposal)
False friends — these match the words but not the capability, so do
not list them:
- Downgrade any paper that only classifies a whole message, conversation, or sentence as actionable when it does not annotate or evaluate the action arguments needed by the project.
- Downgrade action-item detection papers that cannot distinguish several actions within one sentence or dialogue region.
- Downgrade generic intent classification unless its labels explicitly distinguish workplace-relevant acts such as request-for-action, commitment, proposal, approval, rejection, or decision.
- Downgrade request detection that only identifies questions or requests-for-information and does not distinguish requests-for-action.
- Downgrade commitment or promise work that provides only sentence-level labels when owner, action content, condition, or other arguments are unavailable.
- Downgrade decision detection that labels decision-related dialogue regions but provides no evidence about the actual decision proposition or decision act.
- Downgrade agreement, approval, or rejection work if it assumes the antecedent proposition is known and offers no evidence relevant to Topic 05 act classification; antecedent resolution itself remains Topic 04.
- Downgrade event extraction that treats an action mention and an assigned/requested/committed action as equivalent.
- Downgrade SRL or event-argument papers when all arguments are overt and sentence-local if they are being used as evidence for implicit-owner recovery.
- Downgrade zero-anaphora work as evidence for English workplace owner extraction unless it demonstrates a transferable omitted-argument mechanism rather than only pro-drop-language restoration.
- Downgrade temporal-expression recognition or normalization when no relation is annotated between the time expression and a specific action/event.
- Downgrade deadline systems that infer a deadline from proximity to a date without evaluating action-to-time binding.
- Downgrade scheduling and calendar-event extraction that treats mentioned dates as events or deadlines by default.
- Downgrade condition detection when it only classifies a sentence as conditional and does not identify which action or proposition is governed by the condition.
- Downgrade negation detection that identifies only the cue and not the scope or negated event.
- Downgrade modality classification when epistemic possibility, ability/capability, intention, and deontic obligation are collapsed into one undifferentiated label.
- Downgrade hedge/speculation papers used as direct evidence for obligations; they are only transfer evidence for cue-and-scope modeling.
- Downgrade responsibility-assignment papers based on project scheduling, organization design, or resource optimization rather than language understanding.
- Downgrade assignee prediction from bug trackers, issue trackers, or ticket-routing systems unless the model actually resolves assignees from natural-language action expressions.
- Downgrade datasets constructed from synthetic email, generated chat, or templated examples when claiming authentic workplace evidence.
- Downgrade meeting-transcript results from DIRECT to TRANSFER for claims about written email or enterprise chat.
- Downgrade customer-service, social-media, telephone-dialogue, and open-domain chat evidence from DIRECT to TRANSFER unless the corpus is genuine organizational work communication.
- Downgrade benchmarks that report only aggregate act accuracy when argument-level false positives, false negatives, or role errors cannot be recovered.
- Downgrade extraction systems that generate normalized task summaries but do not preserve source spans or provenance sufficient to verify each argument.
- Downgrade work that silently forces unknown owner, deadline, condition, or act subtype into a label rather than permitting unresolved or absent arguments.
- Downgrade quoted-message or forwarded-history extraction when author/source zoning is not preserved and the system cannot distinguish a current obligation from quoted historical text.
- Do not treat a paper as closing gap-1 unless its annotation jointly covers, or provides empirically separable evaluation for, act/action type plus multiple key arguments and exact supporting evidence spans.
- Do not treat a paper as closing gap-2 merely because it summarizes decisions; it must empirically distinguish at least some of decision, proposal, approval/acceptance, or rejection and identify the associated content.
- Do not treat a paper as closing gap-3 if assignees are always explicit named entities in the same sentence; implicit, contextual, group, or multi-action ownership must be separately evidenced.
- Do not treat a paper as closing gap-4 if it only recognizes or normalizes time expressions; a relation between the time and the correct action must be evaluated.
- Do not treat a paper as closing gap-5 if it merely detects negation, modality, or conditional cues; scope or attachment to the correct action must be evaluated.
Reach back to 1997 at least. Discovery should reach at least 1997. Direct computational work on email speech acts and email action items becomes visible in the early 2000s, especially 2004, but the transferable empirical dialogue-act lineage needed to interpret request, acceptance, rejection, agreement, proposal, and other communicative-function terminology is already established by DAMSL work in 1997. Starting at 2004 would silently exclude that foundational annotation vocabulary. There is no need for bulk discovery to extend back to classical philosophical speech-act theory unless a later paper explicitly requires it; the purpose here is empirical NLP benchmark and extraction terminology.

This is gap-closure round 4 of at most 4 for the
original topic **authentic workplace email and enterprise-chat extraction of structured action and decision arguments, with emphasis on implicit or group assignees, deadline-to-action relations, condition/negation/modality attachment, and exact evidence-span annotation**. Earlier rounds could not
close the open gaps below. Run every suggested query as well, and look
specifically for papers that answer these gaps:
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

Papers already reviewed in earlier rounds (do NOT list them again):
1410.4868, 1606.07849, 1909.03546, 1909.10094, 2005.13084, 2106.08037, 2202.12109, 2303.16763, 2312.05471, 2409.18602, 2410.03594, doi-10-1007-11965152-18, doi-10-1109-hicss-2006-528, doi-10-1109-scc-2013-62, doi-10-1145-1076034-1076094, doi-10-1145-1076034-1076140, doi-10-1145-3289600-3290984, doi-10-1145-3331184-3331260, doi-10-1162-tacl-a-00006, doi-10-1186-1471-2105-9-s11-s9, doi-10-18653-v1-2007-sigdial-1-4, doi-10-18653-v1-2020-acl-main-667, doi-10-18653-v1-2020-coling-main-164, doi-10-18653-v1-2023-findings-acl-378, doi-10-18653-v1-d16-1078, doi-10-18653-v1-w18-6104, doi-10-3115-1564535-1564540, doi-10-3115-1708376-1708410, manual-01c535c108, manual-0839b98ee7, manual-1e8332286e, manual-20b8cd2fdd, manual-69bc2555ab, manual-90280d2776, manual-cd3fa58e4c, manual-d19b0f6f1e, manual-e6bb5aee88, manual-ee40d588e3, manual-fde6beef40

Write one JSON object per line. Fields (only `title` is mandatory):
- title: exact paper title
- url: arxiv.org/abs/<id> when available, else the landing page
- arxiv_id: e.g. 2401.12345 (omit when not on arXiv)
- doi: if known
- authors: list of author names
- year: integer
- published: YYYY-MM-DD if known
- abstract: the abstract, or a faithful paraphrase of at most 5 sentences
- venue: conference or journal if known

Reply format (one block, one JSON object per line, no array brackets):
===BEGIN llm_candidates.jsonl===
<content>
===END llm_candidates.jsonl===
