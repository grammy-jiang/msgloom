"""Abstract attachment traversal shared with the Full acquisition spider."""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Iterator
from typing import Any
from urllib.parse import quote, urlencode

import scrapy
from scrapy.http import Response, TextResponse

from message_ingest.items import OutlookAttachmentItem, OutlookMessageSurfaceItem
from message_ingest.profiles import FULL_V1, attachment_type_name

from ._base import OutlookMailSpider


class OutlookAttachmentTraversal(OutlookMailSpider):
    """
    Keep attachment callbacks on the full spider for request serialization.

    File attachments need raw bytes. Item attachments also need expanded item
    detail. Reference and unknown types record a terminal unsupported surface
    for Full-v1; they must not vanish from completeness tracking.
    """

    @abstractmethod
    def parse_raw_evidence(
        self,
        response: Response,
        *,
        purpose: str,
        message_id: str,
        attachment_id: str | None = None,
    ) -> Iterator[Any]:
        """Record an acquired MIME or attachment surface."""
        raise NotImplementedError

    def parse_attachments(
        self,
        response: TextResponse,
        *,
        purpose: str,
        message_id: str,
        page_number: int,
    ):
        """Emit attachment metadata and schedule each supported raw surface."""
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        payload = response.json()
        attachments = payload.get("value", [])
        self.logger.debug(
            "Processed Outlook attachment page: message_id=%s page=%s attachments=%s",
            message_id,
            page_number,
            len(attachments),
        )
        self.crawler.stats.inc_value("msgloom/crawl/enrichment/attachment_page_count")
        self.crawler.stats.inc_value(
            "msgloom/crawl/enrichment/attachment_count", count=len(attachments)
        )
        for attachment in attachments:
            attachment_id = attachment["id"]
            attachment_type = attachment.get("@odata.type")
            type_name = attachment_type_name(attachment_type)
            self.crawler.stats.inc_value(
                f"msgloom/crawl/enrichment/attachment_type_count/{type_name}"
            )
            yield OutlookAttachmentItem(
                message_id=message_id,
                attachment_id=attachment_id,
                attachment_type=attachment_type,
                raw=attachment,
                source_response_url=response.url,
                observed_at=evidence.observed_at,
                evidence_id=evidence.evidence_id,
                run_id=self.run_id,
            )

            if type_name in {"fileAttachment", "itemAttachment"}:
                yield self._attachment_raw_request(message_id, attachment_id)
                if type_name == "itemAttachment":
                    yield self._item_attachment_detail_request(
                        message_id, attachment_id
                    )
            else:
                yield OutlookMessageSurfaceItem(
                    message_id=message_id,
                    surface=f"attachment_raw:{attachment_id}",
                    status="unsupported",
                    observed_at=evidence.observed_at,
                    evidence_id=evidence.evidence_id,
                    profile_version=FULL_V1,
                )

        if next_link := payload.get("@odata.nextLink"):
            self.crawler.stats.inc_value(
                "msgloom/crawl/enrichment/attachment_continuation_count"
            )
            yield self._attachments_request(
                message_id,
                url=next_link,
                page_number=page_number + 1,
                verbatim_url=True,
            )
            return
        # Only the final page proves the attachment inventory is complete.
        yield OutlookMessageSurfaceItem(
            message_id=message_id,
            surface="attachments",
            status="acquired",
            observed_at=evidence.observed_at,
            evidence_id=evidence.evidence_id,
            profile_version=FULL_V1,
        )

    def parse_attachment_detail(
        self,
        response: TextResponse,
        *,
        purpose: str,
        message_id: str,
        attachment_id: str,
    ):
        """Record expanded item attachment metadata and surface completion."""
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        self.crawler.stats.inc_value(
            "msgloom/crawl/enrichment/item_attachment_detail_count"
        )
        payload = response.json()
        yield OutlookAttachmentItem(
            message_id=message_id,
            attachment_id=attachment_id,
            attachment_type=payload.get("@odata.type"),
            raw=payload,
            source_response_url=response.url,
            observed_at=evidence.observed_at,
            evidence_id=evidence.evidence_id,
            run_id=self.run_id,
        )
        yield OutlookMessageSurfaceItem(
            message_id=message_id,
            surface=f"item_attachment_detail:{attachment_id}",
            status="acquired",
            observed_at=evidence.observed_at,
            evidence_id=evidence.evidence_id,
            profile_version=FULL_V1,
        )

    def _attachments_request(
        self,
        message_id: str,
        *,
        url: str | None = None,
        page_number: int,
        verbatim_url: bool = False,
    ) -> scrapy.Request:
        """
        List attachment metadata; only the final page marks the inventory
        acquired.
        """
        encoded_id = quote(message_id, safe="")
        return self._request(
            url or f"{self.graph_root}/me/messages/{encoded_id}/attachments",
            callback=self.parse_attachments,
            purpose="attachments-list",
            cb_kwargs={
                "message_id": message_id,
                "page_number": page_number,
            },
            verbatim_url=verbatim_url,
        )

    def _attachment_raw_request(
        self,
        message_id: str,
        attachment_id: str,
    ) -> scrapy.Request:
        """
        Request raw attachment bytes with a representation-specific ``Accept``
        header.
        """
        encoded_message_id = quote(message_id, safe="")
        encoded_attachment_id = quote(attachment_id, safe="")
        return self._request(
            f"{self.graph_root}/me/messages/{encoded_message_id}/attachments/"
            f"{encoded_attachment_id}/$value",
            callback=self.parse_raw_evidence,
            purpose="attachment-raw",
            cb_kwargs={
                "message_id": message_id,
                "attachment_id": attachment_id,
            },
            accept="*/*",
        )

    def _item_attachment_detail_request(
        self,
        message_id: str,
        attachment_id: str,
    ) -> scrapy.Request:
        """
        Expand the embedded Graph item separately from its raw content surface.
        """
        encoded_message_id = quote(message_id, safe="")
        encoded_attachment_id = quote(attachment_id, safe="")
        query = urlencode({"$expand": "microsoft.graph.itemattachment/item"})
        return self._request(
            f"{self.graph_root}/me/messages/{encoded_message_id}/attachments/"
            f"{encoded_attachment_id}?{query}",
            callback=self.parse_attachment_detail,
            purpose="item-attachment-detail",
            cb_kwargs={
                "message_id": message_id,
                "attachment_id": attachment_id,
            },
        )
