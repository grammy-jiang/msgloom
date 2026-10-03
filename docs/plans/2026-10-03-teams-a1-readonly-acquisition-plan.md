# Microsoft Teams A1 read-only acquisition plan

**Status:** reviewed planning baseline; no implementation in this round
**Prepared:** 2026-10-03
**Branch:** program/a1-teams-spider
**Worktree:** /home/grammy-jiang/Projects/msgloom-worktrees/a1-teams-spider
**Base:** A1 closed baseline 9e072eed17672f8380c709a9932ea56dbcbaff85
**Live acceptance:** deferred until a Microsoft work/school account is available

## 1. Objective

Add a future read-only Microsoft Teams acquisition program while keeping the
closed A1 baseline on master untouched. The worktree must stay isolated until
company-account live acceptance succeeds.

Teams is broader than chat messages. The design must inventory what the Teams
UI exposes, while keeping ownership correct when the data actually belongs to
Outlook/Exchange, SharePoint/OneDrive, OneNote, Planner, Shifts, online meeting
artifacts, or Viva Engage.

Existing A1 rules remain mandatory: read-only permissions, raw evidence before
semantic projection, opaque provider IDs and continuation URLs, awaited Scrapy
item processing, no unsafe deletion inference, and no live-support claim before
actual work/school testing.

## 1.1 Existing framework-first implementation constraint

The future Teams implementation must use the repository's existing
`microsoft_graph/` **Graph-over-Scrapy framework** as the provider foundation.

Do not add or use Microsoft's generated Python `msgraph-sdk` for this lane.
Do not add Azure Identity, Kiota, or a second HTTP client merely for Teams.
The current A1 architecture is already the approved Microsoft provider stack.

Teams should extend the same framework responsibilities already used by Outlook,
To Do, OneDrive, Contacts, and profile acquisition:

- `microsoft_graph.spiders.graph.MicrosoftGraphSpider` for Graph request
  construction and declared resource permissions;
- the existing Graph add-on and Scrapy Downloader stack;
- the existing MSAL authentication session/middleware;
- the existing privacy-safe retry, Graph error, diagnostics, and logging
  components;
- the existing request fingerprint/representation helpers;
- existing provider protocol primitives such as collection/error parsing and
  opaque continuation handling;
- provider-owned Teams path builders, projections, dataclasses, pure payload
  parsers, and request-spec helpers added below `microsoft_graph/`.

Do not move response callback traversal wholesale into `microsoft_graph/`.
The reusable framework cannot emit msgloom raw-evidence items without reversing
the dependency boundary. The application callback remains the smallest correct
owner of the sequence: capture raw response evidence, parse with pure provider
helpers, emit semantic items, then schedule provider-built follow-up paths.

The `microsoft_graph/` package must remain reusable and must not import
`message_ingest`, msgloom product modules, or SQLAlchemy.

`message_ingest/` should contain only application-owned concerns:

- source identity and source scope;
- raw evidence item creation and canonical evidence linking;
- logical-run integrity;
- thin evidence-first callbacks that compose provider path/parser helpers
  into named acquisition spiders;
- durable current/history state;
- checkpoint/presence promotion;
- bounded stats;
- public `scrapy microsoft teams ...` command mapping.

Do not reimplement Graph URLs, permissions, retry/auth policy, continuation
handling, or provider object parsing inside the Teams Item Pipeline.

## 1.2 Single Scrapy transport rule

Teams must use the existing Scrapy Downloader as the **only** Graph network
transport.

The target request path is:

```text
message_ingest Teams spider
        |
        v
microsoft_graph Teams provider helper/spider
        |
        v
MicrosoftGraphSpider.graph_request()
        |
        v
Scrapy Scheduler / Downloader
        |
        +--> existing MSAL auth middleware
        +--> existing privacy-safe retry/error middleware
        +--> existing diagnostics/privacy components
        |
        v
Microsoft Graph
        |
        v
Scrapy Response
        |
        +--> RawHttpEvidenceItem first
        |
        +--> provider parsing / semantic acquisition items second
```

No HTTPX client, generated SDK transport, or second Graph fetch is introduced.

Provider `@odata.nextLink` values remain opaque and are replayed verbatim
through the existing request API. Retry/backoff remains owned by the existing
Graph/Scrapy middleware. Request identity remains owned by the existing
fingerprinting layer.

Evidence-before-semantics remains exactly the current A1 pattern: each callback
emits its raw HTTP evidence before any Teams item derived from that response.

## 1.3 Authentication compatibility

Teams must reuse the current Microsoft authentication lifecycle unchanged:

- the same public `scrapy microsoft auth ...` management commands;
- the same `MicrosoftGraphAuthSession`;
- the same local MSAL token cache;
- the same delegated device-code/account selection behavior;
- the same source-identity binding and mismatch protection;
- resource-specific Teams read scopes declared by the provider spider.

No second sign-in implementation is allowed.

The future company-account acceptance may require a different Entra application
registration or administrator consent for some Teams scopes, but that changes
configuration/consent, not the framework's authentication workflow.

## 1.4 Source identity and live concurrency

Use one stable core Teams logical source ID for native delegated Teams surfaces
by default, for example `microsoft-teams-default`. Chats, teams, channels,
message/context lanes, and meeting-chat observations must bind to the same
signed-in Microsoft home-account identity rather than silently creating
unrelated logical sources. Adjacent products such as Planner, OneNote, Shifts,
and Viva Engage retain their own source ownership where their persistence model
is separate.

The current MSAL token-cache implementation does not provide cross-process
locking/merge. Parallel development and synthetic fixture crawls can use
auth-disabled/local fixture settings, but live company-account crawls that share
the same `MSGLOOM_MS_TOKEN_CACHE` must run serially or use explicitly distinct
cache paths until cross-process cache coordination is implemented. This is a
credential-state constraint, not a reason to reduce parallel code development.

Application-only Teams acquisition, if ever approved, requires a separately
designed source-identity key scheme because it has no signed-in user home
account; it must not reuse the delegated source binding by assumption.

## 2. Surface inventory

### 2.1 Native Teams

The Teams acquisition program must account for all of these:

- one-on-one chats;
- group chats;
- meeting chats;
- chat members;
- chat messages;
- teams and team membership;
- standard, private, and shared channels;
- shared-channel and associated-team topology;
- channel root posts and every reply page;
- message edits, deletes, reactions, mentions, history, and system events;
- attachments, forwarded-message references, and hosted content;
- pinned chat messages;
- custom-emoji occurrences and other message-body fidelity data;
- tabs, installed apps, resource-specific permission grants, and Teams tags.

### 2.2 Microsoft 365 resources surfaced in Teams

These should be linked to Teams records while retaining their actual provider
ownership:

- user Outlook calendar events for Teams meetings;
- Microsoft 365 group/team calendars;
- onlineMeeting metadata;
- meeting attendance reports;
- meeting transcripts and recordings;
- Teams webinars, town halls, virtual-event sessions, presenters, and event
  metadata;
- SharePoint and OneDrive files;
- OneNote notebooks/pages;
- Planner plans/tasks;
- Shifts schedules and work-state records;
- Teams presence/activity state;
- Viva Learning provider/content metadata;
- Microsoft 365 group conversations where they are relevant, while keeping them
  owned by the group/Outlook resource model rather than Teams chat.

