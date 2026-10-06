"""Test exact non-Mail releases against current-state changes and bad pins."""

import asyncio
from dataclasses import replace

import pytest
from sqlalchemy import text

from message_ingest.catalog import Catalog
from msgloom.sources import CollectedSelectionCodec, SourceReaderError
from tests.source_reader.release_nonmail_helpers import (
    SOURCE,
    fact,
    publish,
    reader_api,
)


@pytest.mark.parametrize(
    "stream,kind,identity,evidence,scope,subject",
    [
        (
            "todo",
            "todo_task",
            '["list","task"]',
            "ev-todo-old",
            ("todo_list", "list"),
            "Old task",
        ),
        (
            "contacts",
            "contact",
            "contact",
            "ev-contact",
            ("contacts_collection", "default"),
            "Synthetic Contact",
        ),
        ("onedrive", "onedrive_item", "file", "ev-drive", (None, None), "report.txt"),
    ],
)
def test_exact_release_roundtrip_after_current_mutation(
    saved_catalog,
    stream,
    kind,
    identity,
    evidence,
    scope,
    subject,
):
    item = fact(
        stream, kind, identity, evidence, scope_kind=scope[0], scope_identity=scope[1]
    )
    seq = publish(saved_catalog, [item])

    async def check():
        reader = reader_api(saved_catalog)
        try:
            entry = await reader.catalog.get_release_entry(seq)
            before = await reader.read_entry(entry.reference)
            if before.selection is None:
                pytest.fail("Readable release lost its exact selection")
            if before.selection.record.subject != subject:
                pytest.fail("Reader did not reconstruct released evidence")
            codec = CollectedSelectionCodec()
            if codec.decode(codec.encode(before.selection)) != before.selection:
                pytest.fail("CollectedSelection roundtrip changed exact input")
            catalog = Catalog(f"sqlite:///{saved_catalog['database']}")
            try:
                with catalog.writer_session() as session:
                    session.execute(
                        text(
                            "UPDATE onedrive_items SET name='future', raw='{}', "
                            "latest_evidence_id='ev-todo-new'"
                        )
                    )
            finally:
                catalog.close()
            after = await reader.read_entry(entry.reference)
            if after != before:
                pytest.fail("Mutable current state changed released input")
            context = await reader.read_supporting_context(entry.reference)
            if context.selection != before.selection:
                pytest.fail("Supporting context did not pin exact selection")
            if context.primary:
                pytest.fail("Historical context expanded primary work")
        finally:
            await reader.close()

    asyncio.run(check())


@pytest.mark.parametrize("failure", ["missing", "corrupt", "cross_source"])
def test_required_evidence_fails_closed(saved_catalog, failure):
    item = fact(
        "todo",
        "todo_task",
        '["list","task"]',
        "ev-todo-old",
        scope_kind="todo_list",
        scope_identity="list",
    )
    seq = publish(saved_catalog, [item])
    catalog = Catalog(f"sqlite:///{saved_catalog['database']}")
    try:
        with catalog.writer_session() as session:
            path = session.execute(
                text(
                    "SELECT response_body_path FROM raw_http_evidence "
                    "WHERE evidence_id='ev-todo-old'"
                )
            ).scalar_one()
            if failure == "cross_source":
                session.execute(
                    text(
                        "UPDATE raw_http_evidence SET source_id='other' "
                        "WHERE evidence_id='ev-todo-old'"
                    )
                )
            else:
                from pathlib import Path

                if failure == "missing":
                    Path(path).unlink()
                else:
                    Path(path).write_bytes(b"corrupt")
    finally:
        catalog.close()

    async def check():
        reader = reader_api(saved_catalog)
        try:
            entry = await reader.catalog.get_release_entry(seq)
            with pytest.raises(SourceReaderError):
                await reader.read_entry(entry.reference)
        finally:
            await reader.close()

    asyncio.run(check())


