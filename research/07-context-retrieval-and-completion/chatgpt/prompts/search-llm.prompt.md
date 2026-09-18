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

Research topic: **Unified iterative RAG stopping and provenance control under distribution shift: search specifically for controllers that combine structured evidence sufficiency with temporal/version-aware provenance and calibrated or conformal risk-controlled stopping, including any systems that additionally integrate permission-aware access or bounded retrieval budgets.**

Must-have terms: unified, iterative, rag
Nice-to-have terms: provenance, under, distribution, shift:, search, specifically, controllers, combine, structured, evidence, sufficiency, temporal/version-aware, calibrated, conformal, risk-controlled, stopping,, including, any, systems, additionally, integrate, permission-aware, access, bounded, retrieval, budgets.
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
- F1 [TRANSFER]
    "question decontextualization" retrieval unresolved antecedent evidence
    "conversational query rewriting" missing context retrieval
    "query reformulation" conversational search unresolved reference retrieval
    "question-in-context rewriting" evidence retrieval
- F2 [DIRECT]
    "evidence coverage" multi-hop retrieval expected claims
    "structured evidence" multi-hop question answering retrieval planning
    "query decomposition" iterative retrieval compositional question answering
    "multi-entity" multi-hop retrieval temporal constraints question answering
    "compositional retrieval" evidence sufficiency multi-hop
    "structured evidence requirements" retrieval planning question answering
    "evidence graph" iterative retrieval sufficiency
- F3 [DIRECT]
    "adaptive retrieval" RAG iterative stopping
    "active retrieval augmented generation" iterative retrieval confidence
    "self-reflective retrieval" RAG retrieve on demand
    "adaptive RAG" retrieve more evidence stop
    "dynamic retrieval" RAG controller iterative
    "retrieval necessity" RAG adaptive retrieval
- F4 [DIRECT]
    "verification-aware stopping" retrieval augmented
    "evidence coverage" stopping retrieval agent
    "retrieval stopping" evidence sufficiency multi-hop
    "claim-evidence alignment" stopping search agent
    "multi-round RAG" stopping criterion sufficiency
    "retrieval termination policy" evidence coverage RAG
    "stopping judgment" iterative RAG evidence
- F5 [TRANSFER]
    "selective question answering" domain shift abstention
    "answer abstention" out-of-distribution question answering calibration
    "risk-coverage" question answering domain shift
    "selective prediction" question answering distribution shift calibration
    "reject option" question answering uncertainty
- F6 [DIRECT]
    "conformal" retrieval augmented generation stopping
    "conformal retrieval" evidence acquisition
    "conformal risk control" RAG retrieval
    "certified generation risk" RAG distribution shift
    "information-directed conformal retrieval"
    "conformal abstention" RAG
    "risk-controlled" RAG retrieval stopping
    "conformal prediction" adaptive retrieval question answering
- F7 [DIRECT]
    "temporal information retrieval" effective time document versions
    "time-aware retrieval" temporal validity question answering
    "temporal RAG" historical version effective time
    "time-sensitive retrieval" multi-hop question answering
    "recency-aware retrieval" temporal validity version
    "temporal question answering" evolving documents retrieval
- F8 [TRANSFER]
    "valid time" "transaction time" retrieval augmented generation
    "effective time" document retrieval version
    "bitemporal" RAG retrieval
    "valid-time" question answering evolving documents
    "transaction-time" information retrieval provenance
    "application time" version-aware retrieval
- F9 [DIRECT]
    "versioned document QA"
    "version-aware retrieval augmented generation"
    "document version lineage" retrieval question answering
    "version graph" RAG temporal
    "evolving documents" retrieval QA provenance
    "supersession" version-aware retrieval RAG
    "historical version" RAG question answering
- F10 [DIRECT]
    "provenance-aware retrieval" RAG lineage
    "attributed question answering" retrieval evidence source
    "source attribution" RAG claim evidence provenance
    "evidence provenance" multi-hop question answering
    "claim-level attribution" retrieval augmented generation
    "source lineage" RAG retrieval evidence
    "provenance" versioned documents retrieval augmented generation
- F11 [DIRECT]
    "retrieval-time gating" RAG authorization
    "permission-aware retrieval" RAG
    "access-controlled retrieval" RAG ABAC
    "multitenant" RAG retrieval authorization
    "policy-aware retrieval" RAG lineage
    "attribute-based access control" vector retrieval RAG
    "identity-aware retrieval" RAG permissions
    "authorization-aware retrieval" retrieval augmented generation
