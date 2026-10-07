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

Research topic: **direct empirical studies of proposition-level partial reply scope in workplace email or enterprise dialogue, especially multi-question messages, unanswered subquestions, scoped approval/rejection, and responses linked jointly to multiple antecedent propositions**

Must-have terms: direct, empirical, studies
Nice-to-have terms: proposition-level, partial, reply, workplace, email, enterprise, dialogue,, especially, multi-question, messages,, unanswered, subquestions,, scoped, approval/rejection,, responses, linked, jointly, multiple, antecedent, propositions
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
    "non-nominal antecedent" anaphora resolution dialogue proposition
    "non-nominal antecedent anaphora" dialogue
    "abstract anaphora" dialogue antecedent resolution proposition
    "abstract anaphora" conversation antecedent span
    "discourse deixis" dialogue antecedent proposition
    "discourse-deictic" dialogue antecedent resolution
    "propositional anaphora" dialogue antecedent
    "sentential antecedent" dialogue anaphora
    "clausal antecedent" dialogue anaphora
    "abstract anaphora" email
- F2 [DIRECT]
    "dialogue discourse parsing" response relation antecedent
    "dialogue discourse parsing" question answer acknowledgment correction
    "multiparty dialogue discourse parsing" attachment relation
    "discourse attachment" dialogue response antecedent
    "reply-to structure" dialogue discourse relation
    "response relation" dialogue discourse attachment
    "conversational discourse relations" response antecedent
    "discourse dependency" dialogue question answer relation
    "complex discourse unit" dialogue response
    SDRT dialogue response relation antecedent
- F3 [DIRECT]
    "question answer pairs" enterprise email
    "question answer pair" workplace email thread
    "question answer alignment" email thread
    "question answer matching" email conversation
    "question answer extraction" enterprise email
    "question answer pairs" threaded email conversations
    "matching questions and answers" dialogue conversation
    "QA matching" dialogue antecedent question
    "answer selection" dialogue previous question
    "question-answer relation" workplace email
- F4 [DIRECT]
    "partial answer" dialogue question
    "partial answers" conversation question
    "answer completeness" dialogue question
    "incomplete answer" dialogue question
    "unanswered question" dialogue discourse
    "unanswered questions" email thread
    "unanswered subquestion" dialogue
    "multiple questions" dialogue answer alignment
    "multiple questions" email answer
    "multi-part question" dialogue answer
    "multi-question" conversation answer alignment -"questions about a transcript"
    "question resolution" dialogue unanswered
    "question under discussion" partial answer dialogue
    "answerhood" partial answer conversation
- F5 [DIRECT]
    "agreement target" dialogue
    "agreement target identification" conversation
    "agreement detection" target utterance conversation
    "agreement detection" addressee target dialogue
    "disagreement target" dialogue
    "agreement disagreement" adjacency pair target
    "agreement" "target utterance" multiparty conversation
    "acceptance" "target" dialogue proposition
    "rejection" "target" dialogue proposition
    "acceptance rejection" discourse relation dialogue
    "agreement scope" conversation
    "partial agreement" dialogue target
- F6 [DIRECT]
    "multiple antecedents" discourse anaphora proposition
    "multi-antecedent" discourse reference dialogue
    "split antecedent" abstract anaphora
    "split antecedents" discourse reference proposition
    "complex antecedent" abstract anaphora
    "composite antecedent" discourse anaphora
    "complex discourse unit" antecedent response dialogue
    "complex discourse unit" question answer dialogue
    "discourse segment" demonstrative "one or more clauses"
    "multiple discourse units" response relation dialogue
- F7 [TRANSFER]
    "email speech acts" Enron request commitment
    "requests and commitments" email messages annotation
    "utterance level" workplace email request commitment
    "business email" acceptance rejection corpus
    "workplace email" agreement disagreement corpus
    "enterprise email" speech act annotation
    "workplace email" proposal acceptance rejection
    "email" request commitment response annotation
- F8 [TRANSFER]
    "stance target identification" claim span
    "targeted stance" proposition target extraction
    "stance target extraction" argument claim
    "stance" "target span" conversation
    "claim target" agreement disagreement dialogue
    "target-specific stance" conversation claim
- F9 [TRANSFER]
    "textual entailment" dialogue response proposition
    "natural language inference" dialogue agreement disagreement
    "contradiction" dialogue response proposition
    "entailment" "target proposition" dialogue
    "semantic relation" response antecedent proposition
    "NLI" conversation agreement disagreement target
