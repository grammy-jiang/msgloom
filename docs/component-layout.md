# Message ingestion: Scrapy component layout

`message_ingest` is the product acquisition Scrapy project within the `msgloom`
repository. Shared Microsoft Graph authentication lives in the sibling `microsoft_graph`
package so account/token handling is independent of the Microsoft product being
acquired. Outlook Mail is the mature resource,
and Microsoft Calendar now has explicit inventory, bounded-window, incremental
delta, and targeted full-content modes that reuse the shared Graph provider and
evidence components.

The project uses **Scrapy 2.19.0**. The runtime, dependency declaration, and lockfile
agree on this version. `scrapy.cfg` selects `message_ingest.settings` and uses
`message_ingest` as the deployment project name. The root Python distribution
remains `msgloom`.

| Package | Responsibility |
| --- | --- |
| `message_ingest/extensions/catalog.py` | Own the crawler's catalog, write lock, evidence aliases, and shutdown. |
| `message_ingest/extensions/microsoft/outlook/email/checkpoint.py` | Commit complete Mail delta rounds after Scrapy becomes idle. |
| `message_ingest/extensions/microsoft/outlook/email/status.py` | Publish terminal status for Outlook Mail discovery, delta, and full crawls. |
| `message_ingest/extensions/microsoft/outlook/calendar/checkpoint.py` | Promote complete fixed-window Calendar delta candidates after Scrapy becomes idle. |
| `microsoft_graph/auth/accounts.py` | Select opaque MSAL account identities without resource semantics. |
| `microsoft_graph/auth/binding.py` | Define the opaque application account-binding protocol with no msgloom dependency. |
| `microsoft_graph/auth/session.py` | Own crawler-scoped MSAL token/account state; application binding is injected through a protocol. |
| `microsoft_graph/middlewares/authentication.py` | Attach/remove credentials at the downloader boundary and refresh one pinned account after 401. |
| `message_ingest/extensions/microsoft_graph/identity.py` | Verify persisted source identity before Scheduler requests execute. |
| `message_ingest/spiders/microsoft/_graph.py` | Graph request construction, raw evidence, terminal request failures, and logical run integrity. |
| `message_ingest/fingerprints/microsoft_graph.py` | Keep source context and Graph representation headers in stable request identity. |
| `message_ingest/fingerprints/microsoft/outlook/calendar.py` | Separate Calendar delta reset attempts while preserving native duplicate filtering within one attempt. |
| `message_ingest/middlewares/microsoft_graph/errors.py` | Graph-specific retry decisions and delays through Scrapy's retry helper. |
| `message_ingest/middlewares/microsoft_graph/diagnostics.py` | Request correlation IDs and protocol diagnostics. |
| `message_ingest/extensions/microsoft_graph/integrity.py` | Mark Graph logical runs failed for callback and item-processing signals. |
| `message_ingest/extensions/microsoft_graph/privacy.py` | Install Graph-wide Scrapy core LogRecord privacy filtering. |
| `message_ingest/observability/formatter.py` | Apply provider-neutral Scrapy LogFormatter policy without URLs, payloads, or arbitrary exception text. |
| `message_ingest/observability/item_summary.py` | Produce public allowlisted summaries for acquisition, Outlook Mail, and Calendar items. |
| `message_ingest/items/acquisition.py` | Define provider-independent raw-evidence and exhausted-acquisition failure items. |
| `message_ingest/items/microsoft/outlook/email.py` | Define Outlook Mail discovery, enrichment, attachment, removal, surface, and delta-candidate items. |
| `message_ingest/items/microsoft/outlook/calendar.py` | Define Calendar inventory, event, attachment, delta-observation, and checkpoint-candidate items. |
| `message_ingest/pipelines/evidence.py` | Store raw HTTP evidence and content-addressed payload files. |
| `message_ingest/acquisition/contracts.py` | Define provider-independent structural contracts for evidence-linked items. |
| `message_ingest/acquisition/source_identity.py` | Bind logical sources to hashed opaque provider identities. |
| `message_ingest/acquisition/source_target.py` | Bind one logical source to one hashed provider resource target and refuse target switching. |
| `message_ingest/acquisition/source_context.py` | Isolate JOBDIR and request identity by logical source/catalog context. |
| `message_ingest/acquisition/evidence_link.py` | Resolve canonical evidence IDs/timestamps and validate persisted evidence before resource storage. |
| `message_ingest/acquisition/microsoft/outlook/email/profile.py` | Define versioned Outlook Mail full-acquisition completion policy and attachment surface requirements. |
| `message_ingest/acquisition/microsoft/outlook/email/planner.py` | Select current Mail records with incomplete Full-v1 surfaces from the catalog. |
| `message_ingest/acquisition/microsoft/outlook/calendar/profile.py` | Define changeKey-aware versioned Calendar full-acquisition completion policy. |
| `message_ingest/acquisition/microsoft/outlook/calendar/planner.py` | Select incomplete Calendar Full-v1 targets, optionally scoped to collection runs. |
| `message_ingest/acquisition/microsoft/outlook/notifications.py` | Validate basic Graph notification clientState and reduce payloads to privacy-safe sync hints. |
| `message_ingest/commands/microsoft/__init__.py` | Expose the sole public `scrapy microsoft` command and dispatch its hierarchy. |
| `message_ingest/commands/microsoft/auth.py` | Dispatch offline Microsoft auth status/clear operations through shared auth management. |
| `message_ingest/commands/microsoft/outlook/mail.py` | Map Outlook Mail CLI actions to existing spiders. |
| `message_ingest/commands/microsoft/outlook/calendar.py` | Map Outlook Calendar CLI actions to existing spiders. |
| `message_ingest/commands/microsoft/outlook/sync.py` | Compose sequential Mail/Calendar collection and planner-driven enrichment phases from existing spiders. |
| `message_ingest/pipelines/microsoft/outlook/email.py` | Route Outlook Mail items through the shared write lock into Mail/checkpoint stores. |
| `message_ingest/spiders/microsoft/outlook/calendar/discover.py` | Inventory visible calendars through paginated Graph callbacks. |
| `message_ingest/spiders/microsoft/outlook/calendar/window.py` | Acquire an explicit occurrence-expanded Calendar time window. |
| `message_ingest/spiders/microsoft/outlook/calendar/delta.py` | Incrementally synchronize one exact primary-calendar window. |
| `message_ingest/spiders/microsoft/outlook/calendar/full.py` | Acquire rich detail and attachments for selected events. |
| `message_ingest/spiders/microsoft/outlook/calendar/_attachments.py` | Own Calendar attachment pagination, raw-content requests, and item expansion. |
| `message_ingest/pipelines/microsoft/outlook/calendar.py` | Route Calendar/event/attachment/delta items through the shared write lock into Calendar/checkpoint stores. |
| `message_ingest/sync/microsoft/outlook/calendar/checkpoints.py` | Stage and atomically promote fixed-window Calendar delta cursors. |
| `message_ingest/sync/microsoft/outlook/calendar/state.py` | Apply winning delta observations to committed fixed-window membership. |
| `message_ingest/spiders/microsoft/outlook/calendar/_delta_state.py` | Serialize and validate Calendar execution facts independently of cursors. |
| `message_ingest/spiders/microsoft/outlook/calendar/_base.py` | Share Calendar own/delegated permission and mailbox-target behavior. |
| `message_ingest/extensions/microsoft/outlook/calendar/resume.py` | Validate Calendar window/full JOBDIR scope before saved requests execute. |
| `message_ingest/spiders/microsoft/outlook/email/_delta_state.py` | Serialize Mail delta execution facts independently of provider cursors. |
| `message_ingest/spiders/microsoft/outlook/_mailbox.py` | Select signed-in versus delegated mailbox paths and resource scopes. |
| `message_ingest/spiders/microsoft/outlook/email/folder_delta.py` | Track mailbox folder add/update/remove changes through an independent mailFolder delta cursor. |
| `message_ingest/catalog/models/base.py` | Own the shared SQLAlchemy declarative metadata. |
| `message_ingest/catalog/models/acquisition.py` | Define account/target source bindings and provider-independent raw-evidence models. |
| `message_ingest/catalog/models/microsoft/outlook/email.py` | Define Mail records, folder/message presence and sightings, Full-v1 surfaces, and independent folder/message delta checkpoints. |
| `message_ingest/catalog/models/microsoft/outlook/calendar.py` | Define Calendar resources, semantic versions, series topology, run sightings, Full-v1 surfaces, attachments, and fixed-window delta models. |
| `message_ingest/catalog/store.py` | Own the shared SQLite engine and session lifecycle only. |
| `message_ingest/catalog/stores/evidence.py` | Persist and query provider-independent raw HTTP evidence metadata. |
| `message_ingest/catalog/stores/microsoft/outlook/email.py` | Persist/query Outlook Mail, folder, attachment, and enrichment-surface state. |
| `message_ingest/catalog/stores/microsoft/outlook/_email_lifecycle.py` | Promote complete folder/message presence snapshots and apply explicit folder tombstones. |
| `message_ingest/catalog/stores/microsoft/outlook/calendar.py` | Persist Calendar inventory, event versions, delta observations, and attachment state. |
| `message_ingest/sync/microsoft/outlook/email/checkpoints.py` | Own source-scoped candidate queries and atomic checkpoint promotion. |
| `message_ingest/extensions/microsoft/outlook/email/folder_checkpoint.py` | Promote complete mailbox-level mailFolder delta cursors at Scrapy idle. |