### 2.3 Separate or privileged surfaces

These must not be silently folded into ordinary delegated Teams collection:

- Viva Engage;
- application-only Teams export and delta APIs;
- targeted-message export, which is application-only even though the resource
  is v1.0;
- complete virtual-event registration export where the API requires
  application/RSC access;
- tenant-wide meeting Q&A export;
- live calling/IVR APIs and call records;
- user Teams sections, whose current API is beta;
- the tenant custom-emoji directory, whose current API is beta;
- the native Teams Approvals app: Microsoft documents an Approvals Graph API
  overview and subscriptions, but the approvalItem list/get surface reviewed in
  this round is still `/beta`; keep it inventory-only until a stable v1.0 read
  contract exists;
- legacy Teams device-management Graph APIs, which Microsoft marked deprecated
  and unsupported after 2025;
- other tenant-wide application-only export surfaces.

They may reuse Graph transport helpers but require separate permission,
identity, acceptance, and persistence decisions.

### 2.4 Coverage and permission matrix

This table is the implementation checklist. "Initial delegated" means eligible
for the first company-account build. "Separate" means it is part of the complete
inventory but must not be silently enabled by the core Teams permission set.

| Surface | Representative Graph surface | Read permission/profile | Mode | Plan |
| --- | --- | --- | --- | --- |
| One-on-one/group/meeting chats | `/me/chats` | `Chat.Read` | Delegated work/school | Initial delegated |
| Chat members | `/chats/{id}/members` | T1 `Chat.Read`; `Chat.ReadBasic` is sufficient for members-only reads | Delegated work/school | Initial delegated |
| Chat messages | `/chats/{id}/messages` | `Chat.Read` | Delegated work/school | Initial delegated |
| Chat pinned messages | `/chats/{id}/pinnedMessages` | `Chat.Read` | Delegated work/school | Initial delegated |
| Chat hosted content | message `hostedContents` | `Chat.Read` | Delegated work/school | Initial delegated |
| Direct teams | `/me/joinedTeams` | `Team.ReadBasic.All` | Delegated work/school | Initial delegated |
| Team rosters | `/teams/{id}/members` | `TeamMember.Read.All` | Delegated work/school; admin consent | T2 complete profile |
| Channels/shared topology | `associatedTeams`, `allChannels`, `incomingChannels`, `sharedWithTeams` | `Team.ReadBasic.All` + `Channel.ReadBasic.All` | Delegated work/school | Initial delegated |
| Channel direct/all membership | channel `members` / `allMembers` | `ChannelMember.Read.All` | Delegated work/school; admin consent | T2 complete profile |
| Channel root/reply messages | channel `messages` / `replies` | `ChannelMessage.Read.All` | Delegated work/school; admin consent | Initial delegated |
| Channel hosted content | message `hostedContents` | `ChannelMessage.Read.All` | Delegated work/school; admin consent | Initial delegated |
| Tags/tag members | `/teams/{id}/tags` | `TeamworkTag.Read` | Delegated work/school | Optional T3 |
| Chat/channel tabs | chat/channel `tabs` | `TeamsTab.Read.All` | Delegated work/school | Optional T3 |
| Installed apps | user/chat/team `installedApps` | scoped `TeamsAppInstallation.ReadFor*` | Delegated work/school | Optional T3 |
| Targeted messages | `userTeamwork/getAllTargetedMessages` | `TeamworkTargetedMessage.Read.All` | Application only | Separate future profile |
| User chat-list sections | `userTeamwork/sections` | `TeamworkSection.Read` | Beta | Inventory only |
| Tenant custom-emoji directory | `/teamwork/messaging/customEmojis` | beta custom-emoji read scope | Beta | Inventory only |
| Channel files location | channel `filesFolder` | `Files.Read.All` | Delegated work/school | Separate file profile |
| User Teams meeting calendar | Outlook event/calendarView | existing A1 Calendar permission | Delegated | Link existing A1 |
| Team/group calendar | `/groups/{id}/calendarView` | `Group.Read.All` or supported calendar scope | Delegated work/school | Separate calendar lane |
| Online meeting | `onlineMeeting` | `OnlineMeetings.Read` | Delegated work/school | Optional T4 |
| Attendance | attendance reports/records | `OnlineMeetingArtifact.Read.All` | Delegated work/school | Optional T4 |
| Transcript | meeting transcripts | `OnlineMeetingTranscript.Read.All` | Delegated work/school | Optional T4 |
| Recording | meeting recordings | `OnlineMeetingRecording.Read.All` | Delegated work/school | Optional T4 |
| Webinar/town hall | `/solutions/virtualEvents/...` | `VirtualEvent.Read` | Delegated work/school | Optional T4 |
| Full virtual-event registration export | registration collections | application/RSC permission | Application/RSC | Separate future profile |
| Planner basic plans/tasks | Planner resources | `Tasks.Read` | Delegated work/school | Separate T5 lane |
| OneNote team/group content | group/site OneNote resources | `Notes.Read` for content; endpoint recheck at T0 | Delegated | Separate T5 lane |
| Shifts | `/teams/{id}/schedule/...` | `Schedule.Read.All` | Delegated work/school | Separate T5 lane |
| Presence | `/me/presence` | `Presence.Read` | Delegated work/school | Optional contextual lane |
| Viva Learning | `/employeeExperience/learningProviders/...` | `LearningContent.Read.All` | Delegated work/school | Separate adjacent lane |
| Viva Engage communities | `/employeeExperience/communities` | `Community.Read.All` | Delegated work/school | Separate Engage lane |
| Chat export/delta | user `getAllMessages` / `getAllMessages/delta` | `Chat.Read.All` | Application only | Separate future profile |
| Channel message delta | official overview advertises channel `/delta`, but its current linked v1.0 reference resolves to user chat delta | unresolved at plan review | Recheck at T0 | Do not implement until exact endpoint/permissions are verified |
| Meeting Q&A export | cloud communications export | application permission | Application only | Separate future profile |
| Call records | callRecords | `CallRecords.Read.All` | Application only | Separate future profile |
| Teams devices | legacy teamworkDevice | deprecated beta API | Unsupported old API | Exclude |

## 3. Core API findings

### 3.1 Chats

GET /me/chats enumerates the signed-in work/school user's chats. Preserve
chatType so one-on-one, group, and meeting chats remain distinct. Personal
Microsoft accounts are not supported.

Core delegated profile: Chat.Read.

Do not rely on expanding members inline. Microsoft documents an expansion cap
of 25 members. Traverse members explicitly. T1 already needs `Chat.Read`, which
covers the member read; the narrower members-only permission is
`Chat.ReadBasic`.

For every chat, traverse all Graph-visible retained message pages and preserve
provider continuation links verbatim. "All" means all records the selected
Graph API still exposes in the authorized scope, not an assertion that Microsoft
retains or returns every message ever created.

Chat membership alone is not a semantic grouping edge. Chat messages do not
use the channel `replyToId` threading model; chat replies can instead surface a
`messageReference` attachment that must be preserved as an explicit relation
candidate.

### 3.2 Teams, channels, and shared channels

