# Outlook mail delta synchronization

msgloom uses two complementary Microsoft Graph paths for Outlook mail:

1. per-folder message delta for efficient incremental change tracking;
2. a lightweight whole-mailbox reconciliation pass for coverage gaps that
   cannot be represented by the enumerable mail-folder hierarchy.

## Why per-folder delta

Microsoft Graph message delta is a folder-scoped operation. Each enumerable
mail folder therefore has its own opaque `@odata.deltaLink` checkpoint.

A delta run:

1. enumerates top-level mail folders with `includeHiddenFolders=true`;
2. traverses child folders only when `childFolderCount > 0`;
3. starts or resumes message delta independently for every unique folder;
4. follows every `@odata.nextLink` verbatim;
5. treats the final `@odata.deltaLink` as a checkpoint candidate;
6. performs whole-mailbox reconciliation;
7. commits all candidates only after Scrapy becomes idle and the complete round
   is known to be safe.

Folder inventory, message delta and reconciliation requests set
`dont_cache=True`. Even when the development HTTP cache is explicitly enabled,
an old cached response must never substitute for current change tracking.

## SQLAlchemy checkpoint state

Committed per-folder delta links and per-run candidates live in the shared
SQLAlchemy catalog. The older JSON checkpoint file is a legacy development
backup only and is not a runtime authority.

At delta start the Spider loads the committed delta-link map once through the
crawler-scoped catalog service, then uses the in-memory map during traversal.
The Spider never commits checkpoint state directly.

For every folder whose final Graph response contains `@odata.deltaLink`, the
Spider emits an `OutlookDeltaCheckpointCandidateItem`. `OutlookMailPipeline`
persists that candidate through SQLAlchemy.

## Checkpoint safety at `spider_idle`

`OutlookDeltaCheckpointExtension` handles Scrapy's `spider_idle` signal. Scrapy
2.19 defines this state as having no Requests waiting to download, no Requests
scheduled, and no Items still being processed by the Item Pipeline.

Correctness is not inferred from Stats. The extension compares two sources:

- the Spider's execution snapshot;
- durable SQLAlchemy checkpoint candidates for the current run id.

A checkpoint round is committed only if:

- the run has no acquisition-failure flag;
- folder inventory completed and did not fail;
- reconciliation completed;
- the set of started folders equals the set of completed folders;
- the set of completed folders equals the set of durable candidate folders.

If any condition fails, the existing committed checkpoints remain unchanged and
the crawl closes with `delta_incomplete` or `checkpoint_commit_failed` as
appropriate.

The SQLAlchemy catalog database is a private local file. Runtime database access
uses SQLAlchemy only; application code does not query SQLite with `sqlite3`.

## JOBDIR and business checkpoint separation

Scrapy `JOBDIR` is used only for execution-resume state: Scheduler Requests,
DupeFilter state and `Spider.state`. It is not the durable Microsoft delta
checkpoint.

Before Scrapy constructs the Scheduler, `SourceContextExtension` creates or
verifies a private JOBDIR marker containing only a digest of the logical
source and normalized catalog location. A different source/catalog is
rejected. A non-empty legacy JOBDIR without the marker is also rejected
because queued requests cannot be safely attributed after this upgrade.

For a delta job `Spider.state` records:

- run id;
- seen, started and completed folder ids;
- folder-inventory pending/completion/failure state;
- reconciliation orphan ids and completion state;
- run-failure state;
- whether the initial delta start request was already scheduled.

This allows a cleanly paused Scrapy job to resume the same acquisition round
without generating a new run id or re-emitting its root traversal request.

A real integration test verified this against Microsoft Graph: a deliberately
slowed crawl was interrupted once with SIGINT, closed with
`finish_reason=shutdown`, left one reconciliation Request in the persistent
Scheduler and retained twelve durable candidates. Running the same spider with
the same JOBDIR logged `Resuming crawl (1 requests scheduled)`, restored the
same run id, executed only reconciliation/orphan recovery, and then committed
the original twelve candidate checkpoints.

## Whole-mailbox reconciliation

Real personal-account testing demonstrated that `/me/messages` can expose a
message whose `parentFolderId` cannot be retrieved as a `mailFolder` and is not
present in the recursively enumerated folder tree. Pure per-folder delta would
therefore silently miss that message.

To protect the completeness goal, after folder inventory finishes msgloom makes
a lightweight whole-mailbox pass selecting only:

- `id`
- `parentFolderId`
- `lastModifiedDateTime`

The reconciliation callback processes each page as it arrives. It does not
accumulate the entire mailbox index in Spider memory. Messages whose parent
folder belongs to the enumerated tree need no additional request. A message
whose parent folder is not enumerable is treated as an orphan and receives one
targeted discovery request.

The tested personal mailbox currently has 232 visible messages, 12 enumerable
folders and one such orphan message.

## Throttling

Microsoft Graph may return HTTP 429 with `Retry-After`.

`MicrosoftGraphThrottleMiddleware` is independent of authentication and runs
before Scrapy's generic RetryMiddleware on the response path. It:

- honors `Retry-After` when present;
- understands both numeric seconds and HTTP-date forms;
- uses bounded exponential backoff when the header is absent;
- uses Scrapy's public `get_retry_request()` helper for retry construction;
- keeps a Graph-throttle retry counter separate from Scrapy's generic
  `retry_times`, so quota waits do not consume transport retry budget;
- prevents the generic RetryMiddleware from starting a second retry loop after
  Graph-throttle retries are exhausted.

Scrapy AutoThrottle is also enabled. It provides latency-based pacing, while the
custom Graph middleware handles Microsoft-specific 429 semantics. The hard
per-domain concurrency cap remains 2.

## HTTP cache

Scrapy HttpCache is a development/replay facility, not a normal synchronization
mechanism. It is disabled by default because Scrapy's default DummyPolicy does
not expire cached responses. Enable it explicitly with
`MSGLOOM_HTTP_CACHE_ENABLED=1` when deterministic local replay is useful.

Cached replay is not a new Microsoft source observation. Cached responses are
relinked to their original raw-evidence id and acquisition timestamp.
