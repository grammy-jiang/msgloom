"""Qualify channel mentions and observed reaction changes through persistence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import select

from message_ingest.catalog import Catalog
from message_ingest.catalog.models.acquisition import RawHttpEvidence
from message_ingest.catalog.models.microsoft.teams import (
    TeamsMessageObservation,
    TeamsTopologyObservation,
)
from tests.teams_support import GraphFixture, crawl, json_reply
from tests.teams_support import graph_fixture as shared_graph_fixture
from tests.test_teams_channel_hosted import _add_hosted_base

graph_fixture = shared_graph_fixture


def test_channel_mentions_and_reaction_history_keep_observed_bodies_only(
    tmp_path: Path, graph_fixture: GraphFixture
) -> None:
    """An action history change creates only the actually observed version.

    Mention identities and custom emoji remain provider content. URLs in that
    content cannot authorize extra network requests or reconstruct old bodies.
    """
    _add_hosted_base(graph_fixture)
    team_detail = {
        "id": "team",
        "tenantId": "tenant",
        "displayName": "Hydrated team",
        "description": "Full team detail",
    }
    graph_fixture.add("/v1.0/teams/team", json_reply(team_detail))
    base = "/v1.0/teams/team/channels/channel/messages"
    graph_fixture.add(base + "/root/hostedContents", json_reply({"value": []}))
    mentions = [
        {
            "id": 0,
            "mentionText": "User",
            "mentioned": {"user": {"id": "same-id", "displayName": "User"}},
        },
        *[
            {
                "id": index,
                "mentionText": kind,
                "mentioned": {
                    "conversation": {
                        "id": "same-id",
                        "displayName": kind,
                        "conversationIdentityType": kind,
                    }
                },
            }
            for index, kind in enumerate(("channel", "team"), start=1)
        ],
    ]
    body = {
        "contentType": "html",
        "content": '<p><at id="0">User</at><emoji id="custom-emoji"/></p>',
    }
    original = {
        "id": "root",
        "etag": "v1",
        "body": body,
        "mentions": mentions,
        "scope": "channel",
        "webUrl": "https://teams.invalid/do-not-fetch",
        "reactions": [],
        "messageHistory": [],
    }
    updated = {
        **original,
        "etag": "v2",
        "reactions": [{"reactionType": "like", "user": {"user": {"id": "u"}}}],
        "messageHistory": [
            {
                "actions": "reactionAdded",
                "modifiedDateTime": "2026-10-04T00:00:00Z",
                "reaction": {"reactionType": "like"},
            }
        ],
    }
    for message in (original, updated):
        graph_fixture.add(base + "?%24top=50", json_reply({"value": [message]}))
        result = crawl(
            tmp_path, graph_fixture, ["microsoft", "teams", "channel", "discover"]
        )
        if result.returncode:
            pytest.fail(result.stderr[-5000:])
    if any("do-not-fetch" in request.target for request in graph_fixture.seen):
        pytest.fail("Message webUrl became an unauthorized crawl target")

    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        with catalog.Session() as session:
            rows = session.scalars(
                select(TeamsMessageObservation).order_by(
                    TeamsMessageObservation.observation_id
                )
            ).all()
            teams = session.scalars(
                select(TeamsTopologyObservation).where(
                    TeamsTopologyObservation.resource_kind == "team"
                )
            ).all()
            details = [
                row for row in teams if row.context.get("representation") == "detail"
            ]
            if len(details) != 2 or any(row.raw != team_detail for row in details):
                pytest.fail("Full team hydration was not retained beside discovery")
            if {row.context.get("representation") for row in teams} != {
                "associated",
                "joined",
                "detail",
            }:
                pytest.fail("Team discovery and hydration representations collapsed")
            if [row.raw for row in rows] != [original, updated]:
                pytest.fail("Observed reaction versions changed or invented old bodies")
            for row in rows:
                evidence = session.get(RawHttpEvidence, row.evidence_id)
                if evidence is None:
                    pytest.fail("Channel version lacks committed raw evidence")
                raw = json.loads(Path(evidence.response_body_path).read_bytes())
                if raw != {"value": [row.raw]}:
                    pytest.fail("Channel observation differs from saved provider bytes")
            if len({row.evidence_id for row in rows}) != 2:
                pytest.fail("Repeated acquisition did not preserve separate captures")
    finally:
        catalog.close()
