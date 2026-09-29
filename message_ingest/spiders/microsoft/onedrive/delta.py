"""Traverse OneDrive hierarchy metadata with opaque, durable delta cursors."""

import asyncio
from collections.abc import AsyncIterator, Iterator
from typing import Any

from scrapy.http import TextResponse
from scrapy.settings import BaseSettings

from message_ingest.catalog.stores.microsoft.onedrive import OneDriveStore
from message_ingest.extensions.catalog import CatalogService
from message_ingest.items.microsoft.onedrive import (
    OneDriveDeltaCheckpointCandidateItem,
    OneDriveItem,
)
from microsoft_graph.protocol import GraphDeltaPage

from ._base import OneDriveSpider


class MicrosoftOneDriveDeltaSpider(OneDriveSpider):
    """
    Capture metadata changes before proposing a new terminal checkpoint.

    The lifecycle extension promotes a persisted candidate only at clean idle.
    An expired cursor fails through the ordinary errback; this slice never
    discards a checkpoint or starts an implicit reset. JOBDIR is unsupported.
    """

    name = "microsoft_onedrive_delta"

    def __init__(self, *args, page_size: str = "100", **kwargs) -> None:
        """Start a fresh run with no terminal completion or cursor revision."""
        super().__init__(*args, **kwargs)
        self.page_size = self._bounded_int(
            page_size, name="page_size", minimum=1, maximum=1000
        )
        self.base_revision: int | None = None
        self.terminal_delta_seen = False

    @classmethod
    def update_settings(cls, settings: BaseSettings) -> None:
        """Enable the OneDrive-specific idle checkpoint gate."""
        super().update_settings(settings)
        settings.set(
            "MSGLOOM_ONEDRIVE_DELTA_CHECKPOINT_ENABLED", True, priority="spider"
        )

    async def start(self) -> AsyncIterator[Any]:
        """Load a committed opaque cursor, or enumerate the first hierarchy."""
        checkpoint = None
        if self.crawler.settings.getbool("MSGLOOM_CATALOG_ENABLED"):
            service = CatalogService.from_crawler(self.crawler)
            store = OneDriveStore(
                service.catalog, source_id=self.crawler.settings["MSGLOOM_SOURCE_ID"]
            )
            checkpoint = await asyncio.to_thread(store.load_checkpoint)
        if checkpoint is not None:
            self.base_revision = checkpoint.revision
        yield self._request(
            checkpoint.delta_link
            if checkpoint
            else self.delta_path(page_size=self.page_size),
            callback=self.parse_delta,
            purpose="onedrive-delta-page",
            cb_kwargs={},
            verbatim_url=checkpoint is not None,
            dont_cache=True,
        )

    def parse_delta(self, response: TextResponse, *, purpose: str) -> Iterator[Any]:
        """Emit evidence, each entry including tombstones, then cursor work."""
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        page = GraphDeltaPage.from_payload(
            response.json(),
            context="OneDrive delta",
            strict=False,
            validate_links=False,
        )
        self.crawler.stats.inc_value("msgloom/crawl/onedrive/delta/page_count")
        for raw in page.values:
            yield OneDriveItem.from_graph(
                raw,
                observed_at=evidence.observed_at,
                evidence_id=evidence.evidence_id,
                run_id=self.run_id,
            )
            self.crawler.stats.inc_value("msgloom/crawl/onedrive/delta/item_count")
        page.validate_state()
        if next_link := page.next_link:
            yield self._request(
                next_link,
                callback=self.parse_delta,
                purpose=purpose,
                cb_kwargs={},
                verbatim_url=True,
                dont_cache=True,
            )
            return
        delta_link = page.delta_link
        if delta_link is None:
            raise ValueError("OneDrive terminal delta requires a deltaLink")
        self.terminal_delta_seen = True
        yield OneDriveDeltaCheckpointCandidateItem(
            delta_link=delta_link,
            base_revision=self.base_revision,
            observed_at=evidence.observed_at,
            evidence_id=evidence.evidence_id,
            run_id=self.run_id,
        )
