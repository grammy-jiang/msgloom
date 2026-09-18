# Joint adaptive RAG controllers for structured evidence-gap completion with temporal and version-aware provenance and calibrated risk-controlled stopping under distribution shift academic terminology analysis

## Product problem

The target is narrower than generic retrieval-augmented generation. The research object is a controller that starts from an **explicit unresolved evidence requirement**, converts that requirement into bounded retrieval actions, preserves the meaning and lineage of what comes back, repeatedly decides whether the evidence requirement is now satisfied, and terminates with an answer, an explicit unresolved state, or a reason retrieval cannot responsibly continue.

The desired loop is therefore closer to:

`structured missing-information state → planned retrieval → source/version/time/permission-aware evidence or typed failure → sufficiency/risk reassessment → retrieve again, answer, abstain, or terminate`

than to:

`question → top-k retrieval → generation`.

Round 3 should consequently stop treating the vocabulary from ordinary RAG as sufficient. The unresolved gaps require terminology from several adjacent literatures:

- **complex and compositional information needs** for temporal constraints and multi-entity joins;
- **adaptive/active/iterative RAG** for repeated evidence acquisition;
- **answerability and evidence sufficiency** for deciding whether another retrieval step is needed;
- **temporal IR and temporal QA** for time-scoped evidence;
- **temporal databases, document versioning, and data provenance** for valid time and lineage;
- **authorization-aware search and security trimming** for permission-constrained retrieval;
- **selective prediction, reject options, and conformal risk control** for calibrated stopping under shift;
- **budgeted information acquisition and optimal stopping** for bounded retrieval;
- **retrieval-failure discrimination** for terminal-state semantics;
- **enterprise/workplace search** for realistic heterogeneous source conditions.

An important terminology correction is that several project phrases are useful specifications but are not established academic task names. In particular, `"structured evidence gap"`, `"version-aware retrieval"`, `"provenance-aware retrieval"`, and `"retrieval stopping criterion"` should not be relied upon as exact-string anchors. Discovery should search their established neighboring vocabularies as well.

## Seed keyword audit

