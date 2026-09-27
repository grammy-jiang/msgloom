# Microsoft Graph authentication

msgloom keeps Microsoft Graph authentication inside dedicated Scrapy downloader
middleware. Spiders do not acquire tokens and Item Pipelines do not handle
credentials.

## Authentication selection

Select the authentication flow per crawl through:

`MSGLOOM_MS_AUTH_METHOD`

Supported values today:

- `device_code` (default)
- `interactive`

Both authentication middleware classes are registered in Scrapy's downloader
middleware component list. During component construction each reads the final
crawler settings and raises Scrapy `NotConfigured` unless its `auth_method`
matches `MS_GRAPH_AUTH_METHOD`. Consequently exactly one authentication
implementation participates in the request/response chain, while command-line
or project-level setting overrides can select the flow without changing Spider
code.

## Device code

`device_code` is the default for Raspberry Pi, SSH, CLI, and other headless
execution environments.

The flow is:

1. Try MSAL silent token acquisition from the local token cache.
2. If no usable cached token or refresh token can satisfy the request, start
   Microsoft device-code authentication.
3. The user signs in and grants consent in a browser on any device.
4. MSAL stores the resulting account/token state in the local token cache.
5. Later runs normally use silent acquisition.

## Interactive authorization code + PKCE

`interactive` is intended for a desktop environment with a browser.

MSAL's `acquire_token_interactive` opens browser-based sign-in and performs the
public-client authorization-code flow with PKCE. The app registration must
include the public-client redirect URI required by Microsoft (normally
`http://localhost`).

Like device code, later runs first attempt silent token acquisition from the
same MSAL token cache.

## App registration

For a msgloom public-client app intended to support work/school and personal
Microsoft accounts:

1. Register an application in Microsoft Entra.
2. Supported account types: accounts in any organizational directory and
   personal Microsoft accounts.
3. Enable public client flows.
4. Add the Microsoft Graph delegated permissions required by the enabled
   msgloom capabilities. Outlook mail currently requires `Mail.Read`.
5. Do not create or embed a client secret for these public-client flows.

Default authority:

`https://login.microsoftonline.com/common`

A personal-account-only installation may use `consumers` instead.

## Configuration

Required for live Microsoft Graph acquisition:

`MSGLOOM_MS_CLIENT_ID=<application-client-id>`

Optional:

`MSGLOOM_MS_AUTH_METHOD=device_code`

`MSGLOOM_MS_AUTHORITY=https://login.microsoftonline.com/common`

`MSGLOOM_MS_USERNAME=<account-email>`

`MSGLOOM_MS_TOKEN_CACHE=var/auth/msal-token-cache.json`

`MSGLOOM_MS_USERNAME` is only a selector for an account already known to MSAL
and a login hint for interactive browser authentication. It is not a password
credential.

## Shared delegated-authentication behavior

Both current authentication middleware share only authentication concerns:

- acquire and cache delegated tokens with MSAL;
- select the configured cached account;
- attach a Bearer token only to `graph.microsoft.com` requests;
- remove the transient `Authorization` header on the response path before
  Scrapy's optional filesystem HTTP cache persists request headers;
- on the first Graph HTTP 401, clear the in-memory token and retry once with a
  forced silent refresh;
- allow a second 401 to pass through instead of creating an authentication
  retry loop.

Authentication retries are separate from Microsoft Graph 429 throttling. The
Graph throttling middleware and Scrapy's generic RetryMiddleware remain distinct
components.

HTTP 401 and 403 are excluded if the development HTTP cache is explicitly
enabled. HTTP cache is disabled by default for normal Outlook operation.

The serialized MSAL token cache is written with user-only file permissions
(`0600`).

## Evidence boundary

Access tokens and authentication request state are never evidence. The raw
network-evidence downloader middleware persists response representation but does
not persist the transient `Authorization` request header.

## Other Microsoft authentication flows

The middleware selection model is intentionally extensible, but additional
flows should only be added when their Microsoft-supported scenario matches a
msgloom source.

### Legacy ROPC / username-password

Not implemented today. Microsoft currently deprecates ROPC, recommends more
secure flows, and documents that ROPC does not support personal Microsoft
accounts. If msgloom later needs legacy work/school-account compatibility, it
can be added as a separate explicitly selected middleware rather than changing
the supported public-client middleware.

### Client credentials

Not implemented for the current personal Outlook collector. Client credentials
is an app-only daemon flow for organizational tenants. It has no signed-in user,
so it is not a drop-in replacement for the current `/me` delegated-mail path.
If msgloom later supports organization-wide app-only acquisition, it should use
its own authentication middleware and source semantics.

### Integrated Windows authentication / broker

These are platform- and account-environment-specific and are not useful for the
current Raspberry Pi target. They can be added later without changing the
Spider because authentication is isolated behind downloader middleware.

## Microsoft first-party client IDs

Microsoft-owned public-client IDs can be useful for diagnostics and historical
compatibility testing. The current live development smoke tests use the
Microsoft Graph Command Line Tools public client id, but msgloom's long-term
deployment model should use its own app registration so application identity,
permissions, and consent remain under the owner's control.
