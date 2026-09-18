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

Research topic: **Direct empirical NLP methods for longitudinal work-item revision in workplace or operational communication, especially relation labeling for supersession/correction/supplementation/reopening/conflict and evidence models separating claimed completion from independently corroborated completion.**

Must-have terms: direct, empirical, nlp
Nice-to-have terms: longitudinal, work-item, revision, workplace, operational, communication,, especially, relation, labeling, supersession/correction/supplementation/reopening/conflict, evidence, separating, claimed, independently, corroborated, completion.
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
    "work item" longitudinal revision classification email supersession correction supplementation reopening conflict
    "task status" email longitudinal revision correction cancellation completion reopening
    "action item" email thread status change completion cancellation correction
    "workplace email" task lifecycle requested planned approved completed revoked superseded
    "enterprise chat" task status update correction cancellation completion
    "operational communication" state tracking revision contradiction supersession
    "issue tracker" natural language status update correction reopen close supersede
    "incident management" communication revision status update correction resolution reopen
    "message" "supersedes" correction supplementation contradiction task status NLP
    "revision relation" messages supersession correction supplementation retraction reopening
- F2 [TRANSFER]
    "event factuality" source commitment longitudinal
    "event factuality prediction" source attribution temporal
    "event veridicality" source attribution event status
    "event modality" factuality intention completion negation
    "speaker commitment" event factuality dialogue
    "source commitment" factuality NLP event
    epistemic modality event factuality conditional planned completed
    "factuality" correction retraction event
- F3 [TRANSFER]
    "source attribution" factuality evidence corroboration NLP
    "speaker commitment" independent evidence verification
    "claim verification" source attribution corroborating evidence temporal
    "fact verification" multiple sources provenance claim evidence
    "evidence attribution" claim verification provenance NLP
    "evidentiality" source attribution event factuality NLP
    "independent corroboration" claim verification NLP
    "source independence" corroboration claim verification
    "event factuality" "fact verification" source
    "completion" claim corroboration evidence task NLP
- F4 [TRANSFER]
    "temporal relation extraction" event ordering cross-document
    "event temporal ordering" cross-document update
    "temporal relation classification" discourse events
    "temporal graph" event ordering consistency NLP
    "temporal closure" event relations NLP
    "temporal constraint reasoning" natural language events
    TimeML cross-document temporal relations
    "document creation time" event time temporal relation extraction
    "event time" "message time" NLP temporal
    "effective time" natural language event temporal extraction
- F5 [TRANSFER]
    "event evolution" NLP cross-document
    "event evolution" news timeline state change
    "event tracking" cross-document temporal NLP
    "event timeline extraction" cross-document
    "timeline extraction" evolving events NLP
    "event update" cross-document semantic revision
    "event progression" NLP temporal
    "event history" natural language temporal
- F6 [TRANSFER]
    "contradiction detection" temporal information source attribution
    "textual contradiction" temporal contradiction NLP
    "natural language inference" temporal contradiction
    "natural language inference" source attribution contradiction
    "contradiction" correction supersession NLP
    "entailment" correction retraction dialogue
    "temporal NLI" contradiction events
    "fact consistency" revisions contradiction text
- F7 [TRANSFER]
    "dialogue commitment" retraction correction
    "commitment tracking" dialogue retraction
    "public commitments" dialogue revision
    "dialogue state" correction retraction belief update
    "belief tracking" dialogue correction contradiction
    "dialogue repair" correction retraction commitment
    "conversational commitment" update retraction
    "commitment store" dialogue correction
- F8 [TRANSFER]
    "belief revision" natural language evidence
    "belief revision" source reliability temporal
    "belief revision" dialogue contradiction
    "truth maintenance system" conflicting evidence provenance
    "truth maintenance" retraction justification provenance
    "assumption-based truth maintenance" conflicting evidence
    "belief revision" provenance temporal information
    "non-monotonic reasoning" conflicting reports source
- F9 [TRANSFER]
    "edit intent classification" document revisions
    "revision purpose classification" NLP
    "semantic edit classification" document revision
    "document revision" correction addition deletion classification NLP
    "revision classification" Wikipedia correction clarification addition
    "document supersession" semantic revision NLP
    "version comparison" semantic change NLP
    "document change" correction supersession natural language
- F10 [TRANSFER]
    "temporal knowledge graph" fact update contradiction
    "dynamic knowledge graph" evolving facts provenance
    "temporal knowledge graph" provenance source
    "knowledge graph update" contradictory information source
    "knowledge base revision" temporal provenance
    "dynamic knowledge graph" event state change
    "temporal knowledge graph" validity interval fact
