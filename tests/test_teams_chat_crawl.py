"""Run core Teams chat topology and history cases through real Scrapy crawls."""

from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import select
from teams_support import GraphFixture, crawl, json_reply

from message_ingest.catalog.models.microsoft.teams import (
    TeamsMessageCurrent,
    TeamsMessageDeletionObservation,
    TeamsMessageObservation,
    TeamsTopologyCurrent,
    TeamsTopologyObservation,
)
from message_ingest.catalog.store import Catalog

pytest_plugins = ("teams_support",)

CHAT_SETTINGS = {"SPIDER_MODULES": "message_ingest.spiders.microsoft.teams"}


def _run(tmp_path: Path, fixture: GraphFixture) -> None:
    """Run the production chat spider against the shared local Graph fixture."""
    result = crawl(
        tmp_path,
        fixture,
        ["crawl", "microsoft_teams_chat_discover"],
        extra_settings=CHAT_SETTINGS,
    )
    if result.returncode != 0:
        pytest.fail(result.stderr)


def _catalog(tmp_path: Path) -> Catalog:
    """Open the crawl catalog after globally registered Teams models load."""
    return Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")


def _add_chat_routes(
    fixture: GraphFixture,
    *,
    chat_id: str,
    messages: list[dict[str, Any]],
    members: list[dict[str, Any]] | None = None,
    pins: list[dict[str, Any]] | None = None,
) -> None:
    """Add terminal member/message/pin routes and empty hosted inventories."""
    fixture.add(
        f"/v1.0/chats/{chat_id}/members",
        json_reply({"value": members or []}),
    )
    fixture.add(
        f"/v1.0/chats/{chat_id}/messages?%24top=50",
        json_reply({"value": messages}),
    )
    fixture.add(
        f"/v1.0/chats/{chat_id}/pinnedMessages",
        json_reply({"value": pins or []}),
    )
    for message in messages:
        fixture.add(
            f"/v1.0/chats/{chat_id}/messages/{message['id']}/hostedContents",
            json_reply({"value": []}),
        )


def test_chat_topology_matrix_explicit_members_meeting_and_federation(
    tmp_path: Path,
    graph_fixture: GraphFixture,
) -> None:
    """Explicit pagination must exceed 25 members and preserve chat context."""
    chats = [
        {"id": "one", "chatType": "oneOnOne", "tenantId": "tenant-home"},
        {"id": "group", "chatType": "group", "tenantId": "tenant-home"},
        {
            "id": "meeting",
            "chatType": "meeting",
            "tenantId": "tenant-home",
            "onlineMeetingInfo": {"joinWebUrl": "https://meeting.invalid/join"},
        },
    ]
    graph_fixture.add("/v1.0/me/chats?%24top=50", json_reply({"value": chats}))
    _add_chat_routes(graph_fixture, chat_id="one", messages=[])
    _add_chat_routes(graph_fixture, chat_id="meeting", messages=[])

    first_members = [
        {
            "id": f"member-{index}",
            "userId": f"user-{index}",
            "tenantId": "tenant-home",
        }
        for index in range(25)
    ]
    next_target = "/v1.0/chats/group/members?cursor=a%2Fb+plus&cursor=x%20y"
    graph_fixture.add(
        "/v1.0/chats/group/members",
        json_reply(
            {
                "value": first_members,
                "@odata.nextLink": graph_fixture.url(next_target),
            }
        ),
    )
    graph_fixture.add(
        next_target,
        json_reply(
            {
                "value": [
                    {
                        "id": "member-25",
                        "userId": "foreign-user",
                        "tenantId": "tenant-foreign",
                    }
                ]
            }
        ),
    )
    graph_fixture.add(
        "/v1.0/chats/group/messages?%24top=50",
        json_reply({"value": []}),
    )
    graph_fixture.add("/v1.0/chats/group/pinnedMessages", json_reply({"value": []}))

    _run(tmp_path, graph_fixture)

    catalog = _catalog(tmp_path)
    try:
        with catalog.Session() as session:
            rows = session.scalars(
                select(TeamsTopologyObservation).order_by(
                    TeamsTopologyObservation.observation_id
                )
            ).all()
        chats_by_id = {
            row.context["chat_id"]: row for row in rows if row.resource_kind == "chat"
        }
        members = [row for row in rows if row.resource_kind == "chat-member"]
        if set(chats_by_id) != {"one", "group", "meeting"}:
            pytest.fail("All one-on-one, group, and meeting chats must persist")
        if chats_by_id["meeting"].context["chat_type"] != "meeting":
            pytest.fail("Meeting chat type was not preserved")
        meeting_raw = chats_by_id["meeting"].raw
        if meeting_raw is None or meeting_raw.get("onlineMeetingInfo") is None:
            pytest.fail("Meeting chat context was lost")
        if len([row for row in members if row.context["chat_id"] == "group"]) != 26:
            pytest.fail("Explicit chat member traversal was truncated at 25")
        if not any(row.context.get("tenant_id") == "tenant-foreign" for row in members):
            pytest.fail("Federated member tenant identity was not preserved")
        if next_target not in [seen.target for seen in graph_fixture.seen]:
            pytest.fail("Opaque member continuation was not replayed verbatim")
    finally:
        catalog.close()