Do not use `/me/joinedTeams` as the completeness root. For the signed-in
user, `/me/teamwork/associatedTeams` includes directly joined teams plus host
teams reached through shared channels. For each directly associated team,
enumerate `allChannels` (or the equivalent `channels` plus `incomingChannels`)
so incoming shared channels are not lost. For a hosted shared channel, preserve
the `sharedWithTeams` topology.

Treat these endpoints as **discovery inventories**, not complete entity
snapshots. `associatedTeamInfo` carries only association-oriented team fields,
and Microsoft documents that team list responses populate only a subset of the
`team` resource. For each directly accessible discovered team, fetch
`GET /teams/{team-id}` under `Team.ReadBasic.All` and preserve the detail
response separately. If an associated host team reached only through a shared
channel cannot be retrieved as a full team with the current user token, retain
the `associatedTeamInfo` evidence plus an explicit partial-detail limitation.

Likewise, channel list/allChannels/incomingChannels currently return
`layoutType=null`. Fetch `GET /teams/{team-id}/channels/{channel-id}` for each
accessible discovered channel to hydrate meaning-bearing channel properties
such as layout type. Expensive optional fields such as channel `summary` or
`email` should be selected only when their product value is accepted; omission
must be explicit rather than silently treating the list projection as complete.

Preserve standard/private/shared channel type, host tenant/team identity, and
membership context. For shared/private channels, capture both direct members
and `allMembers`. The latter includes indirect access paths and can return the
same person multiple times through different source teams; preserve each
membership path and its `@microsoft.graph.originalSourceMembershipUrl` rather
than deduplicating to one user.

A documented Graph known issue affects cross-tenant `incomingChannels` and
`allChannels`: the returned channel `@odata.id` can contain a
`/tenants/{tenant-id}` segment that fails when called with the current token.
Preserve the raw `@odata.id` as evidence, but a provider path helper may apply
Microsoft's documented removal of that segment for the follow-up request. This
is a resource-link workaround, not permission to rewrite opaque
`@odata.nextLink` values.

T2 complete delegated permissions:

- `Team.ReadBasic.All`
- `Channel.ReadBasic.All`
- `ChannelMessage.Read.All`
- `TeamMember.Read.All`
- `ChannelMember.Read.All`

The last two and `ChannelMessage.Read.All` require administrator consent in the
delegated permission model. If the company cannot approve them, record the
resulting roster/membership/message coverage gap explicitly instead of silently
calling the reduced profile complete.

### 3.3 Channel messages

The team/channel messages endpoint yields channel root messages. For every root,
explicitly traverse its replies collection. Never assume root listing includes
all replies.

Later A2 can map the exact root/reply edge to teams_channel_reply_to.

### 3.4 Message fidelity

Do not reduce a Teams message to id plus body. Preserve raw provider evidence
and meaning-bearing fields including creation/edit/delete/modified timestamps,
etag, message type, system-event detail, sender, `onBehalfOf` attribution when
present, body/content type, mentions, reactions, message history, importance,
subject/summary, attachments, scope, channel `replyToId`, and web URL.

`messageHistory` is an activity/action history (for example reaction changes);
it is **not** a history of previous message bodies. Under ordinary delegated
list/read/change-notification APIs, the store can preserve only message
body/versions that msgloom actually observes, keyed by scoped identity and
provider version/etag; it must not claim those APIs reconstruct unseen edits.

A separate **application-only retained-message** lane is materially different.
When the tenant has an applicable Teams retention policy, Microsoft's Export
APIs document that `getAllRetainedMessages` can return soft-deleted messages
and previous edited versions. Chat retained messages require `Chat.Read.All`;
channel retained messages require `ChannelMessage.Read.All`. This lane is
optional/admin-controlled and must preserve retention-policy coverage, time
limits, private/shared-channel storage limitations, and any migration cutoffs.
It must never be used to overstate the history available from delegated T1/T2.

System-event messages are source evidence, not noise. They can describe
membership, calls, recordings, pins, tabs, apps, team, and channel lifecycle.

Message IDs must be scoped to their chat/channel/reply context rather than
treated as globally unique.

### 3.5 Attachments and forwarding

A `chatMessageAttachment` can represent more than a file. The stable schema
and Teams messaging overview include at least:

- `reference` for a SharePoint/OneDrive file link;
- `forwardedMessageReference`;
- `messageReference`, used when a chat replies to a specific message;
- `meetingReference`, whose content can carry an Exchange event ID;
- `tabReference`;
- Bot Framework cards;
- code-snippet and announcement cards;
- Microsoft Loop `application/vnd.microsoft.card.fluidEmbedCard`;
- other app-attributed attachment content.

Unknown future/content types must be retained as raw provider values rather than
dropped.

A contentUrl proves a reference exists; it does not prove the bytes currently
at the target equal what existed when the message was posted.

Required model:

1. save the Teams message and attachment/reference metadata;
2. classify the reference;
3. resolve Microsoft-hosted content only through an authorised provider API;
4. save resolution evidence and version facts;
5. retain explicit resolved, denied, missing, stale, or not-attempted state.

Forwarded content must remain distinct from newly authored content.

### 3.6 Hosted content

Inline Teams-hosted content is a separate chatMessageHostedContent resource.
Files are not hosted content; they are stored in SharePoint/OneDrive.

For hosted content: save message evidence, enumerate hosted content, fetch
supported bytes, and save each response independently. Link the hosted-content
evidence to the **triggering observed message record**, but do not claim the
returned bytes are provider-version bound to that exact message etag/body
version: the hosted-content GET is addressed by message ID + hosted-content ID
and exposes no historical-version selector.

Microsoft documents `ConsistencyLevel: eventual` as an option when retrieving
hosted content for edited or deleted messages. Provider request helpers should
support that header deliberately and persist the retrieval timestamp/response
evidence. Hosted-content retrieval is not supported for messages in deleted
threads; record that case as an explicit unrecoverable provider limitation
rather than treating the content as an empty attachment.

### 3.7 Files

Channel files are SharePoint-backed; the channel filesFolder API exposes the
storage driveItem. Chat file references can target OneDrive or SharePoint.

Never hand an arbitrary Teams contentUrl to a generic downloader. Resolve
Microsoft-hosted references through Graph. Keep site/drive/item identity,
version/etag facts, evidence, saved bytes, and explicit failure state.

Broader file permissions such as Files.Read.All must be an optional profile,
not silently added to core chat/channel access.

### 3.8 Pinned messages, tabs, apps, tags, and permission grants

Pinned chat messages are a stable v1.0 read surface and are available under
Chat.Read. Capture the pin relation separately from the underlying message so a
later unpin does not erase the historical message observation.

Tabs are stable v1.0 resources for chats/channels and use TeamsTab.Read.All for
delegated read access. Installed apps have narrower per-scope read permissions,
including TeamsAppInstallation.ReadForUser, TeamsAppInstallation.ReadForChat,
and TeamsAppInstallation.ReadForTeam. Prefer these scoped read permissions over
legacy broad Group.Read.All or Directory.Read.All alternatives.

Teams tags and tag members are stable v1.0 resources under TeamworkTag.Read.
Tags are audience/context evidence, not automatic Topic identity.

Resource-specific permission grants can reveal which apps have access to a chat
or team. They are useful security/context evidence when their existing scoped
read permission is already enabled; do not request a broader permission only to
collect permission-grant metadata.

