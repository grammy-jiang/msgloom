# authentic workplace email and enterprise-chat extraction of structured action and decision arguments, with emphasis on implicit or group assignees, deadline-to-action relations, condition/negation/modality attachment, and exact evidence-span annotation academic terminology analysis

## Product problem

The product problem is more specific than ordinary action-item detection, intent classification, or date extraction.

The target object is a structured representation of a work-relevant communicative act or event from authentic workplace email or enterprise chat:

- act type: request, commitment, decision, approval, proposal, action item, or related subtype;
- actor or owner;
- action object or target;
- recipient or beneficiary where relevant;
- modality/status at utterance time;
- original deadline wording and a normalized time only when justified;
- conditions, prerequisites, exceptions, and negation;
- exact supporting source span or spans;
- uncertainty and explicitly unresolved fields.

The most important terminology correction is therefore to distinguish **detection** from **structured extraction**. A large academic literature detects that an utterance is a request, decision, commitment, or action item. That literature is relevant, but it does not establish that owner, object, deadline, condition, and evidence can be extracted correctly.

A second correction is to distinguish **time extraction** from **deadline binding**. Detecting and normalizing “Friday” is not sufficient. The required problem is determining which action, if any, Friday constrains.

A third is to distinguish **implicit assignee recovery** from ordinary person-name extraction. “Can you send this?”, “Finance to confirm”, “Someone from Legal should review”, and a request addressed implicitly to a participant require pragmatic or discourse reasoning, not just named-entity recognition.

A fourth is to distinguish **condition or modality detection** from **scope attachment**. Recognizing an if-clause, a negator, “should”, or “might” is insufficient when several actions occur in the same sentence or message. The system must identify which action is conditioned, negated, tentative, obligatory, or excepted.

Finally, the project's use of **argument** means a semantic argument or structured slot such as actor, object, recipient, time, or condition. It should not be confused with rhetorical argument mining of claims and premises.

For the five still-open academic gaps, direct evidence means authentic workplace email or enterprise chat. Meeting research is highly valuable but remains transfer evidence.

## Seed keyword audit