| Seed | Academic meaning | Fit | Main risk |
| --- | --- | --- | --- |
| conversational query rewriting | Rewrite a context-dependent conversational utterance into a standalone search query. | MODERATE | Solves query expression, not whether retrieval is needed or when evidence is sufficient. |
| query reformulation | Expansion, rewriting, substitution, decomposition, or feedback used to improve a search query. | MODERATE | Extremely broad; generally assumes retrieval is already warranted. |
| query resolution | Ambiguous label covering query disambiguation, reference resolution, database processing, and other tasks. | WEAK | Not a stable name for evidence-gap completion and produces many unrelated results. |
| conversational search | Interactive IR over evolving, multi-turn information needs. | MODERATE | Most work optimizes dialogue-context ranking rather than explicit bounded investigation. |
| context-aware search | Search incorporating conversation, user, location, task, or other contextual features. | WEAK | Frequently means personalization rather than missing-evidence reasoning. |
| question decontextualization | Convert a context-dependent question into a self-contained one. | MODERATE | Can formulate a query but cannot determine that a gap exists or that it has been filled. |
| retrieval-augmented generation | Generate using retrieved external evidence. | MODERATE | Generic RAG normally has fixed retrieval and lacks the required controller semantics. |
| adaptive retrieval augmented generation | Vary retrieval according to difficulty, information need, confidence, or intermediate state. | STRONG | Adaptation can be only a one-time routing decision rather than iterative gap closure. |
| active retrieval augmented generation | Trigger retrieval during reasoning or generation when additional information appears necessary. | STRONG | Need is often represented only by token uncertainty rather than a structured evidence requirement. |
| iterative retrieval | Repeated retrieval where earlier results affect later queries. | STRONG | Repetition alone provides no evidence-sufficiency or safe-stop semantics. |
| self-directed retrieval | Models or agents autonomously deciding what or when to retrieve. | MODERATE | Nonstandard phrase and heavily contaminated by unrestricted autonomous-agent literature. |
| multi-hop retrieval | Acquire evidence across several dependent retrieval hops. | STRONG | Standard benchmarks commonly fix hop count and assume evidence exists. |
| iterative multi-hop question answering | Alternate reasoning and retrieval across several evidence steps. | STRONG | Usually answer-accuracy oriented and closed-world. |
| retrieval planning | Select retrieval actions, sources, subqueries, or their order. | STRONG | Strong overlap with generic agent planning lacking evidence sufficiency. |
| evidence acquisition | Obtain observations or information required to resolve a question or decision. | MODERATE | Very broad cross-disciplinary terminology. |
| tool-use planning | Select and sequence external tool calls. | WEAK | Usually permits much broader actions than bounded read-only investigation. |
| query-focused evidence retrieval | Retrieve evidence relevant to a particular question. | MODERATE | Descriptive rather than strongly standardized terminology. |
| temporal information retrieval | IR where time contributes to relevance, query intent, or document interpretation. | STRONG | Much of the literature models freshness, not effective-time validity. |
| time-aware retrieval | Retrieval incorporating temporal signals or constraints. | MODERATE | Often fails to distinguish publication, event, valid, retrieval, and version time. |
| recency-aware retrieval | Favor recent information when freshness matters. | MODERATE | Latest evidence can be wrong for a historical or effective-time question. |
| version-aware retrieval | Retrieval distinguishing revisions or versions of evidence sources. | STRONG | The phrase can instead mean software, model, API, dataset, or index versions. |
| provenance-aware retrieval | Retrieval making use of origin, derivation, or lineage metadata. | STRONG | Provenance is often reduced to post-hoc citation rather than controller-visible lineage. |
| unanswerability detection | Detect that supplied knowledge is inadequate to answer a question. | STRONG | Fixed-context QA does not expose retrieval failure, permission denial, or unavailable sources. |
| answerability prediction | Predict whether current evidence is enough to answer. | STRONG | Often performed only after one fixed retrieval step. |
| selective question answering | Answer only when confidence/risk is acceptable; otherwise abstain. | STRONG | Does not itself decide whether another retrieval step would resolve the problem. |
| answer abstention | Withhold an answer under insufficient evidence or confidence. | STRONG | Final-answer refusal can be calibrated while retrieval remains unsafe. |
| retrieval stopping criterion | Decide when further retrieval should terminate. | STRONG | Exact wording is inconsistent; relevant work uses stopping policy, sufficiency, termination, or optimal stopping. |
| budgeted retrieval | Retrieve under explicit limits such as calls, documents, tokens, latency, or money. | STRONG | May optimize one cost dimension without controlling answer risk. |
| cost-aware retrieval | Include retrieval or inference cost in retrieval decisions. | STRONG | Frequently means search-engine efficiency rather than total investigation cost. |
| enterprise search | Search heterogeneous organizational information repositories. | MODERATE | Domain fit is useful, but evidence-gap completion and stopping are usually absent. |
| access-controlled retrieval | Restrict retrievable evidence according to user authorization. | STRONG | Literature is fragmented across IR, databases, security, and searchable encryption. |
| evidence sufficiency estimation | Estimate whether available evidence adequately supports answering or deciding. | STRONG | Relevant work is dispersed across answerability, sufficient context, verification, completeness, and stopping terminology. |

The highest-value changes from the original seed set are therefore not new synonyms for RAG. They are the introduction of terminology that exposes missing semantics:

**Promote strongly**

