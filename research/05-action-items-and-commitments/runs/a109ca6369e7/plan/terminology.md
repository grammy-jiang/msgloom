# action items, requests, commitments, and decisions in workplace email and chat: extracting action, owner, object, deadline, conditions, and speech act with evidence academic terminology analysis

## Product problem

The target is not generic task extraction and not generic intent classification. The target is a **source-grounded semantic representation of work-relevant communicative acts**:

- request / directive;
- commitment / commissive;
- assignment / action item;
- proposal / intention;
- decision;
- approval / rejection / agreement;
- permission / obligation where relevant.

For each act, discovery should favor work that can preserve or help recover:

`actor/owner + action/object + recipient/beneficiary + deadline + conditions/prerequisites/exceptions + modality/status-at-utterance + source evidence`.

The central failure modes are semantic rather than cosmetic: request mistaken for commitment, proposal mistaken for decision, capability mistaken for promise, nearby date mistaken for deadline, contextual actor mistaken for explicitly assigned owner, and conditional or negated action reported as unconditional work.

This means the literature search needs two layers. The **DIRECT** layer looks for empirical work that actually detects these communicative phenomena in email, written workplace communication, or closely matching action-item data. The **TRANSFER** layer looks for specific mechanisms—meeting action-item structure, dialogue acts, implicit argument recovery, deontic modality, modal/negation scope, and temporal normalization—that could fill argument-level gaps but cannot establish production-email accuracy by themselves.

The closest direct historical line is real rather than hypothetical: email speech-act classification appears in Cohen, Carvalho, and Mitchell (2004), email action-item detection in Bennett and Carbonell (2005), collective email-act classification in Carvalho and Cohen (2005), and semantic-email action-item classification in Scerri et al. (2010). citeturn623287search0turn623287search3turn623287search4turn623287search2

## Seed keyword audit