| Seed | Academic meaning | Fit | Main risk |
| --- | --- | --- | --- |
| action item extraction | Extraction of follow-up tasks or assignments from discourse, sometimes including task, responsible party, or timeframe. Established especially in meeting research. | STRONG | Many papers actually perform only utterance detection and do not extract the complete argument structure. |
| action item detection | Classification or segmentation of discourse regions associated with action items. | STRONG | Detection normally stops at a binary label or discourse region. |
| task extraction | Broad extraction of tasks, procedures, work steps, or instructions. | MODERATE | “Task” is overloaded and attracts process mining, instructional text, job-task analysis, and ML-task literature. |
| to-do extraction | Informal identification of text suitable for a to-do list. | WEAK | Weak academic standardization; strongly attracts productivity products and demonstrations. |
| task-oriented information extraction | Usually confused with task-oriented dialogue and slot filling. | REJECT | Does not reliably mean extraction of workplace tasks. |
| email speech act classification | Classification of email communicative functions such as request, commitment, proposal, or information delivery. | STRONG | Usually message-level or segment-level labels, with little structured argument extraction. |
| dialogue act classification | Classification of utterances as question, answer, request, statement, agreement, backchannel, etc. | MODERATE | Very broad and usually label-only rather than argument extraction. |
| request detection | Identification of direct or indirect directive/request acts. | STRONG | Request presence does not identify the responsible performer, exact action, deadline relation, or conditions. |
| request identification | Near-synonym of request detection. | STRONG | Can drift toward information-request or customer-intent classification. |
| commissive speech acts | Acts that commit the speaker to future action, including promises and offers. | STRONG | Much literature is theoretical; an offer is not automatically an accepted obligation. |
| commitment extraction | Extraction of linguistic future-action commitments and sometimes their content or participants. | STRONG | “Commitment” may refer to abstract social/dialogue commitments rather than executable workplace action. |
| commitment detection | Classification of text as containing a commitment. | STRONG | Often label-only and may collapse conditional, tentative, and unconditional commitments. |
| promise detection | Identification of promissory commissives. | MODERATE | Narrower than routine workplace commitments and can attract political-promise research. |
| obligation detection | Identification of duties, requirements, or prohibitions. | MODERATE | Dominated by legal, regulatory, requirements, and policy text. |
| deontic modality | Linguistic obligation, permission, prohibition, or normative force. | MODERATE | Captures semantic force, not necessarily a concrete assigned workplace action. |
| intention detection | Detection of speaker/user intention. | WEAK | In NLP this overwhelmingly means generic intent classification. |
| intent-to-act | Unstable term for behavioral or legal intention to perform an action. | REJECT | Attracts marketing, psychology, law, and security rather than workplace extraction. |
| decision extraction | Extraction of decisions or decision records from discourse or documents. | STRONG | Definitions vary from structured records to decision-related summaries. |
| decision detection | Identification of decision-related utterances or segments. | MODERATE | A decision-related region does not identify proposal versus approval/rejection or the acted-on proposition. |
| meeting decision detection | Detection of decision-related dialogue acts or segments in meetings. | STRONG | Strong adjacent evidence but not direct email/chat evidence and often lacks structured arguments. |
| event extraction | Extraction of event mentions and possibly participants/attributes. | MODERATE | Dominated by news, biomedical, crisis, and factual-event domains without speech-act semantics. |
| event argument extraction | Extraction of typed participants and attributes associated with an event. | STRONG | Useful transfer mechanism, but standard roles omit pragmatic assignee and act-force distinctions. |
| semantic role labeling | Predicate-argument labeling such as agent-like and patient-like roles. | MODERATE | Does not determine pragmatic ownership, request addressee, modality, or deadline relation. |
| implicit argument resolution | Recovery of unexpressed semantic arguments from discourse context. | STRONG | Existing datasets often concern nominal predicates rather than pragmatic task owners. |
| zero anaphora | Resolution of omitted pronominal arguments, especially in pro-drop languages. | WEAK | English implicit assignees are usually not canonical zero-pronoun cases. |
| omitted argument recovery | Broad recovery of unexpressed predicate arguments. | MODERATE | Less standardized and attracts ellipsis/parsing literature unrelated to workplace responsibility. |
| conditionality detection | Identification of conditional constructions or conditioned propositions. | MODERATE | Detection alone does not attach the condition to the correct action. |
| hedge detection | Detection of uncertainty/qualification cues. | WEAK | Hedges are only one form of uncertainty and do not establish action structure. |
| speculation detection | Identification of speculative propositions and sometimes their scope. | WEAK | Dominated by biomedical/scientific factuality rather than workplace commitments. |
| modality detection | Classification of possibility, necessity, obligation, permission, intention, etc. | WEAK | Ambiguous term and often lacks scope; unqualified search also attracts multimodal ML. |
| temporal expression extraction | Identification of dates, times, durations, and relative times. | MODERATE | A time mention is not necessarily a deadline. |
| temporal expression normalization | Mapping temporal phrases to normalized values. | MODERATE | Says what time is denoted, not which action that time modifies. |
| deadline extraction | Extraction of due dates or deadline expressions. | STRONG | Many approaches equate proximity to a future date with deadline binding. |
| responsibility assignment | Identification or assignment of responsibility for an activity. | MODERATE | Heavily overloaded with management, RACI, blame, workflow allocation, and legal literature. |
| owner assignment | Informal assignment of ownership for an issue, task, component, or resource. | WEAK | Not a stable NLP term and strongly attracts code/data/process ownership. |
| assignee extraction | Extraction of the person or group assigned to a task. | MODERATE | Search results often concern bug-triage assignee recommendation from metadata, not text extraction. |
| email action-item corpora | Discovery phrase for email corpora annotated with actions/tasks. | STRONG | Not a standardized task term; some corpora may label only message-level actionability. |
| request-response corpora | Corpora linking requests/questions to responses. | MODERATE | Often means response generation, retrieval, QA, or next-response prediction. |

### Important seed replacements

Several seeds should not be deleted, but they should no longer drive discovery alone.

Promote the following more precise terms:

