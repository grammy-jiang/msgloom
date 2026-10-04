"""Prove evidence ordering through a real delayed native Teams crawl."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import select

from message_ingest.catalog.models.microsoft.teams import TeamsMessageObservation
from message_ingest.catalog.store import Catalog
from tests.teams_support import GraphFixture, crawl, json_reply
from tests.teams_support import graph_fixture as shared_graph_fixture

graph_fixture = shared_graph_fixture


def _routes(fixture: GraphFixture) -> None:
    """Serve one actual production message callback and its follow-up reads."""
    fixture.add(
        "/v1.0/me/chats?%24top=50",
        json_reply({"value": [{"id": "chat-order", "chatType": "group"}]}),
    )
    for suffix in (
        "members",
        "pinnedMessages",
        "messages/message-order/hostedContents",
    ):
        fixture.add(f"/v1.0/chats/chat-order/{suffix}", json_reply({"value": []}))
    fixture.add(
        "/v1.0/chats/chat-order/messages?%24top=50",
        json_reply(
            {"value": [{"id": "message-order", "body": {"content": "ordering"}}]}
        ),
    )


@pytest.mark.parametrize("broken_control", [False, True], ids=["serial", "broken"])
def test_native_delayed_evidence_precedes_semantic_entry(
    tmp_path: Path,
    graph_fixture: GraphFixture,
    broken_control: bool,
) -> None:
    """Hold evidence and detect overtaking before any semantic store call.

    The broken case changes only the subprocess's native scraper concurrency
    after initialization. It qualifies this probe by demonstrating the precise
    failure that serial callback output prevents. It must fail logical run
    integrity and must not create a message observation.
    """
    _routes(graph_fixture)
    trace = tmp_path / "ordering.jsonl"
    result = crawl(
        tmp_path,
        graph_fixture,
        ["crawl", "microsoft_teams_chat_discover"],
        extra_settings={
            "SPIDER_MODULES": "message_ingest.spiders.microsoft.teams",
            "TEAMS_ORDER_TRACE": str(trace),
            "TEAMS_ORDER_BROKEN_CONTROL": broken_control,
            "ITEM_PIPELINES": {
                "teams_ordering_support.DelayedRawEvidencePipeline": 200,
                "teams_ordering_support.EntryEvidenceLinkPipeline": 250,
                "message_ingest.pipelines.microsoft.teams.TeamsPipeline": 300,
            },
        },
    )
    if result.returncode or not trace.exists():
        pytest.fail(f"Native ordering crawl did not execute: {result.stderr}")
    events = [json.loads(line) for line in trace.read_text().splitlines()]
    ids = {evidence_id for _, evidence_id in events}
    if len(ids) != 1:
        pytest.fail(f"Expected one instrumented message page: {events!r}")
    names = [event for event, _ in events]
    expected = (
        ["held", "semantic-enter", "overtook", "released", "committed"]
        if broken_control
        else ["held", "released", "committed", "semantic-enter", "semantic-ready"]
    )
    if names != expected:
        pytest.fail(f"Wrong native item boundary order: {names!r}")
    failed = "msgloom/crawl/integrity_failure_reason_count/item_error" in result.stderr
    if failed != broken_control:
        pytest.fail("Ordering failure did not match native run-integrity outcome")
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        with catalog.Session() as session:
            rows = session.scalars(select(TeamsMessageObservation)).all()
        if len(rows) != (0 if broken_control else 1):
            pytest.fail("Unexpected semantic storage after the native entry probe")
        if rows and rows[0].evidence_id not in ids:
            pytest.fail("Semantic storage lost the entry-verified evidence ID")
    finally:
        catalog.close()
