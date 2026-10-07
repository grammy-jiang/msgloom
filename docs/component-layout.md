# Message ingestion: Scrapy component layout

`message_ingest` is the consumer Scrapy project in the `msgloom` distribution.
The sibling `microsoft_graph` package is a reusable Microsoft Graph-over-Scrapy
framework. Its component packages follow Scrapy's ownership model: spiders own
traversal, downloader middleware owns transport, and items carry provider data.
It also owns protocol parsing and authentication support. It imports neither
`message_ingest` nor SQLAlchemy.
Msgloom owns evidence, persistence, logical run integrity, source identity,
checkpoints, JOBDIR application state, enrichment completeness, and workflows.

The project uses **Scrapy 2.19.0**. The runtime, dependency declaration, and lockfile
agree on this version. `scrapy.cfg` selects `message_ingest.settings` and uses
`message_ingest` as the deployment project name. The root Python distribution
remains `msgloom`.

## Durable collection-to-preparation handoff

The integrated handoff keeps Scrapy component ownership unchanged. Spiders
still own traversal, pipelines await persistence, and extensions or workflows
own completion gates. A1 does not import A2 source-reader or preparation code.
The runtime is implemented and qualified. Final documentation review and
independent acceptance remain pending; see the
[qualification record](notes/a1-closeout.md#handoff-qualification-record--2026-10-07).

| Component | Responsibility |
| --- | --- |
| `message_ingest/acquisition/handoff.py` | Define provider-independent immutable fact and release contracts. |
| `message_ingest/catalog/stores/handoff.py` | Store catalog identity, staged facts, release groups, and pageable entries under transaction guards. |
| Provider catalog stores | Commit effective state with its fact and publish authority with the winning checkpoint and lifecycle changes. |
| `message_ingest/extensions/handoff.py` | Join native lifecycle completion to eligible non-authoritative publication. |
| `msgloom/sources/release_reader.py` | Read exact committed release entries and verify saved evidence without calling a live crawler. |
| `msgloom/preparation_pipeline/intake.py` | Capture a bounded cutoff, save exact selections, and admit entries as selections, scoped transitions, or held dispositions. |
| `msgloom/preparation_pipeline/historical_baseline.py` | Admit caller-approved exact historical versions as one starting workset for a new consumer scope. |
| `msgloom/persistence/intake_store.py` | Commit the workset, pending state, and cursor atomically under the intake claim. |
| `msgloom/persistence/intake_scheduling.py` | Discover pending work with durable bounded rotation. |
| `msgloom/persistence/intake_completion.py` | Require exact accepted preparation proof before workset finalization. |
| `msgloom/preparation_pipeline/scheduled.py` | Verify each trusted catalog pin before bounded pending replay and fresh admission. |
| `msgloom/preparation_pipeline/transitions.py` | Save accepted `prepared_transitions` from exact frozen scope facts. |
| `msgloom/cli/app.py` and `msgloom/configuration/models.py` | Expose one finite command and strict reusable target configuration. |

Evidence precedes semantics. The Reader rejects evidence that does not match
its immutable references. Intake saves selections before committing cursor
progress. A crash before cursor finalization permits exact retry; a later
preparation failure leaves the admitted workset pending. Within an existing
catalog identity, cursor-anchor checks reject restore behind the cursor and
a changed cursor entry. A different catalog identity at the start of a new
scheduled invocation selects another cursor scope; it is not compared with
the old catalog cursor.
No parser runs inside an A1 authority transaction or the short intake commit.

See [Phase 1 architecture](phase-1/architecture.md#durable-incremental-handoff)
and [scheduled preparation](notes/operator-configuration.md#scheduled-preparation).
The original [handoff contract](superpowers/specs/2026-10-03-a1-a2-handoff-contract-design.md)
remains the governing design; this section does not declare final acceptance.

## Microsoft Graph framework structure

```text
microsoft_graph/
  __init__.py
  auth/
    __init__.py
    accounts.py
    binding.py
    management.py
    session.py
  middlewares/
    __init__.py
    authentication.py
    errors.py
    diagnostics.py
    retry.py
  spiders/
    __init__.py
    graph.py
    user.py
    resources.py
    todo.py
    onedrive.py
    outlook/
      __init__.py
      mailbox.py
      mail.py
      calendar.py
  items/
    __init__.py
    graph.py
    todo.py
    onedrive.py
    outlook/
      __init__.py
      mail.py
      calendar.py
  protocol/
    __init__.py
    attachments.py
    calendar.py
    notifications.py
  extensions/
    __init__.py
    _logfilters.py
    privacy.py
    onedrive.py
  logformatter.py
  fingerprints.py
  request.py
  stats.py
  addon.py
```

`microsoft_graph` itself is the Scrapy framework package. `auth/` contains MSAL
session, account selection, account-binding, and management support code.
`middlewares/authentication.py` is the Scrapy authentication adapter. It imports
that support code and sits beside the error and diagnostics downloader
middleware. `protocol/` contains shared provider parsing and endpoint helpers
that do not depend on Scrapy.

Reusable configuration lives in `addon.py`, spider declarations, and consumer
settings. The framework has no `settings.py` or `pipelines/`. Its optional
privacy extension only sanitizes Scrapy records. Msgloom supplies persistence
pipelines and stateful lifecycle extensions through the consumer Scrapy project.

Msgloom enables `MicrosoftGraphAddon` at priority 100. It supplies safe retry
(550), Graph error handling (555), diagnostics (960), and default representation
and logging components. Explicit consumer component entries retain their
priorities. An explicit Graph privacy extension subclass, including a disabled
entry, replaces the default. Msgloom retains its privacy subclass, fingerprinter,
formatter, authentication selection, and lifecycle extensions. The separate
OneDrive content privacy extension supplements core privacy at priority 530.

`MicrosoftOneDriveSpider.content_request()` builds uncached binary requests and
marks them for private native redirects. `OneDriveContentPrivacyExtension`
sanitizes marked redirect/duplicate records and native HTTP/1.1 and compression
warnings for live marked requests. It keeps weak request references through
response middleware and removes filters at engine shutdown. Other product and
unmarked request logs retain their behavior. Native redirects still remove
cross-origin Authorization. Msgloom alone rewrites evidence URLs, selects retained
headers, records failures, and stores content digests and bytes.

Mail and Calendar provider spiders default to `IdType="ImmutableId"`.
`compose_prefer()` appends complete directives in order; explicit `prefer=None`
still suppresses the header. The user provider supplies only `User.Read` and
`user_path()` (`/me`); msgloom retains profile evidence and command output.

## Component ownership

| Package | Responsibility |
| --- | --- |
| `message_ingest/extensions/catalog.py` | Own the crawler's catalog, write lock, evidence aliases, and shutdown. |
| `message_ingest/extensions/microsoft/outlook/email/checkpoint.py` | Validate Mail delta rounds at Scrapy idle and adapt immediate/deferred/blocked commit modes without owning final rules-enabled promotion. |
| `message_ingest/extensions/microsoft/outlook/email/status.py` | Publish terminal status for Outlook Mail discovery, delta, and full crawls. |
| `message_ingest/extensions/microsoft/outlook/calendar/checkpoint.py` | Promote complete fixed-window Calendar delta candidates after Scrapy becomes idle. |
| `microsoft_graph/auth/accounts.py` | Select opaque MSAL account identities without resource semantics. |
| `microsoft_graph/auth/binding.py` | Define the opaque application account-binding protocol with no msgloom dependency. |
| `microsoft_graph/auth/session.py` | Own crawler-scoped MSAL token/account state; application binding is injected through a protocol. |
| `microsoft_graph/auth/management.py` | Inspect local authentication configuration and clear the local token cache. |
| `microsoft_graph/middlewares/authentication.py` | Attach/remove credentials at the downloader boundary and refresh one pinned account after 401. |
| `microsoft_graph/protocol/` | Validate Graph object, collection, delta, error, Calendar, attachment, and notification structures without Scrapy dependencies. |
| `microsoft_graph/spiders/graph.py` | Construct Graph requests, declare scopes, and preserve opaque continuation URLs. |
| `microsoft_graph/spiders/user.py` | Own the signed-in-user path and read scope without application output policy. |
| `microsoft_graph/spiders/resources.py` | Provide minimal object/collection spiders with replaceable item hooks and native pagination. |
| `microsoft_graph/items/graph.py` | Provide an optional provider-only GraphResourceItem dataclass. |
| `microsoft_graph/items/outlook/` | Provide optional Mail and Calendar dataclasses and resource mappers. |
| `microsoft_graph/items/todo.py` | Provide optional task-list, task, checklist, and linked-resource dataclasses with unchanged provider values. |
| `microsoft_graph/spiders/todo.py` | Own To Do read scopes and encoded v1.0 collection paths. |
| `microsoft_graph/items/onedrive.py` | Provide optional drive and driveItem dataclasses with unchanged provider values. |
| `microsoft_graph/spiders/onedrive.py` | Own OneDrive read scopes, encoded v1.0 paths, and safe binary content requests. |
| `microsoft_graph/items/contacts.py` | Preserve personal contact/folder projections and sparse tombstones without application state. |
| `microsoft_graph/spiders/contacts.py` | Own Contacts.Read and separate default/custom-folder paths with opaque continuation support. |
| `microsoft_graph/middlewares/errors.py` | Own Graph-specific retry/backoff through Scrapy's retry helper. |
| `microsoft_graph/middlewares/diagnostics.py` | Record Graph transport diagnostics for each attempt. |
| `microsoft_graph/middlewares/retry.py` | Preserve native generic retries with URL-safe logging. |
| `microsoft_graph/fingerprints.py` | Hash Accept/Prefer representations with Scrapy's native fingerprint helper. |
| `microsoft_graph/request.py` | Read the configured Graph host and request operation metadata. |
| `microsoft_graph/stats.py` | Resolve the consumer-selected Graph statistics prefix. |
| `microsoft_graph/spiders/outlook/` | Own mailbox/resource paths, own/shared scopes, caller-selected queries, and representation preferences. |
| `microsoft_graph/addon.py` | Supply overridable safe retry, transport diagnostics, representation identity, and Graph formatter defaults. |
| `microsoft_graph/logformatter.py` | Format Graph requests and item types without URLs, payloads, or arbitrary exception text. |
| `microsoft_graph/extensions/privacy.py` | Install crawler-scoped Scrapy core log sanitization without changing application state or stats. |
| `microsoft_graph/extensions/onedrive.py` | Supplement Graph privacy for sensitive native OneDrive content transport logs. |
| `message_ingest/extensions/microsoft_graph/identity.py` | Verify persisted source identity before Scheduler requests execute. |
| `message_ingest/spiders/microsoft/_graph.py` | Adapt reusable requests to msgloom evidence, failures, auth enablement, and logical run integrity. |
| `message_ingest/fingerprints/microsoft_graph.py` | Keep source context and Graph representation headers in stable request identity. |
| `message_ingest/fingerprints/microsoft/outlook/calendar.py` | Separate Calendar delta reset attempts while preserving native duplicate filtering within one attempt. |
| `message_ingest/extensions/microsoft_graph/integrity.py` | Mark Graph logical runs failed for callback and item-processing signals. |
| `message_ingest/extensions/microsoft_graph/privacy.py` | Select the application filter subclass, which preserves item summaries, run failures, lifecycle stats, and final-status correction. |
| `message_ingest/observability/formatter.py` | Supply application item summaries and preserve global acquisition privacy scope through the framework formatter. |
| `message_ingest/observability/item_summary.py` | Produce public allowlisted summaries for acquisition, Outlook Mail, and Calendar items. |
| `message_ingest/items/acquisition.py` | Define provider-independent raw-evidence and exhausted-acquisition failure items. |
| `message_ingest/items/microsoft/outlook/email.py` | Define Outlook Mail discovery, enrichment, attachment, removal, surface, and delta-candidate items. |
| `message_ingest/items/microsoft/outlook/calendar.py` | Define Calendar inventory, event, attachment, delta-observation, and checkpoint-candidate items. |
| `message_ingest/items/microsoft/todo.py` | Inherit To Do provider projections and add observation, evidence, and run context. |
| `message_ingest/pipelines/evidence.py` | Store raw HTTP evidence and content-addressed payload files. |
| `message_ingest/acquisition/contracts.py` | Define provider-independent structural contracts for evidence-linked items. |
| `message_ingest/acquisition/source_identity.py` | Bind logical sources to hashed opaque provider identities. |
| `message_ingest/acquisition/source_target.py` | Bind one logical source to one hashed provider resource target and refuse target switching. |
| `message_ingest/acquisition/source_context.py` | Isolate JOBDIR and request identity by logical source/catalog context. |
| `message_ingest/acquisition/evidence_link.py` | Resolve canonical evidence IDs/timestamps and validate persisted evidence before resource storage. |
| `message_ingest/acquisition/microsoft/outlook/email/rule_config.py` | Validate the closed V1 Mail policy vocabulary, profile mapping, rule ordering, bounds, and private effective-policy identity. |
| `message_ingest/acquisition/microsoft/outlook/email/rule_regex.py` | Implement the bounded privacy-safe `msgloom-regex-v1` adapter on pinned Google RE2. |
| `message_ingest/acquisition/microsoft/outlook/email/rule_body.py` | Convert bounded Graph text/HTML message bodies into deterministic logical BODY text for rule evaluation. |
| `message_ingest/acquisition/microsoft/outlook/email/rule_evaluation.py` | Define Scrapy-independent bounded Mail facts, observation/probe contracts, evaluator states, and terminal decisions. |
| `message_ingest/acquisition/microsoft/outlook/email/rule_predicates.py` | Evaluate discovery/metadata predicates and shared tri-state composition without Scrapy/provider I/O. |
| `message_ingest/acquisition/microsoft/outlook/email/rule_predicates_probe.py` | Evaluate BODY/header/extended-property predicates and documented message-class classifications behind the shared predicate API. |
| `message_ingest/acquisition/microsoft/outlook/email/rule_engine.py` | Evaluate ordered Mail rules deterministically, union reachable missing-data requirements, enforce monotonic profiles, and apply fail-safe Full fallback. |
| `message_ingest/acquisition/microsoft/outlook/email/rule_probe.py` | Define the internal bounded composite-probe result passed from Mail collection Spider callbacks back to the rule middleware. |
| `message_ingest/acquisition/microsoft/outlook/email/policy_context.py` | Bind the private effective Mail policy identity to JOBDIR before Scheduler construction and reject unsafe resume. |
| `message_ingest/acquisition/microsoft/outlook/email/full_completion.py` | Verify rule-selected Full-v1 terminal completeness from current-run evidence, including attachment inventory provenance and terminal limitations. |
| `message_ingest/acquisition/microsoft/outlook/email/profile.py` | Define versioned Outlook Mail discovery/full profiles and Full-v1 attachment surface requirements. |
| `message_ingest/acquisition/microsoft/outlook/email/planner.py` | Select the legacy rules-disabled catalog backlog of incomplete Full-v1 Mail records. |
| `message_ingest/acquisition/microsoft/outlook/calendar/profile.py` | Define changeKey-aware versioned Calendar full-acquisition completion policy. |
| `message_ingest/acquisition/microsoft/outlook/calendar/planner.py` | Select incomplete Calendar Full-v1 targets, optionally scoped to collection runs. |
| `message_ingest/acquisition/microsoft/outlook/notifications.py` | Classify validated provider resources, coalesce Outlook sync triggers, and select recovery reasons. |
| `message_ingest/commands/microsoft/__init__.py` | Expose the sole public `scrapy microsoft` command and dispatch its hierarchy. |
| `message_ingest/commands/microsoft/auth.py` | Dispatch offline Microsoft auth status/clear operations through shared auth management. |
| `message_ingest/commands/microsoft/outlook/mail.py` | Map Outlook Mail CLI actions to existing spiders. |
| `message_ingest/commands/microsoft/outlook/calendar.py` | Map Outlook Calendar CLI actions to existing spiders. |
| `message_ingest/commands/microsoft/todo.py` | Map read-only To Do discovery and authoritative snapshot sync to their spiders. |
| `message_ingest/spiders/microsoft/todo/discover.py` | Traverse lists, tasks, checklist items, and explicit linked resources with evidence-first callbacks. |
| `message_ingest/spiders/microsoft/todo/sync.py` | Reuse discovery callbacks with uncached authoritative traversal. |
| `message_ingest/extensions/microsoft/todo/snapshot.py` | Gate synchronous presence promotion on clean native idle and durable traversal proof. |
| `message_ingest/sync/microsoft/todo/snapshots.py` | Persist sightings and completions; atomically compare and swap snapshot presence. |
| `message_ingest/pipelines/microsoft/todo.py` | Await current-state writes under the shared catalog lock after evidence linking. |
| `message_ingest/catalog/models/microsoft/todo.py` | Define four additive current-state tables with source and provider identity keys. |
| `message_ingest/catalog/stores/microsoft/todo.py` | Apply latest-capture To Do projections without inferring deletion. |
| `message_ingest/commands/microsoft/onedrive.py` | Map OneDrive discovery, delta, and explicit content to their spiders. |
| `message_ingest/commands/microsoft/contacts.py` | Dispatch read-only Contacts discovery and authoritative snapshot sync. |
| `message_ingest/spiders/microsoft/contacts/` | Traverse default contacts and recursive custom folders; support explicit custom-folder delta. |
| `message_ingest/catalog/stores/microsoft/contacts.py` | Save current state and reconcile snapshot presence under shared promotion generations. |
| `message_ingest/catalog/stores/microsoft/_contacts_delta.py` | Stage ordered sparse changes and atomically promote the opaque cursor. |
| `message_ingest/catalog/stores/microsoft/_contacts_state.py` | Own shared snapshot/delta ordering and semantic state assignments. |
| `message_ingest/pipelines/microsoft/contacts.py` | Await Contacts writes after evidence linking under the shared catalog lock. |
| `message_ingest/extensions/microsoft/contacts/` | Gate synchronous snapshot/delta promotion on clean native idle. |
| `message_ingest/items/microsoft/onedrive.py` | Add provenance to provider metadata and define content metadata and checkpoint candidates. |
| `message_ingest/spiders/microsoft/onedrive/` | Own root discovery, metadata delta, explicit content, and download URL redaction. |
| `message_ingest/pipelines/microsoft/onedrive.py` | Await OneDrive current-state writes under the catalog lock after evidence linking. |
| `message_ingest/catalog/models/microsoft/onedrive.py` | Define additive source-scoped drive, item, content, and checkpoint tables. |
| `message_ingest/catalog/stores/microsoft/onedrive.py` | Preserve current metadata, explicit tombstones, content references, and checkpoint candidates. |
| `message_ingest/extensions/microsoft/onedrive/` | Promote clean delta candidates at Scrapy idle and sanitize native download logs. |
| `message_ingest/commands/microsoft/outlook/sync.py` | Compose Mail/Calendar workflows; rules-enabled Mail uses attempt-local Full targets, current-run completion validation, deferred delta promotion, and no legacy global backlog. |
| `message_ingest/pipelines/microsoft/outlook/email.py` | Route Outlook Mail items through the shared write lock into Mail/checkpoint stores. |
| `message_ingest/spiders/microsoft/outlook/calendar/discover.py` | Inventory visible calendars through paginated Graph callbacks. |
| `message_ingest/spiders/microsoft/outlook/calendar/window.py` | Acquire an explicit occurrence-expanded Calendar time window. |
| `message_ingest/spiders/microsoft/outlook/calendar/delta.py` | Incrementally synchronize one exact primary-calendar window. |
| `message_ingest/spiders/microsoft/outlook/calendar/full.py` | Acquire rich detail and attachments for selected events. |
| `message_ingest/spiders/microsoft/outlook/calendar/_attachments.py` | Own attachment traversal, evidence, size omissions, and Full-v1 completion using framework endpoints. |
| `message_ingest/pipelines/microsoft/outlook/calendar.py` | Route Calendar/event/attachment/delta items through the shared write lock into Calendar/checkpoint stores. |
| `message_ingest/sync/microsoft/outlook/calendar/checkpoints.py` | Stage and atomically promote fixed-window Calendar delta cursors. |
| `message_ingest/sync/microsoft/outlook/calendar/state.py` | Apply winning delta observations to committed fixed-window membership. |
| `message_ingest/spiders/microsoft/outlook/calendar/_delta_state.py` | Serialize and validate Calendar execution facts independently of cursors. |
| `message_ingest/spiders/microsoft/outlook/calendar/_base.py` | Compose framework Calendar scopes with msgloom mailbox/evidence behavior. |
| `message_ingest/extensions/microsoft/outlook/calendar/resume.py` | Validate Calendar window/full JOBDIR scope before saved requests execute. |
| `message_ingest/spiders/microsoft/outlook/email/_base.py` | Own Mail collection policy activation, one dynamic JOBDIR-serializable composite probe, bounded provider fact parsing, and attempt-local strongest-profile handoff; it does not implement rule matching. |
| `message_ingest/spidermiddlewares/microsoft/outlook/email.py` | Apply the pure Mail acquisition-policy evaluator at Spider output priority 1100, preserve source Items, schedule bounded probes, and emit privacy-safe rule logs/stats without database persistence. |
| `message_ingest/spiders/microsoft/outlook/email/_delta_state.py` | Serialize Mail delta execution facts independently of provider cursors. |
| `message_ingest/spiders/microsoft/outlook/_mailbox.py` | Bind framework mailbox paths/scopes to MSGLOOM_TARGET_MAILBOX and source-target identity. |
| `message_ingest/spiders/microsoft/outlook/email/folder_delta.py` | Track mailbox folder add/update/remove changes through an independent mailFolder delta cursor. |
| `message_ingest/catalog/models/base.py` | Own the shared SQLAlchemy declarative metadata. |
| `message_ingest/catalog/models/acquisition.py` | Define account/target source bindings and provider-independent raw-evidence models. |
| `message_ingest/catalog/models/microsoft/outlook/email.py` | Define Mail records, folder/message presence and sightings, Full-v1 surfaces, and independent folder/message delta checkpoints. |
| `message_ingest/catalog/models/microsoft/outlook/calendar.py` | Define Calendar resources, semantic versions, series topology, run sightings, Full-v1 surfaces, attachments, and fixed-window delta models. |
| `message_ingest/catalog/store.py` | Own the shared SQLite engine/session lifecycle and the explicit database writer-intent transaction context. |
| `message_ingest/catalog/stores/evidence.py` | Persist and query provider-independent raw HTTP evidence metadata. |
| `message_ingest/catalog/stores/microsoft/outlook/email.py` | Persist/query Outlook Mail, folder, attachment, and enrichment-surface state. |
| `message_ingest/catalog/stores/microsoft/outlook/_email_lifecycle.py` | Promote complete folder/message presence snapshots and apply explicit folder tombstones. |
| `message_ingest/catalog/stores/microsoft/outlook/calendar.py` | Persist Calendar inventory, event versions, delta observations, and attachment state. |
| `message_ingest/sync/microsoft/outlook/email/checkpoints.py` | Own source-scoped Mail delta candidate queries and session-scoped checkpoint promotion primitives. |
| `message_ingest/sync/microsoft/outlook/email/promotion.py` | Validate one Mail delta run and atomically promote message lifecycle plus authoritative delta cursors after immediate or rules-enabled workflow completion. |
| `message_ingest/extensions/microsoft/outlook/email/folder_checkpoint.py` | Promote complete mailbox-level mailFolder delta cursors at Scrapy idle. |

Catalog model modules are split by persistence domain while `message_ingest.catalog.models` and `message_ingest.catalog` continue to re-export model classes. P0/P1 schema evolution is additive only: new Calendar enrichment/topology and Mail lifecycle/folder-delta tables are created through current metadata without altering existing columns.

Synchronization state and Scrapy lifecycle are intentionally separate. The `message_ingest/sync/` tree owns provider checkpoint/state rules and catalog transactions; `message_ingest/extensions/microsoft/outlook/` only adapts Scrapy signals and SpiderState to those rules. JOBDIR remains a framework resume mechanism rather than the provider checkpoint store.

Request identity and observability are project-level Scrapy policies rather than product Spider concerns. Graph-wide fingerprinting remains source-aware; Calendar delta adds only its reset-attempt identity. The global LogFormatter uses provider-neutral wording, while item summaries expose only allowlisted fields and are shared with Graph LogRecord privacy filtering.

`message_ingest/settings.py` uses the component paths above. Custom settings and Python
imports should also use these module paths. `Catalog` owns engine/session lifecycle plus the shared `writer_session()` boundary,
which acquires SQLite writer intent before domain read-modify-write transactions;
domain stores own SQL behavior. Commands remain thin intent/argument mapping over named
Scrapy spiders, and only `message_ingest.commands.microsoft.Command` is a public command.

The root `microsoft_graph.__all__` remains limited to `GRAPH_HOST`, `GRAPH_ROOT`,
and `PROVIDER_ID`. Public component imports use their owning packages:

- `microsoft_graph.spiders`: `MicrosoftGraphSpider`, `GraphObjectSpider`, and
  `GraphCollectionSpider`.
- `microsoft_graph.spiders.outlook`: `OutlookMailboxSpider`, `OutlookMailSpider`,
  and `OutlookCalendarSpider`.
- `microsoft_graph.spiders.todo`: `MicrosoftTodoSpider`.
- `microsoft_graph.items.todo`: `TodoTaskListItem`, `TodoTaskItem`,
  `TodoChecklistItem`, and `TodoLinkedResourceItem`.
- `microsoft_graph.spiders.onedrive`: `MicrosoftOneDriveSpider`.
- `microsoft_graph.items.onedrive`: `OneDriveDriveItem` and `OneDriveItem`.
- `microsoft_graph.middlewares`: `MicrosoftGraphDelegatedAuthMiddleware`,
  `MicrosoftGraphDeviceCodeAuthMiddleware`,
  `MicrosoftGraphInteractiveAuthMiddleware`,
  `MicrosoftGraphErrorMiddleware`, and `MicrosoftGraphDiagnosticsMiddleware`.
- `microsoft_graph.items`: `GraphResourceItem`.
- `microsoft_graph.addon`: `MicrosoftGraphAddon`.
- `microsoft_graph.fingerprints`: `GraphRequestFingerprinter`.
- `microsoft_graph.request` and `microsoft_graph.stats`: shared transport helpers.

Authentication remains optional and keeps its existing import paths. Msgloom
connects source identity through `MicrosoftGraphAccountBinding`; the reusable
auth support code does not own source/catalog bindings.

Configuration keeps the existing `MSGLOOM_*` settings and environment variables.
Database and evidence paths, `msgloom/*` statistics, and persisted state keys also
keep their existing names so the package rename does not reset operational state.

The reusable `microsoft_graph.spiders.MicrosoftGraphSpider` owns request
construction and scope declarations. It does not enable an authentication method.
The consumer subclass at `message_ingest.spiders.microsoft._graph` retains
`MS_GRAPH_AUTH_ENABLED` behavior, raw evidence and failure items, `run_id`, run
failure state, and raw content limits. Outlook provider bases own mailbox scopes
and immutable Mail IDs. Msgloom bases add Item provenance and resource
failure context. Identity, integrity, checkpoint, and resume extensions remain
in `message_ingest`. Its privacy adapter layers integrity effects over the
framework's stateless log sanitization.

`MSGLOOM_SOURCE_ID` remains an internal namespace. Source identity binding,
Graph account selection, and source-context isolation are provider/acquisition
infrastructure rather than Mail semantics. Graph fingerprints include source
context so cache/dupefilter state cannot cross sources. JOBDIR ownership is
validated before Scheduler construction.

Large Spider modules are not split by line count alone. Pagination, request construction, errbacks, and reset handling remain with their owning Spider state machine. Only independently serializable Mail delta execution state was extracted, matching the existing Calendar delta execution-state boundary.

User-level `mail sync` and `calendar sync` workflows compose those native spiders sequentially through one `CrawlerProcess`. Catalog planners run only after a preceding crawler has fully closed. Mail refreshes resources changed by the current delta run before filling older incomplete Full-v1 backlog. Calendar records non-semantic per-run event sightings, uses primary-calendar delta plus secondary-calendar bounded windows, and enriches only events sighted by those collection phases whose Full-v1 surfaces do not match the current `changeKey`. Multi-phase sync intentionally rejects a shared JOBDIR; JOBDIR remains scoped to one crawler.

## Standalone framework usage

A collection needs no msgloom settings, catalog, or persistence pipeline:

```python
from microsoft_graph.spiders import GraphCollectionSpider


class ContactsSpider(GraphCollectionSpider):
    name = "contacts"
    endpoint = "/me/contacts"
    graph_permissions = ("Contacts.Read",)
```

`GraphObjectSpider` has the same declarations and validates a single JSON object.
`GraphCollectionSpider` validates the collection and each object, emits one item
per value, and follows opaque `@odata.nextLink` URLs through named callbacks and
the native scheduler. The optional `GraphResourceItem` dataclass has only
`resource` (the unchanged provider object) and `url` (its response URL). Scrapy
feed exporters and `ItemAdapter` accept it directly. Override
`resource_to_item(resource, response)` or `make_item(resource, response)` to
return a custom dataclass, Scrapy Item, or dict. No pipeline is required.

Optional Outlook defaults live in `microsoft_graph.items.outlook`:

| Resource | Default dataclass |
| --- | --- |
| Message | `OutlookMessageItem` |
| Mail folder | `OutlookMailFolderItem` |
| Message attachment | `OutlookAttachmentItem` |
| Calendar | `OutlookCalendarItem` |
| Event | `OutlookEventItem` |
| Event attachment | `OutlookCalendarAttachmentItem` |

Each class provides `from_graph(resource, ...)`. Attachment mapping also
requires the containing `message_id` or `event_id`. Mappers retain the original
resource as `raw`, including unknown fields and attachment content. Mail maps
common message/folder properties. Calendar projects name, change key, default
calendar and access flags. Events project subject, change key, start/end objects,
event type, series-master ID, all-day/cancellation flags, and attachment presence.
Calendar attachments project type, name, content type, size, and inline status.
Missing optional values stay `None`; false, zero, and empty strings survive.
Calendar `from_graph()` requires an object and a nonempty string ID. It does not
enforce completeness, window membership, or content retention policy. Direct
constructors accept IDs from consumer context and snapshot optional projections
from `raw`. Nested date/time objects keep their identity.
They do not add source URLs, observation times, evidence, run IDs, profiles,
surfaces, or checkpoints. Extra keyword arguments populate consumer subclass
fields. These defaults work with native Scrapy feed exports:

```python
from microsoft_graph.items.outlook import OutlookMessageItem


class MessagesSpider(GraphCollectionSpider):
    name = "messages"
    endpoint = "/me/messages"
    graph_permissions = ("Mail.Read",)

    def resource_to_item(self, resource, response):
        return OutlookMessageItem.from_graph(resource)
```

Msgloom retains its public Item names and exact dataclass field order. Mail
Items inherit provider dataclasses. Calendar Items compose provider projections
through a `provider` property; adding inherited dataclass fields would change
their existing serialized schema. The property reflects current raw metadata
and retains the application's explicit resource ID. Calendar storage consumes
these projections but still owns type filtering, observed-at validation,
change-key comparisons, and merging rich/basic captures of the same version.
Detail surfaces, raw evidence,
removals, presence sightings, and checkpoint candidates remain consumer Items.
Calendar's removal of attachment content from semantic storage also remains
consumer policy; provider mappers do not filter resource JSON.

Opt into the transport and privacy defaults with:

```python
ADDONS = {"microsoft_graph.addon.MicrosoftGraphAddon": 100}
```

The add-on replaces the implicit native `RetryMiddleware` with
`PrivacySafeRetryMiddleware` at 550. It also enables
`MicrosoftGraphErrorMiddleware` at 555 and
`MicrosoftGraphDiagnosticsMiddleware` at 960. Fingerprinting and log formatting
default to `GraphRequestFingerprinter` and `MicrosoftGraphLogFormatter` at
add-on settings priority. The add-on also installs the reusable
`MicrosoftGraphLogPrivacyExtension` at extension priority 100 and add-on settings
priority. Extension priority controls loading, not signal handler order.
Explicit project, spider, and CLI values win. An explicit privacy extension
entry, including `None` or a different priority, is preserved whether supplied
as a class or import path.

An explicit native retry entry, including `None` or a different component
priority, opts out of replacement. An explicit safe retry priority is retained
and disables the implicit native entry. An explicit safe retry `None` opts out
of that replacement. Existing custom `RetryMiddleware` subclasses and custom
middleware base dictionaries remain consumer choices. Independent custom retry
implementations should disable native retry through the standard `None` entry.
The add-on never overrides `RETRY_ENABLED=False`. Retry counts, HTTP codes,
priority adjustment, and stat names remain Scrapy's native contract.

Scrapy 2.19's component helpers merge class/path aliases and preserve component
entries, but mutate dictionaries regardless of setting priority. The add-on
checks explicit choices before using those helpers. See the exact release's
[add-on guidance](https://github.com/scrapy/scrapy/blob/2.19.0/docs/topics/addons.rst)
and [settings implementation](https://github.com/scrapy/scrapy/blob/2.19.0/scrapy/settings/__init__.py).

The add-on installs no auth component, pipeline, application lifecycle extension,
or concurrency/throttle/cache policy. Select an authentication component
and its settings explicitly, or provide authentication through another native
Scrapy middleware. Scope declarations populate `MS_GRAPH_SCOPES` defaults without
forcing `MS_GRAPH_AUTH_ENABLED`.

Use `graph_request()` for new requests and `continuation_request()` for opaque
provider URLs. The latter sets Scrapy 2.19's public `meta["verbatim_url"]`; it does
not parse or rebuild the URL. Both support Accept/Prefer, cache bypass, raw
response size limits, and named callbacks/errbacks. The neutral operation key is
`meta["microsoft_graph_operation"]`. Middleware reads that key first and falls
back to legacy `cb_kwargs["purpose"]`. Callback arguments remain consumer-owned.

`MS_GRAPH_SERVICE_ROOT` or the spider's `service_root` attribute overrides the
default `https://graph.microsoft.com/v1.0` and its allowed domain. Transport host
matching follows that root. This is a transport extension point, not a promise
of national-cloud authentication support. Outlook bases use
`MS_GRAPH_TARGET_MAILBOX` for `/me` versus `/users/{encoded locator}` and select
own/shared scopes. The msgloom adapter continues to use `MSGLOOM_TARGET_MAILBOX`.
Its small mailbox, Mail, and Calendar bases retain necessary MRO composition
with evidence and lifecycle behavior. Removing the mailbox setting alias would
save one override while risking existing project settings and source-target
bindings. The CLI `--mailbox`, shared scopes, target identity, and JOBDIR
ownership therefore keep their existing contract.
Mail defaults to `Prefer: IdType="ImmutableId"`; explicit `prefer=None` suppresses
that default. Calendar preferences remain request-specific.

Graph retry statuses are configurable with `MS_GRAPH_ERROR_RETRY_HTTP_CODES`.
Framework defaults are 429/503. `MS_GRAPH_ERROR_RETRY_409_CODES` defaults to
`["Directory_ConcurrencyViolation"]` and matches nested Graph codes without
case sensitivity. An empty list disables special 409 retries. Msgloom explicitly
retains 429/503/509 and that transient 409 code. Retry-After seconds/date, bounded fallback
backoff, 503 `Connection: close`, independent provider retry counts, and generic
retry suppression on exhaustion are unchanged. Retry requests still use
Scrapy's `get_retry_request`.

`MS_GRAPH_STATS_PREFIX` defaults to `microsoft_graph`; counters keep the `graph`,
`graph_error`, `graph_error_retry`, and `auth` families under that prefix.
Msgloom sets `msgloom` and retains all existing stat keys. Authentication errors
and remediation use `MS_GRAPH_CLIENT_ID` and `MS_GRAPH_ACCOUNT_USERNAME`.
Environment variable translation and CLI guidance belong to msgloom commands
and settings. Account selection, token acquisition, and MSAL cache behavior
remain unchanged.

Msgloom enables framework middleware directly; it has no middleware package or
wrapper classes. Logger names follow the canonical framework modules. Priorities
remain PrivacySafeRetry 550, Graph errors 555, device-code auth 950, interactive
auth 951, and diagnostics 960. Diagnostics therefore observes responses before
auth can replace a 401. Msgloom continues to select `PrivacySafeRetryMiddleware`
explicitly as its global replacement for native retry. Standalone consumers
receive it from the add-on only when they have not selected another retry policy.

The add-on enables both privacy components for Scrapy core exception
sanitization. Consumers that configure components without the add-on must select
the framework formatter and extension explicitly:

```python
LOG_FORMATTER = "microsoft_graph.logformatter.MicrosoftGraphLogFormatter"
EXTENSIONS = {
    "microsoft_graph.extensions.privacy.MicrosoftGraphLogPrivacyExtension": 100,
}
```

The formatter uses `graph_operation()` for request summaries and emits only
item types by default. It leaves non-Graph spider formatting unchanged. The
extension removes traceback data, sanitizes core Request representations,
start/close/signal errors, and native HttpCache read-failure records. Filters
install at `spider_opened` and are removed at `engine_stopped`. Records tagged
with another spider are left unchanged. Use both components: Scrapy attaches
tracebacks outside the LogFormatter hooks.

Msgloom's existing formatter and privacy extension paths remain selected. Their
small subclasses retain allowlisted item summaries, global acquisition
formatting, `mark_run_failed()`, lifecycle counters, and late final-status
correction. The framework does not know about logical run success or storage
failure policy.

Request metadata defaults are neutral and configurable:

| Setting | Framework default | Msgloom value |
| --- | --- | --- |
| `MS_GRAPH_ERROR_RETRY_META_KEY` | `_microsoft_graph_error_retry` | `_msgloom_graph_error_retry` |
| `MS_GRAPH_CLIENT_REQUEST_ID_META_KEY` | `_microsoft_graph_client_request_id` | `_msgloom_ms_client_request_id` |
| `MS_GRAPH_AUTH_RETRY_META_KEY` | `_microsoft_graph_auth_retry` | `_msgloom_ms_auth_retry` |
| `MS_GRAPH_AUTH_FORCE_REFRESH_META_KEY` | `_microsoft_graph_force_refresh` | `_msgloom_ms_force_refresh` |

Keep these settings stable when resuming an existing JOBDIR. Msgloom settings
preserve its saved counters and forced-refresh state without legacy names in
framework code. The crawler-only auth session attribute is not serialized.

The framework fingerprint uses native `scrapy.utils.request.fingerprint` with
`Accept` and `Prefer` for the configured host. Authorization never enters identity.
Msgloom composes its existing source/catalog digest and exact
`msgloom-graph-fingerprint-v1` hash format around the Graph representation hash;
existing default-host fingerprints remain unchanged. Custom service roots use
the same source isolation and representation rules. Calendar's reset-attempt
fingerprinter remains in msgloom.

## Protocol and delta compatibility

Outlook resource bases expose path helpers without callback, purpose, cache,
profile, or checkpoint policy. Mail provides `messages_path`, `message_path`,
`message_mime_path`, `mail_folders_path`, `message_delta_path`, and
`mail_folder_delta_path`. Folder arguments select folder messages or child
folders. The application Mail profile selects discovery, full-detail, and folder
fields. The application Contacts profile selects fields and excludes
``personalNotes``. Provider helpers accept caller-selected projections.

Calendar provides `calendars_path`, `event_path`, `calendar_view_path`,
`calendar_view_delta_path`, and `series_master_path`. Event and view paths
support default and named calendars; delta retains the current primary-calendar
endpoint. IDs are encoded once, and new query strings preserve field order and
boundary text. Continuation URLs remain opaque and never enter these builders.
`protocol/delta.py` validates tombstone shape without interpreting removal
semantics. `protocol/onedrive.py` validates exact same-origin reset locations;
the application retains retry limits, evidence redaction, and checkpoint policy.
Mail cursor handling follows request provenance, never token text.
`protocol/calendar.py` validates timezone-aware increasing window bounds,
derives series-master relations, and validates cancelled/exception occurrence
lists. It does not decide topology freshness, persistence, or acquisition scope.
Calendar discovery uses `calendars_path(page_size=...)` and the provider item
mapper. CLI datetime and window validation delegate to the same protocol
helpers while translating errors to argparse/Scrapy errors. Query bytes and
accepted boundary text stay unchanged. Store `observed_at` parsing remains
application timestamp validation.

Attachment reuse is deliberately at the protocol path boundary:
`attachment_list_path`, `attachment_raw_path`, and `item_attachment_path`.
The former `OutlookAttachmentSpider` request layer bypassed msgloom's `_request`
adapter and required duplicate purpose/errback wiring. It was removed. Both
Mail and Calendar traversal already use these paths through their application
request factories. Evidence-first callbacks, `purpose` callback arguments,
operation metadata, headers, cache/size options, and JOBDIR serialization stay
with the consumer. `attachment_type_name()` also serves Calendar persistence;
content status and Full-v1 completion remain application policy.

`protocol/notifications.py` authenticates basic webhook `clientState`, validates
the value list and entries, resolves resource/subscription mappings, and parses
change and lifecycle events. It returns ordered `GraphNotification` values.
Errors contain no provider identifiers, and resource values are omitted from
the dataclass representation. It neither classifies Outlook resources nor
chooses sync or recovery work. The application adapter classifies Mail/Calendar,
coalesces `OutlookSyncTrigger` values, chooses the strongest reason, and exposes
`requires_subscription_recovery`. Existing application error imports alias the
framework errors for compatibility. Catalogs, schedulers, and sync workflows
remain outside the notification protocol.

`microsoft_graph.protocol` exposes `GraphProtocolError`, `graph_object`,
`GraphCollectionPage`, `GraphDeltaPage`, and `GraphError`. Parsers consume decoded
JSON. Collections require an object and a value list; links must be non-empty
strings when present (JSON null means absent). Error envelopes retain nested
codes from both `innerError` and `innererror`. Parsing does not interpret cursors,
store them, promote candidates, or decide whether to restart after HTTP 410.

`GraphDeltaPage.from_payload()` validates exactly one next/delta link by default.
`strict=False` leaves missing/conflicting-state decisions with the consumer;
`validate_state()` is available for explicit strict validation. Msgloom defers
link validation until after evidence and semantic observations. Mail and
mailFolder delta explicitly retain missing-value-as-empty, falsey-link-as-absent,
and nextLink precedence, including ignoring an unused deltaLink when nextLink
exists. Calendar still requires a value list, emits its existing conflict or
missing-state failure item after observations, and blocks checkpoint promotion.
No checkpoint storage, CAS revision, 410 reset, DB schema, or JOBDIR application
state changed during this extraction.

Window callbacks and Mail folder/reconciliation callbacks use
`GraphCollectionPage`; object callbacks use `graph_object` or the series parser.
Raw evidence remains the first output. Mail inventory links retain falsey-link
compatibility. Calendar links remain strict. Both defer link validation until
after observations. Msgloom callbacks still own stats, topology Items, catalog
freshness, request sequencing, and promotion gates.

## Acquisition pipeline contract

Scrapy remains the pipeline engine. The enabled item stages are:

1. `RawEvidencePipeline` (200) persists raw HTTP evidence and publishes any
   cache-replay alias from the provisional evidence ID to its canonical capture.
2. `EvidenceLinkPipeline` (250) applies that alias to any item satisfying
   `EvidenceLinkedItem` and verifies that a non-null evidence reference exists.
3. Resource pipelines at 300 persist only their own domain item types. Outlook
   Mail uses `OutlookMailPipeline`; Calendar uses `OutlookCalendarPipeline`.
   To Do and OneDrive use their own current-state pipelines at the same stage.

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

## Microsoft To Do discovery and authoritative sync

Msgloom is a personal work-information system. Microsoft To Do supplies
obligation and action state: task status, deadlines, checklist state, and linked
evidence for future Topic analysis. This slice acquires current state through
the Microsoft Graph v1.0 `todoTask` API.

```console
.venv/bin/scrapy microsoft todo discover --page-size 100
.venv/bin/scrapy microsoft todo sync --page-size 100
```

The command accepts only `--page-size` as a product option, plus normal Scrapy
settings and logging options. It rejects resource IDs, `--mailbox`, and Outlook
Mail/Calendar options. Discovery uses `microsoft_todo_discover`; sync uses
`microsoft_todo_sync` and reuses the same four traversal callbacks.

The provider base declares only `Tasks.Read`. Microsoft documents this as the
least-privilege delegated permission for personal accounts for
[lists](https://learn.microsoft.com/en-us/graph/api/todo-list-lists?view=graph-rest-1.0),
[tasks](https://learn.microsoft.com/en-us/graph/api/todotasklist-list-tasks?view=graph-rest-1.0),
[checklist items](https://learn.microsoft.com/en-us/graph/api/todotask-list-checklistitems?view=graph-rest-1.0),
and [linked resources](https://learn.microsoft.com/en-us/graph/api/todotask-list-linkedresources?view=graph-rest-1.0).
All acquisition requests use GET. The framework owns scopes, path grammar,
single ID encoding, and optional provider-only Items. Nested body, date/time,
and recurrence objects retain their provider shape. Built-in `wellknownListName`
values, including `defaultList` and `flaggedEmails`, remain intact and follow
the same traversal.

The application owns callbacks, evidence, run integrity, and persistence.
Lists lead to tasks. Every task leads to explicit `checklistItems` and
`linkedResources` requests. These relation collections supply authoritative
relation observations even when task JSON embeds links. A linked resource can
omit `webUrl`. Each callback yields raw evidence before semantic Items and uses
`GraphCollectionPage` to read an opaque `nextLink`. Parent IDs travel through
`cb_kwargs` and are retained in failure context, never in stats labels.

The spider inherits the existing Graph authentication, retry, diagnostics,
privacy, and request-fingerprint policies. It uses the application `_request()`
helper and shared errback. Outlook checkpoint and status modes are disabled.
The pipeline stages are raw evidence at 200, evidence linking at 250, and To Do
storage at 300. Writes are awaited under `CatalogService.write_lock`. Storage
failures propagate to the shared integrity extension. To Do refuses `JOBDIR`
with `ValueError` because application resume behavior is not yet validated.

`MSGLOOM_TODO_SOURCE_ID` reads the environment and defaults to
`microsoft-todo-default`. The To Do spider sets effective `MSGLOOM_SOURCE_ID`
at spider priority. An explicit `-s MSGLOOM_SOURCE_ID=...` still wins. Outlook
source behavior is unchanged. To Do verifies account identity without creating
an Outlook source-target binding.

The catalog adds `todo_task_lists`, `todo_tasks`, `todo_checklist_items`, and
`todo_linked_resources`. Primary keys combine source ID with list ID, task ID,
and relation ID as applicable. Each row keeps the provider projection, raw
JSON, latest observation time, and latest evidence ID. Scalar provider dates
retain their original text; nested zoned dates remain JSON. Capture times are
compared as timezone-aware instants. Older captures cannot replace current
state. Equal capture times use processing order. Missing inventory entries do
not imply deletion.

Authoritative sync bypasses the HTTP cache for every page. It records source/run
sightings and terminal completion proof for lists, tasks, checklist items, and
linked resources. A candidate requires the exact complete traversal implied by
the sightings and current-run evidence for every completion.

At clean native idle, the snapshot extension verifies that the shared write
lock is free, then promotes synchronously before pipeline shutdown. One
transaction compares and swaps the source revision and reconciles separate
presence tables. A stale competing run cannot change authoritative presence.
Failure, dropped items, and incomplete pagination prevent promotion. Historical
provider records and evidence remain available when a key becomes absent.

The read-only task-delta capability probe succeeded with ``Tasks.Read``. Delta
remains optional and deferred. Snapshot correctness does not depend on it.
Write operations, task completion, and Topic linking remain out of scope. No
``baseTask`` path is used. See [the snapshot contract](notes/todo-sync.md).

## Microsoft OneDrive evidence and context

OneDrive is an evidence and context source for msgloom's personal
work-information system. It is not a primary Topic generator. This slice does
not create Topics automatically or download every file body.

```console
.venv/bin/scrapy microsoft onedrive discover --page-size 100
.venv/bin/scrapy microsoft onedrive delta --page-size 100
.venv/bin/scrapy microsoft onedrive content ITEM_ID [ITEM_ID ...]
```

These actions remain below the single public `microsoft` command. Discovery
and delta accept page sizes from 1 through 1000. Content requires explicit item
IDs and rejects `--page-size`. All three reject `--mailbox` and unrelated
Outlook, Calendar, To Do, and authentication options. Normal Scrapy settings
and logging options remain available. No upload, create, rename, move, delete,
or share mutation is implemented.

The provider declares only `Files.Read`. Microsoft documents this delegated
personal-account least privilege for
[drive metadata](https://learn.microsoft.com/en-us/graph/api/drive-get?view=graph-rest-1.0),
[folder children](https://learn.microsoft.com/en-us/graph/api/driveitem-list-children?view=graph-rest-1.0),
[driveItem delta](https://learn.microsoft.com/en-us/graph/api/driveitem-delta?view=graph-rest-1.0),
and [content](https://learn.microsoft.com/en-us/graph/api/driveitem-get-content?view=graph-rest-1.0).
All acquisition requests use GET. The framework owns path construction,
single ID encoding, and optional provider projections. It owns no traversal,
catalog, checkpoint, evidence, or content-retention policy for OneDrive.

`microsoft_onedrive_discover` reads `/me/drive`, then paginates
`/me/drive/root/children`. It records drive metadata and root children without
recursing through folders. `microsoft_onedrive_delta` reads metadata across
the drive hierarchy through `/me/drive/root/delta`. A first run supplies
`$top`; subsequent runs reuse the exact stored opaque `deltaLink`. Both modes
follow opaque `nextLink` values unchanged. Delta requests bypass the HTTP
cache. Each callback yields raw HTTP evidence before semantic items.

The terminal delta response produces a candidate linked to its evidence and
run. The OneDrive checkpoint extension promotes that candidate only after
Scrapy becomes idle, item writes complete, and the run passes its integrity
gates. Request, callback, or persistence failure blocks promotion. All three
OneDrive spiders reject `JOBDIR` until application resume semantics are validated.
An expired checkpoint response (HTTP 410) fails closed; this slice does not
discard the cursor or automatically reset it.

The app uses `MSGLOOM_ONEDRIVE_SOURCE_ID`, which defaults to
`microsoft-onedrive-default`. Each OneDrive spider sets effective
`MSGLOOM_SOURCE_ID` at spider priority; explicit command-line settings win.
The source belongs to the signed-in account and has no Outlook source-target
binding. Outlook and To Do retain their existing source behavior. Statistics
use bounded keys below `msgloom/crawl/onedrive/` and contain no provider IDs.

Current-state tables keep drive metadata by source, and drive items and latest
explicit content by source and item ID. Older observations cannot replace newer
state. False, zero, empty strings, and nested provider values remain intact.
Only a `deleted` facet marks an item deleted. Tombstones preserve useful prior
metadata that the provider omits; a first observation can be a sparse tombstone.
Discovery absence never implies deletion. The app removes
`@microsoft.graph.downloadUrl`, including nested `remoteItem` occurrences,
before semantic metadata storage. Raw metadata response bodies remain exact
HTTP evidence.

`microsoft_onedrive_content` requests `/me/drive/items/{item-id}/content` only
for the requested IDs. Microsoft's content endpoint redirects to a short-lived
preauthenticated download URL. Native Scrapy `RedirectMiddleware` follows that
redirect. The original request sets `allow_offsite=True`, which redirected
requests inherit. Existing delegated authentication strips Authorization
before redirect processing and never attaches it to a non-Graph host. Native
redirect handling also strips Authorization when scheme, host, or port changes.
No custom redirect or authentication middleware is needed.

Content requests use `dont_cache=True`. A nonzero
`MSGLOOM_MAX_RAW_CONTENT_BYTES` sets Scrapy's `download_maxsize`, so an oversized
download fails. The successful binary response emits sanitized raw evidence
before its semantic content item. Both evidence URL fields retain the safe
Graph `/content` source URL. URL-bearing headers, including `Location`, are
removed, and `preauthenticated_download_url_redacted` marks the response.
The content errback applies the same URL policy to failure evidence and
`AcquisitionFailureItem.url`. Existing retry, diagnostics, fingerprint, and
privacy components remain active. A OneDrive content privacy extension also
sanitizes native redirect and download-size log records that can contain the
preauthenticated URL.

The raw-evidence pipeline stores content bytes once in its content-addressed
blob store. The OneDrive content record contains only the item ID, digest,
byte count, observation time, evidence reference, and run provenance. It stores
no body bytes or preauthenticated URL. Raw evidence runs at priority 200,
evidence linking at 250, and OneDrive persistence at 300. Writes are awaited
under the shared `CatalogService.write_lock`; a disabled catalog disables the
resource pipeline.

## Simplifications

- `CatalogService.from_crawler()` is the single factory for shared resources.
- Message discovery, delta observations, and message details share their persistence
  path while retaining their observation kinds, surface names, profiles, and stats.
- Observation replay detection is shared by messages and folder removals.
- The evidence pipeline passes one SQLAlchemy record to the catalog, removing a
  second copy of the same long argument list.
- The database schema is separated from query code. Schema initialization holds
  `BEGIN IMMEDIATE` across the known `raw_http_evidence` migration and table
  creation. The migration accepts only the exact response-only legacy column
  set, preserves every legacy row and `body_*` value, and rebuilds the table
  with the current request/response columns plus the three old `body_*`
  compatibility columns. Those old columns become nullable so current ORM
  inserts are not blocked by obsolete NOT NULL constraints. Historical
  `body_*` metadata is copied exactly into `response_body_*`; historical
  GET request bodies are recorded as empty, while unavailable request headers,
  response URLs, flags, and error metadata remain empty or null.
  Migration-only fingerprints use a separate SHA-256 domain and the evidence
  ID, so current requests cannot intentionally select historical captures as
  cache aliases. Current indexes are recreated, the historical response-body
  digest index is retained, reopening is idempotent, and unknown partial
  schemas fail before DDL. `source_bindings` is still created from current
  SQLAlchemy metadata; legacy source ownership requires the existing explicit
  operator bootstrap.
- Checkpoint SQL lives directly in `OutlookDeltaCheckpointStore`, removing the
  forwarding layer through `Catalog`.
- Enrichment reads only the state it uses and streams its output. Small forwarding
  methods and the unused profile object were removed.
- Attachment type normalization and endpoint construction live in
  `microsoft_graph/protocol/attachments.py`. Mail and Calendar profiles re-export
  normalization for compatibility; Full-v1 completion rules remain in msgloom.

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

Run these checks from the repository root:

```console
.venv/bin/pytest -q
.venv/bin/ruff check microsoft_graph message_ingest tests
.venv/bin/ruff format --check microsoft_graph message_ingest tests
pyright microsoft_graph message_ingest
.venv/bin/scrapy check
```

The tests include local Graph crawls for Mail and Calendar commands, authentication and
retry boundaries, evidence replay, checkpoint failure handling, and JOBDIR resume.
Framework tests verify canonical public imports, the absence of a nested Scrapy
package, imports without `message_ingest` or SQLAlchemy, and protocol imports
without Scrapy. They also preserve standalone crawls, add-on precedence, exact
fingerprint bytes, callback/errback serialization, and delta compatibility.
Run Python LSP diagnostics on `microsoft_graph/`, `message_ingest/`, and `tests/`
after changing imports.

## Microsoft Contacts context

Contacts supplies identity and relationship context. It does not create Topics.
The provider requests only `Contacts.Read`. The selected projection excludes
`personalNotes`; raw evidence preserves the response to that selected request.

```console
.venv/bin/scrapy microsoft contacts discover --page-size 100
.venv/bin/scrapy microsoft contacts sync --page-size 100
```

Default contacts and recursive custom-folder inventory are separate surfaces.
Discovery saves observations without absence inference. Sync bypasses the HTTP
cache and requires terminal completion proof for the default collection,
folder inventory, and each custom folder's child and contact collections.
A complete clean run promotes separate presence tables at native idle.

Custom-folder delta requires an explicit concrete folder ID and remains a
low-level spider. It stages sparse changes and tombstones in provider order,
then promotes them with the exact opaque terminal cursor. Snapshot and delta
share a durable generation captured before traversal. A stale competing run
cannot advance presence or a cursor. All Contacts mutations use the shared
SQLite writer transaction boundary across independent Catalog instances.
Failures, dropped items, and incomplete traversal prevent promotion. `JOBDIR`
is rejected until Contacts resume semantics are qualified.

Synthetic acceptance covers recursion, pagination, schema registration,
ordering, and failure gates. Personal-account live acceptance completed on
2026-10-03 with read-only `Contacts.Read`: both discovery and authoritative
sync reached terminal Graph pages and the clean snapshot promotion committed.
The accepted account was empty, so non-empty recursive traversal remains
covered by synthetic fixtures. No provider mutation is part of automated
validation. See [the Contacts contract](notes/contacts-sync.md).
