"""Exercise evidence linking and awaited OneDrive catalog pipeline writes."""

import asyncio
import importlib
from threading import Event

import pytest
from scrapy.exceptions import NotConfigured
from scrapy.utils.test import get_crawler
from sqlalchemy import select

from message_ingest.acquisition.evidence_link import EvidenceLinkPipeline
from message_ingest.catalog.models.microsoft.onedrive import (
    OneDriveContentCapture,
    OneDriveContentRecord,
    OneDriveItemRecord,
)
from message_ingest.extensions.catalog import CatalogService
from message_ingest.items.acquisition import RawHttpEvidenceItem
from message_ingest.items.microsoft.onedrive import OneDriveContentItem, OneDriveItem
from message_ingest.pipelines.evidence import RawEvidencePipeline


def _pipeline_type():
    try:
        return importlib.import_module(
            "message_ingest.pipelines.microsoft.onedrive"
        ).OneDrivePipeline
    except ModuleNotFoundError:
        pytest.fail("OneDrive persistence pipeline is missing")


def _crawler(tmp_path):
    return get_crawler(
        settings_dict={
            "MSGLOOM_CATALOG_ENABLED": True,
            "MSGLOOM_RAW_EVIDENCE_ENABLED": True,
            "MSGLOOM_SOURCE_ID": "onedrive-source",
            "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
            "MSGLOOM_RAW_EVIDENCE_DIR": str(tmp_path / "raw"),
        }
    )


def _raw(evidence_id, *, origin="network", observed="2026-09-29T00:00:00Z"):
    return RawHttpEvidenceItem(
        evidence_id=evidence_id,
        run_id="run",
        purpose="onedrive.content",
        observed_at=observed,
        origin=origin,
        request_fingerprint="fingerprint",
        request_url="https://graph.microsoft.com/v1.0/me/drive/items/item/content",
        request_method="GET",
        request_headers={},
        request_body=b"",
        response_url="https://graph.microsoft.com/v1.0/me/drive/items/item/content",
        response_status=200,
        response_headers={},
        response_body=b"file bytes",
        response_flags=["preauthenticated_download_url_redacted"],
    )


def test_pipeline_disabled_without_catalog():
    pipeline_type = _pipeline_type()
    crawler = get_crawler(settings_dict={"MSGLOOM_CATALOG_ENABLED": False})
    with pytest.raises(NotConfigured):
        pipeline_type.from_crawler(crawler)
    if hasattr(crawler, "_msgloom_catalog_service"):
        pytest.fail("Disabled OneDrive pipeline must not initialize a catalog")


def test_pipeline_persists_canonical_evidence_reference_after_linking(tmp_path):
    crawler = _crawler(tmp_path)
    pipeline = _pipeline_type().from_crawler(crawler)
    raw_pipeline = RawEvidencePipeline.from_crawler(crawler)
    link_pipeline = EvidenceLinkPipeline.from_crawler(crawler)
    original = _raw("original")
    replay = _raw("provisional", origin="http_cache", observed="2026-09-30T00:00:00Z")
    item = OneDriveContentItem(
        item_id="private-provider-id",
        content_sha256="digest",
        content_bytes=10,
        observed_at=replay.observed_at,
        evidence_id=replay.evidence_id,
        run_id="run",
    )

    async def exercise():
        await raw_pipeline.process_item(original)
        await raw_pipeline.process_item(replay)
        await link_pipeline.process_item(item)
        if await pipeline.process_item(item) is not item:
            pytest.fail("OneDrive pipeline must return the committed item")

    try:
        asyncio.run(exercise())
        with pipeline.catalog.Session() as session:
            row = session.scalars(select(OneDriveContentRecord)).one()
            if row.latest_evidence_id != "original" or row.latest_observed_at != (
                original.observed_at
            ):
                pytest.fail("OneDrive write overtook canonical evidence linking")
            capture = session.scalars(select(OneDriveContentCapture)).one()
            if (
                capture.evidence_id != "original"
                or capture.observed_at != original.observed_at
            ):
                pytest.fail(
                    "Content version association did not use canonical evidence"
                )
        if (
            crawler.stats.get_value("msgloom/catalog/onedrive/content_created_count")
            != 1
        ):
            pytest.fail("Pipeline did not publish its bounded persistence outcome")
        if any("private-provider-id" in key for key in crawler.stats.get_stats()):
            pytest.fail("Provider ID leaked into a catalog statistic key")
    finally:
        pipeline.close_spider()


def test_pipeline_waits_for_shared_lock_and_worker_commit(tmp_path, monkeypatch):
    crawler = _crawler(tmp_path)
    pipeline = _pipeline_type().from_crawler(crawler)
    item = OneDriveItem.from_graph(
        {"id": "item", "size": 0},
        observed_at="2026-09-29T00:00:00Z",
        evidence_id=None,
        run_id="run",
    )
    release = Event()
    original = pipeline.store.persist_item

    async def exercise():
        service = CatalogService.from_crawler(crawler)
        entered = asyncio.Event()
        loop = asyncio.get_running_loop()

        def blocked_write(item):
            if not service.write_lock.locked():
                raise RuntimeError("OneDrive worker ran outside catalog write lock")
            loop.call_soon_threadsafe(entered.set)
            if not release.wait(5):
                raise RuntimeError("Test did not release OneDrive write")
            return original(item)

        monkeypatch.setattr(pipeline.store, "persist_item", blocked_write)
        await service.write_lock.acquire()
        task = asyncio.create_task(pipeline.process_item(item))
        try:
            await asyncio.sleep(0)
            if entered.is_set():
                pytest.fail("OneDrive write did not wait for the shared lock")
            service.write_lock.release()
            await asyncio.wait_for(entered.wait(), 5)
            if task.done():
                pytest.fail("Pipeline returned before its worker committed")
        finally:
            release.set()
            await task
        marker = object()
        if await pipeline.process_item(marker) is not marker:
            pytest.fail("Unrelated acquisition items must pass through")

    try:
        asyncio.run(exercise())
        with pipeline.catalog.Session() as session:
            if session.scalars(select(OneDriveItemRecord)).one().size != 0:
                pytest.fail("Awaited OneDrive write was not durable")
    finally:
        pipeline.close_spider()


def test_pipeline_propagates_write_errors_for_checkpoint_integrity(
    tmp_path, monkeypatch
):
    crawler = _crawler(tmp_path)
    pipeline = _pipeline_type().from_crawler(crawler)
    item = OneDriveItem.from_graph(
        {"id": "item"},
        observed_at="2026-09-29T00:00:00Z",
        evidence_id=None,
        run_id="run",
    )

    def failed_write(_item):
        raise OSError("catalog write failed")

    monkeypatch.setattr(pipeline.store, "persist_item", failed_write)
    try:
        with pytest.raises(OSError, match="catalog write failed"):
            asyncio.run(pipeline.process_item(item))
        if crawler.stats.get_value("msgloom/catalog/onedrive/item_created_count"):
            pytest.fail("A failed catalog write was counted as durable")
    finally:
        pipeline.close_spider()
