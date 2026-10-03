# P0-E architecture pre-review

**Verdict:** PASS for the parallel pre-review only.
**Closure:** pending exact converged P0-A-D input; P1 remains gated.
**Input commit:** `7b9a7572b935f0e6ce6a96057b55951190afc8bf`.
**Task:** `MSGLOOM_TEAMS_A1_P0-E_20261003_R1`.

The independent [ChatGPT reviewer](https://chatgpt.com/c/6ac1079d-559c-83ec-a23c-b55854f56909)
verified all 124 inventoried archive members against their SHA-256 hashes.
The finished transcript records `gpt-5-6-thinking` / `max` for all four visible
assistant replies. The reviewer returned no blocker, major, or minor findings.
The original JSON and transcript remain in the durable program workspace.

## Ownership and reuse

Provider scopes, v1.0 paths, projections, query helpers, pure parsers, dataclasses,
and request specifications belong in `microsoft_graph/`. Application response
callbacks, traversal, source/run semantics, and persistence belong in
`message_ingest/`.

Reuse the existing Graph request builders, MSAL session, Downloader middleware,
fingerprinting, privacy components, and integrity extension. A provider
collection callback must not consume the response before the application emits
its evidence. Compose narrow provider helpers with the application Graph spider.
No second transport, scheduler, auth flow, or generic workflow layer is justified.

## Evidence and source identity

Callbacks yield raw evidence before calling pure parsers. Pipelines retain the
200/250/300 order and `CONCURRENT_ITEMS=1`. Raw persistence awaits file and SQL
writes; evidence linking checks committed evidence before semantic persistence.
The shared catalog lock protects cross-response writes.

Scrapy 2.19 can prefetch callback output. These rules establish yield-before-parse
and durable-evidence-before-dependent-semantic-storage. They do not establish
durable-write-before-parser-execution. The coordinator verified this distinction
in the installed scraper and asyncio helper, and with a native-helper probe.
The [fixture contract](p0-fixture-harness.md) includes the corrected assertion.

T1 and T2 must share one delegated Teams source and the existing hashed MSAL
home-account binding. Existing binding mismatches and ambiguous legacy bootstrap
fail closed. Auth remains scoped to the Graph host and HTTPS. Shared live MSAL
cache paths require serial crawls. Application-only identity remains out of scope.

## Lifecycle and JOBDIR

Every Teams application spider must retain the application
`MicrosoftGraphSpider` inheritance and named errback. Reuse the existing
`spider_error`, `item_error`, and `item_dropped` integrity signals.

Initial discovery stores observations and must not infer deletion from absence.
Reject JOBDIR before requests unless a later real pause/resume qualification
explicitly enables it. Any future checkpoint or promotion requires native idle,
a clean run, a free shared write lock, and durable resource completion proof.

## Coordinator acceptance and remaining gate

The coordinator inspected the current application Graph spider, evidence/link
pipelines, integrity extension, source-identity service, auth middleware, catalog
service, and installed Scrapy output-processing source. These support the four
reviewed architecture cells. No production changes have been made since the
review input. Documentation changes do not alter that framework input.

This pre-review does not verify future Teams code or cancellation safety of
future writes. P2/P3 must test those behaviors. The P0-B/C deliverables remain the
owners of the exact permission/API freeze. After A-D converge, the independent
reviewer must receive their exact corrected content, the exact framework input,
and the execution-plan corrections for a new bounded closure verdict.
