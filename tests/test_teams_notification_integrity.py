"""Notification-specific integrity, item failure, and cancellation tests."""

from __future__ import annotations

import asyncio
import threading
from pathlib import Path
from typing import Any

import pytest
from scrapy import Spider
from scrapy.exceptions import DropItem
from scrapy.utils.test import get_crawler
from sqlalchemy import select

from message_ingest.catalog.models.acquisition import RawHttpEvidence
from message_ingest.catalog.models.microsoft.teams import (
    TeamsCoverageObservation,
    TeamsMessageDeletionObservation,
)
from message_ingest.extensions.catalog import CatalogService
from message_ingest.items.acquisition import RawHttpEvidenceItem
from message_ingest.items.microsoft.teams.coverage import TeamsCoverageItem
from message_ingest.items.microsoft.teams.message import TeamsMessageDeletionItem
from message_ingest.pipelines.microsoft.teams import TeamsPipeline
from microsoft_graph.protocol.teams import TeamsMessageIdentity
from tests.teams_notification_support import (
    GraphFixture,
    change_event,
    chat_subscription,
    crawl_notification,
    encode_envelope,
    open_catalog,
)
from tests.teams_persistence_support import record_evidence

pytest_plugins = ("teams_support",)


class RejectInboundPipeline:
    """Inject a failure before raw persistence to test start-item gating."""

    def __init__(self, mode: str) -> None:
        self.mode = mode

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings.get("NOTIFICATION_TEST_REJECT_MODE", ""))

    def process_item(self, item: Any) -> Any:
        if not isinstance(item, RawHttpEvidenceItem):
            return item
        if item.origin != "inbound-webhook":
            return item
        if self.mode == "error":
            raise RuntimeError("synthetic inbound raw write failure")
        if self.mode == "drop":
            raise DropItem("synthetic inbound raw drop")
        return item


class FailAfterSemanticPipeline:
    """Fail a selected Teams item after the normal Teams persistence stage."""

    def __init__(self, kind: str) -> None:
        self.kind = kind

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings.get("NOTIFICATION_TEST_LATE_KIND", ""))

    def process_item(self, item: Any) -> Any:
        if self.kind == "coverage" and isinstance(item, TeamsCoverageItem):
            raise RuntimeError("synthetic late coverage failure")
        if self.kind == "deletion" and isinstance(item, TeamsMessageDeletionItem):
            raise RuntimeError("synthetic late deletion failure")
        return item


def _pipelines(*, reject: bool = False, late: bool = False) -> dict[str, int]:
    pipelines = {
        "message_ingest.pipelines.evidence.RawEvidencePipeline": 200,
        "message_ingest.acquisition.evidence_link.EvidenceLinkPipeline": 250,
        "message_ingest.pipelines.microsoft.teams.TeamsPipeline": 300,
    }
    if reject:
        pipelines["test_teams_notification_integrity.RejectInboundPipeline"] = 150
    if late:
        pipelines["test_teams_notification_integrity.FailAfterSemanticPipeline"] = 350
    return pipelines


@pytest.mark.parametrize("mode", ["error", "drop"])
def test_raw_item_error_or_drop_cannot_advance_to_semantics_or_graph(
    tmp_path: Path,
    graph_fixture: GraphFixture,
    mode: str,
) -> None:
    result = crawl_notification(
        tmp_path,
        graph_fixture,
        body=encode_envelope([change_event()]),
        subscriptions=[chat_subscription()],
        extra_settings={
            "ITEM_PIPELINES": _pipelines(reject=True),
            "NOTIFICATION_TEST_REJECT_MODE": mode,
        },
    )
    if result.returncode != 0:
        pytest.fail(result.stderr)
    if graph_fixture.seen:
        pytest.fail("Rejected inbound raw item still advanced to Graph")
    reason = "item_error" if mode == "error" else "item_dropped"
    if reason not in result.stderr:
        pytest.fail("Rejected raw item did not use existing integrity signal handling")

    catalog = open_catalog(tmp_path)
    try:
        with catalog.Session() as session:
            if session.scalars(select(RawHttpEvidence)).all():
                pytest.fail(
                    "Pre-persistence raw failure unexpectedly committed evidence"
                )
            if session.scalars(select(TeamsCoverageObservation)).all():
                pytest.fail("Rejected raw item advanced semantic coverage")
    finally:
        catalog.close()


