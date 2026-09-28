# Scrapy 2.19 architecture audit: Outlook mail acquisition

This document audits msgloom's Outlook mail collector against Scrapy 2.19.0's
component model and lifecycle. The local Scrapy 2.19.0 tag is the normative
reference for this project; behavior from Scrapy `master` is not assumed.

## Architectural rule

Scrapy is the workflow engine. msgloom does not wrap it in a second acquisition
engine.

The expected data flow remains:

1. Spider yields Requests and Items.
2. Engine sends Requests through Scheduler and Downloader Middleware.
3. Downloader returns Responses through Downloader Middleware.
4. Spider callbacks parse Responses and yield more Requests or Items.
5. Item Pipelines process structured state.
6. Extensions observe lifecycle events such as `spider_idle`.

Provider traversal decisions remain in the Spider. HTTP concerns remain in
Downloader Middleware. Durable semantic state remains in the Item Pipeline.
Lifecycle-wide validation and checkpoint commit remain in an Extension.

## Component review

### Spiders — discovery, delta, and Full acquisition

Scrapy purpose: parse responses, extract structured data, and generate follow-up
requests.

Verdict: correct component, after refactoring.

Changes made during this audit:

- Split the acquisition modes into `OutlookDiscoverSpider`, `OutlookDeltaSpider`,
  and `OutlookFullSpider`, with an abstract `OutlookMailSpider` base. They use
  normal `scrapy.Spider` traversal; generic web spiders do not match Graph APIs.
- Folder and attachment traversal use small abstract helpers with bound callbacks.
  Each Spider module stays below 500 lines without changing request persistence.
- Kept `async def start()`, which is the Scrapy 2.19 start API.
- Business callback arguments (`message_id`, `attachment_id`, `folder_id`,
  `page_number`, `purpose`) now use `Request.cb_kwargs`, as Scrapy recommends.
- `Request.meta` is reserved for Scrapy/component behavior and cross-cutting
  request metadata such as `dont_cache`, `verbatim_url`, evidence identity,
  run identity, authentication and retry state.
- Reconciliation is streaming. It no longer accumulates the whole mailbox
  index in a Spider dictionary before producing follow-up requests.
- Folder traversal state remains in the Spider because Scrapy does not provide
  a native request-subgraph join primitive. This is provider traversal state,
  not a replacement workflow engine.
- Folder traversal execution state is mirrored into `Spider.state` so Scrapy
  `JOBDIR` can pause and resume a crawl correctly.

### Requests, Responses, Scheduler and DupeFilter

Scrapy purpose: Requests describe work; Scheduler queues Requests and the
DupeFilter identifies duplicate work from request fingerprints.

Verdict: native components retained.

Changes made:

- Opaque Graph `@odata.nextLink` and `@odata.deltaLink` values are reused as
  complete URLs rather than reconstructed.
- `verbatim_url=True` is retained for opaque continuation URLs where URL
  canonicalization must not change identity.
- `URLLENGTH_LIMIT=0` is intentional because Graph continuation and delta URLs
  are opaque and may exceed Scrapy's generic 2083-character safety limit.
- Added `RepresentationAwareRequestFingerprinter`. Scrapy's default fingerprint
  ignores headers, but Graph `Accept` and `Prefer` can change the returned
  representation. Graph request identity therefore includes those two headers.
- `Authorization` is intentionally excluded from the fingerprint, so token
  rotation does not create a new request identity.

### Downloader Middleware — authentication

Scrapy purpose: low-level request/response processing between Engine and
Downloader.

Verdict: correct component.

Current components:

- `MicrosoftGraphAuthSession` owns one crawler MSAL cache, account pin and token;
- device-code/interactive downloader middleware are selectable thin adapters;
- `MicrosoftGraphSourceIdentityExtension` verifies persisted source identity
  before Scheduler requests execute.

Account selection and token acquisition therefore remain provider
authentication concerns, while provider-independent source binding lives in
`message_ingest/acquisition/source_identity.py`. The downloader boundary still
owns Bearer injection/removal and the one authentication-specific 401 retry.

### Downloader Middleware — Microsoft Graph throttling

Scrapy purpose: HTTP-level cross-cutting behavior.

Verdict: correct component, with Scrapy retry mechanics reused.

`MicrosoftGraphThrottleMiddleware` handles provider-specific HTTP 429 semantics:

