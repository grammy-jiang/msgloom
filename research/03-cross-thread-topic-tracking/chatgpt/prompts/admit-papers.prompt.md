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

# Task: admission gate for 25 screened candidate(s)

Research topic: **Direct enterprise email/chat studies of longitudinal cross-thread conversation or work-item linking, especially evidence for concrete business-event identity and for partial, evolving, subevent, or non-transitive continuity relations in organizational workflows.**

Decide which of these candidates enters the reading round. Admit a paper only
when it materially strengthens one of the research streams below, and the
abstract shows that, not merely shared vocabulary. A paper count is never a
reason to admit: admitting six of twenty is a valid answer, and so is
admitting none. Rejecting a paper here costs little; reading a paper that
cannot strengthen a stream costs a reading slot that a better paper needed.

Research streams:
- F1 [DIRECT] Enterprise cross-thread and cross-channel work-item identity: Direct studies that decide whether independent workplace emails, chat messages, conversations, attachments, or channels concern the same concrete task, case, issue, business matter, or process instance over time.
- F2 [DIRECT] Process-mining event correlation and case identification: Methods that infer which uncorrelated business events belong to the same process instance or case, including case correlation, case-notion discovery, process-instance identification, and event-to-case assignment.
- F3 [TRANSFER] Cross-document event coreference and same-event identity: Determining whether event mentions distributed across independent documents refer to the same underlying event and clustering coreferent mentions.
- F4 [TRANSFER] Partial, quasi-, subevent, membership, and non-identity event relations: Work that distinguishes strict event identity from partial identity, quasi-identity, subevent, membership, overlap, or other related-but-not-identical event relations.
- F5 [TRANSFER] Topic Detection and Tracking, story-link, and new-event detection: Streaming text tasks that link incoming stories to an existing event/topic or decide that they introduce a new event, including first-story detection and topic tracking.
- F6 [TRANSFER] Incremental, online, and streaming clustering with cluster evolution: Sequential clustering methods that assign new observations, create clusters, and sometimes merge, split, retire, or revise clusters as evidence changes.
- F7 [TRANSFER] Entity resolution, record linkage, and incremental identity resolution: Matching observations or records to persistent identities, including probabilistic match/non-match decisions, uncertain matches, incremental updates, and collective resolution.
- F8 [TRANSFER] Object-centric and artifact-centric process representations: Workflow representations in which events can relate to multiple business objects or artifacts rather than being forced into one flat case sequence.
- F9 [DIRECT] Enterprise email/chat longitudinal task, case, and issue tracking: Studies in real organizational communication that explicitly track tasks, issues, cases, activities, or work items across multiple messages or conversations over time.
- F10 [TRANSFER] Selective prediction, abstention, and calibration under distribution shift: Methods that allow prediction systems to abstain or reject uncertain cases and that study confidence calibration under changing or shifted data distributions.
- F11 [TRANSFER] Retrieval and global-context evidence for cross-document identity: Methods that retrieve candidate mentions, documents, clusters, or historical context and use the additional evidence to improve event/coreference or identity decisions.
- F12 [TRANSFER] Identity revision, cluster merge/split, and provenance-preserving correction: Incremental resolution and clustering work that revises prior assignments, performs merge or split operations, or maintains lineage/history as clusters evolve.

Open gaps this round must close (a paper that speaks to one of these
is worth admitting even when its topic wording is unusual):
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
Decisions:
- ADMIT — name the stream and why the abstract shows the contribution.
- REJECT — name the reason: topic words match but the capability does not,
  the evidence duplicates a paper already admitted, or the claim is out of
  scope.
- PENDING — the abstract cannot settle it; say what would.

`identity: UNCHECKED` means the host could not confirm the paper's identifier
with the provider. That is not proof the paper is wrong, but prefer a
VERIFIED paper when the two are otherwise equal, and say so in the reason.


## Project context you must work within

This is the project's own description of the problem, its boundaries,
and the distinctions it needs preserved. It governs what counts as
relevant; the academic task names alone do not.

# Topic 03 context — Cross-thread Topic identity and incremental continuity

## Why this Topic exists

After Topic 02 identifies work-matter evidence inside supplied messages/groups, msgloom still needs to answer a harder longitudinal question: **does new evidence continue an existing concrete work matter, start a new work matter, or remain uncertain?**

