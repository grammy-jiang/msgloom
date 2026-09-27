"""Exercise Calendar checkpoint gates through real Scrapy lifecycle paths."""

from __future__ import annotations

import pickle
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import select

from message_ingest.catalog import (
    CalendarDeltaCheckpoint,
    CalendarDeltaCheckpointCandidate,
    CalendarDeltaObservation,
    Catalog,
)
from test_calendar_delta_crawl import (
    DELTA_COMMAND,
    END,
    ROOT,
    START,
    _settings,
    calendar_delta_server as calendar_delta_server,
)

PAUSE_SETUP = r'''
import asyncio
from scrapy import signals

original_factory = OutlookCalendarDeltaSpider.from_crawler

def factory(cls, crawler, *args, **kwargs):
    spider = original_factory(crawler, *args, **kwargs)

    def pause(request, **kwargs):
        if request.cb_kwargs.get("page_number") == 2:
            crawler.engine.pause()
            asyncio.create_task(crawler.engine.close_spider_async(reason="paused"))

    crawler.signals.connect(pause, signal=signals.request_scheduled, weak=False)
    return spider

OutlookCalendarDeltaSpider.from_crawler = classmethod(factory)
'''

FAILURE_SETUP = r'''
import asyncio
from scrapy.exceptions import DropItem
from message_ingest.items import OutlookCalendarEventItem
from message_ingest.pipelines.calendar import CalendarPipeline

original_process = CalendarPipeline.process_item

async def process(self, item):
    if isinstance(item, OutlookCalendarEventItem):
        await asyncio.sleep(0.05)
        raise FAILURE_TYPE("injected late persistence failure")
    return await original_process(self, item)

CalendarPipeline.process_item = process
'''


def _run(graph_root: str, tmp_path: Path, *, setup="", start=START):
    script = DELTA_COMMAND.replace("execute([", setup + "\nexecute([")
    return subprocess.run(
        [
            sys.executable, "-c", script, graph_root,
            "--start", start, "--end", END,
            "-s", f"JOBDIR={tmp_path / 'job'}",
            "-s", "SCHEDULER_DEBUG=True", *_settings(tmp_path),
        ],
        cwd=ROOT, capture_output=True, text=True, timeout=30, check=False,
    )


def _catalog(tmp_path: Path) -> Catalog:
    return Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")


def _pause(graph_root: str, tmp_path: Path, seen: list[str]) -> str:
    result = _run(graph_root, tmp_path, setup=PAUSE_SETUP)
    if result.returncode != 0 or "ERROR" in result.stderr:
        pytest.fail(result.stderr)
    if len(seen) != 1:
        pytest.fail(f"Expected one response before a clean pause: {seen!r}")
    catalog = _catalog(tmp_path)
    try:
        with catalog.Session() as session:
            if session.scalar(select(CalendarDeltaCheckpoint)) is not None:
                pytest.fail("A paused traversal must not promote a checkpoint")
    finally:
        catalog.close()
    with (tmp_path / "job" / "spider.state").open("rb") as handle:
        return pickle.load(handle)["msgloom_calendar_delta"]["run_id"]


def test_clean_pause_resumes_queued_page_and_promotes_once(
    tmp_path: Path, calendar_delta_server,
) -> None:
    graph_root, seen = calendar_delta_server
    run_id = _pause(graph_root, tmp_path, seen)
    result = _run(graph_root, tmp_path)
    if result.returncode != 0 or "ERROR" in result.stderr:
        pytest.fail(result.stderr)
    if len(seen) != 2 or "$skiptoken=page2" not in seen[-1]:
        pytest.fail("Expected resume of the saved continuation only")
    if "scheduler/unserializable" in result.stderr:
        pytest.fail("Calendar requests must stay in the native disk queue")
    catalog = _catalog(tmp_path)
    try:
        with catalog.Session() as session:
            checkpoint = session.scalar(select(CalendarDeltaCheckpoint))
            if checkpoint is None or checkpoint.revision != 1:
                pytest.fail("Expected one checkpoint after resumed completion")
            if checkpoint.run_id != run_id:
                pytest.fail("Resume must retain the original run identity")
            rows = session.scalars(select(CalendarDeltaObservation)).all()
            if len(rows) != 2 or {row.run_id for row in rows} != {run_id}:
                pytest.fail("Both processes must persist one logical round")
    finally:
        catalog.close()


def test_changed_window_cannot_dequeue_or_destroy_a_saved_job(
    tmp_path: Path, calendar_delta_server,
) -> None:
    graph_root, seen = calendar_delta_server
    _pause(graph_root, tmp_path, seen)
    state_path = tmp_path / "job" / "spider.state"
    before = state_path.read_bytes()
    rejected = _run(graph_root, tmp_path, start="2026-09-28T00:00:00+10:00")
    if rejected.returncode == 0:
        pytest.fail("A changed Calendar window must fail the public command")
    if len(seen) != 1 or state_path.read_bytes() != before:
        pytest.fail("Rejected startup must retain the queue and original state")
    resumed = _run(graph_root, tmp_path)
    if resumed.returncode != 0 or len(seen) != 2:
        pytest.fail(f"Original window must still resume:\n{resumed.stderr}")


@pytest.mark.parametrize("failure_type", ["RuntimeError", "DropItem"])
def test_delayed_pipeline_failure_blocks_durable_candidate(
    tmp_path: Path, calendar_delta_server, failure_type: str,
) -> None:
    graph_root, _seen = calendar_delta_server
    result = _run(
        graph_root, tmp_path,
        setup=FAILURE_SETUP.replace("FAILURE_TYPE", failure_type),
    )
    if result.returncode == 0:
        pytest.fail("Pipeline failure must fail the public Calendar command")
    catalog = _catalog(tmp_path)
    try:
        with catalog.Session() as session:
            candidate = session.scalar(select(CalendarDeltaCheckpointCandidate))
            if candidate is None or candidate.committed_at is not None:
                pytest.fail("Expected a durable but uncommitted terminal cursor")
            if session.scalar(select(CalendarDeltaCheckpoint)) is not None:
                pytest.fail("Failed item processing must block promotion")
    finally:
        catalog.close()
