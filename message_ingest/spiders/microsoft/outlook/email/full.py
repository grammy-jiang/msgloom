"""Acquire all required surfaces for selected Outlook messages."""

from __future__ import annotations

import asyncio
from typing import Any

import scrapy
from scrapy.exceptions import DownloadCancelledError
from scrapy.http import Response, TextResponse
from twisted.python.failure import Failure

from message_ingest.acquisition.microsoft.outlook.email.profile import (
    FULL_V1,
    attachment_required_surfaces,
    attachment_type_name,
    surface_is_complete,
)
from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore
from message_ingest.extensions.catalog import CatalogService
from message_ingest.items.microsoft.outlook.email import (
    OutlookMailDetailItem,
    OutlookMessageSurfaceItem,
)
from microsoft_graph.protocol import graph_object

from ._attachments import OutlookAttachmentTraversal


class OutlookFullSpider(OutlookAttachmentTraversal):
    """Acquire or enrich the Full-profile surfaces of selected messages."""

    name = "outlook_full"

    def __init__(
        self,
        *args,
        message_ids: str = "",
        operation: str = "refresh",
        profile: str = FULL_V1,
        **kwargs,
    ) -> None:
        """
        Normalize unique target IDs and reject unsupported operations or
        profiles.
        """
        super().__init__(*args, **kwargs)
        self.message_ids = tuple(
            dict.fromkeys(
                cleaned
                for message_id in message_ids.split(",")
                if (cleaned := message_id.strip())
            )
        )
        self.operation = operation.strip().lower()
        if self.operation not in {"enrich", "refresh"}:
            raise ValueError("operation must be 'enrich' or 'refresh'")
        self.profile = profile.strip()
        if self.profile != FULL_V1:
            raise ValueError(f"unsupported profile: {self.profile!r}")
        if not self.message_ids:
            raise ValueError("at least one message ID is required")

    async def start(self):
        """
        Refresh always requests the three base surfaces; enrich plans only
        gaps.

        Read catalog state off the event loop. Async start must yield normally,
        while synchronous callbacks can delegate output with ``yield from``.
        """
        self.logger.info(
            "Starting Outlook targeted acquisition: messages=%s operation=%s profile=%s",
            len(self.message_ids),
            self.operation,
            self.profile,
        )
        self.crawler.stats.set_value("msgloom/crawl/mode", "full")
        self.crawler.stats.set_value("msgloom/crawl/run_id", self.run_id)
        self.crawler.stats.set_value(
            "msgloom/crawl/enrichment/target_message_count",
            len(self.message_ids),
        )
        self.crawler.stats.set_value(
            "msgloom/crawl/enrichment/operation", self.operation
        )
        self.crawler.stats.set_value("msgloom/crawl/enrichment/profile", self.profile)
        for message_id in self.message_ids:
            if self.operation == "refresh":
                yield self._message_detail_request(message_id)
                yield self._message_mime_request(message_id)
                yield self._attachments_request(message_id, page_number=1)
                continue

            state = await asyncio.to_thread(self._load_enrichment_state, message_id)
            emitted = False
            # Async generators cannot delegate with yield from. Stream each
            # result without retaining a list of all attachment requests.
            for output in self._full_enrich_outputs(message_id, state):
                emitted = True
                yield output
            if not emitted:
                self.crawler.stats.inc_value(
                    "msgloom/crawl/enrichment/already_complete_count"
                )

    def parse_message_detail(
        self,
        response: TextResponse,
        *,
        purpose: str,
        message_id: str,
    ):
        """Record message detail and the complete provider response."""
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        self.logger.debug("Fetched Outlook message detail: message_id=%s", message_id)
        self.crawler.stats.inc_value("msgloom/crawl/enrichment/message_detail_count")
        yield OutlookMailDetailItem(
            message_id=message_id,
            raw=graph_object(response.json(), context="Outlook message detail"),
            source_response_url=response.url,
            observed_at=evidence.observed_at,
            evidence_id=evidence.evidence_id,
            run_id=self.run_id,
        )

    def parse_raw_evidence(
        self,
        response: Response,
        *,
        purpose: str,
        message_id: str,
        attachment_id: str | None = None,
    ):
        """
        Emit raw bytes first, then mark the matching MIME or attachment surface
        acquired.
        """
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        if purpose == "message-mime":
            self.logger.debug("Fetched Outlook MIME surface: message_id=%s", message_id)
            self.crawler.stats.inc_value("msgloom/crawl/enrichment/message_mime_count")
            surface = "mime"
        elif purpose == "attachment-raw" and attachment_id:
            self.crawler.stats.inc_value(
                "msgloom/crawl/enrichment/attachment_raw_count"
            )
            surface = f"attachment_raw:{attachment_id}"
        else:
            return
        yield OutlookMessageSurfaceItem(
            message_id=message_id,
            surface=surface,
            status="acquired",
            observed_at=evidence.observed_at,
            evidence_id=evidence.evidence_id,
            profile_version=FULL_V1,
        )

    def errback(self, failure: Failure):
        """
        Record final HTTP outcomes as versioned terminal surfaces when
        appropriate.

        Authorization, absence, and unsupported-operation results stop repeated
        enrich attempts for Full-v1. Transient errors remain retryable in a
        later run. All final request failures still emit evidence and a
        semantic acquisition failure.
        """
        callback_data = self._failure_request(failure).cb_kwargs
        purpose = callback_data.get("purpose", "unknown")
        evidence = self._failure_evidence_item(failure)
        yield evidence
        if failure.check(DownloadCancelledError) and purpose in {
            "message-mime",
            "attachments-list",
            "attachment-raw",
            "item-attachment-detail",
        }:
            surface = self._surface_for_purpose(
                purpose, callback_data.get("attachment_id")
            )
            if surface and (message_id := callback_data.get("message_id")):
                self.crawler.stats.inc_value(
                    "msgloom/crawl/enrichment/download_size_limit_omission_count"
                )
                yield OutlookMessageSurfaceItem(
                    message_id=message_id,
                    surface=surface,
                    status="omitted_size_limit",
                    observed_at=evidence.observed_at,
                    evidence_id=evidence.evidence_id,
                    profile_version=FULL_V1,
                )
                return
        terminal_status = {
            401: "unauthorized",
            403: "unauthorized",
            404: "unavailable",
            410: "unavailable",
            405: "unsupported",
        }.get(evidence.response_status or 0)
        surface = self._surface_for_purpose(purpose, callback_data.get("attachment_id"))
        if (
            terminal_status
            and surface
            and (message_id := callback_data.get("message_id"))
        ):
            self.logger.warning(
                "Outlook surface reached terminal HTTP state: "
                "purpose=%s status=%s surface=%s terminal=%s",
                purpose,
                evidence.response_status,
                surface,
                terminal_status,
            )
            yield OutlookMessageSurfaceItem(
                message_id=message_id,
                surface=surface,
                status=terminal_status,
                observed_at=evidence.observed_at,
                evidence_id=evidence.evidence_id,
                profile_version=FULL_V1,
            )
        yield self._request_failure_item(failure, evidence)

    @staticmethod
    def _surface_for_purpose(purpose: str, attachment_id: str | None) -> str | None:
        """
        Map known acquisition purposes to catalog surface keys; unknown
        purposes stay unmarked.
        """
        if purpose == "message-detail":
            return "detail"
        if purpose == "message-mime":
            return "mime"
        if purpose == "attachments-list":
            return "attachments"
        if purpose == "attachment-raw" and attachment_id:
            return f"attachment_raw:{attachment_id}"
        if purpose == "item-attachment-detail" and attachment_id:
            return f"item_attachment_detail:{attachment_id}"
        return None

    def _load_enrichment_state(self, message_id: str) -> dict[str, Any]:
        """
        Read only the surface and attachment state needed to plan missing
        acquisition.
        """
        catalog = CatalogService.from_crawler(self.crawler).catalog
        store = OutlookMailStore(
            catalog,
            source_id=self.crawler.settings["MSGLOOM_SOURCE_ID"],
        )
        return {
            "surfaces": store.get_surfaces(message_id=message_id),
            "attachments": store.get_attachments(message_id=message_id),
        }

    def _full_enrich_outputs(self, message_id: str, state: dict[str, Any]):
        """
        Stream missing profile surfaces using the persisted attachment
        inventory.

        When attachment inventory is incomplete, fetch it before planning child
        surfaces. An unsupported child retains the original metadata evidence
        and observation time.
        """
        surfaces = state["surfaces"]

        if not surface_is_complete(surfaces, "detail"):
            yield self._message_detail_request(message_id)
        if not surface_is_complete(surfaces, "mime"):
            yield self._message_mime_request(message_id)

        if not surface_is_complete(surfaces, "attachments"):
            yield self._attachments_request(message_id, page_number=1)
            return
        if surfaces["attachments"]["status"] != "acquired":
            return

        for attachment in state["attachments"]:
            attachment_id = attachment["attachment_id"]
            attachment_type = attachment["attachment_type"]
            required = attachment_required_surfaces(
                attachment_type,
                attachment_id,
            )
            for surface in required:
                if surface_is_complete(surfaces, surface):
                    continue
                if surface.startswith("attachment_raw:"):
                    normalized = attachment_type_name(attachment_type)
                    if normalized in {"fileAttachment", "itemAttachment"}:
                        yield self._attachment_raw_request(
                            message_id,
                            attachment_id,
                        )
                    else:
                        yield OutlookMessageSurfaceItem(
                            message_id=message_id,
                            surface=surface,
                            status="unsupported",
                            observed_at=attachment["latest_observed_at"],
                            evidence_id=attachment["latest_evidence_id"],
                            profile_version=FULL_V1,
                        )
                elif surface.startswith("item_attachment_detail:"):
                    yield self._item_attachment_detail_request(
                        message_id,
                        attachment_id,
                    )

    def _message_detail_request(self, message_id: str) -> scrapy.Request:
        """
        Acquire full JSON fields without changing the shared discovery
        representation.
        """
        return self._request(
            self.message_path(message_id, fields=self.full_fields),
            callback=self.parse_message_detail,
            purpose="message-detail",
            cb_kwargs={"message_id": message_id},
        )

    def _message_mime_request(self, message_id: str) -> scrapy.Request:
        """
        Acquire the MIME representation with its own request fingerprint
        headers.
        """
        return self._request(
            self.message_mime_path(message_id),
            callback=self.parse_raw_evidence,
            purpose="message-mime",
            cb_kwargs={"message_id": message_id},
            accept="message/rfc822, */*",
            download_maxsize=self._max_raw_content_bytes(),
        )
