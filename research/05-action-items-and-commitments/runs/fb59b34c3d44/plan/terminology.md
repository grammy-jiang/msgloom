# empirical workplace email and chat studies on structured action and decision extraction, focusing on owner assignment, deadline-to-action binding, conditional or negated obligations, and evidence-span annotation academic terminology analysis

## Product problem

The target is not generic email intent classification and not generic summarization. The research object is a **structured work-relevant communicative act** whose semantics and arguments remain separately recoverable:

- act type: request, commitment, proposal, decision, approval, rejection, action item, etc.;
- actor / owner / assignee;
- action object or target;
- recipient / beneficiary where relevant;
- modality or status at utterance time;
- deadline wording and normalized time only where justified;
- conditions, prerequisites, exceptions, and negation;
- exact source evidence span or spans;
- unresolved fields rather than invented values.

The most important terminology correction is therefore to distinguish **detection/classification** from **structured extraction and argument binding**. A paper can accurately detect that a sentence contains an action item while still providing no evidence for who owns it, which date is its deadline, whether it is conditional, or which characters in the source support the extracted record.

A second correction is domain-related. Meeting dialogue, generic conversational datasets, event extraction, semantic role labeling, implicit-argument resolution, temporal extraction, and modality/negation research are valuable, but for the outstanding gaps they are generally **TRANSFER** evidence. The high-priority unresolved questions specifically ask for authentic workplace email or enterprise-chat evidence.

The Topic 04 boundary must remain explicit: recognizing `approved`, `agreed`, `rejected`, or a commitment does not prove that the system attached that act to the correct antecedent proposition. Topic 04 owns that scope problem and left direct workplace evidence open.

## Seed keyword audit

