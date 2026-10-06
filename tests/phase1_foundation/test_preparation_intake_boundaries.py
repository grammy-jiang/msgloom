"""Writer timing, bounded paging, and durable processing dependencies."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest
from sqlalchemy import event

from msgloom.contracts import ResultRef, TerminalStatus
from msgloom.persistence import DependencyNotReadyError, StaleClaimError


def test_saved_selection_payload_is_read_before_final_writer_transaction(tmp_path):
    from tests.phase1_foundation import intake_helpers as h

    store = h.store(tmp_path / "neutral.db")
    value = h.workset(selected=True)
    token = h.claim(store, value)
    h.selection(store, token)
    saved = h.result(store, value, token)
    payload_reads = []

    def inspect_read(connection, _cursor, statement, _params, _context, _many):
        if (
            statement.startswith("SELECT")
            and "phase1_semantic_data.payload" in statement
            and "data-selection" in _params
        ):
            raw = connection.connection.driver_connection
            payload_reads.append(raw.in_transaction)

    event.listen(store.engine, "before_cursor_execute", inspect_read)
    try:
        store.finalize_preparation_intake(saved, value, claim=token)
        if not payload_reads or any(payload_reads):
            pytest.fail("Selection bytes were not validated before writer ownership")
    finally:
        event.remove(store.engine, "before_cursor_execute", inspect_read)
        store.close()


def test_same_claim_concurrent_finalizers_have_one_atomic_winner(tmp_path):
    from tests.phase1_foundation import intake_helpers as h

    path = tmp_path / "neutral.db"
    stores = (h.store(path), h.store(path))
    value = h.workset()
    token = h.claim(stores[0], value)

    def finalize(index):
        try:
            stores[index].finalize_preparation_intake(
                h.result(stores[index], value, token, f"workset-{index}"),
                value,
                claim=token,
            )
            return "committed"
        except StaleClaimError:
            return "stale"

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            observed = sorted(executor.map(finalize, (0, 1)))
        if observed != ["committed", "stale"]:
            pytest.fail("Concurrent finalization did not have exactly one winner")
        if len(stores[0].list_preparation_intake_worksets(value.scope)) != 1:
            pytest.fail("Concurrent finalization lost or duplicated pending work")
    finally:
        for store in stores:
            store.close()


def test_pending_and_held_indexes_are_bounded_and_paged(tmp_path):
    from tests.phase1_foundation import intake_helpers as h

    store = h.store(tmp_path / "neutral.db")
    first = h.workset(seq=7)
    second = h.workset(previous=first.cutoff, seq=11)
    token = h.claim(store, first)
    try:
        for value in (first, second):
            saved = h.result(
                store, value, token, f"workset-{value.cutoff.last_release_entry_seq}"
            )
            store.finalize_preparation_intake(saved, value, claim=token)
        page = store.list_preparation_intake_worksets(first.scope, limit=1)
        following = store.list_preparation_intake_worksets(
            first.scope,
            after_seq=page[0].cutoff.last_release_entry_seq,
            limit=1,
        )
        if [row.cutoff.last_release_entry_seq for row in (*page, *following)] != [
            7,
            11,
        ]:
            pytest.fail("Pending pagination lost monotonic admission order")
        held = store.list_preparation_intake_held_entries(
            first.scope, after_seq=7, limit=1
        )
        if len(held) != 1 or held[0].disposition.entry.release_entry_seq != 11:
            pytest.fail("Held pagination ignored its bounded cursor")
        for limit in (0, 1025, True):
            with pytest.raises(ValueError):
                store.list_preparation_intake_worksets(first.scope, limit=limit)
            with pytest.raises(ValueError):
                store.list_preparation_intake_held_entries(first.scope, limit=limit)
    finally:
        store.close()


def test_terminal_requires_output_for_readable_workset(tmp_path):
    from tests.phase1_foundation import intake_helpers as h

    store = h.store(tmp_path / "neutral.db")
    value = h.workset(selected=True)
    token = h.claim(store, value)
    h.selection(store, token)
    saved = h.result(store, value, token)
    store.finalize_preparation_intake(saved, value, claim=token)
    owner = h.processing_claim(store, saved)
    try:
        with pytest.raises(ValueError, match="output"):
            store.finalize_preparation_intake_workset(
                saved.result_id,
                TerminalStatus.COMPLETE,
                (),
                claim=owner,
            )
        if not store.list_preparation_intake_worksets(value.scope):
            pytest.fail("Readable inputs were completed without output references")
    finally:
        store.close()


def test_terminal_output_references_are_bounded_before_database_work(tmp_path):
    from tests.phase1_foundation import intake_helpers as h

    store = h.store(tmp_path / "neutral.db")
    value = h.workset()
    token = h.claim(store, value)
    saved = h.result(store, value, token)
    store.finalize_preparation_intake(saved, value, claim=token)
    owner = h.processing_claim(store, saved)
    try:
        with pytest.raises(ValueError, match="bounded"):
            store.finalize_preparation_intake_workset(
                saved.result_id,
                TerminalStatus.COMPLETE,
                (ResultRef("x" * 2049, "test_output", "1"),),
                claim=owner,
            )
    finally:
        store.close()


@pytest.mark.parametrize("invalid", ["missing", "foreign_execution", "unacceptable"])
def test_terminal_rejects_unproven_output_references(tmp_path, invalid):
    from tests.phase1_foundation import intake_helpers as h

    store = h.store(tmp_path / "neutral.db")
    value = h.workset()
    token = h.claim(store, value)
    saved = h.result(store, value, token)
    store.finalize_preparation_intake(saved, value, claim=token)
    owner = h.processing_claim(store, saved)
    ref = ResultRef("missing", "test_output", "1")
    if invalid != "missing":
        output = replace(
            saved,
            result_id="output",
            kind="test_output",
            semantic_data_ref=None,
            acceptable=invalid != "unacceptable",
            execution=token.execution
            if invalid == "foreign_execution"
            else owner.execution,
        )
        store.append_result(output)
        ref = ResultRef("output", "test_output", "1")
    try:
        with pytest.raises((DependencyNotReadyError, StaleClaimError)):
            store.finalize_preparation_intake_workset(
                saved.result_id,
                TerminalStatus.COMPLETE,
                (ref,),
                claim=owner,
            )
        if not store.list_preparation_intake_worksets(value.scope):
            pytest.fail("Unproven outputs consumed pending work")
    finally:
        store.close()
