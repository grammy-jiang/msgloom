"""Pin consumer-specific delta decisions across the protocol extraction."""

import json

import pytest
from scrapy import Request
from scrapy.http import TextResponse
from scrapy.utils.test import get_crawler

from message_ingest.items.acquisition import AcquisitionFailureItem, RawHttpEvidenceItem
from message_ingest.spiders.microsoft.outlook.calendar.delta import (
    OutlookCalendarDeltaSpider,
)
from message_ingest.spiders.microsoft.outlook.email.delta import OutlookDeltaSpider
from message_ingest.spiders.microsoft.outlook.email.folder_delta import (
    OutlookFolderDeltaSpider,
)


def build(spider_class):
    crawler = get_crawler(
        spider_class,
        settings_dict={
            "MSGLOOM_SOURCE_ID": "compatibility",
            "MSGLOOM_DATABASE_URL": "sqlite:///:memory:",
        },
    )
    kwargs = {}
    if spider_class is OutlookCalendarDeltaSpider:
        kwargs = {
            "start_datetime": "2026-09-27T00:00:00Z",
            "end_datetime": "2026-10-04T00:00:00Z",
        }
    spider = spider_class.from_crawler(crawler, **kwargs)
    crawler.spider = spider
    url = "https://graph.microsoft.com/v1.0/delta"
    if isinstance(spider, OutlookDeltaSpider):
        request = spider._message_delta_request(
            url, folder_id="folder", page_number=1, from_checkpoint=False, reset_count=0
        )
    else:
        request = spider._delta_request(
            url, page_number=1, from_checkpoint=False, reset_count=0
        )
    return spider, request


@pytest.mark.parametrize("spider_class", [OutlookDeltaSpider, OutlookFolderDeltaSpider])
def test_mail_and_folder_nextlink_wins_even_with_unused_invalid_delta(spider_class):
    _spider, request = build(spider_class)
    link = "https://graph.microsoft.com/v1.0/delta?$skiptoken=a%2fb"
    response = TextResponse(
        request.url,
        request=request,
        encoding="utf-8",
        body=json.dumps(
            {
                "@odata.nextLink": link,
                "@odata.deltaLink": 42,
            }
        ).encode(),
    )
    if request.callback is None:
        pytest.fail("Delta request requires a named callback")
    outputs = list(request.callback(response, **request.cb_kwargs))
    if not isinstance(outputs[0], RawHttpEvidenceItem):
        pytest.fail("Raw evidence must precede all parsing outputs")
    if not isinstance(outputs[-1], Request) or outputs[-1].url != link:
        pytest.fail("Mail and folder compatibility must let nextLink win")


@pytest.mark.parametrize("spider_class", [OutlookDeltaSpider, OutlookFolderDeltaSpider])
def test_mail_and_folder_empty_links_retain_missing_state_failure(spider_class):
    _spider, request = build(spider_class)
    response = TextResponse(
        request.url,
        request=request,
        encoding="utf-8",
        body=b'{"@odata.nextLink":"","@odata.deltaLink":""}',
    )
    if request.callback is None:
        pytest.fail("Delta request requires a named callback")
    outputs = list(request.callback(response, **request.cb_kwargs))
    if (
        not isinstance(outputs[-1], AcquisitionFailureItem)
        or outputs[-1].error_type != "DeltaStateMissing"
    ):
        pytest.fail("Legacy falsey links must retain missing-state failure items")


def test_calendar_conflict_preserves_observations_before_failure():
    spider, request = build(OutlookCalendarDeltaSpider)
    response = TextResponse(
        request.url,
        request=request,
        encoding="utf-8",
        body=json.dumps(
            {
                "value": [{"id": "event"}],
                "@odata.nextLink": "next",
                "@odata.deltaLink": "delta",
            }
        ).encode(),
    )
    if request.callback is None:
        pytest.fail("Delta request requires a named callback")
    outputs = list(request.callback(response, **request.cb_kwargs))
    if not isinstance(outputs[0], RawHttpEvidenceItem) or len(outputs) != 4:
        pytest.fail("Calendar must retain raw evidence, observation, and event")
    if (
        not isinstance(outputs[-1], AcquisitionFailureItem)
        or outputs[-1].error_type != "DeltaStateConflict"
    ):
        pytest.fail("Calendar must reject conflicting state after observations")
    if not spider.run_failed:
        pytest.fail("Calendar conflict must still block checkpoint promotion")
