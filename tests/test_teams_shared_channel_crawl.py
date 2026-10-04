"""Exercise shared and incoming channel topology without context collapse."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from message_ingest.catalog.models.microsoft.teams import TeamsTopologyObservation
from message_ingest.catalog.store import Catalog
from tests.teams_support import GraphFixture, crawl, json_reply
from tests.teams_support import graph_fixture as shared_graph_fixture

graph_fixture = shared_graph_fixture

SELECT = (
    "?%24select=id%2CcreatedDateTime%2CdisplayName%2Cdescription%2CisArchived"
    "%2CisFavoriteByDefault%2ClayoutType%2CmembershipType%2CmigrationMode"
    "%2CoriginalCreatedDateTime%2CtenantId%2CwebUrl"
)


def test_shared_topology_preserves_receivers_and_membership_paths(
    tmp_path: Path,
    graph_fixture: GraphFixture,
) -> None:
    associated = [
        {"id": "recv-a", "tenantId": "tenant-a"},
        {"id": "recv-b", "tenantId": "tenant-b"},
    ]
    graph_fixture.add(
        "/v1.0/me/teamwork/associatedTeams",
        json_reply({"value": associated}),
    )
    graph_fixture.add("/v1.0/me/joinedTeams", json_reply({"value": associated}))
    link = (
        "https://graph.microsoft.com/v1.0/tenants/host-tenant/"
        "teams/host-team/channels/shared"
    )
    incoming = {
        "id": "shared",
        "@odata.id": link,
        "tenantId": "host-tenant",
        "membershipType": "shared",
        "layoutType": None,
    }
    for team, tenant in (("recv-a", "tenant-a"), ("recv-b", "tenant-b")):
        graph_fixture.add(
            f"/v1.0/teams/{team}",
            json_reply({"id": team, "tenantId": tenant}),
        )
        graph_fixture.add(
            f"/v1.0/teams/{team}/members?%24top=999",
            json_reply({"value": []}),
        )
        graph_fixture.add(
            f"/v1.0/teams/{team}/allChannels" + SELECT,
            json_reply({"value": [incoming]}),
        )
        graph_fixture.add(
            f"/v1.0/teams/{team}/incomingChannels" + SELECT,
            json_reply({"value": [incoming]}),
        )

    detail_target = "/v1.0/teams/host-team/channels/shared"
    graph_fixture.add(
        detail_target,
        json_reply(
            {
                "id": "shared",
                "tenantId": "host-tenant",
                "membershipType": "shared",
                "layoutType": "posts",
            }
        ),
    )
    graph_fixture.add(
        "/v1.0/teams/host-team/channels/shared/sharedWithTeams",
        json_reply(
            {
                "value": [
                    {"id": "recv-a", "tenantId": "tenant-a"},
                    {"id": "recv-b", "tenantId": "tenant-b"},
                ]
            }
        ),
    )
    graph_fixture.add(
        "/v1.0/teams/host-team/channels/shared/members?%24top=999",
        json_reply({"value": [{"id": "same", "userId": "user-x"}]}),
    )
    graph_fixture.add(
        "/v1.0/teams/host-team/channels/shared/allMembers",
        json_reply(
            {
                "value": [
                    {
                        "id": "same",
                        "userId": "user-x",
                        "@microsoft.graph.originalSourceMembershipUrl": "source-a",
                    },
                    {
                        "id": "same",
                        "userId": "user-x",
                        "@microsoft.graph.originalSourceMembershipUrl": "source-b",
                    },
                ]
            }
        ),
    )
    graph_fixture.add(
        "/v1.0/teams/host-team/channels/shared/messages?%24top=50",
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

    detail_hits = [
        request for request in graph_fixture.seen if request.target == detail_target
    ]
    if len(detail_hits) < 2:
        pytest.fail(
            "Distinct receiving contexts were collapsed by the native dupefilter"
        )

    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        with catalog.Session() as session:
            rows = session.scalars(select(TeamsTopologyObservation)).all()
        channels = [
            row
            for row in rows
            if row.resource_kind == "channel"
            and row.context.get("channel_id") == "shared"
        ]
        receiving = {
            row.context.get("receiving_team_id")
            for row in channels
            if row.context.get("receiving_team_id")
        }
        if receiving != {"recv-a", "recv-b"}:
            pytest.fail("Shared channel receiving-team contexts were conflated")
        memberships = [
            row
            for row in rows
            if row.resource_kind == "channel-membership"
            and row.context.get("membership_source") == "all"
        ]
        sources = {
            row.context.get("original_source_membership_url") for row in memberships
        }
        if sources != {"source-a", "source-b"}:
            pytest.fail("Direct/indirect allMembers paths were deduplicated")
        if any(row.context.get("host_team_id") != "host-team" for row in channels):
            pytest.fail("Incoming channel content host identity was not preserved")
    finally:
        catalog.close()