| Seed | Academic meaning | Fit | Main risk |
| --- | --- | --- | --- |
| action item extraction | Identification and sometimes structured extraction of follow-up work from communication. | STRONG | Frequently means sentence/utterance detection rather than owner/object/deadline/condition extraction. |
| action item detection | Recognition of utterances or segments containing actionable follow-up work. | STRONG | Usually stops at an action-item label. |
| task extraction | Extraction of tasks or task-like events from language. | MODERATE | Highly polysemous across dialogue, workflow, software engineering, and procedural text. |
| to-do extraction | Extraction or generation of to-do items from messages, notes, meetings, or documents. | MODERATE | Often a productivity/summarization term rather than a standardized argument-level IE task. |
| task-oriented information extraction | Ambiguous term for IE serving a task and easily confused with task-oriented dialogue. | WEAK | Strongly attracts intent/slot-filling literature unrelated to workplace obligations. |
| email speech act classification | Classification of email communicative functions such as request, inform, commit, or propose. | STRONG | Usually provides act labels without structured action arguments. |
| dialogue act classification | Classification of conversational turns by discourse function. | MODERATE | Dominated by general conversational datasets rather than workplace action extraction. |
| request detection | Recognition of direct or indirect requests/directives. | STRONG | Often does not extract addressee, requested action, deadline, condition, or request subtype. |
| request identification | Near-synonym of request detection. | STRONG | Can retrieve pragmatics-only research without computational structured extraction. |
| commissive speech acts | Speech acts committing the speaker to future action. | STRONG | Theoretical speech-act literature can dominate without empirical extraction. |
| commitment extraction | Extraction of commitments and sometimes their participants/action. | STRONG | Also retrieves formal multi-agent social-commitment research. |
| commitment detection | Recognition of commitment-bearing utterances. | STRONG | Commonly a binary/act-label task rather than structured extraction. |
| promise detection | Recognition of promises or promise-like commissives. | MODERATE | Too narrow to cover all workplace commitments and assignments. |
| obligation detection | Identification of text expressing duties or required actions. | STRONG | Dominated by legal, regulatory, policy, and requirements domains. |
| deontic modality | Obligation, permission, prohibition, and related normative modal force. | STRONG | Modal-force detection alone does not identify the responsible actor or action. |
| intention detection | Recognition of expressed intentions/plans. | MODERATE | Intention is not necessarily commitment, and generic intent classification causes heavy noise. |
| intent-to-act | Descriptive phrase for intention to perform an action. | WEAK | Not a stable academic NLP task name. |
| decision extraction | Identification and sometimes structured extraction of decisions. | STRONG | Often decision sentence/segment detection or summarization rather than structured act extraction. |
| decision detection | Recognition of decision-bearing utterances or segments. | STRONG | May collapse proposal, agreement, approval, and finalized decision. |
| meeting decision detection | Decision detection in multiparty meetings. | MODERATE | Valuable transfer evidence but not direct asynchronous workplace email/chat evidence. |
| event extraction | Trigger/type and sometimes argument extraction for events. | MODERATE | Standard events are usually factual events, not communicative obligations. |
| event argument extraction | Extraction of participants and attributes associated with events. | STRONG | Highly useful machinery, but conventional argument schemas do not encode assignment/deontic semantics. |
| semantic role labeling | Predicate-argument labeling such as agent, theme, recipient, and temporal roles. | MODERATE | An event agent is not automatically a task owner; SRL does not encode request/commitment/decision force. |
| implicit argument resolution | Recovery/linking of arguments omitted locally but recoverable from discourse. | STRONG | Existing benchmarks mostly do not concern implicit workplace owners. |
| zero anaphora | Resolution of omitted pronouns/arguments, especially in pro-drop languages. | WEAK | Search results are dominated by non-English zero-pronoun resolution. |
| omitted argument recovery | Recovery of missing predicate arguments. | MODERATE | Less standardized terminology; retrieves ellipsis and MT work. |
| conditionality detection | Detection of conditional constructions or condition-dependent propositions. | STRONG | Sentence-level conditional flags are insufficient without condition-to-action binding. |
| hedge detection | Detection of qualification or reduced certainty. | WEAK | Hedges are not equivalent to conditions, prerequisites, exceptions, or obligations. |
| speculation detection | Recognition of hypothetical or uncertain propositions. | WEAK | Mainly epistemic/factuality research rather than deontic action semantics. |
| modality detection | Detection/classification of modal meanings. | MODERATE | Mixes ability, possibility, intention, obligation, permission, and epistemic uncertainty. |
| temporal expression extraction | Identification of dates, times, durations, and relative times. | MODERATE | Finding a date does not prove that it is an action deadline. |
| temporal expression normalization | Mapping time expressions to normalized values. | MODERATE | Correct normalization does not solve action-to-time attachment. |
| deadline extraction | Identification of due dates or temporal constraints. | STRONG | Often implemented as date detection without a task-to-deadline relation. |
| responsibility assignment | Identification/inference of the responsible person or unit. | MODERATE | Dominated by bug triage, RACI, organizational accountability, or workload allocation. |
| owner assignment | Informal term for assigning responsibility for a task. | WEAK | Mostly retrieves project-management/process-ownership material. |
| assignee extraction | Extraction of the entity assigned to a task. | MODERATE | Often retrieves assignee recommendation/prediction in issue trackers. |
| email action-item corpora | Corpus-discovery phrase for email datasets annotated with actionable content. | STRONG | Relevant corpora may use different terminology, so exact-phrase recall is poor. |
| request-response corpora | Corpora containing request/response pairs. | WEAK | Dominated by response generation, QA, response selection, and Topic-04-style alignment. |

### Terms to promote

The raw seeds should be expanded with combinations that force **arguments and relations**, not just detection:

- structured action-item extraction;
- action-item argument extraction;
- speech-act argument extraction;
- request extraction;
- commitment extraction;
- commissive speech act recognition;
- decision act extraction;
- approval detection;
- rejection detection;
- proposal detection;
- assignee extraction;
- responsible-person extraction;
- implicit owner / implicit assignee;
- deadline binding;
- due-date relation extraction;
- action-time relation extraction;
- conditional obligation;
- conditional commitment;
- negated obligation / negated request;
- deontic modality;
- modality scope / negation scope;
- implicit argument resolution;
- event argument extraction;
- argument span annotation;
- evidence span annotation.

### Terms to demote

Use these only as secondary expansion terms, not as primary discovery families:

- task-oriented information extraction;
- intent-to-act;
- zero anaphora;
- hedge detection;
- speculation detection;
- owner assignment;
- request-response corpora;
- generic intent classification;
- generic event extraction;
- generic dialogue act classification.

## Academic task families

### F1 — Workplace email/chat speech-act and action-item recognition — DIRECT

Studies classification or extraction of requests, commitments, directives, proposals, approvals, decisions, and action items in authentic workplace communication.

