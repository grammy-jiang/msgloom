"""Outlook Calendar current-state and observation persistence."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import select

from message_ingest.catalog.models.microsoft.outlook.calendar import (
    CalendarDeltaObservation,
    CalendarEventObservation,
    CalendarEventRecord,
    CalendarEventSighting,
    CalendarRecord,
)
from message_ingest.items.microsoft.outlook.calendar import (
    OutlookCalendarDeltaObservationItem,
    OutlookCalendarEventItem,
    OutlookCalendarItem,
)
from microsoft_graph.items.outlook import OutlookEventItem

from ._calendar_components import CalendarComponentStore
from ._calendar_handoff import CALENDAR_FIELDS, projection


class OutlookCalendarStore(CalendarComponentStore):
    """Own Outlook Calendar persistence for one logical source."""

    def persist_calendar(self, item: OutlookCalendarItem) -> str:
        """Upsert latest calendar metadata without inferring missing deletions."""
        raw = item.raw
        with self.catalog.writer_session() as session:
            record = session.scalar(
                select(CalendarRecord).filter_by(
                    source_id=self.source_id,
                    calendar_id=item.calendar_id,
                )
            )
            created = record is None
            if record is None:
                record = CalendarRecord(
                    source_id=self.source_id,
                    calendar_id=item.calendar_id,
                    name=None,
                    change_key=None,
                    is_default_calendar=None,
                    can_edit=None,
                    can_share=None,
                    can_view_private_items=None,
                    latest_observed_at=item.observed_at,
                    latest_evidence_id=item.evidence_id,
                    raw=raw,
                )
                session.add(record)
            if not created and self._is_older_capture(
                item.observed_at, record.latest_observed_at
            ):
                self._stage_calendar(session, item, "stale")
                return "stale"
            previous_change_key = record.change_key
            previous_raw = record.raw
            provider = item.provider
            record.name = self._string(provider.name)
            record.change_key = self._string(provider.change_key)
            record.is_default_calendar = self._bool(provider.is_default_calendar)
            record.can_edit = self._bool(provider.can_edit)
            record.can_share = self._bool(provider.can_share)
            record.can_view_private_items = self._bool(provider.can_view_private_items)
            record.latest_observed_at = item.observed_at
            record.latest_evidence_id = item.evidence_id
            record.raw = raw
            if created:
                self._stage_calendar(session, item, "created")
                return "created"
            if self._same_semantic_version(
                previous_change_key,
                record.change_key,
                previous_raw,
                raw,
            ):
                self._stage_calendar(session, item, "unchanged")
                return "unchanged"
            self._stage_calendar(session, item, "changed")
            return "changed"

    def _stage_calendar(self, session, item, outcome) -> None:
        """Pin inventory context to exact evidence within the calendar write."""
        self._stage_fact(
            session,
            item,
            resource_kind="calendar",
            identity=item.calendar_id,
            state=projection(item.raw, CALENDAR_FIELDS),
            outcome=outcome,
            spider_name="outlook_calendar_discover",
            resource_version=item.provider.change_key,
        )

    def persist_event(self, item: OutlookCalendarEventItem) -> str:
        """Upsert current event state and append changed semantic versions."""
        raw = item.raw
        with self.catalog.writer_session() as session:
            if item.evidence_id is not None:
                replay = session.scalar(
                    select(CalendarEventObservation.observation_id).filter_by(
                        source_id=self.source_id,
                        event_id=item.event_id,
                        evidence_id=item.evidence_id,
                    )
                )
            else:
                replay = None
            record = session.scalar(
                select(CalendarEventRecord).filter_by(
                    source_id=self.source_id,
                    event_id=item.event_id,
                )
            )
            created = record is None
            if replay is not None:
                equivalent = record is not None and self._same_semantic_version(
                    record.change_key,
                    self._string(item.provider.change_key),
                    record.raw,
                    raw,
                )
                self._stage_event(
                    session,
                    item,
                    "replay" if equivalent else "stale",
                    replay,
                )
                return "replay"
            if record is not None and self._is_older_capture(
                item.observed_at, record.latest_observed_at
            ):
                self._stage_event(session, item, "stale")
                return "stale"
            previous_change_key = record.change_key if record else None
            previous_raw = record.raw if record else None
            calendar_id = self._resolved_calendar_id(session, item.calendar_id)
            if record is None:
                record = CalendarEventRecord(
                    source_id=self.source_id,
                    event_id=item.event_id,
                    calendar_id=calendar_id,
                    change_key=None,
                    subject=None,
                    start=None,
                    end=None,
                    event_type=None,
                    series_master_id=None,
                    is_all_day=None,
                    is_cancelled=None,
                    is_removed=False,
                    latest_observed_at=item.observed_at,
                    latest_evidence_id=item.evidence_id,
                    raw=raw,
                )
                session.add(record)
            same_version = not created and self._same_semantic_version(
                previous_change_key,
                self._string(item.provider.change_key),
                previous_raw,
                raw,
            )
            effective_raw = raw
            if same_version and previous_raw is not None:
                effective_raw = {**previous_raw, **raw}
            self._apply_event(
                record,
                item,
                calendar_id=calendar_id,
                raw=effective_raw,
            )
            session.add(
                CalendarEventSighting(
                    sighting_id=uuid4().hex,
                    source_id=self.source_id,
                    event_id=item.event_id,
                    calendar_id=calendar_id,
                    run_id=item.run_id,
                    observation_kind=item.observation_kind,
                    evidence_id=item.evidence_id,
                    observed_at=item.observed_at,
                )
            )
            if same_version:
                self._stage_event(session, item, "unchanged")
                return "unchanged"
            observation_id = uuid4().hex
            session.add(
                CalendarEventObservation(
                    observation_id=observation_id,
                    source_id=self.source_id,
                    event_id=item.event_id,
                    run_id=item.run_id,
                    evidence_id=item.evidence_id,
                    observed_at=item.observed_at,
                    subject=record.subject,
                    start=record.start,
                    end=record.end,
                    event_type=record.event_type,
                    raw=raw,
                )
            )
            outcome = "created" if created else "changed"
            self._stage_event(session, item, outcome, observation_id)
            return outcome

    def persist_delta_observation(
        self,
        item: OutlookCalendarDeltaObservationItem,
    ) -> str:
        """Append one exact-window delta entry without global deletion inference."""
        with self.catalog.writer_session() as session:
            replay = session.scalar(
                select(CalendarDeltaObservation.observation_id).filter_by(
                    source_id=self.source_id,
                    calendar_scope=item.calendar_scope,
                    start_datetime=item.start_datetime,
                    end_datetime=item.end_datetime,
                    evidence_id=item.evidence_id,
                    entry_index=item.entry_index,
                )
            )
            if replay is not None:
                self._stage_delta(session, item, replay)
                return "replay"
            observation_id = uuid4().hex
            session.add(
                CalendarDeltaObservation(
                    observation_id=observation_id,
                    source_id=self.source_id,
                    calendar_scope=item.calendar_scope,
                    start_datetime=item.start_datetime,
                    end_datetime=item.end_datetime,
                    run_id=item.run_id,
                    attempt=item.attempt,
                    page_number=item.page_number,
                    entry_index=item.entry_index,
                    event_id=item.event_id,
                    kind=item.kind,
                    removed_reason=item.removed_reason,
                    evidence_id=item.evidence_id,
                    observed_at=item.observed_at,
                    raw=item.raw,
                )
            )
            self._stage_delta(session, item, observation_id)
        return "created"

    def _apply_event(
        self,
        record: CalendarEventRecord,
        item: OutlookCalendarEventItem,
        *,
        calendar_id: str,
        raw: dict[str, object] | None = None,
    ) -> None:
        if raw is None:
            raw = item.raw
        # The store owns same-version merging. Project the merged response so
        # a later basic capture cannot erase fields from a richer response.
        provider = OutlookEventItem(event_id=item.event_id, raw=raw)
        record.calendar_id = calendar_id
        record.change_key = self._string(provider.change_key)
        record.subject = self._string(provider.subject)
        record.start = provider.start if isinstance(provider.start, dict) else None
        record.end = provider.end if isinstance(provider.end, dict) else None
        record.event_type = self._string(provider.event_type)
        record.series_master_id = self._string(provider.series_master_id)
        record.is_all_day = self._bool(provider.is_all_day)
        record.is_cancelled = self._bool(provider.is_cancelled)
        record.is_removed = False
        record.latest_observed_at = item.observed_at
        record.latest_evidence_id = item.evidence_id
        record.raw = raw

    def _resolved_calendar_id(self, session, calendar_id: str) -> str:
        if calendar_id != "default":
            return calendar_id
        matches = session.scalars(
            select(CalendarRecord.calendar_id).filter_by(
                source_id=self.source_id,
                is_default_calendar=True,
            )
        ).all()
        if len(matches) == 1:
            return matches[0]
        return calendar_id

    @classmethod
    def _is_older_capture(cls, incoming: str, current: str) -> bool:
        return cls._capture_time(incoming) < cls._capture_time(current)

    @staticmethod
    def _capture_time(value: str) -> datetime:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("Calendar observed_at must include a timezone offset")
        return parsed

    @staticmethod
    def _same_semantic_version(
        old_change_key: str | None,
        new_change_key: str | None,
        old_raw: dict[str, object] | None,
        new_raw: dict[str, object],
    ) -> bool:
        if old_change_key is not None and new_change_key is not None:
            return old_change_key == new_change_key
        return old_raw == new_raw

    @staticmethod
    def _string(value: object) -> str | None:
        return value if isinstance(value, str) else None

    @staticmethod
    def _bool(value: object) -> bool | None:
        return value if isinstance(value, bool) else None


__all__ = ["OutlookCalendarStore"]
