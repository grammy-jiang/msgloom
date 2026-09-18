# Unified iterative RAG stopping and provenance control under distribution shift academic terminology analysis

## Product problem

The target is not generic RAG and not generic search. The academic object is a **bounded evidence-acquisition controller**:

`explicit unresolved evidence requirement → structured retrieval action → source/version/permission-aware evidence → reassess evidence coverage and risk → retrieve again, answer, abstain, or terminate with an explicit failure reason`.

The key requirement is therefore a conjunction of capabilities that are usually studied separately:

- a structured representation of what evidence is still missing;
- iterative or adaptive retrieval rather than a fixed retrieve-once pipeline;
- evidence-coverage or sufficiency judgments rather than generator confidence alone;
- temporal validity and document-version lineage rather than simple recency;
- claim-to-source provenance;
- calibrated, selective, or conformal reliability, especially under distribution shift;
- authorization enforced during retrieval;
- bounded evidence-access, token, computation, latency, or monetary budgets;
- distinct terminal outcomes for absence, denial, source failure, extraction failure, budget exhaustion, and true negative evidence.

Round 4 should therefore stop treating the original seed phrases as equally useful. Several newer and more precise terms are substantially better search handles: **verification-aware stopping**, **evidence coverage**, **conformal retrieval**, **certified generation risk**, **information-directed conformal retrieval**, **versioned document QA**, **valid-time retrieval**, **retrieval-time gating**, **ABAC-gated retrieval**, **budgeted evidence acquisition**, and **cost-aware evidence selection**.

Recent literature now contains papers addressing significant subsets of the target: adaptive and active RAG, verification-aware stopping, conformal RAG reliability, conformal retrieval, versioned-document QA, permission-gated enterprise retrieval, and cost-aware evidence acquisition. Those component results must not be interpreted as proof that a single joint controller exists.

## Seed keyword audit

