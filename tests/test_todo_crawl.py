"""Run the To Do command through real Scrapy and a local Graph fixture."""

import json
import os
import subprocess
import sys
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Any
from urllib.parse import quote

import pytest
from sqlalchemy import select

from message_ingest.catalog import Catalog
from message_ingest.catalog.models.acquisition import (
    RawHttpEvidence,
    SourceTargetBinding,
)
from message_ingest.catalog.models.microsoft.todo import (
    TodoChecklistItemPresence,
    TodoChecklistItemRecord,
    TodoLinkedResourcePresence,
    TodoLinkedResourceRecord,
    TodoSnapshotCandidate,
    TodoSnapshotState,
    TodoTaskListPresence,
    TodoTaskListRecord,
    TodoTaskPresence,
    TodoTaskRecord,
    TodoTraversalCompletion,
)
from tests.handoff_qualification.release_assertions import (
    assert_release_contract,
)

ROOT = Path(__file__).parents[1]
LIST_ID = "private-list/+%2F"
TASK_ID = "private-task/+%2f"
LISTS = "/v1.0/me/todo/lists"
TASKS = f"{LISTS}/{quote(LIST_ID, safe='')}/tasks"
TASK = f"{TASKS}/{quote(TASK_ID, safe='')}"
CHECKS = TASK + "/checklistItems"
LINKS = TASK + "/linkedResources"
CURSOR = "?$skiptoken=opaque-secret%2f&x=+&x=%20"


@pytest.fixture
def graph_server():
    requests = []
    state = {"mode": "success", "retried": False}
    pages: dict[str, dict[str, Any]] = {
        LISTS + "?%24top=2": {
            "value": [
                {
                    "id": LIST_ID,
                    "displayName": "",
                    "isOwner": False,
                    "isShared": False,
                    "wellknownListName": "defaultList",
                }
            ],
            "@odata.nextLink": LISTS + CURSOR,
        },
        LISTS + CURSOR: {
            "value": [{"id": "flagged", "wellknownListName": "flaggedEmails"}]
        },
        TASKS + "?%24top=2": {
            "value": [
                {
                    "id": TASK_ID,
                    "title": "provider-private-title",
                    "status": "notStarted",
                    "categories": [],
                    "isReminderOn": False,
                    "body": {"contentType": "html", "content": ""},
                    "dueDateTime": {
                        "dateTime": "2026-10-01T00:00:00",
                        "timeZone": "UTC",
                    },
                    "linkedResources": [{"id": "embedded-only"}],
                }
            ],
            "@odata.nextLink": TASKS + CURSOR,
        },
        TASKS + CURSOR: {"value": [{"id": "second", "title": ""}]},
        LISTS + "/flagged/tasks?%24top=2": {"value": []},
        CHECKS: {
            "value": [{"id": "check-one", "displayName": "", "isChecked": False}],
            "@odata.nextLink": CHECKS + CURSOR,
        },
        CHECKS + CURSOR: {"value": [{"id": "check-two", "isChecked": True}]},
        LINKS: {
            "value": [{"id": "link-one", "displayName": "", "externalId": "external"}],
            "@odata.nextLink": LINKS + CURSOR,
        },
        LINKS + CURSOR: {
            "value": [{"id": "link-two", "webUrl": "https://example.test/evidence"}]
        },
        TASKS + "/second/checklistItems": {"value": []},
        TASKS + "/second/linkedResources": {"value": []},
    }

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def do_GET(self):
            requests.append(self.path)
            status = 200
            payload = pages.get(self.path)
            if state["mode"] == "empty":
                payload = {"value": []}
            elif self.path == LINKS and state["mode"] == "failure":
                status = 403
                payload = {
                    "error": {
                        "code": "ErrorAccessDenied",
                        "message": "provider-private-title",
                    }
                }
            elif self.path == LINKS and state["mode"] == "malformed":
                payload = {"value": [{"displayName": "no identity"}]}
            elif self.path == LINKS and not state["retried"]:
                state["retried"] = True
                status = 503
                payload = {"error": {"code": "ServiceUnavailable", "message": "retry"}}
            if payload is None:
                status = 404
                payload = {"error": {"code": "FixtureRouteMissing"}}
            if isinstance(next_link := payload.get("@odata.nextLink"), str):
                payload = {
                    **payload,
                    "@odata.nextLink": origin + next_link,
                }
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            if status == 503:
                self.send_header("Retry-After", "0")
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    origin = f"http://127.0.0.1:{server.server_port}"
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield origin, state, requests, pages
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _crawl(tmp_path, origin, *, action="discover", extra_settings=None, timeout=30):
    """Run a fixture crawl with a finite, caller-selected workload budget."""
    settings = {
        "MS_GRAPH_SERVICE_ROOT": origin + "/v1.0",
        "MS_GRAPH_AUTH_METHOD": "none",
        "MSGLOOM_SOURCE_IDENTITY_REQUIRED": "False",
        "MSGLOOM_TODO_SOURCE_ID": "todo-fixture",
        "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
        "MSGLOOM_RAW_EVIDENCE_DIR": str(tmp_path / "raw"),
        "MSGLOOM_CATALOG_ENABLED": "True",
        "MSGLOOM_RAW_EVIDENCE_ENABLED": "True",
        "HTTPCACHE_ENABLED": "False",
        "AUTOTHROTTLE_ENABLED": "False",
        "LOG_LEVEL": "DEBUG",
    }
    settings.update(extra_settings or {})
    args = [
        sys.executable,
        "-m",
        "scrapy",
        "microsoft",
        "todo",
        action,
        "--page-size",
        "2",
    ]
    for key, value in settings.items():
        args.extend(["-s", f"{key}={value}"])
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "tests") + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        args,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        env=env,
    )


