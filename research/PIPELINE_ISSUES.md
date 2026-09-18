# Research Pipeline issue register

This register records observed problems during msgloom Topic 01, for a later improvement of the Research Pipeline Skill/MCP/CLI. It is an engineering record, not a literature review or an approved change plan.

- Environment: Raspberry Pi, Codex CLI 0.154.0, research-pipeline 0.32.0, installed manifest 2.0.0.
- Topic run: `101cf2285113`; Codex thread: `01a09d3a-7eca-7173-94b6-f1797ade7843`.
- All listed issues remain open unless a row explicitly describes a run-local workaround. Shared Skill/package files were not changed for this register.
- Runtime observations, source-code findings, configuration choices and external failures are labeled separately. A failed provider search is not evidence of an academic gap.
- Static report-stage findings have not been exercised by this run and must not be described as observed end-to-end failures.
- Severity describes impact on this research workflow. Source snapshots and current implementation may differ; any future patch must recheck the actually installed version.
- The Codex process has finished. The final outcome and conditional rerun decision are recorded in Topic 01's EVALUATION.md.

## Common reproduction context

Working directory:

`/home/grammy-jiang/Projects/msgloom/research/01-email-conversation-structure`

The observed delegated search command was:

```bash
research-pipeline search --run-id 101cf2285113 --source all --config /home/grammy-jiang/Projects/msgloom/research/01-email-conversation-structure/config.run.toml
```

This is the historical reproduction command. Future production research should resume through the Skill's manifest-governed runner; do not bypass it or repeat rate-limited calls simply to reproduce these logs.

The exact Codex alias expansion and process arguments are in [launch metadata](01-email-conversation-structure/execution/launch.json). Attempt timestamps, environment override names and exit codes are in the command JSON files. Secret values must never be added to this register.

## Index

