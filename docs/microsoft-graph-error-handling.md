# Microsoft Graph HTTP error handling

msgloom follows Microsoft Graph's documented HTTP error semantics while keeping
Scrapy component responsibilities intact.

## Component boundary

- Downloader Middleware handles only cross-cutting HTTP/provider protocol
  behavior: authentication, Microsoft retry/backoff rules, and request
  correlation IDs.
- The Spider handles Outlook acquisition semantics such as delta reset and
  terminal Full-profile surfaces.
- Item Pipelines persist raw HTTP evidence and semantic/catalog state.
- A thin PrivacySafeRetryMiddleware subclass remains responsible for
  ordinary transient HTTP failures that need no Microsoft-specific policy. It
  preserves Scrapy 2.19 RetryMiddleware behavior and native retry/* stats,
  but suppresses helper log messages that would include full Request URLs.

## Status handling

| HTTP | Microsoft Graph meaning | msgloom V1 action |
| --- | --- | --- |
| 400 | Bad Request | No provider retry. Spider errback records failure. |
| 401 | Unauthorized | Auth middleware refreshes/retries once; a second 401 is returned to Spider. |
| 402 | Payment Required | No automatic retry. |
| 403 | Forbidden / possible insufficient_claims | No automatic retry. Full surface may become terminal `unauthorized`. |
| 404 | Not Found | No automatic retry. Full surface may become terminal `unavailable`. |
| 405 | Method Not Allowed | No automatic retry. Full surface may become terminal `unsupported`. |
| 406 | Not Acceptable | No automatic retry; request/representation error. |
| 409 | Conflict | Retry only when Graph error codes contain `Directory_ConcurrencyViolation`; otherwise Spider handles it. |
| 410 | Gone | No generic middleware retry. Message-delta Spider may reset that folder's delta once; other surfaces may become `unavailable`. |
| 411 | Length Required | No automatic retry. |
| 412 | Precondition Failed | No automatic retry. |
| 413 | Request Entity Too Large | No automatic retry. |
| 415 | Unsupported Media Type | No automatic retry. |
| 416 | Requested Range Not Satisfiable | No automatic retry. |
| 422 | Unprocessable Entity | No automatic retry. |
| 423 | Locked | No automatic retry without API-specific guidance. |
| 429 | Too Many Requests | Graph error middleware honors `Retry-After`; otherwise bounded exponential backoff. |
| 500 | Internal Server Error | Scrapy-compatible privacy-safe RetryMiddleware. |
| 501 | Not Implemented | No automatic retry. |
| 503 | Service Unavailable | Graph error middleware uses `Retry-After`/backoff and sends retry with `Connection: close`. |
| 504 | Gateway Timeout | Scrapy-compatible privacy-safe RetryMiddleware. |
| 507 | Insufficient Storage | No automatic retry. |
| 509 | Bandwidth Limit Exceeded | Graph error middleware uses `Retry-After` when present, otherwise bounded exponential backoff. |

Scrapy also retries 408, 502, 522 and 524 through the same privacy-safe
subclass. Retry construction, priorities, metadata, and retry/* counters still
come from Scrapy's get_retry_request() helper.

## Graph error bodies

Microsoft Graph error JSON contains a machine-readable `error.code` and may
contain recursively nested `innerError` / `innererror` codes. msgloom does not
make control-flow decisions from the human-readable `message`; it walks nested
codes and uses the most specific code it understands.

## Correlation IDs and logging

MicrosoftGraphDiagnosticsMiddleware assigns a new client-request-id GUID to
every Graph HTTP attempt. It counts requests, responses, statuses, purposes,
missing server request IDs, and transport exceptions, while DEBUG logs contain
only bounded purpose/status/type data plus correlation IDs. It never logs the
Graph URL or payload.

The diagnostics middleware runs after authentication on the request path and
before authentication on the response path. A 401 that becomes an auth retry
is therefore still visible in transport stats.

MessageIngestLogFormatter keeps Scrapy's standard logging system but prevents
raw HTTP bodies, Outlook subjects/body previews, opaque delta URLs, and
arbitrary exception text from being printed in normal Scrapy
item/crawl/error log messages.

Scrapy's generic retry helper normally includes the full Request repr in retry
and give-up logs. PrivacySafeRetryMiddleware routes those helper messages to a
non-propagating logger and emits bounded purpose/reason/count replacements.
Provider-specific retry middleware uses the same safe helper logger. Final
exhausted failures still reach the Spider errback and evidence pipeline.