- F10 [TRANSFER]
    "abstract anaphora" "no antecedent"
    "abstract anaphora" ambiguous antecedent annotation
    "non-nominal antecedent" ambiguous multiple antecedents
    "anaphora resolution" "no identifiable antecedent" dialogue
    "discourse attachment" "no link" dialogue
    "dialogue discourse parsing" no-link antecedent
    "antecedent selection" abstention anaphora
    "antecedent selection" multiple candidates discourse
    "anaphora" unresolved antecedent annotation guidelines
    "discourse deixis" ambiguous antecedent corpus
- F11 [TRANSFER]
    "adjacency pairs" question answer conversation
    "adjacency pair" proposal acceptance rejection
    "adjacency pair" request compliance refusal
    "conditional relevance" unanswered question conversation
    "sequence organization" question answer acceptance rejection
    "adjacency pair identification" dialogue computational
False friends — these match the words but not the capability, so do
not list them:
- Downgrade entity-only coreference or pronoun resolution unless non-nominal, clausal, sentential, eventive, factual, situational, or propositional antecedents are explicitly modeled.
- Downgrade agreement or disagreement detection when the system predicts only a polarity or dialogue-act label and does not identify the prior target.
- Downgrade agreement-target work that identifies only the target speaker if it cannot identify the target utterance, discourse unit, clause, proposition, or span.
- Downgrade dialogue-act or speech-act classification when the current utterance is labeled request, answer, accept, reject, acknowledge, or approve but no antecedent link is annotated or predicted.
- Downgrade whole-message intent or email-act classification when one message may contain several propositions but the method cannot represent different reply scopes for them.
- Downgrade generic QA and reading-comprehension papers when the antecedent question is already supplied as gold input and no question-to-reply alignment is required.
- Downgrade multi-question QA where several externally supplied questions are answered from one transcript or document; this is not evidence that a natural reply can be mapped to one of several preceding conversational questions.
- Downgrade answer-generation, Smart Reply, response-generation, and next-utterance prediction unless evaluation explicitly measures which antecedent proposition the response addresses.
- Downgrade answer-correctness or answer-quality scoring when it does not determine which prior question or subquestion the answer resolves.
- Downgrade email threading, Message-ID/In-Reply-To reconstruction, reply-tree induction, and reply-likelihood prediction unless semantic relation endpoints below message level are studied.
- Downgrade addressee recognition when it predicts only which person is addressed and not which proposition or discourse unit is answered, accepted, rejected, or clarified.
- Downgrade discourse-relation classification when relation endpoints are supplied as gold and the task never chooses the antecedent; retain only as TRANSFER evidence for relation labeling.
- Downgrade monologic discourse parsing unless its annotation or evaluation contains mechanisms directly reusable for non-adjacent, multiple, complex, ambiguous, or no-link antecedents.
- Downgrade stance or sentiment work when the stance target is a fixed topic, entity, politician, product, or aspect rather than a preceding conversational proposition selected from context.
- Downgrade NLI, textual entailment, and contradiction work when the proposition pair is supplied in advance; such work is TRANSFER evidence only.
- Downgrade event coreference when it clusters mentions of the same event but does not model a response relation to eventive or propositional content.
- Downgrade grammatical agreement literature despite lexical overlap with agreement detection.
- Downgrade 'approval scope' literature from access control, governance, regulation, procurement, legal authorization, or workflow permissions unless linguistic reply scope is explicitly studied.
- Downgrade business-email pragmatics, politeness, genre, pedagogy, move analysis, or writing-quality studies when they contain no response-to-antecedent annotation.
- Downgrade conversation-analysis papers that discuss adjacency pairs qualitatively but provide no empirical annotation relevant to antecedent granularity; retain foundational terminology but not as direct computational validation.
- Downgrade datasets that permit only one antecedent per response when the paper does not discuss whether multiple or composite antecedents occur naturally.
- Downgrade datasets that delete, collapse, or force-resolve ambiguous or unsupported antecedents instead of preserving uncertainty or explicit no-link cases.
- Downgrade studies that report only turn-level or message-level accuracy when the target capability requires clause-, EDU-, proposition-, or span-level distinctions.
- Downgrade synthetic-only or task-generated dialogue from DIRECT workplace evidence to TRANSFER unless the study also evaluates authentic workplace email or enterprise dialogue.
- Downgrade public forum, game chat, social media, customer-support, and casual conversation evidence to TRANSFER for production-domain claims unless the mechanism being evaluated is domain-independent and this limitation is stated.
- Downgrade enterprise-email question-answer extraction that establishes only one-to-one QA pairs and does not evaluate multi-question messages, partial answers, unanswered subquestions, or one answer linked to several questions; it remains directly relevant but does not close gap-3 by itself.
- Downgrade approval, acceptance, rejection, or agreement papers that assume the entire immediately preceding turn is the target and cannot distinguish acceptance of one clause from rejection or non-response to another.
- Downgrade any paper that infers a missing antecedent rather than allowing unresolved, unsupported, exophoric, or unavailable-context outcomes when the evidence is absent.
- Exclude visual, table, document-cell, screenshot, page, or attachment-object grounding as primary Topic 04 evidence; hand those cases to Topic 08 unless the paper also evaluates propositional response scope.
- Do not treat paper count, benchmark scale, or model accuracy as closure of a direct-evidence gap when the evaluated annotation contract lacks partial, ambiguous, multiple-antecedent, discontinuous, or explicit no-link cases.
Reach back to 1974 at least. Discovery must reach at least 1974. The conceptual foundations relevant to this topic predate modern NLP benchmarks: Lakoff's 1974 work on demonstratives is a recognized precursor to later discourse-deixis work, and conversation-analysis work from the same period establishes adjacency-pair and sequential-response concepts used for question-answer, proposal-acceptance/rejection, and other response relations. Computational treatments of discourse deixis and non-nominal antecedents become especially important in the late 1980s and 1990s, followed by dialogue anaphora, discourse parsing, agreement targeting, and enterprise-email QA in the 2000s and 2010s. A 2000-, 2010-, or recent-only window would therefore silently remove foundational terminology needed to find the later empirical literature. Bulk discovery may prioritize post-1990 empirical NLP after the foundational pass, but it must not hard-cut publications before 1974.

