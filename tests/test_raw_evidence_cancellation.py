"""Exercise native raw pipeline ownership under public task cancellation."""

from __future__ import annotations

import asyncio
import json
import threading
from pathlib import Path

import pytest
from scrapy.pipelines import ItemPipelineManager
from scrapy.utils.test import get_crawler
from sqlalchemy import event, select

from message_ingest.catalog import Catalog, RawHttpEvidence
from message_ingest.extensions.catalog import CatalogService
from message_ingest.items.acquisition import RawHttpEvidenceItem
from message_ingest.pipelines.evidence import RawEvidencePipeline


def _item(identity="capture", origin="network"):
    """Build a real raw exchange with distinct request and response blobs."""
    return RawHttpEvidenceItem(
        evidence_id=identity,
        run_id="logical-run",
        purpose="message-list",
        observed_at="2026-10-04T00:00:00Z",
        origin=origin,
        request_fingerprint="same-request",
        request_url="https://example.test",
        request_method="GET",
        request_headers={},
        request_body=b"request",
        response_url="https://example.test",
        response_status=200,
        response_headers={},
        response_body=b"response",
        response_flags=[],
    )


class DurableObserver:
    """Reject any next-stage admission before durable evidence publication."""

    def __init__(self, crawler):
        """Borrow the native crawler service and record completed items."""
        self.service = CatalogService.from_crawler(crawler)
        self.stats = crawler.stats
        self.items = []

    @classmethod
    def from_crawler(cls, crawler):
        """Construct through the native pipeline manager."""
        return cls(crawler)

    def process_item(self, item):
        if isinstance(item, RawHttpEvidenceItem):
            if not self.service.catalog.evidence.contains(item.evidence_id):
                pytest.fail("Semantic stage overtook durable evidence")
            if (item.evidence_id, item.observed_at) not in (
                self.service.evidence_aliases.values()
            ):
                pytest.fail("Semantic stage overtook canonical alias")
            if not self.stats.get_value("msgloom/evidence/response_persisted_count", 0):
                pytest.fail("Semantic stage overtook durable success statistic")
        self.items.append(item)
        return item


def _setup(tmp_path, memory=False):
    """Use Scrapy's native builder, manager and shared catalog service."""
    crawler = get_crawler(
        settings_dict={
            "ITEM_PIPELINES": {RawEvidencePipeline: 200, DurableObserver: 300},
            "MSGLOOM_CATALOG_ENABLED": True,
            "MSGLOOM_RAW_EVIDENCE_ENABLED": True,
            "MSGLOOM_DATABASE_URL": (
                "sqlite://" if memory else f"sqlite:///{tmp_path / 'catalog.db'}"
            ),
            "MSGLOOM_RAW_EVIDENCE_DIR": str(tmp_path / "raw"),
            "MSGLOOM_SOURCE_ID": "source-a",
        }
    )
    manager = ItemPipelineManager.from_crawler(crawler)
    raw, observer = manager.middlewares
    return manager, raw, observer, crawler.stats


async def _checkpoint():
    """Yield to already queued callbacks without a timing-based sleep."""
    reached = asyncio.Event()
    asyncio.get_running_loop().call_soon(reached.set)
    await reached.wait()


def _count(catalog):
    """Read after worker completion, never while coordinating a writer."""
    with catalog.Session() as session:
        return len(session.scalars(select(RawHttpEvidence)).all())


@pytest.mark.parametrize("phase", ["before_execution", "lock_wait"])
def test_public_cancellation_before_acceptance(tmp_path, monkeypatch, phase):
    """Reject unaccepted work without any persistence or publication."""
    manager, raw, observer, stats = _setup(tmp_path)
    starts = []
    original = raw._persist_sync

    def track(item):
        starts.append(item.evidence_id)
        return original(item)

    monkeypatch.setattr(raw, "_persist_sync", track)

    async def exercise():
        if phase == "lock_wait":
            await raw.service.write_lock.acquire()
        task = asyncio.create_task(manager.process_item_async(_item()))
        if phase == "lock_wait":
            await _checkpoint()
        accepted = task.cancel("before acceptance")
        try:
            with pytest.raises(asyncio.CancelledError):
                await task
        finally:
            if phase == "lock_wait":
                raw.service.write_lock.release()
        if not accepted or starts or _count(raw.catalog):
            pytest.fail("Unaccepted cancellation started a worker or row")
        if list(raw.raw_dir.iterdir()) or raw.service.evidence_aliases:
            pytest.fail("Unaccepted cancellation created a blob or alias")
        if observer.items or stats.get_value(
            "msgloom/evidence/response_persisted_count", 0
        ):
            pytest.fail("Unaccepted cancellation admitted downstream success")
        await manager.close_spider_async()

    asyncio.run(exercise())


