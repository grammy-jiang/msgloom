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

Research topic: **Direct enterprise email/chat studies of longitudinal cross-thread conversation or work-item linking, especially evidence for concrete business-event identity and for partial, evolving, subevent, or non-transitive continuity relations in organizational workflows.**

Must-have terms: direct, enterprise, email/chat
Nice-to-have terms: studies, longitudinal, cross-thread, conversation, work-item, linking,, especially, evidence, concrete, business-event, identity, partial,, evolving,, subevent,, non-transitive, continuity, relations, organizational, workflows.
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
    ("work item identity" OR "work-item identity" OR "work matter" OR "business matter" OR "case identity") AND (email OR "enterprise chat" OR "workplace communication") AND (longitudinal OR "cross-thread" OR "cross-conversation" OR "cross-channel")
    ("task continuity" OR "case continuity" OR "issue continuity" OR "work item linking") AND (email OR messaging OR "enterprise communication") AND (thread OR conversation OR channel)
    ("cross-channel" OR "cross-source") AND (email AND chat) AND ("task tracking" OR "case tracking" OR "work item" OR "business process")
    ("same case" OR "same task" OR "same issue" OR "same work item") AND (email OR "workplace chat" OR "enterprise messaging") AND (linking OR classification OR correlation)
    ("Outlook" OR "business email" OR "enterprise email") AND ("work item" OR case OR task OR issue) AND (linking OR continuity OR correlation) AND (longitudinal OR "cross-thread")
- F2 [DIRECT]
    ("event correlation" OR "case correlation" OR "case identification" OR "case notion discovery") AND ("process mining" OR workflow) AND (enterprise OR business)
    ("process instance identification" OR "process instance discovery" OR "event-to-case" OR "case assignment") AND ("process mining" OR "business process")
    ("uncorrelated event log" OR "uncorrelated events") AND (correlation OR "case identification" OR "case notion") AND "process mining"
    ("event correlation" OR "case correlation") AND (email OR communication OR message OR document) AND (workflow OR "business process")
    ("case notion" OR "case identification") AND (temporal OR resource OR object OR attribute OR state) AND "process mining"
- F3 [TRANSFER]
    "cross-document event coreference" AND (identity OR "same event" OR clustering)
    "cross-document event coreference resolution" AND (time OR temporal OR participant OR argument OR location)
    ("event coreference" AND "cross-document") AND (identity OR nonidentity OR "identity criteria")
    ("same-event" OR "same event") AND (detection OR classification) AND ("cross-document" OR documents) AND event
    "cross-document event coreference" AND (arguments OR participants OR temporal OR location OR context) AND (features OR evidence)
- F4 [TRANSFER]
    ("event identity" OR "event coreference") AND ("partial identity" OR "partial coreference" OR "quasi-identity")
    ("event identity" OR "event coreference") AND (subevent OR "sub-event" OR membership OR overlap)
    ("non-transitive" OR nontransitive) AND ("event coreference" OR "event identity" OR "event relation")
    ("event relation" OR "event relations") AND (subevent OR membership OR overlap) AND (identity OR coreference)
    ("event evolution" OR "evolving event") AND (identity OR coreference OR continuation) AND (subevent OR state OR relation)
- F5 [TRANSFER]
    ("topic detection and tracking" OR TDT) AND ("new event detection" OR "story link detection")
    ("online new event detection" OR "first story detection") AND (threshold OR similarity OR clustering)
    "story link detection" AND (same OR link OR topic OR event) AND evaluation
    ("new event detection" OR "first story detection") AND ("new cluster" OR "cluster assignment" OR threshold) AND streaming
    ("topic tracking" AND "new event") AND (false alarm OR miss OR detection cost)
- F6 [TRANSFER]
    ("incremental clustering" OR "online clustering") AND text AND ("new cluster" OR "cluster assignment")
    ("streaming clustering" OR "dynamic clustering") AND text AND (merge OR split OR evolution)
    "incremental clustering" AND ("cluster evolution" OR "cluster creation" OR "cluster deletion")
    ("online clustering" OR "streaming clustering") AND (abstention OR reject OR uncertainty OR "unknown class")
    ("dynamic clustering" OR "evolving clusters") AND (merge OR split) AND (stream OR text)
