"""Qualify Task15 #12's required fileAttachment child over native HTTP.

Ignoring nonempty inventory obligations or treating raw HTTP 503 as terminal
must fail these checks. The HTTP hook reads committed state before replying;
Scrapy owns traversal, evidence, pipelines, completion, and publication.
"""

from __future__ import annotations

import hashlib
import json
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from message_ingest.acquisition.microsoft.outlook.email.profile import FULL_V1
from message_ingest.catalog import Catalog, DeltaCheckpoint
from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore
from tests.test_outlook_mail_rule_authority_gate_crawl import (
    SOURCE,
    _groups,
    _require_blocked,
    _run_sync,
    _snapshot,
)
from tests.test_outlook_mail_rule_sync_crawl import (
    RULE_DISCOVERY_ID,
    RULE_FULL_ID,
    rules_sync_graph_server,
)

__all__ = ["rules_sync_graph_server"]
ATTACHMENT_ID = "required-file"
RAW_SURFACE = f"attachment_raw:{ATTACHMENT_ID}"
RAW_BODY = b"Task15 current-run attachment\x00\xff\r\n"
ERROR_BODY = b'{"error":{"code":"ErrorServiceUnavailable","message":"fixture"}}'
INVENTORY_BODY = json.dumps(
    {
        "value": [
            {
                "@odata.type": "#microsoft.graph.fileAttachment",
                "id": ATTACHMENT_ID,
                "name": "required.bin",
                "contentType": "application/octet-stream",
                "size": len(RAW_BODY),
                "isInline": False,
            }
        ]
    }
).encode()


def _reply(
    handler: BaseHTTPRequestHandler, status: int, body: bytes, content_type: str
) -> None:
    """Send an exact local Graph response without touching crawl state."""
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _response(state: dict, path: str, status: int, body: bytes) -> dict:
    """Require one persisted HTTP outcome with exact bytes and digest."""
    rows = [
        row
        for row in state["evidence"]
        if urlsplit(row["request_url"]).path == f"/v1.0{path}"
    ]
    if len(rows) != 1 or rows[0]["response_status"] != status:
        pytest.fail(f"Missing exact HTTP outcome for {path}: {rows}")
    row = rows[0]
    if (
        Path(row["response_body_path"]).read_bytes() != body
        or row["response_body_sha256"] != hashlib.sha256(body).hexdigest()
    ):
        pytest.fail(f"Saved HTTP bytes or digest differ for {path}")
    return row


def _surface_fact(state: dict, surface: str, response: dict) -> dict:
    """Bind a Full surface to its exact current-run immutable fact."""
    rows = [
        row
        for row in state["surfaces"]
        if row["message_id"] == RULE_FULL_ID and row["surface"] == surface
    ]
    if len(rows) != 1 or (
        rows[0]["status"],
        rows[0]["profile_version"],
        rows[0]["evidence_id"],
    ) != ("acquired", FULL_V1, response["evidence_id"]):
        pytest.fail(f"Missing exact acquired Full surface: {surface}")
    facts = [
        {**fact, "fact_id": row["fact_id"]}
        for row in state["facts"]
        if (fact := json.loads(row["payload"]))["resource_identity"] == RULE_FULL_ID
        and fact["component_kind"] == surface
        and fact["evidence_id"] == response["evidence_id"]
    ]
    if len(facts) != 1 or facts[0]["run_id"] != response["run_id"]:
        pytest.fail(f"Missing current-run Full provenance: {surface}")
    return facts[0]


