"""Prove source isolation through overlapping native Mail crawls."""

import json
import os
import sqlite3
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from message_ingest.acquisition.microsoft.outlook.email.planner import (
    pending_full_v1_message_ids,
)
from message_ingest.catalog import Catalog
from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore

ROOT = Path(__file__).resolve().parents[1]
RUNNER = r"""
import asyncio, json, pickle, sys
from pathlib import Path
from sqlalchemy import text
from scrapy import signals
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from scrapy.utils.request import request_from_dict
from message_ingest.extensions.catalog import CatalogService
from message_ingest.items.microsoft.outlook.email import (
    OutlookMailDetailItem, OutlookAttachmentItem,
    OutlookMessageSurfaceItem, OutlookMailInventoryPageItem)
from message_ingest.pipelines.microsoft.outlook.email import OutlookMailPipeline
from message_ingest.spiders.microsoft.outlook.email.full import OutlookFullSpider

root, graph, phase, fail = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
barrier, a_primary, b_pending = asyncio.Barrier(2), asyncio.Event(), asyncio.Event()
events, services, errors = [], {}, []

def item_error(item, response, spider, failure):
    errors.append({"source": spider.crawler.settings["MSGLOOM_SOURCE_ID"],
                   "item": type(item).__name__, "traceback": failure.getTraceback()})

original = OutlookMailPipeline.process_item
request_original = OutlookFullSpider._message_detail_request
components = (OutlookAttachmentItem, OutlookMessageSurfaceItem,
              OutlookMailInventoryPageItem)

def selected_request(self, *args, **kwargs):
    path = root / self.crawler.settings["MSGLOOM_SOURCE_ID"] / "request.pickle"
    if phase == "retry":
        return request_from_dict(pickle.loads(path.read_bytes()), spider=self)
    request = request_original(self, *args, **kwargs)
    path.write_bytes(pickle.dumps(request.to_dict(spider=self)))
    return request

def rows(pipeline, sql, **parameters):
    with pipeline.catalog.Session() as session:
        return [dict(row) for row in session.execute(
            text(sql), parameters).mappings()]

async def process_item(self, item):
    source = self.store.source_id
    service = self.service
    services[source] = service
    if phase == "overlap" and isinstance(item, OutlookMailDetailItem):
        events.append([source, "detail-enter"])
        await asyncio.wait_for(barrier.wait(), 8)
        if source == "b":
            await asyncio.wait_for(a_primary.wait(), 8)
            await asyncio.wait_for(b_pending.wait(), 8)
            facts = rows(self, "SELECT payload FROM acquisition_facts "
                         "WHERE source_id=:source", source="b")
            bindings = rows(self, "SELECT * FROM mail_application_bindings "
                            "WHERE source_id=:source", source="b")
            if facts or bindings:
                raise RuntimeError("B claimed authority before its primary")
            events.append(["b", "pending-before-primary"])
            if fail == "yes":
                with self.catalog.writer_session() as session:
                    session.execute(text(
                        "CREATE TRIGGER fail_b BEFORE INSERT ON acquisition_facts "
                        "WHEN NEW.source_id='b' AND "
                        "json_extract(NEW.payload,'$.resource_kind')='message' "
                        "BEGIN SELECT RAISE(ABORT,'native B rollback'); END"))
        try:
            result = await original(self, item)
        except Exception as exc:
            if source != "b" or fail != "yes" or "native B rollback" not in str(exc):
                raise
            events.append(["b", "primary-rollback"])
            raise
        finally:
            if source == "b" and fail == "yes":
                with self.catalog.writer_session() as session:
                    session.execute(text("DROP TRIGGER fail_b"))
        events.append([source, "primary-committed"])
        if source == "a":
            a_primary.set()
        return result
    if phase == "overlap" and source == "a" and isinstance(item, components):
        await asyncio.wait_for(a_primary.wait(), 8)
    result = await original(self, item)
    if phase == "overlap" and isinstance(item, components):
        events.append([source, "component-committed"])
        if source == "b" and not b_pending.is_set():
            captures = rows(self, "SELECT * FROM mail_component_captures "
                            "WHERE source_id=:source", source="b")
            if {"mime", "attachments", "attachment_metadata", "attachment_raw:a"} <= {
                    row["component"] for row in captures}:
                (root / "pending.json").write_text(json.dumps(captures))
                b_pending.set()
    return result

OutlookMailPipeline.process_item = process_item
OutlookFullSpider._message_detail_request = selected_request
OutlookFullSpider.allowed_domains = ["127.0.0.1"]
settings = get_project_settings()
settings.setdict({
    "MS_GRAPH_AUTH_METHOD": "none",
    "MSGLOOM_DATABASE_URL": "sqlite:///" + str(root / "catalog.db"),
    "MSGLOOM_SOURCE_IDENTITY_REQUIRED": False,
    "MSGLOOM_CATALOG_ENABLED": True, "MSGLOOM_RAW_EVIDENCE_ENABLED": True,
    "HTTPCACHE_ENABLED": True, "AUTOTHROTTLE_ENABLED": False,
    "CONCURRENT_REQUESTS_PER_DOMAIN": 8, "DOWNLOAD_DELAY": 0,
    "LOG_LEVEL": "INFO",
}, priority="cmdline")
process = CrawlerProcess(settings)
crawlers = {}
for source in (["b"] if phase == "retry" else ["a", "b"]):
    directory = root / source
    directory.mkdir(exist_ok=True)
    crawler = process.create_crawler(OutlookFullSpider)
    crawler.settings.setdict({
        "MSGLOOM_SOURCE_ID": source,
        "MSGLOOM_DATA_DIR": str(directory / "data"),
        "MSGLOOM_RAW_EVIDENCE_DIR": str(directory / "raw"),
        "MS_GRAPH_TOKEN_CACHE": str(directory / "auth.json"),
        "HTTPCACHE_DIR": str(directory / "cache"),
        "JOBDIR": None,
    }, priority="cmdline")
    crawler.signals.connect(item_error, signal=signals.item_error)
    crawlers[source] = crawler
    process.crawl(crawler, message_ids="m", graph_root=graph + "/" + source,
                  operation="enrich" if phase == "enrich" else "refresh")
process.start()
if phase != "enrich" and any(
       services.get(source) is not CatalogService.from_crawler(crawler)
       for source, crawler in crawlers.items()):
    raise RuntimeError("Native pipeline did not borrow its crawler service")
if phase == "overlap" and (
        set(services) != {"a", "b"} or services["a"] is services["b"]
        or services["a"].catalog is services["b"].catalog
        or services["a"].write_lock is services["b"].write_lock):
    raise RuntimeError("Crawls did not own independent CatalogService instances")
result = {"events": events, "errors": errors,
          "independent_services": len(services),
          "stats": {source: crawler.stats.get_stats()
                    for source, crawler in crawlers.items()}}
(root / (phase + ".json")).write_text(json.dumps(result, default=str, indent=2))
"""