def _private_logs(stderr):
    for private in (
        LIST_ID,
        TASK_ID,
        quote(LIST_ID, safe=""),
        quote(TASK_ID, safe=""),
        "provider-private-title",
        "opaque-secret",
    ):
        if private in stderr:
            pytest.fail(f"Shared privacy components leaked provider data: {private}")


def test_real_todo_command_crawls_all_surfaces_and_preserves_evidence(
    tmp_path, graph_server
):
    origin, state, requests, pages = graph_server
    result = _crawl(tmp_path, origin)
    if result.returncode or "ERROR" in result.stderr:
        pytest.fail(result.stderr)
    _private_logs(result.stderr)
    if Counter(requests) != Counter(
        {path: 2 if path == LINKS else 1 for path in pages}
    ):
        pytest.fail(f"Traversal or opaque request bytes changed: {requests!r}")
    for component in (
        "MicrosoftGraphErrorMiddleware",
        "PrivacySafeRetryMiddleware",
        "MicrosoftGraphDiagnosticsMiddleware",
        "MicrosoftGraphLogPrivacyExtension",
        "RepresentationAwareRequestFingerprinter",
    ):
        if component not in result.stderr:
            pytest.fail(f"Shared Graph component was not enabled: {component}")
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        with catalog.Session() as session:
            records = []
            for model in (
                TodoTaskListRecord,
                TodoTaskRecord,
                TodoChecklistItemRecord,
                TodoLinkedResourceRecord,
            ):
                rows = session.scalars(select(model)).all()
                if len(rows) != 2:
                    pytest.fail(f"Missing paginated {model.__name__} state")
                records.extend(rows)
            evidence = session.scalars(select(RawHttpEvidence)).all()
            if len(evidence) != len(pages):
                pytest.fail("Expected one raw capture per callback-visible response")
            evidence_by_id = {row.evidence_id: row for row in evidence}
            for row in records:
                capture = evidence_by_id.get(row.latest_evidence_id)
                if capture is None or row.latest_observed_at != capture.observed_at:
                    pytest.fail(
                        "Semantic state must reference persisted evidence and time"
                    )
                if (
                    row.source_id != "todo-fixture"
                    or capture.source_id != row.source_id
                ):
                    pytest.fail("To Do source identity did not reach storage")
            links = session.scalars(select(TodoLinkedResourceRecord)).all()
            if {row.linked_resource_id for row in links} != {"link-one", "link-two"}:
                pytest.fail("Embedded relation replaced explicit relation fetch")
            if (
                next(
                    row for row in links if row.linked_resource_id == "link-one"
                ).web_url
                is not None
            ):
                pytest.fail("A missing provider web URL must remain valid")
            if session.scalars(select(SourceTargetBinding)).first() is not None:
                pytest.fail("To Do must not create Outlook source-target bindings")
        context_facts = (("context", None),)
        primary_facts = (("primary", None),)
        checklist_facts = (("component", "checklist_item"),)
        linked_facts = (("component", "linked_resource"),)
        list_identity = f'["{LIST_ID}"]'
        flagged_identity = '["flagged"]'
        task_identity = f'["{LIST_ID}","{TASK_ID}"]'
        second_identity = f'["{LIST_ID}","second"]'
        check_one_identity = f'["{LIST_ID}","{TASK_ID}","check-one"]'
        check_two_identity = f'["{LIST_ID}","{TASK_ID}","check-two"]'
        link_one_identity = f'["{LIST_ID}","{TASK_ID}","link-one"]'
        link_two_identity = f'["{LIST_ID}","{TASK_ID}","link-two"]'
        check_kind = "todo_checklist_item"
        link_kind = "todo_linked_resource"
        assert_release_contract(
            tmp_path / "catalog.sqlite3",
            source_id="todo-fixture",
            stream="todo",
            expected_groups={
                ("todo_discovery", "source"): ("resource_set", False, 8),
            },
            expected_entries={
                ("todo_discovery", "source"): (
                    ("context", "todo_task_list", list_identity, context_facts),
                    ("context", "todo_task_list", flagged_identity, context_facts),
                    ("resource", "todo_task", task_identity, primary_facts),
                    ("resource", "todo_task", second_identity, primary_facts),
                    ("component", check_kind, check_one_identity, checklist_facts),
                    ("component", check_kind, check_two_identity, checklist_facts),
                    ("component", link_kind, link_one_identity, linked_facts),
                    ("component", link_kind, link_two_identity, linked_facts),
                ),
            },
            expected_fact_spiders={"microsoft_todo_discover"},
        )
        # An empty later inventory must not remove any previously observed row.
        state["mode"] = "empty"
        second = _crawl(tmp_path, origin)
        if second.returncode:
            pytest.fail(second.stderr)
        with catalog.Session() as session:
            if len(session.scalars(select(TodoTaskRecord)).all()) != 2:
                pytest.fail("Discovery inferred task removal from absence")
    finally:
        catalog.close()


