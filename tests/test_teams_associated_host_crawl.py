"""Qualify associated-only hosts and partial hydration in a native crawl."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from message_ingest.catalog import Catalog
from message_ingest.catalog.models.acquisition import RawHttpEvidence
from message_ingest.catalog.models.microsoft.teams import (
    TeamsCoverageObservation,
    TeamsMessageObservation,
    TeamsTopologyObservation,
)
from tests.teams_support import GraphFixture, crawl, json_reply
from tests.teams_support import graph_fixture as shared_graph_fixture
from tests.test_teams_channel_crawl import SELECT

graph_fixture = shared_graph_fixture


def test_associated_host_survives_denied_detail_and_keeps_shared_content(
    tmp_path: Path, graph_fixture: GraphFixture
) -> None:
    """Direct membership is not the completeness root for shared content.

    The second associated page discovers a host absent from joinedTeams. Its
    denied team detail must preserve discovery and an explicit coverage gap.
    Accessible shared-channel detail and messages must still be persisted.
    """
    next_target = "/v1.0/me/teamwork/associatedTeams?cursor=h%2F1+%20&x=1&x=2"
    graph_fixture.add(
        "/v1.0/me/teamwork/associatedTeams",
        json_reply({"value": [], "@odata.nextLink": graph_fixture.url(next_target)}),
    )
    host = {"id": "host-only", "tenantId": "tenant-host"}
    graph_fixture.add(next_target, json_reply({"value": [host]}))
    graph_fixture.add("/v1.0/me/joinedTeams", json_reply({"value": []}))
    graph_fixture.add(
        "/v1.0/teams/host-only",
        json_reply({"error": {"code": "Forbidden"}}, status=403),
    )
    channel = {
        "id": "shared",
        "tenantId": "tenant-host",
        "membershipType": "shared",
        "layoutType": None,
    }
    graph_fixture.add(
        "/v1.0/teams/host-only/allChannels" + SELECT,
        json_reply({"value": [channel]}),
    )
    for target in (
        "/v1.0/teams/host-only/incomingChannels" + SELECT,
        "/v1.0/teams/host-only/members?%24top=999",
        "/v1.0/teams/host-only/channels/shared/members?%24top=999",
        "/v1.0/teams/host-only/channels/shared/allMembers",
    ):
        graph_fixture.add(target, json_reply({"value": []}))
    detail = {**channel, "layoutType": "posts", "description": "full detail"}
    base = "/v1.0/teams/host-only/channels/shared"
    graph_fixture.add(base + SELECT, json_reply(detail))
    graph_fixture.add(
        base + "/sharedWithTeams",
        json_reply({"value": [{"id": "receiver", "tenantId": "tenant-receiver"}]}),
    )
    message = {"id": "visible", "body": {"content": "shared host content"}}
    graph_fixture.add(base + "/messages?%24top=50", json_reply({"value": [message]}))
    for suffix in ("/replies?%24top=50", "/hostedContents"):
        graph_fixture.add(
            base + "/messages/visible" + suffix, json_reply({"value": []})
        )

    result = crawl(
        tmp_path,
        graph_fixture,
        ["microsoft", "teams", "channel", "discover"],
        extra_settings={"RETRY_TIMES": 0},
    )
    if result.returncode != 1:
        pytest.fail("Denied host detail must fail the public logical run")
    if "request_failure:teams-team-detail" not in result.stderr:
        pytest.fail(result.stderr[-5000:])
    if next_target not in {request.target for request in graph_fixture.seen}:
        pytest.fail("Associated-team continuation was not replayed verbatim")

    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        with catalog.Session() as session:
            topology = session.scalars(select(TeamsTopologyObservation)).all()
            messages = session.scalars(select(TeamsMessageObservation)).all()
            coverage = session.scalars(select(TeamsCoverageObservation)).all()
            host_rows = [row for row in topology if row.resource_kind == "team"]
            if len(host_rows) != 1 or host_rows[0].raw != host:
                pytest.fail("Associated-only host discovery was lost or fabricated")
            if host_rows[0].context.get("representation") != "associated":
                pytest.fail("Denied detail was incorrectly promoted to full detail")
            channel_rows = [row for row in topology if row.resource_kind == "channel"]
            if {row.context.get("representation") for row in channel_rows} != {
                "allChannels",
                "detail",
            }:
                pytest.fail("Channel discovery and detail were not kept separately")
            detail_rows = [row for row in channel_rows if row.raw == detail]
            if len(detail_rows) != 1:
                pytest.fail("Hydrated channel layout and detail fields were lost")
            if len(messages) != 1 or messages[0].raw != message:
                pytest.fail("Denied host detail prevented accessible shared messages")
            if not any(
                row.scope_kind == "team"
                and row.scope_key == ["coverage", "team", "host-only"]
                and row.status == "unavailable"
                and row.history_incomplete
                for row in coverage
            ):
                pytest.fail("Associated-only host detail gap is missing")
            for row in [*topology, *messages, *coverage]:
                evidence = session.get(RawHttpEvidence, row.evidence_id)
                if evidence is None or not Path(evidence.response_body_path).is_file():
                    pytest.fail("A shared-host observation lacks durable evidence")
    finally:
        catalog.close()
