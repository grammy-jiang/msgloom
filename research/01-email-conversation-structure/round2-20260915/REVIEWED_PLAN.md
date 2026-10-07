# Topic 01 Round 2 — reviewed execution plan

## Readiness verdict

READY. The full acquisition-to-publication workflow was rechecked against Topic 01 Round 1 and Topic 02 Round 1 execution evidence before starting this round. The prior mistake—claiming review without reconstructing the true manual-acquisition starting point—is explicitly addressed by the process gate in `PROCESS_RETROSPECTIVE.md`.

## Phase A — manual academic corpus construction

1. Re-read Topic 01 Brief and Round 1 synthesis/gaps; freeze Round 2 scope to R2-A/R2-B only.
2. Audit Round 1 seed/gap terms and convert them to academic terminology.
3. Build query families for incomplete/incremental reconstruction and quotation-source alignment.
4. Search manually across canonical/trusted academic pages and indexes. Do not invoke Research Pipeline provider search.
5. Start from Round 1 high-value cited leads, then refine vocabulary from titles/abstracts/related-work terminology.
6. Maintain a candidate bibliography with DIRECT_EMAIL / TRANSFER_METHOD role, R2 stream, relevance, canonical source and OA status.
7. Apply the paper admission gate before download.
8. Download clean public PDFs manually. Sequential requests; >=31 seconds to the same provider; no aggressive retry loops.
9. At acquisition time verify PDF identity from the file itself and canonical metadata, plus `%PDF`, byte size, SHA-256, page count and extraction sanity.
10. Record unresolved candidates rather than lowering provenance quality.
11. Review coverage by R2 capability, not paper count.
12. Freeze corpus and provenance before semantic full-text analysis.

## Phase B — governed Research Pipeline over frozen local corpus

1. Re-preflight installed Pipeline/Skill contracts at launch time.
2. Create a new isolated namespace; Round 1 artifacts remain untouched.
3. Reconcile local candidates honestly with zero provider-search/download claims.
4. Screen against R2-A/R2-B capability axes; do not select merely because a paper is historically relevant.
5. Convert/extract locally and launch one fresh Codex worker per selected paper, maximum 3 live workers.
6. Default paper worker `high`; source-driven `xhigh`; selective `max` only if xhigh leaves a material analytical contradiction.
7. Validate schema, identity, LF locators, exact source quote matches, metric/task/population definitions, limitations and actual runtime effort.
8. Parent semantic review is required for every paper; preserve all failed/retry attempts.
9. Run fresh xhigh cross-paper synthesis only after all selected papers are accepted.
10. Claim stages use verified source-backed findings; failed adapters remain preserved and may be repaired only against actual installed contracts.
11. Render from exact accepted synthesis hash; fresh xhigh independent reviewer; strict validation; publish identical bytes; completion; high gap classifier.
12. Produce Round 2 retrospective and separate remaining academic versus engineering gaps. Do not automatically start Round 3.

## Runtime reasoning policy

- planning / bookkeeping: medium
- semantic screening: high
- normal paper analysis: high
- ambiguous/conflicting paper: xhigh
- unresolved analytical contradiction after xhigh: max selectively
- synthesis: xhigh
- independent reviewer: xhigh
- gap classifier: high

Every fresh Codex worker must receive an explicit runtime override because the user's global Codex config currently uses `max`.