- structured information need
- query decomposition
- complex/compositional question answering
- compositional retrieval
- multi-relation or conjunctive constraints
- retrieval necessity prediction
- dynamic retrieval
- evidence sufficiency / sufficient context
- selective QA under domain shift
- valid time / transaction time
- bitemporal data
- document versioning / version lineage
- data provenance / temporal provenance
- authorization-aware search
- security trimming
- selective prediction / reject option
- risk-coverage
- conformal risk control
- calibrated abstention
- optimal stopping
- value of information
- budgeted information acquisition
- retrieval failure detection
- terminal-state discrimination

**Demote as primary exact-string anchors**

- query resolution
- context-aware search
- self-directed retrieval
- query-focused evidence retrieval
- tool-use planning
- generic evidence acquisition
- generic enterprise search
- recency-aware retrieval

These demoted concepts are not necessarily irrelevant; they are simply too ambiguous to drive round-3 discovery without stronger companion terms.

## Academic task families

### F1 — Structured compositional information needs and query decomposition — DIRECT

This family covers explicit decomposition of a difficult information requirement into entities, relations, temporal predicates, subquestions, and intermediate evidence requirements.

It is the most important terminology expansion for **gap-1**. Searching only `"structured evidence gap"` is too project-specific. Discovery should also search:

- structured information need;
- query decomposition;
- complex question answering;
- compositional retrieval;
- conjunctive query answering;
- multi-relation QA;
- temporal constraints in multi-hop retrieval.

A known seed is **Interleaving Retrieval with Chain-of-Thought Reasoning for Knowledge-Intensive Multi-Step Questions**. It does not by itself establish the required structured schema, but it anchors the iterative decomposition/retrieval literature.

### F2 — Adaptive, active, and iterative RAG — DIRECT

This is the closest controller literature.

Known seeds include:

- **Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks**
- **Active Retrieval Augmented Generation**
- **Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection**
- **Adaptive-RAG: Learning to Adapt Retrieval-Augmented Large Language Models through Question Complexity**
- **Interleaving Retrieval with Chain-of-Thought Reasoning for Knowledge-Intensive Multi-Step Questions**

Round 3 should distinguish three increasingly strong capabilities:

1. decide whether retrieval is needed;
2. decide what to retrieve next after seeing evidence;
3. decide that current evidence is sufficient and terminate safely.

A paper implementing only the first capability does not close the iterative stopping gaps.

### F3 — Evidence sufficiency, answerability, unanswerability, and abstention — DIRECT

This family supplies the semantics missing from the statement "retrieval succeeded."

Relevant concepts include:

- answerability prediction;
- sufficient context;
- evidence sufficiency;
- no-answer detection;
- unanswerability;
- selective QA;
- answer abstention.

Known seeds include **Know What You Don't Know: Unanswerable Questions for SQuAD** and **Selective Question Answering under Domain Shift**.

The central distinction for msgloom is:

`retrieved something ≠ obtained sufficient evidence`.

The strongest candidates will expose a sufficiency signal that could govern another retrieval action or safe termination.

### F4 — Temporal information retrieval and temporal QA — DIRECT

This family addresses retrieval when the required evidence is time-dependent.

Search must distinguish:

- publication/document time;
- event time;
- effective or valid time;
- retrieval/observation time;
- version time.

Known seeds include **Time-Based Language Models** and **CronQuestions: A Large-scale Benchmark for Temporal Question Answering over Knowledge Graphs**.

Pure recency ranking should not be treated as a solution to temporal validity.

### F5 — Document-version lineage, temporal databases, and data provenance — TRANSFER

This is the principal terminology expansion for **gap-2**.

RAG literature frequently uses loose phrases such as "fresh" or "up to date". The stronger neighboring literature already has concepts for:

- valid time;
- transaction time;
- bitemporal records;
- versions and revisions;
- derivation lineage;
- provenance graphs;
- provenance annotations.

Known foundational papers include:

- **A Taxonomy of Time in Databases**
- **Why and Where: A Characterization of Data Provenance**
- **Provenance Semirings**

This literature is TRANSFER because it generally does not implement an adaptive RAG controller. It is nevertheless important because it provides the semantics necessary to tell a retrieval controller that two passages came from different historical states of the same source.

