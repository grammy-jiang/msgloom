"""Run Calendar delta twice through real Scrapy crawls."""

from __future__ import annotations

import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urlsplit

import pytest
from sqlalchemy import func, select

from message_ingest.catalog import (
    CalendarDeltaCheckpoint,
    CalendarDeltaEventState,
    CalendarDeltaObservation,
    CalendarEventObservation,
    CalendarEventRecord,
    Catalog,
    RawHttpEvidence,
)

ROOT = Path(__file__).parents[1]
START = "2026-09-27T00:00:00+10:00"
END = "2026-10-04T00:00:00+10:00"

DELTA_COMMAND = r"""
import sys
from scrapy.cmdline import execute
from message_ingest.spiders.outlook_calendar_delta import OutlookCalendarDeltaSpider

OutlookCalendarDeltaSpider.graph_root = sys.argv[1]
OutlookCalendarDeltaSpider.allowed_domains = ["127.0.0.1"]
execute([
    "scrapy",
    "microsoft",
    "outlook",
    "calendar",
    "delta",
    *sys.argv[2:],
])
"""


@pytest.fixture
def calendar_delta_server():
    requests_seen: list[str] = []
    graph_root = ""

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:
            pass

        def do_GET(self) -> None:
            nonlocal graph_root
            parsed = urlsplit(self.path)
            query = parse_qs(parsed.query)
            requests_seen.append(self.path)

            if parsed.path != "/v1.0/me/calendarView/delta":
                self.send_response(404)
                self.end_headers()
                return

            if "$deltatoken" in query:
                if query["$deltatoken"] != ["round1"]:
                    self.send_error(400, "unexpected delta token")
                    return
                self._json(
                    {
                        "value": [
                            {
                                "id": "event-1",
                                "changeKey": "e1-v2",
                                "subject": "Meeting moved",
                                "type": "singleInstance",
                                "isAllDay": False,
                                "isCancelled": False,
                                "start": {
                                    "dateTime": "2026-09-28T11:00:00",
                                    "timeZone": "UTC",
                                },
                                "end": {
                                    "dateTime": "2026-09-28T12:00:00",
                                    "timeZone": "UTC",
                                },
                            },
                            {
                                "id": "event-2",
                                "@removed": {"reason": "deleted"},
                            },
                        ],
                        "@odata.deltaLink": (
                            f"{graph_root}/me/calendarView/delta?$deltatoken=round2"
                        ),
                    }
                )
                return

            if "$skiptoken" in query:
                if query["$skiptoken"] != ["page2"]:
                    self.send_error(400, "unexpected skip token")
                    return
                self._json(
                    {
                        "value": [
                            {
                                "id": "event-2",
                                "changeKey": "e2-v1",
                                "subject": "Second meeting",
                                "type": "singleInstance",
                                "isAllDay": False,
                                "isCancelled": False,
                                "start": {
                                    "dateTime": "2026-09-29T09:00:00",
                                    "timeZone": "UTC",
                                },
                                "end": {
                                    "dateTime": "2026-09-29T10:00:00",
                                    "timeZone": "UTC",
                                },
                            }
                        ],
                        "@odata.deltaLink": (
                            f"{graph_root}/me/calendarView/delta?$deltatoken=round1"
                        ),
                    }
                )
                return

            if query.get("startDateTime") != [START]:
                self.send_error(400, "missing startDateTime")
                return
            if query.get("endDateTime") != [END]:
                self.send_error(400, "missing endDateTime")
                return
            self._json(
                {
                    "value": [
                        {
                            "id": "event-1",
                            "changeKey": "e1-v1",
                            "subject": "Meeting",
                            "type": "singleInstance",
                            "isAllDay": False,
                            "isCancelled": False,
                            "start": {
                                "dateTime": "2026-09-28T09:00:00",
                                "timeZone": "UTC",
                            },
                            "end": {
                                "dateTime": "2026-09-28T10:00:00",
                                "timeZone": "UTC",
                            },
                        }
                    ],
                    "@odata.nextLink": (
                        f"{graph_root}/me/calendarView/delta?$skiptoken=page2"
                    ),
                }
            )

        def _json(self, payload: dict) -> None:
            body = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    graph_root = f"http://127.0.0.1:{server.server_port}/v1.0"
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield graph_root, requests_seen
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def _settings(tmp_path: Path) -> list[str]:
    return [
        "-s",
        "MS_GRAPH_AUTH_METHOD=none",
        "-s",
        f"MSGLOOM_DATABASE_URL=sqlite:///{tmp_path / 'catalog.sqlite3'}",
        "-s",
        f"MSGLOOM_RAW_EVIDENCE_DIR={tmp_path / 'raw'}",
        "-s",
        "MSGLOOM_SOURCE_ID=calendar-delta-fixture",
        "-s",
        "MSGLOOM_SOURCE_IDENTITY_REQUIRED=False",
        "-s",
        "MSGLOOM_CATALOG_ENABLED=True",
        "-s",
        "MSGLOOM_RAW_EVIDENCE_ENABLED=True",
        "-s",
        "HTTPCACHE_ENABLED=False",
        "-s",
        "AUTOTHROTTLE_ENABLED=False",
        "-L",
        "INFO",
    ]


