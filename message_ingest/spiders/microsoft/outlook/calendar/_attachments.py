"""Calendar attachment traversal shared by targeted full acquisition."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Any
from urllib.parse import quote, urlencode

import scrapy
from scrapy.http import Response, TextResponse

from message_ingest.acquisition.microsoft.outlook.calendar.profile import (
    FULL_V1,
    attachment_type_name,
)
from message_ingest.items.microsoft.outlook.calendar import (
    OutlookCalendarAttachmentContentItem,
    OutlookCalendarAttachmentItem,
    OutlookCalendarEventSurfaceItem,
)
from message_ingest.spiders.microsoft._graph import MicrosoftGraphSpider


def _metadata_without_content(value: Any) -> Any:
    """Keep expanded item metadata while evidence owns nested content bytes."""
    if isinstance(value, dict):
        return {
            key: _metadata_without_content(child)
            for key, child in value.items()
            if key != "contentBytes"
        }
    if isinstance(value, list):
        return [_metadata_without_content(child) for child in value]
    return value


class OutlookCalendarAttachmentTraversal(MicrosoftGraphSpider, ABC):
    """Own Calendar attachment pagination, raw content, and item expansion."""

    page_size: int
    calendar_id: str

    @abstractmethod
    def _event_path(self, event_id: str) -> str:
        """Return the Graph path for one event in the active calendar scope."""
        raise NotImplementedError

    def parse_attachments(
        self,
        response: TextResponse,
        *,
        purpose: str,
        event_id: str,
        page_number: int,
        resource_version: str | None,
    ) -> Iterator[Any]:
        """
        Persist attachment metadata while raw evidence keeps provider content.

        File attachment contentBytes can be large. The semantic attachment row
        records that content was present and removes that field from its
        metadata JSON; the preceding raw HTTP evidence retains the exact bytes.
        """
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence

        payload = response.json()
        if not isinstance(payload, dict):
            raise TypeError("Calendar attachment response must be a JSON object")
        values = payload.get("value")
        if not isinstance(values, list):
            raise TypeError("Calendar attachment response must contain a value list")

        calendar_key = self.calendar_id or "default"
        self.crawler.stats.inc_value(
            "msgloom/crawl/calendar/full/attachment_page_count"
        )
        for attachment in values:
            if not isinstance(attachment, dict):
                raise TypeError("Calendar attachment entry must be a JSON object")
            attachment_id = attachment.get("id")
            if not isinstance(attachment_id, str) or not attachment_id:
                raise ValueError("Calendar attachment must contain a non-empty id")
            raw = _metadata_without_content(attachment)
            content_bytes_present = "contentBytes" in attachment
            attachment_type = raw.get("@odata.type")
            if attachment_type is not None and not isinstance(
                attachment_type,
                str,
            ):
                raise ValueError("Calendar attachment @odata.type must be a string")

            self.crawler.stats.inc_value("msgloom/crawl/calendar/full/attachment_count")
            yield OutlookCalendarAttachmentItem(
                event_id=event_id,
                attachment_id=attachment_id,
                attachment_type=attachment_type,
                raw=raw,
                observed_at=evidence.observed_at,
                evidence_id=evidence.evidence_id,
                run_id=self.run_id,
                calendar_id=calendar_key,
                content_bytes_present=content_bytes_present,
            )

            type_name = attachment_type_name(attachment_type)
            self.crawler.stats.inc_value(
                f"msgloom/crawl/calendar/full/attachment_type_count/{type_name}"
            )
            if type_name in {"fileAttachment", "itemAttachment"}:
                yield self._attachment_raw_request(
                    event_id,
                    attachment_id,
                    resource_version=resource_version,
                )
                if type_name == "itemAttachment":
                    yield self._item_attachment_detail_request(
                        event_id,
                        attachment_id,
                        resource_version=resource_version,
                    )
            else:
                yield OutlookCalendarEventSurfaceItem(
                    event_id=event_id,
                    surface=f"attachment_raw:{attachment_id}",
                    status="unsupported",
                    observed_at=evidence.observed_at,
                    evidence_id=evidence.evidence_id,
                    profile_version=FULL_V1,
                    resource_version=resource_version,
                )

        next_link = payload.get("@odata.nextLink")
        if next_link is None:
            yield OutlookCalendarEventSurfaceItem(
                event_id=event_id,
                surface="attachments",
                status="acquired",
                observed_at=evidence.observed_at,
                evidence_id=evidence.evidence_id,
                profile_version=FULL_V1,
                resource_version=resource_version,
            )
            return
        if not isinstance(next_link, str) or not next_link:
            raise ValueError(
                "Calendar attachment @odata.nextLink must be a non-empty string"
            )
        yield self._request(
            next_link,
            callback=self.parse_attachments,
            purpose="calendar-event-attachments",
            cb_kwargs={
                "event_id": event_id,
                "page_number": page_number + 1,
                "resource_version": resource_version,
            },
            verbatim_url=True,
            prefer='IdType="ImmutableId"',
        )

    def parse_attachment_content(
        self,
        response: Response,
        *,
        purpose: str,
        event_id: str,
        attachment_id: str,
        resource_version: str | None,
    ) -> Iterator[Any]:
        """Link one raw file/item attachment response to its metadata."""
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        self.crawler.stats.inc_value(
            "msgloom/crawl/calendar/full/attachment_content_count"
        )
        yield OutlookCalendarAttachmentContentItem(
            event_id=event_id,
            attachment_id=attachment_id,
            observed_at=evidence.observed_at,
            evidence_id=evidence.evidence_id,
            run_id=self.run_id,
        )
        yield OutlookCalendarEventSurfaceItem(
            event_id=event_id,
            surface=f"attachment_raw:{attachment_id}",
            status="acquired",
            observed_at=evidence.observed_at,
            evidence_id=evidence.evidence_id,
            profile_version=FULL_V1,
            resource_version=resource_version,
        )

    def parse_attachment_detail(
        self,
        response: TextResponse,
        *,
        purpose: str,
        event_id: str,
        attachment_id: str,
        resource_version: str | None,
    ) -> Iterator[Any]:
        """Persist expanded item-attachment detail as richer metadata."""
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        payload = response.json()
        if not isinstance(payload, dict):
            raise TypeError("Calendar item attachment detail must be a JSON object")
        provider_id = payload.get("id")
        if provider_id != attachment_id:
            raise ValueError("Calendar item attachment detail ID changed in flight")
        raw = _metadata_without_content(payload)
        content_bytes_present = "contentBytes" in payload
        attachment_type = raw.get("@odata.type")
        if attachment_type is not None and not isinstance(
            attachment_type,
            str,
        ):
            raise ValueError("Calendar attachment @odata.type must be a string")
        self.crawler.stats.inc_value(
            "msgloom/crawl/calendar/full/item_attachment_detail_count"
        )
        yield OutlookCalendarAttachmentItem(
            event_id=event_id,
            attachment_id=attachment_id,
            attachment_type=attachment_type,
            raw=raw,
            observed_at=evidence.observed_at,
            evidence_id=evidence.evidence_id,
            run_id=self.run_id,
            calendar_id=self.calendar_id or "default",
            content_bytes_present=content_bytes_present,
        )
        yield OutlookCalendarEventSurfaceItem(
            event_id=event_id,
            surface=f"item_attachment_detail:{attachment_id}",
            status="acquired",
            observed_at=evidence.observed_at,
            evidence_id=evidence.evidence_id,
            profile_version=FULL_V1,
            resource_version=resource_version,
        )

    def _attachments_request(
        self,
        event_id: str,
        *,
        page_number: int,
        resource_version: str | None = None,
    ) -> scrapy.Request:
        """Inventory attachments only for events that report attachments."""
        event_path = self._event_path(event_id)
        query = urlencode({"$top": self.page_size})
        return self._request(
            f"{self.graph_root}{event_path}/attachments?{query}",
            callback=self.parse_attachments,
            purpose="calendar-event-attachments",
            cb_kwargs={
                "event_id": event_id,
                "page_number": page_number,
                "resource_version": resource_version,
            },
            prefer='IdType="ImmutableId"',
        )

    def _attachment_raw_request(
        self,
        event_id: str,
        attachment_id: str,
        *,
        resource_version: str | None = None,
    ) -> scrapy.Request:
        """Request raw bytes for file and item attachments."""
        event_path = self._event_path(event_id)
        encoded_attachment = quote(attachment_id, safe="")
        return self._request(
            f"{self.graph_root}{event_path}/attachments/{encoded_attachment}/$value",
            callback=self.parse_attachment_content,
            purpose="calendar-attachment-raw",
            cb_kwargs={
                "event_id": event_id,
                "attachment_id": attachment_id,
                "resource_version": resource_version,
            },
            accept="*/*",
            prefer='IdType="ImmutableId"',
        )

    def _item_attachment_detail_request(
        self,
        event_id: str,
        attachment_id: str,
        *,
        resource_version: str | None = None,
    ) -> scrapy.Request:
        """Expand an embedded Graph item separately from its raw bytes."""
        event_path = self._event_path(event_id)
        encoded_attachment = quote(attachment_id, safe="")
        query = urlencode({"$expand": "microsoft.graph.itemattachment/item"})
        return self._request(
            f"{self.graph_root}{event_path}/attachments/{encoded_attachment}?{query}",
            callback=self.parse_attachment_detail,
            purpose="calendar-item-attachment-detail",
            cb_kwargs={
                "event_id": event_id,
                "attachment_id": attachment_id,
                "resource_version": resource_version,
            },
            prefer='IdType="ImmutableId"',
        )


__all__ = ["OutlookCalendarAttachmentTraversal"]