### F6 — Authorization-aware and security-trimmed IR — DIRECT

This family directly addresses the retrieval boundary imposed by user permissions.

Promoted search vocabulary:

- authorization-aware search;
- permission-aware retrieval;
- access-controlled search;
- security trimming;
- security-trimmed search;
- document-level access control;
- authorization filtering;
- attribute-based access control plus information retrieval.

For **gap-4**, admission requires more than "we enforce access control." The relevant controller behavior is:

`retrieve candidates → enforce native authorization → observe that authorized evidence is still insufficient → issue another authorized query`

without converting denied candidates into negative factual evidence.

### F7 — Selective prediction and calibrated risk control under shift — TRANSFER

This is the most important theoretical expansion for **gap-3**.

Promoted terminology:

- selective prediction;
- selective classification;
- reject option;
- risk-coverage;
- calibrated abstention;
- selective QA under domain shift;
- conformal risk control;
- out-of-distribution selective prediction.

Known seeds include:

- **On Optimum Recognition Error and Reject Tradeoff**
- **Selective Classification for Deep Neural Networks**
- **SelectiveNet: A Deep Neural Network with an Integrated Reject Option**
- **Selective Question Answering under Domain Shift**
- **Conformal Risk Control**

This literature should not be claimed as direct proof of safe RAG stopping. Its value is to supply formalisms for a future retrieval controller where continuing retrieval, answering, and abstaining are risk-bearing decisions.

For round 3, a particularly valuable paper would explicitly connect selective prediction or conformal risk control to **iterative retrieval termination under shift**.

### F8 — Budgeted information acquisition and resource-rational stopping — TRANSFER

This family is needed because `"budgeted retrieval"` alone tends to attract search-engine efficiency work.

Search should expand into:

- budgeted information acquisition;
- resource-constrained QA;
- value of information;
- optimal stopping;
- resource-rational information seeking;
- anytime QA;
- adaptive computation;
- retrieval-budget allocation.

For **gap-6**, total cost should ideally include more than one dimension:

- retrieval calls;
- passages/documents/tokens retrieved;
- reranking;
- planner/judge/model inference;
- permission checks;
- latency;
- overall wall-clock time.

### F9 — Retrieval failure and terminal-state discrimination — DIRECT

This family targets a subtle but critical requirement that standard QA evaluations often erase.

The controller needs different observable states for at least:

- successful evidence retrieval;
- empty retrieval;
- authorization denial;
- source unavailable;
- unsupported extraction;
- exhausted retrieval budget;
- evidence still insufficient;
- evidence supporting a genuine negative proposition.

Queries should therefore combine retrieval failure terminology with no-answer, answerability, source availability, and tool failure.

This is the best terminology family for **gap-5**.

### F10 — Enterprise and workplace heterogeneous search — DIRECT

This is the direct-domain family for **gap-7**.

Useful searches should explicitly combine enterprise/workplace terms with the required mechanism:

- email;
- documents;
- attachments;
- heterogeneous repositories;
- permissions;
- temporal or versioned records;
- question answering;
- missing context.

Generic enterprise-search papers should not be admitted merely because the source domain resembles msgloom.

### F11 — Conversational query rewriting and decontextualization — TRANSFER

Known seeds:

- **Can You Unpack That? Learning to Rewrite Questions-in-Context**
- **Open-Domain Question Answering Goes Conversational via Question Rewriting**

These techniques can convert an unresolved reference or context-dependent missing-information requirement into a self-contained search query.

They remain downstream of gap detection:

`explicit gap → rewrite/decontextualize → retrieve`

not:

`conversation → query rewrite → therefore evidence was missing`.

### F12 — Bounded information-seeking tool planning — TRANSFER

Tool-using agents can contribute methods for selecting the next retrieval operation.

