"""Retain real Calendar writes through native pipeline cancellation."""

from __future__ import annotations

import asyncio
import threading

import pytest
from _full_completion_fixtures import NOW, save
from scrapy.pipelines import ItemPipelineManager
from scrapy.utils.test import get_crawler
from sqlalchemy import event, text
from test_raw_evidence_cancellation import _checkpoint

from message_ingest.items.microsoft.outlook.calendar import (
    OutlookCalendarDeltaCheckpointCandidateItem,
    OutlookCalendarEventItem,
    OutlookCalendarEventSurfaceItem,
)
from message_ingest.pipelines.microsoft.outlook.calendar import OutlookCalendarPipeline


class Observer:
    """Record public downstream admission through the native manager."""

    def __init__(self):
        self.items = []

    def process_item(self, item):
        self.items.append(item)
        return item


def _setup(directory, kind):
    """Build a real shared service and evidence before semantic writes."""
    crawler = get_crawler(
        settings_dict={
            "ITEM_PIPELINES": {OutlookCalendarPipeline: 100, Observer: 200},
            "MSGLOOM_CATALOG_ENABLED": True,
            "MSGLOOM_DATABASE_URL": f"sqlite:///{directory / 'catalog.db'}",
            "MSGLOOM_SOURCE_ID": "source",
        }
    )
    manager = ItemPipelineManager.from_crawler(crawler)
    pipeline, observer = manager.middlewares
    raw = {"id": "one", "changeKey": "v1"}
    evidence = save(pipeline.catalog, "capture", raw)
    common = {"run_id": "run", "evidence_id": evidence, "observed_at": NOW}
    if kind == "event":
        return (
            crawler,
            manager,
            pipeline,
            observer,
            OutlookCalendarEventItem(event_id="one", raw=raw, **common),
            pipeline.store,
            "persist_event",
            "calendar_events",
        )
    if kind == "surface":
        return (
            crawler,
            manager,
            pipeline,
            observer,
            OutlookCalendarEventSurfaceItem(
                event_id="one",
                surface="detail",
                status="acquired",
                resource_version="v1",
                profile_version="outlook-calendar-full-v1",
                **common,
            ),
            pipeline.store,
            "set_event_surface",
            "calendar_event_surfaces",
        )
    return (
        crawler,
        manager,
        pipeline,
        observer,
        OutlookCalendarDeltaCheckpointCandidateItem(
            attempt=1,
            base_revision=None,
            delta_link="https://example.test/delta",
            start_datetime="2026-10-01T00:00:00Z",
            end_datetime="2026-11-01T00:00:00Z",
            **common,
        ),
        pipeline,
        "_persist_delta_candidate",
        "calendar_delta_checkpoint_candidates",
    )


