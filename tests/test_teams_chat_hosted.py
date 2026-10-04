"""Exercise Teams hosted-content traversal, evidence, and trigger association."""

import hashlib
from collections import Counter
from pathlib import Path

import pytest
from sqlalchemy import select
from teams_support import (
    FixtureReply,
    GraphFixture,
    crawl,
    json_reply,
)

from message_ingest.catalog.models.microsoft.teams import (
    TeamsHostedContentObservation,
    TeamsMessageObservation,
)
from message_ingest.catalog.store import Catalog

pytest_plugins = ("teams_support",)

CHAT_SETTINGS = {"SPIDER_MODULES": "message_ingest.spiders.microsoft.teams"}


def _base_routes(
    fixture: GraphFixture,
    *,
    message_payload: dict[str, object],
) -> None:
    """Add one chat/message shell; callers own hosted-content routes."""
    fixture.add(
        "/v1.0/me/chats?%24top=50",
        json_reply({"value": [{"id": "chat-hosted", "chatType": "group"}]}),
    )
    fixture.add("/v1.0/chats/chat-hosted/members", json_reply({"value": []}))
    fixture.add(
        "/v1.0/chats/chat-hosted/messages?%24top=50",
        json_reply({"value": [message_payload]}),
    )
    fixture.add(
        "/v1.0/chats/chat-hosted/pinnedMessages",
        json_reply({"value": []}),
    )


def _run(tmp_path: Path, fixture: GraphFixture):
    """Run the production spider and return its completed subprocess."""
    return crawl(
        tmp_path,
        fixture,
        ["crawl", "microsoft_teams_chat_discover"],
        extra_settings=CHAT_SETTINGS,
    )


def test_hosted_all_pages_metadata_and_bytes_keep_response_fidelity(
    tmp_path: Path,
    graph_fixture: GraphFixture,
) -> None:
    """Hosted list/item/bytes traversal preserves headers, digest, and trigger."""
    message = {
        "id": "message-hosted",
        "etag": "etag-hosted",
        "body": {"contentType": "html", "content": "inline hosted content"},
    }
    _base_routes(graph_fixture, message_payload=message)
    next_target = (
        "/v1.0/chats/chat-hosted/messages/message-hosted/hostedContents"
        "?cursor=a%2Fb+plus&cursor=x%20y"
    )
    list_target = "/v1.0/chats/chat-hosted/messages/message-hosted/hostedContents"
    graph_fixture.add(
        list_target,
        json_reply(
            {
                "value": [{"id": "hosted-1", "contentType": "image/png"}],
                "@odata.nextLink": graph_fixture.url(next_target),
            }
        ),
    )
    graph_fixture.add(
        next_target,
        json_reply({"value": [{"id": "hosted-2", "contentType": "text/plain"}]}),
    )

    bodies = {"hosted-1": b"\x89PNG\x00fixture", "hosted-2": b"print('fixture')"}
    for hosted_id, body in bodies.items():
        graph_fixture.add(
            f"{list_target}/{hosted_id}",
            json_reply({"id": hosted_id, "contentType": "application/octet-stream"}),
        )
        graph_fixture.add(
            f"{list_target}/{hosted_id}/$value",
            FixtureReply(
                body=body,
                headers=(("Content-Type", "application/octet-stream"),),
            ),
        )

    result = _run(tmp_path, graph_fixture)
    if result.returncode != 0:
        pytest.fail(result.stderr)

    seen_targets = [seen.target for seen in graph_fixture.seen]
    if next_target not in seen_targets:
        pytest.fail("Hosted continuation URL was not replayed verbatim")
    for seen in graph_fixture.seen:
        if seen.target in {
            f"{list_target}/hosted-1",
            f"{list_target}/hosted-2",
            f"{list_target}/hosted-1/$value",
            f"{list_target}/hosted-2/$value",
        } and seen.header("ConsistencyLevel") != ("eventual",):
            pytest.fail("Hosted item/byte reads must use eventual consistency")
        if seen.target.endswith("/$value") and seen.header("Accept") != (
            "application/octet-stream",
        ):
            pytest.fail("Hosted bytes must request the frozen binary representation")

    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        with catalog.Session() as session:
            rows = session.scalars(
                select(TeamsHostedContentObservation).order_by(
                    TeamsHostedContentObservation.observation_id
                )
            ).all()
        counts = Counter(row.observation_kind for row in rows)
        if counts != Counter({"metadata": 4, "bytes": 2}):
            pytest.fail(f"Unexpected hosted observation kinds: {counts}")
        if any(row.provider_version_bound for row in rows):
            pytest.fail("Hosted observations must never claim provider-version binding")
        bytes_rows = [row for row in rows if row.observation_kind == "bytes"]
        for row in bytes_rows:
            expected = bodies[row.hosted_content_id]
            if row.content_sha256 != hashlib.sha256(expected).hexdigest():
                pytest.fail("Hosted byte digest differs from linked raw response")
            if row.content_bytes != len(expected):
                pytest.fail("Hosted byte length differs from linked raw response")
        if len({row.trigger_evidence_id for row in rows}) != 1:
            pytest.fail("One message observation should own all hosted follow-ups")
    finally:
        catalog.close()


