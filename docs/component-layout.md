# Message ingestion: Scrapy component layout

`message_ingest` is the Scrapy project within the `msgloom` repository. It owns
message acquisition from external providers. Outlook Mail is the mature resource,
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
| `message_ingest/extensions/delta_checkpoint.py` | Commit complete Mail delta rounds after Scrapy becomes idle. |
| `message_ingest/extensions/calendar_delta_checkpoint.py` | Promote complete fixed-window Calendar delta candidates after Scrapy becomes idle. |
| `message_ingest/providers/microsoft_graph/accounts.py` | Select opaque MSAL account identities without resource semantics. |
| `message_ingest/providers/microsoft_graph/auth_session.py` | Own crawler-scoped MSAL token/account state and source pinning. |
| `message_ingest/providers/microsoft_graph/auth.py` | Attach/remove source-pinned credentials at the downloader boundary. |
| `message_ingest/providers/microsoft_graph/identity_gate.py` | Verify persisted source identity before Scheduler requests execute. |
| `message_ingest/providers/microsoft_graph/spider.py` | Graph request construction, raw evidence, terminal request failures, and logical run integrity. |
| `message_ingest/providers/microsoft_graph/fingerprints.py` | Keep source, Graph representation, and Calendar reset attempts in request identity. |
| `message_ingest/providers/microsoft_graph/errors.py` | Graph-specific retry decisions and delays through Scrapy's retry helper. |
| `message_ingest/providers/microsoft_graph/diagnostics.py` | Request correlation IDs and protocol diagnostics. |
| `message_ingest/providers/microsoft_graph/integrity.py` | Mark Graph logical runs failed for callback and item-processing signals. |
| `message_ingest/providers/microsoft_graph/log_privacy.py` | Install Graph-wide Scrapy core LogRecord privacy filtering. |
| `message_ingest/pipelines/evidence.py` | Store raw HTTP evidence and content-addressed payload files. |
| `message_ingest/acquisition/contracts.py` | Define provider-independent structural contracts for evidence-linked items. |
| `message_ingest/acquisition/source_identity.py` | Bind logical sources to hashed opaque provider identities. |
| `message_ingest/acquisition/source_context.py` | Isolate JOBDIR and request identity by logical source/catalog context. |
| `message_ingest/acquisition/evidence_link.py` | Resolve canonical evidence IDs/timestamps and validate persisted evidence before resource storage. |
| `message_ingest/pipelines/catalog.py` | Store Outlook Mail semantic items and checkpoint candidates after evidence linking. |
| `message_ingest/spiders/outlook_calendar_discover.py` | Inventory visible calendars through paginated Graph callbacks. |
| `message_ingest/spiders/outlook_calendar_window.py` | Acquire an explicit occurrence-expanded Calendar time window. |
| `message_ingest/spiders/outlook_calendar_delta.py` | Incrementally synchronize one exact primary-calendar window. |
| `message_ingest/spiders/outlook_calendar_full.py` | Acquire rich detail and attachments for selected events. |
| `message_ingest/pipelines/calendar.py` | Store Calendar/event/delta items after evidence linking. |
| `message_ingest/pipelines/calendar_attachments.py` | Store Calendar attachment metadata and raw-content evidence links. |
| `message_ingest/calendar_checkpoints.py` | Stage and atomically promote fixed-window Calendar delta cursors. |
| `message_ingest/calendar_delta_state.py` | Apply winning delta observations to committed fixed-window membership. |
| `message_ingest/spiders/_calendar_delta_state.py` | Serialize and validate Calendar execution facts independently of cursors. |
| `message_ingest/catalog/models.py` | Define the existing SQLAlchemy schema. |
| `message_ingest/catalog/store.py` | Perform catalog queries and transactions. |
| `message_ingest/checkpoints.py` | Own source-scoped candidate queries and atomic checkpoint promotion. |

`message_ingest/settings.py` uses the component paths above. Custom settings and Python
imports should also use these module paths. `Catalog` and its models remain
available from `message_ingest.catalog`. Commands remain thin intent/argument mapping over named Scrapy spiders.

Configuration keeps the existing `MSGLOOM_*` settings and environment variables.
Database and evidence paths, `msgloom/*` statistics, and persisted state keys also
keep their existing names so the package rename does not reset operational state.

`MicrosoftGraphSpider` is deliberately resource-neutral: it does not add Mail's
`Prefer: IdType="ImmutableId"` header and it accepts only explicitly allowlisted
string identifiers in failure context. `OutlookMailSpider` adds `Mail.Read`,
the immutable-ID preference, and Mail item projection. Provider integrity and
privacy extensions apply to every Graph resource; Outlook status/checkpoint
extensions remain resource-specific.

`MSGLOOM_SOURCE_ID` remains an internal namespace. Source identity binding,
Graph account selection, and source-context isolation are provider/acquisition
infrastructure rather than Mail semantics. Graph fingerprints include source
context so cache/dupefilter state cannot cross sources. JOBDIR ownership is
validated before Scheduler construction.

## Acquisition pipeline contract

Scrapy remains the pipeline engine. The enabled item stages are:

1. `RawEvidencePipeline` (200) persists raw HTTP evidence and publishes any
   cache-replay alias from the provisional evidence ID to its canonical capture.
2. `EvidenceLinkPipeline` (250) applies that alias to any item satisfying
   `EvidenceLinkedItem` and verifies that a non-null evidence reference exists.
3. Resource pipelines at 300 persist only their own domain item types. Outlook
   Mail uses `CatalogPipeline`; Calendar uses `CalendarPipeline`.

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
source. Full acquisition currently rejects JOBDIR; rerun the target IDs to
refresh an interrupted acquisition.

`CalendarPipeline` maintains latest calendar/event state and append-only semantic
event versions. Graph `changeKey` remains the semantic version boundary. When a
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
  `message_ingest/profiles.py` and are shared by discovery of attachments and enrichment.

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
