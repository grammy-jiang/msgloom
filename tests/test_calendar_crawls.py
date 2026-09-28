"""Run Calendar inventory and window modes through real Scrapy crawls."""

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
    CalendarEventObservation,
    CalendarEventRecord,
    CalendarRecord,
    Catalog,
    RawHttpEvidence,
)

ROOT = Path(__file__).parents[1]
START = "2026-09-27T00:00:00+10:00"
END = "2026-10-04T00:00:00+10:00"

DISCOVER_COMMAND = r"""
import sys
from scrapy.cmdline import execute
from message_ingest.spiders.outlook_calendar_discover import (
    OutlookCalendarDiscoverSpider,
)

OutlookCalendarDiscoverSpider.graph_root = sys.argv[1]
OutlookCalendarDiscoverSpider.allowed_domains = ["127.0.0.1"]
execute(["scrapy", "microsoft", "outlook", "calendar", "discover", *sys.argv[2:]])
"""

WINDOW_COMMAND = r"""
import sys
from scrapy.cmdline import execute
from message_ingest.spiders.outlook_calendar_window import (
    OutlookCalendarWindowSpider,
)

OutlookCalendarWindowSpider.graph_root = sys.argv[1]
OutlookCalendarWindowSpider.allowed_domains = ["127.0.0.1"]
execute(["scrapy", "microsoft", "outlook", "calendar", "window", *sys.argv[2:]])
"""


@pytest.fixture
def calendar_server():
    requests_seen: list[str] = []
    graph_root = ""

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:
            pass

        def do_GET(self) -> None:
            nonlocal graph_root
            parsed = urlsplit(self.path)
            requests_seen.append(self.path)
            query = parse_qs(parsed.query)

            if parsed.path == "/v1.0/me/calendars":
                if "$skiptoken" in query:
                    payload = {
                        "value": [
                            {
                                "id": "calendar-3",
                                "name": "Shared",
                                "changeKey": "c3",
                                "isDefaultCalendar": False,
                            }
                        ]
                    }
                else:
                    payload = {
                        "value": [
                            {
                                "id": "calendar-1",
                                "name": "Calendar",
                                "changeKey": "c1",
                                "isDefaultCalendar": True,
                            },
                            {
                                "id": "calendar-2",
                                "name": "Projects",
                                "changeKey": "c2",
                                "isDefaultCalendar": False,
                            },
                        ],
                        "@odata.nextLink": (
                            f"{graph_root}/me/calendars?$skiptoken=calendar-page-2"
                        ),
                    }
                self._json(payload)
                return

            if parsed.path == "/v1.0/me/calendar/calendarView":
                if "$skiptoken" in query:
                    payload = {
                        "value": [
                            {
                                "id": "event-3",
                                "changeKey": "e3",
                                "subject": "Page two",
                                "type": "singleInstance",
                                "isAllDay": False,
                                "isCancelled": False,
                                "start": {
                                    "dateTime": "2026-09-30T09:00:00",
                                    "timeZone": "UTC",
                                },
                                "end": {
                                    "dateTime": "2026-09-30T10:00:00",
                                    "timeZone": "UTC",
                                },
                            }
                        ]
                    }
                else:
                    if query.get("startDateTime") != [START]:
                        self.send_error(400, "missing startDateTime")
                        return
                    if query.get("endDateTime") != [END]:
                        self.send_error(400, "missing endDateTime")
                        return
                    payload = {
                        "value": [
                            {
                                "id": "event-1",
                                "changeKey": "e1",
                                "subject": "Occurrence",
                                "type": "occurrence",
                                "seriesMasterId": "series-1",
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
                            },
                            {
                                "id": "event-2",
                                "changeKey": "e2",
                                "subject": "Exception",
                                "type": "exception",
                                "seriesMasterId": "series-1",
                                "isAllDay": False,
                                "isCancelled": False,
                                "start": {
                                    "dateTime": "2026-09-29T11:00:00",
                                    "timeZone": "UTC",
                                },
                                "end": {
                                    "dateTime": "2026-09-29T12:00:00",
                                    "timeZone": "UTC",
                                },
                            },
                        ],
                        "@odata.nextLink": (
                            f"{graph_root}/me/calendar/calendarView?"
                            "$skiptoken=window-page-2"
                        ),
                    }
                self._json(payload)
                return

            self.send_response(404)
            self.end_headers()

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
        "MSGLOOM_SOURCE_ID=calendar-fixture",
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


def _run(code: str, graph_root: str, args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", code, graph_root, *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def test_calendar_inventory_then_window_persist_real_usage_state(
    tmp_path: Path,
    calendar_server,
) -> None:
    graph_root, requests_seen = calendar_server
    settings = _settings(tmp_path)

    discover = _run(
        DISCOVER_COMMAND,
        graph_root,
        ["--page-size", "2", *settings],
    )
    if discover.returncode != 0:
        pytest.fail(discover.stderr)
    if "ERROR" in discover.stderr:
        pytest.fail(f"Expected successful Calendar discovery:\n{discover.stderr}")

    window = _run(
        WINDOW_COMMAND,
        graph_root,
        [
            "--start",
            START,
            "--end",
            END,
            "--page-size",
            "2",
            *settings,
        ],
    )
    if window.returncode != 0:
        pytest.fail(window.stderr)
    if "ERROR" in window.stderr:
        pytest.fail(f"Expected successful Calendar window:\n{window.stderr}")

    if len(requests_seen) != 4:
        pytest.fail(f"Expected four Graph pages, got {requests_seen!r}")
    if "'msgloom/crawl/calendar/calendar_count': 3" not in discover.stderr:
        pytest.fail("Expected three discovered calendars")
    if "'msgloom/crawl/calendar/event_count': 3" not in window.stderr:
        pytest.fail("Expected three bounded Calendar events")

    database_url = f"sqlite:///{tmp_path / 'catalog.sqlite3'}"
    catalog = Catalog(database_url)
    try:
        with catalog.Session() as session:
            calendars = session.scalars(
                select(CalendarRecord).order_by(CalendarRecord.calendar_id)
            ).all()
            if [row.calendar_id for row in calendars] != [
                "calendar-1",
                "calendar-2",
                "calendar-3",
            ]:
                pytest.fail("Expected complete Calendar inventory")

            current = session.scalars(
                select(CalendarEventRecord).order_by(CalendarEventRecord.event_id)
            ).all()
            if [row.event_id for row in current] != [
                "event-1",
                "event-2",
                "event-3",
            ]:
                pytest.fail("Expected current state for both Calendar pages")
            if [row.event_type for row in current[:2]] != [
                "occurrence",
                "exception",
            ]:
                pytest.fail("Expected recurrence-expanded current state")
            if any(row.calendar_id != "calendar-1" for row in current):
                pytest.fail(
                    "Expected default-window events to join discovered calendar"
                )

            observations = session.scalars(
                select(CalendarEventObservation).order_by(
                    CalendarEventObservation.event_id
                )
            ).all()
            if len(observations) != 3:
                pytest.fail("Expected one semantic observation per event")
            if any(row.evidence_id is None for row in observations):
                pytest.fail("Expected Calendar events linked to raw evidence")

            evidence_count = session.scalar(
                select(func.count()).select_from(RawHttpEvidence)
            )
            if evidence_count != 4:
                pytest.fail(f"Expected one raw capture per page, got {evidence_count}")
    finally:
        catalog.close()
