# Microsoft Graph live acceptance

This is an operator-only, read-only remote acceptance workflow. It is not part
of CI and it does not create, modify, move, or delete Microsoft data.

The harness reuses the normal msgloom Graph authentication, source-identity,
retry, evidence, catalog, Spider, and Pipeline paths. It does not implement a
second Graph client.

## Preconditions

Configure the same environment used for normal Microsoft acquisition, at
minimum:

~~~text
MSGLOOM_MS_CLIENT_ID=<public-client-id>
~~~

Run the offline authentication diagnosis first:

~~~bash
uv run scrapy microsoft auth status
~~~

Choose a timezone-aware Calendar window that is small enough for a smoke test.
A window containing at least one event gives the strongest Calendar full
coverage.

## Dry run

Dry-run prints the planned phases and never touches Graph:

~~~bash
uv run python scripts/microsoft-live-acceptance.py \
  --dry-run \
  --calendar-start 2026-09-27T00:00:00+10:00 \
  --calendar-end 2026-10-04T00:00:00+10:00
~~~

## Live run

Live execution requires explicit opt-in:

~~~bash
uv run python scripts/microsoft-live-acceptance.py \
  --confirm-live \
  --calendar-start 2026-09-27T00:00:00+10:00 \
  --calendar-end 2026-10-04T00:00:00+10:00
~~~

By default the harness creates an isolated directory under
var/live-acceptance/UTC-timestamp/. It never uses the normal application
catalog.

The workflow is:

1. Microsoft profile through the shared Graph lifecycle;
2. one page of Mail discovery;
3. targeted Mail Full-v1 refresh for one discovered message, when available;
4. Calendar inventory;
5. one bounded Calendar window;
6. targeted Calendar Full-v1 refresh for one event from that isolated catalog,
   when available;
7. privacy-safe catalog/evidence checks and acceptance.json output.

Use --require-mail-message or --require-calendar-event when an empty resource
set should fail the acceptance run rather than skip the targeted full phase.

The JSON summary contains phase names, pass/skip status, counts and booleans.
It does not include usernames, Graph resource IDs, provider account keys, or
token material.

## Shared/delegated qualification

Use `--mailbox USER_ID_OR_UPN` to run the same bounded acceptance workflow
against a delegated/shared Outlook mailbox. Prefer an Entra object ID and use a
source ID dedicated to that target. The Microsoft profile phase still describes
the signed-in account; subsequent Outlook phases use the delegated target.

The privacy-safe acceptance summary records only `delegated_target: true`; it
does not print or persist the mailbox locator in `acceptance.json`.

## Cleanup

The remote workflow is read-only, so no Microsoft-side fixture cleanup is
required. After reviewing acceptance.json, remove the isolated local output
directory when its evidence is no longer needed.

Do not add this harness to ordinary CI. It uses real delegated credentials and
real account data, and its purpose is deployment/operator qualification rather
than deterministic unit/integration testing.
