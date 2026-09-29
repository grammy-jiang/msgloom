"""Promote complete OneDrive delta rounds only after native idle."""

from __future__ import annotations

import asyncio
import logging

from scrapy import signals
from scrapy.exceptions import CloseSpider, DontCloseSpider, NotConfigured
from scrapy.utils.defer import deferred_from_coro
from twisted.python.failure import Failure

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
        self._promotion_started = False
        self._promotion_done = False
        self._promotion_error: Failure | None = None

    @classmethod
    def from_crawler(cls, crawler):
        """Enable only for the explicit OneDrive delta spider setting."""
        if not crawler.settings.getbool("MSGLOOM_ONEDRIVE_DELTA_CHECKPOINT_ENABLED"):
            raise NotConfigured("OneDrive delta checkpoint extension disabled")
        extension = cls(crawler)
        crawler.signals.connect(extension.spider_idle, signal=signals.spider_idle)
        return extension

    def spider_idle(self, spider) -> None:
        """Gate promotion on durable completion and await it under the write lock."""
        if not isinstance(spider, MicrosoftOneDriveDeltaSpider):
            return
        if self._promotion_error is not None:
            spider.mark_run_failed("onedrive_checkpoint_promotion_failed")
            raise CloseSpider(reason="onedrive_checkpoint_promotion_failed")
        if self._promotion_done:
            return
        if self._promotion_started:
            raise DontCloseSpider

        if spider.run_failed or not spider.terminal_delta_seen:
            spider.mark_run_failed("onedrive_delta_incomplete")
            self.crawler.stats.set_value(
                "msgloom/onedrive/checkpoint/outcome", "skipped"
            )
            raise CloseSpider(reason="onedrive_delta_incomplete")

        service = CatalogService.from_crawler(self.crawler)
        store = OneDriveStore(
            service.catalog,
            source_id=self.crawler.settings["MSGLOOM_SOURCE_ID"],
        )
        candidate = store.load_candidate(
            run_id=spider.run_id, base_revision=spider.base_revision
        )
        if candidate is None:
            spider.mark_run_failed("onedrive_delta_candidate_missing")
            self.crawler.stats.set_value(
                "msgloom/onedrive/checkpoint/outcome", "skipped"
            )
            raise CloseSpider(reason="onedrive_delta_candidate_missing")

        self._promotion_started = True
        deferred = deferred_from_coro(self._promote(spider, service, store))
        deferred.addCallbacks(self._promotion_succeeded, self._promotion_failed)
        raise DontCloseSpider

    async def _promote(self, spider, service: CatalogService, store: OneDriveStore):
        """Serialize the idle-time SQL transaction with every pipeline write."""
        async with service.write_lock:
            return await asyncio.to_thread(
                store.promote_checkpoint,
                run_id=spider.run_id,
                base_revision=spider.base_revision,
                reset_attempt=spider.reset_attempt or None,
            )

    def _promotion_succeeded(self, checkpoint):
        """Publish bounded success facts after the awaited transaction returns."""
        self._promotion_done = True
        self.crawler.stats.set_value("msgloom/onedrive/checkpoint/outcome", "committed")
        self.crawler.stats.set_value(
            "msgloom/onedrive/checkpoint/revision", checkpoint.revision
        )
        self.crawler.stats.inc_value("msgloom/onedrive/checkpoint/commit_count")
        logger.info(
            "OneDrive delta checkpoint committed: revision=%s",
            checkpoint.revision,
            extra={"spider": self.crawler.spider},
        )
        return checkpoint

    def _promotion_failed(self, failure: Failure):
        """Retain the failure for the next idle pass to close deterministically."""
        self._promotion_error = failure
        self.crawler.stats.set_value("msgloom/onedrive/checkpoint/outcome", "error")
        self.crawler.stats.inc_value("msgloom/onedrive/checkpoint/error_count")
        logger.error(
            "OneDrive checkpoint promotion failed: error_type=%s",
            failure.type.__name__ if failure.type else "UnknownError",
            extra={"spider": self.crawler.spider},
        )


__all__ = ["OneDriveDeltaCheckpointExtension"]