def _run(graph_root: str, args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", DELTA_COMMAND, graph_root, *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def test_calendar_delta_initial_then_incremental_round(
    tmp_path: Path,
    calendar_delta_server,
) -> None:
    graph_root, requests_seen = calendar_delta_server
    args = [
        "--start",
        START,
        "--end",
        END,
        "--page-size",
        "2",
        *_settings(tmp_path),
    ]

    first = _run(graph_root, args)
    if first.returncode != 0:
        pytest.fail(first.stderr)
    if "ERROR" in first.stderr:
        pytest.fail(f"Expected successful first Calendar delta round:\n{first.stderr}")

    second = _run(graph_root, args)
    if second.returncode != 0:
        pytest.fail(second.stderr)
    if "ERROR" in second.stderr:
        pytest.fail(
            f"Expected successful second Calendar delta round:\n{second.stderr}"
        )

    if len(requests_seen) != 3:
        pytest.fail(
            f"Expected three Graph requests across two rounds: {requests_seen!r}"
        )
    first_query = parse_qs(urlsplit(requests_seen[0]).query)
    if first_query.get("startDateTime") != [START]:
        pytest.fail("Expected initial Calendar delta fixed-window request")
    second_round_query = parse_qs(urlsplit(requests_seen[2]).query)
    if second_round_query.get("$deltatoken") != ["round1"]:
        pytest.fail("Expected second run to resume committed deltaLink")

    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        with catalog.Session() as session:
            checkpoint = session.scalar(select(CalendarDeltaCheckpoint))
            if checkpoint is None or checkpoint.revision != 2:
                pytest.fail("Expected two committed Calendar delta revisions")
            if not checkpoint.delta_link.endswith("$deltatoken=round2"):
                pytest.fail("Expected latest Calendar deltaLink")

            delta_count = session.scalar(
                select(func.count()).select_from(CalendarDeltaObservation)
            )
            if delta_count != 4:
                pytest.fail(
                    f"Expected four Calendar delta observations, got {delta_count}"
                )

            view_state = {
                row.event_id: row
                for row in session.scalars(select(CalendarDeltaEventState)).all()
            }
            if (
                view_state["event-1"].is_present is not True
                or view_state["event-1"].raw.get("subject") != "Meeting moved"
                or view_state["event-1"].latest_revision != 2
            ):
                pytest.fail("Expected committed current state for event-1")
            if (
                view_state["event-2"].is_present is not False
                or view_state["event-2"].removed_reason != "deleted"
                or view_state["event-2"].latest_revision != 2
            ):
                pytest.fail("Expected committed scoped removal for event-2")

            semantic_count = session.scalar(
                select(func.count()).select_from(CalendarEventObservation)
            )
            if semantic_count != 3:
                pytest.fail(
                    f"Expected three semantic event versions, got {semantic_count}"
                )

            current = {
                row.event_id: row
                for row in session.scalars(select(CalendarEventRecord)).all()
            }
            if current["event-1"].subject != "Meeting moved":
                pytest.fail("Expected incremental Calendar event update")
            if current["event-2"].is_removed is not False:
                pytest.fail("Scoped delta removal must not claim global event deletion")

            raw_count = session.scalar(
                select(func.count()).select_from(RawHttpEvidence)
            )
            if raw_count != 3:
                pytest.fail(f"Expected three raw captures, got {raw_count}")
    finally:
        catalog.close()
