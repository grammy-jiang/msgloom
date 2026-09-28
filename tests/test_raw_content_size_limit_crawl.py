"""Exercise Scrapy's native response maxsize through Outlook full acquisition."""

from __future__ import annotations

import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit

import pytest

from message_ingest.catalog import Catalog
from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore

ROOT = Path(__file__).parents[1]
MESSAGE_ID = "large-message"

RUN_COMMAND = r"""
import sys
from scrapy.cmdline import execute
from message_ingest.spiders.microsoft.outlook.email.full import OutlookFullSpider
OutlookFullSpider.graph_root = sys.argv[1]
OutlookFullSpider.allowed_domains = ["127.0.0.1"]
execute(["scrapy", "microsoft", "outlook", "mail", "full", "large-message", *sys.argv[2:]])
"""


@pytest.fixture
def large_content_server():
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:
            pass

        def do_GET(self) -> None:
            path = urlsplit(self.path).path.removeprefix("/v1.0")
            if path == f"/me/messages/{MESSAGE_ID}":
                self._json(
                    {
                        "id": MESSAGE_ID,
                        "changeKey": "v1",
                        "subject": "Large",
                        "hasAttachments": False,
                    }
                )
                return
            if path == f"/me/messages/{MESSAGE_ID}/attachments":
                self._json({"value": []})
                return
            if path == f"/me/messages/{MESSAGE_ID}/$value":
                body = b"x" * 1024
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
    root = f"http://127.0.0.1:{server.server_port}/v1.0"
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield root
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def test_native_maxsize_records_terminal_mime_omission_without_failing_run(
    tmp_path: Path,
    large_content_server: str,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'catalog.sqlite3'}"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            RUN_COMMAND,
            large_content_server,
            "-L",
            "INFO",
            "-s",
            "MS_GRAPH_AUTH_METHOD=none",
            "-s",
            f"MSGLOOM_DATABASE_URL={database_url}",
            "-s",
            f"MSGLOOM_RAW_EVIDENCE_DIR={tmp_path / 'raw'}",
            "-s",
            "MSGLOOM_SOURCE_ID=size-fixture",
            "-s",
            "MSGLOOM_SOURCE_IDENTITY_REQUIRED=False",
            "-s",
            "MSGLOOM_MAX_RAW_CONTENT_BYTES=128",
            "-s",
            "AUTOTHROTTLE_ENABLED=False",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(result.stderr)
    catalog = Catalog(database_url)
    try:
        surfaces = OutlookMailStore(catalog, source_id="size-fixture").get_surfaces(
            message_id=MESSAGE_ID
        )
        if surfaces.get("mime", {}).get("status") != "omitted_size_limit":
            pytest.fail(f"Expected terminal MIME size omission: {surfaces!r}")
        if surfaces.get("detail", {}).get("status") != "acquired":
            pytest.fail("Expected detail surface to remain acquired")
        if surfaces.get("attachments", {}).get("status") != "acquired":
            pytest.fail("Expected attachment inventory to remain acquired")
    finally:
        catalog.close()
