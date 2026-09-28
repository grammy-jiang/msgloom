"""Calendar enrichment and orchestration planning queries."""

from __future__ import annotations

from datetime import datetime
from typing import TypedDict

from sqlalchemy import select

from message_ingest.catalog.models.microsoft.outlook.calendar import (
    CalendarDeltaEventState,
    CalendarEventAttachmentRecord,
    CalendarEventRecord,
    CalendarEventSighting,
    CalendarEventSurface,
    CalendarRecord,
    CalendarSeriesTopologyRecord,
)


class CalendarSurfaceState(TypedDict):
    status: str
    evidence_id: str | None
    observed_at: str
    profile_version: str | None
    resource_version: str | None


class CalendarEventPlanningState(TypedDict):
    event_id: str
    calendar_id: str
    resource_version: str | None
    event_type: str | None
    series_master_id: str | None
    latest_observed_at: str


class CalendarAttachmentPlanningState(TypedDict):
    attachment_id: str
    attachment_type: str | None
    calendar_id: str
    latest_observed_at: str
    latest_evidence_id: str | None


class CalendarPlanningStore:
    """Own detached Calendar completeness and workflow planning state."""

    def __init__(self, catalog, *, source_id: str) -> None:
        self.catalog = catalog
        self.source_id = source_id

    @classmethod
    def _is_older_capture(cls, incoming: str, current: str) -> bool:
        return cls._capture_time(incoming) < cls._capture_time(current)

    @staticmethod
    def _capture_time(value: str) -> datetime:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("Calendar observed_at must include a timezone offset")
        return parsed

    def set_event_surface(
        self,
        *,
        event_id: str,
        surface: str,
        status: str,
        evidence_id: str | None,
        observed_at: str,
        profile_version: str | None = None,
        resource_version: str | None = None,
    ) -> None:
        """Upsert one event surface without letting older evidence replace it."""
        with self.catalog.Session() as session, session.begin():
            record = session.scalar(
                select(CalendarEventSurface).filter_by(
                    source_id=self.source_id,
                    event_id=event_id,
                    surface=surface,
                )
            )
            if record is None:
                session.add(
                    CalendarEventSurface(
                        source_id=self.source_id,
                        event_id=event_id,
                        surface=surface,
                        status=status,
                        evidence_id=evidence_id,
                        observed_at=observed_at,
                        profile_version=profile_version,
                        resource_version=resource_version,
                    )
                )
                return
            if self._is_older_capture(observed_at, record.observed_at):
                return
            record.status = status
            record.evidence_id = evidence_id
            record.observed_at = observed_at
            record.profile_version = profile_version
            record.resource_version = resource_version

    def get_event_state(self, *, event_id: str) -> CalendarEventPlanningState | None:
        """Return the current event version and calendar for acquisition planning."""
        with self.catalog.Session() as session:
            row = session.scalar(
                select(CalendarEventRecord).filter_by(
                    source_id=self.source_id,
                    event_id=event_id,
                )
            )
            if row is None:
                return None
            return {
                "event_id": row.event_id,
                "calendar_id": row.calendar_id,
                "resource_version": row.change_key,
                "event_type": row.event_type,
                "series_master_id": row.series_master_id,
                "latest_observed_at": row.latest_observed_at,
            }

    def series_topology_covers(
        self,
        *,
        series_master_id: str,
        observed_at: str,
    ) -> bool:
        """Return whether terminal topology state is at least as fresh as the event."""
        with self.catalog.Session() as session:
            row = session.scalar(
                select(CalendarSeriesTopologyRecord).filter_by(
                    source_id=self.source_id,
                    series_master_id=series_master_id,
                )
            )
            if row is None:
                return False
            if row.status not in {
                "acquired",
                "unsupported",
                "unauthorized",
                "unavailable",
            }:
                return False
            return self._capture_time(row.latest_observed_at) >= self._capture_time(
                observed_at
            )

    def get_event_surfaces(
        self,
        *,
        event_id: str,
    ) -> dict[str, CalendarSurfaceState]:
        """Return detached surface state for Calendar enrichment planning."""
        with self.catalog.Session() as session:
            rows = session.scalars(
                select(CalendarEventSurface).filter_by(
                    source_id=self.source_id,
                    event_id=event_id,
                )
            ).all()
            return {
                row.surface: {
                    "status": row.status,
                    "evidence_id": row.evidence_id,
                    "observed_at": row.observed_at,
                    "profile_version": row.profile_version,
                    "resource_version": row.resource_version,
                }
                for row in rows
            }

    def get_event_attachments(
        self, *, event_id: str
    ) -> list[CalendarAttachmentPlanningState]:
        """Return detached attachment state needed by the Full-v1 planner."""
        with self.catalog.Session() as session:
            rows = session.scalars(
                select(CalendarEventAttachmentRecord).filter_by(
                    source_id=self.source_id,
                    event_id=event_id,
                )
            ).all()
            return [
                {
                    "attachment_id": row.attachment_id,
                    "attachment_type": row.attachment_type,
                    "calendar_id": row.calendar_id,
                    "latest_observed_at": row.latest_observed_at,
                    "latest_evidence_id": row.latest_evidence_id,
                }
                for row in rows
            ]

    def list_calendars(self) -> list[tuple[str, bool | None]]:
        """Return discovered calendar IDs and default-calendar facts."""
        with self.catalog.Session() as session:
            rows = session.execute(
                select(
                    CalendarRecord.calendar_id,
                    CalendarRecord.is_default_calendar,
                )
                .where(CalendarRecord.source_id == self.source_id)
                .order_by(
                    CalendarRecord.is_default_calendar.desc(),
                    CalendarRecord.calendar_id,
                )
            )
            return [(row.calendar_id, row.is_default_calendar) for row in rows]

    def list_event_targets(
        self,
        *,
        run_ids=None,
        event_ids=None,
    ) -> list[tuple[str, str, str | None]]:
        """Return current event/calendar/version tuples for an explicit scope."""
        normalized_runs = None if run_ids is None else tuple(dict.fromkeys(run_ids))
        normalized_events = (
            None if event_ids is None else tuple(dict.fromkeys(event_ids))
        )
        if normalized_runs == () or normalized_events == ():
            return []
        with self.catalog.Session() as session:
            stmt = select(
                CalendarEventRecord.event_id,
                CalendarEventRecord.calendar_id,
                CalendarEventRecord.change_key,
            ).where(
                CalendarEventRecord.source_id == self.source_id,
                CalendarEventRecord.is_removed.is_(False),
            )
            if normalized_events is not None:
                stmt = stmt.where(CalendarEventRecord.event_id.in_(normalized_events))
            if normalized_runs is not None:
                stmt = (
                    stmt.join(
                        CalendarEventSighting,
                        (
                            CalendarEventSighting.source_id
                            == CalendarEventRecord.source_id
                        )
                        & (
                            CalendarEventSighting.event_id
                            == CalendarEventRecord.event_id
                        ),
                    )
                    .where(CalendarEventSighting.run_id.in_(normalized_runs))
                    .distinct()
                )
            stmt = stmt.order_by(
                CalendarEventRecord.latest_observed_at.desc(),
                CalendarEventRecord.event_id,
            )
            return [
                (row.event_id, row.calendar_id, row.change_key)
                for row in session.execute(stmt)
            ]

    def list_delta_window_event_ids(
        self,
        *,
        start_datetime: str,
        end_datetime: str,
        calendar_scope: str = "default",
    ) -> list[str]:
        """Return committed present members of one fixed Calendar delta window."""
        with self.catalog.Session() as session:
            return list(
                session.scalars(
                    select(CalendarDeltaEventState.event_id)
                    .where(
                        CalendarDeltaEventState.source_id == self.source_id,
                        CalendarDeltaEventState.calendar_scope == calendar_scope,
                        CalendarDeltaEventState.start_datetime == start_datetime,
                        CalendarDeltaEventState.end_datetime == end_datetime,
                        CalendarDeltaEventState.is_present.is_(True),
                    )
                    .order_by(CalendarDeltaEventState.event_id)
                ).all()
            )


__all__ = [
    "CalendarAttachmentPlanningState",
    "CalendarEventPlanningState",
    "CalendarPlanningStore",
    "CalendarSurfaceState",
]
