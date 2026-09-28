"""Commit complete mailFolder delta rounds after Scrapy reaches idle."""

from __future__ import annotations

import logging

from scrapy import signals
from scrapy.exceptions import CloseSpider, NotConfigured

from message_ingest.spiders.microsoft.outlook.email.folder_delta import (
    OutlookFolderDeltaSpider,
)
from message_ingest.sync.microsoft.outlook.email.checkpoints import (
    OutlookFolderDeltaCheckpointStore,
)

logger = logging.getLogger(__name__)


class OutlookFolderDeltaCheckpointExtension:
    """Promote the mailbox-level folder delta cursor only for a clean round."""

    def __init__(self, crawler) -> None:
        self.crawler = crawler
        self.store = OutlookFolderDeltaCheckpointStore.from_crawler(crawler)
        self._handled_run_ids: set[str] = set()

    @classmethod
    def from_crawler(cls, crawler):
        if not crawler.settings.getbool("MSGLOOM_FOLDER_DELTA_CHECKPOINT_ENABLED"):
            raise NotConfigured("Outlook folder delta checkpoint extension disabled")
        if not crawler.settings.getbool("MSGLOOM_CATALOG_ENABLED"):
            raise NotConfigured("Folder delta checkpoints require the SQL catalog")
        extension = cls(crawler)
        crawler.signals.connect(extension.spider_idle, signal=signals.spider_idle)
        crawler.signals.connect(extension.spider_error, signal=signals.spider_error)
        crawler.signals.connect(extension.item_error, signal=signals.item_error)
        crawler.signals.connect(extension.item_dropped, signal=signals.item_dropped)
        return extension

    @staticmethod
    def _is_target(spider) -> bool:
        return isinstance(spider, OutlookFolderDeltaSpider)

    def spider_error(self, spider, **_kwargs) -> None:
        if self._is_target(spider):
            spider.mark_run_failed("spider_error")

    def item_error(self, spider, **_kwargs) -> None:
        if self._is_target(spider):
            spider.mark_run_failed("item_error")

    def item_dropped(self, spider, **_kwargs) -> None:
        if self._is_target(spider):
            spider.mark_run_failed("item_dropped")

    def spider_idle(self, spider) -> None:
        if not self._is_target(spider):
            return
        run_id = getattr(spider, "run_id", "")
        if not run_id or run_id in self._handled_run_ids:
            return
        self._handled_run_ids.add(run_id)

        snapshot = spider.folder_delta_execution_snapshot()
        candidate = self.store.get_candidate(run_id)
        if (
            snapshot["run_failed"]
            or not snapshot["terminal_delta_seen"]
            or candidate is None
        ):
            spider.mark_run_failed("folder_delta_incomplete")
            self.crawler.stats.set_value(
                "msgloom/folder_delta_checkpoint/outcome", "skipped"
            )
            raise CloseSpider(reason="folder_delta_incomplete")

        try:
            self.store.commit(run_id)
        except Exception as exc:
            spider.mark_run_failed("folder_delta_checkpoint_commit_failed")
            self.crawler.stats.set_value(
                "msgloom/folder_delta_checkpoint/outcome", "error"
            )
            logger.error(
                "Unable to commit Outlook folder delta checkpoint: error_type=%s",
                type(exc).__name__,
                extra={"spider": spider},
            )
            raise CloseSpider(reason="folder_delta_checkpoint_commit_failed") from exc
        self.crawler.stats.set_value(
            "msgloom/folder_delta_checkpoint/outcome", "committed"
        )


__all__ = ["OutlookFolderDeltaCheckpointExtension"]
