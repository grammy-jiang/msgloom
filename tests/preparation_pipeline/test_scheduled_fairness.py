"""Bind durable scheduling turns to bounded attempts across real restarts."""

import asyncio
from dataclasses import replace

import pytest

from msgloom.contracts import AttemptIdentity, ExecutionIdentity, TerminalStatus
from msgloom.persistence import Phase1Persistence
from msgloom.preparation_pipeline.intake import PreparationIntakeService
from msgloom.preparation_pipeline.scheduled import ScheduledPreparationHandler
from msgloom.sources.release_reader import ReleaseSourceReader
from tests.application_cli.test_scheduled_prepare import configuration
from tests.preparation_intake_helpers import run
from tests.preparation_pipeline.test_scheduled_recovery import (
    context,
    repeated_release,
)


@pytest.mark.parametrize("budget", [1, 2])
def test_failures_rotate_after_restart_and_new_arrivals_in_each_scope(
    saved_catalog, tmp_path, monkeypatch, budget
):
    """Each consumer gets bounded durable turns despite persistent failures."""
    for index in range(3):
        repeated_release(saved_catalog, f"initial-{index}")

    async def check():
        config = configuration(saved_catalog, tmp_path)
        persistence, scope, handler, request = await context(
            saved_catalog, tmp_path, budget=budget, entries=3
        )
        other = scope.model_copy(update={"consumer_id": "other"})
        reader = ReleaseSourceReader(config.source_reader_config())
        try:
            service = PreparationIntakeService(persistence, reader)
            for index in range(3):
                await run(service, other, identity=f"other-{index}", limit=1)
            scopes = (scope, other)
            original = {
                value.consumer_id: tuple(
                    state.workset
                    for state in await persistence.list_preparation_intake_worksets(
                        value
                    )
                )
                for value in scopes
            }
            operation = replace(
                handler._operation,
                intake_targets=tuple(
                    handler._operation.intake_targets[0].model_copy(
                        update={"consumer_id": value.consumer_id}
                    )
                    for value in scopes
                ),
            )
        finally:
            await reader.close()
            await persistence.close()
        seen = {value.consumer_id: [] for value in scopes}
        turns = []

        async def failed(self, reference, reader, request):
            turns.append(("attempt", reference))
            for value in scopes:
                states = await self._persistence.list_preparation_intake_worksets(value)
                if reference in tuple(state.workset for state in states):
                    seen[value.consumer_id].append(reference)
                    break
            raise ValueError("persistent failure consumes one scheduling turn")

        monkeypatch.setattr(ScheduledPreparationHandler, "_process", failed)
        for invocation in range(4):
            repeated_release(saved_catalog, f"arrival-{invocation}")
            persistence = await Phase1Persistence.open(config.database_url)
            select = persistence.select_preparation_intake_worksets

            async def selected(value, *, limit, select_api=select):
                if limit != 1:
                    pytest.fail("caller reserved more than one future attempt")
                result = await select_api(value, limit=limit)
                if result:
                    turns.append(("select", result[0].workset))
                return result

            monkeypatch.setattr(
                persistence, "select_preparation_intake_worksets", selected
            )
            current = ScheduledPreparationHandler(
                persistence,
                config.source_reader_config(),
                operation,
                AttemptIdentity(f"restart-{invocation}"),
            )
            before = {key: len(value) for key, value in seen.items()}
            try:
                outcome = await current.run(
                    replace(request, execution=ExecutionIdentity(f"run-{invocation}"))
                )
                if outcome.status is not TerminalStatus.INCOMPLETE:
                    pytest.fail("persistent failures did not remain pending")
                for value in scopes:
                    key = value.consumer_id
                    if len(seen[key]) - before[key] != budget:
                        pytest.fail("per-scope attempt budget was not preserved")
                    states = await persistence.list_preparation_intake_worksets(value)
                    if len(states) != 4 + invocation:
                        pytest.fail("new arrivals did not advance durable intake")
            finally:
                await persistence.close()
        for key, expected in original.items():
            if tuple(seen[key][:4]) != (*expected, expected[0]):
                pytest.fail("restart or arrivals starved an original pending turn")
        expected_turns = []
        for kind, reference in turns:
            if kind == "attempt":
                expected_turns.extend((("select", reference), ("attempt", reference)))
        if turns != expected_turns:
            pytest.fail("each attempt needs its own immediately preceding selection")

    asyncio.run(check())


def test_new_intake_reserves_one_turn_before_exact_replay(
    saved_catalog, tmp_path, monkeypatch
):
    """Newly admitted work uses the same selector and accepted exact proof."""
    repeated_release(saved_catalog, "new")

    async def check():
        persistence, scope, handler, request = await context(
            saved_catalog, tmp_path, budget=1, entries=0
        )
        turns = []
        select = persistence.select_preparation_intake_worksets
        process = handler._process

        async def selected(value, *, limit):
            if limit != 1:
                pytest.fail("new work reserved an oversized selection")
            states = await select(value, limit=limit)
            turns.extend(("select", state.workset) for state in states)
            return states

        async def replay(reference, reader, request):
            turns.append(("attempt", reference))
            return await process(reference, reader, request)

        monkeypatch.setattr(persistence, "select_preparation_intake_worksets", selected)
        monkeypatch.setattr(handler, "_process", replay)
        try:
            await handler.run(request)
            states = await persistence.list_preparation_intake_worksets(
                scope, pending_only=False
            )
            if len(states) != 1 or not states[0].result_refs:
                pytest.fail("new work lost its exact accepted completion manifest")
            reference = states[0].workset
            if turns != [("select", reference), ("attempt", reference)]:
                pytest.fail("new intake bypassed durable scheduling selection")
            if await persistence.list_preparation_intake_worksets(scope):
                pytest.fail("accepted exact replay stayed pending")
        finally:
            await persistence.close()

    asyncio.run(check())
