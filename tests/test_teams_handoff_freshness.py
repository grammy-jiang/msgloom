"""Chronological Teams release contracts for cross-run restoration and stale data."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import select

from message_ingest.acquisition.handoff import AcquisitionStream, FactSpec
from message_ingest.catalog.models.handoff import AcquisitionFact
from message_ingest.catalog.models.microsoft.teams import (
    TeamsHostedContentObservation,
)
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from message_ingest.catalog.stores.microsoft.teams._handoff_hosted import stage_hosted
from message_ingest.catalog.stores.microsoft.teams.message import TeamsMessageStore
from message_ingest.extensions._handoff_traversal import (
    _entries,
    release_teams_notifications,
)
from message_ingest.items.microsoft.teams.message import TeamsMessageDeletionItem
from tests.teams_persistence_support import (
    SOURCE,
    chat_message,
    open_catalog,
    record_evidence,
)

TIME0 = "2026-10-04T00:00:00+00:00"
TIME1 = "2026-10-04T00:00:01+00:00"
TIME2 = "2026-10-04T00:00:02+00:00"
TIME3 = "2026-10-04T00:00:03+00:00"


def _deletion(evidence_id: str, time: str, run: str) -> TeamsMessageDeletionItem:
    return TeamsMessageDeletionItem(
        source_id=SOURCE,
        identity=chat_message().identity,
        deletion_kind="notification",
        declared_deleted_at=None,
        observed_at=time,
        evidence_id=evidence_id,
        run_id=run,
        readback_state="not-attempted",
    )


def _published_presence(catalog) -> list[str | None]:
    handoff = AcquisitionHandoffStore(catalog)
    rows = handoff.list_release_entries(SOURCE, AcquisitionStream.TEAMS_CHAT, limit=100)
    return [
        fact.transition_reason
        for entry in rows
        for fact in handoff.load_release_facts(entry["release_entry_seq"])
        if fact.resource_kind == "teams_message_presence"
    ]


def test_restore_then_second_deletion_stays_publishable(tmp_path) -> None:
    """live → deleted → restored → deleted must produce two distinct deletions."""
    catalog = open_catalog(tmp_path)
    store = TeamsMessageStore(
        catalog, source_id=SOURCE, spider_name="microsoft_teams_notification_reconcile"
    )
    steps = (
        ("live-first", TIME0, "run-live1"),
        ("delete-first", TIME1, "run-delete1"),
        ("live-second", TIME2, "run-live2"),
        ("delete-second", TIME3, "run-delete2"),
    )
    try:
        for evidence_id, at, run in steps:
            record_evidence(catalog, evidence_id, observed_at=at, run_id=run)
            if evidence_id.startswith("live"):
                value = chat_message(
                    evidence_id=evidence_id,
                    observed_at=at,
                    run_id=run,
                    body=evidence_id,
                )
                outcome = store.persist_message(value)
            else:
                outcome = store.persist_deletion(_deletion(evidence_id, at, run))
            if outcome not in {"created", "advanced"}:
                pytest.fail("Fixture could not advance provider state")
            with catalog.writer_session() as writer:
                release_teams_notifications(
                    catalog, writer, SOURCE, SimpleNamespace(run_id=run)
                )
        transitions = _published_presence(catalog)
        if transitions != ["provider_deleted", "observed_present", "provider_deleted"]:
            pytest.fail(
                f"Restoration/re-deletion did not produce all state changes: {transitions}"
            )
    finally:
        catalog.close()


def test_concurrent_deletion_supersedes_old_live_before_release(tmp_path) -> None:
    """A delayed discovery completion must not publish a deleted message as live."""
    catalog = open_catalog(tmp_path)
    store = TeamsMessageStore(
        catalog, source_id=SOURCE, spider_name="microsoft_teams_notification_reconcile"
    )
    try:
        record_evidence(catalog, "live-before", observed_at=TIME0, run_id="run-old")
        record_evidence(catalog, "deletion-after", observed_at=TIME1, run_id="run-new")
        store.persist_message(
            chat_message(evidence_id="live-before", observed_at=TIME0, run_id="run-old")
        )
        store.persist_deletion(_deletion("deletion-after", TIME1, "run-new"))
        with catalog.writer_session() as writer:
            entries = _entries(
                catalog,
                writer,
                SOURCE,
                SimpleNamespace(run_id="run-old"),
                AcquisitionStream.TEAMS_CHAT,
            )
        if entries:
            pytest.fail("A delayed old live crawl released a superseded message")
    finally:
        catalog.close()


def test_out_of_order_hosted_observation_cannot_replace_newer_state(tmp_path) -> None:
    """Persist order must not override hosted-content observation chronology."""
    catalog = open_catalog(tmp_path)
    handoff = AcquisitionHandoffStore(catalog)
    trigger = SimpleNamespace(scope_key=["message", "chat", "chat-a", "opaque-message"])
    try:
        for evidence_id, at, run in (
            ("hosted-new", TIME2, "run-new"),
            ("hosted-old", TIME1, "run-old"),
        ):
            record_evidence(catalog, evidence_id, observed_at=at, run_id=run)
            with catalog.writer_session() as writer:
                row = TeamsHostedContentObservation(
                    source_id=SOURCE,
                    trigger_scope_sha256="a" * 64,
                    trigger_evidence_id="message-trigger",
                    trigger_observed_at=TIME0,
                    hosted_content_id="hosted-1",
                    observation_kind="metadata",
                    provider_version_bound=False,
                    content_type="text/plain",
                    content_sha256=None,
                    content_bytes=None,
                    failure_kind=None,
                    status_code=None,
                    raw={"id": "hosted-1", "capture": evidence_id},
                    details={},
                    observed_at=at,
                    evidence_id=evidence_id,
                    run_id=run,
                    evidence_run_id=run,
                )
                writer.add(row)
                writer.flush()
                stage_hosted(
                    writer,
                    handoff,
                    spider_name="microsoft_teams_chat_discover",
                    row=row,
                    trigger=trigger,
                    run_id=run,
                    outcome="created",
                )
        with catalog.writer_session() as writer:
            earlier = _entries(
                catalog,
                writer,
                SOURCE,
                SimpleNamespace(run_id="run-old"),
                AcquisitionStream.TEAMS_CHAT,
            )
            newer = _entries(
                catalog,
                writer,
                SOURCE,
                SimpleNamespace(run_id="run-new"),
                AcquisitionStream.TEAMS_CHAT,
            )
        if earlier or len(newer) != 1:
            pytest.fail("Hosted freshness followed write order, not capture time")
        with catalog.Session() as session:
            rows = session.scalars(
                select(AcquisitionFact.payload).where(
                    AcquisitionFact.source_id == SOURCE,
                    AcquisitionFact.stream == AcquisitionStream.TEAMS_CHAT,
                )
            ).all()
        facts = [FactSpec.from_json(raw) for raw in rows]
        stale = [f for f in facts if f.run_id == "run-old"]
        if len(stale) != 1 or stale[0].storage_relation != "stale":
            pytest.fail("Older hosted observation was not retained as stale history")
    finally:
        catalog.close()


def test_hosted_same_state_revalidation_keeps_newer_capture_highwater(tmp_path) -> None:
    """A(t1), A(t3 equivalent), B(t2 late) cannot publish stale B."""
    catalog = open_catalog(tmp_path)
    handoff = AcquisitionHandoffStore(catalog)
    trigger = SimpleNamespace(scope_key=["message", "chat", "chat-a", "opaque-message"])
    try:
        for evidence_id, at, run, variant in (
            ("hosted-A1", TIME1, "run-A1", "A"),
            ("hosted-A3", TIME3, "run-A3", "A"),
            ("hosted-B2", TIME2, "run-B2", "B"),
        ):
            record_evidence(catalog, evidence_id, observed_at=at, run_id=run)
            with catalog.writer_session() as writer:
                row = TeamsHostedContentObservation(
                    source_id=SOURCE,
                    trigger_scope_sha256="a" * 64,
                    trigger_evidence_id="message-trigger",
                    trigger_observed_at=TIME0,
                    hosted_content_id="hosted-1",
                    observation_kind="metadata",
                    provider_version_bound=False,
                    content_type="text/plain",
                    content_sha256=None,
                    content_bytes=None,
                    failure_kind=None,
                    status_code=None,
                    raw={"id": "hosted-1", "content": variant},
                    details={},
                    observed_at=at,
                    evidence_id=evidence_id,
                    run_id=run,
                    evidence_run_id=run,
                )
                writer.add(row)
                writer.flush()
                stage_hosted(
                    writer,
                    handoff,
                    spider_name="microsoft_teams_chat_discover",
                    row=row,
                    trigger=trigger,
                    run_id=run,
                    outcome="created",
                )
        with catalog.writer_session() as writer:
            previous = _entries(
                catalog,
                writer,
                SOURCE,
                SimpleNamespace(run_id="run-A3"),
                AcquisitionStream.TEAMS_CHAT,
            )
            delayed = _entries(
                catalog,
                writer,
                SOURCE,
                SimpleNamespace(run_id="run-B2"),
                AcquisitionStream.TEAMS_CHAT,
            )
        if delayed or len(previous) != 1:
            pytest.fail("Late hosted B(t2) wrongly replaced newer A(t3)")
        with catalog.Session() as session:
            records = session.scalars(
                select(AcquisitionFact.payload).where(
                    AcquisitionFact.source_id == SOURCE,
                    AcquisitionFact.stream == AcquisitionStream.TEAMS_CHAT,
                )
            ).all()
        facts = [FactSpec.from_json(raw) for raw in records]
        newest = [fact for fact in facts if fact.run_id == "run-A3"]
        older = [fact for fact in facts if fact.run_id == "run-B2"]
        if (
            len(newest) != 1
            or newest[0].storage_relation != "current_equivalent"
            or len(older) != 1
            or older[0].storage_relation != "stale"
        ):
            pytest.fail("Hosted accepted-capture highwater was not retained")
    finally:
        catalog.close()
