# Integrated adaptive retrieval controllers with structured evidence gaps, temporal and version-aware provenance, permission-aware access, and calibrated bounded-risk stopping academic terminology analysis

## Product problem

The target is not generic RAG and not generic search. The research object is a controlled evidence-acquisition trajectory:

`explicit unresolved requirement → bounded authorized retrieval → source/version/time-mapped evidence or typed failure → reassess evidence sufficiency → retrieve again, answer, abstain, or terminate because a limit or terminal condition was reached`

Four distinctions are especially important for gap-closure round 2.

First, **query formulation and retrieval control are different tasks**. Conversational query rewriting and question decontextualization can express a known need more clearly, but they do not establish that retrieval is warranted, identify the missing evidence, or decide that enough evidence has arrived.

Second, **retrieval relevance and evidence sufficiency are different tasks**. The closest direct terminology is now *structured sufficiency and gap judging*, *evidence sufficiency verification*, *evidence coverage*, and *retrieval stopping*. S2G-RAG is particularly important because it makes the missing-information state explicit, but its current structured schema is intentionally limited and does not close temporal-constraint, multi-entity-join, or richer compositional gaps.

Third, **freshness, version lineage, provenance, and temporal validity are separate concepts**. Temporal IR supplies time-sensitive retrieval terminology; version-aware retrieval supplies evolving-document selection; provenance supplies source lineage; and temporal-database research supplies the crucial distinction between **valid time** and **transaction time**. For msgloom, this is materially more precise than simply searching for “latest” or “fresh” documents.

Fourth, **confidence-based stopping is not yet bounded-risk stopping under shift**. The appropriate transfer literature is selective prediction, the reject option, risk-coverage analysis, calibration under domain shift, risk-controlling prediction, and conformal risk control. These methods provide useful statistical machinery, but they do not by themselves establish correctness of an iterative RAG stopping controller.

The round-2 terminology should therefore search both the direct retrieval-controller literature and carefully labelled transfer literatures for temporal semantics, provenance, authorization, and statistical risk control.

## Seed keyword audit

