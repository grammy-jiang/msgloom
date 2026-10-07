# Topic 01 versioned-artifact policy

Topic 01 keeps research conclusions, provenance, hashes, executable validation code, tests, and accepted review artifacts in Git. Large or mechanically generated raw evidence remains local because the repository pre-commit policy rejects files over 500 KiB and because raw execution streams are not maintainable source artifacts.

## Versioned

- research briefs, plans, terminology notes, retrospectives, current/deferred status;
- acquisition manifests, bibliographic metadata, source-access notes and SHA-256 provenance;
- accepted cross-paper synthesis, final research reports, classified gaps and key validation/reviewer receipts;
- engineering-validation source, tests, gold JSON/fixture manifest, deterministic metrics, results, closure audit and independent reviewer verdicts;
- compact standards/product-document snapshots that remain below repository size limits.

## Local-only but provenance-preserved

- academic PDF bytes and pipeline download copies;
- rendered PDF page images;
- raw Codex/pipeline event streams;
- large decomposed/scored claim dumps and paper-summary JSONL intermediates;
- generated RFC 5322 `.eml` fixture bytes;
- run-local Python dependencies and package caches.

The local-only assets are not treated as absent. Their identities and hashes remain in the versioned manifests/audits, and the canonical synthetic `.eml` fixtures are deterministically regenerable from `engineering-validation/src/topic01_validation/fixtures.py`.

This policy does not alter the historical Research Pipeline artifacts or their scientific meaning. It defines only what belongs in the source repository.
