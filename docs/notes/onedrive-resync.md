# OneDrive 410 resync and explicit-content version linkage

This lane implements the OneDrive completion contract from implementation-program
Section 7 without changing Graph permissions or introducing provider writes.

## Staged reset versus current state

A delta request that receives HTTP 410 persists redacted response evidence first.
A reset is accepted only when the response contains exactly one absolute Location
on the configured Graph origin, an existing committed checkpoint revision is
loaded, and no reset has already started in the run. The Location is scheduled
verbatim with cache bypass. Request fingerprints include reset-attempt identity,
so the fresh chain can legally reuse the expired URL while native duplicate
filtering still rejects repeats inside the same attempt.

The 410 starts one durable resync-attempt row. Every returned driveItem is then
stored as an append-only, ordered resync observation keyed by source, run,
attempt, page, and entry position. These rows do **not** update
`onedrive_items`. The old checkpoint and current presence therefore remain
authoritative throughout a partial or failed reset.

At a terminal deltaLink the existing candidate mechanism stages the exact opaque
cursor. Scrapy's native idle gate runs only after pending requests and item
processing are empty. The OneDrive checkpoint extension additionally requires a
clean logical run and a terminal candidate. Promotion is awaited under the shared `CatalogService.write_lock` and performs
revision CAS plus resync materialization in one catalog transaction. A losing/stale CAS rolls back
without applying staged observations.

Winning observations are applied in provider order, so the last occurrence of a
repeated item wins. Sparse provider tombstones preserve useful metadata from an
earlier current/reset observation. Previously current items unseen in the full
enumeration are marked absent through `is_deleted` while their provider
`deleted` facet and raw JSON remain unchanged; this distinguishes inferred
authoritative absence from a provider tombstone and preserves useful metadata.
A metadata observation newer than the reset start is not marked absent. The
checkpoint advances only after these state changes succeed in the same
transaction. Repeated promotion of the same committed candidate is idempotent.

Any invalid/off-origin/missing Location, second 410, missing terminal link,
request/callback failure, item error/drop, pipeline failure, or stale checkpoint
revision blocks authoritative promotion. OneDrive continues to reject JOBDIR.

## Explicit content freshness proof

Explicit content remains opt-in. Before requests are scheduled, the content
spider snapshots any known current driveItem metadata eTag, cTag, observation
time, and evidence ID into callback context. The cTag is retained only as the
documented file-content tag; eTag is the primary whole-item version proof.

Each successful capture appends one `onedrive_content_captures` association
containing digest/size, planning-version facts, safe response ETag when exactly
one URL-free value is present, capture time, run, and evidence ID. The existing
`onedrive_contents` table remains the latest digest/size pointer and no semantic
table stores body bytes or transport URLs. Older capture associations and raw
binary evidence are retained.

`OneDriveStore.content_freshness(item_id)` reports:

- `current` only when current metadata eTag, planned eTag, and response ETag
  are all present and exactly equal, and the item is currently present;
- `stale` when current metadata advanced, the response version mismatches, or
  the current item is deleted/absent;
- `unknown` when metadata/capture linkage or response-version corroboration is
  insufficient to exclude a planning/download race;
- `missing` when no explicit content has been stored.

Freshness is query-only. A stale/unknown result never triggers an automatic
download.

## Integration note

New catalog tables must remain imported through
`message_ingest.catalog.models.__init__` so additive schema creation sees them.
The delta spider selects the OneDrive reset-aware request fingerprinter only for
its own crawl. No global settings or dependency locks are changed.