| Seed | Academic meaning | Fit | Main risk |
| --- | --- | --- | --- |
| conversational query rewriting | Rewrites a context-dependent conversational turn into a standalone retrieval query. | MODERATE | Solves expression of an existing need, not evidence-need detection or stopping. |
| query reformulation | Broad modification of queries through rewriting, expansion, reduction, feedback, or clarification. | MODERATE | Far broader than targeted evidence-gap completion. |
| query resolution | Ambiguous phrase covering several unrelated meanings rather than a stable task family. | WEAK | High lexical noise from databases, DNS, entity resolution, and generic ambiguity resolution. |
| conversational search | Multi-turn interactive information seeking. | MODERATE | Umbrella field; most work lacks explicit gaps, sufficiency, and bounded investigation. |
| context-aware search | Retrieval conditioned on contextual variables such as session, task, user, or location. | WEAK | “Context” usually means personalization or session history rather than missing evidence. |
| question decontextualization | Makes a context-dependent question self-contained while preserving meaning. | MODERATE | Usually assumes the required conversational context is already available. |
| retrieval-augmented generation | Generation conditioned on retrieved external information. | MODERATE | Generic RAG is dominated by fixed one-shot top-k pipelines. |
| adaptive retrieval augmented generation | Dynamically chooses whether, when, how, or how much to retrieve. | STRONG | Adaptation may be only routing among fixed strategies rather than an explicit evidence loop. |
| active retrieval augmented generation | Triggers retrieval during generation/reasoning instead of only once at the start. | STRONG | Triggers may be token-confidence heuristics rather than structured evidence needs. |
| iterative retrieval | Uses results from one retrieval round to influence later retrieval. | STRONG | Iteration does not guarantee sufficiency, typed failure, provenance, or stopping reliability. |
| self-directed retrieval | Informal label for models deciding their own retrieval actions. | WEAK | Not standardized and attracts autonomous-agent literature. |
| multi-hop retrieval | Retrieves dependent evidence pieces across multiple hops. | STRONG | Often assumes fixed small hop counts and stable public corpora. |
| iterative multi-hop question answering | Alternates retrieval and reasoning for dependent QA steps. | STRONG | QA benchmarks simplify versions, permissions, failures, and workplace evidence. |
| retrieval planning | Plans subqueries, sources, ordering, or retrieval strategies. | STRONG | Planning may optimize answer accuracy without evidence-completeness or stopping guarantees. |
| evidence acquisition | Gathering information needed to support inference or a decision. | MODERATE | Cross-disciplinary phrase with substantial legal, medical, and scientific noise. |
| tool-use planning | Plans external tool calls or actions. | MODERATE | Much broader and more autonomous than bounded read-only retrieval. |
| query-focused evidence retrieval | Descriptive rather than well-standardized task name. | WEAK | Exact terminology may miss the literature's actual labels. |
| temporal information retrieval | Models temporal intent, temporal relevance, document time, recency, and dynamic collections. | STRONG | Often models publication time or freshness rather than effective validity. |
| time-aware retrieval | Broad retrieval using temporal information. | STRONG | Can silently collapse multiple distinct clocks. |
| recency-aware retrieval | Promotes fresh information for recency-sensitive needs. | MODERATE | Newest does not mean valid for the requested historical/effective time. |
| version-aware retrieval | Retrieves among explicit versions of evolving source documents or data. | STRONG | Emerging terminology; “version-aware” can refer to model/software versions instead. |
| provenance-aware retrieval | Uses or retains information about information origin and lineage. | MODERATE | Provenance research often studies derivation rather than retrieval control. |
| unanswerability detection | Determines that supplied evidence or a knowledge source cannot support an answer. | MODERATE | Usually collapses many failure causes into one no-answer state. |
| answerability prediction | Predicts whether available evidence can answer a question. | MODERATE | Typically operates on fixed context and does not specify the next retrieval action. |
| selective question answering | QA with abstention, commonly evaluated through risk versus coverage. | STRONG | Controls answer emission, not necessarily whether retrieval should continue. |
| answer abstention | Refuses or defers answering when support/confidence is inadequate. | STRONG | Premature abstention can replace a useful bounded retrieval step. |
| retrieval stopping criterion | Decides when an iterative retrieval trajectory should stop. | STRONG | Existing criteria can be heuristic, uncalibrated, or benchmark-specific. |
| budgeted retrieval | Performs retrieval subject to a document, hop, token, compute, latency, or monetary budget. | STRONG | Efficiency can conceal missed evidence unless unsafe stopping is measured separately. |
| cost-aware retrieval | Incorporates action or processing costs into retrieval decisions. | STRONG | Frequently measures only one cost component rather than end-to-end investigation cost. |
| enterprise search | Search over proprietary heterogeneous organizational information. | MODERATE | Most work concerns ranking, indexing, governance, or UX rather than evidence-gap loops. |
| access-controlled retrieval | Restricts retrieval according to ACL/RBAC/ABAC or equivalent authorization. | STRONG | Authorization enforcement alone does not test replenishment after denied candidates. |
| evidence sufficiency estimation | Judges whether accumulated evidence is enough to support an answer or required claims. | STRONG | Scalar/binary sufficiency can hide the exact missing requirement and can drift under shift. |

The most important terminology changes are therefore:

**Promote:** structured sufficiency and gap judging; structured gap items; evidence sufficiency verification; set-level evidence sufficiency; evidence coverage; claim-evidence coverage; retrieval control; retrieval stopping policy; stop/continue criterion; retrieval utility; budget-aware active RAG; selective prediction; reject option; risk-coverage; conformal risk control; valid time; transaction time; bitemporal data; as-of query; temporal validity; document evolution; versioned-document QA; version lineage; data provenance; where provenance; authorization-aware retrieval; permission-constrained retrieval; document-level access control; query-time access control; knowledge-source incompleteness; query decomposition; subquestion generation; bridge-entity retrieval; and retrieval-reasoning process.

**Demote as primary search terms:** query resolution; context-aware search; self-directed retrieval; query-focused evidence retrieval; generic RAG; generic enterprise search; recency-aware retrieval when the requirement is temporal validity; and generic tool-use planning.

