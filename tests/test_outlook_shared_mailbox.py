"""Verify delegated/shared Outlook mailbox paths and scopes."""

from __future__ import annotations

import asyncio
from urllib.parse import urlsplit

import pytest
from scrapy import Request
from scrapy.utils.test import get_crawler

from message_ingest.spiders.microsoft.outlook.calendar.window import (
    OutlookCalendarWindowSpider,
)
from message_ingest.spiders.microsoft.outlook.email.discover import (
    OutlookDiscoverSpider,
)

START = "2026-09-27T00:00:00+10:00"
END = "2026-10-04T00:00:00+10:00"
TARGET = "shared.owner@example.test"


async def _first(spider) -> Request:
    return await anext(spider.start())


def test_mail_shared_target_uses_users_path_and_shared_scope() -> None:
    crawler = get_crawler(
        OutlookDiscoverSpider,
        settings_dict={"MSGLOOM_TARGET_MAILBOX": TARGET},
    )
    spider = OutlookDiscoverSpider.from_crawler(crawler, page_size="10")
    if crawler.settings.getlist("MS_GRAPH_SCOPES") != ["Mail.Read.Shared"]:
        pytest.fail("Expected delegated Mail read scope")
    request = asyncio.run(_first(spider))
    if urlsplit(request.url).path != "/v1.0/users/shared.owner%40example.test/messages":
        pytest.fail(f"Unexpected delegated Mail path: {request.url}")


def test_calendar_shared_target_uses_users_path_and_shared_scope() -> None:
    crawler = get_crawler(
        OutlookCalendarWindowSpider,
        settings_dict={"MSGLOOM_TARGET_MAILBOX": TARGET},
    )
    spider = OutlookCalendarWindowSpider.from_crawler(
        crawler,
        start_datetime=START,
        end_datetime=END,
    )
    if crawler.settings.getlist("MS_GRAPH_SCOPES") != ["Calendars.Read.Shared"]:
        pytest.fail("Expected delegated Calendar read scope")
    request = asyncio.run(_first(spider))
    if urlsplit(request.url).path != (
        "/v1.0/users/shared.owner%40example.test/calendar/calendarView"
    ):
        pytest.fail(f"Unexpected delegated Calendar path: {request.url}")


def test_self_mailbox_keeps_existing_scopes_and_me_path() -> None:
    mail_crawler = get_crawler(OutlookDiscoverSpider)
    mail = OutlookDiscoverSpider.from_crawler(mail_crawler, page_size="10")
    if mail_crawler.settings.getlist("MS_GRAPH_SCOPES") != ["Mail.Read"]:
        pytest.fail("Expected existing self-Mail scope")
    if urlsplit(asyncio.run(_first(mail)).url).path != "/v1.0/me/messages":
        pytest.fail("Expected self mailbox /me path")
