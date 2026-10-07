"""Use local Graph bytes and real Full crawls for release revalidation tests."""

import json
import subprocess
import sys
from functools import wraps
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit

import pytest
from sqlalchemy import select

from message_ingest.acquisition.handoff import AcquisitionStream
from message_ingest.catalog import Catalog
from message_ingest.catalog.models.acquisition import RawHttpEvidence
from message_ingest.catalog.models.handoff import (
    AcquisitionFact,
    AcquisitionReleaseEntryFact,
    AcquisitionReleaseGroup,
)
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore

ROOT = Path(__file__).parents[1]
COMMAND = """
import sys
from scrapy.cmdline import execute
import message_ingest.settings as settings
from message_ingest.spiders.microsoft.outlook.email.full import OutlookFullSpider
from message_ingest.spiders.microsoft.outlook.calendar.full import OutlookCalendarFullSpider
for cls in (OutlookFullSpider, OutlookCalendarFullSpider):
    cls.graph_root = sys.argv[1]
    cls.allowed_domains = ["127.0.0.1"]
extension = "message_ingest.extensions.handoff.HandoffReleaseExtension"
settings.EXTENSIONS[extension] = 70 if sys.argv[2] == "enabled" else None
sys.path.insert(0, str(__import__("pathlib").Path.cwd() / "tests"))
from handoff_full_crawl_helpers import install_failure
install_failure(sys.argv[3])
execute(["scrapy", *sys.argv[4:]])
"""


@pytest.fixture
def full_graph_server():
    """Serve exact targets with a controllable attachment inventory outcome."""
    seen = []
    policy = {"attachments_status": 200}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def do_GET(self):
            path = urlsplit(self.path).path
            seen.append(path)
            bases = tuple(
                f"/v1.0/me/{kind}/{target}"
                for kind in ("messages", "events")
                for target in ("one", "two")
            )
            status = 200
            content_type = "application/json"
            if path in bases:
                payload = {"id": path.rsplit("/", 1)[1], "changeKey": "v1"}
                if "/events/" in path:
                    payload["type"] = "singleInstance"
            elif path in tuple(base + "/attachments" for base in bases):
                status = policy["attachments_status"]
                payload = (
                    {"value": []}
                    if status == 200
                    else {"error": {"code": "ErrorAccessDenied", "message": "Denied"}}
                )
            elif path in tuple(base + "/$value" for base in bases[:2]):
                payload = b"From: sender@example.test\r\nSubject: Test\r\n\r\nBody\r\n"
                content_type = "message/rfc822"
            else:
                self.send_error(404)
                return
            body = (
                payload if isinstance(payload, bytes) else json.dumps(payload).encode()
            )
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1.0", seen, policy
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def run_full(
    tmp_path,
    root,
    family,
    *,
    operation,
    enabled,
    direct=False,
    cache=False,
    expected_returncode=0,
    targets="one",
    failure="",
):
    """Run a bounded native lifecycle with an explicit release opt-in.

    Expected injected failures allow error output for native signal checks.
    Ordinary runs reject every traceback. No case in this helper sets JOBDIR.
    """
    if direct:
        name = "outlook_full" if family == "mail" else "outlook_calendar_full"
        target = "message_ids" if family == "mail" else "event_ids"
        command = [
            "crawl",
            name,
            "-a",
            f"{target}={targets}",
            "-a",
            f"operation={operation}",
        ]
    else:
        command = [
            "microsoft",
            "outlook",
            family,
            "full",
            *targets.split(","),
            "--operation",
            operation,
        ]
    settings = {
        "MS_GRAPH_AUTH_METHOD": "none",
        "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.db'}",
        "MSGLOOM_RAW_EVIDENCE_DIR": str(tmp_path / "raw"),
        "MSGLOOM_SOURCE_ID": "source",
        "MSGLOOM_SOURCE_IDENTITY_REQUIRED": "False",
        "MSGLOOM_CATALOG_ENABLED": "True",
        "MSGLOOM_RAW_EVIDENCE_ENABLED": "True",
        "HTTPCACHE_ENABLED": str(cache),
        "HTTPCACHE_DIR": str(tmp_path / "cache"),
        "AUTOTHROTTLE_ENABLED": "False",
        "RETRY_ENABLED": "False",
        # Provider retries have their own budget; reach the injected 503 now.
        "MS_GRAPH_ERROR_MAX_RETRIES": "0",
        "LOG_LEVEL": "INFO",
    }
    if failure == "item":
        provider = "email" if family == "mail" else "calendar"
        pipeline = (
            "OutlookMailPipeline" if family == "mail" else "OutlookCalendarPipeline"
        )
        settings["ITEM_PIPELINES"] = json.dumps(
            {
                "message_ingest.pipelines.evidence.RawEvidencePipeline": 200,
                "message_ingest.acquisition.evidence_link.EvidenceLinkPipeline": 250,
                f"message_ingest.pipelines.microsoft.outlook.{provider}.{pipeline}": 300,
                "handoff_full_crawl_helpers.TargetItemFailure": 400,
            }
        )
    for key, value in settings.items():
        command.extend(["-s", f"{key}={value}"])
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            COMMAND,
            root,
            "enabled" if enabled else "disabled",
            failure,
            *command,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode != expected_returncode or (
        not failure and "Traceback (most recent call last)" in result.stderr
    ):
        pytest.fail(result.stderr)
    return result.stderr