## Academic task families

### TF1 — Structured evidence-gap representation and evidence sufficiency judging — DIRECT

This is the closest match to the product's control state: determine whether accumulated evidence is sufficient and, if not, represent exactly what is still missing.

High-confidence seed papers:

- *S2G-RAG: Structured Sufficiency and Gap Judging for Iterative Retrieval-Augmented QA* (ACL 2026).
- *SURE-RAG: Sufficiency and Uncertainty-Aware Evidence Verification for Selective Retrieval-Augmented Generation* (arXiv preprint, 2026).

Round 2 should specifically search for richer gap representations involving temporal constraints, multi-entity joins, several intermediate variables, compositional constraints, claim sets, and query decomposition. A binary sufficiency output without a structured missing requirement is useful for stopping research but does not close gap-1.

### TF2 — Iterative multi-hop retrieval and retrieval-reasoning control — DIRECT

This family studies dependent evidence acquisition where later queries depend on earlier retrieval or reasoning.

High-confidence seeds include:

- *PullNet: Open Domain Question Answering with Iterative Retrieval on Knowledge Bases and Text* (2019).
- *Interleaving Retrieval with Chain-of-Thought Reasoning for Knowledge-Intensive Multi-Step Questions* / IRCoT (ACL 2023).
- *Active Retrieval Augmented Generation* / FLARE (EMNLP 2023).
- *Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection* (ICLR 2024).
- *Adaptive-RAG: Learning to Adapt Retrieval-Augmented Large Language Models through Question Complexity* (NAACL 2024).

This is the core literature for multi-hop dependency, query planning, bridge entities, query decomposition, and iterative evidence acquisition. Fixed-hop methods must not be mistaken for validated adaptive stopping.

### TF3 — Adaptive retrieval stopping, evidence coverage, utility, and hard budgets — DIRECT

This family asks whether another retrieval action is worthwhile and when accumulated evidence is sufficient enough to terminate.

High-confidence seeds include:

- *Re3MHQA: Retrieve, Remove, and Return facts in multi-hop QA* (2025).
- *Stop-RAG: Value-Based Retrieval Control for Iterative RAG* (arXiv preprint, 2025).
- *When Should Active RAG Retrieve? A Budget-Aware Evaluation of Utility, Calibration, and Cost* (arXiv preprint, 2026).
- *HALT: Verification-Aware Stopping for Retrieval-Augmented Search Agents* (arXiv preprint, 2026).

For gap-3, discovery should favor **stop/continue policy**, **evidence coverage**, **retrieval utility**, **realized retrieval budget**, **threshold-transfer error**, and **unsafe early stopping** over vague “confidence” terminology.

### TF4 — Selective prediction, abstention, calibration, and risk control under shift — TRANSFER

This is the theoretical/statistical transfer family for bounded-risk stopping.

Relevant foundations include:

- C. K. Chow, *On Optimum Recognition Error and Reject Tradeoff* (1970).
- *SelectiveNet: A Deep Neural Network with an Integrated Reject Option* (ICML 2019).
- *Selective Question Answering under Domain Shift* (ACL 2020).
- *Distribution-free, Risk-controlling Prediction Sets* (JACM 2021).
- *Conformal Risk Control* (ICLR 2024).

The terminology that matters is **reject option**, **selective prediction**, **risk-coverage trade-off**, **calibration under domain shift**, **risk-controlling prediction**, **learn-then-test**, and **conformal risk control**.

These results are transfer evidence only until a retrieval-controller-specific experiment defines the loss corresponding to unsafe stopping and validates the calibration assumptions.

### TF5 — Temporal information retrieval — DIRECT

Temporal IR studies temporal intent, time-sensitive relevance, dynamic collections, recency-sensitive queries, and temporal ranking.

Useful anchors include the 2014 *Survey of Temporal Information Retrieval and Related Applications* and the 2015 *Temporal Information Retrieval* survey.

The critical qualification for msgloom is:

`recency/freshness ≠ effective-time validity`

A document can be newest while describing a fact that was not valid at the time relevant to the question.

### TF6 — Valid time, transaction time, and bitemporal semantics — TRANSFER

