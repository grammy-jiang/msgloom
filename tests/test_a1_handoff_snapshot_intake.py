"""Drain a native To Do snapshot through the real bounded A2 intake."""

import asyncio

import pytest

from msgloom.persistence import Phase1Persistence
from msgloom.preparation_pipeline.intake import PreparationIntakeService
from msgloom.preparation_pipeline.intake_models import IntakeAnchor, IntakeScope
from msgloom.sources import ReleaseSourceReader, SavedSourceReaderConfig
from tests import test_todo_crawl as todo
from tests.handoff_qualification.feed import feed, successful
from tests.handoff_release_reader_helpers import bind_fixture_source
from tests.preparation_intake_helpers import payload, run

graph_server = todo.graph_server


def test_native_todo_snapshot_drains_through_bounded_worksets(tmp_path, graph_server):
    """Keep exact entry union and cursor continuity across an atomic group."""
    origin, _state, _seen, pages = graph_server
    extra = [f"extra-{number}" for number in range(40)]
    pages[todo.LISTS + todo.CURSOR]["value"].extend(
        {"id": identity} for identity in extra
    )
    for identity in extra:
        pages[f"{todo.LISTS}/{identity}/tasks?%24top=2"] = {"value": []}
    bind_fixture_source(tmp_path / "catalog.sqlite3", "todo-fixture")
    successful(todo._crawl(tmp_path, origin, action="sync"))
    published = feed(tmp_path, "todo-fixture", "todo", limit=7)
    expected = tuple(entry.reference for entry, _facts in published)
    if len(expected) != 96 or len({e.release_group_id for e, _ in published}) != 1:
        pytest.fail("Native snapshot did not publish one large atomic group")

    async def check():
        reader = ReleaseSourceReader(
            SavedSourceReaderConfig(
                catalog_path=tmp_path / "catalog.sqlite3",
                evidence_roots=(tmp_path / "raw",),
            )
        )
        persistence = await Phase1Persistence.open(f"sqlite:///{tmp_path / 'a2.db'}")
        try:
            scope = IntakeScope(
                catalog=await reader.catalog.catalog_identity(),
                source_id="todo-fixture",
                stream="todo",
                consumer_id="snapshot-consumer",
            )
            service = PreparationIntakeService(persistence, reader)
            previous = IntakeAnchor()
            admitted = []
            worksets = []
            # Six finite calls drain 96 entries with a 17-entry admission cap.
            for index in range(6):
                result = await run(
                    service, scope, identity=f"snapshot-{index}", limit=17
                )
                workset = await payload(persistence, result)
                if (
                    workset.previous != previous
                    or not 0 < len(workset.entries) <= 17
                    or workset.held
                ):
                    pytest.fail("Bounded native intake lost continuity or evidence")
                admitted.extend(workset.entries)
                worksets.append(result)
                previous = workset.cutoff
            if tuple(admitted) != expected or len(
                {e.release_entry_seq for e in admitted}
            ) != len(expected):
                pytest.fail("Native snapshot intake omitted or duplicated entries")
            final = expected[-1]
            cursor = await persistence.get_preparation_intake_cursor(scope)
            if (
                cursor != previous
                or cursor.last_release_entry_seq != final.release_entry_seq
                or cursor.last_release_entry_digest != final.entry_digest
            ):
                pytest.fail("Final native intake cursor lost the exact A1 anchor")
            pending = await persistence.list_preparation_intake_worksets(scope)
            if {s.workset.result_id for s in pending} != {
                result.result_id for result in worksets
            } or len(pending) != 6:
                pytest.fail("Snapshot worksets are not all durably discoverable")
            if await run(service, scope, identity="drained", limit=17) is not None:
                pytest.fail("Drained native snapshot was admitted again")
        finally:
            await reader.close()
            await persistence.close()

    asyncio.run(check())