Known foundational email examples include:

- Cohen, Carvalho, and Mitchell (2004), *Learning to Classify Email into 'Speech Acts'*.
- Carvalho and Cohen (2005), *On the Collective Classification of Email 'Speech Acts'*.

These are important terminology anchors, but speech-act classification alone does not establish structured owner/deadline/condition extraction.

### F2 — Structured action-item argument extraction — DIRECT

The closest formulation to msgloom's target representation: extract an action plus owner/actor, object, recipient, temporal constraint, conditions, and evidence.

This family is the critical search family for gap-1. A paper performing only binary action-item detection is partial evidence, not a solution to this family.

### F3 — Request, commitment, promise, and obligation extraction — DIRECT

Covers directives and commissives and the distinction between someone asking another participant to act and someone committing themselves to act.

This family is central to avoiding:

- request → false commitment;
- capability → false commitment;
- intention → false decision;
- mentioned action → false assignment.

### F4 — Decision, approval, rejection, agreement, and proposal extraction — DIRECT

Targets gap-2. Search should explicitly combine decision terminology with approval, rejection, agreement, and proposal terminology because literature often uses different labels.

A decision detector that merges proposal and finalized decision is insufficient for this project.

Topic 04's open scope problem remains in force: recognizing `approved` does not demonstrate correct identification of what was approved.

### F5 — Owner, assignee, and responsibility extraction — DIRECT

Targets gap-3.

The desired evidence distinguishes at least:

- explicit owner;
- implicit owner inferred from discourse;
- group owner;
- missing/unresolved owner;
- multiple actions assigned to different owners.

Generic people NER or `sender = owner` heuristics do not qualify.

### F6 — Deadline and temporal-argument binding — DIRECT

Targets gap-4.

The academic object should be a relation such as:

`ACTION --has_deadline--> TIMEX`

rather than merely a TIMEX detector.

The key adversarial distinction is:

- action deadline;
- meeting date;
- date of an earlier event;
- shared date covering several actions;
- conditional future date;
- merely mentioned date.

### F7 — Conditional, negated, modal, and exception-bearing obligations — DIRECT

Targets gap-5.

The required unit is not simply a sentence-level flag. A condition, exception, prohibition, or negation must be connected to the action it modifies.

Examples of different semantics that must remain distinct include:

- `send it Friday`;
- `send it Friday if Finance approves`;
- `do not send it`;
- `no action needed unless Finance rejects it`;
- `I can send it`;
- `I will send it`.

### F8 — Dialogue-act modeling — TRANSFER

General dialogue-act modeling supplies mature act taxonomies and context-aware classification methods.

Relevant foundations include:

- Core and Allen (1997), *Coding Dialogs with the DAMSL Annotation Scheme*.
- Stolcke et al. (2000), *Dialogue Act Modeling for Automatic Tagging and Recognition of Conversational Speech*.

This family should not be allowed to dominate discovery because standard dialogue-act benchmarks usually lack structured work arguments.

### F9 — Event extraction and event argument extraction — TRANSFER

Provides a mature trigger-plus-argument representation and argument-level evaluation.

A key foundational anchor is:

- Doddington et al. (2004), *The Automatic Content Extraction (ACE) Program - Tasks, Data, and Evaluation*.

The representation is relevant, but news-style `Agent`, `Victim`, `Place`, and `Time` roles cannot simply be relabeled as workplace owner/deadline semantics.

### F10 — Semantic role labeling and frame-semantic argument extraction — TRANSFER

Relevant foundation:

- Gildea and Jurafsky (2002), *Automatic Labeling of Semantic Roles*.

SRL is useful for separating several predicates and recovering agents, themes, recipients, and temporal modifiers. It does not determine whether the predicate expresses a request, commitment, proposal, or assignment.

### F11 — Implicit argument and omitted participant resolution — TRANSFER

This is the strongest transfer family for gap-3's implicit-owner cases.

Known example:

- Gerber and Chai (2010), *Beyond NomBank: A Study of Implicit Arguments for Nominal Predicates*.

The transfer hypothesis is that discourse-level missing-argument methods may help recover implicit workplace owners. Such evidence does not establish email accuracy until evaluated in the target domain.

### F12 — Temporal expression extraction, normalization, and event-time relations — TRANSFER

Relevant foundations include:

