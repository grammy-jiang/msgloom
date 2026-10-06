"""Acquire all required surfaces for selected Outlook messages."""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import uuid4

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
from message_ingest.catalog.stores.microsoft.outlook._email_handoff import (
    primary_projection,
    semantic_digest,
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

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        """Reject JOBDIR until logical-run resume is separately qualified."""
        if crawler.settings.get("JOBDIR"):
            raise ValueError("Outlook Mail full does not support JOBDIR")
        return super().from_crawler(crawler, *args, **kwargs)

    def __init__(
        self,
        *args,
        message_ids: str = "",
        operation: str = "refresh",
        profile: str = FULL_V1,
        _authoritative_rule_refresh: bool = False,
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
        if not isinstance(_authoritative_rule_refresh, bool):
            raise TypeError("_authoritative_rule_refresh must be bool")
        if _authoritative_rule_refresh and self.operation != "refresh":
            raise ValueError("authoritative rule refresh requires refresh operation")
        self._authoritative_rule_refresh = _authoritative_rule_refresh
        self.profile = profile.strip()
        if self.profile != FULL_V1:
            raise ValueError(f"unsupported profile: {self.profile!r}")
        if not self.message_ids:
            raise ValueError("at least one message ID is required")

    async def start(self):
        """
        Select exact detail before scheduling the remaining Full surfaces.

        Enrich skips only a profile with validated immutable bindings.

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
                yield self._message_detail_request(message_id, acquire_components=True)
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
        acquire_components: bool = False,
        selection_id: str | None = None,
    ):
        """Record message detail and the complete provider response."""
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        self.logger.debug("Fetched Outlook message detail: message_id=%s", message_id)
        self.crawler.stats.inc_value("msgloom/crawl/enrichment/message_detail_count")
        payload = graph_object(response.json(), context="Outlook message detail")
        if payload.get("id") != message_id:
            raise ValueError("Full detail identity does not match selected target")
        if acquire_components:
            # Select from these exact bytes before scheduling child Requests.
            # Their pipeline writes may finish before or after detail; no
            # mutable latest-row lookup establishes their parent association.
            pin = {
                "resource_version": semantic_digest(primary_projection(payload)),
                "primary_observed_at": evidence.observed_at,
                "selection_id": selection_id,
                "parent_evidence_id": evidence.evidence_id,
            }
            yield self._message_mime_request(message_id, **pin)
            yield self._attachments_request(
                message_id,
                page_number=1,
                **pin,
            )
        yield OutlookMailDetailItem(
            message_id=message_id,
            raw=payload,
            selection_id=selection_id,
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
        resource_version: str | None = None,
        primary_observed_at: str | None = None,
        selection_id: str | None = None,
        parent_evidence_id: str | None = None,
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
            run_id=self.run_id,
            message_id=message_id,
            surface=surface,
            resource_version=resource_version,
            primary_observed_at=primary_observed_at,
            selection_id=selection_id,
            parent_evidence_id=parent_evidence_id,
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
        if purpose == "message-detail" and callback_data.get("selection_id"):
            # No primary bytes exist to bind a failed detail selection.
            yield self._request_failure_item(failure, evidence)
            return
        if purpose == "attachments-list" and callback_data.get("selection_id"):
            inventory_status = (
                "omitted_size_limit"
                if failure.check(DownloadCancelledError)
                else {
                    401: "unauthorized",
                    403: "unauthorized",
                    404: "unavailable",
                    410: "unavailable",
                    405: "unsupported",
                }.get(evidence.response_status or 0)
            )
            if inventory_status:
                yield self._inventory_page_item(
                    evidence, callback_data, inventory_status
                )
            if inventory_status != "omitted_size_limit":
                yield self._request_failure_item(failure, evidence)
            return
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
                    run_id=self.run_id,
                    message_id=message_id,
                    surface=surface,
                    resource_version=callback_data.get("resource_version"),
                    primary_observed_at=callback_data.get("primary_observed_at"),
                    selection_id=callback_data.get("selection_id"),
                    parent_evidence_id=callback_data.get("parent_evidence_id"),
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
                run_id=self.run_id,
                message_id=message_id,
                surface=surface,
                resource_version=callback_data.get("resource_version"),
                primary_observed_at=callback_data.get("primary_observed_at"),
                selection_id=callback_data.get("selection_id"),
                parent_evidence_id=callback_data.get("parent_evidence_id"),
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
        return store.full_binding_state(message_id=message_id)

    def _full_enrich_outputs(self, message_id: str, state: dict[str, Any]):
        """
        Plan existing gaps only after validating their immutable primary pin.

        An invalid detail forces exact target reacquisition. Valid partial
        profiles keep the existing missing-surface traversal and cache policy.
        """
        surfaces = state["surfaces"]
        if not state.get("resource_version") or not surface_is_complete(
            surfaces, "detail"
        ):
            yield self._message_detail_request(message_id, acquire_components=True)
            return
        pin = {
            "resource_version": state["resource_version"],
            "primary_observed_at": state["primary_observed_at"],
            "selection_id": state["selection_id"],
            "parent_evidence_id": state["parent_evidence_id"],
        }
        if not surface_is_complete(surfaces, "mime"):
            yield self._message_mime_request(message_id, **pin)
        if not surface_is_complete(surfaces, "attachments"):
            yield self._attachments_request(message_id, page_number=1, **pin)
            return
        if surfaces["attachments"]["status"] != "acquired":
            return
        for attachment in state["attachments"]:
            attachment_id = attachment["attachment_id"]
            attachment_type = attachment["attachment_type"]
            for surface in attachment_required_surfaces(attachment_type, attachment_id):
                if surface_is_complete(surfaces, surface):
                    continue
                if surface.startswith("attachment_raw:"):
                    if attachment_type_name(attachment_type) in {
                        "fileAttachment",
                        "itemAttachment",
                    }:
                        yield self._attachment_raw_request(
                            message_id,
                            attachment_id,
                            **pin,
                        )
                    else:
                        yield OutlookMessageSurfaceItem(
                            run_id=self.run_id,
                            message_id=message_id,
                            surface=surface,
                            status="unsupported",
                            observed_at=attachment["latest_observed_at"],
                            evidence_id=attachment["latest_evidence_id"],
                            profile_version=FULL_V1,
                            **pin,
                        )
                elif surface.startswith("item_attachment_detail:"):
                    yield self._item_attachment_detail_request(
                        message_id,
                        attachment_id,
                        **pin,
                    )

    def _message_detail_request(
        self,
        message_id: str,
        *,
        acquire_components: bool = False,
    ) -> scrapy.Request:
        """
        Acquire full JSON fields without changing the shared discovery
        representation.
        """
        return self._request(
            self.message_path(message_id, fields=self.full_fields),
            callback=self.parse_message_detail,
            purpose="message-detail",
            cb_kwargs={
                "message_id": message_id,
                "acquire_components": acquire_components,
                "selection_id": uuid4().hex,
            },
            dont_cache=self._authoritative_rule_refresh,
        )

    def _message_mime_request(
        self,
        message_id: str,
        *,
        resource_version: str | None = None,
        primary_observed_at: str | None = None,
        selection_id: str | None = None,
        parent_evidence_id: str | None = None,
    ) -> scrapy.Request:
        """
        Acquire the MIME representation with its own request fingerprint
        headers.
        """
        return self._request(
            self.message_mime_path(message_id),
            callback=self.parse_raw_evidence,
            purpose="message-mime",
            cb_kwargs={
                "message_id": message_id,
                "resource_version": resource_version,
                "primary_observed_at": primary_observed_at,
                "selection_id": selection_id,
                "parent_evidence_id": parent_evidence_id,
            },
            accept="message/rfc822, */*",
            download_maxsize=self._max_raw_content_bytes(),
            dont_cache=self._authoritative_rule_refresh,
        )
