"""Check OneDrive releases through local Graph and real Scrapy pipelines."""

import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest
from sqlalchemy import select

from message_ingest.acquisition.handoff import AcquisitionStream
from message_ingest.catalog import Catalog
from message_ingest.catalog.models.handoff import AcquisitionReleaseGroup
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore

ROOT = Path(__file__).parents[1]
ENABLE = """
import message_ingest.settings as settings
settings.EXTENSIONS["message_ingest.extensions.handoff.HandoffReleaseExtension"] = 70
"""


@pytest.fixture
def server():
    state = {"failure": False}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def do_GET(self):
            status = 200
            if self.path == "/v1.0/me/drive":
                payload = {"id": "drive"}
            elif self.path.startswith("/v1.0/me/drive/root/children"):
                payload = {
                    "value": [{"id": name, "eTag": '"v1"'} for name in ("one", "two")]
                }
            elif self.path.endswith("/content"):
                payload = {"bytes": self.path}
                if state["failure"] and "/two/" in self.path:
                    status = 403
            else:
                status, payload = 404, {}
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("ETag", '"v1"')
            self.end_headers()
            self.wfile.write(body)

    service = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=service.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{service.server_port}/v1.0", state
    finally:
        service.shutdown()
        service.server_close()
        thread.join(timeout=5)


def run(tmp_path, root, mode, *, direct=False, setup="", failure=False):
    settings = {
        "MS_GRAPH_SERVICE_ROOT": root,
        "MS_GRAPH_AUTH_METHOD": "none",
        "MSGLOOM_SOURCE_IDENTITY_REQUIRED": "False",
        "MSGLOOM_ONEDRIVE_SOURCE_ID": "onedrive-fixture",
        "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.db'}",
        "MSGLOOM_RAW_EVIDENCE_DIR": str(tmp_path / "raw"),
        "MSGLOOM_CATALOG_ENABLED": "True",
        "MSGLOOM_RAW_EVIDENCE_ENABLED": "True",
        "HTTPCACHE_ENABLED": "False",
        "AUTOTHROTTLE_ENABLED": "False",
        "LOG_LEVEL": "DEBUG",
    }
    command = (
        ["crawl", "microsoft_onedrive_" + mode]
        if direct
        else ["microsoft", "onedrive", mode]
    )
    if mode == "content":
        command += ["-a", 'item_ids=["one","two"]'] if direct else ["one", "two"]
    for key, value in settings.items():
        command += ["-s", f"{key}={value}"]
    code = (
        ENABLE
        + setup
        + "\nimport sys\nfrom scrapy.cmdline import execute\nexecute(['scrapy', *sys.argv[1:]])"
    )
    result = subprocess.run(
        [sys.executable, "-c", code, *command],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if not failure and (result.returncode or "ERROR" in result.stderr):
        pytest.fail(result.stderr)
    if failure and not any(
        marker in result.stderr
        for marker in ("failure_count", "item_error", "spider_error")
    ):
        pytest.fail("Failure did not reach native crawl: " + result.stderr)


def read(tmp_path):
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.db'}")
    try:
        with catalog.Session() as writer:
            groups = [
                json.loads(row)
                for row in writer.scalars(select(AcquisitionReleaseGroup.payload))
            ]
        entries = AcquisitionHandoffStore(catalog).list_release_entries(
            "onedrive-fixture", AcquisitionStream.ONEDRIVE
        )
        return groups, [json.loads(row["payload"]) for row in entries]
    finally:
        catalog.close()


@pytest.mark.parametrize("direct", [False, True])
@pytest.mark.parametrize("partial", [False, True])
def test_native_inventory_and_independent_content(tmp_path, server, direct, partial):
    root, state = server
    run(tmp_path, root, "discover", direct=direct)
    groups, entries = read(tmp_path)
    if len(groups) != 1 or len(entries) != 3:
        pytest.fail("Native drive/root traversal did not release its inventory")
    if {entry["entry_kind"] for entry in entries} != {"context", "resource"}:
        pytest.fail("Drive inventory lost context/positive observation semantics")
    state["failure"] = partial
    run(tmp_path, root, "content", direct=direct, failure=partial)
    groups, entries = read(tmp_path)
    content = [group for group in groups if group["release_kind"] == "content_capture"]
    if {group["subject_identity"] for group in content} != (
        {"one"} if partial else {"one", "two"}
    ):
        pytest.fail("Successful version-linked targets did not release independently")
    components = [entry for entry in entries if entry["entry_kind"] == "component"]
    if len(components) != len(content) or any(
        entry["resource_kind"] != "onedrive_item" for entry in components
    ):
        pytest.fail("Content entries lost their semantic parent")


@pytest.mark.parametrize("failure", ["callback", "item"])
def test_native_inventory_failure_blocks_release(tmp_path, server, failure):
    if failure == "callback":
        setup = """
from message_ingest.spiders.microsoft.onedrive.discover import MicrosoftOneDriveDiscoverSpider as Spider
original = Spider.parse_children
def failed(self, response, **kwargs):
    yield from original(self, response, **kwargs)
    raise ValueError("injected callback failure")
Spider.parse_children = failed
"""
    else:
        setup = """
from message_ingest.pipelines.microsoft.onedrive import OneDrivePipeline
from message_ingest.items.microsoft.onedrive import OneDriveItem
original = OneDrivePipeline.process_item
async def failed(self, item):
    if isinstance(item, OneDriveItem):
        raise ValueError("injected item failure")
    return await original(self, item)
OneDrivePipeline.process_item = failed
"""
    run(tmp_path, server[0], "discover", setup=setup, failure=True)
    if read(tmp_path)[0]:
        pytest.fail("Failed native inventory published a release")


@pytest.mark.parametrize("failure", ["callback", "item"])
def test_native_content_failure_preserves_independent_target(tmp_path, server, failure):
    run(tmp_path, server[0], "discover")
    if failure == "callback":
        setup = """
from message_ingest.spiders.microsoft.onedrive.content import MicrosoftOneDriveContentSpider as Spider
original = Spider.parse_content
def failed(self, response, **kwargs):
    yield from original(self, response, **kwargs)
    if kwargs["item_id"] == "two":
        raise ValueError("injected callback failure")
Spider.parse_content = failed
"""
    else:
        setup = """
from message_ingest.pipelines.microsoft.onedrive import OneDrivePipeline
from message_ingest.items.microsoft.onedrive import OneDriveContentItem
original = OneDrivePipeline.process_item
async def failed(self, item):
    if isinstance(item, OneDriveContentItem) and item.item_id == "two":
        raise ValueError("injected item failure")
    return await original(self, item)
OneDrivePipeline.process_item = failed
"""
    run(tmp_path, server[0], "content", setup=setup, failure=True)
    groups, _ = read(tmp_path)
    content = [group for group in groups if group["release_kind"] == "content_capture"]
    if {group["subject_identity"] for group in content} != {"one"}:
        pytest.fail("Native failure lost independent per-item completion")
