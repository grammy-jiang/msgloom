"""Exercise hosted metadata/bytes and explicit hosted retrieval failures."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from sqlalchemy import select

from message_ingest.catalog.models.microsoft.teams import (
    TeamsHostedContentObservation,
    TeamsReferenceResolutionObservation,
)
from message_ingest.catalog.store import Catalog
from tests.teams_support import FixtureReply, GraphFixture, crawl, json_reply
from tests.teams_support import graph_fixture as shared_graph_fixture

graph_fixture = shared_graph_fixture

SELECT = (
    "?%24select=id%2CcreatedDateTime%2CdisplayName%2Cdescription%2CisArchived"
    "%2CisFavoriteByDefault%2ClayoutType%2CmembershipType%2CmigrationMode"
    "%2CoriginalCreatedDateTime%2CtenantId%2CwebUrl"
)


def _add_hosted_base(fixture: GraphFixture) -> None:
    team = {"id": "team", "tenantId": "tenant"}
    channel = {
        "id": "channel",
        "tenantId": "tenant",
        "membershipType": "standard",
        "layoutType": None,
    }
    fixture.add("/v1.0/me/teamwork/associatedTeams", json_reply({"value": [team]}))
    fixture.add("/v1.0/me/joinedTeams", json_reply({"value": [team]}))
    fixture.add("/v1.0/teams/team", json_reply(team))
    fixture.add("/v1.0/teams/team/members?%24top=999", json_reply({"value": []}))
    fixture.add(
        "/v1.0/teams/team/allChannels" + SELECT,
        json_reply({"value": [channel]}),
    )
    fixture.add(
        "/v1.0/teams/team/incomingChannels" + SELECT,
        json_reply({"value": []}),
    )
    fixture.add(
        "/v1.0/teams/team/channels/channel" + SELECT,
        json_reply({**channel, "layoutType": "posts"}),
    )
    fixture.add(
        "/v1.0/teams/team/channels/channel/members?%24top=999",
        json_reply({"value": []}),
    )
    fixture.add(
        "/v1.0/teams/team/channels/channel/allMembers",
        json_reply({"value": []}),
    )
    fixture.add(
        "/v1.0/teams/team/channels/channel/messages?%24top=50",
        json_reply(
            {
                "value": [
                    {
                        "id": "root",
                        "attachments": [
                            {
                                "id": "file",
                                "contentType": "reference",
                                "contentUrl": "https://sharepoint.example/file",
                            }
                        ],
                    }
                ]
            }
        ),
    )
    fixture.add(
        "/v1.0/teams/team/channels/channel/messages/root/replies?%24top=50",
        json_reply({"value": []}),
    )


def test_hosted_bytes_match_raw_response_and_file_reference_is_not_attempted(
    tmp_path: Path,
    graph_fixture: GraphFixture,
) -> None:
    _add_hosted_base(graph_fixture)
    base = "/v1.0/teams/team/channels/channel/messages/root/hostedContents"
    graph_fixture.add(
        base,
        json_reply({"value": [{"id": "hosted", "contentType": "image/png"}]}),
    )
    graph_fixture.add(
        base + "/hosted",
        json_reply({"id": "hosted", "contentType": "image/png"}),
    )
    body = b"\x89PNG\r\nfixture-bytes"
    graph_fixture.add(
        base + "/hosted/$value",
        FixtureReply(
            body=body,
            headers=(("Content-Type", "image/png"),),
        ),
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

    detail_seen = [
        request
        for request in graph_fixture.seen
        if request.target in {base + "/hosted", base + "/hosted/$value"}
    ]
    if len(detail_seen) != 2:
        pytest.fail("Hosted current metadata and byte reads were not both issued")
    if any(
        request.header("ConsistencyLevel") != ("eventual",) for request in detail_seen
    ):
        pytest.fail("Hosted current reads lost eventual-consistency representation")
    byte_request = next(
        request for request in detail_seen if request.target.endswith("/$value")
    )
    if byte_request.header("Accept") != ("application/octet-stream",):
        pytest.fail("Hosted byte request lost its binary Accept representation")

    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        with catalog.Session() as session:
            hosted = session.scalars(select(TeamsHostedContentObservation)).all()
            references = session.scalars(
                select(TeamsReferenceResolutionObservation)
            ).all()
        byte_rows = [row for row in hosted if row.observation_kind == "bytes"]
        if len(byte_rows) != 1:
            pytest.fail("Hosted byte response was not persisted exactly once")
        row = byte_rows[0]
        if (
            row.content_sha256 != hashlib.sha256(body).hexdigest()
            or row.content_bytes != len(body)
            or row.provider_version_bound
        ):
            pytest.fail("Hosted byte digest/length or version binding is incorrect")
        if len(references) != 1 or references[0].state != "not-attempted":
            pytest.fail("File reference must remain explicitly not-attempted")
        if any(
            "sharepoint.example" in request.target for request in graph_fixture.seen
        ):
            pytest.fail("Spider fetched an arbitrary attachment URL")
    finally:
        catalog.close()


def test_hosted_byte_failure_persists_failure_and_marks_run_failed(
    tmp_path: Path,
    graph_fixture: GraphFixture,
) -> None:
    _add_hosted_base(graph_fixture)
    graph_fixture.add(
        "/v1.0/teams/team/channels/channel/messages?%24top=50",
        json_reply(
            {
                "value": [
                    {
                        "id": "root",
                        "deletedDateTime": "2026-10-04T00:00:00Z",
                    }
                ]
            }
        ),
    )
    base = "/v1.0/teams/team/channels/channel/messages/root/hostedContents"
    graph_fixture.add(base, json_reply({"value": [{"id": "gone"}]}))
    graph_fixture.add(base + "/gone", json_reply({"id": "gone"}))
    graph_fixture.add(
        base + "/gone/$value",
        json_reply({"error": {"code": "NotFound"}}, status=404),
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
    if "request_failure:teams-channel-hosted-content-bytes" not in result.stderr:
        pytest.fail("Hosted terminal failure did not mark run integrity failed")

    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        with catalog.Session() as session:
            rows = session.scalars(select(TeamsHostedContentObservation)).all()
        failures = [row for row in rows if row.observation_kind == "failure"]
        if len(failures) != 1:
            pytest.fail("Hosted terminal failure must persist one limitation fact")
        if failures[0].hosted_content_id != "gone" or failures[0].status_code != 404:
            pytest.fail("Hosted failure lost provider content identity/status")
    finally:
        catalog.close()
