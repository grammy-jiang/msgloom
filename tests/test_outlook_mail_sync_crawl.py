"""Run the multi-phase Outlook Mail sync workflow through a real Scrapy process."""

from __future__ import annotations

import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urlsplit

import pytest

from message_ingest.acquisition.microsoft.outlook.email.profile import FULL_V1
from message_ingest.catalog import Catalog
from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore

ROOT = Path(__file__).parents[1]
MESSAGE_ID = "sync-message-1"

RUN_COMMAND = r"""
import sys
from scrapy.cmdline import execute
from message_ingest.spiders.microsoft.outlook.email.delta import OutlookDeltaSpider
from message_ingest.spiders.microsoft.outlook.email.full import OutlookFullSpider

for spider_cls in (OutlookDeltaSpider, OutlookFullSpider):
    spider_cls.graph_root = sys.argv[1]
    spider_cls.allowed_domains = ["127.0.0.1"]
execute(["scrapy", "microsoft", "outlook", "mail", "sync", *sys.argv[2:]])
"""


@pytest.fixture
def sync_graph_server():
    requests_seen: list[str] = []
    graph_root = ""

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:
            pass

        def do_GET(self) -> None:
            nonlocal graph_root
            parsed = urlsplit(self.path)
            requests_seen.append(self.path)
            path = parsed.path.removeprefix("/v1.0")
            query = parse_qs(parsed.query)

            if path == "/me/mailFolders":
                self._json(
                    {
                        "value": [
                            {
                                "id": "folder-inbox",
                                "displayName": "Inbox",
                                "parentFolderId": "msgfolderroot",
                                "childFolderCount": 0,
                                "totalItemCount": 1,
                                "unreadItemCount": 0,
                                "isHidden": False,
                            }
                        ]
                    }
                )
                return

            if path == "/me/mailFolders/folder-inbox/messages/delta":
                self._json(
                    {
                        "value": [
                            {
                                "id": MESSAGE_ID,
                                "subject": "Sync candidate",
                                "sender": {
                                    "emailAddress": {"address": "sender@example.test"}
                                },
                                "from": {
                                    "emailAddress": {"address": "sender@example.test"}
                                },
                                "receivedDateTime": "2026-09-28T00:00:00Z",
                                "lastModifiedDateTime": "2026-09-28T00:00:00Z",
                                "parentFolderId": "folder-inbox",
                                "isRead": False,
                                "hasAttachments": False,
                            }
                        ],
                        "@odata.deltaLink": (
                            f"{graph_root}/me/mailFolders/folder-inbox/messages/delta?"
                            "$deltatoken=done"
                        ),
                    }
                )
                return

            if path == "/me/messages" and query.get("$select") == [
                "id,parentFolderId,lastModifiedDateTime"
            ]:
                self._json(
                    {
                        "value": [
                            {
                                "id": MESSAGE_ID,
                                "parentFolderId": "folder-inbox",
                                "lastModifiedDateTime": "2026-09-28T00:00:00Z",
                            }
                        ]
                    }
                )
                return

            if path == f"/me/messages/{MESSAGE_ID}":
                self._json(
                    {
                        "id": MESSAGE_ID,
                        "changeKey": "message-v1",
                        "subject": "Sync candidate",
                        "body": {"contentType": "text", "content": "Full body"},
                        "uniqueBody": {
                            "contentType": "text",
                            "content": "Full body",
                        },
                        "internetMessageHeaders": [],
                        "parentFolderId": "folder-inbox",
                        "hasAttachments": False,
                    }
                )
                return

            if path == f"/me/messages/{MESSAGE_ID}/attachments":
                self._json({"value": []})
                return

            if path == f"/me/messages/{MESSAGE_ID}/$value":
                body = b"From: sender@example.test\r\nSubject: Sync candidate\r\n\r\nFull body\r\n"
                self.send_response(200)
                self.send_header("Content-Type", "message/rfc822")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
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


def test_mail_sync_delta_then_full_refresh_in_one_scrapy_process(
    tmp_path: Path,
    sync_graph_server,
) -> None:
    graph_root, requests_seen = sync_graph_server
    database_url = f"sqlite:///{tmp_path / 'catalog.sqlite3'}"
    args = [
        sys.executable,
        "-c",
        RUN_COMMAND,
        graph_root,
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
        "MSGLOOM_SOURCE_ID=sync-fixture",
        "-s",
        "MSGLOOM_SOURCE_IDENTITY_REQUIRED=False",
        "-s",
        "MSGLOOM_CATALOG_ENABLED=True",
        "-s",
        "MSGLOOM_RAW_EVIDENCE_ENABLED=True",
        "-s",
        "MSGLOOM_DELTA_CHECKPOINT_ENABLED=True",
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
        pytest.fail(f"Expected successful Mail sync crawl:\n{result.stderr}")

    delta_index = next(
        index
        for index, request in enumerate(requests_seen)
        if "/messages/delta" in request
    )
    reconcile_index = next(
        index
        for index, request in enumerate(requests_seen)
        if request.startswith("/v1.0/me/messages?")
    )
    detail_index = next(
        index
        for index, request in enumerate(requests_seen)
        if request.startswith(f"/v1.0/me/messages/{MESSAGE_ID}?")
    )
    if max(delta_index, reconcile_index) >= detail_index:
        pytest.fail(
            f"Expected delta and reconciliation before full refresh: {requests_seen!r}"
        )

    catalog = Catalog(database_url)
    try:
        store = OutlookMailStore(catalog, source_id="sync-fixture")
        surfaces = store.get_surfaces(message_id=MESSAGE_ID)
        for surface in ("detail", "mime", "attachments"):
            state = surfaces.get(surface)
            if state is None or state["status"] != "acquired":
                pytest.fail(f"Expected acquired Mail Full-v1 surface {surface!r}")
            if state["profile_version"] != FULL_V1:
                pytest.fail(f"Expected Mail Full-v1 version on {surface!r}")
    finally:
        catalog.close()
