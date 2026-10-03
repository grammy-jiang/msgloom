# Contacts sync implementation note

**Lane:** W-CONTACTS
**Date:** 2026-09-29
**Status:** implementation and personal-account live acceptance completed

## Scope and permissions

Personal Contacts acquisition is read-only and declares only delegated
`Contacts.Read`. It does not add Graph writes, directory contacts, enterprise
directory scopes, Outlook mailbox target binding, Teams, OneNote, SharePoint,
Planner, or Topic generation.

The provider framework exposes these v1.0 reads:

- `/me/contacts` for the default Contacts collection.
- `/me/contactFolders` for top-level custom-folder inventory.
- `/me/contactFolders/{id}/childFolders` for recursive custom folders.
- `/me/contactFolders/{id}/contacts` for contacts in a concrete custom folder.
- `/me/contactFolders/{id}/contacts/delta` only for a validated concrete
  custom-folder ID.

Folder IDs are accepted as raw provider IDs and encoded exactly once when a
path is constructed. Provider `@odata.nextLink` and `@odata.deltaLink` values
are opaque and are replayed verbatim.

Microsoft Graph documentation used for the provider contract:

- List contacts:
  [Microsoft Graph: list contacts](https://learn.microsoft.com/en-us/graph/api/user-list-contacts?view=graph-rest-1.0)
- List contact folders:
  [Microsoft Graph: list contact folders](https://learn.microsoft.com/en-us/graph/api/user-list-contactfolders?view=graph-rest-1.0)
- List child contact folders:
  [Microsoft Graph: list child contact folders](https://learn.microsoft.com/en-us/graph/api/contactfolder-list-childfolders?view=graph-rest-1.0)
- Contact delta:
  [Microsoft Graph: contact delta](https://learn.microsoft.com/en-us/graph/api/contact-delta?view=graph-rest-1.0)
- Delta query behavior:
  [Microsoft Graph: delta query overview](https://learn.microsoft.com/en-us/graph/delta-query-overview)

## Privacy projection

The selected contact projection is intentionally bounded to stable identity and
context fields needed by the implementation plan. `personalNotes` is excluded
from `$select` because no explicit policy acceptance for that field exists.
The raw provider JSON returned by the selected request is retained unchanged as
evidence; semantic projection does not normalize falsey or nested values.

## Snapshot correctness

Default contacts and custom-folder inventory are separate collection surfaces.
No provider default-folder ID is invented, and custom-folder enumeration is not
treated as proof of default Contacts identity.

`microsoft contacts discover` performs complete recursive traversal and
additive state capture without absence inference. `microsoft contacts sync`
uses the same traversal and additionally promotes authoritative presence at
native Scrapy idle only after durable completion rows prove all of the
following:

1. the default contacts collection reached its terminal page;
2. the top-level custom-folder inventory reached its terminal page;
3. every folder sighted in the run reached terminal pages for both its child
   folder collection and its contacts collection;
4. request, callback, item-processing, and item-drop integrity remained clean;
5. all resource and completion items finished the awaited catalog pipeline.

All Contacts mutations acquire SQLite writer intent through
``Catalog.writer_session()`` before reading mutable state. This shared catalog
boundary serializes independent Catalog instances and restores connection state
on commit, rollback, or a failed transaction start.

Snapshot and custom-folder delta runs capture one durable shared promotion
generation before traversal. The first promotion advances that generation;
overlapping stale runs fail without changing presence or committed cursors.
Delta entries also obey observation-time ordering, including equal-time
last-wins order within the same delta round.

Presence promotion is one SQL transaction. Older/equal snapshot run start times
cannot replace a newer committed run. Missing resources are marked absent only
during a clean authoritative sync; provider rows remain preserved for history.
Discovery and incomplete runs never infer absence.

`JOBDIR` is rejected for Contacts spiders because no persistent-scheduler
resume contract has been qualified.

## Custom-folder delta

Contacts delta is resource-specific and deliberately not the default correctness
path. The delta spider requires an explicit concrete custom-folder ID. The
default Contacts collection continues to use authoritative snapshots until
manager live validation establishes a real provider folder identity/capability;
there is no guessed well-known default folder ID.

Sparse delta entries, including `@removed` tombstones, are staged first.
A terminal opaque cursor is staged separately. At clean native idle the store
checks the prior checkpoint revision, applies staged observations in provider
order, merges sparse updates with preserved provider state, applies tombstones,
and advances the opaque cursor in the same transaction. A failed or incomplete
round cannot promote its cursor. The next round reuses the exact committed
`@odata.deltaLink`.

The delta spider is intentionally not added to the public Microsoft command
hierarchy in this lane. It remains directly invocable as
`microsoft_contacts_delta` for the manager's synthetic/local capability probe
with a concrete custom-folder ID.

## Component-layout integration note

The manager should merge these lane-owned additions into the component layout
rather than replacing `docs/component-layout.md` wholesale:

- `microsoft_graph/items/contacts.py` and
  `microsoft_graph/spiders/contacts.py`: reusable provider-only Contacts
  projection/path layer with no application or SQLAlchemy imports.
- `message_ingest/spiders/microsoft/contacts/`: recursive snapshot and
  custom-folder delta spiders.
- `message_ingest/items/microsoft/contacts.py`: application provenance and
  lifecycle items.
- `message_ingest/catalog/models/microsoft/contacts.py` and
  `message_ingest/catalog/stores/microsoft/contacts.py`: additive current
  state, sightings, presence, completion, and checkpoint persistence.
- `message_ingest/pipelines/microsoft/contacts.py`: awaited shared-lock
  persistence.
- `message_ingest/extensions/microsoft/contacts/`: clean-idle snapshot and
  delta promotion gates.
- `message_ingest/sync/microsoft/contacts/`: Contacts-specific scope
  validation.
- `message_ingest/commands/microsoft/contacts.py`: public discover/sync
  dispatch.

Shared wiring changes are limited to Contacts command selection/dispatch,
Contacts source/checkpoint settings, and Contacts lifecycle extension registration.

## Manager live acceptance

Read-only personal-account acceptance completed on 2026-10-03 using the
documented Microsoft Graph Command Line Tools development public client. The
account granted only `Contacts.Read` for this lane.

An isolated `contacts discover` run completed two real Graph requests with
HTTP 200 responses: the default Contacts collection and the top-level contact
folder inventory. Both terminal collection-completion items and their raw
network evidence were persisted, and source identity was bound successfully.

A subsequent authoritative `contacts sync` against the same isolated catalog
again completed both Graph requests with HTTP 200 responses. The clean-idle
snapshot gate committed one promotion generation with no request, callback,
pipeline, or item-drop failure. The tested account contained no contacts or
custom contact folders, so the live run validates authentication, transport,
terminal traversal, evidence persistence, source identity, and empty-snapshot
promotion. Recursive non-empty folder traversal, pagination, removals, and
failure gates remain covered by the synthetic integration fixtures.

No Microsoft-side data was created, modified, moved, or deleted. No write
permission was requested.