@pytest.mark.parametrize("memory", [False, True])
@pytest.mark.parametrize("failure", ["none", "ordinary", "sql", "commit"])
@pytest.mark.parametrize("cancels", [0, 1, 2])
def test_accepted_worker_drains_and_preserves_failure(
    tmp_path, monkeypatch, memory, failure, cancels
):
    """Drain one real worker across repeated cancellation and rollback."""
    manager, raw, observer, stats = _setup(tmp_path, memory)
    release = threading.Event()
    error = RuntimeError(f"ordinary-{failure}")
    calls, statements, snapshots = [], [], []
    hooks = []
    outcome = None

    def sql_hook(connection, cursor, statement, parameters, context, many):
        statements.append(statement)
        if failure == "sql" and statement.startswith("INSERT INTO raw_http"):
            raise error

    def commit_hook(connection, cursor, statement, parameters, context, many):
        if failure == "commit" and statement == "COMMIT":
            raise error

    def ordinary_commit(connection):
        if failure == "commit":
            raise error

    hooks.extend(
        [
            ("after_cursor_execute", sql_hook),
            ("before_cursor_execute", commit_hook),
            ("commit", ordinary_commit),
        ]
    )
    for name, hook in hooks:
        event.listen(raw.catalog.engine, name, hook)

    async def exercise():
        nonlocal outcome
        loop = asyncio.get_running_loop()
        accepted, drained = asyncio.Event(), asyncio.Event()
        original = raw.catalog.evidence.record

        def gated_record(evidence):
            calls.append(evidence.evidence_id)
            if (
                Path(evidence.request_body_path).read_bytes() != b"request"
                or Path(evidence.response_body_path).read_bytes() != b"response"
            ):
                raise RuntimeError("Fixture did not reach real blob durability")
            loop.call_soon_threadsafe(accepted.set)
            try:
                if not release.wait(5):
                    raise RuntimeError("External pre-SQL gate expired")
                if failure == "ordinary":
                    raise error
                return original(evidence)
            finally:
                loop.call_soon_threadsafe(drained.set)

        monkeypatch.setattr(raw.catalog.evidence, "record", gated_record)
        item = _item()
        task = asyncio.create_task(manager.process_item_async(item))
        try:
            await asyncio.wait_for(accepted.wait(), 5)
            for number in range(cancels):
                delivered = task.cancel(f"outer-{number}")
                await _checkpoint()
                snapshots.append(
                    {
                        "delivered": delivered,
                        "pending": not task.done(),
                        "locked": raw.service.write_lock.locked(),
                        "open": not raw.service._closed,
                        "drained": drained.is_set(),
                    }
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
                event.remove(raw.catalog.engine, name, hook)
        rows = _count(raw.catalog)
        if raw.service.write_lock.locked() or raw.service._closed:
            pytest.fail("Worker exit did not retain normal caller lifetime")
        for snapshot in snapshots:
            if snapshot != {
                "delivered": True,
                "pending": True,
                "locked": True,
                "open": True,
                "drained": False,
            }:
                pytest.fail(f"Cancellation escaped accepted worker: {snapshots}")
        if calls != ["capture"]:
            pytest.fail("Accepted persistence was resubmitted")
        if statements.count("BEGIN IMMEDIATE") != int(failure != "ordinary"):
            pytest.fail("Accepted worker did not own exactly one transaction")
        if failure != "none":
            if outcome is not error or rows:
                pytest.fail(f"Worker error lost identity or rollback: {outcome}")
            if cancels and not isinstance(
                error.__cause__ or error.__context__, asyncio.CancelledError
            ):
                pytest.fail("Worker error lost the pending cancellation context")
        elif cancels:
            if not isinstance(outcome, asyncio.CancelledError) or rows != 1:
                pytest.fail("Cancelled successful worker was not drained once")
        elif outcome is not None or rows != 1 or observer.items != [item]:
            pytest.fail(f"Ordinary success did not complete once: {outcome}")
        if (failure != "none" or cancels) and (
            raw.service.evidence_aliases
            or observer.items
            or stats.get_value("msgloom/evidence/response_persisted_count", 0)
        ):
            pytest.fail("Failed or cancelled stage fabricated publication")
        # Retry a distinct capture after cleanup, without the fixture gate.
        monkeypatch.setattr(raw.catalog.evidence, "record", original)
        await manager.process_item_async(_item("independent"))
        if _count(raw.catalog) != rows + 1:
            pytest.fail("An independent write could not follow worker cleanup")
        await manager.close_spider_async()
        if not raw.service._closed:
            pytest.fail("Normal await-then-close did not close the service")
        return rows + 1

    try:
        expected = asyncio.run(exercise())
    finally:
        release.set()
        raw.catalog.close()
        (tmp_path / "observations.json").write_text(
            json.dumps(
                {
                    "cancels": cancels,
                    "snapshots": snapshots,
                    "calls": calls,
                    "statements": statements,
                },
                indent=2,
            )
        )
    if not memory:
        reopened = Catalog(raw.catalog.database_url)
        try:
            if _count(reopened) != expected:
                pytest.fail("Reopen changed committed worker results")
        finally:
            reopened.close()


def test_blob_failure_preserves_identity(tmp_path, monkeypatch):
    """Fail actual blob replacement before SQL and admit no downstream item."""
    manager, raw, observer, stats = _setup(tmp_path)
    error = OSError("blob replace")
    original = Path.replace

    def fail(path, target):
        if path.parent == raw.raw_dir:
            raise error
        return original(path, target)

    monkeypatch.setattr(Path, "replace", fail)

    async def exercise():
        with pytest.raises(OSError) as caught:
            await manager.process_item_async(_item())
        if caught.value is not error or _count(raw.catalog):
            pytest.fail("Blob failure changed identity or created SQL evidence")
        if (
            observer.items
            or raw.service.evidence_aliases
            or stats.get_value("msgloom/evidence/response_persisted_count", 0)
        ):
            pytest.fail("Blob failure admitted downstream success")
        if raw.service.write_lock.locked():
            pytest.fail("Blob failure retained the completed worker lock")
        await manager.close_spider_async()

    asyncio.run(exercise())


@pytest.mark.parametrize("terminal", ["commit_race", "error_race", "worker_cancel"])
def test_terminal_worker_races_do_not_detach_or_spin(tmp_path, monkeypatch, terminal):
    """Distinguish a pre-SQL worker cancellation from the retained E5 fault."""
    manager, raw, observer, stats = _setup(tmp_path)
    original = raw.catalog.evidence.record
    error = RuntimeError("terminal ordinary worker failure")

    async def exercise():
        loop = asyncio.get_running_loop()
        task: asyncio.Task
        deliveries = []

        def record(evidence):
            if terminal == "worker_cancel":
                raise asyncio.CancelledError("worker before SQL; not E5")
            result = original(evidence) if terminal == "commit_race" else None
            loop.call_soon_threadsafe(
                lambda: deliveries.append(task.cancel("completion race"))
            )
            if terminal == "error_race":
                raise error
            return result

        monkeypatch.setattr(raw.catalog.evidence, "record", record)
        task = asyncio.create_task(manager.process_item_async(_item()))
        expected_error = (
            RuntimeError if terminal == "error_race" else asyncio.CancelledError
        )
        with pytest.raises(expected_error) as caught:
            await asyncio.wait_for(task, 5)
        if terminal == "error_race" and (
            caught.value is not error
            or not isinstance(error.__cause__, asyncio.CancelledError)
        ):
            pytest.fail("Completion race lost worker error or cancellation")
        if terminal != "worker_cancel" and deliveries != [True]:
            pytest.fail("Terminal race did not deliver a real caller cancel")
        if _count(raw.catalog) != int(terminal == "commit_race"):
            pytest.fail("Terminal cancellation changed durable row outcome")
        if (
            observer.items
            or raw.service.evidence_aliases
            or stats.get_value("msgloom/evidence/response_persisted_count", 0)
        ):
            pytest.fail("Terminal cancellation published success")
        if raw.service.write_lock.locked():
            pytest.fail("Terminal worker was not retrieved")
        await manager.close_spider_async()

    asyncio.run(exercise())


def test_success_cache_and_passthrough_publish_only_after_evidence(
    tmp_path, monkeypatch
):
    """Retain canonical cache ID/time and publication order through manager."""
    manager, raw, observer, stats = _setup(tmp_path)
    original = raw.service.register_evidence_alias
    order = []

    def alias(provisional, canonical, observed_at):
        if not raw.catalog.evidence.contains(canonical):
            pytest.fail("Alias publication preceded durable SQL evidence")
        order.append(("alias", provisional, canonical, observed_at))
        return original(provisional, canonical, observed_at)

    monkeypatch.setattr(raw.service, "register_evidence_alias", alias)
    increment = stats.inc_value

    def durable_stat(key, count=1, **kwargs):
        if key.startswith("msgloom/evidence/") and (
            not order or not raw.catalog.evidence.contains(order[-1][2])
        ):
            pytest.fail("Success statistic preceded durable evidence and alias")
        return increment(key, count=count, **kwargs)

    monkeypatch.setattr(stats, "inc_value", durable_stat)

    async def exercise():
        unknown = object()
        if await manager.process_item_async(unknown) is not unknown:
            pytest.fail("Non-raw pass-through changed the item")
        if _count(raw.catalog) or order or list(raw.raw_dir.iterdir()):
            pytest.fail("Non-raw pass-through persisted evidence")
        first = _item()
        await manager.process_item_async(first)
        cached = _item("provisional-cache", "http_cache")
        cached.observed_at = "2026-10-05T00:00:00Z"
        cached.run_id = "new-logical-run"
        await manager.process_item_async(cached)
        if (cached.evidence_id, cached.observed_at, cached.run_id) != (
            first.evidence_id,
            first.observed_at,
            "new-logical-run",
        ):
            pytest.fail("Cache replay changed canonical ID/time or logical run")
        if _count(raw.catalog) != 1 or order != [
            ("alias", "capture", "capture", first.observed_at),
            ("alias", "provisional-cache", "capture", first.observed_at),
        ]:
            pytest.fail("Exact cache replay created a capture or wrong alias")
        if (
            observer.items != [unknown, first, cached]
            or stats.get_value("msgloom/evidence/cache_link_count", 0) != 1
        ):
            pytest.fail("Cache replay lost sequential downstream completion")
        await manager.close_spider_async()

    asyncio.run(exercise())