| Seed | Academic meaning | Fit | Main risk |
| --- | --- | --- | --- |
| conversational query rewriting | Rewrite a context-dependent turn as a standalone search query. | MODERATE | Helps formulate a gap but does not decide whether retrieval is needed or sufficient. |
| query reformulation | Transform a query using feedback, expansion, decomposition, or context. | MODERATE | Very broad; much of the literature is ranking optimization rather than evidence acquisition. |
| query resolution | Overloaded label for ambiguity, entity/reference resolution, query interpretation, or processing. | WEAK | No stable task family corresponding to the required controller. |
| conversational search | Multi-turn interactive information retrieval using dialogue history. | MODERATE | Often evaluates ranking, rewriting, and interaction quality rather than explicit gap closure. |
| context-aware search | Retrieval using user, session, location, task, or other contextual variables. | WEAK | Context personalization is not missing-evidence detection. |
| question decontextualization | Turn a context-dependent question into a self-contained question. | MODERATE | Produces a retrieval-ready question but normally has no retrieve/reassess/stop loop. |
| retrieval-augmented generation | Generation conditioned on externally retrieved evidence. | MODERATE | An umbrella term dominated by fixed one-shot RAG. |
| adaptive retrieval augmented generation | Dynamically choose retrieval strategy, depth, or whether retrieval is needed. | STRONG | Some methods adapt only once and have no iterative sufficiency test. |
| active retrieval augmented generation | Trigger retrieval during generation according to emerging information needs. | STRONG | Triggers may be token-confidence heuristics rather than structured evidence gaps. |
| iterative retrieval | Repeated retrieval where earlier results influence later searches. | STRONG | Fixed iteration counts are common and do not establish responsible stopping. |
| self-directed retrieval | Model-controlled decision to retrieve on demand. | MODERATE | Noncanonical phrase; overlaps better-defined adaptive, active, and self-reflective RAG terminology. |
| multi-hop retrieval | Retrieve several connected pieces of evidence required for a compositional question. | STRONG | Frequently assumes a small fixed hop count and ignores temporal, permission, and provenance constraints. |
| iterative multi-hop question answering | Alternate reasoning or subquestion generation with retrieval. | STRONG | Final QA accuracy usually dominates evaluation; failure-state semantics are often absent. |
| retrieval planning | Plan subqueries, search actions, routing, and retrieval order. | STRONG | General agent work can be unbounded and may include non-read-only actions. |
| evidence acquisition | Acquire observations or documents to reduce uncertainty or support a decision. | MODERATE | Extremely broad across active learning, experimentation, vision, and decision theory. |
| tool-use planning | Plan calls to search, APIs, databases, or other tools. | MODERATE | Often concerns general autonomous agents rather than bounded read-only retrieval. |
| query-focused evidence retrieval | Retrieve evidence relevant to a specific question or proposition. | MODERATE | Often one-shot evidence retrieval; phrase is less standardized than multi-hop or adaptive retrieval. |
| temporal information retrieval | Model temporal intent, document/content time, and temporal relevance in IR. | STRONG | Temporal relevance alone does not imply historical validity or version lineage. |
| time-aware retrieval | Incorporate time constraints, temporal context, time decay, or event time. | STRONG | Can collapse to simple recency weighting. |
| recency-aware retrieval | Prefer fresh or recently published evidence. | MODERATE | Latest evidence is not necessarily the evidence valid at the requested time. |
| version-aware retrieval | Retrieve using explicit document versions, supersession, evolution, or change history. | STRONG | Also attracts software-package and code-version work; version labels alone are insufficient. |
| provenance-aware retrieval | Retain or reason over source origin, lineage, trust, or transformation history. | STRONG | Provenance is often reduced to citation or trust and may omit version identity. |
| unanswerability detection | Detect when available information cannot support an answer. | STRONG | Most benchmarks collapse multiple failure causes into one unanswerable class. |
| answerability prediction | Estimate whether enough evidence exists to answer correctly. | STRONG | Binary labels can hide the reason for insufficiency and do not imply iterative replenishment. |
| selective question answering | Answer only a selected subset while controlling risk or accuracy among answered cases. | STRONG | Usually answer-versus-abstain with fixed evidence, not retrieve-more-versus-stop. |
| answer abstention | Refuse or withhold an answer when confidence or support is inadequate. | STRONG | Generic safety refusal is not evidence-based stopping. |
| retrieval stopping criterion | Rule for terminating iterative retrieval or search. | STRONG | Older IR literature may mean top-k cutoff, crawler stopping, or convergence. |
| budgeted retrieval | Retrieve under a fixed call, passage, token, compute, time, or resource budget. | STRONG | Efficiency alone does not protect evidence completeness. |
| cost-aware retrieval | Trade information value against access, compute, latency, or monetary cost. | STRONG | Often accounts for only one cost component rather than end-to-end cost. |
| enterprise search | Search over organizational repositories and private information. | WEAK | Large volume of vendor and system literature with little controller evaluation. |
| access-controlled retrieval | Filter retrieval through ACL, RBAC, ABAC, tenant, or identity authorization. | STRONG | Security alone does not specify what happens after relevant evidence is denied. |
| evidence sufficiency estimation | Judge whether accumulated evidence supports every required claim or subgoal. | STRONG | Terminology is not fully standardized, and confidence is sometimes substituted for true coverage. |

The most important demotions are **query resolution**, **context-aware search**, and **enterprise search**. They are too ambiguous or too broad for a fourth gap-closure round. Generic **RAG**, **query reformulation**, **recency-aware retrieval**, **tool-use planning**, and **self-directed retrieval** should also be used only in constrained conjunctions.

## Academic task families

### F1 — Context-dependent gap-to-query transformation — TRANSFER

This family covers conversational query rewriting and question decontextualization. It is useful when an unresolved pronoun, missing antecedent, or missing field must be transformed into a standalone retrieval request.

Known seed paper: *Can You Unpack That? Learning to Rewrite Questions-in-Context* (2019).

It does **not** establish retrieval necessity, evidence completeness, provenance, or stopping.

### F2 — Structured evidence decomposition and compositional retrieval — DIRECT

