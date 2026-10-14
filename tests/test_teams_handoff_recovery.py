"""Native Teams handoff current-run recovery and superseded-state contracts."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from message_ingest.acquisition.handoff import AcquisitionStream
from message_ingest.catalog.models.acquisition import RawHttpEvidence
from message_ingest.catalog.models.handoff import AcquisitionFact
from message_ingest.catalog.stores.microsoft.teams.message import TeamsMessageStore
from message_ingest.extensions._handoff_traversal import _entries, _teams_complete
from message_ingest.pipelines.microsoft.teams import TeamsPipeline
from tests.teams_persistence_support import (
    OBSERVED,
    SOURCE,
    chat_message,
    open_catalog,
    raw_item,
    record_evidence,
)


def test_cached_initial_inventory_proves_current_logical_run(tmp_path) -> None:
    """The canonical HTTP cache row retains its old capture-run identity."""
    catalog = open_catalog(tmp_path)
    record_evidence(catalog, "cached-inventory", run_id="old-run")
    with catalog.writer_session() as writer:
        row = writer.get(RawHttpEvidence, "cached-inventory")
        if row is None:
            pytest.fail("Fixture lost canonical cached inventory")
        row.purpose = "teams-chat-list"

    class FakeService:
        def __init__(self) -> None:
            self.catalog = catalog

        async def write(self, function, *args, **kwargs):
            return function(*args, **kwargs)

    from typing import cast

    from message_ingest.extensions.catalog import CatalogService

    pipeline = TeamsPipeline(
        service=cast(CatalogService, FakeService()),
        source_id=SOURCE,
        spider_name="microsoft_teams_chat_discover",
    )
    item = raw_item("cached-inventory", source_run="new-run", origin="http_cache")
    item.purpose = "teams-chat-list"
    item.observed_at = OBSERVED
    try:
        asyncio.run(pipeline.process_item(item))
        spider = SimpleNamespace(name="microsoft_teams_chat_discover", run_id="new-run")
        with catalog.writer_session() as writer:
            if not _teams_complete(writer, SOURCE, spider):
                pytest.fail("Cache replay did not establish current-run completion")
            entries = _entries(
                catalog, writer, SOURCE, spider, AcquisitionStream.TEAMS_CHAT
            )
            if entries:
                pytest.fail("Completion proof leaked into the downstream release")
            fact = writer.scalar(
                select(AcquisitionFact).where(AcquisitionFact.run_id == "new-run")
            )
            if fact is None:
                pytest.fail("Completion proof was not durable")
            original = writer.get(RawHttpEvidence, "cached-inventory")
            if original is None or original.run_id != "old-run":
                pytest.fail("Cache replay rewrote canonical evidence ownership")
    finally:
        catalog.close()


def test_direct_deletion_replay_restages_transition(tmp_path) -> None:
    """An unchanged canonical capture must recover both resource and deletion."""
    catalog = open_catalog(tmp_path)
    record_evidence(catalog, "deleted-message", run_id="original-run")
    store = TeamsMessageStore(
        catalog, source_id=SOURCE, spider_name="microsoft_teams_chat_discover"
    )
    try:
        before = chat_message(
            evidence_id="deleted-message",
            run_id="original-run",
            deleted_date_time=OBSERVED,
        )
        if store.persist_message(before) != "created":
            pytest.fail("Initial deleted message was not saved")
        retry = chat_message(
            evidence_id="deleted-message",
            run_id="recovery-run",
            deleted_date_time=OBSERVED,
        )
        if store.persist_message(retry) != "replay":
            pytest.fail("Exact retry did not take the replay path")
        with catalog.writer_session() as writer:
            entries = _entries(
                catalog,
                writer,
                SOURCE,
                SimpleNamespace(run_id="recovery-run"),
                AcquisitionStream.TEAMS_CHAT,
            )
        if {entry.resource_kind for entry in entries} != {
            "teams_message",
            "teams_message_presence",
        }:
            pytest.fail("Replay omitted exact scoped deletion recovery")
    finally:
        catalog.close()


def test_newer_live_message_supersedes_deletion_before_release(tmp_path) -> None:
    """One Teams scope cannot release live resource plus obsolete deletion."""
    catalog = open_catalog(tmp_path)
    record_evidence(catalog, "deleted", observed_at=OBSERVED, run_id="run-same")
    later = "2026-10-04T00:00:10+00:00"
    record_evidence(catalog, "live", observed_at=later, run_id="run-same")
    store = TeamsMessageStore(
        catalog, source_id=SOURCE, spider_name="microsoft_teams_notification_reconcile"
    )
    try:
        store.persist_message(
            chat_message(
                evidence_id="deleted", run_id="run-same", deleted_date_time=OBSERVED
            )
        )
        store.persist_message(
            chat_message(
                evidence_id="live",
                run_id="run-same",
                observed_at=later,
                body="restored",
            )
        )
        with catalog.writer_session() as writer:
            entries = _entries(
                catalog,
                writer,
                SOURCE,
                SimpleNamespace(run_id="run-same"),
                AcquisitionStream.TEAMS_CHAT,
            )
        if [entry.resource_kind for entry in entries] != ["teams_message"]:
            pytest.fail("Reconciliation released a superseded deletion transition")
    finally:
        catalog.close()
