"""Qualify Task15 #12 with native Scrapy and loopback Graph responses.

Removing the rules workflow's Full completion gate must break the failed
cases: a staged Delta cursor and discovery facts are not release authority.
The HTTP hook reads committed state before replying to a required component.
It does not replace Scrapy callbacks, pipelines, signals, or promotion.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from message_ingest.acquisition.microsoft.outlook.email.profile import FULL_V1
from message_ingest.catalog import Catalog, DeltaCheckpoint
from tests.test_outlook_mail_rule_sync_crawl import (
    ROOT,
    RULE_DISCOVERY_ID,
    RULE_FULL_ID,
    RUN_COMMAND,
    rules_sync_graph_server,
)

__all__ = ["rules_sync_graph_server"]
SOURCE = "rules-sync-fixture"


def _snapshot(database_url: str) -> dict:
    """Read durable state without constructing a writer in the HTTP thread."""
    database = database_url.removeprefix("sqlite:///")
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True, timeout=5)
    connection.row_factory = sqlite3.Row
    try:
        # One read transaction prevents a mixed view of atomic publication.
        connection.execute("BEGIN")
        tables = {
            "cursors": "delta_checkpoints",
            "candidates": "delta_checkpoint_candidates",
            "groups": "acquisition_release_groups",
            "entries": "acquisition_release_entries",
            "facts": "acquisition_facts",
            "evidence": "raw_http_evidence",
            "surfaces": "message_surfaces",
        }
        return {
            key: [
                dict(row)
                for row in connection.execute(
                    f"SELECT * FROM {table} WHERE source_id = ?", (SOURCE,)
                )
            ]
            for key, table in tables.items()
        }
    finally:
        connection.close()


def _groups(state: dict) -> set[tuple[str, str]]:
    """Identify publication subjects, including zero-entry decisions."""
    return {
        (payload["subject_kind"], payload["subject_identity"])
        for row in state["groups"]
        if (payload := json.loads(row["payload"]))
    }


def _require_blocked(state: dict, old_cursor: str) -> None:
    """Require unchanged provider authority and no selected Full release."""
    cursors = {row["folder_id"]: row["delta_link"] for row in state["cursors"]}
    if cursors != {"folder-inbox": old_cursor}:
        pytest.fail(f"Incomplete Full advanced the provider cursor: {cursors}")
    # Folder authority completes independently before message discovery.
    if _groups(state) != {("folder_delta", SOURCE)}:
        pytest.fail(f"Incomplete Full published authority/profile: {_groups(state)}")
    group_ids = {row["release_group_id"] for row in state["groups"]}
    if not state["entries"] or any(
        row["release_group_id"] not in group_ids for row in state["entries"]
    ):
        pytest.fail("Independent folder entries were lost or orphaned")


def _run_sync(tmp_path: Path, root: str, database_url: str):
    """Run the actual multi-crawl command with bounded, local-only transport."""
    config = tmp_path / "msgloom.toml"
    config.write_text(
        "[acquisition.microsoft.outlook.mail]\n"
        'enabled = true\ndefault_profile = "discovery"\n'
        "[[acquisition.microsoft.outlook.mail.rules]]\n"
        'id = "body-full"\nsequence = 10\nprofile = "full"\n'
        "[acquisition.microsoft.outlook.mail.rules.conditions]\n"
        'body_contains = ["escalate"]\n',
        encoding="utf-8",
    )
    settings = {
        "MS_GRAPH_AUTH_METHOD": "none",
        "MSGLOOM_DATABASE_URL": database_url,
        "MSGLOOM_RAW_EVIDENCE_DIR": str(tmp_path / "rules-raw"),
        "MSGLOOM_SOURCE_ID": SOURCE,
        "MSGLOOM_SOURCE_IDENTITY_REQUIRED": "False",
        "MSGLOOM_CATALOG_ENABLED": "True",
        "MSGLOOM_RAW_EVIDENCE_ENABLED": "True",
        "MSGLOOM_DELTA_CHECKPOINT_ENABLED": "True",
        "HTTPCACHE_ENABLED": "False",
        "AUTOTHROTTLE_ENABLED": "False",
        "RETRY_ENABLED": "False",
        "MS_GRAPH_ERROR_MAX_RETRIES": "0",
    }
    args = [
        sys.executable,
        "-c",
        RUN_COMMAND,
        root,
        "--page-size",
        "25",
        "--no-reconcile",
        "--config",
        str(config),
        "-L",
        "INFO",
    ]
    for key, value in settings.items():
        args.extend(["-s", f"{key}={value}"])
    return subprocess.run(
        args, cwd=ROOT, capture_output=True, text=True, timeout=35, check=False
    )


@pytest.mark.parametrize("component", ["mime", "attachments"])
@pytest.mark.parametrize("status", [503, 200], ids=["failed", "persisted"])
def test_rules_authority_waits_for_required_full_component(
    tmp_path: Path, rules_sync_graph_server, component: str, status: int
) -> None:
    """Require no promotion before response or after nonterminal HTTP failure.

    The success control must publish only after native pipeline persistence.
    A 503 is deliberately not a supported terminal limitation such as 403.
    The discovery-only message and independent folder authority must survive.
    The fixture has no attachments; child attachment obligations are outside
    this regression's evidence claim.
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
    suffix = "$value" if component == "mime" else "attachments"
    target = f"/me/messages/{RULE_FULL_ID}/{suffix}"
    before = []

    def component_response(handler, path: str) -> bool:
        if path != target:
            return False
        before.append(_snapshot(database_url))
        if status == 200:
            return False
        body = b'{"error":{"code":"ErrorServiceUnavailable","message":"fixture"}}'
        handler.send_response(status)
        handler.send_header("Content-Type", "application/json")
        handler.send_header("Content-Length", str(len(body)))
        handler.end_headers()
        handler.wfile.write(body)
        return True

    policy["component_response"] = component_response
    result = _run_sync(tmp_path, root, database_url)
    if not any("$deltatoken=old" in request for request in seen):
        pytest.fail("Native Delta traversal did not resume the seeded cursor")
    if len(before) != 1:
        pytest.fail(f"Required component was not observed exactly once: {seen}")
    _require_blocked(before[0], old_cursor)
    if any(
        row["message_id"] == RULE_FULL_ID and row["surface"] == component
        for row in before[0]["surfaces"]
    ):
        pytest.fail("Pending response already had a persisted component surface")
    candidates = before[0]["candidates"]
    if len(candidates) != 1 or not candidates[0]["delta_link"].endswith("rules-done"):
        pytest.fail("Full gate was not exercised against a saved Delta candidate")
    if candidates[0]["committed_at"] is not None:
        pytest.fail("Pending Full committed the candidate early")

    expected_code = 0 if status == 200 else 1
    if result.returncode != expected_code:
        pytest.fail(f"Unexpected native workflow exit: {result.stderr}")
    after = _snapshot(database_url)
    saved_facts = {row["fact_id"]: row["payload"] for row in after["facts"]}
    if any(
        saved_facts.get(row["fact_id"]) != row["payload"] for row in before[0]["facts"]
    ):
        pytest.fail("Full completion rewrote or removed prior immutable facts")
    if not all(row in after["groups"] for row in before[0]["groups"]):
        pytest.fail("Full completion changed independent folder publication")
    if status == 503:
        _require_blocked(after, old_cursor)
        if any(row["committed_at"] is not None for row in after["candidates"]):
            pytest.fail("Failed Full marked a Delta candidate committed")
    else:
        cursors = {row["folder_id"]: row["delta_link"] for row in after["cursors"]}
        if cursors != {"folder-inbox": candidates[0]["delta_link"]}:
            pytest.fail("Persisted Full did not advance the staged cursor")
        if _groups(after) != {
            ("folder_delta", SOURCE),
            ("message_delta", SOURCE),
            ("message", RULE_FULL_ID),
        }:
            pytest.fail("Persisted Full did not release the expected subjects")

    evidence = {row["evidence_id"]: row for row in after["evidence"]}
    responses = [
        row
        for row in evidence.values()
        if urlsplit(row["request_url"]).path == f"/v1.0{target}"
    ]
    if len(responses) != 1 or responses[0]["response_status"] != status:
        pytest.fail("Required component outcome lacks saved HTTP evidence")
    for row in evidence.values():
        body = Path(row["response_body_path"]).read_bytes()
        if hashlib.sha256(body).hexdigest() != row["response_body_sha256"]:
            pytest.fail("Saved HTTP evidence does not match its digest")
    facts = [json.loads(row["payload"]) for row in after["facts"]]
    for surface in ("detail", "mime", "attachments"):
        rows = [
            row
            for row in after["surfaces"]
            if row["message_id"] == RULE_FULL_ID and row["surface"] == surface
        ]
        if status == 503 and surface == component:
            if rows:
                pytest.fail("503 incorrectly became a terminal Full surface")
            continue
        if len(rows) != 1 or rows[0]["status"] != "acquired":
            pytest.fail(f"Successful Full component was not persisted: {surface}")
        row = rows[0]
        if row["profile_version"] != FULL_V1:
            pytest.fail("Full component lost its profile version")
        bound = [
            fact
            for fact in facts
            if fact["resource_identity"] == RULE_FULL_ID
            and fact["component_kind"] == surface
            and fact["evidence_id"] == row["evidence_id"]
        ]
        if len(bound) != 1 or bound[0]["run_id"] != responses[0]["run_id"]:
            pytest.fail("Full component lacks exact current-run fact provenance")
        if evidence[row["evidence_id"]]["run_id"] != bound[0]["run_id"]:
            pytest.fail("Full component fact is not backed by current-run evidence")
    discovery = [
        row for row in after["surfaces"] if row["message_id"] == RULE_DISCOVERY_ID
    ]
    if status == 503:
        # The entire message Delta remains provisional when any required
        # selected Full component fails. Neither the selected nor unselected
        # discovery becomes an accepted mutable surface yet.
        if discovery:
            pytest.fail("Failed Full prematurely materialized Delta discovery")
        if not any(
            fact["resource_identity"] == RULE_DISCOVERY_ID
            and fact["component_kind"] == "discovery"
            and fact["evidence_id"] in evidence
            for fact in facts
        ):
            pytest.fail("Failed Full discarded original provisional evidence")
    else:
        if len(discovery) != 1 or discovery[0]["surface"] != "discovery":
            pytest.fail("Unselected message acquired Full obligations")
        if discovery[0]["status"] != "acquired" or discovery[0]["profile_version"]:
            pytest.fail("Unselected discovery evidence was lost")
        if not any(
            fact["resource_identity"] == RULE_DISCOVERY_ID
            and fact["component_kind"] == "discovery"
            and fact["evidence_id"] == discovery[0]["evidence_id"]
            for fact in facts
        ):
            pytest.fail("Unselected discovery lost its immutable provenance")
    if any(
        urlsplit(request).path.startswith(f"/v1.0/me/messages/{RULE_DISCOVERY_ID}/")
        for request in seen
    ):
        pytest.fail("Unselected message entered Full traversal")
