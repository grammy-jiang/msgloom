# authentic workplace email and enterprise-chat benchmarks for structured action/decision extraction, focusing specifically on implicit and group assignees, action-to-deadline binding, condition/negation/modality scope, and exact argument evidence spans academic terminology analysis

## Product problem

The target is not generic intent classification, generic summarization, or extraction of verbs and dates. The required object is a structured communicative event such as a request, commitment, decision, approval, proposal, or action item, with independently recoverable arguments:

- actor / owner / responsible person or group;
- action or decision content;
- recipient or beneficiary where relevant;
- deadline only when semantically attached to that action;
- conditions, prerequisites, exceptions, negation, and modality;
- exact source span or spans supporting the act and each argument;
- unresolved fields when the source does not justify a value.

The terminology audit therefore separates three levels that are frequently conflated in search results:

1. **Act or action detection:** does this sentence/utterance contain a request, commitment, decision, or action item?
2. **Argument extraction:** who is responsible, what is the action, and what other roles are expressed?
3. **Scope and relation attachment:** which action is negated, conditional, modalized, or governed by a particular time expression?

Rounds 1–3 appear to have searched many correct-looking surface terms but may have missed literature filed under more specific names. Three especially important refinements are:

- **owner extraction → task-person assignment / addressee tagging for detected task intent;**
- **deadline extraction → event-time relation extraction / event-time linking / temporal anchoring;**
- **condition or negation detection → scope resolution and relation attachment.**

A direct precedent for the first refinement is the Enron People Assignment work, whose task is explicitly framed as associating detected email tasks with the person or persons responsible for them. citeturn702556search1turn702556search4

Likewise, early workplace-email literature already used the more precise distinction **Requests-for-Action** versus **Commitments-to-Act**, rather than generic request or intent classification. Lampert, Dale, and Paris explicitly motivated these categories by the need to identify utterances that place responsibility for action on the author or another participant. citeturn702556search0turn702556search10

## Seed keyword audit

