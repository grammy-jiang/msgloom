# Outlook Scrapy commands

The `message_ingest` Scrapy project in the `msgloom` repository exposes Outlook
Mail acquisition through project-specific commands.
Each command translates CLI options into arguments for its matching Spider:
`outlook_discover`, `outlook_delta`, or `outlook_full`. The commands contain no
Graph traversal, parsing, or persistence logic.

The three Spiders inherit the abstract `OutlookMailSpider` in
`message_ingest/spiders/outlook_mail.py`. It provides shared Graph requests,
evidence, and failure handling. Folder traversal and attachment traversal use separate
abstract subclasses with explicit contracts. Their callbacks remain bound
methods for `JOBDIR` serialization. Every module in `message_ingest/spiders`
is less than 500 lines.

## Discovery

```console
scrapy outlook_discover [options]
```

Default behavior is complete mailbox discovery.

Options:

- `--folder FOLDER_ID` — restrict discovery to one Graph mail folder;
- `--page-size N` — Graph page size, 1 through 1000; default 25;
- `--max-pages N` — explicit development/test limiter; 0 means unlimited and is
  the default.

Examples:

```console
scrapy outlook_discover
scrapy outlook_discover --page-size 100
scrapy outlook_discover --folder inbox --page-size 100
scrapy outlook_discover --page-size 5 --max-pages 1
```

The command runs `OutlookDiscoverSpider`. It needs no mode argument.

## Delta synchronization

```console
scrapy outlook_delta [options]
```

Options:

- `--page-size N` — preferred Graph delta page size, 1 through 1000; default 25;
- `--reconcile` / `--no-reconcile` — enable or disable the whole-mailbox
  reconciliation safety net; enabled by default.

Examples:

```console
scrapy outlook_delta
scrapy outlook_delta --page-size 100
scrapy outlook_delta --no-reconcile
```

The command runs `OutlookDeltaSpider`. Checkpoint loading, folder traversal,
delta continuation, and reconciliation remain Spider responsibilities.

## Targeted Full acquisition

```console
scrapy outlook_full [options] MESSAGE_ID [MESSAGE_ID ...]
```

One or more message IDs are required. Duplicate IDs on the same command line
are removed while preserving their first-seen order.
The command runs `OutlookFullSpider`.

Options:

- `--operation refresh|enrich` — `refresh` reacquires all current Full-profile
  surfaces; `enrich` only requests surfaces that are not already terminal in the
  local catalog; default `refresh`;
- `--acquisition-profile outlook-mail-full-v1` — versioned acquisition profile.

Examples:

```console
scrapy outlook_full MESSAGE_ID
scrapy outlook_full MESSAGE_ID_1 MESSAGE_ID_2
scrapy outlook_full --operation enrich MESSAGE_ID_1 MESSAGE_ID_2
```

`--acquisition-profile` intentionally does not use the name `--profile`, because
Scrapy already defines global `--profile FILE` for Python cProfile output.

## Standard Scrapy options remain available

All three commands inherit Scrapy's normal global command options, including:

- `-L / --loglevel`;
- `--logfile`;
- `--nolog`;
- `--profile FILE` for cProfile;
- `--pidfile`;
- `-s NAME=VALUE` for normal Scrapy setting overrides;
- `--pdb`.

For example:

```console
scrapy outlook_delta -L INFO -s JOBDIR=var/jobs/outlook-delta
```

The low-level commands are available for development and debugging:

```console
scrapy crawl outlook_discover -a folder=inbox -a page_size=100
scrapy crawl outlook_delta -a page_size=100 -a reconcile_global=1
scrapy crawl outlook_full -a message_ids=MESSAGE_ID_1,MESSAGE_ID_2 -a operation=enrich
```

`outlook_mail` is now an abstract base and is no longer a crawl target.
Replace old `scrapy crawl outlook_mail` invocations with the matching command
above. The `sync_mode` argument is no longer needed.

Normal operational use should prefer the Outlook-specific commands.
