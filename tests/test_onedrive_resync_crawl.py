"""Exercise OneDrive 410 resync lifecycle through a real local Scrapy crawl."""

from __future__ import annotations

import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest
from sqlalchemy import select

from message_ingest.catalog import Catalog
from message_ingest.catalog.models.acquisition import RawHttpEvidence
from message_ingest.catalog.models.microsoft.onedrive import (
    OneDriveDeltaCheckpoint,
    OneDriveDeltaResyncAttempt,
    OneDriveDeltaResyncObservation,
    OneDriveItemRecord,
)

ROOT = Path(__file__).parents[1]
DELTA = "/v1.0/me/drive/root/delta"
INITIAL = DELTA + "?%24top=2"
OLD_CURSOR = DELTA + "?token=synthetic-reset-secret%2F&x=+&x=%20"
PAGE_TWO = DELTA + "?token=synthetic-reset-page-2%2F&x=%20&x=+"
NEW_CURSOR = DELTA + "?token=synthetic-reset-done%2F&x=+"
BASE_ITEMS = [
    {"id": "kept", "name": "old-kept", "eTag": '"v1"', "file": {}},
    {"id": "absent", "name": "keep-metadata", "eTag": '"a1"', "file": {}},
]


@pytest.fixture
def resync_server():
    state = {"mode": "baseline", "reset_started": False}
    seen: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def do_GET(self):
            seen.append(self.path)
            status = 200
            headers = {}
            if self.path == INITIAL:
                payload = {"value": BASE_ITEMS, "@odata.deltaLink": origin + OLD_CURSOR}
            elif self.path == OLD_CURSOR and not state["reset_started"]:
                state["reset_started"] = True
                status = 410
                headers["Location"] = origin + OLD_CURSOR
                payload = {"error": {"code": "resyncChangesApplyDifferences"}}
            elif self.path == OLD_CURSOR:
                payload = {
                    "value": [
                        {
                            "id": "kept",
                            "name": "server-kept",
                            "eTag": '"v2"',
                            "file": {},
                        }
                    ],
                    "@odata.nextLink": origin + PAGE_TWO,
                }
            elif self.path == PAGE_TWO and state["mode"] == "http_error":
                status = 500
                payload = {"error": {"code": "SyntheticFailure"}}
            elif self.path == PAGE_TWO and state["mode"] == "malformed":
                payload = {
                    "value": [{"name": "missing-id"}],
                    "@odata.deltaLink": origin + NEW_CURSOR,
                }
            elif self.path == PAGE_TWO:
                payload = {
                    "value": [
                        {"id": "new", "name": "new-item", "eTag": '"n1"', "file": {}}
                    ],
                    "@odata.deltaLink": origin + NEW_CURSOR,
                }
            else:
                status = 404
                payload = {"error": {"code": "UnexpectedTraversal"}}
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            for name, value in headers.items():
                self.send_header(name, value)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    origin = f"http://127.0.0.1:{server.server_port}"
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield origin, state, seen
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _crawl(tmp_path, origin, *, setup=""):
    settings = {
        "MS_GRAPH_SERVICE_ROOT": origin + "/v1.0",
        "MS_GRAPH_AUTH_METHOD": "none",
        "MSGLOOM_SOURCE_IDENTITY_REQUIRED": "False",
        "MSGLOOM_ONEDRIVE_SOURCE_ID": "onedrive-resync-fixture",
        "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
        "MSGLOOM_RAW_EVIDENCE_DIR": str(tmp_path / "raw"),
        "MSGLOOM_CATALOG_ENABLED": "True",
        "MSGLOOM_RAW_EVIDENCE_ENABLED": "True",
        "HTTPCACHE_ENABLED": "True",
        "HTTPCACHE_DIR": str(tmp_path / "httpcache"),
        "AUTOTHROTTLE_ENABLED": "False",
        "RETRY_TIMES": "0",
        "LOG_LEVEL": "DEBUG",
    }
    script = (
        "import sys\n"
        + setup
        + "\nfrom scrapy.cmdline import execute\n"
        + "execute(['scrapy', 'microsoft', 'onedrive', *sys.argv[1:]])\n"
    )
    args = [sys.executable, "-c", script, "delta", "--page-size", "2"]
    for key, value in settings.items():
        args.extend(["-s", f"{key}={value}"])
    return subprocess.run(
        args,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=35,
        check=False,
    )


def _catalog(tmp_path):
    return Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")


def _baseline(tmp_path, origin, state):
    result = _crawl(tmp_path, origin)
    if result.returncode or "ERROR" in result.stderr:
        pytest.fail(result.stderr)
    state["mode"] = "resync"
    state["reset_started"] = False


