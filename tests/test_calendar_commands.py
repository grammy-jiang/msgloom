"""Verify Outlook Calendar command mapping below the Microsoft namespace."""

from __future__ import annotations

import argparse
from types import SimpleNamespace
from typing import cast

import pytest
from scrapy.crawler import CrawlerProcessBase
from scrapy.exceptions import UsageError

from message_ingest.commands.microsoft import (
    Command as MicrosoftCommand,
)
from message_ingest.commands.microsoft.options import aware_datetime


class FakeStats:
    def get_value(self, key: str, default=None):
        return default


class FakeCrawler:
    def __init__(self, spider_name: str) -> None:
        self.spider_name = spider_name
        self.stats = FakeStats()
        self.spider = SimpleNamespace(run_failed=False)


class FakeCrawlerProcess:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.started = False
        self.bootstrap_failed = False

    def create_crawler(self, spider_name: str) -> FakeCrawler:
        return FakeCrawler(spider_name)

    def crawl(self, crawler: FakeCrawler, **kwargs) -> None:
        self.calls.append((crawler.spider_name, kwargs))

    def start(self) -> None:
        self.started = True


def _opts(
    *,
    action: str,
    page_size: int | None = None,
    start: str | None = None,
    end: str | None = None,
    calendar: str | None = None,
    resource_ids: list[str] | None = None,
) -> argparse.Namespace:
    return argparse.Namespace(
        section="outlook",
        resource_or_action="calendar",
        action=action,
        message_ids=resource_ids or [],
        json=False,
        yes=False,
        folder=None,
        page_size=page_size,
        max_pages=None,
        reconcile=None,
        operation=None,
        max_enrich=None,
        acquisition_profile=None,
        start=start,
        end=end,
        calendar=calendar,
    )


def _run(opts: argparse.Namespace) -> FakeCrawlerProcess:
    command = MicrosoftCommand()
    process = FakeCrawlerProcess()
    command.crawler_process = cast(CrawlerProcessBase, process)
    command.run([], opts)
    return process


def test_calendar_discover_maps_page_size() -> None:
    process = _run(_opts(action="discover", page_size=250))
    if process.calls != [("outlook_calendar_discover", {"page_size": "250"})]:
        pytest.fail(f"Unexpected calendar discover mapping: {process.calls!r}")


def test_calendar_window_maps_declared_scope() -> None:
    process = _run(
        _opts(
            action="window",
            start="2026-09-27T00:00:00+10:00",
            end="2026-10-04T00:00:00+10:00",
            calendar="calendar-1",
            page_size=500,
        )
    )
    if process.calls != [
        (
            "outlook_calendar_window",
            {
                "start_datetime": "2026-09-27T00:00:00+10:00",
                "end_datetime": "2026-10-04T00:00:00+10:00",
                "calendar_id": "calendar-1",
                "page_size": "500",
            },
        )
    ]:
        pytest.fail(f"Unexpected calendar window mapping: {process.calls!r}")


def test_calendar_delta_maps_fixed_primary_calendar_scope() -> None:
    process = _run(
        _opts(
            action="delta",
            start="2026-09-27T00:00:00+10:00",
            end="2026-10-04T00:00:00+10:00",
            page_size=250,
        )
    )
    if process.calls != [
        (
            "outlook_calendar_delta",
            {
                "start_datetime": "2026-09-27T00:00:00+10:00",
                "end_datetime": "2026-10-04T00:00:00+10:00",
                "page_size": "250",
            },
        )
    ]:
        pytest.fail(f"Unexpected calendar delta mapping: {process.calls!r}")


def test_calendar_delta_rejects_named_calendar_scope() -> None:
    command = MicrosoftCommand()
    command.crawler_process = cast(CrawlerProcessBase, FakeCrawlerProcess())
    with pytest.raises(UsageError, match="--calendar"):
        command.run(
            [],
            _opts(
                action="delta",
                start="2026-09-27T00:00:00+10:00",
                end="2026-10-04T00:00:00+10:00",
                calendar="calendar-1",
            ),
        )