Catalog model modules are split by persistence domain while `message_ingest.catalog.models` and `message_ingest.catalog` continue to re-export model classes. P0/P1 schema evolution is additive only: new Calendar enrichment/topology and Mail lifecycle/folder-delta tables are created through current metadata without altering existing columns.

Synchronization state and Scrapy lifecycle are intentionally separate. The `message_ingest/sync/` tree owns provider checkpoint/state rules and catalog transactions; `message_ingest/extensions/microsoft/outlook/` only adapts Scrapy signals and SpiderState to those rules. JOBDIR remains a framework resume mechanism rather than the provider checkpoint store.

Request identity and observability are project-level Scrapy policies rather than product Spider concerns. Graph-wide fingerprinting remains source-aware; Calendar delta adds only its reset-attempt identity. The global LogFormatter uses provider-neutral wording, while item summaries expose only allowlisted fields and are shared with Graph LogRecord privacy filtering.

`message_ingest/settings.py` uses the component paths above. Custom settings and Python
imports should also use these module paths. `Catalog` owns only engine/session lifecycle;
domain stores own SQL behavior. Commands remain thin intent/argument mapping over named
Scrapy spiders, and only `message_ingest.commands.microsoft.Command` is a public command.

The sibling `microsoft_graph` package contains only Microsoft account/token
handling and the authentication downloader middleware. It imports no msgloom
module. Msgloom source identity is connected through the
`MicrosoftGraphAccountBinding` protocol by the source-identity extension, so
authentication stays reusable across Outlook Mail, Calendar, Teams, and
future Microsoft resources.

