"""Teams pipeline evidence provenance, dispatch, and failure tests."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from scrapy import Spider
from scrapy.utils.test import get_crawler
from sqlalchemy import select

from message_ingest.acquisition.evidence_link import EvidenceLinkPipeline
from message_ingest.catalog.models.microsoft.teams import TeamsMessageObservation
from message_ingest.extensions.catalog import CatalogService
from message_ingest.pipelines.evidence import RawEvidencePipeline
from message_ingest.pipelines.microsoft.teams import TeamsPipeline
from tests.teams_persistence_support import (
    RUN,
    SOURCE,
    chat_message,
    raw_item,
    record_evidence,
)


class _PipelineSpider(Spider):
    """Minimal owner for direct pipeline construction tests."""

    name = "teams-persistence-pipeline-test"


def _crawler(tmp_path: Path):
    """Build a crawler with isolated catalog/raw paths."""
    return get_crawler(
        _PipelineSpider,
        settings_dict={
            "MSGLOOM_CATALOG_ENABLED": True,
            "MSGLOOM_RAW_EVIDENCE_ENABLED": True,
            "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
            "MSGLOOM_RAW_EVIDENCE_DIR": str(tmp_path / "raw"),
            "MSGLOOM_SOURCE_ID": SOURCE,
            "CONCURRENT_ITEMS": 1,
            "LOG_ENABLED": False,
            "TELNETCONSOLE_ENABLED": False,
        },
    )


def test_missing_or_wrong_source_evidence_fails_before_semantic_write(
    tmp_path: Path,
) -> None:
    crawler = _crawler(tmp_path)
    pipeline = TeamsPipeline.from_crawler(crawler)
    service = CatalogService.from_crawler(crawler)
    try:
        missing = chat_message(evidence_id="missing")
        with pytest.raises(ValueError, match="committed evidence"):
            asyncio.run(pipeline.process_item(missing))

        record_evidence(
            service.catalog,
            "wrong-source",
            source_id="other-teams-source",
        )
        wrong = chat_message(evidence_id="wrong-source")
        with pytest.raises(ValueError, match="source"):
            asyncio.run(pipeline.process_item(wrong))

        with service.catalog.Session() as session:
            rows = session.scalars(select(TeamsMessageObservation)).all()
            if rows:
                pytest.fail("Invalid evidence must fail before semantic storage")
    finally:
        service.close()


def test_cache_alias_accepts_earlier_evidence_run_and_keeps_both_provenances(
    tmp_path: Path,
) -> None:
    crawler = _crawler(tmp_path)
    raw = RawEvidencePipeline.from_crawler(crawler)
    linker = EvidenceLinkPipeline.from_crawler(crawler)
    teams = TeamsPipeline.from_crawler(crawler)
    service = CatalogService.from_crawler(crawler)
    old_at = "2026-10-04T05:00:00+00:00"
    replay_at = "2026-10-04T06:00:00+00:00"
    body = b'{"same":"provider-response"}'
    try:
        original = raw_item(
            "canonical-old",
            source_run="run-old",
            observed_at=old_at,
            body=body,
        )
        replay = raw_item(
            "provisional-current",
            source_run=RUN,
            observed_at=replay_at,
            origin="http_cache",
            body=body,
        )
        asyncio.run(raw.process_item(original))
        asyncio.run(raw.process_item(replay))
        if replay.evidence_id != "canonical-old":
            pytest.fail("Expected HTTP cache response to alias canonical evidence")
        if replay.observed_at != old_at:
            pytest.fail("Cache alias must restore canonical capture time")

        item = chat_message(
            evidence_id="provisional-current",
            observed_at=replay_at,
            run_id=RUN,
            body="semantic parsed from cached response",
        )
        asyncio.run(linker.process_item(item))
        if item.evidence_id != "canonical-old" or item.observed_at != old_at:
            pytest.fail("EvidenceLinkPipeline must canonicalize Teams provenance")
        asyncio.run(teams.process_item(item))

        with service.catalog.Session() as session:
            row = session.scalar(select(TeamsMessageObservation))
            if row is None:
                pytest.fail(
                    "Canonical cache replay should persist semantic observation"
                )
            if row.run_id != RUN:
                pytest.fail(
                    "Semantic observation must retain current crawl run provenance"
                )
            if row.evidence_run_id != "run-old":
                pytest.fail("Canonical evidence must retain its earlier capture run")
            if row.observed_at != old_at:
                pytest.fail("Semantic time must use canonical evidence capture time")
    finally:
        service.close()


def test_pipeline_write_failure_propagates_and_emits_no_success_stat(
    tmp_path: Path,
    monkeypatch,
) -> None:
    crawler = _crawler(tmp_path)
    pipeline = TeamsPipeline.from_crawler(crawler)
    service = CatalogService.from_crawler(crawler)
    item = chat_message(evidence_id="write-error")
    record_evidence(service.catalog, "write-error")

    def fail_write(_item):
        raise RuntimeError("forced Teams write failure")

    monkeypatch.setattr(pipeline.message_store, "persist_message", fail_write)
    try:
        before = crawler.stats.get_stats().copy()
        with pytest.raises(RuntimeError, match="forced Teams write failure"):
            asyncio.run(pipeline.process_item(item))
        after = crawler.stats.get_stats()
        if after != before:
            pytest.fail("Failed Teams writes must not publish success stats")
    finally:
        service.close()


def test_pipeline_stats_are_bounded_allowlisted_keys(tmp_path: Path) -> None:
    crawler = _crawler(tmp_path)
    pipeline = TeamsPipeline.from_crawler(crawler)
    service = CatalogService.from_crawler(crawler)
    opaque_id = "provider-id-must-not-be-stat-key"
    record_evidence(service.catalog, "bounded-stat")
    item = chat_message(
        message_id=opaque_id,
        evidence_id="bounded-stat",
    )
    try:
        asyncio.run(pipeline.process_item(item))
        keys = tuple(crawler.stats.get_stats())
        catalog_keys = [key for key in keys if key.startswith("msgloom/catalog/teams/")]
        if not catalog_keys:
            pytest.fail("Successful Teams write should publish bounded catalog stats")
        if any(opaque_id in key for key in catalog_keys):
            pytest.fail("Provider IDs must never appear in Teams stat keys")
        allowed = {
            "msgloom/catalog/teams/message_processed_count",
            "msgloom/catalog/teams/message_created_count",
        }
        unexpected = set(catalog_keys) - allowed
        if unexpected:
            pytest.fail(
                f"Teams pipeline emitted unexpected dynamic stats: {unexpected!r}"
            )
    finally:
        service.close()


def test_hosted_trigger_canonicalizes_before_message_linker_mutation(tmp_path):
    """A scheduled trigger must survive canonicalization of its message item."""
    from message_ingest.catalog.models.microsoft.teams import (
        TeamsHostedContentObservation,
    )
    from message_ingest.items.microsoft.teams.content import TeamsHostedContentBytesItem
    from message_ingest.items.microsoft.teams.message import TeamsMessageTrigger

    crawler = _crawler(tmp_path)
    raw = RawEvidencePipeline.from_crawler(crawler)
    linker = EvidenceLinkPipeline.from_crawler(crawler)
    teams = TeamsPipeline.from_crawler(crawler)
    service = CatalogService.from_crawler(crawler)
    old_at = "2026-10-04T05:00:00+00:00"
    new_at = "2026-10-04T06:00:00+00:00"
    message = chat_message(evidence_id="alias", observed_at=new_at)
    trigger = TeamsMessageTrigger.from_message(message)

    async def scenario():
        await raw.process_item(raw_item("canonical", observed_at=old_at))
        await raw.process_item(
            raw_item("alias", observed_at=new_at, origin="http_cache")
        )
        await linker.process_item(message)
        await teams.process_item(message)
        await raw.process_item(raw_item("binary", observed_at=new_at, body=b"PNG"))
        item = TeamsHostedContentBytesItem.from_bytes(
            body=b"PNG",
            source_id=SOURCE,
            message_identity=message.identity,
            hosted_content_id="image",
            trigger=trigger,
            content_type="image/png",
            observed_at=new_at,
            evidence_id="binary",
            run_id=RUN,
        )
        await linker.process_item(item)
        await teams.process_item(item)

    try:
        asyncio.run(scenario())
        with service.catalog.Session() as session:
            row = session.scalar(select(TeamsHostedContentObservation))
            if row is None or row.trigger_evidence_id != "canonical":
                pytest.fail(
                    "Hosted trigger must resolve the provisional evidence alias"
                )
            if row.trigger_observed_at != old_at or row.evidence_id != "binary":
                pytest.fail(
                    "Trigger and byte response must keep separate capture facts"
                )
    finally:
        service.close()
