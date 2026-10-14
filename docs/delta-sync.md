# Outlook mail delta synchronization

msgloom uses three complementary Microsoft Graph paths for Outlook mail:

1. mailbox-level mailFolder delta for folder add/update/remove lifecycle;
2. recursive folder inventory plus per-folder message delta for complete
   folder-tree/message synchronization;
3. a lightweight whole-mailbox reconciliation pass for coverage gaps that
   cannot be represented by the enumerable mail-folder hierarchy.

## Folder lifecycle delta

The user-level Mail sync workflow first runs the stable Graph
/me/mailFolders/delta stream. Its opaque deltaLink is stored independently from
all per-folder message delta cursors. Folder add/update entries refresh local
folder metadata and presence; explicit removed entries tombstone folder
presence and remove that folder's stale message-delta checkpoint.

This stream does not replace recursive folder inventory. Recursive inventory
remains the snapshot truth used to verify the complete nested folder tree and
to reconcile any folder that was missed or whose prior incremental state is
unavailable. Folder delta provides efficient lifecycle evidence, while a
complete recursive inventory can rebuild state.

The mailbox-level mailFolder delta cursor has **its own** immutable causal
contract, separate from each folder's message-delta cursor. The native Spider
reads the currently committed cursor URL *and its generation identity* before
constructing the first Graph request. It retains that digest across opaque
nextLink pages and one bounded 410 reset. A terminal page stages both its
next deltaLink and the original request-start identity in the additive,
SQL-guarded `mail_folder_delta_candidate_bases` table. The existing
`OutlookFolderDeltaCheckpointStore.commit` publishes scoped folder lifecycle
transitions, promotes the provider cursor, and verifies the exact baseline
generation under one shared catalog writer transaction. A delayed response
from an old baseline cannot override a newer committed folder cursor, even
if its receipt timestamp is later. Exact winner replay is read-only; a
pre-upgrade pending candidate without causal proof fails closed.

MailFolder delta **does not support JOBDIR**; this path starts a fresh native
Scrapy run and never invents a resume baseline. The separate per-folder message
delta implementation retains its existing JOBDIR/Scrapy resume contract.

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

At delta start the Spider loads a single read snapshot of committed per-folder
URLs and their causal baseline identities, then uses that in-memory map during
traversal. Each baseline is an SHA-256-tagged identity of the source, folder,
exact cursor URL, owner run and commit generation (or an explicit absent state).
The opaque Graph URL stays in the private catalog, never in the baseline tag.
For absent cursors, an additional private, source/folder-scoped generation
is incremented atomically whenever an authoritative folder removal invalidates
the message cursor. A delayed pre-removal initial request therefore cannot
become current again after the checkpoint was deleted. This marker is not
changed by ordinary folder metadata updates.
The Spider never commits checkpoint state directly.

For every folder whose final Graph response contains `@odata.deltaLink`, the
Spider emits an `OutlookDeltaCheckpointCandidateItem`. `OutlookMailPipeline`
persists that candidate together with its first-request baseline in the
additive `mail_delta_candidate_bases` table. A legacy pending candidate missing
proof is retained but cannot be promoted or retroactively authorized.

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
appropriate. After completion, the committing catalog writer transaction also
compares every original request-start baseline against the currently committed
checkpoint generation. The latest response timestamp does not prove Graph
cursor ancestry. One mismatched folder aborts lifecycle, all cursor commits
and release publication; an exact committed replay preserves the original
generation without modifying `committed_at`.

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

For a delta job `Spider.state` records only hashed baseline identities
alongside execution facts. Scrapy request `cb_kwargs` keeps the frozen identity
through provider `nextLink`, bounded 410 reset, and native disk scheduling.
On clean JOBDIR resume, previously started folders without persisted proof
fail closed. Provider delta URL bytes stay in the private catalog or Scrapy
request, never in the application SpiderState map.

For a delta job `Spider.state` records:

- run id;
- seen, started and completed folder ids;
- folder-inventory pending/completion/failure state;
- reconciliation orphan ids and completion state;
- run-failure state;
- whether the initial delta start request was already scheduled;
- the original per-folder causal identity tags (never raw Graph URL tokens).

This allows a cleanly paused Scrapy job to resume the same acquisition round
without generating a new run id or re-emitting its root traversal request.

A real integration test verified this against Microsoft Graph: a deliberately
slowed crawl was interrupted once with SIGINT, closed with
`finish_reason=shutdown`, left one reconciliation Request in the persistent
Scheduler and retained twelve durable candidates. Running the same spider with
the same JOBDIR logged `Resuming crawl (1 requests scheduled)`, restored the
same run id, executed only reconciliation/orphan recovery, and then committed
the original twelve candidate checkpoints.

## Mailbox presence semantics

A per-folder message removed record means only that the message left that
folder. It is persisted as a folder-removal observation and never by itself
marks the message globally absent.

Whole-mailbox reconciliation records one lightweight sighting for every message
ID it sees. Only after reconciliation reaches its terminal page and Scrapy
becomes idle can the snapshot be promoted. Messages known historically but
missing from that complete snapshot become confirmed mailbox-absent; messages
that are present or whose presence has never been globally reconciled remain
eligible for acquisition planning.

Folder inventory uses the same candidate/promotion pattern for current folder
presence. Missing folders from a complete recursive snapshot become absent and
their stale per-folder message delta cursors are removed.

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
