"""Native Teams handoff current-run recovery and superseded-state contracts."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from message_ingest.acquisition.handoff import AcquisitionStream, FactSpec
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
        kinds = {entry.resource_kind for entry in entries}
        if kinds != {"teams_message", "teams_message_presence"}:
            pytest.fail("Reconciliation lost live resource or restored presence")
        accepted = []
        with catalog.Session() as session:
            for entry in entries:
                for fact_id, _role in entry.facts:
                    payload = session.scalar(
                        select(AcquisitionFact.payload).where(
                            AcquisitionFact.fact_id == fact_id
                        )
                    )
                    if payload is None:
                        pytest.fail("Released fact is missing from the ledger")
                    accepted.append(FactSpec.from_json(payload))
        if {
            fact.transition_reason
            for fact in accepted
            if fact.resource_kind == "teams_message_presence"
        } != {"observed_present"}:
            pytest.fail("Reconciliation leaked superseded deletion")
    finally:
        catalog.close()


def test_restoration_replay_recovers_unpublished_presence(tmp_path) -> None:
    """A failed restoration run must not strand consumers in deleted state."""
    catalog = open_catalog(tmp_path)
    store = TeamsMessageStore(
        catalog, source_id=SOURCE, spider_name="microsoft_teams_notification_reconcile"
    )
    from tests.test_teams_handoff_freshness import _deletion

    at0 = "2026-10-04T00:00:00+00:00"
    at1 = "2026-10-04T00:00:01+00:00"
    at2 = "2026-10-04T00:00:02+00:00"
    try:
        for evidence_id, observed, run in (
            ("first-live", at0, "first-run"),
            ("first-delete", at1, "delete-run"),
            ("restoration", at2, "failed-restore"),
        ):
            record_evidence(catalog, evidence_id, observed_at=observed, run_id=run)
        store.persist_message(
            chat_message(evidence_id="first-live", observed_at=at0, run_id="first-run")
        )
        store.persist_deletion(_deletion("first-delete", at1, "delete-run"))
        store.persist_message(
            chat_message(
                evidence_id="restoration",
                observed_at=at2,
                run_id="failed-restore",
                body="restored",
            )
        )
        # The restoration run exits before any release. The exact HTTP/evidence
        # capture is replayed under a fresh logical run ID.
        if (
            store.persist_message(
                chat_message(
                    evidence_id="restoration",
                    observed_at=at2,
                    run_id="retry-restore",
                    body="restored",
                )
            )
            != "replay"
        ):
            pytest.fail("Fixture failed to replay a canonical restoration")
        with catalog.writer_session() as writer:
            entries = _entries(
                catalog,
                writer,
                SOURCE,
                SimpleNamespace(run_id="retry-restore"),
                AcquisitionStream.TEAMS_CHAT,
            )
        if {entry.resource_kind for entry in entries} != {
            "teams_message",
            "teams_message_presence",
        }:
            pytest.fail("Restoration replay omitted unpublished positive presence")
    finally:
        catalog.close()


def test_new_live_capture_recovers_pending_restoration_once(tmp_path) -> None:
    """A newer live response can publish an earlier unpublished restoration."""
    from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
    from message_ingest.extensions._handoff_traversal import release_teams_notifications
    from tests.test_teams_handoff_freshness import _deletion

    catalog = open_catalog(tmp_path)
    store = TeamsMessageStore(
        catalog, source_id=SOURCE, spider_name="microsoft_teams_notification_reconcile"
    )
    times = [f"2026-10-04T00:00:0{i}+00:00" for i in range(5)]
    try:
        for i, name in enumerate(
            ("initial", "deleted", "restored", "updated", "updated-again")
        ):
            record_evidence(catalog, name, observed_at=times[i], run_id=f"run-{i}")
        store.persist_message(
            chat_message(evidence_id="initial", observed_at=times[0], run_id="run-0")
        )
        store.persist_deletion(_deletion("deleted", times[1], "run-1"))
        with catalog.writer_session() as writer:
            release_teams_notifications(
                catalog, writer, SOURCE, SimpleNamespace(run_id="run-1")
            )
        store.persist_message(
            chat_message(
                evidence_id="restored",
                observed_at=times[2],
                run_id="run-2",
                body="now live",
            )
        )
        # The restoration transaction succeeded; the release did not.
        store.persist_message(
            chat_message(
                evidence_id="updated",
                observed_at=times[3],
                run_id="run-3",
                body="edited live content",
            )
        )
        with catalog.writer_session() as writer:
            entries = _entries(
                catalog,
                writer,
                SOURCE,
                SimpleNamespace(run_id="run-3"),
                AcquisitionStream.TEAMS_CHAT,
            )
            kinds = {entry.resource_kind for entry in entries}
            if kinds != {"teams_message", "teams_message_presence"}:
                pytest.fail("New live capture lost pending restoration")
            release_teams_notifications(
                catalog, writer, SOURCE, SimpleNamespace(run_id="run-3")
            )
        store.persist_message(
            chat_message(
                evidence_id="updated-again",
                observed_at=times[4],
                run_id="run-4",
                body="another edit",
            )
        )
        with catalog.writer_session() as writer:
            release_teams_notifications(
                catalog, writer, SOURCE, SimpleNamespace(run_id="run-4")
            )
        handoff = AcquisitionHandoffStore(catalog)
        releases = handoff.list_release_entries(
            SOURCE, AcquisitionStream.TEAMS_CHAT, limit=100
        )
        present = [
            fact.transition_reason
            for row in releases
            for fact in handoff.load_release_facts(row["release_entry_seq"])
            if fact.resource_kind == "teams_message_presence"
        ]
        if present != ["provider_deleted", "observed_present"]:
            pytest.fail("Restoration was missed or emitted more than once")
    finally:
        catalog.close()