async def _accepted(directory, kind, cancels, failure, monkeypatch, race=False):
    """Gate an accepted real store write, then drain before native close."""
    crawler, manager, pipeline, observer, item, owner, name, table = _setup(
        directory, kind
    )
    accepted, finished = asyncio.Event(), asyncio.Event()
    release = threading.Event()
    loop = asyncio.get_running_loop()
    error = RuntimeError("Calendar SQL INSERT failure")
    original = getattr(owner, name)
    starts = []
    unobserved = []
    loop.set_exception_handler(lambda _loop, context: unobserved.append(context))

    def before(_connection, _cursor, statement, _parameters, _context, _many):
        if failure and statement.startswith(f"INSERT INTO {table} "):
            raise error

    def gated(*args, **kwargs):
        starts.append(name)
        loop.call_soon_threadsafe(accepted.set)
        try:
            if not release.wait(5):
                raise RuntimeError("Calendar test worker deadline")
            return original(*args, **kwargs)
        finally:
            if race:
                loop.call_soon_threadsafe(task.cancel, "completion race")
            loop.call_soon_threadsafe(finished.set)

    event.listen(pipeline.catalog.engine, "before_cursor_execute", before)
    monkeypatch.setattr(owner, name, gated)
    task = asyncio.create_task(manager.process_item_async(item))
    snapshots = []
    try:
        await asyncio.wait_for(accepted.wait(), 5)
        for number in range(cancels):
            task.cancel(f"accepted-{number}")
            await _checkpoint()
            snapshots.append((task.done(), pipeline.service.write_lock.locked()))
        release.set()
        outcome = (await asyncio.gather(task, return_exceptions=True))[0]
        await asyncio.wait_for(finished.wait(), 5)
        if any(done or not locked for done, locked in snapshots):
            pytest.fail(f"Accepted worker lost public ownership: {snapshots}")
        if starts != [name] or pipeline.service.write_lock.locked():
            pytest.fail("Worker was resubmitted or lock was not released")
        if failure:
            if outcome is not error:
                pytest.fail("Original worker error identity was lost")
            if (cancels or race) and not isinstance(
                error.__cause__, asyncio.CancelledError
            ):
                pytest.fail("Worker error lost caller cancellation cause")
        elif cancels or race:
            if not isinstance(outcome, asyncio.CancelledError):
                pytest.fail("Successful cancelled write published an item")
        elif outcome is not item:
            pytest.fail("Successful write lost public item")
        stats = {
            key: value
            for key, value in crawler.stats.get_stats().items()
            if key.startswith("msgloom/calendar/")
        }
        if failure or cancels or race:
            if stats or observer.items:
                pytest.fail("Cancelled or failed write published success")
        elif observer.items != [item] or not stats:
            pytest.fail("Successful write did not publish exactly once")
        with pipeline.catalog.Session() as session:
            count = session.scalar(text(f"SELECT count(*) FROM {table}"))
        if count != (0 if failure else 1):
            pytest.fail("Real store transaction did not commit or roll back")
        await manager.close_spider_async()
        if not pipeline.service._closed or not finished.is_set():
            pytest.fail("Native close did not follow actual worker completion")
        await _checkpoint()
        if unobserved:
            pytest.fail(f"Unobserved worker outcome: {unobserved}")
    finally:
        release.set()
        await asyncio.gather(task, return_exceptions=True)
        if accepted.is_set():
            await asyncio.wait_for(finished.wait(), 5)
        event.remove(pipeline.catalog.engine, "before_cursor_execute", before)
        pipeline.close_spider()
        loop.set_exception_handler(None)


@pytest.mark.parametrize("kind", ["event", "surface", "checkpoint"])
@pytest.mark.parametrize("cancels", [0, 1, 2])
@pytest.mark.parametrize("failure", [False, True])
def test_calendar_accepted_write_drains_before_close(
    tmp_path, kind, cancels, failure, monkeypatch
):
    """Preserve lock, real SQL, errors and canceled publication semantics."""
    asyncio.run(_accepted(tmp_path, kind, cancels, failure, monkeypatch))


@pytest.mark.parametrize("kind", ["event", "surface", "checkpoint"])
@pytest.mark.parametrize("failure", [False, True])
def test_calendar_completion_cancel_race(tmp_path, kind, failure, monkeypatch):
    """Do not lose a cancellation queued at worker completion."""
    asyncio.run(_accepted(tmp_path, kind, 0, failure, monkeypatch, race=True))


@pytest.mark.parametrize("kind", ["event", "surface", "checkpoint"])
def test_calendar_cancel_before_worker_acceptance(tmp_path, kind, monkeypatch):
    """A caller waiting for the shared lock must not dispatch a worker."""

    async def run():
        _, manager, pipeline, observer, item, owner, name, _ = _setup(tmp_path, kind)
        starts = []
        monkeypatch.setattr(owner, name, lambda *args, **kwargs: starts.append(name))
        await pipeline.service.write_lock.acquire()
        task = asyncio.create_task(manager.process_item_async(item))
        try:
            await _checkpoint()
            task.cancel("before acceptance")
            outcome = (await asyncio.gather(task, return_exceptions=True))[0]
            if not isinstance(outcome, asyncio.CancelledError):
                pytest.fail("Unaccepted caller lost cancellation")
            if starts or observer.items:
                pytest.fail("Unaccepted caller persisted or published an item")
        finally:
            pipeline.service.write_lock.release()
            await asyncio.gather(task, return_exceptions=True)
            await manager.close_spider_async()

    asyncio.run(run())
