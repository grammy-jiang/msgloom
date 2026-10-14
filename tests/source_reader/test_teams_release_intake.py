"""Prove a committed Teams release is readable through the actual A2 intake API."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import select

from message_ingest.acquisition.handoff import (
    AcquisitionStream,
    FactSpec,
    ReleaseEntrySpec,
    ReleaseGroupSpec,
    ReleaseKind,
)
from message_ingest.catalog.models.handoff import AcquisitionFact
from message_ingest.catalog.models.microsoft.teams import TeamsMessageObservation
from message_ingest.catalog.store import Catalog
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from message_ingest.catalog.stores.microsoft.teams._handoff import stage_message
from msgloom.preparation.records import PreparedSourceType
from msgloom.sources.models import SavedSourceReaderConfig
from msgloom.sources.release_reader import ReleaseSourceReader
from tests.source_reader.test_teams_saved_source import SOURCE, _build_fixture


def _release_messages(path: Path, stream: AcquisitionStream) -> None:
    catalog = Catalog(f"sqlite:///{path}")
    try:
        handoff = AcquisitionHandoffStore(catalog)
        with catalog.writer_session() as writer:
            for observation_id in (
                (1, 2) if stream is AcquisitionStream.TEAMS_CHAT else (3, 4)
            ):
                row = writer.get(TeamsMessageObservation, observation_id)
                assert row is not None
                stage_message(
                    writer,
                    handoff,
                    spider_name="microsoft_teams_chat_discover"
                    if stream is AcquisitionStream.TEAMS_CHAT
                    else "microsoft_teams_channel_discover",
                    row=row,
                    run_id="test-release-run",
                    outcome="created",
                )
            staged = writer.scalars(
                select(AcquisitionFact.payload)
                .where(
                    AcquisitionFact.source_id == SOURCE,
                    AcquisitionFact.stream == stream,
                )
                .order_by(AcquisitionFact.fact_id)
            ).all()
            facts = [FactSpec.from_json(payload) for payload in staged]
            entries = tuple(
                ReleaseEntrySpec(
                    resource_kind=fact.resource_kind,
                    resource_identity=fact.resource_identity,
                    scope_kind=fact.scope_kind,
                    scope_identity=fact.scope_identity,
                    facts=((fact.fact_id, "primary"),),
                )
                for fact in facts
            )
            handoff.release_effective_group_in_session(
                writer,
                ReleaseGroupSpec(
                    source_id=SOURCE,
                    stream=stream,
                    release_kind=ReleaseKind.RESOURCE_SET,
                    subject_kind="teams_discovery",
                    subject_identity="test-release-run",
                    owner_run_id="test-release-run",
                    released_at=datetime.now(UTC).isoformat(),
                    coverage_kind="complete",
                ),
                entries,
            )
    finally:
        catalog.close()


@pytest.mark.parametrize(
    ("stream", "source_type", "count"),
    [
        (AcquisitionStream.TEAMS_CHAT, PreparedSourceType.TEAMS_CHAT_MESSAGE, 2),
        (AcquisitionStream.TEAMS_CHANNEL, PreparedSourceType.TEAMS_CHANNEL_MESSAGE, 2),
    ],
)
def test_release_reader_reconstructs_exact_teams_messages(
    tmp_path: Path,
    stream: AcquisitionStream,
    source_type: PreparedSourceType,
    count: int,
) -> None:
    # Production Catalog establishes immutable guards before fixture rows exist.
    bootstrap = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    bootstrap.close()
    fixture = _build_fixture(tmp_path)
    _release_messages(fixture.database, stream)

    async def run() -> None:
        reader = ReleaseSourceReader(
            SavedSourceReaderConfig(
                catalog_path=fixture.database,
                evidence_roots=(fixture.evidence_root,),
            )
        )
        try:
            cutoff = await reader.catalog.max_release_entry_seq(SOURCE, stream.value)
            page = await reader.catalog.list_release_entries(
                SOURCE, stream.value, after_seq=0, through_seq=cutoff, limit=10
            )
            assert len(page.entries) == count
            for entry in page.entries:
                result = await reader.read_entry(entry.reference)
                assert result.reference == entry.reference
                assert result.selection is not None
                assert result.selection.record.source_type == source_type
                assert result.selection.record.source_scope.kind == "source_scope"
                assert result.selection.record.body is not None
                assert result.selection.record.source_bytes is not None
                assert len(result.facts) == 1
        finally:
            await reader.close()

    asyncio.run(run())


def test_release_reader_preserves_teams_context_and_scoped_deletion(
    tmp_path: Path,
) -> None:
    """Non-message Teams impacts must be readable, not silently held."""

    from message_ingest.catalog.models.microsoft.teams import (
        TeamsMessageDeletionObservation,
        TeamsTopologyObservation,
    )
    from message_ingest.catalog.stores.microsoft.teams._handoff import (
        stage_deletion,
        stage_topology,
    )
    from tests.source_reader.test_teams_saved_source import _evidence

    bootstrap = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    bootstrap.close()
    fixture = _build_fixture(tmp_path)
    catalog = Catalog(f"sqlite:///{fixture.database}")
    try:
        handoff = AcquisitionHandoffStore(catalog)
        with catalog.writer_session() as writer:
            at = "2026-10-04T00:00:05+00:00"
            _evidence(
                writer, fixture.evidence_root, "topology-extra", {"id": "chat-a"}, at
            )
            _evidence(
                writer,
                fixture.evidence_root,
                "deletion-extra",
                {"id": "same-message"},
                at,
            )
            top = TeamsTopologyObservation(
                source_id=SOURCE,
                resource_kind="chat",
                scope_key=["chat", "chat-a"],
                scope_key_sha256="f" * 64,
                observed_at=at,
                evidence_id="topology-extra",
                run_id="context-run",
                evidence_run_id="teams-test-run",
                raw={"id": "chat-a"},
                context={},
            )
            deleted = TeamsMessageDeletionObservation(
                source_id=SOURCE,
                scope_key=["message", "chat", "chat-a", "same-message"],
                scope_key_sha256="e" * 64,
                deletion_kind="notification",
                declared_deleted_at=None,
                observed_at=at,
                evidence_id="deletion-extra",
                run_id="context-run",
                evidence_run_id="teams-test-run",
                readback_state="not_found",
                readback_observed_at=None,
                readback_evidence_id=None,
                readback_evidence_run_id=None,
            )
            writer.add_all([top, deleted])
            writer.flush()
            stage_topology(
                writer,
                handoff,
                spider_name="microsoft_teams_chat_discover",
                row=top,
                run_id="context-run",
                outcome="created",
            )
            stage_deletion(
                writer,
                handoff,
                spider_name="microsoft_teams_notification_reconcile",
                row=deleted,
                run_id="context-run",
                outcome="created",
            )
            staged = writer.scalars(
                select(AcquisitionFact.payload)
                .where(
                    AcquisitionFact.source_id == SOURCE,
                    AcquisitionFact.stream == AcquisitionStream.TEAMS_CHAT,
                    AcquisitionFact.run_id == "context-run",
                )
                .order_by(AcquisitionFact.fact_id)
            ).all()
            facts = [FactSpec.from_json(payload) for payload in staged]
            entries = tuple(
                ReleaseEntrySpec(
                    resource_kind=fact.resource_kind,
                    resource_identity=fact.resource_identity,
                    scope_kind=fact.scope_kind,
                    scope_identity=fact.scope_identity,
                    entry_kind="transition"
                    if fact.fact_kind == "scoped_state_transition"
                    else "context",
                    facts=(
                        (
                            fact.fact_id,
                            "transition"
                            if fact.fact_kind == "scoped_state_transition"
                            else "context",
                        ),
                    ),
                )
                for fact in facts
            )
            handoff.release_effective_group_in_session(
                writer,
                ReleaseGroupSpec(
                    source_id=SOURCE,
                    stream=AcquisitionStream.TEAMS_CHAT,
                    release_kind=ReleaseKind.RESOURCE_SET,
                    subject_kind="teams_notification_reconcile",
                    subject_identity="test",
                    owner_run_id="context-run",
                    released_at=at,
                    coverage_kind="complete",
                ),
                entries,
            )
    finally:
        catalog.close()

    async def run() -> None:
        reader = ReleaseSourceReader(
            SavedSourceReaderConfig(
                catalog_path=fixture.database,
                evidence_roots=(fixture.evidence_root,),
            )
        )
        try:
            max_seq = await reader.catalog.max_release_entry_seq(SOURCE, "teams_chat")
            page = await reader.catalog.list_release_entries(
                SOURCE, "teams_chat", after_seq=0, through_seq=max_seq, limit=10
            )
            assert len(page.entries) == 2
            contexts = transitions = 0
            for entry in page.entries:
                released = await reader.read_entry(entry.reference)
                if entry.entry_kind == "context":
                    contexts += 1
                    assert any(f.fact_kind == "control_context" for f in released.facts)
                    assert released.selection is None
                else:
                    transitions += 1
                    assert len(released.transitions) == 1
                    assert released.transitions[0].reason == "provider_deleted"
                    assert released.transitions[0].scope_kind == "teams_chat"
            assert (contexts, transitions) == (1, 1)
        finally:
            await reader.close()

    asyncio.run(run())


@pytest.mark.parametrize(
    "stream", [AcquisitionStream.TEAMS_CHAT, AcquisitionStream.TEAMS_CHANNEL]
)
def test_teams_release_drains_once_through_real_a2_workset(
    tmp_path: Path, stream: AcquisitionStream
) -> None:
    """Save release anchors and exact Teams selections, not a current-table scan."""
    from msgloom.persistence import Phase1Persistence
    from msgloom.preparation_pipeline.intake import PreparationIntakeService
    from msgloom.preparation_pipeline.intake_models import IntakeScope
    from tests.preparation_intake_helpers import payload, run

    bootstrap = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    bootstrap.close()
    fixture = _build_fixture(tmp_path)
    _release_messages(fixture.database, stream)

    async def check() -> None:
        reader = ReleaseSourceReader(
            SavedSourceReaderConfig(
                catalog_path=fixture.database,
                evidence_roots=(fixture.evidence_root,),
            )
        )
        persistence = await Phase1Persistence.open(f"sqlite:///{tmp_path / 'a2.db'}")
        try:
            scope = IntakeScope(
                catalog=await reader.catalog.catalog_identity(),
                source_id=SOURCE,
                stream=stream.value,
                consumer_id="teams-test-consumer",
            )
            service = PreparationIntakeService(persistence, reader)
            refs = []
            for index in range(2):
                result = await run(service, scope, identity=f"intake-{index}", limit=1)
                workset = await payload(persistence, result)
                assert len(workset.entries) == 1
                assert len(workset.selections) == 1
                assert not workset.held and not workset.transitions
                refs.extend(workset.entries)
            assert refs[0].release_entry_seq < refs[1].release_entry_seq
            cursor = await persistence.get_preparation_intake_cursor(scope)
            assert cursor.last_release_entry_seq == refs[1].release_entry_seq
            assert cursor.last_release_entry_digest == refs[1].entry_digest
            assert await run(service, scope, identity="intake-drained", limit=1) is None
            assert len(await persistence.list_preparation_intake_worksets(scope)) == 2
        finally:
            await reader.close()
            await persistence.close()

    asyncio.run(check())


def test_component_change_is_a_durable_parent_refresh_not_held(
    tmp_path: Path,
) -> None:
    """Pin component updates must retain a scoped downstream refresh impact."""
    from message_ingest.catalog.models.microsoft.teams import TeamsTopologyObservation
    from message_ingest.catalog.stores.microsoft.teams._handoff import stage_topology
    from msgloom.persistence import Phase1Persistence
    from msgloom.preparation_pipeline.intake import PreparationIntakeService
    from msgloom.preparation_pipeline.intake_models import IntakeScope
    from tests.preparation_intake_helpers import payload, run
    from tests.source_reader.test_teams_saved_source import _evidence

    bootstrap = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    bootstrap.close()
    fixture = _build_fixture(tmp_path)
    catalog = Catalog(f"sqlite:///{fixture.database}")
    try:
        handoff = AcquisitionHandoffStore(catalog)
        with catalog.writer_session() as writer:
            at = "2026-10-04T00:00:05+00:00"
            _evidence(writer, fixture.evidence_root, "pin-extra", {"id": "pin-1"}, at)
            pin = TeamsTopologyObservation(
                source_id=SOURCE,
                resource_kind="pin",
                scope_key=["pin", "chat-a", "same-message"],
                scope_key_sha256="d" * 64,
                observed_at=at,
                evidence_id="pin-extra",
                run_id="pin-run",
                evidence_run_id="teams-test-run",
                raw={"id": "pin-1"},
                context={"chat_id": "chat-a", "message_id": "same-message"},
            )
            writer.add(pin)
            writer.flush()
            stage_topology(
                writer,
                handoff,
                spider_name="microsoft_teams_chat_discover",
                row=pin,
                run_id="pin-run",
                outcome="created",
            )
            payloads = writer.scalars(
                select(AcquisitionFact.payload).where(
                    AcquisitionFact.source_id == SOURCE,
                    AcquisitionFact.stream == AcquisitionStream.TEAMS_CHAT,
                    AcquisitionFact.run_id == "pin-run",
                )
            ).all()
            assert len(payloads) == 1
            fact = FactSpec.from_json(payloads[0])
            assert fact.fact_kind == "component_observation"
            handoff.release_effective_group_in_session(
                writer,
                ReleaseGroupSpec(
                    source_id=SOURCE,
                    stream=AcquisitionStream.TEAMS_CHAT,
                    release_kind=ReleaseKind.RESOURCE_SET,
                    subject_kind="teams_chat_discovery",
                    subject_identity="pin-run",
                    owner_run_id="pin-run",
                    released_at=at,
                    coverage_kind="complete",
                ),
                (
                    ReleaseEntrySpec(
                        resource_kind=fact.resource_kind,
                        resource_identity=fact.resource_identity,
                        parent_resource_kind=fact.parent_resource_kind,
                        parent_resource_identity=fact.parent_resource_identity,
                        scope_kind=fact.scope_kind,
                        scope_identity=fact.scope_identity,
                        entry_kind="component",
                        facts=((fact.fact_id, "component"),),
                    ),
                ),
            )
    finally:
        catalog.close()

    async def check() -> None:
        reader = ReleaseSourceReader(
            SavedSourceReaderConfig(
                catalog_path=fixture.database,
                evidence_roots=(fixture.evidence_root,),
            )
        )
        persistence = await Phase1Persistence.open(f"sqlite:///{tmp_path / 'a2.db'}")
        try:
            scope = IntakeScope(
                catalog=await reader.catalog.catalog_identity(),
                source_id=SOURCE,
                stream="teams_chat",
                consumer_id="pin-consumer",
            )
            result = await run(
                PreparationIntakeService(persistence, reader),
                scope,
                identity="pin-intake",
                limit=10,
            )
            workset = await payload(persistence, result)
            assert len(workset.entries) == 1
            assert not workset.held and not workset.selections
            assert len(workset.transitions) == 1
            transition = workset.transitions[0]
            assert transition.transition_kind == "context_refresh"
            assert transition.resource_kind == "teams_message"
            assert transition.resource_identity == fact.parent_resource_identity
        finally:
            await reader.close()
            await persistence.close()

    asyncio.run(check())
