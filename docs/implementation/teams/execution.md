# Teams A1 execution record

## Scope and baseline

The selected production scope is delegated T1 chats and complete T2
teams/channels. T3, T4, T5, and application-only production profiles are not
selected. No Teams production implementation has started at this checkpoint.

- Integration branch: `program/a1-teams-spider`.
- Starting commit: `7b9a7572b935f0e6ce6a96057b55951190afc8bf`.
- Authoritative design: `46ff93e0e3cd3122743b6048526ebdbd88ea3252`.
- Historical A1 baseline: `9e072eed17672f8380c709a9932ea56dbcbaff85`.
- Actual `master` at entry: `765d3c67c707257514d882310873f8a89f3d866b`.
  This already contains unrelated work. This program must preserve it.

The integration worktree was clean at entry. The coordinator read the complete
Teams design, implementation plan, repository instructions, and relevant
framework source before making changes.

## Local qualification

The isolated worktree environment was installed with
`uv sync --locked --group dev`. Two runtime checks confirmed:

| Component | Actual runtime |
| --- | --- |
| Python | 3.13.5 |
| Architecture | aarch64 |
| Scrapy | 2.19.0 |
| MSAL | 1.39.0, from the locked project dependencies |

The existing Graph, evidence-link, source-identity, and Contacts-ordering
regression selection passed: **298 tests**, 44.33 seconds. This is a baseline
framework result, not a Teams implementation qualification.

Native Scrapy source confirms that `CONCURRENT_ITEMS` controls callback-output
processing concurrency and that `scrapy check` normally disables pipelines.
Pipeline persistence therefore requires actual crawl tests in addition to
contracts. The existing provider fingerprinter includes `Accept` and `Prefer`;
the application fingerprinter also includes source/catalog context.

## P0 worker program

