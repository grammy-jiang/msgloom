"""Exact component ownership, content pinning, and context-only releases."""

import asyncio
import json
from dataclasses import replace

import pytest
from sqlalchemy import select

from message_ingest.acquisition.handoff import (
    AcquisitionFactKind,
    FactSpec,
    SourceVersionLocator,
    source_state_key,
)
from message_ingest.catalog import Catalog
from message_ingest.catalog.models.handoff import AcquisitionFact
from message_ingest.catalog.stores.microsoft.outlook.calendar import (
    OutlookCalendarStore,
)
from message_ingest.items.microsoft.outlook.calendar import (
    OutlookCalendarAttachmentContentItem,
    OutlookCalendarAttachmentItem,
)
from msgloom.sources import SourceReaderError
from tests.source_reader.release_nonmail_helpers import (
    SOURCE,
    WHEN,
    fact,
    publish,
    reader_api,
    save_evidence,
)


@pytest.mark.parametrize("broken", [False, True])
def test_calendar_attachment_content_and_version_binding(saved_catalog, broken):
    raw = {"id": "event", "subject": "Event", "changeKey": "v1"}
    save_evidence(saved_catalog, "event-basic", raw)
    attachment = {
        "id": "attachment",
        "@odata.type": "#microsoft.graph.fileAttachment",
        "name": "note.txt",
        "contentType": "text/plain",
        "size": 5,
        "isInline": False,
    }
    save_evidence(saved_catalog, "attachment-meta", {"value": [attachment]})
    save_evidence(saved_catalog, "attachment-raw", b"hello")
    catalog = Catalog(f"sqlite:///{saved_catalog['database']}")
    try:
        store = OutlookCalendarStore(catalog, source_id=SOURCE)
        store.persist_attachment_metadata(
            OutlookCalendarAttachmentItem.from_graph(
                attachment,
                event_id="event",
                observed_at=WHEN,
                evidence_id="attachment-meta",
                run_id="run",
                resource_version="v2" if broken else "v1",
            )
        )
        store.persist_attachment_content(
            OutlookCalendarAttachmentContentItem(
                event_id="event",
                attachment_id="attachment",
                observed_at=WHEN,
                evidence_id="attachment-raw",
                run_id="run",
                resource_version="v2" if broken else "v1",
            )
        )
        with catalog.Session() as session:
            children = [
                FactSpec.from_json(p)
                for p in session.scalars(select(AcquisitionFact.payload))
            ]
    finally:
        catalog.close()
    if broken:
        children = [f for f in children if f.component_kind == "attachment_metadata"]
    parent = fact("outlook_calendar", "calendar_event", "event", "event-basic")
    if parent.source_version_locator is None:
        pytest.fail("Fixture requires an exact locator")
    parent = replace(
        parent,
        source_version_locator=replace(
            parent.source_version_locator, resource_version="v1"
        ),
    )
    seq = publish(
        saved_catalog,
        [parent, *children],
        roles=("primary", *("component" for _ in children)),
    )

    async def check():
        reader = reader_api(saved_catalog)
        try:
            entry = await reader.catalog.get_release_entry(seq)
            if broken:
                with pytest.raises(SourceReaderError):
                    await reader.read_entry(entry.reference)
                return
            result = await reader.read_entry(entry.reference)
            values = result.selection.record.attachments
            if len(values) != 1 or values[0].name != "note.txt":
                pytest.fail("Calendar attachment metadata lost")
            if await reader.load_saved_bytes(values[0].saved_bytes) != b"hello":
                pytest.fail("Calendar attachment selected wrong saved bytes")
        finally:
            await reader.close()

    asyncio.run(check())


def test_exact_detail_component_enriches_calendar_body(saved_catalog):
    save_evidence(
        saved_catalog,
        "basic",
        {
            "id": "event",
            "subject": "Sparse",
            "changeKey": "v1",
        },
    )
    save_evidence(
        saved_catalog,
        "detail",
        {
            "id": "event",
            "subject": "Full",
            "changeKey": "v1",
            "body": {"contentType": "text", "content": "Pinned full body"},
        },
    )
    primary = fact("outlook_calendar", "calendar_event", "event", "basic")
    detail = replace(
        fact(
            "outlook_calendar",
            "calendar_event_surface",
            "event",
            "detail",
            component_kind="detail",
        ),
        fact_kind=AcquisitionFactKind.COMPONENT_OBSERVATION,
        parent_resource_kind="calendar_event",
        parent_resource_identity="event",
        transition_reason='{"profile_version":"full-v1","status":"acquired"}',
    )
    seq = publish(saved_catalog, [primary, detail], roles=("primary", "component"))

    async def check():
        reader = reader_api(saved_catalog)
        try:
            entry = await reader.catalog.get_release_entry(seq)
            result = await reader.read_entry(entry.reference)
            body = result.selection.record.body
            if body is None or body.content != "Pinned full body":
                pytest.fail("Released detail component was not applied")
            if body.saved_bytes.reference != "a1-response:detail":
                pytest.fail("Full body provenance points to sparse evidence")
        finally:
            await reader.close()

    asyncio.run(check())