| Seed | Academic meaning | Fit | Main risk |
| --- | --- | --- | --- |
| action item extraction | Extract task/action content discussed in communication | STRONG | Often means detection or summarization, not structured owner/deadline/condition extraction |
| action item detection | Classify sentences, utterances, or subdialogues as action-item related | STRONG | Binary detection is weaker than argument-level extraction |
| task extraction | Extract textual task descriptions | MODERATE | Overloaded with procedural/task-model literature |
| to-do extraction | Produce personal or collaborative to-do items from text | MODERATE | More common in applications than stable academic terminology |
| task-oriented information extraction | IE optimized for a downstream task | WEAK | Frequently unrelated to extracting workplace tasks |
| email speech act classification | Classify communicative functions in email | STRONG | Older work may be message-level and argument-free |
| dialogue act classification | Classify communicative functions of dialogue utterances | MODERATE | Very broad labels/domains; usually no task arguments |
| request detection | Detect request speech acts | STRONG | Request-for-information and request-for-action may be conflated |
| request identification | Identify linguistic requests | STRONG | Same ambiguity as request detection; terminology less standardized |
| commissive speech acts | Acts committing the speaker to future action | STRONG | Large non-computational pragmatics literature |
| commitment extraction | Extract commitments to future action | STRONG | “Commitment” has unrelated organizational and formal meanings |
| commitment detection | Detect spans/sentences expressing commitments | STRONG | Frequently sentence-level only |
| promise detection | Detect promises as commissive acts | MODERATE | Narrower than ordinary workplace commitment |
| obligation detection | Detect duties, requirements, permissions, prohibitions | STRONG | Dominated by legal/regulatory text |
| deontic modality | Obligation, permission, prohibition and related normative modality | STRONG | Often legal rather than conversational |
| intention detection | Detect expressed intention or conversational intent | WEAK | Generic chatbot/user-intent literature dominates |
| intent-to-act | Expressed intention to perform an action | WEAK | Not a stable canonical NLP task name |
| decision extraction | Extract decisions or decision-containing discourse | STRONG | May not distinguish proposal/approval/rejection or arguments |
| decision detection | Classify decision-related text | STRONG | Frequently identifies a region rather than the decided proposition |
| meeting decision detection | Detect decisions in meeting dialogue | STRONG | Strong semantic transfer, but not direct email/chat evidence |
| event extraction | Extract event triggers and possibly arguments | MODERATE | Mentioned actions are not necessarily assigned actions |
| event argument extraction | Extract semantic roles associated with events | STRONG | Good argument machinery but generic schemas lack speech-act semantics |
| semantic role labeling | Predicate-argument labeling | MODERATE | Usually explicit/local roles and no request/commitment status |
| implicit argument resolution | Recover discourse arguments not overt with a predicate | STRONG | Benchmarks usually are not workplace-owner datasets |
| zero anaphora | Resolve omitted arguments, especially in pro-drop languages | WEAK | Poor primary term for English implicit assignees |
| omitted argument recovery | Recover unexpressed predicate arguments | MODERATE | Less standardized than implicit argument resolution |
| conditionality detection | Detect conditional constructions or relations | STRONG | Presence detection does not establish attachment |
| hedge detection | Detect weakened epistemic commitment | WEAK | Hedge ≠ condition or deontic modality |
| speculation detection | Detect speculative propositions and sometimes their scope | MODERATE | Primarily epistemic uncertainty |
| modality detection | Detect modal meanings | MODERATE | Ability, possibility, intention, and obligation may be conflated |
| temporal expression extraction | Identify dates/times/durations | MODERATE | Date mention ≠ deadline |
| temporal expression normalization | Normalize temporal phrases | MODERATE | Normalization ≠ action-to-time binding |
| deadline extraction | Extract due dates or deadlines | STRONG | Weakly standardized; may rely on proximity rather than semantic relation |
| responsibility assignment | Identify/assign actors responsible for tasks | STRONG | Management/operations-research literature dominates without NLP constraints |
| owner assignment | Identify the responsible owner | MODERATE | “Owner” is highly ambiguous across domains |
| assignee extraction | Extract the assigned person | STRONG | Bug/ticket assignment dominates search results |
| email action-item corpora | Email datasets annotated for tasks/actions | STRONG | Relevant datasets may use completely different terminology |
| request-response corpora | Corpora pairing requests/questions with responses | MODERATE | QA, response generation and customer service dominate |

The early direct-email anchors are unusually useful terminology guides. Corston-Oliver et al. explicitly describe automatic identification of action items in email, while Cohen, Carvalho, and Mitchell frame email classification through speech acts. citeturn190358search2turn190358search1

## Academic task families

### F1 — Workplace email action-item and task extraction — DIRECT

Search for authentic business-email datasets in which actionable content is detected or extracted.

The foundational direct seed is **Task-Focused Summarization of Email** (Corston-Oliver et al., 2004), which explicitly treats action items/tasks in email as the target. citeturn190358search0turn190358search2

The admission bar for round 4 should be higher than simple task-sentence detection: papers become especially valuable when they expose task spans, semantic arguments, context dependencies, or multi-task cases.

### F2 — Requests-for-Action and Commitments-to-Act — DIRECT

Promote the historical workplace-email terminology:

- **Requests-for-Action**
- **Commitments-to-Act**
- **email speech acts**
- **commitment detection in email**

This vocabulary is substantially more precise than generic “request detection” or “intent detection.” The Lampert/Dale/Paris work specifically studies workplace email and emphasizes indirect realization and context-dependent interpretation. citeturn702556search0turn702556search67

**Domain Adaptation for Commitment Detection in Email** is another direct anchor for the term “commitment detection” in actual email research. citeturn227971search5

### F3 — Task-person assignment / addressee tagging — DIRECT

This should become the primary gap-3 search family.

Promote:

- **people assignment**
- **addressee tagging for detected task intent**
- **responsible person(s)**
- **task-person assignment**
- **multi-recipient task assignment**

