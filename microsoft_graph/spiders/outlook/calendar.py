"""Outlook Calendar mailbox target and permission contract."""

from __future__ import annotations

from collections.abc import Sequence
from typing import ClassVar
from urllib.parse import quote, urlencode

from .mailbox import OutlookMailboxSpider


class OutlookCalendarSpider(OutlookMailboxSpider):
    """Supply Calendar scopes, mailbox paths, and immutable IDs."""

    graph_prefer = 'IdType="ImmutableId"'
    graph_permissions: ClassVar[tuple[str, ...]] = ("Calendars.Read",)
    shared_graph_permissions: ClassVar[tuple[str, ...]] = ("Calendars.Read.Shared",)

    def calendars_path(self, *, page_size: int | None = None) -> str:
        """List visible calendars with the provider's encoded page-size query."""
        path = f"{self._mailbox_path()}/calendars"
        if page_size is None:
            return path
        return f"{path}?{urlencode({'$top': page_size})}"

    def event_path(self, event_id: str, *, calendar_id: str = "") -> str:
        """Build an event path in the mailbox or one named calendar."""
        path = self._mailbox_path()
        if calendar_id:
            path += f"/calendars/{quote(calendar_id, safe='')}"
        return f"{path}/events/{quote(event_id, safe='')}"

    def calendar_view_path(
        self,
        start_datetime: str,
        end_datetime: str,
        *,
        calendar_id: str = "",
        page_size: int | None = None,
    ) -> str:
        """
        Build a default or named calendarView with exact boundary text.

        Use :func:`~microsoft_graph.protocol.calendar.calendar_window`
        before request construction. This helper does not choose a window.
        """
        calendar = (
            f"calendars/{quote(calendar_id, safe='')}" if calendar_id else "calendar"
        )
        query: dict[str, str | int] = {
            "startDateTime": start_datetime,
            "endDateTime": end_datetime,
        }
        if page_size is not None:
            query["$top"] = page_size
        return f"{self._mailbox_path()}/{calendar}/calendarView?{urlencode(query)}"

    def calendar_view_delta_path(self, start_datetime: str, end_datetime: str) -> str:
        """Build primary-calendar delta; do not add unsupported select/top fields."""
        query = urlencode(
            {"startDateTime": start_datetime, "endDateTime": end_datetime}
        )
        return f"{self._mailbox_path()}/calendarView/delta?{query}"

    def series_master_path(
        self,
        event_id: str,
        *,
        calendar_id: str = "",
        fields: Sequence[str] = (),
    ) -> str:
        """Expand series exceptions with an optional caller-selected projection."""
        query = {}
        if fields:
            query["$select"] = ",".join(fields)
        query["$expand"] = "exceptionOccurrences"
        return (
            f"{self.event_path(event_id, calendar_id=calendar_id)}?{urlencode(query)}"
        )


__all__ = ["OutlookCalendarSpider"]
