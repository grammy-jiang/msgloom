"""Abstract attachment traversal shared with the Full acquisition spider."""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import scrapy
from scrapy.http import Response, TextResponse

from message_ingest.acquisition.microsoft.outlook.email.profile import (
    FULL_V1,
    attachment_required_surfaces,
    attachment_type_name,
)
from message_ingest.items.microsoft.outlook.email import (
    OutlookAttachmentItem,
    OutlookMailInventoryPageItem,
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

    _authoritative_rule_refresh = False

    @abstractmethod
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
        resource_version: str | None = None,
        primary_observed_at: str | None = None,
        selection_id: str | None = None,
        parent_evidence_id: str | None = None,
        inventory_id: str | None = None,
        page_id: str | None = None,
        previous_page_id: str | None = None,
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
        member_capture_ids = []
        for attachment in attachments:
            attachment_id = attachment["id"]
            attachment_type = attachment.get("@odata.type")
            type_name = attachment_type_name(attachment_type)
            self.crawler.stats.inc_value(
                f"msgloom/crawl/enrichment/attachment_type_count/{type_name}"
            )
            from message_ingest.catalog.stores.microsoft.outlook._email_handoff import (
                semantic_digest,
            )

            capture_id = semantic_digest([page_id, attachment_id]) if page_id else None
            member_capture_ids.append(capture_id)
            yield OutlookAttachmentItem.from_graph(
                attachment,
                capture_id=capture_id,
                message_id=message_id,
                source_response_url=response.url,
                observed_at=evidence.observed_at,
                evidence_id=evidence.evidence_id,
                run_id=self.run_id,
                resource_version=resource_version,
                primary_observed_at=primary_observed_at,
                selection_id=selection_id,
                parent_evidence_id=parent_evidence_id,
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
                            run_id=self.run_id,
                            resource_version=resource_version,
                            primary_observed_at=primary_observed_at,
                            selection_id=selection_id,
                            parent_evidence_id=parent_evidence_id,
                            message_id=message_id,
                            surface=surface,
                            status="omitted_size_limit",
                            observed_at=evidence.observed_at,
                            evidence_id=evidence.evidence_id,
                            profile_version=FULL_V1,
                        )
                    continue
                yield self._attachment_raw_request(
                    message_id,
                    attachment_id,
                    resource_version=resource_version,
                    primary_observed_at=primary_observed_at,
                    selection_id=selection_id,
                    parent_evidence_id=parent_evidence_id,
                )
                if type_name == "itemAttachment":
                    yield self._item_attachment_detail_request(
                        message_id,
                        attachment_id,
                        resource_version=resource_version,
                        primary_observed_at=primary_observed_at,
                        selection_id=selection_id,
                        parent_evidence_id=parent_evidence_id,
                    )
            else:
                yield OutlookMessageSurfaceItem(
                    run_id=self.run_id,
                    resource_version=resource_version,
                    primary_observed_at=primary_observed_at,
                    selection_id=selection_id,
                    parent_evidence_id=parent_evidence_id,
                    message_id=message_id,
                    surface=f"attachment_raw:{attachment_id}",
                    status="unsupported",
                    observed_at=evidence.observed_at,
                    evidence_id=evidence.evidence_id,
                    profile_version=FULL_V1,
                )

        if selection_id is not None:
            yield self._inventory_page_item(
                evidence,
                {
                    "message_id": message_id,
                    "selection_id": selection_id,
                    "resource_version": resource_version,
                    "parent_evidence_id": parent_evidence_id,
                    "inventory_id": inventory_id,
                    "page_id": page_id,
                    "previous_page_id": previous_page_id,
                    "page_number": page_number,
                },
                "acquired",
                tuple(member_capture_ids),
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
                inventory_id=inventory_id,
                previous_page_id=page_id,
                resource_version=resource_version,
                primary_observed_at=primary_observed_at,
                selection_id=selection_id,
                parent_evidence_id=parent_evidence_id,
            )
            return
        if selection_id is not None:
            return
        # Legacy producers cannot establish the new exact inventory contract.
        yield OutlookMessageSurfaceItem(
            run_id=self.run_id,
            resource_version=resource_version,
            primary_observed_at=primary_observed_at,
            selection_id=selection_id,
            parent_evidence_id=parent_evidence_id,
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
        resource_version: str | None = None,
        primary_observed_at: str | None = None,
        selection_id: str | None = None,
        parent_evidence_id: str | None = None,
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
            resource_version=resource_version,
            primary_observed_at=primary_observed_at,
            selection_id=selection_id,
            parent_evidence_id=parent_evidence_id,
        )
        yield OutlookMessageSurfaceItem(
            run_id=self.run_id,
            resource_version=resource_version,
            primary_observed_at=primary_observed_at,
            selection_id=selection_id,
            parent_evidence_id=parent_evidence_id,
            message_id=message_id,
            surface=f"item_attachment_detail:{attachment_id}",
            status="acquired",
            observed_at=evidence.observed_at,
            evidence_id=evidence.evidence_id,
            profile_version=FULL_V1,
        )

    def _inventory_page_item(self, evidence, data, status, members=()):
        """Retain a selected page or explicit terminal traversal limitation."""
        return OutlookMailInventoryPageItem(
            message_id=data["message_id"],
            selection_id=data["selection_id"],
            resource_version=data["resource_version"],
            parent_evidence_id=data["parent_evidence_id"],
            inventory_id=data["inventory_id"],
            page_id=data["page_id"],
            previous_page_id=data.get("previous_page_id"),
            page_number=data["page_number"],
            member_capture_ids=members,
            status=status,
            profile_version=FULL_V1,
            evidence_id=evidence.evidence_id,
            observed_at=evidence.observed_at,
            run_id=self.run_id,
        )

    def _attachments_request(
        self,
        message_id: str,
        *,
        url: str | None = None,
        page_number: int,
        verbatim_url: bool = False,
        resource_version: str | None = None,
        primary_observed_at: str | None = None,
        selection_id: str | None = None,
        parent_evidence_id: str | None = None,
        inventory_id: str | None = None,
        previous_page_id: str | None = None,
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
                "resource_version": resource_version,
                "primary_observed_at": primary_observed_at,
                "selection_id": selection_id,
                "parent_evidence_id": parent_evidence_id,
                "page_number": page_number,
                "inventory_id": inventory_id or uuid4().hex,
                "page_id": uuid4().hex,
                "previous_page_id": previous_page_id,
            },
            verbatim_url=verbatim_url,
            download_maxsize=self._max_raw_content_bytes(),
            dont_cache=self._authoritative_rule_refresh,
        )

    def _attachment_raw_request(
        self,
        message_id: str,
        attachment_id: str,
        *,
        resource_version: str | None = None,
        primary_observed_at: str | None = None,
        selection_id: str | None = None,
        parent_evidence_id: str | None = None,
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
                "resource_version": resource_version,
                "primary_observed_at": primary_observed_at,
                "selection_id": selection_id,
                "parent_evidence_id": parent_evidence_id,
                "attachment_id": attachment_id,
            },
            accept="*/*",
            download_maxsize=self._max_raw_content_bytes(),
            dont_cache=self._authoritative_rule_refresh,
        )

    def _item_attachment_detail_request(
        self,
        message_id: str,
        attachment_id: str,
        *,
        resource_version: str | None = None,
        primary_observed_at: str | None = None,
        selection_id: str | None = None,
        parent_evidence_id: str | None = None,
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
                "resource_version": resource_version,
                "primary_observed_at": primary_observed_at,
                "selection_id": selection_id,
                "parent_evidence_id": parent_evidence_id,
                "attachment_id": attachment_id,
            },
            download_maxsize=self._max_raw_content_bytes(),
            dont_cache=self._authoritative_rule_refresh,
        )
