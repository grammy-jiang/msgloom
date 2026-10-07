"""Pin Calendar provider projections and application composition contracts."""

from dataclasses import fields

import pytest
from itemadapter import ItemAdapter

from message_ingest.items.microsoft.outlook import calendar
from microsoft_graph.items.outlook import (
    OutlookCalendarAttachmentItem,
    OutlookCalendarItem,
    OutlookEventItem,
)


@pytest.mark.parametrize(
    "provider,consumer,context,raw,expected",
    [
        (
            OutlookCalendarItem,
            calendar.OutlookCalendarItem,
            {},
            {
                "name": "",
                "changeKey": "version",
                "isDefaultCalendar": False,
                "canEdit": False,
                "canShare": True,
                "canViewPrivateItems": False,
            },
            {
                "name": "",
                "change_key": "version",
                "is_default_calendar": False,
                "can_edit": False,
                "can_share": True,
                "can_view_private_items": False,
            },
        ),
        (
            OutlookEventItem,
            calendar.OutlookCalendarEventItem,
            {},
            {
                "changeKey": "",
                "subject": "",
                "start": {"dateTime": "2026-09-01T00:00:00", "timeZone": "UTC"},
                "end": {"dateTime": "2026-09-02T00:00:00", "timeZone": "UTC"},
                "type": "exception",
                "seriesMasterId": "master",
                "isAllDay": False,
                "isCancelled": False,
                "hasAttachments": False,
            },
            {
                "change_key": "",
                "subject": "",
                "event_type": "exception",
                "series_master_id": "master",
                "is_all_day": False,
                "is_cancelled": False,
                "has_attachments": False,
            },
        ),
        (
            OutlookCalendarAttachmentItem,
            calendar.OutlookCalendarAttachmentItem,
            {"event_id": "event"},
            {
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": "",
                "contentType": "",
                "size": 0,
                "isInline": False,
                "contentBytes": "AAAA",
            },
            {
                "attachment_type": "#microsoft.graph.fileAttachment",
                "name": "",
                "content_type": "",
                "size": 0,
                "is_inline": False,
            },
        ),
    ],
)
def test_provider_fields_and_consumer_composition(
    provider, consumer, context, raw, expected
):
    raw = {"id": "resource", "unknown": {"retained": True}, **raw}
    standalone = provider.from_graph(raw, **context)
    observation = consumer.from_graph(
        raw, **context, observed_at="now", evidence_id=None, run_id="run"
    )
    for item in (standalone, observation.provider):
        if item.raw is not raw:
            pytest.fail("Provider mapping must retain raw identity")
        actual = ItemAdapter(item).asdict()
        for name, value in expected.items():
            if actual[name] != value or type(actual[name]) is not type(value):
                pytest.fail(f"Provider projection changed for {name}")
        if isinstance(item, OutlookEventItem) and (
            item.start is not raw["start"] or item.end is not raw["end"]
        ):
            pytest.fail("Date/time objects must remain unchanged")
    if "provider" in {field.name for field in fields(observation)}:
        pytest.fail("Composition must not extend the persisted item schema")


@pytest.mark.parametrize(
    "provider,context",
    [
        (OutlookCalendarItem, {}),
        (OutlookEventItem, {}),
        (OutlookCalendarAttachmentItem, {"event_id": "event"}),
    ],
)
def test_partial_resources_validate_only_shape_and_identity(provider, context):
    item = provider.from_graph({"id": "resource"}, **context)
    if getattr(item, "name", getattr(item, "subject", None)) is not None:
        pytest.fail("Missing optional fields must remain absent")
    for raw in ({}, {"id": None}, {"id": ""}, {"id": 12}, {"id": []}):
        with pytest.raises(ValueError, match="non-empty id"):
            provider.from_graph(raw, **context)
    with pytest.raises(TypeError, match="JSON object"):
        provider.from_graph([], **context)


def test_consumer_projection_retains_context_identity_and_tracks_raw_changes():
    item = calendar.OutlookCalendarItem("calendar", {}, "now", None, None)
    item.raw["name"] = "new name"
    if item.provider.calendar_id != "calendar" or item.provider.name != "new name":
        pytest.fail("Consumer construction and mutable raw behavior changed")
