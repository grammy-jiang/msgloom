# Topic 01: Email conversation structure, branching, and inline replies

## Objective

Recover reply relationships and quotation structure without losing unique contributions or conflating conversation membership with Topic identity.

## Research questions

- Which deterministic metadata and text-based methods reconstruct parent/ancestor relations when headers or history are missing or inconsistent?
- How should new text, nested quotations, forwards, signatures, disclaimers, and interleaved replies be segmented and aligned to their source spans?
- How can a single email respond to multiple prior messages or spans while preserving uncertainty?
- How should forks, out-of-order arrivals, partial histories, and subsequent corrections be represented and evaluated?

## Search keywords

- `email thread reconstruction`
- `reply-to prediction`
- `conversation disentanglement`
- `email quotation extraction`
- `quoted text detection`
- `inline replies`

## Initial search queries

- `email "thread reconstruction"`
- `"conversation disentanglement"`
- `email "quotation extraction"`
- `email "inline replies"`

Read [shared context](../CONTEXT.md) before execution.

## Detailed scope for Topic 01

Study email conversation reconstruction and quotation/reply alignment as an evidence-preserving foundation for msgloom. A Group is not a Topic. Do not expand this study into implementing Topic classification, action extraction or a full RAG system.

Research questions:

- RQ1: What reliable reply/ancestry evidence is available from message metadata? How do methods handle absent, duplicated, malformed or conflicting identifiers, subject changes, forwards and partial exports?
- RQ2: How can original text, nested quotations, interleaved/inline replies, forwarded text, signatures and disclaimers be identified while preserving every unique decision-relevant contribution? Cover HTML and plain-text representations.
- RQ3: Can relations be attached to spans, and can one message respond to multiple parent messages or spans? Distinguish tree assumptions, graph representations, inferred links and unresolved references.
- RQ4: How do methods preserve forks, late and out-of-order arrivals, missing ancestors and later corrections? What can and cannot be inferred about participants seeing other branches?
- RQ5: Which deterministic baselines, statistical methods, neural approaches and LLM-assisted methods have relevant evidence, and what are their data, annotation, domain and computational assumptions?
- RQ6: Which datasets and annotations cover email-specific phenomena, and what transfer gaps remain for asynchronous business email? Assess leakage, near-duplicate quoted text, train/test splits, licensing and availability.
- RQ7: How should evaluation measure reply-edge precision/recall, ancestry/grouping errors, quotation/span alignment, loss of unique reply text, uncertainty/abstention and incremental corrections? Record exact task/metric/dataset definitions before comparing published numbers.
- RQ8: What minimal representation and evaluation plan should msgloom investigate next, which decisions are supported by evidence, and which remain engineering hypotheses?

Include adversarial/edge cases: two replies to the same parent; each branch later forwarded; a message answering two earlier messages; inline replies embedded within quotes; quote markers missing; HTML blockquotes or tables; duplicate history; forwarded header blocks; missing parent then late arrival; same subject on unrelated matters; changed subject in the same conversation; only part of a quoted proposal approved; conflicting or implausible reply metadata.

Look for relevant older email/Enron/thread-reassembly/quotation studies and newer conversation-disentanglement or reply-to prediction work. Do not assume chat benchmarks establish production-email accuracy. Check authoritative specifications/documentation for metadata semantics when necessary (for example message identifiers, reply/reference headers, IMAP threading and Microsoft Graph conversation metadata). Label those engineering sources separately, with exact URLs and access dates.

## Acceptance criteria for the research report

- Each RQ has an explicit answer, evidence links, confidence and residual gap.
- Clearly separate published results, standards/documentation facts, transfer hypotheses and msgloom proposals.
- Include a paper comparison table with metadata, direct-email versus transferred domain, method, supervision/data, assumptions, benchmark/metric, limitations, code/data/license, and whether full text or only abstract was examined.
- Major findings cite verified primary sources with section/page or saved-text locators; the References section has usable links/DOIs.
- Include a compact synthetic-case catalogue with expected relationship/preservation behaviour. It is an evaluation proposal, not a claim of executed benchmarking.
- Propose a small, justified set of next engineering experiments and explicit rejection criteria. Do not write application code or change design documents.
- Record actual search dates, query variants, sources, exclusions, search/download/conversion failures, stage counts, run IDs, and applicable reviewer/validation outcomes.
- Follow the installed Skill's report structure and gates. Do not present a draft as accepted; do not suppress or fabricate rejected gates.
- Use the Skill's gap-closure stopping rules; do not fill a paper quota with weakly relevant papers.
- Finish Topic 01 only. Leave Topics 02–10 unstarted.
