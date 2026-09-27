"""
Validate CLI arguments and their mapping into the native Scrapy crawler
process.
"""

from __future__ import annotations

import argparse
from typing import cast

import pytest
from scrapy.crawler import CrawlerProcessBase
from scrapy.exceptions import UsageError

from message_ingest.commands.outlook_delta import Command as OutlookDeltaCommand
from message_ingest.commands.outlook_discover import Command as OutlookDiscoverCommand
from message_ingest.commands.outlook_full import Command as OutlookFullCommand
from message_ingest.profiles import FULL_V1


class FakeCrawlerProcess:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.started = False
        self.bootstrap_failed = False

    def crawl(self, spider_name: str, **kwargs):
        self.calls.append((spider_name, kwargs))

    def start(self) -> None:
        self.started = True


def _run(command, args: list[str], opts: argparse.Namespace) -> FakeCrawlerProcess:
    process = FakeCrawlerProcess()
    command.crawler_process = process
    command.run(args, opts)
    return process


def test_discover_command_maps_cli_options_to_spider_arguments() -> None:
    process = _run(
        OutlookDiscoverCommand(),
        [],
        argparse.Namespace(folder="archive", page_size=100, max_pages=3),
    )

    if process.started is not True:
        pytest.fail("Expected: process.started is True")
    if process.calls != [
        (
            "outlook_discover",
            {"folder": "archive", "page_size": "100", "max_pages": "3"},
        )
    ]:
        pytest.fail(
            'Expected: process.calls == [ ( "outlook_discover", { "folder": "archive", "page_size": "100", "max_pages": "3", }, ) ]'
        )


def test_discover_command_rejects_positional_arguments() -> None:
    command = OutlookDiscoverCommand()
    command.crawler_process = cast(CrawlerProcessBase, FakeCrawlerProcess())
    with pytest.raises(UsageError):
        command.run(
            ["unexpected"],
            argparse.Namespace(folder="", page_size=25, max_pages=0),
        )


def test_delta_command_maps_page_size_and_reconciliation() -> None:
    process = _run(
        OutlookDeltaCommand(),
        [],
        argparse.Namespace(page_size=50, reconcile=False),
    )

    if process.calls != [
        ("outlook_delta", {"page_size": "50", "reconcile_global": "0"})
    ]:
        pytest.fail(
            'Expected: process.calls == [ ( "outlook_delta", { "page_size": "50", "reconcile_global": "0", }, ) ]'
        )


def test_full_command_accepts_multiple_ids_and_deduplicates_them() -> None:
    process = _run(
        OutlookFullCommand(),
        ["message-1", "message-2", "message-1"],
        argparse.Namespace(operation="enrich", acquisition_profile=FULL_V1),
    )

    if process.calls != [
        (
            "outlook_full",
            {
                "message_ids": "message-1,message-2",
                "operation": "enrich",
                "profile": FULL_V1,
            },
        )
    ]:
        pytest.fail(
            'Expected: process.calls == [ ( "outlook_full", { "message_ids": "message-1,message-2", "operation": "enrich", "profile": FULL_V1, }, ) ]'
        )


def test_full_command_requires_at_least_one_message_id() -> None:
    command = OutlookFullCommand()
    command.crawler_process = cast(CrawlerProcessBase, FakeCrawlerProcess())
    with pytest.raises(UsageError):
        command.run(
            [],
            argparse.Namespace(operation="refresh", acquisition_profile=FULL_V1),
        )


def test_command_sets_exitcode_when_crawler_bootstrap_fails() -> None:
    command = OutlookDeltaCommand()
    process = FakeCrawlerProcess()
    process.bootstrap_failed = True
    command.crawler_process = cast(CrawlerProcessBase, process)

    command.run([], argparse.Namespace(page_size=25, reconcile=True))

    if command.exitcode != 1:
        pytest.fail("Expected: command.exitcode == 1")
