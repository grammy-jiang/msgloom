"""
Run all three CLI modes against a local Graph server with native Scrapy
components.
"""

from __future__ import annotations

import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urlsplit

import pytest

from message_ingest.catalog import Catalog
from message_ingest.checkpoints import OutlookDeltaCheckpointStore

ROOT = Path(__file__).parents[1]
FIXTURES = Path(__file__).parent / "fixtures" / "microsoft_graph"
GRAPH_ROOT = "https://graph.microsoft.com/v1.0"
MESSAGE_ID = "immutable-message-002"
RUN_COMMAND = """
import sys
from scrapy.cmdline import execute
from message_ingest.spiders.outlook_delta import OutlookDeltaSpider
from message_ingest.spiders.outlook_discover import OutlookDiscoverSpider
from message_ingest.spiders.outlook_full import OutlookFullSpider

for spider_cls in (OutlookDiscoverSpider, OutlookDeltaSpider, OutlookFullSpider):
    spider_cls.graph_root = sys.argv[1]
    spider_cls.allowed_domains = ["127.0.0.1"]
execute(["scrapy", *sys.argv[2:]])
"""


@pytest.fixture
def graph_server():
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:
            pass

        def do_GET(self):
            parsed = urlsplit(self.path)
            path = parsed.path.removeprefix("/v1.0")
            query = parse_qs(parsed.query)
            content_type = "application/json"
            status = 200
            if path == "/me/mailFolders":
                filename = (
                    "mail_folders_root_page_2.json"
                    if "$skiptoken" in query
                    else "mail_folders_root.json"
                )
                payload = (FIXTURES / filename).read_bytes()
            elif path.endswith("/childFolders"):
                payload = (FIXTURES / "mail_folders_child.json").read_bytes()
            elif path.endswith("/messages/delta"):
                if "folder-inbox" in path:
                    filename = (
                        "message_delta_page_2.json"
                        if "$skiptoken" in query
                        else "message_delta_page_1.json"
                    )
                    payload = (FIXTURES / filename).read_bytes()
                else:
                    payload = json.dumps(
                        {
                            "value": [],
                            "@odata.deltaLink": f"{GRAPH_ROOT}{path}?$deltatoken=done",
                        }
                    ).encode()
            elif path == "/me/messages":
                if query.get("$select") == ["id,parentFolderId,lastModifiedDateTime"]:
                    payload = json.dumps(
                        {
                            "value": [
                                {
                                    "id": "delta-message-001",
                                    "parentFolderId": "folder-inbox",
                                },
                                {"id": "orphan", "parentFolderId": "missing-folder"},
                            ]
                        }
                    ).encode()
                else:
                    filename = (
                        "list_messages_page_2.json"
                        if "$skip" in query
                        else "list_messages_page_1.json"
                    )
                    payload = (FIXTURES / filename).read_bytes()
            elif path == "/me/messages/orphan":
                payload = b'{"id":"orphan","parentFolderId":"missing-folder"}'
            elif path == f"/me/messages/{MESSAGE_ID}":
                payload = (FIXTURES / "message_detail.json").read_bytes()
            elif path == f"/me/messages/{MESSAGE_ID}/attachments":
                payload = (FIXTURES / "message_attachments.json").read_bytes()
            elif path.endswith("/$value"):
                payload = (FIXTURES / "message_mime.eml").read_bytes()
                content_type = "message/rfc822"
            elif path.endswith("/attachments/attachment-item-001"):
                payload = (FIXTURES / "item_attachment_detail.json").read_bytes()
            else:
                status = 404
                payload = b'{"error":{"message":"Unexpected fixture request"}}'
            payload = payload.replace(GRAPH_ROOT.encode(), graph_root.encode())
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    graph_root = f"http://127.0.0.1:{server.server_port}/v1.0"
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield graph_root
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


