"""Task 15: future-only bootstrap and restored-catalog cursor fences."""

import asyncio
import sqlite3
from dataclasses import replace

import pytest

from message_ingest.acquisition.handoff import source_state_key
from msgloom.preparation.records import PreparedSourceType
from msgloom.preparation_pipeline.intake import PreparationIntakeService
from msgloom.sources import ReleaseSourceReader, SavedSourceReaderConfig
from msgloom.sources.models import SourceReferenceError
from tests.preparation_intake_helpers import payload, release, run, setup
from tests.source_reader.conftest import saved_catalog as saved_catalog  # noqa: PLC0414
from tests.source_reader.release_nonmail_helpers import fact, publish


def test_populated_history_requires_new_release_before_future_only_intake(
    saved_catalog, tmp_path
):
    """Unreleased pre-ledger data cannot be silently admitted as new work."""

    async def check():
        reader, persistence, scope, service = await setup(saved_catalog, tmp_path)
        try:
            historical = await reader.list_versions(
                PreparedSourceType.TODO, source_id=scope.source_id, limit=10
            )
            if not any("todo-old" in value.version for value in historical):
                pytest.fail("Fixture does not contain readable pre-ledger history")
            if await reader.catalog.max_release_entry_seq(
                scope.source_id, scope.stream
            ):
                pytest.fail("Historical fixture unexpectedly has released work")

            if await run(service, scope, identity="future-only-initial") is not None:
                pytest.fail("Future-only intake emitted unreleased legacy history")
            initial_cursor = await persistence.get_preparation_intake_cursor(scope)
            if initial_cursor.last_release_entry_seq != 0:
                pytest.fail("Future-only no-work invocation advanced its cursor")
            if await persistence.list_preparation_intake_worksets(scope):
                pytest.fail("Unreleased history invented an immutable workset")

            published = release(saved_catalog)
            result = await run(service, scope, identity="future-first-release")
            workset = await payload(persistence, result)
            if (
                len(workset.entries) != 1
                or len(workset.selections) != 1
                or workset.held
                or workset.transitions
                or workset.entries[0].release_entry_seq != published
                or workset.previous != initial_cursor
            ):
                pytest.fail("A new release was not admitted exactly once")
            if await run(service, scope, identity="future-after-release") is not None:
                pytest.fail("Future-only replay re-admitted a consumed release")
            if len(await persistence.list_preparation_intake_worksets(scope)) != 1:
                pytest.fail("Repeated no-work invocation changed durable worksets")
        finally:
            await reader.close()
            await persistence.close()

    asyncio.run(check())


@pytest.mark.parametrize("backup_has_release", [False, True])
def test_restored_old_a1_backup_cannot_advance_existing_a2_cursor(
    saved_catalog, tmp_path, backup_has_release
):
    """Reject an older same-identity A1 snapshot, including empty release history."""
    backup = tmp_path / "old-a1-backup.sqlite3"

    def backup_catalog():
        with (
            sqlite3.connect(saved_catalog["database"]) as current,
            sqlite3.connect(backup) as saved,
        ):
            current.backup(saved)

    if not backup_has_release:
        backup_catalog()
    original = release(saved_catalog)
    if backup_has_release:
        backup_catalog()
    newer = replace(
        fact(
            "todo",
            "todo_task",
            '["list","task"]',
            "ev-todo-old",
            scope_kind="todo_list",
            scope_identity="list",
        ),
        run_id="second-acquisition",
        source_state_key=source_state_key({"revision": "second"}),
    )
    newer_sequence = publish(saved_catalog, [newer])
    if newer_sequence <= original:
        pytest.fail("Test did not publish a newer release after the backup")

    async def check():
        reader, persistence, scope, service = await setup(saved_catalog, tmp_path)
        older_reader = ReleaseSourceReader(
            SavedSourceReaderConfig(
                catalog_path=backup,
                evidence_roots=(saved_catalog["evidence_root"],),
            )
        )
        try:
            if await reader.catalog.catalog_identity() != (
                await older_reader.catalog.catalog_identity()
            ):
                pytest.fail("Backup did not preserve the original A1 catalog identity")
            backup_ceiling = await older_reader.catalog.max_release_entry_seq(
                scope.source_id, scope.stream
            )
            if backup_ceiling != (original if backup_has_release else 0):
                pytest.fail(
                    "A1 backup does not have the expected historic ledger cutoff"
                )
            result = await run(service, scope, identity="up-to-date")
            workset = await payload(persistence, result)
            cursor = await persistence.get_preparation_intake_cursor(scope)
            before_worksets = await persistence.list_preparation_intake_worksets(
                scope, pending_only=False
            )
            if (
                cursor.last_release_entry_seq != newer_sequence
                or len(workset.entries) != 2
                or len(before_worksets) != 1
            ):
                pytest.fail("Fixture did not commit an A2 cursor beyond the backup")
            older = PreparationIntakeService(persistence, older_reader)
            with pytest.raises(SourceReferenceError, match="anchor mismatch|behind"):
                await run(older, scope, identity="restored-old-backup")
            if await persistence.get_preparation_intake_cursor(scope) != cursor:
                pytest.fail("Restored catalog rewound A2's committed cursor")
            if (
                await persistence.list_preparation_intake_worksets(
                    scope, pending_only=False
                )
                != before_worksets
            ):
                pytest.fail("Rejected catalog restore modified A2 worksets")
        finally:
            await reader.close()
            await older_reader.close()
            await persistence.close()

    asyncio.run(check())
