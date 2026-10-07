"""Validate the read-only OneDrive CLI below one Microsoft namespace."""

import argparse
import json
from types import SimpleNamespace
from typing import cast

import pytest
from scrapy.crawler import CrawlerProcessBase
from scrapy.exceptions import UsageError
from scrapy.settings import Settings

from message_ingest.commands.microsoft import Command


class _CrawlerProcess:
    """Capture the native crawl boundary without starting a reactor."""

    bootstrap_failed = False

    def __init__(self):
        self.calls = []
        self.started = False

    def create_crawler(self, name):
        return SimpleNamespace(
            name=name,
            spider=SimpleNamespace(run_failed=False),
            stats=SimpleNamespace(get_value=lambda key, default=None: default),
        )

    def crawl(self, crawler, **kwargs):
        self.calls.append((crawler.name, kwargs))

    def start(self):
        self.started = True


def _options(arguments):
    command = Command()
    command.settings = Settings()
    process = _CrawlerProcess()
    command.crawler_process = cast(CrawlerProcessBase, process)
    parser = argparse.ArgumentParser()
    command.add_options(parser)
    return command, parser.parse_args(["onedrive", *arguments]), process


@pytest.mark.parametrize("action", ["discover", "delta"])
@pytest.mark.parametrize(
    "options,size",
    [([], "100"), (["--page-size", "1"], "1"), (["--page-size", "1000"], "1000")],
)
def test_onedrive_metadata_dispatches_to_normal_crawl(action, options, size):
    command, opts, process = _options([action, *options])
    command.run([], opts)
    if process.calls != [(f"microsoft_onedrive_{action}", {"page_size": size})]:
        pytest.fail("OneDrive metadata must dispatch exactly one matching crawl")
    if not process.started:
        pytest.fail("OneDrive must enter Scrapy's crawler process")


def test_onedrive_content_preserves_explicit_ids_in_json():
    ids = ["item,a", "item/b%2Fc", "文書?key=value", "item,a"]
    command, opts, process = _options(["content", *ids])
    command.run([], opts)
    if len(process.calls) != 1:
        pytest.fail("OneDrive content must dispatch one normal crawl")
    name, arguments = process.calls[0]
    if name != "microsoft_onedrive_content" or set(arguments) != {"item_ids"}:
        pytest.fail("OneDrive content must pass only explicit item IDs")
    if json.loads(arguments["item_ids"]) != ids[:3]:
        pytest.fail("Content IDs must retain exact bytes and deduplicate in order")


@pytest.mark.parametrize(
    "arguments",
    [
        [],
        ["sync"],
        ["full"],
        ["upload"],
        ["create"],
        ["rename"],
        ["move"],
        ["delete"],
        ["share"],
        ["discover", "item"],
        ["delta", "item", "other-item"],
        ["content"],
        ["content", ""],
        ["content", " item"],
        ["content", "item "],
        ["content", "item", ""],
        ["content", "item", "--page-size", "25"],
    ],
)
def test_onedrive_rejects_unsupported_actions_and_ids(arguments):
    command, opts, process = _options(arguments)
    with pytest.raises(UsageError):
        command.run([], opts)
    if process.calls:
        pytest.fail("Invalid OneDrive requests must fail before scheduling a crawl")


@pytest.mark.parametrize("action", ["discover", "delta", "content"])
@pytest.mark.parametrize(
    "options",
    [
        ["--mailbox", "mailbox"],
        ["--folder", ""],
        ["--folder", "folder"],
        ["--calendar", "calendar"],
        ["--start", "2026-09-29T00:00:00Z"],
        ["--end", "2026-10-01T00:00:00Z"],
        ["--max-pages", "0"],
        ["--max-enrich", "0"],
        ["--reconcile"],
        ["--no-reconcile"],
        ["--operation", "refresh"],
        ["--json"],
        ["--yes"],
        ["--acquisition-profile", "outlook-mail-full-v1"],
    ],
)
def test_onedrive_rejects_unrelated_options(action, options):
    identifiers = ["item"] if action == "content" else []
    command, opts, process = _options([action, *identifiers, *options])
    with pytest.raises(UsageError):
        command.run([], opts)
    if process.calls:
        pytest.fail("Unrelated options must fail before scheduling a crawl")


@pytest.mark.parametrize("action", ["discover", "delta"])
@pytest.mark.parametrize("size", ["0", "1001", "bad"])
def test_onedrive_cli_validates_page_size(action, size):
    with pytest.raises(SystemExit):
        _options([action, "--page-size", size])
