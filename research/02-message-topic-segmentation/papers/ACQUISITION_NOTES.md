# Topic 02 acquisition notes

## Scope

This phase manually discovers and acquires a candidate academic PDF corpus **before** Research Pipeline semantic analysis. Downloading a paper does not mean it will be selected as final evidence, and no full-text research conclusion is claimed yet.

## Lessons carried from Topic 01

- The provider-driven search is not the primary discovery path. Academic terminology is refined first and papers are discovered manually from canonical/trusted academic pages.
- Direct-domain evidence is prioritized. Transfer papers are acquired only for a capability missing or needing comparison.
- PDF identity is checked during acquisition instead of waiting for a paper worker to discover a mismatch.
- Integrity and identity are separate checks.
- Unresolved clean-OA candidates remain explicit rather than being filled from questionable mirrors.
- Same-provider download requests are spaced by at least 31 seconds. No retry loops are used for manual acquisition.

## Seed batch status

The first two acquisition batches contain 12 PDFs: 3 DIRECT_EMAIL, 3 DIRECT_WORK, 4 TRANSFER_SEGMENTATION, and 2 TRANSFER_SPAN. All 12 passed PDF signature, byte-count, SHA-256 and pdfinfo/page-count checks; all 12 downloads succeeded with no retry.

Title-page extraction cleanly confirms 11 of 12 identities. T01 (Hearst 1997 TextTiling) has garbled local text extraction caused by the saved PDF's encoding; its exact canonical Berkeley PDF URL and canonical Berkeley publication metadata match the artifact. This limitation is kept explicit.

The arXiv-hosted D03 PDF downloaded successfully as a single manual PDF request. This does **not** establish recovery of the arXiv API used by the historical Topic 01 pipeline search; the access path and request are different.

## Current discovery emphasis

The direct-email Joty line is the primary evidence anchor. D01's acquisition-stage inspection shows that its topic annotation permits multiple relevant topic labels on a sentence, making `topic assignment`, `topical clustering`, and sentence-level topic membership stronger search terms than generic whole-message `multi-label text classification`. Formal evidence extraction is deferred to the later paper worker.

General dialogue segmentation, contiguous document segmentation, and discontinuous/overlapping span methods remain explicitly labelled transfer evidence.
