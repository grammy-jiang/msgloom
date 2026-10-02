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
from message_ingest.sync.microsoft.outlook.email.checkpoints import (
    OutlookDeltaCheckpointStore,
    OutlookFolderDeltaCheckpointStore,
)

ROOT = Path(__file__).parents[1]
MESSAGE_ID = "sync-message-1"

RUN_COMMAND = r"""
import sys
from scrapy.cmdline import execute
from message_ingest.spiders.microsoft.outlook.email.delta import OutlookDeltaSpider
from message_ingest.spiders.microsoft.outlook.email.folder_delta import OutlookFolderDeltaSpider
from message_ingest.spiders.microsoft.outlook.email.full import OutlookFullSpider
for spider_cls in (OutlookFolderDeltaSpider, OutlookDeltaSpider, OutlookFullSpider):
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

            if path == "/me/mailFolders/delta":
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
                        ],
                        "@odata.deltaLink": (
                            f"{graph_root}/me/mailFolders/delta?$deltatoken=folder-done"
                        ),
                    }
                )
                return

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

    folder_delta_index = next(
        index
        for index, request in enumerate(requests_seen)
        if request.startswith("/v1.0/me/mailFolders/delta?")
    )
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
    if not folder_delta_index < min(delta_index, reconcile_index):
        pytest.fail(
            f"Expected folder delta before message collection: {requests_seen!r}"
        )
    if max(delta_index, reconcile_index) >= detail_index:
        pytest.fail(
            f"Expected delta and reconciliation before full refresh: {requests_seen!r}"
        )

    catalog = Catalog(database_url)
    try:
        folder_cursor = OutlookFolderDeltaCheckpointStore(
            catalog, "sync-fixture"
        ).get_delta_link()
        if folder_cursor is None or "$deltatoken=folder-done" not in folder_cursor:
            pytest.fail("Expected committed mailFolder delta cursor")
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


RULE_FULL_ID = "rule-full-message"
RULE_DISCOVERY_ID = "rule-discovery-message"


@pytest.fixture
def rules_sync_graph_server(tmp_path: Path):
    requests_seen: list[str] = []
    state: dict[str, object] = {
        "cursor_before_full": None,
    }
    graph_root = ""
    database_url = f"sqlite:///{tmp_path / 'rules-catalog.sqlite3'}"

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:
            pass

        def do_GET(self) -> None:
            nonlocal graph_root
            parsed = urlsplit(self.path)
            requests_seen.append(self.path)
            path = parsed.path.removeprefix("/v1.0")
            query = parse_qs(parsed.query)

            if path == "/me/mailFolders/delta":
                self._json(
                    {
                        "value": [
                            {
                                "id": "folder-inbox",
                                "displayName": "Inbox",
                                "parentFolderId": "msgfolderroot",
                                "childFolderCount": 0,
                                "totalItemCount": 2,
                                "unreadItemCount": 0,
                                "isHidden": False,
                            }
                        ],
                        "@odata.deltaLink": (
                            f"{graph_root}/me/mailFolders/delta?$deltatoken=folder-done"
                        ),
                    }
                )
                return

            if path == "/me/mailFolders":
                self._json(
                    {
                        "value": [
                            {
                                "id": "folder-inbox",
                                "displayName": "Inbox",
                                "parentFolderId": "msgfolderroot",
                                "childFolderCount": 0,
                                "totalItemCount": 2,
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
                                "id": RULE_FULL_ID,
                                "changeKey": "full-v1",
                                "subject": "Needs body rule",
                                "lastModifiedDateTime": "2026-10-02T00:00:00Z",
                                "parentFolderId": "folder-inbox",
                                "isRead": False,
                                "hasAttachments": False,
                                "bodyPreview": "preview without keyword",
                            },
                            {
                                "id": RULE_DISCOVERY_ID,
                                "changeKey": "discovery-v1",
                                "subject": "Discovery only",
                                "lastModifiedDateTime": "2026-10-02T00:00:01Z",
                                "parentFolderId": "folder-inbox",
                                "isRead": True,
                                "hasAttachments": False,
                                "bodyPreview": "routine preview",
                            },
                        ],
                        "@odata.deltaLink": (
                            f"{graph_root}/me/mailFolders/folder-inbox/messages/delta?"
                            "$deltatoken=rules-done"
                        ),
                    }
                )
                return

            if path in {
                f"/me/messages/{RULE_FULL_ID}",
                f"/me/messages/{RULE_DISCOVERY_ID}",
            }:
                message_id = path.rsplit("/", 1)[-1]
                selected = query.get("$select", [""])[0].split(",")
                is_rule_probe = set(selected) == {"id", "changeKey", "body"}
                if is_rule_probe:
                    self._json(
                        {
                            "id": message_id,
                            "changeKey": (
                                "full-v1"
                                if message_id == RULE_FULL_ID
                                else "discovery-v1"
                            ),
                            "body": {
                                "contentType": "text",
                                "content": (
                                    "please escalate this message"
                                    if message_id == RULE_FULL_ID
                                    else "routine message body"
                                ),
                            },
                            "bodyPreview": "provider preview",
                        }
                    )
                    return

                if message_id != RULE_FULL_ID:
                    self.send_response(500)
                    self.end_headers()
                    return

                catalog = Catalog(database_url)
                try:
                    state["cursor_before_full"] = OutlookDeltaCheckpointStore(
                        catalog,
                        "rules-sync-fixture",
                    ).get_delta_links()
                finally:
                    catalog.close()

                self._json(
                    {
                        "id": RULE_FULL_ID,
                        "changeKey": "full-v1",
                        "subject": "Needs body rule",
                        "body": {
                            "contentType": "text",
                            "content": "please escalate this message",
                        },
                        "uniqueBody": {
                            "contentType": "text",
                            "content": "please escalate this message",
                        },
                        "internetMessageHeaders": [],
                        "parentFolderId": "folder-inbox",
                        "hasAttachments": False,
                    }
                )
                return

            if path == f"/me/messages/{RULE_FULL_ID}/attachments":
                self._json({"value": []})
                return

            if path == f"/me/messages/{RULE_FULL_ID}/$value":
                body = (
                    b"From: sender@example.test\r\n"
                    b"Subject: Needs body rule\r\n\r\n"
                    b"please escalate this message\r\n"
                )
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
        yield graph_root, database_url, requests_seen, state
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def test_rules_enabled_sync_probes_then_fulls_only_selected_and_promotes_last(
    tmp_path: Path,
    rules_sync_graph_server,
) -> None:
    graph_root, database_url, requests_seen, state = rules_sync_graph_server
    config = tmp_path / "msgloom.toml"
    config.write_text(
        """
