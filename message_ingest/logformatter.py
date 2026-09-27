"""
Summarize acquisition events without dumping private message bodies into logs.
"""

from __future__ import annotations

import logging
from typing import Any

from scrapy.logformatter import LogFormatter, LogFormatterResult

from message_ingest.items import (
    AcquisitionFailureItem,
    OutlookAttachmentItem,
    OutlookDeltaCheckpointCandidateItem,
    OutlookMailDetailItem,
    OutlookMailFolderItem,
    OutlookMailItem,
    OutlookMailRemovalItem,
    OutlookMessageSurfaceItem,
    RawHttpEvidenceItem,
)


class MessageIngestLogFormatter(LogFormatter):
    """
    Keep Scrapy item logs useful without logging acquired message content.
    """

    def crawled(self, request, response, spider) -> LogFormatterResult:
        """
        Log response metadata without a URL that may contain mailbox IDs or
        cursor tokens.
        """
        return {
            "level": logging.DEBUG,
            "msg": "Crawled Graph response: status=%(status)s method=%(method)s purpose=%(purpose)s cached=%(cached)s",
            "args": {
                "status": response.status,
                "method": request.method,
                "purpose": request.cb_kwargs.get("purpose", "unknown"),
                "cached": "cached" in response.flags,
            },
        }

    def spider_error(self, failure, request, response, spider) -> LogFormatterResult:
        """
        Summarize a callback failure without formatting its acquired response
        body.
        """
        return {
            "level": logging.ERROR,
            "msg": "Spider error processing Graph request: method=%(method)s purpose=%(purpose)s",
            "args": {
                "method": request.method,
                "purpose": request.cb_kwargs.get("purpose", "unknown"),
            },
        }

    def download_error(
        self, failure, request, spider, errmsg=None
    ) -> LogFormatterResult:
        """Report a transport failure without arbitrary exception text."""
        error_type = failure.type.__name__ if failure.type else "UnknownError"
        return {
            "level": logging.ERROR,
            "msg": (
                "Error downloading Graph request: method=%(method)s "
                "purpose=%(purpose)s error_type=%(error_type)s"
            ),
            "args": {
                "method": request.method,
                "purpose": request.cb_kwargs.get("purpose", "unknown"),
                "error_type": error_type,
            },
        }

    def scraped(self, item: Any, response, spider) -> LogFormatterResult:
        """
        Replace Scrapy's default item repr with a bounded, field-selected
        summary.
        """
        return {
            "level": logging.DEBUG,
            "msg": "Scraped %(summary)s",
            "args": {"summary": self._summary(item)},
        }

    def dropped(self, item: Any, exception, response, spider) -> LogFormatterResult:
        """
        Honor Scrapy's configured drop level while avoiding full item contents.
        """
        level = getattr(exception, "log_level", None)
        if level is None:
            level = spider.crawler.settings["DEFAULT_DROPITEM_LOG_LEVEL"]
        if isinstance(level, str):
            level = getattr(logging, level)
        return {
            "level": level,
            "msg": "Dropped %(summary)s: error_type=%(error_type)s",
            "args": {
                "summary": self._summary(item),
                "error_type": type(exception).__name__,
            },
        }

    def item_error(self, item: Any, exception, response, spider) -> LogFormatterResult:
        """
        Record persistence failure without exposing the failed item payload.
        """
        return {
            "level": logging.ERROR,
            "msg": "Error processing %(summary)s",
            "args": {"summary": self._summary(item)},
        }

    @staticmethod
    def _summary(item: Any) -> str:
        """
        Allowlist useful identifiers per item type; never fall back to an
        arbitrary item repr.
        """
        if isinstance(item, RawHttpEvidenceItem):
            return (
                f"RawHttpEvidenceItem(purpose={item.purpose!r}, "
                f"status={item.response_status!r}, origin={item.origin!r}, "
                f"evidence_id={item.evidence_id!r})"
            )
        if isinstance(item, OutlookMailItem):
            return f"OutlookMailItem(message_id={item.message_id!r})"
        if isinstance(item, OutlookMailDetailItem):
            return f"OutlookMailDetailItem(message_id={item.message_id!r})"
        if isinstance(item, OutlookAttachmentItem):
            return (
                f"OutlookAttachmentItem(message_id={item.message_id!r}, "
                f"attachment_id={item.attachment_id!r})"
            )
        if isinstance(item, OutlookMailFolderItem):
            return f"OutlookMailFolderItem(folder_id={item.folder_id!r})"
        if isinstance(item, OutlookMailRemovalItem):
            return (
                f"OutlookMailRemovalItem(message_id={item.message_id!r}, "
                f"folder_id={item.folder_id!r})"
            )
        if isinstance(item, OutlookMessageSurfaceItem):
            return (
                f"OutlookMessageSurfaceItem(message_id={item.message_id!r}, "
                f"surface={item.surface!r}, status={item.status!r})"
            )
        if isinstance(item, OutlookDeltaCheckpointCandidateItem):
            return f"OutlookDeltaCheckpointCandidateItem(folder_id={item.folder_id!r})"
        if isinstance(item, AcquisitionFailureItem):
            return (
                f"AcquisitionFailureItem(purpose={item.purpose!r}, "
                f"error_type={item.error_type!r})"
            )
        return type(item).__name__