- **email act classification**
- **workplace speech-act classification**
- **structured action-item extraction**
- **action-item argument extraction**
- **action-item assignment**
- **task-assignment extraction**
- **request extraction**
- **commitment extraction**
- **commissive act detection**
- **decision-related dialogue act**
- **approval detection**
- **rejection detection**
- **proposal detection**
- **assignee identification**
- **responsible-party extraction**
- **addressee identification / addressee recognition**
- **implicit argument resolution**
- **implicit semantic role labeling**
- **cross-sentence argument extraction**
- **document-level event argument extraction**
- **event-time relation extraction**
- **temporal relation extraction**
- **deadline binding / deadline-to-action relation**
- **negation scope resolution**
- **modality scope**
- **deontic modality annotation**
- **conditional clause scope**
- **condition-to-event attachment**
- **span-based event extraction**
- **argument span extraction**
- **trigger and argument span annotation**
- **thread-context classification**
- **collective classification of email acts**
- **quoted-text identification in email**
- **workplace messaging corpus**
- **enterprise instant messaging corpus**

Demote as standalone discovery terms:

- task-oriented information extraction;
- intent-to-act;
- to-do extraction;
- task extraction;
- intention detection;
- dialogue act classification;
- event extraction;
- semantic role labeling;
- zero anaphora for English owner recovery;
- hedge detection;
- speculation detection;
- modality detection;
- temporal expression extraction without a relation term;
- temporal expression normalization without a relation term;
- owner assignment;
- responsibility assignment;
- request-response corpora;
- unqualified “argument extraction”.

## Academic task families

### F1 — Structured action-item and task-assignment extraction from workplace email or enterprise chat — DIRECT

This is the closest academic formulation of the product problem.

The desired literature explicitly works on authentic workplace email, enterprise messaging, workplace instant messaging, Slack-like communication, or Microsoft Teams-like communication and extracts more than an actionable/non-actionable label.

The ideal annotation contains:

- action or act type;
- assignee/owner;
- action object;
- deadline;
- conditions/exceptions;
- exact supporting text.

This family is the main route for closing gap-1.

No confidently established seed paper is listed here because the absence of a direct modern benchmark with the complete required structure is precisely the open gap.

### F2 — Email acts and workplace speech-act classification — DIRECT

This family covers computational classification of requests, commitments, proposals, and other communicative functions in email.

Known seed:

- Vitor R. Carvalho and William W. Cohen (2005), *On the Collective Classification of Email "Speech Acts"*.

This paper family is particularly relevant because email acts such as request and commitment are direct predecessors of the project's semantic labels, and thread/context modeling is explicitly part of the research tradition.

However, message-level email-act classification must not be mistaken for structured action extraction.

### F3 — Decision, approval, rejection, and proposal extraction from workplace communication — DIRECT

This family directly targets gap-2.

The preferred papers must deal with authentic workplace email or enterprise chat and must distinguish decision-like communicative acts rather than merely detecting vaguely “decision-related” text.

High-value distinctions are:

- proposal versus accepted decision;
- approval versus rejection;
- agreement versus acknowledgement;
- decision versus recommendation;
- the semantic proposition or object affected by the act.

Topic 04's boundary remains in force: Topic 05 may classify the act, but the existence of a correct act label does not prove that the system attached it to the correct antecedent proposition.

### F4 — Meeting action-item detection and assignment modeling — TRANSFER

Meeting research is the closest mature adjacent literature for how people establish tasks in organizational discourse.

Known seeds:

- Matthew Purver, Patrick Ehlen, and John Niekrasz (2006), *Detecting Action Items in Multi-party Meetings: Annotation and Initial Experiments*.
- Matthew Purver, Patrick Ehlen, and John Niekrasz (2006), *Shallow Discourse Structure for Action Item Detection*.
- Yun-Nung Chen, Dilek Hakkani-Tür, and Xiaodong He (2015), *Detecting Actionable Items in Meetings by Convolutional Deep Structured Semantic Models*.
- Jiaqing Liu, Chong Deng, Qinglin Zhang, Qian Chen, and Wen Wang (2023), *Meeting Action Item Detection with Regularized Context Modeling*.

This is important transfer evidence because classic meeting action-item work explicitly treats action items as discourse objects that can include a task, responsible participant, and timeframe.

It still cannot establish target-domain performance on asynchronous email or enterprise chat.

### F5 — Meeting decision and decision-related dialogue-act detection — TRANSFER

Known seeds:

- Pei-Yun Hsueh and Johanna D. Moore (2007), *What Decisions Have You Made?: Automatic Decision Detection in Meeting Conversations*.
- Pei-Yun Hsueh and Johanna D. Moore (2008), *Automatic Decision Detection in Meeting Speech*.

This is useful for identifying how decisions emerge from conversational context and how surrounding dialogue differs from the utterances that carry a decision.

