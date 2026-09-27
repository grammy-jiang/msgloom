"""
Validate CLI arguments and their mapping into the native Scrapy crawler
process.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from scrapy.crawler import CrawlerProcessBase
from scrapy.exceptions import UsageError

from message_ingest.commands.outlook_delta import Command as OutlookDeltaCommand
from message_ingest.commands.outlook_discover import Command as OutlookDiscoverCommand
from message_ingest.commands.outlook_full import Command as OutlookFullCommand
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



def test_command_sets_exitcode_when_spider_integrity_failed() -> None:
    command = OutlookDeltaCommand()
    process = FakeCrawlerProcess(run_failed=True)
    command.crawler_process = cast(CrawlerProcessBase, process)

    command.run([], argparse.Namespace(page_size=25, reconcile=True))

    if command.exitcode != 1:
        pytest.fail("Expected spider integrity failure to set exit code 1")


def test_command_sets_exitcode_when_final_crawl_status_failed() -> None:
    command = OutlookDeltaCommand()
    process = FakeCrawlerProcess(final_status="failed")
    command.crawler_process = cast(CrawlerProcessBase, process)

    command.run([], argparse.Namespace(page_size=25, reconcile=True))

    if command.exitcode != 1:
        pytest.fail("Expected failed final crawl status to set exit code 1")


def test_identity_gate_failure_returns_nonzero_before_graph_requests(
    tmp_path,
) -> None:
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scrapy",
            "outlook_discover",
            "-s",
            "MS_GRAPH_AUTH_METHOD=none",
            "-s",
            f"MSGLOOM_DATABASE_URL=sqlite:///{tmp_path / 'catalog.sqlite3'}",
            "-s",
            f"MSGLOOM_RAW_EVIDENCE_DIR={tmp_path / 'raw'}",
            "-s",
            f"JOBDIR={tmp_path / 'job'}",
            "-s",
            "HTTPCACHE_ENABLED=True",
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
            f"Expected identity gate command failure, got {result.returncode}:\n"
            + result.stderr
        )
    if "source_identity_failed" not in result.stderr:
        pytest.fail("Expected source identity failure close reason")
    if "'msgloom/final/status': 'failed'" not in result.stderr:
        pytest.fail("Expected final crawl status to be failed")
    if "requests=0 responses=0" not in result.stderr:
        pytest.fail("Expected zero Graph requests before identity gate")


def test_identity_gate_failure_is_nonzero_without_status_extension(
    tmp_path,
) -> None:
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scrapy",
            "outlook_discover",
            "-s",
            "MS_GRAPH_AUTH_METHOD=none",
            "-s",
            "MSGLOOM_CRAWL_STATUS_ENABLED=False",
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
            "Expected source identity gate failure to set exit code 1 "
            "without crawl status extension"
        )
    if "msgloom/source_identity/gate_failed_count" not in result.stderr:
        pytest.fail("Expected source identity gate failure stat in final dump")


def test_identity_gate_failure_preserves_existing_jobdir_spider_state(
    tmp_path: Path,
) -> None:
    import pickle
    import subprocess
    import sys
    from pathlib import Path

    from message_ingest.acquisition.source_context import ensure_jobdir_context

    root = Path(__file__).parents[1]
    jobdir = tmp_path / "job"
    database_url = f"sqlite:///{tmp_path / 'catalog.sqlite3'}"
    source_id = "source-1"
    ensure_jobdir_context(str(jobdir), source_id, database_url)
    original_state = {
        "msgloom_delta": {
            "run_id": "existing-run",
            "seen_folder_ids": ["f1"],
            "started_folder_ids": ["f1"],
            "completed_folder_ids": [],
            "reconcile_orphan_ids": [],
            "folder_inventory_pending": 1,
            "folder_inventory_complete": False,
            "folder_inventory_failed": False,
            "reconcile_complete": False,
            "run_failed": False,
            "failure_reasons": [],
            "delta_start_scheduled": True,
        }
    }
    state_path = jobdir / "spider.state"
    state_path.write_bytes(pickle.dumps(original_state, protocol=4))

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scrapy",
            "outlook_delta",
            "-s",
            "MS_GRAPH_AUTH_METHOD=none",
            "-s",
            f"MSGLOOM_DATABASE_URL={database_url}",
            "-s",
            f"MSGLOOM_SOURCE_ID={source_id}",
            "-s",
            f"JOBDIR={jobdir}",
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
            f"Expected identity-gate failure, got {result.returncode}:\n"
            + result.stderr
        )
    restored = pickle.loads(state_path.read_bytes())
    if restored != original_state:
        pytest.fail(
            "Expected startup identity failure to preserve existing JOBDIR "
            f"Spider.state, got {restored!r}"
        )


def test_prestart_bootstrap_failure_does_not_access_uninitialized_stats() -> None:
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scrapy",
            "outlook_full",
            ",",
            "-s",
            "LOG_ENABLED=False",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )

    if result.returncode != 1:
        pytest.fail("Expected invalid pre-start crawl to return exit code 1")
    output = result.stdout + result.stderr
    if "Crawler.stats is not set yet" in output:
        pytest.fail("Expected bootstrap failure not to access uninitialized stats")



def test_identity_gate_failure_is_nonzero_with_dummy_stats(tmp_path) -> None:
    import subprocess
    import sys

    root = Path(__file__).parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scrapy",
            "outlook_discover",
            "-s",
            "MS_GRAPH_AUTH_METHOD=none",
            "-s",
            "STATS_CLASS=scrapy.statscollectors.DummyStatsCollector",
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
            "Expected spider integrity state to produce exit code 1 even "
            "with DummyStatsCollector"
        )
    if "source_identity_failed" not in result.stderr:
        pytest.fail("Expected source identity gate failure in command log")
