"""Reject mismatched evidence and changed immutable Teams replay facts."""

from dataclasses import replace
from pathlib import Path

import pytest
from sqlalchemy import select

from message_ingest.catalog.models.microsoft.teams import TeamsHostedContentObservation
from message_ingest.catalog.stores.microsoft.teams import (
    TeamsContentStore,
    TeamsCoverageStore,
    TeamsMessageStore,
)
from message_ingest.items.microsoft.teams.content import TeamsHostedContentBytesItem
from message_ingest.items.microsoft.teams.coverage import TeamsCoverageItem
from message_ingest.items.microsoft.teams.message import (
    TeamsMessageDeletionItem,
    TeamsMessageTrigger,
)
from tests.teams_persistence_support import (
    OBSERVED,
    RUN,
    SOURCE,
    chat_message,
    open_catalog,
    record_evidence,
)


@pytest.mark.parametrize(
    "field,value", [("content_sha256", "0" * 64), ("content_bytes", 99)]
)
def test_hosted_bytes_must_match_committed_response(tmp_path: Path, field, value):
    catalog = open_catalog(tmp_path)
    try:
        record_evidence(catalog, "message")
        record_evidence(catalog, "bytes", body=b"PNG")
        message = chat_message(evidence_id="message")
        TeamsMessageStore(catalog, source_id=SOURCE).persist_message(message)
        item = TeamsHostedContentBytesItem.from_bytes(
            body=b"PNG",
            source_id=SOURCE,
            message_identity=message.identity,
            hosted_content_id="image",
            trigger=TeamsMessageTrigger.from_message(message),
            content_type="image/png",
            observed_at=OBSERVED,
            evidence_id="bytes",
            run_id=RUN,
        )
        store = TeamsContentStore(catalog, source_id=SOURCE)
        with pytest.raises(ValueError, match="response bytes"):
            store.persist_hosted_bytes(replace(item, **{field: value}))
        with catalog.Session() as session:
            if session.scalar(select(TeamsHostedContentObservation)) is not None:
                pytest.fail("Mismatched byte evidence must not create an observation")
        if store.persist_hosted_bytes(item) != "created":
            pytest.fail("Matching committed byte evidence should persist")
    finally:
        catalog.close()


@pytest.mark.parametrize(
    "field,value",
    [
        ("history_incomplete", True),
        ("visible_scope", {"chat": "other"}),
        ("retention_limitations", ["limited"]),
        ("subscription_id", "changed"),
        ("subscription_valid_from", OBSERVED),
        ("subscription_valid_until", OBSERVED),
        ("gap_kind", "delivery"),
    ],
)
def test_coverage_replay_cannot_change_immutable_facts(tmp_path: Path, field, value):
    catalog = open_catalog(tmp_path)
    try:
        record_evidence(catalog, "coverage")
        item = TeamsCoverageItem(
            source_id=SOURCE,
            scope_kind="chat",
            scope=("chat-a",),
            fact_kind="inventory",
            status="visible",
            history_incomplete=False,
            observed_at=OBSERVED,
            evidence_id="coverage",
            run_id=RUN,
        )
        store = TeamsCoverageStore(catalog, source_id=SOURCE)
        store.persist(item)
        with pytest.raises(ValueError, match="immutable"):
            store.persist(replace(item, **{field: value}))
        if store.persist(replace(item, run_id="replay-run")) != "replay":
            pytest.fail("A new semantic run must still permit exact evidence replay")
    finally:
        catalog.close()


@pytest.mark.parametrize(
    "field,value",
    [
        ("declared_deleted_at", OBSERVED),
        ("readback_state", "failed"),
    ],
)
def test_deletion_replay_cannot_change_immutable_facts(tmp_path: Path, field, value):
    catalog = open_catalog(tmp_path)
    try:
        record_evidence(catalog, "deletion")
        item = TeamsMessageDeletionItem(
            source_id=SOURCE,
            identity=chat_message().identity,
            deletion_kind="notification",
            declared_deleted_at=None,
            observed_at=OBSERVED,
            evidence_id="deletion",
            run_id=RUN,
            readback_state="not-attempted",
        )
        store = TeamsMessageStore(catalog, source_id=SOURCE)
        store.persist_deletion(item)
        with pytest.raises(ValueError, match="immutable"):
            store.persist_deletion(replace(item, **{field: value}))
    finally:
        catalog.close()


@pytest.mark.parametrize("incoming_at", [OBSERVED, "2026-10-03T23:59:00+00:00"])
def test_stale_or_tied_gap_is_sticky_and_deletion_does_not_regress(
    tmp_path, incoming_at
):
    from message_ingest.catalog.models.microsoft.teams import (
        TeamsCoverageCurrent,
        TeamsMessageCurrent,
    )

    catalog = open_catalog(tmp_path)
    try:
        record_evidence(catalog, "current")
        record_evidence(catalog, "earlier", observed_at=incoming_at)
        message = chat_message(evidence_id="current")
        messages = TeamsMessageStore(catalog, source_id=SOURCE)
        messages.persist_message(message)
        messages.persist_deletion(
            TeamsMessageDeletionItem(
                source_id=SOURCE,
                identity=message.identity,
                deletion_kind="notification",
                declared_deleted_at=None,
                observed_at=incoming_at,
                evidence_id="earlier",
                run_id=RUN,
                readback_state="not-attempted",
            )
        )
        coverage = TeamsCoverageStore(catalog, source_id=SOURCE)
        current = TeamsCoverageItem(
            source_id=SOURCE,
            scope_kind="chat",
            scope=("chat-a",),
            fact_kind="reconciliation",
            status="visible",
            history_incomplete=False,
            observed_at=OBSERVED,
            evidence_id="current",
            run_id=RUN,
        )
        coverage.persist(current)
        coverage.persist(
            replace(
                current,
                fact_kind="gap",
                history_incomplete=True,
                observed_at=incoming_at,
                evidence_id="earlier",
            )
        )
        with catalog.Session() as session:
            message_row = session.scalar(select(TeamsMessageCurrent))
            coverage_row = session.scalar(select(TeamsCoverageCurrent))
            if message_row is None or message_row.is_deleted:
                pytest.fail(
                    "Stale or tied deletion must not regress the latest message"
                )
            if coverage_row is None or not coverage_row.history_incomplete:
                pytest.fail("Even stale or tied gaps must preserve history uncertainty")
            if coverage_row.latest_evidence_id != "current":
                pytest.fail("A stale or tied gap must not replace the latest capture")
    finally:
        catalog.close()
