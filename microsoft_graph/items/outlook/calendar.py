"""Optional Calendar resources with no storage or acquisition state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Self

from microsoft_graph.protocol import graph_object


def _resource(resource: dict[str, Any], context: str) -> dict[str, Any]:
    """Require a provider object and nonempty ID without inspecting policy."""
    raw = graph_object(resource, context=context)
    if not isinstance(raw.get("id"), str) or not raw["id"]:
        raise ValueError(f"{context} requires a non-empty id")
    return raw


@dataclass(slots=True)
class OutlookCalendarItem:
    """
    Calendar fields and the unchanged provider representation.

    Projections snapshot optional values at construction; missing fields are
    ``None``. The constructor also accepts an identity from consumer context.
    :meth:`from_graph` validates the provider's object and ID instead.
    """

    calendar_id: str
    raw: dict[str, Any]
    name: str | None = field(init=False)
    change_key: str | None = field(init=False)
    is_default_calendar: bool | None = field(init=False)
    can_edit: bool | None = field(init=False)
    can_share: bool | None = field(init=False)
    can_view_private_items: bool | None = field(init=False)

    def __post_init__(self) -> None:
        """Project optional provider fields without coercing falsey values."""
        self.name = self.raw.get("name")
        self.change_key = self.raw.get("changeKey")
        self.is_default_calendar = self.raw.get("isDefaultCalendar")
        self.can_edit = self.raw.get("canEdit")
        self.can_share = self.raw.get("canShare")
        self.can_view_private_items = self.raw.get("canViewPrivateItems")

    @classmethod
    def from_graph(cls, resource: dict[str, Any], **kwargs: Any) -> Self:
        """Map a calendar; extra keyword arguments supply subclass fields."""
        raw = _resource(resource, "Calendar inventory entry")
        return cls(calendar_id=raw["id"], raw=raw, **kwargs)


@dataclass(slots=True)
class OutlookEventItem:
    """Event fields and full JSON without window or completeness policy."""

    event_id: str
    raw: dict[str, Any]
    change_key: str | None = field(init=False)
    subject: str | None = field(init=False)
    start: dict[str, Any] | None = field(init=False)
    end: dict[str, Any] | None = field(init=False)
    event_type: str | None = field(init=False)
    series_master_id: str | None = field(init=False)
    is_all_day: bool | None = field(init=False)
    is_cancelled: bool | None = field(init=False)
    has_attachments: bool | None = field(init=False)

    def __post_init__(self) -> None:
        """Retain provider values, including nested date/time object identity."""
        self.change_key = self.raw.get("changeKey")
        self.subject = self.raw.get("subject")
        self.start = self.raw.get("start")
        self.end = self.raw.get("end")
        self.event_type = self.raw.get("type")
        self.series_master_id = self.raw.get("seriesMasterId")
        self.is_all_day = self.raw.get("isAllDay")
        self.is_cancelled = self.raw.get("isCancelled")
        self.has_attachments = self.raw.get("hasAttachments")

    @classmethod
    def from_graph(cls, resource: dict[str, Any], **kwargs: Any) -> Self:
        """Map an event without assigning collection or calendar scope."""
        raw = _resource(resource, "Outlook event")
        return cls(event_id=raw["id"], raw=raw, **kwargs)


@dataclass(slots=True)
class OutlookCalendarAttachmentItem:
    """Attachment identity, provider type, and JSON under one event."""

    event_id: str
    attachment_id: str
    attachment_type: str | None
    raw: dict[str, Any]
    name: str | None = field(init=False)
    content_type: str | None = field(init=False)
    size: int | None = field(init=False)
    is_inline: bool | None = field(init=False)

    def __post_init__(self) -> None:
        """Project metadata without removing content or normalizing type names."""
        self.name = self.raw.get("name")
        self.content_type = self.raw.get("contentType")
        self.size = self.raw.get("size")
        self.is_inline = self.raw.get("isInline")

    @classmethod
    def from_graph(
        cls, resource: dict[str, Any], *, event_id: str, **kwargs: Any
    ) -> Self:
        """Retain attachment JSON; keyword arguments supply subclass fields."""
        raw = _resource(resource, "Calendar attachment")
        return cls(
            event_id=event_id,
            attachment_id=raw["id"],
            attachment_type=raw.get("@odata.type"),
            raw=raw,
            **kwargs,
        )
