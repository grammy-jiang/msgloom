"""Validate persisted Calendar attachment MIME through the public reader."""

import asyncio
from dataclasses import replace

import pytest
from sqlalchemy import select

from message_ingest.acquisition.handoff import FactSpec
from message_ingest.catalog import Catalog
from message_ingest.catalog.models.handoff import AcquisitionFact
from message_ingest.catalog.stores.microsoft.outlook.calendar import (
    OutlookCalendarStore,
)
from message_ingest.items.microsoft.outlook.calendar import (
    OutlookCalendarAttachmentItem,
)
from msgloom.sources import ContentKind, SourceEvidenceError
from tests.source_reader.release_nonmail_helpers import (
    SOURCE,
    WHEN,
    fact,
    publish,
    reader_api,
    save_evidence,
)


def _attachment_release(saved, metadata):
    """Stage real attachment metadata and release its exact event binding."""
    raw = {
        "id": "attachment",
        "@odata.type": "#microsoft.graph.fileAttachment",
        "name": "note.txt",
        "size": 5,
        "isInline": False,
        **metadata,
    }
    save_evidence(saved, "attachment-metadata", {"value": [raw]})
    save_evidence(
        saved,
        "attachment-event",
        {"id": "event", "subject": "Event", "changeKey": "v1"},
    )
    catalog = Catalog(f"sqlite:///{saved['database']}")
    try:
        store = OutlookCalendarStore(catalog, source_id=SOURCE)
        store.persist_attachment_metadata(
            OutlookCalendarAttachmentItem.from_graph(
                raw,
                event_id="event",
                observed_at=WHEN,
                evidence_id="attachment-metadata",
                run_id="attachment-shape-run",
                resource_version="v1",
            )
        )
        with catalog.Session() as session:
            children = [
                FactSpec.from_json(payload)
                for payload in session.scalars(select(AcquisitionFact.payload))
            ]
    finally:
        catalog.close()
    parent = fact("outlook_calendar", "calendar_event", "event", "attachment-event")
    if parent.source_version_locator is None:
        pytest.fail("fixture did not bind the parent source version")
    parent = replace(
        parent,
        source_version_locator=replace(
            parent.source_version_locator, resource_version="v1"
        ),
    )
    return publish(
        saved,
        [parent, *children],
        roles=("primary", *("component" for _ in children)),
    )


@pytest.mark.parametrize(
    ("metadata", "valid", "content_type", "expected_kind"),
    [
        pytest.param({"contentType": 42}, False, None, None, id="number"),
        pytest.param({"contentType": ["private-mime"]}, False, None, None, id="list"),
        pytest.param(
            {"contentType": {"type": "private-mime"}},
            False,
            None,
            None,
            id="object",
        ),
        pytest.param({"contentType": True}, False, None, None, id="boolean"),
        pytest.param({"contentType": 0}, False, None, None, id="zero"),
        pytest.param({"contentType": []}, False, None, None, id="empty-list"),
        pytest.param({"contentType": {}}, False, None, None, id="empty-object"),
        pytest.param({"contentType": False}, False, None, None, id="false"),
        pytest.param(
            {"contentType": "text/plain; charset=utf-8"},
            True,
            "text/plain; charset=utf-8",
            ContentKind.PLAIN,
            id="string",
        ),
        pytest.param(
            {"contentType": ""}, True, "", ContentKind.BINARY, id="empty-string"
        ),
        pytest.param({"contentType": None}, True, None, ContentKind.BINARY, id="null"),
        pytest.param({}, True, None, ContentKind.BINARY, id="absent"),
    ],
)
def test_public_reader_validates_calendar_attachment_content_type(
    saved_catalog, metadata, valid, content_type, expected_kind
):
    """Reject non-string MIME without exposing the saved provider value."""
    seq = _attachment_release(saved_catalog, metadata)

    async def check() -> None:
        reader = reader_api(saved_catalog)
        try:
            entry = await reader.catalog.get_release_entry(seq)
            if entry is None:
                pytest.fail("fixture did not publish the release entry")
            if not valid:
                with pytest.raises(SourceEvidenceError) as caught:
                    await reader.read_entry(entry.reference)
                if str(caught.value) != (
                    "Calendar attachment MIME type must be a string"
                ):
                    pytest.fail("invalid MIME did not produce a bounded error")
                return
            result = await reader.read_entry(entry.reference)
            if result.selection is None:
                pytest.fail("release did not retain its event selection")
            attachments = result.selection.record.attachments
            if len(attachments) != 1:
                pytest.fail("release did not retain its exact attachment")
            attachment = attachments[0]
            if attachment.content_type != content_type:
                pytest.fail("valid attachment MIME metadata changed")
            if attachment.content_kind is not expected_kind:
                pytest.fail("valid attachment MIME classification changed")
            if attachment.name != "note.txt" or attachment.byte_count != 5:
                pytest.fail("attachment metadata changed during MIME mapping")
            if attachment.inline is not False or attachment.saved_bytes is not None:
                pytest.fail("metadata was confused with saved attachment bytes")
        finally:
            await reader.close()

    asyncio.run(check())
