"""Outlook Calendar mailbox target and permission contract."""

from __future__ import annotations

from typing import ClassVar

from .mailbox import OutlookMailboxSpider


class OutlookCalendarSpider(OutlookMailboxSpider):
    """Share Calendar own/shared scopes and mailbox path behavior."""

    graph_permissions: ClassVar[tuple[str, ...]] = ("Calendars.Read",)
    shared_graph_permissions: ClassVar[tuple[str, ...]] = ("Calendars.Read.Shared",)


__all__ = ["OutlookCalendarSpider"]
