"""Pin provider endpoint bytes and Calendar validation without workflow state."""

from urllib.parse import urlencode

import pytest
from scrapy.utils.test import get_crawler

from microsoft_graph.protocol.calendar import (
    calendar_series_master,
    calendar_window,
    series_master_id,
)
from microsoft_graph.spiders.outlook import OutlookCalendarSpider, OutlookMailSpider


def spider(cls, mailbox=""):
    crawler = get_crawler(cls, {"MS_GRAPH_TARGET_MAILBOX": mailbox})
    return cls.from_crawler(crawler, name="provider")


@pytest.mark.parametrize(
    "mailbox,root", [("", "/me"), ("a+b/@x", "/users/a%2Bb%2F%40x")]
)
def test_mail_resource_paths_and_query_bytes(mailbox, root):
    mail = spider(OutlookMailSpider, mailbox)
    encoded = "A%2FB%2B%3D%252F"
    identifier = "A/B+=%2F"
    cases = {
        mail.messages_path(): f"{root}/messages",
        mail.messages_path(
            folder_id=identifier
        ): f"{root}/mailFolders/{encoded}/messages",
        mail.message_path(identifier): f"{root}/messages/{encoded}",
        mail.message_mime_path(identifier): f"{root}/messages/{encoded}/$value",
        mail.mail_folders_path(): f"{root}/mailFolders",
        mail.mail_folders_path(
            parent_folder_id=identifier
        ): f"{root}/mailFolders/{encoded}/childFolders",
        mail.message_delta_path(
            identifier
        ): f"{root}/mailFolders/{encoded}/messages/delta",
        mail.mail_folder_delta_path(): f"{root}/mailFolders/delta",
    }
    for actual, expected in cases.items():
        if actual != expected:
            pytest.fail(f"Path encoding changed: {actual!r} != {expected!r}")
    query = urlencode(
        {"$select": "id,subject", "$orderby": "receivedDateTime desc", "$top": 25}
    )
    actual = mail.messages_path(
        fields=("id", "subject"), order_by="receivedDateTime desc", page_size=25
    )
    if actual != f"{root}/messages?{query}":
        pytest.fail("Mail list query order/encoding changed")
    query = urlencode({"includeHiddenFolders": "true", "$top": 25})
    if (
        mail.mail_folders_path(include_hidden=True, page_size=25)
        != f"{root}/mailFolders?{query}"
    ):
        pytest.fail("Folder inventory query changed")
    fields = ("id", "body", "internetMessageHeaders")
    query = urlencode({"$select": ",".join(fields)})
    if (
        mail.message_path(identifier, fields=fields)
        != f"{root}/messages/{encoded}?{query}"
    ):
        pytest.fail("Message detail query changed")


@pytest.mark.parametrize(
    "calendar_id,suffix", [("", ""), ("c/+=", "/calendars/c%2F%2B%3D")]
)
@pytest.mark.parametrize("mailbox,root", [("", "/me"), ("a+b@x", "/users/a%2Bb%40x")])
def test_calendar_paths_preserve_default_named_and_delta_grammar(
    calendar_id, suffix, mailbox, root
):
    calendar = spider(OutlookCalendarSpider, mailbox)
    if calendar.calendars_path() != f"{root}/calendars":
        pytest.fail("Calendar inventory path changed")
    if calendar.calendars_path(page_size=100) != f"{root}/calendars?%24top=100":
        pytest.fail("Calendar inventory query bytes changed")
    start, end = "2026-09-27T00:00:00+10:00", "2026-10-04T00:00:00Z"
    event = f"{root}{suffix}/events/e%2F%2B%3D"
    if calendar.event_path("e/+=", calendar_id=calendar_id) != event:
        pytest.fail("Calendar event path changed")
    view = suffix if calendar_id else "/calendar"
    query = urlencode({"startDateTime": start, "endDateTime": end, "$top": 100})
    if (
        calendar.calendar_view_path(start, end, calendar_id=calendar_id, page_size=100)
        != f"{root}{view}/calendarView?{query}"
    ):
        pytest.fail("Bounded calendarView endpoint changed")
    query = urlencode({"startDateTime": start, "endDateTime": end})
    if (
        calendar.calendar_view_delta_path(start, end)
        != f"{root}/calendarView/delta?{query}"
    ):
        pytest.fail("Primary Calendar delta endpoint changed")
    query = urlencode(
        {
            "$select": "id,subject",
            "$expand": "exceptionOccurrences",
        }
    )
    if (
        calendar.series_master_path(
            "e/+=", calendar_id=calendar_id, fields=("id", "subject")
        )
        != f"{event}?{query}"
    ):
        pytest.fail("Series detail query changed")


@pytest.mark.parametrize(
    "start,end",
    [
        ("", "2026-10-04T00:00:00Z"),
        (" 2026-09-27T00:00:00Z", "2026-10-04T00:00:00Z"),
        ("2026-09-27", "2026-10-04T00:00:00Z"),
        ("invalid", "2026-10-04T00:00:00Z"),
        ("2026-10-04T00:00:00Z", "2026-10-04T00:00:00Z"),
        ("2026-10-04T00:00:00-10:00", "2026-10-04T00:00:00Z"),
    ],
)
def test_calendar_window_rejects_invalid_or_reversed_bounds(start, end):
    with pytest.raises(ValueError):
        calendar_window(start, end)


def test_calendar_window_preserves_original_text_and_compares_instants():
    bounds = ("2026-10-04T00:00:00+10:00", "2026-10-04T00:00:00Z")
    if calendar_window(*bounds) != bounds:
        pytest.fail("Window text must survive for opaque scope identity")


@pytest.mark.parametrize(
    "payload,expected",
    [
        ({"type": "seriesMaster"}, "event"),
        ({"type": "occurrence", "seriesMasterId": "master"}, "master"),
        ({"type": "exception", "seriesMasterId": "master"}, "master"),
        ({"type": "singleInstance", "seriesMasterId": "master"}, None),
        ({"type": "occurrence", "seriesMasterId": 1}, None),
        ({"type": "exception", "seriesMasterId": ""}, None),
    ],
)
def test_series_relation_uses_provider_event_type(payload, expected):
    if series_master_id(payload, "event") != expected:
        pytest.fail("Series relationship changed")


@pytest.mark.parametrize(
    "field,value",
    [
        ("cancelledOccurrences", None),
        ("cancelledOccurrences", [{}]),
        ("exceptionOccurrences", None),
        ("exceptionOccurrences", ["id"]),
    ],
)
def test_series_shape_validation(field, value):
    with pytest.raises(TypeError):
        calendar_series_master({"id": "master", field: value}, expected_id="master")


def test_series_parser_retains_object_and_checks_inflight_identity():
    payload = {
        "id": "master",
        "cancelledOccurrences": [""],
        "exceptionOccurrences": [{}],
    }
    if calendar_series_master(payload, expected_id="master") is not payload:
        pytest.fail("Series parser must preserve all provider fields")
    if calendar_series_master({"id": "master"}, expected_id="master") != {
        "id": "master"
    }:
        pytest.fail("Absent occurrence lists must remain valid")
    with pytest.raises(ValueError, match="ID changed in flight"):
        calendar_series_master(payload, expected_id="different")


def test_calendar_series_path_has_no_implicit_projection():
    calendar = spider(OutlookCalendarSpider)
    if calendar.series_master_path("master") != (
        "/me/events/master?%24expand=exceptionOccurrences"
    ):
        pytest.fail("Provider series paths must not select an application profile")
