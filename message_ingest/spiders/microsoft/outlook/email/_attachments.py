"""Abstract attachment traversal shared with the Full acquisition spider."""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Iterator
from typing import Any

import scrapy
from scrapy.http import Response, TextResponse

from message_ingest.acquisition.microsoft.outlook.email.profile import (
    FULL_V1,
    attachment_required_surfaces,
    attachment_type_name,
)
from message_ingest.items.microsoft.outlook.email import (
    OutlookAttachmentItem,
    OutlookMessageSurfaceItem,
)
from microsoft_graph.protocol import GraphCollectionPage, graph_object
from microsoft_graph.protocol.attachments import (
    attachment_list_path,
    attachment_raw_path,
    item_attachment_path,
)

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
        page = GraphCollectionPage.from_payload(
            response.json(),
            missing_value_empty=True,
            empty_links_absent=True,
            validate_links=False,
        )
        attachments = page.values
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
            yield OutlookAttachmentItem.from_graph(
                attachment,
                message_id=message_id,
                source_response_url=response.url,
                observed_at=evidence.observed_at,
                evidence_id=evidence.evidence_id,
                run_id=self.run_id,
            )

            if type_name in {"fileAttachment", "itemAttachment"}:
                if self._attachment_size_exceeds_limit(attachment.get("size")):
                    self.crawler.stats.inc_value(
                        "msgloom/crawl/enrichment/size_limit_omission_count"
                    )
                    for surface in attachment_required_surfaces(
                        attachment_type, attachment_id
                    ):
                        yield OutlookMessageSurfaceItem(
                            message_id=message_id,
                            surface=surface,
                            status="omitted_size_limit",
                            observed_at=evidence.observed_at,
                            evidence_id=evidence.evidence_id,
                            profile_version=FULL_V1,
                        )
                    continue
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

        if next_link := page.next_link:
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
        payload = graph_object(response.json(), context="Outlook attachment detail")
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
        if url is None:
            url = f"{self.graph_root}{attachment_list_path(self.message_path(message_id))}"
        return self._request(
            url,
            callback=self.parse_attachments,
            purpose="attachments-list",
            cb_kwargs={
                "message_id": message_id,
                "page_number": page_number,
            },
            verbatim_url=verbatim_url,
            download_maxsize=self._max_raw_content_bytes(),
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
        path = attachment_raw_path(self.message_path(message_id), attachment_id)
        return self._request(
            f"{self.graph_root}{path}",
            callback=self.parse_raw_evidence,
            purpose="attachment-raw",
            cb_kwargs={
                "message_id": message_id,
                "attachment_id": attachment_id,
            },
            accept="*/*",
            download_maxsize=self._max_raw_content_bytes(),
        )

    def _item_attachment_detail_request(
        self,
        message_id: str,
        attachment_id: str,
    ) -> scrapy.Request:
        """
        Expand the embedded Graph item separately from its raw content surface.
        """
        path = item_attachment_path(self.message_path(message_id), attachment_id)
        return self._request(
            f"{self.graph_root}{path}",
            callback=self.parse_attachment_detail,
            purpose="item-attachment-detail",
            cb_kwargs={
                "message_id": message_id,
                "attachment_id": attachment_id,
            },
            download_maxsize=self._max_raw_content_bytes(),
        )