def snapshot(database):
    """Read complete native state without altering acquisition ownership."""
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        return {
            table["name"]: [
                dict(row)
                for row in connection.execute(f'SELECT * FROM "{table["name"]}"')
            ]
            for table in tables
        }


def source_rows(state, source):
    """Include source-owned rows and members owned through exact pages."""
    pages = {
        row["page_id"]
        for row in state["mail_inventory_pages"]
        if row["source_id"] == source
    }
    return {
        table: [
            row
            for row in values
            if row.get("source_id") == source
            or (table == "mail_inventory_members" and row["page_id"] in pages)
        ]
        for table, values in state.items()
    }


def check_ownership(database, pending_b=False):
    """Verify exact native evidence, bindings, inventory and planner scope."""
    state = snapshot(database)
    evidence = {r["evidence_id"]: r for r in state["raw_http_evidence"]}
    facts = {r["fact_id"]: json.loads(r["payload"]) for r in state["acquisition_facts"]}
    captures = {r["capture_id"]: r for r in state["mail_component_captures"]}
    pages = {r["page_id"]: r for r in state["mail_inventory_pages"]}
    for capture in captures.values():
        data = json.loads(capture["payload"])
        for key in ("evidence_id", "parent_evidence_id"):
            if evidence[data[key]]["source_id"] != capture["source_id"]:
                pytest.fail("Capture crossed canonical evidence ownership")
    for binding in state["mail_application_bindings"]:
        source = binding["source_id"]
        primary, fact = facts[binding["primary_fact_id"]], facts[binding["fact_id"]]
        if {primary["source_id"], fact["source_id"]} != {source}:
            pytest.fail("Binding crossed exact primary or component source")
        if primary["resource_kind"] != "message":
            pytest.fail("Binding did not select an immutable primary fact")
        if binding["capture_id"]:
            capture = captures[binding["capture_id"]]
            if (
                capture["source_id"] != source
                or capture["selection_id"] != binding["selection_id"]
                or capture["parent_key"] != primary["source_state_key"]
                or fact["source_version_locator"]["resource_version"]
                != primary["source_state_key"]
            ):
                pytest.fail("Capture lost its exact source/application pin")
    for page in pages.values():
        data = json.loads(page["payload"])
        if any(
            evidence[data[key]]["source_id"] != page["source_id"]
            for key in ("evidence_id", "parent_evidence_id")
        ):
            pytest.fail("Inventory page crossed evidence ownership")
    for member in state["mail_inventory_members"]:
        page, capture = pages[member["page_id"]], captures[member["capture_id"]]
        if (
            page["source_id"] != capture["source_id"]
            or page["selection_id"] != capture["selection_id"]
            or json.loads(member["payload"])["name"] != page["source_id"]
        ):
            pytest.fail("Inventory member crossed source or selected page")
    for fact in facts.values():
        if evidence[fact["evidence_id"]]["source_id"] != fact["source_id"]:
            pytest.fail("Immutable fact crossed evidence ownership")
    catalog = Catalog(f"sqlite:///{database}")
    try:
        keys = []
        for source in ("a", "b"):
            store = OutlookMailStore(catalog, source_id=source)
            binding = store.full_binding_state(message_id="m")
            pending = source == "b" and pending_b
            if pending:
                if (
                    store.get_message_state(message_id="m") is not None
                    or store.get_surfaces(message_id="m")
                    or store.get_attachments(message_id="m")
                    or binding["resource_version"] is not None
                    or store.full_binding_complete(message_id="m")
                    or pending_full_v1_message_ids(store)
                ):
                    pytest.fail("Other source satisfied failed source B")
            else:
                if (
                    not store.full_binding_complete(message_id="m")
                    or pending_full_v1_message_ids(store)
                    or [a["name"] for a in binding["attachments"]] != [source]
                    or [a["name"] for a in store.get_attachments(message_id="m")]
                    != [source]
                ):
                    pytest.fail("Native exact source projections/planner disagree")
                keys.append(binding["resource_version"])
        if not pending_b and len(set(keys)) != 2:
            pytest.fail("Different source primary bytes became one parent key")
    finally:
        catalog.close()
    return state


