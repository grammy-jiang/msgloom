"""Optional Outlook resource dataclasses accepted by Scrapy's item adapters."""

from .calendar import (
    OutlookCalendarAttachmentItem,
    OutlookCalendarItem,
    OutlookEventItem,
)
from .mail import OutlookAttachmentItem, OutlookMailFolderItem, OutlookMessageItem

__all__ = [
    "OutlookAttachmentItem",
    "OutlookCalendarAttachmentItem",
    "OutlookCalendarItem",
    "OutlookEventItem",
    "OutlookMailFolderItem",
    "OutlookMessageItem",
]
