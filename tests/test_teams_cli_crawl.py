"""Qualify public Teams commands through native crawls and durable evidence."""

from pathlib import Path

import pytest
from sqlalchemy import select
from teams_support import crawl, json_reply, serve_graph

from message_ingest.catalog import Catalog
from message_ingest.catalog.models.acquisition import RawHttpEvidence


@pytest.mark.parametrize(
    ("resource", "targets"),
    [
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
