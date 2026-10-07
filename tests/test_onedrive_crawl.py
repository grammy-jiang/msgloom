"""Exercise OneDrive traversal and checkpoint safety through native Scrapy."""

import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Any

import pytest
from sqlalchemy import select

from message_ingest.catalog import Catalog
from message_ingest.catalog.models.acquisition import (
    RawHttpEvidence,
    SourceTargetBinding,
)
from message_ingest.catalog.models.microsoft.onedrive import (
    OneDriveContentRecord,
    OneDriveDeltaCheckpoint,
    OneDriveDeltaCheckpointCandidate,
    OneDriveDriveRecord,
    OneDriveItemRecord,
)

ROOT = Path(__file__).parents[1]
DRIVE = "/v1.0/me/drive"
CHILDREN = DRIVE + "/root/children"
DELTA = DRIVE + "/root/delta"
PAGE_QUERY = "?$skiptoken=private-page%2f%2F&x=+&x=%20"
FIRST_CURSOR = DELTA + "?$deltatoken=private-round1%2f%2F&x=+&x=%20"
SECOND_CURSOR = DELTA + "?$deltatoken=private-round2%2f%2F&x=%20&x=+"
ITEM_ID = "private-file/+%2f"
FILE = {
    "id": ITEM_ID,
    "name": "private-useful-name",
    "size": 0,
    "eTag": "",
    "parentReference": {"driveId": "drive", "id": "folder"},
    "file": {"mimeType": "application/octet-stream", "hashes": {}},
}


