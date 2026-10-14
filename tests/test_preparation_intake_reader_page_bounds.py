"""Do not strand accepted A2 work behind a narrower A1 reader page bound."""

import asyncio
from dataclasses import replace

import pytest

from msgloom.contracts import TerminalStatus
from msgloom.persistence import Phase1Persistence
from msgloom.preparation_pipeline.intake import PreparationIntakeService
from msgloom.preparation_pipeline.intake_models import IntakeScope
from msgloom.sources import SavedSourceReaderConfig, SourceReaderLimits
from msgloom.sources.release_reader import ReleaseSourceReader
from tests.preparation_intake_helpers import payload, run
from tests.preparation_pipeline.test_scheduled_recovery import context, repeated_release
from tests.source_reader.conftest import saved_catalog as saved_catalog  # noqa: PLC0414


@pytest.mark.parametrize("reader_limit", [1, 2, 200])
def test_public_intake_caps_requested_page_to_reader_limits(
    saved_catalog, tmp_path, reader_limit: int
) -> None:
    """A 201-entry intake budget must still drain finite smaller reader pages."""
    for index in range(3):
        repeated_release(saved_catalog, f"page-{index}")

    async def check() -> None:
        reader = ReleaseSourceReader(
            SavedSourceReaderConfig(
                catalog_path=saved_catalog["database"],
                evidence_roots=(saved_catalog["evidence_root"],),
                limits=SourceReaderLimits(max_list_results=reader_limit),
            )
        )
        persistence = await Phase1Persistence.open(
            f"sqlite:///{tmp_path / 'reader-bounded-intake.sqlite3'}"
        )
        try:
            scope = IntakeScope(
                catalog=await reader.catalog.catalog_identity(),
                source_id="synthetic-source",
                stream="todo",
                consumer_id="reader-limit-consumer",
            )
            service = PreparationIntakeService(persistence, reader)
            seen = []
            previous = 0
            for i in range(3):
                result = await run(service, scope, identity=f"page-{i}", limit=201)
                if result is None:
                    break
                workset = await payload(persistence, result)
                if (
                    workset.held
                    or not workset.entries
                    or len(workset.entries) > reader_limit
                ):
                    pytest.fail("Reader bound was not enforced without losing work")
                if workset.previous.last_release_entry_seq != previous:
                    pytest.fail("Reader page cap changed the committed cursor anchor")
                seen.extend(entry.release_entry_seq for entry in workset.entries)
                previous = workset.cutoff.last_release_entry_seq
            if len(seen) != 3 or len(set(seen)) != 3:
                pytest.fail(f"Page cap omitted or duplicated committed work: {seen}")
            if await run(service, scope, identity="drained", limit=201) is not None:
                pytest.fail("Drained reader-limited releases reappeared")
            if (
                await persistence.get_preparation_intake_cursor(scope)
            ).last_release_entry_seq != seen[-1]:
                pytest.fail("Page cap failed to advance the final durable cursor")
        finally:
            await reader.close()
            await persistence.close()

    asyncio.run(check())


def test_configured_scheduled_201_entry_budget_is_bounded_not_stuck(
    saved_catalog, tmp_path
) -> None:
    """The valid 201-entry operator budget does not suppress new work."""
    repeated_release(saved_catalog, "configured-201")

    async def check() -> None:
        persistence, scope, handler, request = await context(
            saved_catalog, tmp_path, entries=0
        )
        try:
            original = handler._operation
            target = original.intake_targets[0].model_copy(update={"max_entries": 201})
            handler._operation = replace(
                original,
                max_records=201,
                intake_targets=(target,),
            )
            outcome = await handler.run(request)
            cursor = await persistence.get_preparation_intake_cursor(scope)
            worksets = await persistence.list_preparation_intake_worksets(
                scope, pending_only=False
            )
            if cursor.last_release_entry_seq != 1 or not worksets:
                pytest.fail("Configured 201-entry budget stranded valid fresh work")
            if outcome.status not in {
                TerminalStatus.COMPLETE,
                TerminalStatus.INCOMPLETE,
            }:
                pytest.fail("Scheduled operation did not safely finish its page")
        finally:
            await persistence.close()

    asyncio.run(check())
