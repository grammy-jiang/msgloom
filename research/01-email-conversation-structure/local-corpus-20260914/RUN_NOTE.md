# Topic 01 local-corpus continuation

Run **20260914T084949Z** uses the installed research-pipeline **deep** profile. Its state is [workflow_state.json](workflow_state.json). All outputs remain under Topic 01.

The 27 academic PDFs were acquired outside this pipeline run. The source corpus and its MANIFEST.json remain unchanged. Validation found 20 direct-email PDFs, 7 transfer PDFs, 27 distinct SHA-256 values, and 325 PDF pages. Every PDF matched its recorded hash and byte count. PDF parsing and text extraction returned exit code zero for every file. Bibliographic validation separately checks whether each PDF matches the manifest identity.

The installed version has no formal corpus-import command. This continuation uses the smallest supported reconciliation path:

1. Normalize real local metadata and PDF abstract text to CandidateRecord entries. Keep stable local IDs in the schema's legacy `arxiv_id` field. Record the source path, SHA-256, provenance, identity corrections, and date precision in audit/paper-id-map.json. `v1` denotes this local artifact version. January 1 timestamps are required-schema sentinels for year-only bibliography; they are not verified publication dates.
2. Stage search/candidates.jsonl and source_coverage.json. Coverage is `partial`, with an empty attempts list and explicit local acquisition scope. This does not claim a provider searched successfully.
3. Call the installed MCP `tool_search` with `resume=true`, the exact run ID, and the exact workspace. The audited implementation reads saved candidates and coverage and returns before resolving or querying providers. Submit the genuine saved ToolResult through the runner's `--complete-task search` interface.
4. Copy selected local PDFs into download/pdf using the local paper IDs. Recheck hashes. The runner's actual download CLI uses its `skipped_exists` path. It issues no PDF requests. The resulting download manifest must record zero downloaded files.
5. Execute downstream CLI stages through `--execute-task`. Submit actual worker results through `--complete-task`. The runner remains the only authority for task acceptance.

Expansion is skipped by the runner when no prior IDs are selected. Network metadata enrichment is outside this run's scope and is recorded through the optional task's skip policy. Local quality scoring may run; missing citation/h-index metadata and venue proxies do not establish academic quality or peer-review status. Full-text workers assess evidence quality separately.

The package lacked its rough converter dependency. PyMuPDF4LLM 0.0.27 and PyMuPDF 1.28.2 were installed only into this directory's python-deps, with a local package cache. The PyMuPDF wheel is aarch64. These package downloads are separate from paper acquisition. No shared skill or pipeline source was edited. CLI stages use this local dependency path. No external LLM API is configured; semantic workers and reviewers inherit the active Codex session runtime without model overrides.

The nested workflow working directory prevents the runner from overwriting the earlier run's root state, resume context, round state, logs, snapshots, or evaluation. The original blocked run **101cf2285113** is historical evidence and contributes no successful search receipt. audit/historical-artifact-hashes.json records the pre-run baseline.

Status: **complete**, as recorded by the manifest-governed runner at **2026-09-14T12:46:12.997730+00:00**. All 21 required/executed tasks are accepted. The three optional tasks expand, enrich and convert-fine are skipped_by_policy. The runner accepted classify-gaps and ended round 1 without starting another round. No task status was edited manually. No new paper search or redownload was performed. No application implementation, mailbox access, design approval, commit, push, deployment, service restart, or work on Topics 02–10 was performed.

The continuation verified 24 genuine worker analyses (18 DIRECT_EMAIL, 6 TRANSFER), 167 findings with locators and 181 normalized source-matched raw claims. The accepted synthesis answers RQ1–RQ8 and contains 319 traceability entries. Actual claim stages processed 811 heuristic claims after a supported projection of the genuine analyses. All 81 original deterministic summarize artifacts remain byte-identical. The report was rendered by the actual MCP report tool using the supported custom template and explicit accepted synthesis path. Receipts are under execution/.

The old blocked run and root workflow state match the historical baseline. Two earlier corpus-analysis launcher logs already differed from the early baseline at the first continuation audit. Their observed hashes were recorded; neither file was restored or modified. See audit/continuation-historical-observed-hashes.json.

## Terminal results

| Verified round | Screened | Selected | Full-text analyzed | Deprioritized | Runner status |
| --- | ---: | ---: | ---: | ---: | --- |
| 1: existing local corpus | 27 | 24 | 24 | 3 | complete |