This database literature is the strongest terminology for the time semantics required by gap-2.

Its central distinction is:

- **valid time**: when a fact is true in the modeled reality;
- **transaction time**: when the information is stored/recorded by the system.

Relevant foundations occur in the 1990s, including work on transaction versus valid time, temporal validity, bitemporal relations, and time-varying information.

For msgloom this maps naturally onto the need to avoid collapsing message time, effective time, collection time, document-version time, and later corrections into one timestamp.

### TF7 — Versioned-document retrieval and document evolution — DIRECT

The preferred terminology is **version-aware retrieval**, **versioned document QA**, **document evolution**, **change-aware retrieval**, **version lineage**, and **historical version retrieval**.

A high-confidence recent seed is *VersionRAG: Version-Aware Retrieval-Augmented Generation for Evolving Documents* (arXiv preprint, 2025).

This family should be combined with TF6. Knowing the source version is necessary but not sufficient: the controller must still determine whether that version is temporally valid for the question.

### TF8 — Data provenance and source lineage — TRANSFER

Database provenance provides rigorous language for origin and derivation. A foundational seed is:

- *Why and Where: A Characterization of Data Provenance* (ICDT 2001).

Useful promoted terms are **data provenance**, **where provenance**, **source lineage**, **evidence provenance**, and **temporal provenance**.

Provenance is not itself a retrieval policy. Admit it as direct support only when provenance actually survives retrieval and constrains or audits evidence use.

### TF9 — Authorization-aware and permission-constrained retrieval — DIRECT

This family covers retrieval whose candidate universe depends on the requesting principal's authorization.

Useful terminology includes:

- access-controlled retrieval;
- authorization-aware retrieval;
- permission-constrained retrieval;
- document-level access control;
- query-time access control;
- ACL/RBAC/ABAC retrieval;
- security trimming;
- authorization predicates in vector retrieval.

Relevant foundations include *Access control for large collections* (TOIS, 1997), while recent vector-database work such as *HONEYBEE: Efficient Role-based Access Control for Vector Databases via Dynamic Partitioning* (2026) addresses modern retrieval infrastructure.

For gap-4, simple authorization filtering is not enough. The target experiment must look like:

`retrieve candidates → enforce native authorization → retain authorized evidence → reassess structured sufficiency → issue a new permission-constrained retrieval if required`

### TF10 — Answerability, unanswerability, and incomplete knowledge sources — TRANSFER

This literature is useful for distinguishing insufficient evidence from a supported answer.

Important seeds include:

- *Know What You Don't Know: Unanswerable Questions for SQuAD* (2018).
- *Challenges in Information-Seeking QA: Unanswerable Questions and Paragraph Retrieval* (ACL 2021).
- *Do I have the Knowledge to Answer? Investigating Answerability of Knowledge Base Questions* (ACL 2023).
- *Detecting (Un)answerability in Large Language Models with Linear Directions* (EACL 2026).

For gap-5, binary answerable/unanswerable labels are insufficient. Discovery should favor studies that analyze **why** information is unavailable: missing facts, incomplete knowledge source, retrieval failure, evidence insufficiency, or unsupported context.

### TF11 — Conversational query reformulation and decontextualization — TRANSFER

Relevant seeds include:

- *Can You Unpack That? Learning to Rewrite Questions-in-Context* (2019).
- *Explicit Query Rewriting for Conversational Dense Retrieval* (2022).
- *ConvGQR: Generative Query Reformulation for Conversational Search* (ACL 2023).

The appropriate role in msgloom is downstream of gap identification:

`structured missing requirement → retrieval-oriented query reformulation`

It must not be used as a substitute for the decision that evidence is missing.

### TF12 — Bounded tool-use and information-gathering planning — TRANSFER

General agent planning may provide mechanisms for choosing a sequence of reads or searches. *ReAct: Synergizing Reasoning and Acting in Language Models* (ICLR 2023) is a useful broad seed.

This family should be tightly filtered. The target is not autonomous browsing; it is a bounded, read-only, authorization-preserving evidence-acquisition controller.

### TF13 — Enterprise and workplace information retrieval — DIRECT

