"""Focused behavior tests for exact saved A1 source reads."""

from __future__ import annotations

import asyncio
import hashlib
import sqlite3
import threading
from pathlib import Path
from typing import cast

import pytest

from msgloom.preparation.records import PreparedSourceType
from msgloom.sources import (
    ContentKind,
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


def test_outlook_old_version_does_not_fall_forward(saved_catalog) -> None:
    async def scenario() -> None:
        reader = _reader(saved_catalog)
        refs = await reader.list_versions(
            PreparedSourceType.OUTLOOK_EMAIL,
            source_id=saved_catalog["source_id"],
            limit=10,
        )
        old_ref = next(ref for ref in refs if ref.version == "obs-old")
        current_ref = next(ref for ref in refs if ref.version == "obs-current")
        old = await reader.read(old_ref)
        current = await reader.read(current_ref)

        if old.subject != "Old subject" or current.subject != "Current subject":
            pytest.fail("Reader substituted mutable latest Outlook fields")
        if old.semantic_identity != current.semantic_identity:
            pytest.fail("Message identity changed across observed versions")
        if old.attachments:
            pytest.fail("Historical message received current attachment state")
        old_codes = {item.code for item in old.limitations}
        if "historical-attachment-association-unavailable" not in old_codes:
            pytest.fail("Historical attachment association gap was not visible")
        if current.body is None or current.body.kind is not ContentKind.HTML:
            pytest.fail("Unparsed HTML body kind was not preserved")
        if current.body.content != "<p>Current body</p>":
            pytest.fail("Raw HTML body text changed before A2 parsing")
        if len(current.attachments) != 1:
            pytest.fail("Current attachment association was not retained")
        saved = current.attachments[0].saved_bytes
        if saved is None:
            pytest.fail("Verified current attachment bytes were not referenced")
        if await reader.load_saved_bytes(saved) != b"synthetic attachment":
            pytest.fail("Saved attachment bytes changed")
        relation_kinds = {item.kind for item in current.relationships}
        if relation_kinds != {
            "source_scope",
            "outlook_conversation",
            "in_reply_to",
        }:
            pytest.fail(f"Unexpected Outlook relationships: {relation_kinds}")
        await reader.close()

    asyncio.run(scenario())


def test_context_sources_use_saved_evidence_versions(saved_catalog) -> None:
    async def scenario() -> None:
        reader = _reader(saved_catalog)

        todo_refs = await reader.list_versions(
            PreparedSourceType.TODO,
            source_id=saved_catalog["source_id"],
            limit=10,
        )
        old_todo = await reader.read(
            next(ref for ref in todo_refs if "todo-old" in ref.version)
        )
        current_todo = await reader.read(
            next(ref for ref in todo_refs if "todo-new" in ref.version)
        )
        if old_todo.subject != "Old task" or current_todo.subject != "Current task":
            pytest.fail("To Do sighting evidence was replaced by latest state")
        if old_todo.body is None or old_todo.body.kind is not ContentKind.HTML:
            pytest.fail("To Do HTML content kind was not preserved")

        contact_refs = await reader.list_versions(
            PreparedSourceType.CONTACT,
            source_id=saved_catalog["source_id"],
            limit=10,
        )
        contact = await reader.read(contact_refs[0])
        if contact.subject != "Synthetic Contact":
            pytest.fail("Contact snapshot evidence was not read")
        delta_ref = next(
            ref for ref in contact_refs if ref.version.startswith("delta/")
        )
        delta_contact = await reader.read(delta_ref)
        if delta_contact.subject != "Delta Contact":
            pytest.fail("Contact delta observation evidence was not read")

        drive_refs = await reader.list_versions(
            PreparedSourceType.ONEDRIVE,
            source_id=saved_catalog["source_id"],
            limit=10,
        )
        drive = await reader.read(drive_refs[0])
        if len(drive.attachments) != 1:
            pytest.fail("Exact OneDrive content capture was not associated")
        if drive.attachments[0].saved_bytes is None:
            pytest.fail("OneDrive verified bytes were not referenced")
        if {item.kind for item in drive.relationships} != {"source_scope"}:
            pytest.fail("Context source received a communication grouping relation")
        await reader.close()

    asyncio.run(scenario())


def test_onedrive_old_evidence_ref_survives_latest_projection_change(
    saved_catalog,
) -> None:
    async def scenario() -> None:
        reader = _reader(saved_catalog)
        refs = await reader.list_versions(
            PreparedSourceType.ONEDRIVE,
            source_id=saved_catalog["source_id"],
            limit=10,
        )
        selected = refs[0]
        with sqlite3.connect(saved_catalog["database"]) as connection:
            connection.execute(
                "UPDATE onedrive_items SET latest_observed_at = ?, name = ? "
                "WHERE source_id = ? AND item_id = ?",
                (
                    "2026-09-30T00:00:00+00:00",
                    "newer-name.txt",
                    saved_catalog["source_id"],
                    "file",
                ),
            )
        old = await reader.read(selected)
        if old.subject != "report.txt":
            pytest.fail("Selected OneDrive evidence fell forward to mutable latest")
        if len(old.attachments) != 1:
            pytest.fail("Exact historical content association was lost")
        await reader.close()

    asyncio.run(scenario())


def test_onedrive_rejects_obsolete_content_association(saved_catalog) -> None:
    async def scenario() -> None:
        reader = _reader(saved_catalog)
        refs = await reader.list_versions(
            PreparedSourceType.ONEDRIVE,
            source_id=saved_catalog["source_id"],
            limit=10,
        )
        with sqlite3.connect(saved_catalog["database"]) as connection:
            connection.execute(
                "UPDATE onedrive_content_captures "
                "SET planned_metadata_evidence_id = ? WHERE evidence_id = ?",
                ("unknown-version", "ev-drive-content"),
            )
        record = await reader.read(refs[0])
        if record.attachments:
            pytest.fail("Obsolete OneDrive bytes were associated to selected version")
        if "onedrive-content-not-current" not in {
            item.code for item in record.limitations
        }:
            pytest.fail("Rejected OneDrive content association was not visible")
        await reader.close()

    asyncio.run(scenario())


def test_reader_is_read_only_and_corrupt_evidence_is_visible(saved_catalog) -> None:
    database = Path(saved_catalog["database"])
    before = hashlib.sha256(database.read_bytes()).hexdigest()
    with sqlite3.connect(database) as connection:
        row = connection.execute(
            "SELECT response_body_path FROM raw_http_evidence "
            "WHERE evidence_id = 'ev-old'"
        ).fetchone()
    if row is None:
        pytest.fail("Synthetic evidence row missing")
    Path(row[0]).write_bytes(b"corrupt")

    async def scenario() -> None:
        reader = _reader(saved_catalog)
        refs = await reader.list_versions(
            PreparedSourceType.OUTLOOK_EMAIL,
            source_id=saved_catalog["source_id"],
            limit=10,
        )
        old = await reader.read(next(ref for ref in refs if ref.version == "obs-old"))
        codes = {item.code for item in old.limitations}
        if "unavailable-evidence" not in codes:
            pytest.fail("Corrupt saved evidence was not visible as a limitation")
        await reader.close()

    asyncio.run(scenario())
    after = hashlib.sha256(database.read_bytes()).hexdigest()
    if before != after:
        pytest.fail("Read-only adapter changed the A1 catalog")


def test_cancelled_read_drains_accepted_file_work(saved_catalog) -> None:
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
        task = asyncio.create_task(reader.read(target))
        if not await asyncio.to_thread(entered.wait, 2):
            pytest.fail("Synthetic file read did not start")
        task.cancel()
        task.cancel()
        await asyncio.sleep(0.05)
        if task.done():
            pytest.fail("Cancelled read returned before accepted file work drained")
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        await reader.close()

    asyncio.run(scenario())


def test_mutable_reply_projection_does_not_override_saved_evidence(
    saved_catalog,
) -> None:
    database = Path(saved_catalog["database"])
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO messages "
            "(source_id, message_id, internet_message_id, is_removed, "
            "latest_observed_at) VALUES (?, ?, ?, ?, ?)",
            (
                saved_catalog["source_id"],
                "parent-duplicate",
                "<parent@example.test>",
                0,
                "2026-09-27T01:00:00+00:00",
            ),
        )
        connection.execute(
            "INSERT INTO message_observations "
            "(observation_id, source_id, message_id, run_id, kind, evidence_id, "
            "observed_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "obs-parent-duplicate",
                saved_catalog["source_id"],
                "parent-duplicate",
                "run-parent-duplicate",
                "detail",
                None,
                "2026-09-27T01:00:00+00:00",
            ),
        )

    async def scenario() -> None:
        reader = _reader(saved_catalog)
        refs = await reader.list_versions(
            PreparedSourceType.OUTLOOK_EMAIL,
            source_id=saved_catalog["source_id"],
            limit=10,
        )
        current = await reader.read(
            next(ref for ref in refs if ref.version == "obs-current")
        )
        targets = [
            item.target for item in current.relationships if item.kind == "in_reply_to"
        ]
        if len(targets) != 1 or targets[0].version != "obs-parent":
            pytest.fail("Mutable messages join overrode exact saved reply evidence")
        await reader.close()

    asyncio.run(scenario())


