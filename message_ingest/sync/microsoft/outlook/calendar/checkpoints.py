"""Persist Calendar delta candidates and promote one fixed window atomically."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast

from sqlalchemy import Table, create_engine, insert, select, update
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from message_ingest.catalog import (
    CalendarDeltaCheckpoint,
    CalendarDeltaCheckpointCandidate,
    Catalog,
)
from message_ingest.extensions.catalog import CatalogService

from .state import apply_calendar_delta_state


class CalendarDeltaCheckpointConflict(RuntimeError):
    """A candidate was based on an obsolete committed Calendar revision."""


@dataclass(frozen=True, slots=True)
class CalendarDeltaCheckpointState:
    """Detached committed state for one fixed Calendar delta window."""

    delta_link: str
    revision: int
    run_id: str
    attempt: int
    committed_at: str


@dataclass(frozen=True, slots=True)
class CalendarDeltaCandidateState:
    """Detached pending state for one Calendar delta attempt."""

    run_id: str
    attempt: int
    base_revision: int | None
    delta_link: str
    evidence_id: str
    observed_at: str
    committed_at: str | None


class CalendarDeltaCheckpointStore:
    """Own checkpoint state for one source and one exact Calendar window."""

    def __init__(
        self,
        catalog_or_url: Catalog | str,
        *,
        source_id: str,
        start_datetime: str,
        end_datetime: str,
        calendar_scope: str = "default",
    ) -> None:
        """Bind this store instance to one immutable synchronization scope."""
        self._owns_catalog = isinstance(catalog_or_url, str)
        self.catalog = (
            Catalog(catalog_or_url)
            if isinstance(catalog_or_url, str)
            else catalog_or_url
        )
        self.source_id = self._scope_value(source_id, "source_id")
        self.calendar_scope = self._scope_value(calendar_scope, "calendar_scope")
        self.start_datetime = self._scope_value(start_datetime, "start_datetime")
        self.end_datetime = self._scope_value(end_datetime, "end_datetime")

    @classmethod
    def from_crawler(
        cls,
        crawler,
        *,
        start_datetime: str,
        end_datetime: str,
        calendar_scope: str = "default",
    ):
        """Borrow the crawler-owned catalog for one Calendar delta scope."""
        return cls(
            CatalogService.from_crawler(crawler).catalog,
            source_id=crawler.settings["MSGLOOM_SOURCE_ID"],
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            calendar_scope=calendar_scope,
        )

    def close(self) -> None:
        """Release only a standalone catalog created by this store."""
        if self._owns_catalog:
            self.catalog.close()

    def get_checkpoint(self) -> CalendarDeltaCheckpointState | None:
        """Read committed state; candidates are never resume points."""
        with self.catalog.Session() as session:
            row = session.scalar(
                select(CalendarDeltaCheckpoint).filter_by(**self._scope())
            )
            if row is None:
                return None
            return self._checkpoint_state(row)

    def get_delta_link(self) -> str | None:
        """Return only the committed cursor for this exact scope."""
        state = self.get_checkpoint()
        return state.delta_link if state is not None else None

    def write_candidate(
        self,
        *,
        run_id: str,
        attempt: int,
        base_revision: int | None,
        delta_link: str,
        evidence_id: str,
        observed_at: str,
    ) -> None:
        """Stage a terminal cursor without advancing committed state."""
        self._validate_candidate(
            run_id=run_id,
            attempt=attempt,
            base_revision=base_revision,
            delta_link=delta_link,
            evidence_id=evidence_id,
            observed_at=observed_at,
        )
        with self.catalog.Session() as session, session.begin():
            record = session.scalar(
                select(CalendarDeltaCheckpointCandidate).filter_by(
                    **self._scope(),
                    run_id=run_id,
                    attempt=attempt,
                )
            )
            if record is None:
                session.add(
                    CalendarDeltaCheckpointCandidate(
                        **self._scope(),
                        run_id=run_id,
                        attempt=attempt,
                        base_revision=base_revision,
                        delta_link=delta_link,
                        evidence_id=evidence_id,
                        observed_at=observed_at,
                        committed_at=None,
                    )
                )
                return
            if record.committed_at is not None:
                raise CalendarDeltaCheckpointConflict(
                    "Cannot replace an already committed Calendar candidate"
                )
            record.base_revision = base_revision
            record.delta_link = delta_link
            record.evidence_id = evidence_id
            record.observed_at = observed_at

    def load_candidate(
        self,
        *,
        run_id: str,
        attempt: int,
    ) -> CalendarDeltaCandidateState | None:
        """Load one attempt candidate for idle-time completion validation."""
        with self.catalog.Session() as session:
            row = session.scalar(
                select(CalendarDeltaCheckpointCandidate).filter_by(
                    **self._scope(),
                    run_id=run_id,
                    attempt=attempt,
                )
            )
            if row is None:
                return None
            return self._candidate_state(row)

    def commit(
        self,
        *,
        run_id: str,
        attempt: int,
    ) -> CalendarDeltaCheckpointState:
        """
        Promote one candidate under a SQLite writer lock and revision CAS.

        The caller owns lifecycle correctness: before calling this method it
        must prove that traversal reached its terminal delta link and that all
        required evidence and semantic writes completed successfully. After
        revision CAS succeeds, this same transaction materializes the winning
        attempt's fixed-window membership before advancing the candidate marker.
        """
        checkpoint_table = cast(Table, CalendarDeltaCheckpoint.__table__)
        candidate_table = cast(Table, CalendarDeltaCheckpointCandidate.__table__)
        committed_at = datetime.now(UTC).isoformat()
        scope = self._scope()

        with self._promotion_connection() as connection:
            candidate = (
                connection.execute(
                    select(candidate_table).filter_by(
                        **scope,
                        run_id=run_id,
                        attempt=attempt,
                    )
                )
                .mappings()
                .one_or_none()
            )
            if candidate is None:
                raise LookupError(
                    "Calendar delta candidate is missing for this attempt"
                )

            current = (
                connection.execute(select(checkpoint_table).filter_by(**scope))
                .mappings()
                .one_or_none()
            )

            if candidate["committed_at"] is not None:
                return self._idempotent_committed_state(
                    current=current,
                    candidate=candidate,
                )

            base_revision = candidate["base_revision"]
            if current is None:
                if base_revision is not None:
                    raise CalendarDeltaCheckpointConflict(
                        "First Calendar checkpoint requires base_revision=None"
                    )
                revision = 1
                connection.execute(
                    insert(checkpoint_table).values(
                        **scope,
                        delta_link=candidate["delta_link"],
                        revision=revision,
                        run_id=run_id,
                        attempt=attempt,
                        committed_at=committed_at,
                    )
                )
            else:
                if base_revision != current["revision"]:
                    raise CalendarDeltaCheckpointConflict(
                        "Calendar checkpoint revision changed before promotion"
                    )
                revision = int(current["revision"]) + 1
                connection.execute(
                    update(checkpoint_table)
                    .where(checkpoint_table.c.id == current["id"])
                    .values(
                        delta_link=candidate["delta_link"],
                        revision=revision,
                        run_id=run_id,
                        attempt=attempt,
                        committed_at=committed_at,
                    )
                )

            apply_calendar_delta_state(
                connection,
                scope=scope,
                run_id=run_id,
                attempt=attempt,
                revision=revision,
                rebaseline=(base_revision is None or int(candidate["attempt"]) > 0),
            )

            connection.execute(
                update(candidate_table)
                .where(candidate_table.c.id == candidate["id"])
                .values(committed_at=committed_at)
            )
            return CalendarDeltaCheckpointState(
                delta_link=str(candidate["delta_link"]),
                revision=revision,
                run_id=run_id,
                attempt=attempt,
                committed_at=committed_at,
            )

    @contextmanager
    def _promotion_connection(self):
        """Yield a connection with the strongest useful SQLite writer lock."""
        url = make_url(self.catalog.database_url)
        database = url.database
        in_memory = not database or database == ":memory:"
        if in_memory:
            with self.catalog.engine.begin() as connection:
                yield connection
            return

        engine = create_engine(
            self.catalog.database_url,
            connect_args={"autocommit": True, "timeout": 30.0},
            poolclass=NullPool,
        )
        try:
            with engine.connect() as connection:
                connection.exec_driver_sql("BEGIN IMMEDIATE")
                try:
                    yield connection
                    connection.exec_driver_sql("COMMIT")
                except BaseException:
                    connection.exec_driver_sql("ROLLBACK")
                    raise
        finally:
            engine.dispose()

    def _idempotent_committed_state(
        self,
        *,
        current,
        candidate,
    ) -> CalendarDeltaCheckpointState:
        """Allow repeated idle handling only for the exact committed attempt."""
        if (
            current is None
            or current["run_id"] != candidate["run_id"]
            or current["attempt"] != candidate["attempt"]
            or current["delta_link"] != candidate["delta_link"]
        ):
            raise CalendarDeltaCheckpointConflict(
                "Committed candidate no longer matches Calendar checkpoint"
            )
        return CalendarDeltaCheckpointState(
            delta_link=str(current["delta_link"]),
            revision=int(current["revision"]),
            run_id=str(current["run_id"]),
            attempt=int(current["attempt"]),
            committed_at=str(current["committed_at"]),
        )

    def _scope(self) -> dict[str, str]:
        """Return the exact database identity for this Calendar window."""
        return {
            "source_id": self.source_id,
            "calendar_scope": self.calendar_scope,
            "start_datetime": self.start_datetime,
            "end_datetime": self.end_datetime,
        }

    @staticmethod
    def _scope_value(value: str, name: str) -> str:
        """Reject ambiguous scope strings without normalizing them."""
        if not isinstance(value, str):
            raise TypeError(f"{name} must be a string")
        if not value or value != value.strip():
            raise ValueError(f"{name} must be non-empty without whitespace")
        return value

    @staticmethod
    def _validate_candidate(
        *,
        run_id: str,
        attempt: int,
        base_revision: int | None,
        delta_link: str,
        evidence_id: str,
        observed_at: str,
    ) -> None:
        """Reject malformed pending state before any transaction is opened."""
        for name, value in (
            ("run_id", run_id),
            ("delta_link", delta_link),
            ("evidence_id", evidence_id),
            ("observed_at", observed_at),
        ):
            if not isinstance(value, str) or not value:
                raise ValueError(f"{name} must be a non-empty string")
        if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt < 0:
            raise ValueError("attempt must be an integer >= 0")
        if base_revision is not None and (
            isinstance(base_revision, bool)
            or not isinstance(base_revision, int)
            or base_revision <= 0
        ):
            raise ValueError("base_revision must be a positive integer or None")

    @staticmethod
    def _checkpoint_state(row: CalendarDeltaCheckpoint) -> CalendarDeltaCheckpointState:
        """Detach committed ORM state from its session."""
        return CalendarDeltaCheckpointState(
            delta_link=row.delta_link,
            revision=row.revision,
            run_id=row.run_id,
            attempt=row.attempt,
            committed_at=row.committed_at,
        )

    @staticmethod
    def _candidate_state(
        row: CalendarDeltaCheckpointCandidate,
    ) -> CalendarDeltaCandidateState:
        """Detach pending ORM state from its session."""
        return CalendarDeltaCandidateState(
            run_id=row.run_id,
            attempt=row.attempt,
            base_revision=row.base_revision,
            delta_link=row.delta_link,
            evidence_id=row.evidence_id,
            observed_at=row.observed_at,
            committed_at=row.committed_at,
        )