@pytest.mark.parametrize("mode", ["failure", "malformed"])
def test_real_todo_failure_retains_evidence_and_fails_command(
    tmp_path, graph_server, mode
):
    origin, state, _requests, _pages = graph_server
    state["mode"] = mode
    result = _crawl(tmp_path, origin)
    if result.returncode != 1:
        pytest.fail(f"Request/callback failure must fail the command: {result.stderr}")
    _private_logs(result.stderr)
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        with catalog.Session() as session:
            captures = session.scalars(
                select(RawHttpEvidence).filter_by(purpose="todo-linked-resources-page")
            ).all()
            if not any(row.request_url == origin + LINKS for row in captures):
                pytest.fail("Failed relation response lost its raw evidence")
            if session.scalars(select(TodoLinkedResourceRecord)).first() is not None:
                pytest.fail("Failed or malformed response produced relation state")
    finally:
        catalog.close()


def _presence_state(session):
    """Return current presence without exposing provider identities in failures."""
    state = session.get(TodoSnapshotState, "todo-fixture")
    rows = []
    for model in (
        TodoTaskListPresence,
        TodoTaskPresence,
        TodoChecklistItemPresence,
        TodoLinkedResourcePresence,
    ):
        rows.extend(
            (row.is_present, row.latest_run_id, row.latest_observed_at)
            for row in session.scalars(select(model)).all()
        )
    return None if state is None else (state.revision, state.run_id), sorted(rows)