- F7 [TRANSFER]
    ("incremental entity resolution" OR "online entity resolution") AND (merge OR split OR revision OR history)
    ("record linkage" OR "entity resolution") AND (match OR nonmatch OR "non-match") AND (uncertain OR threshold OR cost)
    ("entity resolution" OR "record linkage") AND ("false match" OR "false merge" OR "false non-match" OR "false split")
    ("entity resolution" OR "record linkage") AND ("clerical review" OR abstention OR uncertain) AND decision
    ("incremental entity resolution" OR "dynamic entity resolution") AND (provenance OR lineage OR cluster)
- F8 [TRANSFER]
    "object-centric process mining" AND (convergence OR divergence OR "multiple objects")
    ("object-centric" OR "artifact-centric") AND "process mining" AND (event OR case OR relation)
    ("multi-object" OR "multiple objects") AND event AND ("process mining" OR workflow) AND relation
    ("case notion" AND "object-centric") AND (event OR process)
    ("artifact-centric process" OR "artifact-centric process mining") AND (correlation OR interaction OR lifecycle)
- F9 [DIRECT]
    (enterprise OR workplace OR organizational) AND (email OR "Microsoft Teams" OR "enterprise chat" OR "workplace chat") AND ("task tracking" OR "case tracking" OR "issue tracking" OR "work item") AND longitudinal
    ("business email" OR "enterprise email") AND (task OR case OR issue OR activity) AND ("cross-thread" OR "across threads" OR longitudinal) AND (linking OR tracking)
    ("Microsoft Teams" OR "enterprise messaging" OR "enterprise chat") AND (task OR case OR issue OR "work item") AND (tracking OR linking OR continuity)
    (email AND chat) AND ("cross-channel" OR "cross-source") AND (task OR case OR workflow OR issue) AND (identity OR linking OR correlation)
    ("organizational communication" OR "workplace communication") AND ("case linking" OR "task linking" OR "work-item linking" OR "issue linking")
- F10 [TRANSFER]
    ("selective classification" OR "selective prediction" OR abstention OR "reject option") AND ("distribution shift" OR nonstationary OR "concept drift") AND (text OR NLP)
    ("confidence calibration" OR calibration) AND ("distribution shift" OR "concept drift") AND (NLP OR text OR streaming)
    ("adaptive conformal inference" OR "conformal prediction") AND ("distribution shift" OR nonstationary) AND classification
    ("selective prediction" OR abstention) AND (coreference OR clustering OR "entity resolution")
    (calibration OR abstention) AND streaming AND text AND (risk OR coverage OR uncertainty)
- F11 [TRANSFER]
    ("event coreference" OR "cross-document event coreference") AND (retrieval OR "candidate retrieval" OR "document retrieval")
    "cross-document event coreference" AND ("global context" OR context) AND retrieval
    ("event coreference" OR "entity resolution") AND ("candidate generation" OR blocking OR retrieval) AND cross-document
    (retrieval AND "event coreference") AND (evidence OR context OR history)
    ("historical context" OR "additional context") AND (coreference OR "event identity") AND retrieval
- F12 [TRANSFER]
    ("incremental entity resolution" OR "dynamic clustering") AND ("cluster merge" OR "cluster split" OR "merge split")
    ("cluster evolution" OR "cluster maintenance") AND (merge OR split) AND (provenance OR lineage OR history)
    ("entity resolution" OR "record linkage") AND (correction OR revision OR adjudication) AND (cluster OR identity)
    ("stable identifier" OR "persistent identity") AND (cluster OR "entity resolution") AND incremental
    ("human-in-the-loop entity resolution" OR "interactive entity resolution") AND (correction OR review OR uncertain)
