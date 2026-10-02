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


CACHE_MESSAGE_ID = "cache-message"

CACHE_REFRESH_COMMAND = r"""
import sys
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from message_ingest.spiders.microsoft.outlook.email.full import OutlookFullSpider

OutlookFullSpider.graph_root = sys.argv[1]
OutlookFullSpider.allowed_domains = ["127.0.0.1"]
authoritative = sys.argv[2] == "1"
settings = get_project_settings()
for assignment in sys.argv[3:]:
    key, value = assignment.split("=", 1)
    settings.set(key, value, priority="cmdline")
process = CrawlerProcess(settings)
crawler = process.create_crawler(OutlookFullSpider)
process.crawl(
    crawler,
    message_ids="cache-message",
    operation="refresh",
    _authoritative_rule_refresh=authoritative,
)
process.start()
if process.bootstrap_failed or crawler.stats.get_value("msgloom/final/status") == "failed":
    raise SystemExit(1)
"""


@pytest.fixture
def cache_refresh_server():
    state = {"version": "v1"}
    seen: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:
            pass

        def do_GET(self) -> None:
            path = urlsplit(self.path).path
            seen.append(path)
            if path == f"/v1.0/me/messages/{CACHE_MESSAGE_ID}":
                self._json(
                    {
                        "id": CACHE_MESSAGE_ID,
                        "changeKey": state["version"],
                        "subject": state["version"],
                        "hasAttachments": False,
                    }
                )
                return
            if path == f"/v1.0/me/messages/{CACHE_MESSAGE_ID}/attachments":
                self._json({"value": []})
                return
            if path == f"/v1.0/me/messages/{CACHE_MESSAGE_ID}/$value":
                body = f"mime-{state['version']}".encode()
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
        yield root, state, seen
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def _cache_refresh_crawl(
    tmp_path: Path,
    graph_root: str,
    *,
    authoritative: bool,
) -> subprocess.CompletedProcess[str]:
    database_url = f"sqlite:///{tmp_path / 'cache-catalog.sqlite3'}"
    settings = {
        "MS_GRAPH_AUTH_METHOD": "none",
        "MSGLOOM_DATABASE_URL": database_url,
        "MSGLOOM_RAW_EVIDENCE_DIR": str(tmp_path / "cache-raw"),
        "MSGLOOM_SOURCE_ID": "cache-fixture",
        "MSGLOOM_SOURCE_IDENTITY_REQUIRED": "False",
        "HTTPCACHE_ENABLED": "True",
        "HTTPCACHE_DIR": str(tmp_path / "httpcache"),
        "AUTOTHROTTLE_ENABLED": "False",
        "RETRY_TIMES": "0",
        "LOG_LEVEL": "INFO",
    }
    args = [
        sys.executable,
        "-c",
        CACHE_REFRESH_COMMAND,
        graph_root,
        "1" if authoritative else "0",
        *(f"{key}={value}" for key, value in settings.items()),
    ]
    return subprocess.run(
        args,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=35,
        check=False,
    )


def test_rule_authoritative_full_refresh_bypasses_existing_http_cache(
    tmp_path: Path,
    cache_refresh_server,
) -> None:
    graph_root, state, seen = cache_refresh_server

    first = _cache_refresh_crawl(tmp_path, graph_root, authoritative=False)
    if first.returncode != 0:
        pytest.fail(first.stderr)
    first_hits = len(seen)
    if first_hits != 3:
        pytest.fail(f"Initial Full did not populate three cacheable surfaces: {seen!r}")

    state["version"] = "v2"
    replay = _cache_refresh_crawl(tmp_path, graph_root, authoritative=False)
    if replay.returncode != 0:
        pytest.fail(replay.stderr)
    if len(seen) != first_hits:
        pytest.fail("Ordinary Full did not prove an existing matching HTTP cache entry")

    authoritative = _cache_refresh_crawl(tmp_path, graph_root, authoritative=True)
    if authoritative.returncode != 0:
        pytest.fail(authoritative.stderr)
    if len(seen) != first_hits + 3:
        pytest.fail("Rule-authoritative Full did not bypass all three cached surfaces")

    catalog = Catalog(f"sqlite:///{tmp_path / 'cache-catalog.sqlite3'}")
    try:
        store = OutlookMailStore(catalog, source_id="cache-fixture")
        surfaces = store.get_surfaces(message_id=CACHE_MESSAGE_ID)
        detail_evidence = surfaces.get("detail", {}).get("evidence_id")
        if not isinstance(detail_evidence, str):
            pytest.fail("Authoritative detail surface lost evidence provenance")
        detail_run = catalog.evidence.run_ids_for((detail_evidence,)).get(
            detail_evidence
        )
        if detail_run is None:
            pytest.fail("Authoritative detail evidence lost run identity")

        from sqlalchemy import select

        from message_ingest.catalog.models.acquisition import RawHttpEvidence

        with catalog.Session() as session:
            detail_rows = session.scalars(
                select(RawHttpEvidence).where(
                    RawHttpEvidence.source_id == "cache-fixture",
                    RawHttpEvidence.purpose == "message-detail",
                    RawHttpEvidence.origin == "network",
                )
            ).all()
        if len(detail_rows) != 2:
            pytest.fail(
                "Expected only initial + authoritative network detail captures; "
                f"got {len(detail_rows)}"
            )
        if detail_run != detail_rows[-1].run_id or detail_run == detail_rows[0].run_id:
            pytest.fail("Latest Full surface did not prove current authoritative run")
    finally:
        catalog.close()
