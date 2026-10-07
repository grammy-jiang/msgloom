"""Public Outlook email spiders."""

from .delta import OutlookDeltaSpider
from .discover import OutlookDiscoverSpider
from .folder_delta import OutlookFolderDeltaSpider
from .full import OutlookFullSpider

__all__ = [
    "OutlookDeltaSpider",
    "OutlookDiscoverSpider",
    "OutlookFolderDeltaSpider",
    "OutlookFullSpider",
]