- Pustejovsky et al. (2003), *TimeML: Robust Specification of Event and Temporal Expressions in Text*.
- Verhagen et al. (2007), *SemEval-2007 Task 15: TempEval Temporal Relation Identification*.

The useful transfer is the separation of:

1. finding the temporal expression;
2. normalizing it;
3. linking it to an event.

Msgloom needs a further semantic distinction: whether that event-time relation is specifically a **deadline**.

### F13 — Modality, negation, hedge, speculation, and factuality scope — TRANSFER

Useful examples include:

- Baker et al. (2010), *The Annotation and Detection of Modality in English Text*.
- Farkas et al. (2010), *The CoNLL-2010 Shared Task: Learning to Detect Hedges and Their Scope in Natural Language Text*.

The important transferable idea is **scope**. A negation or modal cue must be linked to the proposition/action it governs.

However, epistemic uncertainty must not be treated as deontic obligation, and hedge detection alone does not solve conditional commitments.

### F14 — Span-based structured information extraction — TRANSFER

This family supplies annotation and evaluation mechanisms for exact source grounding.

The relevant capability is not model-generated explanation. It is gold annotation linking:

- act;
- action trigger/object;
- owner;
- deadline;
- condition;
- exception;

to explicit source spans where such evidence exists.

It is especially important for gap-1 and for msgloom's traceability requirement.

### F15 — Meeting action and decision extraction — TRANSFER

Meeting studies are likely to contain richer action-item and decision annotations than many email datasets and therefore deserve a dedicated transfer search.

They must remain labeled TRANSFER for the specific outstanding gaps requiring authentic workplace email or chat.

## Query families

### F1 — DIRECT: workplace email/chat speech acts

- `"email speech act" request commitment action workplace corpus`
- `"speech act classification" email request commitment decision`
- `"speech act" enterprise chat request commitment action`
- `"workplace email" request commitment action item corpus`
- `"business email" speech act request commitment`

### F2 — DIRECT: structured action-item arguments

- `"action item extraction" email owner deadline`
- `"action item extraction" workplace communication assignee due date`
- `"action item" email corpus owner assignee deadline annotation`
- `"action item" structured extraction email argument span`
- `"task extraction" business email assignee deadline`
- `"action item extraction" chat owner action deadline condition`
- `"action item" owner object deadline condition corpus`

This is the primary family for gap-1.

### F3 — DIRECT: requests, commitments, obligations

- `"commitment extraction" email action owner`
- `"commitment detection" workplace email`
- `"commitment detection" chat action`
- `"commissive" email NLP commitment`
- `"request detection" email action`
- `"request identification" workplace email NLP`
- `"obligation extraction" email workplace`
- `"deontic" email obligation request commitment`

### F4 — DIRECT: decisions, approvals, rejections, proposals

- `"decision extraction" workplace email approval rejection proposal`
- `"decision detection" email approval agreement rejection`
- `"approval detection" email NLP`
- `"agreement detection" workplace email decision`
- `"proposal detection" email dialogue act`
- `"rejection detection" email dialogue act`
- `"decision extraction" enterprise chat`
- `"decision" "business email" corpus annotation`

This is the primary family for gap-2.

### F5 — DIRECT: owner and assignee extraction

- `"assignee extraction" email action item`
- `"owner extraction" email action item NLP`
- `"responsibility extraction" email task NLP`
- `"action item" assignee extraction workplace`
- `"action item" responsible person email`
- `"implicit owner" action item email`
- `"implicit assignee" email task`
- `"group ownership" action item extraction`
- `"multiple action items" different assignees email`

This is the primary family for gap-3.

### F6 — DIRECT: deadline binding

- `"deadline extraction" email action item`
- `"due date extraction" email task`
- `"deadline" "action item" corpus annotation`
- `"deadline extraction" workplace communication`
- `"action item" temporal argument email`
- `"action deadline" relation extraction email`
- `"due date" relation extraction task action`
- `"temporal relation" action item deadline workplace`

This family deliberately adds **relation**, **action**, and **argument** terminology so discovery does not return only TIMEX detection.

### F7 — DIRECT: condition, negation, exception, modality

- `"conditional commitment" email`
- `"conditional commitment" dialogue NLP`
- `"conditional obligation" email NLP`
- `"deontic modality" workplace communication`
- `"negated obligation" NLP email`
- `"negated request" email NLP`
- `"condition" "action item" extraction`
- `"exception" obligation extraction email`
- `"no action" unless email NLP`
- `"modality" request commitment email`

