# Topic 02 reviewed execution plan

## Readiness verdict

Ready to start. This plan was reviewed against Topic 02 BRIEF.md, the completed Topic 01 acquisition and local-corpus workflow, the Topic 01 failure/recovery records, and the current msgloom design terminology.

The true starting point is manual academic corpus construction. The Research Pipeline begins only after the corpus is acquired, identity-checked, hashed, and coverage-reviewed.

## Non-negotiable semantic constraints

- **Topic** keeps the msgloom design definition: a work matter described by information from one or more sources. It is not a generic taxonomy label.
- A Group/conversation may contain several Topics. Conversation membership is not Topic identity.
- Within one message, Topic evidence may be non-contiguous and may have multiple Topic memberships.
- Topic segmentation must not silently remove conditions, evidence, exceptions, approval scope, or reply scope.
- Direct email/work-message evidence and transfer evidence remain separate.

## Phase A — manual academic corpus construction

1. Read BRIEF.md and authoritative shared/design context.
2. Audit every seed keyword: identify its standard academic meaning, fit, ambiguity, and likely false-positive literature.
3. Translate the product problem into academic task families and terminology.
4. Build query families per task family, with explicit DIRECT / TRANSFER roles.
5. Perform manual academic discovery from primary/canonical academic pages and trusted indexes.
6. Use strong seed papers to refine terminology and queries iteratively.
7. Maintain a candidate bibliography before bulk download.
8. Manually download clean public academic PDFs; no questionable mirrors. Respect >=30 s/provider project policy.
9. At acquisition time verify PDF title page/authors/artifact type/venue/year against the candidate record; then verify PDF signature, size, SHA-256, page count, and extraction sanity.
10. Record unresolved clean-OA candidates separately rather than lowering source quality.
11. Review corpus coverage by capability, not paper count.
12. Freeze the acquisition corpus and provenance before starting semantic full-text analysis.

## Phase B — Research Pipeline on the frozen local corpus

1. Preflight the actually installed Research Pipeline version and contracts; do not assume historical Topic 01 defects still exist.
2. Create an isolated Topic 02 run namespace.
3. Reconcile/import the already-acquired corpus honestly; no fabricated provider search/download receipts.
4. Screen all candidate papers against Topic 02 capability axes.
5. Convert/extract selected PDFs and run one full-text paper worker per selected paper.
6. Worker orchestration must verify that delegated work has real live workers; delegated + zero workers is a failure, not a wait state.
7. Validate worker schema, source locators, claim/source match, paper identity, task definition, metric definition, and limitations.
8. Run fresh cross-paper synthesis only after the selected paper set is complete and validated.
9. Run claim stages, render from the exact accepted synthesis, run a fresh independent reviewer, strict validation, publication, completion, and gap classification.
10. Record a Topic 02 retrospective for Topic 03.

## Reasoning-effort policy

The Skill remains unchanged. Fresh Codex workers receive explicit runtime effort overrides:

- planning/simple classification: medium
- screening: high
- ordinary paper analysis: high
- ambiguous/conflicting paper: xhigh
- unresolved contradiction after xhigh: max selectively
- cross-paper synthesis: xhigh
- independent reviewer: xhigh
- gap classifier: high

Do not claim a lower/higher effort merely from prompt wording; record the actual runtime model and effort per delegated worker.

## Topic 01 lessons enforced as gates

- Manual discovery/acquisition is the entry point.
- Brief keywords are seeds, not trusted academic terminology.
- Provider/API failure is not a literature gap.
- Direct-domain evidence is prioritised; transfer literature is bounded and labelled.
- PDF bibliographic identity is checked before analysis.
- Corpus size is not a stopping rule.
- Runner artifact existence alone is insufficient; semantic validation is independent.
- Do not conflate metrics from different tasks.
- Native delegation failure must fall back to verified independent workers.
- Accepted synthesis identity/hash must be the report input.
- Reviewer rejection/issues remain visible and cannot be overwritten.
- Historical/failed artifacts are preserved.

## Phase A exit gate

Research Pipeline execution is not allowed until all are true:

- terminology taxonomy reviewed;
- search/query provenance recorded;
- candidate bibliography exists;
- acquired PDFs have identity + integrity QA;
- provenance manifest exists;
- unresolved candidates are explicit;
- capability coverage has been reviewed;
- no paper-count quota is being used as evidence of adequacy.
