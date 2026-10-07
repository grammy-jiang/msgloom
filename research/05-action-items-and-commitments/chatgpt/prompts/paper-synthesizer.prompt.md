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

# Task: cross-paper synthesis

Research topic: **authentic workplace email and enterprise-chat benchmarks for structured action/decision extraction, focusing specifically on implicit and group assignees, action-to-deadline binding, condition/negation/modality scope, and exact argument evidence spans**

Below are 48 per-paper analyses (reduced to questions and top findings to fit the size cap). Synthesize them into a
cross-paper synthesis: recurring themes, contradictions (name the papers on
both sides), open gaps classified as ENGINEERING (fillable from docs, code,
or benchmarks), ACADEMIC (needs more papers) or OUT_OF_SCOPE, actionable
insights, an overall confidence note, and the synthesis' own limitations.
Every finding must cite at least one paper_id from this list: `1410.4868`, `1606.07849`, `1606.07965`, `1909.03546`, `1909.10094`, `1911.03766`, `2005.13084`, `2104.05919`, `2106.08037`, `2109.09393`, `2202.12109`, `2303.16763`, `2305.13469`, `2312.05471`, `2409.18602`, `2410.03594`, `doi-10-1007-11965152-18`, `doi-10-1109-hicss-2006-528`, `doi-10-1109-scc-2013-62`, `doi-10-1145-1076034-1076094`, `doi-10-1145-1076034-1076140`, `doi-10-1145-3289600-3290984`, `doi-10-1145-3331184-3331260`, `doi-10-1145-3594536-3595162`, `doi-10-1162-coli-a-00110`, `doi-10-1162-tacl-a-00006`, `doi-10-1186-1471-2105-9-s11-s9`, `doi-10-18653-v1-2007-sigdial-1-4`, `doi-10-18653-v1-2020-acl-main-667`, `doi-10-18653-v1-2020-coling-main-164`, `doi-10-18653-v1-2023-findings-acl-378`, `doi-10-18653-v1-d16-1078`, `doi-10-18653-v1-n18-1076`, `doi-10-18653-v1-w18-6104`, `doi-10-26615-978-954-452-092-2-076`, `doi-10-3115-1564535-1564540`, `doi-10-3115-1708376-1708410`, `manual-01c535c108`, `manual-0839b98ee7`, `manual-1e8332286e`, `manual-20b8cd2fdd`, `manual-69bc2555ab`, `manual-90280d2776`, `manual-cd3fa58e4c`, `manual-d19b0f6f1e`, `manual-e6bb5aee88`, `manual-ee40d588e3`, `manual-fde6beef40`.
Do not cite any other paper.

The independent reviewer that reads this rejects one thing above all others,
and it has rejected the first round of every topic so far for it: **a
project judgement written as a literature finding**. Separate them here and
the review passes on the first attempt.

- A `finding` states what the cited papers demonstrate, and nothing further.
  If the papers show a method works on one corpus, say that; do not say the
  method is required, necessary, or suitable for this project.
- An `actionable_insight` is where a recommendation belongs. Mark every one
  that goes beyond the experiments as a synthesis-derived recommendation,
  in those words, and do not attach paper citations to the part that is a
  project decision. Citing a paper for a decision it never tested is the
  single most common rejection.
- Deciding which part of the product owns a problem, or which later topic a
  case is routed to, is always a project decision. It carries no citation.
- `confidence_summary` describes the evidence, not the design. Write
  "well-supported design principles", never "necessary design requirements".
- Papers that each validate one aspect do not jointly validate a combined
  scheme. Say what each one covers and that the combination is untested.
- A gap you believe is real stays in `gaps` with its classification. It does
  not become a finding by being restated confidently.

Before you reply, check your own draft against the five things the reviewer
rejects for. These are its triggers, not a paraphrase, and any one of them
sends the work back:

1. A finding cites no analysis, or cites a paper outside the list above.
2. A finding states more than its evidence supports.
3. A contradiction between analyses is dropped or silently averaged away.
   Name it in `contradictions` even when it is inconvenient.
4. A gap the corpus cannot close is presented as closed. If no admitted paper
   answers it, it is open.
5. Transfer evidence is presented as direct evidence. Say which domain each
   result comes from, and never let an adjacent-domain or synthetic result
   carry a production claim.

Go through your findings one at a time against this list. Fixing a sentence
now costs you nothing; a rejection costs a full synthesis and review cycle.


## Project context you must work within

This is the project's own description of the problem, its boundaries,
and the distinctions it needs preserved. It governs what counts as
relevant; the academic task names alone do not.

# Topic 05 context — Action items, requests, commitments, and decisions

## Why this Topic exists

msgloom's primary success criterion is not generic summarization quality: it is avoiding missed work that requires the user's response. That requires identifying what someone is asking for, promising, deciding, approving, assigning, or expecting — including owner, object, deadline, conditions, prerequisites, and evidence.

Business language is often indirect: “Can you take a look?”, “I’ll get this over once Finance confirms”, “We should proceed”, “Approved up to 50k”, “John to send by Friday”, or “No action needed unless X happens”. A system that extracts only verbs or dates can create false obligations or lose conditions.

Topic 05 owns **the semantic extraction and classification of action/commitment/decision content**, not its later state over time.

## Core research object

Represent work-relevant speech acts/events with explicit arguments and uncertainty, for example:

```text
type: request | commitment | decision | approval | proposal | action item
actor / owner
object / target
recipient / beneficiary
status/modality at utterance time
original deadline wording + normalized time if justified
conditions / prerequisites / exceptions
source span(s)
confidence / unresolved fields
```

Missing owner or deadline must remain unknown rather than be invented to make an action executable.

## Product and phase relevance

Topic 05 directly supports Phase 1 A3 triage outputs: actions, deadlines, risks, and required responses. Phase 3 A6 later consumes accepted Topic information to prepare drafts/proposals, but Topic 05 research must not cross into executing actions. A reviewed draft is not approval.

## Direct handoffs from earlier Topics

Topic 04 (completed 2026-09-16, 47 papers, 4 rounds) resolved **what a response is about**: the exact proposition, question or request an approval, rejection, answer or commitment applies to, including partial and multi-antecedent scope. It explicitly does **not** classify the act itself. Topic 05 owns the speech-act label and takes the antecedent scope as given. Topic 04's open ACADEMIC gap 1 is directly relevant: direct empirical evidence for proposition-level approval, rejection and agreement scope in authentic workplace mail or chat is still missing, so a Topic 05 act label must not be read as evidence that its scope is correct.

**The full text of every inherited handoff is in [`INHERITED_HANDOFFS.md`](INHERITED_HANDOFFS.md)**, including what each sending Topic established, what it left open, and where the ownership boundary lies. Read it before planning; you do not need to open an earlier Topic's folder.

## Relationships to other Topics

| Topic | Relationship |
| --- | --- |
| 02 | Supplies correct Topic scope so extracted actions/conditions attach to the right work matter. |
| 04 | Resolves what “approved”, “agreed”, or “please do that” refers to before Topic 05 interprets the speech act/action. |
| 06 | Topic 05 extracts the event/commitment; Topic 06 tracks whether it is planned, confirmed, revoked, completed, contradicted, etc. |
| 07 | Missing owner/object/context can become an explicit retrieval gap in Phase 2. |
| 08 | Action evidence may live in attachments/tables/screenshots; Topic 08 supplies grounded content. |
| 09 | Briefing uses action/deadline/decision outputs to decide what must remain visible. |
| 10 | Reliability evaluation checks evidence support and missed actions; generic calibration belongs there. |

## Key conceptual distinctions

- Request ≠ commitment.
- Proposal/intention ≠ decision.
- Mentioned action ≠ assigned action item.
- Capability (“can do”) ≠ promise (“will do”).
- Conditional commitment ≠ unconditional commitment.
- Deadline mention ≠ deadline for this action.
- Owner inferred from context must remain distinguished from explicitly stated owner.
- Extracting an action is not the same as determining its later state (Topic 06).

## High-value academic terminology

- action item extraction / detection;
- task extraction; to-do extraction; task-oriented information extraction;
- email speech act classification; dialogue act classification;
- request detection / request identification;
- commissive speech acts; commitment extraction/detection;
- promise detection; obligation detection; deontic modality;
- intention detection; intent-to-act;
- decision extraction / decision detection; meeting decision detection;
- event extraction; event argument extraction; semantic role labeling;
- implicit argument resolution; zero anaphora / omitted argument recovery (transfer);
- conditionality detection; hedge/speculation/modality detection;
- temporal expression extraction and normalization; deadline extraction;
- responsibility/owner assignment; assignee extraction;
- email action-item / request-response corpora.

## Query families

- `"action item extraction" email`
- `"task extraction" business email`
- `email "speech act classification" request commitment`
- `"commitment detection" dialogue email`
- `"commissive" speech act NLP commitment`
- `"decision extraction" meeting email`
- `"event argument extraction" implicit argument owner`
- `"deontic modality" obligation NLP`
- `deadline extraction email temporal normalization`
- `conditional commitment detection NLP`
- `request detection workplace communication`

## False friends / exclusions

