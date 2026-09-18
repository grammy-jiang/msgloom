# Executive Summary

Across 48 papers, the evidence supports structured treatment of workplace actions beyond message-level intent labels. Authentic email and Slack studies show that requests, commitments, assignments, proposals, and decisions are context-sensitive, often coexist within one message, and can depend on preceding turns, participant roles, or recipient metadata. Owner extraction is particularly difficult because responsibility may be implicit, plural, or absent from listed recipients. Explicit argument spans are feasible for stated arguments, but adjacent-domain event research shows that implicit and scattered arguments cannot always be represented by one contiguous evidence span. Temporal, modality, negation, and conditionality research provides useful transfer evidence for relation and scope modeling, but direct workplace evaluation remains sparse. No paper in the corpus jointly evaluates act type, owner, object, deadline, conditions, and exact provenance in authentic workplace communication.

# Themes

## Context-sensitive extraction in authentic workplace communication

Authentic workplace email and Slack studies show that surrounding message or conversation context can materially improve classification or extraction of actionable intents, event arguments, and dialogue acts compared with isolated-sentence or isolated-message processing. Full-email context improved actionable-intent classification, preceding emails improved MAILEX event and argument extraction, and longer conversational context improved Slack dialogue-act classification. [doi-10-1145-3331184-3331260] [2305.13469] [2312.05471]

The effect is nevertheless task-dependent. Collective thread modeling degraded the Deliver act in one email experiment, different context configurations were optimal on AMC-A and AMI, and erroneous predicted event structure could reduce modality performance. [doi-10-1145-1076034-1076094] [2303.16763] [2106.08037]

## Structured action items as multi-argument and sometimes multi-utterance objects

Meeting action-item research repeatedly decomposes an action item into components such as task description, owner, timeframe, and agreement rather than treating it as only a binary sentence label. The same component can be realized across several utterances, and one utterance can contribute several components. [doi-10-1007-11965152-18] [doi-10-3115-1564535-1564540] [doi-10-18653-v1-2007-sigdial-1-4]

End-to-end argument extraction remains substantially harder than extraction with gold triggers or candidate spans. MAILEX reports low workplace-email argument F1 and strong improvement from gold triggers; RAMS shows a severe drop when candidate argument spans must be discovered rather than supplied. [2305.13469] [1911.03766]

## Implicit, plural, and context-dependent responsibility assignment

Responsibility assignment is empirically difficult. Meeting action-item studies report owner as one of the weakest detected components. [doi-10-1007-11965152-18] [doi-10-3115-1564535-1564540]

The EPA email benchmark directly shows that task responsibility may be implicit, plural, or absent from the candidate recipients and explicitly permits both multiple responsible people and a no-one outcome. Its owner annotations also show substantial disagreement. [doi-10-18653-v1-w18-6104]

In workplace Slack, participant role and project responsibility can affect whether an utterance is interpreted as a request or an assignment, showing that responsibility is not always recoverable from surface wording alone. [2312.05471]

Transfer work on implicit semantic arguments likewise shows that missing fillers can often be linked to discourse antecedents, but some are non-resolvable and candidate-generation limitations remain important. [doi-10-1162-coli-a-00110] [doi-10-18653-v1-n18-1076] [manual-69bc2555ab]

## Multiple acts and multiple actions within one message or sentence

Enterprise email frequently contains more than one actionable intent: one study reports substantial proportions of messages with two or more annotated intents. [doi-10-1145-3331184-3331260]

The Lin task extractor explicitly handles coordination so that several task verbs may be extracted from one sentence, while the Slack taxonomy permits multiple acts at clause or fragment granularity. [doi-10-18653-v1-2020-coling-main-164] [2312.05471]

These findings demonstrate the presence of multi-act and multi-action communication; they do not by themselves validate any particular combined representation for those cases.

## Action-to-time relations rather than date detection alone

