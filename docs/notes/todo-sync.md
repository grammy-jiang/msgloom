# Microsoft To Do authoritative snapshot sync

This lane implements plan Section 6 snapshot correctness only. It does not
implement task-list or task delta and does not expand the delegated permission
surface beyond the existing read-only `Tasks.Read` contract. The manager-owned
T0 probe succeeded with ``Tasks.Read`` on 2026-09-29. Delta remains optional
and deferred; full snapshots provide the correctness path.

## Runtime contract

`scrapy microsoft todo sync --page-size 100` runs
`microsoft_todo_sync`, a thin subclass of the existing discovery spider. The
four discovery callbacks remain the single traversal implementation. Sync mode
marks every Graph request `dont_cache=True` and follows provider
`@odata.nextLink` values verbatim. JOBDIR remains unsupported and is rejected
by both the command and spider boundary.

Each callback emits raw HTTP evidence before semantic items. On the terminal
page of each collection chain, sync mode also emits a traversal-completion item.
The To Do pipeline awaits current-state persistence and then records the
run-scoped sighting under the shared `CatalogService.write_lock`. Completion
items use the same awaited pipeline boundary.

## Durable full-traversal proof

The snapshot store persists four source/run-scoped sighting sets plus terminal
completion rows. A candidate is valid only when durable completions equal the
inventory implied by durable sightings:

- one terminal task-list collection;
- one terminal task collection for every sighted list;
- one terminal checklist collection for every sighted task; and
- one terminal linked-resource collection for every sighted task.

The candidate also requires current-run raw evidence for every completion.
Therefore scheduler emptiness and Scrapy stats are not used as correctness
proof. A missing terminal page, filtered continuation, request/callback error,
pipeline error, or dropped item prevents authoritative promotion.

## Presence and stale-run exclusion

Provider content tables remain historical latest-observation state. Separate
presence tables carry current authoritative membership for list, list/task, and
list/task/relation keys. A clean snapshot reconciles all historical content keys
against the current run's sightings without deleting prior JSON or evidence.

The snapshot extension captures the source revision at `spider_opened`.
At native Scrapy idle, after requests and item-pipeline work are drained, it
verifies the shared write lock is free, then stages and promotes synchronously
before pipeline shutdown can dispose the catalog. Native idle proves that all
item writes finished. Promotion atomically compares and swaps the source
revision while reconciling presence. A competing run with a stale base revision
rolls back before presence changes. Repeating promotion of an already committed
run is idempotent. Newer observation timestamps are not overwritten by older
snapshot observations; equal timestamps use later processing order.

## Failure and privacy boundaries

Shared Graph integrity signals mark request, callback, pipeline, and DropItem
failures on the logical run. Snapshot idle checks that failure state before
candidate creation. Promotion errors also mark the run failed so the Microsoft
command exits nonzero. Stats contain only bounded counters and revision/count
values, never provider identifiers.

## Component-layout integration note

For the shared component-layout document, add the To Do sync spider beside the
existing To Do discovery spider; add the To Do snapshot extension under
application extensions; add `sync/microsoft/todo/snapshots.py` under
application synchronization; and describe the To Do catalog additions as
run-scoped sightings/completions/candidates plus separate current-presence
tables. No `microsoft_graph` framework dependency on application catalog or
SQLAlchemy code is introduced.

## Manager live acceptance

Two read-only personal-account snapshot runs completed on 2026-09-29 with
existing ``Tasks.Read`` consent. The second run preserved the same presence
set and advanced the source revision. No provider mutation or interactive
authentication occurred. Deletions, nested child resources, partial traversal,
and stale-run races remain covered by synthetic fixtures.