- generic intent classification with no action arguments;
- calendar/event extraction that treats every date as a deadline;
- sentiment or urgency classification;
- Topic 06 factuality/state tracking;
- recommendation generation / drafting (Phase 3 A6);
- action execution / tool invocation (Phase 4 A7).

## Gap-evaluation guidance

Give highest priority to gaps that cause missed user-response obligations, false obligations, wrong owners, wrong deadlines, or lost conditions. Evaluate argument-level preservation rather than only speech-act accuracy. Direct business-email evidence is especially valuable, but strong transfer evidence from meetings/dialogue can justify representations or experiments if labeled as transfer. Engineering tests should include implicit owner, multiple actions in one sentence, shared deadlines, conditional/negated actions, and ambiguous references resolved by Topic 04.

## How to use this file

This file is the self-contained research context for this Topic. A future AI research agent should read **this file first**, then `BRIEF.md`, then any existing `CURRENT_STATUS.md`, gap decisions, reports, manifests, and prior-round artifacts in this folder. The aim is that an agent given only this Topic folder can reconstruct the project intent, Topic boundary, dependencies, search vocabulary, and gap-prioritization logic without relying on the original ChatGPT conversation.

If the full repository is available, the authoritative product documents remain `../../docs/design-brief.md`, `../../docs/design-principles.md`, `../../docs/design.md`, and `../../docs/phase-roadmap.md`. This file explains how those product constraints apply to this research Topic; it does not replace or approve changes to those design documents.

## Shared msgloom background

msgloom is a personal work-information system for one user. It is intended to process very large daily volumes of work communication, initially Outlook email and Microsoft Teams, while ensuring that **work requiring the user's response is not missed** and reducing how much the user must read to stay current.

The product is organized around **Topics**, not message summaries. A Topic is a concrete work matter described by information from one or more sources. One message can contain several Topics; one Topic can span many messages, conversations, attachments, groups, and eventually multiple sources. A conversation or Group is therefore not automatically one Topic.

The report contract is the ultimate product pressure on all ten research Topics. Reports must preserve every due Topic and the decision-relevant information needed to act on it, including developments, actions, deadlines, conditions, risks, uncertainty, and links back to exact source evidence. Missing or conflicting information must remain visible rather than being silently filled in.

The design decision order is important when evaluating research gaps: user permissions are fixed; then preserve correct meaning and report coverage; then traceability and recovery; then usability/maintenance; finally speed, brevity, and token savings. A method that is faster but loses a condition, deadline, branch, source relation, or important Topic is not an improvement for msgloom.

Important persistent principles:

- Use deterministic code for reliable mechanical relationships and AI for language understanding/judgement.
- Preserve source bytes, versions, stage history, identities, and lineage. New assessments do not erase old evidence.
- Group only on reliable relationships. Similar subjects, participants, wording, or model labels are not enough to prove Topic identity.
- Keep uncertain relationships separate and make the reason for uncertainty visible.
- Brevity must come from concise wording and layered detail, never from omitting decision-essential information.
- User-reviewed examples, missed important work, false alerts, wrong grouping, lost actions/deadlines, and evidence that changes a decision matter more than paper count or message throughput.

## Research-programme relationship

The ten Topics form a dependency network rather than ten independent literature reviews. A useful conceptual flow is:

```text
01 source/conversation structure
        ↓
02 within-message Topic spans/membership
        ↓
03 cross-thread/source Topic identity
        ↓
04 reference and response scope
        ↓
05 actions / requests / commitments / decisions
        ↓
06 state / factuality / time / revision
        ↓
07 retrieve missing context when needed
        ↘
08 understand attachments / tables / images
        ↓
09 incremental personalized briefing
        ↓
10 evidence, completeness, calibration, reliability evaluation
```

This is not a strict processing pipeline. Several Topics feed each other, and Topic 10 is cross-cutting. The numbering primarily gives a research order and ownership boundary so that one Topic does not silently absorb the whole product problem.

## Gap-evaluation rules inherited from Topics 01 and 02

The Research Pipeline must evaluate gaps using **project value**, not just academic novelty. The following rules are part of the context for every Topic:

1. A machine-classified `HIGH` or `ACADEMIC` gap does **not** automatically authorize another literature round.
2. After each academic round, perform a human/project-value review: decide whether the uncertainty is best addressed by more papers, engineering experiments, a later Topic, production-domain data, candidate-method selection, or no further current work.
3. Prefer targeted academic follow-up over broad searching. Do not fill paper quotas with weakly related literature.
4. Distinguish direct target-domain evidence from transfer methods/evaluation evidence. Transfer evidence can justify a mechanism or experiment, not production-email accuracy.
5. Engineering validation may use independent synthetic/adversarial fixtures and public data. Lack of production mailbox examples is not a reason to stop work that can be validly completed without them.
6. Never claim production representativeness from synthetic or transfer evidence. Record it as deferred until suitable authorized domain data exists.
7. If a gap belongs to another Topic, hand it off explicitly rather than duplicating research.
8. Research closure means **everything actionable at the current stage is complete and remaining work is explicitly deferred/handed off**. It does not mean literature exhaustion, production accuracy, or architecture approval.
9. For new academic work, use terminology refinement, strict paper admission, manual/controlled canonical acquisition, corpus freeze, fresh isolated Pipeline runs, direct-vs-transfer labels, independent review, strict validation, and post-round gap review. These are lessons learned from Topics 01 and 02.
10. For engineering research, keep gold independent from the component under test; structurally separate prediction inputs from evaluation gold/future context; count false positives and false negatives in end-to-end denominators; use clean-workspace reproducibility, mutation/regression tests, and fresh independent methodological review.

## Work handed to this topic by an earlier one

Treat each entry as a starting condition, not as something to
rediscover. Where a sending topic left a gap open it is still open:
do not report it as established. Respect the stated ownership
boundary and do not absorb what the sender still owns.

# Inherited handoffs

Everything an earlier Topic explicitly handed to this one, copied in full so
that this folder is enough on its own. You do not need to open an earlier
Topic's documents to start work here.

Each entry states what was handed over, what the sending Topic still owns, and
what it had established or left open at the time. A handoff is not a finding:
where the sender left a gap open, it is still open.

## From Topic 04 — Reference resolution and response scope

*Completed 2026-09-16. 4 rounds, 47 papers, report validated PASS,
faithfulness 0.91. Five gaps left open, none downgraded.*

**Handed to Topic 05.** Topic 04 resolves **what a response is about**: the
exact proposition, question or request that an approval, rejection, answer or
commitment applies to, including partial scope and links to several
antecedents at once. It explicitly does not classify the act. Topic 05 owns
the speech-act label and takes the antecedent scope as given.

**What Topic 04 established.** Direct evidence for multi-question partial
replies is materially stronger than for the other scope questions. Response
scope is routinely partial: a reply commonly addresses some propositions in a
message and leaves others unresolved, and systems that force one
message-level label lose that distinction.

**What Topic 04 left open, and that Topic 05 must not treat as settled:**

- *(ACADEMIC, HIGH)* Direct empirical evidence for exact proposition-level
  agreement, rejection, approval, clarification and answer scope in authentic
  workplace email or enterprise chat is still missing. **A Topic 05 act label
  must therefore not be read as evidence that its scope is correct.**
- *(ACADEMIC, HIGH)* Workplace messages that mix questions, requests,
  alternatives and conditions are not yet validated together with complete
  unresolved-subquestion detection. Missing mixed-act validation can cause
  open work to be closed incorrectly, which is directly a Topic 05 risk.
- *(ACADEMIC, MEDIUM)* Whether a response independently targets several
  propositions or targets one composite object is unresolved. This affects
  how many action items one reply should produce.

**Boundary.** If Topic 05 finds itself deciding which proposition an action
applies to, that is Topic 04's question and its evidence, including its open
gaps, applies.

