# Saved source reader API

## Ownership and boundary

msgloom.sources is the read-only adapter from the existing A1 acquisition
catalog and saved evidence files to later A2 preparation. It does not collect,
parse, filter, group, persist Phase 1 results, advance checkpoints, construct
message_ingest.catalog.Catalog, or fetch a URI.

The live adapter supports saved Outlook Mail, To Do tasks, OneDrive items, and
Contacts. Real Teams collection remains unavailable. Tests or later adapters
may implement CollectedSourceReader for synthetic Teams records without
claiming a live provider.

## Public contracts and exact selection

SavedSourceReaderConfig contains one absolute A1 SQLite path, explicit absolute
evidence roots, and finite SourceReaderLimits. Limits bound list size, selected
records, evidence/snapshot bytes, SQLite rows/query time, active blocking
workers, and the waiting queue. Configuration is strictly revalidated before
file/database operations; mutation or non-finite limits fail before access.

The awaited reader operations are:

    list_versions(source_type, *, source_id, limit)
    read(source)
    read_selection(source)
    read_many(sources)
    encode_selection(selection)
    decode_selection(bytes)
    load_saved_bytes(reference)
    close()

read is a convenience view of a newly captured selection. read_selection
returns CollectedSelection: the primary VersionRef, a content-derived
collected_selection reference, and the complete validated CollectedRecord. The
selection version hashes canonical bounded JSON for all component metadata and
exact body/MIME/attachment/content references. Changing a mutable current A1
surface therefore changes the selection version even when the primary source
version is unchanged.

CollectedSelectionCodec is the closed ``collected_selection`` schema version
``1`` codec. It exposes the SemanticDataRegistry-compatible ``kind``,
``schema_version``, ``python_type``, ``max_bytes``, ``encode`` and ``decode``
surface without registering itself globally. Its fixed ceiling is 32 MiB.
Reader ``max_snapshot_bytes`` may impose a lower limit but can never raise the
codec ceiling. Encoding treats serializer warnings as errors, strictly
revalidates nested models and dataclasses through canonical JSON, and rejects
malformed, duplicate-key, non-finite, unknown, wrong-typed, oversized and
noncanonical data with fixed privacy-safe failures.

The durable A2 handoff order is exact:

1. ``read_selection(source)`` captures the complete current component record.
2. Encode and durably save that exact collected-selection payload before
   parsing.
3. Parse only bytes separately identified for the selected representation. For
   an extracted body field, A2 first persists separately identified
   derived body bytes and parses those bytes.
4. On restart, decode and replay the saved selection. Do not re-read current A1
   projections to reconstruct MIME, attachment, body or metadata state.

The default Phase 1 registries now compose CollectedSelectionCodec and require
semantic data for accepted collected-selection results. Primary observation
identity alone never proves ownership of mutable MIME, attachment or current
content tables.

Listing is finite and deterministic. Selection is always by exact VersionRef.
Contact delta ordinals use canonical nonnegative SQLite integers. Malformed,
noncanonical, or overflowing ordinals fail with an opaque reference error.
There is no latest fallback, recursive discovery, URI fetch, provider request,
or implicit network operation.

## Record representation and lineage

CollectedRecord is strict and frozen. It retains source/source-scope versions,
semantic identity, observation/source times, parties, recipients, raw
representation, verified source bytes, body variants, attachments, native
relationships, metadata, source locations, and limitations.

CollectedBody.kind and CollectedAttachment.content_kind distinguish plain,
HTML, MIME, JSON, and binary. HTML remains raw HTML data. Binary content
remains binary until A2 selects a parser. Collected body locations and the
record's source locations remain part of the saved selection and survive codec
replay.

For Graph-backed records, ``CollectedBody.saved_bytes`` may intentionally equal
``CollectedRecord.source_bytes``: that reference identifies the whole verified
Graph JSON response from which ``body.content`` was extracted. It does **not**
identify UTF-8 bytes consisting only of ``body.content``. A2 must persist a
new, separately identified derived byte object for the selected body field
before sending HTML/plain body bytes to a parser; it must never attach the
whole Graph response hash to the extracted body text.

A source scope is VersionRef("source_scope", source_id, bound_at) from the
existing immutable source binding. Account keys, credential headers, raw
request URLs, filesystem paths, and transport errors are not copied into the
public models or public errors.

Outlook primary identity is the A1 source plus immutable Graph message ID; its
version is the immutable observation ID. Old detail observations use their own
evidence. Current MIME/attachment tables are not proven by A1 to be permanently
owned by that observation. They are usable only as a captured current component
selection, with an explicit limitation and composite snapshot version.
Historical/unbound associations remain limitations; attachment metadata not
bound to the selected primary evidence cannot supply saved bytes.

To Do task versions bind snapshot run and task-sighting evidence. Contact
snapshot/delta versions bind their exact saved evidence. OneDrive listing
enumerates immutable item-page evidence. Content is associated only when
planned metadata observation/evidence and ETag match the selected item version,
the saved content evidence belongs to the same source, and the bounded capture
query is complete.

## Native relationships and query completeness

Every record has exactly one source_scope relationship. Outlook conversationId
is support within that scope. In-Reply-To uses the Internet-Message-ID
namespace and is confirmed only when a complete bounded observation scan finds
exactly one target whose selected saved evidence contains that exact
Internet-Message-ID. Mutable messages projection data alone cannot establish
the target.

Query bounds never imply completeness. Reply-scan overflow prevents reply
confirmation and adds in-reply-to-query-overflow. Outlook surface and
attachment inventory overflow is explicit. OneDrive page-scan overflow fails
listing rather than returning a list that looks complete; content-capture
overflow suppresses association and is visible on the record.

## Saved bytes and containment

SavedByteReference.reference uses local a1-response:EVIDENCE_ID form; it is
neither a path nor a fetchable URI. Loading resolves the A1 evidence row, then
verifies configured-root containment, exact byte count, and SHA-256.

Evidence roots are opened descriptor-relatively from the filesystem root with
O_NOFOLLOW at every component. Each child directory is then opened relative to
the pinned root. The final file uses O_NOFOLLOW and O_NONBLOCK and must be a
regular file. Before/open/after inode, device, size, and modification metadata
checks defend races; a bounded loop handles legitimate short reads. FIFO,
device, symlink, ancestor-swap, missing, corrupt, escaped, and oversized inputs
fail safely.

The SQLite catalog similarly pins its ancestor directory descriptors and
regular-file identity. SQLite opens read-only through that pinned directory so
a replaced ancestor path cannot redirect it. It deliberately does not use
immutable=1: A1 may be actively written in WAL mode and ordinary SQLite read
locking/change detection must remain effective. The final catalog inode is
rechecked around each open.

## Ordering, failure, and cancellation

SQLite uses mode=ro, PRAGMA query_only=ON, zero write-lock timeout, bounded
rows, and a progress-handler deadline. Every short-lived connection is
explicitly closed; the SQLite connection context manager is not relied on for
ownership.

Blocking SQLite/file work uses a bounded awaited thread gate. Queue admission
and active workers are finite. Once a blocking call starts, cancellation drains
it, consumes its result/error, and only then communicates cancellation. close
rejects new work, drains all accepted workers even under repeated cancellation,
releases pinned descriptors, and then re-raises cancellation. No accepted
blocking work intentionally survives return.

Public failures are opaque and path/credential safe. SQLite exceptions,
filesystem details, provider identifiers, and malformed timestamp text are not
chained into public adapter errors. Parsing and accepted Phase 1 persistence
remain downstream handler ownership.