Its main limitation is that meeting “decision detection” often identifies a decision-related dialogue act or region rather than a structured decision with approval/rejection/proposal distinctions and arguments.

### F6 — Assignee, responsible-party, and addressee extraction in workplace communication — DIRECT

This family directly targets gap-3.

It must distinguish at least three cases:

1. explicitly named assignee;
2. implicit assignee recoverable from the conversational situation;
3. unresolved owner that should remain unknown.

Group assignees are important. “Legal should review”, “Can someone from Finance confirm?”, or a request addressed to several people should not be forced into a single named-person slot.

The family should also test messages containing several actions assigned to different people.

### F7 — Addressee recognition and implicit participant resolution — TRANSFER

The project's implicit-owner problem is partly pragmatic.

For:

> Can you send the revised version?

the missing semantic performer may be inferred from the addressee rather than from a locally expressed noun phrase.

Accordingly, discovery should include:

- addressee identification;
- addressee recognition;
- multi-party dialogue addressee detection;
- implicit argument resolution;
- implicit semantic role labeling;
- omitted participant recovery.

These are transfer mechanisms until validated on workplace action extraction.

### F8 — Deadline binding and event-time temporal relation extraction — DIRECT

This is the precise formulation needed for gap-4.

The task is not:

> find “Friday”.

It is:

> determine whether “Friday” is a deadline, and if so, which action it constrains.

The benchmark should distinguish:

- deadline for action A;
- deadline for action B;
- one deadline shared by several actions;
- meeting/scheduling date;
- historical date;
- condition-trigger time;
- expected completion time;
- unrelated date mention.

### F9 — Temporal expression normalization and event-time relation modeling — TRANSFER

This family supplies mature temporal representations.

A foundational seed is:

- James Pustejovsky et al. (2003), *TimeML: Robust Specification of Event and Temporal Expressions in Text*.

Useful terminology includes:

- event-time relation extraction;
- temporal relation extraction;
- TIMEX;
- TIMEX3;
- TLINK;
- temporal expression normalization.

This literature can supply representations and algorithms but cannot prove that an extracted time is a workplace deadline.

### F10 — Condition, exception, negation, and modality scope attachment — TRANSFER

Gap-5 is best understood as a **scope and attachment** problem.

For example:

> I can send the report Friday if Legal signs off, but don't publish the appendix.

The useful representation must determine:

- whether “can” is capability, possibility, or commitment;
- which action “if Legal signs off” conditions;
- which action is negated by “don't”;
- whether Friday belongs to sending or some other action.

The important terminology is therefore not merely conditionality detection or modality detection, but:

- condition-to-event attachment;
- conditional-clause scope;
- negation scope resolution;
- modality scope;
- deontic modality annotation;
- exception extraction.

### F11 — Event and semantic-argument extraction with implicit or cross-sentence arguments — TRANSFER

Generic event extraction is too broad, but its argument machinery is directly useful.

Search should focus on:

- event argument extraction;
- document-level event extraction;
- cross-sentence event argument extraction;
- cross-sentence argument extraction;
- implicit argument resolution;
- implicit semantic role labeling.

This literature supplies techniques for actor, object, recipient, time, and other roles when arguments are separated from the event trigger.

It remains transfer evidence because standard event inventories generally do not encode request, commitment, approval, or proposal semantics.

### F12 — Span-based structured information extraction and evidence annotation — TRANSFER

The product requires exact evidence spans.

Discovery should therefore include work where:

- event triggers are spans;
- arguments are spans;
- source evidence is explicitly annotated;
- document-level structures retain links to source mentions.

Useful terms include:

- span-based event extraction;
- argument span extraction;
- trigger span;
- span-level annotation;
- evidence span;
- source span.

This family is primarily methodological transfer for benchmark construction and traceability.

### F13 — Workplace email and enterprise-chat corpora with act/action annotations — DIRECT

Corpus discovery must not rely only on task names because older datasets may be described by corpus, annotation scheme, or communicative-function terminology.

Search should explicitly include:

- email speech-act corpus;
- email act corpus;
- Enron plus request/commitment/action terms;
- business email corpus;
- workplace email corpus;
- enterprise chat corpus;
- workplace instant-messaging corpus;
- Slack;
- Microsoft Teams where academically available.

A direct corpus can close a gap only for fields it actually annotates.

