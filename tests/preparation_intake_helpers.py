"""Real release and neutral-store fixtures for intake recovery tests."""

import importlib

import pytest

from msgloom.contracts import AttemptIdentity, ExecutionIdentity
from msgloom.persistence import Phase1Persistence
from msgloom.preparation_pipeline.intake_models import IntakeScope
from msgloom.sources.handoff_models import Stream
from tests.source_reader.release_nonmail_helpers import (
    SOURCE,
    fact,
    publish,
    reader_api,
)


def release(saved, *, stream="todo", suffix=""):
    """Publish one authentic local Graph release with unique fact identity."""
    from dataclasses import replace

    item = (
        fact(
            "todo",
            "todo_task",
            '["list","task"]',
            "ev-todo-old",
            scope_kind="todo_list",
            scope_identity="list",
        )
        if stream == "todo"
        else fact(
            "contacts",
            "contact",
            "contact",
            "ev-contact",
            scope_kind="contacts_collection",
            scope_identity="default",
        )
    )
    return publish(saved, [replace(item, run_id="run" + suffix)])


async def setup(saved, tmp_path, *, stream: Stream = "todo"):
    """Open actual reader and async persistence; demand the public service."""
    module = importlib.import_module("msgloom.preparation_pipeline")
    if not hasattr(module, "PreparationIntakeService"):
        pytest.fail("Task13 PreparationIntakeService is missing")
    reader = reader_api(saved)
    persistence = await Phase1Persistence.open(f"sqlite:///{tmp_path / 'a2.db'}")
    scope = IntakeScope(
        catalog=await reader.catalog.catalog_identity(),
        source_id=SOURCE,
        stream=stream,
        consumer_id="consumer",
    )
    return (
        reader,
        persistence,
        scope,
        module.PreparationIntakeService(persistence, reader),
    )


async def run(service, scope, *, identity="one", **kwargs):
    """Run one finite intake with stable consumer and explicit build versions."""
    return await service.run(
        scope,
        execution=ExecutionIdentity(identity),
        attempt=AttemptIdentity(identity),
        configuration_version=kwargs.pop("configuration_version", "config-1"),
        code_version=kwargs.pop("code_version", "code-1"),
        **kwargs,
    )


async def payload(persistence, result):
    """Load a real committed workset through its integrity reference."""
    if result is None or result.semantic_data_ref is None:
        pytest.fail("Expected durable intake workset")
    return await persistence.load_semantic_data(result.semantic_data_ref)


def large_transition_group(
    saved,
    *,
    entry_count=9,
    identity_pad="",
    scope_kind="contacts_collection",
    scope_identity="default",
    selections=False,
):
    """Publish real authority entries with 128 transitions or components."""
    from dataclasses import replace

    from message_ingest.acquisition.handoff import (
        AcquisitionFactKind,
        AcquisitionStream,
        ReleaseEntryKind,
        ReleaseEntrySpec,
        ReleaseGroupSpec,
        ReleaseKind,
    )
    from message_ingest.catalog import Catalog
    from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
    from tests.source_reader.release_nonmail_helpers import WHEN

    catalog = Catalog(f"sqlite:///{saved['database']}")
    ledger = AcquisitionHandoffStore(catalog)
    try:
        with catalog.writer_session() as session:
            stream = "outlook_calendar" if selections else "contacts"
            parent_kind = "calendar_event" if selections else "contact_folder"
            entries = []
            winning = []
            for index in range(entry_count):
                members = []
                for ordinal in range(128):
                    item = replace(
                        fact(
                            stream,
                            "calendar_series" if selections else "contact",
                            f"contact-{index}-{ordinal}" + identity_pad,
                            "unused",
                            parent_resource_kind=parent_kind,
                            parent_resource_identity=f"folder-{index}",
                            scope_kind=scope_kind,
                            scope_identity=scope_identity,
                        ),
                        fact_kind=(
                            AcquisitionFactKind.COMPONENT_OBSERVATION
                            if selections
                            else AcquisitionFactKind.SCOPED_STATE_TRANSITION
                        ),
                        component_kind="series" if selections else None,
                        source_version_locator=None,
                        evidence_id=None,
                        transition_reason="unavailable" if selections else "present",
                    )
                    staged = ledger.stage_authority_fact_in_session(session, item)
                    members.append(
                        (staged.fact_id, "component" if selections else "transition")
                    )
                    winning.append(staged.fact_id)
                entries.append(
                    ReleaseEntrySpec(
                        resource_kind=parent_kind,
                        resource_identity=f"folder-{index}",
                        scope_kind=scope_kind,
                        scope_identity=scope_identity,
                        entry_kind=(
                            ReleaseEntryKind.COMPONENT
                            if selections
                            else ReleaseEntryKind.TRANSITION
                        ),
                        facts=tuple(members),
                    )
                )
            ledger.release_authority_group_in_session(
                session,
                ReleaseGroupSpec(
                    source_id=SOURCE,
                    stream=AcquisitionStream(stream),
                    release_kind=ReleaseKind.AUTHORITY_SCOPE,
                    subject_kind="fixture",
                    subject_identity="large-group",
                    owner_run_id="current-acquisition-run",
                    released_at=WHEN,
                    coverage_kind="complete",
                ),
                entries,
                winning_fact_ids=winning,
            )
    finally:
        catalog.close()
