# Message ingestion: Scrapy component layout

`message_ingest` is the Scrapy project within the `msgloom` repository. It owns
message acquisition from external providers. Outlook Mail is the first resource.
The code now separates Microsoft Graph provider infrastructure from Mail-specific
traversal so Calendar, Teams, and non-Microsoft resources can be added without
copying transport behavior.

The project uses **Scrapy 2.19.0**. The runtime, dependency declaration, and lockfile
agree on this version. `scrapy.cfg` selects `message_ingest.settings` and uses
`message_ingest` as the deployment project name. The root Python distribution
remains `msgloom`.

| Package | Responsibility |
| --- | --- |
| `message_ingest/extensions/catalog.py` | Own the crawler's catalog, write lock, evidence aliases, and shutdown. |
| `message_ingest/extensions/delta_checkpoint.py` | Commit complete delta rounds after Scrapy becomes idle. |
| `message_ingest/providers/microsoft_graph/auth.py` | Device-code and browser authentication, token caching, and one 401 refresh retry. |
| `message_ingest/providers/microsoft_graph/spider.py` | Graph request construction, raw evidence, terminal request failures, and logical run integrity. |
| `message_ingest/providers/microsoft_graph/fingerprints.py` | Keep Graph representation headers in scheduler/cache request identity. |
| `message_ingest/providers/microsoft_graph/errors.py` | Graph-specific retry decisions and delays through Scrapy's retry helper. |
| `message_ingest/providers/microsoft_graph/diagnostics.py` | Request correlation IDs and protocol diagnostics. |
| `message_ingest/providers/microsoft_graph/integrity.py` | Mark Graph logical runs failed for callback and item-processing signals. |
| `message_ingest/providers/microsoft_graph/log_privacy.py` | Install Graph-wide Scrapy core LogRecord privacy filtering. |
| `message_ingest/pipelines/evidence.py` | Store raw HTTP evidence and content-addressed payload files. |
| `message_ingest/pipelines/catalog.py` | Store semantic items and checkpoint candidates. |
| `message_ingest/catalog/models.py` | Define the existing SQLAlchemy schema. |
| `message_ingest/catalog/store.py` | Perform catalog queries and transactions. |
| `message_ingest/checkpoints.py` | Own source-scoped candidate queries and atomic checkpoint promotion. |

`message_ingest/settings.py` uses the component paths above. Custom settings and Python
imports should also use these module paths. `Catalog` and its models remain
available from `message_ingest.catalog`. Commands and spider names are unchanged.

Configuration keeps the existing `MSGLOOM_*` settings and environment variables.
Database and evidence paths, `msgloom/*` statistics, and persisted state keys also
keep their existing names so the package rename does not reset operational state.

`MicrosoftGraphSpider` is deliberately resource-neutral: it does not add Mail's
`Prefer: IdType="ImmutableId"` header and it accepts only explicitly allowlisted
string identifiers in failure context. `OutlookMailSpider` adds `Mail.Read`,
the immutable-ID preference, and Mail item projection. Provider integrity and
privacy extensions apply to every Graph resource; Outlook status/checkpoint
extensions remain resource-specific.

## Simplifications

- `CatalogService.from_crawler()` is the single factory for shared resources.
- Message discovery, delta observations, and message details share their persistence
  path while retaining their observation kinds, surface names, profiles, and stats.
- Observation replay detection is shared by messages and folder removals.
- The evidence pipeline passes one SQLAlchemy record to the catalog, removing a
  second copy of the same long argument list.
- The database schema is separated from query code. No migration is required.
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
HTTP exchanges visible to the spider, including cache replay. Pipeline priority
orders stages for each item; `CONCURRENT_ITEMS` does not provide a global lock.
See the [2.19.0 pipeline contract](https://github.com/scrapy/scrapy/blob/2.19.0/docs/topics/item-pipeline.rst).

The checkpoint extension checks explicit completion state on `spider_idle`, when
no items remain in processing. It keeps the commit synchronous because that signal
does not support asynchronous handlers. Catalog disposal stays on `spider_closed`.
See the [2.19.0 signal contract](https://github.com/scrapy/scrapy/blob/2.19.0/docs/topics/signals.rst).

## Validation

Run `.venv/bin/python -m pytest -q` and `.venv/bin/python -m scrapy check`.
The tests include local Graph crawls for all three commands, authentication and
retry boundaries, evidence replay, checkpoint failure handling, and JOBDIR resume.
Run Python LSP diagnostics on both `message_ingest/` and `tests/` after changing imports.
