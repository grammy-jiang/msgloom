# Topic 01 paper acquisition notes

## Scope of this pass

This pass builds a **candidate PDF corpus only**. It does not claim full-text reading, paper-level analysis, benchmark comparison, or research convergence.

Selection was deliberately biased toward **direct email evidence**. Adjacent conversation-disentanglement work was capped so that chat/forum benchmarks do not dominate the evidence base for an asynchronous business-email problem.

## Search taxonomy used

1. **Email threading / reconstruction** — email threading, thread reconstruction, thread reassembly, parent/reply relation, reply tree, conversation reconstruction.
2. **Quotation / span relations** — quoted text, reply lines, inline replies, fragment quotation graphs, sentence quotation graphs, question–answer pairing, replies as annotations.
3. **Email body structure** — email zoning, signature/reply extraction, forwarded content, cleaning, template/boilerplate induction, mailing-list preprocessing.
4. **Transfer methods** — conversation disentanglement, thread reconstruction and reply-to prediction in chat/newsgroup/forum-style corpora.

## Sources represented in the downloaded corpus

The downloaded PDFs come from a deliberately mixed set of public academic sources rather than one API or index: ACL Anthology, arXiv, AAAI proceedings, PVLDB, NIST TREC, Microsoft Research, LDC public materials, ALTA proceedings, institutional repositories (including EPFL and NOVA University Lisbon), and university/author publication sites (including CMU, NYCU, HDU, TU Darmstadt UKP, HPI, UBC, TU Delft and Tsinghua).

Discovery also used bibliographic/index pages and publisher records to identify papers and validate identity. A discovery hit was **not** sufficient by itself to justify downloading from a questionable mirror.

## Request behavior

Downloads were sequential. The acquisition scripts enforce a minimum 31-second interval when more than one request is made to the same provider host in a run, matching the project's conservative 30-second-per-provider policy.

## Current corpus boundary

- `direct-email/` contains work whose primary object is email structure or a directly relevant email-body/reply representation task.
- `transfer-conversation/` contains a bounded set of adjacent conversation-disentanglement/thread-reconstruction work.
- Engineering specifications and product documentation remain in `../supporting/engineering/`; they are not counted as academic papers.
- High-value academic papers for which no clean OA PDF was resolved are listed in `PENDING_CANDIDATES.md` rather than silently omitted or downloaded from an uncertain mirror.
