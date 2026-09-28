# Microsoft Outlook Scrapy commands

All product-facing Microsoft acquisition commands live below one top-level
Scrapy command:

    scrapy microsoft ...

Outlook is a Microsoft product, so Outlook Mail and Calendar are resources
below the Microsoft and Outlook namespaces. The command layer only validates
CLI input and maps it to existing spiders. Graph traversal, authentication,
parsing, persistence, resume, and retry behavior remain in their established
Scrapy components.

## Outlook Mail discovery

    scrapy microsoft outlook mail discover [options]

Options:

- --folder FOLDER_ID: restrict discovery to one Graph mail folder;
- --page-size N: Graph page size, 1 through 1000; default 25;
- --max-pages N: explicit development/test limiter; 0 means unlimited.

Examples:

    scrapy microsoft outlook mail discover
    scrapy microsoft outlook mail discover --page-size 100
    scrapy microsoft outlook mail discover --folder inbox --page-size 100
    scrapy microsoft outlook mail discover --page-size 5 --max-pages 1

The command delegates to the internal outlook_discover spider.

## Outlook Mail delta synchronization

    scrapy microsoft outlook mail delta [options]

Options:

- --page-size N: preferred Graph delta page size; default 25;
- --reconcile / --no-reconcile: enable or disable whole-mailbox
  reconciliation; enabled by default.

Examples:

    scrapy microsoft outlook mail delta
    scrapy microsoft outlook mail delta --page-size 100
    scrapy microsoft outlook mail delta --no-reconcile

The command delegates to the internal outlook_delta spider.

## Outlook Mail synchronized acquisition

    scrapy microsoft outlook mail sync [options]

This is the normal user-level Mail workflow. It composes the existing Scrapy
spiders instead of implementing another traversal engine:

1. run per-folder delta synchronization and whole-mailbox reconciliation;
2. refresh every message changed or recovered by that delta run;
3. query the catalog for older messages whose `outlook-mail-full-v1` surfaces
   are still incomplete and run targeted `enrich` acquisition for that backlog.

Options:

- --page-size N: delta page size, 1 through 1000; default 25;
- --reconcile / --no-reconcile: whole-mailbox reconciliation, enabled by default;
- --max-enrich N: cap only planner-selected historical backlog; 0 or omitted is
  unlimited. Messages changed by the current delta run are never dropped by
  this backlog limit.

The phases run sequentially inside one Scrapy process. A delta phase must reach
terminal status `completed` before enrichment starts. `sync` rejects a shared
`JOBDIR`: JOBDIR belongs to one Scrapy crawl's Scheduler/SpiderState, not a
multi-spider workflow. Use `mail delta` directly when resumable single-phase
execution is required.

## Outlook Mail targeted full acquisition

    scrapy microsoft outlook mail full MESSAGE_ID [MESSAGE_ID ...] [options]

One or more message IDs are required. Duplicate IDs on one invocation are
removed while preserving first-seen order.

Options:

- --operation refresh|enrich: default refresh;
- --acquisition-profile outlook-mail-full-v1: versioned acquisition profile.

Examples:

    scrapy microsoft outlook mail full MESSAGE_ID
    scrapy microsoft outlook mail full MESSAGE_ID_1 MESSAGE_ID_2
    scrapy microsoft outlook mail full MESSAGE_ID_1 MESSAGE_ID_2 --operation enrich

The command delegates to the internal outlook_full spider.

## Outlook Calendar discovery

    scrapy microsoft outlook calendar discover [options]

Options:

- --page-size N: Graph page size, 1 through 1000; default 100.

The command delegates to the internal outlook_calendar_discover spider.

## Outlook Calendar window acquisition

    scrapy microsoft outlook calendar window --start ISO --end ISO [options]

Both bounds must be timezone-aware ISO-8601 datetimes and start must be earlier
than end.

Options:

- --calendar CALENDAR_ID: select a specific calendar; omitted uses the default;
- --page-size N: Graph page size, 1 through 1000; default 100.

The command delegates to the internal outlook_calendar_window spider.

## Outlook Calendar delta synchronization

    scrapy microsoft outlook calendar delta --start ISO --end ISO [options]

Calendar delta tracks one fixed time window in the signed-in user's primary
calendar. Both bounds are part of the durable checkpoint scope, so changing
either bound starts a different synchronization stream.

Options:

- --page-size N: preferred Graph delta page size, 1 through 1000; default 100.