Configuration keeps the existing `MSGLOOM_*` settings and environment variables.
Database and evidence paths, `msgloom/*` statistics, and persisted state keys also
keep their existing names so the package rename does not reset operational state.

`MicrosoftGraphSpider` is deliberately resource-neutral: it does not add Mail's
`Prefer: IdType="ImmutableId"` header and it accepts only explicitly allowlisted
string identifiers in failure context. Product Spiders declare only their
`graph_permissions` resource contract; the shared Graph Spider translates that
contract into auth settings. `OutlookMailSpider` additionally owns the
immutable-ID preference and Mail item projection. Provider integrity and
privacy extensions apply to every Graph resource; Outlook status/checkpoint
extensions remain resource-specific.

`MSGLOOM_SOURCE_ID` remains an internal namespace. Source identity binding,
Graph account selection, and source-context isolation are provider/acquisition
infrastructure rather than Mail semantics. Graph fingerprints include source
context so cache/dupefilter state cannot cross sources. JOBDIR ownership is
validated before Scheduler construction.

Large Spider modules are not split by line count alone. Pagination, request construction, errbacks, and reset handling remain with their owning Spider state machine. Only independently serializable Mail delta execution state was extracted, matching the existing Calendar delta execution-state boundary.

User-level `mail sync` and `calendar sync` workflows compose those native spiders sequentially through one `CrawlerProcess`. Catalog planners run only after a preceding crawler has fully closed. Mail refreshes resources changed by the current delta run before filling older incomplete Full-v1 backlog. Calendar records non-semantic per-run event sightings, uses primary-calendar delta plus secondary-calendar bounded windows, and enriches only events sighted by those collection phases whose Full-v1 surfaces do not match the current `changeKey`. Multi-phase sync intentionally rejects a shared JOBDIR; JOBDIR remains scoped to one crawler.

## Acquisition pipeline contract