def _assert_private_logs(result):
    if "synthetic-reset-secret" in result.stderr:
        pytest.fail("Opaque reset cursor leaked into logs")


def test_clean_410_resync_is_multi_page_staged_and_promoted_atomically(
    tmp_path, resync_server
):
    origin, state, seen = resync_server
    _baseline(tmp_path, origin, state)
    result = _crawl(tmp_path, origin)
    if result.returncode or "ERROR" in result.stderr:
        pytest.fail(result.stderr)
    _assert_private_logs(result)
    if seen != [INITIAL, OLD_CURSOR, OLD_CURSOR, PAGE_TWO]:
        pytest.fail(f"Reset did not replay and follow exact opaque links: {seen!r}")

    catalog = _catalog(tmp_path)
    try:
        with catalog.Session() as session:
            checkpoint = session.scalar(select(OneDriveDeltaCheckpoint))
            if checkpoint is None or checkpoint.revision != 2:
                pytest.fail("Clean reset did not advance exactly one checkpoint")
            if checkpoint.delta_link != origin + NEW_CURSOR:
                pytest.fail("Reset terminal cursor was rebuilt instead of preserved")
            attempts = session.scalars(select(OneDriveDeltaResyncAttempt)).all()
            observations = session.scalars(select(OneDriveDeltaResyncObservation)).all()
            if len(attempts) != 1 or len(observations) != 2:
                pytest.fail("Full reset attempt/sightings were not durably staged")
            rows = {
                row.item_id: row
                for row in session.scalars(select(OneDriveItemRecord)).all()
            }
            if rows["kept"].e_tag != '"v2"' or rows["kept"].is_deleted:
                pytest.fail("Returned server version did not win at clean idle")
            if (
                not rows["absent"].is_deleted
                or rows["absent"].name != "keep-metadata"
                or rows["absent"].deleted is not None
            ):
                pytest.fail("Unseen item absence lost useful prior metadata")
            if rows["new"].is_deleted:
                pytest.fail("Second reset page was not included before promotion")
            captures = session.scalars(select(RawHttpEvidence)).all()
            gone = next((row for row in captures if row.response_status == 410), None)
            if gone is None:
                pytest.fail("410 response evidence was not persisted")
            if any(name.lower() == "location" for name in gone.response_headers):
                pytest.fail("Persisted 410 evidence retained opaque Location")
            if "onedrive_delta_resync_location_redacted" not in gone.response_flags:
                pytest.fail("Persisted 410 evidence lacks redaction marker")
    finally:
        catalog.close()


@pytest.mark.parametrize("mode", ["http_error", "malformed", "pipeline", "drop"])
def test_failed_resync_keeps_old_checkpoint_and_current_presence(
    tmp_path, resync_server, mode
):
    origin, state, _seen = resync_server
    _baseline(tmp_path, origin, state)
    state["mode"] = mode
    setup = ""
    if mode in {"pipeline", "drop"}:
        failure = (
            "raise DropItem('synthetic staged drop')"
            if mode == "drop"
            else "raise RuntimeError('synthetic staged pipeline failure')"
        )
        setup = f"""
from scrapy.exceptions import DropItem
from message_ingest.items.microsoft.onedrive import OneDriveDeltaResyncObservationItem
from message_ingest.pipelines.microsoft.onedrive import OneDrivePipeline
original_process = OneDrivePipeline.process_item
async def process(self, item):
    result = await original_process(self, item)
    if isinstance(item, OneDriveDeltaResyncObservationItem):
        {failure}
    return result
OneDrivePipeline.process_item = process
"""
    result = _crawl(tmp_path, origin, setup=setup)
    if result.returncode != 1:
        pytest.fail(f"Failed reset must fail the command: {result.stderr}")
    _assert_private_logs(result)

    catalog = _catalog(tmp_path)
    try:
        with catalog.Session() as session:
            checkpoint = session.scalar(select(OneDriveDeltaCheckpoint))
            if checkpoint is None or checkpoint.revision != 1:
                pytest.fail("Failed reset advanced or discarded the old checkpoint")
            rows = {
                row.item_id: row
                for row in session.scalars(select(OneDriveItemRecord)).all()
            }
            if (
                set(rows) != {"kept", "absent"}
                or rows["kept"].e_tag != '"v1"'
                or rows["absent"].is_deleted
            ):
                pytest.fail("Partial failed reset changed authoritative current state")
            if not session.scalars(select(OneDriveDeltaResyncAttempt)).all():
                pytest.fail("Failed reset lost its durable attempt marker")
            if not session.scalars(select(OneDriveDeltaResyncObservation)).all():
                pytest.fail("Failed reset lost already staged sightings")
    finally:
        catalog.close()
