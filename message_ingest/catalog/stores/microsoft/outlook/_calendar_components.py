"""Calendar component writes and their atomic event-owned handoff facts."""

from __future__ import annotations

from sqlalchemy import select

from message_ingest.catalog.models.microsoft.outlook.calendar import (
    CalendarEventAttachmentRecord,
    CalendarEventRecord,
    CalendarSeriesTopologyRecord,
)
from message_ingest.items.microsoft.outlook.calendar import (
    OutlookCalendarAttachmentContentItem,
    OutlookCalendarAttachmentItem,
    OutlookCalendarSeriesTopologyItem,
)
from microsoft_graph.protocol.attachments import attachment_type_name

from ._calendar_handoff import ATTACHMENT_FIELDS, SERIES_FIELDS, projection
from ._calendar_planning import CalendarPlanningStore


class CalendarComponentStore(CalendarPlanningStore):
    """Preserve provider freshness while staging parent-event component facts."""

    def persist_series_topology(
        self,
        item: OutlookCalendarSeriesTopologyItem,
    ) -> str:
        """Upsert one recurring-series topology or terminal provider outcome."""
        raw = item.raw
        with self.catalog.writer_session() as session:
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
                self._stage_component(session, item, "stale")
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
                self._stage_component(session, item, "created")
                return "created"
            current = (
                record.status,
                record.change_key,
                record.cancelled_occurrences,
                record.exception_occurrences,
                record.raw,
            )
            outcome = "unchanged" if current == previous else "changed"
            self._stage_component(session, item, outcome)
            return outcome

    def persist_attachment_metadata(
        self,
        item: OutlookCalendarAttachmentItem,
    ) -> str:
        """Upsert attachment metadata without storing provider content bytes."""
        raw = item.raw
        with self.catalog.writer_session() as session:
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
                self._stage_component(session, item, "stale")
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
                self._stage_component(session, item, "created")
                return "created"
            outcome = "unchanged" if previous_raw == raw else "changed"
            self._stage_component(session, item, outcome)
            return outcome

    def persist_attachment_content(
        self,
        item: OutlookCalendarAttachmentContentItem,
    ) -> str:
        """Link successful attachment content evidence to existing metadata."""
        with self.catalog.writer_session() as session:
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
                self._stage_component(session, item, "stale")
                return "stale"
            previous_evidence = record.content_evidence_id
            record.content_status = "acquired"
            record.content_observed_at = item.observed_at
            record.content_evidence_id = item.evidence_id
            outcome = "replay" if previous_evidence == item.evidence_id else "acquired"
            self._stage_component(session, item, outcome)
            return outcome

    def _stage_component(self, session, item, outcome: str) -> None:
        """Bind component identity and version without consulting future rows."""
        if isinstance(item, OutlookCalendarSeriesTopologyItem):
            identity = parent = item.series_master_id
            component = "series_topology"
            kind = "calendar_series"
            version = self._string((item.raw or {}).get("changeKey"))
            state = {
                "status": item.status,
                "topology": projection(item.raw, SERIES_FIELDS),
            }
            reason = item.status
        else:
            identity, parent = item.attachment_id, item.event_id
            kind = "calendar_attachment"
            version = item.resource_version
            reason = None
            if isinstance(item, OutlookCalendarAttachmentContentItem):
                component = "attachment_content"
                state = {"sha256": self._evidence_digest(session, item.evidence_id)}
            else:
                component = "attachment_metadata"
                state = {
                    "metadata": projection(item.raw, ATTACHMENT_FIELDS),
                    "attachment_type": item.attachment_type,
                    "content_bytes_present": item.content_bytes_present,
                }
        self._stage_fact(
            session,
            item,
            resource_kind=kind,
            identity=identity,
            parent=parent,
            component=component,
            state={"component": state, "resource_version": version},
            outcome=outcome,
            resource_version=version,
            reason=reason,
        )

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