Real work does not respect email subjects or thread boundaries. A procurement matter can move from one email chain to another, then into Teams, then return under a new title. Conversely, two messages with the same customer, project name, participants, or subject can still be distinct matters. Wrong merging can hide a due item; wrong splitting can fragment history and obscure state.

This Topic is therefore the owner of **stable Topic identity across independent Groups and sources**, especially incrementally over time.

## Direct handoff from earlier Topics

Topic 01 established that conversation/group relationships are evidence but **not Topic identity**. Topic 02 explicitly handed off its G10 problem — concrete work-matter identity and Topic count — to Topic 03. Those handoffs are part of this Topic's starting context, not new gaps to rediscover.

## Core research object

Given a new candidate matter/span/group and a set of existing Topic identities, decide among:

```text
CONTINUE existing Topic
NEW Topic
UNCERTAIN relationship (keep separate)
MERGE correction
SPLIT correction
```

Identity must be stable and independent of generated titles. Corrections create new assessments and links; they do not rewrite source history.

## Product and phase relevance

This Topic straddles phases:

- Phase 1 can link a continuation only with explicit supporting evidence and otherwise must keep matters separate with uncertainty.
- Phase 2 A4 explicitly owns Topic relationships across **independent groups and sources** and can investigate additional evidence.

Therefore research should distinguish what can safely be done from supplied content in Phase 1 from what requires Phase 2 investigation.

## Relationships to other Topics

| Topic | Relationship |
| --- | --- |
| 01 | Supplies conversation/group ancestry and source provenance; these are features/evidence, not identity decisions. |
| 02 | Supplies within-message candidate Topic spans/memberships. Topic 03 decides cross-message/group continuity. |
| 04 | Reference resolution may provide evidence that a new message refers to a prior matter, but reference evidence alone may remain ambiguous. |
| 05 | Actions/commitments can be strong identity evidence when owner/object/target match, but must not force a merge by themselves. |
| 06 | State and temporal compatibility help distinguish continuation from a similar but different matter and help detect merge/split errors. |
| 07 | When identity is uncertain, Topic 07 may retrieve bounded historical evidence to resolve the relationship in Phase 2. |
| 09 | Briefing needs stable identities to avoid duplicate or missing Topic entries. |
| 10 | Topic 10 evaluates confidence/calibration and relationship evidence quality; Topic 03 owns the domain decision. |

## Key conceptual distinctions

- Group/conversation membership ≠ Topic identity.
- Same subject/customer/project ≠ same work matter.
- Semantic similarity ≠ continuation.
- One new message may continue multiple existing matters through different spans.
- A Topic label/title is presentation, not identity.
- “No confident match” ≠ proven new Topic; abstention/uncertainty may be correct.
- Online assignment decisions must support later correction when new evidence arrives.

## Research questions to emphasize

- What evidence establishes same-event/same-work-matter identity across documents?
- How do event/entity coreference methods distinguish identity from similarity?
- How should online clustering create a new cluster versus attach to an existing one?
- How are novelty/new-event detection and open-set rejection evaluated?
- How can merge/split corrections preserve stable IDs and history?
- How should temporal, participant, object, action, reference, and source-structure evidence be combined without over-merging?
- Which benchmarks actually test cross-document identity rather than topical similarity?
- How should uncertain cross-source relationships remain separate and visible?

## High-value academic terminology

Search across several research communities:

- cross-document event coreference (CDCR); event coreference resolution;
- cross-document entity coreference; entity resolution; entity matching; record linkage;
- event identity; event linking; event clustering;
- topic detection and tracking (TDT); topic tracking; new event detection;
- online clustering; incremental clustering; streaming clustering;
- novelty detection; open-set recognition/classification; reject option;
- cluster assignment with abstention; unknown-class detection;
- dynamic clustering; cluster merge/split; incremental entity resolution;
- temporal/event consistency; event evolution; storyline/event tracking;
- cross-source information linking; cross-channel conversation linking;
- task/work-item identity (when available in enterprise/workflow literature).

## Query families

- `"cross-document event coreference" identity`
- `"event coreference" cross-document clustering`
- `"new event detection" topic tracking`
- `"online clustering" event stream novelty`
- `"incremental clustering" entity resolution`
- `"open set" event classification clustering`
- `"cluster assignment" abstention streaming text`
- `"topic detection and tracking" new event`
- `work item identity email cross thread`
- `business email cross-thread topic tracking`
- `cross-source work matter identity`

Use snowballing aggressively because useful terminology may come from event coreference, entity resolution, TDT, streaming clustering, or case/workflow management rather than email research.

