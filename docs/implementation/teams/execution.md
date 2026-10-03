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
exclusion; notification semantics remain mandatory. A/B remain in collection.
The B retry posted
successfully after the shared cooldown expired, with conversation ID
`6ac10eed-b518-83ec-9e67-a02983191572`. Its collector then exited on an uncaught
120-second read timeout. The coordinator adopted that conversation into a
bounded read-only collector with timeout recovery. The original dispatcher
still owns A collection. Do not duplicate these sends.

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
