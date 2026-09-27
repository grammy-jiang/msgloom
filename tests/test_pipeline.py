"""
Check semantic SQL persistence, timestamp ordering, replay detection, and
profile stats.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from scrapy.utils.test import get_crawler
from sqlalchemy import select

from message_ingest.catalog import MessageObservation, MessageRecord, MessageSurface
from message_ingest.extensions.catalog import CatalogService
from message_ingest.items import (
    OutlookMailDetailItem,
    OutlookMailItem,
    OutlookMailRemovalItem,
    OutlookMessageSurfaceItem,
    RawHttpEvidenceItem,
)
from message_ingest.pipelines.catalog import CatalogPipeline
from message_ingest.pipelines.evidence import RawEvidencePipeline
from message_ingest.profiles import FULL_V1


def _raw(evidence_id: str, observed_at: str) -> RawHttpEvidenceItem:
    return RawHttpEvidenceItem(
        evidence_id=evidence_id,
        run_id="run-test",
        purpose="test",
        observed_at=observed_at,
        origin="network",
        request_fingerprint=f"fp-{evidence_id}",
        request_url=f"https://graph.microsoft.com/v1.0/test/{evidence_id}",
        request_method="GET",
        request_headers={"Accept": ["application/json"]},
        request_body=b"",
        response_url=f"https://graph.microsoft.com/v1.0/test/{evidence_id}",
        response_status=200,
        response_headers={"Content-Type": ["application/json"]},
        response_body=b"{}",
        response_flags=[],
    )


def _persist_raw(crawler, evidence_id: str, observed_at: str) -> None:
    raw_pipeline = RawEvidencePipeline.from_crawler(crawler)
    asyncio.run(raw_pipeline.process_item(_raw(evidence_id, observed_at)))


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


def test_catalog_pipeline_persists_identity_observation_and_surface(
    tmp_path: Path,
) -> None:
    db_url = f"sqlite:///{tmp_path / 'catalog.sqlite3'}"
    crawler = get_crawler(
        settings_dict={
            "MSGLOOM_DATABASE_URL": db_url,
            "MSGLOOM_SOURCE_ID": "source-1",
            "MSGLOOM_CATALOG_ENABLED": True,
            "MSGLOOM_RAW_EVIDENCE_ENABLED": True,
            "MSGLOOM_RAW_EVIDENCE_DIR": str(tmp_path / "raw"),
        }
    )
    _persist_raw(crawler, "evidence-1", "2026-09-26T01:02:00+00:00")
    _persist_raw(crawler, "evidence-2", "2026-09-26T01:03:00+00:00")
    pipeline = CatalogPipeline.from_crawler(crawler)
    try:
        asyncio.run(pipeline.process_item(_message()))
        asyncio.run(
            pipeline.process_item(
                OutlookMessageSurfaceItem(
                    message_id="m1",
                    surface="mime",
                    status="acquired",
                    observed_at="2026-09-26T01:03:00+00:00",
                    evidence_id="evidence-2",
                )
            )
        )

        with pipeline.catalog.Session() as session:
            message = session.scalar(select(MessageRecord))
            observations = session.scalars(select(MessageObservation)).all()
            surfaces = session.scalars(select(MessageSurface)).all()
            if message is None:
                pytest.fail("Expected: message is not None")
            if message.message_id != "m1":
                pytest.fail('Expected: message.message_id == "m1"')
            if message.latest_evidence_id != "evidence-1":
                pytest.fail('Expected: message.latest_evidence_id == "evidence-1"')
            if len(observations) != 1:
                pytest.fail("Expected: len(observations) == 1")
            if {surface.surface for surface in surfaces} != {"discovery", "mime"}:
                pytest.fail(
                    'Expected: {surface.surface for surface in surfaces} == {"discovery", "mime"}'
                )
    finally:
        CatalogService.from_crawler(crawler).spider_closed(None, "test-finished")

    if (tmp_path / "catalog.sqlite3").stat().st_mode & 511 != 384:
        pytest.fail(
            'Expected: (tmp_path / "catalog.sqlite3").stat().st_mode & 0o777 == 0o600'
        )


def test_catalog_reprocessing_same_evidence_does_not_duplicate_source_observation(
    tmp_path: Path,
) -> None:
    db_url = f"sqlite:///{tmp_path / 'catalog.sqlite3'}"
    crawler = get_crawler(
        settings_dict={
            "MSGLOOM_DATABASE_URL": db_url,
            "MSGLOOM_SOURCE_ID": "source-1",
            "MSGLOOM_CATALOG_ENABLED": True,
            "MSGLOOM_RAW_EVIDENCE_ENABLED": True,
            "MSGLOOM_RAW_EVIDENCE_DIR": str(tmp_path / "raw"),
        }
    )
    _persist_raw(crawler, "evidence-1", "2026-09-26T01:02:00+00:00")
    pipeline = CatalogPipeline.from_crawler(crawler)
    item = _message()
    asyncio.run(pipeline.process_item(item))
    asyncio.run(pipeline.process_item(item))

    with pipeline.catalog.Session() as session:
        observations = session.scalars(select(MessageObservation)).all()
        if len(observations) != 1:
            pytest.fail("Expected: len(observations) == 1")
    CatalogService.from_crawler(crawler).spider_closed(None, "test-finished")


def test_older_cached_evidence_cannot_overwrite_newer_latest_message_state(
    tmp_path: Path,
) -> None:
    db_url = f"sqlite:///{tmp_path / 'catalog.sqlite3'}"
    crawler = get_crawler(
        settings_dict={
            "MSGLOOM_DATABASE_URL": db_url,
            "MSGLOOM_SOURCE_ID": "source-1",
            "MSGLOOM_CATALOG_ENABLED": True,
            "MSGLOOM_RAW_EVIDENCE_ENABLED": True,
            "MSGLOOM_RAW_EVIDENCE_DIR": str(tmp_path / "raw"),
        }
    )
    _persist_raw(crawler, "new-evidence", "2026-09-26T02:00:00+00:00")
    _persist_raw(crawler, "old-evidence", "2026-09-26T01:00:00+00:00")
    pipeline = CatalogPipeline.from_crawler(crawler)
    newer = _message()
    newer.subject = "Newer subject"
    newer.raw = {**newer.raw, "subject": "Newer subject"}
    newer.observed_at = "2026-09-26T02:00:00+00:00"
    newer.evidence_id = "new-evidence"
    older = _message()
    older.subject = "Old cached subject"
    older.raw = {**older.raw, "subject": "Old cached subject"}
    older.observed_at = "2026-09-26T01:00:00+00:00"
    older.evidence_id = "old-evidence"

    asyncio.run(pipeline.process_item(newer))
    asyncio.run(pipeline.process_item(older))

    with pipeline.catalog.Session() as session:
        message = session.scalar(select(MessageRecord))
        if message is None:
            pytest.fail("Expected: message is not None")
        if message.subject != "Newer subject":
            pytest.fail('Expected: message.subject == "Newer subject"')
        if message.latest_observed_at != "2026-09-26T02:00:00+00:00":
            pytest.fail(
                'Expected: message.latest_observed_at == "2026-09-26T02:00:00+00:00"'
            )
        if message.latest_evidence_id != "new-evidence":
            pytest.fail('Expected: message.latest_evidence_id == "new-evidence"')
        if len(session.scalars(select(MessageObservation)).all()) != 2:
            pytest.fail(
                "Expected: len(session.scalars(select(MessageObservation)).all()) == 2"
            )
    CatalogService.from_crawler(crawler).spider_closed(None, "test-finished")


def test_folder_delta_removal_does_not_imply_global_message_deletion(
    tmp_path: Path,
) -> None:
    db_url = f"sqlite:///{tmp_path / 'catalog.sqlite3'}"
    crawler = get_crawler(
        settings_dict={
            "MSGLOOM_DATABASE_URL": db_url,
            "MSGLOOM_SOURCE_ID": "source-1",
            "MSGLOOM_CATALOG_ENABLED": True,
            "MSGLOOM_RAW_EVIDENCE_ENABLED": True,
            "MSGLOOM_RAW_EVIDENCE_DIR": str(tmp_path / "raw"),
        }
    )
    _persist_raw(crawler, "evidence-1", "2026-09-26T01:02:00+00:00")
    _persist_raw(crawler, "evidence-removal", "2026-09-26T03:00:00+00:00")
    pipeline = CatalogPipeline.from_crawler(crawler)
    asyncio.run(pipeline.process_item(_message()))
    asyncio.run(
        pipeline.process_item(
            OutlookMailRemovalItem(
                message_id="m1",
                folder_id="inbox",
                removed_reason="deleted",
                raw={"id": "m1", "@removed": {"reason": "deleted"}},
                source_response_url="https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages/delta",
                observed_at="2026-09-26T03:00:00+00:00",
                evidence_id="evidence-removal",
                run_id="run-2",
            )
        )
    )

    with pipeline.catalog.Session() as session:
        message = session.scalar(select(MessageRecord))
        if message is None:
            pytest.fail("Expected: message is not None")
        if message.is_removed is not False:
            pytest.fail("Expected: message.is_removed is False")
        if message.parent_folder_id != "inbox":
            pytest.fail('Expected: message.parent_folder_id == "inbox"')
        removals = session.scalars(
            select(MessageObservation).where(
                MessageObservation.kind == "folder_removed"
            )
        ).all()
        if len(removals) != 1:
            pytest.fail("Expected: len(removals) == 1")
        if removals[0].parent_folder_id != "inbox":
            pytest.fail('Expected: removals[0].parent_folder_id == "inbox"')
        if removals[0].removed_reason != "deleted":
            pytest.fail('Expected: removals[0].removed_reason == "deleted"')
    CatalogService.from_crawler(crawler).spider_closed(None, "test-finished")


def test_catalog_pipeline_persists_attachment_metadata(tmp_path: Path) -> None:
    from message_ingest.catalog import AttachmentRecord
    from message_ingest.items import OutlookAttachmentItem

    db_url = f"sqlite:///{tmp_path / 'catalog.sqlite3'}"
    crawler = get_crawler(
        settings_dict={
            "MSGLOOM_DATABASE_URL": db_url,
            "MSGLOOM_SOURCE_ID": "source-1",
            "MSGLOOM_CATALOG_ENABLED": True,
            "MSGLOOM_RAW_EVIDENCE_ENABLED": True,
            "MSGLOOM_RAW_EVIDENCE_DIR": str(tmp_path / "raw"),
        }
    )
    _persist_raw(crawler, "ev-a1", "2026-09-26T03:00:00+00:00")
    pipeline = CatalogPipeline.from_crawler(crawler)
    item = OutlookAttachmentItem(
        message_id="m1",
        attachment_id="a1",
        attachment_type="#microsoft.graph.fileAttachment",
        raw={
            "@odata.type": "#microsoft.graph.fileAttachment",
            "id": "a1",
            "name": "report.pdf",
            "contentType": "application/pdf",
            "size": 1234,
            "isInline": False,
        },
        source_response_url="https://graph.microsoft.com/v1.0/me/messages/m1/attachments",
        observed_at="2026-09-26T03:00:00+00:00",
        evidence_id="ev-a1",
        run_id="run-a",
    )
    asyncio.run(pipeline.process_item(item))

    with pipeline.catalog.Session() as session:
        attachment = session.scalar(select(AttachmentRecord))
        if attachment is None:
            pytest.fail("Expected: attachment is not None")
        if attachment.message_id != "m1":
            pytest.fail('Expected: attachment.message_id == "m1"')
        if attachment.attachment_id != "a1":
            pytest.fail('Expected: attachment.attachment_id == "a1"')
        if attachment.name != "report.pdf":
            pytest.fail('Expected: attachment.name == "report.pdf"')
        if attachment.content_type != "application/pdf":
            pytest.fail('Expected: attachment.content_type == "application/pdf"')
        if attachment.size != 1234:
            pytest.fail("Expected: attachment.size == 1234")
        if attachment.is_inline is not False:
            pytest.fail("Expected: attachment.is_inline is False")
        if attachment.latest_evidence_id != "ev-a1":
            pytest.fail('Expected: attachment.latest_evidence_id == "ev-a1"')
    CatalogService.from_crawler(crawler).spider_closed(None, "test-finished")


@pytest.mark.parametrize(
    ("kind", "surface", "profile", "stat_prefix"),
    [
        ("delta", "discovery", None, "message"),
        ("detail", "detail", FULL_V1, "message_detail"),
    ],
)
def test_message_replay_preserves_kind_surface_profile_and_stats(
    tmp_path: Path,
    kind: str,
    surface: str,
    profile: str | None,
    stat_prefix: str,
) -> None:
    crawler = get_crawler(
        settings_dict={
            "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
            "MSGLOOM_SOURCE_ID": "source-1",
            "MSGLOOM_CATALOG_ENABLED": True,
            "MSGLOOM_RAW_EVIDENCE_ENABLED": True,
            "MSGLOOM_RAW_EVIDENCE_DIR": str(tmp_path / "raw"),
        }
    )
    message = _message()
    message.observation_kind = kind
    item: OutlookMailItem | OutlookMailDetailItem = message
    if kind == "detail":
        item = OutlookMailDetailItem(
            message_id=message.message_id,
            raw=message.raw,
            source_response_url=message.source_response_url,
            observed_at=message.observed_at,
            evidence_id=message.evidence_id,
            run_id=message.run_id,
        )
    _persist_raw(crawler, "evidence-1", message.observed_at)
    pipeline = CatalogPipeline.from_crawler(crawler)
    try:
        asyncio.run(pipeline.process_item(item))
        asyncio.run(pipeline.process_item(item))

        with pipeline.catalog.Session() as session:
            observations = session.scalars(select(MessageObservation)).all()
            if [observation.kind for observation in observations] != [kind]:
                pytest.fail(
                    "Expected: [observation.kind for observation in observations] == [kind]"
                )
            stored = session.scalar(select(MessageSurface))
            if stored is None:
                pytest.fail("Expected: stored is not None")
            if (stored.surface, stored.status, stored.profile_version) != (
                surface,
                "acquired",
                profile,
            ):
                pytest.fail(
                    'Expected: (stored.surface, stored.status, stored.profile_version) == ( surface, "acquired", profile, )'
                )
        if (
            crawler.stats.get_value(
                f"msgloom/catalog/{stat_prefix}_item_processed_count"
            )
            != 2
        ):
            pytest.fail(
                'Expected: crawler.stats.get_value(f"msgloom/catalog/{stat_prefix}_item_processed_count") == 2'
            )
        if (
            crawler.stats.get_value(
                f"msgloom/catalog/{stat_prefix}_observation_created_count"
            )
            != 1
        ):
            pytest.fail(
                'Expected: crawler.stats.get_value(f"msgloom/catalog/{stat_prefix}_observation_created_count") == 1'
            )
        if (
            crawler.stats.get_value(
                f"msgloom/catalog/{stat_prefix}_observation_replay_count"
            )
            != 1
        ):
            pytest.fail(
                'Expected: crawler.stats.get_value(f"msgloom/catalog/{stat_prefix}_observation_replay_count") == 1'
            )
    finally:
        CatalogService.from_crawler(crawler).spider_closed(None, "test-finished")


def test_surface_stats_use_surface_kind_not_provider_identifier(
    tmp_path: Path,
) -> None:
    crawler = get_crawler(
        settings_dict={
            "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
            "MSGLOOM_SOURCE_ID": "source-1",
            "MSGLOOM_CATALOG_ENABLED": True,
            "MSGLOOM_RAW_EVIDENCE_ENABLED": True,
            "MSGLOOM_RAW_EVIDENCE_DIR": str(tmp_path / "raw"),
        }
    )
    _persist_raw(crawler, "surface-evidence", "2026-09-26T04:00:00+00:00")
    pipeline = CatalogPipeline.from_crawler(crawler)
    try:
        asyncio.run(
            pipeline.process_item(
                OutlookMessageSurfaceItem(
                    message_id="m1",
                    surface="attachment_raw:private-attachment-id",
                    status="acquired",
                    observed_at="2026-09-26T04:00:00+00:00",
                    evidence_id="surface-evidence",
                    profile_version=FULL_V1,
                )
            )
        )
        expected = (
            "msgloom/catalog/surface_item_processed_count/attachment_raw/acquired"
        )
        if crawler.stats.get_value(expected) != 1:
            pytest.fail("Expected: crawler.stats.get_value(expected) == 1")
        if any("private-attachment-id" in key for key in crawler.stats.get_stats()):
            pytest.fail("Expected: provider attachment id not present in stats keys")
    finally:
        CatalogService.from_crawler(crawler).spider_closed(None, "test-finished")
