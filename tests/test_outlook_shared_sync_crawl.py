"""Exercise public shared/delegated Outlook sync paths through real Scrapy crawlers."""

from __future__ import annotations

import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urlsplit

import pytest

ROOT = Path(__file__).parents[1]
TARGET = "shared.owner@example.test"
ENCODED = "shared.owner%40example.test"
START = "2026-09-27T00:00:00+10:00"
END = "2026-10-04T00:00:00+10:00"

RUN_COMMAND = r"""
import sys
from scrapy.cmdline import execute
from message_ingest.spiders.microsoft.outlook.email.folder_delta import OutlookFolderDeltaSpider
from message_ingest.spiders.microsoft.outlook.email.delta import OutlookDeltaSpider
from message_ingest.spiders.microsoft.outlook.email.full import OutlookFullSpider
from message_ingest.spiders.microsoft.outlook.calendar.discover import OutlookCalendarDiscoverSpider
from message_ingest.spiders.microsoft.outlook.calendar.delta import OutlookCalendarDeltaSpider
from message_ingest.spiders.microsoft.outlook.calendar.full import OutlookCalendarFullSpider

for spider_cls in (
    OutlookFolderDeltaSpider,
    OutlookDeltaSpider,
    OutlookFullSpider,
    OutlookCalendarDiscoverSpider,
    OutlookCalendarDeltaSpider,
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


def _json(handler: BaseHTTPRequestHandler, payload: dict, status: int = 200) -> None:
    body = json.dumps(payload).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _serve(handler_cls):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
    root = f"http://127.0.0.1:{server.server_port}/v1.0"
    server.graph_root = root  # type: ignore[attr-defined]
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, root


def test_shared_mail_sync_uses_users_scope_for_every_phase(tmp_path: Path) -> None:
    seen: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:
            pass

        def do_GET(self) -> None:
            parsed = urlsplit(self.path)
            seen.append(parsed.path)
            root = self.server.graph_root  # type: ignore[attr-defined]
            prefix = f"/v1.0/users/{ENCODED}"
            if not parsed.path.startswith(prefix):
                _json(self, {"error": {"message": "wrong mailbox scope"}}, 404)
                return
            path = parsed.path.removeprefix(prefix)
            query = parse_qs(parsed.query)

            if path == "/mailFolders/delta":
                _json(
                    self,
                    {
                        "value": [
                            {
                                "id": "folder-inbox",
                                "displayName": "Inbox",
                                "childFolderCount": 0,
                                "totalItemCount": 1,
                                "unreadItemCount": 0,
                                "isHidden": False,
                            }
                        ],
                        "@odata.deltaLink": (
                            f"{root}/users/{ENCODED}/mailFolders/delta?"
                            "$deltatoken=folder-done"
                        ),
                    },
                )
                return
            if path == "/mailFolders":
                _json(
                    self,
                    {
                        "value": [
                            {
                                "id": "folder-inbox",
                                "displayName": "Inbox",
                                "childFolderCount": 0,
                                "totalItemCount": 1,
                                "unreadItemCount": 0,
                                "isHidden": False,
                            }
                        ]
                    },
                )
                return
            if path == "/mailFolders/folder-inbox/messages/delta":
                _json(
                    self,
                    {
                        "value": [
                            {
                                "id": "m1",
                                "subject": "Shared",
                                "parentFolderId": "folder-inbox",
                                "lastModifiedDateTime": "2026-09-28T00:00:00Z",
                                "hasAttachments": False,
                                "isRead": False,
                            }
                        ],
                        "@odata.deltaLink": (
                            f"{root}/users/{ENCODED}/mailFolders/folder-inbox/"
                            "messages/delta?$deltatoken=message-done"
                        ),
                    },
                )
                return
            if path == "/messages/m1" and query:
                _json(
                    self,
                    {
                        "id": "m1",
                        "subject": "Shared",
                        "changeKey": "v1",
                        "parentFolderId": "folder-inbox",
                        "hasAttachments": False,
                        "body": {"contentType": "text", "content": "Body"},
                    },
                )
                return
            if path == "/messages/m1/attachments":
                _json(self, {"value": []})
                return
            if path == "/messages/m1/$value":
                body = b"From: sender@example.test\r\n\r\nShared body"
                self.send_response(200)
                self.send_header("Content-Type", "message/rfc822")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            _json(self, {"error": {"message": f"unexpected {path}"}}, 404)

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
                "--mailbox",
                TARGET,
                "--no-reconcile",
                *_settings(tmp_path, "shared-mail"),
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
    if not seen or any("/v1.0/me/" in path for path in seen):
        pytest.fail(f"Shared Mail workflow escaped delegated mailbox scope: {seen!r}")


def test_shared_calendar_sync_uses_users_scope_for_every_phase(tmp_path: Path) -> None:
    seen: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:
            pass

        def do_GET(self) -> None:
            parsed = urlsplit(self.path)
            seen.append(parsed.path)
            root = self.server.graph_root  # type: ignore[attr-defined]
            prefix = f"/v1.0/users/{ENCODED}"
            if not parsed.path.startswith(prefix):
                _json(self, {"error": {"message": "wrong mailbox scope"}}, 404)
                return
            path = parsed.path.removeprefix(prefix)
            query = parse_qs(parsed.query)

            if path == "/calendars":
                _json(
                    self,
                    {
                        "value": [
                            {
                                "id": "primary",
                                "name": "Calendar",
                                "isDefaultCalendar": True,
                            }
                        ]
                    },
                )
                return
            if path == "/calendarView/delta":
                if query.get("startDateTime") != [START] or query.get(
                    "endDateTime"
                ) != [END]:
                    _json(self, {"error": {"message": "wrong window"}}, 400)
                    return
                _json(
                    self,
                    {
                        "value": [
                            {
                                "id": "e1",
                                "changeKey": "ev1",
                                "subject": "Shared event",
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
                        "@odata.deltaLink": (
                            f"{root}/users/{ENCODED}/calendarView/delta?"
                            "$deltatoken=done"
                        ),
                    },
                )
                return
            if path in {"/events/e1", "/calendars/primary/events/e1"}:
                _json(
                    self,
                    {
                        "id": "e1",
                        "changeKey": "ev1",
                        "subject": "Shared event",
                        "type": "singleInstance",
                        "isAllDay": False,
                        "isCancelled": False,
                        "hasAttachments": False,
                        "body": {"contentType": "text", "content": "Body"},
                        "start": {
                            "dateTime": "2026-09-28T09:00:00",
                            "timeZone": "UTC",
                        },
                        "end": {
                            "dateTime": "2026-09-28T10:00:00",
                            "timeZone": "UTC",
                        },
                    },
                )
                return
            if path in {
                "/events/e1/attachments",
                "/calendars/primary/events/e1/attachments",
            }:
                _json(self, {"value": []})
                return
            _json(self, {"error": {"message": f"unexpected {path}"}}, 404)

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
                "--mailbox",
                TARGET,
                "--start",
                START,
                "--end",
                END,
                *_settings(tmp_path, "shared-calendar"),
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
    if not seen or any("/v1.0/me/" in path for path in seen):
        pytest.fail(f"Shared Calendar workflow escaped delegated scope: {seen!r}")
