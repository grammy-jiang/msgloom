"""Use two HTTP hosts to prove native redirect auth and content privacy."""

import gzip
import json
import os
import socket
import subprocess
import sys
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest
from sqlalchemy import select

from message_ingest.catalog import Catalog
from message_ingest.catalog.models import RawHttpEvidence
from message_ingest.catalog.models.microsoft.onedrive import OneDriveContentRecord

ROOT = Path(__file__).parents[1]
TOKEN = "OBVIOUS-PREAUTHENTICATED-SECRET-TOKEN"
DOWNLOAD_PATH = f"/private-download-path/{TOKEN}?token={TOKEN}&x=%2f"
SOURCE = "/v1.0/me/drive/items/file%2F%2B%252F/content"
BODY = b"\x00OneDrive explicit binary evidence\xff\xfe"


@pytest.fixture
def download_servers():
    state = {"mode": "success"}
    observed = {"graph": [], "download": []}

    class DownloadHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def do_GET(self):
            observed["download"].append((self.path, self.headers.get("Authorization")))
            if state["mode"] == "disconnect":
                self.connection.shutdown(socket.SHUT_RDWR)
                self.connection.close()
                return
            status = 403 if state["mode"] == "http_error" else 200
            if state["mode"] == "retry" and len(observed["download"]) == 1:
                status = 500
            body = BODY
            if state["mode"] == "decompression_limit":
                body = gzip.compress(BODY * 1024)
            self.send_response(status)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(body)))
            if state["mode"] == "decompression_limit":
                self.send_header("Content-Encoding", "gzip")
            self.send_header("Content-Location", download_url)
            self.send_header("X-Download-Source", download_url)
            # A final Location header is still private, even on a HTTP 200/403.
            self.send_header("Location", download_url)
            self.end_headers()
            self.wfile.write(body)

    download = ThreadingHTTPServer(("127.0.0.1", 0), DownloadHandler)
    download_url = f"http://127.0.0.1:{download.server_port}{DOWNLOAD_PATH}"

    class GraphHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def do_GET(self):
            observed["graph"].append((self.path, self.headers.get("Authorization")))
            self.send_response(302)
            self.send_header("Location", download_url)
            self.send_header("Content-Length", "0")
            self.end_headers()

    graph = ThreadingHTTPServer(("127.0.0.1", 0), GraphHandler)
    threads = [
        Thread(target=server.serve_forever, daemon=True) for server in (graph, download)
    ]
    for thread in threads:
        thread.start()
    try:
        yield f"http://localhost:{graph.server_port}", download_url, state, observed
    finally:
        for server, thread in zip((graph, download), threads, strict=True):
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


def crawl(tmp_path, origin, *, maxsize=1024):
    settings = {
        "MS_GRAPH_SERVICE_ROOT": origin + "/v1.0",
        "MS_GRAPH_AUTH_METHOD": "none",
        "MSGLOOM_SOURCE_IDENTITY_REQUIRED": False,
        "MSGLOOM_ONEDRIVE_SOURCE_ID": "onedrive-content-fixture",
        "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
        "MSGLOOM_RAW_EVIDENCE_DIR": str(tmp_path / "raw"),
        "MSGLOOM_CATALOG_ENABLED": True,
        "MSGLOOM_RAW_EVIDENCE_ENABLED": True,
        "MSGLOOM_MAX_RAW_CONTENT_BYTES": maxsize,
        "HTTPCACHE_ENABLED": True,
        "HTTPCACHE_DIR": str(tmp_path / "cache"),
        "AUTOTHROTTLE_ENABLED": False,
        "RETRY_TIMES": 1,
        "LOG_LEVEL": "DEBUG",
    }
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "tests/onedrive_content_runner.py"),
            json.dumps(settings),
            str(tmp_path / "failures.json"),
        ],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT)},
        capture_output=True,
        text=True,
        timeout=40,
        check=False,
    )


def verify_transport(observed):
    if observed["graph"] != [(SOURCE, "Bearer ONE-DRIVE-AUTH-SENTINEL")]:
        pytest.fail(f"Graph request or original authentication changed: {observed!r}")
    if not observed["download"] or any(
        auth is not None for _, auth in observed["download"]
    ):
        pytest.fail("Native offsite redirect failed or forwarded Authorization")
    if any(path != DOWNLOAD_PATH for path, _ in observed["download"]):
        pytest.fail("Native redirect changed download URL bytes")


