"""Recurring-series topology traversal for Calendar Full-v1 acquisition."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import scrapy
from scrapy.http import TextResponse

from message_ingest.items.microsoft.outlook.calendar import (
    OutlookCalendarSeriesTopologyItem,
)
from microsoft_graph.protocol.calendar import calendar_series_master

from ._attachments import OutlookCalendarAttachmentTraversal


class OutlookCalendarSeriesTraversal(OutlookCalendarAttachmentTraversal):
    """Acquire recurring-series masters and emit topology observations."""

    def parse_series_master(
        self,
        response: TextResponse,
        *,
        purpose: str,
        series_master_id: str,
    ) -> Iterator[Any]:
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        payload = calendar_series_master(response.json(), expected_id=series_master_id)
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
        return self._request(
            self.series_master_path(series_master_id, calendar_id=self.calendar_id),
            callback=self.parse_series_master,
            purpose="calendar-series-master",
            cb_kwargs={"series_master_id": series_master_id},
            prefer='IdType="ImmutableId"',
        )


__all__ = ["OutlookCalendarSeriesTraversal"]
