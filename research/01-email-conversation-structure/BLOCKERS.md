# Topic 01 execution blockers

**The research run stopped at the manifest search gate. No academic report exists.** Run ID: `101cf2285113`. The initial search and its one allowed retry produced empty candidate artifacts. Both CLI processes returned exit 0; the manifest's `non_empty` requirement failed. The execution agent recorded the failure and did not let the runner accept the empty file.

## Exact command and saved evidence

The installed runner requested this command for both attempts:

```bash
research-pipeline search --run-id 101cf2285113 --source all --config /home/grammy-jiang/Projects/msgloom/research/01-email-conversation-structure/config.run.toml
```

It was executed from `/home/grammy-jiang/Projects/msgloom/research/01-email-conversation-structure`. [Attempt 1 command record](execution/logs/search-01.command.json) and [attempt 2 command record](execution/logs/search-02.command.json) preserve argv, timestamps, cwd, and exit codes. [Search attempt records](execution/search_attempts.json) contain exact error lines. Complete stderr is preserved in [attempt 1](execution/logs/search-01.stderr.log) and [attempt 2](execution/logs/search-02.stderr.log).

The candidate file is 0 bytes. Both [first check](execution/checks/search-01.json) and [retry check](execution/checks/search-02.json) record `non_empty: false`, `candidate_count: 0`, and `accepted: false`. Original artifacts and state are preserved under `execution/snapshots/`.

## Source failures

| Source | Exact error or observed result | Consequence |
| --- | --- | --- |
| arXiv | `arXiv API returned 429 after 5 attempts. Try again later or reduce request frequency.` | First attempt produced no candidates. |
| arXiv retry | `HTTPSConnectionPool(host='export.arxiv.org', port=443): Read timed out. (read timeout=60)` | Final surfaced error. Individual retries include four HTTP 429 responses and one timeout. Preserve both the individual outcomes and final exception. |
| Scholar | `scholarly is not installed. Install with: pip install 'research-pipeline[scholar]'` | No usable Scholar search occurred. The missing dependency was not installed during this run. |
| Semantic Scholar | HTTP `429 Client Error` for the `email+thread` search request with `year=1987-2026` | Each invocation exhausted three attempts. |
| OpenAlex | HTTP `400 Client Error: Bad Request` with filter `from_publication_date:1987041200,to_publication_date:2026091400` | The installed connector passed malformed dates. The first invocation also encountered an intermediate 429. |
| DBLP | `Expecting value: line 1 column 1 (char 0)` | Each invocation exhausted three JSON-decoding attempts. No response metadata was parsed. |
| HuggingFace | `0 candidates after filtering (from 100 daily papers)` | A daily-feed zero match provides no basis to exclude foundational email work. |

## Smallest correction and recovery boundary

The reproducible implementation defect is the OpenAlex date-format boundary. The installed [search caller](/home/grammy-jiang/.local/share/pipx/venvs/research-pipeline/lib/python3.13/site-packages/research_pipeline/cli/cmd_search.py:176) obtains arXiv-format timestamps from `date_window`. The installed [OpenAlex connector](/home/grammy-jiang/.local/share/pipx/venvs/research-pipeline/lib/python3.13/site-packages/research_pipeline/sources/openalex_source.py:103) slices those values to ten characters, producing an invalid OpenAlex publication date.

The smallest correction is to convert the dates to `YYYY-MM-DD` at the OpenAlex call boundary. Keep arXiv's existing timestamp format for arXiv. A CLI/config option to disable or override OpenAlex's date filter was not found. This correction was **not applied**, because the initial supervisory RUN_PROMPT.md scoped execution to research artifacts and excluded shared implementation changes. This was a supervisory execution boundary, not a separately stated prohibition from the original user.

At least one academic source must return usable records before the search task can pass. Restored arXiv/Semantic Scholar access may enable a later resumed attempt, but rate-limit recovery has not been demonstrated. Missing Scholar dependencies and DBLP access/parsing problems are additional source limitations. No credentials, services, package installations, or shared infrastructure were changed.

The permitted run-local recovery used lower request frequency: arXiv minimum interval increased from 5 to 15 seconds and Semantic Scholar from 1 to 5 seconds. It still returned no candidates. The manifest retry limit is exhausted. The saved state should remain blocked until a real external correction or available-source change exists; it must not be reset repeatedly to create an appearance of progress.

## Runner and artifact checks

The installed [runner validator](/home/grammy-jiang/.agents/skills/research-pipeline/runners/runner.py:135) checks only whether the output path exists. It does not enforce the manifest's `non_empty` or JSON-schema validations for delegated MCP tasks. It also accepts delegated no-output verification stages on the next resume without inspecting their CLI exit status. This run saved real exit codes and performed the required checks before each resume.

A separate plan mismatch was corrected within the allowed artifact-optimization step: the CLI wrote `topic_raw` and `topic_normalized`, while the installed plan schema requires `topic`. The exact topic field was added, the original generated plan was preserved, and both schema validation and the declared six-check verify command passed. See [plan check](execution/checks/plan.json). This correction did not modify package code or weaken the schema.

## Inspected report integration issues, not executed failures

The report stage was never reached. Inspection found three issues that must be resolved or given an explicit compatible staging contract before a future final report can be accepted:

1. [SKILL.md](/home/grammy-jiang/.agents/skills/research-pipeline/SKILL.md) Rule 5 says: “Write `./<topic-slug>-research-report.md` only after `validate-report` is `accepted`.” The installed manifest requires that same path as the `report` output before `validate-report` becomes ready. No final-path report was written in this run.
2. The declared report CLI does not specify an output path. Its [default output](/home/grammy-jiang/.local/share/pipx/venvs/research-pipeline/lib/python3.13/site-packages/research_pipeline/cli/cmd_report.py:120) is inside `summarize/`, while the manifest expects the cwd slug path. A coherent staging contract should render and validate a candidate first, then publish the final path after acceptance.
3. The [report renderer input](/home/grammy-jiang/.local/share/pipx/venvs/research-pipeline/lib/python3.13/site-packages/research_pipeline/cli/cmd_report.py:83) is the deterministic `summarize/synthesis_report.json` or legacy file. The delegated synthesizer writes `analysis/synthesis.json`. A future integration must make the candidate report faithfully use the independently reviewed evidence. That integration was not attempted or fabricated.

These inspected inconsistencies are distinct from the actual stopping failure: no valid nonempty search corpus. The original user authorized real research and later requested an issue record for future Skill improvement. The supervising RUN_PROMPT.md scoped this run to research artifacts. The preserved artifacts support a later resumed run after the smallest necessary correction is made through the later Skill-improvement work or another explicitly scoped recovery change.
