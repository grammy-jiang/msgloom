"""Promote complete OneDrive delta rounds only after native idle."""

from __future__ import annotations

import logging
from typing import NoReturn

from scrapy import signals
from scrapy.exceptions import CloseSpider, NotConfigured

from message_ingest.catalog.stores.microsoft.onedrive import OneDriveStore
from message_ingest.extensions.catalog import CatalogService
from message_ingest.spiders.microsoft.onedrive.delta import (
    MicrosoftOneDriveDeltaSpider,
)

logger = logging.getLogger(__name__)


class OneDriveDeltaCheckpointExtension:
    """Promote one terminal cursor after requests and item pipelines are idle."""

    def __init__(self, crawler) -> None:
        self.crawler = crawler
        self._promotion_done = False

    @classmethod
    def from_crawler(cls, crawler):
        """Enable only for the explicit OneDrive delta spider setting."""
        if not crawler.settings.getbool("MSGLOOM_ONEDRIVE_DELTA_CHECKPOINT_ENABLED"):
            raise NotConfigured("OneDrive delta checkpoint extension disabled")
        extension = cls(crawler)
        crawler.signals.connect(extension.spider_idle, signal=signals.spider_idle)
        return extension

    def spider_idle(self, spider) -> None:
        """
        Promote synchronously after Scrapy proves pipeline work is idle.

        Native idle excludes pending item-pipeline work. The shared asyncio
        write lock must therefore be free; synchronous promotion then remains
        owned by this signal handler and must finish before pipeline shutdown
        can dispose the shared catalog.
        """
        if not isinstance(spider, MicrosoftOneDriveDeltaSpider):
            return
        if self._promotion_done:
            return
        if spider.run_failed or not spider.terminal_delta_seen:
            spider.mark_run_failed("onedrive_delta_incomplete")
            self.crawler.stats.set_value(
                "msgloom/onedrive/checkpoint/outcome", "skipped"
            )
            raise CloseSpider(reason="onedrive_delta_incomplete")

        service = CatalogService.from_crawler(self.crawler)
        if service.write_lock.locked():
            self._promotion_failed(spider, RuntimeError("catalog write lock is held"))
        store = OneDriveStore(
            service.catalog,
            source_id=self.crawler.settings["MSGLOOM_SOURCE_ID"],
        )
        try:
            candidate = store.load_candidate(
                run_id=spider.run_id, base_revision=spider.base_revision
            )
        # This lifecycle boundary must convert ordinary persistence failures
        # into one bounded logical-run failure instead of leaking them through
        # Scrapy's idle signal.
        except Exception as exc:  # noqa: BLE001
            self._promotion_failed(spider, exc)
        if candidate is None:
            spider.mark_run_failed("onedrive_delta_candidate_missing")
            self.crawler.stats.set_value(
                "msgloom/onedrive/checkpoint/outcome", "skipped"
            )
            raise CloseSpider(reason="onedrive_delta_candidate_missing")

        try:
            checkpoint = store.promote_checkpoint(
                run_id=spider.run_id,
                base_revision=spider.base_revision,
                reset_attempt=spider.reset_attempt or None,
            )
        except Exception as exc:  # noqa: BLE001
            self._promotion_failed(spider, exc)

        self._promotion_done = True
        self.crawler.stats.set_value("msgloom/onedrive/checkpoint/outcome", "committed")
        self.crawler.stats.set_value(
            "msgloom/onedrive/checkpoint/revision", checkpoint.revision
        )
        self.crawler.stats.inc_value("msgloom/onedrive/checkpoint/commit_count")
        logger.info(
            "OneDrive delta checkpoint committed: revision=%s",
            checkpoint.revision,
            extra={"spider": spider},
        )

    def _promotion_failed(self, spider, error: Exception) -> NoReturn:
        """Fail the run in the same lifecycle callback that attempted promotion."""
        spider.mark_run_failed("onedrive_checkpoint_promotion_failed")
        self.crawler.stats.set_value("msgloom/onedrive/checkpoint/outcome", "error")
        self.crawler.stats.inc_value("msgloom/onedrive/checkpoint/error_count")
        logger.error(
            "OneDrive checkpoint promotion failed: error_type=%s",
            type(error).__name__,
            extra={"spider": spider},
        )
        raise CloseSpider(reason="onedrive_checkpoint_promotion_failed") from error


__all__ = ["OneDriveDeltaCheckpointExtension"]
