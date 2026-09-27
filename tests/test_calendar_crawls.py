"""Run the minimal Calendar slice through a real local Scrapy crawl."""

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
    Catalog,
    RawHttpEvidence,
)

ROOT = Path(__file__).parents[1]
RUN_COMMAND = r"""
import sys
from scrapy.cmdline import execute
from message_ingest.spiders.outlook_calendar import OutlookCalendarSpider

OutlookCalendarSpider.graph_root = sys.argv[1]
OutlookCalendarSpider.allowed_domains = ["127.0.0.1"]
execute(["scrapy", "crawl", "outlook_calendar", *sys.argv[2:]])
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
            if parsed.path != "/v1.0/me/calendar/events":
                self.send_response(404)
                self.end_headers()
                return

            query = parse_qs(parsed.query)
            if "$skiptoken" in query:
                payload = {
                    "value": [
                        {
                            "id": "event-3",
                            "subject": "Page two",
                            "start": {
                                "dateTime": "2026-09-29T09:00:00",
                                "timeZone": "UTC",
                            },
                            "end": {
                                "dateTime": "2026-09-29T10:00:00",
                                "timeZone": "UTC",
                            },
                            "type": "singleInstance",
                        }
                    ]
                }
            else:
                payload = {
                    "value": [
                        {
                            "id": "event-1",
                            "subject": "Planning",
                            "start": {
                                "dateTime": "2026-09-27T09:00:00",
                                "timeZone": "UTC",
                            },
                            "end": {
                                "dateTime": "2026-09-27T10:00:00",
                                "timeZone": "UTC",
                            },
                            "type": "singleInstance",
                        },
                        {
                            "id": "event-2",
                            "subject": "Series",
                            "start": {
                                "dateTime": "2026-09-28T09:00:00",
                                "timeZone": "UTC",
                            },
                            "end": {
                                "dateTime": "2026-09-28T10:00:00",
                                "timeZone": "UTC",
                            },
                            "type": "seriesMaster",
                        },
                    ],
                    "@odata.nextLink": (
                        f"{graph_root}/me/calendar/events?"
                        "$skiptoken=opaque%2Fpage2"
                    ),
                }

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


def test_calendar_two_page_crawl_reuses_graph_and_evidence_components(
    tmp_path: Path,
    calendar_server,
) -> None:
    graph_root, requests_seen = calendar_server
    database_url = f"sqlite:///{tmp_path / 'catalog.sqlite3'}"
    args = [
        sys.executable,
        "-c",
        RUN_COMMAND,
        graph_root,
        "-s",
        "MS_GRAPH_AUTH_METHOD=none",
        "-s",
        f"MSGLOOM_DATABASE_URL={database_url}",
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
        pytest.fail(f"Expected successful Calendar crawl:\n{result.stderr}")
    if len(requests_seen) != 2:
        pytest.fail(f"Expected two provider pages, got {requests_seen!r}")
    if "'msgloom/crawl/calendar/page_count': 2" not in result.stderr:
        pytest.fail("Expected two Calendar pages in final Scrapy stats")
    if "'msgloom/crawl/calendar/event_count': 3" not in result.stderr:
        pytest.fail("Expected three Calendar events in final Scrapy stats")
    if (
        "'msgloom/crawl/calendar/pagination_exhausted': True"
        not in result.stderr
    ):
        pytest.fail("Expected Calendar pagination exhaustion in final stats")

    catalog = Catalog(database_url)
    try:
        with catalog.Session() as session:
            rows = session.scalars(
                select(CalendarEventObservation).order_by(
                    CalendarEventObservation.event_id
                )
            ).all()
            if [row.event_id for row in rows] != [
                "event-1",
                "event-2",
                "event-3",
            ]:
                pytest.fail("Expected persisted Calendar events from both pages")
            if any(row.evidence_id is None for row in rows):
                pytest.fail("Expected every Calendar event linked to raw evidence")
            evidence_count = session.scalar(
                select(func.count()).select_from(RawHttpEvidence)
            )
            if evidence_count != 2:
                pytest.fail(
                    f"Expected one raw capture per page, got {evidence_count}"
                )
    finally:
        catalog.close()