### F14 — Thread-context and discourse-context modeling for workplace act extraction — DIRECT

This family supports engineering gap-7.

Carvalho and Cohen's email-act work is a known seed because it explicitly exploits dependencies among messages in a thread.

The important empirical question is not merely whether context can be used. Discovery should look for controlled comparison among:

- local utterance/sentence;
- whole message;
- preceding messages;
- thread context;
- participant information;
- global conversation context.

Papers without an ablation cannot establish whether context helps enough to justify the added contamination risk.

### F15 — Email quotation, authorship-zone, and forwarded-content segmentation — DIRECT

This family supports engineering gap-8.

The relevant task is separating:

- newly authored text;
- quoted prior text;
- forwarded content;
- signatures/disclaimers where applicable.

It matters because an old request quoted in a reply must not automatically become a new request from the current author.

Quotation segmentation by itself does not prove improved action extraction; it is a supporting mechanism whose downstream effect must be evaluated separately.

## Query families

### F1 — DIRECT: structured workplace action extraction

Run:

- `"action item extraction" (email OR "business email" OR "workplace email") assignee deadline condition corpus`
- `"action item extraction" ("enterprise chat" OR "workplace chat" OR Slack OR "Microsoft Teams") assignee deadline`
- `"task assignment extraction" email assignee deadline`
- `"task extraction" "business email" request commitment assignee`
- `"action item" email annotation "responsible party" timeframe`
- `"structured action item" workplace communication owner deadline condition`
- `"action item extraction" email "evidence span"`
- `"action item" email corpus owner deadline condition`

### F2 — DIRECT: workplace speech acts

Run:

- `email "speech act classification" request commitment proposal`
- `"email act" classification request commitment corpus`
- `"business email" "speech act" request commitment`
- `"workplace email" request commitment classification`
- `"request detection" email commitment corpus`
- `"commissive" email NLP commitment`
- `"speech act" Slack request commitment workplace`
- `"dialogue act" "enterprise chat" request commitment`

### F3 — DIRECT: decisions, approvals, rejections, proposals

Run:

- `"decision extraction" (email OR "workplace email") approval rejection proposal`
- `"decision detection" ("enterprise chat" OR Slack OR "Microsoft Teams") approval rejection`
- `"approval detection" email NLP decision`
- `"rejection detection" email proposal approval`
- `"proposal detection" email "speech act"`
- `"agreement" rejection approval email "speech act" corpus`
- `"decision" "business email" corpus annotation`
- `"decision extraction" workplace communication argument`

### F4 — TRANSFER: meeting action items

Run:

- `"Detecting Action Items in Multi-party Meetings"`
- `"action item detection" meeting annotation responsible party timeframe`
- `"action item extraction" meeting assignee deadline`
- `"actionable item" meeting task assignee`
- `"action item assignment" meeting discourse`
- `"meeting action item" corpus annotation owner deadline`
- `"action item detection" AMI corpus`
- `"multiple action items" meeting assignee`

### F5 — TRANSFER: meeting decisions

Run:

- `"decision detection" meeting dialogue act`
- `"decision-related dialogue act" meeting`
- `"decision extraction" meeting proposal agreement`
- `"Automatic Decision Detection" meeting speech`
- `"meeting decision" corpus annotation dialogue act`
- `"decision point" meeting dialogue act classification`

### F6 — DIRECT: assignees and responsible parties

Run:

- `"assignee extraction" email NLP`
- `"responsible party" extraction email action`
- `"responsibility extraction" email action item`
- `"task assignment" extraction "workplace communication"`
- `"implicit assignee" action item`
- `"implicit owner" action item email`
- `"group assignee" action item`
- `"group owner" workplace request`
- `"assignee" "enterprise chat" task extraction`
- `"responsible person" email request extraction`

### F7 — TRANSFER: addressees and implicit participants

Run:

- `"addressee identification" multi-party dialogue request`
- `"addressee recognition" multiparty conversation`
- `"addressee detection" group chat request`
- `"implicit argument resolution" agent discourse`
- `"implicit semantic role labeling" discourse argument`
- `"omitted argument" recovery discourse agent`
- `"implicit participant" event extraction discourse`
- `"collective addressee" dialogue`

### F8 — DIRECT: deadline binding

Run:

