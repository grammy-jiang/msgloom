"""Native Mail binding probes use only temporary local fixture state."""

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from test_outlook_mail_handoff_facts import setup as setup  # noqa: PLC0414


def test_native_full_bindings_across_orders_and_cache(tmp_path):
    """Keep all component pins through real pipelines, cache, and enrich."""
    ROOT = Path(__file__).resolve().parents[1]
    PREFIX = tmp_path / "native-"

    def read_rows(database, query):
        if not database.exists():
            return []
        try:
            with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as con:
                con.row_factory = sqlite3.Row
                return [dict(r) for r in con.execute(query)]
        except sqlite3.OperationalError:
            return []

    def facts(database):
        return [
            json.loads(r["payload"])
            for r in read_rows(database, "SELECT payload FROM acquisition_facts")
        ]

    def wait_fact(database, message, components):
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            seen = {
                f["component_kind"]
                for f in facts(database)
                if f["resource_identity"] == message
            }
            if components <= seen:
                return True
            time.sleep(0.03)
        return False

    def summarize(database):
        fs = facts(database)
        evidence = {
            r["evidence_id"]: r
            for r in read_rows(
                database,
                "SELECT evidence_id,run_id,purpose,response_status,response_body_bytes,origin FROM raw_http_evidence",
            )
        }
        return [
            {
                "run_id": f["run_id"],
                "resource": f["resource_identity"],
                "parent": f["parent_resource_identity"],
                "component": f["component_kind"],
                "resource_kind": f["resource_kind"],
                "relation": f["storage_relation"],
                "state": f["source_state_key"],
                "reason": f["transition_reason"],
                "locator": f["source_version_locator"],
                "evidence": evidence.get(f["evidence_id"]),
            }
            for f in fs
        ]

    output: dict[str, Any] = {"orders": [], "runs": []}
    with tempfile.TemporaryDirectory(prefix="mail-contract-repair-r1-green-") as tmp:
        fixture = Path(tmp)
        db = fixture / "mail.db"

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: object):
                pass

            def do_GET(self):
                parts = urlsplit(self.path).path.split("/")
                message = parts[4] if len(parts) > 4 else ""
                leaf = parts[5:]
                status = 200
                content_type = "application/json"
                if message not in {"slow", "fast", "empty"}:
                    status, payload = 404, b""
                elif not leaf:
                    payload = json.dumps(
                        {
                            "id": message,
                            "changeKey": "v1-" + message,
                            "subject": "fixture",
                            "hasAttachments": message != "empty",
                        }
                    ).encode()
                else:
                    if message == "fast":
                        output["orders"].append(
                            {
                                "case": "detail_before_components",
                                "established": wait_fact(db, message, {"detail"}),
                            }
                        )
                    if leaf == ["$value"]:
                        if message == "empty":
                            status, payload = 404, b""
                        else:
                            payload = b"Subject: fixture\r\n\r\nbody"
                            content_type = "message/rfc822"
                    elif leaf == ["attachments"]:
                        values = (
                            []
                            if message == "empty"
                            else [
                                {
                                    "id": "ref",
                                    "@odata.type": "#microsoft.graph.referenceAttachment",
                                    "name": "ref",
                                    "size": 1,
                                },
                                {
                                    "id": "large",
                                    "@odata.type": "#microsoft.graph.fileAttachment",
                                    "name": "large",
                                    "size": 10000,
                                },
                                {
                                    "id": "item",
                                    "@odata.type": "#microsoft.graph.itemAttachment",
                                    "name": "item",
                                    "size": 3,
                                },
                                {
                                    "id": "raw",
                                    "@odata.type": "#microsoft.graph.fileAttachment",
                                    "name": "raw",
                                    "size": 3,
                                },
                            ]
                        )
                        payload = json.dumps({"value": values}).encode()
                    elif leaf == ["attachments", "item"]:
                        payload = json.dumps(
                            {
                                "id": "item",
                                "@odata.type": "#microsoft.graph.itemAttachment",
                                "name": "item",
                                "size": 3,
                                "item": {"subject": "embedded"},
                            }
                        ).encode()
                    elif leaf in [
                        ["attachments", "raw", "$value"],
                        ["attachments", "item", "$value"],
                    ]:
                        content_type, payload = (
                            "application/octet-stream",
                            b"\x00\xff\x01",
                        )
                    else:
                        status, payload = 404, b""
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        graph = f"http://127.0.0.1:{server.server_port}/v1.0"
        run_command = """
    import sys
    import asyncio
    import json
    import sqlite3
    import time
    from scrapy.cmdline import execute
    from message_ingest.pipelines.microsoft.outlook.email import OutlookMailPipeline
    from message_ingest.items.microsoft.outlook.email import OutlookMailDetailItem
    original = OutlookMailPipeline.process_item
    async def delayed_detail(self, item):
        if isinstance(item, OutlookMailDetailItem) and item.message_id == "slow":
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline:
                with self.catalog.Session() as session:
                    from sqlalchemy import text
                    rows = session.execute(text("SELECT component FROM mail_component_captures WHERE selection_id=:selection"), {"selection":item.selection_id}).scalars()
                    seen = set(rows)
                if {"mime", "attachments"} <= seen:
                    print("MAIL_CONTRACT_DETAIL_PIPELINE_LAST_CONFIRMED", flush=True)
                    break
                await asyncio.sleep(0.03)
            else:
                raise RuntimeError("Pipeline-last ordering was not established")
        return await original(self, item)
    OutlookMailPipeline.process_item = delayed_detail

    from message_ingest.spiders.microsoft.outlook.email.full import OutlookFullSpider
    OutlookFullSpider.graph_root = sys.argv[1]
    OutlookFullSpider.allowed_domains = ["127.0.0.1"]
    execute(["scrapy", *sys.argv[2:]])
    """
        settings = {
            "MS_GRAPH_AUTH_METHOD": "none",
            "MSGLOOM_DATABASE_URL": f"sqlite:///{db}",
            "MSGLOOM_RAW_EVIDENCE_DIR": str(fixture / "raw"),
            "MSGLOOM_SOURCE_ID": "review",
            "MSGLOOM_SOURCE_IDENTITY_REQUIRED": "False",
            "MSGLOOM_CATALOG_ENABLED": "True",
            "MSGLOOM_RAW_EVIDENCE_ENABLED": "True",
            "HTTPCACHE_ENABLED": "True",
            "HTTPCACHE_DIR": str(fixture / "cache"),
            "AUTOTHROTTLE_ENABLED": "False",
            "CONCURRENT_REQUESTS_PER_DOMAIN": "8",
            "DOWNLOAD_DELAY": "0",
            "MSGLOOM_MAX_RAW_CONTENT_BYTES": "4096",
            "LOG_LEVEL": "INFO",
        }
        try:
            for number, operation in enumerate(["refresh", "refresh", "enrich"], 1):
                cmd = [
                    sys.executable,
                    "-c",
                    textwrap.dedent(run_command),
                    graph,
                    "crawl",
                    "outlook_full",
                    "-a",
                    "message_ids=slow,fast,empty",
                    "-a",
                    f"operation={operation}",
                ]
                for key, value in settings.items():
                    cmd.extend(["-s", f"{key}={value}"])
                env = os.environ.copy()
                env["PYTHONDONTWRITEBYTECODE"] = "1"
                completed = subprocess.run(
                    cmd,
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    env=env,
                    check=False,
                )
                log = Path(str(PREFIX) + f"crawl-{number}.log")
                log.write_text(completed.stdout + completed.stderr)
                snap = summarize(db)
                output["runs"].append(
                    {
                        "number": number,
                        "operation": operation,
                        "returncode": completed.returncode,
                        "fact_count": len(snap),
                        "cache_hit": "'httpcache/hit':" in completed.stderr,
                        "already_complete": "'msgloom/crawl/enrichment/already_complete_count': 3"
                        in completed.stderr,
                        "item_errors": "'msgloom/persistence/item_error_count':"
                        in completed.stderr,
                        "detail_pipeline_last": "MAIL_CONTRACT_DETAIL_PIPELINE_LAST_CONFIRMED"
                        in completed.stdout,
                        "facts": snap,
                    }
                )
                if completed.returncode:
                    raise RuntimeError(f"Crawl {number} failed; see {log}")
            first = output["runs"][0]["facts"]
            output["checks"] = {
                "detail_first_established": all(
                    r["established"] for r in output["orders"]
                ),
                "detail_pipeline_last_established": all(
                    r["detail_pipeline_last"] for r in output["runs"][:2]
                ),
                "no_pipeline_errors": all(not r["item_errors"] for r in output["runs"]),
                "all_components_exact_bound": all(
                    f["locator"]
                    and f["locator"]["resource_version"]
                    == next(
                        p["state"]
                        for p in first
                        if p["resource"] == f["parent"]
                        and p["resource_kind"] == "message"
                    )
                    for f in first
                    if f["component"]
                ),
                "expanded_item_detail_present": any(
                    f["component"] == "item_attachment_detail:item" for f in first
                ),
                "all_surface_outcomes_readable": all(
                    json.loads(f["reason"])["profile_version"] == "outlook-mail-full-v1"
                    for f in first
                    if f["resource_kind"] == "message_surface"
                ),
                "old_canonical_evidence_in_new_run": any(
                    f["evidence"] and f["run_id"] != f["evidence"]["run_id"]
                    for f in output["runs"][1]["facts"]
                ),
                "no_work_enrich_stages_no_facts": output["runs"][2]["already_complete"]
                and output["runs"][2]["fact_count"] == output["runs"][1]["fact_count"],
            }
            if not all(output["checks"].values()):
                raise RuntimeError(str(output["checks"]))
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()
    Path(str(PREFIX) + "native-repro.json").write_text(json.dumps(output, indent=2))
    print(
        json.dumps(
            {
                "checks": output["checks"],
                "runs": [
                    {k: v for k, v in r.items() if k != "facts"} for r in output["runs"]
                ],
            },
            indent=2,
        )
    )


