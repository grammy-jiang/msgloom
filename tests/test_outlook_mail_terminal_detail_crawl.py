"""Retain failed detail evidence through the native Mail pipeline chain."""

import json
import sqlite3
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest
from test_outlook_crawls import ROOT, RUN_COMMAND

EVIDENCE_GUARD = """
import message_ingest.settings as settings
from message_ingest.extensions.catalog import CatalogService
from message_ingest.items.microsoft.outlook.email import OutlookMessageSurfaceItem

class EvidenceBeforeTerminal:
    @classmethod
    def from_crawler(cls, crawler):
        instance = cls()
        instance.service = CatalogService.from_crawler(crawler)
        instance.stats = crawler.stats
        return instance

    def process_item(self, item):
        if isinstance(item, OutlookMessageSurfaceItem):
            if not self.service.catalog.evidence.contains(item.evidence_id):
                raise RuntimeError("Terminal semantics preceded saved evidence")
            self.stats.inc_value("test/evidence_before_terminal")
        return item

settings.ITEM_PIPELINES["__main__.EvidenceBeforeTerminal"] = 275
"""


@pytest.mark.parametrize("status", [404, 500])
def test_native_failed_detail_retains_only_proven_terminal_state(tmp_path, status):
    """A real missing detail is diagnostic proof, never a complete profile."""
    seen = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def do_GET(self):
            seen.append(self.path)
            body = b'{"error":{"code":"fixture","message":"detail unavailable"}}'
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    database = tmp_path / "mail.db"
    settings = {
        "MS_GRAPH_AUTH_METHOD": "none",
        "MSGLOOM_DATABASE_URL": f"sqlite:///{database}",
        "MSGLOOM_RAW_EVIDENCE_DIR": str(tmp_path / "raw"),
        "MSGLOOM_SOURCE_ID": "source",
        "MSGLOOM_SOURCE_IDENTITY_REQUIRED": "False",
        "RETRY_ENABLED": "False",
        "AUTOTHROTTLE_ENABLED": "False",
        "LOG_LEVEL": "INFO",
    }
    runner = RUN_COMMAND.replace(
        'execute(["scrapy",', EVIDENCE_GUARD + '\nexecute(["scrapy",'
    )
    args = [
        sys.executable,
        "-c",
        runner,
        f"http://127.0.0.1:{server.server_port}/v1.0",
        "microsoft",
        "outlook",
        "mail",
        "full",
        "missing",
    ]
    for key, value in settings.items():
        args.extend(["-s", f"{key}={value}"])
    try:
        result = subprocess.run(
            args, cwd=ROOT, capture_output=True, text=True, timeout=30, check=False
        )
    finally:
        server.shutdown()
        thread.join()
        server.server_close()
    (tmp_path / "crawl.stderr.log").write_text(result.stderr)
    (tmp_path / "crawl.stdout.log").write_text(result.stdout)
    if "Error processing" in result.stderr or "Traceback" in result.stderr:
        pytest.fail(result.stderr)
    if len(seen) != 1 or "/messages/missing?" not in seen[0]:
        pytest.fail(f"Failed detail fabricated component requests: {seen!r}")
    with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        evidence = [
            dict(row) for row in connection.execute("SELECT * FROM raw_http_evidence")
        ]
        surfaces = [
            dict(row) for row in connection.execute("SELECT * FROM message_surfaces")
        ]
        facts = [
            json.loads(row[0])
            for row in connection.execute("SELECT payload FROM acquisition_facts")
        ]
        for table in (
            "mail_application_bindings",
            "acquisition_release_entries",
            "acquisition_release_groups",
        ):
            if connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]:
                pytest.fail(f"Failed detail incorrectly populated {table}")
    if len(evidence) != 1 or evidence[0]["response_status"] != status:
        pytest.fail("Failed detail did not retain its exact HTTP evidence")
    if status == 500:
        if surfaces or facts:
            pytest.fail("Transient detail failure became terminal semantics")
        return
    if len(surfaces) != 1 or len(facts) != 1:
        pytest.fail("Missing detail lost its one unavailable diagnostic fact")
    surface, fact, capture = surfaces[0], facts[0], evidence[0]
    if (surface["surface"], surface["status"]) != ("detail", "unavailable"):
        pytest.fail("Missing detail changed terminal meaning")
    if (fact["source_id"], fact["run_id"], fact["evidence_id"]) != (
        "source",
        capture["run_id"],
        capture["evidence_id"],
    ):
        pytest.fail("Terminal diagnostic lost source, logical run, or evidence")
    if fact["source_version_locator"]["resource_version"] is not None:
        pytest.fail("Failed detail invented a primary version binding")
    if "'test/evidence_before_terminal': 1" not in result.stderr:
        pytest.fail("Native pipeline did not prove evidence-before-semantics")
