"""Selected Mail inventories retain exact pages and bounded member bindings."""

import hashlib
import json
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.engine import make_url

from message_ingest.catalog.models.acquisition import RawHttpEvidence
from message_ingest.items.microsoft.outlook.email import OutlookMailInventoryPageItem

PROFILE = "outlook-mail-full-v1"
NOW = "2026-09-28T00:00:00+00:00"


def page_evidence(store, evidence_id, message, payload, when=NOW, url=None):
    """Save controlled Graph bytes with the actual selected request URL."""
    database = make_url(store.catalog.database_url).database
    if database is None:
        pytest.fail("Page fixture requires a file-backed catalog")
    root = Path(database).parent
    body = json.dumps(payload).encode() if payload is not None else b""
    digest = hashlib.sha256(body).hexdigest()
    path = root / (digest + ".json")
    path.write_bytes(body)
    url = url or f"https://graph.test/messages/{message}/attachments"
    store.catalog.evidence.record(
        RawHttpEvidence(
            evidence_id=evidence_id,
            source_id=store.source_id,
            run_id="fixture-run",
            purpose="attachments-list",
            observed_at=when,
            origin="network",
            request_fingerprint=hashlib.sha256(url.encode()).hexdigest(),
            request_url=url,
            request_method="GET",
            request_headers={},
            request_body_sha256=digest,
            request_body_path=str(path),
            request_body_bytes=len(body),
            response_url=url,
            response_status=200,
            response_headers={},
            response_body_sha256=digest,
            response_body_path=str(path),
            response_body_bytes=len(body),
            response_flags=[],
            error_type=None,
            error_message=None,
        )
    )


def seed_inventory(
    store,
    message,
    selection,
    parent,
    parent_evidence,
    members,
    when=NOW,
    status="acquired",
    profile: str | None = PROFILE,
):
    """Seed an explicit selected one-page fixture, never historical union."""
    if profile is None:
        raise ValueError("Exact inventory requires a declared profile")
    page_id = uuid4().hex
    page_evidence(store, page_id, message, {"value": members}, when)
    captures = []
    for member in members:
        capture_id = uuid4().hex
        captures.append(capture_id)
        store.upsert_attachment(
            run_id="fixture-run",
            message_id=message,
            attachment=member,
            evidence_id=page_id,
            observed_at=when,
            resource_version=parent,
            selection_id=selection,
            parent_evidence_id=parent_evidence,
            profile_version=profile,
            capture_id=capture_id,
        )
    item = OutlookMailInventoryPageItem(
        message_id=message,
        selection_id=selection,
        resource_version=parent,
        parent_evidence_id=parent_evidence,
        inventory_id=page_id,
        page_id=page_id,
        previous_page_id=None,
        page_number=1,
        member_capture_ids=tuple(captures),
        status=status,
        profile_version=profile,
        evidence_id=page_id,
        observed_at=when,
        run_id="fixture-run",
    )
    return store.record_inventory_page(item)


from test_mail_authority_associations import T1, T2, T3, _mime, primary
from test_outlook_mail_handoff_facts import setup as setup  # noqa: PLC0414


def make_page(
    store,
    parent,
    members,
    number,
    *,
    previous=None,
    inventory="chain",
    terminal=True,
    status="acquired",
    metadata=True,
    when=T2,
):
    """Create controlled immutable page/member evidence for ordering tests."""
    page_id = uuid4().hex
    payload = {"value": members}
    url = f"https://graph.test/messages/m1/attachments?page={number}"
    if not terminal:
        payload["@odata.nextLink"] = (
            f"https://graph.test/messages/m1/attachments?page={number + 1}"
        )
    page_evidence(
        store, page_id, "m1", payload if status == "acquired" else None, when, url
    )
    captures = tuple(uuid4().hex for _ in members)
    item = OutlookMailInventoryPageItem(
        message_id="m1",
        selection_id="selected",
        resource_version=parent,
        parent_evidence_id="detail-selected",
        inventory_id=inventory,
        page_id=page_id,
        previous_page_id=previous,
        page_number=number,
        member_capture_ids=captures,
        status=status,
        profile_version=PROFILE,
        evidence_id=page_id,
        observed_at=when,
        run_id="selected",
    )
    if metadata:
        persist_members(store, item, members)
    return item


