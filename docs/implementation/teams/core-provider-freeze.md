# Core Teams provider contract freeze

**Validated code candidate:** `5f64bb78b84069a8854ea651f7029a00d5540d2d`.
**Date:** 2026-10-04 UTC.
**Scope:** delegated T1 chats and complete T2 teams/channels only.

All five core P1 lanes are accepted. The provider package contains pure
message/content models, scoped opaque identities, chat and channel topology,
and request composition helpers. Application callbacks remain outside the
provider package. Existing Scrapy 2.19.0 transport, MSAL, continuation,
fingerprint, retry, privacy, and error components remain the owners of those
responsibilities. The P0 API and permission contract remains unchanged.

## Composition acceptance

| Lane | Worker commit | Integrated commit |
| --- | --- | --- |
| Chat composition | `872890c0b0476751fb2bf5dd2ab9216ffe8f6bcd` | `c768e498eabaeb6afd10ea6135a9f35ea989b578` |
| Channel composition | `eddb0e126e5c2d8e44fadd6dc1e5113e1fac928d` | `a1809153f41d18baf145a98040bc4f52825e2ba1` |
| Channel validation correction | `79d20db11c9a19f9f26abb63439f58fc20136ed2` | `5f64bb78b84069a8854ea651f7029a00d5540d2d` |

The coordinator verified exact parents, prompt hashes, owned paths, finished
`gpt-5-6-thinking` / `max` transcript metadata, code, and tests. Chat composition
passed 14 tests. Channel composition passed 10 original tests. The coordinator
added 13 collection-boundary cases. Before the correction, 11 failed because
empty iteration bypassed scope and value-list validation. After the correction,
all 23 channel composition and validation cases passed.

## Combined gate

- All 458 affected Teams, Graph, evidence, integrity, and source-identity tests
  passed in 31.50 seconds.
- Ruff check and format check passed for all core provider and Teams test files.
- Pyright reported zero errors, warnings, or information messages.
- AST checks found no forbidden application/persistence/transport imports in
  Teams provider modules, no Python assertions, and no module of 500 lines or
  more among the changed core files.
- Changed-file pre-commit and diff checks passed for the composition correction.

Runtime evidence and exact commands are retained in
`.superpowers/teams-a1/core-provider-validation.json` and its referenced logs.

## Downstream contract

P2 persistence may now start from the committed freeze. It must use the provider
models and preserve canonical raw evidence, scoped identity, observed versions,
explicit deletion, topology paths, and history uncertainty. Shared package
exports and catalog registration remain coordinator-owned. Chat/channel spider
writers wait for the persistence item contract. Saved-source implementation
waits for the schema contract. Optional profiles remain unselected.

This freeze does not claim application, full repository, compatibility, live
LSP, independent P3 review, or company-account acceptance. Those gates remain
required. No merge to `master` is permitted by this freeze.