- respects `Retry-After`;
- uses bounded fallback backoff if it is absent;
- uses Scrapy's public `get_retry_request()` helper for request cloning,
  scheduling semantics and retry stats;
- maintains a Graph-throttle retry counter separate from Scrapy's generic
  `retry_times`, so 429 throttling does not consume the generic transport retry
  budget;
- lets Scrapy's ordinary RetryMiddleware continue handling its normal error
  classes and status codes.

### AutoThrottle

Scrapy purpose: adapt download-slot delay to observed latency and avoid request
bursts.

Verdict: enabled and complementary to Graph 429 handling.

The project keeps a hard per-domain concurrency cap of 2 and enables
AutoThrottle with target concurrency 1.0. Real mailbox testing with this
combination produced a clean 17/17 HTTP-200 delta round with zero 429s.
Provider `Retry-After` handling remains necessary for quota/throttling events
that latency-based pacing cannot predict.

### Raw HTTP evidence middleware

Scrapy has no built-in component whose purpose is immutable provider evidence
capture before Spider interpretation. Custom middleware is justified here.

The responsibility is split by middleware order:

- `RawNetworkEvidenceMiddleware` runs at response priority 975. A freshly
  downloaded Graph response is durably persisted before authentication
  response handling, HttpCache, decompression and Spider callbacks continue.
- `CachedEvidenceLinkMiddleware` runs after HttpCache on the response path and
  relinks a cache replay to the already-existing source evidence record.

Raw bytes are content-addressed on the filesystem. SQLAlchemy stores evidence
metadata and provenance. Request authorization headers are never stored.

A cache replay is not treated as a new Microsoft source observation. The
original evidence acquisition timestamp is propagated to semantic Items.

### HttpCacheMiddleware

Scrapy purpose: development/offline HTTP response caching.

Verdict: use native Scrapy cache, but default it off.

Scrapy's `DummyPolicy` does not expire cached responses. Leaving HttpCache on in
normal Outlook operation could silently return stale Discovery or Full data.
Therefore:

- msgloom production default: HTTP cache disabled;
- development/replay: explicitly enable `MSGLOOM_HTTP_CACHE_ENABLED=1`;
- delta, folder inventory and reconciliation requests always use
  `dont_cache=True` even when the development cache is enabled;
- retry/auth error status codes remain excluded from caching.

### Referer, Cookies, Telnet and Remote Control

- Cookies are disabled; bearer-token Graph API requests do not use cookie
  sessions.
- `RefererMiddleware` remains enabled with `REFERRER_POLICY="no-referrer"`.
  This prevents Referer headers while still allowing Scrapy RedirectMiddleware
  and MetaRefreshMiddleware to cooperate with the expected Referer component.
- Telnet Console is disabled.
- Scrapy 2.19 Remote Control is disabled because this collector does not need it
  and its job metadata includes control authentication material.

### Items

Scrapy purpose: structured data produced by Spiders and consumed by Pipelines
and Feed Exporters.

Verdict: dataclass Items are supported natively by Scrapy through ItemAdapter.

Raw HTTP response bodies are no longer represented as Spider Items. That was a
critical correction: Scrapy processes callback output in parallel up to
`CONCURRENT_ITEMS`, so yielding a raw-response Item before a semantic Item does
not create a durability ordering barrier.

Current Items represent Outlook domain observations, surface state, failures and
checkpoint candidates.

### Item Pipeline

Scrapy purpose: validation, transformation, deduplication and persistence of
Items after Spider extraction.

Verdict: one custom pipeline remains and has a single durable-state role.

`OutlookMailPipeline` writes the queryable SQLAlchemy catalog/state model. SQLite is
only a SQLAlchemy backend; application code does not use `sqlite3` directly.

The pipeline uses Scrapy's coroutine support. SQLite writes are moved to a
worker thread and serialized with the crawler-scoped catalog write lock, so the
asyncio reactor is not blocked and multiple Scrapy Items do not race multiple
SQLite writers.

### Media / Files Pipeline

Scrapy purpose: download file URLs attached to an Item, cache those files and
hold the Item at the pipeline stage until downloads complete.

Verdict: intentionally not used for Microsoft Graph attachments.

Outlook attachment acquisition is part of provider traversal, not a generic
file side effect:

- attachment collection pagination can create more acquisition Requests;
- fileAttachment, itemAttachment and referenceAttachment have different Graph
  behavior;
