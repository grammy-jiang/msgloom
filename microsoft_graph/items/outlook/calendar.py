"""Optional Calendar resources with no storage or acquisition state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Self

from microsoft_graph.protocol import graph_object


@dataclass(slots=True)
class OutlookCalendarItem:
    """Calendar identity and the unchanged provider representation."""

    calendar_id: str
    raw: dict[str, Any]

    @classmethod
    def from_graph(cls, resource: dict[str, Any], **kwargs: Any) -> Self:
        """Map a calendar; extra keyword arguments supply subclass fields."""
        raw = graph_object(resource, context="Outlook calendar")
        return cls(calendar_id=raw["id"], raw=raw, **kwargs)


@dataclass(slots=True)
class OutlookEventItem:
    """Event identity and full provider JSON, including recurrence fields."""

    event_id: str
    raw: dict[str, Any]

    @classmethod
    def from_graph(cls, resource: dict[str, Any], **kwargs: Any) -> Self:
        """Map an event without assigning collection or calendar scope."""
        raw = graph_object(resource, context="Outlook event")
        return cls(event_id=raw["id"], raw=raw, **kwargs)


@dataclass(slots=True)
class OutlookCalendarAttachmentItem:
    """Attachment identity, provider type, and JSON under one event."""

    event_id: str
    attachment_id: str
    attachment_type: str | None
    raw: dict[str, Any]

    @classmethod
    def from_graph(
        cls, resource: dict[str, Any], *, event_id: str, **kwargs: Any
    ) -> Self:
        """Retain attachment JSON; keyword arguments supply subclass fields."""
        raw = graph_object(resource, context="Calendar attachment")
        return cls(
            event_id=event_id,
            attachment_id=raw["id"],
            attachment_type=raw.get("@odata.type"),
            raw=raw,
            **kwargs,
        )