INTERLEAVE_RUNNER = r"""
import asyncio, json, os, sys, time
from sqlalchemy import select
from scrapy.cmdline import execute
from message_ingest.catalog.models.microsoft.outlook._email_bindings import (
    MailApplicationBinding as Binding, MailComponentCapture as Capture,
    MailInventoryPage as Page)
from message_ingest.items.microsoft.outlook.email import OutlookMailDetailItem
from message_ingest.pipelines.microsoft.outlook.email import OutlookMailPipeline
from message_ingest.spiders.microsoft.outlook.email.full import OutlookFullSpider
active = None
original_parse = OutlookFullSpider.parse_message_detail
original_process = OutlookMailPipeline.process_item

def remember(self, response, **kwargs):
    global active
    active = self
    return original_parse(self, response, **kwargs)

async def delay(self, item):
    if (sys.argv[2] == "2" and isinstance(item, OutlookMailDetailItem)
            and item.message_id == "m"):
        deadline = time.monotonic() + 8
        old = None
        while time.monotonic() < deadline:
            with self.catalog.Session() as session:
                captures = session.scalars(select(Capture).where(
                    Capture.selection_id == item.selection_id)).all()
                pages = session.scalar(select(Page.page_id).where(
                    Page.selection_id == item.selection_id))
                primary = self.store._facts().effective_fact(session, "message", "m")
                if pages and any(c.component == "mime" for c in captures):
                    old = session.scalar(select(Binding).where(
                        Binding.primary_fact_id == primary.fact_id,
                        Binding.capture_id.is_(None)))
                    if any(self.store._facts().effective_fact(
                        session, "message_surface", "m", c.component, "m"
                    ).source_version_locator.resource_version == c.parent_key
                        for c in captures if c.component == "mime"):
                        raise RuntimeError("Pending v2 displaced v1 before primary")
                    break
            await asyncio.sleep(0.03)
        else:
            raise RuntimeError("Native v2 pending barrier was not established")
        pin = dict(resource_version=primary.source_state_key,
                   selection_id=old.selection_id,
                   parent_evidence_id=json.loads(old.payload)["parent_evidence_id"])
        request = active._message_mime_request("m", **pin)
        active.crawler.engine.crawl(request.replace(url=request.url + "?old=1"))
        active.crawler.engine.crawl(active._attachments_request(
            "m", page_number=1, url=active.graph_root +
            "/me/messages/m/attachments?old=1", verbatim_url=True, **pin))
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            with self.catalog.Session() as session:
                rows = session.scalars(select(Capture).where(
                    Capture.selection_id == old.selection_id)).all()
                seen = {r.component for r in rows
                        if json.loads(r.payload)["run_id"] == item.run_id}
            if {"mime", "attachment_metadata"} <= seen:
                print("NATIVE_V2_PENDING_OLD_V1_COMPONENTS_BEFORE_V2_PRIMARY", flush=True)
                break
            await asyncio.sleep(0.03)
        else:
            raise RuntimeError("Delayed native v1 components did not finish")
    if (os.environ.get("MAIL_FIXTURE_FAIL_PRIMARY") == "True"
            and sys.argv[2] == "2" and isinstance(item, OutlookMailDetailItem)
            and item.message_id == "m"):
        from sqlalchemy import text
        with self.catalog.writer_session() as session:
            session.execute(text(
                "CREATE TRIGGER fail_native_primary BEFORE INSERT ON "
                "acquisition_facts WHEN json_extract(NEW.payload, '$.resource_kind')='message' "
                "BEGIN SELECT RAISE(ABORT, 'native primary failure'); END"))
        try:
            return await original_process(self, item)
        except Exception as exc:
            if "native primary failure" not in str(exc):
                raise RuntimeError("Unexpected native failure injection") from exc
            print("NATIVE_PRIMARY_FAILURE_ROLLED_BACK", flush=True)
            raise
        finally:
            with self.catalog.writer_session() as session:
                session.execute(text("DROP TRIGGER fail_native_primary"))
    return await original_process(self, item)

OutlookFullSpider.parse_message_detail = remember
OutlookMailPipeline.process_item = delay
OutlookFullSpider.graph_root = sys.argv[1]
OutlookFullSpider.allowed_domains = ["127.0.0.1"]
execute(["scrapy", *sys.argv[3:]])
"""