### 3.9 Targeted messages and beta-only personalization surfaces

Targeted messages are user-specific messages in group chats/channels, for
example bot authentication prompts or new-member summaries. Microsoft exposes
userTeamwork/getAllTargetedMessages in v1.0, but it has no delegated permission;
it requires application TeamworkTargetedMessage.Read.All. Therefore targeted
messages belong to the future application-only completeness profile, not T1.

The user chat-list section model (teamworkSection/teamworkSectionItem) currently
remains beta. The tenant custom-emoji directory also remains beta. Preserve any
custom emoji that appears in ordinary stable message bodies/hosted content, but
do not introduce beta-only directory or section APIs into the production A1
implementation. Re-evaluate them at T0 if Microsoft promotes them to v1.0.

Microsoft's old teamworkDevice beta management API was documented as deprecated
by November 2025 and unsupported afterward. Device inventory/management is also
an administrative surface rather than msgloom work content, so it is excluded
unless Microsoft publishes a current supported replacement and a concrete
product need appears.

## 4. Meetings and calendar boundary

There is no single independent Teams calendar store.

### 4.1 User calendar

Scheduled Teams meetings normally exist as Outlook/Exchange events. Existing A1
Outlook Calendar remains the owner. Do not duplicate those records in Teams
storage.

### 4.2 Team/group calendar

A team is backed by a Microsoft 365 group. Group calendar surfaces such as
groups/{team-id}/events and groups/{team-id}/calendarView are useful but belong
to the group/calendar API and permission boundary. Microsoft 365 group
conversations are likewise a group/Outlook surface and must not be substituted
for Teams channel messages.

### 4.3 Channel Calendar

Treat Channel Calendar as Teams tab/context metadata. Resolve actual events via
supported Outlook, group-calendar, and onlineMeeting resources rather than
inventing a second calendar model.

### 4.4 Online meetings and artifacts

A meeting chat is a Teams chat with chatType=meeting; onlineMeeting is a
separate resource. Preserve both and link them.

Optional read profiles can add:

- OnlineMeetings.Read
- OnlineMeetingArtifact.Read.All
- OnlineMeetingTranscript.Read.All
- OnlineMeetingRecording.Read.All

Attendance, transcripts, and recordings have separate availability and
retention constraints. Missing, expired, or policy-blocked artifacts remain
explicit gaps.

Meeting Q&A export and call records are application-only/admin-oriented
surfaces and belong to a later separate lane.

### 4.5 Webinars and town halls

Microsoft Graph models Teams webinars and town halls as virtual-event resources,
separate from ordinary onlineMeeting objects. The virtualEvent base has webinar
and town-hall derived types with sessions, presenters, schedules, settings, and
registration-related resources.

Delegated work/school read access to webinar/town-hall event metadata uses
VirtualEvent.Read; personal Microsoft accounts are not supported. The exact
registration APIs are asymmetric: reading one registration can allow delegated
VirtualEvent.Read, while listing complete registration collections is currently
application/RSC-only. Therefore the first delegated meeting lane may capture
event/session/presenter metadata but must not claim complete registrant coverage.

Treat webinar/town-hall chat and attendance/artifacts according to their own
message/meeting-artifact permissions and link them to the virtual event. Do not
flatten webinar, town hall, online meeting, calendar event, and meeting chat into
one record.

## 5. Planner, OneNote, and Shifts

These appear in Teams but are independent Graph resource families.

- Planner: acquire basic group/team plans, buckets, tasks, and details under its
  own contract. Do not confuse Planner with Microsoft To Do. Standard Graph
  Planner does not cover premium Planner plans/tasks.
- OneNote: group/site notebooks use the group/site OneNote resource families;
  use an independent read permission and parser.
- Shifts: team schedules expose not only shifts/scheduling groups/time-off and
  open/swap/offer requests, but also time cards/time-clock state and related
  schedule settings. `Schedule.Read.All` covers the read-only schedule/time-card
  surfaces selected for msgloom. `workforceIntegration` is a separate v1.0
  teamwork resource with `WorkforceIntegration.Read.All` and can describe
  external workforce-system callback configuration; include it only if that
  integration metadata has product value. Treat all of this as obligation/state
  data, not chat content.

## 6. Presence, Viva Learning, activity feed, and calling

### 6.1 Presence

Microsoft Graph exposes the signed-in user's Teams presence through /me/presence
with delegated Presence.Read. Presence is highly mutable contextual state, not a
message and not durable evidence of what a user knew at an earlier time. If
enabled, save timestamped observations and do not use presence to infer Topic
identity, responsibility, or message receipt.

### 6.2 Viva Learning

The Teams API overview explicitly lists Viva Learning integration. Graph exposes
learning providers/content through the employeeExperience resource family;
reading learning content uses LearningContent.Read.All. Treat Viva Learning as
an adjacent optional source, not part of chat/channel persistence.

### 6.3 Teams activity feed

The Microsoft Graph permissions reference now contains delegated
`TeamsActivity.Read` for reading the signed-in user's teamwork activity feed,
but this review did not locate a stable v1.0 read endpoint whose public contract
matches that permission. Do not infer an endpoint from the permission name.
Keep activity-feed acquisition as a T0 documentation gap until the exact stable
read API, pagination, retention, and permission contract are located.

The separate `TeamworkUserInteraction.Read.All` permission likewise indicates
possible user-to-user Teams interaction data, but no production collector is
authorized until its exact stable resource API and product meaning are
verified. Sending activity-feed notifications remains out of scope because A1
is read-only.

### 6.4 Calls and call records

Calling/IVR is a separate Cloud Communications API family. Interactive calling
operations are write/action capabilities and are outside this read-only A1 lane.

Call records are read-only telemetry, but Microsoft documents them as
application-permission-only with CallRecords.Read.All and tenant-wide scope;
delegated permissions are not supported. They therefore remain in the future
admin-approved application profile rather than the normal company-user Teams
spider.

## 7. Viva Engage

Viva Engage is integrated into the Teams experience but is a separate service
and data model.

Graph v1.0 exposes Viva Engage employee-experience/community APIs under
/employeeExperience, with network-mode restrictions. The reviewed Graph v1.0
surface does not provide a simple complete signed-in-user message/feed export.

Legacy Viva Engage/Yammer Core REST APIs expose feeds/messages but Microsoft
states they are not intended for bulk export. Whole-network export uses the
Viva Engage Data Export APIs and requires Verified Administrator privileges.

Therefore reserve a future microsoft engage lane rather than embedding Engage
in a Teams spider. The delegated Graph `Community.Read.All` permission itself
requires administrator consent. Before implementation, determine:

1. whether the company Engage network is native mode;
2. whether msgloom needs only the signed-in user's visible communities/feed or
   administrator-level network archival;
3. which Graph/REST/export permission model is acceptable.

## 8. Permission profiles

Avoid one giant consent request.

### T1 core chats

- Chat.Read

### T2 core teams/channels

Complete T2:

- `Team.ReadBasic.All`
- `Channel.ReadBasic.All`
- `ChannelMessage.Read.All`
- `TeamMember.Read.All`
- `ChannelMember.Read.All`

