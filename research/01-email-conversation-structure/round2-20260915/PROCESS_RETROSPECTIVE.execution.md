# Topic 01 Round 2 execution retrospective

## Result

Topic 01 academic Round 2 completed successfully in recovery runner run `fb483e38f452`.

The true entry point remained **manual academic discovery and PDF acquisition before Research Pipeline execution**. Exactly three new papers passed the user-reviewed admission gate: H01 and H02 as one related DIRECT_EMAIL research line, and T01 as TRANSFER_METHOD evidence. No paper quota was used.

The final runner status is `complete`. The final report was independently reviewed, strictly validated, published, completion-checked and gap-classified. No application/design code, mailbox, deployment, service, commit or push was changed.

## Workflow that should be reused

1. Review the previous completed round and its failures before new discovery.
2. Translate product concepts into academic terminology before search.
3. Manually discover candidates and apply a capability-specific admission gate.
4. Download clean primary/canonical PDFs sequentially, respecting provider intervals.
5. Verify bibliographic identity and byte integrity separately at acquisition time.
6. Freeze the local corpus and provenance before starting the Research Pipeline.
7. Reconcile the local corpus honestly: `source_coverage.attempts=[]`; no fabricated provider search or download.
8. Use real runner gates; never edit workflow state manually.
9. Separate semantic reasoning from mechanical artifact construction where possible.
10. Validate exact source locators, hashes and task/metric meanings before synthesis.
11. Bind rendering to the exact accepted synthesis hash.
12. Use a fresh independent reviewer. Honor rejection and use bounded runner retry.
13. Strictly validate, publish, completion-check and classify gaps before calling the round complete.
14. Review resulting gaps by project importance before authorizing another academic round.

## What failed and what was learned

### 1. File-writing semantic screeners were unreliable

The first runner run `f471e319ea1c` reached semantic screening but two fresh high-effort screeners stalled after producing substantive reasoning without the required artifact/receipt. The runner retry budget was exhausted honestly; the run remains preserved as blocked.

A recovery run was then started rather than editing/copying the failed state. The successful pattern was:

`fresh no-tool semantic worker -> JSON judgment -> deterministic adapter -> schema/evidence validation -> runner submission`

This succeeded on the first recovery attempt. Future research should prefer this pattern for bounded semantic classification tasks.

### 2. Long paper-analysis threads could finish source work but hang during artifact finalization

H01/H02/T01 all completed substantive source reading and PDF checking, but the original worker processes later stopped emitting activity while preparing large output artifacts.

Important lesson: **a terminated process does not imply all work was lost**. H01 had already written a valid analysis before its process was terminated. Hash/time checks detected that and prevented accidental overwrite.

Successful recovery separated two responsibilities:

- difficult source interpretation used the planned effort (`H01=high`, `H02/T01=xhigh`);
- artifact finalization/reconciliation was bounded and independently validated.

For H02/T01 the stable pattern became fresh self-contained xhigh semantic JSON output followed by deterministic locator/provenance assembly. Future workers should not combine long full-text analysis with large artifact serialization when the two can be separated.

### 3. Monolithic cross-paper synthesis was too large for one generation turn

Several one-shot synthesis attempts hung during large-output generation even though source reasoning was already substantially complete. This was not solved by waiting longer or using `max`.

The successful pattern split synthesis into four small independent no-tool xhigh semantic sections:

- A: R2-A / A1 / A7;
- B: R2-B / structural A2;
- C1: source conflicts, gaps, readiness;
- C2: E1-E4 engineering proposals and synthetic cases.

All four exited successfully. A deterministic run-local assembler then mapped their validated findings into the installed `synthesis_report.schema.json`, validated every current paper/evidence ID, and ran the runner's own validation before submission.

This is a strong reason to make **sectioned semantic synthesis + deterministic schema assembly** the default for future deep research rather than asking one model turn to author a very large schema object.

### 4. Independent review found a real semantic presentation bug

Reviewer attempt 1 rejected the first synthesis/report. The Evidence Matrix put values from each paper analysis's `unsafe_assumptions` field under an unqualified `Assumptions` column. That transformed statements such as “recovered fragments equal a complete original” from explicit unsafe extrapolations into something a reader could interpret as accepted paper assumptions.

The rejection was submitted to the runner and the workflow genuinely blocked. The bounded retry was started at `paper-synthesizer`; no status was manually changed.

The repair changed only:

- the Evidence Matrix content, separating `SOURCE-STATED / UNVALIDATED MODEL ASSUMPTION`, `UNVALIDATED TRANSFER ASSUMPTION`, and `UNSAFE EXTRAPOLATION TO AVOID — NOT a source-accepted assumption`;
- the Evidence Matrix heading;
- one methodology note recording the rejected review and repair.

Fresh reviewer attempt 2 returned `accepted`, with faithfulness 0.98, coherence 0.96, gap completeness 0.97 and citation integrity true.

Lesson: schema-valid and citation-valid synthesis can still contain a semantic labeling error. Independent review must inspect claim roles, not merely IDs.

### 5. Event-stream silence is not sufficient to diagnose a hung Codex worker

During long reasoning, CLI event JSONL could remain unchanged while the underlying Codex rollout continued to receive reasoning items. A worker should be considered hung only after checking both:

- execution event activity; and
- the underlying rollout/session activity.

Future worker watchdogs should use both signals and distinguish semantic reasoning from artifact/output serialization.

## Reasoning-effort outcome

No `max` worker was necessary.

- parent/orchestration: high;
- screener semantic judgment: high;
- H01 analysis: high;
- H02/T01 difficult source review: xhigh;
- cross-paper semantic sections: xhigh;
- independent reviewer: xhigh;
- gap classifier: high.

The practical lesson is that higher effort did not fix large-output orchestration hangs. Smaller semantic tasks plus deterministic assembly were more effective than escalating to `max`.

## Evidence/research conclusions that remain bounded

Round 2 does not establish production email accuracy or approve an architecture.

- H01/H02 are one related direct-email research line.
- They support reconstruction of surviving quoted fragments and partial-order representation under assumptions; they do not recover unquoted missing text or validate online late-parent correction/retraction.
- T01 supplies transferable local passage-alignment mechanisms only; its reported results are not email accuracy.
- A1 primary-source acquisition is closed, but complete-original/source-span accuracy is still an engineering evaluation need.
- Structural A2 is only partially resolved.
- A7 remains academically open.
- E1-E4 remain the important engineering validation program.

## Pipeline/Skill improvements suggested by this execution

These are recommendations only; the installed Skill/package was not modified.

1. Add a first-class local-corpus import/reconciliation command.
2. Make semantic-worker output and deterministic schema/artifact serialization separate responsibilities by default.
3. Add worker heartbeat logic that observes rollout activity as well as CLI events.
4. Treat `final prose without required artifact/receipt` as a clear orchestration failure.
5. Prefer sectioned synthesis with deterministic assembly for deep profiles.
6. Record actual runtime model/effort automatically in delegated-worker provenance.
7. Make the report validator understand structured paper IDs / evidence IDs used by custom templates; this run's generic citation parser reported 0% citation coverage even though the independent reviewer verified citation integrity.
8. Preserve reviewer rejection and bounded retry as first-class workflow history.
9. Keep user-reviewed gap importance separate from automatic gap-classifier priority.

## Final integrity

`pipeline-workspace-recovery/audit/final-round2-audit.json` passed. It verifies the complete runner state, reviewed/validated/published report identity, synthesis/review/gaps artifacts, frozen PDF hashes, zero provider search attempts, local-only pipeline download reconciliation, and unchanged key Round 1 artifacts.
