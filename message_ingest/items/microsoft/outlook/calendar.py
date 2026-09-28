"""Typed items produced by Outlook Calendar spiders."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from microsoft_graph.items.outlook import (
    OutlookCalendarAttachmentItem as GraphOutlookCalendarAttachmentItem,
)
from microsoft_graph.items.outlook import (
    OutlookCalendarItem as GraphOutlookCalendarItem,
)
from microsoft_graph.items.outlook import (
    OutlookEventItem as GraphOutlookEventItem,
)


@dataclass(slots=True)
class OutlookCalendarItem(GraphOutlookCalendarItem):
    """One observation of a calendar visible to the signed-in user."""

    observed_at: str
    evidence_id: str | None
    run_id: str | None


@dataclass(slots=True)
class OutlookCalendarEventItem(GraphOutlookEventItem):
    """One observation of an event in a declared Calendar scope."""

    observed_at: str
    evidence_id: str | None
    run_id: str | None
    calendar_id: str = "default"
    observation_kind: str = "window"


@dataclass(slots=True)
class OutlookCalendarAttachmentItem(GraphOutlookCalendarAttachmentItem):
    """One attachment metadata/content observation for a Calendar event."""

    observed_at: str
    evidence_id: str | None
    run_id: str | None
    calendar_id: str = "default"
    content_bytes_present: bool = False


@dataclass(slots=True)
class OutlookCalendarAttachmentContentItem:
    """Successful raw-content acquisition for one Calendar attachment."""

    event_id: str
    attachment_id: str
    observed_at: str
    evidence_id: str | None
    run_id: str | None


@dataclass(slots=True)
class OutlookCalendarEventSurfaceItem:
    """Versioned acquisition outcome for one Calendar event surface."""

    event_id: str
    surface: str
    status: str
    observed_at: str
    evidence_id: str | None
    profile_version: str | None = None
    resource_version: str | None = None


@dataclass(slots=True)
class OutlookCalendarSeriesTopologyItem:
    """Expanded or terminal recurring-series topology for one series master."""

    series_master_id: str
    calendar_id: str
    status: str
    raw: dict[str, Any] | None
    observed_at: str
    evidence_id: str | None
    run_id: str | None


@dataclass(slots=True)
class OutlookCalendarDeltaObservationItem:
    """One ordered event entry from a fixed Calendar delta window."""

    event_id: str
    kind: str
    raw: dict[str, Any]
    observed_at: str
    evidence_id: str
    run_id: str
    attempt: int
    page_number: int
    entry_index: int
    start_datetime: str
    end_datetime: str
    removed_reason: str | None = None
    calendar_scope: str = "default"


@dataclass(slots=True)
class OutlookCalendarDeltaCheckpointCandidateItem:
    """Terminal Calendar delta cursor pending idle-time promotion."""

    run_id: str
    attempt: int
    base_revision: int | None
    delta_link: str
    observed_at: str
    evidence_id: str
    start_datetime: str
    end_datetime: str
    calendar_scope: str = "default"


__all__ = [
    "OutlookCalendarAttachmentContentItem",
    "OutlookCalendarAttachmentItem",
    "OutlookCalendarDeltaCheckpointCandidateItem",
    "OutlookCalendarDeltaObservationItem",
    "OutlookCalendarEventItem",
    "OutlookCalendarEventSurfaceItem",
    "OutlookCalendarItem",
    "OutlookCalendarSeriesTopologyItem",
]
