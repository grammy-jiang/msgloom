"""R2 regressions for saved-source ownership and replay boundaries."""

from __future__ import annotations

import asyncio
import hashlib
import os
import sqlite3
import threading
from pathlib import Path
from typing import cast
from unittest.mock import patch

import pytest

from msgloom.preparation.records import PreparedSourceType
from msgloom.sources import (
    SavedSourceReader,
    SavedSourceReaderConfig,
    SourceReaderLimits,
    SourceReferenceError,
)


def _reader(fixture: dict[str, object]) -> SavedSourceReader:
    return SavedSourceReader(
        SavedSourceReaderConfig(
            catalog_path=cast(Path, fixture["database"]),
            evidence_roots=(cast(Path, fixture["evidence_root"]),),
        )
    )


def _reader_with_limits(
    fixture: dict[str, object], limits: SourceReaderLimits
) -> SavedSourceReader:
    return SavedSourceReader(
        SavedSourceReaderConfig(
            catalog_path=cast(Path, fixture["database"]),
            evidence_roots=(cast(Path, fixture["evidence_root"]),),
            limits=limits,
        )
    )


def test_query_overflow_never_confirms_reply_or_complete_surface_inventory(
    saved_catalog,
) -> None:
    async def scenario() -> None:
        reader = _reader_with_limits(
            saved_catalog,
            SourceReaderLimits(max_query_rows=1),
        )
        refs = await reader.list_versions(
            PreparedSourceType.OUTLOOK_EMAIL,
            source_id=saved_catalog["source_id"],
            limit=10,
        )
        current = await reader.read(
            next(ref for ref in refs if ref.version == "obs-current")
        )
        if any(item.kind == "in_reply_to" for item in current.relationships):
            pytest.fail("Truncated reply scan confirmed a relationship")
        codes = {item.code for item in current.limitations}
        if "in-reply-to-query-overflow" not in codes:
            pytest.fail("Reply query overflow was not visible")
        if "outlook-surface-inventory-overflow" not in codes:
            pytest.fail("Surface inventory overflow was not visible")
        await reader.close()

    asyncio.run(scenario())


def test_sqlite_connections_are_closed_per_query(saved_catalog) -> None:
    real_connect = sqlite3.connect
    connections = []

    class TrackedConnection(sqlite3.Connection):
        was_closed = False

        def close(self) -> None:
            self.was_closed = True
            super().close()

    def tracked_connect(*args, **kwargs):
        kwargs["factory"] = TrackedConnection
        connection = real_connect(*args, **kwargs)
        connections.append(connection)
        return connection

    async def scenario() -> None:
        with patch("msgloom.sources._catalog.sqlite3.connect", tracked_connect):
            reader = _reader(saved_catalog)
            refs = await reader.list_versions(
                PreparedSourceType.OUTLOOK_EMAIL,
                source_id=saved_catalog["source_id"],
                limit=10,
            )
            await reader.read(next(ref for ref in refs if ref.version == "obs-current"))
            await reader.close()

    asyncio.run(scenario())
    if not connections:
        pytest.fail("Connection tracking did not observe any catalog query")
    if any(not connection.was_closed for connection in connections):
        pytest.fail("A short-lived SQLite query connection leaked")


def test_descriptor_relative_read_rejects_swapped_ancestor_and_handles_short_reads(
    saved_catalog,
) -> None:
    from msgloom.sources._catalog import EvidenceRow
    from msgloom.sources._io import EvidenceFiles
    from msgloom.sources.models import SourceEvidenceError

    root = cast(Path, saved_catalog["evidence_root"])
    nested = root / "nested"
    nested.mkdir()
    outside = root.parent / "outside"
    outside.mkdir()
    content = b"controlled-synthetic-content"
    path = nested / "evidence.bin"
    path.write_bytes(content)
    (outside / "evidence.bin").write_bytes(content)
    row = EvidenceRow(
        "synthetic",
        cast(str, saved_catalog["source_id"]),
        "2026-09-29T00:00:00+00:00",
        "test",
        hashlib.sha256(content).hexdigest(),
        str(path),
        len(content),
    )
    files = EvidenceFiles((root,), 1024)
    real_read = os.read

    def short_read(descriptor: int, count: int) -> bytes:
        return real_read(descriptor, min(count, 3))

    with patch("msgloom.sources._io.os.read", short_read):
        if files.read(row) != content:
            pytest.fail("Bounded short-read loop changed evidence bytes")

    nested.rename(root / "old")
    nested.symlink_to(outside, target_is_directory=True)
    with pytest.raises(SourceEvidenceError):
        files.read(row)
    files.close()


def test_selection_snapshot_replays_after_current_surface_changes(
    saved_catalog,
) -> None:
    async def scenario() -> None:
        reader = _reader(saved_catalog)
        refs = await reader.list_versions(
            PreparedSourceType.OUTLOOK_EMAIL,
            source_id=saved_catalog["source_id"],
            limit=10,
        )
        source = next(ref for ref in refs if ref.version == "obs-current")
        before = await reader.read_selection(source)
        encoded = await reader.encode_selection(before)
        if before.record.attachments[0].saved_bytes is None:
            pytest.fail("Initial captured attachment bytes were unavailable")

        with sqlite3.connect(saved_catalog["database"]) as connection:
            connection.execute(
                "UPDATE message_surfaces SET status = 'failed' "
                "WHERE surface LIKE 'attachment_raw:%'"
            )

        after = await reader.read_selection(source)
        if after.selection == before.selection:
            pytest.fail("Mutable component selection did not change snapshot version")
        if after.record.attachments[0].saved_bytes is not None:
            pytest.fail("Changed current surface was silently reused")
        replay = await reader.decode_selection(encoded)
        if replay != before:
            pytest.fail("Persisted selection did not replay exact descriptor")
        saved = replay.record.attachments[0].saved_bytes
        if (
            saved is None
            or await reader.load_saved_bytes(saved) != b"synthetic attachment"
        ):
            pytest.fail("Replay lost exact verified attachment bytes")
        await reader.close()

    asyncio.run(scenario())


