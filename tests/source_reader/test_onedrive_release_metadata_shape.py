"""Validate released OneDrive content metadata through the public reader."""

import asyncio
from dataclasses import replace

import pytest
from sqlalchemy import text

from message_ingest.acquisition.handoff import (
    AcquisitionFactKind,
    SourceVersionLocator,
)
from message_ingest.catalog import Catalog
from msgloom.sources import ContentKind, SourceEvidenceError
from tests.source_reader.release_nonmail_helpers import (
    fact,
    publish,
    reader_api,
    save_evidence,
)


def _content_only_release(saved, label, facet):
    """Publish content whose capture pins the supplied metadata shape."""
    evidence_id = f"shape-metadata-{label}"
    raw = {
        "id": "file",
        "name": "report.txt",
        "eTag": "etag-1",
        **facet,
    }
    save_evidence(saved, evidence_id, raw)
    catalog = Catalog(f"sqlite:///{saved['database']}")
    try:
        with catalog.writer_session() as session:
            session.execute(
                text(
                    "UPDATE onedrive_content_captures "
                    "SET planned_metadata_evidence_id=:evidence_id"
                ),
                {"evidence_id": evidence_id},
            )
    finally:
        catalog.close()
    item = replace(
        fact(
            "onedrive",
            "onedrive_content",
            "file",
            "ev-drive-content",
        ),
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
    return publish(
        saved,
        [item],
        roles=("component",),
        entry_kind="component",
        scope={"resource_kind": "onedrive_item"},
    )


@pytest.mark.parametrize(
    ("label", "facet", "valid", "content_type"),
    [
        ("null", {"file": None}, False, None),
        ("list", {"file": []}, False, None),
        ("string", {"file": "invalid"}, False, None),
        ("number", {"file": 42}, False, None),
        ("object", {"file": {"mimeType": "text/plain"}}, True, "text/plain"),
        ("absent", {}, True, None),
    ],
)
def test_public_reader_validates_onedrive_file_facet(
    saved_catalog,
    label,
    facet,
    valid,
    content_type,
):
    """Require an object when the metadata contains a OneDrive file facet."""
    seq = _content_only_release(saved_catalog, label, facet)

    async def check() -> None:
        reader = reader_api(saved_catalog)
        try:
            entry = await reader.catalog.get_release_entry(seq)
            if entry is None:
                pytest.fail("fixture did not publish the release entry")
            if not valid:
                with pytest.raises(
                    SourceEvidenceError,
                    match="OneDrive file facet must be an object",
                ):
                    await reader.read_entry(entry.reference)
                return
            result = await reader.read_entry(entry.reference)
            if result.selection is None:
                pytest.fail("content-only release did not reconstruct its parent")
            attachments = result.selection.record.attachments
            if len(attachments) != 1:
                pytest.fail("content-only release did not retain exact content")
            attachment = attachments[0]
            if attachment.saved_bytes is None:
                pytest.fail("content-only release omitted its saved-byte reference")
            if await reader.load_saved_bytes(attachment.saved_bytes) != b"content":
                pytest.fail("content-only release loaded different bytes")
            if attachment.content_type != content_type:
                pytest.fail("file facet content type changed")
            expected_kind = ContentKind.PLAIN if content_type else ContentKind.BINARY
            if attachment.content_kind is not expected_kind:
                pytest.fail("file facet content kind changed")
        finally:
            await reader.close()

    asyncio.run(check())


@pytest.mark.parametrize(
    ("label", "facet", "valid", "content_type", "expected_kind"),
    [
        ("mime-number", {"file": {"mimeType": 42}}, False, None, None),
        (
            "mime-list",
            {"file": {"mimeType": ["text/plain"]}},
            False,
            None,
            None,
        ),
        (
            "mime-object",
            {"file": {"mimeType": {"type": "text/plain"}}},
            False,
            None,
            None,
        ),
        ("mime-bool", {"file": {"mimeType": True}}, False, None, None),
        ("mime-zero", {"file": {"mimeType": 0}}, False, None, None),
        ("mime-empty-list", {"file": {"mimeType": []}}, False, None, None),
        ("mime-empty-object", {"file": {"mimeType": {}}}, False, None, None),
        ("mime-false", {"file": {"mimeType": False}}, False, None, None),
        (
            "mime-string",
            {"file": {"mimeType": "text/plain"}},
            True,
            "text/plain",
            ContentKind.PLAIN,
        ),
        ("mime-null", {"file": {"mimeType": None}}, True, None, ContentKind.BINARY),
        ("mime-absent", {"file": {}}, True, None, ContentKind.BINARY),
    ],
)
def test_public_reader_validates_onedrive_mime_type(
    saved_catalog,
    label,
    facet,
    valid,
    content_type,
    expected_kind,
):
    """Require a string or null when the OneDrive file facet declares MIME."""
    seq = _content_only_release(saved_catalog, label, facet)

    async def check() -> None:
        reader = reader_api(saved_catalog)
        try:
            entry = await reader.catalog.get_release_entry(seq)
            if entry is None:
                pytest.fail("fixture did not publish the release entry")
            if not valid:
                with pytest.raises(
                    SourceEvidenceError,
                    match="OneDrive file MIME type must be a string",
                ):
                    await reader.read_entry(entry.reference)
                return
            result = await reader.read_entry(entry.reference)
            if result.selection is None:
                pytest.fail("content-only release did not reconstruct its parent")
            attachments = result.selection.record.attachments
            if len(attachments) != 1:
                pytest.fail("content-only release did not retain exact content")
            attachment = attachments[0]
            if attachment.saved_bytes is None:
                pytest.fail("content-only release omitted its saved-byte reference")
            if await reader.load_saved_bytes(attachment.saved_bytes) != b"content":
                pytest.fail("content-only release loaded different bytes")
            if attachment.content_type != content_type:
                pytest.fail("file MIME content type changed")
            if attachment.content_kind is not expected_kind:
                pytest.fail("file MIME content kind changed")
        finally:
            await reader.close()

    asyncio.run(check())
