"""Exercise Contacts snapshots and custom-folder delta through real Scrapy crawls."""

import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urlsplit

import pytest
from sqlalchemy import select

from message_ingest.catalog import Catalog
from message_ingest.catalog.models.acquisition import (
    RawHttpEvidence,
    SourceTargetBinding,
)
from message_ingest.catalog.models.microsoft.contacts import (
    ContactDeltaCheckpoint,
    ContactFolderPresence,
    ContactPresence,
    ContactRecord,
    ContactsSnapshotState,
)

ROOT = Path(__file__).resolve().parents[1]
FOLDER_PARENT = "folder-parent"
FOLDER_CHILD = "folder-child"
FOLDER_OTHER = "folder-other"
DELTA_FOLDER = "folder-delta"


@pytest.fixture
def contacts_server():
    state = {"mode": "normal", "delta_round": 0}
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def do_GET(self):
            requests.append(self.path)
            split = urlsplit(self.path)
            path = split.path
            query = parse_qs(split.query)
            payload = None
            status = 200

            if state["mode"] == "empty" and (
                path.endswith(("/me/contacts", "/me/contactFolders"))
            ):
                payload = {"value": []}
            elif path.endswith("/me/contacts"):
                payload = {
                    "value": [
                        {
                            "id": "default-one",
                            "displayName": "",
                            "emailAddresses": [],
                            "businessPhones": [],
                            "homePhones": [],
                            "mobilePhone": "",
                        }
                    ],
                    "@odata.nextLink": origin + "/opaque/default?cursor=opaque-a",
                }
            elif path == "/opaque/default":
                payload = {"value": [{"id": "default-two", "displayName": ""}]}
            elif path.endswith("/me/contactFolders"):
                payload = {
                    "value": [
                        {
                            "id": FOLDER_PARENT,
                            "displayName": "",
                            "parentFolderId": "synthetic-parent",
                        }
                    ],
                    "@odata.nextLink": origin + "/opaque/folders?cursor=opaque-b",
                }
            elif path == "/opaque/folders":
                payload = {"value": [{"id": FOLDER_OTHER, "displayName": ""}]}
            elif path.endswith(f"/contactFolders/{FOLDER_PARENT}/contacts"):
                if state["mode"] == "request_failure":
                    status = 403
                    payload = {
                        "error": {"code": "ErrorAccessDenied", "message": "synthetic"}
                    }
                else:
                    payload = {"value": [{"id": "parent-contact", "companyName": ""}]}
            elif path.endswith(f"/contactFolders/{FOLDER_PARENT}/childFolders"):
                if state["mode"] == "callback_failure":
                    payload = {"value": [{"displayName": "missing-id"}]}
                else:
                    payload = {
                        "value": [
                            {
                                "id": FOLDER_CHILD,
                                "displayName": "",
                                "parentFolderId": FOLDER_PARENT,
                            }
                        ]
                    }
            elif path.endswith(f"/contactFolders/{FOLDER_CHILD}/contacts"):
                payload = {
                    "value": [{"id": "child-one", "jobTitle": ""}],
                    "@odata.nextLink": origin
                    + "/opaque/child-contacts?cursor=opaque-c",
                }
            elif path == "/opaque/child-contacts":
                payload = {"value": [{"id": "child-two", "department": ""}]}
            elif path.endswith(
                (
                    f"/contactFolders/{FOLDER_CHILD}/childFolders",
                    f"/contactFolders/{FOLDER_OTHER}/contacts",
                    f"/contactFolders/{FOLDER_OTHER}/childFolders",
                )
            ):
                payload = {"value": []}
            elif path.endswith(f"/contactFolders/{DELTA_FOLDER}/contacts/delta"):
                if "$select" not in query:
                    status = 400
                    payload = {"error": {"code": "MissingProjection"}}
                else:
                    payload = {
                        "value": [
                            {
                                "id": "delta-one",
                                "displayName": "",
                                "companyName": "first",
                            },
                            {"id": "delta-gone", "@removed": {"reason": "deleted"}},
                        ],
                        "@odata.nextLink": origin + "/opaque/delta?skip=opaque-d",
                    }
            elif path == "/opaque/delta":
                payload = {
                    "value": [{"id": "delta-two", "displayName": ""}],
                    "@odata.deltaLink": origin
                    + "/opaque/checkpoint?$deltatoken=opaque-terminal",
                }
            elif path == "/opaque/checkpoint":
                if state["mode"] == "delta_request_failure":
                    status = 403
                    payload = {
                        "error": {"code": "ErrorAccessDenied", "message": "synthetic"}
                    }
                else:
                    state["delta_round"] += 1
                    payload = {
                        "value": [{"id": "delta-one", "companyName": "second"}],
                        "@odata.deltaLink": origin
                        + f"/opaque/checkpoint-{state['delta_round']}?$deltatoken=opaque-next",
                    }
            else:
                status = 404
                payload = {"error": {"code": "FixtureRouteMissing"}}

            body = json.dumps(payload).encode()
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
        yield origin, state, requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _settings(tmp_path, origin):
    return {
        "MS_GRAPH_SERVICE_ROOT": origin + "/v1.0",
        "MS_GRAPH_AUTH_METHOD": "none",
        "MSGLOOM_SOURCE_IDENTITY_REQUIRED": "False",
        "MSGLOOM_CONTACTS_SOURCE_ID": "contacts-fixture",
        "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
        "MSGLOOM_RAW_EVIDENCE_DIR": str(tmp_path / "raw"),
        "MSGLOOM_CATALOG_ENABLED": "True",
        "MSGLOOM_RAW_EVIDENCE_ENABLED": "True",
        "HTTPCACHE_ENABLED": "False",
        "AUTOTHROTTLE_ENABLED": "False",
        "LOG_LEVEL": "INFO",
    }


