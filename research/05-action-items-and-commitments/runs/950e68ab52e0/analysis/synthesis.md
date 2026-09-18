# Executive Summary

The 39-paper corpus provides direct workplace-email and enterprise-chat evidence for detecting requests, commitments, action items, assignees, proposals, decisions, and related dialogue acts, while adjacent event, temporal, modality, and negation research supplies transfer evidence for argument and scope modeling. Across the corpus, contextual information frequently improves extraction, but gains are task- and corpus-dependent and can reverse for particular classes. Owner assignment is especially difficult because responsibility can be implicit, plural, role-dependent, or absent from message recipients. Conditionality, negation, and modality require attachment to the affected action rather than cue detection alone. Exact spans work well for explicit arguments, but implicit and scattered arguments can lack one contiguous evidence span. No admitted paper jointly validates the complete target representation, so the combined scheme remains untested.

# Themes

- Structured action and commitment representations separate the speech act or event from arguments such as actor, action, beneficiary, timeframe, agreement, and condition.
- Context beyond the target sentence often improves workplace act extraction, but its benefit depends on task, corpus, and context-selection strategy.
- Owner or assignee resolution is substantially harder than detecting that an action or commitment exists.
- Conditionality, negation, speculation, and modality are scope or attachment problems rather than only lexical-cue problems.
- Temporal expressions must be related to particular events or actions; detecting a date alone does not establish a deadline relation.
- Exact evidence spans provide strong provenance for explicit arguments but do not naturally represent implicit or discourse-scattered arguments.
- Workplace messages can contain multiple intents, acts, or task predicates, and action creation can span several utterances.
- Proposal, decision, agreement, request, and commitment are empirically distinguishable categories, but their structured argument extraction is unevenly covered.
- Domain and genre differences materially affect extraction and transfer performance.

## Evidence-based findings

1. Direct workplace-email annotation studies show that requests and commitments can be identified with useful agreement, but commitments are harder to annotate consistently than requests, especially for conditional offers, implicit obligations, and group-directed messages. [manual-0839b98ee7] [manual-20b8cd2fdd] [manual-d19b0f6f1e]

2. Workplace email, Slack, and meeting studies repeatedly report benefits from conversational context, but the magnitude and direction of the effect depend on the act being classified and on the corpus or context configuration. [doi-10-1145-3331184-3331260] [2312.05471] [2303.16763] [doi-10-1145-1076034-1076094]

3. In the studied meeting corpora, action items are represented more informatively as multi-component and sometimes multi-utterance structures containing task description, owner, timeframe, and agreement than as a single flat action-item label; owner detection is among the weakest reported component tasks. [doi-10-1007-11965152-18] [doi-10-3115-1564535-1564540] [doi-10-18653-v1-2007-sigdial-1-4]

4. Direct email and enterprise-chat evidence shows that responsibility can be implicit, plural, absent from the recipient list, or dependent on participant role and project responsibility, and owner annotation itself has substantial disagreement. [doi-10-18653-v1-w18-6104] [2312.05471]

5. The studied workplace corpora contain messages or sentences with multiple intents or multiple task-related acts, and systems or annotation schemes have represented coordinated task predicates or multiple acts rather than forcing one label per message. [doi-10-1145-3331184-3331260] [2312.05471] [doi-10-18653-v1-2020-coling-main-164]

6. Transfer evidence from meeting action-item summarization and general temporal-event extraction shows that temporal expressions alone are insufficient for accurate event or action timing: semantic features and the linguistic relation between an event and its temporal expression materially affect extraction performance. [doi-10-18653-v1-2007-sigdial-1-4] [doi-10-1162-tacl-a-00006]

7. Direct email annotation and adjacent-domain modality and negation studies show that conditionality, modality, speculation, and negation cannot be reliably reduced to detecting cue words: the affected proposition or event and the cue's scope or target must also be resolved, and scope resolution remains substantially harder than cue detection. [manual-d19b0f6f1e] [manual-0839b98ee7] [1410.4868] [doi-10-1186-1471-2105-9-s11-s9] [manual-ee40d588e3] [2106.08037]

8. Event-extraction transfer studies demonstrate two different evidence regimes: explicit arguments can be evaluated and extracted as exact spans, while implicit or scattered arguments may have no single contiguous source span and remain substantially harder to recover. [2202.12109] [1909.03546] [2410.03594] [doi-10-18653-v1-2020-acl-main-667]

