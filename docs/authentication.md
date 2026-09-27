# Microsoft Graph authentication and source identity

msgloom separates three concerns:

- `MicrosoftGraphAuthSession` owns crawler-scoped MSAL account/token state.
- downloader auth middleware only attaches/removes Graph credentials.
- `MicrosoftGraphSourceIdentityExtension` verifies the persisted logical source
  before Scrapy begins executing Scheduler requests.

Spiders never acquire tokens and Item Pipelines never handle credentials.

## Authentication and resource scopes

`MSGLOOM_MS_AUTH_METHOD` selects `device_code` (default) or `interactive`.
Both thin downloader adapters borrow the same crawler-scoped auth session.
Set `MSGLOOM_MS_ALLOW_INTERACTIVE_AUTH=false` for unattended jobs so missing
silent credentials fail closed instead of opening an authentication prompt.

Authentication is provider infrastructure, but scopes belong to resources.
Project defaults keep Graph auth/scopes disabled. Outlook Mail declares only
`Mail.Read`, Calendar declares `Calendars.ReadBasic`, and the one-shot
Microsoft profile command declares `User.Read`. Future Graph resources must
continue to own their least-privilege scopes.

## Logical source identity

`MSGLOOM_SOURCE_ID` is a stable msgloom namespace, not a username or token
cache account ID. A `source_bindings` row binds that source to:

- provider (`microsoft_graph` today);
- key scheme (`msal_home_account_id/sha256-v1`);
- domain-separated SHA-256 of the opaque provider account key;
- binding method (`auto_empty` or `bootstrap_attested`);
- original binding timestamp.

The raw Microsoft account key and username are not copied into the catalog.
The MSAL credential cache remains a private credential file and still contains
the account data MSAL needs.

For MSAL 1.39, msgloom treats `home_account_id` as an opaque stable account
key and never parses or normalizes it. This binds the signed-in home account;
it does not prove a tenant-specific target such as a shared mailbox.

## Startup identity gate

For catalog-backed live Graph crawls, the async `spider_opened` gate completes
before the engine executes Scheduler requests. Therefore:

- HTTP-cache hits cannot bypass source verification;
- queued JOBDIR requests cannot execute first;
- externally supplied Authorization cannot select another persisted account;
- gate failures cannot become normal request errbacks/evidence rows.

A failure marks the run failed and closes with `source_identity_failed`.
Outlook custom commands convert final `status=failed` into exit code 1.
Catalog-disabled diagnostics do not persist identity. Tests or controlled
fixtures that intentionally bypass external identity must explicitly set
`MSGLOOM_SOURCE_IDENTITY_REQUIRED=False`; endpoint hostnames never disable the
gate implicitly.

## Account and token pinning

The account being verified must own the token sent to Graph. Existing bindings
select cached accounts by the hashed opaque account key, not username.

For first binding, one cached account may be selected. `MSGLOOM_MS_USERNAME`
can narrow the initial choice, but duplicate matches are rejected. Multiple
cached accounts without a selector are rejected.

When interaction is needed, msgloom deliberately discards the token returned
directly by device-code/browser interaction. It re-reads MSAL account state,
selects one account, and uses `acquire_token_silent_with_error(account=...)`
for that exact account. Only that silently reacquired token is pinned and sent
to Graph. A 401 forced refresh follows the same pinned-account rule.

## Legacy source bootstrap

An empty source auto-binds. A source with historical rows but no binding is
refused because its owner cannot be inferred safely.

Bootstrap is an operator attestation and is not environment-backed. Confirm
the exact source for one invocation, for example:

`-s MSGLOOM_SOURCE_IDENTITY_BOOTSTRAP_CONFIRM=microsoft-outlook-default`

The current historical default database uses `microsoft-outlook-default`.
Confirm the selected Microsoft account owns that data before bootstrap.
Bootstrap never overwrites a binding or rewrites historical rows/checkpoints.

## Cache and JOBDIR isolation

Graph request fingerprints include a digest of the logical source plus the
normalized catalog context, together with the representation-changing
`Accept`/`Prefer` headers. Authorization remains excluded. Different
source/catalog contexts therefore cannot share Graph cache or duplicate-filter
identity; old unscoped Graph cache keys naturally miss.

When JOBDIR is configured, `SourceContextExtension` creates a private marker
before Scheduler construction. It contains only a digest of logical source
plus normalized catalog location. Reusing a JOBDIR with another source/catalog
fails. A non-empty legacy JOBDIR without a marker is refused.

## Configuration

Required for live acquisition:

`MSGLOOM_MS_CLIENT_ID=<application-client-id>`

Common optional settings:

`MSGLOOM_MS_AUTH_METHOD=device_code`

`MSGLOOM_MS_AUTHORITY=https://login.microsoftonline.com/common`

`MSGLOOM_MS_USERNAME=<account-email>`

`MSGLOOM_MS_TOKEN_CACHE=var/auth/msal-token-cache.json`

`MSGLOOM_MS_ALLOW_INTERACTIVE_AUTH=false`

`MSGLOOM_SOURCE_IDENTITY_REQUIRED` defaults to true as a Scrapy setting.
For a controlled fixture or diagnostic that deliberately skips provider-account
binding, override it only for that invocation:

`-s MSGLOOM_SOURCE_IDENTITY_REQUIRED=False`

`MSGLOOM_MS_USERNAME` is only a first-binding selector/login hint. It is not
the persisted source identity and is not a password.

## Credential and evidence boundary

Access/refresh tokens, provider account keys, and interactive auth state are
not evidence. The MSAL cache is replaced atomically through a same-directory
temporary file created as mode `0600`; a failed replacement keeps the old
cache and leaves the in-memory cache dirty for a later retry.

The downloader auth middleware sends bearer credentials only to HTTPS requests
for `graph.microsoft.com`. HTTPS-to-HTTP downgrade requests are rejected.
`Authorization` is removed on both response and downloader-exception paths
before Scrapy's native HTTP-cache recovery or RetryMiddleware can copy/store
the request.

The current cache writer does not merge simultaneous changes from independent
processes. Until cross-process cache locking/merge is added, crawls sharing the
same `MSGLOOM_MS_TOKEN_CACHE` should be scheduled serially or use distinct cache
paths. Source identity still prevents a wrong account from being persisted.

When source identity is required for catalog-backed acquisition, an externally
supplied Authorization header is replaced by the source-pinned token. If source
identity is explicitly disabled, or catalog persistence is disabled, a
diagnostic acquisition may supply its own Authorization header.

Authentication retry is separate from Graph throttling. The first Graph 401
gets one forced refresh; a second 401 passes through normally.

## Future providers/resources

Calendar and delegated Teams can share the same Microsoft home-account binding
while owning their own scopes. App-only Teams acquisition needs a different
key scheme because it has no user home account. A future Google provider can
reuse `SourceIdentityService` while supplying its own stable key scheme.
