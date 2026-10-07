# Evidence-gap-driven context retrieval and completion for workplace communication academic terminology analysis

## Product problem

Topic 07 is not a generic retrieval-augmented generation problem. Its research object is a controlled investigation loop:

`explicit evidence gap -> bounded retrieval action -> source-mapped result or explicit failure -> reassess the residual gap -> retrieve again or stop`

The key academic question is therefore not simply how to retrieve relevant passages. The literature must jointly inform five decisions:

1. **What exactly is missing?** An unresolved antecedent, owner, object, prerequisite, approval, historical state, attachment version, corroborating evidence, or other explicit information requirement must be converted into a searchable need.
2. **What should be fetched next?** The system may need query reformulation, source selection, decomposition, multi-hop evidence acquisition, or retrieval planning.
3. **Did the new evidence actually close the gap?** Retrieval success is not answer success. A returned document can be irrelevant, stale, contradictory, inaccessible in part, or insufficient.
4. **Should retrieval continue?** Additional acquisition must be justified against residual uncertainty, permissions, temporal validity, retrieval scope, cost, and configured limits.
5. **Why did the loop stop?** `answered`, `budget exhausted`, `access denied`, `source unavailable`, `extraction failed`, and `still unanswerable` are materially different outcomes.

This means the discovery strategy should not use "RAG" as the umbrella term and hope the required capability emerges. The closest literature is distributed across conversational information-need resolution, adaptive retrieval, multi-hop retrieval, selective question answering, sequential information acquisition, temporal IR, provenance/versioned retrieval, and authorization-constrained enterprise search.

A second important distinction is between **DIRECT** and **TRANSFER** evidence. DIRECT families explicitly study a component of the target problem, such as whether more retrieval is required, whether enough evidence exists, how temporal relevance affects retrieval, or how authorization constrains searchable evidence. TRANSFER families offer a mechanism that may be useful but were normally evaluated under a different objective, such as benchmark multi-hop QA or general-purpose agent tool planning.

## Seed keyword audit