- F12 [DIRECT]
    "budgeted evidence acquisition" RAG
    "adaptive budgeted retrieval augmented generation"
    "cost-aware evidence selection" RAG
    "cost-aware RAG" stop retrieval
    "retrieval budget" multi-hop question answering stopping
    "latency" "token cost" adaptive RAG retrieval
    "evidence access budget" retrieval augmented generation
    "budget exhaustion" RAG stopping
- F13 [DIRECT]
    "unanswerability detection" RAG retrieval failure
    "answerability prediction" retrieved evidence sufficiency
    "retrieval failure" RAG abstention empty results
    "negative evidence" retrieval question answering
    "missing evidence" RAG abstention
    "empty retrieval" question answering abstention
    "access denied" retrieval augmented generation unanswerable
    "source unavailable" RAG abstention
- F14 [DIRECT]
    "adaptive RAG controller" provenance temporal permission conformal
    "retrieval controller" version-aware authorization calibrated stopping
    "iterative RAG" evidence coverage version provenance conformal
    "risk-controlled" retrieval permission provenance temporal
    "version-aware" "conformal" RAG retrieval stopping
    "policy-aware" "conformal" RAG
    "permission-aware" "version-aware" RAG
    "adaptive retrieval" provenance "access control" RAG
    "temporal RAG" conformal stopping provenance
    "retrieval controller" evidence sufficiency budget authorization
- F15 [DIRECT]
    "enterprise email" RAG multi-hop permissions
    "workplace communication" retrieval augmented generation evidence
    "email question answering" attachments retrieval permissions
    "enterprise search" versioned documents access control RAG
    "organizational knowledge" adaptive RAG provenance
    "enterprise RAG" temporal provenance permissions evaluation
    "workplace documents" multi-hop retrieval access control
    "enterprise communication" evidence retrieval stale conflicting documents
False friends — these match the words but not the capability, so do
not list them:
- Downgrade generic one-shot RAG that never decides whether to retrieve again or when evidence is sufficient.
- Downgrade adaptive RAG that only routes once among no-retrieval, single-hop, and multi-hop strategies without iterative reassessment.
- Downgrade iterative retrieval that simply runs a fixed number of hops or stops at a hard maximum with no semantic sufficiency signal.
- Downgrade stopping based only on generator confidence, entropy, token probability, or self-consistency when there is no explicit evidence-coverage or support check.
- Downgrade query rewriting or decontextualization papers that stop after producing a standalone query and do not study evidence acquisition.
- Downgrade multi-hop QA that assumes oracle supporting documents, oracle decompositions, or a known hop count when no stopping decision is learned or evaluated.
- Downgrade temporal retrieval that merely boosts recent documents; recency is not equivalent to validity for historical or effective-time questions.
- Downgrade work that uses publication timestamp only and does not distinguish content time, valid or effective time, and collection or transaction time where those distinctions matter.
- Downgrade version-aware work when 'version' means software-package, code, model, API, or dependency version rather than evolving evidence documents, unless its lineage method is explicitly transferable.
- Downgrade document-version systems that attach a version label but do not preserve supersession, change lineage, or the relationship between retrieved evidence and the referenced version.
- Downgrade provenance work that provides citations without binding claims to a specific source identity or document version when version lineage is the target gap.
- Downgrade generic database provenance that never participates in retrieval selection, stopping, or evidence validation; retain only as TRANSFER if lineage semantics are useful.
- Downgrade conformal or calibrated generation work that calibrates only the final answer while retrieval depth and stopping remain fixed; it can be TRANSFER evidence for risk control but not direct evidence for iterative stopping.
- Downgrade studies claiming distribution robustness when calibration and evaluation are purely IID and no distribution-shift setting or assumption is analyzed.
- Downgrade conformal guarantees whose assumptions are incompatible with the claimed non-stationary setting unless the paper explicitly handles or bounds that shift.
- Downgrade secure-RAG work concerned only with prompt injection, poisoning, encryption, or privacy when it does not enforce user-specific authorization over retrieved evidence.
- Downgrade access-control mechanisms applied only at ingestion or storage if retrieval-time authorization for the requesting identity is not enforced.
- Downgrade permission-filtered retrieval if the system never reassesses sufficiency or issues a replenishment query after unauthorized candidates are removed.
- Downgrade enterprise-search product pages, vendor documentation, architecture blogs, and benchmark-free demonstrations when the discovery stage is seeking academic evidence.
- Downgrade budgeted retrieval that optimizes compute, top-k, or latency without measuring answer support, evidence completeness, abstention, or missed evidence.
- Downgrade cost evaluations that report only LLM token cost while omitting retrieval calls, retrieved passages, reranking, planner or judge inference, authorization checks, or wall-clock latency when claiming end-to-end cost.
- Downgrade studies that treat empty retrieval as evidence that the proposition is false unless the retrieval source and query semantics justify closed-world negation.
- Downgrade evaluations that collapse authorization denial, empty search, unavailable source, extraction failure, exhausted budget, and genuine negative evidence into one generic 'no answer' label when gap-5 is being targeted.
- Downgrade tool-use agents whose retrieval is unbounded autonomous browsing or whose primary actions modify external systems; Topic 07 requires bounded evidence acquisition.
- Downgrade recommendation retrieval, ad retrieval, product search, and other retrieval tasks that do not answer a bounded evidential question.
- Downgrade transfer-domain results presented as proof of workplace-email accuracy. They may justify mechanisms or experiments but not production representativeness.
- For gap-8, do not admit a paper as an integrated-controller solution merely because separate modules for provenance, security, calibration, or budgeting could theoretically be composed; the joint behavior must actually be implemented and evaluated.
Reach back to 1970 at least. Do not impose one modern recency cutoff across all task families. The controller itself is modern, with RAG emerging in 2020 and most adaptive or conformal RAG work appearing from 2023 onward, but two required intellectual lineages are much older. Selective prediction and abstention trace at least to C. K. Chow's 1970 reject-option work, while precise temporal-validity semantics are established in temporal-database work by the mid-1980s, and temporal information retrieval has important work from the early 2000s, including Time-Based Language Models in 2003. Discovery should therefore be capable of reaching 1970 for foundational TRANSFER families while prioritizing 2020-2026 for DIRECT integrated-RAG controller queries. No global 2018, 2020, or 2023 cutoff should be applied.