The dedicated [ChatGPT Project](https://chatgpt.com/g/g-p-6ac105579cbc8191a64f6c31fc7bc5ae-msgloom-teams-a1-20261003/project)
contains separate P0 lane conversations. Each send explicitly selects
`gpt-5-6-thinking` and `max`. The coordinator must also verify the returned
transcript metadata before accepting a verdict.

P0-A through P0-E received finite, read-only contracts and an archive of 124
tracked baseline files with a SHA-256 inventory. No production code is
permitted before A-D convergence and the independent P0-E closure PASS.

The initial dispatch failed before posting. An authenticated Project read
confirmed zero conversations. Recovery uses the installed workflow's
`RP_NEWCHAT_FAST=1` browser-first send path. It avoids an unrelated HTTP
history-list prerequisite. It does not solve or bypass a security challenge.
A later auth-lane composer failure occurred before posting. The shared browser
cooldown also refused two recovery attempts before they opened a tab. A bounded
external script made one retry after that cooldown expired. The cooldown
applies before browser selection; explicitly selecting the dedicated browser
does not bypass it. Future sends select both `RP_NEWCHAT_FAST=1` and
`RP_BROWSER_CDP=http://127.0.0.1:9222`.

The first fresh coordinator accepted P0-D's harness-design deliverable after
checking the actual framework and the finished transcript's model/effort.
See [the fixture harness and 36-case map](p0-fixture-harness.md) and the accepted
[P0-E pre-review](p0-architecture-pre-review.md). Pre-review PASS is not closure
of the converged contracts. The corrected [P0-C API contract](p0-api-contract.md) is now accepted for
converged closure input. Its delta finding is resolved by the existing core
exclusion; notification semantics remain mandatory. The corrected
[P0-B auth contract](p0-auth-scope-contract.md) is also accepted for closure.
It preserves existing scope tests and adds the requirement to validate effective
Teams scopes before authentication. A remains in collection.
The B retry posted
successfully after the shared cooldown expired, with conversation ID
`6ac10eed-b518-83ec-9e67-a02983191572`. Its collector then exited on an uncaught
120-second read timeout. The coordinator adopted that conversation into a
bounded read-only collector with timeout recovery. The original dispatcher
has now exited. Its successor owns A collection without sending new prompts.

The framework worker's transcript remained at message 219 on an unfinished
Python tool call. Its first bounded finish request failed during browser page
navigation. A later HTTP adoption check confirmed the same 219 messages, so
that request did not post. The second same-conversation request also timed
out during page navigation. A new HTTP adoption check confirmed the unchanged
219-message transcript and its pinned model/effort. No continuation has posted.

The next coordinator ran the supported browser preflight. The dedicated
browser answered, but its page showed an incomplete Chat interface with no
matching composer, login prompt, or challenge. The history-list request returned
403 while other account reads answered. These are separate observed failures;
they do not establish an account-wide block. Host load was also high. A bounded,
read-only page-load diagnostic found a local routing defect: the installed
sender blocks the history-list URL prefix, which also blocks the individual
`/backend-api/conversations/{id}` read needed for a continuation. The diagnostic
recorded that exact read failing. Five routing probes reproduce the old defect
and verify a process-local correction that permits individual reads while
keeping the exact history-list rule. The installed sender, model/effort pins,
security checks, and cooldown remain in use; the shared skill is unchanged.

A third bounded finish request used this correction. It passed the normal
memory gate but again found no composer, with no visible challenge or login
prompt. The route correction alone has therefore not restored continuation.
A later HTTP read still shows the original unfinished 219-message transcript.
The bounded, read-only diagnostic recorded HTTP 200 for the individual
conversation with the corrected route. That response arrived after the
composer timeout and final page snapshot. The snapshot still showed no
composer, login prompt, or challenge. This proves the route permits the read;
it does not prove the page can finish loading within the current timeout.
The diagnostic obeyed the existing memory guard and cooldown. The same route
correction remains necessary for the later E closure follow-up until the
installed rule is repaired.

The original A turn has been stalled for more than two hours. One external
recovery driver uses the diagnostic evidence. It may send one fresh,
shorter A review only if the diagnostic confirms an absent composer without
a challenge, login prompt, or relevant authentication refusal; a new HTTP read
still finds the unchanged unfinished turn; and the account probe succeeds.
If any condition fails, it exits without sending. A ready composer instead
returns control to the coordinator for same-conversation recovery. The fresh
review retains the exact baseline archive and required model/effort, covers
four bounded cells, and writes separate result and transcript records. Nine
recovery-condition probes and eight result-validation probes passed. This
does not qualify P0-A or waive the later independent closure.

The first replacement driver exited before any send because its adoption read
timed out. The original collector then completed a newer HTTP read and still
found the unfinished 219-message turn. One bounded retry passed a fresh adoption
read and the account probe. After waiting under the normal browser memory
budget, it posted the replacement review in conversation
`6ac12b13-0a6c-83ec-9d75-0563b50c18c3`. Its bounded collector retains separate
records and verifies the final transcript pin. No verdict has been accepted.

The three first-tranche P1 contracts have 15 disjoint owned paths. Their finite
worker prompt template is prepared. No P1 worktree or worker has started.
Dispatch remains gated on accepted P0-A, exact P0-E closure, and a committed
P0 freeze. A prepared external closure collector rejects stale task IDs,
candidate mismatches, unfinished replies, wrong model/effort, missing review
cells, unverified hashes, and unresolved material findings in a PASS result.
Its local acceptance/rejection probes passed. It has not collected a closure
verdict and does not replace coordinator review.

A source audit found that the initial archive omitted the shared catalog
service, evidence-item protocol, application fingerprinter, and concrete
Contacts/To Do idle gates. The closure builder now includes those exact
committed implementations and their focused tests, alongside the previously
added scope tests. All 12 supplemental files are available at the candidate
commit. This supplies review evidence; it does not claim a closure verdict.

Worker prompts, replies, pin evidence, process records, and command logs are
kept in the ignored `.superpowers/teams-a1/` execution directory. Independent
closure reviews are not yet complete.

## Coordinator continuity

The initial externally configured coordinator reported `gpt-6-astra` with
`max` effort. This differs from the requested `high` setting. The session has
no in-place effort control. Fresh coordinator sessions must use
`codex-budgeted-manager` with `gpt-6-astra` and `high`.

The daily usage guard was critical at initial entry. The first fresh coordinator
started at `2026-10-03T14:13:32Z` with `gpt-6-astra` / `high`; its entry guard
check passed. No new Codex manager may start unless the guard permits it. A
bounded external supervisor is armed to start a
fresh coordinator from the durable ledger when work is actionable. It must not
resume this large context. The current coordinator must release ownership
before its 35-minute or 6,000,000-token rotation limit.

The first continuation corrected the implementation plan's coordinator budget,
shared-export ownership, live LSP gate, and obsolete `master` assumption. These
are execution corrections. The authoritative design remains unchanged.

## Acceptance state

| Gate | State |
| --- | --- |
| Runtime and baseline framework regression | PASS |
| P0 independent contract closure | Pending |
| P1 core provider implementation | Not started |
| P2 application integration and synthetic crawls | Not started |
| P3 complete gates and independent reviews | Not started |
| T1/T2 company live acceptance | BLOCKED |
| Notification-driven live acceptance | NOT EXERCISED |
| Optional profiles | Not selected |
| Merge to `master` | Not authorized by the current gate state |

The worktree has no configured Microsoft client ID, username, authority
override, token-cache override, or default MSAL cache. No approved work/school
tenant resources or administrator-consent evidence were supplied. This is the
precise current live-acceptance blocker. It does not block local implementation
or synthetic qualification. A personal Microsoft account cannot satisfy the
live gate.