This family represents the target question as subquestions, expected claims, entities, relations, joins, or other explicit evidence requirements. Retrieval is driven by what remains unresolved.

Useful vocabulary:

- structured evidence requirements;
- expected hop claims;
- evidence graph;
- query decomposition;
- compositional retrieval;
- multi-entity multi-hop retrieval;
- evidence coverage.

Known seed papers include *Interleaving Retrieval with Chain-of-Thought Reasoning for Knowledge-Intensive Multi-Step Questions* (2023), *ReAct: Synergizing Reasoning and Acting in Language Models* (2023), and the more stopping-specific *HALT: Verification-Aware Stopping for Retrieval-Augmented Search Agents* (2026).

This is the primary family for gap-1.

### F3 — Adaptive, active, and iterative RAG control — DIRECT

This family asks whether retrieval is needed, when it should occur, how much should be retrieved, and whether another round should be executed.

Known seed papers:

- *Active Retrieval Augmented Generation* (2023);
- *Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection* (2024);
- *Adaptive-RAG: Learning to Adapt Retrieval-Augmented Large Language Models through Question Complexity* (2024);
- *AB-RAG: Adaptive Budgeted Retrieval-Augmented Generation for Reliable Question Answering* (2026).

Admission must distinguish a true iterative controller from a one-time query-complexity router.

### F4 — Evidence-coverage and verification-aware stopping — DIRECT

This is a higher-value term family than generic “retrieval stopping criterion.”

The desired controller stops because the accumulated evidence covers the required propositions, not simply because:

- the model feels confident;
- entropy is low;
- an arbitrary top-k has been reached;
- a predefined number of hops has executed.

The strongest current search handles are **verification-aware stopping**, **evidence coverage**, **claim-evidence alignment**, **expected hop claims**, and **retrieval termination policy**.

Known seed paper: *HALT: Verification-Aware Stopping for Retrieval-Augmented Search Agents* (2026).

### F5 — Selective QA and abstention under distribution shift — TRANSFER

This family supplies the risk-coverage framework for answering only when predicted reliability is acceptable.

Foundational and seed work includes:

- *On Optimum Recognition Error and Reject Tradeoff* (1970);
- *Selective Question Answering under Domain Shift* (2020).

This literature is important to gap-3, but a static answer/abstain decision should not be mistaken for a retrieve-more/stop controller.

### F6 — Conformal and risk-controlled retrieval-augmented prediction — DIRECT

This is a priority round-4 family.

Useful terminology:

- conformal RAG;
- conformal retrieval;
- conformal risk control;
- certified generation risk;
- information-directed conformal retrieval;
- conformal abstention;
- risk-controlled RAG.

Known seed papers include:

- *Conformal Risk Control* (2024);
- *TRAQ: Trustworthy Retrieval Augmented Question Answering via Conformal Prediction* (2024);
- *C-RAG: Certified Generation Risks for Retrieval-Augmented Language Models* (2024);
- *Response Quality Assessment for Retrieval-Augmented Generation via Conditional Conformal Factuality* (2025);
- *IDCR: Information-Directed Conformal Retrieval* (2026).

These papers make generic “calibrated stopping” too weak a search phrase. Discovery should explicitly search conformal retrieval and risk-controlled retrieval, then check whether the guarantee actually governs the iterative stopping decision and whether distribution-shift assumptions match the claim.

### F7 — Temporal information retrieval and temporal QA — DIRECT

This family covers temporal intent, historical questions, document/content time, and time-sensitive relevance.

Known seed work includes *Time-Based Language Models* (2003) and the temporal-IR literature synthesized in *Temporal Information Retrieval* (2015).

The critical exclusion is **recency-only** retrieval. Topic 07 requires “which evidence was valid for the question's time,” not merely “which evidence is newest.”

### F8 — Valid-time, transaction-time, and bitemporal semantics — TRANSFER

Temporal database terminology is unusually valuable for this project because it gives precise names to an ambiguity that generic RAG terminology often leaves implicit.

