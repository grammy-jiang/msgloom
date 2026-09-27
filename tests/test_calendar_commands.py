"""Verify Calendar command argument mapping and validation."""

from __future__ import annotations

import argparse
from types import SimpleNamespace
from typing import cast

import pytest
from scrapy.crawler import CrawlerProcessBase
from scrapy.exceptions import UsageError

from message_ingest.commands.outlook_calendar_discover import (
    Command as CalendarDiscoverCommand,
)
from message_ingest.commands.outlook_calendar_window import (
    Command as CalendarWindowCommand,
    _aware_datetime,
)


class FakeStats:
    """Minimal stats collector for :func:`run_graph`."""

    def get_value(self, key: str, default=None):
        return default


class FakeCrawler:
    """Minimal crawler returned by the fake process."""

    def __init__(self, spider_name: str) -> None:
        self.spider_name = spider_name
        self.stats = FakeStats()
        self.spider = SimpleNamespace(run_failed=False)


class FakeCrawlerProcess:
    """Record the spider and arguments scheduled by one command."""

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


def _run(command, args: list[str], opts: argparse.Namespace) -> FakeCrawlerProcess:
    process = FakeCrawlerProcess()
    command.crawler_process = cast(CrawlerProcessBase, process)
    command.run(args, opts)
    return process


def test_calendar_discover_maps_page_size() -> None:
    process = _run(
        CalendarDiscoverCommand(),
        [],
        argparse.Namespace(page_size=250),
    )
    if process.calls != [
        ("outlook_calendar_discover", {"page_size": "250"})
    ]:
        pytest.fail(f"Unexpected discover command mapping: {process.calls!r}")


def test_calendar_window_maps_declared_scope() -> None:
    process = _run(
        CalendarWindowCommand(),
        [],
        argparse.Namespace(
            start="2026-09-27T00:00:00+10:00",
            end="2026-10-04T00:00:00+10:00",
            calendar="calendar-1",
            page_size=500,
        ),
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
        pytest.fail(f"Unexpected window command mapping: {process.calls!r}")


def test_calendar_commands_reject_positional_arguments() -> None:
    command = CalendarDiscoverCommand()
    command.crawler_process = cast(CrawlerProcessBase, FakeCrawlerProcess())
    with pytest.raises(UsageError):
        command.run(["unexpected"], argparse.Namespace(page_size=100))


def test_calendar_window_rejects_reversed_range() -> None:
    command = CalendarWindowCommand()
    command.crawler_process = cast(CrawlerProcessBase, FakeCrawlerProcess())
    with pytest.raises(UsageError, match="earlier"):
        command.run(
            [],
            argparse.Namespace(
                start="2026-10-04T00:00:00+10:00",
                end="2026-09-27T00:00:00+10:00",
                calendar="",
                page_size=100,
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
        _aware_datetime(value)