## False friends / exclusions

Be cautious with:

- document-level semantic similarity or embeddings without identity labels;
- ordinary topic modeling where “topic” means latent word distribution;
- thread/conversation reconstruction (Topic 01);
- within-document segmentation (Topic 02);
- duplicate detection, which is narrower than work-matter identity;
- recommendation-session/user-interest tracking unless identity semantics match;
- clustering results that force every item into a cluster and cannot abstain/create a new Topic.

## Gap-evaluation guidance

The highest-value gaps are those that affect **false merges, false splits, new-Topic detection, stable identity, or correction**. A small precision gain on similarity clustering is less valuable than evidence about when to abstain. Evaluate false merges especially harshly because they can cause one matter to disappear from reports. Separate Phase 1 supplied-evidence decisions from Phase 2 evidence-seeking decisions.

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

Candidates:
- paper_id `doi-10-1145-1242572-1242580` [identity: UNCHECKED] Learning information intent via observation (2007, Proceedings of the 16th International Conference on World Wide Web (WWW 2007))
    Studies organizational request messages in which workers ask assistants to perform information-system tasks. The system learns the information intent associated with a request by observing how an expert carries out the corresponding operation, providing direct evidence for mapping workplace messages to concrete tasks.
- paper_id `doi-10-1145-1111449-1111472` [identity: UNCHECKED] Linking messages and form requests (2006, Proceedings of the 11th International Conference on Intelligent User Interfaces (IUI 2006))
    Studies an organizational setting in which employees describe tasks by email and instant message to specialists who may need follow-up clarification before completing structured forms. A prototype reads communication and assists with the associated task, providing direct evidence of message-to-business-task association across interactive exchanges.
- paper_id `doi-10-18653-v1-2025-acl-long-1134` [identity: UNCHECKED] Employing Discourse Coherence Enhancement to Improve Cross-Document Event and Entity Coreference Resolution (2025, Proceedings of the 63rd Annual Meeting of the Association for Computational Linguistics)
    Addresses cross-document coreference where relevant mentions lack a shared coherent document context. The method retrieves additional coherent text, inserts it between mention contexts, and uses the augmented context for event and entity identity decisions, allowing direct evaluation of whether retrieved context improves coreference.
- paper_id `2211.07342` [identity: VERIFIED] MAVEN-ERE: A Unified Large-scale Dataset for Event Coreference, Temporal, Causal, and Subevent Relation Extraction (2022, Proceedings of the 2022 Conference on Empirical Methods in Natural Language Processing)
    Introduces a unified event-relation dataset with human annotation of event coreference, temporal, causal, and subevent relations. By representing identity and subevent membership as distinct relations within the same event structures, it provides transferable evidence for modeling continuity relations that are not all equivalence relations.
- paper_id `2607.26384` [identity: VERIFIED] An ER-Model-Based Framework for Case Notion Selection in Object-Centric Processes (2026)
    Proposes deriving process cases from an entity-relationship schema rather than assuming a single pre-existing case identifier. Cases are constructed from connected components of primary and secondary business entities, making explicit how relational structure induces process-instance identity while avoiding unrestricted resource-based linking.
- paper_id `2608.01401` [identity: VERIFIED] Designing Ambiguity-Aware Clerical Review: A Stratified Sampling Framework for Record Linkage and Deduplication (2026)
    Studies how limited human-review budgets should be allocated to uncertain candidate record pairs in record linkage. The framework stratifies candidates using match weights, comparison patterns, ambiguity, and demographic groups so that clerical adjudication covers the uncertainty structure rather than simply reviewing the closest-to-threshold pairs.
- paper_id `doi-10-1109-tbdata-2022-3204207` [identity: UNCHECKED] Tracking the Evolution of Clusters in Social Media Streams (2023, IEEE Transactions on Big Data)
    Studies longitudinal cluster evolution in high-volume social-media streams. The framework explicitly tracks cluster emergence, disappearance, adjustment, splitting, and merging, making it useful as transfer evidence for histories in which a persistent grouping can change structure over time.
- paper_id `doi-10-3390-industries1010003` [identity: UNCHECKED] StableID: An Iterative Graph-Based Framework for Persistent Entity Identification in Evolving Industrial Data Systems (2026, Industries)
    Addresses persistent entity identifiers in evolving industrial data where newly discovered links can merge previously separate graph components and destabilize identifiers. The framework incorporates historical identity information, applies dominance rules during component merges, and aims to preserve stable and auditable identity over time.
