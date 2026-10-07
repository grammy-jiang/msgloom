"""Privacy-safe summaries for items emitted by acquisition spiders."""

from __future__ import annotations

from typing import Any

from message_ingest.items.acquisition import (
    AcquisitionFailureItem,
    RawHttpEvidenceItem,
)
from message_ingest.items.microsoft.outlook.calendar import (
    OutlookCalendarAttachmentContentItem,
    OutlookCalendarAttachmentItem,
    OutlookCalendarDeltaCheckpointCandidateItem,
    OutlookCalendarDeltaObservationItem,
    OutlookCalendarEventItem,
    OutlookCalendarItem,
)
from message_ingest.items.microsoft.outlook.email import (
    OutlookAttachmentItem,
    OutlookDeltaCheckpointCandidateItem,
    OutlookMailDetailItem,
    OutlookMailFolderItem,
    OutlookMailItem,
    OutlookMailRemovalItem,
    OutlookMessageSurfaceItem,
)


def summarize_item(item: Any) -> str:
    """Return a bounded allowlisted summary without rendering arbitrary payloads."""
    if isinstance(item, RawHttpEvidenceItem):
        return (
            f"RawHttpEvidenceItem(purpose={item.purpose!r}, "
            f"status={item.response_status!r}, origin={item.origin!r}, "
            f"evidence_id={item.evidence_id!r})"
        )
    if isinstance(item, AcquisitionFailureItem):
        return (
            f"AcquisitionFailureItem(purpose={item.purpose!r}, "
            f"error_type={item.error_type!r})"
        )

    if isinstance(item, OutlookMailItem):
        return f"OutlookMailItem(message_id={item.message_id!r})"
    if isinstance(item, OutlookMailDetailItem):
        return f"OutlookMailDetailItem(message_id={item.message_id!r})"
    if isinstance(item, OutlookAttachmentItem):
        return (
            f"OutlookAttachmentItem(message_id={item.message_id!r}, "
            f"attachment_id={item.attachment_id!r})"
        )
    if isinstance(item, OutlookMailFolderItem):
        return f"OutlookMailFolderItem(folder_id={item.folder_id!r})"
    if isinstance(item, OutlookMailRemovalItem):
        return (
            f"OutlookMailRemovalItem(message_id={item.message_id!r}, "
            f"folder_id={item.folder_id!r})"
        )
    if isinstance(item, OutlookMessageSurfaceItem):
        return (
            f"OutlookMessageSurfaceItem(message_id={item.message_id!r}, "
            f"surface={item.surface!r}, status={item.status!r})"
        )
    if isinstance(item, OutlookDeltaCheckpointCandidateItem):
        return f"OutlookDeltaCheckpointCandidateItem(folder_id={item.folder_id!r})"

    if isinstance(item, OutlookCalendarItem):
        return f"OutlookCalendarItem(calendar_id={item.calendar_id!r})"
    if isinstance(item, OutlookCalendarEventItem):
        return (
            f"OutlookCalendarEventItem(event_id={item.event_id!r}, "
            f"calendar_id={item.calendar_id!r})"
        )
    if isinstance(item, OutlookCalendarAttachmentItem):
        return (
            f"OutlookCalendarAttachmentItem(event_id={item.event_id!r}, "
            f"attachment_id={item.attachment_id!r})"
        )
    if isinstance(item, OutlookCalendarAttachmentContentItem):
        return (
            f"OutlookCalendarAttachmentContentItem(event_id={item.event_id!r}, "
            f"attachment_id={item.attachment_id!r})"
        )
    if isinstance(item, OutlookCalendarDeltaObservationItem):
        return (
            f"OutlookCalendarDeltaObservationItem(event_id={item.event_id!r}, "
            f"kind={item.kind!r}, attempt={item.attempt!r})"
        )
    if isinstance(item, OutlookCalendarDeltaCheckpointCandidateItem):
        return (
            "OutlookCalendarDeltaCheckpointCandidateItem("
            f"attempt={item.attempt!r}, calendar_scope={item.calendar_scope!r})"
        )

    return type(item).__name__


__all__ = ["summarize_item"]
