"""Public cancellation-safe saved-source reader."""

from __future__ import annotations

import asyncio
import sqlite3

from pydantic import ValidationError

from msgloom.contracts import VersionRef
from msgloom.preparation.contracts import SavedByteReference
from msgloom.preparation.records import PreparedSourceType
from msgloom.sources._assemble import RecordAssembler
from msgloom.sources._catalog import ReadOnlyCatalog
from msgloom.sources._io import BlockingGate, EvidenceFiles
from msgloom.sources._snapshot import (
    capture_selection,
    decode_selection,
    encode_selection,
)
from msgloom.sources.models import (
    CollectedRecord,
    CollectedSelection,
    SavedSourceReaderConfig,
    SourceEvidenceError,
    SourceReferenceError,
)


class SavedSourceReader:
    """Read existing A1 SQLite/evidence stores without constructing Catalog."""

    def __init__(self, config: SavedSourceReaderConfig) -> None:
        """Validate finite configuration before opening local read-only stores."""
        try:
            validated = SavedSourceReaderConfig.model_validate(
                config.model_dump(mode="python")
            )
        except ValidationError:
            raise SourceReferenceError(
                "saved source configuration is invalid"
            ) from None
        self.config = validated
        self._initial_config = validated.model_copy(deep=True)
        self._catalog = ReadOnlyCatalog(validated.catalog_path, validated.limits)
        try:
            self._files = EvidenceFiles(
                validated.evidence_roots,
                validated.limits.max_evidence_bytes,
            )
        except Exception:
            self._catalog.close()
            raise
        self._assembler = RecordAssembler(self._catalog, self._files)
        self._gate = BlockingGate(
            validated.limits.max_blocking_workers,
            validated.limits.max_blocking_queue,
        )
        self._resources_closed = False

    def _revalidate_config(self) -> None:
        try:
            validated = SavedSourceReaderConfig.model_validate(
                self.config.model_dump(mode="python")
            )
        except ValidationError:
            raise SourceReferenceError(
                "saved source configuration is invalid"
            ) from None
        if validated != self._initial_config:
            raise SourceReferenceError(
                "saved source configuration changed after reader construction"
            )

    async def list_versions(
        self,
        source_type: PreparedSourceType,
        *,
        source_id: str,
        limit: int,
    ) -> tuple[VersionRef, ...]:
        """Return a deterministic bounded list without provider discovery."""
        self._revalidate_config()
        if not source_id.strip():
            raise ValueError("source_id must be non-empty")
        if isinstance(limit, bool) or limit < 1:
            raise ValueError("limit must be positive")
        if limit > self.config.limits.max_list_results:
            raise ValueError("limit exceeds configured listing bound")
        try:
            return await self._gate.run(
                self._assembler.list_versions,
                source_type,
                source_id,
                limit,
            )
        except sqlite3.Error:
            raise SourceReferenceError("read-only catalog query failed") from None

    async def read(self, source: VersionRef) -> CollectedRecord:
        """Read one source using a newly captured composite component selection."""
        return (await self.read_selection(source)).record

    async def read_selection(self, source: VersionRef) -> CollectedSelection:
        """Capture exact primary/component lineage for durable downstream replay."""
        self._revalidate_config()
        try:
            return await self._gate.run(self._read_selection_sync, source)
        except sqlite3.Error:
            raise SourceReferenceError("read-only catalog query failed") from None

    def _read_selection_sync(self, source: VersionRef) -> CollectedSelection:
        record = self._assembler.read(source)
        selection = capture_selection(record)
        encode_selection(selection, self.config.limits.max_snapshot_bytes)
        return selection

    async def read_many(
        self, sources: tuple[VersionRef, ...]
    ) -> tuple[CollectedRecord, ...]:
        """Read an explicit finite selection in caller order."""
        self._revalidate_config()
        if len(sources) > self.config.limits.max_selected_records:
            raise ValueError("selection exceeds configured record bound")
        if len(sources) != len(set(sources)):
            raise ValueError("selection must not contain duplicate versions")
        try:
            return await self._gate.run(
                lambda: tuple(self._assembler.read(source) for source in sources)
            )
        except sqlite3.Error:
            raise SourceReferenceError("read-only catalog query failed") from None

    async def encode_selection(self, selection: CollectedSelection) -> bytes:
        """Encode a captured selection through the bounded closed snapshot codec."""
        self._revalidate_config()
        return await self._gate.run(
            encode_selection,
            selection,
            self.config.limits.max_snapshot_bytes,
        )

    async def decode_selection(self, data: bytes) -> CollectedSelection:
        """Decode a persisted selection without consulting mutable A1 state."""
        self._revalidate_config()
        return await self._gate.run(
            decode_selection,
            data,
            self.config.limits.max_snapshot_bytes,
        )

    async def load_saved_bytes(self, reference: SavedByteReference) -> bytes:
        """Resolve and verify only a path-free adapter-issued reference."""
        self._revalidate_config()
        try:
            return await self._gate.run(self._load_reference_sync, reference)
        except sqlite3.Error:
            raise SourceReferenceError("read-only catalog query failed") from None

    async def close(self) -> None:
        """Drain accepted work, release pinned paths, and preserve cancellation."""
        if self._resources_closed:
            return
        cancelled = False
        try:
            await self._gate.close()
        except asyncio.CancelledError:
            cancelled = True
        finally:
            self._files.close()
            self._catalog.close()
            self._resources_closed = True
        if cancelled:
            raise asyncio.CancelledError

    def _load_reference_sync(self, reference: SavedByteReference) -> bytes:
        evidence_id = self._files.evidence_id(reference)
        row = self._catalog.evidence(evidence_id)
        expected = self._files.reference(row)
        if expected != reference:
            raise SourceEvidenceError(
                "saved byte integrity reference no longer matches"
            )
        return self._files.read(row)