def _run(tmp_path, origin, *args):
    command = [sys.executable, "-m", "scrapy", *args]
    for key, value in _settings(tmp_path, origin).items():
        command.extend(["-s", f"{key}={value}"])
    return subprocess.run(
        command, cwd=ROOT, capture_output=True, text=True, timeout=30, check=False
    )


def test_real_contacts_sync_recurses_paginates_and_promotes_clean_snapshot(
    tmp_path, contacts_server
):
    origin, state, requests = contacts_server
    first = _run(
        tmp_path,
        origin,
        "microsoft",
        "contacts",
        "sync",
        "--page-size",
        "2",
    )
    if first.returncode:
        pytest.fail(first.stderr)
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        with catalog.Session() as session:
            folders = session.scalars(select(ContactFolderPresence)).all()
            contacts = session.scalars(select(ContactPresence)).all()
            if len(folders) != 3 or not all(row.is_present for row in folders):
                pytest.fail("Recursive custom-folder inventory was not authoritative")
            if len(contacts) != 5 or not all(row.is_present for row in contacts):
                pytest.fail("Default/custom paginated contacts were not promoted")
            if session.scalars(select(SourceTargetBinding)).first() is not None:
                pytest.fail("Contacts must not create Outlook mailbox target bindings")
            evidence = session.scalars(select(RawHttpEvidence)).all()
            if not evidence:
                pytest.fail("Contacts crawl did not retain raw HTTP evidence")
            evidence_ids = {row.evidence_id for row in evidence}
            for row in session.scalars(select(ContactRecord)).all():
                if row.latest_evidence_id not in evidence_ids:
                    pytest.fail("Semantic Contacts state is not linked to raw evidence")
        second = _run(tmp_path, origin, "microsoft", "contacts", "sync")
        if second.returncode:
            pytest.fail(second.stderr)
        with catalog.Session() as session:
            if len(session.scalars(select(ContactRecord)).all()) != 5:
                pytest.fail("Repeated clean sync duplicated contact state")
        state["mode"] = "empty"
        third = _run(tmp_path, origin, "microsoft", "contacts", "sync")
        if third.returncode:
            pytest.fail(third.stderr)
        with catalog.Session() as session:
            if any(
                row.is_present for row in session.scalars(select(ContactPresence)).all()
            ):
                pytest.fail("Complete empty snapshot did not publish contact absence")
            if any(
                row.is_present
                for row in session.scalars(select(ContactFolderPresence)).all()
            ):
                pytest.fail("Complete empty snapshot did not publish folder absence")
            if len(session.scalars(select(ContactRecord)).all()) != 5:
                pytest.fail("Snapshot absence deleted historical provider state")
            if session.get(ContactsSnapshotState, "contacts-fixture") is None:
                pytest.fail("Authoritative snapshot state was not committed")
    finally:
        catalog.close()
    if not any("/opaque/default?cursor=opaque-a" in path for path in requests):
        pytest.fail("Opaque default-contact continuation was not followed verbatim")
    if not any("/opaque/child-contacts?cursor=opaque-c" in path for path in requests):
        pytest.fail("Nested custom-folder contact pagination was incomplete")


