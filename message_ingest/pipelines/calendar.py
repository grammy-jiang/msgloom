"""Persist Microsoft Calendar inventory and event state."""

from __future__ import annotations

import asyncio
from datetime import datetime
from uuid import uuid4

from scrapy.exceptions import NotConfigured
from sqlalchemy import select

from message_ingest.catalog import (
    CalendarEventObservation,
    CalendarEventRecord,
    CalendarRecord,
)
from message_ingest.extensions.catalog import CatalogService
from message_ingest.items import OutlookCalendarEventItem, OutlookCalendarItem


class CalendarPipeline:
    """
    Persist Calendar resource items after evidence linking.

    Calendar inventory updates its latest known record. Event observations are
    appended only when their semantic provider version changes; repeated
    retrieval of the same changeKey updates current evidence without creating
    another semantic version.
    """

    def __init__(
        self,
        *,
        service: CatalogService,
        source_id: str,
        stats=None,
    ) -> None:
        """Borrow the crawler-owned catalog, write lock, and stats collector."""
        self.service = service
        self.catalog = service.catalog
        self.source_id = source_id
        self.stats = stats
        self._write_lock = service.write_lock

    @classmethod
    def from_crawler(cls, crawler):
        """Enable Calendar persistence only when the SQL catalog is available."""
        if not crawler.settings.getbool("MSGLOOM_CATALOG_ENABLED"):
            raise NotConfigured("Calendar persistence requires the SQL catalog")
        return cls(
            service=CatalogService.from_crawler(crawler),
            source_id=crawler.settings["MSGLOOM_SOURCE_ID"],
            stats=crawler.stats,
        )

    def close_spider(self) -> None:
        """Close the crawler-shared catalog after item processing completes."""
        self.service.close()

    async def process_item(self, item):
        """Persist supported Calendar items and pass other resources through."""
        if isinstance(item, OutlookCalendarItem):
            async with self._write_lock:
                outcome = await asyncio.to_thread(
                    self._persist_calendar_sync,
                    item,
                )
            self._inc("msgloom/calendar/calendar_item_processed_count")
            self._inc(f"msgloom/calendar/calendar_{outcome}_count")
            return item

        if isinstance(item, OutlookCalendarEventItem):
            async with self._write_lock:
                outcome = await asyncio.to_thread(
                    self._persist_event_sync,
                    item,
                )
            self._inc("msgloom/calendar/event_item_processed_count")
            self._inc(f"msgloom/calendar/event_{outcome}_count")
            return item

        return item

    def _persist_calendar_sync(self, item: OutlookCalendarItem) -> str:
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

            if (
                not created
                and self._is_older_capture(
                    item.observed_at, record.latest_observed_at
                )
            ):
                return "stale"

            previous_change_key = record.change_key
            previous_raw = record.raw
            record.name = self._string(raw.get("name"))
            record.change_key = self._string(raw.get("changeKey"))
            record.is_default_calendar = self._bool(
                raw.get("isDefaultCalendar")
            )
            record.can_edit = self._bool(raw.get("canEdit"))
            record.can_share = self._bool(raw.get("canShare"))
            record.can_view_private_items = self._bool(
                raw.get("canViewPrivateItems")
            )
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

    def _persist_event_sync(self, item: OutlookCalendarEventItem) -> str:
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
            if (
                record is not None
                and self._is_older_capture(
                    item.observed_at, record.latest_observed_at
                )
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

            self._apply_event(record, item, calendar_id=calendar_id)

            if not created and self._same_semantic_version(
                previous_change_key,
                record.change_key,
                previous_raw,
                raw,
            ):
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

    def _apply_event(
        self,
        record: CalendarEventRecord,
        item: OutlookCalendarEventItem,
        *,
        calendar_id: str,
    ) -> None:
        """Copy searchable projections while retaining the raw provider JSON."""
        raw = item.raw
        start = raw.get("start")
        end = raw.get("end")
        record.calendar_id = calendar_id
        record.change_key = self._string(raw.get("changeKey"))
        record.subject = self._string(raw.get("subject"))
        record.start = start if isinstance(start, dict) else None
        record.end = end if isinstance(end, dict) else None
        record.event_type = self._string(raw.get("type"))
        record.series_master_id = self._string(raw.get("seriesMasterId"))
        record.is_all_day = self._bool(raw.get("isAllDay"))
        record.is_cancelled = self._bool(raw.get("isCancelled"))
        record.is_removed = False
        record.latest_observed_at = item.observed_at
        record.latest_evidence_id = item.evidence_id
        record.raw = raw

    def _resolved_calendar_id(self, session, calendar_id: str) -> str:
        """Resolve the default scope to one discovered provider calendar ID."""
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
        """Prevent older canonical cache evidence from rolling state back."""
        return cls._capture_time(incoming) < cls._capture_time(current)

    @staticmethod
    def _capture_time(value: str) -> datetime:
        """Parse one msgloom evidence capture timestamp."""
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError(
                "Calendar observed_at must include a timezone offset"
            )
        return parsed
    @staticmethod
    def _same_semantic_version(
        old_change_key: str | None,
        new_change_key: str | None,
        old_raw: dict[str, object] | None,
        new_raw: dict[str, object],
    ) -> bool:
        """Prefer Graph changeKey; fall back to exact raw equality."""
        if old_change_key is not None and new_change_key is not None:
            return old_change_key == new_change_key
        return old_raw == new_raw

    @staticmethod
    def _string(value: object) -> str | None:
        """Project only actual strings."""
        return value if isinstance(value, str) else None

    @staticmethod
    def _bool(value: object) -> bool | None:
        """Project only actual booleans."""
        return value if isinstance(value, bool) else None

    def _inc(self, key: str) -> None:
        """Publish bounded Calendar persistence counters when stats are present."""
        if self.stats is not None:
            self.stats.inc_value(key)