False friends — these match the words but not the capability, so do
not list them:
- Downgrade or exclude ordinary topic modeling in which a topic is a latent word distribution rather than a concrete persistent work matter.
- Downgrade conversation disentanglement, reply-thread reconstruction, email threading, and channel reconstruction unless the study separately evaluates work-item, task, case, issue, or event identity beyond conversation membership.
- Exclude entity-linking papers whose target is assignment of mentions to a fixed knowledge-base entity unless they additionally study incremental same-identity clustering relevant to the research question.
- Downgrade document similarity, embedding similarity, nearest-neighbor retrieval, or related-document recommendation unless positive labels explicitly mean same event, case, task, or work item.
- Downgrade within-document-only event coreference unless the paper contributes an identity criterion, relation taxonomy, or decision method clearly transferable to cross-document identity.
- Downgrade duplicate detection and near-duplicate detection because duplication is narrower than continuation of an evolving matter.
- Downgrade TDT and story-link papers when their positive relation is only topical relatedness and cannot be distinguished from strict same-event identity.
- Downgrade new-event or novelty methods that merely score surprising content and do not decide whether an item attaches to an existing identity or starts a new one.
- Downgrade clustering methods that force every observation into an existing cluster and provide neither new-cluster creation nor abstention/rejection.
- Downgrade incremental or streaming clustering papers that optimize only geometric cohesion, throughput, or memory and provide no interpretable identity relation, merge/split behavior, or evaluation of assignment errors.
- Downgrade process-mining papers that assume a correct case identifier is already present in the event log; prioritize papers that infer, correlate, or evaluate case membership.
- Downgrade object-centric process-mining work that presupposes all correct event-object identifiers if it offers no evidence about discovering or validating those relations; retain it only for relation semantics such as multi-object membership, convergence, or divergence.
- Downgrade event-timeline and event-evolution papers when timeline membership merely means related events and no identity, subevent, membership, or continuation relation is annotated.
- Downgrade general workplace-communication, CSCW, organizational-behavior, or asynchronous-communication studies unless they operationalize message-to-task, message-to-case, work-item, event, or longitudinal continuity relations.
- Downgrade enterprise-email studies on spam, prioritization, summarization, speech acts, response prediction, social networks, or intent classification unless they directly contribute evidence for longitudinal work-matter identity.
- Downgrade chat conversation disentanglement as Topic-01-style source/conversation structure rather than Topic identity unless it independently annotates a business task, case, issue, or work item spanning conversations.
- Downgrade static entity-resolution and record-linkage work when used to support merge/split or longitudinal correction claims unless it contains incremental revision, uncertain matching, adjudication, or identity-history mechanisms.
- Downgrade calibration papers that report only in-distribution confidence accuracy; gap-7 requires distribution shift, concept drift, streaming, non-stationarity, or another explicit changing-distribution condition.
- Downgrade selective-prediction papers that optimize risk-coverage without explaining how abstention interacts with clustering, matching, or identity assignment; they are method-transfer evidence only.
- Downgrade retrieval papers that improve recall without measuring whether retrieved evidence changes identity decisions correctly; retrieval volume alone does not close gap-6.
- Never treat a news, social-media, biomedical, bibliographic, customer-deduplication, or other transfer-domain benchmark as direct evidence of Outlook-email or Microsoft-Teams production accuracy.
- Never infer work-matter identity from identical subject, participant, customer, project, lexical similarity, source thread, or generated label unless the study's gold relation explicitly defines those observations as evidence for the same concrete matter.
- Do not admit a paper as evidence for partial/non-transitive continuity merely because it contains multiple event types; it must explicitly model relations such as partial identity, quasi-identity, subevent, membership, overlap, convergence/divergence, or another non-equivalence relation.
- Do not treat merge/split algorithm support as evidence that msgloom should perform a particular MERGE or SPLIT: project-specific correction semantics, stable Topic IDs, supersession, and immutable lineage remain engineering decisions.
Reach back to 1969 at least. Discovery must reach 1969 because record linkage is a deliberate transfer family and Fellegi and Sunter's A Theory for Record Linkage is foundational for probabilistic match/non-match evidence and uncertain decisions. The more directly relevant streaming-text lineage begins in the late 1990s: Topic Detection and Tracking and online new-event detection were established in 1998, and cross-document event-coreference work appears by 1999. A modern-only recency window would therefore silently remove foundational identity, threshold, and new-event formulations. Bulk searches should still prioritize recent enterprise, cross-document event-coreference, process-mining, calibration, and streaming work, but discovery must permit targeted foundation sweeps back to 1969.