`ChannelMessage.Read.All`, `TeamMember.Read.All`, and
`ChannelMember.Read.All` require delegated administrator consent. A
company-approved reduced T2 may omit roster/member scopes, but the live
acceptance report must then label membership coverage incomplete.

### T3 Teams context

Candidate delegated scopes:

- `TeamworkTag.Read` — administrator consent required;
- `TeamsTab.Read.All` — administrator consent required;
- `TeamsAppInstallation.ReadForUser` — no administrator consent required;
- `TeamsAppInstallation.ReadForChat` — no administrator consent required;
- `TeamsAppInstallation.ReadForTeam` — administrator consent required.

Pinned chat-message state is already covered by T1 `Chat.Read`. Beta-only user
sections and the custom-emoji directory are not enabled in this profile.

Resource-specific permission-grant reads have a documentation transition to
resolve at T0: current v1.0 endpoint pages still list app-installation read
permissions, while the permissions reference exposes narrower
`ResourceSpecificPermissionGrant.ReadForChat` / `...ReadForTeam` delegated
permissions. Do not request both or guess which one is effective; pin the exact
v1.0 endpoint/permission contract immediately before implementation.

### T4 meeting and virtual-event artifacts

Candidate delegated scopes:

- `OnlineMeetings.Read` — no administrator consent required;
- `OnlineMeetingArtifact.Read.All` — no administrator consent required;
- `OnlineMeetingTranscript.Read.All` — administrator consent required;
- `OnlineMeetingRecording.Read.All` — administrator consent required;
- `VirtualEvent.Read` — administrator consent required.

These consent requirements are independent even though the resources all appear
inside the Teams meeting experience. A company-approved reduced T4 must label
which artifact classes are unavailable rather than treating "meeting access" as
one permission.

Complete virtual-event registration enumeration can require application/RSC
access and therefore is not implied by this delegated profile.

### T5 adjacent Microsoft 365 surfaces

These are independent opt-in provider surfaces, not one consent bundle:

- group calendar via `Group.Read.All` — administrator consent required;
- SharePoint/team files via `Files.Read.All` where that broad file profile is
  selected — no delegated administrator consent required by the permissions
  reference, but company SharePoint policy can still restrict effective access;
- OneNote via `Notes.Read` for the selected group/site endpoints — no delegated
  administrator consent required; recheck the exact endpoint at T0 because the
  permission description and multi-location OneNote endpoint surface are broad;
- Planner via `Tasks.Read` — no delegated administrator consent required;
- Shifts schedule/time-card state via `Schedule.Read.All` — administrator
  consent required; optional `workforceIntegration` metadata uses its separate
  `WorkforceIntegration.Read.All` permission and must be rechecked at T0;
- signed-in-user presence via `Presence.Read` — no administrator consent
  required;
- Viva Learning content via `LearningContent.Read.All` — administrator consent
  required.

Do not request `Group.Read.All` merely because some Planner/Shifts APIs list it
as a higher-privileged alternative when their dedicated read permission is
sufficient.

### Future application-only profile

Never enable implicitly. It may include:

- user chat `getAllMessages` and user chat delta under application
  `Chat.Read.All`;
- channel `getAllMessages` under application `ChannelMessage.Read.All` (the
  documented export covers public/private channel messages and is not a
  substitute for delegated shared-channel traversal);
- chat/channel `getAllRetainedMessages` when retention policy and compliance
  requirements justify historical edited/deleted versions;
- targeted messages via `TeamworkTargetedMessage.Read.All`;
- complete virtual-event registration exports;
- tenant-wide exports, meeting Q&A export, and call records.

This requires a separate application identity/admin-approval design and its own
source-identity key scheme. Retained/export coverage is policy/time dependent
and must not be merged into delegated completeness claims.

## 9. Proposed Scrapy topology

Do not build a monolithic Teams spider.

Future provider-only package:

```text
microsoft_graph/
  items/teams/
    chat.py
    channel.py
    message.py
    context.py
  spiders/teams/
    base.py
    chat.py
    channel.py
    meeting.py
```

Candidate msgloom spiders:

- microsoft_teams_chat_discover
  - one-on-one/group/meeting chats;
  - explicit members;
  - all Graph-visible retained message pages in the authorized scope;
  - attachments and hosted content.

- microsoft_teams_channel_discover
  - direct and associated/shared teams;
  - all channel kinds;
  - roots and every reply page;
  - membership/topology.

- microsoft_teams_context_discover
  - optional tags/tabs/app installations/permission grants;
  - pinned-message relations under the core chat permission.

- microsoft_teams_meeting_discover
  - optional onlineMeeting/artifacts;
  - webinar/town-hall virtual-event metadata when T4 is enabled;
  - link to Outlook Calendar rather than duplicate it.

Planner, OneNote, Shifts, group calendar, and broad SharePoint file acquisition
remain separate resource spiders/adapters even if the CLI groups them under
scrapy microsoft teams.

No persistence schema is approved in this planning round.

## 9.1 Thin message_ingest rule

The Teams `message_ingest` layer must be intentionally small and should reuse
the existing A1 pipeline chain rather than create another acquisition framework.

Target ownership:

```text
microsoft_graph/
    - Teams scopes, paths, projections, and query helpers
    - provider protocol validation and pure payload parsers
    - provider dataclasses/item constructors
    - existing Graph auth/retry/error/diagnostics/fingerprinting
        |
        v
message_ingest/spiders/microsoft/teams/
    - select source ID and acquisition intent
    - own Scrapy callbacks and traversal scheduling
    - emit RawHttpEvidenceItem before parsing each response
    - call pure provider parsers/item constructors
    - yield semantic items and provider-built follow-up requests
    - own msgloom run/completion semantics
        |
        v
RawEvidencePipeline (existing, priority 200)
        |
EvidenceLinkPipeline (existing, priority 250)
        |
TeamsPipeline (new, priority 300)
    - type dispatch only
    - await shared catalog write lock
    - publish bounded persistence stats
        |
TeamsStore
```

The Teams Item Pipeline must **not**:

- construct Graph URLs;
- implement pagination;
- authenticate;
- retry Graph requests;
- parse provider JSON;
- classify Graph system-event payloads;
- interpret mentions, reactions, attachments, or hosted-content structures;
- resolve SharePoint/OneDrive URLs;
- perform A2 grouping or semantic processing.

Provider parsing/path mechanics belong in `microsoft_graph/`.
Business-state persistence belongs in the Teams store.

Prefer one small Teams persistence pipeline over one pipeline per Teams
sub-resource. If `process_item()` starts accumulating provider logic, move
that logic back to the reusable Graph framework before continuing.

The application spiders should remain thin, but they **must own the callbacks
that see Scrapy Responses** so they can preserve the established
evidence-before-semantics ordering without making `microsoft_graph/` depend on
msgloom. Minimize callback code by calling pure provider helpers; do not hide
the callback itself behind a framework layer that cannot emit msgloom evidence.

### 9.2 Existing Scrapy integrity invariants

Teams must reuse, not recreate, the current A1 integrity mechanisms:

- project setting `CONCURRENT_ITEMS = 1` is a **correctness invariant**: callback
  output is processed serially so a yielded `RawHttpEvidenceItem` finishes the
  priority-200 pipeline before its dependent semantic item begins. Do not
  override it for Teams. Raising it later requires an explicit durable evidence
  dependency mechanism.
