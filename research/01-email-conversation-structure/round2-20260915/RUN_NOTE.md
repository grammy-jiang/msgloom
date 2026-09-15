# Topic 01 Round 2 — complete

## Run

- Active successful runner: `pipeline-workspace-recovery/workflow_state.json`
- Run ID: `fb483e38f452`
- Profile: deep
- Final runner status: **complete**
- New academic PDFs: **3** (`H01`, `H02`, `T01`)
- Full-text analyzed: **3/3**
- Provider search attempts inside the pipeline run: **0**
- Pipeline PDF downloads: **0 new / 3 skipped_exists / 0 failed**

The earlier runner attempt `f471e319ea1c` is preserved as a failed/blocked screening attempt and is not the successful research run.

## Final gates

- paper-analyzer: accepted
- paper-synthesizer: accepted on bounded retry attempt 2
- analyze-claims: accepted
- score-claims: accepted
- report: accepted on bounded retry attempt 2
- review-synthesis: accepted on bounded retry attempt 2
- validate-report: accepted, strict validation `PASS`
- publish-report: accepted
- check-completion: accepted
- classify-gaps: accepted

Reviewer attempt 1 was genuinely rejected for a semantic Evidence Matrix labeling problem. The rejected bytes and verdict remain archived. The bounded repair changed only the Evidence Matrix labeling/heading and a methodology audit note. Fresh reviewer attempt 2 accepted the corrected artifact with faithfulness 0.98, coherence 0.96, gap completeness 0.97 and citation integrity true.

## Final artifacts

- Published report: `topic-01-round-2-incomplete-email-reconstruction-and-robust-quotation-source-span-alignment-research-report.md`
  - SHA-256: `02c2e28d5d3871ab545f32b16266bdcecd6008334324307f1ae16b836be8a544`
  - 67,122 bytes
  - byte-identical to the reviewed and validated draft
- Accepted synthesis: `pipeline-workspace-recovery/runs/fb483e38f452/analysis/synthesis.json`
  - SHA-256: `ce366833b1b25348c536817d033b8743b0e7dbd1b83155e47be9bf532d677173`
- Accepted reviewer verdict: `pipeline-workspace-recovery/runs/fb483e38f452/review/synthesis_review.json`
  - SHA-256: `861cc20bbf5a419e6eebe7ce7760a12caa0292532735dc42c0da11408f0faa2e`
- Strict validation: `pipeline-workspace-recovery/runs/fb483e38f452/validate/validation_result.json`
  - SHA-256: `6faf938e5e8eba19d4e7306d4299e9ac70b1e56db7b81d6c7139e15d1287fc76`
- Gap classification: `gaps.json`
  - SHA-256: `a168344ec921aad1b58f19afa53cf4c455d5a02323f367074cdc1af2e65681c0`

## Gap outcome

10 remaining classified gaps:

- ACADEMIC: **2**
  - A2 structural robust quote/source-span evidence — MEDIUM
  - A7 modern/incremental/LLM direct-email reconstruction — HIGH
- ENGINEERING: **6**
  - E1–E4 HIGH
  - E5 MEDIUM
  - E6 LOW
- OUT_OF_SCOPE for this follow-up: **2**
  - A3/A4/A6 deprioritized by the user-reviewed scope
  - A5 / semantic A2 transferred to Topic 04

A1 is no longer an academic acquisition gap. `convergence.should_continue=false` with reason `user_marked_out_of_scope`: no automatic Topic 01 Round 3 is authorized. This is an authorization boundary, not literature exhaustion.

## Integrity

`pipeline-workspace-recovery/audit/final-round2-audit.json` is `PASS`.

It additionally verifies that the key Round 1 report, synthesis and gaps hashes remain unchanged.