def _require_discovery(before: dict, after: dict, seen: list[str], status: int):
    """Preserve original Delta facts and leave unselected discovery alone."""
    originals = {
        row["fact_id"]: row["payload"]
        for row in before["facts"]
        if (fact := json.loads(row["payload"]))["resource_identity"]
        in {RULE_FULL_ID, RULE_DISCOVERY_ID}
        and fact["component_kind"] == "discovery"
    }
    if len(originals) != 2:
        pytest.fail("Pre-child snapshot lacks both original discovery facts")
    saved = {row["fact_id"]: row["payload"] for row in after["facts"]}
    if any(saved.get(key) != payload for key, payload in originals.items()):
        pytest.fail("Child completion changed original immutable discovery")
    discovery = [
        row for row in after["surfaces"] if row["message_id"] == RULE_DISCOVERY_ID
    ]
    if status == 503:
        if discovery:
            pytest.fail("Failed child prematurely materialized Delta discovery")
    elif len(discovery) != 1 or (
        discovery[0]["surface"],
        discovery[0]["status"],
        discovery[0]["profile_version"],
    ) != ("discovery", "acquired", None):
        pytest.fail("Unselected discovery was lost or acquired Full obligations")
    else:
        original = next(
            json.loads(payload)
            for payload in originals.values()
            if json.loads(payload)["resource_identity"] == RULE_DISCOVERY_ID
        )
        if discovery[0]["evidence_id"] != original["evidence_id"]:
            pytest.fail("Unselected discovery lost its original evidence")
        delta_groups = {
            row["release_group_id"]
            for row in after["groups"]
            if json.loads(row["payload"])["subject_kind"] == "message_delta"
        }
        entries = [
            json.loads(row["payload"])
            for row in after["entries"]
            if row["release_group_id"] in delta_groups
        ]
        if len(entries) != 2 or {entry["resource_identity"] for entry in entries} != {
            RULE_FULL_ID,
            RULE_DISCOVERY_ID,
        }:
            pytest.fail("Winning Delta lost its two original discovery entries")
        for entry in entries:
            expected = next(
                key
                for key, payload in originals.items()
                if json.loads(payload)["resource_identity"]
                == entry["resource_identity"]
            )
            if [expected, "component"] not in entry["facts"]:
                pytest.fail("Winning Delta replaced its original discovery fact")
    requests = [
        urlsplit(request)
        for request in seen
        if urlsplit(request).path.startswith(f"/v1.0/me/messages/{RULE_DISCOVERY_ID}")
    ]
    if len(requests) != 1 or set(
        parse_qs(requests[0].query).get("$select", [""])[0].split(",")
    ) != {"id", "changeKey", "body"}:
        pytest.fail("Unselected message traversal exceeded its rule probe")


def _require_winner(state: dict, candidate: dict, component_facts: list[dict]):
    """Require committed authority and publication of the exact child facts."""
    if (
        _groups(state)
        != {
            ("folder_delta", SOURCE),
            ("message_delta", SOURCE),
            ("message", RULE_FULL_ID),
        }
        or len(state["groups"]) != 3
    ):
        pytest.fail("Successful child did not publish exactly the expected subjects")
    if len(state["cursors"]) != 1 or (
        state["cursors"][0]["delta_link"],
        state["cursors"][0]["run_id"],
    ) != (candidate["delta_link"], candidate["run_id"]):
        pytest.fail("Successful child did not commit the winning Delta cursor")
    if len(state["candidates"]) != 1 or not state["candidates"][0]["committed_at"]:
        pytest.fail("Successful child did not mark its candidate committed")
    for row in state["groups"]:
        group = json.loads(row["payload"])
        if group["subject_kind"] == "folder_delta":
            continue
        if group["coverage_kind"] != "complete":
            pytest.fail("Successful child published incomplete coverage")
        if group["subject_kind"] == "message_delta":
            if (
                group["release_kind"] != "authority_scope"
                or group["authority_revision"] != candidate["run_id"]
                or group["owner_run_id"] != candidate["run_id"]
            ):
                pytest.fail("Message Delta release lost winning authority")
            continue
        if (
            group["release_kind"] != "resource_profile"
            or group["authority_revision"] is not None
            or group["owner_run_id"] != component_facts[0]["run_id"]
            or group["profile"] != FULL_V1
        ):
            pytest.fail("Full release lost current-run profile ownership")
        entries = [
            json.loads(entry["payload"])
            for entry in state["entries"]
            if entry["release_group_id"] == row["release_group_id"]
        ]
        if len(entries) != 1 or entries[0]["resource_identity"] != RULE_FULL_ID:
            pytest.fail("Full publication lost its exact message entry")
        members = entries[0]["facts"]
        if any(
            [fact["fact_id"], "component"] not in members for fact in component_facts
        ):
            pytest.fail("Full publication omitted exact inventory or child facts")