def test_hosted_same_url_keeps_distinct_trigger_observations(
    tmp_path: Path,
    graph_fixture: GraphFixture,
) -> None:
    """Application scheduling must bypass dupefilter only per distinct trigger."""
    graph_fixture.add(
        "/v1.0/me/chats?%24top=50",
        json_reply({"value": [{"id": "chat-hosted", "chatType": "group"}]}),
    )
    graph_fixture.add("/v1.0/chats/chat-hosted/members", json_reply({"value": []}))
    second_page = (
        "/v1.0/chats/chat-hosted/messages?cursor=second%2Fpage+plus&cursor=x%20y"
    )
    graph_fixture.add(
        "/v1.0/chats/chat-hosted/messages?%24top=50",
        json_reply(
            {
                "value": [
                    {
                        "id": "same-message",
                        "etag": "etag-1",
                        "body": {"contentType": "text", "content": "first"},
                    }
                ],
                "@odata.nextLink": graph_fixture.url(second_page),
            }
        ),
    )
    graph_fixture.add(
        second_page,
        json_reply(
            {
                "value": [
                    {
                        "id": "same-message",
                        "etag": "etag-2",
                        "body": {"contentType": "text", "content": "edited"},
                    }
                ]
            }
        ),
    )
    graph_fixture.add(
        "/v1.0/chats/chat-hosted/pinnedMessages",
        json_reply({"value": []}),
    )

    list_target = "/v1.0/chats/chat-hosted/messages/same-message/hostedContents"
    graph_fixture.add(
        list_target,
        json_reply({"value": [{"id": "hosted-shared", "contentType": "text/plain"}]}),
    )
    graph_fixture.add(
        f"{list_target}/hosted-shared",
        json_reply({"id": "hosted-shared", "contentType": "text/plain"}),
    )
    graph_fixture.add(
        f"{list_target}/hosted-shared/$value",
        FixtureReply(
            body=b"same current bytes", headers=(("Content-Type", "text/plain"),)
        ),
    )

    result = _run(tmp_path, graph_fixture)
    if result.returncode != 0:
        pytest.fail(result.stderr)

    list_hits = [seen for seen in graph_fixture.seen if seen.target == list_target]
    if len(list_hits) != 2:
        pytest.fail(
            "Native dupefilter collapsed hosted requests for distinct message triggers"
        )

    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        with catalog.Session() as session:
            messages = session.scalars(
                select(TeamsMessageObservation).order_by(
                    TeamsMessageObservation.observation_id
                )
            ).all()
            hosted = session.scalars(select(TeamsHostedContentObservation)).all()
        if len(messages) != 2:
            pytest.fail("Both observed edits must persist as separate message captures")
        if {row.raw["body"]["content"] for row in messages} != {"first", "edited"}:
            pytest.fail("Observed edit bodies were not both retained")
        if len({row.trigger_evidence_id for row in hosted}) != 2:
            pytest.fail("Hosted observations lost one exact triggering capture")
        if second_page not in [seen.target for seen in graph_fixture.seen]:
            pytest.fail("Message continuation representation changed")
    finally:
        catalog.close()


def test_hosted_deleted_thread_limitation_is_explicit_and_fails_run(
    tmp_path: Path,
    graph_fixture: GraphFixture,
) -> None:
    """A failed current hosted read persists a limitation and run failure."""
    message = {
        "id": "message-deleted-thread",
        "etag": "etag-deleted-thread",
        "deletedDateTime": "2026-10-04T02:00:00Z",
        "body": {"contentType": "text", "content": ""},
    }
    _base_routes(graph_fixture, message_payload=message)
    list_target = (
        "/v1.0/chats/chat-hosted/messages/message-deleted-thread/hostedContents"
    )
    graph_fixture.add(
        list_target,
        json_reply({"value": [{"id": "hosted-gone", "contentType": "image/png"}]}),
    )
    graph_fixture.add(
        f"{list_target}/hosted-gone",
        json_reply({"id": "hosted-gone", "contentType": "image/png"}),
    )
    graph_fixture.add(
        f"{list_target}/hosted-gone/$value",
        json_reply({"error": {"code": "Gone"}}, status=410),
    )

    result = _run(tmp_path, graph_fixture)
    if result.returncode != 0:
        pytest.fail(result.stderr)
    reason = (
        "'msgloom/crawl/integrity_failure_reason_count/"
        "request_failure:teams-chat-hosted-content-bytes': 1"
    )
    if reason not in result.stderr:
        pytest.fail("Hosted terminal failure did not mark inherited run integrity")

    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        with catalog.Session() as session:
            rows = session.scalars(select(TeamsHostedContentObservation)).all()
        failures = [row for row in rows if row.observation_kind == "failure"]
        if len(failures) != 1:
            pytest.fail("Expected one explicit hosted retrieval failure observation")
        failure = failures[0]
        if failure.status_code != 410:
            pytest.fail("Hosted failure lost the terminal HTTP status")
        if failure.failure_kind != "hosted-content-retrieval-failed":
            pytest.fail("Hosted failure kind is not the bounded application contract")
        if (
            failure.details.get("known_provider_limitation")
            != "hosted-content-in-deleted-thread-unsupported"
        ):
            pytest.fail("Deleted-thread hosted-content limitation was not recorded")
        if failure.provider_version_bound:
            pytest.fail("Hosted failure must not imply historical version binding")
    finally:
        catalog.close()
