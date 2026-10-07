# Topic 01 continuation: complete

## Terminal update — 2026-09-14

This update supersedes the historical checkpoints below. Do not restart their completed tasks.

- The existing run `20260914T084949Z`, profile `deep`, reached runner status `complete` at `2026-09-14T12:46:12.997730+00:00`. All 21 executed tasks are accepted; expand, enrich and convert-fine are skipped_by_policy. No new round started.
- Verified counts: 27 screened, 24 selected, 24 full-text analyses and genuine worker results, three deprioritized. The selected set contains 18 DIRECT_EMAIL and six TRANSFER papers. Independent checks found 167 located findings and 181 source-matched raw claims.
- Fresh, separate synthesizer, reviewer and gap-classifier workers completed their contracts. The exact synthesis covers all 24 papers and RQ1–RQ8. Review is `accepted_with_issues`, with two nonblocking issues and no required fixes or unsupported claims. Strict validation is `PASS`.
- Published report: [email-conversation-structure-branching-and-inline-replies-research-report.md](email-conversation-structure-branching-and-inline-replies-research-report.md). It is byte-identical to the reviewed/validated draft; SHA-256 `00b37a667db289f7d0dbf5e8610e1f7ac728720bdd473196e43dc1ff3c7a92cc`.
- [gaps.json](gaps.json) records seven ACADEMIC follow-up acquisition groups and six ENGINEERING groups. All remain open. The terminal stop reflects the current ban on further acquisition, not empirical convergence or literature exhaustion. Readiness remains `HAS_GAPS`.
- [audit/final-local-audit.json](audit/final-local-audit.json) passes all 26 checks. The old blocked run `101cf2285113` and root workflow state match the original baseline. Two historical launcher logs had already differed at the first continuation audit; all 125 protected files stayed unchanged during this continuation. No historical file was restored or modified.
- See [RUN_NOTE.md](RUN_NOTE.md) for receipts, exact confidence grades and limits, and [SUMMARY.local-corpus.zh-CN.md](SUMMARY.local-corpus.zh-CN.md) for the Chinese handoff. The historical root summary is unchanged.
- No new provider search or paper download, real mailbox access, application/design edit, shared Skill/package modification, commit/push/deploy, service restart, or Topics 02–10 work was performed in this continuation. Follow-up proposals are not authorization to execute them.

## Historical checkpoints retained for provenance