- `"deadline extraction" email action item`
- `"due date extraction" email task`
- `"deadline" "action item" corpus annotation`
- `"deadline extraction" "workplace communication"`
- `"event-time relation" email task deadline`
- `"temporal relation" email action item deadline`
- `"shared deadline" action item extraction`
- `"deadline binding" action extraction`

### F9 — TRANSFER: temporal relations

Run:

- `"event-time relation extraction" NLP`
- `"temporal relation extraction" event time`
- `TimeML event TIMEX relation extraction`
- `TIMEX3 TLINK event time relation`
- `"temporal expression normalization" event relation`
- `"time expression" event argument extraction`
- `"temporal relation classification" event time`

### F10 — TRANSFER: condition, exception, negation, modality

Run:

- `"conditional commitment" NLP`
- `"conditional request" NLP`
- `"condition extraction" event argument NLP`
- `"conditional clause" scope NLP`
- `"negation scope" request obligation`
- `"negation scope resolution" event extraction`
- `"modality scope" commitment NLP`
- `"deontic modality" obligation NLP annotation`
- `"exception extraction" obligation NLP`
- `"if clause" action commitment NLP`
- `"unless" obligation extraction NLP`
- `condition negation modality "event argument" extraction`

### F11 — TRANSFER: event and implicit argument extraction

Run:

- `"event argument extraction" implicit argument`
- `"cross-sentence event argument extraction"`
- `"document-level event extraction" argument`
- `"implicit argument resolution" event extraction`
- `"semantic role labeling" implicit argument discourse`
- `"cross-sentence argument extraction" NLP`
- `"event argument" temporal condition agent extraction`
- `"document-level event argument extraction"`

### F12 — TRANSFER: exact spans and evidence

Run:

- `"span-based event extraction" trigger argument`
- `"argument span extraction" event NLP`
- `"trigger span" "argument span" event extraction`
- `"span-level annotation" event argument corpus`
- `"evidence span" information extraction event`
- `"source span" information extraction annotation`
- `"exact span" event argument extraction`

### F13 — DIRECT: target-domain corpora

Run:

- `"email speech act" corpus request commitment`
- `"email act" corpus request commitment`
- `Enron email request commitment speech act corpus`
- `Enron "action item" annotation`
- `"business email corpus" request commitment decision`
- `"workplace email corpus" action request commitment`
- `"enterprise chat corpus" request commitment decision`
- `Slack workplace corpus request commitment action`
- `"instant messaging" workplace corpus speech act`
- `"organizational chat" corpus dialogue act`

### F14 — DIRECT: context and thread ablations

Run:

- `email speech act thread context classification`
- `"email act" collective classification thread`
- `"conversation context" email request commitment classification`
- `"thread context" action item extraction email`
- `"context modeling" workplace chat request commitment`
- `"message context" enterprise chat speech act`
- `"conversation history" request detection workplace`

### F15 — DIRECT: quotation and authorship zoning

Run:

- `"quoted text" email segmentation NLP`
- `"email quotation" extraction authorship`
- `"quoted text identification" email thread`
- `"reply text" quotation email segmentation`
- `"forwarded content" email segmentation NLP`
- `"authored text" quoted email classification`
- `"email thread" quotation attribution`
- `"quoted history" email classification speech act`

## False friends and downgrade rules

Discovery should downgrade or reject literature according to the following rules.

1. **Binary actionability is not structured extraction.** A paper that labels a sentence or message as actionable does not establish owner, object, deadline, condition, or evidence extraction.

2. **Gap-1 requires independently evaluable arguments.** An alleged action-item benchmark cannot close the gap unless it supplies independently evaluable labels for the relevant structured fields. A generated summary containing these fields is not equivalent to gold argument annotation.

3. **Message-level speech acts remain useful but partial.** Request/commitment email labels are direct evidence for act classification, not for argument extraction.

4. **Meeting evidence remains TRANSFER.** Authentic organizational meetings are extremely relevant, but they do not establish accuracy on asynchronous email or enterprise chat.

5. **Non-workplace dialogue is not direct evidence.** Customer service, social media, casual dialogue, human-assistant dialogue, and task-oriented dialogue should be marked TRANSFER or excluded depending on capability.

6. **Synthetic workplace data is not authentic workplace evidence.** It can support engineering or adversarial evaluation but cannot close a production-domain academic gap.

7. **Bug-triage assignee prediction is a false friend.** Predicting a developer from repository history, code ownership, or ticket metadata is not linguistic assignee extraction.