- itemAttachment needs both `$value` MIME and expanded item detail;
- referenceAttachment does not support the same raw endpoint;
- FilesPipeline URL-age caching conflicts with msgloom's source-observation
  history and content-addressed raw-evidence model.

The Spider therefore continues to schedule Graph attachment requests through the
normal Scrapy Scheduler/Downloader path.

### Extensions and signals

Scrapy purpose: functionality that does not belong to the request/item data
flow, usually driven by signals.

Verdict: checkpoint commit belongs in an Extension.

`OutlookDeltaCheckpointExtension` handles `spider_idle`. Scrapy 2.19 explicitly
recommends this signal for assessing final crawl results and changing the final
closing reason.

At `spider_idle` there are no scheduled/downloading requests and no Items still
being processed by pipelines. Only then can a complete delta round commit its
candidate deltaLinks.

### Stats

Scrapy purpose: cheap run observability.

Verdict: Stats are observability only, never correctness state.

During the audit, checkpoint correctness was removed from Stats. A resumed
JOBDIR does not guarantee prior-batch Stats, so checkpoint commit now compares:

- Spider execution state;
- durable SQLAlchemy checkpoint candidates.

`msgloom/*` stats remain useful for logs, monitoring and diagnostics.

### JOBDIR and Spider.state

Scrapy purpose: pause and resume one crawl job by persisting Scheduler,
DupeFilter and Spider execution state.

Verdict: supported, without confusing JOBDIR with business checkpoints.

`Spider.state` persists:

- delta run id;
- seen/started/completed folder ids;
- folder-inventory pending and completion state;
- reconciliation state;
- run failure state.

The Graph deltaLink remains durable business state in SQLAlchemy.

A real integration audit verified clean pause/resume:

1. A deliberately slowed real Graph delta crawl was interrupted once with
   SIGINT.
2. Scrapy closed with `finish_reason=shutdown`.
3. JOBDIR contained one scheduled reconciliation Request and a `spider.state`
   with the original run id and 12 completed folders.
4. No new checkpoint set was committed by the partial run.
5. Re-running with the same JOBDIR logged `Resuming crawl (1 requests
   scheduled)`.
6. The same run id was restored; no initial folder request was emitted.
7. Only reconciliation and orphan recovery ran.
8. The original 12 checkpoint candidates were then committed successfully.

## SQLAlchemy/SQLite catalog

SQLite is used as the local database backend through SQLAlchemy 2.x only.

One `CatalogService` Extension owns one SQLAlchemy Engine per Crawler and a
shared async write lock. RawEvidencePipeline, EvidenceLinkPipeline,
OutlookMailPipeline and checkpoint logic share that service. This replaced an
earlier design where separate
components created separate Engines, which real testing proved could produce
`database is locked` errors.

The current catalog contains:

- raw HTTP evidence metadata;
- message identity/latest state;
- message observations;
- message surface completeness;
- attachment catalog/latest metadata;
- folder catalog;
- committed delta checkpoints;
- per-run delta checkpoint candidates.

Raw message/MIME/attachment bytes remain on the filesystem, not in SQLite.

Old evidence cannot overwrite newer latest-state rows. Reprocessing the same
cached evidence does not create a fake new source observation.

## Components deliberately left native

No custom Scheduler, Downloader, DupeFilter, Spider Middleware, StatsCollector,
HttpCache storage/policy, RetryMiddleware or Download Handler is used.

That is intentional. Custom code exists only where Microsoft Graph semantics or
msgloom's evidence/checkpoint model requires behavior Scrapy does not provide
out of the box.

## Remaining audit/engineering items

The current component boundaries are now aligned with Scrapy 2.19. Remaining
work is feature/completeness work rather than replacing core Scrapy mechanics.
For V1 development the SQLite catalog is treated as a fresh database generated
from the current SQLAlchemy metadata. Historical-schema migration support is
explicitly deferred until the schema is stable enough to create a compatibility
burden.

- keep the V1 SQLAlchemy schema simple and recreate development databases when
  the schema changes;
- real delta mutation tests (create/update/move/delete);
- real attachment tests (file, inline, attached message, reference attachment);
- recursive nested itemAttachment traversal;
- extend the current versioned Full-v1 profile as new supported surfaces are
  added;
- Progressive Enrichment policy on top of the implemented Enrich versus Refresh
  semantics;
- request-priority policy once enrichment is automatic;
- explicit migration tooling before existing V1 tables require in-place schema changes.
