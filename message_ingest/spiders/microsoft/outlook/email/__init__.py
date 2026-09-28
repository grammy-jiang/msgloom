"""Public Outlook email spiders."""

from .delta import OutlookDeltaSpider
from .discover import OutlookDiscoverSpider
from .full import OutlookFullSpider

__all__ = ["OutlookDeltaSpider", "OutlookDiscoverSpider", "OutlookFullSpider"]