A known seed is **ReAct: Synergizing Reasoning and Acting in Language Models**.

Only bounded, information-seeking behavior is relevant. Papers whose core contribution is unrestricted browsing, executing code, controlling applications, purchasing, sending messages, or other action-taking should be downgraded.

### F13 — Joint adaptive retrieval controllers — DIRECT

This family explicitly searches for **gap-8**, rather than assuming a combination exists because all individual components exist somewhere in the literature.

Required combinations include several of:

- explicit evidence-need state;
- iterative retrieval;
- source or query planning;
- permission constraint;
- temporal validity;
- document-version lineage;
- provenance;
- sufficiency estimation;
- calibrated stopping;
- abstention;
- distribution shift;
- resource budget.

A paper should not close gap-8 unless these properties are exercised in one evaluated controller. A set of separate papers covering one property each is still only component evidence.

## Query families

### F1 — Structured compositional information needs — DIRECT

- `"structured information need" retrieval temporal constraints compositional`
- `"query decomposition" retrieval temporal multi-hop evidence`
- `"complex question answering" query decomposition temporal constraints retrieval`
- `"compositional retrieval" multi-entity temporal`
- `"multi-hop retrieval" entity relation constraints iterative`
- `"conjunctive query" question answering retrieval temporal`
- `"multi-relation" question answering retrieval temporal`
- `"structured evidence" retrieval sufficiency compositional`
- `"evidence requirements" retrieval decomposition question answering`

### F2 — Adaptive/active/iterative RAG — DIRECT

- `"adaptive RAG" retrieval decision stopping`
- `"adaptive retrieval augmented generation" sufficiency stopping`
- `"active retrieval augmented generation" evidence sufficiency`
- `"iterative RAG" retrieval stopping evidence`
- `"iterative retrieval" evidence sufficiency question answering`
- `"dynamic retrieval" language model information need stopping`
- `"retrieval necessity" RAG iterative`
- `"Self-RAG" retrieval critique stopping`
- `"FLARE" active retrieval information need`

### F3 — Sufficiency, answerability, and abstention — DIRECT

- `"evidence sufficiency" question answering retrieval`
- `"sufficient evidence" iterative retrieval question answering`
- `"answerability prediction" retrieval augmented generation`
- `"unanswerability detection" retrieval augmented generation`
- `"insufficient context" question answering retrieval`
- `"selective question answering" retrieval`
- `"answer abstention" RAG evidence`
- `"no-answer" retrieval failure question answering`
- `"retrieval sufficiency" language model`

### F4 — Temporal retrieval — DIRECT

- `"temporal information retrieval" document versions`
- `"temporal question answering" retrieval historical state`
- `"time-aware retrieval" question answering temporal constraints`
- `"valid time" information retrieval question answering`
- `"effective time" retrieval documents`
- `"historical question answering" document retrieval`
- `"temporal retrieval" multi-hop question answering`
- `"time-sensitive question answering" retrieval`
- `"freshness" "temporal validity" retrieval`

### F5 — Version lineage and provenance — TRANSFER

- `"document version" retrieval provenance lineage`
- `"versioned documents" information retrieval provenance`
- `"document versioning" retrieval temporal`
- `"data provenance" retrieval document version`
- `"provenance semirings" temporal data`
- `"valid time" "transaction time" provenance retrieval`
- `"bitemporal" provenance information retrieval`
- `"temporal database" provenance version lineage`
- `"version lineage" document retrieval`
- `"temporal provenance" document version`

### F6 — Permission-aware retrieval — DIRECT

- `"access control" information retrieval authorization`
- `"authorization-aware" search retrieval`
- `"permission-aware retrieval" enterprise search`
- `"access-controlled search" information retrieval`
- `"security trimming" enterprise search`
- `"security-trimmed search" retrieval`
- `"document-level access control" search retrieval`
- `"attribute-based access control" information retrieval`
- `"authorization filtering" search results`
- `"permission constrained" retrieval`