The EPA paper is directly on this problem: tasks in Enron email are associated with the person or persons responsible for carrying them out. citeturn702556search1

This is a major terminology correction. Searching only for “assignee extraction,” “owner assignment,” or “responsibility extraction” is liable to miss precisely the most relevant direct email benchmark.

Round 4 should drill further into whether EPA or follow-on work contains:

- implicit addressees;
- group responsibility;
- several tasks with different responsible parties;
- owners recoverable from greetings, message headers, thread context, or organizational context;
- explicit versus inferred responsibility.

### F4 — Structured decisions, proposals, approvals, and rejections — DIRECT

This is the direct gap-2 family.

Search terms must enumerate the act subtypes rather than relying on “decision extraction” alone:

- decision;
- proposal;
- approval / acceptance;
- rejection;
- agreement / disagreement where used as decision acts.

A paper that merely detects a “decision-related” sentence does not close the gap. The useful benchmark must identify what act occurred and the associated decision/proposal content.

Topic 04's boundary remains in force: determining **what prior proposition an approval or rejection refers to** is response-scope resolution. Topic 05 should search for act classification and argument extraction, not silently claim that an approval label establishes correct antecedent scope.

### F5 — Meeting action-item and decision discourse modeling — TRANSFER

Meeting literature is a strong transfer source because it models how actions and decisions emerge across several utterances.

Useful anchors include:

- **Detecting Action Items in Multi-party Meetings: Annotation and Initial Experiments**;
- **Detecting and Summarizing Action Items in Multi-Party Dialogue**;
- **What Decisions Have You Made?: Automatic Decision Detection in Meeting Conversations**;
- **Modelling and Detecting Decisions in Multi-party Dialogue**. citeturn190358search9turn737877search1turn190358search7turn936407search3

Purver et al. are particularly relevant because they model action-item subdialogues and then extract phrases describing the task, rather than treating action-item detection as an isolated sentence classification problem. citeturn737877search52

Modern meeting work should remain transfer evidence. For example, more recent action-item detection research explicitly studies local/global context, but its meeting-domain performance cannot establish email or enterprise-chat accuracy. citeturn737877academia54

### F6 — Span-based event and predicate argument extraction — TRANSFER

Promote:

- **event argument extraction**;
- **span-based event extraction**;
- **argument span extraction**;
- **trigger-argument extraction**;
- **semantic role labeling**.

The transfer value is not the event ontology itself. It is the annotation and evaluation machinery for representing:

`action/act → actor + object + recipient + time + condition`

with exact spans and independent role errors.

This family is especially relevant to gap-1 and engineering gap-6 because msgloom should score each argument separately rather than accept a single sentence-level F1.

### F7 — Implicit semantic role labeling / implicit argument resolution — TRANSFER

Promote **implicit argument resolution** and **implicit semantic role labeling** over “zero anaphora.”

Gerber and Chai's work established an explicit NLP task around semantic arguments that are not locally realized and may need to be recovered from preceding discourse. citeturn725034search0

This is not direct evidence for implicit email owners, but it supplies the appropriate academic vocabulary for mechanisms capable of recovering omitted actor/object roles.

“Zero anaphora” should remain a secondary transfer term because much of that literature concerns Japanese, Chinese, Korean, and other pro-drop phenomena rather than English business-email assignment.

### F8 — Event-time relation extraction / temporal anchoring — TRANSFER

This is the most important correction for gap-4.

The project does **not** primarily need another date recognizer. It needs:

`action A ──deadline/time relation──> temporal expression T`

Therefore promote:

- **event-time relation extraction**;
- **event-time linking**;
- **temporal anchoring**;
- **time argument extraction**.

**Temporal Anchoring of Events for the TimeBank Corpus** is a clear example of a task in which events are explicitly linked to time rather than merely detecting TIMEX expressions. citeturn936407search0

A deadline paper cannot close gap-4 if it only recognizes “Friday” or normalizes it to a date. It must establish that Friday belongs to the correct action.

