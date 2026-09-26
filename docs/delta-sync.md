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
6. commits all candidates only after Scrapy becomes idle and the entire run is
   known to be complete.

Delta and folder-inventory requests set `dont_cache=True`. Scrapy's permanent
HTTP development cache must never substitute an old response for a current
change-tracking request.

## Checkpoint safety

The spider emits checkpoint-candidate items but never commits checkpoint state.
The item pipeline persists candidates under a per-run staging directory.

`OutlookDeltaCheckpointExtension` handles `spider_idle`, at which point Scrapy
has no pending downloader requests, scheduled requests, or items still being
processed by the item pipeline.

The extension commits the checkpoint set only if:

- folder inventory completed;
- global reconciliation completed (when enabled);
- every started folder delta completed;
- exactly one durable candidate exists for every completed folder;
- no acquisition failure or spider exception was recorded.

Otherwise the current checkpoint file is left unchanged and the crawl closes
with a specific incomplete/checkpoint-failure reason.

The committed checkpoint file is written atomically with mode `0600`.

## Whole-mailbox reconciliation

Real personal-account testing demonstrated that `/me/messages` can expose a
message whose `parentFolderId` cannot be retrieved as a `mailFolder` and is not
present in the recursively enumerated folder tree. Pure per-folder delta would
therefore silently miss that message.

To protect the completeness goal, after folder inventory finishes msgloom makes
one lightweight whole-mailbox request selecting only:

- `id`
- `parentFolderId`
- `lastModifiedDateTime`

Messages whose parent folder is part of the enumerated tree need no additional
request. A message whose parent folder is not enumerable is treated as an
orphan and receives one targeted discovery request so the observation is still
preserved.

This keeps normal incremental sync efficient while retaining a safety net for
Graph/container edge cases.

## Throttling

Delta and folder traversal can create short request bursts. Microsoft Graph may
respond with HTTP 429 and a `Retry-After` header.

`MicrosoftGraphThrottleMiddleware` is independent of authentication and runs
before Scrapy's generic retry handling on the response path. It:

- honors `Retry-After` when present;
- uses bounded exponential backoff when it is absent;
- prevents immediate generic retries of a throttled request;
- records throttle counters in Scrapy Stats;
- stops after a configured maximum rather than retrying forever.

The Graph domain concurrency is also intentionally conservative. Real mailbox
testing showed that reducing per-domain concurrency to 2 and avoiding pointless
`childFolders` requests for leaf folders eliminated observed 429 responses in
the tested mailbox.

## SQLAlchemy checkpoint state

Committed per-folder delta links and per-run candidates now live in the shared
SQLAlchemy catalog rather than a JSON checkpoint file. The earlier JSON file is
retained only as a legacy development backup and is not the runtime authority.

The Spider loads all committed delta links once in `start()` and keeps them in
memory for the run. This avoids repeated synchronous database reads in folder
callbacks. Candidate persistence is performed by `CatalogPipeline`; final
promotion remains the responsibility of the `spider_idle` checkpoint extension.
