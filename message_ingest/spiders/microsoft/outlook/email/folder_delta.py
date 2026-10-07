"""Incrementally track Outlook Mail folder lifecycle changes."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Any

import scrapy
from scrapy.http import TextResponse
from scrapy.settings import BaseSettings
from twisted.python.failure import Failure

from message_ingest.items.acquisition import AcquisitionFailureItem
from message_ingest.items.microsoft.outlook.email import (
    OutlookFolderDeltaCheckpointCandidateItem,
    OutlookMailFolderItem,
    OutlookMailFolderRemovalItem,
)
from message_ingest.sync.microsoft.outlook.email.checkpoints import (
    OutlookFolderDeltaCheckpointStore,
)
from microsoft_graph.protocol import GraphDeltaPage

from ._base import OutlookMailSpider


class OutlookFolderDeltaSpider(OutlookMailSpider):
    """Track mailbox folder add/update/remove events with an opaque delta cursor."""

    name = "outlook_folder_delta"

    def __init__(self, *args, page_size: str = "25", **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.page_size = self._bounded_int(
            page_size,
            name="page_size",
            minimum=1,
            maximum=1000,
        )
        self._terminal_delta_seen = False

    @classmethod
    def update_settings(cls, settings: BaseSettings) -> None:
        settings.set("MSGLOOM_DELTA_CHECKPOINT_ENABLED", False, priority="spider")
        settings.set("MSGLOOM_FOLDER_DELTA_CHECKPOINT_ENABLED", True, priority="spider")
        settings.set("MSGLOOM_CRAWL_STATUS_ENABLED", False, priority="spider")
        settings.set(
            "ITEM_PIPELINES",
            {
                "message_ingest.pipelines.evidence.RawEvidencePipeline": 200,
                "message_ingest.acquisition.evidence_link.EvidenceLinkPipeline": 250,
                "message_ingest.pipelines.microsoft.outlook.email.OutlookMailPipeline": 300,
            },
            priority="spider",
        )
        super().update_settings(settings)

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        if crawler.settings.get("JOBDIR"):
            raise ValueError("Outlook folder delta does not support JOBDIR")
        return super().from_crawler(crawler, *args, **kwargs)

    async def start(self) -> AsyncIterator[Any]:
        self.crawler.stats.set_value("msgloom/crawl/mode", "folder_delta")
        self.crawler.stats.set_value("msgloom/crawl/run_id", self.run_id)
        store = OutlookFolderDeltaCheckpointStore.from_crawler(self.crawler)
        delta_link = await self._to_thread(store.get_delta_link)
        self.crawler.stats.set_value(
            "msgloom/crawl/folder_delta/checkpoint_loaded", bool(delta_link)
        )
        if delta_link:
            yield self._delta_request(
                delta_link,
                page_number=1,
                from_checkpoint=True,
                reset_count=0,
            )
            return
        yield self._initial_request(reset_count=0)

    async def _to_thread(self, func, *args):
        import asyncio

        return await asyncio.to_thread(func, *args)

    def parse_folder_delta(
        self,
        response: TextResponse,
        *,
        purpose: str,
        page_number: int,
        from_checkpoint: bool,
        reset_count: int,
    ) -> Iterator[Any]:
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        # Compatibility: missing value is empty and nextLink wins. Link
        # validation stays after observations, before scheduling/promotion.
        page = GraphDeltaPage.from_payload(
            response.json(),
            strict=False,
            missing_value_empty=True,
            empty_links_absent=True,
            validate_links=False,
        )
        values = page.values
        self.crawler.stats.inc_value("msgloom/crawl/folder_delta/page_count")
        self.crawler.stats.inc_value(
            "msgloom/crawl/folder_delta/change_count", count=len(values)
        )
        for folder in values:
            if not isinstance(folder, dict):
                raise TypeError("mailFolder delta entry must be a JSON object")
            folder_id = folder.get("id")
            if not isinstance(folder_id, str) or not folder_id:
                raise ValueError("mailFolder delta entry must contain a non-empty id")
            removed = folder.get("@removed")
            if isinstance(removed, dict):
                yield OutlookMailFolderRemovalItem(
                    folder_id=folder_id,
                    removed_reason=removed.get("reason"),
                    raw=folder,
                    observed_at=evidence.observed_at,
                    evidence_id=evidence.evidence_id,
                    run_id=self.run_id,
                )
                continue
            yield OutlookMailFolderItem.from_graph(
                folder,
                source_response_url=response.url,
                observed_at=evidence.observed_at,
                evidence_id=evidence.evidence_id,
                run_id=self.run_id,
            )

        if next_link := page.next_link:
            yield self._delta_request(
                next_link,
                page_number=page_number + 1,
                from_checkpoint=from_checkpoint,
                reset_count=reset_count,
            )
            return
        if delta_link := page.delta_link:
            self._terminal_delta_seen = True
            yield OutlookFolderDeltaCheckpointCandidateItem(
                run_id=self.run_id,
                delta_link=delta_link,
                observed_at=evidence.observed_at,
                evidence_id=evidence.evidence_id,
            )
            return

        self.mark_run_failed("folder_delta_state_missing")
        yield AcquisitionFailureItem(
            url=response.url,
            purpose="folder-delta",
            error_type="DeltaStateMissing",
            error_message=(
                "Microsoft Graph mailFolder delta response contained neither "
                "@odata.nextLink nor @odata.deltaLink"
            ),
            observed_at=evidence.observed_at,
            context={},
            evidence_id=evidence.evidence_id,
            run_id=self.run_id,
        )

    def errback(self, failure: Failure):
        callback_data = self._failure_request(failure).cb_kwargs
        evidence = self._failure_evidence_item(failure)
        yield evidence
        if (
            callback_data.get("purpose") == "folder-delta"
            and evidence.response_status == 410
        ):
            reset_count = int(callback_data.get("reset_count", 0))
            if reset_count < 1:
                self.crawler.stats.inc_value(
                    "msgloom/crawl/folder_delta/checkpoint_reset_count"
                )
                yield self._initial_request(reset_count=reset_count + 1)
                return
        yield self._request_failure_item(failure, evidence)

    def folder_delta_execution_snapshot(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "terminal_delta_seen": self._terminal_delta_seen,
            "run_failed": self.run_failed,
            "failure_reasons": set(self.failure_reasons),
        }

    def _initial_request(self, *, reset_count: int) -> scrapy.Request:
        path = self.mail_folder_delta_path(fields=self.folder_fields)
        return self._delta_request(
            f"{self.graph_root}{path}",
            page_number=1,
            from_checkpoint=False,
            reset_count=reset_count,
        )

    def _delta_request(
        self,
        url: str,
        *,
        page_number: int,
        from_checkpoint: bool,
        reset_count: int,
    ) -> scrapy.Request:
        return self._request(
            url,
            callback=self.parse_folder_delta,
            purpose="folder-delta",
            cb_kwargs={
                "page_number": page_number,
                "from_checkpoint": from_checkpoint,
                "reset_count": reset_count,
            },
            dont_cache=True,
            # Initial/reset paths are local; later pages and saved cursors
            # come from Graph. Their query bytes carry no application meaning.
            verbatim_url=page_number > 1 or from_checkpoint,
            prefer=f"odata.maxpagesize={self.page_size}",
        )


__all__ = ["OutlookFolderDeltaSpider"]
