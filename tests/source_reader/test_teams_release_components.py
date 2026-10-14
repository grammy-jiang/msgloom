"""Teams context, parent refresh and immutable release evidence contracts."""

import asyncio
from pathlib import Path

import pytest
from sqlalchemy import select

from message_ingest.acquisition.handoff import (
    AcquisitionStream,
    FactSpec,
    ReleaseEntryKind,
    ReleaseEntrySpec,
    ReleaseGroupSpec,
    ReleaseKind,
)
from message_ingest.catalog.models.handoff import AcquisitionFact
from message_ingest.catalog.store import Catalog
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from msgloom.sources.models import SavedSourceReaderConfig
from msgloom.sources.release_reader import ReleaseSourceReader
from tests.source_reader.test_teams_release_intake import _release_messages
from tests.source_reader.test_teams_saved_source import SOURCE, _build_fixture


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
                    entry_kind=ReleaseEntryKind.TRANSITION
                    if fact.fact_kind == "scoped_state_transition"
                    else ReleaseEntryKind.CONTEXT,
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
            if len(page.entries) != 2:
                pytest.fail("Expected len(page.entries) == 2")
            contexts = transitions = 0
            for entry in page.entries:
                released = await reader.read_entry(entry.reference)
                if entry.entry_kind == "context":
                    contexts += 1
                    if not (
                        any(f.fact_kind == "control_context" for f in released.facts)
                    ):
                        pytest.fail(
                            "Expected any((f.fact_kind == 'control_context' for f in released.facts))"
                        )
                    if not (released.selection is None):
                        pytest.fail("Expected released.selection is None")
                else:
                    transitions += 1
                    if len(released.transitions) != 1:
                        pytest.fail("Expected len(released.transitions) == 1")
                    if released.transitions[0].reason != "provider_deleted":
                        pytest.fail(
                            "Expected released.transitions[0].reason == 'provider_deleted'"
                        )
                    if released.transitions[0].scope_kind != "teams_chat":
                        pytest.fail(
                            "Expected released.transitions[0].scope_kind == 'teams_chat'"
                        )
            if (contexts, transitions) != (1, 1):
                pytest.fail("Expected (contexts, transitions) == (1, 1)")
        finally:
            await reader.close()

    asyncio.run(run())


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
            if len(payloads) != 1:
                pytest.fail("Expected len(payloads) == 1")
            fact = FactSpec.from_json(payloads[0])
            if fact.fact_kind != "component_observation":
                pytest.fail("Expected fact.fact_kind == 'component_observation'")
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
                        entry_kind=ReleaseEntryKind.COMPONENT,
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
            if len(workset.entries) != 1:
                pytest.fail("Expected len(workset.entries) == 1")
            if not (not workset.held and not workset.selections):
                pytest.fail("Expected not workset.held and (not workset.selections)")
            if len(workset.transitions) != 1:
                pytest.fail("Expected len(workset.transitions) == 1")
            transition = workset.transitions[0]
            if transition.transition_kind != "context_refresh":
                pytest.fail("Expected transition.transition_kind == 'context_refresh'")
            if transition.resource_kind != "teams_message":
                pytest.fail("Expected transition.resource_kind == 'teams_message'")
            if transition.resource_identity != fact.parent_resource_identity:
                pytest.fail(
                    "Expected transition.resource_identity == fact.parent_resource_identity"
                )
        finally:
            await reader.close()
            await persistence.close()

    asyncio.run(check())


def test_immutable_teams_release_keeps_attachment_and_ignores_later_deletion(
    tmp_path: Path,
) -> None:
    """An exact release cannot gain future context or lose embedded attachments."""
    from message_ingest.catalog.models.microsoft.teams import (
        TeamsMessageDeletionObservation,
    )
    from msgloom.sources._snapshot import encode_selection
    from msgloom.sources._teams_catalog import scope_digest
    from tests.source_reader.test_teams_saved_source import _evidence

    bootstrap = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    bootstrap.close()
    fixture = _build_fixture(tmp_path)
    _release_messages(fixture.database, AcquisitionStream.TEAMS_CHAT)

    async def check() -> None:
        reader = ReleaseSourceReader(
            SavedSourceReaderConfig(
                catalog_path=fixture.database, evidence_roots=(fixture.evidence_root,)
            )
        )
        try:
            page = await reader.catalog.list_release_entries(
                SOURCE, "teams_chat", after_seq=0, through_seq=100, limit=10
            )
            original = None
            ref = None
            for entry in page.entries:
                released = await reader.read_entry(entry.reference)
                if (
                    released.selection
                    and released.selection.record.source == fixture.chat_a
                ):
                    original = released.selection
                    ref = entry.reference
            if original is None or ref is None:
                pytest.fail("The first Teams chat message was never released")
            if len(original.record.attachments) != 1:
                pytest.fail("Teams release dropped its embedded attachment")
            before = encode_selection(original, 32 * 1024 * 1024)
            catalog = Catalog(f"sqlite:///{fixture.database}")
            try:
                observed = "2026-10-05T00:00:00+00:00"
                scope = ["message", "chat", "chat-a", "same-message"]
                with catalog.writer_session() as session:
                    _evidence(
                        session,
                        fixture.evidence_root,
                        "future-unreleased-deletion",
                        {"id": "same-message"},
                        observed,
                    )
                    session.add(
                        TeamsMessageDeletionObservation(
                            source_id=SOURCE,
                            scope_key=scope,
                            scope_key_sha256=scope_digest(scope),
                            deletion_kind="notification",
                            declared_deleted_at=observed,
                            observed_at=observed,
                            evidence_id="future-unreleased-deletion",
                            run_id="future-unreleased-run",
                            evidence_run_id="teams-test-run",
                            readback_state="not-attempted",
                            readback_observed_at=None,
                            readback_evidence_id=None,
                            readback_evidence_run_id=None,
                        )
                    )
            finally:
                catalog.close()
            after = await reader.read_entry(ref)
            if after.selection is None:
                pytest.fail("A previous Teams selection disappeared")
            if encode_selection(after.selection, 32 * 1024 * 1024) != before:
                pytest.fail(
                    "Future Teams deletion mutated an immutable released selection"
                )
        finally:
            await reader.close()

    asyncio.run(check())