Enterprise search studies proprietary, heterogeneous organizational corpora, governance, organizational metadata, and user-specific visibility.

Useful domain anchors include:

- *Enterprise Search: Tough Stuff: Why is it that searching an intranet is so much harder than searching the Web?* (2004).
- *Enterprise search: A state of the art* (2019).

This family is necessary for gap-7, but ordinary intranet ranking does not constitute evidence for an iterative controller. Direct-domain papers should receive high value only if they also exercise evidence incompleteness, heterogeneous documents/messages, permissions, conflicting or stale sources, and bounded retrieval.

### TF14 — Integrated adaptive evidence-retrieval controller — DIRECT

This is the exact gap-8 target:

`structured gap + iterative planning + permission-aware source access + document/version lineage + effective-time validity + provenance + calibrated stop/abstain + total budget`

This query family should be run even if discovery finds no qualifying paper. The absence of an integrated result is itself different from failing to search for one.

Component papers must not be combined inferentially to claim that this complete controller has been validated.

## Query families

### TF1 — Structured gap and sufficiency — DIRECT

- `"structured sufficiency" "gap" iterative retrieval RAG`
- `"structured gap" evidence sufficiency multi-hop retrieval`
- `"missing information" "evidence sufficiency" iterative RAG`
- `"evidence sufficiency verification" retrieval augmented generation`
- `"evidence coverage" multi-hop retrieval stopping`
- `"gap judging" retrieval augmented QA`
- `"structured evidence" temporal constraints multi-entity compositional retrieval`
- `"multi-entity" compositional question answering iterative retrieval sufficiency`
- `"query decomposition" "evidence coverage" multi-hop RAG`
- `"claim decomposition" retrieval evidence completeness multi-hop`

### TF2 — Iterative multi-hop control — DIRECT

- `"iterative retrieval" multi-hop question answering stopping`
- `"multi-hop retrieval" retrieval planning sufficiency`
- `"retrieval reasoning" process stop continue multi-hop QA`
- `"interleaving retrieval" reasoning multi-step question answering`
- `"adaptive RAG" iterative retrieval question complexity`
- `"active retrieval augmented generation" iterative`
- `"retrieval planning" multi-hop QA next query`
- `"subquestion generation" iterative retrieval multi-hop evidence`
- `"bridge entity" iterative retrieval query generation`
- `"compositional question answering" iterative retrieval evidence`

### TF3 — Stopping, utility, and budget — DIRECT

- `"retrieval stopping" iterative RAG`
- `"stopping policy" multi-hop retrieval RAG`
- `"when to stop" iterative retrieval question answering`
- `"evidence coverage" stopping retrieval augmented`
- `"value-based" retrieval stopping RAG`
- `"budget-aware" active RAG retrieval`
- `"hard budget" multi-round retrieval RAG`
- `"retrieval utility" adaptive RAG cost`
- `"adaptive retrieval" calibration cost budget`
- `"retrieval reduction" sufficiency multi-round RAG`
- `"retrieval stopping" domain shift calibration RAG`
- `"unsafe early stop" retrieval augmented generation`

### TF4 — Selective risk and calibration — TRANSFER

- `"selective question answering" domain shift`
- `"selective prediction" domain shift risk coverage`
- `"reject option" calibration distribution shift`
- `"answer abstention" calibration question answering`
- `"risk coverage" question answering abstention`
- `"conformal risk control" question answering abstention`
- `"risk-controlling" prediction abstention domain shift`
- `"learn then test" risk control abstention`
- `"high probability risk control" covariate shift`
- `"calibration transfer" abstention domain shift`

### TF5 — Temporal IR — DIRECT

- `"temporal information retrieval" time-sensitive queries`
- `"temporal information retrieval" evolving documents`
- `"time-aware retrieval" temporal query intent`
- `"recency-sensitive queries" information retrieval freshness`
- `"temporal relevance" information retrieval document time`
- `"temporal question answering" retrieval evolving facts`
- `"as-of" question answering retrieval temporal`
- `"historical question answering" temporal retrieval`

### TF6 — Bitemporal/effective-time validity — TRANSFER