### F9 — Negation, speculation, and modality scope resolution — TRANSFER

Promote **scope resolution**, not merely cue detection.

For negation, the mature terminology is:

- negation cue;
- negation scope;
- negated event;
- scope resolution.

The *SEM 2012 shared task explicitly evaluated negation cues, scopes, and negated events, including exact-match-style evaluation. citeturn936407search1turn936407search2

That structure maps well to msgloom's requirement:

`No action needed unless X happens`

must not become an unconditional action item.

For modality, queries should combine **deontic modality** with obligation, permission, prohibition, request, or commitment. Generic modality detection is too broad because capability (“can do”) must remain different from commitment (“will do”).

### F10 — Conditional relation and exception attachment — TRANSFER

Promote relation-level terminology:

- **conditional relation extraction**;
- **condition-action relation**;
- **conditional obligation**;
- **exception attachment**;
- **prerequisite-action relation**.

A classifier that says “this sentence contains an if-clause” is insufficient.

The project needs:

`condition C ──governs──> action A`

and must handle several actions in the same sentence without attaching C to all of them.

### F11 — Span-level structured communicative-event annotation — DIRECT

This family deliberately searches for the benchmark that gap-1 says has not yet been found.

The decisive terminology is the conjunction of:

- workplace/email/chat domain;
- communicative act or action-item type;
- actor/owner;
- deadline/time argument;
- condition/modality;
- **span annotation / argument span / trigger-argument annotation**.

Do not weaken the search because a paper has only sentence labels. Round 4 should actively test whether a genuinely structured benchmark exists under event-extraction rather than action-item terminology.

### F12 — Authentic enterprise-messaging benchmarks — DIRECT

Previous searches may have over-weighted “Slack” and “workplace chat,” neither of which is necessarily the vocabulary authors use.

Add:

- **enterprise messaging**;
- **organizational communication**;
- **business chat**;
- **collaboration platform**;
- named systems such as Slack, Microsoft Teams, and Mattermost.

The admission criterion remains strict: a commercial system or product feature is not a benchmark. The corpus must represent authentic organizational communication and expose enough annotation/evaluation detail to answer one of the academic gaps.

## Query families

### F1 — DIRECT: workplace email action items

- `"action item" (extraction OR detection OR identification) (email OR "business email" OR "workplace email") corpus annotation`
- `("actionable item" OR "actionable sentence" OR "task extraction") Enron email annotation`
- `"task-focused summarization" email action items`
- `(email OR Enron) ("task intent" OR "task sentence") annotation extraction`
- `("action item extraction" OR "task extraction") email (owner OR assignee OR deadline OR condition OR argument)`

### F2 — DIRECT: request and commitment acts

- `"requests-for-action" email`
- `"commitments-to-act" email`
- `(request OR commitment) "workplace email" annotation speech act`
- `("commitment detection" OR "commitment extraction") email Enron`
- `"email speech acts" (request OR commit OR proposal) corpus`
- `(commissive OR promise OR obligation) email NLP workplace`

### F3 — DIRECT: owner / assignee

- `"addressee tagging" "task intent" email`
- `"people assignment" task email NLP`
- `"Enron People Assignment"`
- `(email OR Enron) task "responsible person" extraction`
- `(email OR "workplace email") (assignee OR responsibility OR responsible) task extraction`
- `(email OR Enron) task assignment (implicit OR context OR addressee OR recipient)`
- `(email OR Enron) task assignment (group OR multiple OR multi-recipient OR "person(s)")`

### F4 — DIRECT: decision / approval / rejection / proposal

- `("decision extraction" OR "decision detection") (email OR "business email" OR "workplace email" OR "enterprise chat") corpus`
- `(approval OR rejection OR acceptance OR proposal) detection (email OR "enterprise chat" OR "workplace communication") NLP`
- `("speech act" OR "dialogue act") (approval OR reject OR rejection OR proposal OR acceptance) email`
- `(decision OR approval OR rejection OR proposal) (Slack OR Teams OR "enterprise messaging" OR "business chat") corpus annotation`
- `("decision extraction" OR "proposal extraction") workplace (actor OR argument OR span OR proposition)`