This is gap-closure round 4 of at most 4 for the
original topic **empirical reply-to-proposition alignment in email and dialogue, focusing on partial replies, multiple questions, unanswered questions, and multi-proposition antecedents**. Earlier rounds could not
close the open gaps below. Run every suggested query as well, and look
specifically for papers that answer these gaps:
- gap-1 [ACADEMIC, HIGH]: Direct empirical evidence is still missing for proposition-level agreement, rejection, approval, clarification, and answer scope in authentic workplace email or enterprise chat, especially cases where one short response applies to only part of a preceding message.
    suggested query: "partial reply" OR "response scope" email workplace dialogue proposition agreement rejection approval
    searched in rounds: [1, 2, 3] (still open)
- gap-3 [ACADEMIC, HIGH]: Direct evidence remains insufficient for aligning replies to one or more questions when a preceding workplace message contains multiple questions, requests, or alternatives, including proposition-level detection of questions that remain unanswered.
    suggested query: "multiple questions" "partial answer" dialogue email question answer alignment unanswered subquestions
    searched in rounds: [1, 2, 3] (still open)
- gap-4 [ACADEMIC, MEDIUM]: It remains open whether and how a workplace response should be modeled as targeting a composite or multi-proposition antecedent. The corpus supports composite abstract discourse referents and multi-unit discourse antecedents, but does not directly evaluate multi-proposition reply scope in work communication.
    suggested query: "multi-antecedent" dialogue response "composite antecedent" proposition discourse email
    searched in rounds: [1, 2, 3] (still open)

Papers already reviewed in earlier rounds (do NOT list them again):
1706.02256, 2403.16609, doi-10-1007-bf00351935, doi-10-1007-bf00983299, doi-10-1007-s10489-013-0481-1, doi-10-1016-j-pragma-2007-07-011, doi-10-1016-j-pragma-2018-03-015, doi-10-1093-jos-17-1-51, doi-10-1109-icaicta63815-2024-10762999, doi-10-1162-coli-a-00327, doi-10-1177-002383099603900306, doi-10-1515-ling-2018-0008, doi-10-15398-jlm-v4i2-173, doi-10-1609-aaai-v33i01-3301134, doi-10-18653-v1-2021-codi-sharedtask-1, doi-10-18653-v1-2021-naacl-main-329, doi-10-18653-v1-2022-emnlp-main-778, doi-10-18653-v1-2023-eacl-main-247, doi-10-18653-v1-2023-findings-acl-710, doi-10-18653-v1-d15-1109, doi-10-18653-v1-p17-1009, doi-10-18653-v1-s15-1035, doi-10-3115-1220355-1220483, doi-10-3115-1708376-1708429, doi-10-3115-v1-d14-1056, doi-10-3233-aic-2012-0516, doi-10-3765-sp-5-6, doi-10-5210-dad-2022-203, doi-10-5210-dad-2023-201, manual-555fa5b6e8, manual-5a32708675, manual-5c0971730d, manual-7743c50805, manual-8b8a394daa, manual-a6314f615a, manual-ad98de9372, manual-be69c3aa17, manual-e1981ecd9a

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
