"""Exercise malformed provenance, explicit bounds, and reader cancellation."""

import asyncio
import json
import threading
from dataclasses import replace

import pytest
from sqlalchemy import text

from message_ingest.acquisition.handoff import AcquisitionFactKind, SourceVersionLocator
from message_ingest.catalog import Catalog
from msgloom.sources import SourceReaderError
from tests.source_reader.release_nonmail_helpers import (
    SOURCE,
    fact,
    publish,
    reader_api,
)


@pytest.mark.parametrize("case", ["wrong_kind", "wrong_scope", "wrong_parent"])
def test_todo_locator_hierarchy_is_not_interchangeable(saved_catalog, case):
    item = fact(
        "todo",
        "todo_task",
        '["list","task"]',
        "ev-todo-old",
        scope_kind="todo_list",
        scope_identity="list",
    )
    if case == "wrong_kind":
        item = replace(item, resource_kind="contact")
    if case == "wrong_scope":
        item = replace(item, scope_identity="other-list")
    if case == "wrong_parent":
        item = replace(
            item,
            parent_resource_kind="todo_task_list",
            parent_resource_identity='["other-list"]',
        )
    seq = publish(saved_catalog, [item])

    async def check():
        reader = reader_api(saved_catalog)
        try:
            entry = await reader.catalog.get_release_entry(seq)
            with pytest.raises(SourceReaderError):
                await reader.read_entry(entry.reference)
        finally:
            await reader.close()

    asyncio.run(check())


def test_contacts_sparse_observation_uses_exact_old_capture(saved_catalog):
    item = replace(
        fact(
            "contacts",
            "contact",
            "contact-delta",
            "ev-contact-delta",
            scope_kind="contacts_collection",
            scope_identity="folder:folder-1",
            parent_resource_kind="contact_folder",
            parent_resource_identity="folder-1",
        ),
        source_version_locator=SourceVersionLocator(
            kind="observation",
            evidence_id="ev-contact-delta",
            resource_identity="contact-delta",
            observation_id=json.dumps(
                [SOURCE, "folder:folder-1", "contacts-delta-run", 0],
                separators=(",", ":"),
            ),
        ),
    )
    seq = publish(saved_catalog, [item])

    async def check():
        reader = reader_api(saved_catalog)
        try:
            entry = await reader.catalog.get_release_entry(seq)
            result = await reader.read_entry(entry.reference)
            if result.selection.record.subject != "Delta Contact":
                pytest.fail("Sparse immutable observation was not reconstructed")
            if result.facts[0].run_id != "current-acquisition-run":
                pytest.fail("Old capture overwrote logical run provenance")
            catalog = Catalog(f"sqlite:///{saved_catalog['database']}")
            try:
                with catalog.writer_session() as session:
                    session.execute(
                        text("UPDATE contact_delta_observations SET folder_id='other'")
                    )
            finally:
                catalog.close()
            with pytest.raises(SourceReaderError):
                await reader.read_entry(entry.reference)
        finally:
            await reader.close()

    asyncio.run(check())


def test_terminal_calendar_component_without_payload(saved_catalog):
    item = replace(
        fact(
            "outlook_calendar",
            "calendar_event_surface",
            "event",
            "unused",
            component_kind="series_master",
        ),
        fact_kind=AcquisitionFactKind.COMPONENT_OBSERVATION,
        parent_resource_kind="calendar_event",
        parent_resource_identity="event",
        evidence_id=None,
        source_version_locator=None,
        transition_reason='{"profile_version":"outlook-calendar-full-v1","status":"not_applicable"}',
    )
    seq = publish(saved_catalog, [item], roles=("component",), entry_kind="component")

    async def check():
        reader = reader_api(saved_catalog)
        try:
            entry = await reader.catalog.get_release_entry(seq)
            result = await reader.read_entry(entry.reference)
            if result.selection is not None or len(result.components) != 1:
                pytest.fail("Terminal-only component fabricated a parent body")
            if not result.components[0].record.limitations:
                pytest.fail("Payload-free terminal limitation was dropped")
        finally:
            await reader.close()

    asyncio.run(check())


@pytest.mark.parametrize("limit", ["evidence", "aggregate"])
def test_bounded_evidence_fails_closed(saved_catalog, limit):
    seq = publish(
        saved_catalog,
        [
            fact(
                "todo",
                "todo_task",
                '["list","task"]',
                "ev-todo-old",
                scope_kind="todo_list",
                scope_identity="list",
            )
        ],
    )

    async def check():
        limits = (
            {"max_evidence_bytes": 10}
            if limit == "evidence"
            else {"max_snapshot_bytes": 100}
        )
        reader = reader_api(saved_catalog, **limits)
        try:
            with pytest.raises(SourceReaderError):
                entry = await reader.catalog.get_release_entry(seq)
                await reader.read_entry(entry.reference)
        finally:
            await reader.close()

    asyncio.run(check())


