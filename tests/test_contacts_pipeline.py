"""Exercise Contacts pipeline ordering and failure gates around native idle."""

import asyncio
from threading import Event

import pytest
from scrapy.exceptions import CloseSpider
from scrapy.utils.test import get_crawler

from message_ingest.extensions.catalog import CatalogService
from message_ingest.extensions.microsoft.contacts.checkpoint import (
    ContactsSnapshotPromotionExtension,
)
from message_ingest.extensions.microsoft_graph.integrity import (
    MicrosoftGraphIntegrityExtension,
)
from message_ingest.items.microsoft.contacts import ContactItem
from message_ingest.pipelines.microsoft.contacts import ContactsPipeline
from message_ingest.spiders.microsoft.contacts.snapshot import (
    MicrosoftContactsSyncSpider,
)


def _crawler(tmp_path):
    return get_crawler(
        MicrosoftContactsSyncSpider,
        {
            "MSGLOOM_CATALOG_ENABLED": True,
            "MSGLOOM_CONTACTS_SOURCE_ID": "contacts-test",
            "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
            "MSGLOOM_SOURCE_IDENTITY_REQUIRED": False,
        },
    )


def _item(spider):
    return ContactItem.from_graph(
        {"id": "synthetic-contact", "displayName": ""},
        folder_id=None,
        is_default_scope=True,
        observation_kind="snapshot",
        observed_at="2026-09-29T00:01:00Z",
        evidence_id="synthetic-evidence",
        run_id=spider.run_id,
        run_started_at=spider.run_started_at,
    )


def test_contacts_pipeline_awaits_shared_lock_and_worker_commit(tmp_path, monkeypatch):
    crawler = _crawler(tmp_path)
    spider = crawler._create_spider()
    if not isinstance(spider, MicrosoftContactsSyncSpider):
        pytest.fail("Crawler created an unexpected Contacts spider")
    pipeline = ContactsPipeline.from_crawler(crawler)
    item = _item(spider)
    release = Event()
    original = pipeline.store.persist_contact

    async def exercise():
        service = CatalogService.from_crawler(crawler)
        entered = asyncio.Event()
        loop = asyncio.get_running_loop()

        def blocked_write(value):
            if not service.write_lock.locked():
                raise RuntimeError("Contacts worker ran outside shared write lock")
            loop.call_soon_threadsafe(entered.set)
            if not release.wait(5):
                raise RuntimeError("Test did not release Contacts write")
            return original(value)

        monkeypatch.setattr(pipeline.store, "persist_contact", blocked_write)
        await service.write_lock.acquire()
        task = asyncio.create_task(pipeline.process_item(item))
        try:
            await asyncio.sleep(0)
            if entered.is_set():
                pytest.fail("Contacts write did not wait for shared catalog lock")
            service.write_lock.release()
            await asyncio.wait_for(entered.wait(), 5)
            if task.done():
                pytest.fail("Contacts pipeline returned before worker commit")
        finally:
            release.set()
            await task

    try:
        asyncio.run(exercise())
        contact_stats = {
            key: value
            for key, value in crawler.stats.get_stats().items()
            if key.startswith("msgloom/catalog/contacts/")
        }
        if len(contact_stats) > 3 or any(
            "synthetic-contact" in key for key in contact_stats
        ):
            pytest.fail(
                "Contacts persistence emitted unbounded provider-labelled stats"
            )
    finally:
        pipeline.close_spider()


def test_pipeline_error_marks_run_failed_and_blocks_snapshot_promotion(
    tmp_path, monkeypatch
):
    crawler = _crawler(tmp_path)
    spider = crawler._create_spider()
    if not isinstance(spider, MicrosoftContactsSyncSpider):
        pytest.fail("Crawler created an unexpected Contacts spider")
    pipeline = ContactsPipeline.from_crawler(crawler)

    def fail_write(_item):
        raise OSError("synthetic catalog failure")

    monkeypatch.setattr(pipeline.store, "persist_contact", fail_write)
    try:
        with pytest.raises(OSError, match="synthetic catalog failure"):
            asyncio.run(pipeline.process_item(_item(spider)))
        MicrosoftGraphIntegrityExtension.item_error(spider)
        extension = ContactsSnapshotPromotionExtension.from_crawler(crawler)
        with pytest.raises(CloseSpider) as raised:
            extension.spider_idle(spider)
        if raised.value.reason != "contacts_snapshot_incomplete":
            pytest.fail("Pipeline failure used the wrong close reason")
        if not spider.run_failed:
            pytest.fail("Pipeline failure did not poison Contacts run integrity")
    finally:
        pipeline.close_spider()


def test_item_drop_marks_run_failed_and_blocks_snapshot_promotion(tmp_path):
    crawler = _crawler(tmp_path)
    spider = crawler._create_spider()
    if not isinstance(spider, MicrosoftContactsSyncSpider):
        pytest.fail("Crawler created an unexpected Contacts spider")
    pipeline = ContactsPipeline.from_crawler(crawler)
    try:
        MicrosoftGraphIntegrityExtension.item_dropped(spider)
        extension = ContactsSnapshotPromotionExtension.from_crawler(crawler)
        with pytest.raises(CloseSpider) as raised:
            extension.spider_idle(spider)
        if raised.value.reason != "contacts_snapshot_incomplete":
            pytest.fail("Item drop used the wrong close reason")
        if not spider.run_failed:
            pytest.fail("Dropped Contacts item did not poison run integrity")
    finally:
        pipeline.close_spider()
