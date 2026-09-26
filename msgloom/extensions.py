from __future__ import annotations

import logging

from scrapy import signals
from scrapy.exceptions import CloseSpider, NotConfigured

from msgloom.checkpoints import OutlookDeltaCheckpointStore

logger = logging.getLogger(__name__)


class OutlookDeltaCheckpointExtension:
    """Commit a complete delta round only after Scrapy becomes fully idle."""

    def __init__(self, crawler) -> None:
        self.crawler = crawler
        self.store = OutlookDeltaCheckpointStore.from_crawler(crawler)
        self._handled_run_ids: set[str] = set()

    @classmethod
    def from_crawler(cls, crawler):
        if not crawler.settings.getbool("MSGLOOM_DELTA_CHECKPOINT_ENABLED"):
            raise NotConfigured("Outlook delta checkpoint extension disabled")
        if not crawler.settings.getbool("MSGLOOM_CATALOG_ENABLED"):
            raise NotConfigured("Delta checkpoints require the SQLAlchemy catalog")
        extension = cls(crawler)
        crawler.signals.connect(extension.spider_idle, signal=signals.spider_idle)
        crawler.signals.connect(extension.item_error, signal=signals.item_error)
        crawler.signals.connect(extension.item_dropped, signal=signals.item_dropped)
        return extension

    def item_error(self, item, response, spider, failure) -> None:
        self.crawler.stats.inc_value("msgloom/persistence/item_error_count")

    def item_dropped(self, item, response, spider, exception) -> None:
        self.crawler.stats.inc_value("msgloom/persistence/item_dropped_count")

    def spider_idle(self, spider) -> None:
        if spider.name != "outlook_mail" or getattr(spider, "sync_mode", "") != "delta":
            return
        run_id = getattr(spider, "run_id", "")
        if not run_id or run_id in self._handled_run_ids:
            return
        self._handled_run_ids.add(run_id)

        stats = self.crawler.stats
        started = stats.get_value("msgloom/crawl/delta/folder_started_count", 0)
        completed = stats.get_value("msgloom/crawl/delta/folder_completed_count", 0)
        failures = stats.get_value("msgloom/crawl/failure_count", 0)
        spider_errors = stats.get_value("spider_exceptions/count", 0)
        item_errors = stats.get_value("msgloom/persistence/item_error_count", 0)
        item_drops = stats.get_value("msgloom/persistence/item_dropped_count", 0)
        candidates = self.store.load_candidates(run_id)
        folder_inventory_complete = bool(
            stats.get_value("msgloom/crawl/delta/folder_inventory_completed", False)
        )
        reconcile_complete = bool(
            stats.get_value("msgloom/crawl/reconcile/completed", False)
        )

        if (
            failures
            or spider_errors
            or item_errors
            or item_drops
            or not folder_inventory_complete
            or not reconcile_complete
            or started != completed
            or completed != len(candidates)
        ):
            stats.inc_value("msgloom/checkpoint/commit_skipped_count")
            stats.set_value("msgloom/checkpoint/expected_folder_count", started)
            stats.set_value("msgloom/checkpoint/candidate_folder_count", len(candidates))
            raise CloseSpider(reason="delta_incomplete")

        try:
            committed = self.store.commit(run_id)
        except Exception as exc:
            stats.inc_value("msgloom/checkpoint/commit_error_count")
            logger.exception("Unable to commit Outlook delta checkpoints")
            raise CloseSpider(reason="checkpoint_commit_failed") from exc

        stats.inc_value("msgloom/checkpoint/commit_count")
        stats.set_value("msgloom/checkpoint/committed_folder_count", committed)