def test_late_coverage_failure_prevents_readback_scheduling(
    tmp_path: Path,
    graph_fixture: GraphFixture,
) -> None:
    result = crawl_notification(
        tmp_path,
        graph_fixture,
        body=encode_envelope([change_event()]),
        subscriptions=[chat_subscription()],
        extra_settings={
            "ITEM_PIPELINES": _pipelines(late=True),
            "NOTIFICATION_TEST_LATE_KIND": "coverage",
        },
    )
    if result.returncode != 0:
        pytest.fail(result.stderr)
    if graph_fixture.seen:
        pytest.fail("Late coverage item error allowed notification readback")
    if "item_error" not in result.stderr:
        pytest.fail("Late coverage error did not mark inherited integrity failure")


def test_deletion_persisted_before_late_item_error_cannot_be_lost(
    tmp_path: Path,
    graph_fixture: GraphFixture,
) -> None:
    result = crawl_notification(
        tmp_path,
        graph_fixture,
        body=encode_envelope([change_event(change_type="deleted")]),
        subscriptions=[chat_subscription()],
        extra_settings={
            "ITEM_PIPELINES": _pipelines(late=True),
            "NOTIFICATION_TEST_LATE_KIND": "deletion",
        },
    )
    if result.returncode != 0:
        pytest.fail(result.stderr)
    if graph_fixture.seen:
        pytest.fail("Late deletion failure scheduled GET before item completion")

    catalog = open_catalog(tmp_path)
    try:
        with catalog.Session() as session:
            rows = session.scalars(select(TeamsMessageDeletionObservation)).all()
        if len(rows) != 1 or rows[0].readback_state != "not-attempted":
            pytest.fail("Late downstream error lost the already committed deletion")
    finally:
        catalog.close()


class _PipelineSpider(Spider):
    name = "teams-notification-cancellation-pipeline-test"


def _pipeline_crawler(tmp_path: Path):
    return get_crawler(
        _PipelineSpider,
        settings_dict={
            "MSGLOOM_CATALOG_ENABLED": True,
            "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'cancel.sqlite3'}",
            "MSGLOOM_SOURCE_ID": "teams-source",
            "LOG_ENABLED": False,
            "TELNETCONSOLE_ENABLED": False,
        },
    )


def test_cancellation_during_deletion_write_drains_and_preserves_declaration(
    tmp_path: Path,
    monkeypatch,
) -> None:
    crawler = _pipeline_crawler(tmp_path)
    pipeline = TeamsPipeline.from_crawler(crawler)
    service = CatalogService.from_crawler(crawler)
    evidence_id = "c" * 32
    observed_at = "2026-10-04T05:00:00+00:00"
    record_evidence(
        service.catalog,
        evidence_id,
        source_id="teams-source",
        observed_at=observed_at,
    )
    deletion = TeamsMessageDeletionItem(
        source_id="teams-source",
        identity=TeamsMessageIdentity.chat("message-a", chat_id="chat-a"),
        deletion_kind="notification",
        declared_deleted_at=None,
        observed_at=observed_at,
        evidence_id=evidence_id,
        run_id="notification-run",
        readback_state="not-attempted",
    )

    started = threading.Event()
    release = threading.Event()
    original = pipeline.message_store.persist_deletion

    def controlled_write(item, **kwargs):
        started.set()
        if not release.wait(timeout=5):
            raise RuntimeError("test failed to release deletion writer")
        return original(item, **kwargs)

    monkeypatch.setattr(
        pipeline.message_store,
        "persist_deletion",
        controlled_write,
    )

    async def scenario() -> None:
        task = asyncio.create_task(pipeline.process_item(deletion))
        if not await asyncio.to_thread(started.wait, 5):
            pytest.fail("Notification deletion writer did not start")
        task.cancel()
        await asyncio.sleep(0)
        if not service.write_lock.locked():
            pytest.fail("Cancellation released notification write lock early")
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task

    try:
        asyncio.run(scenario())
        with service.catalog.Session() as session:
            rows = session.scalars(select(TeamsMessageDeletionObservation)).all()
        if len(rows) != 1:
            pytest.fail("Cancellation returned before deletion declaration drained")
        if rows[0].readback_state != "not-attempted":
            pytest.fail("Cancellation changed immutable deletion readback state")
    finally:
        release.set()
        service.close()


def test_jobdir_is_rejected_before_local_intake_or_graph(
    tmp_path: Path,
    graph_fixture: GraphFixture,
) -> None:
    result = crawl_notification(
        tmp_path,
        graph_fixture,
        body=encode_envelope([change_event()]),
        subscriptions=[chat_subscription()],
        extra_settings={"JOBDIR": str(tmp_path / "jobdir")},
    )
    if result.returncode == 0:
        pytest.fail("Notification spider unexpectedly accepted JOBDIR")
    if graph_fixture.seen:
        pytest.fail("JOBDIR rejection occurred after a Graph request")
    if "Teams discovery does not support JOBDIR yet" not in result.stderr:
        pytest.fail("Notification JOBDIR rejection bypassed the shared Teams base")
