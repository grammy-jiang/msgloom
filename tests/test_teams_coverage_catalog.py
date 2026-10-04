"""Teams explicit deletion and durable coverage-uncertainty tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from message_ingest.catalog.models.microsoft.teams import (
    TeamsCoverageCurrent,
    TeamsCoverageObservation,
    TeamsMessageCurrent,
    TeamsMessageDeletionObservation,
    TeamsMessageObservation,
)
from message_ingest.catalog.stores.microsoft.teams.coverage import TeamsCoverageStore
from message_ingest.catalog.stores.microsoft.teams.message import TeamsMessageStore
from message_ingest.items.microsoft.teams.coverage import TeamsCoverageItem
from message_ingest.items.microsoft.teams.message import TeamsMessageDeletionItem
from microsoft_graph.protocol.teams import TeamsMessageIdentity
from tests.teams_persistence_support import (
    RUN,
    SOURCE,
    chat_message,
    open_catalog,
    record_evidence,
)


def test_direct_deletion_keeps_prior_message_body_and_evidence(tmp_path: Path) -> None:
    catalog = open_catalog(tmp_path)
    store = TeamsMessageStore(catalog, source_id=SOURCE)
    try:
        first_at = "2026-10-04T01:00:00+00:00"
        deleted_at = "2026-10-04T01:01:00+00:00"
        record_evidence(catalog, "body-evidence", observed_at=first_at)
        record_evidence(catalog, "delete-evidence", observed_at=deleted_at)

        store.persist_message(
            chat_message(
                evidence_id="body-evidence",
                observed_at=first_at,
                body="content before deletion",
                etag="etag-before",
            )
        )
        store.persist_message(
            chat_message(
                evidence_id="delete-evidence",
                observed_at=deleted_at,
                body="",
                etag="etag-deleted",
                deleted_date_time=deleted_at,
            )
        )

        with catalog.Session() as session:
            messages = session.scalars(
                select(TeamsMessageObservation).order_by(
                    TeamsMessageObservation.observation_id
                )
            ).all()
            if len(messages) != 2:
                pytest.fail("Direct deletion must not erase prior message observations")
            if messages[0].raw["body"]["content"] != "content before deletion":
                pytest.fail("Old observed body must remain after explicit deletion")
            deletions = session.scalars(select(TeamsMessageDeletionObservation)).all()
            if len(deletions) != 1:
                pytest.fail("deletedDateTime must produce one explicit deletion fact")
            if deletions[0].evidence_id != "delete-evidence":
                pytest.fail("Direct deletion fact must retain its response evidence")
            current = session.scalar(select(TeamsMessageCurrent))
            if current is None or not current.is_deleted:
                pytest.fail("Direct provider deletion must update current projection")
    finally:
        catalog.close()


def test_notification_deletion_failed_readback_preserves_old_content(
    tmp_path: Path,
) -> None:
    catalog = open_catalog(tmp_path)
    store = TeamsMessageStore(catalog, source_id=SOURCE)
    try:
        message_at = "2026-10-04T02:00:00+00:00"
        notification_at = "2026-10-04T02:01:00+00:00"
        failed_read_at = "2026-10-04T02:02:00+00:00"
        record_evidence(catalog, "message-before", observed_at=message_at)
        record_evidence(
            catalog,
            "notification-delete",
            observed_at=notification_at,
            body=b'{"changeType":"deleted"}',
        )
        record_evidence(
            catalog,
            "readback-410",
            observed_at=failed_read_at,
            body=b'{"error":{"code":"Gone"}}',
        )
        message = chat_message(
            evidence_id="message-before",
            observed_at=message_at,
            body="must survive notification deletion",
        )
        store.persist_message(message)

        deletion = TeamsMessageDeletionItem(
            source_id=SOURCE,
            identity=message.identity,
            deletion_kind="notification",
            declared_deleted_at=None,
            observed_at=notification_at,
            evidence_id="notification-delete",
            run_id=RUN,
            readback_state="failed",
            readback_evidence_id="readback-410",
            readback_observed_at=failed_read_at,
        )
        store.persist_deletion(deletion)

        with catalog.Session() as session:
            current = session.scalar(select(TeamsMessageCurrent))
            if current is None or not current.is_deleted:
                pytest.fail("Persisted deletion notification must change current state")
            if current.raw is None:
                pytest.fail("Notification deletion must preserve prior current body")
            if current.raw["body"]["content"] != ("must survive notification deletion"):
                pytest.fail("Failed readback must not replace the last observed body")
            deletion_row = session.scalar(select(TeamsMessageDeletionObservation))
            if deletion_row is None:
                pytest.fail("Notification deletion fact was not persisted")
            if deletion_row.evidence_id != "notification-delete":
                pytest.fail(
                    "Notification evidence must precede and back deletion state"
                )
            if deletion_row.readback_evidence_id != "readback-410":
                pytest.fail("Failed readback evidence must be retained independently")

        # Empty inventory has no semantic deletion item. Re-read current state
        # to prove no absence inference was needed or performed.
        with catalog.Session() as session:
            rows = session.scalars(select(TeamsMessageDeletionObservation)).all()
            if len(rows) != 1:
                pytest.fail("List absence must not fabricate a deletion observation")
    finally:
        catalog.close()


def test_gap_history_remains_incomplete_after_current_state_reconciliation(
    tmp_path: Path,
) -> None:
    catalog = open_catalog(tmp_path)
    store = TeamsCoverageStore(catalog, source_id=SOURCE)
    try:
        gap_at = "2026-10-04T03:00:00+00:00"
        reconcile_at = "2026-10-04T03:10:00+00:00"
        record_evidence(
            catalog,
            "subscription-gap",
            observed_at=gap_at,
            body=b'{"lifecycleEvent":"subscriptionRemoved"}',
        )
        record_evidence(
            catalog,
            "reconciliation",
            observed_at=reconcile_at,
        )
        gap = TeamsCoverageItem(
            source_id=SOURCE,
            scope_kind="chat-messages",
            scope=("chat-a",),
            fact_kind="subscription-lifecycle",
            status="gap",
            history_incomplete=True,
            observed_at=gap_at,
            evidence_id="subscription-gap",
            run_id=RUN,
            visible_scope={"resource": "chat-a"},
            retention_limitations=["provider-visible retained history only"],
            subscription_id="opaque-subscription",
            subscription_valid_from="2026-10-04T00:00:00+00:00",
            subscription_valid_until="2026-10-04T03:00:00+00:00",
            gap_kind="subscription-removed",
            details={"lifecycle_event": "subscriptionRemoved"},
        )
        reconcile = TeamsCoverageItem(
            source_id=SOURCE,
            scope_kind="chat-messages",
            scope=("chat-a",),
            fact_kind="reconciliation",
            status="current-state-read",
            history_incomplete=False,
            observed_at=reconcile_at,
            evidence_id="reconciliation",
            run_id=RUN,
            visible_scope={"resource": "chat-a"},
            retention_limitations=["provider-visible retained history only"],
            subscription_id="opaque-subscription",
            subscription_valid_from=None,
            subscription_valid_until=None,
            gap_kind=None,
            details={"readback": "successful"},
        )
        store.persist(gap)
        store.persist(reconcile)

        with catalog.Session() as session:
            history = session.scalars(
                select(TeamsCoverageObservation).order_by(
                    TeamsCoverageObservation.observation_id
                )
            ).all()
            if len(history) != 2:
                pytest.fail("Coverage gap and reconciliation must both remain history")
            if history[0].subscription_id != "opaque-subscription":
                pytest.fail("Subscription identity was not retained with gap evidence")
            if history[0].subscription_valid_until != ("2026-10-04T03:00:00+00:00"):
                pytest.fail("Subscription validity window must remain durable")
            current = session.scalar(select(TeamsCoverageCurrent))
            if current is None:
                pytest.fail("Expected one durable coverage projection")
            if not current.history_incomplete:
                pytest.fail(
                    "Successful current-state reconciliation cannot erase old "
                    "history uncertainty"
                )
            if current.latest_status != "current-state-read":
                pytest.fail(
                    "Later reconciliation should remain the latest coverage fact"
                )
    finally:
        catalog.close()


def test_deletion_scope_handles_duplicate_provider_ids(tmp_path: Path) -> None:
    catalog = open_catalog(tmp_path)
    store = TeamsMessageStore(catalog, source_id=SOURCE)
    try:
        for index, chat_id in enumerate(("chat-a", "chat-b")):
            observed_at = f"2026-10-04T04:00:0{index}+00:00"
            evidence_id = f"delete-{index}"
            record_evidence(catalog, evidence_id, observed_at=observed_at)
            store.persist_deletion(
                TeamsMessageDeletionItem(
                    source_id=SOURCE,
                    identity=TeamsMessageIdentity.chat(
                        "same-message",
                        chat_id=chat_id,
                    ),
                    deletion_kind="notification",
                    declared_deleted_at=None,
                    observed_at=observed_at,
                    evidence_id=evidence_id,
                    run_id=RUN,
                    readback_state="not-attempted",
                )
            )
        with catalog.Session() as session:
            rows = session.scalars(select(TeamsMessageDeletionObservation)).all()
            if len(rows) != 2:
                pytest.fail("Deletion facts must retain chat-scoped opaque identity")
            if len({row.scope_key_sha256 for row in rows}) != 2:
                pytest.fail("Deletion scoped keys must distinguish duplicate IDs")
    finally:
        catalog.close()