9. Large-organization email annotation distinguishes proposed actions from stated decisions, while meeting-decision corpora distinguish proposal, restatement, agreement, and related stages of collective decision formation rather than treating all decision-related utterances as one class. [doi-10-18653-v1-2023-findings-acl-378] [doi-10-3115-1708376-1708410] [manual-90280d2776]

10. Email-domain variation measurably affects commitment and intent classification: cross-corpus commitment performance degrades without adaptation, while separate weak-supervision experiments show that noisy behavioral labels can still improve or transfer intent detection under their evaluated conditions. [doi-10-1145-3289600-3290984] [2005.13084]

# Contradictions

### Context is useful, but not uniformly so

Full-message or longer context improves several workplace-email, Slack, and meeting tasks. The email DCRNN results improve with increasing context, Slack dialogue-act classification improves with a longer temporally bounded window, and AMC-A action detection improves with local and global context. [doi-10-1145-3331184-3331260] [2312.05471] [2303.16763]

However, collective thread classification degrades the Deliver act in one email study, and the context configuration strongest on AMC-A is not the strongest configuration on AMI. [doi-10-1145-1076034-1076094] [2303.16763] The corpus therefore does not establish a universally beneficial context window.

### Sentence-level versus message-level granularity

Sentence-level action-item classifiers improve document-level action-item detection in one email study. [doi-10-1145-1076034-1076140] In contrast, workplace request/commitment annotation reaches higher human agreement when performed at message level than at sentence level in another line of work. [manual-20b8cd2fdd] [manual-d19b0f6f1e]

These experiments measure different outcomes—model detection versus annotation reliability—so neither result eliminates the other, and the evidence does not identify a single granularity that dominates both.

### Exact spans versus implicit or scattered arguments

PAIE and span-based information-extraction work successfully represent explicit arguments through start/end offsets. [2202.12109] [1909.03546] In contrast, the complex-event-argument study reports that many arguments are implicit or scattered and therefore lack a single contiguous textual span. [2410.03594] Head-based implicit-argument work likewise treats non-local argument recovery as a distinct problem. [doi-10-18653-v1-2020-acl-main-667]

These papers use different event-extraction settings; they do not jointly validate one provenance representation covering both regimes.

### Recipient-based ownership versus recipient-external ownership

The French professional-email extractor uses an Agent corresponding to the email recipient as part of its action-request filter. [manual-e6bb5aee88] EPA explicitly observes email tasks whose responsible people are plural, implicit, or absent from the candidate recipients. [doi-10-18653-v1-w18-6104]

The former is an operational restriction for one task formulation; the latter demonstrates that such a restriction does not cover all email ownership cases.

### Negation has incompatible operational meanings across tasks

Lin filters negated imperatives so that prohibitions are not extracted as positive tasks. [doi-10-18653-v1-2020-coling-main-164] The commitment-monitoring work primarily treats negation as evidence that an existing commitment has been canceled. [doi-10-1109-scc-2013-62] The French email task definition explicitly permits negative requested actions. [manual-e6bb5aee88]

These are different semantic phenomena and cannot be silently reduced to one rule such as “negation means no action.”

### Cross-domain transfer is possible but not stable

Commitment detection degrades when transferred between Avocado and Enron without adaptation, and corpus identity itself is highly predictable. [doi-10-1145-3289600-3290984] A separate weak-supervision study nevertheless reports useful Avocado-to-Enron zero-shot intent performance. [2005.13084]

The experiments use different tasks, supervision, and metrics. They demonstrate that transfer can work under some conditions but do not demonstrate domain invariance.

# Open Gaps

### gap-1 — ACADEMIC, HIGH

There is no direct modern workplace email/chat benchmark in this corpus that jointly annotates speech-act type, owner/assignee, action object, deadline, conditions/exceptions, and exact evidence spans.

Suggested query: `"action item extraction" (email OR Slack OR workplace chat) assignee deadline condition "evidence span" corpus`

**Status: open.** Direct workplace papers cover subsets of the structure, including speech acts, owners, semantic roles, and context, but no admitted benchmark jointly covers all requested fields. [manual-d19b0f6f1e] [doi-10-18653-v1-w18-6104] [manual-e6bb5aee88] [2312.05471]

### gap-2 — ACADEMIC, HIGH

Direct empirical evidence for extracting decisions, approvals, rejections, and proposals with structured arguments from authentic workplace email or chat is still missing from this corpus.

