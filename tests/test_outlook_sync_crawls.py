"""Run user-level Mail and Calendar sync workflows through real Scrapy crawlers."""

from __future__ import annotations

import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urlsplit

import pytest

from message_ingest.acquisition.microsoft.outlook.calendar.profile import (
    FULL_V1 as CALENDAR_FULL_V1,
)
from message_ingest.acquisition.microsoft.outlook.email.profile import (
    FULL_V1 as MAIL_FULL_V1,
)
from message_ingest.catalog import Catalog
from message_ingest.catalog.stores.microsoft.outlook.calendar import (
    OutlookCalendarStore,
)
from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore
from message_ingest.sync.microsoft.outlook.calendar.checkpoints import (
    CalendarDeltaCheckpointStore,
)
from message_ingest.sync.microsoft.outlook.email.checkpoints import (
    OutlookDeltaCheckpointStore,
)

ROOT = Path(__file__).parents[1]
START = "2026-09-27T00:00:00+10:00"
END = "2026-10-04T00:00:00+10:00"

RUN_COMMAND = r"""
import sys
from scrapy.cmdline import execute
from message_ingest.spiders.microsoft.outlook.email.delta import OutlookDeltaSpider
from message_ingest.spiders.microsoft.outlook.email.full import OutlookFullSpider
from message_ingest.spiders.microsoft.outlook.calendar.discover import OutlookCalendarDiscoverSpider
from message_ingest.spiders.microsoft.outlook.calendar.delta import OutlookCalendarDeltaSpider
from message_ingest.spiders.microsoft.outlook.calendar.window import OutlookCalendarWindowSpider
from message_ingest.spiders.microsoft.outlook.calendar.full import OutlookCalendarFullSpider

for spider_cls in (
    OutlookDeltaSpider,
    OutlookFullSpider,
    OutlookCalendarDiscoverSpider,
    OutlookCalendarDeltaSpider,
    OutlookCalendarWindowSpider,
    OutlookCalendarFullSpider,
):
    spider_cls.graph_root = sys.argv[1]
    spider_cls.allowed_domains = ["127.0.0.1"]
execute(["scrapy", *sys.argv[2:]])
"""


