"""Check Contacts integration with shared transactions and delta failure gates."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from scrapy.exceptions import CloseSpider
from scrapy.utils.test import get_crawler
from sqlalchemy import event

from message_ingest.catalog import Catalog
from message_ingest.catalog.models.microsoft.contacts import ContactRecord
from message_ingest.catalog.stores.microsoft.contacts import ContactsStore
from message_ingest.extensions.microsoft.contacts.checkpoint import (
    ContactsDeltaCheckpointExtension,
)
from message_ingest.extensions.microsoft_graph.integrity import (
    MicrosoftGraphIntegrityExtension,
)
from message_ingest.items.microsoft.contacts import (
    ContactDeltaCheckpointCandidateItem,
    ContactItem,
)
from message_ingest.pipelines.microsoft.contacts import ContactsPipeline
from message_ingest.spiders.microsoft.contacts.delta import MicrosoftContactsDeltaSpider


def _contact(run, *, kind="delta", company="first"):
    return ContactItem.from_graph(
        {"id": "contact", "companyName": company},
        folder_id="folder-a",
        is_default_scope=False,
        observation_kind=kind,
        observed_at="2026-09-29T00:01:00Z",
        evidence_id="synthetic-evidence",
        run_id=run,
        run_started_at="2026-09-29T00:00:00Z",
    )


def _candidate(run, revision):
    return ContactDeltaCheckpointCandidateItem(
        folder_id="folder-a",
        delta_link=f"https://graph.example.test/opaque/{run}",
        base_revision=revision,
        observed_at="2026-09-29T00:02:00Z",
        evidence_id="synthetic-terminal",
        run_id=run,
    )


def test_contacts_mutation_waits_for_independent_catalog_writer(tmp_path):
    url = f"sqlite:///{tmp_path / 'writer.sqlite3'}"
    first = Catalog(url)
    second = Catalog(url)
    holding = Event()
    release = Event()
    writer_attempted = Event()
    store = ContactsStore(second, source_id="contacts-test")

    def hold_writer():
        with first.writer_session():
            holding.set()
            if not release.wait(5):
                raise RuntimeError("Test did not release catalog writer")

    def observe(_conn, _cursor, statement, _params, _context, _many):
        if statement.strip().upper() == "BEGIN IMMEDIATE":
            writer_attempted.set()

    event.listen(second.engine, "before_cursor_execute", observe)
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            owner = executor.submit(hold_writer)
            if not holding.wait(5):
                release.set()
                pytest.fail("First catalog did not acquire writer intent")
            writer = executor.submit(
                store.persist_contact,
                _contact("snapshot", kind="snapshot", company="preserved"),
            )
            try:
                if not writer_attempted.wait(3):
                    pytest.fail("Contacts mutation read before acquiring writer intent")
                if writer.done():
                    pytest.fail("Contacts mutation did not wait for catalog writer")
            finally:
                release.set()
            owner.result(timeout=5)
            writer.result(timeout=5)
        with second.Session() as session:
            record = session.get(
                ContactRecord,
                {
                    "source_id": "contacts-test",
                    "scope_key": "folder:folder-a",
                    "contact_id": "contact",
                },
            )
            if record is None or record.company_name != "preserved":
                pytest.fail("Serialized Contacts mutation did not persist")
    finally:
        release.set()
        second.close()
        first.close()


@pytest.mark.parametrize("failure", ["item_error", "item_drop", "locked", "promotion"])
def test_delta_failure_gate_preserves_committed_cursor(tmp_path, monkeypatch, failure):
    crawler = get_crawler(
        MicrosoftContactsDeltaSpider,
        {
            "MSGLOOM_CATALOG_ENABLED": True,
            "MSGLOOM_CONTACTS_SOURCE_ID": "contacts-test",
            "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'delta.sqlite3'}",
            "MSGLOOM_SOURCE_IDENTITY_REQUIRED": False,
        },
    )
    spider = crawler._create_spider(folder_id="folder-a")
    if not isinstance(spider, MicrosoftContactsDeltaSpider):
        pytest.fail("Crawler created an unexpected Contacts delta spider")
    pipeline = ContactsPipeline.from_crawler(crawler)
    store = pipeline.store
    try:
        store.begin_delta_run(folder_id="folder-a", run_id="prior")
        store.persist_delta_observation(_contact("prior"))
        store.stage_delta_candidate(_candidate("prior", None))
        store.promote_delta(folder_id="folder-a", run_id="prior", base_revision=None)
        store.begin_delta_run(folder_id="folder-a", run_id=spider.run_id)
        store.stage_delta_candidate(_candidate(spider.run_id, 1))
        spider.base_revision = 1
        spider.terminal_delta_seen = True

        if failure == "item_error":

            def fail_write(_item):
                raise OSError("synthetic write failure")

            monkeypatch.setattr(store, "persist_delta_observation", fail_write)
            with pytest.raises(OSError, match="synthetic write failure"):
                asyncio.run(pipeline.process_item(_contact(spider.run_id)))
            MicrosoftGraphIntegrityExtension.item_error(spider)
        elif failure == "item_drop":
            MicrosoftGraphIntegrityExtension.item_dropped(spider)
        elif failure == "locked":
            asyncio.run(pipeline.service.write_lock.acquire())
        else:

            def fail_promotion(*_args, **_kwargs):
                raise RuntimeError("synthetic promotion failure")

            monkeypatch.setattr(ContactsStore, "promote_delta", fail_promotion)

        extension = ContactsDeltaCheckpointExtension.from_crawler(crawler)
        with pytest.raises(CloseSpider) as raised:
            extension.spider_idle(spider)
        expected = (
            "contacts_delta_promotion_failed"
            if failure == "promotion"
            else "contacts_delta_incomplete"
        )
        if raised.value.reason != expected or not spider.run_failed:
            pytest.fail("Delta failure did not mark and close the run")
        checkpoint = store.load_delta_checkpoint("folder-a")
        if (
            checkpoint is None
            or checkpoint.revision != 1
            or checkpoint.run_id != "prior"
        ):
            pytest.fail("Failed delta advanced the committed cursor")
    finally:
        if pipeline.service.write_lock.locked():
            pipeline.service.write_lock.release()
        pipeline.close_spider()
