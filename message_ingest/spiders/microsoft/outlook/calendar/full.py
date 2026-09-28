"""Acquire full Microsoft Calendar event detail and attachments."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Any, ClassVar
from urllib.parse import quote, urlencode

import scrapy
from scrapy.http import Response, TextResponse
from scrapy.settings import BaseSettings

from message_ingest.items import (
    OutlookCalendarAttachmentContentItem,
    OutlookCalendarAttachmentItem,
    OutlookCalendarEventItem,
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


class OutlookCalendarFullSpider(MicrosoftGraphSpider):
    """Refresh rich detail for selected Calendar event IDs."""

    name = "outlook_calendar_full"
    graph_permissions: ClassVar[tuple[str, ...]] = ("Calendars.Read",)
    failure_context_keys = ("event_id", "attachment_id")

    def __init__(
        self,
        *args,
        event_ids: str | list[str] = "",
        calendar_id: str = "",
        page_size: str = "100",
        **kwargs,
    ) -> None:
        """Normalize target IDs and the optional containing calendar."""
        super().__init__(*args, **kwargs)
        targets = event_ids.split(",") if isinstance(event_ids, str) else event_ids
        self.event_ids = tuple(
            dict.fromkeys(
                cleaned for event_id in targets if (cleaned := event_id.strip())
            )
        )
        if not self.event_ids:
            raise ValueError("at least one event ID is required")
        self.calendar_id = calendar_id.strip()
        if calendar_id != self.calendar_id:
            raise ValueError("calendar_id must not contain surrounding whitespace")
        self.page_size = self._bounded_int(
            page_size,
            name="page_size",
            minimum=1,
            maximum=1000,
        )

    @classmethod
    def update_settings(cls, settings: BaseSettings) -> None:
        """Require rich Calendar read access and Calendar persistence."""
        settings.set(
            "MSGLOOM_DELTA_CHECKPOINT_ENABLED",
            False,
            priority="spider",
        )
        settings.set(
            "MSGLOOM_CALENDAR_DELTA_CHECKPOINT_ENABLED",
            False,
            priority="spider",
        )
        settings.set(
            "MSGLOOM_CRAWL_STATUS_ENABLED",
            False,
            priority="spider",
        )
        settings.set(
            "ITEM_PIPELINES",
            {
                "message_ingest.pipelines.evidence.RawEvidencePipeline": 200,
                "message_ingest.acquisition.evidence_link.EvidenceLinkPipeline": 250,
                "message_ingest.pipelines.calendar.CalendarPipeline": 300,
            },
            priority="spider",
        )
        super().update_settings(settings)

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        """Reject JOBDIR until targeted Calendar resume is explicitly tested."""
        if crawler.settings.get("JOBDIR"):
            raise ValueError("Calendar full acquisition does not support JOBDIR yet")
        return super().from_crawler(crawler, *args, **kwargs)

    async def start(self) -> AsyncIterator[Any]:
        """Schedule one full event-detail request per target."""
        self.crawler.stats.set_value("msgloom/crawl/mode", "calendar_full")
        self.crawler.stats.set_value("msgloom/crawl/run_id", self.run_id)
        self.crawler.stats.set_value(
            "msgloom/crawl/calendar/full/target_event_count",
            len(self.event_ids),
        )
        for event_id in self.event_ids:
            yield self._event_detail_request(event_id)

    def parse_event_detail(
        self,
        response: TextResponse,
        *,
        purpose: str,
        event_id: str,
    ) -> Iterator[Any]:
        """Persist full event JSON and inventory attachments when present."""
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence

        payload = response.json()
        if not isinstance(payload, dict):
            raise TypeError("Calendar event detail must be a JSON object")
        provider_id = payload.get("id")
        if not isinstance(provider_id, str) or not provider_id:
            raise ValueError("Calendar event detail must contain a non-empty id")
        if provider_id != event_id:
            raise ValueError("Calendar event detail ID changed in flight")

        calendar_key = self.calendar_id or "default"
        self.crawler.stats.inc_value("msgloom/crawl/calendar/full/event_detail_count")
        yield OutlookCalendarEventItem(
            event_id=event_id,
            raw=payload,
            observed_at=evidence.observed_at,
            evidence_id=evidence.evidence_id,
            run_id=self.run_id,
            calendar_id=calendar_key,
            observation_kind="full",
        )

        has_attachments = payload.get("hasAttachments")
        if has_attachments is True:
            yield self._attachments_request(event_id, page_number=1)
        elif has_attachments is not False and has_attachments is not None:
            raise ValueError("Calendar hasAttachments must be a boolean")

    def parse_attachments(
        self,
        response: TextResponse,
        *,
        purpose: str,
        event_id: str,
        page_number: int,
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

            type_name = self._attachment_type_name(attachment_type)
            self.crawler.stats.inc_value(
                f"msgloom/crawl/calendar/full/attachment_type_count/{type_name}"
            )
            if type_name in {"fileAttachment", "itemAttachment"}:
                yield self._attachment_raw_request(
                    event_id,
                    attachment_id,
                )
                if type_name == "itemAttachment":
                    yield self._item_attachment_detail_request(
                        event_id,
                        attachment_id,
                    )

        next_link = payload.get("@odata.nextLink")
        if next_link is None:
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

    def parse_attachment_detail(
        self,
        response: TextResponse,
        *,
        purpose: str,
        event_id: str,
        attachment_id: str,
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

    def _event_detail_request(self, event_id: str) -> scrapy.Request:
        """Request the full event representation with a text body."""
        event_path = self._event_path(event_id)
        return self._request(
            f"{self.graph_root}{event_path}",
            callback=self.parse_event_detail,
            purpose="calendar-event-detail",
            cb_kwargs={"event_id": event_id},
            prefer=('IdType="ImmutableId", outlook.body-content-type="text"'),
        )

    def _attachments_request(
        self,
        event_id: str,
        *,
        page_number: int,
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
            },
            prefer='IdType="ImmutableId"',
        )

    def _attachment_raw_request(
        self,
        event_id: str,
        attachment_id: str,
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
            },
            accept="*/*",
            prefer='IdType="ImmutableId"',
        )

    def _item_attachment_detail_request(
        self,
        event_id: str,
        attachment_id: str,
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
            },
            prefer='IdType="ImmutableId"',
        )

    @staticmethod
    def _attachment_type_name(attachment_type: str | None) -> str:
        """Normalize Graph namespace spellings while keeping unknown visible."""
        return (
            (attachment_type or "unknown")
            .removeprefix("#microsoft.graph.")
            .removeprefix("microsoft.graph.")
        )

    def _event_path(self, event_id: str) -> str:
        """Return an event path scoped to default or one named calendar."""
        encoded_event = quote(event_id, safe="")
        if not self.calendar_id:
            return f"/me/events/{encoded_event}"
        encoded_calendar = quote(self.calendar_id, safe="")
        return f"/me/calendars/{encoded_calendar}/events/{encoded_event}"
