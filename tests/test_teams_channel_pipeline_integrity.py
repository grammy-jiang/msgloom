"""Qualify channel integrity at native pipeline and close boundaries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from scrapy import signals
from scrapy.exceptions import DropItem
from sqlalchemy import select
from teams_support import crawl, serve_graph

from message_ingest.catalog import Catalog
from message_ingest.catalog.models.acquisition import RawHttpEvidence
from message_ingest.catalog.models.microsoft.teams import TeamsMessageObservation
from message_ingest.items.acquisition import RawHttpEvidenceItem
from message_ingest.items.microsoft.teams.message import TeamsMessageItem
from message_ingest.settings import EXTENSIONS
from tests.test_teams_channel_crawl import (
    _add_channel_routes,
    _add_common_team_routes,
)


class ChannelFailurePipeline:
    """Inject one controlled failure before raw or after semantic persistence."""

    def __init__(self, mode: str) -> None:
        self.mode = mode

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings.get("TEAMS_TEST_FAILURE_MODE"))

    def process_item(self, item: Any) -> Any:
        if self.mode == "raw":
            if isinstance(item, RawHttpEvidenceItem) and item.purpose in {
                "teams-channel-root-messages",
                "teams-channel-replies",
            }:
                raise OSError("synthetic channel evidence write failure")
            return item
        if not isinstance(item, TeamsMessageItem):
            return item
        if self.mode == "drop":
            raise DropItem("synthetic channel item drop")
        raise RuntimeError("synthetic channel item failure")


class ChannelIntegrityCapture:
    """Capture actual logical failure state after native processing drains."""

    def __init__(self, path: Path) -> None:
        self.path = path

    @classmethod
    def from_crawler(cls, crawler):
        instance = cls(Path(crawler.settings["TEAMS_TEST_INTEGRITY_PATH"]))
        crawler.signals.connect(instance.closed, signal=signals.spider_closed)
        return instance

    def closed(self, spider, reason: str) -> None:
        self.path.write_text(
            json.dumps({"run_failed": spider.run_failed, "close_reason": reason})
        )


@pytest.mark.parametrize("mode", ["error", "drop", "raw"])
def test_channel_pipeline_failure_marks_actual_run_failed(
    tmp_path: Path, mode: str
) -> None:
    """Failed raw writes cannot leave dependent message rows in the catalog.

    Late failures retain observations already written. Both late failure modes
    must still invalidate the logical run through the existing extension.
    Initial discovery has no checkpoint or absence promotion to advance.
    """
    capture = tmp_path / "integrity.json"
    pipelines = {
        "message_ingest.pipelines.evidence.RawEvidencePipeline": 200,
        "message_ingest.acquisition.evidence_link.EvidenceLinkPipeline": 250,
        "message_ingest.pipelines.microsoft.teams.TeamsPipeline": 300,
        "test_teams_channel_pipeline_integrity.ChannelFailurePipeline": (
            190 if mode == "raw" else 400
        ),
    }
    with serve_graph() as fixture:
        _add_common_team_routes(fixture)
        _add_channel_routes(fixture)
        result = crawl(
            tmp_path,
            fixture,
            ["microsoft", "teams", "channel", "discover"],
            extra_settings={
                "ITEM_PIPELINES": pipelines,
                "TEAMS_TEST_FAILURE_MODE": mode,
                "TEAMS_TEST_INTEGRITY_PATH": str(capture),
                "EXTENSIONS": {
                    **EXTENSIONS,
                    "test_teams_channel_pipeline_integrity.ChannelIntegrityCapture": 100,
                },
            },
        )
    if result.returncode != 1 or not capture.is_file():
        pytest.fail(result.stderr[-6000:])
    if json.loads(capture.read_text())["run_failed"] is not True:
        pytest.fail("Native channel pipeline failure left the logical run clean")
    reason = "item_dropped" if mode == "drop" else "item_error"
    if f"integrity_failure_reason_count/{reason}" not in result.stderr:
        pytest.fail("Existing Graph integrity extension missed the failure signal")
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        with catalog.Session() as session:
            messages = session.scalars(select(TeamsMessageObservation)).all()
            expected = 0 if mode == "raw" else 5
            if len(messages) != expected:
                pytest.fail("Channel persistence crossed the failed evidence boundary")
            for message in messages:
                evidence = session.get(RawHttpEvidence, message.evidence_id)
                if evidence is None or not Path(evidence.response_body_path).is_file():
                    pytest.fail("A persisted message has no durable raw evidence")
    finally:
        catalog.close()
