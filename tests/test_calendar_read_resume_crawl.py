"""Exercise native JOBDIR pause/resume for Calendar window and full reads."""

from __future__ import annotations

import pickle
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import select
from test_calendar_crawls import (
    END,
    ROOT,
    START,
    WINDOW_COMMAND,
)
from test_calendar_crawls import (
    _settings as window_settings,
)
from test_calendar_crawls import calendar_server as calendar_server  # noqa: PLC0414
from test_calendar_full_crawl import FULL_COMMAND
from test_calendar_full_crawl import _settings as full_settings
from test_calendar_full_crawl import (
    calendar_full_server as calendar_full_server,  # noqa: PLC0414
)

from message_ingest.catalog import CalendarEventObservation, Catalog

WINDOW_PAUSE_SETUP = r"""
import asyncio
from scrapy import signals

original_factory = OutlookCalendarWindowSpider.from_crawler

def factory(cls, crawler, *args, **kwargs):
    spider = original_factory(crawler, *args, **kwargs)

    def pause(request, **kwargs):
        if "$skiptoken=window-page-2" in request.url:
            crawler.engine.pause()
            asyncio.create_task(crawler.engine.close_spider_async(reason="paused"))

    crawler.signals.connect(pause, signal=signals.request_scheduled, weak=False)
    return spider

OutlookCalendarWindowSpider.from_crawler = classmethod(factory)
"""

FULL_PAUSE_SETUP = r"""
import asyncio
from scrapy import signals

original_factory = OutlookCalendarFullSpider.from_crawler

def factory(cls, crawler, *args, **kwargs):
    spider = original_factory(crawler, *args, **kwargs)

    def pause(request, **kwargs):
        if request.cb_kwargs.get("purpose") == "calendar-event-attachments":
            crawler.engine.pause()
            asyncio.create_task(crawler.engine.close_spider_async(reason="paused"))

    crawler.signals.connect(pause, signal=signals.request_scheduled, weak=False)
    return spider

OutlookCalendarFullSpider.from_crawler = classmethod(factory)
"""


def _window_run(graph_root: str, tmp_path: Path, *, setup: str = ""):
    script = WINDOW_COMMAND.replace("execute([", setup + "\nexecute([")
    return subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            graph_root,
            "--start",
            START,
            "--end",
            END,
            "-s",
            f"JOBDIR={tmp_path / 'window-job'}",
            "-s",
            "SCHEDULER_DEBUG=True",
            *window_settings(tmp_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def _full_run(graph_root: str, tmp_path: Path, *, setup: str = ""):
    script = FULL_COMMAND.replace("execute([", setup + "\nexecute([")
    return subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            graph_root,
            "-s",
            f"JOBDIR={tmp_path / 'full-job'}",
            "-s",
            "SCHEDULER_DEBUG=True",
            *full_settings(tmp_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def test_calendar_window_clean_pause_resumes_saved_continuation_only(
    tmp_path: Path,
    calendar_server,
) -> None:
    graph_root, seen = calendar_server
    paused = _window_run(graph_root, tmp_path, setup=WINDOW_PAUSE_SETUP)
    if paused.returncode != 0 or "ERROR" in paused.stderr:
        pytest.fail(paused.stderr)
    if len(seen) != 1 or "$skiptoken" in seen[0]:
        pytest.fail(f"Expected only the initial Calendar window page: {seen!r}")

    state_path = tmp_path / "window-job" / "spider.state"
    with state_path.open("rb") as handle:
        run_id = pickle.load(handle)["msgloom_calendar_window"]["run_id"]

    resumed = _window_run(graph_root, tmp_path)
    if resumed.returncode != 0 or "ERROR" in resumed.stderr:
        pytest.fail(resumed.stderr)
    if len(seen) != 2 or "$skiptoken=window-page-2" not in seen[-1]:
        pytest.fail(f"Expected only saved continuation on resume: {seen!r}")
    if "scheduler/unserializable" in resumed.stderr:
        pytest.fail("Calendar window continuation must stay in the disk queue")

    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        with catalog.Session() as session:
            observations = session.scalars(select(CalendarEventObservation)).all()
            if len(observations) != 3:
                pytest.fail("Expected all Calendar window events after resume")
            if {row.run_id for row in observations} != {run_id}:
                pytest.fail("Window resume must retain one logical run identity")
    finally:
        catalog.close()


def test_calendar_full_clean_pause_resumes_attachment_work_without_refetch_detail(
    tmp_path: Path,
    calendar_full_server,
) -> None:
    graph_root, seen = calendar_full_server
    paused = _full_run(graph_root, tmp_path, setup=FULL_PAUSE_SETUP)
    if paused.returncode != 0 or "ERROR" in paused.stderr:
        pytest.fail(paused.stderr)
    detail_path = "/v1.0/me/events/event-1"
    if [path.split("?", 1)[0] for path in seen].count(detail_path) != 1:
        pytest.fail(f"Expected exactly one event detail before pause: {seen!r}")

    state_path = tmp_path / "full-job" / "spider.state"
    with state_path.open("rb") as handle:
        run_id = pickle.load(handle)["msgloom_calendar_full"]["run_id"]

    resumed = _full_run(graph_root, tmp_path)
    if resumed.returncode != 0 or "ERROR" in resumed.stderr:
        pytest.fail(resumed.stderr)
    paths = [path.split("?", 1)[0] for path in seen]
    if paths.count(detail_path) != 1:
        pytest.fail(
            f"Persistent dupefilter must suppress refetched event detail: {seen!r}"
        )
    if "/v1.0/me/events/event-1/attachments" not in paths:
        pytest.fail("Expected resumed Calendar attachment inventory")
    if "scheduler/unserializable" in resumed.stderr:
        pytest.fail("Calendar full follow-up requests must stay in the disk queue")

    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        with catalog.Session() as session:
            observations = session.scalars(select(CalendarEventObservation)).all()
            if len(observations) != 1 or observations[0].run_id != run_id:
                pytest.fail(
                    "Calendar full resume must retain the original run identity"
                )
    finally:
        catalog.close()
