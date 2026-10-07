"""Provider-only Outlook bases; semantic projection belongs to consumers."""

from .calendar import OutlookCalendarSpider
from .mail import OutlookMailSpider
from .mailbox import OutlookMailboxSpider

__all__ = ["OutlookCalendarSpider", "OutlookMailSpider", "OutlookMailboxSpider"]