- paper_id `doi-10-1145-3297280-3297534` [identity: UNCHECKED] On the elicitation and annotation of business activities based on emails (2019, Proceedings of the 34th ACM/SIGAPP Symposium on Applied Computing (SAC 2019))
    Studies discovery and annotation of business-process activities from email. Beyond activity labels, it extracts metadata such as participant roles, attachment types, and link domains, providing evidence about observable signals associated with organizational work activities.
- paper_id `doi-10-1016-j-procs-2026-02-155` [identity: UNCHECKED] Surrogate Case Identifier Rules for Construction Site Hoists (2026, Procedia Computer Science)
    Examines how to construct surrogate process case identifiers when sensor-generated operational events have no native case ID. Multiple candidate case-identification rules are evaluated on a month-long construction-hoist event log, showing that the choice of identity rule can materially alter the resulting process structure.
- paper_id `doi-10-1016-j-knosys-2017-09-039` [identity: UNCHECKED] Adaptive online event detection in news streams (2017, Knowledge-Based Systems)
    Studies online clustering of news reports that describe the same event. The method adapts event clusters as a stream evolves and includes mechanisms for event merging and noise handling, providing transfer evidence for incremental identity assignment with changing event representations.
- paper_id `doi-10-3390-math11122691` [identity: UNCHECKED] Object-Centric Process Mining: Unraveling the Fabric of Real Processes (2023, Mathematics)
    Presents object-centric process mining as an alternative to forcing each event into one conventional case. Events may involve any number of business objects of different types, allowing explicit representation of many-to-many event-object relations and the convergence and divergence patterns that result.
- paper_id `doi-10-1515-jos-2018-0003` [identity: UNCHECKED] Design-Based Estimation with Record-Linked Administrative Files and a Clerical Review Sample (2018, Journal of Official Statistics)
    Addresses record linkage when automated links contain both erroneous and missing matches. It uses a probability sample subjected to clerical review to establish match status, providing transfer evidence for explicit adjudication of uncertain identity decisions rather than forcing every candidate into match or non-match automatically.
- paper_id `2406.15990` [identity: VERIFIED] Enhancing Cross-Document Event Coreference Resolution by Discourse Structure and Semantic Information (2024, LREC-COLING 2024)
    Improves cross-document event coreference by combining semantic event arguments with document-level discourse structure. Features include agents, patients, times, and locations, while rhetorical structure trees and cross-document lexical chains provide longer-range evidence before mention-pair scoring and clustering.
- paper_id `doi-10-1007-978-3-030-30284-9-5` [identity: UNCHECKED] Email Business Activities Extraction and Annotation (2019, Information Search, Integration, and Personalization)
    Treats organizational emails as resources associated with business activities. It discovers process activities, clusters activity types, and extracts metadata describing those activities, with validation on a public email dataset.
- paper_id `2405.05160` [identity: VERIFIED] Selective Classification Under Distribution Shifts (2024, Transactions on Machine Learning Research)
    Studies classifiers that can abstain on likely errors when deployment distributions differ from training data. It formulates selective classification under label shift, covariate shift, and out-of-distribution inputs and evaluates confidence-score designs intended to preserve useful risk-coverage behavior under such changes.
- paper_id `doi-10-1016-j-ins-2016-03-002` [identity: UNCHECKED] Assessing e-mail intent and tasks in e-mail messages (2016, Information Sciences)
    Studies work tasks and communicative intent in corporate email using Enron and Avocado data. It develops a task taxonomy and manual annotations and examines how work-related email conversations and tasks develop over time, while also evaluating automatic classification across corporate collections.
- paper_id `doi-10-18653-v1-2025-uncertainlp-main-2` [identity: UNCHECKED] Phases of Uncertainty: Confidence–Calibration Dynamics in Language Model Training (2025, Proceedings of the Workshop on Uncertainty-Aware NLP)
    Studies how confidence and calibration evolve during language-model training, including behavior under distribution shift. It reports that increasing confidence in later training need not imply improved calibration and motivates calibration strategies that account for changing uncertainty characteristics.
- paper_id `doi-10-1016-j-knosys-2016-07-032` [identity: UNCHECKED] Cross-document event ordering through temporal, lexical and distributional knowledge (2016, Knowledge-Based Systems)
    Studies cross-document event ordering while explicitly addressing event coreference. Event mentions are treated as coreferential when temporal compatibility and semantic compatibility support the same-event interpretation, using lexical and distributional semantic knowledge together with temporal information.
