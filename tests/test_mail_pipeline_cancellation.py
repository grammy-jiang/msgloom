"""Qualify Mail semantic worker ownership through the native manager."""

from __future__ import annotations

import asyncio
import json
import threading

import pytest
from scrapy.pipelines import ItemPipelineManager
from scrapy.utils.test import get_crawler
from sqlalchemy import event, text
from test_raw_evidence_cancellation import _checkpoint, _item
from test_raw_evidence_transactions import _rows

from message_ingest.catalog import Catalog
from message_ingest.extensions.catalog import CatalogService
from message_ingest.items.microsoft.outlook.email import OutlookMailDetailItem
from message_ingest.pipelines.evidence import RawEvidencePipeline
from message_ingest.pipelines.microsoft.outlook.email import OutlookMailPipeline

MODES = ("file", "memory", "memory-colon")


def _settings(directory, mode):
    """Isolate every storage path and retain the existing database modes."""
    return {
        "ITEM_PIPELINES": {OutlookMailPipeline: 100, Observer: 200},
        "MSGLOOM_CATALOG_ENABLED": True,
        "MSGLOOM_RAW_EVIDENCE_ENABLED": True,
        "MSGLOOM_DATABASE_URL": {
            "file": f"sqlite:///{directory / 'catalog.db'}",
            "memory": "sqlite://",
            "memory-colon": "sqlite:///:memory:",
        }[mode],
        "MSGLOOM_RAW_EVIDENCE_DIR": str(directory / "raw"),
        "MSGLOOM_DATA_DIR": str(directory / "data"),
        "MSGLOOM_SOURCE_ID": "mail-cancellation-source",
        "MS_GRAPH_AUTH_ENABLED": False,
        "MS_GRAPH_AUTH_METHOD": "none",
        "MS_GRAPH_TOKEN_CACHE": str(directory / "auth.json"),
        "HTTPCACHE_DIR": str(directory / "cache"),
        "HTTPCACHE_ENABLED": False,
        "JOBDIR": "",
        "FEEDS": {},
        "LOG_FILE": str(directory / "crawl.log"),
    }


class Observer:
    """Observe native downstream admission after real semantic persistence."""

    def __init__(self, crawler):
        """Borrow the crawler's service without another catalog."""
        self.service = CatalogService.from_crawler(crawler)
        self.items = []

    @classmethod
    def from_crawler(cls, crawler):
        """Construct through the native manager."""
        return cls(crawler)

    def process_item(self, item):
        """Reject semantic admission before durable evidence and facts."""
        if isinstance(item, OutlookMailDetailItem):
            if item.evidence_id is None:
                pytest.fail("Semantic item has no durable evidence identity")
            if not self.service.catalog.evidence.contains(item.evidence_id):
                pytest.fail("Semantic admission overtook raw evidence")
            if _counts(self.service.catalog) != (1, 2):
                pytest.fail("Downstream admission overtook semantic commit")
        self.items.append(item)
        return item


async def _saved_item(crawler, identity="detail"):
    """
    Persist actual raw blobs and SQL before constructing the semantic item.
    """
    raw = RawEvidencePipeline.from_crawler(crawler)
    body = {"id": "m", "changeKey": "v1"}
    evidence = _item(identity)
    evidence.response_body = json.dumps(body).encode()
    await raw.process_item(evidence)
    return OutlookMailDetailItem(
        message_id="m",
        raw=body,
        source_response_url="https://example.test/m",
        observed_at=evidence.observed_at,
        evidence_id=evidence.evidence_id,
        run_id="mail-cancellation-run",
        selection_id="mail-cancellation-selection",
    )


def _counts(catalog):
    """Count actual rows only outside the gated writer transaction."""
    with catalog.Session() as session:
        return tuple(
            session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
            for table in ("messages", "acquisition_facts")
        )


def _stats(crawler):
    """Select semantic success statistics without mixing prior raw success."""
    return {
        key: value
        for key, value in crawler.stats.get_stats().items()
        if key.startswith("msgloom/catalog/")
    }


def _faults(catalog, failure, error, statements):
    """Install real INSERT and pre-COMMIT faults without replacing writes."""

    def after(connection, cursor, statement, parameters, context, many):
        statements.append(statement)
        if failure == "insert" and statement.startswith("INSERT INTO messages "):
            raise error

    def before(connection, cursor, statement, parameters, context, many):
        if failure == "commit" and statement == "COMMIT":
            raise error

    hooks = [("after_cursor_execute", after), ("before_cursor_execute", before)]
    for name, hook in hooks:
        event.listen(catalog.engine, name, hook)
    return hooks


