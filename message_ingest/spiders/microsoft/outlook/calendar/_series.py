"""Recurring-series topology traversal for Calendar Full-v1 acquisition."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from urllib.parse import urlencode

import scrapy
from scrapy.http import TextResponse

from message_ingest.items.microsoft.outlook.calendar import (
    OutlookCalendarSeriesTopologyItem,
)

from ._attachments import OutlookCalendarAttachmentTraversal


class OutlookCalendarSeriesTraversal(OutlookCalendarAttachmentTraversal):
    """Own recurring-series master lookup and topology parsing."""

    def parse_series_master(
        self,
        response: TextResponse,
        *,
        purpose: str,
        series_master_id: str,
    ) -> Iterator[Any]:
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        payload = response.json()
        if not isinstance(payload, dict):
            raise TypeError("Calendar series master must be a JSON object")
        if payload.get("id") != series_master_id:
            raise ValueError("Calendar series master ID changed in flight")
        cancelled = payload.get("cancelledOccurrences", [])
        exceptions = payload.get("exceptionOccurrences", [])
        if not isinstance(cancelled, list) or not all(
            isinstance(value, str) for value in cancelled
        ):
            raise TypeError("Calendar cancelledOccurrences must be a string list")
        if not isinstance(exceptions, list) or not all(
            isinstance(value, dict) for value in exceptions
        ):
            raise TypeError("Calendar exceptionOccurrences must be an object list")
        self.crawler.stats.inc_value(
            "msgloom/crawl/calendar/full/series_topology_count"
        )
        yield OutlookCalendarSeriesTopologyItem(
            series_master_id=series_master_id,
            calendar_id=self.calendar_id or "default",
            status="acquired",
            raw=payload,
            observed_at=evidence.observed_at,
            evidence_id=evidence.evidence_id,
            run_id=self.run_id,
        )

    def _series_master_request(self, series_master_id: str) -> scrapy.Request:
        event_path = self._event_path(series_master_id)
        query = urlencode(
            {
                "$select": (
                    "id,changeKey,type,subject,start,end,occurrenceId,"
                    "exceptionOccurrences,cancelledOccurrences"
                ),
                "$expand": "exceptionOccurrences",
            }
        )
        return self._request(
            f"{self.graph_root}{event_path}?{query}",
            callback=self.parse_series_master,
            purpose="calendar-series-master",
            cb_kwargs={"series_master_id": series_master_id},
            prefer='IdType="ImmutableId"',
        )

    @staticmethod
    def _series_master_id(payload: dict[str, Any], event_id: str) -> str | None:
        event_type = payload.get("type")
        if event_type == "seriesMaster":
            return event_id
        if event_type not in {"occurrence", "exception"}:
            return None
        series_master_id = payload.get("seriesMasterId")
        return (
            series_master_id
            if isinstance(series_master_id, str) and series_master_id
            else None
        )


__all__ = ["OutlookCalendarSeriesTraversal"]
