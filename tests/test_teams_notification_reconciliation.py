"""Targeted Graph readback and sticky-history notification reconciliation tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from message_ingest.catalog.models.acquisition import RawHttpEvidence
from message_ingest.catalog.models.microsoft.teams import (
    TeamsCoverageCurrent,
    TeamsCoverageObservation,
    TeamsMessageCurrent,
    TeamsMessageDeletionObservation,
    TeamsMessageObservation,
)
from message_ingest.catalog.stores.microsoft.teams.message import TeamsMessageStore
from tests.teams_notification_support import (
    SOURCE,
    GraphFixture,
    change_event,
    channel_subscription,
    chat_subscription,
    crawl_notification,
    encode_envelope,
    json_reply,
    lifecycle_event,
    open_catalog,
)
from tests.teams_persistence_support import chat_message, record_evidence

pytest_plugins = ("teams_support",)


def test_chat_and_channel_reply_readbacks_use_provider_paths_and_scoped_identity(
    tmp_path: Path,
    graph_fixture: GraphFixture,
) -> None:
    body = encode_envelope(
        [
            change_event(
                subscription_id="sub-chat",
                resource="/chats/same/messages/same",
            ),
            change_event(
                subscription_id="sub-channel",
                resource="/teams/same/channels/same/messages/root/replies/same",
            ),
        ]
    )
    chat_target = "/v1.0/chats/same/messages/same"
    reply_target = "/v1.0/teams/same/channels/same/messages/root/replies/same"
    graph_fixture.add(
        chat_target,
        json_reply(
            {
                "id": "same",
                "etag": "chat-version",
                "body": {"contentType": "text", "content": "chat body"},
            }
        ),
    )
    graph_fixture.add(
        reply_target,
        json_reply(
            {
                "id": "same",
                "etag": "reply-version",
                "replyToId": "root",
                "body": {"contentType": "text", "content": "reply body"},
            }
        ),
    )
    result = crawl_notification(
        tmp_path,
        graph_fixture,
        body=body,
        subscriptions=[
            chat_subscription(subscription_id="sub-chat", chat_id="same"),
            channel_subscription(
                subscription_id="sub-channel",
                team_id="same",
                channel_id="same",
            ),
        ],
    )
    if result.returncode != 0:
        pytest.fail(result.stderr)
    targets = [seen.target for seen in graph_fixture.seen]
    if targets.count(chat_target) != 1 or targets.count(reply_target) != 1:
        pytest.fail("Notification readback bypassed provider-built targeted paths")
    if any("evil" in target for target in targets):
        pytest.fail("Unexpected arbitrary notification resource URL fetch")

    catalog = open_catalog(tmp_path)
    try:
        with catalog.Session() as session:
            messages = session.scalars(select(TeamsMessageObservation)).all()
            raw = session.scalars(
                select(RawHttpEvidence).where(
                    RawHttpEvidence.purpose == "teams-notification-message-readback"
                )
            ).all()
        if len(messages) != 2 or len(raw) != 2:
            pytest.fail("Expected one raw Graph capture and message per readback")
        if {row.evidence_id for row in messages} != {row.evidence_id for row in raw}:
            pytest.fail("Message semantics were not linked to actual Graph evidence")
        identities = {
            (
                row.location,
                row.chat_id,
                row.team_id,
                row.channel_id,
                row.root_message_id,
                row.message_id,
            )
            for row in messages
        }
        expected = {
            ("chat", "same", None, None, None, "same"),
            ("channel-reply", None, "same", "same", "root", "same"),
        }
        if identities != expected:
            pytest.fail("Equal opaque message IDs leaked across Teams scopes")
    finally:
        catalog.close()


@pytest.mark.parametrize("status", [403, 404])
def test_deleted_declaration_survives_failed_readback_and_preserves_old_body(
    tmp_path: Path,
    graph_fixture: GraphFixture,
    status: int,
) -> None:
    target = "/v1.0/chats/chat-a/messages/message-a"
    catalog = open_catalog(tmp_path)
    try:
        record_evidence(
            catalog,
            "1" * 32,
            source_id=SOURCE,
            observed_at="2026-10-04T04:30:00+00:00",
        )
        TeamsMessageStore(catalog, source_id=SOURCE).persist_message(
            chat_message(
                chat_id="chat-a",
                message_id="message-a",
                evidence_id="1" * 32,
                observed_at="2026-10-04T04:30:00+00:00",
                source_id=SOURCE,
                etag="old-version",
                body="old body",
            )
        )
    finally:
        catalog.close()

    graph_fixture.add(
        target,
        json_reply({"error": {"code": "ReadbackFailure"}}, status=status),
    )
    deleted = crawl_notification(
        tmp_path,
        graph_fixture,
        body=encode_envelope([change_event(change_type="deleted")]),
        subscriptions=[chat_subscription()],
        evidence_id="2" * 32,
        captured_at="2026-10-04T05:10:00+00:00",
    )
    if deleted.returncode != 0:
        pytest.fail(deleted.stderr)

    catalog = open_catalog(tmp_path)
    try:
        with catalog.Session() as session:
            deletions = session.scalars(
                select(TeamsMessageDeletionObservation).where(
                    TeamsMessageDeletionObservation.evidence_id == "2" * 32
                )
            ).all()
            current = session.scalar(select(TeamsMessageCurrent))
            observations = session.scalars(select(TeamsMessageObservation)).all()
            failures = session.scalars(
                select(RawHttpEvidence).where(RawHttpEvidence.response_status == status)
            ).all()
            associations = session.scalars(
                select(TeamsCoverageObservation).where(
                    TeamsCoverageObservation.fact_kind == "notification-readback",
                    TeamsCoverageObservation.status == "failed",
                )
            ).all()
        if len(deletions) != 1 or deletions[0].readback_state != "not-attempted":
            pytest.fail(
                "Failed readback rewrote or lost immutable deletion declaration"
            )
        if deletions[0].readback_evidence_id is not None:
            pytest.fail("Deletion row must not absorb later readback evidence")
        if current is None or not current.is_deleted:
            pytest.fail(
                "Explicit notification deletion did not project current deletion"
            )
        if (
            current.raw is None
            or current.raw.get("body", {}).get("content") != "old body"
        ):
            pytest.fail("Failed deletion readback discarded the last observed body")
        if len(observations) != 1:
            pytest.fail("Failed readback invented a new message body")
        if len(failures) != 1:
            pytest.fail("Failed readback raw Graph response was not retained")
        if len(associations) != 1:
            pytest.fail("Failed readback did not add a separate coverage association")
        details = associations[0].details
        if details.get("notification_evidence_id") != "2" * 32:
            pytest.fail("Readback association lost notification evidence identity")
    finally:
        catalog.close()


def test_failed_created_or_updated_readback_never_invents_message_or_deletion(
    tmp_path: Path,
    graph_fixture: GraphFixture,
) -> None:
    graph_fixture.add(
        "/v1.0/chats/chat-a/messages/message-a",
        json_reply({"error": {"code": "Forbidden"}}, status=403),
    )
    result = crawl_notification(
        tmp_path,
        graph_fixture,
        body=encode_envelope([change_event(change_type="updated")]),
        subscriptions=[chat_subscription()],
    )
    if result.returncode != 0:
        pytest.fail(result.stderr)

    catalog = open_catalog(tmp_path)
    try:
        with catalog.Session() as session:
            messages = session.scalars(select(TeamsMessageObservation)).all()
            deletions = session.scalars(select(TeamsMessageDeletionObservation)).all()
            associations = session.scalars(
                select(TeamsCoverageObservation).where(
                    TeamsCoverageObservation.fact_kind == "notification-readback"
                )
            ).all()
        if messages or deletions:
            pytest.fail("Failed update readback invented message/deletion semantics")
        if len(associations) != 1 or associations[0].status != "failed":
            pytest.fail("Failed update readback lacked additive failure association")
    finally:
        catalog.close()


@pytest.mark.parametrize(
    ("lifecycle", "local_gap"),
    [
        ("reauthorizationRequired", None),
        ("subscriptionRemoved", None),
        (
            None,
            {
                "evidence_id": "8" * 32,
                "captured_at": "2026-10-04T05:05:00+00:00",
                "subscription_id": "sub-chat",
                "gap_kind": "delivery-interruption",
            },
        ),
        (
            None,
            {
                "evidence_id": "9" * 32,
                "captured_at": "2026-10-04T05:05:00+00:00",
                "subscription_id": "sub-chat",
                "gap_kind": "subscription-expired",
            },
        ),
    ],
)
def test_gap_uncertainty_remains_sticky_after_successful_current_readback(
    tmp_path: Path,
    graph_fixture: GraphFixture,
    lifecycle: str | None,
    local_gap: dict[str, object] | None,
) -> None:
    first_entry = (
        lifecycle_event(lifecycle=lifecycle)
        if lifecycle is not None
        else change_event(
            resource="/chats/chat-a/messages/message-a",
            change_type="updated",
        )
    )
    if local_gap is not None:
        graph_fixture.add(
            "/v1.0/chats/chat-a/messages/message-a",
            json_reply(
                {
                    "id": "message-a",
                    "body": {"contentType": "text", "content": "gap-current"},
                }
            ),
        )
    first = crawl_notification(
        tmp_path,
        graph_fixture,
        body=encode_envelope([first_entry]),
        subscriptions=[chat_subscription()],
        evidence_id="3" * 32,
        captured_at="2026-10-04T05:00:00+00:00",
        local_gap=local_gap,
    )
    if first.returncode != 0:
        pytest.fail(first.stderr)

    graph_fixture.add(
        "/v1.0/chats/chat-a/messages/message-a",
        json_reply(
            {
                "id": "message-a",
                "etag": "after-gap",
                "body": {"contentType": "text", "content": "current after gap"},
            }
        ),
    )
    second = crawl_notification(
        tmp_path,
        graph_fixture,
        body=encode_envelope([change_event(change_type="updated")]),
        subscriptions=[chat_subscription()],
        evidence_id="4" * 32,
        captured_at="2026-10-04T05:20:00+00:00",
    )
    if second.returncode != 0:
        pytest.fail(second.stderr)

    catalog = open_catalog(tmp_path)
    try:
        with catalog.Session() as session:
            current = session.scalar(
                select(TeamsCoverageCurrent).where(
                    TeamsCoverageCurrent.scope_kind == "chat-messages"
                )
            )
        if current is None or not current.history_incomplete:
            pytest.fail("Successful current-state readback erased known history gap")
    finally:
        catalog.close()