async def _unaccepted(directory, mode, lock_wait, monkeypatch):
    """Cancel the public manager before accepting any semantic worker."""
    crawler = get_crawler(settings_dict=_settings(directory, mode))
    manager = ItemPipelineManager.from_crawler(crawler)
    pipeline, observer = manager.middlewares
    item = await _saved_item(crawler)
    rows, aliases = _rows(pipeline.catalog), dict(pipeline.service.evidence_aliases)
    starts = []
    original = pipeline._process_item_sync

    def track(value):
        starts.append(value)
        return original(value)

    monkeypatch.setattr(pipeline, "_process_item_sync", track)
    if lock_wait:
        await pipeline.service.write_lock.acquire()
    task = asyncio.create_task(manager.process_item_async(item))
    try:
        if lock_wait:
            await _checkpoint()
        if not task.cancel("before acceptance"):
            pytest.fail("Preacceptance cancellation was not delivered")
        with pytest.raises(asyncio.CancelledError):
            await task
    finally:
        if lock_wait:
            pipeline.service.write_lock.release()
    try:
        if starts or _counts(pipeline.catalog) != (0, 0):
            pytest.fail("Unaccepted item started semantic persistence")
        if _stats(crawler) or observer.items:
            pytest.fail("Unaccepted item published semantic success")
        if (
            _rows(pipeline.catalog) != rows
            or pipeline.service.evidence_aliases != aliases
        ):
            pytest.fail("Unaccepted semantic item changed prior raw evidence")
    finally:
        await manager.close_spider_async()


@pytest.mark.parametrize("mode", MODES)
def test_mail_cancel_before_acceptance_starts_no_write(tmp_path, mode, monkeypatch):
    """Cancel before the actual manager coroutine executes."""
    asyncio.run(_unaccepted(tmp_path, mode, False, monkeypatch))


@pytest.mark.parametrize("mode", MODES)
def test_mail_cancel_waiting_for_existing_lock_starts_no_write(
    tmp_path, mode, monkeypatch
):
    """Cancel a manager blocked on the fixture-owned existing write lock."""
    asyncio.run(_unaccepted(tmp_path, mode, True, monkeypatch))


async def _accepted(directory, mode, monkeypatch, cancels, failure, race=False):
    """Drain one real worker with finite external gates before SQL."""
    crawler = get_crawler(settings_dict=_settings(directory, mode))
    manager = ItemPipelineManager.from_crawler(crawler)
    pipeline, observer = manager.middlewares
    item = await _saved_item(crawler)
    baseline, aliases = _rows(pipeline.catalog), dict(pipeline.service.evidence_aliases)
    accepted, drained = asyncio.Event(), asyncio.Event()
    release = threading.Event()
    loop = asyncio.get_running_loop()
    calls, statements, snapshots, deliveries, unobserved = [], [], [], [], []
    error = RuntimeError(f"actual Mail {failure} failure")
    hooks = _faults(pipeline.catalog, failure, error, statements)
    original = pipeline._process_item_sync
    previous_handler = loop.get_exception_handler()
    loop.set_exception_handler(lambda loop, context: unobserved.append(context))
    task: asyncio.Task

    def gated(value):
        calls.append(value)
        loop.call_soon_threadsafe(accepted.set)
        try:
            if not release.wait(5):
                raise RuntimeError("External Mail worker gate expired")
            return original(value)
        finally:
            if race:
                loop.call_soon_threadsafe(
                    lambda: deliveries.append(task.cancel("terminal race"))
                )
            loop.call_soon_threadsafe(drained.set)

    monkeypatch.setattr(pipeline, "_process_item_sync", gated)
    task = asyncio.create_task(manager.process_item_async(item))
    outcome = None
    try:
        await asyncio.wait_for(accepted.wait(), 5)
        for number in range(cancels):
            delivered = task.cancel(f"accepted-{number}")
            await _checkpoint()
            await _checkpoint()
            snapshots.append(
                (
                    delivered,
                    task.done(),
                    pipeline.service.write_lock.locked(),
                    pipeline.service._closed,
                    drained.is_set(),
                )
            )
        release.set()
        try:
            await asyncio.wait_for(task, 5)
        except (RuntimeError, asyncio.CancelledError) as caught:
            outcome = caught
        await asyncio.wait_for(drained.wait(), 5)
    finally:
        release.set()
        await asyncio.wait_for(drained.wait(), 5)
        for name, hook in hooks:
            event.remove(pipeline.catalog.engine, name, hook)
        loop.set_exception_handler(previous_handler)
        (directory / "observations.json").write_text(
            json.dumps(
                {
                    "snapshots": snapshots,
                    "deliveries": deliveries,
                    "statements": statements,
                    "calls": len(calls),
                    "outcome": type(outcome).__name__,
                },
                indent=2,
            )
        )
    try:
        if any(row != (True, False, True, False, False) for row in snapshots):
            pytest.fail(f"Accepted worker escaped its lifetime guard: {snapshots}")
        if calls != [item] or statements.count("BEGIN IMMEDIATE") != 1:
            pytest.fail("Accepted semantic work was lost or resubmitted")
        if pipeline.service.write_lock.locked() or pipeline.service._closed:
            pytest.fail("Public terminal completion violated normal lifetime")
        if pipeline.catalog.engine.pool.checkedout() != 0:
            pytest.fail("Worker leaked a catalog checkout")
        if failure != "none":
            if outcome is not error or _counts(pipeline.catalog) != (0, 0):
                pytest.fail(f"Original SQL failure or atomic rollback lost: {outcome}")
            if (cancels or race) and not isinstance(
                error.__cause__ or error.__context__, asyncio.CancelledError
            ):
                pytest.fail("Worker failure lost caller cancellation context")
        elif cancels or race:
            if not isinstance(outcome, asyncio.CancelledError):
                pytest.fail("Cancelled successful worker fabricated success")
            if _counts(pipeline.catalog) != (1, 2):
                pytest.fail("Accepted successful worker did not actually commit")
        elif outcome is not None or observer.items != [item]:
            pytest.fail("Ordinary semantic success did not complete exactly once")
        if failure != "none" or cancels or race:
            if observer.items or _stats(crawler):
                pytest.fail("Error or cancellation published semantic success")
        elif _stats(crawler) != {
            "msgloom/catalog/message_detail_item_processed_count": 1,
            "msgloom/catalog/message_detail_observation_created_count": 1,
        }:
            pytest.fail("Normal success statistics changed")
        if (
            _rows(pipeline.catalog) != baseline
            or pipeline.service.evidence_aliases != aliases
        ):
            pytest.fail("Semantic completion altered prior evidence or aliases")
        if race and deliveries != [True]:
            pytest.fail("Completion race did not accept caller cancellation")
        if task.cancel("after public terminal") or unobserved:
            pytest.fail("Terminal control or worker exception observation failed")
        monkeypatch.setattr(pipeline, "_process_item_sync", original)
        await manager.process_item_async(item)
        if _counts(pipeline.catalog) != (1, 2):
            pytest.fail("Subsequent valid semantic write failed after cleanup")
    finally:
        await manager.close_spider_async()
    if not pipeline.service._closed:
        pytest.fail("Normal await-then-close did not release the service")
    if mode == "file":
        reopened = Catalog(pipeline.catalog.database_url)
        try:
            if _counts(reopened) != (1, 2) or _rows(reopened) != baseline:
                pytest.fail("File reopen lost exact semantic or evidence rows")
        finally:
            reopened.close()