def test_symlink_and_uri_byte_references_are_rejected(saved_catalog) -> None:
    async def scenario() -> None:
        reader = _reader(saved_catalog)
        refs = await reader.list_versions(
            PreparedSourceType.OUTLOOK_EMAIL,
            source_id=saved_catalog["source_id"],
            limit=10,
        )
        current = await reader.read(
            next(ref for ref in refs if ref.version == "obs-current")
        )
        if current.source_bytes is None:
            pytest.fail("Current Graph JSON bytes were not referenced")
        from msgloom.preparation.contracts import SavedByteReference

        forged = SavedByteReference(
            reference="https://provider.example.invalid/private",
            sha256="0" * 64,
            byte_count=0,
        )
        with pytest.raises(SourceReferenceError):
            await reader.load_saved_bytes(forged)
        await reader.close()

    asyncio.run(scenario())

    with sqlite3.connect(saved_catalog["database"]) as connection:
        row = connection.execute(
            "SELECT response_body_path FROM raw_http_evidence "
            "WHERE evidence_id = 'ev-old'"
        ).fetchone()
        if row is None:
            pytest.fail("Synthetic old evidence missing")
        original = Path(row[0])
        target = original.with_name("real-evidence.bin")
        original.rename(target)
        original.symlink_to(target)

    async def symlink_scenario() -> None:
        reader = _reader(saved_catalog)
        refs = await reader.list_versions(
            PreparedSourceType.OUTLOOK_EMAIL,
            source_id=saved_catalog["source_id"],
            limit=10,
        )
        old = await reader.read(next(ref for ref in refs if ref.version == "obs-old"))
        if "unavailable-evidence" not in {item.code for item in old.limitations}:
            pytest.fail("Symlinked evidence was not rejected visibly")
        await reader.close()

    asyncio.run(symlink_scenario())