@pytest.mark.parametrize("mode", ["discover", "delta", "full"])
def test_outlook_command_crawls_local_graph_with_native_components(
    tmp_path: Path,
    graph_server: str,
    mode: str,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'catalog.sqlite3'}"
    args = [sys.executable, "-c", RUN_COMMAND, graph_server, f"outlook_{mode}"]
    if mode == "full":
        args.append(MESSAGE_ID)
    settings = {
        "MS_GRAPH_AUTH_METHOD": "none",
        "MSGLOOM_DATABASE_URL": database_url,
        "MSGLOOM_RAW_EVIDENCE_DIR": str(tmp_path / "raw"),
        "MSGLOOM_SOURCE_ID": "fixture",
        "MSGLOOM_CATALOG_ENABLED": "True",
        "MSGLOOM_RAW_EVIDENCE_ENABLED": "True",
        "MSGLOOM_DELTA_CHECKPOINT_ENABLED": "True",
        "HTTPCACHE_ENABLED": "False",
        "AUTOTHROTTLE_ENABLED": "False",
        "JOBDIR": str(tmp_path / "job"),
        "LOG_LEVEL": "INFO",
    }
    for key, value in settings.items():
        args.extend(["-s", f"{key}={value}"])
    result = subprocess.run(
        args,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(str(result.stderr))
    if "'finish_reason': 'finished'" not in result.stderr:
        pytest.fail("Expected: \"'finish_reason': 'finished'\" in result.stderr")
    if "ERROR" in result.stderr:
        pytest.fail('Expected: "ERROR" not in result.stderr')
    if "scheduler/unserializable" in result.stderr:
        pytest.fail('Expected: "scheduler/unserializable" not in result.stderr')

    expected_summary = {
        "discover": "Outlook discovery final summary: status=completed",
        "delta": "Outlook delta final summary: status=completed",
        "full": "Outlook full final summary: status=completed",
    }[mode]
    if expected_summary not in result.stderr:
        pytest.fail("Expected: expected_summary in result.stderr")
    if "'msgloom/final/status': 'completed'" not in result.stderr:
        pytest.fail("Expected final status=completed in dumped Scrapy stats")
    if mode == "discover":
        if "'msgloom/final/pagination_outcome': 'exhausted'" not in result.stderr:
            pytest.fail("Expected: discovery final pagination outcome is exhausted")
    elif mode == "delta":
        if "'msgloom/final/checkpoint_outcome': 'committed'" not in result.stderr:
            pytest.fail("Expected: delta final checkpoint outcome is committed")
    elif "'msgloom/final/profile_completeness': 'not_evaluated'" not in result.stderr:
        pytest.fail("Expected: Full execution does not claim profile completeness")
    if "msgloom/catalog/surface_item_processed_count/attachment_raw:" in result.stderr:
        pytest.fail("Expected: provider attachment IDs absent from catalog stat keys")

    catalog = Catalog(database_url)
    try:
        links = OutlookDeltaCheckpointStore(catalog, "fixture").get_delta_links()
        if mode == "delta":
            if set(links) != {
                "folder-inbox",
                "folder-hidden",
                "folder-project",
                "folder-archive",
            }:
                pytest.fail(
                    'Expected: set(links) == { "folder-inbox", "folder-hidden", "folder-project", "folder-archive", }'
                )
            if not all(link.startswith(graph_server) for link in links.values()):
                pytest.fail(
                    "Expected: all(link.startswith(graph_server) for link in links.values())"
                )
            if not catalog.get_message_state(source_id="fixture", message_id="orphan"):
                pytest.fail(
                    'Expected: catalog.get_message_state(source_id="fixture", message_id="orphan")'
                )
        else:
            if links:
                pytest.fail("Expected: not links")
            if not catalog.get_message_state(
                source_id="fixture", message_id=MESSAGE_ID
            ):
                pytest.fail(
                    'Expected: catalog.get_message_state(source_id="fixture", message_id=MESSAGE_ID)'
                )
        if mode == "full":
            surfaces = catalog.get_message_surfaces(
                source_id="fixture",
                message_id=MESSAGE_ID,
            )
            if {name: value["status"] for name, value in surfaces.items()} != {
                "detail": "acquired",
                "mime": "acquired",
                "attachments": "acquired",
                "attachment_raw:attachment-file-001": "acquired",
                "attachment_raw:attachment-item-001": "acquired",
                "attachment_raw:attachment-reference-001": "unsupported",
                "item_attachment_detail:attachment-item-001": "acquired",
            }:
                pytest.fail(
                    'Expected: {name: value["status"] for name, value in surfaces.items()} == { "detail": "acquired", "mime": "acquired", "attachments": "acquired", "attachment_raw:attachment-file-001": "acquired", "attachment_raw:attachment-item-001": "acquired", "attachment_raw:attachment-reference-001": "unsupported", "item_attachment_detail:attachment-item-001": "acquired", }'
                )
    finally:
        catalog.close()