def test_message_edits_and_direct_deletion_preserve_old_body(
    tmp_path: Path,
    graph_fixture: GraphFixture,
) -> None:
    """Separate observed versions survive when a later capture is deleted."""
    chat = {"id": "chat-a", "chatType": "group"}
    graph_fixture.add("/v1.0/me/chats?%24top=50", json_reply({"value": [chat]}))
    first = {
        "id": "message-a",
        "etag": "etag-1",
        "body": {"contentType": "html", "content": "first body"},
    }
    _add_chat_routes(graph_fixture, chat_id="chat-a", messages=[first])
    _run(tmp_path, graph_fixture)

    second = {
        "id": "message-a",
        "etag": "etag-2",
        "deletedDateTime": "2026-10-04T01:00:00Z",
        "body": {"contentType": "html", "content": ""},
    }
    graph_fixture.add("/v1.0/me/chats?%24top=50", json_reply({"value": [chat]}))
    _add_chat_routes(graph_fixture, chat_id="chat-a", messages=[second])
    _run(tmp_path, graph_fixture)

    catalog = _catalog(tmp_path)
    try:
        with catalog.Session() as session:
            observations = session.scalars(
                select(TeamsMessageObservation).order_by(
                    TeamsMessageObservation.observation_id
                )
            ).all()
            current = session.scalar(select(TeamsMessageCurrent))
            deletions = session.scalars(select(TeamsMessageDeletionObservation)).all()
        if len(observations) != 2:
            pytest.fail("Both observed message versions must remain in history")
        if observations[0].raw["body"]["content"] != "first body":
            pytest.fail("Direct deletion erased the previously observed body")
        if current is None or not current.is_deleted:
            pytest.fail("deletedDateTime must advance the explicit current state")
        if len(deletions) != 1 or deletions[0].deletion_kind != "direct":
            pytest.fail("Direct provider deletion evidence was not retained")
    finally:
        catalog.close()


def test_later_empty_lists_do_not_delete_message_or_unpin(
    tmp_path: Path,
    graph_fixture: GraphFixture,
) -> None:
    """Ordinary inventory absence must not invent deletion or unpin state."""
    chat = {"id": "chat-a", "chatType": "group"}
    message = {
        "id": "message-a",
        "etag": "etag-1",
        "body": {"contentType": "text", "content": "keep me"},
    }
    pin = {"id": "message-a", "message": {"id": "message-a"}}

    graph_fixture.add("/v1.0/me/chats?%24top=50", json_reply({"value": [chat]}))
    _add_chat_routes(
        graph_fixture,
        chat_id="chat-a",
        messages=[message],
        pins=[pin],
    )
    _run(tmp_path, graph_fixture)

    graph_fixture.add("/v1.0/me/chats?%24top=50", json_reply({"value": [chat]}))
    _add_chat_routes(graph_fixture, chat_id="chat-a", messages=[], pins=[])
    _run(tmp_path, graph_fixture)

    catalog = _catalog(tmp_path)
    try:
        with catalog.Session() as session:
            current_message = session.scalar(select(TeamsMessageCurrent))
            pin_current = session.scalar(
                select(TeamsTopologyCurrent).where(
                    TeamsTopologyCurrent.resource_kind == "pin"
                )
            )
            deletions = session.scalars(select(TeamsMessageDeletionObservation)).all()
            messages = session.scalars(select(TeamsMessageObservation)).all()
        if current_message is None or current_message.is_deleted:
            pytest.fail("An empty later message list must not imply deletion")
        if pin_current is None or pin_current.context.get("state") != "pinned":
            pytest.fail("An empty later pin list must not imply unpin")
        if deletions:
            pytest.fail("Inventory absence created unsupported deletion evidence")
        if len(messages) != 1:
            pytest.fail("Expanded pin representation became a second message version")
    finally:
        catalog.close()


