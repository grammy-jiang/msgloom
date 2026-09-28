"""Public Outlook Calendar spiders."""

from .delta import OutlookCalendarDeltaSpider
from .discover import OutlookCalendarDiscoverSpider
from .full import OutlookCalendarFullSpider
from .window import OutlookCalendarWindowSpider

__all__ = [
    "OutlookCalendarDeltaSpider",
    "OutlookCalendarDiscoverSpider",
    "OutlookCalendarFullSpider",
    "OutlookCalendarWindowSpider",
]
