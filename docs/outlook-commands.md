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

## Outlook Calendar targeted full acquisition

    scrapy microsoft outlook calendar full EVENT_ID [EVENT_ID ...] [options]

Use this after discovery/window/delta identifies events whose full content is
needed. Duplicate event IDs are removed while preserving first-seen order.

Options:

- --calendar CALENDAR_ID: scope event and attachment paths to a specific
  calendar; omitted uses the default event path;
- --page-size N: attachment inventory page size, 1 through 1000; default 100.

Full acquisition uses Calendar read permission to retrieve the rich event
representation, asks Graph for a text event body, inventories attachments, and
retrieves raw content for file and item attachments. Reference attachments are
recorded without issuing an unsupported raw-content request. Large attachment
content remains in raw HTTP evidence rather than being duplicated in the
semantic attachment table.

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