- **Valid time / effective time**: when a fact applies in the modeled world.
- **Transaction time / system time**: when the information system stored or knew the fact.

Known seed work includes *A Taxonomy of Time in Databases* (1985) and *Temporal Data Management* (1999).

This is a transfer family, but it directly sharpens gap-2 and the inherited distinction between message/effective time and collection/version time.

### F9 — Version-aware retrieval and versioned document QA — DIRECT

Round 4 should promote **versioned document QA** and **version-aware RAG**.

Known seed paper: *VersionRAG: Version-Aware Retrieval-Augmented Generation for Evolving Documents* (2025).

Useful related terms include:

- document version lineage;
- version graph;
- supersession;
- evolving documents;
- historical version QA;
- change-aware retrieval.

A paper should not count toward gap-2 merely because documents have version metadata. The retrieval path must use version identity or evolution semantics materially.

### F10 — Evidence provenance, attribution, and claim-level grounding — DIRECT

This family covers the relationship between generated claims and supporting evidence.

Known seed papers include:

- *Attributed Question Answering: Evaluation and Modeling for Attributed Large Language Models* (2022);
- *Provenance: A Light-weight Fact-checker for Retrieval Augmented LLM Generation Output* (2024).

For Topic 07, ordinary citation generation is insufficient when version lineage is relevant. Queries should therefore join provenance with **source lineage**, **document version**, or **version-aware retrieval**.

### F11 — Permission-aware and policy-gated retrieval — DIRECT

The correct terminology is more specific than “enterprise search” or “secure RAG.”

Promote:

- retrieval-time authorization;
- retrieval-time gating;
- policy-aware retrieval;
- permission-aware retrieval;
- identity-aware retrieval;
- multitenant retrieval;
- ABAC-gated retrieval.

Known seed papers include *SecureRAG: End-to-End Secure Retrieval-Augmented Generation* (2025) and *Securing the Agent: Vendor-Neutral, Multitenant Enterprise Retrieval and Tool Use* (2026).

Gap-4 requires one additional condition that access-control papers may not test: after unauthorized candidates are removed, the controller must re-evaluate evidence sufficiency and, if needed, issue another authorized retrieval request.

### F12 — Budgeted and cost-aware evidence acquisition — DIRECT

This family should replace vague searches for “efficient RAG.”

Promote:

- budgeted evidence acquisition;
- adaptive budgeted RAG;
- cost-aware evidence selection;
- evidence-access budget;
- access-cost tiers;
- retrieval budget;
- dynamic resource optimization.

Known seed papers include:

- *AB-RAG: Adaptive Budgeted Retrieval-Augmented Generation for Reliable Question Answering* (2026);
- *When Knowledge Is Not Free: Cost-Aware Evidence Selection in Retrieval-Augmented Generation* (2026);
- *RAG-on-a-Diet: A Reinforcement Learning-Based Dynamic Resource Optimization Framework for RAG* (2026).

For gap-6, discovery should record whether costs include retrieval, reranking, planner/judge inference, generation, authorization checks, tokens, and wall-clock latency rather than accepting a single-component cost number.

### F13 — Failure-aware answerability and evidence absence — DIRECT

“Unanswerability” remains useful but is too coarse for the product contract.

The target terminal-state vocabulary should explicitly search for:

- empty retrieval;
- missing evidence;
- access denied;
- source unavailable;
- extraction failure;
- budget exhaustion;
- unsupported answer;
- negative evidence;
- abstention.

Gap-5 remains open unless a system distinguishes operational failure from evidential negation.

### F14 — Integrated retrieval-controller architectures — DIRECT

This is the direct search family for gap-8.

The search should not require all seven capabilities in one literal query because that would have poor recall. Instead, search combinations of two or three high-value dimensions:

- adaptive retrieval + version-aware + conformal;
- temporal RAG + provenance + stopping;
- permission-aware + version-aware RAG;
- authorization + evidence sufficiency + budget;
- policy-aware retrieval + conformal risk;
- provenance + retrieval stopping + temporal validity.

