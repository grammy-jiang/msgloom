# Independent execution and deliverable review

**Verdict: Topic 01 research is incomplete. The blocked outcome is supported by the saved evidence.**

The supervising assistant reviewed the work of the separate `research_execution` native agent on 2026-09-14. This review checks execution, provenance, gates, scope, and deliverable completeness. It is not the pipeline's `review-synthesis` verdict. That task was never reached, and no synthesis exists to review.

## Evidence checked

The review independently read the installed Skill, manifest, schemas, runner, and relevant installed CLI code. It checked the generated and amended query plans, both search commands and their full error logs, the plan-verification output, workflow state, local configuration notes, and the ancillary documents. It also compared all 19 preserved `docs/` and `notes/` files against the supervising assistant's hash snapshot.

Key artifacts:

- [Workflow state](../workflow_state.json) and [run status](../RUN_STATUS.md).
- [Original query plan](../runs/101cf2285113/plan/query_plan.generated.json) and [amended query plan](../runs/101cf2285113/plan/query_plan.json).
- [Plan verification output](../execution/logs/verify-plan-01.stdout.log).
- [First search error log](../execution/logs/search-01.stderr.log) and [second search error log](../execution/logs/search-02.stderr.log).
- [First nonempty check](../execution/checks/search-01.json) and [second nonempty check](../execution/checks/search-02.json).
- [Initial independent checkpoint](checkpoint-01.json) and [final independent artifact audit](final-artifact-audit.json).

## Confirmed results

| Item | Independent assessment |
| --- | --- |
| Run identity | One run: `101cf2285113`, deep profile. Round 1 started; zero rounds completed. |
| Runner use | The installed runner initiated and delegated the requested stages. Recorded CLI calls followed those delegations. |
| Plan adjustment | The CLI omitted the installed schema's required `topic` field. The original artifact was preserved. Adding the exact topic and refining queries was documented. An independent Draft 7 check passed for the amended artifact. |
| Accepted tasks | `resume-check`, `plan`, and `verify-plan`. The actual plan verifier returned six passing checks and exit code 0. |
| Search | Both stage invocations exited 0 but saved zero-byte candidate files. This fails the manifest's `non_empty` requirement. Search was never accepted. |
| Corpus and reading | Zero academic candidates, screened papers, shortlisted papers, downloaded PDFs, converted full texts, full texts read, abstracts read, and paper analyses. |
| Delegation | One separate native orchestration worker performed execution. Zero pipeline paper-role workers or synthesis reviewers were reached. |
| Later gates | Screening, analysis, synthesis review, report validation, completion, and gap classification remain pending. No reviewer verdict was overridden or manufactured. |
| Supplemental material | Five official engineering sources were consulted. Twenty synthetic cases were proposed. Neither set is an academic corpus or an executed benchmark. |
| Deliverables | The Chinese summary and reading-list status disclose the failure. The academic report and academic prioritized reading list remain unavailable. |
| Scope | The checked design/context files remained unchanged. No application code was produced. No mailbox data, deployment, service restart, commit, push, or Topic 02–10 run appears in the recorded execution. |

The native worker inherited this session's model and settings. The launch record identifies `gpt-6-astra`, reasoning effort `max`, and the user's stated runtime flags. No additional Codex CLI worker was launched for this execution. No API LLM was enabled.

## Why stopping is justified

The initial search and the manifest's one retry acquired no usable academic records. arXiv and Semantic Scholar returned rate-limit errors. arXiv also timed out. Scholar lacked its optional dependency. DBLP responses failed JSON parsing. OpenAlex received invalid date filters. HuggingFace's limited daily feed contained no matching candidates.

This is a source-access and installed-integration failure. It is **not** evidence that relevant literature does not exist. It is **not** a completed gap-closure round, a saturation result, or the four-round stopping cap. A focused gap search becomes useful once a scholarly source can return valid records. Starting another nominal round now would not cure the observed access or date-format problems.

The runner's delegated-artifact check only tests existence. The execution agent's explicit nonempty checks prevented an empty file from being accepted. This additional evidence check was necessary to enforce the manifest. It did not bypass a failed gate.

## Remaining research questions

Each question remains open as an academic question. The next steps below are research priorities, not completed findings or authorization to change msgloom.

| RQ | Available context and unresolved evidence | Smallest useful next step after source recovery |
| --- | --- | --- |
| RQ1 | RFC metadata semantics are available. No paper establishes reconstruction quality under absent or conflicting headers. | Find and read direct-email thread-reassembly studies; extract the missing-header and collision assumptions. |
| RQ2 | Flowed plain-text rules are available. HTML, disclaimers, interleaved replies, and loss of unique content lack paper evidence. | Find quotation/signature segmentation studies and inspect full-text boundary definitions and error cases. |
| RQ3 | Multiple-parent metadata is permitted. Span-level response alignment and semantic multi-parent methods remain unstudied in this run. | Find methods and annotations that preserve multiple response targets; identify any forced-tree assumptions. |
| RQ4 | Standards and proposed fixtures describe some forks and missing ancestors. Incremental correction accuracy and cost remain unmeasured. | Read methods covering partial histories and late arrivals; determine what temporal evidence each method actually uses. |
| RQ5 | No method comparison is supported by a read paper. | Compare a small relevant set of deterministic, statistical, neural, and LLM-assisted methods with explicit domain and compute assumptions. |
| RQ6 | No dataset, split, annotation, or license has been verified through the pipeline. | Verify primary dataset documentation and paper annotations, including quoted near-duplicate leakage and business-email coverage. |
| RQ7 | Proposed fixture checks exist. No published metrics or executed results have been compared. | Extract exact task, metric, split, and missing-parent definitions before comparing reported numbers. |
| RQ8 | Existing design constraints and synthetic proposals remain available. No evidence-grounded representation recommendation is ready. | Complete the literature checks, then select small experiments with explicit preservation and abstention rejection criteria. |

Missing real-email validation is an engineering-validation gap. Additional papers cannot establish production accuracy for msgloom. Real mailbox access remains outside this task. The saved synthetic catalogue can support later authorized experiments, but it cannot replace representative data or prove zero information loss.

## Smallest corrections before resuming

1. Restore at least one usable configured academic source. The concrete OpenAlex code defect is that the caller supplies compact arXiv dates and the connector slices them as if they were ISO dates. Convert dates at the OpenAlex boundary to `YYYY-MM-DD`; retain compact dates for arXiv. This correction alone does not prove that authentication or service access will work. No installed code was changed in this task.
2. Preserve the failed attempt and resume through the installed runner only after the source issue is resolved. A retry requires an explicit task-state reset because the current `search` status is terminal `failed`. Retain the failure evidence before any reset.
3. Resolve the report handoff before that stage is reached. Static inspection shows that the manifest expects the final topic-path report, while the renderer defaults to `summarize/report_structured_synthesis.md` and reads `summarize/synthesis_report.json`, not the worker's `analysis/synthesis.json`. The Skill also prohibits writing the final path before validation, while the manifest requires that path before the validation task. These are inspected integration inconsistencies, not runtime failures observed at the report stage. The corrected workflow must validate the reviewed candidate and publish the final path afterward.

The execution agent's [blocker record](../BLOCKERS.md) contains the exact failed command and proposed correction boundaries. The initial supervisory RUN_PROMPT.md scoped this execution to research artifacts and excluded shared infrastructure edits; that boundary should not be attributed to a separate prohibition from the original user. `EVALUATION.md` was not created.
