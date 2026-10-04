"""Qualify public Teams commands through native crawls and durable evidence."""

from pathlib import Path

import pytest
from sqlalchemy import select
from teams_support import crawl, json_reply, serve_graph

from message_ingest.catalog import Catalog
from message_ingest.catalog.models.acquisition import RawHttpEvidence
from message_ingest.catalog.models.microsoft.teams import TeamsMessageObservation


@pytest.mark.parametrize(
    ("resource", "targets"),
    [
        ("chat", ("/v1.0/me/chats?%24top=50",)),
        (
            "channel",
            ("/v1.0/me/teamwork/associatedTeams", "/v1.0/me/joinedTeams"),
        ),
    ],
)
def test_public_teams_discovery_persists_empty_inventory(
    tmp_path: Path, resource: str, targets: tuple[str, ...]
) -> None:
    """Native command dispatch must discover spiders without test overrides."""
    with serve_graph() as fixture:
        for target in targets:
            fixture.add(target, json_reply({"value": []}))
        result = crawl(
            tmp_path,
            fixture,
            ["microsoft", "teams", resource, "discover"],
        )
        if result.returncode or "ERROR" in result.stderr:
            pytest.fail(result.stderr[-6000:])
        if sorted(seen.target for seen in fixture.seen) != sorted(targets):
            pytest.fail("Public Teams command did not traverse its exact roots")
        if any(seen.header("Authorization") for seen in fixture.seen):
            pytest.fail("Local fixture received an authorization credential")
        expected_urls = {fixture.url(target) for target in targets}
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        with catalog.Session() as session:
            rows = session.scalars(select(RawHttpEvidence)).all()
            if len(rows) != len(targets):
                pytest.fail("Each empty root must retain a separate raw response")
            if {row.request_url for row in rows} != expected_urls:
                pytest.fail("Persisted root URLs differ from the fixture requests")
            for row in rows:
                if row.source_id != "teams-fixture" or row.response_status != 200:
                    pytest.fail("Public command lost source or response provenance")
                if Path(row.response_body_path).read_bytes() != b'{"value": []}':
                    pytest.fail("Persisted response bytes changed")
    finally:
        catalog.close()


def test_public_chat_command_links_message_to_durable_evidence(tmp_path: Path) -> None:
    """Exercise command mapping, default discovery, and all three pipelines."""
    message = {"id": "message", "etag": "v1", "body": {"content": "saved"}}
    routes = {
        "/v1.0/me/chats?%24top=50": {"value": [{"id": "chat", "chatType": "group"}]},
        "/v1.0/chats/chat/members": {"value": []},
        "/v1.0/chats/chat/messages?%24top=50": {"value": [message]},
        "/v1.0/chats/chat/pinnedMessages": {"value": []},
        "/v1.0/chats/chat/messages/message/hostedContents": {"value": []},
    }
    with serve_graph() as fixture:
        for target, payload in routes.items():
            fixture.add(target, json_reply(payload))
        result = crawl(tmp_path, fixture, ["microsoft", "teams", "chat", "discover"])
        if result.returncode or "ERROR" in result.stderr:
            pytest.fail(result.stderr[-6000:])
        if sorted(seen.target for seen in fixture.seen) != sorted(routes):
            pytest.fail("Public chat discovery missed or invented a follow-up")
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        with catalog.Session() as session:
            rows = session.scalars(select(TeamsMessageObservation)).all()
            if len(rows) != 1 or rows[0].raw != message:
                pytest.fail("Public command did not persist the message observation")
            evidence = session.get(RawHttpEvidence, rows[0].evidence_id)
            if evidence is None or evidence.source_id != rows[0].source_id:
                pytest.fail("Message has no committed same-source evidence")
            if evidence.observed_at != rows[0].observed_at:
                pytest.fail("Message evidence capture time differs")
            if rows[0].source_id != "teams-fixture":
                pytest.fail("Public command ignored the explicit source setting")
            if not Path(evidence.response_body_path).is_file():
                pytest.fail("Message evidence payload was not persisted")
    finally:
        catalog.close()


def test_public_channel_command_rejects_jobdir_before_network(tmp_path: Path) -> None:
    """Unsupported resume fails at the public command before provider access."""
    with serve_graph() as fixture:
        result = crawl(
            tmp_path,
            fixture,
            ["microsoft", "teams", "channel", "discover"],
            extra_settings={"JOBDIR": str(tmp_path / "job")},
        )
        if result.returncode == 0:
            pytest.fail("Public channel command accepted unsupported JOBDIR")
        if fixture.seen:
            pytest.fail("Channel JOBDIR rejection happened after provider access")
        if "Teams discovery does not support JOBDIR" not in result.stderr:
            pytest.fail("Channel command failed for an unrelated reason")
