"""Validate Microsoft Outlook Mail CLI mapping through one public namespace."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from scrapy.crawler import CrawlerProcessBase
from scrapy.exceptions import UsageError

from message_ingest.commands.microsoft import Command as MicrosoftCommand
from message_ingest.profiles import FULL_V1


class FakeStats:
    def __init__(self, final_status: str | None = None) -> None:
        self.final_status = final_status

    def get_value(self, key: str, default=None):
        if key == "msgloom/final/status":
            return self.final_status
        return default


class FakeCrawler:
    def __init__(
        self,
        spider_name: str,
        final_status: str | None = None,
        *,
        run_failed: bool = False,
    ) -> None:
        self.spider_name = spider_name
        self.stats = FakeStats(final_status)
        self.spider = SimpleNamespace(run_failed=run_failed)


class FakeCrawlerProcess:
    def __init__(
        self,
        *,
        final_status: str | None = None,
        run_failed: bool = False,
    ) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.started = False
        self.bootstrap_failed = False
        self.final_status = final_status
        self.run_failed = run_failed

    def create_crawler(self, spider_name: str) -> FakeCrawler:
        return FakeCrawler(
            spider_name,
            self.final_status,
            run_failed=self.run_failed,
        )

    def crawl(self, crawler: FakeCrawler, **kwargs):
        self.calls.append((crawler.spider_name, kwargs))

    def start(self) -> None:
        self.started = True


def _opts(
    *,
    action: str,
    message_ids: list[str] | None = None,
    folder: str | None = None,
    page_size: int | None = None,
    max_pages: int | None = None,
    reconcile: bool | None = None,
    operation: str | None = None,
    acquisition_profile: str | None = None,
) -> argparse.Namespace:
    return argparse.Namespace(
        section="outlook",
        resource_or_action="mail",
        action=action,
        message_ids=message_ids or [],
        json=False,
        yes=False,
        folder=folder,
        page_size=page_size,
        max_pages=max_pages,
        reconcile=reconcile,
        operation=operation,
        acquisition_profile=acquisition_profile,
        start=None,
        end=None,
        calendar=None,
    )


def _run(opts: argparse.Namespace) -> FakeCrawlerProcess:
    command = MicrosoftCommand()
    process = FakeCrawlerProcess()
    command.crawler_process = cast(CrawlerProcessBase, process)
    command.run([], opts)
    return process


def test_discover_maps_cli_options_to_spider_arguments() -> None:
    process = _run(
        _opts(
            action="discover",
            folder="archive",
            page_size=100,
            max_pages=3,
        )
    )
    if process.calls != [
        (
            "outlook_discover",
            {"folder": "archive", "page_size": "100", "max_pages": "3"},
        )
    ]:
        pytest.fail(f"Unexpected Mail discover mapping: {process.calls!r}")


def test_delta_maps_page_size_and_reconciliation() -> None:
    process = _run(_opts(action="delta", page_size=50, reconcile=False))
    if process.calls != [
        ("outlook_delta", {"page_size": "50", "reconcile_global": "0"})
    ]:
        pytest.fail(f"Unexpected Mail delta mapping: {process.calls!r}")


def test_full_accepts_multiple_ids_and_deduplicates_them() -> None:
    process = _run(
        _opts(
            action="full",
            message_ids=["message-1", "message-2", "message-1"],
            operation="enrich",
            acquisition_profile=FULL_V1,
        )
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
        pytest.fail(f"Unexpected Mail full mapping: {process.calls!r}")


def test_full_requires_at_least_one_message_id() -> None:
    command = MicrosoftCommand()
    command.crawler_process = cast(CrawlerProcessBase, FakeCrawlerProcess())
    with pytest.raises(UsageError, match="at least one MESSAGE_ID"):
        command.run([], _opts(action="full"))


def test_command_sets_exitcode_when_crawler_bootstrap_fails() -> None:
    command = MicrosoftCommand()
    process = FakeCrawlerProcess()
    process.bootstrap_failed = True
    command.crawler_process = cast(CrawlerProcessBase, process)

    command.run([], _opts(action="delta"))

    if command.exitcode != 1:
        pytest.fail("Expected crawler bootstrap failure to set exit code 1")


def test_command_sets_exitcode_when_spider_integrity_failed() -> None:
    command = MicrosoftCommand()
    process = FakeCrawlerProcess(run_failed=True)
    command.crawler_process = cast(CrawlerProcessBase, process)

    command.run([], _opts(action="delta"))

    if command.exitcode != 1:
        pytest.fail("Expected spider integrity failure to set exit code 1")


def test_command_sets_exitcode_when_final_crawl_status_failed() -> None:
    command = MicrosoftCommand()
    process = FakeCrawlerProcess(final_status="failed")
    command.crawler_process = cast(CrawlerProcessBase, process)

    command.run([], _opts(action="delta"))

    if command.exitcode != 1:
        pytest.fail("Expected final failed status to set exit code 1")


@pytest.mark.parametrize(
    "path",
    [
        ["outlook_discover"],
        ["outlook_delta"],
        ["outlook_full"],
    ],
)
def test_legacy_top_level_commands_are_not_public(path: list[str]) -> None:
    root = Path(__file__).parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "scrapy", *path],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    if result.returncode != 2:
        pytest.fail(f"Expected legacy command rejection: {result.stderr}")


def test_identity_gate_failure_uses_microsoft_namespace(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scrapy",
            "microsoft",
            "outlook",
            "mail",
            "discover",
            "-s",
            "MS_GRAPH_AUTH_METHOD=none",
            "-s",
            f"MSGLOOM_DATABASE_URL=sqlite:///{tmp_path / 'catalog.sqlite3'}",
            "-s",
            f"MSGLOOM_RAW_EVIDENCE_DIR={tmp_path / 'raw'}",
            "-L",
            "INFO",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    if result.returncode != 1:
        pytest.fail(
            f"Expected identity gate failure, got {result.returncode}:\n"
            + result.stderr
        )
    if "source_identity_failed" not in result.stderr:
        pytest.fail("Expected source identity failure close reason")
