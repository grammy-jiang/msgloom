# P0-C API and path contract

**Checked:** 2026-10-03 UTC.
**Worker input:** `7b9a7572b935f0e6ce6a96057b55951190afc8bf`.
**Status:** coordinator-corrected C deliverable; converged P0-E closure PASS.

The independent [P0-C worker](https://chatgpt.com/c/6ac107e5-dfd4-83ec-a2b2-786098d9141a)
returned `FINDINGS`. Its finished transcript records `gpt-5-6-thinking` and
`max`. The coordinator reopened current Microsoft Learn pages, inspected the
existing request helpers, and retained the raw result and source snapshots in
the program workspace. The corrections below supersede the raw worker text.

## Selected contract and ownership

Production selects delegated T1 and complete T2 in the global Graph v1.0
service. T3/T4/T5, application-only acquisition, and beta endpoints remain
unselected. Paths below are relative to `https://graph.microsoft.com/v1.0`.
Provider IDs are opaque path segments. Encode them once when building a path.
Never interpret message, chat, channel, member, or hosted-content IDs as UUIDs.

Use the existing Graph-over-Scrapy request, auth, retry, error, privacy, and
fingerprint components. Provider modules own paths and pure parsers. Application
callbacks own evidence-first traversal. Initial discovery creates observations;
ordinary absence never proves deletion or complete history.

T1 declares `Chat.Read`. Complete T2 declares `Team.ReadBasic.All`,
`Channel.ReadBasic.All`, `ChannelMessage.Read.All`, `TeamMember.Read.All`, and
`ChannelMember.Read.All`. The last three require delegated administrator
consent. Do not combine optional scopes into these profiles. The P0-B contract
owns source binding and auth integration.

## T1 paths

| Operation | GET path | Selected query |
| --- | --- | --- |
| Chat inventory | `/me/chats` | `$top=50` |
| Explicit chat members | `/chats/{chat-id}/members` | None |
| Message inventory | `/chats/{chat-id}/messages` | `$top=50` |
| Targeted message | `/chats/{chat-id}/messages/{message-id}` | None |
| Pins | `/chats/{chat-id}/pinnedMessages` | None |

Chat and message page sizes must be between 1 and 50. Do not expand members;
the expanded member view is capped at 25. Explicit member traversal has no
selected query. Preserve every returned continuation. Pins are relation
observations; they do not replace the message observation. See the official
[chat list](https://learn.microsoft.com/en-us/graph/api/chat-list?view=graph-rest-1.0),
[members](https://learn.microsoft.com/en-us/graph/api/chat-list-members?view=graph-rest-1.0),
[message list](https://learn.microsoft.com/en-us/graph/api/chat-list-messages?view=graph-rest-1.0),
[message GET](https://learn.microsoft.com/en-us/graph/api/chatmessage-get?view=graph-rest-1.0),
and [pins](https://learn.microsoft.com/en-us/graph/api/chat-list-pinnedmessages?view=graph-rest-1.0)
contracts.

The selected optional date-window helper adds these query values to the chat
message collection, using validated UTC bounds with lower less than upper:

```text
$orderby=lastModifiedDateTime desc
$filter=lastModifiedDateTime gt {lower-UTC} and lastModifiedDateTime lt {upper-UTC}
```

The filter and order properties must match or Graph can ignore the filter.
Only descending order is supported. The separate `createdDateTime` filter
supports `lt`; it is not selected for this helper. A strict bounded query is
not proof of continuous history and does not authorize frequent polling.

## T2 paths

| Operation | GET path | Selected query |
| --- | --- | --- |
| Associated teams | `/me/teamwork/associatedTeams` | None |
| Direct-team inventory | `/me/joinedTeams` | None |
| Team detail | `/teams/{team-id}` | None |
| All channels | `/teams/{team-id}/allChannels` | Channel projection below |
| Incoming channels | `/teams/{team-id}/incomingChannels` | Channel projection below |
| Channel detail | `/teams/{team-id}/channels/{channel-id}` | Channel projection below |
| Shared-with topology | `/teams/{team-id}/channels/{channel-id}/sharedWithTeams` | None |
| Team members | `/teams/{team-id}/members` | `$top=999` |
| Direct channel members | `/teams/{team-id}/channels/{channel-id}/members` | `$top=999` |
| All channel members | `/teams/{team-id}/channels/{channel-id}/allMembers` | None |
| Root messages | `/teams/{team-id}/channels/{channel-id}/messages` | `$top=50` |
| Replies | `/teams/{team-id}/channels/{channel-id}/messages/{root-id}/replies` | `$top=50` |
| Root detail | `/teams/{team-id}/channels/{channel-id}/messages/{root-id}` | None |
| Reply detail | `/teams/{team-id}/channels/{channel-id}/messages/{root-id}/replies/{reply-id}` | None |

The associated-team operation documents `/users/{user-id}/teamwork/associatedTeams`;
the delegated `/me` alias selects the signed-in user. Associated teams are the
discovery root. Direct-team inventory establishes direct membership separately;
it cannot establish completeness for shared host teams. Retain association and
detail observations independently. An inaccessible host team remains a partial
observation, not a missing/deleted team. See
[associated teams](https://learn.microsoft.com/en-us/graph/api/associatedteaminfo-list?view=graph-rest-1.0),
[direct teams](https://learn.microsoft.com/en-us/graph/api/user-list-joinedteams?view=graph-rest-1.0),
and [team detail](https://learn.microsoft.com/en-us/graph/api/team-get?view=graph-rest-1.0).

The selected channel `$select` value is:

```text
id,createdDateTime,displayName,description,isArchived,isFavoriteByDefault,layoutType,membershipType,migrationMode,originalCreatedDateTime,tenantId,webUrl
```

These fields appear in the current stable
[channel schema](https://learn.microsoft.com/en-us/graph/api/resources/channel?view=graph-rest-1.0).
List results do not provide full layout detail. Hydrate each accessible channel
with a separate GET. Omit `email`, `summary`, and `moderationSettings` explicitly;
the selected projection is not an exhaustive channel snapshot. Preserve raw
response properties if Graph returns additional fields. See
[allChannels](https://learn.microsoft.com/en-us/graph/api/team-list-allchannels?view=graph-rest-1.0),
[incomingChannels](https://learn.microsoft.com/en-us/graph/api/team-list-incomingchannels?view=graph-rest-1.0),
and [channel detail](https://learn.microsoft.com/en-us/graph/api/channel-get?view=graph-rest-1.0).

`allChannels` includes incoming channels. The incoming inventory also supplies
explicit receiving-team topology evidence. Use host identity for channel
content; preserve the receiving team and discovery path independently.
`sharedWithTeams` applies only to shared channels and requires
`ChannelMember.Read.All` in delegated mode. It is covered by complete T2, not
by channel-basic scope alone. See
[sharedWithTeams](https://learn.microsoft.com/en-us/graph/api/sharedwithchannelteaminfo-list?view=graph-rest-1.0).

Team and direct-channel member page sizes range from 1 to 999. Do not invent
`$top` support for `allMembers`. Preserve direct and indirect paths, including
multiple records for one person and
`@microsoft.graph.originalSourceMembershipUrl`. See
[team members](https://learn.microsoft.com/en-us/graph/api/team-list-members?view=graph-rest-1.0),
[channel members](https://learn.microsoft.com/en-us/graph/api/channel-list-members?view=graph-rest-1.0),
and [allMembers](https://learn.microsoft.com/en-us/graph/api/channel-list-allmembers?view=graph-rest-1.0).

Root and reply page sizes range from 1 to 50. Traverse replies separately for
every root. Do not expand replies and do not invent a channel-root date filter.
See [root messages](https://learn.microsoft.com/en-us/graph/api/channel-list-messages?view=graph-rest-1.0)
and [replies](https://learn.microsoft.com/en-us/graph/api/chatmessage-list-replies?view=graph-rest-1.0).

## Hosted content and message fidelity

Define a message path from one of these exact contexts:

```text
/chats/{chat-id}/messages/{message-id}
/teams/{team-id}/channels/{channel-id}/messages/{root-id}
/teams/{team-id}/channels/{channel-id}/messages/{root-id}/replies/{reply-id}
```

Append `/hostedContents` to enumerate metadata. Append
`/hostedContents/{hosted-content-id}` for a hosted item, and append `/$value`
to that item path for bytes. No query is selected for these requests. Use the
[hosted list](https://learn.microsoft.com/en-us/graph/api/chatmessage-list-hostedcontents?view=graph-rest-1.0)
and [hosted GET](https://learn.microsoft.com/en-us/graph/api/chatmessagehostedcontent-get?view=graph-rest-1.0)
contracts. The currently published Learn GET page documents the optional
`ConsistencyLevel: eventual` header for edited/deleted messages. The downloaded
public repository Markdown copy lacks that header row; use the published Learn
contract and retain this evidence difference.

Set `ConsistencyLevel: eventual` deliberately on hosted item/byte reads. Keep
that policy fixed for core hosted requests and disable response caching for
current observations. Use the existing request builder, then native request
headers; no new transport or middleware is needed. Byte requests use an
appropriate binary Accept value and preserve response Content-Type. Hosted
content in deleted threads is unsupported. Persist an explicit failure state.
Link each retrieval to its triggering message observation and retrieval time.
The API has no selector for the historical message version; bytes are not
provider-version-bound to its etag.

Set `Prefer: include-unknown-enum-members` on channel inventory/detail and on
message list/detail/reply requests. Carry it to continuation requests. This
retains shared-channel membership type and system-event message types. Reuse
the existing `Prefer` representation fingerprint. See the
[channel schema](https://learn.microsoft.com/en-us/graph/api/resources/channel?view=graph-rest-1.0)
and [message schema](https://learn.microsoft.com/en-us/graph/api/resources/chatmessage?view=graph-rest-1.0).

Preserve raw message fields, including `scope`, `webUrl`, `onBehalfOf`, system
events, reactions, mentions, history, and every attachment content type. A chat
`messageReference` is a relation candidate, not a channel reply. Retain file,
forwarded, meeting, tab, Loop, code, announcement, and unknown card values.
File references default to `not-attempted` because broad file acquisition is
unselected. Never fetch an attachment URL or `webUrl` as an arbitrary URL.
See [attachment schema](https://learn.microsoft.com/en-us/graph/api/resources/chatmessageattachment?view=graph-rest-1.0).

## Continuations and resource-link normalization

Replay every `@odata.nextLink` verbatim through `continuation_request()`.
Do not decode, reorder, append, or normalize it. Retain the relevant request
headers and callback context on every page. See
[Graph paging](https://learn.microsoft.com/en-us/graph/paging).

Only the shared-channel resource-link workaround may remove a tenant segment.
Accept the documented trusted shape
`https://graph.microsoft.com/v1.0/tenants/{tenant-id}/teams/{team-id}/channels/{channel-id}`
from an `allChannels` or `incomingChannels` `@odata.id`. Preserve the raw value.
Remove exactly the leading `/tenants/{tenant-id}` path portion for the derived
resource request, preserving the remaining encoded path and query. Reject
credentials, fragments, unexpected origins, and unrelated path shapes as
unresolved resource links. Never apply this helper to continuation links or UI
URLs. See the [documented Graph issue](https://learn.microsoft.com/en-us/graph/known-issues#unable-to-access-a-cross-tenant-shared-channel-when-the-request-url-contains-tenantscross-tenant-id).

## Findings disposition and remaining checks

- **Delta major:** resolved for core by exclusion. The located stable chat
  delta is application-only. No delegated channel delta is frozen. This agrees
  with the design; it does not block list-based core implementation.
- **Activity/interaction:** no stable delegated read contract was established
  for the requested semantics. Neither permission is selected.
- **Permission grants:** the endpoint/reference scope transition remains open
  for optional T3. The raw worker incorrectly called this T5. No grant scope
  or endpoint is selected for core.
- **Notification lifetime:** the general subscription table says 4,320 minutes
  for Teams messages; the Teams overview says 60 minutes. Freeze no maximum
  lifetime constant. N0 must recheck and qualify its contract before renewal
  implementation. The resource-specific message page requires a lifecycle URL
  when requesting more than one hour.
- **Notification scope correction:** notifications are not waived. Fixtures
  for deletion with failed readback and delivery-gap history uncertainty remain
  mandatory. Implement locally executable N0/N1/N2 after basic discovery.
  Reconciliation cannot restore a gap-free history claim. Tenant-permitted
  notification-driven live acceptance remains required before merge.

Notification sources:
[subscription limits](https://learn.microsoft.com/en-us/graph/api/resources/subscription?view=graph-rest-1.0),
[Teams overview](https://learn.microsoft.com/en-us/graph/teams-change-notification-in-microsoft-teams-overview),
[message subscriptions](https://learn.microsoft.com/en-us/graph/teams-changenotifications-chatmessage),
and [lifecycle gaps](https://learn.microsoft.com/en-us/graph/change-notifications-lifecycle-events).

The corrected document, exact A/B/D content, framework input, and corrections
must reach P0-E for closure. No production code or live support is qualified by
this API review alone.