- `RawEvidencePipeline` must complete file+SQL persistence before returning;
  `EvidenceLinkPipeline` must continue validating that every non-null semantic
  evidence ID already exists before the Teams persistence pipeline runs.
- `MicrosoftGraphIntegrityExtension` already marks `spider_error`,
  `item_error`, and `item_dropped`; request/download terminal failures are
  marked by the msgloom Graph spider errback. Teams must remain an instance of
  that application Graph spider so these signals apply.
- any future Teams checkpoint, subscription cursor, or authoritative promotion
  may commit only after native `spider_idle`, `spider.run_failed is False`, and
  the shared catalog write lock is free, following the established To Do /
  Contacts fail-closed pattern. Initial observation-based Teams discovery has
  no absence promotion.

`JOBDIR` is not silently supported just because framework requests use named
callbacks. The first Teams spiders must either reject `JOBDIR` explicitly or
qualify it with a real pause/resume fixture that proves all callbacks/errbacks
are bound spider methods, `cb_kwargs`/meta are pickle-safe, continuation URLs
resume correctly, and no provider checkpoint is inferred from scheduler state.
One JOBDIR belongs to one spider/job only; do not add a custom scheduler.

## 10. Incremental strategy

The first company-account implementation should use delegated UI-aligned APIs:

- list chats plus per-chat messages;
- list visible teams/channels plus roots/replies.

For later continuous operation:

1. obey the Teams platform polling rule: do not repeatedly poll a resource for
   change more than once per day unless a specific API documents a different
   supported pattern;
2. use chat-message `lastModifiedDateTime` date-range reads where the stable API
   supports them; ordinary channel root listing does not expose an equivalent
   general date filter;
3. use delegated per-chat/per-channel change notifications for fresher message
   changes where supported;
4. persist the raw notification before it changes durable message state;
5. normally follow created/updated notifications with a targeted Graph GET or
   reconciliation read, unless included resource data is intentionally accepted
   as the source payload;
6. treat a provider `deleted` notification as potentially authoritative
   deletion evidence: Microsoft does not guarantee a later list/read will still
   return a deleted message;
7. evaluate application-only user chat export/delta separately;
8. do not implement the overview's advertised "channel messages /delta" until
   T0 resolves the current documentation inconsistency: the overview links to
   the user-chat delta API, whose v1.0 endpoint is application-only.

Notifications are therefore both triggers **and provider evidence**. They are
not ordinary business state by themselves, but a deletion event can be the only
remaining provider declaration of deletion and must not be discarded merely
because a follow-up GET fails.

Subscription health is itself coverage state. Persist subscription ID/resource,
creation/expiration/renewal timestamps, reauthorization/subscription-removal
lifecycle evidence, and the last known continuous-delivery window. Microsoft
explicitly documents periods in which notifications can be lost during
reauthorization/removal recovery, and webhook delivery can also drop
notifications. Teams `chatMessage` supports `subscriptionRemoved` lifecycle
events but the generic `missed` lifecycle event is not currently documented for
Teams messages. Therefore a delivery gap might not be fully enumerable.

Subscription planning must also respect provider limits. Microsoft currently
documents a tenant-wide quota of 10,000 active Teams subscriptions shared across
Teams resource types. Current Microsoft pages disagree on maximum lifetime for
Teams chat/channel/message subscriptions: the general Graph subscription table
lists 4,320 minutes (three days), while the Teams change-notification overview
still states 60 minutes. Do not hard-code either value from this plan. T0 must
re-read the exact current resource-specific contract and tests must derive
renewal timing from the accepted limit. Rich-notification subscriptions have
their own shorter generic lifetime constraints.

After any known or suspected gap, reconcile the current readable state where
possible and mark the intervening history **incomplete/unknown**. A later GET
cannot prove that an intermediate edit/delete never occurred. Never restore a
gap-free completeness claim merely because current-state reconciliation
succeeds.

## 10.1 Initial state and deletion semantics

The first delegated Teams implementation is **observation/version based**, not
an authoritative whole-account absence snapshot.

- Persist every observed message/resource version and its evidence.
- Promote explicit current projections only from observed provider facts.
- Do not mark a chat, channel, member, or message deleted merely because it is
  absent from a later list; loss of access, federation, membership changes,
  retention, and API visibility can all produce absence.
- Mark message deletion only when the provider exposes `deletedDateTime`, a
  supported delta/tombstone contract is proven, or a persisted change
  notification explicitly reports `changeType=deleted`.
- Preserve old observed content after deletion; deletion changes current state,
  not evidence history.
- Record coverage windows and provider-retention limitations so "complete"
  always means complete over the Graph-visible scope actually traversed.

## 11. Synthetic validation before live access

Synthetic gates are **profile scoped**. Optional T3/T4/T5 work must not block
core T1/T2 company acceptance.

### 11.1 Mandatory core T1/T2 fixtures

Before company testing of the core profile, cover:

1. one-on-one chat;
2. group chat with more than 25 members;
3. meeting chat;
4. federated members;
5. standard channel and multi-page replies;
6. private channel;
7. shared channel plus associated host team;
8. incoming shared channel;
9. full-detail team hydration after `associatedTeams`;
10. full-detail channel hydration after list/allChannels;
11. edited message with two separately observed etag/body versions;
12. deleted message observed directly;
13. deleted-message change notification with no successful readback;
14. subscription reauthorization/removal or simulated notification-delivery gap
    followed by current-state reconciliation and explicit incomplete-history
    status;
15. reactions/messageHistory changes without inventing old body versions;
16. system event;
17. user/channel/team mentions and custom-emoji message content;
18. `reference` file attachment;
19. `forwardedMessageReference`;
20. chat-reply `messageReference`;
21. `meetingReference` linked by Exchange event ID;
22. `tabReference` retained even if T3 tab resolution is disabled;
23. Loop `fluidEmbedCard`, code-snippet, announcement, ordinary, and unknown
    card/app content retained without loss;
24. hosted image/code content on normal and edited/deleted messages with no
    false exact-version claim;
25. hosted-content failure for a deleted thread;
26. denied/missing/stale file reference;
27. pinned chat-message relation;
28. direct and indirect shared-channel `allMembers` with multiple membership
    paths for one user;
29. cross-tenant `incomingChannels` resource-link workaround;
30. collection pagination and reply pagination;
31. malformed provider envelopes;
32. request/callback/pipeline failure, including `spider_error`, `item_error`,
    and item drop blocking any promotion/checkpoint;
33. evidence-before-semantics committed ordering under
    `CONCURRENT_ITEMS = 1`;
34. duplicate message IDs in different scopes;
35. empty chat/team/channel sets;
36. explicit JOBDIR rejection, or a qualified pause/resume pagination case if
    JOBDIR support is enabled.

All core crawl tests must prove raw evidence is durably available before
dependent semantic storage and provider continuation URLs are replayed verbatim.

### 11.2 Optional-profile fixtures

Each optional profile gates only itself:

- **T3 context:** tabs, app installations, tags, resource-specific permission
  grants, and their exact consent requirements.
- **T4 meeting/virtual events:** onlineMeeting, attendance, transcript,
  recording, webinar/town-hall metadata/session linkage, policy/expiry gaps,
  and incomplete registration coverage.