Only implementation and joint evaluation count. A paper describing individually available modules does not establish an integrated controller.

### F15 — Workplace and enterprise multi-source evidence investigation — DIRECT

This family targets gap-7.

Search for heterogeneous organizational evidence including:

- email;
- workplace communication;
- enterprise documents;
- attachments;
- organizational knowledge;
- versioned enterprise content;
- access-controlled enterprise RAG.

This family should come **after** capability-specific searching. “Enterprise search” alone is too noisy and will mostly return product and architecture material.

## Query families

### F1 — Context-dependent gap-to-query transformation — TRANSFER

- `"question decontextualization" retrieval unresolved antecedent evidence`
- `"conversational query rewriting" missing context retrieval`
- `"query reformulation" conversational search unresolved reference retrieval`
- `"question-in-context rewriting" evidence retrieval`

### F2 — Structured evidence decomposition and compositional retrieval — DIRECT

- `"evidence coverage" multi-hop retrieval expected claims`
- `"structured evidence" multi-hop question answering retrieval planning`
- `"query decomposition" iterative retrieval compositional question answering`
- `"multi-entity" multi-hop retrieval temporal constraints question answering`
- `"compositional retrieval" evidence sufficiency multi-hop`
- `"structured evidence requirements" retrieval planning question answering`
- `"evidence graph" iterative retrieval sufficiency`

These are the highest-priority gap-1 queries. They deliberately combine the structural representation with retrieval behavior; another round of `"structured evidence gap" RAG` alone is unlikely to add much.

### F3 — Adaptive, active, and iterative RAG — DIRECT

- `"adaptive retrieval" RAG iterative stopping`
- `"active retrieval augmented generation" iterative retrieval confidence`
- `"self-reflective retrieval" RAG retrieve on demand`
- `"adaptive RAG" retrieve more evidence stop`
- `"dynamic retrieval" RAG controller iterative`
- `"retrieval necessity" RAG adaptive retrieval`

### F4 — Evidence-coverage stopping — DIRECT

- `"verification-aware stopping" retrieval augmented`
- `"evidence coverage" stopping retrieval agent`
- `"retrieval stopping" evidence sufficiency multi-hop`
- `"claim-evidence alignment" stopping search agent`
- `"multi-round RAG" stopping criterion sufficiency`
- `"retrieval termination policy" evidence coverage RAG`
- `"stopping judgment" iterative RAG evidence`

### F5 — Selective QA under distribution shift — TRANSFER

- `"selective question answering" domain shift abstention`
- `"answer abstention" out-of-distribution question answering calibration`
- `"risk-coverage" question answering domain shift`
- `"selective prediction" question answering distribution shift calibration`
- `"reject option" question answering uncertainty`

### F6 — Conformal and risk-controlled retrieval — DIRECT

- `"conformal" retrieval augmented generation stopping`
- `"conformal retrieval" evidence acquisition`
- `"conformal risk control" RAG retrieval`
- `"certified generation risk" RAG distribution shift`
- `"information-directed conformal retrieval"`
- `"conformal abstention" RAG`
- `"risk-controlled" RAG retrieval stopping`
- `"conformal prediction" adaptive retrieval question answering`

This family is a major round-4 promotion. It should be searched before another generic `"calibrated stopping" RAG` query.

### F7 — Temporal IR and temporal QA — DIRECT

- `"temporal information retrieval" effective time document versions`
- `"time-aware retrieval" temporal validity question answering`
- `"temporal RAG" historical version effective time`
- `"time-sensitive retrieval" multi-hop question answering`
- `"recency-aware retrieval" temporal validity version`
- `"temporal question answering" evolving documents retrieval`

### F8 — Valid-time and bitemporal semantics — TRANSFER

- `"valid time" "transaction time" retrieval augmented generation`
- `"effective time" document retrieval version`
- `"bitemporal" RAG retrieval`
- `"valid-time" question answering evolving documents`
- `"transaction-time" information retrieval provenance`
- `"application time" version-aware retrieval`

