"""Exercise Teams chat failure paths through native Scrapy integrity signals."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from scrapy.exceptions import DropItem
from sqlalchemy import select
from teams_support import GraphFixture, crawl, json_reply

from message_ingest.catalog.models.acquisition import RawHttpEvidence
from message_ingest.catalog.models.microsoft.teams import TeamsMessageObservation
from message_ingest.catalog.store import Catalog
from message_ingest.items.microsoft.teams.message import TeamsMessageItem

pytest_plugins = ("teams_support",)

CHAT_SETTINGS = {"SPIDER_MODULES": "message_ingest.spiders.microsoft.teams"}


class LateTeamsFailurePipeline:
    """Inject a post-persistence item error or drop for real signal coverage."""

    def __init__(self, mode: str) -> None:
        self.mode = mode

    @classmethod
    def from_crawler(cls, crawler):
        """Read one test-only failure mode from crawler settings."""
        return cls(crawler.settings.get("TEAMS_TEST_FAILURE_MODE", ""))

    def process_item(self, item: Any) -> Any:
        """Fail only the final Teams message semantic item."""
        if not isinstance(item, TeamsMessageItem):
            return item
        if self.mode == "error":
            raise RuntimeError("synthetic Teams late item failure")
        if self.mode == "drop":
            raise DropItem("synthetic Teams late item drop")
        return item


def _run(
    tmp_path: Path,
    fixture: GraphFixture,
    *,
    extra_settings: dict[str, object] | None = None,
):
    settings: dict[str, object] = dict(CHAT_SETTINGS)
    settings.update(extra_settings or {})
    return crawl(
        tmp_path,
        fixture,
        ["crawl", "microsoft_teams_chat_discover"],
        extra_settings=settings,
    )


def _catalog(tmp_path: Path) -> Catalog:
    return Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")


def _one_message_routes(fixture: GraphFixture) -> None:
    fixture.add(
        "/v1.0/me/chats?%24top=50",
        json_reply({"value": [{"id": "chat-integrity", "chatType": "group"}]}),
    )
    fixture.add("/v1.0/chats/chat-integrity/members", json_reply({"value": []}))
    fixture.add(
        "/v1.0/chats/chat-integrity/messages?%24top=50",
        json_reply(
            {
                "value": [
                    {
                        "id": "message-integrity",
                        "etag": "etag-integrity",
                        "body": {"contentType": "text", "content": "payload"},
                    }
                ]
            }
        ),
    )
    fixture.add(
        "/v1.0/chats/chat-integrity/messages/message-integrity/hostedContents",
        json_reply({"value": []}),
    )
    fixture.add(
        "/v1.0/chats/chat-integrity/pinnedMessages",
        json_reply({"value": []}),
    )


def test_malformed_collection_keeps_raw_evidence_and_marks_callback_failure(
    tmp_path: Path,
    graph_fixture: GraphFixture,
) -> None:
    """Raw evidence must survive a collection-envelope parser exception."""
    graph_fixture.add(
        "/v1.0/me/chats?%24top=50",
        json_reply({"value": {"not": "a list"}}),
    )

    result = _run(tmp_path, graph_fixture)
    if result.returncode != 0:
        pytest.fail(result.stderr)
    reason = "'msgloom/crawl/integrity_failure_reason_count/spider_error': 1"
    if reason not in result.stderr:
        pytest.fail("Malformed callback output did not mark spider_error")

    catalog = _catalog(tmp_path)
    try:
        with catalog.Session() as session:
            evidence = session.scalar(
                select(RawHttpEvidence).where(
                    RawHttpEvidence.purpose == "teams-chat-list"
                )
            )
        if evidence is None or evidence.response_status != 200:
            pytest.fail("Malformed Graph response raw evidence was not durable")
        if b'"not": "a list"' not in Path(evidence.response_body_path).read_bytes():
            pytest.fail("Malformed provider payload was not retained in raw evidence")
    finally:
        catalog.close()


@pytest.mark.parametrize(
    ("status", "expected_hits"),
    [
        (403, 1),
        (503, 3),
    ],
)
def test_terminal_request_failure_uses_native_retry_and_inherited_errback(
    tmp_path: Path,
    graph_fixture: GraphFixture,
    status: int,
    expected_hits: int,
) -> None:
    """Terminal HTTP failures retain final evidence and inherited integrity."""
    target = "/v1.0/me/chats?%24top=50"
    graph_fixture.add(
        target,
        json_reply({"error": {"code": "FixtureFailure"}}, status=status),
    )

    retry_settings: dict[str, object] = {}
    if status == 503:
        retry_settings = {
            "MS_GRAPH_ERROR_MAX_RETRIES": 2,
            "MS_GRAPH_ERROR_FALLBACK_BASE_SECONDS": 0,
            "MS_GRAPH_ERROR_FALLBACK_MAX_SECONDS": 0,
        }
    result = _run(
        tmp_path,
        graph_fixture,
        extra_settings=retry_settings,
    )
    if result.returncode != 0:
        pytest.fail(result.stderr)
    reason = (
        "'msgloom/crawl/integrity_failure_reason_count/"
        "request_failure:teams-chat-list': 1"
    )
    if reason not in result.stderr:
        pytest.fail("Terminal request failure did not mark inherited run integrity")
    hits = [seen for seen in graph_fixture.seen if seen.target == target]
    if len(hits) != expected_hits:
        pytest.fail("Teams request failure bypassed native retry ownership")
    if any(seen.header("Authorization") for seen in hits):
        pytest.fail("Fixture-only auth-none crawl unexpectedly sent Authorization")

    catalog = _catalog(tmp_path)
    try:
        with catalog.Session() as session:
            evidence = session.scalars(
                select(RawHttpEvidence).where(
                    RawHttpEvidence.purpose == "teams-chat-list"
                )
            ).all()
        if len(evidence) != 1 or evidence[0].response_status != status:
            pytest.fail("Inherited errback did not retain the final HTTP exchange")
    finally:
        catalog.close()


@pytest.mark.parametrize(
    ("mode", "reason"),
    [
        ("error", "item_error"),
        ("drop", "item_dropped"),
    ],
)
def test_late_pipeline_failure_marks_run_failed(
    tmp_path: Path,
    graph_fixture: GraphFixture,
    mode: str,
    reason: str,
) -> None:
    """Real item_error/item_dropped signals fail integrity after semantic write."""
    _one_message_routes(graph_fixture)
    pipelines = {
        "message_ingest.pipelines.evidence.RawEvidencePipeline": 200,
        "message_ingest.acquisition.evidence_link.EvidenceLinkPipeline": 250,
        "message_ingest.pipelines.microsoft.teams.TeamsPipeline": 300,
        "test_teams_chat_integrity.LateTeamsFailurePipeline": 400,
    }
    result = _run(
        tmp_path,
        graph_fixture,
        extra_settings={
            "ITEM_PIPELINES": pipelines,
            "TEAMS_TEST_FAILURE_MODE": mode,
        },
    )
    if result.returncode != 0:
        pytest.fail(result.stderr)
    expected = f"'msgloom/crawl/integrity_failure_reason_count/{reason}': 1"
    if expected not in result.stderr:
        pytest.fail(f"Late Teams {mode} did not mark {reason}")

    catalog = _catalog(tmp_path)
    try:
        with catalog.Session() as session:
            rows = session.scalars(select(TeamsMessageObservation)).all()
        if len(rows) != 1:
            pytest.fail("Late failure test did not pass through real Teams persistence")
    finally:
        catalog.close()


def test_jobdir_is_rejected_before_any_fixture_request(
    tmp_path: Path,
    graph_fixture: GraphFixture,
) -> None:
    """Unsupported scheduler persistence must fail before network activity."""
    graph_fixture.add(
        "/v1.0/me/chats?%24top=50",
        json_reply({"value": []}),
    )
    result = _run(
        tmp_path,
        graph_fixture,
        extra_settings={"JOBDIR": str(tmp_path / "jobdir")},
    )
    if result.returncode == 0:
        pytest.fail("Teams chat crawl unexpectedly accepted JOBDIR")
    if graph_fixture.seen:
        pytest.fail("JOBDIR rejection occurred after a Graph request")
    if "Teams discovery does not support JOBDIR yet" not in result.stderr:
        pytest.fail("JOBDIR rejection did not expose the shared Teams contract")
