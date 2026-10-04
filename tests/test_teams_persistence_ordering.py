"""Scrapy pipeline ordering, shared-lock, and cancellation-drain tests."""

from __future__ import annotations

import asyncio
import threading
from pathlib import Path

import pytest
from scrapy import Spider
from scrapy.pipelines import ItemPipelineManager
from scrapy.utils.test import get_crawler
from sqlalchemy import select

from message_ingest.catalog.models.microsoft.teams import TeamsMessageObservation
from message_ingest.extensions.catalog import CatalogService
from message_ingest.pipelines.microsoft.teams import TeamsPipeline
from tests.teams_persistence_support import (
    SOURCE,
    chat_message,
    raw_item,
    record_evidence,
)


class _OrderingSpider(Spider):
    """Minimal spider used to build the real native pipeline manager."""

    name = "teams-persistence-ordering-test"


def _settings(tmp_path: Path) -> dict[str, object]:
    """Return isolated settings with the exact required pipeline priorities."""
    return {
        "ITEM_PIPELINES": {
            "message_ingest.pipelines.evidence.RawEvidencePipeline": 200,
            "message_ingest.acquisition.evidence_link.EvidenceLinkPipeline": 250,
            "message_ingest.pipelines.microsoft.teams.TeamsPipeline": 300,
        },
        "MSGLOOM_CATALOG_ENABLED": True,
        "MSGLOOM_RAW_EVIDENCE_ENABLED": True,
        "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
        "MSGLOOM_RAW_EVIDENCE_DIR": str(tmp_path / "raw"),
        "MSGLOOM_SOURCE_ID": SOURCE,
        "CONCURRENT_ITEMS": 1,
        "LOG_ENABLED": False,
        "TELNETCONSOLE_ENABLED": False,
    }


def _crawler(tmp_path: Path):
    """Create a crawler with one shared catalog service."""
    return get_crawler(_OrderingSpider, settings_dict=_settings(tmp_path))


def test_real_pipeline_order_persists_evidence_before_semantics(
    tmp_path: Path,
) -> None:
    crawler = _crawler(tmp_path)
    manager = ItemPipelineManager.from_crawler(crawler)
    service = CatalogService.from_crawler(crawler)
    names = [type(pipeline).__name__ for pipeline in manager.middlewares]
    expected = ["RawEvidencePipeline", "EvidenceLinkPipeline", "TeamsPipeline"]
    if names != expected:
        pytest.fail(f"Unexpected Teams pipeline order: {names!r}")
    if crawler.settings.getint("CONCURRENT_ITEMS") != 1:
        pytest.fail("Teams evidence ordering requires CONCURRENT_ITEMS=1")

    evidence = raw_item("ordering-evidence")
    semantic = chat_message(evidence_id="ordering-evidence")
    try:
        asyncio.run(manager.process_item_async(evidence))
        asyncio.run(manager.process_item_async(semantic))
        with service.catalog.Session() as session:
            row = session.scalar(select(TeamsMessageObservation))
            if row is None or row.evidence_id != evidence.evidence_id:
                pytest.fail("Semantic Teams write did not follow committed evidence")
    finally:
        service.close()


def test_shared_write_lock_serializes_concurrent_semantic_writes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    crawler = _crawler(tmp_path)
    pipeline = TeamsPipeline.from_crawler(crawler)
    service = CatalogService.from_crawler(crawler)
    for evidence_id in ("serialized-1", "serialized-2"):
        record_evidence(service.catalog, evidence_id)
    first = chat_message(
        chat_id="chat-1",
        evidence_id="serialized-1",
    )
    second = chat_message(
        chat_id="chat-2",
        evidence_id="serialized-2",
    )

    started_first = threading.Event()
    release_first = threading.Event()
    started_second = threading.Event()
    active = 0
    maximum_active = 0
    counter_lock = threading.Lock()
    original = pipeline.message_store.persist_message

    def controlled_write(item):
        nonlocal active, maximum_active
        with counter_lock:
            active += 1
            maximum_active = max(maximum_active, active)
        try:
            if item.identity.chat_id == "chat-1":
                started_first.set()
                if not release_first.wait(timeout=5):
                    raise RuntimeError("test failed to release first Teams writer")
            else:
                started_second.set()
            return original(item)
        finally:
            with counter_lock:
                active -= 1

    monkeypatch.setattr(
        pipeline.message_store,
        "persist_message",
        controlled_write,
    )

    async def scenario() -> None:
        first_task = asyncio.create_task(pipeline.process_item(first))
        if not await asyncio.to_thread(started_first.wait, 5):
            pytest.fail("First Teams write did not start")
        second_task = asyncio.create_task(pipeline.process_item(second))
        await asyncio.sleep(0)
        if started_second.is_set():
            pytest.fail("Second Teams write entered while shared lock was held")
        release_first.set()
        await first_task
        await second_task

    try:
        asyncio.run(scenario())
        if maximum_active != 1:
            pytest.fail(f"Shared Teams write lock allowed {maximum_active} writers")
    finally:
        release_first.set()
        service.close()