This search family is specifically intended to prevent “latest document” from silently replacing “document valid at the relevant time.”

### F9 — Version lineage — DIRECT

- `"versioned document QA"`
- `"version-aware retrieval augmented generation"`
- `"document version lineage" retrieval question answering`
- `"version graph" RAG temporal`
- `"evolving documents" retrieval QA provenance`
- `"supersession" version-aware retrieval RAG`
- `"historical version" RAG question answering`

### F10 — Provenance and attribution — DIRECT

- `"provenance-aware retrieval" RAG lineage`
- `"attributed question answering" retrieval evidence source`
- `"source attribution" RAG claim evidence provenance`
- `"evidence provenance" multi-hop question answering`
- `"claim-level attribution" retrieval augmented generation`
- `"source lineage" RAG retrieval evidence`
- `"provenance" versioned documents retrieval augmented generation`

### F11 — Permission-aware retrieval — DIRECT

- `"retrieval-time gating" RAG authorization`
- `"permission-aware retrieval" RAG`
- `"access-controlled retrieval" RAG ABAC`
- `"multitenant" RAG retrieval authorization`
- `"policy-aware retrieval" RAG lineage`
- `"attribute-based access control" vector retrieval RAG`
- `"identity-aware retrieval" RAG permissions`
- `"authorization-aware retrieval" retrieval augmented generation`

For gap-4, candidates should then be screened for **replenishment after filtering**, not merely correct access denial.

### F12 — Budget and total cost — DIRECT

- `"budgeted evidence acquisition" RAG`
- `"adaptive budgeted retrieval augmented generation"`
- `"cost-aware evidence selection" RAG`
- `"cost-aware RAG" stop retrieval`
- `"retrieval budget" multi-hop question answering stopping`
- `"latency" "token cost" adaptive RAG retrieval`
- `"evidence access budget" retrieval augmented generation`
- `"budget exhaustion" RAG stopping`

### F13 — Failure-aware answerability — DIRECT

- `"unanswerability detection" RAG retrieval failure`
- `"answerability prediction" retrieved evidence sufficiency`
- `"retrieval failure" RAG abstention empty results`
- `"negative evidence" retrieval question answering`
- `"missing evidence" RAG abstention`
- `"empty retrieval" question answering abstention`
- `"access denied" retrieval augmented generation unanswerable`
- `"source unavailable" RAG abstention`

### F14 — Integrated controller — DIRECT

- `"adaptive RAG controller" provenance temporal permission conformal`
- `"retrieval controller" version-aware authorization calibrated stopping`
- `"iterative RAG" evidence coverage version provenance conformal`
- `"risk-controlled" retrieval permission provenance temporal`
- `"version-aware" "conformal" RAG retrieval stopping`
- `"policy-aware" "conformal" RAG`
- `"permission-aware" "version-aware" RAG`
- `"adaptive retrieval" provenance "access control" RAG`
- `"temporal RAG" conformal stopping provenance`
- `"retrieval controller" evidence sufficiency budget authorization`

The discovery strategy should search these conjunctions individually and combine the candidate sets. Requiring every capability in a single literal search query would produce false negatives.

### F15 — Workplace and enterprise evaluation — DIRECT

- `"enterprise email" RAG multi-hop permissions`
- `"workplace communication" retrieval augmented generation evidence`
- `"email question answering" attachments retrieval permissions`
- `"enterprise search" versioned documents access control RAG`
- `"organizational knowledge" adaptive RAG provenance`
- `"enterprise RAG" temporal provenance permissions evaluation`
- `"workplace documents" multi-hop retrieval access control`
- `"enterprise communication" evidence retrieval stale conflicting documents`

## False friends and downgrade rules

Discovery should downgrade or reject the following even when titles or abstracts contain the requested words:

1. **One-shot RAG** with no decision to retrieve again and no semantic stopping condition.
2. **Adaptive routing only**: one initial choice among no retrieval, single-hop, or multi-hop is not an iterative controller.
3. **Fixed-hop iteration** presented as stopping. A hard cap is a budget safeguard, not evidence sufficiency.
4. **Confidence-only stopping** based on entropy, token probability, or self-consistency with no explicit evidence-coverage check.
5. **Query rewriting only**, including conversational rewriting or decontextualization without downstream retrieval control.
6. **Oracle multi-hop QA** with gold supporting documents, gold decomposition, or known hop count when the target problem is open-corpus evidence acquisition.
7. **Recency-only temporal retrieval**. Freshness is not effective-time validity.
8. **Timestamp-only methods** that never distinguish document publication time, content/effective time, and collection/system time when those distinctions affect correctness.
9. **Software-version retrieval** unless the technique genuinely transfers to lineage over evolving evidence documents.
10. **Version labels without lineage**. Merely storing `version=3` does not establish supersession, history, or validity.
11. **Citation-only provenance** when the gap requires immutable document-version identity and source lineage.
12. **Generic database provenance** with no retrieval or stopping role. This can be TRANSFER evidence, not a direct controller result.
13. **Conformal generation only** if retrieval depth and stopping are fixed. It is useful reliability evidence but does not close iterative-stopping gap-3.
14. **IID calibration described as distribution-shift robustness**. Shift must be explicitly evaluated or theoretically handled.
15. **Guarantees with unexamined exchangeability assumptions** when the claimed setting is non-stationary.
16. **Secure RAG concerned only with prompt injection, poisoning, encryption, or embedding privacy** and no user-specific authorization.
17. **Ingestion-time ACL only** without retrieval-time enforcement for the requesting identity.
18. **Permission filtering without replenishment** when relevant unauthorized candidates are removed.
19. **Enterprise-search product literature** without academic evaluation.
20. **Budget optimization without evidence-quality evaluation**.
21. **Token-only cost accounting** presented as end-to-end cost.
22. **Empty results interpreted as a negative fact** without closed-world semantics.
23. **A single “unanswerable” label** that hides denial, source outage, extraction failure, budget exhaustion, and genuine negative evidence when evaluating gap-5.
24. **Unbounded autonomous browsing or acting agents** when the desired mechanism is bounded read-only evidence acquisition.
25. **Recommendation, advertising, or product retrieval** unrelated to evidential question answering.
26. **Transfer-domain success presented as workplace accuracy**. Wikipedia, web QA, medical, legal, or vision results may justify mechanisms but not production-mailbox representativeness.
27. **Synthetic composition claims** that infer an integrated controller from independent modules. Gap-8 requires the joint behavior to be implemented and evaluated.

The strictest downgrade rule for this round is: **a paper does not close gap-8 merely because it solves two or three components that could theoretically be wired to other components**.

## Date policy

**Earliest publication year discovery must be able to reach: 1970.**

A single modern recency cutoff would silently remove foundational material needed to interpret the reliability side of the problem.

The relevant historical layers are different:

- selective prediction and reject-option theory reaches at least **1970**, including C. K. Chow's *On Optimum Recognition Error and Reject Tradeoff*;
- precise valid-time and transaction-time terminology is established in temporal-database research by the **1980s**, including *A Taxonomy of Time in Databases* (1985);
- temporal information retrieval has important foundational work from the early **2000s**, including *Time-Based Language Models* (2003);
- conversational question rewriting becomes directly relevant around **2019**;
- modern RAG begins in **2020**;
- adaptive, active, conformal, version-aware, permission-aware, and budgeted RAG controller work is concentrated largely in **2023–2026**.

Accordingly, discovery should **not apply a global 2018, 2020, or 2023 cutoff**. The operational policy should be:

- allow searches back to **1970** for foundational TRANSFER families;
- prioritize **2020–2026** for DIRECT RAG/controller queries;
- prioritize **2023–2026** when searching adaptive, conformal, version-aware, permission-aware, and budget-controlled RAG;
- back-search temporal validity to the **1980s** and temporal IR to the **2000s** when terminology or semantics are needed.

The round-4 search should be recent-heavy but not recent-only.
