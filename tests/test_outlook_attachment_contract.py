"""Keep attachment path reuse inside the application's request contract."""

import pytest
from scrapy.http import TextResponse
from scrapy.utils.request import request_from_dict
from scrapy.utils.test import get_crawler
from twisted.python.failure import Failure

from message_ingest.items.acquisition import AcquisitionFailureItem, RawHttpEvidenceItem
from message_ingest.spiders.microsoft.outlook.calendar.full import (
    OutlookCalendarFullSpider,
)
from message_ingest.spiders.microsoft.outlook.email.full import OutlookFullSpider
from microsoft_graph.protocol.attachments import (
    attachment_raw_path,
    item_attachment_path,
)
from microsoft_graph.request import graph_operation


@pytest.fixture(params=["mail", "calendar"])
def attachment_spider(request):
    cls = OutlookFullSpider if request.param == "mail" else OutlookCalendarFullSpider
    crawler = get_crawler(cls, {"MSGLOOM_MAX_RAW_CONTENT_BYTES": 12345})
    kwargs = (
        {"message_ids": "resource/+=%2F"}
        if request.param == "mail"
        else {
            "event_ids": ["resource/+=%2F"],
            "calendar_id": "calendar/+=",
            "page_size": "25",
        }
    )
    return cls.from_crawler(crawler, **kwargs)


def test_path_primitives_preserve_application_request_and_evidence_contract(
    attachment_spider,
):
    spider = attachment_spider
    resource_id, attachment_id = "resource/+=%2F", "attachment/+=%2F"
    calendar = isinstance(spider, OutlookCalendarFullSpider)
    parent = (
        spider.event_path(resource_id, calendar_id=spider.calendar_id)
        if calendar
        else spider.message_path(resource_id)
    )
    cases = [
        (
            spider._attachments_request(resource_id, page_number=1),
            f"{parent}/attachments?"
            + ("%24top=25&" if calendar else "")
            + "%24select=id%2Cname%2CcontentType%2Csize%2CisInline%2C"
            "lastModifiedDateTime",
            b"application/json",
        ),
        (
            spider._attachment_raw_request(resource_id, attachment_id),
            attachment_raw_path(parent, attachment_id),
            b"*/*",
        ),
        (
            spider._item_attachment_detail_request(resource_id, attachment_id),
            item_attachment_path(parent, attachment_id),
            b"application/json",
        ),
    ]
    for request, path, accept in cases:
        if request.url != spider.graph_root + path:
            pytest.fail("Attachment endpoint/query bytes changed")
        if request.headers.get("Accept") != accept:
            pytest.fail("Attachment representation changed")
        if request.headers.get("Prefer") != b'IdType="ImmutableId"':
            pytest.fail("Attachment immutable-ID preference changed")
        if request.meta.get("download_maxsize") != 12345 or request.meta.get(
            "dont_cache"
        ):
            pytest.fail("Attachment transport limits or cache behavior changed")
        if graph_operation(request) != request.cb_kwargs["purpose"]:
            pytest.fail("Transport operation lost application purpose")
        restored = request_from_dict(request.to_dict(spider=spider), spider=spider)
        if restored.callback != request.callback or restored.errback != spider.errback:
            pytest.fail("JOBDIR must retain application callbacks and errback")
        if restored.cb_kwargs != request.cb_kwargs or restored.meta != request.meta:
            pytest.fail("JOBDIR must retain attachment traversal context")
        response = TextResponse(request.url, request=request, body=b"invalid JSON")
        if request.callback is None:
            pytest.fail("Attachment callback is missing")
        output = iter(request.callback(response, **request.cb_kwargs))
        if not isinstance(next(output), RawHttpEvidenceItem):
            pytest.fail("Evidence must precede attachment parsing")

    failure = Failure(RuntimeError("transport failed"))
    failure.request = cases[0][0]  # type: ignore[attr-defined]
    output = list(spider.errback(failure))
    if not isinstance(output[0], RawHttpEvidenceItem) or not isinstance(
        output[1], AcquisitionFailureItem
    ):
        pytest.fail(
            "Attachment failures must retain evidence-first application handling"
        )


def test_attachment_request_only_framework_layer_is_removed():
    for cls in (OutlookFullSpider, OutlookCalendarFullSpider):
        for name in (
            "attachment_list_request",
            "attachment_raw_request",
            "item_attachment_request",
        ):
            if hasattr(cls, name):
                pytest.fail("Unused request layer must not duplicate path primitives")
