# Scrapy-native architecture review

This review targets the exact Scrapy version used by msgloom: **Scrapy 2.19.0**.
The local Scrapy `master` branch is not treated as the runtime API contract.

## Architectural rule

msgloom does not run a workflow engine outside Scrapy. A crawl begins with a
run intent and starting state; after that, the Outlook spider expresses work as
Scrapy Requests and Items and the Scrapy engine owns the asynchronous loop.

The normal flow is:

Spider -> Engine -> Scheduler -> Downloader middleware -> Downloader ->
Downloader middleware -> Spider -> Requests/Items -> Scheduler/Item Pipeline.

## Spider

### Purpose in Scrapy

A Spider defines which requests are sent and how responses are interpreted into
Items and additional Requests.

### msgloom usage

`OutlookMailSpider` owns Microsoft Outlook mail traversal:

- whole-mailbox discovery and paging;
- folder-tree traversal;
- per-folder message delta traversal;
- whole-mailbox reconciliation for Graph folder-coverage gaps;
- targeted detail/MIME/attachment enrichment;
- translation from Graph continuation links and resource relationships into
  new Scrapy Requests.

The Spider does **not** authenticate, throttle HTTP, persist raw HTTP evidence,
or write SQL/JSONL storage directly.

### `start()`

Scrapy 2.19 requires `Spider.start()` to be an asynchronous generator. msgloom
uses it to express the starting Requests for one run intent:

- discovery;
- delta;
- targeted full enrichment.

For delta runs, `start()` also asynchronously loads committed per-folder delta
links before emitting the first folder-inventory Request. Database IO is moved
off the reactor thread.

### Spider arguments

Scrapy documents spider arguments as strings. msgloom parses `page_size`,
`max_pages`, `sync_mode`, `message_ids`, and reconciliation options explicitly.
They are run-specific inputs, not Scrapy global settings.

### `cb_kwargs` versus `Request.meta`

Scrapy explicitly recommends `cb_kwargs` for data passed from one Spider
callback to another. msgloom therefore uses `cb_kwargs` for domain callback
state such as:

- `message_id`;
- `attachment_id`;
- `folder_id`;
- `parent_folder_id`;
- `page_number`;
- logical request purpose.

`Request.meta` is reserved for Scrapy/component state and request-specific
framework instructions, for example:

- `dont_cache`;
- `verbatim_url`;
- raw-evidence provenance IDs;
- msgloom middleware run/purpose context;
- retry/authentication middleware state.

This avoids accidentally carrying Scrapy internal metadata such as retry state
into unrelated follow-up Requests.

### Stateful traversal

The Spider keeps a small amount of crawl-graph state for folder inventory
(`seen folders`, pending folder-list callbacks, inventory completion/failure).
This remains in the Spider because it is provider traversal state and Scrapy has
no built-in request-subgraph join primitive. Moving it to an Extension would
move source traversal out of the Spider, which would be less aligned with
Scrapy's component model.

This state is currently **not** claimed to survive JOBDIR pause/resume. That is
a separate remaining task.

## Requests and Scheduler

All provider continuation work is represented as Scrapy Requests and therefore
passes through Scrapy's normal Scheduler and duplicate filtering.

Graph-provided `@odata.nextLink` and `@odata.deltaLink` values are treated as
opaque and are followed verbatim.

`URLLENGTH_LIMIT = 0` is intentional. Scrapy's default 2083-character web URL
safety limit is unsuitable for opaque Graph continuation URLs.

No custom Scheduler or DupeFilter exists today.

## Downloader middleware

Scrapy downloader middleware is the low-level request/response hook layer. The
custom middleware stack contains only HTTP-level cross-cutting concerns.

### Microsoft Graph authentication

Authentication middleware only handles delegated authentication:

- MSAL token acquisition/cache;
- Bearer injection for `graph.microsoft.com`;
- cached account selection;
- one 401 forced-refresh replacement Request;
- removal of Authorization before Scrapy HTTP cache persistence.

Device-code and interactive-browser authentication are separate selectable
middleware classes.

### Raw network evidence

`RawNetworkEvidenceMiddleware` runs at downloader-middleware priority **975**.
On the response path it therefore sees an actual downloaded Graph Response
before authentication, HTTP cache, redirect/compression, throttling, retry, or
Spider handling can consume/transform it.

It synchronously enforces a durability barrier from Scrapy's point of view:
its coroutine does not return the Response until raw body storage and the
SQLAlchemy evidence row have completed. Blocking filesystem/SQLite work itself
runs in a worker thread.

This records the Scrapy download-handler Response representation, not TCP/TLS
wire framing. In particular, content encoding has not yet been decoded by
`HttpCompressionMiddleware` at this point.

### HTTP-cache evidence linkage

`CachedEvidenceLinkMiddleware` runs at priority **875**, after Scrapy's
`HttpCacheMiddleware` on the response path. A cache hit is linked to the
existing durable evidence instead of being falsely recorded as a new provider
network retrieval. Legacy cache entries with no catalog evidence are recovered
as evidence with origin `http_cache`.

### Microsoft Graph throttling

`MicrosoftGraphThrottleMiddleware` runs at priority **555**, immediately before
Scrapy's built-in RetryMiddleware on the response path.