### F7 — Risk-controlled stopping under shift — TRANSFER

- `"selective question answering" "domain shift"`
- `"selective prediction" distribution shift calibration`
- `"selective classification" distribution shift risk coverage`
- `"risk coverage" selective prediction domain shift`
- `"reject option" distribution shift calibration`
- `"conformal risk control" distribution shift`
- `"risk-controlling prediction sets" distribution shift`
- `"calibrated abstention" domain shift`
- `"selective prediction" "out-of-distribution" calibration`
- `"conformal" abstention question answering`

### F8 — Budgeted acquisition — TRANSFER

- `"budgeted retrieval" question answering`
- `"cost-aware retrieval" question answering`
- `"resource-constrained" retrieval question answering`
- `"budgeted information acquisition" question answering`
- `"value of information" information retrieval stopping`
- `"optimal stopping" information retrieval evidence`
- `"adaptive computation" retrieval augmented generation cost`
- `"resource-rational" information seeking retrieval`
- `"anytime" question answering retrieval`
- `"retrieval budget" iterative RAG latency`

### F9 — Failure and terminal states — DIRECT

- `"retrieval failure detection" question answering`
- `"retrieval failure" RAG abstention`
- `"no evidence" retrieval question answering abstain`
- `"source unavailable" information retrieval question answering`
- `"insufficient evidence" retrieval failure`
- `"empty retrieval" question answering`
- `"no result" retrieval answerability`
- `"tool failure" question answering retrieval agent`
- `"retrieval exhausted" question answering`
- `"true negative" information retrieval no result`

### F10 — Workplace/enterprise retrieval — DIRECT

- `"enterprise search" email documents access control`
- `"enterprise information retrieval" email permissions`
- `"workplace search" email documents retrieval`
- `"organizational search" email document retrieval`
- `"email search" contextual retrieval enterprise`
- `"enterprise search" document versions provenance`
- `"enterprise search" heterogeneous sources permissions`
- `"workplace question answering" email documents`
- `"enterprise question answering" access control retrieval`

### F11 — Query rewriting/decontextualization — TRANSFER

- `"conversational query rewriting" retrieval`
- `"question decontextualization" conversational search`
- `"question rewriting" conversational retrieval`
- `"context dependent question" rewriting retrieval`
- `"conversational query reformulation" information retrieval`
- `"standalone question" decontextualization retrieval`

### F12 — Bounded information-seeking planning — TRANSFER

- `"information seeking" tool planning language model retrieval`
- `"retrieval planning" language model iterative`
- `"tool-use planning" information retrieval question answering`
- `"read-only" agent retrieval planning`
- `"bounded" information-seeking agent retrieval`
- `"ReAct" retrieval question answering evidence`
- `"planning" "evidence acquisition" question answering`

### F13 — Joint-controller gap search — DIRECT

These should be treated as deliberately high-precision round-3 probes, even if they return few papers.

- `"adaptive RAG controller" provenance temporal stopping`
- `"adaptive RAG" provenance temporal abstention budget`
- `"iterative RAG" version provenance calibrated stopping`
- `"iterative RAG" temporal provenance answerability`
- `"adaptive retrieval" access control provenance abstention`
- `"permission-aware" RAG provenance temporal`
- `"version-aware" RAG iterative retrieval stopping`
- `"temporal" "version-aware" retrieval augmented generation`
- `"calibrated stopping" iterative RAG`
- `"conformal" iterative retrieval RAG stopping`
- `"distribution shift" iterative RAG abstention`
- `"risk-controlled" retrieval augmented generation`
- `"evidence sufficiency" provenance iterative retrieval`
- `"budgeted" "permission-aware" retrieval augmented generation`
- `"access control" temporal provenance RAG`
- `"adaptive retrieval" provenance budget abstention`

## False friends and downgrade rules