@pytest.mark.parametrize("status", [503, 200], ids=["failed", "persisted"])
def test_rules_authority_waits_for_required_attachment_raw(
    tmp_path: Path, rules_sync_graph_server, status: int
) -> None:
    """Gate authority on required child bytes from a nonempty file inventory.

    A 503 remains incomplete; a 200 must persist the exact current-run bytes
    and publish their facts. Independent folder releases and original Delta
    discovery survive both outcomes. No live Graph or pipeline mocks are used.
    """
    root, database_url, seen, policy = rules_sync_graph_server
    old_cursor = f"{root}/me/mailFolders/folder-inbox/messages/delta?$deltatoken=old"
    catalog = Catalog(database_url)
    try:
        with catalog.writer_session() as session:
            session.add(
                DeltaCheckpoint(
                    source_id=SOURCE,
                    folder_id="folder-inbox",
                    delta_link=old_cursor,
                    committed_at="2026-10-01T00:00:00Z",
                    run_id="prior-run",
                )
            )
    finally:
        catalog.close()
    inventory_path = f"/me/messages/{RULE_FULL_ID}/attachments"
    raw_path = f"{inventory_path}/{ATTACHMENT_ID}/$value"
    before: list[dict] = []

    def component_response(handler: BaseHTTPRequestHandler, path: str) -> bool:
        if path == inventory_path:
            _reply(handler, 200, INVENTORY_BODY, "application/json")
            return True
        if path != raw_path:
            return False
        before.append(_snapshot(database_url))
        _reply(
            handler,
            status,
            RAW_BODY if status == 200 else ERROR_BODY,
            "application/octet-stream" if status == 200 else "application/json",
        )
        return True

    policy["has_attachments"] = True
    policy["component_response"] = component_response
    result = _run_sync(tmp_path, root, database_url)
    if len(before) != 1:
        pytest.fail(f"Required raw child was not requested exactly once: {seen}")
    pending = before[0]
    _require_blocked(pending, old_cursor)
    if any(row["surface"] == RAW_SURFACE for row in pending["surfaces"]):
        pytest.fail("Child surface existed before its HTTP response")
    if any(
        urlsplit(row["request_url"]).path == f"/v1.0{raw_path}"
        for row in pending["evidence"]
    ):
        pytest.fail("Child evidence existed before its HTTP response")
    candidates = pending["candidates"]
    if (
        len(candidates) != 1
        or not candidates[0]["delta_link"].endswith("rules-done")
        or candidates[0]["committed_at"] is not None
    ):
        pytest.fail("Child gate was not exercised against an uncommitted candidate")
    if not any("$deltatoken=old" in request for request in seen):
        pytest.fail("Native Delta did not resume the seeded cursor")
    if result.returncode != (0 if status == 200 else 1):
        pytest.fail(f"Unexpected native workflow exit: {result.stderr}")
    after = _snapshot(database_url)
    if not all(row in after["groups"] for row in pending["groups"]) or not all(
        row in after["entries"] for row in pending["entries"]
    ):
        pytest.fail("Child completion changed independent folder publication")
    _require_discovery(pending, after, seen, status)
    inventory = _response(after, inventory_path, 200, INVENTORY_BODY)
    child = _response(
        after, raw_path, status, RAW_BODY if status == 200 else ERROR_BODY
    )
    if inventory["run_id"] != child["run_id"] or child["run_id"] == "prior-run":
        pytest.fail("Inventory and child evidence do not belong to the new Full run")
    # Both other base obligations must succeed even in the failed-child case.
    # This distinguishes a child gate from an unrelated MIME/detail failure.
    for surface, path in (
        ("detail", f"/me/messages/{RULE_FULL_ID}"),
        ("mime", f"/me/messages/{RULE_FULL_ID}/$value"),
    ):
        responses = [
            row
            for row in after["evidence"]
            if urlsplit(row["request_url"]).path == f"/v1.0{path}"
            and row["run_id"] == child["run_id"]
            and row["response_status"] == 200
        ]
        if len(responses) != 1:
            pytest.fail(f"Child was not the only outstanding obligation: {surface}")
        _surface_fact(after, surface, responses[0])
    inventory_fact = _surface_fact(after, "attachments", inventory)
    metadata = [
        {**fact, "fact_id": row["fact_id"]}
        for row in after["facts"]
        if (fact := json.loads(row["payload"]))["resource_identity"] == ATTACHMENT_ID
        and fact["component_kind"] == "attachment_metadata"
        and fact["evidence_id"] == inventory["evidence_id"]
    ]
    if len(metadata) != 1 or metadata[0]["run_id"] != child["run_id"]:
        pytest.fail("Nonempty inventory lost its exact current-run metadata fact")
    catalog = Catalog(database_url)
    try:
        attachments = OutlookMailStore(catalog, source_id=SOURCE).get_attachments(
            message_id=RULE_FULL_ID
        )
    finally:
        catalog.close()
    if len(attachments) != 1 or (
        attachments[0]["attachment_id"],
        attachments[0]["attachment_type"],
        attachments[0]["latest_evidence_id"],
        attachments[0]["name"],
        attachments[0]["content_type"],
        attachments[0]["size"],
        attachments[0]["is_inline"],
    ) != (
        ATTACHMENT_ID,
        "#microsoft.graph.fileAttachment",
        inventory["evidence_id"],
        "required.bin",
        "application/octet-stream",
        len(RAW_BODY),
        False,
    ):
        pytest.fail("Nonempty fileAttachment inventory was not persisted")
    if status == 503:
        _require_blocked(after, old_cursor)
        if any(row["committed_at"] is not None for row in after["candidates"]):
            pytest.fail("Failed child committed a Delta candidate")
        if any(row["surface"] == RAW_SURFACE for row in after["surfaces"]):
            pytest.fail("Raw 503 incorrectly became a terminal Full surface")
        return
    child_fact = _surface_fact(after, RAW_SURFACE, child)
    _require_winner(after, candidates[0], [inventory_fact, metadata[0], child_fact])
