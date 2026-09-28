"""Typed items produced by Outlook Calendar spiders."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Self

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
class OutlookCalendarItem:
    """Keep the persisted observation schema; compose provider projections."""

    calendar_id: str
    raw: dict[str, Any]
    observed_at: str
    evidence_id: str | None
    run_id: str | None

    @property
    def provider(self) -> GraphOutlookCalendarItem:
        """Project current raw metadata using the observation's identity."""
        return GraphOutlookCalendarItem(calendar_id=self.calendar_id, raw=self.raw)

    @classmethod
    def from_graph(cls, resource: dict[str, Any], **kwargs: Any) -> Self:
        """Validate a provider calendar and attach application provenance."""
        provider = GraphOutlookCalendarItem.from_graph(resource)
        return cls(calendar_id=provider.calendar_id, raw=provider.raw, **kwargs)


@dataclass(slots=True)
class OutlookCalendarEventItem:
    """One observation of an event in a declared Calendar scope."""

    event_id: str
    raw: dict[str, Any]
    observed_at: str
    evidence_id: str | None
    run_id: str | None
    calendar_id: str = "default"
    observation_kind: str = "window"

    @property
    def provider(self) -> GraphOutlookEventItem:
        """Project current raw metadata without changing the item schema."""
        return GraphOutlookEventItem(event_id=self.event_id, raw=self.raw)

    @classmethod
    def from_graph(cls, resource: dict[str, Any], **kwargs: Any) -> Self:
        """Validate a provider event and attach application provenance."""
        provider = GraphOutlookEventItem.from_graph(resource)
        return cls(event_id=provider.event_id, raw=provider.raw, **kwargs)


@dataclass(slots=True)
class OutlookCalendarAttachmentItem:
    """One attachment metadata/content observation for a Calendar event."""

    event_id: str
    attachment_id: str
    attachment_type: str | None
    raw: dict[str, Any]
    observed_at: str
    evidence_id: str | None
    run_id: str | None
    calendar_id: str = "default"
    content_bytes_present: bool = False

    @property
    def provider(self) -> GraphOutlookCalendarAttachmentItem:
        """Project current metadata after application content removal."""
        return GraphOutlookCalendarAttachmentItem(
            event_id=self.event_id,
            attachment_id=self.attachment_id,
            attachment_type=self.attachment_type,
            raw=self.raw,
        )

    @classmethod
    def from_graph(
        cls, resource: dict[str, Any], *, event_id: str, **kwargs: Any
    ) -> Self:
        """Validate provider metadata without changing content ownership."""
        provider = GraphOutlookCalendarAttachmentItem.from_graph(
            resource, event_id=event_id
        )
        return cls(
            event_id=event_id,
            attachment_id=provider.attachment_id,
            attachment_type=provider.attachment_type,
            raw=provider.raw,
            **kwargs,
        )


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