def test_calendar_full_maps_event_ids_calendar_and_page_size() -> None:
    process = _run(
        _opts(
            action="full",
            calendar="calendar-1",
            page_size=25,
            resource_ids=["event-1", "event-2", "event-1"],
        )
    )
    if process.calls != [
        (
            "outlook_calendar_full",
            {
                "event_ids": ["event-1", "event-2"],
                "calendar_id": "calendar-1",
                "page_size": "25",
                "operation": "refresh",
                "profile": "outlook-calendar-full-v1",
            },
        )
    ]:
        pytest.fail(f"Unexpected calendar full mapping: {process.calls!r}")


def test_calendar_full_requires_event_id() -> None:
    command = MicrosoftCommand()
    command.crawler_process = cast(CrawlerProcessBase, FakeCrawlerProcess())
    with pytest.raises(UsageError, match="EVENT_ID"):
        command.run([], _opts(action="full"))


def test_full_keeps_opaque_positional_ids() -> None:
    process = _run(_opts(action="full", resource_ids=["opaque,id"]))
    if process.calls[0][1]["event_ids"] != ["opaque,id"]:
        pytest.fail("An opaque event ID must not be split into targets")


@pytest.mark.parametrize("calendar", ["", " ", " calendar-1"])
def test_calendar_rejects_ambiguous_explicit_scope(calendar: str) -> None:
    with pytest.raises(UsageError, match="--calendar"):
        _run(_opts(action="full", resource_ids=["event"], calendar=calendar))


def test_calendar_window_rejects_reversed_range() -> None:
    command = MicrosoftCommand()
    command.crawler_process = cast(CrawlerProcessBase, FakeCrawlerProcess())
    with pytest.raises(UsageError, match="earlier"):
        command.run(
            [],
            _opts(
                action="window",
                start="2026-10-04T00:00:00+10:00",
                end="2026-09-27T00:00:00+10:00",
            ),
        )


@pytest.mark.parametrize(
    "value",
    [
        "",
        "2026-09-27T00:00:00",
        " 2026-09-27T00:00:00+10:00",
        "not-a-date",
    ],
)
def test_calendar_window_datetime_validator_rejects_unsafe_scope(value: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        aware_datetime(value)


@pytest.mark.parametrize(
    "value,message",
    [
        ("", "datetime must be non-empty with no surrounding whitespace"),
        ("invalid", "datetime must be valid ISO-8601"),
        ("2026-09-27T00:00:00", "datetime must include a timezone offset"),
    ],
)
def test_datetime_protocol_errors_keep_cli_text(value, message):
    with pytest.raises(argparse.ArgumentTypeError) as caught:
        aware_datetime(value)
    if str(caught.value) != message:
        pytest.fail("Calendar CLI validation text changed")


def test_calendar_cli_preserves_offset_text_and_compares_instants():
    start, end = "2026-10-04T00:00:00+10:00", "2026-10-04T00:00:00Z"
    if aware_datetime(start) != start or aware_datetime(end) != end:
        pytest.fail("CLI validation must preserve exact datetime text")
    process = _run(_opts(action="window", start=start, end=end))
    if process.calls[0][1]["start_datetime"] != start:
        pytest.fail("Calendar request scope changed")


def test_calendar_dispatch_translates_provider_validation_errors():
    with pytest.raises(UsageError, match="include an offset"):
        _run(_opts(action="window", start="2026-10-04", end="2026-10-05"))


def test_calendar_sync_dispatches_user_level_workflow(monkeypatch) -> None:
    calls = []

    def fake_sync(command, opts) -> None:
        calls.append((command, opts.start, opts.end, opts.page_size, opts.max_enrich))

    import message_ingest.commands.microsoft.outlook.calendar as calendar_command

    monkeypatch.setattr(calendar_command, "run_calendar_sync", fake_sync)
    command = MicrosoftCommand()
    command.crawler_process = cast(CrawlerProcessBase, FakeCrawlerProcess())
    opts = _opts(
        action="sync",
        start="2026-09-27T00:00:00+10:00",
        end="2026-10-04T00:00:00+10:00",
        page_size=60,
    )
    opts.max_enrich = 20
    command.run([], opts)

    if len(calls) != 1 or calls[0][1:] != (
        "2026-09-27T00:00:00+10:00",
        "2026-10-04T00:00:00+10:00",
        60,
        20,
    ):
        pytest.fail(f"Unexpected Calendar sync dispatch: {calls!r}")