@pytest.mark.parametrize("mode", ["request_failure", "callback_failure"])
def test_real_contacts_failure_retains_evidence_and_blocks_snapshot_promotion(
    tmp_path, contacts_server, mode
):
    origin, state, _requests = contacts_server
    state["mode"] = mode
    result = _run(tmp_path, origin, "microsoft", "contacts", "sync")
    if result.returncode != 1:
        pytest.fail(f"{mode} must fail authoritative sync: {result.stderr}")
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        with catalog.Session() as session:
            if session.get(ContactsSnapshotState, "contacts-fixture") is not None:
                pytest.fail("Failed traversal promoted authoritative snapshot state")
            if session.scalars(select(RawHttpEvidence)).first() is None:
                pytest.fail("Failed traversal lost raw provider evidence")
    finally:
        catalog.close()


def test_real_custom_folder_delta_uses_opaque_pages_tombstones_and_checkpoint(
    tmp_path, contacts_server
):
    origin, _state, requests = contacts_server
    first = _run(
        tmp_path,
        origin,
        "crawl",
        "microsoft_contacts_delta",
        "-a",
        f"folder_id={DELTA_FOLDER}",
    )
    if first.returncode:
        pytest.fail(first.stderr)
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        with catalog.Session() as session:
            checkpoint = session.get(
                ContactDeltaCheckpoint,
                {"source_id": "contacts-fixture", "folder_id": DELTA_FOLDER},
            )
            if checkpoint is None or checkpoint.revision != 1:
                pytest.fail("Initial custom-folder delta checkpoint was not promoted")
            if checkpoint.delta_link != (
                origin + "/opaque/checkpoint?$deltatoken=opaque-terminal"
            ):
                pytest.fail("Opaque terminal Contacts cursor was rebuilt or changed")
            gone = session.get(
                ContactPresence,
                {
                    "source_id": "contacts-fixture",
                    "scope_key": f"folder:{DELTA_FOLDER}",
                    "contact_id": "delta-gone",
                },
            )
            if gone is None or gone.is_present or gone.removed_reason != "deleted":
                pytest.fail("Contacts delta tombstone was not applied")
        second = _run(
            tmp_path,
            origin,
            "crawl",
            "microsoft_contacts_delta",
            "-a",
            f"folder_id={DELTA_FOLDER}",
        )
        if second.returncode:
            pytest.fail(second.stderr)
        with catalog.Session() as session:
            checkpoint = session.get(
                ContactDeltaCheckpoint,
                {"source_id": "contacts-fixture", "folder_id": DELTA_FOLDER},
            )
            row = session.scalars(
                select(ContactRecord).filter_by(
                    source_id="contacts-fixture",
                    scope_key=f"folder:{DELTA_FOLDER}",
                    contact_id="delta-one",
                )
            ).one()
            if checkpoint is None or checkpoint.revision != 2:
                pytest.fail("Resumed custom-folder delta did not advance one revision")
            if row.company_name != "second" or row.display_name != "":
                pytest.fail("Sparse resumed delta did not merge provider state")
    finally:
        catalog.close()
    if requests.count("/opaque/checkpoint?$deltatoken=opaque-terminal") != 1:
        pytest.fail("Committed deltaLink was not reused verbatim on the next round")


def test_failed_delta_page_keeps_committed_cursor_and_current_state(
    tmp_path, contacts_server
):
    origin, state, _requests = contacts_server
    first = _run(
        tmp_path,
        origin,
        "crawl",
        "microsoft_contacts_delta",
        "-a",
        f"folder_id={DELTA_FOLDER}",
    )
    if first.returncode:
        pytest.fail(first.stderr)
    state["mode"] = "delta_request_failure"
    failed = _run(
        tmp_path,
        origin,
        "crawl",
        "microsoft_contacts_delta",
        "-a",
        f"folder_id={DELTA_FOLDER}",
    )
    if "contacts_delta_incomplete" not in failed.stderr:
        pytest.fail("Failed delta page did not trip the fail-closed delta gate")
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        with catalog.Session() as session:
            checkpoint = session.get(
                ContactDeltaCheckpoint,
                {"source_id": "contacts-fixture", "folder_id": DELTA_FOLDER},
            )
            row = session.scalars(
                select(ContactRecord).filter_by(
                    source_id="contacts-fixture",
                    scope_key=f"folder:{DELTA_FOLDER}",
                    contact_id="delta-one",
                )
            ).one()
            if checkpoint is None or checkpoint.revision != 1:
                pytest.fail("Failed delta page advanced the committed cursor")
            if row.company_name != "first":
                pytest.fail("Failed delta page changed current contact state")
    finally:
        catalog.close()


def test_contacts_rejects_jobdir_before_crawl(tmp_path, contacts_server):
    origin, _state, _requests = contacts_server
    result = _run(
        tmp_path,
        origin,
        "microsoft",
        "contacts",
        "sync",
        "-s",
        f"JOBDIR={tmp_path / 'job'}",
    )
    if result.returncode == 0:
        pytest.fail("Contacts must reject unsupported JOBDIR semantics")