def _settings(tmp_path: Path, source_id: str) -> list[str]:
    return [
        "-s",
        "MS_GRAPH_AUTH_METHOD=none",
        "-s",
        f"MSGLOOM_DATABASE_URL=sqlite:///{tmp_path / 'catalog.sqlite3'}",
        "-s",
        f"MSGLOOM_RAW_EVIDENCE_DIR={tmp_path / 'raw'}",
        "-s",
        f"MSGLOOM_SOURCE_ID={source_id}",
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


def _serve(handler_cls):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
    root = f"http://127.0.0.1:{server.server_port}/v1.0"
    server.graph_root = root  # type: ignore[attr-defined]
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, root


def _json(handler: BaseHTTPRequestHandler, payload: dict, status: int = 200) -> None:
    body = json.dumps(payload).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def test_mail_sync_runs_delta_then_refreshes_changed_message(tmp_path: Path) -> None:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:
            pass

        def do_GET(self) -> None:
            parsed = urlsplit(self.path)
            path = parsed.path.removeprefix("/v1.0")
            root = self.server.graph_root  # type: ignore[attr-defined]
            if path == "/me/mailFolders":
                _json(
                    self,
                    {
                        "value": [
                            {
                                "id": "folder-inbox",
                                "displayName": "Inbox",
                                "parentFolderId": None,
                                "childFolderCount": 0,
                                "totalItemCount": 1,
                                "unreadItemCount": 1,
                                "isHidden": False,
                            }
                        ]
                    },
                )
                return
            if path == "/me/mailFolders/folder-inbox/messages/delta":
                _json(
                    self,
                    {
                        "value": [
                            {
                                "id": "message-1",
                                "subject": "Changed",
                                "parentFolderId": "folder-inbox",
                                "lastModifiedDateTime": "2026-09-28T00:00:00Z",
                                "hasAttachments": False,
                                "isRead": False,
                            }
                        ],
                        "@odata.deltaLink": (
                            f"{root}/me/mailFolders/folder-inbox/messages/delta?"
                            "$deltatoken=done"
                        ),
                    },
                )
                return
            if path == "/me/messages/message-1":
                _json(
                    self,
                    {
                        "id": "message-1",
                        "subject": "Changed",
                        "parentFolderId": "folder-inbox",
                        "lastModifiedDateTime": "2026-09-28T00:00:00Z",
                        "changeKey": "mail-v1",
                        "hasAttachments": False,
                        "body": {"contentType": "text", "content": "Body"},
                    },
                )
                return
            if path == "/me/messages/message-1/attachments":
                _json(self, {"value": []})
                return
            if path == "/me/messages/message-1/$value":
                body = b"From: example@example.test\r\n\r\nBody"
                self.send_response(200)
                self.send_header("Content-Type", "message/rfc822")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            _json(self, {"error": {"message": f"unexpected {path}"}}, status=404)

    server, thread, graph_root = _serve(Handler)
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                RUN_COMMAND,
                graph_root,
                "microsoft",
                "outlook",
                "mail",
                "sync",
                "--no-reconcile",
                *_settings(tmp_path, "mail-sync-fixture"),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    finally:
        server.shutdown()
        thread.join()
        server.server_close()

    if result.returncode != 0 or "ERROR" in result.stderr:
        pytest.fail(result.stderr)
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        links = OutlookDeltaCheckpointStore(
            catalog, "mail-sync-fixture"
        ).get_delta_links()
        if set(links) != {"folder-inbox"}:
            pytest.fail(f"Expected committed Mail delta cursor: {links!r}")
        store = OutlookMailStore(catalog, source_id="mail-sync-fixture")
        surfaces = store.get_surfaces(message_id="message-1")
        for surface in ("detail", "mime", "attachments"):
            state = surfaces.get(surface)
            if state is None or state["status"] != "acquired":
                pytest.fail(f"Expected Mail sync to complete {surface}: {surfaces!r}")
            if state["profile_version"] != MAIL_FULL_V1:
                pytest.fail("Expected Mail sync Full-v1 surface version")
    finally:
        catalog.close()


def test_calendar_sync_runs_discover_delta_then_versioned_enrichment(
    tmp_path: Path,
) -> None:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:
            pass

        def do_GET(self) -> None:
            parsed = urlsplit(self.path)
            path = parsed.path.removeprefix("/v1.0")
            query = parse_qs(parsed.query)
            root = self.server.graph_root  # type: ignore[attr-defined]
            if path == "/me/calendars":
                _json(
                    self,
                    {
                        "value": [
                            {
                                "id": "calendar-1",
                                "name": "Calendar",
                                "changeKey": "cal-v1",
                                "isDefaultCalendar": True,
                            }
                        ]
                    },
                )
                return
            if path == "/me/calendarView/delta":
                if query.get("startDateTime") != [START] or query.get(
                    "endDateTime"
                ) != [END]:
                    self.send_error(400, "missing fixed window")
                    return
                _json(
                    self,
                    {
                        "value": [
                            {
                                "id": "event-1",
                                "changeKey": "event-v1",
                                "subject": "Planning",
                                "type": "singleInstance",
                                "isAllDay": False,
                                "isCancelled": False,
                            }
                        ],
                        "@odata.deltaLink": (
                            f"{root}/me/calendarView/delta?$deltatoken=done"
                        ),
                    },
                )
                return
            if path == "/me/calendars/calendar-1/events/event-1":
                _json(
                    self,
                    {
                        "id": "event-1",
                        "changeKey": "event-v1",
                        "subject": "Planning",
                        "body": {"contentType": "text", "content": "Agenda"},
                        "hasAttachments": False,
                        "type": "singleInstance",
                        "isAllDay": False,
                        "isCancelled": False,
                    },
                )
                return
            if path == "/me/calendars/calendar-1/events/event-1/attachments":
                _json(self, {"value": []})
                return
            _json(self, {"error": {"message": f"unexpected {path}"}}, status=404)

    server, thread, graph_root = _serve(Handler)
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                RUN_COMMAND,
                graph_root,
                "microsoft",
                "outlook",
                "calendar",
                "sync",
                "--start",
                START,
                "--end",
                END,
                *_settings(tmp_path, "calendar-sync-fixture"),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    finally:
        server.shutdown()
        thread.join()
        server.server_close()

    if result.returncode != 0 or "ERROR" in result.stderr:
        pytest.fail(result.stderr)
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        checkpoint = CalendarDeltaCheckpointStore(
            catalog,
            source_id="calendar-sync-fixture",
            start_datetime=START,
            end_datetime=END,
            calendar_scope="default",
        ).get_checkpoint()
        if checkpoint is None:
            pytest.fail("Expected Calendar sync to commit fixed-window delta cursor")
        store = OutlookCalendarStore(catalog, source_id="calendar-sync-fixture")
        surfaces = store.get_event_surfaces(event_id="event-1")
        for surface in ("detail", "attachments"):
            state = surfaces.get(surface)
            if state is None or state["status"] != "acquired":
                pytest.fail(
                    f"Expected Calendar sync to complete {surface}: {surfaces!r}"
                )
            if state["profile_version"] != CALENDAR_FULL_V1:
                pytest.fail("Expected Calendar Full-v1 profile version")
            if state["resource_version"] != "event-v1":
                pytest.fail("Expected Calendar surface bound to current changeKey")
    finally:
        catalog.close()
