# Topic 02 versioning policy

Git stores the durable research record, not the complete execution sandbox.

Committed assets include research briefs/plans, terminology and coverage decisions, acquisition manifests and hashes, canonical paper analyses, accepted synthesis/report/gaps/review/validation artifacts, post-round gap decisions, engineering-validation source/tests/fixtures/results, mutation/reproducibility audits, reviewer verdicts, and closure state.

Large or regenerable evidence stays in the local research workspace and is referenced through manifests/provenance: paper PDFs, rendered pages, raw worker/tool traces and event streams, dependency/package caches, converted text, claim dumps, and other execution intermediates. Their omission from Git does not mean they were deleted.

This follows the repository's large-file and secret-scanning policy and preserves exact reviewed/generated artifacts without rewriting them merely for formatting.
