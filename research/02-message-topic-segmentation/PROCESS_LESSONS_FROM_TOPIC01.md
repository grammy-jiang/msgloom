# Topic 02 process lessons inherited from Topic 01

These are execution gates, not optional advice.

## Academic discovery and acquisition

1. Start with project-value gap review, not automatic classifier priority.
2. Translate product concepts to academic task terminology before searching.
3. Manually discover candidates; use strong papers to refine terminology iteratively.
4. Apply a capability-specific admission gate; do not target a paper count.
5. Download only clean primary/canonical public PDFs, with conservative per-provider spacing.
6. Verify bibliographic identity separately from byte integrity at acquisition time.
7. Freeze corpus/provenance before Research Pipeline execution.
8. Provider/API failure is not evidence of a literature gap.

## Research Pipeline

1. New Round 2 state must be isolated; Round 1 is read-only context.
2. Local-corpus reconciliation must honestly record zero provider attempts/downloads where applicable.
3. Prefer `fresh semantic worker -> small JSON judgment -> deterministic adapter -> runner validation` for bounded classification tasks.
4. Separate difficult semantic reasoning from large artifact serialization.
5. Use high by default, xhigh only for material ambiguity/source conflicts, max only after xhigh cannot resolve a material contradiction.
6. A delegated task with zero live workers is orchestration failure, not progress.
7. Diagnose worker hangs using both runner/event activity and underlying rollout/session activity.
8. Preserve failed attempts and exact artifact hashes; never edit workflow state manually.

## Synthesis and review

1. Avoid monolithic large synthesis turns. Prefer small independent xhigh semantic sections plus deterministic schema assembly.
2. Validate all paper/evidence IDs and source roles before runner submission.
3. Render from the exact accepted synthesis hash.
4. Fresh independent review must be able to reject.
5. Reviewer rejection must block the workflow and trigger bounded repair/re-review, not softer wording or manual status changes.
6. Strict validation, publication, completion, and gap classification are separate gates.
7. Review gaps by project importance again after the round; pipeline completion is not research convergence.

## Engineering-validation methodology

Topic 01 independent reviews exposed methodological defects that must be prevented from the start:

1. Synthetic gold must be authored independently of the component under evaluation.
2. End-to-end denominators must include false-positive predictions, not only gold-matched predictions.
3. Arrival-time evaluation must not use future context; final/full-context diagnostics must be named separately.
4. One-to-one or set-valued matching rules require regression/mutation tests.
5. Representation capability, detection, assignment, and semantic scope are distinct metrics.
6. Experiment execution status and independent-review acceptance status must be separate machine-readable concepts.
7. Production representativeness cannot be claimed without future user-reviewed domain data.
8. A fresh engineering reviewer should rerun tests, regenerate artifacts in a temporary directory, inspect denominators, and use targeted mutations where useful.

## Version-control boundary

Follow Topic 01's curated repository policy:

- version reports, synthesis, gaps, manifests/provenance, code, tests, metrics, compact audits, and reviewer verdicts;
- keep large raw PDFs, rendered pages, raw event streams, giant intermediate claim dumps, generated fixtures, and run-local dependencies local-only when repository policy rejects them, with hashes/provenance retained.
