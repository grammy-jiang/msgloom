"""Freeze Mail delta authority at native first-request creation."""

from __future__ import annotations

import asyncio
from typing import Any

import scrapy

from message_ingest.sync.microsoft.outlook.email._cursor_causality import (
    absent_baseline,
)
from message_ingest.sync.microsoft.outlook.email.checkpoints import (
    OutlookDeltaCheckpointStore,
)


async def load_delta_start_snapshot(spider: Any) -> None:
    """Release native JOBDIR callbacks after exact cursor snapshot loading."""
    try:
        spider._restore_execution_state()
        store = OutlookDeltaCheckpointStore.from_crawler(spider.crawler)
        spider._delta_initial_starts = await asyncio.to_thread(store.get_delta_starts)
        spider._delta_links = committed_delta_links(spider._delta_initial_starts)
        if any(
            folder not in spider._delta_baselines
            for folder in spider._started_folder_ids
        ):
            spider.mark_run_failed("delta_baseline_missing_on_resume")
            raise ValueError("Resumed Mail delta run lacks causal cursor identities")
    except BaseException:
        spider._delta_snapshot_failed = True
        raise
    finally:
        spider._delta_snapshot_ready.set()


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


__all__ = [
    "committed_delta_links",
    "load_delta_start_snapshot",
    "start_message_delta_request",
]