The selected papers are E01–E18, T01 and T03–T07. E19, E20 and T02 are already acquired but deprioritized. The 24-paper evidence base contains 18 DIRECT_EMAIL papers and six TRANSFER papers. Five saved RFC/Microsoft Graph sources remain ENGINEERING documentation outside the academic counts. No chat/forum score is claimed as business-email accuracy. Source coverage remains partial. The selected artifacts have nominal publication years 2003–2023.

The [published report](email-conversation-structure-branching-and-inline-replies-research-report.md) is byte-identical to the exact reviewed and validated draft. Its SHA-256 is `00b37a667db289f7d0dbf5e8610e1f7ac728720bdd473196e43dc1ff3c7a92cc` (247181 bytes). The accepted [synthesis](runs/20260914T084949Z/analysis/synthesis.json) is schema-valid and has SHA-256 `98034e544b00e1fcac071569c2f5961f54381dfc8aeb0dc339adeed868f563be`. The actual supported MCP report receipt and render arguments are in execution/report-tool-result.json and execution/report-call-arguments.json. The accepted draft was not edited after rendering.

The fresh independent [reviewer](runs/20260914T084949Z/review/synthesis_review.json) returned **accepted_with_issues**. It found no unsupported claims and required no fixes. Faithfulness was 0.97, coherence 0.95 and gap completeness 0.96; citation integrity passed. Two nonblocking issues remain in the accepted bytes: RQ7 calls E04 boundary precision/recall “boundary accuracy,” while the evidence matrix gives the actual precision/recall; 18 contradiction-resolution paragraphs contain duplicate periods. The genuine worker receipt is runs/20260914T084949Z/review/synthesis-review.worker-result.json.

Actual runner validate-report, publish-report and check-completion tasks all passed. [Strict validation](runs/20260914T084949Z/validate/validation_result.json) returned **PASS**, no issues, with Contents, Round History, Mermaid and LaTeX requirements satisfied. Its 1.0 score is a structural report score, not a scientific accuracy estimate.

RQ1–RQ8 are explicitly answered. Confidence is MEDIUM for RQ1, RQ2, RQ3, RQ5, RQ6 and RQ8; LOW for RQ4; HIGH for RQ7's need to separate evaluation targets. Readiness remains **HAS_GAPS**. These confidence grades do not measure a deployed system's correctness. The synthesis distinguishes Group from Topic and separates reply edges, conversation membership, quotation-source matches and semantic response scope. It does not equate quoted-fragment recovery with complete-message recovery or claim unmeasured preservation of unique or decision-bearing text.

The fresh [gap classifier](gaps.json) retained seven ACADEMIC acquisition groups and six ENGINEERING groups. All 13 remain open and deferred. `should_continue=false` with reason `user_marked_out_of_scope` records the current acquisition boundary; it does not claim literature exhaustion or empirical convergence. Recommended acquisition order is A1 hidden-email primary studies, A2 quotation/deliberation studies, A5 multi-sentence helpdesk responses, A7 current email/LLM/incremental evaluations, then A3 the Lewis–Knowles baseline, A4 the distinct EACL multilingual-zoning article, and A6 transfer protocols/supplements/metric sources. Exact leads and unexecuted queries are in gaps.json. E19/E20/T02 are not missing acquisitions.

The six engineering needs are representative authorized mailbox labels; measured unique/decision-bearing text preservation; incremental late-parent and correction replay; confidence calibration and abstention; exact artifacts/releases/access/licenses; and Raspberry Pi 5 arm64 latency, peak memory and per-arrival cost. These remain proposed checks and experiments, not claims that literature does not exist. No experiment or implementation was performed.

The [final audit](audit/final-local-audit.json) passed all **26 checks**. All 125 protected historical files match their first observed continuation hashes. The old blocked run 101cf2285113 and root workflow state also match the earlier baseline. The two preexisting launcher-log differences remain documented. All 81 original deterministic fallback artifacts and all accepted artifact fingerprints are unchanged. Installed Skill/contract hashes match their recorded baseline. Worker receipts record inherited Codex settings; they do not independently attest an exact historical model ID.

The concise Chinese handoff is [SUMMARY.local-corpus.zh-CN.md](SUMMARY.local-corpus.zh-CN.md). The historical root summary remains untouched.
