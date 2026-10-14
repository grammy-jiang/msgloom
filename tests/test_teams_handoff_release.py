"""Native Scrapy qualification for Teams acquisition-ledger publication."""

import json
from pathlib import Path

import pytest
from teams_support import GraphFixture, crawl, json_reply

from message_ingest.acquisition.handoff import AcquisitionStream
from message_ingest.catalog.store import Catalog
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore

pytest_plugins = ("teams_support",)

_SETTINGS = {"SPIDER_MODULES": "message_ingest.spiders.microsoft.teams"}


def _routes(fixture: GraphFixture, *, message_status: int = 200) -> None:
    fixture.add(
        "/v1.0/me/chats?%24top=50",
        json_reply({"value": [{"id": "chat-a", "chatType": "group"}]}),
    )
    fixture.add("/v1.0/chats/chat-a/members", json_reply({"value": []}))
    message = {
        "id": "message-a",
        "etag": "etag-a",
        "createdDateTime": "2026-10-08T00:00:00Z",
        "lastModifiedDateTime": "2026-10-08T00:00:00Z",
        "messageType": "message",
        "from": {"user": {"id": "user-a", "displayName": "Alice"}},
        "body": {"contentType": "html", "content": "hello"},
        "attachments": [],
    }
    fixture.add(
        "/v1.0/chats/chat-a/messages?%24top=50",
        json_reply({"value": [message]}, status=message_status),
    )
    fixture.add("/v1.0/chats/chat-a/pinnedMessages", json_reply({"value": []}))
    if message_status == 200:
        fixture.add(
            "/v1.0/chats/chat-a/messages/message-a/hostedContents",
            json_reply({"value": []}),
        )


def _entries(tmp_path: Path):
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        return AcquisitionHandoffStore(catalog).list_release_entries(
            "teams-fixture", AcquisitionStream.TEAMS_CHAT, limit=1000
        )
    finally:
        catalog.close()


def test_chat_discovery_publishes_exact_incremental_release(
    tmp_path: Path, graph_fixture: GraphFixture
) -> None:
    _routes(graph_fixture)
    result = crawl(
        tmp_path,
        graph_fixture,
        ["crawl", "microsoft_teams_chat_discover"],
        extra_settings=_SETTINGS,
    )
    if result.returncode:
        pytest.fail(result.stderr[-4000:])
    entries = _entries(tmp_path)
    if not entries:
        pytest.fail("Successful Teams chat discovery published no release entries")
    if not any(
        json.loads(entry["payload"])["entry_kind"] == "resource" for entry in entries
    ):
        pytest.fail("Teams release omitted the message resource impact")


def test_failed_chat_discovery_does_not_publish_release(
    tmp_path: Path, graph_fixture: GraphFixture
) -> None:
    _routes(graph_fixture, message_status=503)
    result = crawl(
        tmp_path,
        graph_fixture,
        ["crawl", "microsoft_teams_chat_discover"],
        extra_settings={**_SETTINGS, "RETRY_TIMES": 0, "MS_GRAPH_ERROR_MAX_RETRIES": 0},
    )
    if result.returncode:
        pytest.fail(result.stderr[-4000:])
    if _entries(tmp_path):
        pytest.fail("Failed Teams chat discovery published downstream work")


def test_deletion_locator_uses_exact_deletion_primary_key() -> None:
    """A Teams deletion has `deletion_id`, not a message observation id."""
    from types import SimpleNamespace
    from typing import cast

    from sqlalchemy.orm import Session

    from message_ingest.catalog.stores.microsoft.teams._handoff import stage_deletion

    class Recorder:
        fact = None

        def stage_state_fact_in_session(self, _writer, fact):
            self.fact = fact

    row = SimpleNamespace(
        source_id="teams-fixture",
        scope_key=["message", "chat", "chat-a", "message-a"],
        deletion_id=42,
        deletion_kind="notification",
        declared_deleted_at=None,
        readback_state="not_found",
        readback_observed_at=None,
        readback_evidence_id=None,
        evidence_id="deletion-evidence",
        observed_at="2026-10-08T00:00:00+00:00",
    )
    recorder = Recorder()
    stage_deletion(
        cast(Session, object()),
        cast(AcquisitionHandoffStore, recorder),
        spider_name="microsoft_teams_notification_reconcile",
        row=row,
        run_id="run-a",
        outcome="created",
    )
    assert recorder.fact is not None
    assert json.loads(recorder.fact.source_version_locator.observation_id) == [
        "deletion",
        42,
    ]


