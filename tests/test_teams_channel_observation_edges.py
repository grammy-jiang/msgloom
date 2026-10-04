"""Exercise empty channel inventories and readable hosted data after deletion."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from message_ingest.catalog import Catalog
from message_ingest.catalog.models.microsoft.teams import (
    TeamsHostedContentObservation,
    TeamsMessageDeletionObservation,
    TeamsMessageObservation,
    TeamsTopologyObservation,
)
from tests.teams_support import FixtureReply, GraphFixture, crawl, json_reply
from tests.teams_support import graph_fixture as shared_graph_fixture
from tests.test_teams_channel_crawl import SELECT, _add_common_team_routes
from tests.test_teams_channel_hosted import _add_hosted_base

graph_fixture = shared_graph_fixture


def test_nonempty_team_with_empty_channels_saves_only_observed_topology(
    tmp_path: Path, graph_fixture: GraphFixture
) -> None:
    """An empty channel list cannot create content or infer channel deletion."""
    _add_common_team_routes(graph_fixture)
    graph_fixture.add(
        "/v1.0/teams/team-a/allChannels" + SELECT, json_reply({"value": []})
    )
    result = crawl(
        tmp_path, graph_fixture, ["microsoft", "teams", "channel", "discover"]
    )
    if result.returncode:
        pytest.fail(result.stderr[-5000:])
    if any("/channels/" in request.target for request in graph_fixture.seen):
        pytest.fail("Empty inventories scheduled a phantom channel")
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        with catalog.Session() as session:
            topology = session.scalars(select(TeamsTopologyObservation)).all()
            if {row.resource_kind for row in topology} != {"team", "team-membership"}:
                pytest.fail("Empty channels changed the observed topology scope")
            if session.scalar(select(TeamsMessageObservation)) is not None:
                pytest.fail("Empty channels invented a message")
            if session.scalar(select(TeamsMessageDeletionObservation)) is not None:
                pytest.fail("Empty channels invented a deletion")
    finally:
        catalog.close()


def test_deleted_message_can_keep_current_hosted_bytes_without_version_claim(
    tmp_path: Path, graph_fixture: GraphFixture
) -> None:
    """Successful current hosted reads do not undo explicit message deletion."""
    _add_hosted_base(graph_fixture)
    base = "/v1.0/teams/team/channels/channel/messages"
    graph_fixture.add(
        base + "?%24top=50",
        json_reply(
            {"value": [{"id": "root", "deletedDateTime": "2026-10-04T00:00:00Z"}]}
        ),
    )
    hosted = base + "/root/hostedContents"
    graph_fixture.add(
        hosted, json_reply({"value": [{"id": "code", "contentType": "text/plain"}]})
    )
    graph_fixture.add(
        hosted + "/code", json_reply({"id": "code", "contentType": "text/plain"})
    )
    graph_fixture.add(
        hosted + "/code/$value",
        FixtureReply(
            body=b"print('retained')", headers=(("Content-Type", "text/plain"),)
        ),
    )
    result = crawl(
        tmp_path, graph_fixture, ["microsoft", "teams", "channel", "discover"]
    )
    if result.returncode:
        pytest.fail(result.stderr[-5000:])
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        with catalog.Session() as session:
            messages = session.scalars(select(TeamsMessageObservation)).all()
            deletions = session.scalars(select(TeamsMessageDeletionObservation)).all()
            byte_rows = session.scalars(
                select(TeamsHostedContentObservation).where(
                    TeamsHostedContentObservation.observation_kind == "bytes"
                )
            ).all()
            if len(messages) != 1 or len(deletions) != 1 or len(byte_rows) != 1:
                pytest.fail("Deleted message, deletion fact, or hosted bytes were lost")
            if byte_rows[0].provider_version_bound:
                pytest.fail("Current hosted bytes claimed a historical version binding")
            if byte_rows[0].trigger_evidence_id != messages[0].evidence_id:
                pytest.fail("Hosted bytes lost the triggering deleted observation")
    finally:
        catalog.close()
