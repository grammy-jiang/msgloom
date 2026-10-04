"""Prove channel hydration and malformed payload failures fail closed."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from message_ingest.catalog.models.acquisition import RawHttpEvidence
from message_ingest.catalog.models.microsoft.teams import TeamsCoverageObservation
from message_ingest.catalog.store import Catalog
from tests.teams_support import GraphFixture, crawl, json_reply
from tests.teams_support import graph_fixture as shared_graph_fixture

graph_fixture = shared_graph_fixture

SELECT = (
    "?%24select=id%2CcreatedDateTime%2CdisplayName%2Cdescription%2CisArchived"
    "%2CisFavoriteByDefault%2ClayoutType%2CmembershipType%2CmigrationMode"
    "%2CoriginalCreatedDateTime%2CtenantId%2CwebUrl"
)


def test_team_detail_403_retains_failure_evidence_and_limitation(
    tmp_path: Path,
    graph_fixture: GraphFixture,
) -> None:
    team = {"id": "host-only", "tenantId": "tenant-host"}
    graph_fixture.add(
        "/v1.0/me/teamwork/associatedTeams",
        json_reply({"value": [team]}),
    )
    graph_fixture.add("/v1.0/me/joinedTeams", json_reply({"value": []}))
    graph_fixture.add(
        "/v1.0/teams/host-only",
        json_reply({"error": {"code": "Forbidden"}}, status=403),
    )
    graph_fixture.add(
        "/v1.0/teams/host-only/members?%24top=999",
        json_reply({"value": []}),
    )
    graph_fixture.add(
        "/v1.0/teams/host-only/allChannels" + SELECT,
        json_reply({"value": []}),
    )
    graph_fixture.add(
        "/v1.0/teams/host-only/incomingChannels" + SELECT,
        json_reply({"value": []}),
    )
    result = crawl(
        tmp_path,
        graph_fixture,
        ["crawl", "microsoft_teams_channel_discover"],
        extra_settings={
            "SPIDER_MODULES": "message_ingest.spiders.microsoft.teams",
            "RETRY_TIMES": 0,
        },
    )
    if result.returncode:
        pytest.fail(result.stderr)
    if "request_failure:teams-team-detail" not in result.stderr:
        pytest.fail("Hydration terminal failure did not mark run integrity failed")

    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        with catalog.Session() as session:
            coverage = session.scalars(select(TeamsCoverageObservation)).all()
            failures = session.scalars(
                select(RawHttpEvidence).where(RawHttpEvidence.response_status == 403)
            ).all()
        if not failures:
            pytest.fail("403 hydration response was not retained as raw evidence")
        if not any(
            row.fact_kind == "detail-hydration"
            and row.status == "unavailable"
            and row.scope_kind == "team"
            for row in coverage
        ):
            pytest.fail("Hydration failure did not persist an explicit limitation")
    finally:
        catalog.close()


def test_malformed_collection_retains_raw_evidence_and_spider_error(
    tmp_path: Path,
    graph_fixture: GraphFixture,
) -> None:
    graph_fixture.add(
        "/v1.0/me/teamwork/associatedTeams",
        json_reply({"not-value": []}),
    )
    graph_fixture.add("/v1.0/me/joinedTeams", json_reply({"value": []}))
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
    if "spider_error" not in result.stderr:
        pytest.fail("Malformed Graph envelope did not fail logical integrity")

    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        with catalog.Session() as session:
            rows = session.scalars(
                select(RawHttpEvidence).where(
                    RawHttpEvidence.purpose == "teams-associated-teams"
                )
            ).all()
        if not rows:
            pytest.fail("Raw evidence must survive malformed collection parsing")
    finally:
        catalog.close()
