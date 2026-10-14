"""Freeze Mail delta authority at native first-request creation."""

from __future__ import annotations

from typing import Any

import scrapy

from message_ingest.sync.microsoft.outlook.email._cursor_causality import (
    absent_baseline,
)


def committed_delta_links(starts: dict[str, tuple[str | None, str]]) -> dict[str, str]:
    """Retain only live Graph links from the fuller baseline snapshot."""
    return {
        folder: link for folder, (link, _baseline) in starts.items() if link is not None
    }


def start_message_delta_request(spider: Any, folder_id: str) -> scrapy.Request:
    """Use one startup snapshot or capture an explicit first-request baseline."""
    spider.crawler.stats.inc_value("msgloom/crawl/delta/folder_started_count")
    if folder_id in spider._delta_baselines:
        raise ValueError("Mail delta folder already started with a frozen cursor")
    if folder_id in spider._delta_initial_starts:
        link, baseline = spider._delta_initial_starts[folder_id]
    else:
        # First request on the reactor must not perform blocking SQL. A
        # missing startup entry had no committed cursor or absence epoch;
        # concurrent later writes make this CAS fail closed at promotion.
        link = None
        baseline = absent_baseline(
            spider.crawler.settings["MSGLOOM_SOURCE_ID"], folder_id
        )
    spider._delta_baselines[folder_id] = baseline
    spider._persist_execution_state()
    if link is not None:
        spider.crawler.stats.inc_value("msgloom/crawl/delta/folder_resumed_count")
        return spider._message_delta_request(
            link,
            folder_id=folder_id,
            page_number=1,
            from_checkpoint=True,
            reset_count=0,
            baseline_identity=baseline,
        )
    spider.crawler.stats.inc_value("msgloom/crawl/delta/folder_initial_count")
    return spider._initial_message_delta_request(
        folder_id, reset_count=0, baseline_identity=baseline
    )


__all__ = ["committed_delta_links", "start_message_delta_request"]