This is the primary family for gap-5.

### F8 — TRANSFER: dialogue acts

- `"dialogue act classification" request commitment directive`
- `"dialogue act" request commissive commitment corpus`
- `"dialogue act" context request decision agreement`

### F9 — TRANSFER: event arguments

- `"event argument extraction" implicit argument temporal argument`
- `"event argument extraction" agent time condition`
- `"event extraction" argument span annotation`
- `"event argument" relation extraction multiple events sentence`

### F10 — TRANSFER: semantic roles

- `"semantic role labeling" agent recipient temporal argument`
- `"semantic role labeling" multiple predicates sentence`
- `"frame semantic parsing" agent action recipient time`

### F11 — TRANSFER: implicit arguments

- `"implicit argument resolution" discourse agent`
- `"implicit argument" predicate argument extraction discourse`
- `"omitted argument" recovery NLP discourse`
- `"implicit participant" event extraction discourse`
- `"implicit agent" semantic role labeling`

### F12 — TRANSFER: temporal relations

- `"temporal expression normalization" event relation`
- `"temporal relation extraction" event time`
- `"event-time relation" extraction temporal`
- `"temporal argument extraction" event time span`

### F13 — TRANSFER: modality and scope

- `"deontic modality" annotation NLP obligation permission`
- `"modality scope" NLP negation`
- `"negation scope" action event extraction`
- `"conditionality" scope NLP`
- `"hedge scope" NLP corpus`
- `"modality annotation" obligation permission intention ability`

### F14 — TRANSFER: span-grounded extraction

- `"span-based information extraction" argument extraction`
- `"evidence span" information extraction relation argument`
- `"argument span" event extraction annotation`
- `"exact span" event argument extraction`
- `"span-level" structured information extraction`

### F15 — TRANSFER: meeting actions and decisions

- `"action item detection" meeting`
- `"action item extraction" meeting dialogue`
- `"decision detection" meeting dialogue`
- `"decision extraction" meeting action item`
- `"meeting" action item assignee deadline`
- `"meeting" decision proposal agreement extraction`

## False friends and downgrade rules

Discovery should downgrade or reject the following even when keywords match:

1. **Actionability without arguments.** A sentence/message/turn action-item classifier does not establish owner, object, deadline, condition, or evidence extraction.

2. **Generic task-oriented dialogue.** Intent detection, slot filling, dialogue-state tracking, and virtual-assistant task completion are not the target simply because they contain `task`.

3. **Generic dialogue acts.** Switchboard-style act classification is TRANSFER unless authentic workplace communication and relevant work acts are annotated.

4. **Meeting-only evidence.** Action and decision extraction from meetings is useful TRANSFER evidence but does not by itself close gaps requiring email or enterprise chat.

5. **TIMEX =/= deadline.** Finding or normalizing `Friday` is insufficient. There must be evidence that the system attaches the time to the relevant action and identifies deadline semantics.

6. **Calendar extraction =/= deadline extraction.** Appointments, event dates, travel dates, and schedule entries should not be admitted as deadline evidence without task-to-time binding.

7. **Person NER =/= owner extraction.** Recognizing `John` does not establish that John owns an action.

8. **Sender =/= owner.** A sender/author heuristic is not owner extraction and cannot establish implicit ownership.

9. **Bug assignment =/= linguistic assignee extraction.** Developer recommendation, ticket routing, issue assignment, and workload allocation are different tasks.

10. **Organizational responsibility =/= conversational responsibility.** RACI matrices, accountability frameworks, and business-process ownership are false friends.

11. **Agent =/= assignee.** An SRL or event-extraction agent role cannot automatically be interpreted as responsibility for future work.

12. **Generic event extraction is TRANSFER.** News, biomedical, social-media, and KB event extraction can supply methods and representations, not direct workplace accuracy evidence.

13. **Capability =/= commitment.** `Can do X` must not be treated as equivalent to `will do X`.

14. **Intention =/= decision.** A plan or intention cannot be counted as a finalized decision without explicit evidence.

15. **Proposal =/= decision.** Proposal/recommendation classifiers should be kept distinct from decision/approval classes.