def test_pipeline_cancellation_awaits_accepted_writer(setup, monkeypatch):
    """Cancellation cannot release the shared lock before an accepted write."""
    import asyncio

    import pytest

    from message_ingest.items.microsoft.outlook.email import OutlookMailDetailItem

    _, pipeline, _ = setup
    entered, finish, committed = (threading.Event() for _ in range(3))

    def blocked(item):
        entered.set()
        if not finish.wait(5):
            raise RuntimeError("Writer release barrier expired")
        committed.set()
        return ()

    monkeypatch.setattr(pipeline, "_process_item_sync", blocked)

    async def exercise():
        item = OutlookMailDetailItem(
            message_id="m",
            raw={"id": "m"},
            source_response_url="fixture",
            observed_at="2026-10-03T00:00:00+00:00",
            evidence_id="saved",
            run_id="cancelled",
        )
        task = asyncio.create_task(pipeline.process_item(item))
        if not await asyncio.to_thread(entered.wait, 5):
            pytest.fail("Accepted writer did not start")
        task.cancel()
        await asyncio.sleep(0)
        if task.done() or not pipeline._write_lock.locked():
            pytest.fail("Cancellation escaped while the accepted writer was active")
        finish.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        if not committed.is_set() or pipeline._write_lock.locked():
            pytest.fail("Cancellation did not await commit and release the lock")

    asyncio.run(exercise())
