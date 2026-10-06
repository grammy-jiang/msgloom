"""Real ledger regressions for encoded intake and expanded selection bounds."""

import asyncio
from itertools import pairwise

import pytest

from msgloom.preparation_pipeline.intake_codec import PreparationIntakeWorksetCodec
from tests.preparation_intake_helpers import (
    large_transition_group,
    payload,
    run,
    setup,
)
from tests.source_reader.conftest import saved_catalog as saved_catalog  # noqa: PLC0414


@pytest.mark.parametrize("single", [False, True])
def test_encoded_bound_drains_complete_entries(saved_catalog, tmp_path, single):
    # Three escaped identity fields exceed 4 MiB within a single valid entry.
    # One escaped field exceeds the aggregate bound before 1,024 transitions.
    large_transition_group(
        saved_catalog,
        entry_count=1 if single else 4,
        identity_pad="\x01" * 2000,
        scope_kind="k" + "\x01" * 2000 if single else "contacts_collection",
        scope_identity="s" + "\x01" * 2000 if single else "default",
    )

    async def check():
        reader, persistence, scope, service = await setup(
            saved_catalog, tmp_path, stream="contacts"
        )
        try:
            page = await reader.catalog.list_release_entries(
                scope.source_id,
                scope.stream,
                through_seq=await reader.catalog.max_release_entry_seq(
                    scope.source_id, scope.stream
                ),
            )
            # Demand actual reader materialization, not its held-error fallback.
            for entry in page.entries:
                released = await reader.read_entry(entry.reference)
                if len(released.transitions) != 128:
                    pytest.fail("Fixture did not materialize 128 exact transitions")
            worksets = []
            for index in range(5):
                result = await run(service, scope, identity=f"cut-{index}")
                if result is None:
                    break
                value = await payload(persistence, result)
                PreparationIntakeWorksetCodec().encode(value)
                worksets.append(value)
            else:
                pytest.fail("Bounded intake did not terminate")
            refs = [entry for value in worksets for entry in value.entries]
            if refs != [entry.reference for entry in page.entries]:
                pytest.fail("Encoded bound lost, duplicated, or reordered entries")
            for first, second in pairwise(worksets):
                if first.cutoff != second.previous:
                    pytest.fail("Encoded cuts broke cursor continuity")
            if single:
                if len(worksets) != 1 or worksets[0].transitions:
                    pytest.fail("Unrepresentable entry was not held whole")
                if [item.reason for item in worksets[0].held] != ["byte_limit"]:
                    pytest.fail("Unrepresentable entry lacks typed held reason")
            else:
                if len(worksets) != 2 or any(value.held for value in worksets):
                    pytest.fail("Representable aggregate was not split into cuts")
                seen = [
                    (item.entry, item.fact_id)
                    for value in worksets
                    for item in value.transitions
                ]
                expected = [
                    (entry.reference, fact_id)
                    for entry in page.entries
                    for fact_id, _ in entry.facts
                ]
                if seen != expected:
                    pytest.fail("Encoded cuts changed exact transition identities")
            if len(await persistence.list_preparation_intake_worksets(scope)) != len(
                worksets
            ):
                pytest.fail("Worksets were not durably indexed")
        finally:
            await reader.close()
            await persistence.close()

    asyncio.run(check())


def test_selection_count_drains_whole_component_entries(saved_catalog, tmp_path):
    large_transition_group(saved_catalog, selections=True)

    async def check():
        reader, persistence, scope, service = await setup(
            saved_catalog, tmp_path, stream="outlook_calendar"
        )
        try:
            first = await payload(persistence, await run(service, scope))
            second = await payload(
                persistence, await run(service, scope, identity="next")
            )
            if (len(first.entries), len(first.selections)) != (8, 1024):
                pytest.fail("First selection cut did not retain eight whole entries")
            if (len(second.entries), len(second.selections)) != (1, 128):
                pytest.fail("Second selection cut lost the last whole entry")
            if first.held or second.held or first.transitions or second.transitions:
                pytest.fail("Selection bound invented another disposition")
            seen = []
            for value in (first, second):
                for selection in value.selections:
                    result = await persistence.get_result(selection.result.result_id)
                    item = await payload(persistence, result)
                    seen.append(item.source.identity)
            if len(set(seen)) != 1152 or second.previous != first.cutoff:
                pytest.fail("Selection cuts lost exact identities or cursor continuity")
            if await run(service, scope, identity="empty") is not None:
                pytest.fail("Selection cuts did not fully drain")
        finally:
            await reader.close()
            await persistence.close()

    asyncio.run(check())