def test_pin_targets_message_only_when_inventory_did_not_observe_it(
    tmp_path: Path,
    graph_fixture: GraphFixture,
) -> None:
    """A pin relation can trigger one scoped targeted read without expansion."""
    chat = {"id": "chat-pin", "chatType": "group"}
    graph_fixture.add(
        "/v1.0/me/chats?%24top=50",
        json_reply({"value": [chat]}),
    )
    graph_fixture.add("/v1.0/chats/chat-pin/members", json_reply({"value": []}))
    graph_fixture.add(
        "/v1.0/chats/chat-pin/messages?%24top=50",
        json_reply({"value": []}),
    )
    graph_fixture.add(
        "/v1.0/chats/chat-pin/pinnedMessages",
        json_reply({"value": [{"id": "pinned-only"}]}),
    )
    target = "/v1.0/chats/chat-pin/messages/pinned-only"
    graph_fixture.add(
        target,
        json_reply(
            {
                "id": "pinned-only",
                "etag": "etag-pinned",
                "body": {"contentType": "text", "content": "targeted pin body"},
            }
        ),
    )
    graph_fixture.add(
        "/v1.0/chats/chat-pin/messages/pinned-only/hostedContents",
        json_reply({"value": []}),
    )

    _run(tmp_path, graph_fixture)

    if [seen.target for seen in graph_fixture.seen].count(target) != 1:
        pytest.fail("Needed pinned message was not fetched exactly once")
    catalog = _catalog(tmp_path)
    try:
        with catalog.Session() as session:
            messages = session.scalars(select(TeamsMessageObservation)).all()
            pins = session.scalars(
                select(TeamsTopologyObservation).where(
                    TeamsTopologyObservation.resource_kind == "pin"
                )
            ).all()
        if len(messages) != 1 or messages[0].chat_id != "chat-pin":
            pytest.fail("Targeted pinned message did not retain chat scope")
        if messages[0].raw["body"]["content"] != "targeted pin body":
            pytest.fail("Targeted pinned message response was not stored")
        if len(pins) != 1 or pins[0].context.get("state") != "pinned":
            pytest.fail("Pin relation was not preserved separately")
    finally:
        catalog.close()


def test_duplicate_message_ids_are_scoped_to_each_chat(
    tmp_path: Path,
    graph_fixture: GraphFixture,
) -> None:
    """Identical opaque message IDs in different chats remain distinct."""
    chats = [
        {"id": "chat-a", "chatType": "oneOnOne"},
        {"id": "chat-b", "chatType": "group"},
    ]
    graph_fixture.add("/v1.0/me/chats?%24top=50", json_reply({"value": chats}))
    for chat in chats:
        _add_chat_routes(
            graph_fixture,
            chat_id=chat["id"],
            messages=[
                {
                    "id": "same-message",
                    "etag": f"etag-{chat['id']}",
                    "body": {"contentType": "text", "content": chat["id"]},
                }
            ],
        )

    _run(tmp_path, graph_fixture)

    catalog = _catalog(tmp_path)
    try:
        with catalog.Session() as session:
            rows = session.scalars(select(TeamsMessageObservation)).all()
        if len(rows) != 2:
            pytest.fail("Expected one stored observation in each chat")
        if {row.chat_id for row in rows} != {"chat-a", "chat-b"}:
            pytest.fail("Chat scope was not retained with duplicate message IDs")
        if len({row.scope_key_sha256 for row in rows}) != 2:
            pytest.fail("Duplicate provider IDs collapsed across chat scopes")
    finally:
        catalog.close()
