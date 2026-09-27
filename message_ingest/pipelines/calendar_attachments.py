"""Persist Calendar attachment metadata and raw-content linkage."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from message_ingest.catalog import CalendarEventAttachmentRecord, CalendarEventRecord
from message_ingest.items import (
    OutlookCalendarAttachmentContentItem,
    OutlookCalendarAttachmentItem,
)


class CalendarAttachmentStore:
    """Own current-state projection for Calendar event attachments."""

    def __init__(self, catalog, *, source_id: str) -> None:
        self.catalog = catalog
        self.source_id = source_id

    def persist_metadata(
        self,
        item: OutlookCalendarAttachmentItem,
    ) -> str:
        """Upsert metadata without duplicating provider content bytes."""
        raw = item.raw
        with self.catalog.Session() as session, session.begin():
            calendar_id = item.calendar_id
            if calendar_id == "default":
                # The event callback completes before attachment traversal.
                # Reuse its resolved calendar ID within this source only.
                parent = session.scalar(
                    select(CalendarEventRecord).filter_by(
                        source_id=self.source_id, event_id=item.event_id
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
                    content_status=self._initial_content_status(
                        item.attachment_type
                    ),
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
            record.name = self._string(raw.get("name"))
            record.content_type = self._string(raw.get("contentType"))
            size = raw.get("size")
            record.size = (
                size
                if isinstance(size, int) and not isinstance(size, bool)
                else None
            )
            record.is_inline = self._bool(raw.get("isInline"))
            record.content_bytes_present = item.content_bytes_present
            record.latest_observed_at = item.observed_at
            record.latest_evidence_id = item.evidence_id
            record.raw = raw

            if created:
                return "created"
            return "unchanged" if previous_raw == raw else "changed"

    def persist_content(
        self,
        item: OutlookCalendarAttachmentContentItem,
    ) -> str:
        """Link one successful attachment content response to its metadata."""
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
            if (
                record.content_observed_at is not None
                and self._is_older_capture(
                    item.observed_at,
                    record.content_observed_at,
                )
            ):
                return "stale"
            previous_evidence = record.content_evidence_id
            record.content_status = "acquired"
            record.content_observed_at = item.observed_at
            record.content_evidence_id = item.evidence_id
            if previous_evidence == item.evidence_id:
                return "replay"
            return "acquired"

    @classmethod
    def _initial_content_status(cls, attachment_type: str | None) -> str:
        normalized = cls._attachment_type_name(attachment_type)
        if normalized in {"fileAttachment", "itemAttachment"}:
            return "pending"
        if normalized == "referenceAttachment":
            return "reference"
        return "unsupported"

    @staticmethod
    def _attachment_type_name(attachment_type: str | None) -> str:
        return (
            (attachment_type or "unknown")
            .removeprefix("#microsoft.graph.")
            .removeprefix("microsoft.graph.")
        )

    @classmethod
    def _is_older_capture(cls, incoming: str, current: str) -> bool:
        return cls._capture_time(incoming) < cls._capture_time(current)

    @staticmethod
    def _capture_time(value: str) -> datetime:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError(
                "Calendar attachment observed_at must include a timezone offset"
            )
        return parsed

    @staticmethod
    def _string(value: object) -> str | None:
        return value if isinstance(value, str) else None

    @staticmethod
    def _bool(value: object) -> bool | None:
        return value if isinstance(value, bool) else None
