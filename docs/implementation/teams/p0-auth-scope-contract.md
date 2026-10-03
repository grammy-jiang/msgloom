# P0-B auth, scope, and source-identity contract

## Qualification

The independent ChatGPT auth worker returned PASS for baseline
`7b9a7572b935f0e6ce6a96057b55951190afc8bf`. The finished transcript confirms
`gpt-5-6-thinking` / `max`. The coordinator checked the actual auth, source
identity, settings, and tests. This accepted contract includes the corrections
below. It is input to P0-E closure, not permission to start P1.

## Delegated profiles

| Profile | Requested Graph scopes | Delegated administrator consent |
| --- | --- | --- |
| T1 | `Chat.Read` | No by permission metadata |
| Complete T2 | `Team.ReadBasic.All`, `Channel.ReadBasic.All`, `ChannelMessage.Read.All`, `TeamMember.Read.All`, `ChannelMember.Read.All` | Required for the message and two member scopes |

The two basic-read T2 scopes do not require administrator consent by permission
metadata. Tenant consent policy can be stricter. Scope metadata does not prove
resource access. See the current [Microsoft permissions reference](https://learn.microsoft.com/en-us/graph/permissions-reference).
The [chat endpoint](https://learn.microsoft.com/en-us/graph/api/chat-list?view=graph-rest-1.0)
does not support delegated personal Microsoft accounts. A `common` authority
does not establish Teams personal-account support.

These are separate requested scope sets. T1 does not add T2 scopes. T2 does not
add `Chat.Read`. Neither adds `User.Read`, `.default`, application permissions,
write permissions, or optional-profile permissions. Existing token grants can
contain earlier consent history; this contract controls requested Graph scopes.
MSAL's own authentication protocol scopes remain part of the existing flow.

No reduced T2 profile is selected for implementation. Any future approved
reduction may omit roster/member scopes only and must label that coverage
incomplete. `ChannelMessage.Read.All` remains required for channel messages.

## Existing extension points

The provider profile declares its exact `graph_permissions` tuple. Its
`required_graph_permissions(settings)` exposes that tuple. The application
Teams spiders must inherit
`message_ingest.spiders.microsoft._graph.MicrosoftGraphSpider`. Its
`update_settings()` enables Graph auth and sets `MS_GRAPH_SCOPES` at spider
priority. The provider base only supplies defaults for standalone consumers.

Scrapy settings priority still applies. A command-line `MS_GRAPH_SCOPES` can
override a spider-priority declaration. Therefore the declaration alone is not
an enforcement mechanism. Teams application initialization must validate the
effective scope set against the selected profile before the auth session or
requests start. Reject missing, extra, or incompatible Graph scopes with a
clear configuration error. Keep standalone provider override behavior intact;
do not change the shared auth lifecycle or the generic Graph spider contract.

The coordinator owns shared settings and package exports. Add one resource
setting, `MSGLOOM_TEAMS_SOURCE_ID`, with default `microsoft-teams-default`.
Both application spiders map it to `MSGLOOM_SOURCE_ID`, following the existing
To Do and Contacts pattern. Deliberate source configuration must remain
consistent across T1 and T2. Do not silently derive separate chat and channel
sources.

Reuse `MicrosoftGraphAuthSession` and `scrapy microsoft auth ...`.
`auth status` inspects local cache state; `auth clear` clears the selected local
cache. Neither proves tenant authorization. Interactive and device-code sign-in
stay in the current crawler lifecycle. There is no Teams auth middleware,
credential client, retry loop, or second Graph HTTP transport.

## Source identity and cache concurrency

`MicrosoftGraphSourceIdentityExtension.spider_opened()` attaches the shared
crawler auth session to `SourceIdentityService` before scheduled requests run.
The account key is the opaque MSAL `home_account_id`. The key scheme remains
`msal_home_account_id/sha256-v1`. The catalog stores a domain-separated SHA-256
digest, not the raw account key. A mismatched account fails the existing startup
gate and cannot silently rebind the source.

All native delegated Teams lanes use the same logical source and account
binding. Application-only acquisition needs a separate identity design and is
not enabled. Adjacent Microsoft 365 products retain their own source ownership.

`MicrosoftGraphAuthSession._save_token_cache()` writes, flushes, syncs, and
atomically replaces its private cache file. Its async lock is process-local.
It provides no cross-process cache merge or lock. Live crawls sharing
`MSGLOOM_MS_TOKEN_CACHE` must run serially, or use distinct cache paths.
Synthetic auth-disabled crawls can run independently with isolated state.

## Evidence and integrity

Keep `CONCURRENT_ITEMS = 1`, the existing evidence/link pipelines, the
application Graph errback, and `MicrosoftGraphIntegrityExtension`.
Callbacks yield raw evidence before parsing the response. Durable evidence must
exist before dependent semantic storage. Scrapy's async output prefetch can
advance a callback before the yielded item's write completes. Do not claim
durable-write-before-parser ordering. See the exact explanation in the
[fixture contract](p0-fixture-harness.md).

Request identity remains in the existing representation-aware fingerprint
layer and application source/catalog context. Authorization tokens must not
become request identity. Retry policy stays in the existing downloader stack.
Initial discovery records observations and does not infer deletion from absence.

## Focused verification required downstream

The worker's claim that baseline scope tests were absent was incorrect for the
complete repository. `tests/test_graph_framework_spider.py` already checks
scope defaults, explicit consumer overrides, and mailbox scope selection.
`tests/test_graph_user_provider.py` also checks scope settings. The worker's
124-file source archive was not a complete test inventory.

Retain those tests. Add Teams-specific tests when the classes exist:

- T1 declares and requests exactly `Chat.Read`.
- Complete T2 declares and requests exactly the five frozen scopes.
- Both application spiders resolve the same default Teams source.
- An incompatible effective scope override fails before authentication.
- An exact explicit scope set remains valid under normal settings priority.
- Existing generic source-binding mismatch and private-cache tests stay green.

No production source, credentials, or auth behavior changes in P0-B.
Real work/school T1 then T2 acceptance remains blocked by the documented missing
tenant configuration and consent evidence. Local cache inspection is not live
acceptance.
