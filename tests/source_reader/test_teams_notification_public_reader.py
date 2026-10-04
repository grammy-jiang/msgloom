"""Qualify saved Teams history from native notification intake and readback."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from scrapy.utils.project import get_project_settings

from message_ingest.catalog.models.acquisition import RawHttpEvidence, SourceBinding
from msgloom.preparation.records import PreparedSourceType
from msgloom.sources import SavedSourceReader, SavedSourceReaderConfig
from msgloom.sources.models import SourceEvidenceError
from tests.teams_notification_support import (
    SOURCE,
    GraphFixture,
    change_event,
    chat_subscription,
    crawl_notification,
    encode_envelope,
    json_reply,
    lifecycle_event,
    open_catalog,
)

pytest_plugins = ("tests.teams_support",)


@pytest.mark.parametrize("gap_origin", ["webhook", "local"])
def test_native_notification_history_survives_public_selection_replay(
    tmp_path: Path, graph_fixture: GraphFixture, gap_origin: str
) -> None:
    """Verify original bytes, immutable deletion, additive readback and gaps."""
    now = datetime.now(UTC)
    native_settings: dict[str, object] = {
        "SPIDER_MODULES": ",".join(get_project_settings().getlist("SPIDER_MODULES"))
    }
    subscription = chat_subscription()
    subscription.update(
        valid_from=(now - timedelta(hours=1)).isoformat(),
        valid_until=(now + timedelta(hours=1)).isoformat(),
    )
    target = "/v1.0/chats/chat-a/messages/message-a"
    message = {
        "id": "message-a",
        "etag": "observed-version",
        "body": {"contentType": "text", "content": "retained body"},
    }
    graph_fixture.add(target, json_reply(message))
    initial = crawl_notification(
        tmp_path,
        graph_fixture,
        body=encode_envelope([change_event()]),
        subscriptions=[subscription],
        evidence_id="1" * 32,
        captured_at=now.isoformat(),
        extra_settings=native_settings,
    )
    if initial.returncode:
        pytest.fail(initial.stderr[-4000:])
    catalog = open_catalog(tmp_path)
    try:
        # The local transport fixture disables authentication. Supply an explicit
        # synthetic account binding; this does not qualify company identity.
        with catalog.Session.begin() as session:
            session.add(
                SourceBinding(
                    source_id=SOURCE,
                    provider="microsoft",
                    key_scheme="teams-test",
                    account_key_sha256="a" * 64,
                    binding_method="test",
                    bound_at=now.isoformat(),
                )
            )
    finally:
        catalog.close()

    gap_time = (now + timedelta(seconds=10)).isoformat()
    entries = [change_event()]
    local_gap = None
    gap_evidence = "2" * 32
    if gap_origin == "webhook":
        entries.insert(0, lifecycle_event(lifecycle="subscriptionRemoved"))
    else:
        gap_evidence = "3" * 32
        local_gap = {
            "evidence_id": gap_evidence,
            "captured_at": gap_time,
            "subscription_id": "sub-chat",
            "gap_kind": "delivery-interruption",
        }
    reconciled = crawl_notification(
        tmp_path,
        graph_fixture,
        body=encode_envelope(entries),
        subscriptions=[subscription],
        evidence_id="2" * 32,
        captured_at=gap_time,
        local_gap=local_gap,
        extra_settings=native_settings,
    )
    if reconciled.returncode:
        pytest.fail(reconciled.stderr[-4000:])
    graph_fixture.add(target, json_reply({"error": {"code": "Denied"}}, status=403))
    deletion_bytes = encode_envelope([change_event(change_type="deleted")])
    deleted = crawl_notification(
        tmp_path,
        graph_fixture,
        body=deletion_bytes,
        subscriptions=[subscription],
        evidence_id="4" * 32,
        captured_at=(now + timedelta(seconds=20)).isoformat(),
        extra_settings=native_settings,
    )
    if deleted.returncode:
        pytest.fail(deleted.stderr[-4000:])
    catalog = open_catalog(tmp_path)
    try:
        with catalog.Session() as session:
            gap_row = session.get(RawHttpEvidence, gap_evidence)
            deletion_row = session.get(RawHttpEvidence, "4" * 32)
            if gap_row is None or deletion_row is None:
                pytest.fail("Native intake did not persist both evidence captures")
            gap_path = Path(gap_row.request_body_path)
            if Path(deletion_row.request_body_path).read_bytes() != deletion_bytes:
                pytest.fail("Native deletion evidence lost exact inbound bytes")
    finally:
        catalog.close()

    async def exercise() -> None:
        reader = SavedSourceReader(
            SavedSourceReaderConfig(
                catalog_path=tmp_path / "catalog.sqlite3",
                evidence_roots=(tmp_path / "raw",),
            )
        )
        try:
            versions = await reader.list_versions(
                PreparedSourceType.TEAMS_CHAT_MESSAGE, source_id=SOURCE, limit=10
            )
            if not versions:
                pytest.fail("Public reader cannot list native notification readbacks")
            selected = await reader.read_selection(versions[0])
            record = selected.record
            if record.body is None or record.body.content != "retained body":
                pytest.fail("Deletion or reconciliation replaced captured content")
            required = {"teams-explicit-deletion-observed", "teams-history-incomplete"}
            if not required <= {entry.code for entry in record.limitations}:
                pytest.fail("Public reader lost native deletion or gap uncertainty")
            facts = [
                json.loads(relation.target.version)
                for relation in record.relationships
                if relation.kind == "teams_coverage"
            ]
            if not any(
                fact.get("fact_kind") == "notification-readback"
                and fact.get("status") == "failed"
                and fact.get("details", {}).get("notification_evidence_id") == "4" * 32
                for fact in facts
            ):
                pytest.fail("Public history lost additive failed-readback association")
            encoded = await reader.encode_selection(selected)
            if await reader.decode_selection(encoded) != selected:
                pytest.fail(
                    "Public selection replay changed native notification history"
                )
            gap_path.write_bytes(b"tampered native gap evidence")
            with pytest.raises(SourceEvidenceError):
                await reader.read(versions[0])
        finally:
            await reader.close()

    asyncio.run(exercise())
