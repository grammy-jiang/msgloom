"""Verify Calendar delta checkpoint scope and CAS promotion."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest
from sqlalchemy import create_engine, insert, inspect, select
from sqlalchemy.exc import DBAPIError

from message_ingest.catalog import Base, CalendarRecord, Catalog
from message_ingest.calendar_checkpoints import (
    CalendarDeltaCheckpointConflict,
    CalendarDeltaCheckpointStore,
)

START = "2026-10-01T00:00:00+00:00"
END = "2026-11-01T00:00:00+00:00"


def _url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'catalog.sqlite3'}"


def _store(
    tmp_path: Path,
    *,
    source_id: str = "source-1",
    start: str = START,
    end: str = END,
) -> CalendarDeltaCheckpointStore:
    return CalendarDeltaCheckpointStore(
        _url(tmp_path),
        source_id=source_id,
        start_datetime=start,
        end_datetime=end,
    )


def _candidate(
    store: CalendarDeltaCheckpointStore,
    *,
    run_id: str,
    attempt: int,
    base_revision: int | None,
    delta_link: str,
    evidence_id: str,
) -> None:
    store.write_candidate(
        run_id=run_id,
        attempt=attempt,
        base_revision=base_revision,
        delta_link=delta_link,
        evidence_id=evidence_id,
        observed_at="2026-10-02T00:00:00+00:00",
    )


def test_candidate_does_not_advance_committed_cursor(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        _candidate(
            store,
            run_id="run-1",
            attempt=0,
            base_revision=None,
            delta_link="https://graph.microsoft.com/delta/one",
            evidence_id="evidence-1",
        )
        if store.get_delta_link() is not None:
            pytest.fail("Expected pending candidate not to become resume state")
        candidate = store.load_candidate(run_id="run-1", attempt=0)
        if candidate is None or candidate.delta_link.endswith("/one") is False:
            pytest.fail("Expected durable Calendar candidate")
    finally:
        store.close()


def test_first_commit_creates_revision_one_and_is_idempotent(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        _candidate(
            store,
            run_id="run-1",
            attempt=0,
            base_revision=None,
            delta_link="https://graph.microsoft.com/delta/one",
            evidence_id="evidence-1",
        )
        state = store.commit(run_id="run-1", attempt=0)
        if state.revision != 1 or not state.delta_link.endswith("/one"):
            pytest.fail(f"Unexpected first checkpoint state: {state!r}")
        candidate = store.load_candidate(run_id="run-1", attempt=0)
        if candidate is None or candidate.committed_at is None:
            pytest.fail("Expected committed candidate timestamp")

        repeated = store.commit(run_id="run-1", attempt=0)
        if repeated != state:
            pytest.fail("Expected repeated idle promotion to be idempotent")
    finally:
        store.close()


def test_next_round_requires_current_revision_and_increments_it(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        _candidate(
            store,
            run_id="run-1",
            attempt=0,
            base_revision=None,
            delta_link="https://graph.microsoft.com/delta/one",
            evidence_id="evidence-1",
        )
        first = store.commit(run_id="run-1", attempt=0)
        _candidate(
            store,
            run_id="run-2",
            attempt=0,
            base_revision=first.revision,
            delta_link="https://graph.microsoft.com/delta/two",
            evidence_id="evidence-2",
        )
        second = store.commit(run_id="run-2", attempt=0)
        if second.revision != 2 or not second.delta_link.endswith("/two"):
            pytest.fail(f"Unexpected second checkpoint state: {second!r}")
    finally:
        store.close()


def test_stale_candidate_cannot_overwrite_newer_checkpoint(
    tmp_path: Path,
) -> None:
    first_store = _store(tmp_path)
    second_store = _store(tmp_path)
    try:
        _candidate(
            first_store,
            run_id="run-a",
            attempt=0,
            base_revision=None,
            delta_link="https://graph.microsoft.com/delta/a",
            evidence_id="evidence-a",
        )
        _candidate(
            second_store,
            run_id="run-b",
            attempt=0,
            base_revision=None,
            delta_link="https://graph.microsoft.com/delta/b",
            evidence_id="evidence-b",
        )
        first_store.commit(run_id="run-a", attempt=0)
        with pytest.raises(CalendarDeltaCheckpointConflict, match="revision"):
            second_store.commit(run_id="run-b", attempt=0)
        state = second_store.get_checkpoint()
        if state is None or not state.delta_link.endswith("/a"):
            pytest.fail("Expected stale promotion to leave committed cursor intact")
    finally:
        first_store.close()
        second_store.close()


def test_checkpoint_isolated_by_source_and_exact_window(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        _candidate(
            store,
            run_id="run-1",
            attempt=0,
            base_revision=None,
            delta_link="https://graph.microsoft.com/delta/one",
            evidence_id="evidence-1",
        )
        store.commit(run_id="run-1", attempt=0)
    finally:
        store.close()

    other_source = _store(tmp_path, source_id="source-2")
    other_window = _store(
        tmp_path,
        end="2026-12-01T00:00:00+00:00",
    )
    try:
        if other_source.get_checkpoint() is not None:
            pytest.fail("Expected source-scoped Calendar delta checkpoint")
        if other_window.get_checkpoint() is not None:
            pytest.fail("Expected exact-window Calendar delta checkpoint")
    finally:
        other_source.close()
        other_window.close()


def test_replacing_uncommitted_candidate_keeps_same_attempt_identity(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        _candidate(
            store,
            run_id="run-1",
            attempt=0,
            base_revision=None,
            delta_link="https://graph.microsoft.com/delta/old",
            evidence_id="evidence-old",
        )
        _candidate(
            store,
            run_id="run-1",
            attempt=0,
            base_revision=None,
            delta_link="https://graph.microsoft.com/delta/new",
            evidence_id="evidence-new",
        )
        candidate = store.load_candidate(run_id="run-1", attempt=0)
        if candidate is None or not candidate.delta_link.endswith("/new"):
            pytest.fail("Expected latest terminal cursor for same attempt")
        state = store.commit(run_id="run-1", attempt=0)
        if not state.delta_link.endswith("/new"):
            pytest.fail("Expected promotion of replacement candidate")
    finally:
        store.close()


@pytest.mark.parametrize(
    ("attempt", "base_revision", "evidence_id", "match"),
    [
        (-1, None, "evidence", "attempt"),
        (0, 0, "evidence", "base_revision"),
        (0, None, "", "evidence_id"),
    ],
)
def test_invalid_candidate_state_is_rejected_before_write(
    tmp_path: Path,
    attempt: int,
    base_revision: int | None,
    evidence_id: str,
    match: str,
) -> None:
    store = _store(tmp_path)
    try:
        with pytest.raises(ValueError, match=match):
            store.write_candidate(
                run_id="run-1",
                attempt=attempt,
                base_revision=base_revision,
                delta_link="https://graph.microsoft.com/delta/one",
                evidence_id=evidence_id,
                observed_at="2026-10-02T00:00:00+00:00",
            )
        if store.load_candidate(run_id="run-1", attempt=max(attempt, 0)) is not None:
            pytest.fail("Expected invalid candidate not to be persisted")
    finally:
        store.close()


def test_candidate_survives_catalog_reopen(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _candidate(
        store,
        run_id="run-reopen",
        attempt=0,
        base_revision=None,
        delta_link="https://graph.microsoft.com/delta/reopen",
        evidence_id="evidence-reopen",
    )
    store.close()

    reopened = _store(tmp_path)
    try:
        candidate = reopened.load_candidate(
            run_id="run-reopen",
            attempt=0,
        )
        if candidate is None:
            pytest.fail("Expected pending Calendar candidate after reopen")
        if not candidate.delta_link.endswith("/reopen"):
            pytest.fail("Expected reopened candidate to retain opaque cursor")
        if reopened.get_checkpoint() is not None:
            pytest.fail("Expected reopened candidate not to advance checkpoint")
    finally:
        reopened.close()


def test_promotion_failure_rolls_back_checkpoint_and_candidate_marker(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    engine = create_engine(
        _url(tmp_path),
        connect_args={"autocommit": True},
    )
    try:
        _candidate(
            store,
            run_id="run-failure",
            attempt=0,
            base_revision=None,
            delta_link="https://graph.microsoft.com/delta/failure",
            evidence_id="evidence-failure",
        )
        with engine.connect() as connection:
            connection.exec_driver_sql(
                """
                CREATE TRIGGER fail_calendar_candidate_commit
                BEFORE UPDATE OF committed_at
                ON calendar_delta_checkpoint_candidates
                BEGIN
                    SELECT RAISE(ABORT, 'injected promotion failure');
                END
                """
            )

        with pytest.raises(DBAPIError, match="injected promotion failure"):
            store.commit(run_id="run-failure", attempt=0)

        if store.get_checkpoint() is not None:
            pytest.fail("Expected failed promotion to roll back checkpoint")
        candidate = store.load_candidate(
            run_id="run-failure",
            attempt=0,
        )
        if candidate is None or candidate.committed_at is not None:
            pytest.fail("Expected failed promotion to retain pending candidate")

        with engine.connect() as connection:
            connection.exec_driver_sql(
                "DROP TRIGGER fail_calendar_candidate_commit"
            )
        state = store.commit(run_id="run-failure", attempt=0)
        if state.revision != 1:
            pytest.fail("Expected promotion to succeed after rollback recovery")
    finally:
        engine.dispose()
        store.close()


def test_concurrent_promotions_allow_one_revision_advance(
    tmp_path: Path,
) -> None:
    bootstrap = _store(tmp_path)
    try:
        _candidate(
            bootstrap,
            run_id="run-base",
            attempt=0,
            base_revision=None,
            delta_link="https://graph.microsoft.com/delta/base",
            evidence_id="evidence-base",
        )
        first = bootstrap.commit(run_id="run-base", attempt=0)
    finally:
        bootstrap.close()

    left = _store(tmp_path)
    right = _store(tmp_path)
    try:
        _candidate(
            left,
            run_id="run-left",
            attempt=0,
            base_revision=first.revision,
            delta_link="https://graph.microsoft.com/delta/left",
            evidence_id="evidence-left",
        )
        _candidate(
            right,
            run_id="run-right",
            attempt=0,
            base_revision=first.revision,
            delta_link="https://graph.microsoft.com/delta/right",
            evidence_id="evidence-right",
        )
        barrier = Barrier(2)

        def promote(
            pair: tuple[CalendarDeltaCheckpointStore, str],
        ) -> str:
            store, run_id = pair
            barrier.wait()
            try:
                return str(
                    store.commit(
                        run_id=run_id,
                        attempt=0,
                    ).revision
                )
            except CalendarDeltaCheckpointConflict:
                return "conflict"

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(
                executor.map(
                    promote,
                    (
                        (left, "run-left"),
                        (right, "run-right"),
                    ),
                )
            )
        if sorted(outcomes) != ["2", "conflict"]:
            pytest.fail(f"Expected one CAS winner and one conflict: {outcomes!r}")

        state = left.get_checkpoint()
        if state is None or state.revision != 2:
            pytest.fail("Expected exactly one committed revision advance")
    finally:
        left.close()
        right.close()


def test_opening_previous_schema_adds_calendar_delta_tables_only(
    tmp_path: Path,
) -> None:
    url = _url(tmp_path)
    delta_tables = {
        "calendar_delta_checkpoints",
        "calendar_delta_checkpoint_candidates",
        "calendar_delta_observations",
    }
    previous_tables = [
        table
        for table in Base.metadata.sorted_tables
        if table.name not in delta_tables
    ]
    engine = create_engine(url)
    try:
        Base.metadata.create_all(engine, tables=previous_tables)
        with engine.begin() as connection:
            connection.execute(
                insert(CalendarRecord).values(
                    source_id="legacy-source",
                    calendar_id="calendar-legacy",
                    latest_observed_at="2026-09-27T00:00:00+00:00",
                    raw={"id": "calendar-legacy", "name": "Legacy"},
                )
            )
    finally:
        engine.dispose()

    catalog = Catalog(url)
    try:
        if set(inspect(catalog.engine).get_table_names()) != set(
            Base.metadata.tables
        ):
            pytest.fail("Expected additive Calendar delta schema initialization")
        with catalog.Session() as session:
            row = session.scalar(
                select(CalendarRecord).filter_by(
                    source_id="legacy-source",
                    calendar_id="calendar-legacy",
                )
            )
            if row is None or row.raw.get("name") != "Legacy":
                pytest.fail("Expected previous Calendar data to remain unchanged")
    finally:
        catalog.close()