Per-paper analyses:
[
 {
  "paper_id": "1410.4868",
  "title": "A Modality Lexicon and its use in Automatic Tagging",
  "research_question": "Can a practical modality annotation scheme and lexicon support automatic identification of modality triggers and their semantic targets with useful precision for downstream language processing?",
  "key_findings": [
   "The representation explicitly distinguishes a modality trigger from the target proposition or event over which that modality operates, providing a form of trigger-to-evidence binding.",
   "The annotation design represents several interactions between modality and negation through thirteen operational choices plus target polarity, but it deliberately simplifies some semantically distinct negation readings.",
   "Although holder is one of the three theoretical modality components, holders were not annotated and automatic holder identification was left outside the project scope.",
   "The semi-automatically expanded modality lexicon began from about 150 trigger lemmas and was made publicly available.",
   "Sentence-level agreement between the string-based and structure-based taggers was kappa 0.82 for triggers and 0.76 for targets."
  ]
 },
 {
  "paper_id": "1606.07849",
  "title": "Focused Meeting Summarization via Unsupervised Relation Extraction",
  "research_question": "Can unsupervised relation extraction identify the salient content phrases associated with individual meeting decisions well enough to support focused, potentially abstractive decision summaries?",
  "key_findings": [
   "The paper distinguishes a Decision Cue from the Decision Content and argues that only the content phrase, rather than the entire decision-related utterance, should normally enter a focused decision summary.",
   "The relation representation extracts phrase-level indicator-argument structures, providing finer evidence than whole-utterance decision detection and preserving identifiable source phrases.",
   "Under gold decision clusterings, configurations of the unsupervised method outperform the reported utterance-level and generic relation-extraction baselines on ROUGE-1 F1 and ROUGE-SU4 F1, while remaining competitive rather than superior to the strongest supervised SVM.",
   "With true clusterings, the 10-relation model reports ROUGE-1 F1 of 37.47, ROUGE-2 F1 of 12.20, and ROUGE-SU4 F1 of 14.59; the supervised SVM reports 40.87, 12.91, and 16.29 respectively.",
   "Performance falls substantially when automatically produced decision clusterings replace gold clusterings, showing strong dependence on accurate upstream association of dialogue acts with decisions."
  ]
 },
 {
  "paper_id": "1606.07965",
  "title": "Summarizing Decisions in Spoken Meetings",
  "research_question": "How effectively can decision-related utterances in multi-party meetings be clustered by decision and summarized using dialogue-act-level or token-level supervised and unsupervised methods?",
  "key_findings": [
   "Decision-related dialogue acts can be distributed and interleaved across a meeting, motivating an explicit clustering stage before decision summarization.",
   "Supervised clustering performs better than the reported unsupervised LDA clustering on B-cubed F1, although the LDA method remains competitive for downstream summary quality.",
   "With automatically produced clusters, an unsupervised LDA-based clustering pipeline can yield decision-summary quality comparable to the supervised clustering alternative.",
   "When true decision clusters are supplied, supervised token-level summarization with discourse context achieves the strongest reported supervised configuration and approaches the paper's extractive upper bound more closely than automatic-cluster conditions.",
   "The AMI data are scenario-driven four-person design-team meetings rather than authentic enterprise email or chat logs."
  ]
 },
 {
  "paper_id": "1909.03546",
  "title": "Entity, Relation, and Event Extraction with Contextualized Span Representations",
  "research_question": "Can a unified span-based information-extraction architecture combine contextualized language representations and dynamically propagated span graphs to improve entity, relation, and event extraction across domains?",
  "key_findings": [
   "The framework achieves reported state-of-the-art results on the three high-level extraction tasks and on all listed subtasks except event argument identification, although event-argument gains are not statistically supported.",
   "Coreference propagation improves named-entity recognition across the evaluated domains and improves relation extraction on SciERC, demonstrating that non-local mention links can improve span representations.",
   "Event-specific graph propagation does not improve the best ACE event-extraction results; the authors hypothesize that asymmetric trigger-argument structure may require better higher-order modeling.",
   "Increasing BERT's sentence context can help some entity, relation, trigger, and argument tasks, but the effects are task-dependent rather than uniformly positive.",
   "Evaluation explicitly requires matching gold offsets, making this paper directly relevant to exact evidence-span extraction methodology."
  ]
 },
 {
  "paper_id": "1909.10094",
  "title": "Deep Structured Neural Network for Event Temporal Relation Extraction",
  "research_question": "Can a jointly trained neural and structured-prediction model improve event-event temporal relation extraction by combining contextual representations with global consistency constraints?",
  "key_findings": [
   "The global structured model improved over its local neural counterpart across all three temporal-relation datasets, and the TCR improvement of more than 1.2 F1 points was reported as statistically significant.",
   "With BERT representations, reported global-model F1 values were 63.2 on TB-Dense, 81.7 on MATRES, and 80.9 on TCR, exceeding the cited previous state of the art.",
   "Ablations show that transitivity constraints consistently improve results, while symmetry-related augmentation and constraints improve robustness when relation direction is reversed.",
   "BERT representations account for a substantial part of the gain, although the structured architecture using GloVe remained competitive or superior to previous systems on several datasets.",
   "Negation remained a significant failure mode: 20% of a manually analyzed sample of common errors was categorized as negation-related, and the authors explicitly identify better handling of negation and hypothetical language as future work."
  ]
 },
 {
  "paper_id": "1911.03766",
  "title": "Multi-Sentence Argument Linking",
  "research_question": "Can a document-level model reliably link event roles to argument spans across sentence boundaries, and can a new large-scale benchmark support progress on this task?",
  "key_findings": [
   "RAMS contains 9,124 annotated event instances from 3,993 news documents, with 139 event types, 65 role types, and 21,237 annotated argument links.",
   "Although most RAMS arguments occur in the trigger sentence, arguments in neighboring sentences remain common enough to motivate document-level linking, with 82% of annotated arguments reported as sentence-local.",
   "With gold trigger and gold argument spans supplied, the main model obtains 68.3 test F1, and type-constrained decoding using gold event types raises test F1 to 73.3.",
   "When the system must consider all possible spans instead of being given gold argument spans, performance drops to about 6 F1, showing that candidate-span identification is a major unresolved end-to-end difficulty.",
   "Performance on arguments one or two sentences from the trigger is comparable to performance on local arguments in the reported development-set analysis."
  ]
 },
 {
  "paper_id": "2005.13084",
  "title": "Learning with Weak Supervision for Email Intent Detection",
  "research_question": "Can noisy supervision derived from users' post-email interactions be combined with a small quantity of clean annotations to improve enterprise email intent detection?",
  "key_findings": [
   "Behavioral weak-labeling functions are informative but substantially noisy: manual checks reported accuracies of about 0.675 for Request Information, 0.71 for Schedule Meeting, and 0.63 for Promise Action.",
   "Hydra consistently outperformed comparison methods that had access to both clean and weak examples, with the advantage especially useful when clean labels were scarce.",
   "Both self-paced learning and explicit weak-label correction contributed measurably: at a 10% clean ratio aggregate accuracy fell from 0.716 to 0.690 without self-paced learning and to 0.688 without label correction.",
   "For the Request Information task with a fixed clean set, increasing weakly labeled data improved reported accuracy from 0.688 with no weak examples to 0.804 when the full weak set was used.",
   "Weak supervision learned from Avocado transferred to Enron; the reported zero-shot experiment using an Avocado-trained Hydra model achieved 0.738 accuracy on Enron."
  ]
 },
 {
  "paper_id": "2104.05919",
  "title": "Document-Level Event Argument Extraction by Conditional Generation",
  "research_question": "Can document-level event arguments be extracted more accurately by generating filled event templates conditioned on the entire document rather than classifying candidate argument spans independently?",
  "key_findings": [
   "Template-conditioned BART generation outperforms the compared extraction baselines on both RAMS and WikiEvents for document-level event argument extraction.",
   "The paper reports gains of 7.6 F1 on RAMS and 5.7 F1 on WikiEvents over the next-best compared systems, with a 9.3 F1 improvement for informative argument extraction.",
   "WikiEvents evaluates argument heads by matching annotated offsets, while an alternative coreference-aware score gives credit when the predicted mention is coreferential with the reference argument.",
   "Informative argument extraction deliberately prefers more informative mentions, such as names over nominal mentions and pronouns, which often requires selecting arguments farther from the trigger.",
   "The authors identify remaining errors in which mutually exclusive semantic roles are both predicted and note that commonsense reasoning is needed for some implicit arguments."
  ]
 },
 {
  "paper_id": "2106.08037",
  "title": "The Possible, the Plausible, and the Desirable: Event-Based Modality Detection for Language Processing",
  "research_question": "Can modality be modeled and automatically detected at the event level by identifying open-class modal triggers, assigning them a linguistically grounded fine-grained sense, and linking each trigger to the event it modifies?",
  "key_findings": [
   "Restricting modality to a small closed set of modal auxiliary verbs makes detection much easier than allowing modal triggers from arbitrary syntactic classes; for example, RoBERTa modal-versus-nonmodal F1 drops from 99.9 on the six modal verbs to 73.2 on all trigger types.",
   "When a modal trigger is already known, contextual information improves sense classification, especially for fine-grained senses: the full-context RoBERTa condition reaches 76.4 F1 versus 72.0 for majority voting, while masking the trigger reduces F1 to 58.3.",
   "For unrestricted trigger detection and classification, RoBERTa consistently improves over the majority-vote baseline; fine-grained labeled F1 is 58.14 compared with 51.29 for the baseline.",
   "Gold event-head information substantially helps modal-trigger tagging, but using predicted event heads can reduce performance because event-prediction errors propagate into trigger classification.",
   "Modal-trigger information improves detection of the event being modified: modal/nonmodal event-span F1 rises from 51.1 without trigger information to 71.13 with a gold trigger, although predicted-trigger information gives only 53.55."
  ]
 },
 {
  "paper_id": "2109.09393",
  "title": "Modality and Negation in Event Extraction",
  "research_question": "Can an open-domain event extractor distinguish events that happened, did not happen, or remain uncertain by modeling negation, modality, conditionality, counterfactuality, and propositional attitudes with syntactic scope?",
  "key_findings": [
   "MoNTEE represents several kinds of event uncertainty rather than treating all extracted events as factual, including explicit and lexical negation, modal operators, conditionality, counterfactuality, and propositional attitudes.",
   "The system uses dependency paths from modality triggers to events as a mechanism for approximating syntactic scope.",
   "On the 100-relation intrinsic evaluation, the three-way happened/uncertain/did-not-happen classification achieves micro-F1 of 0.81 and macro-F1 of 0.76.",
   "The paper explicitly excludes implicit negation from its treatment of negation, limiting coverage of pragmatically implied negative meaning.",
   "The authors identify missing discourse context as an important limitation because modality can depend on surrounding text rather than only the local sentence."
  ]
 },
 {
  "paper_id": "2202.12109",
  "title": "Prompt for Extraction? PAIE: Prompting Argument Interaction for Event Argument Extraction",
  "research_question": "Can prompt-based joint span extraction improve sentence- and document-level event argument extraction while handling long-range dependencies, multiple same-role arguments, limited supervision, and inference efficiency?",
  "key_findings": [
   "PAIE performs direct evidence-span extraction: an argument is represented by its start and end offsets and associated with an event role.",
   "PAIE achieved the strongest reported results in the paper on all three evaluated benchmarks, including base-model Arg-C scores of 69.8 on ACE05, 49.5 on RAMS, and 63.4 on WIKIEVENTS.",
   "Joint multi-role prompts consistently improved performance over single-role prompting, supporting the value of modeling interactions among argument roles.",
   "Bipartite matching contributed an average Arg-C improvement of about 0.7 percentage points across the three benchmarks.",
   "On WIKIEVENTS roles containing three or at least four arguments, PAIE exceeded EEQA-BART by 9.5 and 26.4 Arg-C F1 points respectively."
  ]
 },
 {
  "paper_id": "2303.16763",
  "title": "Meeting Action Item Detection with Regularized Context Modeling",
  "research_question": "Can regularized modeling of both nearby and non-contiguous meeting context, together with lightweight reuse of different pretrained models, improve sentence-level action-item detection across Chinese and English meetings?",
  "key_findings": [
   "AMC-A substantially expands publicly described action-item resources in the study, containing 424 meetings, 306,846 utterances, and 1,506 labeled actions, with train/dev/test splits of 295, 65, and 64 meetings.",
   "Action-item annotation remained subjective despite detailed guidelines: average pairwise kappa among AMC-A annotators was 0.47, followed by expert review of disagreements.",
   "Adding ordinary local and global context already improved AMC-A StructBERT positive F1 from 67.84 for the focus sentence alone to 69.09 for local plus global context.",
   "On AMC-A, dynamic Context-Drop with local and global context achieved 70.82 positive F1, an absolute gain of 2.98 over the sentence-only baseline and 2.10 over the corresponding R-Drop configuration.",
   "On AMI, the strongest reported Context-Drop configuration was fixed Context-Drop with local context at F1 43.12, compared with 38.67 for sentence-only StructBERT and 42.72 for local-context R-Drop; the configuration that was best on AMC-A was therefore not universally best."
  ]
 },
 {
  "paper_id": "2305.13469",
  "title": "MAILEX: Email Event and Argument Extraction",
  "research_question": "Can event triggers and their structured arguments be extracted reliably from conversational workplace email threads despite shared triggers, long non-entity arguments, and dependencies on preceding messages?",
  "key_findings": [
   "MAILEX provides an authentic workplace-email event extraction benchmark derived from Enron, with event roles that include people or members, dates, times, and action-related information.",
   "End-to-end argument extraction remains difficult: the reported argument-classification F1 is 0.368 for the BERT sequence-labeling system and 0.363 for the BART generation system.",
   "Providing gold triggers substantially improves argument extraction, showing that trigger errors propagate strongly into downstream argument prediction.",
   "Conversation history is useful: removing preceding emails lowers trigger and argument scores, and manual inspection found that 11 of 50 sampled emails required information from an earlier turn.",
   "Shared or discontinuous trigger realizations and long non-named-entity arguments are recurring failure modes for the evaluated models."
  ]
 },
 {
  "paper_id": "2312.05471",
  "title": "Fine-Grained Analysis of Team Collaborative Dialogue",
  "research_question": "Can fine-grained hierarchical dialogue-act annotation and context-aware sequence classification provide explainable measures of team communication and collaboration in long-running workplace Slack conversations?",
  "key_findings": [
   "The taxonomy explicitly distinguishes task assignment, voluntary task ownership, acceptance, requests, proposals, rejection, and counter-assignment, making it directly relevant to extracting action ownership and changes of responsibility from workplace chat. citeturn731643view2",
   "Participant role and project responsibility can change the interpretation of an utterance from a request to an assignment, showing that owner assignment cannot always be inferred from surface wording alone. citeturn246367view0turn731643view4",
   "The annotation scheme can separate multiple acts inside one sentence at clause or fragment granularity, but it also permits annotators to label larger multi-sentence blocks that are subsequently split automatically, so it is not a strict token-level evidence-span annotation scheme. citeturn246367view0turn731643view4",
   "Longer conversational context improves dialogue-act classification relative to classifying isolated messages, with the best reported configuration using a ten-line window plus a one-hour temporal boundary and reaching 0.61 test accuracy versus 0.58 for the one-line setting. citeturn731643view5",
   "Temporal proximity was a better contextual segmentation cue than restricting context to two speakers for this team, while the authors caution that the optimal segmentation strategy is probably team-dependent. citeturn731643view5turn731643view0"
  ]
 },
 {
  "paper_id": "2409.18602",
  "title": "Do LLMs suffer from Multi-Party Hangover? A Diagnostic Approach to Addressee Recognition and Response Selection in Conversations",
  "research_question": "How do textual content, interaction structure, prompt formulation, and structural conversation complexity affect zero-shot LLM performance on response selection and addressee recognition in multi-party conversations?",
  "key_findings": [
   "Addressee recognition benefits strongly from explicit interaction structure: combinations containing the speaker-addressee interaction transcript consistently outperform the text-only conversation baseline.",
   "Response selection depends more strongly on linguistic content: the raw conversation transcript, alone or combined with structure, consistently gives the strongest results across the diagnostic subsets.",
   "Generated conversation summaries preserve substantially more useful information than speaker-description-only representations and can approach the strongest configurations in some higher-participant settings.",
   "Addressee recognition is more sensitive to prompt formulation than response selection, with verbose prompts frequently giving the best addressee results while no consistent verbosity benefit appears for response selection.",
   "As the next speaker's degree centrality increases, addressee-recognition performance generally falls across input combinations, revealing weaknesses that are obscured by aggregate macro accuracy."
  ]
 },
 {
  "paper_id": "2410.03594",
  "title": "Explicit, Implicit, and Scattered: Revisiting Event Extraction to Capture Complex Arguments",
  "research_question": "How should event argument extraction be reformulated and benchmarked when important event arguments may be implicit in context or distributed across multiple discontinuous parts of a discourse rather than appearing as one explicit span?",
  "key_findings": [
   "A majority of annotated event arguments require more than ordinary contiguous-span extraction: 51.2% are implicit and 17.4% are scattered, so 68.6% are either inferred or distributed across the discourse. citeturn326926view0turn568280view2",
   "The paper demonstrates a fundamental limitation of exact evidence-span assumptions: implicit arguments have no directly stated source span, while scattered arguments are assembled from discontinuous information distributed through the document. citeturn568280view1turn945402view3",
   "Because the dataset stores generated natural-text argument values rather than start/end text spans, it supports semantic event reconstruction but does not itself provide strict provenance spans for every extracted argument. citeturn945402view0turn945402view2",
   "Traditional extractive QA performs substantially worse on complex arguments, with mean relaxed-match F1 of 17.13 and recall of only 9.40% for implicit and 13.44% for scattered arguments. citeturn568280view2turn326926view3",
   "Even the strongest evaluated generative system remains far from solving the task: GPT-4 with question-guided prompting reaches mean relaxed-match F1 of 41.98, while its best reported recall for implicit arguments is 36.53% and for scattered arguments is 54.12%. citeturn326926view3turn945402view3"
  ]
 },
 {
  "paper_id": "doi-10-1007-11965152-18",
  "title": "Detecting Action Items in Multi-party Meetings: Annotation and Initial Experiments",
  "research_question": "How should action items in multi-party meetings be annotated and detected so that systems can identify both the relevant dialogue region and properties such as task description, owner, timeframe, and commitment?",
  "key_findings": [
   "The initial flat utterance-level formulation performs poorly, with precision, recall, and F1 below 0.25 on the earlier meeting data and relatively low inter-annotator agreement.",
   "The revised annotation scheme decomposes an action item into task Description, Owner, Timeframe, and Agreement components, explicitly modeling both responsibility and commitment.",
   "Among the component classifiers, Agreement is easiest in the reported experiment with F1 0.40, while Owner is hardest with F1 0.17.",
   "Combining evidence from several nearby utterances can locate action-item regions, but results vary greatly between meetings, with reported per-meeting F1 ranging from 0.00 to 1.00.",
   "The results motivate treating action-item creation as a multi-utterance discourse process rather than as an isolated sentence-classification problem."
  ]
 },
 {
  "paper_id": "doi-10-1109-hicss-2006-528",
  "title": "Using Speech Acts to Categorize Email and Identify Email Genres",
  "research_question": "Can email-specific speech-act and genre categories be reliably annotated and automatically identified from verb-class and email-specific features?",
  "key_findings": [
   "The 30-subcategory annotation scheme achieved Cohen's kappa of 0.89 on 100 emails, indicating high agreement between the two annotators.",
   "The taxonomy explicitly distinguishes information requests, directives that ask another person to act, and commitments or offers to perform an action, but the experimental data merged information requests with directives and did not retain commitments as a standalone classifier class.",
   "Email-specific features alone produced 0.57 precision with Random Forests, outperforming either verb lexicon alone in the overall five-class task.",
   "Combining the 24-class Ballmer-Brennenstuhl verb representation with the email-specific feature set gave the best reported Random Forest result, with precision of 0.63.",
   "Part-of-speech filtering did not improve the best combination: BB plus email features fell from 0.63 without TnT tagging to 0.52 with it."
  ]
 },
 {
  "paper_id": "doi-10-1109-scc-2013-62",
  "title": "Monitoring Commitments in People-Driven Service Engagements",
  "research_question": "Can commitments and their lifecycle operations be automatically identified and tracked from real-world email and chat conversations in people-driven service engagements?",
  "key_findings": [
   "The representation explicitly separates a commitment's debtor, creditor, antecedent, and consequent, making this paper directly relevant to structured responsibility assignment rather than only action-intent classification.",
   "Although the formal model supports conditional commitments, the operational extraction treatment states that most examined email and chat interactions are taken to indicate unconditional commitments, so empirical conditional-antecedent extraction is limited.",
   "The approach derives owner-like roles explicitly: task performer maps to commitment debtor and beneficiary maps to creditor, while conversation roles and parsed linguistic structure help identify those parameters.",
   "Deadline expressions are included as a feature indicating commitment creation or delegation, but the evaluated representation does not separately extract and score an explicit deadline span bound to a particular consequent.",
   "Negation is operationalized primarily as evidence of cancellation: an existing commitment whose matching action appears with a negative dependency such as 'not' can be classified as canceled."
  ]
 },
 {
  "paper_id": "doi-10-1145-1076034-1076094",
  "title": "On the collective classification of email \"speech acts\"",
  "research_question": "Does exploiting the sequential relationship among messages in an email thread improve classification of email acts such as requests and commitments beyond content-only classifiers?",
  "key_findings": [
   "Email acts show exploitable sequential regularities: requests are often followed by delivery-related acts, while commitments are particularly associated with proposals or preceding commitments.",
   "In the preliminary 3F2-to-1F3 experiment, iterative collective classification improved Commit from F1 36.66 and kappa 23.16 to F1 44.06 and kappa 32.42.",
   "The broader Commissive class improved in the same preliminary experiment from F1 77.47 and kappa 35.19 to F1 82.96 and kappa 47.83.",
   "Thread context was not universally beneficial: Deliver degraded in the preliminary experiment from F1 77.08 and kappa 47.47 to F1 71.27 and kappa 35.78.",
   "Across the four test teams, average kappa improvement was statistically significant for the non-delivery-related email acts at p=0.01, but the improvement across all eight acts was not significant at p=0.18."
  ]
 },
 {
  "paper_id": "doi-10-1145-1076034-1076140",
  "title": "Detecting Action-Items in E-mail",
  "research_question": "Does using fine-grained sentence-level action-item annotation improve automatic detection of action-item e-mails compared with document-level annotation, and which text representations work best for the task?",
  "key_findings": [
   "Sentence-level classifiers generally produced better document-level action-item detection than classifiers trained directly on whole e-mails; the advantage was significant for the reported comparisons except SVM F1.",
   "N-gram features improved document-level performance for k-NN and SVM and yielded the strongest document-level representations, while multinomial naive Bayes was hurt by n-gram double-counting.",
   "The best reported document-detection F1 was 0.7790 for the sentence-level n-gram k-NN system, while the best reported document accuracy was 0.8173 for the sentence-level n-gram SVM system.",
   "At sentence granularity, unigrams approached n-gram performance because the short sentence window already captured much of the local lexical-pattern information supplied explicitly by n-grams.",
   "Direct sentence detection achieved accuracy around 0.94-0.96 but substantially lower F1 around 0.62-0.67, indicating that the positive action-item class remained considerably harder than overall accuracy alone suggests."
  ]
 },
 {
  "paper_id": "doi-10-1145-3289600-3290984",
  "title": "Domain Adaptation for Commitment Detection in Email",
  "research_question": "How strongly does email-domain variation degrade sentence-level commitment detection, and can domain-adaptation methods learn commitment models that transfer more reliably between email corpora?",
  "key_findings": [
   "Commitments can be detected reasonably well when training and testing within the same corpus, with word-ngram LR F1 of 0.81 on Avocado and 0.78 on Enron.",
   "Cross-domain transfer without adaptation degraded performance: Avocado-to-Enron F1 fell to 0.73 and Enron-to-Avocado F1 to 0.76, with particularly large AUC deterioration.",
   "A classifier could distinguish Avocado from Enron sentences with F1 of 0.85, empirically demonstrating substantial corpus-specific lexical structure.",
   "Sample-level importance weighting significantly improved transfer in both directions, and the tested feature-level adaptation methods also produced improvements in at least some transfer settings.",
   "The proposed autoencoder benefited from its multiple loss components, and the variant using all available objectives achieved the strongest reported autoencoder performance."
  ]
 },
 {
  "paper_id": "doi-10-1145-3331184-3331260",
  "title": "Context-Aware Intent Identification in Email Conversations",
  "research_question": "Does incorporating the surrounding email-message context improve sentence-level identification of actionable workplace email intents?",
  "key_findings": [
   "Enterprise messages frequently contain multiple intents: 55.2% of the analyzed messages had one intent, 35.8% had two, and 9.0% had three or more.",
   "Providing annotators with the full email body substantially improved Request Information recall, from 52.86 without context to 76.61 with context, while precision changed from 91.51 to 93.45.",
   "The context-sensitive DCRNN significantly outperformed the compared models on all three evaluated intents, reporting F1 values of 73.48 for Schedule Meeting, 80.42 for Promise Action, and 78.37 for Request Information.",
   "Simply concatenating conventional target-sentence and message-context features did not reliably help LR or SVM; the gains came from modeling interactions between the target sentence and relevant parts of context.",
   "Performance generally increased as more surrounding context was supplied, and the full email body produced the best DCRNN results among the tested context windows."
  ]
 },
 {
  "paper_id": "doi-10-1145-3594536-3595162",
  "title": "Computable Contracts by Extracting Obligation Logic Graphs",
  "research_question": "Can contractual obligations and their semantic dependencies be extracted from natural-language contracts into a structured graph representation suitable for downstream conversion into executable code?",
  "key_findings": [
   "The work introduces a structured graph representation intended to preserve contractual obligations and dependencies between obligations rather than extracting isolated entities alone.",
   "Contract-OLG is reported to contain 1,876 contract provisions, 18,597 entities, and 18,170 relationships.",
   "The extraction problem is formulated jointly over entities and relations, which is relevant to tasks that must bind an action or obligation to its associated participants and qualifiers.",
   "The abstract reports a substantial gap between machine systems and human experts, particularly for relation extraction.",
   "The accessible abstract does not establish that the benchmark specifically distinguishes implicit assignees from explicit assignees or evaluates group assignee resolution."
  ]
 },
 {
  "paper_id": "doi-10-1162-coli-a-00110",
  "title": "Semantic Role Labeling of Implicit Arguments for Nominal Predicates",
  "research_question": "Can implicit semantic arguments of nominal predicates be identified and linked to discourse constituents using supervised features derived from lexical, syntactic, semantic, and discourse resources?",
  "key_findings": [
   "Adding manually identified implicit arguments increases semantic-role coverage for the ten studied nominal predicates by roughly 20 absolute percentage points, corresponding to a reported 71% relative increase over NomBank's explicit-role coverage.",
   "The discriminative system achieves 57.9 precision, 44.5 recall, and 50.3 F1 on filled implicit arguments, compared with 28.9 F1 for the baseline.",
   "The oracle reaches 87.6 F1, indicating that a substantial portion of remaining error comes from candidate generation and search-window restrictions rather than only candidate ranking.",
   "Approximately 31% of analyzed system errors arise because the true filler is either absent from the candidate set despite being in the window or lies outside the two-sentence window.",
   "Semantic-role compatibility is among the strongest predictive feature classes, while sentence distance also contributes strongly to filler selection."
  ]
 },
 {
  "paper_id": "doi-10-1162-tacl-a-00006",
  "title": "Event Time Extraction with a Decision Tree of Neural Classifiers",
  "research_question": "Can a hierarchical decision tree of neural classifiers use document-wide temporal evidence to anchor events to precise single-day or multi-day time intervals more accurately than local temporal-relation systems?",
  "key_findings": [
   "Document-wide temporal reasoning is empirically important because the paper reports that a substantial fraction of events require temporal evidence outside the same or adjacent sentence to recover their occurrence time.",
   "The full system achieves 42.0% strict overall accuracy against 56.7% inter-annotator agreement, while relaxed overall accuracy is 84.6%.",
   "For single-day events the model reaches 74.6% exact-match accuracy, a reported 33.1 percentage-point improvement over CAEVO in the paper's conclusion.",
   "Multi-day anchoring remains much harder, with 24.5% strict accuracy and particularly low 28.5% strict accuracy for begin-point extraction.",
   "Removing the text between an event and its temporal expression reduces overall strict accuracy by 9.7 percentage points, supporting explicit modeling of the linguistic relation connecting a time expression to an event."
  ]
 },
 {
  "paper_id": "doi-10-1186-1471-2105-9-s11-s9",
  "title": "The BioScope corpus: biomedical texts annotated for uncertainty, negation and their scopes",
  "research_question": "Can a manually annotated biomedical corpus reliably capture lexical cues and linguistic scopes of negation and uncertainty across heterogeneous clinical and scientific text?",
  "key_findings": [
   "BioScope contains more than 20,000 annotated sentences, and more than 10% of sentences contain at least one negation or uncertainty modifier.",
   "The annotation scheme explicitly links minimal negation or speculation cues to maximal linguistic scope spans, making the resource directly useful for span-level scope-resolution research.",
   "Two independent annotations were reconciled by an expert, and agreement evaluation required exact scope-boundary correspondence for full-scope agreement.",
   "Negation and hedge interpretation cannot be determined from apparent cue words alone because context and syntactic structure can change whether a candidate is genuinely negative or speculative.",
   "Scientific text presents greater cue ambiguity and scope difficulty than the clinical subcorpus; for example, the candidate 'or' was annotated as speculative far less often in scientific abstracts than in clinical text."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-2007-sigdial-1-4",
  "title": "Detecting and Summarizing Action Items in Multi-Party Dialogue",
  "research_question": "Can action items in natural multi-party meetings be detected as structured multi-utterance commitments and summarized into useful task and timeframe information under both manual-transcript and speech-recognition conditions?",
  "key_findings": [
   "The structured detector outperforms the flat detector on manual transcripts, reaching overlap-based F1 of 0.45 versus 0.35 for the flat approach.",
   "Automatic speech recognition reduces action-item detection performance substantially; the structured overlap F1 falls from 0.45 on manual transcripts to 0.36 on 1-best ASR, with word confusion networks recovering only a small amount to 0.37.",
   "Timeframe summarization benefits from semantic and temporal features, with the best reported automatic configuration reaching F1 0.51 compared with 0.31 for a TIMEX-only baseline and 0.39 for an entire-utterance baseline.",
   "Task-description summarization remains difficult: semantic features can raise precision, but the evaluated candidate-ranking systems do not exceed the entire-utterance description baseline in F1.",
   "The action-item annotations are sparse and moderately to substantially reproducible, with only about 1.4% of utterances receiving any action-item class and pairwise kappa values ranging from 0.64 to 0.78."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-2020-acl-main-667",
  "title": "A Two-Step Approach for Implicit Event Argument Detection",
  "research_question": "Can document-level implicit event argument detection be made more tractable and accurate by first detecting argument head words and then expanding those heads to full evidence spans?",
  "key_findings": [
   "When gold argument spans are supplied as candidates, head-word representations produce performance comparable to the earlier span-based RAMS model, supporting the hypothesis that contextualized argument heads can represent much of the useful span information.",
   "For full argument detection with gold event-type constrained decoding, the head-based model reaches 41.8 Span-F1 and 49.7 Head-F1 on the test set, significantly exceeding the corresponding sequence-labeling results of 40.5 and 48.0.",
   "Without type-constrained decoding, the head-based model is also slightly better on average than the sequence-labeling baseline, although the reported significance claim is attached to the type-constrained comparison.",
   "Fine-tuned BERT and explicit indicators marking the trigger/center-sentence context materially improve performance over frozen BERT or an LSTM encoder.",
   "Non-local arguments are much harder than same-sentence arguments; only about 18% of RAMS arguments are non-local, creating a substantial data imbalance in addition to weaker syntactic signals."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-2020-coling-main-164",
  "title": "Lin: Unsupervised Extraction of Tasks from Textual Communication",
  "research_question": "Can specific task actions be extracted from email and chat without supervised task labels by combining dependency syntax with VerbNet semantic information?",
  "key_findings": [
   "Lin achieved 80.42% F1 on the Enron email dataset and 90.45% F1 on the chat dataset.",
   "The combined syntactic-semantic system outperformed its syntax-only and semantics-only variants, showing complementary value from the two information sources.",
   "Lin explicitly filters negated imperatives such as a prohibition from being treated as positive tasks.",
   "The method uses first-person and second-person grammatical information plus dependency relations as a limited representation of the task performer.",
   "Coordination is handled so that multiple distinct task verbs can be extracted from one sentence."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-2023-findings-acl-378",
  "title": "LEDA: a Large-Organization Email-Based Decision-Dialogue-Act Analysis Dataset",
  "research_question": "What dialogue-act taxonomy and empirical patterns can characterize decision-making communication in a large, distributed organization, and how predictable are those acts from email text and conversational context?",
  "key_findings": [
   "The calibrated taxonomy contains explicit decision-relevant categories including ProposeAction and StateDecision while retaining broader information-seeking, information-providing, response, and social categories.",
   "ProposeAction is much more frequent than StateDecision in the annotated corpus, with 2,225 versus 359 labeled instances, indicating substantially more discussion of possible actions than explicit decision statements.",
   "The frequency of ProposeAction remains comparatively stable over the draft life cycle, whereas questions and answers are more common earlier in discussions.",
   "Draft authors and participants with high interaction-graph centrality make more StateDecision acts than their comparison groups; influential participants also propose slightly more actions.",
   "Approximately two thirds of annotated questions appear to remain unanswered, and answer rates vary substantially by participant role, with chairs receiving answers more often than authors."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-d16-1078",
  "title": "Speculation and Negation Scope Detection via Convolutional Neural Networks",
  "research_question": "Can convolutional neural networks using syntactic-path and positional features accurately identify the token-level scope of speculation and negation cues and generalize across biomedical text genres?",
  "key_findings": [
   "On BioScope Abstracts, the strongest reported configuration reaches 85.75% exact-scope accuracy for speculation and 77.14% for negation, outperforming the cited prior result for speculation and ranking second among the compared systems for negation.",
   "Constituency-path features perform better for speculation on Abstracts, whereas dependency-path features perform better for negation, indicating that the two phenomena benefit from different syntactic representations.",
   "The CNN models improve negation right-boundary detection markedly relative to the feature-based baseline, which accounts for an important part of the overall gain.",
   "Models trained on Abstracts transfer comparatively well to Clinical Records, obtaining exact-scope scores of 73.92% for speculation and 89.66% for negation with the best reported configurations.",
   "Cross-domain performance is substantially worse on Full Papers, where the best reported exact-scope scores are 59.82% for speculation and 55.32% for negation."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-n18-1076",
  "title": "Implicit Argument Prediction with Event Knowledge",
  "research_question": "Can distributed event knowledge and entity-salience information improve prediction of implicit arguments whose fillers occur elsewhere in a document?",
  "key_findings": [
   "Combining learned event knowledge with entity-salience features substantially improves argument-cloze accuracy over frequency and simpler event-embedding baselines.",
   "On the shorter OntoNotes setting, the 40-million-example EventComp model with salience reaches 47.75% accuracy, compared with 41.89% without salience and 22.76% for the most-frequent-entity baseline.",
   "On the longer and more entity-dense OntoNotes setting, the 40-million-example EventComp model with salience reaches 27.87% accuracy, outperforming the corresponding model without salience at 21.79%.",
   "For the Gerber-Chai natural implicit-argument task, successive adaptations for deciding whether a role is filled, handling multiple roles, and adding salience raise the 40-million-example EventComp system to 49.6 F1.",
   "The final adapted system approaches the original Gerber-Chai result while exceeding the authors' automatically reproducible Gerber-Chai baseline, suggesting that broad event knowledge can substitute for some manually engineered resources."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-w18-6104",
  "title": "Assigning people to tasks identified in email: The EPA dataset for addressee tagging for detected task intent",
  "research_question": "Given a task already detected in an email thread, how can the people responsible for carrying it out be annotated and predicted from the sender, recipient, and conversational context?",
  "key_findings": [
   "Task ownership in email can be implicit, plural, or absent from the candidate recipients, so recipient metadata and thread context are necessary parts of the assignment problem.",
   "EPA supports multiple responsible people and an explicit no-one outcome rather than assuming every detected task must belong to one recipient.",
   "The released Enron annotations contain 15,649 email-task-recipient tuples covering 5,998 unique emails and 6,300 tasks.",
   "Owner labeling was substantially noisy: recipient-level perfect agreement was 71.07% and Krippendorff's alpha was 0.6123.",
   "The comparable Avocado annotations had higher agreement than Enron, and the authors associate much of the difference with cleaner and more consistent formatting and sentence segmentation."
  ]
 },
 {
  "paper_id": "doi-10-26615-978-954-452-092-2-076",
  "title": "Reading between the Lines: Information Extraction from Industry Requirements",
  "research_question": "Can scope, applicability conditions, and demanded behavior be extracted from authentic industrial requirement sentences when some of that information is implicit in document context?",
  "key_findings": [
   "The final annotated training collection contains 2,147 requirement sentences from 23 authentic DNV industry documents, and contextual annotation yields substantially more scope spans than sentence-only annotation because scope is frequently implicit outside the requirement sentence.",
   "Adding document context produces the largest improvement for scope extraction with RoBERTa, whose average scope scores on the held-out test rise from 0.45 to 0.70 ROUGE-L, 0.43 to 0.62 BLEU-1, and 0.55 to 0.77 embedding similarity.",
   "Condition and demand extraction change comparatively little when context is added to the RoBERTa input, consistent with these components being more often explicit in the requirement sentence itself.",
   "Without contextual input, GPT-3 performs better than RoBERTa on the reported scope and demand text-similarity measures, whereas contextual RoBERTa becomes stronger on scope.",
   "The authors' contextual representation does not produce a comparable scope gain for the GPT-3 few-shot system, suggesting that its prompting setup does not exploit the supplied context as effectively as the supervised sequence-labeling model."
  ]
 },
 {
  "paper_id": "doi-10-3115-1564535-1564540",
  "title": "Shallow Discourse Structure for Action Item Detection",
  "research_question": "Can action items in multi-party meeting transcripts be detected more effectively, while also exposing their task, owner, timeframe, and agreement information, by modeling shallow discourse structure instead of treating all action-item-related utterances as one flat class?",
  "key_findings": [
   "Flat binary action-item classification was weak: the five CALO meetings produced F1 scores between 0.30 and 0.38, and neither higher-order n-grams nor alternative discriminative classifiers improved the reported baseline.",
   "The proposed discourse representation decomposes an action item into task description, timeframe, owner, and agreement, while allowing one utterance to realize multiple components and multiple utterances to realize the same component.",
   "Initial annotation reliability on one relatively complex ISL meeting was substantially higher than the earlier flat action-item agreement cited by the paper, with kappa 0.86 for timeframe, about 0.77 for owner, and 0.73 for agreement and task description.",
   "Subclass detection performance varied greatly: agreement was the strongest subclass at F1 0.40, while owner was weakest at F1 0.17; description and timeframe reached F1 0.29 and 0.26 respectively.",
   "The authors attribute some owner-class difficulty to overlap with other component classes, because owner utterances were especially likely to receive multiple labels."
  ]
 },
 {
  "paper_id": "doi-10-3115-1708376-1708410",
  "title": "Extracting Decisions from Multi-Party Dialogue Using Directed Graphical Models and Semantic Similarity",
  "research_question": "Can directed graphical models improve structured detection of decision-making dialogue, and can semantic similarity improve extraction of concise issue-and-resolution summaries from both manual and ASR meeting transcripts?",
  "key_findings": [
   "The best directed graphical models outperformed the earlier hierarchical SVM for all four decision-dialogue-act classes on both evaluation metrics, with class-level F1 gains reported between 0.04 and 0.19 and p < 0.005.",
   "Using DGM outputs plus simple structural rules improved decision-discussion-region F1 from 0.50 for the hierarchical SVM system to 0.55, with precision 0.39 and recall 0.93 for the DGM-based system.",
   "Explicitly adding dependencies among the DDA classes did not improve Issue, Resolution Proposal, or Resolution Restatement detection; Agreement gained 0.03 under the 40-second metric, but that gain was not statistically significant.",
   "Removing manually annotated dialogue-act features reduced the strongest Issue, Resolution Proposal, and Agreement F1 scores by roughly 0.07 to 0.09, indicating that dialogue-act information was materially useful.",
   "The DGM approach remained usable on one-best ASR output; for some Issue and Resolution Proposal configurations the reported ASR F1 was even higher than on manual transcripts, although the authors partly attribute this to different sparsity caused by segmentation."
  ]
 },
 {
  "paper_id": "manual-01c535c108",
  "title": "Dialogue Act Modeling for Automatic Tagging and Recognition of Conversational Speech",
  "research_question": "Can dialogue acts in spontaneous conversation be automatically recognized by probabilistically combining lexical, prosodic, and dialogue-sequence evidence, while also using dialogue-act information to improve speech recognition?",
  "key_findings": [
   "Using transcribed words, dialogue-act classification reached 71.0% accuracy with a trigram discourse grammar, compared with a 35% chance baseline and approximately 84% human labeling agreement.",
   "Dialogue-sequence context was highly informative: with true words, accuracy rose from 54.3% without a discourse grammar to 71.0% with a trigram model, and with recognized words it rose from 42.8% to 64.8%.",
   "Combining recognized-word evidence with prosody and a bigram discourse grammar yielded 65.0% dialogue-act accuracy, slightly above the 64.3% recognizer-only result.",
   "In balanced focused classifications, adding prosody consistently improved word-only classification for question-versus-statement and agreement-versus-backchannel distinctions, with larger relative value when words came from speech recognition.",
   "The 42-class inventory contains an Action-directive category and an Offers, Options & Commits category, but they account for only about 0.4% and 0.1% of utterances respectively."
  ]
 },
 {
  "paper_id": "manual-0839b98ee7",
  "title": "Can Requests-for-Action and Commitments-to-Act be Reliably Identified in Email Messages?",
  "research_question": "Can human annotators reliably and repeatedly identify the presence and strength of requests for action and commitments to act in workplace email at sentence level well enough to support later automated classification?",
  "key_findings": [
   "Annotators agreed relatively well on whether a sentence contained a Request-for-Action, with three-way kappa 0.78, but agreement on request strength was lower at 0.60.",
   "Commitments-to-Act were substantially harder to annotate: presence achieved three-way kappa 0.54 and strength only 0.37.",
   "Agreement varied with audience type and was highest for single-recipient messages and lowest for closed-group messages, with the effect particularly pronounced for commitments.",
   "Conditional offers were a major systematic ambiguity: sentences containing offers accounted for almost 40% of disagreements about whether a Commitment-to-Act was present.",
   "Implicit requests, especially meeting-related statements, produced recurring disagreement because identifying the obligation can require information from other parts of the message."
  ]
 },
 {
  "paper_id": "manual-1e8332286e",
  "title": "TimeML: Robust Specification of Event and Temporal Expressions in Text",
  "research_question": "How can a general markup language represent events, temporal expressions, temporal ordering, modality, and underspecified temporal information in natural-language text?",
  "key_findings": [
   "TimeML separates event and temporal mentions from the relations among them through four principal structures: EVENT, TIMEX3, SIGNAL, and LINK.",
   "TIMEX3 represents explicit dates, times, durations, and underspecified expressions and supports delayed computation of normalized time values through temporal functions.",
   "TLINK encodes temporal relationships between events or between an event and a time, including before, after, inclusion, simultaneity, beginnings, and endings, making it suitable as a temporal layer for actions associated with dates or deadline-like constraints.",
   "SLINK represents subordination relations such as modality, factuality, counterfactuality, evidentiality, and negation, allowing a temporal-event representation to distinguish asserted events from possible or subordinated ones.",
   "The EVENT taxonomy contains an I_ACTION class whose examples include promise and offer, so commitment-related predicates can be represented as event mentions even though TimeML does not itself define workplace commitment speech acts."
  ]
 },
 {
  "paper_id": "manual-20b8cd2fdd",
  "title": "Requests and Commitments in Email are More Complex Than You Think: Eight Reasons to be Cautious",
  "research_question": "Which recurring phenomena make requests and commitments in real workplace email difficult to annotate or extract reliably, and what annotation principles are needed to handle those phenomena consistently?",
  "key_findings": [
   "More explicit guidance for conditional and indirect phenomena coincided with a large improvement in commitment agreement: three-way commitment kappa increased from 0.54 in the first sentence experiment to 0.74 in the second, while request kappa changed from 0.78 to 0.80.",
   "Message-level annotation yielded still higher agreement, with kappa 0.84 for requests and 0.78 for commitments; the paper links part of this gain to avoiding sentence-level locus ambiguity.",
   "The authors identify eight systematic edge-case categories: locus ambiguity, meetings, pleasantries, requests for inaction, process instructions, attachment-review requests, reported requests and commitments, and third-party commitments that also function as requests.",
   "Several categories cannot be classified reliably from surface wording alone and instead require message context, intended recipient information, or knowledge about whether an obligation is actually imposed.",
   "The same underlying obligation may have multiple direct or indirect sentence realizations, so the authors' high-recall scheme marks every sentence that realizes a request or commitment rather than forcing a single textual locus."
  ]
 },
 {
  "paper_id": "manual-69bc2555ab",
  "title": "Predicate-specific Annotations for Implicit Role Binding: Corpus Annotation, Data Analysis and Evaluation Experiments",
  "research_question": "Can higher-volume, predicate-specific annotation of omitted semantic roles improve the empirical analysis and automatic linking of implicit arguments to discourse antecedents?",
  "key_findings": [
   "The annotation effort yields 630 null-instantiated roles for genuine target-frame readings across 438 verb occurrences, providing substantially denser predicate-specific implicit-role evidence than the sparse SemEval resource motivating the work.",
   "Non-resolvable implicit roles are more common than discourse-resolvable ones in the new annotations, at 61.6% versus 38.4%.",
   "Seventy-eight percent of resolvable implicit roles have their antecedent within a three-sentence window, although the rate differs from previously reported corpora and therefore appears genre- and target-dependent.",
   "For a given predicate, null instantiation tends to concentrate in one or two semantic roles rather than being distributed uniformly across all roles.",
   "Annotation calibration achieves high agreement for resolvability classification and reasonably high agreement for the selected antecedent, including kappa 0.94 and 85.7% antecedent agreement in the two-annotator give calibration."
  ]
 },
 {
  "paper_id": "manual-90280d2776",
  "title": "Decision Detection Using Hierarchical Graphical Models",
  "research_question": "Can hierarchical graphical models improve automatic detection of decision-discussion regions in multi-party meetings by jointly modeling observable utterance features, decision dialogue acts, and higher-level decision regions?",
  "key_findings": [
   "The hierarchical graphical model reports precision 0.69, recall 0.96, and F1 0.80 for decision-region detection, compared with F1 0.55 for the DGM method and 0.50 for the hierarchical SVM in the paper's controlled comparison.",
   "The improvement is attributed to jointly modeling dependencies between high-level decision regions, mid-level decision dialogue acts, and observable utterance features rather than detecting decision-related utterances independently.",
   "The annotation scheme distinguishes issue, resolution proposal, resolution restatement, and agreement utterances, thereby representing stages of collective decision formation rather than only a binary decision/non-decision label.",
   "An utterance can belong to more than one decision-dialogue-act class, and multiple utterances of the same class can contribute to one decision discussion.",
   "The experiment relies on manual transcripts and manually annotated dialogue-act information; it therefore does not establish equivalent performance on raw enterprise chat or automatically transcribed meetings."
  ]
 },
 {
  "paper_id": "manual-cd3fa58e4c",
  "title": "Detecting Emails Containing Requests for Action",
  "research_question": "Can emails containing requests for action be detected accurately at message level, and does removing quoted and other non-author message zones improve classification?",
  "key_findings": [
   "Message zoning substantially improves request detection, raising accuracy from 72.28% without zoning to 83.76% with zoning.",
   "With zoning, request-class F1 reaches 0.843 and weighted overall F1 reaches 0.838.",
   "The improvement from zoning is statistically significant across the reported classification metrics and corresponds to more than a 41% reduction in classification error.",
   "Lexical n-gram features provide most of the predictive power, while zoning makes even small lexical feature sets substantially more effective.",
   "Important remaining errors include implicit requests, request-like spam or marketing text, requests embedded in ignored zones, zoning mistakes, pleasantries, and requests associated with attachments."
  ]
 },
 {
  "paper_id": "manual-d19b0f6f1e",
  "title": "The nature of requests and commitments in email messages",
  "research_question": "How can requests and commitments in workplace email be defined at the utterance level robustly enough to support consistent annotation and subsequent automated detection?",
  "key_findings": [
   "More explicit annotation guidance substantially improved agreement for commitments: three-way kappa rose from 0.54 in the first experiment to 0.74 in the second, while request agreement rose from 0.78 to 0.80.",
   "Conditional commitments and implicit requests were major sources of disagreement in the initial annotation experiment, and better treatment of conditional commitments accounted for much of the later agreement improvement.",
   "The final representation separates the underlying act from its linguistic realization: a request is represented by an action, requestor, requestee, and optional condition, while a commitment contains an action, committor, committee, and optional condition.",
   "Requests are treated broadly as actionable obligations for the recipient, including requests for physical action as well as questions that require an informational response.",
   "Conditionality is modeled explicitly because execution or scheduling of an action may depend on a stated condition that can occur in the same utterance or elsewhere in the email."
  ]
 },
 {
  "paper_id": "manual-e6bb5aee88",
  "title": "Extraction de tâches dans les e-mails : une approche fondée sur les rôles sémantiques",
  "research_question": "Can a semantic-role-based symbolic system detect and structure action and information requests in professional French emails so that the action predicate and participants such as agent, theme, recipient, and temporal context are explicitly represented?",
  "key_findings": [
   "The proposed representation structures a task around a predicate and semantic arguments such as Agent, Theme/Patient, Recipient, Time, Location, Purpose, Manner, Instrument, Cause, and Consequence, making it substantially closer to structured action-argument extraction than simple email classification.",
   "On the uncorrected test emails, the system reports F1 scores of 0.91 for detecting messages containing requests, 0.83 for action requests, 0.93 for information requests, and 0.84 for semantic-role extraction.",
   "After manual spelling correction, reported F1 rises to 0.94 for request-containing messages, 0.88 for action requests, 0.94 for information requests, and 0.89 for semantic roles, indicating notable sensitivity to noisy email text.",
   "The action-request filter requires an Agent corresponding to the email recipient and uses imperative, semi-auxiliary, or complement-clause constructions while excluding predicates governed by conjectural verbs such as think, presume, hope, or believe.",
   "The task definition explicitly allows negative requested actions and includes a Time semantic role, but the evaluation does not separately measure negation attachment or deadline-to-action attachment accuracy."
  ]
 },
 {
  "paper_id": "manual-ee40d588e3",
  "title": "*SEM 2012 Shared Task: Resolving the Scope and Focus of Negation",
  "research_question": "How accurately can computational systems identify negation cues, their scope, negated events or properties, and the focus of negation under standardized shared-task conditions?",
  "key_findings": [
   "Negation cue detection is substantially easier than complete resolution of cue, scope, and negated event together.",
   "The best closed-track official global score for complete negation resolution was 57.63 F1, while individual cue identification reached above 92 F1.",
   "Machine-learning systems generally outperformed the rule-based system on the complete Task 1 evaluation.",
   "Only one team participated in focus detection, and its best reported focus score was 58.40 F1.",
   "Scope scores are sensitive to how partial matches are counted, although the alternative evaluation reported by the organizers did not change the system ranking."
  ]
 },
 {
  "paper_id": "manual-fde6beef40",
  "title": "Classifying Action Items for Semantic Email",
  "research_question": "Can action items in email be automatically classified into useful semantic categories using a computationally tractable speech-act model and linguistic rules?",
  "key_findings": [
   "The proposed model represents action items through action, object, and subject dimensions and yields 22 basic action-item combinations.",
   "The implemented classifier uses modality, verb category, tense, negation, and semantic-role information, with additional rules for phenomena such as conditional constructions.",
   "An earlier human annotation exercise over the 22-category scheme achieved inter-annotator agreement of 0.811, indicating substantial but imperfect agreement on the task.",
   "In the reported evaluation, the rule-based classifier achieved precision 0.56, recall 0.60, and F1 0.58.",
   "The authors conclude that the classifier is not reliable enough for unattended automatic annotation and is better used to suggest candidate annotations for user review and correction."
  ]
 }
]

Open gaps carried over from round 3 (the corpus above
includes the papers of every round so far):
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

Decide for each whether this corpus now resolves it. Never drop or
downgrade an unresolved gap: it stays open, with the same id, until the
literature closes it.

Produce two blocks.

Block 1, `synthesis.json`, one JSON object with these fields:
- topic: string
- paper_count: integer
- executive_summary: 100-150 words
- themes: list of strings
- findings: 5-12 items {statement, confidence: HIGH|MEDIUM|LOW,
  evidence: [{paper_id, section, quote (at most one sentence, optional)}]}
- contradictions: list of {topic, papers: [paper_id...], note}
- gaps: list of {description, classification: ACADEMIC|ENGINEERING|OUT_OF_SCOPE,
  priority: HIGH|MEDIUM|LOW, suggested_query (ACADEMIC only)}
- actionable_insights: list of strings
- confidence_summary: string
- limitations: list of strings
- gap_status (rounds after the first): one entry per prior gap
  {id, status: resolved|open, note, evidence: [paper_id...]}; a gap is
  `resolved` only when papers in this corpus answer it, otherwise it stays
  `open` and must also appear again in `gaps` with the same id

JSON schema (additional fields allowed):
{
 "$schema": "http://json-schema.org/draft-07/schema#",
 "title": "SynthesisReport",
 "description": "Schema for the cross-paper synthesis report produced by the summarize stage.",
 "type": "object",
 "required": [
  "topic",
  "findings",
  "gaps"
 ],
 "properties": {
  "topic": {
   "type": "string",
   "minLength": 1
  },
  "run_id": {
   "type": "string"
  },
  "generated_at": {
   "type": "string"
  },
  "findings": {
   "type": "array",
   "items": {
    "type": "object",
    "required": [
     "statement",
     "confidence",
     "evidence"
    ],
    "properties": {
     "statement": {
      "type": "string",
      "minLength": 1
     },
     "confidence": {
      "type": "string",
      "enum": [
       "HIGH",
       "MEDIUM",
       "LOW"
      ]
     },
     "evidence": {
      "type": "array",
      "items": {
       "type": "object",
       "required": [
        "paper_id"
       ],
       "properties": {
        "paper_id": {
         "type": "string"
        },
        "section": {
         "type": "string"
        },
        "quote": {
         "type": "string"
        }
       }
      },
      "minItems": 1
     }
    }
   }
  },
  "gaps": {
   "type": "array",
   "items": {
    "type": "object",
    "required": [
     "description"
    ],
    "properties": {
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
     "suggested_query": {
      "type": "string"
     }
    }
   }
  },
  "themes": {
   "type": "array",
   "items": {
    "type": "string"
   }
  },
  "paper_count": {
   "type": "integer",
   "minimum": 0
  }
 },
 "additionalProperties": true
}

Block 2, `synthesis.md`: the same content as a Markdown narrative with the
sections Executive Summary, Themes, Contradictions, Open Gaps, Actionable
Insights, Confidence Summary, Limitations. Cite papers as [paper_id].

Reply format:
===BEGIN synthesis.json===
<content>
===END synthesis.json===
===BEGIN synthesis.md===
<content>
===END synthesis.md===