| Seed | Academic meaning | Fit | Main risk |
| --- | --- | --- | --- |
| action item extraction | Extraction of follow-up work/actions from communication | STRONG | Often means binary/span detection rather than owner/object/deadline/condition extraction |
| action item detection | Classification/localization of action-item-bearing text | STRONG | Detection label alone is insufficient for structured action semantics |
| task extraction | Extraction of tasks or procedural steps from text | MODERATE | Large procedural/workflow literature where tasks are already explicit |
| to-do extraction | Informal extraction of text convertible to to-do items | WEAK | Product/prompt terminology rather than stable academic task |
| task-oriented information extraction | IE tailored to a downstream task | WEAK | Too broad; also collides with task-oriented dialogue |
| email speech act classification | Classification of email by request, commitment and related communicative acts | STRONG | Frequently whole-message classification without proposition scope or arguments |
| dialogue act classification | Classification of conversation segments by discourse function | MODERATE | Typical tagsets are broader/coarser than msgloom's work-action distinctions |
| request detection | Detection of directive/request acts | STRONG | May combine requests for information and requests for action |
| request identification | Recognition of request/directive utterances | STRONG | Indirect requests and action-vs-question distinctions may be lost |
| commissive speech acts | Acts committing the speaker to future action | STRONG | Major non-computational pragmatics/philosophy literature |
| commitment extraction | Extraction of future-action undertakings | STRONG | 'Commitment' is highly polysemous outside conversational NLP |
| commitment detection | Detection of commitment-bearing discourse | STRONG | Dedicated empirical NLP literature is smaller than the name suggests |
| promise detection | Detection of promise-like commissive acts | MODERATE | Promise is narrower than workplace commitment and not a dominant NLP benchmark name |
| obligation detection | Detection of duties or required actions | MODERATE | Dominated by legal, regulatory, contract and requirements domains |
| deontic modality | Obligation, permission, prohibition, entitlement and related normative force | MODERATE | Deontic obligation is not equivalent to conversational commitment |
| intention detection | Detection of expressed future intention/plan | MODERATE | Generic user intent and behavioral-intention literature dominates searches |
| intent-to-act | Loosely denotes prospective behavioral action | REJECT | No stable NLP task meaning; very high semantic drift |
| decision extraction | Extraction of decisions reached or recorded in discourse | STRONG | Decision-related text may only contain deliberation or alternatives |
| decision detection | Localization/classification of decision discourse | STRONG | Must distinguish a final decision from proposal/discussion |
| meeting decision detection | Detection of decision-related meeting dialogue | STRONG | Excellent semantic transfer but spoken meetings are not email/chat |
| event extraction | Extraction of event mentions and types | WEAK | News/biomedical events normally do not encode communicatively created obligations |
| event argument extraction | Extraction of actors and other event arguments | MODERATE | Useful machinery but ordinary schemas omit speech-act force |
| semantic role labeling | Predicate-centered semantic argument labeling | MODERATE | Agent/theme roles do not establish request, assignment or commitment |
| implicit argument resolution | Recovery of non-local/unexpressed predicate participants | MODERATE | Mostly studied outside workplace action semantics |
| zero anaphora | Recovery of syntactically omitted arguments, especially in pro-drop languages | WEAK | Language-specific phenomenon only partly overlaps English omitted ownership |
| omitted argument recovery | Broad recovery of unexpressed semantic arguments | MODERATE | Less standardized terminology; attracts ellipsis work |
| conditionality detection | Detection of conditional propositions/relations | MODERATE | Finding an if-clause is not enough; its scope must attach to the action |
| hedge detection | Detection of uncertainty/qualification cues and sometimes scope | MODERATE | Usually epistemic uncertainty rather than action commitment strength |
| speculation detection | Detection of possible/hypothetical propositions | WEAK | Primarily factuality/epistemic research |
| modality detection | Classification of possibility, obligation, ability, volition, etc. | MODERATE | Unqualified search mixes several incompatible notions of modality |
| temporal expression extraction | Recognition of dates, times, durations and relative time | MODERATE | A recognized date is not necessarily a deadline |
| temporal expression normalization | Conversion of temporal expressions to normalized values | MODERATE | Can introduce false precision and does not establish action association |
| deadline extraction | Extraction of due times/time limits for actions | STRONG | Sparse dedicated literature; nearest-date heuristics are dangerous |
| responsibility assignment | Identification/allocation of responsible actor | WEAK | Dominated by governance, accountability, blame and optimization |
| owner assignment | Identification/allocation of task owner | WEAK | Usually project management, bug triage or recommendation rather than text extraction |
| assignee extraction | Extraction of task assignee from text | MODERATE | Search dominated by assignee prediction in software-ticket systems |
| email action-item corpora | Annotated email resources containing action/request/commitment labels | STRONG | Corpora are scarce and may only have message-level labels |
| request-response corpora | Corpora with request/response or adjacency-pair structure | WEAK | Usually QA, customer-service or response-generation rather than work-action extraction |

Several seeds therefore need qualification before bulk search. In particular, **email speech acts**, **action-item detection/extraction**, **request detection**, **commitment/commissive language**, **decision detection**, and **deadline extraction** should be promoted. Generic **event extraction**, **task extraction**, **modality**, and **SRL** should only run as explicit transfer searches. `intent-to-act` should not be used as a primary discovery term.

## Academic task families

### D01 — Workplace email action-item detection and extraction — DIRECT

This is the closest task family to the product requirement. Bennett and Carbonell explicitly framed email action-item detection as detecting messages requiring action or response and locating the specific text indicating the request. Scerri et al. later treated task assignment and meeting proposal as semantic-email action items. citeturn623287search3turn623287search2

Discovery should distinguish:

1. message-level actionability;
2. sentence/segment-level action-item localization;
3. structured action extraction.

Only the third fully approaches the msgloom record contract, but the first two are still useful components.

### D02 — Email speech-act classification for requests and commitments — DIRECT

Cohen, Carvalho, and Mitchell's 2004 work and Carvalho and Cohen's 2005 follow-up explicitly model email acts including requests and commitments. This terminology is considerably better than generic `intent classification` for the target. citeturn623287search0turn623287search1

Important search terms are therefore:

- `email acts`;
- `request`;
- `commitment`;
- `directive`;
- `commissive`;
- `illocutionary act`;
- indirect request.

A positive speech-act label must not be interpreted as proof that Topic 04 antecedent scope is correct.

### D03 — Structured request and commitment argument extraction — DIRECT