def test_real_todo_sync_promotes_only_after_full_multipage_traversal(
    tmp_path, graph_server
):
    origin, _state, requests, pages = graph_server
    result = _crawl(tmp_path, origin, action="sync")
    if result.returncode:
        pytest.fail(result.stderr)
    _private_logs(result.stderr)
    if Counter(requests) != Counter(
        {path: 2 if path == LINKS else 1 for path in pages}
    ):
        pytest.fail("Authoritative sync did not traverse every synthetic page")
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        with catalog.Session() as session:
            state = session.get(TodoSnapshotState, "todo-fixture")
            if state is None or state.revision != 1:
                pytest.fail("Clean full traversal did not promote revision one")
            candidates = session.scalars(select(TodoSnapshotCandidate)).all()
            if len(candidates) != 1 or candidates[0].committed_at is None:
                pytest.fail("Terminal snapshot candidate was not durably committed")
            completions = session.scalars(select(TodoTraversalCompletion)).all()
            if len(completions) != 7:
                pytest.fail("Durable traversal accounting is incomplete")
            for model in (
                TodoTaskListPresence,
                TodoTaskPresence,
                TodoChecklistItemPresence,
                TodoLinkedResourcePresence,
            ):
                rows = session.scalars(select(model)).all()
                if len(rows) != 2 or any(not row.is_present for row in rows):
                    pytest.fail("Full traversal did not promote current presence")
    finally:
        catalog.close()


@pytest.mark.parametrize("mode", ["failure", "malformed"])
def test_real_todo_sync_failure_keeps_promoted_presence(tmp_path, graph_server, mode):
    origin, state, _requests, _pages = graph_server
    first = _crawl(tmp_path, origin, action="sync")
    if first.returncode:
        pytest.fail(first.stderr)
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        with catalog.Session() as session:
            before = _presence_state(session)
        state["mode"] = mode
        failed = _crawl(tmp_path, origin, action="sync")
        if failed.returncode != 1:
            pytest.fail("Incomplete or failed authoritative sync must fail the command")
        _private_logs(failed.stderr)
        with catalog.Session() as session:
            after = _presence_state(session)
        if after != before:
            pytest.fail("Failed authoritative sync changed promoted presence")
    finally:
        catalog.close()


def test_real_todo_sync_incomplete_paging_blocks_promotion(tmp_path, graph_server):
    origin, _state, _requests, _pages = graph_server
    first = _crawl(tmp_path, origin, action="sync")
    if first.returncode:
        pytest.fail(first.stderr)
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        with catalog.Session() as session:
            before = _presence_state(session)
        middlewares = {
            "todo_sync_failures.DropChecklistContinuationMiddleware": 700,
        }
        failed = _crawl(
            tmp_path,
            origin,
            action="sync",
            extra_settings={"SPIDER_MIDDLEWARES": json.dumps(middlewares)},
        )
        if failed.returncode != 1:
            pytest.fail("Missing continuation must block authoritative promotion")
        _private_logs(failed.stderr)
        with catalog.Session() as session:
            after = _presence_state(session)
        if after != before:
            pytest.fail("Incomplete paging changed promoted presence")
    finally:
        catalog.close()


@pytest.mark.parametrize(
    "failure_pipeline",
    [
        "todo_sync_failures.DropTodoTaskPipeline",
        "todo_sync_failures.FailTodoTaskPipeline",
    ],
)
def test_real_todo_sync_pipeline_failure_blocks_promotion(
    tmp_path, graph_server, failure_pipeline
):
    origin, _state, _requests, _pages = graph_server
    first = _crawl(tmp_path, origin, action="sync")
    if first.returncode:
        pytest.fail(first.stderr)
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        with catalog.Session() as session:
            before = _presence_state(session)
        pipelines = {
            "message_ingest.pipelines.evidence.RawEvidencePipeline": 200,
            "message_ingest.acquisition.evidence_link.EvidenceLinkPipeline": 250,
            "message_ingest.pipelines.microsoft.todo.TodoPipeline": 300,
            failure_pipeline: 350,
        }
        failed = _crawl(
            tmp_path,
            origin,
            action="sync",
            extra_settings={"ITEM_PIPELINES": json.dumps(pipelines)},
        )
        if failed.returncode != 1:
            pytest.fail("DropItem/item_error must block authoritative promotion")
        _private_logs(failed.stderr)
        with catalog.Session() as session:
            after = _presence_state(session)
        if after != before:
            pytest.fail("Pipeline failure changed promoted presence")
    finally:
        catalog.close()