| Seed | Academic meaning | Fit | Main risk |
| --- | --- | --- | --- |
| conversational query rewriting | Rewriting a context-dependent conversational request as a stand-alone search query. | STRONG | Usually assumes retrieval is already warranted and does not decide sufficiency or stopping. |
| query reformulation | Broad IR category covering rewriting, expansion, reduction, substitution, and iterative query modification. | MODERATE | Pulls large volumes of generic query-expansion and ranking literature. |
| query resolution | In conversational IR, resolving ellipsis, ambiguity, and context dependence before retrieval. | STRONG | Highly overloaded outside conversational search. |
| conversational search | Multi-turn information seeking through dialogue, retrieval, clarification, and response generation. | MODERATE | Much of the field concerns interaction quality rather than bounded evidence investigation. |
| context-aware search | Retrieval or ranking conditioned on contextual variables. | WEAK | Usually treats context as a relevance feature rather than an explicit evidence gap. |
| question decontextualization | Converting a discourse-dependent question into a stand-alone formulation. | MODERATE | Normally assumes the antecedent context already exists rather than retrieving missing context. |
| retrieval-augmented generation | Generation conditioned on externally retrieved material. | WEAK | Generic RAG is far broader than evidence-gap-driven investigation. |
| adaptive retrieval augmented generation | RAG that varies whether, when, or how retrieval occurs. | STRONG | Adaptation may optimize benchmark accuracy without explicit gap or enterprise semantics. |
| active retrieval augmented generation | Retrieval triggered dynamically during inference or generation. | STRONG | Often model-generation-driven rather than structured evidence-gap-driven. |
| iterative retrieval | Repeated retrieval where earlier results affect later searches. | STRONG | Iteration does not itself provide a sufficiency or stopping criterion. |
| self-directed retrieval | Emerging label for systems deciding autonomously when or how to retrieve. | MODERATE | Not standardized; easily conflated with unrestricted autonomous agents or Self-RAG specifically. |
| multi-hop retrieval | Sequential retrieval of multiple dependent evidence pieces. | STRONG | Benchmark tasks frequently guarantee an answer and use fixed hop structures. |
| iterative multi-hop question answering | Alternating retrieval and reasoning across evidence hops. | MODERATE | Objective is normally answer production rather than permission-preserving investigation. |
| retrieval planning | Planning queries, decompositions, sources, or retrieval actions before or during evidence collection. | STRONG | Modern usage often overlaps broad agent planning and unrestricted browsing. |
| evidence acquisition | Obtaining observations or information necessary to settle a question or decision. | MODERATE | Very broad interdisciplinary phrase rather than a stable IR task name. |
| tool-use planning | Planning external tool/API invocations. | MODERATE | Most tool-use research includes arbitrary actions rather than bounded read-only retrieval. |
| query-focused evidence retrieval | Selecting evidence specifically relevant to a question or claim. | MODERATE | Descriptive phrase; easily collapses into ordinary passage retrieval. |
| temporal information retrieval | Retrieval incorporating temporal intent, evidence time, document time, or time-dependent relevance. | STRONG | Much work models publication recency rather than semantic validity time. |
| time-aware retrieval | Retrieval explicitly using temporal signals in interpretation, filtering, or ranking. | STRONG | Timestamp features may be mistaken for valid-time reasoning. |
| recency-aware retrieval | Retrieval favoring or modeling recently created or modified information. | MODERATE | Newest is not necessarily valid for a historical/effective-time question. |
| version-aware retrieval | Retrieval that distinguishes or selects among revisions of an information object. | STRONG | Terminology is not standardized and attracts software/dataset versioning. |
| provenance-aware retrieval | Retrieval preserving or using source origin, derivation, or lineage. | STRONG | Database-lineage work may not provide a usable evidence address. |
| unanswerability detection | Detecting that available evidence does not support an answer. | STRONG | Closed QA often confuses missing evidence with genuinely unanswerable questions. |
| answerability prediction | Predicting whether current evidence permits an answer. | STRONG | May not identify what is missing or whether another search is worthwhile. |
| selective question answering | Answering only when sufficiently reliable, otherwise abstaining. | STRONG | Provides a stop/abstain decision but usually no acquisition strategy after abstention. |
| answer abstention | Declining to answer when evidence or confidence is insufficient. | STRONG | Does not by itself distinguish denied, unavailable, exhausted, failed, and genuinely unresolved states. |
| retrieval stopping criterion | Rule for terminating retrieval because the need is met or further acquisition is not worthwhile/allowed. | STRONG | Exact terminology is inconsistent and attracts unrelated algorithmic early-termination work. |
| budgeted retrieval | Retrieval constrained by query, document, hop, token, time, compute, or monetary budgets. | STRONG | Budget optimization may ignore unresolved evidence semantics. |
| cost-aware retrieval | Retrieval explicitly modeling acquisition or computational costs. | STRONG | "Cost" frequently means infrastructure efficiency only. |
| enterprise search | Search over heterogeneous organizational repositories with enterprise metadata and access constraints. | MODERATE | Correct domain, but most work is generic ranking, navigation, or knowledge management. |
| access-controlled retrieval | Retrieval constrained by authorization/security policy. | STRONG | Security work often stops at confidentiality enforcement and says nothing about evidence sufficiency. |
| evidence sufficiency estimation | Estimating whether currently available evidence adequately supports an answer or inference. | STRONG | Terminology is fragmented across QA, verification, RAG, and decision theory. |

### Terms to promote

Discovery should add terminology that better isolates the required capability:

- **conversational query resolution**
- **clarification question generation**
- **underspecified information need**
- **retrieval gating**
- **dynamic retrieval**
- **context sufficiency**
- **knowledge insufficiency detection**
- **evidence sufficiency**
- **selective question answering**
- **sequential information acquisition**
- **value of information**
- **resource-constrained retrieval**
- **retrieval stopping rule**
- **temporal relevance**
- **temporal query intent**
- **valid-time retrieval**
- **point-in-time retrieval**
- **document evolution retrieval**
- **evidence provenance**
- **authorization-aware retrieval**
- **permission-aware search**

### Terms to demote as standalone discovery anchors

These terms remain useful only when combined with stronger capability terms:

- retrieval-augmented generation
- context-aware search
- query reformulation
- conversational search
- evidence acquisition
- self-directed retrieval
- tool-use planning
- recency-aware retrieval
- enterprise search