The first run performs the initial fixed-window synchronization. Later runs with
the same source and exact bounds resume the committed Graph delta link. Scoped
`@removed` entries are retained as delta observations and are not treated as
proof that an event was globally deleted, because an event can also leave the
tracked time range.

The command delegates to the internal outlook_calendar_delta spider. Calendar
delta supports Scrapy JOBDIR for clean execution resume. SpiderState keeps only
the run identity/completion facts and the Scheduler keeps opaque queued requests;
the committed provider checkpoint remains in the catalog. Reusing one Calendar
delta JOBDIR with different start/end bounds is rejected before saved requests
run. Source/catalog changes are also rejected. Resume with the same Scrapy
version after a clean stop. Each independent synchronization round needs a new
JOBDIR; a completed JOBDIR does not start another provider poll.

A 410 response restarts the same fixed window once. The old checkpoint and
committed window membership remain available until the new attempt completes.
Checkpoint promotion uses a revision comparison, so concurrent runs cannot
overwrite a newer committed cursor. A failed or dropped item blocks promotion
and causes the public command to exit with failure.

## Outlook Calendar synchronized acquisition

    scrapy microsoft outlook calendar sync --start ISO --end ISO [options]

This is the user-level bounded Calendar workflow:

1. discover all visible calendars;
2. run fixed-window delta for the primary calendar;
3. run bounded `calendarView` acquisition for each secondary calendar;
4. select events sighted by those collection runs whose
   `outlook-calendar-full-v1` surfaces do not match the current Graph
   `changeKey`;
5. group those events by containing calendar and run targeted full enrichment.

This deliberately uses stable v1 primary-calendar delta plus periodic secondary
calendar windows instead of depending on beta multi-calendar delta endpoints.

Options:

- --start / --end: required timezone-aware fixed window;
- --page-size N: Graph page size, 1 through 1000; default 100;
- --max-enrich N: cap planner-selected event enrichment for the invocation;
  0 or omitted means unlimited.

The command rejects a shared `JOBDIR` for the same reason as Mail sync. Use the
`calendar delta` primitive when native JOBDIR resume is required for the primary
calendar phase.

## Outlook Calendar targeted full acquisition

    scrapy microsoft outlook calendar full EVENT_ID [EVENT_ID ...] [options]

Use this after discovery/window/delta identifies events whose full content is
needed. Duplicate event IDs are removed while preserving first-seen order.

Options:

- --calendar CALENDAR_ID: scope event and attachment paths to a specific
  calendar; omitted uses the default event path;
- --page-size N: attachment inventory page size, 1 through 1000; default 100;
- --operation refresh|enrich: default refresh;
- --acquisition-profile outlook-calendar-full-v1: versioned Calendar full
  acquisition profile.

Full acquisition uses Calendar read permission to retrieve the rich event
representation, asks Graph for a text event body, inventories attachments, and
retrieves raw content for file and item attachments. Reference attachments are
recorded without issuing an unsupported raw-content request. Versioned event
surfaces record detail, attachment-inventory, raw-content, and item-detail
outcomes against the event `changeKey`; a later event version therefore becomes
pending again automatically. Large attachment content remains in raw HTTP
evidence rather than being duplicated in the semantic attachment table.

The command delegates to the internal outlook_calendar_full spider.
Full acquisition currently rejects JOBDIR. To recover an interrupted full
acquisition, rerun the same event IDs. Raw evidence retains every capture, and
repeated captures with an unchanged `changeKey` do not add a semantic version.

## Standard Scrapy options

The Microsoft command retains Scrapy global options such as -L/--loglevel,
--logfile, --nolog, --profile for Python cProfile, --pidfile, -s NAME=VALUE,
and --pdb.

For example:

    scrapy microsoft outlook mail delta -L INFO -s JOBDIR=var/jobs/outlook-delta

## Developer-only low-level spider entry points

Scrapy's built-in crawl command still exposes internal spider names for
framework development and debugging, for example:

    scrapy crawl outlook_discover -a folder=inbox -a page_size=100
    scrapy crawl outlook_delta -a page_size=100 -a reconcile_global=1
    scrapy crawl outlook_full -a message_ids=MESSAGE_ID_1,MESSAGE_ID_2
    scrapy crawl outlook_calendar_delta -a start_datetime=ISO -a end_datetime=ISO
    scrapy crawl outlook_calendar_full -a event_ids=EVENT_ID_1,EVENT_ID_2

These are not msgloom's product CLI. Operational and user-facing workflows
should use the Microsoft hierarchy so provider/product/resource ownership is
explicit and command failure handling remains consistent.
