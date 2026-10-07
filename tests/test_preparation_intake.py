"""Exercise finite cutoffs, exact selections, and stable stream cursors."""

import asyncio

import pytest

from tests.preparation_intake_helpers import payload, release, run, setup
from tests.source_reader.conftest import saved_catalog as saved_catalog  # noqa: PLC0414


def test_exact_selection_and_pending_workset(saved_catalog, tmp_path):
    seq = release(saved_catalog)

    async def check():
        reader, persistence, scope, service = await setup(saved_catalog, tmp_path)
        try:
            result = await run(service, scope)
            workset = await payload(persistence, result)
            if (
                len(workset.selections) != 1
                or workset.cutoff.last_release_entry_seq != seq
            ):
                pytest.fail("Intake lost the exact release selection")
            selection = await persistence.get_result(
                workset.selections[0].result.result_id
            )
            value = await payload(persistence, selection)
            if value.record.subject != "Old task":
                pytest.fail("Intake changed the released source")
            pending = await persistence.list_preparation_intake_worksets(scope)
            if len(pending) != 1 or pending[0].state != "pending":
                pytest.fail("Workset is not discoverable for later preparation")
            if (
                await run(service, scope, identity="two", code_version="code-2")
                is not None
            ):
                pytest.fail("Code change created a fresh cursor")
        finally:
            await reader.close()
            await persistence.close()

    asyncio.run(check())


def test_fixed_cutoff_excludes_concurrent_release(saved_catalog, tmp_path, monkeypatch):
    from dataclasses import replace

    from message_ingest.acquisition.handoff import source_state_key
    from tests.source_reader.release_nonmail_helpers import fact, publish

    first = release(saved_catalog)

    async def check():
        reader, persistence, scope, service = await setup(saved_catalog, tmp_path)
        original = reader.catalog.max_release_entry_seq

        async def capture(*args):
            cutoff = await original(*args)
            # A new run of equivalent state emits no entry. Publish a changed
            # state so the first cutoff must exclude a real later release.
            item = fact(
                "todo",
                "todo_task",
                '["list","task"]',
                "ev-todo-old",
                scope_kind="todo_list",
                scope_identity="list",
            )
            publish(
                saved_catalog,
                [
                    replace(
                        item,
                        run_id="run-later",
                        source_state_key=source_state_key({"revision": "later"}),
                    )
                ],
            )
            return cutoff

        monkeypatch.setattr(reader.catalog, "max_release_entry_seq", capture)
        try:
            workset = await payload(persistence, await run(service, scope))
            if (
                len(workset.entries) != 1
                or workset.cutoff.last_release_entry_seq != first
            ):
                pytest.fail("Concurrent A1 release escaped the fixed cutoff")
            monkeypatch.setattr(reader.catalog, "max_release_entry_seq", original)
            later = await reader.catalog.max_release_entry_seq(
                scope.source_id, scope.stream
            )
            next_workset = await payload(
                persistence, await run(service, scope, identity="next")
            )
            if (
                next_workset.previous != workset.cutoff
                or tuple(e.release_entry_seq for e in next_workset.entries) != (later,)
                or later <= first
                or next_workset.cutoff.last_release_entry_seq != later
            ):
                pytest.fail("Next intake lost or repeated the deferred release")
            if await run(service, scope, identity="empty") is not None:
                pytest.fail("Deferred release was admitted more than once")
            if (
                await persistence.get_preparation_intake_cursor(scope)
                != next_workset.cutoff
                or len(await persistence.list_preparation_intake_worksets(scope)) != 2
            ):
                pytest.fail("Deferred release lost its durable workset or cursor")
        finally:
            await reader.close()
            await persistence.close()

    asyncio.run(check())


def test_two_streams_keep_independent_cursors(saved_catalog, tmp_path):
    todo = release(saved_catalog)
    contacts = release(saved_catalog, stream="contacts")

    async def check():
        reader, persistence, scope, service = await setup(saved_catalog, tmp_path)
        try:
            await run(service, scope)
            other = scope.model_copy(update={"stream": "contacts"})
            if (
                await persistence.get_preparation_intake_cursor(other)
            ).last_release_entry_seq:
                pytest.fail("One stream advanced another stream cursor")
            value = await payload(
                persistence, await run(service, other, identity="contacts")
            )
            if value.cutoff.last_release_entry_seq != contacts:
                pytest.fail("Contacts stream was skipped")
            if (
                await persistence.get_preparation_intake_cursor(scope)
            ).last_release_entry_seq != todo:
                pytest.fail("Contacts intake changed To Do cursor")
            if (
                await run(
                    service, scope, identity="config", configuration_version="config-2"
                )
                is not None
            ):
                pytest.fail("Configuration change reset the stable cursor")
        finally:
            await reader.close()
            await persistence.close()

    asyncio.run(check())