1. Generic RAG with fixed top-k retrieval and no retrieve/continue/stop decision is not adaptive evidence-gap completion.
2. Query rewriting without evidence-need detection or sufficiency assessment is a query-construction component, not the controller.
3. Multi-hop QA with a predetermined hop count is not evidence-driven stopping.
4. Closed-world benchmarks where an answer is guaranteed to exist do not validate the required open-world terminal states.
5. Recency ranking is not effective-time validity.
6. A "version-aware" paper about model checkpoints, software releases, API versions, index versions, or dataset releases does not address document-evidence lineage.
7. Post-hoc citation generation is not sufficient provenance if retrieval cannot identify which source version supplied the evidence.
8. Enterprise-search relevance work should be downgraded unless it materially addresses evidence gaps, authorization, temporal/version behavior, or bounded retrieval.
9. Searchable encryption is not enough merely because it contains the words secure or access-controlled retrieval; it must contribute relevant authorization semantics.
10. Permission filtering that silently hides results but cannot expose authorization denial as a distinct state is insufficient for gap-4 and gap-5.
11. Fixed-context no-answer classification is weaker than retrieval-aware unanswerability.
12. Confidence thresholding without calibrated risk/coverage behavior is weak evidence for safe stopping.
13. For gap-3, IID-only selective-prediction evaluation should be downgraded if no distribution shift or calibration drift is tested.
14. Generic conformal prediction is TRANSFER evidence only unless its guarantee is meaningfully connected to answering, abstaining, or retrieval termination.
15. Crawler, graph-search, optimizer, or training stopping rules are false positives when "stopping criterion" is unrelated to evidential sufficiency.
16. Retrieval-efficiency work reporting only ANN speed, index memory, or throughput is not cost-aware investigation.
17. For gap-6, counting only LLM tokens is incomplete; relevant work should approach end-to-end investigation cost.
18. Unrestricted web agents are outside the bounded read-only retrieval object.
19. Empty search results must not count as negative evidence unless source and query semantics support a completeness claim.
20. "Always retrieve the newest document" is not temporally correct when a question concerns an earlier effective state.
21. For gap-8, a paper covering one component cannot establish correctness of a combined controller. Integration must be evaluated, not inferred.
22. Workplace summarization over already collected messages is Topic 09-like behavior, not Topic 07 retrieval.
23. Recommendation and personalization retrieval are false positives unless they resolve an explicit factual evidence requirement.
24. Transfer results should be labeled TRANSFER; they must not be described as production-email validation.

A particularly important downgrade decision for this round is **component aggregation by the reviewer**. If paper A provides temporal retrieval, paper B provides provenance, and paper C provides conformal abstention, this still does not close gap-8. The literature itself must evaluate a controller that combines the relevant properties.

## Date policy

**Earliest publication year discovery must permit: 1970.**

A single modern recency cutoff would remove foundations required by the stopping portion of this topic.

The reject-option literature underlying selective prediction reaches at least to **On Optimum Recognition Error and Reject Tradeoff** from 1970. The other transfer foundations are also substantially older than modern RAG:

- temporal-database distinctions such as valid time and transaction time were developed in the 1980s;
- modern database provenance became a major formal literature by the early 2000s;
- **Time-Based Language Models** appeared in 2003;
- conversational rewriting and modern selective QA are much newer;
- modern RAG begins around 2020.

Discovery therefore should **permit literature back to 1970**, but it should not issue one undifferentiated 1970-present keyword search. Use family-specific searches:

- historical citation chasing for reject-option, temporal-database, provenance, and stopping foundations;
- mostly 2000-present searches for temporal IR, enterprise retrieval, and cost-aware information seeking;
- mostly late-2010s-present searches for conversational rewriting, answerability, and selective QA;
- mostly 2020-present searches for RAG and LLM retrieval controllers.

This preserves foundational terminology without allowing older unrelated IR literature to swamp the round-3 discovery pool.