def persist_members(store, item, members):
    """Persist the exact references supplied by an inventory response."""
    for value, capture_id in zip(members, item.member_capture_ids, strict=True):
        store.upsert_attachment(
            run_id=item.run_id,
            message_id=item.message_id,
            attachment=value,
            evidence_id=item.evidence_id,
            observed_at=item.observed_at,
            resource_version=item.resource_version,
            selection_id=item.selection_id,
            parent_evidence_id=item.parent_evidence_id,
            profile_version=item.profile_version,
            capture_id=capture_id,
        )


def base(setup):
    """Complete detail and MIME while leaving inventory obligations open."""
    crawler, _, store = setup
    fact = primary(crawler, store, "A", "selected", T1).fact
    _mime(crawler, store, "selected", "A", T1)
    return store, fact.source_state_key


@pytest.mark.parametrize(
    "status",
    [
        "unavailable",
        "unauthorized",
        "unsupported",
        "omitted_size_limit",
    ],
)
def test_later_page_terminal_outcome_does_not_import_partial_members(setup, status):
    """Terminal limitations retain partial history without absence claims."""
    store, parent = base(setup)
    first = make_page(store, parent, [{"id": "partial"}], 1, terminal=False)
    store.record_inventory_page(first)
    last = make_page(store, parent, [], 2, previous=first.page_id, status=status)
    store.record_inventory_page(last)
    state = store.full_binding_state(message_id="m1")
    if state["surfaces"]["attachments"]["status"] != status:
        pytest.fail("Terminal limitation was rewritten as acquired empty")
    if state["attachments"] or not store.full_binding_complete(message_id="m1"):
        pytest.fail("Partial historical members became current obligations")


@pytest.mark.parametrize("mutation", ["target", "predecessor", "duplicate"])
def test_invalid_page_chain_fails_closed(setup, mutation):
    """Cross-target links and conflicting duplicate members cannot seal."""
    store, parent = base(setup)
    first = make_page(store, parent, [{"id": "a", "name": "first"}], 1, terminal=False)
    store.record_inventory_page(first)
    members = [{"id": "a", "name": "conflict"}] if mutation == "duplicate" else []
    last = make_page(store, parent, members, 2, previous=first.page_id)
    if mutation == "target":
        last.message_id = "other"
    elif mutation == "predecessor":
        last.page_number = 3
    with pytest.raises(ValueError):
        store.record_inventory_page(last)
    if store.full_binding_complete(message_id="m1"):
        pytest.fail("Invalid traversal became complete")


@pytest.mark.parametrize("table", ["mail_inventory_pages", "mail_inventory_members"])
def test_page_and_member_insert_failure_roll_back_inventory(setup, table):
    """Partial page/member storage cannot survive the writer transaction."""
    from sqlalchemy import text
    from sqlalchemy.exc import DatabaseError

    store, parent = base(setup)
    item = make_page(store, parent, [{"id": "a"}], 1)
    with store.catalog.writer_session() as session:
        session.execute(
            text(
                f"CREATE TRIGGER fail_inventory BEFORE INSERT ON {table} "
                "BEGIN SELECT RAISE(ABORT, 'inventory failure'); END"
            )
        )
    with pytest.raises(DatabaseError, match="inventory failure"):
        store.record_inventory_page(item)
    with store.catalog.Session() as session:
        if session.execute(text("SELECT COUNT(*) FROM mail_inventory_pages")).scalar():
            pytest.fail("Failed page transaction left immutable page rows")
    if "attachments" in store.get_surfaces(message_id="m1"):
        pytest.fail("Failed page transaction left an effective inventory")


