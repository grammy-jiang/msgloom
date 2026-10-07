"""Traverse OneDrive metadata delta with safe HTTP 410 full resynchronization."""

import asyncio
from collections.abc import AsyncIterator, Iterator
from typing import Any

from scrapy.http import TextResponse
from scrapy.settings import BaseSettings
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.python.failure import Failure

from message_ingest.catalog.stores.microsoft.onedrive import OneDriveStore
from message_ingest.extensions.catalog import CatalogService
from message_ingest.items.microsoft.onedrive import (
    OneDriveDeltaCheckpointCandidateItem,
    OneDriveDeltaResyncAttemptItem,
    OneDriveDeltaResyncObservationItem,
    OneDriveItem,
)
from microsoft_graph.protocol import GraphDeltaPage
from microsoft_graph.protocol.onedrive import onedrive_resync_location

from ._base import OneDriveSpider

_RESET_PRIVATE_HEADERS = frozenset(
    {"location", "content-location", "link", "refresh", "set-cookie"}
)


class MicrosoftOneDriveDeltaSpider(OneDriveSpider):
    """Capture normal delta directly and stage one post-410 full resync."""

    name = "microsoft_onedrive_delta"

    def __init__(self, *args, page_size: str = "100", **kwargs) -> None:
        """Start with no terminal completion and no reset chain."""
        super().__init__(*args, **kwargs)
        self.page_size = self._bounded_int(
            page_size, name="page_size", minimum=1, maximum=1000
        )
        self.base_revision: int | None = None
        self.terminal_delta_seen = False
        self.reset_attempt = 0

    @classmethod
    def update_settings(cls, settings: BaseSettings) -> None:
        """Enable the idle gate and reset-attempt-aware duplicate identity."""
        super().update_settings(settings)
        settings.set(
            "MSGLOOM_ONEDRIVE_DELTA_CHECKPOINT_ENABLED", True, priority="spider"
        )
        settings.set(
            "REQUEST_FINGERPRINTER_CLASS",
            "message_ingest.fingerprints.microsoft.onedrive.OneDriveDeltaRequestFingerprinter",
            priority="spider",
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
        yield self._delta_request(
            checkpoint.delta_link
            if checkpoint
            else self.delta_path(page_size=self.page_size),
            page_number=1,
            reset_attempt=0,
            verbatim=checkpoint is not None,
        )

    def parse_delta(
        self,
        response: TextResponse,
        *,
        purpose: str,
        page_number: int,
        reset_attempt: int,
    ) -> Iterator[Any]:
        """Emit evidence, ordered observations, then continuation or candidate."""
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        page = GraphDeltaPage.from_payload(
            response.json(),
            context="OneDrive delta",
            strict=False,
            validate_links=False,
        )
        self.crawler.stats.inc_value("msgloom/crawl/onedrive/delta/page_count")
        for entry_index, raw in enumerate(page.values):
            if reset_attempt:
                if self.base_revision is None:
                    raise ValueError("OneDrive resync requires an existing checkpoint")
                yield OneDriveDeltaResyncObservationItem.from_graph(
                    raw,
                    observed_at=evidence.observed_at,
                    evidence_id=evidence.evidence_id,
                    run_id=self.run_id,
                    reset_attempt=reset_attempt,
                    base_revision=self.base_revision,
                    page_number=page_number,
                    entry_index=entry_index,
                )
                self.crawler.stats.inc_value(
                    "msgloom/crawl/onedrive/delta/resync_observation_count"
                )
            else:
                yield OneDriveItem.from_graph(
                    raw,
                    observed_at=evidence.observed_at,
                    evidence_id=evidence.evidence_id,
                    run_id=self.run_id,
                )
            self.crawler.stats.inc_value("msgloom/crawl/onedrive/delta/item_count")
        page.validate_state()
        if next_link := page.next_link:
            yield self._delta_request(
                next_link,
                page_number=page_number + 1,
                reset_attempt=reset_attempt,
                verbatim=True,
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

    def errback(self, failure: Failure) -> Iterator[Any]:
        """Start one allowed post-410 reset; fail closed for every other failure."""
        request = self._failure_request(failure)
        evidence = self._failure_evidence_item(failure)
        if (
            request.cb_kwargs.get("purpose") == "onedrive-delta-page"
            and isinstance(failure.value, HttpError)
            and evidence.response_status == 410
        ):
            location = onedrive_resync_location(
                failure.value.response.headers.getlist("Location"),
                graph_root=self.graph_root,
            )
            self._redact_resync_evidence(evidence)
            yield evidence
            if (
                self.reset_attempt
                or request.cb_kwargs.get("reset_attempt", 0)
                or self.base_revision is None
                or location is None
            ):
                yield self._request_failure_item(failure, evidence)
                return
            self.reset_attempt = 1
            self.terminal_delta_seen = False
            self.crawler.stats.inc_value(
                "msgloom/crawl/onedrive/delta/checkpoint_reset_count"
            )
            self.logger.warning(
                "OneDrive delta checkpoint expired; starting one full resync"
            )
            yield OneDriveDeltaResyncAttemptItem(
                reset_attempt=1,
                base_revision=self.base_revision,
                started_at=evidence.observed_at,
                trigger_evidence_id=evidence.evidence_id,
                run_id=self.run_id,
            )
            yield self._delta_request(
                location,
                page_number=1,
                reset_attempt=1,
                verbatim=True,
            )
            return
        yield evidence
        yield self._request_failure_item(failure, evidence)

    def _delta_request(
        self,
        url: str,
        *,
        page_number: int,
        reset_attempt: int,
        verbatim: bool,
    ):
        """Build one uncached delta request with durable ordering context."""
        return self._request(
            url,
            callback=self.parse_delta,
            purpose="onedrive-delta-page",
            cb_kwargs={
                "page_number": page_number,
                "reset_attempt": reset_attempt,
            },
            verbatim_url=verbatim,
            dont_cache=True,
        )

    @staticmethod
    def _redact_resync_evidence(evidence) -> None:
        """Remove opaque reset URLs from retained response headers."""
        evidence.response_headers = {
            name: values
            for name, values in evidence.response_headers.items()
            if name.lower() not in _RESET_PRIVATE_HEADERS
        }
        evidence.response_flags.append("onedrive_delta_resync_location_redacted")
