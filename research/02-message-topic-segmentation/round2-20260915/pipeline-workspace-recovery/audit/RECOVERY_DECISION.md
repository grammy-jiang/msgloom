# Topic 02 Academic Round 2 runner recovery decision

The first Round 2 runner run `f7a0a6a5051c` completed all paper analyses and accepted synthesis attempt 2, but the fresh independent reviewer rejected the rendered report for one citation/provenance defect: `R2-C-F07` mixed a C01-supported task-boundary statement with the project decision to hand G10-A/G10-E to Topic 03.

The reviewer required a synthesis/traceability repair. The original run could not retry `paper-synthesizer` because its two-attempt retry budget was already exhausted by an earlier runner-contract repair. The runner explicitly returned: `Task retry budget exhausted; investigate before starting a new run`.

Therefore:

- the original run remains preserved and blocked;
- no workflow state is edited manually;
- this recovery workspace creates a **new runner run**;
- the frozen six-paper corpus is unchanged;
- accepted per-paper high analyses, focused xhigh adjudications, and three xhigh synthesis-section outputs are reused read-only with hash provenance rather than recomputed;
- the only semantic repair authorized is to split `R2-C-F07` into:
  1. a paper-backed C01 task-boundary finding; and
  2. a process-only Topic 03 handoff with GAP_REVIEW_DECISION provenance and no paper citation;
- all downstream artifacts are regenerated from the repaired synthesis and reviewed by a **new independent reviewer**.

This is orchestration recovery, not a new academic discovery round.