@pytest.mark.parametrize(
    "reason,want",
    [
        ("snapshot_present", "presence"),
        ("snapshot_absent", "absence"),
        ("unknown", None),
    ],
)
def test_transition_mapping_is_explicit(saved_catalog, tmp_path, reason, want):
    from dataclasses import replace

    from message_ingest.acquisition.handoff import AcquisitionFactKind
    from tests.source_reader.release_nonmail_helpers import fact, publish

    item = replace(
        fact(
            "todo",
            "todo_task",
            '["list","task"]',
            "ev-todo-old",
            scope_kind="todo_source",
            scope_identity="synthetic-source",
        ),
        fact_kind=AcquisitionFactKind.SCOPED_STATE_TRANSITION,
        evidence_id=None,
        source_version_locator=None,
        transition_reason=reason,
    )
    publish(saved_catalog, [item], roles=("transition",), entry_kind="transition")

    async def check():
        reader, persistence, scope, service = await setup(saved_catalog, tmp_path)
        try:
            workset = await payload(persistence, await run(service, scope))
            if want is None:
                if not workset.held or workset.transitions:
                    pytest.fail("Unknown transition was assigned invented semantics")
            elif (
                len(workset.transitions) != 1
                or workset.transitions[0].transition_kind != want
            ):
                pytest.fail("Transition mapping changed exact authority semantics")
            if workset.selections:
                pytest.fail("Transition fabricated readable source bytes")
        finally:
            await reader.close()
            await persistence.close()

    asyncio.run(check())


def test_control_context_never_becomes_primary_selection(saved_catalog, tmp_path):
    from dataclasses import replace

    from message_ingest.acquisition.handoff import AcquisitionFactKind
    from tests.source_reader.release_nonmail_helpers import fact, publish, save_evidence

    save_evidence(saved_catalog, "context", {"id": "list", "displayName": "List"})
    item = replace(
        fact("todo", "todo_task_list", '["list"]', "context"),
        fact_kind=AcquisitionFactKind.CONTROL_CONTEXT,
    )
    publish(saved_catalog, [item], roles=("context",), entry_kind="context")

    async def check():
        reader, persistence, scope, service = await setup(saved_catalog, tmp_path)
        try:
            workset = await payload(persistence, await run(service, scope))
            if workset.selections or workset.held or len(workset.transitions) != 1:
                pytest.fail("Context was not admitted as a typed refresh")
            if workset.transitions[0].transition_kind != "context_refresh":
                pytest.fail("Context refresh lost its explicit semantic role")
        finally:
            await reader.close()
            await persistence.close()

    asyncio.run(check())


