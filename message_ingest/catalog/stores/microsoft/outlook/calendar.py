"""Outlook Calendar current-state and observation persistence."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import select

from message_ingest.catalog.models.microsoft.outlook.calendar import (
    CalendarDeltaObservation,
    CalendarEventAttachmentRecord,
    CalendarEventObservation,
    CalendarEventRecord,
    CalendarEventSighting,
    CalendarRecord,
    CalendarSeriesTopologyRecord,
)
from message_ingest.items.microsoft.outlook.calendar import (
    OutlookCalendarAttachmentContentItem,
    OutlookCalendarAttachmentItem,
    OutlookCalendarDeltaObservationItem,
    OutlookCalendarEventItem,
    OutlookCalendarItem,
    OutlookCalendarSeriesTopologyItem,
)
from microsoft_graph.items.outlook import OutlookEventItem
from microsoft_graph.protocol.attachments import attachment_type_name

from ._calendar_planning import CalendarPlanningStore


class OutlookCalendarStore(CalendarPlanningStore):
    """Own Outlook Calendar persistence for one logical source."""

    def persist_calendar(self, item: OutlookCalendarItem) -> str:
        """Upsert latest calendar metadata without inferring missing deletions."""
        raw = item.raw
        with self.catalog.Session() as session, session.begin():
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
                return "created"
            if self._same_semantic_version(
                previous_change_key,
                record.change_key,
                previous_raw,
                raw,
            ):
                return "unchanged"
            return "changed"

    def persist_event(self, item: OutlookCalendarEventItem) -> str:
        """Upsert current event state and append changed semantic versions."""
        raw = item.raw
        with self.catalog.Session() as session, session.begin():
            if item.evidence_id is not None:
                replay = session.scalar(
                    select(CalendarEventObservation.observation_id).filter_by(
                        source_id=self.source_id,
                        event_id=item.event_id,
                        evidence_id=item.evidence_id,
                    )
                )
                if replay is not None:
                    return "replay"
            record = session.scalar(
                select(CalendarEventRecord).filter_by(
                    source_id=self.source_id,
                    event_id=item.event_id,
                )
            )
            created = record is None
            if record is not None and self._is_older_capture(
                item.observed_at, record.latest_observed_at
            ):
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
                return "unchanged"
            session.add(
                CalendarEventObservation(
                    observation_id=uuid4().hex,
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
            return "created" if created else "changed"

    def persist_delta_observation(
        self,
        item: OutlookCalendarDeltaObservationItem,
    ) -> str:
        """Append one exact-window delta entry without global deletion inference."""
        with self.catalog.Session() as session, session.begin():
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
                return "replay"
            session.add(
                CalendarDeltaObservation(
                    observation_id=uuid4().hex,
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
        return "created"

    def persist_series_topology(
        self,
        item: OutlookCalendarSeriesTopologyItem,
    ) -> str:
        """Upsert one recurring-series topology or terminal provider outcome."""
        raw = item.raw
        with self.catalog.Session() as session, session.begin():
            record = session.scalar(
                select(CalendarSeriesTopologyRecord).filter_by(
                    source_id=self.source_id,
                    series_master_id=item.series_master_id,
                )
            )
            created = record is None
            if record is not None and self._is_older_capture(
                item.observed_at, record.latest_observed_at
            ):
                return "stale"
            if record is None:
                record = CalendarSeriesTopologyRecord(
                    source_id=self.source_id,
                    series_master_id=item.series_master_id,
                    calendar_id=item.calendar_id,
                    status=item.status,
                    change_key=None,
                    cancelled_occurrences=None,
                    exception_occurrences=None,
                    latest_observed_at=item.observed_at,
                    latest_evidence_id=item.evidence_id,
                    raw=None,
                )
                session.add(record)
            previous = (
                record.status,
                record.change_key,
                record.cancelled_occurrences,
                record.exception_occurrences,
                record.raw,
            )
            record.calendar_id = item.calendar_id
            record.status = item.status
            record.latest_observed_at = item.observed_at
            record.latest_evidence_id = item.evidence_id
            record.raw = raw
            if raw is None:
                record.change_key = None
                record.cancelled_occurrences = None
                record.exception_occurrences = None
            else:
                record.change_key = self._string(raw.get("changeKey"))
                cancelled = raw.get("cancelledOccurrences")
                exceptions = raw.get("exceptionOccurrences")
                record.cancelled_occurrences = (
                    cancelled if isinstance(cancelled, list) else []
                )
                record.exception_occurrences = (
                    exceptions if isinstance(exceptions, list) else []
                )
            if created:
                return "created"
            current = (
                record.status,
                record.change_key,
                record.cancelled_occurrences,
                record.exception_occurrences,
                record.raw,
            )
            return "unchanged" if current == previous else "changed"

    def persist_attachment_metadata(
        self,
        item: OutlookCalendarAttachmentItem,
    ) -> str:
        """Upsert attachment metadata without storing provider content bytes."""
        raw = item.raw
        with self.catalog.Session() as session, session.begin():
            calendar_id = item.calendar_id
            if calendar_id == "default":
                parent = session.scalar(
                    select(CalendarEventRecord).filter_by(
                        source_id=self.source_id,
                        event_id=item.event_id,
                    )
                )
                if parent is not None:
                    calendar_id = parent.calendar_id
            record = session.scalar(
                select(CalendarEventAttachmentRecord).filter_by(
                    source_id=self.source_id,
                    event_id=item.event_id,
                    attachment_id=item.attachment_id,
                )
            )
            created = record is None
            if record is not None and self._is_older_capture(
                item.observed_at,
                record.latest_observed_at,
            ):
                return "stale"
            if record is None:
                record = CalendarEventAttachmentRecord(
                    source_id=self.source_id,
                    event_id=item.event_id,
                    attachment_id=item.attachment_id,
                    calendar_id=calendar_id,
                    attachment_type=item.attachment_type,
                    name=None,
                    content_type=None,
                    size=None,
                    is_inline=None,
                    content_bytes_present=item.content_bytes_present,
                    content_status=self._initial_content_status(item.attachment_type),
                    content_observed_at=None,
                    content_evidence_id=None,
                    latest_observed_at=item.observed_at,
                    latest_evidence_id=item.evidence_id,
                    raw=raw,
                )
                session.add(record)
            previous_raw = record.raw
            record.calendar_id = calendar_id
            record.attachment_type = item.attachment_type
            provider = item.provider
            record.name = self._string(provider.name)
            record.content_type = self._string(provider.content_type)
            size = provider.size
            record.size = (
                size if isinstance(size, int) and not isinstance(size, bool) else None
            )
            record.is_inline = self._bool(provider.is_inline)
            record.content_bytes_present = item.content_bytes_present
            record.latest_observed_at = item.observed_at
            record.latest_evidence_id = item.evidence_id
            record.raw = raw
            if created:
                return "created"
            return "unchanged" if previous_raw == raw else "changed"

    def persist_attachment_content(
        self,
        item: OutlookCalendarAttachmentContentItem,
    ) -> str:
        """Link successful attachment content evidence to existing metadata."""
        with self.catalog.Session() as session, session.begin():
            record = session.scalar(
                select(CalendarEventAttachmentRecord).filter_by(
                    source_id=self.source_id,
                    event_id=item.event_id,
                    attachment_id=item.attachment_id,
                )
            )
            if record is None:
                raise RuntimeError(
                    "Calendar attachment content arrived before metadata"
                )
            if record.content_observed_at is not None and self._is_older_capture(
                item.observed_at,
                record.content_observed_at,
            ):
                return "stale"
            previous_evidence = record.content_evidence_id
            record.content_status = "acquired"
            record.content_observed_at = item.observed_at
            record.content_evidence_id = item.evidence_id
            if previous_evidence == item.evidence_id:
                return "replay"
            return "acquired"

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
    def _initial_content_status(attachment_type: str | None) -> str:
        normalized = attachment_type_name(attachment_type)
        if normalized in {"fileAttachment", "itemAttachment"}:
            return "pending"
        if normalized == "referenceAttachment":
            return "reference"
        return "unsupported"

    @staticmethod
    def _string(value: object) -> str | None:
        return value if isinstance(value, str) else None

    @staticmethod
    def _bool(value: object) -> bool | None:
        return value if isinstance(value, bool) else None


__all__ = ["OutlookCalendarStore"]
