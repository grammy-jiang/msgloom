from __future__ import annotations

import asyncio
import json
from pathlib import Path

from sqlalchemy import select
from scrapy.utils.test import get_crawler

from msgloom.catalog import MessageObservation, MessageRecord, MessageSurface
from msgloom.items import OutlookMailItem, OutlookMessageSurfaceItem
from msgloom.pipelines import CatalogPipeline, LocalJsonlPipeline
from msgloom.services import get_catalog_service


def _message() -> OutlookMailItem:
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
            "receivedDateTime": "2026-09-26T01:00:00Z",
            "lastModifiedDateTime": "2026-09-26T01:01:00Z",
            "parentFolderId": "inbox",
            "isRead": False,
            "hasAttachments": False,
        },
        source_response_url="https://graph.microsoft.com/v1.0/me/messages",
        observed_at="2026-09-26T01:02:00+00:00",
        observation_kind="discovery",
        evidence_id="evidence-1",
        run_id="run-1",
    )


def test_catalog_pipeline_persists_identity_observation_and_surface(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'catalog.sqlite3'}"
    crawler = get_crawler(
        settings_dict={
            "MSGLOOM_DATABASE_URL": db_url,
            "MSGLOOM_SOURCE_ID": "source-1",
            "MSGLOOM_CATALOG_ENABLED": True,
        }
    )
    pipeline = CatalogPipeline.from_crawler(crawler)
    try:
        asyncio.run(pipeline.process_item(_message()))
        asyncio.run(pipeline.process_item(
            OutlookMessageSurfaceItem(
                message_id="m1",
                surface="mime",
                status="acquired",
                observed_at="2026-09-26T01:03:00+00:00",
                evidence_id="evidence-2",
            )
        ))

        with pipeline.catalog.Session() as session:
            message = session.scalar(select(MessageRecord))
            observations = session.scalars(select(MessageObservation)).all()
            surfaces = session.scalars(select(MessageSurface)).all()
            assert message is not None
            assert message.message_id == "m1"
            assert message.latest_evidence_id == "evidence-1"
            assert len(observations) == 1
            assert {surface.surface for surface in surfaces} == {"discovery", "mime"}
    finally:
        get_catalog_service(crawler).spider_closed(None, "test-finished")

    assert (tmp_path / "catalog.sqlite3").stat().st_mode & 0o777 == 0o600


def test_local_jsonl_pipeline_only_writes_semantic_logs_with_private_permissions(tmp_path: Path) -> None:
    crawler = get_crawler(
        settings_dict={
            "MSGLOOM_DATA_DIR": str(tmp_path / "acquisition"),
            "MSGLOOM_JSONL_ENABLED": True,
        }
    )
    pipeline = LocalJsonlPipeline.from_crawler(crawler)
    pipeline.open_spider()
    try:
        asyncio.run(pipeline.process_item(_message()))
    finally:
        pipeline.close_spider()

    path = tmp_path / "acquisition" / "outlook-mail.jsonl"
    rows = path.read_text().splitlines()
    assert len(rows) == 1
    assert json.loads(rows[0])["message_id"] == "m1"
    assert path.stat().st_mode & 0o777 == 0o600
    assert path.parent.stat().st_mode & 0o777 == 0o700