[acquisition.microsoft.outlook.mail]
enabled = true
default_profile = "discovery"

[[acquisition.microsoft.outlook.mail.rules]]
id = "body-full"
sequence = 10
profile = "full"

[acquisition.microsoft.outlook.mail.rules.conditions]
body_contains = ["escalate"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    args = [
        sys.executable,
        "-c",
        RUN_COMMAND,
        graph_root,
        "--page-size",
        "25",
        "--no-reconcile",
        "--config",
        str(config),
        "-L",
        "INFO",
        "-s",
        "MS_GRAPH_AUTH_METHOD=none",
        "-s",
        f"MSGLOOM_DATABASE_URL={database_url}",
        "-s",
        f"MSGLOOM_RAW_EVIDENCE_DIR={tmp_path / 'rules-raw'}",
        "-s",
        "MSGLOOM_SOURCE_ID=rules-sync-fixture",
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
        timeout=35,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(result.stderr)
    if "rules_enabled_sync_not_implemented" in result.stderr:
        pytest.fail("Temporary rules-enabled sync gate was not removed")

    folder_delta_index = next(
        index
        for index, request in enumerate(requests_seen)
        if request.startswith("/v1.0/me/mailFolders/delta?")
    )
    message_delta_index = next(
        index
        for index, request in enumerate(requests_seen)
        if "/messages/delta" in request
    )

    def selected_fields(request: str) -> frozenset[str]:
        parsed = urlsplit(request)
        values = parse_qs(parsed.query).get("$select", [""])
        return frozenset(field for field in values[0].split(",") if field)

    def request_index(message_id: str, *, probe: bool) -> int:
        expected_path = f"/v1.0/me/messages/{message_id}"
        for index, request in enumerate(requests_seen):
            parsed = urlsplit(request)
            if parsed.path != expected_path:
                continue
            fields = selected_fields(request)
            is_probe = fields == frozenset({"id", "changeKey", "body"})
            if is_probe is probe:
                return index
        pytest.fail(
            f"Missing {'rule probe' if probe else 'Full detail'} for {message_id}; "
            f"requests={requests_seen!r}"
        )

    full_probe_index = request_index(RULE_FULL_ID, probe=True)
    discovery_probe_index = request_index(RULE_DISCOVERY_ID, probe=True)
    full_detail_index = request_index(RULE_FULL_ID, probe=False)

    if not folder_delta_index < message_delta_index:
        pytest.fail(f"Folder delta did not precede message delta: {requests_seen!r}")
    if max(full_probe_index, discovery_probe_index) >= full_detail_index:
        pytest.fail(f"Rule probes did not finish before Full phase: {requests_seen!r}")
    discovery_full_prefixes = (
        f"/v1.0/me/messages/{RULE_DISCOVERY_ID}/attachments",
        f"/v1.0/me/messages/{RULE_DISCOVERY_ID}/$value",
    )
    if any(request.startswith(discovery_full_prefixes) for request in requests_seen):
        pytest.fail("Discovery-only rule target incorrectly entered Full traversal")
    discovery_detail_requests = [
        request
        for request in requests_seen
        if request.startswith(f"/v1.0/me/messages/{RULE_DISCOVERY_ID}?")
    ]
    if len(discovery_detail_requests) != 1:
        pytest.fail(
            "Discovery-only message should have exactly one rule probe and no Full detail"
        )

    if state["cursor_before_full"] not in ({}, None):
        pytest.fail(f"Message-delta cursor promoted before Full completion: {state!r}")

    catalog = Catalog(database_url)
    try:
        links = OutlookDeltaCheckpointStore(
            catalog,
            "rules-sync-fixture",
        ).get_delta_links()
        if (
            set(links) != {"folder-inbox"}
            or "$deltatoken=rules-done" not in links["folder-inbox"]
        ):
            pytest.fail(f"Finalizer did not promote deferred message cursor: {links!r}")

        store = OutlookMailStore(catalog, source_id="rules-sync-fixture")
        full_surfaces = store.get_surfaces(message_id=RULE_FULL_ID)
        for surface in ("detail", "mime", "attachments"):
            state_row = full_surfaces.get(surface)
            if state_row is None or state_row["status"] != "acquired":
                pytest.fail(
                    f"Rule-selected Full target missing {surface}: {full_surfaces!r}"
                )
            if state_row["profile_version"] != FULL_V1:
                pytest.fail("Rule-selected Full target lost Full-v1 profile version")
        discovery_surfaces = store.get_surfaces(message_id=RULE_DISCOVERY_ID)
        discovery_state = discovery_surfaces.get("discovery")
        if (
            discovery_state is None
            or discovery_state["status"] != "acquired"
            or discovery_state["profile_version"] is not None
        ):
            pytest.fail(
                f"Discovery-only target lost its normal discovery surface: "
                f"{discovery_surfaces!r}"
            )
        for surface in ("detail", "mime", "attachments"):
            if surface in discovery_surfaces:
                pytest.fail(
                    f"Discovery-only target unexpectedly gained Full surface "
                    f"{surface!r}: {discovery_surfaces!r}"
                )
    finally:
        catalog.close()
