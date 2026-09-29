"""Promote complete Contacts snapshots and custom-folder delta at clean idle."""

from scrapy import signals
from scrapy.exceptions import CloseSpider, NotConfigured

from message_ingest.catalog.stores.microsoft.contacts import ContactsStore
from message_ingest.extensions.catalog import CatalogService
from message_ingest.spiders.microsoft.contacts.delta import MicrosoftContactsDeltaSpider
from message_ingest.spiders.microsoft.contacts.snapshot import (
    MicrosoftContactsSyncSpider,
)


class ContactsSnapshotPromotionExtension:
    """Publish snapshot presence only after all resource writes and requests drain."""

    def __init__(self, crawler) -> None:
        self.crawler = crawler
        self._handled = False

    @classmethod
    def from_crawler(cls, crawler):
        """Enable only for authoritative Contacts snapshot sync."""
        if not crawler.settings.getbool("MSGLOOM_CONTACTS_SNAPSHOT_PROMOTION_ENABLED"):
            raise NotConfigured("Contacts snapshot promotion disabled")
        if not crawler.settings.getbool("MSGLOOM_CATALOG_ENABLED"):
            raise NotConfigured("Contacts snapshot promotion requires catalog")
        extension = cls(crawler)
        crawler.signals.connect(extension.spider_idle, signal=signals.spider_idle)
        return extension

    def spider_idle(self, spider) -> None:
        """Fail closed unless durable collection completions prove a full snapshot."""
        if not isinstance(spider, MicrosoftContactsSyncSpider) or self._handled:
            return
        self._handled = True
        prefix = "msgloom/crawl/contacts/snapshot/"
        service = CatalogService.from_crawler(self.crawler)
        if spider.run_failed or service.write_lock.locked():
            self.crawler.stats.set_value(prefix + "outcome", "skipped")
            spider.mark_run_failed("contacts_snapshot_incomplete")
            raise CloseSpider(reason="contacts_snapshot_incomplete")
        store = ContactsStore(
            service.catalog, source_id=self.crawler.settings["MSGLOOM_SOURCE_ID"]
        )
        try:
            counts = store.promote_snapshot(spider.run_id)
        except Exception as exc:
            self.crawler.stats.set_value(prefix + "outcome", "error")
            spider.mark_run_failed("contacts_snapshot_promotion_failed")
            spider.logger.error(
                "Contacts snapshot promotion failed: error_type=%s",
                type(exc).__name__,
            )
            raise CloseSpider(reason="contacts_snapshot_promotion_failed") from exc
        self.crawler.stats.set_value(prefix + "outcome", "committed")
        self.crawler.stats.inc_value(prefix + "commit_count")
        for name, value in counts.items():
            self.crawler.stats.set_value(prefix + name, value)


class ContactsDeltaCheckpointExtension:
    """Commit one custom-folder delta round only after clean native idle."""

    def __init__(self, crawler) -> None:
        self.crawler = crawler
        self._handled = False

    @classmethod
    def from_crawler(cls, crawler):
        """Enable only for explicit custom-folder Contacts delta."""
        if not crawler.settings.getbool("MSGLOOM_CONTACTS_DELTA_CHECKPOINT_ENABLED"):
            raise NotConfigured("Contacts delta checkpoint disabled")
        if not crawler.settings.getbool("MSGLOOM_CATALOG_ENABLED"):
            raise NotConfigured("Contacts delta checkpoint requires catalog")
        extension = cls(crawler)
        crawler.signals.connect(extension.spider_idle, signal=signals.spider_idle)
        return extension

    def spider_idle(self, spider) -> None:
        """Promote staged changes and opaque cursor only after terminal delta."""
        if not isinstance(spider, MicrosoftContactsDeltaSpider) or self._handled:
            return
        self._handled = True
        prefix = "msgloom/crawl/contacts/delta/checkpoint/"
        service = CatalogService.from_crawler(self.crawler)
        if (
            spider.run_failed
            or not spider.terminal_delta_seen
            or service.write_lock.locked()
        ):
            self.crawler.stats.set_value(prefix + "outcome", "skipped")
            spider.mark_run_failed("contacts_delta_incomplete")
            raise CloseSpider(reason="contacts_delta_incomplete")
        store = ContactsStore(
            service.catalog, source_id=self.crawler.settings["MSGLOOM_SOURCE_ID"]
        )
        try:
            checkpoint = store.promote_delta(
                folder_id=spider.folder_id,
                run_id=spider.run_id,
                base_revision=spider.base_revision,
            )
        except Exception as exc:
            self.crawler.stats.set_value(prefix + "outcome", "error")
            spider.mark_run_failed("contacts_delta_promotion_failed")
            spider.logger.error(
                "Contacts delta checkpoint promotion failed: error_type=%s",
                type(exc).__name__,
            )
            raise CloseSpider(reason="contacts_delta_promotion_failed") from exc
        self.crawler.stats.set_value(prefix + "outcome", "committed")
        self.crawler.stats.set_value(prefix + "revision", checkpoint.revision)
        self.crawler.stats.inc_value(prefix + "commit_count")


__all__ = ["ContactsDeltaCheckpointExtension", "ContactsSnapshotPromotionExtension"]