def test_cancelled_active_write_holds_lock_until_thread_drains_and_close_waits(
    tmp_path: Path,
    monkeypatch,
) -> None:
    crawler = _crawler(tmp_path)
    pipeline = TeamsPipeline.from_crawler(crawler)
    service = CatalogService.from_crawler(crawler)
    record_evidence(service.catalog, "cancel-active")
    item = chat_message(evidence_id="cancel-active")

    started = threading.Event()
    release = threading.Event()
    finished = threading.Event()
    original = pipeline.message_store.persist_message

    def blocked_write(value):
        started.set()
        try:
            if not release.wait(timeout=5):
                raise RuntimeError("test failed to release active Teams writer")
            return original(value)
        finally:
            finished.set()

    monkeypatch.setattr(pipeline.message_store, "persist_message", blocked_write)

    async def scenario() -> None:
        task = asyncio.create_task(pipeline.process_item(item))
        if not await asyncio.to_thread(started.wait, 5):
            pytest.fail("Teams write thread did not start")
        task.cancel()
        task.cancel()
        await asyncio.sleep(0)
        if not service.write_lock.locked():
            pytest.fail("Cancellation released the lock before worker-thread drain")
        close_task = asyncio.create_task(pipeline.close_spider())
        await asyncio.sleep(0)
        if service._closed:
            pytest.fail("Catalog close raced an active Teams writer")
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        if not finished.is_set():
            pytest.fail("Cancelled Teams item returned before its thread drained")
        await close_task
        if not service._closed:
            pytest.fail("Teams pipeline close did not finish after writer drain")
        if service.write_lock.locked():
            pytest.fail("Shared write lock remained held after cancellation drain")

    try:
        asyncio.run(scenario())
    finally:
        release.set()
        service.close()


def test_repeated_cancellation_survives_worker_failure_after_drain(
    tmp_path: Path,
    monkeypatch,
) -> None:
    crawler = _crawler(tmp_path)
    pipeline = TeamsPipeline.from_crawler(crawler)
    service = CatalogService.from_crawler(crawler)
    record_evidence(service.catalog, "cancel-failure")
    item = chat_message(evidence_id="cancel-failure")

    started = threading.Event()
    release = threading.Event()
    finished = threading.Event()

    def failed_write(_value):
        started.set()
        try:
            if not release.wait(timeout=5):
                raise RuntimeError("test failed to release failed Teams writer")
            raise RuntimeError("thread write failed after cancellation")
        finally:
            finished.set()

    monkeypatch.setattr(pipeline.message_store, "persist_message", failed_write)

    async def scenario() -> None:
        task = asyncio.create_task(pipeline.process_item(item))
        if not await asyncio.to_thread(started.wait, 5):
            pytest.fail("Failed Teams write thread did not start")
        task.cancel()
        task.cancel()
        await asyncio.sleep(0)
        if not service.write_lock.locked():
            pytest.fail("Repeated cancellation released active Teams write lock")
        release.set()
        with pytest.raises(asyncio.CancelledError) as captured:
            await task
        if not finished.is_set():
            pytest.fail("Repeated cancellation returned before failed thread drained")
        cause = captured.value.__cause__
        if not isinstance(cause, RuntimeError):
            pytest.fail("Drained worker failure must remain chained to cancellation")
        if "thread write failed" not in str(cause):
            pytest.fail("Unexpected chained worker failure after cancellation")
        if service.write_lock.locked():
            pytest.fail("Write lock remained held after cancelled failed writer")

    try:
        asyncio.run(scenario())
    finally:
        release.set()
        service.close()
