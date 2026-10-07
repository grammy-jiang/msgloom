"""Acceptance for unchanged saved content across repeated listing and runs."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import cast

import pytest

from msgloom.contracts import PhaseCapability, ResultRef, TerminalStatus, VersionRef
from msgloom.persistence import Phase1Persistence
from msgloom.preparation import PreparedSourceType
from msgloom.preparation_pipeline import PreparationHandler

from .helpers import app_for, open_store, preparation_plan, request, saved_reader


async def _prepared_versions(
    store: Phase1Persistence, refs: tuple[ResultRef, ...]
) -> tuple[VersionRef, ...]:
    values: list[VersionRef] = []
    for ref in refs:
        if ref.kind != "prepared":
            continue
        result = await store.get_result(ref.result_id)
        if result is None:
            pytest.fail("prepared result is missing")
        values.extend(result.prepared_versions)
    return tuple(sorted(values, key=lambda item: (item.identity, item.version)))


def test_unchanged_saved_versions_keep_prepared_identity_across_runs(
    saved_catalog: dict[str, object], tmp_path: Path
) -> None:
    """A repeated listing and a new preparation run add no new semantic version."""

    async def exercise() -> None:
        reader = saved_reader(saved_catalog)
        store = await open_store(tmp_path / "unchanged.sqlite3")
        try:
            source_id = cast(str, saved_catalog["source_id"])
            first = await reader.list_versions(
                PreparedSourceType.OUTLOOK_EMAIL, source_id=source_id, limit=10
            )
            repeated = await reader.list_versions(
                PreparedSourceType.OUTLOOK_EMAIL, source_id=source_id, limit=10
            )
            if not first or first != repeated:
                pytest.fail("repeated listing changed the saved source versions")
            sources = tuple(first)
            runs: list[tuple[VersionRef, ...]] = []
            result_ids: list[set[str]] = []
            for run in ("first", "second"):
                plan = preparation_plan(sources, attempt=f"unchanged-{run}")
                handler = PreparationHandler(store, reader, plan)
                outcome = await app_for(
                    store, PhaseCapability.PREPARE, lambda handler=handler: handler
                ).run(request(PhaseCapability.PREPARE, f"unchanged-{run}", sources))
                if outcome.status not in {
                    TerminalStatus.COMPLETE,
                    TerminalStatus.INCOMPLETE,
                }:
                    pytest.fail(f"preparation run failed: {outcome}")
                runs.append(await _prepared_versions(store, outcome.result_refs))
                result_ids.append({ref.result_id for ref in outcome.result_refs})
            if not runs[0] or runs[0] != runs[1]:
                pytest.fail("re-preparing unchanged versions changed prepared identity")
            if result_ids[0] & result_ids[1]:
                pytest.fail("a new run overwrote an earlier durable result")
        finally:
            await store.close()
            await reader.close()

    asyncio.run(exercise())