Suggested query: `("decision extraction" OR "decision detection") (workplace email OR enterprise chat OR Slack) proposal approval rejection argument extraction`

**Status: open.** Large-organization email work distinguishes ProposeAction from StateDecision, and meeting studies model decision-discussion structure, but they do not provide the missing direct workplace structured-argument extraction benchmark. [doi-10-18653-v1-2023-findings-acl-378] [doi-10-3115-1708376-1708410] [manual-90280d2776]

### gap-3 — ACADEMIC, HIGH

Owner/assignee extraction remains weakly evidenced, especially for implicit owners, group ownership, multiple actions with different owners, and owners recoverable only from organizational or conversation context.

Suggested query: `("assignee prediction" OR "assignee extraction" OR "responsibility extraction") email workplace implicit owner group owner action item`

**Status: open.** EPA and Slack establish that responsibility can be plural, implicit, recipient-external, or role-dependent, while meeting work reports low owner-classification performance; the harder variants in this gap remain unresolved. [doi-10-18653-v1-w18-6104] [2312.05471] [doi-10-1007-11965152-18]

### gap-4 — ACADEMIC, HIGH

The corpus does not establish reliable deadline binding in workplace communication: distinguishing a deadline for a particular action from a merely mentioned date, shared date, scheduling expression, or conditional future time remains open.

Suggested query: `("deadline extraction" OR "due date extraction") (email OR workplace communication) action item temporal relation event argument`

**Status: open.** Meeting and temporal-event studies show the importance of relational and semantic evidence, but no admitted direct workplace study evaluates action-specific deadline binding against the stated distractor cases. [doi-10-18653-v1-2007-sigdial-1-4] [doi-10-1162-tacl-a-00006] [manual-e6bb5aee88]

### gap-5 — ACADEMIC, HIGH

Direct workplace evidence is insufficient for attaching conditions, exceptions, negation, and modality to the correct action when several actions or clauses occur together.

Suggested query: `("conditional commitment" OR "deontic modality" OR "negation scope") (email OR workplace communication) action extraction condition attachment`

**Status: open.** Workplace email studies establish that conditional commitments are difficult, and adjacent-domain work supplies scope and target mechanisms, but the corpus does not directly benchmark multi-action workplace attachment. [manual-d19b0f6f1e] [manual-0839b98ee7] [1410.4868] [manual-ee40d588e3] [doi-10-18653-v1-2020-coling-main-164]

### gap-6 — ENGINEERING, HIGH

Build an independent argument-level benchmark and adversarial fixture suite covering implicit owners, multiple actions in one sentence, shared deadlines, conditional and negated actions, overlapping request/commitment labels, quoted-history contamination, and attachment references; score false positives, false negatives, and each argument separately.

**Status: open.** The literature exposes many of these failure modes but does not constitute this independent project benchmark. [doi-10-18653-v1-w18-6104] [doi-10-1145-3331184-3331260] [2410.03594] [manual-cd3fa58e4c]

### gap-7 — ENGINEERING, HIGH

Compare sentence-local, message-level, and selectively expanded thread-context extraction with controlled ablations, because the literature shows both context gains and context-induced degradation.

**Status: open.** Existing papers motivate the comparison but do not perform this project-specific controlled evaluation. [doi-10-1145-3331184-3331260] [2303.16763] [doi-10-1145-1076034-1076094] [2312.05471]

### gap-8 — ENGINEERING, HIGH

Test author/quoted/forwarded content zoning while preserving provenance, and measure whether zoning improves act and argument extraction without losing obligations whose interpretation depends on prior-message context.

**Status: open.** Direct email evidence shows that zoning can substantially improve request detection, while other email work shows that some obligations require wider context. The requested combined provenance-and-recall evaluation has not been performed. [manual-cd3fa58e4c] [manual-20b8cd2fdd]

### gap-9 — ENGINEERING, HIGH

Evaluate an uncertainty-preserving structured output in which owner, deadline, condition, or act subtype can remain unresolved, and measure whether this reduces false obligations and wrong argument assignments without unacceptable recall loss.

**Status: open.** EPA permits a no-one ownership outcome, and implicit-argument research documents unresolved or non-resolvable roles, but no admitted study evaluates this project's uncertainty-preserving output against false obligations and recall. [doi-10-18653-v1-w18-6104] [2410.03594] [manual-69bc2555ab]

### gap-10 — OUT_OF_SCOPE, HIGH