def test_listing_bounds_and_mime_representation(saved_catalog) -> None:
    async def scenario() -> None:
        reader = _reader(saved_catalog)
        with pytest.raises(ValueError):
            await reader.list_versions(
                PreparedSourceType.OUTLOOK_EMAIL,
                source_id=saved_catalog["source_id"],
                limit=reader.config.limits.max_list_results + 1,
            )
        refs = await reader.list_versions(
            PreparedSourceType.OUTLOOK_EMAIL,
            source_id=saved_catalog["source_id"],
            limit=10,
        )
        current = await reader.read(
            next(ref for ref in refs if ref.version == "obs-current")
        )
        if current.source_content_kind is not ContentKind.JSON:
            pytest.fail("Graph response representation was not retained as JSON")
        if len(current.alternate_bodies) != 1:
            pytest.fail("Saved Outlook MIME representation was not retained")
        mime = current.alternate_bodies[0]
        if mime.kind is not ContentKind.MIME or mime.saved_bytes is None:
            pytest.fail("MIME bytes were mislabeled or unavailable")
        if not (await reader.load_saved_bytes(mime.saved_bytes)).startswith(b"From:"):
            pytest.fail("MIME saved-byte reference did not verify exact bytes")
        await reader.close()

    asyncio.run(scenario())
