# Topic 01 Round 2 acquisition notes

## Scope

This is a targeted follow-up corpus, not a re-run of Topic 01 Round 1. Academic admission is restricted to R2-A incomplete/incremental reconstruction and R2-B robust quote-occurrence -> source-span alignment.

## Acquisition method

- Discovery was manual and terminology-led; Research Pipeline provider search was not used.
- Canonical author/institution URLs were preferred.
- Requests used no retry loop.
- The two UBC requests were separated by 31 seconds because they share a provider host.
- Identity was checked from the PDFs themselves, separately from byte integrity.
- A first QA shell failed because local `xxd` is absent; the failure is preserved in `../audit/acquisition-qa-command-failure.md`, and Python was used for magic-byte inspection without installing a new package.

## Frozen admitted candidates so far

- H01 — DIRECT_EMAIL — Discovery and Regeneration of Hidden Emails (SAC 2005)
- H02 — DIRECT_EMAIL — Scalable Discovery of Hidden Emails from Large Folders (KDD 2005)
- T01 — TRANSFER_METHOD — Detecting and Modeling Local Text Reuse (JCDL 2014)

H01/H02 are one related research line, not independent replications. H01 contributes the precedence/partial-order reconstruction model; H02 adds robustness/scalability evaluation on Enron. T01 is transfer-only and is admitted solely for evaluated local passage alignment/source-location methods.

No downloaded file duplicates a Round 1 PDF by SHA-256. All three have `%PDF-` magic, successful `pdfinfo`, non-empty full-text extraction, and title-page identity checks.