Exact proposition-level scope for approvals, rejections, agreement, clarification, and answers in authentic workplace email or enterprise chat remains an inherited Topic 04 research gap. Topic 05 act extraction does not resolve that antecedent-scope question.

# Actionable Insights

- **Synthesis-derived recommendation:** represent each extracted work item as a typed act plus separately addressable arguments and provenance, while allowing any unresolved owner, deadline, condition, or subtype to remain explicitly unknown.
- **Synthesis-derived recommendation:** distinguish explicitly stated owners from context-inferred owners, and support one owner, multiple owners, group ownership, and no resolved owner without forcing a recipient-based assignment.
- **Synthesis-derived recommendation:** represent a deadline as a relation between a particular action and a temporal expression, preserving the original wording separately from any normalized time value.
- **Synthesis-derived recommendation:** represent conditions, exceptions, negation, and modality as scoped relations to particular actions or propositions rather than as message-level flags.
- **Synthesis-derived recommendation:** support multiple actions per sentence or message and permit evidence to consist of several spans; when an argument is implicit, do not fabricate a textual span and instead record the inference and its supporting context separately.
- **Synthesis-derived recommendation:** evaluate sentence-local, message-level, and selectively expanded thread context under controlled ablations instead of assuming that maximum available context is always beneficial.
- **Synthesis-derived recommendation:** apply quoted/forwarded-content zoning as an experimental context-control mechanism while preserving the original source and testing for obligations whose interpretation depends on prior-message material.
- **Synthesis-derived recommendation:** keep speech-act classification separate from antecedent/reference scope; a request, commitment, approval, or rejection label should not by itself be treated as evidence that the system identified the correct proposition to which the act applies.
- **Synthesis-derived recommendation:** evaluate at argument level as well as item level, including false positive obligations, missed obligations, wrong owners, wrong action objects, wrong deadline attachment, lost conditions, and failures involving several actions or owners.
- **Synthesis-derived recommendation:** preserve proposal, intention, decision, approval, request, and commitment as distinct semantic states until direct evidence or project evaluation supports any intended collapsing of categories.
- **Synthesis-derived recommendation:** keep extraction of the uttered action or decision event separate from later lifecycle-state tracking such as completion, revocation, contradiction, or supersession.

# Confidence Summary

The corpus provides **well-supported design principles** around structured action representations, the value and risk of conversational context, the difficulty of owner resolution, the importance of conditionality and scope, the distinction between proposal and decision, and the provenance advantages of span-level extraction for explicit arguments.

Confidence is strongest where several direct workplace email/chat studies converge, particularly for requests and commitments [manual-0839b98ee7] [manual-20b8cd2fdd], contextual effects [doi-10-1145-3331184-3331260] [2312.05471], multiple intents [doi-10-1145-3331184-3331260], and assignee ambiguity [doi-10-18653-v1-w18-6104].

Evidence for deadline-to-action binding, exact condition attachment, and complex implicit arguments relies substantially on meetings or adjacent temporal, modality, negation, and event-extraction domains. [doi-10-18653-v1-2007-sigdial-1-4] [doi-10-1162-tacl-a-00006] [1410.4868] [manual-ee40d588e3] [2410.03594] Those results support candidate mechanisms and experiments, not production workplace accuracy.

No paper validates the full combined speech-act-plus-owner-plus-object-plus-deadline-plus-condition-plus-provenance scheme. Papers validating individual aspects do not jointly validate that combination.

# Limitations

- The synthesis is based on the supplied research questions and top findings rather than independent inspection of each full paper, so details absent from those summaries could alter interpretation.
- The corpus mixes authentic workplace email/chat, meetings, general dialogue, event extraction, biomedical negation, and temporal-relation research; transfer evidence has therefore been kept separate from direct workplace evidence.
- Metrics, label inventories, annotation units, languages, and corpus construction differ substantially across papers, preventing direct numerical aggregation.
- Several older workplace studies use small or organization-specific datasets, and direct evidence for current enterprise-chat environments is comparatively limited.
- The corpus contains no production data from msgloom's intended mailbox or Teams environment, so it does not establish production representativeness.
- Exact-span extraction and implicit-argument recovery use different task formulations; the corpus does not empirically validate a single provenance representation covering both.
- The inherited Topic 04 proposition-scope gaps remain unresolved dependencies and are not closed by Topic 05 act classification.
- The literature validates individual aspects of structured extraction, but no admitted experiment jointly validates their combination.