- `"valid time" "transaction time" information retrieval`
- `"valid time" "transaction time" question answering`
- `"bitemporal" retrieval information access`
- `"bitemporal" question answering`
- `"effective time" document retrieval provenance`
- `"temporal validity" retrieval document versions`
- `"as-of query" provenance version history`
- `"retroactive update" temporal query provenance`

### TF7 — Versioned documents — DIRECT

- `"version-aware retrieval" evolving documents`
- `"version-aware RAG" evolving documents`
- `"versioned document QA" retrieval`
- `"document evolution" retrieval augmented generation`
- `"document version" question answering historical`
- `"change-aware retrieval" document versions`
- `"version lineage" retrieval question answering`
- `"historical version" RAG retrieval`
- `"temporal validity" "version-aware" RAG`

### TF8 — Provenance and lineage — TRANSFER

- `"data provenance" information retrieval lineage`
- `"evidence provenance" retrieval augmented generation`
- `"source provenance" iterative retrieval`
- `"provenance-aware retrieval" document`
- `"temporal provenance" document retrieval`
- `"version provenance" document retrieval`
- `"where provenance" evidence extraction retrieval`
- `"source lineage" RAG evidence`

### TF9 — Permission-constrained retrieval — DIRECT

- `"access-controlled retrieval" information retrieval`
- `"authorization-aware retrieval" documents`
- `"permission-aware retrieval" RAG`
- `"permission-aware RAG" enterprise`
- `"document-level access control" information retrieval`
- `"query-time access control" retrieval`
- `"security trimming" enterprise search retrieval`
- `"role-based access control" vector retrieval`
- `"attribute-based access control" document retrieval`
- `"access control" vector database nearest neighbor retrieval`
- `"iterative retrieval" authorization permissions`
- `"multi-hop retrieval" access control permissions`

### TF10 — Failure-aware answerability — TRANSFER

- `"unanswerability detection" retrieval augmented`
- `"answerability prediction" information seeking retrieval`
- `"unanswerable questions" paragraph retrieval`
- `"knowledge base incompleteness" unanswerable question answering`
- `"missing facts" unanswerable question answering`
- `"incomplete evidence" answerability abstention`
- `"retrieval failure" answerability question answering`
- `"no evidence" abstention retrieval augmented generation`
- `"insufficient evidence" abstention RAG`
- `"unsupported evidence" answerability retrieval`

### TF11 — Conversational reformulation — TRANSFER

- `"conversational query rewriting" retrieval`
- `"conversational query reformulation" retrieval`
- `"question decontextualization" conversational search`
- `"question-in-context rewriting" retrieval`
- `"explicit query rewriting" conversational dense retrieval`
- `"missing antecedent" query reformulation retrieval`
- `"ellipsis" coreference conversational retrieval query rewriting`

### TF12 — Bounded tool planning — TRANSFER

- `"tool-use planning" information retrieval search`
- `"information gathering" agent planning retrieval budget`
- `"search planning" language model multi-step retrieval`
- `"read-only" tool use planning retrieval`
- `"bounded" information gathering agent retrieval`
- `"planning" search actions evidence acquisition language model`

### TF13 — Enterprise/workplace retrieval — DIRECT

- `"enterprise search" permissions provenance documents`
- `"enterprise search" email attachments access control`
- `"enterprise RAG" access control provenance`
- `"enterprise RAG" versioned documents permissions`
- `"workplace communication" retrieval augmented generation evidence`
- `"email search" missing context evidence retrieval`
- `"organizational search" access control heterogeneous documents`
- `"enterprise information retrieval" permission document versions`
- `"workplace" multi-hop retrieval email documents`
- `"enterprise search" stale conflicting information`

### TF14 — Integrated controller — DIRECT

- `"enterprise RAG" permission-aware provenance temporal adaptive retrieval`
- `"enterprise RAG" calibrated stopping abstention access control`
- `"agentic RAG" access control temporal provenance stopping`
- `"iterative RAG" version-aware permission-aware retrieval`
- `"retrieval controller" evidence sufficiency access control provenance`
- `"adaptive RAG" provenance temporal access control`
- `"adaptive retrieval" authorization version lineage sufficiency`
- `"evidence gap" permission temporal provenance retrieval`
- `"bounded retrieval" permissions provenance abstention`
- `"retrieval controller" calibrated stopping domain shift cost`
- `"iterative retrieval" valid time version lineage authorization`
- `"adaptive evidence retrieval" permissions versions temporal validity`