@pytest.mark.parametrize(
    "stream,resource,scope_kind,reason,want",
    [
        ("outlook_mail", "message", "mailbox", "reconciliation_seen", "presence"),
        ("outlook_mail", "mail_folder", "mail_folder", "inventory_present", "presence"),
        (
            "outlook_mail",
            "message",
            "mailbox",
            "not_in_complete_reconciliation",
            "absence",
        ),
        ("outlook_mail", "message", "mailbox", "not_in_complete_inventory", "absence"),
        (
            "outlook_mail",
            "message",
            "mail_folder",
            "folder_delta_removed",
            "membership_removal",
        ),
        ("contacts", "contact", "contacts_collection", "present", "presence"),
        (
            "contacts",
            "contact",
            "contacts_collection",
            "not_in_complete_snapshot",
            "absence",
        ),
        (
            "contacts",
            "contact",
            "contacts_collection",
            "not_in_complete_inventory",
            "absence",
        ),
        (
            "contacts",
            "contact",
            "contacts_collection",
            "delta_removed",
            "membership_removal",
        ),
        (
            "onedrive",
            "onedrive_item",
            "onedrive_source",
            "observed_present",
            "presence",
        ),
        (
            "onedrive",
            "onedrive_item",
            "onedrive_source",
            "provider_deleted",
            "deletion",
        ),
        ("onedrive", "onedrive_item", "onedrive_source", "resync_absent", "absence"),
        (
            "outlook_calendar",
            "calendar_event",
            "calendar_window",
            '{"kind":"present"}',
            "presence",
        ),
        (
            "outlook_calendar",
            "calendar_event",
            "calendar_window",
            '{"kind":"removed","removed_reason":"deleted"}',
            "membership_removal",
        ),
        (
            "outlook_calendar",
            "calendar_event",
            "calendar_window",
            '{"attempt":1,"kind":"rebaseline_absence","removed_reason":null}',
            "absence",
        ),
        (
            "outlook_calendar",
            "calendar_event",
            "calendar_window",
            '{"kind":"unknown"}',
            None,
        ),
        ("outlook_calendar", "calendar_event", "calendar_window", '{"kind":[]}', None),
    ],
)
def test_provider_transition_preserves_exact_scope(
    saved_catalog, tmp_path, stream, resource, scope_kind, reason, want
):
    from dataclasses import replace

    from message_ingest.acquisition.handoff import AcquisitionFactKind
    from tests.source_reader.release_nonmail_helpers import fact, publish

    item = replace(
        fact(
            stream,
            resource,
            "resource",
            "unused",
            scope_kind=scope_kind,
            scope_identity="exact-scope",
        ),
        fact_kind=AcquisitionFactKind.SCOPED_STATE_TRANSITION,
        source_version_locator=None,
        evidence_id=None,
        transition_reason=reason,
    )
    seq = publish(saved_catalog, [item], roles=("transition",), entry_kind="transition")

    async def check():
        reader, persistence, scope, service = await setup(
            saved_catalog, tmp_path, stream=stream
        )
        try:
            entry = await reader.catalog.get_release_entry(seq)
            if entry is None:
                pytest.fail("Fixture release is missing")
            facts = await reader.catalog.get_release_facts(entry.reference)
            value = await payload(persistence, await run(service, scope))
            if value.selections:
                pytest.fail("Transition invented primary evidence")
            if want is None:
                if len(value.held) != 1 or value.transitions:
                    pytest.fail("Unknown provider reason was not held")
                return
            if value.held or len(value.transitions) != 1:
                pytest.fail("Known provider transition was not admitted")
            transition = value.transitions[0]
            if (
                transition.transition_kind != want
                or transition.entry != entry.reference
                or transition.fact_id != facts[0].fact_id
                or transition.resource_kind != resource
                or transition.resource_identity != "resource"
                or transition.scope_kind != scope_kind
                or transition.scope_identity != "exact-scope"
            ):
                pytest.fail("Transition lost exact identity, scope, or classification")
        finally:
            await reader.close()
            await persistence.close()

    asyncio.run(check())


def test_large_group_drains_without_splitting_entry_dispositions(
    saved_catalog, tmp_path
):
    from tests.preparation_intake_helpers import large_transition_group

    large_transition_group(saved_catalog)

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
            if len(page.entries) != 9:
                pytest.fail("Fixture must expose all nine committed entries")
            expected = {
                (entry.release_entry_seq, fact_id)
                for entry in page.entries
                for fact_id, role in entry.facts
            }
            first = await payload(persistence, await run(service, scope))
            second = await payload(
                persistence, await run(service, scope, identity="next")
            )
            if len(first.entries) != 8 or len(first.transitions) != 1024:
                pytest.fail("First workset did not retain eight complete entries")
            if len(second.entries) != 1 or len(second.transitions) != 128:
                pytest.fail("Second workset lost the remaining complete entry")
            seen = [
                (item.entry.release_entry_seq, item.fact_id)
                for value in (first, second)
                for item in value.transitions
            ]
            if len(seen) != len(set(seen)) or set(seen) != expected:
                pytest.fail("Bounded drain lost or duplicated exact dispositions")
            if first.held or second.held or first.selections or second.selections:
                pytest.fail("Aggregate bound fabricated a different disposition")
            if second.previous != first.cutoff:
                pytest.fail("Bounded worksets broke cursor continuity")
            if await run(service, scope, identity="empty") is not None:
                pytest.fail("Drained group was admitted twice")
            if len(await persistence.list_preparation_intake_worksets(scope)) != 2:
                pytest.fail("Bounded worksets are not both durable")
        finally:
            await reader.close()
            await persistence.close()

    asyncio.run(check())
