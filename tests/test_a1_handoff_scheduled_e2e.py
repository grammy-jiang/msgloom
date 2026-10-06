"""Qualify Task 15 scenario 1 through native A1 and public scheduled A2."""

import asyncio

import pytest

from msgloom.cli.composition import execute_invocation
from msgloom.cli.models import ScheduledPrepareInvocation
from msgloom.contracts import TerminalStatus
from msgloom.persistence import Phase1Persistence
from msgloom.preparation.records import PreparedRecord
from msgloom.preparation_pipeline.intake_models import (
    IntakeScope,
    PreparationIntakeWorkset,
)
from msgloom.sources import CollectedSelection
from msgloom.sources.release_reader import ReleaseSourceReader
from tests.handoff_qualification.mail_scheduled import (
    CONSUMER,
    MESSAGE,
    SOURCE,
    SUBJECT,
    acquire_one,
    configuration,
    durable_outputs,
)


def test_native_mail_scheduled_intake_prepares_once(tmp_path):
    """A real release must prepare once and retain its exact replay lineage.

    Missing intake, mutable LIVE recapture, false workset completion, and a
    repeated preparation output must each fail this scenario. The provider
    fixture is already closed before either finite scheduled invocation.
    """
    body = acquire_one(tmp_path)
    config = configuration(tmp_path)

    async def run():
        reader = ReleaseSourceReader(config.source_reader_config())
        try:
            page = await reader.catalog.list_release_entries(
                SOURCE, "outlook_mail", after_seq=0, through_seq=1, limit=2
            )
            if len(page.entries) != 1 or page.has_more:
                pytest.fail("Native acquisition did not release exactly one entry")
            entry = page.entries[0]
            if (
                await reader.catalog.max_release_entry_seq(SOURCE, "outlook_mail") != 1
                or entry.resource_kind != "message"
                or entry.resource_identity != MESSAGE
                or entry.entry_kind != "resource"
                or entry.group.coverage_kind != "complete"
                or entry.group.authority_revision is not None
            ):
                pytest.fail("Native Mail release changed its fixture semantics")
            exact = await reader.read_entry(entry.reference)
            selected = exact.selection
            if selected is None or selected.record.subject != SUBJECT:
                pytest.fail("Released Reader did not reconstruct the fixture Mail")
            saved = selected.record.source_bytes
            if saved is None or await reader.load_saved_bytes(saved) != body:
                pytest.fail("Mail selection lost its exact acquired evidence bytes")
            scope = IntakeScope(
                catalog=await reader.catalog.catalog_identity(),
                source_id=SOURCE,
                stream="outlook_mail",
                consumer_id=CONSUMER,
            )
        finally:
            await reader.close()

        first = await execute_invocation(
            config,
            ScheduledPrepareInvocation(
                configuration_version=config.version,
                execution="scheduled-one",
                attempt="attempt-one",
                caller="operator-cli",
                authority_ref="owner-approved",
            ),
        )
        if first.status not in {TerminalStatus.COMPLETE, TerminalStatus.INCOMPLETE}:
            pytest.fail(f"First scheduled invocation failed: {first}")
        prepared_refs = tuple(r for r in first.result_refs if r.kind == "prepared")
        if len(prepared_refs) != 1:
            pytest.fail("One acquired Mail must produce exactly one prepared result")

        persistence = await Phase1Persistence.open(config.database_url)
        try:
            states = await persistence.list_preparation_intake_worksets(
                scope, pending_only=False
            )
            if len(states) != 1 or states[0].state != "terminal":
                pytest.fail("Scheduled preparation did not durably complete once")
            state = states[0]
            if (
                state.terminal_status != first.status
                or state.result_refs != first.result_refs
            ):
                pytest.fail("Durable completion lost its exact terminal output refs")
            if await persistence.list_preparation_intake_worksets(scope):
                pytest.fail("Completed scheduled work remained pending")
            workset_result = await persistence.get_result(state.workset.result_id)
            if workset_result is None or workset_result.semantic_data_ref is None:
                pytest.fail("Intake omitted its immutable workset payload")
            workset = await persistence.load_semantic_data(
                workset_result.semantic_data_ref
            )
            if not isinstance(workset, PreparationIntakeWorkset):
                pytest.fail("Intake workset payload has the wrong type")
            if (
                workset.entries != (entry.reference,)
                or workset.previous.last_release_entry_seq != 0
                or len(workset.selections) != 1
                or workset.held
                or workset.transitions
                or await persistence.get_preparation_intake_cursor(scope)
                != workset.cutoff
            ):
                pytest.fail("Intake did not commit the exact genesis-to-release cut")
            selection_ref = workset.selection_refs[0]
            selection_result = await persistence.get_result(selection_ref.result_id)
            if selection_result is None or selection_result.semantic_data_ref is None:
                pytest.fail("Intake lost its durable collected selection")
            frozen = await persistence.load_semantic_data(
                selection_result.semantic_data_ref
            )
            if not isinstance(frozen, CollectedSelection) or frozen != selected:
                pytest.fail("Scheduled intake changed the exact released selection")
            prepared_result = await persistence.get_result(prepared_refs[0].result_id)
            if prepared_result is None or prepared_result.semantic_data_ref is None:
                pytest.fail("Preparation did not persist its semantic output")
            if (
                not prepared_result.acceptable
                or prepared_result.input_refs[0] != selection_ref
            ):
                pytest.fail("Preparation did not REPLAY the frozen intake result")
            prepared = await persistence.load_semantic_data(
                prepared_result.semantic_data_ref
            )
            if (
                not isinstance(prepared, PreparedRecord)
                or prepared.source != frozen.source
                or prepared.subject != SUBJECT
            ):
                pytest.fail("Prepared Mail differs from its exact released source")
        finally:
            await persistence.close()

        before = durable_outputs(tmp_path)
        second = await execute_invocation(
            config,
            ScheduledPrepareInvocation(
                configuration_version=config.version,
                execution="scheduled-two",
                attempt="attempt-two",
                caller="operator-cli",
                authority_ref="owner-approved",
            ),
        )
        if second.status is not TerminalStatus.COMPLETE or second.result_refs:
            pytest.fail("Repeated finite invocation fabricated new preparation work")
        if durable_outputs(tmp_path) != before:
            pytest.fail("Repeated invocation duplicated or rewrote durable outputs")

    asyncio.run(run())
