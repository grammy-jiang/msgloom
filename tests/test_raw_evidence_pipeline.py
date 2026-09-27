"""
Verify private content-addressed payload storage and canonical cache evidence
reuse.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from scrapy.utils.test import get_crawler
from sqlalchemy import func, select

from message_ingest.catalog import MessageRecord, RawHttpEvidence
from message_ingest.extensions.catalog import CatalogService
from message_ingest.items import OutlookMailItem, RawHttpEvidenceItem
from message_ingest.pipelines.catalog import CatalogPipeline
from message_ingest.pipelines.evidence import RawEvidencePipeline


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


def test_catalog_pipeline_rejects_semantic_item_without_persisted_raw_evidence(
    tmp_path: Path,
) -> None:
    crawler = _crawler(tmp_path)
    pipeline = CatalogPipeline.from_crawler(crawler)

    with pytest.raises(RuntimeError, match="raw HTTP evidence"):
        asyncio.run(pipeline.process_item(_mail("missing-evidence")))

    with pipeline.catalog.Session() as session:
        if session.scalar(select(func.count()).select_from(MessageRecord)) != 0:
            pytest.fail(
                "Expected: session.scalar(select(func.count()).select_from(MessageRecord)) == 0"
            )
    CatalogService.from_crawler(crawler).spider_closed(None, "test-finished")


def test_raw_pipeline_then_catalog_pipeline_resolves_canonical_evidence(
    tmp_path: Path,
) -> None:
    crawler = _crawler(tmp_path)
    raw_pipeline = RawEvidencePipeline.from_crawler(crawler)
    catalog_pipeline = CatalogPipeline.from_crawler(crawler)

    raw = _raw_item(evidence_id="provisional")
    semantic = _mail("provisional")
    asyncio.run(raw_pipeline.process_item(raw))
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