def test_native_chat_crawl_to_exact_a2_intake(
    tmp_path: Path, graph_fixture: GraphFixture
) -> None:
    """Cross the real Scrapy → saved evidence → release → A2 workset boundary."""
    import asyncio

    from msgloom.persistence import Phase1Persistence
    from msgloom.preparation_pipeline.intake import PreparationIntakeService
    from msgloom.preparation_pipeline.intake_models import IntakeScope
    from msgloom.sources import ReleaseSourceReader, SavedSourceReaderConfig
    from tests.handoff_release_reader_helpers import bind_fixture_source
    from tests.preparation_intake_helpers import payload, run

    _routes(graph_fixture)
    result = crawl(
        tmp_path,
        graph_fixture,
        ["crawl", "microsoft_teams_chat_discover"],
        extra_settings=_SETTINGS,
    )
    if result.returncode:
        pytest.fail(result.stderr[-4000:])
    bind_fixture_source(tmp_path / "catalog.sqlite3", "teams-fixture")

    async def check() -> None:
        reader = ReleaseSourceReader(
            SavedSourceReaderConfig(
                catalog_path=tmp_path / "catalog.sqlite3",
                evidence_roots=(tmp_path / "raw",),
            )
        )
        persistence = await Phase1Persistence.open(f"sqlite:///{tmp_path / 'a2.db'}")
        try:
            ceiling = await reader.catalog.max_release_entry_seq(
                "teams-fixture", "teams_chat"
            )
            page = await reader.catalog.list_release_entries(
                "teams-fixture",
                "teams_chat",
                after_seq=0,
                through_seq=ceiling,
                limit=100,
            )
            assert page.entries and not page.has_more
            records = []
            for entry in page.entries:
                released = await reader.read_entry(entry.reference)
                if entry.entry_kind == "resource":
                    assert released.selection is not None
                    records.append(released.selection.record)
            assert len(records) == 1
            assert records[0].source_type.value == "teams_chat_message"
            assert records[0].body is not None
            assert records[0].body.content == "hello"
            scope = IntakeScope(
                catalog=await reader.catalog.catalog_identity(),
                source_id="teams-fixture",
                stream="teams_chat",
                consumer_id="native-teams-consumer",
            )
            service = PreparationIntakeService(persistence, reader)
            first = await run(service, scope, identity="native-teams-first", limit=100)
            workset = await payload(persistence, first)
            assert len(workset.entries) == len(page.entries)
            assert len(workset.selections) == 1
            assert not workset.held
            assert (
                await persistence.get_preparation_intake_cursor(scope) == workset.cutoff
            )
            assert (
                await run(service, scope, identity="native-teams-repeat", limit=100)
                is None
            )
        finally:
            await reader.close()
            await persistence.close()

    asyncio.run(check())


def test_native_channel_root_reply_to_a2_intake(
    tmp_path: Path, graph_fixture: GraphFixture
) -> None:
    """Verify scoped roots and replies survive real native crawl/release/intake."""
    import asyncio

    from msgloom.persistence import Phase1Persistence
    from msgloom.preparation_pipeline.intake import PreparationIntakeService
    from msgloom.preparation_pipeline.intake_models import IntakeScope
    from msgloom.sources import ReleaseSourceReader, SavedSourceReaderConfig
    from tests.handoff_release_reader_helpers import bind_fixture_source
    from tests.preparation_intake_helpers import payload, run
    from tests.test_teams_channel_crawl import (
        _add_channel_routes,
        _add_common_team_routes,
    )

    _add_common_team_routes(graph_fixture)
    _add_channel_routes(graph_fixture)
    result = crawl(
        tmp_path,
        graph_fixture,
        ["crawl", "microsoft_teams_channel_discover"],
        extra_settings=_SETTINGS,
    )
    if result.returncode:
        pytest.fail(result.stderr[-4000:])
    bind_fixture_source(tmp_path / "catalog.sqlite3", "teams-fixture")

    async def check():
        reader = ReleaseSourceReader(
            SavedSourceReaderConfig(
                catalog_path=tmp_path / "catalog.sqlite3",
                evidence_roots=(tmp_path / "raw",),
            )
        )
        persistence = await Phase1Persistence.open(f"sqlite:///{tmp_path / 'a2.db'}")
        try:
            ceiling = await reader.catalog.max_release_entry_seq(
                "teams-fixture", "teams_channel"
            )
            page = await reader.catalog.list_release_entries(
                "teams-fixture",
                "teams_channel",
                after_seq=0,
                through_seq=ceiling,
                limit=100,
            )
            records = []
            for entry in page.entries:
                released = await reader.read_entry(entry.reference)
                if released.selection is not None:
                    records.append(released.selection.record)
            scopes = {record.source.identity for record in records}
            assert len(records) == 5
            assert len(scopes) == 5
            assert any("channel-reply" in identity for identity in scopes)
            assert all(
                record.source_type.value == "teams_channel_message"
                for record in records
            )
            scope = IntakeScope(
                catalog=await reader.catalog.catalog_identity(),
                source_id="teams-fixture",
                stream="teams_channel",
                consumer_id="native-channel-consumer",
            )
            first = await run(
                PreparationIntakeService(persistence, reader),
                scope,
                identity="native-channel",
                limit=100,
            )
            workset = await payload(persistence, first)
            assert len(workset.entries) == len(page.entries)
            assert len(workset.selections) == 5
            assert not workset.held
            assert (
                await persistence.get_preparation_intake_cursor(scope) == workset.cutoff
            )
        finally:
            await reader.close()
            await persistence.close()

    asyncio.run(check())