@pytest.mark.parametrize(
    "kind,stream,identity",
    [
        ("todo_task_list", "todo", '["list"]'),
        ("contact_folder", "contacts", "folder"),
        ("onedrive_drive", "onedrive", "drive"),
        ("calendar", "outlook_calendar", "calendar"),
    ],
)
def test_context_inventory_is_pinned_without_primary_work(
    saved_catalog,
    kind,
    stream,
    identity,
):
    provider_id = "list" if stream == "todo" else identity
    save_evidence(
        saved_catalog,
        "context",
        {
            "id": provider_id,
            "name": "Pinned inventory",
            "displayName": "Pinned inventory",
        },
    )
    item = replace(
        fact(stream, kind, identity, "context"),
        fact_kind=AcquisitionFactKind.CONTROL_CONTEXT,
    )
    seq = publish(saved_catalog, [item], roles=("context",), entry_kind="context")

    async def check():
        reader = reader_api(saved_catalog)
        try:
            entry = await reader.catalog.get_release_entry(seq)
            result = await reader.read_entry(entry.reference)
            context = await reader.read_supporting_context(entry.reference)
            if result.selection is not None or len(result.contexts) != 1:
                pytest.fail("Inventory became primary source work")
            if context.selection != result.contexts[0] or context.primary:
                pytest.fail("Historical inventory lost exact context pin")
        finally:
            await reader.close()

    asyncio.run(check())


def test_onedrive_repeated_id_uses_sanitized_exact_state(saved_catalog):
    old = {"id": "file", "name": "Old", "eTag": "v1"}
    new = {"id": "file", "name": "Winning", "eTag": "v2"}
    save_evidence(
        saved_catalog,
        "drive-duplicates",
        {"value": [old, {**new, "@microsoft.graph.downloadUrl": "secret-fixture"}]},
    )
    key = source_state_key(new)
    item = replace(
        fact("onedrive", "onedrive_item", "file", "drive-duplicates"),
        source_state_key=key,
        source_version_locator=SourceVersionLocator(
            kind="evidence",
            evidence_id="drive-duplicates",
            resource_identity="file",
            resource_version=key,
        ),
    )
    seq = publish(saved_catalog, [item])

    async def check():
        reader = reader_api(saved_catalog)
        try:
            entry = await reader.catalog.get_release_entry(seq)
            result = await reader.read_entry(entry.reference)
            if result.selection.record.subject != "Winning":
                pytest.fail("OneDrive exact state did not disambiguate repeated ID")
            if "secret-fixture" in result.model_dump_json():
                pytest.fail("Preauthenticated URL leaked into reader metadata")
        finally:
            await reader.close()

    asyncio.run(check())


@pytest.mark.parametrize("status", ["pending", "failed", "unrecognized"])
def test_nonterminal_calendar_surface_fails_closed(saved_catalog, status):
    save_evidence(saved_catalog, "event", {"id": "event", "subject": "Event"})
    parent = fact("outlook_calendar", "calendar_event", "event", "event")
    surface = replace(
        fact(
            "outlook_calendar",
            "calendar_event_surface",
            "event",
            "event",
            component_kind="attachments",
        ),
        fact_kind=AcquisitionFactKind.COMPONENT_OBSERVATION,
        parent_resource_kind="calendar_event",
        parent_resource_identity="event",
        transition_reason=json.dumps({"status": status, "profile_version": "full-v1"}),
    )
    seq = publish(saved_catalog, [parent, surface], roles=("primary", "component"))

    async def check():
        reader = reader_api(saved_catalog)
        try:
            entry = await reader.catalog.get_release_entry(seq)
            with pytest.raises(SourceReaderError):
                await reader.read_entry(entry.reference)
        finally:
            await reader.close()

    asyncio.run(check())


def test_same_attachment_id_under_other_parent_is_distinct(saved_catalog):
    """A reused provider ID must not alias a different event's component."""
    save_evidence(saved_catalog, "shared-meta", {"id": "attachment", "name": "Shared"})
    ids = []
    for parent in ("event-a", "event-b"):
        item = replace(
            fact(
                "outlook_calendar",
                "calendar_attachment",
                "attachment",
                "shared-meta",
                component_kind="attachment_metadata",
            ),
            fact_kind=AcquisitionFactKind.COMPONENT_OBSERVATION,
            parent_resource_kind="calendar_event",
            parent_resource_identity=parent,
        )
        ids.append(
            publish(saved_catalog, [item], roles=("component",), entry_kind="component")
        )

    async def check():
        reader = reader_api(saved_catalog)
        try:
            selections = []
            for seq in ids:
                entry = await reader.catalog.get_release_entry(seq)
                result = await reader.read_entry(entry.reference)
                selections.append(result.components[0].source)
            if selections[0] == selections[1]:
                pytest.fail("Component locator aliased a different parent")
        finally:
            await reader.close()

    asyncio.run(check())
