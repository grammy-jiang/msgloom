"""Exercise standard/private channel traversal through the real Scrapy stack."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from message_ingest.catalog.models.microsoft.teams import (
    TeamsMessageObservation,
    TeamsTopologyObservation,
)
from message_ingest.catalog.store import Catalog
from tests.teams_support import GraphFixture, crawl, json_reply
from tests.teams_support import graph_fixture as shared_graph_fixture

graph_fixture = shared_graph_fixture

SELECT = (
    "?%24select=id%2CcreatedDateTime%2CdisplayName%2Cdescription%2CisArchived"
    "%2CisFavoriteByDefault%2ClayoutType%2CmembershipType%2CmigrationMode"
    "%2CoriginalCreatedDateTime%2CtenantId%2CwebUrl"
)


def _add_common_team_routes(fixture: GraphFixture) -> None:
    team = {"id": "team-a", "displayName": "Team A", "tenantId": "tenant-a"}
    fixture.add("/v1.0/me/teamwork/associatedTeams", json_reply({"value": [team]}))
    fixture.add("/v1.0/me/joinedTeams", json_reply({"value": [team]}))
    fixture.add("/v1.0/teams/team-a", json_reply(team))
    fixture.add(
        "/v1.0/teams/team-a/members?%24top=999",
        json_reply({"value": [{"id": "team-member", "userId": "user-a"}]}),
    )
    fixture.add(
        "/v1.0/teams/team-a/incomingChannels" + SELECT,
        json_reply({"value": []}),
    )


def _add_channel_routes(fixture: GraphFixture) -> tuple[str, str]:
    standard = {
        "id": "standard",
        "tenantId": "tenant-a",
        "displayName": "Standard",
        "membershipType": "standard",
        "layoutType": None,
    }
    private = {
        "id": "private",
        "tenantId": "tenant-a",
        "displayName": "Private",
        "membershipType": "private",
        "layoutType": None,
    }
    fixture.add(
        "/v1.0/teams/team-a/allChannels" + SELECT,
        json_reply({"value": [standard, private]}),
    )
    for channel, layout in (("standard", "posts"), ("private", "posts")):
        fixture.add(
            f"/v1.0/teams/team-a/channels/{channel}" + SELECT,
            json_reply(
                {
                    "id": channel,
                    "tenantId": "tenant-a",
                    "membershipType": channel if channel == "private" else "standard",
                    "layoutType": layout,
                }
            ),
        )
        fixture.add(
            f"/v1.0/teams/team-a/channels/{channel}/members?%24top=999",
            json_reply({"value": [{"id": f"{channel}-direct", "userId": "user-a"}]}),
        )
        fixture.add(
            f"/v1.0/teams/team-a/channels/{channel}/allMembers",
            json_reply({"value": [{"id": f"{channel}-all", "userId": "user-a"}]}),
        )

    roots_next = (
        fixture.graph_root
        + "/teams/team-a/channels/standard/messages?"
        + "%24skiptoken=a%2fb+%20&x=1&x=2"
    )
    fixture.add(
        "/v1.0/teams/team-a/channels/standard/messages?%24top=50",
        json_reply(
            {
                "value": [{"id": "root-1", "body": {"content": "one"}}],
                "@odata.nextLink": roots_next,
            }
        ),
    )
    fixture.add(
        roots_next.removeprefix(fixture.origin),
        json_reply({"value": [{"id": "root-2", "body": {"content": "two"}}]}),
    )
    replies_next = (
        fixture.graph_root
        + "/teams/team-a/channels/standard/messages/root-1/replies?"
        + "%24skiptoken=r%2F1+%20&z=1&z=2"
    )
    fixture.add(
        "/v1.0/teams/team-a/channels/standard/messages/root-1/replies?%24top=50",
        json_reply(
            {
                "value": [{"id": "reply-1", "replyToId": "root-1"}],
                "@odata.nextLink": replies_next,
            }
        ),
    )
    fixture.add(
        replies_next.removeprefix(fixture.origin),
        json_reply({"value": [{"id": "reply-2", "replyToId": "root-1"}]}),
    )
    fixture.add(
        "/v1.0/teams/team-a/channels/standard/messages/root-2/replies?%24top=50",
        json_reply({"value": []}),
    )
    fixture.add(
        "/v1.0/teams/team-a/channels/private/messages?%24top=50",
        json_reply({"value": [{"id": "root-1", "body": {"content": "private"}}]}),
    )
    fixture.add(
        "/v1.0/teams/team-a/channels/private/messages/root-1/replies?%24top=50",
        json_reply({"value": []}),
    )
    fixture.add(
        "/v1.0/teams/team-a/channels/private/messages/root-1/hostedContents",
        json_reply({"value": []}),
    )
    for message in ("root-1", "root-2"):
        fixture.add(
            f"/v1.0/teams/team-a/channels/standard/messages/{message}/hostedContents",
            json_reply({"value": []}),
        )
    for reply in ("reply-1", "reply-2"):
        fixture.add(
            "/v1.0/teams/team-a/channels/standard/messages/root-1/"
            f"replies/{reply}/hostedContents",
            json_reply({"value": []}),
        )
    return roots_next, replies_next


def test_channel_thread_pagination_and_private_inventory(
    tmp_path: Path,
    graph_fixture: GraphFixture,
) -> None:
    _add_common_team_routes(graph_fixture)
    roots_next, replies_next = _add_channel_routes(graph_fixture)
    result = crawl(
        tmp_path,
        graph_fixture,
        ["crawl", "microsoft_teams_channel_discover"],
        extra_settings={
            "SPIDER_MODULES": "message_ingest.spiders.microsoft.teams",
        },
    )
    if result.returncode:
        pytest.fail(result.stderr)

    targets = tuple(request.target for request in graph_fixture.seen)
    for opaque in (
        roots_next.removeprefix(graph_fixture.origin),
        replies_next.removeprefix(graph_fixture.origin),
    ):
        if opaque not in targets:
            pytest.fail("Opaque provider continuation was not replayed verbatim")
    continuation_requests = [
        request
        for request in graph_fixture.seen
        if request.target
        in {
            roots_next.removeprefix(graph_fixture.origin),
            replies_next.removeprefix(graph_fixture.origin),
        }
    ]
    if any(
        "include-unknown-enum-members" not in request.header("Prefer")
        for request in continuation_requests
    ):
        pytest.fail("Message continuation lost its representation header")

    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        with catalog.Session() as session:
            messages = session.scalars(select(TeamsMessageObservation)).all()
            topology = session.scalars(select(TeamsTopologyObservation)).all()
        scopes = {tuple(row.scope_key) for row in messages}
        expected_scopes = {
            ("message", "channel-root", "team-a", "standard", "root-1"),
            ("message", "channel-root", "team-a", "standard", "root-2"),
            ("message", "channel-root", "team-a", "private", "root-1"),
            (
                "message",
                "channel-reply",
                "team-a",
                "standard",
                "root-1",
                "reply-1",
            ),
            (
                "message",
                "channel-reply",
                "team-a",
                "standard",
                "root-1",
                "reply-2",
            ),
        }
        if not expected_scopes.issubset(scopes):
            pytest.fail("Root/reply scoped observations were not all persisted")
        duplicate_id_scopes = {
            scope
            for scope in scopes
            if scope[-1] == "root-1" and scope[1] == "channel-root"
        }
        if len(duplicate_id_scopes) != 2:
            pytest.fail("Duplicate provider message IDs collapsed across channels")
        channel_rows = [row for row in topology if row.resource_kind == "channel"]
        if not any(
            row.context.get("representation") == "detail"
            and row.context.get("channel_id") == "private"
            for row in channel_rows
        ):
            pytest.fail("Private channel inventory was not hydrated separately")
    finally:
        catalog.close()


def test_empty_team_inventory_creates_no_phantom_resources(
    tmp_path: Path,
    graph_fixture: GraphFixture,
) -> None:
    """An empty discovery root is a valid observation, not deletion evidence."""
    graph_fixture.add(
        "/v1.0/me/teamwork/associatedTeams",
        json_reply({"value": []}),
    )
    graph_fixture.add(
        "/v1.0/me/joinedTeams",
        json_reply({"value": []}),
    )
    result = crawl(
        tmp_path,
        graph_fixture,
        ["crawl", "microsoft_teams_channel_discover"],
        extra_settings={
            "SPIDER_MODULES": "message_ingest.spiders.microsoft.teams",
        },
    )
    if result.returncode:
        pytest.fail(result.stderr)

    targets = {request.target for request in graph_fixture.seen}
    if targets != {
        "/v1.0/me/teamwork/associatedTeams",
        "/v1.0/me/joinedTeams",
    }:
        pytest.fail("Empty team inventories scheduled phantom follow-up requests")

    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        with catalog.Session() as session:
            messages = session.scalars(select(TeamsMessageObservation)).all()
            topology = session.scalars(select(TeamsTopologyObservation)).all()
        if messages or topology:
            pytest.fail("Empty team inventories created phantom semantic resources")
    finally:
        catalog.close()