### F5 — TRANSFER: meeting action/decision discourse

- `"action item detection" meeting annotation assignee`
- `"action item assignment" meeting dialogue annotation`
- `"detecting and summarizing action items" dialogue`
- `"decision detection" "multi-party dialogue"`
- `"decision-related dialogue acts" meeting`
- `(proposal OR commitment OR decision) meeting dialogue act annotation`
- `"action item" meeting (owner OR assignee OR deadline OR argument OR condition)`

### F6 — TRANSFER: argument spans

- `"event argument extraction" span argument roles`
- `"span-based event extraction" arguments`
- `("argument span extraction" OR "trigger argument extraction") event`
- `"semantic role labeling" exact span arguments`
- `(event OR predicate) argument extraction (actor OR agent OR recipient OR time) span`
- `"document-level event argument extraction" implicit arguments`

### F7 — TRANSFER: implicit arguments

- `"implicit argument resolution" NLP discourse`
- `"implicit semantic role labeling" discourse`
- `"implicit argument" semantic role labeling context`
- `"implicit argument recovery" NLP`
- `(implicit OR omitted) argument (agent OR actor OR addressee) resolution`
- `"implicit arguments" discourse context semantic roles`

### F8 — TRANSFER: deadline binding

- `"event-time relation extraction" NLP`
- `"event time relation" temporal information extraction`
- `"temporal anchoring" events TimeBank`
- `"event time extraction" temporal argument`
- `("temporal relation extraction" OR "event-time linking") event time expression`
- `(task OR action) ("event-time relation" OR "temporal anchoring" OR "time argument")`
- `(email OR workplace) task deadline ("temporal relation" OR "event-time" OR "time argument")`

### F9 — TRANSFER: negation / modality scope

- `"negation scope resolution" event`
- `"negated event" "scope resolution" NLP`
- `"speculation scope resolution" NLP`
- `(modality OR modal) scope event extraction NLP`
- `"deontic modality" obligation extraction scope`
- `(obligation OR permission OR prohibition) extraction "deontic modality"`
- `(request OR commitment OR action) (negation OR modality) scope NLP`

### F10 — TRANSFER: condition / exception attachment

- `"conditional relation extraction" NLP event`
- `(condition OR prerequisite OR exception) "relation extraction" action`
- `"condition-action" relation extraction NLP`
- `(conditional OR condition) event argument extraction`
- `(unless OR exception) scope extraction NLP`
- `"conditional obligation" extraction NLP`
- `(request OR commitment OR obligation) condition attachment NLP`

### F11 — DIRECT: exact structured spans

- `(email OR "enterprise chat" OR workplace) "action item" "span annotation"`
- `(email OR "workplace communication") (request OR commitment OR decision) "argument span"`
- `(email OR "enterprise messaging") action (actor OR owner) deadline condition "span" corpus`
- `("action item" OR request OR commitment) "exact span" annotation email`
- `(workplace OR email) "structured extraction" (owner OR assignee) deadline condition evidence`
- `(email OR chat) communicative event "trigger" "argument" annotation`

### F12 — DIRECT: authentic enterprise chat

- `("enterprise messaging" OR "enterprise chat" OR "workplace chat") corpus (request OR commitment OR decision OR action)`
- `(Slack OR "Microsoft Teams" OR Mattermost) corpus (action item OR request OR commitment OR decision) NLP`
- `("organizational communication" OR "workplace communication") corpus task assignment NLP`
- `("business chat" OR "collaboration platform") corpus speech act action item`
- `(Slack OR Teams OR "enterprise messaging") annotation (assignee OR deadline OR decision OR proposal)`

## False friends and downgrade rules

Discovery should not return a paper as gap-closing evidence merely because its title contains the right nouns.

Downgrade or exclude:

- whole-message or whole-sentence actionable classification with no structured arguments;
- action-item detection with no way to separate several actions in one sentence;
- generic chatbot intent classification;
- question detection presented as request detection;
- request-for-information corpora with no request-for-action distinction;
- commitment classification with no action content or actor;
- generic decision summarization with no decision-act annotation;
- agreement/approval/rejection work that conflates act classification with correct antecedent scope;
- event extraction that cannot distinguish mentioned actions from requested, assigned, committed, or decided actions;
- SRL evidence where all arguments are explicit and sentence-local when the claim concerns implicit owners;
- zero-anaphora results treated as direct English-email owner evidence;
- TIMEX recognition or normalization treated as deadline extraction;
- calendar extraction treated as task-deadline binding;
- deadline prediction based only on proximity to a date;
- condition-presence classifiers without condition-to-action attachment;
- negation cue detection without scope or negated-event extraction;
- broad modality tagging that merges capability, possibility, intention, and obligation;
- hedge detection presented as evidence for deontic obligations;
- project-scheduling responsibility assignment rather than language understanding;
- bug/issue/ticket assignee prediction that does not extract responsibility from natural-language task statements;
- synthetic email or generated chat presented as authentic workplace evidence;
- meeting evidence presented as direct written-email/chat validation;
- customer-service, social, or telephone corpora presented as workplace-domain validation;
- generated action-item summaries with no recoverable source evidence;
- systems that force an owner, deadline, or condition when the source leaves it unresolved;
- evaluations reporting only one aggregate score when individual argument errors cannot be measured.

Specific gap-closure admission rules should be strict:

**Gap-1:** Do not close it with sentence-level action detection. The paper needs a structured act/action representation with multiple arguments and sufficiently exact evidence annotations to evaluate argument preservation.

**Gap-2:** Do not close it because a system produces meeting minutes or a “decisions” section. It must empirically distinguish decision-related acts such as decision, proposal, approval/acceptance, or rejection and connect them to their content.

**Gap-3:** Do not close it with explicit same-sentence names only. Evidence must address at least one difficult ownership phenomenon such as implicit addressee, contextual owner, group owner, multiple candidate recipients, or different owners for multiple actions.

**Gap-4:** Do not close it with temporal-expression extraction or normalization. The evaluated object must include an action/event ↔ time relation.

**Gap-5:** Do not close it with cue detection. Conditions, negation, exceptions, or modality must be scoped or attached to the correct action/proposition.

## Date policy

**Earliest publication year discovery must include: 1997.**

Direct computational workplace-email work becomes clearly visible in the early 2000s: both **Learning to Classify Email into “Speech Acts”** and **Task-Focused Summarization of Email** appeared in 2004. citeturn190358search1turn190358search2

However, starting discovery in 2004 would silently omit the empirical dialogue-act annotation vocabulary on which much later request, acceptance, rejection, agreement, and proposal terminology rests. **Coding Dialogs with the DAMSL Annotation Scheme** dates to 1997 and describes a layered communicative-act annotation scheme, including backward functions such as accepting a proposal and answering a question. citeturn654725search0turn654725search24 The subsequent Switchboard-style statistical dialogue-act literature was already well established by 2000. citeturn654725search4

Accordingly:

- **Global discovery floor: 1997.**
- Treat 1997–2003 primarily as foundational/TRANSFER terminology.
- Expect the highest-value DIRECT email evidence to begin around 2004.
- Do not bulk-search back to classical philosophical speech-act work from the 1960s unless a later empirical NLP paper makes that lineage necessary; the objective is computational annotation, benchmark, extraction, and evaluation terminology rather than speech-act philosophy.

The practical round-4 change is therefore not merely to broaden the date window. It is to search using **more precise relational terminology**: `task-person assignment`, `Requests-for-Action`, `Commitments-to-Act`, `event-time relation`, `implicit argument resolution`, `negation scope`, and `conditional relation extraction`. Those terms correspond much more closely to the unresolved capabilities than the earlier surface terms `assignee extraction`, `deadline extraction`, and `condition detection`.