This is the most important capability gap between the classic email-act literature and the product representation.

Discovery should look specifically for methods that recover combinations of:

- requester / committer;
- assignee / owner;
- action predicate;
- object, deliverable or target;
- recipient / beneficiary;
- deadline;
- prerequisite or trigger;
- condition or exception;
- source span.

Searches should explicitly include `argument`, `slot`, `owner`, `assignee`, and `deadline`; otherwise retrieval will overproduce message-level classifiers.

### D04 — Decision, approval, rejection, agreement, and proposal acts — DIRECT

The target distinction is:

`proposal/intention ≠ accepted decision ≠ approval ≠ acknowledgment`.

Direct email/chat evidence should receive highest priority. If little exists, discovery should record that as an academic gap rather than silently substituting meeting accuracy.

`approval`, `rejection`, `acceptance`, `agreement`, `proposal`, and `decision` should therefore be promoted even though several were not present in the raw seed list.

### D05 — Deadline extraction and action-time attachment — DIRECT

The real problem is not TIMEX recognition. It is a semantic relation:

`deadline_of(temporal_expression, action)`.

For example, a message containing three actions and two dates requires determining which date, if any, constrains which action. Searches using only `temporal expression extraction` will not establish this capability.

### D06 — Workplace action/request corpora and annotation schemas — DIRECT

Discovery should actively search for:

- email-act corpora;
- action-item annotations;
- request/commitment annotations;
- action spans;
- annotation guidelines;
- argument/slot annotations.

Corpus papers should be checked for unit of annotation. A message-level request label is materially weaker than proposition/span-level action evidence.

### T01 — Meeting action-item detection and argument annotation — TRANSFER

This is the strongest neighboring literature.

Purver, Ehlen, and Niekrasz developed hierarchical annotation around the action-item assignment process rather than treating action items as a flat class. Later work includes audio-meeting action detection, Murray and Renals' meeting action-item classifier, AIMU's actionable-item annotations with associated arguments, and recent meeting action-item detection. citeturn623287search12turn623287search13turn623287search10turn623287search6turn623287academia43

This family is especially valuable for:

- actions emerging over several turns;
- speaker/owner relationships;
- assignments versus volunteered commitments;
- contextual action-item detection;
- argument annotation.

It remains **TRANSFER**, because meeting speech cannot establish performance on asynchronous email or Teams text.

### T02 — Meeting decision detection — TRANSFER

Hsueh and Moore explicitly studied automatic decision detection in meeting conversations, and the CALO Meeting Assistant later integrated decision extraction with action-item recognition and dialogue analysis. citeturn615156search1turn615156search4

This family should be searched for:

- final decision versus deliberation;
- decision-related dialogue acts;
- decision segments;
- agreement and convergence cues.

Any discovered method must still be validated against written workplace communication.

### T03 — Dialogue-act and illocutionary-force classification — TRANSFER

The Switchboard SWBD-DAMSL work from 1997 and Stolcke et al. 2000 are foundational computational references for contextual dialogue-act labeling. citeturn404185search10turn177966search0

This literature is relevant mainly for:

- communicative-function taxonomies;
- sequential context;
- agreement/disagreement;
- questions and directives;
- act classification methodology.

Do not adopt a generic dialogue-act tagset as the Topic 05 ontology without testing whether it preserves request/commitment/decision distinctions.

### T04 — Event and semantic-role argument extraction — TRANSFER

Event extraction and SRL can supply mechanisms for:

`actor → predicate/action → object/theme → recipient`.

They do **not** supply the illocutionary force.

Therefore:

> `John will send the report`

and

> `John might send the report`

may have almost identical semantic roles while carrying materially different commitment status.

Searches should combine event arguments with modality, negation, or implicit arguments rather than admitting generic event-extraction papers purely because they extract actors.

### T05 — Implicit argument identification and omitted participant recovery — TRANSFER

Ruppenhofer et al.'s SemEval formulation explicitly addresses linking events to participants in discourse; Gerber and Chai's work studies implicit arguments beyond local SRL. citeturn177966search5turn352067search1turn615156search0

This is relevant to cases such as:

- speaker implicitly owns an action;
- owner appeared in a preceding sentence/turn;
- action object is omitted;
- a shorthand commitment depends on prior context.

The critical product rule remains: **resolved from context is not the same evidential status as explicitly stated**.

### T06 — Deontic modality and obligation extraction — TRANSFER

Legal NLP has explicit taxonomies for obligation, permission, prohibition and entitlement. Sancheti et al.'s LEXDEMOD work is particularly relevant because it associates deontic modality with an agent and modal triggers. citeturn352067search0

This is useful for schema and mechanism transfer, but:

- external obligation is not voluntary speaker commitment;
- permission is not commitment;
- prohibition is not a task assignment;
- `can` may express ability rather than permission;
- `should` can range from suggestion to norm.

Direct workplace validation is mandatory before treating legal deontic models as operational action detectors.

### T07 — Conditionality, negation, exception, hedge, and modality scope — TRANSFER

This family prevents semantic polarity errors.

Required cases include:

- `I'll send it if Finance approves`;
- `No action needed unless Legal objects`;
- `We may need to revise it`;
- `You don't need to reply`;
- `Only after the migration completes`;
- `I should be able to send it Friday`.

The CoNLL-2010 hedge task demonstrates the established cue-plus-scope formulation for uncertainty, while later event-based modality work explicitly connects modal meaning to the modified event. citeturn352067search2turn404185search6

The transferable lesson is more important than the biomedical domain: **operator scope must be represented, not merely cue presence**.

### T08 — Temporal expression recognition, normalization, and event-time linking — TRANSFER

TimeML established a representation linking events and temporal expressions, and TempEval later benchmarked temporal extraction and normalization. citeturn177966search9turn404185search9

Use this literature after the system knows that a time expression constrains an action.

Preserve both:

- original wording: `by next Friday`;
- normalized value: only if contextual anchoring justifies one.

A normalization component must be allowed to return unresolved/underspecified rather than manufacturing calendar precision.

## Query families

### D01 — DIRECT: workplace email action items

- `"action item extraction" email NLP`
- `"action item detection" email`
- `"action-item detection" email request`
- `"action item" email classification request response`
- `"action item recognition" email`
- `"actionable" email request commitment extraction`
- `"task extraction" business email request commitment`
- `"follow-up action" email extraction NLP`

### D02 — DIRECT: email speech acts

- `email "speech act classification" request commitment`
- `email "speech acts" request commitment propose`
- `"email acts" request commitment classification`
- `"email act" request commitment NLP`
- `workplace email directive commissive classification`
- `business email request commitment speech act`
- `email illocutionary act request promise commitment`
- `email indirect request detection NLP`

### D03 — DIRECT: structured action arguments

- `"action item extraction" owner deadline email`
- `"action item" assignee deadline object extraction email`
- `"request extraction" requester addressee action email`
- `"commitment extraction" actor action deadline dialogue`
- `email request argument extraction actor action recipient`
- `email commitment argument extraction speaker action`
- `"implicit owner" action item email`
- `"assignee extraction" email task`
- `"task owner" extraction email NLP`
- `workplace message action owner due date extraction`

### D04 — DIRECT: decisions and approvals

- `"decision extraction" email NLP`
- `"decision detection" email workplace`
- `"approval" speech act email NLP`
- `"approval detection" email NLP`
- `"agreement" "email acts" classification`
- `"acceptance" "rejection" speech act email`
- `"proposal" "decision" email classification NLP`
- `workplace chat decision approval extraction`
- `business communication decision proposal approval NLP`

### D05 — DIRECT: deadlines

- `"deadline extraction" email NLP`
- `"due date extraction" email NLP`
- `"deadline" "action item" extraction email`
- `"due date" "action item" NLP`
- `email task deadline extraction temporal`
- `email request deadline identification`
- `commitment deadline extraction dialogue`
- `"action-time" relation extraction task deadline`

### D06 — DIRECT: datasets and annotation

- `"email action item" corpus`
- `"email action-item" corpus`
- `"email speech act" corpus request commitment`
- `"email acts" corpus request commitment`
- `annotated email requests commitments dataset`
- `workplace email action item annotation`
- `business email speech act dataset`
- `email request commitment annotation guidelines`