16. **Generic modality =/= obligation.** Epistemic possibility, ability, desire, intention, permission, necessity, and obligation must not be collapsed.

17. **Hedge/speculation =/= condition.** Epistemic uncertainty work is not direct evidence for prerequisites, exceptions, or conditional obligations.

18. **Sentence-level conditionality is insufficient.** Gap-5 requires the condition, negation, or exception to be attached to the correct action when several propositions occur together.

19. **Legal obligation extraction is TRANSFER.** Legal, regulatory, requirements, and policy corpora may provide deontic representations but are not direct workplace-email/chat evidence.

20. **Decision summarization =/= decision extraction.** A meeting summary stating a decision is not equivalent to extracting an approval/rejection/proposal/decision act and its arguments from source dialogue.

21. **Workflow approval =/= conversational approval.** Pull-request status, document workflow approval, authorization databases, and business-process approval metadata are false friends.

22. **Act label =/= correct antecedent scope.** Topic 04 left exact proposition-level workplace agreement/approval/rejection scope unresolved. Topic 05 must not infer scope correctness from act-classification performance.

23. **Request-response alignment belongs to Topic 04 when it only identifies what the reply addresses.** It becomes Topic 05 evidence only when the communicative act itself is classified or extracted.

24. **Commitment state tracking belongs to Topic 06.** Revoked, fulfilled, completed, contradicted, or overdue states do not replace evaluation of initial commitment extraction.

25. **Separate capabilities do not create a joint benchmark.** Gap-1 remains open if one corpus annotates speech acts, another owners, and another temporal expressions. The gap asks whether a single modern workplace email/chat benchmark jointly represents the required structure.

26. **Generated normalized records =/= evidence spans.** A model producing `owner=John` without gold source grounding does not satisfy exact evidence-span annotation.

27. **Post-hoc explanations =/= gold evidence.** Model rationales or retrieved snippets should not be counted as annotated source evidence unless the benchmark explicitly defines and evaluates supporting spans.

28. **Synthetic communication is not authentic workplace evidence.** Synthetic/adversarial examples are valuable for gap-6 engineering work, but they cannot establish production-domain empirical accuracy.

29. **Consumer/social dialogue is TRANSFER.** Customer service, social media, forums, telephone calls, and open-domain chat should not be labeled DIRECT merely because requests or commitments occur.

30. **`Business`, `enterprise`, and `task` are not sufficient domain indicators.** Admission requires inspection of the communication source and annotation task.

31. **Sentiment/priority/urgency are not action semantics.** Such papers should be excluded unless the required act or arguments are independently annotated.

32. **Generation/execution is out of scope.** Action recommendation, to-do generation without source extraction, draft generation, planning, or tool execution does not answer Topic 05.

33. **Aggregate accuracy can hide argument failure.** When owner/deadline/condition annotations exist, evaluation that only reports an overall act score should be treated as partial evidence unless argument-level results can be recovered.

34. **One message-level argument cannot establish multi-action binding.** A paper assigning one owner or deadline to a message containing several actions does not demonstrate the capability required by gaps 3–5.

## Date policy

**Earliest publication year to include: 1997.**

The search must not use a modern recency cutoff such as 2015 or 2020.

The target-domain email speech-act literature is already visible in the early 2000s, while computational dialogue-act annotation and representation underlying modern request/commitment classification dates to the late 1990s. Core and Allen's DAMSL work provides a 1997 anchor; Stolcke et al.'s influential dialogue-act modeling follows in 2000.

Several other transfer families foundational to the structured representation also emerge in the early 2000s:

- semantic role labeling: early 2000s;
- TimeML and structured temporal semantics: 2003;
- ACE event/argument extraction: early 2000s;
- computational email speech-act classification: early-to-mid 2000s.

Accordingly, discovery should search **1997 onward** and use backward citation chaining where later papers point to earlier directly relevant empirical work.

Earlier philosophical or linguistic speech-act theory can be consulted for definitions, but bulk computational discovery does not need to start with classical pre-NLP speech-act literature unless a citation trail demonstrates that an older empirical computational predecessor is materially relevant.

The round-2 priority should remain highly targeted: first exhaust F2–F7 DIRECT queries for the five open academic gaps, then use F8–F15 primarily to find representations, annotation schemes, and evaluation methods that can support engineering gaps 6–9 without misrepresenting transfer results as direct workplace evidence.