def test_cancellation_drains_accepted_evidence_read(saved_catalog, monkeypatch):
    from msgloom.sources._io import EvidenceFiles

    seq = publish(
        saved_catalog,
        [
            fact(
                "todo",
                "todo_task",
                '["list","task"]',
                "ev-todo-old",
                scope_kind="todo_list",
                scope_identity="list",
            )
        ],
    )
    entered = threading.Event()
    release = threading.Event()
    finished = threading.Event()
    original = EvidenceFiles.read

    def blocking_read(self, row):
        entered.set()
        if not release.wait(5):
            raise RuntimeError("Test did not release evidence reader")
        result = original(self, row)
        finished.set()
        return result

    monkeypatch.setattr(EvidenceFiles, "read", blocking_read)

    async def check():
        reader = reader_api(saved_catalog, max_blocking_workers=1)
        try:
            entry = await reader.catalog.get_release_entry(seq)
            task = asyncio.create_task(reader.read_entry(entry.reference))
            if not await asyncio.to_thread(entered.wait, 5):
                pytest.fail("Reader did not enter bounded evidence worker")
            task.cancel()
            await asyncio.sleep(0)
            if task.done():
                pytest.fail("Cancellation abandoned the accepted read")
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await task
            if not finished.is_set():
                pytest.fail("Reader returned before evidence worker drained")
        finally:
            release.set()
            await reader.close()
        with pytest.raises(SourceReaderError):
            await reader.read_entry(entry.reference)

    asyncio.run(check())


def test_onedrive_content_only_pins_metadata_capture(saved_catalog):
    item = replace(
        fact("onedrive", "onedrive_content", "file", "ev-drive-content"),
        fact_kind=AcquisitionFactKind.COMPONENT_OBSERVATION,
        parent_resource_kind="onedrive_item",
        parent_resource_identity="file",
        component_kind="item_content",
        source_version_locator=SourceVersionLocator(
            kind="content_capture",
            evidence_id="ev-drive-content",
            capture_id="ev-drive-content",
            resource_identity="file",
            component_kind="item_content",
            resource_version="etag-1",
        ),
    )
    seq = publish(
        saved_catalog,
        [item],
        roles=("component",),
        entry_kind="component",
        scope={"resource_kind": "onedrive_item"},
    )

    async def check():
        reader = reader_api(saved_catalog)
        try:
            entry = await reader.catalog.get_release_entry(seq)
            result = await reader.read_entry(entry.reference)
            if result.selection is None:
                pytest.fail(
                    "Content-only release did not reconstruct its pinned parent"
                )
            if result.selection.record.source_bytes.reference != "a1-response:ev-drive":
                pytest.fail("Content-only parent did not use capture-bound metadata")
            if len(result.selection.record.attachments) != 1:
                pytest.fail("Content-only release lost its exact content")
        finally:
            await reader.close()

    asyncio.run(check())


def test_acquired_calendar_surface_requires_evidence(saved_catalog):
    item = replace(
        fact(
            "outlook_calendar",
            "calendar_event_surface",
            "event",
            "unused",
            component_kind="attachments",
        ),
        fact_kind=AcquisitionFactKind.COMPONENT_OBSERVATION,
        parent_resource_kind="calendar_event",
        parent_resource_identity="event",
        evidence_id=None,
        source_version_locator=None,
        transition_reason='{"profile_version":"outlook-calendar-full-v1","status":"acquired"}',
    )
    seq = publish(saved_catalog, [item], roles=("component",), entry_kind="component")

    async def check():
        reader = reader_api(saved_catalog)
        try:
            entry = await reader.catalog.get_release_entry(seq)
            with pytest.raises(SourceReaderError):
                await reader.read_entry(entry.reference)
        finally:
            await reader.close()

    asyncio.run(check())


def test_content_parent_reuses_exact_metadata_source_version(saved_catalog):
    """Content enrichment must not fabricate a new primary representation."""
    from message_ingest.acquisition.handoff import source_state_key
    from tests.source_reader.release_nonmail_helpers import save_evidence

    raw = {"id": "file", "name": "report.txt", "eTag": "etag-1"}
    save_evidence(saved_catalog, "same-metadata", raw)
    catalog = Catalog(f"sqlite:///{saved_catalog['database']}")
    try:
        with catalog.writer_session() as session:
            session.execute(
                text(
                    "UPDATE onedrive_content_captures "
                    "SET planned_metadata_evidence_id='same-metadata'"
                )
            )
    finally:
        catalog.close()
    primary = replace(
        fact("onedrive", "onedrive_item", "file", "same-metadata"),
        source_version_locator=SourceVersionLocator(
            kind="evidence",
            evidence_id="same-metadata",
            resource_identity="file",
            resource_version=source_state_key(raw),
        ),
    )
    child = replace(
        fact("onedrive", "onedrive_content", "file", "ev-drive-content"),
        fact_kind=AcquisitionFactKind.COMPONENT_OBSERVATION,
        parent_resource_kind="onedrive_item",
        parent_resource_identity="file",
        component_kind="item_content",
        source_version_locator=SourceVersionLocator(
            kind="content_capture",
            evidence_id="ev-drive-content",
            capture_id="ev-drive-content",
            resource_identity="file",
            component_kind="item_content",
            resource_version="etag-1",
        ),
    )
    first = publish(saved_catalog, [primary])
    second = publish(
        saved_catalog,
        [child],
        roles=("component",),
        entry_kind="component",
        scope={"resource_kind": "onedrive_item"},
    )

    async def check():
        reader = reader_api(saved_catalog)
        try:
            refs = []
            for seq in (first, second):
                entry = await reader.catalog.get_release_entry(seq)
                result = await reader.read_entry(entry.reference)
                refs.append(result.selection.source)
            if refs[0] != refs[1]:
                pytest.fail("Content-only release invented a new source version")
        finally:
            await reader.close()

    asyncio.run(check())