@pytest.mark.parametrize("mode", MODES)
def test_mail_accepted_single_cancel_drains_real_write(tmp_path, mode, monkeypatch):
    """Retain the worker and service through one accepted cancellation."""
    asyncio.run(_accepted(tmp_path, mode, monkeypatch, 1, "none"))


@pytest.mark.parametrize("mode", MODES)
def test_mail_repeated_cancel_retains_worker_and_lock(tmp_path, mode, monkeypatch):
    """Deliver two accepted cancellations at distinct drain checkpoints."""
    asyncio.run(_accepted(tmp_path, mode, monkeypatch, 2, "none"))


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("cancels", [0, 1, 2])
def test_mail_insert_failure_identity_and_cancel_precedence(
    tmp_path, mode, cancels, monkeypatch
):
    """
    Preserve the exact real INSERT error and atomic message/fact rollback.
    """
    asyncio.run(_accepted(tmp_path, mode, monkeypatch, cancels, "insert"))


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("cancels", [0, 1, 2])
def test_mail_commit_failure_identity_and_cancel_precedence(
    tmp_path, mode, cancels, monkeypatch
):
    """Preserve the exact pre-COMMIT failure across caller cancellations."""
    asyncio.run(_accepted(tmp_path, mode, monkeypatch, cancels, "commit"))


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("failure", ["none", "insert", "commit"])
def test_mail_completion_cancel_race_preserves_terminal_outcome(
    tmp_path, mode, failure, monkeypatch
):
    """Queue cancellation from real terminal success or SQL failure."""
    asyncio.run(_accepted(tmp_path, mode, monkeypatch, 0, failure, race=True))


@pytest.mark.parametrize("mode", MODES)
def test_mail_normal_success_and_passthrough_preserve_behavior(
    tmp_path, mode, monkeypatch
):
    """Keep ordinary durable success and unrelated pass-through unchanged."""
    asyncio.run(_accepted(tmp_path, mode, monkeypatch, 0, "none"))

    async def passthrough():
        crawler = get_crawler(settings_dict=_settings(tmp_path / "other", mode))
        manager = ItemPipelineManager.from_crawler(crawler)
        pipeline, observer = manager.middlewares
        unknown = object()
        try:
            if await manager.process_item_async(unknown) is not unknown:
                pytest.fail("Mail pass-through changed the unrelated item")
            if observer.items != [unknown] or _counts(pipeline.catalog) != (0, 0):
                pytest.fail("Pass-through performed a semantic write")
            if _stats(crawler) or pipeline.service.evidence_aliases:
                pytest.fail("Pass-through fabricated persistence publication")
        finally:
            await manager.close_spider_async()

    asyncio.run(passthrough())
