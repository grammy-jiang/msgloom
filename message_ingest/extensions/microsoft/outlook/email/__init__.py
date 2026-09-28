"""Outlook Mail Scrapy lifecycle extensions."""

from .checkpoint import OutlookDeltaCheckpointExtension
from .status import OutlookCrawlStatusExtension

__all__ = ["OutlookCrawlStatusExtension", "OutlookDeltaCheckpointExtension"]
