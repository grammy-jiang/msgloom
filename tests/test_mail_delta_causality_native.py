"""Native Scrapy Mail Delta request/candidate keeps its causal identity."""

import asyncio
import json
from pathlib import Path

import pytest
from scrapy.http import Request, TextResponse
from scrapy.utils.test import get_crawler

from message_ingest.items.microsoft.outlook.email import (
    OutlookDeltaCheckpointCandidateItem,
)
from message_ingest.spiders.microsoft.outlook.email.delta import OutlookDeltaSpider


def _crawler(tmp_path: Path):
    return get_crawler(
        OutlookDeltaSpider,
        settings_dict={
            "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
            "MSGLOOM_SOURCE_ID": "source-1",
            "MSGLOOM_CATALOG_ENABLED": True,
        },
    )


async def _start(spider: OutlookDeltaSpider) -> None:
    async for _request in spider.start():
        pass


def test_native_delta_request_pagination_and_checkpoint_propagate_baseline(
    tmp_path: Path,
) -> None:
    crawler = _crawler(tmp_path)
    spider = OutlookDeltaSpider.from_crawler(crawler)
    asyncio.run(_start(spider))
    first = spider._message_delta_start_request("inbox")
    baseline = first.cb_kwargs.get("baseline_identity")
    if not isinstance(baseline, str) or not baseline.startswith("a:"):
        pytest.fail("First native request lacks a genuine absent baseline")
    # A native Scrapy serialization round-trip must preserve the exact tag.
    from scrapy.utils.request import request_from_dict

    restored = request_from_dict(first.to_dict(spider=spider), spider=spider)
    if restored.cb_kwargs.get("baseline_identity") != baseline:
        pytest.fail("Native JOBDIR request serialization stripped causal proof")
    response = TextResponse(
        restored.url,
        request=restored,
        encoding="utf-8",
        body=json.dumps(
            {"value": [], "@odata.nextLink": "https://graph.test/next"}
        ).encode(),
    )
    outputs = list(spider.parse_message_delta(response, **restored.cb_kwargs))
    continued = [item for item in outputs if isinstance(item, Request)]
    if len(continued) != 1 or continued[0].cb_kwargs["baseline_identity"] != baseline:
        pytest.fail("Opaque nextLink did not retain original causal baseline")
    response2 = TextResponse(
        continued[0].url,
        request=continued[0],
        encoding="utf-8",
        body=json.dumps(
            {"value": [], "@odata.deltaLink": "https://graph.test/delta-Y"}
        ).encode(),
    )
    outputs2 = list(spider.parse_message_delta(response2, **continued[0].cb_kwargs))
    candidates = [
        item
        for item in outputs2
        if isinstance(item, OutlookDeltaCheckpointCandidateItem)
    ]
    if len(candidates) != 1 or candidates[0].baseline_identity != baseline:
        pytest.fail("Terminal candidate changed initial request identity")


def test_legacy_active_resume_cannot_infer_baseline_from_current_checkpoint(
    tmp_path: Path,
) -> None:
    crawler = _crawler(tmp_path)
    spider = OutlookDeltaSpider.from_crawler(crawler)
    spider.state = {
        "msgloom_delta": {
            "run_id": "legacy",
            "started_folder_ids": ["inbox"],
            "completed_folder_ids": [],
            "delta_start_scheduled": True,
            "baseline_identities": {},
        }
    }
    with pytest.raises(ValueError, match="causal cursor"):
        asyncio.run(_start(spider))
    if not spider._run_failed:
        pytest.fail("Invalid JOBDIR cursor ancestry was not marked failed")