It owns only Graph-specific semantics:

- recognize HTTP 429;
- honor `Retry-After` (seconds or HTTP-date);
- use bounded backoff when it is missing.

It delegates retry mechanics to Scrapy's public `get_retry_request()` helper,
so Scrapy owns retry count, duplicate-filter bypass, priority adjustment, and
retry statistics. When the Graph retry budget is exhausted it prevents the
built-in generic RetryMiddleware from creating a second retry loop.

## HTTP cache

Scrapy's native HTTP cache remains enabled for development. It is not used as a
business evidence store.

Delta, folder-inventory, and reconciliation Requests set `dont_cache=True`
because replaying an old delta response would freeze incremental synchronization
in the past.

A future explicit Refresh intent must also bypass HTTP cache. Enrich may use a
previous representation when that is explicitly acceptable to the requested
completeness policy.

## Item types

Scrapy 2.19 officially supports dataclasses as Items through itemadapter.
msgloom uses dataclass Items for Outlook semantic observations and checkpoint
candidates.

Raw HTTP Responses are deliberately **not** Items. Scrapy processes callback
outputs in parallel (`CONCURRENT_ITEMS`, default 100), so yielding a raw Item
before a semantic Item would not establish a durability ordering guarantee.

## Item Pipeline

Scrapy Item Pipelines are for processing/validating/persisting Items, not for
controlling crawl progression.

msgloom uses two sequential pipeline components:

1. `CatalogPipeline` (priority 300) persists queryable identity/state through
   SQLAlchemy.
2. `LocalJsonlPipeline` (priority 400) keeps append-only semantic logs for
   inspection/recovery.

Both use coroutine `process_item()` methods for blocking local IO. SQLite and
JSONL writes run in worker threads and are serialized with async locks rather
than blocking the Scrapy reactor.

The JSONL pipeline is intentionally not a generic feed export. Its role is an
append-only local semantic audit stream with specific per-item-type files and
private permissions, while SQLAlchemy is the query/state store.

## SQLAlchemy catalog service

`CatalogService` is a crawler-scoped Scrapy Extension (priority 100). It owns:

- one SQLAlchemy Engine per Crawler;
- one shared async SQLite write lock;
- database lifecycle through `spider_closed`.

Raw Evidence Middleware, CatalogPipeline, and checkpoint logic share this
service. This is necessary for SQLite's single-writer behavior; an earlier
prototype with one Engine per component produced real `database is locked`
errors under Scrapy's concurrent Item processing.

Application code does not call `sqlite3` directly.

## Checkpoint Extension and signals

`OutlookDeltaCheckpointExtension` uses Scrapy's `spider_idle` signal. Scrapy
2.19 explicitly documents `spider_idle` as the place to assess final crawl
results and optionally provide a custom closing reason.

At `spider_idle`, Scrapy has no pending/scheduled downloads and no Items still
being processed. The extension commits delta candidates only when:

- folder inventory completed;
- reconciliation completed;
- every started folder delta completed;
- the durable candidate count matches the completed folder count;
- no acquisition/spider exception occurred;
- no Item Pipeline error/drop occurred.

Candidates are committed in one SQLAlchemy transaction. Otherwise the previous
committed delta state remains authoritative.

## Stats

msgloom uses Scrapy's built-in Stats Collector. It does not create a parallel
run-statistics framework.

Components add namespaced keys:

- `msgloom/crawl/*` from the Spider;
- `msgloom/auth/*` from authentication middleware;
- `msgloom/evidence/*` from evidence middleware;
- `msgloom/throttle/*` from throttling middleware;
- `msgloom/catalog/*` and `msgloom/storage/*` from pipelines;
- `msgloom/checkpoint/*` / `msgloom/persistence/*` from checkpoint lifecycle.

Scrapy's native downloader/cache/retry/item/finish stats remain authoritative
for framework behavior.

## Scrapy defaults intentionally disabled

These Scrapy web-crawling/debug defaults do not fit this authenticated API
collector and are disabled:

- cookies;
- Referer middleware;
- URL length limit;
- Telnet console;
- Remote Control.

Robots.txt obedience is also disabled because Microsoft Graph is an
authenticated API, not a website being crawled.

Depth tracking remains enabled; its default depth limit is unlimited and its
stats remain useful.

## JOBDIR

Scrapy JOBDIR remains execution-resume state for one crawl only. It is not used
as Microsoft Graph business checkpoint state.

Current delta business checkpoints are SQLAlchemy rows and survive independent
crawl runs. Clean pause/resume through JOBDIR has **not yet been validated** for
all in-memory Spider traversal state and is a remaining task before claiming
pause/resume support.

## Remaining Scrapy-native work

1. Validate JOBDIR pause/resume and decide which Spider crawl-graph fields must
   use `Spider.state` when JOBDIR is enabled.
2. Define explicit Refresh behavior that bypasses HTTP cache.
3. Review request fingerprints when representation-affecting headers can create
   two legitimate representations at the same URL.
4. Use Request priorities when user-triggered enrichment and background work
   coexist in the same crawl.
5. Revisit shared provider settings once a second Graph Spider (Calendar) is
   introduced; avoid abstracting before real reuse exists.