8. **Person NER is not ownership extraction.** A person's name appearing near an action does not establish that the person owns the action.

9. **@mentions are not sufficient implicit-owner resolution.** They are useful explicit metadata signals but do not solve indirect or group responsibility.

10. **Addressee and assignee are different roles.** Addressee recognition can transfer to assignee inference, but a request recipient is not automatically the responsible performer.

11. **Zero anaphora should be treated cautiously.** Pro-drop-language recovery is useful transfer evidence but is not the dominant phenomenon behind English workplace implicit ownership.

12. **Dates are not deadlines.** Temporal expression extraction cannot close gap-4.

13. **Normalization is not relation extraction.** Resolving “next Friday” to a calendar date does not identify the event it constrains.

14. **Calendar extraction is a major false friend.** Scheduling and calendar-event extraction should be excluded unless the evaluation distinguishes deadlines from other temporal references.

15. **Cue detection is not scope attachment.** Finding “not”, “if”, “unless”, “may”, “should”, or “must” cannot close gap-5 unless the affected proposition/action is also identified.

16. **Legal deontic extraction is transfer evidence.** Legal obligations may provide strong semantic representations but are not direct conversational workplace evidence.

17. **Generic event extraction is transfer only.** News and biomedical benchmarks can justify mechanisms, not target-domain accuracy.

18. **Semantic arguments are not rhetorical arguments.** Argument-mining papers about claims, premises, persuasion, or debate do not satisfy owner/object/deadline slots unless they explicitly model those semantic roles.

19. **Decision support is not decision extraction.** Predictive analytics, decision trees, optimization, and management decision-support systems should be rejected.

20. **Decision-related text is weaker than structured decision extraction.** A decision segment or “decision point” does not close gap-2 unless the relevant act distinction and decision object are represented.

21. **Generated meeting minutes do not provide evidence spans by default.** Summarization work should be downgraded unless claims can be traced and evaluated against source annotations.

22. **Generic intent classification is not intention-to-act extraction.** Chatbot intent classes such as book-flight or cancel-order are false friends.

23. **Response-selection datasets are not request-response semantic corpora.** Pairing a turn with its next response is insufficient.

24. **Quotation removal is only a supporting mechanism.** Email cleaning/quote stripping is relevant to gap-8, but it does not demonstrate better action extraction without downstream evaluation.

25. **More context is not automatically better.** For gap-7, papers should receive additional evidential weight only when they compare local, message, and wider-context configurations or otherwise isolate contextual effects.

26. **Later action state belongs primarily to Topic 06.** Completion, cancellation, revocation, contradiction, and supersession after an action has been extracted should not silently expand Topic 05.

27. **Execution is outside scope.** Systems that create tasks, send mail, call tools, or execute commands are not semantic-extraction evidence unless extraction is separately evaluated.

28. **Exact domain wording is insufficient.** A paper should not be admitted as direct evidence merely because its abstract says business, work, enterprise, task, owner, or decision. The communication source, annotation target, and evaluation unit must match the claimed capability.

## Date policy

**Earliest publication year discovery must include: 1990.**

The target-domain email-act, meeting-action-item, and meeting-decision literature becomes prominent in the 2000s, but those papers inherit computational concepts from 1990s work on dialogue-act annotation and tagging, communicative-function classification, conversational discourse structure, semantic roles, and contextual modeling.

A transformer-era or even post-2000 search window would therefore risk silently excluding the terminology and annotation conventions that later action-item and email-act work assumes.

The bulk discovery should consequently use **1990 as the earliest year**.

Classical philosophical speech-act foundations are older than 1990. They should not become the default bulk-search target because this review is about computational extraction rather than general philosophy of language. Where admitted computational papers rely on older theoretical sources, those sources can be followed through citation chains.

The practical chronology for discovery is therefore:

- **1990s:** computational dialogue acts, discourse annotation, communicative-function and contextual foundations;
- **2000s:** email acts, meeting action-item annotation, meeting decision detection, TimeML-style temporal representations;
- **2010s:** neural action/event extraction, stronger contextual models, scope and document-level methods;
- **2020s:** transformer/LLM-era action-item detection, span/document-level extraction, and modern workplace-message methods.

This policy prevents recency filtering from erasing foundational task definitions while still allowing admission rules to prioritize modern authentic workplace evidence for the open gaps.
