"""
Read-only, cancellation-safe access to committed A1 release entries.

Each operation owns one short SQLite read snapshot. Paths use the same pinned
directory and inode checks as SavedSourceReader. Queries have deadlines, row
limits, per-row byte limits, and an aggregate metadata byte budget. The caller
owns downstream cursors; this adapter never initializes or mutates A1.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import sqlite3
from collections.abc import Callable
from contextlib import closing
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, TypeAdapter

from msgloom.sources._catalog import ReadOnlyCatalog
from msgloom.sources._handoff_catalog_validation import (
    validate_impact as _validate_impact,
)
from msgloom.sources._io import BlockingGate
from msgloom.sources.handoff_models import (
    A1CatalogIdentity,
    Digest,
    EntryPayload,
    FactPayload,
    Identifier,
    ReleasedFact,
    ReleaseEntry,
    ReleaseEntryPage,
    ReleaseEntryRef,
    ReleaseGroup,
    Sequence,
    Stream,
)
from msgloom.sources.models import SourceReaderLimits, SourceReferenceError

_T = TypeVar("_T")
_Model = TypeVar("_Model", bound=BaseModel)
_ENTRY_COLUMNS = (
    "release_entry_seq, release_group_id, source_id, stream, entry_digest, payload"
)


def _canonical(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


class _Snapshot:
    """Enforce a shared metadata budget for all rows of one operation."""

    def __init__(self, connection: sqlite3.Connection, limits: SourceReaderLimits):
        self.connection = connection
        self.remaining = limits.max_snapshot_bytes
        # Admission anchors are not A1 fact/evidence materialization. Keep a
        # separate aggregate byte budget, allowing at most one complete signed
        # anchor if configured metadata limits are smaller than its wire size.
        self.anchor_remaining = limits.max_snapshot_bytes
        self.member_limit = min(128, limits.max_query_rows)

    def payload(self, raw: str, model: type[_Model]) -> _Model:
        size = len(raw.encode())
        self.remaining -= size
        if size > 65536 or self.remaining < 0:
            raise SourceReferenceError("Release metadata exceeds reader byte bound")
        value = model.model_validate_json(raw)
        if _canonical(json.loads(raw)) != raw:
            raise SourceReferenceError("Release metadata is not canonical")
        return value

    def identity(self) -> A1CatalogIdentity:
        rows = self.connection.execute(
            "SELECT singleton, catalog_identity, schema_version "
            "FROM acquisition_ledger_metadata LIMIT 2"
        ).fetchall()
        if len(rows) != 1 or rows[0]["singleton"] != 1:
            raise SourceReferenceError("Acquisition ledger identity is unavailable")
        return A1CatalogIdentity(
            catalog_identity=rows[0]["catalog_identity"],
            schema_version=rows[0]["schema_version"],
        )

    def entry(self, row: sqlite3.Row, catalog: A1CatalogIdentity) -> ReleaseEntry:
        payload = self.payload(row["payload"], EntryPayload)
        material = payload.model_dump(mode="json")
        if (
            _digest({"group": row["release_group_id"], "entry": material})
            != row["entry_digest"]
        ):
            raise SourceReferenceError("Release entry digest mismatch")
        members = self.connection.execute(
            "SELECT ordinal, fact_id, role FROM acquisition_release_entry_facts "
            "WHERE release_entry_seq = ? ORDER BY ordinal LIMIT ?",
            (row["release_entry_seq"], self.member_limit + 1),
        ).fetchall()
        expected = [(index, *pair) for index, pair in enumerate(payload.facts)]
        if len(members) > self.member_limit or [tuple(m) for m in members] != expected:
            raise SourceReferenceError("Release entry membership mismatch or bound")
        group_row = self.connection.execute(
            "SELECT source_id, stream, group_digest, payload "
            "FROM acquisition_release_groups WHERE release_group_id = ? LIMIT 1",
            (row["release_group_id"],),
        ).fetchone()
        if group_row is None:
            raise SourceReferenceError("Release completion group is unavailable")
        group = self.payload(group_row["payload"], ReleaseGroup)
        if (group.source_id, group.stream) != (
            group_row["source_id"],
            group_row["stream"],
        ) or (group.source_id, group.stream) != (row["source_id"], row["stream"]):
            raise SourceReferenceError("Release crosses source or stream")
        group_identity = group.model_dump(mode="json")
        for key in ("released_at", "coverage_kind", "limitation_codes"):
            group_identity.pop(key)
        if _digest(group_identity) != row["release_group_id"]:
            raise SourceReferenceError("Release group identity mismatch")
        return ReleaseEntry(
            **payload.model_dump(),
            catalog=catalog,
            release_entry_seq=row["release_entry_seq"],
            release_group_id=row["release_group_id"],
            source_id=row["source_id"],
            stream=row["stream"],
            entry_digest=row["entry_digest"],
            group_digest=group_row["group_digest"],
            group=group,
        )

    @staticmethod
    def anchor_size(row: sqlite3.Row) -> int:
        """Charge all selected anchor columns, not only the JSON payload."""
        if any(
            not isinstance(row[key], str)
            for key in (
                "release_group_id",
                "source_id",
                "stream",
                "entry_digest",
                "payload",
            )
        ):
            raise SourceReferenceError("Release anchor columns are invalid")
        return 8 + sum(
            len(row[key].encode())
            for key in (
                "release_group_id",
                "source_id",
                "stream",
                "entry_digest",
                "payload",
            )
        )

    def admission_ref(
        self, row: sqlite3.Row, catalog: A1CatalogIdentity
    ) -> ReleaseEntryRef:
        """Validate the immutable entry anchor without materializing its facts.

        A2 must be able to hold an oversized or otherwise unreadable entry
        without blocking every later release. Anchor integrity uses the fixed
        ledger wire limit, independent of the *materialization* byte budget.
        The public exact-entry API retains its strict membership checks.
        """
        raw = row["payload"]
        if not isinstance(raw, str) or len(raw.encode()) > 65536:
            raise SourceReferenceError("Release anchor payload exceeds wire bound")
        try:
            material = json.loads(raw)
        except (ValueError, TypeError):
            raise SourceReferenceError("Invalid release anchor encoding") from None
        if (
            _canonical(material) != raw
            or _digest({"group": row["release_group_id"], "entry": material})
            != row["entry_digest"]
        ):
            raise SourceReferenceError("Release anchor digest mismatch")
        return ReleaseEntryRef(
            catalog=catalog,
            release_entry_seq=TypeAdapter(Sequence).validate_python(
                row["release_entry_seq"], strict=True
            ),
            entry_digest=TypeAdapter(Digest).validate_python(
                row["entry_digest"], strict=True
            ),
        )

    def get(self, seq: int, catalog: A1CatalogIdentity) -> ReleaseEntry | None:
        row = self.connection.execute(
            f"SELECT {_ENTRY_COLUMNS} FROM acquisition_release_entries "
            "WHERE release_entry_seq = ? LIMIT 1",
            (seq,),
        ).fetchone()
        return None if row is None else self.entry(row, catalog)

    def facts(self, entry: ReleaseEntry) -> tuple[ReleasedFact, ...]:
        result = []
        for ordinal, (fact_id, role) in enumerate(entry.facts):
            row = self.connection.execute(
                "SELECT source_id, stream, run_id, source_state_key, "
                "storage_relation, payload FROM acquisition_facts "
                "WHERE fact_id = ? LIMIT 1",
                (fact_id,),
            ).fetchone()
            if row is None:
                raise SourceReferenceError("Released fact is unavailable")
            fact = self.payload(row["payload"], FactPayload)
            material = fact.model_dump(mode="json")
            # A1 excludes a null recovery pin from immutable fact identity.
            if material["revalidated_fact_id"] is None:
                material.pop("revalidated_fact_id")
            if _digest(material) != fact_id:
                raise SourceReferenceError("Released fact digest mismatch")
            if any(
                row[key] != getattr(fact, key)
                for key in (
                    "source_id",
                    "stream",
                    "run_id",
                    "source_state_key",
                    "storage_relation",
                )
            ) or (fact.source_id, fact.stream) != (entry.source_id, entry.stream):
                raise SourceReferenceError("Released fact ownership mismatch")
            if fact.storage_relation == "stale":
                raise SourceReferenceError("Stale fact cannot describe a release")
            _validate_impact(entry, fact, role)
            result.append(
                ReleasedFact(
                    **fact.model_dump(),
                    fact_id=fact_id,
                    role=role,
                    ordinal=ordinal,
                )
            )
        return tuple(result)


class HandoffCatalog:
    """
    Expose bounded awaitable release queries without loading A1 code.

    Instantiate with an absolute existing catalog path and optional immutable
    SourceReaderLimits. A page contains exact entries; facts are loaded
    separately from an entry or its catalog-bound reference. A missing or
    different anchor returns false, while malformed catalogs raise
    SourceReferenceError. Sequence zero denotes genesis and has no entry
    digest: callers compare catalog identity before starting a new cursor.
    """

    def __init__(
        self, catalog_path: Path, limits: SourceReaderLimits | None = None
    ) -> None:
        if not catalog_path.is_absolute():
            raise SourceReferenceError("Acquisition catalog path must be absolute")
        self._limits = SourceReaderLimits.model_validate(
            (limits or SourceReaderLimits()).model_dump()
        )
        self._catalog = ReadOnlyCatalog(catalog_path, self._limits)
        self._gate = BlockingGate(
            self._limits.max_blocking_workers,
            self._limits.max_blocking_queue,
        )
        self._closed = False

    @property
    def max_release_page_size(self) -> int:
        """Advertise the finite A1 release page bound to the A2 intake owner."""
        return min(1000, self._limits.max_list_results, self._limits.max_query_rows)

    def _read(self, operation: Callable[[_Snapshot], _T]) -> _T:
        try:
            with closing(self._catalog._connect()) as connection:
                # Bound corrupt SQLite values before Python materializes them.
                connection.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 256 * 1024)
                connection.execute("BEGIN")
                return operation(_Snapshot(connection, self._limits))
        except (sqlite3.Error, ValueError, TypeError, KeyError, RecursionError):
            raise SourceReferenceError(
                "Invalid or unavailable release ledger"
            ) from None

    async def _run(self, operation: Callable[[_Snapshot], _T]) -> _T:
        return await self._gate.run(lambda: self._read(operation))

    async def catalog_identity(self) -> A1CatalogIdentity:
        """Read one stable identity; reject missing or unsupported metadata."""
        return await self._run(lambda snapshot: snapshot.identity())

    async def max_release_entry_seq(self, source_id: str, stream: Stream) -> int:
        """Return the greatest committed sequence for this scope, or zero."""
        TypeAdapter(Identifier).validate_python(source_id, strict=True)
        TypeAdapter(Stream).validate_python(stream, strict=True)

        def read(snapshot: _Snapshot) -> int:
            snapshot.identity()
            row = snapshot.connection.execute(
                "SELECT release_entry_seq FROM acquisition_release_entries "
                "WHERE source_id = ? AND stream = ? "
                "ORDER BY release_entry_seq DESC LIMIT 1",
                (source_id, stream),
            ).fetchone()
            return (
                0
                if row is None
                else TypeAdapter(Sequence).validate_python(
                    row["release_entry_seq"],
                    strict=True,
                )
            )

        return await self._run(read)

    async def list_release_entries(
        self,
        source_id: str,
        stream: Stream,
        *,
        after_seq: int = 0,
        through_seq: int,
        limit: int = 100,
    ) -> ReleaseEntryPage:
        """
        Read a fixed bounded cut; one sentinel detects further entries.

        The caller obtains a ceiling using max_release_entry_seq before
        pagination. Entries committed above that ceiling wait for later intake.
        Aggregate payload overflow raises instead of silently dropping entries.
        """
        TypeAdapter(Identifier).validate_python(source_id, strict=True)
        TypeAdapter(Stream).validate_python(stream, strict=True)
        TypeAdapter(Sequence).validate_python(after_seq, strict=True)
        TypeAdapter(Sequence).validate_python(through_seq, strict=True)
        if (
            type(limit) is not int
            or not 1 <= limit <= self.max_release_page_size
            or after_seq > through_seq
        ):
            raise ValueError("Invalid release page bounds")

        def read(snapshot: _Snapshot) -> ReleaseEntryPage:
            catalog = snapshot.identity()
            rows = snapshot.connection.execute(
                f"SELECT {_ENTRY_COLUMNS} FROM acquisition_release_entries "
                "WHERE source_id = ? AND stream = ? AND release_entry_seq > ? "
                "AND release_entry_seq <= ? ORDER BY release_entry_seq LIMIT ?",
                (source_id, stream, after_seq, through_seq, limit + 1),
            ).fetchall()
            return ReleaseEntryPage(
                catalog=catalog,
                source_id=source_id,
                stream=stream,
                after_seq=after_seq,
                through_seq=through_seq,
                entries=tuple(snapshot.entry(row, catalog) for row in rows[:limit]),
                has_more=len(rows) > limit,
            )

        return await self._run(read)

    async def get_release_entry_ref(
        self, seq: int, source_id: str, stream: Stream
    ) -> ReleaseEntryRef | None:
        """Recheck the exact cursor anchor even if its evidence is unreadable."""
        TypeAdapter(Sequence).validate_python(seq, strict=True)
        TypeAdapter(Identifier).validate_python(source_id, strict=True)
        TypeAdapter(Stream).validate_python(stream, strict=True)

        def read(snapshot: _Snapshot) -> ReleaseEntryRef | None:
            catalog = snapshot.identity()
            row = snapshot.connection.execute(
                f"SELECT {_ENTRY_COLUMNS} FROM acquisition_release_entries "
                "WHERE release_entry_seq = ? AND source_id = ? AND stream = ? "
                "LIMIT 1",
                (seq, source_id, stream),
            ).fetchone()
            return None if row is None else snapshot.admission_ref(row, catalog)

        return await self._run(read)

    async def list_release_entry_refs(
        self,
        source_id: str,
        stream: Stream,
        *,
        after_seq: int,
        through_seq: int,
        limit: int,
    ) -> tuple[ReleaseEntryRef, ...]:
        """Enumerate bounded verified anchors; full payload is per-entry work.

        The cursor may advance past a held entry only after its exact digest
        and the held disposition are saved atomically. No mutable A1 state or
        best-effort data is admitted by this metadata-only enumeration.
        """
        TypeAdapter(Identifier).validate_python(source_id, strict=True)
        TypeAdapter(Stream).validate_python(stream, strict=True)
        TypeAdapter(Sequence).validate_python(after_seq, strict=True)
        TypeAdapter(Sequence).validate_python(through_seq, strict=True)
        if (
            type(limit) is not int
            or not 1 <= limit <= self.max_release_page_size
            or after_seq > through_seq
        ):
            raise ValueError("Invalid release anchor page bounds")

        def read(snapshot: _Snapshot) -> tuple[ReleaseEntryRef, ...]:
            catalog = snapshot.identity()
            cursor = snapshot.connection.execute(
                f"SELECT {_ENTRY_COLUMNS} FROM acquisition_release_entries "
                "WHERE source_id = ? AND stream = ? AND release_entry_seq > ? "
                "AND release_entry_seq <= ? ORDER BY release_entry_seq LIMIT ?",
                (source_id, stream, after_seq, through_seq, limit),
            )
            anchors = []
            # Iterate instead of fetchall: never materialize an unbounded
            # aggregate of entry JSON before charging the page budget. Each
            # bounded call admits at least one valid digest-verified anchor
            # even when the caller chose a sub-wire metadata limit; further
            # anchors wait for the next cursor page.
            for row in cursor:
                size = snapshot.anchor_size(row)
                if anchors and size > snapshot.anchor_remaining:
                    break
                anchor = snapshot.admission_ref(row, catalog)
                anchors.append(anchor)
                snapshot.anchor_remaining = max(0, snapshot.anchor_remaining - size)
            return tuple(anchors)

        return await self._run(read)

    async def get_release_entry(self, seq: int) -> ReleaseEntry | None:
        """Read one exact committed entry and validate ordered membership."""
        TypeAdapter(Sequence).validate_python(seq, strict=True)
        return await self._run(lambda snapshot: snapshot.get(seq, snapshot.identity()))

    async def get_release_facts(
        self,
        entry: ReleaseEntry | ReleaseEntryRef,
    ) -> tuple[ReleasedFact, ...]:
        """Load exact ordered facts after rechecking catalog and entry anchor."""
        reference = entry.reference if isinstance(entry, ReleaseEntry) else entry
        reference = ReleaseEntryRef.model_validate(reference.model_dump())

        def read(snapshot: _Snapshot) -> tuple[ReleasedFact, ...]:
            catalog = snapshot.identity()
            if catalog != reference.catalog:
                raise SourceReferenceError("Release catalog identity mismatch")
            current = snapshot.get(reference.release_entry_seq, catalog)
            if current is None or current.entry_digest != reference.entry_digest:
                raise SourceReferenceError("Release entry anchor mismatch")
            return snapshot.facts(current)

        return await self._run(read)

    async def verify_entry_anchor(self, seq: int, digest: str) -> bool:
        """Verify a non-genesis cursor; missing or divergent entries return false."""
        TypeAdapter(Digest).validate_python(digest, strict=True)
        entry = await self.get_release_entry(seq)
        return entry is not None and entry.entry_digest == digest

    async def close(self) -> None:
        """Drain accepted workers, release pinned paths, preserve cancellation."""
        if self._closed:
            return
        cancelled = False
        try:
            await self._gate.close()
        except asyncio.CancelledError:
            cancelled = True
        finally:
            self._catalog.close()
            self._closed = True
        if cancelled:
            raise asyncio.CancelledError