This is gap-closure round 4 of at most 4 for the
original topic **Direct enterprise email/chat studies of longitudinal cross-thread conversation or work-item linking, especially evidence for concrete business-event identity and for partial, evolving, subevent, or non-transitive continuity relations in organizational workflows.**. Earlier rounds could not
close the open gaps below. Run every suggested query as well, and look
specifically for papers that answer these gaps:
- gap-1 [ACADEMIC, HIGH]: Which evidence combinations actually establish or refute continuity of a concrete work matter across independent workplace messages, conversations, attachments, email, and Teams remains open. The corpus supports adjacent-domain signals but does not validate subject, customer/project names, conversation ancestry, referenced artifacts, commitments, or state compatibility as target-domain identity evidence.
    suggested query: ("work item identity" OR "work matter identity" OR "business event coreference" OR "cross-document event coreference") AND (email OR "workplace communication" OR enterprise) AND (cross-thread OR cross-document OR cross-source)
    searched in rounds: [1, 2, 3] (still open)
- gap-4 [ACADEMIC, HIGH]: There is still no direct production-domain evidence in this corpus for longitudinal work-matter identity across Outlook email and Microsoft Teams. The enterprise email and process-correlation papers provide useful adjacent evidence but do not establish production accuracy or representativeness for msgloom.
    suggested query: (enterprise OR workplace OR organizational) AND (email OR "Microsoft Teams" OR "enterprise chat" OR "workplace chat") AND (cross-thread OR longitudinal OR cross-conversation) AND ("topic identity" OR "task tracking" OR "case tracking" OR "event coreference" OR "conversation linking")
    searched in rounds: [1, 2, 3] (still open)
- gap-5 [ACADEMIC, HIGH]: How partial, subevent, evolving, membership, or otherwise non-transitive relations should map onto workplace work-matter continuity remains unresolved. The corpus establishes that such relations exist and can violate transitivity, but it does not define when they should mean CONTINUE, RELATED-BUT-SEPARATE, MERGE, SPLIT, or another workplace-specific relation.
    suggested query: ("partial event identity" OR "partial coreference" OR "subevent relation" OR "event evolution" OR "event membership" OR "non-transitive coreference") AND (workflow OR task OR case OR workplace OR enterprise)
    searched in rounds: [1, 2, 3] (still open)
- gap-7 [ACADEMIC, MEDIUM]: Calibration under non-stationary workplace streams remains unresolved. The corpus now contains stronger evidence that calibration deteriorates under distribution shift and that drift-aware or conformal approaches can help, but it does not establish reliable calibration, abstention thresholds, or coverage guarantees for longitudinal workplace coreference or clustering.
    suggested query: ("selective classification" OR abstention OR "confidence calibration" OR "selective prediction") AND ("distribution shift" OR nonstationary OR streaming OR "concept drift") AND (text OR NLP OR coreference OR clustering)
    searched in rounds: [1, 2, 3] (still open)

Papers already reviewed in earlier rounds (do NOT list them again):
1402.4417, 1412.5687, 1705.08500, 1707.07344, 1906.01753, 2011.12249, 2104.05022, 2109.06417, 2407.11988, doi-10-1002-asi-21264, doi-10-1002-sim-4780140510, doi-10-1007-978-3-030-33223-5-12, doi-10-1007-978-3-030-49461-2-23, doi-10-1007-978-3-540-27868-9-84, doi-10-1007-s00778-010-0203-9, doi-10-1007-s10115-019-01430-6, doi-10-1016-j-ipm-2025-104085, doi-10-1038-s41598-025-32765-6, doi-10-1038-s41598-026-40637-w, doi-10-1080-01621459-1969-10501049, doi-10-1109-access-2023-3284053, doi-10-1109-icpm57379-2022-9980684, doi-10-1145-1111449-1111473, doi-10-1145-290941-290953, doi-10-1145-354756-354843, doi-10-18653-v1-2020-coling-main-275, doi-10-18653-v1-2022-emnlp-main-58, doi-10-18653-v1-2023-emnlp-main-294, doi-10-2139-ssrn-7284343, doi-10-3115-1220575-1220591, doi-10-3115-v1-w14-2910, manual-03d6dfa532, manual-35bac66e3c, manual-5c20fb0229, manual-61a7e10e5f, manual-c43ffe3135, manual-e988e24127, manual-f56d02b8f9

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