- F11 [TRANSFER]
    "data provenance" derived state source evidence
    "provenance" belief revision evidence lineage
    "provenance-aware" state history
    "immutable event log" derived state provenance
    "event sourcing" provenance current state projection
    "provenance" temporal database changing facts
    "data lineage" temporal assertions source
    "provenance semiring" conflicting information
- F12 [TRANSFER]
    "bitemporal" natural language events provenance
    "valid time" "transaction time" event data
    "valid time" "event time" "transaction time"
    "effective time" "transaction time" temporal database
    "event time" "ingestion time" provenance
    "observation time" temporal database provenance
    "assertion time" "valid time" temporal information
    "bi-temporal" knowledge base changing facts
- F1 [DIRECT]
    "workplace email" supersession correction supplementation contradiction
    "business email" deadline change correction cancellation completion
    "email thread" task status correction completion cancellation
    "enterprise communication" work item lifecycle NLP
    "workplace communication" event factuality temporal revision
    "Teams" task status correction completion NLP
    "Slack" task status update correction NLP
    "operational messages" task state revision NLP
- F2 [TRANSFER]
    "event factuality" temporal relation contradiction joint model
    "factuality" "temporal relation extraction" joint
    "event factuality" provenance source temporal
    "event factuality" lifecycle state
    "factuality" contradiction temporal ordering source
- F3 [TRANSFER]
    "claimed completion" verification evidence
    "completion claim" independent verification
    "task completion" evidence verification natural language
    "asserted completion" corroboration
    "reported completion" evidence provenance
    "completion status" source attribution evidence
False friends — these match the words but not the capability, so do
not list them:
- Downgrade or exclude pure TIMEX/date extraction that does not relate events to one another or distinguish message time from event/effective time.
- Downgrade standard dialogue state tracking when the maintained state is only slots, intents, or user goals and historical evidence/revisions are overwritten.
- Downgrade generic NLI or contradiction benchmarks when they operate only on isolated sentence pairs and contain no temporal, source, provenance, or longitudinal state semantics.
- Downgrade event factuality work that predicts only an author's textual commitment if it is presented as evidence for independent truth or completion verification; retain it only as TRANSFER evidence for source-relative assertion status.
- Downgrade fact-verification literature that retrieves external evidence but does not distinguish source assertions, event time, or longitudinal revisions; retain only for the corroboration mechanism.
- Exclude action-item, request, commitment, or decision extraction papers that stop at extracting the utterance-time event and do not evaluate later revision or lifecycle state; those belong primarily to Topic 05.
- Exclude generic update summarization and incremental summarization that describe what is new but do not determine whether old information remains valid.
- Exclude latest-message-wins, latest-version-wins, or timestamp-only heuristics as evidence of semantic supersession.
- Downgrade workflow-engine or business-process state-machine papers when lifecycle transitions are supplied as structured system events rather than inferred from uncertain natural language evidence.
- Downgrade process mining unless textual communications are the evidence from which state and revision relations are inferred.
- Downgrade document-diff and change-detection work that reports inserted, deleted, or modified text without classifying the semantic effect of the revision.
- Downgrade software-version and package-supersession literature unless it contributes a transferable formal model of lineage; explicit version ordering is not evidence for semantic message supersession.
- Downgrade legal or policy document supersession when replacement is supplied by formal metadata rather than inferred from natural-language relations.
- Downgrade temporal knowledge-graph completion and forecasting if input facts are already canonicalized and the task neither preserves source observations nor reasons about contradictory evidence.
- Downgrade temporal-relation papers that infer BEFORE/AFTER relations but make no claim about validity, supersession, correction, or factuality.
- Downgrade timeline-extraction literature when the output is simply an ordered list of events rather than a history of changing assessments of the same work item.
- Downgrade event-evolution literature that models news-story development or topic drift without same-item revision relations.
- Downgrade belief-revision, TMS, ATMS, and non-monotonic reasoning papers to TRANSFER when they operate only on symbolic propositions; they are not direct evidence of NLP accuracy.
- Downgrade provenance and event-sourcing literature to ENGINEERING/TRANSFER when it assumes that source events have already been interpreted correctly.
- Exclude studies that destructively replace an earlier record with a new current state if the historical source observation and assessment lineage cannot be reconstructed.
- Do not accept a paper as closing gap 1 or gap 2 merely because its label inventory contains words such as update, correction, contradiction, or state; it must evaluate successive communications about the same underlying item.
- Do not accept a paper as closing gap 4 unless its evaluated data are workplace, enterprise, operational, issue-management, incident-management, or comparably task-oriented communication rather than only news or synthetic propositions.
- Do not accept a paper as closing gap 5 merely because it predicts factuality, confidence, or entailment. It must represent or evaluate a distinction between what a source claims and evidence that corroborates or verifies the claim.
- Do not accept a joint model as closing gap 3 unless source-relative factuality, temporal ordering, lifecycle/revision state, contradiction, and provenance are all represented or jointly evaluated rather than merely mentioned as separate upstream features.
- Do not treat a later message as evidence of supersession unless the model uses semantic, referential, temporal, or explicit revision evidence to establish the relation.
- Do not collapse correction, supersession, supplementation, contradiction, retraction/revocation, reopening, and unresolved conflict into a single generic change class when evaluating direct relevance.
Reach back to 1979 at least. Discovery should reach at least 1979 because Doyle's truth-maintenance work is foundational to maintaining conclusions and justifications under additions and retractions. Closely related foundations include Allen's 1983 temporal interval reasoning, AGM belief revision in 1985, and de Kleer's ATMS in 1986. The empirical NLP strands become much more prominent in the 2000s, including TimeML, textual entailment, contradiction detection, event factuality, and later temporal and verification benchmarks. Restricting discovery to recent NLP would therefore silently remove formal mechanisms directly relevant to provenance-preserving historical assessment, while beginning earlier than 1979 is not required by the task families identified here.