Meeting action-item work annotates timeframe as an action-item component and reports that semantic and temporal features improve timeframe summarization beyond TIMEX-only extraction. [doi-10-18653-v1-2007-sigdial-1-4]

General event-time research finds that substantial temporal evidence can occur outside the local sentence and that removing the linguistic material connecting an event to its temporal expression substantially reduces strict anchoring accuracy. [doi-10-1162-tacl-a-00006]

TimeML likewise separates temporal expressions from explicit links between events and times, providing a representation for event-time relations rather than treating each date as an event attribute by default. [manual-1e8332286e]

These results concern timeframe and temporal-relation extraction; they do not establish reliable deadline-to-action binding in authentic workplace email or chat.

## Condition, negation, and modality scope

Modality research explicitly distinguishes a modality trigger from the event or proposition it modifies, and MoNTEE uses syntactic paths to approximate the scope of modality, negation, conditionality, counterfactuality, and related operators. [1410.4868] [2109.09393]

BioScope and the *SEM negation shared task provide span-level evidence that identifying a negation cue is materially easier than correctly recovering its complete linguistic scope. [doi-10-1186-1471-2105-9-s11-s9] [manual-ee40d588e3]

Workplace-email annotation studies independently show that conditional commitments and offers create major ambiguity: conditional offers produced a large share of commitment disagreements, and later annotation guidance explicitly represented optional conditions and improved agreement. [manual-0839b98ee7] [manual-d19b0f6f1e] [manual-20b8cd2fdd]

The strongest scope-resolution experiments, however, are largely outside workplace email or chat, so they constitute transfer evidence rather than direct production-domain validation.

## Exact evidence spans versus implicit and scattered arguments

Span-based event extraction provides established mechanisms for explicit argument provenance. Unified span models, PAIE, and RAMS-style evaluation associate event roles with concrete offsets or spans. [1909.03546] [2202.12109] [1911.03766]

Complex-argument research demonstrates a different class of cases: implicit arguments have no directly stated source span, while scattered arguments may be distributed across several parts of a document. [2410.03594]

The evidence therefore supports exact-span evaluation for explicitly realized arguments while also showing that a single contiguous span cannot represent every semantically recoverable argument. The papers do not jointly validate one combined explicit-plus-implicit provenance scheme.

## Proposal, decision, commitment, and request distinctions

LEDA directly distinguishes ProposeAction from StateDecision in organizational email and reports far more proposals than explicit decision statements. [doi-10-18653-v1-2023-findings-acl-378]

Meeting research represents decisions as multi-utterance processes that may contain issues, resolution proposals, resolution restatements, and agreement. [manual-90280d2776] [doi-10-3115-1708376-1708410] [1606.07965]

Email speech-act work also distinguishes directives, information requests, and commitments at the taxonomy level, although some experimental setups merge categories for classification. [doi-10-1109-hicss-2006-528]

These studies establish distinctions among act types but do not provide direct workplace-email/chat evidence for extracting complete structured decision, approval, rejection, or proposal arguments.

## Domain variation and transfer

Commitment detection is measurably corpus-dependent. Within-corpus Avocado and Enron results exceed unadapted cross-corpus transfer, and a classifier can distinguish the two corpora with high accuracy, indicating substantial lexical domain structure. [doi-10-1145-3289600-3290984]

Domain adaptation improves transfer in that study, while weak-supervision work also reports useful Avocado-to-Enron transfer for email intents. [doi-10-1145-3289600-3290984] [2005.13084]

These are direct email transfer results, but they do not establish equivalent performance for enterprise chat or for the full structured argument problem.

# Contradictions

### 1. Whether more conversational context consistently improves extraction

Several papers report gains from fuller message or conversation context: actionable-intent classification improves with full-email context, MAILEX benefits from preceding messages, and Slack dialogue-act classification improves with longer context. [doi-10-1145-3331184-3331260] [2305.13469] [2312.05471]

