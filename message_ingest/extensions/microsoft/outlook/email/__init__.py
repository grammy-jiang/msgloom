"""Outlook Mail Scrapy lifecycle extensions."""

from .checkpoint import OutlookDeltaCheckpointExtension
from .folder_checkpoint import OutlookFolderDeltaCheckpointExtension
from .status import OutlookCrawlStatusExtension

__all__ = [
    "OutlookCrawlStatusExtension",
    "OutlookDeltaCheckpointExtension",
    "OutlookFolderDeltaCheckpointExtension",
]