def test_locator_resource_mismatch_rejected(saved_catalog):
    item = fact(
        "todo",
        "todo_task",
        '["list","task"]',
        "ev-todo-old",
        scope_kind="todo_list",
        scope_identity="list",
    )
    if item.source_version_locator is None:
        pytest.fail("Fixture requires an exact locator")
    item = replace(
        item,
        source_version_locator=replace(
            item.source_version_locator, resource_identity='["other","task"]'
        ),
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


@pytest.mark.parametrize(
    "stream,kind,identity,scope_kind,scope,reason",
    [
        (
            "todo",
            "todo_task",
            '["list","task"]',
            "todo_source",
            SOURCE,
            "snapshot_absent",
        ),
        (
            "contacts",
            "contact",
            "contact",
            "contacts_collection",
            "folder:folder-1",
            "snapshot_absent",
        ),
        (
            "onedrive",
            "onedrive_item",
            "file",
            "onedrive_source",
            SOURCE,
            "resync_absent",
        ),
        (
            "outlook_calendar",
            "calendar_event",
            "event",
            "calendar_window",
            '["default","2026-09-01T00:00:00Z","2026-10-01T00:00:00Z"]',
            '{"attempt":0,"kind":"removed","removed_reason":"deleted"}',
        ),
    ],
)
def test_scoped_absence_has_no_fabricated_payload(
    saved_catalog,
    stream,
    kind,
    identity,
    scope_kind,
    scope,
    reason,
):
    from message_ingest.acquisition.handoff import AcquisitionFactKind

    item = replace(
        fact(stream, kind, identity, "ev-contact"),
        fact_kind=AcquisitionFactKind.SCOPED_STATE_TRANSITION,
        scope_kind=scope_kind,
        scope_identity=scope,
        transition_reason=reason,
        source_version_locator=None,
        authority_revision="3",
    )
    seq = publish(saved_catalog, [item], roles=("transition",), entry_kind="transition")

    async def check():
        reader = reader_api(saved_catalog)
        try:
            entry = await reader.catalog.get_release_entry(seq)
            result = await reader.read_entry(entry.reference)
            if result.selection is not None or len(result.transitions) != 1:
                pytest.fail("Scoped absence became a source payload")
            transition = result.transitions[0]
            if (
                transition.scope_identity != scope
                or transition.resource_identity != identity
                or transition.reason != reason
                or transition.authority_revision != "3"
            ):
                pytest.fail("Transition lost exact authority scope")
        finally:
            await reader.close()

    asyncio.run(check())


def test_todo_component_preserves_child_and_parent(saved_catalog):
    from message_ingest.acquisition.handoff import AcquisitionFactKind
    from tests.source_reader.release_nonmail_helpers import save_evidence

    save_evidence(
        saved_catalog,
        "checklist",
        {
            "value": [
                {"id": "check", "displayName": "Pinned checklist", "isChecked": False}
            ]
        },
    )
    parent = fact(
        "todo",
        "todo_task",
        '["list","task"]',
        "ev-todo-old",
        scope_kind="todo_list",
        scope_identity="list",
    )
    child = replace(
        fact(
            "todo",
            "todo_checklist_item",
            '["list","task","check"]',
            "checklist",
            component_kind="checklist_item",
        ),
        fact_kind=AcquisitionFactKind.COMPONENT_OBSERVATION,
        parent_resource_kind="todo_task",
        parent_resource_identity='["list","task"]',
        scope_kind="todo_list",
        scope_identity="list",
    )
    seq = publish(saved_catalog, [parent, child], roles=("primary", "component"))

    async def check():
        reader = reader_api(saved_catalog)
        try:
            entry = await reader.catalog.get_release_entry(seq)
            result = await reader.read_entry(entry.reference)
            if len(result.components) != 1:
                pytest.fail("Released child was discarded")
            component = result.components[0]
            if component.record.subject != "Pinned checklist":
                pytest.fail("Released checklist evidence was not reconstructed")
            links = result.selection.record.relationships
            if not any(link.target == component.source for link in links):
                pytest.fail("Task selection omitted exact child lineage")
        finally:
            await reader.close()

    asyncio.run(check())


def test_onedrive_exact_content_capture(saved_catalog):
    from message_ingest.acquisition.handoff import (
        AcquisitionFactKind,
        SourceVersionLocator,
    )

    parent = fact("onedrive", "onedrive_item", "file", "ev-drive")
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
    seq = publish(saved_catalog, [parent, child], roles=("primary", "component"))

    async def check():
        reader = reader_api(saved_catalog)
        try:
            entry = await reader.catalog.get_release_entry(seq)
            result = await reader.read_entry(entry.reference)
            attachments = result.selection.record.attachments
            if len(attachments) != 1:
                pytest.fail("Exact released content was not enriched")
            if await reader.load_saved_bytes(attachments[0].saved_bytes) != b"content":
                pytest.fail("Wrong OneDrive capture selected")
            if "current" in result.selection.source.version:
                pytest.fail("Scheduled source used mutable pseudoversion")
        finally:
            await reader.close()

    asyncio.run(check())


def test_mail_explicitly_unsupported(saved_catalog):
    seq = publish(saved_catalog, [fact("outlook_mail", "message", "message", "ev-old")])

    async def check():
        reader = reader_api(saved_catalog)
        try:
            entry = await reader.catalog.get_release_entry(seq)
            with pytest.raises(SourceReaderError, match="Mail"):
                await reader.read_entry(entry.reference)
        finally:
            await reader.close()

    asyncio.run(check())