In contrast, collective email context degraded the Deliver class, different context configurations were optimal on AMC-A and AMI, and noisy predicted contextual structure could reduce downstream modality performance. [doi-10-1145-1076034-1076094] [2303.16763] [2106.08037]

This is a task- and corpus-dependent tension rather than evidence that context is universally helpful or harmful.

### 2. Sentence-level versus message-level annotation granularity

Sentence-level action-item annotation produced better downstream email-level detection than direct whole-email training in one action-item study. [doi-10-1145-1076034-1076140]

By contrast, request/commitment annotation studies obtained higher human agreement at message level and attributed part of the gain to avoiding ambiguity about which individual sentence realizes an obligation. [manual-20b8cd2fdd] [manual-d19b0f6f1e]

The studies optimize different outcomes—automatic detection versus annotation reliability—so their results should not be silently averaged into one preferred granularity.

### 3. Exact argument spans versus semantically recoverable implicit arguments

Span-based event-extraction work evaluates explicit event arguments through concrete span offsets. [1909.03546] [2202.12109] [doi-10-18653-v1-2020-acl-main-667]

Complex-argument research instead demonstrates implicit arguments with no explicit span and scattered arguments whose evidence is distributed across discourse. [2410.03594]

The apparent conflict reflects different argument-realization regimes rather than an error in either result.

### 4. Surface or recipient-based owner inference versus contextual ownership

Some email-task systems use grammatical person, dependency structure, or email-recipient identity as responsibility cues. [doi-10-18653-v1-2020-coling-main-164] [manual-e6bb5aee88]

EPA and workplace Slack evidence show responsibility that is implicit, plural, outside candidate recipients, or dependent on participant role and project responsibility. [doi-10-18653-v1-w18-6104] [2312.05471]

The former methods demonstrate useful cues; the latter evidence shows those cues do not cover every observed ownership case.

### 5. Operational simplicity of commitments versus observed conditional ambiguity

The people-driven service commitment model formally includes conditional antecedents but operationally treats most examined email/chat interactions as unconditional. [doi-10-1109-scc-2013-62]

Workplace-email annotation studies instead identify conditional offers and commitments as major sources of disagreement and explicitly include optional conditions in the final representation. [manual-0839b98ee7] [manual-d19b0f6f1e] [manual-20b8cd2fdd]

The corpus therefore contains differing empirical emphasis on conditionality rather than a settled workplace result.

# Open Gaps

## gap-1 — ACADEMIC — HIGH

There is no direct modern workplace email/chat benchmark in this corpus that jointly annotates speech-act type, owner/assignee, action object, deadline, conditions/exceptions, and exact evidence spans.

MAILEX covers authentic email events and arguments, EPA covers assignees, and several email datasets cover speech acts, but none closes the joint benchmark question. [2305.13469] [doi-10-18653-v1-w18-6104] [manual-d19b0f6f1e] [doi-10-1145-3331184-3331260]

Suggested query: `"action item extraction" (email OR Slack OR "workplace chat" OR "enterprise chat") assignee deadline condition "evidence span" corpus`

**Status: open.**

## gap-2 — ACADEMIC — HIGH

Direct empirical evidence for extracting decisions, approvals, rejections, and proposals with structured arguments from authentic workplace email or chat is still missing.

LEDA directly labels proposals and decisions in organizational email, and meeting studies model decision formation, but none supplies the requested workplace structured-argument benchmark. [doi-10-18653-v1-2023-findings-acl-378] [manual-90280d2776] [doi-10-3115-1708376-1708410] [1606.07965]

Suggested query: `("decision extraction" OR "decision detection" OR "proposal extraction") ("workplace email" OR "enterprise chat" OR Slack) approval rejection proposal "argument extraction"`

**Status: open.**

## gap-3 — ACADEMIC — HIGH

Owner/assignee extraction remains weakly evidenced, especially for implicit owners, group ownership, multiple actions with different owners, and owners recoverable only from organizational or conversation context.

