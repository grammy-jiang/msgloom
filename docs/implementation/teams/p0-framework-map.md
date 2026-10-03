# P0 framework extension map

**Status:** accepted with the coordinator correction below; P0 closure PASS.
**Input commit:** `7b9a7572b935f0e6ce6a96057b55951190afc8bf`.
**Task:** `MSGLOOM_TEAMS_A1_P0_A_RECOVERY_20261003_R2`.

The replacement [ChatGPT reviewer](https://chatgpt.com/c/6ac12b13-0a6c-83ec-9d75-0563b50c18c3)
returned PASS for four bounded framework cells. The final transcript is finished
and records `gpt-5-6-thinking` / `max`. The reviewer verified the cited archive
members against their SHA-256 inventory. This is static framework qualification,
not Teams implementation or runtime acceptance. The original stalled review is
not the accepted result. Raw results and transcript evidence remain in the
durable program workspace.

## Resource ownership

All rows reuse `MicrosoftGraphSpider.graph_request()` and
`continuation_request()` from `microsoft_graph.spiders.graph`. Application
callbacks own the Response, raw evidence, traversal, and semantic item emission.
The future Teams store owns durable observations. No provider module imports
`message_ingest`, msgloom product modules, or SQLAlchemy.

| Resource | Provider extension under `microsoft_graph/` | Application responsibility |
| --- | --- | --- |
| Chats and full chat detail | Chat paths, query helpers, pure chat dataclass/parser | Discover chats; retain chat type and scoped identity |
| Chat members | Explicit member paths and pure member parser | Traverse every member page; retain federation context |
| Chat messages | Common scoped message/version parser; chat message paths | Yield evidence, retain every observed version, follow opaque pages |
| Pins | Pin paths and relation parser | Store pin observations separately from messages |
| Teams and associated teams | Discovery/detail paths and topology parser | Hydrate accessible teams; retain partial-detail limitations |
| Channels and incoming channels | Discovery/detail paths and topology parser | Preserve host and receiving team/tenant identities separately |
| Shared-channel topology | `sharedWithTeams` paths and pure relation parser | Preserve each observed sharing relation |
| Team/channel membership | Members and `allMembers` paths and parsers | Preserve direct/indirect paths and original membership URL |
| Channel roots and replies | Context-specific paths plus the common message parser | Traverse every root and reply page with scoped IDs |
| Attachments and references | Pure Teams attachment parser and taxonomy | Store unknown forms and explicit resolution state; no arbitrary URL fetch |
| Hosted content metadata/bytes | Teams hosted paths and pure metadata parser | Fetch through Scrapy; retain response evidence and triggering observation link |

## Existing extension points

- `microsoft_graph.spiders.graph.MicrosoftGraphSpider` supplies scope hooks,
  service-root configuration, GET requests, named errbacks, and opaque
  continuation requests. `continuation_request()` sets `verbatim_url=True`.
- `microsoft_graph.protocol.GraphCollectionPage` owns collection-envelope
  validation and continuation values. No second collection abstraction is needed.
- `microsoft_graph.auth.session.MicrosoftGraphAuthSession`, the Graph add-on,
  and existing downloader middleware own MSAL, auth, retries, errors, and privacy.
- `microsoft_graph.fingerprints.GraphRequestFingerprinter` owns provider
  representation identity. The application selects its existing
  `RepresentationAwareRequestFingerprinter` for source/catalog context.
- `message_ingest.spiders.microsoft._graph.MicrosoftGraphSpider` supplies the
  application run identity, evidence constructors, named terminal errback, and
  failure flag. Every Teams application spider must inherit it.
- `RawEvidencePipeline`, `EvidenceLinkPipeline`, and `CatalogService` provide
  awaited raw writes, canonical evidence validation, and the shared write lock.
- `MicrosoftGraphIntegrityExtension` records callback/item/drop failures.
  Existing Contacts and To Do extensions demonstrate native idle gating.

Teams-specific request helpers may set `ConsistencyLevel: eventual` on the
Request returned by the existing builder where selected. This does not require
another transport or downloader middleware. Representation choices must be
qualified by focused fingerprint/cache tests before enabling them.

## Attachment correction

The worker suggested conditional reuse of
`microsoft_graph.protocol.attachments`. Actual source identifies that module as
Outlook mechanics: it selects Outlook attachment fields and exposes embedded
item expansion. These helpers are **not** the Teams attachment contract.

Teams `chatMessageAttachment` values are embedded message metadata. Preserve
their content, content type, references, app attribution, and unknown values in
the common Teams parser. Use Teams `hostedContents` paths for supported hosted
bytes. Do not invent `/attachments` traversal for Teams or use Outlook
`itemAttachment` expansion. Broader file resolution is unselected, so references
default to `not-attempted`.

This correction follows the actual helper source and Microsoft's current
[chatMessageAttachment resource contract](https://learn.microsoft.com/en-us/graph/api/resources/chatmessageattachment?view=graph-rest-1.0),
rechecked on 2026-10-04. It narrows an ambiguous reuse suggestion without adding
a generic framework primitive.

## Ordering, lifecycle, and coverage

Each application callback yields raw evidence before invoking its provider
parser. Scrapy can prefetch callback output; this does not prove that the raw
write completes before parser execution. The durable guarantee is evidence
before dependent semantic storage, using `CONCURRENT_ITEMS=1`, awaited writes,
and pipeline order 200/250/300. The Teams pipeline is type dispatch and awaited
storage only; it must not parse Graph JSON or schedule requests.

Initial Teams spiders reject JOBDIR. Initial discovery has no absence deletion
or authoritative promotion. Any future checkpoint or promotion requires native
`spider_idle`, a clean run, a free shared catalog lock, and durable resource
completion proof. Terminal failures retain the application errback path.

Keep every observed version and old body after explicit deletion. Message
history does not reconstruct unseen bodies. Hosted bytes link to the triggering
message observation without an exact provider-version claim. Preserve opaque
next links unchanged; only the separately documented trusted resource-link
workaround may normalize a resource link. Membership paths remain distinct.

All 36 core fixtures remain mandatory, including failed deletion readback and
delivery-gap uncertainty. Current-state reconciliation cannot restore gap-free
history. Notifications and their later tenant-permitted live gate are not waived.

## First implementation tranche

The coordinator owns all shared package exports, settings, catalog registries,
commands, dependencies, and cross-lane documentation. The three initial writers
have disjoint files:

- Message primitives: `items/teams/message.py`, `items/teams/content.py`, and
  `protocol/teams.py`, plus message/protocol/content tests.
- Chat topology: `spiders/teams/chat.py` and `items/teams/chat.py`, plus chat
  provider tests. No common message parser or application callbacks.
- Channel topology: `spiders/teams/channel.py`, `channel_paths.py`,
  `items/teams/channel.py`, and `membership.py`, plus channel/membership tests.
  No common message parser or application callbacks.

Production paths above are relative to `microsoft_graph/`. Exact owned test
paths and the committed base are frozen in each dispatch. Composition starts
only after its message and topology dependencies pass. No P1 writer starts
before the independent review of the exact converged A-D packet returns PASS
and the coordinator commits the P0 freeze.
