"""Discover Outlook message metadata through Graph list pagination."""

from __future__ import annotations

import scrapy
from scrapy.http import TextResponse

from microsoft_graph.protocol import GraphCollectionPage

from ._base import OutlookMailCollectionSpider


class OutlookDiscoverSpider(OutlookMailCollectionSpider):
    """Discover message metadata across a mailbox or one folder."""

    name = "outlook_discover"

    def __init__(
        self,
        *args,
        folder: str = "",
        page_size: str = "25",
        max_pages: str = "0",
        **kwargs,
    ) -> None:
        """
        Validate list pagination limits; zero ``max_pages`` means unlimited
        discovery.
        """
        super().__init__(*args, **kwargs)
        self.folder = folder
        self.page_size = self._bounded_int(
            page_size, name="page_size", minimum=1, maximum=1000
        )
        self.max_pages = self._bounded_int(max_pages, name="max_pages", minimum=0)

    async def start(self):
        """
        Start the mailbox or folder list using the same discovery field
        selection.
        """
        self.logger.info(
            "Starting Outlook discovery crawl: scope=%s page_size=%s max_pages=%s",
            "folder" if self.folder else "mailbox",
            self.page_size,
            self.max_pages,
        )
        self.crawler.stats.set_value("msgloom/crawl/mode", "discovery")
        self.crawler.stats.set_value("msgloom/crawl/run_id", self.run_id)
        self.crawler.stats.set_value(
            "msgloom/crawl/discovery/pagination_exhausted", False
        )
        self.crawler.stats.set_value(
            "msgloom/crawl/discovery/scope",
            "folder" if self.folder else "mailbox",
        )
        self.crawler.stats.set_value(
            "msgloom/crawl/discovery/page_size", self.page_size
        )
        self.crawler.stats.set_value(
            "msgloom/crawl/discovery/max_pages", self.max_pages
        )

        path = self.messages_path(
            folder_id=self.folder,
            fields=self.discovery_fields,
            order_by="receivedDateTime desc",
            page_size=self.page_size,
        )
        yield self._message_list_request(f"{self.graph_root}{path}", page_number=1)

    def parse(
        self,
        response: TextResponse,
        *,
        purpose: str = "message-list",
        page_number: int = 1,
    ):
        """
        Parse one Graph message-list page.

        @url data:application/json,%7B%22value%22%3A%5B%7B%22id%22%3A%22m1%22%7D%5D%7D
        @returns items 2 2
        @returns requests 0 0
        """
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        page = GraphCollectionPage.from_payload(
            response.json(),
            missing_value_empty=True,
            empty_links_absent=True,
            validate_links=False,
        )
        messages = page.values
        self.logger.debug(
            "Processed Outlook message-list page: page=%s messages=%s cached=%s",
            page_number,
            len(messages),
            "cached" in response.flags,
        )
        self.crawler.stats.inc_value("msgloom/crawl/discovery/page_count")
        self.crawler.stats.inc_value(
            "msgloom/crawl/discovery/message_count", count=len(messages)
        )
        yield from (
            self._message_item(
                message,
                response.url,
                evidence.observed_at,
                observation_kind="discovery",
                evidence_id=evidence.evidence_id,
            )
            for message in messages
        )

        next_link = page.next_link
        if not next_link:
            self.crawler.stats.set_value(
                "msgloom/crawl/discovery/pagination_exhausted", True
            )
            self.logger.info(
                "Outlook discovery traversal complete: pages=%s messages=%s",
                self.crawler.stats.get_value("msgloom/crawl/discovery/page_count", 0),
                self.crawler.stats.get_value(
                    "msgloom/crawl/discovery/message_count", 0
                ),
            )
            return
        if self.max_pages and page_number >= self.max_pages:
            self.crawler.stats.inc_value("msgloom/crawl/discovery/truncated_count")
            self.logger.warning(
                "Outlook discovery stopped by explicit max_pages limit: page=%s max_pages=%s",
                page_number,
                self.max_pages,
            )
            return
        self.crawler.stats.inc_value("msgloom/crawl/discovery/continuation_count")
        yield self._message_list_request(
            next_link,
            page_number=page_number + 1,
            verbatim_url=True,
        )

    def _message_list_request(
        self,
        url: str,
        *,
        page_number: int,
        verbatim_url: bool = False,
    ) -> scrapy.Request:
        """
        Carry page position in callback arguments, not scheduler metadata.
        """
        return self._request(
            url,
            callback=self.parse,
            purpose="message-list",
            cb_kwargs={"page_number": page_number},
            verbatim_url=verbatim_url,
        )
