"""Exercise graceful native Scrapy shutdown with accepted Mail writes."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

import pytest
from scrapy import Request, Spider, signals
from scrapy.crawler import AsyncCrawlerRunner
from sqlalchemy import event
from test_mail_pipeline_cancellation import (
    MODES,
    Observer,
    _checkpoint,
    _counts,
    _faults,
    _saved_item,
    _settings,
    _stats,
)
from test_raw_evidence_transactions import _rows

from message_ingest.items.microsoft.outlook.email import OutlookMailDetailItem
from message_ingest.pipelines.microsoft.outlook.email import OutlookMailPipeline


class Entry:
    """Observe the actual scraper task before the unchanged Mail pipeline."""

    def __init__(self, state):
        """Retain the fixture's heterogeneous observations."""
        self.state = state

    @classmethod
    def from_crawler(cls, crawler):
        """Borrow fixture observations from the crawler."""
        return cls(crawler.spider.state)

    def process_item(self, item):
        """Capture the native item task without replacing manager execution."""
        if isinstance(item, OutlookMailDetailItem):
            self.state["item_task"] = asyncio.current_task()
        return item


class MailSpider(Spider):
    """Acquire one local response through native request and scraper paths."""

    name = "mail_shutdown_fixture"

    def __init__(self, state, **kwargs):
        """Receive fixture state through native spider construction."""
        super().__init__(**kwargs)
        self.state = state

    async def start(self):
        """Schedule a local data URL without credentials or network."""
        yield Request("data:text/plain,mail", callback=self.parse)

    def parse(self, response):
        """
        Yield the semantic item whose real evidence was already persisted.
        """
        yield self.state["item"]


async def _wait_for_fixture_startup(
    ready: asyncio.Event,
    errors: list[BaseException],
    crawl: asyncio.Task[None],
) -> None:
    """Wait for fixture readiness or fail on an earlier native crawl exit."""
    waiter = asyncio.create_task(ready.wait())
    try:
        await asyncio.wait(
            {waiter, crawl},
            return_when=asyncio.FIRST_COMPLETED,
        )
        if ready.is_set():
            if errors:
                raise errors[0]
            return
        if crawl.cancelled():
            raise RuntimeError(
                "Native crawl was cancelled before fixture startup readiness"
            )
        if error := crawl.exception():
            raise error
        raise RuntimeError("Native crawl completed before fixture startup readiness")
    finally:
        if not waiter.done():
            waiter.cancel("mail shutdown startup waiter cleanup")
            try:
                await waiter
            except asyncio.CancelledError:
                pass


async def _cleanup_native_crawl(crawler, crawl: asyncio.Task[None]) -> None:
    """Cancel unfinished crawl and close constructed native resources."""
    if not crawl.done():
        crawl.cancel("mail shutdown fixture cleanup")
        try:
            await asyncio.wait_for(crawl, 5)
        except asyncio.CancelledError:
            pass
    elif not crawl.cancelled():
        crawl.exception()

    engine = crawler._engine
    if engine is None:
        return
    if engine.spider is not None:
        await asyncio.wait_for(
            engine.close_async(reason="mail-fixture-cleanup"),
            5,
        )

    # Before start_async(), Scrapy has not emitted engine_stopped.
    # Reactorless eager download handlers therefore still own their clients.
    if not engine._stopping:
        await asyncio.wait_for(engine.downloader.handlers._close(), 5)


