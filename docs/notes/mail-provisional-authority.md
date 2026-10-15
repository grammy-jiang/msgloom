# Mail provisional authority

Message-delta and folder-delta callbacks retain observations before they own a
cursor generation. These observations cannot change the accepted resource row,
presence, or effective fact. This rule also applies to callbacks that arrive
after a competing run commits.

## Ownership and retained inputs

`mail_authority_observations` stores the original source, logical run, authority
kind, and scope. Message-delta uses the request's original folder ID. It does not
use the message's current parent folder in production. Folder-delta uses the
source's mailbox cursor scope. Each row names its exact immutable fact and
evidence. A local sequence orders applications within that run and scope. The
sequence is not provider order.

The payload retains the original supplied resource and its resolved projection.
Omitted message fields inherit from a pinned accepted row or the same run's
prior primary projection. Explicit null and false values remain explicit.
Membership transitions and primary observations have separate effective keys.
Evidence-free direct observations retain their supplied projection too.

Evidence-backed inputs verify source ownership, saved byte size and digest, and
the resource fields in the original response. Promotion repeats verification
and caches page decoding within its transaction. It never reconstructs a winner
from the losing run's current row or evidence pointer. Canonical evidence may
come from an earlier capture; the fact retains the current logical run.

## Promotion and replay

The existing native idle or deferred Full gate validates completion. Promotion
then reserves the catalog writer and performs these operations together:

1. Validate the exact candidate set and original cursor generations.
2. Resolve the winning run's last eligible observation per effective key.
3. Apply selected projections and exact effective facts.
4. Reconcile components bound to the selected primary application.
5. Apply lifecycle transitions, publish the release, and commit cursors.
6. Seal the inputs and result in `mail_authority_decisions`.

A failure rolls back every operation. An exact replay validates the sealed
inputs and committed cursor ownership, then returns the saved result. It does
not refresh timestamps, invalidate new cursors, or increment absence generations
again. Changed inputs and displaced committed generations fail closed.

The shared ledger exposes a narrow transaction-neutral authority application
operation. It accepts an explicitly selected set, checks source, stream, and
effective-key uniqueness, and rejects stale facts. An advanced application can
restore its exact immutable identity. An equivalent capture retains its exact
original recovery pin. An equivalent pin cannot follow a later A/B/A return.
Ordinary release eligibility and immutable fact payloads remain unchanged.

## Independent state and components

`mail_projection_owners` records which accepted projection belongs to a delta
scope. An independent accepted write clears this ownership. Cursor lineage
controls competing delta runs; timestamps still protect newer independent
metadata. Conservative inventory absence checks can inspect pending positive
folder observations without publishing them.

A folder deletion updates presence and invalidates only that folder's message
cursor, candidate, and causal proof. It increments absence generation once. It
does not delete message primary data. An inventory callback retains its own
run-specific sighting even when its metadata is too old to apply.

Run-local discovery planning reads retained primary inputs. Full captures can
arrive before their primary, but their immutable selection cannot apply until
that exact primary wins. A losing equivalent selection cannot borrow another
run's accepted primary. New inputs for a sealed authority run are rejected;
exact retained retries remain idempotent.

## Compatibility and execution

The three tables are an additive, strictly validated SQLite family. Unknown or
partial definitions fail before initialization commits. Existing facts,
releases, catalog identity, and cursor schemas are preserved. No pending
projection or causal proof is fabricated from legacy mutable state. Legacy
authority work without retained inputs requires reacquisition.

Scrapy 2.19.0 still owns traversal, callback serialization, and idle detection.
Evidence writes remain awaited before semantic items. Original folder scope
travels through the existing callback/item path. Message-delta 410 and JOBDIR
rules remain in their existing owners. Folder-delta still rejects JOBDIR.

Separate crawlers have separate pipeline locks. Lifecycle candidates reserve
the SQLite writer before reading state. Raw evidence uses a private temporary
file per writer, so concurrent identical response bodies cannot rename another
writer's temporary file. The final blob remains content-addressed.