This is gap-closure round 4 of at most 4 for the
original topic **evidence-gap-driven context retrieval and completion for workplace communication: turning an explicit evidence gap into bounded retrieval, deciding what to fetch next, and knowing when to stop, while preserving permissions, versions, temporal validity, cost and uncertainty**. Earlier rounds could not
close the open gaps below. Run every suggested query as well, and look
specifically for papers that answer these gaps:
- gap-1 [ACADEMIC, HIGH]: Structured gap representations remain insufficiently validated for temporal constraints, multi-entity joins, and complex compositional evidence requirements; the corpus contains structured-gap, temporal-retrieval, and query-planning methods, but no admitted study evaluates these capabilities together.
    suggested query: "structured evidence gap" temporal constraints multi-entity joins compositional retrieval iterative RAG
    searched in rounds: [1, 2, 3] (still open)
- gap-2 [ACADEMIC, HIGH]: No admitted study validates an iterative evidence-gap retrieval loop that jointly preserves document-version lineage, freshness or effective-time validity, and structured sufficiency decisions.
    suggested query: "version-aware retrieval" temporal provenance iterative RAG document lineage freshness effective-time sufficiency
    searched in rounds: [1, 2, 3] (still open)
- gap-3 [ACADEMIC, HIGH]: Stopping reliability under domain shift remains open: sufficiency, confidence, conformal, and stability signals guide stopping in separate studies, but no admitted study provides a general bounded-risk iterative-RAG stopping guarantee under distribution shift.
    suggested query: "iterative RAG" calibrated stopping domain shift conformal risk control selective prediction adaptive retrieval
    searched in rounds: [1, 2, 3] (still open)
- gap-8 [ACADEMIC, HIGH]: No admitted study validates a single controller that jointly handles structured evidence gaps, permission-aware source access, version lineage, temporal validity, calibrated stopping, abstention, and total-cost budgeting; the reported successes remain component-level or cover smaller subsets of these functions.
    suggested query: "adaptive RAG controller" permission-aware provenance temporal version calibrated stopping abstention budget
    searched in rounds: [1, 2, 3] (still open)

Papers already reviewed in earlier rounds (do NOT list them again):
1904.06019, 2010.11915, 2105.04166, 2112.08558, 2208.02814, 2210.03350, 2212.10509, 2305.06983, 2310.11511, 2403.10081, 2406.10490, 2406.19215, 2411.06037, 2412.15540, 2508.01084, 2510.08109, 2510.13590, 2510.14337, 2601.19827, 2603.28444, 2604.01413, 2604.23783, 2604.25676, 2605.03534, 2606.05658, 2606.13814, 2606.15964, 2606.29054, 2606.29090, 2606.29959, 2607.24010, 2607.27726, 2608.13237, 2609.11572, 2609.16301, doi-10-1038-s41598-026-71936-x, doi-10-1109-access-2025-3628960, doi-10-1145-1247715-1247720, doi-10-1145-1571941-1572085, doi-10-1145-181550-181560, doi-10-1145-3786625, doi-10-1609-aaai-v39i14-33670, doi-10-18653-v1-2026-acl-long-1562, doi-10-18653-v1-2026-findings-acl-2090, doi-10-32604-cmc-2026-086343

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