async def _crawl(directory, mode, failure, cancels):
    """Request native graceful close while one accepted writer is gated."""
    settings = _settings(directory, mode)
    settings.update(
        {
            "TWISTED_REACTOR_ENABLED": False,
            "ITEM_PIPELINES": {Entry: 50, OutlookMailPipeline: 100, Observer: 200},
            "TELNETCONSOLE_ENABLED": False,
            "LOG_ENABLED": False,
        }
    )
    runner = AsyncCrawlerRunner(settings)
    crawler = runner.create_crawler(MailSpider)
    state: dict[str, Any] = {"scraped": [], "errors": [], "closes": [], "calls": []}
    startup_ready = asyncio.Event()
    startup_errors: list[BaseException] = []
    accepted, drained = asyncio.Event(), asyncio.Event()
    release = threading.Event()
    loop = asyncio.get_running_loop()
    error = RuntimeError(f"native actual {failure} failure")
    snapshots, statements = [], []

    async def opened(spider):
        """
        Gate the real worker before SQL after native pipeline construction.
        """
        try:
            engine = crawler.engine
            pipeline = next(
                component
                for component in engine.scraper.itemproc.middlewares
                if isinstance(component, OutlookMailPipeline)
            )
            state["pipeline"] = pipeline
            state["item"] = await _saved_item(crawler)
            state["baseline"] = _rows(pipeline.catalog)
            state["aliases"] = dict(pipeline.service.evidence_aliases)
            state["hooks"] = _faults(pipeline.catalog, failure, error, statements)
            original = pipeline._process_item_sync
            close = pipeline.service.close

            def guarded(item):
                state["calls"].append(item)
                loop.call_soon_threadsafe(accepted.set)
                try:
                    if not release.wait(5):
                        raise RuntimeError("Native external worker gate expired")
                    return original(item)
                finally:
                    loop.call_soon_threadsafe(drained.set)

            def observed_close():
                state["closes"].append(drained.is_set())
                if drained.is_set() and "terminal_rows" not in state:
                    state["terminal_rows"] = _counts(pipeline.catalog)
                    state["terminal_evidence"] = _rows(pipeline.catalog)
                return close()

            pipeline._process_item_sync = guarded
            pipeline.service.close = observed_close
        except BaseException as exc:
            startup_errors.append(exc)
            raise
        finally:
            startup_ready.set()

    def scraped(item, **kwargs):
        state["scraped"].append(item)

    def failed(failure, **kwargs):
        state["errors"].append(failure.value)

    crawler.signals.connect(opened, signal=signals.spider_opened)
    crawler.signals.connect(scraped, signal=signals.item_scraped)
    crawler.signals.connect(failed, signal=signals.item_error)
    crawl = runner.crawl(crawler, state=state)
    try:
        await _wait_for_fixture_startup(startup_ready, startup_errors, crawl)
        # This deadline belongs only to worker acceptance. Startup readiness
        # above completes its asynchronous fixture prerequisite first.
        await asyncio.wait_for(accepted.wait(), 5)
        pipeline = state["pipeline"]
        public = state["item_task"]
        close = asyncio.create_task(
            crawler.engine.close_spider_async(reason="mail-fault-fixture")
        )
        await _checkpoint()
        slot = crawler.engine._slot
        scraper_slot = crawler.engine.scraper.slot
        if slot is None or scraper_slot is None:
            pytest.fail("Native crawl closed before its accepted worker")
        if slot.closing is None:
            pytest.fail("Native graceful shutdown was not actually requested")
        for number in range(cancels):
            delivered = public.cancel(f"native-accepted-{number}")
            await _checkpoint()
            await _checkpoint()
            snapshots.append(
                {
                    "delivered": delivered,
                    "public_done": public.done(),
                    "lock": pipeline.service.write_lock.locked(),
                    "closed": pipeline.service._closed,
                    "worker_done": drained.is_set(),
                    "native_close_done": close.done(),
                    "item_count": scraper_slot.itemproc_size,
                    "close_calls": list(state["closes"]),
                }
            )
        release.set()
        await asyncio.wait_for(drained.wait(), 5)
        await asyncio.wait_for(close, 5)
        await asyncio.wait_for(crawl, 5)
        for name, hook in state["hooks"]:
            event.remove(pipeline.catalog.engine, name, hook)
        if any(
            row
            != {
                "delivered": True,
                "public_done": False,
                "lock": True,
                "closed": False,
                "worker_done": False,
                "native_close_done": False,
                "item_count": 1,
                "close_calls": [],
            }
            for row in snapshots
        ):
            pytest.fail(f"Native shutdown escaped accepted drain: {snapshots}")
        if len(state["calls"]) != 1 or statements.count("BEGIN IMMEDIATE") != 1:
            pytest.fail("Native cancellation lost or resubmitted persistence")
        if not state["closes"] or not all(state["closes"]):
            pytest.fail("Native close reached the service before actual drain")
        if not pipeline.service._closed or pipeline.service.write_lock.locked():
            pytest.fail("Native terminal shutdown did not release resources")
        if state["scraped"] or _stats(crawler):
            pytest.fail("Native cancelled/error item published success")
        if failure == "none":
            if state["errors"]:
                pytest.fail("Successful cancelled writer fabricated item_error")
        elif state["errors"] != [error] or not isinstance(
            error.__cause__ or error.__context__, asyncio.CancelledError
        ):
            pytest.fail("Native item_error lost worker identity or cancellation")
        # Observe committed state before disposal by wrapping close below.
        if state.get("terminal_rows") != ((1, 2) if failure == "none" else (0, 0)):
            pytest.fail("Native close did not observe actual transaction outcome")
        if state.get("terminal_evidence") != state["baseline"]:
            pytest.fail("Native failure changed prior raw evidence")
        if pipeline.service.evidence_aliases != state["aliases"]:
            pytest.fail("Native semantic failure changed evidence aliases")
    finally:
        release.set()
        if accepted.is_set():
            await asyncio.wait_for(drained.wait(), 5)
        await _cleanup_native_crawl(crawler, crawl)
        (directory / "native-observations.json").write_text(
            json.dumps(
                {
                    "snapshots": snapshots,
                    "statements": statements,
                    "close_after_drain": state["closes"],
                    "error_identity": [value is error for value in state["errors"]],
                    "scraped_count": len(state["scraped"]),
                    "terminal_rows": state.get("terminal_rows"),
                },
                indent=2,
            )
        )


def _run(directory, mode, failure, cancels):
    """Run native reactorless lifecycle in its own bounded Python process."""
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(Path.cwd()), str(Path(__file__).parent)]
    )
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            str(directory),
            mode,
            failure,
            str(cancels),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        env=environment,
        check=False,
    )
    (directory / "native-process.log").write_text(completed.stdout + completed.stderr)
    if completed.returncode:
        pytest.fail(completed.stdout + completed.stderr)


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("cancels", [1, 2])
def test_native_mail_shutdown_waits_for_cancelled_accepted_write(
    tmp_path, mode, cancels
):
    """
    Require native graceful close to wait for cancelled successful writes.
    """
    _run(tmp_path, mode, "none", cancels)


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("failure", ["insert", "commit"])
@pytest.mark.parametrize("cancels", [1, 2])
def test_native_mail_shutdown_reports_worker_error_after_cancel(
    tmp_path, mode, failure, cancels
):
    """
    Deliver exact SQL errors through native item_error before service close.
    """
    _run(tmp_path, mode, failure, cancels)


if __name__ == "__main__":
    asyncio.run(_crawl(Path(sys.argv[1]), sys.argv[2], sys.argv[3], int(sys.argv[4])))