@pytest.mark.parametrize("fail_primary", [False, True])
def test_native_concurrent_sources_keep_exact_bindings(tmp_path, fail_primary):
    """Overlap real crawls and recover only the failing source's captures."""
    requests, response_overlap = [], []
    response_barrier = threading.Barrier(2)
    active_phase = ["overlap"]

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def do_GET(self):
            path = urlsplit(self.path).path.split("/")
            source, leaf = path[1], path[5:]
            requests.append((source, leaf))
            content_type = "application/json"
            if not leaf:
                if active_phase[0] == "overlap":
                    response_barrier.wait(timeout=8)
                    response_overlap.append(source)
                body = {
                    "id": "m",
                    "changeKey": source,
                    "subject": source,
                    "hasAttachments": True,
                }
                payload = json.dumps(body).encode()
            elif leaf == ["attachments"]:
                payload = json.dumps(
                    {
                        "value": [
                            {
                                "id": "a",
                                "name": source,
                                "size": 3,
                                "@odata.type": "#microsoft.graph.fileAttachment",
                            }
                        ]
                    }
                ).encode()
            elif leaf in (["$value"], ["attachments", "a", "$value"]):
                content_type, payload = "application/octet-stream", source.encode() * 3
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def crawl(phase):
        active_phase[0] = phase
        command = [
            sys.executable,
            "-c",
            RUNNER,
            str(tmp_path),
            f"http://127.0.0.1:{server.server_port}",
            phase,
            "yes" if fail_primary else "no",
        ]
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=30,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            check=False,
        )
        (tmp_path / f"{phase}.log").write_text(completed.stdout + completed.stderr)
        if completed.returncode or not (tmp_path / f"{phase}.json").exists():
            pytest.fail(f"Native {phase} failed; see {tmp_path / (phase + '.log')}")
        result = json.loads((tmp_path / f"{phase}.json").read_text())
        for source, stats in result["stats"].items():
            expected = int(phase == "overlap" and source == "b" and fail_primary)
            if stats.get("msgloom/persistence/item_error_count", 0) != expected:
                pytest.fail(f"Unexpected native pipeline failure: {result['errors']}")
            if any(key.startswith("spider_exceptions/") for key in stats):
                pytest.fail(f"Native callback failed: {stats}")
        return result

    database = tmp_path / "catalog.db"
    try:
        overlap = crawl("overlap")
        events = overlap["events"]
        if sorted(response_overlap) != ["a", "b"]:
            pytest.fail("Native response overlap barrier was not established")
        if (
            overlap["independent_services"] != 2
            or max(events.index([s, "detail-enter"]) for s in ("a", "b"))
            >= events.index(["a", "primary-committed"])
            or events.index(["a", "primary-committed"])
            >= events.index(["a", "component-committed"])
            or events.index(["b", "component-committed"])
            >= events.index(["b", "pending-before-primary"])
        ):
            pytest.fail(f"Native simultaneous/opposite ordering unproven: {events}")
        before = check_ownership(database, pending_b=fail_primary)
        pending = json.loads((tmp_path / "pending.json").read_text())
        if fail_primary:
            if ["b", "primary-rollback"] not in events:
                pytest.fail("Native rollback injection was not reached")
            owned_b = source_rows(before, "b")
            if owned_b["acquisition_facts"] or owned_b["mail_application_bindings"]:
                pytest.fail("Failed primary leaked facts or application bindings")
            retry = crawl("retry")
            if retry["stats"]["b"].get("httpcache/hit", 0) < 4:
                pytest.fail("Reopened retry did not use actual canonical HTTP cache")
            after = check_ownership(database)
            if source_rows(before, "a") != source_rows(after, "a"):
                pytest.fail("Source B retry modified source A committed state")
            for table in (
                "mail_component_captures",
                "mail_inventory_pages",
                "mail_inventory_members",
                "acquisition_facts",
            ):
                if any(row not in after[table] for row in before[table]):
                    pytest.fail(f"Native retry changed immutable history: {table}")
        else:
            after = before
        applied = {
            row["capture_id"]
            for row in after["mail_application_bindings"]
            if row["source_id"] == "b"
        }
        if not {row["capture_id"] for row in pending} <= applied:
            pytest.fail("Exact B pending captures were not recovered on application")
        request_count = len(requests)
        enriched = crawl("enrich")
        final = check_ownership(database)
        if len(requests) != request_count:
            pytest.fail("Complete exact source state unexpectedly requested work")
        for stats in enriched["stats"].values():
            if stats.get("msgloom/crawl/enrichment/already_complete_count") != 1:
                pytest.fail("Native enrich did not independently validate each source")
        for table in (
            "acquisition_facts",
            "mail_component_captures",
            "mail_application_bindings",
            "mail_inventory_pages",
            "mail_inventory_members",
        ):
            if after[table] != final[table]:
                pytest.fail(f"No-work native enrich changed immutable {table}")
    finally:
        (tmp_path / "http-overlap.json").write_text(
            json.dumps({"sources": response_overlap, "requests": requests})
        )
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
