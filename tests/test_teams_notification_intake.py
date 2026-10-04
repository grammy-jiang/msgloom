"""Real-pipeline tests for saved Teams notification envelope intake."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from message_ingest.catalog.models.acquisition import RawHttpEvidence
from message_ingest.catalog.models.microsoft.teams import (
    TeamsCoverageObservation,
    TeamsMessageDeletionObservation,
)
from tests.teams_notification_support import (
    DEFAULT_EVIDENCE_ID,
    DELIVERY_URL,
    SECRET,
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

pytest_plugins = ("teams_support",)


def _inbound_row(tmp_path: Path) -> RawHttpEvidence:
    catalog = open_catalog(tmp_path)
    try:
        with catalog.Session() as session:
            row = session.get(RawHttpEvidence, DEFAULT_EVIDENCE_ID)
            if row is None:
                pytest.fail("Expected inbound notification evidence")
            session.expunge(row)
            return row
    finally:
        catalog.close()


def test_exact_inbound_bytes_precede_aggregate_semantics_and_deletion(
    tmp_path: Path,
    graph_fixture: GraphFixture,
) -> None:
    """One scope/evidence row keeps every ordered event and one deletion fact."""
    entries = [
        change_event(
            resource="/chats/chat-a/messages/message-a", change_type="updated"
        ),
        change_event(
            resource="/chats/chat-a/messages/message-a", change_type="deleted"
        ),
        change_event(
            resource="/chats/chat-a/messages/message-a", change_type="deleted"
        ),
    ]
    body = encode_envelope(entries)
    target = "/v1.0/chats/chat-a/messages/message-a"
    graph_fixture.add(
        target,
        json_reply({"error": {"code": "NotFound"}}, status=404),
    )

    result = crawl_notification(
        tmp_path,
        graph_fixture,
        body=body,
        subscriptions=[chat_subscription()],
    )
    if result.returncode != 0:
        pytest.fail(result.stderr)

    row = _inbound_row(tmp_path)
    if row.origin != "inbound-webhook" or row.request_method != "POST":
        pytest.fail("Inbound notification provenance was not preserved")
    if row.request_url != DELIVERY_URL:
        pytest.fail("Caller-trusted delivery URL was not retained")
    if row.response_url is not None or row.response_status is not None:
        pytest.fail("Inbound evidence fabricated a Graph response")
    if row.response_body_bytes != 0:
        pytest.fail("Inbound evidence fabricated a response body")
    if Path(row.request_body_path).read_bytes() != body:
        pytest.fail("Inbound envelope bytes changed before raw persistence")

    catalog = open_catalog(tmp_path)
    try:
        with catalog.Session() as session:
            coverage = session.scalars(
                select(TeamsCoverageObservation).where(
                    TeamsCoverageObservation.evidence_id == DEFAULT_EVIDENCE_ID
                )
            ).all()
            deletions = session.scalars(
                select(TeamsMessageDeletionObservation).where(
                    TeamsMessageDeletionObservation.evidence_id == DEFAULT_EVIDENCE_ID
                )
            ).all()
        if len(coverage) != 1:
            pytest.fail(
                "Notification envelope must aggregate one coverage row per scope"
            )
        details = coverage[0].details
        events = details.get("events") if isinstance(details, dict) else None
        if not isinstance(events, list):
            pytest.fail("Aggregate notification coverage omitted ordered events")
        if [event.get("change_type") for event in events] != [
            "updated",
            "deleted",
            "deleted",
        ]:
            pytest.fail("Aggregate coverage changed provider event order")
        if any(SECRET in str(event) for event in events):
            pytest.fail("Semantic notification rows exposed clientState")
        if len(deletions) != 1:
            pytest.fail(
                "Duplicate deletion declarations must persist one identical fact"
            )
        deletion = deletions[0]
        if deletion.readback_state != "not-attempted":
            pytest.fail("Notification deletion declaration must remain immutable")
        if deletion.readback_evidence_id is not None:
            pytest.fail("Deletion declaration must not be rewritten with readback")
    finally:
        catalog.close()

    hits = [seen for seen in graph_fixture.seen if seen.target == target]
    if len(hits) != 1:
        pytest.fail("Repeated envelope events must coalesce one scoped readback")


@pytest.mark.parametrize(
    "body",
    [
        b'{"value":',
        encode_envelope([change_event(client_state="wrong")]),
        encode_envelope(
            [
                change_event(
                    resource="https://evil.invalid/chats/chat-a/messages/message-a"
                )
            ]
        ),
        encode_envelope([change_event(subscription_id="unknown")]),
        encode_envelope([change_event(tenant_id="tenant-b")]),
        encode_envelope([change_event(resource="/chats/other/messages/message-a")]),
        encode_envelope([change_event(resourceData={"id": "message-a"})]),
    ],
)
def test_invalid_envelope_retains_only_raw_and_never_fetches(
    tmp_path: Path,
    graph_fixture: GraphFixture,
    body: bytes,
) -> None:
    result = crawl_notification(
        tmp_path,
        graph_fixture,
        body=body,
        subscriptions=[chat_subscription()],
    )
    if result.returncode != 0:
        pytest.fail(result.stderr)
    if graph_fixture.seen:
        pytest.fail("Invalid notification caused a Graph request")
    if "notification_invalid" not in result.stderr:
        pytest.fail("Invalid notification did not mark logical run failure")

    row = _inbound_row(tmp_path)
    if Path(row.request_body_path).read_bytes() != body:
        pytest.fail("Invalid input raw bytes were not retained exactly")
    catalog = open_catalog(tmp_path)
    try:
        with catalog.Session() as session:
            if session.scalars(select(TeamsCoverageObservation)).all():
                pytest.fail("Invalid envelope wrote Teams coverage semantics")
            if session.scalars(select(TeamsMessageDeletionObservation)).all():
                pytest.fail("Invalid envelope wrote a deletion declaration")
    finally:
        catalog.close()


def test_exact_replay_is_idempotent_but_changed_bytes_under_same_id_fail_closed(
    tmp_path: Path,
    graph_fixture: GraphFixture,
) -> None:
    original = encode_envelope(
        [
            lifecycle_event(lifecycle="reauthorizationRequired"),
            lifecycle_event(lifecycle="subscriptionRemoved"),
        ]
    )
    subscriptions = [chat_subscription()]

    first = crawl_notification(
        tmp_path,
        graph_fixture,
        body=original,
        subscriptions=subscriptions,
    )
    if first.returncode != 0:
        pytest.fail(first.stderr)
    replay = crawl_notification(
        tmp_path,
        graph_fixture,
        body=original,
        subscriptions=subscriptions,
    )
    if replay.returncode != 0:
        pytest.fail(replay.stderr)

    changed = encode_envelope(
        [
            lifecycle_event(lifecycle="subscriptionRemoved"),
            lifecycle_event(lifecycle="reauthorizationRequired"),
        ]
    )
    conflict = crawl_notification(
        tmp_path,
        graph_fixture,
        body=changed,
        subscriptions=subscriptions,
    )
    if conflict.returncode != 0:
        pytest.fail(conflict.stderr)
    if "notification_replay_conflict" not in conflict.stderr:
        pytest.fail("Changed bytes under one stable evidence ID did not fail closed")

    reordered = crawl_notification(
        tmp_path,
        graph_fixture,
        body=changed,
        subscriptions=subscriptions,
        evidence_id="b" * 32,
    )
    if reordered.returncode != 0:
        pytest.fail(reordered.stderr)

    catalog = open_catalog(tmp_path)
    try:
        with catalog.Session() as session:
            evidence = session.get(RawHttpEvidence, DEFAULT_EVIDENCE_ID)
            coverage = session.scalars(
                select(TeamsCoverageObservation).order_by(
                    TeamsCoverageObservation.evidence_id
                )
            ).all()
        if evidence is None:
            pytest.fail("Replay test lost original raw evidence")
        if Path(evidence.request_body_path).read_bytes() != original:
            pytest.fail("Conflicting replay replaced protected original bytes")
        if len(coverage) != 2:
            pytest.fail("Exact replay/conflict or reordered envelope count changed")
        first_events = coverage[0].details.get("events")
        second_events = coverage[1].details.get("events")
        if not isinstance(first_events, list) or not isinstance(second_events, list):
            pytest.fail("Replay coverage lost ordered event details")
        if [event.get("lifecycle_event") for event in first_events] != [
            "reauthorizationRequired",
            "subscriptionRemoved",
        ]:
            pytest.fail("Conflicting replay changed original event order")
        if [event.get("lifecycle_event") for event in second_events] != [
            "subscriptionRemoved",
            "reauthorizationRequired",
        ]:
            pytest.fail("Reordered new envelope did not retain its own event order")
    finally:
        catalog.close()


def test_multiple_subscriptions_same_scope_preserve_each_validity_in_one_fact(
    tmp_path: Path,
    graph_fixture: GraphFixture,
) -> None:
    subscriptions = [
        chat_subscription(subscription_id="sub-one"),
        chat_subscription(subscription_id="sub-two"),
    ]
    body = encode_envelope(
        [
            change_event(
                subscription_id="sub-two",
                resource="/chats/chat-a/messages/message-2",
            ),
            change_event(
                subscription_id="sub-one",
                resource="/chats/chat-a/messages/message-1",
            ),
        ]
    )
    graph_fixture.add(
        "/v1.0/chats/chat-a/messages/message-2",
        json_reply(
            {"id": "message-2", "body": {"contentType": "text", "content": "2"}}
        ),
    )
    graph_fixture.add(
        "/v1.0/chats/chat-a/messages/message-1",
        json_reply(
            {"id": "message-1", "body": {"contentType": "text", "content": "1"}}
        ),
    )
    result = crawl_notification(
        tmp_path,
        graph_fixture,
        body=body,
        subscriptions=subscriptions,
    )
    if result.returncode != 0:
        pytest.fail(result.stderr)

    catalog = open_catalog(tmp_path)
    try:
        with catalog.Session() as session:
            rows = session.scalars(
                select(TeamsCoverageObservation).where(
                    TeamsCoverageObservation.evidence_id == DEFAULT_EVIDENCE_ID
                )
            ).all()
        if len(rows) != 1:
            pytest.fail("Multiple subscriptions in one scope must aggregate")
        events = rows[0].details.get("events")
        if not isinstance(events, list):
            pytest.fail("Aggregate coverage lacks event details")
        if [event.get("subscription_id") for event in events] != [
            "sub-two",
            "sub-one",
        ]:
            pytest.fail("Per-event subscription identity was overwritten")
        if any(
            not event.get("subscription_valid_from")
            or not event.get("subscription_valid_until")
            for event in events
        ):
            pytest.fail("Per-event trusted validity windows were not preserved")
        if rows[0].subscription_id is not None:
            pytest.fail("Aggregate fact must not silently choose one subscription")
    finally:
        catalog.close()


def test_channel_subscription_cannot_be_selected_by_chat_envelope(
    tmp_path: Path,
    graph_fixture: GraphFixture,
) -> None:
    body = encode_envelope(
        [
            change_event(
                subscription_id="sub-channel",
                resource="/chats/chat-a/messages/message-a",
            )
        ]
    )
    result = crawl_notification(
        tmp_path,
        graph_fixture,
        body=body,
        subscriptions=[channel_subscription()],
    )
    if result.returncode != 0:
        pytest.fail(result.stderr)
    if graph_fixture.seen:
        pytest.fail("Scope-confused subscription caused a Graph fetch")
    if "notification_invalid" not in result.stderr:
        pytest.fail("Scope-confused subscription did not fail integrity")
