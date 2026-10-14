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
                if not (row is not None):
                    pytest.fail("Expected row is not None")
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
            if len(page.entries) != count:
                pytest.fail("Expected len(page.entries) == count")
            for entry in page.entries:
                result = await reader.read_entry(entry.reference)
                if result.reference != entry.reference:
                    pytest.fail("Expected result.reference == entry.reference")
                if not (result.selection is not None):
                    pytest.fail("Expected result.selection is not None")
                if result.selection.record.source_type != source_type:
                    pytest.fail(
                        "Expected result.selection.record.source_type == source_type"
                    )
                if result.selection.record.source_scope.kind != "source_scope":
                    pytest.fail(
                        "Expected result.selection.record.source_scope.kind == 'source_scope'"
                    )
                if not (result.selection.record.body is not None):
                    pytest.fail("Expected result.selection.record.body is not None")
                if not (result.selection.record.source_bytes is not None):
                    pytest.fail(
                        "Expected result.selection.record.source_bytes is not None"
                    )
                if len(result.facts) != 1:
                    pytest.fail("Expected len(result.facts) == 1")
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
                if len(workset.entries) != 1:
                    pytest.fail("Expected len(workset.entries) == 1")
                if len(workset.selections) != 1:
                    pytest.fail("Expected len(workset.selections) == 1")
                if not (not workset.held and not workset.transitions):
                    pytest.fail(
                        "Expected not workset.held and (not workset.transitions)"
                    )
                refs.extend(workset.entries)
            if not (refs[0].release_entry_seq < refs[1].release_entry_seq):
                pytest.fail(
                    "Expected refs[0].release_entry_seq < refs[1].release_entry_seq"
                )
            cursor = await persistence.get_preparation_intake_cursor(scope)
            if cursor.last_release_entry_seq != refs[1].release_entry_seq:
                pytest.fail(
                    "Expected cursor.last_release_entry_seq == refs[1].release_entry_seq"
                )
            if cursor.last_release_entry_digest != refs[1].entry_digest:
                pytest.fail(
                    "Expected cursor.last_release_entry_digest == refs[1].entry_digest"
                )
            if not (
                await run(service, scope, identity="intake-drained", limit=1) is None
            ):
                pytest.fail(
                    "Expected await run(service, scope, identity='intake-drained', limit=1) is None"
                )
            if len(await persistence.list_preparation_intake_worksets(scope)) != 2:
                pytest.fail(
                    "Expected len(await persistence.list_preparation_intake_worksets(scope)) == 2"
                )
        finally:
            await reader.close()
            await persistence.close()

    asyncio.run(check())


@pytest.mark.parametrize("stream", ["teams_chat", "teams_channel"])
def test_teams_stream_is_admissible_in_operator_intake_configuration(
    stream: str,
) -> None:
    """The real configured scheduler must accept explicitly supported Teams streams."""
    from pydantic import ValidationError

    from msgloom.configuration.models import PreparationIntakeTarget

    data = {
        "expected_catalog": {"catalog_identity": "catalog-teams", "schema_version": 1},
        "source_id": "teams-fixture",
        "stream": stream,
        "consumer_id": "teams-consumer",
    }
    try:
        target = PreparationIntakeTarget.model_validate(data)
    except ValidationError as error:
        pytest.fail(f"Configured Teams intake rejected: {error.errors()[0]['type']}")
    if target.stream != stream or target.max_entries != 100:
        pytest.fail("Teams intake validation changed other bounded target defaults")
    with pytest.raises(ValidationError):
        PreparationIntakeTarget.model_validate({**data, "stream": "teams_unsafe"})