Scrapy remains the pipeline engine. The enabled item stages are:

1. `RawEvidencePipeline` (200) persists raw HTTP evidence and publishes any
   cache-replay alias from the provisional evidence ID to its canonical capture.
2. `EvidenceLinkPipeline` (250) applies that alias to any item satisfying
   `EvidenceLinkedItem` and verifies that a non-null evidence reference exists.
3. Resource pipelines at 300 persist only their own domain item types. Outlook
   Mail uses `OutlookMailPipeline`; Calendar uses `OutlookCalendarPipeline`.

Pipeline priorities define stage order for one item. Cross-item dependency still
relies on the existing `CONCURRENT_ITEMS=1` callback-output contract: a callback
emits raw evidence before semantic items that reference it. The catalog write lock
continues to serialize SQL writes across overlapping response callbacks.

## Calendar acquisition modes

Calendar acquisition is intentionally split by user intent instead of making
one Spider carry unrelated traversal and lifecycle rules.

`outlook_calendar_discover` inventories calendars visible to the signed-in
account through `/me/calendars`. Absence from one inventory is not interpreted
as deletion.

`outlook_calendar_window` requires explicit timezone-aware start/end bounds and
uses `calendarView`, which expands recurring occurrences and exceptions inside
that range. The window may target the default calendar or one explicit calendar
ID. This is the bounded history/future-view mode and retains raw evidence before
semantic event items.

`outlook_calendar_delta` tracks changes for one exact start/end window of the
signed-in user's primary calendar. It follows provider next/delta links as
opaque URLs, bypasses HTTP cache, and stores every delta entry before staging a
terminal cursor candidate. `CalendarDeltaCheckpointExtension` promotes that
candidate only at Scrapy idle after item processing succeeds. The checkpoint is
scoped by logical source, primary-calendar scope, start, and end. A Graph 410
restarts the exact window once without advancing the old committed checkpoint.
Attempt-specific request fingerprints allow the reset to replay earlier URLs
while retaining native duplicate filtering inside each attempt. The winning
attempt's membership and checkpoint revision commit in one SQLite transaction.
An expired-token reset replaces previous membership only after successful
completion. Failed and stale competing attempts cannot change committed
membership.

Calendar delta supports clean JOBDIR resume with native SpiderState serialization
and Scrapy's persistent Scheduler. `CalendarDeltaSpiderState` loads and validates
execution facts in one `spider_opened` handler, before queued downloads start.
The source/catalog ownership guard remains separate. A rejected window leaves
the saved execution facts intact. Use the same Scrapy version and exact bounds
to resume a paused job. Use a new JOBDIR for each independent delta round;
reopening a completed job does not poll the provider again. Abrupt termination
is outside Scrapy's clean-resume guarantee.

A Calendar delta `@removed` marker is scoped to the tracked view. It is stored
as an immutable delta observation but does not set
`CalendarEventRecord.is_removed`, because an event that moves outside the fixed
window is also removed from that view.

`outlook_calendar_full` is targeted enrichment for one or more event IDs. It
uses `Calendars.Read`, requests a text body, and inventories event attachments.
File and item attachments receive a separate raw-content request; item
attachments also receive expanded Graph item detail. Reference/unknown
attachments remain visible in semantic metadata without an invalid raw-content
request. Binary/base64 content is not duplicated into the attachment table:
raw HTTP evidence owns the exact provider bytes and the semantic row stores the
content evidence link.
Expanded item attachments also keep nested `contentBytes` only in raw evidence.
Attachment rows use the parent event's resolved calendar ID within the same
source. Full acquisition supports clean JOBDIR pause/resume. Saved execution scope is validated before queued requests run, so a mismatched target/calendar/profile cannot reuse the job state.

`OutlookCalendarStore` maintains latest calendar/event state and append-only semantic
event versions; `OutlookCalendarPipeline` only routes items, serializes writes, and records
stats. Graph `changeKey` remains the semantic version boundary. When a
basic view and a richer detail response share one `changeKey`, their current
JSON projections are merged so a later basic capture cannot erase richer fields
such as body or organizer; no extra semantic version is invented.
If a delta page repeats an event, every entry remains in the delta observations.
Only the final upsert on that page updates the source-wide event projection.

The practical Calendar coverage is therefore:

1. discover available calendars;
2. acquire an occurrence-expanded bounded window from default or named calendar;
3. incrementally synchronize a durable fixed primary-calendar window;
4. enrich selected events with body and attachment content.

These modes share Graph authentication, evidence capture, request fingerprinting,
retry/privacy infrastructure, and source identity, but retain resource-specific
state and lifecycle rules.

## Simplifications

- `CatalogService.from_crawler()` is the single factory for shared resources.
- Message discovery, delta observations, and message details share their persistence
  path while retaining their observation kinds, surface names, profiles, and stats.
- Observation replay detection is shared by messages and folder removals.
- The evidence pipeline passes one SQLAlchemy record to the catalog, removing a
  second copy of the same long argument list.
- The database schema is separated from query code. For this V1-only additive
  change, `source_bindings` is created from current SQLAlchemy metadata; legacy
  source ownership still requires one explicit operator bootstrap. Changes to
  existing tables/columns require a future explicit migration mechanism.
- Checkpoint SQL lives directly in `OutlookDeltaCheckpointStore`, removing the
  forwarding layer through `Catalog`.
- Enrichment reads only the state it uses and streams its output. Small forwarding
  methods and the unused profile object were removed.
- Attachment type normalization and profile completion rules live in
  `message_ingest/acquisition/microsoft/outlook/email/profile.py` and are shared by attachment discovery and enrichment.

## Code documentation and style

Behavioral contracts live beside the implementation in docstrings and comments.
They describe evidence ordering, resource ownership, failure handling, replay,
and resume requirements. Update those contracts when behavior changes.

Docstrings follow Scrapy's PEP 257 and reStructuredText conventions. Use a short
summary and separate paragraphs for details. Short docstrings fit on one line;
multiline blocks have opening and closing quotes on separate lines. Code literals
use double backticks. API references use Sphinx roles such as `:class:`, `:meth:`,
and `:exc:`. Wrap prose and ordinary comments at 79 columns, keeping URLs and
Scrapy contract directives intact.

The reference is Scrapy 2.19.0's
[documentation policy](https://github.com/scrapy/scrapy/blob/2.19.0/docs/contributing.rst#documentation-policies),
[spider source](https://github.com/scrapy/scrapy/blob/2.19.0/scrapy/spiders/__init__.py),
and [retry helper](https://github.com/scrapy/scrapy/blob/2.19.0/scrapy/downloadermiddlewares/retry.py).

Source and tests use explicit failures instead of Python `assert` statements.
Production code raises specific exceptions for invalid state. Tests use guarded
`pytest.fail()` calls so checks remain active with Python optimization enabled.
Early returns and assignment expressions reduce nesting and repeated lookups.
Synchronous generators can use `yield from`; async generators require yield loops.
Every Python module remains below 500 lines, including documentation.
See [repository conventions](../AGENTS.md) for guidance to future contributors.

## Framework boundaries

Downloader middleware retains its existing priorities. Request hooks run in
ascending order; response hooks run in descending order. Native retry, cache,
throttling, and scheduling remain in use. See the
[2.19.0 middleware contract](https://github.com/scrapy/scrapy/blob/2.19.0/docs/topics/downloader-middleware.rst).

Pipelines await storage operations and share a write lock. Raw evidence means the
HTTP exchanges visible to the spider, including cache replay. Priority 200
persists raw evidence, priority 250 canonicalizes/validates evidence links, and
resource persistence starts at priority 300. Pipeline priority orders stages for
each item; `CONCURRENT_ITEMS` does not provide a global lock.
See the [2.19.0 pipeline contract](https://github.com/scrapy/scrapy/blob/2.19.0/docs/topics/item-pipeline.rst).

The checkpoint extensions check explicit completion state on `spider_idle`, when
no items remain in processing. They keep commits synchronous because that signal
does not support asynchronous handlers. Persistence pipelines dispose the shared
catalog in `close_spider`, after item processing and idle-time promotion.
See the [2.19.0 signal contract](https://github.com/scrapy/scrapy/blob/2.19.0/docs/topics/signals.rst).

## Validation

Run `.venv/bin/python -m pytest -q` and `.venv/bin/python -m scrapy check`.
The tests include local Graph crawls for Mail and Calendar commands, authentication and
retry boundaries, evidence replay, checkpoint failure handling, and JOBDIR resume.
Run Python LSP diagnostics on both `message_ingest/` and `tests/` after changing imports.