def test_catalog_and_evidence_roots_stay_pinned_after_parent_replacement(
    saved_catalog,
) -> None:
    async def scenario() -> None:
        reader = _reader(saved_catalog)
        base = cast(Path, saved_catalog["database"]).parent
        moved = base.with_name(base.name + "-moved")
        outside = base.with_name(base.name + "-outside")
        outside.mkdir()
        base.rename(moved)
        base.symlink_to(outside, target_is_directory=True)
        try:
            refs = await reader.list_versions(
                PreparedSourceType.OUTLOOK_EMAIL,
                source_id=saved_catalog["source_id"],
                limit=10,
            )
            current = await reader.read(
                next(ref for ref in refs if ref.version == "obs-current")
            )
            if current.subject != "Current subject":
                pytest.fail("Pinned catalog/evidence roots followed replacement")
            await reader.close()
        finally:
            if base.is_symlink():
                base.unlink()
            if moved.exists():
                moved.rename(base)
            outside.rmdir()

    asyncio.run(scenario())


def test_cancelled_close_drains_then_preserves_cancellation(saved_catalog) -> None:
    async def scenario() -> None:
        reader = _reader(saved_catalog)
        refs = await reader.list_versions(
            PreparedSourceType.OUTLOOK_EMAIL,
            source_id=saved_catalog["source_id"],
            limit=10,
        )
        target = next(ref for ref in refs if ref.version == "obs-current")
        entered = threading.Event()
        release = threading.Event()
        original = reader._files.read

        def blocked(row):
            entered.set()
            if not release.wait(timeout=5):
                raise RuntimeError("synthetic file barrier timed out")
            return original(row)

        reader._files.read = blocked
        read_task = asyncio.create_task(reader.read(target))
        if not await asyncio.to_thread(entered.wait, 2):
            pytest.fail("Synthetic file read did not start")
        close_task = asyncio.create_task(reader.close())
        await asyncio.sleep(0)
        close_task.cancel()
        close_task.cancel()
        await asyncio.sleep(0.05)
        if close_task.done():
            pytest.fail("Cancelled close returned before accepted work drained")
        release.set()
        await read_task
        with pytest.raises(asyncio.CancelledError):
            await close_task

    asyncio.run(scenario())


def test_blocking_queue_is_bounded_before_more_work_is_accepted(
    saved_catalog,
) -> None:
    async def scenario() -> None:
        reader = _reader_with_limits(
            saved_catalog,
            SourceReaderLimits(
                max_blocking_workers=1,
                max_blocking_queue=1,
            ),
        )
        refs = await reader.list_versions(
            PreparedSourceType.OUTLOOK_EMAIL,
            source_id=saved_catalog["source_id"],
            limit=10,
        )
        target = next(ref for ref in refs if ref.version == "obs-current")
        entered = threading.Event()
        release = threading.Event()
        original = reader._assembler.read

        def blocked(source):
            entered.set()
            if not release.wait(timeout=5):
                raise RuntimeError("synthetic assembler barrier timed out")
            return original(source)

        reader._assembler.read = blocked
        first = asyncio.create_task(reader.read(target))
        if not await asyncio.to_thread(entered.wait, 2):
            pytest.fail("First blocking operation did not start")
        second = asyncio.create_task(reader.read(target))
        await asyncio.sleep(0.05)
        with pytest.raises(SourceReferenceError, match="queue is full"):
            await reader.read(target)
        release.set()
        await first
        await second
        await reader.close()

    asyncio.run(scenario())


def test_nonfinite_bypass_configuration_is_revalidated_before_access(
    saved_catalog,
) -> None:
    invalid_limits = SourceReaderLimits.model_construct(
        query_timeout_seconds=float("inf")
    )
    config = SavedSourceReaderConfig.model_construct(
        catalog_path=cast(Path, saved_catalog["database"]),
        evidence_roots=(cast(Path, saved_catalog["evidence_root"]),),
        limits=invalid_limits,
    )
    with pytest.raises(SourceReferenceError, match="configuration is invalid"):
        SavedSourceReader(config)


def test_invalid_saved_timestamp_error_is_opaque(saved_catalog) -> None:
    private_text = "private-invalid-timestamp-/synthetic-secret"
    with sqlite3.connect(saved_catalog["database"]) as connection:
        connection.execute(
            "UPDATE message_observations SET observed_at = ? "
            "WHERE observation_id = 'obs-current'",
            (private_text,),
        )

    async def scenario() -> None:
        reader = _reader(saved_catalog)
        source = next(
            ref
            for ref in await reader.list_versions(
                PreparedSourceType.OUTLOOK_EMAIL,
                source_id=saved_catalog["source_id"],
                limit=10,
            )
            if ref.version == "obs-current"
        )
        try:
            await reader.read(source)
        except SourceReferenceError as exc:
            if private_text in str(exc):
                pytest.fail("Invalid timestamp text leaked through public error")
            if exc.__cause__ is not None:
                pytest.fail("Private parse exception was chained publicly")
        else:
            pytest.fail("Invalid saved timestamp was accepted")
        await reader.close()

    asyncio.run(scenario())