## Academic task families

### F1 — Explicit information-need resolution and conversational query resolution — DIRECT

This family asks how an underspecified need becomes an explicit information request. It includes conversational query resolution, clarification, handling ellipsis or unresolved context, and identifying information required to make the query executable.

This is directly relevant to Topic 07 because upstream Topics deliberately emit unresolved objects rather than guesses. Topic 07 therefore needs to transform something like "antecedent for `it` missing" or "approval owner unresolved" into a concrete, bounded evidence request.

Known seed papers:

- *Can You Unpack That? Learning to Rewrite Questions-in-Context*
- *Query Resolution for Conversational Search with Limited Supervision*

Admission should favor work that represents or resolves an actual information need, not merely work that improves query wording.

### F2 — Conversational query rewriting and question decontextualization — TRANSFER

This family rewrites a context-dependent utterance into a stand-alone search expression.

It is highly useful after Topic 07 has already determined that evidence is missing. It should not be treated as evidence that the system can decide whether investigation is necessary. In particular, decontextualizing a question cannot recover an antecedent that is absent from the available material.

Known seed paper:

- *Can You Unpack That? Learning to Rewrite Questions-in-Context*

### F3 — Adaptive, active, and iterative retrieval-augmented generation — DIRECT

This is the closest modern family to the intended investigation loop. Relevant systems dynamically decide whether to retrieve, retrieve additional material during inference, critique what was retrieved, or alter later retrieval based on what is still missing.

Known seed papers:

- *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*
- *Active Retrieval Augmented Generation*
- *Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection*
- *Adaptive-RAG: Learning to Adapt Retrieval-Augmented Large Language Models through Question Complexity*

The important distinction is between **dynamic retrieval** and merely having a retriever. Fixed top-k RAG should normally be downgraded.

A second admission criterion is whether the method permits unresolved termination. A benchmark system that always generates an answer after retrieval does not establish Topic 07's required behavior.

### F4 — Multi-hop retrieval and iterative evidence chaining — TRANSFER

This literature models retrieval where one result exposes the next subquestion or evidence dependency.

Known seed papers include:

- *HotpotQA: A Dataset for Diverse, Explainable Multi-hop Question Answering*
- *Multi-hop Dense Retrieval for Open-domain Question Answering*
- *Interleaving Retrieval with Chain-of-Thought Reasoning for Knowledge-Intensive Multi-Step Questions*

This transfers directly to cases such as:

`message -> referenced decision -> referenced attachment -> historically valid attachment version -> required evidence`

However, standard multi-hop QA assumptions are dangerous for msgloom. Many datasets guarantee answer existence, predefine the corpus, or implicitly assume successful access. Topic 07 must support missing, denied, inaccessible, stale, and contradictory hops.

### F5 — Retrieval planning and read-only tool-use planning — TRANSFER

This family concerns selecting the next search/read operation, decomposing questions, choosing a source, and sequencing retrieval actions.

Known seed papers:

- *ReAct: Synergizing Reasoning and Acting in Language Models*
- *Toolformer: Language Models Can Teach Themselves to Use Tools*

The transfer boundary must be explicit. Topic 07 wants bounded, inspectable, primarily read-only investigation. General agents that execute arbitrary computer actions or roam the web without scope constraints should not be treated as direct evidence.

### F6 — Answerability, unanswerability, selective QA, abstention, and evidence sufficiency — DIRECT

This family supplies the semantic foundation for deciding whether retrieval has actually solved the gap.

Known seed papers:

- *Know What You Don't Know: Unanswerable Questions for SQuAD*
- *Selective Question Answering under Domain Shift*

The central project distinction is:

`retrieval returned something != sufficient evidence exists`

A search can succeed technically while returning stale, irrelevant, contradictory, weak, or incomplete evidence. Topic 07 therefore needs sufficiency assessment after every meaningful retrieval step.

The literature should be searched beyond the literal term "evidence sufficiency", because closely related work may call the problem **context sufficiency**, **answerability**, **knowledge insufficiency**, **selective QA**, or **abstention**.

### F7 — Budgeted, cost-aware, and value-of-information retrieval — DIRECT

