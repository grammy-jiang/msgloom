"""Run the multi-phase Outlook Calendar sync workflow through real Scrapy crawlers."""

from __future__ import annotations

import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urlsplit

import pytest

from message_ingest.acquisition.microsoft.outlook.calendar.planner import (
    pending_full_v1_targets,
)
from message_ingest.acquisition.microsoft.outlook.calendar.profile import FULL_V1
from message_ingest.catalog import Catalog
from message_ingest.catalog.stores.microsoft.outlook.calendar import (
    OutlookCalendarStore,
)

ROOT = Path(__file__).parents[1]
START = "2026-09-27T00:00:00+10:00"
END = "2026-10-04T00:00:00+10:00"
PRIMARY = "calendar-primary"
SECONDARY = "calendar-secondary"
PRIMARY_EVENT = "primary-event"
SECONDARY_EVENT = "secondary-event"

RUN_COMMAND = r"""
import sys
from scrapy.cmdline import execute
from message_ingest.spiders.microsoft.outlook.calendar.discover import OutlookCalendarDiscoverSpider
from message_ingest.spiders.microsoft.outlook.calendar.delta import OutlookCalendarDeltaSpider
from message_ingest.spiders.microsoft.outlook.calendar.window import OutlookCalendarWindowSpider
from message_ingest.spiders.microsoft.outlook.calendar.full import OutlookCalendarFullSpider

for spider_cls in (
    OutlookCalendarDiscoverSpider,
    OutlookCalendarDeltaSpider,
    OutlookCalendarWindowSpider,
    OutlookCalendarFullSpider,
):
    spider_cls.graph_root = sys.argv[1]
    spider_cls.allowed_domains = ["127.0.0.1"]
execute(["scrapy", "microsoft", "outlook", "calendar", "sync", *sys.argv[2:]])
"""


@pytest.fixture
def sync_calendar_server():
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
            path = parsed.path.removeprefix("/v1.0")

            if path == "/me/calendars":
                self._json(
                    {
                        "value": [
                            {
                                "id": PRIMARY,
                                "name": "Calendar",
                                "changeKey": "calendar-p1",
                                "isDefaultCalendar": True,
                            },
                            {
                                "id": SECONDARY,
                                "name": "Projects",
                                "changeKey": "calendar-s1",
                                "isDefaultCalendar": False,
                            },
                        ]
                    }
                )
                return

            if path == "/me/calendarView/delta":
                if query.get("startDateTime") != [START] or query.get(
                    "endDateTime"
                ) != [END]:
                    self.send_error(400, "invalid delta window")
                    return
                self._json(
                    {
                        "value": [self._event(PRIMARY_EVENT, "p1", "Primary")],
                        "@odata.deltaLink": (
                            f"{graph_root}/me/calendarView/delta?$deltatoken=done"
                        ),
                    }
                )
                return

            if path == f"/me/calendars/{SECONDARY}/calendarView":
                if query.get("startDateTime") != [START] or query.get(
                    "endDateTime"
                ) != [END]:
                    self.send_error(400, "invalid secondary window")
                    return
                self._json({"value": [self._event(SECONDARY_EVENT, "s1", "Secondary")]})
                return

            if path in {
                f"/me/calendars/{PRIMARY}/events/{PRIMARY_EVENT}",
                f"/me/calendars/{SECONDARY}/events/{SECONDARY_EVENT}",
            }:
                if PRIMARY_EVENT in path:
                    event_id, change_key, subject = PRIMARY_EVENT, "p1", "Primary"
                else:
                    event_id, change_key, subject = SECONDARY_EVENT, "s1", "Secondary"
                payload = self._event(event_id, change_key, subject)
                payload["body"] = {"contentType": "text", "content": f"{subject} body"}
                payload["hasAttachments"] = False
                self._json(payload)
                return

            if path in {
                f"/me/calendars/{PRIMARY}/events/{PRIMARY_EVENT}/attachments",
                f"/me/calendars/{SECONDARY}/events/{SECONDARY_EVENT}/attachments",
            }:
                self._json({"value": []})
                return

            self.send_response(404)
            self.end_headers()

        @staticmethod
        def _event(event_id: str, change_key: str, subject: str) -> dict:
            return {
                "id": event_id,
                "changeKey": change_key,
                "subject": subject,
                "type": "singleInstance",
                "isAllDay": False,
                "isCancelled": False,
                "start": {"dateTime": "2026-09-28T09:00:00", "timeZone": "UTC"},
                "end": {"dateTime": "2026-09-28T10:00:00", "timeZone": "UTC"},
            }

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


def test_calendar_sync_collects_all_calendars_then_enriches_current_events(
    tmp_path: Path,
    sync_calendar_server,
) -> None:
    graph_root, requests_seen = sync_calendar_server
    database_url = f"sqlite:///{tmp_path / 'catalog.sqlite3'}"
    args = [
        sys.executable,
        "-c",
        RUN_COMMAND,
        graph_root,
        "--start",
        START,
        "--end",
        END,
        "--page-size",
        "25",
        "-L",
        "INFO",
        "-s",
        "MS_GRAPH_AUTH_METHOD=none",
        "-s",
        f"MSGLOOM_DATABASE_URL={database_url}",
        "-s",
        f"MSGLOOM_RAW_EVIDENCE_DIR={tmp_path / 'raw'}",
        "-s",
        "MSGLOOM_SOURCE_ID=calendar-sync-fixture",
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
    ]
    result = subprocess.run(
        args,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(result.stderr)
    if "ERROR" in result.stderr:
        pytest.fail(f"Expected successful Calendar sync crawl:\n{result.stderr}")

    discover_index = next(
        i
        for i, request in enumerate(requests_seen)
        if request.startswith("/v1.0/me/calendars?")
    )
    delta_index = next(
        i
        for i, request in enumerate(requests_seen)
        if request.startswith("/v1.0/me/calendarView/delta?")
    )
    window_index = next(
        i
        for i, request in enumerate(requests_seen)
        if request.startswith(f"/v1.0/me/calendars/{SECONDARY}/calendarView?")
    )
    full_indices = [
        i
        for i, request in enumerate(requests_seen)
        if "/events/" in request and "/attachments" not in request
    ]
    if not full_indices:
        pytest.fail(f"Expected Calendar full-enrichment requests: {requests_seen!r}")
    if not discover_index < delta_index < window_index < min(full_indices):
        pytest.fail(f"Expected sequential Calendar sync phases: {requests_seen!r}")

    catalog = Catalog(database_url)
    try:
        store = OutlookCalendarStore(catalog, source_id="calendar-sync-fixture")
        for event_id, version in ((PRIMARY_EVENT, "p1"), (SECONDARY_EVENT, "s1")):
            surfaces = store.get_event_surfaces(event_id=event_id)
            for surface in ("detail", "attachments"):
                state = surfaces.get(surface)
                if state is None or state["status"] != "acquired":
                    pytest.fail(
                        f"Expected acquired Calendar surface {event_id}/{surface}"
                    )
                if state["profile_version"] != FULL_V1:
                    pytest.fail("Expected Calendar Full-v1 profile version")
                if state["resource_version"] != version:
                    pytest.fail("Expected surface bound to current Calendar changeKey")
        if pending_full_v1_targets(store):
            pytest.fail("Expected sync to leave no incomplete current Calendar events")
    finally:
        catalog.close()
