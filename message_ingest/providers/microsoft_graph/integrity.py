"""Track Microsoft Graph run integrity across Scrapy failure signals."""

from __future__ import annotations

from scrapy import signals

from message_ingest.providers.microsoft_graph.spider import MicrosoftGraphSpider


class MicrosoftGraphIntegrityExtension:
    """
    Mark Graph logical runs failed when errors bypass request errbacks.

    Request/download terminal failures are marked by
    :class:`~message_ingest.providers.microsoft_graph.spider.MicrosoftGraphSpider`.
    Callback exceptions, item-processing exceptions, and dropped items arrive
    through Scrapy signals instead. This extension records only the integrity
    fact; resource-specific checkpoint and status components still own their
    completion decisions and reporting.
    """

    def __init__(self, crawler) -> None:
        """Keep the crawler only for native signal registration symmetry."""
        self.crawler = crawler

    @classmethod
    def from_crawler(cls, crawler):
        """Register the failure signals for all Microsoft Graph resources."""
        extension = cls(crawler)
        crawler.signals.connect(extension.spider_error, signal=signals.spider_error)
        crawler.signals.connect(extension.item_error, signal=signals.item_error)
        crawler.signals.connect(extension.item_dropped, signal=signals.item_dropped)
        return extension

    @staticmethod
    def spider_error(spider, **_kwargs) -> None:
        """Mark callback/start exceptions that do not invoke request errbacks."""
        if isinstance(spider, MicrosoftGraphSpider):
            spider.mark_run_failed("spider_error")

    @staticmethod
    def item_error(spider, **_kwargs) -> None:
        """Mark item-processing failures without owning a second counter."""
        if isinstance(spider, MicrosoftGraphSpider):
            spider.mark_run_failed("item_error")

    @staticmethod
    def item_dropped(spider, **_kwargs) -> None:
        """Mark dropped acquisition items as an integrity failure."""
        if isinstance(spider, MicrosoftGraphSpider):
            spider.mark_run_failed("item_dropped")
