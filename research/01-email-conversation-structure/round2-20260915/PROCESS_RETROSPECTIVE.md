# Topic 01 Round 2 — process retrospective and inherited gates

## Evidence reviewed before this round

This round was not started from the previous final summary alone. The workflow was rechecked against:

- Topic 01 `BRIEF.md`, `papers/ACQUISITION_NOTES.md`, `papers/PENDING_CANDIDATES.md`;
- successful Topic 01 local-corpus `RUN_NOTE.md` and runner state;
- Topic 02 `REVIEWED_PLAN.md`, `TERMINOLOGY_ANALYSIS.md`, `papers/ACQUISITION_NOTES.md`;
- Topic 02 `audit/RUN_DIARY.md`, including verifier compatibility, locator, worker, escalation, claim-adapter, review and report lessons;
- current installed `research-pipeline 0.33.0`, Skill manifest `2.1.0`, Codex CLI `0.154.0`;
- current global Codex reasoning effort is `max`, therefore all delegated workers in this round must explicitly override effort.

## True starting point

The research begins with **manual academic terminology refinement, discovery and PDF acquisition**. Research Pipeline search/download is not the academic discovery mechanism. The Skill begins only after a local corpus has been identity-checked, integrity-checked, coverage-reviewed and frozen.

## Topic 01 Round 1 failures / lessons that must not recur

1. Provider/API failures are access-path failures, not literature gaps. Do not use provider search as the primary discovery path.
2. Brief keywords are seeds only. Convert product language into academic task terminology, then refine terms from strong seed papers before broad acquisition.
3. Direct email evidence dominates; transfer evidence is admitted only for a capability direct email does not cover.
4. Verify title page, authors, artifact type, venue/year at acquisition time. Bibliographic identity and PDF byte integrity are separate gates.
5. Clean OA unresolved candidates remain explicit; never use questionable mirrors to fill a quota.
6. Same-provider paper requests are sequential with >=31 seconds between requests. No retry loops that hammer a provider.
7. A corpus count is never a stopping rule. Coverage is judged by the research capabilities required by the Brief.
8. A delegated stage must have a real live worker. `delegated + expected work + zero live workers` is an orchestration failure.
9. Paper workers are bounded to at most 3 concurrently. Execution receipts, prompt hashes, model and actual reasoning effort are recorded.
10. LF (`\n`) line numbering is the canonical locator convention; form-feed page separators do not create extra line numbers.
11. Schema-valid output is not semantic acceptance. Major claims require source locators, quote/source matching, correct task/metric population, and parent semantic review.
12. Preserve source contradictions; never silently repair a paper. Distinguish different denominators, configured versus realised outputs, different task metrics and unknown implementation details.
13. Default paper analysis effort is `high`; use `xhigh` only for actual ambiguity/conflicting source evidence, preferably proactively after source pre-reading. `max` is selective only after unresolved xhigh analytical contradiction; missing author facts do not justify max.
14. Run-local compatibility fixes must be lossless, auditable and must not edit installed Skill/package files. Preserve first failures and retry evidence.
15. Exact accepted synthesis path/hash must be the report input. Independent reviewer is fresh; reviewer rejection/issues remain visible. Publication must be byte-identical to the reviewed/validated draft.
16. Historical and failed runs remain untouched. Runner state is never manually edited.
17. Preparatory files do not count as completed workflow work. Runner acceptance is authoritative.

## Topic 01 Round 2 scope after gap review

### R2-A — Incomplete and incremental email reconstruction

Research only literature that materially informs one or more of:

- missing/unavailable parents and partial exports;
- parent/ancestry reconstruction from incomplete history;
- multiple parents / multiple supported reply targets;
- late arrival and out-of-order reconciliation;
- correction/retraction of previously inferred relations;
- modern or LLM-assisted methods when they solve one of the above.

### R2-B — Robust quotation-to-source-span alignment

Research only literature that materially informs one or more of:

- edited/partial quotations;
- markerless quotations;
- inline/interleaved replies;
- HTML/table/nested quotation structure;
- approximate matching of quote occurrence to exact source span;
- quote provenance, ambiguity and alternative source mappings.

### Explicitly not Round 2 academic targets

- A3 historical threading baseline as a standalone goal;
- A4 EACL zoning article as a standalone goal;
- A6 generic transfer protocols/supplements/metric papers;
- semantic partial-answer/agreement scope (Topic 04);
- cross-thread concrete work-matter identity (Topic 03);
- general calibration/selective-prediction methodology (Topic 10);
- Raspberry Pi performance.

## Paper admission gate

A new paper enters the Round 2 corpus only if at least one answer is YES:

1. Does it provide direct email evidence for incomplete/incremental reconstruction?
2. Does it provide direct email evidence for robust quote-occurrence -> source-span alignment?
3. Does it provide a genuinely new transfer mechanism needed for either capability and absent from Round 1?
4. Is it a high-value primary source explicitly identified by Round 1 whose full text can change interpretation of A1/A2/A7?

Papers that merely repeat generic threading, conversation clustering, ordinary zoning, summarization or chat disentanglement are excluded.
