"""Validate Calendar terminal metadata through the public release reader."""

import asyncio
import json
from dataclasses import replace

import pytest

from message_ingest.acquisition.handoff import AcquisitionFactKind
from msgloom.sources import SourceReferenceError
from tests.source_reader.release_nonmail_helpers import fact, publish, reader_api


@pytest.mark.parametrize(
    ("reason", "valid"),
    [
        (
            json.dumps(
                {
                    "profile_version": "outlook-calendar-full-v1",
                    "status": "unsupported",
                },
                separators=(",", ":"),
            ),
            True,
        ),
        ("[]", False),
        ("null", False),
        ('"terminal"', False),
        ("42", False),
    ],
)
def test_public_reader_validates_calendar_terminal_metadata_shape(
    saved_catalog,
    reason,
    valid,
):
    """Exercise terminal metadata via the released public catalog/read path."""
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
        transition_reason=reason,
    )
    seq = publish(
        saved_catalog,
        [item],
        roles=("component",),
        entry_kind="component",
    )

    async def check() -> None:
        reader = reader_api(saved_catalog)
        try:
            entry = await reader.catalog.get_release_entry(seq)
            if entry is None:
                pytest.fail("fixture did not publish the release entry")
            if valid:
                result = await reader.read_entry(entry.reference)
                if len(result.components) != 1:
                    pytest.fail("valid terminal component was not reconstructed")
                if not result.components[0].record.limitations:
                    pytest.fail("valid terminal limitation was not preserved")
                return
            with pytest.raises(
                SourceReferenceError,
                match="Calendar surface terminal metadata",
            ):
                await reader.read_entry(entry.reference)
        finally:
            await reader.close()

    asyncio.run(check())