EPA directly establishes implicit, plural, and no-one ownership cases, and meeting and Slack work document owner difficulty and contextual responsibility, but robust extraction across the full set of cases is not established. [doi-10-18653-v1-w18-6104] [2312.05471] [doi-10-1007-11965152-18] [doi-10-3115-1564535-1564540]

Suggested query: `("assignee prediction" OR "assignee extraction" OR "responsibility extraction" OR "action owner") (email OR Slack OR "workplace chat") implicit owner group owner context`

**Status: open.**

## gap-4 — ACADEMIC — HIGH

The corpus does not establish reliable deadline binding in workplace communication: distinguishing a deadline for a particular action from a merely mentioned date, shared date, scheduling expression, or conditional future time remains open.

Meeting action-item and temporal-relation studies support timeframe and event-time linking, but no admitted workplace email/chat benchmark directly evaluates the target distinction. [doi-10-18653-v1-2007-sigdial-1-4] [doi-10-1162-tacl-a-00006] [doi-10-1109-scc-2013-62] [manual-1e8332286e]

Suggested query: `("deadline extraction" OR "due date extraction" OR "deadline detection") (email OR "workplace communication" OR Slack) "action item" temporal relation event argument`

**Status: open.**

## gap-5 — ACADEMIC — HIGH

Direct workplace evidence is insufficient for attaching conditions, exceptions, negation, and modality to the correct action when several actions or clauses occur together.

Workplace-email studies establish conditional ambiguity, while modality and negation papers provide strong transfer evidence for scope resolution, but the combined workplace attachment problem is not directly validated. [manual-0839b98ee7] [manual-d19b0f6f1e] [1410.4868] [2109.09393] [doi-10-18653-v1-d16-1078]

Suggested query: `("conditional commitment" OR "deontic modality" OR "negation scope" OR "condition extraction") (email OR "workplace communication" OR Slack) action attachment obligation`

**Status: open.**

## gap-6 — ENGINEERING — HIGH

Build an independent argument-level benchmark and adversarial fixture suite covering implicit owners, multiple actions in one sentence, shared deadlines, conditional and negated actions, overlapping request/commitment labels, quoted-history contamination, and attachment references; score false positives, false negatives, and each argument separately.

The literature identifies these component phenomena but does not perform this project-specific evaluation. [doi-10-18653-v1-w18-6104] [doi-10-18653-v1-2020-coling-main-164] [manual-0839b98ee7] [manual-cd3fa58e4c] [2410.03594]

**Status: open.**

## gap-7 — ENGINEERING — HIGH

Compare sentence-local, message-level, and selectively expanded thread-context extraction with controlled ablations.

The literature establishes both context gains and context-induced degradation, but the project-specific comparison remains unperformed. [doi-10-1145-3331184-3331260] [doi-10-1145-1076034-1076094] [2303.16763] [2305.13469]

**Status: open.**

## gap-8 — ENGINEERING — HIGH

Test author/quoted/forwarded content zoning while preserving provenance, and measure whether zoning improves act and argument extraction without losing obligations whose interpretation depends on prior-message context.

Zoning improves email request detection, whereas conversational history can be necessary for event interpretation; the interaction between those effects remains unevaluated here. [manual-cd3fa58e4c] [2305.13469] [manual-20b8cd2fdd]

**Status: open.**

## gap-9 — ENGINEERING — HIGH

Evaluate an uncertainty-preserving structured output in which owner, deadline, condition, or act subtype can remain unresolved, and measure whether this reduces false obligations and wrong argument assignments without unacceptable recall loss.

The corpus documents unresolved ownership, implicit arguments, annotation ambiguity, and systems not reliable enough for unattended annotation, but it does not evaluate this project-specific uncertainty representation. [doi-10-18653-v1-w18-6104] [manual-fde6beef40] [2410.03594] [manual-0839b98ee7]

**Status: open.**

## boundary-1 — OUT_OF_SCOPE — HIGH

