"""Discover the signed-in drive and its root children without recursion."""

from collections.abc import AsyncIterator, Iterator
from typing import Any

from scrapy.http import TextResponse

from message_ingest.items.microsoft.onedrive import OneDriveDriveItem, OneDriveItem
from microsoft_graph.protocol import GraphCollectionPage

from ._base import OneDriveSpider
from ._handoff import completion, discovery_scope


class MicrosoftOneDriveDiscoverSpider(OneDriveSpider):
    """Acquire root metadata as work context; fetch no file bodies."""

    name = "microsoft_onedrive_discover"

    def __init__(self, *args, page_size: str = "100", **kwargs) -> None:
        """Validate the collection page bound before scheduling requests."""
        super().__init__(*args, **kwargs)
        self.handoff_drive_id = None
        self.handoff_drive = None
        self.handoff_completion = None
        self.page_size = self._bounded_int(
            page_size, name="page_size", minimum=1, maximum=1000
        )

    async def start(self) -> AsyncIterator[Any]:
        """Read the signed-in account's drive before enumerating its root."""
        yield self._request(
            self.drive_path(),
            callback=self.parse_drive,
            purpose="onedrive-drive",
            cb_kwargs={},
        )

    def parse_drive(self, response: TextResponse, *, purpose: str) -> Iterator[Any]:
        """Emit drive evidence and metadata, then request root children."""
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        drive = OneDriveDriveItem.from_graph(
            response.json(),
            observed_at=evidence.observed_at,
            evidence_id=evidence.evidence_id,
            run_id=self.run_id,
        )
        yield drive
        self.handoff_drive_id = drive.id
        self.handoff_drive = completion(self, evidence, discovery_scope(self))
        self.crawler.stats.inc_value("msgloom/crawl/onedrive/discover/drive_count")
        yield self._request(
            self.root_children_path(page_size=self.page_size),
            callback=self.parse_children,
            purpose="onedrive-root-children-page",
            cb_kwargs={},
        )

    def parse_children(self, response: TextResponse, *, purpose: str) -> Iterator[Any]:
        """
        Emit root observations after evidence; follow only opaque pages.

        @url data:application/json,%7B%22value%22%3A%5B%7B%22id%22%3A%22root-child%22%7D%5D%7D
        @cb_kwargs {"purpose": "onedrive-root-children-page"}
        @returns items 2 2
        @returns requests 0 0
        """
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        page = GraphCollectionPage.from_payload(
            response.json(), context="OneDrive root children", validate_links=False
        )
        self.crawler.stats.inc_value("msgloom/crawl/onedrive/discover/page_count")
        for raw in page.values:
            yield OneDriveItem.from_graph(
                raw,
                observed_at=evidence.observed_at,
                evidence_id=evidence.evidence_id,
                run_id=self.run_id,
            )
            self.crawler.stats.inc_value("msgloom/crawl/onedrive/discover/item_count")
        if next_link := page.next_link:
            yield self._request(
                next_link,
                callback=self.parse_children,
                purpose=purpose,
                cb_kwargs={},
                verbatim_url=True,
            )
        else:
            self.handoff_completion = completion(self, evidence, discovery_scope(self))