def snapshot(tmp_path, family):
    """Read immutable provenance and publication, retaining exact fact bytes."""
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.db'}")
    try:
        with catalog.Session() as session:
            facts = {
                fact_id: payload
                for fact_id, payload in session.execute(
                    select(AcquisitionFact.fact_id, AcquisitionFact.payload)
                ).all()
            }
            evidence = set(session.scalars(select(RawHttpEvidence.evidence_id)))
            groups = [
                json.loads(value)
                for value in session.scalars(select(AcquisitionReleaseGroup.payload))
            ]
            members = set(session.scalars(select(AcquisitionReleaseEntryFact.fact_id)))
        stream = (
            AcquisitionStream.OUTLOOK_MAIL
            if family == "mail"
            else AcquisitionStream.OUTLOOK_CALENDAR
        )
        entries = AcquisitionHandoffStore(catalog).list_release_entries(
            "source", stream
        )
        return {
            "facts": facts,
            "evidence": evidence,
            "groups": groups,
            "members": members,
            "entries": entries,
        }
    finally:
        catalog.close()


def expected_full_members(state, family, *, limited):
    """Select the exact facts required by this one-target empty inventory."""
    primary, surface, stream, components = {
        "mail": (
            "message",
            "message_surface",
            AcquisitionStream.OUTLOOK_MAIL,
            ("detail", "mime", "attachments"),
        ),
        "calendar": (
            "calendar_event",
            "calendar_event_surface",
            AcquisitionStream.OUTLOOK_CALENDAR,
            ("detail", "attachments"),
        ),
    }[family]
    expected = set()
    for component in (None, *components):
        matches = []
        for fact_id, payload in state["facts"].items():
            fact = json.loads(payload)
            if (
                fact["source_id"] == "source"
                and fact["stream"] == stream
                and fact["resource_identity"] == "one"
                and fact["resource_kind"] == (primary if component is None else surface)
                and fact["component_kind"] == component
                and fact["parent_resource_kind"]
                == (None if component is None else primary)
                and fact["parent_resource_identity"]
                == (None if component is None else "one")
            ):
                matches.append((fact_id, fact))
        if len(matches) != 1:
            pytest.fail(f"Fixture requires one exact {family} {component!r} fact")
        fact_id, fact = matches[0]
        if fact["evidence_id"] not in state["evidence"]:
            pytest.fail("Required fixture fact lacks persisted source evidence")
        if component is not None:
            status = (
                "unauthorized" if limited and component == "attachments" else "acquired"
            )
            if json.loads(fact["transition_reason"]) != {
                "status": status,
                "profile_version": f"outlook-{family}-full-v1",
            }:
                pytest.fail("Required fixture surface has the wrong terminal outcome")
        expected.add(fact_id)
    return expected


class TargetItemFailure:
    """Fail one detail item after awaited production persistence completes."""

    def process_item(self, item):
        """Keep the target identity on the native ``item_error`` signal."""
        if type(item).__name__ in {
            "OutlookMailDetailItem",
            "OutlookCalendarEventItem",
        }:
            target = getattr(item, "message_id", None) or getattr(
                item, "event_id", None
            )
            if target == "one":
                raise RuntimeError("task8 injected item failure")
        return item


def install_failure(failure):
    """Inject callback failure after real output; retain named callbacks.

    Requests still point at bound Spider methods. These cases do not set
    JOBDIR and do not claim resume qualification. Item injection is configured
    at command-line priority so Calendar's pipeline defaults cannot replace it.
    """
    if failure != "callback":
        return
    from message_ingest.spiders.microsoft.outlook.calendar.full import (
        OutlookCalendarFullSpider,
    )
    from message_ingest.spiders.microsoft.outlook.email.full import OutlookFullSpider

    def wrap(callback):
        @wraps(callback)
        def failing(self, response, **kwargs):
            yield from callback(self, response, **kwargs)
            target = kwargs.get("message_id") or kwargs.get("event_id")
            if target == "one":
                raise RuntimeError("task8 injected callback failure")

        return failing

    for cls, name in (
        (OutlookFullSpider, "parse_message_detail"),
        (OutlookCalendarFullSpider, "parse_event_detail"),
    ):
        setattr(cls, name, wrap(getattr(cls, name)))