- paper_id `doi-10-1145-1111449-1111471` [identity: UNCHECKED] Automatically classifying emails into activities (2006, Proceedings of the 11th International Conference on Intelligent User Interfaces (IUI 2006))
    Studies activity-centered email management and the problem of recognizing whether an incoming email belongs to an ongoing user activity. It evaluates reply-thread and Naive Bayes baselines alongside similarity methods using participants and message content, and combines multiple signals for activity assignment.
- paper_id `doi-10-1007-978-3-031-82225-4-30` [identity: UNCHECKED] A Framework for Advanced Case Notions in Object-Centric Process Mining (2025, Process Mining Workshops)
    Studies how sets of related objects in an object-centric event log can be converted into meaningful process executions or cases. It provides a framework for defining, measuring, and optimizing case notions while explicitly considering activity-object relations.
- paper_id `doi-10-1145-1180875-1180942` [identity: UNCHECKED] Going with the flow: email awareness and task management (2006, Proceedings of the 2006 20th Anniversary Conference on Computer Supported Cooperative Work (CSCW 2006))
    Uses workplace studies to examine how people interleave email with day-to-day ongoing work and maintain awareness of current task focus. It develops a workflow-oriented account of email use and derives design recommendations for supporting task management.
- paper_id `2206.10009` [identity: VERIFIED] Event-Case Correlation for Process Mining using Probabilistic Optimization (2023, Information Systems)
    Studies recovery of missing case identifiers from timestamped business-process events. It combines a process model, event attributes, constraints, and probabilistic optimization to assign events to cases, and evaluates multiple similarity measures on real-life datasets.
- paper_id `doi-10-1145-290941-290954` [identity: UNCHECKED] On-Line New Event Detection and Tracking (1998, Proceedings of the 21st Annual International ACM SIGIR Conference on Research and Development in Information Retrieval)
    Studies strict online decisions about whether each incoming news story belongs to an already observed event or represents a new event. It combines single-pass clustering with threshold-based new-event detection and evaluates adaptive tracking intended to follow events as they evolve.
- paper_id `doi-10-18653-v1-2024-findings-emnlp-725` [identity: UNCHECKED] Distance-aware Calibration for Pre-trained Language Models (2024, Findings of the Association for Computational Linguistics: EMNLP 2024)
    Introduces a post-hoc calibration method for pretrained language models that accounts for the distance between test examples and the in-domain training distribution. The method targets overconfidence on shifted and out-of-distribution text and improves calibration and out-of-distribution detection.

JSON schema:
{
 "$schema": "http://json-schema.org/draft-07/schema#",
 "title": "PaperAdmission",
 "description": "Per-candidate admission decision. A paper enters the reading round only when it materially strengthens an authorized research stream; a paper count is never a reason to admit.",
 "type": "object",
 "required": [
  "decisions"
 ],
 "properties": {
  "round": {
   "type": "integer",
   "minimum": 1
  },
  "streams": {
   "type": "array",
   "description": "The authorized research streams this round admits against.",
   "items": {
    "type": "object",
    "required": [
     "id",
     "description"
    ],
    "properties": {
     "id": {
      "type": "string",
      "minLength": 1
     },
     "description": {
      "type": "string",
      "minLength": 1
     }
    }
   }
  },
  "decisions": {
   "type": "array",
   "minItems": 1,
   "items": {
    "type": "object",
    "required": [
     "paper_id",
     "decision",
     "reason"
    ],
    "properties": {
     "paper_id": {
      "type": "string",
      "minLength": 1
     },
     "decision": {
      "type": "string",
      "enum": [
       "ADMIT",
       "REJECT",
       "PENDING"
      ]
     },
     "reason": {
      "type": "string",
      "minLength": 1
     },
     "stream_id": {
      "type": "string",
      "description": "Required for ADMIT: the stream this paper materially strengthens."
     },
     "role": {
      "type": "string",
      "enum": [
       "DIRECT",
       "TRANSFER"
      ]
     },
     "confidence": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0
     }
    }
   }
  },
  "notes": {
   "type": "string"
  }
 },
 "additionalProperties": true
}

Reply with one block containing one JSON object with a `decisions` array
covering every paper_id above, and a `streams` array describing the streams
you admitted against.
===BEGIN admission.json===
<content>
===END admission.json===
