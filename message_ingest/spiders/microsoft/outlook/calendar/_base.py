"""Calendar provider acquisition bound to msgloom lifecycle and targeting."""

from message_ingest.spiders.microsoft.outlook._mailbox import OutlookMailboxSpider
from microsoft_graph.scrapy.outlook.calendar import (
    OutlookCalendarSpider as GraphCalendar,
)


class OutlookCalendarSpider(GraphCalendar, OutlookMailboxSpider):
    """Use reusable Calendar scopes with msgloom mailbox and evidence behavior."""


__all__ = ["OutlookCalendarSpider"]