## False friends and downgrade rules

1. Generic one-shot RAG with fixed top-k retrieval is not evidence for an adaptive controller.
2. Query rewriting is not evidence-need detection.
3. A fixed number of retrieval hops is not a validated stopping policy.
4. A confidence threshold is not a calibrated bounded-risk stopping guarantee.
5. Passage relevance or entailment is not set-level evidence completeness.
6. Binary sufficiency is weaker than a structured missing-evidence representation when the question is what to retrieve next.
7. S2G-style simple gap slots must not be generalized to temporal constraints, multi-entity joins, or complex compositional requirements without direct evaluation.
8. Freshness and recency must not be treated as effective-time validity.
9. Publication time must not stand in for valid time, message time, collection time, or source-version time.
10. “Version-aware” work about model/software versions must not enter the document-version corpus.
11. Provenance work that computes derivation but never preserves evidence lineage through retrieval is TRANSFER, not proof of the target controller.
12. Research about retrieving access-control policies is not the same as retrieving content under access constraints.
13. Permission filtering alone does not close gap-4 unless the system reassesses sufficiency and replenishes from the remaining authorized corpus.
14. Zero results must not be interpreted as negative evidence. Empty retrieval, denied authorization, unavailable source, unsupported extraction, exhausted budget, and true negative evidence are distinct states.
15. Binary unanswerability datasets do not close gap-5 unless the source of unanswerability is represented or experimentally distinguishable.
16. Abstention is not retrieval stopping if the system has no option to conduct another bounded retrieval first.
17. Risk-control results whose guarantee assumes exchangeability must not be described as guarantees under distribution shift unless shift is explicitly handled.
18. Retrieval count or retrieved-token count alone does not constitute the end-to-end cost accounting required by gap-6.
19. ANN throughput, chunking, embedding, and reranking benchmarks are secondary unless they change missed-evidence risk, authorization correctness, temporal/version correctness, or total investigation cost.
20. Generic enterprise search is not direct evidence for the msgloom investigation loop unless explicit gaps, heterogeneous sources, permissions, stale/conflicting evidence, and bounded retrieval are exercised.
21. Unlimited web/agent browsing is outside the intended capability.
22. Systems that discard source identifiers, version identifiers, or retrieval trajectory state cannot support the required auditability.
23. Public homogeneous QA results cannot be represented as production workplace accuracy.
24. No collection of separate component results may be used to claim that gap-8's integrated controller has been validated. Integration requires its own evaluation.

For round 2 specifically, discovery should be skeptical of papers that merely share individual words with the target. The admission question should be: **what exact controller capability was experimentally evaluated?**

## Date policy

**Earliest publication year to include: 1970.**

The lower bound is deliberately earlier than RAG.

Gap-3 requires calibrated abstention and bounded-risk stopping. That problem inherits from the classical **reject option** literature, with C. K. Chow's 1970 *On Optimum Recognition Error and Reject Tradeoff* providing a foundational formulation of the error-versus-rejection trade-off. Restricting discovery to the neural or RAG era would silently remove this theoretical lineage.

The other relevant foundations are also older than modern RAG:

- valid-time, transaction-time, and bitemporal database research developed in the late 1980s and 1990s;
- access-control research for large document collections appears by 1997;
- formal database-provenance work is established by 2001;
- conversational question rewriting becomes prominent much later, including CANARD-era work around 2019;
- modern RAG begins in 2020;
- active, adaptive, self-reflective, and structured-gap RAG are primarily 2023–2026 developments.

Therefore discovery should permit **1970–present**, but queries should remain **task-family scoped**. The purpose is not to conduct a generic fifty-year IR search; it is to prevent a recent-year cutoff from deleting the specific foundations needed to reason correctly about abstention risk, temporal validity, provenance, and access control.
