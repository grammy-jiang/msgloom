"""Regress OneDrive database-writer and idle-promotion ownership races."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from scrapy.exceptions import CloseSpider
from scrapy.utils.test import get_crawler
from sqlalchemy import event, text

import message_ingest.catalog.stores.microsoft.onedrive as onedrive_store_module
from message_ingest.catalog import Catalog, RawHttpEvidence
from message_ingest.catalog.models.microsoft.onedrive import OneDriveItemRecord
from message_ingest.catalog.stores.microsoft.onedrive import OneDriveStore
from message_ingest.extensions.catalog import CatalogService
from message_ingest.extensions.microsoft.onedrive.checkpoint import (
    OneDriveDeltaCheckpointExtension,
)
from message_ingest.items.microsoft.onedrive import (
    OneDriveDeltaCheckpointCandidateItem,
    OneDriveDeltaResyncAttemptItem,
    OneDriveItem,
)
from message_ingest.pipelines.microsoft.onedrive import OneDrivePipeline
from message_ingest.spiders.microsoft.onedrive.delta import (
    MicrosoftOneDriveDeltaSpider,
)


def _evidence(catalog, evidence_id, run_id, observed_at):
    catalog.evidence.record(
        RawHttpEvidence(
            evidence_id=evidence_id,
            source_id="source",
            run_id=run_id,
            purpose="onedrive-delta-page",
            observed_at=observed_at,
            origin="network",
            request_fingerprint=f"fp-{evidence_id}",
            request_url="https://graph.microsoft.com/v1.0/me/drive/root/delta",
            request_method="GET",
            request_headers={},
            request_body_sha256="empty",
            request_body_path="empty.bin",
            request_body_bytes=0,
            response_url="https://graph.microsoft.com/v1.0/me/drive/root/delta",
            response_status=200,
            response_headers={},
            response_body_sha256=f"body-{evidence_id}",
            response_body_path=f"{evidence_id}.bin",
            response_body_bytes=2,
            response_flags=[],
            error_type=None,
            error_message=None,
        )
    )


def _candidate(run_id, base_revision, evidence_id, observed_at, delta_link):
    return OneDriveDeltaCheckpointCandidateItem(
        delta_link=delta_link,
        base_revision=base_revision,
        observed_at=observed_at,
        evidence_id=evidence_id,
        run_id=run_id,
    )


def _item(name, observed_at, run_id):
    return OneDriveItem.from_graph(
        {"id": "raced", "name": name, "eTag": f'"{name}"', "file": {}},
        observed_at=observed_at,
        evidence_id=None,
        run_id=run_id,
    )


def test_independent_catalog_writers_serialize_before_read_modify_write(
    tmp_path, monkeypatch
):
    database_url = f"sqlite:///{tmp_path / 'catalog.sqlite3'}"
    promotion_catalog = Catalog(database_url)
    metadata_catalog = Catalog(database_url)
    promotion_store = OneDriveStore(promotion_catalog, source_id="source")
    metadata_store = OneDriveStore(metadata_catalog, source_id="source")
    promotion_holding = Event()
    release_promotion = Event()
    writer_intent_attempted = Event()
    normal_read_started = Event()
    original_apply = onedrive_store_module.apply_onedrive_resync_state
    original_upsert = metadata_store._upsert_session

    def blocked_apply(*args, **kwargs):
        result = original_apply(*args, **kwargs)
        promotion_holding.set()
        if not release_promotion.wait(5):
            raise RuntimeError("Test did not release checkpoint promotion")
        return result

    def observed_upsert(*args, **kwargs):
        normal_read_started.set()
        return original_upsert(*args, **kwargs)

    def before_cursor_execute(_conn, _cursor, statement, _parameters, _context, _many):
        if statement.strip().upper() == "BEGIN IMMEDIATE":
            writer_intent_attempted.set()

    monkeypatch.setattr(
        onedrive_store_module, "apply_onedrive_resync_state", blocked_apply
    )
    monkeypatch.setattr(metadata_store, "_upsert_session", observed_upsert)
    event.listen(
        metadata_catalog.engine, "before_cursor_execute", before_cursor_execute
    )

    try:
        promotion_store.persist_item(
            _item("old", "2026-09-29T00:00:00+00:00", "old-run")
        )
        _evidence(
            promotion_catalog, "base-terminal", "base-run", "2026-09-29T00:05:00+00:00"
        )
        promotion_store.persist_candidate(
            _candidate(
                "base-run",
                None,
                "base-terminal",
                "2026-09-29T00:05:00+00:00",
                "opaque-base",
            )
        )
        promotion_store.promote_checkpoint(run_id="base-run", base_revision=None)

        _evidence(
            promotion_catalog,
            "reset-trigger",
            "reset-run",
            "2026-09-29T01:00:00+00:00",
        )
        promotion_store.persist_resync_attempt(
            OneDriveDeltaResyncAttemptItem(
                reset_attempt=1,
                base_revision=1,
                started_at="2026-09-29T01:00:00+00:00",
                trigger_evidence_id="reset-trigger",
                run_id="reset-run",
            )
        )
        _evidence(
            promotion_catalog,
            "reset-terminal",
            "reset-run",
            "2026-09-29T01:03:00+00:00",
        )
        promotion_store.persist_candidate(
            _candidate(
                "reset-run",
                1,
                "reset-terminal",
                "2026-09-29T01:03:00+00:00",
                "opaque-reset",
            )
        )

        with ThreadPoolExecutor(max_workers=2) as executor:
            promotion = executor.submit(
                promotion_store.promote_checkpoint,
                run_id="reset-run",
                base_revision=1,
                reset_attempt=1,
            )
            if not promotion_holding.wait(5):
                pytest.fail("Reset promotion did not reach its writer-owned barrier")
            metadata = executor.submit(
                metadata_store.persist_item,
                _item("later", "2026-09-29T01:04:00+00:00", "later-run"),
            )
            try:
                if not writer_intent_attempted.wait(5):
                    pytest.fail("Normal writer never requested database writer intent")
                if normal_read_started.is_set():
                    pytest.fail("Normal writer read state before writer ownership")
            finally:
                release_promotion.set()
            if promotion.result(timeout=5).revision != 2:
                pytest.fail("Reset promotion did not advance the checkpoint")
            if metadata.result(timeout=5) not in {"changed", "unchanged"}:
                pytest.fail("Later metadata observation did not finish")

        with metadata_catalog.Session() as session:
            row = session.get(OneDriveItemRecord, ("source", "raced"))
            if row is None or row.is_deleted or row.name != "later":
                pytest.fail("Later metadata observation did not survive promotion")
    finally:
        release_promotion.set()
        event.remove(
            metadata_catalog.engine, "before_cursor_execute", before_cursor_execute
        )
        promotion_catalog.close()
        metadata_catalog.close()


def test_idle_promotion_finishes_before_pipeline_catalog_close(tmp_path, monkeypatch):
    crawler = get_crawler(
        MicrosoftOneDriveDeltaSpider,
        settings_dict={
            "MSGLOOM_CATALOG_ENABLED": True,
            "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
            "MSGLOOM_ONEDRIVE_SOURCE_ID": "source",
            "MSGLOOM_SOURCE_IDENTITY_REQUIRED": False,
        },
    )
    spider = MicrosoftOneDriveDeltaSpider.from_crawler(crawler)
    crawler.spider = spider
    service = CatalogService.from_crawler(crawler)
    store = OneDriveStore(service.catalog, source_id="source")
    pipeline = OneDrivePipeline.from_crawler(crawler)
    extension = OneDriveDeltaCheckpointExtension.from_crawler(crawler)
    promotion_finished = Event()
    original_promote = OneDriveStore.promote_checkpoint
    original_close = service.close

    _evidence(service.catalog, "terminal", spider.run_id, "2026-09-29T02:00:00+00:00")
    store.persist_candidate(
        _candidate(
            spider.run_id,
            None,
            "terminal",
            "2026-09-29T02:00:00+00:00",
            "opaque-terminal",
        )
    )
    spider.terminal_delta_seen = True

    def tracked_promote(self, **kwargs):
        checkpoint = original_promote(self, **kwargs)
        promotion_finished.set()
        return checkpoint

    def checked_close():
        if not promotion_finished.is_set():
            pytest.fail("Catalog closed before synchronous idle promotion finished")
        checkpoint = store.load_checkpoint()
        if checkpoint is None or checkpoint.revision != 1:
            pytest.fail("Checkpoint was not durable before catalog close")
        original_close()

    monkeypatch.setattr(OneDriveStore, "promote_checkpoint", tracked_promote)
    monkeypatch.setattr(service, "close", checked_close)

    try:
        extension.spider_idle(spider)
        if (
            crawler.stats.get_value("msgloom/onedrive/checkpoint/outcome")
            != "committed"
        ):
            pytest.fail("Clean synchronous promotion lost its committed outcome")
        pipeline.close_spider()
        if not service._closed:
            pytest.fail("Pipeline shutdown did not dispose the catalog")
    finally:
        if not service._closed:
            original_close()

    reopened = Catalog(crawler.settings["MSGLOOM_DATABASE_URL"])
    try:
        checkpoint = OneDriveStore(reopened, source_id="source").load_checkpoint()
        if checkpoint is None or checkpoint.revision != 1:
            pytest.fail("Catalog changed after lifecycle-owned promotion and close")
    finally:
        reopened.close()


@pytest.mark.parametrize("fail", [False, True])
def test_writer_session_restores_driver_mode_and_rolls_back(tmp_path, fail):
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:

        def transact():
            with catalog.writer_session() as session:
                driver = session.connection().connection.driver_connection
                if driver is None:
                    pytest.fail("Writer session has no SQLite driver connection")
                if driver.autocommit is not True:
                    pytest.fail("Writer session did not own driver transaction control")
                session.execute(
                    text("CREATE TABLE writer_session_probe (value INTEGER)")
                )
                if fail:
                    raise RuntimeError("synthetic writer rollback")

        if fail:
            with pytest.raises(RuntimeError, match="synthetic writer rollback"):
                transact()
        else:
            transact()

        with catalog.engine.connect() as connection:
            driver = connection.connection.driver_connection
            if driver is None:
                pytest.fail("Catalog checkout has no SQLite driver connection")
            if driver.autocommit is not False:
                pytest.fail("Writer session did not restore driver autocommit mode")
            table = connection.exec_driver_sql(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name = 'writer_session_probe'"
            ).scalar_one_or_none()
        if (table is None) != fail:
            pytest.fail("Writer session commit/rollback boundary was not atomic")
    finally:
        catalog.close()


def _idle_failure_setup(tmp_path, *, persist_candidate):
    crawler = get_crawler(
        MicrosoftOneDriveDeltaSpider,
        settings_dict={
            "MSGLOOM_CATALOG_ENABLED": True,
            "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
            "MSGLOOM_ONEDRIVE_SOURCE_ID": "source",
            "MSGLOOM_SOURCE_IDENTITY_REQUIRED": False,
        },
    )
    spider = MicrosoftOneDriveDeltaSpider.from_crawler(crawler)
    crawler.spider = spider
    service = CatalogService.from_crawler(crawler)
    store = OneDriveStore(service.catalog, source_id="source")
    extension = OneDriveDeltaCheckpointExtension.from_crawler(crawler)
    spider.terminal_delta_seen = True
    if persist_candidate:
        _evidence(
            service.catalog,
            "failure-terminal",
            spider.run_id,
            "2026-09-29T03:00:00+00:00",
        )
        store.persist_candidate(
            _candidate(
                spider.run_id,
                None,
                "failure-terminal",
                "2026-09-29T03:00:00+00:00",
                "opaque-failure-terminal",
            )
        )
    return crawler, spider, service, store, extension


def _check_fail_closed_idle(crawler, spider, store, excinfo, caplog, secret):
    if excinfo.value.reason != "onedrive_checkpoint_promotion_failed":
        pytest.fail("Persistence failure did not use the checkpoint failure reason")
    if not spider.run_failed:
        pytest.fail("Persistence failure did not invalidate the logical run")
    if crawler.stats.get_value("msgloom/onedrive/checkpoint/outcome") != "error":
        pytest.fail("Persistence failure did not record bounded error outcome")
    if crawler.stats.get_value("msgloom/onedrive/checkpoint/error_count") != 1:
        pytest.fail("Persistence failure did not increment bounded error count")
    if store.load_checkpoint() is not None:
        pytest.fail("Persistence failure unexpectedly committed a checkpoint")
    if secret in caplog.text:
        pytest.fail("Persistence exception value leaked into lifecycle logs")


def test_idle_unexpected_promotion_failure_is_fail_closed(
    tmp_path, monkeypatch, caplog
):
    crawler, spider, service, store, extension = _idle_failure_setup(
        tmp_path, persist_candidate=True
    )
    secret = "opaque-synthetic-promotion-value"

    def fail_promotion(self, **_kwargs):
        raise RuntimeError(secret)

    monkeypatch.setattr(OneDriveStore, "promote_checkpoint", fail_promotion)
    try:
        with pytest.raises(CloseSpider) as excinfo:
            extension.spider_idle(spider)
        _check_fail_closed_idle(crawler, spider, store, excinfo, caplog, secret)
    finally:
        service.close()


def test_idle_candidate_read_failure_is_fail_closed(tmp_path, monkeypatch, caplog):
    crawler, spider, service, store, extension = _idle_failure_setup(
        tmp_path, persist_candidate=False
    )
    secret = "opaque-synthetic-candidate-value"

    def fail_candidate_read(self, **_kwargs):
        raise RuntimeError(secret)

    monkeypatch.setattr(OneDriveStore, "load_candidate", fail_candidate_read)
    try:
        with pytest.raises(CloseSpider) as excinfo:
            extension.spider_idle(spider)
        _check_fail_closed_idle(crawler, spider, store, excinfo, caplog, secret)
    finally:
        service.close()


def test_idle_checks_shared_write_lock_before_candidate_read(tmp_path, monkeypatch):
    _crawler, spider, service, _store, extension = _idle_failure_setup(
        tmp_path, persist_candidate=False
    )
    candidate_read = Event()

    def observe_candidate_read(self, **_kwargs):
        candidate_read.set()
        raise RuntimeError("candidate read must not run")

    monkeypatch.setattr(OneDriveStore, "load_candidate", observe_candidate_read)
    try:
        if not asyncio.run(service.write_lock.acquire()):
            pytest.fail("Synthetic write lock could not be acquired")
        with pytest.raises(CloseSpider) as excinfo:
            extension.spider_idle(spider)
        if candidate_read.is_set():
            pytest.fail(
                "Idle invariant read the database before checking the write lock"
            )
        if excinfo.value.reason != "onedrive_checkpoint_promotion_failed":
            pytest.fail("Held write lock did not fail the checkpoint lifecycle")
        if not spider.run_failed:
            pytest.fail("Held write lock did not invalidate the logical run")
    finally:
        if service.write_lock.locked():
            service.write_lock.release()
        service.close()