def verify_private(result, download_url, tmp_path, observed):
    for secret in (
        TOKEN,
        download_url,
        "private-download-path",
        "ONE-DRIVE-AUTH-SENTINEL",
    ):
        if secret in result.stdout or secret in result.stderr:
            pytest.fail(f"Content logs exposed a secret: {secret}\n{result.stderr}")
    for component in (
        "PrivacySafeRetryMiddleware",
        "MicrosoftGraphDiagnosticsMiddleware",
        "MicrosoftGraphErrorMiddleware",
        "RepresentationAwareRequestFingerprinter",
        "scrapy.downloadermiddlewares.redirect.RedirectMiddleware",
        "scrapy.downloadermiddlewares.offsite.OffsiteMiddleware",
        "microsoft_graph.extensions.onedrive.OneDriveContentPrivacyExtension",
        "microsoft_graph.addon.MicrosoftGraphAddon",
    ):
        if component not in result.stderr:
            pytest.fail(f"Shared or native component was replaced: {component}")
    transport = json.loads((tmp_path / "transport.json").read_text())
    if transport != {
        "framework_content_helper": True,
        "marked_downloads": len(observed["graph"]) + len(observed["download"]),
        "framework_privacy_active": True,
    }:
        pytest.fail(f"Framework content helper or privacy was bypassed: {transport}")
    if "message_ingest.extensions.microsoft.onedrive.privacy" in result.stderr:
        pytest.fail("Legacy application content privacy must not be loaded")


def evidence_rows(tmp_path):
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        with catalog.Session() as session:
            evidence = session.scalars(select(RawHttpEvidence)).all()
            content = session.scalars(select(OneDriveContentRecord)).all()
            session.expunge_all()
            return evidence, content
    finally:
        catalog.close()


def verify_evidence(evidence, source_url):
    if len(evidence) != 1:
        pytest.fail("Only the final callback-visible exchange should be persisted")
    capture = evidence[0]
    if capture.request_url != source_url or capture.response_url not in (
        source_url,
        None,
    ):
        pytest.fail("Raw evidence URLs must identify only the safe Graph source")
    if "preauthenticated_download_url_redacted" not in capture.response_flags:
        pytest.fail("Raw evidence must mark transport URL redaction")
    stored_headers = json.dumps([capture.request_headers, capture.response_headers])
    if TOKEN in stored_headers or "private-download-path" in stored_headers:
        pytest.fail("Persisted raw evidence headers exposed the download URL")
    if TOKEN in (capture.error_message or ""):
        pytest.fail("Persisted failure exception text exposed the download URL")
    return capture


@pytest.mark.parametrize("mode", ["success", "retry"])
def test_native_two_host_content_redirect_persists_exact_bytes_once(
    tmp_path, download_servers, mode
):
    origin, download_url, state, observed = download_servers
    state["mode"] = mode
    result = crawl(tmp_path, origin)
    if result.returncode or "ERROR" in result.stderr:
        pytest.fail(result.stderr)
    verify_transport(observed)
    verify_private(result, download_url, tmp_path, observed)
    if len(observed["download"]) != (2 if mode == "retry" else 1):
        pytest.fail("Shared retry behavior was not preserved on the download host")
    evidence, content = evidence_rows(tmp_path)
    capture = verify_evidence(evidence, origin + SOURCE)
    digest = sha256(BODY).hexdigest()
    if len(content) != 1:
        pytest.fail("Explicit download must produce exactly one semantic record")
    record = content[0]
    if (
        record.content_sha256 != digest
        or record.content_bytes != len(BODY)
        or record.latest_evidence_id != capture.evidence_id
    ):
        pytest.fail("Content semantic digest, length, or evidence link is wrong")
    if Path(capture.response_body_path).read_bytes() != BODY:
        pytest.fail("Raw evidence did not preserve exact downloaded bytes")
    bodies = [
        path for path in (tmp_path / "raw").iterdir() if path.read_bytes() == BODY
    ]
    if len(bodies) != 1:
        pytest.fail("Binary evidence must be stored in one content-addressed blob")
    if any(
        column.name in {"body", "raw", "url", "response_body"}
        for column in record.__table__.columns
    ):
        pytest.fail("Semantic content table must not duplicate raw bytes or URLs")
    if list((tmp_path / "cache").rglob("response_body")):
        pytest.fail("Content request bypass must prevent cached body duplicates")


@pytest.mark.parametrize(
    "mode", ["http_error", "disconnect", "oversize", "decompression_limit"]
)
def test_failed_native_download_keeps_urls_out_of_logs_and_failure_evidence(
    tmp_path, download_servers, mode
):
    origin, download_url, state, observed = download_servers
    state["mode"] = mode
    limit = {"oversize": 1, "decompression_limit": 512}.get(mode, 1024)
    result = crawl(tmp_path, origin, maxsize=limit)
    if result.returncode != 1:
        pytest.fail(f"Failed content acquisition must fail the run: {result.stderr}")
    verify_transport(observed)
    verify_private(result, download_url, tmp_path, observed)
    if (
        mode == "decompression_limit"
        and "component=scrapy.downloadermiddlewares.httpcompression"
        not in result.stderr
    ):
        pytest.fail("Compressed fixture must exercise native compression privacy")
    evidence, content = evidence_rows(tmp_path)
    capture = verify_evidence(evidence, origin + SOURCE)
    if content or not capture.error_type:
        pytest.fail("Failed download must produce failure evidence, not content state")
    failures = (tmp_path / "failures.json").read_text()
    if TOKEN in failures or "private-download-path" in failures:
        pytest.fail("AcquisitionFailureItem exposed the preauthenticated URL")
    items = json.loads(failures)
    if len(items) != 1 or items[0]["url"] != origin + SOURCE:
        pytest.fail("Failed download lost its sanitized acquisition failure item")