@pytest.fixture
def onedrive_server():
    seen: list[str] = []
    state = {"mode": "success"}
    pages: dict[str, dict[str, Any]] = {
        DRIVE: {
            "id": "drive",
            "driveType": "personal",
            "name": "",
            "owner": {"user": {"displayName": ""}},
            "quota": {"remaining": 0},
        },
        CHILDREN + "?%24top=2": {
            "value": [{"id": "folder", "name": "", "folder": {"childCount": 4}}],
            "@odata.nextLink": CHILDREN + PAGE_QUERY,
        },
        CHILDREN + PAGE_QUERY: {"value": [FILE]},
        DELTA + "?%24top=2": {
            "value": [FILE],
            "@odata.nextLink": DELTA + PAGE_QUERY,
        },
        DELTA + PAGE_QUERY: {
            "value": [
                {"id": "folder", "name": "", "folder": {"childCount": 4}},
                {"id": "initial-deleted", "deleted": {}},
            ],
            "@odata.deltaLink": FIRST_CURSOR,
        },
        FIRST_CURSOR: {
            "value": [
                {"id": ITEM_ID, "deleted": {}},
                {"id": "new-item", "name": "", "size": 0},
            ],
            "@odata.deltaLink": SECOND_CURSOR,
        },
    }

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def do_GET(self):
            seen.append(self.path)
            status = 200
            payload = pages.get(self.path)
            if state["mode"] == "empty" and self.path.startswith(CHILDREN):
                payload = {"value": []}
            if self.path == FIRST_CURSOR:
                if state["mode"] in {"403", "410"}:
                    status = int(state["mode"])
                    payload = {"error": {"code": "FixtureFailure"}}
                elif state["mode"] == "malformed":
                    payload = {"value": [{"name": "missing identity"}]}
            if payload is None:
                status = 404
                payload = {"error": {"code": "UnexpectedTraversal"}}
            response_payload: dict[str, Any] = dict(payload)
            for key in ("@odata.nextLink", "@odata.deltaLink"):
                if isinstance(link := response_payload.get(key), str):
                    response_payload[key] = origin + link
            body = json.dumps(response_payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    origin = f"http://127.0.0.1:{server.server_port}"
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield origin, seen, state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _crawl(tmp_path, origin, action="delta", *, setup=""):
    settings = {
        "MS_GRAPH_SERVICE_ROOT": origin + "/v1.0",
        "MS_GRAPH_AUTH_METHOD": "none",
        "MSGLOOM_SOURCE_IDENTITY_REQUIRED": "False",
        "MSGLOOM_ONEDRIVE_SOURCE_ID": "onedrive-fixture",
        "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
        "MSGLOOM_RAW_EVIDENCE_DIR": str(tmp_path / "raw"),
        "MSGLOOM_CATALOG_ENABLED": "True",
        "MSGLOOM_RAW_EVIDENCE_ENABLED": "True",
        "HTTPCACHE_ENABLED": str(action == "delta"),
        "HTTPCACHE_DIR": str(tmp_path / "httpcache"),
        "AUTOTHROTTLE_ENABLED": "False",
        "LOG_LEVEL": "DEBUG",
    }
    script = (
        "import sys\n"
        + setup
        + "\nfrom scrapy.cmdline import execute\n"
        + "execute(['scrapy', 'microsoft', 'onedrive', *sys.argv[1:]])\n"
    )
    args = [sys.executable, "-c", script, action, "--page-size", "2"]
    for key, value in settings.items():
        args.extend(["-s", f"{key}={value}"])
    return subprocess.run(
        args, cwd=ROOT, capture_output=True, text=True, timeout=30, check=False
    )


def _catalog(tmp_path):
    return Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")


def _clean(result):
    if result.returncode or "ERROR" in result.stderr:
        pytest.fail(result.stderr)
    _private_logs(result.stderr)


def _private_logs(stderr):
    for private in (ITEM_ID, "private-useful-name", "private-page", "private-round"):
        if private in stderr:
            pytest.fail(f"Provider identifiers leaked into logs: {private}")


def _linked(session, records):
    captures = {
        row.evidence_id: row for row in session.scalars(select(RawHttpEvidence))
    }
    for record in records:
        capture = captures.get(record.latest_evidence_id)
        if capture is None or capture.observed_at != record.latest_observed_at:
            pytest.fail("Semantic state lacks completed evidence and original time")
        if (
            record.source_id != "onedrive-fixture"
            or capture.source_id != record.source_id
        ):
            pytest.fail("OneDrive source identity did not reach persisted state")
    if session.scalar(select(SourceTargetBinding)) is not None:
        pytest.fail("Account-scoped OneDrive must not bind an Outlook mailbox")
    if session.scalar(select(OneDriveContentRecord)) is not None:
        pytest.fail("Metadata traversal must never acquire file content")
    return captures


def _delayed_candidate_setup(marker, *, failure_type=None):
    failure = (
        f"raise {failure_type}('injected delayed item failure')" if failure_type else ""
    )
    return f"""
import asyncio
from pathlib import Path
from scrapy.exceptions import DropItem
from message_ingest.items.microsoft.onedrive import OneDriveDeltaCheckpointCandidateItem
from message_ingest.pipelines.microsoft.onedrive import OneDrivePipeline

original_process = OneDrivePipeline.process_item

async def process(self, item):
    result = await original_process(self, item)
    if isinstance(item, OneDriveDeltaCheckpointCandidateItem):
        await asyncio.sleep(0.05)
        checkpoint = await asyncio.to_thread(self.store.load_checkpoint)
        revision = checkpoint.revision if checkpoint is not None else None
        if revision != item.base_revision:
            raise RuntimeError('checkpoint promoted before item processing ended')
        Path({str(marker)!r}).write_text(str(revision))
        {failure}
    return result

OneDrivePipeline.process_item = process
"""


def test_discovery_captures_root_only_and_preserves_absent_items(
    tmp_path, onedrive_server
):
    origin, seen, state = onedrive_server
    # Delay evidence writes so any semantic item that overtakes them fails.
    setup = """
import asyncio
from message_ingest.pipelines.evidence import RawEvidencePipeline
original_process = RawEvidencePipeline.process_item
async def process(self, item):
    await asyncio.sleep(0.01)
    return await original_process(self, item)
RawEvidencePipeline.process_item = process
"""
    result = _crawl(tmp_path, origin, "discover", setup=setup)
    _clean(result)
    if seen != [DRIVE, CHILDREN + "?%24top=2", CHILDREN + PAGE_QUERY]:
        pytest.fail(f"Discovery recursed or changed opaque page bytes: {seen!r}")
    for component in (
        "MicrosoftGraphErrorMiddleware",
        "PrivacySafeRetryMiddleware",
        "MicrosoftGraphDiagnosticsMiddleware",
        "MicrosoftGraphLogPrivacyExtension",
        "RepresentationAwareRequestFingerprinter",
    ):
        if component not in result.stderr:
            pytest.fail(f"Shared Graph component is missing: {component}")
    catalog = _catalog(tmp_path)
    try:
        with catalog.Session() as session:
            drives = session.scalars(select(OneDriveDriveRecord)).all()
            items = session.scalars(select(OneDriveItemRecord)).all()
            captures = _linked(session, [*drives, *items])
            if len(drives) != 1 or len(items) != 2 or len(captures) != 3:
                pytest.fail("Expected drive and root-only metadata with evidence")
        state["mode"] = "empty"
        _clean(_crawl(tmp_path, origin, "discover"))
        with catalog.Session() as session:
            items = session.scalars(select(OneDriveItemRecord)).all()
            if len(items) != 2 or any(row.is_deleted for row in items):
                pytest.fail("Discovery absence must not imply deletion")
    finally:
        catalog.close()


def test_delta_reuses_exact_opaque_cursor_and_preserves_sparse_tombstone_metadata(
    tmp_path, onedrive_server
):
    origin, seen, _state = onedrive_server
    marker = tmp_path / "candidate-waited"
    _clean(_crawl(tmp_path, origin, setup=_delayed_candidate_setup(marker)))
    if marker.read_text() != "None":
        pytest.fail("First checkpoint advanced before candidate processing ended")
    catalog = _catalog(tmp_path)
    try:
        with catalog.Session() as session:
            checkpoint = session.scalar(select(OneDriveDeltaCheckpoint))
            if checkpoint is None or checkpoint.revision != 1:
                pytest.fail("Initial clean delta did not promote one checkpoint")
            if checkpoint.delta_link != origin + FIRST_CURSOR:
                pytest.fail("Checkpoint changed provider cursor bytes")
            terminal = session.get(RawHttpEvidence, checkpoint.evidence_id)
            if terminal is None or terminal.request_url != origin + DELTA + PAGE_QUERY:
                pytest.fail("Checkpoint must link completed terminal response evidence")
        _clean(_crawl(tmp_path, origin, setup=_delayed_candidate_setup(marker)))
        if marker.read_text() != "1":
            pytest.fail("Second checkpoint advanced before pending item work ended")
        if seen != [DELTA + "?%24top=2", DELTA + PAGE_QUERY, FIRST_CURSOR]:
            pytest.fail(
                f"Delta changed opaque cursor bytes or traversed content: {seen!r}"
            )
        with catalog.Session() as session:
            checkpoint = session.scalar(select(OneDriveDeltaCheckpoint))
            if checkpoint is None or checkpoint.revision != 2:
                pytest.fail("Clean second delta did not advance exactly once")
            if checkpoint.delta_link != origin + SECOND_CURSOR:
                pytest.fail("Latest checkpoint was not retained verbatim")
            items = session.scalars(select(OneDriveItemRecord)).all()
            captures = _linked(session, items)
            if len(captures) != 3 or len(items) != 4:
                pytest.fail("Expected every delta entry and callback-visible response")
            by_id = {row.item_id: row for row in items}
            deleted = by_id[ITEM_ID]
            if not deleted.is_deleted or deleted.deleted != {}:
                pytest.fail("An empty deleted facet must mark an item deleted")
            if (deleted.name, deleted.size, deleted.e_tag, deleted.file) != (
                FILE["name"],
                0,
                "",
                FILE["file"],
            ) or deleted.parent_reference != FILE["parentReference"]:
                pytest.fail("Sparse tombstone discarded useful or falsey metadata")
            if deleted.raw != {"id": ITEM_ID, "deleted": {}}:
                pytest.fail("Current raw JSON must remain the sparse tombstone")
            initial = by_id["initial-deleted"]
            if not initial.is_deleted or initial.name is not None:
                pytest.fail("An initial tombstone must permit missing metadata")
    finally:
        catalog.close()


@pytest.mark.parametrize("mode", ["403", "410", "malformed"])
def test_delta_failure_retains_checkpoint_and_retries_same_cursor(
    tmp_path, onedrive_server, mode
):
    origin, seen, state = onedrive_server
    _clean(_crawl(tmp_path, origin))
    state["mode"] = mode
    failed = _crawl(tmp_path, origin)
    if failed.returncode != 1:
        pytest.fail(
            f"Request or callback failure must fail the command: {failed.stderr}"
        )
    _private_logs(failed.stderr)
    catalog = _catalog(tmp_path)
    try:
        with catalog.Session() as session:
            checkpoint = session.scalar(select(OneDriveDeltaCheckpoint))
            if checkpoint is None or checkpoint.revision != 1:
                pytest.fail("Failed delta run promoted or discarded its checkpoint")
            if checkpoint.delta_link != origin + FIRST_CURSOR:
                pytest.fail("Failed delta changed the committed opaque cursor")
            captures = session.scalars(select(RawHttpEvidence)).all()
            failed_capture = next(
                (row for row in captures if row.request_url == origin + FIRST_CURSOR),
                None,
            )
            if failed_capture is None or len(captures) != 3:
                pytest.fail("Failed or malformed response lost evidence-first capture")
            expected_status = 200 if mode == "malformed" else int(mode)
            if failed_capture.response_status != expected_status:
                pytest.fail("Failure evidence lost the terminal response status")
        state["mode"] = "success"
        _clean(_crawl(tmp_path, origin))
        if seen != [
            DELTA + "?%24top=2",
            DELTA + PAGE_QUERY,
            FIRST_CURSOR,
            FIRST_CURSOR,
        ]:
            pytest.fail("Failure reset the cursor or cached a delta response")
        with catalog.Session() as session:
            checkpoint = session.scalar(select(OneDriveDeltaCheckpoint))
            if checkpoint is None or checkpoint.revision != 2:
                pytest.fail("Retry of the unchanged cursor did not complete")
    finally:
        catalog.close()


@pytest.mark.parametrize("failure_type", ["RuntimeError", "DropItem"])
def test_delayed_item_failure_blocks_a_durable_candidate(
    tmp_path, onedrive_server, failure_type
):
    origin, _seen, _state = onedrive_server
    _clean(_crawl(tmp_path, origin))
    marker = tmp_path / "candidate-before-failure"
    result = _crawl(
        tmp_path,
        origin,
        setup=_delayed_candidate_setup(marker, failure_type=failure_type),
    )
    if result.returncode != 1:
        pytest.fail(
            f"Delayed item failure must fail the delta command: {result.stderr}"
        )
    if not marker.exists() or marker.read_text() != "1":
        pytest.fail("The durable candidate did not reach delayed item processing")
    _private_logs(result.stderr)
    catalog = _catalog(tmp_path)
    try:
        with catalog.Session() as session:
            checkpoint = session.scalar(select(OneDriveDeltaCheckpoint))
            if checkpoint is None or checkpoint.revision != 1:
                pytest.fail("Pending item failure did not block checkpoint promotion")
            candidates = session.scalars(select(OneDriveDeltaCheckpointCandidate)).all()
            if not any(row.delta_link == origin + SECOND_CURSOR for row in candidates):
                pytest.fail("The test requires a persisted terminal candidate")
    finally:
        catalog.close()
