"""
Verify private content-addressed payload storage and canonical cache evidence
reuse.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from scrapy.pipelines import ItemPipelineManager
from scrapy.utils.test import get_crawler
from sqlalchemy import func, select

from message_ingest.acquisition.contracts import EvidenceLinkedItem
from message_ingest.acquisition.evidence_link import EvidenceLinkPipeline
from message_ingest.catalog import (
    MessageObservation,
    MessageRecord,
    RawHttpEvidence,
)
from message_ingest.extensions.catalog import CatalogService
from message_ingest.items.acquisition import RawHttpEvidenceItem
from message_ingest.items.microsoft.outlook.email import OutlookMailItem
from message_ingest.pipelines.evidence import RawEvidencePipeline
from message_ingest.pipelines.microsoft.outlook.email import OutlookMailPipeline


def _crawler(tmp_path: Path):
    return get_crawler(
        settings_dict={
            "MSGLOOM_RAW_EVIDENCE_ENABLED": True,
            "MSGLOOM_CATALOG_ENABLED": True,
            "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
            "MSGLOOM_RAW_EVIDENCE_DIR": str(tmp_path / "raw"),
            "MSGLOOM_SOURCE_ID": "source-1",
        }
    )


def _raw_item(
    *,
    evidence_id: str = "provisional-1",
    origin: str = "network",
    observed_at: str = "2026-09-26T01:00:00+00:00",
) -> RawHttpEvidenceItem:
    return RawHttpEvidenceItem(
        evidence_id=evidence_id,
        run_id="run-1",
        purpose="message-list",
        observed_at=observed_at,
        origin=origin,
        request_fingerprint="abc123",
        request_url="https://graph.microsoft.com/v1.0/me/messages",
        request_method="GET",
        request_headers={"Accept": ["application/json"]},
        request_body=b"",
        response_url="https://graph.microsoft.com/v1.0/me/messages",
        response_status=200,
        response_headers={"Content-Type": ["application/json"]},
        response_body=b'{"value":[]}',
        response_flags=["cached"] if origin == "http_cache" else [],
    )


def _mail(evidence_id: str) -> OutlookMailItem:
    return OutlookMailItem(
        message_id="m1",
        subject="Hello",
        sender_address="sender@example.com",
        from_address="sender@example.com",
        received_date_time="2026-09-26T01:00:00Z",
        internet_message_id="<m1@example.test>",
        conversation_id="c1",
        parent_folder_id="inbox",
        importance="normal",
        inference_classification="focused",
        is_read=False,
        has_attachments=False,
        body_preview="Preview",
        raw={
            "id": "m1",
            "subject": "Hello",
            "parentFolderId": "inbox",
            "isRead": False,
            "hasAttachments": False,
        },
        source_response_url="https://graph.microsoft.com/v1.0/me/messages",
        observed_at="2026-09-26T01:00:00+00:00",
        observation_kind="discovery",
        evidence_id=evidence_id,
        run_id="run-1",
    )


def test_raw_evidence_pipeline_persists_complete_http_exchange(tmp_path: Path) -> None:
    crawler = _crawler(tmp_path)
    pipeline = RawEvidencePipeline.from_crawler(crawler)
    item = _raw_item()

    returned = asyncio.run(pipeline.process_item(item))

    if returned is not item:
        pytest.fail("Expected: returned is item")
    with pipeline.catalog.Session() as session:
        evidence = session.get(RawHttpEvidence, item.evidence_id)
        if evidence is None:
            pytest.fail("Expected: evidence is not None")
        if evidence.request_url != item.request_url:
            pytest.fail("Expected: evidence.request_url == item.request_url")
        if evidence.request_method != "GET":
            pytest.fail('Expected: evidence.request_method == "GET"')
        if evidence.request_headers != {"Accept": ["application/json"]}:
            pytest.fail(
                'Expected: evidence.request_headers == {"Accept": ["application/json"]}'
            )
        if evidence.request_body_bytes != 0:
            pytest.fail("Expected: evidence.request_body_bytes == 0")
        if evidence.response_status != 200:
            pytest.fail("Expected: evidence.response_status == 200")
        if evidence.response_headers != {"Content-Type": ["application/json"]}:
            pytest.fail(
                'Expected: evidence.response_headers == {"Content-Type": ["application/json"]}'
            )
        if evidence.response_body_bytes != len(item.response_body):
            pytest.fail(
                "Expected: evidence.response_body_bytes == len(item.response_body)"
            )
        if Path(evidence.request_body_path).read_bytes() != b"":
            pytest.fail(
                'Expected: Path(evidence.request_body_path).read_bytes() == b""'
            )
        if Path(evidence.response_body_path).read_bytes() != item.response_body:
            pytest.fail(
                "Expected: Path(evidence.response_body_path).read_bytes() == item.response_body"
            )
        if Path(evidence.response_body_path).stat().st_mode & 511 != 384:
            pytest.fail(
                "Expected: Path(evidence.response_body_path).stat().st_mode & 0o777 == 0o600"
            )
    CatalogService.from_crawler(crawler).spider_closed(None, "test-finished")


def test_http_cache_replay_links_to_existing_source_evidence(tmp_path: Path) -> None:
    crawler = _crawler(tmp_path)
    pipeline = RawEvidencePipeline.from_crawler(crawler)
    first = _raw_item(evidence_id="network-1", origin="network")
    asyncio.run(pipeline.process_item(first))

    replay = _raw_item(
        evidence_id="cache-provisional",
        origin="http_cache",
        observed_at="2026-09-26T02:00:00+00:00",
    )
    asyncio.run(pipeline.process_item(replay))

    if replay.evidence_id != first.evidence_id:
        pytest.fail("Expected: replay.evidence_id == first.evidence_id")
    if replay.observed_at != first.observed_at:
        pytest.fail("Expected: replay.observed_at == first.observed_at")
    with pipeline.catalog.Session() as session:
        count = session.scalar(select(func.count()).select_from(RawHttpEvidence))
        if count != 1:
            pytest.fail("Expected: count == 1")
    if crawler.stats.get_value("msgloom/evidence/cache_link_count") != 1:
        pytest.fail(
            'Expected: crawler.stats.get_value("msgloom/evidence/cache_link_count") == 1'
        )
    CatalogService.from_crawler(crawler).spider_closed(None, "test-finished")


def test_evidence_link_pipeline_rejects_item_without_persisted_raw_evidence(
    tmp_path: Path,
) -> None:
    crawler = _crawler(tmp_path)
    pipeline = EvidenceLinkPipeline.from_crawler(crawler)
    item = _mail("missing-evidence")
    original_observed_at = item.observed_at

    with pytest.raises(RuntimeError, match="raw HTTP evidence"):
        asyncio.run(pipeline.process_item(item))

    if item.evidence_id != "missing-evidence":
        pytest.fail("Expected failed validation not to mutate evidence_id")
    if item.observed_at != original_observed_at:
        pytest.fail("Expected failed validation not to mutate observed_at")
    with pipeline.catalog.Session() as session:
        if session.scalar(select(func.count()).select_from(MessageRecord)) != 0:
            pytest.fail(
                "Expected: session.scalar(select(func.count()).select_from(MessageRecord)) == 0"
            )
    CatalogService.from_crawler(crawler).spider_closed(None, "test-finished")


def test_raw_link_and_catalog_pipelines_preserve_canonical_evidence(
    tmp_path: Path,
) -> None:
    crawler = _crawler(tmp_path)
    raw_pipeline = RawEvidencePipeline.from_crawler(crawler)
    link_pipeline = EvidenceLinkPipeline.from_crawler(crawler)
    catalog_pipeline = OutlookMailPipeline.from_crawler(crawler)

    raw = _raw_item(evidence_id="provisional")
    semantic = _mail("provisional")
    asyncio.run(raw_pipeline.process_item(raw))
    asyncio.run(link_pipeline.process_item(semantic))
    asyncio.run(catalog_pipeline.process_item(semantic))

    if semantic.evidence_id != raw.evidence_id:
        pytest.fail("Expected: semantic.evidence_id == raw.evidence_id")
    with catalog_pipeline.catalog.Session() as session:
        message = session.scalar(select(MessageRecord))
        if message is None:
            pytest.fail("Expected: message is not None")
        if message.latest_evidence_id != raw.evidence_id:
            pytest.fail("Expected: message.latest_evidence_id == raw.evidence_id")
    CatalogService.from_crawler(crawler).spider_closed(None, "test-finished")


def test_evidence_link_contract_covers_current_semantic_item_types() -> None:
    from message_ingest.items.acquisition import AcquisitionFailureItem
    from message_ingest.items.microsoft.outlook.email import (
        OutlookAttachmentItem,
        OutlookDeltaCheckpointCandidateItem,
        OutlookMailDetailItem,
        OutlookMailFolderItem,
        OutlookMailRemovalItem,
        OutlookMessageSurfaceItem,
    )

    item_types = (
        OutlookMailItem,
        OutlookMailDetailItem,
        OutlookAttachmentItem,
        OutlookMailFolderItem,
        OutlookMailRemovalItem,
        OutlookMessageSurfaceItem,
        OutlookDeltaCheckpointCandidateItem,
        AcquisitionFailureItem,
    )
    for item_type in item_types:
        item = object.__new__(item_type)
        item.evidence_id = None
        item.observed_at = "2026-09-27T00:00:00+00:00"
        if not isinstance(item, EvidenceLinkedItem):
            pytest.fail(f"Expected {item_type.__name__} to satisfy EvidenceLinkedItem")


def test_evidence_link_pipeline_passes_unknown_item_through(tmp_path: Path) -> None:
    crawler = _crawler(tmp_path)
    pipeline = EvidenceLinkPipeline.from_crawler(crawler)
    item = object()

    returned = asyncio.run(pipeline.process_item(item))

    if returned is not item:
        pytest.fail("Expected unknown item to pass through unchanged")
    CatalogService.from_crawler(crawler).spider_closed(None, "test-finished")


def test_native_pipeline_manager_orders_raw_link_then_mail_catalog(
    tmp_path: Path,
) -> None:
    from message_ingest.spiders.microsoft.outlook.email.discover import (
        OutlookDiscoverSpider,
    )

    crawler = get_crawler(
        OutlookDiscoverSpider,
        settings_dict={
            "ITEM_PIPELINES": {
                "message_ingest.pipelines.evidence.RawEvidencePipeline": 200,
                "message_ingest.acquisition.evidence_link.EvidenceLinkPipeline": 250,
                "message_ingest.pipelines.microsoft.outlook.email.OutlookMailPipeline": 300,
            },
            "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
            "MSGLOOM_SOURCE_ID": "source-1",
            "MSGLOOM_CATALOG_ENABLED": True,
            "MSGLOOM_RAW_EVIDENCE_ENABLED": True,
            "MSGLOOM_RAW_EVIDENCE_DIR": str(tmp_path / "raw"),
        },
    )
    manager = ItemPipelineManager.from_crawler(crawler)
    names = [type(pipeline).__name__ for pipeline in manager.middlewares]
    expected = ["RawEvidencePipeline", "EvidenceLinkPipeline", "OutlookMailPipeline"]
    if names != expected:
        pytest.fail(f"Unexpected native pipeline order: {names!r}")

    original = _raw_item(
        evidence_id="pipeline-original",
        observed_at="2026-09-26T01:00:00+00:00",
    )
    replay = _raw_item(
        evidence_id="pipeline-provisional",
        origin="http_cache",
        observed_at="2026-09-26T02:00:00+00:00",
    )
    semantic = _mail("pipeline-provisional")
    semantic.observed_at = replay.observed_at

    asyncio.run(manager.process_item_async(original))
    asyncio.run(manager.process_item_async(replay))
    asyncio.run(manager.process_item_async(semantic))

    if replay.evidence_id != original.evidence_id:
        pytest.fail("Expected cache replay to resolve to original evidence")
    if semantic.evidence_id != original.evidence_id:
        pytest.fail("Expected EvidenceLinkPipeline to canonicalize before catalog")
    if semantic.observed_at != original.observed_at:
        pytest.fail("Expected EvidenceLinkPipeline to restore capture timestamp")
    service = CatalogService.from_crawler(crawler)
    with service.catalog.Session() as session:
        message = session.scalar(select(MessageRecord))
        observation = session.scalar(select(MessageObservation))
        if message is None or observation is None:
            pytest.fail("Expected Mail catalog stage to persist the semantic item")
        if message.latest_evidence_id != original.evidence_id:
            pytest.fail("Expected catalog row to reference canonical evidence")
        if observation.evidence_id != original.evidence_id:
            pytest.fail("Expected observation to reference canonical evidence")
        if observation.observed_at != original.observed_at:
            pytest.fail("Expected observation to retain original capture time")
    asyncio.run(manager.close_spider_async())


def test_native_pipeline_manager_blocks_mail_catalog_on_missing_evidence(
    tmp_path: Path,
) -> None:
    from message_ingest.spiders.microsoft.outlook.email.discover import (
        OutlookDiscoverSpider,
    )

    crawler = get_crawler(
        OutlookDiscoverSpider,
        settings_dict={
            "ITEM_PIPELINES": {
                "message_ingest.pipelines.evidence.RawEvidencePipeline": 200,
                "message_ingest.acquisition.evidence_link.EvidenceLinkPipeline": 250,
                "message_ingest.pipelines.microsoft.outlook.email.OutlookMailPipeline": 300,
            },
            "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
            "MSGLOOM_SOURCE_ID": "source-1",
            "MSGLOOM_CATALOG_ENABLED": True,
            "MSGLOOM_RAW_EVIDENCE_ENABLED": True,
            "MSGLOOM_RAW_EVIDENCE_DIR": str(tmp_path / "raw"),
        },
    )
    manager = ItemPipelineManager.from_crawler(crawler)

    with pytest.raises(RuntimeError, match="raw HTTP evidence"):
        asyncio.run(manager.process_item_async(_mail("missing-evidence")))

    service = CatalogService.from_crawler(crawler)
    with service.catalog.Session() as session:
        count = session.scalar(select(func.count()).select_from(MessageRecord))
        if count != 0:
            pytest.fail("Expected Mail catalog stage not to run after link failure")
    asyncio.run(manager.close_spider_async())


@pytest.mark.parametrize("phase", ["before_acceptance", "during_accepted_write"])
def test_public_raw_pipeline_cancellation_drains_accepted_worker(
    tmp_path, monkeypatch, phase
):
    """Keep accepted persistence and resource lifetime inside cancellation."""
    import json
    import sqlite3
    import threading

    crawler = get_crawler(
        settings_dict={
            "ITEM_PIPELINES": {
                "message_ingest.pipelines.evidence.RawEvidencePipeline": 200,
            },
            "MSGLOOM_CATALOG_ENABLED": True,
            "MSGLOOM_RAW_EVIDENCE_ENABLED": True,
            "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
            "MSGLOOM_RAW_EVIDENCE_DIR": str(tmp_path / "raw"),
            "MSGLOOM_SOURCE_ID": "source-1",
        }
    )
    manager = ItemPipelineManager.from_crawler(crawler)
    pipeline = next(
        p for p in manager.middlewares if isinstance(p, RawEvidencePipeline)
    )
    service = pipeline.service
    finish = threading.Event()
    report: dict[str, object] = {
        "phase": phase,
        "worker_entered": False,
        "worker_committed": False,
    }

    async def exercise():
        loop = asyncio.get_running_loop()
        accepted, drained = asyncio.Event(), asyncio.Event()
        original = pipeline.catalog.evidence.record

        def gated_record(evidence):
            report["worker_entered"] = True
            report["blobs_before_sql"] = (
                Path(evidence.request_body_path).read_bytes() == b""
                and Path(evidence.response_body_path).read_bytes() == b'{"value":[]}'
            )
            loop.call_soon_threadsafe(accepted.set)
            try:
                if not finish.wait(5):
                    raise RuntimeError("Raw worker release barrier expired")
                result = original(evidence)
                report["worker_committed"] = True
                return result
            finally:
                loop.call_soon_threadsafe(drained.set)

        async def checkpoint():
            reached = asyncio.Event()
            loop.call_soon(reached.set)
            await reached.wait()

        monkeypatch.setattr(pipeline.catalog.evidence, "record", gated_record)
        if phase == "before_acceptance":
            await service.write_lock.acquire()
        task = asyncio.create_task(manager.process_item_async(_raw_item()))
        try:
            if phase == "during_accepted_write":
                await asyncio.wait_for(accepted.wait(), 5)
            else:
                await checkpoint()
            task.cancel()
            await checkpoint()
            report["cancel_completed_before_drain"] = task.done()
            report["lock_held_before_drain"] = service.write_lock.locked()
            report["alias_before_drain"] = dict(service.evidence_aliases)
            report["success_stats_before_drain"] = crawler.stats.get_value(
                "msgloom/evidence/response_persisted_count", 0
            )
            if task.done():
                with pytest.raises(asyncio.CancelledError):
                    await task
                await manager.close_spider_async()
            report["service_closed_before_drain"] = service._closed
            finish.set()
            if phase == "during_accepted_write":
                await asyncio.wait_for(drained.wait(), 5)
            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(task, 5)
        finally:
            finish.set()
            if report["worker_entered"]:
                await asyncio.wait_for(drained.wait(), 5)
            if phase == "before_acceptance":
                service.write_lock.release()
            await manager.close_spider_async()
            pipeline.catalog.close()

    asyncio.run(exercise())
    with sqlite3.connect(tmp_path / "catalog.sqlite3") as connection:
        report["evidence_rows"] = connection.execute(
            "SELECT COUNT(*) FROM raw_http_evidence"
        ).fetchone()[0]
    report["alias_after_drain"] = dict(service.evidence_aliases)
    report["success_stats_after_drain"] = crawler.stats.get_value(
        "msgloom/evidence/response_persisted_count", 0
    )
    (tmp_path / "cancellation.json").write_text(json.dumps(report, indent=2))
    if report["alias_before_drain"] or report["success_stats_before_drain"]:
        pytest.fail("Cancelled raw write published success before durability")
    if report["alias_after_drain"] or report["success_stats_after_drain"]:
        pytest.fail("Cancelled raw stage fabricated successful completion")
    if phase == "before_acceptance":
        if report["worker_entered"] or report["evidence_rows"]:
            pytest.fail("Cancellation before acceptance started persistence")
        if not report["cancel_completed_before_drain"]:
            pytest.fail("Unaccepted cancellation did not complete")
    else:
        if not report["blobs_before_sql"] or not report["worker_committed"]:
            pytest.fail("Accepted fixture did not execute real blob/SQL persistence")
        if report["evidence_rows"] != 1:
            pytest.fail("Accepted real worker did not persist exactly one capture")
        if (
            report["cancel_completed_before_drain"]
            or not report["lock_held_before_drain"]
            or report["service_closed_before_drain"]
        ):
            pytest.fail(f"Raw cancellation escaped its accepted worker: {report}")
