"""
Keep expired delta-token recovery bounded and retain evidence from failed
attempts.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from scrapy.http import Request, Response
from scrapy.spidermiddlewares.httperror import HttpError
from scrapy.utils.test import get_crawler
from twisted.python.failure import Failure

from message_ingest.items import AcquisitionFailureItem
from message_ingest.spiders.outlook_delta import OutlookDeltaSpider


def _spider(tmp_path: Path) -> OutlookDeltaSpider:
    crawler = get_crawler(
        OutlookDeltaSpider,
        settings_dict={
            "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
            "MSGLOOM_SOURCE_ID": "source-1",
            "MSGLOOM_CATALOG_ENABLED": True,
        },
    )
    return OutlookDeltaSpider.from_crawler(crawler)


def _http_failure(request, status: int) -> Failure:
    response = Response(request.url, status=status, request=request)
    failure = Failure(HttpError(response, "filtered"))
    # Scrapy attaches this attribute dynamically before calling an errback.
    failure.__dict__["request"] = request
    return failure


def test_expired_checkpoint_410_restarts_folder_delta_without_committing_failure(
    tmp_path: Path,
) -> None:
    spider = _spider(tmp_path)
    spider._delta_links["folder-1"] = (
        "https://graph.microsoft.com/v1.0/me/mailFolders/folder-1/messages/delta?$deltatoken=old"
    )
    request = spider._message_delta_start_request("folder-1")
    if request.cb_kwargs["from_checkpoint"] is not True:
        pytest.fail('Expected: request.cb_kwargs["from_checkpoint"] is True')

    output = list(spider.errback(_http_failure(request, 410)))

    reset = next(value for value in output if isinstance(value, Request))
    if reset.cb_kwargs["purpose"] != "message-delta":
        pytest.fail('Expected: reset.cb_kwargs["purpose"] == "message-delta"')
    if reset.cb_kwargs["folder_id"] != "folder-1":
        pytest.fail('Expected: reset.cb_kwargs["folder_id"] == "folder-1"')
    if reset.cb_kwargs["from_checkpoint"] is not False:
        pytest.fail('Expected: reset.cb_kwargs["from_checkpoint"] is False')
    if reset.cb_kwargs["reset_count"] != 1:
        pytest.fail('Expected: reset.cb_kwargs["reset_count"] == 1')
    if "$deltatoken=" in reset.url:
        pytest.fail('Expected: "$deltatoken=" not in reset.url')
    if spider._run_failed is not False:
        pytest.fail("Expected: spider._run_failed is False")
    if (
        spider.crawler.stats.get_value("msgloom/crawl/delta/checkpoint_reset_count")
        != 1
    ):
        pytest.fail(
            'Expected: spider.crawler.stats.get_value( "msgloom/crawl/delta/checkpoint_reset_count" ) == 1'
        )


def test_second_410_after_reset_fails_round_instead_of_looping(tmp_path: Path) -> None:
    spider = _spider(tmp_path)
    request = spider._initial_message_delta_request("folder-1", reset_count=1)

    output = list(spider.errback(_http_failure(request, 410)))

    if spider._run_failed is not True:
        pytest.fail("Expected: spider._run_failed is True")
    if not any(isinstance(value, AcquisitionFailureItem) for value in output):
        pytest.fail(
            "Expected: any(isinstance(value, AcquisitionFailureItem) for value in output)"
        )
    if any(hasattr(value, "cb_kwargs") for value in output):
        pytest.fail(
            'Expected: not any(hasattr(value, "cb_kwargs") for value in output)'
        )
