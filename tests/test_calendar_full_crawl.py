"""Run targeted Calendar full acquisition through a real Scrapy crawl."""

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
    CalendarEventAttachmentRecord,
    CalendarEventObservation,
    CalendarEventRecord,
    Catalog,
    RawHttpEvidence,
)

ROOT = Path(__file__).parents[1]

FULL_COMMAND = r"""
import sys
from scrapy.cmdline import execute
from message_ingest.spiders.outlook_calendar_full import OutlookCalendarFullSpider

OutlookCalendarFullSpider.graph_root = sys.argv[1]
OutlookCalendarFullSpider.allowed_domains = ["127.0.0.1"]
execute([
    "scrapy",
    "microsoft",
    "outlook",
    "calendar",
    "full",
    "event-1",
    "--page-size",
    "1",
    *sys.argv[2:],
])
"""


@pytest.fixture
def calendar_full_server():
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

            if parsed.path == "/v1.0/me/events/event-1":
                prefer = self.headers.get("Prefer", "")
                if 'outlook.body-content-type="text"' not in prefer:
                    self.send_error(400, "missing body preference")
                    return
                self._json(
                    {
                        "id": "event-1",
                        "changeKey": "event-v1",
                        "subject": "Architecture review",
                        "body": {
                            "contentType": "text",
                            "content": "Review the migration plan.",
                        },
                        "bodyPreview": "Review the migration plan.",
                        "hasAttachments": True,
                        "organizer": {
                            "emailAddress": {
                                "name": "Owner",
                                "address": "owner@example.test",
                            }
                        },
                        "start": {
                            "dateTime": "2026-09-28T09:00:00",
                            "timeZone": "UTC",
                        },
                        "end": {
                            "dateTime": "2026-09-28T10:00:00",
                            "timeZone": "UTC",
                        },
                        "type": "singleInstance",
                        "isAllDay": False,
                        "isCancelled": False,
                    }
                )
                return

            if (
                parsed.path
                == "/v1.0/me/events/event-1/attachments/attachment-1/$value"
            ):
                body = b"Hello"
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            if parsed.path == "/v1.0/me/events/event-1/attachments":
                if "$skiptoken" in query:
                    self._json(
                        {
                            "value": [
                                {
                                    "@odata.type": (
                                        "#microsoft.graph.referenceAttachment"
                                    ),
                                    "id": "attachment-2",
                                    "name": "Design notes",
                                    "size": 0,
                                    "isInline": False,
                                }
                            ]
                        }
                    )
                    return
                if query.get("$top") != ["1"]:
                    self.send_error(400, "missing attachment page size")
                    return
                self._json(
                    {
                        "value": [
                            {
                                "@odata.type": (
                                    "#microsoft.graph.fileAttachment"
                                ),
                                "id": "attachment-1",
                                "name": "agenda.txt",
                                "contentType": "text/plain",
                                "size": 12,
                                "isInline": False,
                                "contentBytes": "SGVsbG8=",
                            }
                        ],
                        "@odata.nextLink": (
                            f"{graph_root}/me/events/event-1/attachments?"
                            "$skiptoken=attachment-page-2"
                        ),
                    }
                )
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
        "MSGLOOM_SOURCE_ID=calendar-full-fixture",
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
        [sys.executable, "-c", FULL_COMMAND, graph_root, *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def test_calendar_full_persists_rich_event_and_attachment_metadata(
    tmp_path: Path,
    calendar_full_server,
) -> None:
    graph_root, requests_seen = calendar_full_server
    result = _run(graph_root, _settings(tmp_path))
    if result.returncode != 0:
        pytest.fail(result.stderr)
    if "ERROR" in result.stderr:
        pytest.fail(f"Expected successful Calendar full crawl:\n{result.stderr}")
    if len(requests_seen) != 4:
        pytest.fail(
            "Expected detail, two attachment pages, and raw file content: "
            f"{requests_seen!r}"
        )

    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        with catalog.Session() as session:
            event = session.scalar(select(CalendarEventRecord))
            if event is None:
                pytest.fail("Expected Calendar event current state")
            body = event.raw.get("body")
            if not isinstance(body, dict):
                pytest.fail("Expected full Calendar event body")
            if body.get("content") != "Review the migration plan.":
                pytest.fail("Expected rich Calendar body content")

            observation_count = session.scalar(
                select(func.count()).select_from(CalendarEventObservation)
            )
            if observation_count != 1:
                pytest.fail("Expected one Calendar full semantic observation")

            attachments = session.scalars(
                select(CalendarEventAttachmentRecord).order_by(
                    CalendarEventAttachmentRecord.attachment_id
                )
            ).all()
            if [row.attachment_id for row in attachments] != [
                "attachment-1",
                "attachment-2",
            ]:
                pytest.fail("Expected two Calendar attachment records")
            if attachments[0].content_bytes_present is not True:
                pytest.fail("Expected file content marker")
            if attachments[0].content_status != "acquired":
                pytest.fail("Expected raw file attachment acquisition")
            if attachments[0].content_evidence_id is None:
                pytest.fail("Expected attachment content evidence link")
            if attachments[1].content_status != "reference":
                pytest.fail("Expected reference attachment without raw request")
            if "contentBytes" in attachments[0].raw:
                pytest.fail(
                    "Expected attachment bytes only in raw HTTP evidence"
                )

            evidence_count = session.scalar(
                select(func.count()).select_from(RawHttpEvidence)
            )
            if evidence_count != 4:
                pytest.fail(
                    f"Expected four Calendar full evidence rows, got "
                    f"{evidence_count}"
                )
    finally:
        catalog.close()
