"""
Record final HTTP surface outcomes without treating transient failures as
complete.
"""

from __future__ import annotations

import pytest
from scrapy.http import Response
from scrapy.spidermiddlewares.httperror import HttpError
from scrapy.utils.test import get_crawler
from twisted.python.failure import Failure

from message_ingest.items import (
    AcquisitionFailureItem,
    OutlookMessageSurfaceItem,
    RawHttpEvidenceItem,
)
from message_ingest.profiles import FULL_V1
from message_ingest.spiders.outlook_full import OutlookFullSpider


def _spider() -> OutlookFullSpider:
    crawler = get_crawler(OutlookFullSpider)
    return OutlookFullSpider.from_crawler(crawler, message_ids="m1")


def _failure(request, status: int) -> Failure:
    response = Response(request.url, status=status, request=request)
    failure = Failure(HttpError(response, "filtered"))
    # Scrapy attaches this attribute dynamically before calling an errback.
    failure.__dict__["request"] = request
    return failure


def test_forbidden_full_surface_becomes_terminal_unauthorized() -> None:
    spider = _spider()
    request = spider._message_mime_request("m1")
    output = list(spider.errback(_failure(request, 403)))

    evidence = next(value for value in output if isinstance(value, RawHttpEvidenceItem))
    surface = next(
        value for value in output if isinstance(value, OutlookMessageSurfaceItem)
    )
    failure = next(
        value for value in output if isinstance(value, AcquisitionFailureItem)
    )
    if surface.surface != "mime":
        pytest.fail('Expected: surface.surface == "mime"')
    if surface.status != "unauthorized":
        pytest.fail('Expected: surface.status == "unauthorized"')
    if surface.profile_version != FULL_V1:
        pytest.fail("Expected: surface.profile_version == FULL_V1")
    if surface.evidence_id != evidence.evidence_id:
        pytest.fail("Expected: surface.evidence_id == evidence.evidence_id")
    if failure.evidence_id != evidence.evidence_id:
        pytest.fail("Expected: failure.evidence_id == evidence.evidence_id")
    if failure.observed_at != evidence.observed_at:
        pytest.fail("Expected: failure.observed_at == evidence.observed_at")


def test_missing_message_detail_becomes_terminal_unavailable() -> None:
    spider = _spider()
    request = spider._message_detail_request("m1")
    output = list(spider.errback(_failure(request, 404)))
    if not isinstance(output[0], RawHttpEvidenceItem):
        pytest.fail("Expected: isinstance(output[0], RawHttpEvidenceItem)")
    surface = next(
        value for value in output if isinstance(value, OutlookMessageSurfaceItem)
    )
    if surface.surface != "detail":
        pytest.fail('Expected: surface.surface == "detail"')
    if surface.status != "unavailable":
        pytest.fail('Expected: surface.status == "unavailable"')


def test_method_not_allowed_attachment_raw_becomes_terminal_unsupported() -> None:
    spider = _spider()
    request = spider._attachment_raw_request("m1", "a1")
    output = list(spider.errback(_failure(request, 405)))
    if not isinstance(output[0], RawHttpEvidenceItem):
        pytest.fail("Expected: isinstance(output[0], RawHttpEvidenceItem)")
    surface = next(
        value for value in output if isinstance(value, OutlookMessageSurfaceItem)
    )
    if surface.surface != "attachment_raw:a1":
        pytest.fail('Expected: surface.surface == "attachment_raw:a1"')
    if surface.status != "unsupported":
        pytest.fail('Expected: surface.status == "unsupported"')


def test_server_error_remains_failure_not_terminal_surface() -> None:
    spider = _spider()
    request = spider._message_mime_request("m1")
    output = list(spider.errback(_failure(request, 500)))
    if not isinstance(output[0], RawHttpEvidenceItem):
        pytest.fail("Expected: isinstance(output[0], RawHttpEvidenceItem)")
    if any(isinstance(value, OutlookMessageSurfaceItem) for value in output):
        pytest.fail(
            "Expected: not any(isinstance(value, OutlookMessageSurfaceItem) for value in output)"
        )
    if not any(isinstance(value, AcquisitionFailureItem) for value in output):
        pytest.fail(
            "Expected: any(isinstance(value, AcquisitionFailureItem) for value in output)"
        )