This family asks whether an additional information-acquisition step is worth its cost and how retrieval should operate under explicit resource limits.

This is a direct match for Topic 07's requirement that more retrieval is not automatically better. Relevant costs may include:

- number of searches;
- number of source reads;
- number of hops;
- document-processing cost;
- model/token cost;
- latency;
- user/report delay;
- permission-bound source availability.

Discovery should deliberately include **value of information** and **sequential information acquisition** terminology. Important stopping theory may exist outside work labelled "RAG".

A budget limit is not an evidential conclusion. The resulting state must remain `unresolved because budget exhausted`, not `false`, `absent`, or `answered`.

### F8 — Temporal information retrieval and temporal validity — DIRECT

Temporal IR is required because Topic 07 must not assume the newest available evidence is the correct evidence.

Known seed paper:

- *Time-Based Language Models*

The search should distinguish at least:

- message/publication time;
- event or effective time;
- deadline time;
- document revision time;
- collection/indexing time;
- the time about which the question is asked.

Recency-only work is useful but insufficient. A historical state question may require an older version even when a newer document is available.

### F9 — Version-aware and provenance-aware retrieval — DIRECT

This family covers retrieval over evolving information and preservation of the identity and derivation of the evidence returned.

Topic 07 needs enough provenance to say, in effect:

`this retrieval read this source object, in this version/revision state, under this access result, at this point in the investigation`

Topic 08 still owns interpretation and precise page/region/cell grounding after an artifact is fetched. Topic 07 should therefore not absorb document understanding, but it must preserve the version/source identity passed across that boundary.

The terminology is fragmented. Discovery should search document evolution, versioned corpora, temporal archives, provenance, and evidence lineage rather than assuming the phrase "version-aware retrieval" names one mature field.

### F10 — Enterprise retrieval with authorization and access constraints — DIRECT

Enterprise search is relevant because the deployment domain consists of permission-constrained organizational sources rather than an unrestricted public corpus.

The critical capability is not simply filtering unauthorized results. Topic 07 must preserve **why evidence was unavailable**. These outcomes are semantically different:

- authorized query, no matching result;
- matching object exists but read denied;
- source unavailable;
- attachment unavailable;
- source not searched because outside the permitted scope.

Security literature that only proves confidentiality enforcement is therefore insufficient by itself, but authorization-aware retrieval is a direct part of the product requirement.

## Query families

### F1 — Explicit information-need resolution and conversational query resolution — DIRECT

- `"conversational query resolution" information need retrieval`
- `"query resolution" conversational search context dependent`
- `"conversational search" clarification information need retrieval`
- `"clarification question" conversational search missing information`
- `"underspecified query" conversational search clarification`
- `"information need" missing context conversational retrieval`

### F2 — Conversational query rewriting and decontextualization — TRANSFER

- `"conversational query rewriting" retrieval`
- `"question rewriting" conversational search retrieval`
- `"question decontextualization" conversational search`
- `"context dependent query" rewrite conversational retrieval`
- `"standalone question" rewriting conversational QA retrieval`

### F3 — Adaptive, active, and iterative RAG — DIRECT

- `"adaptive retrieval" retrieval augmented generation`
- `"adaptive RAG" retrieval decision`
- `"active retrieval augmented generation"`
- `"active retrieval" language model evidence`
- `"iterative retrieval" RAG evidence`
- `"dynamic retrieval" RAG when to retrieve`
- `"retrieval gating" retrieval augmented generation`
- `"Self-RAG" retrieve critique`
- `"retrieval augmented generation" evidence sufficiency retrieve again`

### F4 — Multi-hop retrieval and evidence chaining — TRANSFER

- `"multi-hop retrieval" iterative evidence`
- `"iterative multi-hop" question answering retrieval`
- `"multi-hop question answering" adaptive retrieval`
- `"multi-hop retrieval" stopping`
- `"iterative retrieval" multi-step question answering`
- `"interleaving retrieval" reasoning multi-step`

### F5 — Retrieval planning and read-only tool planning — TRANSFER

- `"retrieval planning" information retrieval language model`
- `"retrieval plan" question answering evidence`
- `"search planning" question answering retrieval`
- `"tool use planning" information retrieval language model`
- `"tool-use" retrieval planning evidence`
- `"query planning" multi-step retrieval`
- `"source selection" multi-source question answering retrieval`