| ID | Issue | Classification | Severity |
| --- | --- | --- | --- |
| RP-001 | [OpenAlex receives malformed publication dates](#rp-001) | Confirmed integration defect | P1 — blocks this source |
| RP-002 | [Runner artifact checks do not enforce the manifest's semantic validation](#rp-002) | Confirmed static defect with runtime exposure; false acceptance was prevented | P1 — can permit unsupported completion |
| RP-003 | [All-source failure still returns CLI exit code zero](#rp-003) | Confirmed CLI/runner contract weakness | P1 — misleading success signal |
| RP-004 | [Generated query plan does not satisfy the installed Skill schema](#rp-004) | Confirmed schema integration defect | P1 — blocks the plan gate without manual correction |
| RP-005 | [Manifest --source all overrides the configured source selection](#rp-005) | Confirmed configuration/manifest integration issue | P2 — unnecessary failures and surprising execution |
| RP-006 | [Planned query and date coverage differs from actual connector coverage](#rp-006) | Confirmed coverage/observability limitation | P2 — can overstate search breadth |
| RP-007 | [Manifest and renderer disagree about the final report path](#rp-007) | Static latent integration defect — report stage not reached | P1 for future end-to-end completion; not the current search blocker |
| RP-008 | [Final arXiv failure sleeps despite no attempt remaining](#rp-008) | Confirmed runtime efficiency issue | P2 — unnecessary delay per failed search |
| ENV-001 | [arXiv and Semantic Scholar rate limits / arXiv timeout](#env-001) | Observed external-service/access failures; underlying cause not established | P1 — source acquisition blocked |
| ENV-002 | [DBLP response could not be decoded as JSON](#env-002) | Observed source integration/response failure — cause unconfirmed | P1 for this source |
| CFG-001 | [Default research configuration is a poor fit for foundational email research](#cfg-001) | Configuration fit / Skill guidance improvement | P2 |
| RP-009 | [Final-report creation order conflicts with validation dependencies](#rp-009) | Static Skill/manifest contract inconsistency | P1 for end-to-end completion |
| RP-010 | [Reviewed synthesis is not the renderer's default input](#rp-010) | Static artifact-handoff inconsistency | P1 for evidence-grounded reporting |
| RP-011 | [Delegated output misattributed a supervisory scope boundary](#rp-011) | Reporting/provenance wording issue | P2 |

| RP-012 | [Retry-After can be shortened or ignored](#rp-012) | Installed-code defect; offline reproduction | P1 |
| RP-013 | [Nontransient bad requests are retried](#rp-013) | Runtime/offline retry-policy defect | P2 |
| RP-014 | [Throttle/cooldown is not shared across processes](#rp-014) | Static coordination limitation | P2 |
| RP-015 | [HTTP diagnostics cannot determine restriction scope](#rp-015) | Observed telemetry gap | P2 |


## RP-001

**OpenAlex receives malformed publication dates**

- **Status:** Open; Confirmed integration defect.
- **Severity:** P1 — blocks this source.
- **Expected:** Convert a shared date range to each provider's accepted format before dispatch. OpenAlex publication-date filters should receive ISO dates.
- **Observed:** The CLI passes compact arXiv-style timestamps into OpenAlexSource.search; that source slices the first ten characters and sends values such as 1987041200 and 2026091400. The live API returned HTTP 400.
- **Affected component:** `research_pipeline/cli/cmd_search.py::_search_openalex and research_pipeline/sources/openalex_source.py::OpenAlexSource.search`.
- **Run-local handling:** None applied. Increasing backoff does not correct a malformed date.
- **Improvement proposal:** Add a typed provider-neutral date range and provider-specific serialization, or minimally normalize dates at the OpenAlex boundary.
- **Verification criterion:** Assert the exact outgoing date filters for compact timestamps and ISO input, including month/day boundaries; add a small live provider smoke check separately from deterministic tests.
- **Evidence:** [search-01.stderr.log](01-email-conversation-structure/execution/logs/search-01.stderr.log), [search-02.stderr.log](01-email-conversation-structure/execution/logs/search-02.stderr.log).

## RP-002

**Runner artifact checks do not enforce the manifest's semantic validation**

- **Status:** Open; Confirmed static defect with runtime exposure; false acceptance was prevented.
- **Severity:** P1 — can permit unsupported completion.
- **Expected:** The runner itself should execute every declared validation and retain its result before accepting a task.
- **Observed:** The inspected validate_artifact implementation returns path.exists(). The manifest declares non_empty for search and schema_valid for plan. The first candidate file existed but was zero bytes. The supervising Codex added independent checks and refused to accept search.
- **Affected component:** `skill_data/research-pipeline/runners/runner.py::validate_artifact and manifest.json task validations`.
- **Run-local handling:** The researcher checked CLI exit codes, candidate non-emptiness and JSON schema validity separately before resume.
- **Improvement proposal:** Implement declarative validation dispatch for non_empty, schema_valid, evidence_present and exit_code_zero; fail closed for unknown validators. Keep reviewer verdicts distinct from artifact presence.
- **Verification criterion:** An existing empty candidate file, schema-invalid JSON and a rejected review must each remain unaccepted. A correct nonempty, schema-valid artifact should advance only its relevant task.
- **Evidence:** [search-01.json](01-email-conversation-structure/execution/checks/search-01.json), [plan.json](01-email-conversation-structure/execution/checks/plan.json), [CONFIG_NOTES.md](01-email-conversation-structure/CONFIG_NOTES.md).

## RP-003

**All-source failure still returns CLI exit code zero**

- **Status:** Open; Confirmed CLI/runner contract weakness.
- **Severity:** P1 — misleading success signal.
- **Expected:** Distinguish successful empty search, partial coverage, unavailable sources and total acquisition failure in structured status. The governed workflow must not accept a zero-corpus run.
- **Observed:** Attempt 1 logged that 6/6 sources contributed nothing, wrote a zero-byte candidates.jsonl and exited 0. The CLI offers --strict-sources, but the manifest does not request it. A warning is present, so this was not silent at the log level.
- **Affected component:** `research_pipeline/cli/app.py::search, cli/cmd_search.py and manifest search command`.
- **Run-local handling:** Empty search was rejected independently despite exit code 0.
- **Improvement proposal:** Define an explicit all-sources-failed outcome and align CLI exit/status semantics with runner gates. Preserve a configurable partial-source policy rather than rejecting every partial success.
- **Verification criterion:** Test all-failed, mixed failed/successful, valid zero-result and nonempty-result cases independently.
- **Evidence:** [search-01.command.json](01-email-conversation-structure/execution/logs/search-01.command.json), [search-01.stderr.log](01-email-conversation-structure/execution/logs/search-01.stderr.log), [search-01.json](01-email-conversation-structure/execution/checks/search-01.json).

## RP-004

**Generated query plan does not satisfy the installed Skill schema**

- **Status:** Open; Confirmed schema integration defect.
- **Severity:** P1 — blocks the plan gate without manual correction.
- **Expected:** The CLI's generated artifact and the packaged Skill schema must agree without hand amendment.
- **Observed:** The generated plan omitted the schema-required topic property. The researcher preserved the original, added the exact topic and validated the amended plan.
- **Affected component:** `CLI plan output and skill_data/research-pipeline/schemas/query_plan.schema.json`.
- **Run-local handling:** A documented run-local field amendment; original output retained.
- **Improvement proposal:** Define one canonical plan contract and validate CLI output against the installed schema in release checks.
- **Verification criterion:** Generate an ordinary plan through the packaged CLI and validate the resulting file against the bundled Skill schema.
- **Evidence:** [plan.json](01-email-conversation-structure/execution/checks/plan.json), [query_plan.generated.json](01-email-conversation-structure/runs/101cf2285113/plan/query_plan.generated.json), [query_plan.json](01-email-conversation-structure/runs/101cf2285113/plan/query_plan.json).

## RP-005

**Manifest --source all overrides the configured source selection**

- **Status:** Open; Confirmed configuration/manifest integration issue.
- **Severity:** P2 — unnecessary failures and surprising execution.
- **Expected:** The manifest should honor configured sources or explicitly validate dependencies and explain the override before executing all providers.
- **Observed:** The manifest command requests --source all. This invokes Scholar even though the local sources.enabled list excludes it; scholarly is not installed. The CLI's explicit all semantics are understandable, but they do not match a task labeled search all configured sources.
- **Affected component:** `manifest.json search.executor.cli and CLI source selection`.
- **Run-local handling:** Failure recorded; no shared dependency installation or global configuration change.
- **Improvement proposal:** Use configured sources by default and add provider dependency/credential checks to preflight; make an all-provider override explicit.
- **Verification criterion:** A disabled provider must not be invoked in configured-source mode. Explicit all-provider mode must report missing optional dependencies before a long search.
- **Evidence:** [RUN_STATUS.md](01-email-conversation-structure/RUN_STATUS.md), [CONFIG_NOTES.md](01-email-conversation-structure/CONFIG_NOTES.md), [search-01.stderr.log](01-email-conversation-structure/execution/logs/search-01.stderr.log).

## RP-006

**Planned query and date coverage differs from actual connector coverage**

- **Status:** Open; Confirmed coverage/observability limitation.
- **Severity:** P2 — can overstate search breadth.
- **Expected:** Report actual provider-specific queries, time filters, attempted variants and fallback execution, separately from intended coverage.
- **Observed:** Twelve arXiv query variants were planned, but only the first was attempted before failure. Other connectors used email thread rather than all variants. The configured fallback_months value is not applied by this search command. HuggingFace searched a daily-paper list, not a decades-long archive.
- **Affected component:** `research_pipeline/cli/cmd_search.py, source adapters and query plan/config`.
- **Run-local handling:** The researcher recorded planned versus attempted coverage explicitly.
- **Improvement proposal:** Make provider query translation and fallback policy explicit. Save a request/coverage ledger; label daily feeds as supplemental sources.
- **Verification criterion:** For a plan with several variants and a fallback window, assert which requests each provider makes and that the report reflects the actual attempted/successful set.
- **Evidence:** [RUN_STATUS.md](01-email-conversation-structure/RUN_STATUS.md), [query_plan.json](01-email-conversation-structure/runs/101cf2285113/plan/query_plan.json), [search-01.stderr.log](01-email-conversation-structure/execution/logs/search-01.stderr.log).

## RP-007

**Manifest and renderer disagree about the final report path**

- **Status:** Open; Static latent integration defect — report stage not reached.
- **Severity:** P1 for future end-to-end completion; not the current search blocker.
- **Expected:** The renderer output location must match the artifact the runner and validator expect.
- **Observed:** The manifest expects {cwd}/{topic_slug}-research-report.md, but its report command does not pass --output. cmd_report.py defaults to the summarize stage directory, report_{template}.md.
- **Affected component:** `manifest.json report.executor.cli/output.path and research_pipeline/cli/cmd_report.py::out_path`.
- **Run-local handling:** None needed yet; the report stage has not run.
- **Improvement proposal:** Pass an explicit output path from the manifest and validate the same path. Preserve the distinction between an unaccepted draft and a validated report.
- **Verification criterion:** Use a small valid synthesis fixture to run the declared renderer command and assert the manifest's exact expected output and validator input.
- **Evidence:** [CONFIG_NOTES.md](01-email-conversation-structure/CONFIG_NOTES.md).

## RP-008

**Final arXiv failure sleeps despite no attempt remaining**

- **Status:** Open; Confirmed runtime efficiency issue.
- **Severity:** P2 — unnecessary delay per failed search.
- **Expected:** Respect retry policies and service limits, but return the terminal error once no retry remains.
- **Observed:** Attempt 1 logged arXiv attempt 5/5 at 10:13:15 local time, slept 80 seconds, then raised at 10:14:35 without another request. The second search also reached a final backoff.
- **Affected component:** `research_pipeline/arxiv/client.py retry loop`.
- **Run-local handling:** Allowed the running command to finish and preserved its real terminal result.
- **Improvement proposal:** Avoid a post-final-attempt sleep; continue honoring Retry-After for actual permitted future attempts. Do not increase retries or evade service controls.
- **Verification criterion:** With a fake clock and repeated 429 responses, assert the number of requests and sleeps and ensure no sleep occurs after the final allowed attempt.
- **Evidence:** [search-01.stderr.log](01-email-conversation-structure/execution/logs/search-01.stderr.log), [search-02.stderr.log](01-email-conversation-structure/execution/logs/search-02.stderr.log).

## ENV-001

**arXiv and Semantic Scholar rate limits / arXiv timeout**

- **Status:** Open; Observed external-service/access failures; underlying cause not established.
- **Severity:** P1 — source acquisition blocked.
- **Expected:** Rate-limited/unavailable sources should be represented explicitly, with bounded compliant retry and resumable progress.
- **Observed:** Both search attempts encountered HTTP 429. arXiv also timed out during attempt 2. This evidence does not show that relevant papers are absent.
- **Affected component:** `Source clients and retry/status reporting`.
- **Run-local handling:** One manifest-authorized retry with less frequent local requests; no bypass of service limits.
- **Improvement proposal:** Record response status and safe retry diagnostics; resume after service access is restored or use a supported available source. Check required credentials without logging their values.
- **Verification criterion:** A live source check must return genuine relevant candidates before a new research attempt can be called recovered.
- **Evidence:** [search-01.stderr.log](01-email-conversation-structure/execution/logs/search-01.stderr.log), [search-02.stderr.log](01-email-conversation-structure/execution/logs/search-02.stderr.log).

## ENV-002

**DBLP response could not be decoded as JSON**

- **Status:** Open; Observed source integration/response failure — cause unconfirmed.
- **Severity:** P1 for this source.
- **Expected:** Capture safe status, content type and a limited diagnostic response sample before labeling a provider response.
- **Observed:** DBLP exhausted JSON-decoding retries with Expecting value at line 1 column 1. The available log does not establish whether the response was HTML, an empty body, a redirect or another upstream problem.
- **Affected component:** `research_pipeline/sources/dblp_source.py`.
- **Run-local handling:** Recorded failure without inventing its cause.
- **Improvement proposal:** Improve response validation and structured failure reporting; inspect and redact diagnostics before persistence.
- **Verification criterion:** Exercise valid JSON, empty, HTML and redirect responses with deterministic fixtures, plus one bounded live connectivity check.
- **Evidence:** [search-01.stderr.log](01-email-conversation-structure/execution/logs/search-01.stderr.log), [search-02.stderr.log](01-email-conversation-structure/execution/logs/search-02.stderr.log).

## CFG-001

**Default research configuration is a poor fit for foundational email research**

- **Status:** Open; Configuration fit / Skill guidance improvement.
- **Severity:** P2.
- **Expected:** Derive search windows and delegated model settings from task/user requirements and record effective values.
- **Observed:** The installed baseline used a six-month primary window and a Claude analysis_model example. This study requires classic email work and the user's exact Codex alias model. The analysis_model field is descriptive in the installed configuration model, so its presence does not prove a different model actually ran.
- **Affected component:** `Skill configuration and launch guidance`.
- **Run-local handling:** Local 480-month primary / 600-month configured fallback settings, documented effective coverage, and gpt-6-astra settings. The actual Codex process arguments match the alias.
- **Improvement proposal:** Add a task-fit preflight, warn on descriptive/unrecognized model fields, and report effective worker model settings.
- **Verification criterion:** Foundational-literature tasks must retain old directly relevant work; effective CLI and worker model settings must be inspectable without secrets.
- **Evidence:** [CONFIG_NOTES.md](01-email-conversation-structure/CONFIG_NOTES.md), [configuration-provenance.json](01-email-conversation-structure/execution/configuration-provenance.json), [launch.json](01-email-conversation-structure/execution/launch.json).


## Additional installation observation

The earlier installation check reported `/home/grammy-jiang/.claude/agents/paper-analyzer.md` as a 10-byte stub. This concerns the Claude Code installation; the current Codex Skill was discoverable and enabled, and MCP initialization/tool listing succeeded. There is no evidence that this Claude file caused the current search failure. Record it for separate installation maintenance rather than combining it with the academic-source incidents.

## Prioritized improvement order

1. Make acceptance enforce the declared contracts, and align plan schema and report output contracts.
2. Correct OpenAlex date serialization; add source-selection and dependency preflight.
3. Diagnose external source availability using bounded compliant checks and clearer failure statuses.
4. Make actual query/window coverage and fallback behavior reproducible.
5. Remove final-attempt sleep and other avoidable orchestration delay.
6. After those checks pass, resume Topic 01 and evaluate actual academic/engineering gaps from a real paper corpus.

## RP-009

**Final-report creation order contradicts the manifest dependency order.**

- **Classification:** Static Skill/manifest contract inconsistency; not an executed report-stage failure.
- **Severity:** P1 for end-to-end completion.
- **Observed:** Skill Rule 5 prohibits writing the final topic report path before validate-report is accepted. The manifest requires that same path as the report task's artifact before validate-report becomes ready.
- **Expected:** An explicit draft → validation → accepted publication lifecycle with unambiguous artifact paths.
- **Handling:** No academic final report was written. The blocked search remains the actual stopping cause.
- **Improvement:** Define candidate and final artifacts separately and make the manifest and Skill narrative use the same state transitions.
- **Verification:** A valid candidate can reach validation before final publication; a rejected candidate cannot be published as accepted.
- **Evidence:** [BLOCKERS.md](01-email-conversation-structure/BLOCKERS.md), [CONFIG_NOTES.md](01-email-conversation-structure/CONFIG_NOTES.md); installed Skill Rule 5 and manifest report/validate-report dependencies.

## RP-010

**The deep synthesizer's output is not the renderer's default input.**

- **Classification:** Static artifact-handoff inconsistency; no synthesis was produced in this run.
- **Severity:** P1 for future evidence-grounded report generation.
- **Observed:** The delegated synthesizer writes analysis/synthesis.json. The renderer selects summarize/synthesis_report.json or its legacy alternative. The current manifest does not establish a reviewed-artifact handoff between these locations.
- **Expected:** The final report must derive from the synthesis artifact that was actually analyzed and reviewed.
- **Handling:** No synthesis or report was fabricated to bridge the mismatch.
- **Improvement:** Bind report rendering to an explicit accepted synthesis artifact and record its hash/version in validation and publication results.
- **Verification:** Put intentionally different values in the legacy/deterministic synthesis and the reviewed deep synthesis; assert that rendering uses the declared accepted input and preserves its evidence references.
- **Evidence:** [BLOCKERS.md](01-email-conversation-structure/BLOCKERS.md), [Codex-internal review](01-email-conversation-structure/supervisor/INDEPENDENT_REVIEW.md); manifest paper-synthesizer output and installed cmd_report.py input selection.

## RP-011

**Delegated output attributed a supervisor-chosen scope boundary to the original user.**

- **Classification:** Reporting/provenance wording issue in the delegated workflow, not a provider or parser defect.
- **Severity:** P2 — can cause mistaken permission assumptions in a later session.
- **Observed:** The original BLOCKERS.md said the user prohibited editing the installed implementation. The no-shared-implementation-edit boundary actually came from the supervising assistant's RUN_PROMPT.md. The original user asked for research and later asked to record issues for future Skill improvements.
- **Expected:** Distinguish original user instructions, supervisory execution scope, Skill requirements and implementation limitations.
- **Handling:** The outer supervisor preserved the original files and clarified the affected wording after Codex exited. No code or permission policy was changed.
- **Improvement:** Include instruction origin in handoff records; refer to the specific supervisory prompt rather than attributing every delegated instruction to the end user.
- **Verification:** Review final blocker narratives against the original user request and the delegated prompt before making permission or approval claims.
- **Evidence:** [RUN_PROMPT.md](01-email-conversation-structure/RUN_PROMPT.md), [clarification record](01-email-conversation-structure/execution/supervisor-review/corrections.json), preserved original documents in execution/supervisor-review/originals/.

## Observed orchestration cost and latency

The Codex process exited 0 after **1,499.52 seconds** (about 25 minutes), while the research result remained blocked. The two source-search invocations took 236.20 and 267.73 seconds respectively. No academic candidate was acquired.

The CLI reported 7,901,924 input tokens, of which 7,718,912 were cached; 28,423 output tokens, including a separately reported 12,879 reasoning-output tokens. Preserve these reported fields as-is. They are not an independently measured invoice or a price estimate, and the reasoning field must not be blindly added again to output tokens.

This is an efficiency observation, not proof of a defect in the user's requested gpt-6-astra/max settings. Improvement candidates are earlier source/dependency preflight, fewer repeated full-file reads, compact state handoffs and removing post-final-retry sleeps. Preserve the user's exact alias unless the user changes it.

Evidence: [outer audit](01-email-conversation-structure/execution/independent-supervisor-audit.json), [launch metadata](01-email-conversation-structure/execution/launch.json), and the terminal turn.completed event in execution/codex-events.jsonl.

## Expected runtime warning

Codex emitted an under-development-feature warning for the user-selected mcp_2026_07_28 flag. The alias was preserved exactly. The available evidence does not connect this warning to the external API failures, so it is not classified as their cause.

## Final run outcome

Both searches returned zero-byte candidate files and exit code 0. Their independent nonempty checks failed. The workflow remains blocked, with zero completed academic rounds. The definitive outer evaluation and conditional rerun decision are in [EVALUATION.md](01-email-conversation-structure/EVALUATION.md). Fourteen categorized entries are recorded above, plus the separately noted installation observation, cost baseline and expected feature warning.

## Request-frequency follow-up

The user requested a retrospective request-frequency check and longer defaults. See [REQUEST_FREQUENCY_AUDIT.md](01-email-conversation-structure/REQUEST_FREQUENCY_AUDIT.md) and its machine-readable evidence. The project next-run profile uses 30 seconds per provider. This is a conservative project choice, not proof of source recovery or a provider-specified unblocking interval. The original two runs and their configurations remain preserved.

## RP-012

**Retry-After can be undercut by jitter, and HTTP-date values are unsupported.**

- **Classification:** Confirmed installed-code defect, reproduced offline; actual historical response-header values are unavailable.
- **Severity:** P1 — a retry can precede the server's requested waiting time.
- **Observed:** The generic retry handler takes the maximum of exponential delay and numeric Retry-After, then applies ±25% jitter. A mock response with Retry-After: 60 produced 45-second waits when jitter took its lower bound. HTTP-date input returned None. The independent arXiv path also ignores HTTP-date headers.
- **Expected:** Support both permitted Retry-After forms and treat the server's waiting deadline as a lower bound after all jitter and scheduling calculations.
- **Handling:** No live reproduction; mocked responses, sleep and randomness only. The 30-second profile does not resolve this defect.
- **Improvement:** Normalize server deadlines, combine them with local rate limits, and apply only jitter that does not move dispatch before the applicable deadline.
- **Verification:** Numeric and date headers, skew/expired dates and jitter extremes must never result in an early dispatch. Verify both generic and arXiv paths.
- **Evidence:** [frequency audit](01-email-conversation-structure/REQUEST_FREQUENCY_AUDIT.md), [offline results and installed-source hashes](01-email-conversation-structure/execution/request-frequency-audit.json).

## RP-013

**The generic retry policy repeats nontransient bad requests.**

- **Classification:** Confirmed runtime and offline behavior.
- **Severity:** P2 — unnecessary load and delayed actionable errors.
- **Observed:** OpenAlex repeatedly returned HTTP 400 for malformed dates. The generic decorator catches requests.RequestException without a retryable-status filter. An offline 400 fixture was attempted three times.
- **Expected:** Distinguish retryable transport/transient service failures from parameter errors that need correction.
- **Handling:** No shared-code change or new live requests. Recorded separately from the underlying date-format defect RP-001.
- **Improvement:** Define provider-aware status/error classification; propagate nontransient errors immediately with useful safe diagnostics.
- **Verification:** Invalid-parameter 400 is attempted once; permitted transient failures follow bounded backoff and Retry-After requirements.
- **Evidence:** [frequency audit](01-email-conversation-structure/REQUEST_FREQUENCY_AUDIT.md), both search stderr logs, installed infra/retry.py.

## RP-014

**Per-instance throttling does not preserve a shared service budget or cooldown.**

- **Classification:** Confirmed static limitation; prior aggregate-rate violation is not demonstrated.
- **Severity:** P2 — separately throttled clients can collectively exceed a service limit.
- **Observed:** RateLimiter stores its lock and last-request timestamp in each object. CLI source dispatch creates fresh clients for each search. No shared per-service deadline across processes or persisted source cooldown is established by these paths.
- **Expected:** All concurrent requests sharing a provider budget should be coordinated; process/round restarts should not discard an active server-requested cooldown.
- **Handling:** Future msgloom research is limited to one pipeline task at a time; no claim that unrelated device traffic has been controlled.
- **Improvement:** Use a provider/account-scoped shared budget and persisted not-before state, including the outer workflow retry path.
- **Verification:** Two independent clients/processes respect the combined interval; a new run cannot dispatch before a saved Retry-After deadline.
- **Evidence:** [installed-source hashes](01-email-conversation-structure/execution/request-frequency-audit.json), infra/rate_limit.py and cli/cmd_search.py; [arXiv aggregate-use limits](https://info.arxiv.org/help/api/tou.html#rate-limits).

## RP-015

**HTTP telemetry cannot establish the cause or duration of rate restrictions.**

- **Classification:** Observed diagnostic coverage gap.
- **Severity:** P2 — prevents reliable frequency attribution and recovery decisions.
- **Observed:** Most clients log failure time rather than dispatch time. Failed-response headers and bodies were not retained. No raw Retry-After, quota reset, provider request ID or account/IP aggregate is available.
- **Expected:** A compact event for each attempt should distinguish dispatch, completion, status, retry decision and effective waiting deadline.
- **Handling:** The audit labels application-level counts and response timestamps precisely, and leaves ban scope/expiry and historical aggregate traffic unknown.
- **Improvement:** Add safe allowlisted response diagnostics, actual request timing, attempt/query identity and rate-budget scope. Redact credentials and credential-bearing URLs.
- **Verification:** A synthetic 429 can be traced from dispatch through its response and deadline to the next allowed attempt; sensitive values do not appear in records.
- **Evidence:** [request-frequency-audit.json](01-email-conversation-structure/execution/request-frequency-audit.json), both search stderr logs.

## Repair checkpoint — 2026-09-14

The entries above describe the original installed version and its two failed
research attempts. This checkpoint supersedes their implementation status only;
it does not rewrite historical evidence or claim the providers have recovered.

Repairs are implemented in the separate worktree
/home/grammy-jiang/Projects/research-pipeline-reliability on branch
fix/source-workflow-reliability, based on b4d480e349d77a604edfc40ed32ddaa34f84eb90.
The original checkout's existing MCP dependency pin is preserved. The installed
CLI, MCP package and Skill have not been updated. No new msgloom research round
was started.

Detailed review and proposed remaining test maintenance are in that worktree's
docs/source-reliability-review.md and
docs/source-reliability-test-maintenance.md.

| Issue | Source-branch handling | Remaining qualification |
| --- | --- | --- |
| RP-001 | OpenAlex date normalization repaired. | Offline verification only. |
| RP-002 | Semantic validators, execution receipts, mandatory tasks and review decisions enforced. | Not installed; actual LLM judgment still needs evaluation in future research. |
| RP-003 | All-source failure is nonzero in CLI and unsuccessful in MCP; empty/partial/failed coverage is explicit. | Existing old success-expectation tests need approved maintenance. |
| RP-004 | Runtime and Skill query-plan schemas aligned; CLI/MCP share query planning. | Not installed. |
| RP-005 | Manifest honors configured sources instead of forcing all. | Existing user profiles still determine source selection. |
| RP-006 | Actual query/date coverage recorded; only successful sparse sources receive supported date fallback. | HF feed and SDK-internal HTTP visibility limits remain explicit. |
| RP-007 | Draft and final paths aligned across manifest, renderer and completion. | Not installed. |
| RP-008 | No terminal arXiv retry sleep. | Offline timeout/429 fixtures. |
| RP-009 | Review and validation precede publication; matching content hash required. | Not installed. |
| RP-010 | Deep JSON matches the renderer contract and is passed explicitly. | Independent offline deep-content rendering verified. |
| RP-011 | Instruction-origin guidance clarified; historical correction preserved. | Narratives remain subject to human/supervisory review. |
| RP-012 | Numeric/date Retry-After cannot be shortened by jitter; HTTP 429 creates persisted cooldown. | 15-minute fallback without usable header is local policy, not provider recovery evidence. |
| RP-013 | Nontransient 4xx and invalid JSON stop; permitted transient failures remain bounded. | Offline fixtures. |
| RP-014 | Provider budgets persist and coordinate local processes; code and bundled Skill default to 30 seconds. | Shared directory/POSIX scope; streamed bodies, SDK internals and other hosts are not fully controlled. |
| RP-015 | Safe HTTP attempt IDs, timing, status, content type and cooldown events added. | Historical missing telemetry cannot be reconstructed. |
| ENV-001 / ENV-002 | Remain open. | No successful recovery probe; restriction cause, scope and expiry remain unknown. |
| CFG-001 | Task-fit dates, explicit query variants and model provenance documented. | Root example still needs approved update; existing configs can override new defaults. |

### Verification checkpoint

- Five new regression files: 37 passed in 1.09 seconds with external-network
  blocking, job a88a47190029.
- Full guarded unit suite at the preceding checkpoint: 4,839 passed, 12 failed,
  1 skipped in 80.82 seconds, job 67f75eaa0e3d. Do not combine these counts or
  describe the full suite as green.
- Strict mypy passed for 322 source files; Ruff passed.
- An independent agent exercised quick/deep paths with actual offline CLI
  plan/report/validation/publication/completion commands and synthetic source
  and worker artifacts. Rejected/stale evidence and incorrect run identities
  blocked. This is a workflow contract check, not academic quality validation.
- Existing tests were left unchanged because AGENTS.md explicitly requires
  approval to modify them. The remaining 12 failures affect five files and
  cover stale helper mocks, the old 5-second assertion, a mock limiter, and
  incomplete HTTP isolation. Root config.example.toml is outside HC2's allowed
  write paths and still contains seven old interval examples.

## RP-016

**Resumed search can erase or misrepresent saved evidence.**

- **Classification:** Found during independent source verification.
- **Severity:** P1 — can replace useful partial output or incorrectly promote it.
- **Observed:** CLI/MCP resume paths did not consistently preserve recorded
  coverage and could rerun or replace output.
- **Repair:** Shared resume loading validates the saved JSONL/count/coverage and
  preserves empty/partial/failed status without issuing requests. Legacy output
  without coverage is explicitly unverified.
- **Verification:** Offline saved-artifact and no-network resume cases pass.
- **Status:** Repaired in review branch; not installed.

## RP-017

**Scholar failures and provenance can be lost.**

- **Classification:** Found during independent source verification.
- **Severity:** P1 for failure masking; P2 for unstable/mislabelled identifiers.
- **Observed:** SDK or SerpAPI failures could appear as valid zero-result
  searches. Candidate origin/identity and cross-query pacing were inconsistent.
- **Repair:** Surface dependency, SDK and API errors; preserve scholar source and
  stable IDs; coordinate high-level SDK operations and SerpAPI requests.
- **Limit:** Internal SDK requests can remain invisible to this scheduler.
- **Status:** Repaired and covered offline; not installed.

## RP-018

**Partial arXiv results and invalid response shape are mishandled.**

- **Classification:** Found during independent source verification.
- **Severity:** P1 — acquired evidence can disappear or HTML can look like an
  empty successful search.
- **Repair:** Preserve earlier pages after later failure, separate raw files by
  window/query, and reject non-Atom responses or a feed whose entries all fail
  parsing.
- **Verification:** Mocked partial-page and invalid-response cases pass.
- **Status:** Repaired in review branch; not installed.

## RP-019

**Worker and MCP artifact contracts disagree with downstream consumers.**

- **Classification:** Found during workflow inspection and independent execution.
- **Severity:** P1 — valid-looking files could bypass meaningful screening or
  fail downstream with the wrong shape.
- **Repair:** Use canonical shortlist records; require LLM screening score,
  rationale and evidence for download decisions; provide correct rough/fine
  conversion paths; align synthesis JSON, reviewer draft/hash and gap inputs.
  Unknown synthesis paper IDs fail the gate.
- **Verification:** Offline fixtures and quick/deep forward execution.
- **Status:** Repaired in review branch; not installed.

## RP-020

**Run identity and previous-round context are not reliably preserved.**

- **Classification:** Found during independent workflow execution.
- **Severity:** P1 — failure bookkeeping or continuation could refer to the wrong
  run or lose prior report context.
- **Repair:** Record failed plan exits before run ID assignment, require expected
  run IDs, resolve workspace arguments safely, retain bounded retry history, and
  invalidate dependent task acceptance on relevant artifact changes. Preserve
  prior final reports with unique snapshots and propagate prior paper IDs/gaps.
- **Verification:** Exit-42 planning failure, wrong ID, paths with spaces, changed
  plan, repeated snapshots and resumed context cases pass offline.
- **Limit:** The runner completes one cycle; the parent decides whether to prepare
  a separate gap-focused round. No automatic multi-round completion is claimed.
- **Status:** Repaired in review branch; not installed.

## RP-021

**Validation failure need not fail the CLI or prevent final completion.**

- **Classification:** Found during repair verification.
- **Severity:** P1 — a failed validation file can accompany a successful process.
- **Repair:** Return validation success explicitly, map failure to CLI exit 1 and
  MCP failure, persist report path/hash, and require matching passing validation
  before publication and completion.
- **Verification:** Offline failed-validation and changed-report cases block.
- **Status:** Repaired in review branch; not installed.

## TEST-001

**Legacy unit tests attempted external requests during repair verification.**

- **Classification:** Confirmed assistant test-isolation mistake plus existing
  fixture defects. This is separate from the historical research failures.
- **Observed:** The first broad unit run was launched without a global external
  network guard. Some enrichment tests mocked DOI lookup but not title fallback.
  One Semantic Scholar request is confirmed by the persisted shared budget:
  dispatch at 2026-09-14T03:30:48.368081Z, followed by HTTP 429 and a saved deadline
  of 2026-09-14T03:45:50.751279Z. Subsequent requests sharing that budget were
  stopped by cooldown.
- **Evidence:** /home/grammy-jiang/.cache/research-pipeline/request-budgets/e74adabe62d7ea09a4c844ed.json
  recorded last_start=1789356648.3680813 and not_before=1789357550.7512789.
  The unguarded full-suite job was 1a39e2dbd824.
- **Limits:** There is no complete wire trace for that unguarded suite, so one is
  the confirmed count, not an asserted exhaustive total. This request does not
  establish the cause of the earlier restriction. The user was informed.
- **Additional finding:** The guarded run stopped three incompletely mocked test
  paths: two enrichment cases and a Mistral OCR "import error" case. The latter
  assumed an absent SDK although the backend uses direct HTTP. No fixture PDF
  was sent by the guarded run.
- **Containment:** Added opt-in tests/test_offline_guard.py to block external
  Requests sends, DNS and sockets and isolate synthetic budget state. All
  subsequent pytest invocations use this guard. Real cooldown state was neither
  cleared nor rotated.
- **Follow-up:** Approve maintenance of the identified existing tests, keep the
  guard for unit verification, and require a green guarded suite before install.

### Saved review checkpoint

Commit 31d57a7a4050bd3e9e0f19394fa2c34df6c103db is saved and verified on the
remote branch fix/source-workflow-reliability:
https://github.com/grammy-jiang/research-pipeline/tree/fix/source-workflow-reliability

Final pre-commit run passed (job b94b3773227f). The required guarded
stop-on-first-failure unit check passed 1,135 tests before reaching the known
stale CLI dedup mock (job b90327862438). No existing test or root example was
modified. Approval is pending for the precise maintenance scope documented in
the source branch.

The initial SSH push failed because noninteractive public-key authentication
was unavailable. Synchronization then succeeded using the device's existing
authenticated GitHub CLI over HTTPS; the repository's origin URL was preserved.
No installation, provider recovery probe, or new research round was performed.

## Release preparation authorized — 2026-09-14

The user explicitly authorized committing the remaining changes, pushing,
creating a new release, and updating the local installation. The proposed five
existing test files and root example were updated. The 12 formerly failing cases
pass. The full local guarded suite passes: 4,852 passed, 1 skipped, coverage
84.86% (job a085efc88473). The new network guard is enabled in CI.

Review PR: https://github.com/grammy-jiang/research-pipeline/pull/193
Prepared release commit: 7eb8b4c4393263f9668d735ac2520dcfb0c44e5f
Target release: v0.33.0; bundled Research Pipeline manifest: 2.1.0.

The first PR CI run passed lint, types and unit tests on Python 3.12 and 3.13.
Its security gate failed; that finding is recorded as RP-024 below. The tag has
not been pushed and the running installation has not yet been replaced at this
checkpoint.

The existing Codex MCP entry uses research-pipeline mcp serve. The installed
Skill matches its original packaged source, with no user customization detected.
A private backup of the Skill and installation metadata, together with hashes
of the Codex configuration, shell configuration and persisted request budgets,
was saved before upgrading:
 /home/grammy-jiang/.local/state/research-pipeline/updates/v0.33.0-20260914T042858Z

## RP-022

**Release documentation describes the wrong publishing trigger.**

- **Observed:** The developer guide said creating a GitHub Release triggered
  publishing and that pushing a tag triggered CI. The actual Publish workflow
  triggers on version-tag push or workflow dispatch; CI triggers on master/PR.
- **Impact:** Following the prose could leave a release unpublished or publish
  a tag before checking CI.
- **Repair:** Document the actual order: local checks, PR CI, merge, tag push,
  then verify both PyPI and GitHub publication.
- **Verification:** Read .github/workflows/publish.yml and ci.yml directly.
- **Status:** Corrected in the release branch.

## RP-023

**The operations guide uses a nonexistent version subcommand.**

- **Observed:** A built-wheel smoke check following the guide failed with
  "No such command version". The implemented command is --version.
- **Repair:** Correct both operations-runbook examples.
- **Verification:** The built v0.33.0 wheel reports version 0.33.0 using
  --version, and the packaged workflow --help succeeds (job b32b75f26a5d).
- **Status:** Corrected in the release branch.

## RP-024

**The existing dependency lock contains vulnerable package versions.**

- **Observed:** PR CI run 34806089589 produced 16 vulnerability findings across
  six packages (including repeated advisory rows), while lint, types and both
  Python unit-test jobs passed.
- **Evidence:** https://github.com/grammy-jiang/research-pipeline/actions/runs/34806089589
- **Repair:** Update click 8.3.1 to 8.3.3, cryptography 49.0.0 to 50.0.0,
  mcp 1.26.0 to 1.30.0, mkdocs-material 9.7.6 to 9.7.7, pip 26.1.2 to 26.2,
  and pymdown-extensions 10.21.3 to 11.0.1. Raise corresponding dependency floors,
  retaining the MCP <2 bound. Do not add audit suppressions.
- **Verification:** In the isolated worktree environment, the existing
  make audit-deps policy passes (job dbad3f0adab0), the license gate passes
  (job d3efcbbd335f), and strict mypy passes (job 15529f7ca0f7).
  The existing two audit exceptions remain unchanged; a passing policy gate is
  not a claim that all dependencies are free of every possible vulnerability.
- **Status:** Patched locally; complete the refreshed tests and CI before tagging.


## Release PR review findings — 2026-09-14

PR #193 review at commit 7eb8b4c4393263f9668d735ac2520dcfb0c44e5f
was evaluated against the source and the user's existing release authorization.
Nine new offline regressions reproduced the actionable findings before fixes;
all nine passed afterward as part of a 44-test focused run (job e3ebbe81f19f).
An automated comment alleging missing approval lacked the conversation context:
the user had explicitly approved the proposed test/config maintenance and release.
No extra permission was required or inferred from that comment.

## RP-025

**Configured limits and enrichment credentials did not reach every call path.**

- **Evidence:** PR review comments 4002226630 and 4002229863; shared planning
  replaced configured sparsity thresholds with model defaults. Watch, download
  and enrichment could construct sessions with a default interval despite the
  configured limiter. Enrichment looked up its API key on the wrong config object.
- **Fix:** Propagate configured thresholds, intervals and source credentials
  through CLI, MCP and orchestrator paths. Enrichment session pacing uses the
  supplied limiter interval.
- **Verification:** Offline threshold and watch budget regressions; existing
  enrichment key-header assertions preserved. Explicit watch config fixtures
  now verify a 45-second override reaches both session and limiter.
- **Status:** Patched in the release worktree; final CI and installation pending.

## RP-026

**The new shared budget lock required POSIX fcntl and broke Windows requests.**

- **Evidence:** PR review comments 4002226610 and 4002229860; the shared request
  path imported fcntl at runtime on every supported platform.
- **Fix:** Use filelock with an explicit runtime dependency, preserving
  cross-process serialization and persistent cooldown state.
- **Verification:** Existing shared-client/process budget regressions pass on
  Linux. Windows execution has not been performed locally.
- **Status:** Patched; no process-only fallback or reset of live cooldown state.

## RP-027

**Reports could pass validation without the workflow's required format.**

- **Evidence:** PR review comment 4002229854; the structured report lacked
  Contents, Round History, Mermaid and LaTeX, and weighted checks could still pass.
- **Fix:** Render the required sections and apply strict format validation in the
  workflow, publication and completion checks. Publication rechecks actual draft
  content as well as its hash. The runner supplies its Python interpreter to the
  publication helper so the installed dependency imports work under pipx.
- **Verification:** Four negative format cases fail strict validation, a valid
  structured report passes, and a forged passing validation artifact cannot
  publish a malformed draft. Fresh quick/deep execution is being checked.
- **Status:** Patched in the release worktree; final CI and installation pending.

## RP-028

**MCP report validation was labelled read-only although it writes an artifact.**

- **Evidence:** PR review comment 4002229866 and the validation implementation's
  report-validation JSON write.
- **Fix:** Set readOnlyHint=false and expose the strict_format input consistently.
- **Verification:** The actual MCP tool listing reports mutating validation.
- **Status:** Patched in the release worktree; final CI and installation pending.

The first full suite after these changes stopped on a watch fixture that passed
an explicit nonexistent config path (4,734 passed, 1 skipped, job b4150b7fdb9d).
The fixture now creates the config and preserves original behavior assertions;
watch plus new review regressions pass (25 passed, job ec352289d971). All these
runs used the external-network guard and did not probe academic providers.

## RP-029

**The structured renderer corrupts a valid worker Markdown closing fence.**

- **Evidence:** Independent fresh quick/deep execution retained synthesis
  taxonomy[0].finding ending in a standalone Mermaid closing fence with no
  terminal newline. The template appended [SYNTH-001, SYNTH-002] on that fence
  line. The quick draft passed strict validation at score 0.94 despite the
  malformed Markdown. This is a renderer/validation defect, not invalid worker
  content.
- **Fix:** Separate citations from multiline findings, assumptions and mechanism
  descriptions. Strict format and publication checks reject unterminated Mermaid
  blocks even if the report contains another valid diagram.
- **Verification:** Two focused regressions cover preservation of a valid worker
  block and rejection of a malformed extra block. All 11 release review
  regressions passed together (job 592ba4786cc0).
- **Evidence archive:** Pre-repair quick/deep synthesis, drafts and workflow
  state are retained at
  /home/grammy-jiang/.local/state/research-pipeline/updates/v0.33.0-20260914T042858Z/forward-fence-defect.
- **Status:** Patched before tagging; final offline workflow execution pending.

## RP-030

**Report quality diagnostics undercount structured confidence and opaque IDs.**

- **Evidence:** The independent synthetic workflow rendered visible **LOW**
  labels and SYNTH-* citations, yet legacy diagnostics reported missing
  confidence annotations and zero citation coverage. Confidence detection
  expects emoji or confidence: labels; FACT extraction recognizes narrower
  citation shapes than the supported corpus identifier contract.
- **Impact:** Misleading quality diagnostics. The observed reports still
  completed their actual evidence, review, strict format and publication gates;
  this observation does not establish real scholarly citation accuracy.
- **Status:** Recorded follow-up limitation. A future change should align both
  legacy and structured confidence/citation extraction with known corpus IDs
  and reject unknown references without inventing support.

## RP-031

**Template whitespace turns table rows into ordinary Markdown paragraphs.**

- **Evidence:** Independent deep review found blank lines between header/body
  rows in Scope and Corpus, Evidence Matrix and Traceability Appendix. A
  Markdown-parser regression rendered zero expected paper data cells before
  the fix (job af9b3d94b8c1).
- **Fix:** Apply narrow Jinja whitespace control to those three table loops.
- **Verification:** Both fixture papers now render in all three table bodies.
  All 12 release review regressions pass (job 71e6dbecfec3).
- **Evidence archive:** The pre-fix deep draft is saved as
  /home/grammy-jiang/.local/state/research-pipeline/updates/v0.33.0-20260914T042858Z/forward-table-defect.md.
- **Status:** Patched before tagging; final quick/deep states exercise the final
  renderer without increasing the prior state's exhausted review budget.

The independent review also noted redundant citations when worker prose already
contains the support IDs that the template appends. This is a cosmetic follow-up,
not an unsupported-citation or publication failure. Keep it separate from RP-030.

## Final release candidate verification — 2026-09-14

- Source commit: 119df1206cb3c07152f954b79023a37a41a770d3, clean release worktree.
- Final local guarded suite: 4,864 passed, 1 skipped; coverage 84.87%.
  Formatting, lint, strict types and all pre-commit hooks passed (job 4286d3b934f7).
- Both fresh quick and deep synthetic workflows completed all report, strict
  validation, publication and completion tasks with exit 0. Published hashes
  equal the validated hashes; deep also equals the independent review hash.
- Both reports render four real Markdown tables and two closed Mermaid blocks.
- No academic provider queries were dispatched. The inherited guard blocked
  local DNS/socket/HTTP sentinel probes before dispatch.
- Acquisition/conversion and worker artifacts were explicitly synthetic.
  Each report's one academic and one engineering gap is outside the bounded
  release check, so rerunning live research is not warranted by those gaps.
- Forward evidence is archived at
  /home/grammy-jiang/.local/state/research-pipeline/updates/v0.33.0-20260914T042858Z/forward-final.
- RP-025 through RP-029 and RP-031 fixes are verified in this candidate.
  RP-030 and cosmetic duplicate citations remain recorded follow-up limitations.

## ENV-003

**The package index/cache view lagged behind the new release.**

- **Evidence:** The initial constrained pipx upgrade failed with a generic
  ResolutionImpossible. A read-only resolver check showed only versions through
  0.32.0, while official PyPI JSON and GitHub exposed matching 0.33.0 artifact
  digests. An environment-only index retry also failed.
- **Resolution:** A dry run with explicit official PyPI and no cache succeeded.
  The same explicit source/no-cache settings then upgraded pipx to 0.33.0.
  Temporary source/cache/constraint arguments were removed from persisted pipx
  metadata, preserving the user's original package source preferences.
- **Status:** Resolved for this update. This is package distribution/index
  propagation behavior, not evidence of academic-provider recovery or blocking.
- **Operational notes:** The installed pipx parser required --pip-args=VALUE for
  a value beginning with flags. One preparatory smoke script had a quoted-newline
  syntax error, caught before execution and corrected via structured file input.
  Neither preparation failure changed the installed package or ran research.

## Release and Raspberry Pi installation complete — 2026-09-14

- PR #193 merged:
  https://github.com/grammy-jiang/research-pipeline/pull/193
- Final candidate commit: 119df1206cb3c07152f954b79023a37a41a770d3.
- Master merge/tag commit: 593741fa985cd9f13e77953b6f358a39b95f94e0.
  The merge tree exactly matches the tested candidate.
- Published release:
  https://github.com/grammy-jiang/research-pipeline/releases/tag/v0.33.0
- PyPI: https://pypi.org/project/research-pipeline/0.33.0/
- Candidate CI 34808699193 passed all five jobs, including Python 3.12/3.13,
  security/license, strict types and lint/format.
- Publish workflow 34808959960 completed build, PyPI and GitHub jobs.
  Wheel and sdist SHA-256 values match between PyPI and GitHub.
- Local CLI and MCP package upgraded from 0.32.0 to 0.33.0. MCP SDK remains
  1.30.0 within the retained <2 constraint. The workflow CLI entry point works.
- Installed Research Pipeline Skill manifest is 2.1.0; all 37 non-cache files
  match the released package's bundled Skill.
- Actual installed MCP stdio initialization, discovery of 67 tools, strict-format
  schema/mutating annotation, and synthetic planning with configured thresholds
  passed under inherited network blocking. All seven provider defaults are
  30 seconds. pip check reports no broken requirements.
- The original Codex config, .bashrc alias and all three persistent provider
  budget JSON files match the pre-upgrade hashes. Existing user checkout edits
  are preserved; the release worktree is clean.
- Final local suite: 4,864 passed, 1 skipped, coverage 84.87%. Both fresh quick
  and deep offline workflows completed, with exact validated/publication hashes.
- No Codex session or new msgloom research round was launched during release or
  installation. The installed-package plan is a clearly synthetic smoke check.
  No provider cooldown was reset, and no real recovery claim is made.
- Remaining follow-ups: RP-030 confidence/opaque-ID quality diagnostics and
  cosmetic duplicate citations. Prior issue entries retain their dated history.
- Installation, release and rollback evidence:
  /home/grammy-jiang/.local/state/research-pipeline/updates/v0.33.0-20260914T042858Z

## User-authorized public access check — 2026-09-14T05:36:32.807971+00:00

One anonymous minimal search GET per affected provider, at least 30 seconds apart, from the Raspberry Pi's existing route. No automatic retries, alternate identities, API keys, redirects or research workflow were used. Existing shared budgets were honored; new 429 cooldowns were persisted.

| Provider | HTTP | Result |
| --- | --- | --- |
| arxiv | 429 | rate_limited |
| semantic_scholar | 429 | rate_limited |
| dblp | 200 | unexpected_response |
| openalex | 200 | public_search_ok |

Evidence: 01-email-conversation-structure/execution/public-access-check-20260914T053632Z.json

A successful result establishes current access to this endpoint only. HTTP 429 establishes rate limiting, not its IP/account/shared-quota cause or permanence. A transport error does not establish an IP block.

## RP-032

**Existing MCP progress/log helpers call asynchronous SDK methods without awaiting.**

- **Observed:** src/research_pipeline/mcp_server/tools/_common.py calls
  ctx.report_progress and ctx.info from synchronous helpers without awaiting
  or bridging to the event loop. Local MCP SDK 1.30.0 inspection confirms both
  methods are coroutine functions.
- **Impact:** Those helper paths do not send the intended notifications and can
  produce unawaited-coroutine warnings. This finding does not prove a provider
  block or establish the outcome of any earlier research run.
- **Containment:** The new source-access probe uses a worker thread for blocking
  checks and anyio.from_thread.run for awaited notifications. A notification
  failure is logged by exception type and does not discard source observations.
- **Verification:** New offline tests assert that progress is awaited and that
  notification failure retains a completed report. No live provider calls.
- **Status:** Existing shared helpers remain a recorded follow-up; the new
  diagnostic does not use them.

## TEST-002

**Two existing MCP inventory tests pin the old total of 67 tools.**

- **Observed:** Adding tool_probe_sources increases the registered and
  domain-mapped inventory to 68. Existing test_mcp_server.py::test_tool_count
  and test_mcp_toolsets.py::test_map_has_no_duplicates_and_expected_size
  assert 67. The focused compatibility run reproduces the map-count failure.
- **Required maintenance:** Change only these expected totals from 67 to 68 and
  add a short explanatory comment. Keep duplicate detection, tool coverage and
  all behavior assertions intact.
- **Constraint:** Repository AGENTS.md and testing.instructions.md require
  explicit approval before modifying existing tests; neither file is changed
  at this checkpoint.
- **Status:** Narrow test maintenance pending. The new diagnostic's own tests
  exercise response classification, shared cooldowns, anonymous serial requests,
  JSON/exit codes and MCP annotations/progress.

## Public source-access diagnostic implementation — 2026-09-14

- Added probe-sources CLI and tool_probe_sources MCP diagnostic in source branch
  feat/source-access-probe, based on released v0.33.0.
- Fixed minimal endpoints: arXiv, Semantic Scholar, DBLP and OpenAlex. At most one
  anonymous GET per source, no redirects/retries, at least 30-second spacing,
  longer configured per-source pacing retained, shared cooldowns respected.
- Recognizes DBLP's observed HTTP-200 robot challenge instead of calling it
  recovered. HTTP response receipt is reported separately from search usability.
- No provider was contacted by the implementation tests. The previously saved
  05:36–05:38 UTC live observations are still the latest actual access evidence.
- Source usage and limitations: docs/source-access-probe.md.
- Existing installed release remains v0.33.0 at this checkpoint.

### Saved source-access probe review checkpoint

- Commit: 36e722b99186b2f32baa6e1487c72a6dc6bf6e98.
- Remote branch: feat/source-access-probe; worktree clean.
- Draft PR: https://github.com/grammy-jiang/research-pipeline/pull/194
- ruff, strict mypy and all pre-commit hooks passed.
- Full guarded unit suite: 4,895 passed, 1 skipped, 2 failed; both
  failures are the existing fixed tool-count assertions in TEST-002.
- Required stop-on-first-failure run reproduced the first count failure
  after 3,251 passes. No other failure was found in the complete run.
- Existing tests remain unchanged pending the narrow maintenance approval.
- CLI help check passed. No new live source check, research run, release
  or installed-package replacement was performed.

### PR #194 review-cycle continuation — 2026-09-14

The user authorized continuing through comment fixes, AI follow-up review and
successful checks before merging. TEST-002's two existing inventory expectations
were updated to 68; all duplicate/coverage checks are retained.

- Commit f04ae4c1: test: align MCP inventory with source probe.
- Full guarded local unit suite: 4,897 passed, 1 skipped (job 2ec9fc8b63e3).
- Ruff, strict mypy and all pre-commit hooks pass (job 7d54be804eb2).
- The old PR CI failure was verified to be the same count assertion.
- PR #194 is now ready for AI review of the corrected commit.

## RP-033

**An automatic PR reviewer lacked the active-session authorization context.**

- Codex review 5194655251 raised one P1 policy finding because the two existing
  inventory assertions were changed without approval visible in its review context.
- The owner had directly responded to the specific 67-to-68 approval question by
  instructing completion of the fixes, AI review and successful checks before merge.
- Repair: record the exact instruction and narrow test-change scope in the PR
  discussion/description, then request reevaluation. Do not alter the repository
  approval rule or fabricate a separate approval.
- Copilot reviewed all 16 changed files, generated no comments and recommended
  approval. Five CI jobs pass on f04ae4c1.
- Follow-up Codex review requested on the same source commit; the finding remains
  unresolved until its response is evaluated.

### PR #194 review completed and merged — 2026-09-14T06:49:59Z

- Merged PR: https://github.com/grammy-jiang/research-pipeline/pull/194
- Reviewed/tested candidate: f04ae4c1316e71f8dde8f6bbf78c159e5a49912b.
- Merge commit: a2bf2fc5a79d1b7f076b1015c67b61214765e07f. Its tree exactly matches the reviewed candidate.
- Full local guarded unit suite: 4,897 passed, 1 skipped. Ruff, strict mypy and
  all pre-commit hooks passed.
- Candidate CI 34813434070: all five jobs passed, including Python 3.12/3.13,
  lint/format, strict types and security/license checks.
- Copilot reviewed all 16 changed files, produced zero comments and recommended
  approval: https://github.com/grammy-jiang/research-pipeline/pull/194#pullrequestreview-5194573808
- Codex's initial policy-context finding was answered with the owner's exact
  session instruction and the narrow test-change scope, then sent for reevaluation.
- Codex follow-up completed at 06:47:02 UTC on the same candidate, reported no
  major issues and gave thumbs-up:
  https://github.com/grammy-jiang/research-pipeline/pull/194#issuecomment-5660110261
- The sole review thread was resolved after that follow-up response. All comments,
  review threads, current commit and CI were checked again before the SHA-guarded
  normal merge. No approval rule or branch protection was bypassed.
- TEST-002 and RP-033 are resolved for this PR. RP-032 remains the separately
  recorded pre-existing shared-notification-helper follow-up.
- The Secure Code Warrior comment was a phrase-triggered training link rather
  than a code-specific finding.
- No live academic-provider check, research run, release or installed-package
  replacement occurred during this PR review cycle.

## User-authorized public access recheck — 2026-09-14T07:04:23.481016Z

Executed the reviewed probe from the Raspberry Pi's existing route, using the normal shared request budgets. At most one anonymous request per source, at least 30 seconds apart, no retries or redirect following. No API keys or cooldown reset.

| Provider | HTTP | Result | Local cooldown until (UTC) |
| --- | --- | --- | --- |
| arxiv | 429 | rate_limited | 2026-09-14T07:19:23.868814Z |
| semantic_scholar | 429 | rate_limited | 2026-09-14T07:19:54.092518Z |
| dblp | 200 | bot_challenge | - |
| openalex | 200 | ok | - |

Evidence: 01-email-conversation-structure/execution/public-access-check-20260914T070422Z.json

Results establish current access only to the tested public search endpoints. Rate limits and robot challenges do not prove an IP-specific or permanent ban. Local cooldown deadlines do not predict server-side recovery.


## arXiv website/API discrepancy audit — 2026-09-14T07:22:25Z

The user reports that manual arXiv search, browsing, PDF and HTML access work.
The browser device, network route and exact URL were not observed. This report
must not be generalized to successful API access from the Raspberry Pi.

- The official API Basics documents export.arxiv.org/api/query and anonymous
  GET parameters search_query, start and max_results. The configured host/path
  match. The installed arXiv client, query builder, HTTP session, budget and
  limiter match the reviewed source checkout byte for byte.
- The current diagnostic process has no HTTP(S)/ALL proxy environment
  variables. Offline-prepared requests contain neither Authorization nor Cookie,
  use research-pipeline/0.33.0, and retain normal TLS certificate verification.
  Absence of an explicit proxy does not establish the route used by the user's
  browser or exclude transparent network intermediaries.
- The actual email/conversation query and the minimal email/electron queries
  survive requests preparation and query decoding correctly. No live search
  run, full-text download, alternate identity or alternate IP was used.
- Prior arXiv cooldown ended at 07:19:23.868814 UTC and was honored, not reset.
  Both diagnostic attempts used the same persistent arxiv budget at 60 seconds.
- 07:22:25.347 UTC: the official HTTP minimal electron query returned 301,
  explicitly redirecting to the same export.arxiv.org/api/query host/path over
  HTTPS. The redirect was recorded, not followed automatically.
- 07:23:25.399 UTC: after 60 seconds from completion of the first request, the
  HTTPS equivalent was attempted once and raised ReadTimeout after 15.083 s.
  No HTTP response was received for that attempt; it is not a new 429 observation.
- Exactly two network attempts were made, with no retries. Testing stopped.
  This 15-second diagnostic read timeout is shorter than the normal arXiv
  client's default 60 seconds. A timeout here cannot prove that the normal
  search client would fail with its longer wait, or that an IP is blocked.
- The official status page showed main site, search and export as up at audit
  time. It is provider-wide status, not evidence that this client's route works.

**Conclusion:** retain the HTTPS endpoint. The evidence does not support a
website-wide or IP-specific ban claim. It establishes previous API 429s and a
new API timeout, with the cause still unresolved. Browser success and these API
observations can coexist. No spoofed browser identity, website-search scraper,
IP change, key rotation or repeated recovery polling is justified.

Evidence:
- [Protocol comparison](01-email-conversation-structure/execution/arxiv-api-protocol-diagnostic-20260914T072225Z.json)
- [Offline request audit](01-email-conversation-structure/execution/arxiv-request-construction-audit-20260914.json)
- [Previous probe](01-email-conversation-structure/execution/public-access-check-20260914T070422Z.json)
- [Official API Basics](https://info.arxiv.org/help/api/basics.html)
- [Official API Terms](https://info.arxiv.org/help/api/tou.html)
- [Official robot guidance](https://info.arxiv.org/help/robots.html)
- [Official status](https://status.arxiv.org/)

## RP-034

**arXiv search-query construction does not encode reserved URL characters.**

- **Classification:** Confirmed existing implementation defect, reproduced
  entirely offline in both the reviewed and installed matching implementation.
- **Severity:** P2 — search intent can be silently altered for valid topic text.
- **Affected component:** research_pipeline/arxiv/query_builder.py::build_api_url.
- **Observed:** The function interpolates the raw query into a URL. After normal
  requests preparation, R&D is split by &, C++ decodes plus signs as spaces,
  and # begins a URL fragment that excludes the following text/parameters from
  the HTTP target. All three fail input-to-decoded-query round-trip checks.
- **Scope:** The current email topic and minimal probes do not contain these
  reserved characters and pass the same checks. This defect does not explain
  their observed 429 responses or this audit's HTTPS timeout.
- **Improvement:** Encode the query parameters exactly once using a standard
  URL encoder or requests params; preserve the accepted arXiv query grammar,
  date filter, paging and sorting.
- **Verification:** Offline prepared URL parsing must preserve the full original
  query and all independent parameters for &, +, #, quotes and Unicode.
- **Status:** Recorded for a focused fix; no source-code change in this audit.
- **Evidence:** arxiv-request-construction-audit-20260914.json above.

### RP-015 follow-up — 429 probe diagnostics omit unread response information

- SourceSession raises SourceCooldown on 429 before _probe_one reads the body.
  _cooldown_result closes the attached response without inspecting its body.
- Consequently response_bytes=0 in the 07:04 probe means zero bytes inspected,
  not evidence that arXiv sent an empty response. The earlier 05:36 check
  inspected 14 bytes from an arXiv 429 response.
- The probe report does not preserve allowlisted content type, server/cache
  headers or a safe response fingerprint on this branch. Existing source_http
  logging retains status/content type/retry timing but cannot locate the cause.
- Improvement: retain bounded, credential-safe response diagnostics while
  preserving cooldown behavior and avoiding extra requests; distinguish
  not-read, inspected-empty and truncated bodies. Raw headers, cookies,
  credentials, client IPs and unrestricted error bodies must not be persisted.
- Verification: synthetic 429 fixtures with a nonempty body retain accurate
  inspection metadata and persist the same cooldown; all tests stay offline.
- **Status:** Existing RP-015 coverage gap remains partially open. This audit
  captured no HTTPS response body because the single request timed out.

Diagnostic bookkeeping note: the one-off protocol probe initially marked
request_sent only when its response hook ran. Its JSON now correctly records
the HTTPS timeout as request_attempted=true, received_http_response=false,
using the production probe's documented request_sent semantics. A correction
entry was added; the original execution log was not altered.


## arXiv long-timeout verification and browser-fallback policy — 2026-09-14T07:32:57Z

The owner requested another low-frequency API check and asked whether browser
interaction could replace the failing API while respecting arXiv policy.

### Live result

- Exactly one anonymous HTTPS GET was attempted at 07:32:56.958833 UTC from
  the Raspberry Pi's existing route and existing arxiv request budget.
  The previous attempt was at 07:23:25 UTC; prior cooldown had expired.
- The endpoint was https://export.arxiv.org/api/query with the official minimal
  query all:electron, start=0, max_results=1. Read timeout was 60 seconds,
  connect timeout 10 seconds, with no retries and no automatic redirects.
- The response arrived in 0.382 seconds: HTTP 429, 14 bytes of text/html,
  error text "Rate exceeded.", Server: Google Frontend.
- Via listed Google and Varnish intermediaries; X-Cache was MISS, MISS, MISS.
  These headers do not identify which quota, customer, address or server
  generated the restriction. They must not be treated as proof of an IP ban.
- No Retry-After was provided. Existing local policy saved a fallback cooldown
  until 07:47:57.337765 UTC. This is not a server-provided recovery estimate.
- This observation rules out the 15-second read timeout and downstream parsing
  as causes of this specific failure. It does not prove an arXiv-wide outage.
  The official status page still reported main site, search and export as up.
- All further arXiv requests stopped. No automated webpage search, browser
  impersonation, challenge bypass, identity or routing change was performed.

Evidence:
[Single-request result](01-email-conversation-structure/execution/arxiv-api-long-timeout-check-20260914T073256Z.json).

### Browser fallback decision

The general-agent rules in [arXiv robots.txt](https://arxiv.org/robots.txt)
explicitly disallow /search while allowing /abs, /pdf and /html, with a
15-second crawl delay. The [robot guidance](https://info.arxiv.org/help/robots.html)
says the exclusion file identifies paths off limits to robots and directs
requests for exceptions to arXiv administrators. Browser-driven automation
still constitutes automated access; slower clicks do not create permission.

Therefore no automated homepage/search-result scraping fallback was built.
This follows the owner's instruction to respect website policy. A browser
search automation exception would need permission from arXiv itself.

A viable design is to separate discovery from content acquisition:
use the existing OpenAlex source or owner-supplied paper IDs/links to discover
specific works, then fetch only permitted known-paper content with shared
pacing, caching and cooldowns. Direct public HTTP retrieval is sufficient for
those static resources; browser automation is optional only if needed and
permitted. No current cooldown should be bypassed by changing host or client.
For systematic harvesting, arXiv's bulk-access guidance favors export and
dedicated bulk mechanisms; robots allow rules are not unlimited-download permission.

OpenAlex documents arXiv among its repository locations and exposes
landing_page_url, pdf_url and version in locations. Coverage and version
identity must be verified; discovery through another index does not guarantee
complete arXiv coverage or availability of every full-text link.

References:
- [arXiv API terms](https://info.arxiv.org/help/api/tou.html)
- [arXiv status](https://status.arxiv.org/)
- [arXiv bulk access](https://info.arxiv.org/help/bulk_data.html)
- [OpenAlex API](https://help.openalex.org/api/)
- [OpenAlex locations](https://help.openalex.org/data/locations/)
- [OpenAlex repositories](https://help.openalex.org/data/sources/repositories/)
