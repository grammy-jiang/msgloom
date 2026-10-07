"""Acquire one real Mail release for finite scheduled preparation tests."""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from contextlib import closing, contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit

import pytest

from msgloom.configuration import load_operator_configuration
from msgloom.preparation import DocumentFormat
from tests.application_cli.helpers import minimal_config
from tests.handoff_release_reader_helpers import bind_fixture_source
from tests.preparation_pipeline.helpers import filter_config, profiles
from tests.test_outlook_crawls import FIXTURES, ROOT, RUN_COMMAND

SOURCE = "scheduled-mail-fixture"
CONSUMER = "scheduled-mail-consumer"
MESSAGE = "immutable-message-001"
SUBJECT = "Daily service report"


@contextmanager
def one_message_server():
    """Serve one existing Graph fixture page and drain before A2 starts."""
    page = json.loads((FIXTURES / "list_messages_page_1.json").read_bytes())
    body = json.dumps({"value": page["value"]}).encode()
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            """Keep fixture HTTP logging out of shared test output."""

        def do_GET(self):
            """Expose only the one collection path required by discovery."""
            requests.append(self.path)
            valid = urlsplit(self.path).path == "/v1.0/me/messages"
            payload = body if valid else b"{}"
            self.send_response(200 if valid else 404)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1.0", body, requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        if thread.is_alive():
            pytest.fail("Local Graph fixture did not drain")


def acquire_one(root: Path) -> bytes:
    """Start empty, then let native Scrapy own every evidence/release write."""
    database = root / "catalog.sqlite3"
    if database.exists():
        pytest.fail("Scenario 1 requires a new empty historical catalog")
    bind_fixture_source(database, SOURCE)
    with closing(sqlite3.connect(database)) as connection:
        for table in ("messages", "acquisition_release_entries"):
            if connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]:
                pytest.fail("Scenario 1 was populated before native acquisition")
    with one_message_server() as (origin, body, requests):
        settings = {
            "MS_GRAPH_AUTH_METHOD": "none",
            "MSGLOOM_DATABASE_URL": f"sqlite:///{database}",
            "MSGLOOM_RAW_EVIDENCE_DIR": str(root / "raw"),
            "MSGLOOM_SOURCE_ID": SOURCE,
            "MSGLOOM_SOURCE_IDENTITY_REQUIRED": "False",
            "MSGLOOM_CATALOG_ENABLED": "True",
            "MSGLOOM_RAW_EVIDENCE_ENABLED": "True",
            "HTTPCACHE_ENABLED": "False",
            "AUTOTHROTTLE_ENABLED": "False",
            "LOG_LEVEL": "INFO",
        }
        args = [
            sys.executable,
            "-c",
            RUN_COMMAND,
            origin,
            "microsoft",
            "outlook",
            "mail",
            "discover",
        ]
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
        if result.returncode or "ERROR" in result.stderr:
            pytest.fail(result.stderr)
        if len(requests) != 1:
            pytest.fail("One-message discovery made unexpected Graph requests")
    return body


def configuration(root: Path):
    """Load strict operator config with one bounded stable intake consumer."""
    from message_ingest.catalog import Catalog
    from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore

    catalog = Catalog(f"sqlite:///{root / 'catalog.sqlite3'}")
    try:
        identity = AcquisitionHandoffStore(catalog).catalog_identity()
    finally:
        catalog.close()
    return load_operator_configuration(
        minimal_config(root / "operator.toml"),
        command_options={
            "source": {
                "catalog_path": str(root / "catalog.sqlite3"),
                "evidence_roots": [str(root / "raw")],
            },
            "preparation": {
                "filter_config": filter_config().model_dump(mode="json"),
                "parser_profiles": [
                    profile.model_dump(mode="json")
                    for profile in profiles(
                        DocumentFormat.TEXT,
                        DocumentFormat.HTML,
                        DocumentFormat.JSON,
                        DocumentFormat.MIME,
                    )
                ],
                "execution_timeout_seconds": 30.0,
                "claim_lease_seconds": 35.0,
                "max_records": 1,
                "intake_targets": [
                    {
                        "expected_catalog": {
                            "catalog_identity": identity,
                            "schema_version": 1,
                        },
                        "source_id": SOURCE,
                        "stream": "outlook_mail",
                        "consumer_id": CONSUMER,
                        "max_entries": 1,
                        "max_pending_worksets": 1,
                    }
                ],
            },
        },
    )


def durable_outputs(root: Path):
    """Freeze immutable output rows to detect duplicate scheduled work."""
    database = root / "state" / "phase1.sqlite3"
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as db:
        counts = dict(
            db.execute("SELECT kind, count(*) FROM phase1_stage_results GROUP BY kind")
        )
        if any(
            counts.get(kind) != 1
            for kind in (
                "prepared",
                "collected_selection",
                "preparation_intake_workset",
            )
        ):
            pytest.fail("One release did not yield exactly one durable A2 work unit")
        return {
            table: db.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
            for table in (
                "phase1_stage_results",
                "phase1_semantic_data",
                "phase1_preparation_intake_worksets",
                "phase1_preparation_intake_cursors",
            )
        }
