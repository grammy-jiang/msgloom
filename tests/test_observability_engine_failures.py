"""Exercise observability failures through a real Scrapy engine subprocess."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
PROCESS_SECRET = "private-pipeline-payload-9f0d"
CLOSE_SECRET = "private-close-payload-a18b"
CATALOG_CLOSE_SECRET = "private-catalog-close-payload-b42c"
SIGNAL_SECRET = "private-signal-payload-e61f"

RUN = r"""
import sys
import tempfile

from scrapy import signals
from scrapy.crawler import CrawlerProcess

from message_ingest.catalog import Catalog
from message_ingest.pipelines.catalog import CatalogPipeline
from message_ingest.spiders.outlook_discover import OutlookDiscoverSpider


class ProcessFailingPipeline:
    def process_item(self, item, spider):
        raise RuntimeError("private-pipeline-payload-9f0d")


class CloseFailingPipeline:
    def process_item(self, item, spider):
        return item

    def close_spider(self, spider):
        raise RuntimeError("private-close-payload-a18b")




class SignalFailingExtension:
    @classmethod
    def from_crawler(cls, crawler):
        extension = cls()
        crawler.signals.connect(extension.spider_closed, signal=signals.spider_closed)
        return extension

    def spider_closed(self, spider, reason):
        raise RuntimeError("private-signal-payload-e61f")


class FailureSpider(OutlookDiscoverSpider):
    name = "outlook_discover"

    async def start(self):
        self.crawler.stats.set_value("msgloom/crawl/mode", "discovery")
        self.crawler.stats.set_value("msgloom/crawl/run_id", self.run_id)
        self.crawler.stats.set_value(
            "msgloom/crawl/discovery/pagination_exhausted", True
        )
        yield {"private": "private-item-payload-c77e"}


kind = sys.argv[1]
tmpdir = tempfile.TemporaryDirectory()
if kind == "process":
    pipeline = ProcessFailingPipeline
elif kind == "close":
    pipeline = CloseFailingPipeline
else:
    pipeline = CatalogPipeline

    def fail_catalog_close(self):
        raise RuntimeError("private-catalog-close-payload-b42c")

    Catalog.close = fail_catalog_close

extensions = {
    "message_ingest.extensions.log_privacy.OutlookLogPrivacyExtension": 90,
    "message_ingest.extensions.status.OutlookCrawlStatusExtension": 100,
}
if kind == "signal":
    extensions[SignalFailingExtension] = 110

process = CrawlerProcess(
    {
        "BOT_NAME": "observability_failure_fixture",
        "ITEM_PIPELINES": {pipeline: 100},
        "EXTENSIONS": extensions,
        "MSGLOOM_CRAWL_STATUS_ENABLED": True,
        "MSGLOOM_LOG_PRIVACY_ENABLED": True,
        "MSGLOOM_CATALOG_ENABLED": kind == "catalog",
        "MSGLOOM_DATABASE_URL": f"sqlite:///{tmpdir.name}/catalog.sqlite3",
        "LOG_FORMATTER": "message_ingest.logformatter.MessageIngestLogFormatter",
        "LOG_LEVEL": "INFO",
        "STATS_DUMP": True,
        "TELNETCONSOLE_ENABLED": False,
        "REMOTE_CONTROL_ENABLED": False,
        "ROBOTSTXT_OBEY": False,
    }
)
process.crawl(FailureSpider)
process.start()
tmpdir.cleanup()
"""


@pytest.mark.parametrize("kind", ["process", "close", "catalog"])
def test_engine_failure_is_failed_and_private_text_is_redacted(kind: str) -> None:
    result = subprocess.run(
        [sys.executable, "-c", RUN, kind],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    output = result.stdout + result.stderr
    if result.returncode != 0:
        pytest.fail(output)
    if "'msgloom/final/status': 'failed'" not in output:
        pytest.fail("Expected: final status failed in Scrapy stats dump")
    if (
        PROCESS_SECRET in output
        or CLOSE_SECRET in output
        or CATALOG_CLOSE_SECRET in output
    ):
        pytest.fail("Expected: pipeline exception text not in output")
    if "private-item-payload-c77e" in output:
        pytest.fail("Expected: structured item payload not in output")

    if kind == "process":
        if "'msgloom/persistence/item_error_count': 1" not in output:
            pytest.fail("Expected: pipeline item error counter in stats")
        if "Error processing dict" not in output:
            pytest.fail("Expected: privacy-safe item error log")
        return

    if "'msgloom/lifecycle/close_error_count': 1" not in output:
        pytest.fail("Expected: framework close failure counter in stats")
    if "Scraper close failure: error_type=RuntimeError" not in output:
        pytest.fail("Expected: privacy-safe scraper close failure log")


def test_log_privacy_remains_enabled_when_status_reporting_is_disabled() -> None:
    code = RUN.replace(
        '"MSGLOOM_CRAWL_STATUS_ENABLED": True',
        '"MSGLOOM_CRAWL_STATUS_ENABLED": False',
    )
    result = subprocess.run(
        [sys.executable, "-c", code, "process"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    output = result.stdout + result.stderr
    if result.returncode != 0:
        pytest.fail(output)
    if PROCESS_SECRET in output or "private-item-payload-c77e" in output:
        pytest.fail("Expected: privacy protection independent of status extension")
    if "Error processing dict" not in output:
        pytest.fail("Expected: privacy-safe item error remains visible")
    if "msgloom/final/status" in output:
        pytest.fail("Expected: final status absent when status extension is disabled")


def test_signal_handler_exception_is_redacted_and_counted() -> None:
    result = subprocess.run(
        [sys.executable, "-c", RUN, "signal"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    output = result.stdout + result.stderr
    if result.returncode != 0:
        pytest.fail(output)
    if SIGNAL_SECRET in output:
        pytest.fail("Expected: signal-handler exception text not in output")
    if "'msgloom/lifecycle/signal_error_count': 1" not in output:
        pytest.fail("Expected: signal error counter in final stats")
    if "'msgloom/final/status': 'failed'" not in output:
        pytest.fail("Expected: signal handler failure invalidates final status")
    if "signal_handler_error" not in output:
        pytest.fail("Expected: signal handler failure reason in final stats")
    if "error_type=RuntimeError" not in output:
        pytest.fail("Expected: bounded signal-handler error type log")