- **T5 adjacent:** only the selected SharePoint files, Planner, OneNote, Shifts,
  group calendar, Presence, Viva Learning, or Engage lanes being implemented.
- **Application-only:** export/delta, targeted messages, retained-message edited
  history, registration export, Q&A, and call records. Retention-dependent
  fixtures must prove policy/time coverage limitations.

Beta-only sections/custom-emoji-directory APIs and the currently beta
approvalItem read surface are not production acceptance fixtures until a stable
v1.0 API is selected.

## 12. Future company-account live gate

This worktree must not merge until a real work/school tenant is tested.

Minimum sequence:

1. company-approved public client/application;
2. build a tenant consent-capability matrix before requesting scopes; identify
   which delegated permissions require administrator consent and which the
   company security policy refuses;
3. work/school authentication and source binding;
4. consent T1 only and validate chat acquisition;
5. prove one-on-one/group/meeting chats where available;
6. obtain administrator approval for complete T2, or record an explicit reduced
   T2 coverage decision;
7. validate direct teams, associated/shared host teams, standard/private/shared
   channels, incoming channels, team rosters, and channel `allMembers` where
   examples exist;
8. inspect edits/deletes/replies/attachments/hosted content and at least one
   notification-driven update/delete flow if company policy permits webhook
   acceptance;
9. inspect evidence/catalog privacy;
10. repeat acquisition and verify stable/idempotent observed state without
    inferring deletion from ordinary absence;
11. full regression/static gates;
12. independent implementation review;
13. explicit merge decision.

T3-T5 remain independently gated.

## 13. Later implementation sequence

No implementation is authorized in this round.

- T0: recheck official docs and freeze permission contracts.
- T1: provider paths/scopes/pure parsers/items under `microsoft_graph`.
- T2: thin evidence-first chat callbacks for member/message/reference/hosted
  content acquisition.
- T3: thin evidence-first team/channel callbacks for shared topology,
  membership, roots and replies.
- T4: additive durable Teams storage and pipeline after item contracts settle.
- T5: tags/tabs/apps/permission grants and pinned-message context.
- T6: onlineMeeting, webinar/town-hall, attendance/transcript/recording linkage.
- T7: separate SharePoint files, Planner, OneNote, Shifts, group calendar,
  Presence, and Viva Learning.
- T8: optional change notifications/application-only export/targeted messages/
  registration export/Q&A/call records; re-evaluate beta-only sections and
  custom-emoji directory if they become stable.
- T9: company-account acceptance; keep branch isolated until accepted.

## 13.1 Parallel ChatGPT implementation workflow

When implementation is authorized, maximize dependency-safe parallelism.

Do **not** use traditional local Codex/Claude sub-agents. Every delegated
engineering/review lane must run in a separate ChatGPT **Chat** conversation,
created and driven through the installed `chatgpt-web-operations` workflow.
The local coordinator remains responsible for repository integration, tests,
shared files, and final decisions.

Use one dedicated ChatGPT Project for the Teams implementation round. Every
worker prompt starts with a unique `TASK_ID`, has one finite lane contract,
and returns a compact machine-readable result. Each worker gets its own git
worktree/branch derived from the Teams integration branch unless its task is
strictly read-only.

There is no artificial four-worker cap. Start every independent lane that has
its prerequisites satisfied. Actual simultaneous sends may be bounded by the
available ChatGPT browser/session capacity; excess independent lanes should be
queued immediately rather than serialized by project policy.

### Parallel wave P0 — framework qualification

Run these independently as soon as implementation starts:

- **P0-A framework extension map:** inspect the actual pinned
  `microsoft_graph/` Graph-over-Scrapy framework and assign each Teams
  capability to an existing extension point: spider/path builder, protocol,
  item, downloader middleware, fingerprint, or application adapter.
- **P0-B auth/scope contract:** map delegated Teams scopes into the existing
  `MicrosoftGraphAuthSession` and resource-spider scope declaration without
  creating a second auth flow.
- **P0-C provider surface inventory:** map every selected official v1.0 Teams
  API to reusable `microsoft_graph` modules and identify only the genuinely
  missing framework primitives.
- **P0-D synthetic transport harness:** design local Graph fixtures that run
  through the real Scrapy Downloader, existing auth-disabled fixture mode,
  retry/error middleware, request identity, and evidence pipeline.
- **P0-E independent architecture review:** reject any design that duplicates
  an existing Graph framework feature or pushes provider mechanics into
  `message_ingest`.

P0-A/B/C define the shared framework contract. P0-D/E can proceed in parallel.

The coordinator alone integrates shared framework exports/settings and any
cross-lane component registration after the P0 findings converge. No new Graph
client dependency or alternative transport is expected.

### Parallel wave P1 — provider capabilities

After the Graph-framework/auth contract is frozen, maximize real parallelism
without assigning the same shared module to multiple workers.

First parallel tranche:

- **P1-MESSAGE-PRIMITIVES:** pure `chatMessage` parsing, scoped identity,
  observed-version contract, system events, mentions/reactions,
  attachment/reference taxonomy, hosted-content metadata.
- **P1-CHAT-TOPOLOGY:** chat paths, chat/member inventory, query/date-range
  helpers, pins.
- **P1-CHANNEL-TOPOLOGY:** associated teams, all/incoming/shared channels,
  team/channel membership including `allMembers`, roots/reply path helpers.
- **P1-CONTEXT:** tags, tabs, app installations, permission grants.
- **P1-MEETING:** onlineMeeting, attendance, transcript, recording, webinar and
  town-hall provider primitives.
- **P1-ADJACENT:** read-only design/provider primitives for group calendar,
  files, Planner, OneNote, Shifts, Presence, Viva Learning; preserve separate
  source ownership.
- **P1-APPONLY:** read-only design/tests for application-only capability
  boundaries only; do not enable these permissions.

After `P1-MESSAGE-PRIMITIVES` stabilizes, run in parallel:

- **P1-CHAT-COMPOSITION:** bind chat topology to the common message/content
  contract.
- **P1-CHANNEL-COMPOSITION:** bind channel roots/replies/topology to the common
  message/content contract.

This split prevents CHAT, CHANNEL, and CONTENT workers from simultaneously
editing the same message model/parser while still allowing topology and
adjacent-resource work to proceed in parallel.

### Parallel wave P2 — application integration

P2 uses lane-level dependency edges rather than one global "P1 complete" gate.

File ownership is immutable for a worker round. The coordinator alone edits
shared catalog bases/registries, migration registries, package exports, project
settings, public command dispatch, and cross-lane documentation.

Dependencies:

- **P2-PERSISTENCE:** starts after the common message identity/version contract
  plus chat/channel item contracts are stable. Own dedicated Teams
  models/store/pipeline modules and focused persistence tests.
- **P2-CHAT-SPIDER:** requires `P1-CHAT-COMPOSITION` plus the persistence item
  contract; owns only chat spider modules and chat crawl tests.
- **P2-CHANNEL-SPIDER:** requires `P1-CHANNEL-COMPOSITION` plus the persistence
  item contract; owns only channel spider modules and channel crawl tests.
- **P2-CONTEXT-SPIDER:** optional T3; requires its provider primitives and
  persistence contract; gates only T3.