### F6 — Answerability, abstention, and evidence sufficiency — DIRECT

- `"unanswerability detection" retrieval`
- `"unanswerable question" retrieval augmented generation`
- `"answerability prediction" retrieval question answering`
- `"selective question answering" retrieval`
- `"answer abstention" retrieval evidence`
- `"evidence sufficiency" question answering`
- `"evidence sufficiency" retrieval augmented generation`
- `"context sufficiency" RAG answerability`
- `"insufficient evidence" retrieval question answering`
- `"knowledge insufficiency" retrieval augmented generation`

### F7 — Budget, cost, value, and stopping — DIRECT

- `"budgeted retrieval" information retrieval`
- `"cost-aware retrieval" information retrieval`
- `"resource-constrained retrieval" information seeking`
- `"retrieval stopping" question answering`
- `"stopping criterion" iterative retrieval`
- `"when to stop retrieving" retrieval augmented generation`
- `"retrieval budget" RAG`
- `"value of information" information retrieval search`
- `"value of information" sequential information acquisition`
- `"expected value" additional evidence retrieval`

### F8 — Temporal information retrieval — DIRECT

- `"temporal information retrieval"`
- `"time-aware retrieval" information retrieval`
- `"temporal query" document retrieval`
- `"temporal relevance" information retrieval`
- `"historical query" temporal retrieval document`
- `"point-in-time" information retrieval`
- `"valid time" document retrieval`
- `"effective time" information retrieval`
- `"freshness-aware retrieval" temporal relevance`
- `"recency-aware retrieval" temporal`

Search results using only recency should be retained only when they genuinely inform temporal relevance; they must not be allowed to collapse "valid at the requested time" into "newest available".

### F9 — Versions and provenance — DIRECT

- `"version-aware retrieval" document`
- `"document version" information retrieval provenance`
- `"versioned document" retrieval`
- `"document evolution" information retrieval`
- `"version-aware" search document`
- `"provenance-aware retrieval"`
- `"data provenance" information retrieval evidence`
- `"source provenance" retrieval question answering`
- `"evidence provenance" retrieval augmented generation`
- `"temporal archive" version retrieval document`

### F10 — Enterprise and access-controlled retrieval — DIRECT

- `"enterprise search" access control retrieval`
- `"enterprise search" permissions information retrieval`
- `"access-controlled retrieval" search`
- `"authorization-aware" information retrieval`
- `"permission-aware search" enterprise`
- `"security-aware retrieval" enterprise search`
- `"document retrieval" access control enterprise`
- `"federated enterprise search" permissions`
- `"multi-source enterprise search" authorization`

## False friends and downgrade rules

Discovery should downgrade or exclude literature that matches the vocabulary without supplying the capability Topic 07 needs.

1. **Fixed retrieval is not adaptive retrieval.** Generic RAG with unconditional or fixed top-k retrieval should be downgraded unless the paper contributes directly to evidence-gap closure.

2. **Rewrite quality is not retrieval-need detection.** Query rewriting, question rewriting, and decontextualization should be TRANSFER evidence when they assume the decision to search has already been made.

3. **Generic query improvement is out of scope.** Query expansion, pseudo-relevance feedback, spelling correction, synonym expansion, and search-engine ranking improvements are not Topic 07 evidence unless embedded in a sequential attempt to close an explicit gap.

4. **Conversational UX is not evidence acquisition.** Dialogue naturalness, engagement, recommendation conversations, and general response generation should not be admitted solely because they use the phrase conversational search.

5. **A fixed number of hops is not a stopping rule.** Multi-hop systems that always perform two hops, N hops, or retrieve N documents have a budget baseline, not evidence-sensitive stopping.

6. **Guaranteed-answer QA is weaker evidence.** Multi-hop benchmarks that guarantee the evidence exists should normally be classified TRANSFER because they do not exercise source absence, denial, or unresolved termination.

7. **Unlimited agents are false friends.** Autonomous web agents with broad browsing authority and no bounded source policy should not count as direct solutions to Topic 07.

8. **Arbitrary tool execution is not read-only retrieval.** Tool-use planning centered on code execution, transactions, robotics, or state-changing actions should be downgraded.