def test_equivalent_inventory_keeps_one_exact_manifest_per_fact(setup):
    """Fresh equivalent pages cannot replace an existing fact's manifest."""
    from sqlalchemy import select

    from message_ingest.catalog.models.microsoft.outlook._email_bindings import (
        MailApplicationBinding,
    )

    store, parent = base(setup)
    first = seed_inventory(store, "m1", "selected", parent, "detail-selected", [], T2)
    seed_inventory(store, "m1", "selected", parent, "detail-selected", [], T3)
    with store.catalog.Session() as session:
        links = session.scalars(
            select(MailApplicationBinding).where(
                MailApplicationBinding.fact_id == first.fact.fact_id,
                MailApplicationBinding.capture_id.is_not(None),
            )
        ).all()
    if len(links) != 1:
        pytest.fail("An existing inventory fact acquired a second provenance manifest")
    state = store.full_binding_state(message_id="m1")
    if state["surfaces"]["attachments"]["evidence_id"] != first.fact.evidence_id:
        pytest.fail("Planning projection no longer matches its exact effective fact")


@pytest.mark.parametrize("mode", ["empty", "reduced", "terminal", "partial", "retry"])
def test_native_inventory_changes_and_delayed_parent_gap_only(tmp_path, mode):
    """Native interleavings retain v2 through delayed v1 and reacquire gaps."""
    import os
    import subprocess
    import sys
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from urllib.parse import parse_qs, urlsplit

    from test_mail_contract_native import INTERLEAVE_RUNNER

    from message_ingest.acquisition.microsoft.outlook.email.planner import (
        pending_full_v1_message_ids,
    )
    from message_ingest.catalog import Catalog
    from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore

    requests = []
    phase = 1

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def do_GET(self):
            parts = urlsplit(self.path)
            path = parts.path.split("/")
            message, leaf = path[4], path[5:]
            query = parse_qs(parts.query)
            old = "old" in query
            requests.append((phase, message, leaf, old))
            status, content = 200, "application/json"
            version = 1 if phase == 1 or old or message == "steady" else 2
            if not leaf:
                payload = {"id": message, "changeKey": f"v{version}-{message}"}
            elif leaf == ["$value"]:
                payload, content = b"stable MIME", "message/rfc822"
            elif leaf == ["attachments"]:
                member = {
                    "id": "a",
                    "name": f"v{version}",
                    "size": 3,
                    "@odata.type": "#microsoft.graph.fileAttachment",
                }
                payload: dict | bytes = {"value": [member]}
                if message == "steady" or (phase > 1 and mode == "empty" and not old):
                    payload = {"value": []}
                elif query.get("page") == ["2"]:
                    payload = {
                        "value": [
                            {
                                "id": "removed",
                                "@odata.type": "#microsoft.graph.referenceAttachment",
                            }
                        ]
                    }
                    if phase > 1:
                        payload = {"value": []}
                        if phase == 2 and mode in {"terminal", "partial"}:
                            status = 404 if mode == "terminal" else 500
                            payload = b""
                elif not old and (phase == 1 or mode in {"terminal", "partial"}):
                    payload["@odata.nextLink"] = (
                        f"http://127.0.0.1:{server.server_port}"
                        f"/v1.0/me/messages/{message}/attachments?page=2"
                    )
            else:
                content, payload = "application/octet-stream", b"abc"
                if phase == 2 and mode == "reduced":
                    status, payload = 500, b""
            body = (
                json.dumps(payload).encode() if isinstance(payload, dict) else payload
            )
            self.send_response(status)
            self.send_header("Content-Type", content)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    database = tmp_path / "native.db"
    settings = {
        "MS_GRAPH_AUTH_METHOD": "none",
        "MSGLOOM_DATABASE_URL": f"sqlite:///{database}",
        "MSGLOOM_RAW_EVIDENCE_DIR": str(tmp_path / "raw"),
        "MSGLOOM_SOURCE_ID": "native",
        "MSGLOOM_SOURCE_IDENTITY_REQUIRED": "False",
        "MSGLOOM_CATALOG_ENABLED": "True",
        "MSGLOOM_RAW_EVIDENCE_ENABLED": "True",
        "HTTPCACHE_ENABLED": "False",
        "AUTOTHROTTLE_ENABLED": "False",
        "DOWNLOAD_DELAY": "0",
        "LOG_LEVEL": "INFO",
    }
    snapshots = []
    try:
        for phase in range(1, 5):
            start = len(requests)
            operation = (
                "refresh" if phase < 3 or (phase == 3 and mode == "retry") else "enrich"
            )
            command = [
                sys.executable,
                "-c",
                INTERLEAVE_RUNNER,
                f"http://127.0.0.1:{server.server_port}/v1.0",
                str(phase),
                "crawl",
                "outlook_full",
                "-a",
                "message_ids=m,steady",
                "-a",
                f"operation={operation}",
            ]
            for key, value in settings.items():
                command.extend(["-s", f"{key}={value}"])
            completed = subprocess.run(
                command,
                cwd=Path(__file__).resolve().parents[1],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
                env={
                    **os.environ,
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "MAIL_FIXTURE_FAIL_PRIMARY": str(mode == "retry"),
                },
            )
            log = completed.stdout + completed.stderr
            (tmp_path / f"phase-{phase}.log").write_text(log)
            expected_failure = mode == "retry" and phase == 2
            if expected_failure and (
                "NATIVE_PRIMARY_FAILURE_ROLLED_BACK" not in log
                or "'msgloom/persistence/item_error_count': 1," not in log
            ):
                pytest.fail("Native primary failure injection did not execute")
            if not expected_failure and (
                completed.returncode
                or "'msgloom/persistence/item_error_count':" in log
                or "Traceback" in log
            ):
                pytest.fail(f"Native phase {phase} failed: {log[-6000:]}")
            if (
                phase == 2
                and "NATIVE_V2_PENDING_OLD_V1_COMPONENTS_BEFORE_V2_PRIMARY" not in log
            ):
                pytest.fail("Required native cross-response ordering was not proven")
            catalog = Catalog(settings["MSGLOOM_DATABASE_URL"])
            try:
                store = OutlookMailStore(catalog, source_id="native")
                pending = pending_full_v1_message_ids(store)
                state = store.full_binding_state(message_id="m")
                if expected_failure and (
                    state["resource_version"]
                    != snapshots[0]["state"]["resource_version"]
                ):
                    pytest.fail("Failed native primary displaced its predecessor")
                snapshots.append(
                    {"pending": pending, "state": state, "requests": requests[start:]}
                )
                if not store.full_binding_complete(message_id="steady"):
                    pytest.fail("Unrelated target lost its complete profile")
                if (
                    phase >= 2
                    and not expected_failure
                    and state["attachments"]
                    and any(a["name"] != "v2" for a in state["attachments"])
                ):
                    pytest.fail("Delayed v1 metadata replaced selected v2")
            finally:
                catalog.close()
        if snapshots[0]["pending"]:
            pytest.fail("Initial multi-page inventory did not complete")
        wanted = ("m",) if mode in {"partial", "reduced"} else ()
        if snapshots[1]["pending"] != wanted:
            pytest.fail("New inventory incorrectly counted history or missing work")
        third = snapshots[2]["requests"]
        if mode == "reduced" and [r[2] for r in third] != [
            ["attachments", "a", "$value"]
        ]:
            pytest.fail("Gap-only enrich requested obsolete or complete surfaces")
        if mode in {"empty", "terminal"} and third:
            pytest.fail("Complete empty/terminal inventory performed enrich work")
        if snapshots[2]["pending"] or snapshots[3]["requests"]:
            pytest.fail("Reacquired profile did not settle to exact no-work")
        (tmp_path / "native-inventory.json").write_text(json.dumps(snapshots, indent=2))
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