- Namespace cwd: /home/grammy-jiang/Projects/msgloom/research/01-email-conversation-structure/local-corpus-20260914
- New runner state: workflow_state.json; run ID: 20260914T084949Z; profile: deep.
- Original blocked 101cf2285113 and all root artifacts untouched. audit/historical-artifact-hashes.json baseline.
- Read actual installed Skill/manifest/config/references/contracts; installed and bundled skill match. See audit/runtime-provenance.json and reconciliation-review.md.
- 27 PDF hash/size/signature/pdfinfo/pdftotext validations passed. 325 PDF pages; E14 is 89-page dissertation, not EACL paper. Intake corrected E09/E13 authors and E20 surname discrepancy. Source manifest unchanged.
- Plan actual MCP receipt saved, edits based on RQ1-RQ8 before runner acceptance; verify-plan actual CLI accepted.
- Candidates staged via scripts/stage_local_candidates.py; all27 canonical E01-E20/T01-T07, local version v1. candidates schema forces year-only timestamps; sentinels documented. No arXiv IDs invented.
- Genuine tool_search(resume=True) returned 27 candidates status partial; actual ToolResult submitted to runner. No provider requests. Coverage attempts[].
- Actual BM25 screen accepted. Runner currently delegated paper-screener to agent corpus_intake. Worker plans24 selected (18email,6transfer), E19/E20/T02 deprioritized. Await its final result, then submit via runner. No tasks statuses may be edited manually.
- Run each subsequent CLI stage through `research-pipeline-workflow --state workflow_state.json --execute-task ID` from namespace cwd. It advances/delegates next automatically.
- Before actual download CLI, execute scripts/stage_selected_pdfs.py. This copies selected original PDFs and rechecks hashes. Actual download CLI must yield downloaded0, skipped_exists24 (or actual selected count). Skip-existing returns before any provider request.
- Expansion automatically skipped because prior IDs empty. Quality CLI inspected: local scores only, no network. Enrich must NOT execute; submit truthful success:false policy result through --complete-task enrich; runner's optional failure policy makes skipped_by_policy.
- Rough converter missing from shared env: installed topic-local python-deps with pymupdf4llm0.0.27 and aarch64 PyMuPDF1.28.2. For conversion command use PYTHONPATH=/absolute/namespace/python-deps scoped to runner process. No shared code changed. Convert-fine optional auto skip if IDs empty. Source page text already in screening-text.
- Execute convert-rough, extract, summarize through runner. CLI LLM disabled -> summaries/claim scores are deterministic fallback artifacts, not semantic evidence. Required full-text Codex paper-analyzer workers supply deep evidence. Keep actual runtime inherited (never model/reasoning overrides). One fresh agent per selected paper, up to3 concurrently; root can do useful independent review. ANALYZER_INSTRUCTIONS.md has common detailed contract; paper_id base E01, output stem E01v1.analysis.json and .md. Workers write only analysis/. User requires no network.
- After all analyses, scripts/check_worker_artifacts.py preflight, then actual result submission paper-analyzer. Delegate synthesis to fresh worker using installed contract + REPORT_RENDER_CONTRACT.md. Report custom template templates/topic01.md.j2 uses schema-compatible extra string fields in corpus, RQ answers in evidence_strength_map.
- Actual report can use supported MCP tool_report(custom_template=absolute template, template=structured_synthesis, synthesis_path=exact analysis/synthesis.json, output=exact run/report/draft.md, run_id, workspace=namespace/runs). Save real ToolResult and submit through runner; no package/skill edit or post-acceptance draft edit needed. This custom renderer gives all required report sections and real Topic01 RQ/engineering/evaluation details.
- Required next gates: analyze-claims, score-claims (actual CLI through runner), report, independent review-synthesis exact hash, strict validate-report, publish-report and completion scripts (runner automatically), classify-gaps worker. Preserve failed verdicts and use retry flow only if necessary. No fake success, no accepted-status edits.
- Gap closure: local only; no new discovery/download. Precise reference leads/queries saved, no new round for forbidden acquisition. Engineering experiments proposals only. No architecture approval, application code, mailbox, commits/push/deploy/services or Topics02-10.
- Final audits: original hashes unchanged, all staged and converted manifests/counts, schema/locators/worker receipts, independent reviewer receipt, report validation hashes and publication equal, workflow complete, classified gaps. Update RUN_NOTE.md and final summary. Add concise Chinese executive summary in namespace; keep original root SUMMARY.zh-CN.md historical.

## Update after conversion

- Screener accepted:24selected E01–E18,T01,T03–T07; E19/E20/T02deprioritized. Legacy screen verifier defect fixed with lossless shortlist.jsonl mirror, actual third verify passed; two failures preserved.
- Quality accepted (local metadata proxies); expand/enrich skipped by policy. Download accepted:0downloaded24skipped_exists. Convert rough accepted:24converted,24PDFhashchecks. Convertfine skippednoIDs. Extract accepted24files; summarize accepted24summaries/extractions(templatefallback).
- paper-analyzer is currently delegated. First workers analyze_e14,analyze_e02,analyze_e07 running, fork none but no model/runtime overrides. Need21more fresh perpaperworkers as slotsfree.
- Parent built scripts/prepare_verified_claim_inputs.py: after all24analyses, create new supported summarize/paper_summaries.jsonl from real worker findings and canonical convert/markdown symlinks to same roughbytes so installed claimreader sees fulltext. Original fallbacks remain untouched. Writes schema-valid analysis/verified_extractions and auditlineage. Document as projection,not independent LLM evidence. Run only when all24done.
- E14 worker found annotation all linesafterquote=quote (PDF49–50), untested inlinepreservation; verified source table/prose discrepancies using parentrenderedpages52,71,73,75.
- E02worker verified Table3 originalrecall.5976/MPT.7184 vs filteredT+S.8739/.8949(not same testset); parent independently viewedPDF5. Source arithmetic issues noted byworker.
- E07worker found task perlinezoning, explicitlynotthreadreconstruction; inlinequotes+newresponses samebody; domainmetrics needtaskcontext.
