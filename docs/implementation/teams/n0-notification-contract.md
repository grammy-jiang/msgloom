# Teams notification contract recheck

Checked on 2026-10-04. This record prepares N1/N2. It does not qualify a
webhook, create a subscription, or enable renewal. Initial T1/T2 discovery
remains independent of notification infrastructure.

## Selected resources and permissions

Basic per-resource notifications are the initial local target. A chat uses
`/chats/{chat-id}/messages` with delegated `Chat.Read`. A channel uses
`/teams/{team-id}/channels/{channel-id}/messages` with delegated
`ChannelMessage.Read.All`; channel notifications include replies. Both
support created, updated, and deleted changes. Personal accounts are not
supported. Tenant-wide application subscriptions and beta user-wide examples
are outside this program. The message-specific documentation requires
`lifecycleNotificationUrl` for a requested expiration beyond one hour.
[Message notification contract](https://learn.microsoft.com/en-us/graph/teams-changenotifications-chatmessage).

## Lifetime conflict and implementation decision

The v1.0 subscription reference currently lists 4,320 minutes for Teams
`chatMessage`. Its separate rich-notification limit is 1,440 minutes. It also
states that an expiration requested less than 45 minutes ahead is raised to
45 minutes.
[Subscription reference](https://learn.microsoft.com/en-us/graph/api/resources/subscription?view=graph-rest-1.0).

The Teams notification overview still states a 60-minute maximum. Thus the
P0 discrepancy remains reproducible. Neither page proves the other is obsolete.
[Teams notification overview](https://learn.microsoft.com/en-us/graph/teams-change-notification-in-microsoft-teams-overview).

Decision: do not add a provider maximum or an automatic renewal timer in N1/N2.
Accept an explicitly supplied subscription identity and its recorded validity
window. Persist server-returned expiration separately from receipt time. A
future live subscription manager must qualify its requested lifetime against
the authorized tenant and retain the actual response. A conservative initial
request inside both documented limits can qualify that request, but cannot
prove the provider's maximum. Renewal must use the actual accepted expiration
and a documented safety margin. The unresolved maximum does not block local
notification evidence, targeted readback, or coverage-gap tests.

## Quota and lifecycle

The current quota is one subscription per app and chat/channel combination.
The organization limit is 10,000 across Teams notification resource types,
not 10,000 separately for each type. Additional creation can fail with 403.
No quota probe or subscription creation was performed.
[Notification quotas](https://learn.microsoft.com/en-us/graph/change-notifications-overview).

`reauthorizationRequired` applies to all resources. Teams `chatMessage`
supports `subscriptionRemoved`. The documented `missed` support is limited
to Outlook messages, events, and personal contacts. A Teams delivery gap must
therefore also be representable from local delivery/validity evidence; do not
pretend Graph promises a Teams `missed` event. Reauthorization/removal can
interrupt delivery. Persist that uncertainty before reconciliation and retain
it after a successful current-state read.
[Lifecycle support and recovery](https://learn.microsoft.com/en-us/graph/change-notifications-lifecycle-events).

## Delivery and security boundary

The webhook guide now describes a three-second initial response allowance,
retry attempts for up to four hours, and a ten-second retry timeout. A slow
endpoint can cause delayed or dropped notifications. A successful current
GET cannot reconstruct every lost intermediate edit or deletion. Future live
intake must durably queue accepted envelopes before acknowledging work that
has not yet been processed. Validation handshakes, delivery acknowledgments,
and subscription operations remain separate from message acquisition.
[Webhook delivery](https://learn.microsoft.com/en-us/graph/change-notifications-delivery-webhooks).

Basic notifications require `clientState` validation. Rich notifications add
JWT validation and encrypted resource data, including certificate management.
They require verification of the token signature, lifetime, audience, and
Graph publisher identity. N1/N2 should reject rich envelopes instead of
accepting encrypted bytes as message data. Basic resource metadata can identify
a read target but is not a substitute for a full message response.
[Resource-data security](https://learn.microsoft.com/en-us/graph/change-notifications-with-resource-data).

## Existing code and required local qualification

Reuse `microsoft_graph/protocol/notifications.py` for basic envelope and
constant-time `clientState` validation. It intentionally does not establish
subscription ownership, tenant binding, message scope, or rich-token trust.
The Teams adapter must enforce those boundaries. Match each event to an
explicit trusted subscription record; never let an envelope's resource URL
select an arbitrary fetch or another source account.

The current Teams deletion and coverage stores already require committed
evidence and preserve old bodies and sticky incomplete history. Existing
tests construct those items directly. They do not qualify ingress or
reconciliation. Before closing fixture cells 13 and 14, prove:

1. Raw received bytes become durable evidence before any deletion or coverage
   item. Preserve inbound-request provenance; do not label a webhook payload
   as a Graph GET response. Keep secrets out of diagnostics and semantic rows.
2. Wrong client state, unknown subscription, wrong tenant, mismatched
   chat/channel, malicious resource URL, and rich-envelope input cannot cause
   a semantic write or Graph request.
3. Created/updated notifications schedule a provider-built targeted GET
   through the existing Scrapy Graph transport. A GET failure never creates
   a message body or an implicit deletion.
4. An authenticated explicit deletion persists even when readback returns
   404/403. Prior body observations and both evidence records remain readable.
5. Reauthorization, removal, expiry, and simulated delivery interruption keep
   history incomplete after current-state reconciliation. No native Teams
   `missed` support is claimed.
6. Duplicate/reordered envelopes and repeated reconciliation retain immutable
   facts. One envelope can contain multiple events for the same scope, so the
   adapter must preserve each event without violating the coverage store's
   current one-fact-per-scope-and-evidence identity.

N1/N2 production work starts after basic chat/channel discovery is accepted.
The coordinator must freeze a disjoint file manifest and the raw-evidence
contract before dispatch. Public CLI wiring, shared evidence types, and any
shared registry edits remain coordinator-owned. No webhook exposure or
subscription mutation is authorized by this local fixture record.

## Remaining gates

- Local N1/N2 implementation and meaningful raw-intake/reconciliation tests.
- Independent P3 provider, security, evidence, and history review on the final
  repaired candidate.
- Authorized tenant T1/T2 and notification-driven acceptance when company
  policy permits it. The existing live prerequisites remain unavailable.
- A separately qualified subscription manager before any automatic renewal.