9. **Confidence alone is not sufficiency.** Calibration work that merely assigns a confidence score without an abstention or evidence-sufficiency interpretation is insufficient.

10. **Safety refusal is not evidential abstention.** Refusal caused by policy, toxicity, or alignment must not be conflated with abstention because evidence is missing.

11. **Closed-passage no-answer detection is incomplete.** An unanswerable QA classifier that receives one fixed passage does not establish that a system can distinguish failed retrieval, denied retrieval, and genuine lack of evidence.

12. **Compute cost is not investigation cost.** ANN efficiency, indexing memory, GPU throughput, serving latency, and generic token reduction should be downgraded unless the cost influences a sequential evidence decision.

13. **Freshest is not temporally valid.** Recency boosting alone does not solve historical or effective-time retrieval.

14. **One timestamp is not sufficient temporal modelling.** Work that treats publication timestamp as the only temporal dimension should not be generalized to message/effective/deadline/version time without evidence.

15. **Software-version resolution is usually a false friend.** Dependency versions, package versions, API versions, and source-code version search should be excluded unless they supply a transferable version-identity mechanism for evolving evidence.

16. **Generic provenance is not precise evidence provenance.** Database lineage, blockchain provenance, or generic source reputation is insufficient if the retrieved evidence object/version cannot be identified.

17. **Document understanding remains Topic 08.** OCR, layout understanding, table parsing, spreadsheet QA, image understanding, and attachment extraction are relevant only when they contribute to the retrieval decision itself. Interpretation and exact region/cell/page grounding belong to Topic 08.

18. **State determination remains Topic 06.** Factuality, contradiction, lifecycle, and revision-state models should not be absorbed into Topic 07 unless they emit or consume an explicit missing-evidence need.

19. **Generic fact-checking retrieval is not automatically sufficient.** Fixed-claim, fixed-corpus fact verification may contribute evidence-selection methods but should be TRANSFER unless it handles iterative sufficiency and stopping.

20. **Enterprise search is not enough merely because the corpus is corporate.** Vendor architectures, intranet ranking, expertise search, and knowledge-management systems require additional evidence of the relevant investigation capability.

21. **Security enforcement alone is not evidence-gap handling.** Access-control work must expose a denial or authorization outcome that an investigation can distinguish from absence to be directly useful.

22. **Recommendation retrieval is excluded.** Conversational recommendation, product recommendation, and personalized feed retrieval do not answer the bounded work-information problem.

23. **Empty result must not become negative evidence by default.** Any method that infers nonexistence from zero search hits without completeness semantics conflicts with a core Topic 07 requirement.

24. **Loss of source/version identity is a downgrade.** A method that retrieves useful text but discards which source/version produced it is insufficient for the target system's lineage requirements.

25. **Synthetic or open-domain success is not workplace validation.** Such papers may demonstrate a mechanism, but they remain TRANSFER evidence unless evaluated in an appropriately comparable organizational communication setting.

## Date policy

**Earliest publication year discovery must include: 2000.**

A recent-only search would distort this topic. Although adaptive RAG, active retrieval, Self-RAG, neural multi-hop retrieval, and much modern selective QA are predominantly late-2010s and 2020s research, important component literatures predate LLMs substantially.

In particular, temporal information retrieval has important early-2000s work, including *Time-Based Language Models*. Enterprise retrieval, interactive/context-sensitive information seeking, sequential retrieval, cost-sensitive search, and related query-reformulation concepts also developed before the present RAG vocabulary.

The default discovery window should therefore be:

`2000-2026`

rather than, for example, `2018-2026` or `2020-2026`.

This does **not** mean discovery should fill the corpus with old generic IR papers. Classical relevance feedback, query expansion, and other pre-RAG methods should still pass the same capability admission rules. The purpose of the 2000 boundary is to avoid silently deleting foundational temporal, interactive, cost, and enterprise-retrieval work.

Pre-2000 literature does not need a bulk search in the first discovery pass. If an admitted paper identifies a specific pre-2000 result as foundational to a Topic 07 capability—rather than merely generic IR history—discovery should follow that citation backward deliberately rather than changing the entire corpus window.
