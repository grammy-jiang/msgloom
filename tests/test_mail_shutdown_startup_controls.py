"""Control Mail shutdown fixture startup and cleanup boundaries."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
import test_mail_pipeline_shutdown as shutdown


def _observe_runner(monkeypatch, captured: dict[str, Any]) -> None:
    """Capture the native crawl task, crawler, and fixture state."""
    original_runner = shutdown.AsyncCrawlerRunner

    class ObservedRunner(original_runner):
        def crawl(self, *args, **kwargs):
            task = super().crawl(*args, **kwargs)
            captured["crawl"] = task
            captured["crawler"] = args[0]
            captured["state"] = kwargs["state"]
            return task

    monkeypatch.setattr(shutdown, "AsyncCrawlerRunner", ObservedRunner)


def _require_native_cleanup(
    captured: dict[str, Any],
    *,
    worker_calls: int,
) -> None:
    """Require pipeline and downloader ownership to be fully released."""
    crawler = captured["crawler"]
    if crawler.engine.spider is not None:
        pytest.fail("Native spider remained open after fixture completion")
    pipeline = next(
        (
            component
            for component in crawler.engine.scraper.itemproc.middlewares
            if isinstance(component, shutdown.OutlookMailPipeline)
        ),
        None,
    )
    if pipeline is None:
        pytest.fail("Native Mail pipeline was not constructed")
    if not pipeline.service._closed:
        pytest.fail("Catalog service remained open after fixture completion")
    if len(captured["state"]["calls"]) != worker_calls:
        pytest.fail("Mail worker call count changed across fixture cleanup")
    for handler in crawler.engine.downloader.handlers._handlers.values():
        session = getattr(handler, "_session", None)
        if session is not None and not session.closed:
            pytest.fail("Native downloader session remained open")


def test_delayed_prerequisite_does_not_consume_worker_deadline(tmp_path, monkeypatch):
    """Start the worker deadline after the async prerequisite completes."""
    original_saved_item = shutdown._saved_item

    async def delayed(crawler):
        await asyncio.sleep(5.1)
        return await original_saved_item(crawler)

    monkeypatch.setattr(shutdown, "_saved_item", delayed)
    asyncio.run(shutdown._crawl(tmp_path, "file", "none", 1))


def test_startup_error_preserves_identity_and_closes_native_resources(
    tmp_path, monkeypatch
):
    """Surface the original startup failure promptly and close native state."""
    captured: dict[str, Any] = {}
    _observe_runner(monkeypatch, captured)
    sentinel = OSError("mail shutdown startup prerequisite failed")

    async def failed(crawler):
        raise sentinel

    monkeypatch.setattr(shutdown, "_saved_item", failed)

    async def scenario():
        try:
            await asyncio.wait_for(
                shutdown._crawl(tmp_path, "file", "none", 1),
                2,
            )
        except OSError as exc:
            if exc is not sentinel:
                pytest.fail("Startup failure identity changed")
        else:
            pytest.fail("Injected startup failure was not propagated")
        if not captured["crawl"].done():
            pytest.fail("Native crawl remained pending after startup failure")
        _require_native_cleanup(captured, worker_calls=0)

    asyncio.run(scenario())


def test_cancellation_during_prerequisite_preserves_cancel_and_cleans(
    tmp_path, monkeypatch
):
    """Preserve fixture cancellation while closing the pending native crawl."""
    captured: dict[str, Any] = {}
    _observe_runner(monkeypatch, captured)
    entered = asyncio.Event()
    blocker = asyncio.Event()

    async def blocked(crawler):
        entered.set()
        await blocker.wait()
        raise RuntimeError("Cancelled prerequisite resumed unexpectedly")

    monkeypatch.setattr(shutdown, "_saved_item", blocked)

    async def scenario():
        fixture = asyncio.create_task(shutdown._crawl(tmp_path, "file", "none", 1))
        await asyncio.wait_for(entered.wait(), 2)
        fixture.cancel("mail shutdown startup control cancellation")
        try:
            await fixture
        except asyncio.CancelledError as exc:
            if str(exc) != "mail shutdown startup control cancellation":
                pytest.fail("Fixture cancellation identity changed")
        else:
            pytest.fail("Fixture cancellation was swallowed")
        if not captured["crawl"].done():
            pytest.fail("Native crawl remained pending after fixture cancellation")
        _require_native_cleanup(captured, worker_calls=0)

    asyncio.run(scenario())


def test_early_native_crawl_failure_before_readiness_is_actionable(
    tmp_path,
    monkeypatch,
):
    """Surface a real native startup failure before spider_opened."""
    captured: dict[str, Any] = {}
    _observe_runner(monkeypatch, captured)
    sentinel = RuntimeError("native pipeline startup failed before readiness")

    class FailingEntry(shutdown.Entry):
        async def open_spider(self):
            raise sentinel

    monkeypatch.setattr(shutdown, "Entry", FailingEntry)

    async def scenario():
        try:
            await asyncio.wait_for(
                shutdown._crawl(tmp_path, "file", "none", 1),
                2,
            )
        except RuntimeError as exc:
            if exc is not sentinel:
                pytest.fail("Early native startup failure identity changed")
        else:
            pytest.fail("Early native crawl failure was not propagated")
        if not captured["crawl"].done():
            pytest.fail("Early native crawl remained pending")
        _require_native_cleanup(captured, worker_calls=0)

    asyncio.run(scenario())


def test_normal_startup_reaches_worker_acceptance(tmp_path, monkeypatch):
    """Keep the unchanged native success and cancellation oracle reachable."""
    captured: dict[str, Any] = {}
    _observe_runner(monkeypatch, captured)
    asyncio.run(shutdown._crawl(tmp_path, "file", "none", 1))
    _require_native_cleanup(captured, worker_calls=1)