- **P2-MEETING-SPIDER:** optional T4; requires its provider primitives and
  persistence contract; gates only T4.
- **P2-A2-HANDOFF:** remains read-only/design+tests until Teams persistence
  schema/item contracts land. It then owns dedicated Teams reader/handoff tests
  and must not edit shared persistence models/registries in parallel.
- **P2-FIXTURES:** is split by profile and dependency. Core chat fixture crawls
  require P2-PERSISTENCE + P2-CHAT-SPIDER; core channel fixture crawls require
  P2-PERSISTENCE + P2-CHANNEL-SPIDER. Optional fixture suites wait only for
  their corresponding profile.

Every P1/P2 worker branch must include focused lane-local tests (pure path,
parser, identity, item, or store tests as appropriate) and static checks before
integration. P2 end-to-end fixtures supplement those tests; they are not the
first place provider-contract defects should be discovered.

The coordinator resolves cross-lane integration and runs the combined
regression/static gates after each convergence point.

### Parallel wave P3 — convergence and review

Run independently:

- full code review of provider boundary;
- security/privacy/permission review;
- evidence/replay review;
- Scrapy lifecycle/cancellation review;
- synthetic-fixture completeness review;
- Python 3.12/3.13/3.14 compatibility review.

Repair lanes may run in parallel where findings touch disjoint modules.

### Company-account wave

Live acceptance remains serial at the permission boundary: consent T1, validate,
then T2, then optional T3-T5. Static analysis and review of later profiles can
still run in parallel while one live profile is being validated.

## 14. Explicit non-goals

Until separately approved, do not:

- send/edit/delete/pin/react to messages;
- mutate teams/channels/chats/membership;
- create/modify meetings;
- mutate files, Planner, OneNote, or Shifts;
- request ReadWrite permissions;
- install/uninstall Teams apps;
- use beta APIs merely for convenience, including current Teams section and
  tenant custom-emoji-directory APIs;
- revive deprecated Teams device-management Graph APIs;
- use application permissions to bypass a delegated-consent problem;
- claim personal-account Teams support;
- merge this branch into master.

## 15. Official Microsoft references reviewed

Primary Microsoft Learn material reviewed for this plan:

- Teams API overview and Teams messaging overview
- chat resource, list chats, list chat members, list chat messages
- team/channel resources, joined teams, associated teams, list channels
- channel messages and message replies
- chatMessage, chatMessageAttachment, chatMessageHostedContent
- hosted-content list/get and channel filesFolder
- Teams change notifications
- chat-message delta and chat getAllMessages
- onlineMeeting, attendance, transcripts, and recordings
- group calendar/calendarView
- Planner overview
- OneNote overview
- Shifts list/read APIs
- Teams presence APIs
- Viva Learning learning-provider/content APIs
- virtualEvent webinar/town-hall/session/registration APIs
- pinned chat-message APIs
- targeted-message userTeamwork API
- Teams tabs, installed-app, permission-grant, and teamwork-tag APIs
- beta teamworkSection and custom-emoji APIs (inventory only)
- deprecated teamworkDevice API documentation (exclusion evidence)
- Teams calling and call-record APIs
- Viva Engage Graph overview/community APIs
- Viva Engage Core REST and Data Export APIs
- meeting Q&A export
- call records

### Exact Microsoft Learn links

Core Teams and messages:

- <https://learn.microsoft.com/en-us/graph/change-notifications-lifecycle-events>
- <https://learn.microsoft.com/en-us/microsoftteams/export-teams-content>
- <https://learn.microsoft.com/en-us/graph/api/channel-getallretainedmessages?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/chat-getallretainedmessages?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/channel-getallmessages?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/channel-get?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/team-get?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/manage-channel-memberships>
- <https://learn.microsoft.com/en-us/graph/api/channel-list-allmembers?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/team-list-incomingchannels?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/known-issues?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/resources/teams-api-overview?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/teams-messaging-overview>
- <https://learn.microsoft.com/en-us/graph/api/resources/chat?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/chat-list?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/chat-list-members?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/chat-list-messages?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/chat-list-pinnedmessages?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/userteamwork-getalltargetedmessages?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/resources/team?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/user-list-joinedteams?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/associatedteaminfo-list?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/channel-list?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/channel-list-messages?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/chatmessage-list-replies?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/resources/chatmessage?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/resources/chatmessageattachment?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/resources/chatmessagehostedcontent?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/chatmessagehostedcontent-get?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/channel-get-filesfolder?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/team-list-members?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/teamworktag-get?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/teamworktagmember-list?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/chat-list-tabs?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/channel-list-tabs?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/team-list-installedapps?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/chat-list-installedapps?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/userteamwork-list-installedapps?view=graph-rest-1.0>

Incremental/application-only surfaces:

- <https://learn.microsoft.com/en-us/graph/teams-changenotifications-chatmessage>
- <https://learn.microsoft.com/en-us/graph/teams-changenotifications-chat>
- <https://learn.microsoft.com/en-us/graph/teams-changenotifications-team-and-channel>
- <https://learn.microsoft.com/en-us/graph/api/chatmessage-delta?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/chats-getallmessages?view=graph-rest-1.0>

Meetings and virtual events:

- <https://learn.microsoft.com/en-us/graph/api/resources/onlinemeeting?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/onlinemeeting-get?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/meetingattendancereport-list?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/onlinemeeting-list-transcripts?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/onlinemeeting-list-recordings?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/cloud-communications-virtual-events-overview>
- <https://learn.microsoft.com/en-us/graph/api/resources/virtualevent?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/resources/virtualeventwebinar?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/resources/virtualeventtownhall?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/virtualeventwebinar-get?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/group-list-calendarview?view=graph-rest-1.0>

Adjacent Microsoft 365 products:

- <https://learn.microsoft.com/en-us/graph/api/approvalsolution-list-approvalitems?view=graph-rest-beta>
- <https://learn.microsoft.com/en-us/graph/approvals-app-api>
- <https://learn.microsoft.com/en-us/graph/api/resources/workforceintegration?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/resources/timecard?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/resources/planner-overview?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/planner-list-plans?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/resources/onenote-api-overview?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/onenote-list-pages?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/schedule-list-shifts?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/presence-get?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/learningprovider-list-learningcontents?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/resources/engagement-api-overview?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/employeeexperience-list-communities?view=graph-rest-1.0>

Inventory/exclusion evidence:

- <https://learn.microsoft.com/en-us/graph/api/resources/teamworksection?view=graph-rest-beta>
- <https://learn.microsoft.com/en-us/graph/api/userteamwork-list-sections?view=graph-rest-beta>
- <https://learn.microsoft.com/en-us/graph/api/resources/teamworkcustomemoji?view=graph-rest-beta>
- <https://learn.microsoft.com/en-us/graph/api/teamworkdevice-list?view=graph-rest-beta>
- <https://learn.microsoft.com/en-us/graph/api/cloudcommunications-getallonlinemeetingmessages?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/graph/api/callrecords-callrecord-get?view=graph-rest-1.0>
- <https://learn.microsoft.com/en-us/rest/api/yammer/yammer-core-apis>
- <https://learn.microsoft.com/en-us/rest/api/yammer/data-export-apis>

The implementation round must reopen the exact endpoint pages immediately before
coding because Microsoft Graph permissions and resource behavior can change.
