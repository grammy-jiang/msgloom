"""Acquire full Microsoft Calendar event detail and attachments."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from typing import Any, ClassVar
from urllib.parse import quote

import scrapy
from scrapy.http import TextResponse
from scrapy.settings import BaseSettings
from twisted.python.failure import Failure

from message_ingest.acquisition.microsoft.outlook.calendar.profile import (
    FULL_V1,
    attachment_required_surfaces,
    attachment_type_name,
    surface_is_complete,
)
from message_ingest.catalog.stores.microsoft.outlook.calendar import (
    OutlookCalendarStore,
)
from message_ingest.extensions.catalog import CatalogService
from message_ingest.items.microsoft.outlook.calendar import (
    OutlookCalendarEventItem,
    OutlookCalendarEventSurfaceItem,
)

from ._attachments import OutlookCalendarAttachmentTraversal


class OutlookCalendarFullSpider(OutlookCalendarAttachmentTraversal):
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
        operation: str = "refresh",
        profile: str = FULL_V1,
        **kwargs,
    ) -> None:
        """Normalize target IDs, containing calendar, and acquisition policy."""
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
        self.operation = operation.strip().lower()
        if self.operation not in {"enrich", "refresh"}:
            raise ValueError("operation must be 'enrich' or 'refresh'")
        self.profile = profile.strip()
        if self.profile != FULL_V1:
            raise ValueError(f"unsupported profile: {self.profile!r}")
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
                "message_ingest.pipelines.microsoft.outlook.calendar.OutlookCalendarPipeline": 300,
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
        """Refresh all Full-v1 surfaces or schedule only persisted gaps."""
        self.crawler.stats.set_value("msgloom/crawl/mode", "calendar_full")
        self.crawler.stats.set_value("msgloom/crawl/run_id", self.run_id)
        self.crawler.stats.set_value(
            "msgloom/crawl/calendar/full/target_event_count",
            len(self.event_ids),
        )
        self.crawler.stats.set_value(
            "msgloom/crawl/calendar/full/operation",
            self.operation,
        )
        self.crawler.stats.set_value(
            "msgloom/crawl/calendar/full/profile",
            self.profile,
        )
        for event_id in self.event_ids:
            if self.operation == "refresh":
                yield self._event_detail_request(event_id)
                continue

            state = await asyncio.to_thread(self._load_enrichment_state, event_id)
            emitted = False
            for output in self._full_enrich_outputs(event_id, state):
                emitted = True
                yield output
            if not emitted:
                self.crawler.stats.inc_value(
                    "msgloom/crawl/calendar/full/already_complete_count"
                )

    def parse_event_detail(
        self,
        response: TextResponse,
        *,
        purpose: str,
        event_id: str,
        resource_version: str | None,
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

        provider_version = payload.get("changeKey")
        if provider_version is not None and not isinstance(provider_version, str):
            raise ValueError("Calendar event changeKey must be a string")
        effective_version = provider_version or resource_version

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
        yield OutlookCalendarEventSurfaceItem(
            event_id=event_id,
            surface="detail",
            status="acquired",
            observed_at=evidence.observed_at,
            evidence_id=evidence.evidence_id,
            profile_version=FULL_V1,
            resource_version=effective_version,
        )
        yield self._attachments_request(
            event_id,
            page_number=1,
            resource_version=effective_version,
        )

    def errback(self, failure: Failure) -> Iterator[Any]:
        """Persist terminal Full-v1 surface outcomes; leave transient gaps pending."""
        callback_data = self._failure_request(failure).cb_kwargs
        purpose = callback_data.get("purpose", "unknown")
        evidence = self._failure_evidence_item(failure)
        yield evidence
        terminal_status = {
            401: "unauthorized",
            403: "unauthorized",
            404: "unavailable",
            410: "unavailable",
            405: "unsupported",
        }.get(evidence.response_status or 0)
        surface = self._surface_for_purpose(
            purpose,
            callback_data.get("attachment_id"),
        )
        if terminal_status and surface and (event_id := callback_data.get("event_id")):
            yield OutlookCalendarEventSurfaceItem(
                event_id=event_id,
                surface=surface,
                status=terminal_status,
                observed_at=evidence.observed_at,
                evidence_id=evidence.evidence_id,
                profile_version=FULL_V1,
                resource_version=callback_data.get("resource_version"),
            )
        yield self._request_failure_item(failure, evidence)

    @staticmethod
    def _surface_for_purpose(
        purpose: str,
        attachment_id: str | None,
    ) -> str | None:
        if purpose == "calendar-event-detail":
            return "detail"
        if purpose == "calendar-event-attachments":
            return "attachments"
        if purpose == "calendar-attachment-raw" and attachment_id:
            return f"attachment_raw:{attachment_id}"
        if purpose == "calendar-item-attachment-detail" and attachment_id:
            return f"item_attachment_detail:{attachment_id}"
        return None

    def _load_enrichment_state(self, event_id: str) -> dict[str, Any]:
        catalog = CatalogService.from_crawler(self.crawler).catalog
        store = OutlookCalendarStore(
            catalog,
            source_id=self.crawler.settings["MSGLOOM_SOURCE_ID"],
        )
        event_state = store.get_event_state(event_id=event_id)
        return {
            "resource_version": (
                event_state.get("resource_version") if event_state is not None else None
            ),
            "surfaces": store.get_event_surfaces(event_id=event_id),
            "attachments": store.get_event_attachments(event_id=event_id),
        }

    def _full_enrich_outputs(self, event_id: str, state: dict[str, Any]):
        surfaces = state["surfaces"]
        resource_version = state["resource_version"]
        if not surface_is_complete(
            surfaces,
            "detail",
            resource_version=resource_version,
        ):
            yield self._event_detail_request(
                event_id,
                resource_version=resource_version,
            )
        if not surface_is_complete(
            surfaces,
            "attachments",
            resource_version=resource_version,
        ):
            yield self._attachments_request(
                event_id,
                page_number=1,
                resource_version=resource_version,
            )
            return
        if surfaces["attachments"]["status"] != "acquired":
            return

        for attachment in state["attachments"]:
            attachment_id = attachment["attachment_id"]
            attachment_type = attachment["attachment_type"]
            for surface in attachment_required_surfaces(
                attachment_type,
                attachment_id,
            ):
                if surface_is_complete(
                    surfaces, surface, resource_version=resource_version
                ):
                    continue
                if surface.startswith("attachment_raw:"):
                    normalized = attachment_type_name(attachment_type)
                    if normalized in {"fileAttachment", "itemAttachment"}:
                        yield self._attachment_raw_request(
                            event_id,
                            attachment_id,
                            resource_version=resource_version,
                        )
                    else:
                        yield OutlookCalendarEventSurfaceItem(
                            event_id=event_id,
                            surface=surface,
                            status="unsupported",
                            observed_at=attachment["latest_observed_at"],
                            evidence_id=attachment["latest_evidence_id"],
                            profile_version=FULL_V1,
                            resource_version=resource_version,
                        )
                elif surface.startswith("item_attachment_detail:"):
                    yield self._item_attachment_detail_request(
                        event_id,
                        attachment_id,
                        resource_version=resource_version,
                    )

    def _event_detail_request(
        self, event_id: str, *, resource_version: str | None = None
    ) -> scrapy.Request:
        """Request the full event representation with a text body."""
        event_path = self._event_path(event_id)
        return self._request(
            f"{self.graph_root}{event_path}",
            callback=self.parse_event_detail,
            purpose="calendar-event-detail",
            cb_kwargs={
                "event_id": event_id,
                "resource_version": resource_version,
            },
            prefer=('IdType="ImmutableId", outlook.body-content-type="text"'),
        )

    def _event_path(self, event_id: str) -> str:
        """Return an event path scoped to default or one named calendar."""
        encoded_event = quote(event_id, safe="")
        if not self.calendar_id:
            return f"/me/events/{encoded_event}"
        encoded_calendar = quote(self.calendar_id, safe="")
        return f"/me/calendars/{encoded_calendar}/events/{encoded_event}"