Exact proposition-level scope for approvals, rejections, agreements, answers, and commitments remains an inherited Topic 04 problem. This synthesis does not establish that a Topic 05 act label has the correct antecedent scope.

# Actionable Insights

- **Synthesis-derived recommendation:** represent each extracted work-relevant act with separately nullable fields for act type, actor or owner, object, recipient or beneficiary, deadline wording and normalized time, conditions or exceptions, source evidence, and uncertainty rather than forcing every field to be populated.
- **Synthesis-derived recommendation:** distinguish explicitly stated owners from contextually inferred owners, support multiple or group assignees, and permit a no-owner or unresolved-owner outcome.
- **Synthesis-derived recommendation:** model deadlines and conditions as relations attached to particular actions rather than as message-level attributes; a shared expression may link to several actions, while proximity alone should not establish that relation.
- **Synthesis-derived recommendation:** preserve exact source spans for explicit arguments, but represent implicit arguments as inferred values with separate supporting-context provenance instead of fabricating a nonexistent exact span.
- **Synthesis-derived recommendation:** evaluate speech-act classification and every structured argument independently, including false-positive and false-negative counts for owner, object, deadline, condition, and evidence support.
- **Synthesis-derived recommendation:** compare sentence-local, full-message, and selectively expanded thread context under controlled ablations rather than assuming that more context always improves extraction.
- **Synthesis-derived recommendation:** evaluate quoted-message and forwarded-content zoning separately from contextual expansion so that contamination reduction and loss of necessary historical evidence are measured independently.
- **Synthesis-derived recommendation:** keep proposal, intention, request, commitment, decision, approval, and rejection distinctions explicit instead of treating all actionable language as a single action-item class.
- **Synthesis-derived recommendation:** keep Topic 04 antecedent-scope resolution separate from Topic 05 act classification, and keep later commitment or decision state changes separate for Topic 06.

# Confidence Summary

The corpus provides **well-supported design principles** around context sensitivity, multi-intent communication, structured argument representations, owner ambiguity, end-to-end error propagation, and the distinction between explicit-span extraction and implicit argument recovery. Confidence is highest where authentic Enron, Avocado, organizational email, or Slack data directly support the claim. [2305.13469] [doi-10-18653-v1-w18-6104] [doi-10-1145-3331184-3331260] [doi-10-18653-v1-2023-findings-acl-378] [2312.05471]

Evidence for deadline binding and condition/negation/modality attachment is weaker for the target domain because much of the strongest empirical work comes from meetings, news, biomedical text, contracts, or general event extraction. [doi-10-18653-v1-2007-sigdial-1-4] [doi-10-1162-tacl-a-00006] [1410.4868] [2109.09393] [doi-10-1186-1471-2105-9-s11-s9]

The individual components have substantial empirical support, but no admitted paper validates the complete combined scheme in authentic workplace email or enterprise chat.

# Limitations

- The corpus mixes authentic workplace email and Slack with scenario-driven meetings, telephone dialogue, news, biomedical text, contracts, industry requirements, and other transfer domains; results from those domains do not establish production workplace accuracy.
- No admitted benchmark jointly evaluates all target fields, so evidence for individual components cannot be interpreted as validation of their combination.
- Several older email studies use relatively small datasets, hand-engineered features, or annotation schemes that differ from modern structured extraction tasks.
- Owner, request, commitment, and action-item annotations show nontrivial annotator disagreement, so some apparent model errors may reflect genuine task ambiguity.
- Exact-span metrics favor explicitly realized arguments and cannot by themselves evaluate implicit arguments that have no literal source span.
- Meeting decision studies demonstrate multi-utterance decision structure but do not establish equivalent behavior in authentic enterprise email or chat.
- The synthesis relies on the supplied per-paper analyses rather than re-reading the original papers, so it cannot resolve omissions or interpretation errors in those analyses.
- The inherited Topic 04 uncertainty about exact proposition-level approval, rejection, agreement, and answer scope remains outside this synthesis and must not be inferred from Topic 05 act labels.
