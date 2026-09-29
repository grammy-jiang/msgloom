"""Promote OneDrive terminal cursors only after clean Scrapy idle."""

from scrapy import signals
from scrapy.exceptions import CloseSpider, NotConfigured

from message_ingest.catalog.stores.microsoft.onedrive import OneDriveStore
from message_ingest.extensions.catalog import CatalogService
from message_ingest.spiders.microsoft.onedrive.delta import MicrosoftOneDriveDeltaSpider


class OneDriveDeltaCheckpointExtension:
    """
    Use native idle to gate one source/run candidate after completed writes.

    Scrapy 2.19 excludes pending requests, callbacks, and item pipeline work
    from idle. The shared integrity extension records callback/item failures;
    the Spider marks terminal request failures. No candidate is promoted on
    interrupted shutdown, and a candidate alone never proves run completion.
    """

    def __init__(self, crawler) -> None:
        self.crawler = crawler
        self._handled = False

    @classmethod
    def from_crawler(cls, crawler):
        """Enable only for OneDrive delta with catalog persistence enabled."""
        if not crawler.settings.getbool("MSGLOOM_ONEDRIVE_DELTA_CHECKPOINT_ENABLED"):
            raise NotConfigured("OneDrive delta checkpoints disabled")
        if not crawler.settings.getbool("MSGLOOM_CATALOG_ENABLED"):
            raise NotConfigured("OneDrive checkpoints require the SQL catalog")
        extension = cls(crawler)
        crawler.signals.connect(extension.spider_idle, signal=signals.spider_idle)
        return extension

    def spider_idle(self, spider) -> None:
        """Promote once after terminal completion; fail closed on any gap."""
        if not isinstance(spider, MicrosoftOneDriveDeltaSpider) or self._handled:
            return
        self._handled = True
        prefix = "msgloom/crawl/onedrive/delta/checkpoint/"
        service = CatalogService.from_crawler(self.crawler)
        if (
            spider.run_failed
            or not spider.terminal_delta_seen
            or service.write_lock.locked()
        ):
            self.crawler.stats.set_value(prefix + "outcome", "skipped")
            spider.mark_run_failed("onedrive_delta_incomplete")
            raise CloseSpider(reason="onedrive_delta_incomplete")
        store = OneDriveStore(
            service.catalog, source_id=self.crawler.settings["MSGLOOM_SOURCE_ID"]
        )
        try:
            # This handler is synchronous. At native idle no item write holds
            # the shared lock, and no new work can interleave this transaction.
            checkpoint = store.promote_checkpoint(
                run_id=spider.run_id, base_revision=spider.base_revision
            )
        except Exception as exc:
            self.crawler.stats.set_value(prefix + "outcome", "error")
            spider.mark_run_failed("onedrive_checkpoint_commit_failed")
            spider.logger.error(
                "OneDrive checkpoint promotion failed: error_type=%s",
                type(exc).__name__,
            )
            raise CloseSpider(reason="onedrive_checkpoint_commit_failed") from exc
        self.crawler.stats.set_value(prefix + "outcome", "committed")
        self.crawler.stats.set_value(prefix + "revision", checkpoint.revision)
        self.crawler.stats.inc_value(prefix + "commit_count")