### T01 — TRANSFER: meeting action items

- `"action item detection" meeting`
- `"action item extraction" meeting transcript`
- `"action item" meeting annotation owner`
- `"action item" meeting arguments extraction`
- `"actionable items" meeting understanding`
- `"action item assignment" meeting dialogue`
- `"meeting action item" corpus annotation`
- `"meeting action item detection" context`

### T02 — TRANSFER: meeting decisions

- `"meeting decision detection"`
- `"decision detection" meeting conversations`
- `"decision extraction" meeting transcript`
- `"decision-related dialogue acts" meeting`
- `meeting decision proposal agreement detection NLP`
- `"decision point" meeting dialogue NLP`
- `"decision element extraction" meeting transcript`

### T03 — TRANSFER: dialogue and speech acts

- `"dialogue act classification" directive commissive`
- `"dialog act" request commitment agreement`
- `"dialogue act" request promise commitment`
- `"directive" "commissive" dialogue act classification`
- `"illocutionary force" classification NLP dialogue`
- `"speech act recognition" request promise NLP`
- `"indirect request" dialogue act detection`

### T04 — TRANSFER: event/SRL argument machinery

- `"event argument extraction" agent patient recipient`
- `"event argument extraction" implicit argument`
- `"semantic role labeling" agent recipient event extraction`
- `"frame semantic parsing" agent recipient action`
- `"argument extraction" event actor object NLP`
- `"event extraction" modality negation arguments`
- `"event argument extraction" evidence span`

### T05 — TRANSFER: implicit arguments

- `"implicit argument identification" discourse`
- `"implicit argument resolution" semantic role labeling`
- `"implicit argument" agent recovery NLP`
- `"omitted argument" recovery NLP discourse`
- `"null instantiation" FrameNet implicit arguments`
- `"zero anaphora" semantic role labeling discourse`
- `"implicit semantic role labeling"`
- `"linking events and their participants in discourse"`

### T06 — TRANSFER: deontic modality

- `"deontic modality" NLP obligation permission`
- `"deontic modality classification" agent`
- `"agent-specific deontic modality"`
- `"obligation detection" NLP agent action`
- `"obligation extraction" responsible party condition`
- `contract obligation extraction actor action condition deadline`
- `"norm extraction" obligation permission prohibition NLP`

### T07 — TRANSFER: conditions, negation and modal scope

- `"conditional commitment" NLP dialogue`
- `"conditional request" speech act NLP`
- `"condition extraction" obligation NLP`
- `"exception extraction" obligation NLP`
- `"negation scope" event extraction NLP`
- `"hedge detection" scope NLP`
- `"speculation detection" scope NLP`
- `"modality detection" event-based NLP`
- `"modal scope" event extraction`
- `"no action needed" NLP classification`

### T08 — TRANSFER: temporal semantics

- `"temporal expression extraction" normalization NLP`
- `"temporal expression normalization" relative dates`
- `"temporal relation extraction" event time`
- `"event-time linking" NLP`
- `TimeML event temporal expression relation`
- `TempEval temporal expression normalization`
- `"relative date normalization" document time NLP`
- `"temporal anchoring" events NLP`

## False friends and downgrade rules

Discovery should downgrade or reject the following even when lexical matching is strong:

1. **Whole-message actionability only.** Keep as act-detection evidence, but it does not demonstrate owner/object/deadline/condition extraction.
2. **Generic intent classification.** A chatbot's `book_flight` or `cancel_order` label is not evidence for request-versus-commitment semantics.
3. **Procedural task extraction.** Extracting steps from instructions, recipes, manuals, SOPs, job descriptions, or project plans is a different problem.
4. **Generated action items.** Summarization or LLM task generation without source-grounded gold does not establish extraction capability.
5. **Generic event extraction.** Detecting that an action/event is mentioned does not establish that anybody requested, assigned, promised, approved, or decided it.
6. **SRL used as responsibility.** An `ARG0` or semantic agent is not automatically the accountable owner.
7. **Calendar extraction.** Detecting `Friday` or a meeting date is not deadline extraction.
8. **Nearest-date assignment.** A date must be semantically attached to the action, not assigned because it is close in the sentence.
9. **Assignee recommendation.** Bug triage, ticket routing, workload balancing, code ownership and likely-assignee prediction are not grounded owner extraction.
10. **Legal-domain accuracy presented as workplace accuracy.** Legal deontic work is TRANSFER unless independently evaluated on workplace communication.
11. **Collapsed modality.** Obligation, permission, prohibition, ability, intention, probability and willingness must not become one generic modal flag.
12. **Epistemic uncertainty only.** Hedge/speculation detection is useful only where cue/scope mechanisms help preserve action status.
13. **Conditional cue only.** Detecting `if` is insufficient without identifying what action the condition governs.
14. **Request-for-information only.** Query detection does not establish action-request detection.
15. **Employee/organizational commitment.** Psychological organizational commitment is unrelated.
16. **Git/source-control commitment.** `commit`, `committer`, and `commitment` in software repositories are false friends.
17. **Programming Promise objects.** JavaScript/concurrency `Promise` literature is irrelevant.
18. **HTTP request detection.** Network/API request-response literature is irrelevant.
19. **Decision trees/control decisions.** `Decision detection` must refer to communicative decisions.
20. **Generic request-response datasets.** QA, customer support, response generation and protocol traces need explicit action semantics to qualify.
21. **Synthetic-only evidence.** Synthetic data may support engineering tests but cannot establish authentic workplace prevalence or accuracy.
22. **Filled-in missing fields.** A method that guesses an owner/date because an output schema requires one conflicts with the project contract.
23. **Proposal/action collapse.** `We should`, `we could`, `I intend`, `I can`, `please`, `I will`, and `approved` must not be treated as equivalent actionability cues.
24. **Topic 06 state tracking.** Fulfilled, cancelled, revoked, contradicted and completed commitments belong downstream once Topic 05 has extracted the act.
25. **Topic 04 scope resolution.** Determining what `approved`, `yes`, or `do that` refers to is not Topic 05's primary act-classification task.
26. **Action recommendation or execution.** Drafting, autonomous task creation, tool invocation and execution are outside the topic.

The most important admission test is therefore:

> Does the paper contribute evidence or a transferable mechanism for deciding **what communicative act occurred, who is responsible for what, under what timing/conditions, and where that interpretation is supported in the source**?

If not, matching words such as `task`, `intent`, `action`, `decision`, `commitment`, or `deadline` are insufficient.

## Date policy

**Earliest discovery year: 1962.**

The wide floor is deliberate. The vocabulary around requests, promises and commitments descends from speech-act theory, and a narrow modern recency filter would silently lose that conceptual foundation. Austin's *How to Do Things with Words* appeared in 1962; Searle's subsequent work established the promise/illocutionary framework from which directive and commissive distinctions developed.

The computational lineage is much newer:

- **1997:** SWBD-DAMSL provides an influential empirical dialogue-act annotation framework. citeturn404185search10
- **2000:** Stolcke et al. provide a major statistical dialogue-act modeling reference. citeturn177966search0
- **2003:** TimeML supplies an influential event/time representation. citeturn177966search9
- **2004:** Cohen, Carvalho and Mitchell directly classify email speech acts. citeturn623287search0
- **2005:** Bennett and Carbonell study email action-item detection; Carvalho and Cohen study collective email-act classification. citeturn623287search3turn623287search4
- **2006 onward:** explicit meeting action-item annotation/detection appears, followed by meeting decision detection in 2007. citeturn623287search12turn615156search1
- **2009–2012:** implicit-event-participant and implicit-argument work provides transferable methods for omitted actors/objects. citeturn177966search5turn352067search1turn615156search0
- **2010 onward:** hedge/scope evaluation supplies transferable operator-scope methodology. citeturn352067search2
- **2022:** agent-specific deontic modality work provides a particularly relevant transfer representation for agent plus normative force. citeturn352067search0

The 1962 floor does **not** mean the pipeline should fill the corpus with philosophical speech-act papers. Pre-computational work should normally be retained as terminology/taxonomy background. Empirical admission should prioritize computational papers, authentic annotated data, and direct workplace evidence. The date floor exists so foundational terminology is deliberately assessed rather than accidentally removed by a recency filter.