This is gap-closure round 4 of at most 4 for the
original topic **work-item state, event factuality, temporal reasoning, and conflicting revisions in workplace communication: tracking whether an event is planned, confirmed, revoked, completed, or contradicted**. Earlier rounds could not
close the open gaps below. Run every suggested query as well, and look
specifically for papers that answer these gaps:
- gap-1 [ACADEMIC, HIGH]: No admitted paper directly evaluates longitudinal state tracking across workplace messages in which one work item moves among requested, proposed, planned, approved, completed, revoked, superseded, disputed, conditional, and unresolved states while retaining historical assessments.
    suggested query: workplace email enterprise chat longitudinal work item lifecycle state tracking requested planned approved completed revoked superseded disputed unresolved
    searched in rounds: [1, 2, 3] (still open)
- gap-2 [ACADEMIC, HIGH]: The corpus provides formal treatments of correction, retraction, persistence, and reopening, but does not establish a natural-language method evaluated across successive operational communications for distinguishing supersession, correction, supplementation, contradiction, reopening, and unresolved conflict.
    suggested query: natural language dialogue revision relation classification supersession correction supplementation contradiction reopening unresolved conflict longitudinal
    searched in rounds: [1, 2, 3] (still open)
- gap-3 [ACADEMIC, HIGH]: No admitted paper jointly evaluates source-relative factuality, temporal ordering, lifecycle state, contradiction, and provenance as one longitudinal model; the papers validate separate components and their combination remains untested.
    suggested query: "event factuality" temporal relation contradiction provenance lifecycle longitudinal joint model
    searched in rounds: [1, 2, 3] (still open)
- gap-4 [ACADEMIC, HIGH]: Direct evidence for workplace email, Teams-like dialogue, or comparable operational communication is absent; the empirical NLP evidence is predominantly news-derived, while the commitment and belief-revision papers use formal, modeled, argumentative-dialogue, or adjacent-domain settings.
    suggested query: workplace email enterprise chat operational communication task state tracking revision factuality temporal commitment
    searched in rounds: [1, 2, 3] (still open)
- gap-5 [ACADEMIC, HIGH]: The admitted factuality literature models textual source commitment, and the fact-verification literature models corroborating evidence, but no admitted paper establishes how to distinguish an author's assertion that work is complete from independent confirmation or stronger evidential verification of completion in longitudinal operational communication.
    suggested query: dialogue event factuality evidentiality source attribution claimed completion independent confirmation corroboration longitudinal
    searched in rounds: [1, 2, 3] (still open)

Papers already reviewed in earlier rounds (do NOT list them again):
1804.06020, 1805.06975, 1909.00429, 1909.05360, 2011.03088, 2104.01146, 2406.00197, 2608.20116, doi-10-1007-3-540-44503-x-20, doi-10-1007-s10458-012-9202-0, doi-10-1007-s10579-009-9089-9, doi-10-1007-s11390-024-2655-1, doi-10-1016-0004-3702-86-90080-9, doi-10-1016-0020-0255-94-90059-0, doi-10-1016-j-artint-2003-08-003, doi-10-1016-j-ipm-2021-102836, doi-10-1016-j-ipm-2026-104709, doi-10-1016-j-knosys-2016-07-032, doi-10-1017-cbo9780511526664-007, doi-10-1023-a-1010318403544, doi-10-1093-jos-ffn013, doi-10-1145-1082473-1082754, doi-10-1162-tacl-a-00182, doi-10-18653-v1-2021-acl-long-122, doi-10-18653-v1-2021-emnlp-main-815, doi-10-18653-v1-2023-findings-acl-44, doi-10-18653-v1-d18-1155, doi-10-18653-v1-p19-1412, manual-2362cbe877, manual-b3703967d3, manual-eef7a0219f

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
